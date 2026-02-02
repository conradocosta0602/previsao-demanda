# -*- coding: utf-8 -*-
"""
Verificar: Últimas semanas do histórico combinado
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

    # Combinar todos os dados históricos
    hist_base = resultado.get('historico_base', {})
    hist_teste = resultado.get('historico_teste', {})

    datas_base = hist_base.get('datas', [])
    valores_base = hist_base.get('valores', [])
    datas_teste = hist_teste.get('datas', [])
    valores_teste = hist_teste.get('valores', [])

    # Combinar
    todas_datas = datas_base + datas_teste
    todos_valores = valores_base + valores_teste

    print("=" * 80)
    print("HISTÓRICO COMPLETO (BASE + TESTE):")
    print("=" * 80)
    print(f"Total: {len(todas_datas)} semanas")

    if todas_datas:
        print(f"Primeira: {todas_datas[0]}")
        print(f"Última: {todas_datas[-1]}")

        # Últimas 10
        print("\nÚltimas 10 semanas do histórico completo:")
        for i in range(-10, 0):
            if len(todas_datas) + i >= 0:
                data = todas_datas[i]
                valor = todos_valores[i]
                dt = datetime.strptime(data, '%Y-%m-%d')
                s = f"S{dt.isocalendar()[1]}/{dt.isocalendar()[0]}"
                print(f"  {s}: {valor:,.0f} ({data})")

    # Verificar qual é a última semana antes da previsão
    melhor_modelo = resultado.get('melhor_modelo')
    modelos = resultado.get('modelos', {})
    futuro = modelos.get(melhor_modelo, {}).get('futuro', {})
    datas_prev = futuro.get('datas', [])

    if datas_prev:
        print(f"\nPrimeira semana da previsão: {datas_prev[0]}")
        dt_prev = datetime.strptime(datas_prev[0], '%Y-%m-%d')
        print(f"  = S{dt_prev.isocalendar()[1]}/{dt_prev.isocalendar()[0]}")

else:
    print(f"Erro: {response.status_code}")
    print(response.text[:500])
