"""
Blueprint: Parametros de Fornecedor
Rotas: /importar-parametros-fornecedor, /api/parametros-fornecedor*, /central-parametros-fornecedor, /api/central-parametros/*
"""

from datetime import datetime
import pandas as pd
import psycopg2
from flask import Blueprint, render_template, request, jsonify
from psycopg2.extras import RealDictCursor, execute_values

from app.utils.db_connection import get_db_connection, DB_CONFIG

parametros_bp = Blueprint('parametros', __name__)


@parametros_bp.route('/importar-parametros-fornecedor')
def pagina_importar_parametros_fornecedor():
    """Pagina de importacao de parametros de fornecedor."""
    return render_template('importar_parametros_fornecedor.html')


@parametros_bp.route('/api/parametros-fornecedor', methods=['GET'])
def api_listar_parametros_fornecedor():
    """Lista parametros de fornecedor cadastrados."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar se tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'parametros_fornecedor'
            )
        """)
        if not cursor.fetchone()['exists']:
            conn.close()
            return jsonify([])

        # Filtros opcionais
        cnpj = request.args.get('cnpj')
        cod_empresa = request.args.get('cod_empresa')

        query = """
            SELECT cnpj_fornecedor, nome_fornecedor, cod_empresa, tipo_destino,
                   lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor, ativo
            FROM parametros_fornecedor
            WHERE ativo = TRUE
        """
        params = []

        if cnpj:
            query += " AND cnpj_fornecedor = %s"
            params.append(cnpj)

        if cod_empresa:
            query += " AND cod_empresa = %s"
            params.append(int(cod_empresa))

        query += " ORDER BY nome_fornecedor, cod_empresa"

        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()

        return jsonify(resultados)

    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@parametros_bp.route('/api/importar-parametros-fornecedor', methods=['POST'])
