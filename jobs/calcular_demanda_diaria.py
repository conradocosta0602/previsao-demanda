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
SEMANAS_PREVISAO = 54  # Calcular ~13 meses de previsao semanal
MAX_WORKERS = 4      # Threads para paralelizacao
DIAS_HISTORICO = 730 # 2 anos de historico
LIMITER_CORRECAO = 3.0  # V53: correcao maxima de 3x a media dos dias com estoque
FREQUENCIA_MINIMA_CORRECAO = 0.25  # V53b: so corrige loja se vendeu em >=25% dos dias com estoque


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
    """
    Busca lista de fornecedores para processar.

    Args:
        conn: Conexao com o banco
        cnpj_filtro: CNPJ ou NOME do fornecedor (ambos aceitos)

    Returns:
        Lista de dicionarios com cnpj_fornecedor e nome_fornecedor
    """
    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if cnpj_filtro:
        # Aceita tanto CNPJ quanto nome do fornecedor
        cursor.execute("""
            SELECT DISTINCT cnpj_fornecedor, nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE cnpj_fornecedor = %s OR nome_fornecedor = %s
        """, (cnpj_filtro, cnpj_filtro))
    else:
        cursor.execute("""
            SELECT DISTINCT cnpj_fornecedor, nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE cnpj_fornecedor IS NOT NULL AND TRIM(cnpj_fornecedor) != ''
            ORDER BY nome_fornecedor
        """)

    return cursor.fetchall()


def buscar_itens_bloqueados(conn, cnpj_fornecedor: str) -> Dict[int, set]:
    """
    Busca itens com situacao EN (Em Negociacao) ou FL (Fora de Linha) por loja.

    Args:
        conn: Conexao com o banco
        cnpj_fornecedor: CNPJ do fornecedor

    Returns:
        Dict {cod_produto: {cod_empresa1, cod_empresa2, ...}}
        Mapeia cada produto para o conjunto de lojas onde esta bloqueado.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.codigo, s.cod_empresa
        FROM situacao_compra_itens s
        JOIN cadastro_produtos_completo p ON s.codigo::text = p.cod_produto
        WHERE p.cnpj_fornecedor = %s
          AND s.sit_compra IN ('EN', 'FL')
    """, (cnpj_fornecedor,))

    bloqueados = {}
    for codigo, cod_empresa in cursor.fetchall():
        if codigo not in bloqueados:
            bloqueados[codigo] = set()
        bloqueados[codigo].add(cod_empresa)

    return bloqueados


