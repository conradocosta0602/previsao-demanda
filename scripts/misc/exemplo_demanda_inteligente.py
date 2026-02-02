# -*- coding: utf-8 -*-
"""
Exemplo de Uso do Calculo Inteligente de Demanda
Demonstra os diferentes metodos e quando usar cada um
"""

import pandas as pd
import numpy as np
from core.demand_calculator import DemandCalculator

print("=" * 80)
print(" DEMONSTRACAO: CALCULO INTELIGENTE DE DEMANDA")
print("=" * 80)
print()

# CENARIO 1: Demanda Estavel
print("CENARIO 1: Demanda Estavel")
print("-" * 80)

vendas_estaveis = [100, 105, 98, 102, 100, 103, 99, 101, 100, 104, 102, 98]

demanda_simples, desvio_simples = DemandCalculator.calcular_demanda_simples(vendas_estaveis)
print(f"Metodo Simples:        Demanda = {demanda_simples:.1f}, Desvio = {desvio_simples:.1f}")

demanda_ema, desvio_ema = DemandCalculator.calcular_demanda_ema(vendas_estaveis)
print(f"Metodo EMA:            Demanda = {demanda_ema:.1f}, Desvio = {desvio_ema:.1f}")

demanda_auto, desvio_auto, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_estaveis)
print(f"Metodo Inteligente:    Demanda = {demanda_auto:.1f}, Desvio = {desvio_auto:.1f}")
print(f"  -> Metodo escolhido: {metadata['metodo_usado']}")
print(f"  -> Padrao detectado: {metadata['classificacao']['padrao']}")
print()

# CENARIO 2: Demanda com Tendencia de Crescimento
print("CENARIO 2: Demanda com Tendencia de Crescimento")
print("-" * 80)

vendas_crescimento = [100, 110, 115, 125, 135, 140, 150, 160, 165, 175, 180, 190]

demanda_simples, _ = DemandCalculator.calcular_demanda_simples(vendas_crescimento)
print(f"Metodo Simples:        Demanda = {demanda_simples:.1f} (subestima)")

demanda_tend, desvio_tend = DemandCalculator.calcular_demanda_tendencia(vendas_crescimento)
print(f"Metodo Tendencia:      Demanda = {demanda_tend:.1f} (projeta proximo valor)")

demanda_auto, desvio_auto, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_crescimento)
print(f"Metodo Inteligente:    Demanda = {demanda_auto:.1f}")
print(f"  -> Metodo escolhido: {metadata['metodo_usado']}")
print(f"  -> Tendencia detectada: {metadata['classificacao']['tendencia']}")
print()

# CENARIO 3: Demanda Sazonal (picos em dezembro)
print("CENARIO 3: Demanda Sazonal (Natal em Dezembro)")
print("-" * 80)

vendas_sazonais = [
    100, 95, 90, 85, 90, 95, 100, 105, 110, 120, 130, 200,  # Ano 1
    105, 100, 95, 90, 95, 100, 105, 110, 115, 125, 135, 220  # Ano 2
]

demanda_simples, _ = DemandCalculator.calcular_demanda_simples(vendas_sazonais)
print(f"Metodo Simples:        Demanda = {demanda_simples:.1f} (mistura tudo)")

demanda_saz, desvio_saz = DemandCalculator.calcular_demanda_sazonal(vendas_sazonais, periodo_sazonal=12)
print(f"Metodo Sazonal:        Demanda = {demanda_saz:.1f} (ajusta para proximo mes)")

demanda_auto, desvio_auto, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_sazonais)
print(f"Metodo Inteligente:    Demanda = {demanda_auto:.1f}")
print(f"  -> Metodo escolhido: {metadata['metodo_usado']}")
print(f"  -> Sazonalidade: {metadata['classificacao']['sazonalidade']}")
print()

# CENARIO 4: Demanda Intermitente (vendas esporadicas)
print("CENARIO 4: Demanda Intermitente (vendas esporadicas)")
print("-" * 80)

vendas_intermitentes = [0, 0, 50, 0, 0, 45, 0, 0, 0, 52, 0, 0, 48, 0, 0, 0, 55]

demanda_simples, desvio_simples = DemandCalculator.calcular_demanda_simples(vendas_intermitentes)
print(f"Metodo Simples:        Demanda = {demanda_simples:.1f}, Desvio = {desvio_simples:.1f}")

