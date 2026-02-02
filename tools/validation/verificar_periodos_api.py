# -*- coding: utf-8 -*-
"""
Verificar períodos exatos retornados pela API
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
from datetime import datetime

print("=" * 80)
print("   VERIFICAÇÃO: PERÍODOS EXATOS DA API")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

# Teste 1: Mensal
print("1️⃣  MENSAL")
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
    hist = resultado['historico_base']

    datas = hist['datas']
    valores = hist['valores']

    print(f"Períodos: {len(datas)}")
    print(f"Data início: {datas[0]}")
    print(f"Data fim: {datas[-1]}")
    print(f"Total: {sum(valores):,.2f}")
    print()

    print("Primeiros 3 períodos:")
    for i in range(min(3, len(datas))):
        print(f"   {datas[i]}: {valores[i]:>12,.2f}")
    print()

    print("Últimos 3 períodos:")
    for i in range(max(0, len(datas)-3), len(datas)):
        print(f"   {datas[i]}: {valores[i]:>12,.2f}")
    print()

    total_mensal = sum(valores)
    datas_mensal = datas

# Teste 2: Semanal
print("2️⃣  SEMANAL")
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
    hist = resultado['historico_base']

    datas = hist['datas']
    valores = hist['valores']

    print(f"Períodos: {len(datas)}")
    print(f"Data início: {datas[0]}")
    print(f"Data fim: {datas[-1]}")
    print(f"Total: {sum(valores):,.2f}")
    print()

    print("Primeiros 3 períodos:")
    for i in range(min(3, len(datas))):
        semana = datetime.strptime(datas[i], '%Y-%m-%d').isocalendar()[1]
        print(f"   S{semana:>2} ({datas[i]}): {valores[i]:>12,.2f}")
    print()

    print("Últimos 3 períodos:")
    for i in range(max(0, len(datas)-3), len(datas)):
        semana = datetime.strptime(datas[i], '%Y-%m-%d').isocalendar()[1]
        print(f"   S{semana:>2} ({datas[i]}): {valores[i]:>12,.2f}")
    print()

    total_semanal = sum(valores)
    datas_semanal = datas

# Análise
print("=" * 80)
print("📊 ANÁLISE")
print("=" * 80)
print()

print(f"Total MENSAL:  {total_mensal:>15,.2f}")
print(f"Total SEMANAL: {total_semanal:>15,.2f}")
diferenca = total_mensal - total_semanal
pct = (diferenca / total_mensal) * 100
print(f"Diferença:     {diferenca:>15,.2f}  ({pct:+.2f}%)")
print()

# Converter datas para objetos datetime
data_inicio_mensal = datetime.strptime(datas_mensal[0], '%Y-%m-%d')
data_fim_mensal = datetime.strptime(datas_mensal[-1], '%Y-%m-%d')
data_inicio_semanal = datetime.strptime(datas_semanal[0], '%Y-%m-%d')
data_fim_semanal = datetime.strptime(datas_semanal[-1], '%Y-%m-%d')

print("Cobertura temporal:")
print(f"  Mensal:  {data_inicio_mensal.date()} até {data_fim_mensal.date()}")
print(f"  Semanal: {data_inicio_semanal.date()} até {data_fim_semanal.date()}")
print()

# Verificar se as datas se sobrepõem
if data_inicio_mensal == data_inicio_semanal and data_fim_mensal == data_fim_semanal:
    print("✅ Datas de início e fim são idênticas")
elif data_inicio_mensal != data_inicio_semanal:
    diff_dias = (data_inicio_semanal - data_inicio_mensal).days
    print(f"⚠️  Data início difere em {diff_dias} dias")
elif data_fim_mensal != data_fim_semanal:
    diff_dias = (data_fim_semanal - data_fim_mensal).days
    print(f"⚠️  Data fim difere em {diff_dias} dias")
else:
    print("⚠️  Datas não cobrem o mesmo período")

print()
print("=" * 80)