def buscar_total_lojas(conn) -> int:
    """Retorna o total de lojas ativas no sistema."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT cod_empresa) FROM cadastro_fornecedores")
    return cursor.fetchone()[0]


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


def precarregar_historico_lote(conn, cod_produtos: List[int], cnpj_fornecedor: str) -> Dict[int, Tuple[List[float], Dict]]:
    """
    Pre-carrega historico de vendas de TODOS os itens de uma vez.
    OTIMIZACAO: 1 query em vez de N queries.

    Args:
        conn: Conexao com o banco
        cod_produtos: Lista de codigos de produtos
        cnpj_fornecedor: CNPJ do fornecedor

    Returns:
        Dict {cod_produto: (serie, metadata)}
    """
    if not cod_produtos:
        return {}

    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # V53: Query com cod_empresa para vendas por loja
    placeholders = ','.join(['%s'] * len(cod_produtos))
    cursor.execute(f"""
        SELECT
            h.codigo,
            h.data,
            h.cod_empresa,
            SUM(h.qtd_venda) as qtd_venda
        FROM historico_vendas_diario h
        WHERE h.codigo IN ({placeholders})
          AND h.data >= CURRENT_DATE - INTERVAL '{DIAS_HISTORICO} days'
          AND h.data < CURRENT_DATE
        GROUP BY h.codigo, h.data, h.cod_empresa
        ORDER BY h.codigo, h.data
    """, cod_produtos)

    # Agrupar por produto — consolidado + por loja
    vendas_por_produto = {}       # {cod: {data: qtd_total}}
    vendas_por_loja_produto = {}  # V53: {cod: {(data, cod_empresa): qtd}}
    for row in cursor.fetchall():
        cod = int(row['codigo'])
        qtd = float(row['qtd_venda'])
        data = row['data']
        cod_emp = int(row['cod_empresa'])

        # Consolidado (como antes)
        if cod not in vendas_por_produto:
            vendas_por_produto[cod] = {}
        vendas_por_produto[cod][data] = vendas_por_produto[cod].get(data, 0) + qtd

        # V53: Por loja
        if cod not in vendas_por_loja_produto:
            vendas_por_loja_produto[cod] = {}
        vendas_por_loja_produto[cod][(data, cod_emp)] = qtd

    # Processar cada produto
    resultado = {}
    for cod_produto in cod_produtos:
        vendas_por_data = vendas_por_produto.get(cod_produto, {})

        if vendas_por_data:
            data_min = min(vendas_por_data.keys())
            data_max = max(vendas_por_data.keys())
            dias_total = (data_max - data_min).days + 1

            serie = []
            data_atual = data_min
            while data_atual <= data_max:
                serie.append(vendas_por_data.get(data_atual, 0))
                data_atual += timedelta(days=1)

            # Calcular vendas por mes
            vendas_por_mes = {}
            for data, qtd in vendas_por_data.items():
                chave = (data.year, data.month)
                vendas_por_mes[chave] = vendas_por_mes.get(chave, 0) + qtd

            metadata = {
                'dias_historico': dias_total,
                'dias_com_venda': len(vendas_por_data),
                'total_vendido': sum(vendas_por_data.values()),
                'vendas_por_mes': vendas_por_mes,
                'vendas_por_data': vendas_por_data,  # V51: consolidado
                'vendas_por_loja': vendas_por_loja_produto.get(cod_produto, {})  # V53: por loja
            }
        else:
            serie = []
            metadata = {
                'dias_historico': 0,
                'dias_com_venda': 0,
                'total_vendido': 0,
                'vendas_por_mes': {},
                'vendas_por_data': {},
                'vendas_por_loja': {}  # V53
            }

        resultado[cod_produto] = (serie, metadata)

    return resultado


def precarregar_estoque_diario_lote(conn, cod_produtos: List[int]) -> Dict[int, Dict]:
    """
    V53: Pre-carrega estoque diario POR LOJA para cada item.
    Usado para detectar e corrigir demanda censurada por loja individual.

    Returns:
        Dict {cod_produto: {(data, cod_empresa): estoque_diario}}
    """
    if not cod_produtos:
        return {}

    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    placeholders = ','.join(['%s'] * len(cod_produtos))
    cursor.execute(f"""
        SELECT
            e.codigo,
            e.data,
            e.cod_empresa,
            COALESCE(e.estoque_diario, 0) as estoque_diario
        FROM historico_estoque_diario e
        WHERE e.codigo IN ({placeholders})
          AND e.data >= CURRENT_DATE - INTERVAL '{DIAS_HISTORICO} days'
          AND e.data < CURRENT_DATE
        ORDER BY e.codigo, e.data
    """, cod_produtos)

    resultado = {}
    for row in cursor.fetchall():
        cod = int(row['codigo'])
        if cod not in resultado:
            resultado[cod] = {}
        chave = (row['data'], int(row['cod_empresa']))
        resultado[cod][chave] = float(row['estoque_diario'])

    cursor.close()
    return resultado


def _corrigir_loja(
    serie_loja: List[float],
    datas_serie: list,
    estoque_loja_por_data: Dict
) -> Tuple[List[float], Dict]:
    """
    V53: Aplica correcao de ruptura para uma UNICA loja.
    Mesma logica de 3 estrategias do V51 + limiter 3x.

    Args:
        serie_loja: vendas diarias da loja (alinhada com datas_serie)
        datas_serie: lista de datas correspondentes a serie
        estoque_loja_por_data: {data: estoque} para esta loja

    Returns:
        (serie_corrigida, meta_loja)
    """
    import numpy as np

    meta_loja = {
        'dias_ruptura': 0,
        'dias_corrigidos': 0,
        'dias_verificados': 0,
        'dias_com_estoque': 0,
    }

    serie_corrigida = list(serie_loja)

    # Calcular estatisticas da loja
    vendas_com_estoque = []
    for i, data in enumerate(datas_serie):
        estoque_dia = estoque_loja_por_data.get(data, None)
        if estoque_dia is not None:
            meta_loja['dias_verificados'] += 1
            if estoque_dia > 0:
                meta_loja['dias_com_estoque'] += 1
                if serie_loja[i] > 0:
                    vendas_com_estoque.append(serie_loja[i])

    if meta_loja['dias_verificados'] == 0:
        return serie_corrigida, meta_loja

    # V53b: Filtro de frequencia - nao corrigir itens intermitentes nesta loja
    # Se o item vendeu em menos de 25% dos dias com estoque, venda=0 e normal
    # (demanda intermitente), nao ruptura. TSB ja lida com esses itens.
    dias_com_venda = len(vendas_com_estoque)  # dias com estoque E venda > 0
    if meta_loja['dias_com_estoque'] > 0:
        frequencia_venda = dias_com_venda / meta_loja['dias_com_estoque']
    else:
        frequencia_venda = 0

    if frequencia_venda < FREQUENCIA_MINIMA_CORRECAO:
        # Demanda intermitente nesta loja - nao corrigir
        return serie_corrigida, meta_loja

    # Contar dias de ruptura
    for i, data in enumerate(datas_serie):
        estoque_dia = estoque_loja_por_data.get(data, None)
        if estoque_dia is not None and serie_loja[i] == 0 and estoque_dia <= 0:
            meta_loja['dias_ruptura'] += 1

    # V53: Se nao ha ruptura, nada a corrigir
    if meta_loja['dias_ruptura'] == 0:
        return serie_corrigida, meta_loja

    # Limiter 3x: correcao maxima de 3x a media dos dias com estoque
    media_com_estoque = np.mean(vendas_com_estoque) if vendas_com_estoque else 0
    limite_correcao = media_com_estoque * LIMITER_CORRECAO if media_com_estoque > 0 else 0

    # Corrigir dias de ruptura
    for i, data in enumerate(datas_serie):
        estoque_dia = estoque_loja_por_data.get(data, None)
        if estoque_dia is None:
            continue

        if serie_loja[i] == 0 and estoque_dia <= 0:
            valor_estimado = 0

            # 1. Mesmo dia da semana (+-1/2 semanas)
            for delta_semanas in [1, -1, 2, -2]:
                idx_ref = i + (delta_semanas * 7)
                if 0 <= idx_ref < len(serie_loja):
                    data_ref = datas_serie[idx_ref]
                    estoque_ref = estoque_loja_por_data.get(data_ref, None)
                    if estoque_ref is not None and estoque_ref > 0 and serie_loja[idx_ref] > 0:
                        valor_estimado = serie_loja[idx_ref]
                        break

            # 2. Media de dias adjacentes com estoque
            if valor_estimado == 0:
                vals_adj = []
                for delta in [-1, 1, -2, 2, -3, 3]:
                    idx_adj = i + delta
                    if 0 <= idx_adj < len(serie_loja):
                        data_adj = datas_serie[idx_adj]
                        estoque_adj = estoque_loja_por_data.get(data_adj, None)
                        if estoque_adj is not None and estoque_adj > 0 and serie_loja[idx_adj] > 0:
                            vals_adj.append(serie_loja[idx_adj])
                    if len(vals_adj) >= 2:
                        break
                if vals_adj:
                    valor_estimado = np.mean(vals_adj)

            # 3. Mediana global dos dias com estoque e vendas positivas
            if valor_estimado == 0 and vendas_com_estoque:
                valor_estimado = float(np.median(vendas_com_estoque))

            # Aplicar limiter de seguranca (max 3x media)
            if limite_correcao > 0 and valor_estimado > limite_correcao:
                valor_estimado = limite_correcao

            if valor_estimado > 0:
                serie_corrigida[i] = valor_estimado
                meta_loja['dias_corrigidos'] += 1

    return serie_corrigida, meta_loja


def corrigir_demanda_censurada(
    serie_vendas: List[float],
    vendas_por_data: Dict,
    estoque_por_data: Dict,
    vendas_por_loja: Dict = None
) -> Tuple[List[float], Dict]:
    """
    V53: Corrige serie de vendas POR LOJA e reconsolida.
    Detecta ruptura parcial (loja sem estoque enquanto outras tem).
    Corrige TODOS os dias de ruptura de TODAS as lojas (exceto CDs).

    Protecao:
    - Limiter 3x: correcao max 3x media dos dias com estoque

    Args:
        serie_vendas: Lista de vendas diarias consolidada
        vendas_por_data: Dict {data: qtd_total} consolidado
        estoque_por_data: Dict {(data, cod_empresa): estoque} por loja (V53)
        vendas_por_loja: Dict {(data, cod_empresa): qtd_venda} por loja (V53)

    Returns:
        (serie_corrigida, metadata_censura)
    """
    import numpy as np

    meta = {
        'dias_ruptura': 0,
        'dias_corrigidos': 0,
        'taxa_disponibilidade': 1.0,
        'houve_correcao': False
    }

    if not estoque_por_data or not vendas_por_data:
        return serie_vendas, meta

    # Reconstruir datas da serie
    datas_ordenadas = sorted(vendas_por_data.keys())
    if not datas_ordenadas:
        return serie_vendas, meta

    data_min = min(datas_ordenadas)
    data_max = max(datas_ordenadas)

    datas_serie = []
    data_atual = data_min
    while data_atual <= data_max:
        datas_serie.append(data_atual)
        data_atual += timedelta(days=1)

    if len(datas_serie) != len(serie_vendas):
        return serie_vendas, meta

    # V53: Extrair lojas distintas do estoque (excluir CDs >= 80)
    lojas = set()
    for chave in estoque_por_data.keys():
        if isinstance(chave, tuple) and len(chave) == 2 and chave[1] < 80:
            lojas.add(chave[1])  # cod_empresa (apenas lojas fisicas)

    # Fallback: se estoque nao tem formato (data, cod_empresa) → formato V51 consolidado
    if not lojas or vendas_por_loja is None or not vendas_por_loja:
        # Fallback V51 consolidado (chaves sao datas simples)
        return _corrigir_consolidado_fallback(serie_vendas, datas_serie, vendas_por_data, estoque_por_data)

    # V53: Processar cada loja individualmente
    total_dias_ruptura = 0
    total_dias_corrigidos = 0
    total_dias_verificados = 0
    total_dias_com_estoque = 0
    lojas_corrigidas = 0

    # Acumular correcoes por loja: {loja: serie_corrigida_loja}
    series_por_loja = {}

    for loja in sorted(lojas):
        # Construir serie de vendas da loja
        serie_loja = []
        for data in datas_serie:
            serie_loja.append(vendas_por_loja.get((data, loja), 0))

        # Construir estoque da loja
        estoque_loja = {}
        for data in datas_serie:
            val = estoque_por_data.get((data, loja), None)
            if val is not None:
                estoque_loja[data] = val

        # Corrigir esta loja
        serie_corrigida_loja, meta_loja = _corrigir_loja(serie_loja, datas_serie, estoque_loja)
        series_por_loja[loja] = serie_corrigida_loja

        # Acumular metadata
        total_dias_ruptura += meta_loja['dias_ruptura']
        total_dias_corrigidos += meta_loja['dias_corrigidos']
        total_dias_verificados += meta_loja['dias_verificados']
        total_dias_com_estoque += meta_loja['dias_com_estoque']
        if meta_loja['dias_corrigidos'] > 0:
            lojas_corrigidas += 1

    # Reconsolidar: serie_corrigida[i] = SUM(serie_corrigida_loja[i])
    # Incluir lojas que NAO tem dados de estoque (suas vendas originais)
    serie_corrigida = [0.0] * len(datas_serie)

    # Somar lojas com estoque (corrigidas ou nao)
    for loja, serie_loja in series_por_loja.items():
        for i in range(len(serie_corrigida)):
            serie_corrigida[i] += serie_loja[i]

    # Somar vendas de lojas SEM dados de estoque (nao afetadas pela correcao)
    lojas_com_vendas = set()
    for chave in vendas_por_loja.keys():
        if isinstance(chave, tuple) and len(chave) == 2:
            lojas_com_vendas.add(chave[1])
    lojas_sem_estoque = lojas_com_vendas - lojas

    for loja in lojas_sem_estoque:
        for i, data in enumerate(datas_serie):
            serie_corrigida[i] += vendas_por_loja.get((data, loja), 0)

    taxa_disponibilidade = total_dias_com_estoque / total_dias_verificados if total_dias_verificados > 0 else 1.0

    meta = {
        'dias_ruptura': total_dias_ruptura,
        'dias_corrigidos': total_dias_corrigidos,
        'taxa_disponibilidade': round(taxa_disponibilidade, 4),
        'houve_correcao': total_dias_corrigidos > 0,
        'lojas_corrigidas': lojas_corrigidas  # V53
    }

    return serie_corrigida, meta


def _corrigir_consolidado_fallback(
    serie_vendas: List[float],
    datas_serie: list,
    vendas_por_data: Dict,
    estoque_por_data: Dict
) -> Tuple[List[float], Dict]:
    """Fallback V51: correcao consolidada para itens sem estoque por loja."""
    import numpy as np

    meta = {
        'dias_ruptura': 0,
        'dias_corrigidos': 0,
        'taxa_disponibilidade': 1.0,
        'houve_correcao': False
    }

    serie_corrigida = list(serie_vendas)
    dias_com_estoque = 0
    dias_verificados = 0

    vendas_com_estoque = []
    for i, data in enumerate(datas_serie):
        estoque_dia = estoque_por_data.get(data, None)
        if estoque_dia is not None:
            dias_verificados += 1
            if estoque_dia > 0:
                dias_com_estoque += 1
                if serie_vendas[i] > 0:
                    vendas_com_estoque.append(serie_vendas[i])

    if dias_verificados == 0:
        return serie_vendas, meta

    # V53b: Filtro de frequencia consolidado
    dias_com_venda = len(vendas_com_estoque)
    frequencia_venda = dias_com_venda / dias_com_estoque if dias_com_estoque > 0 else 0
    if frequencia_venda < FREQUENCIA_MINIMA_CORRECAO:
        # Demanda intermitente - nao corrigir
        meta['taxa_disponibilidade'] = dias_com_estoque / dias_verificados if dias_verificados > 0 else 1.0
        return serie_vendas, meta

    media_com_estoque = np.mean(vendas_com_estoque) if vendas_com_estoque else 0
    limite_correcao = media_com_estoque * LIMITER_CORRECAO if media_com_estoque > 0 else 0
    dias_ruptura = 0
    dias_corrigidos = 0

    for i, data in enumerate(datas_serie):
        estoque_dia = estoque_por_data.get(data, None)
        if estoque_dia is None:
            continue
        if serie_vendas[i] == 0 and estoque_dia <= 0:
            dias_ruptura += 1
            valor_estimado = 0

            for delta_semanas in [1, -1, 2, -2]:
                idx_ref = i + (delta_semanas * 7)
                if 0 <= idx_ref < len(serie_vendas):
                    data_ref = datas_serie[idx_ref]
                    estoque_ref = estoque_por_data.get(data_ref, None)
                    if estoque_ref is not None and estoque_ref > 0 and serie_vendas[idx_ref] > 0:
                        valor_estimado = serie_vendas[idx_ref]
                        break

            if valor_estimado == 0:
                vals_adj = []
                for delta in [-1, 1, -2, 2, -3, 3]:
                    idx_adj = i + delta
                    if 0 <= idx_adj < len(serie_vendas):
                        data_adj = datas_serie[idx_adj]
                        estoque_adj = estoque_por_data.get(data_adj, None)
                        if estoque_adj is not None and estoque_adj > 0 and serie_vendas[idx_adj] > 0:
                            vals_adj.append(serie_vendas[idx_adj])
                    if len(vals_adj) >= 2:
                        break
                if vals_adj:
                    valor_estimado = np.mean(vals_adj)

            if valor_estimado == 0 and vendas_com_estoque:
                valor_estimado = float(np.median(vendas_com_estoque))

            if limite_correcao > 0 and valor_estimado > limite_correcao:
                valor_estimado = limite_correcao

            if valor_estimado > 0:
                serie_corrigida[i] = valor_estimado
                dias_corrigidos += 1

    taxa_disponibilidade = dias_com_estoque / dias_verificados if dias_verificados > 0 else 1.0

    meta = {
        'dias_ruptura': dias_ruptura,
        'dias_corrigidos': dias_corrigidos,
        'taxa_disponibilidade': round(taxa_disponibilidade, 4),
        'houve_correcao': dias_corrigidos > 0
    }

    return serie_corrigida, meta


def buscar_historico_item(conn, cod_produto: int, cnpj_fornecedor: str) -> Tuple[List[float], Dict]:
    """
    Busca historico de vendas diarias de um item.
    Retorna serie temporal e metadata.

    NOTA: Funcao mantida para compatibilidade, mas preferir precarregar_historico_lote()
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
    V48: Deteccao de outliers antes do calculo.
    """
    # Buscar historico
    serie, meta_hist = buscar_historico_item(conn, cod_produto, cnpj_fornecedor)

    if not serie or len(serie) < 7:
        # Historico insuficiente
        return []

    # V48: Deteccao e tratamento de outliers ANTES do calculo
    serie_limpa = serie
    if len(serie) >= 30:
        try:
            from core.outlier_detector import AutoOutlierDetector
            detector = AutoOutlierDetector()
            resultado_outliers = detector.analyze_and_clean(serie)
            if resultado_outliers['outliers_count'] > 0:
                serie_limpa = resultado_outliers['cleaned_data']
        except Exception:
            pass

    # Calcular demanda usando DemandCalculator (com serie limpa)
    demanda_total, desvio_total, meta_calc = DemandCalculator.calcular_demanda_diaria_unificada(
        vendas_diarias=serie_limpa,
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

        # Aplicar limitador V11 (-40% a +50%) - Atualizado v5.7
        # NOVO: Para itens com tendencia de crescimento, se previsao < AA, corrigir
        limitador_aplicado = False
        if valor_aa > 0:
            variacao = demanda_prevista / valor_aa

            # NOVO v5.7: Ajuste para itens em crescimento
            # Se item tem tendencia de crescimento mas previsao < AA, corrigir
            if fator_tendencia_yoy > 1.05 and variacao < 1.0:
                # Usar o fator de tendencia para projetar sobre o AA
                # Limitado a +40% para evitar exageros
                demanda_prevista = valor_aa * min(fator_tendencia_yoy, 1.4)
                limitador_aplicado = True
            # Limitar variacao maxima para cima (+50%)
            elif variacao > 1.5:
                demanda_prevista = valor_aa * 1.5
                limitador_aplicado = True
            # Limitar variacao maxima para baixo (-40%)
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
    OTIMIZADO: Usa execute_values para INSERT em lote (muito mais rapido).

    ATUALIZADO v5.7 (Fev/2026):
    - Adicionado fator_tendencia_yoy (captura crescimento/queda YoY)
    - Adicionado classificacao_tendencia (forte_crescimento, crescimento, estavel, queda, forte_queda)
    """
    if not registros:
        return 0

    from psycopg2.extras import execute_values

    cursor = conn.cursor()

    # FIX v6.25: DELETE + INSERT com protecao contra duplicatas
    # 1. Deleta registros SEM ajuste_manual (serao recalculados)
    # 2. Identifica registros COM ajuste_manual (preservados)
    # 3. Deduplicar batch antes do INSERT
    # 4. Usa COALESCE(cod_empresa,0) para casar com o UNIQUE index
    chaves_para_deletar = set()
    for reg in registros:
        chaves_para_deletar.add((
            reg['cod_produto'], reg['cnpj_fornecedor'],
            reg['ano'], reg['mes']
        ))

    # Deletar registros antigos SEM ajuste manual que serao recalculados.
    # Registros com ajuste_manual (salvos pela Tela de Demanda) sao preservados.
    chaves_com_ajuste = set()
    if chaves_para_deletar:
        chaves_list = list(chaves_para_deletar)
        execute_values(cursor, """
            DELETE FROM demanda_pre_calculada
            WHERE ajuste_manual IS NULL
              AND tipo_granularidade = 'mensal'
              AND (cod_produto, cnpj_fornecedor, ano, mes) IN (VALUES %s)
              AND (cod_empresa IS NULL OR cod_empresa = 0)
        """, chaves_list, template="(%s, %s, %s, %s)")

        # Identificar quais chaves ainda existem (tem ajuste_manual) para nao inserir duplicata
        # NOTA: Nao usar execute_values para SELECT (page_size trunca resultados)
        # Extrair cnpj unico do batch para query direta
        cnpjs = set(c[1] for c in chaves_list)
        for cnpj in cnpjs:
            cursor.execute("""
                SELECT cod_produto, cnpj_fornecedor, ano, mes
                FROM demanda_pre_calculada
                WHERE cnpj_fornecedor = %s
                  AND (cod_empresa IS NULL OR cod_empresa = 0)
                  AND ajuste_manual IS NOT NULL
                  AND tipo_granularidade = 'mensal'
            """, (cnpj,))
            for row in cursor.fetchall():
                chaves_com_ajuste.add((str(row[0]), str(row[1]), int(row[2]), int(row[3])))

    # Preparar dados para insert em lote, excluindo os que ja tem ajuste_manual
    registros_para_inserir = [
        reg for reg in registros
        if (str(reg['cod_produto']), str(reg['cnpj_fornecedor']), int(reg['ano']), int(reg['mes'])) not in chaves_com_ajuste
    ]

    # Deduplicar batch: mesmo (cod_produto, cnpj, cod_empresa, ano, mes) pode aparecer 2x
    # UNIQUE index usa COALESCE(cod_empresa,0), entao NULL e 0 sao iguais
    vistos = set()
    registros_unicos = []
    for reg in registros_para_inserir:
        chave = (str(reg['cod_produto']), str(reg['cnpj_fornecedor']),
                 0 if reg['cod_empresa'] is None else int(reg['cod_empresa']),
                 int(reg['ano']), int(reg['mes']))
        if chave not in vistos:
            vistos.add(chave)
            registros_unicos.append(reg)

    valores = [
        (
            reg['cod_produto'], reg['cnpj_fornecedor'], reg['cod_empresa'],
            reg['ano'], reg['mes'],
            reg['demanda_prevista'], reg['demanda_diaria_base'], reg['desvio_padrao'],
            reg['fator_sazonal'], reg['fator_tendencia_yoy'], reg['classificacao_tendencia'],
            reg['valor_ano_anterior'], reg['variacao_vs_aa'],
            reg['limitador_aplicado'], reg['metodo_usado'], reg['categoria_serie'],
            reg['dias_historico'], reg['total_vendido_historico'],
            # V51: Metadata de demanda censurada
            reg.get('taxa_disponibilidade'),
            reg.get('dias_ruptura', 0),
            reg.get('demanda_censurada_corrigida', False)
        )
        for reg in registros_unicos
    ]

    if not valores:
        conn.commit()
        return len(registros)

    # INSERT em lote. Registros com ajuste_manual ja foram excluidos,
    # e batch deduplicado para evitar colisao no UNIQUE index.
    execute_values(cursor, """
        INSERT INTO demanda_pre_calculada (
            cod_produto, cnpj_fornecedor, cod_empresa, ano, mes,
            demanda_prevista, demanda_diaria_base, desvio_padrao,
            fator_sazonal, fator_tendencia_yoy, classificacao_tendencia,
            valor_ano_anterior, variacao_vs_aa,
            limitador_aplicado, metodo_usado, categoria_serie,
            dias_historico, total_vendido_historico,
            taxa_disponibilidade, dias_ruptura, demanda_censurada_corrigida,
            data_calculo
        ) VALUES %s
    """, valores, template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())")

    conn.commit()
    return len(registros)


