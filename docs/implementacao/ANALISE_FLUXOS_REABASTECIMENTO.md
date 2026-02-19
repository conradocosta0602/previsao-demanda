# Análise de Fluxos de Reabastecimento - Melhorias Necessárias

**Data:** 2024-12-29
**Versão:** 2.2

---

## 1. FLUXOS DE REABASTECIMENTO IDENTIFICADOS

### Fluxo 1: Fornecedor → Centro de Distribuição (CD)
**Características:**
- ✅ Ciclos mais longos (mensal, quinzenal)
- ✅ Pedidos maiores (fechar carreta/palete)
- ✅ Lead time mais longo (7-30 dias)
- ✅ Foco em economia de escala
- ⚠️ Pode ser manual ou automático

### Fluxo 2: Fornecedor → Loja Direta
**Características:**
- ✅ Ciclos variados (semanal, quinzenal)
- ✅ Pedidos para fechar carreta/palete
- ✅ Lead time médio (5-15 dias)
- ✅ Produtos específicos (grande volume, perecíveis)
- ⚠️ Pode ser manual ou automático

### Fluxo 3: CD → Loja
**Características:**
- ✅ Ciclos curtos (diário, 2-3x semana)
- ✅ Pedidos fracionados
- ✅ Lead time curto (1-3 dias)
- ✅ Atende demanda + parâmetros de exposição
- ⚠️ Pode ser manual ou automático

### Fluxo 4: Loja → Loja (Transferência)
**Características:**
- ✅ Pedidos emergenciais ou balanceamento
- ✅ Lead time muito curto (0-1 dia)
- ✅ Quantidades variadas
- ✅ Reposição de venda ou ajuste de mix
- ⚠️ Geralmente manual

---

## 2. LACUNAS IDENTIFICADAS NA FERRAMENTA ATUAL

### ❌ Lacuna 1: Tipo de Fluxo Não Identificado
**Problema:**
- Sistema não diferencia origem/destino do pedido
- Não há campo para indicar: Fornecedor→CD, CD→Loja, etc.
- Regras de cálculo são iguais para todos os fluxos

**Impacto:**
- CD pode receber recomendações inadequadas (ciclo curto demais)
- Lojas podem receber sugestões de pedidos muito grandes
- Não considera economia de escala para fluxos upstream

---

### ❌ Lacuna 2: Consolidação de Carga (Carreta/Palete)
**Problema:**
- Sistema não tem conceito de "múltiplo de palete" ou "múltiplo de carreta"
- Apenas valida "lote mínimo" (caixa)
- Não otimiza pedidos para fechar caminhões

**Impacto:**
- Pedidos Fornecedor→CD podem ficar sub-otimizados
- Não aproveita frete cheio (mais econômico)
- Pode gerar muitos pedidos pequenos quando deveria consolidar

**Exemplo Real:**
```
Produto A: Recomenda 500 unidades
Produto B: Recomenda 300 unidades
Total: 800 unidades (1.2 paletes)

Ideal: Ajustar para 1000 unidades (2 paletes cheios)
```

---

### ❌ Lacuna 3: Múltiplas Origens para o Mesmo SKU
**Problema:**
- Sistema não gerencia quando um SKU pode vir de:
  - Fornecedor direto (lead time 15 dias)
  - CD (lead time 2 dias)
- Não há priorização de origem

**Impacto:**
- Loja não sabe se deve pedir do CD ou do fornecedor
- Pode ter estoque no CD mas sistema recomenda do fornecedor
- Risco de duplicação de pedidos

---

### ❌ Lacuna 4: Parâmetros de Exposição (Loja)
**Problema:**
- Sistema não considera:
  - Estoque mínimo de gôndola
  - Quantidade de frentes
  - Necessidade de sortimento
- Foca apenas em demanda estatística

**Impacto:**
- Pode recomendar quantidade insuficiente para exposição adequada
- Lojas podem ficar com gôndola vazia mesmo "tendo estoque"
- Não atende regras de merchandising

