"""
Testes de Validação - Detecção Automática de Sazonalidade

Valida o sistema SeasonalityDetector:
- Detecção de sazonalidade em diferentes períodos
- Cálculo de força e confiança
- Testes estatísticos (ANOVA)
- Tratamento de edge cases
"""

import numpy as np
import sys
from core.seasonality_detector import SeasonalityDetector, detect_seasonality

print("=" * 70)
print("TESTE: SISTEMA DE DETECÇÃO AUTOMÁTICA DE SAZONALIDADE")
print("=" * 70)

# ============================================================================
# 1. TESTE: SÉRIE COM SAZONALIDADE MENSAL/ANUAL FORTE
# ============================================================================
print("\n1. Teste de Sazonalidade Mensal/Anual Forte...")

# Criar série com padrão anual claro (12 meses)
# Pico no verão (meses 6-8), baixa no inverno (meses 11-1)
np.random.seed(42)
base = 100
seasonal_pattern = [80, 85, 90, 95, 100, 120, 130, 125, 110, 100, 90, 85]  # 12 meses
serie_anual = []
for ano in range(3):  # 3 anos = 36 meses
    for mes_idx, valor_sazonal in enumerate(seasonal_pattern):
        noise = np.random.normal(0, 5)
        serie_anual.append(valor_sazonal + noise)

detector1 = SeasonalityDetector(serie_anual)
resultado1 = detector1.detect()

print(f"\n   Serie: 36 meses com padrão anual")
print(f"   Sazonalidade detectada: {resultado1['has_seasonality']}")
print(f"   Período: {resultado1['seasonal_period']}")
print(f"   Força: {resultado1['strength']:.2f}")
print(f"   Confiança: {resultado1['confidence']:.2f}")
print(f"   Método: {resultado1['method']}")
print(f"   Razão: {resultado1['reason']}")

if resultado1['has_seasonality']:
    print(f"   [OK] Sazonalidade anual detectada")
else:
    print(f"   [ERRO] Sazonalidade anual NAO foi detectada")

if resultado1['seasonal_period'] == 12:
    print(f"   [OK] Período correto (12 meses)")
elif resultado1['seasonal_period'] is not None:
    print(f"   [AVISO] Período incorreto: {resultado1['seasonal_period']} (esperado: 12)")
else:
    print(f"   [ERRO] Período não identificado")

if resultado1['strength'] > 0.3:
    print(f"   [OK] Força significativa (> 0.3)")
else:
    print(f"   [AVISO] Força fraca: {resultado1['strength']:.2f}")

# ============================================================================
# 2. TESTE: SÉRIE COM SAZONALIDADE TRIMESTRAL
# ============================================================================
print("\n2. Teste de Sazonalidade Trimestral...")

# Criar série com padrão trimestral (4 trimestres)
seasonal_pattern_trimestral = [100, 120, 110, 90]  # Q1, Q2, Q3, Q4
serie_trimestral = []
for ano in range(4):  # 4 anos = 16 trimestres
    for valor_sazonal in seasonal_pattern_trimestral:
        noise = np.random.normal(0, 3)
        serie_trimestral.append(valor_sazonal + noise)

detector2 = SeasonalityDetector(serie_trimestral)
resultado2 = detector2.detect()

print(f"\n   Serie: 16 trimestres com padrão trimestral")
print(f"   Sazonalidade detectada: {resultado2['has_seasonality']}")
print(f"   Período: {resultado2['seasonal_period']}")
print(f"   Força: {resultado2['strength']:.2f}")
print(f"   Confiança: {resultado2['confidence']:.2f}")

if resultado2['has_seasonality']:
    print(f"   [OK] Sazonalidade detectada")
else:
    print(f"   [AVISO] Sazonalidade NAO detectada")

if resultado2['seasonal_period'] == 4:
    print(f"   [OK] Período trimestral detectado (4)")
else:
    print(f"   [AVISO] Período: {resultado2['seasonal_period']} (esperado: 4)")

