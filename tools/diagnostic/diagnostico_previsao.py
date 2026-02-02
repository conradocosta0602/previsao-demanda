"""
Script de diagnóstico para investigar suavização excessiva da previsão
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from core.demand_calculator import DemandCalculator

# Você pode substituir pelo arquivo Excel que está testando
arquivo = input("Digite o caminho do arquivo Excel (ou pressione Enter para exemplo): ").strip()

if not arquivo:
    # Criar dados de exemplo com sazonalidade forte
    print("\n[INFO] Usando dados de exemplo com sazonalidade")
    np.random.seed(42)
    vendas = []
    for i in range(24):
        mes = i % 12
        base = 100
        sazonal = 30 * np.sin((mes / 12) * 2 * np.pi)  # Padrão sazonal forte
        tendencia = i * 2  # Tendência crescente
        ruido = np.random.normal(0, 5)
        vendas.append(max(0, base + sazonal + tendencia + ruido))

    dados = pd.DataFrame({
        'Periodo': range(1, 25),
        'Vendas': vendas
    })
else:
    # Carregar dados do Excel
    print(f"\n[INFO] Carregando dados de {arquivo}")
    dados = pd.read_excel(arquivo, sheet_name='HISTORICO_VENDAS')

    # Assumir primeira SKU
    sku = dados['SKU'].iloc[0]
    dados_sku = dados[dados['SKU'] == sku].copy()
    dados_sku = dados_sku.sort_values('Data')
    vendas = dados_sku['Quantidade'].tolist()

    print(f"[INFO] Analisando SKU: {sku}")
    print(f"[INFO] {len(vendas)} períodos de vendas")

print("\n" + "="*80)
print("DIAGNÓSTICO DE PREVISÃO DE DEMANDA")
print("="*80)

# Exibir dados históricos
print(f"\nDados históricos ({len(vendas)} períodos):")
print(f"  Média: {np.mean(vendas):.2f}")
print(f"  Mínimo: {np.min(vendas):.2f}")
print(f"  Máximo: {np.max(vendas):.2f}")
print(f"  Desvio padrão: {np.std(vendas):.2f}")
print(f"  Coef. variação: {(np.std(vendas) / np.mean(vendas) * 100):.1f}%")

# Classificar padrão
print("\n" + "="*80)
print("CLASSIFICAÇÃO DO PADRÃO")
print("="*80)
classificacao = DemandCalculator.classificar_padrao_demanda(vendas)
print(f"  Padrão detectado: {classificacao.get('padrao', 'N/A')}")
print(f"  Método recomendado: {classificacao.get('metodo_recomendado', 'N/A')}")
print(f"  CV: {classificacao.get('cv', 0):.2f}")
if 'taxa_zeros' in classificacao:
    print(f"  Taxa de zeros: {classificacao['taxa_zeros']:.1f}%")
if 'tem_tendencia' in classificacao:
    print(f"  Tem tendência? {classificacao['tem_tendencia']}")
if 'tem_sazonalidade' in classificacao:
    print(f"  Tem sazonalidade? {classificacao['tem_sazonalidade']}")
    if classificacao['tem_sazonalidade'] and 'periodo_sazonal' in classificacao:
        print(f"  Período sazonal: {classificacao['periodo_sazonal']}")
    if 'forca_sazonalidade' in classificacao:
        print(f"  Força sazonal: {classificacao['forca_sazonalidade']:.2f}")

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
    'TSB': lambda: DemandCalculator.calcular_demanda_tsb(vendas),
    'INTELIGENTE': lambda: DemandCalculator.calcular_demanda_inteligente(vendas)[:2]
}

resultados = {}
for nome, metodo in metodos.items():
    try:
        demanda, desvio = metodo()
        resultados[nome] = {'demanda': demanda, 'desvio': desvio}
        print(f"\n{nome}:")
        print(f"  Previsão: {demanda:.2f}")
        print(f"  Desvio: {desvio:.2f}")

        # Comparar com última venda
        if len(vendas) > 0:
            ultima_venda = vendas[-1]
            diff = demanda - ultima_venda
            diff_pct = (diff / ultima_venda * 100) if ultima_venda > 0 else 0
            print(f"  vs. Última venda ({ultima_venda:.2f}): {diff:+.2f} ({diff_pct:+.1f}%)")

        # Comparar com média
        media = np.mean(vendas)
        diff_media = demanda - media
        diff_media_pct = (diff_media / media * 100) if media > 0 else 0
        print(f"  vs. Média histórica ({media:.2f}): {diff_media:+.2f} ({diff_media_pct:+.1f}%)")
    except Exception as e:
        print(f"\n{nome}: ERRO - {e}")

# Análise de suavização
print("\n" + "="*80)
print("ANÁLISE DE SUAVIZAÇÃO")
print("="*80)

print(f"\nVariação histórica:")
print(f"  Amplitude: {np.max(vendas) - np.min(vendas):.2f}")
print(f"  Amplitude relativa: {((np.max(vendas) - np.min(vendas)) / np.mean(vendas) * 100):.1f}%")

if len(vendas) >= 3:
    ultimas_3 = vendas[-3:]
    print(f"\nÚltimas 3 vendas: {ultimas_3}")
    print(f"  Tendência recente: {ultimas_3[-1] - ultimas_3[0]:+.2f}")

# Criar gráfico visual
print("\n" + "="*80)
print("GRÁFICO COMPARATIVO")
print("="*80)

plt.figure(figsize=(14, 8))

# Plot 1: Histórico + Previsões
plt.subplot(2, 1, 1)
periodos = list(range(1, len(vendas) + 1))
plt.plot(periodos, vendas, 'o-', label='Histórico', linewidth=2, markersize=6)

# Adicionar linha para cada previsão
for nome, res in resultados.items():
    plt.axhline(y=res['demanda'], linestyle='--', alpha=0.7, label=f"{nome}: {res['demanda']:.0f}")

plt.axhline(y=np.mean(vendas), linestyle=':', color='black', alpha=0.5, label=f"Média: {np.mean(vendas):.0f}")
plt.xlabel('Período')
plt.ylabel('Vendas')
plt.title('Histórico de Vendas vs. Previsões')
plt.legend(loc='best', fontsize=8)
plt.grid(True, alpha=0.3)

# Plot 2: Desvios da previsão
plt.subplot(2, 1, 2)
metodos_nomes = list(resultados.keys())
previsoes = [resultados[m]['demanda'] for m in metodos_nomes]
desvios = [resultados[m]['desvio'] for m in metodos_nomes]

x = range(len(metodos_nomes))
plt.bar(x, previsoes, alpha=0.6, label='Previsão')
plt.axhline(y=np.mean(vendas), linestyle='--', color='red', label='Média histórica')
plt.axhline(y=vendas[-1] if len(vendas) > 0 else 0, linestyle='--', color='green', label='Última venda')
plt.xticks(x, metodos_nomes, rotation=45, ha='right')
plt.ylabel('Valor')
plt.title('Comparação de Previsões')
plt.legend()
plt.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('diagnostico_previsao.png', dpi=150)
print("\n[OK] Gráfico salvo em: diagnostico_previsao.png")

# Diagnóstico final
print("\n" + "="*80)
print("DIAGNÓSTICO FINAL")
print("="*80)

# Verificar se está muito suavizado
media_previsoes = np.mean([r['demanda'] for r in resultados.values()])
variacao_previsoes = np.max([r['demanda'] for r in resultados.values()]) - np.min([r['demanda'] for r in resultados.values()])
variacao_historico = np.max(vendas) - np.min(vendas)

print(f"\nVariação do histórico: {variacao_historico:.2f}")
print(f"Variação entre previsões: {variacao_previsoes:.2f}")
print(f"Média das previsões: {media_previsoes:.2f}")
print(f"Média histórica: {np.mean(vendas):.2f}")

if variacao_previsoes < variacao_historico * 0.1:
    print("\n[ALERTA] Previsoes muito proximas - possivel suavizacao excessiva!")
    print("\nPossiveis causas:")
    print("  1. Metodo sazonal usando apenas media simples ao inves de tendencia")
    print("  2. Metodo de tendencia muito conservador")
    print("  3. Sistema nao capturando padroes sazonais corretamente")

    print("\nRecomendacoes:")
    if classificacao.get('tem_sazonalidade'):
        print("  - Sazonalidade detectada mas pode nao estar sendo aplicada corretamente")
        print("  - Verificar calculo de indices sazonais")
    if classificacao.get('tem_tendencia'):
        print("  - Tendencia detectada mas pode estar sendo ignorada")
        print("  - Verificar se tendencia esta sendo combinada com sazonalidade")
else:
    print("\n[OK] Variacao entre previsoes parece adequada")

print("\n" + "="*80)