demanda_croston, desvio_croston = DemandCalculator.calcular_demanda_croston(vendas_intermitentes)
print(f"Metodo Croston:        Demanda = {demanda_croston:.1f}, Desvio = {desvio_croston:.1f}")

demanda_auto, desvio_auto, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_intermitentes)
print(f"Metodo Inteligente:    Demanda = {demanda_auto:.1f}, Desvio = {desvio_auto:.1f}")
print(f"  -> Metodo escolhido: {metadata['metodo_usado']}")
print(f"  -> Padrao detectado: {metadata['classificacao']['padrao']}")
print(f"  -> % de zeros: {metadata['classificacao']['zeros_pct']:.1f}%")
print()

# CENARIO 5: Demanda Variavel (alta volatilidade)
print("CENARIO 5: Demanda Muito Variavel")
print("-" * 80)

vendas_variaveis = [100, 150, 80, 200, 90, 170, 110, 180, 75, 160, 95, 190]

demanda_simples, desvio_simples = DemandCalculator.calcular_demanda_simples(vendas_variaveis)
print(f"Metodo Simples:        Demanda = {demanda_simples:.1f}, Desvio = {desvio_simples:.1f}")

demanda_ema, desvio_ema = DemandCalculator.calcular_demanda_ema(vendas_variaveis, alpha=0.4)
print(f"Metodo EMA (a=0.4):    Demanda = {demanda_ema:.1f}, Desvio = {desvio_ema:.1f}")

demanda_auto, desvio_auto, metadata = DemandCalculator.calcular_demanda_inteligente(vendas_variaveis)
print(f"Metodo Inteligente:    Demanda = {demanda_auto:.1f}, Desvio = {desvio_auto:.1f}")
print(f"  -> Metodo escolhido: {metadata['metodo_usado']}")
print(f"  -> CV (volatilidade): {metadata['classificacao']['cv']:.2f}")
print()

# COMPARACAO DE IMPACTO NO ESTOQUE DE SEGURANCA
print("=" * 80)
print(" IMPACTO NO ESTOQUE DE SEGURANCA")
print("=" * 80)
print()

from scipy import stats

lead_time = 15  # dias
nivel_servico = 0.95
z_score = stats.norm.ppf(nivel_servico)

print(f"Parametros: Lead Time = {lead_time} dias, Nivel de Servico = {nivel_servico*100:.0f}%")
print()

cenarios = [
    ("Demanda Estavel", vendas_estaveis),
    ("Demanda Crescimento", vendas_crescimento),
    ("Demanda Sazonal", vendas_sazonais),
    ("Demanda Intermitente", vendas_intermitentes),
    ("Demanda Variavel", vendas_variaveis)
]

for nome, vendas in cenarios:
    demanda_s, desvio_s = DemandCalculator.calcular_demanda_simples(vendas)
    demanda_i, desvio_i, _ = DemandCalculator.calcular_demanda_inteligente(vendas)

    desvio_diario_s = desvio_s / np.sqrt(30)
    desvio_diario_i = desvio_i / np.sqrt(30)

    es_simples = z_score * desvio_diario_s * np.sqrt(lead_time)
    es_inteligente = z_score * desvio_diario_i * np.sqrt(lead_time)

    diferenca = es_inteligente - es_simples
    diferenca_pct = (diferenca / es_simples * 100) if es_simples > 0 else 0

    print(f"{nome:25} | Simples: {es_simples:6.1f} un | Inteligente: {es_inteligente:6.1f} un | Delta: {diferenca:+6.1f} ({diferenca_pct:+.1f}%)")

print()
print("=" * 80)
print(" CONCLUSAO")
print("=" * 80)
print()
print("O metodo INTELIGENTE (auto):")
print("  - Detecta automaticamente o padrao de cada item")
print("  - Escolhe o melhor metodo de calculo")
print("  - Reduz risco de ruptura em itens com tendencia/sazonalidade")
print("  - Otimiza estoque de seguranca para cada padrao")
print("  - Economiza capital em itens estaveis")
print()
print("RECOMENDACAO: Use 'auto' para ter o melhor dos dois mundos!")
print("=" * 80)
