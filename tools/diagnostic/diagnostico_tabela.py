# -*- coding: utf-8 -*-
"""
Diagnóstico: Estrutura dos dados para tabela comparativa
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

BASE_URL = 'http://localhost:5001'

# Teste com granularidade DIÁRIA
dados = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'diario',
    'data_inicio': '2026-03-01',
    'data_fim': '2026-04-30',
    'granularidade': 'diario'
}

print("=" * 80)
print("DIAGNÓSTICO: ESTRUTURA DOS DADOS PARA TABELA COMPARATIVA")
print("=" * 80)
print(f"Período solicitado: {dados['data_inicio']} até {dados['data_fim']}")
print(f"Granularidade: {dados['granularidade']}")
print()

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados,
    headers={'Content-Type': 'application/json'},
    timeout=180
)

if response.status_code == 200:
    resultado = response.json()

    melhor_modelo = resultado.get('melhor_modelo')
    print(f"Melhor modelo: {melhor_modelo}")
    print()

    # 1. Previsão futura (linha roxa / linha "Previsão" da tabela)
    futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
    datas_futuro = futuro.get('datas', [])
    valores_futuro = futuro.get('valores', [])

    print("1. PREVISÃO FUTURA (usado na linha 'Previsão' da tabela):")
    print(f"   Total de períodos: {len(datas_futuro)}")
    if datas_futuro:
        print(f"   Primeiro: {datas_futuro[0]}")
        print(f"   Último: {datas_futuro[-1]}")
        print("   Primeiros 10:")
        for i in range(min(10, len(datas_futuro))):
            print(f"      {i+1}. {datas_futuro[i]} = {valores_futuro[i]:,.0f}")

    # 2. Histórico teste (linha verde sólida / atualmente usado na linha "Real" da tabela)
    hist_teste = resultado.get('historico_teste', {})
    datas_teste = hist_teste.get('datas', [])
    valores_teste = hist_teste.get('valores', [])

    print()
    print("2. HISTÓRICO TESTE (atualmente usado na linha 'Real' da tabela):")
    print(f"   Total de períodos: {len(datas_teste)}")
    if datas_teste:
        print(f"   Primeiro: {datas_teste[0]}")
        print(f"   Último: {datas_teste[-1]}")
        print("   Primeiros 10:")
        for i in range(min(10, len(datas_teste))):
            print(f"      {i+1}. {datas_teste[i]} = {valores_teste[i]:,.0f}")

    # 3. Ano anterior
    ano_ant = resultado.get('ano_anterior', {})
    datas_ano_ant = ano_ant.get('datas', [])
    valores_ano_ant = ano_ant.get('valores', [])

    print()
    print("3. ANO ANTERIOR:")
    print(f"   Total de períodos: {len(datas_ano_ant)}")
    if datas_ano_ant:
        print(f"   Primeiro: {datas_ano_ant[0]}")
        print(f"   Último: {datas_ano_ant[-1]}")
        print("   Primeiros 10:")
        for i in range(min(10, len(datas_ano_ant))):
            print(f"      {i+1}. {datas_ano_ant[i]} = {valores_ano_ant[i]:,.0f}")

    print()
    print("=" * 80)
    print("PROBLEMA IDENTIFICADO:")
    print("=" * 80)
    print()
    print("A tabela comparativa ATUALMENTE usa:")
    print("  - Linha 'Previsão': modelos[melhorModelo].futuro (correto)")
    print("  - Linha 'Real': historico_teste (INCORRETO!)")
    print()
    print("O historico_teste contém dados do período de VALIDAÇÃO do modelo,")
    print("que são períodos DIFERENTES dos períodos de previsão.")
    print()
    print("SOLUÇÃO CORRETA:")
    print("  - Linha 'Previsão': modelos[melhorModelo].futuro")
    print("  - Linha 'Real': ano_anterior (mesmo período do ano passado)")
    print()
    print("Isso garante que:")
    print("  - 01/03/2026 (previsão) seja comparado com 01/03/2025 (real)")
    print("  - S1/2026 (previsão) seja comparado com S1/2025 (real)")
    print("  - Jan/2026 (previsão) seja comparado com Jan/2025 (real)")

else:
    print(f"Erro: {response.status_code}")
    print(response.text[:500])
