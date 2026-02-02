# -*- coding: utf-8 -*-
"""
Verificar primeira semana de 2024
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime

print("=" * 80)
print("   VERIFICAÇÃO: PRIMEIRA SEMANA DE 2024")
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

# Verificar primeiros 15 dias de 2024
query = """
    SELECT
        data,
        DATE_TRUNC('week', data)::date as semana,
        SUM(qtd_venda) as total
    FROM historico_vendas_diario
    WHERE data >= '2024-01-01'
      AND data <= '2024-01-15'
    GROUP BY data, DATE_TRUNC('week', data)
    ORDER BY data
"""

cursor.execute(query)
dados = cursor.fetchall()

print("Primeiros 15 dias de 2024:")
print()

for data, semana, total in dados:
    dia_semana = data.strftime('%A')
    print(f"{data} ({dia_semana}): Semana={semana}, Total={total:>12,.0f}")

print()
print("=" * 80)
print("Agregação por semana:")
print("=" * 80)
print()

query_semanas = """
    SELECT
        DATE_TRUNC('week', data)::date as semana,
        SUM(qtd_venda) as total
    FROM historico_vendas_diario
    WHERE data >= '2024-01-01'
      AND data <= '2024-01-31'
    GROUP BY DATE_TRUNC('week', data)
    ORDER BY DATE_TRUNC('week', data)
"""

cursor.execute(query_semanas)
semanas = cursor.fetchall()

total_semanal = 0
for semana, total in semanas:
    semana_iso = semana.isocalendar()[1]
    print(f"S{semana_iso:>2} ({semana}): {total:>12,.0f}")
    total_semanal += total

print()
print(f"Total SEMANAL (Janeiro): {total_semanal:,.0f}")
print()

# Comparar com mensal
query_mensal = """
    SELECT SUM(qtd_venda) as total
    FROM historico_vendas_diario
    WHERE data >= '2024-01-01'
      AND data < '2024-02-01'
"""

cursor.execute(query_mensal)
total_mensal = cursor.fetchone()[0]

print(f"Total MENSAL (Janeiro):  {total_mensal:,.0f}")
print(f"Diferença:               {total_mensal - total_semanal:,.0f}")

conn.close()
