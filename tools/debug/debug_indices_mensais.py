"""
Debug dos índices mensais calculados
"""
import numpy as np
from core.demand_calculator import DemandCalculator

# Dados semestrais: Jan-Jun alto, Jul-Dez baixo
vendas = []
for ano in [0, 1]:
    for mes in range(1, 13):
        if mes <= 6:
            base = 120 + (ano * 5)
        else:
            base = 80 + (ano * 6)
        ruido = np.random.normal(0, 5)
        vendas.append(max(0, base + ruido))

print("Histórico (24 meses):")
for i, v in enumerate(vendas):
    mes = (i % 12) + 1
    ano = 2023 + (i // 12)
    print(f"{ano}-{mes:02d}: {v:.1f}")

# Agrupar por mês do ano
vendas_por_mes = {}
for i, venda in enumerate(vendas):
    mes_do_ano = (i % 12) + 1
    if mes_do_ano not in vendas_por_mes:
        vendas_por_mes[mes_do_ano] = []
    vendas_por_mes[mes_do_ano].append(venda)

print("\n" + "="*60)
print("MÉDIAS POR MÊS DO ANO")
print("="*60)

medias_mensais = {}
for mes in range(1, 13):
    if mes in vendas_por_mes:
        media = np.mean(vendas_por_mes[mes])
        medias_mensais[mes] = media
        valores = vendas_por_mes[mes]
        print(f"Mes {mes:2d}: {valores} => Media: {media:.1f}")

media_geral = np.mean(list(medias_mensais.values()))
print(f"\nMédia geral: {media_geral:.1f}")

print("\n" + "="*60)
print("ÍNDICES SAZONAIS")
print("="*60)

indices = {}
for mes in range(1, 13):
    indice = medias_mensais[mes] / media_geral
    indices[mes] = indice
    print(f"Mês {mes:2d}: {indice:.3f} ({'ALTO' if indice > 1.1 else 'BAIXO' if indice < 0.9 else 'NORMAL'})")

print("\n" + "="*60)
print("PREVISÃO PARA JANEIRO 2025")
print("="*60)

# Último mês = Dezembro (mês 12 do ano, posição 23 na lista)
n = len(vendas)
proximo_mes = (n % 12) + 1
print(f"Próximo mês: {proximo_mes} (Janeiro)")
print(f"Índice sazonal de Janeiro: {indices[proximo_mes]:.3f}")

# Calcular tendência dos últimos meses
janela = min(max(3, n // 4), 6)
print(f"\nUsando últimos {janela} meses para tendência:")
ultimos = vendas[-janela:]
for i, v in enumerate(ultimos):
    pos_real = n - janela + i
    mes_real = (pos_real % 12) + 1
    print(f"  Posição {pos_real}: Mês {mes_real:2d} = {v:.1f}")

tendencia, _ = DemandCalculator.calcular_demanda_tendencia(ultimos)
print(f"\nTendência calculada: {tendencia:.1f}")
print(f"Aplicando índice de Janeiro ({indices[proximo_mes]:.3f}): {tendencia * indices[proximo_mes]:.1f}")

# Teste com método sazonal
demanda_saz, _ = DemandCalculator.calcular_demanda_sazonal(vendas)
print(f"\nPrevisão método sazonal: {demanda_saz:.1f}")

# Expectativa real
print(f"\n{'='*60}")
print("EXPECTATIVA REAL")
print(f"{'='*60}")
print(f"Média Jan histórica: {medias_mensais[1]:.1f}")
print(f"Com tendência ~+5: ~{medias_mensais[1] + 5:.1f}")
