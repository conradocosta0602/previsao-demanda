"""
Blueprint: Previsao de Demanda (APIs)
Rotas: /api/gerar_previsao_banco*, /api/exportar_tabela_comparativa
"""

import os
import io
from datetime import datetime
import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from app.utils.previsao_helper import processar_previsao, set_ultima_previsao_data

previsao_bp = Blueprint('previsao', __name__)


@previsao_bp.route('/api/processar', methods=['POST'])
def processar():
    """
    Processa dados e gera previsoes.
    Aceita arquivo Excel via upload.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'erro': 'Nenhum arquivo selecionado'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'erro': 'Arquivo deve ser Excel (.xlsx ou .xls)'}), 400

        # Obter parametros
        meses_previsao = request.form.get('meses_previsao', 6, type=int)
        granularidade = request.form.get('granularidade', 'mensal')

        # Filtros opcionais
        filiais_filtro = request.form.getlist('filiais')
        produtos_filtro = request.form.getlist('produtos')

        # Salvar arquivo temporariamente
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Processar previsao
        resultado = processar_previsao(
            arquivo_excel=filepath,
            meses_previsao=meses_previsao,
            granularidade=granularidade,
            filiais_filtro=filiais_filtro if filiais_filtro else None,
            produtos_filtro=produtos_filtro if produtos_filtro else None,
            output_folder=current_app.config['OUTPUT_FOLDER']
        )

        # Armazenar dados da ultima previsao para o simulador
        if resultado.get('success') and 'grafico_data' in resultado:
            set_ultima_previsao_data(resultado['grafico_data'])

        # Limpar arquivo temporario
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify(resultado)

    except ValueError as e:
        return jsonify({'success': False, 'erro': str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': f'Erro: {str(e)}'}), 500


@previsao_bp.route('/api/gerar_previsao_banco', methods=['POST'])
def api_gerar_previsao_banco():
    """
    Gera previsao de demanda a partir de dados do banco de dados.
    """
    try:
        from core.previsao_v2 import PrevisaoV2Engine

        dados = request.get_json()

        cod_empresa = dados.get('cod_empresa')
        fornecedor = dados.get('fornecedor')
        linha1 = dados.get('linha1')
        linha3 = dados.get('linha3')
        horizonte_dias = dados.get('horizonte_dias', 90)
        metodo = dados.get('metodo', 'auto')

        # Validar parametros minimos
        if not cod_empresa and not fornecedor:
            return jsonify({
                'success': False,
                'erro': 'Informe ao menos cod_empresa ou fornecedor'
            }), 400

        # Criar engine e gerar previsao
        engine = PrevisaoV2Engine()

        resultado = engine.gerar_previsao(
            cod_empresa=cod_empresa,
            fornecedor=fornecedor,
            linha1=linha1,
            linha3=linha3,
            horizonte_dias=horizonte_dias,
            metodo=metodo
        )

        return jsonify({
            'success': True,
            'resultado': resultado
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@previsao_bp.route('/api/gerar_previsao_banco_v2', methods=['POST'])
def api_gerar_previsao_banco_v2():
    """
    Versao 2 da API de previsao: Bottom-Up (Loja -> Produto).
    Gera previsao por loja/produto e agrega para fornecedor.

    Parametros JSON:
        - loja / cod_empresa: Codigo da loja ou 'TODAS'
        - fornecedor: Nome do fornecedor ou 'TODOS'
        - linha / linha1: Categoria (Linha 1)
        - sublinha / linha3: Sublinha (Linha 3)
        - granularidade: 'mensal', 'semanal' ou 'diario'
        - periodos: Numero de periodos de previsao
        - mes_inicio, ano_inicio, mes_fim, ano_fim: Para granularidade mensal
        - semana_inicio, semana_fim, ano_semana_inicio, ano_semana_fim: Para semanal
        - data_inicio, data_fim: Para granularidade diaria
    """
    try:
        from core.previsao_v2 import PrevisaoV2Engine

        dados = request.get_json()

        # Parametros de filtro (aceita ambos os nomes para compatibilidade)
        cod_empresa = dados.get('cod_empresa') or dados.get('loja', 'TODAS')
        fornecedor = dados.get('fornecedor', 'TODOS')
        linha1 = dados.get('linha1') or dados.get('linha', 'TODAS')
        linha3 = dados.get('linha3') or dados.get('sublinha', 'TODAS')

        # Parametros de previsao
        granularidade = dados.get('granularidade', 'mensal')
        periodos = dados.get('periodos', 6)

        # Parametros de periodo - mensal
        mes_inicio = dados.get('mes_inicio')
        ano_inicio = dados.get('ano_inicio')
        mes_fim = dados.get('mes_fim')
        ano_fim = dados.get('ano_fim')

        # Parametros de periodo - semanal
        semana_inicio = dados.get('semana_inicio')
        semana_fim = dados.get('semana_fim')
        ano_semana_inicio = dados.get('ano_semana_inicio')
        ano_semana_fim = dados.get('ano_semana_fim')

        # Parametros de periodo - diario
        data_inicio = dados.get('data_inicio')
        data_fim = dados.get('data_fim')

        # Criar engine e gerar previsao
        engine = PrevisaoV2Engine()

        resultado = engine.gerar_previsao_bottom_up(
            fornecedor=fornecedor,
            cod_empresa=cod_empresa,
            linha1=linha1,
            linha3=linha3,
            granularidade=granularidade,
            periodos=periodos,
            mes_inicio=mes_inicio,
            ano_inicio=ano_inicio,
            mes_fim=mes_fim,
            ano_fim=ano_fim,
            semana_inicio=semana_inicio,
            semana_fim=semana_fim,
            ano_semana_inicio=ano_semana_inicio,
            ano_semana_fim=ano_semana_fim,
            data_inicio=data_inicio,
            data_fim=data_fim
        )

        # Verificar se houve erro
        if 'erro' in resultado:
            return jsonify({
                'success': False,
                'erro': resultado['erro']
            }), 400

        return jsonify(resultado)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@previsao_bp.route('/api/exportar_tabela_comparativa', methods=['POST'])
def api_exportar_tabela_comparativa():
    """Exporta tabela comparativa YoY para Excel."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

        dados = request.get_json()

        if not dados or 'dados' not in dados:
            return jsonify({'success': False, 'erro': 'Dados nao fornecidos'}), 400

        dados_tabela = dados['dados']

        if not dados_tabela:
            return jsonify({'success': False, 'erro': 'Tabela vazia'}), 400

        wb = Workbook()
        ws = wb.active
        ws.title = 'Comparativo YoY'

        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='667EEA', end_color='764BA2', fill_type='solid')
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Cabecalho
        headers = ['Mes', 'Ano Anterior', 'Previsao Atual', 'Variacao (%)']
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center')

        # Dados
        for row_idx, item in enumerate(dados_tabela, start=2):
            ws.cell(row=row_idx, column=1, value=item.get('mes_nome', '')).border = border
            ws.cell(row=row_idx, column=2, value=item.get('demanda_ano_anterior', 0)).border = border
            ws.cell(row=row_idx, column=2).number_format = '#,##0.0'
            ws.cell(row=row_idx, column=3, value=item.get('previsao_atual', 0)).border = border
            ws.cell(row=row_idx, column=3).number_format = '#,##0.0'
            variacao = item.get('variacao_percentual')
            ws.cell(row=row_idx, column=4, value=variacao if variacao is not None else '-').border = border
            if variacao is not None:
                ws.cell(row=row_idx, column=4).number_format = '+0.0%;-0.0%;0%'

        col_widths = [15, 18, 18, 15]
        for i, width in enumerate(col_widths, start=1):
            ws.column_dimensions[chr(64 + i)].width = width

        ws.freeze_panes = 'A2'

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'comparativo_yoy_{timestamp}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500
