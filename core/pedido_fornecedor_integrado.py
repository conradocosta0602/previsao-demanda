"""
Módulo de Pedido ao Fornecedor Integrado
Integra previsão de demanda V2 com cálculo de cobertura baseado em ABC

Características:
- Usa previsão V2 (Bottom-Up) em tempo real
- Histórico de 2 anos (730 dias) para capturar sazonalidade completa
- Saneamento de rupturas: zeros de falta de estoque são substituídos por estimativas
- Demanda do período: Demanda_Diária × Cobertura (consistente com tela de demanda)
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

    def __init__(self, conn):
        """
        Args:
            conn: Conexão com o banco PostgreSQL
        """
        self.conn = conn
        # Cache das regras de situação de compra
        self._regras_sit_compra = None
        # Cache de situações de compra dos itens (codigo, cod_empresa) -> sit_compra
        self._cache_sit_compra_itens = None
        # Cache de estoque posição atual: (codigo, cod_empresa) -> dict
        self._cache_estoque = None
        # Cache de histórico de vendas agregado: (codigo, tuple(lojas)) -> list
        self._cache_historico = None
        # Cache de dados de produtos: codigo -> dict
        self._cache_produtos = None
        # Cache de embalagem de arredondamento: codigo -> qtd_embalagem
        self._cache_embalagem = None

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

    def precarregar_situacoes_compra(self, codigos: List[int], cod_empresas: List[int]) -> None:
        """
        Pré-carrega todas as situações de compra em lote para otimizar performance.

        Args:
            codigos: Lista de códigos de produtos
            cod_empresas: Lista de códigos de empresas/lojas
        """
        if not codigos or not cod_empresas:
            self._cache_sit_compra_itens = {}
            return

        try:
            # Carregar regras primeiro
            self.carregar_regras_sit_compra()

            # Buscar todas as situações de compra de uma vez
            placeholders_cod = ','.join(['%s'] * len(codigos))
            placeholders_emp = ','.join(['%s'] * len(cod_empresas))

            query = f"""
                SELECT sci.codigo, sci.cod_empresa, sci.sit_compra
                FROM situacao_compra_itens sci
                JOIN situacao_compra_regras scr ON sci.sit_compra = scr.codigo_situacao
                WHERE sci.codigo IN ({placeholders_cod})
                  AND sci.cod_empresa IN ({placeholders_emp})
                  AND scr.bloqueia_compra_automatica = TRUE
                  AND scr.ativo = TRUE
                  AND (sci.data_fim IS NULL OR sci.data_fim >= CURRENT_DATE)
            """
            params = list(codigos) + list(cod_empresas)
            df = pd.read_sql(query, self.conn, params=params)

            # Montar cache
            self._cache_sit_compra_itens = {}
            for _, row in df.iterrows():
                key = (int(row['codigo']), int(row['cod_empresa']))
                self._cache_sit_compra_itens[key] = row['sit_compra']

        except Exception:
            self._cache_sit_compra_itens = {}

    def precarregar_estoque(self, codigos: List[int], cod_empresas: List[int]) -> None:
        """
        Pré-carrega estoque de todos os produtos/lojas em lote para otimizar performance.

        Args:
            codigos: Lista de códigos de produtos
            cod_empresas: Lista de códigos de empresas/lojas
        """
        if not codigos or not cod_empresas:
            self._cache_estoque = {}
            return

        try:
            placeholders_cod = ','.join(['%s'] * len(codigos))
            placeholders_emp = ','.join(['%s'] * len(cod_empresas))

            query = f"""
                SELECT
                    codigo, cod_empresa,
                    COALESCE(estoque, 0) as estoque_disponivel,
                    COALESCE(qtd_pendente, 0) as qtd_pendente,
                    COALESCE(qtd_pend_transf, 0) as qtd_pend_transf,
                    COALESCE(cue, 0) as cue
                FROM estoque_posicao_atual
                WHERE codigo IN ({placeholders_cod})
                  AND cod_empresa IN ({placeholders_emp})
            """
            params = list(codigos) + list(cod_empresas)

            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                df = pd.read_sql(query, self.conn, params=params)

            # Montar cache
            self._cache_estoque = {}
            for _, row in df.iterrows():
                key = (int(row['codigo']), int(row['cod_empresa']))
                estoque_disp = float(row['estoque_disponivel'])
                qtd_pendente = float(row['qtd_pendente'])
                qtd_pend_transf = float(row['qtd_pend_transf'])
                estoque_transito = qtd_pendente + qtd_pend_transf

                self._cache_estoque[key] = {
                    'estoque_disponivel': estoque_disp,
                    'estoque_transito': estoque_transito,
                    'estoque_efetivo': estoque_disp + estoque_transito,
                    'qtd_pendente': qtd_pendente,
                    'qtd_pend_transf': qtd_pend_transf,
                    'cue': float(row['cue'])
                }

            print(f"  [CACHE] Estoque pré-carregado: {len(self._cache_estoque)} registros")

        except Exception as e:
            print(f"  [CACHE] Erro ao pré-carregar estoque: {e}")
            self._cache_estoque = {}

    def precarregar_historico_vendas(self, codigos: List[int], cod_empresas: List[int], dias: int = 730) -> None:
        """
        Pré-carrega histórico de vendas de todos os produtos/lojas em lote.

        Args:
            codigos: Lista de códigos de produtos
            cod_empresas: Lista de códigos de empresas/lojas
            dias: Número de dias de histórico (padrão: 730 = 2 anos)
        """
        if not codigos or not cod_empresas:
            self._cache_historico = {}
            return

        try:
            from datetime import datetime, timedelta

            data_fim = datetime.now().date()
            data_inicio = data_fim - timedelta(days=dias)

            placeholders_cod = ','.join(['%s'] * len(codigos))
            placeholders_emp = ','.join(['%s'] * len(cod_empresas))

            # Query agregada: soma vendas por produto/loja/data
            query = f"""
                SELECT
                    codigo,
                    cod_empresa,
                    data,
                    COALESCE(SUM(qtd_venda), 0) as qtd_venda
                FROM historico_vendas_diario
                WHERE codigo IN ({placeholders_cod})
                  AND cod_empresa IN ({placeholders_emp})
                  AND data >= %s
                  AND data <= %s
                GROUP BY codigo, cod_empresa, data
                ORDER BY codigo, cod_empresa, data
            """
            params = list(codigos) + list(cod_empresas) + [data_inicio, data_fim]

            df = pd.read_sql(query, self.conn, params=params)

            # Montar cache por (codigo, loja) -> lista de vendas ordenada por data
            self._cache_historico = {}
            if not df.empty:
                for (codigo, cod_empresa), group in df.groupby(['codigo', 'cod_empresa']):
                    key = (int(codigo), int(cod_empresa))
                    vendas = group.sort_values('data')['qtd_venda'].tolist()
                    self._cache_historico[key] = [float(v) for v in vendas]

            print(f"  [CACHE] Histórico pré-carregado: {len(self._cache_historico)} combinações produto/loja")

        except Exception as e:
            print(f"  [CACHE] Erro ao pré-carregar histórico: {e}")
            self._cache_historico = {}

    def precarregar_embalagens(self, codigos: List[int]) -> None:
        """
        Pré-carrega dados de embalagem de arredondamento de todos os produtos em lote.

        Args:
            codigos: Lista de códigos de produtos
        """
        if not codigos:
            self._cache_embalagem = {}
            return

        try:
            placeholders = ','.join(['%s'] * len(codigos))

            query = f"""
                SELECT codigo, qtd_embalagem, unidade_compra, unidade_menor
                FROM embalagem_arredondamento
                WHERE codigo IN ({placeholders})
            """

            df = pd.read_sql(query, self.conn, params=list(codigos))

            # Montar cache: codigo -> dict com qtd_embalagem e unidades
            self._cache_embalagem = {}
            for _, row in df.iterrows():
                codigo = int(row['codigo'])
                qtd_embalagem = float(row['qtd_embalagem']) if row['qtd_embalagem'] else 1
                # Garantir que qtd_embalagem seja pelo menos 1
                if qtd_embalagem < 1:
                    qtd_embalagem = 1
                self._cache_embalagem[codigo] = {
                    'qtd_embalagem': int(qtd_embalagem),
                    'unidade_compra': row.get('unidade_compra', ''),
                    'unidade_menor': row.get('unidade_menor', '')
                }

            print(f"  [CACHE] Embalagem pré-carregada: {len(self._cache_embalagem)} produtos")

        except Exception as e:
            print(f"  [CACHE] Erro ao pré-carregar embalagem (tabela pode não existir): {e}")
            self._cache_embalagem = {}

    def buscar_embalagem(self, codigo) -> Dict:
        """
        Busca dados de embalagem de arredondamento do produto.

        Args:
            codigo: Código do produto

        Returns:
            Dicionário com qtd_embalagem, unidade_compra, unidade_menor
        """
        default_result = {'qtd_embalagem': 1, 'unidade_compra': '', 'unidade_menor': ''}

        try:
            codigo_int = int(codigo)
        except (ValueError, TypeError):
            return default_result

        # Usar cache se disponível
        if self._cache_embalagem is not None:
            cached = self._cache_embalagem.get(codigo_int)
            if cached:
                return cached
            return default_result

        # Fallback: query individual (mais lento)
        try:
            query = """
                SELECT qtd_embalagem, unidade_compra, unidade_menor
                FROM embalagem_arredondamento
                WHERE codigo = %s
            """
            df = pd.read_sql(query, self.conn, params=[codigo_int])

            if df.empty:
                return default_result

            row = df.iloc[0]
            qtd_embalagem = float(row['qtd_embalagem']) if row['qtd_embalagem'] else 1
            if qtd_embalagem < 1:
                qtd_embalagem = 1

            return {
                'qtd_embalagem': int(qtd_embalagem),
                'unidade_compra': row.get('unidade_compra', ''),
                'unidade_menor': row.get('unidade_menor', '')
            }
        except Exception:
            return default_result

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

        # Usar cache se disponível (muito mais rápido)
        if self._cache_sit_compra_itens is not None:
            key = (codigo_int, int(cod_empresa))
            sit_compra = self._cache_sit_compra_itens.get(key)
            if sit_compra is None:
                return None  # Não bloqueado

            # Buscar detalhes da regra do cache de regras
            regras = self.carregar_regras_sit_compra()
            regra = regras.get(sit_compra, {})
            return {
                'sit_compra': sit_compra,
                'descricao': regra.get('descricao', sit_compra),
                'bloqueia_compra_automatica': regra.get('bloqueia_compra_automatica', True),
                'permite_compra_manual': regra.get('permite_compra_manual', False),
                'cor_alerta': regra.get('cor_alerta', '#ffc107'),
                'icone': regra.get('icone', '⚠️')
            }

        # Fallback: query individual (mais lento)
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
        default_result = {'estoque_disponivel': 0, 'estoque_transito': 0, 'estoque_efetivo': 0, 'qtd_pendente': 0, 'qtd_pend_transf': 0}

        # Converter codigo para int
        try:
            codigo_int = int(codigo)
        except (ValueError, TypeError):
            return default_result

        # Usar cache se disponível (muito mais rápido)
        if self._cache_estoque is not None:
            key = (codigo_int, int(cod_empresa))
            cached = self._cache_estoque.get(key)
            if cached:
                return cached
            return default_result

        # Fallback: query individual (mais lento)
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
            return default_result

        row = df_estoque.iloc[0]
        estoque_disponivel = float(row['estoque_disponivel'])
        qtd_pendente = float(row['qtd_pendente'])
        qtd_pend_transf = float(row['qtd_pend_transf'])
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

        # Usar cache de estoque se disponível (CUE é carregado junto)
        if self._cache_estoque is not None:
            key = (codigo_int, int(cod_empresa))
            cached = self._cache_estoque.get(key)
            if cached:
                return cached.get('cue', 0.0)
            return 0.0

        # Fallback: query individual (mais lento)
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

    def buscar_historico_vendas(
        self,
        codigo,
        cod_empresa: int,
        dias: int = 730,
        sanear_rupturas: bool = True
    ) -> List[float]:
        """
        Busca histórico de vendas diárias para cálculo de demanda.

        IMPORTANTE: Usa 730 dias (2 anos) por padrão para capturar ciclos
        sazonais completos, mantendo consistência com a tela de demanda.

        Args:
            codigo: Código do produto (pode ser string ou int)
            cod_empresa: Código da empresa/loja
            dias: Número de dias de histórico (padrão: 730 = 2 anos)
            sanear_rupturas: Se True, substitui zeros de ruptura por valores estimados

        Returns:
            Lista com quantidades vendidas por dia (saneadas se aplicável)
        """
        from datetime import datetime, timedelta

        # Converter codigo para int (historico_vendas_diario usa INTEGER)
        try:
            codigo_int = int(codigo)
        except (ValueError, TypeError):
            return []

        # Usar cache se disponível (muito mais rápido)
        # Nota: cache não inclui saneamento de rupturas, mas é aceitável para performance
        if self._cache_historico is not None:
            key = (codigo_int, int(cod_empresa))
            cached = self._cache_historico.get(key)
            if cached:
                return cached
            return []

        # Fallback: query individual (mais lento)
        data_fim = datetime.now().date()
        data_inicio = data_fim - timedelta(days=dias)

        if sanear_rupturas:
            query = """
                SELECT
                    h.data,
                    COALESCE(SUM(h.qtd_venda), 0) as qtd_venda,
                    COALESCE(AVG(e.estoque_diario), -1) as estoque
                FROM historico_vendas_diario h
                LEFT JOIN historico_estoque_diario e
                    ON h.data = e.data
                    AND h.codigo = e.codigo
                    AND h.cod_empresa = e.cod_empresa
                WHERE h.codigo = %s
                  AND h.cod_empresa = %s
                  AND h.data >= %s
                  AND h.data <= %s
                GROUP BY h.data
                ORDER BY h.data
            """
        else:
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

        # Aplicar saneamento de rupturas se habilitado e se temos dados de estoque
        if sanear_rupturas and 'estoque' in df.columns:
            df = self._sanear_rupturas_historico(df, codigo_int, cod_empresa)
            return [float(x) for x in df['qtd_venda_saneada'].tolist()]

        return [float(x) for x in df['qtd_venda'].tolist()]

    def _sanear_rupturas_historico(
        self,
        df: pd.DataFrame,
        codigo: int,
        cod_empresa: int
    ) -> pd.DataFrame:
        """
        Aplica saneamento de rupturas no histórico de vendas.

        Ruptura = venda zero E estoque zero (falta de produto, não demanda real zero)

        Substitui zeros de ruptura por valores estimados usando:
        1. Mesmo dia da semana do ano anterior
        2. Média dos dias adjacentes
        3. Mediana do período

        Args:
            df: DataFrame com colunas data, qtd_venda, estoque
            codigo: Código do produto
            cod_empresa: Código da empresa

        Returns:
            DataFrame com coluna qtd_venda_saneada
        """
        df = df.copy()
        df['qtd_venda_saneada'] = df['qtd_venda'].copy()

        # Identificar rupturas: venda = 0 E estoque = 0 (ou estoque disponível)
        # estoque = -1 significa sem informação de estoque
        mask_ruptura = (df['qtd_venda'] == 0) & (df['estoque'] == 0)

        if not mask_ruptura.any():
            return df

        # Para cada ruptura, estimar valor
        for idx in df[mask_ruptura].index:
            data_ruptura = df.loc[idx, 'data']

            # 1. Tentar mesmo dia da semana do ano anterior (364 dias)
            data_ano_anterior = data_ruptura - timedelta(days=364)
            mask_ano_ant = (
                (df['data'] == data_ano_anterior) &
                (df['qtd_venda'] > 0)
            )
            if mask_ano_ant.any():
                df.loc[idx, 'qtd_venda_saneada'] = df.loc[mask_ano_ant, 'qtd_venda'].iloc[0]
                continue

            # 2. Média dos dias adjacentes (antes e depois)
            valores_adj = []
            for delta in [-1, 1, -2, 2]:
                data_adj = data_ruptura + timedelta(days=delta)
                mask_adj = (df['data'] == data_adj) & (df['qtd_venda'] > 0)
                if mask_adj.any():
                    valores_adj.append(df.loc[mask_adj, 'qtd_venda'].iloc[0])
                if len(valores_adj) >= 2:
                    break

            if valores_adj:
                df.loc[idx, 'qtd_venda_saneada'] = sum(valores_adj) / len(valores_adj)
                continue

            # 3. Mediana do período com vendas positivas
            vendas_positivas = df[df['qtd_venda'] > 0]['qtd_venda']
            if len(vendas_positivas) >= 3:
                df.loc[idx, 'qtd_venda_saneada'] = vendas_positivas.median()

        return df

    def processar_item(
        self,
        codigo: int,
        cod_empresa: int,
        previsao_diaria: float,
        desvio_padrao: float,
        cobertura_dias: Optional[int] = None,
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
            lead_time_dias: Lead time do fornecedor (se None, busca do cadastro ou usa 15)
            ciclo_pedido_dias: Ciclo de pedido do fornecedor (se None, usa padrão)
            pedido_minimo_valor: Valor mínimo do pedido (para validação posterior)

        Returns:
            Dicionário com análise completa do item
        """
        # Inicializar variável de previsão semanal (pode ser populada em versões futuras)
        previsao_semanal_info = None

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

        # 3.1. Buscar embalagem de arredondamento (sobrescreve multiplo_caixa se existir)
        embalagem = self.buscar_embalagem(codigo)
        if embalagem['qtd_embalagem'] > 1:
            parametros['multiplo_caixa'] = embalagem['qtd_embalagem']
            parametros['unidade_compra'] = embalagem['unidade_compra']
            parametros['unidade_menor'] = embalagem['unidade_menor']

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
        # Fórmula simplificada: Demanda_Período = Demanda_Diária × Cobertura
        # Mantém consistência com a tela de demanda (DemandCalculator)
        demanda_periodo_base = previsao_diaria * cobertura_dias

        # 8.1. Aplicar eventos (promoções, sazonais, etc.)
        # Eventos são multiplicativos: se evento1=+80% e evento2=+30%, fator = 1.8 * 1.3
        fator_eventos = 1.0
        eventos_aplicados = []
        try:
            from core.event_manager_v2 import EventManagerV2
            event_manager = EventManagerV2()

            # Calcular período de cobertura
            from datetime import timedelta
            data_base = datetime.now().date()
            data_entrega = data_base + timedelta(days=lead_time)
            data_fim_cobertura = data_entrega + timedelta(days=cobertura_dias)

            # Buscar fator de eventos para o item no período
            resultado_eventos = event_manager.calcular_fator_eventos(
                codigo=codigo,
                cod_empresa=cod_empresa,
                cod_fornecedor=produto.get('codigo_fornecedor'),
                linha1=produto.get('linha1'),
                linha3=produto.get('linha3'),
                data_inicio=data_entrega,
                data_fim=data_fim_cobertura
            )

            fator_eventos = resultado_eventos['fator_total']
            eventos_aplicados = resultado_eventos['eventos_aplicados']

        except Exception as e:
            # Se falhar, continua sem aplicar eventos
            pass

        # Aplicar fator de eventos na demanda
        demanda_periodo = demanda_periodo_base * fator_eventos

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
            'unidade_compra': parametros.get('unidade_compra', ''),
            'unidade_menor': parametros.get('unidade_menor', ''),
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

        # Adicionar informações de eventos aplicados
        resultado['eventos'] = {
            'aplicados': len(eventos_aplicados) > 0,
            'fator_total': round(fator_eventos, 4),
            'impacto_percentual': round((fator_eventos - 1) * 100, 2),
            'demanda_base': round(sanitizar_float(demanda_periodo_base, 0), 0),
            'demanda_ajustada': round(sanitizar_float(demanda_periodo, 0), 0),
            'lista_eventos': [
                {
                    'id': e.get('id'),
                    'nome': e.get('nome'),
                    'tipo': e.get('tipo'),
                    'impacto': e.get('impacto_percentual')
                }
                for e in eventos_aplicados
            ]
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
