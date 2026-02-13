# -*- coding: utf-8 -*-
"""
Script de importacao de dados Soprano
Data: 11/02/2026
"""
import psycopg2
import csv
import os
from datetime import datetime

# Configuracao do banco
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'previsao_demanda'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'FerreiraCost@01'),
    'port': int(os.environ.get('DB_PORT', 5432))
}

# Diretorio base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding('LATIN1')
    return conn

def importar_fornecedores():
    """Importa parametros de fornecedor Soprano"""
    print("\n" + "="*60)
    print("IMPORTANDO FORNECEDORES SOPRANO")
    print("="*60)

    arquivo = os.path.join(BASE_DIR, "Cadastro de Fornecedores_Soprano_11_02_26.csv")

    conn = get_connection()
    cursor = conn.cursor()

    total = 0
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            cnpj = row['cnpj']
            nome = row['fantas']
            cod_empresa = int(row['cod_empresa'])
            tipo_destino = row['tipo_destino']
            lead_time = int(row['lead_time_dias'])
            ciclo = int(row['ciclo_pedido_dias'])
            fat_minimo = float(row['fat_minimo']) if row['fat_minimo'] else 0

            # Verificar se existe
            cursor.execute("""
                SELECT id FROM parametros_fornecedor
                WHERE cnpj_fornecedor = %s AND cod_empresa = %s
            """, (cnpj, cod_empresa))

            exists = cursor.fetchone()

            if exists:
                cursor.execute("""
                    UPDATE parametros_fornecedor SET
                        nome_fornecedor = %s,
                        tipo_destino = %s,
                        lead_time_dias = %s,
                        ciclo_pedido_dias = %s,
                        pedido_minimo_valor = %s,
                        data_importacao = NOW()
                    WHERE cnpj_fornecedor = %s AND cod_empresa = %s
                """, (nome, tipo_destino, lead_time, ciclo, fat_minimo, cnpj, cod_empresa))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO parametros_fornecedor
                    (cnpj_fornecedor, nome_fornecedor, cod_empresa, tipo_destino,
                     lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (cnpj, nome, cod_empresa, tipo_destino, lead_time, ciclo, fat_minimo))
                inseridos += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Total lidos: {total}")
    print(f"Inseridos: {inseridos}")
    print(f"Atualizados: {atualizados}")
    return total

def importar_produtos():
    """Importa cadastro de produtos Soprano"""
    print("\n" + "="*60)
    print("IMPORTANDO PRODUTOS SOPRANO")
    print("="*60)

    arquivo = os.path.join(BASE_DIR, "Cadastro de Produtos_Soprano_11_02_26.csv")

    conn = get_connection()
    cursor = conn.cursor()

    total = 0
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            codigo = row['codigo']
            descricao = row['descricao']
            nome_forn = row['fantas']
            cnpj = row['cnpj']
            linha1 = row.get('descr_linha1', '')
            linha3 = row.get('linha3', '')
            descr_linha3 = row.get('descr_linha3', '')

            # Mapeamento: categoria = descr_linha1, codigo_linha = linha3, descricao_linha = descr_linha3
            categoria = linha1
            codigo_linha = linha3
            descricao_linha = descr_linha3

            # Verificar se existe
            cursor.execute("""
                SELECT cod_produto FROM cadastro_produtos_completo
                WHERE cod_produto = %s
            """, (codigo,))

            exists = cursor.fetchone()

            if exists:
                cursor.execute("""
                    UPDATE cadastro_produtos_completo SET
                        descricao = %s,
                        nome_fornecedor = %s,
                        cnpj_fornecedor = %s,
                        categoria = %s,
                        codigo_linha = %s,
                        descricao_linha = %s
                    WHERE cod_produto = %s
                """, (descricao, nome_forn, cnpj, categoria, codigo_linha, descricao_linha, codigo))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO cadastro_produtos_completo
                    (cod_produto, descricao, nome_fornecedor, cnpj_fornecedor,
                     categoria, codigo_linha, descricao_linha)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (codigo, descricao, nome_forn, cnpj, categoria, codigo_linha, descricao_linha))
                inseridos += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Total lidos: {total}")
    print(f"Inseridos: {inseridos}")
    print(f"Atualizados: {atualizados}")
    return total

