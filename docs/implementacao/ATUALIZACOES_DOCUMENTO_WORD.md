# Atualizações do Documento Word - Sistema de Previsão de Demanda e Reabastecimento

**Data:** 2024-12-29
**Seções para atualizar:** 7.2, 9, 9.1, 9.2, 9.3, 10

---

## SEÇÃO 7.2 - Modo Automático

### TEXTO ATUAL (linhas 221-228):
```
7.2. Modo Automático

No modo automático, o sistema calcula automaticamente a demanda usando o histórico
de vendas e seleciona o melhor método para cada produto.

Planilhas necessárias (2):

Historico_Vendas:
Loja, SKU, Mes, Vendas, Dias_Com_Estoque, Origem

Estoque_Atual:
Loja, SKU, Lead_Time_Dias, Estoque_Disponivel, Estoque_Transito, Nivel_Servico, Lote_Minimo
```

### TEXTO ATUALIZADO:
```
7.2. Modo Automático (Recomendado)

O modo automático é a forma RECOMENDADA de utilizar o sistema. Ele calcula
automaticamente a demanda usando o histórico de vendas e seleciona
inteligentemente o melhor método estatístico para cada produto.

Arquivo necessário: exemplo_reabastecimento_automatico.xlsx

Este arquivo contém 2 abas principais:

ABA 1: ESTOQUE_ATUAL
Colunas obrigatórias:
  • Loja - Código da loja
  • SKU - Código do produto
  • Lead_Time_Dias - Tempo de reposição em dias
  • Estoque_Disponivel - Estoque físico atual
  • Nivel_Servico - Nível de serviço desejado por item (0.90 a 0.99)

Colunas opcionais:
  • Estoque_Transito - Estoque em trânsito (padrão: 0)
  • Pedidos_Abertos - Pedidos em aberto (padrão: 0)
  • Lote_Minimo - Lote mínimo de compra (padrão: 1)

IMPORTANTE - Nível de Serviço por Item:
A partir da versão 2.2, o nível de serviço é especificado POR ITEM no arquivo
de entrada, permitindo gestão diferenciada:
  • 0.99 (99%) - Produtos A: alto giro, críticos
  • 0.95 (95%) - Produtos B: médio giro, importantes
  • 0.90 (90%) - Produtos C: baixo giro, menos críticos
  • 0.98 (98%) - Produtos especiais/estratégicos

ABA 2: HISTORICO_VENDAS
Colunas obrigatórias:
  • Loja - Código da loja
  • SKU - Código do produto
  • Mes - Mês no formato YYYY-MM (ex: 2024-01)
  • Vendas - Quantidade vendida no mês

Colunas opcionais:
  • Dias_Com_Estoque - Dias com estoque disponível (padrão: 30)
  • Origem - Origem dos dados (padrão: "Sistema")

Período de histórico:
  • Mínimo recomendado: 6 meses
  • Ideal: 12 a 24 meses
  • Quanto mais histórico, melhor a precisão

Fluxo de processamento:
1. Upload do arquivo exemplo_reabastecimento_automatico.xlsx
2. Sistema analisa o padrão de demanda de cada item
3. Seleciona automaticamente o melhor método estatístico (entre 7 disponíveis)
4. Calcula demanda média e desvio padrão
5. Calcula estoque de segurança individualizado por nível de serviço
6. Calcula ponto de pedido
7. Determina quantidade ideal de reabastecimento
8. Identifica itens com risco de ruptura
9. Gera relatório Excel completo com método utilizado por item

Métodos selecionados automaticamente:
  • SMA (Média Móvel Simples) - Demanda estável
  • WMA (Média Móvel Ponderada) - Demanda com mudanças graduais
  • EMA (Média Móvel Exponencial) - Demanda com tendência suave
  • Regressão com Tendência - Demanda com tendência clara
  • Decomposição Sazonal - Demanda com padrões sazonais
  • TSB (Teunter-Syntetos-Babai) - Demanda intermitente
  • Última Venda - Histórico insuficiente

O sistema usa validação cruzada (walk-forward) para escolher o método
com menor erro de previsão.
```

---

