# Guia de Uso: Pedidos Manuais Integrados

## 🎯 Visão Geral

Os módulos de **Pedido por Quantidade** e **Pedido por Cobertura** foram integrados ao sistema de reabastecimento, criando uma ferramenta completa e unificada.

---

## 🚀 Como Acessar

### A partir do navegador:

1. Inicie o sistema: `python app.py`
2. Acesse: `http://localhost:5001`
3. Clique em "Reabastecimento Inteligente"
4. Na barra lateral, veja a seção **"Pedido Manual"** com duas opções:
   - 📦 **Por Quantidade** → `/pedido_quantidade`
   - 📅 **Por Cobertura** → `/pedido_cobertura`

---

## 📦 Módulo 1: Pedido por Quantidade

### **Para que serve:**
Você informa a quantidade desejada, o sistema valida e ajusta para múltiplo de caixa automaticamente.

### **Quando usar:**
- Quando você já sabe exatamente quantas unidades quer pedir
- Quando precisa validar se a quantidade está em múltiplo de caixa
- Quando quer garantir embalagens completas

### **Como usar:**

1. **Acesse:** `http://localhost:5001/pedido_quantidade`

2. **Baixe o exemplo:** Clique em "arquivo exemplo" na tela
   - Ou use: `exemplo_pedido_quantidade.xlsx`

3. **Preencha a planilha:**
   ```
   Loja        | SKU      | Quantidade_Desejada | Unidades_Por_Caixa | Demanda_Diaria | Estoque_Disponivel
   ------------|----------|---------------------|--------------------|-----------------|-----------------
   LOJA_01     | PROD_001 | 100                 | 12                 | 5.5 (opcional)  | 20 (opcional)
   ```

4. **Upload:** Arraste o arquivo ou clique para selecionar

5. **Resultado:** O sistema retorna:
   - **Quantidade_Pedido**: Ajustada para múltiplo (ex: 108)
   - **Numero_Caixas**: Quantas caixas pedir (ex: 9)
   - **Foi_Ajustado**: Se houve ajuste (Sim/Não)
   - **Diferenca_Ajuste**: Quanto foi adicionado (ex: +8)
   - **Cobertura_Pedido_Dias**: Dias de estoque (se informou demanda)

6. **Download:** Clique em "Baixar Excel" para obter relatório completo

### **Exemplo Real:**

```
INPUT:
  Quantidade_Desejada: 100
  Unidades_Por_Caixa: 12

PROCESSAMENTO:
  100 ÷ 12 = 8.33 caixas (não é inteiro!)
  Arredonda para cima: 9 caixas
  9 × 12 = 108 unidades

OUTPUT:
  Quantidade_Pedido: 108
  Numero_Caixas: 9
  Foi_Ajustado: Sim
  Diferenca_Ajuste: +8
  Status: "Ajustado para múltiplo de caixa"
```

---

## 📅 Módulo 2: Pedido por Cobertura

### **Para que serve:**
Você informa quantos dias de cobertura quer ter, o sistema calcula a quantidade necessária automaticamente.

### **Quando usar:**
- Quando você trabalha com meta de cobertura (ex: 30 dias)
- Quando quer garantir estoque para período específico
- Quando precisa considerar estoque atual

### **Como usar:**

1. **Acesse:** `http://localhost:5001/pedido_cobertura`

2. **Baixe o exemplo:** Clique em "arquivo exemplo" na tela
   - Ou use: `exemplo_pedido_cobertura.xlsx`

3. **Preencha a planilha:**
   ```
   Loja    | SKU      | Demanda_Diaria | Cobertura_Desejada_Dias | Unidades_Por_Caixa | Estoque_Disponivel
   --------|----------|----------------|-------------------------|--------------------|-----------------
   LOJA_01 | PROD_001 | 5.5            | 30                      | 12                 | 20 (opcional)
   ```

4. **Upload:** Arraste o arquivo ou clique para selecionar

