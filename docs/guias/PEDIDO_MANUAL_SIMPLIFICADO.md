# Pedido Manual - Planilha Interativa

## 🎯 Objetivo

Ferramenta **tipo planilha Excel** para gestores gerenciarem pedidos de múltiplos itens simultaneamente:
- Digite pedidos campo a campo diretamente na interface
- Ou carregue arquivo Excel com vários itens
- Clique em "Calcular" e veja o impacto de todos os pedidos de uma vez
- Visualização clara com indicadores de risco coloridos

**Interface amigável tipo Excel** - sem necessidade de conhecimento técnico!

---

## ✨ Funcionalidades

### 1. **Entrada de Dados Flexível**

**Opção A: Digitação Campo a Campo**
- Clique em "➕ Adicionar Linha" para criar nova linha
- Digite: Loja, SKU, Quantidade, Demanda Diária, Estoque Atual
- Adicione quantas linhas precisar
- Edite diretamente na célula (como Excel)

**Opção B: Carregamento em Massa**
- Clique em "📁 Carregar Excel"
- Selecione arquivo de reabastecimento
- Sistema preenche automaticamente todas as linhas

### 2. **Cálculo em Lote**
- Clique em "🔄 Calcular" uma única vez
- Sistema processa TODAS as linhas simultaneamente
- Resultados aparecem instantaneamente em cada linha

### 3. **Indicadores Visuais**

**Colunas Calculadas Automaticamente:**
- **Cobertura Atual**: Quantos dias o estoque atual dura
- **Estoque Após**: Estoque total após o pedido
- **Cobertura Após**: Quantos dias durará após o pedido
- **Status**: Indicador colorido de risco

**Badges de Status:**
- 🚨 **Risco** (vermelho): < 7 dias
- ⚠️ **Atenção** (amarelo): 7-14 dias
- ✅ **OK** (verde): ≥ 15 dias

### 4. **Resumo Executivo**
Após calcular, veja resumo com:
- Total de itens processados
- Quantos sem risco (✅)
- Quantos em atenção (⚠️)
- Quantos em risco (🚨)

### 5. **Gerenciamento de Linhas**
- **Adicionar**: Botão "➕ Adicionar Linha"
- **Remover**: Botão "✕" em cada linha
- **Limpar Tudo**: Botão "🗑️ Limpar Tudo"

---

## 🚀 Como Usar

### Fluxo Básico - Digitação Manual:

1. **Acesse** `/pedido_manual` ou clique em "⚡ Pedido Manual Rápido"

2. **Adicione linhas:**
   - Clique em "➕ Adicionar Linha"
   - Digite dados em cada campo

3. **Preencha os campos EDITÁVEIS:**
   - **Loja**: Código da filial (ex: LOJA_01)
   - **SKU**: Código do produto (ex: SKU_001)
   - **Qtd. Pedido**: Quantidade que deseja pedir
   - **Demanda Diária**: Consumo médio por dia
   - **Estoque Atual**: Estoque disponível agora

4. **Calcule:**
   - Clique em "🔄 Calcular"
   - Sistema preenche automaticamente:
     - Cobertura Atual
     - Estoque Após
     - Cobertura Após
     - Status (com cor)

5. **Analise os resultados:**
   - Veja o status de cada item
   - Confira o resumo executivo
   - Ajuste quantidades se necessário
   - Recalcule

### Fluxo Básico - Carregamento de Arquivo:

1. **Acesse** `/pedido_manual`

2. **Carregue arquivo:**
   - Clique em "📁 Carregar Excel"
   - Selecione arquivo de reabastecimento
   - Sistema preenche automaticamente Loja, SKU, Demanda e Estoque

3. **Ajuste quantidades:**
   - Edite o campo "Qtd. Pedido" para cada item
   - Digite a quantidade desejada

4. **Calcule:**
   - Clique em "🔄 Calcular"
   - Veja resultados para todos os itens

5. **Revise e ajuste:**
   - Itens em risco? Aumente a quantidade
   - Itens muito seguros? Reduza se desejar
   - Recalcule após ajustes

---

## 📁 Arquivo de Entrada

Use o **Excel gerado pelo Reabastecimento** (modo automático ou manual).

**Colunas Necessárias:**
- `Loja` - Código da filial
- `SKU` - Código do produto
- `Demanda_Media_Mensal` ou `Demanda_Diaria` - Consumo médio
- `Estoque_Disponivel` - Estoque atual
- `Lead_Time_Dias` - Tempo de entrega