## SEÇÃO 9 - Descrição e Orientação de Uso das Planilhas

### TEXTO ATUAL (linha 245):
```
9. Descrição e Orientação de Uso das Planilhas
```

### TEXTO ATUALIZADO:
```
9. Descrição e Orientação de Uso das Planilhas

O sistema aceita dois tipos principais de arquivos Excel (.xlsx):

1. Reabastecimento Automático (RECOMENDADO)
   Arquivo: exemplo_reabastecimento_automatico.xlsx
   Contém histórico de vendas + situação atual de estoque
   Sistema calcula demanda automaticamente

2. Pedidos Manuais
   2.1. Pedido por Quantidade
        Arquivo: exemplo_pedido_quantidade.xlsx
        Para validar múltiplos de caixa em pedidos pré-definidos

   2.2. Pedido por Cobertura
        Arquivo: exemplo_pedido_cobertura.xlsx
        Para calcular quantidade baseada em dias de cobertura desejados

Todos os arquivos exemplo estão disponíveis na interface web e incluem
abas de instruções detalhadas.
```

---

## SEÇÃO 9.1 - Estrutura Geral (ATUALIZAR)

### TEXTO ATUAL (linha 247):
```
9.1. Estrutura Geral

O sistema aceita arquivos Excel (.xlsx) com estruturas específicas
dependendo do modo de operação escolhido.
```

### TEXTO ATUALIZADO:
```
9.1. Arquivo: exemplo_reabastecimento_automatico.xlsx

Este é o arquivo PRINCIPAL do sistema, utilizado para reabastecimento
automático com cálculo inteligente de demanda.

Estrutura: 2 abas obrigatórias + 1 aba de instruções

═══════════════════════════════════════════════════════════════════

ABA 1: ESTOQUE_ATUAL

Contém a situação atual de estoque de cada item.

┌──────────────────────┬──────────┬─────────────┬─────────────────────┐
│ Coluna               │ Tipo     │ Obrigatório │ Descrição           │
├──────────────────────┼──────────┼─────────────┼─────────────────────┤
│ Loja                 │ Texto    │ Sim         │ Código da loja      │
│ SKU                  │ Texto    │ Sim         │ Código do produto   │
│ Lead_Time_Dias       │ Inteiro  │ Sim         │ Tempo de reposição  │
│ Estoque_Disponivel   │ Número   │ Sim         │ Estoque físico      │
│ Nivel_Servico        │ Decimal  │ Sim         │ 0.90 a 0.99         │
│ Estoque_Transito     │ Número   │ Não         │ Padrão: 0           │
│ Pedidos_Abertos      │ Número   │ Não         │ Padrão: 0           │
│ Lote_Minimo          │ Inteiro  │ Não         │ Padrão: 1           │
└──────────────────────┴──────────┴─────────────┴─────────────────────┘

Exemplo de preenchimento:

| Loja    | SKU      | Lead_Time | Estoque | Nivel_Servico | Lote_Min |
|---------|----------|-----------|---------|---------------|----------|
| LOJA_01 | PROD_001 | 7         | 150     | 0.99          | 12       |
| LOJA_01 | PROD_002 | 10        | 80      | 0.95          | 10       |
| LOJA_01 | PROD_003 | 14        | 25      | 0.90          | 6        |

NOVO (v2.2): Nível de Serviço Individualizado

O campo Nivel_Servico é OBRIGATÓRIO e permite gestão diferenciada
por produto:

Produtos A (alto giro, críticos):
  → Nivel_Servico = 0.99 (99%)
  → Maior estoque de segurança
  → Menor risco de ruptura

Produtos B (médio giro, importantes):
  → Nivel_Servico = 0.95 (95%)
  → Estoque de segurança balanceado
  → Equilíbrio custo x disponibilidade

Produtos C (baixo giro, menos críticos):
  → Nivel_Servico = 0.90 (90%)
  → Menor estoque de segurança
  → Otimização de capital de giro

Produtos especiais/estratégicos:
  → Nivel_Servico = 0.98 (98%)
  → Ajuste conforme necessidade

═══════════════════════════════════════════════════════════════════

ABA 2: HISTORICO_VENDAS

Contém o histórico de vendas para cálculo automático de demanda.

┌──────────────────────┬──────────┬─────────────┬─────────────────────┐
│ Coluna               │ Tipo     │ Obrigatório │ Descrição           │
├──────────────────────┼──────────┼─────────────┼─────────────────────┤
│ Loja                 │ Texto    │ Sim         │ Código da loja      │
│ SKU                  │ Texto    │ Sim         │ Código do produto   │
│ Mes                  │ Texto    │ Sim         │ YYYY-MM (2024-01)   │
│ Vendas               │ Número   │ Sim         │ Qtd vendida         │
│ Dias_Com_Estoque     │ Inteiro  │ Não         │ Padrão: 30          │
│ Origem               │ Texto    │ Não         │ Padrão: "Sistema"   │
└──────────────────────┴──────────┴─────────────┴─────────────────────┘

Exemplo de preenchimento:

| Loja    | SKU      | Mes      | Vendas | Dias_Com_Estoque |
|---------|----------|----------|--------|------------------|
| LOJA_01 | PROD_001 | 2024-01  | 120    | 30               |
| LOJA_01 | PROD_001 | 2024-02  | 115    | 30               |
| LOJA_01 | PROD_001 | 2024-03  | 98     | 25               |

IMPORTANTE - Ajuste por Ruptura:

Quando Dias_Com_Estoque < 30, o sistema detecta ruptura parcial e
ajusta automaticamente as vendas:

Vendas_Ajustadas = Vendas × (30 / Dias_Com_Estoque)

Exemplo:
  Vendas registradas: 80 unidades
  Dias_Com_Estoque: 20 dias (houve ruptura)
  Vendas_Ajustadas: 80 × (30/20) = 120 unidades

Isso garante que a demanda real seja estimada corretamente, mesmo
quando houve falta de produto.

Recomendações de período:
  • Mínimo: 6 meses
  • Recomendado: 12 meses
  • Ideal: 18 a 24 meses
  • Produtos sazonais: Mínimo 12 meses

═══════════════════════════════════════════════════════════════════

ABA 3: INSTRUCOES (Gerada automaticamente)

Contém instruções detalhadas de uso e exemplos práticos.
Esta aba é gerada automaticamente pelo script
gerar_exemplo_reabastecimento.py
```

