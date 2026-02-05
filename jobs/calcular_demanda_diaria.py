"""
Cronjob: Calculo Diario de Demanda Pre-Calculada
=================================================
Executa diariamente as 05:00 para calcular demanda de todos os itens.
Os valores sao salvos na tabela demanda_pre_calculada e usados por:
- Tela de Demanda (previsao)
- Tela de Pedido Fornecedor

Isso garante INTEGRIDADE TOTAL entre as duas telas.

Modos de Operacao:
==================
1. CRONJOB DIARIO (05:00):
   python jobs/calcular_demanda_diaria.py

2. EXECUCAO MANUAL (todos os fornecedores):
   python jobs/calcular_demanda_diaria.py --manual

3. RECALCULO DE FORNECEDOR ESPECIFICO:
   python jobs/calcular_demanda_diaria.py --fornecedor 60620366000195

4. VERIFICAR STATUS:
   python jobs/calcular_demanda_diaria.py --status

Autor: Valter Lino / Claude (Anthropic)
Data: Fevereiro 2026
"""

import sys
import os
import argparse
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        logging.FileHandler(os.path.join(LOG_DIR, 'calcular_demanda_diaria.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from jobs.configuracao_jobs import CONFIGURACAO_BANCO
from core.demand_calculator import DemandCalculator, calcular_fator_tendencia_yoy


# Configuracoes
MESES_PREVISAO = 12  # Calcular 12 meses a frente
MAX_WORKERS = 4      # Threads para paralelizacao
DIAS_HISTORICO = 730 # 2 anos de historico


def obter_conexao():
    """Obtem conexao com o banco de dados."""
    import psycopg2
    conn = psycopg2.connect(**CONFIGURACAO_BANCO)
    conn.set_client_encoding('LATIN1')
    return conn


def registrar_inicio_execucao(conn, tipo: str, cnpj_filtro: str = None) -> int:
    """Registra inicio da execucao na tabela de controle."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO demanda_calculo_execucao (tipo, status, cnpj_fornecedor_filtro)
        VALUES (%s, 'iniciado', %s)
        RETURNING id
    """, (tipo, cnpj_filtro))
    execucao_id = cursor.fetchone()[0]
    conn.commit()
    return execucao_id


def atualizar_execucao(conn, execucao_id: int, status: str, metricas: Dict):
    """Atualiza registro de execucao com resultado final."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE demanda_calculo_execucao
        SET status = %s,
            total_itens_processados = %s,
            total_itens_erro = %s,
            total_fornecedores = %s,
            tempo_execucao_ms = %s,
            detalhes = %s
        WHERE id = %s
    """, (
        status,
        metricas.get('total_itens', 0),
        metricas.get('total_erros', 0),
        metricas.get('total_fornecedores', 0),
        metricas.get('tempo_ms', 0),
        json.dumps(metricas.get('detalhes', {})),
        execucao_id
    ))
    conn.commit()


def buscar_fornecedores(conn, cnpj_filtro: str = None) -> List[Dict]:
    """Busca lista de fornecedores para processar."""
    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if cnpj_filtro:
        cursor.execute("""
            SELECT DISTINCT cnpj_fornecedor, nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE cnpj_fornecedor = %s
        """, (cnpj_filtro,))
    else:
        cursor.execute("""
            SELECT DISTINCT cnpj_fornecedor, nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE cnpj_fornecedor IS NOT NULL AND TRIM(cnpj_fornecedor) != ''
            ORDER BY nome_fornecedor
        """)

    return cursor.fetchall()


