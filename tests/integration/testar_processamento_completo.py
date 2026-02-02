"""
Testar o processamento completo como o app.py faz
"""
import sys
import os

# Simular upload do arquivo
arquivo_teste = 'dados_teste_integrado.xlsx'

print('='*80)
print('TESTE: PROCESSAMENTO COMPLETO (como app.py)')
print('='*80)

# Importar função do app
from app import processar_previsao

print(f'\nProcessando arquivo: {arquivo_teste}')
print('Aguarde...\n')

try:
    resultado = processar_previsao(arquivo_teste, meses_previsao=12)

    resumo = resultado['resumo']

    print('='*80)
    print('RESULTADO DO PROCESSAMENTO:')
    print('='*80)
    print(f'Total SKUs: {resumo["total_skus"]}')
    print(f'Total Lojas: {resumo["total_lojas"]}')
    print(f'Periodo: {resumo["periodo_historico"]}')
    print(f'Meses previsao: {resumo["meses_previsao"]}')
    print(f'\n{"="*80}')
    print('VALOR DO CARD YoY:')
    print('='*80)
    print(f'Taxa Variabilidade Media YoY: {resumo["taxa_variabilidade_media_yoy"]:+.1f}%')
    print(f'Periodo comparacao: {resumo["anos_yoy"]}')
    print(f'\n{"="*80}')

    if abs(resumo["taxa_variabilidade_media_yoy"]) > 10:
        print(f'[PROBLEMA] Valor ainda alto: {resumo["taxa_variabilidade_media_yoy"]:+.1f}%')
        print('O modelo corrigido NAO esta sendo usado!')
    else:
        print(f'[OK] Valor correto: {resumo["taxa_variabilidade_media_yoy"]:+.1f}%')
        print('O modelo corrigido ESTA sendo usado!')

except Exception as e:
    print(f'[ERRO] {str(e)}')
    import traceback
    traceback.print_exc()
