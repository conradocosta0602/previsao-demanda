# Guia: Modos de Cálculo de Reabastecimento

## 📋 Visão Geral

O sistema oferece **2 modos de operação** para cálculo de reabastecimento:

1. **Automático (Recomendado)** - Sistema calcula demanda automaticamente do histórico
2. **Manual (Excepcional)** - Você fornece demanda média e desvio padrão previamente calculados

---

## 🤖 Modo AUTOMÁTICO (Recomendado)

### Por que usar?
✅ **Elimina erros humanos** - Sistema calcula demanda com métodos estatísticos avançados
✅ **Detecta padrões automaticamente** - Identifica tendências, sazonalidade, intermitência
✅ **Escolhe melhor método** - Auto, EMA, Tendência, Sazonal ou Croston
✅ **Sem necessidade de conhecimento técnico** - Basta fornecer histórico de vendas
✅ **Mais assertivo** - Até 95% mais preciso que média simples em alguns casos

### Quando usar?
- **Sempre que possível** (padrão recomendado)
- Você tem histórico de vendas disponível
- Quer otimizar estoque de segurança
- Quer evitar erros de cálculo manual

### Arquivo de Entrada

**Estrutura Obrigatória:**

| Coluna | Descrição | Exemplo |
|--------|-----------|---------|
| `Loja` | Código da filial | LOJA_01 |
| `SKU` | Código do produto | SKU_001 |
| `Mes` | Mês do histórico | 2024-01-01 |
| `Vendas` | Quantidade vendida no mês | 150 |
| `Lead_Time_Dias` | Tempo de entrega (dias) | 15 |
| `Estoque_Disponivel` | Estoque atual | 80 |

**Colunas Opcionais:**
- `Estoque_Transito` - Pedidos enviados mas não recebidos
- `Pedidos_Abertos` - Pedidos feitos mas não confirmados
- `Lote_Minimo` - Quantidade mínima por pedido

### Formato do Arquivo

```
Loja    | SKU     | Mes        | Vendas | Lead_Time_Dias | Estoque_Disponivel
--------|---------|------------|--------|----------------|-------------------
LOJA_01 | SKU_001 | 2024-01-01 | 100    |                |
LOJA_01 | SKU_001 | 2024-02-01 | 105    |                |
LOJA_01 | SKU_001 | 2024-03-01 | 98     |                |
...
LOJA_01 | SKU_001 | 2024-12-01 | 110    | 15             | 80
```

**Importante:**
- Cada combinação Loja+SKU deve ter **múltiplas linhas** (uma por mês)
- `Lead_Time_Dias` e `Estoque_Disponivel` **apenas na última linha** de cada item
- Mínimo de **3 meses de histórico** (recomendado: 6-12 meses)

### Arquivo de Exemplo
✅ [exemplo_reabastecimento_automatico.xlsx](exemplo_reabastecimento_automatico.xlsx)

### Saída do Sistema (Modo Automático)

O Excel gerado terá **3 abas**:

1. **Reabastecimento** - Resultado completo com colunas extras:
   - `Metodo_Usado` - Qual método foi escolhido (ema, tendencia, sazonal, croston, simples)
   - `Padrao_Demanda` - Padrão detectado (estavel, tendencia, sazonal, intermitente, variavel)
   - `Confianca` - Nível de confiança (alta, media, baixa)

2. **Top_10_Urgentes** - 10 itens com maior urgência

3. **Resumo_Metodos** - Quantos itens usaram cada método

### Exemplo de Resultado

```
Loja    | SKU     | Metodo_Usado | Padrao_Demanda | Ponto_Pedido | Qtd_Pedir
--------|---------|--------------|----------------|--------------|----------
LOJA_01 | SKU_001 | ema          | estavel        | 85           | 20
LOJA_01 | SKU_002 | tendencia    | tendencia      | 195          | 50
LOJA_01 | SKU_003 | sazonal      | sazonal        | 150          | 80
LOJA_01 | SKU_004 | croston      | intermitente   | 25           | 10
```

---

## 📝 Modo MANUAL (Excepcional)

### Por que usar?
⚠️ **Apenas em casos excepcionais:**
- Você já tem demanda média calculada por sistema externo
- Não possui histórico de vendas digitalizado
- Produto novo sem histórico
- Necessidade de ajuste manual pontual

### Quando NÃO usar?
❌ Você tem histórico de vendas disponível → Use Automático
❌ Quer evitar erros de cálculo → Use Automático
❌ Não sabe calcular demanda média corretamente → Use Automático

### Arquivo de Entrada

**Estrutura Obrigatória:**

| Coluna | Descrição | Exemplo |
|--------|-----------|---------|
| `Loja` | Código da filial | LOJA_01 |
| `SKU` | Código do produto | SKU_001 |
| `Demanda_Media_Mensal` | Demanda média (você calcula) | 150.0 |
| `Desvio_Padrao_Mensal` | Desvio padrão (você calcula) | 25.0 |
| `Lead_Time_Dias` | Tempo de entrega (dias) | 15 |
| `Estoque_Disponivel` | Estoque atual | 80 |

