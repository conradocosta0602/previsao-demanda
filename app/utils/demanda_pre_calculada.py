"""
Utilitario para buscar demanda pre-calculada da tabela demanda_pre_calculada.

Garante que tanto a Tela de Demanda quanto a Tela de Pedido Fornecedor
usem os mesmos valores de demanda, mantendo INTEGRIDADE TOTAL.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from psycopg2.extras import RealDictCursor


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
