"""
Blueprint: Pedido Manual
Rotas: /pedido_manual, /pedido_quantidade, /pedido_cobertura, /processar_*, /api/carregar_dados_pedido, /api/buscar_item
"""

import os
from datetime import datetime
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename

pedido_manual_bp = Blueprint('pedido_manual', __name__)


@pedido_manual_bp.route('/pedido_manual')
def pedido_manual():
    """Pagina de pedido manual simplificado"""
    return render_template('pedido_manual.html')


@pedido_manual_bp.route('/pedido_quantidade')
def pedido_quantidade():
    """Pagina de pedido por quantidade"""
    return render_template('pedido_quantidade.html')


@pedido_manual_bp.route('/pedido_cobertura')
def pedido_cobertura():
    """Pagina de pedido por cobertura"""
    return render_template('pedido_cobertura.html')


@pedido_manual_bp.route('/processar_pedido_quantidade', methods=['POST'])
def processar_pedido_quantidade():
    """
    Processa pedido por quantidade informada pelo usuario
    """
    try:
        from core.order_processor import OrderProcessor, gerar_relatorio_pedido

        if 'file' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'erro': 'Nenhum arquivo selecionado'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'erro': 'Arquivo deve ser Excel'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        df_entrada = pd.read_excel(filepath)

        df_resultado = OrderProcessor.processar_pedido_por_quantidade(
            df_entrada,
            validar_embalagem=True
        )

        resumo = gerar_relatorio_pedido(df_resultado, 'quantidade')

        nome_arquivo_saida = f"pedido_quantidade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        caminho_saida = os.path.join(current_app.config['OUTPUT_FOLDER'], nome_arquivo_saida)

        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            df_resultado.to_excel(writer, sheet_name='Pedido', index=False)

            itens_ajustados = df_resultado[df_resultado['Foi_Ajustado'] == True]
            if len(itens_ajustados) > 0:
                itens_ajustados.to_excel(writer, sheet_name='Itens_Ajustados', index=False)

        try:
            os.remove(filepath)
        except:
            pass

        return jsonify({
            'success': True,
            'arquivo_saida': nome_arquivo_saida,
            'resumo': resumo,
            'dados_tabela': df_resultado.to_dict('records')
        })

    except ValueError as e:
        return jsonify({'success': False, 'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'erro': f'Erro: {str(e)}'}), 500


@pedido_manual_bp.route('/processar_pedido_cobertura', methods=['POST'])
def processar_pedido_cobertura():
    """
    Processa pedido por cobertura desejada informada pelo usuario
    """
    try:
        from core.order_processor import OrderProcessor, gerar_relatorio_pedido

        if 'file' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'erro': 'Nenhum arquivo selecionado'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'erro': 'Arquivo deve ser Excel'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        df_entrada = pd.read_excel(filepath)

        df_resultado = OrderProcessor.processar_pedido_por_cobertura(df_entrada)

        resumo = gerar_relatorio_pedido(df_resultado, 'cobertura')

        nome_arquivo_saida = f"pedido_cobertura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        caminho_saida = os.path.join(current_app.config['OUTPUT_FOLDER'], nome_arquivo_saida)

        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            df_resultado.to_excel(writer, sheet_name='Pedido', index=False)

            itens_sem_necessidade = df_resultado[df_resultado['Quantidade_Pedido'] == 0]
            if len(itens_sem_necessidade) > 0:
                itens_sem_necessidade.to_excel(writer, sheet_name='Sem_Necessidade', index=False)

            itens_ajustados = df_resultado[df_resultado['Foi_Ajustado'] == True]
            if len(itens_ajustados) > 0:
                itens_ajustados.to_excel(writer, sheet_name='Itens_Ajustados', index=False)

        try:
            os.remove(filepath)
        except:
            pass

        return jsonify({
            'success': True,
            'arquivo_saida': nome_arquivo_saida,
            'resumo': resumo,
            'dados_tabela': df_resultado.to_dict('records')
        })

    except ValueError as e:
        return jsonify({'success': False, 'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'erro': f'Erro: {str(e)}'}), 500


@pedido_manual_bp.route('/api/carregar_dados_pedido', methods=['POST'])
def carregar_dados_pedido():
    """
    Carrega dados de reabastecimento para uso no simulador
    """
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'erro': 'Nenhum arquivo selecionado'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'erro': 'Arquivo deve ser Excel'}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], f"temp_{filename}")
        file.save(filepath)

        df = pd.read_excel(filepath)

        colunas_necessarias = [
            'Loja', 'SKU', 'Demanda_Media_Mensal', 'Lead_Time_Dias',
            'Estoque_Disponivel', 'Ponto_Pedido'
        ]

        colunas_faltantes = [col for col in colunas_necessarias if col not in df.columns]

        if colunas_faltantes:
            os.remove(filepath)
            return jsonify({
                'success': False,
                'erro': f'Colunas faltando: {", ".join(colunas_faltantes)}'
            }), 400

        if 'Demanda_Diaria' not in df.columns:
            df['Demanda_Diaria'] = df['Demanda_Media_Mensal'] / 30

        if 'Quantidade_Pedido' not in df.columns:
            df['Quantidade_Pedido'] = 0

        if 'Lote_Minimo' not in df.columns:
            df['Lote_Minimo'] = 1

        colunas_retornar = [
            'Loja', 'SKU', 'Demanda_Diaria', 'Lead_Time_Dias',
            'Estoque_Disponivel', 'Ponto_Pedido', 'Quantidade_Pedido',
            'Lote_Minimo'
        ]

        for col in ['Estoque_Transito', 'Pedidos_Abertos', 'Estoque_Seguranca']:
            if col in df.columns:
                colunas_retornar.append(col)

        df_resultado = df[colunas_retornar].copy()

        try:
            os.remove(filepath)
        except:
            pass

        return jsonify({
            'success': True,
            'dados': df_resultado.to_dict('records'),
            'total_itens': len(df_resultado)
        })

    except Exception as e:
        return jsonify({'success': False, 'erro': f'Erro ao carregar: {str(e)}'}), 500


@pedido_manual_bp.route('/api/buscar_item', methods=['POST'])
def buscar_item():
    """
    Busca item especifico no ultimo resultado processado (placeholder)
    """
    try:
        data = request.get_json()
        loja = data.get('loja')
        sku = data.get('sku')

        if not loja or not sku:
            return jsonify({'success': False, 'erro': 'Loja e SKU sao obrigatorios'}), 400

        return jsonify({
            'success': False,
            'erro': 'Carregue um arquivo Excel primeiro para buscar itens'
        }), 404

    except Exception as e:
        return jsonify({'success': False, 'erro': str(e)}), 500
