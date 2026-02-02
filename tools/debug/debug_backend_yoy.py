"""
Debug: Simular EXATAMENTE o processamento do backend como app.py faz
para verificar qual valor de taxa_variabilidade_media_yoy está sendo calculado
"""
import pandas as pd
import numpy as np
from core.method_selector import MethodSelector
from core.forecasting_models import get_modelo

print('='*80)
print('DEBUG: SIMULANDO PROCESSAMENTO DO BACKEND (app.py)')
print('='*80)

# 1. Carregar dados (como app.py faz)
df = pd.read_excel('dados_teste_integrado.xlsx')
df['Mes'] = pd.to_datetime(df['Mes'])

# 2. Preparar dados agregados para previsão total
df_agg = df.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_agg = df_agg.sort_values('Mes')
df_agg['Ano'] = df_agg['Mes'].dt.year
df_agg['Mes_Numero'] = df_agg['Mes'].dt.month

vendas_hist = df_agg['Vendas'].tolist()
ultima_data = df_agg['Mes'].max()
meses_previsao = 12

print(f'\n1. DADOS CARREGADOS:')
print(f'   Ultima data: {ultima_data.strftime("%Y-%m")}')
print(f'   Total vendas historicas: {len(vendas_hist)}')

# 3. Gerar previsões (app.py usa DemandCalculator.calcular_demanda_inteligente)
# Mas vamos simular o que DEVERIA acontecer com o código corrigido

print(f'\n2. GERANDO PREVISOES (Metodo 1 - usando MethodSelector):')

selector = MethodSelector(vendas_hist)
recomendacao = selector.recomendar_metodo()

print(f'   Metodo recomendado: {recomendacao["metodo"]}')
print(f'   Confianca: {recomendacao["confianca"]:.1%}')

# Treinar modelo
modelo = get_modelo(recomendacao['metodo'])
modelo.fit(vendas_hist)
previsoes_metodo1 = modelo.predict(meses_previsao)

print(f'   Previsoes geradas: {len(previsoes_metodo1)}')

# 4. AGORA vamos simular o que app.py FAZ (usando DemandCalculator iterativamente)
print(f'\n3. GERANDO PREVISOES (Metodo 2 - como app.py linha 167-192):')

from core.demand_calculator import DemandCalculator

vendas_temp = vendas_hist.copy()
previsoes_metodo2 = []

for i in range(meses_previsao):
    demanda, _, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_temp)
    previsoes_metodo2.append(demanda)
    vendas_temp.append(demanda)
    if i == 0:
        print(f'   Metodo usado (1a previsao): {metadata.get("metodo_usado", "N/A")}')

print(f'   Previsoes geradas: {len(previsoes_metodo2)}')

# 5. Comparar os dois métodos
print(f'\n4. COMPARACAO DOS DOIS METODOS:')
print(f'   {"Mes":<10} {"Metodo1":<12} {"Metodo2":<12} {"Diff":<10}')
print(f'   {"-"*50}')
for i in range(min(6, meses_previsao)):
    diff = previsoes_metodo2[i] - previsoes_metodo1[i]
    mes_nome = (ultima_data + pd.DateOffset(months=i+1)).strftime('%b/%y')
    print(f'   {mes_nome:<10} {previsoes_metodo1[i]:<12.1f} {previsoes_metodo2[i]:<12.1f} {diff:+10.1f}')

# 6. Calcular YoY para AMBOS os métodos
def calcular_yoy(previsoes, nome):
    print(f'\n5. CALCULANDO YoY ({nome}):')
    comparacao_yoy = []

    for h in range(meses_previsao):
        data_previsao = ultima_data + pd.DateOffset(months=h + 1)
        mes_num = data_previsao.month
        ano_anterior = data_previsao.year - 1

        demanda_anterior_df = df_agg[
            (df_agg['Ano'] == ano_anterior) &
            (df_agg['Mes_Numero'] == mes_num)
        ]

        if not demanda_anterior_df.empty:
            demanda_anterior = float(demanda_anterior_df['Vendas'].iloc[0])
            variacao_pct = ((previsoes[h] - demanda_anterior) / demanda_anterior) * 100
            comparacao_yoy.append(variacao_pct)

    # Calcular média (como app.py linha 543)
    if comparacao_yoy:
        media = round(sum(comparacao_yoy) / len(comparacao_yoy), 1)
        print(f'   Total comparacoes: {len(comparacao_yoy)}')
        print(f'   Soma variacoes: {sum(comparacao_yoy):+.1f}%')
        print(f'   MEDIA (valor card): {media:+.1f}%')
        return media
    return 0

taxa1 = calcular_yoy(previsoes_metodo1, 'Metodo MethodSelector')
taxa2 = calcular_yoy(previsoes_metodo2, 'Metodo DemandCalculator iterativo')

print(f'\n{"="*80}')
print('CONCLUSAO:')
print('='*80)
print(f'Taxa YoY com MethodSelector:           {taxa1:+.1f}%')
print(f'Taxa YoY com DemandCalculator (app.py): {taxa2:+.1f}%')

if abs(taxa2 - taxa1) > 5:
    print(f'\n[PROBLEMA] Diferenca de {abs(taxa2-taxa1):.1f}pp entre os metodos!')
    print('Isso significa que app.py esta usando DemandCalculator.calcular_demanda_inteligente')
    print('que pode nao estar usando o modelo corrigido.')
else:
    print(f'\n[OK] Diferenca minima entre os metodos')

print(f'\n{"="*80}')
