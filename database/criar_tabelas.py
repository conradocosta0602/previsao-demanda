# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from pathlib import Path

# Conectar ao banco
try:
    print("Conectando ao banco demanda_reabastecimento...")
    conn = psycopg2.connect(
        host='localhost',
        database='demanda_reabastecimento',
        user='postgres',
        password='FerreiraCost@01',
        port=5432
    )
    cursor = conn.cursor()
    print("OK - Conectado!")

    # Ler arquivo schema.sql
    schema_path = Path(__file__).parent / 'schema.sql'
    print(f"\nLendo arquivo: {schema_path}")

    with open(schema_path, 'r', encoding='utf-8') as f:
        sql_commands = f.read()

    print("OK - Arquivo lido!")
    print("\nExecutando comandos SQL...")
    print("(Isso pode levar alguns segundos...)")

    # Executar SQL
    cursor.execute(sql_commands)
    conn.commit()

    print("\nOK - Tabelas criadas com sucesso!")

    # Listar tabelas criadas
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    tabelas = cursor.fetchall()
    print(f"\nTotal de tabelas criadas: {len(tabelas)}")
    print("\nTabelas:")
    for tabela in tabelas:
        print(f"  - {tabela[0]}")

    cursor.close()
    conn.close()

    print("\n" + "="*60)
    print("BANCO DE DADOS PRONTO!")
    print("="*60)

except FileNotFoundError:
    print(f"ERRO: Arquivo schema.sql nao encontrado em {schema_path}")
    sys.exit(1)
except Exception as e:
    print(f"ERRO: {e}")
    sys.exit(1)
