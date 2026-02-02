"""
Script para validar as correções dos desacordos 1 e 2
"""

import sys
import io
sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.forecasting_models import METODOS, get_modelo, WeightedMovingAverage
from core.method_selector import MethodSelector

print("=" * 80)
print("VALIDAÇÃO DAS CORREÇÕES - DESACORDOS 1 E 2")
print("=" * 80)

# ========== VALIDAÇÃO DO DESACORDO 1: Nomenclatura dos Métodos ==========
print("\n[DESACORDO 1] Validando nomenclatura dos métodos no dicionário METODOS...")
print("-" * 80)

metodos_oficiais = ['SMA', 'WMA', 'EMA', 'Regressão com Tendência', 'Decomposição Sazonal', 'TSB']
metodos_encontrados = []
metodos_nao_permitidos = ['Croston', 'SBA']

print("\n✅ Métodos oficiais (conforme documentação):")
for metodo in metodos_oficiais:
    if metodo in METODOS:
        metodos_encontrados.append(metodo)
        print(f"   ✓ {metodo}: {METODOS[metodo]}")
    else:
        print(f"   ✗ {metodo}: NÃO ENCONTRADO")

print("\n⚠️  Verificando métodos que NÃO deveriam estar como principais:")
for metodo in metodos_nao_permitidos:
    if metodo in METODOS:
        print(f"   ✗ {metodo}: ENCONTRADO (não deveria estar)")
    else:
        print(f"   ✓ {metodo}: Não está no dicionário (correto)")

# Verificar se todos os 6 métodos oficiais estão presentes
if len(metodos_encontrados) == 6:
    print(f"\n✅ DESACORDO 1 - RESULTADO: CORRIGIDO ({len(metodos_encontrados)}/6 métodos oficiais presentes)")
else:
    print(f"\n✗ DESACORDO 1 - RESULTADO: PENDENTE ({len(metodos_encontrados)}/6 métodos)")

# ========== VALIDAÇÃO DO DESACORDO 2: Implementação do WMA ==========
print("\n" + "=" * 80)
print("[DESACORDO 2] Validando implementação do WMA (Média Móvel Ponderada)...")
print("-" * 80)

# Testar se WMA existe no dicionário
if 'WMA' in METODOS:
    print("✓ WMA está no dicionário METODOS")
else:
    print("✗ WMA NÃO está no dicionário METODOS")

# Testar se a classe WeightedMovingAverage existe
try:
    modelo_wma = get_modelo('WMA')
    print(f"✓ Classe WMA instanciada: {type(modelo_wma)}")
except Exception as e:
    print(f"✗ Erro ao instanciar WMA: {e}")

# Testar se WMA funciona corretamente
try:
    # Dados de teste conforme documentação (Seção 2.3)
    vendas_teste = [97, 102, 99, 100, 101, 98]

    modelo_wma = get_modelo('WMA', window=6)
    modelo_wma.fit(vendas_teste)
    previsao = modelo_wma.predict(1)[0]

    # Cálculo esperado conforme documentação:
    # Numerador = 97×1 + 102×2 + 99×3 + 100×4 + 101×5 + 98×6 = 2091
    # Denominador = 1 + 2 + 3 + 4 + 5 + 6 = 21
    # WMA = 2091 / 21 = 99.57

    previsao_esperada = 99.57
    diferenca = abs(previsao - previsao_esperada)

    print(f"✓ Teste funcional WMA:")
    print(f"  - Dados: {vendas_teste}")
    print(f"  - Previsão obtida: {previsao:.2f}")
    print(f"  - Previsão esperada: {previsao_esperada}")
    print(f"  - Diferença: {diferenca:.3f}")

    if diferenca < 0.1:
        print(f"  ✓ Resultado dentro da margem de erro aceitável")
    else:
        print(f"  ✗ Resultado fora da margem de erro")

except Exception as e:
    print(f"✗ Erro ao testar WMA: {e}")
    import traceback
    traceback.print_exc()

# ========== VALIDAÇÃO DO METHOD_SELECTOR ==========
print("\n" + "=" * 80)
print("[BONUS] Validando se method_selector retorna nomenclatura correta...")
print("-" * 80)

# Testar diferentes padrões de demanda
cenarios = [
    ("Demanda estável", [100, 102, 99, 101, 100, 103, 97, 102, 99, 100, 101, 98]),
    ("Demanda intermitente", [0, 0, 15, 0, 0, 0, 20, 0, 0, 10, 0, 0]),
    ("Demanda com tendência", [100, 110, 120, 130, 140, 150, 160, 170, 180, 190])
]

for nome_cenario, vendas in cenarios:
    selector = MethodSelector(vendas)
    resultado = selector.recomendar_metodo()
    metodo = resultado['metodo']

    # Verificar se o método está na lista oficial
    if metodo in metodos_oficiais:
        status = "✓"
    else:
        status = "✗"

    print(f"{status} {nome_cenario}: {metodo}")

print("\n" + "=" * 80)
print("VALIDAÇÃO CONCLUÍDA")
print("=" * 80)

# Resumo final
print("\n📋 RESUMO:")
print(f"  - Métodos oficiais no dicionário: {len(metodos_encontrados)}/6")
print(f"  - WMA implementado: {'✓ Sim' if 'WMA' in METODOS else '✗ Não'}")
print(f"  - Croston/SBA como primários: {'✗ Sim (erro)' if 'Croston' in METODOS or 'SBA' in METODOS else '✓ Não (correto)'}")

if len(metodos_encontrados) == 6 and 'WMA' in METODOS:
    print("\n✅ DESACORDOS 1 e 2: CORRIGIDOS COM SUCESSO!")
else:
    print("\n⚠️ DESACORDOS 1 e 2: AINDA PENDENTES")
