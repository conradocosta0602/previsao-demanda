# -*- coding: utf-8 -*-
"""
Debug: Verificar cálculo do período do ano anterior
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
from datetime import datetime as dt

# Simular a última data do histórico
# Baseado no banco: última data é 2026-01-07 (S2/2026)
# Mas o histórico semanal deve ser o início da última semana completa
# que é 2025-12-29 (S1/2026)

# Testar com as possíveis últimas datas
for ultima_data_hist_str in ['2025-12-29', '2026-01-05', '2025-12-22']:
    ultima_data_hist = pd.Timestamp(ultima_data_hist_str)
    print("=" * 80)
    print(f"TESTE COM ÚLTIMA DATA HISTÓRICO: {ultima_data_hist}")
    print(f"  ISO: {ultima_data_hist.isocalendar()}")
    print("=" * 80)

    meses_previsao = 3

    # Início da previsão
    inicio_previsao = ultima_data_hist + pd.Timedelta(weeks=1)
    print(f"Início previsão: {inicio_previsao}")
    print(f"  ISO: {inicio_previsao.isocalendar()}")

    # Fim da previsão
    mes_destino_calc = ultima_data_hist.month + meses_previsao
    ano_destino_calc = ultima_data_hist.year
    while mes_destino_calc > 12:
        mes_destino_calc -= 12
        ano_destino_calc += 1

    from calendar import monthrange
    ultimo_dia = monthrange(ano_destino_calc, mes_destino_calc)[1]
    fim_previsao = pd.Timestamp(year=ano_destino_calc, month=mes_destino_calc, day=ultimo_dia)
    print(f"Fim previsão: {fim_previsao}")
    print(f"  ISO: {fim_previsao.isocalendar()}")

    # Semanas
    semana_inicio = inicio_previsao.isocalendar()[1]
    ano_semana_inicio = inicio_previsao.isocalendar()[0]
    semana_fim = fim_previsao.isocalendar()[1]
    ano_semana_fim = fim_previsao.isocalendar()[0]

    print(f"\nPrevisão vai de S{semana_inicio}/{ano_semana_inicio} até S{semana_fim}/{ano_semana_fim}")

    # Ano anterior
    ano_inicio_ant = ano_semana_inicio - 1
    ano_fim_ant = ano_semana_fim - 1

    print(f"Ano anterior seria S{semana_inicio}/{ano_inicio_ant} até S{semana_fim}/{ano_fim_ant}")

    try:
        inicio_ano_anterior = pd.Timestamp(dt.strptime(f'{ano_inicio_ant}-W{semana_inicio:02d}-1', '%G-W%V-%u'))
        fim_ano_anterior = pd.Timestamp(dt.strptime(f'{ano_fim_ant}-W{semana_fim:02d}-7', '%G-W%V-%u'))
        print(f"\nPeríodo do ano anterior:")
        print(f"  Início: {inicio_ano_anterior} (S{inicio_ano_anterior.isocalendar()[1]}/{inicio_ano_anterior.isocalendar()[0]})")
        print(f"  Fim: {fim_ano_anterior} (S{fim_ano_anterior.isocalendar()[1]}/{fim_ano_anterior.isocalendar()[0]})")
    except ValueError as e:
        print(f"Erro: {e}")

    print()
