# -*- coding: utf-8 -*-
"""
Script para verificar status dos dados REAIS por fornecedor
Banco: previsao_demanda
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Conexão ao banco de dados REAL
DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def print_separator(title):
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)

def main():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =========================================================================
    # 1. RESUMO GERAL DO BANCO
    # =========================================================================
    print_separator("RESUMO GERAL - BANCO previsao_demanda (DADOS REAIS)")

    # Total de fornecedores
    cur.execute("SELECT COUNT(*) as total FROM cadastro_fornecedores")
    total_forn = cur.fetchone()['total']

    # Total de produtos
    cur.execute("SELECT COUNT(*) as total FROM cadastro_produtos")
    total_prod = cur.fetchone()['total']

    # Total de lojas
    cur.execute("SELECT COUNT(DISTINCT cod_empresa) as total FROM historico_vendas_diario")
    total_lojas = cur.fetchone()['total']

    print(f"\n  Fornecedores cadastrados: {total_forn:,}")
    print(f"  Produtos cadastrados: {total_prod:,}")
    print(f"  Lojas/Empresas: {total_lojas:,}")

    # Período de vendas
    cur.execute("SELECT MIN(data) as min_data, MAX(data) as max_data, COUNT(*) as registros FROM historico_vendas_diario")
    vendas = cur.fetchone()
    print(f"\n  Histórico de Vendas:")
    print(f"    - Período: {vendas['min_data']} a {vendas['max_data']}")
    print(f"    - Total de registros: {vendas['registros']:,}")

    # Período de estoque histórico
    cur.execute("SELECT MIN(data) as min_data, MAX(data) as max_data, COUNT(*) as registros FROM historico_estoque_diario")
    estoque_hist = cur.fetchone()
    print(f"\n  Histórico de Estoque:")
    print(f"    - Período: {estoque_hist['min_data']} a {estoque_hist['max_data']}")
    print(f"    - Total de registros: {estoque_hist['registros']:,}")

    # Estoque atual
    cur.execute("SELECT COUNT(*) as registros, MAX(data_importacao) as ultima FROM estoque_posicao_atual")
    est_atual = cur.fetchone()
    print(f"\n  Posição de Estoque Atual:")
    print(f"    - Registros: {est_atual['registros']:,}")
    print(f"    - Última importação: {est_atual['ultima']}")

    # =========================================================================
    # 2. STATUS POR FORNECEDOR - ÚLTIMA DATA DE DEMANDA
    # =========================================================================
    print_separator("STATUS POR FORNECEDOR - ÚLTIMA DATA DE DEMANDA HISTÓRICA (TOP 50)")

    # A relação é: cadastro_fornecedores.cnpj -> parametros_fornecedor.codigo_fornecedor
    # E produto -> fornecedor via id_fornecedor
    # Vamos usar a tabela de parâmetros que tem codigo_fornecedor

    query_demanda_forn = """
    SELECT
        f.cnpj,
        f.nome_fantasia,
        COUNT(DISTINCT p.codigo) as total_produtos,
        COUNT(DISTINCT v.codigo) as produtos_com_venda,
        MIN(v.data) as primeira_data_venda,
        MAX(v.data) as ultima_data_venda,
        SUM(v.qtd_venda) as total_vendas
    FROM cadastro_fornecedores f
    LEFT JOIN cadastro_produtos p ON f.id = p.id_fornecedor
    LEFT JOIN historico_vendas_diario v ON p.codigo = v.codigo
    GROUP BY f.id, f.cnpj, f.nome_fantasia
    HAVING COUNT(DISTINCT p.codigo) > 0
    ORDER BY MAX(v.data) DESC NULLS LAST
    LIMIT 50
    """

    cur.execute(query_demanda_forn)
    resultados = cur.fetchall()

    print(f"\n{'CNPJ':<18} {'Fornecedor':<35} {'Prod.':<8} {'C/Venda':<10} {'Última Data':<12} {'Total Vendas':<15}")
    print("-" * 110)

    for r in resultados:
        cnpj = str(r['cnpj'] or 'N/A')[:16]
        nome = (r['nome_fantasia'] or 'N/A')[:33]
        total_prod = r['total_produtos'] or 0
        prod_venda = r['produtos_com_venda'] or 0
        ultima = r['ultima_data_venda'].strftime('%Y-%m-%d') if r['ultima_data_venda'] else 'SEM DADOS'
        total_v = f"{r['total_vendas']:,.0f}" if r['total_vendas'] else '0'

        print(f"{cnpj:<18} {nome:<35} {total_prod:<8} {prod_venda:<10} {ultima:<12} {total_v:<15}")

    # Total de fornecedores sem venda
    cur.execute("""
        SELECT COUNT(*) as total
        FROM cadastro_fornecedores f
        WHERE EXISTS (
            SELECT 1 FROM cadastro_produtos p WHERE p.id_fornecedor = f.id
        )
        AND NOT EXISTS (
            SELECT 1 FROM cadastro_produtos p
            JOIN historico_vendas_diario v ON p.codigo = v.codigo
            WHERE p.id_fornecedor = f.id
        )
    """)
    total_sem_venda = cur.fetchone()['total']
    print(f"\n  >> Fornecedores com produtos mas SEM histórico de vendas: {total_sem_venda}")

    # =========================================================================
    # 3. STATUS POR FORNECEDOR - POSIÇÃO DE ESTOQUE
    # =========================================================================
    print_separator("STATUS POR FORNECEDOR - POSIÇÃO DE ESTOQUE ATUAL (TOP 50)")

    query_estoque_forn = """
    SELECT
        f.cnpj,
        f.nome_fantasia,
        COUNT(DISTINCT p.codigo) as total_produtos,
        COUNT(DISTINCT e.codigo) as produtos_com_estoque,
        SUM(e.estoque) as estoque_total
    FROM cadastro_fornecedores f
    LEFT JOIN cadastro_produtos p ON f.id = p.id_fornecedor
    LEFT JOIN estoque_posicao_atual e ON p.codigo = e.codigo
    GROUP BY f.id, f.cnpj, f.nome_fantasia
    HAVING COUNT(DISTINCT p.codigo) > 0
    ORDER BY SUM(e.estoque) DESC NULLS LAST
    LIMIT 50
    """

    cur.execute(query_estoque_forn)
    resultados = cur.fetchall()

    print(f"\n{'CNPJ':<18} {'Fornecedor':<35} {'Prod.':<8} {'C/Estoque':<12} {'Est.Total':<18}")
    print("-" * 100)

    for r in resultados:
        cnpj = str(r['cnpj'] or 'N/A')[:16]
        nome = (r['nome_fantasia'] or 'N/A')[:33]
        total_prod = r['total_produtos'] or 0
        prod_est = r['produtos_com_estoque'] or 0
        est_total = f"{r['estoque_total']:,.0f}" if r['estoque_total'] else '0'

        print(f"{cnpj:<18} {nome:<35} {total_prod:<8} {prod_est:<12} {est_total:<18}")

    # Total sem estoque
    cur.execute("""
        SELECT COUNT(*) as total
        FROM cadastro_fornecedores f
        WHERE EXISTS (
            SELECT 1 FROM cadastro_produtos p WHERE p.id_fornecedor = f.id
        )
        AND NOT EXISTS (
            SELECT 1 FROM cadastro_produtos p
            JOIN estoque_posicao_atual e ON p.codigo = e.codigo
            WHERE p.id_fornecedor = f.id
        )
    """)
    total_sem_estoque = cur.fetchone()['total']
    print(f"\n  >> Fornecedores com produtos mas SEM posição de estoque: {total_sem_estoque}")

    # =========================================================================
    # 4. VERIFICAR PARÂMETROS DE FORNECEDOR
    # =========================================================================
    print_separator("STATUS DOS PARÂMETROS DE FORNECEDOR")

    # Total de parâmetros
    cur.execute("SELECT COUNT(*) as total FROM parametros_fornecedor")
    total_param = cur.fetchone()['total']
    print(f"\n  Total de registros de parâmetros: {total_param:,}")

    # Verificar campos da tabela de parâmetros
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'parametros_fornecedor'
        ORDER BY ordinal_position
    """)
    colunas_param = [c['column_name'] for c in cur.fetchall()]
    print(f"  Colunas disponíveis: {colunas_param}")

    # Fornecedores sem parâmetros (usando cnpj_fornecedor)
    cur.execute("""
        SELECT COUNT(*) as total
        FROM cadastro_fornecedores f
        WHERE NOT EXISTS (
            SELECT 1 FROM parametros_fornecedor p
            WHERE p.cnpj_fornecedor = f.cnpj
        )
    """)
    sem_param = cur.fetchone()['total']
    print(f"  Fornecedores SEM parâmetros: {sem_param}")

    # Verificar lead time
    if 'lead_time_dias' in colunas_param:
        cur.execute("SELECT COUNT(*) as total FROM parametros_fornecedor WHERE lead_time_dias IS NULL OR lead_time_dias = 0")
        sem_lt = cur.fetchone()['total']
        print(f"  Parâmetros com Lead Time nulo/zero: {sem_lt}")

    # Amostra de fornecedores sem parâmetros
    if sem_param > 0 and sem_param < 100:
        cur.execute("""
            SELECT f.cnpj, f.nome_fantasia
            FROM cadastro_fornecedores f
            WHERE NOT EXISTS (
                SELECT 1 FROM parametros_fornecedor p
                WHERE p.cnpj_fornecedor = f.cnpj
            )
            LIMIT 10
        """)
        amostra = cur.fetchall()
        if amostra:
            print(f"\n  Amostra de fornecedores sem parâmetros:")
            for f in amostra:
                print(f"    - {f['cnpj']}: {f['nome_fantasia'][:40] if f['nome_fantasia'] else 'N/A'}")

    # =========================================================================
    # 5. PRODUTOS SEM FORNECEDOR
    # =========================================================================
    print_separator("PRODUTOS SEM FORNECEDOR VINCULADO")

    cur.execute("""
        SELECT COUNT(*) as total
        FROM cadastro_produtos
        WHERE id_fornecedor IS NULL
    """)
    prod_sem_forn = cur.fetchone()['total']
    print(f"\n  Produtos SEM fornecedor: {prod_sem_forn}")

    if prod_sem_forn > 0:
        cur.execute("""
            SELECT codigo, descricao
            FROM cadastro_produtos
            WHERE id_fornecedor IS NULL
            LIMIT 10
        """)
        amostra_prod = cur.fetchall()
        print(f"\n  Amostra de produtos sem fornecedor:")
        for p in amostra_prod:
            print(f"    - {p['codigo']}: {p['descricao'][:50] if p['descricao'] else 'N/A'}")

    # =========================================================================
    # 6. RESUMO POR LOJA/EMPRESA
    # =========================================================================
    print_separator("RESUMO POR LOJA/EMPRESA")

    query_lojas = """
    SELECT
        v.cod_empresa,
        COUNT(DISTINCT v.codigo) as produtos_com_venda,
        MAX(v.data) as ultima_venda,
        SUM(v.qtd_venda) as total_vendas
    FROM historico_vendas_diario v
    GROUP BY v.cod_empresa
    ORDER BY v.cod_empresa
    """

    cur.execute(query_lojas)
    lojas_vendas = cur.fetchall()

    print(f"\n{'Empresa':<10} {'Produtos c/ Venda':<20} {'Última Venda':<15} {'Total Vendas':<20}")
    print("-" * 70)
    for l in lojas_vendas:
        print(f"{l['cod_empresa']:<10} {l['produtos_com_venda']:<20} {l['ultima_venda']:<15} {l['total_vendas']:>18,}")

    # Estoque por empresa
    query_estoque_loja = """
    SELECT
        e.cod_empresa,
        COUNT(DISTINCT e.codigo) as produtos_com_estoque,
        SUM(e.estoque) as estoque_total
    FROM estoque_posicao_atual e
    GROUP BY e.cod_empresa
    ORDER BY e.cod_empresa
    """

    cur.execute(query_estoque_loja)
    lojas_estoque = cur.fetchall()

    print(f"\n{'Empresa':<10} {'Produtos c/ Estoque':<22} {'Estoque Total':<18}")
    print("-" * 55)
    for l in lojas_estoque:
        est = f"{l['estoque_total']:,.0f}" if l['estoque_total'] else '0'
        print(f"{l['cod_empresa']:<10} {l['produtos_com_estoque']:<22} {est:<18}")

    # =========================================================================
    # 7. ALERTAS FINAIS
    # =========================================================================
    print_separator("ALERTAS E RECOMENDAÇÕES")

    alertas = []

    if total_sem_venda > 0:
        alertas.append(f"[!] {total_sem_venda} fornecedores com produtos mas SEM histórico de vendas")

    if total_sem_estoque > 0:
        alertas.append(f"[!] {total_sem_estoque} fornecedores com produtos mas SEM posição de estoque")

    if sem_param > 0:
        alertas.append(f"[!] {sem_param} fornecedores SEM parâmetros (lead time, ciclo, etc)")

    if prod_sem_forn > 0:
        alertas.append(f"[!] {prod_sem_forn} produtos SEM fornecedor vinculado")

    if alertas:
        for a in alertas:
            print(f"\n  {a}")
    else:
        print("\n  [OK] Todos os dados estão completos!")

    cur.close()
    conn.close()

    print("\n" + "=" * 100)
    print("  FIM DO RELATÓRIO")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    main()
