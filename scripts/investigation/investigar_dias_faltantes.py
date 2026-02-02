# -*- coding: utf-8 -*-
"""
Investigar: Quais dias estão incluídos em cada agregação?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime

print("=" * 80)
print("   INVESTIGAÇÃO: DIAS INCLUÍDOS EM CADA AGREGAÇÃO")
print("=" * 80)
print()

conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)

cursor = conn.cursor()

# Verificar boundary atual
cursor.execute("SELECT CURRENT_DATE, CURRENT_DATE - INTERVAL '2 years' as boundary")
current_date, boundary = cursor.fetchone()
print(f"📅 CURRENT_DATE: {current_date}")
print(f"📅 BOUNDARY (2 anos atrás): {boundary}")
print()

# 1. CONTAR DIAS TOTAIS no período
print("=" * 80)
print("1️⃣  DIAS TOTAIS NO PERÍODO")
print("=" * 80)
print()

cursor.execute("""
    SELECT
        MIN(data) as primeiro_dia,
        MAX(data) as ultimo_dia,
        COUNT(DISTINCT data) as total_dias,
        SUM(qtd_venda) as total_vendas
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '2 years'
""")
primeiro_dia, ultimo_dia, total_dias, total_vendas = cursor.fetchone()

print(f"Primeiro dia com dados: {primeiro_dia}")
print(f"Último dia com dados: {ultimo_dia}")
print(f"Total de dias: {total_dias}")
print(f"Total vendas (TODOS OS DIAS): {total_vendas:,.0f}")
print()

# 2. AGREGAÇÃO MENSAL - Quais dias são incluídos?
print("=" * 80)
print("2️⃣  AGREGAÇÃO MENSAL")
print("=" * 80)
print()

cursor.execute("""
    SELECT
        DATE_TRUNC('month', h.data) as mes,
        COUNT(DISTINCT h.data) as dias_no_mes,
        MIN(h.data) as primeiro_dia,
        MAX(h.data) as ultimo_dia,
        SUM(h.qtd_venda) as total_mes
    FROM historico_vendas_diario h
    WHERE h.data >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY DATE_TRUNC('month', h.data)
    ORDER BY DATE_TRUNC('month', h.data)
""")
dados_mensal = cursor.fetchall()

total_dias_mensal = 0
total_vendas_mensal = 0

print("Mês         | Dias | Primeiro Dia | Último Dia   | Total")
print("-" * 80)
for mes, dias, primeiro, ultimo, total in dados_mensal:
    print(f"{mes.strftime('%Y-%m')}    | {dias:>4} | {primeiro}  | {ultimo} | {total:>12,.0f}")
    total_dias_mensal += dias
    total_vendas_mensal += total

print("-" * 80)
print(f"TOTAL       | {total_dias_mensal:>4} |              |              | {total_vendas_mensal:>12,.0f}")
print()

# 3. AGREGAÇÃO SEMANAL - Quais dias são incluídos?
print("=" * 80)
print("3️⃣  AGREGAÇÃO SEMANAL")
print("=" * 80)
print()

cursor.execute("""
    WITH dados_diarios AS (
        SELECT
            h.data,
            SUM(h.qtd_venda) as qtd_venda
        FROM historico_vendas_diario h
        WHERE h.data >= CURRENT_DATE - INTERVAL '2 years'
        GROUP BY h.data
    )
    SELECT
        DATE_TRUNC('week', data)::date as semana,
        COUNT(data) as dias_na_semana,
        MIN(data) as primeiro_dia,
        MAX(data) as ultimo_dia,
        SUM(qtd_venda) as total_semana
    FROM dados_diarios
    GROUP BY DATE_TRUNC('week', data)
    ORDER BY DATE_TRUNC('week', data)
""")
dados_semanal = cursor.fetchall()

total_dias_semanal = 0
total_vendas_semanal = 0

print("Semana      | Dias | Primeiro Dia | Último Dia   | Total")
print("-" * 80)

# Mostrar primeiras 10 semanas
for i, (semana, dias, primeiro, ultimo, total) in enumerate(dados_semanal):
    if i < 10 or i >= len(dados_semanal) - 3:  # Primeiras 10 e últimas 3
        semana_iso = semana.isocalendar()[1]
        print(f"S{semana_iso:>2} ({semana}) | {dias:>4} | {primeiro}  | {ultimo} | {total:>12,.0f}")
    elif i == 10:
        print("    ...")

    total_dias_semanal += dias
    total_vendas_semanal += total

print("-" * 80)
print(f"TOTAL       | {total_dias_semanal:>4} |              |              | {total_vendas_semanal:>12,.0f}")
print()

# 4. COMPARAÇÃO
print("=" * 80)
print("📊 COMPARAÇÃO")
print("=" * 80)
print()

print(f"Total dias DISPONÍVEIS:        {total_dias:>6}")
print(f"Total dias na agregação MENSAL:  {total_dias_mensal:>6}")
print(f"Total dias na agregação SEMANAL: {total_dias_semanal:>6}")
print()

print(f"Total vendas (todos os dias):  {total_vendas:>15,.0f}")
print(f"Total vendas (mensal):         {total_vendas_mensal:>15,.0f}")
print(f"Total vendas (semanal):        {total_vendas_semanal:>15,.0f}")
print()

dias_faltantes_mensal = total_dias - total_dias_mensal
dias_faltantes_semanal = total_dias - total_dias_semanal

if dias_faltantes_mensal == 0 and dias_faltantes_semanal == 0:
    print("✅ PERFEITO: Todas as agregações incluem TODOS os dias disponíveis!")
else:
    if dias_faltantes_mensal > 0:
        print(f"⚠️  MENSAL está faltando {dias_faltantes_mensal} dias")
    if dias_faltantes_semanal > 0:
        print(f"⚠️  SEMANAL está faltando {dias_faltantes_semanal} dias")
    print()
    print("ISSO É UM ERRO! Todas as agregações deveriam incluir os mesmos dias.")

print()

# 5. VERIFICAR DIAS ENTRE 01/01/2024 e 08/01/2024
print("=" * 80)
print("5️⃣  DIAS ENTRE 01/01/2024 E 08/01/2024")
print("=" * 80)
print()

cursor.execute("""
    SELECT
        data,
        qtd_venda,
        DATE_TRUNC('week', data)::date as semana
    FROM historico_vendas_diario
    WHERE data >= '2024-01-01'
      AND data < '2024-01-09'
    ORDER BY data
""")
dias_janeiro_inicio = cursor.fetchall()

if len(dias_janeiro_inicio) == 0:
    print("ℹ️  NÃO HÁ DADOS entre 01/01/2024 e 08/01/2024")
    print("   Os dados começam em 09/01/2024 por causa do boundary de 2 anos.")
else:
    print("Dia         | Vendas    | Semana")
    print("-" * 60)
    for data, vendas, semana in dias_janeiro_inicio:
        print(f"{data}  | {vendas:>9,.0f} | {semana}")

print()
print("=" * 80)

conn.close()
