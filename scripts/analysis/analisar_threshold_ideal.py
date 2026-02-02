# -*- coding: utf-8 -*-
"""
Análise: Qual é o THRESHOLD IDEAL para os seus dados reais?
Testa diferentes thresholds (5%, 10%, 15%, 20%, 25%, 30%) e compara resultados
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np

print("=" * 80)
print("ANÁLISE: Qual o THRESHOLD IDEAL para seus dados?")
print("=" * 80)

arquivo = 'demanda_01-01-2023'

print(f"\n[1] Carregando e analisando dados reais")
print("-" * 80)

# Carregar dados
df = pd.read_csv(arquivo, low_memory=False)
df['data'] = pd.to_datetime(df['data'])

print(f"Arquivo: {arquivo}")
print(f"Registros: {len(df):,}")

# Analisar distribuição de rupturas por SKU
print(f"\n[2] Calculando % de rupturas por SKU")
print("-" * 80)

estatisticas = []

for (filial, produto), grupo in df.groupby(['cod_empresa', 'codigo']):
    # Apenas registros com info de estoque
    grupo_com_estoque = grupo[grupo['estoque_diario'].notna()]

    if len(grupo_com_estoque) == 0:
        continue

    # Contar rupturas
    rupturas = ((grupo_com_estoque['qtd_venda'] == 0) &
                (grupo_com_estoque['estoque_diario'] == 0)).sum()

    pct_rupturas = (rupturas / len(grupo_com_estoque)) * 100

    estatisticas.append({
        'cod_empresa': filial,
        'codigo': produto,
        'dias_com_info': len(grupo_com_estoque),
        'dias_ruptura': rupturas,
        'pct_rupturas': pct_rupturas
    })

df_stats = pd.DataFrame(estatisticas)

print(f"SKUs analisados: {len(df_stats)}")
print(f"\n% de Rupturas - Estatísticas Descritivas:")
print(df_stats['pct_rupturas'].describe())

# Distribuição por faixas
print(f"\n[3] Distribuição de SKUs por % de rupturas")
print("-" * 80)

faixas = [
    (0, 5, "0-5%"),
    (5, 10, "5-10%"),
    (10, 15, "10-15%"),
    (15, 20, "15-20%"),
    (20, 25, "20-25%"),
    (25, 30, "25-30%"),
    (30, 40, "30-40%"),
    (40, 50, "40-50%"),
    (50, 100, ">50%")
]

print(f"\n{'Faixa':>12} | {'Qtd SKUs':>10} | {'%':>8} | Barra")
print("-" * 80)

total_skus = len(df_stats)
for min_val, max_val, label in faixas:
    count = ((df_stats['pct_rupturas'] >= min_val) &
             (df_stats['pct_rupturas'] < max_val)).sum()
    pct = (count / total_skus) * 100
    barra = '█' * int(pct / 2)  # Cada █ = 2%
    print(f"{label:>12} | {count:>10} | {pct:>7.1f}% | {barra}")

# Teste de diferentes thresholds
print(f"\n[4] Testando diferentes THRESHOLDS")
print("=" * 80)

thresholds = [5, 10, 15, 20, 25, 30]

resultados = []

for threshold in thresholds:
    # Contar quantos SKUs seriam filtrados vs ajustados
    skus_filtrar = (df_stats['pct_rupturas'] < threshold).sum()
    skus_ajustar = (df_stats['pct_rupturas'] >= threshold).sum()

    pct_filtrar = (skus_filtrar / total_skus) * 100
    pct_ajustar = (skus_ajustar / total_skus) * 100

    # Calcular economia de processamento
    # Assumindo: filtrar = 1x, ajustar = 10x mais lento
    custo_processamento = (skus_filtrar * 1) + (skus_ajustar * 10)
    custo_relativo = custo_processamento / (total_skus * 10)  # vs ajustar tudo
    economia = (1 - custo_relativo) * 100

    # Calcular % médio de rupturas em cada grupo
    if skus_filtrar > 0:
        pct_medio_filtrados = df_stats[df_stats['pct_rupturas'] < threshold]['pct_rupturas'].mean()
    else:
        pct_medio_filtrados = 0

    if skus_ajustar > 0:
        pct_medio_ajustados = df_stats[df_stats['pct_rupturas'] >= threshold]['pct_rupturas'].mean()
    else:
        pct_medio_ajustados = 0

    resultados.append({
        'threshold': threshold,
        'skus_filtrar': skus_filtrar,
        'pct_filtrar': pct_filtrar,
        'pct_medio_filtrados': pct_medio_filtrados,
        'skus_ajustar': skus_ajustar,
        'pct_ajustar': pct_ajustar,
        'pct_medio_ajustados': pct_medio_ajustados,
        'economia_processamento': economia
    })

df_resultados = pd.DataFrame(resultados)

print(f"\nComparação de Thresholds:\n")
print(f"{'Threshold':>10} | {'Filtrar':>8} | {'% Filt':>7} | {'Avg%':>6} | {'Ajustar':>8} | {'% Ajust':>8} | {'Avg%':>6} | {'Economia':>9}")
print("-" * 110)

for _, row in df_resultados.iterrows():
    print(f"{row['threshold']:>9}% | {row['skus_filtrar']:>8} | {row['pct_filtrar']:>6.1f}% | "
          f"{row['pct_medio_filtrados']:>5.1f}% | {row['skus_ajustar']:>8} | {row['pct_ajustar']:>7.1f}% | "
          f"{row['pct_medio_ajustados']:>5.1f}% | {row['economia_processamento']:>8.1f}%")

# Análise de qualidade
print(f"\n[5] ANÁLISE DE QUALIDADE POR THRESHOLD")
print("=" * 80)

print("""
CRITÉRIOS DE AVALIAÇÃO:

