# -*- coding: utf-8 -*-
"""
Script para testar a API de previsão com dados agregados
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 60)
print("   TESTANDO API DE PREVISÃO - DADOS AGREGADOS")
print("=" * 60)
print()

BASE_URL = 'http://localhost:5001'

# Testar com dados agregados (todas as lojas, todos os produtos)
print("Testando previsão com TODAS as lojas e categoria Alimentos...")
print("(Isso pode levar alguns segundos...)")
print()

dados_teste = {
    'loja': 'TODAS',
    'categoria': 'Alimentos',
    'produto': 'TODOS',
    'meses_previsao': 3,
    'granularidade': 'mensal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_teste,
    headers={'Content-Type': 'application/json'},
    timeout=120
)

if response.status_code == 200:
    resultado = response.json()
    print(f"✅ Previsão gerada com sucesso!")
    print(f"Melhor Modelo: {resultado['melhor_modelo']}")
    print(f"Períodos históricos: {len(resultado['historico']['datas'])}")
    print()

    print("Métricas dos modelos:")
    for modelo, metrica in resultado['metricas'].items():
        print(f"  - {modelo}:")
        print(f"    WMAPE: {metrica['wmape']:.2f}%")
        print(f"    BIAS: {metrica['bias']:.2f}%")
        print(f"    MAE: {metrica['mae']:.2f}")
    print()

    print("Previsões geradas:")
    for modelo, dados in resultado['modelos'].items():
        print(f"  - {modelo}: {len(dados['valores'])} períodos")
        if dados['valores']:
            print(f"    Primeiros 3 valores: {[round(v, 2) for v in dados['valores'][:3]]}")

else:
    print(f"❌ Erro: {response.status_code}")
    print(f"Resposta: {response.text}")

print()
print("=" * 60)
print("   TESTE CONCLUÍDO!")
print("=" * 60)