def api_importar_parametros_fornecedor():
    """Importa parametros de fornecedor do arquivo Excel."""
    try:
        dados = request.get_json()
        registros = dados.get('dados', [])
        modo = dados.get('modo', 'atualizar')

        if not registros:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum registro para importar'
            })

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Criar tabela se nao existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parametros_fornecedor (
                id SERIAL PRIMARY KEY,
                cnpj_fornecedor VARCHAR(20) NOT NULL,
                nome_fornecedor VARCHAR(200),
                cod_empresa INTEGER NOT NULL,
                tipo_destino VARCHAR(20) DEFAULT 'LOJA',
                lead_time_dias INTEGER DEFAULT 15,
                ciclo_pedido_dias INTEGER DEFAULT 7,
                pedido_minimo_valor DECIMAL(12,2) DEFAULT 0,
                data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo BOOLEAN DEFAULT TRUE,
                UNIQUE(cnpj_fornecedor, cod_empresa)
            )
        """)
        conn.commit()

        # Criar indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_param_forn_cnpj ON parametros_fornecedor(cnpj_fornecedor)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_param_forn_empresa ON parametros_fornecedor(cod_empresa)")
        conn.commit()

        # Se modo substituir, desativar todos
        if modo == 'substituir':
            cursor.execute("UPDATE parametros_fornecedor SET ativo = FALSE")
            conn.commit()

        # Inserir/atualizar registros
        valores = []
        for r in registros:
            cnpj_raw = str(r.get('cnpj_fornecedor', '')).strip()
            cnpj_formatado = cnpj_raw.zfill(14) if cnpj_raw and len(cnpj_raw) < 14 else cnpj_raw
            valores.append((
                cnpj_formatado,
                str(r.get('nome_fornecedor', '')).strip(),
                int(r.get('cod_empresa', 0)),
                str(r.get('tipo_destino', 'LOJA')).upper(),
                int(r.get('lead_time_dias', 15)),
                int(r.get('ciclo_pedido_dias', 7)),
                float(r.get('pedido_minimo_valor', 0))
            ))

        execute_values(cursor, """
            INSERT INTO parametros_fornecedor
                (cnpj_fornecedor, nome_fornecedor, cod_empresa, tipo_destino,
                 lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor)
            VALUES %s
            ON CONFLICT (cnpj_fornecedor, cod_empresa) DO UPDATE SET
                nome_fornecedor = EXCLUDED.nome_fornecedor,
                tipo_destino = EXCLUDED.tipo_destino,
                lead_time_dias = EXCLUDED.lead_time_dias,
                ciclo_pedido_dias = EXCLUDED.ciclo_pedido_dias,
                pedido_minimo_valor = EXCLUDED.pedido_minimo_valor,
                data_importacao = CURRENT_TIMESTAMP,
                ativo = TRUE
        """, valores)

        conn.commit()
        conn.close()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Importacao concluida com sucesso',
            'total': len(valores)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro na importacao: {str(e)}'
        }), 500


@parametros_bp.route('/api/parametros-fornecedor-produto', methods=['GET'])
def api_parametros_fornecedor_por_produto():
    """Busca parametros do fornecedor de um produto especifico."""
    try:
        codigo = request.args.get('codigo')
        cod_empresa = request.args.get('cod_empresa')

        if not codigo or not cod_empresa:
            return jsonify({'erro': 'Parametros codigo e cod_empresa sao obrigatorios'}), 400

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar se tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'parametros_fornecedor'
            )
        """)
        if not cursor.fetchone()['exists']:
            conn.close()
            return jsonify({
                'encontrado': False,
                'mensagem': 'Tabela de parametros de fornecedor nao existe.'
            })

        # Buscar CNPJ do fornecedor do produto
        cursor.execute("""
            SELECT cnpj_fornecedor, nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE cod_produto = %s
            LIMIT 1
        """, [str(codigo)])

        produto = cursor.fetchone()
        if not produto or not produto['cnpj_fornecedor']:
            conn.close()
            return jsonify({
                'encontrado': False,
                'mensagem': 'Produto nao encontrado ou sem fornecedor cadastrado'
            })

        cnpj = str(produto['cnpj_fornecedor']).strip()

        # Buscar parametros do fornecedor para a loja
        cursor.execute("""
            SELECT cnpj_fornecedor, nome_fornecedor, cod_empresa, tipo_destino,
                   lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor
            FROM parametros_fornecedor
            WHERE cnpj_fornecedor = %s
              AND cod_empresa = %s
              AND ativo = TRUE
            LIMIT 1
        """, [cnpj, int(cod_empresa)])

        params = cursor.fetchone()
        conn.close()

        if not params:
            return jsonify({
                'encontrado': False,
                'cnpj_fornecedor': cnpj,
                'nome_fornecedor': produto.get('nome_fornecedor', ''),
                'mensagem': f'Fornecedor nao cadastrado para loja {cod_empresa}'
            })

        return jsonify({
            'encontrado': True,
            'cnpj_fornecedor': params['cnpj_fornecedor'],
            'nome_fornecedor': params['nome_fornecedor'],
            'cod_empresa': params['cod_empresa'],
            'tipo_destino': params['tipo_destino'],
            'lead_time_dias': params['lead_time_dias'],
            'ciclo_pedido_dias': params['ciclo_pedido_dias'],
            'pedido_minimo_valor': float(params['pedido_minimo_valor']) if params['pedido_minimo_valor'] else 0
        })

    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@parametros_bp.route('/central-parametros-fornecedor')
def pagina_central_parametros_fornecedor():
    """Pagina da Central de Parametros de Fornecedor."""
    return render_template('central_parametros_fornecedor.html')


