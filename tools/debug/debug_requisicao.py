# -*- coding: utf-8 -*-
"""
Debug: testar requisição com filtros agregados
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 70)
print("   DEBUG - TESTANDO REQUISIÇÃO COM FILTROS AGREGADOS")
print("=" * 70)
print()

BASE_URL = 'http://localhost:5001'

# Testar com filtros agregados
configs = [
    {
        'nome': 'Teste 1: Mensal, 6 meses',
        'dados': {
            'loja': 'TODAS',
            'categoria': 'Alimentos',
            'produto': 'TODOS',
            'meses_previsao': 6,
            'granularidade': 'mensal'
        }
    },
    {
        'nome': 'Teste 2: Mensal, 12 meses',
        'dados': {
            'loja': 'TODAS',
            'categoria': 'Alimentos',
            'produto': 'TODOS',
            'meses_previsao': 12,
            'granularidade': 'mensal'
        }
    },
    {
        'nome': 'Teste 3: Semanal, 6 meses',
        'dados': {
            'loja': 'TODAS',
            'categoria': 'Alimentos',
            'produto': 'TODOS',
            'meses_previsao': 6,
            'granularidade': 'semanal'
        }
    }
]

for config in configs:
    print(f"\n{'='*70}")
    print(f"{config['nome']}")
    print(f"{'='*70}")
    print(f"Parâmetros: {json.dumps(config['dados'], indent=2)}")

    try:
        response = requests.post(
            f'{BASE_URL}/api/gerar_previsao_banco',
            json=config['dados'],
            headers={'Content-Type': 'application/json'},
            timeout=60
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            resultado = response.json()
            print(f"✅ Sucesso!")
            print(f"   Períodos históricos: {len(resultado['historico']['datas'])}")
            print(f"   Modelos gerados: {len(resultado['modelos'])}")
            print(f"   Melhor modelo: {resultado['melhor_modelo']}")
        else:
            print(f"❌ Erro!")
            erro = response.json()
            print(f"   Mensagem: {erro.get('erro', 'Erro desconhecido')}")
            if 'detalhes' in erro:
                print(f"   Detalhes: {json.dumps(erro['detalhes'], indent=6)}")

    except Exception as e:
        print(f"❌ Exceção: {e}")

print(f"\n{'='*70}")
print("   DEBUG CONCLUÍDO")
print(f"{'='*70}")
