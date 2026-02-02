# -*- coding: utf-8 -*-
"""
Validação: Histórico via API deve ser idêntico entre granularidades
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 80)
print("   VALIDAÇÃO: HISTÓRICO VIA API")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

# Teste 1: Mensal
print("1️⃣  HISTÓRICO MENSAL (via API)")
print("-" * 80)

dados_mensal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 6,
    'granularidade': 'mensal'
}

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados_mensal,
        headers={'Content-Type': 'application/json'},
        timeout=120
    )

    if response.status_code == 200:
        resultado = response.json()

        if 'historico_base' in resultado:
            hist_base = resultado['historico_base']
            valores_mensal = hist_base['valores']
            datas_mensal = hist_base['datas']

            total_mensal = sum(valores_mensal)

            print(f"Total períodos: {len(valores_mensal)}")
            print(f"Total histórico: {total_mensal:,.2f}")
            print()

            print("Últimos 6 valores:")
            for i in range(max(0, len(valores_mensal)-6), len(valores_mensal)):
                print(f"   {datas_mensal[i]}: {valores_mensal[i]:>12,.2f}")
            print()

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

# Teste 2: Semanal
print("2️⃣  HISTÓRICO SEMANAL (via API)")
print("-" * 80)

dados_semanal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 6,
    'granularidade': 'semanal'
}

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados_semanal,
        headers={'Content-Type': 'application/json'},
        timeout=120
    )

    if response.status_code == 200:
        resultado = response.json()

        if 'historico_base' in resultado:
            hist_base = resultado['historico_base']
            valores_semanal = hist_base['valores']
            datas_semanal = hist_base['datas']

            total_semanal = sum(valores_semanal)

            print(f"Total períodos: {len(valores_semanal)}")
            print(f"Total histórico: {total_semanal:,.2f}")
            print()

            print("Últimos 24 valores:")
            for i in range(max(0, len(valores_semanal)-24), len(valores_semanal)):
                from datetime import datetime
                data_obj = datetime.strptime(datas_semanal[i], '%Y-%m-%d')
                semana = data_obj.isocalendar()[1]
                print(f"   S{semana:>2} ({datas_semanal[i]}): {valores_semanal[i]:>12,.2f}")
            print()

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

# Comparação
print("=" * 80)
print("📊 COMPARAÇÃO")
print("=" * 80)
print()

if 'total_mensal' in locals() and 'total_semanal' in locals():
    print(f"Total MENSAL:  {total_mensal:>15,.2f}")
    print(f"Total SEMANAL: {total_semanal:>15,.2f}")
    print()

    diferenca = total_mensal - total_semanal
    pct_diferenca = (diferenca / total_mensal) * 100

    print(f"Diferença:     {diferenca:>15,.2f}  ({pct_diferenca:+.2f}%)")
    print()

    if abs(pct_diferenca) < 0.1:
        print("✅ SUCESSO: Históricos são idênticos!")
    elif abs(pct_diferenca) < 1.0:
        print("⚠️  ATENÇÃO: Pequena diferença (<1%)")
        print("   Pode ser devido a outliers removidos ou arredondamentos")
    else:
        print(f"🔴 PROBLEMA: Diferença de {abs(pct_diferenca):.2f}% é muito alta!")
        print("   Históricos deveriam ser idênticos (±0.1%)")

print()
print("=" * 80)
