"""
Script para importar cadastro de produtos e fornecedores no banco de dados
"""
import pandas as pd
import psycopg

DB_CONFIG = {
    'host': 'localhost',
    'dbname': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

def criar_tabelas(cursor):
    """Cria as tabelas de cadastro se nao existirem"""

    # Tabela de categorias/linhas de produtos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadastro_categorias (
            codigo_linha VARCHAR(10) PRIMARY KEY,
            descricao_linha VARCHAR(200) NOT NULL,
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # Atualizar tabela de produtos para incluir mais campos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadastro_produtos_completo (
            cod_produto VARCHAR(20) PRIMARY KEY,
            descricao VARCHAR(300) NOT NULL,
            cnpj_fornecedor VARCHAR(20),
            nome_fornecedor VARCHAR(200),
            categoria VARCHAR(200),
            codigo_linha VARCHAR(10),
            descricao_linha VARCHAR(200),
            ativo BOOLEAN DEFAULT TRUE
        )
    """)

    # Dropar tabela antiga de fornecedores se existir com estrutura diferente
    cursor.execute("DROP TABLE IF EXISTS cadastro_fornecedores CASCADE")

    # Tabela de fornecedores com parametros logisticos
    cursor.execute("""
        CREATE TABLE cadastro_fornecedores (
            id SERIAL PRIMARY KEY,
            cnpj VARCHAR(20) NOT NULL,
            nome_fantasia VARCHAR(200) NOT NULL,
            cod_empresa VARCHAR(10),
            tipo_destino VARCHAR(20),
            lead_time_dias INTEGER,
            ciclo_pedido_dias INTEGER,
            faturamento_minimo DECIMAL(12,2),
            ativo BOOLEAN DEFAULT TRUE,
            UNIQUE(cnpj, cod_empresa)
        )
    """)

    print("Tabelas criadas/verificadas com sucesso!")

def importar_produtos(cursor, arquivo_produtos):
    """Importa cadastro de produtos"""
    print(f"\nImportando produtos de: {arquivo_produtos}")

    df = pd.read_excel(arquivo_produtos)

    # Renomear colunas para padronizar
    df = df.rename(columns={
        'CODIGO': 'cod_produto',
        'DESCRICAO': 'descricao',
        'FANTAS': 'nome_fornecedor',
        'CNPJ': 'cnpj_fornecedor',
        'DESCR_LINHA1': 'categoria',
        'LINHA3': 'codigo_linha',
        'DESCR_LINHA3': 'descricao_linha'
    })

    # Remover coluna sem nome (indice)
    if '   ' in df.columns:
        df = df.drop(columns=['   '])

    # Converter CNPJ para string com zeros a esquerda
    df['cnpj_fornecedor'] = df['cnpj_fornecedor'].astype(str).str.zfill(14)
    df['cod_produto'] = df['cod_produto'].astype(str)

    # Importar categorias unicas primeiro
    categorias = df[['codigo_linha', 'descricao_linha']].drop_duplicates()
    categorias = categorias.dropna(subset=['codigo_linha'])

    print(f"  Categorias encontradas: {len(categorias)}")
    for _, row in categorias.iterrows():
        cursor.execute("""
            INSERT INTO cadastro_categorias (codigo_linha, descricao_linha, ativo)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (codigo_linha) DO UPDATE SET descricao_linha = EXCLUDED.descricao_linha
        """, (row['codigo_linha'], row['descricao_linha']))

    # Importar produtos
    print(f"  Produtos a importar: {len(df)}")
    importados = 0
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO cadastro_produtos_completo
                (cod_produto, descricao, cnpj_fornecedor, nome_fornecedor, categoria, codigo_linha, descricao_linha, ativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (cod_produto) DO UPDATE SET
                    descricao = EXCLUDED.descricao,
                    cnpj_fornecedor = EXCLUDED.cnpj_fornecedor,
                    nome_fornecedor = EXCLUDED.nome_fornecedor,
                    categoria = EXCLUDED.categoria,
                    codigo_linha = EXCLUDED.codigo_linha,
                    descricao_linha = EXCLUDED.descricao_linha
            """, (
                row['cod_produto'],
                row['descricao'],
                row['cnpj_fornecedor'],
                row['nome_fornecedor'],
                row['categoria'],
                row['codigo_linha'],
                row['descricao_linha']
            ))
            importados += 1
        except Exception as e:
            print(f"  Erro ao importar produto {row['cod_produto']}: {e}")

    print(f"  Produtos importados: {importados}")

