# -*- coding: utf-8 -*-
"""
Script para verificar status de dados por fornecedor:
- Última data de demanda histórica
- Posição de estoque
- Dados de cadastro faltantes
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import sys

# Forçar encoding UTF-8 na saída
sys.stdout.reconfigure(encoding='utf-8')

DB_CONFIG = {
    'host': 'localhost',
    'database': 'demanda_reabastecimento',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def print_separator(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =========================================================================
    # 0. VERIFICAR ESTRUTURA DOS DADOS
    # =========================================================================
    print_separator("VERIFICANDO ESTRUTURA DOS DADOS")

    # Verificar se há fornecedores cadastrados
    cur.execute("SELECT COUNT(*) as total FROM cadastro_fornecedores")
    total_forn = cur.fetchone()['total']
    print(f"\n  Fornecedores na tabela cadastro_fornecedores: {total_forn}")

    # Verificar produtos
    cur.execute("SELECT COUNT(*) as total FROM cadastro_produtos")
    total_prod = cur.fetchone()['total']
    print(f"  Produtos na tabela cadastro_produtos: {total_prod}")

    # Verificar se produtos têm fornecedor vinculado
    cur.execute("SELECT COUNT(*) as total FROM cadastro_produtos WHERE id_fornecedor IS NOT NULL")
    prod_com_forn = cur.fetchone()['total']
    print(f"  Produtos com fornecedor vinculado: {prod_com_forn}")

    # Verificar campos de fornecedor nos produtos
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'cadastro_produtos'
        AND column_name LIKE '%fornec%'
    """)
    cols_forn = cur.fetchall()
    print(f"  Colunas de fornecedor em cadastro_produtos: {[c['column_name'] for c in cols_forn]}")

    # Verificar se há um campo código_fornecedor ou similar
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'cadastro_produtos'
    """)
    all_cols = cur.fetchall()
    print(f"\n  Todas as colunas de cadastro_produtos:")
    for col in all_cols:
        print(f"    - {col['column_name']}")

    # =========================================================================
    # 1. STATUS POR PRODUTO (já que não há fornecedores)
    # =========================================================================
    print_separator("STATUS DE DEMANDA HISTÓRICA POR PRODUTO")

    query_demanda = """
    SELECT
        p.codigo,
        p.descricao,
        p.categoria,
        p.curva_abc,
        MIN(v.data) as primeira_data_venda,
        MAX(v.data) as ultima_data_venda,
        SUM(v.qtd_venda) as total_vendas,
        COUNT(v.id) as total_registros
    FROM cadastro_produtos p
    LEFT JOIN historico_vendas_diario v ON p.codigo = v.codigo
    GROUP BY p.codigo, p.descricao, p.categoria, p.curva_abc
    ORDER BY p.descricao
    LIMIT 50
    """

    cur.execute(query_demanda)
    resultados_demanda = cur.fetchall()

    print(f"\n{'Código':<12} {'Descrição':<35} {'Categoria':<12} {'ABC':<5} {'Primeira':<12} {'Última':<12} {'Vendas':<12}")
    print("-" * 110)

    produtos_sem_demanda = []
    for r in resultados_demanda:
        codigo = str(r['codigo'])[:10]
        desc = (r['descricao'] or 'N/A')[:33]
        cat = (r['categoria'] or 'N/A')[:10]
        abc = r['curva_abc'] or '-'
        primeira = r['primeira_data_venda'].strftime('%Y-%m-%d') if r['primeira_data_venda'] else 'SEM DADOS'
        ultima = r['ultima_data_venda'].strftime('%Y-%m-%d') if r['ultima_data_venda'] else 'SEM DADOS'
        total_v = f"{r['total_vendas']:,.0f}" if r['total_vendas'] else '0'

        print(f"{codigo:<12} {desc:<35} {cat:<12} {abc:<5} {primeira:<12} {ultima:<12} {total_v:<12}")

        if not r['ultima_data_venda']:
            produtos_sem_demanda.append(r['descricao'])

    # =========================================================================
    # 2. STATUS DE ESTOQUE POR PRODUTO
    # =========================================================================
    print_separator("STATUS DE ESTOQUE POR PRODUTO")

    query_estoque = """
    SELECT
        p.codigo,
        p.descricao,
        p.categoria,
        SUM(e.qtd_estoque) as estoque_total,
        SUM(e.qtd_disponivel) as estoque_disponivel,
        COUNT(DISTINCT e.cod_empresa) as qtd_lojas,
        MAX(e.data_atualizacao) as ultima_atualizacao
    FROM cadastro_produtos p
    LEFT JOIN estoque_atual e ON p.codigo = e.codigo
    GROUP BY p.codigo, p.descricao, p.categoria
    ORDER BY p.descricao
    LIMIT 50
    """

    cur.execute(query_estoque)
    resultados_estoque = cur.fetchall()

    print(f"\n{'Código':<12} {'Descrição':<35} {'Lojas':<8} {'Est.Total':<12} {'Disponível':<12} {'Últ.Atualização':<18}")
    print("-" * 110)

    produtos_sem_estoque = []
    for r in resultados_estoque:
        codigo = str(r['codigo'])[:10]
        desc = (r['descricao'] or 'N/A')[:33]
        lojas = r['qtd_lojas'] or 0
        est_total = f"{r['estoque_total']:,.0f}" if r['estoque_total'] else '0'
        est_disp = f"{r['estoque_disponivel']:,.0f}" if r['estoque_disponivel'] else '0'
        ultima = r['ultima_atualizacao'].strftime('%Y-%m-%d %H:%M') if r['ultima_atualizacao'] else 'SEM DADOS'

        print(f"{codigo:<12} {desc:<35} {lojas:<8} {est_total:<12} {est_disp:<12} {ultima:<18}")

        if not r['ultima_atualizacao']:
            produtos_sem_estoque.append(r['descricao'])

    # =========================================================================
    # 3. ANÁLISE DE CADASTRO DE PRODUTOS
    # =========================================================================
    print_separator("ANÁLISE DE CADASTRO DE PRODUTOS")

    query_cadastro = """
    SELECT
        codigo,
        descricao,
        categoria,
        subcategoria,
        curva_abc,
        und_venda,
        id_fornecedor
    FROM cadastro_produtos
    ORDER BY descricao
    """

    cur.execute(query_cadastro)
    resultados_cadastro = cur.fetchall()

    print(f"\n{'Código':<12} {'Descrição':<35} {'Categoria':<12} {'ABC':<5} {'Unidade':<10} {'Fornecedor':<12}")
    print("-" * 100)

    produtos_cadastro_incompleto = []
    for r in resultados_cadastro:
        codigo = str(r['codigo'])[:10]
        desc = (r['descricao'] or 'N/A')[:33]
        cat = (r['categoria'] or 'FALTA')[:10]
        abc = r['curva_abc'] or 'FALTA'
        und = r['und_venda'] or 'FALTA'
        forn = str(r['id_fornecedor']) if r['id_fornecedor'] else 'FALTA'

        print(f"{codigo:<12} {desc:<35} {cat:<12} {abc:<5} {und:<10} {forn:<12}")

        # Verificar campos faltantes
        campos_faltantes = []
        if not r['categoria']:
            campos_faltantes.append('Categoria')
        if not r['curva_abc']:
            campos_faltantes.append('Curva ABC')
        if not r['und_venda']:
            campos_faltantes.append('Unidade')
        if not r['id_fornecedor']:
            campos_faltantes.append('Fornecedor')

        if campos_faltantes:
            produtos_cadastro_incompleto.append({
                'codigo': r['codigo'],
                'descricao': r['descricao'],
                'campos': campos_faltantes
            })

    # =========================================================================
    # 4. RESUMO POR LOJA
    # =========================================================================
    print_separator("RESUMO POR LOJA")

    query_lojas = """
    SELECT
        l.cod_empresa,
        l.nome_loja,
        COUNT(DISTINCT v.codigo) as produtos_com_venda,
        MAX(v.data) as ultima_venda,
        SUM(e.qtd_estoque) as estoque_total,
        COUNT(DISTINCT e.codigo) as produtos_com_estoque
    FROM cadastro_lojas l
    LEFT JOIN historico_vendas_diario v ON l.cod_empresa = v.cod_empresa
    LEFT JOIN estoque_atual e ON l.cod_empresa = e.cod_empresa
    WHERE l.ativo = true
    GROUP BY l.cod_empresa, l.nome_loja
    ORDER BY l.cod_empresa
    """

    cur.execute(query_lojas)
    resultados_lojas = cur.fetchall()

    print(f"\n{'Cód':<6} {'Loja':<30} {'Prod.Venda':<12} {'Últ.Venda':<12} {'Prod.Estoque':<14} {'Est.Total':<12}")
    print("-" * 100)

    for r in resultados_lojas:
        cod = str(r['cod_empresa'])
        nome = (r['nome_loja'] or 'N/A')[:28]
        prod_v = r['produtos_com_venda'] or 0
        ult_v = r['ultima_venda'].strftime('%Y-%m-%d') if r['ultima_venda'] else 'SEM DADOS'
        prod_e = r['produtos_com_estoque'] or 0
        est_t = f"{r['estoque_total']:,.0f}" if r['estoque_total'] else '0'

        print(f"{cod:<6} {nome:<30} {prod_v:<12} {ult_v:<12} {prod_e:<14} {est_t:<12}")

    # =========================================================================
    # 5. RESUMO EXECUTIVO
    # =========================================================================
    print_separator("RESUMO EXECUTIVO")

    # Totais gerais
    cur.execute("SELECT COUNT(*) as total FROM cadastro_fornecedores")
    total_fornecedores = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM cadastro_produtos")
    total_produtos = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as total FROM cadastro_lojas WHERE ativo = true")
    total_lojas = cur.fetchone()['total']

    cur.execute("SELECT MIN(data) as min_data, MAX(data) as max_data, COUNT(*) as registros FROM historico_vendas_diario")
    datas = cur.fetchone()

    cur.execute("SELECT SUM(qtd_estoque) as total, COUNT(*) as registros, MAX(data_atualizacao) as ultima FROM estoque_atual")
    estoque = cur.fetchone()

    print(f"\n  CADASTROS:")
    print(f"    - Fornecedores: {total_fornecedores}")
    print(f"    - Produtos: {total_produtos}")
    print(f"    - Lojas: {total_lojas}")

    print(f"\n  DEMANDA HISTÓRICA:")
    print(f"    - Primeira data: {datas['min_data']}")
    print(f"    - Última data: {datas['max_data']}")
    print(f"    - Total de registros: {datas['registros']:,}")

    print(f"\n  POSIÇÃO DE ESTOQUE:")
    if estoque['total']:
        print(f"    - Estoque Total: {estoque['total']:,.0f} unidades")
        print(f"    - Registros: {estoque['registros']:,}")
        print(f"    - Última atualização: {estoque['ultima']}")
    else:
        print(f"    - SEM DADOS DE ESTOQUE")

    # Alertas
    print("\n" + "-" * 80)
    print("  ALERTAS DE DADOS FALTANTES")
    print("-" * 80)

    if total_fornecedores == 0:
        print(f"\n  [!] ATENÇÃO: Nenhum fornecedor cadastrado na tabela cadastro_fornecedores")
        print(f"      Produtos não estão vinculados a fornecedores!")

    if produtos_sem_demanda:
        print(f"\n  [!] Produtos SEM histórico de demanda ({len(produtos_sem_demanda)}):")
        for p in produtos_sem_demanda[:5]:
            print(f"      - {p}")
        if len(produtos_sem_demanda) > 5:
            print(f"      ... e mais {len(produtos_sem_demanda) - 5} produtos")

    if produtos_sem_estoque:
        print(f"\n  [!] Produtos SEM posição de estoque ({len(produtos_sem_estoque)}):")
        for p in produtos_sem_estoque[:5]:
            print(f"      - {p}")
        if len(produtos_sem_estoque) > 5:
            print(f"      ... e mais {len(produtos_sem_estoque) - 5} produtos")

    if produtos_cadastro_incompleto:
        print(f"\n  [!] Produtos com CADASTRO INCOMPLETO ({len(produtos_cadastro_incompleto)}):")
        for p in produtos_cadastro_incompleto[:5]:
            print(f"      - {p['codigo']} ({p['descricao'][:30]}): falta {', '.join(p['campos'])}")
        if len(produtos_cadastro_incompleto) > 5:
            print(f"      ... e mais {len(produtos_cadastro_incompleto) - 5} produtos")

    if not produtos_sem_demanda and not produtos_sem_estoque and not produtos_cadastro_incompleto and total_fornecedores > 0:
        print("\n  [OK] Todos os dados estão completos!")

    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("  FIM DO RELATÓRIO")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
