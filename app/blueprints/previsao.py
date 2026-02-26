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
    from core.demand_calculator import DemandCalculator, calcular_fator_tendencia_yoy

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
                    # Filtrar valores de exclusao da lista
                    filtered = [v for v in value if v != exclude_value]
                    if not filtered:
                        return  # Todos os valores eram de exclusao
                    if len(filtered) == 1:
                        where_conditions.append(f"{field} = %s")
                        params.append(int(filtered[0]) if convert_int else filtered[0])
                    elif len(filtered) > 1:
                        placeholders = ', '.join(['%s'] * len(filtered))
                        where_conditions.append(f"{field} IN ({placeholders})")
                        params.extend([int(v) if convert_int else v for v in filtered])
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

        # =====================================================
        # CORTE DE DATA: Exclui dados do periodo de previsao
        # Se usuario quer prever Jan/2026, dados de Jan/2026
        # NAO devem ser usados no calculo do historico
        # =====================================================
        corte_sql = ""
        params_com_corte = list(params)

        if granularidade == 'mensal' and mes_inicio and ano_inicio:
            data_corte = f"{int(ano_inicio):04d}-{int(mes_inicio):02d}-01"
            corte_sql = "AND h.data < %s"
            params_com_corte.append(data_corte)
        elif granularidade == 'semanal' and semana_inicio and ano_semana_inicio:
            try:
                from datetime import datetime as dt_calc
                data_base = dt_calc.strptime(f'{int(ano_semana_inicio)}-W{int(semana_inicio):02d}-1', '%G-W%V-%u')
                corte_sql = "AND h.data < %s"
                params_com_corte.append(data_base.strftime('%Y-%m-%d'))
            except:
                pass
        elif granularidade == 'diario' and data_inicio:
            corte_sql = "AND h.data < %s"
            params_com_corte.append(data_inicio)

        # Buscar lista de itens (incluindo situacao de compra para filtro EN/FL v6.2)
        # A situacao e agregada por item - se tiver EN ou FL em alguma loja, mostra
        query_itens = f"""
            SELECT DISTINCT
                h.codigo as cod_produto,
                p.descricao,
                p.nome_fornecedor,
                p.cnpj_fornecedor,
                p.categoria,
                p.descricao_linha,
                COALESCE(
                    (SELECT string_agg(DISTINCT s.sit_compra, ',')
                     FROM situacao_compra_itens s
                     WHERE s.codigo = h.codigo
                       AND s.sit_compra IN ('EN', 'FL')),
                    'ATIVO'
                ) as situacao_compra
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

        # Buscar vendas historicas (COM corte de data para excluir periodo de previsao)
        query_vendas = f"""
            SELECT
                h.codigo as cod_produto,
                h.data as periodo,
                SUM(h.qtd_venda) as qtd_venda
            FROM historico_vendas_diario h
            JOIN cadastro_produtos_completo p ON h.codigo::text = p.cod_produto
            WHERE h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
            {where_sql}
            {corte_sql}
            GROUP BY h.codigo, h.data
            ORDER BY h.codigo, h.data
        """
        cursor.execute(query_vendas, params_com_corte)
        vendas_por_item_raw = cursor.fetchall()

        # =====================================================
        # BUSCAR DADOS DE ESTOQUE PARA CALCULAR COBERTURA
        # Usado para decidir entre saneamento de rupturas vs normalização
        # =====================================================
        # Ajustar filtros para usar alias 'e' em vez de 'h'
        where_sql_estoque = where_sql.replace("h.cod_empresa", "e.cod_empresa").replace("h.codigo", "e.codigo")
        corte_sql_estoque = corte_sql.replace("h.data", "e.data")

        query_estoque = f"""
            SELECT
                e.codigo as cod_produto,
                e.data as periodo,
                e.estoque_diario
            FROM historico_estoque_diario e
            JOIN cadastro_produtos_completo p ON e.codigo::text = p.cod_produto
            WHERE e.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
            {where_sql_estoque}
            {corte_sql_estoque}
            ORDER BY e.codigo, e.data
        """
        cursor.execute(query_estoque, params_com_corte)
        estoque_por_item_raw = cursor.fetchall()

        # =====================================================
        # BUSCAR CUE (Custo Unitario de Estoque) POR ITEM
        # Media ponderada pelo estoque de cada loja
        # =====================================================
        query_cue = """
            SELECT codigo as cod_produto,
                   CASE WHEN SUM(estoque) > 0
                        THEN SUM(cue * estoque) / SUM(estoque)
                        ELSE MAX(cue)
                   END as cue_medio
            FROM estoque_posicao_atual
            WHERE cue > 0
            GROUP BY codigo
        """
        cursor.execute(query_cue)
        cue_rows = cursor.fetchall()
        cue_por_item = {}
        for row in cue_rows:
            cue_por_item[row['cod_produto']] = float(row['cue_medio'] or 0)

        # Organizar estoque por item
        estoque_item_dict = {}
        for est in estoque_por_item_raw:
            cod = est['cod_produto']
            if cod not in estoque_item_dict:
                estoque_item_dict[cod] = {}
            data_str = est['periodo'].strftime('%Y-%m-%d')
            estoque_item_dict[cod][data_str] = float(est['estoque_diario'] or 0)

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

        # =====================================================
        # CARREGAR AJUSTES MANUAIS DO BANCO DE DADOS
        # Se existir ajuste para item/periodo, usar valor_ajustado
        # =====================================================
        ajustes_por_item_periodo = {}
        try:
            cursor.execute("""
                SELECT cod_produto, periodo, valor_ajustado
                FROM ajuste_previsao
                WHERE ativo = TRUE
                  AND granularidade = %s
            """, (granularidade,))
            ajustes_rows = cursor.fetchall()
            for ajuste in ajustes_rows:
                chave = (str(ajuste['cod_produto']), ajuste['periodo'])
                ajustes_por_item_periodo[chave] = float(ajuste['valor_ajustado'])
            print(f"[Ajustes] Carregados {len(ajustes_por_item_periodo)} ajustes manuais do banco")
        except Exception as e:
            print(f"[Ajustes] Erro ao carregar ajustes: {e}")

        # Calcular total de dias no periodo historico (para detectar intermitencia real)
        dias_historico_total = len(datas_ordenadas) if datas_ordenadas else 1

        for item in lista_itens:
            cod_produto = item['cod_produto']
            situacao_compra = item.get('situacao_compra', 'ATIVO')

            # =====================================================
            # FILTRO EN/FL v6.2: Itens com situacao EN ou FL
            # Nao calcular demanda, mas incluir na tabela com demanda zerada
            # =====================================================
            if situacao_compra and situacao_compra != 'ATIVO' and ('EN' in situacao_compra or 'FL' in situacao_compra):
                # Item bloqueado - incluir na tabela com demanda zerada
                # previsao_por_periodo deve ser um array para o frontend processar
                # Determinar a situacao principal (EN ou FL)
                sit_principal = 'FL' if 'FL' in situacao_compra else 'EN'
                sit_descricao = 'Fora de Linha' if sit_principal == 'FL' else 'Em Negociacao'

                relatorio_itens.append({
                    'cod_produto': cod_produto,
                    'descricao': item['descricao'],
                    'nome_fornecedor': item['nome_fornecedor'] or 'SEM FORNECEDOR',
                    'categoria': item['categoria'],
                    'situacao_compra': situacao_compra,
                    'sit_compra': sit_principal,  # Campo esperado pelo frontend
                    'sit_compra_descricao': sit_descricao,  # Campo esperado pelo frontend
                    'demanda_prevista_total': 0,
                    'demanda_ano_anterior': 0,
                    'variacao_percentual': 0,
                    'sinal_emoji': '⚫',  # Preto para bloqueado
                    'metodo_estatistico': 'BLOQUEADO',
                    'fator_tendencia_yoy': 0,
                    'classificacao_tendencia': 'bloqueado',
                    'previsao_por_periodo': [],  # Array vazio para compatibilidade com frontend
                    'cue': round(cue_por_item.get(cod_produto, 0), 4)
                })
                continue

            vendas_hist = vendas_item_dict.get(cod_produto, [])
            vendas_hist_sorted = sorted(vendas_hist, key=lambda x: x['periodo'])

            if not vendas_hist_sorted:
                continue

            # =====================================================
            # LOGICA DE COBERTURA DE ESTOQUE (LIMIAR 50%)
            # - >= 50%: Sanear rupturas (excluir rupturas)
            # - < 50%: Normalizar pelo total de dias do periodo
            # =====================================================
            estoque_item = estoque_item_dict.get(cod_produto, {})
            dias_com_registro_estoque = len(estoque_item)
            cobertura_estoque = dias_com_registro_estoque / dias_historico_total if dias_historico_total > 0 else 0

            # Calcular total vendido para normalizacao
            total_vendido_item = sum(v['qtd_venda'] for v in vendas_hist_sorted)
            dias_com_venda = len(vendas_hist_sorted)

            if cobertura_estoque >= 0.50:
                # =====================================================
                # COBERTURA >= 50%: Sanear rupturas
                # Exclui dias com estoque=0 E venda=0 (ruptura)
                # Inclui dias com estoque>0 E venda=0 (demanda zero real)
                # =====================================================
                serie_saneada = []
                dias_validos = 0

                # Para cada data no periodo historico
                for data_str in datas_ordenadas:
                    # Buscar venda e estoque nessa data
                    venda_dia = 0
                    for v in vendas_hist_sorted:
                        if v['periodo'] == data_str:
                            venda_dia = v['qtd_venda']
                            break

                    estoque_dia = estoque_item.get(data_str, None)

                    # Logica de saneamento:
                    # - estoque > 0 ou sem registro de estoque: incluir a venda (real ou zero)
                    # - estoque = 0 E venda = 0: ruptura, EXCLUIR
                    if estoque_dia is not None and estoque_dia == 0 and venda_dia == 0:
                        # Ruptura detectada - nao incluir no calculo
                        continue
                    else:
                        # Incluir: ou tinha estoque, ou vendeu, ou sem info de estoque
                        serie_saneada.append(venda_dia)
                        dias_validos += 1

                serie_item = serie_saneada if serie_saneada else [0]
                metodo_usado = 'ruptura_saneada'

                # Taxa de presenca baseada em dias validos
                taxa_presenca = dias_com_venda / dias_validos if dias_validos > 0 else 0

            else:
                # =====================================================
                # COBERTURA < 50%: Normalizar pelo total de dias
                # Nao temos dados suficientes de estoque para identificar rupturas
                # Entao dividimos total vendido pelo total de dias do periodo
                # =====================================================
                # Calcular demanda diaria normalizada
                demanda_diaria_normalizada = total_vendido_item / dias_historico_total if dias_historico_total > 0 else 0

                # Criar serie artificial para o DemandCalculator
                # com a demanda diaria normalizada
                serie_item = [demanda_diaria_normalizada] * dias_historico_total
                metodo_usado = 'normalizado_sem_estoque'

                # Taxa de presenca baseada no total de dias
                taxa_presenca = dias_com_venda / dias_historico_total if dias_historico_total > 0 else 0

            # Usar DemandCalculator para calcular demanda unificada
            demanda_total_unificada, desvio_total, metadata = DemandCalculator.calcular_demanda_diaria_unificada(
                vendas_diarias=serie_item,
                dias_periodo=dias_periodo_total,
                granularidade_exibicao=granularidade
            )

            demanda_diaria_base = metadata.get('demanda_diaria_base', 0)
            metodo_calc = metadata.get('metodo_usado', 'media_simples')

            # Preservar metodo de saneamento/normalizacao se foi aplicado
            if metodo_usado in ['ruptura_saneada', 'normalizado_sem_estoque']:
                metodo_usado = f"{metodo_usado}+{metodo_calc}"
            else:
                metodo_usado = metodo_calc

            # AJUSTE PARA DEMANDA EXTREMAMENTE INTERMITENTE
            # Se vendeu em menos de 5% dos dias, aplicar fator de correcao
            if taxa_presenca < 0.05 and dias_com_venda > 0:
                # Calculo TSB: probabilidade de demanda x media quando ha demanda
                media_quando_vende = total_vendido_item / dias_com_venda
                # Demanda esperada = prob_venda * media_venda
                demanda_diaria_base = taxa_presenca * media_quando_vende
                metodo_usado = 'tsb_intermitente_extremo'

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

            # =====================================================
            # CALCULO DE FATORES SAZONAIS (como multiplicadores)
            # O fator sazonal indica se um periodo eh acima/abaixo da media
            # Ex: fator=1.2 significa 20% acima da media geral
            # =====================================================
            media_por_periodo = {}
            for chave, vendas_lista in vendas_por_periodo_hist.items():
                if len(vendas_lista) > 0:
                    media_por_periodo[chave] = sum(vendas_lista) / len(vendas_lista)
                else:
                    media_por_periodo[chave] = 0

            # Calcular media geral de TODOS os periodos historicos
            todas_medias = [m for m in media_por_periodo.values() if m > 0]
            media_geral_hist = sum(todas_medias) / len(todas_medias) if todas_medias else 0

            # Calcular fator sazonal para cada periodo
            # fator = media_do_periodo / media_geral
            fatores_sazonais = {}
            for chave, media_periodo in media_por_periodo.items():
                if media_geral_hist > 0 and media_periodo > 0:
                    fator = media_periodo / media_geral_hist
                    # Limitar fator entre 0.5 e 2.0 para evitar distorcoes extremas
                    fatores_sazonais[chave] = max(0.5, min(2.0, fator))
                else:
                    fatores_sazonais[chave] = 1.0

            # Usar demanda_diaria_base dos 6 metodos estatisticos
            demanda_diaria_inteligente = demanda_diaria_base
            if demanda_diaria_inteligente == 0 and len(serie_item) > 0:
                # Fallback apenas se DemandCalculator retornou 0
                demanda_diaria_inteligente = sum(serie_item) / len(serie_item)

            # =====================================================
            # FATOR DE TENDENCIA YoY (V5.7)
            # Corrige subestimacao em itens com crescimento historico
            # Ex: Item com +29% de crescimento real nao deve prever queda
            # =====================================================
            vendas_por_mes_yoy = {}
            for venda in vendas_hist_sorted:
                data_venda = venda['periodo']
                try:
                    ano_v = int(data_venda[:4])
                    mes_v = int(data_venda[5:7])
                    chave_yoy = (ano_v, mes_v)
                    if chave_yoy not in vendas_por_mes_yoy:
                        vendas_por_mes_yoy[chave_yoy] = 0
                    vendas_por_mes_yoy[chave_yoy] += venda['qtd_venda']
                except:
                    continue

            fator_tendencia_yoy = 1.0
            classificacao_tendencia = 'nao_calculado'
            if vendas_por_mes_yoy:
                fator_tendencia_yoy, classificacao_tendencia, _ = calcular_fator_tendencia_yoy(
                    vendas_por_mes=vendas_por_mes_yoy,
                    min_anos=2,
                    fator_amortecimento=0.7
                )

            # Calcular previsao de cada periodo usando demanda diaria especifica
            previsao_item_periodos = []
            total_previsao_item = 0
            total_ano_anterior_item = 0

            # Criar dicionario de vendas por data para lookup rapido (para ano anterior)
            vendas_item_por_data = {}
            for venda in vendas_hist_sorted:
                data_venda = venda['periodo']
                if granularidade == 'mensal':
                    # Agregar por mes: YYYY-MM-01
                    chave_data = data_venda[:7] + '-01'
                elif granularidade == 'semanal':
                    try:
                        data_obj = dt.strptime(data_venda, '%Y-%m-%d')
                        ano_iso, semana_iso, _ = data_obj.isocalendar()
                        chave_data = f"{ano_iso}-S{semana_iso:02d}"
                    except:
                        continue
                else:
                    chave_data = data_venda

                if chave_data not in vendas_item_por_data:
                    vendas_item_por_data[chave_data] = 0
                vendas_item_por_data[chave_data] += venda['qtd_venda']

            for i, data_prev in enumerate(datas_previsao):
                if granularidade == 'mensal':
                    ano = int(data_prev[:4])
                    mes = int(data_prev[5:7])
                    dias_periodo = monthrange(ano, mes)[1]
                    chave_periodo = mes
                    # Chave do ano anterior para este periodo
                    chave_ano_anterior = f"{ano - 1:04d}-{mes:02d}-01"
                elif granularidade == 'semanal':
                    dias_periodo = 7
                    if '-S' in data_prev:
                        ano_str, sem_str = data_prev.split('-S')
                        chave_periodo = int(sem_str)
                        chave_ano_anterior = f"{int(ano_str) - 1}-S{sem_str}"
                    else:
                        data_obj = dt.strptime(data_prev, '%Y-%m-%d')
                        chave_periodo = data_obj.isocalendar()[1]
                        chave_ano_anterior = f"{data_obj.year - 1}-S{chave_periodo:02d}"
                else:
                    dias_periodo = 1
                    data_obj = dt.strptime(data_prev, '%Y-%m-%d')
                    chave_periodo = data_obj.weekday()
                    chave_ano_anterior = f"{data_obj.year - 1}-{data_obj.month:02d}-{data_obj.day:02d}"

                # =====================================================
                # FORMULA CORRETA V5.7: demanda * fator_sazonal * fator_tendencia_yoy * dias
                # - demanda_inteligente: vem dos 6 metodos (SMA, WMA, EMA, Tendencia, Sazonal, TSB)
                # - fator_sazonal: multiplicador baseado na sazonalidade historica
                # - fator_tendencia_yoy: ajuste para crescimento/queda historica YoY
                # - dias: quantidade de dias no periodo
                # =====================================================
                fator_sazonal = fatores_sazonais.get(chave_periodo, 1.0)
                previsao_periodo = demanda_diaria_inteligente * fator_sazonal * fator_tendencia_yoy * dias_periodo

                # Buscar valor do ano anterior para este item neste periodo
                valor_aa_periodo = vendas_item_por_data.get(chave_ano_anterior, 0)
                total_ano_anterior_item += valor_aa_periodo

                # =====================================================
                # LIMITADOR DE VARIACAO vs ANO ANTERIOR (V11) - Atualizado v5.7
                # Evita previsoes extremas limitando variacao entre -40% e +50%
                # do valor do ano anterior.
                #
                # NOVO v5.7: Para itens com tendencia de crescimento, se a previsao
                # estiver abaixo do ano anterior, ajusta para pelo menos igualar o AA
                # (respeitando o fator de tendencia detectado).
                # =====================================================
                previsao_periodo_limitada = previsao_periodo
                variacao_limitada = False

                if valor_aa_periodo > 0:
                    variacao_vs_aa = previsao_periodo / valor_aa_periodo

                    # NOVO v5.7: Ajuste para itens em crescimento
                    # Se item tem tendencia de crescimento mas previsao < AA, corrigir
                    if fator_tendencia_yoy > 1.05 and variacao_vs_aa < 1.0:
                        # Usar o fator de tendencia para projetar sobre o AA
                        # Limitado a +40% para evitar exageros
                        previsao_periodo_limitada = valor_aa_periodo * min(fator_tendencia_yoy, 1.4)
                        variacao_limitada = True
                    # Limitar variacao maxima para cima (+50%)
                    elif variacao_vs_aa > 1.5:
                        previsao_periodo_limitada = valor_aa_periodo * 1.5
                        variacao_limitada = True
                    # Limitar variacao maxima para baixo (-40%)
                    elif variacao_vs_aa < 0.6:
                        previsao_periodo_limitada = valor_aa_periodo * 0.6
                        variacao_limitada = True

                # Usar valor limitado se aplicavel
                previsao_periodo = previsao_periodo_limitada

                # Arredondar previsao do periodo para inteiro (como exibido no frontend)
                previsao_periodo_int = round(previsao_periodo)

                # =====================================================
                # VERIFICAR SE EXISTE AJUSTE MANUAL PARA ESTE ITEM/PERIODO
                # Se existir, usar o valor ajustado em vez do calculado
                # =====================================================
                chave_ajuste = (str(cod_produto), data_prev)
                tem_ajuste = chave_ajuste in ajustes_por_item_periodo
                if tem_ajuste:
                    previsao_periodo_int = int(ajustes_por_item_periodo[chave_ajuste])

                previsao_item_periodos.append({
                    'periodo': data_prev,
                    'previsao': previsao_periodo_int,
                    'ano_anterior': round(valor_aa_periodo),
                    'ajuste_manual': tem_ajuste  # Flag para indicar que foi ajustado
                })
                previsoes_agregadas_por_periodo[data_prev] += previsao_periodo_int
                total_previsao_item += previsao_periodo_int

            # =====================================================
            # APLICAR EVENTOS (promocoes, sazonais, etc.)
            # Ajusta a previsao de cada periodo pelo fator do evento
            # =====================================================
            try:
                from core.event_manager_v2 import EventManagerV2
                _evt_mgr = EventManagerV2()
                cnpj_forn = item.get('cnpj_fornecedor')
                cat_item = item.get('categoria')
                linha3_item = item.get('descricao_linha')

                total_previsao_item = 0  # Recalcular com eventos
                for pp in previsao_item_periodos:
                    try:
                        data_prev_str = pp['periodo']
                        if granularidade == 'mensal':
                            data_inicio_evt = dt.strptime(data_prev_str, '%Y-%m-%d').date()
                            dias_mes = monthrange(data_inicio_evt.year, data_inicio_evt.month)[1]
                            data_fim_evt = data_inicio_evt.replace(day=dias_mes)
                        else:
                            data_inicio_evt = dt.strptime(data_prev_str[:10], '%Y-%m-%d').date()
                            data_fim_evt = data_inicio_evt + timedelta(days=6)

                        resultado_evt = _evt_mgr.calcular_fator_eventos(
                            codigo=int(cod_produto),
                            cod_empresa=0,
                            cod_fornecedor=cnpj_forn,
                            linha1=cat_item,
                            linha3=linha3_item,
                            data_inicio=data_inicio_evt,
                            data_fim=data_fim_evt
                        )
                        fator_evt = resultado_evt.get('fator_total', 1.0)
                        if fator_evt != 1.0:
                            pp['previsao_original'] = pp['previsao']
                            pp['previsao'] = round(pp['previsao'] * fator_evt)
                            pp['evento_fator'] = fator_evt
                            pp['evento_nomes'] = ', '.join(
                                e.get('nome', '') for e in resultado_evt.get('eventos_aplicados', [])
                            )
                    except Exception:
                        pass
                    total_previsao_item += pp['previsao']

                # Atualizar agregado por periodo
                for pp in previsao_item_periodos:
                    if pp.get('evento_fator') and pp.get('previsao_original') is not None:
                        diff = pp['previsao'] - pp['previsao_original']
                        previsoes_agregadas_por_periodo[pp['periodo']] += diff
            except Exception as e_evt:
                print(f"[EVENTOS] Erro ao aplicar eventos para item {cod_produto}: {e_evt}")

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

            # Calcular variacao percentual
            variacao_pct = 0
            if total_ano_anterior_item > 0:
                variacao_pct = ((total_previsao_item - total_ano_anterior_item) / total_ano_anterior_item) * 100

            # Determinar sinal de alerta baseado na variacao
            # 🔴 Critico: variacao > 50% ou < -50%
            # 🟡 Alerta: variacao > 30% ou < -30%
            # 🔵 Atencao: variacao > 20% ou < -20%
            # 🟢 Normal: variacao entre -20% e +20%
            # ⚪ Sem dados: sem ano anterior para comparar
            if total_ano_anterior_item == 0:
                sinal_emoji = '⚪'
            elif abs(variacao_pct) > 50:
                sinal_emoji = '🔴'
            elif abs(variacao_pct) > 30:
                sinal_emoji = '🟡'
            elif abs(variacao_pct) > 20:
                sinal_emoji = '🔵'
            else:
                sinal_emoji = '🟢'

            relatorio_itens.append({
                'cod_produto': cod_produto,
                'descricao': item['descricao'],
                'nome_fornecedor': item['nome_fornecedor'] or 'SEM FORNECEDOR',
                'categoria': item['categoria'],
                'situacao_compra': item.get('situacao_compra', 'ATIVO'),
                'demanda_prevista_total': total_previsao_item,
                'demanda_ano_anterior': round(total_ano_anterior_item, 2),
                'variacao_percentual': round(variacao_pct, 1),
                'sinal_emoji': sinal_emoji,
                'metodo_estatistico': metodo_exibicao,
                'fator_tendencia_yoy': round(fator_tendencia_yoy, 4),
                'classificacao_tendencia': classificacao_tendencia,
                'previsao_por_periodo': previsao_item_periodos,
                'cue': round(cue_por_item.get(cod_produto, 0), 4)
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

        # =====================================================
        # AGREGAR POR FORNECEDOR - Comparacao YoY por Fornecedor
        # =====================================================
        # Funcao auxiliar para formatar periodo igual ao frontend
        meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        def formatar_periodo_display(periodo_str, gran):
            """Formata periodo para exibicao (igual ao frontend)"""
            try:
                if gran == 'semanal':
                    if '-S' in periodo_str:
                        ano, sem = periodo_str.split('-S')
                        return f"S{int(sem)}/{ano}"
                    else:
                        data_obj = dt.strptime(periodo_str, '%Y-%m-%d')
                        semana = data_obj.isocalendar()[1]
                        return f"S{semana}/{data_obj.year}"
                elif gran == 'diario' or gran == 'diaria':
                    data_obj = dt.strptime(periodo_str, '%Y-%m-%d')
                    return f"{data_obj.day:02d}/{data_obj.month:02d}/{data_obj.year}"
                else:  # mensal
                    data_obj = dt.strptime(periodo_str, '%Y-%m-%d')
                    return f"{meses_nomes[data_obj.month - 1]}/{data_obj.year}"
            except:
                return periodo_str

        comparacao_por_fornecedor = {}
        for item in relatorio_itens:
            nome_forn = item.get('nome_fornecedor') or 'SEM FORNECEDOR'

            if nome_forn not in comparacao_por_fornecedor:
                comparacao_por_fornecedor[nome_forn] = {
                    'nome_fornecedor': nome_forn,
                    'previsao_total': 0,
                    'ano_anterior_total': 0,
                    'previsao_por_periodo': {},
                    'ano_anterior_por_periodo': {}
                }

            comparacao_por_fornecedor[nome_forn]['previsao_total'] += item.get('demanda_prevista_total', 0)
            comparacao_por_fornecedor[nome_forn]['ano_anterior_total'] += item.get('demanda_ano_anterior', 0)

            # Agregar por periodo (usando formato de exibicao para matching com frontend)
            if item.get('previsao_por_periodo'):
                for p in item['previsao_por_periodo']:
                    periodo_raw = p.get('periodo')
                    if periodo_raw:
                        # Formatar periodo igual ao frontend para matching correto
                        periodo = formatar_periodo_display(periodo_raw, granularidade)
                        if periodo not in comparacao_por_fornecedor[nome_forn]['previsao_por_periodo']:
                            comparacao_por_fornecedor[nome_forn]['previsao_por_periodo'][periodo] = 0
                            comparacao_por_fornecedor[nome_forn]['ano_anterior_por_periodo'][periodo] = 0
                        comparacao_por_fornecedor[nome_forn]['previsao_por_periodo'][periodo] += p.get('previsao', 0)
                        comparacao_por_fornecedor[nome_forn]['ano_anterior_por_periodo'][periodo] += p.get('ano_anterior', 0)

        # Calcular variacao percentual e ordenar
        comparacao_yoy_por_fornecedor = []
        for nome_forn, dados in comparacao_por_fornecedor.items():
            prev = dados['previsao_total']
            ant = dados['ano_anterior_total']
            variacao = ((prev - ant) / ant * 100) if ant > 0 else 0

            comparacao_yoy_por_fornecedor.append({
                'nome_fornecedor': nome_forn,
                'previsao_total': round(prev, 2),
                'ano_anterior_total': round(ant, 2),
                'variacao_percentual': round(variacao, 1),
                'previsao_por_periodo': dados['previsao_por_periodo'],
                'ano_anterior_por_periodo': dados['ano_anterior_por_periodo']
            })

        # Ordenar por previsao total (descendente)
        comparacao_yoy_por_fornecedor = sorted(
            comparacao_yoy_por_fornecedor,
            key=lambda x: x['previsao_total'],
            reverse=True
        )

        print(f"  Comparacao YoY montada para {len(comparacao_yoy_por_fornecedor)} fornecedores", flush=True)

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
            'periodos_previsao_formatados': datas_previsao,
            'periodos_previsao_display': [formatar_periodo_display(d, granularidade) for d in datas_previsao],
            'comparacao_yoy_por_fornecedor': comparacao_yoy_por_fornecedor
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
        from openpyxl.utils import get_column_letter

        dados = request.get_json()

        if not dados:
            return jsonify({'success': False, 'erro': 'Dados nao fornecidos'}), 400

        # Suportar dois formatos: novo (periodos, previsao, real) e antigo (dados)
        if 'periodos' in dados:
            # Novo formato V2 do frontend
            periodos = dados.get('periodos', [])
            previsao = dados.get('previsao', [])
            real = dados.get('real', [])
            variacao = dados.get('variacao', [])
            granularidade = dados.get('granularidade', 'mensal')
            total_previsao = dados.get('total_previsao', 0)
            total_real = dados.get('total_real', 0)
            variacao_total = dados.get('variacao_total', 0)
            filtros = dados.get('filtros', {})
            fornecedores = dados.get('fornecedores', [])

            if not periodos or not previsao:
                return jsonify({'success': False, 'erro': 'Periodos ou previsao vazios'}), 400

            wb = Workbook()
            ws = wb.active
            ws.title = 'Comparativo YoY'

            # Estilos
            header_font = Font(bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='667EEA', end_color='764BA2', fill_type='solid')
            total_fill = PatternFill(start_color='E8E8E8', end_color='E8E8E8', fill_type='solid')
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )

            row_num = 1

            # Informacoes de filtros (se houver)
            if filtros:
                ws.cell(row=row_num, column=1, value='Filtros Aplicados:').font = Font(bold=True)
                row_num += 1
                for chave, valor in filtros.items():
                    ws.cell(row=row_num, column=1, value=f'  {chave.title()}: {valor}')
                    row_num += 1
                row_num += 1

            # ===== TABELA CONSOLIDADA =====
            ws.cell(row=row_num, column=1, value='TABELA COMPARATIVA - CONSOLIDADO').font = Font(bold=True, size=12)
            row_num += 1

            # Cabecalho: Tipo | Periodo1 | Periodo2 | ... | TOTAL | Var %
            header_row = row_num
            ws.cell(row=header_row, column=1, value='Tipo').font = header_font
            ws.cell(row=header_row, column=1).fill = header_fill
            ws.cell(row=header_row, column=1).border = border

            for col_idx, periodo in enumerate(periodos, start=2):
                cell = ws.cell(row=header_row, column=col_idx, value=periodo)
                cell.font = header_font
                cell.fill = header_fill
                cell.border = border
                cell.alignment = Alignment(horizontal='center')

            col_total = len(periodos) + 2
            col_var = len(periodos) + 3

            ws.cell(row=header_row, column=col_total, value='TOTAL').font = header_font
            ws.cell(row=header_row, column=col_total).fill = header_fill
            ws.cell(row=header_row, column=col_total).border = border

            ws.cell(row=header_row, column=col_var, value='Var %').font = header_font
            ws.cell(row=header_row, column=col_var).fill = header_fill
            ws.cell(row=header_row, column=col_var).border = border

            # Linha de Previsao
            row_num += 1
            ws.cell(row=row_num, column=1, value='Previsao').border = border
            for col_idx, valor in enumerate(previsao, start=2):
                cell = ws.cell(row=row_num, column=col_idx, value=valor)
                cell.border = border
                cell.number_format = '#,##0'
            ws.cell(row=row_num, column=col_total, value=total_previsao).border = border
            ws.cell(row=row_num, column=col_total).number_format = '#,##0'

            # Linha de Ano Anterior
            row_num += 1
            ws.cell(row=row_num, column=1, value='Ano Ant.').border = border
            for col_idx, valor in enumerate(real, start=2):
                cell = ws.cell(row=row_num, column=col_idx, value=valor)
                cell.border = border
                cell.number_format = '#,##0'
            ws.cell(row=row_num, column=col_total, value=total_real).border = border
            ws.cell(row=row_num, column=col_total).number_format = '#,##0'

            # Linha de Variacao
            row_num += 1
            ws.cell(row=row_num, column=1, value='Var %').border = border
            for col_idx, valor in enumerate(variacao, start=2):
                cell = ws.cell(row=row_num, column=col_idx, value=f'{valor:.1f}%' if valor else '-')
                cell.border = border
            ws.cell(row=row_num, column=col_var, value=f'{variacao_total:.1f}%').border = border

            row_num += 2

            # ===== DETALHAMENTO POR FORNECEDOR (se houver) =====
            # Debug: log quantidade de fornecedores
            print(f"[Exportar] Fornecedores recebidos: {len(fornecedores) if fornecedores else 0}")
            if fornecedores:
                for f in fornecedores:
                    print(f"[Exportar]   - {f.get('nome_fornecedor', 'SEM NOME')}: {f.get('previsao_total', 0)}")

            if fornecedores and len(fornecedores) >= 1:
                ws.cell(row=row_num, column=1, value='DETALHAMENTO POR FORNECEDOR').font = Font(bold=True, size=12)
                row_num += 2

                for forn in fornecedores:
                    nome_forn = forn.get('nome_fornecedor', 'SEM NOME')
                    previsao_total_forn = forn.get('previsao_total', 0)
                    ano_ant_total_forn = forn.get('ano_anterior_total', 0)
                    variacao_forn = forn.get('variacao_percentual', 0)
                    previsao_por_periodo = forn.get('previsao_por_periodo', {})
                    ano_ant_por_periodo = forn.get('ano_anterior_por_periodo', {})

                    # Nome do fornecedor como titulo
                    ws.cell(row=row_num, column=1, value=nome_forn).font = Font(bold=True, size=11)
                    ws.cell(row=row_num, column=1).fill = total_fill
                    # Mesclar celula do nome ou deixar mais largo
                    row_num += 1

                    # Cabecalho do fornecedor
                    ws.cell(row=row_num, column=1, value='Tipo').font = header_font
                    ws.cell(row=row_num, column=1).fill = header_fill
                    ws.cell(row=row_num, column=1).border = border

                    for col_idx, periodo in enumerate(periodos, start=2):
                        cell = ws.cell(row=row_num, column=col_idx, value=periodo)
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.border = border
                        cell.alignment = Alignment(horizontal='center')

                    ws.cell(row=row_num, column=col_total, value='TOTAL').font = header_font
                    ws.cell(row=row_num, column=col_total).fill = header_fill
                    ws.cell(row=row_num, column=col_total).border = border

                    ws.cell(row=row_num, column=col_var, value='Var %').font = header_font
                    ws.cell(row=row_num, column=col_var).fill = header_fill
                    ws.cell(row=row_num, column=col_var).border = border

                    # Linha de Previsao do fornecedor
                    row_num += 1
                    ws.cell(row=row_num, column=1, value='Previsao').border = border
                    for col_idx, periodo in enumerate(periodos, start=2):
                        valor = previsao_por_periodo.get(periodo, 0)
                        cell = ws.cell(row=row_num, column=col_idx, value=round(valor) if valor else 0)
                        cell.border = border
                        cell.number_format = '#,##0'
                    ws.cell(row=row_num, column=col_total, value=round(previsao_total_forn)).border = border
                    ws.cell(row=row_num, column=col_total).number_format = '#,##0'

                    # Linha de Ano Anterior do fornecedor
                    row_num += 1
                    ws.cell(row=row_num, column=1, value='Ano Ant.').border = border
                    for col_idx, periodo in enumerate(periodos, start=2):
                        valor = ano_ant_por_periodo.get(periodo, 0)
                        cell = ws.cell(row=row_num, column=col_idx, value=round(valor) if valor else 0)
                        cell.border = border
                        cell.number_format = '#,##0'
                    ws.cell(row=row_num, column=col_total, value=round(ano_ant_total_forn)).border = border
                    ws.cell(row=row_num, column=col_total).number_format = '#,##0'

                    # Linha de Variacao do fornecedor
                    row_num += 1
                    ws.cell(row=row_num, column=1, value='Var %').border = border
                    for col_idx, periodo in enumerate(periodos, start=2):
                        prev = previsao_por_periodo.get(periodo, 0)
                        ant = ano_ant_por_periodo.get(periodo, 0)
                        var_periodo = ((prev - ant) / ant * 100) if ant > 0 else 0
                        cell = ws.cell(row=row_num, column=col_idx, value=f'{var_periodo:.1f}%' if ant > 0 else '-')
                        cell.border = border
                    ws.cell(row=row_num, column=col_var, value=f'{variacao_forn:.1f}%').border = border

                    row_num += 2

            # Ajustar largura das colunas
            ws.column_dimensions['A'].width = 15
            for col_idx in range(2, col_var + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 12

            ws.freeze_panes = 'B1'

        else:
            # Formato antigo (compatibilidade)
            if 'dados' not in dados:
                return jsonify({'success': False, 'erro': 'Dados nao fornecidos no formato esperado'}), 400

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


# =====================================================
# API DE AJUSTES MANUAIS DE PREVISAO
# =====================================================

@previsao_bp.route('/api/ajuste_previsao/salvar', methods=['POST'])
def api_salvar_ajuste_previsao():
    """
    Salva ajustes manuais de previsao.
    Recebe uma lista de ajustes por item/periodo.
    """
    try:
        dados = request.get_json()

        if not dados or 'ajustes' not in dados:
            return jsonify({'success': False, 'erro': 'Dados de ajuste nao fornecidos'}), 400

        ajustes = dados.get('ajustes', [])
        motivo = dados.get('motivo', None)
        usuario = dados.get('usuario', 'sistema')

        if not ajustes:
            return jsonify({'success': False, 'erro': 'Nenhum ajuste fornecido'}), 400

        # Conectar ao banco
        from app.utils.db_connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        ajustes_salvos = 0

        for ajuste in ajustes:
            cod_produto = ajuste.get('cod_produto')
            periodo = ajuste.get('periodo')
            granularidade = ajuste.get('granularidade', 'mensal')
            valor_original = ajuste.get('valor_original', 0)
            valor_ajustado = ajuste.get('valor_ajustado', 0)
            cod_fornecedor = ajuste.get('cod_fornecedor')
            nome_fornecedor = ajuste.get('nome_fornecedor')
            metodo_estatistico = ajuste.get('metodo_estatistico')

            if not cod_produto or not periodo:
                continue

            # Calcular diferenca e percentual
            diferenca = valor_ajustado - valor_original
            percentual_ajuste = 0
            if valor_original > 0:
                percentual_ajuste = ((valor_ajustado - valor_original) / valor_original) * 100

            # Inserir ajuste (trigger desativa ajustes antigos automaticamente)
            cursor.execute("""
                INSERT INTO ajuste_previsao (
                    cod_produto, cod_fornecedor, nome_fornecedor,
                    periodo, granularidade,
                    valor_original, valor_ajustado, diferenca, percentual_ajuste,
                    motivo, usuario_ajuste, metodo_estatistico
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                cod_produto, cod_fornecedor, nome_fornecedor,
                periodo, granularidade,
                valor_original, valor_ajustado, diferenca, percentual_ajuste,
                motivo, usuario, metodo_estatistico
            ))

            ajustes_salvos += 1

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'mensagem': f'{ajustes_salvos} ajuste(s) salvo(s) com sucesso',
            'ajustes_salvos': ajustes_salvos
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@previsao_bp.route('/api/ajuste_previsao/carregar', methods=['GET'])
def api_carregar_ajustes_previsao():
    """
    Carrega ajustes ativos para um produto ou lista de produtos.
    Parametros: cod_produto, cod_fornecedor, granularidade
    """
    try:
        cod_produto = request.args.get('cod_produto')
        cod_fornecedor = request.args.get('cod_fornecedor')
        granularidade = request.args.get('granularidade')

        # Conectar ao banco
        from app.utils.db_connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Construir query dinamicamente
        query = """
            SELECT
                id, cod_produto, cod_fornecedor, nome_fornecedor,
                periodo, granularidade,
                valor_original, valor_ajustado, diferenca, percentual_ajuste,
                motivo, usuario_ajuste, data_ajuste, metodo_estatistico
            FROM ajuste_previsao
            WHERE ativo = TRUE
        """
        params = []

        if cod_produto:
            query += " AND cod_produto = %s"
            params.append(cod_produto)

        if cod_fornecedor:
            query += " AND cod_fornecedor = %s"
            params.append(cod_fornecedor)

        if granularidade:
            query += " AND granularidade = %s"
            params.append(granularidade)

        query += " ORDER BY cod_produto, periodo"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Formatar resultados
        ajustes = []
        for row in rows:
            ajustes.append({
                'id': row[0],
                'cod_produto': row[1],
                'cod_fornecedor': row[2],
                'nome_fornecedor': row[3],
                'periodo': row[4],
                'granularidade': row[5],
                'valor_original': float(row[6]) if row[6] else 0,
                'valor_ajustado': float(row[7]) if row[7] else 0,
                'diferenca': float(row[8]) if row[8] else 0,
                'percentual_ajuste': float(row[9]) if row[9] else 0,
                'motivo': row[10],
                'usuario_ajuste': row[11],
                'data_ajuste': row[12].isoformat() if row[12] else None,
                'metodo_estatistico': row[13]
            })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'ajustes': ajustes,
            'total': len(ajustes)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@previsao_bp.route('/api/ajuste_previsao/historico', methods=['GET'])
