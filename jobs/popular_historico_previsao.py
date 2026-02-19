"""
Job: Popular Historico de Previsoes
====================================
Popula a tabela historico_previsao com dados historicos para calculo de WMAPE e BIAS.

Este job:
1. Le as demandas pre-calculadas (demanda_pre_calculada)
2. Compara com as vendas reais (historico_vendas_diario)
3. Salva em historico_previsao para calculo de metricas de acuracia

Modos de Operacao:
==================
1. POPULAR DADOS HISTORICOS (ultimos N meses):
   python jobs/popular_historico_previsao.py --meses 6

2. EXECUTAR PARA UM MES ESPECIFICO:
   python jobs/popular_historico_previsao.py --mes 2026-01

3. VERIFICAR STATUS:
   python jobs/popular_historico_previsao.py --status

Autor: Valter Lino / Claude (Anthropic)
Data: Fevereiro 2026
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional

# Adicionar pasta raiz ao path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Configurar logging
LOG_DIR = os.path.join(ROOT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'popular_historico_previsao.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from jobs.configuracao_jobs import CONFIGURACAO_BANCO


def obter_conexao():
    """Obtem conexao com o banco de dados."""
    import psycopg2
    conn = psycopg2.connect(**CONFIGURACAO_BANCO)
    conn.set_client_encoding('LATIN1')
    return conn


def popular_mes(conn, ano_mes: str) -> Dict:
    """
    Popula historico_previsao para um mes especifico.

    Para calcular WMAPE/BIAS, usamos a demanda media diaria prevista vs realizada.
    A previsao e baseada na demanda_pre_calculada (que usa media movel dos ultimos 730 dias).
    O realizado e a soma das vendas do mes.

    Args:
        conn: Conexao com banco
        ano_mes: Mes no formato YYYY-MM

    Returns:
        Dict com estatisticas da execucao
    """
    cursor = conn.cursor()

    # Parsear ano/mes
    ano, mes = map(int, ano_mes.split('-'))
    data_inicio = datetime(ano, mes, 1)

    # Calcular ultimo dia do mes
    if mes == 12:
        data_fim = datetime(ano + 1, 1, 1) - timedelta(days=1)
    else:
        data_fim = datetime(ano, mes + 1, 1) - timedelta(days=1)

    dias_no_mes = (data_fim - data_inicio).days + 1

    logger.info(f"Populando historico_previsao para {ano_mes} ({dias_no_mes} dias)")

    # Buscar demanda pre-calculada que existia no inicio do mes
    # Como a demanda_pre_calculada e sobrescrita, usamos uma aproximacao:
    # A demanda media diaria do historico de vendas

    # Inserir registros comparando previsao (media movel) com realizado
    insert_query = """
        INSERT INTO historico_previsao (
            data, cod_empresa, codigo, qtd_prevista, qtd_realizada,
            tipo_previsao, modelo, versao
        )
        SELECT
            %s as data,
            hvd.cod_empresa,
            hvd.codigo,
            -- Previsao: media diaria dos ultimos 365 dias antes do mes * dias do mes
            COALESCE(
                (
                    SELECT SUM(hvd2.qtd_venda) / NULLIF(COUNT(DISTINCT hvd2.data), 0) * %s
                    FROM historico_vendas_diario hvd2
                    WHERE hvd2.codigo = hvd.codigo
                    AND hvd2.cod_empresa = hvd.cod_empresa
                    AND hvd2.data >= %s - INTERVAL '365 days'
                    AND hvd2.data < %s
                ), 0
            ) as qtd_prevista,
            -- Realizado: soma das vendas do mes
            SUM(hvd.qtd_venda) as qtd_realizada,
            'mensal' as tipo_previsao,
            'media_movel_365d' as modelo,
            1 as versao
        FROM historico_vendas_diario hvd
        WHERE hvd.data >= %s
        AND hvd.data <= %s
        GROUP BY hvd.cod_empresa, hvd.codigo
        HAVING SUM(hvd.qtd_venda) > 0
        ON CONFLICT (data, cod_empresa, codigo, tipo_previsao, versao)
        DO UPDATE SET
            qtd_prevista = EXCLUDED.qtd_prevista,
            qtd_realizada = EXCLUDED.qtd_realizada,
            updated_at = CURRENT_TIMESTAMP
    """

    try:
        cursor.execute(insert_query, (
            data_inicio,  # data da previsao (primeiro dia do mes)
            dias_no_mes,  # multiplicador para previsao mensal
            data_inicio,  # inicio do periodo de historico
            data_inicio,  # fim do periodo de historico
            data_inicio,  # inicio do mes
            data_fim      # fim do mes
        ))

        registros_inseridos = cursor.rowcount
        conn.commit()

        logger.info(f"  {registros_inseridos} registros inseridos/atualizados para {ano_mes}")

        return {
            'mes': ano_mes,
            'registros': registros_inseridos,
            'sucesso': True
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao popular mes {ano_mes}: {e}")
        return {
            'mes': ano_mes,
            'registros': 0,
            'sucesso': False,
            'erro': str(e)
        }


def calcular_metricas_acuracia(conn) -> Dict:
    """
    Calcula WMAPE e BIAS global a partir dos dados de historico_previsao.
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total_registros,
            SUM(qtd_realizada) as total_realizado,
            SUM(ABS(qtd_realizada - qtd_prevista)) as soma_erros_abs,
            SUM(qtd_prevista - qtd_realizada) as soma_erros,
            CASE
                WHEN SUM(qtd_realizada) > 0
                THEN ROUND(SUM(ABS(qtd_realizada - qtd_prevista)) / SUM(qtd_realizada) * 100, 2)
                ELSE NULL
            END as wmape,
            CASE
                WHEN SUM(qtd_realizada) > 0
                THEN ROUND(SUM(qtd_prevista - qtd_realizada) / SUM(qtd_realizada) * 100, 2)
                ELSE NULL
            END as bias
        FROM historico_previsao
        WHERE qtd_realizada IS NOT NULL
        AND qtd_realizada > 0
    """)

    result = cursor.fetchone()

    return {
        'total_registros': result[0],
        'total_realizado': float(result[1]) if result[1] else 0,
        'wmape': float(result[4]) if result[4] else None,
        'bias': float(result[5]) if result[5] else None
    }


def verificar_status(conn) -> Dict:
    """
    Verifica status atual da tabela historico_previsao.
    """
    cursor = conn.cursor()

    # Contagem total
    cursor.execute("SELECT COUNT(*) FROM historico_previsao")
    total = cursor.fetchone()[0]

    # Meses disponveis
    cursor.execute("""
        SELECT
            TO_CHAR(data, 'YYYY-MM') as mes,
            COUNT(*) as registros,
            SUM(CASE WHEN qtd_realizada IS NOT NULL THEN 1 ELSE 0 END) as com_realizado
        FROM historico_previsao
        GROUP BY TO_CHAR(data, 'YYYY-MM')
        ORDER BY mes DESC
        LIMIT 12
    """)
    meses = cursor.fetchall()

    # Metricas
    metricas = calcular_metricas_acuracia(conn)

    return {
        'total_registros': total,
        'meses': [{'mes': m[0], 'registros': m[1], 'com_realizado': m[2]} for m in meses],
        'metricas': metricas
    }


def main():
    parser = argparse.ArgumentParser(description='Popular historico de previsoes')
    parser.add_argument('--meses', type=int, help='Numero de meses historicos a popular')
    parser.add_argument('--mes', type=str, help='Mes especifico no formato YYYY-MM')
    parser.add_argument('--status', action='store_true', help='Mostrar status atual')

    args = parser.parse_args()

    conn = obter_conexao()

    try:
        if args.status:
            status = verificar_status(conn)
            print("\n" + "="*60)
            print("STATUS DO HISTORICO DE PREVISOES")
            print("="*60)
            print(f"Total de registros: {status['total_registros']:,}")

            if status['meses']:
                print("\nMeses disponveis (ltimos 12):")
                for m in status['meses']:
                    print(f"  {m['mes']}: {m['registros']:,} registros ({m['com_realizado']:,} com realizado)")

            print("\nMetricas de Acuracia:")
            print(f"  WMAPE: {status['metricas']['wmape']:.2f}%" if status['metricas']['wmape'] else "  WMAPE: N/A")
            print(f"  BIAS:  {status['metricas']['bias']:+.2f}%" if status['metricas']['bias'] else "  BIAS:  N/A")
            print("="*60 + "\n")

        elif args.mes:
            result = popular_mes(conn, args.mes)
            if result['sucesso']:
                print(f"Sucesso: {result['registros']} registros para {args.mes}")
            else:
                print(f"Erro: {result.get('erro', 'Desconhecido')}")

        elif args.meses:
            # Popular ultimos N meses
            hoje = datetime.now()
            total_registros = 0

            for i in range(args.meses):
                # Comecar do mes passado
                mes_ref = hoje - relativedelta(months=i+1)
                ano_mes = mes_ref.strftime('%Y-%m')

                result = popular_mes(conn, ano_mes)
                total_registros += result.get('registros', 0)

            print(f"\nTotal: {total_registros:,} registros populados para {args.meses} meses")

            # Calcular metricas
            metricas = calcular_metricas_acuracia(conn)
            print(f"\nMetricas Atualizadas:")
            print(f"  WMAPE: {metricas['wmape']:.2f}%" if metricas['wmape'] else "  WMAPE: N/A")
            print(f"  BIAS:  {metricas['bias']:+.2f}%" if metricas['bias'] else "  BIAS:  N/A")

        else:
            # Default: popular ultimo mes completo
            mes_passado = datetime.now() - relativedelta(months=1)
            ano_mes = mes_passado.strftime('%Y-%m')

            result = popular_mes(conn, ano_mes)
            if result['sucesso']:
                print(f"Sucesso: {result['registros']} registros para {ano_mes}")
            else:
                print(f"Erro: {result.get('erro', 'Desconhecido')}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