---

## SEÇÃO 9.2 - SUBSTITUIR COMPLETAMENTE

### TEXTO ATUAL (linha 248):
```
9.2. Modo Manual - exemplo_reabastecimento.xlsx
```

### TEXTO ATUALIZADO:
```
9.2. Arquivo: exemplo_pedido_quantidade.xlsx

Este arquivo é utilizado para PEDIDOS MANUAIS quando você já sabe a
quantidade desejada e quer apenas validar múltiplos de caixa.

Estrutura: 1 aba de dados + 1 aba de instruções

═══════════════════════════════════════════════════════════════════

ABA: PEDIDO

┌──────────────────────┬──────────┬─────────────┬─────────────────────┐
│ Coluna               │ Tipo     │ Obrigatório │ Descrição           │
├──────────────────────┼──────────┼─────────────┼─────────────────────┤
│ Loja                 │ Texto    │ Sim         │ Código da loja      │
│ SKU                  │ Texto    │ Sim         │ Código do produto   │
│ Quantidade_Desejada  │ Número   │ Sim         │ Qtd que você quer   │
│ Unidades_Por_Caixa   │ Inteiro  │ Sim         │ Un por embalagem    │
│ Demanda_Diaria       │ Decimal  │ Não         │ Para calc cobertura │
│ Estoque_Disponivel   │ Número   │ Não         │ Para calc cobertura │
└──────────────────────┴──────────┴─────────────┴─────────────────────┘

Exemplo:

| Loja    | SKU      | Qtd_Desejada | Un_Caixa | Demanda_Diaria |
|---------|----------|--------------|----------|----------------|
| LOJA_01 | PROD_001 | 100          | 12       | 5.5            |
| LOJA_01 | PROD_002 | 75           | 10       | 3.2            |

O que o sistema faz:

1. Valida se quantidade está em múltiplo de caixa
2. Ajusta automaticamente para cima se necessário
3. Calcula número de caixas a pedir
4. Se informou demanda, calcula cobertura em dias
5. Gera relatório Excel pronto para emissão

Exemplo de processamento:

Input:
  Quantidade_Desejada: 100
  Unidades_Por_Caixa: 12

Cálculo:
  100 ÷ 12 = 8.33 caixas (não é inteiro!)
  Arredonda para cima: 9 caixas
  9 × 12 = 108 unidades

Output:
  Quantidade_Pedido: 108
  Numero_Caixas: 9
  Foi_Ajustado: Sim
  Diferenca_Ajuste: +8
  Status: "Ajustado para múltiplo de caixa"

Arquivo de saída: pedido_quantidade_YYYYMMDD_HHMMSS.xlsx
  • Aba 1: Pedido (todos os itens)
  • Aba 2: Itens_Ajustados (apenas itens ajustados)
```

