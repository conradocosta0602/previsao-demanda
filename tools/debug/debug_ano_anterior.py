# -*- coding: utf-8 -*-
"""
Debug: Verificar alinhamento de semanas entre previsão e ano anterior
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

print("=" * 80)
print("   DEBUG: ALINHAMENTO SEMANAS PREVISÃO vs ANO ANTERIOR")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

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

        # Previsão
        melhor_modelo = resultado.get('melhor_modelo')
        previsoes = resultado.get('modelos', {})
        modelo_data = previsoes.get(melhor_modelo, {})
        futuro = modelo_data.get('futuro', {})
        datas_futuro = futuro.get('datas', [])
        valores_futuro = futuro.get('valores', [])

        print(f"Total de períodos na previsão: {len(datas_futuro)}")
        print(f"Total de períodos no ano anterior: {len(datas_ano_anterior)}")
        print()

        print("COMPARAÇÃO POSIÇÃO A POSIÇÃO:")
        print("-" * 100)
        print(f"{'Pos':<5} {'Data Prev':<15} {'Sem/Ano':<12} {'Previsão':>12} | {'Data Ant':<15} {'Sem/Ano':<12} {'Real':>12} | {'Match':>6}")
        print("-" * 100)

        max_rows = max(len(datas_futuro), len(datas_ano_anterior))

        for i in range(max_rows):
            # Previsão
            if i < len(datas_futuro):
                dt_prev = datetime.strptime(datas_futuro[i], '%Y-%m-%d')
                sem_prev = f"S{dt_prev.isocalendar()[1]}/{dt_prev.year}"
                val_prev = valores_futuro[i]
            else:
                dt_prev = None
                sem_prev = "-"
                val_prev = "-"

            # Ano anterior
            if i < len(datas_ano_anterior):
                dt_ant = datetime.strptime(datas_ano_anterior[i], '%Y-%m-%d')
                sem_ant = f"S{dt_ant.isocalendar()[1]}/{dt_ant.year}"
                val_ant = valores_ano_anterior[i]
            else:
                dt_ant = None
                sem_ant = "-"
                val_ant = "-"

            # Verificar se as semanas correspondem (mesma semana do ano)
            match = ""
            if dt_prev and dt_ant:
                if dt_prev.isocalendar()[1] == dt_ant.isocalendar()[1]:
                    match = "OK"
                else:
                    match = f"DIFF ({dt_ant.isocalendar()[1] - dt_prev.isocalendar()[1]:+d})"

            print(f"{i+1:<5} {datas_futuro[i] if i < len(datas_futuro) else '-':<15} {sem_prev:<12} {val_prev if isinstance(val_prev, str) else f'{val_prev:>12,.0f}':>12} | {datas_ano_anterior[i] if i < len(datas_ano_anterior) else '-':<15} {sem_ant:<12} {val_ant if isinstance(val_ant, str) else f'{val_ant:>12,.0f}':>12} | {match:>6}")

        # Resumo
        print()
        print("=" * 80)
        print("RESUMO:")
        print("=" * 80)

        # Contar matches corretos
        matches = 0
        mismatches = 0
        for i in range(min(len(datas_futuro), len(datas_ano_anterior))):
            dt_prev = datetime.strptime(datas_futuro[i], '%Y-%m-%d')
            dt_ant = datetime.strptime(datas_ano_anterior[i], '%Y-%m-%d')
            if dt_prev.isocalendar()[1] == dt_ant.isocalendar()[1]:
                matches += 1
            else:
                mismatches += 1

        print(f"Semanas correspondentes (mesma semana do ano): {matches}")
        print(f"Semanas NÃO correspondentes: {mismatches}")

        if mismatches > 0:
            print("\nPROBLEMA IDENTIFICADO: As semanas do ano anterior não correspondem às semanas da previsão!")
            print("Isso significa que a comparação está errada (comparando semanas diferentes do ano).")

    else:
        print(f"Erro: {response.status_code}")
        print(response.text[:500])

except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
