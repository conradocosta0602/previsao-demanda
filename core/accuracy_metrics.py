"""
Módulo de Métricas de Acurácia

Calcula métricas de precisão das previsões usando validação cruzada temporal (walk-forward).
Implementa MAPE (Mean Absolute Percentage Error) e BIAS (Mean Error).
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from core.forecasting_models import get_modelo


def calculate_mape(actual: List[float], predicted: List[float], min_value: float = 0.5) -> float:
    """
    Calcula MAPE (Mean Absolute Percentage Error)

    IMPORTANTE: Para dados semanais/diários, ignora períodos onde actual = 0
    pois não faz sentido calcular erro percentual quando não houve venda real.

    MAPE = (1/n) * Σ |actual - predicted| / |actual| * 100

    Args:
        actual: Valores reais
        predicted: Valores previstos
        min_value: Valor mínimo para considerar no cálculo (default: 0.5)
                  Períodos com actual < min_value são ignorados

    Returns:
        MAPE em percentual (0-100+), ou None se não houver dados válidos
    """
    actual_arr = np.array(actual)
    predicted_arr = np.array(predicted)

    # Filtrar apenas períodos onde houve venda significativa
    # Isso evita divisões por zero e MAPEs absurdos
    mask = actual_arr >= min_value

    if not mask.any():
        # Se não houver nenhum período com venda, retornar None ou valor padrão
        return None

    actual_filtered = actual_arr[mask]
    predicted_filtered = predicted_arr[mask]

    # Calcular erro percentual absoluto apenas nos períodos válidos
    ape = np.abs((actual_filtered - predicted_filtered) / actual_filtered) * 100

    # Retornar média
    return float(np.mean(ape))


def calculate_bias(actual: List[float], predicted: List[float]) -> float:
    """
    Calcula BIAS (Mean Error)

    BIAS = (1/n) * Σ (predicted - actual)

    Valores:
    - BIAS > 0: Tendência de SUPERESTIMAR (excesso de estoque)
    - BIAS < 0: Tendência de SUBESTIMAR (risco de ruptura)
    - BIAS ≈ 0: Sem viés sistemático

    Args:
        actual: Valores reais
        predicted: Valores previstos

    Returns:
        BIAS (pode ser positivo ou negativo)
    """
    actual_arr = np.array(actual)
    predicted_arr = np.array(predicted)

    # BIAS = média dos erros (com sinal)
    errors = predicted_arr - actual_arr
    return float(np.mean(errors))


def calculate_mae(actual: List[float], predicted: List[float]) -> float:
    """
    Calcula MAE (Mean Absolute Error)

    MAE = (1/n) * Σ |actual - predicted|

    Args:
        actual: Valores reais
        predicted: Valores previstos

    Returns:
        MAE (sempre positivo)
    """
    actual_arr = np.array(actual)
    predicted_arr = np.array(predicted)

    # MAE = média dos erros absolutos
    errors = np.abs(actual_arr - predicted_arr)
    return float(np.mean(errors))


def walk_forward_validation(
    data: List[float],
    model_name: str,
    horizon: int = 1,
    min_train_size: int = 6,
    **model_params
) -> Dict:
    """
    Validação cruzada temporal (walk-forward validation)

    Divide a série em múltiplos treino/teste sequenciais:
    - Treino: [0:t]
    - Teste: [t:t+horizon]
    - Repete avançando janela

    Args:
        data: Série temporal completa
        model_name: Nome do modelo ('SMA', 'WMA', 'AUTO', etc)
        horizon: Horizonte de previsão
        min_train_size: Tamanho mínimo de treino
        **model_params: Parâmetros do modelo

    Returns:
        Dicionário com:
        - mape: MAPE médio
        - bias: BIAS médio
        - mae: MAE médio
        - n_folds: Número de validações
        - actuals: Valores reais usados
        - predictions: Valores previstos
    """
    n = len(data)

    if n < min_train_size + horizon:
        raise ValueError(
            f"Dados insuficientes para validação. "
            f"Necessário: {min_train_size + horizon}, disponível: {n}"
        )

    actuals = []
    predictions = []

    # Walk-forward: começar com min_train_size, prever horizon, avançar 1
    for t in range(min_train_size, n - horizon + 1):
        # Dados de treino: [0:t]
        train_data = data[:t]

        # Criar e treinar modelo
        try:
            model = get_modelo(model_name, **model_params)
            model.fit(train_data)

            # Prever próximos 'horizon' períodos
            forecast = model.predict(horizon)

            # Valores reais correspondentes: [t:t+horizon]
            actual_values = data[t:t + horizon]

            # Armazenar apenas o primeiro valor previsto vs real
            # (evita sobreposição em validações subsequentes)
            actuals.append(actual_values[0])
            predictions.append(forecast[0])

        except Exception as e:
            # Se falhar, pular essa validação
            continue

    if len(actuals) == 0:
        raise ValueError("Nenhuma validação bem-sucedida. Verifique os dados e parâmetros.")

    # Calcular métricas
    mape = calculate_mape(actuals, predictions)
    bias = calculate_bias(actuals, predictions)
    mae = calculate_mae(actuals, predictions)

    # Se MAPE é None (sem dados válidos), usar 999.9 para indicar métrica não calculável
    if mape is None:
        mape = 999.9

    return {
        'mape': mape,
        'bias': bias,
        'mae': mae,
        'n_folds': len(actuals),
        'actuals': actuals,
        'predictions': predictions
    }


def evaluate_model_accuracy(
    data: List[float],
    model_name: str,
    horizon: int = 1,
    **model_params
) -> Dict:
    """
    Avalia acurácia de um modelo usando walk-forward validation

    Args:
        data: Série temporal
        model_name: Nome do modelo
        horizon: Horizonte de previsão
        **model_params: Parâmetros do modelo

    Returns:
        Dicionário com métricas e interpretação
    """
    # Executar validação
    results = walk_forward_validation(data, model_name, horizon, **model_params)

    # Interpretar MAPE
    mape = results['mape']
    if mape < 10:
        mape_interpretation = "Excelente"
    elif mape < 20:
        mape_interpretation = "Boa"
    elif mape < 30:
        mape_interpretation = "Aceitável"
    elif mape < 50:
        mape_interpretation = "Fraca"
    else:
        mape_interpretation = "Muito fraca"

    # Interpretar BIAS
    bias = results['bias']
    bias_pct = (bias / np.mean(results['actuals'])) * 100 if np.mean(results['actuals']) > 0 else 0

    if abs(bias_pct) < 5:
        bias_interpretation = "Sem viés significativo"
        bias_action = "Modelo equilibrado, não requer ajuste"
    elif bias > 0:
        bias_interpretation = f"Superestimando em {abs(bias):.1f} unidades ({abs(bias_pct):.1f}%)"
        bias_action = "Reduzir previsão para evitar excesso de estoque"
    else:
        bias_interpretation = f"Subestimando em {abs(bias):.1f} unidades ({abs(bias_pct):.1f}%)"
        bias_action = "Aumentar previsão para evitar rupturas"

    return {
        'mape': mape,
        'mape_interpretation': mape_interpretation,
        'bias': bias,
        'bias_interpretation': bias_interpretation,
        'bias_action': bias_action,
        'mae': results['mae'],
        'n_folds': results['n_folds'],
        'model_name': model_name
    }


def format_accuracy_report(metrics: Dict) -> str:
    """
    Formata relatório de acurácia para exibição

    Args:
        metrics: Dicionário com métricas

    Returns:
        String formatada
    """
    report = f"""
Acurácia do Modelo: {metrics['model_name']}
{'=' * 50}

MAPE (Erro Percentual): {metrics['mape']:.1f}%
  → Classificação: {metrics['mape_interpretation']}
  → Interpretação: Em média, o erro é {metrics['mape']:.1f}% do valor real

BIAS (Viés Direcional): {metrics['bias']:+.2f} unidades
  → {metrics['bias_interpretation']}
  → Ação: {metrics['bias_action']}

MAE (Erro Absoluto): {metrics['mae']:.2f} unidades
  → Erro médio por período

Validações: {metrics['n_folds']} testes realizados
"""
    return report
