# -*- coding: utf-8 -*-
"""
Validação: Histórico deve ser idêntico entre granularidades
O histórico já aconteceu e não deve mudar!
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime, timedelta
import pandas as pd

print("=" * 80)
print("   VALIDAÇÃO: HISTÓRICO IDÊNTICO ENTRE GRANULARIDADES")
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

cursor = conn.cursor()

# Verificar o período de 6 meses do ano anterior
# Precisamos simular o que o sistema faz ao buscar "6 meses de previsão"

print("1️⃣  DADOS HISTÓRICOS - GRANULARIDADE MENSAL")
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

cursor.execute(query_mensal)
dados_mensal = cursor.fetchall()

print(f"Total de meses: {len(dados_mensal)}")

# Calcular total
total_mensal_completo = sum(float(d[1]) for d in dados_mensal)
print(f"Total completo (2 anos): {total_mensal_completo:,.2f}")

# Pegar últimos 6 meses para comparação
ultimos_6_meses = dados_mensal[-6:]
total_mensal_6m = sum(float(d[1]) for d in ultimos_6_meses)

print(f"\nÚltimos 6 meses:")
for data, qtd in ultimos_6_meses:
    print(f"   {data.strftime('%Y-%m')}: {qtd:>12,.0f}")
print(f"\nTotal últimos 6 meses: {total_mensal_6m:,.2f}")
print()

print("2️⃣  DADOS HISTÓRICOS - GRANULARIDADE SEMANAL")
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

cursor.execute(query_semanal)
dados_semanal = cursor.fetchall()

print(f"Total de semanas: {len(dados_semanal)}")

# Calcular total
total_semanal_completo = sum(float(d[1]) for d in dados_semanal)
print(f"Total completo (2 anos): {total_semanal_completo:,.2f}")

# Pegar últimas 24 semanas (~6 meses)
ultimas_24_semanas = dados_semanal[-24:]
total_semanal_24s = sum(float(d[1]) for d in ultimas_24_semanas)

print(f"\nÚltimas 24 semanas:")
for i, (data, qtd) in enumerate(ultimas_24_semanas, 1):
    semana_ano = data.isocalendar()[1]
    print(f"   S{semana_ano:>2} ({data}): {qtd:>12,.0f}")
print(f"\nTotal últimas 24 semanas: {total_semanal_24s:,.2f}")
print()

print("3️⃣  VERIFICAÇÃO DIRETA NOS DIAS")
print("-" * 80)

# Pegar o intervalo de datas dos últimos 6 meses
data_inicio_6m = ultimos_6_meses[0][0]
data_fim_6m = ultimos_6_meses[-1][0]

# Adicionar 1 mês ao fim para pegar o mês completo
data_fim_6m_inclusivo = data_fim_6m + timedelta(days=31)

print(f"Período dos últimos 6 meses (mensal):")
print(f"   Início: {data_inicio_6m}")
print(f"   Fim: {data_fim_6m}")
print()

# Buscar TODOS os dias dentro desse período
query_dias = """
    SELECT
        h.data,
        SUM(h.qtd_venda) as qtd_venda
    FROM historico_vendas_diario h
    WHERE h.data >= %s
      AND h.data < %s
    GROUP BY h.data
    ORDER BY h.data
"""

cursor.execute(query_dias, (data_inicio_6m, data_fim_6m_inclusivo))
dados_dias = cursor.fetchall()

total_dias = sum(float(d[1]) for d in dados_dias)
print(f"Total DIÁRIO no período dos 6 meses: {total_dias:,.2f}")
print(f"Número de dias: {len(dados_dias)}")
print()

# Comparar com agregação semanal no mesmo período
print("4️⃣  AGREGAÇÃO SEMANAL NO MESMO PERÍODO")
print("-" * 80)

# Pegar semanas que caem dentro do período mensal
semanas_no_periodo = [
    (data, qtd) for data, qtd in dados_semanal
    if data >= data_inicio_6m.date() and data < data_fim_6m_inclusivo.date()
]

total_semanas_periodo = sum(float(qtd) for data, qtd in semanas_no_periodo)
print(f"Semanas no período dos 6 meses: {len(semanas_no_periodo)}")
print(f"Total SEMANAL (mesmo período): {total_semanas_periodo:,.2f}")
print()

for data, qtd in semanas_no_periodo:
    semana_ano = data.isocalendar()[1]
    print(f"   S{semana_ano:>2} ({data}): {qtd:>12,.0f}")

print()
print("=" * 80)
print("📊 ANÁLISE COMPARATIVA")
print("=" * 80)
print()

print(f"Total MENSAL (6 meses):         {total_mensal_6m:>15,.2f}")
print(f"Total SEMANAL (24 semanas):     {total_semanal_24s:>15,.2f}")
print(f"Total DIÁRIO (mesmo período):   {total_dias:>15,.2f}")
print(f"Total SEMANAL (mesmo período):  {total_semanas_periodo:>15,.2f}")
print()

# Calcular diferenças
diff_mensal_dia = total_mensal_6m - total_dias
diff_semanal_dia = total_semanal_24s - total_dias
diff_mensal_semanal = total_mensal_6m - total_semanal_24s

print("Diferenças:")
print(f"   Mensal vs Diário:   {diff_mensal_dia:>15,.2f}  ({(diff_mensal_dia/total_dias)*100:+.2f}%)")
print(f"   Semanal vs Diário:  {diff_semanal_dia:>15,.2f}  ({(diff_semanal_dia/total_dias)*100:+.2f}%)")
print(f"   Mensal vs Semanal:  {diff_mensal_semanal:>15,.2f}  ({(diff_mensal_semanal/total_mensal_6m)*100:+.2f}%)")
print()

print("=" * 80)
print("🩺 DIAGNÓSTICO")
print("=" * 80)
print()

if abs(diff_mensal_dia) < 1:
    print("✅ Mensal está correto (soma dos dias)")
else:
    print(f"⚠️  Mensal tem diferença de {diff_mensal_dia:,.0f} vs soma dos dias")

if abs(diff_semanal_dia) < 1:
    print("✅ Semanal está correto (soma dos dias)")
else:
    print(f"⚠️  Semanal tem diferença de {diff_semanal_dia:,.0f} vs soma dos dias")

if abs(diff_mensal_semanal) > 1000:
    print(f"\n🔴 PROBLEMA CONFIRMADO!")
    print(f"   Diferença de {abs(diff_mensal_semanal):,.0f} entre mensal e semanal")
    print()
    print("   Possíveis causas:")
    print("   1. DATE_TRUNC('week') incluindo dias fora do período de 2 anos")
    print("   2. Semanas parciais no início/fim do período")
    print("   3. Agregação semanal pegando dias de meses adjacentes")
    print()
    print("   📋 RECOMENDAÇÃO:")
    print("   Usar CTE com filtro de data ANTES do DATE_TRUNC para garantir")
    print("   que apenas dias dentro do intervalo sejam agregados!")
else:
    print("\n✅ Diferença aceitável (<1000 unidades)")

conn.close()

print()
print("=" * 80)
