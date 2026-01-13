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
from core.data_adapter import DataAdapter
from core.stockout_handler import processar_stockouts_dataframe, calcular_metricas_stockout
from core.method_selector import MethodSelector
from core.forecasting_models import get_modelo
from core.aggregator import CDAggregator, gerar_previsoes_cd
from core.reporter import ExcelReporter, gerar_nome_arquivo, preparar_resultados
from core.replenishment_calculator import processar_reabastecimento
from core.smart_alerts import generate_alerts_for_forecast
from core.outlier_detector import auto_clean_outliers
from core.validation import validate_series
from core.seasonality_detector import detect_seasonality
from core.auto_logger import get_auto_logger

# Configuração do Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo


def processar_previsao(arquivo_excel: str,
                      meses_previsao: int = 6,
                      granularidade: str = 'semanal',
                      filiais_filtro: list = None,
                      produtos_filtro: list = None) -> dict:
    """
    Pipeline completo de processamento de previsão de demanda
    Trabalha com dados diários do banco de dados

    Args:
        arquivo_excel: Caminho para arquivo Excel com dados diários
                      Colunas esperadas: data, cod_empresa, codigo, und_venda, qtd_venda, padrao_compra
        meses_previsao: Número de períodos para prever (semanas ou meses, conforme granularidade)
        granularidade: 'semanal' (padrão) ou 'mensal'
        filiais_filtro: Lista de códigos de filiais para filtrar (None = todas)
        produtos_filtro: Lista de códigos de produtos para filtrar (None = todos)

    Returns:
        Dicionário com todos os resultados e arquivo Excel gerado
    """
    alertas = []

    # 1. CARREGAR E VALIDAR DADOS DIÁRIOS
    print("1. Carregando dados diários do banco...")
    adapter = DataAdapter(arquivo_excel)

    valido, mensagens = adapter.carregar_e_validar()
    if not valido:
        raise ValueError(f"Dados inválidos: {'; '.join(mensagens)}")

    # Converter para formato processável (agregação semanal/mensal)
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

    # Adicionar mensagens de validação como alertas
    for msg in mensagens:
        alertas.append({'tipo': 'info', 'mensagem': msg})

    print(f"   [OK] {len(df)} registros ({granularidade}) carregados")

    # 2. PREPARAR COLUNAS NECESSÁRIAS
    if 'Mes_Projetado' not in df.columns:
        df['Mes_Projetado'] = False
        df['Taxa_Progresso'] = 1.0
        df['Vendas_Original'] = df['Vendas']

    # 3. TRATAR STOCKOUTS
    print("3. Tratando stockouts...")
    df = processar_stockouts_dataframe(df)
    df_rupturas = calcular_metricas_stockout(df)

    # 3.5 TREINAR SELETOR ML DE MÉTODOS
    print("3.5 Treinando seletor inteligente de métodos...")
    ml_selector = None
    try:
        from core.ml_selector import MLMethodSelector
        ml_selector = MLMethodSelector()

        # Treinar com histórico
        stats_treino = ml_selector.treinar_com_historico(df[['SKU', 'Loja', 'Mes', 'Vendas_Corrigidas']].rename(columns={'Vendas_Corrigidas': 'Vendas'}))

        if stats_treino['sucesso']:
            print(f"   [OK] Modelo ML treinado com {stats_treino['series_validas']} séries")
            print(f"   [OK] Acurácia: {stats_treino['acuracia']:.1%}")
        else:
            print(f"   [AVISO] ML não treinado - usando seletor baseado em regras")
            ml_selector = None
    except Exception as e:
        print(f"   [AVISO] Erro ao treinar ML: {e}")
        ml_selector = None

    # 4. GERAR PREVISÕES POR LOJA + SKU
    print("4. Gerando previsões por loja...")
    previsoes_lojas = []
    metodos_utilizados = []
    caracteristicas_series = []
    todos_alertas = []  # Lista de todos os alertas gerados

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

        # TRATAMENTO ESPECIAL PARA SÉRIES CURTAS
        from core.short_series_handler import ShortSeriesHandler
        short_handler = ShortSeriesHandler()
        classificacao_serie = short_handler.classificar_serie(serie)

        # Se série é muito curta, usar tratamento especializado
        if len(serie) < 6:  # Menos de 6 meses
            sugestao_adaptativa = short_handler.sugerir_metodo_adaptativo(serie)

            recomendacao = {
                'metodo': sugestao_adaptativa['metodo_sugerido'],
                'confianca': sugestao_adaptativa['confianca_estimada'],
                'razao': sugestao_adaptativa['razao'] + f" ({len(serie)} meses de histórico)",
                'caracteristicas': {
                    'serie_curta': True,
                    'classificacao': classificacao_serie['categoria'],
                    'tendencia': sugestao_adaptativa['analise_tendencia']['tipo']
                },
                'alternativas': []
            }
        # Selecionar método (usar ML se disponível e série suficientemente longa)
        elif ml_selector and ml_selector.is_trained and classificacao_serie['permite_ml']:
            # Usar seletor ML
            metodo_ml, confianca_ml = ml_selector.selecionar_metodo(serie)

            # Criar recomendação compatível
            recomendacao = {
                'metodo': metodo_ml,
                'confianca': confianca_ml,
                'razao': f'Selecionado por ML (confiança: {confianca_ml:.1%})',
                'caracteristicas': ml_selector.extrair_caracteristicas(serie),
                'alternativas': []
            }
        else:
            # Usar seletor baseado em regras (fallback)
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

        # Calcular métricas de acurácia (WMAPE + BIAS)
        wmape = None
        bias = None
        try:
            from core.accuracy_metrics import evaluate_model_accuracy
            if len(vendas) >= 9:  # Mínimo para validação confiável
                accuracy = evaluate_model_accuracy(
                    vendas,
                    recomendacao['metodo'],
                    horizon=1
                )
                wmape = accuracy['wmape']
                bias = accuracy['bias']
        except Exception:
            pass  # Se falhar, continua sem métricas

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
            # Preparar modelo_info com métricas e parâmetros
            modelo_info = {
                **modelo.params,  # Parâmetros do modelo (outliers, sazonalidade, etc)
                'wmape': wmape,
                'bias': bias
            }

            # Gerar alertas (sem estoque_atual e custo_unitario por enquanto)
            alertas_resultado = generate_alerts_for_forecast(
                sku=sku,
                loja=loja,
                historico=vendas,
                previsao=previsoes,
                modelo_params=modelo_info,
                estoque_atual=None,  # TODO: Integrar com dados de estoque
                lead_time_dias=7,  # Padrão: 7 dias
                custo_unitario=None  # TODO: Integrar com dados de custo
            )

            # Adicionar alertas à lista global
            todos_alertas.extend(alertas_resultado['alertas'])

        except Exception as e:
            # Se falhar geração de alertas, não quebra o processo
            print(f"Aviso: Não foi possível gerar alertas para {loja}/{sku}: {e}")

    df_previsoes_lojas = pd.DataFrame(previsoes_lojas)
    df_metodos = pd.DataFrame(metodos_utilizados)
    df_caracteristicas = pd.DataFrame(caracteristicas_series)

    # 4.5 APLICAR EVENTOS SAZONAIS
    print("4.5 Aplicando eventos sazonais...")
    try:
        from core.event_manager import EventManager

        manager = EventManager()
        df_previsoes_lojas = manager.aplicar_eventos_na_previsao(df_previsoes_lojas)

        # Contar quantos eventos foram aplicados
        eventos_aplicados = df_previsoes_lojas[df_previsoes_lojas['Evento_Aplicado'].notna()]
        if len(eventos_aplicados) > 0:
            print(f"   OK {len(eventos_aplicados)} previsoes ajustadas por eventos sazonais")
            eventos_unicos = eventos_aplicados['Evento_Aplicado'].unique()
            for evento in eventos_unicos:
                count = len(eventos_aplicados[eventos_aplicados['Evento_Aplicado'] == evento])
                print(f"     - {evento}: {count} ajustes")
    except Exception as e:
        print(f"Aviso: Não foi possível aplicar eventos sazonais: {e}")

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

    # 8. PREPARAR DADOS PARA GRÁFICO
    print("8. Preparando dados para gráfico...")

    # Dados históricos por loja
    dados_historicos_lojas = df.groupby(['Mes', 'Loja', 'SKU'])['Vendas_Corrigidas'].sum().reset_index()
    dados_historicos_lojas['Mes'] = dados_historicos_lojas['Mes'].dt.strftime('%Y-%m')

    # Dados históricos agregados (total)
    dados_historicos_total = df.groupby('Mes')['Vendas_Corrigidas'].sum().reset_index()
    dados_historicos_total['Mes'] = dados_historicos_total['Mes'].dt.strftime('%Y-%m')

    # Dados históricos por SKU (agregado todas lojas)
    dados_historicos_sku = df.groupby(['Mes', 'SKU'])['Vendas_Corrigidas'].sum().reset_index()
    dados_historicos_sku['Mes'] = dados_historicos_sku['Mes'].dt.strftime('%Y-%m')

    # Converter para formato JSON
    grafico_data = {
        'historico_lojas': dados_historicos_lojas.to_dict('records'),
        'historico_total': dados_historicos_total.to_dict('records'),
        'historico_sku': dados_historicos_sku.to_dict('records'),
        'previsoes_lojas': df_previsoes_lojas.to_dict('records'),
        'lojas': sorted(df['Loja'].unique().tolist()),
        'skus': sorted(skus)
    }

    # Converter datas de previsão para string
    for item in grafico_data['previsoes_lojas']:
        if 'Mes_Previsao' in item and hasattr(item['Mes_Previsao'], 'strftime'):
            item['Mes_Previsao'] = item['Mes_Previsao'].strftime('%Y-%m')

    # 9. PREPARAR DADOS PARA COMPARAÇÃO YoY (Ano contra Ano)
    print("9. Preparando dados para comparação YoY...")

    # Agrupar por mês (MM) ignorando ano para comparação
    df_copy = df.copy()
    df_copy['Mes_Numero'] = df_copy['Mes'].dt.month
    df_copy['Ano'] = df_copy['Mes'].dt.year

    # Dados históricos agregados por mês do ano
    historico_por_mes = df_copy.groupby(['Ano', 'Mes_Numero'])['Vendas_Corrigidas'].sum().reset_index()

    # Preparar dados de comparação YoY
    comparacao_yoy = []

    # Obter meses únicos de previsão
    meses_previsao_unicos = sorted(list(set([p['Mes_Previsao'] for p in grafico_data['previsoes_lojas']])))

    # Para cada mês de previsão, buscar o mesmo mês do ano anterior
    for mes_prev in meses_previsao_unicos:
        try:
            mes_prev_date = pd.to_datetime(mes_prev)
            mes_num = mes_prev_date.month
            ano_anterior = mes_prev_date.year - 1

            # Buscar demanda do mesmo mês no ano anterior
            demanda_ano_anterior = historico_por_mes[
                (historico_por_mes['Ano'] == ano_anterior) &
                (historico_por_mes['Mes_Numero'] == mes_num)
            ]

            if not demanda_ano_anterior.empty:
                valor_ano_anterior = float(demanda_ano_anterior['Vendas_Corrigidas'].iloc[0])
            else:
                valor_ano_anterior = None

            # Buscar previsão agregada para este mês
            previsao_agregada = sum([
                p['Previsao'] for p in grafico_data['previsoes_lojas']
                if p['Mes_Previsao'] == mes_prev
            ])

            # Calcular variação percentual
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

    # Função para padronizar nomenclatura dos métodos conforme documentação
    def padronizar_metodo(metodo):
        """
        Converte nomenclatura interna para nomenclatura da documentação.
        Agora simplificado pois method_selector já retorna os nomes corretos.
        """
        if not metodo:
            return 'N/A'

        # Mapeamento apenas para casos legados ou compatibilidade retroativa
        # Os 7 métodos oficiais: SMA, WMA, EMA, Regressão com Tendência, Decomposição Sazonal, TSB, AUTO
        mapeamento = {
            # Casos legados (caso algum código antigo ainda use)
            'média móvel simples': 'SMA',
            'média móvel ponderada': 'WMA',
            'suavização exponencial simples': 'EMA',
            'regressão linear': 'Regressão com Tendência',
            'média móvel sazonal': 'Decomposição Sazonal',
            'holt-winters': 'Decomposição Sazonal',
            'holt': 'Regressão com Tendência',
            'croston': 'TSB',  # Croston foi SUBSTITUÍDO por TSB
            'sba': 'TSB',
        }

        # Tentar match case-insensitive
        metodo_lower = metodo.lower()

        # Se já está no formato correto, retornar direto
        if metodo in ['SMA', 'WMA', 'EMA', 'Regressão com Tendência', 'Decomposição Sazonal', 'TSB', 'AUTO']:
            return metodo

        # Caso contrário, tentar conversão
        return mapeamento.get(metodo_lower, metodo)

    # Mapeamento SKU → Fornecedor (baseado na documentação INTEGRACAO_ARQUIVOS.md)
    def get_fornecedor_by_sku(sku):
        try:
            # Extrair número do SKU (ex: PROD_001 → 1)
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

    # Agregar previsões por SKU (soma de todas as lojas)
    previsoes_por_sku = {}
    for prev in grafico_data['previsoes_lojas']:
        sku = prev['SKU']
        if sku not in previsoes_por_sku:
            previsoes_por_sku[sku] = {
                'previsao_total': 0,
                'metodo': prev['Metodo']
            }
        previsoes_por_sku[sku]['previsao_total'] += prev['Previsao']

    # Calcular demanda do MESMO PERÍODO DO ANO ANTERIOR por SKU
    # Igual à lógica da comparação YoY mensal (linhas 398-434)
    print(f"9.1. Calculando demanda do mesmo período do ano anterior por SKU...")

    # Preparar histórico agregado por SKU, Ano e Mês
    df_copy['Ano'] = df_copy['Mes'].dt.year
    df_copy['Mes_Numero'] = df_copy['Mes'].dt.month

    # Para cada mês de previsão, buscar o mesmo mês do ano anterior
    meses_previsao_unicos = sorted(list(set([p['Mes_Previsao'] for p in grafico_data['previsoes_lojas']])))

    # Calcular demanda ano anterior por SKU (somando os mesmos meses do ano anterior)
    demanda_ano_anterior_sku = {}

    for sku in skus:
        total_ano_anterior = 0
        for mes_prev in meses_previsao_unicos:
            try:
                mes_prev_date = pd.to_datetime(mes_prev)
                mes_num = mes_prev_date.month
                ano_anterior = mes_prev_date.year - 1

                # Buscar demanda do mesmo mês no ano anterior para este SKU
                demanda_mes = df_copy[
                    (df_copy['SKU'] == sku) &
                    (df_copy['Ano'] == ano_anterior) &
                    (df_copy['Mes_Numero'] == mes_num)
                ]['Vendas_Corrigidas'].sum()

                total_ano_anterior += demanda_mes
            except:
                pass

        demanda_ano_anterior_sku[sku] = total_ano_anterior

    print(f"   Comparando previsões com mesmos meses do ano anterior")
    print(f"   Exemplo: Se prevendo Jul-Dez/2024, compara com Jul-Dez/2023")

    # Montar dados por fornecedor/item
    dados_fornecedor_item = []
    for sku in sorted(skus):
        fornecedor = get_fornecedor_by_sku(sku)
        previsao_dados = previsoes_por_sku.get(sku, {'previsao_total': 0, 'metodo': 'N/A'})
        previsao_total = previsao_dados['previsao_total']
        metodo = previsao_dados['metodo']

        # Demanda do mesmo período do ano anterior
        demanda_anterior = demanda_ano_anterior_sku.get(sku, 0)

        # Calcular variação percentual YoY (igual à comparação mensal)
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

    # 10. CALCULAR MÉTRICAS ADICIONAIS PARA O RESUMO
    print("10. Calculando métricas adicionais...")

    # Calcular taxa YoY usando SOMA DAS PREVISÕES INDIVIDUAIS
    # Isso é o mesmo cálculo que aparece na tabela YoY da interface
    print("10.1. Calculando YoY das previsões individuais...")

    # Somar todas as previsões e todas as demandas do ano anterior da tabela YoY
    total_previsao_agregada = sum([item['previsao_atual'] for item in comparacao_yoy if item['previsao_atual']])
    total_ano_anterior_agregado = sum([item['demanda_ano_anterior'] for item in comparacao_yoy if item['demanda_ano_anterior']])

    # Calcular variação percentual SIMPLES (igual à coluna Total da tabela)
    if total_ano_anterior_agregado > 0:
        taxa_variabilidade_media_yoy = round(((total_previsao_agregada - total_ano_anterior_agregado) / total_ano_anterior_agregado) * 100, 1)
        print(f"   [OK] YoY Total (soma das previsões individuais): {taxa_variabilidade_media_yoy:+.1f}%")
        print(f"       Total previsto (soma individual): {total_previsao_agregada:,.0f}")
        print(f"       Total ano anterior: {total_ano_anterior_agregado:,.0f}")
    else:
        taxa_variabilidade_media_yoy = 0
        print(f"   [AVISO] Total período anterior é zero")

    # Extrair período da comparação YoY
    if comparacao_yoy and len(comparacao_yoy) > 0:
        primeiro_mes_previsao = pd.to_datetime(comparacao_yoy[0]['mes'])
        ultimo_mes_previsao = pd.to_datetime(comparacao_yoy[-1]['mes'])

        # Mesmo período no ano anterior (subtrair 12 meses de cada data)
        primeiro_mes_anterior = primeiro_mes_previsao - pd.DateOffset(months=12)
        ultimo_mes_anterior = ultimo_mes_previsao - pd.DateOffset(months=12)

        # Formato: Mês/Ano
        mes_inicio = primeiro_mes_previsao.strftime('%b/%y')
        mes_fim = ultimo_mes_previsao.strftime('%b/%y')
        mes_inicio_anterior = primeiro_mes_anterior.strftime('%b/%y')
        mes_fim_anterior = ultimo_mes_anterior.strftime('%b/%y')

        # Se for apenas um mês
        if len(comparacao_yoy) == 1:
            anos_yoy = f"{mes_inicio_anterior} vs {mes_inicio}"
        else:
            anos_yoy = f"{mes_inicio_anterior}-{mes_fim_anterior} vs {mes_inicio}-{mes_fim}"
    else:
        anos_yoy = "N/A"

    # Calcular taxa de vendas perdidas (%)
    vendas_perdidas = resumo['vendas_perdidas']
    vendas_totais = df['Vendas_Corrigidas'].sum()
    vendas_potenciais = vendas_totais + vendas_perdidas
    taxa_vendas_perdidas = round((vendas_perdidas / vendas_potenciais * 100), 1) if vendas_potenciais > 0 else 0

    # Extrair período histórico (apenas ano inicial e final)
    ano_min = df['Mes'].min().year
    ano_max = df['Mes'].max().year
    periodo_vendas_perdidas = f"{ano_min}-{ano_max}" if ano_min != ano_max else str(ano_min)

    # Atualizar resumo com novas métricas
    resumo['taxa_variabilidade_media_yoy'] = taxa_variabilidade_media_yoy
    resumo['taxa_vendas_perdidas'] = taxa_vendas_perdidas
    resumo['anos_yoy'] = anos_yoy
    resumo['periodo_vendas_perdidas'] = periodo_vendas_perdidas

    print("Processamento concluído!")

    # Calcular resumo de alertas inteligentes
    from core.smart_alerts import SmartAlertGenerator
    generator = SmartAlertGenerator()
    generator.alertas = todos_alertas
    resumo_alertas = generator.get_summary()

    # Retornar resultado com metadados
    return {
        'success': True,
        'arquivo_saida': nome_arquivo,
        'resumo': resumo,
        'alertas': alertas,
        'grafico_data': grafico_data,
        'smart_alerts': todos_alertas,
        'smart_alerts_summary': resumo_alertas,
        'metadados': metadados  # Informações sobre filiais, produtos, estatísticas
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

        # Parâmetros básicos
        meses_previsao = int(request.form.get('meses_previsao', 6))
        granularidade = request.form.get('granularidade', 'semanal')  # 'semanal' ou 'mensal'

        # Filtros (podem vir como lista ou string separada por vírgula)
        filiais_str = request.form.get('filiais', '')
        produtos_str = request.form.get('produtos', '')

        # Processar filtros de filiais
        filiais_filtro = None
        if filiais_str and filiais_str.strip():
            try:
                # Aceita tanto lista JSON quanto string separada por vírgula
                if filiais_str.startswith('['):
                    import json
                    filiais_filtro = json.loads(filiais_str)
                else:
                    filiais_filtro = [int(f.strip()) for f in filiais_str.split(',') if f.strip()]
            except:
                pass  # Se falhar, não filtra

        # Processar filtros de produtos
        produtos_filtro = None
        if produtos_str and produtos_str.strip():
            try:
                if produtos_str.startswith('['):
                    import json
                    produtos_filtro = json.loads(produtos_str)
                else:
                    produtos_filtro = [int(p.strip()) for p in produtos_str.split(',') if p.strip()]
            except:
                pass  # Se falhar, não filtra

        # Salvar arquivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Processar com filtros
        resultados = processar_previsao(
            filepath,
            meses_previsao,
            granularidade=granularidade,
            filiais_filtro=filiais_filtro,
            produtos_filtro=produtos_filtro
        )

        # Armazenar dados para o simulador
        global ultima_previsao_data
        if resultados.get('success') and resultados.get('grafico_data'):
            ultima_previsao_data = resultados['grafico_data']

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
    """Download do arquivo Excel gerado ou exemplo"""
    # Primeiro tenta na pasta de outputs
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)

    # Se não encontrar, tenta na raiz (arquivos de exemplo)
    if not os.path.exists(filepath):
        filepath = filename

    if not os.path.exists(filepath):
        return jsonify({'erro': 'Arquivo não encontrado'}), 404

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ===== SIMULADOR DE CENÁRIOS =====

