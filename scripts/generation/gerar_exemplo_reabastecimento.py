#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera arquivo de exemplo para Reabastecimento Automático
"""

import pandas as pd
from datetime import datetime, timedelta
import random

def gerar_exemplo_reabastecimento():
    """
    Gera exemplo completo para reabastecimento automático
    Inclui duas abas: ESTOQUE_ATUAL e HISTORICO_VENDAS
    """

    # ============================================================
    # ABA 1: ESTOQUE_ATUAL
    # ============================================================

    dados_estoque = [
        {
            'Loja': 'LOJA_01',
            'SKU': 'PROD_001',
            'Lead_Time_Dias': 7,
            'Estoque_Disponivel': 150,
            'Estoque_Transito': 50,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.99,  # 99% - Produto A (alto giro)
            'Lote_Minimo': 12
        },
        {
            'Loja': 'LOJA_01',
            'SKU': 'PROD_002',
            'Lead_Time_Dias': 10,
            'Estoque_Disponivel': 80,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.95,  # 95% - Produto B (médio giro)
            'Lote_Minimo': 10
        },
        {
            'Loja': 'LOJA_01',
            'SKU': 'PROD_003',
            'Lead_Time_Dias': 14,
            'Estoque_Disponivel': 25,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.90,  # 90% - Produto C (baixo giro)
            'Lote_Minimo': 6
        },
        {
            'Loja': 'LOJA_02',
            'SKU': 'PROD_001',
            'Lead_Time_Dias': 7,
            'Estoque_Disponivel': 200,
            'Estoque_Transito': 100,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.99,  # 99% - Produto A
            'Lote_Minimo': 12
        },
        {
            'Loja': 'LOJA_02',
            'SKU': 'PROD_002',
            'Lead_Time_Dias': 10,
            'Estoque_Disponivel': 50,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 30,
            'Nivel_Servico': 0.95,  # 95% - Produto B
            'Lote_Minimo': 10
        },
        {
            'Loja': 'LOJA_02',
            'SKU': 'PROD_004',
            'Lead_Time_Dias': 5,
            'Estoque_Disponivel': 10,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.98,  # 98% - Item crítico
            'Lote_Minimo': 24
        },
    ]

    df_estoque = pd.DataFrame(dados_estoque)

    # ============================================================
    # ABA 2: HISTORICO_VENDAS
    # ============================================================

    # Gerar 12 meses de histórico
    data_fim = datetime.now()
    dados_vendas = []

    # PROD_001 - Alto giro, demanda estável (~120/mês)
    for i in range(12):
        mes = (data_fim - timedelta(days=30*i)).strftime('%Y-%m')
        dados_vendas.append({
            'Loja': 'LOJA_01',
            'SKU': 'PROD_001',
            'Mes': mes,
            'Vendas': random.randint(110, 130)
        })
        dados_vendas.append({
            'Loja': 'LOJA_02',
            'SKU': 'PROD_001',
            'Mes': mes,
            'Vendas': random.randint(140, 160)
        })

    # PROD_002 - Médio giro com tendência crescente
    for i in range(12):
        mes = (data_fim - timedelta(days=30*i)).strftime('%Y-%m')
        base = 60 + (11-i) * 3  # Crescimento de 3 un/mês
        dados_vendas.append({
            'Loja': 'LOJA_01',
            'SKU': 'PROD_002',
            'Mes': mes,
            'Vendas': base + random.randint(-5, 5)
        })
        dados_vendas.append({
            'Loja': 'LOJA_02',
            'SKU': 'PROD_002',
            'Mes': mes,
            'Vendas': base + random.randint(-5, 5) + 10
        })

    # PROD_003 - Baixo giro, demanda intermitente
    for i in range(12):
        mes = (data_fim - timedelta(days=30*i)).strftime('%Y-%m')
        # 40% de chance de venda zero
        vendas = 0 if random.random() < 0.4 else random.randint(10, 25)
        dados_vendas.append({
            'Loja': 'LOJA_01',
            'SKU': 'PROD_003',
            'Mes': mes,
            'Vendas': vendas
        })

    # PROD_004 - Produto com sazonalidade (só LOJA_02)
    for i in range(12):
        mes = (data_fim - timedelta(days=30*i)).strftime('%Y-%m')
        mes_num = int(mes.split('-')[1])
        # Pico em dez (12) e jun (6), baixa em mar (3) e set (9)
        if mes_num in [12, 1, 6, 7]:
            vendas = random.randint(80, 100)
        elif mes_num in [3, 4, 9, 10]:
            vendas = random.randint(20, 40)
        else:
            vendas = random.randint(50, 70)

        dados_vendas.append({
            'Loja': 'LOJA_02',
            'SKU': 'PROD_004',
            'Mes': mes,
            'Vendas': vendas
        })

    df_vendas = pd.DataFrame(dados_vendas)
    df_vendas = df_vendas.sort_values(['Loja', 'SKU', 'Mes'])

    # ============================================================
    # ABA 3: INSTRUCOES
    # ============================================================

    instrucoes = [
        ['INSTRUÇÕES - REABASTECIMENTO AUTOMÁTICO', ''],
        ['', ''],
        ['Objetivo:', 'Calcular ponto de pedido e quantidade de reabastecimento automaticamente'],
        ['', ''],
        ['Este arquivo possui 2 abas principais:', ''],
        ['', ''],
        ['ABA 1: ESTOQUE_ATUAL', ''],
        ['  Contém a situação atual de estoque de cada item', ''],
        ['', ''],
        ['Colunas OBRIGATÓRIAS:', ''],
        ['  Loja', 'Código da loja'],
        ['  SKU', 'Código do produto'],
        ['  Lead_Time_Dias', 'Tempo de reposição em dias'],
        ['  Estoque_Disponivel', 'Estoque físico atual'],
        ['  Nivel_Servico', 'Nível de serviço desejado (0.90 a 0.99)'],
        ['', ''],
        ['Colunas OPCIONAIS:', ''],
        ['  Estoque_Transito', 'Estoque em trânsito (padrão: 0)'],
        ['  Pedidos_Abertos', 'Pedidos em aberto (padrão: 0)'],
        ['  Lote_Minimo', 'Lote mínimo de compra (padrão: 1)'],
        ['', ''],
        ['IMPORTANTE - Nível de Serviço:', ''],
        ['  0.99 (99%)', 'Produtos A - Alto giro, críticos'],
        ['  0.95 (95%)', 'Produtos B - Médio giro, importantes'],
        ['  0.90 (90%)', 'Produtos C - Baixo giro, menos críticos'],
        ['', ''],
        ['ABA 2: HISTORICO_VENDAS', ''],
        ['  Contém o histórico de vendas para cálculo automático de demanda', ''],
        ['', ''],
        ['Colunas OBRIGATÓRIAS:', ''],
        ['  Loja', 'Código da loja'],
        ['  SKU', 'Código do produto'],
        ['  Mes', 'Mês no formato YYYY-MM (ex: 2024-01)'],
        ['  Vendas', 'Quantidade vendida no mês'],
        ['', ''],
        ['Recomendações:', ''],
        ['  • Mínimo de 6 meses de histórico'],
        ['  • Ideal: 12 a 24 meses'],
        ['  • Dados mais recentes têm maior peso'],
        ['', ''],
        ['O que o sistema faz:', ''],
        ['  1. Analisa padrão de demanda de cada item'],
        ['  2. Escolhe método estatístico mais adequado'],
        ['  3. Calcula demanda média e variabilidade'],
        ['  4. Calcula estoque de segurança (baseado em Nivel_Servico)'],
        ['  5. Calcula ponto de pedido'],
        ['  6. Determina quantidade ideal de reabastecimento'],
        ['  7. Identifica itens com risco de ruptura'],
        ['', ''],
        ['Métodos utilizados automaticamente:', ''],
        ['  • SMA - Demanda estável'],
        ['  • WMA - Demanda com mudanças graduais'],
        ['  • EMA - Demanda com tendência suave'],
        ['  • Regressão - Demanda com tendência clara'],
        ['  • Sazonal - Demanda com padrões sazonais'],
        ['  • TSB - Demanda intermitente (muitos zeros)'],
        ['', ''],
        ['Resultado:', ''],
        ['  Excel com análise completa incluindo:', ''],
        ['  • Ponto de pedido calculado'],
        ['  • Quantidade a pedir'],
        ['  • Cobertura de estoque em dias'],
        ['  • Alertas de ruptura'],
        ['  • Método utilizado por item'],
    ]

    df_instrucoes = pd.DataFrame(instrucoes, columns=['Campo', 'Descrição'])

    # ============================================================
    # SALVAR ARQUIVO
    # ============================================================

    caminho = 'exemplo_reabastecimento_automatico.xlsx'

    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df_estoque.to_excel(writer, sheet_name='ESTOQUE_ATUAL', index=False)
        df_vendas.to_excel(writer, sheet_name='HISTORICO_VENDAS', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"[OK] Criado: {caminho}")
    print()
    print("Estrutura do arquivo:")
    print("  - Aba 1: ESTOQUE_ATUAL (6 itens)")
    print("  - Aba 2: HISTORICO_VENDAS (12 meses)")
    print("  - Aba 3: INSTRUCOES")
    print()
    print("Niveis de Servico no exemplo:")
    print("  - 99% - Produtos A (alto giro)")
    print("  - 95% - Produtos B (medio giro)")
    print("  - 90% - Produtos C (baixo giro)")
    print("  - 98% - Itens criticos")

    return caminho


if __name__ == '__main__':
    print("=" * 60)
    print("  GERADOR DE ARQUIVO EXEMPLO - REABASTECIMENTO")
    print("=" * 60)
    print()

    gerar_exemplo_reabastecimento()

    print()
    print("Arquivo pronto para uso!")
    print("Faça upload na tela de Reabastecimento Inteligente")
