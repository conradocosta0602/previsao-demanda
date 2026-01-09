"""
Módulo de Detecção Automática de Outliers

Analisa automaticamente a série temporal e decide:
1. Se há outliers significativos
2. Qual método usar para detectá-los (IQR ou Z-Score)
3. Como tratá-los (remover, substituir pela mediana, ou manter)

Similar ao AUTO dos métodos estatísticos, mas para tratamento de outliers.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats


class AutoOutlierDetector:
    """
    Detector automático de outliers

    Analisa características da série e decide automaticamente a melhor
    estratégia de detecção e tratamento de outliers.
    """

    def __init__(self):
        self.data = None
        self.outlier_indices = []
        self.method_used = None
        self.treatment_applied = None
        self.cleaned_data = None
        self.decision_log = {}

    def analyze_and_clean(self, data: List[float]) -> Dict:
        """
        Analisa a série e limpa outliers automaticamente

        Args:
            data: Série temporal original

        Returns:
            Dicionário com:
            - cleaned_data: Série limpa
            - outliers_detected: Índices dos outliers
            - method_used: Método de detecção usado
            - treatment: Como foram tratados
            - reason: Razão das decisões
            - confidence: Confiança na decisão (0-1)
            - original_values: Valores originais dos outliers
            - replaced_values: Valores após tratamento
        """
        self.data = np.array(data)
        n = len(self.data)

        # 1. ANÁLISE DE CARACTERÍSTICAS DA SÉRIE
        characteristics = self._analyze_characteristics()

        # 2. DECISÃO AUTOMÁTICA: USAR DETECÇÃO DE OUTLIERS?
        should_detect, reason = self._should_detect_outliers(characteristics)

        if not should_detect:
            return {
                'cleaned_data': list(self.data),
                'outliers_detected': [],
                'outliers_count': 0,
                'method_used': 'NONE',
                'treatment': 'NONE',
                'reason': reason,
                'confidence': 1.0,
                'original_values': [],
                'replaced_values': [],
                'characteristics': characteristics
            }

        # 3. ESCOLHER MÉTODO DE DETECÇÃO
        method, method_reason = self._choose_detection_method(characteristics)

        # 4. DETECTAR OUTLIERS
        outlier_indices, outlier_stats = self._detect_outliers(method)

        if len(outlier_indices) == 0:
            return {
                'cleaned_data': list(self.data),
                'outliers_detected': [],
                'outliers_count': 0,
                'method_used': method,
                'treatment': 'NONE',
                'reason': f"Método {method} não detectou outliers significativos",
                'confidence': 0.9,
                'original_values': [],
                'replaced_values': [],
                'characteristics': characteristics,
                'stats': outlier_stats
            }

        # 5. DECIDIR TRATAMENTO
        treatment, treatment_reason = self._choose_treatment(
            outlier_indices,
            characteristics
        )

        # 6. APLICAR TRATAMENTO
        cleaned_data, original_values, replaced_values = self._apply_treatment(
            outlier_indices,
            treatment
        )

        # 7. CALCULAR CONFIANÇA NA DECISÃO
        confidence = self._calculate_confidence(
            outlier_indices,
            characteristics,
            outlier_stats
        )

        # 8. MONTAR RESULTADO
        return {
            'cleaned_data': list(cleaned_data),
            'outliers_detected': outlier_indices,
            'outliers_count': len(outlier_indices),
            'method_used': method,
            'treatment': treatment,
            'reason': f"{method_reason}. {treatment_reason}",
            'confidence': confidence,
            'original_values': original_values,
            'replaced_values': replaced_values,
            'characteristics': characteristics,
            'stats': outlier_stats
        }

    def _analyze_characteristics(self) -> Dict:
        """Analisa características estatísticas da série"""
        data = self.data
        n = len(data)

        mean = np.mean(data)
        std = np.std(data)
        median = np.median(data)

        # Coeficiente de Variação
        cv = (std / mean) if mean > 0 else 0

        # Assimetria (skewness)
        skewness = stats.skew(data)

        # Curtose (kurtosis) - detecta caudas pesadas
        kurtosis = stats.kurtosis(data)

        # Percentual de zeros
        zeros_pct = 100 * np.sum(data == 0) / n

        # Range relativo
        data_range = np.max(data) - np.min(data)
        relative_range = (data_range / mean) if mean > 0 else 0

        # Detectar picos (valores muito acima da média)
        threshold_high = mean + 2 * std
        high_values = np.sum(data > threshold_high)
        high_values_pct = 100 * high_values / n

        return {
            'n': n,
            'mean': float(mean),
            'std': float(std),
            'median': float(median),
            'cv': float(cv),
            'skewness': float(skewness),
            'kurtosis': float(kurtosis),
            'zeros_pct': float(zeros_pct),
            'relative_range': float(relative_range),
            'high_values_count': int(high_values),
            'high_values_pct': float(high_values_pct)
        }

    def _should_detect_outliers(self, chars: Dict) -> Tuple[bool, str]:
        """
        Decide se deve aplicar detecção de outliers

        Retorna (should_detect, reason)
        """
        # Critério 1: Série muito curta (< 6 períodos) - não detectar
        if chars['n'] < 6:
            return False, "Série muito curta (< 6 períodos), detecção não confiável"

        # Critério 2: Demanda intermitente (>30% zeros) - não detectar
        # Zeros são normais, não outliers
        if chars['zeros_pct'] > 30:
            return False, f"Demanda intermitente ({chars['zeros_pct']:.1f}% zeros), zeros são esperados"

        # Critério 3 (PRIORITÁRIO): Alta assimetria ou curtose - DETECTAR
        # Indica distribuição com caudas pesadas (outliers prováveis)
        # IMPORTANTE: Este critério deve vir ANTES do CV baixo!
        # Mesmo séries "estáveis" (CV baixo) podem ter outliers extremos
        if abs(chars['skewness']) > 1.5 or chars['kurtosis'] > 3:
            return True, f"Assimetria/curtose elevada (skew={chars['skewness']:.2f}, kurt={chars['kurtosis']:.2f}), outliers prováveis"

        # Critério 4: Baixa variabilidade (CV < 0.15) - não detectar
        # Série muito estável, outliers improváveis
        # NOTA: Este critério só se aplica se não houver skewness/kurtosis elevados
        if chars['cv'] < 0.15:
            return False, f"Série muito estável (CV={chars['cv']:.2f}), outliers improváveis"

        # Critério 5: Muitos valores altos (>10% acima de mean+2*std) - DETECTAR
        if chars['high_values_pct'] > 10:
            return True, f"{chars['high_values_pct']:.1f}% dos valores muito acima da média, outliers prováveis"

        # Critério 6: Range relativo muito grande - DETECTAR
        if chars['relative_range'] > 2.5:
            return True, f"Amplitude relativa alta ({chars['relative_range']:.2f}), outliers prováveis"

        # Critério 7: Variabilidade moderada a alta - DETECTAR
        # Se CV > 0.4 e não é intermitente, pode ter outliers
        if chars['cv'] > 0.4 and chars['zeros_pct'] < 30:
            return True, f"Alta variabilidade (CV={chars['cv']:.2f}), outliers prováveis"

        # Padrão: não detectar se nenhum critério forte
        return False, "Série não apresenta sinais claros de outliers"

    def _choose_detection_method(self, chars: Dict) -> Tuple[str, str]:
        """
        Escolhe automaticamente o melhor método de detecção

        Retorna (method, reason)
        """
        # Método IQR (Interquartile Range)
        # - Robusto a outliers extremos
        # - Bom para distribuições assimétricas
        # - Não assume normalidade

        # Método Z-Score
        # - Assume distribuição normal
        # - Sensível a outliers extremos
        # - Bom para distribuições simétricas

        # Decisão baseada em assimetria
        if abs(chars['skewness']) > 1.0:
            # Distribuição assimétrica -> IQR
            return 'IQR', "Método IQR selecionado (distribuição assimétrica)"

        # Decisão baseada em curtose
        if chars['kurtosis'] > 3:
            # Caudas pesadas -> IQR (mais robusto)
            return 'IQR', "Método IQR selecionado (caudas pesadas)"

        # Decisão baseada em tamanho
        if chars['n'] < 12:
            # Poucos dados -> IQR (mais conservador)
            return 'IQR', "Método IQR selecionado (série curta)"

        # Padrão: Z-Score para distribuições aproximadamente normais
        return 'ZSCORE', "Método Z-Score selecionado (distribuição aproximadamente normal)"

    def _detect_outliers(self, method: str) -> Tuple[List[int], Dict]:
        """Detecta outliers usando o método escolhido"""
        from core.validation import detect_outliers

        if method == 'IQR':
            # IQR com threshold 1.5 (padrão estatístico)
            outlier_indices, stats_dict = detect_outliers(
                list(self.data),
                method='iqr',
                threshold=1.5
            )
        else:  # ZSCORE
            # Z-Score com threshold 3.0 (99.7% intervalo de confiança)
            outlier_indices, stats_dict = detect_outliers(
                list(self.data),
                method='zscore',
                threshold=3.0
            )

        return outlier_indices, stats_dict

    def _choose_treatment(
        self,
        outlier_indices: List[int],
        chars: Dict
    ) -> Tuple[str, str]:
        """
        Escolhe automaticamente como tratar os outliers

        Opções:
        - REMOVE: Remove outliers (reduz série)
        - REPLACE_MEDIAN: Substitui pela mediana
        - REPLACE_MEAN: Substitui pela média
        - WINSORIZE: Limita aos percentis 5-95

        Retorna (treatment, reason)
        """
        n_outliers = len(outlier_indices)
        n_total = chars['n']
        outlier_pct = 100 * n_outliers / n_total

        # Critério 1: Muitos outliers (>20%) - SUBSTITUIR por mediana
        # Remover muitos pontos encurtaria demais a série
        if outlier_pct > 20:
            return 'REPLACE_MEDIAN', f"{outlier_pct:.1f}% outliers, substituindo por mediana para preservar comprimento"

        # Critério 2: Poucos outliers (<10%) em série longa (>12) - REMOVER
        # Série tem dados suficientes mesmo removendo
        if outlier_pct < 10 and n_total > 12:
            return 'REMOVE', f"Apenas {outlier_pct:.1f}% outliers em série longa, removendo para limpeza total"

        # Critério 3: Outliers moderados (10-20%) - SUBSTITUIR por mediana
        # Mediana é robusta a outliers
        if 10 <= outlier_pct <= 20:
            return 'REPLACE_MEDIAN', f"{outlier_pct:.1f}% outliers, substituindo por mediana (robusto)"

        # Critério 4: Série curta (<12) - SUBSTITUIR por mediana
        # Não queremos encurtar mais ainda
        if n_total < 12:
            return 'REPLACE_MEDIAN', f"Série curta ({n_total} períodos), substituindo por mediana para preservar comprimento"

        # Padrão: SUBSTITUIR por mediana (mais seguro)
        return 'REPLACE_MEDIAN', "Substituindo por mediana (estratégia conservadora)"

    def _apply_treatment(
        self,
        outlier_indices: List[int],
        treatment: str
    ) -> Tuple[np.ndarray, List[float], List[float]]:
        """
        Aplica o tratamento escolhido

        Retorna (cleaned_data, original_values, replaced_values)
        """
        cleaned = self.data.copy()
        original_values = [float(self.data[i]) for i in outlier_indices]
        replaced_values = []

        if treatment == 'REMOVE':
            # Remover outliers (criar máscara)
            mask = np.ones(len(self.data), dtype=bool)
            mask[outlier_indices] = False
            cleaned = self.data[mask]
            replaced_values = []  # Valores removidos, não substituídos

        elif treatment == 'REPLACE_MEDIAN':
            # Substituir por mediana (robusta a outliers)
            # Calcular mediana SEM os outliers
            mask = np.ones(len(self.data), dtype=bool)
            mask[outlier_indices] = False
            median_value = np.median(self.data[mask])

            for idx in outlier_indices:
                cleaned[idx] = median_value
                replaced_values.append(float(median_value))

        elif treatment == 'REPLACE_MEAN':
            # Substituir por média (menos robusto, mas útil em alguns casos)
            mask = np.ones(len(self.data), dtype=bool)
            mask[outlier_indices] = False
            mean_value = np.mean(self.data[mask])

            for idx in outlier_indices:
                cleaned[idx] = mean_value
                replaced_values.append(float(mean_value))

        return cleaned, original_values, replaced_values

    def _calculate_confidence(
        self,
        outlier_indices: List[int],
        chars: Dict,
        outlier_stats: Dict
    ) -> float:
        """
        Calcula confiança na decisão de tratamento de outliers

        Retorna valor entre 0 e 1
        """
        confidence = 0.5  # Base

        # Fator 1: Quantidade de outliers
        outlier_pct = 100 * len(outlier_indices) / chars['n']
        if outlier_pct < 5:
            confidence += 0.2  # Poucos outliers -> alta confiança
        elif outlier_pct > 25:
            confidence -= 0.1  # Muitos outliers -> menor confiança

        # Fator 2: Assimetria e curtose
        if abs(chars['skewness']) > 2 or chars['kurtosis'] > 5:
            confidence += 0.2  # Forte evidência de outliers

        # Fator 3: Tamanho da série
        if chars['n'] >= 24:
            confidence += 0.1  # Mais dados -> mais confiança
        elif chars['n'] < 6:
            confidence -= 0.2  # Poucos dados -> menos confiança

        # Limitar entre 0 e 1
        return max(0.0, min(1.0, confidence))


def auto_clean_outliers(data: List[float]) -> Dict:
    """
    Função helper para limpeza automática de outliers

    Args:
        data: Série temporal

    Returns:
        Dicionário com série limpa e metadados
    """
    detector = AutoOutlierDetector()
    return detector.analyze_and_clean(data)