# Variável global para armazenar dados da última previsão (sessão simples)
ultima_previsao_data = None

@app.route('/simulador')
def simulador():
    """Página do simulador de cenários"""
    return render_template('simulador.html')


@app.route('/simulador/dados', methods=['GET'])
def get_dados_simulador():
    """
    Retorna dados da última previsão para o simulador
    """
    global ultima_previsao_data

    if ultima_previsao_data is None:
        return jsonify({
            'success': False,
            'erro': 'Nenhuma previsão disponível. Processe uma previsão primeiro na página principal.'
        }), 404

    # Transformar dados para formato esperado pelo simulador
    # JavaScript espera: { previsoes: [...], lojas: [...], skus: [...] }
    dados_formatados = {
        'previsoes': ultima_previsao_data.get('previsoes_lojas', []),
        'lojas': ultima_previsao_data.get('lojas', []),
        'skus': ultima_previsao_data.get('skus', [])
    }

    # Normalizar nomes de campos para minúsculas (JavaScript espera lowercase)
    for prev in dados_formatados['previsoes']:
        # Criar campos com nomes lowercase mantendo originais para compatibilidade
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


@app.route('/simulador/aplicar', methods=['POST'])
def aplicar_cenario():
    """
    Aplica um cenário de simulação
    """
    global ultima_previsao_data

    if ultima_previsao_data is None:
        return jsonify({
            'success': False,
            'erro': 'Nenhuma previsão disponível'
        }), 404

    try:
        from core.scenario_simulator import criar_simulador_de_dados

        # Criar simulador
        simulador = criar_simulador_de_dados(ultima_previsao_data['previsoes_lojas'])

        # Obter tipo de ajuste
        dados_request = request.get_json()
        tipo_ajuste = dados_request.get('tipo')

        # Aplicar cenário
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
            return jsonify({'success': False, 'erro': 'Tipo de ajuste inválido'}), 400

        # Calcular impacto
        impacto = simulador.calcular_impacto()

        # Obter comparação
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


@app.route('/simulador/exportar', methods=['POST'])
def exportar_cenario():
    """
    Exporta cenário simulado para Excel
    """
    global ultima_previsao_data

    if ultima_previsao_data is None:
        return jsonify({'success': False, 'erro': 'Nenhuma previsão disponível'}), 404

    try:
        from core.scenario_simulator import ScenarioSimulator
        import pandas as pd
        from io import BytesIO

        # Receber previsões simuladas do frontend
        dados_request = request.get_json()
        previsoes_simuladas = dados_request.get('previsoes_simuladas', [])

        # Converter para DataFrame
        df_base = pd.DataFrame(ultima_previsao_data['previsoes_lojas'])
        df_simulado = pd.DataFrame(previsoes_simuladas)

        # Renomear colunas para maiúsculas (padrão esperado)
        df_simulado.columns = [col.capitalize() if col.lower() in ['loja', 'sku', 'mes', 'previsao'] else col
                               for col in df_simulado.columns]

        # Criar simulador e substituir dados simulados
        simulador = ScenarioSimulator(df_base)
        simulador.previsoes_simuladas = df_simulado

        # Exportar para Excel em memória
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"Cenario_Simulado_{timestamp}.xlsx"
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], nome_arquivo)

        simulador.exportar_para_excel(filepath)

        # Enviar arquivo para download
        return send_file(
            filepath,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nome_arquivo
        )

    except Exception as e:
        print(f"Erro ao exportar cenário: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@app.route('/eventos')
def eventos():
    """Página de gerenciamento de eventos"""
    return render_template('eventos.html')


@app.route('/eventos_simples')
def eventos_simples():
    """Página simplificada de gerenciamento de eventos"""
    return render_template('eventos_simples.html')


@app.route('/eventos/cadastrar', methods=['POST'])
def cadastrar_evento():
    """Cadastra um novo evento"""
    try:
        from core.event_manager import EventManager

        dados = request.get_json()

        # Validação de dados
        if not dados:
            return jsonify({'success': False, 'erro': 'Nenhum dado recebido'}), 400

        if 'tipo' not in dados or 'data_evento' not in dados:
            return jsonify({'success': False, 'erro': 'Campos obrigatórios faltando'}), 400

        # Log de debug
        print(f"[EVENTOS] Cadastrando evento:")
        print(f"   Tipo: {dados.get('tipo')}")
        print(f"   Data: {dados.get('data_evento')}")
        print(f"   Multiplicador: {dados.get('multiplicador_manual')}")
        print(f"   Duracao: {dados.get('duracao_dias')}")

        manager = EventManager()
        evento_id = manager.cadastrar_evento(
            tipo=dados['tipo'],
            data_evento=dados['data_evento'],
            multiplicador_manual=dados.get('multiplicador_manual'),
            nome_custom=dados.get('nome_custom'),
            duracao_dias=dados.get('duracao_dias'),
            observacoes=dados.get('observacoes')
        )

        print(f"   [OK] Evento cadastrado com ID: {evento_id}")

        return jsonify({
            'success': True,
            'evento_id': evento_id,
            'mensagem': 'Evento cadastrado com sucesso'
        })

    except Exception as e:
        print(f"[ERRO] Erro ao cadastrar evento: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@app.route('/eventos/listar', methods=['GET'])
def listar_eventos():
    """Lista todos os eventos cadastrados"""
    try:
        from core.event_manager import EventManager

        manager = EventManager()
        eventos = manager.listar_eventos(apenas_ativos=False, apenas_futuros=False)

        # Converter para JSON manualmente para garantir compatibilidade
        import json
        eventos_serializaveis = []

        for evento in eventos:
            try:
                # Criar dict limpo apenas com campos necessários (SEM timestamps)
                # Função auxiliar para converter número de forma segura
                def safe_float(valor):
                    if valor is None or valor == '':
                        return None
                    try:
                        num = float(valor)
                        # Verificar se é NaN ou infinito
                        import math
                        if math.isnan(num) or math.isinf(num):
                            return None
                        return num
                    except (ValueError, TypeError):
                        return None

                evento_limpo = {
                    'id': int(evento.get('id', 0)),
                    'tipo': str(evento.get('tipo', '')),
                    'nome': str(evento.get('nome', '')),
                    'data_evento': str(evento.get('data_evento', '')),
                    'duracao_dias': int(evento.get('duracao_dias', 1)),
                    'multiplicador_manual': safe_float(evento.get('multiplicador_manual')),
                    'multiplicador_calculado': safe_float(evento.get('multiplicador_calculado')),
                    'usar_multiplicador_manual': bool(int(evento.get('usar_multiplicador_manual', 0))),
                    'ativo': bool(int(evento.get('ativo', 1))),
                    'observacoes': str(evento['observacoes']) if evento.get('observacoes') else None
                }
                eventos_serializaveis.append(evento_limpo)
            except Exception as e:
                print(f"[AVISO] Erro ao processar evento {evento.get('id')}: {e}")
                continue

        print(f"[EVENTOS] Listando {len(eventos_serializaveis)} eventos")

        # Testar serialização
        try:
            json.dumps(eventos_serializaveis)
        except Exception as e:
            print(f"[ERRO] Falha ao serializar: {e}")
            return jsonify({'success': False, 'erro': 'Erro ao serializar eventos'}), 500

        return jsonify({
            'success': True,
            'eventos': eventos_serializaveis
        })

    except Exception as e:
        print(f"[ERRO] Erro ao listar eventos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@app.route('/eventos/teste', methods=['GET'])
def teste_eventos():
    """Endpoint de teste simples"""
    return jsonify({
        'success': True,
        'mensagem': 'Teste OK',
        'eventos': [
            {'id': 1, 'nome': 'Teste', 'tipo': 'BLACK_FRIDAY', 'data_evento': '2026-11-01'}
        ]
    })


@app.route('/eventos/atualizar', methods=['POST'])
def atualizar_evento():
    """Atualiza multiplicador de um evento"""
    try:
        from core.event_manager import EventManager

        dados = request.get_json()
        evento_id = dados['evento_id']
        multiplicador = dados['multiplicador']

        manager = EventManager()
        manager.atualizar_multiplicador(evento_id, multiplicador)

        return jsonify({
            'success': True,
            'mensagem': 'Evento atualizado com sucesso'
        })

    except Exception as e:
        print(f"Erro ao atualizar evento: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@app.route('/eventos/desativar', methods=['POST'])
def desativar_evento():
    """Desativa um evento"""
    try:
        from core.event_manager import EventManager

        dados = request.get_json()
        evento_id = dados['evento_id']

        manager = EventManager()
        manager.desativar_evento(evento_id)

        return jsonify({
            'success': True,
            'mensagem': 'Evento desativado'
        })

    except Exception as e:
        print(f"Erro ao desativar evento: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@app.route('/eventos/reativar', methods=['POST'])
def reativar_evento():
    """Reativa um evento"""
    try:
        from core.event_manager import EventManager
        import sqlite3

        dados = request.get_json()
        evento_id = dados['evento_id']

        manager = EventManager()

        # Reativar manualmente via SQL
        conn = sqlite3.connect(manager.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE eventos
            SET ativo = 1, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (evento_id,))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'mensagem': 'Evento reativado'
        })

    except Exception as e:
        print(f"Erro ao reativar evento: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@app.route('/eventos/excluir', methods=['POST'])
def excluir_evento():
    """Exclui permanentemente um evento"""
    try:
        from core.event_manager import EventManager

        dados = request.get_json()
        evento_id = dados['evento_id']

        manager = EventManager()
        manager.excluir_evento(evento_id)

        return jsonify({
            'success': True,
            'mensagem': 'Evento excluído permanentemente'
        })

    except Exception as e:
        print(f"[ERRO] ao excluir evento: {e}")
        return jsonify({'success': False, 'erro': str(e)}), 500


@app.route('/reabastecimento')
def reabastecimento():
    """Página de reabastecimento"""
    return render_template('reabastecimento.html')


@app.route('/pedido_fornecedor')
def pedido_fornecedor():
    """Página de pedidos ao fornecedor"""
    return render_template('pedido_fornecedor.html')


@app.route('/pedido_cd')
def pedido_cd():
    """Página de pedidos CD → Lojas"""
    return render_template('pedido_cd.html')


@app.route('/transferencias')
def transferencias():
    """Página de transferências entre lojas"""
    return render_template('transferencias.html')


@app.route('/pedido_manual')
def pedido_manual():
    """Página de pedido manual simplificado"""
    return render_template('pedido_manual.html')


@app.route('/pedido_quantidade')
def pedido_quantidade():
    """Página de pedido por quantidade"""
    return render_template('pedido_quantidade.html')


@app.route('/pedido_cobertura')
def pedido_cobertura():
    """Página de pedido por cobertura"""
    return render_template('pedido_cobertura.html')


@app.route('/processar_pedido_quantidade', methods=['POST'])
def processar_pedido_quantidade():
    """
    Processa pedido por quantidade informada pelo usuário
    """
    try:
        from core.order_processor import OrderProcessor, gerar_relatorio_pedido
        from datetime import datetime

        if 'file' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'erro': 'Nenhum arquivo selecionado'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'erro': 'Arquivo deve ser Excel'}), 400

        # Salvar arquivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Carregar dados
        df_entrada = pd.read_excel(filepath)

        # Processar pedido
        df_resultado = OrderProcessor.processar_pedido_por_quantidade(
            df_entrada,
            validar_embalagem=True
        )

        # Gerar resumo
        resumo = gerar_relatorio_pedido(df_resultado, 'quantidade')

        # Salvar resultado
        nome_arquivo_saida = f"pedido_quantidade_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        caminho_saida = os.path.join(app.config['OUTPUT_FOLDER'], nome_arquivo_saida)

        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            df_resultado.to_excel(writer, sheet_name='Pedido', index=False)

            # Criar aba de resumo
            itens_ajustados = df_resultado[df_resultado['Foi_Ajustado'] == True]
            if len(itens_ajustados) > 0:
                itens_ajustados.to_excel(writer, sheet_name='Itens_Ajustados', index=False)

        # Limpar arquivo de upload
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


@app.route('/processar_pedido_cobertura', methods=['POST'])
def processar_pedido_cobertura():
    """
    Processa pedido por cobertura desejada informada pelo usuário
    """
    try:
        from core.order_processor import OrderProcessor, gerar_relatorio_pedido
        from datetime import datetime

        if 'file' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'erro': 'Nenhum arquivo selecionado'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'erro': 'Arquivo deve ser Excel'}), 400

        # Salvar arquivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Carregar dados
        df_entrada = pd.read_excel(filepath)

        # Processar pedido
        df_resultado = OrderProcessor.processar_pedido_por_cobertura(df_entrada)

        # Gerar resumo
        resumo = gerar_relatorio_pedido(df_resultado, 'cobertura')

        # Salvar resultado
        nome_arquivo_saida = f"pedido_cobertura_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        caminho_saida = os.path.join(app.config['OUTPUT_FOLDER'], nome_arquivo_saida)

        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            df_resultado.to_excel(writer, sheet_name='Pedido', index=False)

            # Criar aba de itens sem necessidade
            itens_sem_necessidade = df_resultado[df_resultado['Quantidade_Pedido'] == 0]
            if len(itens_sem_necessidade) > 0:
                itens_sem_necessidade.to_excel(writer, sheet_name='Sem_Necessidade', index=False)

            # Criar aba de itens ajustados
            itens_ajustados = df_resultado[df_resultado['Foi_Ajustado'] == True]
            if len(itens_ajustados) > 0:
                itens_ajustados.to_excel(writer, sheet_name='Itens_Ajustados', index=False)

        # Limpar arquivo de upload
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


