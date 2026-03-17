"""
Blueprint: KPIs
Rotas: /kpis, /api/kpis/*
Painel de indicadores: Ruptura, Cobertura Media, Excesso
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection

kpis_bp = Blueprint('kpis', __name__)


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


def parse_filtros(req):
    """
    Parse filtros do request de forma robusta.
    Aceita tanto JSON.stringify (frontend antigo) quanto getlist (padrao).
    Retorna dict com listas de valores.
    """
    resultado = {
        'fornecedores': [],
        'categorias': [],
        'linhas3': [],
        'filiais': []
    }

    # Fornecedores
    raw = req.args.get('fornecedor') or req.args.get('fornecedores', '')
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                resultado['fornecedores'] = [v for v in parsed if v]
            elif parsed:
                resultado['fornecedores'] = [parsed]
        except (json.JSONDecodeError, TypeError):
            vals = req.args.getlist('fornecedor') or req.args.getlist('fornecedores')
            resultado['fornecedores'] = [v for v in vals if v]

    # Categorias
    raw = req.args.get('categoria') or req.args.get('categorias', '')
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                resultado['categorias'] = [v for v in parsed if v]
            elif parsed:
                resultado['categorias'] = [parsed]
        except (json.JSONDecodeError, TypeError):
            vals = req.args.getlist('categoria') or req.args.getlist('categorias')
            resultado['categorias'] = [v for v in vals if v]

    # Linhas3
    raw = req.args.get('codigo_linha') or req.args.get('linhas3', '')
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                resultado['linhas3'] = [v for v in parsed if v]
            elif parsed:
                resultado['linhas3'] = [parsed]
        except (json.JSONDecodeError, TypeError):
            vals = req.args.getlist('codigo_linha') or req.args.getlist('linhas3')
            resultado['linhas3'] = [v for v in vals if v]

    # Filiais
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


def build_where_clauses(filtros, prefixo_estoque='hed'):
    """
    Constroi clausulas WHERE e params a partir dos filtros parseados.
    Retorna (clauses_list, params_list, precisa_cpc).
    """
    clauses = []
    params = []
    precisa_cpc = False

    if filtros['fornecedores']:
        placeholders = ','.join(['%s'] * len(filtros['fornecedores']))
        clauses.append(f"cpc.nome_fornecedor IN ({placeholders})")
        params.extend(filtros['fornecedores'])
        precisa_cpc = True

    if filtros['categorias']:
        placeholders = ','.join(['%s'] * len(filtros['categorias']))
        clauses.append(f"cpc.categoria IN ({placeholders})")
        params.extend(filtros['categorias'])
        precisa_cpc = True

    if filtros['linhas3']:
        placeholders = ','.join(['%s'] * len(filtros['linhas3']))
        clauses.append(f"cpc.codigo_linha IN ({placeholders})")
        params.extend(filtros['linhas3'])
        precisa_cpc = True

    if filtros['filiais']:
        placeholders = ','.join(['%s'] * len(filtros['filiais']))
        clauses.append(f"{prefixo_estoque}.cod_empresa IN ({placeholders})")
        params.extend(filtros['filiais'])

    return clauses, params, precisa_cpc


def get_dias_from_visao(req):
    """Retorna numero de dias baseado na visao temporal."""
    visao = req.args.get('visao', 'mensal')
    dias_param = req.args.get('dias', type=int)
    if dias_param:
        return dias_param
    if visao == 'diario':
        return 30
    elif visao == 'semanal':
        return 180
    return 365  # mensal


@kpis_bp.route('/kpis')
def kpis_page():
    """Pagina de indicadores de desempenho (KPIs)"""
    return render_template('kpis.html')


@kpis_bp.route('/api/kpis/filtros', methods=['GET'])
def api_kpis_filtros():
    """Retorna opcoes de filtros para a tela de KPIs."""
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

        cursor.close()
        conn.close()

        return jsonify({
            'fornecedores': fornecedores,
            'categorias': categorias,
            'linhas3_por_categoria': linhas3_por_categoria,
            'filiais': filiais
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_filtros: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@kpis_bp.route('/api/kpis/resumo', methods=['GET'])
def api_kpis_resumo():
    """
    Retorna resumo atual dos KPIs: Ruptura, Cobertura Media, Excesso.
    """
    conn = None
    try:
        filtros = parse_filtros(request)
        dias = get_dias_from_visao(request)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        where_clauses, where_params, precisa_cpc = build_where_clauses(filtros, 'hed')

        # =====================================================================
        # KPI 1: RUPTURA
        # =====================================================================
        filtro_sql = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""
        join_cpc = "LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto" if precisa_cpc else ""

        query_ruptura = f"""
            SELECT
                COUNT(DISTINCT (hed.codigo, hed.cod_empresa)) as total_itens,
                SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as total_dias_ruptura,
                COUNT(*) as total_pontos_abastecimento,
                CASE WHEN COUNT(*) > 0
                    THEN ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2)
                    ELSE 0 END as taxa_ruptura
            FROM historico_estoque_diario hed
            INNER JOIN estoque_posicao_atual epa ON hed.codigo = epa.codigo AND hed.cod_empresa = epa.cod_empresa
            {join_cpc}
            LEFT JOIN situacao_compra_itens sci
                ON hed.codigo = sci.codigo AND hed.cod_empresa = sci.cod_empresa
            WHERE hed.data >= %s
            AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
            {filtro_sql}
        """
        try:
            cursor.execute(query_ruptura, [data_inicio] + where_params)
            ruptura = cursor.fetchone() or {}
        except Exception as e:
            print(f"[ERRO] Query Ruptura: {e}")
            conn.rollback()
            ruptura = {'taxa_ruptura': 0, 'total_itens': 0, 'total_pontos_abastecimento': 0, 'total_dias_ruptura': 0}

        # Ruptura periodo anterior
        data_inicio_anterior = (datetime.now() - timedelta(days=dias*2)).strftime('%Y-%m-%d')
        data_fim_anterior = data_inicio

        query_ruptura_ant = f"""
            SELECT
                CASE WHEN COUNT(*) > 0
                    THEN ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2)
                    ELSE 0 END as taxa_ruptura
            FROM historico_estoque_diario hed
            INNER JOIN estoque_posicao_atual epa ON hed.codigo = epa.codigo AND hed.cod_empresa = epa.cod_empresa
            {join_cpc}
            LEFT JOIN situacao_compra_itens sci
                ON hed.codigo = sci.codigo AND hed.cod_empresa = sci.cod_empresa
            WHERE hed.data >= %s AND hed.data < %s
            AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
            {filtro_sql}
        """
        try:
            cursor.execute(query_ruptura_ant, [data_inicio_anterior, data_fim_anterior] + where_params)
            ruptura_ant = cursor.fetchone() or {}
        except Exception as e:
            print(f"[ERRO] Query Ruptura Anterior: {e}")
            conn.rollback()
            ruptura_ant = {'taxa_ruptura': 0}

        # =====================================================================
        # KPI 2: COBERTURA MEDIA (snapshot - dados atuais)
        # estoque_atual / (demanda_prevista / 30) ponderado por demanda
        # =====================================================================
        where_cob_clauses, where_cob_params, _ = build_where_clauses(filtros, 'epa')

        filtro_cob_sql = (" AND " + " AND ".join(where_cob_clauses)) if where_cob_clauses else ""

        query_cobertura = f"""
            WITH cobertura_item AS (
                SELECT
                    epa.codigo,
                    epa.cod_empresa,
                    epa.estoque,
                    COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 as demanda_diaria,
                    CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                        THEN epa.estoque / (COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0)
                        ELSE NULL END as dias_cobertura
                FROM estoque_posicao_atual epa
                INNER JOIN demanda_pre_calculada d
                    ON epa.codigo::text = d.cod_produto
                    AND epa.cod_empresa = COALESCE(d.cod_empresa, epa.cod_empresa)
                    AND d.ano = EXTRACT(YEAR FROM CURRENT_DATE)::int
                    AND d.mes = EXTRACT(MONTH FROM CURRENT_DATE)::int
                LEFT JOIN cadastro_produtos_completo cpc ON epa.codigo::text = cpc.cod_produto
                LEFT JOIN situacao_compra_itens sci
                    ON epa.codigo = sci.codigo AND epa.cod_empresa = sci.cod_empresa
                WHERE COALESCE(d.ajuste_manual, d.demanda_prevista) > 0
                AND epa.cod_empresa < 80
                AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
                {filtro_cob_sql}
            )
            SELECT
                ROUND(SUM(estoque)::numeric / NULLIF(SUM(demanda_diaria), 0), 1) as cobertura_media,
                COUNT(*) as total_itens
            FROM cobertura_item
            WHERE dias_cobertura IS NOT NULL
        """
        try:
            cursor.execute(query_cobertura, where_cob_params)
            cobertura = cursor.fetchone() or {}
        except Exception as e:
            print(f"[ERRO] Query Cobertura: {e}")
            conn.rollback()
            cobertura = {'cobertura_media': 0, 'total_itens': 0}

        # Cobertura periodo anterior (usando historico_estoque_diario do ultimo dia do periodo anterior)
        query_cobertura_ant = f"""
            WITH ultimo_dia AS (
                SELECT MAX(data) as data FROM historico_estoque_diario WHERE data < %s AND data >= %s
            ),
            cobertura_ant AS (
                SELECT
                    hed.codigo, hed.cod_empresa,
                    hed.estoque_diario as estoque,
                    COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 as demanda_diaria
                FROM historico_estoque_diario hed
                INNER JOIN ultimo_dia ud ON hed.data = ud.data
                INNER JOIN demanda_pre_calculada d
                    ON hed.codigo::text = d.cod_produto
                    AND hed.cod_empresa = COALESCE(d.cod_empresa, hed.cod_empresa)
                    AND d.ano = EXTRACT(YEAR FROM hed.data)::int
                    AND d.mes = EXTRACT(MONTH FROM hed.data)::int
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                LEFT JOIN situacao_compra_itens sci
                    ON hed.codigo = sci.codigo AND hed.cod_empresa = sci.cod_empresa
                WHERE COALESCE(d.ajuste_manual, d.demanda_prevista) > 0
                AND hed.cod_empresa < 80
                AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
                {filtro_cob_sql}
            )
            SELECT
                ROUND(SUM(estoque)::numeric / NULLIF(SUM(demanda_diaria), 0), 1) as cobertura_media
            FROM cobertura_ant
        """
        try:
            cursor.execute(query_cobertura_ant, [data_inicio, data_inicio_anterior] + where_cob_params)
            cobertura_ant = cursor.fetchone() or {}
        except Exception as e:
            print(f"[ERRO] Query Cobertura Anterior: {e}")
            conn.rollback()
            cobertura_ant = {'cobertura_media': 0}

        # =====================================================================
        # KPI 3: EXCESSO (snapshot - % itens com cobertura > 90 dias + faixas)
        # =====================================================================
        query_excesso = f"""
            WITH cobertura_item AS (
                SELECT
                    epa.codigo,
                    epa.cod_empresa,
                    CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                        THEN epa.estoque / (COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0)
                        ELSE NULL END as dias_cobertura
                FROM estoque_posicao_atual epa
                INNER JOIN demanda_pre_calculada d
                    ON epa.codigo::text = d.cod_produto
                    AND epa.cod_empresa = COALESCE(d.cod_empresa, epa.cod_empresa)
                    AND d.ano = EXTRACT(YEAR FROM CURRENT_DATE)::int
                    AND d.mes = EXTRACT(MONTH FROM CURRENT_DATE)::int
                LEFT JOIN cadastro_produtos_completo cpc ON epa.codigo::text = cpc.cod_produto
                LEFT JOIN situacao_compra_itens sci
                    ON epa.codigo = sci.codigo AND epa.cod_empresa = sci.cod_empresa
                WHERE COALESCE(d.ajuste_manual, d.demanda_prevista) > 0
                AND epa.cod_empresa < 80
                AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
                {filtro_cob_sql}
            )
            SELECT
                COUNT(*) as total_itens,
                SUM(CASE WHEN dias_cobertura > 90 THEN 1 ELSE 0 END) as itens_excesso,
                ROUND(SUM(CASE WHEN dias_cobertura > 90 THEN 1 ELSE 0 END)::numeric
                    / NULLIF(COUNT(*), 0) * 100, 1) as pct_excesso,
                SUM(CASE WHEN dias_cobertura > 90 AND dias_cobertura <= 120 THEN 1 ELSE 0 END) as faixa_90_120,
                SUM(CASE WHEN dias_cobertura > 120 AND dias_cobertura <= 180 THEN 1 ELSE 0 END) as faixa_120_180,
                SUM(CASE WHEN dias_cobertura > 180 THEN 1 ELSE 0 END) as faixa_acima_180
            FROM cobertura_item
            WHERE dias_cobertura IS NOT NULL
        """
        try:
            cursor.execute(query_excesso, where_cob_params)
            excesso = cursor.fetchone() or {}
        except Exception as e:
            print(f"[ERRO] Query Excesso: {e}")
            conn.rollback()
            excesso = {'pct_excesso': 0, 'total_itens': 0, 'itens_excesso': 0,
                       'faixa_90_120': 0, 'faixa_120_180': 0, 'faixa_acima_180': 0}

        # Excesso periodo anterior
        query_excesso_ant = f"""
            WITH ultimo_dia AS (
                SELECT MAX(data) as data FROM historico_estoque_diario WHERE data < %s AND data >= %s
            ),
            cobertura_ant AS (
                SELECT
                    hed.codigo, hed.cod_empresa,
                    CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                        THEN hed.estoque_diario / (COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0)
                        ELSE NULL END as dias_cobertura
                FROM historico_estoque_diario hed
                INNER JOIN ultimo_dia ud ON hed.data = ud.data
                INNER JOIN demanda_pre_calculada d
                    ON hed.codigo::text = d.cod_produto
                    AND hed.cod_empresa = COALESCE(d.cod_empresa, hed.cod_empresa)
                    AND d.ano = EXTRACT(YEAR FROM hed.data)::int
                    AND d.mes = EXTRACT(MONTH FROM hed.data)::int
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                LEFT JOIN situacao_compra_itens sci
                    ON hed.codigo = sci.codigo AND hed.cod_empresa = sci.cod_empresa
                WHERE COALESCE(d.ajuste_manual, d.demanda_prevista) > 0
                AND hed.cod_empresa < 80
                AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
                {filtro_cob_sql}
            )
            SELECT
                ROUND(SUM(CASE WHEN dias_cobertura > 90 THEN 1 ELSE 0 END)::numeric
                    / NULLIF(COUNT(*), 0) * 100, 1) as pct_excesso
            FROM cobertura_ant
            WHERE dias_cobertura IS NOT NULL
        """
        try:
            cursor.execute(query_excesso_ant, [data_inicio, data_inicio_anterior] + where_cob_params)
            excesso_ant = cursor.fetchone() or {}
        except Exception as e:
            print(f"[ERRO] Query Excesso Anterior: {e}")
            conn.rollback()
            excesso_ant = {'pct_excesso': 0}

        cursor.close()
        conn.close()

        # Calcular variacoes
        taxa_ruptura_atual = float(ruptura.get('taxa_ruptura') or 0)
        taxa_ruptura_anterior = float(ruptura_ant.get('taxa_ruptura') or 0)
        variacao_ruptura = round(taxa_ruptura_atual - taxa_ruptura_anterior, 2)

        cobertura_atual = float(cobertura.get('cobertura_media') or 0)
        cobertura_anterior = float(cobertura_ant.get('cobertura_media') or 0)
        variacao_cobertura = round(cobertura_atual - cobertura_anterior, 1)

        pct_excesso_atual = float(excesso.get('pct_excesso') or 0)
        pct_excesso_anterior = float(excesso_ant.get('pct_excesso') or 0)
        variacao_excesso = round(pct_excesso_atual - pct_excesso_anterior, 1)

        # Formatar periodo
        data_fim = datetime.now()
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        periodo_texto = f"{data_inicio_dt.strftime('%d/%m')} a {data_fim.strftime('%d/%m/%Y')}"

        return jsonify({
            'periodo': periodo_texto,
            'dias': dias,
            'ruptura': {
                'valor': taxa_ruptura_atual,
                'variacao': variacao_ruptura,
                'total_itens': ruptura.get('total_itens') or 0,
                'total_pontos': ruptura.get('total_pontos_abastecimento') or 0,
                'total_ruptura': ruptura.get('total_dias_ruptura') or 0,
                'periodo': f'Ultimos {dias} dias'
            },
            'cobertura': {
                'valor': cobertura_atual,
                'variacao': variacao_cobertura,
                'total_itens': cobertura.get('total_itens') or 0,
                'periodo': f'Posicao atual'
            },
            'excesso': {
                'valor': pct_excesso_atual,
                'variacao': variacao_excesso,
                'total_itens': excesso.get('total_itens') or 0,
                'itens_excesso': excesso.get('itens_excesso') or 0,
                'faixa_90_120': excesso.get('faixa_90_120') or 0,
                'faixa_120_180': excesso.get('faixa_120_180') or 0,
                'faixa_acima_180': excesso.get('faixa_acima_180') or 0,
                'periodo': f'Posicao atual'
            }
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_resumo: {e}")
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'erro': str(e)}), 500


@kpis_bp.route('/api/kpis/evolucao', methods=['GET'])
def api_kpis_evolucao():
    """
    Retorna dados de evolucao temporal dos KPIs para graficos.
    Granularidade: diario (30d), semanal (6m), mensal (12m)
    """
    conn = None
    try:
        granularidade = request.args.get('visao') or request.args.get('granularidade', 'mensal')
        filtros = parse_filtros(request)

        if granularidade == 'diario':
            dias = 30
            group_by = "hed.data"
        elif granularidade == 'semanal':
            dias = 180
            group_by = "DATE_TRUNC('week', hed.data)"
        else:
            dias = 365
            group_by = "DATE_TRUNC('month', hed.data)"

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        where_clauses, where_params, precisa_cpc = build_where_clauses(filtros, 'hed')

        filtro_sql = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""
        join_cpc = "LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto" if precisa_cpc else ""

        if granularidade == 'diario':
            period_format = f"TO_CHAR({group_by}, 'DD/MM')"
        elif granularidade == 'semanal':
            period_format = f"TO_CHAR({group_by}, 'DD/MM/YY')"
        else:
            period_format = f"TO_CHAR({group_by}, 'MM/YYYY')"

        # =====================================================================
        # EVOLUCAO RUPTURA
        # =====================================================================
        query_ruptura = f"""
            SELECT
                {group_by} as periodo,
                {period_format} as periodo_label,
                COUNT(*) as total_pontos,
                SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as pontos_ruptura,
                CASE WHEN COUNT(*) > 0
                    THEN ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2)
                    ELSE 0 END as taxa_ruptura
            FROM historico_estoque_diario hed
            INNER JOIN estoque_posicao_atual epa ON hed.codigo = epa.codigo AND hed.cod_empresa = epa.cod_empresa
            {join_cpc}
            LEFT JOIN situacao_compra_itens sci
                ON hed.codigo = sci.codigo AND hed.cod_empresa = sci.cod_empresa
            WHERE hed.data >= %s
            AND hed.cod_empresa < 80
            AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
            {filtro_sql}
            GROUP BY {group_by}
            ORDER BY {group_by}
        """
        cursor.execute(query_ruptura, [data_inicio] + where_params)
        evolucao_ruptura = format_result(cursor.fetchall())

        # =====================================================================
        # EVOLUCAO COBERTURA MEDIA
        # Estoque agregado / demanda agregada por periodo
        # =====================================================================
        query_cobertura = f"""
            SELECT
                {group_by} as periodo,
                {period_format} as periodo_label,
                ROUND(
                    SUM(hed.estoque_diario)::numeric
                    / NULLIF(SUM(COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0), 0)
                , 1) as cobertura_media
            FROM historico_estoque_diario hed
            INNER JOIN demanda_pre_calculada d
                ON hed.codigo::text = d.cod_produto
                AND hed.cod_empresa = COALESCE(d.cod_empresa, hed.cod_empresa)
                AND d.ano = EXTRACT(YEAR FROM hed.data)::int
                AND d.mes = EXTRACT(MONTH FROM hed.data)::int
            {join_cpc}
            LEFT JOIN situacao_compra_itens sci
                ON hed.codigo = sci.codigo AND hed.cod_empresa = sci.cod_empresa
            WHERE hed.data >= %s
            AND hed.cod_empresa < 80
            AND COALESCE(d.ajuste_manual, d.demanda_prevista) > 0
            AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
            {filtro_sql}
            GROUP BY {group_by}
            ORDER BY {group_by}
        """
        try:
            cursor.execute(query_cobertura, [data_inicio] + where_params)
            evolucao_cobertura = format_result(cursor.fetchall())
        except Exception as e:
            print(f"[ERRO] Query Evolucao Cobertura: {e}")
            conn.rollback()
            evolucao_cobertura = []

        # =====================================================================
        # EVOLUCAO EXCESSO (% itens com cobertura > 90 dias por periodo)
        # =====================================================================
        query_excesso = f"""
            SELECT
                {group_by} as periodo,
                {period_format} as periodo_label,
                COUNT(*) as total_itens,
                SUM(CASE WHEN hed.estoque_diario / NULLIF(COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0, 0) > 90
                    THEN 1 ELSE 0 END) as itens_excesso,
                ROUND(
                    SUM(CASE WHEN hed.estoque_diario / NULLIF(COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0, 0) > 90
                        THEN 1 ELSE 0 END)::numeric
                    / NULLIF(COUNT(*), 0) * 100
                , 1) as pct_excesso
            FROM historico_estoque_diario hed
            INNER JOIN demanda_pre_calculada d
                ON hed.codigo::text = d.cod_produto
                AND hed.cod_empresa = COALESCE(d.cod_empresa, hed.cod_empresa)
                AND d.ano = EXTRACT(YEAR FROM hed.data)::int
                AND d.mes = EXTRACT(MONTH FROM hed.data)::int
            {join_cpc}
            LEFT JOIN situacao_compra_itens sci
                ON hed.codigo = sci.codigo AND hed.cod_empresa = sci.cod_empresa
            WHERE hed.data >= %s
            AND hed.cod_empresa < 80
            AND COALESCE(d.ajuste_manual, d.demanda_prevista) > 0
            AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
            {filtro_sql}
            GROUP BY {group_by}
            ORDER BY {group_by}
        """
        try:
            cursor.execute(query_excesso, [data_inicio] + where_params)
            evolucao_excesso = format_result(cursor.fetchall())
        except Exception as e:
            print(f"[ERRO] Query Evolucao Excesso: {e}")
            conn.rollback()
            evolucao_excesso = []

        cursor.close()
        conn.close()

        # Formatar dados para o JavaScript
        valores_ruptura = [r.get('taxa_ruptura', 0) for r in evolucao_ruptura if r.get('taxa_ruptura') is not None]
        melhor_ruptura = min(valores_ruptura) if valores_ruptura else 0

        valores_cobertura = [r.get('cobertura_media', 0) for r in evolucao_cobertura if r.get('cobertura_media') is not None]

        valores_excesso = [r.get('pct_excesso', 0) for r in evolucao_excesso if r.get('pct_excesso') is not None]
        melhor_excesso = min(valores_excesso) if valores_excesso else 0

        def formatar_evolucao(dados, campo_valor, melhor_valor=None):
            resultado = []
            for d in dados:
                item = {
                    'periodo': d.get('periodo_label', ''),
                    'valor': d.get(campo_valor, 0)
                }
                if melhor_valor is not None:
                    item['melhor_historico'] = melhor_valor
                resultado.append(item)
            return resultado

        return jsonify({
            'ruptura': formatar_evolucao(evolucao_ruptura, 'taxa_ruptura', melhor_ruptura),
            'cobertura': formatar_evolucao(evolucao_cobertura, 'cobertura_media'),
            'excesso': formatar_evolucao(evolucao_excesso, 'pct_excesso', melhor_excesso)
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_evolucao: {e}")
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'erro': str(e)}), 500


@kpis_bp.route('/api/kpis/ranking', methods=['GET'])
def api_kpis_ranking():
    """
    Retorna ranking de itens/grupos por KPI.
    Inclui ruptura, cobertura e excesso.
    """
    conn = None
    try:
        ordenar_por = request.args.get('ordenar_por', 'ruptura')
        ordem = request.args.get('ordem', 'desc')
        agregacao = request.args.get('agregacao', 'item')
        pagina = request.args.get('pagina', default=1, type=int)
        por_pagina = request.args.get('por_pagina', default=20, type=int)
        dias = get_dias_from_visao(request)
        filtros = parse_filtros(request)

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        where_clauses, where_params, _ = build_where_clauses(filtros, 'hed')
        filtro_sql = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""

        # Validar ordenacao
        ordem_sql = "DESC" if ordem.lower() == 'desc' else "ASC"
        campos_validos = ['ruptura', 'cobertura', 'excesso']
        if ordenar_por not in campos_validos:
            ordenar_por = 'ruptura'

        # Mapear campo de ordenacao para coluna SQL
        col_ordenacao = {
            'ruptura': 'ruptura',
            'cobertura': 'cobertura',
            'excesso': 'pct_excesso'
        }.get(ordenar_por, 'ruptura')

        offset = (pagina - 1) * por_pagina

        if agregacao == 'item':
            query = f"""
                SELECT
                    hed.codigo,
                    cpc.descricao,
                    cpc.nome_fornecedor as fornecedor,
                    ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric
                        / NULLIF(COUNT(*), 0) * 100, 2) as ruptura,
                    ROUND(
                        AVG(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            THEN hed.estoque_diario / (COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0)
                            ELSE NULL END)
                    , 1) as cobertura,
                    ROUND(
                        SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            AND hed.estoque_diario / (COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0) > 90
                            THEN 1 ELSE 0 END)::numeric
                        / NULLIF(SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            THEN 1 ELSE 0 END), 0) * 100
                    , 1) as pct_excesso
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                LEFT JOIN demanda_pre_calculada d
                    ON hed.codigo::text = d.cod_produto
                    AND hed.cod_empresa = COALESCE(d.cod_empresa, hed.cod_empresa)
                    AND d.ano = EXTRACT(YEAR FROM hed.data)::int
                    AND d.mes = EXTRACT(MONTH FROM hed.data)::int
                WHERE hed.data >= %s
                AND hed.cod_empresa < 80
                {filtro_sql}
                GROUP BY hed.codigo, cpc.descricao, cpc.nome_fornecedor
                HAVING COUNT(*) >= 5
                ORDER BY {col_ordenacao} {ordem_sql} NULLS LAST
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, [data_inicio] + where_params + [por_pagina, offset])

        elif agregacao == 'fornecedor':
            query = f"""
                SELECT
                    cpc.nome_fornecedor as nome,
                    COUNT(*) as total_registros,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as registros_ruptura,
                    ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric
                        / NULLIF(COUNT(*), 0) * 100, 2) as ruptura,
                    ROUND(
                        SUM(hed.estoque_diario)::numeric
                        / NULLIF(SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            THEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 ELSE 0 END), 0)
                    , 1) as cobertura,
                    ROUND(
                        SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            AND hed.estoque_diario / (COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0) > 90
                            THEN 1 ELSE 0 END)::numeric
                        / NULLIF(SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            THEN 1 ELSE 0 END), 0) * 100
                    , 1) as pct_excesso
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                LEFT JOIN demanda_pre_calculada d
                    ON hed.codigo::text = d.cod_produto
                    AND hed.cod_empresa = COALESCE(d.cod_empresa, hed.cod_empresa)
                    AND d.ano = EXTRACT(YEAR FROM hed.data)::int
                    AND d.mes = EXTRACT(MONTH FROM hed.data)::int
                WHERE hed.data >= %s
                AND hed.cod_empresa < 80
                {filtro_sql}
                GROUP BY cpc.nome_fornecedor
                ORDER BY {col_ordenacao} {ordem_sql} NULLS LAST
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, [data_inicio] + where_params + [por_pagina, offset])

        elif agregacao == 'filial':
            query = f"""
                SELECT
                    hed.cod_empresa as codigo,
                    cl.nome_loja as nome,
                    COUNT(*) as total_registros,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as registros_ruptura,
                    ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric
                        / NULLIF(COUNT(*), 0) * 100, 2) as ruptura,
                    ROUND(
                        SUM(hed.estoque_diario)::numeric
                        / NULLIF(SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            THEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 ELSE 0 END), 0)
                    , 1) as cobertura,
                    ROUND(
                        SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            AND hed.estoque_diario / (COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0) > 90
                            THEN 1 ELSE 0 END)::numeric
                        / NULLIF(SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            THEN 1 ELSE 0 END), 0) * 100
                    , 1) as pct_excesso
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_lojas cl ON hed.cod_empresa = cl.cod_empresa
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                LEFT JOIN demanda_pre_calculada d
                    ON hed.codigo::text = d.cod_produto
                    AND hed.cod_empresa = COALESCE(d.cod_empresa, hed.cod_empresa)
                    AND d.ano = EXTRACT(YEAR FROM hed.data)::int
                    AND d.mes = EXTRACT(MONTH FROM hed.data)::int
                WHERE hed.data >= %s
                AND hed.cod_empresa < 80
                {filtro_sql}
                GROUP BY hed.cod_empresa, cl.nome_loja
                ORDER BY {col_ordenacao} {ordem_sql} NULLS LAST
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, [data_inicio] + where_params + [por_pagina, offset])

        else:  # linha
            query = f"""
                SELECT
                    cpc.categoria as nome,
                    cpc.codigo_linha as codigo,
                    cpc.descricao_linha as descricao,
                    COUNT(*) as total_registros,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as registros_ruptura,
                    ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric
                        / NULLIF(COUNT(*), 0) * 100, 2) as ruptura,
                    ROUND(
                        SUM(hed.estoque_diario)::numeric
                        / NULLIF(SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            THEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 ELSE 0 END), 0)
                    , 1) as cobertura,
                    ROUND(
                        SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            AND hed.estoque_diario / (COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0) > 90
                            THEN 1 ELSE 0 END)::numeric
                        / NULLIF(SUM(CASE WHEN COALESCE(d.ajuste_manual, d.demanda_prevista) / 30.0 > 0
                            THEN 1 ELSE 0 END), 0) * 100
                    , 1) as pct_excesso
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                LEFT JOIN demanda_pre_calculada d
                    ON hed.codigo::text = d.cod_produto
                    AND hed.cod_empresa = COALESCE(d.cod_empresa, hed.cod_empresa)
                    AND d.ano = EXTRACT(YEAR FROM hed.data)::int
                    AND d.mes = EXTRACT(MONTH FROM hed.data)::int
                WHERE hed.data >= %s
                AND hed.cod_empresa < 80
                {filtro_sql}
                GROUP BY cpc.categoria, cpc.codigo_linha, cpc.descricao_linha
                ORDER BY {col_ordenacao} {ordem_sql} NULLS LAST
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, [data_inicio] + where_params + [por_pagina, offset])

        ranking = format_result(cursor.fetchall())

        # Contar total para paginacao
        if agregacao == 'item':
            count_query = f"""
                SELECT COUNT(DISTINCT hed.codigo) as total
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s AND hed.cod_empresa < 80 {filtro_sql}
            """
        elif agregacao == 'fornecedor':
            count_query = f"""
                SELECT COUNT(DISTINCT cpc.nome_fornecedor) as total
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s AND hed.cod_empresa < 80 {filtro_sql}
            """
        elif agregacao == 'filial':
            count_query = f"""
                SELECT COUNT(DISTINCT hed.cod_empresa) as total
                FROM historico_estoque_diario hed
                WHERE hed.data >= %s AND hed.cod_empresa < 80 {filtro_sql}
            """
        else:  # linha
            count_query = f"""
                SELECT COUNT(DISTINCT (cpc.categoria, cpc.codigo_linha)) as total
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s AND hed.cod_empresa < 80 {filtro_sql}
            """
        cursor.execute(count_query, [data_inicio] + where_params)
        total = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        # Formatar itens
        itens = []
        for r in ranking:
            if agregacao == 'item':
                itens.append({
                    'identificador': str(r.get('codigo', '')),
                    'descricao': r.get('descricao', '') or r.get('fornecedor', ''),
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'excesso': r.get('pct_excesso'),
                    'total_skus': 1,
                    'skus_ruptura': 1 if (r.get('ruptura') or 0) > 0 else 0
                })
            elif agregacao == 'fornecedor':
                itens.append({
                    'identificador': r.get('nome', ''),
                    'descricao': '',
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'excesso': r.get('pct_excesso'),
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })
            elif agregacao == 'filial':
                itens.append({
                    'identificador': str(r.get('codigo', '')),
                    'descricao': r.get('nome', ''),
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'excesso': r.get('pct_excesso'),
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })
            else:  # linha
                itens.append({
                    'identificador': f"{r.get('codigo', '')} - {r.get('descricao', '')}",
                    'descricao': r.get('nome', ''),
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'excesso': r.get('pct_excesso'),
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })

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
        print(f"[ERRO] api_kpis_ranking: {e}")
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'erro': str(e)}), 500
