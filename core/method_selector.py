"""
Módulo de Seleção de Método Estatístico
Analisa características da série temporal e seleciona o melhor método de previsão
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats


class MethodSelector:
    """
    Analisa características da demanda e seleciona o melhor método de previsão.

    Usado tanto para (Loja + SKU) quanto para (CD + SKU)
    """

    def __init__(self, vendas: List[float], datas: List = None):
        """
        Inicializa o seletor

        Args:
            vendas: Série temporal de vendas (já corrigida por stockouts)
            datas: Lista de datas (opcional, para análise sazonal)
        """
        self.vendas = np.array(vendas)
        self.datas = datas
        self.caracteristicas = {}

    def analisar_caracteristicas(self) -> Dict:
        """
        Analisa todas as características da série temporal

        Returns:
            Dicionário com características:
            - intermittence: Análise de intermitência
            - trend: Análise de tendência
            - seasonality: Análise de sazonalidade
            - volatility: Análise de volatilidade
            - data_volume: Volume de dados
        """
        self.caracteristicas = {
            'intermittence': self._analisar_intermitencia(),
            'trend': self._analisar_tendencia(),
            'seasonality': self._analisar_sazonalidade(),
            'volatility': self._analisar_volatilidade(),
            'data_volume': self._analisar_volume_dados()
        }
        return self.caracteristicas

    def _analisar_intermitencia(self) -> Dict:
        """
        Analisa intermitência da demanda (proporção de zeros)

        Returns:
            Dicionário com métricas de intermitência
        """
        n = len(self.vendas)
        zeros = np.sum(self.vendas == 0)
        zero_ratio = zeros / n if n > 0 else 0

        # Calcular ADI (Average Demand Interval) se houver demandas
        demandas_nao_zero = self.vendas[self.vendas > 0]
        if len(demandas_nao_zero) > 1:
            # Calcular intervalos entre demandas
            indices_nao_zero = np.where(self.vendas > 0)[0]
            intervalos = np.diff(indices_nao_zero)
            adi = np.mean(intervalos) if len(intervalos) > 0 else 1
        else:
            adi = n  # Só uma ou nenhuma demanda

        # Calcular CV² (coeficiente de variação ao quadrado) das demandas
        if len(demandas_nao_zero) > 1:
            cv2 = (np.std(demandas_nao_zero) / np.mean(demandas_nao_zero)) ** 2
        else:
            cv2 = 0

        # Classificar tipo de demanda (Syntetos-Boylan classification)
        if adi < 1.32:
            if cv2 < 0.49:
                category = 'smooth'  # Suave - SES ou Média Móvel
            else:
                category = 'erratic'  # Errática - SES com alpha baixo
        else:
            if cv2 < 0.49:
                category = 'intermittent'  # Intermitente - Croston
            else:
                category = 'lumpy'  # Irregular - SBA ou TSB

        return {
            'zero_ratio': zero_ratio,
            'adi': adi,
            'cv2': cv2,
            'category': category,
            'is_intermittent': zero_ratio > 0.3 or category in ['intermittent', 'lumpy']
        }

    def _analisar_tendencia(self) -> Dict:
        """
        Analisa presença de tendência na série

        Returns:
            Dicionário com métricas de tendência
        """
        n = len(self.vendas)

        if n < 3:
            return {
                'has_trend': False,
                'strength': 0,
                'type': 'none',
                'slope': 0,
                'p_value': 1.0
            }

        # Regressão linear para detectar tendência
        x = np.arange(n)
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, self.vendas)

        # Força da tendência (R²)
        r_squared = r_value ** 2

        # Determinar tipo de tendência
        if p_value < 0.1 and abs(r_squared) > 0.3:
            has_trend = True
            if slope > 0:
                trend_type = 'increasing'
            else:
                trend_type = 'decreasing'
        else:
            has_trend = False
            trend_type = 'none'

        return {
            'has_trend': has_trend,
            'strength': r_squared,
            'type': trend_type,
            'slope': slope,
            'p_value': p_value
        }

    def _analisar_sazonalidade(self) -> Dict:
        """
        Analisa presença de sazonalidade na série

        Returns:
            Dicionário com métricas de sazonalidade
        """
        n = len(self.vendas)

        # Precisa de pelo menos 2 ciclos para detectar sazonalidade
        if n < 24:  # Menos de 2 anos
            return {
                'has_seasonality': False,
                'period': 12,
                'strength': 0,
                'indices': None
            }

        # Calcular autocorrelação para período 12 (mensal -> anual)
        try:
            # Normalizar dados
            vendas_norm = (self.vendas - np.mean(self.vendas)) / (np.std(self.vendas) + 1e-10)

            # Autocorrelação no lag 12
            if n > 12:
                acf_12 = np.corrcoef(vendas_norm[:-12], vendas_norm[12:])[0, 1]
            else:
                acf_12 = 0

            # Verificar se autocorrelação é significativa
            # Limite de significância aproximado: 2/sqrt(n)
            limite = 2 / np.sqrt(n)
            has_seasonality = abs(acf_12) > limite and abs(acf_12) > 0.3

            # Calcular índices sazonais se houver sazonalidade
            if has_seasonality and self.datas is not None:
                indices = self._calcular_indices_sazonais()
            else:
                indices = None

        except:
            has_seasonality = False
            acf_12 = 0
            indices = None

        return {
            'has_seasonality': has_seasonality,
            'period': 12,
            'strength': abs(acf_12) if not np.isnan(acf_12) else 0,
            'indices': indices
        }

    def _calcular_indices_sazonais(self) -> List[float]:
        """
        Calcula índices sazonais mensais

        Returns:
            Lista com 12 índices sazonais
        """
        if self.datas is None:
            return [1.0] * 12

        # Agrupar por mês
        vendas_por_mes = {m: [] for m in range(1, 13)}
        for i, data in enumerate(self.datas):
            mes = data.month
            vendas_por_mes[mes].append(self.vendas[i])

        # Calcular média geral
        media_geral = np.mean(self.vendas)

        # Calcular índice para cada mês
        indices = []
        for mes in range(1, 13):
            if vendas_por_mes[mes] and media_geral > 0:
                media_mes = np.mean(vendas_por_mes[mes])
                indice = media_mes / media_geral
            else:
                indice = 1.0
            indices.append(indice)

        return indices

    def _analisar_volatilidade(self) -> Dict:
        """
        Analisa volatilidade da série

        Returns:
            Dicionário com métricas de volatilidade
        """
        # Remover zeros para cálculo de CV
        vendas_positivas = self.vendas[self.vendas > 0]

        if len(vendas_positivas) < 2:
            return {
                'cv': 0,
                'category': 'low',
                'std': 0,
                'mean': 0
            }

        media = np.mean(vendas_positivas)
        std = np.std(vendas_positivas)
        cv = std / media if media > 0 else 0

        # Classificar volatilidade
        if cv < 0.3:
            category = 'low'
        elif cv < 0.7:
            category = 'medium'
        else:
            category = 'high'

        return {
            'cv': cv,
            'category': category,
            'std': std,
            'mean': media
        }

    def _analisar_volume_dados(self) -> Dict:
        """
        Analisa volume de dados disponíveis

        Returns:
            Dicionário com métricas de volume
        """
        n = len(self.vendas)

        if n < 6:
            category = 'insufficient'
        elif n < 12:
            category = 'minimal'
        elif n < 24:
            category = 'adequate'
        else:
            category = 'abundant'

        return {
            'n_periods': n,
            'category': category,
            'can_use_seasonal': n >= 24,
            'can_use_trend': n >= 6
        }

    def recomendar_metodo(self) -> Dict:
        """
        Recomenda o melhor método de previsão baseado nas características

        Returns:
            Dicionário com:
            - metodo: Nome do método recomendado
            - confianca: Confiança na recomendação (0-1)
            - razao: Explicação da escolha
            - alternativas: Lista de métodos alternativos
            - caracteristicas: Resumo das características
        """
        if not self.caracteristicas:
            self.analisar_caracteristicas()

        intermittence = self.caracteristicas['intermittence']
        trend = self.caracteristicas['trend']
        seasonality = self.caracteristicas['seasonality']
        volatility = self.caracteristicas['volatility']
        data_volume = self.caracteristicas['data_volume']

        # Árvore de decisão para seleção do método

        # 1. Dados insuficientes
        if data_volume['category'] == 'insufficient':
            return {
                'metodo': 'Média Móvel Simples',
                'confianca': 0.4,
                'razao': 'Dados insuficientes para métodos mais complexos',
                'alternativas': [],
                'caracteristicas': self._resumo_caracteristicas()
            }

        # 2. Demanda intermitente (muitos zeros)
        if intermittence['is_intermittent']:
            if intermittence['category'] == 'lumpy':
                metodo = 'TSB'
                razao = 'Demanda irregular com alta intermitência'
            elif intermittence['category'] == 'intermittent':
                metodo = 'Croston'
                razao = 'Demanda intermitente com baixa variabilidade'
            else:
                metodo = 'SBA'
                razao = 'Demanda intermitente'

            return {
                'metodo': metodo,
                'confianca': 0.75,
                'razao': razao,
                'alternativas': ['Croston', 'SBA', 'TSB'],
                'caracteristicas': self._resumo_caracteristicas()
            }

        # 3. Com sazonalidade e tendência
        if seasonality['has_seasonality'] and trend['has_trend']:
            return {
                'metodo': 'Holt-Winters',
                'confianca': 0.85,
                'razao': 'Série com tendência e padrão sazonal',
                'alternativas': ['Média Móvel Sazonal', 'Holt'],
                'caracteristicas': self._resumo_caracteristicas()
            }

        # 4. Apenas sazonalidade
        if seasonality['has_seasonality']:
            if data_volume['n_periods'] >= 24:
                return {
                    'metodo': 'Holt-Winters',
                    'confianca': 0.80,
                    'razao': 'Série com padrão sazonal identificado',
                    'alternativas': ['Média Móvel Sazonal', 'Suavização Exponencial Simples'],
                    'caracteristicas': self._resumo_caracteristicas()
                }
            else:
                return {
                    'metodo': 'Média Móvel Sazonal',
                    'confianca': 0.65,
                    'razao': 'Indícios de sazonalidade com dados limitados',
                    'alternativas': ['Suavização Exponencial Simples'],
                    'caracteristicas': self._resumo_caracteristicas()
                }

        # 5. Apenas tendência
        if trend['has_trend']:
            if trend['strength'] > 0.6:
                return {
                    'metodo': 'Regressão Linear',
                    'confianca': 0.80,
                    'razao': f"Tendência {trend['type']} forte (R²={trend['strength']:.2f})",
                    'alternativas': ['Holt', 'Suavização Exponencial Simples'],
                    'caracteristicas': self._resumo_caracteristicas()
                }
            else:
                return {
                    'metodo': 'Holt',
                    'confianca': 0.70,
                    'razao': f"Tendência {trend['type']} moderada",
                    'alternativas': ['Regressão Linear', 'Suavização Exponencial Simples'],
                    'caracteristicas': self._resumo_caracteristicas()
                }

        # 6. Série estável (sem tendência nem sazonalidade)
        if volatility['category'] == 'low':
            return {
                'metodo': 'Média Móvel Simples',
                'confianca': 0.75,
                'razao': 'Série estável com baixa volatilidade',
                'alternativas': ['Suavização Exponencial Simples'],
                'caracteristicas': self._resumo_caracteristicas()
            }
        elif volatility['category'] == 'medium':
            return {
                'metodo': 'Suavização Exponencial Simples',
                'confianca': 0.70,
                'razao': 'Série estável com volatilidade moderada',
                'alternativas': ['Média Móvel Simples', 'Holt'],
                'caracteristicas': self._resumo_caracteristicas()
            }
        else:
            return {
                'metodo': 'Suavização Exponencial Simples',
                'confianca': 0.60,
                'razao': 'Série com alta volatilidade - usar alpha baixo',
                'alternativas': ['Média Móvel Simples'],
                'caracteristicas': self._resumo_caracteristicas()
            }

    def _resumo_caracteristicas(self) -> Dict:
        """
        Retorna resumo formatado das características

        Returns:
            Dicionário resumido
        """
        return {
            'intermitente': self.caracteristicas['intermittence']['is_intermittent'],
            'tem_tendencia': self.caracteristicas['trend']['has_trend'],
            'tipo_tendencia': self.caracteristicas['trend']['type'],
            'tem_sazonalidade': self.caracteristicas['seasonality']['has_seasonality'],
            'volatilidade': self.caracteristicas['volatility']['category'],
            'n_periodos': self.caracteristicas['data_volume']['n_periods']
        }


def selecionar_metodo(vendas: List[float], datas: List = None) -> Dict:
    """
    Função auxiliar para selecionar método

    Args:
        vendas: Série temporal de vendas
        datas: Lista de datas (opcional)

    Returns:
        Dicionário com recomendação de método
    """
    selector = MethodSelector(vendas, datas)
    return selector.recomendar_metodo()