---

### ❌ Lacuna 5: Ciclo de Revisão Fixo por Item
**Problema:**
- Sistema usa período de revisão GLOBAL (7 dias padrão)
- Não diferencia ciclo por tipo de fluxo
- Não adapta ciclo ao tipo de produto

**Impacto:**
- CD deveria ter ciclo mais longo (14-30 dias)
- Loja deveria ter ciclo curto (1-7 dias)
- Produtos perecíveis precisam ciclo diferente

**Exemplo:**
```
ATUAL:
- Todos os itens: revisão a cada 7 dias

IDEAL:
- Fornecedor→CD: 30 dias
- CD→Loja: 2 dias
- Loja→Loja: 0 dias (emergencial)
```

---

### ❌ Lacuna 6: Transferências Entre Lojas
**Problema:**
- Sistema não tem módulo específico para transferências
- Não identifica lojas doadoras com excesso
- Não sugere balanceamento de estoque

**Impacto:**
- Loja A pode ter excesso enquanto Loja B tem ruptura
- Oportunidade de transferir antes de pedir novo estoque
- Custo de oportunidade (venda perdida)

---

### ❌ Lacuna 7: Restrições de Capacidade
**Problema:**
- Não considera:
  - Capacidade de armazenamento do CD
  - Capacidade de recebimento da loja
  - Capacidade de área de venda
- Pode recomendar pedidos maiores que a capacidade física

**Impacto:**
- Pedidos não executáveis
- Necessidade de ajuste manual
- Perda de confiança na ferramenta

---

### ❌ Lacuna 8: Custo de Transporte Diferenciado
**Problema:**
- Sistema não considera:
  - Custo frete fornecedor vs CD
  - Desconto por volume (carreta cheia)
  - Frete FOB vs CIF
- Foca apenas em quantidade, não em custo total

**Impacto:**
- Decisões sub-ótimas de sourcing
- Não maximiza economia de frete
- Pode escolher origem mais cara

---

## 3. MELHORIAS PROPOSTAS POR PRIORIDADE

### 🔴 PRIORIDADE 1 - CRÍTICA (Implementar Primeiro)

#### Melhoria 1.1: Campo "Tipo de Fluxo"
**Adicionar ao arquivo de entrada:**

```
Nova coluna: Tipo_Fluxo

Valores possíveis:
- FORNECEDOR_CD
- FORNECEDOR_LOJA
- CD_LOJA
- LOJA_LOJA
```

**Impacto:**
- Sistema pode aplicar regras diferentes por fluxo
- Ciclos de revisão adequados
- Múltiplos de embalagem corretos

**Alterações necessárias:**
- [x] Adicionar coluna `Tipo_Fluxo` em ESTOQUE_ATUAL
- [x] Backend: lógica condicional baseada no tipo
- [x] Definir parâmetros padrão por tipo de fluxo

---

#### Melhoria 1.2: Ciclo de Revisão por Tipo de Fluxo
**Implementar tabela de ciclos padrão:**

```python
CICLOS_PADRAO = {
    'FORNECEDOR_CD': 30,      # Mensal
    'FORNECEDOR_LOJA': 14,    # Quinzenal
    'CD_LOJA': 2,             # 2x semana
    'LOJA_LOJA': 1            # Diário (emergencial)
}
```

**Impacto:**
- Quantidades adequadas ao ciclo de cada fluxo
- Menos pedidos urgentes
- Melhor planejamento

**Alterações necessárias:**
- [x] Adicionar campo `Ciclo_Revisao_Dias` (opcional)
- [x] Se não informado, usar padrão do Tipo_Fluxo
- [x] Backend: calcular demanda_revisao baseado no ciclo correto

---

#### Melhoria 1.3: Múltiplos de Consolidação
**Adicionar campos:**

```
Nova coluna: Multiplo_Palete (opcional, padrão: 0)
Nova coluna: Multiplo_Carreta (opcional, padrão: 0)
```

