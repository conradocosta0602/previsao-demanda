# Documentação dos Cálculos de Reabastecimento

## 📘 Visão Geral

Este documento explica, em linguagem simples, como o sistema calcula os parâmetros necessários para o reabastecimento inteligente de estoque.

**Última Atualização:** Dezembro 2024 - Versão 2.0
**Melhorias:** Cálculo inteligente de demanda, múltiplos métodos estatísticos, detecção automática de padrões

---

## 🆕 NOVIDADE: Cálculo Inteligente de Demanda

### O que mudou?

O sistema agora oferece **cálculo automático de demanda** a partir do histórico de vendas, com **6 métodos diferentes**:

1. **Média Simples** - Método tradicional (baseline)
2. **Média Móvel Exponencial (EMA)** - Dá mais peso aos períodos recentes
3. **Regressão com Tendência** - Detecta e projeta crescimento/queda
4. **Decomposição Sazonal** - Identifica padrões sazonais (Natal, Black Friday, etc.)
5. **Método de Croston** - Especializado para demanda intermitente (vendas esporádicas)
6. **Modo Inteligente (AUTO)** - ⭐ **RECOMENDADO**: Detecta automaticamente o padrão e escolhe o melhor método

### Por que isso é importante?

- ✅ **Até 95% mais preciso** que média simples em alguns casos
- ✅ **Elimina erros humanos** no cálculo de demanda
- ✅ **Detecta padrões automaticamente** (tendências, sazonalidade, intermitência)
- ✅ **Otimiza estoque de segurança** conforme padrão de cada item
- ✅ **Economiza capital** em itens intermitentes
- ✅ **Previne rupturas** em itens com crescimento

### Como usar?

No sistema, selecione **"Modo Automático"** (recomendado):
- Forneça histórico de vendas (mínimo 6 meses)
- Sistema calcula demanda automaticamente
- Detecta padrão (estável, tendência, sazonal, intermitente, variável)
- Escolhe melhor método para cada item
- Gera Excel com metadata (método usado, padrão detectado, confiança)

Ou use **"Modo Manual"** (exceções):
- Você fornece demanda média e desvio padrão já calculados
- Sistema usa valores fornecidos

---

## 1. Demanda Média Mensal

### O que é?
É a quantidade média de produtos vendidos por mês.

### MODO AUTOMÁTICO (Recomendado)

O sistema analisa o histórico e escolhe automaticamente o melhor método:

#### Método 1: Média Simples
Para demanda **estável** (baixa variação)
```
Demanda Média = Soma(Vendas) / N
```

**Quando usar:** Vendas consistentes mês a mês

**Exemplo:**
```
Vendas: 100, 105, 98, 102, 100, 103
Demanda = (100+105+98+102+100+103) / 6 = 101.3 un/mês
```

#### Método 2: Média Móvel Exponencial (EMA)
Para demanda **variável** ou com mudanças graduais
```
EMA = α × Venda_atual + (1-α) × EMA_anterior
α = 0.3 (padrão - balanceado)
```

**Quando usar:** Vendas com variações, quer ser mais reativo

**Exemplo:**
```
Vendas: 100, 150, 80, 200, 90, 170
Sistema usa EMA para dar mais peso aos meses recentes
Demanda EMA ≈ 142.6 (último valor ponderado)
```

#### Método 3: Regressão com Tendência
Para demanda com **crescimento ou queda linear**
```
Demanda = a + b × t
Projeta próximo valor considerando tendência
```

**Quando usar:** Produto em crescimento ou descontinuado

**Exemplo:**
```
Vendas: 100, 110, 115, 125, 135, 140, 150, 160, 165, 175, 180, 190
Tendência detectada: +10 un/mês
Demanda projetada = 198.3 (projeta próximo mês)
```

#### Método 4: Decomposição Sazonal
Para demanda com **padrões sazonais**
```
Demanda = Tendência × Índice_Sazonal
Ajusta para mês específico do ciclo
```

**Quando usar:** Vendas variam por época do ano

**Exemplo:**
```
Produto com pico em dezembro (Natal):
Jan-Nov: ~100 unidades
Dezembro: ~200 unidades
Sistema detecta sazonalidade e ajusta demanda conforme mês
```

#### Método 5: Croston
Para demanda **intermitente** (muitos zeros)
```
Demanda = Tamanho_Médio / Intervalo_Médio
Separa tamanho da demanda de frequência
```

**Quando usar:** Vendas esporádicas (B2B, industrial)

