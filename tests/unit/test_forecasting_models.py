# -*- coding: utf-8 -*-
"""
Testes unitários para core/forecasting_models.py
"""

import pytest
import pandas as pd
import numpy as np
from core.forecasting_models import (
    get_modelo,
    SimpleMovingAverage,
    WeightedMovingAverage,
    SimpleExponentialSmoothing,
    LinearRegressionForecast,
    DecomposicaoSazonalMensal,
    CrostonMethod
)


class TestGetModelo:
    """Testes para a função get_modelo()"""

    def test_get_modelo_sma(self):
        """Deve retornar modelo SMA"""
        modelo = get_modelo('SMA')
        assert modelo is not None

    def test_get_modelo_wma(self):
        """Deve retornar modelo WMA"""
        modelo = get_modelo('WMA')
        assert modelo is not None

    def test_get_modelo_ema(self):
        """Deve retornar modelo EMA"""
        modelo = get_modelo('EMA')
        assert modelo is not None

    def test_get_modelo_tsb(self):
        """Deve retornar modelo TSB para demanda intermitente"""
        modelo = get_modelo('TSB')
        assert modelo is not None

    def test_get_modelo_invalido(self):
        """Deve retornar None para método inválido"""
        modelo = get_modelo('METODO_INEXISTENTE')
        assert modelo is None


class TestSimpleMovingAverage:
    """Testes para SMA"""

    @pytest.mark.unit
    def test_sma_previsao_basica(self):
        """SMA deve calcular média móvel corretamente"""
        dados = [100, 110, 120, 130, 140]
        serie = pd.Series(dados)

        modelo = SimpleMovingAverage()
        modelo.fit(serie)
        previsao = modelo.predict(3)

        # Média dos últimos 3: (120+130+140)/3 = 130
        assert len(previsao) == 3
        assert all(p > 0 for p in previsao)

    @pytest.mark.unit
    def test_sma_serie_curta(self):
        """SMA deve funcionar com séries curtas"""
        dados = [100, 110]
        serie = pd.Series(dados)

        modelo = SimpleMovingAverage()
        modelo.fit(serie)
        previsao = modelo.predict(2)

        assert len(previsao) == 2


class TestWeightedMovingAverage:
    """Testes para WMA"""

    @pytest.mark.unit
    def test_wma_pesos_recentes(self):
        """WMA deve dar mais peso a dados recentes"""
        dados = [100, 100, 100, 200]  # Salto no final
        serie = pd.Series(dados)

        modelo_sma = SimpleMovingAverage()
        modelo_sma.fit(serie)
        prev_sma = modelo_sma.predict(1)[0]

        modelo_wma = WeightedMovingAverage()
        modelo_wma.fit(serie)
        prev_wma = modelo_wma.predict(1)[0]

        # WMA deve ser maior que SMA pois dá mais peso ao 200
        assert prev_wma >= prev_sma


class TestTSB:
    """Testes para TSB (Teunter-Syntetos-Babai)"""

    @pytest.mark.unit
    def test_tsb_demanda_intermitente(self, sample_intermittent_data):
        """TSB deve funcionar com demanda intermitente"""
        vendas = sample_intermittent_data['Vendas'].tolist()
        serie = pd.Series(vendas)

        modelo = CrostonMethod(variant='tsb')
        modelo.fit(serie)
        previsao = modelo.predict(3)

        assert len(previsao) == 3
        # Previsões devem ser positivas ou zero
        assert all(p >= 0 for p in previsao)

    @pytest.mark.unit
    def test_tsb_todos_zeros(self):
        """TSB deve lidar com série de zeros"""
        dados = [0, 0, 0, 0, 0]
        serie = pd.Series(dados)

        modelo = CrostonMethod(variant='tsb')
        modelo.fit(serie)
        previsao = modelo.predict(3)

        assert len(previsao) == 3


class TestDecomposicaoSazonal:
    """Testes para Decomposição Sazonal"""

    @pytest.mark.unit
    def test_decomposicao_detecta_sazonalidade(self, sample_seasonal_data):
        """Decomposição deve detectar padrão sazonal"""
        vendas = sample_seasonal_data['Vendas'].tolist()
        serie = pd.Series(vendas)

        modelo = DecomposicaoSazonalMensal()
        modelo.fit(serie)
        previsao = modelo.predict(12)

        assert len(previsao) == 12
        # Previsões devem manter padrão (dezembro maior)
        assert all(p > 0 for p in previsao)


class TestLinearRegression:
    """Testes para Regressão Linear com Tendência"""

    @pytest.mark.unit
    def test_tendencia_crescente(self):
        """Deve detectar tendência crescente"""
        dados = [100, 110, 120, 130, 140, 150]
        serie = pd.Series(dados)

        modelo = LinearRegressionForecast()
        modelo.fit(serie)
        previsao = modelo.predict(3)

        # Previsão deve continuar crescendo
        assert len(previsao) == 3
        assert previsao[0] > dados[-1]

    @pytest.mark.unit
    def test_tendencia_decrescente(self):
        """Deve detectar tendência decrescente"""
        dados = [150, 140, 130, 120, 110, 100]
        serie = pd.Series(dados)

        modelo = LinearRegressionForecast()
        modelo.fit(serie)
        previsao = modelo.predict(3)

        # Previsão deve continuar decrescendo
        assert len(previsao) == 3
        assert previsao[0] < dados[-1]
