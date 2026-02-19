# Nível de Serviço por Item - Implementação

**Data:** 2024-12-29
**Alteração:** Nível de serviço movido de configuração global para especificação por item

---

## Motivação

### Problema Anterior
- Nível de serviço era único para TODOS os itens (configuração global)
- Não permitia diferenciação entre produtos A, B e C
- Gestão de estoque menos refinada
- Desperdício de capital de giro

### Solução Implementada
- **Nível de serviço agora é especificado por item no arquivo de entrada**
- Permite gestão personalizada baseada na criticidade do produto
- Otimização do investimento em estoque

---

## Classificação ABC Recomendada

### Produtos A - Alto Giro (Críticos)
**Nível de Serviço:** 99% (`0.99`)

- Itens de alta rotatividade
- Grande impacto na receita
- Ruptura causa perdas significativas
- Maior investimento em estoque de segurança

**Exemplos:**
- Best-sellers
- Produtos em promoção
- Itens sazonais em alta
- Produtos de alto valor

### Produtos B - Médio Giro (Importantes)
**Nível de Serviço:** 95% (`0.95`)

- Venda regular e constante
- Impacto moderado na receita
- Ruptura é indesejável mas tolerável
- Equilíbrio entre disponibilidade e custo

**Exemplos:**
- Produtos complementares
- Segunda linha de vendas
- Itens de reposição regular

### Produtos C - Baixo Giro (Menos Críticos)
**Nível de Serviço:** 90% (`0.90`)

- Baixa rotatividade
- Menor impacto na receita
- Ruptura ocasional é aceitável
- Minimizar investimento em estoque

**Exemplos:**
- Produtos de cauda longa
- Itens específicos/nichados
- Produtos em descontinuação

### Produtos Críticos/Especiais
**Nível de Serviço:** 98% (`0.98`)

- Itens estratégicos independente do giro
- Contratos com SLA
- Produtos exclusivos

---

## Estrutura do Arquivo de Entrada

### Arquivo: `exemplo_reabastecimento_automatico.xlsx`

#### Aba 1: ESTOQUE_ATUAL

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| Loja | Texto | Sim | Código da loja | LOJA_01 |
| SKU | Texto | Sim | Código do produto | PROD_001 |
| Lead_Time_Dias | Inteiro | Sim | Tempo de reposição | 7 |
| Estoque_Disponivel | Número | Sim | Estoque físico atual | 150 |
| **Nivel_Servico** | **Decimal** | **Sim** | **Nível desejado (0.90 a 0.99)** | **0.99** |
| Estoque_Transito | Número | Não | Estoque em trânsito | 50 |
| Pedidos_Abertos | Número | Não | Pedidos em aberto | 0 |
| Lote_Minimo | Inteiro | Não | Lote mínimo de compra | 12 |

**NOVO:** A coluna `Nivel_Servico` agora é **obrigatória** e deve ser informada para cada item.

#### Aba 2: HISTORICO_VENDAS

*Sem alterações - mantém estrutura atual:*
- Loja
- SKU
- Mes (formato YYYY-MM)
- Vendas

---

## Impacto do Nível de Serviço

### Fórmula do Estoque de Segurança

```
ES = Z × σ × √LT

Onde:
- ES = Estoque de Segurança
- Z = Z-score baseado no Nível de Serviço
- σ = Desvio padrão da demanda diária
- LT = Lead Time em dias
```

### Tabela de Z-scores

| Nível de Serviço | Z-score | Interpretação |
|------------------|---------|---------------|
| 90% (0.90) | 1.28 | 10% de chance de ruptura |
| 95% (0.95) | 1.64 | 5% de chance de ruptura |
| 98% (0.98) | 2.05 | 2% de chance de ruptura |
| 99% (0.99) | 2.33 | 1% de chance de ruptura |

**Quanto maior o Z-score, maior o estoque de segurança necessário.**

---

## Exemplo Prático

### Cenário

Dois produtos com a mesma demanda, mas níveis de serviço diferentes:

| Item | Demanda Diária | Desvio | Lead Time | Nível Serviço | Z-score |
|------|---------------|---------|-----------|---------------|---------|
| PROD_A | 10 un/dia | 3 | 7 dias | 99% | 2.33 |
| PROD_C | 10 un/dia | 3 | 7 dias | 90% | 1.28 |

### Cálculo do Estoque de Segurança

**PROD_A (99%):**
```
ES = 2.33 × (3/√30) × √7
ES = 2.33 × 0.548 × 2.646
ES ≈ 3.4 unidades
```

**PROD_C (90%):**
```
ES = 1.28 × (3/√30) × √7
ES = 1.28 × 0.548 × 2.646
ES ≈ 1.9 unidades
```

**Diferença:** PROD_A precisa de **78% mais estoque de segurança** que PROD_C!

