"""
Módulo de Métricas de Acurácia

Calcula métricas de precisão das previsões usando validação cruzada temporal (walk-forward).
Implementa WMAPE (Weighted MAPE - recomendado), MAPE (legacy) e BIAS (Mean Error).
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from core.forecasting_models import get_modelo


def calculate_wmape(actual: List[float], predicted: List[float], min_value: float = 2.0) -> float:
    """
    Calcula WMAPE (Weighted Mean Absolute Percentage Error)

    WMAPE é superior ao MAPE tradicional para dados de varejo pois:
    - Pondera erros pelo volume de vendas
    - Produtos de alto volume têm peso proporcional
    - Evita distorções de produtos de baixo volume

    WMAPE = Σ|actual - predicted| / Σ|actual| * 100

    Args:
        actual: Valores reais
        predicted: Valores previstos
        min_value: Valor mínimo para considerar no cálculo (default: 2.0)
                  Períodos com actual < min_value são ignorados.
                  Threshold de 2.0 é ideal para dados semanais.

    Returns:
        WMAPE em percentual (0-100+), ou None se não houver dados válidos

    Exemplo:
        Produto A: real=1, prev=2  → erro=1
        Produto B: real=100, prev=101 → erro=1
        MAPE: (100% + 1%) / 2 = 50.5% (errado!)
        WMAPE: (1+1) / (1+100) = 1.98% (correto!)
    """
    actual_arr = np.array(actual)
    predicted_arr = np.array(predicted)

    # Filtrar apenas períodos onde houve venda significativa
    mask = actual_arr >= min_value

    if not mask.any():
        return None

    actual_filtered = actual_arr[mask]
    predicted_filtered = predicted_arr[mask]

    # Calcular WMAPE: soma dos erros absolutos / soma dos valores reais
    total_error = np.sum(np.abs(actual_filtered - predicted_filtered))
    total_actual = np.sum(np.abs(actual_filtered))

    if total_actual == 0:
        return None

    wmape = (total_error / total_actual) * 100

    return float(wmape)


def calculate_mape(actual: List[float], predicted: List[float], min_value: float = 2.0) -> float:
    """
    Calcula MAPE (Mean Absolute Percentage Error)

    ⚠️ DEPRECADO: Use calculate_wmape() para melhor precisão em varejo.
    Mantido apenas para compatibilidade com código legado.

    MAPE tem limitações para dados de varejo:
    - Não pondera por volume (produto de 1 un tem mesmo peso que 100 un)
    - Pode ser distorcido por produtos de baixo volume
    - WMAPE é superior para 99% dos casos

    MAPE = (1/n) * Σ |actual - predicted| / |actual| * 100

    Args:
        actual: Valores reais
        predicted: Valores previstos
        min_value: Valor mínimo para considerar no cálculo (default: 2.0)

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
        - wmape: WMAPE (Weighted MAPE - recomendado)
        - mape: MAPE (legacy - mantido para compatibilidade)
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
    wmape = calculate_wmape(actuals, predictions)  # NOVA métrica principal
    mape = calculate_mape(actuals, predictions)    # Legacy (compatibilidade)
    bias = calculate_bias(actuals, predictions)
    mae = calculate_mae(actuals, predictions)

    # Se métricas são None (sem dados válidos), usar 999.9
    if wmape is None:
        wmape = 999.9
    if mape is None:
        mape = 999.9

    return {
        'wmape': wmape,  # Métrica principal (ponderada)
        'mape': mape,    # Legacy (não ponderada)
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

    # Interpretar WMAPE (métrica principal)
    wmape = results['wmape']
    if wmape < 10:
        wmape_interpretation = "Excelente"
    elif wmape < 20:
        wmape_interpretation = "Boa"
    elif wmape < 30:
        wmape_interpretation = "Aceitável"
    elif wmape < 50:
        wmape_interpretation = "Fraca"
    else:
        wmape_interpretation = "Muito fraca"

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
        'wmape': wmape,
        'wmape_interpretation': wmape_interpretation,
        'mape': results['mape'],  # Mantido para compatibilidade
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

WMAPE (Erro Percentual Ponderado): {metrics['wmape']:.1f}%
  → Classificação: {metrics['wmape_interpretation']}
  → Interpretação: Erro ponderado por volume de {metrics['wmape']:.1f}%

BIAS (Viés Direcional): {metrics['bias']:+.2f} unidades
  → {metrics['bias_interpretation']}
  → Ação: {metrics['bias_action']}

MAE (Erro Absoluto): {metrics['mae']:.2f} unidades
  → Erro médio por período

Validações: {metrics['n_folds']} testes realizados
"""
    return report