---

## SEÇÃO 9.3 - SUBSTITUIR COMPLETAMENTE

### TEXTO ATUAL (linhas 250-252):
```
9.3. Modo Automático - Aba Historico_Vendas

IMPORTANTE: O sistema ajusta automaticamente as vendas quando houve
ruptura (Dias_Com_Estoque < 30), extrapolando a demanda real.
```

### TEXTO ATUALIZADO:
```
9.3. Arquivo: exemplo_pedido_cobertura.xlsx

Este arquivo é utilizado para PEDIDOS MANUAIS quando você quer definir
dias de cobertura e deixar o sistema calcular a quantidade automaticamente.

Estrutura: 1 aba de dados + 1 aba de instruções

═══════════════════════════════════════════════════════════════════

ABA: PEDIDO

┌──────────────────────────┬──────────┬─────────────┬───────────────────┐
│ Coluna                   │ Tipo     │ Obrigatório │ Descrição         │
├──────────────────────────┼──────────┼─────────────┼───────────────────┤
│ Loja                     │ Texto    │ Sim         │ Código da loja    │
│ SKU                      │ Texto    │ Sim         │ Código do produto │
│ Demanda_Diaria           │ Decimal  │ Sim         │ Demanda diária    │
│ Cobertura_Desejada_Dias  │ Inteiro  │ Sim         │ Dias desejados    │
│ Unidades_Por_Caixa       │ Inteiro  │ Sim         │ Un por embalagem  │
│ Estoque_Disponivel       │ Número   │ Não         │ Estoque atual     │
└──────────────────────────┴──────────┴─────────────┴───────────────────┘

Exemplo:

| Loja    | SKU      | Demanda | Cobertura | Un_Caixa | Estoque |
|---------|----------|---------|-----------|----------|---------|
| LOJA_01 | PROD_001 | 5.5     | 30        | 12       | 20      |
| LOJA_01 | PROD_002 | 3.2     | 45        | 10       | 15      |

O que o sistema faz:

1. Calcula cobertura atual do estoque
2. Calcula necessidade líquida (desejado - atual)
3. Converte dias em quantidade (dias × demanda diária)
4. Ajusta para múltiplo de caixa
5. Calcula cobertura real após pedido
6. Gera relatório Excel pronto para emissão

Exemplo de processamento:

Input:
  Demanda_Diaria: 5.5 unidades/dia
  Cobertura_Desejada_Dias: 30
  Estoque_Disponivel: 20
  Unidades_Por_Caixa: 12

Cálculo:
  Cobertura atual = 20 ÷ 5.5 = 3.6 dias
  Necessidade = 30 - 3.6 = 26.4 dias
  Quantidade bruta = 26.4 × 5.5 = 145.2 unidades
  Ajuste para múltiplo: 156 unidades (13 caixas × 12)
  Cobertura real = (20 + 156) ÷ 5.5 = 32.0 dias

Output:
  Quantidade_Pedido: 156
  Numero_Caixas: 13
  Cobertura_Real_Dias: 32.0
  Diferenca_Cobertura: +2.0 dias
  Status: "Ajustado para múltiplo de caixa"

IMPORTANTE: Se o estoque atual já fornecer a cobertura desejada ou
mais, a Quantidade_Pedido será ZERO (não há necessidade de pedido).

Arquivo de saída: pedido_cobertura_YYYYMMDD_HHMMSS.xlsx
  • Aba 1: Pedido (todos os itens)
  • Aba 2: Sem_Necessidade (itens com estoque suficiente)
  • Aba 3: Itens_Ajustados (itens ajustados para múltiplo)
```