**Colunas Opcionais:**
- `Quantidade_Pedido` - Sugestão do sistema
- `Ponto_Pedido` - Ponto de reabastecimento
- `Lote_Minimo` - Quantidade mínima
- `Estoque_Transito` - Em trânsito
- `Pedidos_Abertos` - Pedidos pendentes

---

## 🎨 Interface

### Layout Principal

```
┌──────────────────────────────────────────────────────────────┐
│ Pedido Manual - Planilha Interativa                         │
│ Digite os pedidos campo a campo ou carregue arquivo Excel   │
├──────────────────────────────────────────────────────────────┤
│ [➕ Adicionar Linha] [🔄 Calcular] [🗑️ Limpar]  [📁 Carregar]│
├──────────────────────────────────────────────────────────────┤
│ RESUMO:                                                      │
│ [Total: 15] [✅ OK: 10] [⚠️ Atenção: 3] [🚨 Risco: 2]     │
├──────────────────────────────────────────────────────────────┤
│ # │ Loja    │ SKU     │ Qtd   │ Dem  │ Est  │ Cob  │ ...  │
│───┼─────────┼─────────┼───────┼──────┼──────┼──────┼──────│
│ 1 │ LOJA_01 │ SKU_001 │ [100] │ 5.0  │ 80   │ 16.0 │ ... │
│ 2 │ LOJA_01 │ SKU_002 │ [150] │ 8.0  │ 50   │ 6.3  │ ... │
│ 3 │ LOJA_02 │ SKU_001 │ [200] │ 10.0 │ 120  │ 12.0 │ ... │
│ ...                                                          │
└──────────────────────────────────────────────────────────────┘
```

### Campos Editáveis (brancos):
- Loja
- SKU
- Qtd. Pedido
- Demanda Diária
- Estoque Atual

### Campos Calculados (cinza claro):
- Cobertura Atual
- Estoque Após
- Cobertura Após
- Status (badge colorido)

---

## 📊 Lógica de Cálculo

### Cobertura Atual
```
Cobertura Atual = Estoque Atual / Demanda Diária
```

**Exemplo:**
- Estoque Atual: 80 unidades
- Demanda Diária: 5 un/dia
- **Cobertura Atual = 80 / 5 = 16.0 dias**

### Estoque Após Pedido
```
Estoque Após = Estoque Atual + Quantidade Pedido
```

**Exemplo:**
- Estoque Atual: 80 unidades
- Quantidade Pedido: 100 unidades
- **Estoque Após = 80 + 100 = 180 unidades**

### Cobertura Após Pedido
```
Cobertura Após = Estoque Após / Demanda Diária
```

**Exemplo:**
- Estoque Após: 180 unidades
- Demanda Diária: 5 un/dia
- **Cobertura Após = 180 / 5 = 36.0 dias**

### Classificação de Risco
```
🚨 Risco    : Cobertura Após < 7 dias
⚠️ Atenção  : 7 ≤ Cobertura Após < 15 dias
✅ OK       : Cobertura Após ≥ 15 dias
```

---

## 💡 Casos de Uso

### Caso 1: Planejamento Semanal de Compras

```
Situação: Preciso planejar pedidos de 50 itens para a semana

Ação:
1. Carregue Excel do reabastecimento (50 itens)
2. Sistema preenche Loja, SKU, Demanda, Estoque
3. Ajuste campo "Qtd. Pedido" para cada item
4. Clique "Calcular"
5. Veja resumo: 10 em risco, 15 atenção, 25 OK
6. Foque nos 10 em risco - aumente quantidades
7. Recalcule até eliminar riscos
8. Pronto para enviar pedidos
```

### Caso 2: Análise de Múltiplos Cenários

```
Situação: Quer testar diferentes quantidades para 5 itens

Ação:
1. Adicione 5 linhas manualmente
2. Preencha Loja, SKU, Demanda, Estoque
3. Cenário 1: Digite quantidades conservadoras → Calcule
4. Anote resultados no papel
5. Cenário 2: Mude quantidades para mais ousadas → Calcule
6. Compare resultados
7. Escolha melhor equilíbrio custo x risco
```

### Caso 3: Validação de Sugestões do Sistema

```
Situação: Sistema recomendou pedidos, quer validar antes de aprovar

Ação:
1. Carregue Excel com sugestões
2. Campo "Qtd. Pedido" vem vazio (ou zero)
3. Copie valores da coluna "Quantidade_Pedido" do sistema
4. Clique "Calcular"
5. Veja se algum item fica em risco
6. Se sim, ajuste quantidades problemáticas
7. Recalcule
8. Aprove pedidos
```

### Caso 4: Urgência - Priorizar Itens em Risco

