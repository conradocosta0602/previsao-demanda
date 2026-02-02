# -*- coding: utf-8 -*-
"""
Teste: Validar correção da defasagem do dia da semana
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

print("=" * 100)
print("TESTE: VALIDAÇÃO DA CORREÇÃO DE DEFASAGEM DO DIA DA SEMANA")
print("=" * 100)
print()

BASE_URL = 'http://localhost:5001'

# Fazer consulta diária
dados = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'diario',
    'data_inicio': '2026-01-01',
    'data_fim': '2026-01-31',
    'granularidade': 'diario'
}

print("Consultando API...")
try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados,
        headers={'Content-Type': 'application/json'},
        timeout=180
    )
except requests.exceptions.ConnectionError:
    print("ERRO: Servidor não está rodando em localhost:5001")
    print("Execute 'python app.py' para iniciar o servidor")
    sys.exit(1)

if response.status_code == 200:
    resultado = response.json()
    melhor_modelo = resultado.get('melhor_modelo')
    futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
    datas = futuro.get('datas', [])
    valores = futuro.get('valores', [])

    print(f"Modelo: {melhor_modelo}")
    print(f"Períodos: {len(datas)}")
    print()

    dias_semana_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

    # Agrupar por dia da semana
    previsao_por_dow = {}
    contagem_por_dow = {}

    for d, v in zip(datas, valores):
        dt = datetime.strptime(d, '%Y-%m-%d')
        dow = dt.weekday()  # Python: 0=Segunda, 6=Domingo
        if dow not in previsao_por_dow:
            previsao_por_dow[dow] = 0
            contagem_por_dow[dow] = 0
        previsao_por_dow[dow] += v
        contagem_por_dow[dow] += 1

    media_geral = sum(valores) / len(valores) if valores else 0

    print("PREVISÃO POR DIA DA SEMANA (após correção):")
    print("-" * 60)
    print(f"{'Dia':<12} {'Média':>12} {'Variação':>10} {'Status':>15}")
    print("-" * 60)

    # Verificar se Sábado e Domingo estão com fator alto
    sabado_ok = False
    domingo_ok = False
    segunda_ok = True

    for dow in range(7):
        dia = dias_semana_pt[dow]
        if dow in previsao_por_dow and contagem_por_dow[dow] > 0:
            media = previsao_por_dow[dow] / contagem_por_dow[dow]
            var = ((media - media_geral) / media_geral * 100) if media_geral > 0 else 0
            sinal = "+" if var >= 0 else ""

            # Verificar expectativas
            if dow == 5:  # Sábado
                status = "✓ CORRETO" if var > 10 else "✗ ERRO (deveria ser alto)"
                sabado_ok = var > 10
            elif dow == 6:  # Domingo
                status = "✓ CORRETO" if var > 10 else "✗ ERRO (deveria ser alto)"
                domingo_ok = var > 10
            elif dow == 0:  # Segunda
                status = "✓ CORRETO" if var < 5 else "✗ ERRO (deveria ser baixo)"
                segunda_ok = var < 5
            else:
                status = "✓ OK" if abs(var) < 15 else "?"

            print(f"{dia:<12} {media:>12,.0f} {sinal}{var:>8.1f}% {status:>15}")

    print()
    print("=" * 60)
    print("RESULTADO DO TESTE:")
    print("=" * 60)

    if sabado_ok and domingo_ok and segunda_ok:
        print("✓ SUCESSO: A defasagem foi corrigida!")
        print("  - Sábado está com variação positiva (pico)")
        print("  - Domingo está com variação positiva (pico)")
        print("  - Segunda está com variação normal/baixa")
    else:
        print("✗ FALHA: Ainda há problemas na sazonalidade:")
        if not sabado_ok:
            print("  - Sábado deveria ter variação > 10%")
        if not domingo_ok:
            print("  - Domingo deveria ter variação > 10%")
        if not segunda_ok:
            print("  - Segunda deveria ter variação < 5%")
else:
    print(f"Erro na API: {response.status_code}")
    print(response.text)
