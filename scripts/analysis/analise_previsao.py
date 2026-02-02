# -*- coding: utf-8 -*-
"""
Análise profunda do comportamento da previsão
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

print("=" * 80)
print("   ANÁLISE DETALHADA DA PREVISÃO")
print("=" * 80)
print()

# Conectar ao banco
conn = psycopg2.connect(
    host="localhost",
    database="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    port=5432
)

cursor = conn.cursor(cursor_factory=RealDictCursor)

# Buscar dados históricos mensais de Alimentos
query = """
    SELECT
        DATE_TRUNC('month', h.data) as data,
        SUM(h.qtd_venda) as qtd_venda
    FROM historico_vendas_diario h
    JOIN cadastro_produtos p ON h.codigo = p.codigo
    WHERE h.data >= CURRENT_DATE - INTERVAL '2 years'
      AND p.categoria = 'Alimentos'
    GROUP BY DATE_TRUNC('month', h.data)
    ORDER BY DATE_TRUNC('month', h.data)
"""

cursor.execute(query)
dados = cursor.fetchall()
cursor.close()
conn.close()

# Converter para DataFrame
df = pd.DataFrame(dados)
df['data'] = pd.to_datetime(df['data'])
df['qtd_venda'] = df['qtd_venda'].astype(float)
df = df.sort_values('data')

print(f"Total de períodos históricos: {len(df)}")
print(f"Data início: {df['data'].min()}")
print(f"Data fim: {df['data'].max()}")
print()

# Estatísticas básicas
print("ESTATÍSTICAS DOS DADOS HISTÓRICOS:")
print(f"  Média: {df['qtd_venda'].mean():,.2f}")
print(f"  Mediana: {df['qtd_venda'].median():,.2f}")
print(f"  Desvio Padrão: {df['qtd_venda'].std():,.2f}")
print(f"  Mínimo: {df['qtd_venda'].min():,.2f}")
print(f"  Máximo: {df['qtd_venda'].max():,.2f}")
print(f"  Coef. Variação: {(df['qtd_venda'].std() / df['qtd_venda'].mean() * 100):.2f}%")
print()

# Análise de tendência
df['mes_num'] = range(len(df))
correlacao = df['mes_num'].corr(df['qtd_venda'])
print(f"TENDÊNCIA:")
print(f"  Correlação temporal: {correlacao:.4f}")
if abs(correlacao) < 0.3:
    print(f"  Interpretação: Tendência FRACA (série relativamente estável)")
elif abs(correlacao) < 0.7:
    print(f"  Interpretação: Tendência MODERADA")
else:
    print(f"  Interpretação: Tendência FORTE")
print()

# Análise de sazonalidade
df['mes'] = df['data'].dt.month
media_por_mes = df.groupby('mes')['qtd_venda'].mean()
print("SAZONALIDADE (média por mês):")
meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
for mes in sorted(media_por_mes.index):
    valor = media_por_mes[mes]
    desvio_media = ((valor - df['qtd_venda'].mean()) / df['qtd_venda'].mean() * 100)
    print(f"  {meses_nomes[mes-1]}: {valor:,.0f} ({desvio_media:+.1f}% vs média)")

print()

# Análise da divisão 50/25/25
total_periodos = len(df)
tamanho_base = int(total_periodos * 0.50)
tamanho_teste = int(total_periodos * 0.25)
tamanho_previsao = total_periodos - tamanho_base - tamanho_teste

serie_base = df['qtd_venda'].iloc[:tamanho_base].values
serie_teste = df['qtd_venda'].iloc[tamanho_base:tamanho_base + tamanho_teste].values
serie_validacao = df['qtd_venda'].iloc[tamanho_base + tamanho_teste:].values

print("DIVISÃO DOS DADOS (50/25/25):")
print(f"  Base ({tamanho_base} períodos):")
print(f"    Média: {serie_base.mean():,.2f}")
print(f"    Últimos 3 meses: {serie_base[-3:].mean():,.2f}")
print()
print(f"  Teste ({tamanho_teste} períodos):")
print(f"    Média: {serie_teste.mean():,.2f}")
print(f"    Valores: {[f'{v:,.0f}' for v in serie_teste]}")
print()
print(f"  Validação ({len(serie_validacao)} períodos):")
print(f"    Média: {serie_validacao.mean():,.2f}")
print(f"    Valores: {[f'{v:,.0f}' for v in serie_validacao]}")
print()

# Problema identificado
print("=" * 80)
print("ANÁLISE DO PROBLEMA:")
print("=" * 80)
print()

# 1. Suavização Exponencial Simples
alpha = 0.3
nivel = serie_base[0]
previsoes_ses = []

for i in range(len(serie_base)):
    previsoes_ses.append(nivel)
    nivel = alpha * serie_base[i] + (1 - alpha) * nivel

# Previsão do SES (sempre o último nível)
previsao_ses = nivel
print(f"1. SUAVIZAÇÃO EXPONENCIAL SIMPLES:")
print(f"   Último nível calculado: {nivel:,.2f}")
print(f"   Previsão (constante): {previsao_ses:,.2f}")
print(f"   Problema: Modelo assume que o futuro = último nível calculado")
print(f"   Não captura sazonalidade nem tendência!")
print()

# 2. Comparação dos últimos meses
ultimos_6_base = serie_base[-6:].mean()
ultimos_6_teste = serie_teste.mean()
print(f"2. COMPARAÇÃO TEMPORAL:")
print(f"   Média últimos 6 meses da base: {ultimos_6_base:,.2f}")
print(f"   Média período de teste: {ultimos_6_teste:,.2f}")
print(f"   Diferença: {((ultimos_6_teste - ultimos_6_base) / ultimos_6_base * 100):+.2f}%")
print()

# 3. Ano anterior
print(f"3. COMPARAÇÃO ANO ANTERIOR:")
print(f"   Previsão SES: {previsao_ses:,.2f}")
print(f"   Média histórica: {df['qtd_venda'].mean():,.2f}")
print(f"   Redução: {((previsao_ses - df['qtd_venda'].mean()) / df['qtd_venda'].mean() * 100):.2f}%")
print()

print("=" * 80)
print("RECOMENDAÇÕES:")
print("=" * 80)
print()
print("1. PROBLEMA PRINCIPAL:")
print("   - Modelos simples (SES, Média Móvel) NÃO capturam sazonalidade")
print("   - Resultado: previsão LINEAR (mesmo valor todos os meses)")
print("   - Isso é INADEQUADO para dados com padrão sazonal")
print()
print("2. DIVISÃO 50/25/25:")
print("   - Com apenas 25 períodos históricos, usar só 12 para treinar é INSUFICIENTE")
print("   - Modelos não têm dados suficientes para aprender padrões sazonais")
print()
print("3. SOLUÇÕES PROPOSTAS:")
print("   a) Usar divisão 70/15/15 (mais dados para treino)")
print("   b) Implementar modelo sazonal (Holt-Winters sazonal)")
print("   c) Usar SARIMAX (média móvel sazonal autoregressiva)")
print("   d) Adicionar decomposição sazonal antes da previsão")
print()
print("4. MODELO HOLT-WINTERS:")
print("   - PROBLEMA: Implementação atual não está capturando sazonalidade")
print("   - Precisa de ajuste nos parâmetros sazonais")
print()

print("=" * 80)
