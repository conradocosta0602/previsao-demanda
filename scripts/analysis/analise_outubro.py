"""
Análise específica: Outubro 2023 vs Outubro 2024
"""
import pandas as pd
import numpy as np
from core.demand_calculator import DemandCalculator

# Carregar dados PROD_001
df = pd.read_excel('dados_teste_integrado.xlsx')
df_sku = df[df['SKU'] == 'PROD_001'].copy()
df_sku = df_sku.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_sku = df_sku.sort_values('Mes')

vendas = df_sku['Vendas'].tolist()
datas = df_sku['Mes'].tolist()

print('='*80)
print('ANÁLISE: OUTUBRO 2023 vs OUTUBRO 2024')
print('='*80)

print('\nHistórico completo:')
for i, (data, venda) in enumerate(zip(datas, vendas)):
    mes_ano = (i % 12) + 1
    marcador = ' <-- OUTUBRO' if mes_ano == 10 else ''
    print(f'{i+1:2d}. {data}: {venda:6.1f}{marcador}')

# Identificar Outubros
outubro_2023_idx = 9  # Posição 10 (índice 9)
outubro_2023_valor = vendas[outubro_2023_idx]

print(f'\n{"="*80}')
print('DADOS HISTÓRICOS')
print('='*80)
print(f'Outubro 2023 (posição {outubro_2023_idx+1}): {outubro_2023_valor:.1f}')

# Calcular qual seria a previsão para Outubro 2024
# Outubro 2024 seria a posição 22 (18 + 4 meses após o último dado)
print(f'\nÚltimo dado histórico: {datas[-1]} (posição 18)')
print(f'Outubro 2024 seria a posição 22 (18 + 4 meses)')

# Simular previsões até Outubro 2024
vendas_simuladas = vendas.copy()
previsoes = []

print(f'\n{"="*80}')
print('GERANDO PREVISÕES ATÉ OUTUBRO 2024')
print('='*80)

nomes_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

for i in range(4):  # Jul, Ago, Set, Out
    demanda, desvio, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_simuladas)
    mes_num = (len(vendas_simuladas) % 12) + 1
    mes_nome = nomes_meses[mes_num - 1]

    print(f'\nPrevisão {i+1}: {mes_nome}/2024')
    print(f'  Valor previsto: {demanda:.1f}')
    print(f'  Método usado: {metadata["metodo_usado"]}')
    if 'periodo_sazonal' in metadata:
        print(f'  Período sazonal: {metadata["periodo_sazonal"]}')

    previsoes.append((mes_nome, demanda))
    vendas_simuladas.append(demanda)

outubro_2024_prev = previsoes[3][1]  # Quarta previsão (Outubro)

print(f'\n{"="*80}')
print('COMPARAÇÃO OUTUBRO 2023 vs OUTUBRO 2024')
print('='*80)
print(f'Outubro 2023 (real):      {outubro_2023_valor:6.1f}')
print(f'Outubro 2024 (previsão):  {outubro_2024_prev:6.1f}')
print(f'Diferença:                {outubro_2024_prev - outubro_2023_valor:+6.1f}')
print(f'Crescimento:              {((outubro_2024_prev / outubro_2023_valor - 1) * 100):+.1f}%')

# Analisar o cálculo sazonal detalhado
print(f'\n{"="*80}')
print('DIAGNÓSTICO: POR QUE ESSE CRESCIMENTO?')
print('='*80)

# Agrupar vendas por mês do ano
vendas_por_mes = {}
for i, venda in enumerate(vendas):
    mes_do_ano = (i % 12) + 1
    if mes_do_ano not in vendas_por_mes:
        vendas_por_mes[mes_do_ano] = []
    vendas_por_mes[mes_do_ano].append(venda)

# Média de Outubro no histórico
media_out = np.mean(vendas_por_mes[10])
print(f'\nMédia histórica de Outubro: {media_out:.1f}')
print(f'Valores de Outubro no histórico: {vendas_por_mes[10]}')

# Calcular índice sazonal de Outubro
medias_mensais = {}
for mes in range(1, 13):
    if mes in vendas_por_mes and len(vendas_por_mes[mes]) > 0:
        medias_mensais[mes] = np.mean(vendas_por_mes[mes])
    else:
        medias_mensais[mes] = np.mean(vendas)

media_geral = np.mean(list(medias_mensais.values()))
indice_out = medias_mensais[10] / media_geral

print(f'\nMédia geral de todos os meses: {media_geral:.1f}')
print(f'Índice sazonal de Outubro: {indice_out:.3f} ({"BAIXO" if indice_out < 0.9 else "NORMAL" if indice_out < 1.1 else "ALTO"})')

# Analisar a tendência
print(f'\n{"="*80}')
print('ANÁLISE DA TENDÊNCIA')
print('='*80)

# Tendência geral do histórico
from sklearn.linear_model import LinearRegression
X = np.arange(len(vendas)).reshape(-1, 1)
y = np.array(vendas)
modelo = LinearRegression()
modelo.fit(X, y)
tendencia_coef = modelo.coef_[0]

print(f'Coeficiente de tendência (crescimento por mês): {tendencia_coef:+.2f}')
print(f'Tendência anual (~12 meses): {tendencia_coef * 12:+.1f}')

# Previsão simples com tendência
outubro_2024_posicao = 21  # índice 21 = posição 22
previsao_tendencia = modelo.predict([[outubro_2024_posicao]])[0]
print(f'\nPrevisão por regressão linear: {previsao_tendencia:.1f}')

# Comparar com o método sazonal
print(f'\n{"="*80}')
print('RESUMO DO PROBLEMA')
print('='*80)

print(f'\n1. Média histórica de Outubro: {media_out:.1f}')
print(f'2. Índice sazonal de Outubro: {indice_out:.3f} (mês com demanda {"baixa" if indice_out < 0.9 else "normal"})')
print(f'3. Tendência de crescimento: {tendencia_coef:+.2f} por mês')
print(f'4. Previsão do sistema para Out/2024: {outubro_2024_prev:.1f}')
print(f'5. Crescimento vs Out/2023: {((outubro_2024_prev / outubro_2023_valor - 1) * 100):+.1f}%')

if abs((outubro_2024_prev / outubro_2023_valor - 1) * 100) > 20:
    print(f'\n⚠️ ALERTA: Crescimento > 20% pode indicar problema!')
    print('\nPossíveis causas:')
    print('  a) Tendência muito forte nos dados recentes')
    print('  b) Método sazonal amplificando tendência')
    print('  c) Poucos dados de Outubro (apenas 1 amostra)')
    print('  d) Dados recentes (Jan-Jun 2024) muito altos influenciando tendência')
