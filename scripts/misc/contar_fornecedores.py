# -*- coding: utf-8 -*-
"""
Script para contar fornecedores únicos (por CNPJ)
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
    print("  FORNECEDORES ÚNICOS (por CNPJ)")
    print("=" * 80)

    # Contar CNPJs únicos
    cur.execute("""
        SELECT COUNT(DISTINCT cnpj) as total
        FROM cadastro_fornecedores
    """)
    total = cur.fetchone()['total']
    print(f"\n  TOTAL DE FORNECEDORES ÚNICOS: {total}")

    # Listar todos os fornecedores únicos com seus nomes
    cur.execute("""
        SELECT DISTINCT cnpj, nome_fantasia
        FROM cadastro_fornecedores
        ORDER BY nome_fantasia
    """)
    fornecedores = cur.fetchall()

    print(f"\n  Lista completa:")
    print(f"  {'#':<4} {'CNPJ':<18} {'Nome Fantasia':<50}")
    print("  " + "-" * 75)

    for i, f in enumerate(fornecedores, 1):
        cnpj = f['cnpj'] or 'N/A'
        nome = (f['nome_fantasia'] or 'N/A')[:48]
        print(f"  {i:<4} {cnpj:<18} {nome:<50}")

    print("\n" + "=" * 80)
    print(f"  TOTAL: {total} fornecedores únicos")
    print("=" * 80)

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
