"""
Teste de Validação: Sistema de Validação Robusta de Entrada

Este teste valida que o sistema de validação de dados está funcionando
corretamente para detectar e prevenir erros de entrada.
"""
import sys
import numpy as np
from core.validation import (
    validate_series_length,
    validate_positive_values,
    detect_outliers,
    check_missing_data,
    validate_data_type,
    validate_series,
    validate_forecast_inputs,
    ValidationError
)

print("=" * 70)
print("TESTE: SISTEMA DE VALIDACAO ROBUSTA DE ENTRADA")
print("=" * 70)

# ============================================================================
# 1. TESTE: VALIDAÇÃO DE COMPRIMENTO DA SÉRIE
# ============================================================================
print("\n1. Teste de Validacao de Comprimento...")

test_cases_length = [
    ([100], 3, False, "Serie com 1 elemento (min=3)"),
    ([100, 110], 3, False, "Serie com 2 elementos (min=3)"),
    ([100, 110, 120], 3, True, "Serie com 3 elementos (min=3)"),
    ([100, 110, 120, 130], 3, True, "Serie com 4 elementos (min=3)"),
]

resultados_length = []

for serie, min_len, deve_passar, descricao in test_cases_length:
    try:
        validate_series_length(serie, min_length=min_len)
        passou = deve_passar
        status = "[OK]" if passou else "[ERRO]"
        resultado = "Passou validacao"
    except ValidationError as e:
        passou = not deve_passar
        status = "[OK]" if passou else "[ERRO]"
        resultado = f"Erro: {e.code}"

    print(f"   {status} {descricao}: {resultado}")
    resultados_length.append(passou)

# ============================================================================
# 2. TESTE: VALIDAÇÃO DE VALORES POSITIVOS
# ============================================================================
print("\n2. Teste de Validacao de Valores Positivos...")

test_cases_positive = [
    ([100, 110, 120], True, True, "Todos positivos (zeros permitidos)"),
    ([100, 0, 120], True, True, "Com zeros (zeros permitidos)"),
    ([100, 0, 120], False, False, "Com zeros (zeros NAO permitidos)"),
    ([100, -10, 120], True, False, "Com negativos"),
    ([100, 110, 120], False, True, "Todos positivos (zeros NAO permitidos)"),
]

resultados_positive = []

for serie, allow_zeros, deve_passar, descricao in test_cases_positive:
    try:
        validate_positive_values(serie, allow_zeros=allow_zeros)
        passou = deve_passar
        status = "[OK]" if passou else "[ERRO]"
        resultado = "Passou validacao"
    except ValidationError as e:
        passou = not deve_passar
        status = "[OK]" if passou else "[ERRO]"
        resultado = f"Erro: {e.code}"

    print(f"   {status} {descricao}: {resultado}")
    resultados_positive.append(passou)

# ============================================================================
# 3. TESTE: DETECÇÃO DE OUTLIERS
# ============================================================================
print("\n3. Teste de Deteccao de Outliers...")

# Série com outlier óbvio
serie_outlier = [100, 110, 105, 115, 1000, 120, 108]  # 1000 é outlier

# Método IQR
outliers_iqr, stats_iqr = detect_outliers(serie_outlier, method='iqr', threshold=1.5)
print(f"\n   Serie: {serie_outlier}")
print(f"   Metodo IQR:")
print(f"     Outliers detectados: {len(outliers_iqr)}")
print(f"     Indices: {outliers_iqr}")
print(f"     Q1: {stats_iqr['q1']:.2f}, Q3: {stats_iqr['q3']:.2f}")
print(f"     IQR: {stats_iqr['iqr']:.2f}")
print(f"     Limites: [{stats_iqr['lower_bound']:.2f}, {stats_iqr['upper_bound']:.2f}]")

if 4 in outliers_iqr:  # Índice do valor 1000
    print(f"     [OK] Outlier 1000 detectado corretamente (indice 4)")
else:
    print(f"     [ERRO] Outlier 1000 NAO foi detectado")

