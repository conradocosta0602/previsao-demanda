# -*- coding: utf-8 -*-
"""
Diagnóstico: Por que a previsão mostra S1/2025 em vez de S1/2026?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

BASE_URL = 'http://localhost:5001'

dados = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'semanal',
    'semana_inicio': 1,
    'ano_semana_inicio': 2026,
    'semana_fim': 12,
    'ano_semana_fim': 2026,
    'granularidade': 'semanal'
}

print("=" * 80)
print("DIAGNÓSTICO: DATAS DA PREVISÃO SEMANAL")
print("=" * 80)
print(f"Período solicitado: S1/2026 até S12/2026")
print()

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados,
    headers={'Content-Type': 'application/json'},
    timeout=180
)

if response.status_code == 200:
    resultado = response.json()

    melhor_modelo = resultado.get('melhor_modelo')
    print(f"Melhor modelo: {melhor_modelo}")
    print()

    # Previsão futura
    futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
    datas_futuro = futuro.get('datas', [])
    valores_futuro = futuro.get('valores', [])

    print("PREVISÃO FUTURA (linha roxa / linha 'Previsão'):")
    print("-" * 80)
    print(f"Total de períodos: {len(datas_futuro)}")
    print()

    for i, (data_str, valor) in enumerate(zip(datas_futuro, valores_futuro)):
        dt = datetime.strptime(data_str, '%Y-%m-%d')
        iso_year, iso_week, _ = dt.isocalendar()
        print(f"  {i+1}. Data: {data_str} -> ISO: S{iso_week}/{iso_year} | Valor: {valor:,.0f}")

    print()
    print("=" * 80)
    print("ANÁLISE:")
    print("=" * 80)

    if datas_futuro:
        primeira_data = datetime.strptime(datas_futuro[0], '%Y-%m-%d')
        iso_year, iso_week, _ = primeira_data.isocalendar()

        print(f"Primeira data retornada: {datas_futuro[0]}")
        print(f"Ano ISO dessa data: {iso_year}")
        print(f"Semana ISO dessa data: {iso_week}")
        print()

        if iso_year == 2025:
            print("PROBLEMA IDENTIFICADO:")
            print("  A data 2025-12-29 pertence à SEMANA 1 de 2026 pelo calendário ISO!")
            print("  Isso porque a semana ISO 1 de 2026 começa em 29/12/2025 (segunda-feira).")
            print()
            print("  MAS o isocalendar() do Python retorna:")
            print(f"    {primeira_data.date()}.isocalendar() = {primeira_data.isocalendar()}")
            print()
            print("  Vamos verificar:")

            # Verificar manualmente
            from datetime import date
            d = date(2025, 12, 29)
            print(f"    date(2025, 12, 29).isocalendar() = {d.isocalendar()}")

            d2 = date(2026, 1, 5)
            print(f"    date(2026, 1, 5).isocalendar() = {d2.isocalendar()}")

else:
    print(f"Erro: {response.status_code}")
    print(response.text[:500])
