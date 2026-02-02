# -*- coding: utf-8 -*-
"""
Teste de integração do app.py com dados diários
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Simular import do app (sem rodar Flask)
from app import processar_previsao

print("=" * 80)
print("TESTE: Integracao app.py com Dados Diarios (Simplificado)")
print("=" * 80)

arquivo_diario = 'demanda_01-12-2025.xlsx'

# Teste: Processamento completo com dados diários
print("\n[1] Teste de processamento completo")
print("-" * 80)

try:
    print("Processando previsao com dados diarios...")
    print("  - Granularidade: semanal")
    print("  - Filtro: Filiais 1, 2, 3")
    print("  - Periodos: 4 semanas")

    resultado = processar_previsao(
        arquivo_excel=arquivo_diario,
        meses_previsao=4,
        granularidade='semanal',
        filiais_filtro=[1, 2, 3],
        produtos_filtro=None
    )

    print("\n[OK] Processamento concluido!")
    print(f"\nResultado:")
    print(f"  - Success: {resultado.get('success')}")
    print(f"  - Arquivo gerado: {resultado.get('arquivo_saida')}")

    if 'resumo' in resultado:
        resumo = resultado['resumo']
        print(f"\nResumo:")
        print(f"  - Total SKUs: {resumo.get('total_skus', 'N/A')}")
        print(f"  - Meses previsao: {resumo.get('meses_previsao', 'N/A')}")

    if 'metadados' in resultado:
        meta = resultado['metadados']
        print(f"\nMetadados:")
        print(f"  - Formato origem: {meta.get('formato_origem')}")
        print(f"  - Granularidade: {meta.get('granularidade')}")

        if 'estatisticas' in meta:
            stats = meta['estatisticas']
            print(f"  - Filiais: {stats['totais']['filiais']}")
            print(f"  - Produtos: {stats['totais']['produtos']}")
            print(f"  - Vendas totais: {stats['totais']['vendas_totais']}")

    if 'alertas' in resultado:
        print(f"\nAlertas ({len(resultado['alertas'])}):")
        for alerta in resultado['alertas'][:3]:
            print(f"  - [{alerta.get('tipo', 'info')}] {alerta.get('mensagem', 'N/A')}")

    if 'grafico_data' in resultado:
        grafico = resultado['grafico_data']
        if 'previsoes_lojas' in grafico:
            print(f"\nPrevisoes geradas: {len(grafico['previsoes_lojas'])} lojas")

    print("\n" + "=" * 80)
    print("[OK] TESTE COMPLETO PASSOU!")
    print("=" * 80)

except Exception as e:
    print(f"\n[ERRO] {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
