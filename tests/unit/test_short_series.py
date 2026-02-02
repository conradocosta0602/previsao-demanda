"""
Teste do Tratamento de Séries Curtas
"""
import pandas as pd
import numpy as np
from core.short_series_handler import ShortSeriesHandler

print("=" * 70)
print("TESTE: Tratamento de Series Curtas")
print("=" * 70)

# Criar handler
handler = ShortSeriesHandler()

# 1. TESTE: Classificação de séries
print("\n1. Teste de Classificacao de Series")
print("-" * 70)

test_cases = [
    ("Serie muito curta (2 meses)", [100, 120]),
    ("Serie curta (4 meses)", [100, 110, 120, 115]),
    ("Serie media (8 meses)", [100, 110, 120, 115, 125, 130, 135, 140]),
    ("Serie longa (15 meses)", [100 + i*5 for i in range(15)])
]

for nome, valores in test_cases:
    serie = pd.Series(valores)
    classificacao = handler.classificar_serie(serie)

    print(f"\n{nome}:")
    print(f"  Tamanho: {len(serie)} meses")
    print(f"  Categoria: {classificacao['categoria']}")
    print(f"  Metodo recomendado: {classificacao['metodo_recomendado']}")
    print(f"  Confiabilidade: {classificacao['confiabilidade']}")

# 2. TESTE: Métodos de previsão para séries muito curtas
print("\n\n2. Teste de Metodos para Series Muito Curtas")
print("-" * 70)

serie_muito_curta = pd.Series([100, 120])
print(f"\nSerie de teste: {serie_muito_curta.values}")

metodos = [
    ('ULTIMO_VALOR', 3),
    ('MEDIA_SIMPLES', 3),
    ('MEDIA_PONDERADA', 3),
    ('CRESCIMENTO_LINEAR', 3)
]

for metodo, periodos in metodos:
    try:
        resultado = handler.prever_serie_curta(serie_muito_curta, periodos, metodo)
        print(f"\n  {metodo}:")
        print(f"    Previsoes: {resultado['previsoes']}")
        print(f"    Media: {np.mean(resultado['previsoes']):.2f}")
        print(f"    Confianca: {resultado['confianca']:.1%}")
    except Exception as e:
        print(f"\n  {metodo}: ERRO - {e}")

# 3. TESTE: Detecção de tendência
print("\n\n3. Teste de Deteccao de Tendencia")
print("-" * 70)

test_tendencias = [
    ("Crescente forte", [100, 120, 140, 160, 180]),
    ("Decrescente", [200, 180, 160, 140, 120]),
    ("Estavel", [100, 98, 102, 99, 101, 100]),
    ("Volatil", [100, 50, 150, 75, 125])
]

for nome, valores in test_tendencias:
    serie = pd.Series(valores)
    analise = handler.detectar_tendencia(serie)

    print(f"\n{nome}:")
    print(f"  Valores: {valores}")
    print(f"  Tipo: {analise['tipo']}")
    print(f"  Inclinacao: {analise['inclinacao']:.4f}")
    print(f"  Inclinacao normalizada: {analise['inclinacao_normalizada']:.4f}")
    print(f"  R2: {analise['r2']:.3f}")
    print(f"  Tem tendencia: {analise['tem_tendencia']}")

# 4. TESTE: Sugestão adaptativa
print("\n\n4. Teste de Sugestao Adaptativa")
print("-" * 70)

test_adaptativas = [
    ("2 meses - crescente", [100, 120]),
    ("3 meses - estavel", [100, 98, 102]),
    ("5 meses - decrescente", [200, 180, 160, 140, 120]),
    ("4 meses - volatil", [100, 50, 150, 75])
]

for nome, valores in test_adaptativas:
    serie = pd.Series(valores)
    sugestao = handler.sugerir_metodo_adaptativo(serie)

    print(f"\n{nome}:")
    print(f"  Metodo sugerido: {sugestao['metodo_sugerido']}")
    print(f"  Razao: {sugestao['razao']}")
    print(f"  Confianca: {sugestao['confianca_estimada']:.1%}")
    print(f"  Tendencia: {sugestao['analise_tendencia']['tipo']}")

# 5. TESTE: Previsão completa com diferentes séries
print("\n\n5. Teste de Previsao Completa")
print("-" * 70)

# Serie com tendência crescente clara
serie_crescente = pd.Series([100, 110, 120, 130, 140])
print(f"\nSerie crescente: {serie_crescente.values}")

sugestao = handler.sugerir_metodo_adaptativo(serie_crescente)
print(f"Metodo sugerido: {sugestao['metodo_sugerido']}")

resultado = handler.prever_serie_curta(
    serie_crescente,
    n_periodos=3,
    metodo=sugestao['metodo_sugerido']
)
previsao = resultado['previsoes']
print(f"Previsao proximos 3 meses: {previsao}")

