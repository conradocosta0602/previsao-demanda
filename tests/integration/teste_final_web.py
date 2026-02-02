"""
Teste final - Simulação do comportamento na interface web
"""
import pandas as pd
from core.demand_calculator import DemandCalculator

# 1. Carregar dados PROD_001
df = pd.read_excel('dados_teste_integrado.xlsx')
df_sku = df[df['SKU'] == 'PROD_001'].copy()
df_sku = df_sku.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_sku = df_sku.sort_values('Mes')

vendas = df_sku['Vendas'].tolist()
datas = df_sku['Mes'].tolist()

print('='*70)
print('SIMULACAO WEB - PREVISAO DE DEMANDA')
print('='*70)
print(f'SKU: PROD_001')
print(f'Periodo historico: {datas[0]} a {datas[-1]}')
print(f'Total de meses: {len(vendas)}')

# 2. Classificar padrão de demanda
classificacao = DemandCalculator.classificar_padrao_demanda(vendas)
print(f'\nPadrao detectado: {classificacao["padrao"]}')
print(f'Metodo recomendado: {classificacao["metodo_recomendado"]}')
print(f'Tem sazonalidade? {classificacao.get("tem_sazonalidade", False)}')
if classificacao.get('tem_sazonalidade'):
    print(f'Periodo sazonal: {classificacao.get("periodo_sazonal")}')
    print(f'Forca sazonal: {classificacao.get("forca_sazonalidade", 0):.3f}')

# 3. Gerar previsões
print(f'\n{"="*70}')
print('PREVISOES (proximos 12 meses)')
print('='*70)

nomes_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

vendas_temp = vendas.copy()
previsoes = []
for i in range(12):
    demanda, desvio, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_temp)
    mes_num = (len(vendas_temp) % 12) + 1
    mes_nome = nomes_meses[mes_num - 1]
    previsoes.append((mes_nome, demanda, metadata['metodo_usado']))
    vendas_temp.append(demanda)

# Mostrar resultados formatados
for i, (mes, prev, metodo) in enumerate(previsoes):
    if i % 6 == 0:
        print()
    status = 'BAIXO' if prev < 700 else 'ALTO' if prev > 900 else 'MEDIO'
    print(f'{mes}: {prev:6.1f} ({status})', end='  ')

print(f'\n\n{"="*70}')
print('ANALISE DA CURVA')
print('='*70)

previsoes_valores = [p[1] for p in previsoes]
media_prev = sum(previsoes_valores) / len(previsoes_valores)
max_prev = max(previsoes_valores)
min_prev = min(previsoes_valores)
variacao = ((max_prev - min_prev) / media_prev) * 100

print(f'Media das previsoes: {media_prev:.1f}')
print(f'Maximo: {max_prev:.1f} (mes {previsoes[previsoes_valores.index(max_prev)][0]})')
print(f'Minimo: {min_prev:.1f} (mes {previsoes[previsoes_valores.index(min_prev)][0]})')
print(f'Variacao: {variacao:.1f}%')

if variacao > 30:
    print('\n[OK] CURVA COM SAZONALIDADE DETECTADA')
    print('   A previsao captura o padrao mensal com variacao significativa')
else:
    print('\n[ALERTA] CURVA AINDA MUITO LINEAR')
    print('   Variacao < 30% indica suavizacao excessiva')

# Comparar com histórico
print(f'\n{"="*70}')
print('COMPARACAO COM HISTORICO')
print('='*70)

vendas_por_mes = {}
for i, venda in enumerate(vendas):
    mes_do_ano = (i % 12) + 1
    if mes_do_ano not in vendas_por_mes:
        vendas_por_mes[mes_do_ano] = []
    vendas_por_mes[mes_do_ano].append(venda)

import numpy as np

print('\n         Historico    Previsao    Diferenca')
print('-'*50)

# Próximo mês começa após os 18 meses de histórico
# 18 % 12 = 6, então próximo = 7 (Julho)
proximo_mes_inicial = (len(vendas) % 12) + 1

for i, (mes, prev, _) in enumerate(previsoes):
    mes_num = ((proximo_mes_inicial - 1 + i) % 12) + 1  # Calcular mês correto
    if mes_num in vendas_por_mes:
        hist_media = np.mean(vendas_por_mes[mes_num])
        diff = prev - hist_media
        diff_pct = (diff / hist_media * 100) if hist_media > 0 else 0
        print(f'{mes}:     {hist_media:6.1f}      {prev:6.1f}     {diff:+6.1f} ({diff_pct:+.1f}%)')
    else:
        print(f'{mes}:       N/A         {prev:6.1f}       N/A')
