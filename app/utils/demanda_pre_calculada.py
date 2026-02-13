"""
Utilitario para buscar demanda pre-calculada da tabela demanda_pre_calculada.

Garante que tanto a Tela de Demanda quanto a Tela de Pedido Fornecedor
usem os mesmos valores de demanda, mantendo INTEGRIDADE TOTAL.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from psycopg2.extras import RealDictCursor
import numpy as np


def calcular_proporcoes_vendas_por_loja(
    conn,
    cod_produtos: List[str],
    cod_empresas: List[int],
    dias_historico: int = 365
) -> Dict:
    """
    Calcula a proporcao de vendas de cada loja para cada produto.

    Esta funcao e usada para ratear a demanda consolidada de forma proporcional
    as vendas historicas de cada loja, em vez de dividir uniformemente.

    Args:
        conn: Conexao com o banco de dados
        cod_produtos: Lista de codigos de produtos
        cod_empresas: Lista de codigos de empresas/lojas
        dias_historico: Numero de dias de historico para calcular proporcao (default: 365)

    Returns:
        Dicionario com chave (cod_produto, cod_empresa) -> proporcao (0.0 a 1.0)
        A soma das proporcoes de todas as lojas para um produto = 1.0
    """
    if not cod_produtos or not cod_empresas:
        return {}

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Converter codigos para int
    cod_produtos_int = [int(c) for c in cod_produtos]
    placeholders_prod = ','.join(['%s'] * len(cod_produtos_int))
    placeholders_emp = ','.join(['%s'] * len(cod_empresas))

    data_inicio = datetime.now().date() - timedelta(days=dias_historico)

    # Query para somar vendas por produto/loja
    query = f"""
        SELECT
            codigo,
            cod_empresa,
            SUM(qtd_venda) as total_vendas
        FROM historico_vendas_diario
        WHERE codigo IN ({placeholders_prod})
          AND cod_empresa IN ({placeholders_emp})
          AND data >= %s
        GROUP BY codigo, cod_empresa
    """
    params = cod_produtos_int + list(cod_empresas) + [data_inicio]

    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()

    # Calcular total de vendas por produto (todas as lojas)
    totais_por_produto = {}
    vendas_por_produto_loja = {}

    for row in rows:
        cod_produto = str(row['codigo'])
        cod_empresa = row['cod_empresa']
        total_vendas = float(row['total_vendas'] or 0)

        # Acumular total do produto
        if cod_produto not in totais_por_produto:
            totais_por_produto[cod_produto] = 0
        totais_por_produto[cod_produto] += total_vendas

        # Guardar venda por produto/loja
        vendas_por_produto_loja[(cod_produto, cod_empresa)] = total_vendas

    # Calcular proporcoes
    proporcoes = {}
    for (cod_produto, cod_empresa), vendas in vendas_por_produto_loja.items():
        total_produto = totais_por_produto.get(cod_produto, 0)
        if total_produto > 0:
            proporcao = vendas / total_produto
        else:
            # Se nao houver vendas, distribui uniformemente
            proporcao = 1.0 / len(cod_empresas)

        proporcoes[(cod_produto, cod_empresa)] = proporcao

    return proporcoes


def precarregar_demanda_em_lote(
    conn,
    cod_produtos: List[str],
    cnpj_fornecedor: str,
    cod_empresas: List[int] = None,
    ano: int = None,
    mes: int = None
) -> Dict:
    """
    Pre-carrega demanda de multiplos produtos em uma unica query.

    Otimizacao de performance: em vez de N queries individuais,
    faz uma unica query para todos os produtos.

    Args:
        conn: Conexao com o banco de dados
        cod_produtos: Lista de codigos de produtos
        cnpj_fornecedor: CNPJ do fornecedor
        cod_empresas: Lista de codigos de empresas/lojas (None = consolidado)
        ano: Ano do periodo (default: ano atual)
        mes: Mes do periodo (default: mes atual)

    Returns:
        Dicionario com chave (cod_produto, cod_empresa) -> dados da demanda
        cod_empresa = None para dados consolidados
    """
    if not cod_produtos:
        return {}

    if ano is None:
        ano = datetime.now().year
    if mes is None:
        mes = datetime.now().month

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Converter codigos para string
    cod_produtos_str = [str(c) for c in cod_produtos]
    placeholders = ','.join(['%s'] * len(cod_produtos_str))

    # Query para buscar todos os produtos de uma vez
    if cod_empresas:
        # Buscar por lojas especificas + consolidado (NULL)
        cod_empresas_query = cod_empresas + [None]
        emp_placeholders = ','.join(['%s' if e is not None else 'NULL' for e in cod_empresas_query])

        query = f"""
            SELECT *
            FROM vw_demanda_efetiva
            WHERE cod_produto IN ({placeholders})
              AND cnpj_fornecedor = %s
              AND ano = %s
              AND mes = %s
              AND (cod_empresa IN ({emp_placeholders}) OR cod_empresa IS NULL)
        """
        params = cod_produtos_str + [cnpj_fornecedor, ano, mes] + [e for e in cod_empresas if e is not None]
    else:
        # Buscar apenas consolidado (cod_empresa IS NULL)
        query = f"""
            SELECT *
            FROM vw_demanda_efetiva
            WHERE cod_produto IN ({placeholders})
              AND cnpj_fornecedor = %s
              AND ano = %s
              AND mes = %s
              AND cod_empresa IS NULL
        """
        params = cod_produtos_str + [cnpj_fornecedor, ano, mes]

    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()

    # Montar cache: (cod_produto, cod_empresa) -> dados
    cache = {}
    for row in rows:
        key = (str(row['cod_produto']), row.get('cod_empresa'))
        cache[key] = dict(row)

    return cache


def obter_demanda_do_cache(
    cache: Dict,
    cod_produto: str,
    cod_empresa: int = None,
    num_lojas: int = 1,
    proporcao_loja: float = None
) -> Tuple[float, float, Dict]:
    """
    Obtem demanda do cache pre-carregado.

    Args:
        cache: Cache retornado por precarregar_demanda_em_lote()
        cod_produto: Codigo do produto
        cod_empresa: Codigo da empresa/loja (None = consolidado)
        num_lojas: Numero de lojas para dividir demanda consolidada (default=1)
        proporcao_loja: Proporcao de vendas desta loja (0.0 a 1.0). Se informado,
                        usa rateio proporcional em vez de divisao uniforme.

    Returns:
        Tupla (demanda_diaria, desvio_padrao, metadata)
    """
    key = (str(cod_produto), cod_empresa)
    demanda = cache.get(key)

    # FALLBACK: Se nao encontrou por loja especifica, usar consolidado e ratear
    usar_consolidado_rateado = False
    metodo_rateio = None
    if not demanda and cod_empresa is not None:
        key_consolidado = (str(cod_produto), None)
        demanda = cache.get(key_consolidado)
        if demanda:
            usar_consolidado_rateado = True

    if demanda:
        demanda_diaria = float(demanda.get('demanda_diaria_base', 0) or 0)
        desvio = float(demanda.get('desvio_padrao', 0) or 0)

        # Se usando consolidado para loja especifica, aplicar rateio
        if usar_consolidado_rateado:
            if proporcao_loja is not None and proporcao_loja > 0:
                # RATEIO PROPORCIONAL: usa proporcao baseada em vendas historicas
                # Demanda: rateia linearmente pela proporcao
                demanda_diaria = demanda_diaria * proporcao_loja
                # Desvio: usa raiz quadrada da proporcao (propriedade estatistica da variancia)
                # Variancia rateia linearmente, desvio padrao rateia pela raiz
                desvio = desvio * np.sqrt(proporcao_loja)
                metodo_rateio = 'proporcional'
            elif num_lojas > 1:
                # RATEIO UNIFORME (fallback): divide igualmente
                demanda_diaria = demanda_diaria / num_lojas
                # Desvio: usa raiz quadrada do numero de lojas
                desvio = desvio / np.sqrt(num_lojas)
                metodo_rateio = 'uniforme'

        return (
            demanda_diaria,
            desvio,
            {
                'fonte': 'pre_calculada_consolidada' if usar_consolidado_rateado else 'pre_calculada',
                'metodo_usado': demanda.get('metodo_usado', 'auto'),
                'fator_sazonal': float(demanda.get('fator_sazonal', 1.0) or 1.0),
                'fator_tendencia_yoy': float(demanda.get('fator_tendencia_yoy', 1.0) or 1.0),
                'classificacao_tendencia': demanda.get('classificacao_tendencia', 'nao_calculado'),
                'limitador_aplicado': demanda.get('limitador_aplicado', False),
                'tem_ajuste_manual': demanda.get('tem_ajuste_manual', False),
                'data_calculo': demanda.get('data_calculo'),
                'demanda_mensal': float(demanda.get('demanda_efetiva', 0) or 0),
                'variacao_vs_aa': demanda.get('variacao_vs_aa'),
                'metodo_rateio': metodo_rateio,
                'proporcao_loja': proporcao_loja if usar_consolidado_rateado else None
            }
        )

    return (0, 0, {'fonte': 'sem_dados', 'metodo_usado': 'sem_historico'})


def buscar_demanda_pre_calculada(
    conn,
    cod_produto: str,
    cnpj_fornecedor: str,
    ano: int = None,
    mes: int = None,
    cod_empresa: int = None
) -> Optional[Dict]:
    """
    Busca demanda pre-calculada de um item para um periodo especifico.

    Args:
        conn: Conexao com o banco de dados
        cod_produto: Codigo do produto
        cnpj_fornecedor: CNPJ do fornecedor
        ano: Ano do periodo (default: ano atual)
        mes: Mes do periodo (default: mes atual)
        cod_empresa: Codigo da empresa/loja (NULL = consolidado)

    Returns:
        Dicionario com dados da demanda ou None se nao encontrado
    """
    if ano is None:
        ano = datetime.now().year
    if mes is None:
        mes = datetime.now().month

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Usar a view que retorna demanda efetiva (ajuste manual ou calculada)
    cursor.execute("""
        SELECT *
        FROM vw_demanda_efetiva
        WHERE cod_produto = %s
          AND cnpj_fornecedor = %s
          AND ano = %s
          AND mes = %s
          AND (cod_empresa = %s OR (cod_empresa IS NULL AND %s IS NULL))
    """, (str(cod_produto), cnpj_fornecedor, ano, mes, cod_empresa, cod_empresa))

    row = cursor.fetchone()
    cursor.close()

    if row:
        return dict(row)
    return None


def buscar_demanda_proximos_meses(
    conn,
    cod_produto: str,
    cnpj_fornecedor: str,
    meses: int = 12,
    cod_empresa: int = None
) -> List[Dict]:
    """
    Busca demanda pre-calculada para os proximos N meses.

    Args:
        conn: Conexao com o banco de dados
        cod_produto: Codigo do produto
        cnpj_fornecedor: CNPJ do fornecedor
        meses: Numero de meses a buscar
        cod_empresa: Codigo da empresa/loja (NULL = consolidado)

    Returns:
        Lista de dicionarios com dados da demanda por mes
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    agora = datetime.now()
    ano_atual = agora.year
    mes_atual = agora.month

    cursor.execute("""
        SELECT *
        FROM vw_demanda_efetiva
        WHERE cod_produto = %s
          AND cnpj_fornecedor = %s
          AND (cod_empresa = %s OR (cod_empresa IS NULL AND %s IS NULL))
          AND (ano * 100 + mes) >= %s
        ORDER BY ano, mes
        LIMIT %s
    """, (
        str(cod_produto),
        cnpj_fornecedor,
        cod_empresa,
        cod_empresa,
        ano_atual * 100 + mes_atual,
        meses
    ))

    rows = cursor.fetchall()
    cursor.close()

    return [dict(row) for row in rows]