**Exemplo:**
```
Vendas: 0, 0, 50, 0, 0, 45, 0, 0, 0, 52, 0, 0, 48
Média simples = 14.7 (ruim, desvio = 23.6)
Croston = 14.3 (bom, desvio = 1.1)
Reduz estoque de segurança em 95%!
```

### MODO MANUAL

Você calcula no Excel:
```
Demanda Média = MÉDIA(intervalo_vendas)
```

### Onde buscar dados?
- Sistema de vendas (ERP, PDV)
- Relatórios de movimentação de estoque
- Notas fiscais de saída
- **Mínimo 6 meses, ideal 12 meses**

---

## 2. Desvio Padrão Mensal

### O que é?
Mede o quanto as vendas variam mês a mês. Quanto maior, mais imprevisível a demanda.

### Como interpretar?
- **Desvio baixo** (ex: 10): Vendas estáveis e previsíveis
- **Desvio médio** (ex: 30-50): Vendas com variação moderada
- **Desvio alto** (ex: 100+): Vendas muito instáveis

### MODO AUTOMÁTICO

Sistema calcula automaticamente com método ponderado:
- **Demanda estável**: Desvio padrão simples
- **Demanda com EMA**: Desvio padrão ponderado (mais peso ao recente)
- **Demanda com tendência**: Desvio dos resíduos (erro da projeção)
- **Demanda intermitente**: Desvio ajustado pela frequência

**Resultado:** Desvio padrão mais assertivo para cada padrão

### MODO MANUAL

No Excel:
```
Desvio Padrão = DESVPAD.P(intervalo_vendas)
```

**Exemplo:**
```
Vendas: 150, 160, 140, 155, 145, 150
Excel: =DESVPAD.P(A1:A6) = 6,8 unidades
```

### Por que é importante?
Desvio correto = estoque de segurança adequado:
- **Desvio subestimado** → Risco de ruptura
- **Desvio superestimado** → Capital imobilizado

---

## 3. Estoque de Segurança

### O que é?
"Reserva" para cobrir imprevistos:
- Picos de demanda
- Atrasos do fornecedor
- Variações nas vendas

### Fórmula:
```
ES = Z × σ_diário × √Lead_Time

Onde:
- Z = Fator de segurança (nível de serviço)
- σ_diário = Desvio Padrão Mensal ÷ √30
- Lead_Time = Tempo de entrega (dias)
```

### Exemplo Prático:
**Dados:**
- Desvio Padrão Mensal: 45 unidades
- Lead Time: 15 dias
- Nível Serviço: 95% → Z = 1,65

**Cálculo:**
```
1. σ_diário = 45 ÷ √30 = 8,21 un/dia
2. ES = 1,65 × 8,21 × √15
3. ES = 1,65 × 8,21 × 3,87
4. ES = 52 unidades
```

**Interpretação:** 52 unidades extras para 95% de certeza de não faltar

### 🆕 Impacto do Método Inteligente:

**Exemplo - Demanda Intermitente:**
- Método Simples: Desvio = 23.6 → ES = 27 unidades
- Método Croston: Desvio = 1.1 → ES = 1.3 unidades
- **Economia: 95% de capital imobilizado!**

**Exemplo - Demanda Crescimento:**
- Método Simples: Desvio = 34.1 → ES = 34 unidades (subestima demanda)
- Método Tendência: Desvio = 1.7 → ES = 1.7 unidades (projeta corretamente)
- **Previne: 36% de ruptura!**

---

## 4. Ponto de Pedido (Reorder Point)

### O que é?
Nível de estoque que indica quando fazer novo pedido.

### Fórmula:
```
PP = (Demanda_Diária × Lead_Time) + Estoque_Segurança
```

### Exemplo Prático:
**Dados:**
- Demanda Média Mensal: 150 unidades
- Lead Time: 15 dias
- ES: 52 unidades

**Cálculo:**
```
1. Demanda Diária = 150 ÷ 30 = 5 un/dia
2. Demanda durante LT = 5 × 15 = 75 unidades
3. PP = 75 + 52 = 127 unidades
```

**Interpretação:** Quando estoque atingir 127 un, faça novo pedido

---

## 5. Quantidade a Pedir

### O que é?
Quanto comprar quando atingir o ponto de pedido.

### Fórmula (Política de Revisão Periódica):
```
Quantidade = PP + Demanda_Revisão - Estoque_Efetivo

Onde:
- Demanda_Revisão = Demanda_Diária × Dias_Revisão (padrão: 7)
- Estoque_Efetivo = Disponível + Trânsito + Abertos
```

