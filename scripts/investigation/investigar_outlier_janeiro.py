# -*- coding: utf-8 -*-
"""
Investigação: Outlier de Janeiro e Impacto na Previsão Semanal
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Backend não-interativo
import matplotlib.pyplot as plt

print("=" * 80)
print("   INVESTIGAÇÃO: OUTLIER DE JANEIRO E TENDÊNCIA")
print("=" * 80)
print()

# Conectar ao banco
conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)

# 1. DADOS HISTÓRICOS MENSAIS
print("1️⃣  DADOS HISTÓRICOS MENSAIS")
print("-" * 80)

query_mensal = """
    SELECT
        DATE_TRUNC('month', h.data) as data,
        SUM(h.qtd_venda) as qtd_venda
    FROM historico_vendas_diario h
    WHERE h.data >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY DATE_TRUNC('month', h.data)
    ORDER BY DATE_TRUNC('month', h.data)
"""

df_mensal = pd.read_sql(query_mensal, conn)
df_mensal['data'] = pd.to_datetime(df_mensal['data'])
df_mensal.set_index('data', inplace=True)

print(f"Períodos mensais: {len(df_mensal)}")
print()

# Identificar outliers mensais usando IQR
Q1 = df_mensal['qtd_venda'].quantile(0.25)
Q3 = df_mensal['qtd_venda'].quantile(0.75)
IQR = Q3 - Q1
limite_inferior = Q1 - 1.5 * IQR
limite_superior = Q3 + 1.5 * IQR

outliers_mensais = df_mensal[(df_mensal['qtd_venda'] < limite_inferior) |
                              (df_mensal['qtd_venda'] > limite_superior)]

print(f"📊 Estatísticas mensais:")
print(f"   Média: {df_mensal['qtd_venda'].mean():,.0f}")
print(f"   Q1: {Q1:,.0f}  |  Q3: {Q3:,.0f}")
print(f"   IQR: {IQR:,.0f}")
print(f"   Limite inferior: {limite_inferior:,.0f}")
print(f"   Limite superior: {limite_superior:,.0f}")
print()

if len(outliers_mensais) > 0:
    print(f"🔴 OUTLIERS MENSAIS DETECTADOS: {len(outliers_mensais)}")
    for data, row in outliers_mensais.iterrows():
        desvio = ((row['qtd_venda'] / df_mensal['qtd_venda'].mean()) - 1) * 100
        print(f"   {data.strftime('%Y-%m')}: {row['qtd_venda']:>10,.0f}  ({desvio:+.1f}% da média)")
    print()
else:
    print("✅ Nenhum outlier mensal detectado")
    print()

# Mostrar últimos 6 meses em detalhe
print("📅 Últimos 6 meses (histórico):")
ultimos_6 = df_mensal.tail(6)
for data, row in ultimos_6.iterrows():
    print(f"   {data.strftime('%Y-%m')}: {row['qtd_venda']:>10,.0f}")
print()

# 2. DADOS HISTÓRICOS SEMANAIS
print("2️⃣  DADOS HISTÓRICOS SEMANAIS")
print("-" * 80)

query_semanal = """
    WITH dados_diarios AS (
        SELECT
            h.data,
            SUM(h.qtd_venda) as qtd_venda
        FROM historico_vendas_diario h
        WHERE h.data >= CURRENT_DATE - INTERVAL '2 years'
        GROUP BY h.data
    )
    SELECT
        DATE_TRUNC('week', data)::date as data,
        SUM(qtd_venda) as qtd_venda
    FROM dados_diarios
    GROUP BY DATE_TRUNC('week', data)
    ORDER BY DATE_TRUNC('week', data)
