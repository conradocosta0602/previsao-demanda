"""
Modulo de Previsao Semanal (ISO-8601)
=====================================
Calcula demanda prevista por semana ISO para pedidos de fornecedor.

Logica:
- Hoje = Semana W_atual
- Entrega = Hoje + Lead_Time => Semana W_entrega
- Cobertura = N dias => Semanas W_entrega ate W_final
- Demanda = Soma das previsoes semanais de W_entrega ate W_final

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
from scipy import stats


def get_iso_week(d: date) -> Tuple[int, int]:
    """
    Retorna o ano e semana ISO-8601 de uma data.

    Args:
        d: Data a ser convertida

    Returns:
        Tupla (ano_iso, semana_iso)
    """
    iso_calendar = d.isocalendar()
    return iso_calendar[0], iso_calendar[1]


def get_date_from_iso_week(ano: int, semana: int, dia_semana: int = 1) -> date:
    """
    Retorna a data correspondente a um ano/semana ISO.

    Args:
        ano: Ano ISO
        semana: Semana ISO (1-53)
        dia_semana: Dia da semana (1=Segunda, 7=Domingo)

    Returns:
        Data correspondente
    """
    return datetime.strptime(f'{ano}-W{semana:02d}-{dia_semana}', '%G-W%V-%u').date()


def calcular_semanas_cobertura(
    data_base: date,
    lead_time_dias: int,
    cobertura_dias: int
) -> List[Tuple[int, int, int]]:
    """
    Calcula as semanas ISO que serao cobertas pelo pedido.

    Args:
        data_base: Data atual (hoje)
        lead_time_dias: Tempo de entrega do fornecedor
        cobertura_dias: Dias de cobertura do pedido

    Returns:
        Lista de tuplas (ano_iso, semana_iso, dias_na_semana)
        onde dias_na_semana indica quantos dias da cobertura caem nessa semana
    """
    # Data de entrega
    data_entrega = data_base + timedelta(days=lead_time_dias)

    # Data final da cobertura
    data_final = data_entrega + timedelta(days=cobertura_dias - 1)

    # Coletar todas as semanas no intervalo
    semanas = []
    data_atual = data_entrega

    while data_atual <= data_final:
        ano_iso, semana_iso = get_iso_week(data_atual)

        # Calcular quantos dias da cobertura caem nesta semana
        # Inicio da semana (segunda)
        inicio_semana = get_date_from_iso_week(ano_iso, semana_iso, 1)
        fim_semana = get_date_from_iso_week(ano_iso, semana_iso, 7)

        # Dias dentro do intervalo de cobertura
        inicio_contagem = max(data_atual, data_entrega)
        fim_contagem = min(fim_semana, data_final)

        dias_na_semana = (fim_contagem - inicio_contagem).days + 1

        # Verificar se ja nao foi adicionada
        if not semanas or semanas[-1][:2] != (ano_iso, semana_iso):
            semanas.append((ano_iso, semana_iso, dias_na_semana))
        else:
            # Atualizar dias na ultima semana adicionada
            semanas[-1] = (ano_iso, semana_iso, semanas[-1][2] + dias_na_semana)

        # Avancar para proxima semana
        data_atual = fim_semana + timedelta(days=1)

    return semanas


class WeeklyForecast:
    """
    Classe para calcular previsao de demanda por semana ISO.
    """

    def __init__(self, conn):
        """
        Args:
            conn: Conexao com o banco PostgreSQL
        """
        self.conn = conn
        self._cache_historico_semanal = {}

    def buscar_historico_semanal(
        self,
        codigo: int,
        cod_empresa: int,
        anos_historico: int = 2
    ) -> pd.DataFrame:
        """
        Busca historico de vendas agrupado por semana ISO.

        Args:
            codigo: Codigo do produto
            cod_empresa: Codigo da empresa/loja
            anos_historico: Anos de historico a buscar

        Returns:
            DataFrame com colunas: ano_iso, semana_iso, qtd_venda
        """
        cache_key = (codigo, cod_empresa, anos_historico)
        if cache_key in self._cache_historico_semanal:
            return self._cache_historico_semanal[cache_key]

        # Converter codigo para int
        try:
            codigo_int = int(codigo)
        except (ValueError, TypeError):
            return pd.DataFrame(columns=['ano_iso', 'semana_iso', 'qtd_venda'])

        data_fim = datetime.now().date()
        data_inicio = data_fim - timedelta(days=anos_historico * 365)

        query = """
            SELECT
                EXTRACT(ISOYEAR FROM data)::INTEGER as ano_iso,
                EXTRACT(WEEK FROM data)::INTEGER as semana_iso,
                SUM(COALESCE(qtd_venda, 0)) as qtd_venda
            FROM historico_vendas_diario
            WHERE codigo = %s
              AND cod_empresa = %s
              AND data >= %s
              AND data <= %s
            GROUP BY ano_iso, semana_iso
            ORDER BY ano_iso, semana_iso
        """

        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                df = pd.read_sql(query, self.conn, params=[codigo_int, cod_empresa, data_inicio, data_fim])
        except Exception:
            df = pd.DataFrame(columns=['ano_iso', 'semana_iso', 'qtd_venda'])

        self._cache_historico_semanal[cache_key] = df
        return df

    def calcular_indice_semanal(
        self,
        df_historico: pd.DataFrame
    ) -> Dict[int, float]:
        """
        Calcula indice sazonal para cada semana do ano.

        Similar ao indice mensal, mas para 52 semanas.
        indice_semana = media_semana / media_geral

        Args:
            df_historico: DataFrame com historico semanal

        Returns:
            Dicionario {semana_iso: indice_sazonal}
        """
        if df_historico.empty:
            # Retornar indices neutros (1.0)
            return {s: 1.0 for s in range(1, 54)}

        # Agrupar por semana (ignorando ano)
        media_por_semana = df_historico.groupby('semana_iso')['qtd_venda'].mean()

        # Media geral
        media_geral = df_historico['qtd_venda'].mean()

        if media_geral == 0:
            return {s: 1.0 for s in range(1, 54)}

        # Calcular indices
        indices = {}
        for semana in range(1, 54):
            if semana in media_por_semana.index:
                indices[semana] = media_por_semana[semana] / media_geral
            else:
                indices[semana] = 1.0

        return indices

    def calcular_previsao_semana(
        self,
        df_historico: pd.DataFrame,
        ano_iso: int,
        semana_iso: int,
        demanda_media_diaria: float = None
    ) -> Tuple[float, float]:
        """
        Calcula previsao de demanda para uma semana especifica.

        Usa combinacao de:
        1. Media historica da mesma semana em anos anteriores
        2. Tendencia recente
        3. Indice sazonal semanal

        Args:
            df_historico: DataFrame com historico semanal
            ano_iso: Ano ISO da semana a prever
            semana_iso: Semana ISO a prever
            demanda_media_diaria: Se fornecida, usa como base para ajuste

        Returns:
            Tupla (previsao_semanal, desvio_padrao)
        """
        if df_historico.empty:
            # Sem historico, usar demanda diaria * 7 se disponivel
            if demanda_media_diaria is not None:
                return demanda_media_diaria * 7, demanda_media_diaria * 2
            return 0.0, 0.0

        # 1. Buscar historico da mesma semana em anos anteriores
        hist_semana = df_historico[df_historico['semana_iso'] == semana_iso]['qtd_venda'].tolist()

        # 2. Calcular indices sazonais
        indices = self.calcular_indice_semanal(df_historico)
        indice_semana = indices.get(semana_iso, 1.0)

        # 3. Calcular media geral semanal recente (ultimas 12 semanas)
        ultimas_semanas = df_historico.tail(12)
        media_recente = ultimas_semanas['qtd_venda'].mean() if not ultimas_semanas.empty else 0

        # 4. Combinar metodos
        if len(hist_semana) >= 2:
            # Temos historico da mesma semana - usar media com peso
            media_historica = np.mean(hist_semana)
            desvio_historico = np.std(hist_semana, ddof=1) if len(hist_semana) > 1 else media_historica * 0.3

            # Combinar: 60% historico da semana, 40% tendencia recente ajustada
            previsao = 0.6 * media_historica + 0.4 * (media_recente * indice_semana)
        else:
            # Sem historico suficiente da semana - usar tendencia com indice
            previsao = media_recente * indice_semana
            desvio_historico = media_recente * 0.3

        # Se temos demanda_media_diaria, fazer sanity check
        if demanda_media_diaria is not None and demanda_media_diaria > 0:
            demanda_semanal_base = demanda_media_diaria * 7

            # Se previsao semanal difere muito da base diaria, ajustar
            if previsao > 0:
                ratio = previsao / demanda_semanal_base
                if ratio > 3 or ratio < 0.3:
                    # Ajuste mais conservador
                    previsao = demanda_semanal_base * indice_semana

        return max(0, previsao), max(0, desvio_historico)

    def calcular_demanda_periodo_cobertura(
        self,
        codigo: int,
        cod_empresa: int,
        lead_time_dias: int,
        cobertura_dias: int,
        demanda_media_diaria: float = None,
        data_base: date = None
    ) -> Dict:
        """
        Calcula a demanda total para o periodo de cobertura usando previsao semanal.

        Esta e a funcao principal que deve ser chamada pelo PedidoFornecedorIntegrado.

        Args:
            codigo: Codigo do produto
            cod_empresa: Codigo da empresa/loja
            lead_time_dias: Lead time do fornecedor em dias
            cobertura_dias: Dias de cobertura do pedido
            demanda_media_diaria: Demanda media diaria atual (para sanity check)
            data_base: Data base para calculo (default: hoje)

        Returns:
            Dicionario com:
            - demanda_total: Demanda total prevista para o periodo
            - demanda_por_dia: Demanda media diaria equivalente
            - semanas_cobertura: Lista de semanas e suas previsoes
            - detalhes: Informacoes adicionais do calculo
        """
        if data_base is None:
            data_base = datetime.now().date()

        # 1. Calcular semanas de cobertura
        semanas = calcular_semanas_cobertura(data_base, lead_time_dias, cobertura_dias)

        # 2. Buscar historico semanal
        df_historico = self.buscar_historico_semanal(codigo, cod_empresa)

        # 3. Calcular previsao para cada semana
        demanda_total = 0.0
        desvio_total = 0.0
        previsoes_semanas = []

        for ano_iso, semana_iso, dias_na_semana in semanas:
            # Previsao para a semana completa
            previsao_semanal, desvio_semanal = self.calcular_previsao_semana(
                df_historico, ano_iso, semana_iso, demanda_media_diaria
            )

            # Proporcao da semana (se nao usa a semana inteira)
            proporcao = dias_na_semana / 7.0
            demanda_semana = previsao_semanal * proporcao
            desvio_semana = desvio_semanal * proporcao

            demanda_total += demanda_semana
            desvio_total += desvio_semana ** 2  # Variancia

            previsoes_semanas.append({
                'ano_iso': ano_iso,
                'semana_iso': semana_iso,
                'dias_na_semana': dias_na_semana,
                'previsao_semanal_completa': round(previsao_semanal, 2),
                'previsao_proporcional': round(demanda_semana, 2),
                'proporcao': round(proporcao, 2)
            })

        # Desvio total (raiz da soma das variancias)
        desvio_total = np.sqrt(desvio_total)

        # Demanda media por dia (para manter compatibilidade com interface)
        demanda_por_dia = demanda_total / cobertura_dias if cobertura_dias > 0 else 0

        # Semana atual e semana de entrega
        ano_atual, semana_atual = get_iso_week(data_base)
        data_entrega = data_base + timedelta(days=lead_time_dias)
        ano_entrega, semana_entrega = get_iso_week(data_entrega)

        return {
            'demanda_total': round(demanda_total, 2),
            'demanda_por_dia': round(demanda_por_dia, 4),
            'desvio_padrao_total': round(desvio_total, 2),
            'semanas_cobertura': previsoes_semanas,
            'numero_semanas': len(semanas),
            'detalhes': {
                'data_base': data_base.isoformat(),
                'semana_atual': f'{ano_atual}-W{semana_atual:02d}',
                'data_entrega': data_entrega.isoformat(),
                'semana_entrega': f'{ano_entrega}-W{semana_entrega:02d}',
                'lead_time_dias': lead_time_dias,
                'cobertura_dias': cobertura_dias,
                'metodo': 'previsao_semanal_iso8601',
                'historico_usado': not df_historico.empty,
                'demanda_diaria_base': demanda_media_diaria
            }
        }


def criar_weekly_forecast(conn) -> WeeklyForecast:
    """
    Factory function para criar instancia de WeeklyForecast.

    Args:
        conn: Conexao com o banco PostgreSQL

    Returns:
        Instancia de WeeklyForecast
    """
    return WeeklyForecast(conn)
