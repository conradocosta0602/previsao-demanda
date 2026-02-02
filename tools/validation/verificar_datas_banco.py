# -*- coding: utf-8 -*-
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Configurar encoding
os.environ['PGCLIENTENCODING'] = 'UTF8'

def main():
    # Conexao
    conn = psycopg2.connect(
        host='localhost',
        database='previsao_demanda',
        user='postgres',
        password='1234'
    )
    conn.set_client_encoding('UTF8')
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print('='*60)
    print('VALIDACAO DE DADOS DO BANCO')
    print('='*60)
    print()

    # 1. Estoque
    print('1. ESTOQUE (tabela estoque_posicao_atual)')
    print('-'*60)

    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'estoque_posicao_atual'
        ORDER BY ordinal_position
    """)
    colunas = [r['column_name'] for r in cursor.fetchall()]
    print(f'   Colunas: {colunas}')

    cursor.execute('SELECT COUNT(*) as total FROM estoque_posicao_atual')
    print(f"   Total de registros: {cursor.fetchone()['total']:,}")

    # Tentar encontrar coluna de data
    for col in ['data_atualizacao', 'data_posicao', 'data_carga', 'created_at', 'updated_at']:
        if col in colunas:
            cursor.execute(f'SELECT MAX({col}) as ultima FROM estoque_posicao_atual')
            result = cursor.fetchone()
            print(f'   Ultima data ({col}): {result["ultima"]}')
            break

    print()

    # 2. Situacao de itens
    print('2. SITUACAO DE ITENS (tabela sit_compra)')
    print('-'*60)

    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'sit_compra'
        )
    """)

    if cursor.fetchone()['exists']:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'sit_compra'
            ORDER BY ordinal_position
        """)
        colunas_sit = [r['column_name'] for r in cursor.fetchall()]
        print(f'   Colunas: {colunas_sit}')

        cursor.execute('SELECT COUNT(*) as total FROM sit_compra')
        print(f"   Total de registros: {cursor.fetchone()['total']:,}")

        for col in ['data_atualizacao', 'data_carga', 'created_at', 'updated_at']:
            if col in colunas_sit:
                cursor.execute(f'SELECT MAX({col}) as ultima FROM sit_compra')
                result = cursor.fetchone()
                print(f'   Ultima data ({col}): {result["ultima"]}')
                break

        # Distribuicao por situacao
        cursor.execute("""
            SELECT sit_compra, COUNT(*) as qtd
            FROM sit_compra
            GROUP BY sit_compra
            ORDER BY qtd DESC
        """)
        print('   Distribuicao por situacao:')
        for r in cursor.fetchall():
            print(f"     {r['sit_compra']}: {r['qtd']:,} itens")
    else:
        print('   Tabela NAO EXISTE')

    print()

    # 3. Historico de vendas
    print('3. HISTORICO DE VENDAS (tabela historico_vendas_diario)')
    print('-'*60)

    cursor.execute("""
        SELECT
            MIN(data) as primeira,
            MAX(data) as ultima,
            COUNT(*) as total
        FROM historico_vendas_diario
    """)
    result = cursor.fetchone()
    print(f'   Primeira data: {result["primeira"]}')
    print(f'   Ultima data: {result["ultima"]}')
    print(f'   Total de registros: {result["total"]:,}')

    # Ultimos 5 dias com dados
    cursor.execute("""
        SELECT data, SUM(qtd_venda) as total_vendas, COUNT(DISTINCT codigo) as itens
        FROM historico_vendas_diario
        GROUP BY data
        ORDER BY data DESC
        LIMIT 5
    """)
    print('   Ultimos 5 dias com dados:')
    for r in cursor.fetchall():
        print(f"     {r['data']}: {r['total_vendas']:,.0f} unidades ({r['itens']} itens)")

    print()

    # 4. Cadastro de produtos
    print('4. CADASTRO DE PRODUTOS (tabela produtos)')
    print('-'*60)

    cursor.execute('SELECT COUNT(*) as total FROM produtos')
    print(f"   Total de produtos: {cursor.fetchone()['total']:,}")

    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'produtos'
        ORDER BY ordinal_position
    """)
    colunas_prod = [r['column_name'] for r in cursor.fetchall()]

    for col in ['data_atualizacao', 'updated_at', 'created_at']:
        if col in colunas_prod:
            cursor.execute(f'SELECT MAX({col}) as ultima FROM produtos')
            result = cursor.fetchone()
            print(f'   Ultima atualizacao ({col}): {result["ultima"]}')
            break

    conn.close()

if __name__ == '__main__':
    main()
