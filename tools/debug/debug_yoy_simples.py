"""
Debug: Verificar o cálculo YoY simples
"""
import pandas as pd
from core.method_selector import MethodSelector
from core.forecasting_models import get_modelo

# Carregar dados
df = pd.read_excel('dados_teste_integrado.xlsx')
df['Mes'] = pd.to_datetime(df['Mes'])
df_agg = df.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_agg = df_agg.sort_values('Mes')

print('='*80)
print('DEBUG: CALCULO YoY SIMPLES')
print('='*80)

# Histórico agregado
vendas_hist = df_agg['Vendas'].tolist()
meses_previsao = 12

print(f'\nHistorico completo: {len(vendas_hist)} meses')
print(f'Datas: {df_agg["Mes"].min()} ate {df_agg["Mes"].max()}')

# Gerar previsão
selector = MethodSelector(vendas_hist)
rec = selector.recomendar_metodo()
modelo = get_modelo(rec['metodo'])
modelo.fit(vendas_hist)
previsoes = modelo.predict(meses_previsao)

print(f'\nMetodo usado: {rec["metodo"]}')
print(f'Previsoes geradas: {len(previsoes)} meses')

# Calcular YoY simples
total_previsto = sum(previsoes)
print(f'\n{"="*80}')
print('CALCULO YoY:')
print('='*80)

print(f'\n1. TOTAL PREVISTO (proximos {meses_previsao} meses):')
print(f'   Soma das previsoes: {total_previsto:,.2f}')

# Últimos N meses do histórico
if len(vendas_hist) >= meses_previsao:
    vendas_periodo_anterior = vendas_hist[-meses_previsao:]
    total_periodo_anterior = sum(vendas_periodo_anterior)

    print(f'\n2. TOTAL PERIODO ANTERIOR (ultimos {meses_previsao} meses do historico):')
    print(f'   Soma dos ultimos {meses_previsao} meses: {total_periodo_anterior:,.2f}')

    # Mostrar quais meses
    ultimas_datas = df_agg.tail(meses_previsao)['Mes'].tolist()
    print(f'   Periodo: {ultimas_datas[0].strftime("%Y-%m")} ate {ultimas_datas[-1].strftime("%Y-%m")}')

    # Calcular variação
    variacao_pct = ((total_previsto - total_periodo_anterior) / total_periodo_anterior) * 100

    print(f'\n3. VARIACAO:')
    print(f'   Diferenca absoluta: {total_previsto - total_periodo_anterior:+,.2f}')
    print(f'   Variacao percentual: {variacao_pct:+.1f}%')

    print(f'\n{"="*80}')
    print('ANALISE:')
    print('='*80)

    if variacao_pct < 0:
        print(f'[INFO] Previsao indica QUEDA de {abs(variacao_pct):.1f}%')
        print(f'       Total previsto ({total_previsto:,.0f}) < Total anterior ({total_periodo_anterior:,.0f})')
    elif variacao_pct > 0:
        print(f'[INFO] Previsao indica CRESCIMENTO de {variacao_pct:.1f}%')
        print(f'       Total previsto ({total_previsto:,.0f}) > Total anterior ({total_periodo_anterior:,.0f})')
    else:
        print(f'[INFO] Previsao indica ESTABILIDADE (0%)')

    # Mostrar detalhes mês a mês
    print(f'\n{"="*80}')
    print('DETALHES MES A MES:')
    print('='*80)
    print(f'{"Mes Historico":<20} {"Realizado":<15} {"Mes Previsao":<20} {"Previsto":<15}')
    print('-'*80)

    ultima_data = df_agg['Mes'].max()
    for i in range(min(6, meses_previsao)):
        data_hist = ultimas_datas[i]
        valor_hist = vendas_periodo_anterior[i]

        data_prev = ultima_data + pd.DateOffset(months=i+1)
        valor_prev = previsoes[i]

        print(f'{data_hist.strftime("%Y-%m"):<20} {valor_hist:<15,.0f} {data_prev.strftime("%Y-%m"):<20} {valor_prev:<15,.0f}')

    if meses_previsao > 6:
        print('...')

print(f'\n{"="*80}')