**Lógica:**
```
1. Calcular quantidade base (atual)
2. Ajustar para Lote_Minimo (caixa) - JÁ EXISTE
3. Se Multiplo_Palete > 0: ajustar para múltiplo de palete
4. Se Multiplo_Carreta > 0: ajustar para múltiplo de carreta
```

**Exemplo:**
```
Quantidade calculada: 850 unidades
Lote_Minimo (caixa): 12 → 852 unidades (71 caixas)
Multiplo_Palete: 240 → 960 unidades (4 paletes × 240)
Multiplo_Carreta: 2400 → 2400 unidades (1 carreta)
```

**Alterações necessárias:**
- [x] Adicionar colunas `Multiplo_Palete` e `Multiplo_Carreta`
- [x] Backend: método `ajustar_para_consolidacao()`
- [x] Relatório: mostrar "Paletes" e "Carretas" se aplicável

---

### 🟡 PRIORIDADE 2 - IMPORTANTE (Implementar em Seguida)

#### Melhoria 2.1: Parâmetros de Exposição
**Adicionar campos:**

```
Nova coluna: Estoque_Minimo_Gondola (opcional, padrão: 0)
Nova coluna: Numero_Frentes (opcional, padrão: 1)
```

**Lógica:**
```
Quantidade mínima = MAX(
    Ponto_Pedido,
    Estoque_Minimo_Gondola × Numero_Frentes
)
```

**Impacto:**
- Garante exposição adequada
- Atende regras de merchandising
- Evita gôndola vazia

**Alterações necessárias:**
- [x] Adicionar colunas de exposição
- [x] Backend: calcular quantidade_minima_exposicao
- [x] Ajustar ponto de pedido se necessário

---

#### Melhoria 2.2: Múltiplas Origens (Sourcing)
**Adicionar estrutura:**

```
Nova aba: ORIGENS_DISPONIVEIS

Colunas:
- Loja (destino)
- SKU
- Origem (FORNECEDOR_A, CD_PRINCIPAL, CD_REGIONAL)
- Lead_Time_Dias
- Custo_Unitario
- Custo_Frete
- Estoque_Origem (disponível na origem)
- Prioridade (1=primeira escolha, 2=segunda, etc.)
```

**Lógica:**
```
1. Calcular necessidade
2. Verificar Origem Prioridade 1
   - Se tem estoque suficiente: usar
   - Se não: complementar com Prioridade 2
3. Considerar custo total (produto + frete)
```

**Impacto:**
- Otimiza sourcing
- Reduz custo total
- Aproveita estoque em trânsito entre níveis

**Alterações necessárias:**
- [x] Nova aba ORIGENS_DISPONIVEIS
- [x] Backend: classe `SourcingOptimizer`
- [x] Relatório: mostrar origem escolhida e custo

---

#### Melhoria 2.3: Restrições de Capacidade
**Adicionar campos:**

```
Nova coluna: Capacidade_Maxima_Armazenamento (opcional)
Nova coluna: Capacidade_Maxima_Recebimento_Diario (opcional)
```

**Lógica:**
```
Validar:
- Estoque atual + Pedido < Capacidade_Armazenamento
- Pedido / Ciclo_Revisao < Capacidade_Recebimento_Diario

Se exceder: alertar e sugerir split do pedido
```

**Impacto:**
- Evita pedidos não executáveis
- Alerta sobre limitações físicas
- Sugere alternativas viáveis

**Alterações necessárias:**
- [x] Adicionar colunas de capacidade
- [x] Backend: validação de capacidade
- [x] Relatório: alertas de capacidade excedida

---

### 🟢 PRIORIDADE 3 - DESEJÁVEL (Implementar Posteriormente)

#### Melhoria 3.1: Módulo de Transferências
**Novo módulo: Sugestão de Transferências Loja→Loja**

