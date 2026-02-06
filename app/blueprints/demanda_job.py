"""
Blueprint: Gerenciamento de Demanda Pre-Calculada
Rotas: /api/demanda_job/*

Endpoints para:
- Recalculo manual de demanda por fornecedor
- Status do job de calculo
- Ajustes manuais de demanda
"""

import sys
import os
from datetime import datetime
from flask import Blueprint, request, jsonify

from app.utils.db_connection import get_db_connection
from app.utils.demanda_pre_calculada import (
    verificar_dados_disponiveis,
    registrar_ajuste_manual,
    limpar_ajuste_manual,
    buscar_demanda_pre_calculada,
    buscar_demanda_proximos_meses
)

demanda_job_bp = Blueprint('demanda_job', __name__)


@demanda_job_bp.route('/api/demanda_job/status', methods=['GET'])
def api_demanda_job_status():
    """
    Retorna status do job de calculo de demanda.

    Returns:
        JSON com estatisticas e ultimas execucoes
    """
    try:
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Estatisticas gerais
        stats = verificar_dados_disponiveis(conn)

        # Ultimas execucoes
        cursor.execute("""
            SELECT
                id, data_execucao, tipo, status,
                total_itens_processados, total_itens_erro,
                total_fornecedores, tempo_execucao_ms,
                cnpj_fornecedor_filtro
            FROM demanda_calculo_execucao
            ORDER BY data_execucao DESC
            LIMIT 10
        """)
        execucoes = [dict(row) for row in cursor.fetchall()]

        # Converter datetime para string
        for exec in execucoes:
            if exec.get('data_execucao'):
                exec['data_execucao'] = exec['data_execucao'].isoformat()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'estatisticas': stats,
            'ultimas_execucoes': execucoes
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500


