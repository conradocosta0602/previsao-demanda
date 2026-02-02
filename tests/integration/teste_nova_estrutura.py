# -*- coding: utf-8 -*-
"""
Teste da nova estrutura com divisão de dados (50% base / 25% teste / 25% previsão)
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

print("=" * 70)
print("   TESTE - NOVA ESTRUTURA DE DADOS")
print("=" * 70)
print()

BASE_URL = 'http://localhost:5001'

# Testar com configuração mensal simples
dados_teste = {
    'loja': 'TODAS',
    'categoria': 'Alimentos',
    'produto': 'TODOS',
    'meses_previsao': 6,
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

        print("✅ SUCESSO!")
        print()
        print("=== ESTRUTURA DA RESPOSTA ===")
        print()

        # Verificar estrutura base histórica
        if 'historico_base' in resultado:
            print(f"✓ historico_base encontrado:")
            print(f"  - {len(resultado['historico_base']['datas'])} períodos (50%)")
            print(f"  - Primeira data: {resultado['historico_base']['datas'][0]}")
            print(f"  - Última data: {resultado['historico_base']['datas'][-1]}")
        else:
            print("✗ historico_base NÃO encontrado")

        print()

        # Verificar estrutura teste
        if 'historico_teste' in resultado:
            print(f"✓ historico_teste encontrado:")
            print(f"  - {len(resultado['historico_teste']['datas'])} períodos (25%)")
            print(f"  - Primeira data: {resultado['historico_teste']['datas'][0]}")
            print(f"  - Última data: {resultado['historico_teste']['datas'][-1]}")
        else:
            print("✗ historico_teste NÃO encontrado")

        print()

        # Verificar melhor modelo
        melhor_modelo = resultado.get('melhor_modelo')
        print(f"Melhor modelo: {melhor_modelo}")
        print()

        # Verificar estrutura do modelo
        if melhor_modelo and melhor_modelo in resultado.get('modelos', {}):
            modelo_data = resultado['modelos'][melhor_modelo]

            if 'teste' in modelo_data:
                print(f"✓ Previsões do período de teste:")
                print(f"  - {len(modelo_data['teste']['valores'])} previsões")
                print(f"  - Valores: {modelo_data['teste']['valores'][:3]}... (primeiros 3)")
            else:
                print("✗ Previsões de teste NÃO encontradas")

            print()

            if 'futuro' in modelo_data:
                print(f"✓ Previsões futuras:")
                print(f"  - {len(modelo_data['futuro']['valores'])} previsões")
                print(f"  - Valores: {modelo_data['futuro']['valores'][:3]}... (primeiros 3)")
            else:
                print("✗ Previsões futuras NÃO encontradas")

        print()

        # Verificar métricas
        if melhor_modelo and melhor_modelo in resultado.get('metricas', {}):
            metricas = resultado['metricas'][melhor_modelo]
            print(f"✓ Métricas do período de teste:")
            print(f"  - WMAPE: {metricas.get('wmape', 0):.2f}%")
            print(f"  - BIAS: {metricas.get('bias', 0):.2f}%")
            print(f"  - MAE: {metricas.get('mae', 0):.2f}")

        print()

        # Verificar métricas futuras
        if 'metricas_futuro' in resultado and melhor_modelo in resultado['metricas_futuro']:
            metricas_futuro = resultado['metricas_futuro'][melhor_modelo]
            print(f"✓ Métricas da previsão futura (comparação YoY):")
            print(f"  - WMAPE: {metricas_futuro.get('wmape', 0):.2f}%")
            print(f"  - BIAS: {metricas_futuro.get('bias', 0):.2f}%")
            print(f"  - MAE: {metricas_futuro.get('mae', 0):.2f}")
        else:
            print("✗ Métricas futuras NÃO encontradas")

        print()
        print("=" * 70)
        print("   VERIFICAÇÃO DA ESTRUTURA CONCLUÍDA")
        print("=" * 70)

    else:
        print(f"❌ ERRO: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Exceção: {e}")
    import traceback
    traceback.print_exc()
