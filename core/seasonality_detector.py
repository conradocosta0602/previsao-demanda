"""
Módulo de Detecção Automática de Sazonalidade

Analisa séries temporais para detectar:
1. SE existe sazonalidade significativa
2. QUAL período sazonal (semanal=7, mensal=12, trimestral=4, etc)
3. QUÃO forte é o padrão sazonal

Usa decomposição sazonal + testes estatísticos.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose
import warnings
warnings.filterwarnings('ignore')


class SeasonalityDetector:
    """
    Detector automático de sazonalidade

    Testa múltiplos períodos sazonais e identifica o mais forte.
    """

    def __init__(self, data: List[float]):
        """
        Args:
            data: Série temporal
        """
        self.data = np.array(data)
        self.n = len(self.data)

    def detect(self) -> Dict:
        """
        Detecta sazonalidade automaticamente

        Returns:
            Dicionário com:
            - has_seasonality: bool
            - seasonal_period: int ou None
            - strength: float (0-1)
            - confidence: float (0-1)
            - method: str
            - reason: str
            - seasonal_indices: List[float] ou None
        """
        # Critério mínimo: pelo menos 2 ciclos completos
        if self.n < 8:
            return {
                'has_seasonality': False,
                'seasonal_period': None,
                'strength': 0.0,
                'confidence': 1.0,
                'method': 'INSUFFICIENT_DATA',
                'reason': f'Dados insuficientes ({self.n} períodos). Mínimo: 8',
                'seasonal_indices': None
            }

        # Testar múltiplos períodos sazonais
        candidate_periods = self._get_candidate_periods()

        if len(candidate_periods) == 0:
            return {
                'has_seasonality': False,
                'seasonal_period': None,
                'strength': 0.0,
                'confidence': 1.0,
                'method': 'NO_CANDIDATES',
                'reason': 'Nenhum período sazonal viável para testar',
                'seasonal_indices': None
            }

        # Avaliar cada período candidato
        results = []
        for period in candidate_periods:
            try:
                score = self._evaluate_period(period)
                results.append({
                    'period': period,
                    'score': score['strength'],
                    'pvalue': score['pvalue'],
                    'seasonal_indices': score['seasonal_indices']
                })
            except Exception:
                continue

        if len(results) == 0:
            return {
                'has_seasonality': False,
                'seasonal_period': None,
                'strength': 0.0,
                'confidence': 0.5,
                'method': 'DECOMPOSITION_FAILED',
                'reason': 'Falha ao decompor série para todos os períodos testados',
                'seasonal_indices': None
            }

        # Ordenar por score (força da sazonalidade) e depois por período (preferir menor)
        # Isso garante que se período 6 e 12 têm força similar, escolhe o 6
        results.sort(key=lambda x: (-x['score'], x['period']))
        best = results[0]

        # Se o melhor período é múltiplo de outro período com força similar,
        # preferir o período menor (mais fundamental)
        for result in results[1:]:
            # Se força é similar (diferença < 10%) e período atual é divisor do melhor
            # Evitar divisão por zero quando best['score'] é 0
            if best['score'] > 0 and (best['score'] - result['score']) / best['score'] < 0.10:
                if best['period'] % result['period'] == 0:
                    # Período menor com força similar - trocar
                    best = result
                    break

        # Decidir se há sazonalidade significativa
        # Critérios ajustados para lidar com períodos curtos e poucos ciclos
        #
        # Estratégia: Quanto maior a força detectada, mais permissivo com p-value
        #
        # 1. Força MUITO ALTA (>0.5): Padrão extremamente claro
        #    - Aceitar p-value < 0.20 (ANOVA tem baixo poder com poucos ciclos)
        #
        # 2. Força ALTA (0.3-0.5): Padrão claro
        #    - Para períodos <= 6: p-value < 0.15
        #    - Para períodos > 6: p-value < 0.10
        #
        # 3. Força MODERADA (0.2-0.3): Padrão detectável
        #    - Para períodos <= 6: p-value < 0.10
        #    - Para períodos > 6: p-value < 0.05
        #
        if best['score'] > 0.5:
            # Força muito alta - padrão extremamente claro
            has_seasonality = (best['pvalue'] < 0.20)
        elif best['score'] > 0.3:
            # Força alta
            if best['period'] <= 6:
                has_seasonality = (best['pvalue'] < 0.15)
            else:
                has_seasonality = (best['pvalue'] < 0.10)
        elif best['score'] > 0.2:
            # Força moderada - critério mais rigoroso
            if best['period'] <= 6:
                has_seasonality = (best['pvalue'] < 0.10)
            else:
                has_seasonality = (best['pvalue'] < 0.05)

            # Se falhou no teste estatístico mas força >= 0.15, tentar heurística visual
            if not has_seasonality and best['score'] >= 0.15:
                has_seasonality = self._check_visual_seasonality()
        elif best['score'] > 0.15:
            # Força fraca - verificar heurística adicional
            # Para dados agregados, STL pode subdimensionar a força sazonal
            # Verificar se há diferença consistente entre meses altos e baixos
            has_seasonality = self._check_visual_seasonality()
        else:
            # Força muito fraca - não considerar sazonal
            has_seasonality = False

        # Calcular confiança
        confidence = self._calculate_confidence(best, results)

        # Determinar razão
        if has_seasonality:
            period_name = self._get_period_name(best['period'])
            reason = f"Sazonalidade {period_name} detectada (força: {best['score']:.2f}, p<{best['pvalue']:.3f})"
        else:
            if best['score'] <= 0.3:
                reason = f"Padrão sazonal fraco (força: {best['score']:.2f} < 0.3)"
            else:
                reason = f"Padrão não estatisticamente significativo (p={best['pvalue']:.3f} >= 0.05)"

        return {
            'has_seasonality': has_seasonality,
            'seasonal_period': best['period'] if has_seasonality else None,
            'strength': best['score'],
            'confidence': confidence,
            'method': 'STL_DECOMPOSITION',
            'reason': reason,
            'seasonal_indices': best['seasonal_indices'] if has_seasonality else None
        }

    def _get_candidate_periods(self) -> List[int]:
        """
        Retorna períodos sazonais candidatos baseado no tamanho da série

        Returns:
            Lista de períodos para testar
        """
        candidates = []

        # Semanal (7)
        if self.n >= 14:  # Pelo menos 2 semanas
            candidates.append(7)

        # Trimestral (4)
        if self.n >= 8:  # Pelo menos 2 trimestres
            candidates.append(4)

        # Mensal (12)
        if self.n >= 24:  # Pelo menos 2 anos
            candidates.append(12)

        # Quinzenal (14)
        if self.n >= 28:
            candidates.append(14)

        # Semestral (6)
        if self.n >= 12:
            candidates.append(6)

        # Bimestral (2)
        if self.n >= 4:
            candidates.append(2)

        # Ordenar do menor para o maior (preferir períodos curtos)
        candidates.sort()

        return candidates

    def _evaluate_period(self, period: int) -> Dict:
        """
        Avalia a força da sazonalidade para um período específico

        Args:
            period: Período sazonal a testar

        Returns:
            Dicionário com strength, pvalue, seasonal_indices
        """
        # Decomposição sazonal usando método aditivo
        # (multiplicativo pode falhar com zeros)
        decomposition = seasonal_decompose(
            self.data,
            model='additive',
            period=period,
            extrapolate_trend='freq'
        )

        seasonal = decomposition.seasonal
        trend = decomposition.trend
        resid = decomposition.resid

        # Remover NaN
        mask = ~(np.isnan(seasonal) | np.isnan(trend) | np.isnan(resid))
        seasonal_clean = seasonal[mask]
        trend_clean = trend[mask]
        resid_clean = resid[mask]

        if len(seasonal_clean) == 0:
            raise ValueError("Decomposição resultou em todos NaN")

        # Calcular força da sazonalidade
        # Força = Var(sazonal) / Var(sazonal + residual)
        var_seasonal = np.var(seasonal_clean)
        var_residual = np.var(resid_clean)
        var_total = var_seasonal + var_residual

        if var_total > 0:
            strength = var_seasonal / var_total
        else:
            strength = 0.0

        # Teste estatístico: ANOVA para verificar se as médias sazonais diferem
        # Agrupar dados por índice sazonal
        seasonal_groups = []
        for i in range(period):
            indices = np.arange(i, len(self.data), period)
            group = self.data[indices]
            if len(group) > 0:
                seasonal_groups.append(group)

        # ANOVA one-way - com proteção contra erros
        try:
            if len(seasonal_groups) < 2:
                pvalue = 1.0
            elif any(len(group) < 2 for group in seasonal_groups):
                # Grupos com observações insuficientes para ANOVA
                pvalue = 1.0
            else:
                f_stat, pvalue = stats.f_oneway(*seasonal_groups)
                # Proteger contra NaN (pode ocorrer se todos os valores são iguais)
                if np.isnan(pvalue):
                    pvalue = 1.0
        except (ValueError, RuntimeError, ZeroDivisionError):
            pvalue = 1.0

        # Calcular índices sazonais médios
        seasonal_indices = []
        for i in range(period):
            indices = np.arange(i, len(seasonal_clean), period)
            seasonal_values = seasonal_clean[indices]
            if len(seasonal_values) > 0:
                seasonal_indices.append(float(np.mean(seasonal_values)))
            else:
                seasonal_indices.append(0.0)

        return {
            'strength': float(strength),
            'pvalue': float(pvalue),
            'seasonal_indices': seasonal_indices
        }

    def _calculate_confidence(self, best: Dict, all_results: List[Dict]) -> float:
        """
        Calcula confiança na detecção

        Args:
            best: Melhor resultado
            all_results: Todos os resultados

        Returns:
            Confiança (0-1)
        """
        confidence = 0.5  # Base

        # Fator 1: Força da sazonalidade
        if best['score'] > 0.7:
            confidence += 0.3
        elif best['score'] > 0.5:
            confidence += 0.2
        elif best['score'] > 0.3:
            confidence += 0.1

        # Fator 2: Significância estatística
        if best['pvalue'] < 0.01:
            confidence += 0.2
        elif best['pvalue'] < 0.05:
            confidence += 0.1

        # Fator 3: Separação do segundo melhor
        if len(all_results) > 1:
            second_best = all_results[1]
            gap = best['score'] - second_best['score']
            if gap > 0.2:
                confidence += 0.1

        # Limitar entre 0 e 1
        return min(1.0, max(0.0, confidence))

    def _check_visual_seasonality(self) -> bool:
        """
        Verifica se há sazonalidade visual clara nos dados.

        Quando STL subdimensiona a força sazonal (comum em dados agregados),
        esta heurística verifica se há diferença consistente entre meses.

        Returns:
            True se houver padrão sazonal visual claro
        """
        n = len(self.data)

        # Precisa de pelo menos 12 meses
        if n < 12:
            return False

        # Agrupar por mês do ano
        vendas_por_mes = {}
        for i, venda in enumerate(self.data):
            mes_do_ano = (i % 12) + 1
            if mes_do_ano not in vendas_por_mes:
                vendas_por_mes[mes_do_ano] = []
            vendas_por_mes[mes_do_ano].append(venda)

        # Calcular médias mensais
        medias_mensais = []
        for mes in range(1, 13):
            if mes in vendas_por_mes and len(vendas_por_mes[mes]) > 0:
                medias_mensais.append((mes, np.mean(vendas_por_mes[mes])))

        if len(medias_mensais) < 8:  # Precisa de pelo menos 8 meses com dados
            return False

        # Ordenar por valor
        medias_ordenadas = sorted(medias_mensais, key=lambda x: x[1])

        # Pegar os 3 meses mais baixos e 3 mais altos
        meses_baixos = medias_ordenadas[:3]
        meses_altos = medias_ordenadas[-3:]

        media_baixos = np.mean([v for _, v in meses_baixos])
        media_altos = np.mean([v for _, v in meses_altos])
        media_geral = np.mean(self.data)

        # Verificar se há diferença significativa (>15%)
        if media_geral > 0:
            diff_baixos = abs((media_baixos - media_geral) / media_geral)
            diff_altos = abs((media_altos - media_geral) / media_geral)

            # Se ambos os grupos (alto e baixo) diferem >15% da média, há sazonalidade
            if diff_baixos > 0.15 and diff_altos > 0.15:
                return True

        return False

    def _get_period_name(self, period: int) -> str:
        """
        Retorna nome descritivo do período

        Args:
            period: Período numérico

        Returns:
            Nome do período
        """
        names = {
            2: 'bimestral',
            4: 'trimestral',
            6: 'semestral',
            7: 'semanal',
            12: 'mensal/anual',
            14: 'quinzenal'
        }
        return names.get(period, f'período-{period}')


def detect_seasonality(data: List[float]) -> Dict:
    """
    Função helper para detecção automática de sazonalidade

    Args:
        data: Série temporal

    Returns:
        Dicionário com resultados da detecção
    """
    detector = SeasonalityDetector(data)
    return detector.detect()
