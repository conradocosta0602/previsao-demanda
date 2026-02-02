"""
Script para validar as melhorias implementadas:
1. Janela adaptativa no WMA
2. Validação robusta de entrada
3. Logging de seleção AUTO
"""

import sys
import io
sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.forecasting_models import get_modelo, WeightedMovingAverage, AutoMethodSelector
from core.validation import validate_series, ValidationError
from core.auto_logger import get_auto_logger

print("=" * 80)
print("VALIDAÇÃO DAS MELHORIAS IMPLEMENTADAS")
print("=" * 80)

# ========================================
# TESTE 1: Janela Adaptativa no WMA
# ========================================
print("\n✅ TESTE 1: Janela Adaptativa no WMA")
print("-" * 80)

cenarios_wma = [
    {'dados': [100, 102, 99], 'janela_esperada': 3, 'nome': '3 meses'},
    {'dados': [100] * 6, 'janela_esperada': 3, 'nome': '6 meses'},
    {'dados': [100] * 12, 'janela_esperada': 6, 'nome': '12 meses'},
    {'dados': [100] * 24, 'janela_esperada': 12, 'nome': '24 meses'},
]

erros_wma = 0
for cenario in cenarios_wma:
    try:
        modelo = get_modelo('WMA')  # window=None por padrão (adaptativo)
        modelo.fit(cenario['dados'])

        janela_obtida = modelo.params['window']
        window_type = modelo.params['window_type']

        if janela_obtida == cenario['janela_esperada'] and window_type == 'adaptive':
            print(f"  ✓ {cenario['nome']}: janela={janela_obtida} (esperado={cenario['janela_esperada']}) - CORRETO")
        else:
            print(f"  ✗ {cenario['nome']}: janela={janela_obtida} (esperado={cenario['janela_esperada']}) - ERRO")
            erros_wma += 1
    except Exception as e:
        print(f"  ✗ {cenario['nome']}: ERRO - {e}")
        erros_wma += 1

# Testar modo fixo (compatibilidade retroativa)
print("\n  Testando modo fixo (compatibilidade):")
try:
    modelo_fixo = get_modelo('WMA', window=5)
    modelo_fixo.fit([100] * 12)

    if modelo_fixo.params['window'] == 5 and modelo_fixo.params['window_type'] == 'fixed':
        print(f"  ✓ Modo fixo: window=5, type=fixed - CORRETO")
    else:
        print(f"  ✗ Modo fixo: ERRO")
        erros_wma += 1
except Exception as e:
    print(f"  ✗ Modo fixo: ERRO - {e}")
    erros_wma += 1

if erros_wma == 0:
    print("\n  ✅ TESTE 1 PASSOU: Janela adaptativa no WMA funcionando corretamente!")
else:
    print(f"\n  ❌ TESTE 1 FALHOU: {erros_wma} erro(s) encontrado(s)")

# ========================================
# TESTE 2: Validação Robusta de Entrada
# ========================================
print("\n\n✅ TESTE 2: Validação Robusta de Entrada")
print("-" * 80)

erros_validacao = 0

# Teste 2.1: Série muito curta
print("\n  2.1. Testando detecção de série muito curta:")
try:
    from core.validation import validate_series_length
    validate_series_length([100, 101], min_length=3)
    print("  ✗ Deveria ter lançado ValidationError para série curta")
    erros_validacao += 1
except ValidationError as e:
    if e.code == 'ERR001':
        print(f"  ✓ ValidationError detectado: [{e.code}] {e.message}")
    else:
        print(f"  ✗ Código de erro errado: {e.code}")
        erros_validacao += 1
except Exception as e:
    print(f"  ✗ Erro inesperado: {e}")
    erros_validacao += 1

# Teste 2.2: Valores negativos
print("\n  2.2. Testando detecção de valores negativos:")
try:
    from core.validation import validate_positive_values
    validate_positive_values([100, 102, -50, 99])
    print("  ✗ Deveria ter lançado ValidationError para valores negativos")
    erros_validacao += 1
except ValidationError as e:
    if e.code == 'ERR002':
        print(f"  ✓ ValidationError detectado: [{e.code}] {e.message}")
    else:
        print(f"  ✗ Código de erro errado: {e.code}")
        erros_validacao += 1
except Exception as e:
    print(f"  ✗ Erro inesperado: {e}")
    erros_validacao += 1

