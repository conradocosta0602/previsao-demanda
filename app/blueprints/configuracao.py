"""
Blueprint: Configuracao (Parametros Globais)
Rotas: /api/parametros-globais*
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection

configuracao_bp = Blueprint('configuracao', __name__)


@configuracao_bp.route('/api/parametros-globais', methods=['GET'])
def api_listar_parametros_globais():
    """Lista todos os parametros globais do sistema."""
    # Parametros padrao - retorna esses se tabela nao existir
    parametros_padrao_dict = [
        {'chave': 'cobertura_alvo_dias', 'valor': '21', 'descricao': 'Cobertura alvo em dias', 'tipo': 'integer', 'categoria': 'pedidos'},
        {'chave': 'estoque_seguranca_dias', 'valor': '7', 'descricao': 'Dias de estoque de seguranca', 'tipo': 'integer', 'categoria': 'estoque'},
        {'chave': 'lead_time_padrao', 'valor': '15', 'descricao': 'Lead time padrao', 'tipo': 'integer', 'categoria': 'fornecedor'},
        {'chave': 'ciclo_pedido_padrao', 'valor': '7', 'descricao': 'Ciclo de pedido padrao', 'tipo': 'integer', 'categoria': 'fornecedor'},
        {'chave': 'dias_historico_vendas', 'valor': '730', 'descricao': 'Dias de historico de vendas', 'tipo': 'integer', 'categoria': 'previsao'},
        {'chave': 'dias_transferencia_padrao_compra', 'valor': '10', 'descricao': 'Dias de lead time para transferencia', 'tipo': 'integer', 'categoria': 'transferencia'},
        {'chave': 'cobertura_minima_doador', 'valor': '10', 'descricao': 'Cobertura minima doador', 'tipo': 'integer', 'categoria': 'transferencia'},
        {'chave': 'margem_excesso_dias', 'valor': '7', 'descricao': 'Dias acima do alvo para excesso', 'tipo': 'integer', 'categoria': 'transferencia'},
    ]

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar se tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'parametros_globais'
            )
        """)
        tabela_existe = cursor.fetchone()['exists']

        if not tabela_existe:
            # Criar tabela
            cursor.execute("""
                CREATE TABLE parametros_globais (
                    id SERIAL PRIMARY KEY,
                    chave VARCHAR(100) UNIQUE NOT NULL,
                    valor TEXT NOT NULL,
                    descricao TEXT,
                    tipo VARCHAR(20) DEFAULT 'string',
                    categoria VARCHAR(50) DEFAULT 'geral',
                    ativo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

            # Inserir parametros padrao
            parametros_padrao = [
                ('cobertura_alvo_dias', '21', 'Cobertura alvo em dias para calculo de pedidos', 'integer', 'pedidos'),
                ('estoque_seguranca_dias', '7', 'Dias de estoque de seguranca', 'integer', 'estoque'),
                ('lead_time_padrao', '15', 'Lead time padrao quando nao ha cadastro especifico', 'integer', 'fornecedor'),
                ('ciclo_pedido_padrao', '7', 'Ciclo de pedido padrao em dias', 'integer', 'fornecedor'),
                ('dias_historico_vendas', '730', 'Dias de historico de vendas a considerar', 'integer', 'previsao'),
                ('dias_transferencia_padrao_compra', '10', 'Dias de lead time para transferencia entre lojas', 'integer', 'transferencia'),
                ('cobertura_minima_doador', '10', 'Cobertura minima em dias que doador deve manter', 'integer', 'transferencia'),
                ('margem_excesso_dias', '7', 'Dias acima do alvo para considerar excesso', 'integer', 'transferencia'),
            ]

            for chave, valor, descricao, tipo, categoria in parametros_padrao:
                cursor.execute("""
                    INSERT INTO parametros_globais (chave, valor, descricao, tipo, categoria)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (chave) DO NOTHING
                """, (chave, valor, descricao, tipo, categoria))

            conn.commit()

        # Buscar parametros
        categoria = request.args.get('categoria')

        query = """
            SELECT id, chave, valor, descricao, tipo, categoria, ativo, updated_at
            FROM parametros_globais
            WHERE ativo = TRUE
        """
        params = []

        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)

        query += " ORDER BY categoria, chave"

        cursor.execute(query, tuple(params) if params else None)
        parametros = cursor.fetchall()

        # Converter para lista
        resultado = []
        for p in parametros:
            item = dict(p)
            if item.get('updated_at'):
                item['updated_at'] = str(item['updated_at'])
            resultado.append(item)

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'parametros': resultado
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_listar_parametros_globais: {e}")
        traceback.print_exc()
        # Fallback: retornar parametros padrao se houver erro
        print("[INFO] Retornando parametros padrao devido a erro")
        return jsonify({
            'success': True,
            'parametros': parametros_padrao_dict,
            'aviso': 'Usando valores padrao (tabela nao disponivel)'
        })


@configuracao_bp.route('/api/parametros-globais/<chave>', methods=['GET'])
def api_obter_parametro_global(chave):
    """Obtem valor de um parametro especifico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT valor, tipo
            FROM parametros_globais
            WHERE chave = %s AND ativo = TRUE
        """, [chave])

        resultado = cursor.fetchone()

        cursor.close()
        conn.close()

        if not resultado:
            return jsonify({'success': False, 'erro': 'Parametro nao encontrado'}), 404

        # Converter valor conforme tipo
        valor = resultado['valor']
        tipo = resultado['tipo']

        if tipo == 'integer':
            valor = int(valor)
        elif tipo == 'float':
            valor = float(valor)
        elif tipo == 'boolean':
            valor = valor.lower() in ('true', '1', 'sim', 'yes')

        return jsonify({
            'success': True,
            'chave': chave,
            'valor': valor,
            'tipo': tipo
        })

    except Exception as e:
        print(f"[ERRO] api_obter_parametro_global: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@configuracao_bp.route('/api/parametros-globais', methods=['POST'])
def api_salvar_parametro_global():
    """Salva ou atualiza um parametro global."""
    try:
        dados = request.get_json()

        chave = dados.get('chave')
        valor = dados.get('valor')
        descricao = dados.get('descricao')
        tipo = dados.get('tipo', 'string')
        categoria = dados.get('categoria', 'geral')

        if not chave or valor is None:
            return jsonify({'success': False, 'erro': 'Chave e valor sao obrigatorios'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO parametros_globais (chave, valor, descricao, tipo, categoria)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (chave) DO UPDATE SET
                valor = EXCLUDED.valor,
                descricao = COALESCE(EXCLUDED.descricao, parametros_globais.descricao),
                tipo = COALESCE(EXCLUDED.tipo, parametros_globais.tipo),
                categoria = COALESCE(EXCLUDED.categoria, parametros_globais.categoria),
                updated_at = CURRENT_TIMESTAMP
        """, (chave, str(valor), descricao, tipo, categoria))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'mensagem': f'Parametro {chave} salvo com sucesso'
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_salvar_parametro_global: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@configuracao_bp.route('/api/parametros-globais/<chave>', methods=['DELETE'])
def api_excluir_parametro_global(chave):
    """Desativa um parametro global."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE parametros_globais
            SET ativo = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE chave = %s
        """, [chave])

        rows_affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()

        if rows_affected == 0:
            return jsonify({'success': False, 'erro': 'Parametro nao encontrado'}), 404

        return jsonify({
            'success': True,
            'mensagem': f'Parametro {chave} desativado com sucesso'
        })

    except Exception as e:
        print(f"[ERRO] api_excluir_parametro_global: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@configuracao_bp.route('/api/parametros-globais/categorias', methods=['GET'])
def api_listar_categorias_parametros():
    """Lista categorias de parametros disponiveis."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT DISTINCT categoria, COUNT(*) as total
            FROM parametros_globais
            WHERE ativo = TRUE
            GROUP BY categoria
            ORDER BY categoria
        """)

        categorias = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'categorias': [dict(c) for c in categorias]
        })

    except Exception as e:
        print(f"[ERRO] api_listar_categorias_parametros: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500
