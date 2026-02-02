"""
Verificar o cálculo do card de variação YoY que aparece no topo da tela
"""
import pandas as pd
import numpy as np
from core.method_selector import MethodSelector
from core.forecasting_models import get_modelo

# Carregar dados agregados
df = pd.read_excel('dados_teste_integrado.xlsx')
df['Mes'] = pd.to_datetime(df['Mes'])
df_agg = df.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_agg = df_agg.sort_values('Mes')
df_agg['Ano'] = df_agg['Mes'].dt.year
df_agg['Mes_Numero'] = df_agg['Mes'].dt.month

vendas_hist = df_agg['Vendas'].tolist()
ultima_data = df_agg['Mes'].max()
meses_previsao = 12

print('='*80)
print('VERIFICACAO DO CARD DE VARIACAO YoY')
print('='*80)

# Gerar previsões (como o backend faz)
selector = MethodSelector(vendas_hist)
recomendacao = selector.recomendar_metodo()

modelo = get_modelo(recomendacao['metodo'])
modelo.fit(vendas_hist)
previsoes = modelo.predict(meses_previsao)

print(f'\nMetodo usado: {recomendacao["metodo"]}')
print(f'Total previsoes: {len(previsoes)} meses\n')

# Calcular comparação YoY (como app.py faz na linha 542-543)
comparacao_yoy = []

for h in range(meses_previsao):
    data_previsao = ultima_data + pd.DateOffset(months=h + 1)
    mes_num = data_previsao.month
    ano_anterior = data_previsao.year - 1

    # Buscar demanda do mesmo mês no ano anterior
    demanda_anterior_df = df_agg[
        (df_agg['Ano'] == ano_anterior) &
        (df_agg['Mes_Numero'] == mes_num)
    ]

    if not demanda_anterior_df.empty:
        demanda_anterior = float(demanda_anterior_df['Vendas'].iloc[0])
        variacao_pct = ((previsoes[h] - demanda_anterior) / demanda_anterior) * 100

        comparacao_yoy.append({
            'mes_nome': data_previsao.strftime('%b/%y'),
            'previsao': previsoes[h],
            'demanda_anterior': demanda_anterior,
            'variacao_pct': variacao_pct
        })

# Calcular média das variações (como app.py linha 543)
variacoes_validas = [item['variacao_pct'] for item in comparacao_yoy if item['variacao_pct'] is not None]
taxa_variabilidade_media_yoy = round(sum(variacoes_validas) / len(variacoes_validas), 1) if variacoes_validas else 0

print('VARIACOES YoY POR MES:')
print('='*80)
print(f'{"Mes":<10} {"Ano Ant.":<12} {"Previsao":<12} {"Var%":<10}')
print('-'*80)

for item in comparacao_yoy:
    print(f'{item["mes_nome"]:<10} {item["demanda_anterior"]:<12.1f} {item["previsao"]:<12.1f} {item["variacao_pct"]:+9.1f}%')

print(f'\n{"="*80}')
print('CALCULO DO CARD (media das variacoes):')
print('='*80)
print(f'Total de meses comparados: {len(variacoes_validas)}')
print(f'Soma das variacoes: {sum(variacoes_validas):+.1f}%')
print(f'MEDIA (valor do card): {taxa_variabilidade_media_yoy:+.1f}%')

print(f'\n{"="*80}')
print('ANALISE:')
print('='*80)

if abs(taxa_variabilidade_media_yoy) > 20:
    print(f'[ALERTA] Media de {taxa_variabilidade_media_yoy:+.1f}% parece alta!')
    print('\nPossivel causa:')
    print('  - O calculo esta correto, mas usa MEDIA de todos os meses')
    print('  - Se alguns meses tem variacao maior, a media sobe')
    print('\nMeses com maior impacto:')
    ordenados = sorted(comparacao_yoy, key=lambda x: abs(x['variacao_pct']), reverse=True)
    for item in ordenados[:5]:
        print(f'  {item["mes_nome"]}: {item["variacao_pct"]:+.1f}%')
elif abs(taxa_variabilidade_media_yoy) > 10:
    print(f'[INFO] Media de {taxa_variabilidade_media_yoy:+.1f}% esta em nivel moderado')
else:
    print(f'[OK] Media de {taxa_variabilidade_media_yoy:+.1f}% esta em nivel baixo')

print(f'\n{"="*80}')
