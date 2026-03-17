# -*- coding: utf-8 -*-
"""
Script de Importacao de Estoque e CUE (Custo Unitario)
======================================================
Importa dados de estoque atual e custo unitario do arquivo de posicao de estoque.

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


def criar_tabela_estoque_posicao(conn):
    """Cria tabela para armazenar posicao de estoque atual com CUE."""
    cur = conn.cursor()

    # Criar tabela
    cur.execute("""
        CREATE TABLE IF NOT EXISTS estoque_posicao_atual (
            id SERIAL PRIMARY KEY,
            codigo INTEGER NOT NULL,
            cod_empresa INTEGER NOT NULL,
            estoque DECIMAL(12,2) DEFAULT 0,
            qtd_pendente DECIMAL(12,2) DEFAULT 0,
            qtd_pend_transf DECIMAL(12,2) DEFAULT 0,
            cue DECIMAL(12,4) DEFAULT 0,
            preco_venda DECIMAL(12,2) DEFAULT 0,
            sit_venda VARCHAR(10),
            curva_abc VARCHAR(5),
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(codigo, cod_empresa)
        )
    """)

    # Adicionar coluna curva_abc se nao existir
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='estoque_posicao_atual' AND column_name='curva_abc') THEN
                ALTER TABLE estoque_posicao_atual ADD COLUMN curva_abc VARCHAR(5);
            END IF;
        END $$;
    """)

    # Criar indices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_estoque_pos_codigo ON estoque_posicao_atual(codigo)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_estoque_pos_empresa ON estoque_posicao_atual(cod_empresa)")

    conn.commit()
    cur.close()
    print("Tabela estoque_posicao_atual criada/verificada.")


