# -*- coding: utf-8 -*-
"""
Debug: Ver exatamente o que o SQL retorna
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime, timedelta

print("=" * 80)
print("   DEBUG: DATAS DO SQL")
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

# Verificar CURRENT_DATE e boundary
cursor.execute("SELECT CURRENT_DATE, CURRENT_DATE - INTERVAL '2 years' as boundary")
current_date, boundary = cursor.fetchone()
print(f"CURRENT_DATE: {current_date}")
print(f"Boundary (2 years ago): {boundary}")
print()

# Query MENSAL (exatamente como no app.py)
print("=" * 80)
print("QUERY MENSAL")
print("=" * 80)
print()

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

print(f"Total meses: {len(dados_mensal)}")
print(f"Primeiro mês: {dados_mensal[0][0]} = {dados_mensal[0][1]:,.0f}")
print(f"Último mês: {dados_mensal[-1][0]} = {dados_mensal[-1][1]:,.0f}")
total_mensal = sum(d[1] for d in dados_mensal)
print(f"Total MENSAL: {total_mensal:,.0f}")
print()

# Query SEMANAL (exatamente como no app.py DEPOIS da correção)
print("=" * 80)
print("QUERY SEMANAL (após correção)")
print("=" * 80)
print()

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

print(f"Total semanas: {len(dados_semanal)}")
print(f"Primeira semana: {dados_semanal[0][0]} = {dados_semanal[0][1]:,.0f}")
print(f"Última semana: {dados_semanal[-1][0]} = {dados_semanal[-1][1]:,.0f}")
total_semanal = sum(d[1] for d in dados_semanal)
print(f"Total SEMANAL: {total_semanal:,.0f}")
print()

# Comparar
print("=" * 80)
print("COMPARAÇÃO")
print("=" * 80)
print()

diferenca = total_mensal - total_semanal
pct = (diferenca / total_mensal) * 100 if total_mensal > 0 else 0

print(f"Total MENSAL:  {total_mensal:>15,.0f}")
print(f"Total SEMANAL: {total_semanal:>15,.0f}")
print(f"Diferença:     {diferenca:>15,.0f}  ({pct:+.2f}%)")
print()

if abs(pct) < 0.1:
    print("✅ SUCESSO: Totais idênticos!")
else:
    print(f"⚠️  Ainda há diferença de {abs(pct):.2f}%")
    print()
    print("Investigando causa...")
    print()

    # Verificar quais dias estão na boundary
    cursor.execute("""
        SELECT data, SUM(qtd_venda) as total
        FROM historico_vendas_diario
        WHERE data >= CURRENT_DATE - INTERVAL '2 years'
        ORDER BY data
        LIMIT 10
    """)
    primeiros_dias = cursor.fetchall()

    print("Primeiros 10 dias na boundary:")
    for data, total in primeiros_dias:
        semana = data - timedelta(days=data.weekday())  # Segunda-feira da semana
        print(f"   {data} ({data.strftime('%A')}): {total:>10,.0f}  | Semana: {semana}")

conn.close()
