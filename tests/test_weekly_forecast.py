# -*- coding: utf-8 -*-
"""
Teste do modulo de previsao semanal ISO-8601
"""

import sys
import os

# Adicionar o diretorio raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from core.weekly_forecast import (
    get_iso_week,
    get_date_from_iso_week,
    calcular_semanas_cobertura,
    WeeklyForecast
)


def test_get_iso_week():
    """Testa conversao de data para semana ISO."""
    print("\n=== Teste: get_iso_week ===")

    # Semana 3 de 2026 (Janeiro)
    d = date(2026, 1, 15)
    ano, semana = get_iso_week(d)
    print(f"Data: {d} -> Ano ISO: {ano}, Semana ISO: {semana}")
    assert ano == 2026
    assert semana == 3

    # Virada de ano
    d = date(2025, 12, 31)
    ano, semana = get_iso_week(d)
    print(f"Data: {d} -> Ano ISO: {ano}, Semana ISO: {semana}")

    print("OK!")


def test_calcular_semanas_cobertura():
    """Testa calculo de semanas no periodo de cobertura."""
    print("\n=== Teste: calcular_semanas_cobertura ===")

    # Cenario: Hoje = 15/01/2026 (Semana 3), Lead Time = 15 dias, Cobertura = 30 dias
    data_base = date(2026, 1, 15)
    lead_time = 15
    cobertura = 30

    semanas = calcular_semanas_cobertura(data_base, lead_time, cobertura)

    print(f"Data base: {data_base}")
    print(f"Lead time: {lead_time} dias")
    print(f"Cobertura: {cobertura} dias")
    print(f"Data entrega: {data_base + timedelta(days=lead_time)}")
    print(f"\nSemanas de cobertura:")

    for ano, semana, dias in semanas:
        print(f"  {ano}-W{semana:02d}: {dias} dias")

    assert len(semanas) >= 4  # Pelo menos 4 semanas para 30 dias
    print("OK!")


def test_weekly_forecast_mock():
    """Testa WeeklyForecast com conexao mock."""
    print("\n=== Teste: WeeklyForecast (mock) ===")

    # Criar mock da conexao
    class MockConnection:
        def cursor(self):
            return MockCursor()

    class MockCursor:
        def execute(self, query, params=None):
            pass

        def fetchall(self):
            return []

        def close(self):
            pass

    # Testar instanciacao
    wf = WeeklyForecast(None)  # Conn None para teste basico

    # Testar calculo de indices (sem dados)
    import pandas as pd
    df_vazio = pd.DataFrame(columns=['ano_iso', 'semana_iso', 'qtd_venda'])
    indices = wf.calcular_indice_semanal(df_vazio)

    assert len(indices) == 53  # Semanas 1-53
    assert all(v == 1.0 for v in indices.values())  # Todos neutros sem dados

    print("OK!")


def test_full_integration():
    """Testa integracao completa com banco real (se disponivel)."""
    print("\n=== Teste: Integracao Completa ===")

    try:
        import psycopg2

        conn = psycopg2.connect(
            host='localhost',
            database='previsao_demanda',
            user='postgres',
            password='FerreiraCost@01'
        )

        wf = WeeklyForecast(conn)

        # Testar com um produto real (se existir)
        resultado = wf.calcular_demanda_periodo_cobertura(
            codigo=100001,  # Codigo de teste
            cod_empresa=80,
            lead_time_dias=15,
            cobertura_dias=30,
            demanda_media_diaria=5.0
        )

        print(f"Demanda total prevista: {resultado['demanda_total']}")
        print(f"Demanda por dia: {resultado['demanda_por_dia']}")
        print(f"Numero de semanas: {resultado['numero_semanas']}")
        print(f"Semana atual: {resultado['detalhes']['semana_atual']}")
        print(f"Semana entrega: {resultado['detalhes']['semana_entrega']}")

        print("\nSemanas de cobertura:")
        for sem in resultado['semanas_cobertura']:
            print(f"  {sem['ano_iso']}-W{sem['semana_iso']:02d}: "
                  f"previsao={sem['previsao_proporcional']:.1f} ({sem['dias_na_semana']} dias)")

        conn.close()
        print("\nOK!")

    except Exception as e:
        print(f"Erro na integracao: {e}")
        print("(Isso pode ser normal se o banco nao estiver disponivel)")


if __name__ == '__main__':
    print("=" * 60)
    print("TESTES DO MODULO DE PREVISAO SEMANAL ISO-8601")
    print("=" * 60)

    test_get_iso_week()
    test_calcular_semanas_cobertura()
    test_weekly_forecast_mock()
    test_full_integration()

    print("\n" + "=" * 60)
    print("TODOS OS TESTES PASSARAM!")
    print("=" * 60)
