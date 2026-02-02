# -*- coding: utf-8 -*-
"""
Teste: Verificar se a correção não impactou outras granularidades
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests

print("=" * 100)
print("TESTE: VERIFICAR QUE MENSAL E SEMANAL NÃO FORAM AFETADOS")
print("=" * 100)
print()

BASE_URL = 'http://localhost:5001'

# 1. Teste Mensal
print("1. TESTE GRANULARIDADE MENSAL")
print("-" * 60)

dados_mensal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'mensal',
    'primeiro_mes_previsao': 1,
    'ano_primeiro_mes': 2026,
    'mes_destino': 3,
    'ano_destino': 2026,
    'granularidade': 'mensal'
}

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados_mensal,
        headers={'Content-Type': 'application/json'},
        timeout=180
    )

    if response.status_code == 200:
        resultado = response.json()
        melhor_modelo = resultado.get('melhor_modelo')
        futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
        datas = futuro.get('datas', [])
        valores = futuro.get('valores', [])

        print(f"Modelo: {melhor_modelo}")
        print(f"Períodos: {len(datas)}")
        total = sum(valores)
        print(f"Total: {total:,.0f}")

        if len(datas) == 3 and total > 0:
            print("✓ MENSAL: OK - Retornou 3 meses com valores")
        else:
            print("✗ MENSAL: PROBLEMA - Verificar resposta")
    else:
        print(f"✗ MENSAL: Erro {response.status_code}")
except Exception as e:
    print(f"✗ MENSAL: Erro - {e}")

print()

# 2. Teste Semanal
print("2. TESTE GRANULARIDADE SEMANAL")
print("-" * 60)

dados_semanal = {
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

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados_semanal,
        headers={'Content-Type': 'application/json'},
        timeout=180
    )

    if response.status_code == 200:
        resultado = response.json()
        melhor_modelo = resultado.get('melhor_modelo')
        futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
        datas = futuro.get('datas', [])
        valores = futuro.get('valores', [])

        print(f"Modelo: {melhor_modelo}")
        print(f"Períodos: {len(datas)}")
        total = sum(valores)
        print(f"Total: {total:,.0f}")

        if len(datas) == 12 and total > 0:
            print("✓ SEMANAL: OK - Retornou 12 semanas com valores")
        else:
            print("✗ SEMANAL: PROBLEMA - Verificar resposta")
    else:
        print(f"✗ SEMANAL: Erro {response.status_code}")
except Exception as e:
    print(f"✗ SEMANAL: Erro - {e}")

print()

# 3. Teste Diário (para confirmar correção)
print("3. TESTE GRANULARIDADE DIÁRIA")
print("-" * 60)

dados_diario = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'diario',
    'data_inicio': '2026-01-01',
    'data_fim': '2026-01-31',
    'granularidade': 'diario'
}

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados_diario,
        headers={'Content-Type': 'application/json'},
        timeout=180
    )

    if response.status_code == 200:
        resultado = response.json()
        melhor_modelo = resultado.get('melhor_modelo')
        futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
        datas = futuro.get('datas', [])
        valores = futuro.get('valores', [])

        print(f"Modelo: {melhor_modelo}")
        print(f"Períodos: {len(datas)}")
        total = sum(valores)
        print(f"Total: {total:,.0f}")

        if len(datas) == 31 and total > 0:
            print("✓ DIÁRIO: OK - Retornou 31 dias com valores")
        else:
            print("✗ DIÁRIO: PROBLEMA - Verificar resposta")
    else:
        print(f"✗ DIÁRIO: Erro {response.status_code}")
except Exception as e:
    print(f"✗ DIÁRIO: Erro - {e}")

print()
print("=" * 100)
print("RESUMO: As três granularidades devem mostrar ✓ OK")
print("=" * 100)
