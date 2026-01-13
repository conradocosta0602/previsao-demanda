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
    - estoque_diario: Posição de estoque no dia (OPCIONAL)
    """

    # Colunas obrigatórias no arquivo
    COLUNAS_OBRIGATORIAS = ['data', 'cod_empresa', 'codigo', 'und_venda', 'qtd_venda', 'padrao_compra']

    # Colunas opcionais que agregam valor
    COLUNAS_OPCIONAIS = ['estoque_diario']

    def __init__(self, caminho_arquivo: str):
        """
        Inicializa o carregador de dados diários

        Args:
            caminho_arquivo: Caminho para o arquivo Excel ou CSV com dados diários
        """
        self.caminho = caminho_arquivo
        self.df_diario = None
        self.df_semanal = None
        self.df_mensal = None
        self.erros = []
        self.avisos = []

        # Flag para indicar se tem coluna de estoque
        self.tem_estoque = False

        # Metadados
        self.filiais = []
        self.produtos = []
        self.periodo_inicial = None
        self.periodo_final = None

    def carregar(self) -> pd.DataFrame:
        """
        Carrega o arquivo Excel ou CSV com dados diários

        Returns:
            DataFrame com os dados diários carregados
        """
        try:
            # Detectar tipo de arquivo pela extensão
            if self.caminho.endswith('.csv'):
                self.df_diario = pd.read_csv(self.caminho, low_memory=False)
            elif self.caminho.endswith(('.xlsx', '.xls')):
                self.df_diario = pd.read_excel(self.caminho)
            else:
                # Tentar CSV primeiro (arquivos sem extensão)
                try:
                    self.df_diario = pd.read_csv(self.caminho, low_memory=False)
                except:
                    self.df_diario = pd.read_excel(self.caminho)

            # Garantir que a coluna data é datetime
            if 'data' in self.df_diario.columns:
                self.df_diario['data'] = pd.to_datetime(self.df_diario['data'])

            # Preencher qtd_venda NaN com 0
            if 'qtd_venda' in self.df_diario.columns:
                self.df_diario['qtd_venda'] = self.df_diario['qtd_venda'].fillna(0)

            # Verificar se tem coluna estoque_diario
            if 'estoque_diario' in self.df_diario.columns:
                self.tem_estoque = True
                # Manter NaN para indicar que não há informação de estoque naquele dia
                # Não preencher com 0, pois 0 significa ruptura
            else:
                self.avisos.append("Coluna 'estoque_diario' não encontrada. Detecção de rupturas desabilitada.")

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

    def detectar_rupturas(self) -> pd.DataFrame:
        """
        Detecta rupturas de estoque (dias onde não houve venda E estoque = 0)

        Ruptura ocorre quando:
        - qtd_venda = 0 (não vendeu)
        - estoque_diario = 0 (não tinha estoque)

        Returns:
            DataFrame com registros de rupturas detectadas
        """
        if not self.tem_estoque:
            raise ValueError("Coluna 'estoque_diario' não disponível. Não é possível detectar rupturas.")

        if self.df_diario is None:
            raise ValueError("Dados não carregados. Execute carregar() primeiro.")

        # Filtrar dias com ruptura: venda = 0 E estoque = 0
        df_rupturas = self.df_diario[
            (self.df_diario['qtd_venda'] == 0) &
            (self.df_diario['estoque_diario'] == 0)
        ].copy()

        # Adicionar informações úteis
        df_rupturas['ruptura'] = True

        return df_rupturas

    def calcular_demanda_perdida(self, janela_dias: int = 7) -> pd.DataFrame:
        """
        Estima a demanda perdida durante rupturas usando média móvel dos dias anteriores

        Args:
            janela_dias: Número de dias anteriores para calcular a média (default: 7)

        Returns:
            DataFrame com demanda perdida estimada por ruptura
        """
        if not self.tem_estoque:
            raise ValueError("Coluna 'estoque_diario' não disponível.")

        # Detectar rupturas
        df_rupturas = self.detectar_rupturas()

        if len(df_rupturas) == 0:
            return pd.DataFrame()  # Sem rupturas

        # Calcular demanda perdida para cada ruptura
        demandas_perdidas = []

        for idx, row in df_rupturas.iterrows():
            filial = row['cod_empresa']
            produto = row['codigo']
            data_ruptura = row['data']

            # Buscar vendas dos N dias anteriores (excluindo rupturas)
            df_historico = self.df_diario[
                (self.df_diario['cod_empresa'] == filial) &
                (self.df_diario['codigo'] == produto) &
                (self.df_diario['data'] < data_ruptura) &
                (self.df_diario['data'] >= data_ruptura - timedelta(days=janela_dias)) &
                (self.df_diario['qtd_venda'] > 0)  # Apenas dias com venda
            ]

            if len(df_historico) > 0:
                # Média das vendas dos dias anteriores
                demanda_estimada = df_historico['qtd_venda'].mean()
            else:
                # Se não houver histórico, usar 0 (conservador)
                demanda_estimada = 0

            demandas_perdidas.append({
                'data': data_ruptura,
                'cod_empresa': filial,
                'codigo': produto,
                'demanda_perdida_estimada': round(demanda_estimada, 2),
                'dias_historico_usados': len(df_historico)
            })

        return pd.DataFrame(demandas_perdidas)

    def ajustar_vendas_com_rupturas(self) -> pd.DataFrame:
        """
        Ajusta o histórico de vendas adicionando a demanda perdida durante rupturas

        Retorna DataFrame com coluna 'qtd_ajustada' que inclui demanda perdida

        Returns:
            DataFrame diário com vendas ajustadas
        """
        if not self.tem_estoque:
            # Se não tem estoque, retornar vendas originais
            df_ajustado = self.df_diario.copy()
            df_ajustado['qtd_ajustada'] = df_ajustado['qtd_venda']
            df_ajustado['tem_ruptura'] = False
            df_ajustado['demanda_perdida'] = 0
            return df_ajustado

        # Calcular demanda perdida
        df_demanda_perdida = self.calcular_demanda_perdida()

        # Criar cópia do DataFrame original
        df_ajustado = self.df_diario.copy()

        # Inicializar colunas
        df_ajustado['qtd_ajustada'] = df_ajustado['qtd_venda']
        df_ajustado['tem_ruptura'] = False
        df_ajustado['demanda_perdida'] = 0

        # Aplicar ajustes nas rupturas
        if len(df_demanda_perdida) > 0:
            for _, ruptura in df_demanda_perdida.iterrows():
                mascara = (
                    (df_ajustado['data'] == ruptura['data']) &
                    (df_ajustado['cod_empresa'] == ruptura['cod_empresa']) &
                    (df_ajustado['codigo'] == ruptura['codigo'])
                )

                df_ajustado.loc[mascara, 'qtd_ajustada'] = ruptura['demanda_perdida_estimada']
                df_ajustado.loc[mascara, 'tem_ruptura'] = True
                df_ajustado.loc[mascara, 'demanda_perdida'] = ruptura['demanda_perdida_estimada']

        return df_ajustado

    def processar_historico_hibrido(self, threshold_filtrar: float = 20.0) -> pd.DataFrame:
        """
        ABORDAGEM HÍBRIDA: Escolhe automaticamente a melhor estratégia por SKU/Filial

        Estratégia adaptativa baseada no % de rupturas:
        - Se < threshold_filtrar (default 20%): FILTRAR rupturas (mais simples e rápido)
        - Se >= threshold_filtrar: AJUSTAR com demanda estimada (preserva dados)

        Esta abordagem combina o melhor dos dois mundos:
        - Produtos com poucas rupturas: processamento rápido via filtro
        - Produtos com rupturas frequentes: ajuste preserva continuidade temporal

        Args:
            threshold_filtrar: % de rupturas abaixo do qual usa filtro (default: 20%)

        Returns:
            DataFrame com coluna 'qtd_processada' e informações da abordagem usada
        """
        if not self.tem_estoque:
            # Se não tem estoque, retornar vendas originais
            df_processado = self.df_diario.copy()
            df_processado['qtd_processada'] = df_processado['qtd_venda']
            df_processado['abordagem'] = 'original'
            df_processado['pct_rupturas'] = 0
            return df_processado

        # Calcular % de rupturas por SKU/Filial
        estatisticas_rupturas = []

        for (filial, produto), grupo in self.df_diario.groupby(['cod_empresa', 'codigo']):
            # Considerar apenas registros com informação de estoque
            grupo_com_estoque = grupo[grupo['estoque_diario'].notna()]

            if len(grupo_com_estoque) == 0:
                continue

            # Contar rupturas
            rupturas = ((grupo_com_estoque['qtd_venda'] == 0) &
                       (grupo_com_estoque['estoque_diario'] == 0)).sum()

            pct_rupturas = (rupturas / len(grupo_com_estoque)) * 100

            # Decidir abordagem
            abordagem = 'filtrar' if pct_rupturas < threshold_filtrar else 'ajustar'

            estatisticas_rupturas.append({
                'cod_empresa': filial,
                'codigo': produto,
                'dias_com_info_estoque': len(grupo_com_estoque),
                'dias_ruptura': rupturas,
                'pct_rupturas': round(pct_rupturas, 1),
                'abordagem': abordagem
            })

        df_estrategias = pd.DataFrame(estatisticas_rupturas)

        # Preparar DataFrame de saída
        df_processado = self.df_diario.copy()
        df_processado['qtd_processada'] = df_processado['qtd_venda']
        df_processado['abordagem'] = 'original'
        df_processado['pct_rupturas'] = 0.0
        df_processado['rupturas_removidas'] = False

        # Calcular demanda perdida UMA VEZ (para SKUs que usarão ajuste)
        skus_ajustar = df_estrategias[df_estrategias['abordagem'] == 'ajustar']

        if len(skus_ajustar) > 0:
            df_demanda_perdida = self.calcular_demanda_perdida()
        else:
            df_demanda_perdida = pd.DataFrame()

        # Aplicar estratégia por SKU
        for _, estrategia in df_estrategias.iterrows():
            filial = estrategia['cod_empresa']
            produto = estrategia['codigo']
            abordagem = estrategia['abordagem']
            pct_rupturas = estrategia['pct_rupturas']

            # Máscara para este SKU
            mascara_sku = ((df_processado['cod_empresa'] == filial) &
                          (df_processado['codigo'] == produto))

            # Aplicar informações estatísticas
            df_processado.loc[mascara_sku, 'abordagem'] = abordagem
            df_processado.loc[mascara_sku, 'pct_rupturas'] = pct_rupturas

            if abordagem == 'filtrar':
                # ABORDAGEM 1: FILTRAR - Remover rupturas
                mascara_ruptura = (mascara_sku &
                                  (df_processado['qtd_venda'] == 0) &
                                  (df_processado['estoque_diario'] == 0))

                df_processado.loc[mascara_ruptura, 'rupturas_removidas'] = True
                # qtd_processada permanece 0, mas será filtrada posteriormente

            else:  # ajustar
                # ABORDAGEM 2: AJUSTAR - Substituir por demanda estimada
                # Buscar rupturas deste SKU na demanda perdida
                df_rupturas_sku = df_demanda_perdida[
                    (df_demanda_perdida['cod_empresa'] == filial) &
                    (df_demanda_perdida['codigo'] == produto)
                ]

                for _, ruptura in df_rupturas_sku.iterrows():
                    mascara_data = (mascara_sku &
                                   (df_processado['data'] == ruptura['data']))

                    df_processado.loc[mascara_data, 'qtd_processada'] = ruptura['demanda_perdida_estimada']

        return df_processado

    def get_resumo_abordagem_hibrida(self, df_processado: pd.DataFrame) -> Dict:
        """
        Gera resumo estatístico da abordagem híbrida aplicada

        Args:
            df_processado: DataFrame retornado por processar_historico_hibrido()

        Returns:
            Dicionário com estatísticas da aplicação
        """
        resumo = {
            'total_skus': df_processado.groupby(['cod_empresa', 'codigo']).ngroups,
            'skus_filtrados': 0,
            'skus_ajustados': 0,
            'skus_originais': 0,
            'registros_rupturas_removidos': 0,
            'registros_ajustados': 0,
            'pct_rupturas_medio': 0
        }

        # Contar por abordagem
        abordagens = df_processado.groupby(['cod_empresa', 'codigo', 'abordagem']).size().reset_index()
        resumo['skus_filtrados'] = (abordagens['abordagem'] == 'filtrar').sum()
        resumo['skus_ajustados'] = (abordagens['abordagem'] == 'ajustar').sum()
        resumo['skus_originais'] = (abordagens['abordagem'] == 'original').sum()

        # Contar registros afetados
        resumo['registros_rupturas_removidos'] = (df_processado['rupturas_removidas'] == True).sum()
        resumo['registros_ajustados'] = ((df_processado['qtd_processada'] != df_processado['qtd_venda']) &
                                         (df_processado['abordagem'] == 'ajustar')).sum()

        # % médio de rupturas
        if len(df_processado) > 0:
            resumo['pct_rupturas_medio'] = df_processado['pct_rupturas'].mean()

        return resumo

    def calcular_nivel_servico(self) -> pd.DataFrame:
        """
        Calcula métricas de nível de serviço por SKU/Filial

        Métricas calculadas:
        - dias_total: Total de dias no período
        - dias_com_estoque: Dias onde estoque > 0
        - dias_em_ruptura: Dias onde estoque = 0
        - taxa_disponibilidade: % de dias com estoque disponível
        - demanda_total: Vendas totais realizadas
        - demanda_perdida: Demanda estimada durante rupturas

        Returns:
            DataFrame com métricas por cod_empresa e codigo
        """
        if not self.tem_estoque:
            raise ValueError("Coluna 'estoque_diario' não disponível.")

        # Calcular demanda perdida
        df_demanda_perdida = self.calcular_demanda_perdida()

        # Agregar demanda perdida por filial/produto
        demanda_perdida_total = df_demanda_perdida.groupby(
            ['cod_empresa', 'codigo']
        )['demanda_perdida_estimada'].sum().reset_index()
        demanda_perdida_total.rename(columns={'demanda_perdida_estimada': 'demanda_perdida'}, inplace=True)

        # Calcular métricas por filial/produto
        metricas = []

        for (filial, produto), grupo in self.df_diario.groupby(['cod_empresa', 'codigo']):
            # Filtrar apenas registros onde temos informação de estoque
            grupo_com_estoque = grupo[grupo['estoque_diario'].notna()]

            if len(grupo_com_estoque) == 0:
                continue  # Pular se não houver dados de estoque

            dias_total = len(grupo_com_estoque)
            dias_com_estoque = (grupo_com_estoque['estoque_diario'] > 0).sum()
            dias_em_ruptura = (grupo_com_estoque['estoque_diario'] == 0).sum()
            taxa_disponibilidade = (dias_com_estoque / dias_total * 100) if dias_total > 0 else 0

            demanda_total = grupo['qtd_venda'].sum()

            # Buscar demanda perdida
            dp = demanda_perdida_total[
                (demanda_perdida_total['cod_empresa'] == filial) &
                (demanda_perdida_total['codigo'] == produto)
            ]
            demanda_perdida = dp['demanda_perdida'].values[0] if len(dp) > 0 else 0

            metricas.append({
                'cod_empresa': filial,
                'codigo': produto,
                'dias_total': dias_total,
                'dias_com_estoque': dias_com_estoque,
                'dias_em_ruptura': dias_em_ruptura,
                'taxa_disponibilidade': round(taxa_disponibilidade, 1),
                'demanda_total': round(demanda_total, 2),
                'demanda_perdida': round(demanda_perdida, 2),
                'demanda_potencial': round(demanda_total + demanda_perdida, 2)
            })

        return pd.DataFrame(metricas)
