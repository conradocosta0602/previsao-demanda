# -*- coding: utf-8 -*-
"""
Script para testar e mostrar detalhes completos da resposta
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 70)
print("   TESTE DETALHADO - RESPOSTA COMPLETA DA API")
print("=" * 70)
print()

BASE_URL = 'http://localhost:5001'

dados_teste = {
    'loja': 'TODAS',
    'categoria': 'Alimentos',
    'produto': 'TODOS',
    'meses_previsao': 3,
    'granularidade': 'mensal'
}

print("Enviando requisição...")
response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_teste,
    headers={'Content-Type': 'application/json'},
    timeout=120
)

if response.status_code == 200:
    resultado = response.json()

    print("\n=== ESTRUTURA COMPLETA DA RESPOSTA ===\n")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    print("\n\n=== RESUMO ===")
    print(f"Melhor modelo: {resultado.get('melhor_modelo')}")
    print(f"\nMétricas retornadas: {list(resultado.get('metricas', {}).keys())}")
    print(f"Modelos com previsões: {list(resultado.get('modelos', {}).keys())}")
    print(f"\nTotal de métricas: {len(resultado.get('metricas', {}))}")
    print(f"Total de modelos com previsões: {len(resultado.get('modelos', {}))}")

else:
    print(f"❌ Erro: {response.status_code}")
    print(response.text)