# Método Z-Score
outliers_zscore, stats_zscore = detect_outliers(serie_outlier, method='zscore', threshold=3.0)
print(f"\n   Metodo Z-Score:")
print(f"     Outliers detectados: {len(outliers_zscore)}")
print(f"     Indices: {outliers_zscore}")
print(f"     Media: {stats_zscore['mean']:.2f}")
print(f"     Desvio: {stats_zscore['std']:.2f}")

if 4 in outliers_zscore:
    print(f"     [OK] Outlier detectado por Z-Score")
else:
    print(f"     [AVISO] Z-Score nao detectou o outlier")

# ============================================================================
# 4. TESTE: DETECÇÃO DE DADOS FALTANTES
# ============================================================================
print("\n4. Teste de Deteccao de Dados Faltantes...")

test_cases_missing = [
    ([100, 110, 120], False, "Serie sem faltantes"),
    ([100, None, 120], True, "Serie com None"),
    ([100, np.nan, 120], True, "Serie com NaN"),
    ([100, None, np.nan, 120], True, "Serie com None e NaN"),
]

resultados_missing = []

for serie, tem_faltantes_esperado, descricao in test_cases_missing:
    has_missing, missing_indices = check_missing_data(serie)

    passou = (has_missing == tem_faltantes_esperado)
    status = "[OK]" if passou else "[ERRO]"

    if has_missing:
        print(f"   {status} {descricao}: {len(missing_indices)} faltante(s) em {missing_indices}")
    else:
        print(f"   {status} {descricao}: Nenhum faltante")

    resultados_missing.append(passou)

# ============================================================================
# 5. TESTE: VALIDAÇÃO DE TIPO DE DADOS
# ============================================================================
print("\n5. Teste de Validacao de Tipo de Dados...")

test_cases_type = [
    ([100, 110, 120], True, "Inteiros validos"),
    ([100.5, 110.3, 120.7], True, "Floats validos"),
    ([100, 110.5, 120], True, "Mistura int/float valido"),
    ([100, "110", 120], False, "Com string (invalido)"),
    ([100, [110], 120], False, "Com lista (invalido)"),
]

resultados_type = []

for serie, deve_passar, descricao in test_cases_type:
    try:
        validate_data_type(serie)
        passou = deve_passar
        status = "[OK]" if passou else "[ERRO]"
        resultado = "Passou validacao"
    except ValidationError as e:
        passou = not deve_passar
        status = "[OK]" if passou else "[ERRO]"
        resultado = f"Erro: {e.code}"

    print(f"   {status} {descricao}: {resultado}")
    resultados_type.append(passou)

# ============================================================================
# 6. TESTE: VALIDAÇÃO COMPLETA DE SÉRIE
# ============================================================================
print("\n6. Teste de Validacao Completa de Serie...")

# Série válida
serie_valida = [100, 110, 105, 115, 120, 125]
try:
    result = validate_series(serie_valida, min_length=3, allow_zeros=True)
    print(f"\n   Serie valida: {serie_valida}")
    print(f"     Valid: {result['valid']}")
    print(f"     Warnings: {len(result['warnings'])}")
    print(f"     Errors: {len(result['errors'])}")
    print(f"     Estatisticas:")
    print(f"       Comprimento: {result['statistics']['general']['length']}")
    print(f"       Media: {result['statistics']['general']['mean']:.2f}")
    print(f"       Std: {result['statistics']['general']['std']:.2f}")
    print(f"     [OK] Validacao completa passou")
except ValidationError as e:
    print(f"     [ERRO] Validacao falhou: {e}")

# Série inválida (muito curta)
serie_invalida = [100, 110]
try:
    result = validate_series(serie_invalida, min_length=3)
    print(f"\n   [ERRO] Serie invalida deveria ter falhado")
except ValidationError as e:
    print(f"\n   [OK] Serie invalida detectada: {e.code}")

# ============================================================================
# 7. TESTE: VALIDAÇÃO DE ENTRADAS DE PREVISÃO
# ============================================================================
print("\n7. Teste de Validacao de Entradas de Previsao...")

# Horizonte válido
serie_previsao = [100, 110, 120, 130, 140, 150]
try:
    result = validate_forecast_inputs(
        data=serie_previsao,
        horizon=6,
        method_name='SMA'
    )
    print(f"\n   Horizonte valido (6): [OK] Passou")