**Lógica:**
```
1. Identificar lojas com excesso:
   - Cobertura > 2× média da rede
   - Estoque > Ponto_Pedido + 50%

2. Identificar lojas com necessidade:
   - Em risco de ruptura
   - Estoque < Ponto_Pedido

3. Sugerir transferências:
   - Priorizar proximidade geográfica
   - Considerar custo de transferência
   - Validar tempo de trânsito
```

**Impacto:**
- Reduz rupturas sem novos pedidos
- Balanceia estoque da rede
- Reduz obsolescência

**Alterações necessárias:**
- [x] Novo módulo: `/transferencias`
- [x] Backend: `TransferOptimizer`
- [x] Arquivo entrada: dados agregados de toda rede

---

#### Melhoria 3.2: Otimização de Frete
**Adicionar análise de trade-off:**

```
Calcular:
- Custo pedido atual: Quantidade × Custo_Unit + Frete
- Custo pedido consolidado: Qtd_Maior × Custo_Unit + Frete_Cheio
- Custo estoque extra: (Qtd_Maior - Qtd_Atual) × Custo_Oportunidade

Sugerir consolidação se:
Economia_Frete > Custo_Estoque_Extra
```

**Impacto:**
- Decisões baseadas em custo total
- Maximiza economia de escala
- Trade-off explícito

---

#### Melhoria 3.3: Dashboard de Visão de Rede
**Visualização agregada:**
```
- Estoque total por SKU em toda rede
- Distribuição: CD vs Lojas
- Cobertura média da rede
- Oportunidades de transferência
- Pedidos em trânsito por nível
```

**Impacto:**
- Visão holística
- Decisões de rede (não apenas local)
- Identifica desequilíbrios

---

## 4. ESTRUTURA PROPOSTA DO ARQUIVO ATUALIZADO

### Arquivo: exemplo_reabastecimento_multifluxo.xlsx

#### ABA 1: ESTOQUE_ATUAL (ATUALIZADA)

| Coluna | Tipo | Obrigatório | Novo? | Descrição |
|--------|------|-------------|-------|-----------|
| Loja | Texto | Sim | Não | Código da loja/CD |
| SKU | Texto | Sim | Não | Código do produto |
| **Tipo_Fluxo** | **Texto** | **Sim** | **✅ SIM** | **FORNECEDOR_CD, CD_LOJA, etc** |
| Lead_Time_Dias | Inteiro | Sim | Não | Tempo de reposição |
| Estoque_Disponivel | Número | Sim | Não | Estoque físico |
| Nivel_Servico | Decimal | Sim | Não | 0.90 a 0.99 |
| **Ciclo_Revisao_Dias** | **Inteiro** | **Não** | **✅ SIM** | **Padrão: baseado em Tipo_Fluxo** |
| Estoque_Transito | Número | Não | Não | Padrão: 0 |
| Pedidos_Abertos | Número | Não | Não | Padrão: 0 |
| Lote_Minimo | Inteiro | Não | Não | Padrão: 1 (caixa) |
| **Multiplo_Palete** | **Inteiro** | **Não** | **✅ SIM** | **Padrão: 0 (não usar)** |
| **Multiplo_Carreta** | **Inteiro** | **Não** | **✅ SIM** | **Padrão: 0 (não usar)** |
| **Estoque_Min_Gondola** | **Inteiro** | **Não** | **✅ SIM** | **Padrão: 0 (CD não tem)** |
| **Numero_Frentes** | **Inteiro** | **Não** | **✅ SIM** | **Padrão: 1** |
| **Capacidade_Max_Armazenamento** | **Número** | **Não** | **✅ SIM** | **Padrão: 999999** |

#### ABA 2: HISTORICO_VENDAS (SEM ALTERAÇÃO)
Mantém estrutura atual.

#### ABA 3: ORIGENS_DISPONIVEIS (NOVA - PRIORIDADE 2)