def obter_demanda_diaria_efetiva(
    conn,
    cod_produto: str,
    cnpj_fornecedor: str,
    cod_empresa: int = None
) -> Tuple[float, float, Dict]:
    """
    Obtem demanda diaria efetiva para uso no calculo de pedidos.

    Esta funcao substitui o uso direto de DemandCalculator.calcular_demanda_inteligente()
    garantindo que a demanda usada no Pedido Fornecedor seja a mesma da Tela Demanda.

    Args:
        conn: Conexao com o banco de dados
        cod_produto: Codigo do produto
        cnpj_fornecedor: CNPJ do fornecedor
        cod_empresa: Codigo da empresa/loja (NULL = consolidado)

    Returns:
        Tupla (demanda_diaria, desvio_padrao, metadata)
        Se nao houver dados pre-calculados, retorna (0, 0, {'fonte': 'sem_dados'})
    """
    demanda = buscar_demanda_pre_calculada(
        conn,
        cod_produto,
        cnpj_fornecedor,
        cod_empresa=cod_empresa
    )

    if demanda:
        return (
            float(demanda.get('demanda_diaria_base', 0) or 0),
            float(demanda.get('desvio_padrao', 0) or 0),
            {
                'fonte': 'pre_calculada',
                'metodo_usado': demanda.get('metodo_usado', 'auto'),
                'fator_sazonal': float(demanda.get('fator_sazonal', 1.0) or 1.0),
                'fator_tendencia_yoy': float(demanda.get('fator_tendencia_yoy', 1.0) or 1.0),
                'classificacao_tendencia': demanda.get('classificacao_tendencia', 'nao_calculado'),
                'limitador_aplicado': demanda.get('limitador_aplicado', False),
                'tem_ajuste_manual': demanda.get('tem_ajuste_manual', False),
                'data_calculo': demanda.get('data_calculo'),
                'demanda_mensal': float(demanda.get('demanda_efetiva', 0) or 0),
                'variacao_vs_aa': demanda.get('variacao_vs_aa')
            }
        )

    return (0, 0, {'fonte': 'sem_dados', 'metodo_usado': 'sem_historico'})


