"""
Módulo de Cálculo de Reabastecimento
Calcula ponto de pedido, quantidade de pedido e análise de cobertura
"""

import pandas as pd
import numpy as np
from scipy import stats
from core.demand_calculator import DemandCalculator, processar_demandas_dataframe


class ReplenishmentCalculator:
    """
    Calculadora de reabastecimento baseada em demanda, lead time e nível de serviço
    """

    def __init__(self, nivel_servico: float = 0.95):
        """
        Args:
            nivel_servico: Nível de serviço desejado (ex: 0.95 = 95%)
        """
        self.nivel_servico = nivel_servico
        # Z-score para o nível de serviço (distribuição normal)
        self.z_score = stats.norm.ppf(nivel_servico)

    def calcular_estoque_seguranca(
        self,
        demanda_media_mensal: float,
        desvio_padrao_mensal: float,
        lead_time_dias: int
    ) -> float:
        """
        Calcula o estoque de segurança

        Fórmula: ES = Z × σ × √LT
        onde:
        - Z = Z-score do nível de serviço
        - σ = Desvio padrão da demanda diária
        - LT = Lead time em dias

        Args:
            demanda_media_mensal: Demanda média mensal
            desvio_padrao_mensal: Desvio padrão mensal da demanda
            lead_time_dias: Lead time em dias

        Returns:
            Estoque de segurança em unidades
        """
        # Converter para demanda e desvio diário
        demanda_diaria = demanda_media_mensal / 30
        desvio_diario = desvio_padrao_mensal / np.sqrt(30)

        # Estoque de segurança
        estoque_seguranca = self.z_score * desvio_diario * np.sqrt(lead_time_dias)

        return max(0, estoque_seguranca)

    def calcular_ponto_pedido(
        self,
        demanda_media_mensal: float,
        desvio_padrao_mensal: float,
        lead_time_dias: int
    ) -> dict:
        """
        Calcula o ponto de pedido (reorder point)

        Fórmula: PP = (Demanda Diária × Lead Time) + Estoque de Segurança

        Args:
            demanda_media_mensal: Demanda média mensal
            desvio_padrao_mensal: Desvio padrão mensal
            lead_time_dias: Lead time em dias

        Returns:
            Dicionário com ponto de pedido e estoque de segurança
        """
        # Demanda diária
        demanda_diaria = demanda_media_mensal / 30

        # Estoque de segurança
        estoque_seguranca = self.calcular_estoque_seguranca(
            demanda_media_mensal,
            desvio_padrao_mensal,
            lead_time_dias
        )

        # Demanda durante o lead time
        demanda_lead_time = demanda_diaria * lead_time_dias

        # Ponto de pedido
        ponto_pedido = demanda_lead_time + estoque_seguranca

        return {
            'ponto_pedido': round(ponto_pedido, 0),
            'estoque_seguranca': round(estoque_seguranca, 0),
            'demanda_lead_time': round(demanda_lead_time, 0),
            'demanda_diaria': round(demanda_diaria, 2)
        }

    def calcular_quantidade_pedido(
        self,
        estoque_disponivel: float,
        estoque_transito: float,
        pedidos_abertos: float,
        ponto_pedido: float,
        demanda_media_mensal: float,
        lote_minimo: int = 1,
        revisao_dias: int = 7  # Política semanal
    ) -> dict:
        """
        Calcula a quantidade a pedir considerando política de revisão periódica

        Args:
            estoque_disponivel: Estoque atual disponível
            estoque_transito: Estoque em trânsito
            pedidos_abertos: Pedidos em aberto
            ponto_pedido: Ponto de pedido calculado
            demanda_media_mensal: Demanda média mensal
            lote_minimo: Lote mínimo de compra
            revisao_dias: Período de revisão em dias (padrão: 7 = semanal)

        Returns:
            Dicionário com quantidade a pedir e análise
        """
        # Estoque efetivo (disponível + em trânsito + pedidos abertos)
        estoque_efetivo = estoque_disponivel + estoque_transito + pedidos_abertos

        # Demanda esperada durante o período de revisão
        demanda_diaria = demanda_media_mensal / 30
        demanda_revisao = demanda_diaria * revisao_dias

        # Quantidade necessária = Ponto de Pedido + Demanda no período de revisão - Estoque Efetivo
        quantidade_necessaria = ponto_pedido + demanda_revisao - estoque_efetivo

        # Ajustar para lote mínimo
        if quantidade_necessaria > 0:
            # Arredondar para cima para o múltiplo do lote mínimo
            quantidade_pedido = np.ceil(quantidade_necessaria / lote_minimo) * lote_minimo
        else:
            quantidade_pedido = 0

        return {
            'quantidade_pedido': int(quantidade_pedido),
            'estoque_efetivo': round(estoque_efetivo, 0),
            'quantidade_necessaria': round(quantidade_necessaria, 0),
            'demanda_revisao': round(demanda_revisao, 0),
            'deve_pedir': quantidade_pedido > 0
        }

    def calcular_cobertura_dias(
        self,
        estoque: float,
        demanda_diaria: float
    ) -> float:
        """
        Calcula cobertura de estoque em dias

        Args:
            estoque: Quantidade em estoque
            demanda_diaria: Demanda média diária

        Returns:
            Dias de cobertura
        """
        if demanda_diaria > 0:
            return estoque / demanda_diaria
        return 999  # Cobertura "infinita" se não há demanda

    def analisar_item(
        self,
        loja: str,
        sku: str,
        demanda_media_mensal: float,
        desvio_padrao_mensal: float,
        lead_time_dias: int,
        estoque_disponivel: float,
        estoque_transito: float,
        pedidos_abertos: float,
        lote_minimo: int = 1,
        revisao_dias: int = 7
    ) -> dict:
        """
        Análise completa de reabastecimento para um item

        Returns:
            Dicionário completo com todas as análises
        """
        # Calcular ponto de pedido
        pp_info = self.calcular_ponto_pedido(
            demanda_media_mensal,
            desvio_padrao_mensal,
            lead_time_dias
        )

        # Calcular quantidade de pedido
        pedido_info = self.calcular_quantidade_pedido(
            estoque_disponivel,
            estoque_transito,
            pedidos_abertos,
            pp_info['ponto_pedido'],
            demanda_media_mensal,
            lote_minimo,
            revisao_dias
        )

        # Calcular coberturas
        demanda_diaria = pp_info['demanda_diaria']
        cobertura_atual = self.calcular_cobertura_dias(estoque_disponivel, demanda_diaria)
        cobertura_com_pedido = self.calcular_cobertura_dias(
            estoque_disponivel + pedido_info['quantidade_pedido'],
            demanda_diaria
        )

        # Indicador de ruptura (estoque < demanda próximos 7 dias)
        demanda_proximos_7_dias = demanda_diaria * 7
        risco_ruptura = estoque_disponivel < demanda_proximos_7_dias

        return {
            'Loja': loja,
            'SKU': sku,
            'Demanda_Media_Mensal': round(demanda_media_mensal, 1),
            'Desvio_Padrao': round(desvio_padrao_mensal, 1),
            'Lead_Time_Dias': lead_time_dias,
            'Estoque_Disponivel': round(estoque_disponivel, 0),
            'Estoque_Transito': round(estoque_transito, 0),
            'Pedidos_Abertos': round(pedidos_abertos, 0),
            'Ponto_Pedido': pp_info['ponto_pedido'],
            'Estoque_Seguranca': pp_info['estoque_seguranca'],
            'Quantidade_Pedido': pedido_info['quantidade_pedido'],
            'Estoque_Efetivo': pedido_info['estoque_efetivo'],
            'Cobertura_Atual_Dias': round(cobertura_atual, 1),
            'Cobertura_Com_Pedido_Dias': round(cobertura_com_pedido, 1),
            'Risco_Ruptura': 'Sim' if risco_ruptura else 'Não',
            'Deve_Pedir': 'Sim' if pedido_info['deve_pedir'] else 'Não',
            'Lote_Minimo': lote_minimo
        }


