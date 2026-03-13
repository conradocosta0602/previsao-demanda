"""
Blueprint: Acuracia
Rotas: /acuracia, /api/acuracia/*
Painel de acuracia de previsao: WMAPE, BIAS, MAE
Compara demanda_pre_calculada (previsto) vs historico_vendas_diario (realizado)
"""

import json
from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection

acuracia_bp = Blueprint('acuracia', __name__)


def decimal_to_float(obj):
    """Converte Decimal para float para serializacao JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def format_result(result):
    """Formata resultado do banco convertendo Decimals."""
    if isinstance(result, dict):
        return {k: decimal_to_float(v) for k, v in result.items()}
    elif isinstance(result, list):
        return [format_result(r) for r in result]
    return decimal_to_float(result)


def parse_filtros_acuracia(req):
    """
    Parse filtros do request de forma robusta.
    Inclui curva_abc alem dos filtros padrao.
    """
    resultado = {
        'fornecedores': [],
        'categorias': [],
        'linhas3': [],
        'filiais': [],
        'curvas': []
    }

    def _parse_param(req, names):
        for name in names:
            raw = req.args.get(name, '')
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [v for v in parsed if v]
                    elif parsed:
                        return [parsed]
                except (json.JSONDecodeError, TypeError):
                    vals = req.args.getlist(name)
                    return [v for v in vals if v]
        return []

    resultado['fornecedores'] = _parse_param(req, ['fornecedor', 'fornecedores'])
    resultado['categorias'] = _parse_param(req, ['categoria', 'categorias'])
    resultado['linhas3'] = _parse_param(req, ['codigo_linha', 'linhas3'])
    resultado['curvas'] = _parse_param(req, ['curva_abc', 'curvas'])

    # Filiais (int)
    raw = req.args.get('cod_empresa') or req.args.get('filiais', '')
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                resultado['filiais'] = [int(v) for v in parsed if v]
            elif parsed:
                resultado['filiais'] = [int(parsed)]
        except (json.JSONDecodeError, TypeError, ValueError):
            vals = req.args.getlist('cod_empresa') or req.args.getlist('filiais')
            resultado['filiais'] = [int(v) for v in vals if v]

    return resultado


def build_cte_comparacao(meses, filtros):
    """
    Constroi a CTE 'comparacao' parametrizada.
    Retorna (sql_string, params_list).

    A CTE faz JOIN entre demanda_pre_calculada (previsto) e
    historico_vendas_diario agregado por mes (realizado).
    Apenas meses completos do passado.
    """
    # Calcular data de inicio (N meses atras, primeiro dia do mes)
    hoje = datetime.now()
    # Voltar N meses: calcular mes/ano de inicio
    mes_inicio = hoje.month - meses
    ano_inicio = hoje.year
    while mes_inicio <= 0:
        mes_inicio += 12
        ano_inicio -= 1
    data_inicio = f"{ano_inicio}-{mes_inicio:02d}-01"

    # Filtros WHERE adicionais
    where_parts = []
    params = [data_inicio]  # %(data_inicio)s

    if filtros['fornecedores']:
        placeholders = ','.join(['%s'] * len(filtros['fornecedores']))
        where_parts.append(f"cpc.nome_fornecedor IN ({placeholders})")
        params.extend(filtros['fornecedores'])

    if filtros['categorias']:
        placeholders = ','.join(['%s'] * len(filtros['categorias']))
        where_parts.append(f"cpc.categoria IN ({placeholders})")
        params.extend(filtros['categorias'])

    if filtros['linhas3']:
        placeholders = ','.join(['%s'] * len(filtros['linhas3']))
        where_parts.append(f"cpc.codigo_linha IN ({placeholders})")
        params.extend(filtros['linhas3'])

    # Filtro por filiais: aplicado na CTE realizado_mensal (filtra lojas nas vendas)
    filial_filter = ""
    if filtros['filiais']:
        placeholders = ','.join(['%s'] * len(filtros['filiais']))
        filial_filter = f"AND hvd.cod_empresa IN ({placeholders})"
        params.extend(filtros['filiais'])

    if filtros['curvas']:
        placeholders = ','.join(['%s'] * len(filtros['curvas']))
        where_parts.append(f"COALESCE(epa.curva_abc, 'B') IN ({placeholders})")
        params.extend(filtros['curvas'])

    filtros_where = ""
    if where_parts:
        filtros_where = "AND " + " AND ".join(where_parts)

    # NOTA: demanda_pre_calculada armazena dados CONSOLIDADOS (cod_empresa IS NULL).
    # Portanto, agregamos vendas tambem de forma consolidada (SUM por item, sem loja).
    # Se o usuario filtrar por filial, filtramos as vendas ANTES de consolidar.
    cte_sql = f"""
    WITH realizado_mensal AS (
        SELECT
            hvd.codigo,
            EXTRACT(YEAR FROM hvd.data)::int AS ano,
            EXTRACT(MONTH FROM hvd.data)::int AS mes,
            SUM(hvd.qtd_venda) AS qtd_realizada
        FROM historico_vendas_diario hvd
        WHERE hvd.data >= %s
          AND hvd.data < DATE_TRUNC('month', CURRENT_DATE)
          AND hvd.cod_empresa < 80
          {filial_filter}
        GROUP BY hvd.codigo,
                 EXTRACT(YEAR FROM hvd.data), EXTRACT(MONTH FROM hvd.data)
    ),
    comparacao AS (
        SELECT
            dpc.cod_produto,
            dpc.cnpj_fornecedor,
            dpc.ano,
            dpc.mes,
            COALESCE(dpc.ajuste_manual, dpc.demanda_prevista) AS qtd_prevista,
            rm.qtd_realizada,
            dpc.metodo_usado,
            cpc.nome_fornecedor,
            cpc.categoria,
            cpc.codigo_linha,
            cpc.descricao AS descricao_item,
            COALESCE(epa.curva_abc, 'B') AS curva_abc
        FROM demanda_pre_calculada dpc
        INNER JOIN realizado_mensal rm
            ON dpc.cod_produto = rm.codigo::text
            AND dpc.ano = rm.ano
            AND dpc.mes = rm.mes
        LEFT JOIN cadastro_produtos_completo cpc
            ON dpc.cod_produto = cpc.cod_produto
        LEFT JOIN LATERAL (
            SELECT curva_abc FROM estoque_posicao_atual
            WHERE codigo::text = dpc.cod_produto
            LIMIT 1
        ) epa ON true
        WHERE dpc.demanda_prevista > 0
          AND rm.qtd_realizada >= 2
          AND COALESCE(dpc.tipo_granularidade, 'mensal') = 'mensal'
          {filtros_where}
    )
    """

    return cte_sql, params


@acuracia_bp.route('/acuracia')
def acuracia_page():
    """Pagina de acuracia de previsao."""
    return render_template('acuracia.html')


@acuracia_bp.route('/api/acuracia/filtros', methods=['GET'])
def api_acuracia_filtros():
    """Retorna opcoes de filtros para a tela de acuracia."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT DISTINCT nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE nome_fornecedor IS NOT NULL AND TRIM(nome_fornecedor) != ''
            ORDER BY nome_fornecedor
        """)
        fornecedores = [r['nome_fornecedor'] for r in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT categoria
            FROM cadastro_produtos_completo
            WHERE categoria IS NOT NULL AND categoria != ''
            ORDER BY categoria
        """)
        categorias = [r['categoria'] for r in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT categoria, codigo_linha, descricao_linha
            FROM cadastro_produtos_completo
            WHERE codigo_linha IS NOT NULL AND codigo_linha != ''
            AND categoria IS NOT NULL
            ORDER BY categoria, descricao_linha
        """)
        linhas3_rows = cursor.fetchall()

        linhas3_por_categoria = {}
        for r in linhas3_rows:
            cat = r['categoria']
            if cat not in linhas3_por_categoria:
                linhas3_por_categoria[cat] = []
            linhas3_por_categoria[cat].append({
                'codigo': r['codigo_linha'],
                'descricao': r['descricao_linha'] or r['codigo_linha']
            })

        cursor.execute("""
            SELECT cod_empresa, nome_loja
            FROM cadastro_lojas
            WHERE ativo = TRUE
            ORDER BY cod_empresa
        """)
        filiais = [{'codigo': r['cod_empresa'], 'nome': r['nome_loja']} for r in cursor.fetchall()]

        # Curvas ABC distintas
        cursor.execute("""
            SELECT DISTINCT curva_abc
            FROM estoque_posicao_atual
            WHERE curva_abc IS NOT NULL AND curva_abc != ''
            ORDER BY curva_abc
        """)
        curvas = [r['curva_abc'] for r in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({
            'fornecedores': fornecedores,
            'categorias': categorias,
            'linhas3_por_categoria': linhas3_por_categoria,
            'filiais': filiais,
            'curvas': curvas if curvas else ['A', 'B', 'C']
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_acuracia_filtros: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@acuracia_bp.route('/api/acuracia/resumo', methods=['GET'])
def api_acuracia_resumo():
    """
    Retorna resumo de acuracia: WMAPE, BIAS, MAE + distribuicao por faixa.
    Inclui variacao vs periodo anterior.
    """
    conn = None
    try:
        filtros = parse_filtros_acuracia(request)
        meses = request.args.get('meses', default=6, type=int)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # --- Periodo atual ---
        cte_sql, cte_params = build_cte_comparacao(meses, filtros)

        query_resumo = cte_sql + """
        SELECT
            COUNT(*) AS total_comparacoes,
            COUNT(DISTINCT cod_produto) AS total_itens,
            ROUND(
                SUM(ABS(qtd_realizada - qtd_prevista))::numeric
                / NULLIF(SUM(qtd_realizada), 0) * 100
            , 2) AS wmape,
            ROUND(
                SUM(qtd_prevista - qtd_realizada)::numeric
                / NULLIF(SUM(qtd_realizada), 0) * 100
            , 2) AS bias_pct,
            ROUND(AVG(ABS(qtd_realizada - qtd_prevista)), 2) AS mae
        FROM comparacao
        """
        cursor.execute(query_resumo, cte_params)
        resumo = format_result(cursor.fetchone() or {})

        # Distribuicao WMAPE por item
        query_dist = cte_sql + """
        SELECT
            SUM(CASE WHEN item_wmape < 10 THEN 1 ELSE 0 END) AS excelente,
            SUM(CASE WHEN item_wmape >= 10 AND item_wmape < 20 THEN 1 ELSE 0 END) AS boa,
            SUM(CASE WHEN item_wmape >= 20 AND item_wmape < 30 THEN 1 ELSE 0 END) AS aceitavel,
            SUM(CASE WHEN item_wmape >= 30 AND item_wmape < 50 THEN 1 ELSE 0 END) AS fraca,
            SUM(CASE WHEN item_wmape >= 50 THEN 1 ELSE 0 END) AS muito_fraca
        FROM (
            SELECT
                cod_produto,
                ROUND(
                    SUM(ABS(qtd_realizada - qtd_prevista))::numeric
                    / NULLIF(SUM(qtd_realizada), 0) * 100
                , 2) AS item_wmape
            FROM comparacao
            GROUP BY cod_produto
            HAVING SUM(qtd_realizada) > 0
        ) sub
        """
        cursor.execute(query_dist, cte_params)
        dist = format_result(cursor.fetchone() or {})

        # --- Periodo anterior (para variacao) ---
        cte_ant_sql, cte_ant_params = build_cte_comparacao(meses * 2, filtros)

        # Calcular limites do periodo anterior
        hoje = datetime.now()
        mes_fim_ant = hoje.month - meses
        ano_fim_ant = hoje.year
        while mes_fim_ant <= 0:
            mes_fim_ant += 12
            ano_fim_ant -= 1

        query_ant = cte_ant_sql + """
        SELECT
            ROUND(
                SUM(ABS(qtd_realizada - qtd_prevista))::numeric
                / NULLIF(SUM(qtd_realizada), 0) * 100
            , 2) AS wmape,
            ROUND(
                SUM(qtd_prevista - qtd_realizada)::numeric
                / NULLIF(SUM(qtd_realizada), 0) * 100
            , 2) AS bias_pct
        FROM comparacao
        WHERE (ano < %s OR (ano = %s AND mes < %s))
        """
        cursor.execute(query_ant, cte_ant_params + [ano_fim_ant, ano_fim_ant, mes_fim_ant])
        resumo_ant = format_result(cursor.fetchone() or {})

        cursor.close()
        conn.close()

        # Classificacao WMAPE
        wmape_val = resumo.get('wmape') or 0
        if wmape_val < 10:
            classificacao = 'Excelente'
        elif wmape_val < 20:
            classificacao = 'Boa'
        elif wmape_val < 30:
            classificacao = 'Aceitavel'
        elif wmape_val < 50:
            classificacao = 'Fraca'
        else:
            classificacao = 'Muito Fraca'

        # Direcao BIAS
        bias_val = resumo.get('bias_pct') or 0
        if bias_val > 2:
            direcao = 'superestimando'
        elif bias_val < -2:
            direcao = 'subestimando'
        else:
            direcao = 'equilibrado'

        # Variacoes
        wmape_ant = resumo_ant.get('wmape') or 0
        bias_ant = resumo_ant.get('bias_pct') or 0
        variacao_wmape = round(wmape_val - wmape_ant, 2) if wmape_ant else 0
        variacao_bias = round(bias_val - bias_ant, 2) if bias_ant else 0

        # Periodo texto
        hoje = datetime.now()
        mes_ini = hoje.month - meses
        ano_ini = hoje.year
        while mes_ini <= 0:
            mes_ini += 12
            ano_ini -= 1
        meses_nomes = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        mes_fim = hoje.month - 1 if hoje.month > 1 else 12
        ano_fim = hoje.year if hoje.month > 1 else hoje.year - 1
        periodo_texto = f"{meses_nomes[mes_ini]}/{str(ano_ini)[2:]} a {meses_nomes[mes_fim]}/{str(ano_fim)[2:]}"

        return jsonify({
            'periodo': periodo_texto,
            'meses_analisados': meses,
            'total_itens': resumo.get('total_itens') or 0,
            'total_comparacoes': resumo.get('total_comparacoes') or 0,
            'wmape': {
                'valor': wmape_val,
                'variacao': variacao_wmape,
                'classificacao': classificacao,
                'periodo': f'Ultimos {meses} meses'
            },
            'bias': {
                'valor': bias_val,
                'variacao': variacao_bias,
                'direcao': direcao,
                'periodo': f'Ultimos {meses} meses'
            },
            'mae': {
                'valor': resumo.get('mae') or 0
            },
            'distribuicao_wmape': {
                'excelente': dist.get('excelente') or 0,
                'boa': dist.get('boa') or 0,
                'aceitavel': dist.get('aceitavel') or 0,
                'fraca': dist.get('fraca') or 0,
                'muito_fraca': dist.get('muito_fraca') or 0
            }
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_acuracia_resumo: {e}")
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'erro': str(e)}), 500


@acuracia_bp.route('/api/acuracia/evolucao', methods=['GET'])
def api_acuracia_evolucao():
    """
    Retorna dados de evolucao mensal de WMAPE e BIAS para grafico.
    """
    conn = None
    try:
        filtros = parse_filtros_acuracia(request)
        meses = request.args.get('meses', default=12, type=int)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cte_sql, cte_params = build_cte_comparacao(meses, filtros)

        query = cte_sql + """
        SELECT
            ano,
            mes,
            ROUND(
                SUM(ABS(qtd_realizada - qtd_prevista))::numeric
                / NULLIF(SUM(qtd_realizada), 0) * 100
            , 2) AS wmape,
            ROUND(
                SUM(qtd_prevista - qtd_realizada)::numeric
                / NULLIF(SUM(qtd_realizada), 0) * 100
            , 2) AS bias_pct,
            COUNT(DISTINCT cod_produto) AS total_itens,
            SUM(qtd_realizada)::numeric AS total_realizado
        FROM comparacao
        GROUP BY ano, mes
        ORDER BY ano, mes
        """
        cursor.execute(query, cte_params)
        rows = format_result(cursor.fetchall())

        cursor.close()
        conn.close()

        meses_nomes = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                       'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        evolucao = []
        for r in rows:
            ano = r.get('ano', 0)
            mes = r.get('mes', 0)
            evolucao.append({
                'periodo': f"{mes:02d}/{ano}",
                'periodo_label': f"{meses_nomes[mes]}/{str(ano)[2:]}",
                'wmape': r.get('wmape') or 0,
                'bias_pct': r.get('bias_pct') or 0,
                'total_itens': r.get('total_itens') or 0,
                'total_realizado': r.get('total_realizado') or 0
            })

        return jsonify({'evolucao': evolucao})

    except Exception as e:
        import traceback
        print(f"[ERRO] api_acuracia_evolucao: {e}")
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'erro': str(e)}), 500


@acuracia_bp.route('/api/acuracia/ranking', methods=['GET'])
def api_acuracia_ranking():
    """
    Retorna ranking de acuracia por agregacao (fornecedor, categoria, curva, item).
    """
    conn = None
    try:
        filtros = parse_filtros_acuracia(request)
        meses = request.args.get('meses', default=6, type=int)
        agregacao = request.args.get('agregacao', 'fornecedor')
        ordenar_por = request.args.get('ordenar_por', 'wmape')
        ordem = request.args.get('ordem', 'desc')
        pagina = request.args.get('pagina', default=1, type=int)
        por_pagina = request.args.get('por_pagina', default=20, type=int)

        # Validar
        if agregacao not in ('fornecedor', 'categoria', 'curva', 'item'):
            agregacao = 'fornecedor'
        if ordenar_por not in ('wmape', 'bias_pct', 'mae'):
            ordenar_por = 'wmape'
        ordem_sql = 'DESC' if ordem.lower() == 'desc' else 'ASC'

        # Para WMAPE, "pior" = maior, entao DESC faz sentido como default
        # Para BIAS, o usuario pode querer ver maior superestimacao ou subestimacao
        col_order = {
            'wmape': 'wmape',
            'bias_pct': 'ABS(bias_pct)',
            'mae': 'mae'
        }.get(ordenar_por, 'wmape')

        offset = (pagina - 1) * por_pagina

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cte_sql, cte_params = build_cte_comparacao(meses, filtros)

        # Mapear agregacao para GROUP BY e SELECT
        if agregacao == 'fornecedor':
            group_col = 'nome_fornecedor'
            select_id = 'nome_fornecedor AS identificador'
            select_metodo = ''
        elif agregacao == 'categoria':
            group_col = 'categoria'
            select_id = 'categoria AS identificador'
            select_metodo = ''
        elif agregacao == 'curva':
            group_col = 'curva_abc'
            select_id = 'curva_abc AS identificador'
            select_metodo = ''
        else:  # item
            group_col = 'cod_produto, descricao_item, nome_fornecedor'
            select_id = 'cod_produto AS identificador, descricao_item, nome_fornecedor'
            select_metodo = ', MODE() WITHIN GROUP (ORDER BY metodo_usado) AS metodo_predominante'

        query = cte_sql + f"""
        SELECT
            {select_id},
            ROUND(
                SUM(ABS(qtd_realizada - qtd_prevista))::numeric
                / NULLIF(SUM(qtd_realizada), 0) * 100
            , 2) AS wmape,
            ROUND(
                SUM(qtd_prevista - qtd_realizada)::numeric
                / NULLIF(SUM(qtd_realizada), 0) * 100
            , 2) AS bias_pct,
            ROUND(AVG(ABS(qtd_realizada - qtd_prevista)), 2) AS mae,
            COUNT(DISTINCT cod_produto) AS total_itens,
            SUM(qtd_realizada)::numeric AS total_realizado
            {select_metodo}
        FROM comparacao
        GROUP BY {group_col}
        HAVING SUM(qtd_realizada) > 0
        ORDER BY {col_order} {ordem_sql} NULLS LAST
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, cte_params + [por_pagina, offset])
        ranking = format_result(cursor.fetchall())

        # Contagem total
        count_query = cte_sql + f"""
        SELECT COUNT(*) AS total FROM (
            SELECT 1 FROM comparacao
            GROUP BY {group_col}
            HAVING SUM(qtd_realizada) > 0
        ) sub
        """
        cursor.execute(count_query, cte_params)
        total = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        # Formatar itens
        itens = []
        for r in ranking:
            item = {
                'identificador': r.get('identificador') or '',
                'wmape': r.get('wmape') or 0,
                'bias_pct': r.get('bias_pct') or 0,
                'mae': r.get('mae') or 0,
                'total_itens': r.get('total_itens') or 0,
                'total_realizado': r.get('total_realizado') or 0,
                'metodo_predominante': r.get('metodo_predominante') or ''
            }
            if agregacao == 'item':
                item['descricao'] = r.get('descricao_item') or ''
                item['fornecedor'] = r.get('nome_fornecedor') or ''
            itens.append(item)

        total_paginas = (total + por_pagina - 1) // por_pagina if total > 0 else 1

        return jsonify({
            'itens': itens,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total': total,
            'total_paginas': total_paginas
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_acuracia_ranking: {e}")
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'erro': str(e)}), 500
