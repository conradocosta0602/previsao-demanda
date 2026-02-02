# -*- coding: utf-8 -*-
"""
Teste com TODAS as categorias
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 80)
print("   TESTE: TODAS AS CATEGORIAS")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

dados_teste = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 12,
    'granularidade': 'mensal'
}

print("Enviando requisição...")
print(f"Parâmetros: {json.dumps(dados_teste, indent=2)}")
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
        print(f"Melhor modelo: {melhor_modelo}")
        print()

        if melhor_modelo and melhor_modelo in resultado.get('modelos', {}):
            modelo_data = resultado['modelos'][melhor_modelo]

            if 'futuro' in modelo_data:
                valores_futuro = modelo_data['futuro']['valores']
                valores_unicos = len(set(valores_futuro))

                print(f"Previsões futuras:")
                print(f"  Total: {len(valores_futuro)} períodos")
                print(f"  Valores únicos: {valores_unicos}")

                if valores_unicos > 1:
                    print(f"  ✅ Variam corretamente!")
                    print(f"  Min: {min(valores_futuro):,.2f}")
                    print(f"  Max: {max(valores_futuro):,.2f}")
                    amplitude = max(valores_futuro) - min(valores_futuro)
                    variacao_pct = (amplitude / min(valores_futuro)) * 100
                    print(f"  Amplitude: {amplitude:,.2f} ({variacao_pct:.2f}%)")
                else:
                    print(f"  ⚠️  Todos os valores são iguais: {valores_futuro[0]:,.2f}")

            print()

            if 'teste' in modelo_data:
                valores_teste = modelo_data['teste']['valores']
                valores_unicos_teste = len(set(valores_teste))

                print(f"Previsões de teste:")
                print(f"  Total: {len(valores_teste)} períodos")
                print(f"  Valores únicos: {valores_unicos_teste}")

                if valores_unicos_teste > 1:
                    print(f"  ✅ Variam corretamente!")
                    print(f"  Min: {min(valores_teste):,.2f}")
                    print(f"  Max: {max(valores_teste):,.2f}")
                else:
                    print(f"  ⚠️  Todos os valores são iguais: {valores_teste[0]:,.2f}")

        print()
        print("=" * 80)

    else:
        print(f"❌ ERRO: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Exceção: {e}")
    import traceback
    traceback.print_exc()
