"""
Módulo de Modelos de Previsão
Implementa diversos métodos estatísticos para previsão de demanda
"""

import numpy as np
from typing import List, Tuple, Optional
from scipy import stats
from sklearn.linear_model import LinearRegression
from core.validation import validate_forecast_inputs, ValidationError


class BaseForecaster:
    """Classe base para todos os modelos de previsão"""

    def __init__(self, auto_clean_outliers: bool = False):
        """
        Args:
            auto_clean_outliers: Se True, aplica detecção automática de outliers antes do fit
        """
        self.fitted = False
        self.data = None
        self.params = {}
        self.auto_clean_outliers = auto_clean_outliers
        self.outlier_info = None

    def _preprocess_data(self, data: List[float]) -> List[float]:
        """
        Pré-processa os dados antes do fit

        Se auto_clean_outliers=True, detecta e trata outliers automaticamente
        """
        if not self.auto_clean_outliers:
            # Não aplicar detecção, mas inicializar outlier_info como None
            self.outlier_info = None
            return data

        # Aplicar detecção automática de outliers
        from core.outlier_detector import auto_clean_outliers

        result = auto_clean_outliers(data)
        self.outlier_info = {
            'outliers_detected': result['outliers_detected'],
            'outliers_count': result['outliers_count'],
            'method_used': result['method_used'],
            'treatment': result['treatment'],
            'reason': result['reason'],
            'confidence': result['confidence'],
            'original_values': result.get('original_values', []),
            'replaced_values': result.get('replaced_values', [])
        }

        # Adicionar info de outliers aos params (SEMPRE, mesmo se não detectou)
        # Isso garante que outlier_detection está presente em self.params
        self.params['outlier_detection'] = self.outlier_info

        return result['cleaned_data']

    def fit(self, data: List[float]) -> 'BaseForecaster':
        """Ajusta o modelo aos dados"""
        raise NotImplementedError

    def predict(self, horizon: int) -> List[float]:
        """Gera previsões para o horizonte especificado"""
        raise NotImplementedError

    def get_params(self) -> dict:
        """Retorna os parâmetros do modelo"""
        return self.params