| Coluna | Tipo | Obrigatório | Descrição |
|--------|------|-------------|-----------|
| Loja | Texto | Sim | Destino do pedido |
| SKU | Texto | Sim | Código do produto |
| Origem | Texto | Sim | ID da origem (FORN_A, CD_01) |
| Lead_Time_Dias | Inteiro | Sim | Lead time dessa origem |
| Custo_Unitario | Decimal | Não | Custo por unidade |
| Custo_Frete | Decimal | Não | Custo frete dessa origem |
| Estoque_Origem | Número | Não | Disponível na origem |
| Prioridade | Inteiro | Sim | 1=preferencial, 2=alternativa |

---

## 5. EXEMPLO PRÁTICO DE USO

### Cenário: CD comprando de Fornecedor

**Entrada:**
```
Loja: CD_PRINCIPAL
SKU: PROD_001
Tipo_Fluxo: FORNECEDOR_CD
Lead_Time_Dias: 15
Estoque_Disponivel: 5000
Nivel_Servico: 0.95
Ciclo_Revisao_Dias: 30 (mensal)
Lote_Minimo: 12 (caixa)
Multiplo_Palete: 240 (20 caixas/palete)
Multiplo_Carreta: 4800 (20 paletes/carreta)
Demanda_Media_Mensal: 3000
```

**Cálculo Sistema Atual:**
```
Demanda diária: 3000/30 = 100 un/dia
Demanda lead time: 100 × 15 = 1500
Estoque segurança: ~400 (Z=1.64)
Ponto pedido: 1500 + 400 = 1900

Demanda revisão: 100 × 7 = 700 (PROBLEMA: ciclo errado!)
Qtd necessária: 1900 + 700 - 5000 = -2400
Resultado: Não pedir (tem estoque suficiente)
```

**Cálculo Sistema MELHORADO:**
```
Demanda diária: 100 un/dia
Demanda lead time: 1500
Estoque segurança: 400
Ponto pedido: 1900

Demanda revisão: 100 × 30 = 3000 (ciclo correto!)
Qtd necessária: 1900 + 3000 - 5000 = -100
Resultado: Não pedir (tem estoque suficiente)

MAS: Previsão para próximo ciclo (30 dias):
Estoque final = 5000 - 3000 = 2000
Se 2000 > 1900: OK, aguardar
Se 2000 < 1900: Pedir agora

Quantidade a pedir: 3000 (demanda próximo ciclo)
Ajuste caixa: 3000 → 3000 (já é múltiplo de 12)
Ajuste palete: 3000 → 3120 (13 paletes × 240)
Ajuste carreta: 3120 → 4800 (1 carreta)

SUGESTÃO FINAL: 4800 unidades (1 carreta cheia)
Economia frete: 30% vs carga fracionada
Cobertura: 4800/100 = 48 dias (adequado para ciclo mensal)
```

---

### Cenário: Loja comprando de CD

**Entrada:**
```
Loja: LOJA_01
SKU: PROD_001
Tipo_Fluxo: CD_LOJA
Lead_Time_Dias: 2
Estoque_Disponivel: 15
Nivel_Servico: 0.99
Ciclo_Revisao_Dias: 2 (2x por semana)
Lote_Minimo: 6 (caixa)
Estoque_Min_Gondola: 12 (2 caixas na frente)
Numero_Frentes: 3
Demanda_Media_Mensal: 120
```

**Cálculo Sistema MELHORADO:**
```
Demanda diária: 120/30 = 4 un/dia
Demanda lead time: 4 × 2 = 8
Estoque segurança: ~10 (Z=2.33, alto nível serviço)
Ponto pedido estatístico: 8 + 10 = 18

NOVO: Validar exposição
Estoque mínimo gôndola: 12 × 3 = 36 unidades

Ponto pedido REAL: MAX(18, 36) = 36 unidades

Demanda revisão: 4 × 2 = 8
Qtd necessária: 36 + 8 - 15 = 29
Ajuste caixa: 29 → 30 (5 caixas × 6)

SUGESTÃO FINAL: 30 unidades
Cobertura: (15 + 30) / 4 = 11.2 dias
Frentes cobertas: 45 / 12 = 3.75 frentes (OK!)
```