@app.route('/api/carregar_dados_pedido', methods=['POST'])
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

        # Salvar arquivo temporário
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
        file.save(filepath)

        # Carregar Excel
        df = pd.read_excel(filepath)

        # Validar colunas mínimas necessárias
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

        # Calcular demanda diária
        if 'Demanda_Diaria' not in df.columns:
            df['Demanda_Diaria'] = df['Demanda_Media_Mensal'] / 30

        # Garantir que quantidade de pedido existe
        if 'Quantidade_Pedido' not in df.columns:
            df['Quantidade_Pedido'] = 0

        if 'Lote_Minimo' not in df.columns:
            df['Lote_Minimo'] = 1

        # Selecionar colunas relevantes
        colunas_retornar = [
            'Loja', 'SKU', 'Demanda_Diaria', 'Lead_Time_Dias',
            'Estoque_Disponivel', 'Ponto_Pedido', 'Quantidade_Pedido',
            'Lote_Minimo'
        ]

        # Adicionar colunas opcionais se existirem
        for col in ['Estoque_Transito', 'Pedidos_Abertos', 'Estoque_Seguranca']:
            if col in df.columns:
                colunas_retornar.append(col)

        df_resultado = df[colunas_retornar].copy()

        # Limpar arquivo temporário
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


@app.route('/api/buscar_item', methods=['POST'])
def buscar_item():
    """
    Busca item específico no último resultado processado (placeholder)
    """
    try:
        data = request.get_json()
        loja = data.get('loja')
        sku = data.get('sku')

        if not loja or not sku:
            return jsonify({'success': False, 'erro': 'Loja e SKU são obrigatórios'}), 400

        # TODO: Implementar busca em cache ou banco de dados
        # Por enquanto, retorna erro informativo
        return jsonify({
            'success': False,
            'erro': 'Carregue um arquivo Excel primeiro para buscar itens'
        }), 404

    except Exception as e:
        return jsonify({'success': False, 'erro': str(e)}), 500


