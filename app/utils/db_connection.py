"""
Configuracao e conexao com o banco de dados PostgreSQL
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor


# Configuracao do banco de dados
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'previsao_demanda'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'FerreiraCost@01'),
    'port': int(os.environ.get('DB_PORT', 5432))
}


def get_db_connection():
    """
    Cria conexao com o banco PostgreSQL.

    Returns:
        Conexao psycopg2 com encoding LATIN1
    """
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding('LATIN1')
    return conn


def get_db_cursor(dict_cursor=False):
    """
    Cria conexao e cursor para o banco.

    Args:
        dict_cursor: Se True, retorna cursor que retorna dicionarios

    Returns:
        Tupla (conexao, cursor)
    """
    conn = get_db_connection()
    if dict_cursor:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        cursor = conn.cursor()
    return conn, cursor
