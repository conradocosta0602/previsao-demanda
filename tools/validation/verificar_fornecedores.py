# -*- coding: utf-8 -*-
"""
Script para verificar a estrutura real dos fornecedores
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

sys.stdout.reconfigure(encoding='utf-8')

DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 80)
    print("  ANÁLISE DETALHADA DE FORNECEDORES")
    print("=" * 80)

    # 1. Total na tabela cadastro_fornecedores
    cur.execute("SELECT COUNT(*) as total FROM cadastro_fornecedores")
    total_cadastro = cur.fetchone()['total']
    print(f"\n1. Total em cadastro_fornecedores: {total_cadastro:,}")

    # 2. CNPJs únicos
    cur.execute("SELECT COUNT(DISTINCT cnpj) as total FROM cadastro_fornecedores")
    cnpjs_unicos = cur.fetchone()['total']
    print(f"2. CNPJs únicos: {cnpjs_unicos:,}")

    # 3. Verificar se há duplicação por empresa
    cur.execute("""
        SELECT cnpj, COUNT(*) as qtd, COUNT(DISTINCT cod_empresa) as empresas
        FROM cadastro_fornecedores
        GROUP BY cnpj
        ORDER BY qtd DESC
        LIMIT 10
    """)
    duplicados = cur.fetchall()
    print(f"\n3. Amostra de CNPJs (verificando duplicação por empresa):")
    print(f"   {'CNPJ':<18} {'Registros':<12} {'Empresas':<10}")
    print("   " + "-" * 40)
    for d in duplicados:
        print(f"   {d['cnpj']:<18} {d['qtd']:<12} {d['empresas']:<10}")

    # 4. Empresas distintas nos fornecedores
    cur.execute("SELECT DISTINCT cod_empresa FROM cadastro_fornecedores ORDER BY cod_empresa")
    empresas = cur.fetchall()
    print(f"\n4. Empresas com cadastro de fornecedores: {[e['cod_empresa'] for e in empresas]}")

    # 5. Verificar tabela parametros_fornecedor
    cur.execute("SELECT COUNT(*) as total FROM parametros_fornecedor")
    total_param = cur.fetchone()['total']
    print(f"\n5. Total em parametros_fornecedor: {total_param:,}")

    cur.execute("SELECT COUNT(DISTINCT cnpj_fornecedor) as total FROM parametros_fornecedor")
    cnpjs_param = cur.fetchone()['total']
    print(f"   CNPJs únicos em parâmetros: {cnpjs_param:,}")

    # 6. Verificar se há tabela de fornecedores completo
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name LIKE '%fornec%'
        ORDER BY table_name
    """)
    tabelas_forn = cur.fetchall()
    print(f"\n6. Tabelas relacionadas a fornecedor:")
    for t in tabelas_forn:
        cur.execute(f"SELECT COUNT(*) as total FROM {t['table_name']}")
        total = cur.fetchone()['total']
        print(f"   - {t['table_name']}: {total:,} registros")

    # 7. Verificar cadastro_fornecedores_completo
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'cadastro_fornecedores_completo'
        ORDER BY ordinal_position
    """)
    colunas = cur.fetchall()
    if colunas:
        print(f"\n7. Colunas de cadastro_fornecedores_completo:")
        print(f"   {[c['column_name'] for c in colunas]}")

        cur.execute("SELECT * FROM cadastro_fornecedores_completo LIMIT 5")
        amostra = cur.fetchall()
        print(f"\n   Amostra dos dados:")
        for a in amostra:
            print(f"   {dict(a)}")

    # 8. Então qual é o número REAL de fornecedores únicos?
    print("\n" + "=" * 80)
    print("  CONCLUSÃO")
    print("=" * 80)
    print(f"\n  O número {total_cadastro:,} está INFLADO porque a tabela cadastro_fornecedores")
    print(f"  tem um registro para cada combinação FORNECEDOR x EMPRESA.")
    print(f"\n  FORNECEDORES ÚNICOS (por CNPJ): {cnpjs_unicos:,}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