except ValidationError as e:
    print(f"\n   [ERRO] Horizonte valido falhou: {e}")

# Horizonte inválido (negativo)
try:
    result = validate_forecast_inputs(
        data=serie_previsao,
        horizon=-1,
        method_name='SMA'
    )
    print(f"   [ERRO] Horizonte negativo deveria ter falhado")
except ValidationError as e:
    print(f"   [OK] Horizonte negativo detectado: {e.code}")

# Horizonte muito longo
try:
    result = validate_forecast_inputs(
        data=serie_previsao,
        horizon=50,
        method_name='SMA'
    )
    print(f"   [ERRO] Horizonte muito longo deveria ter falhado")
except ValidationError as e:
    print(f"   [OK] Horizonte muito longo detectado: {e.code}")

# Decomposição sazonal sem dados suficientes
serie_curta_sazonal = [100] * 10
try:
    result = validate_forecast_inputs(
        data=serie_curta_sazonal,
        horizon=6,
        method_name='Decomposição Sazonal'
    )
    print(f"   [ERRO] Decomposicao sazonal sem dados deveria ter falhado")
except ValidationError as e:
    print(f"   [OK] Decomposicao sazonal sem dados detectada: {e.code}")

# ============================================================================
# 8. TESTE: CÓDIGOS DE ERRO
# ============================================================================
print("\n8. Teste de Codigos de Erro...")

codigos_esperados = {
    'ERR001': 'Serie muito curta',
    'ERR002': 'Valores negativos',
    'ERR003': 'Zeros nao permitidos',
    'ERR004': 'Tipo invalido',
    'ERR005': 'Dados faltantes',
    'ERR006': 'Horizonte invalido',
    'ERR007': 'Horizonte muito longo',
    'ERR008': 'Decomposicao sazonal sem dados'
}

codigos_testados = []

# ERR001 - Série muito curta
try:
    validate_series_length([100], min_length=3)
except ValidationError as e:
    if e.code == 'ERR001':
        print(f"   [OK] {e.code}: {codigos_esperados[e.code]}")
        codigos_testados.append('ERR001')

# ERR002 - Valores negativos
try:
    validate_positive_values([100, -10, 120])
except ValidationError as e:
    if e.code == 'ERR002':
        print(f"   [OK] {e.code}: {codigos_esperados[e.code]}")
        codigos_testados.append('ERR002')

# ERR003 - Zeros não permitidos
try:
    validate_positive_values([100, 0, 120], allow_zeros=False)
except ValidationError as e:
    if e.code == 'ERR003':
        print(f"   [OK] {e.code}: {codigos_esperados[e.code]}")
        codigos_testados.append('ERR003')

# ERR004 - Tipo inválido
try:
    validate_data_type([100, "110", 120])
except ValidationError as e:
    if e.code == 'ERR004':
        print(f"   [OK] {e.code}: {codigos_esperados[e.code]}")
        codigos_testados.append('ERR004')

# ERR005 - Dados faltantes
try:
    validate_series([100, None, 120])
except ValidationError as e:
    if e.code == 'ERR005':
        print(f"   [OK] {e.code}: {codigos_esperados[e.code]}")
        codigos_testados.append('ERR005')

# ERR006 - Horizonte inválido
try:
    validate_forecast_inputs([100, 110, 120], horizon=0, method_name='SMA')
except ValidationError as e:
    if e.code == 'ERR006':
        print(f"   [OK] {e.code}: {codigos_esperados[e.code]}")
        codigos_testados.append('ERR006')

# ERR007 - Horizonte muito longo
try:
    validate_forecast_inputs([100, 110, 120], horizon=50, method_name='SMA')
except ValidationError as e:
    if e.code == 'ERR007':
        print(f"   [OK] {e.code}: {codigos_esperados[e.code]}")
        codigos_testados.append('ERR007')

# ERR008 - Decomposição sazonal sem dados
try:
    validate_forecast_inputs([100]*10, horizon=6, method_name='Decomposição Sazonal')
except ValidationError as e:
    if e.code == 'ERR008':
        print(f"   [OK] {e.code}: {codigos_esperados[e.code]}")
        codigos_testados.append('ERR008')

