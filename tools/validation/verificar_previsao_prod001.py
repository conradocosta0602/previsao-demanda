"""
Verificar se a previsão está correta para PROD_001
"""
import pandas as pd
import numpy as np
from core.demand_calculator import DemandCalculator

# Carregar dados
df = pd.read_excel('dados_teste_integrado.xlsx')
df_sku = df[df['SKU'] == 'PROD_001'].copy()
df_sku = df_sku.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_sku = df_sku.sort_values('Mes')

vendas = df_sku['Vendas'].tolist()
datas = df_sku['Mes'].tolist()

print("Histórico completo:")
for i, (data, venda) in enumerate(zip(datas, vendas)):
    print(f"{i+1:2d}. {data}: {venda:4.0f}")

print(f"\n{'='*60}")
print("ANÁLISE")
print(f"{'='*60}")

# Último mês
ultimo_mes = datas[-1]
print(f"Último mês no histórico: {ultimo_mes} ({vendas[-1]:.0f})")

# Próximo mês
from datetime import datetime
ultimo_dt = datetime.strptime(ultimo_mes, '%Y-%m')
proximo_mes_num = (ultimo_dt.month % 12) + 1
proximo_ano = ultimo_dt.year if proximo_mes_num > ultimo_dt.month else ultimo_dt.year + 1
print(f"Próximo mês a prever: {proximo_ano}-{proximo_mes_num:02d} (Julho)")

# Médias mensais
vendas_por_mes = {}
for i, venda in enumerate(vendas):
    mes_do_ano = (i % 12) + 1
    if mes_do_ano not in vendas_por_mes:
        vendas_por_mes[mes_do_ano] = []
    vendas_por_mes[mes_do_ano].append(venda)

print(f"\nMédias por mês do ano:")
nomes_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
               'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
for mes in range(1, 13):
    if mes in vendas_por_mes:
        media = np.mean(vendas_por_mes[mes])
        valores = vendas_por_mes[mes]
        print(f"  {nomes_meses[mes-1]}: {media:6.1f} (valores: {valores})")

# Expectativa para Julho
print(f"\n{'='*60}")
print("EXPECTATIVA PARA JULHO 2024")
print(f"{'='*60}")
if 7 in vendas_por_mes:
    media_jul = np.mean(vendas_por_mes[7])
    print(f"Média histórica de Julho: {media_jul:.1f}")
    print("Valores históricos de Julho:", vendas_por_mes[7])
else:
    print("Não há dados históricos de Julho")

# Calcular previsão
demanda, desvio, metadata = DemandCalculator.calcular_demanda_inteligente(vendas)
print(f"\nPrevisão do sistema: {demanda:.1f}")
print(f"Método usado: {metadata['metodo_usado']}")
if 'periodo_sazonal' in metadata:
    print(f"Período sazonal: {metadata['periodo_sazonal']}")

# Verificar se está correto
print(f"\n{'='*60}")
if 7 in vendas_por_mes:
    media_jul = np.mean(vendas_por_mes[7])
    diff = abs(demanda - media_jul)
    if diff < 50:
        print(f"[OK] Previsão próxima da média de Julho (diff: {diff:.1f})")
    else:
        print(f"[ALERTA] Previsão diferente da média de Julho (diff: {diff:.1f})")
