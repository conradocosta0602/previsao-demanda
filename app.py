"""
Sistema de Previsão de Demanda - Aplicação Flask
Interface web para upload de dados, processamento e geração de relatórios
"""

import os
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
from datetime import datetime

# Importar módulos do core
from core.data_loader import DataLoader, ajustar_mes_corrente
from core.stockout_handler import processar_stockouts_dataframe, calcular_metricas_stockout
from core.method_selector import MethodSelector
from core.forecasting_models import get_modelo
from core.aggregator import CDAggregator, gerar_previsoes_cd
from core.reporter import ExcelReporter, gerar_nome_arquivo, preparar_resultados

# Configuração do Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo


def processar_previsao(arquivo_excel: str, meses_previsao: int = 6) -> dict:
    """
    Pipeline completo de processamento de previsão

    Args:
        arquivo_excel: Caminho para o arquivo Excel
        meses_previsao: Número de meses para prever

    Returns:
        Dicionário com todos os resultados e arquivo gerado
    """
    alertas = []

    # 1. CARREGAR E VALIDAR DADOS
    print("1. Carregando dados...")
    loader = DataLoader(arquivo_excel)
    df = loader.carregar()

    valido, mensagens = loader.validar()
    if not valido:
        raise ValueError(f"Dados inválidos: {'; '.join(mensagens)}")

    # Adicionar avisos
    for msg in mensagens:
        if 'Aviso' in msg or 'Gap' in msg:
            alertas.append({'tipo': 'warning', 'mensagem': msg})

    df = loader.get_dados_validados()

    # 2. AJUSTAR MÊS CORRENTE
    print("2. Ajustando mês corrente...")
    df = ajustar_mes_corrente(df)

    meses_projetados = df['Mes_Projetado'].sum()
    if meses_projetados > 0:
        alertas.append({
            'tipo': 'info',
            'mensagem': f'{meses_projetados} registros do mês atual foram projetados'
        })

    # 3. TRATAR STOCKOUTS
    print("3. Tratando stockouts...")
    df = processar_stockouts_dataframe(df)
    df_rupturas = calcular_metricas_stockout(df)

    # 4. GERAR PREVISÕES POR LOJA + SKU
    print("4. Gerando previsões por loja...")
    previsoes_lojas = []
    metodos_utilizados = []
    caracteristicas_series = []

    combinacoes = df.groupby(['Loja', 'SKU']).size().reset_index()[['Loja', 'SKU']]

    for _, row in combinacoes.iterrows():
        loja = row['Loja']
        sku = row['SKU']

        # Filtrar dados
        df_filtro = df[(df['Loja'] == loja) & (df['SKU'] == sku)].copy()
        df_filtro = df_filtro.sort_values('Mes')

        if len(df_filtro) < 3:
            alertas.append({
                'tipo': 'warning',
                'mensagem': f'Dados insuficientes para {loja}/{sku}'
            })
            continue

        vendas = df_filtro['Vendas_Corrigidas'].tolist()
        datas = df_filtro['Mes'].tolist()

        # Selecionar método
        selector = MethodSelector(vendas, datas)
        recomendacao = selector.recomendar_metodo()

        # Registrar método
        metodos_utilizados.append({
            'Local': loja,
            'SKU': sku,
            'Metodo': recomendacao['metodo'],
            'Confianca': recomendacao['confianca'],
            'Razao': recomendacao['razao'],
            'Alternativas': ', '.join(recomendacao.get('alternativas', []))
        })

        # Registrar características
        caract = recomendacao['caracteristicas']
        caracteristicas_series.append({
            'Local': loja,
            'SKU': sku,
            'Intermitente': 'Sim' if caract.get('intermitente') else 'Não',
            'Tendencia': caract.get('tipo_tendencia', 'none'),
            'Sazonalidade': 'Sim' if caract.get('tem_sazonalidade') else 'Não',
            'Volatilidade': caract.get('volatilidade', 'N/A'),
            'N_Periodos': caract.get('n_periodos', len(vendas))
        })

        # Gerar previsão
        try:
            modelo = get_modelo(recomendacao['metodo'])
            modelo.fit(vendas)
            previsoes = modelo.predict(meses_previsao)
        except Exception as e:
            # Fallback
            modelo = get_modelo('Média Móvel Simples')
            modelo.fit(vendas)
            previsoes = modelo.predict(meses_previsao)

        # Gerar datas futuras
        ultima_data = datas[-1]
        for h in range(meses_previsao):
            data_previsao = ultima_data + pd.DateOffset(months=h + 1)
            previsoes_lojas.append({
                'Loja': loja,
                'SKU': sku,
                'Mes_Previsao': data_previsao,
                'Previsao': round(previsoes[h], 1),
                'Metodo': recomendacao['metodo'],
                'Confianca': recomendacao['confianca']
            })

    df_previsoes_lojas = pd.DataFrame(previsoes_lojas)
    df_metodos = pd.DataFrame(metodos_utilizados)
    df_caracteristicas = pd.DataFrame(caracteristicas_series)

    # 5. GERAR PREVISÕES DO CD
    print("5. Gerando previsões do CD...")
    skus = df['SKU'].unique().tolist()
    df_previsoes_cd = gerar_previsoes_cd(df, skus, meses_previsao)

    # Adicionar métodos do CD
    for sku in skus:
        aggregator = CDAggregator(df)
        previsao_cd = aggregator.gerar_previsao_cd(sku, meses_previsao)

        if 'erro' not in previsao_cd and previsao_cd['metodo']:
            metodos_utilizados.append({
                'Local': 'CD',
                'SKU': sku,
                'Metodo': previsao_cd['metodo'],
                'Confianca': previsao_cd['confianca'],
                'Razao': previsao_cd.get('razao', ''),
                'Alternativas': ''
            })

            caract = previsao_cd.get('caracteristicas', {})
            caracteristicas_series.append({
                'Local': 'CD',
                'SKU': sku,
                'Intermitente': 'Sim' if caract.get('intermitente') else 'Não',
                'Tendencia': caract.get('tipo_tendencia', 'none'),
                'Sazonalidade': 'Sim' if caract.get('tem_sazonalidade') else 'Não',
                'Volatilidade': caract.get('volatilidade', 'N/A'),
                'N_Periodos': caract.get('n_periodos', 0)
            })

    df_metodos = pd.DataFrame(metodos_utilizados)
    df_caracteristicas = pd.DataFrame(caracteristicas_series)

    # 6. COMPILAR RESUMO
    print("6. Compilando resumo...")

    # Contagem de métodos
    contagem_metodos = df_metodos['Metodo'].value_counts().to_dict()

    # Período histórico
    data_min = df['Mes'].min().strftime('%Y-%m')
    data_max = df['Mes'].max().strftime('%Y-%m')

    resumo = {
        'total_skus': len(skus),
        'total_lojas': len(df['Loja'].unique()),
        'total_combinacoes': len(combinacoes),
        'periodo_historico': f"{data_min} a {data_max}",
        'meses_previsao': meses_previsao,
        'meses_com_ruptura': int(df_rupturas['meses_com_ruptura'].sum()) if 'meses_com_ruptura' in df_rupturas.columns else 0,
        'taxa_ruptura_media': float(df_rupturas['taxa_ruptura'].mean()) if 'taxa_ruptura' in df_rupturas.columns else 0,
        'vendas_perdidas': float(df_rupturas['vendas_perdidas'].sum()) if 'vendas_perdidas' in df_rupturas.columns else 0,
        'contagem_metodos': contagem_metodos
    }

    # 7. GERAR EXCEL
    print("7. Gerando relatório Excel...")

    nome_arquivo = gerar_nome_arquivo()
    caminho_saida = os.path.join(app.config['OUTPUT_FOLDER'], nome_arquivo)

    resultados = preparar_resultados(
        df_previsoes_lojas,
        df_previsoes_cd,
        df_metodos,
        df_rupturas,
        df_caracteristicas,
        resumo,
        alertas
    )

    reporter = ExcelReporter()
    reporter.gerar_relatorio(resultados, caminho_saida)

    print("Processamento concluído!")

    return {
        'success': True,
        'arquivo_saida': nome_arquivo,
        'resumo': resumo,
        'alertas': alertas
    }


@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Recebe arquivo Excel e processa previsão
    """
    try:
        # Verificar arquivo
        if 'file' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'erro': 'Nenhum arquivo selecionado'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'erro': 'Arquivo deve ser Excel (.xlsx ou .xls)'}), 400

        # Parâmetros
        meses_previsao = int(request.form.get('meses_previsao', 6))

        # Salvar arquivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Processar
        resultados = processar_previsao(filepath, meses_previsao)

        # Limpar arquivo de upload
        try:
            os.remove(filepath)
        except:
            pass

        return jsonify(resultados)

    except ValueError as e:
        return jsonify({'success': False, 'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Download do arquivo Excel gerado"""
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    if not os.path.exists(filepath):
        return jsonify({'erro': 'Arquivo não encontrado'}), 404

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


if __name__ == '__main__':
    # Criar pastas necessárias
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('outputs', exist_ok=True)

    print("=" * 50)
    print("  SISTEMA DE PREVISÃO DE DEMANDA")
    print("  Acesse: http://localhost:5001")
    print("=" * 50)

    # Rodar servidor
    app.run(debug=True, host='0.0.0.0', port=5001)
