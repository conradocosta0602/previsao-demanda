# -*- coding: utf-8 -*-
"""
Script para verificar valores de MAPE no arquivo Excel gerado
"""

import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

arquivo = './outputs/previsao_demanda_20260106_125610.xlsx'

print("=" * 80)
print("VERIFICAÇÃO: MAPE no Arquivo Excel Gerado")
print("=" * 80)

try:
    # Tentar ler aba de resumo ou previsões
    xls = pd.ExcelFile(arquivo)

    print(f"\nArquivo: {arquivo}")
    print(f"Abas disponíveis: {xls.sheet_names}")

    # Procurar MAPE em cada aba
    for sheet_name in xls.sheet_names:
        print(f"\n--- Aba: {sheet_name} ---")

        df = pd.read_excel(arquivo, sheet_name=sheet_name)

        # Procurar colunas que contenham 'MAPE'
        mape_cols = [col for col in df.columns if 'MAPE' in str(col).upper()]

        if mape_cols:
            print(f"Colunas com MAPE encontradas: {mape_cols}")

            for col in mape_cols:
                valores = df[col].dropna()
                if len(valores) > 0:
                    print(f"\n  Coluna: {col}")
                    print(f"    Valores únicos: {valores.nunique()}")
                    print(f"    Mínimo: {valores.min():.2f}")
                    print(f"    Máximo: {valores.max():.2f}")
                    print(f"    Média: {valores.mean():.2f}")
                    print(f"    Mediana: {valores.median():.2f}")

                    # Mostrar alguns exemplos
                    print(f"\n    Primeiros 10 valores:")
                    for i, val in enumerate(valores.head(10)):
                        print(f"      {i+1}. {val:.2f}%")

        # Procurar células que contenham valores de MAPE
        # (caso esteja em formato diferente)
        for col in df.columns:
            if df[col].dtype in ['float64', 'int64']:
                # Verificar se há valores que parecem MAPE (0-999)
                valores_numericos = df[col].dropna()
                if len(valores_numericos) > 0:
                    if valores_numericos.max() > 1 and valores_numericos.max() < 1000:
                        # Pode ser MAPE
                        if any(keyword in str(col).upper() for keyword in ['ACURA', 'ERRO', 'METRIC']):
                            print(f"\n  Coluna suspeita: {col}")
                            print(f"    Min: {valores_numericos.min():.2f}, Max: {valores_numericos.max():.2f}")

except Exception as e:
    print(f"\n[ERRO] {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("[OK] Verificação concluída")
print("=" * 80)