def importar_estoque():
    """Importa posicao de estoque Soprano"""
    print("\n" + "="*60)
    print("IMPORTANDO ESTOQUE SOPRANO")
    print("="*60)

    arquivo = os.path.join(BASE_DIR, "Relatório de Posição de Estoque_Soprano_11_02_26.csv")

    conn = get_connection()
    cursor = conn.cursor()

    total = 0
    inseridos = 0
    atualizados = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            codigo = int(row['codigo'])
            cod_empresa = int(row['cod_empresa'])
            sit_venda = row.get('sit_venda', '') or None
            sit_compra = row.get('sit_compra', '') or None
            cue = float(row['cue']) if row['cue'] else 0
            estoque = int(row['estoque']) if row['estoque'] else 0
            qtd_pendente = int(row['qtd_pendente']) if row['qtd_pendente'] else 0
            qtd_pend_transf = float(row['qtd_pend_transf']) if row['qtd_pend_transf'] else 0
            preco_venda = float(row['preco_venda']) if row['preco_venda'] else 0
            curva = row.get('curva_abc_popularidade', '') or None

            # Verificar se existe
            cursor.execute("""
                SELECT id FROM estoque_posicao_atual
                WHERE codigo = %s AND cod_empresa = %s
            """, (codigo, cod_empresa))

            exists = cursor.fetchone()

            if exists:
                cursor.execute("""
                    UPDATE estoque_posicao_atual SET
                        sit_venda = %s,
                        sit_compra = %s,
                        cue = %s,
                        estoque = %s,
                        qtd_pendente = %s,
                        qtd_pend_transf = %s,
                        preco_venda = %s,
                        curva_abc = %s,
                        data_importacao = NOW()
                    WHERE codigo = %s AND cod_empresa = %s
                """, (sit_venda, sit_compra, cue, estoque, qtd_pendente,
                      qtd_pend_transf, preco_venda, curva, codigo, cod_empresa))
                atualizados += 1
            else:
                cursor.execute("""
                    INSERT INTO estoque_posicao_atual
                    (codigo, cod_empresa, sit_venda, sit_compra, cue,
                     estoque, qtd_pendente, qtd_pend_transf, preco_venda, curva_abc)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (codigo, cod_empresa, sit_venda, sit_compra, cue, estoque,
                      qtd_pendente, qtd_pend_transf, preco_venda, curva))
                inseridos += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Total lidos: {total}")
    print(f"Inseridos: {inseridos}")
    print(f"Atualizados: {atualizados}")
    return total

def importar_demanda(arquivo, descricao, ano):
    """Importa arquivo de demanda para tabela do ano especifico"""
    print(f"\nImportando: {descricao}")
    print("-"*40)

    filepath = os.path.join(BASE_DIR, arquivo)

    if not os.path.exists(filepath):
        print(f"ERRO: Arquivo nao encontrado: {arquivo}")
        return 0

    tabela = f"historico_vendas_diario_{ano}"

    conn = get_connection()
    cursor = conn.cursor()

    total = 0
    inseridos = 0
    atualizados = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1

            data_str = row['data']
            cod_empresa = int(row['cod_empresa'])
            codigo = row['codigo']
            qtd_venda = int(float(row['qtd_venda'])) if row['qtd_venda'] else 0

            # Converter data
            try:
                data = datetime.strptime(data_str, '%Y-%m-%d').date()
            except:
                continue

            # Extrair informacoes da data
            dia_semana = data.weekday()  # 0=segunda, 6=domingo
            dia_mes = data.day
            semana_ano = data.isocalendar()[1]
            mes = data.month
            ano_data = data.year
            fim_semana = True if dia_semana >= 5 else False

            # Pular se ano nao corresponde
            if ano_data != ano:
                continue

            # Verificar se existe
            cursor.execute(f"""
                SELECT id FROM {tabela}
                WHERE data = %s AND cod_empresa = %s AND codigo = %s
            """, (data, cod_empresa, codigo))

            exists = cursor.fetchone()

            if exists:
                cursor.execute(f"""
                    UPDATE {tabela} SET
                        qtd_venda = %s
                    WHERE data = %s AND cod_empresa = %s AND codigo = %s
                """, (qtd_venda, data, cod_empresa, codigo))
                atualizados += 1
            else:
                cursor.execute(f"""
                    INSERT INTO {tabela}
                    (data, cod_empresa, codigo, qtd_venda, dia_semana, dia_mes,
                     semana_ano, mes, ano, fim_semana)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (data, cod_empresa, codigo, qtd_venda, dia_semana, dia_mes,
                      semana_ano, mes, ano_data, fim_semana))
                inseridos += 1

            if total % 10000 == 0:
                print(f"  Processados: {total}")
                conn.commit()

    conn.commit()
    cursor.close()
    conn.close()

    print(f"  Total: {total} | Inseridos: {inseridos} | Atualizados: {atualizados}")
    return total

def importar_demanda_historica():
    """Importa toda demanda historica Soprano"""
    print("\n" + "="*60)
    print("IMPORTANDO DEMANDA HISTORICA SOPRANO")
    print("="*60)

    total = 0

    # Anos historicos
    arquivos = [
        ("demanda_Soprano_2023.csv", "Demanda 2023", 2023),
        ("demanda_Soprano_2024.csv", "Demanda 2024", 2024),
        ("demanda_Soprano_2025.csv", "Demanda 2025", 2025),
    ]

    for arquivo, desc, ano in arquivos:
        total += importar_demanda(arquivo, desc, ano)

    print(f"\nTotal demanda historica: {total}")
    return total

def importar_demanda_recente():
    """Importa demanda recente Soprano (2026)"""
    print("\n" + "="*60)
    print("IMPORTANDO DEMANDA RECENTE SOPRANO (2026)")
    print("="*60)

    return importar_demanda("demanda_Soprano_01-01_a_10-02-2026.csv", "Demanda Jan-Fev 2026", 2026)

def main():
    print("="*60)
    print("IMPORTACAO DE DADOS SOPRANO")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 1. Fornecedores
    importar_fornecedores()

    # 2. Produtos
    importar_produtos()

    # 3. Estoque
    importar_estoque()

    # 4. Demanda historica
    importar_demanda_historica()

    # 5. Demanda recente
    importar_demanda_recente()

    print("\n" + "="*60)
    print("IMPORTACAO CONCLUIDA!")
    print("="*60)

if __name__ == "__main__":
    main()
