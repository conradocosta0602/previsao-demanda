# -*- coding: utf-8 -*-
"""Script para importar dados da categoria Forceline (Eletrica)"""
import sys
import os
import csv
from datetime import datetime

# Adicionar diretorio ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar funcao de conexao do app
from app import get_db_connection

# Diretorio base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def importar_fornecedores_arquivo(arquivo, conn, cursor):
    """Importa fornecedores de um arquivo CSV"""
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cnpj = row['cnpj']
            fantas = row['fantas']
            cod_empresa = row['cod_empresa']
            tipo_destino = row['tipo_destino']
            lead_time = int(row['lead_time_dias'])
            ciclo_pedido = int(row['ciclo_pedido_dias'])
            fat_minimo = float(row['fat_minimo']) if row['fat_minimo'] else 0

            # Verificar se ja existe
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
                """, (fantas, tipo_destino, lead_time, ciclo_pedido, fat_minimo, cnpj, cod_empresa))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO cadastro_fornecedores
                    (cnpj, nome_fantasia, cod_empresa, tipo_destino, lead_time_dias, ciclo_pedido_dias, faturamento_minimo, ativo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                """, (cnpj, fantas, cod_empresa, tipo_destino, lead_time, ciclo_pedido, fat_minimo))
                inseridos += 1

    return inseridos, atualizados


def importar_fornecedores():
    """Importa cadastro de fornecedores de todos os arquivos"""
    print('\n' + '='*60)
    print('1. IMPORTANDO FORNECEDORES')
    print('='*60)

    arquivos = [
        os.path.join(BASE_DIR, 'Cadastro de Fornecedores_Forceline_22_01_26 (1)'),
        os.path.join(BASE_DIR, 'Cadastro de Fornecedores_Pial_26_01_26'),
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    total_inseridos = 0
    total_atualizados = 0

    for arquivo in arquivos:
        if os.path.exists(arquivo):
            nome = os.path.basename(arquivo)
            print(f'   Processando: {nome}')
            inseridos, atualizados = importar_fornecedores_arquivo(arquivo, conn, cursor)
            total_inseridos += inseridos
            total_atualizados += atualizados
            print(f'      -> Inseridos: {inseridos}, Atualizados: {atualizados}')
            conn.commit()

    conn.close()

    print(f'   TOTAL Inseridos: {total_inseridos}')
    print(f'   TOTAL Atualizados: {total_atualizados}')
    print(f'   TOTAL processado: {total_inseridos + total_atualizados}')
    return total_inseridos + total_atualizados


def limpar_texto(texto):
    """Remove caracteres especiais problematicos e normaliza o texto"""
    if not texto:
        return ''
    # Substituir caracteres especiais comuns por equivalentes ASCII
    import unicodedata
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = texto.encode('ascii', 'ignore').decode('ascii')
    return texto.strip().strip('"')


def importar_produtos_arquivo(arquivo, conn, cursor, fornecedor_map, separador=','):
    """Importa produtos de um arquivo CSV"""
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter=separador)
        for row in reader:
            # Normalizar nomes das colunas (maiusculas ou minusculas)
            row_lower = {k.lower().strip().strip('"'): v for k, v in row.items()}

            codigo_str = row_lower.get('codigo', '')
            if not codigo_str:
                continue
            codigo = int(codigo_str.strip('"'))

            descricao = limpar_texto(row_lower.get('descricao', ''))
            cnpj = row_lower.get('cnpj', '').strip('"')
            categoria = limpar_texto(row_lower.get('descr_linha1', ''))
            subcategoria = limpar_texto(row_lower.get('descr_linha3', ''))

            # Buscar id_fornecedor pelo cnpj
            id_fornecedor = fornecedor_map.get(cnpj)

            # Verificar se ja existe
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

    return inseridos, atualizados


