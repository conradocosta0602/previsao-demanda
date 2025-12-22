"""
Módulo de Carregamento e Validação de Dados
Responsável por carregar arquivos Excel e validar estrutura dos dados
"""

import pandas as pd
import numpy as np
from datetime import datetime
import calendar


class DataLoader:
    """
    Classe para carregar e validar dados de vendas
    """

    # Colunas obrigatórias no arquivo Excel
    COLUNAS_OBRIGATORIAS = ['Mes', 'Loja', 'SKU', 'Vendas', 'Dias_Com_Estoque', 'Origem']

    # Lojas válidas
    LOJAS_VALIDAS = [f'L0{i}' for i in range(1, 10)]  # L01 a L09

    # Origens válidas
    ORIGENS_VALIDAS = ['CD', 'DIRETO']

    def __init__(self, caminho_arquivo: str):
        """
        Inicializa o carregador de dados

        Args:
            caminho_arquivo: Caminho para o arquivo Excel
        """
        self.caminho = caminho_arquivo
        self.df = None
        self.erros = []
        self.avisos = []

    def carregar(self) -> pd.DataFrame:
        """
        Carrega o arquivo Excel

        Returns:
            DataFrame com os dados carregados
        """
        try:
            self.df = pd.read_excel(self.caminho)
            return self.df
        except Exception as e:
            raise ValueError(f"Erro ao carregar arquivo: {str(e)}")

    def validar(self) -> tuple:
        """
        Valida os dados carregados

        Returns:
            Tupla (válido: bool, mensagens: list)
        """
        if self.df is None:
            return False, ["Dados não carregados. Execute carregar() primeiro."]

        self.erros = []
        self.avisos = []

        # 1. Verificar colunas obrigatórias
        colunas_faltantes = [col for col in self.COLUNAS_OBRIGATORIAS if col not in self.df.columns]
        if colunas_faltantes:
            self.erros.append(f"Colunas faltantes: {', '.join(colunas_faltantes)}")

        if self.erros:
            return False, self.erros

        # 2. Validar formato de data (YYYY-MM)
        try:
            self.df['Mes'] = pd.to_datetime(self.df['Mes'], format='%Y-%m')
        except:
            try:
                self.df['Mes'] = pd.to_datetime(self.df['Mes'])
                self.df['Mes'] = self.df['Mes'].dt.to_period('M').dt.to_timestamp()
            except:
                self.erros.append("Formato de data inválido na coluna 'Mes'. Use YYYY-MM.")

        # 3. Validar lojas
        lojas_invalidas = set(self.df['Loja'].unique()) - set(self.LOJAS_VALIDAS)
        if lojas_invalidas:
            self.erros.append(f"Lojas inválidas encontradas: {', '.join(lojas_invalidas)}. Use L01 a L09.")

        # 4. Validar vendas >= 0
        vendas_negativas = (self.df['Vendas'] < 0).sum()
        if vendas_negativas > 0:
            self.erros.append(f"{vendas_negativas} registro(s) com vendas negativas.")

        # 5. Validar Dias_Com_Estoque
        dias_negativos = (self.df['Dias_Com_Estoque'] < 0).sum()
        if dias_negativos > 0:
            self.erros.append(f"{dias_negativos} registro(s) com dias de estoque negativos.")

        # Validar dias <= dias do mês
        if 'Mes' in self.df.columns and self.df['Mes'].dtype == 'datetime64[ns]':
            self.df['Dias_Mes'] = self.df['Mes'].apply(
                lambda x: calendar.monthrange(x.year, x.month)[1]
            )
            dias_excedentes = (self.df['Dias_Com_Estoque'] > self.df['Dias_Mes']).sum()
            if dias_excedentes > 0:
                self.avisos.append(f"{dias_excedentes} registro(s) com dias de estoque > dias do mês (serão ajustados).")
                # Ajustar automaticamente
                self.df['Dias_Com_Estoque'] = self.df.apply(
                    lambda row: min(row['Dias_Com_Estoque'], row['Dias_Mes']), axis=1
                )

        # 6. Validar origem
        origens_invalidas = set(self.df['Origem'].str.upper().unique()) - set(self.ORIGENS_VALIDAS)
        if origens_invalidas:
            self.erros.append(f"Origens inválidas: {', '.join(origens_invalidas)}. Use 'CD' ou 'DIRETO'.")
        else:
            # Normalizar origem para maiúsculas
            self.df['Origem'] = self.df['Origem'].str.upper()

        # 7. Verificar gaps temporais
        if 'Mes' in self.df.columns and self.df['Mes'].dtype == 'datetime64[ns]':
            for (loja, sku), grupo in self.df.groupby(['Loja', 'SKU']):
                meses = grupo['Mes'].sort_values()
                if len(meses) > 1:
                    # Verificar se há gaps
                    meses_esperados = pd.date_range(start=meses.min(), end=meses.max(), freq='MS')
                    meses_faltantes = set(meses_esperados) - set(meses)
                    if meses_faltantes:
                        self.avisos.append(f"Gap temporal em {loja}/{sku}: {len(meses_faltantes)} mês(es) faltante(s).")

        return len(self.erros) == 0, self.erros + self.avisos

    def get_dados_validados(self) -> pd.DataFrame:
        """
        Retorna os dados validados e processados

        Returns:
            DataFrame processado
        """
        if self.df is None:
            raise ValueError("Dados não carregados.")

        return self.df.copy()


