# -*- coding: utf-8 -*-
"""
Script para verificar todos os bancos e schemas disponíveis no PostgreSQL
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Conexão inicial ao postgres (banco padrão)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'postgres',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

def print_separator(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =========================================================================
    # 1. LISTAR TODOS OS BANCOS DE DADOS
    # =========================================================================
    print_separator("BANCOS DE DADOS DISPONÍVEIS")

    cur.execute("""
        SELECT datname, pg_size_pretty(pg_database_size(datname)) as tamanho
        FROM pg_database
        WHERE datistemplate = false
        ORDER BY pg_database_size(datname) DESC
    """)
    bancos = cur.fetchall()

    print(f"\n{'Banco de Dados':<40} {'Tamanho':<15}")
    print("-" * 55)
    for b in bancos:
        print(f"{b['datname']:<40} {b['tamanho']:<15}")

    cur.close()
    conn.close()

    # =========================================================================
    # 2. VERIFICAR CADA BANCO
    # =========================================================================
    for banco in bancos:
        db_name = banco['datname']
        if db_name in ['postgres', 'template0', 'template1']:
            continue

        print_separator(f"BANCO: {db_name}")

        try:
            conn = psycopg2.connect(
                host='localhost',
                database=db_name,
                user='postgres',
                password='FerreiraCost@01',
                port=5432
            )
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # Listar schemas
            cur.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schema_name
            """)
            schemas = cur.fetchall()
            print(f"\n  Schemas: {[s['schema_name'] for s in schemas]}")

            # Listar tabelas principais
            cur.execute("""
                SELECT table_schema, table_name,
                       pg_size_pretty(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))) as tamanho
                FROM information_schema.tables
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                AND table_type = 'BASE TABLE'
                ORDER BY pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name)) DESC
                LIMIT 20
            """)
            tabelas = cur.fetchall()

            print(f"\n  {'Schema':<15} {'Tabela':<40} {'Tamanho':<15}")
            print("  " + "-" * 70)
            for t in tabelas:
                print(f"  {t['table_schema']:<15} {t['table_name']:<40} {t['tamanho']:<15}")

            # Verificar se tem tabela de vendas
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name LIKE '%venda%' OR table_name LIKE '%historico%'
                AND table_schema NOT IN ('information_schema', 'pg_catalog')
            """)
            tabelas_vendas = cur.fetchall()
            if tabelas_vendas:
                print(f"\n  Tabelas de vendas/histórico encontradas:")
                for t in tabelas_vendas:
                    print(f"    - {t['table_name']}")

                    # Verificar quantidade de registros e período
                    try:
                        cur.execute(f"SELECT COUNT(*) as total FROM {t['table_name']}")
                        total = cur.fetchone()['total']
                        print(f"      Total de registros: {total:,}")

                        # Tentar pegar período
                        cur.execute(f"""
                            SELECT column_name FROM information_schema.columns
                            WHERE table_name = '{t['table_name']}'
                            AND column_name LIKE '%data%'
                        """)
                        cols_data = cur.fetchall()
                        if cols_data:
                            col_data = cols_data[0]['column_name']
                            cur.execute(f"SELECT MIN({col_data}) as min_data, MAX({col_data}) as max_data FROM {t['table_name']}")
                            periodo = cur.fetchone()
                            print(f"      Período: {periodo['min_data']} a {periodo['max_data']}")
                    except Exception as e:
                        print(f"      Erro ao consultar: {e}")

            # Verificar se tem tabela de fornecedor
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name LIKE '%fornec%'
                AND table_schema NOT IN ('information_schema', 'pg_catalog')
            """)
            tabelas_forn = cur.fetchall()
            if tabelas_forn:
                print(f"\n  Tabelas de fornecedor encontradas:")
                for t in tabelas_forn:
                    print(f"    - {t['table_name']}")
                    try:
                        cur.execute(f"SELECT COUNT(*) as total FROM {t['table_name']}")
                        total = cur.fetchone()['total']
                        print(f"      Total de registros: {total:,}")
                    except Exception as e:
                        print(f"      Erro: {e}")

            cur.close()
            conn.close()

        except Exception as e:
            print(f"  Erro ao conectar: {e}")

    print("\n" + "=" * 80)
    print("  FIM DA VERIFICAÇÃO")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