---

## 6. ROADMAP DE IMPLEMENTAÇÃO

### FASE 1 - Básico Multifluxo (Sprint 1 - 2 semanas)
- [ ] Adicionar campo `Tipo_Fluxo`
- [ ] Adicionar campo `Ciclo_Revisao_Dias` (opcional)
- [ ] Backend: lógica condicional baseada em Tipo_Fluxo
- [ ] Definir ciclos padrão por tipo
- [ ] Atualizar arquivo exemplo
- [ ] Documentação atualizada

**Entregável:** Sistema diferencia fluxos e usa ciclos adequados

---

### FASE 2 - Consolidação de Carga (Sprint 2 - 2 semanas)
- [ ] Adicionar campos `Multiplo_Palete` e `Multiplo_Carreta`
- [ ] Backend: método `ajustar_para_consolidacao()`
- [ ] Relatório: mostrar paletes/carretas
- [ ] Análise de economia de frete
- [ ] Atualizar exemplos

**Entregável:** Sistema recomenda consolidação de carga

---

### FASE 3 - Parâmetros de Exposição (Sprint 3 - 1 semana)
- [ ] Adicionar `Estoque_Min_Gondola` e `Numero_Frentes`
- [ ] Backend: validar quantidade mínima de exposição
- [ ] Ajustar ponto de pedido
- [ ] Atualizar exemplos para lojas

**Entregável:** Sistema garante exposição adequada

---

### FASE 4 - Múltiplas Origens (Sprint 4-5 - 3 semanas)
- [ ] Nova aba ORIGENS_DISPONIVEIS
- [ ] Backend: classe `SourcingOptimizer`
- [ ] Lógica de priorização
- [ ] Cálculo de custo total
- [ ] Relatório com origem escolhida
- [ ] Interface de configuração

**Entregável:** Sistema sugere melhor origem (sourcing)

---

### FASE 5 - Restrições de Capacidade (Sprint 6 - 1 semana)
- [ ] Adicionar campos de capacidade
- [ ] Validações no backend
- [ ] Alertas no relatório
- [ ] Sugestão de split de pedidos

**Entregável:** Sistema valida viabilidade física

---

### FASE 6 - Transferências (Sprint 7-8 - 3 semanas)
- [ ] Novo módulo `/transferencias`
- [ ] Backend: `TransferOptimizer`
- [ ] Identificar lojas doadoras/receptoras
- [ ] Cálculo de custo de transferência
- [ ] Interface de aprovação
- [ ] Relatório de oportunidades

**Entregável:** Sistema sugere transferências entre lojas

---

## 7. BENEFÍCIOS ESPERADOS

### Quantificáveis
- ✅ **Redução de 30-40%** em pedidos urgentes (ciclos adequados)
- ✅ **Economia de 15-25%** em frete (consolidação de carga)
- ✅ **Redução de 20%** em rupturas (melhor exposição + sourcing)
- ✅ **Redução de 10-15%** em estoque total (transferências)

### Qualitativos
- ✅ Maior confiança na ferramenta (recomendações executáveis)
- ✅ Menos ajustes manuais necessários
- ✅ Decisões baseadas em custo total, não apenas quantidade
- ✅ Visão de rede (não apenas pontual)

---

## 8. COMPATIBILIDADE COM VERSÃO ATUAL

### ✅ Retrocompatibilidade Garantida
Todos os campos novos são **OPCIONAIS**:
- Arquivos antigos continuam funcionando
- Se `Tipo_Fluxo` não informado: assume `CD_LOJA` (comportamento atual)
- Se `Ciclo_Revisao_Dias` não informado: usa padrão baseado em Tipo_Fluxo
- Se campos de consolidação não informados: usa apenas `Lote_Minimo`

---

**Status:** 📋 Análise completa - Aguardando aprovação para implementação
**Próximo Passo:** Definir prioridades e iniciar FASE 1
