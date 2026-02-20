# Pedido ao Fornecedor Integrado

Sistema inteligente de geracao de pedidos de compra com suporte a multiplas lojas, calculo automatico de transferencias entre lojas e integracao com parametros de fornecedor.

## Visao Geral

O modulo de Pedido ao Fornecedor Integrado permite gerar pedidos de compra otimizados considerando:

- **Previsao de demanda** baseada em historico e sazonalidade
- **Cobertura de estoque** configuravel por curva ABC
- **Parametros de fornecedor** (Lead Time, Ciclo de Pedido, Faturamento Minimo)
- **Situacao de compra** dos itens (bloqueios, restricoes)
- **Transferencias entre lojas** do mesmo grupo regional

## Fluxos de Pedido

### 1. Pedido para Lojas (Direto)

Gera pedidos individuais para cada loja selecionada, considerando o estoque e demanda especificos de cada unidade.

**Quando usar:**
- Pedidos diretos do fornecedor para lojas
- Reposicao de itens especificos por loja
- Pedidos emergenciais

### 2. Pedido para CD (Centralizado)

Gera um pedido consolidado para o Centro de Distribuicao, agregando a demanda de todas as lojas do grupo regional. Automaticamente identifica oportunidades de transferencia entre lojas.

**Quando usar:**
- Compras centralizadas
- Maior poder de negociacao com fornecedor
- Otimizacao logistica

## Interface do Usuario

### Filtros Disponiveis

| Filtro | Descricao | Multi-selecao |
|--------|-----------|---------------|
| Destino | Loja (Direto) ou CD (Centralizado) | Nao |
| Loja/CD | Seleciona lojas ou CDs destino | Sim (Ctrl+Click) |
| Fornecedor | Filtra por fornecedor especifico | Sim (Ctrl+Click) |
| Categoria | Filtra por categoria de produto | Sim (Ctrl+Click) |
| Cobertura | Dias de cobertura alvo | Nao |

### Cobertura por Curva ABC

Se nenhuma cobertura for informada, o sistema calcula automaticamente usando a formula:

```
Cobertura = Lead Time + Ciclo de Pedido (7d) + Seguranca ABC
```

Onde Seguranca ABC varia conforme a curva:

| Curva | Seguranca ABC | Exemplo (LT=15d) |
|-------|---------------|------------------|
| A | +2 dias | 15 + 7 + 2 = **24 dias** |
| B | +4 dias | 15 + 7 + 4 = **26 dias** |
| C | +6 dias | 15 + 7 + 6 = **28 dias** |

**Nota:** A cobertura e dinamica e depende do Lead Time do fornecedor cadastrado.

## Layout Multi-Loja

Quando multiplas lojas sao selecionadas ou pedido e para CD, o sistema exibe:

### Estrutura Hierarquica

```
Fornecedor X
├── Loja 1 (N SKUs, R$ valor)
│   ├── Item 1 [Pedir/Bloqueado/OK]
│   ├── Item 2 [Enviar -> Loja 2]
│   └── ...
├── Loja 2 (N SKUs, R$ valor)
│   ├── Item 1 [Receber <- Loja 1]
│   └── ...
└── Loja 3 (N SKUs, R$ valor)
    └── ...
```

### Indicadores Visuais

| Badge | Cor | Significado |
|-------|-----|-------------|
| Pedir | Azul | Item precisa ser pedido |
| Bloqueado | Amarelo | Item com restricao de compra |
| OK | Verde | Estoque suficiente |
| Ruptura | Vermelho | Ruptura iminente |
| Enviar X un | Laranja | Loja vai enviar para outra |
| Receber X un | Verde | Loja vai receber de outra |

## Transferencias entre Lojas

### Como Funciona

1. Sistema identifica lojas com **excesso de estoque** (cobertura > cobertura_alvo_item)
2. Identifica lojas com **falta de estoque** (quantidade_pedido > 0)
3. Sugere transferencias entre lojas do **mesmo grupo regional**
4. Prioriza por urgencia (CRITICA > ALTA > MEDIA > BAIXA)

### Logica Hibrida de Cobertura (v5.7+)

O sistema usa uma **logica hibrida** para determinar a cobertura alvo:

```python
cobertura_alvo_item = cobertura_dias if cobertura_dias else item['cobertura_necessaria_dias']
```

| Filtro de Cobertura | Comportamento |
|---------------------|---------------|
| **Fixa (ex: 90 dias)** | Todos os itens usam 90 dias como alvo |
| **ABC (automatica)** | Cada item usa sua propria cobertura calculada |

