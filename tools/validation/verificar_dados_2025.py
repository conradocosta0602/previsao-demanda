# -*- coding: utf-8 -*-
"""
Verificar: Existem dados de 2025 no banco?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2

print("=" * 80)
print("   VERIFICAÇÃO: DADOS POR ANO NO BANCO")
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

# Total por ano
print("TOTAL DE VENDAS POR ANO:")
print("-" * 80)
cursor.execute("""
    SELECT
        EXTRACT(YEAR FROM data) as ano,
        COUNT(DISTINCT data) as dias,
        MIN(data) as primeira_data,
        MAX(data) as ultima_data,
        SUM(qtd_venda) as total
    FROM historico_vendas_diario
    GROUP BY EXTRACT(YEAR FROM data)
    ORDER BY ano
""")

for row in cursor.fetchall():
    print(f"  {int(row[0])}: {row[1]} dias ({row[2]} a {row[3]}) - Total: {row[4]:,.0f}")

print()
print("=" * 80)
print("ÚLTIMOS REGISTROS NO BANCO:")
print("-" * 80)
cursor.execute("""
    SELECT data, SUM(qtd_venda) as total
    FROM historico_vendas_diario
    GROUP BY data
    ORDER BY data DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]:,.0f}")

# Verificar semanas de 2025
print()
print("=" * 80)
print("SEMANAS DE 2025:")
print("-" * 80)
cursor.execute("""
    SELECT
        EXTRACT(WEEK FROM data) as semana,
        DATE_TRUNC('week', data)::date as inicio_semana,
        SUM(qtd_venda) as total
    FROM historico_vendas_diario
    WHERE EXTRACT(YEAR FROM data) = 2025
    GROUP BY EXTRACT(WEEK FROM data), DATE_TRUNC('week', data)
    ORDER BY inicio_semana
""")

semanas_2025 = cursor.fetchall()
print(f"Total de semanas em 2025: {len(semanas_2025)}")
for row in semanas_2025[:15]:  # Mostrar só as primeiras 15
    print(f"  S{int(row[0])}/25: {row[2]:,.0f} ({row[1]})")

if len(semanas_2025) > 15:
    print(f"  ... mais {len(semanas_2025) - 15} semanas")

conn.close()