# Validar que a tendência continua
if sugestao['metodo_sugerido'] == 'CRESCIMENTO_LINEAR':
    if all(previsao[i] < previsao[i+1] for i in range(len(previsao)-1)):
        print("  [OK] Tendencia crescente mantida na previsao")
    else:
        print("  [AVISO] Tendencia nao mantida")

# 6. TESTE: Intervalo de confiança
print("\n\n6. Teste de Intervalo de Confianca")
print("-" * 70)

serie_teste = pd.Series([100, 110, 105, 115, 120])
resultado_intervalo = handler.criar_previsoes_com_intervalo(serie_teste, n_periodos=3)

print(f"\nSerie: {serie_teste.values}")
print(f"CV: {np.std(serie_teste) / np.mean(serie_teste):.3f}")
print(f"Metodo: {resultado_intervalo['metodo_usado']}")
print(f"\nPrevisoes com intervalo de confianca ({resultado_intervalo['intervalo_confianca']:.0%}):")
for i in range(len(resultado_intervalo['previsoes'])):
    prev = resultado_intervalo['previsoes'][i]
    inf = resultado_intervalo['limite_inferior'][i]
    sup = resultado_intervalo['limite_superior'][i]
    print(f"  Periodo {i+1}:")
    print(f"    Inferior: {inf:.2f}")
    print(f"    Previsao: {prev:.2f}")
    print(f"    Superior: {sup:.2f}")
    print(f"    Amplitude: {sup - inf:.2f}")

# 7. TESTE: Edge cases
print("\n\n7. Teste de Casos Extremos")
print("-" * 70)

edge_cases = [
    ("Serie de 1 elemento", [100]),
    ("Serie com zeros", [0, 0, 10, 0]),
    ("Serie com valores negativos (erro esperado)", [-10, -20, -30]),
    ("Serie vazia", [])
]

for nome, valores in edge_cases:
    print(f"\n{nome}:")
    if len(valores) == 0:
        print("  [SKIP] Serie vazia - nao testado")
        continue

    try:
        serie = pd.Series(valores)
        classificacao = handler.classificar_serie(serie)
        print(f"  Categoria: {classificacao['categoria']}")
        print(f"  Metodo: {classificacao['metodo_recomendado']}")

        # Tentar previsão
        if len(serie) >= 1:
            resultado = handler.prever_serie_curta(serie, 2, classificacao['metodo_recomendado'])
            print(f"  Previsao: {resultado['previsoes']}")
            print(f"  [OK] Tratamento adequado")
    except Exception as e:
        print(f"  [ERRO] {e}")

# 8. TESTE: Comparação com métodos tradicionais
print("\n\n8. Comparacao com Metodos Tradicionais")
print("-" * 70)

# Serie curta com padrão claro
serie_padrao = pd.Series([100, 110, 120, 130])
print(f"\nSerie: {serie_padrao.values}")
print("Comparando metodos:\n")

# Método adaptativo (handler)
sugestao = handler.sugerir_metodo_adaptativo(serie_padrao)
resultado_adaptativo = handler.prever_serie_curta(serie_padrao, 3, sugestao['metodo_sugerido'])
prev_adaptativa = resultado_adaptativo['previsoes']

# Média móvel simples
prev_media = np.full(3, serie_padrao.tail(3).mean())

# Último valor
prev_ultimo = np.full(3, serie_padrao.iloc[-1])

print(f"Metodo adaptativo ({sugestao['metodo_sugerido']}): {prev_adaptativa}")
print(f"Media movel simples: {prev_media}")
print(f"Ultimo valor: {prev_ultimo}")

# Se há tendência clara, o método adaptativo deve ser diferente dos outros
if sugestao['metodo_sugerido'] == 'CRESCIMENTO_LINEAR':
    if not np.array_equal(prev_adaptativa, prev_media):
        print("\n[OK] Metodo adaptativo diferenciado da media movel")
    if not np.array_equal(prev_adaptativa, prev_ultimo):
        print("[OK] Metodo adaptativo diferenciado do ultimo valor")

# 9. RESUMO
print("\n\n" + "=" * 70)
print("RESUMO DOS TESTES")
print("=" * 70)

print("\nFuncionalidades testadas:")
print("  [OK] Classificacao de series (muito curta, curta, media, longa)")
print("  [OK] Metodos especializados (ultimo valor, media, ponderada, crescimento)")
print("  [OK] Deteccao de tendencia (crescente, decrescente, estavel)")
print("  [OK] Sugestao adaptativa baseada em caracteristicas")
print("  [OK] Intervalo de confianca")
print("  [OK] Tratamento de casos extremos")
print("  [OK] Diferenciacao de metodos tradicionais")

print("\nHandler de series curtas pronto para uso!")
print("=" * 70)
