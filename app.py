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
from core.data_adapter import DataAdapter
from core.stockout_handler import processar_stockouts_dataframe, calcular_metricas_stockout
from core.method_selector import MethodSelector
from core.forecasting_models import get_modelo
from core.aggregator import CDAggregator, gerar_previsoes_cd
from core.reporter import ExcelReporter, gerar_nome_arquivo, preparar_resultados
from core.replenishment_calculator import processar_reabastecimento
from core.smart_alerts import generate_alerts_for_forecast

# Configuração do Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo


def detectar_formato_dados(arquivo_excel: str) -> str:
    """
    Detecta o formato dos dados no arquivo Excel

    Returns:
        'diario' se formato novo (data, cod_empresa, codigo, qtd_venda, padrao_compra)
        'mensal' se formato legado (Mes, Loja, SKU, Vendas, Dias_Com_Estoque, Origem)
    """
    try:
        df = pd.read_excel(arquivo_excel, nrows=5)
        colunas = df.columns.tolist()

        # Verificar se é formato diário (novo)
        colunas_diarias = ['data', 'cod_empresa', 'codigo', 'qtd_venda']
        if all(col in colunas for col in colunas_diarias):
            return 'diario'

        # Verificar se é formato mensal (legado)
        colunas_mensais = ['Mes', 'Loja', 'SKU', 'Vendas']
        if all(col in colunas for col in colunas_mensais):
            return 'mensal'

        # Formato não reconhecido
        return 'desconhecido'

    except Exception as e:
        print(f"Erro ao detectar formato: {e}")
        return 'desconhecido'


def processar_previsao(arquivo_excel: str,
                      meses_previsao: int = 6,
                      granularidade: str = 'semanal',
                      filiais_filtro: list = None,
                      produtos_filtro: list = None) -> dict:
    """
    Pipeline completo de processamento de previsão
    Suporta tanto formato legado (mensal) quanto novo formato (diário)

    Args:
        arquivo_excel: Caminho para o arquivo Excel
        meses_previsao: Número de meses/semanas para prever
        granularidade: 'semanal' ou 'mensal' (apenas para formato diário)
        filiais_filtro: Lista de códigos de filiais para filtrar (formato diário)
        produtos_filtro: Lista de códigos de produtos para filtrar (formato diário)

    Returns:
        Dicionário com todos os resultados e arquivo gerado
    """
    alertas = []
    metadados_extras = {}

    # DETECTAR FORMATO DOS DADOS
    formato = detectar_formato_dados(arquivo_excel)
    print(f"Formato detectado: {formato}")

    # 1. CARREGAR E VALIDAR DADOS
    print("1. Carregando dados...")

    if formato == 'diario':
        # Usar novo adaptador para dados diários
        print("   [INFO] Usando adaptador de dados diários...")
        adapter = DataAdapter(arquivo_excel)

        valido, mensagens = adapter.carregar_e_validar()
        if not valido:
            raise ValueError(f"Dados inválidos: {'; '.join(mensagens)}")

        # Converter para formato legado
        df = adapter.converter_para_formato_legado(
            granularidade=granularidade,
            filiais=filiais_filtro,
            produtos=produtos_filtro
        )

        # Adicionar metadados extras
        metadados_extras = {
            'formato_origem': 'diario',
            'granularidade': granularidade,
            'filiais_disponiveis': adapter.get_lista_filiais(),
            'produtos_disponiveis': adapter.get_lista_produtos(),
            'estatisticas': adapter.estatisticas_dados()
        }

        # Adicionar avisos
        for msg in mensagens:
            alertas.append({'tipo': 'info', 'mensagem': msg})

    else:
        # Usar loader legado para dados mensais
        print("   [INFO] Usando loader de dados mensais (legado)...")
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

        # Ajustar mês corrente (apenas para formato mensal)
        print("2. Ajustando mês corrente...")
        df = ajustar_mes_corrente(df)

        meses_projetados = df['Mes_Projetado'].sum()
        if meses_projetados > 0:
            alertas.append({
                'tipo': 'info',
                'mensagem': f'{meses_projetados} registros do mês atual foram projetados'
            })

        metadados_extras = {'formato_origem': 'mensal'}

    print(f"   [OK] {len(df)} registros carregados")

    # 2. TRATAR STOCKOUTS (apenas se tiver coluna Mes_Projetado)
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

        # Calcular métricas de acurácia (MAPE + BIAS)
        mape = None
        bias = None
        try:
            from core.accuracy_metrics import evaluate_model_accuracy
            if len(vendas) >= 9:  # Mínimo para validação confiável
                accuracy = evaluate_model_accuracy(
                    vendas,
                    recomendacao['metodo'],
                    horizon=1
                )
                mape = accuracy['mape']
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
                'MAPE': round(mape, 1) if mape is not None else None,
                'BIAS': round(bias, 2) if bias is not None else None
            })

        # Gerar alertas inteligentes
        try:
            # Preparar modelo_info com métricas e parâmetros
            modelo_info = {
                **modelo.params,  # Parâmetros do modelo (outliers, sazonalidade, etc)
                'mape': mape,
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
            print(f"   ✓ {len(eventos_aplicados)} previsões ajustadas por eventos sazonais")
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

    # Adicionar metadados extras ao resultado
    resultado = {
        'success': True,
        'arquivo_saida': nome_arquivo,
        'resumo': resumo,
        'alertas': alertas,  # Alertas do sistema (validação, etc)
        'grafico_data': grafico_data,
        'smart_alerts': todos_alertas,  # Alertas inteligentes
        'smart_alerts_summary': resumo_alertas  # Resumo dos alertas inteligentes
    }

    # Adicionar metadados se houver (formato diário)
    if metadados_extras:
        resultado['metadados'] = metadados_extras

    return resultado


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
