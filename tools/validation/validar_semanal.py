# -*- coding: utf-8 -*-
"""
Validar: Previsão semanal - comparar semanas específicas
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime, timedelta

print("=" * 80)
print("   VALIDAÇÃO: PREVISÃO SEMANAL - 12 PERÍODOS")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

# Fazer consulta semanal com 12 períodos
dados = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 12,
    'granularidade': 'semanal'
}

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados,
        headers={'Content-Type': 'application/json'},
        timeout=180
    )

    if response.status_code == 200:
        resultado = response.json()

        # Dados do ano anterior
        ano_anterior = resultado.get('ano_anterior', {})
        datas_ano_anterior = ano_anterior.get('datas', [])
        valores_ano_anterior = ano_anterior.get('valores', [])

        print("DADOS DO ANO ANTERIOR (2025):")
        print("-" * 80)
        for i, (data, valor) in enumerate(zip(datas_ano_anterior, valores_ano_anterior)):
            dt = datetime.strptime(data, '%Y-%m-%d')
            semana = dt.isocalendar()[1]
            print(f"  S{semana}/25: {valor:,.0f} ({data})")
        print()

        # Pegar o melhor modelo
        melhor_modelo = resultado.get('melhor_modelo')
        previsoes = resultado.get('modelos', {})

        if melhor_modelo and melhor_modelo in previsoes:
            modelo_data = previsoes[melhor_modelo]
            futuro = modelo_data.get('futuro', {})

            datas_futuro = futuro.get('datas', [])
            valores_futuro = futuro.get('valores', [])

            print(f"PREVISÕES ({melhor_modelo}):")
            print("-" * 80)
            for i, (data, valor) in enumerate(zip(datas_futuro, valores_futuro)):
                dt = datetime.strptime(data, '%Y-%m-%d')
                semana = dt.isocalendar()[1]

                # Comparar com ano anterior (mesma semana)
                valor_ano_ant = None
                for j, data_ant in enumerate(datas_ano_anterior):
                    dt_ant = datetime.strptime(data_ant, '%Y-%m-%d')
                    if dt_ant.isocalendar()[1] == semana:
                        valor_ano_ant = valores_ano_anterior[j]
                        break

                if valor_ano_ant:
                    var = ((valor - valor_ano_ant) / valor_ano_ant) * 100
                    print(f"  S{semana}/26: {valor:,.0f} ({data}) | S{semana}/25: {valor_ano_ant:,.0f} | Var: {var:+.1f}%")
                else:
                    print(f"  S{semana}/26: {valor:,.0f} ({data})")

            print()

            # Semanas específicas mencionadas pelo usuário
            semanas_interesse = [3, 9, 10, 11]
            print("=" * 80)
            print("ANÁLISE DAS SEMANAS MENCIONADAS:")
            print("=" * 80)

            for semana in semanas_interesse:
                # Previsão 2026
                prev_26 = None
                for i, data in enumerate(datas_futuro):
                    dt = datetime.strptime(data, '%Y-%m-%d')
                    if dt.isocalendar()[1] == semana:
                        prev_26 = valores_futuro[i]
                        break

                # Ano anterior 2025
                valor_25 = None
                for i, data in enumerate(datas_ano_anterior):
                    dt = datetime.strptime(data, '%Y-%m-%d')
                    if dt.isocalendar()[1] == semana:
                        valor_25 = valores_ano_anterior[i]
                        break

                print(f"\nSemana {semana}:")
                if prev_26 and valor_25:
                    var = ((prev_26 - valor_25) / valor_25) * 100
                    print(f"  S{semana}/26 (previsão): {prev_26:,.0f}")
                    print(f"  S{semana}/25 (real):     {valor_25:,.0f}")
                    print(f"  Variação: {var:+.1f}%")
                else:
                    print(f"  Dados não encontrados")

        # Verificar histórico base para semanas de 2024
        hist_base = resultado.get('historico_base', {})
        datas_hist = hist_base.get('datas', [])
        valores_hist = hist_base.get('valores', [])

        print()
        print("=" * 80)
        print("HISTÓRICO 2024 (SEMANAS 1-12):")
        print("=" * 80)

        for i, (data, valor) in enumerate(zip(datas_hist, valores_hist)):
            dt = datetime.strptime(data, '%Y-%m-%d')
            if dt.year == 2024 and dt.isocalendar()[1] <= 12:
                semana = dt.isocalendar()[1]
                print(f"  S{semana}/24: {valor:,.0f} ({data})")

    else:
        print(f"Erro: {response.status_code}")
        print(response.text[:500])

except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
