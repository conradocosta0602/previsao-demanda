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
    Redireciona para a versao Bottom-Up que retorna WMAPE, BIAS e grafico de linha.
    """
    # Redirecionar para a API V2 interna que tem a estrutura correta
    return _api_gerar_previsao_banco_v2_interno()


def _api_gerar_previsao_banco_v2_interno():
    """
    BOTTOM-UP FORECASTING V2 - Conforme app_original.py

    Usa DemandCalculator.calcular_demanda_diaria_unificada() que implementa
    os 6 metodos estatisticos de forma otimizada para dados diarios:
    - media_simples: Media Movel Simples
    - media_ponderada: Media Movel Ponderada (WMA)
    - media_movel_exp: Suavizacao Exponencial (EMA)
    - tendencia: Regressao com Tendencia
    - sazonal: Decomposicao Sazonal
    - tsb: TSB para demanda intermitente

    Calcula previsao para cada item individualmente, depois agrega para o total.
    Retorna estrutura com WMAPE, BIAS e dados para grafico de linha.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from datetime import datetime as dt, timedelta
    from calendar import monthrange
    from app.utils.db_connection import get_db_connection, DB_CONFIG
    from core.ruptura_sanitizer import RupturaSanitizer
    from core.demand_calculator import DemandCalculator

    try:
        dados = request.get_json()

        # Extrair parametros
        loja = dados.get('loja', 'TODAS')
        categoria = dados.get('categoria', 'TODAS')
        produto = dados.get('produto', 'TODOS')
        granularidade = dados.get('granularidade', 'mensal')

        # Parametros adicionais de filtro
        fornecedor = dados.get('fornecedor', 'TODOS')
        linha = dados.get('linha', 'TODAS')
        sublinha = dados.get('sublinha', 'TODAS')

        # Parametros de periodo
        mes_inicio = dados.get('mes_inicio')
        ano_inicio = dados.get('ano_inicio')
        mes_fim = dados.get('mes_fim')
        ano_fim = dados.get('ano_fim')
        semana_inicio = dados.get('semana_inicio')
        semana_fim = dados.get('semana_fim')
        ano_semana_inicio = dados.get('ano_semana_inicio')
        ano_semana_fim = dados.get('ano_semana_fim')
        data_inicio = dados.get('data_inicio')
        data_fim = dados.get('data_fim')

        # Calcular numero de periodos de previsao
        meses_previsao = 6
        dias_periodo_total = 181

        if granularidade == 'mensal' and mes_inicio and ano_inicio and mes_fim and ano_fim:
            meses_previsao = (int(ano_fim) - int(ano_inicio)) * 12 + (int(mes_fim) - int(mes_inicio)) + 1
            dias_periodo_total = 0
            for i in range(meses_previsao):
                mes_atual = int(mes_inicio) + i
                ano_atual = int(ano_inicio)
                while mes_atual > 12:
                    mes_atual -= 12
                    ano_atual += 1
                dias_periodo_total += monthrange(ano_atual, mes_atual)[1]

        elif granularidade == 'semanal' and semana_inicio and ano_semana_inicio and semana_fim and ano_semana_fim:
            semanas = (int(ano_semana_fim) - int(ano_semana_inicio)) * 52 + (int(semana_fim) - int(semana_inicio)) + 1
            meses_previsao = semanas
            dias_periodo_total = semanas * 7

        elif granularidade == 'diario' and data_inicio and data_fim:
            d1 = dt.strptime(data_inicio, '%Y-%m-%d')
            d2 = dt.strptime(data_fim, '%Y-%m-%d')
            dias = (d2 - d1).days + 1
            meses_previsao = dias
            dias_periodo_total = dias

        periodos_previsao = meses_previsao

        # Conectar ao banco
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construir filtros SQL
        where_conditions = []
        params = []

        def add_filter(field, value, exclude_value, convert_int=False):
            if value and value != exclude_value:
                if isinstance(value, list):
                    if len(value) == 1:
                        where_conditions.append(f"{field} = %s")
                        params.append(int(value[0]) if convert_int else value[0])
                    elif len(value) > 1:
                        placeholders = ', '.join(['%s'] * len(value))
                        where_conditions.append(f"{field} IN ({placeholders})")
                        params.extend([int(v) if convert_int else v for v in value])
                else:
                    where_conditions.append(f"{field} = %s")
                    params.append(int(value) if convert_int else value)

        add_filter("h.cod_empresa", loja, 'TODAS', convert_int=True)
        add_filter("p.nome_fornecedor", fornecedor, 'TODOS')
        add_filter("p.categoria", linha, 'TODAS')
        add_filter("p.codigo_linha", sublinha, 'TODAS')
        add_filter("h.codigo", produto, 'TODOS', convert_int=True)

        where_sql = ""
        if where_conditions:
            where_sql = "AND " + " AND ".join(where_conditions)

        # Buscar lista de itens
        query_itens = f"""
            SELECT DISTINCT
                h.codigo as cod_produto,
                p.descricao,
                p.nome_fornecedor,
                p.cnpj_fornecedor,
                p.categoria,
                p.descricao_linha
            FROM historico_vendas_diario h
            JOIN cadastro_produtos_completo p ON h.codigo::text = p.cod_produto
            WHERE h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
            {where_sql}
            ORDER BY p.nome_fornecedor, p.descricao
        """
        cursor.execute(query_itens, params)
        lista_itens = cursor.fetchall()

        if not lista_itens:
            cursor.close()
            conn.close()
            return jsonify({'erro': 'Nenhum item encontrado com os filtros selecionados'}), 400

        # Buscar vendas historicas
        query_vendas = f"""
            SELECT
                h.codigo as cod_produto,
                h.data as periodo,
                SUM(h.qtd_venda) as qtd_venda
            FROM historico_vendas_diario h
            JOIN cadastro_produtos_completo p ON h.codigo::text = p.cod_produto
            WHERE h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
            {where_sql}
            GROUP BY h.codigo, h.data
            ORDER BY h.codigo, h.data
        """
        cursor.execute(query_vendas, params)
        vendas_por_item_raw = cursor.fetchall()

        # Organizar vendas por item
        vendas_item_dict = {}
        todas_datas = set()
        for venda in vendas_por_item_raw:
            cod = venda['cod_produto']
            if cod not in vendas_item_dict:
                vendas_item_dict[cod] = []
            data_str = venda['periodo'].strftime('%Y-%m-%d')
            todas_datas.add(data_str)
            vendas_item_dict[cod].append({
                'periodo': data_str,
                'qtd_venda': float(venda['qtd_venda'] or 0)
            })

        datas_ordenadas = sorted(list(todas_datas))

        # Agregar vendas para serie historica
        vendas_agregadas = {}
        for cod, vendas in vendas_item_dict.items():
            for v in vendas:
                periodo = v['periodo']
                if periodo not in vendas_agregadas:
                    vendas_agregadas[periodo] = 0
                vendas_agregadas[periodo] += v['qtd_venda']

        # Agregar para granularidade de exibicao
        vendas_agregadas_por_periodo = {}
        for data_str in datas_ordenadas:
            valor = vendas_agregadas.get(data_str, 0)
            try:
                data_obj = dt.strptime(data_str, '%Y-%m-%d')
                if granularidade == 'mensal':
                    chave_periodo = f"{data_obj.year:04d}-{data_obj.month:02d}-01"
                elif granularidade == 'semanal':
                    ano_iso, semana_iso, _ = data_obj.isocalendar()
                    chave_periodo = f"{ano_iso}-S{semana_iso:02d}"
                else:
                    chave_periodo = data_str

                if chave_periodo not in vendas_agregadas_por_periodo:
                    vendas_agregadas_por_periodo[chave_periodo] = 0
                vendas_agregadas_por_periodo[chave_periodo] += valor
            except:
                pass

        datas_historicas = sorted(vendas_agregadas_por_periodo.keys())
        serie_historica_agregada = [vendas_agregadas_por_periodo[d] for d in datas_historicas]

        # Dividir serie em BASE (75%) e TESTE (25%)
        split_index = int(len(datas_historicas) * 0.75)
        datas_base = datas_historicas[:split_index]
        valores_base = serie_historica_agregada[:split_index]
        datas_teste = datas_historicas[split_index:]
        valores_teste = serie_historica_agregada[split_index:]

        # Gerar datas de previsao
        datas_previsao = []
        if granularidade == 'mensal' and mes_inicio and ano_inicio:
            for i in range(periodos_previsao):
                mes_atual = int(mes_inicio) + i
                ano_atual = int(ano_inicio)
                while mes_atual > 12:
                    mes_atual -= 12
                    ano_atual += 1
                datas_previsao.append(f"{ano_atual:04d}-{mes_atual:02d}-01")
        elif granularidade == 'semanal' and semana_inicio and ano_semana_inicio:
            try:
                data_base = dt.strptime(f'{int(ano_semana_inicio)}-W{int(semana_inicio):02d}-1', '%G-W%V-%u')
            except ValueError:
                data_base = dt(int(ano_semana_inicio), 1, 1) + timedelta(weeks=int(semana_inicio) - 1)
            for i in range(periodos_previsao):
                data_prev = data_base + timedelta(weeks=i)
                semana_atual = data_prev.isocalendar()[1]
                ano_atual = data_prev.isocalendar()[0]
                datas_previsao.append(f"{ano_atual}-S{semana_atual:02d}")
        elif granularidade == 'diario' and data_inicio:
            data_base = dt.strptime(data_inicio, '%Y-%m-%d')
            for i in range(periodos_previsao):
                data_prev = data_base + timedelta(days=i)
                datas_previsao.append(data_prev.strftime('%Y-%m-%d'))
        else:
            from dateutil.relativedelta import relativedelta
            ultima_data = dt.strptime(datas_historicas[-1], '%Y-%m-%d') if datas_historicas else dt.now()
            for i in range(periodos_previsao):
                if granularidade == 'mensal':
                    data_prev = ultima_data + relativedelta(months=i+1)
                    datas_previsao.append(data_prev.strftime('%Y-%m-01'))
                else:
                    data_prev = ultima_data + timedelta(days=(i+1)*7)
                    datas_previsao.append(data_prev.strftime('%Y-%m-%d'))

        # =====================================================
        # CALCULAR PREVISAO POR ITEM usando DemandCalculator
        # Conforme app_original.py - usa demanda diaria especifica por periodo
        # =====================================================
        relatorio_itens = []
        previsoes_agregadas_por_periodo = {d: 0 for d in datas_previsao}
        contagem_modelos = {}

        for item in lista_itens:
            cod_produto = item['cod_produto']
            vendas_hist = vendas_item_dict.get(cod_produto, [])
            vendas_hist_sorted = sorted(vendas_hist, key=lambda x: x['periodo'])
            serie_item = [v['qtd_venda'] for v in vendas_hist_sorted]

            if not serie_item:
                continue

            # Usar DemandCalculator para calcular demanda unificada
            demanda_total_unificada, desvio_total, metadata = DemandCalculator.calcular_demanda_diaria_unificada(
                vendas_diarias=serie_item,
                dias_periodo=dias_periodo_total,
                granularidade_exibicao=granularidade
            )

            demanda_diaria_base = metadata.get('demanda_diaria_base', 0)
            metodo_usado = metadata.get('metodo_usado', 'media_simples')

            # =====================================================
            # CALCULAR DEMANDA DIARIA ESPECIFICA POR PERIODO
            # Agrupa historico por mes/semana para calcular media especifica
            # =====================================================
            vendas_por_periodo_hist = {}
            for venda in vendas_hist_sorted:
                data_venda = venda['periodo']
                if not data_venda:
                    continue

                if granularidade == 'mensal':
                    chave = int(data_venda[5:7])  # mes (1-12)
                elif granularidade == 'semanal':
                    try:
                        data_obj = dt.strptime(data_venda, '%Y-%m-%d')
                        chave = data_obj.isocalendar()[1]  # semana ISO
                    except:
                        continue
                else:
                    try:
                        data_obj = dt.strptime(data_venda, '%Y-%m-%d')
                        chave = data_obj.weekday()  # dia da semana
                    except:
                        continue

                if chave not in vendas_por_periodo_hist:
                    vendas_por_periodo_hist[chave] = []
                vendas_por_periodo_hist[chave].append(venda['qtd_venda'])

            # Calcular media diaria por periodo
            media_diaria_por_periodo = {}
            for chave, vendas_lista in vendas_por_periodo_hist.items():
                if len(vendas_lista) > 0:
                    media_diaria_por_periodo[chave] = sum(vendas_lista) / len(vendas_lista)
                else:
                    media_diaria_por_periodo[chave] = 0

            # Fallback: demanda diaria geral
            demanda_diaria_geral = demanda_diaria_base
            if demanda_diaria_geral == 0 and len(serie_item) > 0:
                demanda_diaria_geral = sum(serie_item) / len(serie_item)

            # Calcular previsao de cada periodo usando demanda diaria especifica
            previsao_item_periodos = []
            total_previsao_item = 0

            for i, data_prev in enumerate(datas_previsao):
                if granularidade == 'mensal':
                    ano = int(data_prev[:4])
                    mes = int(data_prev[5:7])
                    dias_periodo = monthrange(ano, mes)[1]
                    chave_periodo = mes
                elif granularidade == 'semanal':
                    dias_periodo = 7
                    if '-S' in data_prev:
                        chave_periodo = int(data_prev.split('-S')[1])
                    else:
                        data_obj = dt.strptime(data_prev, '%Y-%m-%d')
                        chave_periodo = data_obj.isocalendar()[1]
                else:
                    dias_periodo = 1
                    data_obj = dt.strptime(data_prev, '%Y-%m-%d')
                    chave_periodo = data_obj.weekday()

                # Usar demanda diaria ESPECIFICA do periodo (se disponivel)
                demanda_diaria_periodo = media_diaria_por_periodo.get(chave_periodo, demanda_diaria_geral)

                # Previsao do periodo = demanda_diaria_do_periodo x dias
                previsao_periodo = demanda_diaria_periodo * dias_periodo

                previsao_item_periodos.append({
                    'periodo': data_prev,
                    'previsao': round(previsao_periodo, 2)
                })
                previsoes_agregadas_por_periodo[data_prev] += previsao_periodo
                total_previsao_item += previsao_periodo

            # Mapeamento de metodos para nomes simplificados
            mapeamento_metodos = {
                'media_simples': 'SMA',
                'media_ponderada': 'WMA',
                'media_movel_exp': 'EMA',
                'tendencia': 'Regressao com Tendencia',
                'sazonal': 'Decomposicao Sazonal',
                'tsb': 'TSB',
                'tsb_simplificado': 'TSB',
                'wma': 'WMA',
                'ema': 'EMA',
                'wma_adaptativo_estavel': 'WMA',
                'wma_adaptativo_crescente': 'Regressao com Tendencia',
                'wma_adaptativo_decrescente': 'Regressao com Tendencia'
            }
            metodo_exibicao = mapeamento_metodos.get(metodo_usado, metodo_usado)

            relatorio_itens.append({
                'cod_produto': cod_produto,
                'descricao': item['descricao'],
                'nome_fornecedor': item['nome_fornecedor'] or 'SEM FORNECEDOR',
                'categoria': item['categoria'],
                'demanda_prevista_total': round(total_previsao_item, 2),
                'metodo_estatistico': metodo_exibicao,
                'previsao_por_periodo': previsao_item_periodos
            })

            # Contar modelos
            if metodo_exibicao not in contagem_modelos:
                contagem_modelos[metodo_exibicao] = 0
            contagem_modelos[metodo_exibicao] += 1

        # =====================================================
        # CALCULAR BACKTEST - USAR ANO ANTERIOR + TENDENCIA
        # Conforme app_original.py - abordagem mais realista
        # =====================================================
        from dateutil.relativedelta import relativedelta

        # Calcular fatores sazonais para o grafico
        fatores_sazonais = {}
        if len(serie_historica_agregada) >= 12:
            vendas_por_chave_saz = {}
            for i, data_str in enumerate(datas_historicas):
                try:
                    if '-S' in data_str:
                        chave_saz = int(data_str.split('-S')[1])
                    else:
                        data_obj = dt.strptime(data_str, '%Y-%m-%d')
                        if granularidade == 'mensal':
                            chave_saz = data_obj.month
                        else:
                            chave_saz = data_obj.isocalendar()[1]
                    if chave_saz not in vendas_por_chave_saz:
                        vendas_por_chave_saz[chave_saz] = []
                    vendas_por_chave_saz[chave_saz].append(serie_historica_agregada[i])
                except:
                    pass
            media_geral_saz = sum(serie_historica_agregada) / len(serie_historica_agregada) if serie_historica_agregada else 1
            for chave, valores_saz in vendas_por_chave_saz.items():
                media_chave = sum(valores_saz) / len(valores_saz)
                fatores_sazonais[chave] = media_chave / media_geral_saz if media_geral_saz > 0 else 1.0

        # =====================================================
        # BACKTEST - Mesma metodologia do app_original.py
        # Para cada periodo de teste: buscar mesmo periodo do ano anterior
        # e aplicar fator de tendencia observado na base
        # =====================================================
        previsao_teste = []
        wmape_backtest = 0
        bias_backtest = 0

        if len(datas_teste) > 0 and len(valores_base) >= 3:
            # Criar indice de vendas agregadas por periodo para lookup rapido
            vendas_por_data = {d: v for d, v in zip(datas_historicas, serie_historica_agregada)}

            # =====================================================
            # CALCULAR FATOR DE TENDENCIA REAL (ano atual vs ano anterior)
            # Comparar periodos equivalentes dentro da base para detectar
            # crescimento ou queda real entre os anos
            # =====================================================
            soma_valores_ano_recente = 0
            soma_valores_ano_anterior = 0
            pares_encontrados = 0

            for i, data_str in enumerate(datas_base):
                try:
                    if '-S' in data_str:
                        ano_str, sem_str = data_str.split('-S')
                        ano = int(ano_str)
                        chave = int(sem_str)
                        data_aa_str = f"{ano - 1}-S{chave:02d}"
                    else:
                        data_obj = dt.strptime(data_str, '%Y-%m-%d')
                        if granularidade == 'mensal':
                            data_aa_str = f"{data_obj.year - 1:04d}-{data_obj.month:02d}-01"
                        else:
                            data_aa_str = f"{data_obj.year - 1}-{data_obj.month:02d}-{data_obj.day:02d}"

                    # Se encontrar o periodo correspondente do ano anterior na base
                    valor_atual = valores_base[i]
                    valor_aa = vendas_por_data.get(data_aa_str, 0)

                    if valor_aa > 0 and valor_atual > 0:
                        soma_valores_ano_recente += valor_atual
                        soma_valores_ano_anterior += valor_aa
                        pares_encontrados += 1
                except:
                    pass

            # Calcular fator de tendencia baseado em periodos equivalentes
            if pares_encontrados >= 3 and soma_valores_ano_anterior > 0:
                fator_tendencia_geral = soma_valores_ano_recente / soma_valores_ano_anterior
                # Limitar entre 0.6 (-40%) e 1.5 (+50%)
                fator_tendencia_geral = max(0.6, min(1.5, fator_tendencia_geral))
            else:
                # Fallback: comparar metades da base
                meio_base = len(valores_base) // 2
                if meio_base > 0:
                    media_primeira_metade = sum(valores_base[:meio_base]) / meio_base
                    media_segunda_metade = sum(valores_base[meio_base:]) / (len(valores_base) - meio_base)
                    if media_primeira_metade > 0:
                        fator_tendencia_geral = media_segunda_metade / media_primeira_metade
                        fator_tendencia_geral = max(0.6, min(1.5, fator_tendencia_geral))
                    else:
                        fator_tendencia_geral = 1.0
                else:
                    fator_tendencia_geral = 1.0

            for data_teste_str in datas_teste:
                previsao_periodo = 0

                try:
                    # Determinar chave sazonal e buscar periodo correspondente do ano anterior
                    if '-S' in data_teste_str:
                        # Formato semanal: YYYY-SWW
                        ano_str, sem_str = data_teste_str.split('-S')
                        chave_teste = int(sem_str)
                        ano_teste = int(ano_str)
                        # Buscar mesma semana do ano anterior
                        ano_anterior = ano_teste - 1
                        data_aa_str = f"{ano_anterior}-S{chave_teste:02d}"
                    else:
                        data_obj = dt.strptime(data_teste_str, '%Y-%m-%d')
                        if granularidade == 'mensal':
                            chave_teste = data_obj.month
                            # Buscar mesmo mes do ano anterior (formato: YYYY-MM-01)
                            data_aa_str = f"{data_obj.year - 1:04d}-{data_obj.month:02d}-01"
                        elif granularidade == 'semanal':
                            chave_teste = data_obj.isocalendar()[1]
                            # Buscar mesma semana do ano anterior
                            ano_aa = data_obj.year - 1
                            data_aa_str = f"{ano_aa}-S{chave_teste:02d}"
                        else:
                            chave_teste = data_obj.weekday()
                            data_aa_str = f"{data_obj.year - 1}-{data_obj.month:02d}-{data_obj.day:02d}"

                    # Tentar encontrar valor do ano anterior
                    valor_aa = vendas_por_data.get(data_aa_str, 0)

                    if valor_aa > 0:
                        # Usar valor do ano anterior com ajuste de tendencia
                        previsao_periodo = valor_aa * fator_tendencia_geral
                    else:
                        # Fallback: usar fator sazonal agregado
                        media_base = sum(valores_base) / len(valores_base)
                        fator = fatores_sazonais.get(chave_teste, 1.0)
                        previsao_periodo = media_base * fator

                except Exception as e:
                    # Fallback simples
                    media_base = sum(valores_base) / len(valores_base)
                    previsao_periodo = media_base

                previsao_teste.append(round(previsao_periodo, 2))

        # =====================================================
        # CALCULAR WMAPE e BIAS
        # WMAPE (Weighted MAPE) = soma(|erro|) / soma(|real|) * 100
        # BIAS = soma(erro com sinal) / soma(real) * 100
        # =====================================================
        if previsao_teste and valores_teste:
            soma_erros_abs = 0
            soma_erros_signed = 0
            soma_reais = 0

            for i in range(min(len(previsao_teste), len(valores_teste))):
                real = valores_teste[i]
                previsto = previsao_teste[i]
                erro = previsto - real
                if real > 0:
                    soma_erros_abs += abs(erro)
                    soma_erros_signed += erro
                    soma_reais += real

            if soma_reais > 0:
                wmape_backtest = (soma_erros_abs / soma_reais) * 100
                bias_backtest = (soma_erros_signed / soma_reais) * 100

        # Fallback se nao calculou backtest
        if not previsao_teste and len(valores_base) >= 3 and len(datas_teste) > 0:
            media_base_fb = sum(valores_base) / len(valores_base)
            previsao_teste = [round(media_base_fb, 2)] * len(datas_teste)

        # =====================================================
        # PREVISAO FUTURA - SOMA DAS PREVISOES POR ITEM (Bottom-Up)
        # A previsao ja foi calculada por item usando DemandCalculator
        # Aqui apenas agregamos os valores por periodo
        # =====================================================
        previsao_agregada = []

        # A previsao ja foi calculada na secao anterior (por item)
        # Apenas arredondar os valores agregados
        for data_prev in datas_previsao:
            previsao_base = previsoes_agregadas_por_periodo.get(data_prev, 0)
            previsao_agregada.append(round(previsao_base, 2))

        # Buscar ano anterior
        ano_anterior_valores = []
        ano_anterior_datas = []
        ano_anterior_total = 0

        for data_prev in datas_previsao:
            try:
                if '-S' in data_prev:
                    ano_str, sem_str = data_prev.split('-S')
                    ano_anterior_str = f"{int(ano_str)-1}-S{sem_str}"
                else:
                    data_obj = dt.strptime(data_prev, '%Y-%m-%d')
                    data_aa = data_obj.replace(year=data_obj.year - 1)
                    if granularidade == 'mensal':
                        ano_anterior_str = f"{data_aa.year:04d}-{data_aa.month:02d}-01"
                    else:
                        ano_anterior_str = data_aa.strftime('%Y-%m-%d')

                valor_aa = vendas_agregadas_por_periodo.get(ano_anterior_str, 0)
                ano_anterior_valores.append(valor_aa)
                ano_anterior_datas.append(ano_anterior_str)
                ano_anterior_total += valor_aa
            except:
                ano_anterior_valores.append(0)
                ano_anterior_datas.append('')

        # Formatar periodos
        periodos_formatados = []
        for data_str in datas_previsao:
            try:
                if '-S' in data_str:
                    ano_str, sem_str = data_str.split('-S')
                    periodos_formatados.append({'semana': int(sem_str), 'ano': int(ano_str)})
                else:
                    data_obj = dt.strptime(data_str, '%Y-%m-%d')
                    if granularidade == 'mensal':
                        periodos_formatados.append({'mes': data_obj.month, 'ano': data_obj.year})
                    else:
                        periodos_formatados.append(data_str)
            except:
                periodos_formatados.append(data_str)

        # Montar resposta
        resposta = {
            'sucesso': True,
            'versao': 'v2_bottom_up',
            'granularidade': granularidade,
            'filtros': {
                'loja': loja,
                'fornecedor': fornecedor,
                'linha': linha,
                'sublinha': sublinha,
                'produto': produto
            },
            'serie_temporal': {
                'datas': datas_historicas,
                'valores': serie_historica_agregada
            },
            'historico_base': {
                'datas': datas_base,
                'valores': valores_base
            },
            'historico_teste': {
                'datas': datas_teste,
                'valores': valores_teste
            },
            'melhor_modelo': 'Bottom-Up (Individual por Item)',
            'modelos': {
                'Bottom-Up (Individual por Item)': {
                    'metricas': {
                        'wmape': round(wmape_backtest, 2),
                        'bias': round(bias_backtest, 2)
                    },
                    'teste': {
                        'datas': datas_teste,
                        'valores': previsao_teste
                    },
                    'futuro': {
                        'datas': datas_previsao,
                        'valores': [round(v, 2) for v in previsao_agregada]
                    }
                }
            },
            'ano_anterior': {
                'datas': ano_anterior_datas,
                'valores': ano_anterior_valores,
                'total': ano_anterior_total
            },
            'relatorio_detalhado': {
                'itens': relatorio_itens,  # Todos os itens para consistencia com totais
                'periodos_previsao': periodos_formatados,
                'total_itens': len(relatorio_itens),
                'granularidade': granularidade
            },
            'estatisticas_modelos': contagem_modelos,
            'periodos_previsao_formatados': datas_previsao
        }

        cursor.close()
        conn.close()

        return jsonify(resposta)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'erro': str(e)}), 500


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
