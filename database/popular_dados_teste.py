# -*- coding: utf-8 -*-
"""
Script para Popular Banco com Dados de Teste
Cria dados mockados realistas para testar a ferramenta
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
import random
from datetime import datetime, timedelta

# Conexão
DB_CONFIG = {
    'host': 'localhost',
    'database': 'demanda_reabastecimento',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

def conectar():
    return psycopg2.connect(**DB_CONFIG)

def popular_cadastro_lojas(conn):
    """Cria 5 lojas"""
    print("\n1. Criando lojas...")
    cursor = conn.cursor()

    lojas = [
        (1, 'Loja Centro SP', 'Sudeste', 'Loja', 5000.00),
        (2, 'Loja Norte Shopping', 'Sudeste', 'Loja', 3500.00),
        (3, 'Loja Sul Express', 'Sul', 'Loja', 2000.00),
        (4, 'Loja Litoral', 'Sudeste', 'Loja', 3000.00),
        (5, 'CD Central', 'Sudeste', 'CD', 15000.00),
    ]

    for loja in lojas:
        cursor.execute("""
            INSERT INTO cadastro_lojas (cod_empresa, nome_loja, regiao, tipo, capacidade_estoque)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, loja)

    conn.commit()
    print(f"   OK - {len(lojas)} lojas criadas")
    cursor.close()

def popular_cadastro_produtos(conn):
    """Cria 50 produtos"""
    print("\n2. Criando produtos...")
    cursor = conn.cursor()

    categorias = {
        'Alimentos': ['Grãos', 'Massas', 'Enlatados', 'Biscoitos'],
        'Bebidas': ['Refrigerantes', 'Sucos', 'Águas'],
        'Limpeza': ['Detergentes', 'Sabão', 'Amaciantes'],
        'Higiene': ['Shampoo', 'Sabonete', 'Pasta de dente']
    }

    produtos = [
        'Arroz Branco 5kg', 'Feijão Preto 1kg', 'Macarrão Espaguete 500g',
        'Óleo de Soja 900ml', 'Açúcar Cristal 1kg', 'Sal Refinado 1kg',
        'Café Torrado 500g', 'Farinha de Trigo 1kg', 'Leite Integral 1L',
        'Achocolatado Pó 400g', 'Bolacha Cream Cracker', 'Bolacha Recheada',
        'Biscoito Maisena', 'Biscoito Agua e Sal', 'Suco de Laranja 1L',
        'Refrigerante Cola 2L', 'Refrigerante Guaraná 2L', 'Água Mineral 1.5L',
        'Detergente Líquido 500ml', 'Sabão em Pó 1kg', 'Amaciante 2L',
        'Desinfetante 2L', 'Água Sanitária 1L', 'Esponja Multiuso',
        'Shampoo 400ml', 'Condicionador 400ml', 'Sabonete 90g',
        'Papel Higiênico 12un', 'Pasta de Dente 90g', 'Fralda Descartável',
        'Queijo Mussarela kg', 'Presunto kg', 'Mortadela kg',
        'Linguiça Toscana kg', 'Carne Moída kg', 'Frango Inteiro kg',
        'Tomate kg', 'Cebola kg', 'Batata kg', 'Alface un',
        'Banana Prata kg', 'Maçã kg', 'Laranja kg', 'Melancia kg',
        'Pão Francês kg', 'Pão de Forma', 'Bolo Simples', 'Iogurte 170g',
        'Margarina 500g', 'Requeijão 200g'
    ]

    curvas_abc = ['A', 'A', 'A', 'B', 'B', 'B', 'B', 'C', 'C', 'C']

    codigo = 1001
    for produto in produtos:
        # Escolher categoria aleatória
        categoria = random.choice(list(categorias.keys()))
        subcategoria = random.choice(categorias[categoria])
        curva = random.choice(curvas_abc)

        cursor.execute("""
            INSERT INTO cadastro_produtos
            (codigo, descricao, categoria, subcategoria, und_venda, curva_abc, ativo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (codigo, produto, categoria, subcategoria, 'UN', curva, True))

        codigo += 1

    conn.commit()
    print(f"   OK - {len(produtos)} produtos criados")
    cursor.close()

def popular_historico_vendas(conn):
    """Cria histórico de vendas (últimos 2 anos)"""
    print("\n3. Criando histórico de vendas...")
    print("   (Isso pode levar 1-2 minutos...)")

    cursor = conn.cursor()

    # Buscar produtos e lojas
    cursor.execute("SELECT codigo, curva_abc FROM cadastro_produtos")
    produtos = cursor.fetchall()

    cursor.execute("SELECT cod_empresa FROM cadastro_lojas")
    lojas = [row[0] for row in cursor.fetchall()]

    # Gerar vendas diárias dos últimos 2 anos
    data_inicio = datetime.now() - timedelta(days=730)  # 2 anos
    data_fim = datetime.now()

    total_registros = 0
    batch = []

    data_atual = data_inicio
    while data_atual <= data_fim:
        # Para cada loja
        for loja in lojas:
            # Selecionar produtos aleatórios para vender neste dia
            produtos_do_dia = random.sample(produtos, k=random.randint(20, 40))

            for codigo, curva in produtos_do_dia:
                # Quantidade base por curva
                if curva == 'A':
                    qtd_base = random.uniform(50, 200)
                elif curva == 'B':
                    qtd_base = random.uniform(20, 80)
                else:  # C
                    qtd_base = random.uniform(5, 30)

                # Variação por dia da semana
                dia_semana = data_atual.weekday()
                if dia_semana in [5, 6]:  # Fim de semana
                    qtd_base *= 1.3

                # Variação aleatória
                qtd = qtd_base * random.uniform(0.7, 1.3)

                # Valor unitário aleatório
                valor_unit = random.uniform(3, 50)
                valor_total = qtd * valor_unit

                batch.append((
                    data_atual.strftime('%Y-%m-%d'),
                    loja,
                    codigo,
                    round(qtd, 2),
                    round(valor_total, 2)
                ))

                # Insert em lotes de 1000
                if len(batch) >= 1000:
                    cursor.executemany("""
                        INSERT INTO historico_vendas_diario
                        (data, cod_empresa, codigo, qtd_venda, valor_venda)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, batch)
                    total_registros += len(batch)
                    print(f"   Inseridos: {total_registros} registros...", end='\r')
                    batch = []

        data_atual += timedelta(days=1)

    # Inserir últimos registros
    if batch:
        cursor.executemany("""
            INSERT INTO historico_vendas_diario
            (data, cod_empresa, codigo, qtd_venda, valor_venda)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, batch)
        total_registros += len(batch)

    conn.commit()
    print(f"\n   OK - {total_registros} registros de vendas criados")
    cursor.close()

def popular_estoque_atual(conn):
    """Cria estoque atual para cada produto/loja"""
    print("\n4. Criando estoque atual...")
    cursor = conn.cursor()

    cursor.execute("SELECT codigo FROM cadastro_produtos")
    produtos = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT cod_empresa FROM cadastro_lojas")
    lojas = [row[0] for row in cursor.fetchall()]

    total = 0
    for loja in lojas:
        for codigo in produtos:
            qtd_estoque = random.uniform(50, 500)

            cursor.execute("""
                INSERT INTO estoque_atual (cod_empresa, codigo, qtd_estoque)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (loja, codigo, round(qtd_estoque, 2)))
            total += 1

    conn.commit()
    print(f"   OK - {total} registros de estoque criados")
    cursor.close()

