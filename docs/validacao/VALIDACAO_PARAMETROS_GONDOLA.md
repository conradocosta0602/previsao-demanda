# ⚠️ Validação - Parâmetros de Exposição de Gôndola (Pedidos CD)

**Data**: 2025-12-31
**Arquivo analisado**: `core/flow_processor.py`
**Função**: `processar_pedidos_cd()` (linhas 308-477)
**Status**: ⚠️ **VALIDAÇÃO CRÍTICA - INPUT EXTERNO OBRIGATÓRIO**

---

## 📋 Resumo da Validação

**Questão do usuário**:
> "Como a ferramenta está calculando a exposição de gôndola e o número de frentes no cálculo de pedido CD? Eu entendo que esse dado deveria ser um input externo, alimentado pela planilha Excel ou banco de dados."

**Resposta**: ✅ **O usuário está CORRETO**

O sistema **NÃO calcula** esses valores. Ele **tenta ler** da planilha Excel, mas se os dados não forem fornecidos, usa valores padrão que **desabilitam** o ajuste de exposição.

---

## 🔍 Análise do Código Atual

### Localização: [flow_processor.py:374-408](core/flow_processor.py#L374-L408)

```python
# Linha 374-376: Leitura dos parâmetros
estoque_min_gondola = int(row.get('Estoque_Min_Gondola', 0))
numero_frentes = int(row.get('Numero_Frentes', 1))

# Linha 378: Condição para aplicar ajuste
if estoque_min_gondola > 0 and numero_frentes > 0:
    # Linhas 379-408: Cálculo do ajuste de exposição
    estoque_minimo_exposicao = estoque_min_gondola * numero_frentes
    ponto_pedido_original = resultado['Ponto_Pedido']
    ponto_pedido_ajustado = max(ponto_pedido_original, estoque_minimo_exposicao)

    # ... resto do cálculo ...
else:
    # Linha 406-408: Se não fornecido, ajuste é desabilitado
    resultado['ajustado_exposicao'] = False
    estoque_minimo_exposicao = 0
    frentes_cobertas = 0
```

---

## ⚠️ Comportamento Atual

### Cenário 1: Dados de Exposição **FORNECIDOS** na Planilha ✅

**Planilha Excel (aba PEDIDOS_CD)**:
```
Loja_Destino | SKU | Estoque_Min_Gondola | Numero_Frentes
-------------|-----|---------------------|----------------
LOJA_001     | A01 | 10                  | 3
```

**Resultado**:
```python
estoque_min_gondola = 10
numero_frentes = 3
estoque_minimo_exposicao = 10 * 3 = 30 unidades

# Condição é TRUE
if 10 > 0 and 3 > 0:  # ✅ Verdadeiro
    # Ajuste de exposição É APLICADO
    ponto_pedido_ajustado = max(ponto_pedido_original, 30)
    ajustado_exposicao = True
```

---

### Cenário 2: Dados de Exposição **NÃO FORNECIDOS** na Planilha ❌

**Planilha Excel (aba PEDIDOS_CD)** - SEM as colunas de exposição:
```
Loja_Destino | SKU | Estoque_Disponivel_Loja | Lead_Time_Dias
-------------|-----|------------------------|----------------
LOJA_001     | A01 | 50                     | 2
```

**Resultado**:
```python
estoque_min_gondola = 0  # Padrão do .get('Estoque_Min_Gondola', 0)
numero_frentes = 1       # Padrão do .get('Numero_Frentes', 1)
estoque_minimo_exposicao = 0 * 1 = 0

# Condição é FALSE
if 0 > 0 and 1 > 0:  # ❌ Falso (estoque_min_gondola = 0)
    # Este bloco NUNCA executa
else:
    # Ajuste de exposição NÃO É APLICADO
    ajustado_exposicao = False
    estoque_minimo_exposicao = 0
    frentes_cobertas = 0
```

**Impacto**:
- O cálculo do pedido ignora completamente a necessidade de exposição
- Pode gerar pedidos **insuficientes** para manter gôndola abastecida
- Risco de **ruptura visual** (prateleira vazia mesmo com estoque no backroom)

