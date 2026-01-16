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

Se nenhuma cobertura for informada, o sistema usa valores automaticos:

| Curva | Cobertura Padrao |
|-------|------------------|
| A | 15 dias |
| B | 21 dias |
| C | 30 dias |

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

1. Sistema identifica lojas com **excesso de estoque** (cobertura > alvo + margem)
2. Identifica lojas com **falta de estoque** (cobertura < alvo)
3. Sugere transferencias entre lojas do **mesmo grupo regional**
4. Prioriza por urgencia (CRITICA > ALTA > MEDIA > BAIXA)

### Regras de Transferencia

- Loja doadora mantem minimo de 10 dias de cobertura apos doacao
- Margem de excesso: 7 dias acima da cobertura alvo
- Transferencia nao pode deixar doadora em situacao de ruptura
- Mesma loja NAO pode enviar e receber o mesmo produto

### Niveis de Urgencia

| Urgencia | Cobertura Destino | Cor |
|----------|-------------------|-----|
| CRITICA | 0 dias (ruptura) | Vermelho |
| ALTA | 1-3 dias | Laranja |
| MEDIA | 4-7 dias | Amarelo |
| BAIXA | > 7 dias | Verde |

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
