# -*- coding: utf-8 -*-
"""
Debug simples: Ver dados retornados da API
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
    'meses_previsao': 3,  # Apenas 3 meses para simplificar
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

    ano_anterior = resultado.get('ano_anterior', {})
    datas_aa = ano_anterior.get('datas', [])
    valores_aa = ano_anterior.get('valores', [])

    melhor_modelo = resultado.get('melhor_modelo')
    modelos = resultado.get('modelos', {})
    futuro = modelos.get(melhor_modelo, {}).get('futuro', {})
    datas_prev = futuro.get('datas', [])
    valores_prev = futuro.get('valores', [])

    print(f"Total previsões: {len(datas_prev)}")
    print(f"Total ano anterior: {len(datas_aa)}")
    print()

    print("Comparação:")
    print("-" * 80)
    for i in range(min(len(datas_prev), 15)):
        data_p = datas_prev[i] if i < len(datas_prev) else None
        valor_p = valores_prev[i] if i < len(valores_prev) else None
        data_a = datas_aa[i] if i < len(datas_aa) else None
        valor_a = valores_aa[i] if i < len(valores_aa) else None

        if data_p:
            dt_p = datetime.strptime(data_p, '%Y-%m-%d')
            s_p = f"S{dt_p.isocalendar()[1]}/{dt_p.year}"
        else:
            s_p = "-"

        if data_a:
            dt_a = datetime.strptime(data_a, '%Y-%m-%d')
            s_a = f"S{dt_a.isocalendar()[1]}/{dt_a.year}"
        else:
            s_a = "-"

        print(f"{i+1}. Prev: {s_p:<12} {valor_p:>10,.0f} | Ant: {s_a:<12} {valor_a if valor_a else 0:>10,.0f}")

else:
    print(f"Erro: {response.status_code}")
    print(response.text[:500])
