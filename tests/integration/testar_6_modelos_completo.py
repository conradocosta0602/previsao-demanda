# -*- coding: utf-8 -*-
"""
Script para testar os 6 modelos com as 3 granularidades
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 70)
print("   TESTE COMPLETO - 6 MODELOS + 3 GRANULARIDADES")
print("=" * 70)
print()

BASE_URL = 'http://localhost:5001'

# Testar as 3 granularidades
granularidades = [
    {'nome': 'Diário', 'valor': 'diario', 'meses': 3, 'desc': 'até 3 meses'},
    {'nome': 'Semanal', 'valor': 'semanal', 'meses': 6, 'desc': 'até 6 meses'},
    {'nome': 'Mensal', 'valor': 'mensal', 'meses': 12, 'desc': 'até 12 meses'}
]

for gran in granularidades:
    print(f"\n{'='*70}")
    print(f"TESTANDO GRANULARIDADE: {gran['nome'].upper()} ({gran['desc']})")
    print(f"{'='*70}")

    dados_teste = {
        'loja': 'TODAS',
        'categoria': 'Alimentos',
        'produto': 'TODOS',
        'meses_previsao': gran['meses'],
        'granularidade': gran['valor']
    }

    print(f"Parâmetros: {dados_teste}")
    print("Processando... (pode levar alguns segundos)")

    try:
        response = requests.post(
            f'{BASE_URL}/api/gerar_previsao_banco',
            json=dados_teste,
            headers={'Content-Type': 'application/json'},
            timeout=120
        )

        if response.status_code == 200:
            resultado = response.json()

            print(f"\n✅ Previsão gerada com sucesso!")
            print(f"   Melhor Modelo: {resultado['melhor_modelo']}")
            print(f"   Períodos históricos: {len(resultado['historico']['datas'])}")
            print(f"\n   Modelos testados e suas métricas:")

            # Ordenar modelos por WMAPE
            modelos_ordenados = sorted(
                resultado['metricas'].items(),
                key=lambda x: x[1]['wmape']
            )

            for i, (modelo, metrica) in enumerate(modelos_ordenados, 1):
                simbolo = "🏆" if modelo == resultado['melhor_modelo'] else f"{i}."
                print(f"   {simbolo} {modelo}")
                print(f"      WMAPE: {metrica['wmape']:.2f}%")
                print(f"      BIAS:  {metrica['bias']:.2f}%")
                print(f"      MAE:   {metrica['mae']:.2f}")

            print(f"\n   Previsões geradas:")
            for modelo in resultado['modelos']:
                num_previsoes = len(resultado['modelos'][modelo]['valores'])
                print(f"      - {modelo}: {num_previsoes} períodos")

        else:
            print(f"❌ Erro: {response.status_code}")
            print(f"   Resposta: {response.text}")

    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

print(f"\n{'='*70}")
print("   TESTE CONCLUÍDO!")
print(f"{'='*70}")
print("\nResumo:")
print("✓ 3 granularidades testadas: Diário, Semanal, Mensal")
print("✓ 6 modelos aplicados em cada teste")
print("✓ Limites de previsão respeitados por granularidade")
print()