# ============================================================================
# 3. TESTE: SÉRIE SEM SAZONALIDADE (ALEATÓRIA)
# ============================================================================
print("\n3. Teste de Serie Sem Sazonalidade (Aleatoria)...")

# Série puramente aleatória
np.random.seed(123)
serie_aleatoria = list(np.random.normal(100, 10, 36))

detector3 = SeasonalityDetector(serie_aleatoria)
resultado3 = detector3.detect()

print(f"\n   Serie: 36 valores aleatorios")
print(f"   Sazonalidade detectada: {resultado3['has_seasonality']}")
print(f"   Força: {resultado3['strength']:.2f}")
print(f"   Confiança: {resultado3['confidence']:.2f}")
print(f"   Razão: {resultado3['reason']}")

if not resultado3['has_seasonality']:
    print(f"   [OK] Corretamente identificada como NAO sazonal")
else:
    print(f"   [AVISO] Detectou sazonalidade em serie aleatoria")

if resultado3['strength'] < 0.3:
    print(f"   [OK] Força fraca (< 0.3)")
else:
    print(f"   [AVISO] Força inesperadamente alta: {resultado3['strength']:.2f}")

# ============================================================================
# 4. TESTE: SÉRIE MUITO CURTA (< 8 PERÍODOS)
# ============================================================================
print("\n4. Teste de Serie Muito Curta...")

serie_curta = [100, 110, 105, 120, 115, 110, 108]  # Apenas 7 valores

detector4 = SeasonalityDetector(serie_curta)
resultado4 = detector4.detect()

print(f"\n   Serie: {len(serie_curta)} periodos")
print(f"   Sazonalidade detectada: {resultado4['has_seasonality']}")
print(f"   Método: {resultado4['method']}")
print(f"   Razão: {resultado4['reason']}")

if not resultado4['has_seasonality']:
    print(f"   [OK] Detectacao desabilitada para serie curta")
else:
    print(f"   [ERRO] Detectou sazonalidade em serie muito curta")

if resultado4['method'] == 'INSUFFICIENT_DATA':
    print(f"   [OK] Método correto: INSUFFICIENT_DATA")
else:
    print(f"   [AVISO] Método: {resultado4['method']}")

# ============================================================================
# 5. TESTE: SAZONALIDADE SEMANAL
# ============================================================================
print("\n5. Teste de Sazonalidade Semanal...")

# Criar série com padrão semanal (7 dias)
# Menor demanda no fim de semana (dias 5-6), maior durante semana
seasonal_pattern_semanal = [100, 105, 110, 108, 95, 70, 75]  # Seg-Dom
serie_semanal = []
for semana in range(8):  # 8 semanas = 56 dias
    for valor_sazonal in seasonal_pattern_semanal:
        noise = np.random.normal(0, 5)
        serie_semanal.append(valor_sazonal + noise)

detector5 = SeasonalityDetector(serie_semanal)
resultado5 = detector5.detect()

print(f"\n   Serie: 56 dias (8 semanas)")
print(f"   Sazonalidade detectada: {resultado5['has_seasonality']}")
print(f"   Período: {resultado5['seasonal_period']}")
print(f"   Força: {resultado5['strength']:.2f}")

if resultado5['has_seasonality']:
    print(f"   [OK] Sazonalidade detectada")
else:
    print(f"   [AVISO] Sazonalidade semanal NAO detectada")

if resultado5['seasonal_period'] == 7:
    print(f"   [OK] Período semanal detectado (7)")
else:
    print(f"   [AVISO] Período: {resultado5['seasonal_period']} (esperado: 7)")

# ============================================================================
# 6. TESTE: ÍNDICES SAZONAIS
# ============================================================================
print("\n6. Teste de Indices Sazonais...")

