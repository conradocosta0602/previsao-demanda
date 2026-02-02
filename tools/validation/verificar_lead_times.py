# -*- coding: utf-8 -*-
import psycopg2
import os

conn = psycopg2.connect(
    host='localhost',
    database='forecast_db',
    user='postgres',
    password='FerreiraCost@01',
    port=5432
)
conn.set_client_encoding('LATIN1')
cursor = conn.cursor()

# Verificar lead times dos fornecedores PIAL e FORCELINE
print('=== Lead Times Reais dos Fornecedores PIAL e FORCELINE ===')
print()

fornecedores = ['FORCELINE', 'DANEVA', 'HDL', 'BTICINO', 'CEMAR']
for forn in fornecedores:
    cursor.execute('''
        SELECT pf.cod_empresa, pf.lead_time_dias, cf.fantas
        FROM parametros_fornecedor pf
        JOIN cadastro_fornecedores cf ON pf.cnpj_fornecedor = cf.cnpj
        WHERE cf.fantas = %s
        ORDER BY pf.cod_empresa
    ''', (forn,))

    rows = cursor.fetchall()
    if rows:
        print(f'{forn}:')
        for row in rows:
            tipo = 'CD' if row[0] >= 80 else 'Loja'
            print(f'  Empresa {row[0]} ({tipo}): {row[1]} dias')
        print()

# Verificar total de registros
cursor.execute('SELECT COUNT(*) FROM parametros_fornecedor')
total = cursor.fetchone()[0]
print(f'Total de registros em parametros_fornecedor: {total}')

conn.close()
