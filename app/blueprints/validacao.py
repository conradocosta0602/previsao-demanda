"""
Blueprint: Validacao e Conformidade de Metodologia
===================================================
Endpoints para monitoramento e auditoria da conformidade
dos calculos de demanda e pedido.

Autor: Valter Lino / Claude (Anthropic)
Data: Fevereiro 2026
"""

import json
import numpy as np
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template

# Imports do sistema
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.validador_conformidade import ValidadorConformidade
from app.utils.db_connection import get_db_connection


def _converter_tipos_numpy(obj):
    """Converte tipos numpy para tipos nativos Python (JSON-serializaveis)."""
    if isinstance(obj, dict):
        return {k: _converter_tipos_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_converter_tipos_numpy(item) for item in obj]
    elif isinstance(obj, (np.bool_, )):
        return bool(obj)
    elif isinstance(obj, (np.integer, )):
        return int(obj)
    elif isinstance(obj, (np.floating, )):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


validacao_bp = Blueprint('validacao', __name__, url_prefix='/api/validacao')


# =============================================================================
# ENDPOINTS DE EXECUCAO
# =============================================================================

@validacao_bp.route('/executar-checklist', methods=['POST'])
def executar_checklist():
    """
    Executa o checklist completo de conformidade manualmente.

    Retorna:
        JSON com resultado da validacao
    """
    try:
        conn = get_db_connection()
        validador = ValidadorConformidade(conn=conn)

        # Executar checklist
        resultado = validador.executar_checklist_completo()

        # Salvar resultado no banco
        _salvar_resultado_auditoria(conn, resultado, tipo='manual')

        conn.close()

        return jsonify({
            'sucesso': True,
            'resultado': _converter_tipos_numpy(resultado)
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_bp.route('/executar-verificacao/<codigo>', methods=['POST'])
def executar_verificacao_especifica(codigo):
    """
    Executa uma verificacao especifica do checklist.

    Args:
        codigo: Codigo da verificacao (ex: V01_MODULOS)

    Retorna:
        JSON com resultado da verificacao
    """
    try:
        conn = get_db_connection()
        validador = ValidadorConformidade(conn=conn)

        # Mapear codigo para metodo
        mapa_verificacoes = {
            'V01': validador._verificar_modulos_carregam,
            'V02': validador._verificar_metodos_disponiveis,
            'V03': validador._verificar_sma_calcula,
            'V04': validador._verificar_sazonalidade_valida,
            'V05': validador._verificar_saneamento_rupturas,
            'V06': validador._verificar_normalizacao_dias,
            'V07': validador._verificar_corte_data,
            'V08': validador._verificar_formula_pedido,
            'V09': validador._verificar_padrao_compra,
            'V10': validador._verificar_es_abc
        }

        # Extrair prefixo do codigo (ex: V01 de V01_MODULOS)
        prefixo = codigo.split('_')[0] if '_' in codigo else codigo

        if prefixo not in mapa_verificacoes:
            return jsonify({
                'sucesso': False,
                'erro': f'Verificacao nao encontrada: {codigo}'
            }), 404

        # Executar verificacao
        resultado = mapa_verificacoes[prefixo]()

        conn.close()

        return jsonify({
            'sucesso': True,
            'verificacao': codigo,
            'resultado': resultado
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# ENDPOINTS DE CONSULTA
# =============================================================================

@validacao_bp.route('/dashboard', methods=['GET'])
def dashboard_conformidade():
    """
    Retorna metricas de conformidade para dashboard.

    Query params:
        dias: Numero de dias para analise (default: 30)

    Retorna:
        JSON com metricas agregadas
    """
    try:
        dias = request.args.get('dias', 30, type=int)
        conn = get_db_connection()
        cursor = conn.cursor()

        # Metricas dos ultimos N dias
        cursor.execute("""
            SELECT
                COUNT(*) as total_execucoes,
                COUNT(*) FILTER (WHERE status = 'aprovado') as aprovadas,
                COUNT(*) FILTER (WHERE status = 'reprovado') as reprovadas,
                COUNT(*) FILTER (WHERE status = 'alerta') as alertas,
                ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'aprovado') / NULLIF(COUNT(*), 0), 2) as taxa_conformidade,
                AVG(tempo_execucao_ms) as tempo_medio_ms
            FROM auditoria_conformidade
            WHERE data_execucao >= NOW() - INTERVAL '%s days'
        """, (dias,))

        row = cursor.fetchone()
        metricas_periodo = {
            'total_execucoes': row[0] or 0,
            'aprovadas': row[1] or 0,
            'reprovadas': row[2] or 0,
            'alertas': row[3] or 0,
            'taxa_conformidade': float(row[4]) if row[4] else 100.0,
            'tempo_medio_ms': float(row[5]) if row[5] else 0
        }

        # Ultima execucao
        cursor.execute("""
            SELECT
                data_execucao,
                tipo,
                status,
                total_verificacoes,
                verificacoes_ok,
                verificacoes_falha,
                tempo_execucao_ms,
                detalhes
            FROM auditoria_conformidade
            ORDER BY data_execucao DESC
            LIMIT 1
        """)

        ultima = cursor.fetchone()
        ultima_execucao = None
        if ultima:
            ultima_execucao = {
                'data': ultima[0].isoformat() if ultima[0] else None,
                'tipo': ultima[1],
                'status': ultima[2],
                'total_verificacoes': ultima[3],
                'verificacoes_ok': ultima[4],
                'verificacoes_falha': ultima[5],
                'tempo_ms': ultima[6],
                'detalhes': ultima[7]
            }

        # Historico diario (ultimos 7 dias)
        cursor.execute("""
            SELECT
                DATE(data_execucao) as data,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'aprovado') as aprovadas,
                COUNT(*) FILTER (WHERE status != 'aprovado') as falhas
            FROM auditoria_conformidade
            WHERE data_execucao >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(data_execucao)
            ORDER BY data DESC
        """)

        historico = []
        for row in cursor.fetchall():
            historico.append({
                'data': row[0].isoformat() if row[0] else None,
                'total': row[1],
                'aprovadas': row[2],
                'falhas': row[3]
            })

        # Calcular tendencia
        if len(historico) >= 2:
            taxa_recente = historico[0]['aprovadas'] / max(historico[0]['total'], 1)
            taxa_anterior = historico[-1]['aprovadas'] / max(historico[-1]['total'], 1)

            if taxa_recente > taxa_anterior + 0.05:
                tendencia = 'melhorando'
            elif taxa_recente < taxa_anterior - 0.05:
                tendencia = 'piorando'
            else:
                tendencia = 'estavel'
        else:
            tendencia = 'sem_dados'

        # Alertas pendentes (reprovacoes recentes)
        cursor.execute("""
            SELECT
                data_execucao,
                status,
                detalhes
            FROM auditoria_conformidade
            WHERE status != 'aprovado'
              AND data_execucao >= NOW() - INTERVAL '24 hours'
            ORDER BY data_execucao DESC
            LIMIT 5
        """)

        alertas_pendentes = []
        for row in cursor.fetchall():
            alertas_pendentes.append({
                'data': row[0].isoformat() if row[0] else None,
                'status': row[1],
                'detalhes': row[2]
            })

        conn.close()

        return jsonify({
            'sucesso': True,
            'periodo_dias': dias,
            'metricas': metricas_periodo,
            'ultima_execucao': ultima_execucao,
            'historico_diario': historico,
            'tendencia': tendencia,
            'alertas_pendentes': alertas_pendentes
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_bp.route('/historico', methods=['GET'])
def historico_conformidade():
    """
    Retorna historico de execucoes do checklist.

    Query params:
        limite: Numero maximo de registros (default: 50)
        offset: Offset para paginacao (default: 0)
        status: Filtrar por status (opcional)
        tipo: Filtrar por tipo (opcional)

    Retorna:
        JSON com lista de execucoes
    """
    try:
        limite = request.args.get('limite', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status_filtro = request.args.get('status')
        tipo_filtro = request.args.get('tipo')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Construir query com filtros
        query = """
            SELECT
                id,
                data_execucao,
                tipo,
                status,
                total_verificacoes,
                verificacoes_ok,
                verificacoes_falha,
                verificacoes_alerta,
                tempo_execucao_ms,
                alerta_enviado
            FROM auditoria_conformidade
            WHERE 1=1
        """
        params = []

        if status_filtro:
            query += " AND status = %s"
            params.append(status_filtro)

        if tipo_filtro:
            query += " AND tipo = %s"
            params.append(tipo_filtro)

        query += " ORDER BY data_execucao DESC LIMIT %s OFFSET %s"
        params.extend([limite, offset])

        cursor.execute(query, params)

        execucoes = []
        for row in cursor.fetchall():
            execucoes.append({
                'id': row[0],
                'data_execucao': row[1].isoformat() if row[1] else None,
                'tipo': row[2],
                'status': row[3],
                'total_verificacoes': row[4],
                'verificacoes_ok': row[5],
                'verificacoes_falha': row[6],
                'verificacoes_alerta': row[7],
                'tempo_execucao_ms': row[8],
                'alerta_enviado': row[9]
            })

        # Contar total para paginacao
        count_query = "SELECT COUNT(*) FROM auditoria_conformidade WHERE 1=1"
        count_params = []

        if status_filtro:
            count_query += " AND status = %s"
            count_params.append(status_filtro)

        if tipo_filtro:
            count_query += " AND tipo = %s"
            count_params.append(tipo_filtro)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'sucesso': True,
            'execucoes': execucoes,
            'paginacao': {
                'total': total,
                'limite': limite,
                'offset': offset,
                'paginas': (total + limite - 1) // limite if limite > 0 else 0
            }
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_bp.route('/detalhes/<int:execucao_id>', methods=['GET'])
def detalhes_execucao(execucao_id):
    """
    Retorna detalhes completos de uma execucao especifica.

    Args:
        execucao_id: ID da execucao

    Retorna:
        JSON com detalhes da execucao
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                data_execucao,
                tipo,
                status,
                total_verificacoes,
                verificacoes_ok,
                verificacoes_falha,
                verificacoes_alerta,
                detalhes,
                tempo_execucao_ms,
                alerta_enviado,
                alerta_destinatarios,
                created_at
            FROM auditoria_conformidade
            WHERE id = %s
        """, (execucao_id,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({
                'sucesso': False,
                'erro': 'Execucao nao encontrada'
            }), 404

        execucao = {
            'id': row[0],
            'data_execucao': row[1].isoformat() if row[1] else None,
            'tipo': row[2],
            'status': row[3],
            'total_verificacoes': row[4],
            'verificacoes_ok': row[5],
            'verificacoes_falha': row[6],
            'verificacoes_alerta': row[7],
            'detalhes': row[8],
            'tempo_execucao_ms': row[9],
            'alerta_enviado': row[10],
            'alerta_destinatarios': row[11],
            'created_at': row[12].isoformat() if row[12] else None
        }

        conn.close()

        return jsonify({
            'sucesso': True,
            'execucao': execucao
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# ENDPOINTS DE AUDITORIA DE CALCULOS
# =============================================================================

@validacao_bp.route('/calculos', methods=['GET'])
def listar_calculos():
    """
    Lista calculos auditados com filtros.

    Query params:
        limite: Numero maximo de registros (default: 50)
        offset: Offset para paginacao (default: 0)
        tipo: Tipo de calculo (demanda, pedido)
        fornecedor: Codigo do fornecedor
        produto: Codigo do produto
        validacao: true/false para filtrar por validacao

    Retorna:
        JSON com lista de calculos
    """
    try:
        limite = request.args.get('limite', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        tipo_filtro = request.args.get('tipo')
        fornecedor_filtro = request.args.get('fornecedor', type=int)
        produto_filtro = request.args.get('produto')
        validacao_filtro = request.args.get('validacao')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Construir query com filtros
        query = """
            SELECT
                id,
                data_calculo,
                tipo_calculo,
                cod_produto,
                cod_empresa,
                cod_fornecedor,
                nome_fornecedor,
                metodo_usado,
                categoria_serie,
                confianca,
                validacao_ok,
                observacoes
            FROM auditoria_calculos
            WHERE 1=1
        """
        params = []

        if tipo_filtro:
            query += " AND tipo_calculo = %s"
            params.append(tipo_filtro)

        if fornecedor_filtro:
            query += " AND cod_fornecedor = %s"
            params.append(fornecedor_filtro)

        if produto_filtro:
            query += " AND cod_produto = %s"
            params.append(produto_filtro)

        if validacao_filtro is not None:
            query += " AND validacao_ok = %s"
            params.append(validacao_filtro.lower() == 'true')

        query += " ORDER BY data_calculo DESC LIMIT %s OFFSET %s"
        params.extend([limite, offset])

        cursor.execute(query, params)

        calculos = []
        for row in cursor.fetchall():
            calculos.append({
                'id': row[0],
                'data_calculo': row[1].isoformat() if row[1] else None,
                'tipo_calculo': row[2],
                'cod_produto': row[3],
                'cod_empresa': row[4],
                'cod_fornecedor': row[5],
                'nome_fornecedor': row[6],
                'metodo_usado': row[7],
                'categoria_serie': row[8],
                'confianca': row[9],
                'validacao_ok': row[10],
                'observacoes': row[11]
            })

        conn.close()

        return jsonify({
            'sucesso': True,
            'calculos': calculos,
            'paginacao': {
                'limite': limite,
                'offset': offset
            }
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@validacao_bp.route('/metodos-utilizados', methods=['GET'])
def metodos_utilizados():
    """
    Retorna estatisticas de metodos de calculo utilizados.

    Query params:
        dias: Numero de dias para analise (default: 30)

    Retorna:
        JSON com estatisticas por metodo
    """
    try:
        dias = request.args.get('dias', 30, type=int)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                metodo_usado,
                COUNT(*) as total_usos,
                COUNT(*) FILTER (WHERE validacao_ok = TRUE) as validacoes_ok,
                ROUND(100.0 * COUNT(*) FILTER (WHERE validacao_ok = TRUE) / NULLIF(COUNT(*), 0), 2) as taxa_sucesso,
                DATE(MIN(data_calculo)) as primeiro_uso,
                DATE(MAX(data_calculo)) as ultimo_uso
            FROM auditoria_calculos
            WHERE data_calculo >= NOW() - INTERVAL '%s days'
              AND metodo_usado IS NOT NULL
            GROUP BY metodo_usado
            ORDER BY total_usos DESC
        """, (dias,))

        metodos = []
        for row in cursor.fetchall():
            metodos.append({
                'metodo': row[0],
                'total_usos': row[1],
                'validacoes_ok': row[2],
                'taxa_sucesso': float(row[3]) if row[3] else 100.0,
                'primeiro_uso': row[4].isoformat() if row[4] else None,
                'ultimo_uso': row[5].isoformat() if row[5] else None
            })

        conn.close()

        return jsonify({
            'sucesso': True,
            'periodo_dias': dias,
            'metodos': metodos
        })

    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================

def _salvar_resultado_auditoria(conn, resultado: dict, tipo: str = 'manual'):
    """
    Salva resultado do checklist na tabela de auditoria.

    Args:
        conn: Conexao com banco de dados
        resultado: Dicionario com resultado do checklist
        tipo: Tipo de execucao (manual, cronjob_diario, tempo_real)
    """
    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO auditoria_conformidade (
                data_execucao,
                tipo,
                status,
                total_verificacoes,
                verificacoes_ok,
                verificacoes_falha,
                verificacoes_alerta,
                detalhes,
                tempo_execucao_ms
            ) VALUES (
                NOW(),
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            tipo,
            resultado.get('status', 'erro'),
            resultado.get('total_verificacoes', 0),
            resultado.get('verificacoes_ok', 0),
            resultado.get('verificacoes_falha', 0),
            resultado.get('verificacoes_alerta', 0),
            json.dumps(resultado.get('verificacoes', [])),
            resultado.get('tempo_execucao_ms')
        ))

        conn.commit()

    except Exception as e:
        print(f"Erro ao salvar auditoria: {e}")
        conn.rollback()
