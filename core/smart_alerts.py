"""
Módulo de Alertas Inteligentes

Gera alertas automáticos baseados em:
- Risco de ruptura de estoque
- Excesso de estoque
- Mudanças bruscas na demanda
- Sazonalidade detectada
- Problemas de acurácia
- Outliers frequentes
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np


class SmartAlertGenerator:
    """
    Gerador de alertas inteligentes para previsão de demanda

    Analisa previsões, histórico e métricas para gerar alertas
    acionáveis com priorização automática.
    """

    # Tipos de alerta
    CRITICAL = 'CRITICAL'  # 🔴 Vermelho - Ação imediata
    WARNING = 'WARNING'    # 🟡 Amarelo - Atenção necessária
    INFO = 'INFO'          # 🔵 Azul - Informativo
    SUCCESS = 'SUCCESS'    # 🟢 Verde - Positivo

    # Categorias de alerta
    CATEGORY_STOCKOUT = 'RUPTURA_ESTOQUE'
    CATEGORY_OVERSTOCK = 'EXCESSO_ESTOQUE'
    CATEGORY_DEMAND_SPIKE = 'PICO_DEMANDA'
    CATEGORY_DEMAND_DROP = 'QUEDA_DEMANDA'
    CATEGORY_SEASONALITY = 'SAZONALIDADE'
    CATEGORY_ACCURACY = 'ACURACIA'
    CATEGORY_OUTLIERS = 'OUTLIERS'
    CATEGORY_DATA_QUALITY = 'QUALIDADE_DADOS'

    def __init__(self):
        self.alertas = []

    def generate_alerts(
        self,
        sku: str,
        loja: str,
        historico: List[float],
        previsao: List[float],
        modelo_info: Dict,
        estoque_atual: Optional[float] = None,
        lead_time_dias: int = 7,
        custo_unitario: Optional[float] = None
    ) -> List[Dict]:
        """
        Gera todos os alertas relevantes para um SKU/loja

        Args:
            sku: Código do SKU
            loja: Código da loja
            historico: Histórico de vendas
            previsao: Previsão futura
            modelo_info: Informações do modelo (params, métricas, etc)
            estoque_atual: Estoque atual (se disponível)
            lead_time_dias: Lead time de reposição em dias
            custo_unitario: Custo por unidade (para calcular valor financeiro)

        Returns:
            Lista de alertas ordenados por prioridade
        """
        self.alertas = []

        # 1. Alertas de Ruptura de Estoque
        if estoque_atual is not None:
            self._check_stockout_risk(
                sku, loja, estoque_atual, previsao,
                lead_time_dias, historico
            )

        # 2. Alertas de Excesso de Estoque
        if estoque_atual is not None and custo_unitario is not None:
            self._check_overstock_risk(
                sku, loja, estoque_atual, previsao,
                custo_unitario, historico
            )

        # 3. Alertas de Mudança Brusca na Demanda
        self._check_demand_changes(sku, loja, historico, previsao)

        # 4. Alertas de Sazonalidade
        if 'seasonality_detected' in modelo_info:
            self._check_seasonality_alerts(
                sku, loja, modelo_info['seasonality_detected']
            )

        # 5. Alertas de Acurácia
        if 'mape' in modelo_info or 'bias' in modelo_info:
            self._check_accuracy_alerts(
                sku, loja, modelo_info
            )

        # 6. Alertas de Outliers
        if 'outlier_detection' in modelo_info:
            self._check_outlier_alerts(
                sku, loja, modelo_info['outlier_detection']
            )

        # 7. Alertas de Qualidade de Dados
        self._check_data_quality(sku, loja, historico)

        # Ordenar por prioridade (críticos primeiro)
        self.alertas.sort(key=lambda x: x['prioridade'])

        return self.alertas

    def _check_stockout_risk(
        self,
        sku: str,
        loja: str,
        estoque_atual: float,
        previsao: List[float],
        lead_time_dias: int,
        historico: List[float]
    ):
        """Verifica risco de ruptura de estoque"""

        # Calcular demanda média diária
        demanda_media_mensal = np.mean(previsao[:3]) if len(previsao) >= 3 else previsao[0]
        demanda_diaria = demanda_media_mensal / 30

        # Demanda durante lead time
        demanda_lead_time = demanda_diaria * lead_time_dias

        # Estoque de segurança (1 desvio padrão do histórico)
        if len(historico) >= 3:
            std_historico = np.std(historico)
            estoque_seguranca = std_historico / 30 * lead_time_dias
        else:
            estoque_seguranca = demanda_lead_time * 0.2  # 20% como backup

        # Ponto de pedido = demanda durante lead time + estoque de segurança
        ponto_pedido = demanda_lead_time + estoque_seguranca

        # Dias até ruptura (estimativa)
        if demanda_diaria > 0:
            dias_ate_ruptura = estoque_atual / demanda_diaria
        else:
            dias_ate_ruptura = 999

        # CRÍTICO: Estoque abaixo do ponto de pedido
        if estoque_atual < ponto_pedido:
            quantidade_sugerida = max(
                ponto_pedido * 2,  # 2x ponto de pedido
                demanda_media_mensal * 1.5  # 1.5 meses de demanda
            )

            self.alertas.append({
                'tipo': self.CRITICAL,
                'categoria': self.CATEGORY_STOCKOUT,
                'sku': sku,
                'loja': loja,
                'titulo': 'Ruptura de estoque iminente',
                'mensagem': f'Estoque atual ({estoque_atual:.0f} un) abaixo do ponto de pedido ({ponto_pedido:.0f} un). Ruptura estimada em {dias_ate_ruptura:.0f} dias.',
                'acao_recomendada': f'Solicitar reposição urgente de {quantidade_sugerida:.0f} unidades',
                'prioridade': 1,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'estoque_atual': float(estoque_atual),
                    'ponto_pedido': float(ponto_pedido),
                    'demanda_diaria': float(demanda_diaria),
                    'dias_ate_ruptura': float(dias_ate_ruptura),
                    'quantidade_sugerida': float(quantidade_sugerida),
                    'lead_time_dias': lead_time_dias
                }
            })

        # ATENÇÃO: Estoque baixo mas ainda acima do ponto de pedido
        elif estoque_atual < ponto_pedido * 1.5 and dias_ate_ruptura < 14:
            self.alertas.append({
                'tipo': self.WARNING,
                'categoria': self.CATEGORY_STOCKOUT,
                'sku': sku,
                'loja': loja,
                'titulo': 'Estoque baixo',
                'mensagem': f'Estoque de {estoque_atual:.0f} un suficiente para aproximadamente {dias_ate_ruptura:.0f} dias.',
                'acao_recomendada': f'Monitorar estoque e planejar reposição',
                'prioridade': 2,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'estoque_atual': float(estoque_atual),
                    'dias_ate_ruptura': float(dias_ate_ruptura)
                }
            })

    def _check_overstock_risk(
        self,
        sku: str,
        loja: str,
        estoque_atual: float,
        previsao: List[float],
        custo_unitario: float,
        historico: List[float]
    ):
        """Verifica risco de excesso de estoque"""

        # Demanda média mensal
        demanda_media_mensal = np.mean(previsao[:3]) if len(previsao) >= 3 else previsao[0]

        if demanda_media_mensal <= 0:
            return

        # Cobertura em meses
        cobertura_meses = estoque_atual / demanda_media_mensal

        # Valor financeiro parado
        valor_parado = estoque_atual * custo_unitario

        # CRÍTICO: Excesso muito alto (>6 meses de cobertura)
        if cobertura_meses > 6:
            self.alertas.append({
                'tipo': self.CRITICAL,
                'categoria': self.CATEGORY_OVERSTOCK,
                'sku': sku,
                'loja': loja,
                'titulo': 'Excesso crítico de estoque',
                'mensagem': f'Estoque de {estoque_atual:.0f} un equivale a {cobertura_meses:.1f} meses de demanda. Valor parado: R$ {valor_parado:,.2f}',
                'acao_recomendada': f'Considerar promoção ou transferência para outras lojas. Suspender reposição.',
                'prioridade': 1,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'estoque_atual': float(estoque_atual),
                    'cobertura_meses': float(cobertura_meses),
                    'valor_parado': float(valor_parado),
                    'demanda_mensal': float(demanda_media_mensal)
                }
            })

        # ATENÇÃO: Excesso moderado (3-6 meses)
        elif cobertura_meses > 3:
            self.alertas.append({
                'tipo': self.WARNING,
                'categoria': self.CATEGORY_OVERSTOCK,
                'sku': sku,
                'loja': loja,
                'titulo': 'Excesso de estoque',
                'mensagem': f'Estoque de {cobertura_meses:.1f} meses acima do ideal (2-3 meses).',
                'acao_recomendada': f'Reduzir reposição. Monitorar giro de estoque.',
                'prioridade': 2,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'estoque_atual': float(estoque_atual),
                    'cobertura_meses': float(cobertura_meses)
                }
            })

    def _check_demand_changes(
        self,
        sku: str,
        loja: str,
        historico: List[float],
        previsao: List[float]
    ):
        """Detecta mudanças bruscas na demanda (crescimento ou queda)"""

        if len(historico) < 6:
            return

        # Comparar últimos 3 meses vs 3 meses anteriores
        ultimos_3 = np.mean(historico[-3:])
        anteriores_3 = np.mean(historico[-6:-3])

        if anteriores_3 == 0:
            return

        # Variação percentual
        variacao_pct = ((ultimos_3 - anteriores_3) / anteriores_3) * 100

        # CRÍTICO: Crescimento muito rápido (>50%)
        if variacao_pct > 50:
            self.alertas.append({
                'tipo': self.CRITICAL,
                'categoria': self.CATEGORY_DEMAND_SPIKE,
                'sku': sku,
                'loja': loja,
                'titulo': 'Crescimento acelerado da demanda',
                'mensagem': f'Demanda cresceu {variacao_pct:.1f}% nos últimos 3 meses. Média atual: {ultimos_3:.0f} un/mês.',
                'acao_recomendada': f'Revisar política de estoque urgentemente. Aumentar ponto de pedido.',
                'prioridade': 1,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'variacao_pct': float(variacao_pct),
                    'media_atual': float(ultimos_3),
                    'media_anterior': float(anteriores_3)
                }
            })

        # ATENÇÃO: Crescimento moderado (20-50%)
        elif variacao_pct > 20:
            self.alertas.append({
                'tipo': self.WARNING,
                'categoria': self.CATEGORY_DEMAND_SPIKE,
                'sku': sku,
                'loja': loja,
                'titulo': 'Demanda em crescimento',
                'mensagem': f'Crescimento de {variacao_pct:.1f}% detectado.',
                'acao_recomendada': f'Monitorar tendência e ajustar estoque de segurança.',
                'prioridade': 2,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'variacao_pct': float(variacao_pct)
                }
            })

        # ATENÇÃO: Queda significativa (< -30%)
        elif variacao_pct < -30:
            self.alertas.append({
                'tipo': self.WARNING,
                'categoria': self.CATEGORY_DEMAND_DROP,
                'sku': sku,
                'loja': loja,
                'titulo': 'Queda na demanda',
                'mensagem': f'Demanda caiu {abs(variacao_pct):.1f}% nos últimos 3 meses.',
                'acao_recomendada': f'Reduzir reposição. Investigar causa da queda.',
                'prioridade': 2,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'variacao_pct': float(variacao_pct),
                    'media_atual': float(ultimos_3),
                    'media_anterior': float(anteriores_3)
                }
            })

    def _check_seasonality_alerts(
        self,
        sku: str,
        loja: str,
        seasonality_info: Dict
    ):
        """Alertas sobre sazonalidade detectada"""

        if not seasonality_info.get('has_seasonality'):
            return

        periodo = seasonality_info.get('detected_period')
        forca = seasonality_info.get('strength', 0)

        # INFO: Sazonalidade forte detectada
        if forca > 0.7:
            periodo_nome = self._get_period_name(periodo)

            self.alertas.append({
                'tipo': self.INFO,
                'categoria': self.CATEGORY_SEASONALITY,
                'sku': sku,
                'loja': loja,
                'titulo': f'Sazonalidade {periodo_nome} forte detectada',
                'mensagem': f'Padrão sazonal com período de {periodo} detectado (força: {forca:.2f}).',
                'acao_recomendada': f'Preparar estoque adicional para picos sazonais. Ajustar planejamento.',
                'prioridade': 3,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'periodo': periodo,
                    'forca': float(forca),
                    'periodo_nome': periodo_nome
                }
            })

    def _check_accuracy_alerts(
        self,
        sku: str,
        loja: str,
        modelo_info: Dict
    ):
        """Alertas sobre acurácia do modelo"""

        mape = modelo_info.get('mape')
        bias = modelo_info.get('bias')

        # ATENÇÃO: MAPE alto (>30%)
        if mape is not None and mape > 30:
            self.alertas.append({
                'tipo': self.WARNING,
                'categoria': self.CATEGORY_ACCURACY,
                'sku': sku,
                'loja': loja,
                'titulo': 'Baixa acurácia do modelo',
                'mensagem': f'MAPE de {mape:.1f}% indica previsões pouco confiáveis.',
                'acao_recomendada': f'Revisar dados históricos. Considerar outro método de previsão.',
                'prioridade': 2,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'mape': float(mape)
                }
            })

        # INFO: MAPE excelente (<10%)
        elif mape is not None and mape < 10:
            self.alertas.append({
                'tipo': self.SUCCESS,
                'categoria': self.CATEGORY_ACCURACY,
                'sku': sku,
                'loja': loja,
                'titulo': 'Previsão de alta qualidade',
                'mensagem': f'MAPE de {mape:.1f}% indica previsões muito confiáveis.',
                'acao_recomendada': f'Manter método atual. Confiar nas previsões.',
                'prioridade': 4,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'mape': float(mape)
                }
            })

        # ATENÇÃO: BIAS alto (super/subestimação)
        if bias is not None and abs(bias) > 10:
            if bias > 0:
                direcao = 'superestimando'
            else:
                direcao = 'subestimando'

            self.alertas.append({
                'tipo': self.WARNING,
                'categoria': self.CATEGORY_ACCURACY,
                'sku': sku,
                'loja': loja,
                'titulo': f'Modelo {direcao} demanda',
                'mensagem': f'BIAS de {bias:+.1f} un indica viés sistemático.',
                'acao_recomendada': f'Ajustar parâmetros do modelo ou considerar outro método.',
                'prioridade': 2,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'bias': float(bias),
                    'direcao': direcao
                }
            })

    def _check_outlier_alerts(
        self,
        sku: str,
        loja: str,
        outlier_info: Dict
    ):
        """Alertas sobre outliers detectados"""

        outliers_count = outlier_info.get('outliers_count', 0)

        # ATENÇÃO: Muitos outliers (>20%)
        if outliers_count > 0:
            tratamento = outlier_info.get('treatment', 'NONE')

            if tratamento != 'NONE':
                self.alertas.append({
                    'tipo': self.INFO,
                    'categoria': self.CATEGORY_OUTLIERS,
                    'sku': sku,
                    'loja': loja,
                    'titulo': f'{outliers_count} outlier(s) detectado(s)',
                    'mensagem': f'Valores extremos foram tratados automaticamente ({tratamento}).',
                    'acao_recomendada': f'Revisar se outliers são eventos recorrentes ou pontuais.',
                    'prioridade': 3,
                    'timestamp': datetime.now().isoformat(),
                    'dados_contexto': {
                        'outliers_count': outliers_count,
                        'tratamento': tratamento
                    }
                })

    def _check_data_quality(
        self,
        sku: str,
        loja: str,
        historico: List[float]
    ):
        """Alertas sobre qualidade dos dados"""

        # ATENÇÃO: Histórico muito curto (<6 meses)
        if len(historico) < 6:
            self.alertas.append({
                'tipo': self.WARNING,
                'categoria': self.CATEGORY_DATA_QUALITY,
                'sku': sku,
                'loja': loja,
                'titulo': 'Histórico de dados limitado',
                'mensagem': f'Apenas {len(historico)} períodos de histórico disponíveis.',
                'acao_recomendada': f'Previsões podem ser menos precisas. Coletar mais dados históricos.',
                'prioridade': 3,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'periodos_historico': len(historico)
                }
            })

        # INFO: Histórico longo (>24 meses)
        elif len(historico) > 24:
            self.alertas.append({
                'tipo': self.SUCCESS,
                'categoria': self.CATEGORY_DATA_QUALITY,
                'sku': sku,
                'loja': loja,
                'titulo': 'Histórico robusto disponível',
                'mensagem': f'{len(historico)} períodos de histórico permitem previsões mais precisas.',
                'acao_recomendada': f'Aproveitar histórico longo para análise de tendências.',
                'prioridade': 4,
                'timestamp': datetime.now().isoformat(),
                'dados_contexto': {
                    'periodos_historico': len(historico)
                }
            })

    def _get_period_name(self, periodo: int) -> str:
        """Converte período numérico para nome"""
        nomes = {
            2: 'bimestral',
            4: 'trimestral',
            6: 'semestral',
            7: 'semanal',
            12: 'mensal/anual',
            14: 'quinzenal'
        }
        return nomes.get(periodo, f'período {periodo}')

    def get_summary(self) -> Dict:
        """
        Retorna resumo dos alertas

        Returns:
            Dicionário com contagens por tipo
        """
        summary = {
            'total': len(self.alertas),
            'critical': sum(1 for a in self.alertas if a['tipo'] == self.CRITICAL),
            'warning': sum(1 for a in self.alertas if a['tipo'] == self.WARNING),
            'info': sum(1 for a in self.alertas if a['tipo'] == self.INFO),
            'success': sum(1 for a in self.alertas if a['tipo'] == self.SUCCESS)
        }
        return summary


def generate_alerts_for_forecast(
    sku: str,
    loja: str,
    historico: List[float],
    previsao: List[float],
    modelo_params: Dict,
    estoque_atual: Optional[float] = None,
    lead_time_dias: int = 7,
    custo_unitario: Optional[float] = None
) -> Dict:
    """
    Função helper para gerar alertas de uma previsão

    Args:
        sku: Código do SKU
        loja: Código da loja
        historico: Histórico de vendas
        previsao: Previsão futura
        modelo_params: Parâmetros do modelo (params com métricas)
        estoque_atual: Estoque atual (opcional)
        lead_time_dias: Lead time de reposição
        custo_unitario: Custo unitário (opcional)

    Returns:
        Dicionário com alertas e resumo
    """
    generator = SmartAlertGenerator()

    alertas = generator.generate_alerts(
        sku=sku,
        loja=loja,
        historico=historico,
        previsao=previsao,
        modelo_info=modelo_params,
        estoque_atual=estoque_atual,
        lead_time_dias=lead_time_dias,
        custo_unitario=custo_unitario
    )

    summary = generator.get_summary()

    return {
        'alertas': alertas,
        'resumo': summary
    }