def importar_estoque(conn, arquivo):
    """Importa dados de estoque do arquivo Excel"""
    import shutil
    import tempfile

    cur = conn.cursor()

    print(f"Lendo arquivo: {arquivo}")

    # Copiar arquivo para temp para evitar problemas de permissao (arquivo aberto no Excel)
    try:
        df = pd.read_excel(arquivo)
    except PermissionError:
        print("  Arquivo em uso, criando copia temporaria...")
        temp_file = Path(tempfile.gettempdir()) / 'temp_posicao_estoque.xlsx'
        shutil.copy2(arquivo, temp_file)
        df = pd.read_excel(temp_file)
        temp_file.unlink()  # Remove arquivo temp

    print(f"Total de registros no arquivo: {len(df)}")
    print(f"Colunas: {df.columns.tolist()}")

    # Verificar colunas necessarias
    colunas_necessarias = ['CODIGO', 'COD_EMPRESA', 'ESTOQUE', 'CUE']
    for col in colunas_necessarias:
        if col not in df.columns:
            print(f"ERRO: Coluna {col} nao encontrada!")
            return 0

    # Limpar tabela existente
    print("\nLimpando dados existentes...")
    cur.execute("TRUNCATE TABLE estoque_posicao_atual RESTART IDENTITY")
    conn.commit()

    # Preparar dados para insercao
    dados = []
    for _, row in df.iterrows():
        try:
            codigo = int(row['CODIGO'])
            cod_empresa = int(row['COD_EMPRESA'])
            estoque = float(row['ESTOQUE']) if pd.notna(row['ESTOQUE']) else 0
            qtd_pendente = float(row['QTD_PENDENTE']) if pd.notna(row.get('QTD_PENDENTE', 0)) else 0
            qtd_pend_transf = float(row['QTD_PEND_TRANSF']) if pd.notna(row.get('QTD_PEND_TRANSF', 0)) else 0
            cue = float(row['CUE']) if pd.notna(row['CUE']) else 0
            preco_venda = float(row['PRECO_VENDA']) if pd.notna(row.get('PRECO_VENDA', 0)) else 0
            sit_venda = str(row['SIT_VENDA']).strip() if pd.notna(row.get('SIT_VENDA')) else None
            # Curva ABC - verificar diferentes nomes de coluna
            curva_abc = None
            for col_abc in ['CURVA_ABC_POPULARIDADE', 'CURVA_ABC', 'ABC']:
                if col_abc in row.index and pd.notna(row.get(col_abc)):
                    curva_abc = str(row[col_abc]).strip().upper()
                    break

            dados.append((codigo, cod_empresa, estoque, qtd_pendente, qtd_pend_transf, cue, preco_venda, sit_venda, curva_abc))
        except Exception as e:
            continue

    print(f"\nRegistros validos para importar: {len(dados)}")

    if not dados:
        print("Nenhum registro valido para importar.")
        return 0

    # Inserir em batch
    print("Inserindo dados...")
    execute_values(cur, """
        INSERT INTO estoque_posicao_atual
            (codigo, cod_empresa, estoque, qtd_pendente, qtd_pend_transf, cue, preco_venda, sit_venda, curva_abc)
        VALUES %s
        ON CONFLICT (codigo, cod_empresa) DO UPDATE SET
            estoque = EXCLUDED.estoque,
            qtd_pendente = EXCLUDED.qtd_pendente,
            qtd_pend_transf = EXCLUDED.qtd_pend_transf,
            cue = EXCLUDED.cue,
            preco_venda = EXCLUDED.preco_venda,
            sit_venda = EXCLUDED.sit_venda,
            curva_abc = EXCLUDED.curva_abc,
            data_importacao = CURRENT_TIMESTAMP
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
    cur.execute("SELECT COUNT(*) FROM estoque_posicao_atual")
    total = cur.fetchone()[0]
    print(f"Total de registros importados: {total:,}")

    # Registros com estoque > 0
    cur.execute("SELECT COUNT(*) FROM estoque_posicao_atual WHERE estoque > 0")
    com_estoque = cur.fetchone()[0]
    print(f"Registros com estoque > 0: {com_estoque:,}")

    # Registros com CUE > 0
    cur.execute("SELECT COUNT(*) FROM estoque_posicao_atual WHERE cue > 0")
    com_cue = cur.fetchone()[0]
    print(f"Registros com CUE > 0: {com_cue:,}")

    # Valor total em estoque
    cur.execute("SELECT SUM(estoque * cue) FROM estoque_posicao_atual WHERE estoque > 0 AND cue > 0")
    valor_total = cur.fetchone()[0] or 0
    print(f"Valor total em estoque: R$ {valor_total:,.2f}")

    # Por loja (top 10)
    cur.execute("""
        SELECT cod_empresa,
               COUNT(*) as itens,
               SUM(estoque) as total_estoque,
               SUM(estoque * cue) as valor
        FROM estoque_posicao_atual
        WHERE estoque > 0
        GROUP BY cod_empresa
        ORDER BY valor DESC
        LIMIT 10
    """)
    print("\nTop 10 lojas por valor em estoque:")
    for row in cur.fetchall():
        valor = row[3] or 0
        print(f"  Loja {row[0]}: {row[1]:,} itens, {row[2]:,.0f} un, R$ {valor:,.2f}")

    # Amostra de dados
    cur.execute("""
        SELECT codigo, cod_empresa, estoque, cue, estoque * cue as valor
        FROM estoque_posicao_atual
        WHERE estoque > 0 AND cue > 0
        ORDER BY estoque * cue DESC
        LIMIT 5
    """)
    print("\nTop 5 itens por valor em estoque:")
    for row in cur.fetchall():
        print(f"  Codigo {row[0]} (Loja {row[1]}): {row[2]:.0f} un x R$ {row[3]:.2f} = R$ {row[4]:,.2f}")

    cur.close()


def main():
    """Funcao principal"""
    print("=" * 60)
    print("IMPORTACAO DE ESTOQUE E CUE (CUSTO UNITARIO)")
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

    # Criar tabela
    criar_tabela_estoque_posicao(conn)

    # Importar
    total = importar_estoque(conn, ARQUIVO_ESTOQUE)

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
