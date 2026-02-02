# -*- coding: utf-8 -*-
"""
Diagnóstico detalhado: Onde está a defasagem?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime, date

print("=" * 100)
print("DIAGNÓSTICO DETALHADO: ONDE ESTÁ A DEFASAGEM?")
print("=" * 100)
print()

conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Verificar alguns dias específicos e seus dias da semana
print("1. VERIFICAÇÃO DE DATAS ESPECÍFICAS NO BANCO")
print("-" * 80)

cursor.execute("""
    SELECT
        data,
        EXTRACT(DOW FROM data) as dow_pg,
        TO_CHAR(data, 'Day') as dia_nome,
        SUM(qtd_venda) as total
    FROM historico_vendas_diario
    WHERE data >= '2025-01-01' AND data <= '2025-01-14'
    GROUP BY data, EXTRACT(DOW FROM data), TO_CHAR(data, 'Day')
    ORDER BY data
""")

print(f"{'Data':<12} {'DOW PG':<8} {'Dia (PG)':<12} {'Dia (Python)':<12} {'Total':>12}")
print("-" * 70)

dias_python = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

for row in cursor.fetchall():
    data = row[0]
    dow_pg = int(row[1])  # PostgreSQL: 0=Domingo, 1=Segunda, ..., 6=Sábado
    dia_pg = row[2].strip()
    total = row[3]

    # Calcular dia da semana em Python
    dow_py = data.weekday()  # Python: 0=Segunda, 6=Domingo
    dia_py = dias_python[dow_py]

    print(f"{data}   {dow_pg:<8} {dia_pg:<12} {dia_py:<12} {total:>12,.0f}")

print()
print("LEGENDA:")
print("  PostgreSQL DOW: 0=Domingo, 1=Segunda, ..., 6=Sábado")
print("  Python weekday: 0=Segunda, 1=Terça, ..., 6=Domingo")
print()

# Verificar médias por DOW no PostgreSQL
print("2. MÉDIAS POR DIA DA SEMANA - COMPARAÇÃO POSTGRESQL vs PYTHON")
print("-" * 80)

cursor.execute("""
    SELECT
        EXTRACT(DOW FROM data) as dow_pg,
        AVG(qtd_venda) as media
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY EXTRACT(DOW FROM data)
    ORDER BY dow_pg
""")

print(f"{'DOW PG':<8} {'Dia (PG)':<12} {'DOW Python':<10} {'Dia (Python)':<12} {'Média':>12}")
print("-" * 70)

# Mapear DOW PostgreSQL para Python
dias_pg = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']

for row in cursor.fetchall():
    dow_pg = int(row[0])
    media = row[1]

    # PostgreSQL DOW para Python weekday
    if dow_pg == 0:  # Domingo no PG
        dow_py = 6  # Domingo no Python
    else:
        dow_py = dow_pg - 1

    dia_pg = dias_pg[dow_pg]
    dia_py = dias_python[dow_py]

    print(f"{dow_pg:<8} {dia_pg:<12} {dow_py:<10} {dia_py:<12} {media:>12,.0f}")

conn.close()

print()
print("=" * 100)
print("3. VERIFICAÇÃO DO CÁLCULO NO BACKEND")
print("=" * 100)
print()

# Simular o que o backend faz
from datetime import timedelta
import pandas as pd

# Simular datas de previsão
data_inicio = date(2026, 1, 1)
print(f"Simulando previsão a partir de {data_inicio}:")
print()
print(f"{'Data':<12} {'weekday()':<10} {'Dia':<12} {'Fator esperado':<20}")
print("-" * 60)

# Fatores sazonais esperados (baseado no histórico)
# Sábado e Domingo deveriam ter fator > 1
fatores_esperados = {
    0: 0.94,   # Segunda - abaixo da média
    1: 0.92,   # Terça
    2: 0.92,   # Quarta
    3: 0.91,   # Quinta
    4: 0.92,   # Sexta
    5: 1.20,   # Sábado - acima da média
    6: 1.20,   # Domingo - acima da média
}

for i in range(14):
    data = data_inicio + timedelta(days=i)
    dow = data.weekday()  # Python: 0=Segunda, 6=Domingo
    dia = dias_python[dow]
    fator = fatores_esperados[dow]
    situacao = "ALTO" if fator > 1.1 else ("baixo" if fator < 0.95 else "normal")
    print(f"{data}   {dow:<10} {dia:<12} {fator:.2f} ({situacao})")

print()
print("=" * 100)
print("CONCLUSÃO")
print("=" * 100)
print()
print("Se o backend usa Python weekday() corretamente:")
print("  - weekday() 5 = Sábado -> deveria ter fator ALTO")
print("  - weekday() 6 = Domingo -> deveria ter fator ALTO")
print()
print("MAS a previsão mostra:")
print("  - Domingo (weekday 6) com fator ALTO ✓")
print("  - Segunda (weekday 0) com fator ALTO ✗ (deveria ser baixo)")
print("  - Sábado (weekday 5) com fator BAIXO ✗ (deveria ser alto)")
print()
print("POSSÍVEL CAUSA:")
print("  O cálculo do índice sazonal no backend pode estar usando")
print("  o índice do LOOP (i) em vez do dia da semana da DATA.")
print("  Ou há uma confusão entre DOW do PostgreSQL e weekday() do Python.")