def precarregar_historico_semanal_lote(conn, cod_produtos: List[int]) -> Dict[int, Tuple[Dict, Dict]]:
    """
    Pre-carrega historico de vendas agregado por semana ISO para TODOS os itens de uma vez.
    V53: Retorna tambem vendas por loja para correcao de ruptura por loja.

    Returns:
        Dict {cod_produto: (
            {(ano_iso, semana_iso): qtd_venda_total},                    # consolidado
            {(ano_iso, semana_iso, cod_empresa): qtd_venda_loja}         # V53: por loja
        )}
    """
    if not cod_produtos:
        return {}

    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # V53: Incluir cod_empresa no GROUP BY
    placeholders = ','.join(['%s'] * len(cod_produtos))
    cursor.execute(f"""
        SELECT
            h.codigo,
            h.cod_empresa,
            EXTRACT(ISOYEAR FROM h.data)::INTEGER as ano_iso,
            EXTRACT(WEEK FROM h.data)::INTEGER as semana_iso,
            SUM(COALESCE(h.qtd_venda, 0)) as qtd_venda
        FROM historico_vendas_diario h
        WHERE h.codigo IN ({placeholders})
          AND h.data >= CURRENT_DATE - INTERVAL '{DIAS_HISTORICO} days'
          AND h.data < CURRENT_DATE
        GROUP BY h.codigo, h.cod_empresa, ano_iso, semana_iso
        ORDER BY h.codigo, ano_iso, semana_iso
    """, cod_produtos)

    consolidado = {}    # {cod: {(ano_iso, sem_iso): qtd_total}}
    por_loja = {}       # {cod: {(ano_iso, sem_iso, cod_emp): qtd}}
    for row in cursor.fetchall():
        cod = int(row['codigo'])
        qtd = float(row['qtd_venda'])
        ano_iso = int(row['ano_iso'])
        sem_iso = int(row['semana_iso'])
        cod_emp = int(row['cod_empresa'])

        # Consolidado
        if cod not in consolidado:
            consolidado[cod] = {}
        chave_cons = (ano_iso, sem_iso)
        consolidado[cod][chave_cons] = consolidado[cod].get(chave_cons, 0) + qtd

        # V53: Por loja
        if cod not in por_loja:
            por_loja[cod] = {}
        por_loja[cod][(ano_iso, sem_iso, cod_emp)] = qtd

    cursor.close()

    # Montar resultado como tuple (consolidado, por_loja)
    resultado = {}
    for cod in set(list(consolidado.keys()) + list(por_loja.keys())):
        resultado[cod] = (consolidado.get(cod, {}), por_loja.get(cod, {}))

    return resultado


