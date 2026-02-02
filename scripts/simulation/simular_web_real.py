"""
Simula EXATAMENTE como a aplicação web real gera previsões
Gera todas as previsões de uma vez, sem processo iterativo
"""
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
from core.method_selector import MethodSelector
from core.forecasting_models import get_modelo

# Carregar dados agregados (como o backend faz)
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
print('SIMULAÇÃO WEB REAL - Gera todas previsões de uma vez')
print('='*80)
print(f'Última data: {ultima_data.strftime("%Y-%m")}')
print(f'Total períodos históricos: {len(vendas_hist)}')
print(f'Meses a prever: {meses_previsao}\n')

# ===== EXATAMENTE COMO APP.PY FAZ (linhas 167-192) =====

# 1. Obter recomendação do método
selector = MethodSelector(vendas_hist)
recomendacao = selector.recomendar_metodo()

print(f'Método recomendado: {recomendacao["metodo"]}')
print(f'Confiança: {recomendacao["confianca"]:.1%}')
print(f'Razão: {recomendacao["razao"]}\n')

# 2. Treinar modelo e gerar TODAS as previsões de uma vez
try:
    modelo = get_modelo(recomendacao['metodo'])
    modelo.fit(vendas_hist)
    previsoes = modelo.predict(meses_previsao)  # Todas de uma vez!
    print(f'[OK] Modelo treinado: {recomendacao["metodo"]}')
except Exception as e:
    print(f'[ERRO] Falha no método {recomendacao["metodo"]}: {e}')
    print('[FALLBACK] Usando Média Móvel Simples')
    modelo = get_modelo('Média Móvel Simples')
    modelo.fit(vendas_hist)
    previsoes = modelo.predict(meses_previsao)

print(f'Previsões geradas: {len(previsoes)} meses\n')

# 3. Criar lista de previsões com datas
previsoes_lista = []
for h in range(meses_previsao):
    data_previsao = ultima_data + pd.DateOffset(months=h + 1)
    previsoes_lista.append({
        'mes': data_previsao,
        'mes_nome': data_previsao.strftime('%b/%y'),
        'mes_num': data_previsao.month,
        'ano': data_previsao.year,
        'previsao': previsoes[h],
        'metodo': recomendacao['metodo']
    })

# 4. Comparação YoY (como app.py faz)
print('='*80)
print('COMPARAÇÃO YoY - Previsão vs Ano Anterior')
print('='*80)
print(f'{"Mês":<10} {"Ano Ant.":<12} {"Previsão":<12} {"Var%":<10} {"Status":<15}')
print('-'*80)

problemas = []
avisos = []
atencao = []
ok = []

for prev in previsoes_lista:
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

        # Classificar
        if abs(variacao_pct) > 50:
            status = 'PROBLEMA!'
            problemas.append((prev['mes_nome'], variacao_pct))
        elif abs(variacao_pct) > 30:
            status = 'ALERTA'
            avisos.append((prev['mes_nome'], variacao_pct))
        elif abs(variacao_pct) > 20:
            status = 'ATENCAO'
            atencao.append((prev['mes_nome'], variacao_pct))
        else:
            status = 'OK'
            ok.append((prev['mes_nome'], variacao_pct))

        print(f'{prev["mes_nome"]:<10} {demanda_anterior:<12.0f} {prev["previsao"]:<12.0f} '
              f'{variacao_pct:+9.1f}% {status:<15}')
    else:
        print(f'{prev["mes_nome"]:<10} {"N/A":<12} {prev["previsao"]:<12.0f} {"N/A":<10} '
              f'{"SEM COMP.":<15}')

# 5. Resumo
print(f'\n{"="*80}')
print('RESUMO')
print('='*80)

total = len(ok) + len(atencao) + len(avisos) + len(problemas)

print(f'\nTotal comparações: {total}')
print(f'  OK (<20%):        {len(ok)} meses')
print(f'  Atenção (20-30%): {len(atencao)} meses')
print(f'  Alerta (30-50%):  {len(avisos)} meses')
print(f'  Problema (>50%):  {len(problemas)} meses')

if problemas:
    print(f'\nMESES COM PROBLEMA (>50%):')
    for mes, var in problemas:
        print(f'  {mes}: {var:+.1f}%')
    print('\nACAO NECESSARIA!')

if avisos:
    print(f'\nMESES COM ALERTA (30-50%):')
    for mes, var in avisos:
        print(f'  {mes}: {var:+.1f}%')
    print('\nRECOMENDACO: Revisar')

if atencao:
    print(f'\nMESES COM ATENCAO (20-30%):')
    for mes, var in atencao:
        print(f'  {mes}: {var:+.1f}%')

if not problemas and not avisos:
    print('\n[OK] Todas as previsoes com variacoes razoaveis!')

# 6. Estatísticas
print(f'\n{"="*80}')
print('ESTATISTICAS DAS VARIACOES')
print('='*80)

variacoes = [var for _, var in ok + atencao + avisos + problemas]
if variacoes:
    print(f'Média:    {np.mean(variacoes):+.1f}%')
    print(f'Mediana:  {np.median(variacoes):+.1f}%')
    print(f'Desvio:   {np.std(variacoes):.1f}%')
    print(f'Mínima:   {np.min(variacoes):+.1f}%')
    print(f'Máxima:   {np.max(variacoes):+.1f}%')

# 7. Análise específica de Outubro
print(f'\n{"="*80}')
print('ANALISE ESPECIFICA: OUTUBRO 2024')
print('='*80)

outubro = [p for p in previsoes_lista if p['mes_num'] == 10]
if outubro:
    out = outubro[0]
    demanda_anterior_df = df_agg[
        (df_agg['Ano'] == out['ano'] - 1) &
        (df_agg['Mes_Numero'] == 10)
    ]

    if not demanda_anterior_df.empty:
        demanda_ant = float(demanda_anterior_df['Vendas'].iloc[0])
        var = ((out['previsao'] - demanda_ant) / demanda_ant) * 100

        print(f'Outubro/{out["ano"]-1} (real):     {demanda_ant:,.0f}')
        print(f'Outubro/{out["ano"]} (previsão): {out["previsao"]:,.0f}')
        print(f'Variação YoY:              {var:+.1f}%')
        print(f'Método usado:              {out["metodo"]}')

        if abs(var) > 50:
            print('\n[PROBLEMA] Crescimento > 50%!')
        elif abs(var) > 20:
            print('\n[ATENCAO] Variação > 20%')
        else:
            print('\n[OK] Variação dentro do esperado')

print(f'\n{"="*80}')
