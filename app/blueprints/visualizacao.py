"""
Blueprint: Visualizacao de Demanda
Rotas: /visualizacao, /api/lojas, /api/categorias, /api/produtos*, /api/fornecedores, /api/linhas, /api/sublinhas, /api/vendas
"""

from datetime import datetime, timedelta
import pandas as pd
from flask import Blueprint, render_template, request, jsonify
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection

visualizacao_bp = Blueprint('visualizacao', __name__)


@visualizacao_bp.route('/visualizacao')
def visualizacao():
    """Pagina de visualizacao de demanda"""
    return render_template('visualizacao_demanda.html')


@visualizacao_bp.route('/api/lojas', methods=['GET'])
def api_lojas():
    """Retorna lista de lojas do cadastro"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT cod_empresa, nome_loja, tipo, ativo
            FROM cadastro_lojas
            WHERE ativo = TRUE
            ORDER BY cod_empresa
        """)
        lojas = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'lojas': [dict(l) for l in lojas]
        })

    except Exception as e:
        print(f"Erro ao buscar lojas: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@visualizacao_bp.route('/api/categorias', methods=['GET'])
def api_categorias():
    """Retorna lista de categorias (Linha 1)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT DISTINCT categoria
            FROM cadastro_produtos_completo
            WHERE ativo = TRUE AND categoria IS NOT NULL
            ORDER BY categoria
        """)
        categorias = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'categorias': [c['categoria'] for c in categorias]
        })

    except Exception as e:
        print(f"Erro ao buscar categorias: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@visualizacao_bp.route('/api/fornecedores', methods=['GET'])
def api_fornecedores():
    """Retorna lista de fornecedores"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Filtros opcionais
        categoria = request.args.get('categoria')
        linha = request.args.get('linha')

        query = """
            SELECT DISTINCT nome_fornecedor, cnpj_fornecedor
            FROM cadastro_produtos_completo
            WHERE ativo = TRUE AND nome_fornecedor IS NOT NULL
        """
        params = []

        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)

        if linha:
            query += " AND codigo_linha = %s"
            params.append(linha)

        query += " ORDER BY nome_fornecedor"

        cursor.execute(query, params if params else None)
        fornecedores = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'fornecedores': [dict(f) for f in fornecedores]
        })

    except Exception as e:
        print(f"Erro ao buscar fornecedores: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@visualizacao_bp.route('/api/linhas', methods=['GET'])
def api_linhas():
    """Retorna lista de linhas (Linha 1 = categorias)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT DISTINCT categoria as linha
            FROM cadastro_produtos_completo
            WHERE ativo = TRUE AND categoria IS NOT NULL
            ORDER BY categoria
        """)
        linhas = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'linhas': [l['linha'] for l in linhas]
        })

    except Exception as e:
        print(f"Erro ao buscar linhas: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@visualizacao_bp.route('/api/sublinhas', methods=['GET'])
def api_sublinhas():
    """Retorna lista de sublinhas (Linha 3) filtradas por categoria"""
    try:
        categoria = request.args.get('categoria')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT DISTINCT codigo_linha, descricao_linha
            FROM cadastro_produtos_completo
            WHERE ativo = TRUE AND codigo_linha IS NOT NULL
        """
        params = []

        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)

        query += " ORDER BY codigo_linha"

        cursor.execute(query, params if params else None)
        sublinhas = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'sublinhas': [{'codigo': s['codigo_linha'], 'descricao': s['descricao_linha']} for s in sublinhas]
        })

    except Exception as e:
        print(f"Erro ao buscar sublinhas: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@visualizacao_bp.route('/api/produtos', methods=['GET'])
def api_produtos():
    """Retorna lista de produtos com filtros opcionais"""
    try:
        categoria = request.args.get('categoria')
        fornecedor = request.args.get('fornecedor')
        linha = request.args.get('linha')
        termo = request.args.get('termo')
        limit = request.args.get('limit', default=100, type=int)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT cod_produto as codigo, descricao, categoria, codigo_linha, nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE ativo = TRUE
        """
        params = []

        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)

        if fornecedor:
            query += " AND nome_fornecedor = %s"
            params.append(fornecedor)

        if linha:
            query += " AND codigo_linha = %s"
            params.append(linha)

        if termo:
            query += " AND (cod_produto ILIKE %s OR descricao ILIKE %s)"
            params.extend([f'%{termo}%', f'%{termo}%'])

        query += f" ORDER BY cod_produto LIMIT {limit}"

        cursor.execute(query, params if params else None)
        produtos = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'produtos': [dict(p) for p in produtos]
        })

    except Exception as e:
        print(f"Erro ao buscar produtos: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@visualizacao_bp.route('/api/produtos_fornecedor', methods=['GET'])
def api_produtos_fornecedor():
    """Retorna produtos de um fornecedor especifico"""
    try:
        nome_fornecedor = request.args.get('fornecedor')
        categoria = request.args.get('categoria')
        linha = request.args.get('linha')
        limit = request.args.get('limit', default=500, type=int)

        if not nome_fornecedor:
            return jsonify({'success': False, 'erro': 'Fornecedor e obrigatorio'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT cod_produto as codigo, descricao, categoria, codigo_linha, nome_fornecedor, cnpj_fornecedor
            FROM cadastro_produtos_completo
            WHERE ativo = TRUE AND nome_fornecedor = %s
        """
        params = [nome_fornecedor]

        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)

        if linha:
            query += " AND codigo_linha = %s"
            params.append(linha)

        query += f" ORDER BY cod_produto LIMIT {limit}"

        cursor.execute(query, params)
        produtos = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'produtos': [dict(p) for p in produtos],
            'total': len(produtos)
        })

    except Exception as e:
        print(f"Erro ao buscar produtos: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@visualizacao_bp.route('/api/vendas', methods=['GET'])
def api_vendas():
    """Retorna historico de vendas com filtros"""
    try:
        cod_empresa = request.args.get('cod_empresa', type=int)
        codigo = request.args.get('codigo')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        dias = request.args.get('dias', default=90, type=int)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Se nao informou datas, usar ultimos N dias
        if not data_inicio:
            data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        if not data_fim:
            data_fim = datetime.now().strftime('%Y-%m-%d')

        query = """
            SELECT data, codigo, cod_empresa, qtd_venda, vl_venda
            FROM historico_vendas_diario
            WHERE data BETWEEN %s AND %s
        """
        params = [data_inicio, data_fim]

        if cod_empresa:
            query += " AND cod_empresa = %s"
            params.append(cod_empresa)

        if codigo:
            query += " AND codigo = %s"
            params.append(codigo)

        query += " ORDER BY data DESC LIMIT 10000"

        cursor.execute(query, params)
        vendas = cursor.fetchall()

        vendas_list = []
        for v in vendas:
            vendas_list.append({
                'data': str(v['data']),
                'codigo': v['codigo'],
                'cod_empresa': v['cod_empresa'],
                'qtd_venda': float(v['qtd_venda'] or 0),
                'vl_venda': float(v['vl_venda'] or 0)
            })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'vendas': vendas_list,
            'periodo': {
                'data_inicio': data_inicio,
                'data_fim': data_fim
            }
        })

    except Exception as e:
        print(f"Erro ao buscar vendas: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500