def precarregar_estoque_semanal_lote(conn, cod_produtos: List[int]) -> Dict[int, Dict]:
    """
    V53: Pre-carrega dias com estoque por semana ISO POR LOJA.
    Usado para corrigir demanda censurada na serie semanal.

    Returns:
        {cod_produto: {(ano_iso, semana_iso, cod_empresa): (dias_com_estoque, dias_totais)}}
    """
    if not cod_produtos:
        return {}

    from psycopg2.extras import RealDictCursor
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    placeholders = ','.join(['%s'] * len(cod_produtos))
    cursor.execute(f"""
        SELECT
            sub.codigo,
            sub.cod_empresa,
            sub.ano_iso,
            sub.semana_iso,
            COUNT(*) FILTER (WHERE sub.estoque_diario > 0) as dias_com_estoque,
            COUNT(*) as dias_totais
        FROM (
            SELECT
                e.codigo,
                e.cod_empresa,
                e.data,
                EXTRACT(ISOYEAR FROM e.data)::INTEGER as ano_iso,
                EXTRACT(WEEK FROM e.data)::INTEGER as semana_iso,
                COALESCE(e.estoque_diario, 0) as estoque_diario
            FROM historico_estoque_diario e
            WHERE e.codigo IN ({placeholders})
              AND e.data >= CURRENT_DATE - INTERVAL '{DIAS_HISTORICO} days'
              AND e.data < CURRENT_DATE
        ) sub
        GROUP BY sub.codigo, sub.cod_empresa, sub.ano_iso, sub.semana_iso
    """, cod_produtos)

    resultado = {}
    for row in cursor.fetchall():
        cod = int(row['codigo'])
        if cod not in resultado:
            resultado[cod] = {}
        resultado[cod][(int(row['ano_iso']), int(row['semana_iso']), int(row['cod_empresa']))] = (
            int(row['dias_com_estoque']),
            int(row['dias_totais'])
        )

    cursor.close()
    return resultado


