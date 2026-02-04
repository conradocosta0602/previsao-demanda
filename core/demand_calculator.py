"""
Módulo de Cálculo Avançado de Demanda
Oferece múltiplos métodos para calcular demanda média de forma mais assertiva
Inclui tratamento especial para séries curtas (< 12 períodos)
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
from scipy import stats


class DemandCalculator:
    """
    Calculadora de demanda com múltiplos métodos estatísticos
    Inclui tratamento inteligente para séries curtas
    """

    # =====================================================
    # MÉTODOS PARA SÉRIES CURTAS (< 12 períodos)
    # =====================================================

    @staticmethod
    def calcular_demanda_serie_muito_curta(
        vendas: List[float],
        media_cluster: Optional[float] = None
    ) -> Tuple[float, float, Dict]:
        """
        Método para séries muito curtas (1-2 períodos)
        Usa abordagem Naïve com ajuste de confiança e prior bayesiano

        Args:
            vendas: Lista de vendas (1-2 valores)
            media_cluster: Média de produtos similares (opcional, para prior bayesiano)

        Returns:
            (demanda, desvio, metadata)
        """
        if len(vendas) == 0:
            return 0.0, 0.0, {'metodo_usado': 'sem_dados', 'confianca': 'muito_baixa'}

        if len(vendas) == 1:
            valor = vendas[0]

            # Se temos média do cluster, fazer média bayesiana
            if media_cluster is not None and media_cluster > 0:
                # Peso 30% para o único dado, 70% para o prior (cluster)
                demanda = 0.3 * valor + 0.7 * media_cluster
                # Desvio estimado: 50% da demanda (alta incerteza)
                desvio = demanda * 0.5
                metodo = 'bayesiano_prior'
            else:
                # Naïve: usar o único valor disponível
                demanda = valor
                # Desvio heurístico: 40% do valor (alta incerteza)
                desvio = max(valor * 0.4, 1.0)
                metodo = 'naive_unico'

            return demanda, desvio, {
                'metodo_usado': metodo,
                'confianca': 'muito_baixa',
                'num_periodos': 1,
                'fator_seguranca_recomendado': 2.0  # Dobrar estoque de segurança
            }

        # 2 períodos
        media = np.mean(vendas)
        variacao = abs(vendas[1] - vendas[0])

        # Se temos média do cluster, combinar
        if media_cluster is not None and media_cluster > 0:
            # Peso 50% para dados, 50% para prior
            demanda = 0.5 * media + 0.5 * media_cluster
            metodo = 'bayesiano_2periodos'
        else:
            demanda = media
            metodo = 'media_2periodos'

        # Desvio baseado na variação entre os 2 pontos
        # Se variação alta, mais incerteza
        cv_estimado = variacao / media if media > 0 else 0.5
        desvio = demanda * max(0.3, min(0.6, cv_estimado))

        return demanda, desvio, {
            'metodo_usado': metodo,
            'confianca': 'muito_baixa',
            'num_periodos': 2,
            'variacao_detectada': round(variacao, 2),
            'fator_seguranca_recomendado': 1.8
        }

    @staticmethod
    def calcular_demanda_serie_curta(
        vendas: List[float],
        media_cluster: Optional[float] = None
    ) -> Tuple[float, float, Dict]:
        """
        Método para séries curtas (3-6 períodos)
        Usa SMA/WMA adaptativo com tendência simplificada

        Args:
            vendas: Lista de vendas (3-6 valores)
            media_cluster: Média de produtos similares (opcional)

        Returns:
            (demanda, desvio, metadata)
        """
        n = len(vendas)
        vendas_array = np.array(vendas)

        # Calcular estatísticas básicas
        media = np.mean(vendas_array)
        desvio_base = np.std(vendas_array, ddof=1) if n > 1 else media * 0.3

        # Verificar intermitência (muitos zeros)
        zeros_pct = (vendas_array == 0).sum() / n
        if zeros_pct > 0.4:
            # Demanda intermitente - usar TSB simplificado COM TENDENCIA
            demandas_nz = vendas_array[vendas_array > 0]
            if len(demandas_nz) > 0:
                prob_demanda = len(demandas_nz) / n
                media_nz = np.mean(demandas_nz)
                demanda_base = prob_demanda * media_nz

                # CORRECAO: Considerar tendencia para demanda intermitente
                # Se a segunda metade da serie tem menos vendas, aplicar fator de queda
                meio = n // 2
                primeira_metade = vendas_array[:meio]
                segunda_metade = vendas_array[meio:]

                media_primeira = np.mean(primeira_metade)
                media_segunda = np.mean(segunda_metade)

                fator_tendencia = 1.0
                tendencia = 'estavel'

                if media_primeira > 0:
                    razao = media_segunda / media_primeira
                    if razao < 0.5:
                        # Queda significativa (>50%) - produto pode estar saindo de linha
                        fator_tendencia = max(0.1, razao)  # Minimo 10% da demanda base
                        tendencia = 'queda_acentuada'
                    elif razao < 0.85:
                        # Queda moderada
                        fator_tendencia = razao
                        tendencia = 'decrescente'
                    elif razao > 1.15:
                        # Crescimento
                        fator_tendencia = min(1.5, razao)  # Maximo 50% acima
                        tendencia = 'crescente'

                demanda = demanda_base * fator_tendencia
                desvio = demanda * 0.5  # Alta incerteza

                return demanda, desvio, {
                    'metodo_usado': 'tsb_simplificado',
                    'confianca': 'baixa',
                    'num_periodos': n,
                    'zeros_pct': round(zeros_pct * 100, 1),
                    'tendencia_detectada': tendencia,
                    'fator_tendencia': round(fator_tendencia, 3),
                    'media_primeira_metade': round(media_primeira, 4),
                    'media_segunda_metade': round(media_segunda, 4),
                    'fator_seguranca_recomendado': 1.6
                }

        # Detectar tendência simples (comparar primeira e segunda metade)
        meio = n // 2
        media_primeira = np.mean(vendas_array[:meio])
        media_segunda = np.mean(vendas_array[meio:])

        tendencia = 'estavel'
        fator_tendencia = 1.0

        if media_primeira > 0:
            variacao_tendencia = (media_segunda - media_primeira) / media_primeira
            if variacao_tendencia > 0.15:
                tendencia = 'crescente'
                fator_tendencia = 1.0 + (variacao_tendencia * 0.5)  # Projetar parcialmente
            elif variacao_tendencia < -0.15:
                tendencia = 'decrescente'
                fator_tendencia = 1.0 + (variacao_tendencia * 0.5)

        # WMA com janela = n (todos os dados, mais peso nos recentes)
        pesos = np.arange(1, n + 1)
        pesos = pesos / pesos.sum()
        demanda_wma = np.sum(vendas_array * pesos)

        # Aplicar fator de tendência
        demanda = demanda_wma * fator_tendencia

        # Combinar com prior se disponível
        if media_cluster is not None and media_cluster > 0:
            # Peso proporcional ao número de dados (mais dados = menos prior)
            peso_dados = min(0.8, n * 0.15)  # 3 períodos = 45%, 6 períodos = 80%
            demanda = peso_dados * demanda + (1 - peso_dados) * media_cluster

        # Ajustar desvio pela incerteza (série curta)
        fator_incerteza = 1.5 - (n * 0.1)  # 3 períodos = 1.2, 6 períodos = 0.9
        desvio = desvio_base * max(1.0, fator_incerteza)

        return demanda, desvio, {
            'metodo_usado': f'wma_adaptativo_{tendencia}',
            'confianca': 'baixa',
            'num_periodos': n,
            'tendencia_detectada': tendencia,
            'fator_tendencia': round(fator_tendencia, 3),
            'fator_seguranca_recomendado': 1.5
        }

    @staticmethod
    def calcular_demanda_serie_media(
        vendas: List[float]
    ) -> Tuple[float, float, Dict]:
        """
        Método para séries médias (7-11 períodos)
        Usa métodos completos mas sem sazonalidade (ciclo incompleto)

        Args:
            vendas: Lista de vendas (7-11 valores)

        Returns:
            (demanda, desvio, metadata)
        """
        n = len(vendas)
        vendas_array = np.array(vendas)

        # Verificar intermitência
        zeros_pct = (vendas_array == 0).sum() / n
        if zeros_pct > 0.3:
            # Usar TSB completo
            demanda, desvio = DemandCalculator.calcular_demanda_tsb(vendas)
            return demanda, desvio, {
                'metodo_usado': 'tsb',
                'confianca': 'media',
                'num_periodos': n,
                'zeros_pct': round(zeros_pct * 100, 1),
                'fator_seguranca_recomendado': 1.3
            }

        # Calcular CV para determinar variabilidade
        media = np.mean(vendas_array)
        desvio_base = np.std(vendas_array, ddof=1)
        cv = desvio_base / media if media > 0 else 0.5

        # Detectar tendência com regressão
        X = np.arange(n)
        slope, intercept, r_value, _, _ = stats.linregress(X, vendas_array)

        tendencia_significativa = abs(r_value) > 0.5  # Correlação moderada

        if tendencia_significativa:
            # Usar regressão para projetar
            demanda = intercept + slope * n  # Próximo período
            demanda = max(0, demanda)
            metodo = 'tendencia'
        elif cv > 0.5:
            # Alta variabilidade - usar EMA
            demanda, desvio = DemandCalculator.calcular_demanda_ema(vendas)
            return demanda, desvio, {
                'metodo_usado': 'ema',
                'confianca': 'media',
                'num_periodos': n,
                'cv': round(cv, 2),
                'fator_seguranca_recomendado': 1.3
            }
        else:
            # Demanda estável - usar WMA
            demanda, desvio = DemandCalculator.calcular_demanda_wma(vendas)
            return demanda, desvio, {
                'metodo_usado': 'wma',
                'confianca': 'media',
                'num_periodos': n,
                'cv': round(cv, 2),
                'fator_seguranca_recomendado': 1.2
            }

        # Calcular desvio dos resíduos para tendência
        y_pred = intercept + slope * X
        residuos = vendas_array - y_pred
        desvio = np.std(residuos, ddof=2) if n > 2 else desvio_base

        return demanda, desvio, {
            'metodo_usado': metodo,
            'confianca': 'media',
            'num_periodos': n,
            'r_squared': round(r_value ** 2, 3),
            'slope': round(slope, 3),
            'fator_seguranca_recomendado': 1.2
        }

    @staticmethod
    def calcular_demanda_adaptativa(
        vendas: List[float],
        granularidade: str = 'mensal',
        media_cluster: Optional[float] = None
    ) -> Tuple[float, float, Dict]:
        """
        MÉTODO PRINCIPAL ADAPTATIVO
        Seleciona automaticamente a melhor estratégia baseada no tamanho da série

        Args:
            vendas: Lista de vendas
            granularidade: 'diario', 'semanal' ou 'mensal'
            media_cluster: Média de produtos similares (para prior bayesiano)

        Returns:
            (demanda, desvio, metadata)
        """
        n = len(vendas)

        # Definir limiares baseados na granularidade
        if granularidade == 'diario':
            # Diário: precisa de mais dados para padrões
            limiar_muito_curta = 7    # < 1 semana
            limiar_curta = 30         # < 1 mês
            limiar_media = 90         # < 3 meses
        elif granularidade == 'semanal':
            limiar_muito_curta = 2    # < 2 semanas
            limiar_curta = 8          # < 2 meses
            limiar_media = 26         # < 6 meses
        else:  # mensal
            limiar_muito_curta = 2    # < 2 meses
            limiar_curta = 6          # < 6 meses
            limiar_media = 11         # < 1 ano

        # Selecionar método baseado no tamanho
        if n <= limiar_muito_curta:
            demanda, desvio, metadata = DemandCalculator.calcular_demanda_serie_muito_curta(
                vendas, media_cluster
            )
            metadata['categoria_serie'] = 'muito_curta'

        elif n <= limiar_curta:
            demanda, desvio, metadata = DemandCalculator.calcular_demanda_serie_curta(
                vendas, media_cluster
            )
            metadata['categoria_serie'] = 'curta'

        elif n <= limiar_media:
            demanda, desvio, metadata = DemandCalculator.calcular_demanda_serie_media(vendas)
            metadata['categoria_serie'] = 'media'

        else:
            # Série longa - usar método inteligente completo
            demanda, desvio, metadata = DemandCalculator.calcular_demanda_inteligente(vendas)
            metadata['categoria_serie'] = 'longa'
            metadata['fator_seguranca_recomendado'] = 1.0

        metadata['granularidade'] = granularidade
        metadata['tamanho_serie'] = n

        return demanda, desvio, metadata

    @staticmethod
    def calcular_demanda_diaria_unificada(
        vendas_diarias: List[float],
        dias_periodo: int,
        granularidade_exibicao: str = 'mensal',
        media_cluster_diaria: Optional[float] = None
    ) -> Tuple[float, float, Dict]:
        """
        MÉTODO UNIFICADO PARA CONSISTÊNCIA ENTRE GRANULARIDADES

        Calcula demanda usando SEMPRE a base diária, garantindo que:
        - Semanal e mensal produzam resultados proporcionais aos dias
        - Os 6 métodos inteligentes são aplicados na série diária
        - Fatores sazonais podem ser aplicados depois na exibição

        Fluxo:
        1. Recebe histórico DIÁRIO (730 dias = 2 anos)
        2. Aplica os 6 métodos na série diária
        3. Calcula demanda_diaria_base
        4. Multiplica pelos dias do período solicitado

        Args:
            vendas_diarias: Lista de vendas diárias (ordenadas do mais antigo ao mais recente)
            dias_periodo: Número de dias do período de previsão (ex: 181 para Jan-Jun, 217 para Sem 1-31)
            granularidade_exibicao: 'diario', 'semanal' ou 'mensal' (para metadata)
            media_cluster_diaria: Média diária de produtos similares (para prior bayesiano)

        Returns:
            (demanda_total_periodo, desvio_total, metadata)

        Exemplo:
            # Para Jan-Jun 2026 (181 dias)
            demanda, desvio, meta = calcular_demanda_diaria_unificada(historico_diario, 181, 'mensal')

            # Para Semana 1-31 2026 (217 dias)
            demanda, desvio, meta = calcular_demanda_diaria_unificada(historico_diario, 217, 'semanal')

            # Ambos devem ser proporcionais: demanda_semanal / demanda_mensal ≈ 217/181 = 1.20
        """
        if not vendas_diarias or len(vendas_diarias) == 0:
            return 0.0, 0.0, {
                'metodo_usado': 'sem_dados',
                'confianca': 'muito_baixa',
                'demanda_diaria_base': 0,
                'dias_periodo': dias_periodo,
                'granularidade_exibicao': granularidade_exibicao
            }

        # 1. Calcular demanda diária usando método adaptativo
        demanda_diaria, desvio_diario, metadata = DemandCalculator.calcular_demanda_adaptativa(
            vendas=vendas_diarias,
            granularidade='diario',
            media_cluster=media_cluster_diaria
        )

        # 2. Calcular demanda total para o período
        demanda_total = demanda_diaria * dias_periodo

        # 3. Calcular desvio total (propagação de incerteza)
        # Desvio do período = desvio_diario * sqrt(dias)
        import math
        desvio_total = desvio_diario * math.sqrt(dias_periodo)

        # 4. Enriquecer metadata
        metadata['calculo_unificado'] = True
        metadata['demanda_diaria_base'] = round(demanda_diaria, 4)
        metadata['desvio_diario_base'] = round(desvio_diario, 4)
        metadata['dias_periodo'] = dias_periodo
        metadata['granularidade_exibicao'] = granularidade_exibicao
        metadata['demanda_total_calculada'] = round(demanda_total, 2)

        # 5. Calcular métricas auxiliares para validação
        if granularidade_exibicao == 'mensal':
            # Converter para equivalente mensal (30 dias)
            metadata['demanda_mensal_equivalente'] = round(demanda_diaria * 30, 2)
            metadata['num_meses_equivalente'] = round(dias_periodo / 30, 2)
        elif granularidade_exibicao == 'semanal':
            # Converter para equivalente semanal (7 dias)
            metadata['demanda_semanal_equivalente'] = round(demanda_diaria * 7, 2)
            metadata['num_semanas_equivalente'] = round(dias_periodo / 7, 2)

        return demanda_total, desvio_total, metadata

    @staticmethod
    def validar_consistencia_granularidades(
        demanda_mensal: float,
        dias_mensal: int,
        demanda_semanal: float,
        dias_semanal: int,
        tolerancia_pct: float = 0.10
    ) -> Dict:
        """
        Valida se as previsões mensal e semanal são consistentes.

        Args:
            demanda_mensal: Demanda total prevista no período mensal
            dias_mensal: Dias no período mensal (ex: 181 para Jan-Jun)
            demanda_semanal: Demanda total prevista no período semanal
            dias_semanal: Dias no período semanal (ex: 217 para Sem 1-31)
            tolerancia_pct: Tolerância aceitável (padrão: 10%)

        Returns:
            Dict com:
            - consistente: bool
            - demanda_diaria_mensal: float
            - demanda_diaria_semanal: float
            - diferenca_pct: float
            - alerta: str (se inconsistente)
        """
        # Calcular demanda diária equivalente de cada granularidade
        demanda_diaria_mensal = demanda_mensal / dias_mensal if dias_mensal > 0 else 0
        demanda_diaria_semanal = demanda_semanal / dias_semanal if dias_semanal > 0 else 0

        # Calcular diferença percentual
        if demanda_diaria_mensal > 0:
            diferenca_pct = abs(demanda_diaria_semanal - demanda_diaria_mensal) / demanda_diaria_mensal
        elif demanda_diaria_semanal > 0:
            diferenca_pct = abs(demanda_diaria_semanal - demanda_diaria_mensal) / demanda_diaria_semanal
        else:
            diferenca_pct = 0

        consistente = diferenca_pct <= tolerancia_pct

        resultado = {
            'consistente': consistente,
            'demanda_diaria_mensal': round(demanda_diaria_mensal, 4),
            'demanda_diaria_semanal': round(demanda_diaria_semanal, 4),
            'diferenca_pct': round(diferenca_pct * 100, 2),
            'tolerancia_pct': tolerancia_pct * 100
        }

        if not consistente:
            resultado['alerta'] = (
                f"ATENÇÃO: Diferença de {resultado['diferenca_pct']:.1f}% entre granularidades. "
                f"Demanda diária via mensal: {demanda_diaria_mensal:.2f}, "
                f"via semanal: {demanda_diaria_semanal:.2f}. "
                f"Verifique sazonalidade ou padrões específicos."
            )

        return resultado

    # =====================================================
    # MÉTODOS ORIGINAIS (mantidos para compatibilidade)
    # =====================================================

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
