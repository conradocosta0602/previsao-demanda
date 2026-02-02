# -*- coding: utf-8 -*-
"""
Verificar: Existem dados do dia 01 ao dia 08 de janeiro de 2024?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2

print("=" * 80)
print("   VERIFICAÇÃO: DADOS DE JANEIRO 2024")
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

# 1. Verificar dados SEM filtro de data (base completa)
print("1️⃣  DADOS SEM FILTRO (base completa)")
print("-" * 80)

cursor.execute("""
    SELECT
        MIN(data) as primeiro_dia,
        MAX(data) as ultimo_dia,
        COUNT(DISTINCT data) as total_dias
    FROM historico_vendas_diario
""")
primeiro_dia, ultimo_dia, total_dias = cursor.fetchone()

print(f"Primeiro dia na base: {primeiro_dia}")
print(f"Último dia na base:   {ultimo_dia}")
print(f"Total de dias:        {total_dias}")
print()

# 2. Verificar dados de 01/01/2024 a 08/01/2024
print("2️⃣  DADOS DE 01/01/2024 A 08/01/2024")
print("-" * 80)

cursor.execute("""
    SELECT
        data,
        SUM(qtd_venda) as total_vendas
    FROM historico_vendas_diario
    WHERE data >= '2024-01-01'
      AND data <= '2024-01-08'
    GROUP BY data
    ORDER BY data
""")
dados_janeiro = cursor.fetchall()

if dados_janeiro:
    print("Dados encontrados:")
    for data, total in dados_janeiro:
        print(f"   {data}: {total:>12,.0f} unidades")
    print()
    print(f"Total de dias com dados: {len(dados_janeiro)}")
else:
    print("⚠️  NÃO HÁ DADOS entre 01/01/2024 e 08/01/2024!")
print()

# 3. Verificar primeiros 15 dias da base
print("3️⃣  PRIMEIROS 15 DIAS DA BASE")
print("-" * 80)

cursor.execute("""
    SELECT
        data,
        SUM(qtd_venda) as total_vendas
    FROM historico_vendas_diario
    GROUP BY data
    ORDER BY data
    LIMIT 15
""")
primeiros_dias = cursor.fetchall()

print("Primeiros 15 dias com dados:")
for data, total in primeiros_dias:
    print(f"   {data}: {total:>12,.0f} unidades")
print()

# 4. Verificar dados de dezembro 2023 (se existem)
print("4️⃣  DADOS DE DEZEMBRO 2023 (antes do boundary)")
print("-" * 80)

cursor.execute("""
    SELECT
        MIN(data) as primeiro_dia,
        MAX(data) as ultimo_dia,
        COUNT(DISTINCT data) as total_dias,
        SUM(qtd_venda) as total_vendas
    FROM historico_vendas_diario
    WHERE data >= '2023-12-01'
      AND data < '2024-01-01'
""")
dez_2023 = cursor.fetchone()

if dez_2023[0]:
    print(f"Dados de dezembro 2023 encontrados:")
    print(f"   Período: {dez_2023[0]} a {dez_2023[1]}")
    print(f"   Dias: {dez_2023[2]}")
    print(f"   Total vendas: {dez_2023[3]:,.0f}")
else:
    print("⚠️  NÃO HÁ DADOS de dezembro 2023!")
print()

conn.close()
