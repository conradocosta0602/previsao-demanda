"""
Debug detalhado para PROD_001
"""
import pandas as pd
import numpy as np
from core.seasonality_detector import SeasonalityDetector

# Carregar dados
df = pd.read_excel('dados_teste_integrado.xlsx')
df_sku = df[df['SKU'] == 'PROD_001'].copy()
df_sku = df_sku.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_sku = df_sku.sort_values('Mes')

vendas = df_sku['Vendas'].tolist()
print(f"Total períodos: {len(vendas)}")
print(f"Vendas: {vendas}\n")

# Criar detector
detector = SeasonalityDetector(vendas)

# Testar cada período manualmente
print("="*80)
print("AVALIAÇÃO DE CADA PERÍODO")
print("="*80)

for periodo in [2, 3, 4, 6, 7, 9, 12]:
    if len(vendas) >= periodo * 2:
        try:
            score_info = detector._evaluate_period(periodo)
            print(f"\nPeríodo {periodo}:")
            print(f"  Força: {score_info['strength']:.4f}")
            print(f"  P-value: {score_info['pvalue']:.6f}")
            sig_05 = "SIM" if score_info['pvalue'] < 0.05 else "NAO"
            sig_15 = "SIM" if score_info['pvalue'] < 0.15 else "NAO"
            print(f"  Significativo (p<0.05)? {sig_05}")
            print(f"  Significativo (p<0.15)? {sig_15}")
        except Exception as e:
            print(f"\nPeríodo {periodo}: ERRO - {e}")

# Resultado final
print("\n" + "="*80)
print("DETECÇÃO AUTOMÁTICA")
print("="*80)
resultado = detector.detect()
print(f"Detectado: Período {resultado['seasonal_period']}")
print(f"Tem sazonalidade? {resultado['has_seasonality']}")
print(f"Força: {resultado['strength']:.4f}")
print(f"P-value: {resultado.get('pvalue', 'N/A')}")
print(f"Razão: {resultado['reason']}")
