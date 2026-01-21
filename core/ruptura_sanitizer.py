"""
Módulo de Saneamento de Rupturas no Histórico
Responsável por identificar e substituir zeros de ruptura por valores estimados
usando interpolação sazonal hierárquica.

Hierarquia de estimação:
1. Interpolação Sazonal (mesmo período do ano anterior)
2. Média dos períodos adjacentes
3. Mediana do período com vendas

Autor: Sistema de Previsão de Demanda
Data: Janeiro 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Optional, Any
import warnings

warnings.filterwarnings('ignore')


class RupturaSanitizer:
    """
    Classe para sanear rupturas no histórico de vendas.

    Ruptura é definida como: qtd_venda = 0 E estoque = 0

    A classe substitui zeros de ruptura por valores estimados usando
    uma hierarquia de métodos de interpolação.
    """

    # Métodos de estimação disponíveis
    METODO_SAZONAL = 'sazonal_ano_anterior'
    METODO_ADJACENTE = 'media_adjacentes'
    METODO_MEDIANA = 'mediana_periodo'
    METODO_ORIGINAL = 'sem_alteracao'

    def __init__(self):
        """Inicializa o sanitizador de rupturas."""
        self.estatisticas = {
            'total_rupturas_detectadas': 0,
            'rupturas_saneadas': 0,
            'metodos_usados': {},
            'por_item': []
        }

    def sanear_serie_temporal(
        self,
        df: pd.DataFrame,
        col_data: str = 'periodo',
        col_venda: str = 'qtd_venda',
        col_estoque: str = 'estoque',
        col_produto: str = 'cod_produto',
        col_loja: str = 'cod_empresa',
        granularidade: str = 'mensal'
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Saneia rupturas em uma série temporal de vendas.

        Args:
            df: DataFrame com dados históricos
            col_data: Nome da coluna de data/período
            col_venda: Nome da coluna de quantidade vendida
            col_estoque: Nome da coluna de estoque (pode ser None)
            col_produto: Nome da coluna de código do produto
            col_loja: Nome da coluna de código da loja
            granularidade: 'mensal', 'semanal' ou 'diario'

        Returns:
            Tuple com:
            - DataFrame com vendas saneadas (nova coluna 'qtd_venda_saneada')
            - Dicionário com estatísticas do saneamento
        """
        if df is None or len(df) == 0:
            return df, self.estatisticas

        df_result = df.copy()

        # Inicializar colunas de resultado
        df_result['qtd_venda_saneada'] = df_result[col_venda].copy()
        df_result['foi_saneado'] = False
        df_result['metodo_saneamento'] = self.METODO_ORIGINAL

        # Verificar se tem coluna de estoque
        tem_estoque = col_estoque in df_result.columns and df_result[col_estoque].notna().any()

        if not tem_estoque:
            # Sem estoque, não conseguimos identificar rupturas com certeza
            # Retornar dados originais
            return df_result, self.estatisticas

        # Identificar rupturas: venda = 0 E estoque = 0
        mask_ruptura = (
            (df_result[col_venda] == 0) &
            (df_result[col_estoque] == 0)
        )

        rupturas = df_result[mask_ruptura]
        self.estatisticas['total_rupturas_detectadas'] = len(rupturas)

        if len(rupturas) == 0:
            # Sem rupturas, retornar dados originais
            return df_result, self.estatisticas

        # Processar cada ruptura
        for idx in rupturas.index:
            row = df_result.loc[idx]
            produto = row[col_produto]
            loja = row[col_loja] if col_loja in df_result.columns else None
            periodo = row[col_data]

            # Filtrar dados do mesmo item
            if loja is not None:
                mask_item = (df_result[col_produto] == produto) & (df_result[col_loja] == loja)
            else:
                mask_item = (df_result[col_produto] == produto)

            df_item = df_result[mask_item].copy()

            # Tentar estimar valor
            valor_estimado, metodo = self._estimar_valor(
                df_item,
                periodo,
                col_data,
                col_venda,
                col_estoque,
                granularidade
            )

            if valor_estimado is not None and valor_estimado > 0:
                df_result.loc[idx, 'qtd_venda_saneada'] = valor_estimado
                df_result.loc[idx, 'foi_saneado'] = True
                df_result.loc[idx, 'metodo_saneamento'] = metodo
                self.estatisticas['rupturas_saneadas'] += 1

                # Contabilizar método usado
                if metodo not in self.estatisticas['metodos_usados']:
                    self.estatisticas['metodos_usados'][metodo] = 0
                self.estatisticas['metodos_usados'][metodo] += 1

        return df_result, self.estatisticas

    def _estimar_valor(
        self,
        df_item: pd.DataFrame,
        periodo_ruptura: Any,
        col_data: str,
        col_venda: str,
        col_estoque: str,
        granularidade: str
    ) -> Tuple[Optional[float], str]:
        """
        Estima o valor de venda para um período em ruptura.

        Hierarquia de estimação:
        1. Interpolação sazonal (mesmo período do ano anterior)
        2. Média dos períodos adjacentes
        3. Mediana dos períodos com venda

        Args:
            df_item: DataFrame filtrado para o item específico
            periodo_ruptura: Data/período da ruptura
            col_data: Nome da coluna de data
            col_venda: Nome da coluna de venda
            col_estoque: Nome da coluna de estoque
            granularidade: Tipo de granularidade

        Returns:
            Tuple com (valor_estimado, método_usado)
        """
        # Converter período para datetime se necessário
        if isinstance(periodo_ruptura, str):
            periodo_dt = pd.to_datetime(periodo_ruptura)
        elif isinstance(periodo_ruptura, pd.Timestamp):
            periodo_dt = periodo_ruptura
        else:
            periodo_dt = pd.to_datetime(periodo_ruptura)

        # 1. INTERPOLAÇÃO SAZONAL - Mesmo período do ano anterior
        valor_sazonal = self._interpolar_sazonal(
            df_item, periodo_dt, col_data, col_venda, col_estoque, granularidade
        )
        if valor_sazonal is not None and valor_sazonal > 0:
            return valor_sazonal, self.METODO_SAZONAL

        # 2. MÉDIA DOS PERÍODOS ADJACENTES
        valor_adjacente = self._media_adjacentes(
            df_item, periodo_dt, col_data, col_venda, col_estoque, granularidade
        )
        if valor_adjacente is not None and valor_adjacente > 0:
            return valor_adjacente, self.METODO_ADJACENTE

        # 3. MEDIANA DO PERÍODO
        valor_mediana = self._mediana_periodo(
            df_item, col_venda, col_estoque
        )
        if valor_mediana is not None and valor_mediana > 0:
            return valor_mediana, self.METODO_MEDIANA

        # Não conseguiu estimar
        return None, self.METODO_ORIGINAL

    def _interpolar_sazonal(
        self,
        df_item: pd.DataFrame,
        periodo_dt: datetime,
        col_data: str,
        col_venda: str,
        col_estoque: str,
        granularidade: str
    ) -> Optional[float]:
        """
        Busca o valor do mesmo período do ano anterior.

        Para granularidade:
        - Mensal: mesmo mês do ano anterior
        - Semanal: mesma semana do ano anterior
        - Diário: mesmo dia da semana do ano anterior
        """
        # Calcular período correspondente do ano anterior
        ano_anterior = periodo_dt.year - 1

        if granularidade == 'mensal':
            # Buscar mesmo mês do ano anterior
            periodo_alvo = periodo_dt.replace(year=ano_anterior)
            tolerancia = timedelta(days=15)  # Tolerância de 15 dias para mês
        elif granularidade == 'semanal':
            # Buscar mesma semana do ano anterior
            periodo_alvo = periodo_dt - timedelta(days=364)  # ~52 semanas
            tolerancia = timedelta(days=7)  # Tolerância de 1 semana
        else:  # diario
            # Buscar mesmo dia da semana do ano anterior
            periodo_alvo = periodo_dt - timedelta(days=364)  # Manter dia da semana
            tolerancia = timedelta(days=3)  # Tolerância de 3 dias

        # Converter coluna de data para datetime se necessário
        df_item = df_item.copy()
        df_item['_data_dt'] = pd.to_datetime(df_item[col_data])

        # Filtrar período do ano anterior que não seja ruptura
        mask_ano_anterior = (
            (df_item['_data_dt'] >= periodo_alvo - tolerancia) &
            (df_item['_data_dt'] <= periodo_alvo + tolerancia) &
            (df_item[col_venda] > 0)  # Não pegar zeros
        )

        # Se temos coluna de estoque, garantir que não era ruptura
        if col_estoque in df_item.columns:
            mask_nao_ruptura = df_item[col_estoque].isna() | (df_item[col_estoque] > 0)
            mask_ano_anterior = mask_ano_anterior & mask_nao_ruptura

        df_ano_anterior = df_item[mask_ano_anterior]

        if len(df_ano_anterior) > 0:
            # Usar o valor mais próximo da data alvo
            df_ano_anterior = df_ano_anterior.copy()
            df_ano_anterior['_diff'] = abs(df_ano_anterior['_data_dt'] - periodo_alvo)
            df_ano_anterior = df_ano_anterior.sort_values('_diff')
            return float(df_ano_anterior[col_venda].iloc[0])

        return None

    def _media_adjacentes(
        self,
        df_item: pd.DataFrame,
        periodo_dt: datetime,
        col_data: str,
        col_venda: str,
        col_estoque: str,
        granularidade: str
    ) -> Optional[float]:
        """
        Calcula a média dos períodos imediatamente antes e depois.
        """
        # Determinar intervalo baseado na granularidade
        if granularidade == 'mensal':
            intervalo = timedelta(days=32)  # ~1 mês
        elif granularidade == 'semanal':
            intervalo = timedelta(days=8)  # ~1 semana
        else:  # diario
            intervalo = timedelta(days=2)  # 1-2 dias

        # Converter coluna de data
        df_item = df_item.copy()
        df_item['_data_dt'] = pd.to_datetime(df_item[col_data])

        # Filtrar adjacentes que não sejam ruptura
        mask_antes = (
            (df_item['_data_dt'] < periodo_dt) &
            (df_item['_data_dt'] >= periodo_dt - intervalo) &
            (df_item[col_venda] > 0)
        )

        mask_depois = (
            (df_item['_data_dt'] > periodo_dt) &
            (df_item['_data_dt'] <= periodo_dt + intervalo) &
            (df_item[col_venda] > 0)
        )

        # Se temos estoque, garantir que não são rupturas
        if col_estoque in df_item.columns:
            mask_nao_ruptura = df_item[col_estoque].isna() | (df_item[col_estoque] > 0)
            mask_antes = mask_antes & mask_nao_ruptura
            mask_depois = mask_depois & mask_nao_ruptura

        valores = []

        # Pegar valor antes
        df_antes = df_item[mask_antes].sort_values('_data_dt', ascending=False)
        if len(df_antes) > 0:
            valores.append(float(df_antes[col_venda].iloc[0]))

        # Pegar valor depois
        df_depois = df_item[mask_depois].sort_values('_data_dt', ascending=True)
        if len(df_depois) > 0:
            valores.append(float(df_depois[col_venda].iloc[0]))

        if len(valores) > 0:
            return sum(valores) / len(valores)

        return None

    def _mediana_periodo(
        self,
        df_item: pd.DataFrame,
        col_venda: str,
        col_estoque: str
    ) -> Optional[float]:
        """
        Calcula a mediana dos períodos com venda > 0 (não rupturas).
        """
        # Filtrar apenas registros com venda positiva
        mask_com_venda = df_item[col_venda] > 0

        # Se temos estoque, garantir que não são rupturas
        if col_estoque in df_item.columns:
            mask_nao_ruptura = df_item[col_estoque].isna() | (df_item[col_estoque] > 0)
            mask_com_venda = mask_com_venda & mask_nao_ruptura

        df_com_venda = df_item[mask_com_venda]

        if len(df_com_venda) >= 3:  # Mínimo de 3 registros para mediana confiável
            return float(df_com_venda[col_venda].median())
        elif len(df_com_venda) > 0:
            return float(df_com_venda[col_venda].mean())

        return None

    def get_estatisticas(self) -> Dict:
        """Retorna estatísticas do último saneamento."""
        return self.estatisticas

    def reset_estatisticas(self):
        """Reseta as estatísticas para um novo processamento."""
        self.estatisticas = {
            'total_rupturas_detectadas': 0,
            'rupturas_saneadas': 0,
            'metodos_usados': {},
            'por_item': []
        }


