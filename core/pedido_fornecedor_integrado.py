"""
Módulo de Pedido ao Fornecedor Integrado
Integra previsão de demanda V2 com cálculo de cobertura baseado em ABC

Características:
- Usa previsão V2 (Bottom-Up) em tempo real
- Previsão semanal ISO-8601 para cálculo de demanda no período
- Cobertura: Lead Time + Ciclo + Segurança_ABC
- Curva ABC do cadastro de produtos para nível de serviço
- Arredondamento para múltiplo de caixa
- Destino configurável (Lojas ou CD)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, date
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
# FUNÇÕES AUXILIARES
# ==============================================================================

def sanitizar_float(valor, valor_padrao=0):
    """Sanitiza valor float, substituindo NaN/Inf por valor padrao."""
    if valor is None:
        return valor_padrao
    try:
        if np.isnan(valor) or np.isinf(valor):
            return valor_padrao
        return valor
    except (TypeError, ValueError):
        return valor_padrao


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

    def __init__(self, conn, usar_previsao_semanal: bool = False):
        """
        Args:
            conn: Conexão com o banco PostgreSQL
            usar_previsao_semanal: Se True, usa previsão semanal ISO-8601.
                                   Desativado por padrão para manter consistência
                                   com a demanda exibida na tela (DemandCalculator).
        """
        self.conn = conn
        self.usar_previsao_semanal = usar_previsao_semanal
        # Cache das regras de situação de compra
        self._regras_sit_compra = None
        # Instância de previsão semanal
        self._weekly_forecast = None

    def _get_weekly_forecast(self):
        """Retorna instância de WeeklyForecast (lazy loading)."""
        if self._weekly_forecast is None and self.usar_previsao_semanal:
            from core.weekly_forecast import WeeklyForecast
            self._weekly_forecast = WeeklyForecast(self.conn)
        return self._weekly_forecast

    def carregar_regras_sit_compra(self) -> Dict:
        """
        Carrega as regras de situação de compra do banco.

        Returns:
            Dicionário com código -> regra
        """
        if self._regras_sit_compra is not None:
            return self._regras_sit_compra

        try:
            query = """
                SELECT codigo_situacao, descricao, bloqueia_compra_automatica,
                       permite_compra_manual, cor_alerta, icone
                FROM situacao_compra_regras
                WHERE ativo = TRUE
            """
            df = pd.read_sql(query, self.conn)

            self._regras_sit_compra = {}
            for _, row in df.iterrows():
                self._regras_sit_compra[row['codigo_situacao']] = {
                    'descricao': row['descricao'],
                    'bloqueia_compra_automatica': row['bloqueia_compra_automatica'],
                    'permite_compra_manual': row['permite_compra_manual'],
                    'cor_alerta': row['cor_alerta'],
                    'icone': row['icone']
                }
        except Exception:
            # Se tabela não existe, retorna vazio
            self._regras_sit_compra = {}

        return self._regras_sit_compra

    def verificar_situacao_compra(self, codigo, cod_empresa: int) -> Optional[Dict]:
        """
        Verifica se o item tem alguma situação de compra que bloqueia pedido.

        Args:
            codigo: Código do produto
            cod_empresa: Código da empresa/loja

        Returns:
            None se liberado, ou dicionário com informações do bloqueio
        """
        try:
            codigo_int = int(codigo)
        except (ValueError, TypeError):
            return None

        try:
            query = """
                SELECT sci.sit_compra, scr.descricao, scr.bloqueia_compra_automatica,
                       scr.permite_compra_manual, scr.cor_alerta, scr.icone
                FROM situacao_compra_itens sci
                JOIN situacao_compra_regras scr ON sci.sit_compra = scr.codigo_situacao
                WHERE sci.codigo = %s
                  AND sci.cod_empresa = %s
                  AND scr.bloqueia_compra_automatica = TRUE
                  AND scr.ativo = TRUE
                  AND (sci.data_fim IS NULL OR sci.data_fim >= CURRENT_DATE)
            """
            df = pd.read_sql(query, self.conn, params=[codigo_int, cod_empresa])

            if df.empty:
                return None

            row = df.iloc[0]
            return {
                'sit_compra': row['sit_compra'],
                'descricao': row['descricao'],
                'bloqueia_compra_automatica': row['bloqueia_compra_automatica'],
                'permite_compra_manual': row['permite_compra_manual'],
                'cor_alerta': row['cor_alerta'],
                'icone': row['icone']
            }
        except Exception:
            # Se tabela não existe, não bloqueia
            return None

    def buscar_dados_produto(self, codigo) -> Optional[Dict]:
        """
        Busca dados do produto no cadastro.

        Args:
            codigo: Código do produto (pode ser string ou int)

        Returns:
            Dicionário com dados do produto ou None
        """
        # cod_produto em cadastro_produtos_completo é VARCHAR
        codigo_str = str(codigo)

        query = """
            SELECT
                cod_produto as codigo,
                descricao,
                categoria,
                descricao_linha as subcategoria,
                'B' as curva_abc,
                'UN' as und_venda,
                cnpj_fornecedor as codigo_fornecedor,
                nome_fornecedor,
                15 as lead_time_dias,
                0 as pedido_minimo
            FROM cadastro_produtos_completo
            WHERE cod_produto = %s AND ativo = TRUE
        """

        df = pd.read_sql(query, self.conn, params=[codigo_str])

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    def buscar_estoque_atual(self, codigo, cod_empresa: int) -> Dict:
        """
        Busca estoque atual da tabela estoque_posicao_atual (importada do arquivo).

        Args:
            codigo: Código do produto (pode ser string ou int)
            cod_empresa: Código da empresa/loja

        Returns:
            Dicionário com estoque disponível, em trânsito e pendente
        """
        # Converter codigo para int
        try:
            codigo_int = int(codigo)
        except (ValueError, TypeError):
            return {'estoque_disponivel': 0, 'estoque_transito': 0, 'estoque_efetivo': 0, 'qtd_pendente': 0}

        # Buscar estoque da tabela de posição atual (dados importados)
        query_estoque = """
            SELECT
                COALESCE(estoque, 0) as estoque_disponivel,
                COALESCE(qtd_pendente, 0) as qtd_pendente,
                COALESCE(qtd_pend_transf, 0) as qtd_pend_transf
            FROM estoque_posicao_atual
            WHERE codigo = %s AND cod_empresa = %s
        """

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            df_estoque = pd.read_sql(query_estoque, self.conn, params=[codigo_int, cod_empresa])

        if df_estoque.empty:
            return {'estoque_disponivel': 0, 'estoque_transito': 0, 'estoque_efetivo': 0, 'qtd_pendente': 0}

        row = df_estoque.iloc[0]
        estoque_disponivel = float(row['estoque_disponivel'])
        qtd_pendente = float(row['qtd_pendente'])  # Pedidos pendentes de entrega
        qtd_pend_transf = float(row['qtd_pend_transf'])  # Transferências pendentes

        # Estoque em trânsito = pedidos pendentes + transferências pendentes
        estoque_transito = qtd_pendente + qtd_pend_transf

        return {
            'estoque_disponivel': estoque_disponivel,
            'estoque_transito': estoque_transito,
            'estoque_efetivo': estoque_disponivel + estoque_transito,
            'qtd_pendente': qtd_pendente,
            'qtd_pend_transf': qtd_pend_transf
        }

    def buscar_parametros_gondola(self, codigo, cod_empresa: int) -> Dict:
        """
        Busca parâmetros de gôndola (múltiplo, lote mínimo).

        Args:
            codigo: Código do produto
            cod_empresa: Código da empresa

        Returns:
            Dicionário com parâmetros padrão (tabela parametros_gondola não existe)
        """
        # Retornar valores padrão - tabela parametros_gondola não existe no banco atual
        return {
            'multiplo_caixa': 1,
            'lote_minimo': 1,
            'estoque_seguranca_gondola': 0
        }

    def buscar_preco_custo(self, codigo, cod_empresa: int) -> float:
        """
        Busca preço de custo (CUE) do produto da tabela estoque_posicao_atual.

        Args:
            codigo: Código do produto
            cod_empresa: Código da empresa

        Returns:
            Preço de custo (CUE)
        """
        # Converter codigo para int
        try:
            codigo_int = int(codigo)
        except (ValueError, TypeError):
            return 0.0

        # Buscar CUE da tabela de posição atual
        query = """
            SELECT COALESCE(cue, 0) as cue
            FROM estoque_posicao_atual
            WHERE codigo = %s AND cod_empresa = %s
        """

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            df = pd.read_sql(query, self.conn, params=[codigo_int, cod_empresa])

        if df.empty:
            return 0.0

        return float(df.iloc[0]['cue'])

    def buscar_historico_vendas(self, codigo, cod_empresa: int, dias: int = 365) -> List[float]:
        """
        Busca histórico de vendas diárias para cálculo de demanda.

        Args:
            codigo: Código do produto (pode ser string ou int)
            cod_empresa: Código da empresa/loja
            dias: Número de dias de histórico

        Returns:
            Lista com quantidades vendidas por dia
        """
        from datetime import datetime, timedelta

        data_fim = datetime.now().date()
        data_inicio = data_fim - timedelta(days=dias)

        # Converter codigo para int (historico_vendas_diario usa INTEGER)
        try:
            codigo_int = int(codigo)
        except (ValueError, TypeError):
            return []

        query = """
            SELECT data, COALESCE(SUM(qtd_venda), 0) as qtd_venda
            FROM historico_vendas_diario
            WHERE codigo = %s
              AND cod_empresa = %s
              AND data >= %s
              AND data <= %s
            GROUP BY data
            ORDER BY data
        """

        df = pd.read_sql(query, self.conn, params=[codigo_int, cod_empresa, data_inicio, data_fim])

        if df.empty:
            return []

        return [float(x) for x in df['qtd_venda'].tolist()]

    def processar_item(
        self,
        codigo: int,
        cod_empresa: int,
        previsao_diaria: float,
        desvio_padrao: float,
        cobertura_dias: Optional[int] = None,
        usar_previsao_semanal_item: bool = True,
        lead_time_dias: Optional[int] = None,
        ciclo_pedido_dias: Optional[int] = None,
        pedido_minimo_valor: Optional[float] = None
    ) -> Dict:
        """
        Processa um item individual calculando necessidade de pedido.

        Args:
            codigo: Código do produto
            cod_empresa: Código da empresa/loja
            previsao_diaria: Demanda média diária prevista (da previsão V2)
            desvio_padrao: Desvio padrão da demanda
            cobertura_dias: Cobertura em dias (se None, calcula automaticamente)
            usar_previsao_semanal_item: Se True, usa previsão semanal para este item.
                                        Se False, usa previsao_diaria * cobertura_dias
                                        (útil quando demanda já foi calculada externamente)
            lead_time_dias: Lead time do fornecedor (se None, busca do cadastro ou usa 15)
            ciclo_pedido_dias: Ciclo de pedido do fornecedor (se None, usa padrão)
            pedido_minimo_valor: Valor mínimo do pedido (para validação posterior)

        Returns:
            Dicionário com análise completa do item
        """
        # 0. Verificar situação de compra (antes de qualquer processamento)
        bloqueio = self.verificar_situacao_compra(codigo, cod_empresa)
        if bloqueio:
            # Item bloqueado - retorna informações mínimas
            produto = self.buscar_dados_produto(codigo)
            return {
                'codigo': codigo,
                'descricao': produto.get('descricao', '') if produto else f'Produto {codigo}',
                'categoria': produto.get('categoria', '') if produto else '',
                'cod_empresa': cod_empresa,
                'bloqueado': True,
                'sit_compra': bloqueio['sit_compra'],
                'motivo_bloqueio': bloqueio['descricao'],
                'permite_compra_manual': bloqueio['permite_compra_manual'],
                'cor_alerta': bloqueio['cor_alerta'],
                'icone_bloqueio': bloqueio['icone'],
                'quantidade_pedido': 0,
                'deve_pedir': False,
                'codigo_fornecedor': produto.get('codigo_fornecedor', '') if produto else '',
                'nome_fornecedor': produto.get('nome_fornecedor', '') if produto else ''
            }

        # 1. Buscar dados do produto
        produto = self.buscar_dados_produto(codigo)
        if not produto:
            return {'erro': f'Produto {codigo} não encontrado'}

        # 1.5 Validar previsao_diaria
        if previsao_diaria is None or np.isnan(previsao_diaria) or np.isinf(previsao_diaria):
            previsao_diaria = 0.01  # Valor minimo para evitar divisao por zero

        # 2. Buscar estoque atual
        estoque = self.buscar_estoque_atual(codigo, cod_empresa)

        # 3. Buscar parâmetros de gôndola
        parametros = self.buscar_parametros_gondola(codigo, cod_empresa)

        # 4. Buscar preço de custo
        preco_custo = self.buscar_preco_custo(codigo, cod_empresa)

        # 5. Dados do fornecedor (usar parametro se fornecido, senao buscar do produto ou usar padrao)
        lead_time = lead_time_dias if lead_time_dias is not None else (produto.get('lead_time_dias') or 15)
        ciclo_pedido = ciclo_pedido_dias if ciclo_pedido_dias is not None else CICLO_PEDIDO_DIAS
        curva_abc = produto.get('curva_abc') or 'B'

        # 6. Calcular cobertura baseada em ABC (se não informada)
        if cobertura_dias is None:
            cobertura_info = calcular_cobertura_abc(
                lead_time_dias=lead_time,
                curva_abc=curva_abc,
                ciclo_pedido_dias=ciclo_pedido
            )
            cobertura_dias = cobertura_info['cobertura_total_dias']
        else:
            cobertura_info = {
                'cobertura_total_dias': cobertura_dias,
                'lead_time_dias': lead_time,
                'ciclo_pedido_dias': ciclo_pedido,
                'seguranca_abc_dias': SEGURANCA_BASE_ABC.get(curva_abc.upper(), 4),
                'curva_abc': curva_abc
            }

        # 7. Calcular estoque de segurança
        # Garantir que desvio_padrao nao seja NaN
        if desvio_padrao is None or np.isnan(desvio_padrao) or np.isinf(desvio_padrao):
            desvio_padrao = previsao_diaria * 0.3 if previsao_diaria > 0 else 0.1
        desvio_diario = desvio_padrao / np.sqrt(30) if desvio_padrao > 0 else previsao_diaria * 0.3
        # Garantir que desvio_diario nao seja NaN
        if np.isnan(desvio_diario) or np.isinf(desvio_diario):
            desvio_diario = 0.1
        es_info = calcular_estoque_seguranca(
            desvio_padrao_diario=desvio_diario,
            lead_time_dias=lead_time,
            curva_abc=curva_abc
        )

        # 8. Calcular demanda no período de cobertura
        # Usa previsão semanal ISO-8601 se habilitado E se o item permitir
        # (para CDs com demanda agregada de múltiplas lojas, usar_previsao_semanal_item=False)
        previsao_semanal_info = None
        if self.usar_previsao_semanal and usar_previsao_semanal_item:
            weekly_forecast = self._get_weekly_forecast()
            if weekly_forecast:
                try:
                    previsao_semanal_info = weekly_forecast.calcular_demanda_periodo_cobertura(
                        codigo=codigo,
                        cod_empresa=cod_empresa,
                        lead_time_dias=lead_time,
                        cobertura_dias=cobertura_dias,
                        demanda_media_diaria=previsao_diaria
                    )
                    demanda_periodo = previsao_semanal_info['demanda_total']
                    # Atualizar desvio se disponível
                    if previsao_semanal_info.get('desvio_padrao_total', 0) > 0:
                        desvio_diario = previsao_semanal_info['desvio_padrao_total'] / cobertura_dias
                except Exception:
                    # Fallback para cálculo tradicional
                    demanda_periodo = previsao_diaria * cobertura_dias
                    previsao_semanal_info = None
            else:
                demanda_periodo = previsao_diaria * cobertura_dias
        else:
            # Usar demanda diária fornecida (já calculada externamente, ex: soma de lojas)
            demanda_periodo = previsao_diaria * cobertura_dias

        # 9. Calcular quantidade a pedir
        pedido_info = calcular_quantidade_pedido(
            demanda_periodo=demanda_periodo,
            estoque_disponivel=estoque['estoque_disponivel'],
            estoque_transito=estoque['estoque_transito'],
            estoque_seguranca=es_info['estoque_seguranca'],
            multiplo_caixa=parametros['multiplo_caixa']
        )

        # 10. Calcular valor do pedido (antes de calcular coberturas para usar CUE)
        valor_pedido = pedido_info['quantidade_pedido'] * preco_custo

        # Calcular demanda média diária a partir da previsão do período
        # (usa a demanda do período dividida pelo número de dias)
        demanda_prevista_diaria = demanda_periodo / cobertura_dias if cobertura_dias > 0 else previsao_diaria

        # Garantir que demanda_prevista_diaria não seja NaN ou infinito
        if np.isnan(demanda_prevista_diaria) or np.isinf(demanda_prevista_diaria):
            demanda_prevista_diaria = previsao_diaria if previsao_diaria > 0 else 0.01

        # 11. Calcular coberturas com base na demanda prevista diária
        cobertura_atual = (
            estoque['estoque_efetivo'] / demanda_prevista_diaria
            if demanda_prevista_diaria > 0 else 999
        )

        # Garantir que cobertura não seja NaN ou infinito
        if np.isnan(cobertura_atual) or np.isinf(cobertura_atual):
            cobertura_atual = 999

        cobertura_pos_pedido = calcular_cobertura_pos_pedido(
            estoque_disponivel=estoque['estoque_disponivel'],
            estoque_transito=estoque['estoque_transito'],
            quantidade_pedido=pedido_info['quantidade_pedido'],
            demanda_media_diaria=demanda_prevista_diaria
        )

        # Garantir que cobertura_pos_pedido não seja NaN ou infinito
        if np.isnan(cobertura_pos_pedido) or np.isinf(cobertura_pos_pedido):
            cobertura_pos_pedido = 999

        # 12. Montar resultado
        resultado = {
            # Identificação
            'codigo': codigo,
            'descricao': produto.get('descricao', ''),
            'categoria': produto.get('categoria', ''),
            'cod_empresa': cod_empresa,

            # Situação de compra (não bloqueado)
            'bloqueado': False,
            'sit_compra': None,
            'motivo_bloqueio': None,

            # Fornecedor
            'codigo_fornecedor': produto.get('codigo_fornecedor', ''),
            'nome_fornecedor': produto.get('nome_fornecedor', ''),
            'lead_time_dias': lead_time,

            # Classificação
            'curva_abc': curva_abc,
            'nivel_servico': es_info['nivel_servico'],

            # Demanda Prevista (do período de cobertura) - sanitizar valores
            'demanda_prevista': round(sanitizar_float(demanda_periodo, 0), 0),
            'demanda_prevista_diaria': round(sanitizar_float(demanda_prevista_diaria, 0.01), 2),

            # Estoque Atual (da posição de estoque importada)
            'estoque_atual': round(sanitizar_float(estoque['estoque_disponivel'], 0), 0),
            'estoque_transito': round(sanitizar_float(estoque['estoque_transito'], 0), 0),
            'estoque_efetivo': round(sanitizar_float(estoque['estoque_efetivo'], 0), 0),
            'estoque_seguranca': sanitizar_float(es_info['estoque_seguranca'], 0),

            # Cobertura (sempre em DIAS para interface) - sanitizar valores
            'cobertura_atual_dias': round(sanitizar_float(cobertura_atual, 999), 1),
            'cobertura_necessaria_dias': sanitizar_float(cobertura_dias, 30),
            'cobertura_pos_pedido_dias': round(sanitizar_float(cobertura_pos_pedido, 999), 1),
            'detalhes_cobertura': cobertura_info,

            # Pedido
            'quantidade_pedido': sanitizar_float(pedido_info['quantidade_pedido'], 0),
            'numero_caixas': sanitizar_float(pedido_info['numero_caixas'], 0),
            'multiplo_caixa': sanitizar_float(parametros['multiplo_caixa'], 1),
            'deve_pedir': pedido_info['deve_pedir'],
            'ajustado_multiplo': pedido_info['ajustado_multiplo'],

            # Valores (usando CUE importado) - sanitizar valores
            'preco_custo': round(sanitizar_float(preco_custo, 0), 2),
            'cue': round(sanitizar_float(preco_custo, 0), 2),  # Alias para compatibilidade com transferencias
            'valor_pedido': round(sanitizar_float(valor_pedido, 0), 2),

            # Alertas - usar valor sanitizado para comparacao
            'risco_ruptura': sanitizar_float(cobertura_atual, 999) < lead_time,
            'ruptura_iminente': sanitizar_float(cobertura_atual, 999) < 3
        }

        # Adicionar informações da previsão semanal (se usada)
        if previsao_semanal_info is not None:
            resultado['previsao_semanal'] = {
                'usado': True,
                'numero_semanas': previsao_semanal_info.get('numero_semanas', 0),
                'semana_atual': previsao_semanal_info.get('detalhes', {}).get('semana_atual', ''),
                'semana_entrega': previsao_semanal_info.get('detalhes', {}).get('semana_entrega', ''),
                'semanas_cobertura': previsao_semanal_info.get('semanas_cobertura', []),
                'metodo': 'previsao_semanal_iso8601'
            }
        else:
            resultado['previsao_semanal'] = {
                'usado': False,
                'metodo': 'demanda_diaria_simples'
            }

        return resultado


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

    # Contar itens bloqueados
    itens_bloqueados = []
    if 'bloqueado' in df.columns:
        df_bloqueados = df[df['bloqueado'] == True].copy()
        if not df_bloqueados.empty:
            # Agrupar bloqueados por situação
            bloqueados_por_sit = df_bloqueados.groupby('sit_compra').agg({
                'codigo': 'count',
                'motivo_bloqueio': 'first'
            }).reset_index()
            bloqueados_por_sit.columns = ['sit_compra', 'quantidade', 'descricao']
            itens_bloqueados = bloqueados_por_sit.to_dict('records')

    # Filtrar apenas itens que devem ser pedidos (não bloqueados)
    df_pedidos = df[(df['deve_pedir'] == True) & (df.get('bloqueado', False) != True)].copy()

    if df_pedidos.empty:
        return {
            'total_fornecedores': 0,
            'total_itens': 0,
            'total_itens_bloqueados': len(df[df.get('bloqueado', False) == True]) if 'bloqueado' in df.columns else 0,
            'itens_bloqueados_por_situacao': itens_bloqueados,
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
        'total_itens_bloqueados': len(df[df['bloqueado'] == True]) if 'bloqueado' in df.columns else 0,
        'itens_bloqueados_por_situacao': itens_bloqueados,
        'valor_total': round(float(df_pedidos['valor_pedido'].sum()), 2),
        'fornecedores': fornecedores
    }
