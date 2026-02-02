"""
Teste do Seletor ML de Métodos
"""
import pandas as pd
import numpy as np
from core.ml_selector import MLMethodSelector

print("=" * 70)
print("TESTE: Seletor ML de Métodos de Previsão")
print("=" * 70)

# 1. Criar dados sintéticos para teste
print("\n1. Criando dados sintéticos de teste...")

np.random.seed(42)
dados_teste = []

# Série 1: Tendência crescente (deve escolher Holt-Winters ou Exponencial)
for i in range(24):
    dados_teste.append({
        'SKU': 'PROD001',
        'Loja': 'L001',
        'Mes': pd.Timestamp('2024-01-01') + pd.DateOffset(months=i),
        'Vendas': 100 + i * 5 + np.random.normal(0, 10)
    })

# Série 2: Estável (deve escolher Média Móvel)
for i in range(24):
    dados_teste.append({
        'SKU': 'PROD002',
        'Loja': 'L001',
        'Mes': pd.Timestamp('2024-01-01') + pd.DateOffset(months=i),
        'Vendas': 200 + np.random.normal(0, 15)
    })

# Série 3: Sazonal (deve escolher Holt-Winters)
for i in range(24):
    sazonalidade = 50 * np.sin(2 * np.pi * i / 12)
    dados_teste.append({
        'SKU': 'PROD003',
        'Loja': 'L001',
        'Mes': pd.Timestamp('2024-01-01') + pd.DateOffset(months=i),
        'Vendas': 150 + sazonalidade + np.random.normal(0, 10)
    })

# Série 4: Volátil/Intermitente (deve escolher Média Móvel)
for i in range(24):
    dados_teste.append({
        'SKU': 'PROD004',
        'Loja': 'L001',
        'Mes': pd.Timestamp('2024-01-01') + pd.DateOffset(months=i),
        'Vendas': np.random.choice([0, 0, 50, 100, 200])
    })

df_teste = pd.DataFrame(dados_teste)
print(f"   Criadas {len(df_teste)} observações")
print(f"   SKUs: {df_teste['SKU'].nunique()}")
print(f"   Lojas: {df_teste['Loja'].nunique()}")

# 2. Criar e treinar seletor ML
print("\n2. Criando e treinando seletor ML...")
ml_selector = MLMethodSelector()

stats = ml_selector.treinar_com_historico(df_teste)

if stats['sucesso']:
    print(f"   [OK] Modelo treinado!")
    print(f"   Séries válidas: {stats['series_validas']}")
    print(f"   Acurácia: {stats['acuracia']:.1%}")

    print("\n   Top 3 características mais importantes:")
    importancias = sorted(stats['importancia_features'].items(),
                         key=lambda x: x[1], reverse=True)
    for feature, importancia in importancias[:3]:
        print(f"     - {feature}: {importancia:.3f}")
else:
    print(f"   [ERRO] Treinamento falhou")
    print(f"   Séries válidas: {stats['series_validas']}")
    exit(1)

# 3. Testar predições
print("\n3. Testando predições para cada série...")

for sku in df_teste['SKU'].unique():
    serie = df_teste[df_teste['SKU'] == sku].sort_values('Mes')['Vendas']

    metodo, confianca = ml_selector.selecionar_metodo(serie)

    print(f"\n   {sku}:")
    print(f"     Método selecionado: {metodo}")
    print(f"     Confiança: {confianca:.1%}")

    # Características
    caract = ml_selector.extrair_caracteristicas(serie)
    print(f"     Média: {caract['media']:.1f}")
    print(f"     CV: {caract['cv']:.2f}")
    print(f"     Tendência: {caract['tendencia']:.4f}")
    print(f"     Sazonalidade: {caract['sazonalidade']:.2f}")

# 4. Seleção em massa
print("\n4. Testando seleção em massa...")
resultados = ml_selector.selecionar_metodos_em_massa(df_teste)

print("\n   Resumo dos métodos selecionados:")
print(resultados.to_string(index=False))

print("\n   Distribuição de métodos:")
distribuicao = resultados['Metodo_Sugerido'].value_counts()
for metodo, count in distribuicao.items():
    print(f"     {metodo}: {count} ({count/len(resultados)*100:.1f}%)")

print("\n   Confiança média: {:.1%}".format(resultados['Confianca'].mean()))

print("\n" + "=" * 70)
print("TESTE CONCLUÍDO COM SUCESSO!")
print("=" * 70)
