# -*- coding: utf-8 -*-
"""
Análise: Fatores Sazonais Semanais
Verificar se fatores muito baixos estão causando queda na previsão
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from datetime import datetime, timedelta
import numpy as np

print("=" * 80)
print("   ANÁLISE: FATORES SAZONAIS SEMANAIS")
print("=" * 80)
print()

# Conectar ao banco
try:
    conn = psycopg2.connect(
        dbname="demanda_reabastecimento",
        user="postgres",
        password="FerreiraCost@01",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    print("✅ Conectado ao banco de dados")
    print()

    # Buscar dados históricos semanais
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
            DATE_TRUNC('week', data)::date as data_semana,
            SUM(qtd_venda) as qtd_venda
        FROM dados_diarios
        GROUP BY DATE_TRUNC('week', data)
        ORDER BY DATE_TRUNC('week', data)
    """

    cursor.execute(query)
    dados = cursor.fetchall()

    print(f"📊 Dados históricos: {len(dados)} semanas")
    print()

    # Calcular fatores sazonais por semana do ano (1-52)
    indices_sazonais = {}
    serie_completa = []

    for data_semana, qtd_venda in dados:
        semana_ano = data_semana.isocalendar()[1]  # 1-52/53

        if semana_ano not in indices_sazonais:
            indices_sazonais[semana_ano] = []

        indices_sazonais[semana_ano].append(float(qtd_venda))
        serie_completa.append(float(qtd_venda))

    # Calcular média geral e fatores sazonais
    media_geral = np.mean(serie_completa)
    fatores_sazonais = {}

    for semana, valores in indices_sazonais.items():
        fatores_sazonais[semana] = np.mean(valores) / media_geral

    print(f"🔢 Fatores sazonais calculados: {len(fatores_sazonais)} semanas")
    print(f"   Média geral: {media_geral:,.2f}")
    print(f"   Min fator: {min(fatores_sazonais.values()):.3f}")
    print(f"   Max fator: {max(fatores_sazonais.values()):.3f}")
    print()

    # Mostrar fatores sazonais ordenados
    print("=" * 80)
    print("📋 FATORES SAZONAIS POR SEMANA (ordenados por fator)")
    print("=" * 80)
    print()

    fatores_ordenados = sorted(fatores_sazonais.items(), key=lambda x: x[1])

    print("🔴 10 SEMANAS COM MENORES FATORES (maior redução):")
    for semana, fator in fatores_ordenados[:10]:
        n_observacoes = len(indices_sazonais[semana])
        media_semana = np.mean(indices_sazonais[semana])
        reducao = (1 - fator) * 100
        print(f"   S{semana:>2}: Fator={fator:.3f}  Redução={reducao:>5.1f}%  Média={media_semana:>10,.0f}  ({n_observacoes} obs)")

    print()
    print("🟢 10 SEMANAS COM MAIORES FATORES (maior aumento):")
    for semana, fator in fatores_ordenados[-10:]:
        n_observacoes = len(indices_sazonais[semana])
        media_semana = np.mean(indices_sazonais[semana])
        aumento = (fator - 1) * 100
        print(f"   S{semana:>2}: Fator={fator:.3f}  Aumento={aumento:>5.1f}%  Média={media_semana:>10,.0f}  ({n_observacoes} obs)")

    print()
    print("=" * 80)
    print("🔮 IMPACTO NA PREVISÃO (próximas 24 semanas)")
    print("=" * 80)
    print()

    # Simular impacto nos próximos 6 meses (24 semanas)
    hoje = datetime.now().date()
    # Achar a próxima segunda-feira
    dias_ate_segunda = (7 - hoje.weekday()) % 7
    if dias_ate_segunda == 0:
        dias_ate_segunda = 7
    proxima_segunda = hoje + timedelta(days=dias_ate_segunda)

    print(f"Período de previsão: {proxima_segunda} até {proxima_segunda + timedelta(weeks=23)}")
    print()

    fatores_previsao = []
    semanas_baixas = 0
    semanas_altas = 0

    for i in range(24):
        data_semana = proxima_segunda + timedelta(weeks=i)
        semana_ano = data_semana.isocalendar()[1]
        fator = fatores_sazonais.get(semana_ano, 1.0)
        fatores_previsao.append(fator)

        if fator < 0.85:
            semanas_baixas += 1
        elif fator > 1.15:
            semanas_altas += 1

    fator_medio_previsao = np.mean(fatores_previsao)
    fator_min_previsao = min(fatores_previsao)
    fator_max_previsao = max(fatores_previsao)

    print(f"Fator médio das 24 semanas de previsão: {fator_medio_previsao:.3f}")
    print(f"Fator mínimo: {fator_min_previsao:.3f}")
    print(f"Fator máximo: {fator_max_previsao:.3f}")
    print()

    print(f"Semanas com fator < 0.85 (baixa): {semanas_baixas}/24")
    print(f"Semanas com fator > 1.15 (alta):  {semanas_altas}/24")
    print()

    # DIAGNÓSTICO
    print("=" * 80)
    print("🩺 DIAGNÓSTICO")
    print("=" * 80)
    print()

    if fator_medio_previsao < 0.90:
        print("🔴 PROBLEMA CRÍTICO IDENTIFICADO!")
        print(f"   Fator médio das semanas de previsão ({fator_medio_previsao:.3f}) é MUITO BAIXO")
        print()
        print("   Isso significa que o período de previsão (próximos 6 meses)")
        print("   corresponde historicamente a um período de BAIXA demanda.")
        print()
        print("   🚨 Consequência: Previsão será reduzida em ~"
              f"{(1-fator_medio_previsao)*100:.1f}% devido aos fatores sazonais!")
        print()
        print("   ⚠️  ISSO EXPLICA POR QUE A PREVISÃO SEMANAL É METADE DA MENSAL!")
        print()
    elif fator_medio_previsao < 0.95:
        print("⚠️  ATENÇÃO: Fator médio abaixo de 0.95")
        print("   Período de previsão corresponde a semanas de demanda ligeiramente baixa")
    else:
        print("✅ Fatores sazonais equilibrados no período de previsão")

    print()
    print("💡 RECOMENDAÇÕES:")
    print()

    if fator_medio_previsao < 0.90:
        print("1. 🔧 CORREÇÃO NECESSÁRIA:")
        print("   - Fatores sazonais semanais estão distorcendo drasticamente a previsão")
        print("   - Possível solução: Normalizar fatores ou aplicar piso mínimo (ex: 0.85)")
        print("   - Ou: Usar sazonalidade mais suave (ex: trimestral em vez de semanal)")
        print()
        print("2. 📊 VALIDAÇÃO:")
        print("   - Verificar se dados históricos realmente têm essa sazonalidade forte")
        print("   - Comparar com dados de vendas reais de anos anteriores")
        print("   - Considerar eventos especiais que podem ter afetado o histórico")
    else:
        print("   - Comportamento normal para granularidade semanal")
        print("   - Diferenças de até 15% são aceitáveis vs mensal")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
