"""
Diagnóstico específico do arquivo do usuário
"""
import pandas as pd
import numpy as np
import sys
from core.demand_calculator import DemandCalculator
from core.seasonality_detector import detect_seasonality

# Aceitar arquivo via argumento ou usar padrão
if len(sys.argv) > 1:
    arquivo = sys.argv[1]
else:
    arquivo = 'dados_teste_integrado.xlsx'

print(f"\n[INFO] Carregando {arquivo}...")

# Carregar dados - tentar diferentes formatos de planilha
try:
    df = pd.read_excel(arquivo, sheet_name='HISTORICO_VENDAS')
    col_data = 'Data'
    col_quantidade = 'Quantidade'
except:
    df = pd.read_excel(arquivo)
    col_data = 'Mes'
    col_quantidade = 'Vendas'

print(f"[INFO] Formato detectado - Colunas: {df.columns.tolist()}")

# Listar SKUs disponíveis
skus = df['SKU'].unique()
print(f"\n[INFO] SKUs disponíveis no arquivo: {len(skus)}")
print("Primeiros 10:", skus[:10].tolist())

# Usar SKU do argumento ou primeira disponível
if len(sys.argv) > 2:
    sku = sys.argv[2]
else:
    sku = skus[0]

print(f"\n[INFO] Analisando SKU: {sku}")

# Filtrar dados da SKU - agregar por data se houver múltiplas lojas
df_sku = df[df['SKU'] == sku].copy()

# Se tem coluna Loja, agregar vendas por data
if 'Loja' in df_sku.columns:
    df_sku = df_sku.groupby(col_data, as_index=False).agg({col_quantidade: 'sum'})

df_sku = df_sku.sort_values(col_data)

vendas = df_sku[col_quantidade].tolist()
datas = df_sku[col_data].tolist()

print("\n" + "="*80)
print(f"ANÁLISE DETALHADA - SKU: {sku}")
print("="*80)
print(f"Períodos: {len(vendas)}")
print(f"Primeira data: {datas[0]}")
print(f"Última data: {datas[-1]}")
print(f"\nEstatísticas:")
print(f"  Média: {np.mean(vendas):.2f}")
print(f"  Mínimo: {np.min(vendas):.2f}")
print(f"  Máximo: {np.max(vendas):.2f}")
print(f"  Desvio: {np.std(vendas):.2f}")
print(f"  CV: {(np.std(vendas) / np.mean(vendas) * 100):.1f}%")

# Verificar zeros
zeros = sum(1 for v in vendas if v == 0)
print(f"  Zeros: {zeros} ({zeros/len(vendas)*100:.1f}%)")

# Histórico recente
print(f"\nÚltimos 12 meses:")
for i in range(max(0, len(vendas)-12), len(vendas)):
    print(f"  {datas[i]}: {vendas[i]:.1f}")

# Classificação automática
print("\n" + "="*80)
print("CLASSIFICAÇÃO AUTOMÁTICA")
print("="*80)

classificacao = DemandCalculator.classificar_padrao_demanda(vendas)
print(f"Padrão: {classificacao.get('padrao', 'N/A')}")
print(f"Método recomendado: {classificacao.get('metodo_recomendado', 'N/A')}")
print(f"CV: {classificacao.get('cv', 0):.3f}")
print(f"Tendência: {classificacao.get('tendencia', 'N/A')}")
print(f"Sazonalidade: {classificacao.get('sazonalidade', 'N/A')}")

if classificacao.get('tem_sazonalidade'):
    print(f"Período sazonal: {classificacao.get('periodo_sazonal', 'N/A')}")
    print(f"Força sazonal: {classificacao.get('forca_sazonalidade', 'N/A')}")

# Detector de sazonalidade detalhado
print("\n" + "="*80)
print("DETECTOR DE SAZONALIDADE DETALHADO")
print("="*80)

