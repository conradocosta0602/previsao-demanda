"""
Seletor de Métodos de Previsão usando Machine Learning

Este módulo analisa características das séries temporais e usa ML para selecionar
o método de previsão mais adequado para cada combinação SKU/Loja.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class MLMethodSelector:
    """
    Seletor inteligente de métodos de previsão usando Random Forest
    """

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False

    def extrair_caracteristicas(self, serie_temporal: pd.Series) -> Dict:
        """
        Extrai características estatísticas de uma série temporal

        Args:
            serie_temporal: Série de vendas ao longo do tempo

        Returns:
            Dicionário com características extraídas
        """
        # Garantir que a série não está vazia
        if len(serie_temporal) < 3:
            return self._caracteristicas_padrao()

        valores = serie_temporal.values

        # 1. Estatísticas básicas
        media = np.mean(valores)
        std = np.std(valores)
        cv = std / media if media > 0 else 0  # Coeficiente de variação

        # 2. Tendência
        x = np.arange(len(valores))
        coef_tendencia = np.polyfit(x, valores, 1)[0] if len(valores) > 1 else 0
        tendencia_normalizada = coef_tendencia / media if media > 0 else 0

        # 3. Sazonalidade (autocorrelação lag 12 para dados mensais)
        if len(valores) >= 13:
            autocorr_12 = np.corrcoef(valores[:-12], valores[12:])[0, 1]
        else:
            autocorr_12 = 0

        # 4. Estabilidade (diferença primeira ordem)
        if len(valores) > 1:
            diffs = np.diff(valores)
            estabilidade = np.std(diffs) / std if std > 0 else 0
        else:
            estabilidade = 0

        # 5. Zeros e outliers
        pct_zeros = np.sum(valores == 0) / len(valores)
        q1, q3 = np.percentile(valores, [25, 75])
        iqr = q3 - q1
        outliers_superiores = np.sum(valores > q3 + 1.5 * iqr) / len(valores)

        # 6. Padrão de crescimento
        if len(valores) >= 6:
            primeira_metade = np.mean(valores[:len(valores)//2])
            segunda_metade = np.mean(valores[len(valores)//2:])
            crescimento = (segunda_metade - primeira_metade) / primeira_metade if primeira_metade > 0 else 0
        else:
            crescimento = 0

        # 7. Regularidade (entropia)
        if media > 0:
            entropia = -np.sum((valores / np.sum(valores)) * np.log2((valores / np.sum(valores)) + 1e-10))
        else:
            entropia = 0

        return {
            'media': media,
            'cv': cv,
            'tendencia': tendencia_normalizada,
            'sazonalidade': autocorr_12,
            'estabilidade': estabilidade,
            'pct_zeros': pct_zeros,
            'pct_outliers': outliers_superiores,
            'crescimento': crescimento,
            'entropia': entropia,
            'tamanho_serie': len(valores)
        }

    def _caracteristicas_padrao(self) -> Dict:
        """Retorna características padrão para séries muito curtas"""
        return {
            'media': 0,
            'cv': 0,
            'tendencia': 0,
            'sazonalidade': 0,
            'estabilidade': 0,
            'pct_zeros': 1,
            'pct_outliers': 0,
            'crescimento': 0,
            'entropia': 0,
            'tamanho_serie': 0
        }

    def avaliar_metodo(self, serie: pd.Series, metodo: str, meses_teste: int = 3) -> float:
        """
        Avalia a performance de um método em uma série temporal

        Args:
            serie: Série temporal
            metodo: Nome do método ('media_movel', 'exponencial', 'holt_winters')
            meses_teste: Quantidade de meses para validação

        Returns:
            MAPE (Mean Absolute Percentage Error)
        """
        if len(serie) < meses_teste + 3:
            return 100.0  # MAPE alto para séries muito curtas

        # Dividir em treino e teste
        treino = serie[:-meses_teste]
        teste = serie[-meses_teste:]

        try:
            if metodo == 'media_movel':
                previsao = self._prever_media_movel(treino, meses_teste)
            elif metodo == 'exponencial':
                previsao = self._prever_exponencial(treino, meses_teste)
            elif metodo == 'holt_winters':
                previsao = self._prever_holt_winters(treino, meses_teste)
            else:
                return 100.0

            # Calcular MAPE
            mape = np.mean(np.abs((teste.values - previsao) / (teste.values + 1e-10))) * 100
            return mape

        except:
            return 100.0

    def _prever_media_movel(self, serie: pd.Series, n_periodos: int) -> np.ndarray:
        """Previsão usando média móvel simples"""
        janela = min(3, len(serie))
        media = serie.tail(janela).mean()
        return np.full(n_periodos, media)

    def _prever_exponencial(self, serie: pd.Series, n_periodos: int) -> np.ndarray:
        """Previsão usando suavização exponencial simples"""
        alpha = 0.3
        s = serie.iloc[0]
        for val in serie.values[1:]:
            s = alpha * val + (1 - alpha) * s
        return np.full(n_periodos, s)

    def _prever_holt_winters(self, serie: pd.Series, n_periodos: int) -> np.ndarray:
        """Previsão simplificada tipo Holt-Winters"""
        if len(serie) < 6:
            return self._prever_exponencial(serie, n_periodos)

        # Tendência linear simples
        x = np.arange(len(serie))
        coefs = np.polyfit(x, serie.values, 1)

        # Projetar tendência
        x_futuro = np.arange(len(serie), len(serie) + n_periodos)
        previsao = np.polyval(coefs, x_futuro)

        return np.maximum(previsao, 0)  # Garantir não-negatividade

    def treinar_com_historico(self, df_historico: pd.DataFrame) -> Dict:
        """
        Treina o modelo usando histórico de vendas

        Args:
            df_historico: DataFrame com colunas ['SKU', 'Loja', 'Mes', 'Vendas']

        Returns:
            Dicionário com estatísticas do treinamento
        """
        print("\n[ML] Iniciando treinamento do seletor de métodos...")

        # Preparar dados de treinamento
        X_train = []
        y_train = []

        # Para cada combinação SKU/Loja
        grupos = df_historico.groupby(['SKU', 'Loja'])
        total_series = len(grupos)
        series_validas = 0

        for (sku, loja), grupo in grupos:
            serie = grupo.sort_values('Mes')['Vendas']

            # Só usar séries com dados suficientes
            if len(serie) < 12:
                continue

            # Extrair características
            caracteristicas = self.extrair_caracteristicas(serie)

            # Avaliar cada método
            mape_mm = self.avaliar_metodo(serie, 'media_movel')
            mape_exp = self.avaliar_metodo(serie, 'exponencial')
            mape_hw = self.avaliar_metodo(serie, 'holt_winters')

            # Melhor método = menor MAPE
            mapes = [mape_mm, mape_exp, mape_hw]
            metodos = ['MEDIA_MOVEL', 'EXPONENCIAL', 'HOLT_WINTERS']
            melhor_metodo = metodos[np.argmin(mapes)]

            # Adicionar ao dataset de treino
            features = list(caracteristicas.values())
            X_train.append(features)
            y_train.append(melhor_metodo)
            series_validas += 1

        if series_validas < 3:
            print(f"[ML] AVISO: Apenas {series_validas} séries válidas. Mínimo recomendado: 3")
            return {
                'sucesso': False,
                'total_series': total_series,
                'series_validas': series_validas
            }

        # Converter para arrays numpy
        X_train = np.array(X_train)
        y_train = np.array(y_train)

        # Normalizar features
        X_train_scaled = self.scaler.fit_transform(X_train)

        # Treinar modelo
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True

        # Importância das features
        self.feature_names = list(self.extrair_caracteristicas(pd.Series([1, 2, 3])).keys())
        importancias = dict(zip(self.feature_names, self.model.feature_importances_))

        print(f"[ML] Treinamento concluído!")
        print(f"    - Séries analisadas: {series_validas}")
        print(f"    - Acurácia (treino): {self.model.score(X_train_scaled, y_train):.2%}")

        return {
            'sucesso': True,
            'total_series': total_series,
            'series_validas': series_validas,
            'acuracia': self.model.score(X_train_scaled, y_train),
            'importancia_features': importancias
        }

    def selecionar_metodo(self, serie: pd.Series) -> Tuple[str, float]:
        """
        Seleciona o melhor método para uma série temporal

        Args:
            serie: Série temporal de vendas

        Returns:
            Tupla (metodo, confianca)
        """
        if not self.is_trained:
            # Fallback: usar média móvel se não treinado
            return 'MEDIA_MOVEL', 0.5

        # Extrair características
        caracteristicas = self.extrair_caracteristicas(serie)
        features = np.array(list(caracteristicas.values())).reshape(1, -1)

        # Normalizar
        features_scaled = self.scaler.transform(features)

        # Predizer método
        metodo = self.model.predict(features_scaled)[0]

        # Confiança = probabilidade da classe predita
        probabilidades = self.model.predict_proba(features_scaled)[0]
        confianca = np.max(probabilidades)

        return metodo, confianca

    def selecionar_metodos_em_massa(self, df_historico: pd.DataFrame) -> pd.DataFrame:
        """
        Seleciona métodos para todas as combinações SKU/Loja

        Args:
            df_historico: DataFrame com histórico de vendas

        Returns:
            DataFrame com colunas ['SKU', 'Loja', 'Metodo_Sugerido', 'Confianca']
        """
        resultados = []

        grupos = df_historico.groupby(['SKU', 'Loja'])

        for (sku, loja), grupo in grupos:
            serie = grupo.sort_values('Mes')['Vendas']
            metodo, confianca = self.selecionar_metodo(serie)

            resultados.append({
                'SKU': sku,
                'Loja': loja,
                'Metodo_Sugerido': metodo,
                'Confianca': confianca
            })

        return pd.DataFrame(resultados)