@parametros_bp.route('/api/central-parametros/buscar', methods=['GET'])
def api_central_parametros_buscar():
    """Busca fornecedor e seus produtos para consulta de parametros."""
    conn = None
    try:
        codigo = request.args.get('codigo', '').strip()
        cnpj = request.args.get('cnpj', '').strip()
        nome = request.args.get('nome', '').strip()
        cod_empresa = request.args.get('cod_empresa', '').strip()

        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cnpj_fornecedor = None
        nome_fornecedor = None

        # Se busca por codigo de produto
        if codigo:
            cursor.execute("""
                SELECT cnpj_fornecedor, nome_fornecedor
                FROM cadastro_produtos_completo
                WHERE cod_produto = %s
                LIMIT 1
            """, [codigo])
            produto = cursor.fetchone()

            if not produto:
                cursor.execute("""
                    SELECT cnpj_fornecedor, nome_fornecedor
                    FROM cadastro_produtos_completo
                    WHERE cod_produto LIKE %s
                    LIMIT 1
                """, [f"%{codigo}%"])
                produto = cursor.fetchone()

            if produto:
                cnpj_fornecedor = produto['cnpj_fornecedor']
                nome_fornecedor = produto['nome_fornecedor']

        # Se busca por CNPJ
        elif cnpj:
            cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '').strip()
            cnpj_formatado = cnpj_limpo.zfill(14)

            cursor.execute("""
                SELECT DISTINCT cnpj_fornecedor, nome_fornecedor
                FROM cadastro_produtos_completo
                WHERE cnpj_fornecedor = %s
                LIMIT 1
            """, [cnpj_formatado])
            forn = cursor.fetchone()

            if forn:
                cnpj_fornecedor = forn['cnpj_fornecedor']
                nome_fornecedor = forn['nome_fornecedor']

        # Se busca por nome
        elif nome:
            cursor.execute("""
                SELECT DISTINCT cnpj_fornecedor, nome_fornecedor
                FROM cadastro_produtos_completo
                WHERE nome_fornecedor ILIKE %s
                LIMIT 1
            """, [f"%{nome}%"])
            forn = cursor.fetchone()

            if forn:
                cnpj_fornecedor = forn['cnpj_fornecedor']
                nome_fornecedor = forn['nome_fornecedor']

        if not cnpj_fornecedor:
            conn.close()
            return jsonify({
                'success': False,
                'mensagem': 'Fornecedor nao encontrado'
            }), 404

        # Buscar parametros cadastrados
        parametros = []
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'parametros_fornecedor'
            )
        """)
        tabela_existe = cursor.fetchone()['exists']

        if tabela_existe:
            query_params = """
                SELECT cod_empresa, tipo_destino, lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor
                FROM parametros_fornecedor
                WHERE cnpj_fornecedor = %s AND ativo = TRUE
            """
            params_query = [cnpj_fornecedor]

            if cod_empresa:
                query_params += " AND cod_empresa = %s"
                params_query.append(int(cod_empresa))

            query_params += " ORDER BY cod_empresa"

            cursor.execute(query_params, params_query)
            parametros = cursor.fetchall()

        # Buscar lojas disponiveis
        cursor.execute("""
            SELECT cod_empresa, nome_loja
            FROM cadastro_lojas
            WHERE ativo = TRUE
            ORDER BY cod_empresa
        """)
        lojas = cursor.fetchall()

        # Buscar produtos do fornecedor com situacao de compra e padrao de compra
        # Curva ABC: vem de estoque_posicao_atual (pega a mais comum por produto)
        # Situacao de compra: pega a mais recente por produto (agregando todas as lojas)
        # Padrao de compra: pega a loja destino mais recente
        cursor.execute("""
            WITH sit_compra_agg AS (
                SELECT
                    codigo::text as cod_produto,
                    sit_compra,
                    ROW_NUMBER() OVER (PARTITION BY codigo ORDER BY updated_at DESC NULLS LAST) as rn
                FROM situacao_compra_itens
                WHERE sit_compra IS NOT NULL
            ),
            padrao_compra_agg AS (
                SELECT
                    codigo::text as cod_produto,
                    cod_empresa_destino,
                    ROW_NUMBER() OVER (PARTITION BY codigo ORDER BY data_referencia DESC, updated_at DESC NULLS LAST) as rn
                FROM padrao_compra_item
            ),
            curva_abc_agg AS (
                SELECT
                    codigo::text as cod_produto,
                    curva_abc,
                    ROW_NUMBER() OVER (PARTITION BY codigo ORDER BY data_importacao DESC NULLS LAST) as rn
                FROM estoque_posicao_atual
                WHERE curva_abc IS NOT NULL
            )
            SELECT
                p.cod_produto,
                p.descricao,
                p.categoria,
                p.codigo_linha,
                p.descricao_linha,
                COALESCE(c.curva_abc, '-') as curva_abc,
                COALESCE(s.sit_compra, 'ATIVO') as sit_compra,
                pc.cod_empresa_destino as padrao_compra
            FROM cadastro_produtos_completo p
            LEFT JOIN curva_abc_agg c ON c.cod_produto = p.cod_produto AND c.rn = 1
            LEFT JOIN sit_compra_agg s ON s.cod_produto = p.cod_produto AND s.rn = 1
            LEFT JOIN padrao_compra_agg pc ON pc.cod_produto = p.cod_produto AND pc.rn = 1
            WHERE p.cnpj_fornecedor = %s AND p.ativo = TRUE
            ORDER BY p.cod_produto
        """, [cnpj_fornecedor])
        produtos = cursor.fetchall()

        conn.close()

        return jsonify({
            'success': True,
            'fornecedor': {
                'cnpj': cnpj_fornecedor,
                'nome': nome_fornecedor
            },
            'parametros': [dict(p) for p in parametros],
            'lojas': [dict(l) for l in lojas],
            'produtos': [dict(p) for p in produtos]
        })

    except Exception as e:
        if conn:
            conn.close()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'mensagem': str(e)}), 500


@parametros_bp.route('/api/central-parametros/salvar', methods=['POST'])
def api_central_parametros_salvar():
    """Salva parametros de fornecedor editados."""
    conn = None
    try:
        dados = request.get_json()

        cnpj_fornecedor = dados.get('cnpj_fornecedor')
        nome_fornecedor = dados.get('nome_fornecedor')
        parametros = dados.get('parametros', [])

        if not cnpj_fornecedor:
            return jsonify({'success': False, 'mensagem': 'CNPJ do fornecedor e obrigatorio'}), 400

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Criar tabela se nao existir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parametros_fornecedor (
                id SERIAL PRIMARY KEY,
                cnpj_fornecedor VARCHAR(20) NOT NULL,
                nome_fornecedor VARCHAR(200),
                cod_empresa INTEGER NOT NULL,
                tipo_destino VARCHAR(20) DEFAULT 'LOJA',
                lead_time_dias INTEGER DEFAULT 15,
                ciclo_pedido_dias INTEGER DEFAULT 7,
                pedido_minimo_valor DECIMAL(12,2) DEFAULT 0,
                data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ativo BOOLEAN DEFAULT TRUE,
                UNIQUE(cnpj_fornecedor, cod_empresa)
            )
        """)
        conn.commit()

        atualizados = 0
        for p in parametros:
            cursor.execute("""
                INSERT INTO parametros_fornecedor
                    (cnpj_fornecedor, nome_fornecedor, cod_empresa, tipo_destino,
                     lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cnpj_fornecedor, cod_empresa) DO UPDATE SET
                    nome_fornecedor = EXCLUDED.nome_fornecedor,
                    tipo_destino = EXCLUDED.tipo_destino,
                    lead_time_dias = EXCLUDED.lead_time_dias,
                    ciclo_pedido_dias = EXCLUDED.ciclo_pedido_dias,
                    pedido_minimo_valor = EXCLUDED.pedido_minimo_valor,
                    data_importacao = CURRENT_TIMESTAMP,
                    ativo = TRUE
            """, (
                cnpj_fornecedor,
                nome_fornecedor,
                int(p['cod_empresa']),
                p.get('tipo_destino', 'LOJA'),
                int(p.get('lead_time_dias', 15)),
                int(p.get('ciclo_pedido_dias', 7)),
                float(p.get('pedido_minimo_valor', 0))
            ))
            atualizados += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'mensagem': f'Parametros aplicados para {atualizados} lojas'
        })

    except Exception as e:
        if conn:
            conn.close()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'mensagem': f'Erro: {str(e)}'
        }), 500