def importar_fornecedores(cursor, arquivo_fornecedores):
    """Importa cadastro de fornecedores"""
    print(f"\nImportando fornecedores de: {arquivo_fornecedores}")

    df = pd.read_excel(arquivo_fornecedores)

    # Renomear colunas
    df = df.rename(columns={
        'CNPJ': 'cnpj',
        'FANTAS': 'nome_fantasia',
        'COD_EMPRESA': 'cod_empresa',
        'TIPO_DESTINO': 'tipo_destino',
        'LEAD_TIME_DIAS': 'lead_time_dias',
        'CICLO_PEDIDO_DIAS': 'ciclo_pedido_dias',
        'FAT_MINIMO': 'faturamento_minimo'
    })

    # Remover coluna sem nome (indice)
    if '   ' in df.columns:
        df = df.drop(columns=['   '])

    # Converter CNPJ para string
    df['cnpj'] = df['cnpj'].astype(str).str.zfill(14)
    df['cod_empresa'] = df['cod_empresa'].astype(str)

    print(f"  Fornecedores a importar: {len(df)}")
    importados = 0

    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO cadastro_fornecedores
                (cnpj, nome_fantasia, cod_empresa, tipo_destino, lead_time_dias, ciclo_pedido_dias, faturamento_minimo, ativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (cnpj, cod_empresa) DO UPDATE SET
                    nome_fantasia = EXCLUDED.nome_fantasia,
                    tipo_destino = EXCLUDED.tipo_destino,
                    lead_time_dias = EXCLUDED.lead_time_dias,
                    ciclo_pedido_dias = EXCLUDED.ciclo_pedido_dias,
                    faturamento_minimo = EXCLUDED.faturamento_minimo
            """, (
                row['cnpj'],
                row['nome_fantasia'],
                row['cod_empresa'],
                row['tipo_destino'],
                row['lead_time_dias'] if pd.notna(row['lead_time_dias']) else None,
                row['ciclo_pedido_dias'] if pd.notna(row['ciclo_pedido_dias']) else None,
                row['faturamento_minimo'] if pd.notna(row['faturamento_minimo']) else None
            ))
            importados += 1
        except Exception as e:
            print(f"  Erro ao importar fornecedor {row['cnpj']}: {e}")

    print(f"  Fornecedores importados: {importados}")

def mostrar_resumo(cursor):
    """Mostra resumo dos dados importados"""
    print("\n" + "="*60)
    print("RESUMO DA IMPORTACAO")
    print("="*60)

    cursor.execute("SELECT COUNT(*) FROM cadastro_categorias")
    print(f"Categorias: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM cadastro_produtos_completo")
    print(f"Produtos: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(DISTINCT cnpj) FROM cadastro_fornecedores")
    print(f"Fornecedores unicos: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM cadastro_fornecedores")
    print(f"Registros fornecedor-loja: {cursor.fetchone()[0]}")

    print("\n--- Categorias cadastradas ---")
    cursor.execute("SELECT codigo_linha, descricao_linha FROM cadastro_categorias ORDER BY codigo_linha LIMIT 15")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    print("\n--- Fornecedores cadastrados ---")
    cursor.execute("SELECT DISTINCT nome_fantasia FROM cadastro_fornecedores ORDER BY nome_fantasia LIMIT 15")
    for row in cursor.fetchall():
        print(f"  {row[0]}")

def main():
    """Executa a importacao completa"""
    arquivo_produtos = r'C:\Users\valter.lino\Downloads\Cadastro de Produtos.xlsx'
    arquivo_fornecedores = r'C:\Users\valter.lino\Downloads\Cadastro de Fornecedores.xlsx'

    print("Conectando ao banco de dados...")

    try:
        conn = psycopg.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Criar tabelas
        criar_tabelas(cursor)
        conn.commit()

        # Importar dados
        importar_produtos(cursor, arquivo_produtos)
        conn.commit()

        importar_fornecedores(cursor, arquivo_fornecedores)
        conn.commit()

        # Mostrar resumo
        mostrar_resumo(cursor)

        cursor.close()
        conn.close()

        print("\nImportacao concluida com sucesso!")

    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
