"""
Módulo de Carregamento e Processamento de Dados Diários
Responsável por carregar dados diários do banco de dados e processá-los
para previsão semanal com visualizações múltiplas
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, Dict, List, Optional
import warnings

warnings.filterwarnings('ignore')


class DailyDataLoader:
    """
    Classe para carregar e processar dados de vendas diárias

    Estrutura esperada do arquivo:
    - data: Data da venda (datetime)
    - cod_empresa: Código da filial
    - codigo: Código do produto
    - und_venda: Unidade de venda (UN, CX, etc)
    - qtd_venda: Quantidade vendida
    - padrao_compra: Filial que reabastece
    """

    # Colunas obrigatórias no arquivo
    COLUNAS_OBRIGATORIAS = ['data', 'cod_empresa', 'codigo', 'und_venda', 'qtd_venda', 'padrao_compra']

    def __init__(self, caminho_arquivo: str):
        """
        Inicializa o carregador de dados diários

        Args:
            caminho_arquivo: Caminho para o arquivo Excel com dados diários
        """
        self.caminho = caminho_arquivo
        self.df_diario = None
        self.df_semanal = None
        self.df_mensal = None
        self.erros = []
        self.avisos = []

        # Metadados
        self.filiais = []
        self.produtos = []
        self.periodo_inicial = None
        self.periodo_final = None

    def carregar(self) -> pd.DataFrame:
        """
        Carrega o arquivo Excel com dados diários

        Returns:
            DataFrame com os dados diários carregados
        """
        try:
            self.df_diario = pd.read_excel(self.caminho)

            # Garantir que a coluna data é datetime
            if 'data' in self.df_diario.columns:
                self.df_diario['data'] = pd.to_datetime(self.df_diario['data'])

            # Preencher qtd_venda NaN com 0
            if 'qtd_venda' in self.df_diario.columns:
                self.df_diario['qtd_venda'] = self.df_diario['qtd_venda'].fillna(0)

            # Extrair metadados
            self._extrair_metadados()

            return self.df_diario

        except Exception as e:
            raise ValueError(f"Erro ao carregar arquivo: {str(e)}")

    def _extrair_metadados(self):
        """Extrai metadados dos dados carregados"""
        if self.df_diario is not None and len(self.df_diario) > 0:
            self.filiais = sorted(self.df_diario['cod_empresa'].unique().tolist())
            self.produtos = sorted(self.df_diario['codigo'].unique().tolist())
            self.periodo_inicial = self.df_diario['data'].min()
            self.periodo_final = self.df_diario['data'].max()

    def validar(self) -> Tuple[bool, List[str]]:
        """
        Valida os dados carregados

        Returns:
            Tupla (válido: bool, mensagens: list)
        """
        if self.df_diario is None:
            return False, ["Dados não carregados. Execute carregar() primeiro."]

        self.erros = []
        self.avisos = []

        # 1. Verificar colunas obrigatórias
        colunas_faltantes = [col for col in self.COLUNAS_OBRIGATORIAS
                            if col not in self.df_diario.columns]
        if colunas_faltantes:
            self.erros.append(f"Colunas faltantes: {', '.join(colunas_faltantes)}")
            return False, self.erros

        # 2. Validar tipos de dados
        if self.df_diario['data'].dtype != 'datetime64[ns]':
            self.erros.append("Coluna 'data' deve ser do tipo datetime")

        # 3. Validar valores negativos
        if (self.df_diario['qtd_venda'] < 0).any():
            qtd_negativos = (self.df_diario['qtd_venda'] < 0).sum()
            self.erros.append(f"{qtd_negativos} registro(s) com quantidade negativa")

        # 4. Verificar se há dados suficientes
        dias_unicos = self.df_diario['data'].nunique()
        if dias_unicos < 7:
            self.avisos.append(f"Apenas {dias_unicos} dias de dados. Recomendado: mínimo 28 dias (4 semanas)")
        elif dias_unicos < 28:
            self.avisos.append(f"Apenas {dias_unicos} dias de dados. Para melhor precisão, use 90+ dias")

        # 5. Verificar gaps de datas
        self._verificar_gaps_temporais()

        # 6. Estatísticas gerais
        total_vendas = (self.df_diario['qtd_venda'] > 0).sum()
        total_registros = len(self.df_diario)
        taxa_venda = (total_vendas / total_registros) * 100

        self.avisos.append(f"Taxa de dias com venda: {taxa_venda:.1f}% ({total_vendas}/{total_registros})")
        self.avisos.append(f"Período: {self.periodo_inicial.date()} a {self.periodo_final.date()} ({dias_unicos} dias)")
        self.avisos.append(f"Filiais: {len(self.filiais)} | Produtos: {len(self.produtos)}")

        return len(self.erros) == 0, self.erros + self.avisos

    def _verificar_gaps_temporais(self):
        """Verifica gaps nas séries temporais por filial e produto"""
        if self.df_diario is None:
            return

        # Verificar por combinação filial-produto
        for (filial, produto), grupo in self.df_diario.groupby(['cod_empresa', 'codigo']):
            datas = pd.Series(grupo['data'].unique()).sort_values()

            if len(datas) > 1:
                # Criar range completo de datas
                data_min = datas.min()
                data_max = datas.max()
                datas_esperadas = pd.date_range(start=data_min, end=data_max, freq='D')

                # Verificar gaps
                datas_faltantes = set(datas_esperadas) - set(datas)

                if len(datas_faltantes) > 0:
                    pct_gap = (len(datas_faltantes) / len(datas_esperadas)) * 100
                    if pct_gap > 10:  # Apenas alertar se gap > 10%
                        self.avisos.append(
                            f"Filial {filial} / Produto {produto}: {len(datas_faltantes)} dias faltantes ({pct_gap:.1f}%)"
                        )

    def agregar_semanal(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Agrega dados diários em semanais (semana começa na segunda-feira)

        Args:
            df: DataFrame opcional para agregar. Se None, usa self.df_diario

        Returns:
            DataFrame com agregação semanal
        """
        if df is None:
            df = self.df_diario

        if df is None:
            raise ValueError("Nenhum dado disponível para agregação")

        df = df.copy()

        # Adicionar coluna de semana (ISO: segunda a domingo)
        df['ano_semana'] = df['data'].dt.isocalendar().year.astype(str) + '-W' + \
                          df['data'].dt.isocalendar().week.astype(str).str.zfill(2)

        # Data de início da semana (segunda-feira)
        df['inicio_semana'] = df['data'] - pd.to_timedelta(df['data'].dt.dayofweek, unit='D')

        # Agregar por filial, produto e semana
        df_semanal = df.groupby(
            ['cod_empresa', 'codigo', 'ano_semana', 'inicio_semana', 'und_venda', 'padrao_compra'],
            dropna=False
        ).agg({
            'qtd_venda': 'sum',
            'data': 'count'  # Número de dias na semana
        }).reset_index()

        # Renomear colunas
        df_semanal.rename(columns={
            'qtd_venda': 'qtd_venda_semanal',
            'data': 'dias_na_semana'
        }, inplace=True)

        # Ordenar
        df_semanal.sort_values(['cod_empresa', 'codigo', 'inicio_semana'], inplace=True)
        df_semanal.reset_index(drop=True, inplace=True)

        self.df_semanal = df_semanal
        return df_semanal

    def agregar_mensal(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Agrega dados diários em mensais

        Args:
            df: DataFrame opcional para agregar. Se None, usa self.df_diario

        Returns:
            DataFrame com agregação mensal
        """
        if df is None:
            df = self.df_diario

        if df is None:
            raise ValueError("Nenhum dado disponível para agregação")

        df = df.copy()

        # Adicionar colunas de ano e mês
        df['ano'] = df['data'].dt.year
        df['mes'] = df['data'].dt.month
        df['ano_mes'] = df['data'].dt.to_period('M')
        df['inicio_mes'] = df['data'].dt.to_period('M').dt.to_timestamp()

        # Agregar por filial, produto e mês
        df_mensal = df.groupby(
            ['cod_empresa', 'codigo', 'ano_mes', 'inicio_mes', 'und_venda', 'padrao_compra'],
            dropna=False
        ).agg({
            'qtd_venda': 'sum',
            'data': 'count'  # Número de dias no mês
        }).reset_index()

        # Renomear colunas
        df_mensal.rename(columns={
            'qtd_venda': 'qtd_venda_mensal',
            'data': 'dias_no_mes'
        }, inplace=True)

        # Ordenar
        df_mensal.sort_values(['cod_empresa', 'codigo', 'inicio_mes'], inplace=True)
        df_mensal.reset_index(drop=True, inplace=True)

        self.df_mensal = df_mensal
        return df_mensal

    def filtrar_dados(self,
                     filiais: Optional[List[int]] = None,
                     produtos: Optional[List[int]] = None,
                     data_inicio: Optional[datetime] = None,
                     data_fim: Optional[datetime] = None) -> pd.DataFrame:
        """
        Filtra dados diários por filial, produto e período

        Args:
            filiais: Lista de códigos de filiais (None = todas)
            produtos: Lista de códigos de produtos (None = todos)
            data_inicio: Data inicial do filtro (None = sem filtro)
            data_fim: Data final do filtro (None = sem filtro)

        Returns:
            DataFrame filtrado
        """
        if self.df_diario is None:
            raise ValueError("Dados não carregados")

        df = self.df_diario.copy()

        # Filtrar por filiais
        if filiais is not None and len(filiais) > 0:
            df = df[df['cod_empresa'].isin(filiais)]

        # Filtrar por produtos
        if produtos is not None and len(produtos) > 0:
            df = df[df['codigo'].isin(produtos)]

        # Filtrar por data inicial
        if data_inicio is not None:
            df = df[df['data'] >= data_inicio]

        # Filtrar por data final
        if data_fim is not None:
            df = df[df['data'] <= data_fim]

        return df

    def get_metadados(self) -> Dict:
        """
        Retorna metadados dos dados carregados

        Returns:
            Dicionário com metadados
        """
        return {
            'filiais': self.filiais,
            'produtos': self.produtos,
            'periodo_inicial': self.periodo_inicial,
            'periodo_final': self.periodo_final,
            'total_dias': (self.periodo_final - self.periodo_inicial).days + 1 if self.periodo_final else 0,
            'total_registros': len(self.df_diario) if self.df_diario is not None else 0
        }

    def desagregar_previsao_semanal_para_diaria(self,
                                                df_previsao_semanal: pd.DataFrame) -> pd.DataFrame:
        """
        Desagrega previsões semanais em diárias usando método proporcional
        baseado no padrão histórico de cada dia da semana

        Args:
            df_previsao_semanal: DataFrame com previsões semanais

        Returns:
            DataFrame com previsões diárias
        """
        return self._desagregar_proporcional(df_previsao_semanal)

    def _desagregar_proporcional(self, df_semanal: pd.DataFrame) -> pd.DataFrame:
        """
        Desagrega proporcionalmente ao padrão histórico do dia da semana.

        Calcula a proporção média de vendas para cada dia da semana (0=Segunda, 6=Domingo)
        baseado no histórico e distribui a previsão semanal proporcionalmente.

        Se não houver histórico ou padrão para um item, usa distribuição uniforme (1/7 por dia).
        """
        if self.df_diario is None:
            raise ValueError("Histórico diário não disponível para desagregação proporcional")

        # Calcular padrão histórico por dia da semana
        df_hist = self.df_diario.copy()
        df_hist['dia_semana'] = df_hist['data'].dt.dayofweek  # 0=Segunda, 6=Domingo

        # Proporção média de cada dia da semana por filial e produto
        padroes = df_hist.groupby(['cod_empresa', 'codigo', 'dia_semana'])['qtd_venda'].mean().reset_index()
        padroes.rename(columns={'qtd_venda': 'media_dia'}, inplace=True)

        # Calcular proporção relativa
        totais_semanais = padroes.groupby(['cod_empresa', 'codigo'])['media_dia'].sum().reset_index()
        totais_semanais.rename(columns={'media_dia': 'total_semanal'}, inplace=True)

        padroes = padroes.merge(totais_semanais, on=['cod_empresa', 'codigo'])
        padroes['proporcao'] = padroes['media_dia'] / padroes['total_semanal']
        padroes['proporcao'] = padroes['proporcao'].fillna(1/7)  # Se zero, usar distribuição uniforme

        # Desagregar
        registros_diarios = []

        for _, row in df_semanal.iterrows():
            inicio_semana = row['inicio_semana']
            qtd_semanal = row.get('previsao_semanal', row.get('qtd_venda_semanal', 0))

            # Buscar padrão para esta filial/produto
            filtro = (padroes['cod_empresa'] == row['cod_empresa']) & \
                     (padroes['codigo'] == row['codigo'])
            padroes_item = padroes[filtro]

            if len(padroes_item) == 0:
                # Usar distribuição uniforme
                proporcoes = {i: 1/7 for i in range(7)}
            else:
                proporcoes = dict(zip(padroes_item['dia_semana'], padroes_item['proporcao']))
                # Preencher dias faltantes com média
                for dia in range(7):
                    if dia not in proporcoes:
                        proporcoes[dia] = 1/7

            # Criar 7 dias
            for dia in range(7):
                data_dia = inicio_semana + timedelta(days=dia)
                qtd_diaria = qtd_semanal * proporcoes[dia]

                registro = {
                    'data': data_dia,
                    'cod_empresa': row['cod_empresa'],
                    'codigo': row['codigo'],
                    'qtd_prevista_diaria': round(qtd_diaria, 2)
                }

                registros_diarios.append(registro)

        return pd.DataFrame(registros_diarios)
