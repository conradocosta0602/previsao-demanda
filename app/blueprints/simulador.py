"""
Blueprint: Simulador de Cenarios
Rotas: /simulador, /simulador/dados, /simulador/aplicar, /simulador/exportar
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file, current_app

from app.utils.previsao_helper import get_ultima_previsao_data

simulador_bp = Blueprint('simulador', __name__)


@simulador_bp.route('')
def simulador():
    """Pagina do simulador de cenarios"""
    return render_template('simulador.html')


@simulador_bp.route('/dados', methods=['GET'])
def get_dados_simulador():
    """
    Retorna dados da ultima previsao para o simulador
    """
    ultima_previsao_data = get_ultima_previsao_data()

    if ultima_previsao_data is None:
        return jsonify({
            'success': False,
            'erro': 'Nenhuma previsao disponivel. Processe uma previsao primeiro na pagina principal.'
        }), 404

    # Transformar dados para formato esperado pelo simulador
    dados_formatados = {
        'previsoes': ultima_previsao_data.get('previsoes_lojas', []),
        'lojas': ultima_previsao_data.get('lojas', []),
        'skus': ultima_previsao_data.get('skus', [])
    }

    # Normalizar nomes de campos para minusculas (JavaScript espera lowercase)
    for prev in dados_formatados['previsoes']:
        if 'Loja' in prev:
            prev['loja'] = prev['Loja']
        if 'SKU' in prev:
            prev['sku'] = prev['SKU']
        if 'Mes_Previsao' in prev:
            prev['mes'] = prev['Mes_Previsao']
        if 'Previsao' in prev:
            prev['previsao'] = prev['Previsao']

    return jsonify({
        'success': True,
        'dados': dados_formatados
    })


@simulador_bp.route('/aplicar', methods=['POST'])
def aplicar_cenario():
    """
    Aplica um cenario de simulacao
    """
    ultima_previsao_data = get_ultima_previsao_data()

    if ultima_previsao_data is None:
        return jsonify({
            'success': False,
            'erro': 'Nenhuma previsao disponivel'
        }), 404

    try:
        from core.scenario_simulator import criar_simulador_de_dados

        # Criar simulador
        simulador = criar_simulador_de_dados(ultima_previsao_data['previsoes_lojas'])

        # Obter tipo de ajuste
        dados_request = request.get_json()
        tipo_ajuste = dados_request.get('tipo')

        # Aplicar cenario
        if tipo_ajuste == 'predefinido':
            cenario = dados_request.get('cenario')
            simulador.aplicar_cenario_predefinido(cenario)

        elif tipo_ajuste == 'global':
            percentual = float(dados_request.get('percentual', 0))
            simulador.aplicar_ajuste_global(percentual)

        elif tipo_ajuste == 'por_loja':
            loja = dados_request.get('loja')
            percentual = float(dados_request.get('percentual', 0))
            simulador.aplicar_ajuste_por_loja(loja, percentual)

        elif tipo_ajuste == 'por_sku':
            sku = dados_request.get('sku')
            percentual = float(dados_request.get('percentual', 0))
            simulador.aplicar_ajuste_por_sku(sku, percentual)

        elif tipo_ajuste == 'por_mes':
            mes = int(dados_request.get('mes'))
            percentual = float(dados_request.get('percentual', 0))
            simulador.aplicar_ajuste_por_mes(mes, percentual)

        else:
            return jsonify({'success': False, 'erro': 'Tipo de ajuste invalido'}), 400

        # Calcular impacto
        impacto = simulador.calcular_impacto()

        # Obter comparacao
        df_comp = simulador.get_comparacao()

        # Converter para lista de dicts
        previsoes_comparacao = df_comp.to_dict('records')

        # Serializar datas
        for prev in previsoes_comparacao:
            if 'Mes_Previsao' in prev and hasattr(prev['Mes_Previsao'], 'strftime'):
                prev['Mes_Previsao'] = prev['Mes_Previsao'].strftime('%Y-%m-%d')

        return jsonify({
            'success': True,
            'cenario_nome': simulador.cenario_nome,
            'previsoes_comparacao': previsoes_comparacao,
            'impacto': impacto,
            'ajustes_aplicados': simulador.ajustes_aplicados
        })

    except Exception as e:
        return jsonify({'success': False, 'erro': str(e)}), 500


@simulador_bp.route('/exportar', methods=['POST'])
def exportar_cenario():
    """
    Exporta cenario simulado para Excel
    """
    import pandas as pd
    from core.scenario_simulator import ScenarioSimulator

    ultima_previsao_data = get_ultima_previsao_data()

    if ultima_previsao_data is None:
        return jsonify({'success': False, 'erro': 'Nenhuma previsao disponivel'}), 404

    try:
        # Receber previsoes simuladas do frontend
        dados_request = request.get_json()
        previsoes_simuladas = dados_request.get('previsoes_simuladas', [])

        # Converter para DataFrame
        df_base = pd.DataFrame(ultima_previsao_data['previsoes_lojas'])
        df_simulado = pd.DataFrame(previsoes_simuladas)

        # Renomear colunas para maiusculas (padrao esperado)
        df_simulado.columns = [col.capitalize() if col.lower() in ['loja', 'sku', 'mes', 'previsao'] else col
                               for col in df_simulado.columns]

        # Criar simulador e substituir dados simulados
        simulador = ScenarioSimulator(df_base)
        simulador.previsoes_simuladas = df_simulado

        # Exportar para Excel em memoria
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"Cenario_Simulado_{timestamp}.xlsx"
        filepath = os.path.join(current_app.config['OUTPUT_FOLDER'], nome_arquivo)

        simulador.exportar_para_excel(filepath)

        # Enviar arquivo para download
        return send_file(
            filepath,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nome_arquivo
        )

    except Exception as e:
        print(f"Erro ao exportar cenario: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500
