#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para importar tabela de codigos DIG do Excel para PostgreSQL.

Uso:
    python database/importar_codigo_dig.py [caminho_arquivo.xlsx]

Se nenhum arquivo for especificado, usa o padrao 'CODIGOS AMANDA (1).xlsx'
"""

import sys
import os

# Adicionar o diretorio raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from app.utils.db_connection import get_db_connection


def criar_tabela_se_nao_existe(cursor):
    """Cria a tabela codigo_dig se nao existir."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS codigo_dig (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(20) NOT NULL UNIQUE,
            codigo_dig VARCHAR(20) NOT NULL,
            descricao VARCHAR(200),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_codigo_dig_codigo ON codigo_dig(codigo)")


def importar_codigo_dig(arquivo_excel):
    """Importa dados do Excel para a tabela codigo_dig."""

    print(f"Lendo arquivo: {arquivo_excel}")

    # Ler Excel
    df = pd.read_excel(arquivo_excel)

    # Verificar colunas esperadas
    colunas_esperadas = ['CODIGO', 'CODIGO_DIG']
    for col in colunas_esperadas:
        if col not in df.columns:
            raise ValueError(f"Coluna '{col}' nao encontrada no arquivo. Colunas disponiveis: {df.columns.tolist()}")

    # Preparar dados
    df['CODIGO'] = df['CODIGO'].astype(str).str.strip()
    df['CODIGO_DIG'] = df['CODIGO_DIG'].astype(str).str.strip()

    # Coluna descricao e opcional
    if 'DESCRICAO' in df.columns:
        df['DESCRICAO'] = df['DESCRICAO'].astype(str).str.strip()
    else:
        df['DESCRICAO'] = ''

    # Remover duplicatas (manter ultimo)
    df = df.drop_duplicates(subset=['CODIGO'], keep='last')

    print(f"Registros a importar: {len(df)}")

    # Conectar ao banco
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Criar tabela se nao existir
        criar_tabela_se_nao_existe(cursor)

        # Limpar dados existentes
        cursor.execute("DELETE FROM codigo_dig")

        # Inserir novos dados
        dados = [
            (row['CODIGO'], row['CODIGO_DIG'], row['DESCRICAO'][:200] if row['DESCRICAO'] else None)
            for _, row in df.iterrows()
        ]

        execute_values(
            cursor,
            """
            INSERT INTO codigo_dig (codigo, codigo_dig, descricao)
            VALUES %s
            ON CONFLICT (codigo) DO UPDATE SET
                codigo_dig = EXCLUDED.codigo_dig,
                descricao = EXCLUDED.descricao,
                updated_at = NOW()
            """,
            dados
        )

        conn.commit()

        # Verificar quantidade importada
        cursor.execute("SELECT COUNT(*) FROM codigo_dig")
        total = cursor.fetchone()[0]

        print(f"Importacao concluida com sucesso!")
        print(f"Total de registros na tabela: {total}")

    except Exception as e:
        conn.rollback()
        print(f"Erro na importacao: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    # Arquivo padrao ou passado por argumento
    if len(sys.argv) > 1:
        arquivo = sys.argv[1]
    else:
        # Arquivo padrao na raiz do projeto
        arquivo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'CODIGOS AMANDA (1).xlsx'
        )

    if not os.path.exists(arquivo):
        print(f"Arquivo nao encontrado: {arquivo}")
        sys.exit(1)

    importar_codigo_dig(arquivo)