1. ECONOMIA DE PROCESSAMENTO:
   - Maior economia = mais SKUs filtrados (rápido)
   - Meta: > 60% de economia

2. QUALIDADE DOS FILTRADOS:
   - % médio de rupturas dos SKUs filtrados
   - Ideal: < 10% (poucas rupturas, ok filtrar)

3. QUALIDADE DOS AJUSTADOS:
   - % médio de rupturas dos SKUs ajustados
   - Ideal: > 20% (muitas rupturas, precisa ajustar)

4. BALANCEAMENTO:
   - Evitar extremos (quase tudo filtrado ou quase tudo ajustado)
   - Ideal: 70-90% filtrados, 10-30% ajustados
""")

# Recomendar melhor threshold
print(f"\n[6] RECOMENDAÇÃO")
print("=" * 80)

# Critérios para escolher o melhor threshold:
# 1. % médio de rupturas dos filtrados deve ser < 10%
# 2. % médio de rupturas dos ajustados deve ser > 20%
# 3. Economia deve ser > 60%
# 4. % filtrados deve estar entre 70-90%

pontuacoes = []

for _, row in df_resultados.iterrows():
    pontos = 0

    # Critério 1: Filtrados têm poucas rupturas
    if row['pct_medio_filtrados'] < 10:
        pontos += 40
    elif row['pct_medio_filtrados'] < 15:
        pontos += 20

    # Critério 2: Ajustados têm muitas rupturas
    if row['pct_medio_ajustados'] > 25:
        pontos += 30
    elif row['pct_medio_ajustados'] > 20:
        pontos += 20
    elif row['pct_medio_ajustados'] > 15:
        pontos += 10

    # Critério 3: Boa economia
    if row['economia_processamento'] > 70:
        pontos += 20
    elif row['economia_processamento'] > 60:
        pontos += 15
    elif row['economia_processamento'] > 50:
        pontos += 10

    # Critério 4: Balanceamento
    if 70 <= row['pct_filtrar'] <= 90:
        pontos += 10
    elif 60 <= row['pct_filtrar'] <= 95:
        pontos += 5

    pontuacoes.append(pontos)

df_resultados['pontuacao'] = pontuacoes

# Ordenar por pontuação
df_resultados_sorted = df_resultados.sort_values('pontuacao', ascending=False)

melhor = df_resultados_sorted.iloc[0]

print(f"\nRANKING de Thresholds (por adequação aos dados):\n")
print(f"{'Posição':>8} | {'Threshold':>10} | {'Pontuação':>10} | Análise")
print("-" * 80)

for i, (_, row) in enumerate(df_resultados_sorted.iterrows(), 1):
    analise = []
    if row['pct_medio_filtrados'] < 10:
        analise.append("✓ Filtrados OK")
    if row['pct_medio_ajustados'] > 20:
        analise.append("✓ Ajustados OK")
    if row['economia_processamento'] > 60:
        analise.append("✓ Boa economia")

    if i == 1:
        simbolo = "🏆"
    elif i == 2:
        simbolo = "🥈"
    elif i == 3:
        simbolo = "🥉"
    else:
        simbolo = "  "

    print(f"{simbolo} {i:>5} | {row['threshold']:>9}% | {row['pontuacao']:>10.0f} | {', '.join(analise)}")

print(f"\n{'=' * 80}")
print(f"RECOMENDAÇÃO FINAL")
print(f"{'=' * 80}")

print(f"""
Baseado na análise dos SEUS DADOS REAIS:

