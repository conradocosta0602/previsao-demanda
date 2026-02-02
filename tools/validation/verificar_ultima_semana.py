# -*- coding: utf-8 -*-
"""
Verificar: Qual é a última semana no histórico semanal?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2

print("=" * 80)
print("   VERIFICAÇÃO: ÚLTIMAS SEMANAS NO HISTÓRICO")
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

# Últimas semanas agrupadas
cursor.execute("""
    WITH semanal AS (
        SELECT
            DATE_TRUNC('week', data)::date as inicio_semana,
            EXTRACT(ISOYEAR FROM data) as iso_ano,
            EXTRACT(WEEK FROM data) as semana,
            SUM(qtd_venda) as total,
            COUNT(DISTINCT data) as dias
        FROM historico_vendas_diario
        GROUP BY DATE_TRUNC('week', data), EXTRACT(ISOYEAR FROM data), EXTRACT(WEEK FROM data)
    )
    SELECT * FROM semanal
    ORDER BY inicio_semana DESC
    LIMIT 10
""")

print("Últimas 10 semanas no histórico:")
print("-" * 80)
for row in cursor.fetchall():
    completa = "✓ Completa" if row[4] == 7 else f"⚠ {row[4]} dias"
    print(f"  {row[0]}: ISO {int(row[1])}-S{int(row[2])}, Total: {row[3]:,.0f}, {completa}")

# Verificar se S2/2025 existe
print()
print("=" * 80)
print("VERIFICAR S2/2025:")
print("-" * 80)
cursor.execute("""
    SELECT
        DATE_TRUNC('week', data)::date as inicio_semana,
        EXTRACT(ISOYEAR FROM data) as iso_ano,
        EXTRACT(WEEK FROM data) as semana,
        SUM(qtd_venda) as total,
        COUNT(DISTINCT data) as dias
    FROM historico_vendas_diario
    WHERE EXTRACT(ISOYEAR FROM data) = 2025 AND EXTRACT(WEEK FROM data) = 2
    GROUP BY DATE_TRUNC('week', data), EXTRACT(ISOYEAR FROM data), EXTRACT(WEEK FROM data)
""")

rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0]}: ISO {int(row[1])}-S{int(row[2])}, Total: {row[3]:,.0f}, {row[4]} dias")
else:
    print("  S2/2025 NÃO ENCONTRADA!")

conn.close()