# Usar série anual (teste 1)
if resultado1['has_seasonality'] and resultado1['seasonal_indices']:
    indices = resultado1['seasonal_indices']
    print(f"\n   Serie: Anual (12 meses)")
    print(f"   Indices sazonais: {len(indices)} valores")

    if len(indices) == 12:
        print(f"   [OK] 12 indices sazonais (correto)")
    else:
        print(f"   [ERRO] {len(indices)} indices (esperado: 12)")

    # Verificar que há variação nos índices
    indices_array = np.array(indices)
    variacao = np.std(indices_array)

    if variacao > 0:
        print(f"   [OK] Indices variam (std: {variacao:.2f})")
    else:
        print(f"   [ERRO] Indices sem variacao")

    # Mostrar índices (primeiros 6)
    print(f"   Primeiros 6 indices: {[f'{x:.1f}' for x in indices[:6]]}")
else:
    print(f"   [AVISO] Indices sazonais nao disponiveis")

# ============================================================================
# 7. TESTE: SÉRIE COM TENDÊNCIA + SAZONALIDADE
# ============================================================================
print("\n7. Teste de Serie com Tendencia + Sazonalidade...")

# Criar série com tendência crescente + sazonalidade anual
np.random.seed(456)
serie_tendencia_sazonal = []
for mes in range(36):
    tendencia = 100 + (mes * 2)  # Tendência crescente
    sazonalidade = seasonal_pattern[mes % 12] - 100  # Componente sazonal
    noise = np.random.normal(0, 5)
    serie_tendencia_sazonal.append(tendencia + sazonalidade + noise)

detector7 = SeasonalityDetector(serie_tendencia_sazonal)
resultado7 = detector7.detect()

print(f"\n   Serie: 36 meses com tendencia + sazonalidade")
print(f"   Sazonalidade detectada: {resultado7['has_seasonality']}")
print(f"   Período: {resultado7['seasonal_period']}")
print(f"   Força: {resultado7['strength']:.2f}")

if resultado7['has_seasonality']:
    print(f"   [OK] Sazonalidade detectada apesar da tendencia")
else:
    print(f"   [AVISO] Sazonalidade NAO detectada")

# ============================================================================
# 8. TESTE: SAZONALIDADE FRACA (LIMIAR)
# ============================================================================
print("\n8. Teste de Sazonalidade Fraca (Limiar)...")

# Criar série com sazonalidade muito fraca
seasonal_pattern_fraco = [100, 102, 101, 99, 100, 103, 102, 98, 100, 101, 99, 100]
serie_fraca = []
for ano in range(3):
    for valor_sazonal in seasonal_pattern_fraco:
        noise = np.random.normal(0, 8)  # Ruído maior que sinal
        serie_fraca.append(valor_sazonal + noise)

detector8 = SeasonalityDetector(serie_fraca)
resultado8 = detector8.detect()

print(f"\n   Serie: 36 meses com sazonalidade fraca")
print(f"   Sazonalidade detectada: {resultado8['has_seasonality']}")
print(f"   Força: {resultado8['strength']:.2f}")
print(f"   Razão: {resultado8['reason']}")

if not resultado8['has_seasonality']:
    print(f"   [OK] Corretamente rejeitada (sazonalidade fraca)")
else:
    print(f"   [AVISO] Detectou sazonalidade fraca")

# ============================================================================
# 9. TESTE: FUNÇÃO HELPER detect_seasonality()
# ============================================================================
print("\n9. Teste de Funcao Helper...")

resultado_helper = detect_seasonality(serie_anual)

print(f"\n   Funcao: detect_seasonality()")
print(f"   Retornou dicionario: {isinstance(resultado_helper, dict)}")
print(f"   Contem 'has_seasonality': {'has_seasonality' in resultado_helper}")
print(f"   Contem 'seasonal_period': {'seasonal_period' in resultado_helper}")
print(f"   Contem 'strength': {'strength' in resultado_helper}")

if isinstance(resultado_helper, dict):
    print(f"   [OK] Funcao helper retorna dicionario")
else:
    print(f"   [ERRO] Funcao helper NAO retorna dicionario")

campos_esperados = ['has_seasonality', 'seasonal_period', 'strength',
                    'confidence', 'method', 'reason', 'seasonal_indices']
