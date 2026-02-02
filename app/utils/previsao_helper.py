"""
Funcoes auxiliares para processamento de previsao de demanda.
Contem a funcao principal processar_previsao() e variaveis globais compartilhadas.
"""

import os
import pandas as pd
from flask import current_app

# Importar modulos do core
from core.data_adapter import DataAdapter
from core.stockout_handler import processar_stockouts_dataframe, calcular_metricas_stockout
from core.method_selector import MethodSelector
from core.forecasting_models import get_modelo
from core.aggregator import CDAggregator, gerar_previsoes_cd
from core.reporter import ExcelReporter, gerar_nome_arquivo, preparar_resultados
from core.smart_alerts import generate_alerts_for_forecast, SmartAlertGenerator

# Variavel global para armazenar dados da ultima previsao (sessao simples)
ultima_previsao_data = None


def get_ultima_previsao_data():
    """Retorna os dados da ultima previsao processada."""
    global ultima_previsao_data
    return ultima_previsao_data


def set_ultima_previsao_data(data):
    """Define os dados da ultima previsao processada."""
    global ultima_previsao_data
    ultima_previsao_data = data


def processar_previsao(arquivo_excel: str,
                      meses_previsao: int = 6,
                      granularidade: str = 'semanal',
                      filiais_filtro: list = None,
                      produtos_filtro: list = None,
                      output_folder: str = 'outputs') -> dict:
    """
    Pipeline completo de processamento de previsao de demanda.
    Trabalha com dados diarios do banco de dados.

    Args:
        arquivo_excel: Caminho para arquivo Excel com dados diarios
                      Colunas esperadas: data, cod_empresa, codigo, und_venda, qtd_venda, padrao_compra
        meses_previsao: Numero de periodos para prever (semanas ou meses, conforme granularidade)
        granularidade: 'semanal' (padrao) ou 'mensal'
        filiais_filtro: Lista de codigos de filiais para filtrar (None = todas)
        produtos_filtro: Lista de codigos de produtos para filtrar (None = todos)
        output_folder: Pasta para salvar arquivos de saida

    Returns:
        Dicionario com todos os resultados e arquivo Excel gerado
    """
    alertas = []

    # 1. CARREGAR E VALIDAR DADOS DIARIOS
    print("1. Carregando dados diarios do banco...")
    adapter = DataAdapter(arquivo_excel)

    valido, mensagens = adapter.carregar_e_validar()
    if not valido:
        raise ValueError(f"Dados invalidos: {'; '.join(mensagens)}")

    # Converter para formato processavel (agregacao semanal/mensal)
    print(f"   Agregando dados: {granularidade}")
    df = adapter.converter_para_formato_legado(
        granularidade=granularidade,
        filiais=filiais_filtro,
        produtos=produtos_filtro
    )

    # Adicionar metadados
    metadados = {
        'granularidade': granularidade,
        'filiais_disponiveis': adapter.get_lista_filiais(),
        'produtos_disponiveis': adapter.get_lista_produtos(),
        'estatisticas': adapter.estatisticas_dados()
    }

    # Adicionar mensagens de validacao como alertas
    for msg in mensagens:
        alertas.append({'tipo': 'info', 'mensagem': msg})

    print(f"   [OK] {len(df)} registros ({granularidade}) carregados")

    # 2. PREPARAR COLUNAS NECESSARIAS
    if 'Mes_Projetado' not in df.columns:
        df['Mes_Projetado'] = False
        df['Taxa_Progresso'] = 1.0
        df['Vendas_Original'] = df['Vendas']

    # 3. TRATAR STOCKOUTS
    print("3. Tratando stockouts...")
    df = processar_stockouts_dataframe(df)
    df_rupturas = calcular_metricas_stockout(df)

    # 3.5 TREINAR SELETOR ML DE METODOS
    print("3.5 Treinando seletor inteligente de metodos...")
    ml_selector = None
    try:
        from core.ml_selector import MLMethodSelector
        ml_selector = MLMethodSelector()

        # Treinar com historico
        stats_treino = ml_selector.treinar_com_historico(
            df[['SKU', 'Loja', 'Mes', 'Vendas_Corrigidas']].rename(columns={'Vendas_Corrigidas': 'Vendas'})
        )

        if stats_treino['sucesso']:
            print(f"   [OK] Modelo ML treinado com {stats_treino['series_validas']} series")
            print(f"   [OK] Acuracia: {stats_treino['acuracia']:.1%}")
        else:
            print(f"   [AVISO] ML nao treinado - usando seletor baseado em regras")
            ml_selector = None
    except Exception as e:
        print(f"   [AVISO] Erro ao treinar ML: {e}")
        ml_selector = None

    # 4. GERAR PREVISOES POR LOJA + SKU
    print("4. Gerando previsoes por loja...")
    previsoes_lojas = []
    metodos_utilizados = []
    caracteristicas_series = []
    todos_alertas = []

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
        serie = pd.Series(vendas)

        # TRATAMENTO ESPECIAL PARA SERIES CURTAS
        from core.short_series_handler import ShortSeriesHandler
        short_handler = ShortSeriesHandler()
        classificacao_serie = short_handler.classificar_serie(serie)

        # Se serie e muito curta, usar tratamento especializado
        if len(serie) < 6:
            sugestao_adaptativa = short_handler.sugerir_metodo_adaptativo(serie)

            recomendacao = {
                'metodo': sugestao_adaptativa['metodo_sugerido'],
                'confianca': sugestao_adaptativa['confianca_estimada'],
                'razao': sugestao_adaptativa['razao'] + f" ({len(serie)} meses de historico)",
                'caracteristicas': {
                    'serie_curta': True,
                    'classificacao': classificacao_serie['categoria'],
                    'tendencia': sugestao_adaptativa['analise_tendencia']['tipo']
                },
                'alternativas': []
            }
        elif ml_selector and ml_selector.is_trained and classificacao_serie['permite_ml']:
            metodo_ml, confianca_ml = ml_selector.selecionar_metodo(serie)

            recomendacao = {
                'metodo': metodo_ml,
                'confianca': confianca_ml,
                'razao': f'Selecionado por ML (confianca: {confianca_ml:.1%})',
                'caracteristicas': ml_selector.extrair_caracteristicas(serie),
                'alternativas': []
            }
        else:
            selector = MethodSelector(vendas, datas)
            recomendacao = selector.recomendar_metodo()

        # Registrar metodo
        metodos_utilizados.append({
            'Local': loja,
            'SKU': sku,
            'Metodo': recomendacao['metodo'],
            'Confianca': recomendacao['confianca'],
            'Razao': recomendacao['razao'],
            'Alternativas': ', '.join(recomendacao.get('alternativas', []))
        })

        # Registrar caracteristicas
        caract = recomendacao['caracteristicas']
        caracteristicas_series.append({
            'Local': loja,
            'SKU': sku,
            'Intermitente': 'Sim' if caract.get('intermitente') else 'Nao',
            'Tendencia': caract.get('tipo_tendencia', 'none'),
            'Sazonalidade': 'Sim' if caract.get('tem_sazonalidade') else 'Nao',
            'Volatilidade': caract.get('volatilidade', 'N/A'),
            'N_Periodos': caract.get('n_periodos', len(vendas))
        })

        # Gerar previsao
        try:
            modelo = get_modelo(recomendacao['metodo'])
            modelo.fit(vendas)
            previsoes = modelo.predict(meses_previsao)
        except Exception:
            modelo = get_modelo('Media Movel Simples')
            modelo.fit(vendas)
            previsoes = modelo.predict(meses_previsao)

        # Calcular metricas de acuracia (WMAPE + BIAS)
        wmape = None
        bias = None
        try:
            from core.accuracy_metrics import evaluate_model_accuracy
            if len(vendas) >= 9:
                accuracy = evaluate_model_accuracy(
                    vendas,
                    recomendacao['metodo'],
                    horizon=1
                )
                wmape = accuracy['wmape']
                bias = accuracy['bias']
        except Exception:
            pass

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
                'Confianca': recomendacao['confianca'],
                'WMAPE': round(wmape, 1) if wmape is not None else None,
                'BIAS': round(bias, 2) if bias is not None else None
            })

        # Gerar alertas inteligentes
        try:
            modelo_info = {
                **modelo.params,
                'wmape': wmape,
                'bias': bias
            }

            alertas_resultado = generate_alerts_for_forecast(
                sku=sku,
                loja=loja,
                historico=vendas,
                previsao=previsoes,
                modelo_params=modelo_info,
                estoque_atual=None,
                lead_time_dias=7,
                custo_unitario=None
            )

            todos_alertas.extend(alertas_resultado['alertas'])

        except Exception as e:
            print(f"Aviso: Nao foi possivel gerar alertas para {loja}/{sku}: {e}")

    df_previsoes_lojas = pd.DataFrame(previsoes_lojas)
    df_metodos = pd.DataFrame(metodos_utilizados)
    df_caracteristicas = pd.DataFrame(caracteristicas_series)

    # 4.5 APLICAR EVENTOS SAZONAIS (V2)
    print("4.5 Aplicando eventos sazonais (EventManagerV2)...")
    try:
        from core.event_manager_v2 import EventManagerV2

        manager = EventManagerV2()
        df_previsoes_lojas = manager.aplicar_eventos_na_previsao(df_previsoes_lojas)

        eventos_aplicados = df_previsoes_lojas[df_previsoes_lojas['Evento_Aplicado'].notna()]
        if len(eventos_aplicados) > 0:
            print(f"   OK {len(eventos_aplicados)} previsoes ajustadas por eventos")
            eventos_unicos = eventos_aplicados['Evento_Aplicado'].unique()
            for evento in eventos_unicos:
                count = len(eventos_aplicados[eventos_aplicados['Evento_Aplicado'] == evento])
                mult_medio = eventos_aplicados[eventos_aplicados['Evento_Aplicado'] == evento]['Multiplicador_Evento'].mean()
                print(f"     - {evento}: {count} ajustes (fator medio: {mult_medio:.2f}x)")
        else:
            print("   Nenhum evento aplicavel no periodo de previsao")
    except Exception as e:
        print(f"Aviso: Nao foi possivel aplicar eventos: {e}")

    # 5. GERAR PREVISOES DO CD
    print("5. Gerando previsoes do CD...")
    skus = df['SKU'].unique().tolist()
    df_previsoes_cd = gerar_previsoes_cd(df, skus, meses_previsao)

    # Adicionar metodos do CD
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
                'Intermitente': 'Sim' if caract.get('intermitente') else 'Nao',
                'Tendencia': caract.get('tipo_tendencia', 'none'),
                'Sazonalidade': 'Sim' if caract.get('tem_sazonalidade') else 'Nao',
                'Volatilidade': caract.get('volatilidade', 'N/A'),
                'N_Periodos': caract.get('n_periodos', 0)
            })

    df_metodos = pd.DataFrame(metodos_utilizados)
    df_caracteristicas = pd.DataFrame(caracteristicas_series)

    # 6. COMPILAR RESUMO
    print("6. Compilando resumo...")

    contagem_metodos = df_metodos['Metodo'].value_counts().to_dict()

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
    print("7. Gerando relatorio Excel...")

    nome_arquivo = gerar_nome_arquivo()
    caminho_saida = os.path.join(output_folder, nome_arquivo)

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

    # 8. PREPARAR DADOS PARA GRAFICO
    print("8. Preparando dados para grafico...")

    dados_historicos_lojas = df.groupby(['Mes', 'Loja', 'SKU'])['Vendas_Corrigidas'].sum().reset_index()
    dados_historicos_lojas['Mes'] = dados_historicos_lojas['Mes'].dt.strftime('%Y-%m')

    dados_historicos_total = df.groupby('Mes')['Vendas_Corrigidas'].sum().reset_index()
    dados_historicos_total['Mes'] = dados_historicos_total['Mes'].dt.strftime('%Y-%m')

    dados_historicos_sku = df.groupby(['Mes', 'SKU'])['Vendas_Corrigidas'].sum().reset_index()
    dados_historicos_sku['Mes'] = dados_historicos_sku['Mes'].dt.strftime('%Y-%m')

    grafico_data = {
        'historico_lojas': dados_historicos_lojas.to_dict('records'),
        'historico_total': dados_historicos_total.to_dict('records'),
        'historico_sku': dados_historicos_sku.to_dict('records'),
        'previsoes_lojas': df_previsoes_lojas.to_dict('records'),
        'lojas': sorted(df['Loja'].unique().tolist()),
        'skus': sorted(skus)
    }

    for item in grafico_data['previsoes_lojas']:
        if 'Mes_Previsao' in item and hasattr(item['Mes_Previsao'], 'strftime'):
            item['Mes_Previsao'] = item['Mes_Previsao'].strftime('%Y-%m')

    # 9. PREPARAR DADOS PARA COMPARACAO YoY
    print("9. Preparando dados para comparacao YoY...")

    df_copy = df.copy()
    df_copy['Mes_Numero'] = df_copy['Mes'].dt.month
    df_copy['Ano'] = df_copy['Mes'].dt.year

    historico_por_mes = df_copy.groupby(['Ano', 'Mes_Numero'])['Vendas_Corrigidas'].sum().reset_index()

    comparacao_yoy = []
    meses_previsao_unicos = sorted(list(set([p['Mes_Previsao'] for p in grafico_data['previsoes_lojas']])))

    for mes_prev in meses_previsao_unicos:
        try:
            mes_prev_date = pd.to_datetime(mes_prev)
            mes_num = mes_prev_date.month
            ano_anterior = mes_prev_date.year - 1

            demanda_ano_anterior = historico_por_mes[
                (historico_por_mes['Ano'] == ano_anterior) &
                (historico_por_mes['Mes_Numero'] == mes_num)
            ]

            if not demanda_ano_anterior.empty:
                valor_ano_anterior = float(demanda_ano_anterior['Vendas_Corrigidas'].iloc[0])
            else:
                valor_ano_anterior = None

            previsao_agregada = sum([
                p['Previsao'] for p in grafico_data['previsoes_lojas']
                if p['Mes_Previsao'] == mes_prev
            ])

            if valor_ano_anterior and valor_ano_anterior > 0:
                variacao_percentual = ((previsao_agregada - valor_ano_anterior) / valor_ano_anterior) * 100
            else:
                variacao_percentual = None

            comparacao_yoy.append({
                'mes': mes_prev,
                'mes_nome': mes_prev_date.strftime('%b/%y'),
                'demanda_ano_anterior': valor_ano_anterior,
                'previsao_atual': previsao_agregada,
                'variacao_percentual': round(variacao_percentual, 1) if variacao_percentual is not None else None
            })
        except:
            pass

    grafico_data['comparacao_yoy'] = comparacao_yoy

    # 9.1. PREPARAR DADOS POR FORNECEDOR/ITEM
    print("9.1. Preparando dados por fornecedor/item...")

    def padronizar_metodo(metodo):
        if not metodo:
            return 'N/A'

        mapeamento = {
            'media movel simples': 'SMA',
            'media movel ponderada': 'WMA',
            'suavizacao exponencial simples': 'EMA',
            'regressao linear': 'Regressao com Tendencia',
            'media movel sazonal': 'Decomposicao Sazonal',
            'holt-winters': 'Decomposicao Sazonal',
            'holt': 'Regressao com Tendencia',
            'croston': 'TSB',
            'sba': 'TSB',
        }

        metodo_lower = metodo.lower()

        if metodo in ['SMA', 'WMA', 'EMA', 'Regressao com Tendencia', 'Decomposicao Sazonal', 'TSB', 'AUTO']:
            return metodo

        return mapeamento.get(metodo_lower, metodo)

    def get_fornecedor_by_sku(sku):
        try:
            sku_num = int(sku.split('_')[1])
            if 1 <= sku_num <= 34:
                return 'FORNECEDOR_A'
            elif 35 <= sku_num <= 67:
                return 'FORNECEDOR_B'
            elif 68 <= sku_num <= 100:
                return 'FORNECEDOR_C'
            else:
                return 'OUTROS'
        except:
            return 'OUTROS'

    previsoes_por_sku = {}
    for prev in grafico_data['previsoes_lojas']:
        sku = prev['SKU']
        if sku not in previsoes_por_sku:
            previsoes_por_sku[sku] = {
                'previsao_total': 0,
                'metodo': prev['Metodo']
            }
        previsoes_por_sku[sku]['previsao_total'] += prev['Previsao']

    print(f"9.1. Calculando demanda do mesmo periodo do ano anterior por SKU...")

    df_copy['Ano'] = df_copy['Mes'].dt.year
    df_copy['Mes_Numero'] = df_copy['Mes'].dt.month

    demanda_ano_anterior_sku = {}

    for sku in skus:
        total_ano_anterior = 0
        for mes_prev in meses_previsao_unicos:
            try:
                mes_prev_date = pd.to_datetime(mes_prev)
                mes_num = mes_prev_date.month
                ano_anterior = mes_prev_date.year - 1

                demanda_mes = df_copy[
                    (df_copy['SKU'] == sku) &
                    (df_copy['Ano'] == ano_anterior) &
                    (df_copy['Mes_Numero'] == mes_num)
                ]['Vendas_Corrigidas'].sum()

                total_ano_anterior += demanda_mes
            except:
                pass

        demanda_ano_anterior_sku[sku] = total_ano_anterior

    print(f"   Comparando previsoes com mesmos meses do ano anterior")
    print(f"   Exemplo: Se prevendo Jul-Dez/2024, compara com Jul-Dez/2023")

    dados_fornecedor_item = []
    for sku in sorted(skus):
        fornecedor = get_fornecedor_by_sku(sku)
        previsao_dados = previsoes_por_sku.get(sku, {'previsao_total': 0, 'metodo': 'N/A'})
        previsao_total = previsao_dados['previsao_total']
        metodo = previsao_dados['metodo']

        demanda_anterior = demanda_ano_anterior_sku.get(sku, 0)

        if demanda_anterior > 0:
            variacao_pct = ((previsao_total - demanda_anterior) / demanda_anterior) * 100
        else:
            variacao_pct = None

        dados_fornecedor_item.append({
            'Fornecedor': fornecedor,
            'SKU': sku,
            'Demanda_Prevista': round(previsao_total, 1),
            'Demanda_Ano_Anterior': round(demanda_anterior, 1),
            'Variacao_YoY_Percentual': round(variacao_pct, 1) if variacao_pct is not None else None,
            'Metodo_Estatistico': padronizar_metodo(metodo)
        })

    grafico_data['fornecedor_item'] = dados_fornecedor_item

    # 10. CALCULAR METRICAS ADICIONAIS PARA O RESUMO
    print("10. Calculando metricas adicionais...")

    print("10.1. Calculando YoY das previsoes individuais...")

    total_previsao_agregada = sum([item['previsao_atual'] for item in comparacao_yoy if item['previsao_atual']])
    total_ano_anterior_agregado = sum([item['demanda_ano_anterior'] for item in comparacao_yoy if item['demanda_ano_anterior']])

    if total_ano_anterior_agregado > 0:
        taxa_variabilidade_media_yoy = round(((total_previsao_agregada - total_ano_anterior_agregado) / total_ano_anterior_agregado) * 100, 1)
        print(f"   [OK] YoY Total (soma das previsoes individuais): {taxa_variabilidade_media_yoy:+.1f}%")
        print(f"       Total previsto (soma individual): {total_previsao_agregada:,.0f}")
        print(f"       Total ano anterior: {total_ano_anterior_agregado:,.0f}")
    else:
        taxa_variabilidade_media_yoy = 0
        print(f"   [AVISO] Total periodo anterior e zero")

    if comparacao_yoy and len(comparacao_yoy) > 0:
        primeiro_mes_previsao = pd.to_datetime(comparacao_yoy[0]['mes'])
        ultimo_mes_previsao = pd.to_datetime(comparacao_yoy[-1]['mes'])

        primeiro_mes_anterior = primeiro_mes_previsao - pd.DateOffset(months=12)
        ultimo_mes_anterior = ultimo_mes_previsao - pd.DateOffset(months=12)

        mes_inicio = primeiro_mes_previsao.strftime('%b/%y')
        mes_fim = ultimo_mes_previsao.strftime('%b/%y')
        mes_inicio_anterior = primeiro_mes_anterior.strftime('%b/%y')
        mes_fim_anterior = ultimo_mes_anterior.strftime('%b/%y')

        if len(comparacao_yoy) == 1:
            anos_yoy = f"{mes_inicio_anterior} vs {mes_inicio}"
        else:
            anos_yoy = f"{mes_inicio_anterior}-{mes_fim_anterior} vs {mes_inicio}-{mes_fim}"
    else:
        anos_yoy = "N/A"

    vendas_perdidas = resumo['vendas_perdidas']
    vendas_totais = df['Vendas_Corrigidas'].sum()
    vendas_potenciais = vendas_totais + vendas_perdidas
    taxa_vendas_perdidas = round((vendas_perdidas / vendas_potenciais * 100), 1) if vendas_potenciais > 0 else 0

    ano_min = df['Mes'].min().year
    ano_max = df['Mes'].max().year
    periodo_vendas_perdidas = f"{ano_min}-{ano_max}" if ano_min != ano_max else str(ano_min)

    resumo['taxa_variabilidade_media_yoy'] = taxa_variabilidade_media_yoy
    resumo['taxa_vendas_perdidas'] = taxa_vendas_perdidas
    resumo['anos_yoy'] = anos_yoy
    resumo['periodo_vendas_perdidas'] = periodo_vendas_perdidas

    print("Processamento concluido!")

    generator = SmartAlertGenerator()
    generator.alertas = todos_alertas
    resumo_alertas = generator.get_summary()

    return {
        'success': True,
        'arquivo_saida': nome_arquivo,
        'resumo': resumo,
        'alertas': alertas,
        'grafico_data': grafico_data,
        'smart_alerts': todos_alertas,
        'smart_alerts_summary': resumo_alertas,
        'metadados': metadados
    }
