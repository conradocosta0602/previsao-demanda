# -*- coding: utf-8 -*-
"""
Script de Importacao de Situacao de Compra (SIT_COMPRA)
======================================================
Importa dados de SIT_COMPRA do arquivo de posicao de estoque para o banco.

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path

# Configuracao de encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIGURACOES
# ============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01'
}

# Caminho do arquivo - Atualizado para 20/01/2026
ARQUIVO_ESTOQUE = Path(__file__).parent.parent / 'Posição de Estoque 20_01_2026.xlsx'


# ============================================================================
# FUNCOES
# ============================================================================

def conectar_banco():
    """Conecta ao banco PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        print(f"ERRO ao conectar ao banco: {e}")
        sys.exit(1)


def importar_sit_compra(conn, arquivo):
    """Importa dados de SIT_COMPRA do arquivo Excel"""
    import shutil
    import tempfile

    cur = conn.cursor()

    print(f"Lendo arquivo: {arquivo}")

    # Copiar arquivo para temp para evitar problemas de permissao (arquivo aberto no Excel)
    try:
        df = pd.read_excel(arquivo)
    except PermissionError:
        print("  Arquivo em uso, criando copia temporaria...")
        temp_file = Path(tempfile.gettempdir()) / 'temp_sit_compra.xlsx'
        shutil.copy2(arquivo, temp_file)
        df = pd.read_excel(temp_file)
        temp_file.unlink()  # Remove arquivo temp

    print(f"Total de registros no arquivo: {len(df)}")
    print(f"Colunas: {df.columns.tolist()}")

    # Verificar se tem a coluna SIT_COMPRA
    if 'SIT_COMPRA' not in df.columns:
        print("ERRO: Coluna SIT_COMPRA nao encontrada!")
        return 0

    # Filtrar apenas registros com SIT_COMPRA preenchido
    df_sit = df[df['SIT_COMPRA'].notna() & (df['SIT_COMPRA'] != '')].copy()
    print(f"Registros com SIT_COMPRA preenchido: {len(df_sit)}")

    if df_sit.empty:
        print("Nenhum registro com SIT_COMPRA para importar.")
        return 0

    # Mostrar distribuicao
    print("\nDistribuicao de SIT_COMPRA:")
    print(df_sit['SIT_COMPRA'].value_counts())

    # Limpar tabela existente
    print("\nLimpando dados existentes...")
    cur.execute("DELETE FROM situacao_compra_itens")
    conn.commit()

    # Preparar dados para insercao
    # Colunas: cod_empresa, codigo, sit_compra
    dados = []
    for _, row in df_sit.iterrows():
        cod_empresa = int(row['COD_EMPRESA'])
        codigo = int(row['CODIGO'])
        sit_compra = str(row['SIT_COMPRA']).strip().upper()

        # Validar sit_compra (deve ser FL, NC, EN, CO ou FF)
        if sit_compra in ['FL', 'NC', 'EN', 'CO', 'FF']:
            dados.append((cod_empresa, codigo, sit_compra))

    print(f"\nRegistros validos para importar: {len(dados)}")

    if not dados:
        print("Nenhum registro valido para importar.")
        return 0

    # Inserir em batch
    print("Inserindo dados...")
    execute_values(cur, """
        INSERT INTO situacao_compra_itens (cod_empresa, codigo, sit_compra)
        VALUES %s
        ON CONFLICT (cod_empresa, codigo) DO UPDATE SET
            sit_compra = EXCLUDED.sit_compra,
            updated_at = CURRENT_TIMESTAMP
    """, dados)

    conn.commit()
    cur.close()

    return len(dados)


def verificar_importacao(conn):
    """Verifica estatisticas apos importacao"""
    cur = conn.cursor()

    print("\n" + "=" * 60)
    print("VERIFICACAO DA IMPORTACAO")
    print("=" * 60)

    # Total de registros
    cur.execute("SELECT COUNT(*) FROM situacao_compra_itens")
    total = cur.fetchone()[0]
    print(f"Total de registros importados: {total}")

    # Por situacao
    cur.execute("""
        SELECT sit_compra, COUNT(*) as qtd
        FROM situacao_compra_itens
        GROUP BY sit_compra
        ORDER BY qtd DESC
    """)
    print("\nPor situacao de compra:")
    for row in cur.fetchall():
        cur.execute("SELECT descricao FROM situacao_compra_regras WHERE codigo_situacao = %s", (row[0],))
        desc = cur.fetchone()
        desc_text = desc[0] if desc else 'Desconhecido'
        print(f"  {row[0]}: {row[1]:,} ({desc_text})")

    # Por loja (top 10)
    cur.execute("""
        SELECT cod_empresa, COUNT(*) as qtd
        FROM situacao_compra_itens
        GROUP BY cod_empresa
        ORDER BY qtd DESC
        LIMIT 10
    """)
    print("\nTop 10 lojas com mais itens bloqueados:")
    for row in cur.fetchall():
        print(f"  Loja {row[0]}: {row[1]:,} itens")

    cur.close()


def main():
    """Funcao principal"""
    print("=" * 60)
    print("IMPORTACAO DE SITUACAO DE COMPRA (SIT_COMPRA)")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Verificar se arquivo existe
    if not ARQUIVO_ESTOQUE.exists():
        print(f"ERRO: Arquivo nao encontrado: {ARQUIVO_ESTOQUE}")
        sys.exit(1)

    # Conectar
    print("Conectando ao banco de dados...")
    conn = conectar_banco()
    print("Conectado com sucesso!")

    # Importar
    total = importar_sit_compra(conn, ARQUIVO_ESTOQUE)

    # Verificar
    if total > 0:
        verificar_importacao(conn)

    # Fechar
    conn.close()

    print("\n" + "=" * 60)
    print("IMPORTACAO CONCLUIDA!")
    print("=" * 60)


if __name__ == '__main__':
    main()
