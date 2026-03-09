"""
Script de importacao de SOLIs abertas para o banco de dados.
SOLIs = Solicitacoes de movimentacao de estoque entre filiais/CDs.

Uso:
    python database/importar_solis.py [caminho_csv]

Se nenhum caminho for fornecido, busca o CSV mais recente com padrao "Solis*".
"""

import sys
import os
import glob
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils.db_connection import get_db_connection


def criar_tabela(conn):
    """Cria a tabela solis_abertas se nao existir."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solis_abertas (
            id SERIAL PRIMARY KEY,
            codigo INTEGER NOT NULL,
            filial_origem INTEGER NOT NULL,
            filial_destino INTEGER NOT NULL,
            qtde NUMERIC(10,2) NOT NULL,
            codigo_soli BIGINT,
            dt_confirmacao DATE,
            data_importacao TIMESTAMP DEFAULT NOW()
        );
    """)

    # Indices
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_solis_codigo ON solis_abertas(codigo);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_solis_origem ON solis_abertas(filial_origem);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_solis_destino ON solis_abertas(filial_destino);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_solis_codigo_origem_destino
        ON solis_abertas(codigo, filial_origem, filial_destino);
    """)

    conn.commit()
    print("[SOLI] Tabela solis_abertas criada/verificada.")


def importar_csv(conn, caminho_csv):
    """Importa CSV de SOLIs para o banco."""
    print(f"[SOLI] Lendo arquivo: {caminho_csv}")
    df = pd.read_csv(caminho_csv)

    print(f"[SOLI] Total de registros no CSV: {len(df)}")
    print(f"[SOLI] Colunas: {list(df.columns)}")

    # Filtrar apenas SOLIs com data de confirmacao (autorizadas)
    df_confirmadas = df[df['dt_confirmacao_soli'].notna()].copy()
    print(f"[SOLI] Registros com confirmacao (autorizadas): {len(df_confirmadas)}")
    print(f"[SOLI] Registros sem confirmacao (ignorados): {len(df) - len(df_confirmadas)}")

    if len(df_confirmadas) == 0:
        print("[SOLI] Nenhuma SOLI autorizada encontrada. Nada a importar.")
        return 0

    # Limpar tabela antes de importar (posicao atualizada)
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE solis_abertas RESTART IDENTITY;")
    print("[SOLI] Tabela solis_abertas limpa.")

    # Preparar dados
    registros = 0
    erros = 0
    for _, row in df_confirmadas.iterrows():
        try:
            codigo = int(row['codigo_dig'])
            filial_origem = int(row['filial_origem_soli'])
            filial_destino = int(row['filial_destino_soli'])
            qtde = float(row['qtde_soli'])
            codigo_soli = int(row['codigo_soli']) if pd.notna(row['codigo_soli']) and row['codigo_soli'] != 0 else None
            dt_confirmacao = row['dt_confirmacao_soli'] if pd.notna(row['dt_confirmacao_soli']) else None

            cursor.execute("""
                INSERT INTO solis_abertas (codigo, filial_origem, filial_destino, qtde, codigo_soli, dt_confirmacao)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (codigo, filial_origem, filial_destino, qtde, codigo_soli, dt_confirmacao))
            registros += 1
        except Exception as e:
            erros += 1
            if erros <= 5:
                print(f"[SOLI] Erro na linha {_}: {e}")

    conn.commit()
    print(f"[SOLI] Importacao concluida: {registros} registros importados, {erros} erros.")

    # Estatisticas
    cursor.execute("SELECT COUNT(*) FROM solis_abertas")
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE filial_origem >= 80) as cd_origem,
            COUNT(*) FILTER (WHERE filial_origem < 80) as loja_origem,
            COUNT(DISTINCT codigo) as itens_unicos,
            SUM(qtde) as qtde_total
        FROM solis_abertas
    """)
    stats = cursor.fetchone()
    print(f"[SOLI] Resumo:")
    print(f"  Total no banco: {total}")
    print(f"  Origem CD: {stats[0]}, Origem Loja: {stats[1]}")
    print(f"  Itens unicos: {stats[2]}")
    print(f"  Quantidade total: {stats[3]:,.0f} unidades")

    return registros


def main():
    # Determinar caminho do CSV
    if len(sys.argv) > 1:
        caminho_csv = sys.argv[1]
    else:
        # Buscar CSV mais recente na pasta do projeto
        pasta_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        padrao = os.path.join(pasta_projeto, "Solis*.*")
        arquivos = glob.glob(padrao)
        if not arquivos:
            print("[SOLI] Nenhum arquivo de SOLIs encontrado na pasta do projeto.")
            print("[SOLI] Uso: python database/importar_solis.py [caminho_csv]")
            sys.exit(1)
        caminho_csv = max(arquivos, key=os.path.getmtime)
        print(f"[SOLI] Arquivo mais recente encontrado: {os.path.basename(caminho_csv)}")

    if not os.path.exists(caminho_csv):
        print(f"[SOLI] Arquivo nao encontrado: {caminho_csv}")
        sys.exit(1)

    conn = get_db_connection()
    try:
        criar_tabela(conn)
        importar_csv(conn, caminho_csv)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