**Exemplo com Cobertura ABC:**
- Item curva A (LT=15): alvo = 15 + 7 + 2 = **24 dias**
- Item curva C (LT=15): alvo = 15 + 7 + 6 = **28 dias**

**Exemplo com Cobertura Fixa (90 dias):**
- Item curva A (LT=15): alvo = **90 dias**
- Item curva C (LT=15): alvo = **90 dias**

### Regras de Transferencia

- **Margem de excesso: 0** - Qualquer excesso acima do alvo pode ser doado
- **Cobertura minima do doador**: Doador mantem exatamente a cobertura alvo apos doacao
- Transferencia nao pode deixar doadora em situacao de ruptura
- Mesma loja NAO pode enviar e receber o mesmo produto

### Niveis de Urgencia

| Urgencia | Cobertura Destino | Cor |
|----------|-------------------|-----|
| CRITICA | 0 dias (ruptura) | Vermelho |
| ALTA | 1-3 dias | Laranja |
| MEDIA | 4-7 dias | Amarelo |
| BAIXA | > 7 dias | Verde |

## Rateio Proporcional de Demanda (v5.9+)

### O Problema

Quando a demanda e calculada de forma **consolidada** (todas as lojas somadas) e precisa ser distribuida entre lojas, o rateio uniforme (dividir igualmente) pode gerar distorcoes:

```
Demanda Total: 90 un/mes
Lojas: 3
Rateio Uniforme: 30 un/mes cada

Problema: Loja 1 vende 50%, Loja 2 vende 35%, Loja 3 vende 15%
          Mas todas recebem a mesma demanda (30 un)
```

### A Solucao: Rateio Proporcional

O sistema agora calcula a **proporcao de vendas historicas** de cada loja e aplica no rateio:

```python
# Calcula proporcao baseada no ultimo ano de vendas
proporcao_loja = vendas_loja / vendas_total

# Aplica no rateio da demanda consolidada
demanda_loja = demanda_consolidada * proporcao_loja
```

### Exemplo Pratico

**Cenario:** Produto com demanda consolidada de 90 un/mes, 3 lojas

| Loja | Vendas Historicas | Proporcao | Demanda Rateada |
|------|-------------------|-----------|-----------------|
| Loja 1 | 450 un | 50.0% | 45 un/mes |
| Loja 2 | 315 un | 35.0% | 31.5 un/mes |
| Loja 3 | 135 un | 15.0% | 13.5 un/mes |
| **Total** | **900 un** | **100%** | **90 un/mes** |

### Metodos de Rateio

| Metodo | Quando Usado | Comportamento |
|--------|--------------|---------------|
| **Proporcional** | Quando ha historico de vendas | Demanda × proporcao da loja |
| **Uniforme** | Fallback quando nao ha historico | Demanda ÷ numero de lojas |

### Visualizacao na Interface

O tooltip de detalhamento por loja agora exibe a proporcao:

```
Loja 1: 50 un (est: 100, dem.mensal: 45.00 [50.0%])
Loja 2: 35 un (est: 80, dem.mensal: 31.50 [35.0%])
Loja 3: 15 un (est: 60, dem.mensal: 13.50 [15.0%])
```

### Beneficios

1. **Precisao**: Demanda reflete o perfil real de vendas de cada loja
2. **Otimizacao de Estoque**: Evita excesso em lojas de baixo giro
3. **Reducao de Rupturas**: Lojas de alto giro recebem mais estoque
4. **Transparencia**: Proporcao visivel no tooltip

## Parametros de Fornecedor

O sistema considera parametros especificos por fornecedor:

| Parametro | Descricao | Impacto |
|-----------|-----------|---------|
| Lead Time | Dias entre pedido e entrega | Ajusta cobertura necessaria |
| Ciclo de Pedido | Frequencia de pedidos (dias) | Define janela de compra |
| Faturamento Minimo | Valor minimo do pedido | Alerta se pedido abaixo |

### Importacao de Parametros

Acesse **Menu > Parametros de Fornecedor** para importar planilha Excel com formato:

| Coluna | Obrigatoria | Descricao |
|--------|-------------|-----------|
| cnpj_fornecedor | Sim | CNPJ do fornecedor |
| cod_empresa | Nao | Codigo da empresa (0 = todas) |
| lead_time_dias | Sim | Lead time em dias |
| ciclo_pedido_dias | Nao | Ciclo de pedido em dias |
| faturamento_minimo | Nao | Valor minimo do pedido |