class SimpleMovingAverage(BaseForecaster):
    """
    Média Móvel Simples (SMA)

    Calcula a média dos últimos N períodos para fazer previsões.
    Implementa janela adaptativa: N = max(3, total_períodos / 2)
    Bom para séries estáveis sem tendência ou sazonalidade.
    """

    def __init__(self, window: int = None, auto_clean_outliers: bool = False):
        """
        Args:
            window: Número de períodos para a média móvel.
                   Se None, usa janela adaptativa: max(3, len(data) / 2)
            auto_clean_outliers: Se True, detecta e trata outliers automaticamente
        """
        super().__init__(auto_clean_outliers=auto_clean_outliers)
        self.window = window
        self.adaptive_window = None

    def fit(self, data: List[float]) -> 'SimpleMovingAverage':
        """
        Ajusta o modelo aos dados

        Args:
            data: Série temporal de dados históricos
        """
        # Pré-processar dados (detectar outliers se habilitado)
        cleaned_data = self._preprocess_data(data)
        self.data = np.array(cleaned_data)

        # Calcular janela adaptativa conforme documentação
        # N = max(3, total_períodos / 2)
        if self.window is None:
            total_periodos = len(self.data)
            self.adaptive_window = max(3, total_periodos // 2)
        else:
            self.adaptive_window = self.window

        self.fitted = True

        # Preservar outlier_detection se já foi adicionado
        outlier_info = self.params.get('outlier_detection')

        self.params = {
            'window': self.adaptive_window,
            'window_type': 'adaptive' if self.window is None else 'fixed'
        }

        # Re-adicionar outlier_detection
        if outlier_info is not None:
            self.params['outlier_detection'] = outlier_info

        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões

        Args:
            horizon: Número de períodos futuros para prever

        Returns:
            Lista com previsões
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        previsoes = []
        dados_temp = list(self.data)

        for _ in range(horizon):
            # Usar os últimos 'adaptive_window' valores
            janela = dados_temp[-self.adaptive_window:]
            previsao = np.mean(janela)
            previsoes.append(max(0, previsao))  # Não permitir negativos
            dados_temp.append(previsao)

        return previsoes


class WeightedMovingAverage(BaseForecaster):
    """
    Média Móvel Ponderada (WMA)

    Atribui pesos lineares crescentes aos períodos, dando maior importância
    aos dados mais recentes. Mais responsivo a mudanças que SMA.
    Implementa janela adaptativa: N = max(3, total_períodos / 2)
    """

    def __init__(self, window: int = None, auto_clean_outliers: bool = False):
        """
        Args:
            window: Número de períodos para a média móvel ponderada.
                   Se None, usa janela adaptativa: max(3, len(data) / 2)
            auto_clean_outliers: Se True, detecta e trata outliers automaticamente
        """
        super().__init__(auto_clean_outliers=auto_clean_outliers)
        self.window = window
        self.adaptive_window = None

    def fit(self, data: List[float]) -> 'WeightedMovingAverage':
        """
        Ajusta o modelo aos dados

        Args:
            data: Série temporal de dados históricos
        """
        # Pré-processar dados (detectar outliers se habilitado)
        cleaned_data = self._preprocess_data(data)
        self.data = np.array(cleaned_data)

        # Calcular janela adaptativa conforme documentação
        # N = max(3, total_períodos / 2)
        if self.window is None:
            total_periodos = len(self.data)
            self.adaptive_window = max(3, total_periodos // 2)
        else:
            self.adaptive_window = self.window

        self.fitted = True

        # Preservar outlier_detection se já foi adicionado
        outlier_info = self.params.get('outlier_detection')

        self.params = {
            'window': self.adaptive_window,
            'window_type': 'adaptive' if self.window is None else 'fixed'
        }

        # Re-adicionar outlier_detection
        if outlier_info is not None:
            self.params['outlier_detection'] = outlier_info

        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões

        Args:
            horizon: Número de períodos futuros para prever

        Returns:
            Lista com previsões
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        previsoes = []
        dados_temp = list(self.data)

        for _ in range(horizon):
            # Usar os últimos 'adaptive_window' valores
            janela = dados_temp[-self.adaptive_window:]
            n = len(janela)

            # Pesos lineares crescentes: [1, 2, 3, ..., n]
            pesos = np.arange(1, n + 1)

            # WMA = Σ(Vi × Pi) / Σ(Pi)
            previsao = np.sum(janela * pesos) / np.sum(pesos)

            previsoes.append(max(0, previsao))  # Não permitir negativos
            dados_temp.append(previsao)

        return previsoes


class SimpleExponentialSmoothing(BaseForecaster):
    """
    Suavização Exponencial Simples (SES)

    Dá mais peso aos dados recentes usando um fator de suavização alpha.
    Bom para séries estáveis sem tendência.
    """

    def __init__(self, alpha: float = 0.3):
        """
        Args:
            alpha: Fator de suavização (0 < alpha < 1)
        """
        super().__init__()
        self.alpha = alpha
        self.level = None

    def fit(self, data: List[float]) -> 'SimpleExponentialSmoothing':
        """
        Ajusta o modelo aos dados

        Args:
            data: Série temporal de dados históricos
        """
        self.data = np.array(data)

        # Inicializar nível com primeiro valor
        self.level = self.data[0]

        # Atualizar nível para cada observação
        for obs in self.data[1:]:
            self.level = self.alpha * obs + (1 - self.alpha) * self.level

        self.fitted = True
        self.params = {'alpha': self.alpha, 'level': self.level}
        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões

        Args:
            horizon: Número de períodos futuros para prever

        Returns:
            Lista com previsões (todas iguais para SES)
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        # SES sempre prevê o último nível
        return [max(0, self.level)] * horizon


class HoltMethod(BaseForecaster):
    """
    Método de Holt (Suavização Exponencial Dupla)

    Captura tendência linear além do nível.
    Bom para séries com tendência.
    """

    def __init__(self, alpha: float = 0.3, beta: float = 0.1):
        """
        Args:
            alpha: Fator de suavização do nível
            beta: Fator de suavização da tendência
        """
        super().__init__()
        self.alpha = alpha
        self.beta = beta
        self.level = None
        self.trend = None

    def fit(self, data: List[float]) -> 'HoltMethod':
        """
        Ajusta o modelo aos dados
        """
        self.data = np.array(data)

        if len(self.data) < 2:
            raise ValueError("Necessário pelo menos 2 observações para Holt")

        # Inicialização
        self.level = self.data[0]
        self.trend = self.data[1] - self.data[0]

        # Atualização
        for obs in self.data[1:]:
            level_anterior = self.level
            self.level = self.alpha * obs + (1 - self.alpha) * (self.level + self.trend)
            self.trend = self.beta * (self.level - level_anterior) + (1 - self.beta) * self.trend

        self.fitted = True
        self.params = {
            'alpha': self.alpha,
            'beta': self.beta,
            'level': self.level,
            'trend': self.trend
        }
        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        previsoes = []
        for h in range(1, horizon + 1):
            previsao = self.level + h * self.trend
            previsoes.append(max(0, previsao))

        return previsoes


class HoltWinters(BaseForecaster):
    """
    Método de Holt-Winters (Suavização Exponencial Tripla)

    Captura nível, tendência e sazonalidade.
    Bom para séries com tendência e padrão sazonal.
    """

    def __init__(self, season_period: int = None, alpha: float = 0.3,
                 beta: float = 0.1, gamma: float = 0.1,
                 seasonal: str = 'additive', auto_clean_outliers: bool = False):
        """
        Args:
            season_period: Período da sazonalidade (12 para mensal, None para auto-detectar)
            alpha: Fator de suavização do nível
            beta: Fator de suavização da tendência
            gamma: Fator de suavização da sazonalidade
            seasonal: Tipo de sazonalidade ('additive' ou 'multiplicative')
            auto_clean_outliers: Se True, detecta e trata outliers automaticamente
        """
        super().__init__(auto_clean_outliers=auto_clean_outliers)
        self.season_period = season_period
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.seasonal = seasonal
        self.level = None
        self.trend = None
        self.seasonals = None
        self.seasonality_detected = None

    def fit(self, data: List[float]) -> 'HoltWinters':
        """
        Ajusta o modelo aos dados
        """
        # Pré-processar dados (detectar outliers se habilitado)
        cleaned_data = self._preprocess_data(data)
        self.data = np.array(cleaned_data)
        n = len(self.data)

        # Auto-detectar período sazonal se não especificado
        if self.season_period is None:
            from core.seasonality_detector import detect_seasonality
            seasonality_info = detect_seasonality(list(self.data))
            self.seasonality_detected = seasonality_info

            if seasonality_info['has_seasonality']:
                m = seasonality_info['seasonal_period']
            else:
                # Fallback: usar 12 (mensal) como padrão
                m = 12
        else:
            m = self.season_period
            self.seasonality_detected = None

        self.season_period = m  # Atualizar com o valor detectado

        if n < 2 * m:
            # Se não tem dados suficientes para sazonalidade, usar Holt simples
            holt = HoltMethod(self.alpha, self.beta)
            holt.fit(data)
            self.level = holt.level
            self.trend = holt.trend
            self.seasonals = [0] * m if self.seasonal == 'additive' else [1] * m
            self.fitted = True
            self.params = {
                'alpha': self.alpha, 'beta': self.beta, 'gamma': self.gamma,
                'level': self.level, 'trend': self.trend, 'seasonals': self.seasonals
            }
            return self

        # Inicialização
        # Nível inicial: média do primeiro período sazonal
        self.level = np.mean(self.data[:m])

        # Tendência inicial: diferença média entre períodos
        self.trend = (np.mean(self.data[m:2*m]) - np.mean(self.data[:m])) / m

        # Sazonalidade inicial
        if self.seasonal == 'additive':
            self.seasonals = list(self.data[:m] - self.level)
        else:
            self.seasonals = list(self.data[:m] / self.level)

        # Atualização
        for i in range(m, n):
            obs = self.data[i]
            season_idx = i % m

            if self.seasonal == 'additive':
                level_anterior = self.level
                self.level = self.alpha * (obs - self.seasonals[season_idx]) + \
                            (1 - self.alpha) * (self.level + self.trend)
                self.trend = self.beta * (self.level - level_anterior) + \
                            (1 - self.beta) * self.trend
                self.seasonals[season_idx] = self.gamma * (obs - self.level) + \
                                             (1 - self.gamma) * self.seasonals[season_idx]
            else:
                level_anterior = self.level
                self.level = self.alpha * (obs / self.seasonals[season_idx]) + \
                            (1 - self.alpha) * (self.level + self.trend)
                self.trend = self.beta * (self.level - level_anterior) + \
                            (1 - self.beta) * self.trend
                self.seasonals[season_idx] = self.gamma * (obs / self.level) + \
                                             (1 - self.gamma) * self.seasonals[season_idx]

        self.fitted = True

        # Preservar outlier_detection se já foi adicionado
        outlier_info = self.params.get('outlier_detection')

        self.params = {
            'alpha': self.alpha, 'beta': self.beta, 'gamma': self.gamma,
            'season_period': self.season_period, 'seasonal': self.seasonal,
            'level': self.level, 'trend': self.trend, 'seasonals': self.seasonals
        }

        # Re-adicionar outlier_detection
        if outlier_info is not None:
            self.params['outlier_detection'] = outlier_info

        # Adicionar informação de sazonalidade detectada
        if self.seasonality_detected is not None:
            self.params['seasonality_detected'] = {
                'has_seasonality': self.seasonality_detected['has_seasonality'],
                'detected_period': self.seasonality_detected['seasonal_period'],
                'strength': self.seasonality_detected['strength'],
                'confidence': self.seasonality_detected['confidence'],
                'method': self.seasonality_detected['method'],
                'reason': self.seasonality_detected['reason']
            }

        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        previsoes = []
        n = len(self.data)

        for h in range(1, horizon + 1):
            season_idx = (n + h - 1) % self.season_period

            if self.seasonal == 'additive':
                previsao = self.level + h * self.trend + self.seasonals[season_idx]
            else:
                previsao = (self.level + h * self.trend) * self.seasonals[season_idx]

            previsoes.append(max(0, previsao))

        return previsoes


class CrostonMethod(BaseForecaster):
    """
    Método de Croston

    Para demanda intermitente (com muitos zeros).
    Separa a previsão em tamanho da demanda e intervalo entre demandas.
    """

    def __init__(self, alpha: float = 0.2, variant: str = 'original'):
        """
        Args:
            alpha: Fator de suavização
            variant: Variante do método ('original', 'sba', 'tsb')
        """
        super().__init__()
        self.alpha = alpha
        self.variant = variant
        self.demand_level = None
        self.interval_level = None

    def fit(self, data: List[float]) -> 'CrostonMethod':
        """
        Ajusta o modelo aos dados
        """
        self.data = np.array(data)

        # Separar demandas não-zero e intervalos
        demandas = []
        intervalos = []
        intervalo_atual = 0

        for obs in self.data:
            intervalo_atual += 1
            if obs > 0:
                demandas.append(obs)
                intervalos.append(intervalo_atual)
                intervalo_atual = 0

        if len(demandas) == 0:
            # Todos zeros
            self.demand_level = 0
            self.interval_level = float('inf')
        else:
            # Inicialização
            self.demand_level = demandas[0]
            self.interval_level = intervalos[0]

            # Atualização
            for i in range(1, len(demandas)):
                self.demand_level = self.alpha * demandas[i] + (1 - self.alpha) * self.demand_level
                self.interval_level = self.alpha * intervalos[i] + (1 - self.alpha) * self.interval_level

        self.fitted = True
        self.params = {
            'alpha': self.alpha,
            'variant': self.variant,
            'demand_level': self.demand_level,
            'interval_level': self.interval_level
        }
        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        if self.interval_level == 0 or self.interval_level == float('inf'):
            return [0] * horizon

        # Previsão = demanda_média / intervalo_médio
        if self.variant == 'original':
            previsao = self.demand_level / self.interval_level
        elif self.variant == 'sba':
            # Syntetos-Boylan Approximation
            previsao = (self.demand_level / self.interval_level) * (1 - self.alpha / 2)
        elif self.variant == 'tsb':
            # Teunter-Syntetos-Babai
            previsao = self.demand_level / self.interval_level
        else:
            previsao = self.demand_level / self.interval_level

        return [max(0, previsao)] * horizon


class LinearRegressionForecast(BaseForecaster):
    """
    Previsão por Regressão Linear

    Ajusta uma reta aos dados históricos e extrapola.
    Bom para tendências lineares claras.
    """

    def __init__(self):
        super().__init__()
        self.model = None
        self.intercept = None
        self.slope = None

    def fit(self, data: List[float]) -> 'LinearRegressionForecast':
        """
        Ajusta o modelo aos dados
        """
        self.data = np.array(data)
        n = len(self.data)

        # Preparar dados para regressão
        X = np.arange(n).reshape(-1, 1)
        y = self.data

        # Ajustar modelo
        self.model = LinearRegression()
        self.model.fit(X, y)

        self.intercept = self.model.intercept_
        self.slope = self.model.coef_[0]

        self.fitted = True
        self.params = {
            'intercept': self.intercept,
            'slope': self.slope
        }
        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        n = len(self.data)
        previsoes = []

        for h in range(1, horizon + 1):
            X_futuro = np.array([[n + h - 1]])
            previsao = self.model.predict(X_futuro)[0]
            previsoes.append(max(0, previsao))

        return previsoes


class AutoMethodSelector(BaseForecaster):
    """
    AUTO - Seleção Automática de Método

    Não é um método de previsão em si, mas uma estratégia que analisa
    automaticamente as características dos dados (intermitência, tendência,
    sazonalidade, volatilidade) e seleciona o melhor entre os 6 métodos
    estatísticos disponíveis.

    Métodos disponíveis para seleção:
    - SMA: Média Móvel Simples
    - WMA: Média Móvel Ponderada
    - EMA: Suavização Exponencial Simples
    - Regressão com Tendência: Para séries com crescimento/queda
    - Decomposição Sazonal: Para padrões sazonais
    - TSB: Para demanda intermitente
    """

    def __init__(self, sku: str = None, loja: str = None):
        super().__init__()
        self.selected_method = None
        self.method_name = None
        self.recommendation = None
        self.sku = sku
        self.loja = loja
        self.validation_result = None

    def fit(self, data: List[float]) -> 'AutoMethodSelector':
        """
        Analisa os dados e seleciona automaticamente o melhor método

        Args:
            data: Série temporal de dados históricos
        """
        # Validação robusta de entrada
        try:
            self.validation_result = validate_forecast_inputs(
                data=data,
                horizon=1,  # Validação inicial, horizonte será definido no predict
                method_name='AUTO'
            )
        except ValidationError as e:
            # Registrar falha no log
            from core.auto_logger import get_auto_logger
            logger = get_auto_logger()
            logger.log_selection(
                metodo_selecionado='N/A',
                confianca=0.0,
                razao='Validação falhou',
                caracteristicas={},
                sku=self.sku,
                loja=self.loja,
                sucesso=False,
                erro_msg=f"[{e.code}] {e.message}"
            )

            # Re-raise com contexto adicional
            raise ValidationError(
                code=e.code,
                message=f"Validação falhou para AUTO: {e.message}",
                suggestion=e.suggestion
            )

        # Evitar import circular
        from core.method_selector import MethodSelector
        from core.auto_logger import get_auto_logger

        self.data = np.array(data)

        # Usar MethodSelector para escolher o melhor método
        selector = MethodSelector(list(data))
        self.recommendation = selector.recomendar_metodo()

        self.method_name = self.recommendation['metodo']

        # Instanciar o método recomendado
        self.selected_method = get_modelo(self.method_name)
        self.selected_method.fit(data)

        self.fitted = True
        self.params = {
            'strategy': 'AUTO',
            'selected_method': self.method_name,
            'confidence': self.recommendation['confianca'],
            'reason': self.recommendation['razao'],
            'alternatives': self.recommendation.get('alternativas', []),
            'characteristics': self.recommendation.get('caracteristicas', {})
        }

        # Registrar seleção no log
        logger = get_auto_logger()
        logger.log_selection(
            metodo_selecionado=self.method_name,
            confianca=self.recommendation['confianca'],
            razao=self.recommendation['razao'],
            caracteristicas=self.recommendation.get('caracteristicas', {}),
            alternativas=self.recommendation.get('alternativas', []),
            data_stats=self.validation_result.get('statistics', {}).get('general', {}),
            sku=self.sku,
            loja=self.loja,
            sucesso=True
        )

        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões usando o método automaticamente selecionado

        Args:
            horizon: Número de períodos futuros para prever

        Returns:
            Lista com previsões
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        return self.selected_method.predict(horizon)


class SeasonalMovingAverage(BaseForecaster):
    """
    Média Móvel Sazonal

    Usa médias do mesmo período sazonal em anos anteriores.
    """

    def __init__(self, season_period: int = 12):
        super().__init__()
        self.season_period = season_period
        self.seasonal_means = None

    def fit(self, data: List[float]) -> 'SeasonalMovingAverage':
        """
        Ajusta o modelo calculando médias por período sazonal
        """
        self.data = np.array(data)
        n = len(self.data)

        # Calcular média para cada período sazonal
        self.seasonal_means = []
        for s in range(self.season_period):
            valores = [self.data[i] for i in range(s, n, self.season_period)]
            self.seasonal_means.append(np.mean(valores) if valores else 0)

        self.fitted = True
        self.params = {
            'season_period': self.season_period,
            'seasonal_means': self.seasonal_means
        }
        return self

    def predict(self, horizon: int = 1) -> List[float]:
        """
        Gera previsões
        """
        if not self.fitted:
            raise ValueError("Modelo não ajustado. Execute fit() primeiro.")

        n = len(self.data)
        previsoes = []

        for h in range(1, horizon + 1):
            season_idx = (n + h - 1) % self.season_period
            previsao = self.seasonal_means[season_idx]
            previsoes.append(max(0, previsao))

        return previsoes


class DecomposicaoSazonalMensal(BaseForecaster):
    """
    Decomposição Sazonal com Índices Mensais

    Usa a função calcular_demanda_sazonal do DemandCalculator
    que foi corrigida para capturar comportamento mensal real
    """

    def __init__(self):
        super().__init__()
        self.data = None

    def fit(self, data: List[float]) -> 'DecomposicaoSazonalMensal':
        """Ajusta o modelo"""
        self.data = np.array(data)
        return self

    def predict(self, n_periods: int = 1) -> List[float]:
        """
        Gera previsões usando o método sazonal corrigido

        Args:
            n_periods: Número de períodos a prever

        Returns:
            Lista com previsões
        """
        from core.demand_calculator import DemandCalculator

        previsoes = []
        vendas_temp = self.data.tolist()

        # Gerar previsões uma a uma (necessário para método sazonal)
        for _ in range(n_periods):
            demanda, _ = DemandCalculator.calcular_demanda_sazonal(vendas_temp)
            previsoes.append(demanda)
            vendas_temp.append(demanda)  # Adicionar para próxima previsão

        return previsoes


# Mapeamento de métodos disponíveis
# Nomenclatura conforme documentação oficial
# 6 métodos estatísticos + AUTO (estratégia de seleção automática)
METODOS = {
    # Métodos estatísticos oficiais (nomenclatura da documentação)
    'SMA': SimpleMovingAverage,
    'WMA': WeightedMovingAverage,
    'EMA': SimpleExponentialSmoothing,
    'Regressão com Tendência': LinearRegressionForecast,
    'Decomposição Sazonal': DecomposicaoSazonalMensal,  # Usando modelo corrigido!
    'TSB': lambda: CrostonMethod(variant='tsb'),

    # Estratégia de seleção automática (analisa dados e escolhe entre os 6 métodos)
    'AUTO': AutoMethodSelector,

    # Aliases para compatibilidade retroativa (serão convertidos pela função padronizar_metodo)
    'Média Móvel Simples': SimpleMovingAverage,
    'Média Móvel Ponderada': WeightedMovingAverage,
    'Suavização Exponencial Simples': SimpleExponentialSmoothing,
    'Holt': HoltMethod,
    'Holt-Winters': HoltWinters,
    'Regressão Linear': LinearRegressionForecast,
    'Média Móvel Sazonal': SeasonalMovingAverage,

    # Aliases para compatibilidade com ML Selector
    'MEDIA_MOVEL': SimpleMovingAverage,
    'EXPONENCIAL': SimpleExponentialSmoothing,
    'HOLT_WINTERS': DecomposicaoSazonalMensal,  # Usar nosso modelo sazonal corrigido!
    'REGRESSAO': LinearRegressionForecast
}


def get_modelo(nome: str, **kwargs):
    """
    Retorna uma instância do modelo especificado

    Args:
        nome: Nome do modelo
        **kwargs: Parâmetros adicionais para o modelo

    Returns:
        Instância do modelo
    """
    if nome not in METODOS:
        raise ValueError(f"Modelo '{nome}' não encontrado. Disponíveis: {list(METODOS.keys())}")

    modelo_class = METODOS[nome]

    if callable(modelo_class) and not isinstance(modelo_class, type):
        # É uma função lambda
        return modelo_class()
    else:
        return modelo_class(**kwargs)