def semanas_iso_do_mes(ano: int, mes: int) -> List[int]:
    """
    V55: Retorna lista de semanas ISO cujas segundas-feiras caem no mes dado.
    Usado para mapear semanas -> meses na decomposicao mensal->semanal.
    """
    from datetime import date as d_date
    semanas = []
    dia = d_date(ano, mes, 1)
    while dia.month == mes:
        if dia.weekday() == 0:  # segunda-feira
            semanas.append(dia.isocalendar()[1])
        dia += timedelta(days=1)
    return semanas


def calcular_pesos_semanais(historico_semanal: Dict) -> Dict[int, float]:
    """
    V55: Calcula peso medio de cada semana ISO (1-53) baseado no historico de vendas.
    peso = media_vendas_semana_iso / media_geral
    Usado para distribuir demanda mensal entre semanas com sazonalidade intra-mensal.
    """
    vendas_por_semana_iso = {}
    contagem = {}
    for (ano, sem), qtd in historico_semanal.items():
        if sem not in vendas_por_semana_iso:
            vendas_por_semana_iso[sem] = 0
            contagem[sem] = 0
        vendas_por_semana_iso[sem] += qtd
        contagem[sem] += 1

    medias = {}
    for sem in range(1, 54):
        if sem in vendas_por_semana_iso and contagem.get(sem, 0) > 0:
            medias[sem] = vendas_por_semana_iso[sem] / contagem[sem]
        else:
            medias[sem] = None

    # Media geral (apenas semanas com dados)
    vals = [v for v in medias.values() if v is not None and v > 0]
    media_geral = sum(vals) / len(vals) if vals else 1.0

    pesos = {}
    for sem in range(1, 54):
        if medias[sem] is not None and media_geral > 0:
            pesos[sem] = medias[sem] / media_geral
        else:
            pesos[sem] = 1.0
    return pesos


