"""
Blueprint: KPIs
Rotas: /kpis, /api/kpis/*
"""

from datetime import datetime, timedelta
import pandas as pd
from flask import Blueprint, render_template, request, jsonify
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection

kpis_bp = Blueprint('kpis', __name__)


@kpis_bp.route('/kpis')
def kpis_page():
    """Pagina de indicadores de desempenho (KPIs)"""
    return render_template('kpis.html')


@kpis_bp.route('/api/kpis/resumo', methods=['GET'])
def api_kpis_resumo():
    """
    Retorna resumo de KPIs do sistema.
    Inclui metricas de estoque, vendas, ruptura e cobertura.
    """
    try:
        cod_empresa = request.args.get('cod_empresa', type=int)
        fornecedor = request.args.get('fornecedor')
        dias = request.args.get('dias', default=30, type=int)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # KPIs de Estoque
        query_estoque = """
            SELECT
                COUNT(DISTINCT codigo) as total_skus,
                SUM(estoque_disponivel) as estoque_total,
                SUM(estoque_disponivel * preco_custo) as valor_estoque,
                AVG(CASE WHEN demanda_diaria > 0 THEN estoque_disponivel / demanda_diaria END) as cobertura_media
            FROM estoque_atual ea
            WHERE 1=1
        """
        params_estoque = []

        if cod_empresa:
            query_estoque += " AND ea.cod_empresa = %s"
            params_estoque.append(cod_empresa)

        cursor.execute(query_estoque, params_estoque if params_estoque else None)
        kpis_estoque = cursor.fetchone() or {}

        # KPIs de Vendas (ultimos N dias)
        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        query_vendas = """
            SELECT
                COUNT(DISTINCT codigo) as skus_vendidos,
                SUM(qtd_venda) as qtd_total_vendida,
                SUM(vl_venda) as valor_total_vendido,
                COUNT(DISTINCT data) as dias_com_venda
            FROM historico_vendas_diario
            WHERE data >= %s
        """
        params_vendas = [data_inicio]

        if cod_empresa:
            query_vendas += " AND cod_empresa = %s"
            params_vendas.append(cod_empresa)

        cursor.execute(query_vendas, params_vendas)
        kpis_vendas = cursor.fetchone() or {}

        # Taxa de Ruptura (itens com estoque <= 0)
        query_ruptura = """
            SELECT
                COUNT(*) as total_itens,
                SUM(CASE WHEN estoque_disponivel <= 0 THEN 1 ELSE 0 END) as itens_ruptura
            FROM estoque_atual
            WHERE demanda_diaria > 0.01
        """
        params_ruptura = []

        if cod_empresa:
            query_ruptura += " AND cod_empresa = %s"
            params_ruptura.append(cod_empresa)

        cursor.execute(query_ruptura, params_ruptura if params_ruptura else None)
        kpis_ruptura = cursor.fetchone() or {}

        total_itens = kpis_ruptura.get('total_itens') or 0
        itens_ruptura = kpis_ruptura.get('itens_ruptura') or 0
        taxa_ruptura = round((itens_ruptura / total_itens * 100), 2) if total_itens > 0 else 0

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'kpis': {
                'estoque': {
                    'total_skus': kpis_estoque.get('total_skus') or 0,
                    'estoque_total_unidades': float(kpis_estoque.get('estoque_total') or 0),
                    'valor_estoque': float(kpis_estoque.get('valor_estoque') or 0),
                    'cobertura_media_dias': round(float(kpis_estoque.get('cobertura_media') or 0), 1)
                },
                'vendas': {
                    'skus_vendidos': kpis_vendas.get('skus_vendidos') or 0,
                    'qtd_total_vendida': float(kpis_vendas.get('qtd_total_vendida') or 0),
                    'valor_total_vendido': float(kpis_vendas.get('valor_total_vendido') or 0),
                    'media_diaria': round(float(kpis_vendas.get('qtd_total_vendida') or 0) / max(dias, 1), 2)
                },
                'ruptura': {
                    'total_itens': total_itens,
                    'itens_em_ruptura': itens_ruptura,
                    'taxa_ruptura': taxa_ruptura
                },
                'periodo': {
                    'dias': dias,
                    'data_inicio': data_inicio,
                    'data_fim': datetime.now().strftime('%Y-%m-%d')
                }
            },
            'filtros': {
                'cod_empresa': cod_empresa,
                'fornecedor': fornecedor
            }
        })

    except Exception as e:
        print(f"Erro ao calcular KPIs: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@kpis_bp.route('/api/kpis/tendencias', methods=['GET'])
def api_kpis_tendencias():
    """
    Retorna tendencias historicas de KPIs para graficos.
    """
    try:
        cod_empresa = request.args.get('cod_empresa', type=int)
        dias = request.args.get('dias', default=30, type=int)
        granularidade = request.args.get('granularidade', default='diario')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        # Vendas por periodo
        if granularidade == 'diario':
            group_by = "data"
        elif granularidade == 'semanal':
            group_by = "DATE_TRUNC('week', data)"
        else:
            group_by = "DATE_TRUNC('month', data)"

        query_vendas = f"""
            SELECT
                {group_by} as periodo,
                SUM(qtd_venda) as qtd_vendida,
                SUM(vl_venda) as valor_vendido,
                COUNT(DISTINCT codigo) as skus_vendidos
            FROM historico_vendas_diario
            WHERE data >= %s
        """
        params = [data_inicio]

        if cod_empresa:
            query_vendas += " AND cod_empresa = %s"
            params.append(cod_empresa)

        query_vendas += f" GROUP BY {group_by} ORDER BY {group_by}"

        cursor.execute(query_vendas, params)
        vendas = cursor.fetchall()

        vendas_list = []
        for v in vendas:
            vendas_list.append({
                'periodo': str(v['periodo']),
                'qtd_vendida': float(v['qtd_vendida'] or 0),
                'valor_vendido': float(v['valor_vendido'] or 0),
                'skus_vendidos': v['skus_vendidos'] or 0
            })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'tendencias': {
                'vendas': vendas_list
            },
            'granularidade': granularidade,
            'periodo': {
                'dias': dias,
                'data_inicio': data_inicio
            }
        })

    except Exception as e:
        print(f"Erro ao buscar tendencias: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@kpis_bp.route('/api/kpis/ranking', methods=['GET'])
def api_kpis_ranking():
    """
    Retorna ranking de produtos por diferentes criterios.
    """
    try:
        criterio = request.args.get('criterio', default='vendas')
        cod_empresa = request.args.get('cod_empresa', type=int)
        limit = request.args.get('limit', default=20, type=int)
        dias = request.args.get('dias', default=30, type=int)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        if criterio == 'vendas':
            query = """
                SELECT
                    h.codigo,
                    p.descricao,
                    SUM(h.qtd_venda) as total_vendido,
                    SUM(h.vl_venda) as valor_vendido,
                    COUNT(DISTINCT h.data) as dias_com_venda
                FROM historico_vendas_diario h
                LEFT JOIN cadastro_produtos p ON h.codigo = p.codigo
                WHERE h.data >= %s
            """
            params = [data_inicio]
            if cod_empresa:
                query += " AND h.cod_empresa = %s"
                params.append(cod_empresa)
            query += " GROUP BY h.codigo, p.descricao ORDER BY total_vendido DESC LIMIT %s"
            params.append(limit)

        elif criterio == 'cobertura_baixa':
            query = """
                SELECT
                    e.codigo,
                    p.descricao,
                    e.estoque_disponivel,
                    e.demanda_diaria,
                    CASE WHEN e.demanda_diaria > 0 THEN e.estoque_disponivel / e.demanda_diaria ELSE 999 END as cobertura_dias
                FROM estoque_atual e
                LEFT JOIN cadastro_produtos p ON e.codigo = p.codigo
                WHERE e.demanda_diaria > 0.01
            """
            params = []
            if cod_empresa:
                query += " AND e.cod_empresa = %s"
                params.append(cod_empresa)
            query += " ORDER BY cobertura_dias ASC LIMIT %s"
            params.append(limit)

        elif criterio == 'ruptura':
            query = """
                SELECT
                    e.codigo,
                    p.descricao,
                    e.estoque_disponivel,
                    e.demanda_diaria,
                    e.demanda_diaria * 7 as venda_perdida_semana
                FROM estoque_atual e
                LEFT JOIN cadastro_produtos p ON e.codigo = p.codigo
                WHERE e.estoque_disponivel <= 0 AND e.demanda_diaria > 0.01
            """
            params = []
            if cod_empresa:
                query += " AND e.cod_empresa = %s"
                params.append(cod_empresa)
            query += " ORDER BY e.demanda_diaria DESC LIMIT %s"
            params.append(limit)

        else:
            return jsonify({'success': False, 'erro': 'Criterio invalido'}), 400

        cursor.execute(query, params)
        ranking = cursor.fetchall()

        ranking_list = []
        for r in ranking:
            item = dict(r)
            for k, v in item.items():
                if isinstance(v, (float, int)) and v is not None:
                    if k in ['cobertura_dias', 'demanda_diaria']:
                        item[k] = round(float(v), 2)
                    else:
                        item[k] = float(v) if isinstance(v, float) else v
            ranking_list.append(item)

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'ranking': ranking_list,
            'criterio': criterio,
            'limit': limit
        })

    except Exception as e:
        print(f"Erro ao buscar ranking: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500
