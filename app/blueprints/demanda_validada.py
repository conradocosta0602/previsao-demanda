"""
Blueprint: Demanda Validada
Rotas: /api/demanda_validada/*
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection

demanda_validada_bp = Blueprint('demanda_validada', __name__)


@demanda_validada_bp.route('/api/demanda_validada/salvar', methods=['POST'])
def api_salvar_demanda_validada():
    """
    Salva demanda validada pelo usuario para um periodo especifico.
    """
    try:
        dados = request.get_json()

        itens = dados.get('itens', [])
        usuario = dados.get('usuario', 'sistema')
        observacao = dados.get('observacao', '')

        if not itens:
            return jsonify({'success': False, 'erro': 'Nenhum item para salvar'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar se tabela existe, criar se necessario
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'demanda_validada'
            )
        """)
        if not cursor.fetchone()[0]:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS demanda_validada (
                    id SERIAL PRIMARY KEY,
                    cod_produto VARCHAR(20) NOT NULL,
                    cod_loja INTEGER NOT NULL,
                    cod_fornecedor INTEGER,
                    data_inicio DATE NOT NULL,
                    data_fim DATE NOT NULL,
                    semana_ano VARCHAR(10),
                    demanda_diaria NUMERIC(12,4),
                    demanda_total_periodo NUMERIC(12,2),
                    data_validacao TIMESTAMP DEFAULT NOW(),
                    usuario_validacao VARCHAR(100),
                    versao INTEGER DEFAULT 1,
                    status VARCHAR(20) DEFAULT 'validado',
                    ativo BOOLEAN DEFAULT TRUE,
                    observacao TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        itens_salvos = 0
        for item in itens:
            cod_produto = str(item.get('cod_produto'))
            cod_loja_raw = item.get('cod_loja')
            cod_loja = int(cod_loja_raw) if cod_loja_raw is not None else 0
            cod_fornecedor = item.get('cod_fornecedor')
            data_inicio = item.get('data_inicio')
            data_fim = item.get('data_fim')
            demanda_diaria = float(item.get('demanda_diaria') or 0)
            demanda_total = float(item.get('demanda_total_periodo') or 0)

            # Calcular semana_ano
            from datetime import datetime as dt
            data_ini = dt.strptime(data_inicio, '%Y-%m-%d')
            semana_ano = f"{data_ini.year}-S{data_ini.isocalendar()[1]:02d}"

            # Desativar validacoes anteriores que se sobrepoem
            cursor.execute("""
                UPDATE demanda_validada
                SET ativo = FALSE, updated_at = NOW()
                WHERE cod_produto = %s
                  AND cod_loja = %s
                  AND ativo = TRUE
                  AND (
                      (data_inicio <= %s AND data_fim >= %s)
                      OR (data_inicio >= %s AND data_inicio <= %s)
                      OR (data_fim >= %s AND data_fim <= %s)
                  )
            """, [cod_produto, cod_loja, data_inicio, data_fim,
                  data_inicio, data_fim, data_inicio, data_fim])

            # Inserir nova validacao
            cursor.execute("""
                INSERT INTO demanda_validada
                (cod_produto, cod_loja, cod_fornecedor, data_inicio, data_fim,
                 semana_ano, demanda_diaria, demanda_total_periodo,
                 usuario_validacao, observacao)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [cod_produto, cod_loja, cod_fornecedor, data_inicio, data_fim,
                  semana_ano, demanda_diaria, demanda_total, usuario, observacao])

            itens_salvos += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'itens_salvos': itens_salvos,
            'mensagem': f'{itens_salvos} itens validados com sucesso'
        })

    except Exception as e:
        print(f"[ERRO] api_salvar_demanda_validada: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@demanda_validada_bp.route('/api/demanda_validada/listar', methods=['GET'])
def api_listar_demanda_validada():
    """Lista demandas validadas com filtros opcionais."""
    try:
        cod_produto = request.args.get('cod_produto')
        cod_loja = request.args.get('cod_loja')
        cod_fornecedor = request.args.get('cod_fornecedor')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        apenas_ativos = request.args.get('apenas_ativos', 'true').lower() == 'true'

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar se tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'demanda_validada'
            )
        """)
        if not cursor.fetchone()['exists']:
            conn.close()
            return jsonify([])

        # Construir query com filtros
        where_conditions = []
        params = []

        if apenas_ativos:
            where_conditions.append("ativo = TRUE")

        if cod_produto:
            where_conditions.append("cod_produto = %s")
            params.append(str(cod_produto))

        if cod_loja:
            where_conditions.append("cod_loja = %s")
            params.append(int(cod_loja))

        if cod_fornecedor:
            where_conditions.append("cod_fornecedor = %s")
            params.append(int(cod_fornecedor))

        if data_inicio:
            where_conditions.append("data_fim >= %s")
            params.append(data_inicio)

        if data_fim:
            where_conditions.append("data_inicio <= %s")
            params.append(data_fim)

        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        cursor.execute(f"""
            SELECT id, cod_produto, cod_loja, cod_fornecedor,
                   data_inicio, data_fim, semana_ano,
                   demanda_diaria, demanda_total_periodo,
                   data_validacao, usuario_validacao,
                   versao, status, observacao
            FROM demanda_validada
            WHERE {where_clause}
            ORDER BY data_validacao DESC
            LIMIT 1000
        """, params)

        resultados = cursor.fetchall()
        conn.close()

        # Converter datas para string
        for r in resultados:
            if r.get('data_inicio'):
                r['data_inicio'] = str(r['data_inicio'])
            if r.get('data_fim'):
                r['data_fim'] = str(r['data_fim'])
            if r.get('data_validacao'):
                r['data_validacao'] = str(r['data_validacao'])

        return jsonify(resultados)

    except Exception as e:
        print(f"[ERRO] api_listar_demanda_validada: {e}")
        return jsonify({'erro': str(e)}), 500


@demanda_validada_bp.route('/api/demanda_validada/buscar_para_periodo', methods=['GET'])
def api_buscar_demanda_validada_periodo():
    """Busca demanda validada para um periodo especifico (usado no pedido planejado)."""
    try:
        cod_loja = request.args.get('cod_loja')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        cod_fornecedor = request.args.get('cod_fornecedor')

        if not cod_loja or not data_inicio or not data_fim:
            return jsonify({'erro': 'Parametros obrigatorios: cod_loja, data_inicio, data_fim'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar se tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'demanda_validada'
            )
        """)
        if not cursor.fetchone()['exists']:
            conn.close()
            return jsonify({'itens': [], 'tem_validacao': False})

        # Buscar validacoes que cobrem o periodo
        params = [int(cod_loja), data_inicio, data_fim]
        fornecedor_filter = ""
        if cod_fornecedor:
            fornecedor_filter = " AND cod_fornecedor = %s"
            params.append(int(cod_fornecedor))

        cursor.execute(f"""
            SELECT cod_produto, cod_loja, cod_fornecedor,
                   data_inicio, data_fim,
                   demanda_diaria, demanda_total_periodo,
                   data_validacao, usuario_validacao
            FROM demanda_validada
            WHERE cod_loja = %s
              AND ativo = TRUE
              AND status = 'validado'
              AND data_inicio <= %s
              AND data_fim >= %s
              {fornecedor_filter}
            ORDER BY data_validacao DESC
        """, params)

        resultados = cursor.fetchall()
        conn.close()

        # Converter para dict indexado por produto
        itens_dict = {}
        for r in resultados:
            cod = str(r['cod_produto'])
            if cod not in itens_dict:
                itens_dict[cod] = {
                    'cod_produto': cod,
                    'demanda_diaria': float(r['demanda_diaria']) if r['demanda_diaria'] else 0,
                    'demanda_total_periodo': float(r['demanda_total_periodo']) if r['demanda_total_periodo'] else 0,
                    'data_validacao': str(r['data_validacao']),
                    'usuario_validacao': r['usuario_validacao']
                }

        return jsonify({
            'itens': list(itens_dict.values()),
            'tem_validacao': len(itens_dict) > 0,
            'total_itens': len(itens_dict)
        })

    except Exception as e:
        print(f"[ERRO] api_buscar_demanda_validada_periodo: {e}")
        return jsonify({'erro': str(e)}), 500
