# -*- coding: utf-8 -*-
"""
Teste das novas funcionalidades de estoque e detecção de rupturas
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from core.daily_data_loader import DailyDataLoader

print("=" * 80)
print("TESTE: Funcionalidades de Estoque e Rupturas")
print("=" * 80)

# Testar com o arquivo que tem coluna estoque_diario
arquivo = 'demanda_01-01-2023'

print(f"\n[1] Carregando arquivo: {arquivo}")
print("-" * 80)

try:
    loader = DailyDataLoader(arquivo)
    df = loader.carregar()

    print(f"[OK] Arquivo carregado")
    print(f"  - Total de registros: {len(df):,}")
    print(f"  - Período: {loader.periodo_inicial.date()} a {loader.periodo_final.date()}")
    print(f"  - Filiais: {len(loader.filiais)}")
    print(f"  - Produtos: {len(loader.produtos)}")
    print(f"  - Tem coluna estoque: {loader.tem_estoque}")

    if loader.tem_estoque:
        registros_com_estoque = df['estoque_diario'].notna().sum()
        pct_preenchido = (registros_com_estoque / len(df)) * 100
        print(f"  - Registros com estoque: {registros_com_estoque:,} ({pct_preenchido:.1f}%)")

except Exception as e:
    print(f"[ERRO] {str(e)}")
    sys.exit(1)

# Teste 2: Validar dados
print(f"\n[2] Validando dados")
print("-" * 80)

valido, mensagens = loader.validar()

if valido:
    print("[OK] Dados válidos")
else:
    print("[ERRO] Dados inválidos")

for msg in mensagens[:10]:  # Mostrar primeiras 10 mensagens
    print(f"  {msg}")

# Teste 3: Detectar rupturas
if loader.tem_estoque:
    print(f"\n[3] Detectando rupturas")
    print("-" * 80)

    try:
        df_rupturas = loader.detectar_rupturas()

        print(f"[OK] Rupturas detectadas: {len(df_rupturas):,}")

        if len(df_rupturas) > 0:
            # Contar rupturas por filial
            rupturas_por_filial = df_rupturas.groupby('cod_empresa').size().sort_values(ascending=False)
            print(f"\nRupturas por filial (top 5):")
            for filial, qtd in rupturas_por_filial.head().items():
                print(f"  Filial {filial}: {qtd:,} rupturas")

            # Contar rupturas por produto
            rupturas_por_produto = df_rupturas.groupby('codigo').size().sort_values(ascending=False)
            print(f"\nRupturas por produto (top 5):")
            for produto, qtd in rupturas_por_produto.head().items():
                print(f"  Produto {produto}: {qtd:,} rupturas")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

# Teste 4: Calcular demanda perdida
if loader.tem_estoque:
    print(f"\n[4] Calculando demanda perdida")
    print("-" * 80)

    try:
        df_demanda_perdida = loader.calcular_demanda_perdida(janela_dias=7)

        print(f"[OK] Demanda perdida calculada")
        print(f"  - Rupturas com demanda estimada: {len(df_demanda_perdida):,}")

        if len(df_demanda_perdida) > 0:
            total_demanda_perdida = df_demanda_perdida['demanda_perdida_estimada'].sum()
            print(f"  - Total de demanda perdida: {total_demanda_perdida:,.1f} unidades")
            print(f"  - Média por ruptura: {df_demanda_perdida['demanda_perdida_estimada'].mean():.2f} unidades")

            # Mostrar as 5 maiores demandas perdidas
            top_perdas = df_demanda_perdida.nlargest(5, 'demanda_perdida_estimada')
            print(f"\nTop 5 maiores demandas perdidas:")
            for idx, row in top_perdas.iterrows():
                print(f"  Filial {row['cod_empresa']} | Produto {row['codigo']} | "
                      f"Data: {row['data'].date()} | Perdida: {row['demanda_perdida_estimada']:.1f} un")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

# Teste 5: Ajustar vendas com rupturas
if loader.tem_estoque:
    print(f"\n[5] Ajustando histórico de vendas")
    print("-" * 80)

    try:
        df_ajustado = loader.ajustar_vendas_com_rupturas()

        print(f"[OK] Vendas ajustadas")
        print(f"  - Total de registros: {len(df_ajustado):,}")

        # Comparar vendas originais vs ajustadas
        vendas_originais = df_ajustado['qtd_venda'].sum()
        vendas_ajustadas = df_ajustado['qtd_ajustada'].sum()
        diferenca = vendas_ajustadas - vendas_originais
        pct_aumento = (diferenca / vendas_originais * 100) if vendas_originais > 0 else 0

        print(f"  - Vendas originais: {vendas_originais:,.1f} unidades")
        print(f"  - Vendas ajustadas: {vendas_ajustadas:,.1f} unidades")
        print(f"  - Diferença (demanda perdida): {diferenca:,.1f} unidades ({pct_aumento:+.1f}%)")

        # Contar dias com ruptura
        dias_com_ruptura = df_ajustado['tem_ruptura'].sum()
        print(f"  - Dias com ruptura: {dias_com_ruptura:,}")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

# Teste 6: Calcular nível de serviço
if loader.tem_estoque:
    print(f"\n[6] Calculando nível de serviço")
    print("-" * 80)

    try:
        df_nivel_servico = loader.calcular_nivel_servico()

        print(f"[OK] Nível de serviço calculado")
        print(f"  - SKUs analisados: {len(df_nivel_servico)}")

        if len(df_nivel_servico) > 0:
            # Estatísticas gerais
            taxa_media = df_nivel_servico['taxa_disponibilidade'].mean()
            demanda_total = df_nivel_servico['demanda_total'].sum()
            demanda_perdida_total = df_nivel_servico['demanda_perdida'].sum()

            print(f"  - Taxa de disponibilidade média: {taxa_media:.1f}%")
            print(f"  - Demanda total realizada: {demanda_total:,.1f} unidades")
            print(f"  - Demanda perdida total: {demanda_perdida_total:,.1f} unidades")

            # Top 5 piores níveis de serviço
            piores = df_nivel_servico.nsmallest(5, 'taxa_disponibilidade')
            print(f"\nTop 5 piores níveis de serviço:")
            for idx, row in piores.iterrows():
                print(f"  Filial {row['cod_empresa']} | Produto {row['codigo']} | "
                      f"Disponibilidade: {row['taxa_disponibilidade']:.1f}% | "
                      f"Rupturas: {row['dias_em_ruptura']} dias | "
                      f"Demanda perdida: {row['demanda_perdida']:.1f} un")

            # Top 5 produtos com maior demanda perdida
            maiores_perdas = df_nivel_servico.nlargest(5, 'demanda_perdida')
            print(f"\nTop 5 produtos com maior demanda perdida:")
            for idx, row in maiores_perdas.iterrows():
                print(f"  Filial {row['cod_empresa']} | Produto {row['codigo']} | "
                      f"Perdida: {row['demanda_perdida']:.1f} un | "
                      f"Potencial: {row['demanda_potencial']:.1f} un")

    except Exception as e:
        print(f"[ERRO] {str(e)}")

print("\n" + "=" * 80)
print("[OK] TESTE CONCLUÍDO")
print("=" * 80)
print("""
RESUMO DAS FUNCIONALIDADES IMPLEMENTADAS:
1. Suporte a CSV e coluna estoque_diario
2. Detecção de rupturas (qtd_venda=0 E estoque=0)
3. Cálculo de demanda perdida (média móvel 7 dias)
4. Ajuste do histórico de vendas com demanda perdida
5. Cálculo de nível de serviço por SKU/Filial

Com essas funcionalidades, as previsões serão mais precisas ao considerar
a demanda real (incluindo períodos de ruptura).
""")