def calcular_demanda_item_semanal(
    cod_produto: int,
    cnpj_fornecedor: str,
    historico_semanal: Dict[Tuple[int, int], float],
    registros_mensais: List[Dict] = None,
    estoque_semanal: Dict = None,
    vendas_semanal_por_loja: Dict = None
) -> List[Dict]:
    """
    V55: Calcula demanda semanal DERIVADA da demanda mensal.
    Em vez de calcular independentemente, decompoe cada mes em semanas usando
    pesos sazonais semanais (vendas historicas por semana ISO).

    Garante: soma das semanas de um mes = demanda mensal (consistencia).
    Herda do mensal: metodo, YoY, desvio, limitador, classificacao.

    Args:
        cod_produto: Codigo do produto
        cnpj_fornecedor: CNPJ do fornecedor
        historico_semanal: Dict {(ano_iso, semana_iso): qtd_venda} - para pesos sazonais
        registros_mensais: Lista de registros mensais ja calculados para este item
        estoque_semanal: Dict {(ano_iso, semana_iso, cod_empresa): (dias_ok, dias_tot)} por loja
        vendas_semanal_por_loja: Dict {(ano_iso, semana_iso, cod_empresa): qtd} por loja

    Returns:
        Lista de registros semanais para INSERT
    """
    from datetime import date
    import numpy as np

    if not registros_mensais:
        return []

    # 1. Construir mapa mes -> registro mensal
    mapa_mensal = {}
    for reg in registros_mensais:
        mapa_mensal[(reg['ano'], reg['mes'])] = reg

    if not mapa_mensal:
        return []

    # 2. Calcular pesos sazonais semanais a partir do historico
    #    Se nao ha historico semanal, usar peso uniforme (1.0)
    if historico_semanal and len(historico_semanal) >= 4:
        # V53: Corrigir vendas semanais por loja antes de calcular pesos
        historico_corrigido = dict(historico_semanal)  # copia

        if estoque_semanal and vendas_semanal_por_loja:
            semanas_ordenadas = sorted(historico_semanal.keys())
            lojas = set()
            for chave in estoque_semanal.keys():
                if isinstance(chave, tuple) and len(chave) == 3 and chave[2] < 80:
                    lojas.add(chave[2])

            if lojas:
                for loja in sorted(lojas):
                    loja_dias_verif = 0
                    loja_dias_ok = 0
                    for s in semanas_ordenadas:
                        chave_loja = (s[0], s[1], loja)
                        if chave_loja in estoque_semanal:
                            d_ok, d_tot = estoque_semanal[chave_loja]
                            loja_dias_verif += d_tot
                            loja_dias_ok += d_ok

                    if loja_dias_verif == 0 or (loja_dias_verif - loja_dias_ok) == 0:
                        continue

                    vendas_boas_loja = []
                    semanas_com_estoque_ok = 0
                    for i, s in enumerate(semanas_ordenadas):
                        chave_loja = (s[0], s[1], loja)
                        venda_loja = vendas_semanal_por_loja.get(chave_loja, 0)
                        if chave_loja in estoque_semanal:
                            d_ok, d_tot = estoque_semanal[chave_loja]
                            if d_tot > 0 and d_ok / d_tot >= 0.5:
                                semanas_com_estoque_ok += 1
                                if venda_loja > 0:
                                    vendas_boas_loja.append(venda_loja)

                    # V53b: Filtro de frequencia semanal
                    freq_semanal = len(vendas_boas_loja) / semanas_com_estoque_ok if semanas_com_estoque_ok > 0 else 0
                    if freq_semanal < FREQUENCIA_MINIMA_CORRECAO:
                        continue  # Demanda intermitente nesta loja - nao corrigir

                    media_boa_loja = np.mean(vendas_boas_loja) if vendas_boas_loja else 0
                    limite_loja = media_boa_loja * LIMITER_CORRECAO

                    for i, s in enumerate(semanas_ordenadas):
                        chave_loja = (s[0], s[1], loja)
                        if chave_loja not in estoque_semanal:
                            continue
                        d_ok, d_tot = estoque_semanal[chave_loja]
                        if d_tot == 0 or d_ok / d_tot >= 1.0:
                            continue

                        taxa = d_ok / d_tot
                        venda_loja_raw = vendas_semanal_por_loja.get(chave_loja, 0)

                        if taxa > 0:
                            corrigido = venda_loja_raw / taxa
                        else:
                            mesma_sem = [vendas_semanal_por_loja.get((ss[0], ss[1], loja), 0)
                                         for ss in semanas_ordenadas
                                         if ss[1] == s[1] and ss != s
                                         and (ss[0], ss[1], loja) in estoque_semanal
                                         and estoque_semanal[(ss[0], ss[1], loja)][1] > 0
                                         and estoque_semanal[(ss[0], ss[1], loja)][0] / estoque_semanal[(ss[0], ss[1], loja)][1] >= 0.5]
                            mesma_sem = [v for v in mesma_sem if v > 0]
                            corrigido = np.mean(mesma_sem) if mesma_sem else media_boa_loja

                        if limite_loja > 0 and corrigido > limite_loja:
                            corrigido = limite_loja

                        diferenca = corrigido - venda_loja_raw
                        if diferenca > 0:
                            historico_corrigido[s] = historico_corrigido.get(s, 0) + diferenca

        pesos = calcular_pesos_semanais(historico_corrigido)
    else:
        pesos = {s: 1.0 for s in range(1, 54)}

    # 3. Gerar registros semanais derivados dos mensais
    registros = []
    hoje = date.today()

    for i in range(SEMANAS_PREVISAO):
        alvo = hoje + timedelta(weeks=i)
        ano_iso, semana_iso, dia_semana = alvo.isocalendar()
        monday = alvo - timedelta(days=dia_semana - 1)

        # Determinar mes correspondente pela segunda-feira
        mes_ref = monday.month
        ano_ref = monday.year

        # Buscar registro mensal correspondente
        reg_mensal = mapa_mensal.get((ano_ref, mes_ref))
        if not reg_mensal:
            continue

        demanda_mensal = float(reg_mensal['demanda_prevista'] or 0)
        if demanda_mensal <= 0:
            continue

        # Semanas ISO com segunda-feira neste mes
        semanas_do_mes = semanas_iso_do_mes(ano_ref, mes_ref)
        if not semanas_do_mes:
            continue

        # Peso desta semana e soma dos pesos do mes (normalizacao)
        peso_semana = pesos.get(semana_iso, 1.0)
        soma_pesos_mes = sum(pesos.get(s, 1.0) for s in semanas_do_mes)

        # Demanda semanal = mensal * (peso / soma_pesos) -> garante soma = mensal
        if soma_pesos_mes > 0:
            demanda_prevista = demanda_mensal * (peso_semana / soma_pesos_mes)
        else:
            demanda_prevista = demanda_mensal / len(semanas_do_mes)

        # Valor ano anterior semanal
        valor_aa_key = (ano_iso - 1, semana_iso)
        valor_aa = historico_semanal.get(valor_aa_key, 0) if historico_semanal else 0

        registros.append({
            'cod_produto': str(cod_produto),
            'cnpj_fornecedor': cnpj_fornecedor,
            'cod_empresa': None,
            'ano': ano_iso,
            'mes': None,
            'semana': semana_iso,
            'tipo_granularidade': 'semanal',
            'data_inicio_semana': monday,
            'demanda_prevista': round(demanda_prevista, 2),
            'demanda_diaria_base': round(demanda_prevista / 7.0, 4),
            'desvio_padrao': reg_mensal.get('desvio_padrao', 0),
            'fator_sazonal': reg_mensal.get('fator_sazonal', 1.0),
            'fator_tendencia_yoy': reg_mensal.get('fator_tendencia_yoy', 1.0),
            'classificacao_tendencia': reg_mensal.get('classificacao_tendencia', 'nao_calculado'),
            'valor_ano_anterior': round(valor_aa, 2) if valor_aa else None,
            'variacao_vs_aa': round(demanda_prevista / valor_aa, 4) if valor_aa and valor_aa > 0 else None,
            'limitador_aplicado': reg_mensal.get('limitador_aplicado', False),
            'metodo_usado': reg_mensal.get('metodo_usado', 'auto'),
            'categoria_serie': reg_mensal.get('categoria_serie', 'media'),
            'dias_historico': reg_mensal.get('dias_historico', 0),
            'total_vendido_historico': reg_mensal.get('total_vendido_historico', 0),
            'taxa_disponibilidade': reg_mensal.get('taxa_disponibilidade'),
            'dias_ruptura': reg_mensal.get('dias_ruptura', 0),
            'demanda_censurada_corrigida': reg_mensal.get('demanda_censurada_corrigida', False),
        })

    return registros


