"""
Teste de Validação: Sistema de Alertas Inteligentes

Este teste valida que os alertas estão funcionando corretamente
para diferentes cenários de estoque, demanda e qualidade de dados.
"""
import sys
import numpy as np
from core.smart_alerts import SmartAlertGenerator

print("=" * 70)
print("TESTE: SISTEMA DE ALERTAS INTELIGENTES")
print("=" * 70)

# Criar gerador de alertas
generator = SmartAlertGenerator()

# ============================================================================
# 1. TESTE: ALERTA DE RUPTURA DE ESTOQUE
# ============================================================================
print("\n1. Teste de Alerta de Ruptura de Estoque...")

# Cenário: Estoque baixo, demanda alta
historico_ruptura = [100, 110, 105, 115, 120, 125]
previsao_ruptura = [130, 135, 140]
estoque_atual_ruptura = 50  # Muito baixo!

alertas_ruptura = generator.generate_alerts(
    sku='TEST001',
    loja='L001',
    historico=historico_ruptura,
    previsao=previsao_ruptura,
    modelo_info={},
    estoque_atual=estoque_atual_ruptura,
    lead_time_dias=7
)

# Validar que alerta de ruptura foi gerado
alertas_stockout = [a for a in alertas_ruptura if a['categoria'] == 'RUPTURA_ESTOQUE']

if len(alertas_stockout) > 0:
    alerta = alertas_stockout[0]
    print(f"   [OK] Alerta de ruptura detectado")
    print(f"        Tipo: {alerta['tipo']}")
    print(f"        Titulo: {alerta['titulo']}")
    print(f"        Mensagem: {alerta['mensagem'][:80]}...")
    print(f"        Acao: {alerta['acao_recomendada'][:60]}...")

    # Validar dados de contexto
    ctx = alerta['dados_contexto']
    if 'estoque_atual' in ctx and 'ponto_pedido' in ctx:
        print(f"        Estoque: {ctx['estoque_atual']:.0f} un")
        print(f"        Ponto de pedido: {ctx['ponto_pedido']:.0f} un")
        print(f"        Dias ate ruptura: {ctx.get('dias_ate_ruptura', 0):.0f}")
        print(f"   [OK] Dados de contexto presentes")
    else:
        print(f"   [ERRO] Dados de contexto ausentes")
else:
    print(f"   [ERRO] Alerta de ruptura NAO foi gerado!")

# ============================================================================
# 2. TESTE: ALERTA DE EXCESSO DE ESTOQUE
# ============================================================================
print("\n2. Teste de Alerta de Excesso de Estoque...")

# Cenário: Estoque muito alto, demanda baixa
historico_excesso = [50, 55, 48, 52, 50, 53]
previsao_excesso = [50, 50, 50]
estoque_atual_excesso = 500  # 10 meses de cobertura!
custo_unitario = 10.0

generator2 = SmartAlertGenerator()
alertas_excesso = generator2.generate_alerts(
    sku='TEST002',
    loja='L001',
    historico=historico_excesso,
    previsao=previsao_excesso,
    modelo_info={},
    estoque_atual=estoque_atual_excesso,
    lead_time_dias=7,
    custo_unitario=custo_unitario
)

alertas_overstock = [a for a in alertas_excesso if a['categoria'] == 'EXCESSO_ESTOQUE']

if len(alertas_overstock) > 0:
    alerta = alertas_overstock[0]
    print(f"   [OK] Alerta de excesso detectado")
    print(f"        Tipo: {alerta['tipo']}")
    print(f"        Titulo: {alerta['titulo']}")
    print(f"        Cobertura: {alerta['dados_contexto']['cobertura_meses']:.1f} meses")
    print(f"        Valor parado: R$ {alerta['dados_contexto']['valor_parado']:,.2f}")
else:
    print(f"   [ERRO] Alerta de excesso NAO foi gerado!")

