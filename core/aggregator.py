"""
Módulo de Agregação para Centro de Distribuição (CD)
Agrega demandas das lojas que recebem do CD para gerar previsão consolidada
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from .method_selector import MethodSelector
from .forecasting_models import get_modelo


class CDAggregator:
    """
    Agrega demandas das lojas para gerar previsão do Centro de Distribuição

    O CD precisa abastecer todas as lojas que recebem produtos dele,
    então a previsão do CD é a soma das demandas dessas lojas.
    """

    def __init__(self, df_historico: pd.DataFrame):
        """
        Inicializa o agregador

        Args:
            df_historico: DataFrame com histórico de vendas
                Colunas esperadas: Mes, Loja, SKU, Vendas_Corrigidas, Origem
        """
        self.df = df_historico.copy()

        # Garantir que Mes é datetime
        if self.df['Mes'].dtype != 'datetime64[ns]':
            self.df['Mes'] = pd.to_datetime(self.df['Mes'])

    def identificar_lojas_cd(self, sku: str) -> List[str]:
        """
        Identifica quais lojas recebem um SKU do CD

        Baseado na coluna 'Origem' do último mês disponível.

        Args:
            sku: Código do SKU

        Returns:
            Lista de lojas que recebem do CD
        """
        df_sku = self.df[self.df['SKU'] == sku].copy()

        if df_sku.empty:
            return []

        # Pegar o último mês
        ultimo_mes = df_sku['Mes'].max()
        df_ultimo = df_sku[df_sku['Mes'] == ultimo_mes]

        # Filtrar lojas com origem CD
        lojas_cd = df_ultimo[df_ultimo['Origem'] == 'CD']['Loja'].unique().tolist()

        return sorted(lojas_cd)

    def identificar_lojas_direto(self, sku: str) -> List[str]:
        """
        Identifica quais lojas recebem um SKU direto do fornecedor

        Args:
            sku: Código do SKU

        Returns:
            Lista de lojas que recebem direto
        """
        df_sku = self.df[self.df['SKU'] == sku].copy()

        if df_sku.empty:
            return []

        # Pegar o último mês
        ultimo_mes = df_sku['Mes'].max()
        df_ultimo = df_sku[df_sku['Mes'] == ultimo_mes]

        # Filtrar lojas com origem DIRETO
        lojas_direto = df_ultimo[df_ultimo['Origem'] == 'DIRETO']['Loja'].unique().tolist()

        return sorted(lojas_direto)

    def agregar_vendas_historicas(self, sku: str, usar_corrigidas: bool = True) -> pd.DataFrame:
        """
        Agrega vendas históricas das lojas que recebem do CD

        Args:
            sku: Código do SKU
            usar_corrigidas: Se True, usa Vendas_Corrigidas; senão, Vendas

        Returns:
            DataFrame com série temporal agregada
        """
        lojas_cd = self.identificar_lojas_cd(sku)

        if not lojas_cd:
            return pd.DataFrame()

        # Filtrar dados
        df_sku = self.df[
            (self.df['SKU'] == sku) &
            (self.df['Loja'].isin(lojas_cd))
        ].copy()

        if df_sku.empty:
            return pd.DataFrame()

        # Coluna de vendas a usar
        coluna_vendas = 'Vendas_Corrigidas' if usar_corrigidas and 'Vendas_Corrigidas' in df_sku.columns else 'Vendas'

        # Agregar por mês
        df_agregado = df_sku.groupby('Mes').agg({
            coluna_vendas: 'sum',
            'Loja': lambda x: len(x.unique())  # Número de lojas
        }).reset_index()

        df_agregado.columns = ['Mes', 'Vendas_CD', 'Num_Lojas']
        df_agregado = df_agregado.sort_values('Mes')

        return df_agregado

    def gerar_previsao_cd(self, sku: str, horizon: int = 6, usar_corrigidas: bool = True) -> Dict:
        """
        Gera previsão de demanda para o CD de um SKU

        1. Agrega vendas históricas das lojas que recebem do CD
        2. Seleciona método apropriado para a série agregada
        3. Gera previsão

        Args:
            sku: Código do SKU
            horizon: Número de meses para prever
            usar_corrigidas: Se True, usa vendas corrigidas por stockout

        Returns:
            Dicionário com:
            - sku: Código do SKU
            - lojas_incluidas: Lista de lojas incluídas
            - serie_historica: DataFrame com histórico agregado
            - metodo: Método de previsão utilizado
            - previsoes: Lista de previsões
            - datas_futuras: Lista de datas das previsões
            - confianca: Nível de confiança do método
            - caracteristicas: Características da série
        """
        lojas_cd = self.identificar_lojas_cd(sku)

        if not lojas_cd:
            return {
                'sku': sku,
                'lojas_incluidas': [],
                'serie_historica': pd.DataFrame(),
                'metodo': None,
                'previsoes': [],
                'datas_futuras': [],
                'confianca': 0,
                'caracteristicas': {},
                'erro': 'Nenhuma loja recebe este SKU do CD'
            }

        # Agregar vendas
        df_agregado = self.agregar_vendas_historicas(sku, usar_corrigidas)

        if df_agregado.empty or len(df_agregado) < 3:
            return {
                'sku': sku,
                'lojas_incluidas': lojas_cd,
                'serie_historica': df_agregado,
                'metodo': None,
                'previsoes': [],
                'datas_futuras': [],
                'confianca': 0,
                'caracteristicas': {},
                'erro': 'Dados insuficientes para previsão do CD'
            }

        # Selecionar método
        vendas = df_agregado['Vendas_CD'].tolist()
        datas = df_agregado['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        # Gerar previsão
        try:
            modelo = get_modelo(recomendacao['metodo'])
            modelo.fit(vendas)
            previsoes = modelo.predict(horizon)
        except Exception as e:
            # Fallback para média móvel simples
            modelo = get_modelo('Média Móvel Simples')
            modelo.fit(vendas)
            previsoes = modelo.predict(horizon)
            recomendacao['metodo'] = 'Média Móvel Simples'
            recomendacao['razao'] += f' (fallback devido a erro: {str(e)})'

        # Gerar datas futuras
        ultima_data = datas[-1]
        datas_futuras = []
        for h in range(1, horizon + 1):
            nova_data = ultima_data + pd.DateOffset(months=h)
            datas_futuras.append(nova_data)

        return {
            'sku': sku,
            'lojas_incluidas': lojas_cd,
            'serie_historica': df_agregado,
            'metodo': recomendacao['metodo'],
            'previsoes': previsoes,
            'datas_futuras': datas_futuras,
            'confianca': recomendacao['confianca'],
            'razao': recomendacao['razao'],
            'caracteristicas': recomendacao['caracteristicas']
        }


def gerar_previsoes_cd(df_historico: pd.DataFrame, skus: List[str] = None,
                       horizon: int = 6) -> pd.DataFrame:
    """
    Gera previsões do CD para múltiplos SKUs

    Args:
        df_historico: DataFrame com histórico de vendas
        skus: Lista de SKUs (se None, processa todos)
        horizon: Horizonte de previsão

    Returns:
        DataFrame com previsões do CD
    """
    aggregator = CDAggregator(df_historico)

    if skus is None:
        skus = df_historico['SKU'].unique().tolist()

    resultados = []

    for sku in skus:
        previsao = aggregator.gerar_previsao_cd(sku, horizon)

        if 'erro' in previsao:
            continue

        for i, (data, valor) in enumerate(zip(previsao['datas_futuras'], previsao['previsoes'])):
            resultados.append({
                'SKU': sku,
                'Mes_Previsao': data,
                'Previsao_CD': round(valor, 1),
                'Lojas_Incluidas': ', '.join(previsao['lojas_incluidas']),
                'Num_Lojas': len(previsao['lojas_incluidas']),
                'Metodo': previsao['metodo'],
                'Confianca': previsao['confianca']
            })

    return pd.DataFrame(resultados)
