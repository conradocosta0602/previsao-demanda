# -*- coding: utf-8 -*-
"""
Script para debug dos 6 modelos
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'c:/Users/valter.lino/Desktop/Treinamentos/VS/previsao-demanda')

from core.forecasting_models import get_modelo

# Dados de teste
serie = [100, 105, 102, 110, 108, 115, 112, 120, 118, 125, 122, 130, 128, 135]

print("Testando os 6 modelos com série de teste...")
print(f"Série de entrada: {len(serie)} valores\n")

modelos_testar = [
    'Média Móvel Simples',
    'Média Móvel Ponderada',
    'Suavização Exponencial Simples',
    'Holt',
    'Holt-Winters',
    'Regressão Linear'
]

for nome_modelo in modelos_testar:
    try:
        print(f"Testando: {nome_modelo}")
        modelo = get_modelo(nome_modelo)
        modelo.fit(serie)
        previsoes = modelo.predict(3)
        print(f"  ✓ Sucesso! 3 previsões: {[round(p, 2) for p in previsoes]}\n")
    except Exception as e:
        print(f"  ✗ Erro: {e}\n")