faltando = [c for c in campos_esperados if c not in resultado_helper]

if len(faltando) == 0:
    print(f"   [OK] Todos os campos presentes")
else:
    print(f"   [ERRO] Campos faltando: {faltando}")

# ============================================================================
# 10. TESTE: CONFIANÇA NA DETECÇÃO
# ============================================================================
print("\n10. Teste de Calculo de Confianca...")

# Testar diferentes cenários de confiança
cenarios = [
    (resultado1, "Sazonalidade forte"),
    (resultado3, "Serie aleatoria"),
    (resultado4, "Serie curta"),
]

for resultado, descricao in cenarios:
    conf = resultado['confidence']
    print(f"\n   Cenario: {descricao}")
    print(f"   Confianca: {conf:.2f}")

    if 0 <= conf <= 1:
        print(f"   [OK] Confianca no intervalo [0, 1]")
    else:
        print(f"   [ERRO] Confianca fora do intervalo: {conf}")

# ============================================================================
# 11. TESTE: MÚLTIPLOS PERÍODOS CANDIDATOS
# ============================================================================
print("\n11. Teste de Multiplos Periodos Candidatos...")

# Série longa o suficiente para testar vários períodos
serie_longa = list(np.random.normal(100, 10, 48))  # 48 períodos

detector11 = SeasonalityDetector(serie_longa)
candidatos = detector11._get_candidate_periods()

print(f"\n   Serie: {len(serie_longa)} periodos")
print(f"   Candidatos testados: {candidatos}")
print(f"   Total de candidatos: {len(candidatos)}")

periodos_esperados = [2, 4, 6, 7, 12, 14]  # Todos viáveis para n=48
candidatos_esperados = [p for p in periodos_esperados if p in candidatos]

if len(candidatos) >= 4:
    print(f"   [OK] Multiplos periodos testados")
else:
    print(f"   [AVISO] Poucos candidatos: {len(candidatos)}")

if 12 in candidatos:
    print(f"   [OK] Periodo anual (12) incluido")
else:
    print(f"   [ERRO] Periodo anual NAO incluido")

# ============================================================================
# 12. TESTE: NOMES DE PERÍODOS
# ============================================================================
print("\n12. Teste de Nomes de Periodos...")

detector_teste = SeasonalityDetector([100] * 20)
nomes = {
    2: 'bimestral',
    4: 'trimestral',
    6: 'semestral',
    7: 'semanal',
    12: 'mensal/anual',
    14: 'quinzenal'
}

testes_nomes = []
for periodo, nome_esperado in nomes.items():
    nome_obtido = detector_teste._get_period_name(periodo)

    if nome_obtido == nome_esperado:
        testes_nomes.append(True)
        print(f"   [OK] Periodo {periodo}: '{nome_obtido}'")
    else:
        testes_nomes.append(False)
        print(f"   [ERRO] Periodo {periodo}: '{nome_obtido}' (esperado: '{nome_esperado}')")

# Período desconhecido
nome_desconhecido = detector_teste._get_period_name(99)
if 'período-99' in nome_desconhecido:
    print(f"   [OK] Periodo desconhecido: '{nome_desconhecido}'")
    testes_nomes.append(True)
else:
    print(f"   [ERRO] Periodo desconhecido: '{nome_desconhecido}'")
    testes_nomes.append(False)

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "=" * 70)
print("RESUMO FINAL - VALIDACAO DO DETECTOR DE SAZONALIDADE")
print("=" * 70)

checklist = [
    resultado1['has_seasonality'] and resultado1['seasonal_period'] == 12,  # 1. Anual
    resultado2['has_seasonality'],  # 2. Trimestral
    not resultado3['has_seasonality'],  # 3. Aleatoria
    not resultado4['has_seasonality'] and resultado4['method'] == 'INSUFFICIENT_DATA',  # 4. Curta
    resultado5['has_seasonality'],  # 5. Semanal
    resultado1['seasonal_indices'] is not None and len(resultado1['seasonal_indices']) == 12,  # 6. Indices
    resultado7['has_seasonality'],  # 7. Tendencia + sazonalidade
    not resultado8['has_seasonality'],  # 8. Fraca
    isinstance(resultado_helper, dict) and len(faltando) == 0,  # 9. Helper
    all(0 <= r['confidence'] <= 1 for r, _ in cenarios),  # 10. Confianca
    len(candidatos) >= 4 and 12 in candidatos,  # 11. Candidatos
    all(testes_nomes),  # 12. Nomes
]

