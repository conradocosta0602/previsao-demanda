"""
Módulo de Cálculo Avançado de Demanda
Oferece múltiplos métodos para calcular demanda média de forma mais assertiva
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
from scipy import stats


class DemandCalculator:
    """
    Calculadora de demanda com múltiplos métodos estatísticos
    """

    @staticmethod
    def calcular_demanda_ema(
        vendas: List[float],
        alpha: float = 0.3
    ) -> Tuple[float, float]:
        """
        Método 2: Média Móvel Ponderada Exponencial (EMA)
        Dá mais peso aos períodos recentes

        Args:
            vendas: Lista de vendas mensais (ordenadas do mais antigo ao mais recente)
            alpha: Fator de suavização (0 < alpha < 1)
                   - alpha baixo (0.1-0.2): mais conservador, menos sensível a mudanças
                   - alpha médio (0.3-0.4): balanceado
                   - alpha alto (0.5+): mais reativo, segue tendências rapidamente

        Returns:
            (demanda_ema, desvio_padrao_ponderado)
        """
        if len(vendas) == 0:
            return 0.0, 0.0

        if len(vendas) == 1:
            return vendas[0], 0.0

        # Calcular EMA
        ema = vendas[0]
        emas = [ema]

        for venda in vendas[1:]:
            ema = alpha * venda + (1 - alpha) * ema
            emas.append(ema)

        # Demanda prevista é o último valor EMA
        demanda_ema = emas[-1]

        # Calcular desvio padrão ponderado
        # Pesos exponenciais decrescentes (mais recente = maior peso)
        n = len(vendas)
        pesos = np.array([(1 - alpha) ** (n - i - 1) for i in range(n)])
        pesos = pesos / pesos.sum()  # Normalizar

        media_ponderada = np.sum(np.array(vendas) * pesos)
        variancia_ponderada = np.sum(pesos * (np.array(vendas) - media_ponderada) ** 2)
        desvio_ponderado = np.sqrt(variancia_ponderada)

        return demanda_ema, desvio_ponderado

    @staticmethod
    def calcular_demanda_sma(
        vendas: List[float],
        janela: int = None
    ) -> Tuple[float, float]:
        """
        Método 2A: Média Móvel Simples (SMA)
        Calcula média dos últimos N períodos (janela móvel)

        Útil para: Demanda constante sem tendências fortes

        Args:
            vendas: Lista de vendas mensais
            janela: Número de períodos (se None, usa len(vendas)//2 ou mínimo 3)

        Returns:
            (demanda_sma, desvio_padrao)
        """
        if len(vendas) == 0:
            return 0.0, 0.0

        if len(vendas) == 1:
            return vendas[0], 0.0

        # Definir janela automaticamente se não fornecida
        if janela is None:
            janela = max(3, len(vendas) // 2)

        # Garantir que janela não exceda número de períodos
        janela = min(janela, len(vendas))

        # Calcular SMA (média dos últimos N períodos)
        ultimos_periodos = vendas[-janela:]
        demanda_sma = np.mean(ultimos_periodos)
        desvio_padrao = np.std(ultimos_periodos, ddof=1) if len(ultimos_periodos) > 1 else 0

        return demanda_sma, desvio_padrao

    @staticmethod
    def calcular_demanda_wma(
        vendas: List[float],
        janela: int = None
    ) -> Tuple[float, float]:
        """
        Método 2B: Média Móvel Ponderada (WMA)
        Similar à SMA, mas dá mais peso aos períodos recentes

        Útil para: Quando mudanças recentes devem ter mais influência

        Args:
            vendas: Lista de vendas mensais
            janela: Número de períodos (se None, usa len(vendas)//2 ou mínimo 3)

        Returns:
            (demanda_wma, desvio_padrao_ponderado)
        """
        if len(vendas) == 0:
            return 0.0, 0.0

        if len(vendas) == 1:
            return vendas[0], 0.0

        # Definir janela automaticamente
        if janela is None:
            janela = max(3, len(vendas) // 2)

        janela = min(janela, len(vendas))

        # Pegar últimos períodos
        ultimos_periodos = np.array(vendas[-janela:])

        # Criar pesos lineares (mais recente = maior peso)
        # Exemplo janela=4: pesos = [1, 2, 3, 4]
        pesos = np.arange(1, janela + 1)
        pesos = pesos / pesos.sum()  # Normalizar

        # Calcular WMA
        demanda_wma = np.sum(ultimos_periodos * pesos)

        # Desvio padrão ponderado
        media_ponderada = demanda_wma
        variancia_ponderada = np.sum(pesos * (ultimos_periodos - media_ponderada) ** 2)
        desvio_ponderado = np.sqrt(variancia_ponderada)

        return demanda_wma, desvio_ponderado

    @staticmethod
    def calcular_demanda_tendencia(vendas: List[float]) -> Tuple[float, float]:
        """
        Método 3: Regressão Linear com Tendência
        Identifica e projeta tendências de crescimento/queda

        Args:
            vendas: Lista de vendas mensais

        Returns:
            (demanda_projetada, desvio_padrao_residual)
        """
        if len(vendas) < 3:
            return DemandCalculator.calcular_demanda_sma(vendas)

        # Criar índice temporal
        X = np.arange(len(vendas)).reshape(-1, 1)
        y = np.array(vendas)

        # Regressão linear simples: y = a + b*x
        X_mean = X.mean()
        y_mean = y.mean()

        # Coeficiente angular (b)
        numerador = np.sum((X.flatten() - X_mean) * (y - y_mean))
        denominador = np.sum((X.flatten() - X_mean) ** 2)
        b = numerador / denominador if denominador != 0 else 0

        # Coeficiente linear (a)
        a = y_mean - b * X_mean

        # Projetar próximo período (n+1)
        demanda_projetada = a + b * len(vendas)

        # Calcular desvio padrão dos resíduos
        y_pred = a + b * X.flatten()
        residuos = y - y_pred
        desvio_residual = np.std(residuos, ddof=2) if len(residuos) > 2 else np.std(vendas, ddof=1)

        return max(0, demanda_projetada), desvio_residual

    @staticmethod
    def calcular_demanda_sazonal(
        vendas: List[float],
        periodo_sazonal: int = 12
    ) -> Tuple[float, float]:
        """
        Método 4: Decomposição Sazonal com Índices Mensais
        Calcula índices sazonais para cada mês e projeta usando comportamento mensal real

        Args:
            vendas: Lista de vendas mensais
            periodo_sazonal: Período da sazonalidade (padrão: 12 meses = anual)

        Returns:
            (demanda_ajustada_sazonal, desvio_padrao)
        """
        if len(vendas) < 12:
            # Menos de 1 ano de dados, usar tendência
            return DemandCalculator.calcular_demanda_tendencia(vendas)

        vendas_array = np.array(vendas)
        n = len(vendas_array)

        # NOVA ABORDAGEM: Calcular índice sazonal para cada mês do ano
        # baseado no comportamento histórico real, ignorando período detectado

        # Agrupar vendas por mês do ano (1-12)
        vendas_por_mes = {}
        for i, venda in enumerate(vendas_array):
            mes_do_ano = (i % 12) + 1  # 1 = Jan, 2 = Fev, ..., 12 = Dez
            if mes_do_ano not in vendas_por_mes:
                vendas_por_mes[mes_do_ano] = []
            vendas_por_mes[mes_do_ano].append(venda)

        # Calcular média de cada mês
        medias_mensais = {}
        for mes in range(1, 13):
            if mes in vendas_por_mes and len(vendas_por_mes[mes]) > 0:
                medias_mensais[mes] = np.mean(vendas_por_mes[mes])
            else:
                medias_mensais[mes] = np.mean(vendas_array)

        # Calcular média geral
        media_geral = np.mean(list(medias_mensais.values()))

        # Calcular índices sazonais (média do mês / média geral)
        indices_mensais = {}
        for mes in range(1, 13):
            indices_mensais[mes] = medias_mensais[mes] / media_geral if media_geral > 0 else 1.0

        # Identificar qual será o próximo mês
        proximo_mes_numero = (n % 12) + 1  # 1-12

        # Dessazonalizar dados históricos para calcular tendência sem viés sazonal
        vendas_dessazonalizadas = []
        for i, venda in enumerate(vendas_array):
            mes_do_dado = (i % 12) + 1
            indice_mes = indices_mensais[mes_do_dado]
            venda_dessaz = venda / indice_mes if indice_mes > 0 else venda
            vendas_dessazonalizadas.append(venda_dessaz)

        # Calcular tendência usando dados dessazonalizados (últimos 6-12 meses)
        janela = min(12, max(6, n // 2))
        demanda_tendencia, desvio_tendencia = DemandCalculator.calcular_demanda_tendencia(
            vendas_dessazonalizadas[-janela:]
        )

        # Aplicar índice sazonal do próximo mês
        fator_sazonal = indices_mensais[proximo_mes_numero]
        demanda_sazonal = demanda_tendencia * fator_sazonal

        # Ajustar desvio pela variabilidade sazonal
        # Calcular desvio histórico do mês específico
        if proximo_mes_numero in vendas_por_mes and len(vendas_por_mes[proximo_mes_numero]) > 1:
            desvio_mensal = np.std(vendas_por_mes[proximo_mes_numero], ddof=1)
        else:
            desvio_mensal = desvio_tendencia * abs(fator_sazonal)

        return max(0, demanda_sazonal), desvio_mensal

    @staticmethod
    def calcular_demanda_tsb(
        vendas: List[float],
        alpha_prob: float = 0.1,
        alpha_tamanho: float = 0.1
    ) -> Tuple[float, float]:
        """
        Método 5: Teunter-Syntetos-Babai (TSB)
        Ideal para demanda intermitente (muitos zeros, vendas esporádicas)

        TSB melhora o método de Croston ao separar dois componentes:
        1. Probabilidade de ocorrer demanda
        2. Tamanho médio da demanda quando ocorre

        Fórmula: Previsão = P(demanda > 0) × Tamanho Médio

        Vantagens sobre Croston:
        - Corrige viés positivo do Croston (tende a superestimar)
        - Mais preciso para demanda altamente intermitente (>60% zeros)
        - Suavização exponencial separada para cada componente

        Args:
            vendas: Lista de vendas mensais
            alpha_prob: Fator de suavização para probabilidade (padrão: 0.1)
            alpha_tamanho: Fator de suavização para tamanho (padrão: 0.1)

        Returns:
            (demanda_tsb, desvio_padrao)
        """
        if len(vendas) == 0:
            return 0.0, 0.0

        vendas_array = np.array(vendas)

        # Verificar se há demanda não-zero
        demandas_nao_zero = vendas_array[vendas_array > 0]

        if len(demandas_nao_zero) == 0:
            return 0.0, 0.0

        if len(demandas_nao_zero) == len(vendas_array):
            # Não é intermitente, usar EMA
            return DemandCalculator.calcular_demanda_ema(vendas)

        if len(demandas_nao_zero) == 1:
            # Apenas uma demanda, retornar valor único
            return demandas_nao_zero[0] / len(vendas_array), 0.0

        # Componente 1: Probabilidade de demanda (suavização exponencial)
        # Inicializar com probabilidade empírica
        prob_inicial = len(demandas_nao_zero) / len(vendas_array)
        prob_atual = prob_inicial

        for venda in vendas_array:
            ocorreu_demanda = 1.0 if venda > 0 else 0.0
            prob_atual = alpha_prob * ocorreu_demanda + (1 - alpha_prob) * prob_atual

        probabilidade_demanda = prob_atual

        # Componente 2: Tamanho médio da demanda (suavização exponencial sobre não-zeros)
        tamanho_atual = demandas_nao_zero[0]  # Inicializar com primeiro valor não-zero

        for venda in vendas_array:
            if venda > 0:
                tamanho_atual = alpha_tamanho * venda + (1 - alpha_tamanho) * tamanho_atual

        tamanho_medio = tamanho_atual

        # Previsão TSB
        demanda_tsb = probabilidade_demanda * tamanho_medio

        # Desvio padrão
        # Para demanda intermitente: Var = p × (σ² + μ²) - (p × μ)²
        variancia_tamanho = np.var(demandas_nao_zero, ddof=1) if len(demandas_nao_zero) > 1 else 0
        variancia_total = (
            probabilidade_demanda * (variancia_tamanho + tamanho_medio**2) -
            demanda_tsb**2
        )
        desvio = np.sqrt(max(0, variancia_total))

        return demanda_tsb, desvio

    @staticmethod
    def escolher_melhor_metodo_estavel(vendas: List[float]) -> Tuple[str, float, float, float]:
        """
        Escolhe automaticamente o melhor método entre SMA, WMA e SES para demanda estável
        Usa validação cruzada (walk-forward) para comparar erro de previsão

        Args:
            vendas: Lista de vendas mensais

        Returns:
            (metodo_escolhido, demanda, desvio, mae_melhor)
        """
        if len(vendas) < 4:
            # Poucos dados, usar SMA
            demanda, desvio = DemandCalculator.calcular_demanda_sma(vendas)
            return 'sma', demanda, desvio, 0.0

        # Reservar últimos 30% dos dados para validação (mínimo 2, máximo 6 períodos)
        n_val = max(2, min(6, int(len(vendas) * 0.3)))
        treino = vendas[:-n_val]
        validacao = vendas[-n_val:]

        if len(treino) < 3:
            demanda, desvio = DemandCalculator.calcular_demanda_sma(vendas)
            return 'sma', demanda, desvio, 0.0

        # Testar 2 métodos: SMA e WMA
        metodos_testar = {
            'sma': lambda v: DemandCalculator.calcular_demanda_sma(v),
            'wma': lambda v: DemandCalculator.calcular_demanda_wma(v)
        }

        erros = {}

        # Walk-forward validation
        for nome_metodo, func_metodo in metodos_testar.items():
            erros_metodo = []

            # Simular previsões walk-forward
            for i in range(len(treino), len(vendas)):
                dados_treino = vendas[:i]
                valor_real = vendas[i]

                # Fazer previsão
                previsao, _ = func_metodo(dados_treino)

                # Calcular erro absoluto
                erro = abs(valor_real - previsao)
                erros_metodo.append(erro)

            # MAE (Mean Absolute Error)
            mae = np.mean(erros_metodo) if erros_metodo else float('inf')
            erros[nome_metodo] = mae

        # Escolher método com menor erro
        melhor_metodo = min(erros, key=erros.get)
        mae_melhor = erros[melhor_metodo]

        # Calcular demanda final com todos os dados usando melhor método
        demanda, desvio = metodos_testar[melhor_metodo](vendas)

        return melhor_metodo, demanda, desvio, mae_melhor

    @staticmethod
    def classificar_padrao_demanda(vendas: List[float]) -> Dict[str, any]:
        """
        Classifica o padrão de demanda para escolher o melhor método

        Args:
            vendas: Lista de vendas mensais

        Returns:
            Dicionário com classificação e recomendação de método
        """
        if len(vendas) < 3:
            return {
                'padrao': 'insuficiente',
                'metodo_recomendado': 'simples',
                'confianca': 'baixa'
            }

        vendas_array = np.array(vendas)

        # 1. Verificar intermitência (% de zeros)
        zeros_pct = (vendas_array == 0).sum() / len(vendas_array)

        # 2. Calcular Coeficiente de Variação (CV)
        media = np.mean(vendas_array)
        desvio = np.std(vendas_array, ddof=1)
        cv = desvio / media if media > 0 else 999

        # 3. Detectar tendência (teste de Mann-Kendall simplificado)
        n = len(vendas_array)
        s = 0
        for i in range(n - 1):
            for j in range(i + 1, n):
                s += np.sign(vendas_array[j] - vendas_array[i])

        tendencia_forte = abs(s) > (n * (n - 1) / 4)  # Mais de 50% das comparações na mesma direção

        # 4. Detectar sazonalidade usando o detector automático
        sazonalidade_forte = False
        periodo_sazonal = None
        forca_sazonalidade = 0.0

        if len(vendas_array) >= 8:  # Mínimo para detector de sazonalidade
            from core.seasonality_detector import detect_seasonality
            resultado_sazonal = detect_seasonality(vendas_array.tolist())

            if resultado_sazonal['has_seasonality']:
                sazonalidade_forte = True
                periodo_sazonal = resultado_sazonal['seasonal_period']
                forca_sazonalidade = resultado_sazonal['strength']

        # LÓGICA DE DECISÃO
        if zeros_pct > 0.3:
            # Demanda intermitente
            padrao = 'intermitente'
            metodo = 'tsb'
            confianca = 'media'

        elif sazonalidade_forte:
            # Demanda sazonal
            padrao = 'sazonal'
            metodo = 'sazonal'
            confianca = 'alta'

        elif tendencia_forte:
            # Demanda com tendência
            padrao = 'tendencia'
            metodo = 'tendencia'
            confianca = 'alta'

        elif cv > 0.5:
            # Alta variabilidade - usar EMA para ser mais reativo
            padrao = 'variavel'
            metodo = 'ema'
            confianca = 'media'

        else:
            # Demanda estável - escolher automaticamente entre simples, sma, wma, ses
            padrao = 'estavel'
            metodo = 'auto_estavel'  # Marcador para usar escolha automática
            confianca = 'alta'

        resultado = {
            'padrao': padrao,
            'metodo_recomendado': metodo,
            'confianca': confianca,
            'cv': round(cv, 2),
            'zeros_pct': round(zeros_pct * 100, 1),
            'tendencia': 'sim' if tendencia_forte else 'nao',
            'sazonalidade': 'sim' if sazonalidade_forte else 'nao',
            'tem_tendencia': tendencia_forte,
            'tem_sazonalidade': sazonalidade_forte
        }

        if sazonalidade_forte and periodo_sazonal:
            resultado['periodo_sazonal'] = periodo_sazonal
            resultado['forca_sazonalidade'] = round(forca_sazonalidade, 2)

        return resultado

    @staticmethod
    def calcular_demanda_inteligente(
        vendas: List[float],
        metodo: str = 'auto'
    ) -> Tuple[float, float, Dict]:
        """
        Método 6: INTELIGENTE - Escolhe automaticamente o melhor método

        Args:
            vendas: Lista de vendas mensais
            metodo: 'auto', 'simples', 'ema', 'tendencia', 'sazonal', 'tsb'

        Returns:
            (demanda_media, desvio_padrao, metadata)
        """
        if len(vendas) == 0:
            return 0.0, 0.0, {'metodo_usado': 'nenhum', 'erro': 'sem_dados'}

        # Se método não é automático, usar método específico
        if metodo != 'auto':
            metodos_disponiveis = {
                'sma': DemandCalculator.calcular_demanda_sma,
                'wma': DemandCalculator.calcular_demanda_wma,
                'ema': DemandCalculator.calcular_demanda_ema,
                'tendencia': DemandCalculator.calcular_demanda_tendencia,
                'sazonal': DemandCalculator.calcular_demanda_sazonal,
                'tsb': DemandCalculator.calcular_demanda_tsb
            }

            if metodo in metodos_disponiveis:
                demanda, desvio = metodos_disponiveis[metodo](vendas)
                return demanda, desvio, {'metodo_usado': metodo, 'modo': 'manual'}
            else:
                # Método inválido, usar SMA
                demanda, desvio = DemandCalculator.calcular_demanda_sma(vendas)
                return demanda, desvio, {'metodo_usado': 'sma', 'erro': 'metodo_invalido'}

        # MODO AUTOMÁTICO - Classificar e escolher melhor método
        classificacao = DemandCalculator.classificar_padrao_demanda(vendas)
        metodo_escolhido = classificacao['metodo_recomendado']

        # Calcular demanda com método escolhido
        if metodo_escolhido == 'auto_estavel':
            # Demanda estável - escolher automaticamente entre simples, sma, wma, ses
            metodo_final, demanda, desvio, mae = DemandCalculator.escolher_melhor_metodo_estavel(vendas)

            # Metadata completa
            metadata = {
                'metodo_usado': metodo_final,
                'modo': 'automatico',
                'classificacao': classificacao,
                'num_periodos': len(vendas),
                'ultima_venda': vendas[-1] if len(vendas) > 0 else 0,
                'mae_validacao': round(mae, 2)
            }

        elif metodo_escolhido == 'tsb':
            demanda, desvio = DemandCalculator.calcular_demanda_tsb(vendas)
            metadata = {
                'metodo_usado': metodo_escolhido,
                'modo': 'automatico',
                'classificacao': classificacao,
                'num_periodos': len(vendas),
                'ultima_venda': vendas[-1] if len(vendas) > 0 else 0
            }

        elif metodo_escolhido == 'sazonal':
            # Usar período detectado automaticamente se disponível
            periodo = classificacao.get('periodo_sazonal', 12)
            demanda, desvio = DemandCalculator.calcular_demanda_sazonal(vendas, periodo_sazonal=periodo)
            metadata = {
                'metodo_usado': metodo_escolhido,
                'modo': 'automatico',
                'classificacao': classificacao,
                'num_periodos': len(vendas),
                'ultima_venda': vendas[-1] if len(vendas) > 0 else 0,
                'periodo_sazonal': periodo
            }

        elif metodo_escolhido == 'tendencia':
            demanda, desvio = DemandCalculator.calcular_demanda_tendencia(vendas)
            metadata = {
                'metodo_usado': metodo_escolhido,
                'modo': 'automatico',
                'classificacao': classificacao,
                'num_periodos': len(vendas),
                'ultima_venda': vendas[-1] if len(vendas) > 0 else 0
            }

        elif metodo_escolhido == 'ema':
            demanda, desvio = DemandCalculator.calcular_demanda_ema(vendas)
            metadata = {
                'metodo_usado': metodo_escolhido,
                'modo': 'automatico',
                'classificacao': classificacao,
                'num_periodos': len(vendas),
                'ultima_venda': vendas[-1] if len(vendas) > 0 else 0
            }

        else:
            demanda, desvio = DemandCalculator.calcular_demanda_sma(vendas)
            metadata = {
                'metodo_usado': 'sma',
                'modo': 'automatico',
                'classificacao': classificacao,
                'num_periodos': len(vendas),
                'ultima_venda': vendas[-1] if len(vendas) > 0 else 0
            }

        return demanda, desvio, metadata


def processar_demandas_dataframe(
    df_historico: pd.DataFrame,
    metodo: str = 'auto',
    agrupar_por: List[str] = ['Loja', 'SKU']
) -> pd.DataFrame:
    """
    Processa cálculo de demanda para múltiplos itens em um DataFrame

    Args:
        df_historico: DataFrame com colunas: Loja, SKU, Mes, Vendas
        metodo: Método a usar ('auto', 'simples', 'ema', 'tendencia', 'sazonal', 'tsb')
        agrupar_por: Colunas para agrupar (padrão: ['Loja', 'SKU'])

    Returns:
        DataFrame com demanda média e desvio padrão calculados por item
    """
    resultados = []

    # Agrupar por loja e SKU
    for nome_grupo, grupo in df_historico.groupby(agrupar_por):
        # Ordenar por mês
        grupo = grupo.sort_values('Mes')
        vendas = grupo['Vendas'].tolist()

        # Calcular demanda
        demanda, desvio, metadata = DemandCalculator.calcular_demanda_inteligente(vendas, metodo)

        # Criar dicionário de resultado
        resultado = {}

        # Adicionar chaves de agrupamento
        if isinstance(nome_grupo, tuple):
            for i, col in enumerate(agrupar_por):
                resultado[col] = nome_grupo[i]
        else:
            resultado[agrupar_por[0]] = nome_grupo

        # Adicionar métricas calculadas
        resultado.update({
            'Demanda_Media_Mensal': round(demanda, 2),
            'Desvio_Padrao_Mensal': round(desvio, 2),
            'Metodo_Usado': metadata['metodo_usado'],
            'Num_Periodos_Historico': metadata['num_periodos'],
            'Ultima_Venda': metadata.get('ultima_venda', 0)
        })

        # Adicionar classificação se disponível
        if 'classificacao' in metadata:
            resultado['Padrao_Demanda'] = metadata['classificacao']['padrao']
            resultado['Confianca'] = metadata['classificacao']['confianca']
            resultado['CV'] = metadata['classificacao']['cv']

        resultados.append(resultado)

    return pd.DataFrame(resultados)
