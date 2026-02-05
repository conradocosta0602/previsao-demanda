"""
Blueprint: KPIs
Rotas: /kpis, /api/kpis/*
Painel de indicadores: Ruptura, Cobertura, WMAPE, BIAS
"""

from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from flask import Blueprint, render_template, request, jsonify
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection

kpis_bp = Blueprint('kpis', __name__)


def decimal_to_float(obj):
    """Converte Decimal para float para serialização JSON."""
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


@kpis_bp.route('/kpis')
def kpis_page():
    """Pagina de indicadores de desempenho (KPIs)"""
    return render_template('kpis.html')


@kpis_bp.route('/api/kpis/filtros', methods=['GET'])
def api_kpis_filtros():
    """
    Retorna opcoes de filtros para a tela de KPIs.
    Linha3 agrupada por categoria para filtragem hierarquica no frontend.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Fornecedores
        cursor.execute("""
            SELECT DISTINCT nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE nome_fornecedor IS NOT NULL AND TRIM(nome_fornecedor) != ''
            ORDER BY nome_fornecedor
        """)
        fornecedores = [r['nome_fornecedor'] for r in cursor.fetchall()]

        # Linha1 (Categorias)
        cursor.execute("""
            SELECT DISTINCT categoria
            FROM cadastro_produtos_completo
            WHERE categoria IS NOT NULL AND categoria != ''
            ORDER BY categoria
        """)
        categorias = [r['categoria'] for r in cursor.fetchall()]

        # Linha3 agrupada por categoria para o frontend filtrar
        cursor.execute("""
            SELECT DISTINCT categoria, codigo_linha, descricao_linha
            FROM cadastro_produtos_completo
            WHERE codigo_linha IS NOT NULL AND codigo_linha != ''
            AND categoria IS NOT NULL
            ORDER BY categoria, descricao_linha
        """)
        linhas3_rows = cursor.fetchall()

        # Agrupar linhas3 por categoria
        linhas3_por_categoria = {}
        for r in linhas3_rows:
            cat = r['categoria']
            if cat not in linhas3_por_categoria:
                linhas3_por_categoria[cat] = []
            linhas3_por_categoria[cat].append({
                'codigo': r['codigo_linha'],
                'descricao': r['descricao_linha'] or r['codigo_linha']
            })

        # Filiais
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
    Retorna resumo atual dos 4 KPIs principais.
    Filtros: fornecedor, categoria, codigo_linha, cod_empresa
    """
    try:
        # Parametros de filtro
        fornecedores = request.args.getlist('fornecedor')
        categorias = request.args.getlist('categoria')
        linhas3 = request.args.getlist('codigo_linha')
        filiais = request.args.getlist('cod_empresa')
        dias = request.args.get('dias', default=30, type=int)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        # Construir clausulas WHERE
        where_clauses = []
        params = []

        if fornecedores and fornecedores[0]:
            placeholders = ','.join(['%s'] * len(fornecedores))
            where_clauses.append(f"cpc.nome_fornecedor IN ({placeholders})")
            params.extend(fornecedores)

        if categorias and categorias[0]:
            placeholders = ','.join(['%s'] * len(categorias))
            where_clauses.append(f"cpc.categoria IN ({placeholders})")
            params.extend(categorias)

        if linhas3 and linhas3[0]:
            placeholders = ','.join(['%s'] * len(linhas3))
            where_clauses.append(f"cpc.codigo_linha IN ({placeholders})")
            params.extend(linhas3)

        if filiais and filiais[0]:
            placeholders = ','.join(['%s'] * len(filiais))
            where_clauses.append(f"e.cod_empresa IN ({placeholders})")
            params.extend([int(f) for f in filiais])

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # =====================================================================
        # KPI 1: RUPTURA (% de dias com estoque <= 0)
        # =====================================================================
        query_ruptura = f"""
            WITH itens_com_demanda AS (
                SELECT DISTINCT codigo, cod_empresa
                FROM historico_vendas_diario
                WHERE data >= %s
                AND qtd_venda > 0
            ),
            dias_ruptura AS (
                SELECT
                    hed.codigo,
                    hed.cod_empresa,
                    COUNT(*) as total_dias,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as dias_em_ruptura
                FROM historico_estoque_diario hed
                INNER JOIN itens_com_demanda icd ON hed.codigo = icd.codigo AND hed.cod_empresa = icd.cod_empresa
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s
                AND {where_sql}
                GROUP BY hed.codigo, hed.cod_empresa
            )
            SELECT
                COUNT(*) as total_itens,
                SUM(dias_em_ruptura) as total_dias_ruptura,
                SUM(total_dias) as total_dias_analisados,
                CASE WHEN SUM(total_dias) > 0
                    THEN ROUND(SUM(dias_em_ruptura)::numeric / SUM(total_dias) * 100, 2)
                    ELSE 0 END as taxa_ruptura
            FROM dias_ruptura
        """
        cursor.execute(query_ruptura, [data_inicio, data_inicio] + params)
        ruptura = cursor.fetchone() or {}

        # =====================================================================
        # KPI 2: COBERTURA (dias de estoque)
        # =====================================================================
        query_cobertura = f"""
            WITH demanda_media AS (
                SELECT
                    hvd.codigo,
                    hvd.cod_empresa,
                    SUM(hvd.qtd_venda) / NULLIF(COUNT(DISTINCT hvd.data), 0) as demanda_diaria
                FROM historico_vendas_diario hvd
                LEFT JOIN cadastro_produtos_completo cpc ON hvd.codigo::text = cpc.cod_produto
                WHERE hvd.data >= %s
                AND {where_sql.replace('e.cod_empresa', 'hvd.cod_empresa')}
                GROUP BY hvd.codigo, hvd.cod_empresa
                HAVING SUM(hvd.qtd_venda) > 0
            )
            SELECT
                COUNT(*) as total_itens,
                ROUND(AVG(CASE WHEN dm.demanda_diaria > 0 THEN e.estoque / dm.demanda_diaria END)::numeric, 1) as cobertura_media,
                ROUND(MIN(CASE WHEN dm.demanda_diaria > 0 THEN e.estoque / dm.demanda_diaria END)::numeric, 1) as cobertura_minima,
                ROUND(MAX(CASE WHEN dm.demanda_diaria > 0 THEN e.estoque / dm.demanda_diaria END)::numeric, 1) as cobertura_maxima
            FROM estoque_posicao_atual e
            INNER JOIN demanda_media dm ON e.codigo = dm.codigo AND e.cod_empresa = dm.cod_empresa
            LEFT JOIN cadastro_produtos_completo cpc ON e.codigo::text = cpc.cod_produto
            WHERE {where_sql}
        """
        cursor.execute(query_cobertura, [data_inicio] + params + params)
        cobertura = cursor.fetchone() or {}

        # =====================================================================
        # KPI 3 e 4: WMAPE e BIAS (usando historico_previsao se existir)
        # =====================================================================
        query_wmape = f"""
            SELECT
                CASE WHEN SUM(hp.qtd_realizada) > 0
                    THEN ROUND(SUM(ABS(hp.qtd_realizada - hp.qtd_prevista)) / SUM(hp.qtd_realizada) * 100, 2)
                    ELSE NULL END as wmape,
                CASE WHEN SUM(hp.qtd_realizada) > 0
                    THEN ROUND(SUM(hp.qtd_prevista - hp.qtd_realizada) / SUM(hp.qtd_realizada) * 100, 2)
                    ELSE NULL END as bias,
                COUNT(*) as total_previsoes
            FROM historico_previsao hp
            LEFT JOIN cadastro_produtos_completo cpc ON hp.codigo::text = cpc.cod_produto
            WHERE hp.data >= %s
            AND hp.qtd_realizada IS NOT NULL
            AND {where_sql.replace('e.cod_empresa', 'hp.cod_empresa')}
        """
        try:
            cursor.execute(query_wmape, [data_inicio] + params)
            acuracia = cursor.fetchone() or {}
        except Exception:
            acuracia = {'wmape': None, 'bias': None, 'total_previsoes': 0}

        # Calcular variacao vs periodo anterior
        data_inicio_anterior = (datetime.now() - timedelta(days=dias*2)).strftime('%Y-%m-%d')
        data_fim_anterior = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        # Ruptura anterior para comparacao
        query_ruptura_ant = f"""
            WITH itens_com_demanda AS (
                SELECT DISTINCT codigo, cod_empresa
                FROM historico_vendas_diario
                WHERE data BETWEEN %s AND %s
                AND qtd_venda > 0
            ),
            dias_ruptura AS (
                SELECT
                    hed.codigo,
                    hed.cod_empresa,
                    COUNT(*) as total_dias,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as dias_em_ruptura
                FROM historico_estoque_diario hed
                INNER JOIN itens_com_demanda icd ON hed.codigo = icd.codigo AND hed.cod_empresa = icd.cod_empresa
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data BETWEEN %s AND %s
                AND {where_sql}
                GROUP BY hed.codigo, hed.cod_empresa
            )
            SELECT
                CASE WHEN SUM(total_dias) > 0
                    THEN ROUND(SUM(dias_em_ruptura)::numeric / SUM(total_dias) * 100, 2)
                    ELSE 0 END as taxa_ruptura
            FROM dias_ruptura
        """
        cursor.execute(query_ruptura_ant, [data_inicio_anterior, data_fim_anterior, data_inicio_anterior, data_fim_anterior] + params)
        ruptura_ant = cursor.fetchone() or {}

        cursor.close()
        conn.close()

        # Calcular variações
        taxa_ruptura_atual = float(ruptura.get('taxa_ruptura') or 0)
        taxa_ruptura_anterior = float(ruptura_ant.get('taxa_ruptura') or 0)
        variacao_ruptura = round(taxa_ruptura_atual - taxa_ruptura_anterior, 2)

        cobertura_valor = float(cobertura.get('cobertura_media') or 0)
        wmape_valor = float(acuracia.get('wmape') or 0) if acuracia.get('wmape') else None
        bias_valor = float(acuracia.get('bias') or 0) if acuracia.get('bias') else None

        # Retornar no formato esperado pelo JavaScript
        return jsonify({
            'ruptura': {
                'valor': taxa_ruptura_atual,
                'variacao': variacao_ruptura,
                'total_itens': ruptura.get('total_itens') or 0
            },
            'cobertura': {
                'valor': cobertura_valor,
                'variacao': 0,  # Pode calcular depois
                'meta': 90
            },
            'wmape': {
                'valor': wmape_valor,
                'variacao': 0
            },
            'bias': {
                'valor': bias_valor,
                'variacao': 0
            }
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_resumo: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@kpis_bp.route('/api/kpis/evolucao', methods=['GET'])
def api_kpis_evolucao():
    """
    Retorna dados de evolucao temporal dos KPIs para graficos.
    Granularidade: diario (30d), semanal (6m), mensal (12m)
    Agregacao: geral, fornecedor, linha, filial, item
    """
    try:
        # Parametros
        granularidade = request.args.get('granularidade', default='mensal')
        agregacao = request.args.get('agregacao', default='geral')
        fornecedores = request.args.getlist('fornecedor')
        categorias = request.args.getlist('categoria')
        linhas3 = request.args.getlist('codigo_linha')
        filiais = request.args.getlist('cod_empresa')
        codigos = request.args.getlist('codigo')  # Para agregacao por item

        # Definir periodo baseado na granularidade
        if granularidade == 'diario':
            dias = 30
            group_by = "hed.data"
            date_format = "TO_CHAR(hed.data, 'DD/MM')"
        elif granularidade == 'semanal':
            dias = 180  # 6 meses
            group_by = "DATE_TRUNC('week', hed.data)"
            date_format = "TO_CHAR(DATE_TRUNC('week', hed.data), 'DD/MM/YY')"
        else:  # mensal
            dias = 365  # 12 meses
            group_by = "DATE_TRUNC('month', hed.data)"
            date_format = "TO_CHAR(DATE_TRUNC('month', hed.data), 'MM/YYYY')"

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construir clausulas WHERE
        where_clauses = ["hed.data >= %s"]
        params = [data_inicio]

        if fornecedores and fornecedores[0]:
            placeholders = ','.join(['%s'] * len(fornecedores))
            where_clauses.append(f"cpc.nome_fornecedor IN ({placeholders})")
            params.extend(fornecedores)

        if categorias and categorias[0]:
            placeholders = ','.join(['%s'] * len(categorias))
            where_clauses.append(f"cpc.categoria IN ({placeholders})")
            params.extend(categorias)

        if linhas3 and linhas3[0]:
            placeholders = ','.join(['%s'] * len(linhas3))
            where_clauses.append(f"cpc.codigo_linha IN ({placeholders})")
            params.extend(linhas3)

        if filiais and filiais[0]:
            placeholders = ','.join(['%s'] * len(filiais))
            where_clauses.append(f"hed.cod_empresa IN ({placeholders})")
            params.extend([int(f) for f in filiais])

        if codigos and codigos[0]:
            placeholders = ','.join(['%s'] * len(codigos))
            where_clauses.append(f"hed.codigo IN ({placeholders})")
            params.extend([int(c) for c in codigos])

        where_sql = " AND ".join(where_clauses)

        # Definir campo de agregacao
        if agregacao == 'fornecedor':
            agg_field = "cpc.nome_fornecedor"
            agg_name = "nome_fornecedor"
        elif agregacao == 'linha':
            agg_field = "cpc.categoria"
            agg_name = "categoria"
        elif agregacao == 'filial':
            agg_field = "hed.cod_empresa"
            agg_name = "cod_empresa"
        elif agregacao == 'item':
            agg_field = "hed.codigo"
            agg_name = "codigo"
        else:  # geral
            agg_field = "'Geral'"
            agg_name = "grupo"

        # =====================================================================
        # EVOLUÇÃO RUPTURA
        # =====================================================================
        query_ruptura = f"""
            SELECT
                {group_by} as periodo,
                {date_format} as periodo_label,
                {agg_field} as {agg_name},
                COUNT(*) as total_registros,
                SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as registros_ruptura,
                ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as taxa_ruptura
            FROM historico_estoque_diario hed
            LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
            WHERE {where_sql}
            GROUP BY {group_by}, {agg_field}
            ORDER BY {group_by}, {agg_field}
        """
        cursor.execute(query_ruptura, params)
        evolucao_ruptura = format_result(cursor.fetchall())

        # =====================================================================
        # EVOLUÇÃO COBERTURA
        # =====================================================================
        # Cobertura precisa ser calculada de forma diferente (snapshot por periodo)
        query_cobertura = f"""
            WITH demanda_periodo AS (
                SELECT
                    {group_by.replace('hed.', 'hvd.')} as periodo,
                    {agg_field.replace('hed.', 'hvd.')} as {agg_name},
                    hvd.codigo,
                    hvd.cod_empresa,
                    SUM(hvd.qtd_venda) / NULLIF(COUNT(DISTINCT hvd.data), 0) as demanda_diaria
                FROM historico_vendas_diario hvd
                LEFT JOIN cadastro_produtos_completo cpc ON hvd.codigo::text = cpc.cod_produto
                WHERE {where_sql.replace('hed.', 'hvd.')}
                GROUP BY {group_by.replace('hed.', 'hvd.')}, {agg_field.replace('hed.', 'hvd.')}, hvd.codigo, hvd.cod_empresa
            ),
            estoque_periodo AS (
                SELECT
                    {group_by} as periodo,
                    {agg_field} as {agg_name},
                    hed.codigo,
                    hed.cod_empresa,
                    AVG(hed.estoque_diario) as estoque_medio
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE {where_sql}
                GROUP BY {group_by}, {agg_field}, hed.codigo, hed.cod_empresa
            )
            SELECT
                ep.periodo,
                {date_format.replace('hed.', 'ep.')} as periodo_label,
                ep.{agg_name},
                ROUND(AVG(CASE WHEN dp.demanda_diaria > 0 THEN ep.estoque_medio / dp.demanda_diaria END)::numeric, 1) as cobertura_media
            FROM estoque_periodo ep
            LEFT JOIN demanda_periodo dp ON ep.periodo = dp.periodo
                AND ep.{agg_name} = dp.{agg_name}
                AND ep.codigo = dp.codigo
                AND ep.cod_empresa = dp.cod_empresa
            GROUP BY ep.periodo, ep.{agg_name}
            ORDER BY ep.periodo, ep.{agg_name}
        """
        try:
            cursor.execute(query_cobertura, params + params)
            evolucao_cobertura = format_result(cursor.fetchall())
        except Exception as e:
            print(f"Erro ao calcular cobertura: {e}")
            evolucao_cobertura = []

        # Calcular melhor historico para cada KPI
        melhor_ruptura = min([r['taxa_ruptura'] for r in evolucao_ruptura if r.get('taxa_ruptura')], default=0)

        cursor.close()
        conn.close()

        # Formatar dados para o JavaScript (formato esperado: periodo, valor, melhor_historico)
        def formatar_evolucao(dados, campo_valor, melhor_valor=None):
            resultado = []
            for d in dados:
                resultado.append({
                    'periodo': d.get('periodo_label', ''),
                    'valor': d.get(campo_valor, 0),
                    'melhor_historico': melhor_valor
                })
            return resultado

        # Calcular melhor historico
        valores_ruptura = [r.get('taxa_ruptura', 0) for r in evolucao_ruptura if r.get('taxa_ruptura') is not None]
        melhor_ruptura = min(valores_ruptura) if valores_ruptura else 0

        valores_cobertura = [r.get('cobertura_media', 0) for r in evolucao_cobertura if r.get('cobertura_media') is not None]
        melhor_cobertura = max(valores_cobertura) if valores_cobertura else 0

        return jsonify({
            'ruptura': formatar_evolucao(evolucao_ruptura, 'taxa_ruptura', melhor_ruptura),
            'cobertura': formatar_evolucao(evolucao_cobertura, 'cobertura_media', melhor_cobertura),
            'wmape': [],  # Sera preenchido quando houver dados de previsao
            'bias': []
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_evolucao: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@kpis_bp.route('/api/kpis/ranking', methods=['GET'])
def api_kpis_ranking():
    """
    Retorna ranking de itens/grupos por KPI.
    Ordenacao e paginacao configuravel.
    """
    try:
        # Parametros
        ordenar_por = request.args.get('ordenar_por', default='ruptura')
        ordem = request.args.get('ordem', default='desc')  # asc ou desc
        agregacao = request.args.get('agregacao', default='item')
        pagina = request.args.get('pagina', default=1, type=int)
        por_pagina = request.args.get('por_pagina', default=20, type=int)
        dias = request.args.get('dias', default=30, type=int)

        # Filtros
        fornecedores = request.args.getlist('fornecedor')
        categorias = request.args.getlist('categoria')
        linhas3 = request.args.getlist('codigo_linha')
        filiais = request.args.getlist('cod_empresa')

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construir WHERE
        where_clauses = []
        params = [data_inicio]

        if fornecedores and fornecedores[0]:
            placeholders = ','.join(['%s'] * len(fornecedores))
            where_clauses.append(f"cpc.nome_fornecedor IN ({placeholders})")
            params.extend(fornecedores)

        if categorias and categorias[0]:
            placeholders = ','.join(['%s'] * len(categorias))
            where_clauses.append(f"cpc.categoria IN ({placeholders})")
            params.extend(categorias)

        if linhas3 and linhas3[0]:
            placeholders = ','.join(['%s'] * len(linhas3))
            where_clauses.append(f"cpc.codigo_linha IN ({placeholders})")
            params.extend(linhas3)

        if filiais and filiais[0]:
            placeholders = ','.join(['%s'] * len(filiais))
            where_clauses.append(f"hed.cod_empresa IN ({placeholders})")
            params.extend([int(f) for f in filiais])

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        # Definir agrupamento
        if agregacao == 'fornecedor':
            group_fields = "cpc.nome_fornecedor"
            select_fields = "cpc.nome_fornecedor as nome, NULL as codigo, NULL as descricao"
        elif agregacao == 'linha':
            group_fields = "cpc.categoria, cpc.codigo_linha, cpc.descricao_linha"
            select_fields = "cpc.categoria as nome, cpc.codigo_linha as codigo, cpc.descricao_linha as descricao"
        elif agregacao == 'filial':
            group_fields = "hed.cod_empresa"
            select_fields = "cl.nome_loja as nome, hed.cod_empresa as codigo, NULL as descricao"
        else:  # item
            group_fields = "hed.codigo, cpc.descricao, cpc.nome_fornecedor"
            select_fields = "hed.codigo, cpc.descricao, cpc.nome_fornecedor"

        # Validar ordenacao
        ordem_sql = "DESC" if ordem.lower() == 'desc' else "ASC"
        if ordenar_por not in ['ruptura', 'cobertura', 'wmape']:
            ordenar_por = 'ruptura'

        # Query de ranking
        offset = (pagina - 1) * por_pagina

        if agregacao == 'item':
            query = f"""
                WITH dados AS (
                    SELECT
                        hed.codigo,
                        cpc.descricao,
                        cpc.nome_fornecedor,
                        COUNT(*) as total_dias,
                        SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as dias_ruptura,
                        ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as ruptura
                    FROM historico_estoque_diario hed
                    LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                    WHERE hed.data >= %s {where_sql}
                    GROUP BY hed.codigo, cpc.descricao, cpc.nome_fornecedor
                    HAVING COUNT(*) >= 5
                ),
                demanda AS (
                    SELECT
                        hvd.codigo,
                        SUM(hvd.qtd_venda) / NULLIF(COUNT(DISTINCT hvd.data), 0) as demanda_diaria
                    FROM historico_vendas_diario hvd
                    WHERE hvd.data >= %s
                    GROUP BY hvd.codigo
                ),
                estoque AS (
                    SELECT
                        codigo,
                        cod_empresa,
                        estoque
                    FROM estoque_posicao_atual
                )
                SELECT
                    d.codigo,
                    d.descricao,
                    d.nome_fornecedor as fornecedor,
                    d.ruptura,
                    ROUND((e.estoque / NULLIF(dm.demanda_diaria, 0))::numeric, 1) as cobertura,
                    NULL as wmape
                FROM dados d
                LEFT JOIN demanda dm ON d.codigo = dm.codigo
                LEFT JOIN estoque e ON d.codigo = e.codigo
                ORDER BY {ordenar_por} {ordem_sql} NULLS LAST
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, params + [data_inicio] + [por_pagina, offset])
        else:
            # Agregacao por fornecedor, linha ou filial
            join_loja = "LEFT JOIN cadastro_lojas cl ON hed.cod_empresa = cl.cod_empresa" if agregacao == 'filial' else ""

            query = f"""
                SELECT
                    {select_fields},
                    COUNT(*) as total_registros,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as registros_ruptura,
                    ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as ruptura,
                    NULL as cobertura,
                    NULL as wmape
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                {join_loja}
                WHERE hed.data >= %s {where_sql}
                GROUP BY {group_fields}
                ORDER BY ruptura {ordem_sql} NULLS LAST
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, params + [por_pagina, offset])

        ranking = format_result(cursor.fetchall())

        # Contar total para paginacao
        if agregacao == 'item':
            query_count = f"""
                SELECT COUNT(DISTINCT hed.codigo) as total
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s {where_sql}
            """
        else:
            query_count = f"""
                SELECT COUNT(DISTINCT {group_fields.split(',')[0]}) as total
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s {where_sql}
            """
        cursor.execute(query_count, params)
        total = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        # Formatar itens para o formato esperado pelo JavaScript
        itens = []
        for r in ranking:
            if agregacao == 'item':
                itens.append({
                    'identificador': str(r.get('codigo', '')),
                    'descricao': r.get('descricao', ''),
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'wmape': r.get('wmape'),
                    'bias': None,
                    'total_skus': 1,
                    'skus_ruptura': 1 if r.get('ruptura', 0) > 0 else 0
                })
            elif agregacao == 'fornecedor':
                itens.append({
                    'identificador': r.get('nome', ''),
                    'descricao': '',
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'wmape': r.get('wmape'),
                    'bias': None,
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })
            elif agregacao == 'linha':
                itens.append({
                    'identificador': f"{r.get('codigo', '')} - {r.get('descricao', '')}",
                    'descricao': r.get('nome', ''),
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'wmape': r.get('wmape'),
                    'bias': None,
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })
            elif agregacao == 'filial':
                itens.append({
                    'identificador': str(r.get('codigo', '')),
                    'descricao': r.get('nome', ''),
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'wmape': r.get('wmape'),
                    'bias': None,
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })
            else:  # geral
                itens.append({
                    'identificador': 'Geral',
                    'descricao': '',
                    'ruptura': r.get('ruptura'),
                    'cobertura': r.get('cobertura'),
                    'wmape': r.get('wmape'),
                    'bias': None,
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
        return jsonify({'success': False, 'erro': str(e)}), 500
