# -*- coding: utf-8 -*-
"""
Script para testar a API de previsão com dados do banco
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 60)
print("   TESTANDO API DE PREVISÃO - BANCO DE DADOS")
print("=" * 60)
print()

# Configuração
BASE_URL = 'http://localhost:5001'

# 1. Testar API de Lojas
print("1. Testando /api/lojas...")
response = requests.get(f'{BASE_URL}/api/lojas')
if response.status_code == 200:
    lojas = response.json()
    print(f"   ✅ {len(lojas)} lojas encontradas")
    print(f"   Primeira loja: {lojas[0]}")
else:
    print(f"   ❌ Erro: {response.status_code}")

print()

# 2. Testar API de Categorias
print("2. Testando /api/categorias...")
response = requests.get(f'{BASE_URL}/api/categorias')
if response.status_code == 200:
    categorias = response.json()
    print(f"   ✅ {len(categorias)} categorias encontradas")
    print(f"   Categorias: {categorias[:3]}")
else:
    print(f"   ❌ Erro: {response.status_code}")

print()

# 3. Testar API de Produtos
print("3. Testando /api/produtos...")
response = requests.get(f'{BASE_URL}/api/produtos')
if response.status_code == 200:
    produtos = response.json()
    print(f"   ✅ {len(produtos)} produtos encontrados")
    print(f"   Primeiro produto: {produtos[0]}")
else:
    print(f"   ❌ Erro: {response.status_code}")

print()

# 4. Testar Geração de Previsão
print("4. Testando /api/gerar_previsao_banco...")
print("   (Isso pode levar alguns segundos...)")

dados_teste = {
    'loja': '1',
    'categoria': 'Alimentos',
    'produto': '1001',
    'meses_previsao': 3,
    'granularidade': 'mensal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_teste,
    headers={'Content-Type': 'application/json'}
)

if response.status_code == 200:
    resultado = response.json()
    print(f"   ✅ Previsão gerada com sucesso!")
    print(f"   Melhor Modelo: {resultado['melhor_modelo']}")
    print(f"   Modelos testados: {list(resultado['metricas'].keys())}")
    print(f"   Períodos históricos: {len(resultado['historico']['datas'])}")

    print("\n   Métricas dos modelos:")
    for modelo, metrica in resultado['metricas'].items():
        print(f"   - {modelo}: WMAPE={metrica['wmape']:.2f}%, BIAS={metrica['bias']:.2f}%")

    print("\n   Previsões geradas:")
    for modelo, dados in resultado['modelos'].items():
        print(f"   - {modelo}: {len(dados['valores'])} períodos")
        print(f"     Primeiros valores: {dados['valores'][:3]}")

else:
    print(f"   ❌ Erro: {response.status_code}")
    print(f"   Resposta: {response.text}")

print()
print("=" * 60)
print("   TESTE CONCLUÍDO!")
print("=" * 60)
