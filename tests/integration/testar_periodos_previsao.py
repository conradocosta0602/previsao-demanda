# -*- coding: utf-8 -*-
"""
Testar: Os períodos de previsão estão alinhados entre granularidades?
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime

print("=" * 80)
print("   TESTE: ALINHAMENTO DE PERIODOS DE PREVISAO")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'
MESES_PREVISAO = 3

resultados = {}

for granularidade in ['mensal', 'semanal', 'diario']:
    print(f"\n{'='*80}")
    print(f"GRANULARIDADE: {granularidade.upper()}")
    print(f"{'='*80}")

    dados = {
        'loja': 'TODAS',
        'categoria': 'TODAS',
        'produto': 'TODOS',
        'meses_previsao': MESES_PREVISAO,
        'granularidade': granularidade
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

            # Ver última data do histórico
            hist_base = resultado.get('historico_base', {})
            datas_hist_base = hist_base.get('datas', [])
            if datas_hist_base:
                print(f"Historico BASE: {datas_hist_base[0]} ate {datas_hist_base[-1]} ({len(datas_hist_base)} periodos)")

            hist_teste = resultado.get('historico_teste', {})
            datas_hist_teste = hist_teste.get('datas', [])
            if datas_hist_teste:
                print(f"Historico TESTE: {datas_hist_teste[0]} ate {datas_hist_teste[-1]} ({len(datas_hist_teste)} periodos)")

            # Pegar o melhor modelo
            melhor_modelo = resultado.get('melhor_modelo')
            # Tentar diferentes estruturas
            previsoes = resultado.get('previsoes', resultado.get('modelos', {}))

            if melhor_modelo and melhor_modelo in previsoes:
                modelo_data = previsoes[melhor_modelo]
                futuro = modelo_data.get('futuro', {})

                datas_futuro = futuro.get('datas', [])
                valores_futuro = futuro.get('valores', [])

                if datas_futuro:
                    data_inicio = datetime.strptime(datas_futuro[0], '%Y-%m-%d')
                    data_fim = datetime.strptime(datas_futuro[-1], '%Y-%m-%d')

                    print(f"Modelo: {melhor_modelo}")
                    print(f"Periodos de previsao: {len(datas_futuro)}")
                    print(f"Data inicio: {data_inicio.strftime('%Y-%m-%d')}")
                    print(f"Data fim:    {data_fim.strftime('%Y-%m-%d')}")
                    print(f"Total previsto: {sum(valores_futuro):,.2f}")

                    # Calcular mês de início e fim
                    mes_inicio = data_inicio.strftime('%Y-%m')
                    mes_fim = data_fim.strftime('%Y-%m')
                    print(f"Mes inicio: {mes_inicio}")
                    print(f"Mes fim:    {mes_fim}")

                    resultados[granularidade] = {
                        'periodos': len(datas_futuro),
                        'data_inicio': data_inicio,
                        'data_fim': data_fim,
                        'mes_inicio': mes_inicio,
                        'mes_fim': mes_fim,
                        'total': sum(valores_futuro)
                    }
                else:
                    print("Sem dados de previsao futura")
            else:
                print(f"Modelo nao encontrado: {melhor_modelo}")
        else:
            print(f"Erro: {response.status_code}")
            print(response.text[:500])

    except Exception as e:
        print(f"Erro: {e}")

# Comparar resultados
print("\n" + "=" * 80)
print("COMPARACAO DE PERIODOS")
print("=" * 80)
print()

print(f"{'Granularidade':<15} {'Periodos':<10} {'Data Inicio':<15} {'Data Fim':<15} {'Mes Fim':<10}")
print("-" * 80)

for gran, dados in resultados.items():
    print(f"{gran:<15} {dados['periodos']:<10} {dados['data_inicio'].strftime('%Y-%m-%d'):<15} {dados['data_fim'].strftime('%Y-%m-%d'):<15} {dados['mes_fim']:<10}")

print()

# Verificar se os meses finais são iguais
meses_fim = [r['mes_fim'] for r in resultados.values()]
if len(set(meses_fim)) == 1:
    print(f"SUCESSO: Todas as granularidades terminam no mesmo mes ({meses_fim[0]})")
else:
    print(f"PROBLEMA: Granularidades terminam em meses diferentes!")
    for gran, dados in resultados.items():
        print(f"  {gran}: {dados['mes_fim']}")