def api_historico_ajustes():
    """
    Retorna historico de ajustes para um produto.
    """
    try:
        cod_produto = request.args.get('cod_produto')

        if not cod_produto:
            return jsonify({'success': False, 'erro': 'cod_produto e obrigatorio'}), 400

        # Conectar ao banco
        from app.utils.db_connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                h.id, h.cod_produto, h.periodo, h.granularidade,
                h.valor_original, h.valor_ajustado, h.motivo,
                h.usuario_acao, h.tipo_acao, h.data_acao
            FROM ajuste_previsao_historico h
            WHERE h.cod_produto = %s
            ORDER BY h.data_acao DESC
            LIMIT 100
        """, (cod_produto,))

        rows = cursor.fetchall()

        historico = []
        for row in rows:
            historico.append({
                'id': row[0],
                'cod_produto': row[1],
                'periodo': row[2],
                'granularidade': row[3],
                'valor_original': float(row[4]) if row[4] else 0,
                'valor_ajustado': float(row[5]) if row[5] else 0,
                'motivo': row[6],
                'usuario_acao': row[7],
                'tipo_acao': row[8],
                'data_acao': row[9].isoformat() if row[9] else None
            })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'historico': historico,
            'total': len(historico)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@previsao_bp.route('/api/ajuste_previsao/excluir', methods=['POST'])
def api_excluir_ajuste():
    """
    Exclui (desativa) um ajuste especifico.
    """
    try:
        dados = request.get_json()
        ajuste_id = dados.get('id')
        cod_produto = dados.get('cod_produto')
        periodo = dados.get('periodo')

        if not ajuste_id and not (cod_produto and periodo):
            return jsonify({'success': False, 'erro': 'Informe id ou (cod_produto + periodo)'}), 400

        # Conectar ao banco
        from app.utils.db_connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        if ajuste_id:
            cursor.execute("""
                UPDATE ajuste_previsao
                SET ativo = FALSE, updated_at = NOW()
                WHERE id = %s
            """, (ajuste_id,))
        else:
            cursor.execute("""
                UPDATE ajuste_previsao
                SET ativo = FALSE, updated_at = NOW()
                WHERE cod_produto = %s AND periodo = %s AND ativo = TRUE
            """, (cod_produto, periodo))

        conn.commit()
        registros_afetados = cursor.rowcount

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'mensagem': f'{registros_afetados} ajuste(s) excluido(s)',
            'registros_afetados': registros_afetados
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@previsao_bp.route('/api/historico_item', methods=['GET'])
def api_historico_item():
    """
    Retorna historico de vendas de um item especifico para exibicao no grafico drill-down.
    Retorna dados agregados por mes/semana/dia dos ultimos 2 anos.
    """
    try:
        cod_produto = request.args.get('cod_produto')
        cod_loja = request.args.get('cod_loja')
        granularidade = request.args.get('granularidade', 'mensal')

        if not cod_produto:
            return jsonify({'success': False, 'erro': 'cod_produto e obrigatorio'}), 400

        from app.utils.db_connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Buscar vendas dos ultimos 2 anos da tabela historico_vendas_diario
        # Nota: a tabela usa 'codigo' (INTEGER) e 'data' (DATE)
        query = """
            SELECT
                h.data as data_venda,
                SUM(h.qtd_venda) as qtd_venda
            FROM historico_vendas_diario h
            WHERE h.codigo::text = %s
              AND h.data >= CURRENT_DATE - INTERVAL '2 years'
        """
        params = [str(cod_produto)]

        if cod_loja:
            query += " AND h.cod_loja = %s"
            params.append(cod_loja)

        query += " GROUP BY h.data ORDER BY h.data"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        # Agregar por granularidade
        dados_agregados = {}

        for row in rows:
            data_venda = row[0]
            qtd = float(row[1]) if row[1] else 0

            if granularidade == 'mensal':
                # Formato: YYYY-MM
                chave = data_venda.strftime('%Y-%m')
            elif granularidade == 'semanal':
                # Formato: YYYY-SWW
                ano_iso, semana_iso, _ = data_venda.isocalendar()
                chave = f"{ano_iso}-S{semana_iso:02d}"
            else:
                # Diario: YYYY-MM-DD
                chave = data_venda.strftime('%Y-%m-%d')

            if chave not in dados_agregados:
                dados_agregados[chave] = 0
            dados_agregados[chave] += qtd

        # Converter para lista ordenada
        historico = []
        for periodo in sorted(dados_agregados.keys()):
            historico.append({
                'periodo': periodo,
                'valor': round(dados_agregados[periodo], 2)
            })

        return jsonify({
            'success': True,
            'cod_produto': cod_produto,
            'granularidade': granularidade,
            'historico': historico,
            'total_periodos': len(historico)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


# =====================================================
# API DE EXPORTACAO DO RELATORIO DETALHADO DE ITENS
# =====================================================

@previsao_bp.route('/api/exportar_relatorio_itens', methods=['POST'])
def api_exportar_relatorio_itens():
    """
    Exporta o relatorio detalhado de itens para Excel.
    Recebe os dados do relatorio_detalhado e gera arquivo Excel.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        from openpyxl.utils import get_column_letter

        dados = request.get_json()

        if not dados:
            return jsonify({'success': False, 'erro': 'Dados nao fornecidos'}), 400

        itens = dados.get('itens', [])
        periodos = dados.get('periodos', [])
        granularidade = dados.get('granularidade', 'mensal')
        filtros = dados.get('filtros', {})

        if not itens:
            return jsonify({'success': False, 'erro': 'Nenhum item para exportar'}), 400

        # Criar workbook
        wb = Workbook()
        ws = wb.active
        ws.title = 'Relatorio Detalhado'

        # Estilos
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='10B981', end_color='059669', fill_type='solid')
        fornecedor_fill = PatternFill(start_color='E0F2F1', end_color='E0F2F1', fill_type='solid')
        total_fill = PatternFill(start_color='047857', end_color='047857', fill_type='solid')
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        row_num = 1

        # Informacoes de filtros (se houver)
        if filtros:
            ws.cell(row=row_num, column=1, value='Filtros Aplicados:').font = Font(bold=True)
            row_num += 1
            for chave, valor in filtros.items():
                if valor:
                    ws.cell(row=row_num, column=1, value=f'  {chave.title()}: {valor}')
                    row_num += 1
            row_num += 1

        # Funcao auxiliar para formatar periodo
        meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

        def formatar_periodo_header(periodo):
            if not periodo:
                return '-'
            if granularidade == 'semanal':
                if isinstance(periodo, dict):
                    return f"S{periodo.get('semana', '?')}/{periodo.get('ano', '?')}"
                elif isinstance(periodo, str) and '-S' in periodo:
                    ano, sem = periodo.split('-S')
                    return f"S{int(sem)}/{ano}"
                return str(periodo)
            elif granularidade in ['diario', 'diaria']:
                if isinstance(periodo, str):
                    partes = periodo.split('-')
                    if len(partes) == 3:
                        return f"{partes[2]}/{partes[1]}"
                return str(periodo)
            else:
                # Mensal
                if isinstance(periodo, dict):
                    mes_idx = periodo.get('mes', 1) - 1
                    return f"{meses_nomes[mes_idx]}/{periodo.get('ano', '?')}"
                return str(periodo)

        # Cabecalho
        headers = ['Codigo', 'Descricao']
        for periodo in periodos:
            headers.append(formatar_periodo_header(periodo))
        headers.extend(['Total Prev.', 'Ano Ant.', 'Var. %', 'Alerta', 'Metodo', 'CUE'])

        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=row_num, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center')

        row_num += 1

        # Agrupar itens por fornecedor
        itens_por_fornecedor = {}
        for item in itens:
            fornecedor = item.get('nome_fornecedor') or 'SEM FORNECEDOR'
            if fornecedor not in itens_por_fornecedor:
                itens_por_fornecedor[fornecedor] = []
            itens_por_fornecedor[fornecedor].append(item)

        # Ordenar fornecedores alfabeticamente
        fornecedores_ordenados = sorted(itens_por_fornecedor.keys())

        for fornecedor in fornecedores_ordenados:
            itens_fornecedor = itens_por_fornecedor[fornecedor]

            # Calcular totais do fornecedor
            total_prev_forn = 0
            total_aa_forn = 0
            totais_por_periodo = [0] * len(periodos)

            for item in itens_fornecedor:
                total_prev_forn += item.get('demanda_prevista_total', 0)
                total_aa_forn += item.get('demanda_ano_anterior', 0)

                if item.get('previsao_por_periodo'):
                    for idx, p in enumerate(item['previsao_por_periodo']):
                        if idx < len(periodos):
                            totais_por_periodo[idx] += p.get('previsao', 0)

            variacao_forn = ((total_prev_forn - total_aa_forn) / total_aa_forn * 100) if total_aa_forn > 0 else 0

            # Linha do fornecedor (agregada)
            ws.cell(row=row_num, column=1, value='').fill = fornecedor_fill
            ws.cell(row=row_num, column=1).border = border
            ws.cell(row=row_num, column=2, value=f'{fornecedor} ({len(itens_fornecedor)} itens)').font = Font(bold=True)
            ws.cell(row=row_num, column=2).fill = fornecedor_fill
            ws.cell(row=row_num, column=2).border = border

            for idx, total in enumerate(totais_por_periodo, start=3):
                cell = ws.cell(row=row_num, column=idx, value=round(total))
                cell.fill = fornecedor_fill
                cell.border = border
                cell.number_format = '#,##0'
                cell.font = Font(bold=True)

            col_offset = 3 + len(periodos)
            ws.cell(row=row_num, column=col_offset, value=round(total_prev_forn)).fill = fornecedor_fill
            ws.cell(row=row_num, column=col_offset).border = border
            ws.cell(row=row_num, column=col_offset).number_format = '#,##0'
            ws.cell(row=row_num, column=col_offset).font = Font(bold=True)

            ws.cell(row=row_num, column=col_offset + 1, value=round(total_aa_forn)).fill = fornecedor_fill
            ws.cell(row=row_num, column=col_offset + 1).border = border
            ws.cell(row=row_num, column=col_offset + 1).number_format = '#,##0'
            ws.cell(row=row_num, column=col_offset + 1).font = Font(bold=True)

            ws.cell(row=row_num, column=col_offset + 2, value=f'{variacao_forn:.1f}%').fill = fornecedor_fill
            ws.cell(row=row_num, column=col_offset + 2).border = border
            ws.cell(row=row_num, column=col_offset + 2).font = Font(bold=True)

            ws.cell(row=row_num, column=col_offset + 3, value='').fill = fornecedor_fill
            ws.cell(row=row_num, column=col_offset + 3).border = border

            ws.cell(row=row_num, column=col_offset + 4, value='').fill = fornecedor_fill
            ws.cell(row=row_num, column=col_offset + 4).border = border

            ws.cell(row=row_num, column=col_offset + 5, value='').fill = fornecedor_fill
            ws.cell(row=row_num, column=col_offset + 5).border = border

            row_num += 1

            # Linhas dos itens do fornecedor
            for item in itens_fornecedor:
                ws.cell(row=row_num, column=1, value=item.get('cod_produto', '')).border = border
                ws.cell(row=row_num, column=2, value=item.get('descricao', '')[:50]).border = border

                # Valores por periodo
                if item.get('previsao_por_periodo'):
                    for idx, p in enumerate(item['previsao_por_periodo'], start=3):
                        if idx - 3 < len(periodos):
                            cell = ws.cell(row=row_num, column=idx, value=round(p.get('previsao', 0)))
                            cell.border = border
                            cell.number_format = '#,##0'

                col_offset = 3 + len(periodos)
                ws.cell(row=row_num, column=col_offset, value=round(item.get('demanda_prevista_total', 0))).border = border
                ws.cell(row=row_num, column=col_offset).number_format = '#,##0'

                ws.cell(row=row_num, column=col_offset + 1, value=round(item.get('demanda_ano_anterior', 0))).border = border
                ws.cell(row=row_num, column=col_offset + 1).number_format = '#,##0'

                variacao_item = item.get('variacao_percentual', 0)
                ws.cell(row=row_num, column=col_offset + 2, value=f'{variacao_item:.1f}%').border = border

                # Emoji de alerta (converter para texto)
                sinal = item.get('sinal_emoji', '')
                alerta_texto = {
                    '🔴': 'CRITICO',
                    '🟡': 'ALERTA',
                    '🔵': 'ATENCAO',
                    '🟢': 'NORMAL',
                    '⚪': 'SEM DADOS'
                }.get(sinal, '-')
                ws.cell(row=row_num, column=col_offset + 3, value=alerta_texto).border = border

                ws.cell(row=row_num, column=col_offset + 4, value=item.get('metodo_estatistico', '')).border = border

                cue_valor = item.get('cue', 0)
                ws.cell(row=row_num, column=col_offset + 5, value=cue_valor).border = border
                ws.cell(row=row_num, column=col_offset + 5).number_format = '#,##0.0000'

                row_num += 1

        # Ajustar largura das colunas
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 35
        for col_idx in range(3, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 12

        ws.freeze_panes = 'C2'

        # =====================================================
        # ABA 2: RELATORIO EM VALOR DE CUSTO (CUE)
        # =====================================================
        ws_custo = wb.create_sheet(title='Custo (CUE)')

        custo_header_fill = PatternFill(start_color='3B82F6', end_color='1D4ED8', fill_type='solid')
        custo_fornecedor_fill = PatternFill(start_color='DBEAFE', end_color='DBEAFE', fill_type='solid')
        custo_total_fill = PatternFill(start_color='1E40AF', end_color='1E40AF', fill_type='solid')

        row_custo = 1

        # Filtros (se houver)
        if filtros:
            ws_custo.cell(row=row_custo, column=1, value='Filtros Aplicados:').font = Font(bold=True)
            row_custo += 1
            for chave, valor in filtros.items():
                if valor:
                    ws_custo.cell(row=row_custo, column=1, value=f'  {chave.title()}: {valor}')
                    row_custo += 1
            row_custo += 1

        # Cabecalho
        headers_custo = ['Codigo', 'Descricao']
        for periodo in periodos:
            headers_custo.append(formatar_periodo_header(periodo))
        headers_custo.extend(['Total Prev. R$', 'CUE Unit.'])

        for col, header in enumerate(headers_custo, start=1):
            cell = ws_custo.cell(row=row_custo, column=col, value=header)
            cell.font = header_font
            cell.fill = custo_header_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center')

        row_custo += 1

        # Agrupar e ordenar por fornecedor (mesmo da aba 1)
        for fornecedor in fornecedores_ordenados:
            itens_fornecedor = itens_por_fornecedor[fornecedor]

            # Totais de custo do fornecedor
            total_custo_forn = 0
            totais_custo_periodo = [0] * len(periodos)

            for item in itens_fornecedor:
                cue = item.get('cue', 0)
                total_custo_forn += item.get('demanda_prevista_total', 0) * cue

                if item.get('previsao_por_periodo'):
                    for idx, p in enumerate(item['previsao_por_periodo']):
                        if idx < len(periodos):
                            totais_custo_periodo[idx] += p.get('previsao', 0) * cue

            # Linha do fornecedor
            ws_custo.cell(row=row_custo, column=1, value='').fill = custo_fornecedor_fill
            ws_custo.cell(row=row_custo, column=1).border = border
            ws_custo.cell(row=row_custo, column=2, value=f'{fornecedor} ({len(itens_fornecedor)} itens)').font = Font(bold=True)
            ws_custo.cell(row=row_custo, column=2).fill = custo_fornecedor_fill
            ws_custo.cell(row=row_custo, column=2).border = border

            for idx, total in enumerate(totais_custo_periodo, start=3):
                cell = ws_custo.cell(row=row_custo, column=idx, value=round(total, 2))
                cell.fill = custo_fornecedor_fill
                cell.border = border
                cell.number_format = '#,##0.00'
                cell.font = Font(bold=True)

            col_custo_offset = 3 + len(periodos)
            ws_custo.cell(row=row_custo, column=col_custo_offset, value=round(total_custo_forn, 2)).fill = custo_fornecedor_fill
            ws_custo.cell(row=row_custo, column=col_custo_offset).border = border
            ws_custo.cell(row=row_custo, column=col_custo_offset).number_format = '#,##0.00'
            ws_custo.cell(row=row_custo, column=col_custo_offset).font = Font(bold=True)

            ws_custo.cell(row=row_custo, column=col_custo_offset + 1, value='').fill = custo_fornecedor_fill
            ws_custo.cell(row=row_custo, column=col_custo_offset + 1).border = border

            row_custo += 1

            # Linhas dos itens
            for item in itens_fornecedor:
                cue = item.get('cue', 0)

                ws_custo.cell(row=row_custo, column=1, value=item.get('cod_produto', '')).border = border
                ws_custo.cell(row=row_custo, column=2, value=item.get('descricao', '')[:50]).border = border

                if item.get('previsao_por_periodo'):
                    for idx, p in enumerate(item['previsao_por_periodo'], start=3):
                        if idx - 3 < len(periodos):
                            valor_custo = round(p.get('previsao', 0) * cue, 2)
                            cell = ws_custo.cell(row=row_custo, column=idx, value=valor_custo)
                            cell.border = border
                            cell.number_format = '#,##0.00'

                col_custo_offset = 3 + len(periodos)
                total_item_custo = round(item.get('demanda_prevista_total', 0) * cue, 2)
                ws_custo.cell(row=row_custo, column=col_custo_offset, value=total_item_custo).border = border
                ws_custo.cell(row=row_custo, column=col_custo_offset).number_format = '#,##0.00'

                ws_custo.cell(row=row_custo, column=col_custo_offset + 1, value=round(cue, 4)).border = border
                ws_custo.cell(row=row_custo, column=col_custo_offset + 1).number_format = '#,##0.0000'

                row_custo += 1

        # Ajustar largura
        ws_custo.column_dimensions['A'].width = 12
        ws_custo.column_dimensions['B'].width = 35
        for col_idx in range(3, len(headers_custo) + 1):
            ws_custo.column_dimensions[get_column_letter(col_idx)].width = 15

        ws_custo.freeze_panes = 'C2'

        # Salvar em memoria
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'relatorio_detalhado_itens_{timestamp}.xlsx'

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
