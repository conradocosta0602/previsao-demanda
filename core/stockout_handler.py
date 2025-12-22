"""
Módulo de Tratamento de Rupturas de Estoque (Stockouts)
Responsável por corrigir vendas impactadas por falta de estoque
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import calendar


class StockoutHandler:
    """
    Classe para tratamento de rupturas de estoque

    Quando um produto fica sem estoque, as vendas registradas são menores
    do que a demanda real. Esta classe corrige isso estimando a demanda real.
    """

    def __init__(self, vendas: List[float], dias_estoque: List[int], datas: List = None):
        """
        Inicializa o handler de stockouts

        Args:
            vendas: Lista de vendas por período
            dias_estoque: Lista de dias com estoque por período
            datas: Lista de datas (opcional, para calcular dias do mês)
        """
        self.vendas = np.array(vendas, dtype=float)
        self.dias_estoque = np.array(dias_estoque, dtype=float)
        self.datas = datas

        # Calcular dias totais de cada mês
        if datas is not None:
            self.dias_mes = np.array([
                calendar.monthrange(d.year, d.month)[1] for d in datas
            ], dtype=float)
        else:
            # Assumir 30 dias se não tiver datas
            self.dias_mes = np.full(len(vendas), 30.0)

        # Resultados
        self.vendas_corrigidas = None
        self.taxa_disponibilidade = None
        self.meses_ruptura = None
        self.vendas_perdidas = None

    def calcular_taxa_disponibilidade(self) -> np.ndarray:
        """
        Calcula a taxa de disponibilidade para cada período

        Taxa = dias_com_estoque / dias_totais_mes

        Returns:
            Array com taxas de disponibilidade (0 a 1)
        """
        # Evitar divisão por zero
        self.taxa_disponibilidade = np.where(
            self.dias_mes > 0,
            np.minimum(self.dias_estoque / self.dias_mes, 1.0),
            0.0
        )
        return self.taxa_disponibilidade

    def corrigir_stockouts(self, method: str = 'proporcional') -> np.ndarray:
        """
        Corrige as vendas considerando os stockouts

        Args:
            method: Método de correção
                - 'proporcional': vendas / taxa_disponibilidade
                - 'moving_average': Usa média móvel para meses com ruptura total
                - 'seasonal_average': Usa média sazonal para rupturas

        Returns:
            Array com vendas corrigidas
        """
        if self.taxa_disponibilidade is None:
            self.calcular_taxa_disponibilidade()

        self.vendas_corrigidas = self.vendas.copy()

        if method == 'proporcional':
            # Correção proporcional simples
            # Onde taxa > 0, divide vendas pela taxa
            mascara_valida = self.taxa_disponibilidade > 0
            self.vendas_corrigidas[mascara_valida] = (
                self.vendas[mascara_valida] / self.taxa_disponibilidade[mascara_valida]
            )

            # Onde taxa = 0 (ruptura total), usar média móvel
            self._imputar_rupturas_totais('moving_average')

        elif method == 'moving_average':
            # Primeiro corrige proporcionalmente
            mascara_valida = self.taxa_disponibilidade > 0
            self.vendas_corrigidas[mascara_valida] = (
                self.vendas[mascara_valida] / self.taxa_disponibilidade[mascara_valida]
            )
            # Depois imputa rupturas totais
            self._imputar_rupturas_totais('moving_average')

        elif method == 'seasonal_average':
            mascara_valida = self.taxa_disponibilidade > 0
            self.vendas_corrigidas[mascara_valida] = (
                self.vendas[mascara_valida] / self.taxa_disponibilidade[mascara_valida]
            )
            self._imputar_rupturas_totais('seasonal_average')

        return self.vendas_corrigidas

    def _imputar_rupturas_totais(self, method: str = 'moving_average'):
        """
        Imputa valores para meses com ruptura total (dias_estoque = 0)

        Args:
            method: Método de imputação ('moving_average' ou 'seasonal_average')
        """
        rupturas_totais = self.taxa_disponibilidade == 0

        if not np.any(rupturas_totais):
            return

        if method == 'moving_average':
            # Usar média móvel dos últimos 3 meses com dados válidos
            for i in np.where(rupturas_totais)[0]:
                # Pegar valores anteriores válidos
                valores_anteriores = []
                for j in range(i - 1, max(-1, i - 6), -1):
                    if self.taxa_disponibilidade[j] > 0.5:  # Pelo menos 50% disponível
                        valores_anteriores.append(self.vendas_corrigidas[j])
                    if len(valores_anteriores) >= 3:
                        break

                if valores_anteriores:
                    self.vendas_corrigidas[i] = np.mean(valores_anteriores)
                else:
                    # Se não tem valores anteriores, usar média geral
                    valores_validos = self.vendas_corrigidas[self.taxa_disponibilidade > 0.5]
                    if len(valores_validos) > 0:
                        self.vendas_corrigidas[i] = np.mean(valores_validos)
                    else:
                        self.vendas_corrigidas[i] = 0

        elif method == 'seasonal_average':
            # Usar média do mesmo mês em anos anteriores
            if self.datas is not None:
                for i in np.where(rupturas_totais)[0]:
                    mes_atual = self.datas[i].month
                    valores_mesmo_mes = []

                    for j, data in enumerate(self.datas):
                        if j != i and data.month == mes_atual and self.taxa_disponibilidade[j] > 0.5:
                            valores_mesmo_mes.append(self.vendas_corrigidas[j])

                    if valores_mesmo_mes:
                        self.vendas_corrigidas[i] = np.mean(valores_mesmo_mes)
                    else:
                        # Fallback para média móvel
                        self._imputar_rupturas_totais('moving_average')
                        return
            else:
                # Se não tem datas, usar média móvel
                self._imputar_rupturas_totais('moving_average')

    def calcular_vendas_perdidas(self) -> float:
        """
        Calcula o total de vendas perdidas por ruptura

        Returns:
            Total de vendas perdidas (estimado)
        """
        if self.vendas_corrigidas is None:
            self.corrigir_stockouts()

        self.vendas_perdidas = np.sum(self.vendas_corrigidas - self.vendas)
        return self.vendas_perdidas

    def get_meses_ruptura(self) -> int:
        """
        Retorna o número de meses com ruptura (parcial ou total)

        Returns:
            Número de meses com ruptura
        """
        if self.taxa_disponibilidade is None:
            self.calcular_taxa_disponibilidade()

        self.meses_ruptura = np.sum(self.taxa_disponibilidade < 1.0)
        return self.meses_ruptura

    def get_taxa_ruptura(self) -> float:
        """
        Retorna a taxa de ruptura geral (% de meses com ruptura)

        Returns:
            Taxa de ruptura (0 a 1)
        """
        meses_ruptura = self.get_meses_ruptura()
        return meses_ruptura / len(self.vendas) if len(self.vendas) > 0 else 0.0

    def get_metricas(self) -> Dict:
        """
        Retorna todas as métricas de stockout

        Returns:
            Dicionário com métricas
        """
        if self.vendas_corrigidas is None:
            self.corrigir_stockouts()

        return {
            'total_meses': len(self.vendas),
            'meses_com_ruptura': self.get_meses_ruptura(),
            'meses_ruptura_total': int(np.sum(self.taxa_disponibilidade == 0)),
            'taxa_ruptura': self.get_taxa_ruptura(),
            'vendas_perdidas': self.calcular_vendas_perdidas(),
            'vendas_originais_total': float(np.sum(self.vendas)),
            'vendas_corrigidas_total': float(np.sum(self.vendas_corrigidas)),
            'taxa_disponibilidade_media': float(np.mean(self.taxa_disponibilidade))
        }


def processar_stockouts_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processa stockouts para um DataFrame completo

    Args:
        df: DataFrame com colunas Mes, Loja, SKU, Vendas, Dias_Com_Estoque

    Returns:
        DataFrame com coluna adicional 'Vendas_Corrigidas' e métricas
    """
    df = df.copy()
    df['Vendas_Corrigidas'] = df['Vendas'].astype(float)
    df['Taxa_Disponibilidade'] = 1.0
    df['Vendas_Perdidas'] = 0.0

    # Garantir que Mes é datetime
    if df['Mes'].dtype != 'datetime64[ns]':
        df['Mes'] = pd.to_datetime(df['Mes'])

    # Processar por combinação Loja + SKU
    for (loja, sku), grupo in df.groupby(['Loja', 'SKU']):
        grupo = grupo.sort_values('Mes')
        indices = grupo.index

        handler = StockoutHandler(
            vendas=grupo['Vendas'].tolist(),
            dias_estoque=grupo['Dias_Com_Estoque'].tolist(),
            datas=grupo['Mes'].tolist()
        )

        vendas_corrigidas = handler.corrigir_stockouts('proporcional')
        taxa_disponibilidade = handler.taxa_disponibilidade

        df.loc[indices, 'Vendas_Corrigidas'] = vendas_corrigidas
        df.loc[indices, 'Taxa_Disponibilidade'] = taxa_disponibilidade
        df.loc[indices, 'Vendas_Perdidas'] = vendas_corrigidas - grupo['Vendas'].values

    return df


def calcular_metricas_stockout(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas de stockout por Loja + SKU

    Args:
        df: DataFrame já processado com Vendas_Corrigidas

    Returns:
        DataFrame com métricas por combinação
    """
    metricas = []

    for (loja, sku), grupo in df.groupby(['Loja', 'SKU']):
        handler = StockoutHandler(
            vendas=grupo['Vendas'].tolist(),
            dias_estoque=grupo['Dias_Com_Estoque'].tolist(),
            datas=grupo['Mes'].tolist() if 'Mes' in grupo.columns else None
        )

        m = handler.get_metricas()
        m['Loja'] = loja
        m['SKU'] = sku
        metricas.append(m)

    return pd.DataFrame(metricas)
