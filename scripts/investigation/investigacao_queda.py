# -*- coding: utf-8 -*-
"""
Investigação detalhada: Por que a previsão está -20% abaixo?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 80)
print("   INVESTIGAÇÃO: POR QUE A PREVISÃO ESTÁ -20% ABAIXO?")
print("=" * 80)
print()

# Conectar ao banco
conn = psycopg2.connect(
    host="localhost",
    database="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    port=5432
)

cursor = conn.cursor(cursor_factory=RealDictCursor)

# Buscar dados históricos mensais de Alimentos
query = """
    SELECT
        DATE_TRUNC('month', h.data) as data,
        SUM(h.qtd_venda) as qtd_venda
    FROM historico_vendas_diario h
    JOIN cadastro_produtos p ON h.codigo = p.codigo
    WHERE h.data >= CURRENT_DATE - INTERVAL '2 years'
      AND p.categoria = 'Alimentos'
    GROUP BY DATE_TRUNC('month', h.data)
    ORDER BY DATE_TRUNC('month', h.data)
"""

cursor.execute(query)
dados = cursor.fetchall()
cursor.close()
conn.close()

# Converter para DataFrame
df = pd.DataFrame(dados)
df['data'] = pd.to_datetime(df['data'])
df['qtd_venda'] = df['qtd_venda'].astype(float)
df = df.sort_values('data')

print(f"Total de períodos: {len(df)}")
print()

# Aplicar divisão 50/25/25
total_periodos = len(df)
tamanho_base = int(total_periodos * 0.50)  # 12 períodos
tamanho_teste = int(total_periodos * 0.25)  # 6 períodos
# Restante é para comparação futura

df_base = df.iloc[:tamanho_base].copy()
df_teste = df.iloc[tamanho_base:tamanho_base + tamanho_teste].copy()
df_futuro = df.iloc[tamanho_base + tamanho_teste:].copy()

print("=" * 80)
print("1. DIVISÃO DOS DADOS")
print("=" * 80)
print(f"\nBASE (50% - {len(df_base)} períodos):")
print(f"  Data início: {df_base['data'].min().strftime('%Y-%m')}")
print(f"  Data fim: {df_base['data'].max().strftime('%Y-%m')}")
print(f"  Média: {df_base['qtd_venda'].mean():,.2f}")
print(f"  Total: {df_base['qtd_venda'].sum():,.2f}")

print(f"\nTESTE (25% - {len(df_teste)} períodos):")
print(f"  Data início: {df_teste['data'].min().strftime('%Y-%m')}")
print(f"  Data fim: {df_teste['data'].max().strftime('%Y-%m')}")
print(f"  Média: {df_teste['qtd_venda'].mean():,.2f}")
print(f"  Total: {df_teste['qtd_venda'].sum():,.2f}")
print(f"  Variação vs Base: {((df_teste['qtd_venda'].mean() - df_base['qtd_venda'].mean()) / df_base['qtd_venda'].mean() * 100):+.2f}%")

print(f"\nFUTURO/VALIDAÇÃO ({len(df_futuro)} períodos):")
print(f"  Data início: {df_futuro['data'].min().strftime('%Y-%m')}")
print(f"  Data fim: {df_futuro['data'].max().strftime('%Y-%m')}")
print(f"  Média: {df_futuro['qtd_venda'].mean():,.2f}")
print(f"  Total: {df_futuro['qtd_venda'].sum():,.2f}")
print(f"  Variação vs Base: {((df_futuro['qtd_venda'].mean() - df_base['qtd_venda'].mean()) / df_base['qtd_venda'].mean() * 100):+.2f}%")

print()
print("=" * 80)
print("2. ANÁLISE DO ANO ANTERIOR (YoY)")
print("=" * 80)

# Buscar os mesmos meses do ano anterior aos períodos futuros
data_inicio_futuro = df_futuro['data'].min()
data_fim_futuro = df_futuro['data'].max()

# Calcular datas do ano anterior
data_inicio_ano_ant = data_inicio_futuro - timedelta(days=365)
data_fim_ano_ant = data_fim_futuro - timedelta(days=365)

print(f"\nPeríodo FUTURO: {data_inicio_futuro.strftime('%Y-%m')} a {data_fim_futuro.strftime('%Y-%m')}")
print(f"Mesmo período ANO ANTERIOR: {data_inicio_ano_ant.strftime('%Y-%m')} a {data_fim_ano_ant.strftime('%Y-%m')}")

# Buscar dados do ano anterior
df_ano_anterior = df[(df['data'] >= data_inicio_ano_ant) & (df['data'] <= data_fim_ano_ant)].copy()

if len(df_ano_anterior) > 0:
    print(f"\nDados encontrados do ano anterior: {len(df_ano_anterior)} períodos")
    print(f"  Total ano anterior: {df_ano_anterior['qtd_venda'].sum():,.2f}")
    print(f"  Média ano anterior: {df_ano_anterior['qtd_venda'].mean():,.2f}")

    print(f"\n  Total futuro (real): {df_futuro['qtd_venda'].sum():,.2f}")
    print(f"  Média futuro (real): {df_futuro['qtd_venda'].mean():,.2f}")

    variacao_yoy = ((df_futuro['qtd_venda'].sum() - df_ano_anterior['qtd_venda'].sum()) / df_ano_anterior['qtd_venda'].sum() * 100)
    print(f"\n  Variação YoY REAL: {variacao_yoy:+.2f}%")

print()
print("=" * 80)
print("3. SIMULAÇÃO DA PREVISÃO (Suavização Exponencial Simples)")
print("=" * 80)

# Simular SES manualmente
alpha = 0.3
serie_base = df_base['qtd_venda'].tolist()

# Treinar na base
nivel = serie_base[0]
for valor in serie_base:
    nivel = alpha * valor + (1 - alpha) * nivel

print(f"\nNível final após treinar na BASE: {nivel:,.2f}")
print(f"Previsão constante (sem ajuste sazonal): {nivel:,.2f}")

# Comparar com ano anterior
print(f"\nComparação:")
print(f"  Previsão SES (constante): {nivel:,.2f}")
print(f"  Média ano anterior: {df_ano_anterior['qtd_venda'].mean():,.2f}")
print(f"  Diferença: {((nivel - df_ano_anterior['qtd_venda'].mean()) / df_ano_anterior['qtd_venda'].mean() * 100):+.2f}%")

print()
print("=" * 80)
print("4. ANÁLISE DE SAZONALIDADE")
print("=" * 80)

# Calcular índices sazonais em TODOS os dados
df['mes'] = df['data'].dt.month
media_geral = df['qtd_venda'].mean()

print(f"\nMédia geral de todos os dados: {media_geral:,.2f}")
print("\nÍndices sazonais por mês:")

indices_sazonais = {}
for mes in range(1, 13):
    dados_mes = df[df['mes'] == mes]['qtd_venda']
    if len(dados_mes) > 0:
        media_mes = dados_mes.mean()
        indice = media_mes / media_geral
        indices_sazonais[mes] = indice
        variacao_pct = (indice - 1) * 100
        print(f"  Mês {mes:2d}: Índice={indice:.3f} ({variacao_pct:+.1f}%)")

print()
print("=" * 80)
print("5. APLICANDO AJUSTE SAZONAL NA PREVISÃO")
print("=" * 80)

# Aplicar ajuste sazonal nos períodos futuros
previsoes_ajustadas = []
print(f"\nNível base (sem ajuste): {nivel:,.2f}")
print("\nPrevisões ajustadas para cada mês futuro:")

for i, row in df_futuro.iterrows():
    mes = row['data'].month
    fator_sazonal = indices_sazonais.get(mes, 1.0)
    previsao_ajustada = nivel * fator_sazonal
    previsoes_ajustadas.append(previsao_ajustada)

    valor_real = row['qtd_venda']
    erro_pct = ((previsao_ajustada - valor_real) / valor_real * 100)

    print(f"  {row['data'].strftime('%Y-%m')}: Fator={fator_sazonal:.3f}, Previsão={previsao_ajustada:,.0f}, Real={valor_real:,.0f}, Erro={erro_pct:+.1f}%")

total_previsao_ajustada = sum(previsoes_ajustadas)
total_ano_anterior = df_ano_anterior['qtd_venda'].sum()

print(f"\nTOTAL previsão ajustada: {total_previsao_ajustada:,.2f}")
print(f"TOTAL ano anterior: {total_ano_anterior:,.2f}")
print(f"TOTAL real (futuro): {df_futuro['qtd_venda'].sum():,.2f}")

variacao_vs_ano_ant = ((total_previsao_ajustada - total_ano_anterior) / total_ano_anterior * 100)
print(f"\nVariação previsão vs ano anterior: {variacao_vs_ano_ant:+.2f}%")

print()
print("=" * 80)
print("6. DIAGNÓSTICO DO PROBLEMA")
print("=" * 80)

print("\nPROBLEMA IDENTIFICADO:")
print(f"1. A previsão está comparando com ANO ANTERIOR ({data_inicio_ano_ant.strftime('%Y-%m')} a {data_fim_ano_ant.strftime('%Y-%m')})")
print(f"2. O nível SES ({nivel:,.0f}) está sendo comparado com média ano ant ({df_ano_anterior['qtd_venda'].mean():,.0f})")
print(f"3. Essa comparação gera: {variacao_vs_ano_ant:+.2f}%")

# Comparar com a BASE ao invés do ano anterior
variacao_vs_base = ((nivel - df_base['qtd_venda'].mean()) / df_base['qtd_venda'].mean() * 100)
print(f"\n4. Se comparássemos com a MÉDIA DA BASE: {variacao_vs_base:+.2f}%")

# Comparar período futuro real com ano anterior
variacao_real_yoy = ((df_futuro['qtd_venda'].mean() - df_ano_anterior['qtd_venda'].mean()) / df_ano_anterior['qtd_venda'].mean() * 100)
print(f"5. Variação REAL (futuro vs ano anterior): {variacao_real_yoy:+.2f}%")

print("\nCONCLUSÃO:")
if abs(variacao_vs_ano_ant - variacao_real_yoy) > 10:
    print("A previsão NÃO está capturando corretamente a tendência!")
    print(f"  - Previsão vs Ano Ant: {variacao_vs_ano_ant:+.2f}%")
    print(f"  - Real vs Ano Ant: {variacao_real_yoy:+.2f}%")
    print(f"  - DIFERENÇA: {abs(variacao_vs_ano_ant - variacao_real_yoy):.2f} pontos percentuais")
else:
    print("A previsão ESTÁ capturando bem a tendência!")

print("\n" + "=" * 80)
