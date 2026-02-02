# -*- coding: utf-8 -*-
"""
Teste comparativo: Semanal vs Mensal - TODAS as categorias
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 80)
print("   TESTE COMPARATIVO: SEMANAL VS MENSAL")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

# Teste 1: Mensal (6 meses)
print("1️⃣  TESTE MENSAL (6 meses)")
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
        melhor_modelo = resultado.get('melhor_modelo')

        if melhor_modelo and melhor_modelo in resultado.get('modelos', {}):
            modelo_data = resultado['modelos'][melhor_modelo]
            if 'futuro' in modelo_data:
                valores_futuro = modelo_data['futuro']['valores']
                total_mensal = sum(valores_futuro)
                print(f"✅ Previsão mensal:")
                print(f"   Períodos: {len(valores_futuro)}")
                print(f"   Total previsto: {total_mensal:,.2f}")
                print(f"   Média por período: {total_mensal/len(valores_futuro):,.2f}")
                print()
except Exception as e:
    print(f"❌ Erro no teste mensal: {e}")
    import traceback
    traceback.print_exc()

print()

# Teste 2: Semanal (6 meses = 24 semanas)
print("2️⃣  TESTE SEMANAL (6 meses = 24 semanas)")
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
        melhor_modelo = resultado.get('melhor_modelo')

        if melhor_modelo and melhor_modelo in resultado.get('modelos', {}):
            modelo_data = resultado['modelos'][melhor_modelo]
            if 'futuro' in modelo_data:
                valores_futuro = modelo_data['futuro']['valores']
                total_semanal = sum(valores_futuro)
                print(f"✅ Previsão semanal:")
                print(f"   Períodos: {len(valores_futuro)}")
                print(f"   Total previsto: {total_semanal:,.2f}")
                print(f"   Média por período: {total_semanal/len(valores_futuro):,.2f}")
                print()

                # Comparação
                print("=" * 80)
                print("📊 COMPARAÇÃO")
                print("=" * 80)
                if 'total_mensal' in locals() and 'total_semanal' in locals():
                    diferenca = total_mensal - total_semanal
                    percentual = (diferenca / total_mensal) * 100
                    print(f"Total Mensal (6 meses):    {total_mensal:>15,.2f}")
                    print(f"Total Semanal (24 semanas): {total_semanal:>15,.2f}")
                    print(f"Diferença:                  {diferenca:>15,.2f} ({percentual:+.2f}%)")
                    print()

                    if abs(percentual) > 2:
                        print("⚠️  PROBLEMA: Diferença superior a 2%!")
                    else:
                        print("✅ Diferença aceitável (< 2%)")
except Exception as e:
    print(f"❌ Erro no teste semanal: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
