#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera arquivos de exemplo para os dois tipos de pedido manual
"""

import pandas as pd

def gerar_exemplo_pedido_quantidade():
    """
    Gera exemplo para pedido por quantidade
    """
    dados = [
        {
            'Origem': 'CD_PRINCIPAL',
            'Destino': 'LOJA_01',
            'Tipo_Origem': 'CD',
            'Tipo_Destino': 'LOJA',
            'Loja': 'LOJA_01',  # Mantido para retrocompatibilidade
            'SKU': 'PROD_001',
            'Quantidade_Desejada': 100,
            'Unidades_Por_Caixa': 12,
            'Demanda_Diaria': 5.5,  # Opcional
            'Estoque_Disponivel': 20  # Opcional
        },
        {
            'Origem': 'CD_PRINCIPAL',
            'Destino': 'LOJA_01',
            'Tipo_Origem': 'CD',
            'Tipo_Destino': 'LOJA',
            'Loja': 'LOJA_01',
            'SKU': 'PROD_002',
            'Quantidade_Desejada': 75,
            'Unidades_Por_Caixa': 10,
            'Demanda_Diaria': 3.2,
            'Estoque_Disponivel': 15
        },
        {
            'Origem': 'LOJA_02',
            'Destino': 'LOJA_03',
            'Tipo_Origem': 'LOJA',
            'Tipo_Destino': 'LOJA',
            'Loja': 'LOJA_03',  # Destino
            'SKU': 'PROD_001',
            'Quantidade_Desejada': 48,
            'Unidades_Por_Caixa': 12,
            'Demanda_Diaria': 4.0,
            'Estoque_Disponivel': 10
        },
        {
            'Origem': 'FORNECEDOR_A',
            'Destino': 'CD_PRINCIPAL',
            'Tipo_Origem': 'FORNECEDOR',
            'Tipo_Destino': 'CD',
            'Loja': 'CD_PRINCIPAL',  # Destino
            'SKU': 'PROD_003',
            'Quantidade_Desejada': 240,
            'Unidades_Por_Caixa': 24,
            'Demanda_Diaria': 8.5,
            'Estoque_Disponivel': 30
        },
    ]

    df = pd.DataFrame(dados)

    # Criar instrucoes
    instrucoes = [
        ['INSTRUCOES - PEDIDO POR QUANTIDADE (v3.0)', ''],
        ['', ''],
        ['Objetivo:', 'Informar quantidade desejada de pedido para cada item'],
        ['', ''],
        ['Colunas OBRIGATORIAS:', ''],
        ['  SKU', 'Codigo do produto'],
        ['  Quantidade_Desejada', 'Quantidade que voce deseja pedir'],
        ['  Unidades_Por_Caixa', 'Quantas unidades vem em cada caixa/embalagem'],
        ['', ''],
        ['Colunas OPCIONAIS (v3.0 - Multifluxo):', ''],
        ['  Origem', 'De onde vem o pedido (FORNECEDOR_A, CD_PRINCIPAL, LOJA_01)'],
        ['  Destino', 'Para onde vai (CD_PRINCIPAL, LOJA_01, LOJA_02)'],
        ['  Tipo_Origem', 'Tipo da origem (FORNECEDOR, CD, LOJA)'],
        ['  Tipo_Destino', 'Tipo do destino (CD, LOJA)'],
        ['  Loja', 'Codigo da loja (mantido para compatibilidade v2.x)'],
        ['', ''],
        ['Colunas OPCIONAIS (para calculo de cobertura):', ''],
        ['  Demanda_Diaria', 'Demanda media diaria do produto'],
        ['  Estoque_Disponivel', 'Estoque fisico atual'],
        ['', ''],
        ['O que o sistema faz:', ''],
        ['  1. Valida se quantidade esta em multiplo de caixa'],
        ['  2. Ajusta automaticamente para cima se necessario'],
        ['  3. Calcula numero de caixas a pedir'],
        ['  4. Se tiver demanda, calcula cobertura do pedido'],
        ['  5. Gera relatorio pronto para emissao'],
        ['', ''],
        ['RETROCOMPATIBILIDADE:', ''],
        ['  Arquivos antigos (v2.x) sem Origem/Destino continuam funcionando'],
        ['  Sistema detecta automaticamente a versao do arquivo'],
        ['', ''],
        ['Exemplo:', ''],
        ['  Voce quer 100 unidades, embalagem tem 12 unidades'],
        ['  Sistema ajusta para 108 (9 caixas x 12)'],
        ['  Garante que pedido estara em multiplo de caixa'],
    ]

    df_instrucoes = pd.DataFrame(instrucoes, columns=['Campo', 'Descricao'])

    # Salvar
    caminho = 'exemplo_pedido_quantidade.xlsx'
    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='PEDIDO', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"Criado: {caminho}")
    return caminho


def gerar_exemplo_pedido_cobertura():
    """
    Gera exemplo para pedido por cobertura
    """
    dados = [
        {
            'Loja': 'LOJA_01',
            'SKU': 'PROD_001',
            'Demanda_Diaria': 5.5,
            'Cobertura_Desejada_Dias': 30,
            'Unidades_Por_Caixa': 12,
            'Estoque_Disponivel': 20  # Opcional
        },
        {
            'Loja': 'LOJA_01',
            'SKU': 'PROD_002',
            'Demanda_Diaria': 3.2,
            'Cobertura_Desejada_Dias': 45,
            'Unidades_Por_Caixa': 10,
            'Estoque_Disponivel': 15
        },
        {
            'Loja': 'LOJA_02',
            'SKU': 'PROD_001',
            'Demanda_Diaria': 4.0,
            'Cobertura_Desejada_Dias': 30,
            'Unidades_Por_Caixa': 12,
            'Estoque_Disponivel': 10
        },
        {
            'Loja': 'LOJA_02',
            'SKU': 'PROD_003',
            'Demanda_Diaria': 2.1,
            'Cobertura_Desejada_Dias': 60,
            'Unidades_Por_Caixa': 6,
            'Estoque_Disponivel': 50  # Ja tem estoque alto
        },
    ]

    df = pd.DataFrame(dados)

    # Criar instrucoes
    instrucoes = [
        ['INSTRUCOES - PEDIDO POR COBERTURA', ''],
        ['', ''],
        ['Objetivo:', 'Informar quantos dias de cobertura voce quer ter apos o pedido'],
        ['', ''],
        ['Colunas OBRIGATORIAS:', ''],
        ['  Loja', 'Codigo da loja'],
        ['  SKU', 'Codigo do produto'],
        ['  Demanda_Diaria', 'Demanda media diaria do produto'],
        ['  Cobertura_Desejada_Dias', 'Quantos dias de estoque voce quer ter'],
        ['  Unidades_Por_Caixa', 'Quantas unidades vem em cada caixa'],
        ['', ''],
        ['Colunas OPCIONAIS:', ''],
        ['  Estoque_Disponivel', 'Estoque fisico atual (se tiver)'],
        ['', ''],
        ['O que o sistema faz:', ''],
        ['  1. Calcula cobertura atual do estoque'],
        ['  2. Calcula necessidade liquida (desejado - atual)'],
        ['  3. Converte dias em quantidade (dias x demanda)'],
        ['  4. Ajusta para multiplo de caixa'],
        ['  5. Calcula cobertura real apos pedido'],
        ['  6. Gera relatorio pronto para emissao'],
        ['', ''],
        ['Exemplo:', ''],
        ['  Demanda = 5 un/dia, quer 30 dias, tem 20 em estoque'],
        ['  Cobertura atual = 20/5 = 4 dias'],
        ['  Precisa de 30-4 = 26 dias = 26x5 = 130 unidades'],
        ['  Embalagem = 12, ajusta para 132 (11 caixas)'],
        ['  Cobertura real = (20+132)/5 = 30.4 dias'],
        ['', ''],
        ['Observacao:', ''],
        ['  Se ja tiver cobertura suficiente, quantidade sera ZERO'],
    ]

    df_instrucoes = pd.DataFrame(instrucoes, columns=['Campo', 'Descricao'])

    # Salvar
    caminho = 'exemplo_pedido_cobertura.xlsx'
    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='PEDIDO', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"Criado: {caminho}")
    return caminho


if __name__ == '__main__':
    print("Gerando arquivos de exemplo...")
    print()

    gerar_exemplo_pedido_quantidade()
    gerar_exemplo_pedido_cobertura()

    print()
    print("Arquivos criados com sucesso!")
    print()
    print("Use:")
    print("  - exemplo_pedido_quantidade.xlsx -> Para pedido informando quantidade")
    print("  - exemplo_pedido_cobertura.xlsx -> Para pedido informando cobertura desejada")
