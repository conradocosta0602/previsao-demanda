"""
Teste de detecção de sazonalidade semestral
Simula o caso do usuário: queda de Julho a Dezembro
"""
import numpy as np
from core.demand_calculator import DemandCalculator

# Simular dados com padrão semestral
# Jan-Jun: Alta demanda
# Jul-Dez: Baixa demanda
print("="*80)
print("TESTE - SAZONALIDADE SEMESTRAL (Padrão Jul-Dez baixo)")
print("="*80)

vendas = []
meses = []

# 2023
for mes in range(1, 13):
    if mes <= 6:  # Jan-Jun: Alta
        base = 120
    else:  # Jul-Dez: Baixa
        base = 80
    ruido = np.random.normal(0, 5)
    vendas.append(max(0, base + ruido))
    meses.append(f"2023-{mes:02d}")

# 2024
for mes in range(1, 13):
    if mes <= 6:  # Jan-Jun: Alta
        base = 125  # Leve crescimento
    else:  # Jul-Dez: Baixa
        base = 85
    ruido = np.random.normal(0, 5)
    vendas.append(max(0, base + ruido))
    meses.append(f"2024-{mes:02d}")

print(f"\nDados gerados: {len(vendas)} meses")
print(f"Média Jan-Jun 2023: {np.mean(vendas[0:6]):.1f}")
print(f"Média Jul-Dez 2023: {np.mean(vendas[6:12]):.1f}")
print(f"Média Jan-Jun 2024: {np.mean(vendas[12:18]):.1f}")
print(f"Média Jul-Dez 2024: {np.mean(vendas[18:24]):.1f}")

# Classificar padrão
print("\n" + "="*80)
print("CLASSIFICAÇÃO AUTOMÁTICA")
print("="*80)

classificacao = DemandCalculator.classificar_padrao_demanda(vendas)
print(f"Padrão detectado: {classificacao['padrao']}")
print(f"Método recomendado: {classificacao['metodo_recomendado']}")
print(f"Tem sazonalidade? {classificacao.get('sazonalidade', 'N/A')}")

if classificacao.get('tem_sazonalidade'):
    print(f"Período sazonal: {classificacao.get('periodo_sazonal', 'N/A')}")
    print(f"Força sazonal: {classificacao.get('forca_sazonalidade', 'N/A')}")

# Calcular previsão
print("\n" + "="*80)
print("PREVISÕES")
print("="*80)

# Método inteligente (automático)
demanda_int, desvio_int, metadata = DemandCalculator.calcular_demanda_inteligente(vendas)
print(f"\nINTELIGENTE:")
print(f"  Método usado: {metadata['metodo_usado']}")
print(f"  Previsão: {demanda_int:.1f}")
print(f"  Última venda: {vendas[-1]:.1f}")
print(f"  Diferença: {demanda_int - vendas[-1]:+.1f}")

if 'periodo_sazonal' in metadata:
    print(f"  Período aplicado: {metadata['periodo_sazonal']}")

# Método sazonal explícito
demanda_saz, desvio_saz = DemandCalculator.calcular_demanda_sazonal(vendas, periodo_sazonal=6)
print(f"\nSAZONAL (período=6):")
print(f"  Previsão: {demanda_saz:.1f}")
print(f"  Última venda: {vendas[-1]:.1f}")
print(f"  Diferença: {demanda_saz - vendas[-1]:+.1f}")

# Método tendência (sem sazonalidade)
demanda_tend, desvio_tend = DemandCalculator.calcular_demanda_tendencia(vendas)
print(f"\nTENDÊNCIA (sem sazonalidade):")
print(f"  Previsão: {demanda_tend:.1f}")
print(f"  Última venda: {vendas[-1]:.1f}")
print(f"  Diferença: {demanda_tend - vendas[-1]:+.1f}")

# Análise
print("\n" + "="*80)
print("ANÁLISE")
print("="*80)

mes_atual = 24  # Dezembro 2024 (último mês)
proximo_mes = (mes_atual % 12) + 1  # Janeiro 2025

if proximo_mes <= 6:
    expectativa = "ALTA (Jan-Jun)"
    faixa_esperada = (115, 135)
else:
    expectativa = "BAIXA (Jul-Dez)"
    faixa_esperada = (75, 95)

print(f"\nMês atual: {meses[-1]} (Dezembro)")
print(f"Próximo mês: Janeiro 2025")
print(f"Expectativa: {expectativa}")
print(f"Faixa esperada: {faixa_esperada[0]:.0f} - {faixa_esperada[1]:.0f}")

print(f"\nPrevisão INTELIGENTE: {demanda_int:.1f}")
if faixa_esperada[0] <= demanda_int <= faixa_esperada[1]:
    print("[OK] Previsão dentro da faixa esperada!")
else:
    print("[ALERTA] Previsão FORA da faixa esperada!")
    print("Possível problema: Sazonalidade não capturada corretamente")

# Mostrar últimos 12 meses para visualizar padrão
print("\n" + "="*80)
print("HISTÓRICO ÚLTIMOS 12 MESES")
print("="*80)
for i in range(12, 24):
    print(f"{meses[i]}: {vendas[i]:.1f}")

print("\n" + "="*80)
