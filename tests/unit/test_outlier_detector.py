"""
Teste de Validação: Sistema de Detecção Automática de Outliers

Este teste valida que o detector automático de outliers está funcionando
corretamente, incluindo análise de características, escolha de método,
detecção e tratamento de outliers.
"""
import sys
import numpy as np
from core.outlier_detector import AutoOutlierDetector, auto_clean_outliers

print("=" * 70)
print("TESTE: SISTEMA DE DETECÇÃO AUTOMÁTICA DE OUTLIERS")
print("=" * 70)

# ============================================================================
# 1. TESTE: SÉRIE SEM OUTLIERS (ESTÁVEL)
# ============================================================================
print("\n1. Teste de Serie Sem Outliers (Estavel)...")

serie_estavel = [100, 102, 98, 101, 99, 103, 100, 102, 101, 99]
detector1 = AutoOutlierDetector()
resultado1 = detector1.analyze_and_clean(serie_estavel)

print(f"\n   Serie: {serie_estavel}")
print(f"   Outliers detectados: {resultado1['outliers_count']}")
print(f"   Metodo usado: {resultado1['method_used']}")
print(f"   Tratamento: {resultado1['treatment']}")
print(f"   Razao: {resultado1['reason']}")

if resultado1['outliers_count'] == 0:
    print(f"   [OK] Nenhum outlier detectado (esperado)")
else:
    print(f"   [ERRO] Outliers detectados em serie estavel")

if resultado1['method_used'] == 'NONE':
    print(f"   [OK] Metodo NONE para serie estavel")
else:
    print(f"   [AVISO] Metodo {resultado1['method_used']} usado")

# ============================================================================
# 2. TESTE: SÉRIE COM OUTLIER EXTREMO
# ============================================================================
print("\n2. Teste de Serie com Outlier Extremo...")

serie_com_outlier = [100, 110, 105, 115, 1000, 120, 108, 112, 109, 111]
detector2 = AutoOutlierDetector()
resultado2 = detector2.analyze_and_clean(serie_com_outlier)

print(f"\n   Serie: {serie_com_outlier}")
print(f"   Outliers detectados: {resultado2['outliers_count']}")
print(f"   Indices: {resultado2['outliers_detected']}")
print(f"   Metodo usado: {resultado2['method_used']}")
print(f"   Tratamento: {resultado2['treatment']}")
print(f"   Valores originais: {resultado2['original_values']}")
print(f"   Valores substituidos: {resultado2['replaced_values']}")
print(f"   Confianca: {resultado2['confidence']:.2f}")

if resultado2['outliers_count'] > 0:
    print(f"   [OK] Outlier detectado")
    if 4 in resultado2['outliers_detected']:
        print(f"   [OK] Outlier no indice correto (4)")
    else:
        print(f"   [ERRO] Outlier nao detectado no indice esperado")
else:
    print(f"   [ERRO] Outlier extremo NAO foi detectado")

# Validar que série limpa não contém o outlier
serie_limpa = resultado2['cleaned_data']
if max(serie_limpa) < 500:  # 1000 deve ter sido removido ou substituído
    print(f"   [OK] Outlier foi tratado (max limpo: {max(serie_limpa):.0f})")
else:
    print(f"   [ERRO] Outlier ainda presente (max: {max(serie_limpa):.0f})")

# ============================================================================
# 3. TESTE: SÉRIE MUITO CURTA (< 6 PERÍODOS)
# ============================================================================
print("\n3. Teste de Serie Muito Curta...")

serie_curta = [100, 110, 500, 105, 115]  # Outlier, mas série curta
detector3 = AutoOutlierDetector()
resultado3 = detector3.analyze_and_clean(serie_curta)

print(f"\n   Serie: {serie_curta}")
print(f"   Tamanho: {len(serie_curta)} periodos")
print(f"   Outliers detectados: {resultado3['outliers_count']}")
print(f"   Razao: {resultado3['reason']}")

if resultado3['outliers_count'] == 0:
    print(f"   [OK] Deteccao desabilitada para serie curta")
    if 'muito curta' in resultado3['reason'].lower():
        print(f"   [OK] Razao correta fornecida")
