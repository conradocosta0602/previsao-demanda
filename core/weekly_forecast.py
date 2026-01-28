"""
Modulo de Previsao Semanal (ISO-8601)
=====================================
Calcula demanda prevista por semana ISO para pedidos de fornecedor.

ATUALIZADO: Agora usa os 6 metodos inteligentes do DemandCalculator
com tratamento especial para series curtas.

Logica:
- Hoje = Semana W_atual
- Entrega = Hoje + Lead_Time => Semana W_entrega
- Cobertura = N dias => Semanas W_entrega ate W_final
- Demanda = Soma das previsoes semanais de W_entrega ate W_final

Metodos disponiveis (auto-selecionados):
- SMA (Media Movel Simples) - para demanda estavel
- WMA (Media Movel Ponderada) - para demanda estavel com tendencia leve
- EMA (Media Movel Exponencial) - para alta variabilidade
- Tendencia (Regressao Linear) - para tendencia forte
- Sazonal (Decomposicao Sazonal) - para padroes sazonais (52+ semanas)
- TSB (Teunter-Syntetos-Babai) - para demanda intermitente

Series curtas:
- 1-2 semanas: Naive/Bayesiano com fator de seguranca alto
- 3-8 semanas: WMA adaptativo com tendencia simplificada
- 9-25 semanas: Metodos completos sem sazonalidade
- 26+ semanas: Todos os 6 metodos disponiveis

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
from scipy import stats

# Importar DemandCalculator para usar os 6 metodos inteligentes
from core.demand_calculator import DemandCalculator


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

    ATUALIZADO: Usa os 6 metodos inteligentes do DemandCalculator
    com tratamento especial para series curtas.
    """

    def __init__(self, conn):
        """
        Args:
            conn: Conexao com o banco PostgreSQL
        """
        self.conn = conn
        self._cache_historico_semanal = {}
        self._cache_media_cluster = {}  # Cache para media de produtos similares

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

    def buscar_media_cluster_semanal(
        self,
        cod_empresa: int,
        categoria: str = None,
        subcategoria: str = None,
        fornecedor: str = None,
        curva_abc: str = None,
        preco_referencia: float = None
    ) -> Tuple[float, Dict]:
        """
        Busca media semanal de produtos SIMILARES usando criterios combinados.
        Usado como prior bayesiano para series muito curtas.

        CRITERIOS DE SIMILARIDADE (em ordem de prioridade):
        1. Nivel 1 (mais especifico): Fornecedor + Subcategoria + Curva ABC + Faixa Preco
        2. Nivel 2: Fornecedor + Subcategoria + Curva ABC
        3. Nivel 3: Fornecedor + Subcategoria
        4. Nivel 4: Fornecedor + Categoria
        5. Nivel 5 (mais generico): Apenas Fornecedor

        Args:
            cod_empresa: Codigo da empresa/loja
            categoria: Categoria do produto (linha1)
            subcategoria: Subcategoria do produto (linha3)
            fornecedor: CNPJ do fornecedor
            curva_abc: Classificacao ABC do produto
            preco_referencia: Preco de venda para filtro por faixa (±30%)

        Returns:
            Tupla (media_semanal, metadata) com informacoes do cluster encontrado
        """
        cache_key = (cod_empresa, categoria, subcategoria, fornecedor, curva_abc,
                     round(preco_referencia, 0) if preco_referencia else None)
        if cache_key in self._cache_media_cluster:
            return self._cache_media_cluster[cache_key]

        resultado_default = (0.0, {'nivel': 'nenhum', 'produtos_similares': 0})

        try:
            import warnings

            # Tentar cada nivel de similaridade, do mais especifico ao mais generico
            niveis_similaridade = []

            # Nivel 1: Fornecedor + Subcategoria + ABC + Faixa Preco
            if fornecedor and subcategoria and curva_abc and preco_referencia:
                preco_min = preco_referencia * 0.7
                preco_max = preco_referencia * 1.3
                niveis_similaridade.append({
                    'nivel': 1,
                    'descricao': 'fornecedor+subcategoria+abc+preco',
                    'filtros': {
                        'fornecedor': fornecedor,
                        'subcategoria': subcategoria,
                        'curva_abc': curva_abc,
                        'preco_min': preco_min,
                        'preco_max': preco_max
                    }
                })

            # Nivel 2: Fornecedor + Subcategoria + ABC
            if fornecedor and subcategoria and curva_abc:
                niveis_similaridade.append({
                    'nivel': 2,
                    'descricao': 'fornecedor+subcategoria+abc',
                    'filtros': {
                        'fornecedor': fornecedor,
                        'subcategoria': subcategoria,
                        'curva_abc': curva_abc
                    }
                })

            # Nivel 3: Fornecedor + Subcategoria
            if fornecedor and subcategoria:
                niveis_similaridade.append({
                    'nivel': 3,
                    'descricao': 'fornecedor+subcategoria',
                    'filtros': {
                        'fornecedor': fornecedor,
                        'subcategoria': subcategoria
                    }
                })

            # Nivel 4: Fornecedor + Categoria
            if fornecedor and categoria:
                niveis_similaridade.append({
                    'nivel': 4,
                    'descricao': 'fornecedor+categoria',
                    'filtros': {
                        'fornecedor': fornecedor,
                        'categoria': categoria
                    }
                })

            # Nivel 5: Apenas Fornecedor
            if fornecedor:
                niveis_similaridade.append({
                    'nivel': 5,
                    'descricao': 'fornecedor',
                    'filtros': {
                        'fornecedor': fornecedor
                    }
                })

            # Nivel 6: Categoria + Subcategoria (fallback sem fornecedor)
            if categoria and subcategoria:
                niveis_similaridade.append({
                    'nivel': 6,
                    'descricao': 'categoria+subcategoria',
                    'filtros': {
                        'categoria': categoria,
                        'subcategoria': subcategoria
                    }
                })

            # Tentar cada nivel ate encontrar produtos similares suficientes
            for nivel_info in niveis_similaridade:
                filtros = nivel_info['filtros']

                # Montar query dinamicamente
                query = """
                    WITH vendas_semana AS (
                        SELECT
                            h.codigo,
                            EXTRACT(ISOYEAR FROM h.data)::INTEGER as ano_iso,
                            EXTRACT(WEEK FROM h.data)::INTEGER as semana_iso,
                            SUM(COALESCE(h.qtd_venda, 0)) as qtd_semana
                        FROM historico_vendas_diario h
                        JOIN cadastro_produtos_completo p ON h.codigo::TEXT = p.cod_produto
                        LEFT JOIN estoque_posicao_atual e ON h.codigo = e.codigo AND h.cod_empresa = e.cod_empresa
                        WHERE h.cod_empresa = %s
                          AND h.data >= CURRENT_DATE - INTERVAL '12 weeks'
                          {filtro_fornecedor}
                          {filtro_categoria}
                          {filtro_subcategoria}
                          {filtro_curva_abc}
                          {filtro_preco}
                        GROUP BY h.codigo, ano_iso, semana_iso
                    ),
                    stats AS (
                        SELECT
                            COUNT(DISTINCT codigo) as num_produtos,
                            AVG(qtd_semana) as media_semanal,
                            STDDEV(qtd_semana) as desvio_semanal
                        FROM vendas_semana
                        WHERE qtd_semana > 0
                    )
                    SELECT * FROM stats
                """

                params = [cod_empresa]

                # Adicionar filtros conforme disponivel
                filtro_fornecedor = ""
                filtro_categoria = ""
                filtro_subcategoria = ""
                filtro_curva_abc = ""
                filtro_preco = ""

                if 'fornecedor' in filtros:
                    filtro_fornecedor = "AND p.cnpj_fornecedor = %s"
                    params.append(filtros['fornecedor'])

                if 'categoria' in filtros:
                    filtro_categoria = "AND p.categoria = %s"
                    params.append(filtros['categoria'])

                if 'subcategoria' in filtros:
                    filtro_subcategoria = "AND p.descricao_linha = %s"
                    params.append(filtros['subcategoria'])

                if 'curva_abc' in filtros:
                    filtro_curva_abc = "AND COALESCE(e.curva_abc, 'B') = %s"
                    params.append(filtros['curva_abc'])

                if 'preco_min' in filtros and 'preco_max' in filtros:
                    filtro_preco = "AND COALESCE(e.preco_venda, 0) BETWEEN %s AND %s"
                    params.extend([filtros['preco_min'], filtros['preco_max']])

                query = query.format(
                    filtro_fornecedor=filtro_fornecedor,
                    filtro_categoria=filtro_categoria,
                    filtro_subcategoria=filtro_subcategoria,
                    filtro_curva_abc=filtro_curva_abc,
                    filtro_preco=filtro_preco
                )

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    df = pd.read_sql(query, self.conn, params=params)

                if not df.empty and df['media_semanal'].iloc[0] is not None:
                    num_produtos = int(df['num_produtos'].iloc[0]) if df['num_produtos'].iloc[0] else 0
                    media = float(df['media_semanal'].iloc[0])
                    desvio = float(df['desvio_semanal'].iloc[0]) if df['desvio_semanal'].iloc[0] else media * 0.3

                    # Requer minimo de 3 produtos similares para ser confiavel
                    if num_produtos >= 3 and media > 0:
                        metadata = {
                            'nivel': nivel_info['nivel'],
                            'descricao_nivel': nivel_info['descricao'],
                            'produtos_similares': num_produtos,
                            'media_semanal': round(media, 2),
                            'desvio_cluster': round(desvio, 2),
                            'confianca_cluster': 'alta' if num_produtos >= 10 else ('media' if num_produtos >= 5 else 'baixa')
                        }
                        resultado = (media, metadata)
                        self._cache_media_cluster[cache_key] = resultado
                        return resultado

            # Nenhum nivel encontrou produtos suficientes
            self._cache_media_cluster[cache_key] = resultado_default
            return resultado_default

        except Exception as e:
            self._cache_media_cluster[cache_key] = resultado_default
            return resultado_default

    def calcular_previsao_inteligente_semanal(
        self,
        df_historico: pd.DataFrame,
        cod_empresa: int = None,
        categoria: str = None,
        subcategoria: str = None,
        fornecedor: str = None,
        curva_abc: str = None,
        preco_referencia: float = None
    ) -> Tuple[float, float, Dict]:
        """
        Calcula previsao semanal usando os 6 metodos inteligentes.

        METODO PRINCIPAL - Substitui indices sazonais simples por:
        - Selecao automatica do melhor metodo baseado no padrao da serie
        - Tratamento especial para series curtas
        - Prior bayesiano COMBINADO para produtos novos

        Prior Bayesiano usa criterios combinados (do mais especifico ao mais generico):
        1. Fornecedor + Subcategoria + Curva ABC + Faixa Preco (±30%)
        2. Fornecedor + Subcategoria + Curva ABC
        3. Fornecedor + Subcategoria
        4. Fornecedor + Categoria
        5. Apenas Fornecedor
        6. Categoria + Subcategoria (fallback)

        Args:
            df_historico: DataFrame com colunas ano_iso, semana_iso, qtd_venda
            cod_empresa: Codigo da empresa (para buscar prior)
            categoria: Categoria do produto (linha1)
            subcategoria: Subcategoria do produto (linha3)
            fornecedor: CNPJ fornecedor
            curva_abc: Classificacao ABC do produto
            preco_referencia: Preco para filtro por faixa

        Returns:
            Tupla (previsao_semanal, desvio_padrao, metadata)
        """
        # Converter historico para lista de vendas semanais
        if df_historico.empty:
            # Sem historico - buscar prior do cluster combinado
            media_cluster, cluster_info = self.buscar_media_cluster_semanal(
                cod_empresa, categoria, subcategoria, fornecedor, curva_abc, preco_referencia
            )
            if media_cluster > 0:
                return media_cluster, media_cluster * 0.5, {
                    'metodo_usado': 'prior_cluster_combinado',
                    'confianca': 'muito_baixa',
                    'categoria_serie': 'sem_dados',
                    'tamanho_serie': 0,
                    'fator_seguranca_recomendado': 2.5,
                    'cluster_info': cluster_info
                }
            return 0.0, 0.0, {
                'metodo_usado': 'sem_dados',
                'confianca': 'muito_baixa',
                'categoria_serie': 'sem_dados',
                'tamanho_serie': 0
            }

        # Ordenar por ano/semana e extrair vendas
        df_sorted = df_historico.sort_values(['ano_iso', 'semana_iso'])
        vendas_semanais = df_sorted['qtd_venda'].tolist()

        # Buscar media do cluster para prior bayesiano (series curtas)
        media_cluster = None
        cluster_info = None
        if len(vendas_semanais) < 8 and cod_empresa:
            media_cluster, cluster_info = self.buscar_media_cluster_semanal(
                cod_empresa, categoria, subcategoria, fornecedor, curva_abc, preco_referencia
            )
            if media_cluster == 0:
                media_cluster = None

        # Usar DemandCalculator.calcular_demanda_adaptativa com granularidade semanal
        demanda, desvio, metadata = DemandCalculator.calcular_demanda_adaptativa(
            vendas=vendas_semanais,
            granularidade='semanal',
            media_cluster=media_cluster
        )

        # Adicionar informacoes do cluster se usou prior
        if cluster_info:
            metadata['cluster_info'] = cluster_info

        return demanda, desvio, metadata

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
        demanda_media_diaria: float = None,
        usar_metodo_inteligente: bool = True,
        cod_empresa: int = None,
        categoria: str = None,
        subcategoria: str = None,
        fornecedor: str = None,
        curva_abc: str = None,
        preco_referencia: float = None
    ) -> Tuple[float, float, Dict]:
        """
        Calcula previsao de demanda para uma semana especifica.

        ATUALIZADO: Agora usa os 6 metodos inteligentes por padrao.
        Prior Bayesiano usa criterios COMBINADOS para encontrar produtos similares.

        Metodos disponiveis (auto-selecionados):
        1. SMA - Media Movel Simples (demanda estavel)
        2. WMA - Media Movel Ponderada (tendencia leve)
        3. EMA - Media Movel Exponencial (alta variabilidade)
        4. Tendencia - Regressao Linear (tendencia forte)
        5. Sazonal - Decomposicao (padroes sazonais com 52+ semanas)
        6. TSB - Teunter-Syntetos-Babai (demanda intermitente)

        Args:
            df_historico: DataFrame com historico semanal
            ano_iso: Ano ISO da semana a prever
            semana_iso: Semana ISO a prever
            demanda_media_diaria: Se fornecida, usa como base para ajuste
            usar_metodo_inteligente: Se True, usa os 6 metodos (padrao)
            cod_empresa: Codigo da empresa (para prior bayesiano)
            categoria: Categoria do produto (linha1)
            subcategoria: Subcategoria do produto (linha3)
            fornecedor: CNPJ do fornecedor
            curva_abc: Classificacao ABC do produto
            preco_referencia: Preco de venda para filtro por faixa

        Returns:
            Tupla (previsao_semanal, desvio_padrao, metadata)
        """
        # Fallback: usar demanda diaria * 7
        demanda_semanal_base = demanda_media_diaria * 7 if demanda_media_diaria and demanda_media_diaria > 0 else 0
        desvio_base = demanda_media_diaria * 2 if demanda_media_diaria and demanda_media_diaria > 0 else 0

        metadata_default = {
            'metodo_usado': 'fallback_diario',
            'confianca': 'baixa',
            'indice_sazonal_semana': 1.0
        }

        if df_historico.empty:
            # Sem historico, usar demanda diaria * 7 se disponivel
            return demanda_semanal_base, desvio_base, metadata_default

        # ========================================
        # METODO INTELIGENTE (6 metodos)
        # ========================================
        if usar_metodo_inteligente:
            # Calcular previsao base usando metodo inteligente com criterios combinados
            previsao_base, desvio_base_inteligente, metadata = self.calcular_previsao_inteligente_semanal(
                df_historico, cod_empresa, categoria, subcategoria, fornecedor, curva_abc, preco_referencia
            )

            # Calcular indice sazonal para ajuste fino
            indices = self.calcular_indice_semanal(df_historico)
            indice_semana = indices.get(semana_iso, 1.0)
            metadata['indice_sazonal_semana'] = round(indice_semana, 3)

            # Ajustar previsao pelo indice sazonal da semana especifica
            # Mas so se tivermos historico suficiente para confiar no indice
            if len(df_historico) >= 52:  # Pelo menos 1 ano
                # Indice confiavel - aplicar ajuste
                previsao_ajustada = previsao_base * indice_semana
                metadata['ajuste_sazonal_aplicado'] = True
            elif len(df_historico) >= 26:  # 6 meses
                # Indice parcialmente confiavel - aplicar com peso reduzido
                fator_ajuste = 0.5 + 0.5 * indice_semana  # Suaviza o indice
                previsao_ajustada = previsao_base * fator_ajuste
                metadata['ajuste_sazonal_aplicado'] = True
                metadata['ajuste_suavizado'] = True
            else:
                # Historico curto - nao aplicar ajuste sazonal
                previsao_ajustada = previsao_base
                metadata['ajuste_sazonal_aplicado'] = False

            # Garantir consistencia com demanda diaria base (se fornecida)
            if demanda_semanal_base > 0:
                # Limites de sanidade: 30% a 300% da base
                limite_min = demanda_semanal_base * 0.3
                limite_max = demanda_semanal_base * 3.0

                if previsao_ajustada < limite_min:
                    previsao_ajustada = max(previsao_ajustada, limite_min * 0.8)
                    metadata['ajuste_limite_minimo'] = True
                elif previsao_ajustada > limite_max:
                    previsao_ajustada = min(previsao_ajustada, limite_max)
                    metadata['ajuste_limite_maximo'] = True

            return max(0, previsao_ajustada), max(0, desvio_base_inteligente), metadata

        # ========================================
        # METODO LEGADO (indices sazonais simples)
        # ========================================
        # Mantido para compatibilidade se usar_metodo_inteligente=False

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
            media_historica = np.mean(hist_semana)
            desvio_historico = np.std(hist_semana, ddof=1) if len(hist_semana) > 1 else media_historica * 0.3
            previsao = 0.6 * media_historica + 0.4 * (media_recente * indice_semana)
        elif media_recente > 0:
            previsao = media_recente * indice_semana
            desvio_historico = media_recente * 0.3
        else:
            previsao = demanda_semanal_base * indice_semana if demanda_semanal_base > 0 else 0
            desvio_historico = desvio_base

        # Garantir consistencia
        if demanda_semanal_base > 0:
            indice_ajustado = indice_semana if indice_semana >= 0.5 else 1.0
            limite_minimo = demanda_semanal_base * 0.5 * indice_ajustado

            if previsao < limite_minimo:
                previsao = demanda_semanal_base * indice_ajustado
                desvio_historico = desvio_base
            elif previsao > demanda_semanal_base * 2:
                previsao = demanda_semanal_base * indice_ajustado

        metadata_legado = {
            'metodo_usado': 'indice_sazonal_legado',
            'confianca': 'media',
            'indice_sazonal_semana': round(indice_semana, 3)
        }

        return max(0, previsao), max(0, desvio_historico), metadata_legado

    def calcular_demanda_periodo_cobertura(
        self,
        codigo: int,
        cod_empresa: int,
        lead_time_dias: int,
        cobertura_dias: int,
        demanda_media_diaria: float = None,
        data_base: date = None,
        categoria: str = None,
        subcategoria: str = None,
        fornecedor: str = None,
        curva_abc: str = None,
        preco_referencia: float = None,
        usar_metodo_inteligente: bool = True
    ) -> Dict:
        """
        Calcula a demanda total para o periodo de cobertura usando previsao semanal.

        ATUALIZADO: Agora usa os 6 metodos inteligentes por padrao.
        Prior Bayesiano usa criterios COMBINADOS para encontrar produtos similares.

        Esta e a funcao principal que deve ser chamada pelo PedidoFornecedorIntegrado.

        Args:
            codigo: Codigo do produto
            cod_empresa: Codigo da empresa/loja
            lead_time_dias: Lead time do fornecedor em dias
            cobertura_dias: Dias de cobertura do pedido
            demanda_media_diaria: Demanda media diaria atual (para sanity check)
            data_base: Data base para calculo (default: hoje)
            categoria: Categoria do produto (linha1)
            subcategoria: Subcategoria do produto (linha3)
            fornecedor: CNPJ do fornecedor
            curva_abc: Classificacao ABC do produto
            preco_referencia: Preco de venda para filtro por faixa (±30%)
            usar_metodo_inteligente: Se True, usa os 6 metodos (padrao)

        Returns:
            Dicionario com:
            - demanda_total: Demanda total prevista para o periodo
            - demanda_por_dia: Demanda media diaria equivalente
            - semanas_cobertura: Lista de semanas e suas previsoes
            - detalhes: Informacoes adicionais do calculo
            - metodo_info: Informacoes sobre o metodo usado
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
        metodo_info = None  # Guardar info do primeiro calculo

        for i, (ano_iso, semana_iso, dias_na_semana) in enumerate(semanas):
            # Previsao para a semana completa com criterios combinados
            previsao_semanal, desvio_semanal, metadata = self.calcular_previsao_semana(
                df_historico,
                ano_iso,
                semana_iso,
                demanda_media_diaria,
                usar_metodo_inteligente=usar_metodo_inteligente,
                cod_empresa=cod_empresa,
                categoria=categoria,
                subcategoria=subcategoria,
                fornecedor=fornecedor,
                curva_abc=curva_abc,
                preco_referencia=preco_referencia
            )

            # Guardar metadata do primeiro calculo (mais relevante)
            if i == 0:
                metodo_info = metadata

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
                'proporcao': round(proporcao, 2),
                'indice_sazonal': metadata.get('indice_sazonal_semana', 1.0)
            })

        # Desvio total (raiz da soma das variancias)
        desvio_total = np.sqrt(desvio_total)

        # Demanda media por dia (para manter compatibilidade com interface)
        demanda_por_dia = demanda_total / cobertura_dias if cobertura_dias > 0 else 0

        # Semana atual e semana de entrega
        ano_atual, semana_atual = get_iso_week(data_base)
        data_entrega = data_base + timedelta(days=lead_time_dias)
        ano_entrega, semana_entrega = get_iso_week(data_entrega)

        # Determinar fator de seguranca recomendado baseado na serie
        fator_seguranca = metodo_info.get('fator_seguranca_recomendado', 1.0) if metodo_info else 1.0

        return {
            'demanda_total': round(demanda_total, 2),
            'demanda_por_dia': round(demanda_por_dia, 4),
            'desvio_padrao_total': round(desvio_total, 2),
            'semanas_cobertura': previsoes_semanas,
            'numero_semanas': len(semanas),
            'fator_seguranca_recomendado': fator_seguranca,
            'detalhes': {
                'data_base': data_base.isoformat(),
                'semana_atual': f'{ano_atual}-W{semana_atual:02d}',
                'data_entrega': data_entrega.isoformat(),
                'semana_entrega': f'{ano_entrega}-W{semana_entrega:02d}',
                'lead_time_dias': lead_time_dias,
                'cobertura_dias': cobertura_dias,
                'metodo': 'previsao_semanal_inteligente' if usar_metodo_inteligente else 'previsao_semanal_legado',
                'historico_usado': not df_historico.empty,
                'semanas_historico': len(df_historico),
                'demanda_diaria_base': demanda_media_diaria
            },
            'metodo_info': metodo_info or {
                'metodo_usado': 'desconhecido',
                'confianca': 'baixa'
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
