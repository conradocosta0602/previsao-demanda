"""
Módulo de Pedido ao Fornecedor Integrado
Integra previsão de demanda V2 com cálculo de cobertura baseado em ABC

Características:
- Usa previsão V2 (Bottom-Up) em tempo real
- Cobertura: Lead Time + Ciclo + Segurança_ABC
- Curva ABC do cadastro de produtos para nível de serviço
- Arredondamento para múltiplo de caixa
- Destino configurável (Lojas ou CD)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from scipy import stats


# ==============================================================================
# CONSTANTES E CONFIGURAÇÕES
# ==============================================================================

# Dias de segurança base por curva ABC
SEGURANCA_BASE_ABC = {
    'A': 2,   # Alto giro - reposição frequente
    'B': 4,   # Médio giro - equilíbrio
    'C': 6    # Baixo giro - maior variabilidade
}


# Nível de serviço por curva ABC
NIVEL_SERVICO_ABC = {
    'A': 0.98,  # 98% - itens de alto giro
    'B': 0.95,  # 95% - itens de médio giro
    'C': 0.90   # 90% - itens de baixo giro
}

# Ciclo de pedido padrão (semanal)
CICLO_PEDIDO_DIAS = 7


# ==============================================================================
# FUNÇÕES DE CÁLCULO
# ==============================================================================

def calcular_cobertura_abc(
    lead_time_dias: int,
    curva_abc: str,
    ciclo_pedido_dias: int = CICLO_PEDIDO_DIAS
) -> Dict:
    """
    Calcula a cobertura necessária usando fórmula baseada em ABC.

    Fórmula:
    Cobertura = Lead_Time + Ciclo_Pedido + Segurança_ABC

    Args:
        lead_time_dias: Tempo de entrega do fornecedor
        curva_abc: Classificação ABC do produto ('A', 'B' ou 'C')
        ciclo_pedido_dias: Frequência de pedidos (padrão: 7 dias)

    Returns:
        Dicionário com detalhes da cobertura
    """
    # Normalizar curva ABC
    curva = curva_abc.upper() if curva_abc else 'B'
    if curva not in SEGURANCA_BASE_ABC:
        curva = 'B'

    # Componentes da cobertura
    seguranca_abc = SEGURANCA_BASE_ABC[curva]

    # Cobertura total
    cobertura_total = lead_time_dias + ciclo_pedido_dias + seguranca_abc

    return {
        'cobertura_total_dias': cobertura_total,
        'lead_time_dias': lead_time_dias,
        'ciclo_pedido_dias': ciclo_pedido_dias,
        'seguranca_abc_dias': seguranca_abc,
        'curva_abc': curva
    }


def calcular_estoque_seguranca(
    desvio_padrao_diario: float,
    lead_time_dias: int,
    curva_abc: str
) -> Dict:
    """
    Calcula estoque de segurança com base na curva ABC.

    Fórmula: ES = Z × σ × √LT
    Onde Z é definido pelo nível de serviço da curva ABC

    Args:
        desvio_padrao_diario: Desvio padrão diário da demanda
        lead_time_dias: Lead time em dias
        curva_abc: Classificação ABC

    Returns:
        Dicionário com estoque de segurança e detalhes
    """
    # Normalizar curva ABC
    curva = curva_abc.upper() if curva_abc else 'B'
    if curva not in NIVEL_SERVICO_ABC:
        curva = 'B'

    # Nível de serviço e Z-score baseado na curva ABC
    nivel_servico = NIVEL_SERVICO_ABC[curva]
    z_score = stats.norm.ppf(nivel_servico)

    # Estoque de segurança: ES = Z × σ × √LT
    estoque_seguranca = z_score * desvio_padrao_diario * np.sqrt(lead_time_dias)

    return {
        'estoque_seguranca': round(max(0, estoque_seguranca), 0),
        'nivel_servico': nivel_servico,
        'z_score': round(z_score, 2),
        'curva_abc': curva
    }


def calcular_quantidade_pedido(
    demanda_periodo: float,
    estoque_disponivel: float,
    estoque_transito: float,
    estoque_seguranca: float,
    multiplo_caixa: int = 1
) -> Dict:
    """
    Calcula a quantidade a pedir considerando estoque atual e múltiplo de caixa.

    Args:
        demanda_periodo: Demanda prevista para o período de cobertura
        estoque_disponivel: Estoque atual disponível
        estoque_transito: Estoque em trânsito
        estoque_seguranca: Estoque de segurança calculado
        multiplo_caixa: Unidades por caixa (para arredondamento)

    Returns:
        Dicionário com quantidade a pedir e detalhes
    """
    # Estoque efetivo
    estoque_efetivo = estoque_disponivel + estoque_transito

    # Necessidade bruta
    necessidade_bruta = demanda_periodo + estoque_seguranca - estoque_efetivo

    # Se não precisa pedir
    if necessidade_bruta <= 0:
        return {
            'quantidade_pedido': 0,
            'numero_caixas': 0,
            'necessidade_bruta': round(necessidade_bruta, 0),
            'estoque_efetivo': round(estoque_efetivo, 0),
            'demanda_periodo': round(demanda_periodo, 0),
            'deve_pedir': False,
            'ajustado_multiplo': False
        }

    # Arredondar para múltiplo de caixa (sempre para cima)
    if multiplo_caixa > 1:
        numero_caixas = int(np.ceil(necessidade_bruta / multiplo_caixa))
        quantidade_pedido = numero_caixas * multiplo_caixa
        ajustado = quantidade_pedido != necessidade_bruta
    else:
        quantidade_pedido = int(np.ceil(necessidade_bruta))
        numero_caixas = quantidade_pedido
        ajustado = False

    return {
        'quantidade_pedido': quantidade_pedido,
        'numero_caixas': numero_caixas,
        'necessidade_bruta': round(necessidade_bruta, 0),
        'estoque_efetivo': round(estoque_efetivo, 0),
        'demanda_periodo': round(demanda_periodo, 0),
        'deve_pedir': True,
        'ajustado_multiplo': ajustado,
        'diferenca_ajuste': quantidade_pedido - int(np.ceil(necessidade_bruta))
    }


def calcular_cobertura_pos_pedido(
    estoque_disponivel: float,
    estoque_transito: float,
    quantidade_pedido: float,
    demanda_media_diaria: float
) -> float:
    """
    Calcula a cobertura em dias após receber o pedido.

    Args:
        estoque_disponivel: Estoque atual
        estoque_transito: Estoque em trânsito
        quantidade_pedido: Quantidade a ser pedida
        demanda_media_diaria: Demanda média diária

    Returns:
        Dias de cobertura
    """
    if demanda_media_diaria <= 0:
        return 999  # Cobertura "infinita"

    estoque_total = estoque_disponivel + estoque_transito + quantidade_pedido
    return round(estoque_total / demanda_media_diaria, 1)


# ==============================================================================
# CLASSE PRINCIPAL
# ==============================================================================

class PedidoFornecedorIntegrado:
    """
    Processador de pedidos ao fornecedor integrado com previsão V2.
    """

    def __init__(self, conn):
        """
        Args:
            conn: Conexão com o banco PostgreSQL
        """
        self.conn = conn

    def buscar_dados_produto(self, codigo: int) -> Optional[Dict]:
        """
        Busca dados do produto no cadastro.

        Args:
            codigo: Código do produto

        Returns:
            Dicionário com dados do produto ou None
        """
        query = """
            SELECT
                p.codigo,
                p.descricao,
                p.categoria,
                p.subcategoria,
                p.curva_abc,
                p.und_venda,
                f.codigo_fornecedor,
                f.nome_fornecedor,
                f.lead_time_dias,
                f.pedido_minimo
            FROM cadastro_produtos p
            LEFT JOIN cadastro_fornecedores f ON p.id_fornecedor = f.id_fornecedor
            WHERE p.codigo = %s AND p.ativo = TRUE
        """

        df = pd.read_sql(query, self.conn, params=[codigo])

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    def buscar_estoque_atual(self, codigo: int, cod_empresa: int) -> Dict:
        """
        Busca estoque atual e em trânsito.

        Args:
            codigo: Código do produto
            cod_empresa: Código da empresa/loja

        Returns:
            Dicionário com estoque disponível e em trânsito
        """
        # Estoque disponível
        query_estoque = """
            SELECT COALESCE(SUM(qtd_disponivel), 0) as estoque_disponivel
            FROM estoque_atual
            WHERE codigo = %s AND cod_empresa = %s
        """

        df_estoque = pd.read_sql(query_estoque, self.conn, params=[codigo, cod_empresa])
        estoque_disponivel = float(df_estoque.iloc[0]['estoque_disponivel']) if not df_estoque.empty else 0

        # Estoque em trânsito
        query_transito = """
            SELECT COALESCE(SUM(qtd_transito), 0) as estoque_transito
            FROM transito_atual
            WHERE codigo = %s AND destino = %s::text
        """

        df_transito = pd.read_sql(query_transito, self.conn, params=[codigo, str(cod_empresa)])
        estoque_transito = float(df_transito.iloc[0]['estoque_transito']) if not df_transito.empty else 0

        return {
            'estoque_disponivel': estoque_disponivel,
            'estoque_transito': estoque_transito,
            'estoque_efetivo': estoque_disponivel + estoque_transito
        }

    def buscar_parametros_gondola(self, codigo: int, cod_empresa: int) -> Dict:
        """
        Busca parâmetros de gôndola (múltiplo, lote mínimo).

        Args:
            codigo: Código do produto
            cod_empresa: Código da empresa

        Returns:
            Dicionário com parâmetros
        """
        query = """
            SELECT
                COALESCE(multiplo, 1) as multiplo_caixa,
                COALESCE(lote_minimo, 1) as lote_minimo,
                COALESCE(estoque_seguranca, 0) as estoque_seguranca_gondola
            FROM parametros_gondola
            WHERE codigo = %s AND cod_empresa = %s
        """

        df = pd.read_sql(query, self.conn, params=[codigo, cod_empresa])

        if df.empty:
            return {
                'multiplo_caixa': 1,
                'lote_minimo': 1,
                'estoque_seguranca_gondola': 0
            }

        return df.iloc[0].to_dict()

    def buscar_preco_custo(self, codigo: int, cod_empresa: int) -> float:
        """
        Busca preço de custo do produto.

        Args:
            codigo: Código do produto
            cod_empresa: Código da empresa

        Returns:
            Preço de custo
        """
        query = """
            SELECT preco_custo
            FROM precos_vigentes
            WHERE codigo = %s
              AND cod_empresa = %s
              AND data_inicio <= CURRENT_DATE
              AND (data_fim IS NULL OR data_fim >= CURRENT_DATE)
            ORDER BY data_inicio DESC
            LIMIT 1
        """

        df = pd.read_sql(query, self.conn, params=[codigo, cod_empresa])

        if df.empty or pd.isna(df.iloc[0]['preco_custo']):
            return 0.0

        return float(df.iloc[0]['preco_custo'])

    def processar_item(
        self,
        codigo: int,
        cod_empresa: int,
        previsao_diaria: float,
        desvio_padrao: float,
        cobertura_dias: Optional[int] = None
    ) -> Dict:
        """
        Processa um item individual calculando necessidade de pedido.

        Args:
            codigo: Código do produto
            cod_empresa: Código da empresa/loja
            previsao_diaria: Demanda média diária prevista (da previsão V2)
            desvio_padrao: Desvio padrão da demanda
            cobertura_dias: Cobertura em dias (se None, calcula automaticamente)

        Returns:
            Dicionário com análise completa do item
        """
        # 1. Buscar dados do produto
        produto = self.buscar_dados_produto(codigo)
        if not produto:
            return {'erro': f'Produto {codigo} não encontrado'}

        # 2. Buscar estoque atual
        estoque = self.buscar_estoque_atual(codigo, cod_empresa)

        # 3. Buscar parâmetros de gôndola
        parametros = self.buscar_parametros_gondola(codigo, cod_empresa)

        # 4. Buscar preço de custo
        preco_custo = self.buscar_preco_custo(codigo, cod_empresa)

        # 5. Dados do fornecedor
        lead_time = produto.get('lead_time_dias') or 15
        curva_abc = produto.get('curva_abc') or 'B'

        # 6. Calcular cobertura baseada em ABC (se não informada)
        if cobertura_dias is None:
            cobertura_info = calcular_cobertura_abc(
                lead_time_dias=lead_time,
                curva_abc=curva_abc
            )
            cobertura_dias = cobertura_info['cobertura_total_dias']
        else:
            cobertura_info = {
                'cobertura_total_dias': cobertura_dias,
                'lead_time_dias': lead_time,
                'ciclo_pedido_dias': CICLO_PEDIDO_DIAS,
                'seguranca_abc_dias': SEGURANCA_BASE_ABC.get(curva_abc.upper(), 4),
                'curva_abc': curva_abc
            }

        # 7. Calcular estoque de segurança
        desvio_diario = desvio_padrao / np.sqrt(30) if desvio_padrao else previsao_diaria * 0.3
        es_info = calcular_estoque_seguranca(
            desvio_padrao_diario=desvio_diario,
            lead_time_dias=lead_time,
            curva_abc=curva_abc
        )

        # 8. Calcular demanda no período de cobertura
        demanda_periodo = previsao_diaria * cobertura_dias

        # 9. Calcular quantidade a pedir
        pedido_info = calcular_quantidade_pedido(
            demanda_periodo=demanda_periodo,
            estoque_disponivel=estoque['estoque_disponivel'],
            estoque_transito=estoque['estoque_transito'],
            estoque_seguranca=es_info['estoque_seguranca'],
            multiplo_caixa=parametros['multiplo_caixa']
        )

        # 10. Calcular coberturas
        cobertura_atual = (
            estoque['estoque_efetivo'] / previsao_diaria
            if previsao_diaria > 0 else 999
        )

        cobertura_pos_pedido = calcular_cobertura_pos_pedido(
            estoque_disponivel=estoque['estoque_disponivel'],
            estoque_transito=estoque['estoque_transito'],
            quantidade_pedido=pedido_info['quantidade_pedido'],
            demanda_media_diaria=previsao_diaria
        )

        # 11. Calcular valor do pedido
        valor_pedido = pedido_info['quantidade_pedido'] * preco_custo

        # 12. Montar resultado
        return {
            # Identificação
            'codigo': codigo,
            'descricao': produto.get('descricao', ''),
            'categoria': produto.get('categoria', ''),
            'cod_empresa': cod_empresa,

            # Fornecedor
            'codigo_fornecedor': produto.get('codigo_fornecedor', ''),
            'nome_fornecedor': produto.get('nome_fornecedor', ''),
            'lead_time_dias': lead_time,

            # Classificação
            'curva_abc': curva_abc,
            'nivel_servico': es_info['nivel_servico'],

            # Demanda
            'demanda_media_diaria': round(previsao_diaria, 2),
            'demanda_periodo': round(demanda_periodo, 0),

            # Estoque
            'estoque_disponivel': round(estoque['estoque_disponivel'], 0),
            'estoque_transito': round(estoque['estoque_transito'], 0),
            'estoque_efetivo': round(estoque['estoque_efetivo'], 0),
            'estoque_seguranca': es_info['estoque_seguranca'],

            # Cobertura
            'cobertura_necessaria_dias': cobertura_dias,
            'cobertura_atual_dias': round(cobertura_atual, 1),
            'cobertura_pos_pedido_dias': cobertura_pos_pedido,
            'detalhes_cobertura': cobertura_info,

            # Pedido
            'quantidade_pedido': pedido_info['quantidade_pedido'],
            'numero_caixas': pedido_info['numero_caixas'],
            'multiplo_caixa': parametros['multiplo_caixa'],
            'deve_pedir': pedido_info['deve_pedir'],
            'ajustado_multiplo': pedido_info['ajustado_multiplo'],

            # Valores
            'preco_custo': round(preco_custo, 2),
            'valor_pedido': round(valor_pedido, 2),

            # Alertas
            'risco_ruptura': cobertura_atual < lead_time,
            'ruptura_iminente': cobertura_atual < 3
        }


def agregar_por_fornecedor(resultados: List[Dict]) -> Dict:
    """
    Agrega resultados por fornecedor.

    Args:
        resultados: Lista de resultados por item

    Returns:
        Dicionário com agregação por fornecedor
    """
    if not resultados:
        return {}

    df = pd.DataFrame(resultados)

    # Filtrar apenas itens que devem ser pedidos
    df_pedidos = df[df['deve_pedir'] == True].copy()

    if df_pedidos.empty:
        return {
            'total_fornecedores': 0,
            'total_itens': 0,
            'valor_total': 0,
            'fornecedores': []
        }

    # Agregar por fornecedor
    agregado = df_pedidos.groupby(['codigo_fornecedor', 'nome_fornecedor']).agg({
        'codigo': 'count',
        'quantidade_pedido': 'sum',
        'numero_caixas': 'sum',
        'valor_pedido': 'sum'
    }).reset_index()

    agregado.columns = [
        'codigo_fornecedor', 'nome_fornecedor',
        'total_itens', 'total_unidades', 'total_caixas', 'valor_total'
    ]

    # Converter para lista de dicionários
    fornecedores = agregado.to_dict('records')

    return {
        'total_fornecedores': len(fornecedores),
        'total_itens': int(df_pedidos['codigo'].count()),
        'valor_total': round(float(df_pedidos['valor_pedido'].sum()), 2),
        'fornecedores': fornecedores
    }