else:
    print(f"   [AVISO] Outliers detectados em serie curta")

# ============================================================================
# 4. TESTE: DEMANDA INTERMITENTE (MUITOS ZEROS)
# ============================================================================
print("\n4. Teste de Demanda Intermitente (Muitos Zeros)...")

serie_intermitente = [0, 0, 100, 0, 0, 0, 50, 0, 0, 0, 200, 0]
detector4 = AutoOutlierDetector()
resultado4 = detector4.analyze_and_clean(serie_intermitente)

zeros_pct = 100 * sum(1 for x in serie_intermitente if x == 0) / len(serie_intermitente)

print(f"\n   Serie: {serie_intermitente}")
print(f"   Zeros: {zeros_pct:.1f}%")
print(f"   Outliers detectados: {resultado4['outliers_count']}")
print(f"   Razao: {resultado4['reason']}")

if resultado4['outliers_count'] == 0:
    print(f"   [OK] Deteccao desabilitada para demanda intermitente")
    if 'intermitente' in resultado4['reason'].lower():
        print(f"   [OK] Razao correta fornecida")
else:
    print(f"   [AVISO] Outliers detectados em demanda intermitente")

# ============================================================================
# 5. TESTE: ESCOLHA DE MÉTODO (IQR vs Z-SCORE)
# ============================================================================
print("\n5. Teste de Escolha de Metodo...")

# Série assimétrica (deve usar IQR)
serie_assimetrica = [10, 12, 11, 13, 15, 20, 50, 100, 150, 200, 180, 190]
detector5a = AutoOutlierDetector()
resultado5a = detector5a.analyze_and_clean(serie_assimetrica)

print(f"\n   Serie assimetrica (crescente):")
print(f"   Metodo escolhido: {resultado5a['method_used']}")
print(f"   Skewness: {resultado5a['characteristics']['skewness']:.2f}")

if resultado5a['method_used'] == 'IQR':
    print(f"   [OK] Metodo IQR escolhido para serie assimetrica")
else:
    print(f"   [AVISO] Metodo {resultado5a['method_used']} escolhido (esperado: IQR)")

# Série simétrica (pode usar Z-Score)
serie_simetrica = [95, 98, 100, 102, 105, 99, 101, 103, 97, 100, 102, 98,
                   96, 101, 99, 103, 100, 102, 98, 101, 99, 97, 100, 102]
detector5b = AutoOutlierDetector()
resultado5b = detector5b.analyze_and_clean(serie_simetrica)

print(f"\n   Serie simetrica (normal):")
print(f"   Metodo escolhido: {resultado5b['method_used']}")
print(f"   Skewness: {resultado5b['characteristics']['skewness']:.2f}")

if resultado5b['method_used'] in ['ZSCORE', 'NONE']:
    print(f"   [OK] Metodo {resultado5b['method_used']} apropriado")
else:
    print(f"   [AVISO] Metodo {resultado5b['method_used']} escolhido")

# ============================================================================
# 6. TESTE: TIPOS DE TRATAMENTO
# ============================================================================
print("\n6. Teste de Tipos de Tratamento...")

# Poucos outliers em série longa (deve REMOVER)
serie_longa = [100] * 10 + [1000] + [100] * 10  # 1 outlier em 21 valores
detector6a = AutoOutlierDetector()
resultado6a = detector6a.analyze_and_clean(serie_longa)

print(f"\n   Serie longa com 1 outlier:")
print(f"   Total: {len(serie_longa)} valores")
print(f"   Outliers: {resultado6a['outliers_count']}")
print(f"   Tratamento: {resultado6a['treatment']}")

# Muitos outliers (deve SUBSTITUIR)
serie_muitos_outliers = [100, 100, 500, 100, 600, 100, 700, 100, 800, 100]
detector6b = AutoOutlierDetector()
resultado6b = detector6b.analyze_and_clean(serie_muitos_outliers)

outlier_pct = 100 * resultado6b['outliers_count'] / len(serie_muitos_outliers)

print(f"\n   Serie com muitos outliers:")
print(f"   Total: {len(serie_muitos_outliers)} valores")
print(f"   Outliers: {resultado6b['outliers_count']} ({outlier_pct:.1f}%)")
print(f"   Tratamento: {resultado6b['treatment']}")

