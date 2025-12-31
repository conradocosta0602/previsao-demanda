"""
Tratamento Especializado para Séries Temporais Curtas

Este módulo implementa estratégias específicas para lidar com séries
que possuem poucos pontos de dados históricos.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


class ShortSeriesHandler:
    """
    Manipulador especializado para séries temporais curtas
    """

    # Definição de comprimentos
    MUITO_CURTA = 3      # Menos de 3 meses
    CURTA = 6            # Menos de 6 meses
    MEDIA = 12           # Menos de 12 meses
    LONGA = 24           # 12 ou mais meses

    def __init__(self):
        self.min_confianca_curta = 0.3
        self.min_confianca_media = 0.5
        self.min_confianca_longa = 0.7

    def classificar_serie(self, serie: pd.Series) -> Dict:
        """
        Classifica uma série temporal quanto ao seu comprimento

        Args:
            serie: Série temporal

        Returns:
            Dicionário com classificação e características
        """
        tamanho = len(serie)

        if tamanho < self.MUITO_CURTA:
            categoria = 'MUITO_CURTA'
            confiabilidade = 'BAIXA'
            metodo_recomendado = 'ULTIMO_VALOR'
        elif tamanho < self.CURTA:
            categoria = 'CURTA'
            confiabilidade = 'MEDIA_BAIXA'
            metodo_recomendado = 'MEDIA_SIMPLES'
        elif tamanho < self.MEDIA:
            categoria = 'MEDIA'
            confiabilidade = 'MEDIA'
            metodo_recomendado = 'MEDIA_MOVEL'
        else:
            categoria = 'LONGA'
            confiabilidade = 'ALTA'
            metodo_recomendado = 'AUTO'  # Permite seleção automática

        return {
            'tamanho': tamanho,
            'categoria': categoria,
            'confiabilidade': confiabilidade,
            'metodo_recomendado': metodo_recomendado,
            'permite_ml': tamanho >= self.MEDIA,
            'permite_sazonalidade': tamanho >= self.MEDIA,
            'permite_tendencia': tamanho >= self.CURTA
        }

    def prever_serie_curta(self, serie: pd.Series,
                          n_periodos: int = 6,
                          metodo: Optional[str] = None) -> Dict:
        """
        Gera previsão para série temporal curta

        Args:
            serie: Série temporal
            n_periodos: Número de períodos a prever
            metodo: Método específico (None = automático)

        Returns:
            Dicionário com previsões e metadados
        """
        classificacao = self.classificar_serie(serie)

        # Selecionar método baseado no tamanho
        if metodo is None:
            metodo = classificacao['metodo_recomendado']

        # Executar previsão
        if metodo == 'ULTIMO_VALOR':
            previsoes, confianca = self._prever_ultimo_valor(serie, n_periodos)
            razao = 'Série muito curta - usando último valor observado'

        elif metodo == 'MEDIA_SIMPLES':
            previsoes, confianca = self._prever_media_simples(serie, n_periodos)
            razao = 'Série curta - usando média dos valores observados'

        elif metodo == 'MEDIA_MOVEL':
            previsoes, confianca = self._prever_media_movel(serie, n_periodos)
            razao = 'Série média - usando média móvel'

        elif metodo == 'MEDIA_PONDERADA':
            previsoes, confianca = self._prever_media_ponderada(serie, n_periodos)
            razao = 'Usando média ponderada (valores recentes têm mais peso)'

        elif metodo == 'CRESCIMENTO_LINEAR':
            previsoes, confianca = self._prever_crescimento_linear(serie, n_periodos)
            razao = 'Detectada tendência - usando crescimento linear'

        else:
            # Fallback
            previsoes, confianca = self._prever_media_simples(serie, n_periodos)
            razao = f'Método {metodo} não suportado - usando média simples'

        return {
            'previsoes': previsoes,
            'metodo_usado': metodo,
            'confianca': confianca,
            'razao': razao,
            'classificacao': classificacao,
            'valor_medio': np.mean(serie),
            'valor_ultimo': serie.iloc[-1],
            'desvio_padrao': np.std(serie),
            'cv': np.std(serie) / np.mean(serie) if np.mean(serie) > 0 else 0
        }

    def _prever_ultimo_valor(self, serie: pd.Series, n: int) -> Tuple[np.ndarray, float]:
        """
        Previsão usando o último valor observado
        Adequado para: séries muito curtas (< 3 pontos)
        """
        ultimo_valor = serie.iloc[-1]
        previsoes = np.full(n, ultimo_valor)

        # Confiança baixa porque não há histórico suficiente
        confianca = 0.3

        return previsoes, confianca

    def _prever_media_simples(self, serie: pd.Series, n: int) -> Tuple[np.ndarray, float]:
        """
        Previsão usando média simples
        Adequado para: séries curtas sem tendência clara
        """
        media = np.mean(serie)
        previsoes = np.full(n, media)

        # Confiança depende da volatilidade
        cv = np.std(serie) / media if media > 0 else 1
        confianca = max(0.3, min(0.6, 1 - cv))

        return previsoes, confianca

    def _prever_media_movel(self, serie: pd.Series, n: int) -> Tuple[np.ndarray, float]:
        """
        Previsão usando média móvel
        Adequado para: séries médias (6-12 pontos)
        """
        # Janela = metade do tamanho ou mínimo 3
        janela = max(3, min(len(serie) // 2, 6))
        media_movel = serie.tail(janela).mean()
        previsoes = np.full(n, media_movel)

        # Confiança média-alta
        confianca = 0.55

        return previsoes, confianca

    def _prever_media_ponderada(self, serie: pd.Series, n: int) -> Tuple[np.ndarray, float]:
        """
        Previsão usando média ponderada exponencialmente
        Valores recentes têm mais peso
        """
        # Criar pesos exponenciais (mais peso nos valores recentes)
        pesos = np.exp(np.linspace(0, 1, len(serie)))
        pesos = pesos / pesos.sum()

        media_ponderada = np.sum(serie.values * pesos)
        previsoes = np.full(n, media_ponderada)

        # Confiança média
        confianca = 0.50

        return previsoes, confianca

    def _prever_crescimento_linear(self, serie: pd.Series, n: int) -> Tuple[np.ndarray, float]:
        """
        Previsão usando tendência linear simples
        Adequado para: séries com tendência clara
        """
        if len(serie) < 3:
            # Muito curta para tendência confiável
            return self._prever_media_simples(serie, n)

        # Ajustar linha de tendência
        x = np.arange(len(serie))
        coeficientes = np.polyfit(x, serie.values, 1)

        # Projetar para o futuro
        x_futuro = np.arange(len(serie), len(serie) + n)
        previsoes = np.polyval(coeficientes, x_futuro)

        # Garantir não-negatividade
        previsoes = np.maximum(previsoes, 0)

        # Confiança baseada no R²
        y_pred_historico = np.polyval(coeficientes, x)
        ss_res = np.sum((serie.values - y_pred_historico) ** 2)
        ss_tot = np.sum((serie.values - np.mean(serie)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        confianca = max(0.4, min(0.7, r2))

        return previsoes, confianca

    def detectar_tendencia(self, serie: pd.Series) -> Dict:
        """
        Detecta se há tendência significativa na série

        Returns:
            Dicionário com informações sobre tendência
        """
        if len(serie) < 3:
            return {
                'tem_tendencia': False,
                'tipo': 'INSUFICIENTE',
                'intensidade': 0,
                'confianca': 0
            }

        # Calcular tendência usando regressão linear
        x = np.arange(len(serie))
        coeficientes = np.polyfit(x, serie.values, 1)
        inclinacao = coeficientes[0]

        # Normalizar pela média
        media = np.mean(serie)
        inclinacao_normalizada = inclinacao / media if media > 0 else 0

        # Calcular R² para confiança
        y_pred = np.polyval(coeficientes, x)
        ss_res = np.sum((serie.values - y_pred) ** 2)
        ss_tot = np.sum((serie.values - media) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Classificar tendência
        if abs(inclinacao_normalizada) < 0.02:  # < 2% por período
            tipo = 'ESTAVEL'
            tem_tendencia = False
        elif inclinacao_normalizada > 0:
            tipo = 'CRESCENTE'
            tem_tendencia = r2 > 0.5
        else:
            tipo = 'DECRESCENTE'
            tem_tendencia = r2 > 0.5

        return {
            'tem_tendencia': tem_tendencia,
            'tipo': tipo,
            'inclinacao': inclinacao,
            'inclinacao_normalizada': inclinacao_normalizada,
            'intensidade': abs(inclinacao_normalizada),
            'r2': r2,
            'confianca': r2
        }

    def sugerir_metodo_adaptativo(self, serie: pd.Series) -> Dict:
        """
        Sugere o melhor método baseado em análise adaptativa

        Args:
            serie: Série temporal

        Returns:
            Dicionário com método sugerido e justificativa
        """
        classificacao = self.classificar_serie(serie)
        tendencia = self.detectar_tendencia(serie)

        # Lógica de decisão
        if classificacao['tamanho'] < self.MUITO_CURTA:
            metodo = 'ULTIMO_VALOR'
            razao = 'Série muito curta - dados insuficientes para métodos complexos'

        elif classificacao['tamanho'] < self.CURTA:
            if tendencia['tem_tendencia']:
                metodo = 'CRESCIMENTO_LINEAR'
                razao = f'Série curta com tendência {tendencia["tipo"].lower()}'
            else:
                metodo = 'MEDIA_PONDERADA'
                razao = 'Série curta sem tendência clara - peso maior em valores recentes'

        elif classificacao['tamanho'] < self.MEDIA:
            if tendencia['tem_tendencia'] and tendencia['intensidade'] > 0.05:
                metodo = 'CRESCIMENTO_LINEAR'
                razao = f'Tendência {tendencia["tipo"].lower()} significativa detectada'
            else:
                metodo = 'MEDIA_MOVEL'
                razao = 'Série média sem tendência forte - média móvel apropriada'

        else:
            # Série longa - pode usar métodos avançados
            metodo = 'AUTO'
            razao = 'Série longa - permite uso de métodos avançados (ML, sazonalidade)'

        return {
            'metodo_sugerido': metodo,
            'razao': razao,
            'classificacao': classificacao,
            'analise_tendencia': tendencia,
            'confianca_estimada': self._estimar_confianca(classificacao, tendencia)
        }

    def _estimar_confianca(self, classificacao: Dict, tendencia: Dict) -> float:
        """
        Estima confiança da previsão baseada em características da série
        """
        # Confiança base pelo tamanho
        if classificacao['tamanho'] < self.MUITO_CURTA:
            confianca_base = 0.3
        elif classificacao['tamanho'] < self.CURTA:
            confianca_base = 0.45
        elif classificacao['tamanho'] < self.MEDIA:
            confianca_base = 0.60
        else:
            confianca_base = 0.75

        # Ajustar pela qualidade da tendência
        if tendencia['tem_tendencia']:
            bonus_tendencia = tendencia['r2'] * 0.15
        else:
            bonus_tendencia = 0

        confianca_final = min(0.95, confianca_base + bonus_tendencia)

        return confianca_final

    def criar_previsoes_com_intervalo(self, serie: pd.Series,
                                     n_periodos: int = 6) -> Dict:
        """
        Cria previsões com intervalo de confiança para séries curtas

        Returns:
            Dicionário com previsão central, limite inferior e superior
        """
        resultado = self.prever_serie_curta(serie, n_periodos)

        # Calcular intervalo baseado no desvio padrão histórico
        std = np.std(serie)
        previsoes = resultado['previsoes']

        # Intervalo: ± 1.96 * std (95% de confiança aproximado)
        margem = 1.96 * std

        return {
            **resultado,
            'previsao_central': previsoes,
            'limite_inferior': np.maximum(0, previsoes - margem),
            'limite_superior': previsoes + margem,
            'margem_erro': margem,
            'intervalo_confianca': 0.95
        }
