# -*- coding: utf-8 -*-
"""
Investigar: Por que a API retorna históricos diferentes?
SQL retorna totais idênticos, mas API mostra 1.42% de diferença
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
from datetime import datetime

print("=" * 80)
print("   INVESTIGAÇÃO: DIFERENÇA NO HISTÓRICO DA API")
print("=" * 80)
print()

BASE_URL = 'http://localhost:5001'

# 1. Buscar dados MENSAL
print("1️⃣  BUSCANDO DADOS MENSAL")
print("-" * 80)

dados_mensal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 6,
    'granularidade': 'mensal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_mensal,
    headers={'Content-Type': 'application/json'},
    timeout=120
)

resultado_mensal = response.json()
hist_base_mensal = resultado_mensal['historico_base']
hist_teste_mensal = resultado_mensal.get('historico_teste', {})

valores_base_mensal = hist_base_mensal['valores']
datas_base_mensal = hist_base_mensal['datas']
valores_teste_mensal = hist_teste_mensal.get('valores', [])
datas_teste_mensal = hist_teste_mensal.get('datas', [])

total_base_mensal = sum(valores_base_mensal)
total_teste_mensal = sum(valores_teste_mensal)
total_historico_mensal = total_base_mensal + total_teste_mensal

print(f"Períodos base: {len(valores_base_mensal)}")
print(f"Períodos teste: {len(valores_teste_mensal)}")
print(f"Total períodos histórico: {len(valores_base_mensal) + len(valores_teste_mensal)}")
print()
print(f"Total historico_base:  {total_base_mensal:>15,.2f}")
print(f"Total historico_teste: {total_teste_mensal:>15,.2f}")
print(f"TOTAL HISTÓRICO:       {total_historico_mensal:>15,.2f}")
print()

print("Datas historico_base:")
print(f"  Início: {datas_base_mensal[0]}")
print(f"  Fim:    {datas_base_mensal[-1]}")
print()
if datas_teste_mensal:
    print("Datas historico_teste:")
    print(f"  Início: {datas_teste_mensal[0]}")
    print(f"  Fim:    {datas_teste_mensal[-1]}")
    print()

# 2. Buscar dados SEMANAL
print("2️⃣  BUSCANDO DADOS SEMANAL")
print("-" * 80)

dados_semanal = {
    'loja': 'TODAS',
    'categoria': 'TODAS',
    'produto': 'TODOS',
    'meses_previsao': 6,
    'granularidade': 'semanal'
}

response = requests.post(
    f'{BASE_URL}/api/gerar_previsao_banco',
    json=dados_semanal,
    headers={'Content-Type': 'application/json'},
    timeout=120
)

resultado_semanal = response.json()
hist_base_semanal = resultado_semanal['historico_base']
hist_teste_semanal = resultado_semanal.get('historico_teste', {})

valores_base_semanal = hist_base_semanal['valores']
datas_base_semanal = hist_base_semanal['datas']
valores_teste_semanal = hist_teste_semanal.get('valores', [])
datas_teste_semanal = hist_teste_semanal.get('datas', [])

total_base_semanal = sum(valores_base_semanal)
total_teste_semanal = sum(valores_teste_semanal)
total_historico_semanal = total_base_semanal + total_teste_semanal

print(f"Períodos base: {len(valores_base_semanal)}")
print(f"Períodos teste: {len(valores_teste_semanal)}")
print(f"Total períodos histórico: {len(valores_base_semanal) + len(valores_teste_semanal)}")
print()
print(f"Total historico_base:  {total_base_semanal:>15,.2f}")
print(f"Total historico_teste: {total_teste_semanal:>15,.2f}")
print(f"TOTAL HISTÓRICO:       {total_historico_semanal:>15,.2f}")
print()

print("Datas historico_base:")
print(f"  Início: {datas_base_semanal[0]}")
print(f"  Fim:    {datas_base_semanal[-1]}")
print()
if datas_teste_semanal:
    print("Datas historico_teste:")
    print(f"  Início: {datas_teste_semanal[0]}")
    print(f"  Fim:    {datas_teste_semanal[-1]}")
    print()

# 3. Comparação
print("=" * 80)
print("📊 COMPARAÇÃO")
print("=" * 80)
print()

diferenca = total_historico_mensal - total_historico_semanal
pct = (diferenca / total_historico_mensal) * 100 if total_historico_mensal > 0 else 0

print(f"TOTAL MENSAL:  {total_historico_mensal:>15,.2f}")
print(f"TOTAL SEMANAL: {total_historico_semanal:>15,.2f}")
print(f"Diferença:     {diferenca:>15,.2f}  ({pct:+.2f}%)")
print()

if abs(pct) < 0.1:
    print("✅ SUCESSO: Totais idênticos (diferença < 0.1%)")
else:
    print(f"⚠️  PROBLEMA: Diferença de {abs(pct):.2f}%")
    print()

    # Investigar causa
    print("=" * 80)
    print("🔍 INVESTIGANDO CAUSA")
    print("=" * 80)
    print()

    # Verificar se a divisão 50/25/25 está causando o problema
    print("Divisão dos dados:")
    print()
    print("MENSAL:")
    print(f"  Base:  {len(valores_base_mensal)} períodos = {total_base_mensal:,.2f}")
    print(f"  Teste: {len(valores_teste_mensal)} períodos = {total_teste_mensal:,.2f}")
    print()
    print("SEMANAL:")
    print(f"  Base:  {len(valores_base_semanal)} períodos = {total_base_semanal:,.2f}")
    print(f"  Teste: {len(valores_teste_semanal)} períodos = {total_teste_semanal:,.2f}")
    print()

    # Verificar cobertura de datas
    print("Cobertura de datas:")
    print()

    data_inicio_mensal = datetime.strptime(datas_base_mensal[0], '%Y-%m-%d')
    data_fim_mensal = datetime.strptime(datas_teste_mensal[-1] if datas_teste_mensal else datas_base_mensal[-1], '%Y-%m-%d')

    data_inicio_semanal = datetime.strptime(datas_base_semanal[0], '%Y-%m-%d')
    data_fim_semanal = datetime.strptime(datas_teste_semanal[-1] if datas_teste_semanal else datas_base_semanal[-1], '%Y-%m-%d')

    print(f"MENSAL:  {data_inicio_mensal.date()} até {data_fim_mensal.date()}")
    print(f"SEMANAL: {data_inicio_semanal.date()} até {data_fim_semanal.date()}")
    print()

    if data_inicio_mensal != data_inicio_semanal:
        diff_dias = (data_inicio_semanal - data_inicio_mensal).days
        print(f"⚠️  Data início difere em {diff_dias} dias")

    if data_fim_mensal != data_fim_semanal:
        diff_dias = (data_fim_semanal - data_fim_mensal).days
        print(f"⚠️  Data fim difere em {diff_dias} dias")

print()
print("=" * 80)
