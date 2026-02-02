# -*- coding: utf-8 -*-
"""
Simulacao Comparativa: Metodos de Previsao por Granularidade
Compara o metodo atual (indices sazonais) vs 6 metodos inteligentes
para as granularidades: diaria, semanal e mensal
"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import get_db_connection
from core.demand_calculator import DemandCalculator

# Configuracao
FORNECEDOR = 'FORCELINE'  # Fornecedor para simulacao
MESES_PREVISAO = 6  # Quantos meses prever
LOJAS_AMOSTRA = [1, 2, 3, 5, 6]  # Algumas lojas para teste


def buscar_produtos_fornecedor(fornecedor_nome):
    """Busca produtos do fornecedor"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT p.codigo, p.descricao
        FROM cadastro_produtos p
        JOIN cadastro_fornecedores f ON p.id_fornecedor = f.id
        WHERE UPPER(f.nome_fantasia) LIKE %s
        AND p.ativo = TRUE
        LIMIT 20
    """, (f'%{fornecedor_nome.upper()}%',))

    produtos = cursor.fetchall()
    conn.close()
    return produtos


def buscar_historico_diario(codigo, cod_empresa, dias=730):
    """Busca historico diario de vendas"""
    conn = get_db_connection()
    cursor = conn.cursor()

    data_inicio = datetime.now() - timedelta(days=dias)

    cursor.execute("""
        SELECT data, COALESCE(qtd_venda, 0) as qtd
        FROM historico_vendas_diario
        WHERE codigo = %s AND cod_empresa = %s AND data >= %s
        ORDER BY data
    """, (codigo, cod_empresa, data_inicio))

    rows = cursor.fetchall()
    conn.close()

    # Preencher dias faltantes com 0
    historico = {}
    for row in rows:
        historico[row[0]] = float(row[1])

    # Criar serie completa
    serie = []
    data_atual = data_inicio.date() if hasattr(data_inicio, 'date') else data_inicio
    data_fim = datetime.now().date()

    while data_atual <= data_fim:
        serie.append(historico.get(data_atual, 0.0))
        data_atual += timedelta(days=1)

    return serie


def agregar_semanal(serie_diaria):
    """Agrega serie diaria em semanal"""
    semanas = []
    for i in range(0, len(serie_diaria), 7):
        semana = serie_diaria[i:i+7]
        if len(semana) == 7:
            semanas.append(sum(semana))
    return semanas


def agregar_mensal(serie_diaria):
    """Agrega serie diaria em mensal (aproximado 30 dias)"""
    meses = []
    for i in range(0, len(serie_diaria), 30):
        mes = serie_diaria[i:i+30]
        if len(mes) >= 28:  # Aceita meses com pelo menos 28 dias
            meses.append(sum(mes))
    return meses


def metodo_atual_semanal(serie_semanal, semanas_prever=26):
    """
    Metodo atual: Indices sazonais semanais
    Simplificado do weekly_forecast.py
    """
    if len(serie_semanal) < 52:
        # Fallback: media simples
        media = statistics.mean(serie_semanal) if serie_semanal else 0
        return [media] * semanas_prever

    # Calcular indices sazonais (52 semanas)
    indices = []
    media_geral = statistics.mean(serie_semanal) if serie_semanal else 1

    for semana_ano in range(52):
        valores_semana = [serie_semanal[i] for i in range(semana_ano, len(serie_semanal), 52)]
        if valores_semana:
            media_semana = statistics.mean(valores_semana)
            indice = media_semana / media_geral if media_geral > 0 else 1
        else:
            indice = 1
        indices.append(indice)

    # Prever proximas semanas
    previsoes = []
    semana_atual = datetime.now().isocalendar()[1]

    for i in range(semanas_prever):
        semana_prever = (semana_atual + i) % 52
        previsao = media_geral * indices[semana_prever]
        previsoes.append(max(0, previsao))

    return previsoes


def metodo_6_modelos(serie, granularidade='mensal'):
    """
    Usa os 6 metodos inteligentes do DemandCalculator
    """
    if not serie or len(serie) < 3:
        return {
            'previsao_total': 0,
            'metodo_selecionado': 'sem_dados',
            'demanda_diaria': 0,
            'confianca': 'baixa'
        }

    # Calcular previsao usando metodo inteligente
    demanda, desvio, metadata = DemandCalculator.calcular_demanda_inteligente(serie, metodo='auto')

    metodo = metadata.get('metodo_usado', 'desconhecido')

    # Calcular demanda diaria baseada na granularidade
    if granularidade == 'diario':
        demanda_diaria = demanda
    elif granularidade == 'semanal':
        demanda_diaria = demanda / 7  # Semana -> dia
    else:  # mensal
        demanda_diaria = demanda / 30  # Mes -> dia

    # Retornar previsao e metadados
    return {
        'previsao_total': demanda * 6 if granularidade == 'mensal' else demanda,
        'metodo_selecionado': metodo,
        'demanda_diaria': demanda_diaria,
        'confianca': metadata.get('confianca', 'media'),
        'desvio': desvio
    }


def executar_simulacao():
    """Executa simulacao comparativa"""

    print('='*80)
    print('SIMULACAO COMPARATIVA: METODOS DE PREVISAO POR GRANULARIDADE')
    print(f'Fornecedor: {FORNECEDOR}')
    print(f'Data: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    print('='*80)

    # Buscar produtos
    produtos = buscar_produtos_fornecedor(FORNECEDOR)
    if not produtos:
        print(f'Nenhum produto encontrado para {FORNECEDOR}')
        return

    print(f'\nProdutos encontrados: {len(produtos)}')

    # Resultados
    resultados = {
        'diario': {'atual': [], '6_metodos': []},
        'semanal': {'atual': [], '6_metodos': []},
        'mensal': {'atual': [], '6_metodos': []}
    }

    for codigo, descricao in produtos[:10]:  # Limitar a 10 produtos
        print(f'\n--- Produto {codigo}: {descricao[:40]}... ---')

        for loja in LOJAS_AMOSTRA[:3]:  # Limitar a 3 lojas
            # Buscar historico
            serie_diaria = buscar_historico_diario(codigo, loja)

            if not serie_diaria or sum(serie_diaria) == 0:
                continue

            serie_semanal = agregar_semanal(serie_diaria)
            serie_mensal = agregar_mensal(serie_diaria)

            print(f'  Loja {loja}: {len(serie_diaria)} dias, {len(serie_semanal)} semanas, {len(serie_mensal)} meses')

            # ===== GRANULARIDADE DIARIA =====
            # Metodo atual (nao existe especifico, usa media)
            if serie_diaria:
                media_diaria_atual = statistics.mean(serie_diaria[-90:]) if len(serie_diaria) >= 90 else statistics.mean(serie_diaria)
                previsao_diaria_atual = media_diaria_atual * 180  # 6 meses

                # 6 metodos
                resultado_6m_diario = metodo_6_modelos(serie_diaria[-365:], 'diario')
                previsao_diaria_6m = resultado_6m_diario['demanda_diaria'] * 180

                resultados['diario']['atual'].append(previsao_diaria_atual)
                resultados['diario']['6_metodos'].append(previsao_diaria_6m)

                print(f'    DIARIO  - Atual: {previsao_diaria_atual:.1f} | 6 Metodos: {previsao_diaria_6m:.1f} ({resultado_6m_diario["metodo_selecionado"]})')

            # ===== GRANULARIDADE SEMANAL =====
            if len(serie_semanal) >= 4:
                # Metodo atual (indices sazonais)
                previsoes_semanal_atual = metodo_atual_semanal(serie_semanal, 26)
                previsao_semanal_atual = sum(previsoes_semanal_atual)

                # 6 metodos
                resultado_6m_semanal = metodo_6_modelos(serie_semanal, 'semanal')
                # Converter para 26 semanas
                previsao_semanal_6m = resultado_6m_semanal['demanda_diaria'] * 7 * 26

                resultados['semanal']['atual'].append(previsao_semanal_atual)
                resultados['semanal']['6_metodos'].append(previsao_semanal_6m)

                print(f'    SEMANAL - Atual: {previsao_semanal_atual:.1f} | 6 Metodos: {previsao_semanal_6m:.1f} ({resultado_6m_semanal["metodo_selecionado"]})')

            # ===== GRANULARIDADE MENSAL =====
            if len(serie_mensal) >= 3:
                # Metodo atual para mensal JA USA 6 metodos
                resultado_mensal = metodo_6_modelos(serie_mensal, 'mensal')
                previsao_mensal = resultado_mensal['previsao_total']

                # Para comparacao, calcular com indice sazonal mensal
                if len(serie_mensal) >= 12:
                    media_mensal = statistics.mean(serie_mensal)
                    indices_mensais = []
                    for mes in range(12):
                        valores_mes = [serie_mensal[i] for i in range(mes, len(serie_mensal), 12)]
                        if valores_mes:
                            indice = statistics.mean(valores_mes) / media_mensal if media_mensal > 0 else 1
                        else:
                            indice = 1
                        indices_mensais.append(indice)

                    mes_atual = datetime.now().month - 1
                    previsao_mensal_indice = sum([media_mensal * indices_mensais[(mes_atual + i) % 12] for i in range(6)])
                else:
                    previsao_mensal_indice = statistics.mean(serie_mensal) * 6

                resultados['mensal']['atual'].append(previsao_mensal_indice)
                resultados['mensal']['6_metodos'].append(previsao_mensal)

                print(f'    MENSAL  - Indice: {previsao_mensal_indice:.1f} | 6 Metodos: {previsao_mensal:.1f} ({resultado_mensal["metodo_selecionado"]})')

    # ===== RESUMO ESTATISTICO =====
    print('\n' + '='*80)
    print('RESUMO ESTATISTICO')
    print('='*80)

    for granularidade in ['diario', 'semanal', 'mensal']:
        atual = resultados[granularidade]['atual']
        metodos6 = resultados[granularidade]['6_metodos']

        if not atual or not metodos6:
            print(f'\n{granularidade.upper()}: Dados insuficientes')
            continue

        # Calcular diferencas
        diferencas = []
        diferencas_pct = []
        for a, m in zip(atual, metodos6):
            if a > 0:
                diff = m - a
                diff_pct = (diff / a) * 100
                diferencas.append(diff)
                diferencas_pct.append(diff_pct)

        print(f'\n{granularidade.upper()}:')
        print(f'  Amostras: {len(atual)}')
        print(f'  Media Metodo Atual: {statistics.mean(atual):.1f}')
        print(f'  Media 6 Metodos: {statistics.mean(metodos6):.1f}')

        if diferencas_pct:
            print(f'  Diferenca Media: {statistics.mean(diferencas_pct):.1f}%')
            print(f'  Diferenca Min: {min(diferencas_pct):.1f}%')
            print(f'  Diferenca Max: {max(diferencas_pct):.1f}%')
            if len(diferencas_pct) > 1:
                print(f'  Desvio Padrao: {statistics.stdev(diferencas_pct):.1f}%')

    print('\n' + '='*80)
    print('CONCLUSAO')
    print('='*80)
    print('''
    A simulacao compara:
    - Metodo ATUAL: Indices sazonais (usado na semanal)
    - 6 METODOS: SMA, WMA, EMA, Regressao, Decomposicao Sazonal, TSB

    Se a diferenca for pequena (< 10%), os metodos sao equivalentes.
    Se a diferenca for grande, os 6 metodos podem estar capturando
    padroes que o indice sazonal nao captura (tendencias, intermitencia).
    ''')


if __name__ == '__main__':
    executar_simulacao()