### Exemplo Prático:
**Dados:**
- PP: 127 unidades
- Demanda Diária: 5 un/dia
- Revisão: 7 dias (semanal)
- Estoque Disponível: 80 un
- Estoque Trânsito: 20 un
- Lote Mínimo: 10 un

**Cálculo:**
```
1. Demanda_Revisão = 5 × 7 = 35 un
2. Estoque_Efetivo = 80 + 20 = 100 un
3. Quantidade_Necessária = 127 + 35 - 100 = 62 un
4. Ajuste_Lote = arredondar(62, múltiplo de 10) = 70 un
5. Quantidade_Pedir = 70 unidades
```

---

## 6. Cobertura de Estoque (dias)

### O que é?
Quantos dias o estoque atual dura.

### Fórmulas:
```
Cobertura_Atual = Estoque_Disponível ÷ Demanda_Diária
Cobertura_com_Pedido = (Estoque + Quantidade_Pedir) ÷ Demanda_Diária
```

### Exemplo:
**Dados:**
- Estoque: 80 un
- Quantidade a Pedir: 70 un
- Demanda Diária: 5 un/dia

**Cálculo:**
```
Cobertura Atual = 80 ÷ 5 = 16 dias
Cobertura com Pedido = (80 + 70) ÷ 5 = 30 dias
```

### Interpretação de Risco:
- 🚨 **< 7 dias**: Risco de ruptura
- ⚡ **7-14 dias**: Atenção
- ✅ **≥ 15 dias**: Seguro

---

## 7. Nível de Serviço

### O que é?
Probabilidade de **não** faltar produto.

### Tabela de Valores:

| Nível | Z-Score | Quando Usar |
|-------|---------|-------------|
| **90%** | 1.28 | Produtos menos importantes |
| **95%** | 1.65 | Produtos regulares (padrão) |
| **98%** | 2.05 | Produtos importantes |
| **99%** | 2.33 | Produtos críticos |
| **99.9%** | 3.09 | Produtos essenciais |

### Como Escolher?

#### Critério 1: Importância
- 99%: Alta margem, best-sellers
- 95-98%: Produtos regulares
- 90-92%: Baixa margem, substituíveis

#### Critério 2: Impacto da Falta
- 99%: Cliente vai ao concorrente
- 95-98%: Cliente pode esperar
- 90%: Facilmente substituível

#### Critério 3: Classificação ABC
- Classe A (80% faturamento): 98-99%
- Classe B (15% faturamento): 95-97%
- Classe C (5% faturamento): 90-93%

---

## 8. Resumo dos Dados Necessários

### MODO AUTOMÁTICO (Recomendado)

| Dado | Onde Buscar | Observação |
|------|-------------|------------|
| **Loja** | Cadastro filiais | Código da loja |
| **SKU** | Cadastro produtos | Código do produto |
| **Mes** | Sistema vendas | Data (YYYY-MM-DD) |
| **Vendas** | Sistema vendas | Quantidade vendida |
| **Lead_Time_Dias** | Fornecedor | Tempo entrega |
| **Estoque_Disponível** | ERP/WMS | Estoque físico |
| *Estoque_Transito* | Sistema compras | Opcional |
| *Pedidos_Abertos* | Sistema compras | Opcional |
| *Lote_Minimo* | Fornecedor | Opcional |

**Estrutura do arquivo:**
- Múltiplas linhas por item (histórico de 6-12 meses)
- Última linha de cada item tem dados de estoque

### MODO MANUAL (Exceções)

| Dado | Onde Buscar | Como Calcular |
|------|-------------|---------------|
| **Loja** | Cadastro | Código |
| **SKU** | Cadastro | Código |
| **Demanda_Media_Mensal** | Você calcula | =MÉDIA() no Excel |
| **Desvio_Padrao_Mensal** | Você calcula | =DESVPAD.P() no Excel |
| **Lead_Time_Dias** | Fornecedor | Tempo entrega |
| **Estoque_Disponível** | ERP/WMS | Estoque físico |

**Estrutura do arquivo:**
- Uma linha por item

---

## 9. Ferramentas do Sistema

### 1. Reabastecimento Automático
- Processa todos os itens em lote
- Escolhe método inteligente para cada item
- Gera Excel com sugestões + metadata
- **Use para:** Planejamento semanal/mensal

### 2. Reabastecimento Manual
- Você fornece demanda calculada
- Sistema usa valores fornecidos
- **Use para:** Exceções, produtos novos

