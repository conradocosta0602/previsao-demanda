# -*- coding: utf-8 -*-
"""
Teste: Validar detecção de outliers na série semanal
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
import numpy as np
from core.outlier_detector import auto_clean_outliers

print("=" * 80)
print("   TESTE: DETECÇÃO DE OUTLIERS NA SÉRIE SEMANAL")
print("=" * 80)
print()

# Conectar ao banco
conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)

query = """
    WITH dados_diarios AS (
        SELECT
            h.data,
            SUM(h.qtd_venda) as qtd_venda
        FROM historico_vendas_diario h
        WHERE h.data >= CURRENT_DATE - INTERVAL '2 years'
        GROUP BY h.data
    )
    SELECT
        DATE_TRUNC('week', data)::date as data,
        SUM(qtd_venda) as qtd_venda
    FROM dados_diarios
    GROUP BY DATE_TRUNC('week', data)
    ORDER BY DATE_TRUNC('week', data)
"""

cursor = conn.cursor()
cursor.execute(query)
dados = cursor.fetchall()

print(f"📊 Série histórica semanal: {len(dados)} períodos")
print()

# Extrair série temporal
serie = [float(d[1]) for d in dados]
datas = [d[0] for d in dados]

print("Primeiros 5 valores:")
for i in range(min(5, len(serie))):
    print(f"   {datas[i]}: {serie[i]:,.0f}")
print()

print("Últimos 5 valores:")
for i in range(max(0, len(serie)-5), len(serie)):
    semana_ano = datas[i].isocalendar()[1]
    print(f"   S{semana_ano:>2} ({datas[i]}): {serie[i]:>10,.0f}")
print()

# Estatísticas básicas
print(f"Média: {np.mean(serie):,.0f}")
print(f"Mediana: {np.median(serie):,.0f}")
print(f"Min: {np.min(serie):,.0f}")
print(f"Max: {np.max(serie):,.0f}")
print()

# Executar detector de outliers
print("=" * 80)
print("🔍 EXECUTANDO DETECTOR DE OUTLIERS")
print("=" * 80)
print()

resultado = auto_clean_outliers(serie)

print(f"Método usado: {resultado['method_used']}")
print(f"Tratamento: {resultado['treatment']}")
print(f"Outliers detectados: {resultado['outliers_count']}")
print(f"Razão: {resultado['reason']}")
print(f"Confiança: {resultado['confidence']:.2f}")
print()

if resultado['outliers_count'] > 0:
    print(f"📍 OUTLIERS ENCONTRADOS ({resultado['outliers_count']}):")
    print()

    outlier_indices = resultado['outliers_detected']
    original_values = resultado['original_values']
    replaced_values = resultado['replaced_values']

    for i, idx in enumerate(outlier_indices):
        data_outlier = datas[idx]
        semana_ano = data_outlier.isocalendar()[1]
        valor_original = original_values[i]
        valor_substituido = replaced_values[i] if i < len(replaced_values) else "REMOVIDO"

        # Calcular desvio em %
        media_serie = np.mean(serie)
        desvio_pct = ((valor_original / media_serie) - 1) * 100

        print(f"   Índice {idx:>3}: S{semana_ano:>2} ({data_outlier})")
        print(f"      Original:     {valor_original:>10,.0f}  ({desvio_pct:+6.1f}% da média)")
        if isinstance(valor_substituido, str):
            print(f"      Tratamento:   {valor_substituido}")
        else:
            print(f"      Substituído:  {valor_substituido:>10,.0f}")
        print()

    # Verificar se o outlier crítico de jan/2026 foi detectado
    ultimo_idx = len(serie) - 1
    if ultimo_idx in outlier_indices:
        print("✅ OUTLIER CRÍTICO DE JANEIRO/2026 FOI DETECTADO!")
    else:
        print("⚠️  OUTLIER CRÍTICO DE JANEIRO/2026 NÃO FOI DETECTADO!")
        print(f"   Valor: {serie[ultimo_idx]:,.0f}")
        print(f"   Índice: {ultimo_idx}")
        print()

else:
    print("✅ Nenhum outlier detectado")
    print()
    print("⚠️  MAS SABEMOS QUE HÁ UM OUTLIER EXTREMO (28,569 na última semana)!")
    print("   O detector pode não estar funcionando corretamente.")

# Mostrar características da série
print()
print("=" * 80)
print("📈 CARACTERÍSTICAS DA SÉRIE")
print("=" * 80)
print()

chars = resultado.get('characteristics', {})
if chars:
    print(f"CV (coef. variação): {chars.get('cv', 0):.3f}")
    print(f"Skewness (assimetria): {chars.get('skewness', 0):.3f}")
    print(f"Kurtosis (curtose): {chars.get('kurtosis', 0):.3f}")
    print(f"Zeros: {chars.get('zeros_pct', 0):.1f}%")
    print(f"Amplitude relativa: {chars.get('relative_range', 0):.3f}")

conn.close()

print()
print("=" * 80)
