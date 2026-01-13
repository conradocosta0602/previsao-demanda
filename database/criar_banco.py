# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Conectar ao banco padrão para criar novo banco
try:
    conn = psycopg2.connect(
        host='localhost',
        database='postgres',
        user='postgres',
        password='FerreiraCost@01',
        port=5432
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    # Verificar se banco já existe
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'demanda_reabastecimento'")
    existe = cursor.fetchone()

    if existe:
        print("Banco 'demanda_reabastecimento' ja existe!")
    else:
        print("Criando banco 'demanda_reabastecimento'...")
        cursor.execute("CREATE DATABASE demanda_reabastecimento WITH ENCODING = 'UTF8'")
        print("OK - Banco criado com sucesso!")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"ERRO: {e}")
    sys.exit(1)
