"""
Analise dos métodos utilizados no processamento real
"""
from app import processar_previsao
import pandas as pd

print('='*80)
print('ANALISE: METODOS UTILIZADOS NO PROCESSAMENTO')
print('='*80)

resultado = processar_previsao('dados_teste_integrado.xlsx', meses_previsao=12)

# Carregar o Excel gerado
import glob
import os

# Pegar o arquivo mais recente
arquivos = glob.glob('outputs/previsao_demanda_*.xlsx')
if arquivos:
    arquivo_mais_recente = max(arquivos, key=os.path.getctime)
    print(f'\nArquivo gerado: {os.path.basename(arquivo_mais_recente)}')

    # Ler aba de métodos
    df_metodos = pd.read_excel(arquivo_mais_recente, sheet_name='METODOS_UTILIZADOS')

    print(f'\n{"="*80}')
    print('CONTAGEM DE METODOS:')
    print('='*80)

    contagem = df_metodos['Metodo'].value_counts()
    total = len(df_metodos)

    for metodo, count in contagem.items():
        pct = (count / total) * 100
        print(f'{metodo:<30} {count:>5} ({pct:>5.1f}%)')

    print(f'{"-"*80}')
    print(f'{"TOTAL":<30} {total:>5} (100.0%)')

    # Verificar quantos tem sazonalidade detectada
    df_caract = pd.read_excel(arquivo_mais_recente, sheet_name='CARACTERISTICAS_DEMANDA')

    print(f'\n{"="*80}')
    print('DETECCAO DE SAZONALIDADE:')
    print('='*80)

    saz = df_caract['Sazonalidade'].value_counts()
    for valor, count in saz.items():
        pct = (count / total) * 100
        print(f'{valor:<10} {count:>5} ({pct:>5.1f}%)')

    # Análise cruzada: Método vs Sazonalidade
    print(f'\n{"="*80}')
    print('METODO vs SAZONALIDADE DETECTADA:')
    print('='*80)

    # Juntar as duas tabelas
    df_merged = df_metodos.merge(df_caract, on=['Local', 'SKU'])

    # Cross-tab
    cross = pd.crosstab(df_merged['Metodo'], df_merged['Sazonalidade'])
    print(cross)

    print(f'\n{"="*80}')
    print('CONCLUSAO:')
    print('='*80)

    decomp_count = contagem.get('Decomposição Sazonal', 0) + contagem.get('Decomposicao Sazonal', 0)
    if decomp_count < total * 0.5:
        print(f'[PROBLEMA] Apenas {decomp_count} de {total} series usam Decomposicao Sazonal')
        print('Isso explica porque a media YoY ainda esta alta!')
        print('\nPossivel causa:')
        print('  - Series individuais (SKU+Loja) tem poucos dados (<18 meses)')
        print('  - Deteccao de sazonalidade individual e fraca')
        print('  - Cada serie usa metodo diferente')
    else:
        print(f'[INFO] {decomp_count} de {total} series usam Decomposicao Sazonal')

print(f'\n{"="*80}')