def importar_produtos():
    """Importa cadastro de produtos de todos os arquivos"""
    print('\n' + '='*60)
    print('2. IMPORTANDO PRODUTOS')
    print('='*60)

    # Arquivos com seus separadores
    arquivos = [
        (os.path.join(BASE_DIR, 'Cadastro de Produtos_Forceline_22_01_26 (1)'), ','),
        (os.path.join(BASE_DIR, 'Cadastro de Produtos_Forceline_26_01_26.csv'), ';'),
        (os.path.join(BASE_DIR, 'Cadastro de Produtos_Pial_26_01_26'), ','),
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Obter mapeamento de fornecedor (cnpj -> id)
    cursor.execute("SELECT id, cnpj FROM cadastro_fornecedores")
    fornecedor_map = {row[1]: row[0] for row in cursor.fetchall()}

    total_inseridos = 0
    total_atualizados = 0

    for arquivo, separador in arquivos:
        if os.path.exists(arquivo):
            nome = os.path.basename(arquivo)
            print(f'   Processando: {nome}')
            inseridos, atualizados = importar_produtos_arquivo(arquivo, conn, cursor, fornecedor_map, separador)
            total_inseridos += inseridos
            total_atualizados += atualizados
            print(f'      -> Inseridos: {inseridos}, Atualizados: {atualizados}')
            conn.commit()

    conn.close()

    print(f'   TOTAL Inseridos: {total_inseridos}')
    print(f'   TOTAL Atualizados: {total_atualizados}')
    print(f'   TOTAL processado: {total_inseridos + total_atualizados}')
    return total_inseridos + total_atualizados


def importar_estoque_arquivo(arquivo, conn, cursor, data_importacao):
    """Importa estoque de um arquivo CSV"""
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            codigo = int(row['codigo'])
            cod_empresa = int(row['cod_empresa'])
            sit_venda = row.get('sit_venda', '')
            cue = float(row['cue']) if row['cue'] else 0
            estoque = float(row['estoque']) if row['estoque'] else 0
            qtd_pendente = float(row['qtd_pendente']) if row['qtd_pendente'] else 0
            qtd_pend_transf = float(row['qtd_pend_transf']) if row['qtd_pend_transf'] else 0
            preco_venda = float(row['preco_venda']) if row['preco_venda'] else 0
            curva_abc = row.get('curva_abc_popularidade', '')

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

    return inseridos, atualizados


def importar_estoque():
    """Importa posicao de estoque de todos os arquivos"""
    print('\n' + '='*60)
    print('3. IMPORTANDO ESTOQUE')
    print('='*60)

    arquivos = [
        os.path.join(BASE_DIR, 'Relatório de Posição de Estoque_Forceline_22_01_26 (1)'),
        os.path.join(BASE_DIR, 'Relatório de Posição de Estoque_Pial_26_01_26'),
    ]

    conn = get_db_connection()
    cursor = conn.cursor()
    data_importacao = datetime.now()

    total_inseridos = 0
    total_atualizados = 0

    for arquivo in arquivos:
        if os.path.exists(arquivo):
            nome = os.path.basename(arquivo)
            print(f'   Processando: {nome}')
            inseridos, atualizados = importar_estoque_arquivo(arquivo, conn, cursor, data_importacao)
            total_inseridos += inseridos
            total_atualizados += atualizados
            print(f'      -> Inseridos: {inseridos:,}, Atualizados: {atualizados:,}')
            conn.commit()

    conn.close()

    print(f'   TOTAL Inseridos: {total_inseridos:,}')
    print(f'   TOTAL Atualizados: {total_atualizados:,}')
    print(f'   TOTAL processado: {total_inseridos + total_atualizados:,}')
    return total_inseridos + total_atualizados


def importar_situacao_compra_arquivo(arquivo, conn, cursor):
    """Importa situacao de compra de um arquivo CSV"""
    inseridos = 0
    atualizados = 0
    situacoes_validas = ['FL', 'NC', 'EN', 'CO', 'FF']

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

    return inseridos, atualizados


def importar_situacao_compra():
    """Importa situacao de compra dos itens de todos os arquivos"""
    print('\n' + '='*60)
    print('4. IMPORTANDO SITUACAO DE COMPRA')
    print('='*60)

    arquivos = [
        os.path.join(BASE_DIR, 'Relatório de Posição de Estoque_Forceline_22_01_26 (1)'),
        os.path.join(BASE_DIR, 'Relatório de Posição de Estoque_Pial_26_01_26'),
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    total_inseridos = 0
    total_atualizados = 0

    for arquivo in arquivos:
        if os.path.exists(arquivo):
            nome = os.path.basename(arquivo)
            print(f'   Processando: {nome}')
            inseridos, atualizados = importar_situacao_compra_arquivo(arquivo, conn, cursor)
            total_inseridos += inseridos
            total_atualizados += atualizados
            print(f'      -> Inseridos: {inseridos:,}, Atualizados: {atualizados:,}')
            conn.commit()

    conn.close()

    print(f'   TOTAL Inseridos: {total_inseridos:,}')
    print(f'   TOTAL Atualizados: {total_atualizados:,}')
    print(f'   TOTAL processado: {total_inseridos + total_atualizados:,}')
    return total_inseridos + total_atualizados


def importar_vendas(arquivo, mes_referencia):
    """Importa historico de vendas"""
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
            data_str = row['data']
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
            cod_empresa = int(row['cod_empresa'])
            codigo = int(row['codigo'])
            qtd_venda = float(row['qtd_venda']) if row['qtd_venda'] else 0
            prc_venda = float(row['prc_venda']) if row['prc_venda'] else 0
            valor_venda = qtd_venda * prc_venda

            # Calcular campos auxiliares
            dia_semana = data.weekday()
            dia_mes = data.day
            semana_ano = data.isocalendar()[1]
            mes = data.month
            ano = data.year
            fim_semana = dia_semana >= 5

            # Verificar se ja existe
            cursor.execute("""
                SELECT id FROM historico_vendas_diario
                WHERE data = %s AND cod_empresa = %s AND codigo = %s
            """, (data, cod_empresa, codigo))

            if cursor.fetchone():
                # Atualizar
                cursor.execute("""
                    UPDATE historico_vendas_diario
                    SET qtd_venda = %s, valor_venda = %s
                    WHERE data = %s AND cod_empresa = %s AND codigo = %s
                """, (qtd_venda, valor_venda, data, cod_empresa, codigo))
                atualizados += 1
            else:
                # Inserir
                cursor.execute("""
                    INSERT INTO historico_vendas_diario
                    (data, cod_empresa, codigo, qtd_venda, valor_venda,
                     dia_semana, dia_mes, semana_ano, mes, ano, fim_semana, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (data, cod_empresa, codigo, qtd_venda, valor_venda,
                      dia_semana, dia_mes, semana_ano, mes, ano, fim_semana))
                inseridos += 1

            if (inseridos + atualizados) % 10000 == 0:
                print(f'   Processados: {inseridos + atualizados:,}...')
                conn.commit()

    conn.commit()
    conn.close()

    print(f'   Inseridos: {inseridos:,}')
    print(f'   Atualizados: {atualizados:,}')
    print(f'   Total processado: {inseridos + atualizados:,}')
    return inseridos + atualizados


def main():
    print('='*60)
    print('IMPORTACAO DE DADOS - CATEGORIA FORCELINE (ELETRICA)')
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

    # 5. Vendas Dezembro/2025
    arquivo_dez = os.path.join(BASE_DIR, 'demanda_Eletrica_01-12-2025 (1)')
    print('\n' + '='*60)
    print('5. IMPORTANDO VENDAS - DEZEMBRO/2025')
    total_dez = importar_vendas(arquivo_dez, 'Dezembro/2025')

    # 6. Vendas Janeiro/2026
    arquivo_jan = os.path.join(BASE_DIR, 'demanda_Eletrica_01-01-2026 (1)')
    print('\n' + '='*60)
    print('6. IMPORTANDO VENDAS - JANEIRO/2026')
    total_jan = importar_vendas(arquivo_jan, 'Janeiro/2026')

    # Resumo
    print('\n' + '='*60)
    print('RESUMO DA IMPORTACAO')
    print('='*60)
    print(f'   Fornecedores: {total_forn}')
    print(f'   Produtos: {total_prod}')
    print(f'   Estoque: {total_est}')
    print(f'   Situacao Compra: {total_sit}')
    print(f'   Vendas Dez/2025: {total_dez:,}')
    print(f'   Vendas Jan/2026: {total_jan:,}')
    print('='*60)
    print('IMPORTACAO CONCLUIDA!')
    print('='*60)


if __name__ == '__main__':
    main()
