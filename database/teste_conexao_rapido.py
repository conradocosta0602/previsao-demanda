# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        database='postgres',
        user='postgres',
        password='FerreiraCost@01',
        port=5432
    )
    print("OK - CONEXAO BEM-SUCEDIDA!")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0][:50]
    print(f"OK - PostgreSQL conectado: {version}...")
    cursor.close()
    conn.close()
    print("\nSENHA CORRETA: FerreiraCost@01")
except psycopg2.OperationalError as e:
    if "password" in str(e).lower() or "authentication" in str(e).lower():
        print("ERRO - Senha incorreta")
    else:
        print(f"ERRO - Problema de conexao: {e}")
except Exception as e:
    print(f"ERRO: {e}")
