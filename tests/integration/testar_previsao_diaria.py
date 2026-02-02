# -*- coding: utf-8 -*-
"""
Testar: Previsão diária está aplicando sazonalidade?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

print("=" * 80)
print("   TESTE: PREVISÃO DIÁRIA")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

dados_diario = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 1,  # 1 mês = ~30 dias
    'granularidade': 'diario'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_diario,
    headers={'Content-Type': 'application/json'},
    timeout=120
)

if response.status_code == 200:
    resultado = response.json()

    melhor_modelo = resultado.get('melhor_modelo')
    print(f"Melhor modelo: {melhor_modelo}")
    print()

    # Verificar histórico teste
    if 'historico_teste' in resultado:
        hist_teste = resultado['historico_teste']
        valores_teste = hist_teste.get('valores', [])
        datas_teste = hist_teste.get('datas', [])

        print(f"HISTÓRICO TESTE: {len(valores_teste)} períodos")
        if valores_teste:
            print(f"Primeiros 7 valores:")
            for i in range(min(7, len(valores_teste))):
                data_obj = datetime.strptime(datas_teste[i], '%Y-%m-%d')
                dia_semana = data_obj.strftime('%A')
                print(f"   {datas_teste[i]} ({dia_semana}): {valores_teste[i]:>12,.2f}")
            print()

    # Verificar previsão futura
    if 'modelos' in resultado and melhor_modelo in resultado['modelos']:
        modelo = resultado['modelos'][melhor_modelo]

        if 'futuro' in modelo:
            futuro = modelo['futuro']
            valores = futuro['valores']
            datas = futuro['datas']

            print(f"PREVISÃO FUTURA: {len(valores)} períodos")
            print()

            # Mostrar primeiros 14 valores (2 semanas)
            print("Primeiros 14 dias:")
            for i in range(min(14, len(valores))):
                data_obj = datetime.strptime(datas[i], '%Y-%m-%d')
                dia_semana = data_obj.strftime('%A')
                print(f"   {datas[i]} ({dia_semana}): {valores[i]:>12,.2f}")

            print()

            # Analisar variação
            min_val = min(valores)
            max_val = max(valores)
            amplitude = max_val - min_val
            media = sum(valores) / len(valores)
            variacao_pct = (amplitude / media) * 100 if media > 0 else 0

            print(f"Mínimo:    {min_val:>12,.2f}")
            print(f"Máximo:    {max_val:>12,.2f}")
            print(f"Amplitude: {amplitude:>12,.2f}")
            print(f"Média:     {media:>12,.2f}")
            print(f"Variação:  {variacao_pct:>12.2f}%")
            print()

            # Verificar se todos os valores são iguais
            valores_unicos = len(set([round(v, 2) for v in valores]))
            if valores_unicos == 1:
                print("🔴 PROBLEMA CRÍTICO: Todos os valores são IDÊNTICOS!")
            elif variacao_pct < 5:
                print("🔴 PROBLEMA: Previsão está LINEAR (variação < 5%)")
            else:
                print("✅ Previsão tem variação")

            # Verificar se há padrão semanal (dias da semana)
            print()
            print("Análise por dia da semana:")
            por_dia = {}
            for i, v in enumerate(valores[:14]):  # Primeiras 2 semanas
                data_obj = datetime.strptime(datas[i], '%Y-%m-%d')
                dia = data_obj.weekday()
                nome_dia = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][dia]
                if nome_dia not in por_dia:
                    por_dia[nome_dia] = []
                por_dia[nome_dia].append(v)

            for dia, vals in por_dia.items():
                media_dia = sum(vals) / len(vals)
                print(f"   {dia}: {media_dia:>12,.2f}")

        else:
            print("❌ Não há previsão futura no modelo")
    else:
        print("❌ Modelo não encontrado")
else:
    print(f"❌ Erro na API: {response.status_code}")

print()
print("=" * 80)