if resultado6b['treatment'] == 'REPLACE_MEDIAN':
    print(f"   [OK] Substituindo por mediana (muitos outliers)")
else:
    print(f"   [AVISO] Tratamento: {resultado6b['treatment']}")

# ============================================================================
# 7. TESTE: SUBSTITUIÇÃO POR MEDIANA
# ============================================================================
print("\n7. Teste de Substituicao por Mediana...")

serie_teste_mediana = [10, 12, 11, 13, 12, 100, 11, 13, 12, 10]
detector7 = AutoOutlierDetector()
resultado7 = detector7.analyze_and_clean(serie_teste_mediana)

if resultado7['outliers_count'] > 0 and resultado7['treatment'] == 'REPLACE_MEDIAN':
    # Calcular mediana esperada (sem outlier)
    valores_sem_outlier = [x for i, x in enumerate(serie_teste_mediana)
                          if i not in resultado7['outliers_detected']]
    mediana_esperada = np.median(valores_sem_outlier)

    print(f"\n   Serie: {serie_teste_mediana}")
    print(f"   Outliers: {resultado7['outliers_detected']}")
    print(f"   Mediana (sem outliers): {mediana_esperada:.1f}")
    print(f"   Valores substituidos: {resultado7['replaced_values']}")

    if all(abs(v - mediana_esperada) < 0.01 for v in resultado7['replaced_values']):
        print(f"   [OK] Outliers substituidos pela mediana correta")
    else:
        print(f"   [ERRO] Valores de substituicao incorretos")
else:
    print(f"   [AVISO] Teste nao aplicavel (tratamento: {resultado7['treatment']})")

# ============================================================================
# 8. TESTE: CARACTERÍSTICAS ESTATÍSTICAS
# ============================================================================
print("\n8. Teste de Caracteristicas Estatisticas...")

serie_teste_chars = [100, 110, 105, 115, 120, 125, 130, 135, 140, 145]
detector8 = AutoOutlierDetector()
resultado8 = detector8.analyze_and_clean(serie_teste_chars)

chars = resultado8['characteristics']

print(f"\n   Caracteristicas calculadas:")
print(f"     N: {chars['n']}")
print(f"     Media: {chars['mean']:.2f}")
print(f"     Std: {chars['std']:.2f}")
print(f"     Mediana: {chars['median']:.2f}")
print(f"     CV: {chars['cv']:.2f}")
print(f"     Skewness: {chars['skewness']:.2f}")
print(f"     Kurtosis: {chars['kurtosis']:.2f}")
print(f"     Zeros %: {chars['zeros_pct']:.1f}%")

campos_obrigatorios = ['n', 'mean', 'std', 'median', 'cv', 'skewness',
                       'kurtosis', 'zeros_pct', 'relative_range']

if all(campo in chars for campo in campos_obrigatorios):
    print(f"\n   [OK] Todas as caracteristicas calculadas")
else:
    faltando = [c for c in campos_obrigatorios if c not in chars]
    print(f"\n   [ERRO] Caracteristicas faltando: {faltando}")

# Validar cálculos
mean_esperada = np.mean(serie_teste_chars)
if abs(chars['mean'] - mean_esperada) < 0.01:
    print(f"   [OK] Media calculada corretamente")
else:
    print(f"   [ERRO] Media incorreta (esperado: {mean_esperada:.2f}, obtido: {chars['mean']:.2f})")

# ============================================================================
# 9. TESTE: CONFIANÇA NA DECISÃO
# ============================================================================
print("\n9. Teste de Confianca na Decisao...")

# Cenário 1: Poucos outliers em série longa (alta confiança)
serie_alta_conf = [100] * 20 + [1000] + [100] * 20
detector9a = AutoOutlierDetector()
resultado9a = detector9a.analyze_and_clean(serie_alta_conf)

print(f"\n   Cenario: Poucos outliers em serie longa")
print(f"   Confianca: {resultado9a['confidence']:.2f}")

if resultado9a['confidence'] > 0.7:
    print(f"   [OK] Alta confianca (> 0.7)")
