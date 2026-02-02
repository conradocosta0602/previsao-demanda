import pandas as pd
import glob
import os

arquivos = glob.glob('outputs/previsao_demanda_*.xlsx')
arquivo = max(arquivos, key=os.path.getctime)
xls = pd.ExcelFile(arquivo)

print(f'Arquivo: {os.path.basename(arquivo)}')
print('\nAbas disponiveis:')
for sheet in xls.sheet_names:
    print(f'  - {sheet}')
