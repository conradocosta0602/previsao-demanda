# -*- coding: utf-8 -*-
"""
Validar: Previsão semanal - comparação detalhada com histórico
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
from datetime import datetime, timedelta
import psycopg2

print("=" * 80)
print("   VALIDAÇÃO DETALHADA: PREVISÃO SEMANAL")
print("=" * 80)
print()

# Conectar ao banco para obter dados históricos
conn = psycopg2.connect(
    dbname="demanda_reabastecimento",
    user="postgres",
    password="FerreiraCost@01",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

# Buscar dados por semana para 2024 e 2025
print("HISTÓRICO SEMANAL DO BANCO (2024-2025):")
print("-" * 80)

# Semanas específicas que o usuário mencionou
semanas_interesse = [3, 9, 10, 11]

for semana in semanas_interesse:
    print(f"\nSemana {semana}:")

    # 2024
    cursor.execute("""
        SELECT
            DATE_TRUNC('week', data)::date as inicio_semana,
            EXTRACT(WEEK FROM data) as semana,
            SUM(qtd_venda) as total
        FROM historico_vendas_diario
        WHERE EXTRACT(YEAR FROM data) = 2024
          AND EXTRACT(WEEK FROM data) = %s
        GROUP BY DATE_TRUNC('week', data), EXTRACT(WEEK FROM data)
        ORDER BY inicio_semana
    """, (semana,))

    for row in cursor.fetchall():
        print(f"  S{semana}/24: {row[2]:,.0f} ({row[0]})")

    # 2025
    cursor.execute("""
        SELECT
            DATE_TRUNC('week', data)::date as inicio_semana,
            EXTRACT(WEEK FROM data) as semana,
            SUM(qtd_venda) as total
        FROM historico_vendas_diario
        WHERE EXTRACT(YEAR FROM data) = 2025
          AND EXTRACT(WEEK FROM data) = %s
        GROUP BY DATE_TRUNC('week', data), EXTRACT(WEEK FROM data)
        ORDER BY inicio_semana
    """, (semana,))

    for row in cursor.fetchall():
        print(f"  S{semana}/25: {row[2]:,.0f} ({row[0]})")

conn.close()

# Agora buscar a previsão
print()
print("=" * 80)
print("PREVISÃO DA API:")
print("=" * 80)

BASE_URL = 'http://localhost:5001'

dados = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 12,
    'granularidade': 'semanal'
}

try:
    response = requests.post(
        f'{BASE_URL}/api/gerar_previsao_banco',
        json=dados,
        headers={'Content-Type': 'application/json'},
        timeout=180
    )

    if response.status_code == 200:
        resultado = response.json()

        # Ano anterior
        ano_anterior = resultado.get('ano_anterior', {})
        datas_ano_anterior = ano_anterior.get('datas', [])
        valores_ano_anterior = ano_anterior.get('valores', [])

        print("\nDados 'ano_anterior' retornados pela API:")
        print("-" * 80)

        # Mostrar apenas semanas de interesse
        for semana in semanas_interesse:
            for i, data in enumerate(datas_ano_anterior):
                dt = datetime.strptime(data, '%Y-%m-%d')
                if dt.isocalendar()[1] == semana:
                    print(f"  S{semana}: {valores_ano_anterior[i]:,.0f} ({data}) - ano {dt.year}")
                    break

        # Previsão
        melhor_modelo = resultado.get('melhor_modelo')
        previsoes = resultado.get('modelos', {})

        if melhor_modelo and melhor_modelo in previsoes:
            modelo_data = previsoes[melhor_modelo]
            futuro = modelo_data.get('futuro', {})

            datas_futuro = futuro.get('datas', [])
            valores_futuro = futuro.get('valores', [])

            print(f"\nPrevisão do modelo {melhor_modelo}:")
            print("-" * 80)

            for semana in semanas_interesse:
                for i, data in enumerate(datas_futuro):
                    dt = datetime.strptime(data, '%Y-%m-%d')
                    if dt.isocalendar()[1] == semana:
                        print(f"  S{semana}/26: {valores_futuro[i]:,.0f} ({data})")
                        break

        # Verificar estrutura completa das primeiras 12 semanas
        print()
        print("=" * 80)
        print("PRIMEIRAS 12 SEMANAS DA PREVISÃO:")
        print("=" * 80)

        if melhor_modelo and melhor_modelo in previsoes:
            for i in range(min(12, len(datas_futuro))):
                dt = datetime.strptime(datas_futuro[i], '%Y-%m-%d')
                semana = dt.isocalendar()[1]
                print(f"  {i+1}. S{semana}/26: {valores_futuro[i]:,.0f} ({datas_futuro[i]})")

    else:
        print(f"Erro: {response.status_code}")
        print(response.text[:500])

except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
