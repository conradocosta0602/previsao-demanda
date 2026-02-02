"""
Script para gerar arquivo de dados de teste
Cria dados simulados de vendas para 3 SKUs, 9 lojas e 18 meses
"""

import pandas as pd
import numpy as np
from datetime import datetime
import calendar

# Configurações
np.random.seed(42)

LOJAS = [f'L0{i}' for i in range(1, 10)]  # L01 a L09
SKUS = ['PROD_001', 'PROD_002', 'PROD_003']
MESES = pd.date_range(start='2023-01', end='2024-06', freq='MS')

# Função para gerar dados
def gerar_dados():
    dados = []

    for sku in SKUS:
        for loja in LOJAS:
            # Definir características por SKU
            if sku == 'PROD_001':
                # Demanda estável com pequenas rupturas
                base = 100 + np.random.randint(-20, 20)
                tendencia = 0
                sazonalidade = [1.0] * 12
                ruptura_prob = 0.15
                origem = 'CD'

            elif sku == 'PROD_002':
                # Demanda com tendência crescente
                base = 50 + np.random.randint(-10, 10)
                tendencia = 3  # Crescimento mensal
                sazonalidade = [1.0] * 12
                ruptura_prob = 0.1
                # Metade das lojas recebe do CD, metade direto
                origem = 'CD' if loja in ['L01', 'L02', 'L03', 'L04', 'L05'] else 'DIRETO'

            else:  # PROD_003
                # Demanda intermitente
                base = 30 + np.random.randint(-10, 10)
                tendencia = 1
                # Sazonalidade com pico no final do ano
                sazonalidade = [0.8, 0.7, 0.8, 0.9, 0.9, 1.0, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8]
                ruptura_prob = 0.25
                origem = 'DIRETO' if loja in ['L07', 'L08', 'L09'] else 'CD'

            for i, mes in enumerate(MESES):
                dias_mes = calendar.monthrange(mes.year, mes.month)[1]

                # Calcular vendas base
                vendas_base = base + (tendencia * i)

                # Aplicar sazonalidade
                mes_idx = mes.month - 1
                vendas_base *= sazonalidade[mes_idx]

                # Adicionar ruído
                vendas = vendas_base + np.random.normal(0, vendas_base * 0.15)
                vendas = max(0, int(vendas))

                # Simular ruptura
                if np.random.random() < ruptura_prob:
                    # Ruptura parcial ou total
                    if np.random.random() < 0.3:
                        # Ruptura total
                        dias_estoque = 0
                        vendas = 0
                    else:
                        # Ruptura parcial
                        dias_estoque = np.random.randint(10, dias_mes - 5)
                        # Ajustar vendas proporcionalmente
                        vendas = int(vendas * (dias_estoque / dias_mes))
                else:
                    dias_estoque = dias_mes

                dados.append({
                    'Mes': mes.strftime('%Y-%m'),
                    'Loja': loja,
                    'SKU': sku,
                    'Vendas': vendas,
                    'Dias_Com_Estoque': dias_estoque,
                    'Origem': origem
                })

    return pd.DataFrame(dados)


def gerar_instrucoes():
    """Gera DataFrame com instruções"""
    instrucoes = [
        ['INSTRUCOES DE USO', ''],
        ['', ''],
        ['1. Estrutura do Arquivo', ''],
        ['   - Mes: Formato YYYY-MM (ex: 2024-01)', ''],
        ['   - Loja: L01 a L09', ''],
        ['   - SKU: Identificador do produto', ''],
        ['   - Vendas: Quantidade vendida no mes', ''],
        ['   - Dias_Com_Estoque: Dias que o produto esteve disponivel', ''],
        ['   - Origem: CD ou DIRETO', ''],
        ['', ''],
        ['2. Cenarios nos Dados de Teste', ''],
        ['   - PROD_001: Demanda estavel, todas lojas via CD', ''],
        ['   - PROD_002: Tendencia crescente, mix CD/DIRETO', ''],
        ['   - PROD_003: Demanda sazonal e intermitente', ''],
        ['', ''],
        ['3. Como Usar', ''],
        ['   a) Execute: python app.py', ''],
        ['   b) Acesse: http://localhost:5000', ''],
        ['   c) Faca upload deste arquivo', ''],
        ['   d) Clique em Processar Previsao', ''],
        ['   e) Baixe o Excel com os resultados', ''],
    ]
    return pd.DataFrame(instrucoes, columns=['Instrucao', 'Detalhe'])


if __name__ == '__main__':
    print("Gerando dados de teste...")

    # Gerar dados
    df_dados = gerar_dados()
    df_instrucoes = gerar_instrucoes()

    # Salvar Excel
    caminho = 'tests/dados_teste.xlsx'

    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df_dados.to_excel(writer, sheet_name='DADOS', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"Arquivo gerado: {caminho}")
    print(f"Total de registros: {len(df_dados)}")
    print(f"SKUs: {df_dados['SKU'].unique().tolist()}")
    print(f"Lojas: {df_dados['Loja'].unique().tolist()}")
    print(f"Periodo: {df_dados['Mes'].min()} a {df_dados['Mes'].max()}")
