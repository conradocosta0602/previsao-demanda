"""
Módulo Adaptador de Dados
Converte dados diários do banco para o formato esperado pelo sistema de previsão
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from core.daily_data_loader import DailyDataLoader


class DataAdapter:
    """
    Adapta dados diários do banco de dados para o formato do sistema de previsão

    Transforma:
    - Dados diários (data, cod_empresa, codigo, qtd_venda, padrao_compra)
    - Em formato mensal/semanal para previsão (Mes, Loja, SKU, Vendas, etc.)
    """

    def __init__(self, caminho_arquivo: str):
        """
        Inicializa o adaptador

        Args:
            caminho_arquivo: Caminho para arquivo Excel com dados diários
        """
        self.loader = DailyDataLoader(caminho_arquivo)
        self.df_diario = None
        self.df_semanal = None
        self.df_mensal = None
        self.granularidade = 'semanal'  # 'semanal' ou 'mensal'

    def carregar_e_validar(self) -> Tuple[bool, List[str]]:
        """
        Carrega e valida os dados diários

        Returns:
            Tupla (valido, mensagens)
        """
        # Carregar dados
        self.df_diario = self.loader.carregar()

        # Validar
        valido, mensagens = self.loader.validar()

        if valido:
            # Gerar agregações
            self.df_semanal = self.loader.agregar_semanal()
            self.df_mensal = self.loader.agregar_mensal()

        return valido, mensagens

    def converter_para_formato_legado(self,
                                     granularidade: str = 'semanal',
                                     filiais: Optional[List[int]] = None,
                                     produtos: Optional[List[int]] = None) -> pd.DataFrame:
        """
        Converte dados para o formato esperado pelo sistema de previsão

        O sistema atual espera:
        - Mes: Data do período (mensal ou semanal)
        - Loja: Código da filial
        - SKU: Código do produto
        - Vendas: Quantidade vendida
        - Dias_Com_Estoque: Dias disponíveis (calculado)
        - Origem: Origem do produto (mapeado de padrao_compra)

        Args:
            granularidade: 'semanal' (padrão) ou 'mensal'
            filiais: Lista de filiais para filtrar (None = todas)
            produtos: Lista de produtos para filtrar (None = todos)

        Returns:
            DataFrame no formato legado
        """
        if self.df_semanal is None or self.df_mensal is None:
            raise ValueError("Dados não carregados. Execute carregar_e_validar() primeiro.")

        self.granularidade = granularidade

        # Escolher agregação
        if granularidade == 'semanal':
            df = self.df_semanal.copy()
            periodo_col = 'inicio_semana'
            qtd_col = 'qtd_venda_semanal'
            dias_col = 'dias_na_semana'
        else:  # mensal
            df = self.df_mensal.copy()
            periodo_col = 'inicio_mes'
            qtd_col = 'qtd_venda_mensal'
            dias_col = 'dias_no_mes'

        # Filtrar se necessário
        if filiais is not None and len(filiais) > 0:
            df = df[df['cod_empresa'].isin(filiais)]

        if produtos is not None and len(produtos) > 0:
            df = df[df['codigo'].isin(produtos)]

        # Converter para formato legado
        df_legado = pd.DataFrame({
            'Mes': df[periodo_col],
            'Loja': df['cod_empresa'].apply(lambda x: f'F{str(x).zfill(2)}'),  # F01, F02, etc
            'SKU': df['codigo'].astype(str),
            'Vendas': df[qtd_col],
            'Dias_Com_Estoque': df[dias_col],  # Usar dias disponíveis no período
            'Origem': df['padrao_compra'].apply(self._mapear_origem)
        })

        # Garantir tipos corretos
        df_legado['Mes'] = pd.to_datetime(df_legado['Mes'])
        df_legado['Vendas'] = df_legado['Vendas'].astype(int)
        df_legado['Dias_Com_Estoque'] = df_legado['Dias_Com_Estoque'].astype(int)

        # Remover registros sem vendas e sem estoque (opcional)
        # df_legado = df_legado[(df_legado['Vendas'] > 0) | (df_legado['Dias_Com_Estoque'] > 0)]

        # Ordenar
        df_legado = df_legado.sort_values(['Loja', 'SKU', 'Mes']).reset_index(drop=True)

        return df_legado

    def _mapear_origem(self, padrao_compra: float) -> str:
        """
        Mapeia padrão de compra para origem (CD ou DIRETO)

        Lógica:
        - Se padrao_compra é a própria filial ou NaN: DIRETO
        - Caso contrário: CD (vem de outra filial)

        Args:
            padrao_compra: Código da filial que abastece

        Returns:
            'CD' ou 'DIRETO'
        """
        if pd.isna(padrao_compra):
            return 'DIRETO'

        # Poderia adicionar lógica mais sofisticada aqui
        # Por exemplo, verificar se padrao_compra está em lista de CDs
        return 'CD'

    def get_metadados(self) -> Dict:
        """
        Retorna metadados dos dados carregados

        Returns:
            Dicionário com metadados
        """
        return self.loader.get_metadados()

    def get_lista_filiais(self) -> List[Dict]:
        """
        Retorna lista de filiais disponíveis para interface

        Returns:
            Lista de dicionários {'codigo': int, 'nome': str}
        """
        if self.df_diario is None:
            return []

        filiais = sorted(self.df_diario['cod_empresa'].unique().tolist())
        return [{'codigo': f, 'nome': f'Filial {f}'} for f in filiais]

    def get_lista_produtos(self) -> List[Dict]:
        """
        Retorna lista de produtos disponíveis para interface

        Returns:
            Lista de dicionários {'codigo': int, 'nome': str}
        """
        if self.df_diario is None:
            return []

        produtos = sorted(self.df_diario['codigo'].unique().tolist())
        return [{'codigo': p, 'nome': f'Produto {p}'} for p in produtos]

    def gerar_previsao_para_periodo(self,
                                    df_previsao: pd.DataFrame,
                                    granularidade_destino: str = 'diaria') -> pd.DataFrame:
        """
        Converte previsões do sistema (semanais/mensais) de volta para formato final

        Args:
            df_previsao: DataFrame com previsões no formato legado
            granularidade_destino: 'diaria', 'semanal' ou 'mensal'

        Returns:
            DataFrame com previsões no formato solicitado
        """
        if granularidade_destino == self.granularidade:
            # Já está na granularidade desejada
            return df_previsao

        if granularidade_destino == 'diaria' and self.granularidade == 'semanal':
            # Desagregar semanal para diária
            return self._desagregar_previsao_para_diaria(df_previsao)

        if granularidade_destino == 'mensal' and self.granularidade == 'semanal':
            # Agregar semanal para mensal
            return self._agregar_previsao_para_mensal(df_previsao)

        # Outras conversões podem ser implementadas conforme necessário
        return df_previsao

    def _desagregar_previsao_para_diaria(self, df_previsao: pd.DataFrame) -> pd.DataFrame:
        """
        Desagrega previsões semanais em diárias usando método proporcional

        Args:
            df_previsao: DataFrame com previsões semanais

        Returns:
            DataFrame com previsões diárias
        """
        # Converter de volta para formato interno
        df_interno = pd.DataFrame({
            'inicio_semana': df_previsao['Mes'],
            'cod_empresa': df_previsao['Loja'].str.replace('F', '').astype(int),
            'codigo': df_previsao['SKU'].astype(int),
            'previsao_semanal': df_previsao['Previsao']
        })

        # Desagregar
        df_diario = self.loader.desagregar_previsao_semanal_para_diaria(df_interno)

        # Converter para formato final
        df_final = pd.DataFrame({
            'Data': df_diario['data'],
            'Loja': df_diario['cod_empresa'].apply(lambda x: f'F{str(x).zfill(2)}'),
            'SKU': df_diario['codigo'].astype(str),
            'Previsao_Diaria': df_diario['qtd_prevista_diaria']
        })

        return df_final

    def _agregar_previsao_para_mensal(self, df_previsao: pd.DataFrame) -> pd.DataFrame:
        """
        Agrega previsões semanais em mensais

        Args:
            df_previsao: DataFrame com previsões semanais

        Returns:
            DataFrame com previsões mensais
        """
        df = df_previsao.copy()
        df['Mes_Ref'] = pd.to_datetime(df['Mes']).dt.to_period('M').dt.to_timestamp()

        df_mensal = df.groupby(['Loja', 'SKU', 'Mes_Ref']).agg({
            'Previsao': 'sum'
        }).reset_index()

        df_mensal.rename(columns={'Mes_Ref': 'Mes'}, inplace=True)

        return df_mensal

    def estatisticas_dados(self) -> Dict:
        """
        Retorna estatísticas dos dados carregados

        Returns:
            Dicionário com estatísticas
        """
        if self.df_diario is None:
            return {}

        metadados = self.get_metadados()

        # Estatísticas de vendas
        total_vendas = self.df_diario['qtd_venda'].sum()
        dias_com_venda = (self.df_diario['qtd_venda'] > 0).sum()
        taxa_venda = (dias_com_venda / len(self.df_diario)) * 100

        # Estatísticas por filial
        vendas_por_filial = self.df_diario.groupby('cod_empresa')['qtd_venda'].sum().to_dict()

        # Estatísticas por produto
        vendas_por_produto = self.df_diario.groupby('codigo')['qtd_venda'].sum().sort_values(ascending=False).head(10).to_dict()

        return {
            'periodo': {
                'inicio': metadados['periodo_inicial'],
                'fim': metadados['periodo_final'],
                'total_dias': metadados['total_dias']
            },
            'totais': {
                'filiais': len(metadados['filiais']),
                'produtos': len(metadados['produtos']),
                'registros': metadados['total_registros'],
                'vendas_totais': int(total_vendas)
            },
            'vendas': {
                'dias_com_venda': int(dias_com_venda),
                'taxa_venda': round(taxa_venda, 2),
                'media_diaria': round(total_vendas / metadados['total_dias'], 2)
            },
            'top_filiais': vendas_por_filial,
            'top_produtos': vendas_por_produto
        }


def criar_adapter_do_arquivo(caminho_arquivo: str,
                             granularidade: str = 'semanal',
                             filiais: Optional[List[int]] = None,
                             produtos: Optional[List[int]] = None) -> Tuple[pd.DataFrame, Dict]:
    """
    Função auxiliar para criar adapter e converter dados em uma única chamada

    Args:
        caminho_arquivo: Caminho do arquivo Excel
        granularidade: 'semanal' ou 'mensal'
        filiais: Lista de filiais para filtrar
        produtos: Lista de produtos para filtrar

    Returns:
        Tupla (DataFrame convertido, metadados)
    """
    adapter = DataAdapter(caminho_arquivo)

    # Carregar e validar
    valido, mensagens = adapter.carregar_e_validar()

    if not valido:
        raise ValueError(f"Dados inválidos: {'; '.join(mensagens)}")

    # Converter para formato legado
    df_legado = adapter.converter_para_formato_legado(
        granularidade=granularidade,
        filiais=filiais,
        produtos=produtos
    )

    # Obter metadados
    metadados = {
        'dados': adapter.get_metadados(),
        'filiais_disponiveis': adapter.get_lista_filiais(),
        'produtos_disponiveis': adapter.get_lista_produtos(),
        'estatisticas': adapter.estatisticas_dados(),
        'mensagens_validacao': mensagens
    }

    return df_legado, metadados
