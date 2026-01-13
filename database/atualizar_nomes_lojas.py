"""
Script para atualizar os nomes das lojas no banco de dados
"""
import psycopg

DB_CONFIG = {
    'host': 'localhost',
    'dbname': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

# Mapeamento: cod_empresa -> nome_loja
# Inclui ambos os formatos (com e sem zero) para garantir match
LOJAS = {
    '1': 'Loja 01 - Garanhuns',
    '01': 'Loja 01 - Garanhuns',
    '2': 'Loja 02 - Imbiribeira',
    '02': 'Loja 02 - Imbiribeira',
    '3': 'Loja 03 - Paralela',
    '03': 'Loja 03 - Paralela',
    '4': 'Loja 04 - Tamarineira',
    '04': 'Loja 04 - Tamarineira',
    '5': 'Loja 05 - Aracaju',
    '05': 'Loja 05 - Aracaju',
    '6': 'Loja 06 - Joao Pessoa',
    '06': 'Loja 06 - Joao Pessoa',
    '7': 'Loja 07 - Ponta Negra',
    '07': 'Loja 07 - Ponta Negra',
    '8': 'Loja 08 - Caruaru',
    '08': 'Loja 08 - Caruaru',
    '9': 'Loja 09 - Barris',
    '09': 'Loja 09 - Barris',
    '80': 'Loja 80 - MDC',
    '81': 'Loja 81 - OBC',
    '82': 'Loja 82 - OLSAL',
    '83': 'Loja 83 - TBD',
    '92': 'Loja 92 - CD CABO',
    '93': 'Loja 93 - CD Alhandra',
    '94': 'Loja 94 - CD Lauro de Freitas',
}

def atualizar_nomes_lojas():
    """Atualiza os nomes das lojas na tabela cadastro_lojas"""
    print("Conectando ao banco de dados...")

    try:
        conn = psycopg.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Primeiro, verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'cadastro_lojas'
            )
        """)
        tabela_existe = cursor.fetchone()[0]

        if not tabela_existe:
            print("Tabela cadastro_lojas nao existe. Criando...")
            cursor.execute("""
                CREATE TABLE cadastro_lojas (
                    cod_empresa VARCHAR(10) PRIMARY KEY,
                    nome_loja VARCHAR(100) NOT NULL,
                    regiao VARCHAR(50),
                    tipo VARCHAR(50),
                    ativo BOOLEAN DEFAULT TRUE
                )
            """)
            conn.commit()
            print("Tabela criada com sucesso!")

        # Verificar lojas existentes
        cursor.execute("SELECT cod_empresa, nome_loja FROM cadastro_lojas ORDER BY cod_empresa")
        lojas_existentes = cursor.fetchall()

        print("\nLojas existentes no banco:")
        if lojas_existentes:
            for cod, nome in lojas_existentes:
                print(f"  {cod}: {nome}")
        else:
            print("  (nenhuma loja cadastrada)")

        # Inserir ou atualizar lojas
        print("\nAtualizando nomes das lojas...")

        for cod_empresa, nome_loja in LOJAS.items():
            # Tentar atualizar primeiro
            cursor.execute("""
                UPDATE cadastro_lojas
                SET nome_loja = %s
                WHERE cod_empresa = %s
            """, (nome_loja, cod_empresa))

            if cursor.rowcount == 0:
                # Se nao atualizou, inserir
                # Determinar tipo e regiao baseado no codigo
                if cod_empresa.startswith('9'):
                    tipo = 'CD'
                    regiao = 'Centro de Distribuicao'
                elif cod_empresa.startswith('8'):
                    tipo = 'Operacao'
                    regiao = 'Operacoes Especiais'
                else:
                    tipo = 'Loja'
                    # Determinar regiao pela loja
                    if cod_empresa in ['01', '02', '04', '08']:
                        regiao = 'Pernambuco'
                    elif cod_empresa == '03':
                        regiao = 'Bahia'
                    elif cod_empresa == '05':
                        regiao = 'Sergipe'
                    elif cod_empresa == '06':
                        regiao = 'Paraiba'
                    elif cod_empresa == '07':
                        regiao = 'Rio Grande do Norte'
                    elif cod_empresa == '09':
                        regiao = 'Bahia'
                    else:
                        regiao = 'Outras'

                cursor.execute("""
                    INSERT INTO cadastro_lojas (cod_empresa, nome_loja, regiao, tipo, ativo)
                    VALUES (%s, %s, %s, %s, TRUE)
                """, (cod_empresa, nome_loja, regiao, tipo))
                print(f"  Inserido: {cod_empresa} -> {nome_loja}")
            else:
                print(f"  Atualizado: {cod_empresa} -> {nome_loja}")

        conn.commit()

        # Mostrar resultado final
        print("\n" + "="*60)
        print("Lojas apos atualizacao:")
        print("="*60)
        cursor.execute("SELECT cod_empresa, nome_loja, regiao, tipo FROM cadastro_lojas ORDER BY cod_empresa")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} ({row[2]} - {row[3]})")

        cursor.close()
        conn.close()

        print("\nNomes das lojas atualizados com sucesso!")

    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    atualizar_nomes_lojas()
