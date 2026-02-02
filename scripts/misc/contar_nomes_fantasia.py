# -*- coding: utf-8 -*-
"""
Script para contar fornecedores únicos por Nome Fantasia
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
    print("  FORNECEDORES ÚNICOS (por Nome Fantasia)")
    print("=" * 80)

    # Contar nomes fantasia únicos
    cur.execute("""
        SELECT COUNT(DISTINCT nome_fantasia) as total
        FROM cadastro_fornecedores
        WHERE nome_fantasia IS NOT NULL
    """)
    total = cur.fetchone()['total']
    print(f"\n  TOTAL DE NOMES FANTASIA ÚNICOS: {total}")

    # Comparar com CNPJs
    cur.execute("SELECT COUNT(DISTINCT cnpj) as total FROM cadastro_fornecedores")
    total_cnpj = cur.fetchone()['total']
    print(f"  Total de CNPJs únicos: {total_cnpj}")
    print(f"  Diferença: {total_cnpj - total}")

    # Verificar casos onde mesmo nome tem CNPJs diferentes (filiais)
    cur.execute("""
        SELECT nome_fantasia, COUNT(DISTINCT cnpj) as qtd_cnpjs
        FROM cadastro_fornecedores
        WHERE nome_fantasia IS NOT NULL
        GROUP BY nome_fantasia
        HAVING COUNT(DISTINCT cnpj) > 1
        ORDER BY qtd_cnpjs DESC
    """)
    filiais = cur.fetchall()

    if filiais:
        print(f"\n  Fornecedores com múltiplos CNPJs (filiais):")
        print(f"  {'Nome Fantasia':<40} {'CNPJs':<10}")
        print("  " + "-" * 50)
        for f in filiais:
            print(f"  {f['nome_fantasia']:<40} {f['qtd_cnpjs']:<10}")

    # Listar todos os nomes únicos
    cur.execute("""
        SELECT DISTINCT nome_fantasia
        FROM cadastro_fornecedores
        WHERE nome_fantasia IS NOT NULL
        ORDER BY nome_fantasia
    """)
    nomes = cur.fetchall()

    print(f"\n  Lista de todos os {total} nomes fantasia únicos:")
    print("  " + "-" * 50)
    for i, n in enumerate(nomes, 1):
        print(f"  {i:>4}. {n['nome_fantasia']}")

    print("\n" + "=" * 80)
    print(f"  RESUMO:")
    print(f"    - Nomes Fantasia únicos: {total}")
    print(f"    - CNPJs únicos: {total_cnpj}")
    print(f"    - Fornecedores com filiais (múltiplos CNPJs): {len(filiais)}")
    print("=" * 80)

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
