# -*- coding: utf-8 -*-
"""
Teste para determinar o threshold ideal para MAPE em dados semanais
"""

import numpy as np
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def calculate_mape_with_threshold(actual, predicted, min_value):
    """Calcula MAPE com threshold específico"""
    actual_arr = np.array(actual)
    predicted_arr = np.array(predicted)

    mask = actual_arr >= min_value

    if not mask.any():
        return None, 0

    actual_filtered = actual_arr[mask]
    predicted_filtered = predicted_arr[mask]

    ape = np.abs((actual_filtered - predicted_filtered) / actual_filtered) * 100

    return float(np.mean(ape)), len(actual_filtered)

print("=" * 80)
print("TESTE: Impacto do Threshold no MAPE para Dados Semanais")
print("=" * 80)

# Dados simulados que representam o problema real
# Mix de semanas com vendas zero, baixas (0.5-5) e normais (5-20)
actual = [
    0, 0, 0.3, 0.6, 1.2, 0.8, 1.5, 2.1, 3.0, 4.5,  # Baixas vendas
    5.2, 6.8, 7.1, 8.5, 9.2, 10.1, 12.3, 14.5, 16.2, 18.4,  # Vendas normais
    20.1, 22.5, 19.8, 17.2, 15.9, 13.4, 11.8, 9.5, 7.3, 5.8  # Vendas decrescentes
]

predicted = [
    2, 3, 4, 5, 8, 6, 9, 10, 11, 12,
    5, 7, 8, 9, 10, 11, 13, 15, 17, 19,
    21, 23, 20, 18, 16, 14, 12, 10, 8, 6
]

print(f"\nTotal de períodos: {len(actual)}")
print(f"Vendas totais (actual): {sum(actual):.1f}")
print(f"Vendas totais (predicted): {sum(predicted):.1f}")

print("\n" + "=" * 80)
print("Testando diferentes thresholds:")
print("=" * 80)

thresholds = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]

for threshold in thresholds:
    mape, n_periodos = calculate_mape_with_threshold(actual, predicted, threshold)

    if mape is None:
        print(f"\nThreshold = {threshold:5.1f}: SEM DADOS VÁLIDOS")
    else:
        pct_incluido = (n_periodos / len(actual)) * 100
        print(f"\nThreshold = {threshold:5.1f}:")
        print(f"  - MAPE: {mape:7.2f}%")
        print(f"  - Períodos incluídos: {n_periodos}/{len(actual)} ({pct_incluido:.1f}%)")

# Mostrar detalhes dos períodos excluídos para cada threshold
print("\n" + "=" * 80)
print("Análise Detalhada: Períodos Excluídos vs Incluídos")
print("=" * 80)

for threshold in [0.5, 2.0, 5.0]:
    print(f"\n--- Threshold = {threshold} ---")

    excluidos = []
    incluidos = []

    for i, (a, p) in enumerate(zip(actual, predicted)):
        ape = abs((a - p) / a) * 100 if a > 0 else 0

        if a < threshold:
            excluidos.append((i, a, p, ape))
        else:
            incluidos.append((i, a, p, ape))

    print(f"\nExcluídos ({len(excluidos)} períodos):")
    if len(excluidos) > 0 and len(excluidos) <= 10:
        for i, a, p, ape in excluidos:
            print(f"  Período {i}: actual={a:.1f}, predicted={p:.1f}, APE={ape:.1f}%")
    elif len(excluidos) > 10:
        print(f"  Mostrando primeiros 5 de {len(excluidos)}:")
        for i, a, p, ape in excluidos[:5]:
            print(f"  Período {i}: actual={a:.1f}, predicted={p:.1f}, APE={ape:.1f}%")

    if len(incluidos) > 0:
        apes_incluidos = [ape for _, _, _, ape in incluidos]
        print(f"\nIncluídos ({len(incluidos)} períodos):")
        print(f"  MAPE médio: {np.mean(apes_incluidos):.2f}%")
        print(f"  APE mínimo: {min(apes_incluidos):.2f}%")
        print(f"  APE máximo: {max(apes_incluidos):.2f}%")

print("\n" + "=" * 80)
print("RECOMENDAÇÃO")
print("=" * 80)
print("""
Para dados SEMANAIS de varejo:
- Threshold 0.5: Muito baixo, inclui ruído (MAPE alto)
- Threshold 2.0: Balanceado, exclui semanas muito fracas mas mantém dados suficientes
- Threshold 5.0: Conservador, inclui apenas semanas com vendas relevantes

RECOMENDADO: 2.0 para começar, ajustar conforme necessidade do negócio
""")

print("=" * 80)
print("[OK] Teste concluído")
print("=" * 80)