def verificar_dados_disponiveis(conn, cnpj_fornecedor: str = None) -> Dict:
    """
    Verifica se ha dados pre-calculados disponiveis.

    Args:
        conn: Conexao com o banco de dados
        cnpj_fornecedor: CNPJ do fornecedor (opcional, para filtrar)

    Returns:
        Dicionario com estatisticas dos dados disponiveis
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if cnpj_fornecedor:
        cursor.execute("""
            SELECT
                COUNT(*) as total_registros,
                COUNT(DISTINCT cod_produto) as produtos_unicos,
                MIN(data_calculo) as primeiro_calculo,
                MAX(data_calculo) as ultimo_calculo,
                COUNT(CASE WHEN ajuste_manual IS NOT NULL THEN 1 END) as com_ajuste_manual
            FROM demanda_pre_calculada
            WHERE cnpj_fornecedor = %s
        """, (cnpj_fornecedor,))
    else:
        cursor.execute("""
            SELECT
                COUNT(*) as total_registros,
                COUNT(DISTINCT cod_produto) as produtos_unicos,
                COUNT(DISTINCT cnpj_fornecedor) as fornecedores_unicos,
                MIN(data_calculo) as primeiro_calculo,
                MAX(data_calculo) as ultimo_calculo,
                COUNT(CASE WHEN ajuste_manual IS NOT NULL THEN 1 END) as com_ajuste_manual
            FROM demanda_pre_calculada
        """)

    row = cursor.fetchone()
    cursor.close()

    return dict(row) if row else {}


def registrar_ajuste_manual(
    conn,
    cod_produto: str,
    cnpj_fornecedor: str,
    ano: int,
    mes: int,
    valor_ajuste: float,
    usuario: str,
    motivo: str = None,
    cod_empresa: int = None
) -> int:
    """
    Registra um ajuste manual de demanda.

    O ajuste manual sobrepoe o valor calculado automaticamente.

    Args:
        conn: Conexao com o banco de dados
        cod_produto: Codigo do produto
        cnpj_fornecedor: CNPJ do fornecedor
        ano: Ano do periodo
        mes: Mes do periodo
        valor_ajuste: Novo valor de demanda
        usuario: Nome do usuario que fez o ajuste
        motivo: Motivo do ajuste (opcional)
        cod_empresa: Codigo da empresa/loja (NULL = consolidado)

    Returns:
        ID do registro atualizado
    """
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO demanda_pre_calculada (
            cod_produto, cnpj_fornecedor, cod_empresa, ano, mes,
            demanda_prevista, demanda_diaria_base,
            ajuste_manual, ajuste_manual_data, ajuste_manual_usuario, ajuste_manual_motivo
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s,
            %s, NOW(), %s, %s
        )
        ON CONFLICT (cod_produto, cnpj_fornecedor, cod_empresa, ano, mes)
        DO UPDATE SET
            ajuste_manual = %s,
            ajuste_manual_data = NOW(),
            ajuste_manual_usuario = %s,
            ajuste_manual_motivo = %s
        RETURNING id
    """, (
        str(cod_produto), cnpj_fornecedor, cod_empresa, ano, mes,
        valor_ajuste, valor_ajuste / 30.0,
        valor_ajuste, usuario, motivo,
        valor_ajuste, usuario, motivo
    ))

    registro_id = cursor.fetchone()[0]

    # Registrar no historico
    cursor.execute("""
        INSERT INTO demanda_pre_calculada_historico (
            demanda_id, cod_produto, cnpj_fornecedor, cod_empresa, ano, mes,
            demanda_prevista, ajuste_manual, tipo_operacao
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, 'ajuste_manual'
        )
    """, (
        registro_id, str(cod_produto), cnpj_fornecedor, cod_empresa, ano, mes,
        valor_ajuste, valor_ajuste
    ))

    conn.commit()
    return registro_id


def limpar_ajuste_manual(
    conn,
    cod_produto: str,
    cnpj_fornecedor: str,
    ano: int,
    mes: int,
    cod_empresa: int = None
) -> bool:
    """
    Remove um ajuste manual, voltando a usar o valor calculado.

    Args:
        conn: Conexao com o banco de dados
        cod_produto: Codigo do produto
        cnpj_fornecedor: CNPJ do fornecedor
        ano: Ano do periodo
        mes: Mes do periodo
        cod_empresa: Codigo da empresa/loja (NULL = consolidado)

    Returns:
        True se o ajuste foi removido, False se nao existia
    """
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE demanda_pre_calculada
        SET ajuste_manual = NULL,
            ajuste_manual_data = NULL,
            ajuste_manual_usuario = NULL,
            ajuste_manual_motivo = NULL
        WHERE cod_produto = %s
          AND cnpj_fornecedor = %s
          AND ano = %s
          AND mes = %s
          AND (cod_empresa = %s OR (cod_empresa IS NULL AND %s IS NULL))
        RETURNING id
    """, (str(cod_produto), cnpj_fornecedor, ano, mes, cod_empresa, cod_empresa))

    row = cursor.fetchone()
    conn.commit()

    return row is not None
