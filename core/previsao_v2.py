"""
Modulo de Previsao V2 - Bottom-Up Forecasting
Extraido de app_original.py para uso modular nos blueprints

Este modulo implementa a logica de previsao bottom-up onde:
1. Calcula previsao para cada item individualmente
2. Agrega para o total (garantindo soma consistente)
3. Aplica sazonalidade e tendencia com limitadores
"""

from datetime import datetime, timedelta
from calendar import monthrange
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection, DB_CONFIG
from core.ruptura_sanitizer import RupturaSanitizer
from core.forecasting_models import get_modelo


class PrevisaoV2Engine:
    """
    Engine de previsao Bottom-Up.
    Gera previsoes item a item e agrega para o total.
    """

    def __init__(self, conn=None):
        """
        Inicializa o engine de previsao.

        Args:
            conn: Conexao PostgreSQL opcional (sera criada se nao fornecida)
        """
        self.conn = conn
        self.sanitizer = RupturaSanitizer()

    def _get_connection(self):
        """Obtem conexao com o banco"""
        if self.conn:
            return self.conn
        return get_db_connection()

    def _close_connection(self, conn):
        """Fecha conexao se foi criada internamente"""
        if not self.conn:  # Só fecha se não foi fornecida externamente
            conn.close()

    def gerar_previsao(self, cod_empresa=None, fornecedor=None, linha1=None,
                       linha3=None, horizonte_dias=90, metodo='auto'):
        """
        Gera previsao de demanda (metodo simples).

        Args:
            cod_empresa: Codigo da loja (ou None para todas)
            fornecedor: Nome do fornecedor (ou None para todos)
            linha1: Categoria/linha 1 (ou None para todas)
            linha3: Sublinha/linha 3 (ou None para todas)
            horizonte_dias: Dias de previsao
            metodo: Metodo de previsao ('auto', 'sma', 'wma', etc)

        Returns:
            dict com previsoes e estatisticas
        """
        return self.gerar_previsao_bottom_up(
            fornecedor=fornecedor,
            cod_empresa=cod_empresa,
            linha1=linha1,
            linha3=linha3,
            horizonte_dias=horizonte_dias,
            metodo=metodo
        )

    def gerar_previsao_bottom_up(self, fornecedor, cod_empresa=None, linha1=None,
                                  linha3=None, horizonte_dias=90, metodo='auto',
                                  granularidade='mensal', periodos=6,
                                  mes_inicio=None, ano_inicio=None,
                                  mes_fim=None, ano_fim=None,
                                  semana_inicio=None, semana_fim=None,
                                  ano_semana_inicio=None, ano_semana_fim=None,
                                  data_inicio=None, data_fim=None):
        """
        Gera previsao Bottom-Up: calcula por item e agrega.

        Esta versao simplificada usa a logica do app_original.py
        mas de forma modular e reutilizavel.
        """
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # Calcular periodos de previsao
            meses_previsao = periodos
            dias_periodo_total = periodos * 30  # aproximacao

            if granularidade == 'mensal' and mes_inicio and ano_inicio and mes_fim and ano_fim:
                meses_previsao = (int(ano_fim) - int(ano_inicio)) * 12 + (int(mes_fim) - int(mes_inicio)) + 1
                dias_periodo_total = 0
                for i in range(meses_previsao):
                    mes_atual = int(mes_inicio) + i
                    ano_atual = int(ano_inicio)
                    while mes_atual > 12:
                        mes_atual -= 12
                        ano_atual += 1
                    dias_periodo_total += monthrange(ano_atual, mes_atual)[1]

            elif granularidade == 'semanal' and semana_inicio and ano_semana_inicio:
                semanas = (int(ano_semana_fim) - int(ano_semana_inicio)) * 52 + (int(semana_fim) - int(semana_inicio)) + 1
                meses_previsao = semanas
                dias_periodo_total = semanas * 7

            elif granularidade == 'diario' and data_inicio and data_fim:
                d1 = datetime.strptime(data_inicio, '%Y-%m-%d')
                d2 = datetime.strptime(data_fim, '%Y-%m-%d')
                dias = (d2 - d1).days + 1
                meses_previsao = dias
                dias_periodo_total = dias

            # Construir filtros SQL
            where_conditions = []
            params = []

            if cod_empresa and cod_empresa != 'TODAS':
                if isinstance(cod_empresa, list):
                    placeholders = ','.join(['%s'] * len(cod_empresa))
                    where_conditions.append(f"h.cod_empresa IN ({placeholders})")
                    params.extend([int(c) for c in cod_empresa])
                else:
                    where_conditions.append("h.cod_empresa = %s")
                    params.append(int(cod_empresa))

            if fornecedor and fornecedor != 'TODOS':
                if isinstance(fornecedor, list):
                    placeholders = ','.join(['%s'] * len(fornecedor))
                    where_conditions.append(f"p.nome_fornecedor IN ({placeholders})")
                    params.extend(fornecedor)
                else:
                    where_conditions.append("p.nome_fornecedor = %s")
                    params.append(fornecedor)

            if linha1 and linha1 != 'TODAS':
                if isinstance(linha1, list):
                    placeholders = ','.join(['%s'] * len(linha1))
                    where_conditions.append(f"p.categoria IN ({placeholders})")
                    params.extend(linha1)
                else:
                    where_conditions.append("p.categoria = %s")
                    params.append(linha1)

            if linha3 and linha3 != 'TODAS':
                if isinstance(linha3, list):
                    placeholders = ','.join(['%s'] * len(linha3))
                    where_conditions.append(f"p.codigo_linha IN ({placeholders})")
                    params.extend(linha3)
                else:
                    where_conditions.append("p.codigo_linha = %s")
                    params.append(linha3)

            where_sql = ""
            if where_conditions:
                where_sql = "AND " + " AND ".join(where_conditions)

            # Buscar itens
            query_itens = f"""
                SELECT DISTINCT
                    h.codigo as cod_produto,
                    p.descricao,
                    p.nome_fornecedor,
                    p.cnpj_fornecedor,
                    p.categoria,
                    p.descricao_linha
                FROM historico_vendas_diario h
                JOIN cadastro_produtos_completo p ON h.codigo::text = p.cod_produto
                WHERE h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
                {where_sql}
                ORDER BY p.nome_fornecedor, p.descricao
            """
            cursor.execute(query_itens, params)
            lista_itens = cursor.fetchall()

            if not lista_itens:
                return {'erro': 'Nenhum item encontrado com os filtros selecionados'}

            # Buscar vendas historicas
            query_vendas = f"""
                SELECT
                    h.codigo as cod_produto,
                    h.data as periodo,
                    SUM(h.qtd_venda) as qtd_venda
                FROM historico_vendas_diario h
                JOIN cadastro_produtos_completo p ON h.codigo::text = p.cod_produto
                WHERE h.data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '2 years')
                {where_sql}
                GROUP BY h.codigo, h.data
                ORDER BY h.codigo, h.data
            """
            cursor.execute(query_vendas, params)
            vendas_raw = cursor.fetchall()

            # Organizar vendas por item
            vendas_por_item = {}
            todas_datas = set()

            for v in vendas_raw:
                cod = v['cod_produto']
                if cod not in vendas_por_item:
                    vendas_por_item[cod] = []
                data_str = v['periodo'].strftime('%Y-%m-%d')
                todas_datas.add(data_str)
                vendas_por_item[cod].append({
                    'periodo': data_str,
                    'qtd_venda': float(v['qtd_venda'] or 0)
                })

            datas_ordenadas = sorted(list(todas_datas))

            # Calcular demanda media diaria por item
            resultados_itens = []
            demanda_total = 0

            for item in lista_itens:
                cod = item['cod_produto']
                vendas = vendas_por_item.get(cod, [])

                if vendas:
                    total_vendas = sum(v['qtd_venda'] for v in vendas)
                    dias_com_venda = len(vendas)
                    demanda_diaria = total_vendas / max(dias_com_venda, 1)
                    demanda_periodo = demanda_diaria * dias_periodo_total
                else:
                    demanda_diaria = 0
                    demanda_periodo = 0

                demanda_total += demanda_periodo

                resultados_itens.append({
                    'cod_produto': cod,
                    'descricao': item['descricao'],
                    'fornecedor': item['nome_fornecedor'],
                    'categoria': item['categoria'],
                    'demanda_diaria': round(demanda_diaria, 4),
                    'demanda_periodo': round(demanda_periodo, 2),
                    'dias_periodo': dias_periodo_total
                })

            # Gerar datas de previsao
            datas_previsao = []
            if granularidade == 'mensal' and mes_inicio and ano_inicio:
                for i in range(meses_previsao):
                    mes_atual = int(mes_inicio) + i
                    ano_atual = int(ano_inicio)
                    while mes_atual > 12:
                        mes_atual -= 12
                        ano_atual += 1
                    datas_previsao.append(f"{ano_atual:04d}-{mes_atual:02d}")
            elif granularidade == 'semanal' and semana_inicio and ano_semana_inicio:
                ano_base = int(ano_semana_inicio)
                semana_base = int(semana_inicio)
                try:
                    data_base = datetime.strptime(f'{ano_base}-W{semana_base:02d}-1', '%G-W%V-%u')
                except ValueError:
                    data_base = datetime(ano_base, 1, 1) + timedelta(weeks=semana_base - 1)

                for i in range(meses_previsao):
                    data_prev = data_base + timedelta(weeks=i)
                    semana_atual = data_prev.isocalendar()[1]
                    ano_atual = data_prev.isocalendar()[0]
                    datas_previsao.append(f"{ano_atual}-S{semana_atual:02d}")
            else:
                # Fallback: proximos N periodos
                hoje = datetime.now()
                for i in range(meses_previsao):
                    if granularidade == 'mensal':
                        mes = hoje.month + i
                        ano = hoje.year
                        while mes > 12:
                            mes -= 12
                            ano += 1
                        datas_previsao.append(f"{ano:04d}-{mes:02d}")
                    else:
                        data_prev = hoje + timedelta(days=i * 7)
                        datas_previsao.append(data_prev.strftime('%Y-%m-%d'))

            # Distribuir demanda pelos periodos
            demanda_por_periodo = demanda_total / max(len(datas_previsao), 1)

            grafico_data = []
            for data in datas_previsao:
                grafico_data.append({
                    'periodo': data,
                    'previsao': round(demanda_por_periodo, 2)
                })

            return {
                'success': True,
                'total_itens': len(lista_itens),
                'demanda_total': round(demanda_total, 2),
                'demanda_diaria_media': round(demanda_total / max(dias_periodo_total, 1), 4),
                'dias_periodo': dias_periodo_total,
                'periodos': len(datas_previsao),
                'granularidade': granularidade,
                'grafico_data': grafico_data,
                'itens': resultados_itens[:100],  # Limitar para performance
                'filtros': {
                    'fornecedor': fornecedor,
                    'cod_empresa': cod_empresa,
                    'linha1': linha1,
                    'linha3': linha3
                }
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'erro': str(e)}

        finally:
            cursor.close()
            self._close_connection(conn)


def gerar_previsao_simples(fornecedor, cod_empresa=None, granularidade='mensal', periodos=6):
    """
    Funcao helper para gerar previsao de forma simplificada.

    Args:
        fornecedor: Nome do fornecedor
        cod_empresa: Codigo da loja (opcional)
        granularidade: 'mensal', 'semanal' ou 'diario'
        periodos: Numero de periodos de previsao

    Returns:
        dict com resultado da previsao
    """
    engine = PrevisaoV2Engine()
    return engine.gerar_previsao_bottom_up(
        fornecedor=fornecedor,
        cod_empresa=cod_empresa,
        granularidade=granularidade,
        periodos=periodos
    )