5. **Resultado:** O sistema retorna:
   - **Cobertura_Atual_Dias**: Dias de estoque atual
   - **Necessidade_Liquida_Dias**: Quanto falta para meta
   - **Quantidade_Pedido**: Quantidade calculada e ajustada
   - **Numero_Caixas**: Quantas caixas pedir
   - **Cobertura_Real_Dias**: Cobertura após pedido
   - **Diferenca_Cobertura**: Diferença vs desejado

6. **Download:** Clique em "Baixar Excel" para obter relatório completo

### **Exemplo Real:**

```
INPUT:
  Demanda_Diaria: 5.5 unidades/dia
  Cobertura_Desejada_Dias: 30
  Estoque_Disponivel: 20
  Unidades_Por_Caixa: 12

PROCESSAMENTO:
  Cobertura atual = 20 ÷ 5.5 = 3.6 dias
  Necessidade = 30 - 3.6 = 26.4 dias
  Quantidade bruta = 26.4 × 5.5 = 145.2 unidades
  Ajuste para múltiplo: 156 unidades (13 caixas × 12)

OUTPUT:
  Quantidade_Pedido: 156
  Numero_Caixas: 13
  Cobertura_Real_Dias: 32.0
  Diferenca_Cobertura: +2.0 dias
  Status: "Ajustado para múltiplo de caixa"
```

---

## 📊 Comparação dos Módulos

| Aspecto | Pedido por Quantidade | Pedido por Cobertura |
|---------|----------------------|---------------------|
| **Input** | Quantidade desejada | Dias de cobertura |
| **Cálculo** | Valida múltiplo | Calcula quantidade |
| **Uso típico** | Pedidos pontuais | Metas de cobertura |
| **Considera estoque** | Opcional | Sim (desconta do cálculo) |
| **Demanda necessária** | Não | Sim |
| **Ajuste** | Para cima (caixa completa) | Para cima (caixa completa) |

---

## 🔄 Fluxo de Trabalho Integrado

### **Cenário 1: Reabastecimento Completo**
1. Use **Reabastecimento Automático** para calcular necessidades
2. Sistema gera ponto de pedido e quantidades
3. Download do relatório

### **Cenário 2: Pedido Rápido por Quantidade**
1. Já sabe as quantidades
2. Use **Pedido por Quantidade**
3. Sistema valida múltiplos de caixa
4. Download do relatório pronto

### **Cenário 3: Pedido com Meta de Cobertura**
1. Tem meta de dias de estoque (ex: 45 dias)
2. Use **Pedido por Cobertura**
3. Sistema calcula quantidade automaticamente
4. Download do relatório pronto

---

## 📝 Estrutura dos Arquivos de Entrada

### **exemplo_pedido_quantidade.xlsx**

**Aba: PEDIDO**
| Coluna | Tipo | Obrigatório | Descrição |
|--------|------|-------------|-----------|
| Loja | Texto | Sim | Código da loja |
| SKU | Texto | Sim | Código do produto |
| Quantidade_Desejada | Número | Sim | Quantidade que você quer |
| Unidades_Por_Caixa | Inteiro | Sim | Unidades por embalagem |
| Demanda_Diaria | Decimal | Não | Para calcular cobertura |
| Estoque_Disponivel | Número | Não | Para calcular cobertura total |

**Aba: INSTRUCOES**
- Instruções completas de uso

---

### **exemplo_pedido_cobertura.xlsx**

**Aba: PEDIDO**
| Coluna | Tipo | Obrigatório | Descrição |
|--------|------|-------------|-----------|
| Loja | Texto | Sim | Código da loja |
| SKU | Texto | Sim | Código do produto |
| Demanda_Diaria | Decimal | Sim | Demanda média diária |
| Cobertura_Desejada_Dias | Inteiro | Sim | Dias de estoque desejados |
| Unidades_Por_Caixa | Inteiro | Sim | Unidades por embalagem |
| Estoque_Disponivel | Número | Não | Estoque atual (desconta) |

