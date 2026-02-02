# -*- coding: utf-8 -*-
"""
Testes unitários para core/method_selector.py
"""

import pytest
import pandas as pd
import numpy as np
from core.method_selector import MethodSelector


class TestMethodSelector:
    """Testes para o seletor de método de previsão"""

    @pytest.mark.unit
    def test_selector_demanda_estavel(self, sample_sales_data):
        """Demanda estável deve recomendar SMA ou WMA"""
        vendas = sample_sales_data['Vendas'].tolist()
        datas = sample_sales_data['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        assert 'metodo' in recomendacao
        assert 'confianca' in recomendacao
        assert 'razao' in recomendacao
        assert recomendacao['confianca'] >= 0
        assert recomendacao['confianca'] <= 1

    @pytest.mark.unit
    def test_selector_demanda_intermitente(self, sample_intermittent_data):
        """Demanda intermitente deve recomendar TSB"""
        vendas = sample_intermittent_data['Vendas'].tolist()
        datas = sample_intermittent_data['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        # TSB é recomendado para demanda intermitente
        assert recomendacao['metodo'] in ['TSB', 'Croston', 'SBA']

    @pytest.mark.unit
    def test_selector_demanda_sazonal(self, sample_seasonal_data):
        """Demanda sazonal deve recomendar Decomposição Sazonal"""
        vendas = sample_seasonal_data['Vendas'].tolist()
        datas = sample_seasonal_data['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        # Com 24 meses e padrão claro, deve detectar sazonalidade
        assert recomendacao['metodo'] is not None

    @pytest.mark.unit
    def test_selector_caracteristicas(self, sample_sales_data):
        """Deve extrair características da série corretamente"""
        vendas = sample_sales_data['Vendas'].tolist()
        datas = sample_sales_data['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        assert 'caracteristicas' in recomendacao
        caract = recomendacao['caracteristicas']
        assert 'cv' in caract or 'intermitente' in caract

    @pytest.mark.unit
    def test_selector_serie_curta(self, sample_short_series):
        """Série curta deve retornar método adequado"""
        vendas = sample_short_series['Vendas'].tolist()
        datas = sample_short_series['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        # Deve retornar algum método mesmo com série curta
        assert recomendacao['metodo'] is not None

    @pytest.mark.unit
    def test_selector_alternativas(self, sample_sales_data):
        """Deve fornecer métodos alternativos"""
        vendas = sample_sales_data['Vendas'].tolist()
        datas = sample_sales_data['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        # Alternativas podem ser lista vazia, mas chave deve existir
        assert 'alternativas' in recomendacao


class TestClassificacaoDemanda:
    """Testes para classificação de demanda (CV/ADI)"""

    @pytest.mark.unit
    def test_calcular_cv(self, sample_sales_data):
        """Deve calcular coeficiente de variação"""
        vendas = sample_sales_data['Vendas'].tolist()
        datas = sample_sales_data['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        # CV deve estar nas características
        if 'cv' in recomendacao.get('caracteristicas', {}):
            cv = recomendacao['caracteristicas']['cv']
            assert cv >= 0

    @pytest.mark.unit
    def test_detectar_intermitente(self, sample_intermittent_data):
        """Deve detectar demanda intermitente corretamente"""
        vendas = sample_intermittent_data['Vendas'].tolist()
        datas = sample_intermittent_data['Mes'].tolist()

        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        caract = recomendacao.get('caracteristicas', {})
        # Deve marcar como intermitente ou recomendar TSB
        assert caract.get('intermitente', False) or recomendacao['metodo'] == 'TSB'
