# -*- coding: utf-8 -*-
"""
Teste do adaptador de dados
"""

from core.data_adapter import DataAdapter, criar_adapter_do_arquivo
import pandas as pd
import sys

# Configurar encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("TESTE: Data Adapter - Conversao de Dados Diarios para Formato Legado")
print("=" * 80)

# Teste 1: Criar adapter e carregar dados
print("\n[1] Criando adapter e carregando dados...")
adapter = DataAdapter('demanda_01-12-2025.xlsx')

valido, mensagens = adapter.carregar_e_validar()
print(f"\nValidacao: {'PASSOU' if valido else 'FALHOU'}")
print(f"Mensagens ({len(mensagens)}):")
for msg in mensagens[:5]:  # Mostrar apenas primeiras 5
    print(f"  - {msg}")

# Teste 2: Obter metadados
print("\n" + "=" * 80)
print("[2] Metadados")
print("=" * 80)

metadados = adapter.get_metadados()
print(f"\nPeriodo: {metadados['periodo_inicial'].date()} a {metadados['periodo_final'].date()}")
print(f"Total de dias: {metadados['total_dias']}")
print(f"Filiais: {len(metadados['filiais'])}")
print(f"Produtos: {len(metadados['produtos'])}")

# Teste 3: Converter para formato legado (SEMANAL)
print("\n" + "=" * 80)
print("[3] Conversao para Formato Legado - SEMANAL")
print("=" * 80)

df_semanal = adapter.converter_para_formato_legado(granularidade='semanal')
print(f"\n[OK] Dados convertidos: {len(df_semanal)} registros")
print(f"\nColunas: {df_semanal.columns.tolist()}")
print(f"\nPrimeiras 10 linhas:")
print(df_semanal.head(10))

print(f"\nEstatisticas:")
print(f"  - Lojas unicas: {df_semanal['Loja'].nunique()}")
print(f"  - SKUs unicos: {df_semanal['SKU'].nunique()}")
print(f"  - Periodos unicos: {df_semanal['Mes'].nunique()}")
print(f"  - Total de vendas: {df_semanal['Vendas'].sum()}")
print(f"  - Media de vendas: {df_semanal['Vendas'].mean():.2f}")

# Teste 4: Converter para formato legado (MENSAL)
print("\n" + "=" * 80)
print("[4] Conversao para Formato Legado - MENSAL")
print("=" * 80)

df_mensal = adapter.converter_para_formato_legado(granularidade='mensal')
print(f"\n[OK] Dados convertidos: {len(df_mensal)} registros")
print(f"\nPrimeiras 10 linhas:")
print(df_mensal.head(10))

print(f"\nEstatisticas:")
print(f"  - Lojas unicas: {df_mensal['Loja'].nunique()}")
print(f"  - SKUs unicos: {df_mensal['SKU'].nunique()}")
print(f"  - Periodos unicos: {df_mensal['Mes'].nunique()}")
print(f"  - Total de vendas: {df_mensal['Vendas'].sum()}")

# Teste 5: Filtrar por filial especifica
print("\n" + "=" * 80)
print("[5] Filtro por Filial Especifica")
print("=" * 80)

filial_teste = metadados['filiais'][0]
df_filtrado = adapter.converter_para_formato_legado(
    granularidade='semanal',
    filiais=[filial_teste]
)
print(f"\nFilial: {filial_teste}")
print(f"Registros retornados: {len(df_filtrado)}")
print(f"Lojas no resultado: {df_filtrado['Loja'].unique().tolist()}")

# Teste 6: Listas para interface
print("\n" + "=" * 80)
print("[6] Listas para Interface (Select/Dropdown)")
print("=" * 80)

filiais = adapter.get_lista_filiais()
produtos = adapter.get_lista_produtos()

print(f"\nFiliais disponiveis ({len(filiais)}):")
for f in filiais[:5]:
    print(f"  - {f}")

print(f"\nProdutos disponiveis ({len(produtos)} total, mostrando 5 primeiros):")
for p in produtos[:5]:
    print(f"  - {p}")

# Teste 7: Estatisticas
print("\n" + "=" * 80)
print("[7] Estatisticas dos Dados")
print("=" * 80)

stats = adapter.estatisticas_dados()
print(f"\nPeriodo:")
print(f"  - Inicio: {stats['periodo']['inicio'].date()}")
print(f"  - Fim: {stats['periodo']['fim'].date()}")
print(f"  - Total dias: {stats['periodo']['total_dias']}")

print(f"\nTotais:")
print(f"  - Filiais: {stats['totais']['filiais']}")
print(f"  - Produtos: {stats['totais']['produtos']}")
print(f"  - Registros: {stats['totais']['registros']}")
print(f"  - Vendas totais: {stats['totais']['vendas_totais']}")

print(f"\nVendas:")
print(f"  - Dias com venda: {stats['vendas']['dias_com_venda']}")
print(f"  - Taxa de venda: {stats['vendas']['taxa_venda']}%")
print(f"  - Media diaria: {stats['vendas']['media_diaria']}")

print(f"\nTop 5 Filiais (por volume):")
top_filiais = sorted(stats['top_filiais'].items(), key=lambda x: x[1], reverse=True)[:5]
for filial, vendas in top_filiais:
    print(f"  - Filial {filial}: {vendas} unidades")

print(f"\nTop 5 Produtos (por volume):")
top_prods = list(stats['top_produtos'].items())[:5]
for produto, vendas in top_prods:
    print(f"  - Produto {produto}: {vendas} unidades")

# Teste 8: Funcao auxiliar
print("\n" + "=" * 80)
print("[8] Funcao Auxiliar criar_adapter_do_arquivo()")
print("=" * 80)

df_conv, meta = criar_adapter_do_arquivo(
    'demanda_01-12-2025.xlsx',
    granularidade='semanal',
    filiais=[1, 2, 3]  # Apenas 3 primeiras filiais
)

print(f"\n[OK] Conversao via funcao auxiliar")
print(f"Registros: {len(df_conv)}")
print(f"Filiais no resultado: {df_conv['Loja'].unique().tolist()}")
print(f"\nMetadados disponiveis:")
print(f"  - dados: {len(meta['dados'])} chaves")
print(f"  - filiais_disponiveis: {len(meta['filiais_disponiveis'])} filiais")
print(f"  - produtos_disponiveis: {len(meta['produtos_disponiveis'])} produtos")
print(f"  - mensagens_validacao: {len(meta['mensagens_validacao'])} mensagens")

print("\n" + "=" * 80)
print("[OK] TODOS OS TESTES CONCLUIDOS!")
print("=" * 80)
