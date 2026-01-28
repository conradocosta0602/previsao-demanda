# -*- coding: utf-8 -*-
"""Script para importar dados de demanda adicionais (Amanda e El_Forceline)"""
import sys
import os
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import get_db_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def importar_vendas(arquivo, mes_referencia):
    print('\n' + '='*60)
    print(f'IMPORTANDO VENDAS - {mes_referencia}')
    print('='*60)

    conn = get_db_connection()
    cursor = conn.cursor()
    inseridos = 0
    atualizados = 0
    erros = 0

    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
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
            except Exception as e:
                erros += 1
                if erros <= 5:
                    print(f'   Erro na linha: {e}')

    conn.commit()
    conn.close()
    print(f'   Inseridos: {inseridos:,}, Atualizados: {atualizados:,}, Erros: {erros}')
    return inseridos + atualizados


def main():
    print('='*60)
    print('IMPORTACAO DE DADOS DE DEMANDA ADICIONAIS')
    print('(Amanda e El_Forceline)')
    print('='*60)
    print(f'Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')

    # Lista de arquivos para importar
    arquivos_vendas = [
        ('demanda_Amanda_2023.csv', 'Amanda 2023'),
        ('demanda_Amanda_2024.csv', 'Amanda 2024'),
        ('demanda_Amanda_2025.csv', 'Amanda 2025'),
        ('demanda_El_Forceline_2023.csv', 'El_Forceline 2023'),
        ('demanda_El_Forceline_2024.csv', 'El_Forceline 2024'),
        ('demanda_El_Forceline_2025.csv', 'El_Forceline 2025'),
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
    for label, total in totais_vendas.items():
        print(f'   Vendas {label}: {total:,}')
    print('='*60)
    print('IMPORTACAO CONCLUIDA!')
    print('='*60)


if __name__ == '__main__':
    main()
