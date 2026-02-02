# -*- coding: utf-8 -*-
"""
Testar: Previsão está aplicando sazonalidade?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
from datetime import datetime

print("=" * 80)
print("   TESTE: SAZONALIDADE NAS PREVISÕES")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

# Teste 1: SEMANAL
print("1️⃣  PREVISÃO SEMANAL")
print("-" * 80)

dados_semanal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 6,
    'granularidade': 'semanal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_semanal,
    headers={'Content-Type': 'application/json'},
    timeout=120
)

if response.status_code == 200:
    resultado = response.json()

    melhor_modelo = resultado.get('melhor_modelo')
    print(f"Melhor modelo: {melhor_modelo}")
    print()

    # Verificar se há previsão futura
    if 'modelos' in resultado and melhor_modelo in resultado['modelos']:
        modelo = resultado['modelos'][melhor_modelo]

        if 'futuro' in modelo:
            futuro = modelo['futuro']
            valores = futuro['valores']
            datas = futuro['datas']

            print(f"Total períodos futuros: {len(valores)}")
            print()

            # Mostrar primeiros 12 valores
            print("Primeiras 12 semanas:")
            for i in range(min(12, len(valores))):
                data_obj = datetime.strptime(datas[i], '%Y-%m-%d')
                semana = data_obj.isocalendar()[1]
                print(f"   S{semana:>2} ({datas[i]}): {valores[i]:>12,.2f}")

            print()

            # Analisar variação
            min_val = min(valores)
            max_val = max(valores)
            amplitude = max_val - min_val
            media = sum(valores) / len(valores)
            variacao_pct = (amplitude / media) * 100 if media > 0 else 0

            print(f"Mínimo:    {min_val:>12,.2f}")
            print(f"Máximo:    {max_val:>12,.2f}")
            print(f"Amplitude: {amplitude:>12,.2f}")
            print(f"Média:     {media:>12,.2f}")
            print(f"Variação:  {variacao_pct:>12.2f}%")
            print()

            if variacao_pct < 5:
                print("🔴 PROBLEMA: Previsão está LINEAR!")
                print("   Variação < 5% indica que não há sazonalidade aplicada")
            else:
                print("✅ Previsão tem variação sazonal")
        else:
            print("❌ Não há previsão futura no modelo")
    else:
        print("❌ Modelo não encontrado")
else:
    print(f"❌ Erro na API: {response.status_code}")

print()

# Teste 2: MENSAL
print("2️⃣  PREVISÃO MENSAL")
print("-" * 80)

dados_mensal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 6,
    'granularidade': 'mensal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_mensal,
    headers={'Content-Type': 'application/json'},
    timeout=120
)

if response.status_code == 200:
    resultado = response.json()

    melhor_modelo = resultado.get('melhor_modelo')
    print(f"Melhor modelo: {melhor_modelo}")
    print()

    # Verificar se há previsão futura
    if 'modelos' in resultado and melhor_modelo in resultado['modelos']:
        modelo = resultado['modelos'][melhor_modelo]

        if 'futuro' in modelo:
            futuro = modelo['futuro']
            valores = futuro['valores']
            datas = futuro['datas']

            print(f"Total períodos futuros: {len(valores)}")
            print()

            # Mostrar todos os valores
            print("Todos os meses:")
            for i in range(len(valores)):
                data_obj = datetime.strptime(datas[i], '%Y-%m-%d')
                print(f"   {data_obj.strftime('%Y-%m')}: {valores[i]:>12,.2f}")

            print()

            # Analisar variação
            min_val = min(valores)
            max_val = max(valores)
            amplitude = max_val - min_val
            media = sum(valores) / len(valores)
            variacao_pct = (amplitude / media) * 100 if media > 0 else 0

            print(f"Mínimo:    {min_val:>12,.2f}")
            print(f"Máximo:    {max_val:>12,.2f}")
            print(f"Amplitude: {amplitude:>12,.2f}")
            print(f"Média:     {media:>12,.2f}")
            print(f"Variação:  {variacao_pct:>12.2f}%")
            print()

            if variacao_pct < 5:
                print("🔴 PROBLEMA: Previsão está LINEAR!")
                print("   Variação < 5% indica que não há sazonalidade aplicada")
            else:
                print("✅ Previsão tem variação sazonal")
        else:
            print("❌ Não há previsão futura no modelo")
    else:
        print("❌ Modelo não encontrado")
else:
    print(f"❌ Erro na API: {response.status_code}")

print()
print("=" * 80)
