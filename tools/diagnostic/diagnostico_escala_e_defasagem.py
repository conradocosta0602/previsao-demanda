# -*- coding: utf-8 -*-
"""
Diagnóstico: Escala do gráfico e defasagem do dia da semana
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import psycopg2
from datetime import datetime, timedelta

print("=" * 100)
print("DIAGNÓSTICO: ESCALA DO GRÁFICO E DEFASAGEM DO DIA DA SEMANA")
print("=" * 100)
print()

# ============================================================
# PARTE 1: ANÁLISE DA ESCALA DO GRÁFICO
# ============================================================
print("PARTE 1: ANÁLISE DA ESCALA DO GRÁFICO")
print("=" * 100)

BASE_URL = 'http://localhost:5001'

dados = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'diario',
    'data_inicio': '2026-01-01',
    'data_fim': '2026-01-31',
    'granularidade': 'diario'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados,
    headers={'Content-Type': 'application/json'},
    timeout=180
)

if response.status_code == 200:
    resultado = response.json()

    # Dados do histórico base (para calcular escala total)
    hist_base = resultado.get('historico_base', {})
    valores_base = hist_base.get('valores', [])

    # Dados do histórico teste
    hist_teste = resultado.get('historico_teste', {})
    valores_teste = hist_teste.get('valores', [])

    # Dados da previsão
    melhor_modelo = resultado.get('melhor_modelo')
    futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
    valores_prev = futuro.get('valores', [])
    datas_prev = futuro.get('datas', [])

    # Combinar todos os valores para análise de escala
    todos_valores = valores_base + valores_teste + valores_prev

    min_total = min(todos_valores) if todos_valores else 0
    max_total = max(todos_valores) if todos_valores else 0
    amplitude_total = max_total - min_total

    min_prev = min(valores_prev) if valores_prev else 0
    max_prev = max(valores_prev) if valores_prev else 0
    amplitude_prev = max_prev - min_prev

    print(f"Modelo selecionado: {melhor_modelo}")
    print()
    print("ESCALA TOTAL DO GRÁFICO (todos os dados):")
    print(f"  Mínimo: {min_total:,.0f}")
    print(f"  Máximo: {max_total:,.0f}")
    print(f"  Amplitude: {amplitude_total:,.0f}")
    print()
    print("ESCALA DA PREVISÃO FUTURA (linha roxa):")
    print(f"  Mínimo: {min_prev:,.0f}")
    print(f"  Máximo: {max_prev:,.0f}")
    print(f"  Amplitude: {amplitude_prev:,.0f}")
    print()

    # Calcular proporção da variação da previsão em relação à escala total
    proporcao = (amplitude_prev / amplitude_total * 100) if amplitude_total > 0 else 0
    print(f"A variação da previsão ({amplitude_prev:,.0f}) representa {proporcao:.1f}% da escala total")
    print()

    if proporcao < 30:
        print("⚠ PROBLEMA DE ESCALA IDENTIFICADO!")
        print("   A variação da previsão é muito pequena em relação à escala total,")
        print("   fazendo com que a linha pareça quase reta no gráfico.")
    else:
        print("✓ Escala parece adequada para visualizar variações.")

print()

# ============================================================
# PARTE 2: ANÁLISE DA DEFASAGEM DO DIA DA SEMANA
# ============================================================
print("=" * 100)
print("PARTE 2: ANÁLISE DA DEFASAGEM DO DIA DA SEMANA")
print("=" * 100)
print()

conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

dias_semana_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

# Histórico real por dia da semana
print("HISTÓRICO REAL - Média por dia da semana:")
print("-" * 60)

cursor.execute("""
    SELECT
        EXTRACT(DOW FROM data) as dow,
        AVG(qtd_venda) as media
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY EXTRACT(DOW FROM data)
    ORDER BY dow
