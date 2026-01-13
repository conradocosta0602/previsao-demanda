# -*- coding: utf-8 -*-
"""
Script de Atualizacao Incremental de Dados
==========================================
Adiciona novos arquivos de demanda ao banco PostgreSQL
sem reprocessar os dados ja importados.

Uso: python atualizar_dados_incrementais.py [arquivo_especifico]

Se nenhum arquivo for especificado, processa todos os arquivos
que ainda nao foram importados.

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

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuracoes
DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01'
}

DADOS_PATH = Path(__file__).parent.parent / 'dados_reais' / 'Demanda'
BATCH_SIZE = 10000


def conectar():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding('UTF8')
    return conn


def obter_meses_importados(conn):
    """Retorna set de meses ja importados (formato: 'MM-AAAA')"""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT TO_CHAR(data, 'MM-YYYY') as mes
        FROM historico_vendas_diario
    """)
    meses = set(row[0] for row in cur.fetchall())
    cur.close()
    return meses


def extrair_mes_arquivo(nome_arquivo):
    """Extrai mes do nome do arquivo (demanda_DD-MM-AAAA -> MM-AAAA)"""
    partes = nome_arquivo.replace('demanda_', '').split('-')
    if len(partes) == 3:
        return f"{partes[1]}-{partes[2]}"
    return None


def importar_arquivo(conn, filepath, nome_arquivo):
    """Importa um arquivo para o banco"""
    cur = conn.cursor()

    df = pd.read_csv(filepath)
    df['data'] = pd.to_datetime(df['data']).dt.date
    df['valor_venda'] = df['qtd_venda'] * df['prc_venda']

    df['data_dt'] = pd.to_datetime(df['data'])
    df['dia_semana'] = df['data_dt'].dt.dayofweek + 1
    df['dia_mes'] = df['data_dt'].dt.day
    df['semana_ano'] = df['data_dt'].dt.isocalendar().week
    df['mes'] = df['data_dt'].dt.month
    df['ano'] = df['data_dt'].dt.year
    df['fim_semana'] = df['dia_semana'].isin([6, 7])

    # Criar produtos faltantes
    cur.execute("SELECT codigo FROM cadastro_produtos")
    produtos_existentes = set(row[0] for row in cur.fetchall())
    novos_produtos = set(df['codigo'].unique()) - produtos_existentes

    if novos_produtos:
        print(f"    Criando {len(novos_produtos)} novos produtos...")
        values = [(cod, f'Produto {cod}', True) for cod in novos_produtos]
        execute_values(cur, """
            INSERT INTO cadastro_produtos (codigo, descricao, ativo)
            VALUES %s ON CONFLICT DO NOTHING
        """, values)
        conn.commit()

    # Inserir vendas
    vendas_cols = ['data', 'cod_empresa', 'codigo', 'qtd_venda', 'valor_venda',
                   'dia_semana', 'dia_mes', 'semana_ano', 'mes', 'ano', 'fim_semana']
    vendas_data = df[vendas_cols].values.tolist()

    vendas_inseridas = 0
    for i in range(0, len(vendas_data), BATCH_SIZE):
        batch = vendas_data[i:i+BATCH_SIZE]
        execute_values(cur, """
            INSERT INTO historico_vendas_diario
            (data, cod_empresa, codigo, qtd_venda, valor_venda,
             dia_semana, dia_mes, semana_ano, mes, ano, fim_semana)
            VALUES %s ON CONFLICT DO NOTHING
        """, batch)
        vendas_inseridas += len(batch)

    conn.commit()

    # Inserir estoques
    estoques_inseridos = 0
    if 'estoque_diario' in df.columns:
        estoque_data = df[['data', 'cod_empresa', 'codigo', 'estoque_diario']].dropna().values.tolist()

        for i in range(0, len(estoque_data), BATCH_SIZE):
            batch = estoque_data[i:i+BATCH_SIZE]
            execute_values(cur, """
                INSERT INTO historico_estoque_diario
                (data, cod_empresa, codigo, estoque_diario)
                VALUES %s ON CONFLICT DO NOTHING
            """, batch)
            estoques_inseridos += len(batch)

        conn.commit()

    cur.close()
    return vendas_inseridas, estoques_inseridos


def main():
    print("=" * 60)
    print("ATUALIZACAO INCREMENTAL DE DADOS")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = conectar()

    # Obter meses ja importados
    meses_importados = obter_meses_importados(conn)
    print(f"Meses ja importados: {len(meses_importados)}")

    # Listar arquivos disponiveis
    arquivos_disponiveis = [f for f in os.listdir(DADOS_PATH)
                           if f.startswith('demanda_') and not f.endswith('.csv')]

    # Verificar arquivo especifico ou processar todos novos
    if len(sys.argv) > 1:
        arquivo_especifico = sys.argv[1]
        if arquivo_especifico in arquivos_disponiveis:
            arquivos_processar = [arquivo_especifico]
        else:
            print(f"ERRO: Arquivo {arquivo_especifico} nao encontrado!")
            sys.exit(1)
    else:
        # Encontrar arquivos nao importados
        arquivos_processar = []
        for arquivo in arquivos_disponiveis:
            mes = extrair_mes_arquivo(arquivo)
            if mes and mes not in meses_importados:
                arquivos_processar.append(arquivo)

    if not arquivos_processar:
        print("Nenhum arquivo novo para importar!")
        conn.close()
        return

    print(f"Arquivos a processar: {len(arquivos_processar)}")
    print()

    # Processar arquivos
    total_vendas = 0
    total_estoques = 0

    for i, arquivo in enumerate(sorted(arquivos_processar), 1):
        filepath = DADOS_PATH / arquivo
        print(f"[{i}/{len(arquivos_processar)}] {arquivo}...", end=" ")

        vendas, estoques = importar_arquivo(conn, filepath, arquivo)
        total_vendas += vendas
        total_estoques += estoques

        print(f"OK ({vendas:,} vendas, {estoques:,} estoques)")

    print()
    print("-" * 60)
    print(f"TOTAL IMPORTADO: {total_vendas:,} vendas, {total_estoques:,} estoques")

    conn.close()

    print()
    print("Atualizacao concluida!")


if __name__ == '__main__':
    main()