print("\nChecklist de validacoes:")
print(f"  {'[OK]' if checklist[0] else '[ERRO]'} Sazonalidade anual forte detectada")
print(f"  {'[OK]' if checklist[1] else '[AVISO]'} Sazonalidade trimestral detectada")
print(f"  {'[OK]' if checklist[2] else '[AVISO]'} Serie aleatoria rejeitada")
print(f"  {'[OK]' if checklist[3] else '[ERRO]'} Serie curta protegida")
print(f"  {'[OK]' if checklist[4] else '[AVISO]'} Sazonalidade semanal detectada")
print(f"  {'[OK]' if checklist[5] else '[ERRO]'} Indices sazonais corretos")
print(f"  {'[OK]' if checklist[6] else '[AVISO]'} Sazonalidade com tendencia")
print(f"  {'[OK]' if checklist[7] else '[AVISO]'} Sazonalidade fraca rejeitada")
print(f"  {'[OK]' if checklist[8] else '[ERRO]'} Funcao helper funcionando")
print(f"  {'[OK]' if checklist[9] else '[ERRO]'} Confianca no intervalo [0,1]")
print(f"  {'[OK]' if checklist[10] else '[ERRO]'} Multiplos periodos testados")
print(f"  {'[OK]' if checklist[11] else '[ERRO]'} Nomes de periodos corretos")

aprovados = sum(checklist)
total = len(checklist)
taxa = (aprovados / total) * 100

print(f"\nTaxa de sucesso: {aprovados}/{total} ({taxa:.0f}%)")

print("\n" + "=" * 70)
print("Estatisticas dos Testes:")
print("=" * 70)

# Contar métodos usados
metodos_usados = {}
for r in [resultado1, resultado2, resultado3, resultado4, resultado5, resultado7, resultado8]:
    metodo = r.get('method', 'UNKNOWN')
    metodos_usados[metodo] = metodos_usados.get(metodo, 0) + 1

print("\nMetodos utilizados:")
for metodo, count in sorted(metodos_usados.items(), key=lambda x: x[1], reverse=True):
    print(f"  {metodo}: {count} vezes")

# Contar períodos detectados
periodos_detectados = {}
for r in [resultado1, resultado2, resultado3, resultado4, resultado5, resultado7, resultado8]:
    if r['has_seasonality'] and r['seasonal_period']:
        periodo = r['seasonal_period']
        periodos_detectados[periodo] = periodos_detectados.get(periodo, 0) + 1

if periodos_detectados:
    print("\nPeriodos sazonais detectados:")
    for periodo, count in sorted(periodos_detectados.items()):
        nome = detector_teste._get_period_name(periodo)
        print(f"  {periodo} ({nome}): {count} vez(es)")
else:
    print("\nNenhum periodo sazonal foi detectado nos testes")

# Estatísticas de força
forcas = [r['strength'] for r in [resultado1, resultado2, resultado3, resultado5, resultado7, resultado8]]
print(f"\nForca da sazonalidade:")
print(f"  Media: {np.mean(forcas):.2f}")
print(f"  Min: {np.min(forcas):.2f}")
print(f"  Max: {np.max(forcas):.2f}")

print("\n" + "=" * 70)
if taxa >= 80:
    print("STATUS: [SUCESSO] Sistema funciona muito bem")
elif taxa >= 60:
    print("STATUS: [AVISO] Sistema funciona mas ha problemas menores")
else:
    print("STATUS: [ERRO] Sistema apresenta problemas significativos")
print("=" * 70)