@app.route('/processar_reabastecimento', methods=['POST'])
def processar_reabastecimento_route():
    """
    Processa cálculo de reabastecimento com modo automático ou manual
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
        modo_calculo = request.form.get('modo_calculo', 'automatico')
        nivel_servico = float(request.form.get('nivel_servico', 0.95))
        revisao_dias = int(request.form.get('revisao_dias', 7))

        # Salvar arquivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Carregar dados
        df_entrada = pd.read_excel(filepath)

        # MODO AUTOMÁTICO: Calcula demanda do histórico
        if modo_calculo == 'automatico':
            print("Modo AUTOMÁTICO: Calculando demanda do histórico...")

            # Validar colunas para modo automático
            colunas_obrigatorias_auto = [
                'Loja', 'SKU', 'Mes', 'Vendas',
                'Lead_Time_Dias', 'Estoque_Disponivel'
            ]
            colunas_faltantes = [col for col in colunas_obrigatorias_auto if col not in df_entrada.columns]

            if colunas_faltantes:
                return jsonify({
                    'success': False,
                    'erro': f'MODO AUTOMÁTICO requer colunas: {", ".join(colunas_faltantes)}'
                }), 400

            # Separar histórico de vendas e dados de estoque
            df_historico = df_entrada[['Loja', 'SKU', 'Mes', 'Vendas']].copy()

            # Pegar última linha de cada Loja+SKU para dados de estoque
            df_estoque = df_entrada.drop_duplicates(subset=['Loja', 'SKU'], keep='last')[
                ['Loja', 'SKU', 'Lead_Time_Dias', 'Estoque_Disponivel']
            ].copy()

            # Adicionar colunas opcionais se existirem
            if 'Estoque_Transito' in df_entrada.columns:
                df_estoque['Estoque_Transito'] = df_entrada.drop_duplicates(
                    subset=['Loja', 'SKU'], keep='last'
                )['Estoque_Transito']

            if 'Pedidos_Abertos' in df_entrada.columns:
                df_estoque['Pedidos_Abertos'] = df_entrada.drop_duplicates(
                    subset=['Loja', 'SKU'], keep='last'
                )['Pedidos_Abertos']

            if 'Lote_Minimo' in df_entrada.columns:
                df_estoque['Lote_Minimo'] = df_entrada.drop_duplicates(
                    subset=['Loja', 'SKU'], keep='last'
                )['Lote_Minimo']

            # Processar com cálculo inteligente de demanda
            from core.replenishment_calculator import processar_reabastecimento_com_historico

            df_resultado = processar_reabastecimento_com_historico(
                df_historico=df_historico,
                df_estoque_atual=df_estoque,
                metodo_demanda='auto',  # Sempre automático
                nivel_servico=nivel_servico,
                revisao_dias=revisao_dias
            )

        # MODO MANUAL: Usa demanda fornecida pelo usuário
        else:
            print("Modo MANUAL: Usando demanda fornecida pelo usuário...")

            # Validar colunas para modo manual
            colunas_obrigatorias_manual = [
                'Loja', 'SKU', 'Demanda_Media_Mensal', 'Desvio_Padrao_Mensal',
                'Lead_Time_Dias', 'Estoque_Disponivel'
            ]
            colunas_faltantes = [col for col in colunas_obrigatorias_manual if col not in df_entrada.columns]

            if colunas_faltantes:
                return jsonify({
                    'success': False,
                    'erro': f'MODO MANUAL requer colunas: {", ".join(colunas_faltantes)}'
                }), 400

            # Processar reabastecimento tradicional
            df_resultado = processar_reabastecimento(
                df_entrada,
                nivel_servico=nivel_servico,
                revisao_dias=revisao_dias
            )

        # Gerar resumo
        total_itens = len(df_resultado)
        total_a_pedir = len(df_resultado[df_resultado['Deve_Pedir'] == 'Sim'])
        total_em_risco = len(df_resultado[df_resultado['Risco_Ruptura'] == 'Sim'])
        cobertura_media = df_resultado['Cobertura_Atual_Dias'].mean()

        # Top 10 itens com maior urgência (menor cobertura e deve pedir)
        itens_urgentes = df_resultado[df_resultado['Deve_Pedir'] == 'Sim'].nsmallest(10, 'Cobertura_Atual_Dias')

        # Estatísticas de método usado (modo automático)
        resumo_metodos = {}
        if modo_calculo == 'automatico' and 'Metodo_Usado' in df_resultado.columns:
            metodos_count = df_resultado['Metodo_Usado'].value_counts().to_dict()
            resumo_metodos = {
                'metodos_usados': metodos_count,
                'modo': 'automatico'
            }
        else:
            resumo_metodos = {'modo': 'manual'}

        # Salvar resultado em Excel
        nome_arquivo_saida = f"reabastecimento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        caminho_saida = os.path.join(app.config['OUTPUT_FOLDER'], nome_arquivo_saida)

        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            df_resultado.to_excel(writer, sheet_name='Reabastecimento', index=False)
            itens_urgentes.to_excel(writer, sheet_name='Top_10_Urgentes', index=False)

            # Adicionar aba de resumo do método (modo automático)
            if modo_calculo == 'automatico' and 'Metodo_Usado' in df_resultado.columns:
                df_resumo_metodo = df_resultado.groupby('Metodo_Usado').size().reset_index(name='Quantidade')
                df_resumo_metodo.to_excel(writer, sheet_name='Resumo_Metodos', index=False)

        # Limpar arquivo de upload
        try:
            os.remove(filepath)
        except:
            pass

        resumo = {
            'total_itens': total_itens,
            'total_a_pedir': total_a_pedir,
            'total_em_risco': total_em_risco,
            'cobertura_media_dias': round(cobertura_media, 1),
            'percentual_a_pedir': round((total_a_pedir / total_itens * 100), 1) if total_itens > 0 else 0,
            'modo_calculo': modo_calculo,
            **resumo_metodos
        }

        return jsonify({
            'success': True,
            'arquivo_saida': nome_arquivo_saida,
            'resumo': resumo,
            'dados_tabela': df_resultado.to_dict('records'),
            'itens_urgentes': itens_urgentes.to_dict('records')
        })

    except ValueError as e:
        return jsonify({'success': False, 'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/processar_reabastecimento_v3', methods=['POST'])
def processar_reabastecimento_v3():
    """
    Processa reabastecimento com múltiplas abas (v3.0)
    - PEDIDOS_FORNECEDOR: Compras de fornecedor
    - PEDIDOS_CD: Distribuição CD → Loja
    - TRANSFERENCIAS: Transferências Loja ↔ Loja
    """
    try:
        from core.flow_processor import (
            processar_pedidos_fornecedor,
            processar_pedidos_cd,
            processar_transferencias,
            gerar_relatorio_pedido_fornecedor,
            gerar_relatorio_pedido_cd,
            gerar_relatorio_transferencias
        )

        # Verificar arquivo
        if 'file' not in request.files:
            return jsonify({'success': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'erro': 'Nenhum arquivo selecionado'}), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'erro': 'Arquivo deve ser Excel'}), 400

        # Salvar arquivo
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Ler abas disponíveis
        excel_file = pd.ExcelFile(filepath)
        abas_disponiveis = excel_file.sheet_names

        print(f"[INFO] Abas encontradas: {abas_disponiveis}")

        # Validar que tem pelo menos HISTORICO_VENDAS
        if 'HISTORICO_VENDAS' not in abas_disponiveis:
            return jsonify({
                'success': False,
                'erro': 'Arquivo deve conter aba HISTORICO_VENDAS'
            }), 400

        # Ler histórico (compartilhado por todos os fluxos)
        df_historico = pd.read_excel(filepath, sheet_name='HISTORICO_VENDAS')

        resultados = {}
        arquivos_gerados = []

        # 1. Processar PEDIDOS_FORNECEDOR (se existe)
        if 'PEDIDOS_FORNECEDOR' in abas_disponiveis:
            print("[INFO] Processando PEDIDOS_FORNECEDOR...")
            df_fornecedor = pd.read_excel(filepath, sheet_name='PEDIDOS_FORNECEDOR')

            resultado_fornecedor = processar_pedidos_fornecedor(df_fornecedor, df_historico)

            # Gerar relatório
            nome_arquivo = f"pedido_fornecedor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            caminho_saida = os.path.join(app.config['OUTPUT_FOLDER'], nome_arquivo)
            gerar_relatorio_pedido_fornecedor(resultado_fornecedor, caminho_saida)

            resultados['PEDIDOS_FORNECEDOR'] = {
                'resumo': {
                    'total_itens': int(resultado_fornecedor['total_itens']),
                    'total_a_pedir': int(len(resultado_fornecedor['pedidos'][resultado_fornecedor['pedidos']['Deve_Pedir'] == 'Sim'])) if 'pedidos' in resultado_fornecedor and len(resultado_fornecedor['pedidos']) > 0 else 0,
                    'custo_total': float(resultado_fornecedor['pedidos']['Custo_Total'].sum()) if 'pedidos' in resultado_fornecedor and len(resultado_fornecedor['pedidos']) > 0 and 'Custo_Total' in resultado_fornecedor['pedidos'].columns else 0.0,
                    'total_unidades': int(resultado_fornecedor['total_unidades']),
                    'total_caixas': int(resultado_fornecedor['total_caixas']),
                    'total_paletes': int(resultado_fornecedor['total_paletes']),
                    'total_carretas': int(resultado_fornecedor['total_carretas'])
                },
                'dados_tabela': resultado_fornecedor['pedidos'].replace([np.nan, np.inf, -np.inf], None).replace({pd.NA: None, pd.NaT: None}).to_dict('records') if 'pedidos' in resultado_fornecedor else []
            }
            arquivos_gerados.append(nome_arquivo)

        # 2. Processar PEDIDOS_CD (se existe)
        if 'PEDIDOS_CD' in abas_disponiveis:
            print("[INFO] Processando PEDIDOS_CD...")
            df_cd = pd.read_excel(filepath, sheet_name='PEDIDOS_CD')

            resultado_cd = processar_pedidos_cd(df_cd, df_historico)

            # Gerar relatório
            nome_arquivo = f"pedido_cd_lojas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            caminho_saida = os.path.join(app.config['OUTPUT_FOLDER'], nome_arquivo)
            gerar_relatorio_pedido_cd(resultado_cd, caminho_saida)

            resultados['PEDIDOS_CD'] = {
                'resumo': {
                    'total_itens': int(resultado_cd['total_itens']),
                    'total_a_pedir': int(len(resultado_cd['pedidos'][resultado_cd['pedidos']['Deve_Pedir'] == 'Sim'])) if 'pedidos' in resultado_cd and len(resultado_cd['pedidos']) > 0 else 0,
                    'total_em_risco': int(len(resultado_cd['pedidos'][resultado_cd['pedidos']['Risco_Ruptura'] == 'Sim'])) if 'pedidos' in resultado_cd and len(resultado_cd['pedidos']) > 0 else 0,
                    'cobertura_media_dias': float(resultado_cd['pedidos']['Cobertura_Dias_Apos_Pedido'].mean()) if 'pedidos' in resultado_cd and len(resultado_cd['pedidos']) > 0 and 'Cobertura_Dias_Apos_Pedido' in resultado_cd['pedidos'].columns else 0.0,
                    'total_unidades': int(resultado_cd['total_unidades']),
                    'alertas_count': int(resultado_cd['alertas_count'])
                },
                'dados_tabela': resultado_cd['pedidos'].replace([np.nan, np.inf, -np.inf], None).replace({pd.NA: None, pd.NaT: None}).to_dict('records') if 'pedidos' in resultado_cd else []
            }
            arquivos_gerados.append(nome_arquivo)

        # 3. Processar TRANSFERENCIAS (se existe)
        if 'TRANSFERENCIAS' in abas_disponiveis:
            print("[INFO] Processando TRANSFERENCIAS...")
            df_transf = pd.read_excel(filepath, sheet_name='TRANSFERENCIAS')

            resultado_transf = processar_transferencias(df_transf, df_historico)

            if resultado_transf['total_transferencias'] > 0:
                # Gerar relatório
                nome_arquivo = f"transferencias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                caminho_saida = os.path.join(app.config['OUTPUT_FOLDER'], nome_arquivo)
                gerar_relatorio_transferencias(resultado_transf, caminho_saida)

                resultados['TRANSFERENCIAS'] = {
                    'resumo': {
                        'total_transferencias': int(resultado_transf['total_transferencias']),
                        'total_a_pedir': int(resultado_transf['total_transferencias']),
                        'total_unidades': int(resultado_transf['total_unidades']),
                        'valor_total_estoque': float(resultado_transf['valor_total_estoque']),
                        'custo_operacional_total': float(resultado_transf['custo_operacional_total']),
                        'urgencia_alta': int(resultado_transf.get('alta_prioridade', 0))
                    },
                    'dados_tabela': resultado_transf['transferencias'].replace([np.nan, np.inf, -np.inf], None).replace({pd.NA: None, pd.NaT: None}).to_dict('records') if 'transferencias' in resultado_transf else []
                }
                arquivos_gerados.append(nome_arquivo)
            else:
                resultados['TRANSFERENCIAS'] = {
                    'resumo': {
                        'total_transferencias': 0,
                        'total_a_pedir': 0,
                        'total_unidades': 0,
                        'valor_total_estoque': 0.0,
                        'custo_operacional_total': 0.0,
                        'urgencia_alta': 0
                    },
                    'dados_tabela': []
                }

        # Limpar arquivo de upload
        try:
            os.remove(filepath)
        except:
            pass

        # Verificar se processou alguma aba
        if not resultados:
            return jsonify({
                'success': False,
                'erro': 'Nenhuma aba de fluxo encontrada (PEDIDOS_FORNECEDOR, PEDIDOS_CD ou TRANSFERENCIAS)'
            }), 400

        return jsonify({
            'success': True,
            'resultados': resultados,
            'arquivos_gerados': arquivos_gerados,
            'total_arquivos': len(arquivos_gerados)
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'erro': f'Erro interno: {str(e)}'}), 500


# ===== ROTAS DE KPIs =====
@app.route('/kpis')
def kpis():
    """Página de KPIs"""
    return render_template('kpis.html')


@app.route('/api/kpis/filtros', methods=['GET'])
def kpis_filtros():
    """Retorna opções para filtros de KPIs"""
    try:
        # TODO: Buscar do banco de dados ou cache
        # Por enquanto, retornar dados mockados
        filtros = {
            'lojas': [
                {'id': 1, 'nome': 'Loja 1'},
                {'id': 2, 'nome': 'Loja 2'},
                {'id': 3, 'nome': 'Loja 3'}
            ],
            'produtos': [
                {'id': 1001, 'nome': 'Produto A'},
                {'id': 1002, 'nome': 'Produto B'},
                {'id': 1003, 'nome': 'Produto C'}
            ],
            'categorias': [
                'Alimentos',
                'Bebidas',
                'Limpeza',
                'Higiene'
            ],
            'fornecedores': [
                'Fornecedor 1',
                'Fornecedor 2',
                'Fornecedor 3'
            ]
        }
        return jsonify(filtros)
    except Exception as e:
        print(f"Erro ao buscar filtros: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/api/kpis/dados', methods=['GET'])
def kpis_dados():
    """Retorna dados de KPIs com base nos filtros"""
    try:
        visao = request.args.get('visao', 'mensal')
        loja = request.args.get('loja', '')
        produto = request.args.get('produto', '')
        categoria = request.args.get('categoria', '')
        fornecedor = request.args.get('fornecedor', '')

        # TODO: Buscar dados reais do banco/cache baseado nos filtros
        # Por enquanto, retornar dados mockados

        import random
        from datetime import datetime, timedelta

        # Gerar dados mockados para demonstração
        if visao == 'mensal':
            # Últimos 12 meses
            meses = []
            data_base = datetime.now()
            for i in range(12, 0, -1):
                mes = data_base - timedelta(days=i*30)
                meses.append(mes.strftime('%b/%y'))

            wmape_mensal = [{'mes': m, 'wmape': random.uniform(5, 15)} for m in meses]
            bias_mensal = [{'mes': m, 'bias': random.uniform(-2, 2)} for m in meses]
            ruptura_mensal = [{'mes': m, 'taxa_ruptura': random.uniform(2, 8)} for m in meses]
            cobertura_mensal = [{'mes': m, 'cobertura_media': random.uniform(15, 25)} for m in meses]
            servico_mensal = [{'mes': m, 'nivel_servico': random.uniform(92, 98)} for m in meses]

            classificacao = []
            for m in meses:
                classificacao.append({
                    'mes': m,
                    'excelente': random.randint(50, 80),
                    'bom': random.randint(30, 50),
                    'aceitavel': random.randint(10, 30),
                    'fraca': random.randint(5, 15)
                })

        else:  # semanal
            # Últimas 26 semanas
            semanas = []
            data_base = datetime.now()
            for i in range(26, 0, -1):
                semana = data_base - timedelta(days=i*7)
                semanas.append(semana.strftime('S%V/%y'))

            wmape_mensal = [{'semana': s, 'wmape': random.uniform(5, 15)} for s in semanas]
            bias_mensal = [{'semana': s, 'bias': random.uniform(-2, 2)} for s in semanas]
            ruptura_mensal = [{'semana': s, 'taxa_ruptura': random.uniform(2, 8)} for s in semanas]
            cobertura_mensal = [{'semana': s, 'cobertura_media': random.uniform(15, 25)} for s in semanas]
            classificacao = []
            servico_mensal = []

        # Métricas atuais (últimos 30 dias)
        metricas_atuais = {
            'wmape': random.uniform(8, 12),
            'bias': random.uniform(-1.5, 1.5),
            'previsoes_excelentes': random.randint(120, 180),
            'total_skus': 245,
            'taxa_ruptura': random.uniform(3, 7),
            'cobertura_media': random.uniform(18, 22),
            'nivel_servico': random.uniform(93, 97),
            'skus_criticos': random.randint(5, 15),

            # Tendências
            'wmape_tendencia': {'tipo': 'down', 'valor': '2.3%'},
            'bias_tendencia': {'tipo': 'stable', 'valor': '0.1%'},
            'excelentes_tendencia': {'tipo': 'up', 'valor': '5.2%'},
            'ruptura_tendencia': {'tipo': 'down', 'valor': '1.2%'},
            'cobertura_tendencia': {'tipo': 'up', 'valor': '0.5 dias'},
            'servico_tendencia': {'tipo': 'up', 'valor': '2.1%'},
            'criticos_tendencia': {'tipo': 'down', 'valor': '3 SKUs'}
        }

        # Top/Bottom Performers
        performers = [
            {
                'sku': '1001',
                'descricao': 'Produto A - Amostra',
                'loja': 'Loja 1',
                'wmape': 5.2,
                'bias': 0.3,
                'taxa_ruptura': 1.5,
                'cobertura': 22.5
            },
            {
                'sku': '1002',
                'descricao': 'Produto B - Amostra',
                'loja': 'Loja 2',
                'wmape': 8.7,
                'bias': -0.8,
                'taxa_ruptura': 3.2,
                'cobertura': 19.3
            },
            {
                'sku': '1003',
                'descricao': 'Produto C - Amostra',
                'loja': 'Loja 1',
                'wmape': 25.4,
                'bias': 5.2,
                'taxa_ruptura': 18.7,
                'cobertura': 8.2
            },
            {
                'sku': '1004',
                'descricao': 'Produto D - Amostra',
                'loja': 'Loja 3',
                'wmape': 12.3,
                'bias': -2.1,
                'taxa_ruptura': 5.8,
                'cobertura': 15.7
            }
        ]

        resultado = {
            'metricas_atuais': metricas_atuais,
            'series_temporais': {
                'wmape_mensal' if visao == 'mensal' else 'wmape_semanal': wmape_mensal,
                'bias_mensal' if visao == 'mensal' else 'bias_semanal': bias_mensal,
                'classificacao': classificacao if visao == 'mensal' else [],
                'ruptura_mensal' if visao == 'mensal' else 'ruptura_semanal': ruptura_mensal,
                'cobertura_mensal' if visao == 'mensal' else 'cobertura_semanal': cobertura_mensal,
                'servico_mensal': servico_mensal if visao == 'mensal' else []
            },
            'performers': performers
        }

        return jsonify(resultado)

    except Exception as e:
        print(f"Erro ao buscar dados de KPIs: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


# ==============================================================================
# ROTAS DE API - INTEGRAÇÃO COM BANCO DE DADOS
# ==============================================================================

import psycopg2
from psycopg2.extras import RealDictCursor

# Configuração do banco
DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

def get_db_connection():
    """Cria conexão com o banco PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)


@app.route('/visualizacao')
def visualizacao_demanda():
    """Página de visualização de demanda com dados reais"""
    return render_template('visualizacao_demanda.html')


