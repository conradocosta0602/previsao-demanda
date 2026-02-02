# -*- coding: utf-8 -*-
"""
Debug: Ver qual período está sendo buscado para ano anterior
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from datetime import datetime as dt

# Simular o cálculo que o código faz

# Última data do histórico (aproximadamente 7 jan 2026 baseado no que vimos)
ultima_data_hist = pd.Timestamp('2025-12-29')  # Última segunda-feira completa

print("=" * 80)
print("   DEBUG: CÁLCULO DO PERÍODO ANO ANTERIOR")
print("=" * 80)
print()
print(f"Última data histórico: {ultima_data_hist}")
print(f"  ISO: {ultima_data_hist.isocalendar()}")

meses_previsao = 12  # 12 meses

# Cálculo igual ao código
inicio_previsao = ultima_data_hist + pd.Timedelta(weeks=1)
print(f"\nInício previsão: {inicio_previsao}")
print(f"  ISO: {inicio_previsao.isocalendar()}")

# Data fim
mes_destino_calc = ultima_data_hist.month + meses_previsao
ano_destino_calc = ultima_data_hist.year
while mes_destino_calc > 12:
    mes_destino_calc -= 12
    ano_destino_calc += 1

from calendar import monthrange
ultimo_dia = monthrange(ano_destino_calc, mes_destino_calc)[1]
fim_previsao = pd.Timestamp(year=ano_destino_calc, month=mes_destino_calc, day=ultimo_dia)
print(f"\nFim previsão: {fim_previsao}")
print(f"  ISO: {fim_previsao.isocalendar()}")

# Calcular semanas
semana_inicio = inicio_previsao.isocalendar()[1]
ano_semana_inicio = inicio_previsao.isocalendar()[0]
semana_fim = fim_previsao.isocalendar()[1]
ano_semana_fim = fim_previsao.isocalendar()[0]

print(f"\nPeríodo previsão: S{semana_inicio}/{ano_semana_inicio} até S{semana_fim}/{ano_semana_fim}")

# Ano anterior
ano_inicio_ant = ano_semana_inicio - 1
ano_fim_ant = ano_semana_fim - 1

print(f"\nAno anterior calculado: S{semana_inicio}/{ano_inicio_ant} até S{semana_fim}/{ano_fim_ant}")

# Converter para datas
try:
    inicio_ano_anterior = pd.Timestamp(dt.strptime(f'{ano_inicio_ant}-W{semana_inicio:02d}-1', '%G-W%V-%u'))
    fim_ano_anterior = pd.Timestamp(dt.strptime(f'{ano_fim_ant}-W{semana_fim:02d}-7', '%G-W%V-%u'))
    print(f"\nPeríodo buscado para ano anterior:")
    print(f"  Início: {inicio_ano_anterior}")
    print(f"  Fim: {fim_ano_anterior}")
except ValueError as e:
    print(f"Erro: {e}")

# Verificar quais semanas estão nesse range
print("\n" + "=" * 80)
print("SEMANAS QUE SERIAM BUSCADAS:")
print("=" * 80)

import psycopg2
conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

cursor.execute("""
    WITH dados_diarios AS (
        SELECT
            h.data,
            SUM(h.qtd_venda) as qtd_venda
        FROM historico_vendas_diario h
        WHERE h.data >= %s AND h.data <= %s
        GROUP BY h.data
    )
    SELECT
        DATE_TRUNC('week', data)::date as data,
        EXTRACT(ISOYEAR FROM data) as iso_ano,
        EXTRACT(WEEK FROM data) as semana,
        SUM(qtd_venda) as qtd_venda
    FROM dados_diarios
    GROUP BY DATE_TRUNC('week', data), EXTRACT(ISOYEAR FROM data), EXTRACT(WEEK FROM data)
    ORDER BY DATE_TRUNC('week', data)
""", (inicio_ano_anterior.strftime('%Y-%m-%d'), fim_ano_anterior.strftime('%Y-%m-%d')))

rows = cursor.fetchall()
print(f"\nTotal de semanas encontradas: {len(rows)}")
for row in rows[:10]:
    print(f"  {row[0]}: ISO {int(row[1])}-S{int(row[2])}, Total: {row[3]:,.0f}")
if len(rows) > 10:
    print(f"  ...")
    for row in rows[-5:]:
        print(f"  {row[0]}: ISO {int(row[1])}-S{int(row[2])}, Total: {row[3]:,.0f}")

conn.close()
