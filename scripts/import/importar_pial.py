# -*- coding: utf-8 -*-
"""Script para importar dados Pial e fornecedores associados (Daneva, Bticino, Cemar, HDL)"""
import sys
import os
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import get_db_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def limpar_texto(texto):
    if not texto:
        return ''
    import unicodedata
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = texto.encode('ascii', 'ignore').decode('ascii')
    return texto.strip().strip('"')


def importar_fornecedores():
    print('\n' + '='*60)
    print('1. IMPORTANDO FORNECEDORES')
    print('='*60)

    arquivo = os.path.join(BASE_DIR, 'Cadastro de Fornecedores_Pial_27_01_26.csv')
    conn = get_db_connection()
    cursor = conn.cursor()
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cnpj = row['cnpj'].strip()
            fantas = row['fantas'].strip()
            cod_empresa = row['cod_empresa'].strip()
            tipo_destino = row['tipo_destino'].strip()
            lead_time = int(row['lead_time_dias'].strip())
            ciclo = int(row['ciclo_pedido_dias'].strip())
            fat_min = float(row['fat_minimo'].strip()) if row['fat_minimo'].strip() else 0

            cursor.execute("""
                SELECT id FROM cadastro_fornecedores
                WHERE cnpj = %s AND cod_empresa = %s
            """, (cnpj, cod_empresa))

            if cursor.fetchone():
                cursor.execute("""
                    UPDATE cadastro_fornecedores
                    SET nome_fantasia = %s, tipo_destino = %s, lead_time_dias = %s,
                        ciclo_pedido_dias = %s, faturamento_minimo = %s, ativo = TRUE
                    WHERE cnpj = %s AND cod_empresa = %s
                """, (fantas, tipo_destino, lead_time, ciclo, fat_min, cnpj, cod_empresa))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO cadastro_fornecedores
                    (cnpj, nome_fantasia, cod_empresa, tipo_destino, lead_time_dias, ciclo_pedido_dias, faturamento_minimo, ativo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                """, (cnpj, fantas, cod_empresa, tipo_destino, lead_time, ciclo, fat_min))
                inseridos += 1

    conn.commit()
    conn.close()
    print(f'   Inseridos: {inseridos}, Atualizados: {atualizados}')
    return inseridos + atualizados


def importar_produtos():
    print('\n' + '='*60)
    print('2. IMPORTANDO PRODUTOS')
    print('='*60)

    arquivo = os.path.join(BASE_DIR, 'Cadastro de Produtos_Pial_27_01_26.csv')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Mapear CNPJ -> primeiro id fornecedor
    cursor.execute("SELECT id, cnpj FROM cadastro_fornecedores")
    fornecedor_map = {}
    for row in cursor.fetchall():
        if row[1] not in fornecedor_map:
            fornecedor_map[row[1]] = row[0]

    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            codigo_str = row.get('codigo', '').strip().strip('"')
            if not codigo_str:
                continue
            codigo = int(codigo_str)
            descricao = limpar_texto(row.get('descricao', ''))
            cnpj = row.get('cnpj', '').strip().strip('"')
            categoria = limpar_texto(row.get('descr_linha1', ''))
            subcategoria = limpar_texto(row.get('descr_linha3', ''))
            id_fornecedor = fornecedor_map.get(cnpj)

            cursor.execute("SELECT codigo FROM cadastro_produtos WHERE codigo = %s", (codigo,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE cadastro_produtos
                    SET descricao = %s, categoria = %s, subcategoria = %s,
                        id_fornecedor = %s, ativo = TRUE, updated_at = NOW()
                    WHERE codigo = %s
                """, (descricao, categoria, subcategoria, id_fornecedor, codigo))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO cadastro_produtos
                    (codigo, descricao, categoria, subcategoria, id_fornecedor, ativo, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                """, (codigo, descricao, categoria, subcategoria, id_fornecedor))
                inseridos += 1

    conn.commit()
    conn.close()
    print(f'   Inseridos: {inseridos}, Atualizados: {atualizados}')
    return inseridos + atualizados


def importar_estoque():
    print('\n' + '='*60)
    print('3. IMPORTANDO ESTOQUE')
    print('='*60)

    arquivo = os.path.join(BASE_DIR, u'Relat\u00f3rio de Posi\u00e7\u00e3o de Estoque_Pial_27_01_26.csv')
    conn = get_db_connection()
    cursor = conn.cursor()
    data_importacao = datetime.now()
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            codigo = int(row['codigo'])
            cod_empresa = int(row['cod_empresa'])
            sit_venda = row.get('sit_venda', '').strip()
            cue = float(row['cue']) if row['cue'] else 0
            estoque = float(row['estoque']) if row['estoque'] else 0
            qtd_pendente = float(row['qtd_pendente']) if row['qtd_pendente'] else 0
            qtd_pend_transf = float(row['qtd_pend_transf']) if row['qtd_pend_transf'] else 0
            preco_venda = float(row['preco_venda']) if row['preco_venda'] else 0
            curva_abc = row.get('curva_abc_popularidade', '').strip()

            cursor.execute("""
                SELECT id FROM estoque_posicao_atual
                WHERE codigo = %s AND cod_empresa = %s
            """, (codigo, cod_empresa))

            if cursor.fetchone():
                cursor.execute("""
                    UPDATE estoque_posicao_atual
                    SET sit_venda = %s, cue = %s, estoque = %s,
                        qtd_pendente = %s, qtd_pend_transf = %s, preco_venda = %s,
                        curva_abc = %s, data_importacao = %s
                    WHERE codigo = %s AND cod_empresa = %s
                """, (sit_venda, cue, estoque, qtd_pendente, qtd_pend_transf,
                      preco_venda, curva_abc, data_importacao, codigo, cod_empresa))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO estoque_posicao_atual
                    (codigo, cod_empresa, sit_venda, cue, estoque,
                     qtd_pendente, qtd_pend_transf, preco_venda, curva_abc, data_importacao)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (codigo, cod_empresa, sit_venda, cue, estoque,
                      qtd_pendente, qtd_pend_transf, preco_venda, curva_abc, data_importacao))
                inseridos += 1

            if (inseridos + atualizados) % 1000 == 0 and (inseridos + atualizados) > 0:
                conn.commit()

    conn.commit()
    conn.close()
    print(f'   Inseridos: {inseridos:,}, Atualizados: {atualizados:,}')
    return inseridos + atualizados


def importar_situacao_compra():
    print('\n' + '='*60)
    print('4. IMPORTANDO SITUACAO DE COMPRA')
    print('='*60)

    arquivo = os.path.join(BASE_DIR, u'Relat\u00f3rio de Posi\u00e7\u00e3o de Estoque_Pial_27_01_26.csv')
    conn = get_db_connection()
    cursor = conn.cursor()
    situacoes_validas = ['FL', 'NC', 'EN', 'CO', 'FF']
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            codigo = int(row['codigo'])
            cod_empresa = int(row['cod_empresa'])
            sit_compra = row.get('sit_compra', '').strip()

            if sit_compra and sit_compra in situacoes_validas:
                cursor.execute("""
                    SELECT id FROM situacao_compra_itens
                    WHERE codigo = %s AND cod_empresa = %s
                """, (codigo, cod_empresa))

                if cursor.fetchone():
                    cursor.execute("""
                        UPDATE situacao_compra_itens
                        SET sit_compra = %s, updated_at = NOW()
                        WHERE codigo = %s AND cod_empresa = %s
                    """, (sit_compra, codigo, cod_empresa))
                    atualizados += 1
                else:
                    cursor.execute("""
                        INSERT INTO situacao_compra_itens
                        (codigo, cod_empresa, sit_compra, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                    """, (codigo, cod_empresa, sit_compra))
                    inseridos += 1

            if (inseridos + atualizados) % 1000 == 0 and (inseridos + atualizados) > 0:
                conn.commit()

    conn.commit()
    conn.close()
    print(f'   Inseridos: {inseridos:,}, Atualizados: {atualizados:,}')
    return inseridos + atualizados


def importar_vendas(arquivo, mes_referencia):
    print('\n' + '='*60)
    print(f'IMPORTANDO VENDAS - {mes_referencia}')
    print('='*60)

    conn = get_db_connection()
    cursor = conn.cursor()
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data_str = row['data'].strip()
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
            cod_empresa = int(row['cod_empresa'])
            codigo = int(row['codigo'])
            qtd_venda = float(row['qtd_venda']) if row['qtd_venda'] else 0
            prc_venda = float(row.get('prc_venda', '0')) if row.get('prc_venda', '').strip() else 0
            valor_venda = qtd_venda * prc_venda

            dia_semana = data.weekday()
            dia_mes = data.day
            semana_ano = data.isocalendar()[1]
            mes = data.month
            ano = data.year
            fim_semana = dia_semana >= 5

            cursor.execute("""
                SELECT id FROM historico_vendas_diario
                WHERE data = %s AND cod_empresa = %s AND codigo = %s
            """, (data, cod_empresa, codigo))

            if cursor.fetchone():
                cursor.execute("""
                    UPDATE historico_vendas_diario
                    SET qtd_venda = %s, valor_venda = %s
                    WHERE data = %s AND cod_empresa = %s AND codigo = %s
                """, (qtd_venda, valor_venda, data, cod_empresa, codigo))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO historico_vendas_diario
                    (data, cod_empresa, codigo, qtd_venda, valor_venda,
                     dia_semana, dia_mes, semana_ano, mes, ano, fim_semana, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (data, cod_empresa, codigo, qtd_venda, valor_venda,
                      dia_semana, dia_mes, semana_ano, mes, ano, fim_semana))
                inseridos += 1

            if (inseridos + atualizados) % 10000 == 0 and (inseridos + atualizados) > 0:
                print(f'   Processados: {inseridos + atualizados:,}...')
                conn.commit()

    conn.commit()
    conn.close()
    print(f'   Inseridos: {inseridos:,}, Atualizados: {atualizados:,}')
    return inseridos + atualizados


def main():
    print('='*60)
    print('IMPORTACAO DE DADOS - PIAL E FORNECEDORES ASSOCIADOS')
    print('(Daneva, Pial Legrand, Bticino, Cemar, HDL)')
    print('='*60)
    print(f'Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')

    # 1. Fornecedores
    total_forn = importar_fornecedores()

    # 2. Produtos
    total_prod = importar_produtos()

    # 3. Estoque
    total_est = importar_estoque()

    # 4. Situacao de compra
    total_sit = importar_situacao_compra()

    # 5. Vendas
    arquivos_vendas = [
        ('demanda_Pial_2023.csv', '2023'),
        ('demanda_Pial_2024.csv', '2024'),
        ('demanda_Pial_2025.csv', '2025'),
        ('demanda_Pial_25-01-2026.csv', 'Jan/2026'),
    ]

    totais_vendas = {}
    for arq, label in arquivos_vendas:
        path = os.path.join(BASE_DIR, arq)
        if os.path.exists(path):
            totais_vendas[label] = importar_vendas(path, label)
        else:
            print(f'   ARQUIVO NAO ENCONTRADO: {arq}')

    # Resumo
    print('\n' + '='*60)
    print('RESUMO DA IMPORTACAO')
    print('='*60)
    print(f'   Fornecedores: {total_forn}')
    print(f'   Produtos: {total_prod}')
    print(f'   Estoque: {total_est}')
    print(f'   Situacao Compra: {total_sit}')
    for label, total in totais_vendas.items():
        print(f'   Vendas {label}: {total:,}')
    print('='*60)
    print('IMPORTACAO CONCLUIDA!')
    print('='*60)


if __name__ == '__main__':
    main()