---

## 📊 Fluxo de Dados Correto

### Como DEVE funcionar:

```
┌─────────────────────────────────────┐
│  1. FONTE DE DADOS EXTERNA          │
│     (Planilha Excel ou Banco)       │
│                                     │
│  Colunas obrigatórias:              │
│  - Loja_Destino                     │
│  - SKU                              │
│  - Estoque_Min_Gondola ← OBRIGATÓRIO│
│  - Numero_Frentes      ← OBRIGATÓRIO│
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  2. LEITURA NO CÓDIGO               │
│     (flow_processor.py:374-376)     │
│                                     │
│  estoque_min_gondola = row['...']   │
│  numero_frentes = row['...']        │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  3. VALIDAÇÃO                       │
│                                     │
│  if estoque_min_gondola > 0 and     │
│     numero_frentes > 0:             │
│     ✅ Aplicar ajuste de exposição  │
│  else:                              │
│     ⚠️ Pedido SEM considerar gôndola│
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  4. CÁLCULO DO PEDIDO               │
│                                     │
│  Estoque_Min_Exposicao = Min × Frentes│
│  Ponto_Pedido = max(PP, Min_Exp)    │
│  Quantidade = PP + Demanda - Estoque│
└─────────────────────────────────────┘
```

---

## ✅ Estrutura Esperada da Planilha Excel

### Aba: PEDIDOS_CD

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| CD_Origem | String | ✅ Sim | Centro de distribuição origem | "CD_SP" |
| Loja_Destino | String | ✅ Sim | Loja destino | "LOJA_001" |
| SKU | String | ✅ Sim | Código do produto | "A01234" |
| Lead_Time_Dias | Integer | ✅ Sim | Tempo de entrega em dias | 2 |
| Estoque_Disponivel_Loja | Float | ✅ Sim | Estoque atual na loja | 50 |
| **Estoque_Min_Gondola** | Integer | ⚠️ **CRÍTICO** | Unidades mínimas por frente | **10** |
| **Numero_Frentes** | Integer | ⚠️ **CRÍTICO** | Número de frentes de exposição | **3** |
| Estoque_CD | Float | ⚙️ Opcional | Estoque disponível no CD | 1000 |
| Estoque_Transito | Float | ⚙️ Opcional | Estoque em trânsito | 20 |
| Pedidos_Abertos | Float | ⚙️ Opcional | Pedidos já abertos | 0 |
| Ciclo_Pedido_Dias | Integer | ⚙️ Opcional | Ciclo de revisão (padrão: 2) | 2 |
| Lote_Minimo | Integer | ⚙️ Opcional | Unidades por caixa (padrão: 1) | 6 |
| Custo_Unitario | Float | ⚙️ Opcional | Custo por unidade | 5.50 |

---

## 🔧 Exemplo Prático

### Cenário: Loja com 3 frentes de gôndola

**Dados de entrada**:
```excel
Loja_Destino: LOJA_001
SKU: SABONETE_DOVE_90G
Estoque_Min_Gondola: 8 unidades/frente
Numero_Frentes: 3 frentes
Estoque_Disponivel_Loja: 15 unidades
```

**Cálculo**:
```python
# 1. Estoque mínimo total para exposição
estoque_minimo_exposicao = 8 × 3 = 24 unidades

# 2. Ponto de pedido sem exposição (baseado em demanda/lead time)
ponto_pedido_original = 20 unidades  # Calculado pelo sistema

# 3. Ajuste para garantir exposição
ponto_pedido_ajustado = max(20, 24) = 24 unidades

# 4. Estoque efetivo
estoque_efetivo = 15 + 0 (trânsito) - 0 (abertos) = 15 unidades

# 5. Quantidade a pedir
quantidade_necessaria = 24 + demanda_revisao - 15
# Se demanda_revisao = 10 (5 dias × 2 un/dia)
quantidade_necessaria = 24 + 10 - 15 = 19 unidades

# 6. Ajustar para lote mínimo (ex: caixa com 6 un)
quantidade_pedido = ceil(19 / 6) × 6 = 4 × 6 = 24 unidades
```

