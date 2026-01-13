# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
import pandas as pd

conn = psycopg2.connect(
    host='localhost',
    database='demanda_reabastecimento',
    user='postgres',
    password='FerreiraCost@01',
    port=5432
)

output_dir = r'c:\Users\valter.lino\Desktop\Treinamentos\VS\previsao-demanda\data_export'
import os
os.makedirs(output_dir, exist_ok=True)

print("Exportando amostras dos dados do banco...")
print()

# Lojas
df = pd.read_sql("SELECT * FROM cadastro_lojas ORDER BY cod_empresa", conn)
arquivo = os.path.join(output_dir, 'lojas.xlsx')
df.to_excel(arquivo, index=False)
print(f"✅ {len(df)} lojas → {arquivo}")

# Produtos
df = pd.read_sql("SELECT * FROM cadastro_produtos ORDER BY codigo", conn)
arquivo = os.path.join(output_dir, 'produtos.xlsx')
df.to_excel(arquivo, index=False)
print(f"✅ {len(df)} produtos → {arquivo}")

# Vendas (amostra)
df = pd.read_sql("""
    SELECT data, cod_empresa, codigo, qtd_venda, valor_venda
    FROM historico_vendas_diario
    ORDER BY data DESC
    LIMIT 1000
""", conn)
arquivo = os.path.join(output_dir, 'vendas_amostra_1000.xlsx')
df.to_excel(arquivo, index=False)
print(f"✅ 1000 vendas (amostra) → {arquivo}")

# Estoque
df = pd.read_sql("SELECT * FROM estoque_atual ORDER BY cod_empresa, codigo", conn)
arquivo = os.path.join(output_dir, 'estoque_atual.xlsx')
df.to_excel(arquivo, index=False)
print(f"✅ {len(df)} registros de estoque → {arquivo}")

# Eventos
df = pd.read_sql("SELECT * FROM eventos_promocionais ORDER BY data_inicio", conn)
arquivo = os.path.join(output_dir, 'eventos.xlsx')
df.to_excel(arquivo, index=False)
print(f"✅ {len(df)} eventos → {arquivo}")

conn.close()

print()
print("="*60)
print(f"Arquivos exportados para: {output_dir}")
print("="*60)
