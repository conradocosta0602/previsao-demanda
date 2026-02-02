# -*- coding: utf-8 -*-
"""
Diagnóstico: Diferenças entre granularidades (Mensal, Semanal, Diário)
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime, date

BASE_URL = 'http://localhost:5001'

print("=" * 100)
print("DIAGNÓSTICO: DIFERENÇAS ENTRE GRANULARIDADES")
print("Período: Janeiro/2026, Fevereiro/2026, Março/2026")
print("=" * 100)
print()

# ============================================================
# 1. CONSULTA MENSAL
# ============================================================
print("1. GRANULARIDADE MENSAL")
print("-" * 100)

dados_mensal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'mensal',
    'primeiro_mes_previsao': 1,
    'ano_primeiro_mes': 2026,
    'mes_destino': 3,
    'ano_destino': 2026,
    'granularidade': 'mensal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_mensal,
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
    print(f"Períodos: {len(datas)}")
    total_mensal = sum(valores)
    print(f"Total: {total_mensal:,.0f}")
    print()
    for i, (d, v) in enumerate(zip(datas, valores)):
        print(f"  {d}: {v:,.0f}")
else:
    print(f"Erro: {response.status_code}")
    total_mensal = 0

print()

# ============================================================
# 2. CONSULTA SEMANAL
# ============================================================
print("2. GRANULARIDADE SEMANAL")
print("-" * 100)

# Semana 1/2026 começa em 29/12/2025, Semana 13/2026 termina em 29/03/2026
# Para cobrir Jan, Fev, Mar precisamos das semanas 1 a 13 aproximadamente
dados_semanal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'semanal',
    'semana_inicio': 1,
    'ano_semana_inicio': 2026,
    'semana_fim': 13,
    'ano_semana_fim': 2026,
    'granularidade': 'semanal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_semanal,
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
    print(f"Períodos: {len(datas)}")
    total_semanal = sum(valores)
    print(f"Total: {total_semanal:,.0f}")
    print()

    # Agrupar por mês para comparação
    por_mes = {}
    for d, v in zip(datas, valores):
        dt = datetime.strptime(d, '%Y-%m-%d')
        mes_key = f"{dt.year}-{dt.month:02d}"
        if mes_key not in por_mes:
            por_mes[mes_key] = {'dias': [], 'total': 0}
        por_mes[mes_key]['dias'].append((d, v))
        por_mes[mes_key]['total'] += v

    for d, v in zip(datas, valores):
        dt = datetime.strptime(d, '%Y-%m-%d')
        iso_year, iso_week, _ = dt.isocalendar()
        print(f"  {d} (S{iso_week}/{iso_year}): {v:,.0f}")

    print()
    print("  Agrupado por mês:")
    for mes, info in sorted(por_mes.items()):
        print(f"    {mes}: {info['total']:,.0f} ({len(info['dias'])} semanas)")
else:
    print(f"Erro: {response.status_code}")
    total_semanal = 0

print()

# ============================================================
# 3. CONSULTA DIÁRIA
# ============================================================
print("3. GRANULARIDADE DIÁRIA")
print("-" * 100)

dados_diario = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'tipo_periodo': 'diario',
    'data_inicio': '2026-01-01',
    'data_fim': '2026-03-31',
    'granularidade': 'diario'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_diario,
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
    print(f"Períodos: {len(datas)}")
    total_diario = sum(valores)
    print(f"Total: {total_diario:,.0f}")
    print()

    # Agrupar por mês
    por_mes = {}
    for d, v in zip(datas, valores):
        dt = datetime.strptime(d, '%Y-%m-%d')
        mes_key = f"{dt.year}-{dt.month:02d}"
        if mes_key not in por_mes:
            por_mes[mes_key] = {'dias': 0, 'total': 0}
        por_mes[mes_key]['dias'] += 1
        por_mes[mes_key]['total'] += v

    print("  Agrupado por mês:")
    for mes, info in sorted(por_mes.items()):
        print(f"    {mes}: {info['total']:,.0f} ({info['dias']} dias)")

    print()
    print("  Primeiros 10 dias:")
    for i in range(min(10, len(datas))):
        print(f"    {datas[i]}: {valores[i]:,.0f}")
else:
    print(f"Erro: {response.status_code}")
    total_diario = 0

print()

# ============================================================
# 4. ANÁLISE COMPARATIVA
# ============================================================
print("=" * 100)
print("ANÁLISE COMPARATIVA")
print("=" * 100)
print()
print(f"Total MENSAL:  {total_mensal:>15,.0f}")
print(f"Total SEMANAL: {total_semanal:>15,.0f}")
print(f"Total DIÁRIO:  {total_diario:>15,.0f}")
print()
print(f"Diferença Mensal vs Semanal: {total_mensal - total_semanal:>+15,.0f} ({(total_mensal - total_semanal) / total_mensal * 100:+.1f}%)")
print(f"Diferença Mensal vs Diário:  {total_mensal - total_diario:>+15,.0f} ({(total_mensal - total_diario) / total_mensal * 100:+.1f}%)")
print(f"Diferença Semanal vs Diário: {total_semanal - total_diario:>+15,.0f} ({(total_semanal - total_diario) / total_semanal * 100:+.1f}%)" if total_semanal > 0 else "")
print()

# ============================================================
# 5. VERIFICAR PERÍODO EXATO
# ============================================================
print("=" * 100)
print("VERIFICAÇÃO DE PERÍODOS")
print("=" * 100)
print()
print("MENSAL: Jan/2026 a Mar/2026")
print("  - Janeiro: 01/01/2026 a 31/01/2026 (31 dias)")
print("  - Fevereiro: 01/02/2026 a 28/02/2026 (28 dias)")
print("  - Março: 01/03/2026 a 31/03/2026 (31 dias)")
print("  - TOTAL: 90 dias")
print()

# Calcular período semanal
from datetime import timedelta
s1_2026 = date(2025, 12, 29)  # Segunda-feira da semana 1/2026
s13_2026 = date(2026, 3, 23)  # Segunda-feira da semana 13/2026
s13_fim = s13_2026 + timedelta(days=6)  # Domingo da semana 13

print(f"SEMANAL: S1/2026 a S13/2026")
print(f"  - Início: {s1_2026} (segunda-feira da S1)")
print(f"  - Fim: {s13_fim} (domingo da S13)")
print(f"  - Inclui: 29/12/2025 a 29/03/2026")
print(f"  - TOTAL: 13 semanas = 91 dias")
print()

print("DIÁRIO: 01/01/2026 a 31/03/2026")
print("  - TOTAL: 90 dias")
print()

print("=" * 100)
print("POSSÍVEIS CAUSAS DAS DIFERENÇAS:")
print("=" * 100)
print()
print("1. MODELOS DIFERENTES: Cada granularidade pode selecionar um modelo diferente")
print("   - O modelo que performa melhor em dados mensais pode ser diferente do semanal/diário")
print()
print("2. PERÍODO DIFERENTE:")
print("   - Semanal S1/2026 começa em 29/12/2025 (inclui dias de 2025)")
print("   - Diário começa em 01/01/2026")
print("   - Isso causa 3 dias extras no semanal")
print()
print("3. AGREGAÇÃO DOS DADOS:")
print("   - Dados mensais são agregados de forma diferente dos semanais/diários")
print("   - A soma de semanas pode não corresponder exatamente aos meses")
print()
print("4. SAZONALIDADE:")
print("   - Modelos capturam padrões sazonais diferentes em cada granularidade")
print()