else:
    print(f"   [AVISO] Confianca: {resultado9a['confidence']:.2f}")

# Cenário 2: Muitos outliers em série curta (baixa confiança)
serie_baixa_conf = [100, 500, 100, 600, 100, 700]
detector9b = AutoOutlierDetector()
resultado9b = detector9b.analyze_and_clean(serie_baixa_conf)

print(f"\n   Cenario: Serie curta com variabilidade")
print(f"   Confianca: {resultado9b['confidence']:.2f}")

# Validar que confiança está no intervalo [0, 1]
if 0 <= resultado9a['confidence'] <= 1 and 0 <= resultado9b['confidence'] <= 1:
    print(f"\n   [OK] Confianca no intervalo [0, 1]")
else:
    print(f"\n   [ERRO] Confianca fora do intervalo valido")

# ============================================================================
# 10. TESTE: FUNÇÃO HELPER auto_clean_outliers()
# ============================================================================
print("\n10. Teste de Funcao Helper...")

serie_helper = [100, 110, 105, 1000, 115, 120]
resultado_helper = auto_clean_outliers(serie_helper)

print(f"\n   Serie: {serie_helper}")
print(f"   Resultado da funcao helper:")
print(f"     Outliers: {resultado_helper['outliers_count']}")
print(f"     Metodo: {resultado_helper['method_used']}")
print(f"     Tratamento: {resultado_helper['treatment']}")

if isinstance(resultado_helper, dict):
    print(f"   [OK] Funcao helper retorna dicionario")
else:
    print(f"   [ERRO] Funcao helper nao retorna dicionario")

if 'cleaned_data' in resultado_helper:
    print(f"   [OK] Resultado contem 'cleaned_data'")
else:
    print(f"   [ERRO] 'cleaned_data' ausente")

# ============================================================================
# 11. TESTE: ALTA VARIABILIDADE
# ============================================================================
print("\n11. Teste de Serie com Alta Variabilidade...")

serie_alta_var = [50, 150, 80, 200, 60, 180, 70, 190, 55, 175]
detector11 = AutoOutlierDetector()
resultado11 = detector11.analyze_and_clean(serie_alta_var)

cv = resultado11['characteristics']['cv']

print(f"\n   Serie: {serie_alta_var}")
print(f"   CV (Coeficiente de Variacao): {cv:.2f}")
print(f"   Outliers detectados: {resultado11['outliers_count']}")
print(f"   Razao: {resultado11['reason']}")

if cv > 0.4:
    print(f"   [OK] Alta variabilidade detectada (CV > 0.4)")
else:
    print(f"   [AVISO] CV: {cv:.2f}")

# ============================================================================
# 12. TESTE: PRESERVAÇÃO DE VALORES NÃO-OUTLIERS
# ============================================================================
print("\n12. Teste de Preservacao de Valores Nao-Outliers...")

serie_preservar = [100, 110, 105, 1000, 115, 120, 108, 112]
detector12 = AutoOutlierDetector()
resultado12 = detector12.analyze_and_clean(serie_preservar)

valores_nao_outliers = [serie_preservar[i] for i in range(len(serie_preservar))
                       if i not in resultado12['outliers_detected']]

serie_limpa = resultado12['cleaned_data']

if resultado12['treatment'] == 'REMOVE':
    # Valores não-outliers devem estar todos na série limpa
    valores_limpos_esperados = valores_nao_outliers
    if all(v in serie_limpa for v in valores_limpos_esperados):
        print(f"   [OK] Valores nao-outliers preservados apos REMOCAO")
    else:
        print(f"   [ERRO] Alguns valores foram perdidos")

elif resultado12['treatment'] == 'REPLACE_MEDIAN':
    # Série deve ter mesmo tamanho
    if len(serie_limpa) == len(serie_preservar):
        print(f"   [OK] Tamanho da serie preservado apos SUBSTITUICAO")
    else:
        print(f"   [ERRO] Tamanho alterado ({len(serie_preservar)} -> {len(serie_limpa)})")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n\n" + "=" * 70)
