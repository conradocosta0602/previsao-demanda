# Resumo: Novos Módulos de Pedido Manual

## Contexto

O modo manual anterior estava confuso, misturando cálculo de demanda com emissão de pedidos. Foi reestruturado em dois módulos distintos e focados.

---

## ✅ Implementado

### 1. Módulo: Pedido por Quantidade

**Objetivo:** Usuário informa quantidade desejada, sistema valida múltiplo de caixa

**Arquivo:** `core/order_processor.py` - classe `OrderProcessor`

**Rota:** `/processar_pedido_quantidade` (POST)

**Planilha de entrada:** `exemplo_pedido_quantidade.xlsx`

**Colunas obrigatórias:**
- `Loja` - Código da loja
- `SKU` - Código do produto
- `Quantidade_Desejada` - Quantidade que o usuário quer pedir
- `Unidades_Por_Caixa` - Quantas unidades vêm na embalagem

**Colunas opcionais:**
- `Demanda_Diaria` - Para calcular dias de cobertura
- `Estoque_Disponivel` - Para calcular cobertura total

**O que faz:**
1. Valida se quantidade está em múltiplo de caixa
2. Ajusta automaticamente para cima se necessário
3. Calcula número de caixas
4. Calcula cobertura em dias (se tiver demanda)
5. Gera relatório Excel para emissão

**Exemplo:**
```
Entrada:
  Quantidade_Desejada: 100
  Unidades_Por_Caixa: 12

Processamento:
  100 ÷ 12 = 8.33 caixas (não é inteiro!)
  Ajusta para: 9 caixas × 12 = 108 unidades

Saída:
  Quantidade_Pedido: 108
  Numero_Caixas: 9
  Foi_Ajustado: True
  Diferenca_Ajuste: +8
  Status_Validacao: "Ajustado para múltiplo de caixa"
```

**Arquivo de saída:** `pedido_quantidade_YYYYMMDD_HHMMSS.xlsx`

**Abas geradas:**
- `Pedido` - Todos os itens com validações
- `Itens_Ajustados` - Apenas itens que foram ajustados

---

### 2. Módulo: Pedido por Cobertura

**Objetivo:** Usuário informa dias de cobertura desejados, sistema calcula quantidade

**Rota:** `/processar_pedido_cobertura` (POST)

**Planilha de entrada:** `exemplo_pedido_cobertura.xlsx`

**Colunas obrigatórias:**
- `Loja` - Código da loja
- `SKU` - Código do produto
- `Demanda_Diaria` - Demanda média diária
- `Cobertura_Desejada_Dias` - Quantos dias de estoque quer ter
- `Unidades_Por_Caixa` - Unidades por embalagem

**Colunas opcionais:**
- `Estoque_Disponivel` - Estoque atual (considera na necessidade)

**O que faz:**
1. Calcula cobertura atual do estoque
2. Calcula necessidade líquida (desejado - atual)
3. Converte dias em quantidade (dias × demanda)
4. Ajusta para múltiplo de caixa
5. Calcula cobertura real após pedido
6. Gera relatório Excel

**Exemplo:**
```
Entrada:
  Demanda_Diaria: 5 un/dia
  Cobertura_Desejada_Dias: 30
  Estoque_Disponivel: 20
  Unidades_Por_Caixa: 12

Processamento:
  Cobertura atual = 20 ÷ 5 = 4 dias
  Necessidade = 30 - 4 = 26 dias
  Quantidade bruta = 26 × 5 = 130 unidades
  Ajuste: 132 unidades (11 caixas × 12)

Saída:
  Quantidade_Pedido: 132
  Numero_Caixas: 11
  Cobertura_Real_Dias: 30.4
  Diferenca_Cobertura: +0.4 dias
  Status_Pedido: "Ajustado para múltiplo de caixa"
```

**Arquivo de saída:** `pedido_cobertura_YYYYMMDD_HHMMSS.xlsx`

**Abas geradas:**
- `Pedido` - Todos os itens com cálculos
- `Sem_Necessidade` - Itens que já têm cobertura suficiente (qtd = 0)
- `Itens_Ajustados` - Itens ajustados para múltiplo de caixa

---

## 📊 Estrutura dos Arquivos

### exemplo_pedido_quantidade.xlsx

```
Aba: PEDIDO
+--------+-----------+--------------------+-------------------+------------------+--------------------+
| Loja   | SKU       | Quantidade_Desejada| Unidades_Por_Caixa| Demanda_Diaria   | Estoque_Disponivel |
+--------+-----------+--------------------+-------------------+------------------+--------------------+
| LOJA_01| PROD_001  | 100                | 12                | 5.5              | 20                 |
| LOJA_01| PROD_002  | 75                 | 10                | 3.2              | 15                 |
+--------+-----------+--------------------+-------------------+------------------+--------------------+

Aba: INSTRUCOES
(Instruções completas de uso)
```

### exemplo_pedido_cobertura.xlsx

