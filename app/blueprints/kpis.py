"""
Blueprint: KPIs
Rotas: /kpis, /api/kpis/*
Painel de indicadores: Ruptura
"""

from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify
from psycopg2.extras import RealDictCursor

from app.utils.db_connection import get_db_connection

kpis_bp = Blueprint('kpis', __name__)


def decimal_to_float(obj):
    """Converte Decimal para float para serialização JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def format_result(result):
    """Formata resultado do banco convertendo Decimals."""
    if isinstance(result, dict):
        return {k: decimal_to_float(v) for k, v in result.items()}
    elif isinstance(result, list):
        return [format_result(r) for r in result]
    return decimal_to_float(result)


@kpis_bp.route('/kpis')
def kpis_page():
    """Pagina de indicadores de desempenho (KPIs)"""
    return render_template('kpis.html')


@kpis_bp.route('/api/kpis/filtros', methods=['GET'])
def api_kpis_filtros():
    """
    Retorna opcoes de filtros para a tela de KPIs.
    Linha3 agrupada por categoria para filtragem hierarquica no frontend.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Fornecedores
        cursor.execute("""
            SELECT DISTINCT nome_fornecedor
            FROM cadastro_produtos_completo
            WHERE nome_fornecedor IS NOT NULL AND TRIM(nome_fornecedor) != ''
            ORDER BY nome_fornecedor
        """)
        fornecedores = [r['nome_fornecedor'] for r in cursor.fetchall()]

        # Linha1 (Categorias)
        cursor.execute("""
            SELECT DISTINCT categoria
            FROM cadastro_produtos_completo
            WHERE categoria IS NOT NULL AND categoria != ''
            ORDER BY categoria
        """)
        categorias = [r['categoria'] for r in cursor.fetchall()]

        # Linha3 agrupada por categoria para o frontend filtrar
        cursor.execute("""
            SELECT DISTINCT categoria, codigo_linha, descricao_linha
            FROM cadastro_produtos_completo
            WHERE codigo_linha IS NOT NULL AND codigo_linha != ''
            AND categoria IS NOT NULL
            ORDER BY categoria, descricao_linha
        """)
        linhas3_rows = cursor.fetchall()

        # Agrupar linhas3 por categoria
        linhas3_por_categoria = {}
        for r in linhas3_rows:
            cat = r['categoria']
            if cat not in linhas3_por_categoria:
                linhas3_por_categoria[cat] = []
            linhas3_por_categoria[cat].append({
                'codigo': r['codigo_linha'],
                'descricao': r['descricao_linha'] or r['codigo_linha']
            })

        # Filiais
        cursor.execute("""
            SELECT cod_empresa, nome_loja
            FROM cadastro_lojas
            WHERE ativo = TRUE
            ORDER BY cod_empresa
        """)
        filiais = [{'codigo': r['cod_empresa'], 'nome': r['nome_loja']} for r in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({
            'fornecedores': fornecedores,
            'categorias': categorias,
            'linhas3_por_categoria': linhas3_por_categoria,
            'filiais': filiais
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_filtros: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@kpis_bp.route('/api/kpis/resumo', methods=['GET'])
def api_kpis_resumo():
    """
    Retorna resumo atual do KPI de Ruptura.
    Filtros: fornecedor, categoria, codigo_linha, cod_empresa
    """
    conn = None
    try:
        # Parametros de filtro
        fornecedores = request.args.getlist('fornecedor')
        categorias = request.args.getlist('categoria')
        linhas3 = request.args.getlist('codigo_linha')
        filiais = request.args.getlist('cod_empresa')
        dias = request.args.get('dias', default=30, type=int)

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        # Construir clausulas WHERE
        where_clauses = []
        params = []

        if fornecedores and fornecedores[0]:
            placeholders = ','.join(['%s'] * len(fornecedores))
            where_clauses.append(f"cpc.nome_fornecedor IN ({placeholders})")
            params.extend(fornecedores)

        if categorias and categorias[0]:
            placeholders = ','.join(['%s'] * len(categorias))
            where_clauses.append(f"cpc.categoria IN ({placeholders})")
            params.extend(categorias)

        if linhas3 and linhas3[0]:
            placeholders = ','.join(['%s'] * len(linhas3))
            where_clauses.append(f"cpc.codigo_linha IN ({placeholders})")
            params.extend(linhas3)

        if filiais and filiais[0]:
            placeholders = ','.join(['%s'] * len(filiais))
            where_clauses.append(f"hed.cod_empresa IN ({placeholders})")
            params.extend([int(f) for f in filiais])

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # =====================================================================
        # KPI 1: RUPTURA (% de pontos de abastecimento em ruptura)
        # Item ativo = NÃO está em NC, FL, CO ou EN na situação de compra
        # NC=Não Compra, FL=Fora de Linha, CO=Compra Ocasional, EN=Em Negociação
        # FF=Falta no Fornecedor (INCLUÍDO na ruptura - problema externo mas afeta cliente)
        # Ponto de Abastecimento = Item ativo × Loja × Dia
        # Ruptura = Pontos sem estoque / Total pontos × 100
        # =====================================================================
        # Determinar se precisa JOIN com cadastro_produtos_completo (apenas se tiver filtros)
        precisa_cpc = bool(fornecedores and fornecedores[0]) or bool(categorias and categorias[0]) or bool(linhas3 and linhas3[0])

        if precisa_cpc:
            # Com filtros de fornecedor/categoria/linha
            # Filtra: sit_compra não está em NC/FL/CO/EN (FF incluído na ruptura)
            # Usa estoque_posicao_atual para filtrar itens que já foram abastecidos
            query_ruptura = f"""
                SELECT
                    COUNT(DISTINCT (hed.codigo, hed.cod_empresa)) as total_itens,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as total_dias_ruptura,
                    COUNT(*) as total_pontos_abastecimento,
                    CASE WHEN COUNT(*) > 0
                        THEN ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2)
                        ELSE 0 END as taxa_ruptura
                FROM historico_estoque_diario hed
                INNER JOIN estoque_posicao_atual epa ON hed.codigo = epa.codigo AND hed.cod_empresa = epa.cod_empresa
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                LEFT JOIN situacao_compra_itens sci
                    ON hed.codigo = sci.codigo
                    AND hed.cod_empresa = sci.cod_empresa
                WHERE hed.data >= %s
                AND {where_sql}
                AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
            """
            query_params = [data_inicio] + params
        else:
            # Sem filtros - query mais rápida sem JOIN com cpc
            # Monta WHERE simplificado
            where_clauses_simple = ["hed.data >= %s"]
            params_simple = [data_inicio]
            if filiais and filiais[0]:
                placeholders = ','.join(['%s'] * len(filiais))
                where_clauses_simple.append(f"hed.cod_empresa IN ({placeholders})")
                params_simple.extend([int(f) for f in filiais])

            where_sql_simple = " AND ".join(where_clauses_simple)

            # Filtra: sit_compra não está em NC/FL/CO/EN (FF incluído na ruptura)
            # Usa estoque_posicao_atual para filtrar itens que já foram abastecidos
            query_ruptura = f"""
                SELECT
                    COUNT(DISTINCT (hed.codigo, hed.cod_empresa)) as total_itens,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as total_dias_ruptura,
                    COUNT(*) as total_pontos_abastecimento,
                    CASE WHEN COUNT(*) > 0
                        THEN ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2)
                        ELSE 0 END as taxa_ruptura
                FROM historico_estoque_diario hed
                INNER JOIN estoque_posicao_atual epa ON hed.codigo = epa.codigo AND hed.cod_empresa = epa.cod_empresa
                LEFT JOIN situacao_compra_itens sci
                    ON hed.codigo = sci.codigo
                    AND hed.cod_empresa = sci.cod_empresa
                WHERE {where_sql_simple}
                AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
            """
            query_params = params_simple

        try:
            cursor.execute(query_ruptura, query_params)
            ruptura = cursor.fetchone() or {}
        except Exception as e:
            print(f"[ERRO] Query Ruptura: {e}")
            conn.rollback()
            ruptura = {'taxa_ruptura': 0, 'total_itens': 0}

        # Calcular variacao vs periodo anterior
        data_inicio_anterior = (datetime.now() - timedelta(days=dias*2)).strftime('%Y-%m-%d')
        data_fim_anterior = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        # Ruptura anterior para comparacao (mesma metodologia - pontos de abastecimento)
        query_ruptura_ant = f"""
            WITH itens_com_demanda AS (
                SELECT DISTINCT codigo, cod_empresa
                FROM historico_vendas_diario
                WHERE data BETWEEN %s AND %s
                AND qtd_venda > 0
            ),
            pontos_abastecimento AS (
                SELECT
                    hed.codigo,
                    hed.cod_empresa,
                    hed.data,
                    CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END as em_ruptura
                FROM historico_estoque_diario hed
                INNER JOIN itens_com_demanda icd ON hed.codigo = icd.codigo AND hed.cod_empresa = icd.cod_empresa
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data BETWEEN %s AND %s
                AND {where_sql}
            )
            SELECT
                CASE WHEN COUNT(*) > 0
                    THEN ROUND(SUM(em_ruptura)::numeric / COUNT(*) * 100, 2)
                    ELSE 0 END as taxa_ruptura
            FROM pontos_abastecimento
        """
        try:
            cursor.execute(query_ruptura_ant, [data_inicio_anterior, data_fim_anterior, data_inicio_anterior, data_fim_anterior] + params)
            ruptura_ant = cursor.fetchone() or {}
        except Exception as e:
            print(f"[ERRO] Query Ruptura Anterior: {e}")
            conn.rollback()
            ruptura_ant = {'taxa_ruptura': 0}

        cursor.close()
        conn.close()

        # Calcular variação
        taxa_ruptura_atual = float(ruptura.get('taxa_ruptura') or 0)
        taxa_ruptura_anterior = float(ruptura_ant.get('taxa_ruptura') or 0)
        variacao_ruptura = round(taxa_ruptura_atual - taxa_ruptura_anterior, 2)

        # Formatar periodo para exibicao
        data_fim = datetime.now()
        data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        periodo_texto = f"{data_inicio_dt.strftime('%d/%m')} a {data_fim.strftime('%d/%m/%Y')}"

        # Retornar no formato esperado pelo JavaScript
        return jsonify({
            'periodo': periodo_texto,
            'dias': dias,
            'ruptura': {
                'valor': taxa_ruptura_atual,
                'variacao': variacao_ruptura,
                'total_itens': ruptura.get('total_itens') or 0,
                'total_pontos': ruptura.get('total_pontos_abastecimento') or 0,
                'total_ruptura': ruptura.get('total_dias_ruptura') or 0,
                'periodo': f'Ultimos {dias} dias'
            }
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_resumo: {e}")
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return jsonify({'success': False, 'erro': str(e)}), 500


@kpis_bp.route('/api/kpis/evolucao', methods=['GET'])
def api_kpis_evolucao():
    """
    Retorna dados de evolucao temporal dos KPIs para graficos.
    Granularidade: diario (30d), semanal (6m), mensal (12m)
    Agregacao: geral, fornecedor, linha, filial, item
    """
    try:
        # Parametros (aceita 'visao' ou 'granularidade' para compatibilidade com frontend)
        granularidade = request.args.get('visao') or request.args.get('granularidade', default='mensal')
        agregacao = request.args.get('agregacao', default='geral')
        fornecedores = request.args.getlist('fornecedor')
        categorias = request.args.getlist('categoria')
        linhas3 = request.args.getlist('codigo_linha')
        filiais = request.args.getlist('cod_empresa')
        codigos = request.args.getlist('codigo')  # Para agregacao por item

        # Definir periodo baseado na granularidade
        if granularidade == 'diario':
            dias = 30
            group_by = "hed.data"
        elif granularidade == 'semanal':
            dias = 180  # 6 meses
            group_by = "DATE_TRUNC('week', hed.data)"
        else:  # mensal
            dias = 365  # 12 meses
            group_by = "DATE_TRUNC('month', hed.data)"

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construir clausulas WHERE
        where_clauses = ["hed.data >= %s"]
        params = [data_inicio]

        if fornecedores and fornecedores[0]:
            placeholders = ','.join(['%s'] * len(fornecedores))
            where_clauses.append(f"cpc.nome_fornecedor IN ({placeholders})")
            params.extend(fornecedores)

        if categorias and categorias[0]:
            placeholders = ','.join(['%s'] * len(categorias))
            where_clauses.append(f"cpc.categoria IN ({placeholders})")
            params.extend(categorias)

        if linhas3 and linhas3[0]:
            placeholders = ','.join(['%s'] * len(linhas3))
            where_clauses.append(f"cpc.codigo_linha IN ({placeholders})")
            params.extend(linhas3)

        if filiais and filiais[0]:
            placeholders = ','.join(['%s'] * len(filiais))
            where_clauses.append(f"hed.cod_empresa IN ({placeholders})")
            params.extend([int(f) for f in filiais])

        if codigos and codigos[0]:
            placeholders = ','.join(['%s'] * len(codigos))
            where_clauses.append(f"hed.codigo IN ({placeholders})")
            params.extend([int(c) for c in codigos])

        where_sql = " AND ".join(where_clauses)

        # Definir campo de agregacao
        if agregacao == 'fornecedor':
            agg_field = "cpc.nome_fornecedor"
            agg_name = "nome_fornecedor"
        elif agregacao == 'linha':
            agg_field = "cpc.categoria"
            agg_name = "categoria"
        elif agregacao == 'filial':
            agg_field = "hed.cod_empresa"
            agg_name = "cod_empresa"
        elif agregacao == 'item':
            agg_field = "hed.codigo"
            agg_name = "codigo"
        else:  # geral
            agg_field = "'Geral'"
            agg_name = "grupo"

        # =====================================================================
        # EVOLUÇÃO RUPTURA
        # Indicador de disponibilidade de estoque do sortimento ativo
        # Item ativo = NÃO está em NC, FL, CO ou EN na situação de compra
        # NC=Não Compra, FL=Fora de Linha, CO=Compra Ocasional, EN=Em Negociação
        # FF=Falta no Fornecedor (INCLUÍDO na ruptura - problema externo mas afeta cliente)
        # Ponto de abastecimento = Item ativo × Loja × Dia
        # Ruptura = Pontos sem estoque / Total de pontos × 100
        # =====================================================================
        if granularidade == 'diario':
            period_format = "TO_CHAR({group_by}, 'DD/MM')".format(group_by=group_by)
        elif granularidade == 'semanal':
            period_format = "TO_CHAR({group_by}, 'DD/MM/YY')".format(group_by=group_by)
        else:  # mensal
            period_format = "TO_CHAR({group_by}, 'MM/YYYY')".format(group_by=group_by)

        # Determinar se precisa JOIN com cadastro_produtos_completo
        precisa_cpc_evolucao = bool(fornecedores and fornecedores[0]) or bool(categorias and categorias[0]) or bool(linhas3 and linhas3[0])

        if precisa_cpc_evolucao:
            # Com filtros - mantém JOIN com cpc
            # Filtra: sit_compra não está em NC/FL/CO/EN (FF incluído na ruptura)
            # Usa estoque_posicao_atual para filtrar itens que já foram abastecidos
            query_ruptura = f"""
                SELECT
                    {group_by} as periodo,
                    {period_format} as periodo_label,
                    'Geral' as {agg_name},
                    COUNT(*) as total_pontos,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as pontos_ruptura,
                    CASE WHEN COUNT(*) > 0
                        THEN ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2)
                        ELSE 0 END as taxa_ruptura
                FROM historico_estoque_diario hed
                INNER JOIN estoque_posicao_atual epa ON hed.codigo = epa.codigo AND hed.cod_empresa = epa.cod_empresa
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                LEFT JOIN situacao_compra_itens sci
                    ON hed.codigo = sci.codigo
                    AND hed.cod_empresa = sci.cod_empresa
                WHERE {where_sql}
                AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
                GROUP BY {group_by}
                ORDER BY {group_by}
            """
            query_params_evo = params
        else:
            # Sem filtros de fornecedor/categoria/linha - query mais rápida
            # Filtra: sit_compra não está em NC/FL/CO/EN (FF incluído na ruptura)
            # Usa estoque_posicao_atual para filtrar itens que já foram abastecidos
            query_ruptura = f"""
                SELECT
                    {group_by} as periodo,
                    {period_format} as periodo_label,
                    'Geral' as {agg_name},
                    COUNT(*) as total_pontos,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as pontos_ruptura,
                    CASE WHEN COUNT(*) > 0
                        THEN ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 2)
                        ELSE 0 END as taxa_ruptura
                FROM historico_estoque_diario hed
                INNER JOIN estoque_posicao_atual epa ON hed.codigo = epa.codigo AND hed.cod_empresa = epa.cod_empresa
                LEFT JOIN situacao_compra_itens sci
                    ON hed.codigo = sci.codigo
                    AND hed.cod_empresa = sci.cod_empresa
                WHERE hed.data >= %s
                AND (sci.sit_compra IS NULL OR sci.sit_compra NOT IN ('NC', 'FL', 'CO', 'EN'))
                GROUP BY {group_by}
                ORDER BY {group_by}
            """
            query_params_evo = [data_inicio]

        cursor.execute(query_ruptura, query_params_evo)
        evolucao_ruptura = format_result(cursor.fetchall())

        cursor.close()
        conn.close()

        # Formatar dados para o JavaScript (formato esperado: periodo, valor, melhor_historico)
        valores_ruptura = [r.get('taxa_ruptura', 0) for r in evolucao_ruptura if r.get('taxa_ruptura') is not None]
        melhor_ruptura = min(valores_ruptura) if valores_ruptura else 0

        def formatar_evolucao(dados, campo_valor, melhor_valor=None):
            resultado = []
            for d in dados:
                resultado.append({
                    'periodo': d.get('periodo_label', ''),
                    'valor': d.get(campo_valor, 0),
                    'melhor_historico': melhor_valor
                })
            return resultado

        return jsonify({
            'ruptura': formatar_evolucao(evolucao_ruptura, 'taxa_ruptura', melhor_ruptura)
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_evolucao: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500


@kpis_bp.route('/api/kpis/ranking', methods=['GET'])
def api_kpis_ranking():
    """
    Retorna ranking de itens/grupos por KPI.
    Ordenacao e paginacao configuravel.
    """
    try:
        # Parametros
        ordenar_por = request.args.get('ordenar_por', default='ruptura')
        ordem = request.args.get('ordem', default='desc')  # asc ou desc
        agregacao = request.args.get('agregacao', default='item')
        pagina = request.args.get('pagina', default=1, type=int)
        por_pagina = request.args.get('por_pagina', default=20, type=int)
        dias = request.args.get('dias', default=30, type=int)

        # Filtros
        fornecedores = request.args.getlist('fornecedor')
        categorias = request.args.getlist('categoria')
        linhas3 = request.args.getlist('codigo_linha')
        filiais = request.args.getlist('cod_empresa')

        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construir WHERE
        where_clauses = []
        params = [data_inicio]

        if fornecedores and fornecedores[0]:
            placeholders = ','.join(['%s'] * len(fornecedores))
            where_clauses.append(f"cpc.nome_fornecedor IN ({placeholders})")
            params.extend(fornecedores)

        if categorias and categorias[0]:
            placeholders = ','.join(['%s'] * len(categorias))
            where_clauses.append(f"cpc.categoria IN ({placeholders})")
            params.extend(categorias)

        if linhas3 and linhas3[0]:
            placeholders = ','.join(['%s'] * len(linhas3))
            where_clauses.append(f"cpc.codigo_linha IN ({placeholders})")
            params.extend(linhas3)

        if filiais and filiais[0]:
            placeholders = ','.join(['%s'] * len(filiais))
            where_clauses.append(f"hed.cod_empresa IN ({placeholders})")
            params.extend([int(f) for f in filiais])

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        # Definir agrupamento
        if agregacao == 'fornecedor':
            group_fields = "cpc.nome_fornecedor"
            select_fields = "cpc.nome_fornecedor as nome, NULL as codigo, NULL as descricao"
        elif agregacao == 'linha':
            group_fields = "cpc.categoria, cpc.codigo_linha, cpc.descricao_linha"
            select_fields = "cpc.categoria as nome, cpc.codigo_linha as codigo, cpc.descricao_linha as descricao"
        elif agregacao == 'filial':
            group_fields = "hed.cod_empresa"
            select_fields = "cl.nome_loja as nome, hed.cod_empresa as codigo, NULL as descricao"
        else:  # item
            group_fields = "hed.codigo, cpc.descricao, cpc.nome_fornecedor"
            select_fields = "hed.codigo, cpc.descricao, cpc.nome_fornecedor"

        # Validar ordenacao
        ordem_sql = "DESC" if ordem.lower() == 'desc' else "ASC"
        if ordenar_por not in ['ruptura']:
            ordenar_por = 'ruptura'

        # Query de ranking
        offset = (pagina - 1) * por_pagina

        if agregacao == 'item':
            query = f"""
                SELECT
                    hed.codigo,
                    cpc.descricao,
                    cpc.nome_fornecedor as fornecedor,
                    ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as ruptura
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s {where_sql}
                GROUP BY hed.codigo, cpc.descricao, cpc.nome_fornecedor
                HAVING COUNT(*) >= 5
                ORDER BY ruptura {ordem_sql} NULLS LAST
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, params + [por_pagina, offset])
        else:
            # Agregacao por fornecedor, linha ou filial
            join_loja = "LEFT JOIN cadastro_lojas cl ON hed.cod_empresa = cl.cod_empresa" if agregacao == 'filial' else ""

            query = f"""
                SELECT
                    {select_fields},
                    COUNT(*) as total_registros,
                    SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END) as registros_ruptura,
                    ROUND(SUM(CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*), 0) * 100, 2) as ruptura
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                {join_loja}
                WHERE hed.data >= %s {where_sql}
                GROUP BY {group_fields}
                ORDER BY ruptura {ordem_sql} NULLS LAST
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, params + [por_pagina, offset])

        ranking = format_result(cursor.fetchall())

        # Contar total para paginacao
        if agregacao == 'item':
            query_count = f"""
                SELECT COUNT(DISTINCT hed.codigo) as total
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s {where_sql}
            """
        else:
            query_count = f"""
                SELECT COUNT(DISTINCT {group_fields.split(',')[0]}) as total
                FROM historico_estoque_diario hed
                LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
                WHERE hed.data >= %s {where_sql}
            """
        cursor.execute(query_count, params)
        total = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        # Formatar itens para o formato esperado pelo JavaScript
        itens = []
        for r in ranking:
            if agregacao == 'item':
                itens.append({
                    'identificador': str(r.get('codigo', '')),
                    'descricao': r.get('descricao', ''),
                    'ruptura': r.get('ruptura'),
                    'total_skus': 1,
                    'skus_ruptura': 1 if r.get('ruptura', 0) > 0 else 0
                })
            elif agregacao == 'fornecedor':
                itens.append({
                    'identificador': r.get('nome', ''),
                    'descricao': '',
                    'ruptura': r.get('ruptura'),
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })
            elif agregacao == 'linha':
                itens.append({
                    'identificador': f"{r.get('codigo', '')} - {r.get('descricao', '')}",
                    'descricao': r.get('nome', ''),
                    'ruptura': r.get('ruptura'),
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })
            elif agregacao == 'filial':
                itens.append({
                    'identificador': str(r.get('codigo', '')),
                    'descricao': r.get('nome', ''),
                    'ruptura': r.get('ruptura'),
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })
            else:  # geral
                itens.append({
                    'identificador': 'Geral',
                    'descricao': '',
                    'ruptura': r.get('ruptura'),
                    'total_skus': r.get('total_registros', 0),
                    'skus_ruptura': r.get('registros_ruptura', 0)
                })

        total_paginas = (total + por_pagina - 1) // por_pagina if total > 0 else 1

        return jsonify({
            'itens': itens,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total': total,
            'total_paginas': total_paginas
        })

    except Exception as e:
        import traceback
        print(f"[ERRO] api_kpis_ranking: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'erro': str(e)}), 500
