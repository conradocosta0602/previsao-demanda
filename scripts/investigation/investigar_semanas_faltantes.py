# -*- coding: utf-8 -*-
"""
Investigar: Por que temos 105 semanas ao invés de ~108?
Se 25 meses ≈ 108 semanas, onde estão as 3 semanas faltantes?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime, timedelta

print("=" * 80)
print("   INVESTIGAÇÃO: SEMANAS FALTANTES")
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

# 1. Verificar período coberto pelos dados
print("1️⃣  PERÍODO DOS DADOS")
print("-" * 80)

cursor.execute("""
    SELECT
        MIN(data) as primeiro_dia,
        MAX(data) as ultimo_dia,
        COUNT(DISTINCT data) as total_dias
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '2 years'
""")
primeiro_dia, ultimo_dia, total_dias = cursor.fetchone()

print(f"Primeiro dia com dados: {primeiro_dia}")
print(f"Último dia com dados:   {ultimo_dia}")
print(f"Total de dias:          {total_dias}")
print()

# Calcular quantas semanas DEVERIA ter
dias_teoricos = (ultimo_dia - primeiro_dia).days + 1
semanas_teoricas = dias_teoricos / 7

print(f"Dias no período:        {dias_teoricos}")
print(f"Semanas teóricas:       {semanas_teoricas:.1f}")
print()

# 2. Verificar quantos MESES temos
print("2️⃣  CONTAGEM DE MESES")
print("-" * 80)

cursor.execute("""
    SELECT
        DATE_TRUNC('month', data)::date as mes,
        COUNT(DISTINCT data) as dias
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY DATE_TRUNC('month', data)
    ORDER BY DATE_TRUNC('month', data)
""")
meses = cursor.fetchall()

print(f"Total de meses: {len(meses)}")
print()
print("Meses disponíveis:")
for mes, dias in meses:
    print(f"   {mes.strftime('%Y-%m')}: {dias:>2} dias")
print()

# 3. Verificar quantas SEMANAS temos
print("3️⃣  CONTAGEM DE SEMANAS")
print("-" * 80)

cursor.execute("""
    SELECT
        DATE_TRUNC('week', data)::date as semana,
        COUNT(DISTINCT data) as dias
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY DATE_TRUNC('week', data)
    ORDER BY DATE_TRUNC('week', data)
""")
semanas = cursor.fetchall()

print(f"Total de semanas: {len(semanas)}")
print()

# Mostrar primeiras e últimas semanas
print("Primeiras 5 semanas:")
for semana, dias in semanas[:5]:
    semana_iso = semana.isocalendar()[1]
    print(f"   S{semana_iso:>2} ({semana}): {dias} dias")

print()
print("Últimas 5 semanas:")
for semana, dias in semanas[-5:]:
    semana_iso = semana.isocalendar()[1]
    print(f"   S{semana_iso:>2} ({semana}): {dias} dias")

print()

# 4. Verificar se há semanas com menos de 7 dias
print("4️⃣  SEMANAS INCOMPLETAS")
print("-" * 80)

semanas_incompletas = [(s, d) for s, d in semanas if d < 7]
print(f"Semanas com menos de 7 dias: {len(semanas_incompletas)}")
print()

if semanas_incompletas:
    for semana, dias in semanas_incompletas:
        semana_iso = semana.isocalendar()[1]
        print(f"   S{semana_iso:>2} ({semana}): {dias} dias")
print()

# 5. Calcular expectativa correta
print("5️⃣  ANÁLISE MATEMÁTICA")
print("-" * 80)
print()

# 25 meses = quantas semanas?
meses_total = len(meses)
semanas_esperadas = meses_total * (52/12)

print(f"Total de meses:           {meses_total}")
print(f"Semanas esperadas (×4.33): {semanas_esperadas:.1f}")
print(f"Semanas reais:            {len(semanas)}")
print(f"Diferença:                {semanas_esperadas - len(semanas):.1f} semanas")
print()

# 6. Verificar o boundary de 2 anos
print("6️⃣  VERIFICAR BOUNDARY DE 2 ANOS")
print("-" * 80)

cursor.execute("SELECT CURRENT_DATE, CURRENT_DATE - INTERVAL '2 years'")
current_date, boundary = cursor.fetchone()

print(f"CURRENT_DATE:             {current_date}")
print(f"Boundary (2 anos atrás):  {boundary}")
print()

# Verificar se o primeiro dia dos dados é igual ao boundary
print(f"Primeiro dia com dados:   {primeiro_dia}")
print(f"Diferença do boundary:    {(primeiro_dia - boundary.date()).days} dias")
print()

# Se há diferença, verificar o que aconteceu
if primeiro_dia > boundary.date():
    print("⚠️  PROBLEMA ENCONTRADO!")
    print(f"   Os dados começam {(primeiro_dia - boundary.date()).days} dias DEPOIS do boundary!")
    print(f"   Isso pode ser porque não há dados entre {boundary.date()} e {primeiro_dia}")
    print()

    # Verificar se há dados antes do primeiro dia
    cursor.execute("""
        SELECT MIN(data), MAX(data), COUNT(DISTINCT data)
        FROM historico_vendas_diario
    """)
    min_total, max_total, count_total = cursor.fetchone()
    print(f"   Dados totais no banco: {min_total} até {max_total} ({count_total} dias)")

conn.close()