def salvar_demanda_batch_semanal(conn, registros: List[Dict]):
    """
    Salva batch de registros de demanda SEMANAL no banco.
    Espelha salvar_demanda_batch() mas com chave (cod_produto, cnpj_forn, ano, semana).
    """
    if not registros:
        return 0

    from psycopg2.extras import execute_values

    cursor = conn.cursor()

    # Coletar chaves para deletar (apenas registros semanais sem ajuste manual)
    chaves_para_deletar = set()
    for reg in registros:
        chaves_para_deletar.add((
            reg['cod_produto'], reg['cnpj_fornecedor'],
            reg['ano'], reg['semana']
        ))

    chaves_com_ajuste = set()
    if chaves_para_deletar:
        chaves_list = list(chaves_para_deletar)
        execute_values(cursor, """
            DELETE FROM demanda_pre_calculada
            WHERE ajuste_manual IS NULL
              AND tipo_granularidade = 'semanal'
              AND (cod_produto, cnpj_fornecedor, ano, semana) IN (VALUES %s)
              AND (cod_empresa IS NULL OR cod_empresa = 0)
        """, chaves_list, template="(%s, %s, %s, %s)")

        # Identificar chaves com ajuste manual (preservar)
        cnpjs = set(c[1] for c in chaves_list)
        for cnpj in cnpjs:
            cursor.execute("""
                SELECT cod_produto, cnpj_fornecedor, ano, semana
                FROM demanda_pre_calculada
                WHERE cnpj_fornecedor = %s
                  AND (cod_empresa IS NULL OR cod_empresa = 0)
                  AND ajuste_manual IS NOT NULL
                  AND tipo_granularidade = 'semanal'
            """, (cnpj,))
            for row in cursor.fetchall():
                chaves_com_ajuste.add((str(row[0]), str(row[1]), int(row[2]), int(row[3])))

    # Filtrar e deduplicar
    vistos = set()
    registros_unicos = []
    for reg in registros:
        chave = (str(reg['cod_produto']), str(reg['cnpj_fornecedor']),
                 int(reg['ano']), int(reg['semana']))
        if chave in chaves_com_ajuste:
            continue
        if chave not in vistos:
            vistos.add(chave)
            registros_unicos.append(reg)

    if not registros_unicos:
        conn.commit()
        return len(registros)

    valores = [
        (
            reg['cod_produto'], reg['cnpj_fornecedor'], reg['cod_empresa'],
            reg['ano'], None,  # mes = NULL para semanal
            reg['semana'], reg['tipo_granularidade'], reg['data_inicio_semana'],
            reg['demanda_prevista'], reg['demanda_diaria_base'], reg['desvio_padrao'],
            reg['fator_sazonal'], reg['fator_tendencia_yoy'], reg['classificacao_tendencia'],
            reg['valor_ano_anterior'], reg['variacao_vs_aa'],
            reg['limitador_aplicado'], reg['metodo_usado'], reg['categoria_serie'],
            reg['dias_historico'], reg['total_vendido_historico'],
            # V51: Metadata de demanda censurada
            reg.get('taxa_disponibilidade'),
            reg.get('dias_ruptura', 0),
            reg.get('demanda_censurada_corrigida', False)
        )
        for reg in registros_unicos
    ]

    execute_values(cursor, """
        INSERT INTO demanda_pre_calculada (
            cod_produto, cnpj_fornecedor, cod_empresa,
            ano, mes,
            semana, tipo_granularidade, data_inicio_semana,
            demanda_prevista, demanda_diaria_base, desvio_padrao,
            fator_sazonal, fator_tendencia_yoy, classificacao_tendencia,
            valor_ano_anterior, variacao_vs_aa,
            limitador_aplicado, metodo_usado, categoria_serie,
            dias_historico, total_vendido_historico,
            taxa_disponibilidade, dias_ruptura, demanda_censurada_corrigida,
            data_calculo
        ) VALUES %s
    """, valores, template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())")

    conn.commit()
    return len(registros)


