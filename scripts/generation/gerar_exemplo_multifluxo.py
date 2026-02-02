#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera arquivo de exemplo para Reabastecimento Multifluxo
Versão 3.0 - Abas separadas por tipo de fluxo
"""

import pandas as pd
from datetime import datetime, timedelta
import random

def gerar_exemplo_multifluxo():
    """
    Gera exemplo completo com múltiplos fluxos:
    - PEDIDOS_FORNECEDOR: Compras de fornecedor
    - PEDIDOS_CD: Distribuição CD → Loja
    - TRANSFERENCIAS: Transferências Loja ↔ Loja
    - HISTORICO_VENDAS: Histórico compartilhado
    """

    # ============================================================
    # ABA 1: PEDIDOS_FORNECEDOR
    # ============================================================

    dados_fornecedor = [
        # CD comprando de Fornecedor (ciclo mensal, consolidação de carga)
        {
            'Fornecedor': 'FORN_A',
            'SKU': 'PROD_001',
            'Destino': 'CD_PRINCIPAL',
            'Tipo_Destino': 'CD',
            'Lead_Time_Dias': 15,
            'Ciclo_Pedido_Dias': 30,  # Mensal
            'Lote_Minimo': 24,
            'Multiplo_Palete': 240,  # 10 caixas por palete
            'Multiplo_Carreta': 4800,  # 20 paletes por carreta
            'Custo_Unitario': 10.50,
            'Custo_Frete': 500.00,
            'Estoque_Disponivel': 5000,
            'Estoque_Transito': 2000,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.95,
            'Capacidade_Max_Armazenamento': 50000
        },
        {
            'Fornecedor': 'FORN_A',
            'SKU': 'PROD_002',
            'Destino': 'CD_PRINCIPAL',
            'Tipo_Destino': 'CD',
            'Lead_Time_Dias': 15,
            'Ciclo_Pedido_Dias': 30,
            'Lote_Minimo': 12,
            'Multiplo_Palete': 120,
            'Multiplo_Carreta': 0,  # Não usa carreta (combina com outros)
            'Custo_Unitario': 8.00,
            'Custo_Frete': 500.00,
            'Estoque_Disponivel': 3000,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.95
        },
        # Loja MEGA comprando direto de Fornecedor (quinzenal)
        {
            'Fornecedor': 'FORN_B',
            'SKU': 'PROD_003',
            'Destino': 'LOJA_MEGA',
            'Tipo_Destino': 'LOJA',
            'Lead_Time_Dias': 10,
            'Ciclo_Pedido_Dias': 14,  # Quinzenal
            'Lote_Minimo': 12,
            'Multiplo_Palete': 144,
            'Multiplo_Carreta': 0,
            'Custo_Unitario': 15.00,
            'Custo_Frete': 200.00,
            'Estoque_Disponivel': 200,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.98
        },
    ]

    df_fornecedor = pd.DataFrame(dados_fornecedor)

    # ============================================================
    # ABA 2: PEDIDOS_CD
    # ============================================================

    dados_cd = [
        # Lojas pedindo do CD (ciclo curto, parâmetros de exposição)
        {
            'CD_Origem': 'CD_PRINCIPAL',
            'Loja_Destino': 'LOJA_01',
            'SKU': 'PROD_001',
            'Lead_Time_Dias': 2,
            'Ciclo_Pedido_Dias': 2,  # 2-3x semana
            'Lote_Minimo': 6,
            'Estoque_Disponivel_Loja': 50,
            'Estoque_Disponivel_CD': 5000,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.99,  # Alto para lojas
            'Estoque_Min_Gondola': 12,
            'Numero_Frentes': 3,
            'Capacidade_Max_Loja': 500
        },
        {
            'CD_Origem': 'CD_PRINCIPAL',
            'Loja_Destino': 'LOJA_02',
            'SKU': 'PROD_001',
            'Lead_Time_Dias': 3,
            'Ciclo_Pedido_Dias': 3,
            'Lote_Minimo': 6,
            'Estoque_Disponivel_Loja': 30,
            'Estoque_Disponivel_CD': 5000,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 20,
            'Nivel_Servico': 0.99,
            'Estoque_Min_Gondola': 12,
            'Numero_Frentes': 2,
            'Capacidade_Max_Loja': 400
        },
        {
            'CD_Origem': 'CD_PRINCIPAL',
            'Loja_Destino': 'LOJA_03',
            'SKU': 'PROD_002',
            'Lead_Time_Dias': 2,
            'Ciclo_Pedido_Dias': 2,
            'Lote_Minimo': 10,
            'Estoque_Disponivel_Loja': 15,
            'Estoque_Disponivel_CD': 3000,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.95,
            'Estoque_Min_Gondola': 10,
            'Numero_Frentes': 2,
            'Capacidade_Max_Loja': 300
        },
        {
            'CD_Origem': 'CD_PRINCIPAL',
            'Loja_Destino': 'LOJA_04',
            'SKU': 'PROD_001',
            'Lead_Time_Dias': 2,
            'Ciclo_Pedido_Dias': 2,
            'Lote_Minimo': 6,
            'Estoque_Disponivel_Loja': 5,
            'Estoque_Disponivel_CD': 5000,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.99,
            'Estoque_Min_Gondola': 12,
            'Numero_Frentes': 1,
            'Capacidade_Max_Loja': 200
        },
    ]

    df_cd = pd.DataFrame(dados_cd)

    # ============================================================
    # ABA 3: TRANSFERENCIAS
    # ============================================================

    dados_transferencias = [
        # Transferências identificadas entre lojas
        {
            'Loja_Origem': 'LOJA_02',
            'Loja_Destino': 'LOJA_01',
            'SKU': 'PROD_001',
            'Lead_Time_Dias': 1,
            'Estoque_Origem': 80,
            'Estoque_Destino': 5,
            'Demanda_Diaria_Origem': 3.0,
            'Demanda_Diaria_Destino': 8.0,
            'Custo_Transferencia': 0.50,
            'Distancia_Km': 15
        },
        {
            'Loja_Origem': 'LOJA_03',
            'Loja_Destino': 'LOJA_04',
            'SKU': 'PROD_002',
            'Lead_Time_Dias': 1,
            'Estoque_Origem': 60,
            'Estoque_Destino': 10,
            'Demanda_Diaria_Origem': 2.5,
            'Demanda_Diaria_Destino': 5.0,
            'Custo_Transferencia': 0.40,
            'Distancia_Km': 10
        },
    ]

    df_transferencias = pd.DataFrame(dados_transferencias)

    # ============================================================
    # ABA 4: HISTORICO_VENDAS (Compartilhado)
    # ============================================================

    # Gerar 12 meses de histórico
    data_fim = datetime.now()
    dados_vendas = []

    # PROD_001 - Alto giro, demanda estável
    lojas_prod001 = ['CD_PRINCIPAL', 'LOJA_01', 'LOJA_02', 'LOJA_04']
    demandas_prod001 = {
        'CD_PRINCIPAL': (2800, 3200),  # 3000/mês média
        'LOJA_01': (110, 130),         # 120/mês
        'LOJA_02': (70, 90),           # 80/mês
        'LOJA_04': (50, 70)            # 60/mês
    }

    for loja in lojas_prod001:
        min_val, max_val = demandas_prod001[loja]
        for i in range(12):
            mes = (data_fim - timedelta(days=30*i)).strftime('%Y-%m')
            dados_vendas.append({
                'Loja': loja,
                'SKU': 'PROD_001',
                'Mes': mes,
                'Vendas': random.randint(min_val, max_val),
                'Dias_Com_Estoque': 30,
                'Origem': 'Sistema'
            })

    # PROD_002 - Médio giro com tendência crescente
    lojas_prod002 = ['CD_PRINCIPAL', 'LOJA_03']
    demandas_prod002 = {
        'CD_PRINCIPAL': (1800, 2200),  # 2000/mês média
        'LOJA_03': (55, 75)            # 65/mês
    }

    for loja in lojas_prod002:
        min_val, max_val = demandas_prod002[loja]
        for i in range(12):
            mes = (data_fim - timedelta(days=30*i)).strftime('%Y-%m')
            # Tendência crescente: +2% por mês
            fator = 1 + (11 - i) * 0.02
            base_min = int(min_val * fator)
            base_max = int(max_val * fator)
            dados_vendas.append({
                'Loja': loja,
                'SKU': 'PROD_002',
                'Mes': mes,
                'Vendas': random.randint(base_min, base_max),
                'Dias_Com_Estoque': 30,
                'Origem': 'Sistema'
            })

    # PROD_003 - Produto da LOJA_MEGA com sazonalidade
    for i in range(12):
        mes = (data_fim - timedelta(days=30*i)).strftime('%Y-%m')
        mes_num = int(mes.split('-')[1])

        # Sazonalidade: picos em dezembro e junho
        if mes_num in [12, 1, 6, 7]:
            vendas = random.randint(80, 100)
        elif mes_num in [3, 4, 9, 10]:
            vendas = random.randint(20, 40)
        else:
            vendas = random.randint(50, 70)

        dados_vendas.append({
            'Loja': 'LOJA_MEGA',
            'SKU': 'PROD_003',
            'Mes': mes,
            'Vendas': vendas,
            'Dias_Com_Estoque': 30,
            'Origem': 'Sistema'
        })

    df_vendas = pd.DataFrame(dados_vendas)
    df_vendas = df_vendas.sort_values(['Loja', 'SKU', 'Mes'])

    # ============================================================
    # ABA 5: INSTRUCOES
    # ============================================================

    instrucoes = [
        ['INSTRUÇÕES - REABASTECIMENTO MULTIFLUXO (v3.0)', ''],
        ['', ''],
        ['NOVIDADE - Versão 3.0:', 'Abas separadas por tipo de fluxo!'],
        ['', ''],
        ['Este arquivo contém 4 abas principais:', ''],
        ['', ''],
        ['1. PEDIDOS_FORNECEDOR', 'Compras de fornecedor (para CD ou Lojas)'],
        ['   - Origem: Fornecedor', ''],
        ['   - Destino: CD ou Loja', ''],
        ['   - Ciclo: 30 dias (CD) ou 14 dias (Loja)', ''],
        ['   - Consolidação: Palete/Carreta (apenas CD)', ''],
        ['', ''],
        ['2. PEDIDOS_CD', 'Distribuição CD → Loja'],
        ['   - Origem: Centro de Distribuição', ''],
        ['   - Destino: Loja', ''],
        ['   - Ciclo: 2-3 dias (pedidos frequentes)', ''],
        ['   - Exposição: Valida estoque mínimo de gôndola', ''],
        ['', ''],
        ['3. TRANSFERENCIAS', 'Transferências Loja ↔ Loja'],
        ['   - Balanceamento de estoque entre lojas', ''],
        ['   - Identifica excesso em uma e necessidade em outra', ''],
        ['   - Calcula viabilidade econômica', ''],
        ['', ''],
        ['4. HISTORICO_VENDAS', 'Histórico compartilhado (obrigatório)'],
        ['   - Usado por todos os fluxos', ''],
        ['   - Calcula demanda automaticamente', ''],
        ['', ''],
        ['CAMPOS IMPORTANTES:', ''],
        ['', ''],
        ['Tipo_Destino (PEDIDOS_FORNECEDOR):', ''],
        ['   CD   - Centro de Distribuição (ciclo 30 dias)', ''],
        ['   LOJA - Loja (ciclo 14 dias)', ''],
        ['', ''],
        ['Multiplo_Palete / Multiplo_Carreta:', ''],
        ['   Apenas para CD (consolidação de carga)', ''],
        ['   Ajusta quantidade para economizar frete', ''],
        ['', ''],
        ['Estoque_Min_Gondola / Numero_Frentes:', ''],
        ['   Apenas para Lojas (parâmetros de exposição)', ''],
        ['   Garante estoque mínimo na área de vendas', ''],
        ['', ''],
        ['Nivel_Servico:', ''],
        ['   0.99 (99%) - Produtos A / Lojas', ''],
        ['   0.95 (95%) - Produtos B / CD', ''],
        ['   0.90 (90%) - Produtos C', ''],
        ['', ''],
        ['COMO USAR:', ''],
        ['', ''],
        ['1. Preencha as abas que você precisa', ''],
        ['   - Não é obrigatório preencher todas', ''],
        ['   - HISTORICO_VENDAS é sempre obrigatório', ''],
        ['', ''],
        ['2. Faça upload na tela de Reabastecimento v3.0', ''],
        ['', ''],
        ['3. Sistema processa cada aba separadamente', ''],
        ['   - Gera relatório específico por tipo', ''],
        ['   - Download individual de cada relatório', ''],
        ['', ''],
        ['RESULTADO:', ''],
        ['', ''],
        ['- pedido_fornecedor_YYYYMMDD.xlsx', ''],
        ['  Aba 1: PEDIDOS (todos os itens)', ''],
        ['  Aba 2: CONSOLIDACAO (por fornecedor)', ''],
        ['', ''],
        ['- pedido_cd_lojas_YYYYMMDD.xlsx', ''],
        ['  Aba 1: PEDIDOS (todos os itens)', ''],
        ['  Aba 2: ALERTAS_CD (CD insuficiente)', ''],
        ['', ''],
        ['- transferencias_YYYYMMDD.xlsx', ''],
        ['  Aba 1: TRANSFERENCIAS (oportunidades)', ''],
        ['', ''],
        ['BENEFÍCIOS:', ''],
        ['', ''],
        ['- Cada fluxo tem campos específicos', ''],
        ['- Validações adequadas ao contexto', ''],
        ['- Relatórios separados por tipo', ''],
        ['- Interface intuitiva e organizada', ''],
    ]

    df_instrucoes = pd.DataFrame(instrucoes, columns=['Campo', 'Descrição'])

    # ============================================================
    # SALVAR ARQUIVO
    # ============================================================

    caminho = 'exemplo_reabastecimento_multifluxo.xlsx'

    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df_fornecedor.to_excel(writer, sheet_name='PEDIDOS_FORNECEDOR', index=False)
        df_cd.to_excel(writer, sheet_name='PEDIDOS_CD', index=False)
        df_transferencias.to_excel(writer, sheet_name='TRANSFERENCIAS', index=False)
        df_vendas.to_excel(writer, sheet_name='HISTORICO_VENDAS', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"[OK] Criado: {caminho}")
    print()
    print("Estrutura do arquivo:")
    print("  - Aba 1: PEDIDOS_FORNECEDOR (3 itens)")
    print("  - Aba 2: PEDIDOS_CD (4 itens)")
    print("  - Aba 3: TRANSFERENCIAS (2 oportunidades)")
    print("  - Aba 4: HISTORICO_VENDAS (12 meses)")
    print("  - Aba 5: INSTRUCOES")
    print()
    print("Fluxos exemplo:")
    print("  - CD comprando de fornecedor (ciclo 30 dias)")
    print("  - Loja MEGA comprando direto (ciclo 14 dias)")
    print("  - 4 lojas pedindo do CD (ciclo 2-3 dias)")
    print("  - 2 transferências entre lojas")

    return caminho


if __name__ == '__main__':
    print("=" * 60)
    print("  GERADOR DE EXEMPLO - MULTIFLUXO v3.0")
    print("=" * 60)
    print()

    gerar_exemplo_multifluxo()

    print()
    print("Arquivo pronto para uso!")
    print("Faça upload na tela de Reabastecimento Inteligente v3.0")