**Colunas Opcionais:**
- `Estoque_Transito`
- `Pedidos_Abertos`
- `Lote_Minimo`
- `Nivel_Servico` - Nível de serviço específico por item

### Formato do Arquivo

```
Loja    | SKU     | Demanda_Media_Mensal | Desvio_Padrao_Mensal | Lead_Time | Estoque
--------|---------|---------------------|---------------------|-----------|--------
LOJA_01 | SKU_001 | 150.0               | 25.0                | 15        | 80
LOJA_01 | SKU_002 | 200.0               | 40.0                | 10        | 120
LOJA_02 | SKU_001 | 180.0               | 30.0                | 15        | 90
```

**Importante:**
- Cada combinação Loja+SKU é **uma linha apenas**
- Você é responsável por calcular `Demanda_Media_Mensal` e `Desvio_Padrao_Mensal` corretamente
- Erros nesses valores causam estoque de segurança incorreto

### Arquivo de Exemplo
✅ [exemplo_reabastecimento.xlsx](exemplo_reabastecimento.xlsx) (existente)

### Saída do Sistema (Modo Manual)

O Excel gerado terá **2 abas**:
1. **Reabastecimento** - Resultado completo
2. **Top_10_Urgentes** - 10 itens com maior urgência

---

## 📊 Comparação dos Modos

| Aspecto | Modo Automático | Modo Manual |
|---------|----------------|-------------|
| **Facilidade** | ⭐⭐⭐⭐⭐ Muito fácil | ⭐⭐ Requer conhecimento |
| **Acurácia** | ⭐⭐⭐⭐⭐ Muito alta | ⭐⭐⭐ Depende do usuário |
| **Risco de erro** | ⭐⭐⭐⭐⭐ Muito baixo | ⭐⭐ Alto (erro humano) |
| **Detecção de padrões** | ✅ Automático | ❌ Manual |
| **Histórico necessário** | ✅ Sim (3-12 meses) | ❌ Não |
| **Metadata** | ✅ Sim (método, padrão, confiança) | ❌ Não |
| **Quando usar** | **Sempre que possível** | Apenas exceções |

---

## 🎯 Decisão Rápida

**Use AUTOMÁTICO se:**
- ✅ Você tem histórico de vendas
- ✅ Quer otimizar estoque
- ✅ Quer evitar erros
- ✅ Não sabe calcular demanda estatisticamente

**Use MANUAL apenas se:**
- ⚠️ Sistema externo já calculou demanda
- ⚠️ Produto novo sem histórico
- ⚠️ Ajuste pontual excepcional
- ⚠️ Não tem histórico digitalizado

---

## 💡 Dicas

### Modo Automático
1. **Mínimo 6 meses de histórico** para melhor acurácia
2. **12 meses ideal** para detectar sazonalidade
3. **Remova períodos atípicos** (ex: COVID, greves) se necessário
4. **Última linha** de cada item deve ter dados de estoque

### Modo Manual
1. **Use Excel** `=MÉDIA()` e `=DESVPAD.P()` para calcular
2. **Considere tendências** manualmente se crescimento/queda
3. **Ajuste para sazonalidade** se aplicável
4. **Valide os valores** - demanda e desvio devem fazer sentido

---

## ❓ FAQ

**P: Posso misturar os dois modos?**
R: Não. Escolha um modo por upload. Se precisar dos dois, faça uploads separados.

**P: O modo automático usa qual método?**
R: Depende! O sistema analisa cada item e escolhe automaticamente entre: EMA, Tendência, Sazonal, Croston ou Simples.

**P: Como sei qual método foi usado?**
R: No modo automático, a coluna `Metodo_Usado` mostra qual foi escolhido para cada item.

**P: Posso forçar um método específico?**
R: Não pela interface (decisão de UX). Mas você pode usar a função `processar_reabastecimento_com_historico()` diretamente no código Python.

**P: Qual modo é mais rápido?**
R: Ambos processam em segundos. A diferença está na **preparação do arquivo**.

**P: Modo manual é menos confiável?**
R: Depende! Se você calcular demanda corretamente, funciona bem. Mas o automático elimina erros humanos e detecta padrões que você pode não perceber.

---

## 📚 Recursos Adicionais

- [MELHORIAS_CALCULO_DEMANDA.md](MELHORIAS_CALCULO_DEMANDA.md) - Detalhes técnicos dos métodos
- [DOCUMENTACAO_CALCULO_REABASTECIMENTO.md](DOCUMENTACAO_CALCULO_REABASTECIMENTO.md) - Fórmulas e exemplos
- `exemplo_demanda_inteligente.py` - Demonstração comparativa

---

**Versão**: 2.0
**Data**: Dezembro 2024
**Recomendação**: Use **Modo Automático** sempre que possível!
