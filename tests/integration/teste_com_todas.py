# -*- coding: utf-8 -*-
"""
Teste com a string "TODAS - Todas as Categorias" que vem do dropdown
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 70)
print("   TESTE COM STRING COMPLETA DO DROPDOWN")
print("=" * 70)
print()

BASE_URL = 'http://localhost:5001'

# Simular exatamente o que vem do navegador
dados = {
    'loja': '📊 Todas as Lojas (Agregado)',  # Como vem do dropdown
    'categoria': 'TODAS - Todas as Categorias',  # Como vem do dropdown
    'produto': '📦 Todos os Produtos (Agregado)',  # Como vem do dropdown
    'meses_previsao': 12,
    'granularidade': 'mensal'
}

print("Dados enviados (simulando navegador):")
print(json.dumps(dados, indent=2, ensure_ascii=False))
print()

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados,
        headers={'Content-Type': 'application/json'},
        timeout=60
    )

    print(f"Status: {response.status_code}")
    print()

    if response.status_code == 200:
        resultado = response.json()
        print("✅ SUCESSO!")
        print(f"Períodos históricos: {len(resultado['historico']['datas'])}")
        print(f"Modelos gerados: {len(resultado['modelos'])}")
        print(f"Melhor modelo: {resultado['melhor_modelo']}")
        print(f"\nModelos: {list(resultado['modelos'].keys())}")
    else:
        print("❌ ERRO!")
        print(response.text)

except Exception as e:
    print(f"❌ Exceção: {e}")