"""

df_semanal = pd.read_sql(query_semanal, conn)
df_semanal['data'] = pd.to_datetime(df_semanal['data'])
df_semanal.set_index('data', inplace=True)

print(f"Períodos semanais: {len(df_semanal)}")
print()

# Identificar outliers semanais
Q1_sem = df_semanal['qtd_venda'].quantile(0.25)
Q3_sem = df_semanal['qtd_venda'].quantile(0.75)
IQR_sem = Q3_sem - Q1_sem
limite_inferior_sem = Q1_sem - 1.5 * IQR_sem
limite_superior_sem = Q3_sem + 1.5 * IQR_sem

outliers_semanais = df_semanal[(df_semanal['qtd_venda'] < limite_inferior_sem) |
                                (df_semanal['qtd_venda'] > limite_superior_sem)]

print(f"📊 Estatísticas semanais:")
print(f"   Média: {df_semanal['qtd_venda'].mean():,.0f}")
print(f"   Q1: {Q1_sem:,.0f}  |  Q3: {Q3_sem:,.0f}")
print(f"   IQR: {IQR_sem:,.0f}")
print(f"   Limite inferior: {limite_inferior_sem:,.0f}")
print(f"   Limite superior: {limite_superior_sem:,.0f}")
print()

if len(outliers_semanais) > 0:
    print(f"🔴 OUTLIERS SEMANAIS DETECTADOS: {len(outliers_semanais)}")
    for data, row in outliers_semanais.iterrows():
        desvio = ((row['qtd_venda'] / df_semanal['qtd_venda'].mean()) - 1) * 100
        semana_ano = data.isocalendar()[1]
        print(f"   S{semana_ano:>2} ({data.strftime('%Y-%m-%d')}): {row['qtd_venda']:>10,.0f}  ({desvio:+.1f}% da média)")
    print()
else:
    print("✅ Nenhum outlier semanal detectado")
    print()

# 3. FOCO EM JANEIRO
print("3️⃣  ANÁLISE ESPECÍFICA: JANEIRO")
print("-" * 80)

# Pegar todas as semanas de janeiro nos dados históricos
df_semanal_jan = df_semanal[df_semanal.index.month == 1]

if len(df_semanal_jan) > 0:
    print(f"Semanas de Janeiro no histórico: {len(df_semanal_jan)}")
    print()

    for data, row in df_semanal_jan.iterrows():
        semana_ano = data.isocalendar()[1]
        desvio = ((row['qtd_venda'] / df_semanal['qtd_venda'].mean()) - 1) * 100

        # Marcar se é outlier
        marcador = ""
        if row['qtd_venda'] < limite_inferior_sem or row['qtd_venda'] > limite_superior_sem:
            marcador = "🔴 OUTLIER"

        print(f"   S{semana_ano:>2} ({data.strftime('%Y-%m-%d')}): {row['qtd_venda']:>10,.0f}  ({desvio:+6.1f}%)  {marcador}")

    print()

    # Comparar janeiro com outros meses
    media_janeiro = df_semanal_jan['qtd_venda'].mean()
    media_geral = df_semanal['qtd_venda'].mean()
    diferenca_jan = ((media_janeiro / media_geral) - 1) * 100

    print(f"Média semanal de Janeiro: {media_janeiro:,.0f}")
    print(f"Média semanal geral:      {media_geral:,.0f}")
    print(f"Diferença:                {diferenca_jan:+.1f}%")
    print()

    if abs(diferenca_jan) > 15:
        print(f"⚠️  JANEIRO TEM DEMANDA {'MUITO BAIXA' if diferenca_jan < 0 else 'MUITO ALTA'}")
        print(f"   Isso PODE estar afetando drasticamente a previsão semanal!")
    else:
        print("✅ Janeiro tem demanda dentro da normalidade")
else:
    print("❌ Nenhuma semana de Janeiro encontrada no histórico")

print()

# 4. TENDÊNCIA
print("4️⃣  ANÁLISE DE TENDÊNCIA")
print("-" * 80)

# Calcular tendência mensal
indices_mensais = np.arange(len(df_mensal))
coef_mensal = np.polyfit(indices_mensais, df_mensal['qtd_venda'], 1)
tendencia_mensal = coef_mensal[0]
tendencia_mensal_pct = (tendencia_mensal / df_mensal['qtd_venda'].mean()) * 100

print(f"Tendência mensal:")
print(f"   Slope: {tendencia_mensal:+,.2f} unidades/mês")
print(f"   Percentual: {tendencia_mensal_pct:+.2f}%/mês")
print()

# Calcular tendência semanal
indices_semanais = np.arange(len(df_semanal))
coef_semanal = np.polyfit(indices_semanais, df_semanal['qtd_venda'], 1)
tendencia_semanal = coef_semanal[0]
tendencia_semanal_pct = (tendencia_semanal / df_semanal['qtd_venda'].mean()) * 100

print(f"Tendência semanal:")
print(f"   Slope: {tendencia_semanal:+,.2f} unidades/semana")
print(f"   Percentual: {tendencia_semanal_pct:+.2f}%/semana")
print()

# Projetar tendência para 6 meses
projecao_mensal_6m = df_mensal['qtd_venda'].iloc[-1] + (tendencia_mensal * 6)
projecao_semanal_24s = df_semanal['qtd_venda'].iloc[-1] + (tendencia_semanal * 24)

print(f"Projeção baseada APENAS em tendência linear:")
print(f"   Mensal (6 meses):    {projecao_mensal_6m * 6:,.0f}")
print(f"   Semanal (24 semanas): {projecao_semanal_24s * 24:,.0f}")
print()

diferenca_tendencia = ((projecao_mensal_6m * 6) - (projecao_semanal_24s * 24))
pct_diferenca_tendencia = (diferenca_tendencia / (projecao_mensal_6m * 6)) * 100

print(f"Diferença: {diferenca_tendencia:+,.0f} ({pct_diferenca_tendencia:+.1f}%)")
print()

# 5. DIAGNÓSTICO FINAL
print("=" * 80)
print("🩺 DIAGNÓSTICO FINAL")
print("=" * 80)
print()

print("FATORES INVESTIGADOS:")
print()

print(f"1. Outliers Mensais:  {len(outliers_mensais)} detectados")
print(f"2. Outliers Semanais: {len(outliers_semanais)} detectados")
print(f"3. Janeiro anômalo:   {'SIM' if abs(diferenca_jan) > 15 else 'NÃO'}")
print(f"4. Tendência:         {tendencia_mensal_pct:+.2f}%/mês (mensal) vs {tendencia_semanal_pct:+.2f}%/semana (semanal)")
print()

if tendencia_semanal < -100:  # Queda significativa
    print("🔴 PROBLEMA IDENTIFICADO: TENDÊNCIA DE QUEDA FORTE NA SÉRIE SEMANAL")
    print(f"   A série semanal está com tendência de -{abs(tendencia_semanal):,.0f} unidades/semana")
    print(f"   Isso equivale a ~{tendencia_semanal*4:,.0f} unidades/mês")
    print()
    print("   🚨 ISSO PODE EXPLICAR A QUEDA NA PREVISÃO SEMANAL!")
    print()
    print("   Possíveis causas:")
    print("   - Outliers recentes muito baixos puxando a tendência para baixo")
    print("   - Dados do final de dezembro/início de janeiro com vendas baixas")
    print("   - Problema na agregação semanal capturando mais ruído")

conn.close()

print()
print("=" * 80)
