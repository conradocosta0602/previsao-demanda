# -*- coding: utf-8 -*-
"""
Teste de Integracao: Pedido Fornecedor com Previsao Semanal
===========================================================
Simula o cenario: Pedido destino CD (loja 80), fornecedor Lorenzetti SP.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import pandas as pd
from datetime import datetime


def test_pedido_com_previsao_semanal():
    """Testa geracao de pedido usando previsao semanal."""
    print("=" * 70)
    print("TESTE: Pedido ao Fornecedor com Previsao Semanal ISO-8601")
    print("=" * 70)

    try:
        # Conectar ao banco
        conn = psycopg2.connect(
            host='localhost',
            database='previsao_demanda',
            user='postgres',
            password='FerreiraCost@01'
        )
        print("Conectado ao banco de dados.")

        # Importar modulos
        from core.pedido_fornecedor_integrado import PedidoFornecedorIntegrado
        from core.demand_calculator import DemandCalculator

        # Criar processador COM previsao semanal (padrao)
        processador = PedidoFornecedorIntegrado(conn, usar_previsao_semanal=True)

        # Buscar alguns produtos do fornecedor Lorenzetti para teste
        query = """
            SELECT DISTINCT cod_produto as codigo, descricao
            FROM cadastro_produtos_completo
            WHERE UPPER(nome_fornecedor) LIKE '%LORENZETTI%'
              AND ativo = TRUE
            LIMIT 5
        """

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            df_produtos = pd.read_sql(query, conn)

        if df_produtos.empty:
            print("Nenhum produto Lorenzetti encontrado. Buscando produtos com vendas...")
            # Buscar produtos que tem vendas na loja
            query = """
                SELECT DISTINCT hv.codigo, cp.descricao
                FROM historico_vendas_diario hv
                JOIN cadastro_produtos_completo cp ON hv.codigo::text = cp.cod_produto
                WHERE hv.cod_empresa = 3
                  AND hv.qtd_venda > 0
                GROUP BY hv.codigo, cp.descricao
                HAVING COUNT(*) > 30
                ORDER BY SUM(hv.qtd_venda) DESC
                LIMIT 5
            """
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                df_produtos = pd.read_sql(query, conn)

        print(f"\nProdutos para teste: {len(df_produtos)}")

        # Parametros do pedido
        # Nota: Loja 80 (CD) nao tem vendas, usando loja 3 para teste
        cod_empresa = 3  # Loja com mais vendas
        cobertura_dias = 30  # Cobertura automatica ou manual
        lead_time = 15  # Lead time tipico

        print(f"\nParametros:")
        print(f"  Destino: Loja {cod_empresa} (CD)")
        print(f"  Cobertura: {cobertura_dias} dias")
        print(f"  Lead time estimado: {lead_time} dias")

        # Semana atual
        from core.weekly_forecast import get_iso_week
        ano_atual, semana_atual = get_iso_week(datetime.now().date())
        print(f"  Semana atual ISO: {ano_atual}-W{semana_atual:02d}")

        # Processar cada produto
        print("\n" + "-" * 70)
        print("RESULTADOS POR PRODUTO")
        print("-" * 70)

        for idx, row in df_produtos.iterrows():
            codigo = row['codigo']
            descricao = row['descricao'][:40]

            # Buscar historico (de todas as lojas para CD)
            historico = processador.buscar_historico_vendas(codigo, cod_empresa, dias=365)

            if not historico or len(historico) < 7:
                print(f"\n[{codigo}] {descricao}")
                print(f"  -> Sem historico suficiente")
                continue

            # Calcular demanda
            demanda_diaria, desvio, metadata = DemandCalculator.calcular_demanda_inteligente(historico, metodo='auto')

            if demanda_diaria <= 0:
                print(f"\n[{codigo}] {descricao}")
                print(f"  -> Demanda zero")
                continue

            # Processar item
            resultado = processador.processar_item(
                codigo=codigo,
                cod_empresa=cod_empresa,
                previsao_diaria=demanda_diaria,
                desvio_padrao=desvio,
                cobertura_dias=cobertura_dias
            )

            if 'erro' in resultado:
                print(f"\n[{codigo}] {descricao}")
                print(f"  -> Erro: {resultado['erro']}")
                continue

            # Exibir resultado
            print(f"\n[{codigo}] {descricao}")
            print(f"  Demanda prevista periodo: {resultado.get('demanda_prevista', resultado.get('demanda_periodo', 0)):.0f} un")
            print(f"  Demanda prevista diaria: {resultado.get('demanda_prevista_diaria', demanda_diaria):.2f} un/dia")
            print(f"  Estoque atual: {resultado.get('estoque_atual', resultado.get('estoque_efetivo', 0)):.0f} un")
            print(f"  Estoque transito: {resultado.get('estoque_transito', 0):.0f} un")
            print(f"  Cobertura atual: {resultado['cobertura_atual_dias']:.1f} dias")
            print(f"  Preco custo (CUE): R$ {resultado.get('preco_custo', 0):.2f}")

            # Info da previsao semanal
            prev_semanal = resultado.get('previsao_semanal', {})
            if prev_semanal.get('usado'):
                print(f"  [PREVISAO SEMANAL ISO-8601]")
                print(f"    Semana entrega: {prev_semanal.get('semana_entrega', '?')}")
                print(f"    Semanas cobertura: {prev_semanal.get('numero_semanas', 0)}")

                semanas = prev_semanal.get('semanas_cobertura', [])
                if semanas:
                    print(f"    Detalhes:")
                    for sem in semanas[:3]:  # Mostrar primeiras 3
                        print(f"      W{sem['semana_iso']:02d}: {sem['previsao_proporcional']:.1f} un ({sem['dias_na_semana']} dias)")
                    if len(semanas) > 3:
                        print(f"      ... e mais {len(semanas) - 3} semanas")
            else:
                print(f"  [Metodo: demanda_diaria_simples]")

            if resultado['deve_pedir']:
                print(f"  >>> PEDIR: {resultado['quantidade_pedido']:.0f} un")
                print(f"  >>> Valor: R$ {resultado['valor_pedido']:.2f}")
            else:
                print(f"  >>> NAO PRECISA PEDIR (estoque ok)")

        conn.close()

        print("\n" + "=" * 70)
        print("TESTE CONCLUIDO COM SUCESSO!")
        print("=" * 70)

    except Exception as e:
        import traceback
        print(f"\nERRO: {e}")
        traceback.print_exc()


if __name__ == '__main__':
    test_pedido_com_previsao_semanal()
