# -*- coding: utf-8 -*-
"""
Teste da ABORDAGEM HÍBRIDA de tratamento de rupturas
Escolhe automaticamente filtrar ou ajustar baseado no % de rupturas
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from core.daily_data_loader import DailyDataLoader
import pandas as pd

print("=" * 80)
print("TESTE: ABORDAGEM HÍBRIDA (Filtrar vs Ajustar Automático)")
print("=" * 80)

arquivo = 'demanda_01-01-2023'

print(f"\n[1] Carregando arquivo: {arquivo}")
print("-" * 80)

loader = DailyDataLoader(arquivo)
df = loader.carregar()

print(f"[OK] Arquivo carregado")
print(f"  - Total de registros: {len(df):,}")
print(f"  - Período: {loader.periodo_inicial.date()} a {loader.periodo_final.date()}")
print(f"  - Filiais: {len(loader.filiais)}")
print(f"  - Produtos: {len(loader.produtos)}")
print(f"  - Tem coluna estoque: {loader.tem_estoque}")

if not loader.tem_estoque:
    print("\n[AVISO] Arquivo não tem coluna estoque_diario. Teste cancelado.")
    sys.exit(0)

# Validar dados
valido, mensagens = loader.validar()
if not valido:
    print(f"\n[ERRO] Dados inválidos")
    for msg in mensagens[:5]:
        print(f"  {msg}")
    sys.exit(1)

print(f"\n[2] Aplicando ABORDAGEM HÍBRIDA")
print("-" * 80)
print("Estratégia: ")
print("  - SKUs com < 20% de rupturas → FILTRAR (rápido)")
print("  - SKUs com >= 20% de rupturas → AJUSTAR (preserva dados)")

# Aplicar abordagem híbrida
df_processado = loader.processar_historico_hibrido(threshold_filtrar=20.0)

print(f"\n[OK] Processamento concluído!")
print(f"  - Total de registros processados: {len(df_processado):,}")

# Gerar resumo
resumo = loader.get_resumo_abordagem_hibrida(df_processado)

print(f"\n[3] RESUMO DA APLICAÇÃO")
print("-" * 80)
print(f"Total de SKUs: {resumo['total_skus']}")
print(f"\nAbordagens aplicadas:")
print(f"  - FILTRAR (< 20% rupturas): {resumo['skus_filtrados']} SKUs")
print(f"  - AJUSTAR (>= 20% rupturas): {resumo['skus_ajustados']} SKUs")
print(f"  - ORIGINAL (sem info estoque): {resumo['skus_originais']} SKUs")

print(f"\nImpacto:")
print(f"  - Registros de rupturas removidos (filtro): {resumo['registros_rupturas_removidos']:,}")
print(f"  - Registros ajustados (demanda estimada): {resumo['registros_ajustados']:,}")
print(f"  - % médio de rupturas: {resumo['pct_rupturas_medio']:.1f}%")

# Analisar por abordagem
print(f"\n[4] ANÁLISE POR ABORDAGEM")
print("-" * 80)

for abordagem in ['filtrar', 'ajustar']:
    df_abordagem = df_processado[df_processado['abordagem'] == abordagem]

    if len(df_abordagem) > 0:
        print(f"\n{abordagem.upper()}:")
        print(f"  - Registros: {len(df_abordagem):,}")

        skus_abordagem = df_abordagem.groupby(['cod_empresa', 'codigo']).first()
        pct_rupturas_medio = skus_abordagem['pct_rupturas'].mean()
        pct_rupturas_min = skus_abordagem['pct_rupturas'].min()
        pct_rupturas_max = skus_abordagem['pct_rupturas'].max()

        print(f"  - SKUs: {len(skus_abordagem)}")
        print(f"  - % rupturas médio: {pct_rupturas_medio:.1f}%")
        print(f"  - % rupturas (min/max): {pct_rupturas_min:.1f}% / {pct_rupturas_max:.1f}%")

        # Comparar vendas originais vs processadas
        vendas_originais = df_abordagem['qtd_venda'].sum()
        vendas_processadas = df_abordagem['qtd_processada'].sum()
        diferenca = vendas_processadas - vendas_originais

        print(f"  - Vendas originais: {vendas_originais:,.0f} unidades")
        print(f"  - Vendas processadas: {vendas_processadas:,.0f} unidades")
        if diferenca != 0:
            pct_dif = (diferenca / vendas_originais * 100) if vendas_originais > 0 else 0
            print(f"  - Diferença: {diferenca:+,.0f} unidades ({pct_dif:+.1f}%)")

# Exemplos de SKUs
print(f"\n[5] EXEMPLOS DE SKUs POR ABORDAGEM")
print("-" * 80)

skus_info = df_processado.groupby(['cod_empresa', 'codigo']).agg({
    'abordagem': 'first',
    'pct_rupturas': 'first'
}).reset_index()

# 3 exemplos de cada abordagem
for abordagem in ['filtrar', 'ajustar']:
    skus_abordagem = skus_info[skus_info['abordagem'] == abordagem]

    if len(skus_abordagem) > 0:
        print(f"\n{abordagem.upper()} (3 exemplos):")
        for idx, row in skus_abordagem.head(3).iterrows():
            print(f"  Filial {row['cod_empresa']:2d} | Produto {row['codigo']:6d} | "
                  f"Rupturas: {row['pct_rupturas']:5.1f}%")

print("\n" + "=" * 80)
print("[OK] TESTE CONCLUÍDO")
print("=" * 80)
print("""
VANTAGENS DA ABORDAGEM HÍBRIDA:

1. AUTOMÁTICA: Não precisa decidir manualmente qual abordagem usar
2. OTIMIZADA: Usa filtro (rápido) quando possível, ajuste quando necessário
3. INTELIGENTE: Adapta-se ao padrão de cada produto
4. EFICIENTE: Economiza processamento em produtos com poucas rupturas
5. PRECISA: Preserva dados em produtos com rupturas frequentes

RESULTADO:
- Melhor qualidade de previsão
- Processamento mais rápido
- Sem intervenção manual necessária
""")