resultado_saz = detect_seasonality(vendas)
print(f"Tem sazonalidade? {resultado_saz['has_seasonality']}")
print(f"Período: {resultado_saz['seasonal_period']}")
print(f"Força: {resultado_saz['strength']:.3f}")
print(f"Confiança: {resultado_saz['confidence']:.3f}")
print(f"Método: {resultado_saz['method']}")
print(f"Razão: {resultado_saz['reason']}")

# Testar todos os métodos
print("\n" + "="*80)
print("PREVISÕES POR MÉTODO")
print("="*80)

metodos = {
    'SMA': lambda: DemandCalculator.calcular_demanda_sma(vendas),
    'WMA': lambda: DemandCalculator.calcular_demanda_wma(vendas),
    'EMA': lambda: DemandCalculator.calcular_demanda_ema(vendas),
    'Tendência': lambda: DemandCalculator.calcular_demanda_tendencia(vendas),
    'Sazonal': lambda: DemandCalculator.calcular_demanda_sazonal(vendas),
}

ultima_venda = vendas[-1]
media_historica = np.mean(vendas)

for nome, metodo in metodos.items():
    try:
        demanda, desvio = metodo()
        diff = demanda - ultima_venda
        diff_pct = (diff / ultima_venda * 100) if ultima_venda > 0 else 0
        print(f"\n{nome}:")
        print(f"  Previsão: {demanda:.2f}")
        print(f"  vs. Última: {diff:+.2f} ({diff_pct:+.1f}%)")
    except Exception as e:
        print(f"\n{nome}: ERRO - {e}")

# Método inteligente
print("\n" + "="*80)
demanda_int, desvio_int, metadata = DemandCalculator.calcular_demanda_inteligente(vendas)
print(f"INTELIGENTE (Automático):")
print(f"  Método escolhido: {metadata['metodo_usado']}")
print(f"  Previsão: {demanda_int:.2f}")
print(f"  vs. Última: {(demanda_int - ultima_venda):+.2f} ({(demanda_int - ultima_venda)/ultima_venda*100:+.1f}%)")

# Análise de médias mensais
print("\n" + "="*80)
print("MÉDIAS POR MÊS DO ANO (se aplicável)")
print("="*80)

if len(vendas) >= 12:
    vendas_por_mes = {}
    for i, venda in enumerate(vendas):
        mes = (i % 12) + 1
        if mes not in vendas_por_mes:
            vendas_por_mes[mes] = []
        vendas_por_mes[mes].append(venda)

    nomes_meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    for mes in range(1, 13):
        if mes in vendas_por_mes and len(vendas_por_mes[mes]) > 0:
            media = np.mean(vendas_por_mes[mes])
            print(f"{nomes_meses[mes-1]}: {media:6.1f} ({len(vendas_por_mes[mes])} amostras)")

# Diagnóstico final
print("\n" + "="*80)
print("DIAGNÓSTICO")
print("="*80)

if classificacao.get('metodo_recomendado') != 'sazonal':
    print("\n[PROBLEMA IDENTIFICADO]")
    print(f"O sistema escolheu '{classificacao.get('metodo_recomendado')}' ao invés de 'sazonal'")
    print("\nPossíveis causas:")

    if not classificacao.get('tem_sazonalidade'):
        print("  1. Sazonalidade não detectada")
        print(f"     - Detector retornou: {resultado_saz['has_seasonality']}")
        print(f"     - Razão: {resultado_saz['reason']}")

        if resultado_saz['strength'] < 0.3:
            print(f"  2. Força sazonal muito fraca: {resultado_saz['strength']:.3f} < 0.3")

        if len(vendas) < 12:
            print(f"  3. Dados insuficientes: {len(vendas)} meses < 12 meses")

    print("\nSugestões:")
    print("  - Verificar se há realmente padrão sazonal nos dados")
    print("  - Considerar usar método 'sazonal' manualmente se houver certeza do padrão")
    print("  - Verificar qualidade dos dados (outliers, zeros, etc.)")
else:
    print("\n[OK] Sistema detectou sazonalidade corretamente")

print("\n" + "="*80)
