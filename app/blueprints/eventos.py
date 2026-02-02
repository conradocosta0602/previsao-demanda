"""
Blueprint: Eventos V2
Rotas: /eventos_v2, /eventos/v2/*
"""

import os
import tempfile
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, send_file

eventos_bp = Blueprint('eventos', __name__)


@eventos_bp.route('/eventos_v2')
def eventos_v2_page():
    """Pagina de gestao de eventos V2"""
    return render_template('eventos_v2.html')


@eventos_bp.route('/eventos/v2/listar', methods=['GET'])
def listar_eventos_v2():
    """Lista eventos V2 com filtros"""
    try:
        from core.event_manager_v2 import EventManagerV2

        status = request.args.get('status')
        incluir_expirados = request.args.get('incluir_expirados', 'true') == 'true'

        manager = EventManagerV2()
        eventos = manager.listar_eventos(
            status=status,
            incluir_expirados=incluir_expirados
        )

        return jsonify({
            'success': True,
            'eventos': eventos,
            'total': len(eventos)
        })

    except Exception as e:
        print(f"[ERRO] listar_eventos_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/buscar/<int:evento_id>', methods=['GET'])
def buscar_evento_v2(evento_id):
    """Busca evento V2 por ID com historico"""
    try:
        from core.event_manager_v2 import EventManagerV2

        manager = EventManagerV2()
        evento = manager.buscar_evento(evento_id)

        if evento:
            return jsonify({'success': True, 'evento': evento})
        else:
            return jsonify({'success': False, 'erro': 'Evento nao encontrado'}), 404

    except Exception as e:
        print(f"[ERRO] buscar_evento_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/cadastrar', methods=['POST'])
def cadastrar_evento_v2():
    """Cadastra novo evento V2"""
    try:
        from core.event_manager_v2 import EventManagerV2

        dados = request.get_json()

        manager = EventManagerV2()
        evento_id = manager.cadastrar_evento(
            nome=dados['nome'],
            impacto_percentual=float(dados['impacto_percentual']),
            data_inicio=dados['data_inicio'],
            data_fim=dados['data_fim'],
            tipo=dados.get('tipo', 'CUSTOM'),
            descricao=dados.get('descricao'),
            recorrente_anual=dados.get('recorrente_anual', False),
            filtros=dados.get('filtros'),
            usuario=dados.get('usuario', 'web')
        )

        return jsonify({
            'success': True,
            'evento_id': evento_id,
            'mensagem': 'Evento cadastrado com sucesso'
        })

    except Exception as e:
        print(f"[ERRO] cadastrar_evento_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/atualizar', methods=['POST'])
def atualizar_evento_v2():
    """Atualiza evento V2 existente"""
    try:
        from core.event_manager_v2 import EventManagerV2

        dados = request.get_json()
        evento_id = dados['evento_id']

        manager = EventManagerV2()

        # Atualizar dados principais
        manager.atualizar_evento(
            evento_id=evento_id,
            nome=dados.get('nome'),
            impacto_percentual=dados.get('impacto_percentual'),
            data_inicio=dados.get('data_inicio'),
            data_fim=dados.get('data_fim'),
            tipo=dados.get('tipo'),
            descricao=dados.get('descricao'),
            recorrente_anual=dados.get('recorrente_anual'),
            usuario=dados.get('usuario', 'web')
        )

        # Atualizar filtros se fornecidos
        if 'filtros' in dados:
            manager.atualizar_filtros_evento(
                evento_id=evento_id,
                filtros=dados['filtros'],
                usuario=dados.get('usuario', 'web')
            )

        return jsonify({
            'success': True,
            'mensagem': 'Evento atualizado com sucesso'
        })

    except Exception as e:
        print(f"[ERRO] atualizar_evento_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/cancelar', methods=['POST'])
def cancelar_evento_v2():
    """Cancela evento V2 (mantem historico)"""
    try:
        from core.event_manager_v2 import EventManagerV2

        dados = request.get_json()
        evento_id = dados['evento_id']

        manager = EventManagerV2()
        manager.cancelar_evento(evento_id, usuario=dados.get('usuario', 'web'))

        return jsonify({
            'success': True,
            'mensagem': 'Evento cancelado'
        })

    except Exception as e:
        print(f"[ERRO] cancelar_evento_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/excluir', methods=['POST'])
def excluir_evento_v2():
    """Exclui evento V2 permanentemente"""
    try:
        from core.event_manager_v2 import EventManagerV2

        dados = request.get_json()
        evento_id = dados['evento_id']

        manager = EventManagerV2()
        manager.excluir_evento(evento_id, usuario=dados.get('usuario', 'web'))

        return jsonify({
            'success': True,
            'mensagem': 'Evento excluido permanentemente'
        })

    except Exception as e:
        print(f"[ERRO] excluir_evento_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/alertas', methods=['GET'])
def alertas_eventos_v2():
    """Obtem alertas de eventos proximos e expirados"""
    try:
        from core.event_manager_v2 import EventManagerV2

        dias = int(request.args.get('dias', 7))

        manager = EventManagerV2()
        alertas = manager.obter_alertas(dias_antecedencia=dias)

        return jsonify({
            'success': True,
            'alertas': alertas
        })

    except Exception as e:
        print(f"[ERRO] alertas_eventos_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/importar', methods=['POST'])
def importar_eventos_v2():
    """Importa eventos de arquivo Excel/CSV"""
    try:
        from core.event_manager_v2 import EventManagerV2

        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        arquivo = request.files['arquivo']

        # Salvar temporariamente
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, arquivo.filename)
        arquivo.save(temp_path)

        try:
            manager = EventManagerV2()
            stats = manager.importar_eventos_excel(temp_path, usuario='web')

            return jsonify({
                'success': True,
                'stats': stats
            })
        finally:
            # Limpar arquivo temporario
            os.remove(temp_path)
            os.rmdir(temp_dir)

    except Exception as e:
        print(f"[ERRO] importar_eventos_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/exportar', methods=['GET'])
def exportar_eventos_v2():
    """Exporta eventos para Excel"""
    try:
        from core.event_manager_v2 import EventManagerV2

        # Criar arquivo temporario
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, 'eventos_exportados.xlsx')

        manager = EventManagerV2()
        total = manager.exportar_eventos_excel(temp_path)

        return send_file(
            temp_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='eventos_exportados.xlsx'
        )

    except Exception as e:
        print(f"[ERRO] exportar_eventos_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/acuracia', methods=['GET'])
def relatorio_acuracia_v2():
    """Retorna relatorio de acuracia dos eventos"""
    try:
        from core.event_manager_v2 import EventManagerV2

        manager = EventManagerV2()
        relatorio = manager.obter_relatorio_acuracia()

        return jsonify({
            'success': True,
            'relatorio': relatorio
        })

    except Exception as e:
        print(f"[ERRO] relatorio_acuracia_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/calcular_fator', methods=['POST'])
def calcular_fator_eventos_v2():
    """Calcula fator de eventos para um item especifico"""
    try:
        from core.event_manager_v2 import EventManagerV2

        dados = request.get_json()

        manager = EventManagerV2()

        # Converter datas se fornecidas
        data_inicio = None
        data_fim = None
        if dados.get('data_inicio'):
            data_inicio = datetime.strptime(dados['data_inicio'], '%Y-%m-%d').date()
        if dados.get('data_fim'):
            data_fim = datetime.strptime(dados['data_fim'], '%Y-%m-%d').date()

        resultado = manager.calcular_fator_eventos(
            codigo=int(dados['codigo']),
            cod_empresa=int(dados['cod_empresa']),
            cod_fornecedor=dados.get('cod_fornecedor'),
            linha1=dados.get('linha1'),
            linha3=dados.get('linha3'),
            data_inicio=data_inicio,
            data_fim=data_fim
        )

        return jsonify({
            'success': True,
            'resultado': resultado
        })

    except Exception as e:
        print(f"[ERRO] calcular_fator_eventos_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@eventos_bp.route('/eventos/v2/atualizar_status', methods=['POST'])
def atualizar_status_eventos_v2():
    """Atualiza status de todos os eventos (expirar pendentes, etc)"""
    try:
        from core.event_manager_v2 import EventManagerV2

        manager = EventManagerV2()
        stats = manager.atualizar_status_eventos()

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        print(f"[ERRO] atualizar_status_eventos_v2: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500
