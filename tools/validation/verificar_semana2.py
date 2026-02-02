# -*- coding: utf-8 -*-
"""
Verificar: Dados da semana 2 em 2025 e 2026
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime

print("=" * 80)
print("   VERIFICAÇÃO: SEMANA 2 NOS ANOS 2024, 2025 E 2026")
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

# Semana 2 em cada ano
for ano in [2024, 2025, 2026]:
    print(f"\nSemana 2 de {ano}:")
    print("-" * 50)

    cursor.execute("""
        SELECT
            DATE_TRUNC('week', data)::date as inicio_semana,
            EXTRACT(ISOYEAR FROM data) as iso_ano,
            EXTRACT(WEEK FROM data) as semana,
            MIN(data) as primeira_data,
            MAX(data) as ultima_data,
            SUM(qtd_venda) as total
        FROM historico_vendas_diario
        WHERE EXTRACT(ISOYEAR FROM data) = %s
          AND EXTRACT(WEEK FROM data) = 2
        GROUP BY DATE_TRUNC('week', data), EXTRACT(ISOYEAR FROM data), EXTRACT(WEEK FROM data)
        ORDER BY inicio_semana
    """, (ano,))

    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"  Inicio: {row[0]}, ISO Ano: {int(row[1])}, Semana: {int(row[2])}")
            print(f"  Dados: {row[3]} a {row[4]}")
            print(f"  Total: {row[5]:,.0f}")
    else:
        print(f"  Sem dados para semana 2 de {ano}")

# Ver também a primeira semana de janeiro em cada ano
print()
print("=" * 80)
print("DADOS DE JANEIRO (PRIMEIROS DIAS) EM CADA ANO:")
print("=" * 80)

for ano in [2024, 2025, 2026]:
    print(f"\n{ano}:")
    cursor.execute("""
        SELECT
            data,
            EXTRACT(ISOYEAR FROM data) as iso_ano,
            EXTRACT(WEEK FROM data) as semana,
            SUM(qtd_venda) as total
        FROM historico_vendas_diario
        WHERE EXTRACT(YEAR FROM data) = %s
          AND EXTRACT(MONTH FROM data) = 1
          AND EXTRACT(DAY FROM data) <= 15
        GROUP BY data, EXTRACT(ISOYEAR FROM data), EXTRACT(WEEK FROM data)
        ORDER BY data
    """, (ano,))

    for row in cursor.fetchall():
        print(f"  {row[0]}: ISO {int(row[1])}-S{int(row[2])}, Total: {row[3]:,.0f}")

conn.close()
