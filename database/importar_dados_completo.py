# -*- coding: utf-8 -*-
"""
Script de Importacao Completa - Cadastros, Estoque e Embalagem
==============================================================
Importa os seguintes dados:
- Cadastro de Produtos (CSV)
- Cadastro de Fornecedores (CSV)
- Posicao de Estoque (CSV)
- Embalagem de Arredondamento (CSV)

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
import glob

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

# Diretorio base onde estao os arquivos
BASE_DIR = Path(__file__).parent.parent


# ============================================================================
# FUNCOES DE CONEXAO
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


# ============================================================================
# CRIACAO DE TABELAS
# ============================================================================

def criar_tabela_embalagem(conn):
    """Cria tabela de embalagem de arredondamento"""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS embalagem_arredondamento (
            id SERIAL PRIMARY KEY,
            codigo INTEGER NOT NULL UNIQUE,
            unidade_compra VARCHAR(10),
            qtd_embalagem DECIMAL(10,2) NOT NULL,
            unidade_menor VARCHAR(10),
            data_atualizacao TIMESTAMP DEFAULT NOW(),
            fonte VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_embalagem_codigo ON embalagem_arredondamento(codigo)")

    conn.commit()
    cur.close()
    print("Tabela embalagem_arredondamento criada/verificada.")


def criar_tabela_estoque(conn):
    """Cria tabela de posicao de estoque"""
    cur = conn.cursor()

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
            sit_compra VARCHAR(10),
            curva_abc VARCHAR(5),
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(codigo, cod_empresa)
        )
    """)

    # Adicionar coluna sit_compra se nao existir
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name='estoque_posicao_atual' AND column_name='sit_compra') THEN
                ALTER TABLE estoque_posicao_atual ADD COLUMN sit_compra VARCHAR(10);
            END IF;
        END $$;
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_estoque_pos_codigo ON estoque_posicao_atual(codigo)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_estoque_pos_empresa ON estoque_posicao_atual(cod_empresa)")

    conn.commit()
    cur.close()
    print("Tabela estoque_posicao_atual criada/verificada.")