---

## SEÇÃO 10 - Perguntas Frequentes (FAQ) - ATUALIZAR

### QUESTÕES A MANTER (sem alteração):
- Questão 2: Por que o sistema ajusta vendas quando houve ruptura?
- Questão 4: O que significa risco de ruptura ALTO?
- Questão 5: Posso usar o sistema para previsão de vendas futuras?
- Questão 6: Como o sistema escolhe entre SMA e WMA para demanda estável?
- Questão 7: Quando usar TSB ao invés de outros métodos?

### QUESTÕES A ATUALIZAR:

**Questão 1 (ATUAL):**
```
1. Qual método de demanda devo usar?
Recomendamos sempre usar o método AUTO. Ele analisa automaticamente o
padrão de cada produto e escolhe o melhor método, garantindo previsões
mais assertivas.
```

**Questão 1 (ATUALIZADO):**
```
1. Qual é a melhor forma de usar o sistema?
Recomendamos usar o MODO AUTOMÁTICO (arquivo exemplo_reabastecimento_automatico.xlsx).
Neste modo, o sistema:
  • Analisa automaticamente o padrão de demanda de cada produto
  • Escolhe o melhor método estatístico (entre 7 disponíveis)
  • Calcula demanda média e variabilidade
  • Gera recomendações personalizadas por item

Os módulos de Pedido Manual (por Quantidade ou Cobertura) são úteis para
situações específicas onde você já sabe o que precisa pedir.
```

**Questão 3 (ATUAL):**
```
3. Como definir o nível de serviço adequado?
Use classificação ABC: 95% para produtos B (padrão), 98-99% para produtos A
(alto valor/críticos), 90% para produtos C (baixo valor).
```

**Questão 3 (ATUALIZADO):**
```
3. Como definir o nível de serviço adequado para cada item?
A partir da versão 2.2, o nível de serviço é especificado POR ITEM no
arquivo de entrada. Recomendamos usar classificação ABC:

Produtos A (alto giro/críticos):
  • Nível: 0.99 (99%)
  • Ruptura máxima tolerada: 1%
  • Exemplos: Best-sellers, itens em promoção, alto valor

Produtos B (médio giro/importantes):
  • Nível: 0.95 (95%) ← PADRÃO
  • Ruptura máxima tolerada: 5%
  • Exemplos: Produtos complementares, segunda linha

Produtos C (baixo giro/menos críticos):
  • Nível: 0.90 (90%)
  • Ruptura máxima tolerada: 10%
  • Exemplos: Cauda longa, produtos específicos

Produtos especiais/estratégicos:
  • Nível: 0.98 (98%)
  • Conforme contrato/SLA

Quanto maior o nível de serviço, maior o estoque de segurança necessário
e menor o risco de ruptura.
```

### QUESTÕES A ADICIONAR:

**Questão 8 (NOVA):**
```
8. Qual a diferença entre Pedido por Quantidade e Pedido por Cobertura?

Pedido por Quantidade:
  • Você JÁ SABE quanto quer pedir
  • Sistema valida múltiplo de caixa
  • Ajusta automaticamente para cima se necessário
  • Ideal para: Promoções, pedidos pontuais, volumes definidos

Pedido por Cobertura:
  • Você define QUANTOS DIAS de estoque quer ter
  • Sistema calcula a quantidade automaticamente
  • Considera estoque atual no cálculo
  • Ideal para: Metas de cobertura, reposição regular, gestão por dias

Ambos garantem múltiplos de caixa e geram relatórios prontos para emissão.
```

