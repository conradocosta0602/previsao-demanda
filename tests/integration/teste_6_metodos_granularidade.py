# -*- coding: utf-8 -*-
"""
Teste dos 6 Metodos Inteligentes para Todas as Granularidades
Valida a implementacao do DemandCalculator.calcular_demanda_adaptativa
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.demand_calculator import DemandCalculator
import numpy as np

def gerar_serie_teste(padrao, tamanho):
    """Gera series de teste com diferentes padroes"""
    np.random.seed(42)

    if padrao == 'estavel':
        # Demanda estavel com pouca variacao
        base = 100
        return [base + np.random.normal(0, 10) for _ in range(tamanho)]

    elif padrao == 'tendencia_alta':
        # Demanda crescente
        return [50 + i * 5 + np.random.normal(0, 5) for i in range(tamanho)]

    elif padrao == 'tendencia_baixa':
        # Demanda decrescente
        return [200 - i * 3 + np.random.normal(0, 5) for i in range(tamanho)]

    elif padrao == 'sazonal':
        # Demanda com sazonalidade
        base = 100
        return [base + 30 * np.sin(2 * np.pi * i / 12) + np.random.normal(0, 10) for i in range(tamanho)]

    elif padrao == 'intermitente':
        # Demanda intermitente (muitos zeros)
        serie = []
        for _ in range(tamanho):
            if np.random.random() > 0.6:  # 40% chance de venda
                serie.append(np.random.randint(10, 50))
            else:
                serie.append(0)
        return serie

    elif padrao == 'alta_variabilidade':
        # Alta variabilidade
        return [np.random.randint(10, 200) for _ in range(tamanho)]

    return [100] * tamanho


def testar_series_curtas():
    """Testa tratamento de series curtas"""
    print('\n' + '='*70)
    print('TESTE 1: SERIES CURTAS')
    print('='*70)

    tamanhos = [1, 2, 3, 5, 8, 12, 24]

    for tamanho in tamanhos:
        serie = gerar_serie_teste('estavel', tamanho)[:tamanho]

        # Testar para cada granularidade
        for granularidade in ['mensal', 'semanal', 'diario']:
            demanda, desvio, metadata = DemandCalculator.calcular_demanda_adaptativa(
                serie, granularidade=granularidade, media_cluster=80
            )

            print(f'\n{granularidade.upper()} - {tamanho} pontos:')
            print(f'  Categoria: {metadata.get("categoria_serie", "?")}')
            print(f'  Metodo: {metadata.get("metodo_usado", "?")}')
            print(f'  Confianca: {metadata.get("confianca", "?")}')
            print(f'  Demanda: {demanda:.2f}, Desvio: {desvio:.2f}')
            print(f'  Fator Seguranca: {metadata.get("fator_seguranca_recomendado", 1.0)}')


def testar_selecao_metodo():
    """Testa se o metodo correto e selecionado para cada padrao"""
    print('\n' + '='*70)
    print('TESTE 2: SELECAO AUTOMATICA DE METODO')
    print('='*70)

    padroes = ['estavel', 'tendencia_alta', 'tendencia_baixa', 'sazonal', 'intermitente', 'alta_variabilidade']

    for padrao in padroes:
        # Serie longa (24 pontos mensais)
        serie = gerar_serie_teste(padrao, 24)

        demanda, desvio, metadata = DemandCalculator.calcular_demanda_adaptativa(
            serie, granularidade='mensal'
        )

        print(f'\nPadrao: {padrao.upper()}')
        print(f'  Metodo Selecionado: {metadata.get("metodo_usado", "?")}')
        print(f'  Categoria Serie: {metadata.get("categoria_serie", "?")}')
        print(f'  Confianca: {metadata.get("confianca", "?")}')
        print(f'  Demanda Prevista: {demanda:.2f}')

        # Mostrar classificacao se disponivel
        classif = metadata.get('classificacao', {})
        if classif:
            print(f'  CV: {classif.get("cv", "?")}')
            print(f'  Zeros%: {classif.get("zeros_pct", "?")}')
            print(f'  Tendencia: {classif.get("tendencia", "?")}')
            print(f'  Sazonalidade: {classif.get("sazonalidade", "?")}')


def testar_comparacao_granularidades():
    """Compara resultados entre granularidades"""
    print('\n' + '='*70)
    print('TESTE 3: COMPARACAO ENTRE GRANULARIDADES')
    print('='*70)

    # Serie base mensal (24 meses)
    serie_mensal = gerar_serie_teste('estavel', 24)

    # Converter para semanal (~104 semanas)
    serie_semanal = []
    for mes in serie_mensal:
        # 4 semanas por mes, distribuir proporcionalmente
        for _ in range(4):
            serie_semanal.append(mes / 4 + np.random.normal(0, mes/20))

    # Converter para diario (~730 dias)
    serie_diaria = []
    for mes in serie_mensal:
        # 30 dias por mes, distribuir proporcionalmente
        for _ in range(30):
            serie_diaria.append(mes / 30 + np.random.normal(0, mes/100))

    print('\nMesma demanda base em diferentes granularidades:')

    for nome, serie, granularidade in [
        ('MENSAL (24 meses)', serie_mensal, 'mensal'),
        ('SEMANAL (104 semanas)', serie_semanal, 'semanal'),
        ('DIARIO (730 dias)', serie_diaria, 'diario')
    ]:
        demanda, desvio, metadata = DemandCalculator.calcular_demanda_adaptativa(
            serie, granularidade=granularidade
        )

        # Normalizar para comparacao (demanda diaria equivalente)
        if granularidade == 'mensal':
            demanda_diaria_equiv = demanda / 30
        elif granularidade == 'semanal':
            demanda_diaria_equiv = demanda / 7
        else:
            demanda_diaria_equiv = demanda

        print(f'\n{nome}:')
        print(f'  Categoria: {metadata.get("categoria_serie", "?")}')
        print(f'  Metodo: {metadata.get("metodo_usado", "?")}')
        print(f'  Demanda (periodo): {demanda:.2f}')
        print(f'  Demanda diaria equiv: {demanda_diaria_equiv:.2f}')


def testar_prior_bayesiano():
    """Testa uso de prior bayesiano para series curtas"""
    print('\n' + '='*70)
    print('TESTE 4: PRIOR BAYESIANO')
    print('='*70)

    # Serie muito curta (2 pontos)
    serie_curta = [50, 60]

    # Sem prior
    demanda1, _, meta1 = DemandCalculator.calcular_demanda_adaptativa(
        serie_curta, granularidade='mensal', media_cluster=None
    )

    # Com prior (media do cluster = 100)
    demanda2, _, meta2 = DemandCalculator.calcular_demanda_adaptativa(
        serie_curta, granularidade='mensal', media_cluster=100
    )

    # Com prior mais alto (media do cluster = 200)
    demanda3, _, meta3 = DemandCalculator.calcular_demanda_adaptativa(
        serie_curta, granularidade='mensal', media_cluster=200
    )

    print('\nSerie curta [50, 60]:')
    print(f'  Sem prior:           Demanda = {demanda1:.2f}, Metodo = {meta1.get("metodo_usado", "?")}')
    print(f'  Com prior (100):     Demanda = {demanda2:.2f}, Metodo = {meta2.get("metodo_usado", "?")}')
    print(f'  Com prior (200):     Demanda = {demanda3:.2f}, Metodo = {meta3.get("metodo_usado", "?")}')


def main():
    print('='*70)
    print('VALIDACAO DOS 6 METODOS INTELIGENTES')
    print('Com tratamento para series curtas')
    print('='*70)

    testar_series_curtas()
    testar_selecao_metodo()
    testar_comparacao_granularidades()
    testar_prior_bayesiano()

    print('\n' + '='*70)
    print('TESTES CONCLUIDOS!')
    print('='*70)


if __name__ == '__main__':
    main()