# Teste 2.3: Detecção de outliers
print("\n  2.3. Testando detecção de outliers:")
try:
    from core.validation import detect_outliers
    # Dados com outlier claro: 500 entre valores ~100
    dados = [100, 102, 99, 101, 500, 100, 103, 97]
    outliers, stats = detect_outliers(dados, method='iqr', threshold=1.5)

    if len(outliers) > 0 and 4 in outliers:  # índice 4 = valor 500
        print(f"  ✓ Outlier detectado no índice {outliers}: {[dados[i] for i in outliers]}")
    else:
        print(f"  ✗ Outlier não detectado corretamente")
        erros_validacao += 1
except Exception as e:
    print(f"  ✗ Erro: {e}")
    erros_validacao += 1

# Teste 2.4: Validação completa
print("\n  2.4. Testando validação completa de série:")
try:
    dados_validos = [98, 102, 99, 101, 100, 103, 97, 102, 99, 100, 101, 98]
    resultado = validate_series(dados_validos, min_length=3)

    if resultado['valid'] and 'statistics' in resultado:
        print(f"  ✓ Validação passou:")
        print(f"    - Comprimento: {resultado['statistics']['general']['length']}")
        print(f"    - Média: {resultado['statistics']['general']['mean']:.2f}")
        print(f"    - Desvio: {resultado['statistics']['general']['std']:.2f}")
    else:
        print(f"  ✗ Validação falhou inesperadamente")
        erros_validacao += 1
except Exception as e:
    print(f"  ✗ Erro: {e}")
    erros_validacao += 1

# Teste 2.5: Integração com AUTO
print("\n  2.5. Testando integração de validação com AUTO:")
try:
    # Tentar criar AUTO com dados inválidos (muito curtos)
    modelo_auto = AutoMethodSelector()
    modelo_auto.fit([100])  # Apenas 1 valor (inválido)
    print("  ✗ AUTO deveria ter lançado ValidationError para dados insuficientes")
    erros_validacao += 1
except ValidationError as e:
    print(f"  ✓ AUTO rejeitou dados inválidos: [{e.code}] {e.message[:80]}...")
except Exception as e:
    print(f"  ✗ Erro inesperado: {type(e).__name__}: {e}")
    erros_validacao += 1

if erros_validacao == 0:
    print("\n  ✅ TESTE 2 PASSOU: Validação robusta funcionando corretamente!")
else:
    print(f"\n  ❌ TESTE 2 FALHOU: {erros_validacao} erro(s) encontrado(s)")

# ========================================
# TESTE 3: Logging de Seleção AUTO
# ========================================
print("\n\n✅ TESTE 3: Logging de Seleção AUTO")
print("-" * 80)

erros_logging = 0

# Teste 3.1: Criar modelo AUTO e verificar se registra no log
print("\n  3.1. Testando registro de seleção AUTO:")
try:
    # Limpar logs anteriores do teste (se existirem)
    logger = get_auto_logger()

    # Criar AUTO com dados válidos
    dados_teste = [100, 102, 99, 101, 100, 103, 97, 102, 99, 100, 101, 98]
    modelo_auto = AutoMethodSelector(sku='PROD_001', loja='LOJA_01')
    modelo_auto.fit(dados_teste)

    # Verificar se foi registrado
    recent_logs = logger.get_recent_selections(limit=1)

    if len(recent_logs) > 0:
        ultimo_log = recent_logs[0]
        print(f"  ✓ Seleção registrada no log:")
        print(f"    - SKU: {ultimo_log['sku']}")
        print(f"    - Loja: {ultimo_log['loja']}")
        print(f"    - Método: {ultimo_log['metodo_selecionado']}")
        print(f"    - Confiança: {ultimo_log['confianca']:.2f}")
        print(f"    - Razão: {ultimo_log['razao'][:60]}...")
    else:
        print(f"  ✗ Nenhum log encontrado")
        erros_logging += 1

except Exception as e:
    print(f"  ✗ Erro: {e}")
    import traceback
    traceback.print_exc()
    erros_logging += 1

