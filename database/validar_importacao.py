# -*- coding: utf-8 -*-
"""
Script de Validacao da Importacao de Dados
==========================================
Verifica a integridade dos dados importados no PostgreSQL.

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import sys
import psycopg
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def conectar():
    return psycopg.connect('host=localhost dbname=previsao_demanda user=postgres password=FerreiraCost@01')


def validar():
    print("=" * 70)
    print("VALIDACAO DA IMPORTACAO DE DADOS")
    print("=" * 70)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    conn = conectar()
    cur = conn.cursor()

    erros = 0
    avisos = 0

    # 1. Verificar contagem de registros
    print("1. CONTAGEM DE REGISTROS")
    print("-" * 50)

    cur.execute("SELECT COUNT(*) FROM historico_vendas_diario")
    total_vendas = cur.fetchone()[0]
    print(f"   Vendas: {total_vendas:,}")

    if total_vendas == 0:
        print("   [ERRO] Nenhum registro de vendas encontrado!")
        erros += 1
    elif total_vendas < 1000000:
        print("   [AVISO] Menos de 1 milhao de registros (esperado ~10 milhoes)")
        avisos += 1
    else:
        print("   [OK] Volume adequado de registros")

    cur.execute("SELECT COUNT(*) FROM historico_estoque_diario")
    total_estoques = cur.fetchone()[0]
    print(f"   Estoques: {total_estoques:,}")

    print()

    # 2. Verificar periodo dos dados
    print("2. PERIODO DOS DADOS")
    print("-" * 50)

    cur.execute("SELECT MIN(data), MAX(data) FROM historico_vendas_diario")
    periodo = cur.fetchone()

    if periodo[0] and periodo[1]:
        print(f"   De: {periodo[0]}")
        print(f"   Ate: {periodo[1]}")

        # Verificar se cobre 2023-2025
        ano_min = periodo[0].year
        ano_max = periodo[1].year

        if ano_min <= 2023 and ano_max >= 2025:
            print("   [OK] Periodo cobre 2023-2025")
        else:
            print(f"   [AVISO] Periodo incompleto (esperado 2023-2025)")
            avisos += 1
    else:
        print("   [ERRO] Nao foi possivel determinar o periodo")
        erros += 1

    print()

    # 3. Verificar lojas
    print("3. LOJAS")
    print("-" * 50)

    cur.execute("""
        SELECT cod_empresa, COUNT(*) as registros
        FROM historico_vendas_diario
        GROUP BY cod_empresa
        ORDER BY cod_empresa
    """)
    lojas = cur.fetchall()

    print(f"   Total de lojas: {len(lojas)}")
    for loja in lojas:
        print(f"   Loja {loja[0]}: {loja[1]:,} registros")

    if len(lojas) < 5:
        print("   [AVISO] Menos de 5 lojas encontradas")
        avisos += 1
    else:
        print("   [OK] Quantidade de lojas adequada")

    print()

    # 4. Verificar produtos
    print("4. PRODUTOS")
    print("-" * 50)

    cur.execute("SELECT COUNT(DISTINCT codigo) FROM historico_vendas_diario")
    n_produtos = cur.fetchone()[0]
    print(f"   Total de produtos: {n_produtos:,}")

    cur.execute("""
        SELECT codigo, COUNT(*) as registros
        FROM historico_vendas_diario
        GROUP BY codigo
        ORDER BY registros DESC
        LIMIT 10
    """)
    top_produtos = cur.fetchall()

    print("   Top 10 produtos (por registros):")
    for prod in top_produtos:
        print(f"     Produto {prod[0]}: {prod[1]:,}")

    if n_produtos < 100:
        print("   [AVISO] Menos de 100 produtos")
        avisos += 1
    else:
        print("   [OK] Quantidade de produtos adequada")

    print()

    # 5. Verificar valores
    print("5. VALORES DE VENDA")
    print("-" * 50)

    cur.execute("""
        SELECT
            SUM(qtd_venda) as qtd_total,
            SUM(valor_venda) as valor_total,
            AVG(qtd_venda) as qtd_media,
            AVG(valor_venda) as valor_medio
        FROM historico_vendas_diario
    """)
    valores = cur.fetchone()

    print(f"   Quantidade total: {valores[0]:,.0f}")
    print(f"   Valor total: R$ {valores[1]:,.2f}")
    print(f"   Quantidade media/registro: {valores[2]:.2f}")
    print(f"   Valor medio/registro: R$ {valores[3]:.2f}")

    if valores[1] and valores[1] > 0:
        print("   [OK] Valores parecem corretos")
    else:
        print("   [ERRO] Valores zerados ou negativos")
        erros += 1

    print()

    # 6. Verificar distribuicao por ano
    print("6. DISTRIBUICAO POR ANO")
    print("-" * 50)

    cur.execute("""
        SELECT
            ano,
            COUNT(*) as registros,
            COUNT(DISTINCT EXTRACT(MONTH FROM data)) as meses,
            SUM(qtd_venda) as qtd_total
        FROM historico_vendas_diario
        GROUP BY ano
        ORDER BY ano
    """)

    print(f"   {'Ano':<6} {'Registros':>12} {'Meses':>8} {'Qtd Total':>15}")
    print("   " + "-" * 45)

    for row in cur.fetchall():
        print(f"   {row[0]:<6} {row[1]:>12,} {row[2]:>8} {row[3]:>15,.0f}")

        if row[2] < 12:
            print(f"   [AVISO] Ano {row[0]} com menos de 12 meses")
            avisos += 1

    print()

    # 7. Verificar integridade referencial
    print("7. INTEGRIDADE REFERENCIAL")
    print("-" * 50)

    # Vendas sem loja cadastrada
    cur.execute("""
        SELECT COUNT(DISTINCT v.cod_empresa)
        FROM historico_vendas_diario v
        LEFT JOIN cadastro_lojas l ON v.cod_empresa = l.cod_empresa
        WHERE l.cod_empresa IS NULL
    """)
    lojas_sem_cadastro = cur.fetchone()[0]

    if lojas_sem_cadastro > 0:
        print(f"   [ERRO] {lojas_sem_cadastro} lojas sem cadastro!")
        erros += 1
    else:
        print("   [OK] Todas as lojas estao cadastradas")

    # Vendas sem produto cadastrado
    cur.execute("""
        SELECT COUNT(DISTINCT v.codigo)
        FROM historico_vendas_diario v
        LEFT JOIN cadastro_produtos p ON v.codigo = p.codigo
        WHERE p.codigo IS NULL
    """)
    produtos_sem_cadastro = cur.fetchone()[0]

    if produtos_sem_cadastro > 0:
        print(f"   [ERRO] {produtos_sem_cadastro} produtos sem cadastro!")
        erros += 1
    else:
        print("   [OK] Todos os produtos estao cadastrados")

    print()

    # 8. Verificar dados duplicados
    print("8. VERIFICACAO DE DUPLICADOS")
    print("-" * 50)

    cur.execute("""
        SELECT data, cod_empresa, codigo, COUNT(*) as duplicados
        FROM historico_vendas_diario
        GROUP BY data, cod_empresa, codigo
        HAVING COUNT(*) > 1
        LIMIT 5
    """)
    duplicados = cur.fetchall()

    if duplicados:
        print(f"   [AVISO] Encontrados registros duplicados:")
        for dup in duplicados:
            print(f"     {dup[0]} | Loja {dup[1]} | Produto {dup[2]}: {dup[3]}x")
        avisos += 1
    else:
        print("   [OK] Nenhum duplicado encontrado")

    print()

    # Resumo final
    print("=" * 70)
    print("RESUMO DA VALIDACAO")
    print("=" * 70)

    if erros == 0 and avisos == 0:
        print("RESULTADO: SUCESSO - Todos os testes passaram!")
    elif erros == 0:
        print(f"RESULTADO: SUCESSO COM AVISOS - {avisos} aviso(s)")
    else:
        print(f"RESULTADO: FALHA - {erros} erro(s), {avisos} aviso(s)")

    print()
    print(f"Erros: {erros}")
    print(f"Avisos: {avisos}")

    conn.close()

    return erros == 0


if __name__ == '__main__':
    sucesso = validar()
    sys.exit(0 if sucesso else 1)
