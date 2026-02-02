# -*- coding: utf-8 -*-
"""
Teste rápido com amostra de dados (primeiros 10k registros)
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd

print("=" * 80)
print("TESTE RÁPIDO: Funcionalidades de Estoque (Amostra)")
print("=" * 80)

# Carregar apenas uma amostra para teste rápido
arquivo = 'demanda_01-01-2023'

print(f"\n[1] Carregando amostra do arquivo: {arquivo}")
print("-" * 80)

df = pd.read_csv(arquivo, nrows=10000, low_memory=False)
df['data'] = pd.to_datetime(df['data'])

print(f"[OK] Amostra carregada: {len(df):,} registros")
print(f"  - Período: {df['data'].min().date()} a {df['data'].max().date()}")
print(f"  - Filiais: {df['cod_empresa'].nunique()}")
print(f"  - Produtos: {df['codigo'].nunique()}")

# Verificar coluna estoque
if 'estoque_diario' in df.columns:
    registros_com_estoque = df['estoque_diario'].notna().sum()
    pct_preenchido = (registros_com_estoque / len(df)) * 100
    print(f"  - Registros com estoque: {registros_com_estoque:,} ({pct_preenchido:.1f}%)")

    # Detectar rupturas na amostra
    print(f"\n[2] Detectando rupturas na amostra")
    print("-" * 80)

    df_rupturas = df[
        (df['qtd_venda'] == 0) &
        (df['estoque_diario'] == 0)
    ]

    print(f"[OK] Rupturas detectadas: {len(df_rupturas):,}")

    if len(df_rupturas) > 0:
        print(f"\nExemplos de rupturas:")
        for idx, row in df_rupturas.head(5).iterrows():
            print(f"  {row['data'].date()} | Filial {row['cod_empresa']} | Produto {row['codigo']}")

    # Análise de estoque
    print(f"\n[3] Análise de estoque")
    print("-" * 80)

    df_com_estoque = df[df['estoque_diario'].notna()]

    if len(df_com_estoque) > 0:
        dias_com_estoque = (df_com_estoque['estoque_diario'] > 0).sum()
        dias_em_ruptura = (df_com_estoque['estoque_diario'] == 0).sum()
        taxa_disponibilidade = (dias_com_estoque / len(df_com_estoque)) * 100

        print(f"  - Dias com estoque > 0: {dias_com_estoque:,}")
        print(f"  - Dias em ruptura (estoque = 0): {dias_em_ruptura:,}")
        print(f"  - Taxa de disponibilidade: {taxa_disponibilidade:.1f}%")
        print(f"  - Estoque médio: {df_com_estoque['estoque_diario'].mean():.1f} unidades")
        print(f"  - Estoque máximo: {df_com_estoque['estoque_diario'].max():.0f} unidades")

    # Análise de vendas
    print(f"\n[4] Análise de vendas")
    print("-" * 80)

    vendas_totais = df['qtd_venda'].sum()
    dias_com_venda = (df['qtd_venda'] > 0).sum()
    dias_sem_venda = (df['qtd_venda'] == 0).sum()

    print(f"  - Vendas totais: {vendas_totais:,.0f} unidades")
    print(f"  - Dias com venda: {dias_com_venda:,}")
    print(f"  - Dias sem venda: {dias_sem_venda:,}")

    # Cruzamento: sem venda COM estoque vs sem venda SEM estoque
    if 'estoque_diario' in df.columns:
        df_sem_venda = df[df['qtd_venda'] == 0]
        df_sem_venda_com_info_estoque = df_sem_venda[df_sem_venda['estoque_diario'].notna()]

        if len(df_sem_venda_com_info_estoque) > 0:
            sem_venda_com_estoque = (df_sem_venda_com_info_estoque['estoque_diario'] > 0).sum()
            sem_venda_sem_estoque = (df_sem_venda_com_info_estoque['estoque_diario'] == 0).sum()

            print(f"\n  Dias sem venda (com info de estoque: {len(df_sem_venda_com_info_estoque):,}):")
            print(f"    - Com estoque disponível: {sem_venda_com_estoque:,} (sem demanda)")
            print(f"    - Sem estoque (RUPTURA): {sem_venda_sem_estoque:,} (demanda perdida!)")

else:
    print("[AVISO] Coluna estoque_diario não encontrada")

print("\n" + "=" * 80)
print("[OK] TESTE CONCLUÍDO")
print("=" * 80)
