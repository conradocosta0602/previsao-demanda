# -*- coding: utf-8 -*-
"""
Verificar estrutura dos dados retornados
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

BASE_URL = 'http://localhost:5001'

dados = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'semanal',
    'semana_inicio': 1,
    'ano_semana_inicio': 2026,
    'semana_fim': 12,
    'ano_semana_fim': 2026,
    'granularidade': 'semanal'
}

print("=" * 80)
print("ESTRUTURA DOS DADOS RETORNADOS")
print("=" * 80)

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados,
    headers={'Content-Type': 'application/json'},
    timeout=180
)

if response.status_code == 200:
    resultado = response.json()

    melhor_modelo = resultado.get('melhor_modelo')

    # Previsão futura (linha roxa)
    futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
    print(f"\n1. PREVISÃO FUTURA (linha roxa no gráfico / linha 'Previsão' na tabela):")
    print(f"   Quantidade de períodos: {len(futuro.get('valores', []))}")
    if futuro.get('datas'):
        print(f"   Primeiro: {futuro['datas'][0]}")
        print(f"   Último: {futuro['datas'][-1]}")

    # Histórico teste (linha verde sólida)
    hist_teste = resultado.get('historico_teste', {})
    print(f"\n2. HISTÓRICO TESTE (linha verde sólida no gráfico / deveria ser linha 'Real' na tabela):")
    print(f"   Quantidade de períodos: {len(hist_teste.get('valores', []))}")
    if hist_teste.get('datas'):
        print(f"   Primeiro: {hist_teste['datas'][0]}")
        print(f"   Último: {hist_teste['datas'][-1]}")

    # Ano anterior (linha laranja)
    ano_ant = resultado.get('ano_anterior', {})
    print(f"\n3. ANO ANTERIOR (linha laranja no gráfico):")
    print(f"   Quantidade de períodos: {len(ano_ant.get('valores', []))}")
    if ano_ant.get('datas'):
        print(f"   Primeiro: {ano_ant['datas'][0]}")
        print(f"   Último: {ano_ant['datas'][-1]}")

    print("\n" + "=" * 80)
    print("PROBLEMA IDENTIFICADO:")
    print("=" * 80)
    print(f"- Previsão futura tem {len(futuro.get('valores', []))} períodos")
    print(f"- Histórico teste tem {len(hist_teste.get('valores', []))} períodos")
    print(f"- São períodos DIFERENTES!")
    print()
    print("A tabela comparativa deveria mostrar:")
    print("- Linha 'Previsão': dados da previsão futura (S1-S12/2026)")
    print("- Linha 'Real': dados do MESMO período do ano anterior (S1-S12/2025)")
    print()
    print("Portanto, a linha 'Real' deveria usar ANO_ANTERIOR, não HISTORICO_TESTE")

else:
    print(f"Erro: {response.status_code}")
