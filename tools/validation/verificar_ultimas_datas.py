# -*- coding: utf-8 -*-
"""
Verificar: Qual é a última data em cada granularidade?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2

print("=" * 80)
print("   VERIFICAÇÃO: ÚLTIMAS DATAS POR GRANULARIDADE")
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

# 1. Diário - última data
print("1. GRANULARIDADE DIARIA")
print("-" * 80)
cursor.execute("""
    SELECT MAX(data) as ultima_data, COUNT(DISTINCT data) as total_dias
    FROM historico_vendas_diario
    WHERE data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
""")
ultima_diario, total_dias = cursor.fetchone()
print(f"   Última data: {ultima_diario}")
print(f"   Total de dias: {total_dias}")
print()

# 2. Semanal - última semana
print("2. GRANULARIDADE SEMANAL")
print("-" * 80)
cursor.execute("""
    SELECT
        DATE_TRUNC('week', MAX(data))::date as ultima_semana,
        COUNT(DISTINCT DATE_TRUNC('week', data)) as total_semanas
    FROM historico_vendas_diario
    WHERE data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
""")
ultima_semanal, total_semanas = cursor.fetchone()
print(f"   Última semana: {ultima_semanal}")
print(f"   Total de semanas: {total_semanas}")
print()

# 3. Mensal - último mês
print("3. GRANULARIDADE MENSAL")
print("-" * 80)
cursor.execute("""
    SELECT
        DATE_TRUNC('month', MAX(data))::date as ultimo_mes,
        COUNT(DISTINCT DATE_TRUNC('month', data)) as total_meses
    FROM historico_vendas_diario
    WHERE data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
""")
ultimo_mensal, total_meses = cursor.fetchone()
print(f"   Último mês: {ultimo_mensal}")
print(f"   Total de meses: {total_meses}")
print()

# 4. Verificar últimos dias disponíveis
print("4. ÚLTIMOS 10 DIAS NA BASE")
print("-" * 80)
cursor.execute("""
    SELECT data, SUM(qtd_venda) as total
    FROM historico_vendas_diario
    GROUP BY data
    ORDER BY data DESC
    LIMIT 10
""")
for data, total in cursor.fetchall():
    print(f"   {data}: {total:,.0f}")

conn.close()
