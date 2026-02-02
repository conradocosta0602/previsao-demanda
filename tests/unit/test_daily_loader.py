# -*- coding: utf-8 -*-
"""
Script de teste para o novo modulo de carregamento de dados diarios
"""

from core.daily_data_loader import DailyDataLoader
import pandas as pd
import sys

# Configurar encoding para UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Teste 1: Carregar dados
print("=" * 80)
print("TESTE 1: Carregando dados diarios")
print("=" * 80)

loader = DailyDataLoader('demanda_01-12-2025.xlsx')
df_diario = loader.carregar()

print(f"\n[OK] Dados carregados: {len(df_diario)} registros")
print(f"\nPrimeiras linhas:")
print(df_diario.head(10))

# Teste 2: Validar dados
print("\n" + "=" * 80)
print("TESTE 2: Validando dados")
print("=" * 80)

valido, mensagens = loader.validar()
print(f"\nValidacao: {'PASSOU' if valido else 'FALHOU'}")
for msg in mensagens:
    print(f"  - {msg}")

# Teste 3: Metadados
print("\n" + "=" * 80)
print("TESTE 3: Metadados")
print("=" * 80)

metadados = loader.get_metadados()
print(f"\nFiliais: {metadados['filiais']}")
print(f"Total de produtos: {len(metadados['produtos'])}")
print(f"Periodo: {metadados['periodo_inicial'].date()} a {metadados['periodo_final'].date()}")
print(f"Total de dias: {metadados['total_dias']}")

# Teste 4: Agregacao semanal
print("\n" + "=" * 80)
print("TESTE 4: Agregacao Semanal")
print("=" * 80)

df_semanal = loader.agregar_semanal()
print(f"\n[OK] Dados agregados: {len(df_semanal)} semanas")
print(f"\nPrimeiras linhas:")
print(df_semanal.head(10))

print(f"\nEstatisticas semanais:")
print(f"  - Media de vendas por semana: {df_semanal['qtd_venda_semanal'].mean():.2f}")
print(f"  - Maximo semanal: {df_semanal['qtd_venda_semanal'].max()}")
print(f"  - Semanas com venda: {(df_semanal['qtd_venda_semanal'] > 0).sum()}")

# Teste 5: Agregacao mensal
print("\n" + "=" * 80)
print("TESTE 5: Agregacao Mensal")
print("=" * 80)

df_mensal = loader.agregar_mensal()
print(f"\n[OK] Dados agregados: {len(df_mensal)} meses")
print(f"\nPrimeiras linhas:")
print(df_mensal.head(10))

print(f"\nEstatisticas mensais:")
print(f"  - Media de vendas por mes: {df_mensal['qtd_venda_mensal'].mean():.2f}")
print(f"  - Maximo mensal: {df_mensal['qtd_venda_mensal'].max()}")

# Teste 6: Filtrar dados
print("\n" + "=" * 80)
print("TESTE 6: Filtragem de Dados")
print("=" * 80)

# Filtrar uma filial e um produto especifico
filial_teste = metadados['filiais'][0]
produto_teste = metadados['produtos'][0]

df_filtrado = loader.filtrar_dados(
    filiais=[filial_teste],
    produtos=[produto_teste]
)

print(f"\nFiltro aplicado:")
print(f"  - Filial: {filial_teste}")
print(f"  - Produto: {produto_teste}")
print(f"  - Registros retornados: {len(df_filtrado)}")
print(f"\nDados filtrados (primeiras 10 linhas):")
print(df_filtrado.head(10))

# Teste 7: Desagregacao
print("\n" + "=" * 80)
print("TESTE 7: Desagregacao Semanal -> Diaria (Proporcional)")
print("=" * 80)

# Usar primeiras 4 semanas para teste
df_teste_semanal = df_semanal.head(4).copy()
df_teste_semanal['previsao_semanal'] = df_teste_semanal['qtd_venda_semanal']  # Simular previsao

# Metodo proporcional (unico metodo disponivel)
df_diario_proporcional = loader.desagregar_previsao_semanal_para_diaria(df_teste_semanal)

print(f"\n[OK] Desagregacao Proporcional:")
print(f"  - {len(df_teste_semanal)} semanas -> {len(df_diario_proporcional)} dias")
print(f"  - Metodo: Baseado no padrao historico de cada dia da semana")
print(f"\nPrimeiras linhas:")
print(df_diario_proporcional.head(14))

# Mostrar proporcoes calculadas
print(f"\nProporcoes por dia da semana (exemplo):")
df_exemplo = df_diario_proporcional.head(7).copy()
df_exemplo['dia_semana'] = df_exemplo['data'].dt.day_name()
print(df_exemplo[['dia_semana', 'qtd_prevista_diaria']])

print("\n" + "=" * 80)
print("[OK] TODOS OS TESTES CONCLUIDOS COM SUCESSO!")
print("=" * 80)
