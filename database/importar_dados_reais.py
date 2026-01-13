# -*- coding: utf-8 -*-
"""
Script de Importacao de Dados Reais para PostgreSQL
===================================================
Importa dados de demanda da pasta dados_reais/Demanda para o banco PostgreSQL.

Estrutura esperada dos arquivos:
- demanda_DD-MM-AAAA (arquivos mensais com estoque_diario)

Tabelas destino:
- historico_vendas_diario
- historico_estoque_diario
- cadastro_produtos (criar registros faltantes)
- cadastro_lojas (criar registros faltantes)

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

# Conexao com o banco
DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01'
}

# Caminho dos dados
DADOS_PATH = Path(__file__).parent.parent / 'dados_reais' / 'Demanda'

# Batch size para insercao
BATCH_SIZE = 10000

# ============================================================================
# FUNCOES DE IMPORTACAO
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


def listar_arquivos_mensais(path):
    """Lista todos os arquivos mensais de demanda"""
    arquivos = []
    for f in os.listdir(path):
        if f.startswith('demanda_') and not f.endswith('.csv'):
            arquivos.append(f)

    # Ordenar por data
    arquivos.sort(key=lambda x: datetime.strptime(x.replace('demanda_', ''), '%d-%m-%Y'))
    return arquivos


def criar_lojas_faltantes(conn, cod_empresas):
    """Cria registros de lojas que nao existem"""
    cur = conn.cursor()

    # Verificar lojas existentes
    cur.execute("SELECT cod_empresa FROM cadastro_lojas")
    existentes = set(row[0] for row in cur.fetchall())

    # Criar lojas faltantes
    faltantes = set(cod_empresas) - existentes
    if faltantes:
        print(f"  Criando {len(faltantes)} lojas faltantes...")
        for cod in faltantes:
            cur.execute("""
                INSERT INTO cadastro_lojas (cod_empresa, nome_loja, tipo, ativo)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (cod_empresa) DO NOTHING
            """, (cod, f'Loja {cod}', 'Loja', True))
        conn.commit()

    cur.close()
    return len(faltantes)


def criar_produtos_faltantes(conn, codigos):
    """Cria registros de produtos que nao existem"""
    cur = conn.cursor()

    # Verificar produtos existentes
    cur.execute("SELECT codigo FROM cadastro_produtos")
    existentes = set(row[0] for row in cur.fetchall())

    # Criar produtos faltantes
    faltantes = set(codigos) - existentes
    if faltantes:
        print(f"  Criando {len(faltantes)} produtos faltantes...")

        # Inserir em batches
        faltantes_list = list(faltantes)
        for i in range(0, len(faltantes_list), BATCH_SIZE):
            batch = faltantes_list[i:i+BATCH_SIZE]
            values = [(cod, f'Produto {cod}', True) for cod in batch]
            execute_values(cur, """
                INSERT INTO cadastro_produtos (codigo, descricao, ativo)
                VALUES %s
                ON CONFLICT (codigo) DO NOTHING
            """, values)
        conn.commit()

    cur.close()
    return len(faltantes)


def importar_arquivo_mensal(conn, filepath, nome_arquivo):
    """Importa um arquivo mensal para o banco"""
    cur = conn.cursor()

    # Ler arquivo
    df = pd.read_csv(filepath)

    # Verificar colunas
    colunas_esperadas = ['data', 'cod_empresa', 'codigo', 'qtd_venda', 'prc_venda']
    for col in colunas_esperadas:
        if col not in df.columns:
            print(f"  ERRO: Coluna {col} nao encontrada no arquivo {nome_arquivo}")
            return 0, 0

    # Converter data
    df['data'] = pd.to_datetime(df['data']).dt.date

    # Calcular valor_venda
    df['valor_venda'] = df['qtd_venda'] * df['prc_venda']

    # Extrair componentes da data
    df['data_dt'] = pd.to_datetime(df['data'])
    df['dia_semana'] = df['data_dt'].dt.dayofweek + 1  # 1=Segunda, 7=Domingo
    df['dia_mes'] = df['data_dt'].dt.day
    df['semana_ano'] = df['data_dt'].dt.isocalendar().week
    df['mes'] = df['data_dt'].dt.month
    df['ano'] = df['data_dt'].dt.year
    df['fim_semana'] = df['dia_semana'].isin([6, 7])

    # Preparar dados para historico_vendas_diario
    vendas_cols = ['data', 'cod_empresa', 'codigo', 'qtd_venda', 'valor_venda',
                   'dia_semana', 'dia_mes', 'semana_ano', 'mes', 'ano', 'fim_semana']
    vendas_data = df[vendas_cols].values.tolist()

    # Inserir vendas em batches
    vendas_inseridas = 0
    for i in range(0, len(vendas_data), BATCH_SIZE):
        batch = vendas_data[i:i+BATCH_SIZE]
        try:
            execute_values(cur, """
                INSERT INTO historico_vendas_diario
                (data, cod_empresa, codigo, qtd_venda, valor_venda,
                 dia_semana, dia_mes, semana_ano, mes, ano, fim_semana)
                VALUES %s
                ON CONFLICT DO NOTHING
            """, batch)
            vendas_inseridas += len(batch)
        except Exception as e:
            print(f"  ERRO ao inserir vendas: {e}")
            conn.rollback()
            continue

    conn.commit()

    # Importar estoque se disponivel
    estoques_inseridos = 0
    if 'estoque_diario' in df.columns:
        estoque_cols = ['data', 'cod_empresa', 'codigo', 'estoque_diario']
        estoque_data = df[estoque_cols].dropna(subset=['estoque_diario']).values.tolist()

        for i in range(0, len(estoque_data), BATCH_SIZE):
            batch = estoque_data[i:i+BATCH_SIZE]
            try:
                execute_values(cur, """
                    INSERT INTO historico_estoque_diario
                    (data, cod_empresa, codigo, estoque_diario)
                    VALUES %s
                    ON CONFLICT DO NOTHING
                """, batch)
                estoques_inseridos += len(batch)
            except Exception as e:
                print(f"  ERRO ao inserir estoques: {e}")
                conn.rollback()
                continue

        conn.commit()

    cur.close()
    return vendas_inseridas, estoques_inseridos


def limpar_dados_existentes(conn, confirmar=True):
    """Remove dados existentes das tabelas de historico"""
    if confirmar:
        resposta = input("Deseja limpar dados existentes? (s/N): ")
        if resposta.lower() != 's':
            print("Mantendo dados existentes...")
            return False

    cur = conn.cursor()

    print("Limpando dados existentes...")
    cur.execute("TRUNCATE TABLE historico_vendas_diario CASCADE")
    cur.execute("TRUNCATE TABLE historico_estoque_diario CASCADE")
    conn.commit()

    cur.close()
    print("Dados limpos com sucesso!")
    return True


def verificar_importacao(conn):
    """Verifica estatisticas apos importacao"""
    cur = conn.cursor()

    print("\n" + "=" * 60)
    print("VERIFICACAO DA IMPORTACAO")
    print("=" * 60)

    # Contagem de vendas
    cur.execute("SELECT COUNT(*) FROM historico_vendas_diario")
    total_vendas = cur.fetchone()[0]
    print(f"Total de registros de vendas: {total_vendas:,}")

    # Contagem de estoques
    cur.execute("SELECT COUNT(*) FROM historico_estoque_diario")
    total_estoques = cur.fetchone()[0]
    print(f"Total de registros de estoque: {total_estoques:,}")

    # Periodo dos dados
    cur.execute("SELECT MIN(data), MAX(data) FROM historico_vendas_diario")
    periodo = cur.fetchone()
    print(f"Periodo: {periodo[0]} ate {periodo[1]}")

    # Lojas
    cur.execute("SELECT COUNT(DISTINCT cod_empresa) FROM historico_vendas_diario")
    n_lojas = cur.fetchone()[0]
    print(f"Lojas: {n_lojas}")

    # Produtos
    cur.execute("SELECT COUNT(DISTINCT codigo) FROM historico_vendas_diario")
    n_produtos = cur.fetchone()[0]
    print(f"Produtos: {n_produtos:,}")

    # Vendas por ano
    cur.execute("""
        SELECT ano, COUNT(*), SUM(qtd_venda), SUM(valor_venda)
        FROM historico_vendas_diario
        GROUP BY ano
        ORDER BY ano
    """)
    print("\nVendas por ano:")
    print(f"{'Ano':<6} {'Registros':>12} {'Qtd Total':>15} {'Valor Total':>18}")
    print("-" * 55)
    for row in cur.fetchall():
        print(f"{row[0]:<6} {row[1]:>12,} {row[2]:>15,.0f} {row[3]:>18,.2f}")

    cur.close()


def main():
    """Funcao principal de importacao"""
    print("=" * 60)
    print("IMPORTACAO DE DADOS REAIS PARA PostgreSQL")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Pasta de dados: {DADOS_PATH}")
    print()

    # Verificar se pasta existe
    if not DADOS_PATH.exists():
        print(f"ERRO: Pasta nao encontrada: {DADOS_PATH}")
        sys.exit(1)

    # Listar arquivos
    arquivos = listar_arquivos_mensais(DADOS_PATH)
    print(f"Arquivos encontrados: {len(arquivos)}")

    if not arquivos:
        print("ERRO: Nenhum arquivo de demanda encontrado!")
        sys.exit(1)

    # Conectar ao banco
    print("\nConectando ao banco de dados...")
    conn = conectar_banco()
    print("Conectado com sucesso!")

    # Perguntar se deve limpar dados existentes
    limpar_dados_existentes(conn, confirmar=True)

    # Coletar todos os codigos unicos primeiro
    print("\nAnalisando arquivos para identificar lojas e produtos...")
    todos_cod_empresa = set()
    todos_codigo = set()

    for arquivo in arquivos:
        filepath = DADOS_PATH / arquivo
        df = pd.read_csv(filepath, usecols=['cod_empresa', 'codigo'])
        todos_cod_empresa.update(df['cod_empresa'].unique())
        todos_codigo.update(df['codigo'].unique())

    print(f"  Lojas encontradas: {len(todos_cod_empresa)}")
    print(f"  Produtos encontrados: {len(todos_codigo):,}")

    # Criar registros faltantes
    print("\nCriando registros de cadastro...")
    lojas_criadas = criar_lojas_faltantes(conn, todos_cod_empresa)
    produtos_criados = criar_produtos_faltantes(conn, todos_codigo)
    print(f"  Lojas criadas: {lojas_criadas}")
    print(f"  Produtos criados: {produtos_criados:,}")

    # Importar arquivos
    print("\nImportando arquivos de demanda...")
    print("-" * 60)

    total_vendas = 0
    total_estoques = 0

    for i, arquivo in enumerate(arquivos, 1):
        filepath = DADOS_PATH / arquivo
        print(f"[{i:02d}/{len(arquivos)}] {arquivo}...", end=" ")

        vendas, estoques = importar_arquivo_mensal(conn, filepath, arquivo)
        total_vendas += vendas
        total_estoques += estoques

        print(f"OK (vendas: {vendas:,}, estoques: {estoques:,})")

    print("-" * 60)
    print(f"TOTAL: {total_vendas:,} vendas, {total_estoques:,} estoques")

    # Verificar importacao
    verificar_importacao(conn)

    # Fechar conexao
    conn.close()

    print("\n" + "=" * 60)
    print("IMPORTACAO CONCLUIDA COM SUCESSO!")
    print("=" * 60)


if __name__ == '__main__':
    main()
