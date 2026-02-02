# -*- coding: utf-8 -*-
"""
Verificar: Query de histórico
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2

conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Verificar o filtro de data
cursor.execute("""
    SELECT
        CURRENT_DATE as hoje,
        DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years') as inicio_filtro
""")
row = cursor.fetchone()
print(f"Hoje: {row[0]}")
print(f"Início do filtro: {row[1]}")

# Verificar quantos registros temos
cursor.execute("""
    SELECT
        MIN(data) as primeira,
        MAX(data) as ultima,
        COUNT(DISTINCT data) as dias
    FROM historico_vendas_diario
    WHERE data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
""")
row = cursor.fetchone()
print(f"\nDados disponíveis:")
print(f"  Primeira data: {row[0]}")
print(f"  Última data: {row[1]}")
print(f"  Total de dias: {row[2]}")

# Verificar por semana
cursor.execute("""
    WITH dados AS (
        SELECT
            DATE_TRUNC('week', data)::date as semana,
            SUM(qtd_venda) as total
        FROM historico_vendas_diario
        WHERE data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
        GROUP BY DATE_TRUNC('week', data)
        ORDER BY semana
    )
    SELECT COUNT(*) as total_semanas, MIN(semana), MAX(semana)
    FROM dados
""")
row = cursor.fetchone()
print(f"\nSemanas:")
print(f"  Total: {row[0]}")
print(f"  Primeira: {row[1]}")
print(f"  Última: {row[2]}")

conn.close()
