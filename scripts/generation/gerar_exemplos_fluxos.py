#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera arquivos de exemplo para cada tipo de fluxo separadamente
"""

import pandas as pd
from datetime import datetime, timedelta

def gerar_historico_vendas(skus=None, lojas=None):
    """
    Gera histórico de vendas (comum para todos os fluxos)
    """
    data_inicio = datetime(2024, 1, 1)
    dados_vendas = []

    # Usar SKUs e lojas padrão se não especificado
    if skus is None:
        skus = [f'PROD_{str(i).zfill(3)}' for i in range(1, 101)]  # 100 SKUs padrão
    if lojas is None:
        lojas = ['LOJA_01', 'LOJA_02', 'LOJA_03', 'LOJA_04', 'LOJA_05']

    for mes in range(12):
        data = data_inicio + timedelta(days=30 * mes)
        for sku in skus:
            for loja in lojas:
                # Simular vendas com sazonalidade e variação por produto
                sku_num = int(sku.split('_')[1])
                base = 50 + (sku_num % 50) + (mes * 5)  # Tendência crescente
                sazonalidade = 20 if mes in [10, 11] else 0  # Nov/Dez
                variacao = (hash(sku + loja) % 40) - 20  # Variação entre -20 e +20
                vendas = max(10, base + sazonalidade + variacao)  # Mínimo 10 vendas

                dados_vendas.append({
                    'Loja': loja,
                    'SKU': sku,
                    'Mes': mes + 1,
                    'Vendas': int(vendas)
                })

    return pd.DataFrame(dados_vendas)


def gerar_exemplo_pedido_fornecedor():
    """
    Gera exemplo para pedidos ao fornecedor
    3 fornecedores com SKUs distribuídos (total 100 SKUs - mesmo do CD)
    Isso cria relacionamento entre fornecedor e CD
    """
    print("Gerando exemplo_pedido_fornecedor.xlsx...")

    # Dados do pedido - 3 fornecedores compartilhando 100 SKUs
    dados_fornecedor = []

    # Distribuir 100 SKUs entre 3 fornecedores
    # FORNECEDOR_A: SKUs 001-034 (34 SKUs)
    # FORNECEDOR_B: SKUs 035-067 (33 SKUs)
    # FORNECEDOR_C: SKUs 068-100 (33 SKUs)

    fornecedores = [
        ('FORNECEDOR_A', range(1, 35)),    # 34 SKUs
        ('FORNECEDOR_B', range(35, 68)),   # 33 SKUs
        ('FORNECEDOR_C', range(68, 101))   # 33 SKUs
    ]

    # Todos pedidos vão para CDs (que depois distribuem para lojas)
    cds = ['CD_PRINCIPAL', 'CD_REGIONAL']

    for fornecedor, sku_range in fornecedores:
        for sku_num in sku_range:
            sku = f'PROD_{str(sku_num).zfill(3)}'

            # Alternar entre CDs
            cd = cds[sku_num % len(cds)]

            # Parâmetros variam por fornecedor
            if fornecedor == 'FORNECEDOR_A':
                lead_time = 12 + (sku_num % 5)
                lote_minimo = 200 + (sku_num % 4) * 50
                multiplo_palete = 240
                multiplo_carreta = 4800
                custo_unitario = 8.50 + (sku_num % 8)
                custo_frete = 140.00
            elif fornecedor == 'FORNECEDOR_B':
                lead_time = 15 + (sku_num % 6)
                lote_minimo = 150 + (sku_num % 5) * 40
                multiplo_palete = 200
                multiplo_carreta = 4000
                custo_unitario = 9.00 + (sku_num % 10)
                custo_frete = 160.00
            else:  # FORNECEDOR_C
                lead_time = 10 + (sku_num % 4)
                lote_minimo = 180 + (sku_num % 3) * 60
                multiplo_palete = 220
                multiplo_carreta = 4400
                custo_unitario = 7.50 + (sku_num % 9)
                custo_frete = 150.00

            # Estoque do CD para este SKU
            estoque_disp = (sku_num * 100) + 500

            dados_fornecedor.append({
                'Fornecedor': fornecedor,
                'SKU': sku,
                'Destino': cd,
                'Tipo_Destino': 'CD',
                'Lead_Time_Dias': lead_time,
                'Ciclo_Pedido_Dias': 30,  # Ciclo padrão para fornecedor→CD
                'Lote_Minimo': lote_minimo,
                'Multiplo_Palete': multiplo_palete,
                'Multiplo_Carreta': multiplo_carreta,
                'Custo_Unitario': round(custo_unitario, 2),
                'Custo_Frete_Palete': round(custo_frete, 2),
                'Estoque_Disponivel': estoque_disp,
                'Estoque_Transito': 0
            })

    df_fornecedor = pd.DataFrame(dados_fornecedor)

    # Gerar histórico para os 100 SKUs - MESMAS 5 lojas do CD
    # Isso permite agregar demanda das lojas para calcular pedido ao CD
    skus_fornecedor = [f'PROD_{str(i).zfill(3)}' for i in range(1, 101)]
    lojas = ['LOJA_01', 'LOJA_02', 'LOJA_03', 'LOJA_04', 'LOJA_05']

    df_historico = gerar_historico_vendas(skus=skus_fornecedor, lojas=lojas)

    # Instruções
    instrucoes = [
        ['INSTRUCOES - PEDIDOS AO FORNECEDOR', ''],
        ['', ''],
        ['Objetivo:', 'Calcular pedidos otimizados para compra de fornecedores'],
        ['', ''],
        ['Colunas OBRIGATORIAS:', ''],
        ['  Fornecedor', 'Nome do fornecedor'],
        ['  SKU', 'Codigo do produto'],
        ['  Destino', 'Para onde vai (CD_PRINCIPAL ou LOJA_01)'],
        ['  Tipo_Destino', 'Tipo (CD ou LOJA)'],
        ['  Lead_Time_Dias', 'Tempo de entrega do fornecedor'],
        ['  Ciclo_Pedido_Dias', 'Frequencia de pedido (30=CD, 14=Loja)'],
        ['  Lote_Minimo', 'Quantidade minima que o fornecedor aceita'],
        ['  Multiplo_Palete', 'Unidades por palete'],
        ['  Multiplo_Carreta', 'Unidades por carreta'],
        ['  Custo_Unitario', 'Preco unitario do produto'],
        ['', ''],
        ['Aba HISTORICO_VENDAS:', 'Obrigatoria - historico de vendas das lojas'],
        ['', ''],
        ['O que o sistema faz:', ''],
        ['  1. Calcula demanda prevista com base no historico'],
        ['  2. Define nivel de servico automaticamente (ABC)'],
        ['     - Classe A (>500 un/mes): 98% servico'],
        ['     - Classe B (100-500 un/mes): 95% servico'],
        ['     - Classe C (<100 un/mes): 90% servico'],
        ['  3. Ajusta para multiplos de palete/carreta'],
        ['  4. Calcula custos totais (produto + frete)'],
        ['  5. Gera relatorio com quantidade otimizada'],
    ]

    df_instrucoes = pd.DataFrame(instrucoes, columns=['Campo', 'Descricao'])

    # Salvar
    caminho = 'exemplo_pedido_fornecedor.xlsx'
    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df_fornecedor.to_excel(writer, sheet_name='PEDIDOS_FORNECEDOR', index=False)
        df_historico.to_excel(writer, sheet_name='HISTORICO_VENDAS', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"[OK] Criado: {caminho}")


def gerar_exemplo_pedido_cd():
    """
    Gera exemplo para pedidos CD → Lojas
    ~100 SKUs distribuídos para múltiplas lojas
    """
    print("Gerando exemplo_pedido_cd.xlsx...")

    # Dados do pedido - 100 SKUs para 5 lojas (500 registros total)
    dados_cd = []

    lojas = ['LOJA_01', 'LOJA_02', 'LOJA_03', 'LOJA_04', 'LOJA_05']
    cds = ['CD_PRINCIPAL', 'CD_REGIONAL']

    for sku_num in range(1, 101):  # 100 SKUs
        sku = f'PROD_{str(sku_num).zfill(3)}'

        for idx, loja in enumerate(lojas):
            # Alternar entre CDs
            cd = cds[sku_num % len(cds)]

            # Variar parâmetros
            lead_time = 1 + (sku_num % 3)
            ciclo = 2 + (idx % 2)

            # Estoque no CD varia - alguns com estoque baixo para gerar alertas
            if sku_num % 15 == 0:
                estoque_cd = 50 + (sku_num % 100)  # Baixo estoque
            else:
                estoque_cd = 1000 + (sku_num * 50)  # Estoque normal

            # Configuração de gôndola
            estoque_min = 8 + (sku_num % 12)
            num_frentes = 2 + (idx % 4)

            # Custo de transferência
            custo_transf = 3.00 + (idx % 5) * 0.50

            # Estoque atual da loja (varia)
            estoque_loja = (sku_num * 5) + (idx * 10)

            dados_cd.append({
                'CD_Origem': cd,
                'Loja_Destino': loja,
                'SKU': sku,
                'Lead_Time_Dias': lead_time,
                'Ciclo_Pedido_Dias': ciclo,
                'Estoque_CD': estoque_cd,
                'Estoque_Disponivel_Loja': estoque_loja,
                'Estoque_Min_Gondola': estoque_min,
                'Numero_Frentes': num_frentes,
                'Custo_Transferencia': round(custo_transf, 2)
            })

    df_cd = pd.DataFrame(dados_cd)

    # Gerar histórico para os 100 SKUs
    skus_cd = [f'PROD_{str(i).zfill(3)}' for i in range(1, 101)]
    df_historico = gerar_historico_vendas(skus=skus_cd, lojas=lojas)

    # Instruções
    instrucoes = [
        ['INSTRUCOES - PEDIDOS CD PARA LOJAS', ''],
        ['', ''],
        ['Objetivo:', 'Calcular distribuicao do CD para as lojas'],
        ['', ''],
        ['Colunas OBRIGATORIAS:', ''],
        ['  CD_Origem', 'Nome do Centro de Distribuicao'],
        ['  Loja_Destino', 'Nome da loja que vai receber'],
        ['  SKU', 'Codigo do produto'],
        ['  Lead_Time_Dias', 'Tempo de transporte (normalmente 1-2 dias)'],
        ['  Ciclo_Pedido_Dias', 'Frequencia de pedido (2-3 dias)'],
        ['  Estoque_CD', 'Quantidade disponivel no CD'],
        ['  Estoque_Min_Gondola', 'Estoque minimo para exposicao'],
        ['  Numero_Frentes', 'Numero de frentes de gondola'],
        ['  Custo_Transferencia', 'Custo de transferencia por unidade'],
        ['', ''],
        ['Aba HISTORICO_VENDAS:', 'Obrigatoria - historico de vendas das lojas'],
        ['', ''],
        ['O que o sistema faz:', ''],
        ['  1. Calcula demanda de curto prazo'],
        ['  2. Define nivel de servico automaticamente (ABC)'],
        ['     - Classe A (>500 un/mes): 98% servico'],
        ['     - Classe B (100-500 un/mes): 95% servico'],
        ['     - Classe C (<100 un/mes): 90% servico'],
        ['  3. Valida se o CD tem estoque suficiente'],
        ['  4. Garante estoque minimo de gondola'],
        ['  5. Gera alertas se CD nao tem produto'],
    ]

    df_instrucoes = pd.DataFrame(instrucoes, columns=['Campo', 'Descricao'])

    # Salvar
    caminho = 'exemplo_pedido_cd.xlsx'
    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df_cd.to_excel(writer, sheet_name='PEDIDOS_CD', index=False)
        df_historico.to_excel(writer, sheet_name='HISTORICO_VENDAS', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"[OK] Criado: {caminho}")


def gerar_exemplo_transferencias():
    """
    Gera exemplo para transferências entre lojas
    ~10 SKUs com oportunidades de transferência
    """
    print("Gerando exemplo_transferencias.xlsx...")

    # Dados de transferência - 10 SKUs com cenários variados
    dados_transf = []

    lojas = ['LOJA_01', 'LOJA_02', 'LOJA_03', 'LOJA_04', 'LOJA_05']

    cenarios = [
        # (sku, origem, destino, estoque_origem, estoque_destino, demanda_origem, demanda_destino, custo_produto)
        ('PROD_001', 'LOJA_02', 'LOJA_01', 150, 5, 5.0, 8.0, 12.50),    # Urgência ALTA - origem c/ excesso, destino c/ falta
        ('PROD_002', 'LOJA_03', 'LOJA_02', 120, 8, 4.0, 10.0, 10.00),   # Urgência ALTA - alta demanda destino
        ('PROD_003', 'LOJA_04', 'LOJA_01', 90, 15, 3.0, 6.0, 15.75),    # Urgência MEDIA - demanda moderada
        ('PROD_004', 'LOJA_05', 'LOJA_03', 100, 12, 4.5, 7.0, 9.50),    # Urgência MEDIA
        ('PROD_005', 'LOJA_01', 'LOJA_04', 80, 20, 3.5, 4.0, 11.00),    # Urgência BAIXA - destino c/ estoque razoável
        ('PROD_006', 'LOJA_02', 'LOJA_05', 70, 18, 2.5, 5.0, 13.25),    # Urgência BAIXA
        ('PROD_007', 'LOJA_03', 'LOJA_01', 110, 6, 4.0, 9.0, 8.90),     # Urgência ALTA - destino c/ estoque baixo
        ('PROD_008', 'LOJA_04', 'LOJA_02', 95, 14, 3.0, 5.5, 14.50),    # Urgência MEDIA
        ('PROD_009', 'LOJA_05', 'LOJA_03', 130, 4, 5.0, 11.0, 16.00),   # Urgência ALTA - alta demanda destino
        ('PROD_010', 'LOJA_01', 'LOJA_05', 85, 22, 3.0, 3.5, 12.00),    # Urgência BAIXA - baixa demanda
    ]

    for sku, origem, destino, est_origem, est_destino, dem_origem, dem_destino, custo_prod in cenarios:
        # Custo de transferência varia com distância (simulado)
        distancia_idx = abs(int(origem.split('_')[1]) - int(destino.split('_')[1]))
        custo_transf = 8.00 + (distancia_idx * 2.00)

        dados_transf.append({
            'Loja_Origem': origem,
            'Loja_Destino': destino,
            'SKU': sku,
            'Lead_Time_Dias': 1,
            'Estoque_Origem': est_origem,
            'Estoque_Destino': est_destino,
            'Demanda_Diaria_Origem': dem_origem,
            'Demanda_Diaria_Destino': dem_destino,
            'Custo_Transferencia': round(custo_transf, 2),
            'Custo_Unitario_Produto': custo_prod,
            'Nivel_Servico': 0.95
        })

    df_transf = pd.DataFrame(dados_transf)

    # Gerar histórico apenas para os 10 SKUs de transferência
    skus_transf = [f'PROD_{str(i).zfill(3)}' for i in range(1, 11)]
    df_historico = gerar_historico_vendas(skus=skus_transf, lojas=lojas)

    # Instruções
    instrucoes = [
        ['INSTRUCOES - TRANSFERENCIAS ENTRE LOJAS', ''],
        ['', ''],
        ['Objetivo:', 'Identificar oportunidades de transferencia entre lojas'],
        ['', ''],
        ['Colunas OBRIGATORIAS:', ''],
        ['  Loja_Origem', 'Loja que tem excesso de estoque'],
        ['  Loja_Destino', 'Loja que precisa de estoque'],
        ['  SKU', 'Codigo do produto'],
        ['  Lead_Time_Dias', 'Tempo de transferencia (normalmente 1 dia)'],
        ['  Estoque_Origem', 'Quantidade disponivel na origem'],
        ['  Estoque_Destino', 'Quantidade disponivel no destino'],
        ['  Demanda_Diaria_Origem', 'Demanda diaria media na loja origem'],
        ['  Demanda_Diaria_Destino', 'Demanda diaria media na loja destino'],
        ['  Custo_Transferencia', 'Custo da transferencia'],
        ['  Custo_Unitario_Produto', 'Custo do produto (para calcular economia)'],
        ['  Nivel_Servico', 'Nivel de servico desejado (0.95 = 95%)'],
        ['', ''],
        ['Aba HISTORICO_VENDAS:', 'Obrigatoria - historico de vendas das lojas'],
        ['', ''],
        ['O que o sistema faz:', ''],
        ['  1. Identifica se origem tem excesso'],
        ['  2. Identifica se destino precisa'],
        ['  3. Calcula viabilidade economica'],
        ['  4. Prioriza por urgencia (ALTA, MEDIA, BAIXA)'],
        ['  5. Recomenda apenas transferencias viaveis'],
    ]

    df_instrucoes = pd.DataFrame(instrucoes, columns=['Campo', 'Descricao'])

    # Salvar
    caminho = 'exemplo_transferencias.xlsx'
    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df_transf.to_excel(writer, sheet_name='TRANSFERENCIAS', index=False)
        df_historico.to_excel(writer, sheet_name='HISTORICO_VENDAS', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"[OK] Criado: {caminho}")


if __name__ == '__main__':
    print("============================================================")
    print("  GERADOR DE EXEMPLOS - FLUXOS SEPARADOS")
    print("============================================================\n")

    gerar_exemplo_pedido_fornecedor()
    gerar_exemplo_pedido_cd()
    gerar_exemplo_transferencias()

    print("\n[OK] Todos os arquivos de exemplo foram criados!")
    print("\nArquivos gerados:")
    print("  - exemplo_pedido_fornecedor.xlsx")
    print("  - exemplo_pedido_cd.xlsx")
    print("  - exemplo_transferencias.xlsx")
