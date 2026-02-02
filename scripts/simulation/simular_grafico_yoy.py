"""
Simular EXATAMENTE o gráfico YoY mostrado na interface web
"""
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from core.demand_calculator import DemandCalculator

# Carregar dados
df = pd.read_excel('dados_teste_integrado.xlsx')

# Processar como o backend faz
df['Mes'] = pd.to_datetime(df['Mes'])
df_agg = df.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_agg = df_agg.sort_values('Mes')
df_agg['Ano'] = df_agg['Mes'].dt.year
df_agg['Mes_Numero'] = df_agg['Mes'].dt.month

print('='*80)
print('SIMULAÇÃO DO GRÁFICO YoY (Comparação Ano contra Ano)')
print('='*80)

# Gerar previsões (6 meses como padrão)
vendas_hist = df_agg['Vendas'].tolist()
ultima_data = df_agg['Mes'].max()
meses_previsao = 6

print(f'\nÚltima data do histórico: {ultima_data.strftime("%Y-%m")}')
print(f'Gerando {meses_previsao} meses de previsão...\n')

# Gerar previsões
vendas_temp = vendas_hist.copy()
previsoes = []

for i in range(meses_previsao):
    mes_prev = ultima_data + relativedelta(months=i+1)
    demanda, _, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_temp)

    previsoes.append({
        'mes': mes_prev,
        'mes_nome': mes_prev.strftime('%b/%y'),
        'previsao': demanda,
        'metodo': metadata['metodo_usado']
    })

    vendas_temp.append(demanda)

# Criar comparação YoY como o backend faz
print('COMPARAÇÃO YoY (como mostrado no gráfico):')
print('='*80)
print(f'{"Mês":<12} {"Ano Anterior":<15} {"Previsão":<15} {"Variação":<12} {"Método"}')
print('-'*80)

for prev in previsoes:
    mes_prev_date = prev['mes']
    mes_num = mes_prev_date.month
    ano_anterior = mes_prev_date.year - 1

    # Buscar demanda do mesmo mês no ano anterior
    demanda_anterior_df = df_agg[
        (df_agg['Ano'] == ano_anterior) &
        (df_agg['Mes_Numero'] == mes_num)
    ]

    if not demanda_anterior_df.empty:
        demanda_anterior = float(demanda_anterior_df['Vendas'].iloc[0])

        # Calcular variação
        variacao_pct = ((prev['previsao'] - demanda_anterior) / demanda_anterior) * 100

        print(f'{prev["mes_nome"]:<12} {demanda_anterior:<15.1f} {prev["previsao"]:<15.1f} '
              f'{variacao_pct:+11.1f}% {prev["metodo"]}')
    else:
        print(f'{prev["mes_nome"]:<12} {"N/A":<15} {prev["previsao"]:<15.1f} {"N/A":<12} {prev["metodo"]}')

# Análise específica de Outubro
print(f'\n{"="*80}')
print('ANÁLISE ESPECÍFICA: OUTUBRO')
print('='*80)

outubro_previsao = [p for p in previsoes if p['mes'].month == 10]
if outubro_previsao:
    out_prev = outubro_previsao[0]
    mes_num = out_prev['mes'].month
    ano_anterior = out_prev['mes'].year - 1

    demanda_anterior_df = df_agg[
        (df_agg['Ano'] == ano_anterior) &
        (df_agg['Mes_Numero'] == mes_num)
    ]

    if not demanda_anterior_df.empty:
        demanda_anterior = float(demanda_anterior_df['Vendas'].iloc[0])
        variacao_pct = ((out_prev['previsao'] - demanda_anterior) / demanda_anterior) * 100

        print(f'Mês: {out_prev["mes_nome"]} (Outubro {out_prev["mes"].year})')
        print(f'Demanda Out/{ano_anterior} (real):     {demanda_anterior:.1f}')
        print(f'Previsão Out/{out_prev["mes"].year} (prevista): {out_prev["previsao"]:.1f}')
        print(f'Variação YoY:                 {variacao_pct:+.1f}%')
        print(f'Método usado:                 {out_prev["metodo"]}')

        print(f'\n{"="*80}')
        if abs(variacao_pct) > 50:
            print('[ALERTA] Variação > 50% detectada!')
            print('\nPossíveis causas:')
            print('  1. Método sazonal aplicando índice incorreto')
            print('  2. Tendência muito forte')
            print('  3. Dados do ano anterior com outliers')
            print('  4. Comparação incorreta entre dados agregados/não agregados')
        elif abs(variacao_pct) > 20:
            print('[INFO] Variação significativa (>20%)')
        else:
            print('[OK] Variação dentro do esperado (<20%)')
    else:
        print(f'Não há dados de Outubro/{ano_anterior} para comparação')
else:
    print('Outubro não está nos próximos 6 meses de previsão')

# Mostrar dados históricos de Outubro
print(f'\n{"="*80}')
print('HISTÓRICO DE OUTUBRO (todos os anos):')
print('='*80)

outubros = df_agg[df_agg['Mes_Numero'] == 10].copy()
for idx, row in outubros.iterrows():
    print(f"Outubro/{row['Ano']}: {row['Vendas']:.1f}")

print(f'\n{"="*80}')
