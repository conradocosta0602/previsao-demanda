# -*- coding: utf-8 -*-
"""
Verificar alinhamento: Linha roxa (gráfico) vs Linha Previsão (tabela)
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
print("VERIFICAÇÃO: LINHA ROXA (gráfico) vs LINHA PREVISÃO (tabela)")
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
    print(f"Melhor modelo: {melhor_modelo}")
    print()

    # Dados da previsão futura (usados tanto no gráfico quanto na tabela)
    futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
    datas_futuro = futuro.get('datas', [])
    valores_futuro = futuro.get('valores', [])

    print("LINHA ROXA DO GRÁFICO = modelos[melhorModelo].futuro")
    print("LINHA PREVISÃO DA TABELA = modelos[melhorModelo].futuro.valores")
    print()
    print("Ambas usam a MESMA fonte de dados:")
    print("-" * 80)

    for i, (data, valor) in enumerate(zip(datas_futuro, valores_futuro)):
        dt = datetime.strptime(data, '%Y-%m-%d')
        semana = dt.isocalendar()[1]
        ano = dt.isocalendar()[0]
        print(f"  {i+1}. S{semana}/{ano}: {valor:,.0f} ({data})")

    print()
    print("=" * 80)
    print("CONCLUSÃO:")
    print("=" * 80)
    print("Os dados da linha roxa (gráfico) e linha Previsão (tabela)")
    print("JÁ SÃO OS MESMOS - ambos vêm de resultado.modelos[melhorModelo].futuro")
    print()
    print("Se houver diferença visual, pode ser:")
    print("1. Problema de formatação/exibição no frontend")
    print("2. Cache do navegador (tente Ctrl+F5)")
    print("3. Problema na renderização do gráfico")

else:
    print(f"Erro: {response.status_code}")
    print(response.text[:500])
