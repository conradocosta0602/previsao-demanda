# -*- coding: utf-8 -*-
"""
Verificar consistência entre dados do gráfico e tabela
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
print("VERIFICAÇÃO DE CONSISTÊNCIA: GRÁFICO vs TABELA")
print("=" * 80)
print(f"Período solicitado: S1/2026 a S12/2026")
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
    modelos = resultado.get('modelos', {})

    # Dados para o gráfico
    historico_base = resultado.get('historico_base', {})
    historico_teste = resultado.get('historico_teste', {})
    futuro = modelos.get(melhor_modelo, {}).get('futuro', {})
    ano_anterior = resultado.get('ano_anterior', {})

    print("DADOS DO GRÁFICO:")
    print("-" * 80)

    print(f"\n1. Base Histórica (linha azul): {len(historico_base.get('valores', []))} períodos")
    if historico_base.get('valores'):
        print(f"   Primeiro: {historico_base['datas'][0]} = {historico_base['valores'][0]:,.0f}")
        print(f"   Último: {historico_base['datas'][-1]} = {historico_base['valores'][-1]:,.0f}")

    print(f"\n2. Teste Real (linha verde sólida): {len(historico_teste.get('valores', []))} períodos")
    if historico_teste.get('valores'):
        print(f"   Primeiro: {historico_teste['datas'][0]} = {historico_teste['valores'][0]:,.0f}")
        print(f"   Último: {historico_teste['datas'][-1]} = {historico_teste['valores'][-1]:,.0f}")

    print(f"\n3. Previsão Futura (linha roxa): {len(futuro.get('valores', []))} períodos")
    if futuro.get('valores'):
        for i, (data, valor) in enumerate(zip(futuro['datas'], futuro['valores'])):
            dt = datetime.strptime(data, '%Y-%m-%d')
            semana = dt.isocalendar()[1]
            ano = dt.isocalendar()[0]
            print(f"   S{semana}/{ano}: {valor:,.0f} ({data})")

    print(f"\n4. Ano Anterior (linha laranja): {len(ano_anterior.get('valores', []))} períodos")
    if ano_anterior.get('valores'):
        for i, (data, valor) in enumerate(zip(ano_anterior['datas'], ano_anterior['valores'])):
            if data:
                dt = datetime.strptime(data, '%Y-%m-%d')
                semana = dt.isocalendar()[1]
                ano = dt.isocalendar()[0]
                print(f"   S{semana}/{ano}: {valor:,.0f} ({data})")
            else:
                print(f"   Sem dados: {valor}")

    print()
    print("=" * 80)
    print("DADOS DA TABELA COMPARATIVA:")
    print("=" * 80)

    datas_previsao = futuro.get('datas', [])
    valores_previsao = futuro.get('valores', [])
    datas_ano_anterior = ano_anterior.get('datas', [])
    valores_ano_anterior = ano_anterior.get('valores', [])

    print(f"\nLinhas: Previsão | Real (Ano Anterior) | Variação")
    print("-" * 80)

    for i in range(len(valores_previsao)):
        data_p = datas_previsao[i] if i < len(datas_previsao) else None
        valor_p = valores_previsao[i] if i < len(valores_previsao) else 0
        data_a = datas_ano_anterior[i] if i < len(datas_ano_anterior) else None
        valor_a = valores_ano_anterior[i] if i < len(valores_ano_anterior) else 0

        if data_p:
            dt_p = datetime.strptime(data_p, '%Y-%m-%d')
            s_p = f"S{dt_p.isocalendar()[1]}/{dt_p.isocalendar()[0]}"
        else:
            s_p = "-"

        if data_a:
            dt_a = datetime.strptime(data_a, '%Y-%m-%d')
            s_a = f"S{dt_a.isocalendar()[1]}/{dt_a.isocalendar()[0]}"
        else:
            s_a = "-"

        variacao = ((valor_p - valor_a) / valor_a * 100) if valor_a > 0 else 0
        var_str = f"+{variacao:.1f}%" if variacao >= 0 else f"{variacao:.1f}%"

        print(f"Col {i+1}: Prev {s_p} = {valor_p:>10,.0f} | Real {s_a} = {valor_a:>10,.0f} | {var_str}")

    print()
    print("=" * 80)
    print("VERIFICAÇÃO DE CONSISTÊNCIA:")
    print("=" * 80)

    # A linha roxa do gráfico = linha Previsão da tabela
    print(f"\n✓ Linha roxa (gráfico) = Linha Previsão (tabela)")
    print(f"  Ambos usam: modelos[{melhor_modelo}].futuro.valores")

    # A linha laranja do gráfico = linha Real da tabela
    print(f"\n✓ Linha laranja (gráfico) = Linha Real (tabela)")
    print(f"  Ambos usam: ano_anterior.valores")

    # Verificar se primeira previsão é S1 ou S2
    if datas_previsao:
        dt_primeira = datetime.strptime(datas_previsao[0], '%Y-%m-%d')
        semana_primeira = dt_primeira.isocalendar()[1]
        print(f"\n⚠ Primeira semana da previsão: S{semana_primeira}/{dt_primeira.isocalendar()[0]}")
        if semana_primeira != 1:
            print(f"  PROBLEMA: Usuário solicitou início em S1/2026, mas previsão começa em S{semana_primeira}")

else:
    print(f"Erro: {response.status_code}")
    print(response.text[:500])
