# -*- coding: utf-8 -*-
"""
Diagnóstico: Sazonalidade diária (padrão por dia da semana)
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import psycopg2
from datetime import datetime

print("=" * 100)
print("DIAGNÓSTICO: SAZONALIDADE DIÁRIA (PADRÃO POR DIA DA SEMANA)")
print("=" * 100)
print()

# ============================================================
# 1. Verificar padrão histórico por dia da semana
# ============================================================
print("1. PADRÃO HISTÓRICO POR DIA DA SEMANA (últimos 12 meses)")
print("-" * 100)

conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

cursor.execute("""
    SELECT
        EXTRACT(DOW FROM data) as dia_semana,
        AVG(qtd_venda) as media,
        MIN(qtd_venda) as minimo,
        MAX(qtd_venda) as maximo,
        COUNT(*) as qtd_dias
    FROM historico_vendas_diario
    WHERE data >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY EXTRACT(DOW FROM data)
    ORDER BY dia_semana
""")

print(f"{'Dia':<12} {'Média':>12} {'Mínimo':>12} {'Máximo':>12} {'Qtd Dias':>10}")
print("-" * 60)

medias_por_dia = {}
for row in cursor.fetchall():
    dow = int(row[0])
    # PostgreSQL: 0=Domingo, 1=Segunda, ..., 6=Sábado
    dia_nome = dias_semana[dow - 1] if dow > 0 else dias_semana[6]
    medias_por_dia[dow] = row[1]
    print(f"{dia_nome:<12} {row[1]:>12,.0f} {row[2]:>12,.0f} {row[3]:>12,.0f} {row[4]:>10}")

# Calcular variação percentual em relação à média geral
media_geral = sum(medias_por_dia.values()) / len(medias_por_dia)
print()
print(f"Média geral: {media_geral:,.0f}")
print()
print("Variação em relação à média:")
for dow, media in sorted(medias_por_dia.items()):
    dia_nome = dias_semana[dow - 1] if dow > 0 else dias_semana[6]
    variacao = ((media - media_geral) / media_geral) * 100
    sinal = "+" if variacao >= 0 else ""
    print(f"  {dia_nome:<12}: {sinal}{variacao:.1f}%")

conn.close()

print()

# ============================================================
# 2. Verificar previsão diária retornada pela API
# ============================================================
print("2. PREVISÃO DIÁRIA RETORNADA PELA API (Jan-Mar 2026)")
print("-" * 100)

BASE_URL = 'http://localhost:5001'

dados = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'diario',
    'data_inicio': '2026-01-01',
    'data_fim': '2026-01-14',  # 2 semanas para análise
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
    melhor_modelo = resultado.get('melhor_modelo')
    futuro = resultado.get('modelos', {}).get(melhor_modelo, {}).get('futuro', {})
    datas = futuro.get('datas', [])
    valores = futuro.get('valores', [])

    print(f"Modelo: {melhor_modelo}")
    print()
    print(f"{'Data':<12} {'Dia Semana':<12} {'Previsão':>12} {'Variação':>10}")
    print("-" * 50)

    media_previsao = sum(valores) / len(valores) if valores else 0

    for d, v in zip(datas, valores):
        dt = datetime.strptime(d, '%Y-%m-%d')
        dow = dt.weekday()  # Python: 0=Segunda, 6=Domingo
        dia_nome = dias_semana[dow]
        variacao = ((v - media_previsao) / media_previsao) * 100 if media_previsao > 0 else 0
        sinal = "+" if variacao >= 0 else ""
        print(f"{d:<12} {dia_nome:<12} {v:>12,.0f} {sinal}{variacao:>8.1f}%")

    print()
    print(f"Média da previsão: {media_previsao:,.0f}")

    # Agrupar por dia da semana
    print()
    print("Média da PREVISÃO por dia da semana:")
    previsao_por_dia = {}
    contagem_por_dia = {}
    for d, v in zip(datas, valores):
        dt = datetime.strptime(d, '%Y-%m-%d')
        dow = dt.weekday()
        if dow not in previsao_por_dia:
            previsao_por_dia[dow] = 0
            contagem_por_dia[dow] = 0
        previsao_por_dia[dow] += v
        contagem_por_dia[dow] += 1

    for dow in sorted(previsao_por_dia.keys()):
        media = previsao_por_dia[dow] / contagem_por_dia[dow]
        dia_nome = dias_semana[dow]
        variacao = ((media - media_previsao) / media_previsao) * 100
        sinal = "+" if variacao >= 0 else ""
        print(f"  {dia_nome:<12}: {media:>10,.0f} ({sinal}{variacao:.1f}%)")

else:
    print(f"Erro: {response.status_code}")

print()
print("=" * 100)
print("CONCLUSÃO")
print("=" * 100)
print()
print("Se o histórico mostra variação significativa por dia da semana")
print("(ex: domingo/sábado com +20-30% vs dias úteis),")
print("mas a previsão mostra valores quase constantes,")
print("então o modelo NÃO está capturando a sazonalidade diária.")
print()
print("Isso acontece porque o modelo 'Suavização Exponencial Simples'")
print("não captura padrões sazonais - ele apenas suaviza a tendência.")
print()
print("SOLUÇÃO: Usar um modelo que capture sazonalidade, como:")
print("  - Holt-Winters (Suavização Exponencial Tripla)")
print("  - SARIMA (com componente sazonal)")
print("  - Prophet (Facebook)")