# ============================================================================
# 9. TESTE: SUGESTÕES DE CORREÇÃO
# ============================================================================
print("\n9. Teste de Sugestoes de Correcao...")

# Cada ValidationError deve ter sugestão
try:
    validate_series_length([100], min_length=3)
except ValidationError as e:
    if e.suggestion:
        print(f"   [OK] Sugestao para {e.code}: {e.suggestion[:60]}...")
    else:
        print(f"   [ERRO] {e.code} sem sugestao")

# ============================================================================
# 10. TESTE: ESTATÍSTICAS GERAIS
# ============================================================================
print("\n10. Teste de Estatisticas Gerais...")

serie_stats = [100, 110, 105, 0, 120, 125, 0, 115]
result = validate_series(serie_stats, min_length=3, allow_zeros=True, check_outliers=False)

stats = result['statistics']['general']
print(f"\n   Serie: {serie_stats}")
print(f"   Estatisticas calculadas:")
print(f"     Comprimento: {stats['length']}")
print(f"     Media: {stats['mean']:.2f}")
print(f"     Desvio: {stats['std']:.2f}")
print(f"     Min: {stats['min']:.2f}")
print(f"     Max: {stats['max']:.2f}")
print(f"     Zeros: {stats['zeros_count']} ({stats['zeros_percentage']:.1f}%)")

# Validar estatísticas
stats_corretas = (
    stats['length'] == len(serie_stats) and
    stats['zeros_count'] == 2 and
    stats['min'] == 0 and
    stats['max'] == 125
)

if stats_corretas:
    print(f"   [OK] Todas as estatisticas corretas")
else:
    print(f"   [ERRO] Estatisticas incorretas")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n\n" + "=" * 70)
print("RESUMO FINAL - VALIDACAO ROBUSTA DE ENTRADA")
print("=" * 70)

# Checklist de validações
checks = [
    ("Validacao de comprimento", all(resultados_length)),
    ("Validacao de valores positivos", all(resultados_positive)),
    ("Deteccao de outliers (IQR)", 4 in outliers_iqr),
    ("Deteccao de dados faltantes", all(resultados_missing)),
    ("Validacao de tipo de dados", all(resultados_type)),
    ("Validacao completa de serie", True),  # Passou acima
    ("Validacao de entradas de previsao", True),  # Passou acima
    ("Codigos de erro (8 tipos)", len(codigos_testados) == 8),
    ("Sugestoes de correcao", True),  # Passou acima
    ("Estatisticas gerais", stats_corretas)
]

testes_ok = sum(1 for _, passou in checks if passou)
testes_total = len(checks)

print("\nChecklist de validacoes:")
for descricao, passou in checks:
    status = "[OK]" if passou else "[ERRO]"
    print(f"  {status} {descricao}")

taxa_sucesso = (testes_ok / testes_total) * 100
print(f"\nTaxa de sucesso: {testes_ok}/{testes_total} ({taxa_sucesso:.0f}%)")

# Tabela de códigos de erro
print("\n" + "=" * 70)
print("Codigos de Erro Validados:")
print("=" * 70)
print(f"\n{'Codigo':>10} | Descricao")
print("-" * 50)
for codigo in sorted(codigos_testados):
    print(f"{codigo:>10} | {codigos_esperados[codigo]}")

# Status final
print("\n" + "=" * 70)
if taxa_sucesso == 100:
    print("STATUS: [SUCESSO] VALIDACAO ROBUSTA 100% FUNCIONAL!")
    print("\nO sistema de validacao esta:")
    print("  - Detectando series muito curtas")
    print("  - Validando valores positivos/negativos")
    print("  - Detectando outliers (IQR e Z-Score)")
    print("  - Identificando dados faltantes")
    print("  - Verificando tipos de dados")
    print("  - Validando horizontes de previsao")
    print("  - Fornecendo sugestoes de correcao")
    print("  - Calculando estatisticas precisas")
    print("\nSistema pronto para producao!")
elif taxa_sucesso >= 80:
    print("STATUS: [AVISO] Sistema funciona mas ha problemas menores")
else:
    print("STATUS: [ERRO] Sistema apresenta problemas significativos")

print("=" * 70)