def sanear_vendas_historicas(
    vendas: List[Dict],
    estoque: Dict[str, float],
    granularidade: str = 'mensal'
) -> Tuple[List[Dict], Dict]:
    """
    Função utilitária para sanear lista de vendas históricas.

    Args:
        vendas: Lista de dicts com {'periodo': str, 'qtd_venda': float}
        estoque: Dict com {periodo: estoque} para identificar rupturas
        granularidade: 'mensal', 'semanal' ou 'diario'

    Returns:
        Tuple com (lista_saneada, estatisticas)
    """
    if not vendas:
        return vendas, {'rupturas': 0, 'saneados': 0}

    # Converter para DataFrame
    df = pd.DataFrame(vendas)

    # Adicionar coluna de estoque
    df['estoque'] = df['periodo'].map(estoque).fillna(-1)  # -1 = sem info

    # Adicionar colunas dummy para compatibilidade
    df['cod_produto'] = 'ITEM'
    df['cod_empresa'] = 1

    # Sanear
    sanitizer = RupturaSanitizer()
    df_saneado, stats = sanitizer.sanear_serie_temporal(
        df,
        col_data='periodo',
        col_venda='qtd_venda',
        col_estoque='estoque',
        col_produto='cod_produto',
        col_loja='cod_empresa',
        granularidade=granularidade
    )

    # Converter de volta para lista
    resultado = []
    for _, row in df_saneado.iterrows():
        resultado.append({
            'periodo': row['periodo'],
            'qtd_venda': row['qtd_venda'],
            'qtd_venda_saneada': row['qtd_venda_saneada'],
            'foi_saneado': row['foi_saneado'],
            'metodo_saneamento': row['metodo_saneamento']
        })

    return resultado, stats