def processar_reabastecimento(
    df_entrada: pd.DataFrame,
    nivel_servico: float = 0.95,
    revisao_dias: int = 7
) -> pd.DataFrame:
    """
    Processa reabastecimento para um DataFrame com múltiplos itens

    Args:
        df_entrada: DataFrame com colunas:
            - Loja
            - SKU
            - Demanda_Media_Mensal
            - Desvio_Padrao_Mensal
            - Lead_Time_Dias
            - Estoque_Disponivel
            - Estoque_Transito
            - Pedidos_Abertos
            - Nivel_Servico (opcional)
            - Lote_Minimo (opcional)
        nivel_servico: Nível de serviço padrão (se não especificado por item)
        revisao_dias: Período de revisão em dias

    Returns:
        DataFrame com análise de reabastecimento
    """
    calc = ReplenishmentCalculator(nivel_servico)
    resultados = []

    for _, row in df_entrada.iterrows():
        # Usar nível de serviço específico do item, se disponível
        if 'Nivel_Servico' in row and pd.notna(row['Nivel_Servico']):
            calc = ReplenishmentCalculator(row['Nivel_Servico'])

        # Lote mínimo
        lote_minimo = int(row.get('Lote_Minimo', 1))

        resultado = calc.analisar_item(
            loja=row['Loja'],
            sku=row['SKU'],
            demanda_media_mensal=row['Demanda_Media_Mensal'],
            desvio_padrao_mensal=row['Desvio_Padrao_Mensal'],
            lead_time_dias=int(row['Lead_Time_Dias']),
            estoque_disponivel=row['Estoque_Disponivel'],
            estoque_transito=row.get('Estoque_Transito', 0),
            pedidos_abertos=row.get('Pedidos_Abertos', 0),
            lote_minimo=lote_minimo,
            revisao_dias=revisao_dias
        )

        resultados.append(resultado)

    return pd.DataFrame(resultados)