**Aba: INSTRUCOES**
- Instruções completas de uso

---

## 📥 Arquivos de Saída

### **Pedido por Quantidade:** `pedido_quantidade_YYYYMMDD_HHMMSS.xlsx`

**Aba 1: Pedido**
- Todos os itens com validações e ajustes

**Aba 2: Itens_Ajustados** (se houver)
- Apenas itens que foram ajustados para múltiplo de caixa

---

### **Pedido por Cobertura:** `pedido_cobertura_YYYYMMDD_HHMMSS.xlsx`

**Aba 1: Pedido**
- Todos os itens com cálculos de cobertura

**Aba 2: Sem_Necessidade** (se houver)
- Itens que já têm cobertura suficiente (qtd = 0)

**Aba 3: Itens_Ajustados** (se houver)
- Itens ajustados para múltiplo de caixa

---

## 💡 Dicas e Boas Práticas

### **Pedido por Quantidade:**
1. ✓ Sempre informe Unidades_Por_Caixa correto
2. ✓ Se tiver demanda, informe para ver cobertura
3. ✓ Revise itens ajustados no relatório
4. ✓ Sistema sempre arredonda para cima (garante estoque)

### **Pedido por Cobertura:**
1. ✓ Informe estoque atual para cálculo preciso
2. ✓ Use demanda diária real/média
3. ✓ Defina meta de cobertura por categoria (A=45d, B=30d, C=15d)
4. ✓ Revise itens "Sem Necessidade" (já têm estoque)
5. ✓ Cobertura real pode ser maior que desejada (múltiplo de caixa)

---

## 🎯 Casos de Uso Reais

### **Caso 1: Loja com meta de 30 dias**
- **Módulo:** Pedido por Cobertura
- **Input:** Demanda diária de cada SKU + Meta 30 dias
- **Resultado:** Quantidades exatas para 30 dias (±ajuste)

### **Caso 2: Promoção com volume definido**
- **Módulo:** Pedido por Quantidade
- **Input:** Quantidade necessária da promoção
- **Resultado:** Validação de múltiplo de caixa

### **Caso 3: Reposição CD → Loja**
- **Módulo:** Pedido por Cobertura
- **Input:** Demanda + Meta por loja
- **Resultado:** Transferências calculadas automaticamente

---

## 🔧 Navegação Rápida

De qualquer tela, você pode navegar para:

```
Reabastecimento
    ├─ 📦 Pedido por Quantidade
    ├─ 📅 Pedido por Cobertura
    └─ ← Voltar para Previsão

Pedido por Quantidade
    ├─ 📅 Pedido por Cobertura
    └─ ← Voltar

Pedido por Cobertura
    ├─ 📦 Pedido por Quantidade
    └─ ← Voltar
```

---

## ✅ Checklist de Uso

### **Antes de processar:**
- [ ] Arquivo Excel no formato correto (.xlsx)
- [ ] Todas as colunas obrigatórias preenchidas
- [ ] Unidades_Por_Caixa > 0
- [ ] Demanda_Diaria > 0 (para cobertura)
- [ ] Valores numéricos válidos

### **Após processar:**
- [ ] Revisar resumo (total itens, caixas, unidades)
- [ ] Verificar itens ajustados
- [ ] Conferir cobertura calculada
- [ ] Download do Excel
- [ ] Emitir pedido no ERP

---

## 📞 Suporte

**Dúvidas sobre:**
- Módulo de Quantidade → Ver instruções na tela
- Módulo de Cobertura → Ver instruções na tela
- Erros de processamento → Verificar formato do arquivo

**Arquivos de exemplo:**
- Baixe diretamente nas telas de upload
- Ou use os arquivos na raiz do sistema

---

**Última atualização:** 2024-12-29
**Versão do sistema:** 2.0