def calcular_demanda_item_com_cache(
    cod_produto: int,
    cnpj_fornecedor: str,
    serie: List[float],
    meta_hist: Dict,
    ano_base: int,
    estoque_por_data: Dict = None
) -> List[Dict]:
    """
    Calcula demanda para um item usando historico pre-carregado.
    OTIMIZADO: Nao faz query no banco, usa dados do cache.
    V48: Deteccao de outliers antes do calculo.
    V51: Correcao de demanda censurada antes do calculo.
    """
    if not serie or len(serie) < 7:
        return []

    # V51: Correcao de demanda censurada ANTES de outliers
    meta_censura = {
        'dias_ruptura': 0,
        'dias_corrigidos': 0,
        'taxa_disponibilidade': None,
        'houve_correcao': False
    }
    serie_censurada = serie
    if estoque_por_data:
        vendas_por_data = meta_hist.get('vendas_por_data', {})
        vendas_por_loja = meta_hist.get('vendas_por_loja', None)  # V53
        if vendas_por_data:
            serie_censurada, meta_censura = corrigir_demanda_censurada(
                serie, vendas_por_data, estoque_por_data,
                vendas_por_loja=vendas_por_loja  # V53
            )

    # V48: Deteccao e tratamento de outliers ANTES do calculo
    outlier_info = None
    serie_limpa = serie_censurada
    if len(serie_censurada) >= 30:  # Minimo para deteccao confiavel (1 mes de dados diarios)
        try:
            from core.outlier_detector import AutoOutlierDetector
            detector = AutoOutlierDetector()
            resultado_outliers = detector.analyze_and_clean(serie_censurada)
            if resultado_outliers['outliers_count'] > 0:
                serie_limpa = resultado_outliers['cleaned_data']
                outlier_info = {
                    'outliers_removidos': resultado_outliers['outliers_count'],
                    'metodo_deteccao': resultado_outliers['method_used'],
                    'tratamento': resultado_outliers['treatment'],
                    'confianca': resultado_outliers['confidence']
                }
        except Exception:
            pass  # Falha no detector nao deve bloquear o calculo

    # Calcular demanda usando DemandCalculator (com serie limpa)
    demanda_total, desvio_total, meta_calc = DemandCalculator.calcular_demanda_diaria_unificada(
        vendas_diarias=serie_limpa,
        dias_periodo=30,
        granularidade_exibicao='mensal'
    )

    demanda_diaria_base = meta_calc.get('demanda_diaria_base', 0)
    if demanda_diaria_base <= 0:
        return []

    # V53: Se houve correcao de censura, recalcular vendas_por_mes a partir da serie corrigida
    vendas_por_mes = meta_hist.get('vendas_por_mes', {})
    if meta_censura.get('houve_correcao') and serie_censurada != serie:
        vendas_por_data = meta_hist.get('vendas_por_data', {})
        datas_ordenadas = sorted(vendas_por_data.keys())
        if datas_ordenadas:
            from datetime import timedelta
            data_min = min(datas_ordenadas)
            data_max = max(datas_ordenadas)
            datas_serie = []
            d = data_min
            while d <= data_max:
                datas_serie.append(d)
                d += timedelta(days=1)
            if len(datas_serie) == len(serie_censurada):
                vendas_por_mes_corrigido = {}
                for i, data in enumerate(datas_serie):
                    chave = (data.year, data.month)
                    vendas_por_mes_corrigido[chave] = vendas_por_mes_corrigido.get(chave, 0) + serie_censurada[i]
                vendas_por_mes = vendas_por_mes_corrigido

    # Calcular fatores sazonais
    fatores_sazonais = calcular_fatores_sazonais(vendas_por_mes)
    fator_tendencia_yoy = 1.0
    classificacao_tendencia = 'nao_calculado'

    if vendas_por_mes:
        fator_tendencia_yoy, classificacao_tendencia, _ = calcular_fator_tendencia_yoy(
            vendas_por_mes, min_anos=2, fator_amortecimento=0.7
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

        fator_sazonal = fatores_sazonais.get(mes, 1.0)
        demanda_prevista = demanda_diaria_base * fator_sazonal * fator_tendencia_yoy * dias_mes

        # Valor ano anterior (vendas reais, nao corrigidas - limitador V11 opera sobre dados reais)
        ano_anterior = ano - 1
        vendas_por_mes_original = meta_hist.get('vendas_por_mes', {})
        valor_aa = vendas_por_mes_original.get((ano_anterior, mes), 0)

        # Aplicar limitador V11
        # V53: Quando houve correcao de censura e o valor_aa original e muito inferior
        # ao corrigido, o mes teve ruptura significativa — nao aplicar limitador pois
        # valor_aa original nao representa a demanda real do periodo
        limitador_aplicado = False
        _pular_limitador = False
        if meta_censura.get('houve_correcao'):
            valor_aa_corrigido = vendas_por_mes.get((ano_anterior, mes), 0)
            if valor_aa_corrigido > 0 and (valor_aa == 0 or valor_aa_corrigido / max(valor_aa, 1) > 2.0):
                _pular_limitador = True  # Mes com ruptura significativa

        if valor_aa > 0 and not _pular_limitador:
            variacao = demanda_prevista / valor_aa
            if fator_tendencia_yoy > 1.05 and variacao < 1.0:
                demanda_prevista = valor_aa * min(fator_tendencia_yoy, 1.4)
                limitador_aplicado = True
            elif variacao > 1.5:
                demanda_prevista = valor_aa * 1.5
                limitador_aplicado = True
            elif variacao < 0.6:
                demanda_prevista = valor_aa * 0.6
                limitador_aplicado = True

        variacao_vs_aa = (demanda_prevista / valor_aa) if valor_aa > 0 else None

        registros.append({
            'cod_produto': str(cod_produto),
            'cnpj_fornecedor': cnpj_fornecedor,
            'cod_empresa': None,
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
            'total_vendido_historico': round(meta_hist.get('total_vendido', 0), 2),
            # V51: Metadata de demanda censurada
            'taxa_disponibilidade': meta_censura.get('taxa_disponibilidade'),
            'dias_ruptura': meta_censura.get('dias_ruptura', 0),
            'demanda_censurada_corrigida': meta_censura.get('houve_correcao', False),
        })

    return registros


def processar_fornecedor(cnpj_fornecedor: str, nome_fornecedor: str) -> Dict:
    """
    Processa todos os itens de um fornecedor.
    OTIMIZADO: Pre-carrega historico em lote e salva em batch.

    FILTRO v6.2: Itens com situacao EN (Em Negociacao) ou FL (Fora de Linha)
    nao tem demanda calculada. O filtro e por loja especifica.
    """
    conn = None
    try:
        conn = obter_conexao()
        ano_base = datetime.now().year

        # Buscar itens do fornecedor
        itens = buscar_itens_fornecedor(conn, cnpj_fornecedor)
        if not itens:
            return {
                'cnpj': cnpj_fornecedor,
                'nome': nome_fornecedor,
                'itens': 0,
                'itens_filtrados_en_fl': 0,
                'registros': 0,
                'erros': 0,
                'sucesso': True
            }

        cod_produtos = [item['cod_produto'] for item in itens]

        # FILTRO EN/FL v6.2: Buscar itens bloqueados por loja
        itens_bloqueados = buscar_itens_bloqueados(conn, cnpj_fornecedor)
        total_lojas = buscar_total_lojas(conn)

        # Identificar itens bloqueados em TODAS as lojas (nao calcular demanda)
        itens_filtrados = 0
        itens_ativos = []
        for item in itens:
            cod_produto = item['cod_produto']
            lojas_bloqueadas = itens_bloqueados.get(cod_produto, set())

            # Se bloqueado em todas as lojas, nao calcular demanda
            if len(lojas_bloqueadas) >= total_lojas:
                itens_filtrados += 1
                logger.debug(f"  Item {cod_produto} filtrado (EN/FL em todas as lojas)")
            else:
                itens_ativos.append(item)

        if itens_filtrados > 0:
            logger.info(f"  {itens_filtrados} itens filtrados (EN/FL em todas as lojas)")

        # PRE-CARREGAR HISTORICO EM LOTE (apenas itens ativos)
        cod_produtos_ativos = [item['cod_produto'] for item in itens_ativos]
        logger.debug(f"  Pre-carregando historico de {len(cod_produtos_ativos)} itens ativos...")
        cache_historico = precarregar_historico_lote(conn, cod_produtos_ativos, cnpj_fornecedor)

        # V51: Pre-carregar estoque diario para correcao de demanda censurada
        cache_estoque = {}
        try:
            cache_estoque = precarregar_estoque_diario_lote(conn, cod_produtos_ativos)
            if cache_estoque:
                logger.debug(f"  Estoque diario carregado para {len(cache_estoque)} itens")
        except Exception as e:
            logger.debug(f"  Sem dados de estoque diario: {e}")

        # Processar itens usando cache
        todos_registros = []
        total_erros = 0

        for item in itens_ativos:
            try:
                cod_produto = item['cod_produto']
                serie, meta_hist = cache_historico.get(cod_produto, ([], {}))

                # V51: Passar estoque diario para correcao de censura
                estoque_item = cache_estoque.get(cod_produto, None)

                registros = calcular_demanda_item_com_cache(
                    cod_produto,
                    cnpj_fornecedor,
                    serie,
                    meta_hist,
                    ano_base,
                    estoque_por_data=estoque_item
                )
                todos_registros.extend(registros)
            except Exception as e:
                total_erros += 1
                logger.debug(f"Erro item {item['cod_produto']}: {e}")

        # SALVAR TODOS OS REGISTROS MENSAIS EM UM UNICO BATCH
        total_registros = 0
        if todos_registros:
            total_registros = salvar_demanda_batch(conn, todos_registros)

        # V55: CALCULAR E SALVAR DEMANDA SEMANAL (derivada da mensal)
        total_registros_semanais = 0
        try:
            # Construir mapa de registros mensais por item para o calculo semanal
            registros_mensais_por_item = {}
            for reg in todos_registros:
                cod = reg['cod_produto']
                if cod not in registros_mensais_por_item:
                    registros_mensais_por_item[cod] = []
                registros_mensais_por_item[cod].append(reg)

            cache_hist_semanal = precarregar_historico_semanal_lote(conn, cod_produtos_ativos)

            # V51: Pre-carregar estoque semanal para correcao censurada (pesos sazonais)
            cache_estoque_semanal = {}
            try:
                cache_estoque_semanal = precarregar_estoque_semanal_lote(conn, cod_produtos_ativos)
            except Exception:
                pass

            todos_registros_semanais = []
            for item in itens_ativos:
                try:
                    cod_produto = item['cod_produto']
                    # V53: cache retorna (consolidado, por_loja) tuple
                    hist_sem_data = cache_hist_semanal.get(cod_produto, ({}, {}))
                    if isinstance(hist_sem_data, tuple):
                        hist_sem, hist_sem_loja = hist_sem_data
                    else:
                        hist_sem = hist_sem_data
                        hist_sem_loja = {}
                    est_sem = cache_estoque_semanal.get(cod_produto, None)
                    # V55: Passar registros mensais para decomposicao
                    regs_mensais = registros_mensais_por_item.get(str(cod_produto), [])
                    registros_sem = calcular_demanda_item_semanal(
                        cod_produto, cnpj_fornecedor, hist_sem,
                        registros_mensais=regs_mensais,
                        estoque_semanal=est_sem,
                        vendas_semanal_por_loja=hist_sem_loja
                    )
                    todos_registros_semanais.extend(registros_sem)
                except Exception:
                    pass

            if todos_registros_semanais:
                total_registros_semanais = salvar_demanda_batch_semanal(conn, todos_registros_semanais)
        except Exception as e:
            logger.warning(f"  Erro no calculo semanal: {e}")

        return {
            'cnpj': cnpj_fornecedor,
            'nome': nome_fornecedor,
            'itens': len(itens),
            'itens_ativos': len(itens_ativos),
            'itens_filtrados_en_fl': itens_filtrados,
            'registros': total_registros,
            'registros_semanais': total_registros_semanais,
            'erros': total_erros,
            'sucesso': True
        }

    except Exception as e:
        logger.error(f"Erro processando fornecedor {cnpj_fornecedor}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'cnpj': cnpj_fornecedor,
            'nome': nome_fornecedor,
            'itens': 0,
            'itens_ativos': 0,
            'itens_filtrados_en_fl': 0,
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
