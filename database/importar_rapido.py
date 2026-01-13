# -*- coding: utf-8 -*-
"""
Script de Importacao Rapida usando COPY
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import pandas as pd
import psycopg
from io import StringIO
from datetime import datetime
from pathlib import Path

print('=' * 60)
print('IMPORTACAO RAPIDA DE DADOS REAIS')
print('=' * 60)
print(f'Data/Hora: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# Configuracoes
DADOS_PATH = Path(__file__).parent.parent / 'dados_reais' / 'Demanda'

# Conectar
print('Conectando ao banco...')
conn = psycopg.connect('host=localhost dbname=previsao_demanda user=postgres password=FerreiraCost@01')
cur = conn.cursor()
print('Conectado!')

# Verificar o que ja foi importado
cur.execute('SELECT MAX(data) FROM historico_vendas_diario')
ultima_data = cur.fetchone()[0]
print(f'Ultima data importada: {ultima_data}')

# Listar arquivos
arquivos = [f for f in os.listdir(DADOS_PATH) if f.startswith('demanda_') and not f.endswith('.csv')]
arquivos.sort(key=lambda x: datetime.strptime(x.replace('demanda_', ''), '%d-%m-%Y'))
print(f'Arquivos totais: {len(arquivos)}')

# Filtrar arquivos nao importados
if ultima_data:
    # Importar a partir do proximo mes
    arquivos_filtrados = []
    for arq in arquivos:
        data_arq = datetime.strptime(arq.replace('demanda_', ''), '%d-%m-%Y').date()
        # Se o arquivo e de um mes posterior ao ultimo importado
        if data_arq.year > ultima_data.year or (data_arq.year == ultima_data.year and data_arq.month > ultima_data.month):
            arquivos_filtrados.append(arq)
    arquivos = arquivos_filtrados

print(f'Arquivos a importar: {len(arquivos)}')

if not arquivos:
    print('Nenhum arquivo novo para importar!')
    conn.close()
    sys.exit(0)

print()

# Importar arquivos
print('Importando vendas (metodo COPY)...')
print('-' * 60)

total_vendas = 0
total_estoques = 0

for i, arquivo in enumerate(arquivos, 1):
    filepath = DADOS_PATH / arquivo
    print(f'[{i:02d}/{len(arquivos)}] {arquivo}...', end=' ', flush=True)

    try:
        # Ler arquivo
        df = pd.read_csv(filepath, low_memory=False)

        # Processar
        df['data'] = pd.to_datetime(df['data']).dt.date
        df['valor_venda'] = df['qtd_venda'] * df['prc_venda']
        df['data_dt'] = pd.to_datetime(df['data'])
        df['dia_semana'] = df['data_dt'].dt.dayofweek + 1
        df['dia_mes'] = df['data_dt'].dt.day
        df['semana_ano'] = df['data_dt'].dt.isocalendar().week.astype(int)
        df['mes'] = df['data_dt'].dt.month
        df['ano'] = df['data_dt'].dt.year
        df['fim_semana'] = df['dia_semana'].isin([6, 7])

        # Preparar dados de vendas
        vendas_cols = ['data', 'cod_empresa', 'codigo', 'qtd_venda', 'valor_venda',
                       'dia_semana', 'dia_mes', 'semana_ano', 'mes', 'ano', 'fim_semana']
        df_vendas = df[vendas_cols].copy()

        # Criar buffer CSV
        buffer = StringIO()
        df_vendas.to_csv(buffer, index=False, header=False)
        buffer.seek(0)

        # Usar COPY para insercao rapida
        with cur.copy("""
            COPY historico_vendas_diario
            (data, cod_empresa, codigo, qtd_venda, valor_venda,
             dia_semana, dia_mes, semana_ano, mes, ano, fim_semana)
            FROM STDIN WITH (FORMAT CSV)
        """) as copy:
            while data := buffer.read(8192):
                copy.write(data)

        conn.commit()
        vendas_inseridas = len(df_vendas)
        total_vendas += vendas_inseridas

        # Estoques
        estoques_inseridos = 0
        if 'estoque_diario' in df.columns:
            df_estoque = df[['data', 'cod_empresa', 'codigo', 'estoque_diario']].dropna()

            buffer2 = StringIO()
            df_estoque.to_csv(buffer2, index=False, header=False)
            buffer2.seek(0)

            with cur.copy("""
                COPY historico_estoque_diario
                (data, cod_empresa, codigo, estoque_diario)
                FROM STDIN WITH (FORMAT CSV)
            """) as copy:
                while data := buffer2.read(8192):
                    copy.write(data)

            conn.commit()
            estoques_inseridos = len(df_estoque)
            total_estoques += estoques_inseridos

        print(f'OK ({vendas_inseridas:,} vendas, {estoques_inseridos:,} estoques)')

    except Exception as e:
        print(f'ERRO: {e}')
        conn.rollback()

print('-' * 60)
print(f'TOTAL IMPORTADO: {total_vendas:,} vendas, {total_estoques:,} estoques')

# Verificar
print()
print('Verificando importacao...')
cur.execute('SELECT COUNT(*) FROM historico_vendas_diario')
print(f'  Total vendas no banco: {cur.fetchone()[0]:,}')

cur.execute('SELECT MIN(data), MAX(data) FROM historico_vendas_diario')
periodo = cur.fetchone()
print(f'  Periodo: {periodo[0]} ate {periodo[1]}')

cur.execute('SELECT COUNT(DISTINCT cod_empresa) FROM historico_vendas_diario')
print(f'  Lojas: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(DISTINCT codigo) FROM historico_vendas_diario')
print(f'  Produtos: {cur.fetchone()[0]:,}')

cur.execute('SELECT ano, COUNT(*) FROM historico_vendas_diario GROUP BY ano ORDER BY ano')
print('  Por ano:')
for row in cur.fetchall():
    print(f'    {row[0]}: {row[1]:,}')

conn.close()

print()
print('=' * 60)
print('IMPORTACAO CONCLUIDA!')
print('=' * 60)
