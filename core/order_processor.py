"""
Módulo de Processamento de Pedidos Manuais
Processa pedidos por quantidade ou por cobertura desejada
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List


class OrderProcessor:
    """
    Processador de pedidos manuais com validação de embalagem
    """

    @staticmethod
    def validar_multiplo_caixa(
        quantidade: float,
        unidades_por_caixa: int,
        arredondar: bool = True
    ) -> Tuple[float, int, bool]:
        """
        Valida e ajusta quantidade para múltiplo de caixa

        Args:
            quantidade: Quantidade desejada
            unidades_por_caixa: Unidades por caixa/embalagem
            arredondar: Se True, arredonda para múltiplo mais próximo

        Returns:
            (quantidade_ajustada, numero_caixas, foi_ajustado)
        """
        if unidades_por_caixa <= 0:
            unidades_por_caixa = 1

        # Verificar se já é múltiplo
        if quantidade % unidades_por_caixa == 0:
            return quantidade, int(quantidade / unidades_por_caixa), False

        # Se não arredondar, retorna erro
        if not arredondar:
            return quantidade, 0, True

        # Arredondar para cima (sempre garantir cobertura)
        numero_caixas = int(np.ceil(quantidade / unidades_por_caixa))
        quantidade_ajustada = numero_caixas * unidades_por_caixa

        return quantidade_ajustada, numero_caixas, True

    @staticmethod
    def calcular_quantidade_por_cobertura(
        cobertura_dias: int,
        demanda_diaria: float,
        unidades_por_caixa: int = 1
    ) -> Dict:
        """
        Calcula quantidade necessária para atingir cobertura desejada

        Args:
            cobertura_dias: Dias de cobertura desejados
            demanda_diaria: Demanda média diária
            unidades_por_caixa: Unidades por embalagem

        Returns:
            Dicionário com cálculos detalhados
        """
        # Quantidade bruta necessária
        quantidade_bruta = cobertura_dias * demanda_diaria

        # Ajustar para múltiplo de caixa
        quantidade_ajustada, numero_caixas, foi_ajustado = OrderProcessor.validar_multiplo_caixa(
            quantidade_bruta,
            unidades_por_caixa,
            arredondar=True
        )

        # Cobertura real após ajuste
        cobertura_real = quantidade_ajustada / demanda_diaria if demanda_diaria > 0 else 0

        return {
            'cobertura_desejada_dias': cobertura_dias,
            'quantidade_bruta': round(quantidade_bruta, 2),
            'quantidade_ajustada': int(quantidade_ajustada),
            'numero_caixas': numero_caixas,
            'cobertura_real_dias': round(cobertura_real, 1),
            'foi_ajustado': foi_ajustado,
            'diferenca_cobertura': round(cobertura_real - cobertura_dias, 1)
        }

    @staticmethod
    def processar_pedido_por_quantidade(
        df_pedido: pd.DataFrame,
        validar_embalagem: bool = True
    ) -> pd.DataFrame:
        """
        Processa pedido onde usuário informa quantidade desejada

        Colunas esperadas (v3.0):
        - Origem, Destino, Tipo_Origem, Tipo_Destino, SKU, Quantidade_Desejada, Unidades_Por_Caixa
        - (Opcional) Demanda_Diaria, Estoque_Disponivel
        - (Retrocompatível) Loja, SKU (versão antiga)

        Args:
            df_pedido: DataFrame com dados do pedido
            validar_embalagem: Se True, valida múltiplo de caixa

        Returns:
            DataFrame com validações e ajustes
        """
        df = df_pedido.copy()

        # Validações básicas (retrocompatível)
        # Versão 3.0: Origem, Destino, Tipo_Origem, Tipo_Destino
        # Versão 2.x: Loja (compatibilidade)
        if 'Origem' in df.columns and 'Destino' in df.columns:
            # Versão 3.0 (nova)
            colunas_obrigatorias = ['Origem', 'Destino', 'Tipo_Origem', 'Tipo_Destino', 'SKU', 'Quantidade_Desejada']
        else:
            # Versão 2.x (antiga - retrocompatibilidade)
            colunas_obrigatorias = ['Loja', 'SKU', 'Quantidade_Desejada']
            # Criar colunas de origem/destino para padronizar processamento
            df['Origem'] = 'N/A'
            df['Destino'] = df['Loja']
            df['Tipo_Origem'] = 'N/A'
            df['Tipo_Destino'] = 'LOJA'

        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]

        if colunas_faltantes:
            raise ValueError(f"Colunas obrigatórias faltando: {', '.join(colunas_faltantes)}")

        # Garantir coluna de embalagem
        if 'Unidades_Por_Caixa' not in df.columns:
            df['Unidades_Por_Caixa'] = 1

        # Garantir que são números válidos
        df['Unidades_Por_Caixa'] = df['Unidades_Por_Caixa'].fillna(1).astype(int)
        df['Quantidade_Desejada'] = df['Quantidade_Desejada'].fillna(0).astype(float)

        # Aplicar validação de embalagem
        if validar_embalagem:
            resultados = df.apply(
                lambda row: OrderProcessor.validar_multiplo_caixa(
                    row['Quantidade_Desejada'],
                    row['Unidades_Por_Caixa'],
                    arredondar=True
                ),
                axis=1
            )

            df['Quantidade_Pedido'] = resultados.apply(lambda x: int(x[0]))
            df['Numero_Caixas'] = resultados.apply(lambda x: x[1])
            df['Foi_Ajustado'] = resultados.apply(lambda x: x[2])
            df['Diferenca_Ajuste'] = df['Quantidade_Pedido'] - df['Quantidade_Desejada']
        else:
            df['Quantidade_Pedido'] = df['Quantidade_Desejada'].astype(int)
            df['Numero_Caixas'] = (df['Quantidade_Pedido'] / df['Unidades_Por_Caixa']).astype(int)
            df['Foi_Ajustado'] = False
            df['Diferenca_Ajuste'] = 0

        # Se tiver demanda diária, calcular cobertura
        if 'Demanda_Diaria' in df.columns:
            df['Demanda_Diaria'] = df['Demanda_Diaria'].fillna(0)
            df['Cobertura_Pedido_Dias'] = df.apply(
                lambda row: round(row['Quantidade_Pedido'] / row['Demanda_Diaria'], 1)
                if row['Demanda_Diaria'] > 0 else 0,
                axis=1
            )
        else:
            df['Cobertura_Pedido_Dias'] = 0

        # Se tiver estoque, calcular cobertura total
        if 'Estoque_Disponivel' in df.columns:
            df['Estoque_Disponivel'] = df['Estoque_Disponivel'].fillna(0)
            df['Estoque_Total_Pos_Pedido'] = df['Estoque_Disponivel'] + df['Quantidade_Pedido']

            if 'Demanda_Diaria' in df.columns:
                df['Cobertura_Total_Dias'] = df.apply(
                    lambda row: round(row['Estoque_Total_Pos_Pedido'] / row['Demanda_Diaria'], 1)
                    if row['Demanda_Diaria'] > 0 else 0,
                    axis=1
                )
            else:
                df['Cobertura_Total_Dias'] = 0
        else:
            df['Estoque_Total_Pos_Pedido'] = df['Quantidade_Pedido']
            df['Cobertura_Total_Dias'] = df['Cobertura_Pedido_Dias']

        # Status do ajuste
        df['Status_Validacao'] = df['Foi_Ajustado'].apply(
            lambda x: 'Ajustado para múltiplo de caixa' if x else 'OK - Múltiplo de caixa'
        )

        # Reordenar colunas
        colunas_finais = [
            'Origem', 'Destino', 'Tipo_Origem', 'Tipo_Destino',
            'SKU',
            'Quantidade_Desejada',
            'Unidades_Por_Caixa',
            'Quantidade_Pedido',
            'Numero_Caixas',
            'Foi_Ajustado',
            'Diferenca_Ajuste',
            'Status_Validacao'
        ]

        # Se tiver coluna Loja (retrocompatibilidade), adicionar no início
        if 'Loja' in df.columns:
            colunas_finais = ['Loja'] + colunas_finais

        # Adicionar colunas opcionais se existirem
        if 'Demanda_Diaria' in df.columns:
            colunas_finais.extend(['Demanda_Diaria', 'Cobertura_Pedido_Dias'])

        if 'Estoque_Disponivel' in df.columns:
            colunas_finais.extend(['Estoque_Disponivel', 'Estoque_Total_Pos_Pedido', 'Cobertura_Total_Dias'])

        # Adicionar outras colunas que existam mas não estão na lista
        for col in df.columns:
            if col not in colunas_finais:
                colunas_finais.append(col)

        return df[colunas_finais]

    @staticmethod
    def processar_pedido_por_cobertura(
        df_pedido: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Processa pedido onde usuário informa cobertura desejada

        Colunas esperadas (v3.0):
        - Origem, Destino, Tipo_Origem, Tipo_Destino, SKU, Demanda_Diaria, Cobertura_Desejada_Dias
        - (Opcional) Estoque_Disponivel, Unidades_Por_Caixa
        - (Retrocompatível) Loja, SKU (versão antiga)

        Args:
            df_pedido: DataFrame com dados do pedido

        Returns:
            DataFrame com quantidades calculadas
        """
        df = df_pedido.copy()

        # Validações básicas (retrocompatível)
        if 'Origem' in df.columns and 'Destino' in df.columns:
            # Versão 3.0 (nova)
            colunas_obrigatorias = ['Origem', 'Destino', 'Tipo_Origem', 'Tipo_Destino', 'SKU', 'Demanda_Diaria', 'Cobertura_Desejada_Dias']
        else:
            # Versão 2.x (antiga - retrocompatibilidade)
            colunas_obrigatorias = ['Loja', 'SKU', 'Demanda_Diaria', 'Cobertura_Desejada_Dias']
            # Criar colunas de origem/destino para padronizar processamento
            df['Origem'] = 'N/A'
            df['Destino'] = df['Loja']
            df['Tipo_Origem'] = 'N/A'
            df['Tipo_Destino'] = 'LOJA'

        colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]

        if colunas_faltantes:
            raise ValueError(f"Colunas obrigatórias faltando: {', '.join(colunas_faltantes)}")

        # Garantir coluna de embalagem
        if 'Unidades_Por_Caixa' not in df.columns:
            df['Unidades_Por_Caixa'] = 1

        # Garantir que são números válidos
        df['Demanda_Diaria'] = df['Demanda_Diaria'].fillna(0).astype(float)
        df['Cobertura_Desejada_Dias'] = df['Cobertura_Desejada_Dias'].fillna(0).astype(int)
        df['Unidades_Por_Caixa'] = df['Unidades_Por_Caixa'].fillna(1).astype(int)

        # Se tiver estoque, calcular cobertura já disponível e necessidade líquida
        if 'Estoque_Disponivel' in df.columns:
            df['Estoque_Disponivel'] = df['Estoque_Disponivel'].fillna(0)

            # Cobertura atual do estoque
            df['Cobertura_Atual_Dias'] = df.apply(
                lambda row: round(row['Estoque_Disponivel'] / row['Demanda_Diaria'], 1)
                if row['Demanda_Diaria'] > 0 else 0,
                axis=1
            )

            # Necessidade líquida (em dias)
            df['Necessidade_Liquida_Dias'] = df.apply(
                lambda row: max(0, row['Cobertura_Desejada_Dias'] - row['Cobertura_Atual_Dias']),
                axis=1
            )

            # Calcular quantidade com base na necessidade líquida
            df['Quantidade_Bruta'] = df['Necessidade_Liquida_Dias'] * df['Demanda_Diaria']
        else:
            df['Estoque_Disponivel'] = 0
            df['Cobertura_Atual_Dias'] = 0
            df['Necessidade_Liquida_Dias'] = df['Cobertura_Desejada_Dias']
            df['Quantidade_Bruta'] = df['Cobertura_Desejada_Dias'] * df['Demanda_Diaria']

        # Ajustar para múltiplo de caixa
        resultados = df.apply(
            lambda row: OrderProcessor.validar_multiplo_caixa(
                row['Quantidade_Bruta'],
                row['Unidades_Por_Caixa'],
                arredondar=True
            ),
            axis=1
        )

        df['Quantidade_Pedido'] = resultados.apply(lambda x: int(x[0]))
        df['Numero_Caixas'] = resultados.apply(lambda x: x[1])
        df['Foi_Ajustado'] = resultados.apply(lambda x: x[2])

        # Cobertura real após pedido
        df['Estoque_Total_Pos_Pedido'] = df['Estoque_Disponivel'] + df['Quantidade_Pedido']
        df['Cobertura_Real_Dias'] = df.apply(
            lambda row: round(row['Estoque_Total_Pos_Pedido'] / row['Demanda_Diaria'], 1)
            if row['Demanda_Diaria'] > 0 else 0,
            axis=1
        )

        # Diferença entre desejado e real
        df['Diferenca_Cobertura'] = df['Cobertura_Real_Dias'] - df['Cobertura_Desejada_Dias']

        # Status
        df['Status_Pedido'] = df.apply(
            lambda row: 'Não necessário' if row['Quantidade_Pedido'] == 0
            else 'Ajustado para múltiplo de caixa' if row['Foi_Ajustado']
            else 'OK - Múltiplo de caixa',
            axis=1
        )

        # Reordenar colunas
        colunas_finais = [
            'Origem', 'Destino', 'Tipo_Origem', 'Tipo_Destino',
            'SKU',
            'Demanda_Diaria',
            'Estoque_Disponivel',
            'Cobertura_Atual_Dias',
            'Cobertura_Desejada_Dias',
            'Necessidade_Liquida_Dias',
            'Quantidade_Bruta',
            'Unidades_Por_Caixa',
            'Quantidade_Pedido',
            'Numero_Caixas',
            'Estoque_Total_Pos_Pedido',
            'Cobertura_Real_Dias',
            'Diferenca_Cobertura',
            'Foi_Ajustado',
            'Status_Pedido'
        ]

        # Se tiver coluna Loja (retrocompatibilidade), adicionar no início
        if 'Loja' in df.columns:
            colunas_finais = ['Loja'] + colunas_finais

        # Adicionar outras colunas que existam
        for col in df.columns:
            if col not in colunas_finais:
                colunas_finais.append(col)

        return df[[col for col in colunas_finais if col in df.columns]]


