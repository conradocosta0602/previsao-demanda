"""
Buscar onde está o crescimento de 60% mencionado pelo usuário
"""
import pandas as pd
import numpy as np
from core.demand_calculator import DemandCalculator

df = pd.read_excel('dados_teste_integrado.xlsx')
df_sku = df[df['SKU'] == 'PROD_001'].copy()
df_sku = df_sku.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_sku = df_sku.sort_values('Mes')

vendas = df_sku['Vendas'].tolist()
datas = df_sku['Mes'].tolist()

print('='*80)
print('BUSCANDO CRESCIMENTO DE ~60%')
print('='*80)

# 1. Comparar histórico de Out/2023 com outras previsões
print('\n1. OUTUBRO 2023 vs OUTRAS PREVISÕES 2024:')
print('-'*80)

outubro_2023 = vendas[9]  # posição 10
print(f'Outubro 2023 (real): {outubro_2023:.1f}')

vendas_temp = vendas.copy()
meses = ['Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
previsoes_2024 = []

for mes in meses:
    demanda, _, _ = DemandCalculator.calcular_demanda_inteligente(vendas_temp)
    previsoes_2024.append((mes, demanda))
    vendas_temp.append(demanda)

for mes, prev in previsoes_2024:
    crescimento = ((prev / outubro_2023 - 1) * 100)
    alerta = ' ← POSSÍVEL CRESCIMENTO 60%!' if abs(crescimento - 60) < 5 else ''
    print(f'  {mes}/2024-2025: {prev:6.1f}  (vs Out/2023: {crescimento:+6.1f}%){alerta}')

# 2. Comparar Out/2023 com histórico
print(f'\n2. OUTUBRO 2023 vs HISTÓRICO:')
print('-'*80)

for i, (data, venda) in enumerate(zip(datas, vendas)):
    crescimento = ((venda / outubro_2023 - 1) * 100)
    alerta = ' ← CRESCIMENTO ~60%!' if abs(crescimento - 60) < 5 else ''
    print(f'  {data}: {venda:6.1f}  (vs Out/2023: {crescimento:+6.1f}%){alerta}')

# 3. Variações mês-a-mês no histórico
print(f'\n3. VARIAÇÕES MÊS-A-MÊS NO HISTÓRICO:')
print('-'*80)

for i in range(1, len(vendas)):
    crescimento = ((vendas[i] / vendas[i-1] - 1) * 100)
    alerta = ' ← CRESCIMENTO ~60%!' if abs(crescimento - 60) < 5 else ''
    print(f'  {datas[i-1]} → {datas[i]}: {crescimento:+6.1f}%{alerta}')

# 4. Comparar Out/2024 previsto com outros meses
print(f'\n4. OUTUBRO 2024 (previsto: 621.2) vs HISTÓRICO:')
print('-'*80)

outubro_2024_prev = 621.2

for i, (data, venda) in enumerate(zip(datas, vendas)):
    crescimento = ((outubro_2024_prev / venda - 1) * 100)
    alerta = ' ← CRESCIMENTO ~60%!' if abs(crescimento - 60) < 5 else ''
    print(f'  Out/2024 vs {data}: {crescimento:+6.1f}%{alerta}')

# 5. Médias anuais
print(f'\n5. COMPARAÇÃO DE MÉDIAS ANUAIS:')
print('-'*80)

# Separar por ano
vendas_2023 = vendas[:12]
vendas_2024_hist = vendas[12:18]

media_2023 = np.mean(vendas_2023)
media_2024_parcial = np.mean(vendas_2024_hist)

# Média das previsões 2024
previsoes_2024_valores = [p[1] for p in previsoes_2024[:6]]  # Jul-Dez 2024
media_2024_completa = np.mean(vendas_2024_hist + previsoes_2024_valores)

print(f'Média 2023 (12 meses):          {media_2023:.1f}')
print(f'Média 2024 (Jan-Jun, real):     {media_2024_parcial:.1f}')
print(f'Média 2024 (12 meses projetada): {media_2024_completa:.1f}')
print(f'Crescimento 2023→2024:          {((media_2024_completa / media_2023 - 1) * 100):+.1f}%')

# 6. Comparar Out com média anual
print(f'\n6. OUTUBRO vs MÉDIAS ANUAIS:')
print('-'*80)

print(f'Outubro 2023: {outubro_2023:.1f}')
print(f'Média 2023:   {media_2023:.1f}')
print(f'Out/2023 vs Média 2023: {((outubro_2023 / media_2023 - 1) * 100):+.1f}%')
print()
print(f'Outubro 2024 (prev): {outubro_2024_prev:.1f}')
print(f'Média 2024 (proj):   {media_2024_completa:.1f}')
print(f'Out/2024 vs Média 2024: {((outubro_2024_prev / media_2024_completa - 1) * 100):+.1f}%')

print(f'\n{"="*80}')
print('CONCLUSÃO:')
print('='*80)
print('Procurando por crescimentos próximos a 60% nas comparações acima.')
print('Se não encontrado, o usuário pode estar vendo dados de outra SKU')
print('ou comparando com dados em outra planilha/tela.')