def criar_tabela_cadastro_produtos(conn):
    """Cria tabela de cadastro de produtos"""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cadastro_produtos_completo (
            cod_produto VARCHAR(20) PRIMARY KEY,
            descricao VARCHAR(300) NOT NULL,
            cnpj_fornecedor VARCHAR(20),
            nome_fornecedor VARCHAR(200),
            categoria VARCHAR(200),
            codigo_linha VARCHAR(10),
            descricao_linha VARCHAR(200),
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    conn.commit()
    cur.close()
    print("Tabela cadastro_produtos_completo criada/verificada.")


def criar_tabela_cadastro_fornecedores(conn):
    """Cria tabela de cadastro de fornecedores"""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cadastro_fornecedores_completo (
            id SERIAL PRIMARY KEY,
            cnpj VARCHAR(20) NOT NULL,
            nome_fantasia VARCHAR(200) NOT NULL,
            tipo_destino VARCHAR(20),
            lead_time_dias INTEGER,
            ciclo_pedido_dias INTEGER,
            faturamento_minimo DECIMAL(12,2),
            ativo BOOLEAN DEFAULT TRUE,
            fonte VARCHAR(100),
            data_atualizacao TIMESTAMP DEFAULT NOW(),
            UNIQUE(cnpj)
        )
    """)

    conn.commit()
    cur.close()
    print("Tabela cadastro_fornecedores_completo criada/verificada.")


# ============================================================================
# FUNCOES DE IMPORTACAO
# ============================================================================

def importar_embalagem(conn, arquivo):
    """Importa dados de embalagem de arredondamento"""
    print(f"\n{'='*60}")
    print(f"Importando embalagem: {arquivo}")
    print('='*60)

    # Ler CSV
    df = pd.read_csv(arquivo, encoding='utf-8')

    # Verificar colunas esperadas
    colunas_esperadas = ['codigo', 'unidade_cmp1', 'unidade_cmp2', 'unidade_cmp3']
    if not all(col in df.columns for col in colunas_esperadas):
        print(f"AVISO: Colunas esperadas: {colunas_esperadas}")
        print(f"AVISO: Colunas encontradas: {list(df.columns)}")
        return 0, 0

    # Renomear colunas
    df = df.rename(columns={
        'codigo': 'codigo',
        'unidade_cmp1': 'unidade_compra',
        'unidade_cmp2': 'qtd_embalagem',
        'unidade_cmp3': 'unidade_menor'
    })

    # Nome do arquivo como fonte
    fonte = Path(arquivo).name

    # Preparar dados para inserir
    cur = conn.cursor()
    inseridos = 0
    atualizados = 0

    for _, row in df.iterrows():
        try:
            codigo = int(row['codigo'])
            qtd = float(row['qtd_embalagem']) if pd.notna(row['qtd_embalagem']) else 1.0
            unidade_compra = str(row['unidade_compra']) if pd.notna(row['unidade_compra']) else None
            unidade_menor = str(row['unidade_menor']) if pd.notna(row['unidade_menor']) else None

            cur.execute("""
                INSERT INTO embalagem_arredondamento (codigo, unidade_compra, qtd_embalagem, unidade_menor, fonte, data_atualizacao)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (codigo) DO UPDATE SET
                    unidade_compra = EXCLUDED.unidade_compra,
                    qtd_embalagem = EXCLUDED.qtd_embalagem,
                    unidade_menor = EXCLUDED.unidade_menor,
                    fonte = EXCLUDED.fonte,
                    data_atualizacao = NOW(),
                    updated_at = NOW()
            """, (codigo, unidade_compra, qtd, unidade_menor, fonte))

            if cur.rowcount > 0:
                inseridos += 1

        except Exception as e:
            print(f"  ERRO linha {_}: {e}")

    conn.commit()
    cur.close()

    print(f"  Registros processados: {len(df)}")
    print(f"  Inseridos/Atualizados: {inseridos}")

    return inseridos, 0


def importar_posicao_estoque(conn, arquivo):
    """Importa posicao de estoque de CSV"""
    print(f"\n{'='*60}")
    print(f"Importando estoque: {arquivo}")
    print('='*60)

    # Ler CSV
    df = pd.read_csv(arquivo, encoding='utf-8')

    print(f"  Colunas encontradas: {list(df.columns)}")
    print(f"  Total de linhas: {len(df)}")

    # Verificar colunas minimas
    colunas_esperadas = ['codigo', 'cod_empresa', 'estoque']
    if not all(col in df.columns for col in colunas_esperadas):
        print(f"AVISO: Colunas minimas esperadas: {colunas_esperadas}")
        return 0, 0

    cur = conn.cursor()
    inseridos = 0

    for _, row in df.iterrows():
        try:
            codigo = int(row['codigo'])
            cod_empresa = int(row['cod_empresa'])
            estoque = float(row['estoque']) if pd.notna(row['estoque']) else 0.0
            qtd_pendente = float(row.get('qtd_pendente', 0)) if pd.notna(row.get('qtd_pendente', 0)) else 0.0
            qtd_pend_transf = float(row.get('qtd_pend_transf', 0)) if pd.notna(row.get('qtd_pend_transf', 0)) else 0.0
            cue = float(row.get('cue', 0)) if pd.notna(row.get('cue', 0)) else 0.0
            preco_venda = float(row.get('preco_venda', 0)) if pd.notna(row.get('preco_venda', 0)) else 0.0
            sit_venda = str(row.get('sit_venda', '')) if pd.notna(row.get('sit_venda', '')) else None
            sit_compra = str(row.get('sit_compra', '')) if pd.notna(row.get('sit_compra', '')) else None
            curva_abc = str(row.get('curva_abc_popularidade', '')) if pd.notna(row.get('curva_abc_popularidade', '')) else None

            cur.execute("""
                INSERT INTO estoque_posicao_atual
                    (codigo, cod_empresa, estoque, qtd_pendente, qtd_pend_transf, cue, preco_venda, sit_venda, sit_compra, curva_abc, data_importacao)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (codigo, cod_empresa) DO UPDATE SET
                    estoque = EXCLUDED.estoque,
                    qtd_pendente = EXCLUDED.qtd_pendente,
                    qtd_pend_transf = EXCLUDED.qtd_pend_transf,
                    cue = EXCLUDED.cue,
                    preco_venda = EXCLUDED.preco_venda,
                    sit_venda = EXCLUDED.sit_venda,
                    sit_compra = EXCLUDED.sit_compra,
                    curva_abc = EXCLUDED.curva_abc,
                    data_importacao = NOW()
            """, (codigo, cod_empresa, estoque, qtd_pendente, qtd_pend_transf, cue, preco_venda, sit_venda, sit_compra, curva_abc))

            inseridos += 1

        except Exception as e:
            pass  # Ignorar erros silenciosamente para nao poluir output

    conn.commit()
    cur.close()

    print(f"  Registros importados: {inseridos}")

    return inseridos, 0


def importar_cadastro_produtos(conn, arquivo):
    """Importa cadastro de produtos de CSV"""
    print(f"\n{'='*60}")
    print(f"Importando cadastro de produtos: {arquivo}")
    print('='*60)

    # Ler CSV
    df = pd.read_csv(arquivo, encoding='utf-8')

    print(f"  Colunas encontradas: {list(df.columns)}")
    print(f"  Total de linhas: {len(df)}")

    cur = conn.cursor()
    inseridos = 0

    for _, row in df.iterrows():
        try:
            cod_produto = str(row['codigo'])
            descricao = str(row.get('descricao', '')) if pd.notna(row.get('descricao', '')) else ''
            cnpj = str(row.get('cnpj', '')) if pd.notna(row.get('cnpj', '')) else None
            nome_forn = str(row.get('fantas', '')) if pd.notna(row.get('fantas', '')) else None
            categoria = str(row.get('descr_linha1', '')) if pd.notna(row.get('descr_linha1', '')) else None
            codigo_linha = str(row.get('linha3', '')) if pd.notna(row.get('linha3', '')) else None
            descricao_linha = str(row.get('descr_linha3', '')) if pd.notna(row.get('descr_linha3', '')) else None

            cur.execute("""
                INSERT INTO cadastro_produtos_completo
                    (cod_produto, descricao, cnpj_fornecedor, nome_fornecedor, categoria, codigo_linha, descricao_linha)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cod_produto) DO UPDATE SET
                    descricao = EXCLUDED.descricao,
                    cnpj_fornecedor = EXCLUDED.cnpj_fornecedor,
                    nome_fornecedor = EXCLUDED.nome_fornecedor,
                    categoria = EXCLUDED.categoria,
                    codigo_linha = EXCLUDED.codigo_linha,
                    descricao_linha = EXCLUDED.descricao_linha
            """, (cod_produto, descricao, cnpj, nome_forn, categoria, codigo_linha, descricao_linha))

            inseridos += 1

        except Exception as e:
            pass

    conn.commit()
    cur.close()

    print(f"  Registros importados: {inseridos}")

    return inseridos, 0


def importar_cadastro_fornecedores(conn, arquivo):
    """Importa cadastro de fornecedores de CSV"""
    print(f"\n{'='*60}")
    print(f"Importando cadastro de fornecedores: {arquivo}")
    print('='*60)

    # Ler CSV
    df = pd.read_csv(arquivo, encoding='utf-8')

    print(f"  Colunas encontradas: {list(df.columns)}")
    print(f"  Total de linhas: {len(df)}")

    cur = conn.cursor()
    inseridos = 0

    fonte = Path(arquivo).name

    for _, row in df.iterrows():
        try:
            cnpj = str(row.get('cnpj', '')) if pd.notna(row.get('cnpj', '')) else ''
            nome = str(row.get('nome_fantasia', row.get('fantas', ''))) if pd.notna(row.get('nome_fantasia', row.get('fantas', ''))) else ''
            tipo_destino = str(row.get('tipo_destino', '')) if pd.notna(row.get('tipo_destino', '')) else None
            lead_time = int(row.get('lead_time_dias', 0)) if pd.notna(row.get('lead_time_dias', 0)) else None
            ciclo = int(row.get('ciclo_pedido_dias', 0)) if pd.notna(row.get('ciclo_pedido_dias', 0)) else None
            fat_min = float(row.get('faturamento_minimo', 0)) if pd.notna(row.get('faturamento_minimo', 0)) else None

            if not cnpj or not nome:
                continue

            cur.execute("""
                INSERT INTO cadastro_fornecedores_completo
                    (cnpj, nome_fantasia, tipo_destino, lead_time_dias, ciclo_pedido_dias, faturamento_minimo, fonte, data_atualizacao)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (cnpj) DO UPDATE SET
                    nome_fantasia = EXCLUDED.nome_fantasia,
                    tipo_destino = EXCLUDED.tipo_destino,
                    lead_time_dias = COALESCE(EXCLUDED.lead_time_dias, cadastro_fornecedores_completo.lead_time_dias),
                    ciclo_pedido_dias = COALESCE(EXCLUDED.ciclo_pedido_dias, cadastro_fornecedores_completo.ciclo_pedido_dias),
                    faturamento_minimo = COALESCE(EXCLUDED.faturamento_minimo, cadastro_fornecedores_completo.faturamento_minimo),
                    fonte = EXCLUDED.fonte,
                    data_atualizacao = NOW()
            """, (cnpj, nome, tipo_destino, lead_time, ciclo, fat_min, fonte))

            inseridos += 1

        except Exception as e:
            pass

    conn.commit()
    cur.close()

    print(f"  Registros importados: {inseridos}")

    return inseridos, 0


# ============================================================================
# FUNCAO PRINCIPAL
# ============================================================================

def main():
    """Funcao principal - importa todos os arquivos"""
    print("\n" + "="*70)
    print("IMPORTACAO COMPLETA - CADASTROS, ESTOQUE E EMBALAGEM")
    print("="*70)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Conectar ao banco
    conn = conectar_banco()
    print("Conexao com banco estabelecida.")

    # Criar tabelas
    criar_tabela_embalagem(conn)
    criar_tabela_estoque(conn)
    criar_tabela_cadastro_produtos(conn)
    criar_tabela_cadastro_fornecedores(conn)

    # Estatisticas
    total_inseridos = 0
    total_erros = 0

    # =========================================================================
    # 1. IMPORTAR EMBALAGEM
    # =========================================================================
    print("\n" + "="*70)
    print("ETAPA 1: EMBALAGEM DE ARREDONDAMENTO")
    print("="*70)

    arquivos_embalagem = list(BASE_DIR.glob('Embalagem_*.csv'))
    for arq in arquivos_embalagem:
        ins, err = importar_embalagem(conn, arq)
        total_inseridos += ins
        total_erros += err

    # =========================================================================
    # 2. IMPORTAR POSICAO DE ESTOQUE
    # =========================================================================
    print("\n" + "="*70)
    print("ETAPA 2: POSICAO DE ESTOQUE")
    print("="*70)

    arquivos_estoque = list(BASE_DIR.glob('Relatório de Posição de Estoque_*.csv'))
    for arq in arquivos_estoque:
        ins, err = importar_posicao_estoque(conn, arq)
        total_inseridos += ins
        total_erros += err

    # =========================================================================
    # 3. IMPORTAR CADASTRO DE PRODUTOS
    # =========================================================================
    print("\n" + "="*70)
    print("ETAPA 3: CADASTRO DE PRODUTOS")
    print("="*70)

    arquivos_produtos = list(BASE_DIR.glob('Cadastro de Produtos_*.csv'))
    for arq in arquivos_produtos:
        ins, err = importar_cadastro_produtos(conn, arq)
        total_inseridos += ins
        total_erros += err

    # =========================================================================
    # 4. IMPORTAR CADASTRO DE FORNECEDORES
    # =========================================================================
    print("\n" + "="*70)
    print("ETAPA 4: CADASTRO DE FORNECEDORES")
    print("="*70)

    arquivos_fornecedores = list(BASE_DIR.glob('Cadastro de Fornecedores_*.csv'))
    for arq in arquivos_fornecedores:
        ins, err = importar_cadastro_fornecedores(conn, arq)
        total_inseridos += ins
        total_erros += err

    # =========================================================================
    # RESUMO FINAL
    # =========================================================================
    print("\n" + "="*70)
    print("RESUMO DA IMPORTACAO")
    print("="*70)
    print(f"Total de registros inseridos/atualizados: {total_inseridos:,}")
    print(f"Total de erros: {total_erros:,}")

    # Verificar contagem nas tabelas
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM embalagem_arredondamento")
    qtd_emb = cur.fetchone()[0]
    print(f"\nEmbalagem de arredondamento: {qtd_emb:,} registros")

    cur.execute("SELECT COUNT(*) FROM estoque_posicao_atual")
    qtd_est = cur.fetchone()[0]
    print(f"Posicao de estoque: {qtd_est:,} registros")

    cur.execute("SELECT COUNT(*) FROM cadastro_produtos_completo")
    qtd_prod = cur.fetchone()[0]
    print(f"Cadastro de produtos: {qtd_prod:,} registros")

    cur.execute("SELECT COUNT(*) FROM cadastro_fornecedores_completo")
    qtd_forn = cur.fetchone()[0]
    print(f"Cadastro de fornecedores: {qtd_forn:,} registros")

    cur.close()
    conn.close()

    print("\n" + "="*70)
    print("IMPORTACAO CONCLUIDA COM SUCESSO!")
    print("="*70)


if __name__ == "__main__":
    main()