---

## Alterações Implementadas

### 1. Interface Web ([templates/reabastecimento.html](templates/reabastecimento.html))

**Removido:**
```html
<div class="config-compact">
    <label for="nivel_servico">Nível de Serviço:</label>
    <input type="number" id="nivel_servico" name="nivel_servico" value="0.95" ...>
</div>
```

**Adicionado:**
```html
<!-- Campo oculto (valor padrão usado apenas como fallback) -->
<input type="hidden" id="nivel_servico" name="nivel_servico" value="0.95">

<!-- Aviso ao usuário -->
<div style="background: #fff3cd; ...">
    <strong>💡 Nível de Serviço:</strong><br>
    Agora definido por item no arquivo de entrada
</div>
```

### 2. Backend ([core/replenishment_calculator.py](core/replenishment_calculator.py:270-271))

**JÁ IMPLEMENTADO:**
```python
# Usar nível de serviço específico do item, se disponível
if 'Nivel_Servico' in row and pd.notna(row['Nivel_Servico']):
    calc = ReplenishmentCalculator(row['Nivel_Servico'])
```

O backend **já suportava** nível de serviço por item desde a versão inicial!

### 3. Arquivo Exemplo ([gerar_exemplo_reabastecimento.py](gerar_exemplo_reabastecimento.py))

**NOVO:** Script que gera arquivo exemplo com:
- 6 itens de exemplo
- Níveis de serviço variados (0.90 a 0.99)
- 12 meses de histórico
- Instruções completas

---

## Benefícios

### 1. Otimização de Capital de Giro
✅ Produtos C têm menos estoque de segurança
✅ Libera capital para investir em produtos A
✅ Melhor ROI do estoque

### 2. Gestão Mais Refinada
✅ Cada item tem tratamento adequado à sua criticidade
✅ Produtos estratégicos sempre disponíveis
✅ Produtos de cauda longa não travam capital

### 3. Flexibilidade
✅ Fácil ajustar nível de serviço por item
✅ Permite estratégias diferenciadas por categoria
✅ Adaptação rápida a mudanças de mercado

### 4. Transparência
✅ Usuário vê e controla o nível de serviço de cada item
✅ Decisões conscientes sobre investimento em estoque
✅ Auditoria facilitada

---

## Como Usar

### Passo 1: Classificar seus Produtos

Analise seu portfólio e classifique em A, B, C:

```python
# Critérios sugeridos:
- Produtos A: Top 20% em faturamento → 99%
- Produtos B: 30% seguintes → 95%
- Produtos C: 50% restantes → 90%
```

### Passo 2: Preencher a Planilha

No arquivo `exemplo_reabastecimento_automatico.xlsx`:

```
| Loja    | SKU      | ... | Nivel_Servico |
|---------|----------|-----|---------------|
| LOJA_01 | PROD_001 | ... | 0.99          |  ← Produto A
| LOJA_01 | PROD_002 | ... | 0.95          |  ← Produto B
| LOJA_01 | PROD_003 | ... | 0.90          |  ← Produto C
```

### Passo 3: Upload e Processamento

1. Acesse: `http://localhost:5001/reabastecimento`
2. Faça upload do arquivo
3. Sistema calculará estoque de segurança individualizado
4. Download do relatório com recomendações

---

## Validações

### Valores Aceitos

- **Mínimo:** 0.80 (80%) - não recomendado
- **Máximo:** 0.99 (99%) - limite prático
- **Formato:** Decimal com ponto (0.95, não 95%)

### Tratamento de Erros

**Se `Nivel_Servico` não for informado:**
- Sistema usa valor padrão: 0.95 (95%)
- Aviso no log de processamento

**Se valor for inválido:**
- Sistema corrige para faixa 0.80 - 0.99
- Log indica o ajuste realizado

---

## Compatibilidade

### Arquivos Antigos
❌ Arquivos sem coluna `Nivel_Servico` usarão padrão 0.95
✅ Recomenda-se adicionar a coluna aos arquivos existentes

### API
✅ Endpoint `/processar_reabastecimento` continua funcionando
✅ Parâmetro `nivel_servico` global mantido como fallback
✅ Prioridade: Item > Global > Padrão (0.95)

---

## Arquivo de Exemplo

Para gerar novo arquivo exemplo:

```bash
cd previsao-demanda
python gerar_exemplo_reabastecimento.py
```

Estrutura gerada:
- Aba 1: ESTOQUE_ATUAL (6 itens com níveis variados)
- Aba 2: HISTORICO_VENDAS (12 meses)
- Aba 3: INSTRUCOES (guia completo)

---

**Status:** ✅ Implementado e testado
**Versão:** 2.2
**Impacto:** Melhoria significativa na gestão de estoque
