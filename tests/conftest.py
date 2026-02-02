# -*- coding: utf-8 -*-
"""
Configuração global de fixtures para pytest.
Este arquivo é automaticamente carregado pelo pytest.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Adicionar diretório raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================
# FIXTURES - DADOS DE TESTE
# ============================================

@pytest.fixture
def sample_sales_data():
    """
    DataFrame com dados de vendas para testes.
    12 meses de histórico simulado.
    """
    dates = pd.date_range('2025-01-01', periods=12, freq='M')
    return pd.DataFrame({
        'data': dates,
        'SKU': 'PROD001',
        'Loja': 'L001',
        'Mes': dates.strftime('%Y-%m-%d'),
        'Vendas': [100, 120, 95, 130, 140, 125, 160, 145, 170, 155, 180, 190],
        'Vendas_Corrigidas': [100, 120, 95, 130, 140, 125, 160, 145, 170, 155, 180, 190]
    })


@pytest.fixture
def sample_intermittent_data():
    """
    DataFrame com demanda intermitente (muitos zeros) para testar TSB.
    """
    dates = pd.date_range('2025-01-01', periods=12, freq='M')
    return pd.DataFrame({
        'data': dates,
        'SKU': 'PROD002',
        'Loja': 'L001',
        'Mes': dates.strftime('%Y-%m-%d'),
        'Vendas': [0, 5, 0, 0, 8, 0, 3, 0, 0, 0, 6, 0],
        'Vendas_Corrigidas': [0, 5, 0, 0, 8, 0, 3, 0, 0, 0, 6, 0]
    })


@pytest.fixture
def sample_seasonal_data():
    """
    DataFrame com padrão sazonal claro para testar decomposição.
    """
    dates = pd.date_range('2024-01-01', periods=24, freq='M')
    # Padrão sazonal: pico em dezembro, baixa em janeiro-fevereiro
    seasonal_pattern = [80, 70, 90, 100, 110, 120, 130, 140, 150, 180, 200, 250,
                       85, 75, 95, 105, 115, 125, 135, 145, 155, 185, 210, 260]
    return pd.DataFrame({
        'data': dates,
        'SKU': 'PROD003',
        'Loja': 'L001',
        'Mes': dates.strftime('%Y-%m-%d'),
        'Vendas': seasonal_pattern,
        'Vendas_Corrigidas': seasonal_pattern
    })


@pytest.fixture
def sample_short_series():
    """
    Série curta (menos de 6 meses) para testar ShortSeriesHandler.
    """
    dates = pd.date_range('2025-01-01', periods=4, freq='M')
    return pd.DataFrame({
        'data': dates,
        'SKU': 'PROD004',
        'Loja': 'L001',
        'Mes': dates.strftime('%Y-%m-%d'),
        'Vendas': [100, 110, 105, 115],
        'Vendas_Corrigidas': [100, 110, 105, 115]
    })


@pytest.fixture
def sample_estoque_data():
    """
    DataFrame com dados de estoque para testes de reabastecimento.
    """
    return pd.DataFrame({
        'codigo': ['PROD001', 'PROD002', 'PROD003'],
        'cod_empresa': [1, 1, 1],
        'estoque_atual': [100, 50, 200],
        'demanda_media': [10, 5, 15],
        'lead_time': [7, 14, 10],
        'classificacao_abc': ['A', 'B', 'C'],
        'ponto_reposicao': [70, 70, 150],
        'estoque_maximo': [200, 150, 400]
    })


@pytest.fixture
def sample_fornecedor_params():
    """
    Parâmetros de fornecedor para testes.
    """
    return {
        'cnpj': '12345678000190',
        'nome_fantasia': 'Fornecedor Teste',
        'lead_time_dias': 7,
        'ciclo_pedido_dias': 14,
        'pedido_minimo': 100.00,
        'multiplo_embalagem': 6
    }


# ============================================
# FIXTURES - APLICAÇÃO FLASK
# ============================================

@pytest.fixture
def app():
    """
    Instância da aplicação Flask para testes.
    """
    from app import create_app

    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    return app


@pytest.fixture
def client(app):
    """
    Cliente de teste Flask.
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    CLI runner para testes de comandos.
    """
    return app.test_cli_runner()


# ============================================
# FIXTURES - MOCKS
# ============================================

@pytest.fixture
def mock_db_connection(mocker):
    """
    Mock da conexão com banco de dados.
    """
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mocker.patch('app.utils.db_connection.get_db_connection', return_value=mock_conn)

    return mock_conn, mock_cursor


# ============================================
# HELPERS
# ============================================

def assert_dataframe_equal(df1, df2, check_dtype=False):
    """
    Helper para comparar DataFrames em testes.
    """
    pd.testing.assert_frame_equal(df1, df2, check_dtype=check_dtype)


def assert_series_close(s1, s2, rtol=1e-5):
    """
    Helper para comparar Series numéricas com tolerância.
    """
    np.testing.assert_allclose(s1.values, s2.values, rtol=rtol)