@app.route('/api/lojas', methods=['GET'])
def api_lojas():
    """Retorna lista de lojas do banco"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT cod_empresa, nome_loja, regiao, tipo
            FROM cadastro_lojas
            WHERE ativo = TRUE
            ORDER BY nome_loja
        """)

        lojas = cursor.fetchall()
        cursor.close()
        conn.close()

        # Adicionar opção "Todas"
        resultado = [{'cod_empresa': 'TODAS', 'nome_loja': 'TODAS - Todas as Lojas (Agregado)', 'regiao': None, 'tipo': None}]
        resultado.extend(lojas)

        return jsonify(resultado)

    except Exception as e:
        print(f"Erro ao buscar lojas: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/api/categorias', methods=['GET'])
def api_categorias():
    """Retorna lista de categorias do banco"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT categoria
            FROM cadastro_produtos
            WHERE categoria IS NOT NULL AND ativo = TRUE
            ORDER BY categoria
        """)

        categorias = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        # Adicionar opção "Todas"
        resultado = ['TODAS - Todas as Categorias']
        resultado.extend(categorias)

        return jsonify(resultado)

    except Exception as e:
        print(f"Erro ao buscar categorias: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/api/produtos', methods=['GET'])
def api_produtos():
    """Retorna lista de produtos do banco (com filtros opcionais)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Parâmetros de filtro
        loja = request.args.get('loja', 'TODAS')
        categoria = request.args.get('categoria', 'TODAS')

        # Query base
        query = """
            SELECT DISTINCT p.codigo, p.descricao, p.categoria, p.subcategoria, p.curva_abc
            FROM cadastro_produtos p
            WHERE p.ativo = TRUE
        """

        params = []

        # Filtrar por categoria
        if categoria and categoria != 'TODAS' and not categoria.startswith('TODAS -'):
            query += " AND p.categoria = %s"
            params.append(categoria)

        # Se filtrar por loja específica, mostrar só produtos com vendas nessa loja
        if loja and loja != 'TODAS':
            query += """
                AND EXISTS (
                    SELECT 1 FROM historico_vendas_diario h
                    WHERE h.codigo = p.codigo AND h.cod_empresa = %s
                )
            """
            params.append(int(loja))

        query += " ORDER BY p.descricao LIMIT 200"

        cursor.execute(query, params)
        produtos = cursor.fetchall()
        cursor.close()
        conn.close()

        # Adicionar opção "Todos"
        resultado = [{'codigo': 'TODOS', 'descricao': 'TODOS - Todos os Produtos (Agregado)', 'categoria': None, 'subcategoria': None, 'curva_abc': None}]
        resultado.extend(produtos)

        return jsonify(resultado)

    except Exception as e:
        print(f"Erro ao buscar produtos: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route('/api/vendas', methods=['GET'])
def api_vendas():
    """Retorna dados de vendas históricos"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Parâmetros
        loja = request.args.get('loja', 'TODAS')
        produto = request.args.get('produto', 'TODOS')
        categoria = request.args.get('categoria', 'TODAS')
        meses = int(request.args.get('meses', 12))

        # Query base
        query = """
            SELECT
                DATE_TRUNC('day', h.data) as data,
                SUM(h.qtd_venda) as qtd_venda,
                SUM(h.valor_venda) as valor_venda,
                COUNT(DISTINCT h.cod_empresa) as num_lojas,
                COUNT(DISTINCT h.codigo) as num_produtos
            FROM historico_vendas_diario h
        """

        # Joins se necessário
        if categoria and categoria != 'TODAS' and not categoria.startswith('TODAS -'):
            query += " JOIN cadastro_produtos p ON h.codigo = p.codigo"

        query += " WHERE h.data >= CURRENT_DATE - INTERVAL '%s months'"
        params = [meses]

        # Filtros
        if loja and loja != 'TODAS':
            query += " AND h.cod_empresa = %s"
            params.append(int(loja))

        if produto and produto != 'TODOS':
            query += " AND h.codigo = %s"
            params.append(int(produto))

        if categoria and categoria != 'TODAS' and not categoria.startswith('TODAS -'):
            query += " AND p.categoria = %s"
            params.append(categoria)

        query += """
            GROUP BY DATE_TRUNC('day', h.data)
            ORDER BY data
        """

        cursor.execute(query, params)
        vendas = cursor.fetchall()
        cursor.close()
        conn.close()

        # Converter para formato JSON-friendly
        resultado = []
        for row in vendas:
            resultado.append({
                'data': row['data'].strftime('%Y-%m-%d'),
                'qtd_venda': float(row['qtd_venda']),
                'valor_venda': float(row['valor_venda']) if row['valor_venda'] else 0,
                'num_lojas': row['num_lojas'],
                'num_produtos': row['num_produtos']
            })

        return jsonify(resultado)

    except Exception as e:
        print(f"Erro ao buscar vendas: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500


@app.route('/api/gerar_previsao_banco', methods=['POST'])
def api_gerar_previsao_banco():
    """
    Gera previsão de demanda usando dados do banco PostgreSQL
    Aceita período customizado baseado na granularidade:
    - Mensal: mes_inicio, ano_inicio, mes_fim, ano_fim
    - Semanal: semana_inicio, ano_semana_inicio, semana_fim, ano_semana_fim
    - Diário: data_inicio, data_fim
    """
    try:
        # Inicializar auto-logger para auditoria
        logger = get_auto_logger()

        dados = request.get_json()

        loja = dados.get('loja', '')
        categoria = dados.get('categoria', '')
        produto = dados.get('produto', '')
        granularidade = dados.get('granularidade', 'mensal')

        # Extrair parâmetros de período customizado
        tipo_periodo = dados.get('tipo_periodo', None)

        # Variáveis para armazenar período de previsão (calculado depois)
        periodo_inicio_customizado = None
        periodo_fim_customizado = None

        if tipo_periodo == 'mensal':
            mes_inicio = int(dados.get('mes_inicio', 1))
            ano_inicio = int(dados.get('ano_inicio', 2026))
            mes_fim = int(dados.get('mes_fim', 3))
            ano_fim = int(dados.get('ano_fim', 2026))
            periodo_inicio_customizado = pd.Timestamp(year=ano_inicio, month=mes_inicio, day=1)
            from calendar import monthrange
            ultimo_dia = monthrange(ano_fim, mes_fim)[1]
            periodo_fim_customizado = pd.Timestamp(year=ano_fim, month=mes_fim, day=ultimo_dia)
            print(f"\nPeríodo customizado MENSAL: {mes_inicio:02d}/{ano_inicio} até {mes_fim:02d}/{ano_fim}", flush=True)

        elif tipo_periodo == 'semanal':
            semana_inicio = int(dados.get('semana_inicio', 1))
            ano_semana_inicio = int(dados.get('ano_semana_inicio', 2026))
            semana_fim = int(dados.get('semana_fim', 12))
            ano_semana_fim = int(dados.get('ano_semana_fim', 2026))
            # Converter semana/ano para data
            from datetime import datetime, timedelta
            # Semana 1 = primeira segunda-feira do ano ou 1 de janeiro
            periodo_inicio_customizado = pd.Timestamp(datetime.strptime(f'{ano_semana_inicio}-W{semana_inicio:02d}-1', '%G-W%V-%u'))
            periodo_fim_customizado = pd.Timestamp(datetime.strptime(f'{ano_semana_fim}-W{semana_fim:02d}-7', '%G-W%V-%u'))
            print(f"\nPeríodo customizado SEMANAL: Semana {semana_inicio}/{ano_semana_inicio} até Semana {semana_fim}/{ano_semana_fim}", flush=True)

        elif tipo_periodo == 'diario':
            data_inicio_str = dados.get('data_inicio', '')
            data_fim_str = dados.get('data_fim', '')
            if data_inicio_str and data_fim_str:
                periodo_inicio_customizado = pd.Timestamp(data_inicio_str)
                periodo_fim_customizado = pd.Timestamp(data_fim_str)
                print(f"\nPeríodo customizado DIÁRIO: {data_inicio_str} até {data_fim_str}", flush=True)

        # Fallback para meses_previsao se não houver período customizado
        meses_previsao = int(dados.get('meses_previsao', 3))

        # Normalizar filtros ANTES de fazer prints (remover emojis e prefixos)
        # Se categoria começa com "TODAS -", considerar como TODAS
        if categoria and categoria.startswith('TODAS'):
            categoria = 'TODAS'

        # Se produto começa com "TODOS" ou tem emoji, considerar como TODOS
        if produto and (produto.startswith('TODOS') or '📦' in produto):
            produto = 'TODOS'

        # Se loja começa com "TODAS" ou tem emoji, considerar como TODAS
        if loja and (loja.startswith('TODAS') or '📊' in loja):
            loja = 'TODAS'

        print(f"\n=== Gerando Previsao do Banco ===")
        print(f"Loja: {loja}")
        print(f"Categoria: {categoria}")
        print(f"Produto: {produto}")
        print(f"Granularidade: {granularidade}")
        print(f"Tipo período recebido: {tipo_periodo}")
        if periodo_inicio_customizado and periodo_fim_customizado:
            print(f"Período CUSTOMIZADO: {periodo_inicio_customizado.strftime('%Y-%m-%d')} até {periodo_fim_customizado.strftime('%Y-%m-%d')}")
        else:
            print(f"Meses Previsao (fallback): {meses_previsao}")

        # NOTA: O cálculo exato de períodos será feito APÓS obter a última data do histórico
        # para garantir que o período de previsão corresponda exatamente aos meses solicitados
        # A variável periodos_previsao será calculada mais adiante no código
        periodos_previsao_aproximado = meses_previsao  # valor temporário, será recalculado

        print(f"Período de previsao solicitado", flush=True)

        # Conectar ao banco
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construir query baseada nos filtros
        where_clauses = []
        params = []

        # Filtro de loja (se não for TODAS)
        if loja and loja != 'TODAS' and not loja.startswith('TODAS'):
            where_clauses.append("h.cod_empresa = %s")
            params.append(loja)

        # Filtro de categoria (se não for TODAS)
        if categoria and categoria != 'TODAS' and not categoria.startswith('TODAS'):
            where_clauses.append("p.categoria = %s")
            params.append(categoria)

        # Filtro de produto (se não for TODOS)
        if produto and produto != 'TODOS' and not produto.startswith('TODOS'):
            where_clauses.append("h.codigo = %s")
            params.append(produto)

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        # Query para buscar dados históricos baseado na granularidade
        # IMPORTANTE: Usar DATE_TRUNC('month', ...) para garantir que começamos no primeiro dia do mês
        # Isso garante meses completos e proporção correta entre meses e semanas
        # Exemplo: Se hoje é 2026-01-09, o boundary será 2024-01-01 (não 2024-01-09)
        if granularidade == 'diario':
            query = f"""
                SELECT
                    h.data,
                    SUM(h.qtd_venda) as qtd_venda,
                    SUM(h.valor_venda) as valor_venda
                FROM historico_vendas_diario h
                JOIN cadastro_produtos p ON h.codigo = p.codigo
                WHERE h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
                {where_sql}
                GROUP BY h.data
                ORDER BY h.data
            """
        elif granularidade == 'semanal':
            # Para semanal, agrupar por semana usando EXATAMENTE os mesmos dias do período
            # IMPORTANTE: Não filtrar semanas, apenas agrupar os dias que já foram filtrados
            # Isso garante que mensal e semanal somem EXATAMENTE os mesmos dias
            query = f"""
                WITH dados_diarios AS (
                    SELECT
                        h.data,
                        SUM(h.qtd_venda) as qtd_venda,
                        SUM(h.valor_venda) as valor_venda
                    FROM historico_vendas_diario h
                    JOIN cadastro_produtos p ON h.codigo = p.codigo
                    WHERE h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
                    {where_sql}
                    GROUP BY h.data
                )
                SELECT
                    DATE_TRUNC('week', data)::date as data,
                    SUM(qtd_venda) as qtd_venda,
                    SUM(valor_venda) as valor_venda
                FROM dados_diarios
                GROUP BY DATE_TRUNC('week', data)
                ORDER BY DATE_TRUNC('week', data)
            """
        else:  # mensal
            query = f"""
                SELECT
                    DATE_TRUNC('month', h.data) as data,
                    SUM(h.qtd_venda) as qtd_venda,
                    SUM(h.valor_venda) as valor_venda
                FROM historico_vendas_diario h
                JOIN cadastro_produtos p ON h.codigo = p.codigo
                WHERE h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
                {where_sql}
                GROUP BY DATE_TRUNC('month', h.data)
                ORDER BY DATE_TRUNC('month', h.data)
            """

        cursor.execute(query, params)
        dados_historicos = cursor.fetchall()

        # Log do total de dados históricos base
        if dados_historicos:
            total_historico_base = sum(float(d['qtd_venda']) for d in dados_historicos)
            print(f"Total dados históricos (últimos 2 anos): {total_historico_base:,.2f} em {len(dados_historicos)} períodos", flush=True)

        # Buscar dados do mesmo período do ano anterior para comparação
        print(f"Buscando dados do ano anterior para comparação...", flush=True)

        # Primeiro, precisamos processar dados históricos para calcular o período
        if dados_historicos and len(dados_historicos) >= 3:
            # Criar DataFrame temporário para obter datas
            df_temp = pd.DataFrame(dados_historicos)
            df_temp['data'] = pd.to_datetime(df_temp['data'])
            df_temp.set_index('data', inplace=True)
            df_temp.sort_index(inplace=True)

            # Calcular período correspondente do ano anterior
            # IMPORTANTE: Se período customizado foi fornecido, usar ele para buscar ano anterior
            # Isso garante que a comparação na tabela seja coerente com o período de previsão
            if periodo_inicio_customizado and periodo_fim_customizado:
                # Usar período de previsão customizado para buscar ano anterior correspondente
                inicio_periodo_previsao = periodo_inicio_customizado
                fim_periodo_previsao = periodo_fim_customizado
                print(f"  Usando período customizado para ano anterior: {inicio_periodo_previsao.strftime('%Y-%m-%d')} até {fim_periodo_previsao.strftime('%Y-%m-%d')}", flush=True)

                # CORREÇÃO PARA SEMANAL: Usar EXATAMENTE as mesmas semanas ISO do ano anterior
                # Exemplo: Semana 1-13/2026 -> Semana 1-13/2025
                # Isso garante que o número de períodos seja igual e a comparação seja justa
                if granularidade == 'semanal' and tipo_periodo == 'semanal':
                    from datetime import datetime as dt

                    # Obter os parâmetros originais de semana
                    semana_inicio_param = int(dados.get('semana_inicio', 1))
                    ano_semana_inicio_param = int(dados.get('ano_semana_inicio', 2026))
                    semana_fim_param = int(dados.get('semana_fim', 13))
                    ano_semana_fim_param = int(dados.get('ano_semana_fim', 2026))

                    # Ano anterior
                    ano_inicio_ant = ano_semana_inicio_param - 1
                    ano_fim_ant = ano_semana_fim_param - 1

                    # Converter semana ISO para data: mesmas semanas, ano anterior
                    # Semana X do ano Y-1
                    inicio_ano_anterior = pd.Timestamp(dt.strptime(f'{ano_inicio_ant}-W{semana_inicio_param:02d}-1', '%G-W%V-%u'))
                    fim_ano_anterior = pd.Timestamp(dt.strptime(f'{ano_fim_ant}-W{semana_fim_param:02d}-7', '%G-W%V-%u'))
                    print(f"  Semanal: Semanas {semana_inicio_param}-{semana_fim_param}/{ano_semana_inicio_param} -> Semanas {semana_inicio_param}-{semana_fim_param}/{ano_inicio_ant}", flush=True)
                else:
                    # Para mensal e diário, subtrair 1 ano normalmente
                    inicio_ano_anterior = inicio_periodo_previsao - pd.DateOffset(years=1)
                    fim_ano_anterior = fim_periodo_previsao - pd.DateOffset(years=1)
            else:
                # CORREÇÃO: Calcular o período de PREVISÃO (não histórico) para buscar ano anterior
                # O ano anterior deve corresponder aos mesmos períodos que serão previstos
                ultima_data_hist = df_temp.index[-1]

                if granularidade == 'semanal':
                    # Para semanal sem período customizado:
                    # A previsão começa na semana seguinte ao último histórico
                    # Buscar ano anterior: mesmas semanas do ano Y-1
                    from datetime import datetime as dt

                    # Data de início da previsão: semana seguinte ao último histórico
                    inicio_previsao = ultima_data_hist + pd.Timedelta(weeks=1)
                    # Data fim: calcular baseado em meses_previsao
                    mes_destino_calc = ultima_data_hist.month + meses_previsao
                    ano_destino_calc = ultima_data_hist.year
                    while mes_destino_calc > 12:
                        mes_destino_calc -= 12
                        ano_destino_calc += 1
                    from calendar import monthrange
                    ultimo_dia = monthrange(ano_destino_calc, mes_destino_calc)[1]
                    fim_previsao = pd.Timestamp(year=ano_destino_calc, month=mes_destino_calc, day=ultimo_dia)

                    # Semanas do período de previsão
                    semana_inicio = inicio_previsao.isocalendar()[1]
                    ano_semana_inicio = inicio_previsao.isocalendar()[0]
                    semana_fim = fim_previsao.isocalendar()[1]
                    ano_semana_fim = fim_previsao.isocalendar()[0]

                    # Ano anterior: mesmas semanas ISO, ano -1
                    ano_inicio_ant = ano_semana_inicio - 1
                    ano_fim_ant = ano_semana_fim - 1

                    # Tratar caso especial: semana 53 pode não existir em alguns anos
                    # Nesse caso, limitar à semana 52 ou usar a última disponível
                    semana_fim_ajustada = semana_fim
                    if semana_fim == 53:
                        # Verificar se o ano anterior tem semana 53
                        try:
                            dt.strptime(f'{ano_fim_ant}-W53-1', '%G-W%V-%u')
                        except ValueError:
                            # Ano anterior não tem semana 53, usar semana 52
                            semana_fim_ajustada = 52
                            print(f"  Nota: Semana 53 não existe em {ano_fim_ant}, usando S52", flush=True)

                    try:
                        # IMPORTANTE: Começar 1 semana ANTES para garantir que temos todas as semanas necessárias
                        # Isso cobre casos onde a semana incompleta no histórico desloca o início da previsão
                        semana_busca_inicio = semana_inicio - 1 if semana_inicio > 1 else 52
                        ano_busca_inicio = ano_inicio_ant if semana_inicio > 1 else ano_inicio_ant - 1

                        inicio_ano_anterior = pd.Timestamp(dt.strptime(f'{ano_busca_inicio}-W{semana_busca_inicio:02d}-1', '%G-W%V-%u'))
                        fim_ano_anterior = pd.Timestamp(dt.strptime(f'{ano_fim_ant}-W{semana_fim_ajustada:02d}-7', '%G-W%V-%u'))
                        print(f"  Semanal (auto): Previsão S{semana_inicio}-S{semana_fim}/{ano_semana_inicio} -> Busca S{semana_busca_inicio}-S{semana_fim_ajustada}/{ano_busca_inicio}-{ano_fim_ant}", flush=True)
                    except ValueError as e:
                        # Se ainda assim não funcionar, usar DateOffset
                        inicio_ano_anterior = inicio_previsao - pd.DateOffset(years=1)
                        fim_ano_anterior = fim_previsao - pd.DateOffset(years=1)
                        print(f"  Semanal (fallback): usando DateOffset ({e})", flush=True)
                else:
                    # Para mensal e diário: usar o PERÍODO DE PREVISÃO, não o histórico
                    # Calcular período de previsão baseado em ultima_data_hist e meses_previsao
                    inicio_previsao = ultima_data_hist + pd.Timedelta(days=1)

                    mes_destino_calc = ultima_data_hist.month + meses_previsao
                    ano_destino_calc = ultima_data_hist.year
                    while mes_destino_calc > 12:
                        mes_destino_calc -= 12
                        ano_destino_calc += 1
                    from calendar import monthrange
                    ultimo_dia = monthrange(ano_destino_calc, mes_destino_calc)[1]
                    fim_previsao = pd.Timestamp(year=ano_destino_calc, month=mes_destino_calc, day=ultimo_dia)

                    inicio_ano_anterior = inicio_previsao - pd.DateOffset(years=1)
                    fim_ano_anterior = fim_previsao - pd.DateOffset(years=1)
                    print(f"  {granularidade.capitalize()} (auto): {inicio_previsao.strftime('%Y-%m-%d')} a {fim_previsao.strftime('%Y-%m-%d')} -> {inicio_ano_anterior.strftime('%Y-%m-%d')} a {fim_ano_anterior.strftime('%Y-%m-%d')}", flush=True)

            print(f"  Buscando ano anterior: {inicio_ano_anterior.strftime('%Y-%m-%d')} até {fim_ano_anterior.strftime('%Y-%m-%d')}", flush=True)

            # Buscar dados do ano anterior (mesmos filtros, exceto as datas)
            # params contém os filtros, mas não inclui as datas inicialmente
            # Todas as granularidades: [inicio, fim, ...filtros]
            params_ano_anterior = [
                inicio_ano_anterior.strftime('%Y-%m-%d'),
                fim_ano_anterior.strftime('%Y-%m-%d')
            ] + params

            if granularidade == 'mensal':
                query_ano_anterior = f"""
                    SELECT
                        DATE_TRUNC('month', h.data) as data,
                        SUM(h.qtd_venda) as qtd_venda
                    FROM historico_vendas_diario h
                    JOIN cadastro_produtos p ON h.codigo = p.codigo
                    WHERE h.data >= %s
                      AND h.data <= %s
                      {where_sql}
                    GROUP BY DATE_TRUNC('month', h.data)
                    ORDER BY DATE_TRUNC('month', h.data)
                """
            elif granularidade == 'semanal':
                # Mesma lógica do query principal: agrupar EXATAMENTE os mesmos dias
                query_ano_anterior = f"""
                    WITH dados_diarios AS (
                        SELECT
                            h.data,
                            SUM(h.qtd_venda) as qtd_venda
                        FROM historico_vendas_diario h
                        JOIN cadastro_produtos p ON h.codigo = p.codigo
                        WHERE h.data >= %s
                          AND h.data <= %s
                          {where_sql}
                        GROUP BY h.data
                    )
                    SELECT
                        DATE_TRUNC('week', data)::date as data,
                        SUM(qtd_venda) as qtd_venda
                    FROM dados_diarios
                    GROUP BY DATE_TRUNC('week', data)
                    ORDER BY DATE_TRUNC('week', data)
                """
            else:  # diario
                query_ano_anterior = f"""
                    SELECT
                        h.data,
                        SUM(h.qtd_venda) as qtd_venda
                    FROM historico_vendas_diario h
                    JOIN cadastro_produtos p ON h.codigo = p.codigo
                    WHERE h.data >= %s
                      AND h.data <= %s
                      {where_sql}
                    GROUP BY h.data
                    ORDER BY h.data
                """

            cursor.execute(query_ano_anterior, params_ano_anterior)
            dados_ano_anterior = cursor.fetchall()

            # Processar dados do ano anterior - INCLUIR DATAS
            ano_anterior_datas = [d['data'].strftime('%Y-%m-%d') for d in dados_ano_anterior] if dados_ano_anterior else []
            ano_anterior_valores = [float(d['qtd_venda']) for d in dados_ano_anterior] if dados_ano_anterior else []
            ano_anterior_total = sum(ano_anterior_valores) if ano_anterior_valores else 0

            print(f"Dados ano anterior: {len(ano_anterior_valores)} períodos, total: {ano_anterior_total}", flush=True)
            if ano_anterior_datas:
                print(f"  Período ano anterior: {ano_anterior_datas[0]} até {ano_anterior_datas[-1]}", flush=True)
        else:
            ano_anterior_datas = []
            ano_anterior_valores = []
            ano_anterior_total = 0

        # Fechar conexão
        cursor.close()
        conn.close()

        # Verificar se há dados suficientes (mínimo 3 períodos)
        if not dados_historicos or len(dados_historicos) < 3:
            return jsonify({
                'erro': f'Dados insuficientes para gerar previsão. Encontrados {len(dados_historicos) if dados_historicos else 0} períodos, necessário pelo menos 3 períodos de histórico.',
                'detalhes': {
                    'periodos_encontrados': len(dados_historicos) if dados_historicos else 0,
                    'filtros': {
                        'loja': loja,
                        'categoria': categoria,
                        'produto': produto,
                        'granularidade': granularidade
                    }
                }
            }), 400

        # Converter para DataFrame do pandas
        df = pd.DataFrame(dados_historicos)
        df['data'] = pd.to_datetime(df['data'])
        # Converter qtd_venda para float (pode vir como Decimal do PostgreSQL)
        df['qtd_venda'] = df['qtd_venda'].astype(float)
        df = df.sort_values('data')

        # Preparar série temporal
        df.set_index('data', inplace=True)
        serie_temporal_completa = df['qtd_venda'].tolist()
        datas_completas = df.index.tolist()

        # CALCULAR PERÍODOS DE PREVISÃO
        # Agora suporta período CUSTOMIZADO informado pelo usuário
        from dateutil.relativedelta import relativedelta
        from calendar import monthrange

        ultima_data_historico = datas_completas[-1]

        # Se período customizado foi fornecido, usar diretamente
        if periodo_inicio_customizado and periodo_fim_customizado:
            data_inicio_previsao = periodo_inicio_customizado
            data_fim_previsao = periodo_fim_customizado

            # Para mensal, extrair mês/ano início e destino
            primeiro_mes_previsao = data_inicio_previsao.month
            ano_primeiro_mes = data_inicio_previsao.year
            mes_destino = data_fim_previsao.month
            ano_destino = data_fim_previsao.year

            print(f"Periodo de previsao CUSTOMIZADO:", flush=True)
            print(f"  Data inicio: {data_inicio_previsao.strftime('%Y-%m-%d')}", flush=True)
            print(f"  Data fim: {data_fim_previsao.strftime('%Y-%m-%d')}", flush=True)
        else:
            # LÓGICA ORIGINAL baseada em meses_previsao
            # Primeiro mês de previsão = mês onde a previsão começa
            primeiro_mes_previsao = ultima_data_historico.month
            ano_primeiro_mes = ultima_data_historico.year

            # O MÊS DESTINO é o primeiro mês + (meses_previsao - 1)
            mes_destino = primeiro_mes_previsao + (meses_previsao - 1)
            ano_destino = ano_primeiro_mes
            while mes_destino > 12:
                mes_destino -= 12
                ano_destino += 1

            # Data fim é o ÚLTIMO DIA do mês de destino
            ultimo_dia_mes_destino = monthrange(ano_destino, mes_destino)[1]
            data_fim_previsao = pd.Timestamp(year=ano_destino, month=mes_destino, day=ultimo_dia_mes_destino)

            print(f"Periodo de previsao alvo:", flush=True)
            print(f"  Ultima data historico: {ultima_data_historico.strftime('%Y-%m-%d')}", flush=True)
            print(f"  Primeiro mes previsao: {primeiro_mes_previsao:02d}/{ano_primeiro_mes}", flush=True)
            print(f"  Mes alvo (destino): {mes_destino:02d}/{ano_destino}", flush=True)
            print(f"  Data fim previsao: {data_fim_previsao.strftime('%Y-%m-%d')}", flush=True)

        # Usar pd.date_range para calcular o número EXATO de períodos
        # Isso garante consistência com a geração de datas futuras
        if granularidade == 'diario':
            # Para diário: usar data_inicio_previsao se customizado, senão dia seguinte ao histórico
            if periodo_inicio_customizado:
                start_date = periodo_inicio_customizado
            else:
                start_date = ultima_data_historico + pd.Timedelta(days=1)

            datas_previsao_temp = pd.date_range(
                start=start_date,
                end=data_fim_previsao,
                freq='D'
            )
            periodos_previsao = len(datas_previsao_temp)

        elif granularidade == 'semanal':
            # Para semanal: usar data_inicio_previsao se customizado
            if periodo_inicio_customizado:
                start_date = periodo_inicio_customizado
            else:
                start_date = ultima_data_historico + pd.Timedelta(weeks=1)

            datas_previsao_temp = pd.date_range(
                start=start_date,
                end=data_fim_previsao,
                freq='W-MON'
            )
            periodos_previsao = len(datas_previsao_temp)

        else:  # mensal
            # Para mensal: usar período customizado ou calcular baseado em meses_previsao
            if periodo_inicio_customizado:
                # Período customizado: usar EXATAMENTE o mês/ano que o usuário solicitou
                # primeiro_mes_previsao = mês de início informado pelo usuário
                # ano_primeiro_mes = ano de início informado pelo usuário
                data_inicio_temp = pd.Timestamp(year=ano_primeiro_mes, month=primeiro_mes_previsao, day=1)
                data_fim_temp = pd.Timestamp(year=ano_destino, month=mes_destino, day=1)
                print(f"  Mensal customizado: {primeiro_mes_previsao:02d}/{ano_primeiro_mes} até {mes_destino:02d}/{ano_destino}", flush=True)
            else:
                # Original: primeiro período é o mês SEGUINTE ao último histórico
                mes_inicio_mensal = primeiro_mes_previsao + 1
                ano_inicio_mensal = ano_primeiro_mes
                if mes_inicio_mensal > 12:
                    mes_inicio_mensal = 1
                    ano_inicio_mensal += 1

                data_inicio_temp = pd.Timestamp(year=ano_inicio_mensal, month=mes_inicio_mensal, day=1)
                data_fim_temp = pd.Timestamp(year=ano_destino, month=mes_destino, day=1)

            datas_previsao_temp = pd.date_range(
                start=data_inicio_temp,
                end=data_fim_temp,
                freq='MS'
            )
            periodos_previsao = len(datas_previsao_temp)

        print(f"  Periodos de previsao: {periodos_previsao} ({granularidade})", flush=True)

        # Validar série temporal antes do processamento
        print(f"\nValidando serie temporal...", flush=True)
        validacao = validate_series(
            serie_temporal_completa,
            min_length=3,
            allow_zeros=True,
            check_outliers=False  # Outliers serão tratados separadamente
        )

        if not validacao['valid']:
            return jsonify({
                'erro': 'Dados inválidos para previsão',
                'codigo_erro': validacao.get('errors', [{}])[0].get('code', 'ERR000'),
                'mensagem': validacao.get('errors', [{}])[0].get('message', 'Erro desconhecido'),
                'detalhes': validacao.get('statistics', {})
            }), 400

        print(f"  Validacao OK - {len(serie_temporal_completa)} periodos", flush=True)

        # Log detalhado da série temporal completa
        total_serie_completa = sum(serie_temporal_completa)
        media_serie_completa = total_serie_completa / len(serie_temporal_completa)
        print(f"  Total da série completa: {total_serie_completa:,.2f}", flush=True)
        print(f"  Média por período: {media_serie_completa:,.2f}", flush=True)

        # Dividir dados: 50% base histórica, 25% teste, 25% previsão
        total_periodos = len(serie_temporal_completa)
        print(f"\nTotal de periodos historicos: {total_periodos}", flush=True)

        # Calcular tamanhos - Divisão 50/25/25
        tamanho_base = int(total_periodos * 0.50)
        tamanho_teste = int(total_periodos * 0.25)
        # Usar os períodos restantes para validação futura (comparação YoY)
        # O meses_previsao será usado para prever ALÉM dos dados históricos
        tamanho_validacao_futura = total_periodos - tamanho_base - tamanho_teste

        # Ajustar se necessário para garantir que base + teste <= total
        if tamanho_base + tamanho_teste > total_periodos:
            tamanho_teste = total_periodos - tamanho_base

        print(f"Divisao dos dados (50/25/25):", flush=True)
        print(f"  - Base historica: {tamanho_base} periodos (50%)", flush=True)
        print(f"  - Teste/validacao: {tamanho_teste} periodos (25%)", flush=True)
        print(f"  - Validacao futura (YoY): {tamanho_validacao_futura} periodos (25%)", flush=True)
        print(f"  - Previsao para alem dos dados: {periodos_previsao} periodos", flush=True)

        # IMPORTANTE: Guardar série ORIGINAL para mostrar histórico real ao usuário
        # Outliers só devem ser removidos para CÁLCULO da previsão, não para mostrar dados históricos
        serie_temporal_original = serie_temporal_completa.copy()
        datas_completas_original = datas_completas.copy()

        # Dividir os dados ORIGINAIS (para mostrar ao usuário no gráfico)
        serie_base_original = serie_temporal_original[:tamanho_base]
        serie_teste_original = serie_temporal_original[tamanho_base:tamanho_base + tamanho_teste]

        # IMPORTANTE: Preservar datas ORIGINAIS para exibição ao usuário
        # Estas NÃO devem ser afetadas pela remoção de outliers
        datas_base_original = datas_completas_original[:tamanho_base]
        datas_teste_original = datas_completas_original[tamanho_base:tamanho_base + tamanho_teste]

        # Datas para cálculo (podem ser alteradas se outliers forem removidos)
        datas_base = datas_completas_original[:tamanho_base]
        datas_teste = datas_completas_original[tamanho_base:tamanho_base + tamanho_teste]

        # Calcular índices sazonais para melhorar previsão
        print(f"\nCalculando indices sazonais...", flush=True)
        serie_completa_array = np.array(serie_temporal_completa)

        # Usar módulo robusto de detecção de outliers (IQR ao invés de Z-Score)
        resultado_outliers = auto_clean_outliers(serie_completa_array)
        serie_temporal_completa_limpa = resultado_outliers['cleaned_data']  # Série LIMPA para previsão

        if resultado_outliers['outliers_count'] > 0:
            print(f"  Outliers detectados: {resultado_outliers['outliers_count']}", flush=True)
            print(f"  Método usado: {resultado_outliers['method_used']}", flush=True)
            print(f"  Tratamento: {resultado_outliers['treatment']}", flush=True)
            print(f"  Razão: {resultado_outliers['reason']}", flush=True)
            print(f"  Confiança: {resultado_outliers['confidence']:.2f}", flush=True)

        # Usar série LIMPA para cálculo de previsão
        # NOTA: Se outliers foram REMOVIDOS, a série limpa é mais curta!
        # Precisamos recalcular os tamanhos de base/teste E ajustar as datas
        if resultado_outliers['treatment'] == 'REMOVE' and resultado_outliers['outliers_count'] > 0:
            total_periodos_limpo = len(serie_temporal_completa_limpa)
            tamanho_base_limpo = int(total_periodos_limpo * 0.50)
            tamanho_teste_limpo = int(total_periodos_limpo * 0.25)

            serie_base = serie_temporal_completa_limpa[:tamanho_base_limpo]
            serie_teste = serie_temporal_completa_limpa[tamanho_base_limpo:tamanho_base_limpo + tamanho_teste_limpo]

            # CRÍTICO: Atualizar tamanho_teste para usar o valor limpo
            # Isso garante que modelo.predict() gere o mesmo número de previsões que serie_teste
            tamanho_teste = tamanho_teste_limpo

            # Usar série limpa para cálculos
            serie_temporal_completa = serie_temporal_completa_limpa

            # CRÍTICO: Remover as datas correspondentes aos outliers removidos
            # para manter alinhamento entre datas e valores
            outlier_indices_set = set(resultado_outliers['outliers_detected'])  # Converter para set para lookup rápido
            datas_completas_limpas = [datas_completas_original[i] for i in range(len(datas_completas_original)) if i not in outlier_indices_set]
            datas_completas = datas_completas_limpas

            # Também atualizar datas_base para o loop de ajuste sazonal
            datas_base = datas_completas[:tamanho_base_limpo]

            print(f"  Série ajustada após remoção: {total_periodos_limpo} períodos (era {total_periodos})", flush=True)
            print(f"  Datas ajustadas: {len(datas_completas)} datas (removidos {len(outlier_indices_set)} outliers)", flush=True)
        else:
            # Se substituiu ou não removeu, série tem mesmo tamanho
            serie_temporal_completa = serie_temporal_completa_limpa
            serie_base = serie_temporal_completa[:tamanho_base]
            serie_teste = serie_temporal_completa[tamanho_base:tamanho_base + tamanho_teste]

        # Detectar sazonalidade automaticamente com validação estatística
        print(f"\nDetectando sazonalidade automaticamente...", flush=True)
        resultado_sazonalidade = detect_seasonality(serie_temporal_completa)

        tem_sazonalidade = resultado_sazonalidade['has_seasonality']
        periodo_sazonal = resultado_sazonalidade['seasonal_period']
        forca_sazonal = resultado_sazonalidade['strength']

        print(f"  Sazonalidade detectada: {tem_sazonalidade}", flush=True)
        if tem_sazonalidade:
            print(f"  Período sazonal: {periodo_sazonal}", flush=True)
            print(f"  Força: {forca_sazonal:.2f}", flush=True)
            print(f"  Razão: {resultado_sazonalidade['reason']}", flush=True)
        else:
            print(f"  Razão: {resultado_sazonalidade['reason']}", flush=True)

        # Calcular fatores sazonais com base na GRANULARIDADE, não apenas na detecção automática
        # Isso garante que previsões mensais tenham variação mês a mês mesmo quando a detecção
        # estatística não encontra padrão significativo
        fatores_sazonais = {}

        if granularidade == 'mensal' and len(serie_temporal_completa) >= 12:
            # Calcular fatores sazonais mensais usando TODOS os dados históricos limpos
            # Usar o tamanho mínimo entre datas e série para evitar index out of range
            indices_sazonais = {}
            tamanho_para_sazonalidade = min(len(datas_completas), len(serie_temporal_completa))
            for i in range(tamanho_para_sazonalidade):
                mes = datas_completas[i].month
                if mes not in indices_sazonais:
                    indices_sazonais[mes] = []
                indices_sazonais[mes].append(serie_temporal_completa[i])

            media_geral = np.mean(serie_temporal_completa)
            for mes, valores in indices_sazonais.items():
                fatores_sazonais[mes] = np.mean(valores) / media_geral

            print(f"  Fatores sazonais mensais calculados: {len(fatores_sazonais)} meses", flush=True)
            print(f"  Valores dos fatores mensais: {dict(sorted(fatores_sazonais.items()))}", flush=True)

        elif granularidade == 'semanal' and len(serie_temporal_completa) >= 52:
            # Calcular fatores sazonais semanais usando SEMANA DO ANO (1-52)
            # Assim como mensal usa 12 meses, semanal deve usar 52 semanas para capturar sazonalidade anual
            # Exemplo: Semana 50 da previsão é influenciada pela média histórica das semanas 50
            indices_sazonais = {}
            tamanho_para_sazonalidade = min(len(datas_completas), len(serie_temporal_completa))

            for i in range(tamanho_para_sazonalidade):
                # Usar número da semana no ano (1-52/53)
                semana_ano = datas_completas[i].isocalendar()[1]  # Semana ISO do ano (1-52)

                if semana_ano not in indices_sazonais:
                    indices_sazonais[semana_ano] = []
                indices_sazonais[semana_ano].append(serie_temporal_completa[i])

            media_geral = np.mean(serie_temporal_completa)
            for semana, valores in indices_sazonais.items():
                fatores_sazonais[semana] = np.mean(valores) / media_geral

            print(f"  Fatores sazonais semanais calculados: {len(fatores_sazonais)} semanas do ano", flush=True)
            print(f"  Valores dos fatores semanais: Min={min(fatores_sazonais.values()):.3f}, Max={max(fatores_sazonais.values()):.3f}, Amplitude={(max(fatores_sazonais.values())-min(fatores_sazonais.values()))*100:.2f}%", flush=True)

        elif granularidade == 'diario' and len(serie_temporal_completa) >= 7:
            # Calcular fatores sazonais diários (dia da semana)
            indices_sazonais = {}
            tamanho_para_sazonalidade = min(len(datas_completas), len(serie_temporal_completa))
            for i in range(tamanho_para_sazonalidade):
                dia_semana = datas_completas[i].weekday()  # 0=segunda, 6=domingo
                if dia_semana not in indices_sazonais:
                    indices_sazonais[dia_semana] = []
                indices_sazonais[dia_semana].append(serie_temporal_completa[i])

            media_geral = np.mean(serie_temporal_completa)
            for dia, valores in indices_sazonais.items():
                fatores_sazonais[dia] = np.mean(valores) / media_geral

            print(f"  Fatores sazonais diários calculados: {len(fatores_sazonais)} dias da semana", flush=True)
        else:
            print(f"  Sem ajuste sazonal (dados insuficientes para granularidade {granularidade})", flush=True)

        # Aplicar todos os 6 modelos principais de previsão da ferramenta
        modelos_testar = [
            'Média Móvel Simples',
            'Média Móvel Ponderada',
            'Suavização Exponencial Simples',
            'Holt',
            'Holt-Winters',
            'Regressão Linear'
        ]

        resultados_modelos = {}
        metricas = {}
        melhor_modelo = None
        melhor_wmape = float('inf')

        print(f"\nTreinando e testando modelos...", flush=True)

        for nome_modelo in modelos_testar:
            try:
                print(f"Aplicando modelo: {nome_modelo}", flush=True)
                modelo = get_modelo(nome_modelo)

                # Treinar com dados base
                modelo.fit(serie_base)

                # Prever para o período de teste
                previsoes_teste_base = modelo.predict(tamanho_teste)

                # APLICAR AJUSTE SAZONAL nas previsões de teste baseado na GRANULARIDADE
                if fatores_sazonais:
                    previsoes_teste = []
                    # A última data da base é datas_base[-1]
                    ultima_data_base = datas_base[-1]

                    for i in range(tamanho_teste):
                        # Calcular a chave sazonal com base na granularidade
                        if granularidade == 'mensal':
                            # Para mensal, usar o número do mês (1-12)
                            # CORREÇÃO: O primeiro período de teste é o mês SEGUINTE ao último da base
                            mes_previsao = ((ultima_data_base.month + i) % 12) + 1
                            chave_sazonal = mes_previsao
                        elif granularidade == 'semanal':
                            # Para semanal, usar SEMANA DO ANO (1-52)
                            from datetime import timedelta
                            data_previsao = ultima_data_base + timedelta(weeks=i)
                            semana_ano = data_previsao.isocalendar()[1]  # 1-52/53
                            chave_sazonal = semana_ano  # Usar semana do ano diretamente
                        elif granularidade == 'diario':
                            # Para diário, usar dia da semana (0-6)
                            # CORREÇÃO: Usar i+1 porque o primeiro período de teste é o dia SEGUINTE à última data base
                            from datetime import timedelta
                            data_previsao = ultima_data_base + timedelta(days=i+1)
                            chave_sazonal = data_previsao.weekday()
                        else:
                            chave_sazonal = None

                        # Aplicar fator sazonal
                        fator = fatores_sazonais.get(chave_sazonal, 1.0)
                        valor_ajustado = previsoes_teste_base[i] * fator
                        previsoes_teste.append(valor_ajustado)
                else:
                    previsoes_teste = previsoes_teste_base

                # Calcular métricas no período de teste
                if len(previsoes_teste) == len(serie_teste):
                    erros_absolutos = []
                    erros_percentuais = []
                    erros_reais = []

                    for i in range(len(serie_teste)):
                        real = serie_teste[i]
                        previsto = previsoes_teste[i]

                        if real > 0:
                            erro_abs = abs(previsto - real)
                            erro_perc = (erro_abs / real) * 100
                            erro_real = previsto - real

                            erros_absolutos.append(erro_abs)
                            erros_percentuais.append(erro_perc)
                            erros_reais.append(erro_real)

                    if len(erros_percentuais) > 0:
                        wmape = sum(erros_percentuais) / len(erros_percentuais)
                        bias = (sum(erros_reais) / sum(serie_teste)) * 100 if sum(serie_teste) > 0 else 0
                        mae = sum(erros_absolutos) / len(erros_absolutos)

                        metricas[nome_modelo] = {
                            'wmape': wmape,
                            'bias': bias,
                            'mae': mae
                        }

                        print(f"  OK {nome_modelo}: WMAPE={wmape:.2f}%, BIAS={bias:.2f}%, MAE={mae:.2f}", flush=True)

                        if wmape < melhor_wmape:
                            melhor_wmape = wmape
                            melhor_modelo = nome_modelo
                    else:
                        metricas[nome_modelo] = {'wmape': 0.0, 'bias': 0.0, 'mae': 0.0}
                        print(f"  ! {nome_modelo}: Sem erros calculados", flush=True)
                else:
                    metricas[nome_modelo] = {'wmape': 0.0, 'bias': 0.0, 'mae': 0.0}
                    print(f"  ! {nome_modelo}: Tamanho incompatível (previsto={len(previsoes_teste)}, esperado={len(serie_teste)})", flush=True)

                # Agora treinar com TODOS os dados (base + teste) para fazer previsão futura
                modelo.fit(serie_temporal_completa)
                # Prever para o número de períodos solicitado pelo usuário
                previsoes_futuro_base = modelo.predict(periodos_previsao)

                # Log da previsão base (antes do ajuste sazonal)
                total_base = sum(previsoes_futuro_base)
                media_base = total_base / len(previsoes_futuro_base)
                print(f"    Previsão base (sem ajuste): Total={total_base:,.2f}, Média={media_base:,.2f}", flush=True)

                # APLICAR AJUSTE SAZONAL nas previsões futuras baseado na GRANULARIDADE
                if fatores_sazonais:
                    # Aplicar fatores sazonais nas previsões futuras
                    previsoes_futuro = []
                    # IMPORTANTE: Usar ultima_data_historico (data original antes de remoção de outliers)
                    # para garantir alinhamento com as datas de previsão geradas
                    ultima_data = ultima_data_historico

                    for i in range(periodos_previsao):
                        # Calcular a chave sazonal com base na granularidade
                        if granularidade == 'mensal':
                            # Para mensal, usar o número do mês (1-12)
                            # CORREÇÃO: O primeiro período de previsão é o mês SEGUINTE ao último histórico
                            # Por isso usamos (ultima_data.month + i + 1) ao invés de (ultima_data.month + i)
                            mes_previsao = ((ultima_data.month + i) % 12) + 1
                            chave_sazonal = mes_previsao
                        elif granularidade == 'semanal':
                            # Para semanal, usar SEMANA DO ANO (1-52)
                            from datetime import timedelta
                            data_previsao = ultima_data + timedelta(weeks=i)
                            semana_ano = data_previsao.isocalendar()[1]  # 1-52/53
                            chave_sazonal = semana_ano  # Usar semana do ano diretamente
                        elif granularidade == 'diario':
                            # Para diário, usar dia da semana (0-6)
                            # CORREÇÃO: Usar i+1 porque o primeiro período de previsão é o dia SEGUINTE ao último histórico
                            from datetime import timedelta
                            data_previsao = ultima_data + timedelta(days=i+1)
                            chave_sazonal = data_previsao.weekday()
                        else:
                            chave_sazonal = None

                        # Aplicar fator sazonal
                        fator = fatores_sazonais.get(chave_sazonal, 1.0)
                        valor_ajustado = previsoes_futuro_base[i] * fator
                        previsoes_futuro.append(valor_ajustado)

                    if tem_sazonalidade:
                        print(f"    Ajuste sazonal aplicado (força: {forca_sazonal:.2f}, var: {min(fatores_sazonais.values()):.3f} - {max(fatores_sazonais.values()):.3f})", flush=True)
                    else:
                        print(f"    Ajuste sazonal aplicado baseado em padrões históricos (var: {min(fatores_sazonais.values()):.3f} - {max(fatores_sazonais.values()):.3f})", flush=True)
                else:
                    previsoes_futuro = previsoes_futuro_base
                    print(f"    Sem ajuste sazonal (dados insuficientes)", flush=True)

                resultados_modelos[nome_modelo] = {
                    'previsao_teste': previsoes_teste[:len(serie_teste)],
                    'previsao_futuro': previsoes_futuro
                }

                # Log detalhado do total previsto
                total_previsto = sum(previsoes_futuro)
                print(f"    Total previsto para {periodos_previsao} períodos: {total_previsto:,.2f}", flush=True)

            except Exception as e:
                print(f"  ERRO ao aplicar modelo {nome_modelo}: {e}", flush=True)
                import traceback
                print(traceback.format_exc(), flush=True)
                continue

        # Se nenhum modelo funcionou, usar fallback
        if not resultados_modelos or melhor_modelo is None:
            print("Nenhum modelo funcionou, usando fallback...", flush=True)
            modelo = get_modelo('Média Móvel Simples')
            modelo.fit(serie_base)
            previsoes_teste_base = modelo.predict(tamanho_teste)
            modelo.fit(serie_temporal_completa)
            previsoes_futuro_base = modelo.predict(periodos_previsao)

            # IMPORTANTE: Aplicar fatores sazonais também no fallback!
            if fatores_sazonais:
                # Aplicar sazonalidade nas previsões de TESTE
                previsoes_teste = []
                # Data inicial do período de teste
                data_inicio_teste = datas_base[-1] if len(datas_base) > 0 else datas_completas[tamanho_base - 1]

                for i in range(len(previsoes_teste_base)):
                    if granularidade == 'mensal':
                        # CORREÇÃO: O primeiro período de teste é o mês SEGUINTE ao último da base
                        mes_teste = ((data_inicio_teste.month + i) % 12) + 1
                        chave_sazonal = mes_teste
                    elif granularidade == 'semanal':
                        semana_base = data_inicio_teste.isocalendar()[1]
                        semana_teste = ((semana_base + i - 1) % 52) + 1
                        chave_sazonal = semana_teste
                    elif granularidade == 'diario':
                        # CORREÇÃO: Usar i+1 porque o primeiro período de teste é o dia SEGUINTE à data_inicio_teste
                        from datetime import timedelta
                        data_previsao = data_inicio_teste + timedelta(days=i+1)
                        chave_sazonal = data_previsao.weekday()
                    else:
                        chave_sazonal = None

                    fator = fatores_sazonais.get(chave_sazonal, 1.0)
                    valor_ajustado = previsoes_teste_base[i] * fator
                    previsoes_teste.append(valor_ajustado)

                # Aplicar sazonalidade nas previsões FUTURAS
                previsoes_futuro = []
                # IMPORTANTE: Usar ultima_data_historico (data original antes de remoção de outliers)
                # para garantir alinhamento com as datas de previsão geradas
                ultima_data = ultima_data_historico

                for i in range(len(previsoes_futuro_base)):
                    if granularidade == 'mensal':
                        # CORREÇÃO: O primeiro período de previsão é o mês SEGUINTE ao último histórico
                        mes_futuro = ((ultima_data.month + i) % 12) + 1
                        chave_sazonal = mes_futuro
                    elif granularidade == 'semanal':
                        semana_base = ultima_data.isocalendar()[1]
                        semana_futuro = ((semana_base + i - 1) % 52) + 1
                        chave_sazonal = semana_futuro
                    elif granularidade == 'diario':
                        # CORREÇÃO: Usar i+1 porque o primeiro período de previsão é o dia SEGUINTE ao último histórico
                        from datetime import timedelta
                        data_previsao = ultima_data + timedelta(days=i+1)
                        chave_sazonal = data_previsao.weekday()
                    else:
                        chave_sazonal = None

                    fator = fatores_sazonais.get(chave_sazonal, 1.0)
                    valor_ajustado = previsoes_futuro_base[i] * fator
                    previsoes_futuro.append(valor_ajustado)

                print(f"  Fallback com ajuste sazonal aplicado (var: {min(fatores_sazonais.values()):.3f} - {max(fatores_sazonais.values()):.3f})", flush=True)
            else:
                previsoes_teste = previsoes_teste_base
                previsoes_futuro = previsoes_futuro_base
                print(f"  Fallback sem ajuste sazonal (dados insuficientes)", flush=True)

            resultados_modelos = {
                'Média Móvel Simples': {
                    'previsao_teste': previsoes_teste,
                    'previsao_futuro': previsoes_futuro
                }
            }

            # Calcular métricas WMAPE e BIAS para o fallback
            wmape_fallback = 0
            bias_fallback = 0
            mae_fallback = 0

            if len(previsoes_teste) > 0 and len(serie_teste) > 0:
                erros_absolutos = []
                erros_percentuais = []
                erros_reais = []

                tamanho_comparacao = min(len(previsoes_teste), len(serie_teste))
                for i in range(tamanho_comparacao):
                    real = serie_teste[i]
                    previsto = previsoes_teste[i]

                    if real > 0:
                        erro_abs = abs(previsto - real)
                        erro_perc = (erro_abs / real) * 100
                        erro_real = previsto - real

                        erros_absolutos.append(erro_abs)
                        erros_percentuais.append(erro_perc)
                        erros_reais.append(erro_real)

                if len(erros_percentuais) > 0:
                    wmape_fallback = sum(erros_percentuais) / len(erros_percentuais)
                    soma_reais = sum(serie_teste[:tamanho_comparacao])
                    bias_fallback = (sum(erros_reais) / soma_reais) * 100 if soma_reais > 0 else 0
                    mae_fallback = sum(erros_absolutos) / len(erros_absolutos)

                print(f"  Fallback métricas: WMAPE={wmape_fallback:.2f}%, BIAS={bias_fallback:.2f}%", flush=True)

            metricas = {'Média Móvel Simples': {'wmape': wmape_fallback, 'bias': bias_fallback, 'mae': mae_fallback}}
            melhor_modelo = 'Média Móvel Simples'
            melhor_wmape = wmape_fallback

        print(f"\nMelhor modelo: {melhor_modelo}", flush=True)

        # Registrar seleção do modelo no auto-logger para auditoria
        if melhor_modelo and melhor_modelo in metricas:
            # Extrair características da série temporal
            caracteristicas = {
                'tamanho': total_periodos,
                'media': float(np.mean(serie_temporal_completa)),
                'desvio_padrao': float(np.std(serie_temporal_completa)),
                'coef_variacao': float(np.std(serie_temporal_completa) / np.mean(serie_temporal_completa)),
                'sazonalidade': tem_sazonalidade,
                'periodo_sazonal': periodo_sazonal if tem_sazonalidade else None,
                'forca_sazonal': forca_sazonal if tem_sazonalidade else 0.0,
                'outliers_detectados': resultado_outliers.get('outliers_count', 0),
                'metodo_outlier': resultado_outliers.get('method_used', 'none')
            }

            logger.log_selection(
                metodo_selecionado=melhor_modelo,
                confianca=1.0 - (melhor_wmape / 100.0) if melhor_wmape < 100 else 0.0,  # Converter WMAPE em confiança
                razao=f"Menor WMAPE: {melhor_wmape:.2f}%",
                caracteristicas=caracteristicas,
                sku=produto if produto != 'TODOS' else None,
                loja=loja if loja != 'TODAS' else None,
                horizonte=meses_previsao,
                sucesso=True
            )
            print(f"  Seleção registrada no auto-logger", flush=True)

        # Preparar resposta com 3 séries de dados
        # IMPORTANTE: Usar série ORIGINAL para mostrar histórico ao usuário
        # Outliers só devem ser removidos para CÁLCULO da previsão, não para exibição
        resposta = {
            'sucesso': True,
            'melhor_modelo': melhor_modelo,
            'metricas': metricas,
            'modelos': {},
            'granularidade': granularidade,  # Adicionar granularidade para formatação de labels
            'historico_base': {
                'datas': [d.strftime('%Y-%m-%d') for d in datas_base_original],  # Usar datas ORIGINAIS
                'valores': serie_base_original  # Usar série ORIGINAL (sem remoção de outliers)
            },
            'historico_teste': {
                'datas': [d.strftime('%Y-%m-%d') for d in datas_teste_original],  # Usar datas ORIGINAIS
                'valores': serie_teste_original  # Usar série ORIGINAL (sem remoção de outliers)
            },
            'ano_anterior': {
                'datas': ano_anterior_datas,
                'valores': ano_anterior_valores,
                'total': ano_anterior_total
            }
        }

        # IMPORTANTE: Para granularidade semanal, realinhar dados do ano anterior
        # para corresponder às mesmas semanas ISO das previsões
        # Isso será feito após gerar as datas futuras da primeira previsão

        # Adicionar previsões de cada modelo
        metricas_futuro = {}

        # Verificar se há dados para gerar datas futuras
        if len(datas_completas) == 0:
            return jsonify({'erro': 'Não há dados históricos suficientes para gerar previsão'}), 400

        for nome_modelo, resultado in resultados_modelos.items():
            # Gerar datas futuras baseado na granularidade e no período solicitado
            # Suporta período customizado quando fornecido pelo usuário
            ultima_data = datas_completas[-1]

            if granularidade == 'diario':
                # Para diário: usar período customizado ou calcular baseado no histórico
                if periodo_inicio_customizado:
                    start_date = periodo_inicio_customizado
                else:
                    start_date = ultima_data + pd.Timedelta(days=1)

                datas_futuras = pd.date_range(
                    start=start_date,
                    end=data_fim_previsao,
                    freq='D'
                )
            elif granularidade == 'semanal':
                # Para semanal: usar período customizado ou calcular baseado no histórico
                if periodo_inicio_customizado:
                    start_date = periodo_inicio_customizado
                else:
                    start_date = ultima_data + pd.Timedelta(weeks=1)

                datas_futuras = pd.date_range(
                    start=start_date,
                    end=data_fim_previsao,
                    freq='W-MON'  # Semanas começando na segunda-feira
                )
            else:  # mensal
                # Para mensal: usar período customizado ou calcular baseado no histórico
                if periodo_inicio_customizado:
                    data_inicio_mensal = pd.Timestamp(year=ano_primeiro_mes, month=primeiro_mes_previsao, day=1)
                    data_fim_mensal = pd.Timestamp(year=ano_destino, month=mes_destino, day=1)
                else:
                    # Original: primeiro período é o mês SEGUINTE ao último histórico
                    mes_inicio_mensal = primeiro_mes_previsao + 1
                    ano_inicio_mensal = ano_primeiro_mes
                    if mes_inicio_mensal > 12:
                        mes_inicio_mensal = 1
                        ano_inicio_mensal += 1

                    data_inicio_mensal = pd.Timestamp(year=ano_inicio_mensal, month=mes_inicio_mensal, day=1)
                    data_fim_mensal = pd.Timestamp(year=ano_destino, month=mes_destino, day=1)

                datas_futuras = pd.date_range(
                    start=data_inicio_mensal,
                    end=data_fim_mensal,
                    freq='MS'
                )

            # Ajustar periodos_previsao para corresponder às datas geradas
            periodos_previsao_efetivo = len(datas_futuras)

            # REALINHAMENTO DO ANO ANTERIOR para corresponder às datas futuras
            # Isso é especialmente importante para granularidade semanal onde
            # a mesma semana ISO pode cair em datas diferentes em anos diferentes
            if granularidade == 'semanal' and len(ano_anterior_datas) > 0 and len(datas_futuras) > 0:
                # Criar dicionário de valores do ano anterior indexado por (ano_iso, semana_iso)
                # Isso evita que dados de anos diferentes se sobrescrevam
                ano_anterior_por_semana = {}
                for i, data_str in enumerate(ano_anterior_datas):
                    if data_str is None:
                        continue
                    data_ant = pd.Timestamp(data_str)
                    if pd.isna(data_ant):
                        continue
                    ano_iso = data_ant.isocalendar()[0]
                    semana_iso = data_ant.isocalendar()[1]
                    # Usar tupla (ano, semana) como chave
                    chave = (ano_iso, semana_iso)
                    ano_anterior_por_semana[chave] = {
                        'data': data_str,
                        'valor': ano_anterior_valores[i]
                    }

                # Realinhar para corresponder às datas futuras
                ano_anterior_datas_realinhado = []
                ano_anterior_valores_realinhado = []

                for data_futura in datas_futuras[:periodos_previsao_efetivo]:
                    ano_futura = data_futura.isocalendar()[0]
                    semana_futura = data_futura.isocalendar()[1]
                    # Buscar pelo ano anterior (ano da previsão - 1) e mesma semana
                    ano_busca = ano_futura - 1
                    chave_busca = (ano_busca, semana_futura)

                    if chave_busca in ano_anterior_por_semana:
                        ano_anterior_datas_realinhado.append(ano_anterior_por_semana[chave_busca]['data'])
                        ano_anterior_valores_realinhado.append(ano_anterior_por_semana[chave_busca]['valor'])
                    else:
                        # Se não encontrar a semana (raro), usar None/0
                        # Isso pode acontecer com semana 53 que não existe em todos os anos
                        ano_anterior_datas_realinhado.append(None)
                        ano_anterior_valores_realinhado.append(0)

                # Atualizar resposta com dados realinhados
                resposta['ano_anterior']['datas'] = ano_anterior_datas_realinhado
                resposta['ano_anterior']['valores'] = ano_anterior_valores_realinhado
                # Total permanece o mesmo (soma de todos os valores do período)
                print(f"  Ano anterior realinhado: {len(ano_anterior_valores_realinhado)} semanas correspondentes", flush=True)

                # Atualizar variáveis locais também para cálculo de métricas
                ano_anterior_valores = ano_anterior_valores_realinhado
                ano_anterior_datas = ano_anterior_datas_realinhado

            elif granularidade == 'mensal' and len(ano_anterior_datas) > 0 and len(datas_futuras) > 0:
                # Para mensal, realinhar por mês
                ano_anterior_por_mes = {}
                for i, data_str in enumerate(ano_anterior_datas):
                    if data_str is None:
                        continue
                    data_ant = pd.Timestamp(data_str)
                    if pd.isna(data_ant):
                        continue
                    mes = data_ant.month
                    ano_anterior_por_mes[mes] = {
                        'data': data_str,
                        'valor': ano_anterior_valores[i]
                    }

                ano_anterior_datas_realinhado = []
                ano_anterior_valores_realinhado = []

                for data_futura in datas_futuras[:periodos_previsao_efetivo]:
                    mes_futuro = data_futura.month
                    if mes_futuro in ano_anterior_por_mes:
                        ano_anterior_datas_realinhado.append(ano_anterior_por_mes[mes_futuro]['data'])
                        ano_anterior_valores_realinhado.append(ano_anterior_por_mes[mes_futuro]['valor'])
                    else:
                        ano_anterior_datas_realinhado.append(None)
                        ano_anterior_valores_realinhado.append(0)

                resposta['ano_anterior']['datas'] = ano_anterior_datas_realinhado
                resposta['ano_anterior']['valores'] = ano_anterior_valores_realinhado
                print(f"  Ano anterior realinhado: {len(ano_anterior_valores_realinhado)} meses correspondentes", flush=True)

                ano_anterior_valores = ano_anterior_valores_realinhado
                ano_anterior_datas = ano_anterior_datas_realinhado

            # Estruturar dados do modelo com teste e previsão futura
            modelo_data = {}

            # Adicionar previsões do período de teste
            if 'previsao_teste' in resultado and len(resultado['previsao_teste']) > 0:
                modelo_data['teste'] = {
                    'datas': [d.strftime('%Y-%m-%d') for d in datas_teste],
                    'valores': [float(v) for v in resultado['previsao_teste']]
                }

            # Adicionar previsões futuras
            if 'previsao_futuro' in resultado and len(resultado['previsao_futuro']) > 0:
                modelo_data['futuro'] = {
                    'datas': [d.strftime('%Y-%m-%d') for d in datas_futuras[:len(resultado['previsao_futuro'])]],
                    'valores': [float(v) for v in resultado['previsao_futuro']]
                }

                # Calcular WMAPE e BIAS para previsão futura comparando com ano anterior
                # Usar apenas os primeiros períodos correspondentes à validação futura
                previsao_futuro = resultado['previsao_futuro']
                if len(ano_anterior_valores) > 0 and len(previsao_futuro) > 0:
                    # Comparar apenas os períodos que temos no ano anterior (tamanho_validacao_futura)
                    tamanho_comparacao = min(tamanho_validacao_futura, len(ano_anterior_valores), len(previsao_futuro))

                    erros_absolutos_futuro = []
                    erros_percentuais_futuro = []
                    erros_reais_futuro = []

                    for i in range(tamanho_comparacao):
                        real = ano_anterior_valores[i]
                        previsto = previsao_futuro[i]

                        if real > 0:
                            erro_abs = abs(previsto - real)
                            erro_perc = (erro_abs / real) * 100
                            erro_real = previsto - real

                            erros_absolutos_futuro.append(erro_abs)
                            erros_percentuais_futuro.append(erro_perc)
                            erros_reais_futuro.append(erro_real)

                    if len(erros_percentuais_futuro) > 0:
                        wmape_futuro = sum(erros_percentuais_futuro) / len(erros_percentuais_futuro)
                        bias_futuro = (sum(erros_reais_futuro) / sum(ano_anterior_valores[:tamanho_comparacao])) * 100
                        mae_futuro = sum(erros_absolutos_futuro) / len(erros_absolutos_futuro)

                        metricas_futuro[nome_modelo] = {
                            'wmape': wmape_futuro,
                            'bias': bias_futuro,
                            'mae': mae_futuro
                        }

                        print(f"  Métricas futuras {nome_modelo}: WMAPE={wmape_futuro:.2f}%, BIAS={bias_futuro:.2f}%", flush=True)

            resposta['modelos'][nome_modelo] = modelo_data

        # Adicionar métricas futuras à resposta (comparação com ano anterior)
        resposta['metricas_futuro'] = metricas_futuro

        # Gerar alertas inteligentes baseado na previsão
        print(f"\nGerando alertas inteligentes...", flush=True)
        if melhor_modelo and melhor_modelo in resultados_modelos:
            modelo_info = {
                'modelo': melhor_modelo,
                'wmape': metricas.get(melhor_modelo, {}).get('wmape', 0),
                'bias': metricas.get(melhor_modelo, {}).get('bias', 0),
                'mae': metricas.get(melhor_modelo, {}).get('mae', 0),
                'seasonality_detected': {
                    'has_seasonality': tem_sazonalidade,
                    'detected_period': periodo_sazonal if tem_sazonalidade else None,
                    'strength': forca_sazonal if tem_sazonalidade else 0.0
                },
                'outliers_count': resultado_outliers.get('outliers_count', 0)
            }

            resultado_alertas = generate_alerts_for_forecast(
                sku=produto if produto != 'TODOS' else 'AGREGADO',
                loja=loja if loja != 'TODAS' else 'TODAS',
                historico=serie_temporal_completa,
                previsao=resultados_modelos[melhor_modelo].get('previsao_futuro', []),
                modelo_params=modelo_info,
                estoque_atual=None,  # Não disponível neste endpoint
                lead_time_dias=7,
                custo_unitario=None  # Não disponível neste endpoint
            )

            alertas = resultado_alertas['alertas']
            resumo_alertas = resultado_alertas['resumo']

            resposta['alertas'] = alertas
            resposta['resumo_alertas'] = resumo_alertas
            print(f"  {len(alertas)} alertas gerados", flush=True)

            # Resumo por prioridade
            criticos = sum(1 for a in alertas if a.get('tipo') == 'CRITICAL')
            avisos = sum(1 for a in alertas if a.get('tipo') == 'WARNING')
            info = sum(1 for a in alertas if a.get('tipo') == 'INFO')

            if criticos > 0:
                print(f"  [CRITICO] {criticos} alertas criticos", flush=True)
            if avisos > 0:
                print(f"  [AVISO] {avisos} avisos", flush=True)
            if info > 0:
                print(f"  [INFO] {info} informativos", flush=True)
        else:
            resposta['alertas'] = []

        print(f"\nPrevisão gerada com sucesso! Melhor modelo: {melhor_modelo}")

        return jsonify(resposta)

    except Exception as e:
        import traceback
        erro_msg = traceback.format_exc()
        # Gravar erro em arquivo para debug
        with open('erro_previsao.log', 'w', encoding='utf-8') as f:
            f.write(erro_msg)
        try:
            print(f"Erro ao gerar previsao: {e}", flush=True)
        except:
            pass
        return jsonify({'erro': str(e)}), 500


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