# ============================================================================
# 3. TESTE: ALERTA DE CRESCIMENTO DE DEMANDA
# ============================================================================
print("\n3. Teste de Alerta de Crescimento de Demanda...")

# Cenário: Crescimento de 80% nos últimos 3 meses
historico_crescimento = [50, 55, 60, 100, 105, 110]
previsao_crescimento = [120, 130, 140]

generator3 = SmartAlertGenerator()
alertas_crescimento = generator3.generate_alerts(
    sku='TEST003',
    loja='L001',
    historico=historico_crescimento,
    previsao=previsao_crescimento,
    modelo_info={}
)

alertas_spike = [a for a in alertas_crescimento if a['categoria'] == 'PICO_DEMANDA']

if len(alertas_spike) > 0:
    alerta = alertas_spike[0]
    print(f"   [OK] Alerta de crescimento detectado")
    print(f"        Tipo: {alerta['tipo']}")
    print(f"        Variacao: {alerta['dados_contexto']['variacao_pct']:.1f}%")
    print(f"        Media anterior: {alerta['dados_contexto']['media_anterior']:.0f}")
    print(f"        Media atual: {alerta['dados_contexto']['media_atual']:.0f}")
else:
    print(f"   [ERRO] Alerta de crescimento NAO foi gerado!")

# ============================================================================
# 4. TESTE: ALERTA DE QUEDA DE DEMANDA
# ============================================================================
print("\n4. Teste de Alerta de Queda de Demanda...")

# Cenário: Queda de 50% nos últimos 3 meses
historico_queda = [200, 210, 205, 100, 95, 105]
previsao_queda = [90, 85, 90]

generator4 = SmartAlertGenerator()
alertas_queda = generator4.generate_alerts(
    sku='TEST004',
    loja='L001',
    historico=historico_queda,
    previsao=previsao_queda,
    modelo_info={}
)

alertas_drop = [a for a in alertas_queda if a['categoria'] == 'QUEDA_DEMANDA']

if len(alertas_drop) > 0:
    alerta = alertas_drop[0]
    print(f"   [OK] Alerta de queda detectado")
    print(f"        Tipo: {alerta['tipo']}")
    print(f"        Variacao: {alerta['dados_contexto']['variacao_pct']:.1f}%")
else:
    print(f"   [ERRO] Alerta de queda NAO foi gerado!")

# ============================================================================
# 5. TESTE: ALERTA DE BAIXA ACURÁCIA
# ============================================================================
print("\n5. Teste de Alerta de Baixa Acuracia...")

# Cenário: MAPE alto (40%)
historico_acuracia = [100, 110, 105, 115, 120]
previsao_acuracia = [125, 130, 135]

generator5 = SmartAlertGenerator()
alertas_acuracia = generator5.generate_alerts(
    sku='TEST005',
    loja='L001',
    historico=historico_acuracia,
    previsao=previsao_acuracia,
    modelo_info={'mape': 42.5}  # MAPE alto!
)

alertas_accuracy = [a for a in alertas_acuracia if a['categoria'] == 'ACURACIA']

if len(alertas_accuracy) > 0:
    alerta = alertas_accuracy[0]
    print(f"   [OK] Alerta de acuracia detectado")
    print(f"        Tipo: {alerta['tipo']}")
    print(f"        MAPE: {alerta['dados_contexto']['mape']:.1f}%")
    print(f"        Mensagem: {alerta['mensagem']}")
else:
    print(f"   [ERRO] Alerta de acuracia NAO foi gerado!")

# ============================================================================
# 6. TESTE: ALERTA DE ALTA QUALIDADE
# ============================================================================
print("\n6. Teste de Alerta de Alta Qualidade (Positivo)...")

# Cenário: MAPE excelente (5%)
generator6 = SmartAlertGenerator()
alertas_qualidade = generator6.generate_alerts(
    sku='TEST006',
    loja='L001',
    historico=[100]*12,  # Histórico longo
    previsao=[100]*6,
    modelo_info={'mape': 5.2}  # MAPE excelente!
)