## Exportacao Excel

O arquivo exportado contem as seguintes abas:

### Aba "Resumo"
- Total de itens pedidos
- Total de itens bloqueados
- Valor total do pedido
- Estatisticas por fornecedor

### Aba "Itens Pedido"
Ordenada por Codigo Filial e CNPJ Fornecedor:

| Coluna | Descricao |
|--------|-----------|
| Codigo Filial | Codigo da loja destino |
| CNPJ Fornecedor | CNPJ do fornecedor |
| Codigo | SKU do produto |
| Descricao | Nome do produto |
| Quantidade | Quantidade a pedir |
| Valor Unitario | Preco unitario |
| Valor Total | Valor total da linha |

### Aba "Itens Bloqueados"
Itens que nao podem ser pedidos e motivo do bloqueio.

### Aba "Transferencias" (quando aplicavel)
Oportunidades de transferencia identificadas.

## API Endpoints

### POST /api/pedido_fornecedor_integrado

Processa e gera o pedido.

**Request:**
```json
{
  "destino_tipo": "Loja" | "CD",
  "cod_empresa": [1, 2, 3] | "TODAS",
  "fornecedor": ["FORN1", "FORN2"] | "TODOS",
  "categoria": ["CAT1"] | "TODAS",
  "cobertura_dias": 21 | null
}
```

**Response:**
```json
{
  "success": true,
  "itens_pedido": [...],
  "itens_bloqueados": [...],
  "itens_ok": [...],
  "estatisticas": {...},
  "transferencias": {...},
  "is_pedido_multiloja": true
}
```

### GET /api/pedido_fornecedor_integrado/exportar

Exporta o ultimo pedido processado para Excel.

## Requisitos de Banco de Dados

Execute o script `database/migration_v5.sql` para criar as tabelas necessarias:

- `parametros_fornecedor` - Parametros por fornecedor
- `grupos_transferencia` - Grupos regionais de lojas
- `lojas_grupo_transferencia` - Lojas de cada grupo
- `oportunidades_transferencia` - Historico de transferencias
- `situacao_compra_regras` - Regras de bloqueio
- `situacao_compra_itens` - Itens bloqueados

## Limitador de Cobertura 90 dias - Itens TSB (v6.12)

Itens com metodo de previsao **TSB** (Teunter-Syntetos-Babai) sao itens de demanda intermitente - vendas esporadicas e imprevisíveis. Para esses itens, o sistema aplica um limitador de cobertura pos-pedido de 90 dias por loja.

### Problema Resolvido

Itens TSB com baixa demanda podem gerar pedidos desproporcionais. Exemplo:
- Item vende 17 unidades em 3 anos (demanda intermitente)
- Rateio proporcional concentra 71% da demanda em 1 loja
- Sem limitador: pedido de 42 unidades para loja com 20 em estoque = 8+ meses de cobertura

### Como Funciona

```
1. Calcular pedido normalmente (formula padrao)
2. Se item e TSB:
   - cobertura_pos = (estoque_efetivo + quantidade_pedido) / demanda_diaria
   - Se cobertura_pos > 90 dias:
     - qtd_max = 90 * demanda_diaria - estoque_efetivo
     - Arredondar para BAIXO no multiplo de caixa
     - Minimo: 1 caixa (se ha necessidade real)
3. Se item NAO e TSB: sem limitador (comportamento normal)
```

### Campos no Resultado

| Campo | Tipo | Descricao |
|-------|------|-----------|
| `cobertura_limitada` | bool | Se o limitador atuou |
| `quantidade_original_antes_limite` | int | Quantidade antes do limitador |

### Constante

```python
COBERTURA_MAXIMA_POS_PEDIDO = 90  # dias
```

## Graceful Degradation

O sistema funciona mesmo sem as tabelas novas:

- Sem `parametros_fornecedor`: Usa valores padrao de cobertura
- Sem tabelas de transferencia: Nao calcula transferencias
- Sem `situacao_compra`: Nao aplica bloqueios

## Boas Praticas

1. **Configure grupos regionais** antes de usar pedido CD
2. **Importe parametros de fornecedor** para calculos mais precisos
3. **Revise transferencias sugeridas** antes de executar
4. **Monitore itens bloqueados** e atualize situacao de compra
5. **Use multi-selecao** para pedidos consolidados