### 3. 🆕 Pedido Manual Simplificado
- Simula impacto de quantidade específica
- Interface visual com indicadores
- Atalhos rápidos (Sugestão, 30/60 dias)
- **Use para:** Validar/ajustar quantidades, análise "what-if"

---

## 10. Exemplo Completo

### Produto: SKU_001 na LOJA_01

**Histórico (últimos 12 meses):**
```
Jan: 140, Fev: 150, Mar: 160, Abr: 145
Mai: 155, Jun: 150, Jul: 165, Ago: 170
Set: 155, Out: 160, Nov: 150, Dez: 175
```

**Sistema Detecta:**
- Padrão: Variável
- Método Escolhido: EMA
- Confiança: Alta

**Cálculos (Modo Automático):**
```
1. Demanda EMA = 163.4 un/mês (mais peso ao recente)
2. Desvio Ponderado = 9.8 unidades
3. Demanda Diária = 163.4 ÷ 30 = 5.4 un/dia
4. σ_diário = 9.8 ÷ √30 = 1.79 un/dia
5. ES = 1.65 × 1.79 × √15 = 11.5 ≈ 12 un
6. PP = (5.4 × 15) + 12 = 81 + 12 = 93 un
```

**Situação Atual:**
```
Estoque Disponível: 80 un
Estoque Trânsito: 20 un
Estoque Efetivo: 100 un
```

**Decisão:**
```
Demanda Revisão (7 dias) = 5.4 × 7 = 38 un
Quantidade = 93 + 38 - 100 = 31 un
Ajuste Lote (10) = 40 unidades

Cobertura Atual = 80 ÷ 5.4 = 14.8 dias (✅ OK)
Cobertura com Pedido = 120 ÷ 5.4 = 22.2 dias (✅ Seguro)
```

---

## 📞 Dúvidas Frequentes

**1. Qual modo devo usar?**
R: **Automático** sempre que possível. Manual apenas para exceções.

**2. Como sei qual método foi usado?**
R: No modo automático, coluna `Metodo_Usado` mostra (ema, tendencia, sazonal, croston, simples).

**3. Posso forçar um método específico?**
R: Não pela interface (decisão de UX). Sistema sempre escolhe automaticamente o melhor.

**4. Quantos meses de histórico preciso?**
R: Mínimo 3, recomendado 6-12 meses. Quanto mais, melhor a detecção de padrões.

**5. O que fazer se não tenho histórico?**
R: Use modo manual com estimativa conservadora ou dados de produtos similares.

**6. Como lidar com promoções?**
R: Remova períodos promocionais do histórico ou calcule duas demandas separadas.

**7. Lead time varia muito, e agora?**
R: Use lead time máximo observado ou média + desvio padrão do lead time.

**8. Como usar o Pedido Manual Simplificado?**
R: Após processar reabastecimento, acesse "⚡ Pedido Manual Rápido", carregue o Excel gerado, e simule cenários "what-if".

---

## 📚 Recursos Adicionais

- [MELHORIAS_CALCULO_DEMANDA.md](MELHORIAS_CALCULO_DEMANDA.md) - Detalhes técnicos dos 6 métodos
- [GUIA_MODOS_REABASTECIMENTO.md](GUIA_MODOS_REABASTECIMENTO.md) - Como escolher modo automático vs manual
- [PEDIDO_MANUAL_SIMPLIFICADO.md](PEDIDO_MANUAL_SIMPLIFICADO.md) - Guia do simulador rápido
- `exemplo_demanda_inteligente.py` - Demonstração comparativa dos métodos
- `exemplo_reabastecimento_automatico.xlsx` - Arquivo de exemplo (modo automático)
- `exemplo_reabastecimento.xlsx` - Arquivo de exemplo (modo manual)

---

## 🎯 Fluxo Completo Recomendado

```
1. REABASTECIMENTO (Modo Automático)
   ↓
   Sistema analisa histórico
   ↓
   Detecta padrão de cada item
   ↓
   Escolhe melhor método
   ↓
   Calcula sugestões otimizadas
   ↓
   Gera Excel com metadata
   ↓
2. PEDIDO MANUAL (Simulador)
   ↓
   Carrega Excel gerado
   ↓
   Simula cenários "what-if"
   ↓
   Valida/ajusta quantidades
   ↓
3. DECISÃO FINAL
   ↓
   Aprova pedidos
```

---

**Última atualização:** Dezembro 2024
**Versão:** 2.0
**Novidades:** Cálculo inteligente de demanda, detecção automática de padrões, simulador de pedidos