🏆 MELHOR THRESHOLD: {melhor['threshold']:.0f}%

Motivos:
  - {melhor['skus_filtrar']:.0f} SKUs ({melhor['pct_filtrar']:.1f}%) serão FILTRADOS
    → % médio de rupturas: {melhor['pct_medio_filtrados']:.1f}%
    → {'✓ ÓTIMO' if melhor['pct_medio_filtrados'] < 10 else '⚠ ACEITÁVEL' if melhor['pct_medio_filtrados'] < 15 else '✗ ALTO'} para filtrar

  - {melhor['skus_ajustar']:.0f} SKUs ({melhor['pct_ajustar']:.1f}%) serão AJUSTADOS
    → % médio de rupturas: {melhor['pct_medio_ajustados']:.1f}%
    → {'✓ ÓTIMO' if melhor['pct_medio_ajustados'] > 20 else '⚠ ACEITÁVEL' if melhor['pct_medio_ajustados'] > 15 else '✗ BAIXO'} para ajustar

  - Economia de processamento: {melhor['economia_processamento']:.1f}%
    → {'✓ EXCELENTE' if melhor['economia_processamento'] > 70 else '✓ BOA' if melhor['economia_processamento'] > 60 else '⚠ MODERADA'}

  - Balanceamento: {melhor['pct_filtrar']:.1f}% filtrados / {melhor['pct_ajustar']:.1f}% ajustados
    → {'✓ IDEAL' if 70 <= melhor['pct_filtrar'] <= 90 else '⚠ ACEITÁVEL'}

PONTUAÇÃO: {melhor['pontuacao']:.0f}/100 pontos
""")

# Se 20% não foi o melhor
if melhor['threshold'] != 20:
    threshold_20 = df_resultados[df_resultados['threshold'] == 20].iloc[0]
    print(f"\nCOMPARAÇÃO: Threshold atual (20%) vs Recomendado ({melhor['threshold']:.0f}%):")
    print(f"  Economia: {threshold_20['economia_processamento']:.1f}% → {melhor['economia_processamento']:.1f}% ({melhor['economia_processamento'] - threshold_20['economia_processamento']:+.1f}%)")
    print(f"  SKUs filtrados: {threshold_20['pct_filtrar']:.1f}% → {melhor['pct_filtrar']:.1f}% ({melhor['pct_filtrar'] - threshold_20['pct_filtrar']:+.1f}%)")

print(f"\n{'=' * 80}")