alertas_success = [a for a in alertas_qualidade if a['tipo'] == 'SUCCESS']

if len(alertas_success) > 0:
    print(f"   [OK] Alertas positivos detectados: {len(alertas_success)}")
    for alerta in alertas_success:
        print(f"        - {alerta['titulo']}")
else:
    print(f"   [AVISO] Nenhum alerta positivo gerado")

# ============================================================================
# 7. TESTE: ALERTA DE DADOS LIMITADOS
# ============================================================================
print("\n7. Teste de Alerta de Dados Limitados...")

# Cenário: Apenas 3 meses de histórico
historico_curto = [100, 110, 105]
previsao_curto = [115, 120, 125]

generator7 = SmartAlertGenerator()
alertas_dados = generator7.generate_alerts(
    sku='TEST007',
    loja='L001',
    historico=historico_curto,
    previsao=previsao_curto,
    modelo_info={}
)

alertas_quality = [a for a in alertas_dados if a['categoria'] == 'QUALIDADE_DADOS']

if len(alertas_quality) > 0:
    alerta = alertas_quality[0]
    print(f"   [OK] Alerta de qualidade de dados detectado")
    print(f"        Periodos: {alerta['dados_contexto']['periodos_historico']}")
    print(f"        Mensagem: {alerta['mensagem']}")
else:
    print(f"   [ERRO] Alerta de dados limitados NAO foi gerado!")

# ============================================================================
# 8. TESTE: MÚLTIPLOS ALERTAS SIMULTÂNEOS
# ============================================================================
print("\n8. Teste de Multiplos Alertas Simultaneos...")

# Cenário complexo: estoque baixo + demanda crescendo + dados limitados
historico_multi = [50, 100, 150]  # Crescimento + histórico curto
previsao_multi = [200, 250, 300]

generator8 = SmartAlertGenerator()
alertas_multi = generator8.generate_alerts(
    sku='TEST008',
    loja='L001',
    historico=historico_multi,
    previsao=previsao_multi,
    modelo_info={},
    estoque_atual=80  # Baixo para demanda de 200+
)

print(f"   Total de alertas gerados: {len(alertas_multi)}")

# Resumo por tipo
summary = generator8.get_summary()
print(f"\n   Resumo por tipo:")
print(f"     CRITICAL: {summary['critical']}")
print(f"     WARNING: {summary['warning']}")
print(f"     INFO: {summary['info']}")
print(f"     SUCCESS: {summary['success']}")

# Listar todos os alertas
print(f"\n   Alertas detectados:")
for i, alerta in enumerate(alertas_multi, 1):
    print(f"     {i}. [{alerta['tipo']}] {alerta['titulo']}")

# Validar que alertas foram ordenados por prioridade
prioridades = [a['prioridade'] for a in alertas_multi]
if prioridades == sorted(prioridades):
    print(f"\n   [OK] Alertas ordenados por prioridade corretamente")
else:
    print(f"\n   [ERRO] Alertas NAO estao ordenados por prioridade!")

# ============================================================================
# 9. TESTE: TIPOS DE ALERTA COM ÍCONES
# ============================================================================
print("\n9. Teste de Tipos de Alerta com Icones...")

tipos_esperados = {
    'CRITICAL': 'Vermelho - Acao imediata',
    'WARNING': 'Amarelo - Atencao necessaria',
    'INFO': 'Azul - Informativo',
    'SUCCESS': 'Verde - Positivo'
}

print(f"   Tipos de alerta disponiveis:")
for tipo, descricao in tipos_esperados.items():
    valor_classe = getattr(SmartAlertGenerator, tipo, None)
    if valor_classe == tipo:
        print(f"     [OK] {tipo}: {descricao}")
    else:
        print(f"     [ERRO] {tipo} nao configurado corretamente")

# ============================================================================
# 10. TESTE: ESTRUTURA DO ALERTA
# ============================================================================
print("\n10. Teste de Estrutura do Alerta...")

