"""
Debug do detector de sazonalidade
"""
import numpy as np
from core.seasonality_detector import SeasonalityDetector

# Dados semestrais
vendas = []
for ano in [0, 1]:
    for mes in range(1, 13):
        if mes <= 6:
            base = 120 + (ano * 5)
        else:
            base = 80 + (ano * 6)
        ruido = np.random.normal(0, 5)
        vendas.append(max(0, base + ruido))

print("Dados:", len(vendas), "períodos")
print("Jan-Jun 2023:", np.mean(vendas[0:6]))
print("Jul-Dez 2023:", np.mean(vendas[6:12]))
print("Jan-Jun 2024:", np.mean(vendas[12:18]))
print("Jul-Dez 2024:", np.mean(vendas[18:24]))

# Detectar
detector = SeasonalityDetector(vendas)

# Testar cada período manualmente
print("\n" + "="*60)
print("AVALIAÇÃO DE CADA PERÍODO")
print("="*60)

for periodo in [2, 4, 6, 7, 12, 14]:
    if len(vendas) >= periodo * 2:
        try:
            score_info = detector._evaluate_period(periodo)
            print(f"\nPeríodo {periodo}:")
            print(f"  Força: {score_info['strength']:.4f}")
            print(f"  P-value: {score_info['pvalue']:.6f}")
            print(f"  Significativo? {score_info['pvalue'] < 0.05}")
        except Exception as e:
            print(f"\nPeríodo {periodo}: ERRO - {e}")

# Resultado final
print("\n" + "="*60)
print("DETECÇÃO AUTOMÁTICA")
print("="*60)
resultado = detector.detect()
print(f"Detectado: Período {resultado['seasonal_period']}")
print(f"Força: {resultado['strength']:.4f}")
print(f"Razão: {resultado['reason']}")