**Resultado**:
```
Quantidade a pedir: 24 unidades (4 caixas)
Ajustado_Exposicao: True
Estoque após pedido: 15 + 24 = 39 unidades
Frentes cobertas: 39 / 8 = 4.9 frentes ✅
```

---

## ⚠️ Problemas se Dados NÃO Forem Fornecidos

### Sem `Estoque_Min_Gondola` e `Numero_Frentes`:

```python
# Valores padrão
estoque_min_gondola = 0
numero_frentes = 1
estoque_minimo_exposicao = 0

# Condição falha
if 0 > 0 and 1 > 0:  # ❌ FALSE
    # Nunca executa

# Resultado
quantidade_pedido = 10 unidades  # Baseado SOMENTE em demanda/lead time
```

**Problemas**:
1. ❌ **Ruptura visual**: Gôndola pode ficar vazia mesmo com estoque no backroom
2. ❌ **Perda de vendas**: Cliente não vê o produto, não compra
3. ❌ **Subutilização**: Não aproveita espaço de exposição disponível
4. ❌ **Cálculo incorreto**: Ignora necessidade real de reabastecimento

---

## ✅ Validação Implementada no Código

### O código JÁ valida corretamente:

**Linha 378-408**:
```python
if estoque_min_gondola > 0 and numero_frentes > 0:
    # ✅ Aplica ajuste de exposição
    estoque_minimo_exposicao = estoque_min_gondola * numero_frentes
    ponto_pedido_ajustado = max(ponto_pedido_original, estoque_minimo_exposicao)
    # ... cálculo completo ...
    resultado['ajustado_exposicao'] = True
else:
    # ⚠️ Desabilita ajuste se dados não fornecidos
    resultado['ajustado_exposicao'] = False
    estoque_minimo_exposicao = 0
```

**Campo no resultado** (linha 446):
```python
'Ajustado_Exposicao': resultado.get('ajustado_exposicao', False)
```

Este campo permite **verificar** se o ajuste foi aplicado ou não.

---

## 📝 Recomendações

### 1. ✅ Tornar Colunas Obrigatórias

**Adicionar validação no início da função**:
```python
def processar_pedidos_cd(df_cd, df_historico):
    # Validar colunas obrigatórias
    colunas_obrigatorias = [
        'CD_Origem', 'Loja_Destino', 'SKU',
        'Lead_Time_Dias', 'Estoque_Disponivel_Loja',
        'Estoque_Min_Gondola',  # ← OBRIGATÓRIO
        'Numero_Frentes'         # ← OBRIGATÓRIO
    ]

    faltando = [col for col in colunas_obrigatorias if col not in df_cd.columns]

    if faltando:
        raise ValueError(
            f"Colunas obrigatórias ausentes em PEDIDOS_CD: {faltando}\n"
            f"As colunas 'Estoque_Min_Gondola' e 'Numero_Frentes' são CRÍTICAS "
            f"para o cálculo correto de reabastecimento com exposição de gôndola."
        )
```

---

### 2. ⚠️ Alertar Sobre Valores Zerados

**Adicionar warning se valores inválidos**:
```python
if estoque_min_gondola == 0 or numero_frentes == 0:
    print(
        f"[AVISO] {loja_destino}/{sku}: "
        f"Estoque_Min_Gondola={estoque_min_gondola}, "
        f"Numero_Frentes={numero_frentes}. "
        f"Ajuste de exposição DESABILITADO!"
    )
```

---

### 3. 📊 Validar Valores Realistas

**Adicionar validação de range**:
```python
if estoque_min_gondola > 0 and numero_frentes > 0:
    # Validar ranges realistas
    if estoque_min_gondola > 100:
        print(f"[AVISO] {loja_destino}/{sku}: Estoque_Min_Gondola={estoque_min_gondola} parece alto!")

    if numero_frentes > 10:
        print(f"[AVISO] {loja_destino}/{sku}: Numero_Frentes={numero_frentes} parece alto!")
```

---

### 4. 📋 Documentar Template da Planilha