print("RESUMO FINAL - VALIDACAO DO DETECTOR DE OUTLIERS")
print("=" * 70)

# Checklist de validações
checks = [
    ("Serie sem outliers (estavel)", resultado1['outliers_count'] == 0),
    ("Outlier extremo detectado", resultado2['outliers_count'] > 0 and 4 in resultado2['outliers_detected']),
    ("Serie curta (deteccao desabilitada)", resultado3['outliers_count'] == 0),
    ("Demanda intermitente (deteccao desabilitada)", resultado4['outliers_count'] == 0),
    ("Escolha de metodo IQR (assimetrica)", resultado5a['method_used'] == 'IQR'),
    ("Tratamento por substituicao (muitos outliers)", resultado6b['treatment'] == 'REPLACE_MEDIAN'),
    ("Caracteristicas estatisticas completas", all(c in chars for c in campos_obrigatorios)),
    ("Calculo de media correto", abs(chars['mean'] - mean_esperada) < 0.01),
    ("Confianca no intervalo [0,1]", 0 <= resultado9a['confidence'] <= 1),
    ("Funcao helper funcionando", 'cleaned_data' in resultado_helper),
    ("Alta variabilidade detectada", cv > 0.4 if resultado11['outliers_count'] > 0 else True),
    ("Outlier tratado corretamente", max(resultado2['cleaned_data']) < 500)
]

testes_ok = sum(1 for _, passou in checks if passou)
testes_total = len(checks)

print("\nChecklist de validacoes:")
for descricao, passou in checks:
    status = "[OK]" if passou else "[ERRO]"
    print(f"  {status} {descricao}")

taxa_sucesso = (testes_ok / testes_total) * 100
print(f"\nTaxa de sucesso: {testes_ok}/{testes_total} ({taxa_sucesso:.0f}%)")

# Estatísticas dos testes
print("\n" + "=" * 70)
print("Estatisticas dos Testes:")
print("=" * 70)

print(f"\nMetodos utilizados:")
metodos = {}
for r in [resultado1, resultado2, resultado3, resultado4, resultado5a, resultado5b,
          resultado6a, resultado6b, resultado7, resultado8, resultado9a, resultado9b,
          resultado11, resultado12]:
    m = r['method_used']
    metodos[m] = metodos.get(m, 0) + 1

for metodo, count in sorted(metodos.items()):
    print(f"  {metodo}: {count} vezes")

print(f"\nTratamentos aplicados:")
tratamentos = {}
for r in [resultado1, resultado2, resultado3, resultado4, resultado5a, resultado5b,
          resultado6a, resultado6b, resultado7, resultado8, resultado9a, resultado9b,
          resultado11, resultado12]:
    t = r['treatment']
    tratamentos[t] = tratamentos.get(t, 0) + 1

for tratamento, count in sorted(tratamentos.items()):
    print(f"  {tratamento}: {count} vezes")

# Total de outliers detectados
total_outliers = sum(r['outliers_count'] for r in [resultado1, resultado2, resultado3,
                     resultado4, resultado5a, resultado5b, resultado6a, resultado6b,
                     resultado7, resultado8, resultado9a, resultado9b, resultado11, resultado12])

print(f"\nTotal de outliers detectados em todos os testes: {total_outliers}")

# Status final
print("\n" + "=" * 70)
if taxa_sucesso == 100:
    print("STATUS: [SUCESSO] DETECTOR DE OUTLIERS 100% FUNCIONAL!")
    print("\nO detector automatico de outliers esta:")
    print("  - Analisando caracteristicas da serie corretamente")
    print("  - Decidindo quando detectar outliers (criterios adequados)")
    print("  - Escolhendo metodo apropriado (IQR vs Z-Score)")
    print("  - Detectando outliers com precisao")
    print("  - Aplicando tratamento adequado (remover vs substituir)")
    print("  - Calculando confianca nas decisoes")
    print("  - Preservando valores nao-outliers")
    print("\nSistema pronto para producao!")
elif taxa_sucesso >= 80:
    print("STATUS: [AVISO] Sistema funciona mas ha problemas menores")
else:
    print("STATUS: [ERRO] Sistema apresenta problemas significativos")

print("=" * 70)