def popular_eventos_promocionais(conn):
    """Cria eventos promocionais"""
    print("\n5. Criando eventos promocionais...")
    cursor = conn.cursor()

    eventos = [
        ('Black Friday 2024', '2024-11-24', '2024-11-30', 'BlackFriday', 35.5),
        ('Natal 2024', '2024-12-15', '2024-12-25', 'Natal', 28.0),
        ('Ano Novo 2025', '2024-12-26', '2025-01-05', 'AnoNovo', 22.0),
        ('Carnaval 2025', '2025-02-28', '2025-03-05', 'Carnaval', 18.0),
        ('Páscoa 2025', '2025-03-25', '2025-04-05', 'Páscoa', 25.0),
        ('Dia das Mães 2025', '2025-05-05', '2025-05-11', 'DiadasMaes', 20.0),
        ('Dia dos Namorados 2025', '2025-06-06', '2025-06-12', 'Namorados', 15.0),
        ('Dia dos Pais 2025', '2025-08-04', '2025-08-10', 'DiadosPais', 18.0),
        ('Volta às Aulas 2025', '2025-01-15', '2025-02-05', 'VoltaAulas', 12.0),
        ('Copa do Mundo (futuro)', '2026-06-11', '2026-07-19', 'Copa', 30.0),
    ]

    for evento in eventos:
        cursor.execute("""
            INSERT INTO eventos_promocionais
            (nome_evento, data_inicio, data_fim, tipo_evento, impacto_estimado, ativo)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (*evento, True))

    conn.commit()
    print(f"   OK - {len(eventos)} eventos criados")
    cursor.close()

def main():
    print("="*60)
    print("   POPULANDO BANCO COM DADOS DE TESTE")
    print("="*60)
    print()
    print("Conectando ao banco...")

    conn = conectar()
    print("OK - Conectado!")

    try:
        popular_cadastro_lojas(conn)
        popular_cadastro_produtos(conn)
        popular_historico_vendas(conn)
        popular_estoque_atual(conn)
        popular_eventos_promocionais(conn)

        print()
        print("="*60)
        print("   DADOS DE TESTE CRIADOS COM SUCESSO!")
        print("="*60)
        print()
        print("Resumo:")
        print("  - 5 lojas")
        print("  - 50 produtos")
        print("  - ~150.000 registros de vendas (2 anos)")
        print("  - 250 registros de estoque atual")
        print("  - 10 eventos promocionais")
        print()
        print("Próximo passo:")
        print("  Acesse a ferramenta: python app.py")
        print("  http://127.0.0.1:5000")

    except Exception as e:
        print(f"\nERRO: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
