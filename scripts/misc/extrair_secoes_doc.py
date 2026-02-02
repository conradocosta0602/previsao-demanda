#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrai seções específicas do documento Word
"""

from docx import Document

doc = Document('Sistema_Previsao_Demanda_Reabastecimento.docx')

# Encontrar seções relevantes
secoes = {
    '7.2': [],
    '9': [],
    '9.1': [],
    '9.2': [],
    '9.3': [],
    '10': []
}

secao_atual = None
capturando = False

for i, p in enumerate(doc.paragraphs):
    texto = p.text.strip()

    # Identificar início de seções
    if '7.2' in texto and 'Modo Autom' in texto:
        secao_atual = '7.2'
        capturando = True
        secoes['7.2'].append(f"[{i}] {texto}")
    elif texto.startswith('9.') and not texto.startswith('9.1') and not texto.startswith('9.2') and not texto.startswith('9.3'):
        secao_atual = '9'
        capturando = True
        secoes['9'].append(f"[{i}] {texto}")
    elif '9.1' in texto:
        secao_atual = '9.1'
        capturando = True
        secoes['9.1'].append(f"[{i}] {texto}")
    elif '9.2' in texto:
        secao_atual = '9.2'
        capturando = True
        secoes['9.2'].append(f"[{i}] {texto}")
    elif '9.3' in texto:
        secao_atual = '9.3'
        capturando = True
        secoes['9.3'].append(f"[{i}] {texto}")
    elif texto.startswith('10.'):
        secao_atual = '10'
        capturando = True
        secoes['10'].append(f"[{i}] {texto}")
    elif texto.startswith('11.') or texto.startswith('8.'):
        capturando = False
        secao_atual = None

    # Capturar conteúdo da seção
    if capturando and secao_atual and texto:
        if not texto.startswith(secao_atual):
            secoes[secao_atual].append(f"[{i}] {texto}")

# Salvar em arquivo texto
with open('secoes_extraidas.txt', 'w', encoding='utf-8') as f:
    for secao, conteudo in secoes.items():
        f.write(f"\n{'='*80}\n")
        f.write(f"SEÇÃO {secao}\n")
        f.write(f"{'='*80}\n\n")
        f.write('\n'.join(conteudo[:50]))  # Primeiros 50 parágrafos
        f.write('\n\n')

print("Arquivo 'secoes_extraidas.txt' criado com sucesso!")
print()
for secao, conteudo in secoes.items():
    print(f"Secao {secao}: {len(conteudo)} paragrafos encontrados")