def detectar_e_sanear_rupturas_sql(
    cursor,
    cod_produto: int,
    cod_empresa: int,
    granularidade: str = 'mensal'
) -> Tuple[List[Dict], Dict]:
    """
    Detecta e saneia rupturas diretamente do banco de dados.

    Faz JOIN entre historico_vendas_diario e historico_estoque_diario
    para identificar rupturas e aplicar saneamento.

    Args:
        cursor: Cursor do banco de dados
        cod_produto: Código do produto
        cod_empresa: Código da empresa/loja
        granularidade: 'mensal', 'semanal' ou 'diario'

    Returns:
        Tuple com (lista_vendas_saneadas, estatisticas)
    """
    # Query para buscar vendas com estoque
    if granularidade == 'mensal':
        query = """
            SELECT
                DATE_TRUNC('month', h.data) as periodo,
                SUM(h.qtd_venda) as qtd_venda,
                AVG(COALESCE(e.estoque_diario, -1)) as estoque_medio
            FROM historico_vendas_diario h
            LEFT JOIN historico_estoque_diario e
                ON h.data = e.data
                AND h.codigo = e.codigo
                AND h.cod_empresa = e.cod_empresa
            WHERE h.codigo = %s
                AND h.cod_empresa = %s
                AND h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
            GROUP BY DATE_TRUNC('month', h.data)
            ORDER BY periodo
        """
    elif granularidade == 'semanal':
        query = """
            SELECT
                DATE_TRUNC('week', h.data) as periodo,
                SUM(h.qtd_venda) as qtd_venda,
                AVG(COALESCE(e.estoque_diario, -1)) as estoque_medio
            FROM historico_vendas_diario h
            LEFT JOIN historico_estoque_diario e
                ON h.data = e.data
                AND h.codigo = e.codigo
                AND h.cod_empresa = e.cod_empresa
            WHERE h.codigo = %s
                AND h.cod_empresa = %s
                AND h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
            GROUP BY DATE_TRUNC('week', h.data)
            ORDER BY periodo
        """
    else:  # diario
        query = """
            SELECT
                h.data as periodo,
                SUM(h.qtd_venda) as qtd_venda,
                COALESCE(e.estoque_diario, -1) as estoque_medio
            FROM historico_vendas_diario h
            LEFT JOIN historico_estoque_diario e
                ON h.data = e.data
                AND h.codigo = e.codigo
                AND h.cod_empresa = e.cod_empresa
            WHERE h.codigo = %s
                AND h.cod_empresa = %s
                AND h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
            GROUP BY h.data, e.estoque_diario
            ORDER BY periodo
        """

    cursor.execute(query, (cod_produto, cod_empresa))
    rows = cursor.fetchall()

    if not rows:
        return [], {'rupturas': 0, 'saneados': 0}

    # Converter para lista de dicts
    vendas = []
    for row in rows:
        vendas.append({
            'periodo': row['periodo'].strftime('%Y-%m-%d') if row['periodo'] else None,
            'qtd_venda': float(row['qtd_venda']) if row['qtd_venda'] else 0,
            'estoque': float(row['estoque_medio']) if row['estoque_medio'] and row['estoque_medio'] >= 0 else None
        })

    # Criar DataFrame
    df = pd.DataFrame(vendas)
    df['cod_produto'] = cod_produto
    df['cod_empresa'] = cod_empresa

    # Sanear
    sanitizer = RupturaSanitizer()
    df_saneado, stats = sanitizer.sanear_serie_temporal(
        df,
        col_data='periodo',
        col_venda='qtd_venda',
        col_estoque='estoque',
        col_produto='cod_produto',
        col_loja='cod_empresa',
        granularidade=granularidade
    )

    # Converter para resultado
    resultado = []
    for _, row in df_saneado.iterrows():
        resultado.append({
            'periodo': row['periodo'],
            'qtd_venda_original': row['qtd_venda'],
            'qtd_venda': row['qtd_venda_saneada'],  # Usar valor saneado
            'foi_saneado': row['foi_saneado'],
            'metodo_saneamento': row['metodo_saneamento']
        })

    return resultado, stats
