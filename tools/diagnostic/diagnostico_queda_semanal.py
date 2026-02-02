# -*- coding: utf-8 -*-
"""
Diagnóstico: Queda na Previsão Semanal
Investigar por que previsão semanal está resultando em metade da mensal
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
from datetime import datetime

print("=" * 80)
print("   DIAGNÓSTICO: QUEDA NA PREVISÃO SEMANAL")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

# Teste 1: Previsão MENSAL (6 meses)
print("1️⃣  TESTE MENSAL (6 meses)")
print("-" * 80)
dados_mensal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 6,
    'granularidade': 'mensal'
}

total_mensal = None
modelo_mensal = None

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
        modelo_mensal = melhor_modelo

        if melhor_modelo and melhor_modelo in resultado.get('modelos', {}):
            modelo_data = resultado['modelos'][melhor_modelo]
            if 'futuro' in modelo_data:
                valores_futuro = modelo_data['futuro']['valores']
                total_mensal = sum(valores_futuro)
                print(f"✅ Melhor modelo: {melhor_modelo}")
                print(f"   Períodos: {len(valores_futuro)}")
                print(f"   Total previsto: {total_mensal:,.2f}")
                print(f"   Média por período: {total_mensal/len(valores_futuro):,.2f}")
                print()

                # Mostrar valores individuais
                print("   Valores mensais:")
                datas = modelo_data['futuro']['datas']
                for i, (data, valor) in enumerate(zip(datas, valores_futuro), 1):
                    print(f"      Mês {i} ({data}): {valor:>12,.2f}")
                print()
except Exception as e:
    print(f"❌ Erro no teste mensal: {e}")
    import traceback
    traceback.print_exc()

print()

# Teste 2: Previsão SEMANAL (6 meses = 24 semanas)
print("2️⃣  TESTE SEMANAL (6 meses = 24 semanas)")
print("-" * 80)
dados_semanal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 6,
    'granularidade': 'semanal'
}

total_semanal = None
modelo_semanal = None
fatores_semanais = {}

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
        modelo_semanal = melhor_modelo

        if melhor_modelo and melhor_modelo in resultado.get('modelos', {}):
            modelo_data = resultado['modelos'][melhor_modelo]
            if 'futuro' in modelo_data:
                valores_futuro = modelo_data['futuro']['valores']
                datas_futuro = modelo_data['futuro']['datas']
                total_semanal = sum(valores_futuro)

                print(f"✅ Melhor modelo: {melhor_modelo}")
                print(f"   Períodos: {len(valores_futuro)}")
                print(f"   Total previsto: {total_semanal:,.2f}")
                print(f"   Média por período: {total_semanal/len(valores_futuro):,.2f}")
                print()

                # Analisar valores individuais e identificar semanas com quedas
                print("   Análise detalhada (primeiras 12 semanas):")
                min_val = min(valores_futuro)
                max_val = max(valores_futuro)
                media_val = total_semanal / len(valores_futuro)

                for i in range(min(12, len(valores_futuro))):
                    data_str = datas_futuro[i]
                    valor = valores_futuro[i]

                    # Extrair semana do ano da data
                    try:
                        data_obj = datetime.strptime(data_str, '%Y-%m-%d')
                        semana_ano = data_obj.isocalendar()[1]
                    except:
                        semana_ano = "?"

                    # Calcular % da média
                    pct_media = (valor / media_val - 1) * 100

                    # Marcar valores extremos
                    marcador = ""
                    if valor == min_val:
                        marcador = "🔴 MÍNIMO"
                    elif valor == max_val:
                        marcador = "🟢 MÁXIMO"
                    elif valor < media_val * 0.7:
                        marcador = "⚠️  BAIXO"
                    elif valor > media_val * 1.3:
                        marcador = "⬆️  ALTO"

                    print(f"      S{semana_ano:>2} ({data_str}): {valor:>12,.2f}  ({pct_media:>+6.1f}% média)  {marcador}")

                print()
                print(f"   Min: {min_val:,.2f}  |  Média: {media_val:,.2f}  |  Max: {max_val:,.2f}")
                print(f"   Amplitude: {(max_val - min_val):,.2f} ({(max_val/min_val - 1)*100:.1f}%)")
                print()

except Exception as e:
    print(f"❌ Erro no teste semanal: {e}")
    import traceback
    traceback.print_exc()

print()

# Comparação Final
if total_mensal is not None and total_semanal is not None:
    print("=" * 80)
    print("📊 COMPARAÇÃO MENSAL vs SEMANAL")
    print("=" * 80)
    print()

    print(f"Modelo Mensal:  {modelo_mensal}")
    print(f"Modelo Semanal: {modelo_semanal}")
    print()

    print(f"Total Mensal (6 meses):     {total_mensal:>15,.2f}")
    print(f"Total Semanal (24 semanas): {total_semanal:>15,.2f}")
    print()

    diferenca = total_mensal - total_semanal
    percentual = (diferenca / total_mensal) * 100

    print(f"Diferença:                  {diferenca:>15,.2f} ({percentual:+.2f}%)")
    print()

    # Diagnóstico
    if percentual > 50:
        print("🔴 CRÍTICO: Semanal é METADE da mensal!")
        print("   Possíveis causas:")
        print("   1. Fatores sazonais muito baixos para semanas futuras")
        print("   2. Tendência de queda sendo amplificada na granularidade semanal")
        print("   3. Dados históricos com forte sazonalidade no período de previsão")
    elif percentual > 25:
        print("⚠️  ALERTA: Diferença muito alta (>25%)")
        print("   Investigar fatores sazonais e tendência")
    elif percentual > 15:
        print("⚠️  ATENÇÃO: Diferença acima do esperado (>15%)")
        print("   Pode haver sazonalidade forte no período")
    elif percentual > -15:
        print("✅ OK: Diferença dentro do esperado (-15% a +15%)")
    else:
        print("🔵 INFO: Semanal maior que mensal")

print()
print("=" * 80)