```
Situação: Orçamento limitado, precisa priorizar itens críticos

Ação:
1. Carregue Excel com 100 itens
2. Deixe todas quantidades = 0
3. Clique "Calcular" para ver cobertura atual
4. Identifique visualmente itens em 🚨 Risco (vermelhos)
5. Aumente quantidade APENAS desses itens críticos
6. Recalcule
7. Se ainda sobra orçamento, ataque os ⚠️ Atenção
8. Recalcule novamente
```

---

## 🔄 Fluxo de Trabalho Integrado

```
1. Reabastecimento Automático
   ↓
   Gera Excel com sugestões + análise completa
   ↓
2. Pedido Manual - Planilha
   ↓
   Carrega Excel
   ↓
   Ajusta quantidades visualmente
   ↓
   Calcula impacto de todos os itens
   ↓
   Revisa resumo executivo
   ↓
   Ajusta itens em risco
   ↓
3. Decisão Final
   ↓
   Exporta/copia dados ajustados
   ↓
   Envia para sistema de compras
```

---

## ⚡ Vantagens

✅ **Interface tipo Excel**: Familiar para qualquer usuário
✅ **Edição inline**: Clique e digite, sem formulários
✅ **Processamento em lote**: Calcula todos os itens de uma vez
✅ **Resumo visual**: Vê rapidamente quantos itens OK, atenção, risco
✅ **Badges coloridos**: Identificação visual instantânea
✅ **Flexível**: Digitação manual OU upload de arquivo
✅ **Gerenciamento fácil**: Adicionar/remover linhas com 1 clique
✅ **Sem salvamento**: Apenas simulação, teste à vontade

---

## 🎯 Diferenças da Versão Anterior

| Aspecto | Versão Antiga (Item-a-Item) | Versão Nova (Planilha) |
|---------|----------------------------|------------------------|
| **Interface** | Buscar 1 item por vez | Tabela com N itens |
| **Input** | Loja + SKU → Buscar | Digitar OU carregar arquivo |
| **Processamento** | Individual | Batch (todos de vez) |
| **Visualização** | Cards grandes | Linhas compactas |
| **Comparação** | Difícil comparar itens | Fácil: todos na mesma tela |
| **Produtividade** | 1 item = 5 cliques | N itens = 1 clique |
| **Uso** | Consultas pontuais | Planejamento em lote |

---

## 📝 FAQ

**P: Preciso carregar arquivo ou posso digitar?**
R: Ambos! Digite campo a campo OU carregue Excel. Você escolhe.

**P: Posso editar dados depois de carregar arquivo?**
R: Sim! Todos os campos editáveis podem ser alterados a qualquer momento.

**P: O cálculo salva algo no sistema?**
R: Não! É apenas simulação visual. Nada é persistido.

**P: Posso calcular apenas algumas linhas?**
R: Não. O botão "Calcular" processa todas as linhas. Mas linhas incompletas são ignoradas automaticamente.

**P: Como sei se preenchi tudo corretamente?**
R: Se após calcular aparecer "-" nos resultados, falta preencher algum campo obrigatório (Loja, SKU, Demanda > 0).

**P: Posso adicionar linhas depois de carregar arquivo?**
R: Sim! Clique "➕ Adicionar Linha" e digite manualmente.

**P: Posso usar arquivo diferente do reabastecimento?**
R: Sim, desde que tenha as colunas obrigatórias: Loja, SKU, Demanda_Diaria (ou Demanda_Media_Mensal), Estoque_Disponivel.

**P: Quantas linhas posso adicionar?**
R: Sem limite! Mas para melhor performance, recomenda-se até 200 itens por vez.

**P: Os dados ficam salvos se eu sair da página?**
R: Não. Ao sair, tudo é perdido. Faça anotações/prints se necessário.

---

## 🚀 Acesso Rápido

**URL Direta:** `/pedido_manual`

**Ou pelo menu:**
- Reabastecimento → "⚡ Pedido Manual Rápido"

---

## 📌 Dicas de Uso

1. **Primeiro carregar, depois ajustar**: Carregue Excel, depois ajuste quantidades
2. **Use resumo executivo**: Veja rapidamente quantos itens problemáticos
3. **Foque no vermelho**: Priorize itens 🚨 Risco primeiro
4. **Recalcule à vontade**: Não há limite, teste cenários diferentes
5. **Remova linhas desnecessárias**: Mantenha foco apenas nos itens relevantes
6. **Zero é válido**: Quantidade = 0 é aceita (para ver cobertura atual)

---

**Versão**: 2.0 (Planilha Interativa)
**Data**: Dezembro 2024
**Tipo**: Ferramenta de Simulação em Lote (Somente Leitura)
