# -*- coding: utf-8 -*-
"""
Verificar quantos DIAS reais cada agregação está cobrindo
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime, timedelta

print("=" * 80)
print("   VERIFICAÇÃO: DIAS COBERTOS POR CADA AGREGAÇÃO")
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

# Verificar total de dias disponíveis
cursor.execute("""
    SELECT
        MIN(data) as primeiro_dia,
        MAX(data) as ultimo_dia,
        COUNT(DISTINCT data) as total_dias,
        SUM(qtd_venda) as total_vendas
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '2 years'
""")
primeiro_dia, ultimo_dia, total_dias, total_vendas_diario = cursor.fetchone()

print(f"📅 DADOS DISPONÍVEIS (últimos 2 anos)")
print(f"   Primeiro dia: {primeiro_dia}")
print(f"   Último dia:   {ultimo_dia}")
print(f"   Total dias:   {total_dias}")
print(f"   Total vendas: {total_vendas_diario:,.0f}")
print()

# Simular divisão 50/25/25 para MENSAL
print("=" * 80)
print("1️⃣  SIMULAÇÃO MENSAL (50/25/25)")
print("=" * 80)
print()

cursor.execute("""
    SELECT
        DATE_TRUNC('month', data)::date as mes,
        COUNT(DISTINCT data) as dias_no_mes,
        MIN(data) as primeiro_dia,
        MAX(data) as ultimo_dia,
        SUM(qtd_venda) as total
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY DATE_TRUNC('month', data)
    ORDER BY DATE_TRUNC('month', data)
""")
meses = cursor.fetchall()

total_meses = len(meses)
tamanho_base_mensal = int(total_meses * 0.50)
tamanho_teste_mensal = int(total_meses * 0.25)

print(f"Total meses: {total_meses}")
print(f"Base:  {tamanho_base_mensal} meses (50%)")
print(f"Teste: {tamanho_teste_mensal} meses (25%)")
print()

# Calcular totais para base e teste
base_mensal = meses[:tamanho_base_mensal]
teste_mensal = meses[tamanho_base_mensal:tamanho_base_mensal + tamanho_teste_mensal]

total_dias_base_mensal = sum(m[1] for m in base_mensal)
total_vendas_base_mensal = sum(m[4] for m in base_mensal)
total_dias_teste_mensal = sum(m[1] for m in teste_mensal)
total_vendas_teste_mensal = sum(m[4] for m in teste_mensal)

print(f"BASE ({base_mensal[0][0].strftime('%Y-%m')} a {base_mensal[-1][0].strftime('%Y-%m')}):")
print(f"   Dias:   {total_dias_base_mensal}")
print(f"   Vendas: {total_vendas_base_mensal:,.0f}")
print()

print(f"TESTE ({teste_mensal[0][0].strftime('%Y-%m')} a {teste_mensal[-1][0].strftime('%Y-%m')}):")
print(f"   Dias:   {total_dias_teste_mensal}")
print(f"   Vendas: {total_vendas_teste_mensal:,.0f}")
print()

total_dias_historico_mensal = total_dias_base_mensal + total_dias_teste_mensal
total_vendas_historico_mensal = total_vendas_base_mensal + total_vendas_teste_mensal

print(f"TOTAL HISTÓRICO MENSAL:")
print(f"   Dias:   {total_dias_historico_mensal}")
print(f"   Vendas: {total_vendas_historico_mensal:,.0f}")
print()

# Simular divisão 50/25/25 para SEMANAL
print("=" * 80)
print("2️⃣  SIMULAÇÃO SEMANAL (50/25/25)")
print("=" * 80)
print()

cursor.execute("""
    WITH dados_diarios AS (
        SELECT
            data,
            SUM(qtd_venda) as qtd_venda
        FROM historico_vendas_diario
        WHERE data >= CURRENT_DATE - INTERVAL '2 years'
        GROUP BY data
    )
    SELECT
        DATE_TRUNC('week', data)::date as semana,
        COUNT(data) as dias_na_semana,
        MIN(data) as primeiro_dia,
        MAX(data) as ultimo_dia,
        SUM(qtd_venda) as total
    FROM dados_diarios
    GROUP BY DATE_TRUNC('week', data)
    ORDER BY DATE_TRUNC('week', data)
""")
semanas = cursor.fetchall()

total_semanas = len(semanas)
tamanho_base_semanal = int(total_semanas * 0.50)
tamanho_teste_semanal = int(total_semanas * 0.25)

print(f"Total semanas: {total_semanas}")
print(f"Base:  {tamanho_base_semanal} semanas (50%)")
print(f"Teste: {tamanho_teste_semanal} semanas (25%)")
print()

# Calcular totais para base e teste
base_semanal = semanas[:tamanho_base_semanal]
teste_semanal = semanas[tamanho_base_semanal:tamanho_base_semanal + tamanho_teste_semanal]

total_dias_base_semanal = sum(s[1] for s in base_semanal)
total_vendas_base_semanal = sum(s[4] for s in base_semanal)
total_dias_teste_semanal = sum(s[1] for s in teste_semanal)
total_vendas_teste_semanal = sum(s[4] for s in teste_semanal)

print(f"BASE ({base_semanal[0][0]} a {base_semanal[-1][0]}):")
print(f"   Dias:   {total_dias_base_semanal}")
print(f"   Vendas: {total_vendas_base_semanal:,.0f}")
print()

print(f"TESTE ({teste_semanal[0][0]} a {teste_semanal[-1][0]}):")
print(f"   Dias:   {total_dias_teste_semanal}")
print(f"   Vendas: {total_vendas_teste_semanal:,.0f}")
print()

total_dias_historico_semanal = total_dias_base_semanal + total_dias_teste_semanal
total_vendas_historico_semanal = total_vendas_base_semanal + total_vendas_teste_semanal

print(f"TOTAL HISTÓRICO SEMANAL:")
print(f"   Dias:   {total_dias_historico_semanal}")
print(f"   Vendas: {total_vendas_historico_semanal:,.0f}")
print()

# Comparação
print("=" * 80)
print("📊 COMPARAÇÃO")
print("=" * 80)
print()

print(f"                    MENSAL          SEMANAL         DIFERENÇA")
print(f"Dias cobertos:      {total_dias_historico_mensal:>6}          {total_dias_historico_semanal:>6}            {total_dias_historico_mensal - total_dias_historico_semanal:>+6}")
print(f"Total vendas:   {total_vendas_historico_mensal:>12,.0f}    {total_vendas_historico_semanal:>12,.0f}    {total_vendas_historico_mensal - total_vendas_historico_semanal:>+12,.0f}")
print()

diferenca_pct = ((total_vendas_historico_mensal - total_vendas_historico_semanal) / total_vendas_historico_mensal) * 100
print(f"Diferença percentual: {diferenca_pct:+.2f}%")
print()

if abs(diferenca_pct) > 0.1:
    print("🔴 CAUSA DA DIFERENÇA:")
    print(f"   - Mensal cobre {total_dias_historico_mensal} dias")
    print(f"   - Semanal cobre {total_dias_historico_semanal} dias")
    print(f"   - Diferença de {abs(total_dias_historico_mensal - total_dias_historico_semanal)} dias!")
    print()
    print("   A divisão 50/25/25 aplicada sobre períodos diferentes")
    print("   (meses vs semanas) resulta em coberturas de DIAS diferentes.")

conn.close()
