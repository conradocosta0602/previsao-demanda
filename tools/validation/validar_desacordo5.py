"""
Script para validar a correção do desacordo 5 (Janela Adaptativa do SMA)
"""

import sys
import io
sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.forecasting_models import get_modelo

print("=" * 80)
print("VALIDAÇÃO DA CORREÇÃO - DESACORDO 5")
print("=" * 80)

print("\n[DESACORDO 5] Validando janela adaptativa do SMA...")
print("-" * 80)

# Cenários de teste conforme documentação (Seção 2.2)
cenarios = [
    {
        'nome': '3 meses de histórico',
        'dados': [100, 102, 99],
        'janela_esperada': 3,  # max(3, 3/2) = max(3, 1) = 3
        'formula': 'max(3, 3/2) = max(3, 1) = 3'
    },
    {
        'nome': '6 meses de histórico',
        'dados': [98, 102, 99, 101, 100, 103],
        'janela_esperada': 3,  # max(3, 6/2) = max(3, 3) = 3
        'formula': 'max(3, 6/2) = max(3, 3) = 3'
    },
    {
        'nome': '12 meses de histórico',
        'dados': [98, 102, 99, 101, 100, 103, 97, 102, 99, 100, 101, 98],
        'janela_esperada': 6,  # max(3, 12/2) = max(3, 6) = 6
        'formula': 'max(3, 12/2) = max(3, 6) = 6'
    },
    {
        'nome': '24 meses de histórico',
        'dados': [100] * 24,
        'janela_esperada': 12,  # max(3, 24/2) = max(3, 12) = 12
        'formula': 'max(3, 24/2) = max(3, 12) = 12'
    },
    {
        'nome': '36 meses de histórico',
        'dados': [100] * 36,
        'janela_esperada': 18,  # max(3, 36/2) = max(3, 18) = 18
        'formula': 'max(3, 36/2) = max(3, 18) = 18'
    }
]

resultados = []
erros = 0

print("\n✅ Testando janela adaptativa em diferentes cenários:")
print()

for cenario in cenarios:
    nome = cenario['nome']
    dados = cenario['dados']
    janela_esperada = cenario['janela_esperada']
    formula = cenario['formula']

    try:
        # Criar modelo SMA com janela adaptativa (window=None)
        modelo_sma = get_modelo('SMA', window=None)
        modelo_sma.fit(dados)

        # Obter janela calculada
        janela_obtida = modelo_sma.params['window']
        window_type = modelo_sma.params['window_type']

        # Verificar se é adaptativa
        if window_type == 'adaptive':
            tipo_status = "✓"
        else:
            tipo_status = "✗"
            erros += 1

        # Verificar se a janela está correta
        if janela_obtida == janela_esperada:
            janela_status = "✓"
        else:
            janela_status = "✗"
            erros += 1

        print(f"{tipo_status} {nome}:")
        print(f"  - Períodos totais: {len(dados)}")
        print(f"  - Fórmula: N = {formula}")
        print(f"  - Janela esperada: {janela_esperada}")
        print(f"  - Janela obtida: {janela_obtida} {janela_status}")
        print(f"  - Tipo: {window_type}")
        print()

        resultados.append({
            'nome': nome,
            'correto': janela_obtida == janela_esperada and window_type == 'adaptive'
        })

    except Exception as e:
        print(f"✗ {nome}: ERRO - {e}")
        erros += 1
        resultados.append({'nome': nome, 'correto': False})
        print()

# Testar também modo fixo (compatibilidade retroativa)
print("\n🔧 Testando modo fixo (compatibilidade retroativa):")
print("-" * 80)

try:
    dados_teste = [100, 102, 99, 101, 100, 103, 97, 102, 99, 100, 101, 98]
    modelo_fixo = get_modelo('SMA', window=4)
    modelo_fixo.fit(dados_teste)

    janela_fixo = modelo_fixo.params['window']
    tipo_fixo = modelo_fixo.params['window_type']

    if janela_fixo == 4 and tipo_fixo == 'fixed':
        print(f"✓ Modo fixo funcionando:")
        print(f"  - Janela definida: 4")
        print(f"  - Janela obtida: {janela_fixo}")
        print(f"  - Tipo: {tipo_fixo}")
    else:
        print(f"✗ Modo fixo NÃO está funcionando corretamente")
        erros += 1

except Exception as e:
    print(f"✗ Erro no modo fixo: {e}")
    erros += 1

# Testar previsão com janela adaptativa
print("\n📈 Testando previsão com janela adaptativa:")
print("-" * 80)

try:
    # Dados conforme documentação (Seção 2.2)
    vendas_doc = [98, 102, 99, 101, 100, 103, 97, 102, 99, 100, 101, 98]

    modelo_sma = get_modelo('SMA')  # window=None por padrão
    modelo_sma.fit(vendas_doc)
    previsao = modelo_sma.predict(1)[0]

    # Com 12 meses, janela adaptativa = 6
    # Últimos 6 meses: [97, 102, 99, 100, 101, 98]
    # SMA = (97 + 102 + 99 + 100 + 101 + 98) / 6 = 597 / 6 = 99.5
    previsao_esperada = 99.5

    diferenca = abs(previsao - previsao_esperada)

    print(f"✓ Teste de previsão:")
    print(f"  - Dados (12 meses): {vendas_doc}")
    print(f"  - Janela adaptativa: 6 (últimos 6 meses)")
    print(f"  - Últimos 6 meses: [97, 102, 99, 100, 101, 98]")
    print(f"  - Previsão esperada: {previsao_esperada}")
    print(f"  - Previsão obtida: {previsao:.2f}")
    print(f"  - Diferença: {diferenca:.3f}")

    if diferenca < 0.01:
        print(f"  ✓ Previsão correta!")
    else:
        print(f"  ✗ Previsão incorreta!")
        erros += 1

except Exception as e:
    print(f"✗ Erro ao testar previsão: {e}")
    import traceback
    traceback.print_exc()
    erros += 1

# Resumo
print("\n" + "=" * 80)
print("VALIDAÇÃO CONCLUÍDA")
print("=" * 80)

cenarios_corretos = sum(1 for r in resultados if r['correto'])
total_cenarios = len(resultados)

print(f"\n📋 RESUMO:")
print(f"  - Cenários testados: {total_cenarios}")
print(f"  - Cenários corretos: {cenarios_corretos}")
print(f"  - Erros encontrados: {erros}")

if erros == 0:
    print("\n✅ DESACORDO 5: CORRIGIDO COM SUCESSO!")
    print("\n📝 Implementação conforme documentação:")
    print("  - Janela adaptativa: N = max(3, total_períodos / 2)")
    print("  - 12 meses → janela de 6 meses")
    print("  - 24 meses → janela de 12 meses")
    print("  - Dados antigos automaticamente descartados")
else:
    print(f"\n⚠️ DESACORDO 5: AINDA PENDENTE ({erros} erro(s))")