def processar_reabastecimento_com_historico(
    df_historico: pd.DataFrame,
    df_estoque_atual: pd.DataFrame,
    metodo_demanda: str = 'auto',
    nivel_servico: float = 0.95,
    revisao_dias: int = 7
) -> pd.DataFrame:
    """
    Processa reabastecimento calculando demanda de forma inteligente a partir do histórico

    Args:
        df_historico: DataFrame com histórico de vendas
            Colunas: Loja, SKU, Mes, Vendas
        df_estoque_atual: DataFrame com situação atual de estoque
            Colunas: Loja, SKU, Lead_Time_Dias, Estoque_Disponivel,
                     Estoque_Transito (opcional), Pedidos_Abertos (opcional),
                     Nivel_Servico (opcional), Lote_Minimo (opcional)
        metodo_demanda: Método de cálculo de demanda
            - 'auto': Escolhe automaticamente (RECOMENDADO)
            - 'simples': Média simples
            - 'ema': Média móvel exponencial
            - 'tendencia': Regressão com tendência
            - 'sazonal': Decomposição sazonal
            - 'tsb': Para demanda intermitente (Teunter-Syntetos-Babai)
        nivel_servico: Nível de serviço padrão
        revisao_dias: Período de revisão em dias

    Returns:
        DataFrame com análise de reabastecimento completa incluindo metadata do método usado
    """
    # 1. Calcular demanda e desvio padrão de forma inteligente
    print(f"Calculando demanda com método: {metodo_demanda}")
    df_demanda = processar_demandas_dataframe(df_historico, metodo=metodo_demanda)

    # 2. Combinar com dados de estoque atual
    df_entrada = df_estoque_atual.merge(
        df_demanda,
        on=['Loja', 'SKU'],
        how='left'
    )

    # 3. Preencher valores faltantes
    df_entrada['Demanda_Media_Mensal'] = df_entrada['Demanda_Media_Mensal'].fillna(0)
    df_entrada['Desvio_Padrao_Mensal'] = df_entrada['Desvio_Padrao_Mensal'].fillna(0)

    # 4. Processar reabastecimento
    df_resultado = processar_reabastecimento(
        df_entrada,
        nivel_servico=nivel_servico,
        revisao_dias=revisao_dias
    )

    # 5. Adicionar metadata do método de demanda usado
    if 'Metodo_Usado' in df_entrada.columns:
        df_resultado = df_resultado.merge(
            df_entrada[['Loja', 'SKU', 'Metodo_Usado', 'Padrao_Demanda', 'Confianca']],
            on=['Loja', 'SKU'],
            how='left'
        )

    return df_resultado
