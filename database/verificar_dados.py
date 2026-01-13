# -*- coding: utf-8 -*-
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='demanda_reabastecimento',
    user='postgres',
    password='FerreiraCost@01',
    port=5432
)

cursor = conn.cursor()

print("="*60)
print("   VERIFICANDO DADOS NO BANCO")
print("="*60)
print()

# Lojas
cursor.execute("SELECT COUNT(*) FROM cadastro_lojas")
qtd_lojas = cursor.fetchone()[0]
print(f"1. Lojas: {qtd_lojas} registros")

cursor.execute("SELECT cod_empresa, nome_loja FROM cadastro_lojas ORDER BY cod_empresa")
for row in cursor.fetchall():
    print(f"   - {row[0]}: {row[1]}")

# Produtos
cursor.execute("SELECT COUNT(*) FROM cadastro_produtos")
qtd_produtos = cursor.fetchone()[0]
print(f"\n2. Produtos: {qtd_produtos} registros")

cursor.execute("SELECT codigo, descricao FROM cadastro_produtos ORDER BY codigo LIMIT 5")
print("   Primeiros 5 produtos:")
for row in cursor.fetchall():
    print(f"   - {row[0]}: {row[1]}")

# Vendas
cursor.execute("SELECT COUNT(*) FROM historico_vendas_diario")
qtd_vendas = cursor.fetchone()[0]
print(f"\n3. Histórico de Vendas: {qtd_vendas:,} registros")

cursor.execute("""
    SELECT MIN(data), MAX(data)
    FROM historico_vendas_diario
""")
periodo = cursor.fetchone()
print(f"   Período: {periodo[0]} até {periodo[1]}")

# Estoque
cursor.execute("SELECT COUNT(*) FROM estoque_atual")
qtd_estoque = cursor.fetchone()[0]
print(f"\n4. Estoque Atual: {qtd_estoque} registros")

# Eventos
cursor.execute("SELECT COUNT(*) FROM eventos_promocionais")
qtd_eventos = cursor.fetchone()[0]
print(f"\n5. Eventos Promocionais: {qtd_eventos} registros")

cursor.execute("SELECT nome_evento, data_inicio, data_fim FROM eventos_promocionais ORDER BY data_inicio LIMIT 5")
print("   Próximos eventos:")
for row in cursor.fetchall():
    print(f"   - {row[0]}: {row[1]} a {row[2]}")

print()
print("="*60)
print("   DADOS PRONTOS PARA USO!")
print("="*60)

cursor.close()
conn.close()