**Questão 9 (NOVA):**
```
9. Por que o método utilizado aparece no relatório?

A coluna "Método" no relatório de reabastecimento mostra qual método
estatístico foi selecionado automaticamente para cada item:

  • SMA (Média Móvel Simples) - Demanda estável
  • WMA (Média Móvel Ponderada) - Mudanças graduais
  • EMA (Média Móvel Exponencial) - Tendência suave
  • Regressão com Tendência - Tendência clara
  • Decomposição Sazonal - Padrões sazonais
  • TSB (Teunter-Syntetos-Babai) - Demanda intermitente

Isso permite:
  • Transparência no processo de cálculo
  • Auditoria e validação dos resultados
  • Entendimento de por que diferentes itens usam métodos diferentes
  • Identificação de padrões de demanda do portfólio
```

**Questão 10 (NOVA):**
```
10. Como o sistema calcula o estoque de segurança quando uso níveis de
    serviço diferentes por item?

O estoque de segurança é calculado pela fórmula:

ES = Z × σ × √LT

Onde:
  • Z = Z-score baseado no Nível de Serviço do item
  • σ = Desvio padrão da demanda diária
  • LT = Lead Time em dias

Exemplo com 2 produtos idênticos mas níveis diferentes:

Produto A (Nível 99%):
  Z = 2.33 → ES maior → Mais proteção contra ruptura

Produto C (Nível 90%):
  Z = 1.28 → ES menor → Economia de capital de giro

Isso permite otimizar o investimento em estoque, mantendo alta
disponibilidade onde é crítico e reduzindo capital onde é menos importante.
```

---

## INSTRUÇÕES PARA ATUALIZAÇÃO MANUAL

1. **Abra** o arquivo Sistema_Previsao_Demanda_Reabastecimento.docx

2. **Localize a seção 7.2** (cerca da linha 221)
   - Selecione todo o conteúdo de 7.2
   - Substitua pelo novo texto acima
   - Mantenha formatação: título em negrito, subtítulos destacados

3. **Localize a seção 9** (cerca da linha 245)
   - Substitua o texto introdutório conforme acima

4. **Localize a seção 9.1** (cerca da linha 246)
   - Substitua completamente pelo novo conteúdo
   - Use tabelas para melhor visualização das colunas
   - Destaque os campos OBRIGATÓRIOS

5. **Localize a seção 9.2** (cerca da linha 248)
   - Substitua completamente
   - Este agora é sobre exemplo_pedido_quantidade.xlsx

6. **Localize a seção 9.3** (cerca da linha 250)
   - Substitua completamente
   - Este agora é sobre exemplo_pedido_cobertura.xlsx

7. **Localize a seção 10 - FAQ** (cerca da linha 254)
   - Atualize questões 1 e 3 conforme indicado
   - Adicione questões 8, 9 e 10 ao final
   - Mantenha questões 2, 4, 5, 6, 7 inalteradas

8. **Formatação geral:**
   - Use negrito para títulos de seções
   - Use tabelas para estruturas de colunas
   - Use bullets (•) para listas
   - Use realce amarelo para IMPORTANTE/NOVO
   - Mantenha fonte e espaçamento consistentes

---

## CHECKLIST DE ATUALIZAÇÃO

- [ ] Seção 7.2 atualizada (Modo Automático)
- [ ] Seção 9 atualizada (Introdução)
- [ ] Seção 9.1 atualizada (exemplo_reabastecimento_automatico.xlsx)
- [ ] Seção 9.2 atualizada (exemplo_pedido_quantidade.xlsx)
- [ ] Seção 9.3 atualizada (exemplo_pedido_cobertura.xlsx)
- [ ] FAQ Questão 1 atualizada
- [ ] FAQ Questão 3 atualizada
- [ ] FAQ Questão 8 adicionada
- [ ] FAQ Questão 9 adicionada
- [ ] FAQ Questão 10 adicionada
- [ ] Formatação revisada
- [ ] Documento salvo

---

**Versão do Documento:** 2.2
**Data da Atualização:** 2024-12-29
**Alterações Principais:**
- Nível de serviço por item
- Novos arquivos de pedido manual
- Método estatístico no relatório
- Modo automático como único modo de cálculo
