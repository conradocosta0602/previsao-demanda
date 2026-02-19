# Integração dos Arquivos de Teste

## Visão Geral

Os arquivos de teste foram **correlacionados** para simular um fluxo completo de cadeia de suprimentos:

```
HISTORICO DE VENDAS → PREVISAO → PEDIDO CD → PEDIDO FORNECEDOR
```

---

## Estrutura da Cadeia

### 1. **Histórico de Vendas** (`tests/dados_teste_integrado.xlsx`)

**Estrutura:**
- **100 SKUs** (PROD_001 a PROD_100)
- **5 Lojas** (LOJA_01 a LOJA_05)
- **10 meses** de histórico (2024-01 a 2024-10)
- **6.000 linhas** de dados

**Classificação dos Produtos:**
- **Classe A (PROD_001 a PROD_020):** Alta demanda (100-200 unidades/mês)
- **Classe B (PROD_021 a PROD_060):** Média demanda (30-100 unidades/mês)
- **Classe C (PROD_061 a PROD_100):** Baixa demanda (5-30 unidades/mês)

**Sazonalidade:**
- Padrão sazonal aplicado usando função seno
- Variação de até 30% ao longo do ano

---

### 2. **Pedido CD → Lojas** (`exemplo_pedido_cd.xlsx`)

**Estrutura:**
- **500 linhas** (100 SKUs × 5 Lojas)
- **2 CDs:** CD_REGIONAL e CD_PRINCIPAL

**Correlação com Histórico:**
- Estoque nas lojas varia conforme demanda histórica:
  - Classe A: 3-15 unidades
  - Classe B: 10-30 unidades
  - Classe C: 20-50 unidades
- Custos correlacionados com classe do produto

**Mapeamento SKU → CD:**
- SKUs ímpares → CD_REGIONAL
- SKUs pares → CD_PRINCIPAL

**Abas:**
1. `PEDIDOS_CD` - Dados de pedidos CD→Lojas
2. `HISTORICO_VENDAS` - Mesmo histórico do arquivo integrado

---

### 3. **Pedido ao Fornecedor** (`exemplo_pedido_fornecedor.xlsx`)

**Estrutura:**
- **100 linhas** (100 SKUs)
- **3 Fornecedores:** FORNECEDOR_A, FORNECEDOR_B, FORNECEDOR_C

**Correlação com CD:**
- Estoque agregado de todas as lojas
- Custos baseados na média dos custos das lojas
- Destinos: CD_REGIONAL ou CD_PRINCIPAL

**Distribuição de SKUs por Fornecedor:**
- **FORNECEDOR_A:** PROD_001 a PROD_034 (34 SKUs)
- **FORNECEDOR_B:** PROD_035 a PROD_067 (33 SKUs)
- **FORNECEDOR_C:** PROD_068 a PROD_100 (33 SKUs)

**Abas:**
1. `PEDIDOS_FORNECEDOR` - Dados de pedidos ao fornecedor
2. `HISTORICO_VENDAS` - Mesmo histórico do arquivo integrado

---

## Fluxo de Dados

### Exemplo Completo: **PROD_001**

#### 1. **Histórico de Vendas (LOJA_01)**
```
Mês        | Vendas | Dias Estoque
-----------|--------|-------------
2024-01    | 145    | 30
2024-02    | 162    | 30
2024-03    | 178    | 30
...        | ...    | ...
Média      | 159.3  | ~30
```

#### 2. **Previsão de Demanda**
Sistema calcula:
- Demanda média mensal: **159 unidades**
- Desvio padrão: **~48 unidades**
- Método recomendado: Suavização Exponencial

#### 3. **Pedido CD → LOJA_01**
```
CD Origem:        CD_REGIONAL
Estoque Loja:     5 unidades
Estoque CD:       1.050 unidades
Demanda Média:    159 unidades/mês (~5,3 un/dia)
Custo:            R$ 10,50

CÁLCULO:
- Ponto de Pedido: 18 unidades
- Quantidade a Pedir: 22 unidades
- Cobertura Atual: 1,1 dias
- Cobertura Projetada: 4,7 dias
```

#### 4. **Pedido ao Fornecedor (FORNECEDOR_A → CD_REGIONAL)**
```
Fornecedor:         FORNECEDOR_A
Destino:            CD_REGIONAL (CD)
Estoque Total:      600 unidades
Demanda Agregada:   159 × 5 lojas = ~795 unidades/mês
Custo:              R$ 9,50
Lead Time:          14 dias
Ciclo:              30 dias

CÁLCULO:
- Considera demanda de TODAS as 5 lojas
- Consolida em paletes/carretas
- Otimiza frete
```

---

## Como Usar

### 1. **Previsão de Demanda**
```
Arquivo: tests/dados_teste_integrado.xlsx
Resultado: Previsões para 100 SKUs × 5 lojas
```

### 2. **Pedido CD**
```
Arquivo: exemplo_pedido_cd.xlsx
Usa: Histórico de vendas correlacionado
Resultado: Distribuição CD → Lojas
```

### 3. **Pedido Fornecedor**
```
Arquivo: exemplo_pedido_fornecedor.xlsx
Usa: Histórico de vendas correlacionado
Resultado: Compras Fornecedor → CD
```

---

## Validações

### Consistência de SKUs
- ✅ Todos os arquivos têm os mesmos 100 SKUs
- ✅ Mapeamento SKU → Fornecedor mantido
- ✅ Mapeamento SKU → CD mantido

### Correlação de Dados
- ✅ Estoque nas lojas proporcional à demanda
- ✅ Estoque no CD agregado das lojas
- ✅ Custos consistentes entre níveis
- ✅ Histórico de vendas compartilhado

### Classificação ABC
- ✅ Classe A: 20% dos SKUs, ~80% do volume
- ✅ Classe B: 40% dos SKUs, ~15% do volume
- ✅ Classe C: 40% dos SKUs, ~5% do volume

---

## Arquivos Gerados

1. **tests/dados_teste_integrado.xlsx** - 6.000 linhas de histórico
2. **exemplo_pedido_cd.xlsx** - 500 linhas de pedidos CD + histórico
3. **exemplo_pedido_fornecedor.xlsx** - 100 linhas de pedidos fornecedor + histórico

**Total:** ~12.500 linhas de dados integrados

---

## Atualização

Para regenerar os arquivos com novos dados aleatórios, execute o script de geração novamente. A seed (42) garante reprodutibilidade.
