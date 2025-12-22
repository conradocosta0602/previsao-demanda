"""
Módulo de Modelos de Previsão
Implementa diversos métodos estatísticos para previsão de demanda
"""

import numpy as np
from typing import List, Tuple, Optional
from scipy import stats
from sklearn.linear_model import LinearRegression


class BaseForecaster:
    """Classe base para todos os modelos de previsão"""

    def __init__(self):
        self.fitted = False
        self.data = None
        self.params = {}

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
    Bom para séries estáveis sem tendência ou sazonalidade.
    """

    def __init__(self, window: int = 3):
        """
        Args:
            window: Número de períodos para a média móvel
        """
        super().__init__()
        self.window = window

    def fit(self, data: List[float]) -> 'SimpleMovingAverage':
        """
        Ajusta o modelo aos dados

        Args:
            data: Série temporal de dados históricos
        """
        self.data = np.array(data)
        self.fitted = True
        self.params = {'window': self.window}
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
            # Usar os últimos 'window' valores
            janela = dados_temp[-self.window:]
            previsao = np.mean(janela)
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

    def __init__(self, season_period: int = 12, alpha: float = 0.3,
                 beta: float = 0.1, gamma: float = 0.1,
                 seasonal: str = 'additive'):
        """
        Args:
            season_period: Período da sazonalidade (12 para mensal)
            alpha: Fator de suavização do nível
            beta: Fator de suavização da tendência
            gamma: Fator de suavização da sazonalidade
            seasonal: Tipo de sazonalidade ('additive' ou 'multiplicative')
        """
        super().__init__()
        self.season_period = season_period
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.seasonal = seasonal
        self.level = None
        self.trend = None
        self.seasonals = None

    def fit(self, data: List[float]) -> 'HoltWinters':
        """
        Ajusta o modelo aos dados
        """
        self.data = np.array(data)
        n = len(self.data)
        m = self.season_period

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
        self.params = {
            'alpha': self.alpha, 'beta': self.beta, 'gamma': self.gamma,
            'season_period': self.season_period, 'seasonal': self.seasonal,
            'level': self.level, 'trend': self.trend, 'seasonals': self.seasonals
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


# Mapeamento de métodos disponíveis
METODOS = {
    'Média Móvel Simples': SimpleMovingAverage,
    'Suavização Exponencial Simples': SimpleExponentialSmoothing,
    'Holt': HoltMethod,
    'Holt-Winters': HoltWinters,
    'Croston': CrostonMethod,
    'SBA': lambda: CrostonMethod(variant='sba'),
    'TSB': lambda: CrostonMethod(variant='tsb'),
    'Regressão Linear': LinearRegressionForecast,
    'Média Móvel Sazonal': SeasonalMovingAverage
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
