"""
Análise completa YoY para todos os meses da previsão
Verifica se há crescimentos anormais similares ao problema de Outubro
"""
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from core.demand_calculator import DemandCalculator

# Carregar dados agregados
df = pd.read_excel('dados_teste_integrado.xlsx')
df['Mes'] = pd.to_datetime(df['Mes'])
df_agg = df.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_agg = df_agg.sort_values('Mes')
df_agg['Ano'] = df_agg['Mes'].dt.year
df_agg['Mes_Numero'] = df_agg['Mes'].dt.month

# Gerar previsões
vendas_hist = df_agg['Vendas'].tolist()
ultima_data = df_agg['Mes'].max()
meses_previsao = 12  # Analisar 12 meses

print('='*80)
print('ANÁLISE COMPLETA YoY - TODOS OS MESES')
print('='*80)
print(f'Última data histórica: {ultima_data.strftime("%Y-%m")}')
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
        'mes_num': mes_prev.month,
        'ano': mes_prev.year,
        'previsao': demanda,
        'metodo': metadata['metodo_usado']
    })

    vendas_temp.append(demanda)

# Criar comparação YoY
print('='*80)
print('COMPARAÇÃO YoY - TODOS OS MESES')
print('='*80)
print(f'{"Mês":<10} {"Ano Ant.":<12} {"Previsão":<12} {"Var%":<10} {"Status":<15} {"Método"}')
print('-'*80)

problemas = []
avisos = []
ok = []

for prev in previsoes:
    mes_num = prev['mes_num']
    ano_anterior = prev['ano'] - 1

    # Buscar demanda do mesmo mês no ano anterior
    demanda_anterior_df = df_agg[
        (df_agg['Ano'] == ano_anterior) &
        (df_agg['Mes_Numero'] == mes_num)
    ]

    if not demanda_anterior_df.empty:
        demanda_anterior = float(demanda_anterior_df['Vendas'].iloc[0])
        variacao_pct = ((prev['previsao'] - demanda_anterior) / demanda_anterior) * 100

        # Classificar o status
        if abs(variacao_pct) > 50:
            status = '🔴 PROBLEMA!'
            problemas.append((prev['mes_nome'], variacao_pct))
        elif abs(variacao_pct) > 30:
            status = '🟡 ALERTA'
            avisos.append((prev['mes_nome'], variacao_pct))
        elif abs(variacao_pct) > 20:
            status = '🔵 ATENÇÃO'
        else:
            status = '🟢 OK'
            ok.append((prev['mes_nome'], variacao_pct))

        print(f'{prev["mes_nome"]:<10} {demanda_anterior:<12.0f} {prev["previsao"]:<12.0f} '
              f'{variacao_pct:+9.1f}% {status:<15} {prev["metodo"]}')
    else:
        print(f'{prev["mes_nome"]:<10} {"N/A":<12} {prev["previsao"]:<12.0f} {"N/A":<10} '
              f'{"SEM COMP.":<15} {prev["metodo"]}')

# Resumo
print(f'\n{"="*80}')
print('RESUMO DA ANÁLISE')
print('='*80)

total_comparacoes = len(problemas) + len(avisos) + len(ok)

print(f'\nTotal de comparações: {total_comparacoes}')
print(f'  🟢 OK (<20%):        {len(ok)} meses')
print(f'  🔵 Atenção (20-30%): {total_comparacoes - len(ok) - len(avisos) - len(problemas)} meses')
print(f'  🟡 Alerta (30-50%):  {len(avisos)} meses')
print(f'  🔴 Problema (>50%):  {len(problemas)} meses')

if problemas:
    print(f'\n🔴 MESES COM PROBLEMA (variação > 50%):')
    for mes, var in problemas:
        print(f'  - {mes}: {var:+.1f}%')
    print('\n⚠️ AÇÃO NECESSÁRIA: Estes meses precisam de correção!')

if avisos:
    print(f'\n🟡 MESES COM ALERTA (variação 30-50%):')
    for mes, var in avisos:
        print(f'  - {mes}: {var:+.1f}%')
    print('\n💡 RECOMENDAÇÃO: Revisar estes meses')

if not problemas and not avisos:
    print('\n✅ EXCELENTE! Todas as previsões estão com variações razoáveis (<30%)')

# Análise por método
print(f'\n{"="*80}')
print('ANÁLISE POR MÉTODO UTILIZADO')
print('='*80)

metodos_usados = {}
for prev in previsoes:
    metodo = prev['metodo']
    if metodo not in metodos_usados:
        metodos_usados[metodo] = []
    metodos_usados[metodo].append(prev['mes_nome'])

for metodo, meses in metodos_usados.items():
    print(f'\n{metodo.upper()}: {len(meses)} meses')
    print(f'  Meses: {", ".join(meses)}')

if 'wma' in metodos_usados or 'ema' in metodos_usados or 'sma' in metodos_usados:
    print('\n⚠️ ATENÇÃO: Métodos não-sazonais detectados!')
    print('   Pode indicar que sazonalidade foi perdida após adicionar previsões')

# Estatísticas das variações
print(f'\n{"="*80}')
print('ESTATÍSTICAS DAS VARIAÇÕES')
print('='*80)

variacoes_validas = []
for prev in previsoes:
    mes_num = prev['mes_num']
    ano_anterior = prev['ano'] - 1

    demanda_anterior_df = df_agg[
        (df_agg['Ano'] == ano_anterior) &
        (df_agg['Mes_Numero'] == mes_num)
    ]

    if not demanda_anterior_df.empty:
        demanda_anterior = float(demanda_anterior_df['Vendas'].iloc[0])
        variacao_pct = ((prev['previsao'] - demanda_anterior) / demanda_anterior) * 100
        variacoes_validas.append(variacao_pct)

if variacoes_validas:
    print(f'Variação média:   {np.mean(variacoes_validas):+.1f}%')
    print(f'Variação mediana: {np.median(variacoes_validas):+.1f}%')
    print(f'Desvio padrão:    {np.std(variacoes_validas):.1f}%')
    print(f'Mínima:           {np.min(variacoes_validas):+.1f}%')
    print(f'Máxima:           {np.max(variacoes_validas):+.1f}%')

print(f'\n{"="*80}')
