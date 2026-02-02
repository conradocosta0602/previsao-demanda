"""
Debug detalhado do método sazonal
"""
import pandas as pd
import numpy as np

# Carregar dados PROD_001
df = pd.read_excel('dados_teste_integrado.xlsx')
df_sku = df[df['SKU'] == 'PROD_001'].copy()
df_sku = df_sku.groupby('Mes', as_index=False).agg({'Vendas': 'sum'})
df_sku = df_sku.sort_values('Mes')

vendas = df_sku['Vendas'].tolist()
n = len(vendas)

print(f"Total períodos: {n}")
print(f"Vendas: {vendas}\n")

# Simular cálculo do método sazonal
vendas_array = np.array(vendas)

# Agrupar por mês do ano
vendas_por_mes = {}
for i, venda in enumerate(vendas_array):
    mes_do_ano = (i % 12) + 1
    if mes_do_ano not in vendas_por_mes:
        vendas_por_mes[mes_do_ano] = []
    vendas_por_mes[mes_do_ano].append(venda)

print("Vendas agrupadas por mês do ano:")
for mes, valores in sorted(vendas_por_mes.items()):
    print(f"  Mês {mes:2d}: {valores}")

# Médias mensais
medias_mensais = {}
for mes in range(1, 13):
    if mes in vendas_por_mes and len(vendas_por_mes[mes]) > 0:
        medias_mensais[mes] = np.mean(vendas_por_mes[mes])
    else:
        medias_mensais[mes] = np.mean(vendas_array)

print(f"\nMédias mensais:")
for mes, media in sorted(medias_mensais.items()):
    print(f"  Mês {mes:2d}: {media:.1f}")

# Média geral
media_geral = np.mean(list(medias_mensais.values()))
print(f"\nMédia geral: {media_geral:.1f}")

# Índices sazonais
indices_mensais = {}
for mes in range(1, 13):
    indices_mensais[mes] = medias_mensais[mes] / media_geral if media_geral > 0 else 1.0

print(f"\nÍndices sazonais:")
for mes, indice in sorted(indices_mensais.items()):
    tipo = "ALTO" if indice > 1.1 else "BAIXO" if indice < 0.9 else "NORMAL"
    print(f"  Mês {mes:2d}: {indice:.3f} ({tipo})")

# Próximo mês
proximo_mes = (n % 12) + 1
print(f"\n{'='*60}")
print(f"CÁLCULO DO PRÓXIMO MÊS")
print(f"{'='*60}")
print(f"n = {n}")
print(f"n % 12 = {n % 12}")
print(f"proximo_mes = ({n} % 12) + 1 = {proximo_mes}")
print(f"Índice sazonal do mês {proximo_mes}: {indices_mensais[proximo_mes]:.3f}")

# Dessazonalizar
vendas_dessaz = []
for i, venda in enumerate(vendas_array):
    mes_do_dado = (i % 12) + 1
    indice = indices_mensais[mes_do_dado]
    venda_dessaz = venda / indice if indice > 0 else venda
    vendas_dessaz.append(venda_dessaz)

print(f"\nVendas dessazonalizadas:")
print(f"  {vendas_dessaz}")

# Calcular tendência dos últimos 6-12 meses
from core.demand_calculator import DemandCalculator

janela = min(12, max(6, n // 2))
print(f"\nUsando últimos {janela} meses para tendência")
print(f"Vendas dessazonalizadas[-{janela}:]: {vendas_dessaz[-janela:]}")

tendencia, desvio = DemandCalculator.calcular_demanda_tendencia(vendas_dessaz[-janela:])
print(f"Tendência calculada: {tendencia:.2f}")

# Aplicar índice
fator_sazonal = indices_mensais[proximo_mes]
demanda_final = tendencia * fator_sazonal
print(f"\n{'='*60}")
print(f"RESULTADO FINAL")
print(f"{'='*60}")
print(f"Tendência: {tendencia:.2f}")
print(f"Fator sazonal (mês {proximo_mes}): {fator_sazonal:.3f}")
print(f"Demanda final: {demanda_final:.2f}")

# Comparar com método oficial
demanda_oficial, desvio_oficial = DemandCalculator.calcular_demanda_sazonal(vendas)
print(f"\nDemanda método oficial: {demanda_oficial:.2f}")
print(f"Diferença: {abs(demanda_final - demanda_oficial):.2f}")