if len(alertas_multi) > 0:
    alerta_exemplo = alertas_multi[0]

    campos_obrigatorios = [
        'tipo', 'categoria', 'sku', 'loja', 'titulo', 'mensagem',
        'acao_recomendada', 'prioridade', 'timestamp', 'dados_contexto'
    ]

    campos_presentes = all(campo in alerta_exemplo for campo in campos_obrigatorios)

    if campos_presentes:
        print(f"   [OK] Todos os campos obrigatorios presentes")
        print(f"        Campos: {', '.join(campos_obrigatorios)}")
    else:
        print(f"   [ERRO] Campos obrigatorios ausentes!")
        faltando = [c for c in campos_obrigatorios if c not in alerta_exemplo]
        print(f"        Faltando: {', '.join(faltando)}")
else:
    print(f"   [AVISO] Nenhum alerta para validar estrutura")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n\n" + "=" * 70)
print("RESUMO FINAL - VALIDACAO DO SISTEMA DE ALERTAS")
print("=" * 70)

# Checklist de validações
checks = [
    ("Alerta de ruptura de estoque", len(alertas_stockout) > 0),
    ("Alerta de excesso de estoque", len(alertas_overstock) > 0),
    ("Alerta de crescimento de demanda", len(alertas_spike) > 0),
    ("Alerta de queda de demanda", len(alertas_drop) > 0),
    ("Alerta de baixa acurácia", len(alertas_accuracy) > 0),
    ("Alerta positivo (SUCCESS)", len(alertas_success) > 0),
    ("Alerta de dados limitados", len(alertas_quality) > 0),
    ("Múltiplos alertas simultâneos", len(alertas_multi) > 0),
    ("Ordenação por prioridade", prioridades == sorted(prioridades)),
    ("Estrutura de campos completa", campos_presentes if len(alertas_multi) > 0 else True)
]

testes_ok = sum(1 for _, passou in checks if passou)
testes_total = len(checks)

print("\nChecklist de validações:")
for descricao, passou in checks:
    status = "[OK]" if passou else "[ERRO]"
    print(f"  {status} {descricao}")

taxa_sucesso = (testes_ok / testes_total) * 100
print(f"\nTaxa de sucesso: {testes_ok}/{testes_total} ({taxa_sucesso:.0f}%)")

# Tabela de resumo
print("\n" + "=" * 70)
print("Estatisticas dos Testes:")
print("=" * 70)

print(f"\nTotal de alertas gerados em todos os testes: {len(alertas_ruptura) + len(alertas_excesso) + len(alertas_crescimento) + len(alertas_queda) + len(alertas_acuracia) + len(alertas_qualidade) + len(alertas_dados) + len(alertas_multi)}")

print(f"\nDistribuicao por categoria:")
todas_categorias = {}
for alertas_list in [alertas_ruptura, alertas_excesso, alertas_crescimento, alertas_queda, alertas_acuracia, alertas_qualidade, alertas_dados, alertas_multi]:
    for alerta in alertas_list:
        cat = alerta['categoria']
        todas_categorias[cat] = todas_categorias.get(cat, 0) + 1

for cat, count in sorted(todas_categorias.items()):
    print(f"  {cat}: {count}")

# Status final
print("\n" + "=" * 70)
if taxa_sucesso == 100:
    print("STATUS: [SUCESSO] SISTEMA DE ALERTAS 100% FUNCIONAL!")
    print("\nO sistema de alertas inteligentes esta:")
    print("  - Detectando corretamente todos os tipos de alerta")
    print("  - Gerando mensagens e acoes recomendadas")
    print("  - Ordenando por prioridade")
    print("  - Incluindo dados de contexto")
    print("\nSistema pronto para producao!")
elif taxa_sucesso >= 80:
    print("STATUS: [AVISO] Sistema funciona mas ha problemas menores")
else:
    print("STATUS: [ERRO] Sistema apresenta problemas significativos")

print("=" * 70)
