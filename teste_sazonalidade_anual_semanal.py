# -*- coding: utf-8 -*-
"""
Teste: Validar sazonalidade anual semanal (52 semanas)
Verificar se semana 50 da previsão é influenciada por semanas 50 históricas
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 80)
print("   TESTE: SAZONALIDADE ANUAL SEMANAL (52 SEMANAS)")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

# Teste com granularidade semanal
dados_teste = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 12,  # 48 semanas
    'granularidade': 'semanal'
}

print("📋 Parâmetros:")
print(f"   Categoria: {dados_teste['categoria']}")
print(f"   Meses: {dados_teste['meses_previsao']} (≈ 48 semanas)")
print(f"   Granularidade: {dados_teste['granularidade']}")
print()

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados_teste,
        headers={'Content-Type': 'application/json'},
        timeout=120
    )

    if response.status_code == 200:
        resultado = response.json()
        melhor_modelo = resultado.get('melhor_modelo')

        print(f"✅ Resposta recebida!")
        print(f"   Melhor modelo: {melhor_modelo}")
        print()

        if melhor_modelo and melhor_modelo in resultado.get('modelos', {}):
            modelo_data = resultado['modelos'][melhor_modelo]

            # Analisar previsões futuras
            if 'futuro' in modelo_data:
                datas_futuro = modelo_data['futuro']['datas']
                valores_futuro = modelo_data['futuro']['valores']

                print("=" * 80)
                print("📊 ANÁLISE DE SAZONALIDADE ANUAL")
                print("=" * 80)
                print()

                # Calcular variação
                valores_unicos = set(valores_futuro)
                min_val = min(valores_futuro)
                max_val = max(valores_futuro)
                amplitude = max_val - min_val

                # Evitar divisão por zero
                if min_val > 0:
                    variacao_pct = (amplitude / min_val) * 100
                else:
                    print("⚠️  AVISO: Valor mínimo é zero - usando média para cálculo")
                    media_val = sum(valores_futuro) / len(valores_futuro) if valores_futuro else 1
                    variacao_pct = (amplitude / media_val) * 100 if media_val > 0 else 0

                print(f"Total de períodos: {len(valores_futuro)}")
                print(f"Valores únicos: {len(valores_unicos)}")
                print(f"Valor mínimo: {min_val:,.2f}")
                print(f"Valor máximo: {max_val:,.2f}")
                print(f"Amplitude: {amplitude:,.2f} ({variacao_pct:.2f}%)")
                print()

                # Verificar se variação é significativa
                if variacao_pct > 10:
                    print(f"✅ SUCESSO: Variação significativa ({variacao_pct:.2f}%)")
                    print("   Fatores sazonais estão capturando padrão anual!")
                elif variacao_pct > 5:
                    print(f"⚠️  MODERADO: Variação moderada ({variacao_pct:.2f}%)")
                    print("   Pode haver padrão sazonal suave")
                else:
                    print(f"❌ PROBLEMA: Variação muito baixa ({variacao_pct:.2f}%)")
                    print("   Previsões ainda muito lineares")

                print()
                print("=" * 80)
                print("📅 AMOSTRA DAS PREVISÕES (primeiras 10 semanas)")
                print("=" * 80)
                print()

                for i in range(min(10, len(datas_futuro))):
                    data = datas_futuro[i]
                    valor = valores_futuro[i]
                    print(f"  {data}: {valor:>12,.2f}")

                print()
                print("=" * 80)

            # Verificar dados históricos
            if 'historico_base' in resultado:
                base = resultado['historico_base']
                print()
                print("📈 DADOS HISTÓRICOS:")
                print(f"   Períodos: {len(base['datas'])}")
                print(f"   Primeira data: {base['datas'][0]}")
                print(f"   Última data: {base['datas'][-1]}")
                valores_base = base['valores']
                min_hist = min(valores_base)
                max_hist = max(valores_base)
                amp_hist = max_hist - min_hist
                var_hist = (amp_hist / min_hist) * 100
                print(f"   Variação histórica: {var_hist:.2f}%")
                print(f"   (Min: {min_hist:,.2f}, Max: {max_hist:,.2f})")

    else:
        print(f"❌ ERRO: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Exceção: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