**Criar arquivo de exemplo**: `PEDIDOS_CD_TEMPLATE.xlsx`

Com instruções no cabeçalho:
```
# INSTRUÇÕES IMPORTANTES:
# - Estoque_Min_Gondola: Unidades mínimas por frente (ex: 8, 10, 12)
# - Numero_Frentes: Quantas frentes o produto tem na gôndola (ex: 1, 2, 3, 4)
# - Esses valores devem vir do cadastro de produtos ou planograma
# - Se não fornecidos, o sistema NÃO considerará a exposição no cálculo!
```

---

## 🎯 Fontes de Dados Recomendadas

### De onde DEVEM vir esses dados:

1. **Planograma da Loja**
   - Layout oficial das gôndolas
   - Define quantas frentes cada SKU tem
   - Atualizado por categoria/equipe de merchandising

2. **Cadastro de Produtos**
   - Tabela: `produto_loja_parametros`
   - Campos: `sku`, `loja`, `estoque_min_gondola`, `numero_frentes`

3. **Sistema WMS (Warehouse Management)**
   - Integração via API ou exportação CSV
   - Dados em tempo real

4. **Planilha de Gestão de Categoria**
   - Mantida pelo gerente de categoria
   - Atualizada trimestralmente

---

## 📊 Exemplo de Tabela de Banco de Dados

```sql
CREATE TABLE produto_loja_exposicao (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sku VARCHAR(20) NOT NULL,
    loja VARCHAR(20) NOT NULL,
    estoque_min_gondola INT NOT NULL,     -- Unidades por frente
    numero_frentes INT NOT NULL,           -- Número de frentes
    categoria VARCHAR(50),
    secao_gondola VARCHAR(50),
    data_atualizacao DATE,
    UNIQUE KEY (sku, loja)
);

-- Exemplo de dados
INSERT INTO produto_loja_exposicao VALUES
(1, 'SABONETE_DOVE_90G', 'LOJA_001', 8, 3, 'Higiene Pessoal', 'Gondola_A1', '2025-12-01'),
(2, 'SHAMPOO_CLEAR_400ML', 'LOJA_001', 6, 2, 'Higiene Pessoal', 'Gondola_A2', '2025-12-01'),
(3, 'ARROZ_TIO_JOAO_5KG', 'LOJA_001', 12, 4, 'Mercearia', 'Gondola_B1', '2025-12-01');
```

---

## ✅ Conclusão

### Resposta à Pergunta do Usuário:

**Pergunta**: "Como a ferramenta está calculando a exposição de gôndola e o número de frentes no cálculo de pedido CD?"

**Resposta**:
1. ✅ **A ferramenta NÃO calcula** esses valores
2. ✅ **Ela LIDA CORRETAMENTE** da planilha Excel ou fonte de dados
3. ⚠️ **Se não fornecidos**, usa padrão `(0, 1)` que **desabilita** o ajuste
4. ✅ **O usuário está CORRETO**: esses dados **DEVEM ser input externo**

### Status do Sistema:

**Comportamento atual**: ✅ **CORRETO**
- Sistema não tenta "adivinhar" ou calcular valores de exposição
- Lê corretamente da fonte de dados externa
- Aplica ajuste somente se dados válidos fornecidos

**Ressalva**: ⚠️ **DADOS CRÍTICOS DEVEM SER OBRIGATÓRIOS**
- Planilha Excel deve ter colunas `Estoque_Min_Gondola` e `Numero_Frentes`
- Valores devem vir de planograma, cadastro ou sistema WMS
- Sem esses dados, cálculo pode gerar pedidos insuficientes

### Recomendação:

✅ **Tornar campos obrigatórios** com validação
✅ **Documentar fonte de dados** no manual do usuário
✅ **Criar template de planilha** com instruções claras
✅ **Alertar usuário** se valores zerados ou ausentes

---

**Data da Validação**: 2025-12-31
**Validado por**: Claude Code (Sonnet 4.5)
**Status**: ✅ **SISTEMA ESTÁ CORRETO** (dados devem vir de fonte externa)
**Ação requerida**: Documentar obrigatoriedade e validar entrada
