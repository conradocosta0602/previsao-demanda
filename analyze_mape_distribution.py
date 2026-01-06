# -*- coding: utf-8 -*-
"""
Análise detalhada da distribuição de MAPE
"""

import pandas as pd
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

arquivo = './outputs/previsao_demanda_20260106_125610.xlsx'

print("=" * 80)
print("ANÁLISE DETALHADA: Distribuição de MAPE")
print("=" * 80)

try:
    df = pd.read_excel(arquivo, sheet_name='PREVISOES')

    print(f"\nTotal de registros: {len(df)}")

    if 'MAPE' in df.columns:
        mapes = df['MAPE'].dropna()

        print(f"\n--- ESTATÍSTICAS GERAIS ---")
        print(f"Total de MAPEs calculados: {len(mapes)}")
        print(f"Mínimo: {mapes.min():.2f}%")
        print(f"Máximo: {mapes.max():.2f}%")
        print(f"Média: {mapes.mean():.2f}%")
        print(f"Mediana: {mapes.median():.2f}%")

        # Contar MAPEs = 999.9 (não calculáveis)
        nao_calculaveis = (mapes == 999.9).sum()
        calculaveis = len(mapes) - nao_calculaveis

        print(f"\n--- DISTRIBUIÇÃO ---")
        print(f"MAPEs válidos (< 999.9): {calculaveis} ({calculaveis/len(mapes)*100:.1f}%)")
        print(f"MAPEs não calculáveis (= 999.9): {nao_calculaveis} ({nao_calculaveis/len(mapes)*100:.1f}%)")

        # Analisar apenas MAPEs válidos
        if calculaveis > 0:
            mapes_validos = mapes[mapes < 999.9]

            print(f"\n--- MAPES VÁLIDOS (Excluindo 999.9) ---")
            print(f"Total: {len(mapes_validos)}")
            print(f"Mínimo: {mapes_validos.min():.2f}%")
            print(f"Máximo: {mapes_validos.max():.2f}%")
            print(f"Média: {mapes_validos.mean():.2f}%")
            print(f"Mediana: {mapes_validos.median():.2f}%")

            # Distribuição por faixas
            print(f"\n--- DISTRIBUIÇÃO POR FAIXAS (MAPEs Válidos) ---")
            faixas = [
                (0, 10, "Excelente"),
                (10, 20, "Boa"),
                (20, 30, "Aceitável"),
                (30, 50, "Fraca"),
                (50, 100, "Muito Fraca"),
                (100, 999, "Crítica")
            ]

            for min_val, max_val, categoria in faixas:
                count = ((mapes_validos >= min_val) & (mapes_validos < max_val)).sum()
                pct = (count / len(mapes_validos)) * 100
                print(f"{categoria:15} ({min_val:3d}-{max_val:3d}%): {count:4d} SKUs ({pct:5.1f}%)")

            # Mostrar exemplos de MAPEs válidos
            print(f"\n--- EXEMPLOS DE MAPES VÁLIDOS ---")
            print(f"10 menores MAPEs:")
            melhores = df[df['MAPE'] < 999.9].nsmallest(10, 'MAPE')
            for i, row in melhores.iterrows():
                loja = row.get('Loja', 'N/A')
                sku = row.get('SKU', 'N/A')
                mape = row.get('MAPE', 0)
                metodo = row.get('Método Selecionado', 'N/A')
                print(f"  {loja} | SKU {sku} | MAPE={mape:.2f}% | Método={metodo}")

            print(f"\n10 maiores MAPEs válidos (excluindo 999.9):")
            piores = df[(df['MAPE'] < 999.9)].nlargest(10, 'MAPE')
            for i, row in piores.iterrows():
                loja = row.get('Loja', 'N/A')
                sku = row.get('SKU', 'N/A')
                mape = row.get('MAPE', 0)
                metodo = row.get('Método Selecionado', 'N/A')
                print(f"  {loja} | SKU {sku} | MAPE={mape:.2f}% | Método={metodo}")

        # Analisar os que não puderam ser calculados
        print(f"\n--- ANÁLISE DOS MAPES NÃO CALCULÁVEIS (999.9) ---")
        df_nao_calc = df[df['MAPE'] == 999.9]

        if len(df_nao_calc) > 0:
            print(f"Total: {len(df_nao_calc)}")
            print(f"\nPossíveis causas:")
            print(f"  1. Vendas muito esparsas (< 2 unidades/semana na maioria dos períodos)")
            print(f"  2. Produto novo sem histórico suficiente")
            print(f"  3. Produto sazonal com vendas concentradas")

            # Verificar se há colunas de demanda histórica
            if 'Demanda_Mes_-1' in df.columns:
                print(f"\nExemplos de SKUs não calculáveis:")
                for i, row in df_nao_calc.head(5).iterrows():
                    loja = row.get('Loja', 'N/A')
                    sku = row.get('SKU', 'N/A')
                    hist_cols = [col for col in df.columns if 'Demanda_Mes_' in col]
                    historico = [row[col] for col in hist_cols if col in row]
                    total_historico = sum([h for h in historico if pd.notna(h)])
                    print(f"  {loja} | SKU {sku} | Vendas históricas: {total_historico:.1f}")

    else:
        print("[AVISO] Coluna MAPE não encontrada")

except Exception as e:
    print(f"\n[ERRO] {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("CONCLUSÃO")
print("=" * 80)
print("""
O threshold de 2.0 está funcionando, mas muitos SKUs têm vendas tão esparsas
que mesmo com esse threshold não há períodos suficientes para calcular MAPE.

MAPE = 999.9 indica que o SKU não teve períodos suficientes com vendas >= 2.0
para calcular a métrica de forma confiável.

Isto é ESPERADO em varejo com muitos produtos de cauda longa (baixo giro).
""")
print("=" * 80)
