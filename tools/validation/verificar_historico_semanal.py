# -*- coding: utf-8 -*-
"""
Verificar: Qual é o histórico semanal que a API está usando?
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
    'meses_previsao': 3,
    'granularidade': 'semanal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados,
    headers={'Content-Type': 'application/json'},
    timeout=180
)

if response.status_code == 200:
    resultado = response.json()

    # Histórico Base
    hist_base = resultado.get('historico_base', {})
    datas_base = hist_base.get('datas', [])
    valores_base = hist_base.get('valores', [])

    print("=" * 80)
    print("HISTÓRICO BASE (50%):")
    print("=" * 80)
    print(f"Total: {len(datas_base)} semanas")
    if datas_base:
        print(f"Primeira: {datas_base[0]}")
        print(f"Última: {datas_base[-1]}")

        # Últimas 5
        print("\nÚltimas 5 semanas da base:")
        for i in range(-5, 0):
            if len(datas_base) + i >= 0:
                data = datas_base[i]
                valor = valores_base[i]
                dt = datetime.strptime(data, '%Y-%m-%d')
                s = f"S{dt.isocalendar()[1]}/{dt.isocalendar()[0]}"
                print(f"  {s}: {valor:,.0f} ({data})")

    # Histórico Teste
    hist_teste = resultado.get('historico_teste', {})
    datas_teste = hist_teste.get('datas', [])
    valores_teste = hist_teste.get('valores', [])

    print()
    print("=" * 80)
    print("HISTÓRICO TESTE (25%):")
    print("=" * 80)
    print(f"Total: {len(datas_teste)} semanas")
    if datas_teste:
        print(f"Primeira: {datas_teste[0]}")
        print(f"Última: {datas_teste[-1]}")

        # Últimas 5
        print("\nÚltimas 5 semanas do teste:")
        for i in range(-5, 0):
            if len(datas_teste) + i >= 0:
                data = datas_teste[i]
                valor = valores_teste[i]
                dt = datetime.strptime(data, '%Y-%m-%d')
                s = f"S{dt.isocalendar()[1]}/{dt.isocalendar()[0]}"
                print(f"  {s}: {valor:,.0f} ({data})")

    # Previsão Futura
    melhor_modelo = resultado.get('melhor_modelo')
    modelos = resultado.get('modelos', {})
    futuro = modelos.get(melhor_modelo, {}).get('futuro', {})
    datas_prev = futuro.get('datas', [])
    valores_prev = futuro.get('valores', [])

    print()
    print("=" * 80)
    print("PREVISÃO FUTURA:")
    print("=" * 80)
    print(f"Total: {len(datas_prev)} semanas")
    if datas_prev:
        print(f"Primeira: {datas_prev[0]}")
        print(f"Última: {datas_prev[-1]}")

        # Primeiras 5
        print("\nPrimeiras 5 semanas da previsão:")
        for i in range(min(5, len(datas_prev))):
            data = datas_prev[i]
            valor = valores_prev[i]
            dt = datetime.strptime(data, '%Y-%m-%d')
            s = f"S{dt.isocalendar()[1]}/{dt.isocalendar()[0]}"
            print(f"  {s}: {valor:,.0f} ({data})")

else:
    print(f"Erro: {response.status_code}")
    print(response.text[:500])
