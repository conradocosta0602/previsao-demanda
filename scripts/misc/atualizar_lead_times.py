# -*- coding: utf-8 -*-
"""Script para atualizar lead times reais dos fornecedores por filial"""
import sys
import os
import pandas as pd
from datetime import datetime

# Adicionar diretorio ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar funcao de conexao do app
from app import get_db_connection

# Diretorio base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def formatar_cnpj(cnpj):
    """Formata CNPJ para 14 digitos com zeros a esquerda"""
    cnpj_str = str(cnpj).replace('.', '').replace('/', '').replace('-', '').strip()
    return cnpj_str.zfill(14)


def main():
    print('='*60)
    print('ATUALIZACAO DE LEAD TIMES REAIS')
    print('='*60)
    print(f'Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
    print()

    # Ler arquivo Excel
    arquivo = os.path.join(BASE_DIR, 'lead_time_dias (1).xlsx')
    df = pd.read_excel(arquivo)

    print(f'Fornecedores no arquivo: {len(df)}')
    print()

    # Colunas de lojas
    lojas = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '80', '92', '93', '94']

    conn = get_db_connection()
    cursor = conn.cursor()

    atualizados = 0
    inseridos = 0
    nao_encontrados = 0

    for idx, row in df.iterrows():
        cnpj_original = str(row['fornecedor'])
        cnpj = formatar_cnpj(cnpj_original)
        fantas = row['fantas']

        for loja in lojas:
            lead_time = row[loja]

            # Pular se nao tem lead time para esta loja
            if pd.isna(lead_time):
                continue

            lead_time = int(lead_time)

            # Verificar se fornecedor existe para esta loja
            cursor.execute("""
                SELECT id, lead_time_dias FROM cadastro_fornecedores
                WHERE cnpj = %s AND cod_empresa = %s
            """, (cnpj, loja))

            result = cursor.fetchone()

            if result:
                # Atualizar lead time
                cursor.execute("""
                    UPDATE cadastro_fornecedores
                    SET lead_time_dias = %s
                    WHERE cnpj = %s AND cod_empresa = %s
                """, (lead_time, cnpj, loja))
                atualizados += 1
            else:
                # Inserir novo registro
                cursor.execute("""
                    INSERT INTO cadastro_fornecedores
                    (cnpj, nome_fantasia, cod_empresa, lead_time_dias, ciclo_pedido_dias, ativo)
                    VALUES (%s, %s, %s, %s, 7, TRUE)
                """, (cnpj, fantas, loja, lead_time))
                inseridos += 1

        # Progresso a cada 100 fornecedores
        if (idx + 1) % 100 == 0:
            print(f'   Processados: {idx + 1} fornecedores...')
            conn.commit()

    conn.commit()
    conn.close()

    print()
    print('='*60)
    print('RESUMO DA ATUALIZACAO')
    print('='*60)
    print(f'   Fornecedores processados: {len(df)}')
    print(f'   Lead times atualizados: {atualizados}')
    print(f'   Novos registros inseridos: {inseridos}')
    print(f'   Total de alteracoes: {atualizados + inseridos}')
    print('='*60)
    print('ATUALIZACAO CONCLUIDA!')
    print('='*60)


if __name__ == '__main__':
    main()