def buscar_itens_fornecedor(conn, cnpj_fornecedor: str) -> List[Dict]:
    """Busca lista de itens de um fornecedor."""
    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT DISTINCT
            h.codigo as cod_produto,
            p.descricao
        FROM historico_vendas_diario h
        JOIN cadastro_produtos_completo p ON h.codigo::text = p.cod_produto
        WHERE p.cnpj_fornecedor = %s
          AND h.data >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY h.codigo
    """, (cnpj_fornecedor, DIAS_HISTORICO))

    return cursor.fetchall()


def buscar_historico_item(conn, cod_produto: int, cnpj_fornecedor: str) -> Tuple[List[float], Dict]:
    """
    Busca historico de vendas diarias de um item.
    Retorna serie temporal e metadata.
    """
    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Buscar vendas diarias dos ultimos 2 anos
    cursor.execute("""
        SELECT
            h.data,
            SUM(h.qtd_venda) as qtd_venda
        FROM historico_vendas_diario h
        JOIN cadastro_produtos_completo p ON h.codigo::text = p.cod_produto
        WHERE h.codigo = %s
          AND p.cnpj_fornecedor = %s
          AND h.data >= CURRENT_DATE - INTERVAL '%s days'
          AND h.data < CURRENT_DATE
        GROUP BY h.data
        ORDER BY h.data
    """, (cod_produto, cnpj_fornecedor, DIAS_HISTORICO))

    vendas_por_data = {row['data']: float(row['qtd_venda']) for row in cursor.fetchall()}

    # Criar serie completa (preenchendo zeros nos dias sem venda)
    if vendas_por_data:
        data_min = min(vendas_por_data.keys())
        data_max = max(vendas_por_data.keys())
        dias_total = (data_max - data_min).days + 1

        serie = []
        data_atual = data_min
        while data_atual <= data_max:
            serie.append(vendas_por_data.get(data_atual, 0))
            data_atual += timedelta(days=1)

        # Calcular vendas por mes (para ano anterior)
        vendas_por_mes = {}
        for data, qtd in vendas_por_data.items():
            chave = (data.year, data.month)
            vendas_por_mes[chave] = vendas_por_mes.get(chave, 0) + qtd

        metadata = {
            'dias_historico': dias_total,
            'dias_com_venda': len(vendas_por_data),
            'total_vendido': sum(vendas_por_data.values()),
            'vendas_por_mes': vendas_por_mes
        }
    else:
        serie = []
        metadata = {
            'dias_historico': 0,
            'dias_com_venda': 0,
            'total_vendido': 0,
            'vendas_por_mes': {}
        }

    return serie, metadata


def calcular_fatores_sazonais(vendas_por_mes: Dict) -> Dict[int, float]:
    """
    Calcula fatores sazonais por mes (1-12).
    Fator = media do mes / media geral (limitado entre 0.5 e 2.0)
    """
    # Agrupar por mes do ano
    totais_por_mes = {}
    contagem_por_mes = {}

    for (ano, mes), qtd in vendas_por_mes.items():
        if mes not in totais_por_mes:
            totais_por_mes[mes] = 0
            contagem_por_mes[mes] = 0
        totais_por_mes[mes] += qtd
        contagem_por_mes[mes] += 1

    # Calcular media por mes
    medias = {}
    for mes in range(1, 13):
        if mes in totais_por_mes and contagem_por_mes[mes] > 0:
            medias[mes] = totais_por_mes[mes] / contagem_por_mes[mes]
        else:
            medias[mes] = 0

    # Media geral
    medias_validas = [m for m in medias.values() if m > 0]
    media_geral = sum(medias_validas) / len(medias_validas) if medias_validas else 0

    # Calcular fatores (limitados entre 0.5 e 2.0)
    fatores = {}
    for mes in range(1, 13):
        if media_geral > 0 and medias[mes] > 0:
            fator = medias[mes] / media_geral
            fatores[mes] = max(0.5, min(2.0, fator))
        else:
            fatores[mes] = 1.0

    return fatores


def calcular_demanda_item(
    conn,
    cod_produto: int,
    cnpj_fornecedor: str,
    ano_base: int
) -> List[Dict]:
    """
    Calcula demanda pre-calculada para um item.
    Retorna lista de registros para os proximos 12 meses.
    """
    # Buscar historico
    serie, meta_hist = buscar_historico_item(conn, cod_produto, cnpj_fornecedor)

    if not serie or len(serie) < 7:
        # Historico insuficiente
        return []

    # Calcular demanda usando DemandCalculator (mesmo da tela de demanda)
    demanda_total, desvio_total, meta_calc = DemandCalculator.calcular_demanda_diaria_unificada(
        vendas_diarias=serie,
        dias_periodo=30,  # Base mensal
        granularidade_exibicao='mensal'
    )

    demanda_diaria_base = meta_calc.get('demanda_diaria_base', 0)
    if demanda_diaria_base <= 0:
        return []

    # Calcular fatores sazonais
    fatores_sazonais = calcular_fatores_sazonais(meta_hist.get('vendas_por_mes', {}))

    # ==========================================================================
    # NOVO: Calcular fator de tendencia YoY (Year-over-Year)
    # Implementado em Fev/2026 para corrigir subestimacao em itens com crescimento
    # ==========================================================================
    vendas_por_mes = meta_hist.get('vendas_por_mes', {})
    fator_tendencia_yoy = 1.0
    classificacao_tendencia = 'nao_calculado'
    meta_tendencia = {}

    if vendas_por_mes:
        fator_tendencia_yoy, classificacao_tendencia, meta_tendencia = calcular_fator_tendencia_yoy(
            vendas_por_mes,
            min_anos=2,
            fator_amortecimento=0.7
        )

    # Gerar registros para os proximos 12 meses
    registros = []
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year

    for i in range(MESES_PREVISAO):
        mes = ((mes_atual - 1 + i) % 12) + 1
        ano = ano_atual + ((mes_atual - 1 + i) // 12)

        # Dias no mes
        if mes in [1, 3, 5, 7, 8, 10, 12]:
            dias_mes = 31
        elif mes in [4, 6, 9, 11]:
            dias_mes = 30
        else:
            dias_mes = 29 if ano % 4 == 0 else 28

        # Fator sazonal do mes
        fator_sazonal = fatores_sazonais.get(mes, 1.0)

        # ==========================================================================
        # FORMULA ATUALIZADA (v5.7):
        # Demanda = base * fator_sazonal * fator_tendencia_yoy * dias
        #
        # Ordem de aplicacao:
        # 1. demanda_diaria_base (metodos estatisticos: SMA, WMA, EMA, etc)
        # 2. fator_sazonal (0.5 a 2.0 - padrao mensal)
        # 3. fator_tendencia_yoy (0.7 a 1.4 - crescimento/queda anual)
        # 4. dias_mes (dias no periodo)
        # 5. limitador_v11 (aplicado depois, -40% a +50% vs ano anterior)
        # ==========================================================================
        demanda_prevista = demanda_diaria_base * fator_sazonal * fator_tendencia_yoy * dias_mes

        # Buscar valor ano anterior
        ano_anterior = ano - 1
        valor_aa = meta_hist.get('vendas_por_mes', {}).get((ano_anterior, mes), 0)

        # Aplicar limitador V11 (-40% a +50%)
        limitador_aplicado = False
        if valor_aa > 0:
            variacao = demanda_prevista / valor_aa
            if variacao > 1.5:
                demanda_prevista = valor_aa * 1.5
                limitador_aplicado = True
            elif variacao < 0.6:
                demanda_prevista = valor_aa * 0.6
                limitador_aplicado = True

        # Calcular variacao vs AA
        variacao_vs_aa = (demanda_prevista / valor_aa) if valor_aa > 0 else None

        registros.append({
            'cod_produto': str(cod_produto),
            'cnpj_fornecedor': cnpj_fornecedor,
            'cod_empresa': None,  # Consolidado
            'ano': ano,
            'mes': mes,
            'demanda_prevista': round(demanda_prevista, 2),
            'demanda_diaria_base': round(demanda_diaria_base, 4),
            'desvio_padrao': round(meta_calc.get('desvio_diario_base', 0), 4),
            'fator_sazonal': round(fator_sazonal, 4),
            'fator_tendencia_yoy': round(fator_tendencia_yoy, 4),
            'classificacao_tendencia': classificacao_tendencia,
            'valor_ano_anterior': round(valor_aa, 2) if valor_aa else None,
            'variacao_vs_aa': round(variacao_vs_aa, 4) if variacao_vs_aa else None,
            'limitador_aplicado': limitador_aplicado,
            'metodo_usado': meta_calc.get('metodo_usado', 'auto'),
            'categoria_serie': meta_calc.get('categoria_serie', 'media'),
            'dias_historico': meta_hist.get('dias_historico', 0),
            'total_vendido_historico': round(meta_hist.get('total_vendido', 0), 2)
        })

    return registros


def salvar_demanda_batch(conn, registros: List[Dict]):
    """
    Salva batch de registros de demanda no banco.

    ATUALIZADO v5.7 (Fev/2026):
    - Adicionado fator_tendencia_yoy (captura crescimento/queda YoY)
    - Adicionado classificacao_tendencia (forte_crescimento, crescimento, estavel, queda, forte_queda)
    """
    if not registros:
        return 0

    cursor = conn.cursor()

    # Usar UPSERT para atualizar ou inserir
    for reg in registros:
        cursor.execute("""
            INSERT INTO demanda_pre_calculada (
                cod_produto, cnpj_fornecedor, cod_empresa, ano, mes,
                demanda_prevista, demanda_diaria_base, desvio_padrao,
                fator_sazonal, fator_tendencia_yoy, classificacao_tendencia,
                valor_ano_anterior, variacao_vs_aa,
                limitador_aplicado, metodo_usado, categoria_serie,
                dias_historico, total_vendido_historico, data_calculo
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, NOW()
            )
            ON CONFLICT (cod_produto, cnpj_fornecedor, cod_empresa, ano, mes)
            DO UPDATE SET
                demanda_prevista = EXCLUDED.demanda_prevista,
                demanda_diaria_base = EXCLUDED.demanda_diaria_base,
                desvio_padrao = EXCLUDED.desvio_padrao,
                fator_sazonal = EXCLUDED.fator_sazonal,
                fator_tendencia_yoy = EXCLUDED.fator_tendencia_yoy,
                classificacao_tendencia = EXCLUDED.classificacao_tendencia,
                valor_ano_anterior = EXCLUDED.valor_ano_anterior,
                variacao_vs_aa = EXCLUDED.variacao_vs_aa,
                limitador_aplicado = EXCLUDED.limitador_aplicado,
                metodo_usado = EXCLUDED.metodo_usado,
                categoria_serie = EXCLUDED.categoria_serie,
                dias_historico = EXCLUDED.dias_historico,
                total_vendido_historico = EXCLUDED.total_vendido_historico,
                data_calculo = NOW()
            WHERE demanda_pre_calculada.ajuste_manual IS NULL
        """, (
            reg['cod_produto'], reg['cnpj_fornecedor'], reg['cod_empresa'],
            reg['ano'], reg['mes'],
            reg['demanda_prevista'], reg['demanda_diaria_base'], reg['desvio_padrao'],
            reg['fator_sazonal'], reg['fator_tendencia_yoy'], reg['classificacao_tendencia'],
            reg['valor_ano_anterior'], reg['variacao_vs_aa'],
            reg['limitador_aplicado'], reg['metodo_usado'], reg['categoria_serie'],
            reg['dias_historico'], reg['total_vendido_historico']
        ))

    conn.commit()
    return len(registros)


def processar_fornecedor(cnpj_fornecedor: str, nome_fornecedor: str) -> Dict:
    """
    Processa todos os itens de um fornecedor.
    Executado em thread separada.
    """
    conn = None
    try:
        conn = obter_conexao()
        ano_base = datetime.now().year

        # Buscar itens do fornecedor
        itens = buscar_itens_fornecedor(conn, cnpj_fornecedor)

        total_registros = 0
        total_erros = 0

        for item in itens:
            try:
                registros = calcular_demanda_item(
                    conn,
                    item['cod_produto'],
                    cnpj_fornecedor,
                    ano_base
                )
                if registros:
                    total_registros += salvar_demanda_batch(conn, registros)
            except Exception as e:
                total_erros += 1
                logger.debug(f"Erro item {item['cod_produto']}: {e}")

        return {
            'cnpj': cnpj_fornecedor,
            'nome': nome_fornecedor,
            'itens': len(itens),
            'registros': total_registros,
            'erros': total_erros,
            'sucesso': True
        }

    except Exception as e:
        logger.error(f"Erro processando fornecedor {cnpj_fornecedor}: {e}")
        return {
            'cnpj': cnpj_fornecedor,
            'nome': nome_fornecedor,
            'itens': 0,
            'registros': 0,
            'erros': 1,
            'sucesso': False,
            'erro': str(e)
        }
    finally:
        if conn:
            conn.close()


def executar_calculo(tipo: str = 'cronjob_diario', cnpj_filtro: str = None):
    """
    Executa o calculo de demanda para todos os fornecedores (ou filtrado).
    """
    logger.info("=" * 60)
    logger.info("  CALCULO DIARIO DE DEMANDA PRE-CALCULADA")
    logger.info(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"  Tipo: {tipo}")
    if cnpj_filtro:
        logger.info(f"  Filtro: {cnpj_filtro}")
    logger.info("=" * 60)

    inicio = time.time()
    conn = obter_conexao()

    # Registrar inicio
    execucao_id = registrar_inicio_execucao(conn, tipo, cnpj_filtro)

    # Buscar fornecedores
    fornecedores = buscar_fornecedores(conn, cnpj_filtro)
    logger.info(f"Fornecedores a processar: {len(fornecedores)}")

    conn.close()

    # Processar em paralelo
    resultados = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(processar_fornecedor, f['cnpj_fornecedor'], f['nome_fornecedor']): f
            for f in fornecedores
        }

        for future in as_completed(futures):
            resultado = future.result()
            resultados.append(resultado)
            status = "OK" if resultado['sucesso'] else "ERRO"
            logger.info(f"  [{status}] {resultado['nome'][:30]:<30} - {resultado['registros']:>6} registros")

    # Consolidar metricas
    total_itens = sum(r['itens'] for r in resultados)
    total_registros = sum(r['registros'] for r in resultados)
    total_erros = sum(r['erros'] for r in resultados)
    tempo_ms = int((time.time() - inicio) * 1000)

    metricas = {
        'total_itens': total_itens,
        'total_registros': total_registros,
        'total_erros': total_erros,
        'total_fornecedores': len(fornecedores),
        'tempo_ms': tempo_ms,
        'detalhes': {
            'fornecedores': [r for r in resultados if not r['sucesso']]
        }
    }

    # Atualizar registro de execucao
    conn = obter_conexao()
    status_final = 'sucesso' if total_erros == 0 else ('parcial' if total_registros > 0 else 'erro')
    atualizar_execucao(conn, execucao_id, status_final, metricas)
    conn.close()

    logger.info("=" * 60)
    logger.info(f"  RESULTADO: {status_final.upper()}")
    logger.info(f"  Fornecedores: {len(fornecedores)}")
    logger.info(f"  Itens processados: {total_itens:,}")
    logger.info(f"  Registros salvos: {total_registros:,}")
    logger.info(f"  Erros: {total_erros}")
    logger.info(f"  Tempo: {tempo_ms/1000:.1f}s")
    logger.info("=" * 60)

    return metricas


def verificar_status():
    """Mostra status das ultimas execucoes."""
    conn = obter_conexao()
    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 60)
    print("  STATUS DO CALCULO DE DEMANDA")
    print("=" * 60)

    # Ultima execucao
    cursor.execute("""
        SELECT *
        FROM demanda_calculo_execucao
        ORDER BY data_execucao DESC
        LIMIT 5
    """)

    print("\nUltimas 5 execucoes:")
    for row in cursor.fetchall():
        print(f"  {row['data_execucao']} | {row['tipo']:<20} | {row['status']:<10} | {row['total_itens_processados']:>6} itens")

    # Total de registros
    cursor.execute("SELECT COUNT(*) as total FROM demanda_pre_calculada")
    total = cursor.fetchone()['total']
    print(f"\nTotal registros na tabela: {total:,}")

    # Registros com ajuste manual
    cursor.execute("SELECT COUNT(*) as total FROM demanda_pre_calculada WHERE ajuste_manual IS NOT NULL")
    ajustes = cursor.fetchone()['total']
    print(f"Registros com ajuste manual: {ajustes:,}")

    conn.close()


def iniciar_scheduler():
    """Inicia scheduler para execucao diaria as 05:00."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler nao instalado. Execute: pip install apscheduler")
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(
        executar_calculo,
        CronTrigger(hour=5, minute=0),
        id='calculo_demanda_diaria',
        name='Calculo Diario de Demanda',
        misfire_grace_time=3600
    )

    logger.info("Scheduler iniciado. Calculo agendado para 05:00 diariamente.")
    logger.info("Pressione Ctrl+C para encerrar.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler encerrado.")


def main():
    """Funcao principal."""
    parser = argparse.ArgumentParser(
        description='Calculo Diario de Demanda Pre-Calculada',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--manual', action='store_true',
                        help='Executa calculo imediatamente')
    parser.add_argument('--fornecedor', type=str,
                        help='CNPJ do fornecedor para recalculo especifico')
    parser.add_argument('--status', action='store_true',
                        help='Mostra status das ultimas execucoes')

    args = parser.parse_args()

    if args.status:
        verificar_status()
    elif args.fornecedor:
        executar_calculo(tipo='recalculo_fornecedor', cnpj_filtro=args.fornecedor)
    elif args.manual:
        executar_calculo(tipo='manual')
    else:
        iniciar_scheduler()


if __name__ == '__main__':
    main()
