# -*- coding: utf-8 -*-
"""
Teste de Consistencia entre Granularidades
Valida que semanal e mensal produzem demandas proporcionais aos dias
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.demand_calculator import DemandCalculator
import numpy as np
from datetime import date, timedelta

def gerar_historico_diario(dias=730, demanda_base=100, ruido=10):
    """Gera historico diario simulado (2 anos)"""
    np.random.seed(42)
    historico = []
    for i in range(dias):
        # Adicionar sazonalidade semanal (mais vendas no fim de semana)
        dia_semana = i % 7
        fator_semanal = 1.2 if dia_semana >= 5 else 1.0  # Sabado/Domingo

        # Adicionar sazonalidade mensal leve
        dia_mes = i % 30
        fator_mensal = 1.1 if dia_mes < 5 else 1.0  # Inicio do mes

        demanda = demanda_base * fator_semanal * fator_mensal + np.random.normal(0, ruido)
        historico.append(max(0, demanda))

    return historico


def calcular_dias_periodo(granularidade, inicio, fim):
    """Calcula numero de dias em um periodo"""
    return (fim - inicio).days + 1


def testar_consistencia():
    """Testa se as granularidades sao consistentes"""
    print('=' * 70)
    print('TESTE DE CONSISTENCIA ENTRE GRANULARIDADES')
    print('=' * 70)

    # Gerar historico diario (2 anos)
    historico_diario = gerar_historico_diario(730, demanda_base=100)

    print(f'\nHistorico gerado: {len(historico_diario)} dias')
    print(f'Media diaria: {np.mean(historico_diario):.2f}')
    print(f'Total 2 anos: {sum(historico_diario):.2f}')

    # Definir periodos para teste
    # Mensal: Jan-Jun 2026 = 181 dias
    # Semanal: Sem 1-31 2026 = 217 dias

    dias_mensal = 181
    dias_semanal = 217

    print(f'\n' + '-' * 50)
    print('TESTE 1: Calculo Unificado')
    print('-' * 50)

    # Calcular usando metodo unificado
    demanda_mensal, desvio_mensal, meta_mensal = DemandCalculator.calcular_demanda_diaria_unificada(
        vendas_diarias=historico_diario,
        dias_periodo=dias_mensal,
        granularidade_exibicao='mensal'
    )

    demanda_semanal, desvio_semanal, meta_semanal = DemandCalculator.calcular_demanda_diaria_unificada(
        vendas_diarias=historico_diario,
        dias_periodo=dias_semanal,
        granularidade_exibicao='semanal'
    )

    print(f'\nMENSAL (Jan-Jun, {dias_mensal} dias):')
    print(f'  Demanda total: {demanda_mensal:,.2f}')
    print(f'  Demanda diaria base: {meta_mensal.get("demanda_diaria_base", 0):.2f}')
    print(f'  Metodo: {meta_mensal.get("metodo_usado", "?")}')

    print(f'\nSEMANAL (Sem 1-31, {dias_semanal} dias):')
    print(f'  Demanda total: {demanda_semanal:,.2f}')
    print(f'  Demanda diaria base: {meta_semanal.get("demanda_diaria_base", 0):.2f}')
    print(f'  Metodo: {meta_semanal.get("metodo_usado", "?")}')

    # Verificar proporcionalidade
    proporcao_dias = dias_semanal / dias_mensal
    proporcao_demanda = demanda_semanal / demanda_mensal if demanda_mensal > 0 else 0

    print(f'\nPROPORCAO:')
    print(f'  Dias (semanal/mensal): {proporcao_dias:.4f}')
    print(f'  Demanda (semanal/mensal): {proporcao_demanda:.4f}')
    print(f'  Diferenca: {abs(proporcao_demanda - proporcao_dias) * 100:.2f}%')

    # Validar consistencia
    resultado = DemandCalculator.validar_consistencia_granularidades(
        demanda_mensal=demanda_mensal,
        dias_mensal=dias_mensal,
        demanda_semanal=demanda_semanal,
        dias_semanal=dias_semanal
    )

    print(f'\n' + '-' * 50)
    print('VALIDACAO DE CONSISTENCIA')
    print('-' * 50)
    print(f'  Consistente: {"SIM" if resultado["consistente"] else "NAO"}')
    print(f'  Demanda diaria (via mensal): {resultado["demanda_diaria_mensal"]:.2f}')
    print(f'  Demanda diaria (via semanal): {resultado["demanda_diaria_semanal"]:.2f}')
    print(f'  Diferenca: {resultado["diferenca_pct"]:.2f}%')

    if not resultado['consistente']:
        print(f'\n  ALERTA: {resultado.get("alerta", "")}')

    print(f'\n' + '-' * 50)
    print('TESTE 2: Comparacao com Metodo Tradicional')
    print('-' * 50)

    # Agregar para mensal (30 dias por mes, ~24 meses)
    historico_mensal = []
    for i in range(0, len(historico_diario), 30):
        mes = sum(historico_diario[i:i+30])
        historico_mensal.append(mes)

    # Agregar para semanal (7 dias por semana, ~104 semanas)
    historico_semanal = []
    for i in range(0, len(historico_diario), 7):
        semana = sum(historico_diario[i:i+7])
        historico_semanal.append(semana)

    print(f'\nHistorico agregado:')
    print(f'  Mensal: {len(historico_mensal)} meses, media: {np.mean(historico_mensal):.2f}/mes')
    print(f'  Semanal: {len(historico_semanal)} semanas, media: {np.mean(historico_semanal):.2f}/semana')

    # Calcular usando metodo tradicional (cada granularidade separada)
    demanda_trad_mensal, _, meta_trad_mensal = DemandCalculator.calcular_demanda_adaptativa(
        historico_mensal, granularidade='mensal'
    )

    demanda_trad_semanal, _, meta_trad_semanal = DemandCalculator.calcular_demanda_adaptativa(
        historico_semanal, granularidade='semanal'
    )

    # Calcular totais para os periodos
    total_trad_mensal = demanda_trad_mensal * 6  # 6 meses
    total_trad_semanal = demanda_trad_semanal * 31  # 31 semanas

    print(f'\nMetodo tradicional (granularidade separada):')
    print(f'  Mensal: {demanda_trad_mensal:.2f}/mes x 6 = {total_trad_mensal:,.2f}')
    print(f'  Semanal: {demanda_trad_semanal:.2f}/sem x 31 = {total_trad_semanal:,.2f}')

    proporcao_trad = total_trad_semanal / total_trad_mensal if total_trad_mensal > 0 else 0

    print(f'\n  Proporcao tradicional: {proporcao_trad:.4f} (esperado: {proporcao_dias:.4f})')
    print(f'  Diferenca do esperado: {(proporcao_trad - proporcao_dias) * 100:+.2f}%')

    # Converter para demanda diaria equivalente
    diaria_via_mensal_trad = total_trad_mensal / dias_mensal
    diaria_via_semanal_trad = total_trad_semanal / dias_semanal

    print(f'\n  Demanda diaria via mensal (trad): {diaria_via_mensal_trad:.2f}')
    print(f'  Demanda diaria via semanal (trad): {diaria_via_semanal_trad:.2f}')
    print(f'  Diferenca: {abs(diaria_via_semanal_trad - diaria_via_mensal_trad) / diaria_via_mensal_trad * 100:.2f}%')

    print(f'\n' + '=' * 70)
    print('RESUMO')
    print('=' * 70)
    print(f'''
METODO UNIFICADO (base diaria):
  - Demanda diaria: {meta_mensal.get("demanda_diaria_base", 0):.2f}
  - Mensal ({dias_mensal}d): {demanda_mensal:,.2f}
  - Semanal ({dias_semanal}d): {demanda_semanal:,.2f}
  - Proporcao: {proporcao_demanda:.4f} (esperado: {proporcao_dias:.4f})
  - CONSISTENTE: {"SIM" if resultado["consistente"] else "NAO"}

METODO TRADICIONAL (granularidade separada):
  - Mensal ({dias_mensal}d): {total_trad_mensal:,.2f}
  - Semanal ({dias_semanal}d): {total_trad_semanal:,.2f}
  - Proporcao: {proporcao_trad:.4f} (esperado: {proporcao_dias:.4f})
  - Diferenca do esperado: {(proporcao_trad - proporcao_dias) * 100:+.2f}%

CONCLUSAO:
  O metodo UNIFICADO garante que as previsoes semanal e mensal sejam
  PROPORCIONAIS aos dias do periodo, eliminando discrepancias.
''')

    # Verificar se teste passou
    if resultado['consistente']:
        print('TESTE PASSOU: Granularidades sao consistentes!')
    else:
        print('TESTE FALHOU: Granularidades nao sao consistentes!')

    print('=' * 70)


if __name__ == '__main__':
    testar_consistencia()