```
Aba: PEDIDO
+--------+-----------+----------------+-----------------------+-------------------+--------------------+
| Loja   | SKU       | Demanda_Diaria | Cobertura_Desejada_Dias| Unidades_Por_Caixa| Estoque_Disponivel |
+--------+-----------+----------------+-----------------------+-------------------+--------------------+
| LOJA_01| PROD_001  | 5.5            | 30                    | 12                | 20                 |
| LOJA_01| PROD_002  | 3.2            | 45                    | 10                | 15                 |
+--------+-----------+----------------+-----------------------+-------------------+--------------------+

Aba: INSTRUCOES
(Instruções completas de uso)
```

---

## 🔧 Arquivos Criados/Modificados

### Novos arquivos:

1. **`core/order_processor.py`** (350 linhas)
   - Classe `OrderProcessor` com métodos estáticos
   - `processar_pedido_por_quantidade()`
   - `processar_pedido_por_cobertura()`
   - `validar_multiplo_caixa()`
   - `gerar_relatorio_pedido()`

2. **`gerar_exemplos_pedido.py`**
   - Gera arquivos Excel de exemplo
   - Cria instruções detalhadas

3. **`exemplo_pedido_quantidade.xlsx`**
   - Planilha modelo para pedido por quantidade

4. **`exemplo_pedido_cobertura.xlsx`**
   - Planilha modelo para pedido por cobertura

### Arquivos modificados:

1. **`app.py`**
   - Adicionadas rotas `/pedido_quantidade` e `/pedido_cobertura`
   - Adicionadas funções de processamento
   - Total: +150 linhas

---

## ✅ Testes Realizados

### Teste 1: Pedido por Quantidade
```python
Input:
  Quantidade_Desejada: 100
  Unidades_Por_Caixa: 12

Output:
  Quantidade_Pedido: 108  ✓
  Numero_Caixas: 9        ✓
  Foi_Ajustado: True      ✓
```

### Teste 2: Pedido por Cobertura
```python
Input:
  Demanda_Diaria: 5.5
  Cobertura_Desejada_Dias: 30
  Estoque_Disponivel: 20
  Unidades_Por_Caixa: 12

Output:
  Cobertura_Atual_Dias: 3.6      ✓
  Quantidade_Pedido: 156          ✓
  Numero_Caixas: 13               ✓
  Cobertura_Real_Dias: 32.0       ✓
```

---

## 📋 Próximos Passos Sugeridos

### Implementação Completa:

1. ✅ Módulo de processamento criado
2. ✅ Rotas Flask adicionadas
3. ✅ Arquivos de exemplo gerados
4. ✅ Testes funcionais executados
5. ⏳ Templates HTML (pedido_quantidade.html, pedido_cobertura.html)
6. ⏳ Atualização da documentação Word

### Templates HTML necessários:

Criar em `templates/`:
- `pedido_quantidade.html` - Interface para upload e visualização
- `pedido_cobertura.html` - Interface para upload e visualização

Podem ser baseados em `reabastecimento.html` existente.

---

## 🎯 Benefícios

### Pedido por Quantidade:
- ✅ Garante pedidos em múltiplo de caixa
- ✅ Evita erros de embalagem
- ✅ Relatório pronto para emissão
- ✅ Validação automática

### Pedido por Cobertura:
- ✅ Calcula quantidade automaticamente
- ✅ Considera estoque existente
- ✅ Garante múltiplo de caixa
- ✅ Mostra cobertura real após pedido
- ✅ Identifica itens sem necessidade

### Geral:
- ✅ Elimina confusão do "modo manual" anterior
- ✅ Processos claros e distintos
- ✅ Validações robustas
- ✅ Relatórios detalhados

---

## 📝 Documentação Atualizada

A seção **7.1 (Modo Manual)** do documento Word deve ser atualizada para:

**7.1.1. Pedido por Quantidade**
- Descrição do processo
- Colunas da planilha
- Exemplo prático
- Resultado gerado

**7.1.2. Pedido por Cobertura**
- Descrição do processo
- Colunas da planilha
- Exemplo de cálculo
- Observações importantes

---

## 🚀 Como Usar

### Pedido por Quantidade:

1. Abrir `exemplo_pedido_quantidade.xlsx`
2. Preencher: Loja, SKU, Quantidade_Desejada, Unidades_Por_Caixa
3. Acessar `/pedido_quantidade` no sistema
4. Upload do arquivo
5. Baixar relatório gerado

### Pedido por Cobertura:

1. Abrir `exemplo_pedido_cobertura.xlsx`
2. Preencher: Loja, SKU, Demanda_Diaria, Cobertura_Desejada_Dias, Unidades_Por_Caixa
3. Opcionalmente: Estoque_Disponivel
4. Acessar `/pedido_cobertura` no sistema
5. Upload do arquivo
6. Baixar relatório gerado

---

**Data:** 2024-12-29
**Status:** ✅ Implementado e testado
**Pendente:** Templates HTML, atualização doc Word