def gerar_relatorio_pedido(df_resultado: pd.DataFrame, tipo_pedido: str) -> Dict:
    """
    Gera resumo do pedido processado

    Args:
        df_resultado: DataFrame com pedido processado
        tipo_pedido: 'quantidade' ou 'cobertura'

    Returns:
        Dicionário com resumo
    """
    total_itens = len(df_resultado)
    total_caixas = df_resultado['Numero_Caixas'].sum()
    total_unidades = df_resultado['Quantidade_Pedido'].sum()
    itens_ajustados = len(df_resultado[df_resultado['Foi_Ajustado'] == True])

    resumo = {
        'tipo_pedido': tipo_pedido,
        'total_itens': int(total_itens),
        'total_caixas': int(total_caixas),
        'total_unidades': int(total_unidades),
        'itens_ajustados': int(itens_ajustados),
        'percentual_ajustado': round((itens_ajustados / total_itens * 100), 1) if total_itens > 0 else 0
    }

    # Adicional para pedido por cobertura
    if tipo_pedido == 'cobertura' and 'Cobertura_Real_Dias' in df_resultado.columns:
        resumo['cobertura_media_dias'] = round(df_resultado['Cobertura_Real_Dias'].mean(), 1)
        resumo['itens_sem_necessidade'] = int(len(df_resultado[df_resultado['Quantidade_Pedido'] == 0]))

    return resumo