@demanda_job_bp.route('/api/demanda_job/status/<cnpj_fornecedor>', methods=['GET'])
def api_demanda_job_status_fornecedor(cnpj_fornecedor):
    """
    Retorna status do calculo de demanda para um fornecedor especifico.

    Usado para polling do frontend apos iniciar calculo em background.

    Args:
        cnpj_fornecedor: CNPJ do fornecedor

    Returns:
        JSON com status atual do calculo
    """
    try:
        conn = get_db_connection()
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Buscar ultima execucao deste fornecedor
        cursor.execute("""
            SELECT
                id, data_execucao, tipo, status,
                total_itens_processados, total_itens_erro,
                total_fornecedores, tempo_execucao_ms,
                cnpj_fornecedor_filtro
            FROM demanda_calculo_execucao
            WHERE cnpj_fornecedor_filtro = %s
            ORDER BY data_execucao DESC
            LIMIT 1
        """, (cnpj_fornecedor,))
        execucao = cursor.fetchone()

        if not execucao:
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'status': 'sem_execucao',
                'mensagem': 'Nenhuma execucao encontrada para este fornecedor'
            })

        execucao = dict(execucao)

        # Converter datetime para string
        if execucao.get('data_execucao'):
            execucao['data_execucao'] = execucao['data_execucao'].isoformat()

        # Contar registros atuais para este fornecedor
        cursor.execute("""
            SELECT COUNT(*) as total_registros,
                   COUNT(DISTINCT cod_produto) as total_produtos
            FROM demanda_pre_calculada
            WHERE cnpj_fornecedor = %s
        """, (cnpj_fornecedor,))
        contagem = cursor.fetchone()

        cursor.close()
        conn.close()

        # Determinar se o calculo esta completo
        # Aceitar 'concluido', 'sucesso' ou 'parcial' como estados de conclusao
        status = execucao.get('status', '')
        is_concluido = status in ('concluido', 'sucesso', 'parcial')
        is_erro = status == 'erro'
        is_processando = status in ('iniciado', 'processando')

        return jsonify({
            'success': True,
            'status': execucao.get('status', 'desconhecido'),
            'is_concluido': is_concluido,
            'is_erro': is_erro,
            'is_processando': is_processando,
            'execucao': execucao,
            'dados_atuais': {
                'total_registros': contagem['total_registros'] if contagem else 0,
                'total_produtos': contagem['total_produtos'] if contagem else 0
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500


@demanda_job_bp.route('/api/demanda_job/recalcular', methods=['POST'])
def api_demanda_job_recalcular():
    """
    Inicia recalculo de demanda para um ou todos os fornecedores.

    Request JSON:
    {
        "cnpj_fornecedor": "60620366000195" ou "NOME FORNECEDOR"  # Opcional
        "async": true  # Se true, executa em background e retorna imediatamente
    }

    Returns:
        JSON com resultado do recalculo (ou status de inicio se async)
    """
    import threading

    try:
        # Adicionar pasta raiz ao path para importar jobs
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if ROOT_DIR not in sys.path:
            sys.path.insert(0, ROOT_DIR)

        from jobs.calcular_demanda_diaria import executar_calculo, buscar_fornecedores, buscar_itens_fornecedor, obter_conexao

        dados = request.get_json() or {}
        cnpj_filtro = dados.get('cnpj_fornecedor')
        executar_async = dados.get('async', True)  # Por padrao, executa em background

        # Normalizar cnpj_filtro: se veio como lista, pegar o primeiro elemento
        if isinstance(cnpj_filtro, list):
            cnpj_filtro = cnpj_filtro[0] if cnpj_filtro else None

        # Verificar quantidade de itens para estimar tempo
        if cnpj_filtro:
            conn = obter_conexao()
            fornecedores = buscar_fornecedores(conn, cnpj_filtro)
            total_itens_estimado = 0
            nome_fornecedor = cnpj_filtro

            if fornecedores:
                for f in fornecedores:
                    itens = buscar_itens_fornecedor(conn, f['cnpj_fornecedor'])
                    total_itens_estimado += len(itens)
                    nome_fornecedor = f['nome_fornecedor']
            conn.close()

            if not fornecedores:
                return jsonify({
                    'success': False,
                    'erro': f'Fornecedor nao encontrado: {cnpj_filtro}'
                }), 404

        # Se async, executar em thread separada
        if executar_async:
            def executar_em_background():
                try:
                    if cnpj_filtro:
                        executar_calculo(tipo='recalculo_fornecedor', cnpj_filtro=cnpj_filtro)
                    else:
                        executar_calculo(tipo='manual')
                except Exception as e:
                    print(f"[ERRO] Calculo em background: {e}")

            thread = threading.Thread(target=executar_em_background)
            thread.daemon = True
            thread.start()

            return jsonify({
                'success': True,
                'async': True,
                'mensagem': f'Calculo iniciado em background para {nome_fornecedor if cnpj_filtro else "todos os fornecedores"}',
                'resultado': {
                    'total_itens': total_itens_estimado if cnpj_filtro else 0,
                    'total_registros': total_itens_estimado * 12 if cnpj_filtro else 0,  # Estimativa: 12 meses por item
                    'total_erros': 0,
                    'total_fornecedores': len(fornecedores) if cnpj_filtro else 0,
                    'tempo_ms': 0
                }
            })

        # Se sincrono, executar e aguardar
        if cnpj_filtro:
            resultado = executar_calculo(tipo='recalculo_fornecedor', cnpj_filtro=cnpj_filtro)
        else:
            resultado = executar_calculo(tipo='manual')

        return jsonify({
            'success': True,
            'async': False,
            'resultado': {
                'total_itens': resultado.get('total_itens', 0),
                'total_registros': resultado.get('total_registros', 0),
                'total_erros': resultado.get('total_erros', 0),
                'total_fornecedores': resultado.get('total_fornecedores', 0),
                'tempo_ms': resultado.get('tempo_ms', 0)
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500


@demanda_job_bp.route('/api/demanda_job/ajustar', methods=['POST'])
def api_demanda_job_ajustar():
    """
    Registra um ajuste manual de demanda.

    O ajuste manual sobrepoe o valor calculado automaticamente.

    Request JSON:
    {
        "cod_produto": "123456",
        "cnpj_fornecedor": "60620366000195",
        "ano": 2026,
        "mes": 2,
        "valor_ajuste": 150.0,
        "usuario": "valter.lino",
        "motivo": "Promocao planejada"
    }

    Returns:
        JSON com ID do registro atualizado
    """
    try:
        dados = request.get_json()

        # Validar campos obrigatorios
        campos_obrigatorios = ['cod_produto', 'cnpj_fornecedor', 'ano', 'mes', 'valor_ajuste', 'usuario']
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({
                    'success': False,
                    'erro': f'Campo obrigatorio ausente: {campo}'
                }), 400

        conn = get_db_connection()

        registro_id = registrar_ajuste_manual(
            conn=conn,
            cod_produto=dados['cod_produto'],
            cnpj_fornecedor=dados['cnpj_fornecedor'],
            ano=dados['ano'],
            mes=dados['mes'],
            valor_ajuste=dados['valor_ajuste'],
            usuario=dados['usuario'],
            motivo=dados.get('motivo'),
            cod_empresa=dados.get('cod_empresa')
        )

        conn.close()

        return jsonify({
            'success': True,
            'registro_id': registro_id,
            'mensagem': f'Ajuste manual registrado com sucesso para {dados["cod_produto"]} em {dados["mes"]}/{dados["ano"]}'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500


@demanda_job_bp.route('/api/demanda_job/remover_ajuste', methods=['POST'])
def api_demanda_job_remover_ajuste():
    """
    Remove um ajuste manual, voltando a usar o valor calculado.

    Request JSON:
    {
        "cod_produto": "123456",
        "cnpj_fornecedor": "60620366000195",
        "ano": 2026,
        "mes": 2
    }

    Returns:
        JSON com status da remocao
    """
    try:
        dados = request.get_json()

        # Validar campos obrigatorios
        campos_obrigatorios = ['cod_produto', 'cnpj_fornecedor', 'ano', 'mes']
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({
                    'success': False,
                    'erro': f'Campo obrigatorio ausente: {campo}'
                }), 400

        conn = get_db_connection()

        removido = limpar_ajuste_manual(
            conn=conn,
            cod_produto=dados['cod_produto'],
            cnpj_fornecedor=dados['cnpj_fornecedor'],
            ano=dados['ano'],
            mes=dados['mes'],
            cod_empresa=dados.get('cod_empresa')
        )

        conn.close()

        if removido:
            return jsonify({
                'success': True,
                'mensagem': f'Ajuste manual removido para {dados["cod_produto"]} em {dados["mes"]}/{dados["ano"]}'
            })
        else:
            return jsonify({
                'success': False,
                'erro': 'Nenhum ajuste manual encontrado para remover'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500


@demanda_job_bp.route('/api/demanda_job/consultar', methods=['GET'])
def api_demanda_job_consultar():
    """
    Consulta demanda pre-calculada de um item.

    Query params:
        cod_produto: Codigo do produto
        cnpj_fornecedor: CNPJ do fornecedor
        ano: Ano (opcional, default: atual)
        mes: Mes (opcional, default: atual)
        meses: Numero de meses a consultar (opcional, para consulta de varios meses)

    Returns:
        JSON com dados da demanda
    """
    try:
        cod_produto = request.args.get('cod_produto')
        cnpj_fornecedor = request.args.get('cnpj_fornecedor')
        ano = request.args.get('ano', type=int)
        mes = request.args.get('mes', type=int)
        meses = request.args.get('meses', type=int)

        if not cod_produto or not cnpj_fornecedor:
            return jsonify({
                'success': False,
                'erro': 'Parametros cod_produto e cnpj_fornecedor sao obrigatorios'
            }), 400

        conn = get_db_connection()

        if meses:
            # Consultar varios meses
            dados = buscar_demanda_proximos_meses(
                conn=conn,
                cod_produto=cod_produto,
                cnpj_fornecedor=cnpj_fornecedor,
                meses=meses,
                cod_empresa=request.args.get('cod_empresa', type=int)
            )

            # Converter datetime para string
            for d in dados:
                if d.get('data_calculo'):
                    d['data_calculo'] = d['data_calculo'].isoformat()
                if d.get('ajuste_manual_data'):
                    d['ajuste_manual_data'] = d['ajuste_manual_data'].isoformat()

            conn.close()

            return jsonify({
                'success': True,
                'dados': dados,
                'total': len(dados)
            })

        else:
            # Consultar mes especifico
            dados = buscar_demanda_pre_calculada(
                conn=conn,
                cod_produto=cod_produto,
                cnpj_fornecedor=cnpj_fornecedor,
                ano=ano,
                mes=mes,
                cod_empresa=request.args.get('cod_empresa', type=int)
            )

            conn.close()

            if dados:
                # Converter datetime para string
                if dados.get('data_calculo'):
                    dados['data_calculo'] = dados['data_calculo'].isoformat()
                if dados.get('ajuste_manual_data'):
                    dados['ajuste_manual_data'] = dados['ajuste_manual_data'].isoformat()

                return jsonify({
                    'success': True,
                    'dados': dados
                })
            else:
                return jsonify({
                    'success': False,
                    'erro': 'Nenhum dado encontrado para os parametros informados'
                }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'erro': str(e)
        }), 500