# Teste 3.2: Verificar consulta por SKU
print("\n  3.2. Testando consulta de logs por SKU:")
try:
    logger = get_auto_logger()
    logs_sku = logger.get_selections_by_sku('PROD_001', 'LOJA_01')

    if len(logs_sku) > 0:
        print(f"  ✓ Encontrados {len(logs_sku)} log(s) para PROD_001/LOJA_01")
    else:
        print(f"  ✗ Nenhum log encontrado para SKU especificado")
        erros_logging += 1

except Exception as e:
    print(f"  ✗ Erro: {e}")
    erros_logging += 1

# Teste 3.3: Estatísticas dos métodos
print("\n  3.3. Testando estatísticas de métodos selecionados:")
try:
    # Criar mais algumas seleções
    for i in range(3):
        dados = [100 + i] * 12
        modelo = AutoMethodSelector(sku=f'PROD_00{i+2}', loja='LOJA_01')
        modelo.fit(dados)

    logger = get_auto_logger()
    stats = logger.get_method_statistics()

    print(f"  ✓ Estatísticas obtidas:")
    print(f"    - Total de seleções: {stats['total_selections']}")
    print(f"    - Métodos usados: {list(stats['method_counts'].keys())}")

    if stats['total_selections'] > 0:
        for metodo, count in stats['method_counts'].items():
            pct = stats['method_percentages'][metodo]
            print(f"      • {metodo}: {count} ({pct:.1f}%)")

except Exception as e:
    print(f"  ✗ Erro: {e}")
    erros_logging += 1

# Teste 3.4: Logging de erro
print("\n  3.4. Testando logging de erro (dados inválidos):")
try:
    modelo_invalido = AutoMethodSelector(sku='PROD_ERRO', loja='LOJA_ERRO')
    try:
        modelo_invalido.fit([100])  # Dados insuficientes
    except ValidationError:
        pass  # Esperado

    # Verificar se o erro foi registrado
    logger = get_auto_logger()
    logs_erro = logger.get_selections_by_sku('PROD_ERRO', 'LOJA_ERRO')

    if len(logs_erro) > 0 and logs_erro[0]['sucesso'] == 0:
        print(f"  ✓ Erro registrado no log:")
        print(f"    - Erro: {logs_erro[0]['erro_msg'][:70]}...")
    else:
        print(f"  ✗ Erro não foi registrado corretamente")
        erros_logging += 1

except Exception as e:
    print(f"  ✗ Erro inesperado: {e}")
    erros_logging += 1

if erros_logging == 0:
    print("\n  ✅ TESTE 3 PASSOU: Logging de seleção AUTO funcionando corretamente!")
else:
    print(f"\n  ❌ TESTE 3 FALHOU: {erros_logging} erro(s) encontrado(s)")

# ========================================
# RESUMO FINAL
# ========================================
print("\n" + "=" * 80)
print("RESUMO DA VALIDAÇÃO")
print("=" * 80)

total_erros = erros_wma + erros_validacao + erros_logging

print(f"\n📊 Resultados:")
print(f"  1. Janela Adaptativa WMA: {'✅ PASSOU' if erros_wma == 0 else f'❌ {erros_wma} erro(s)'}")
print(f"  2. Validação Robusta: {'✅ PASSOU' if erros_validacao == 0 else f'❌ {erros_validacao} erro(s)'}")
print(f"  3. Logging AUTO: {'✅ PASSOU' if erros_logging == 0 else f'❌ {erros_logging} erro(s)'}")

if total_erros == 0:
    print(f"\n🎉 TODAS AS MELHORIAS IMPLEMENTADAS E VALIDADAS COM SUCESSO!")
    print("\n📝 Melhorias implementadas:")
    print("  ✓ WMA agora usa janela adaptativa N = max(3, total_períodos / 2)")
    print("  ✓ Validação robusta com códigos de erro estruturados (ERR001-ERR008)")
    print("  ✓ Logging completo de todas as seleções AUTO em banco SQLite")
    print("  ✓ Auditoria e rastreabilidade total das decisões do sistema")
else:
    print(f"\n⚠️ {total_erros} ERRO(S) ENCONTRADO(S) - Revisar implementação")

print("\n📄 Arquivos criados/modificados:")
print("  - core/forecasting_models.py (WMA adaptativo + validação integrada)")
print("  - core/validation.py (módulo de validação robusta)")
print("  - core/auto_logger.py (logging de seleções AUTO)")
print("  - outputs/auto_selection_log.db (banco de dados de logs)")