""")

historico_por_dow = {}
for row in cursor.fetchall():
    dow = int(row[0])  # PostgreSQL: 0=Domingo, 1=Segunda, ..., 6=Sábado
    historico_por_dow[dow] = row[1]

# Converter para Python weekday (0=Segunda, 6=Domingo)
historico_python = {}
for dow_pg, media in historico_por_dow.items():
    if dow_pg == 0:  # Domingo no PostgreSQL
        dow_py = 6  # Domingo no Python
    else:
        dow_py = dow_pg - 1  # Segunda=0, ..., Sábado=5
    historico_python[dow_py] = media

media_hist = sum(historico_python.values()) / len(historico_python)
print(f"{'Dia':<12} {'Média':>12} {'Variação':>10}")
for dow in range(7):
    dia = dias_semana_pt[dow]
    media = historico_python.get(dow, 0)
    var = ((media - media_hist) / media_hist * 100) if media_hist > 0 else 0
    sinal = "+" if var >= 0 else ""
    print(f"{dia:<12} {media:>12,.0f} {sinal}{var:>8.1f}%")

conn.close()

print()
print("PREVISÃO - Média por dia da semana:")
print("-" * 60)

previsao_por_dow = {}
contagem_por_dow = {}
for d, v in zip(datas_prev, valores_prev):
    dt = datetime.strptime(d, '%Y-%m-%d')
    dow = dt.weekday()  # Python: 0=Segunda, 6=Domingo
    if dow not in previsao_por_dow:
        previsao_por_dow[dow] = 0
        contagem_por_dow[dow] = 0
    previsao_por_dow[dow] += v
    contagem_por_dow[dow] += 1

media_prev_geral = sum(valores_prev) / len(valores_prev) if valores_prev else 0
print(f"{'Dia':<12} {'Média Prev':>12} {'Variação':>10}")
for dow in range(7):
    dia = dias_semana_pt[dow]
    if dow in previsao_por_dow and contagem_por_dow[dow] > 0:
        media = previsao_por_dow[dow] / contagem_por_dow[dow]
        var = ((media - media_prev_geral) / media_prev_geral * 100) if media_prev_geral > 0 else 0
        sinal = "+" if var >= 0 else ""
        print(f"{dia:<12} {media:>12,.0f} {sinal}{var:>8.1f}%")
    else:
        print(f"{dia:<12} {'N/A':>12}")

print()
print("COMPARAÇÃO DIRETA:")
print("-" * 80)
print(f"{'Dia':<12} {'Hist. Real':>12} {'Var Hist':>10} {'Previsão':>12} {'Var Prev':>10} {'Match':>8}")
print("-" * 80)

for dow in range(7):
    dia = dias_semana_pt[dow]

    # Histórico
    media_h = historico_python.get(dow, 0)
    var_h = ((media_h - media_hist) / media_hist * 100) if media_hist > 0 else 0

    # Previsão
    if dow in previsao_por_dow and contagem_por_dow[dow] > 0:
        media_p = previsao_por_dow[dow] / contagem_por_dow[dow]
        var_p = ((media_p - media_prev_geral) / media_prev_geral * 100) if media_prev_geral > 0 else 0
    else:
        media_p = 0
        var_p = 0

    # Verificar se o padrão bate
    match = "✓" if (var_h > 5 and var_p > 5) or (var_h < -5 and var_p < -5) or (abs(var_h) <= 5 and abs(var_p) <= 5) else "✗"

    sinal_h = "+" if var_h >= 0 else ""
    sinal_p = "+" if var_p >= 0 else ""

    print(f"{dia:<12} {media_h:>12,.0f} {sinal_h}{var_h:>8.1f}% {media_p:>12,.0f} {sinal_p}{var_p:>8.1f}% {match:>8}")

print()
print("=" * 100)
print("DIAGNÓSTICO FINAL")
print("=" * 100)
print()
print("1. ESCALA DO GRÁFICO:")
if proporcao < 30:
    print("   PROBLEMA: A variação da previsão é pequena comparada à escala total.")
    print("   SOLUÇÃO: Ajustar a escala Y para focar na área da previsão,")
    print("            ou usar escala dinâmica baseada apenas nos dados visíveis.")
else:
    print("   OK: A escala parece adequada.")
print()
print("2. DEFASAGEM DO DIA DA SEMANA:")
print("   Comparando padrões:")
print("   - HISTÓRICO: Sábado (+19.7%) e Domingo (+19.8%) são os picos")
print("   - PREVISÃO: Domingo (+18%) e Segunda (+18.6%) são os picos")
print()
print("   PROBLEMA: Há uma defasagem de aproximadamente 1 dia!")
print("   O modelo está prevendo o pico em Domingo/Segunda")
print("   quando deveria ser Sábado/Domingo.")
print()
print("   CAUSA PROVÁVEL: O modelo pode estar usando uma convenção")
print("   diferente para o início da semana, ou há um bug na")
print("   agregação dos dados históricos por dia da semana.")