def validar_dados(df: pd.DataFrame) -> tuple:
    """
    Função auxiliar para validar um DataFrame já carregado

    Args:
        df: DataFrame com os dados

    Returns:
        Tupla (válido: bool, mensagens: list)
    """
    loader = DataLoader.__new__(DataLoader)
    loader.df = df.copy()
    loader.erros = []
    loader.avisos = []

    return loader.validar()


def ajustar_mes_corrente(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajusta o mês corrente (parcial) para projeção completa

    Se o último mês é o mês atual e está incompleto,
    projeta as vendas para o mês inteiro.

    Args:
        df: DataFrame com os dados

    Returns:
        DataFrame com colunas adicionais:
        - Mes_Projetado (bool): Se o mês foi projetado
        - Taxa_Progresso (float): Proporção do mês decorrida
        - Vendas_Original (int): Vendas antes da projeção
    """
    df = df.copy()

    # Garantir que Mes é datetime
    if df['Mes'].dtype != 'datetime64[ns]':
        df['Mes'] = pd.to_datetime(df['Mes'])

    # Identificar último mês nos dados
    ultimo_mes = df['Mes'].max()

    # Data atual
    hoje = datetime.now()
    mes_atual = datetime(hoje.year, hoje.month, 1)

    # Inicializar colunas
    df['Mes_Projetado'] = False
    df['Taxa_Progresso'] = 1.0
    df['Vendas_Original'] = df['Vendas']

    # Verificar se último mês é o mês atual
    if ultimo_mes.year == hoje.year and ultimo_mes.month == hoje.month:
        # Calcular dias decorridos
        dias_decorridos = hoje.day
        dias_totais = calendar.monthrange(hoje.year, hoje.month)[1]
        taxa_progresso = dias_decorridos / dias_totais

        # Filtrar registros do mês atual
        mascara_mes_atual = (df['Mes'].dt.year == hoje.year) & (df['Mes'].dt.month == hoje.month)

        # Projetar vendas
        df.loc[mascara_mes_atual, 'Mes_Projetado'] = True
        df.loc[mascara_mes_atual, 'Taxa_Progresso'] = taxa_progresso

        # Projetar vendas (vendas / taxa para estimar mês completo)
        df.loc[mascara_mes_atual, 'Vendas'] = (
            df.loc[mascara_mes_atual, 'Vendas'] / taxa_progresso
        ).round().astype(int)

        # Ajustar dias com estoque proporcionalmente
        df.loc[mascara_mes_atual, 'Dias_Com_Estoque'] = (
            df.loc[mascara_mes_atual, 'Dias_Com_Estoque'] / taxa_progresso
        ).round().astype(int)

        # Limitar dias ao máximo do mês
        df.loc[mascara_mes_atual, 'Dias_Com_Estoque'] = df.loc[mascara_mes_atual, 'Dias_Com_Estoque'].clip(upper=dias_totais)

    return df


def dias_no_mes(data: datetime) -> int:
    """
    Retorna o número de dias em um mês

    Args:
        data: Data do mês

    Returns:
        Número de dias no mês
    """
    return calendar.monthrange(data.year, data.month)[1]
