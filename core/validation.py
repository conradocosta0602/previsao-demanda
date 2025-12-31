"""
Módulo de Validação Robusta de Entrada

Valida séries temporais antes de serem usadas nos modelos de previsão,
prevenindo erros e previsões incorretas.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional


class ValidationError(Exception):
    """Exceção personalizada para erros de validação"""
    def __init__(self, code: str, message: str, suggestion: str = None):
        self.code = code
        self.message = message
        self.suggestion = suggestion
        super().__init__(f"[{code}] {message}" + (f" Sugestão: {suggestion}" if suggestion else ""))


def validate_series_length(data: List[float], min_length: int = 3, series_name: str = "série") -> None:
    """
    Valida se a série tem comprimento mínimo necessário

    Args:
        data: Série temporal
        min_length: Comprimento mínimo exigido
        series_name: Nome da série (para mensagens de erro)

    Raises:
        ValidationError: Se a série for muito curta
    """
    if len(data) < min_length:
        raise ValidationError(
            code="ERR001",
            message=f"Série muito curta: {len(data)} período(s). Mínimo necessário: {min_length}.",
            suggestion=f"Forneça pelo menos {min_length} períodos de histórico para {series_name}."
        )


def validate_positive_values(data: List[float], allow_zeros: bool = True) -> None:
    """
    Valida se os valores são não-negativos

    Args:
        data: Série temporal
        allow_zeros: Se True, permite zeros (demanda intermitente)

    Raises:
        ValidationError: Se houver valores negativos ou zeros não permitidos
    """
    data_array = np.array(data)

    # Verificar valores negativos
    negative_count = np.sum(data_array < 0)
    if negative_count > 0:
        negative_indices = np.where(data_array < 0)[0]
        raise ValidationError(
            code="ERR002",
            message=f"Encontrados {negative_count} valor(es) negativo(s) nas posições: {list(negative_indices[:5])}...",
            suggestion="Verifique os dados de entrada. Demanda não pode ser negativa."
        )

    # Verificar zeros (se não permitidos)
    if not allow_zeros:
        zero_count = np.sum(data_array == 0)
        if zero_count > 0:
            raise ValidationError(
                code="ERR003",
                message=f"Encontrados {zero_count} valor(es) zero. Este método não suporta demanda intermitente.",
                suggestion="Use o método TSB (Teunter-Syntetos-Babai) ou AUTO para demanda intermitente."
            )


def detect_outliers(data: List[float], method: str = 'iqr', threshold: float = 3.0) -> Tuple[List[int], Dict]:
    """
    Detecta outliers na série temporal

    Args:
        data: Série temporal
        method: Método de detecção ('iqr' ou 'zscore')
        threshold: Limite para considerar outlier (z-score: 3.0, IQR: 1.5)

    Returns:
        Tupla (índices dos outliers, estatísticas)
    """
    data_array = np.array(data)
    outlier_indices = []
    stats = {}

    if method == 'zscore':
        # Método Z-score: |valor - média| / desvio_padrão > threshold
        mean = np.mean(data_array)
        std = np.std(data_array)

        if std > 0:
            z_scores = np.abs((data_array - mean) / std)
            outlier_indices = np.where(z_scores > threshold)[0].tolist()

            stats = {
                'method': 'Z-Score',
                'threshold': threshold,
                'mean': mean,
                'std': std,
                'outlier_count': len(outlier_indices)
            }

    elif method == 'iqr':
        # Método IQR (Interquartile Range)
        q1 = np.percentile(data_array, 25)
        q3 = np.percentile(data_array, 75)
        iqr = q3 - q1

        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr

        outlier_mask = (data_array < lower_bound) | (data_array > upper_bound)
        outlier_indices = np.where(outlier_mask)[0].tolist()

        stats = {
            'method': 'IQR',
            'threshold': threshold,
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'outlier_count': len(outlier_indices)
        }

    return outlier_indices, stats


def check_missing_data(data: List[float]) -> Tuple[bool, List[int]]:
    """
    Verifica se há dados faltantes (None, NaN)

    Args:
        data: Série temporal

    Returns:
        Tupla (tem_faltantes, índices dos valores faltantes)
    """
    missing_indices = []

    for i, value in enumerate(data):
        if value is None or (isinstance(value, float) and np.isnan(value)):
            missing_indices.append(i)

    return len(missing_indices) > 0, missing_indices


def validate_data_type(data: List[float]) -> None:
    """
    Valida se os dados são do tipo correto (numéricos)

    Args:
        data: Série temporal

    Raises:
        ValidationError: Se houver valores não numéricos
    """
    for i, value in enumerate(data):
        if value is not None and not isinstance(value, (int, float, np.number)):
            raise ValidationError(
                code="ERR004",
                message=f"Valor não numérico encontrado na posição {i}: {value} (tipo: {type(value).__name__})",
                suggestion="Todos os valores devem ser numéricos (int ou float)."
            )


def validate_series(
    data: List[float],
    min_length: int = 3,
    allow_zeros: bool = True,
    check_outliers: bool = True,
    outlier_method: str = 'iqr',
    outlier_threshold: float = 1.5,
    series_name: str = "série"
) -> Dict:
    """
    Validação completa de uma série temporal

    Args:
        data: Série temporal
        min_length: Comprimento mínimo exigido
        allow_zeros: Se permite zeros (demanda intermitente)
        check_outliers: Se deve detectar outliers
        outlier_method: Método de detecção de outliers ('iqr' ou 'zscore')
        outlier_threshold: Limite para outliers
        series_name: Nome da série (para mensagens)

    Returns:
        Dicionário com resultados da validação

    Raises:
        ValidationError: Se alguma validação crítica falhar
    """
    validation_results = {
        'valid': True,
        'warnings': [],
        'errors': [],
        'outliers': [],
        'statistics': {}
    }

    try:
        # 1. Validar tipo de dados
        validate_data_type(data)

        # 2. Verificar dados faltantes
        has_missing, missing_indices = check_missing_data(data)
        if has_missing:
            raise ValidationError(
                code="ERR005",
                message=f"Encontrados {len(missing_indices)} valor(es) faltante(s) nas posições: {missing_indices[:5]}...",
                suggestion="Preencha os valores faltantes usando interpolação ou remova os períodos."
            )

        # 3. Validar comprimento
        validate_series_length(data, min_length, series_name)

        # 4. Validar valores positivos
        validate_positive_values(data, allow_zeros)

        # 5. Detectar outliers (warning, não erro)
        if check_outliers:
            outlier_indices, outlier_stats = detect_outliers(data, outlier_method, outlier_threshold)

            if len(outlier_indices) > 0:
                outlier_values = [data[i] for i in outlier_indices]
                validation_results['warnings'].append({
                    'code': 'WARN001',
                    'message': f"Detectados {len(outlier_indices)} outlier(s) usando {outlier_method.upper()}",
                    'outlier_indices': outlier_indices,
                    'outlier_values': outlier_values,
                    'suggestion': "Considere remover ou substituir outliers se forem eventos não recorrentes (promoções, Black Friday)."
                })
                validation_results['outliers'] = outlier_indices
                validation_results['statistics']['outliers'] = outlier_stats

        # 6. Estatísticas gerais
        data_array = np.array(data)
        validation_results['statistics']['general'] = {
            'length': len(data),
            'mean': float(np.mean(data_array)),
            'std': float(np.std(data_array)),
            'min': float(np.min(data_array)),
            'max': float(np.max(data_array)),
            'zeros_count': int(np.sum(data_array == 0)),
            'zeros_percentage': float(100 * np.sum(data_array == 0) / len(data_array))
        }

    except ValidationError as e:
        validation_results['valid'] = False
        validation_results['errors'].append({
            'code': e.code,
            'message': e.message,
            'suggestion': e.suggestion
        })
        raise

    return validation_results


def validate_forecast_inputs(
    data: List[float],
    horizon: int,
    method_name: str,
    min_periods_by_method: Dict[str, int] = None
) -> Dict:
    """
    Valida entradas específicas para previsão

    Args:
        data: Série temporal
        horizon: Horizonte de previsão
        method_name: Nome do método de previsão
        min_periods_by_method: Mínimo de períodos por método

    Returns:
        Resultados da validação

    Raises:
        ValidationError: Se validação falhar
    """
    # Mínimo de períodos por método
    if min_periods_by_method is None:
        min_periods_by_method = {
            'SMA': 3,
            'WMA': 3,
            'EMA': 3,
            'Regressão com Tendência': 6,
            'Decomposição Sazonal': 24,  # 2 ciclos sazonais
            'TSB': 3,
            'AUTO': 3
        }

    # Validar horizonte
    if horizon < 1:
        raise ValidationError(
            code="ERR006",
            message=f"Horizonte inválido: {horizon}. Deve ser >= 1.",
            suggestion="Defina um horizonte de previsão positivo (ex: 6 para 6 meses)."
        )

    if horizon > 36:
        raise ValidationError(
            code="ERR007",
            message=f"Horizonte muito longo: {horizon} períodos. Máximo recomendado: 36.",
            suggestion="Previsões muito longas tendem a ser imprecisas. Limite a 36 períodos."
        )

    # Obter mínimo para o método
    min_periods = min_periods_by_method.get(method_name, 3)

    # Validação específica por método
    if method_name == 'Decomposição Sazonal' and len(data) < 24:
        raise ValidationError(
            code="ERR008",
            message=f"Decomposição Sazonal requer pelo menos 24 períodos (2 ciclos). Disponível: {len(data)}",
            suggestion="Use AUTO para selecionar automaticamente EMA como fallback, ou forneça mais dados históricos."
        )

    # Validação geral
    return validate_series(
        data=data,
        min_length=min_periods,
        allow_zeros=(method_name in ['TSB', 'AUTO']),
        series_name=f"método {method_name}"
    )
