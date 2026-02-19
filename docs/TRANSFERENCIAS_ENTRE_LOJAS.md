# Transferencias entre Lojas

Sistema de identificacao e gestao de oportunidades de transferencia de estoque entre lojas do mesmo grupo regional.

## Visao Geral

O modulo de Transferencias entre Lojas permite:

- Identificar automaticamente desbalanceamentos de estoque
- Sugerir transferencias entre lojas do mesmo grupo
- Priorizar por urgencia (ruptura, alta, media, baixa)
- Exportar lista de transferencias para Excel
- Integrar com o fluxo de Pedido ao Fornecedor (CD)

## Conceitos Principais

### Grupos de Transferencia

Lojas sao organizadas em grupos regionais que podem trocar estoque entre si. Cada grupo tem:

- **Nome**: Identificacao do grupo (ex: "Regiao Nordeste")
- **CD Principal**: Centro de Distribuicao responsavel
- **Lojas**: Lista de lojas que podem transferir entre si

### Loja Doadora vs Receptora (v6.11)

| Tipo | Criterio | Acao |
|------|----------|------|
| Doadora | Cobertura > 90 dias | Pode enviar excesso acima de 90 dias |
| Receptora | Cobertura <= 90 dias E quantidade_pedido > 0 | Precisa receber estoque |

**Nota:** Lojas com cobertura > 90 dias NAO sao receptoras (podem apenas doar).

### Cobertura de Estoque

```
Cobertura (dias) = Estoque Atual / Demanda Media Diaria
```

## Fluxo de Transferencia

```
1. Pedido CD e processado
   ↓
2. Sistema identifica lojas com excesso
   ↓
3. Sistema identifica lojas com falta
   ↓
4. Calcula quantidade ideal de transferencia
   ↓
5. Registra oportunidades no banco
   ↓
6. Exibe na tela de Transferencias
   ↓
7. Usuario exporta e executa
```

## Interface do Usuario

### Tela Principal

Acesse via **Menu > Transferencias entre Lojas**

#### Cards de Estatisticas

| Card | Descricao |
|------|-----------|
| Oportunidades | Total de transferencias sugeridas |
| Criticas | Transferencias urgentes (ruptura) |
| Alta Prioridade | Transferencias importantes |
| Valor Estimado | Valor total das transferencias |
| Produtos | SKUs unicos envolvidos |

#### Tabela de Oportunidades

Colunas disponiveis:

| Coluna | Descricao |
|--------|-----------|
| Codigo | SKU do produto |
| Descricao | Nome do produto |
| ABC | Curva ABC do item |
| Transferencia | Loja Origem -> Loja Destino |
| Qtd | Quantidade sugerida |
| Valor | Valor estimado da transferencia |
| Urgencia | CRITICA, ALTA, MEDIA, BAIXA |

### Acoes Disponiveis

| Botao | Funcao |
|-------|--------|
| Exportar Excel | Baixa planilha com todas as oportunidades |
| Limpar Historico | Remove oportunidades antigas |

## Faixas de Prioridade (v6.11)

| Faixa | Cobertura | Prioridade | Descricao |
|-------|-----------|------------|-----------|
| RUPTURA | estoque = 0 | 0 (maxima) | Produto em ruptura efetiva |
| CRITICA | 0-30 dias | 1 | Ruptura iminente |
| ALTA | 31-60 dias | 2 | Situacao de alerta |
| MEDIA | 61-90 dias | 3 | Preventiva |
| > 90 dias | - | NAO RECEBE | Pode apenas doar |

**Ordem de atendimento:** RUPTURA > CRITICA > ALTA > MEDIA (menor prioridade primeiro)

## Regras de Calculo (v6.11)

### Identificacao de Doadores

Apenas lojas com cobertura > 90 dias podem doar:

```python
COBERTURA_MINIMA_DOADOR = 90  # dias

if cobertura_atual > COBERTURA_MINIMA_DOADOR:
    excesso_dias = cobertura_atual - COBERTURA_MINIMA_DOADOR
    excesso_unidades = int(excesso_dias * demanda_diaria)
    # Doador mantem minimo de 90 dias apos doar
```

**Exemplo:**
- Loja com 120 dias de cobertura, demanda 10 un/dia
- Excesso = (120 - 90) × 10 = 300 unidades disponiveis para doar

### Identificacao de Receptores

Apenas lojas com cobertura <= 90 dias E pedido pendente podem receber:

```python
if cobertura_atual <= 90 and quantidade_pedido > 0:
    # Loja e receptora
    # Prioridade determinada pela faixa de cobertura
```

### Quantidade de Transferencia

```python
# Excesso do doador
excesso_unidades = (cobertura_atual - 90) * demanda_diaria

# Arredondar para multiplo de embalagem (caixas fechadas)
multiplo = embalagem_arredondamento.get(cod_produto, 1)
qtd_transferir = (qtd_bruta // multiplo) * multiplo

# Nao transferir se resultado for 0
if qtd_transferir == 0:
    continue
```

**Exemplo:**
- Necessidade: 50 unidades
- Multiplo: 12 unidades (caixa)
- Transferir: 48 unidades (4 caixas fechadas)

### Algoritmo de Matching Otimizado

Para minimizar fragmentacao e otimizar frete:

```
1. Ordenar doadores por excesso (MAIOR primeiro)
2. Ordenar receptores por prioridade (RUPTURA > CRITICA > ALTA > MEDIA)
3. Para cada receptor:
   a. Buscar doador que cobre 100% da necessidade
   b. Se encontrou: fazer match exclusivo (1:1)
   c. Se nao encontrou: usar maior doador disponivel
4. Marcar doador como "usado" quando esgotar capacidade
```

**Objetivo:** Preferir 1 doador → 1 receptor para consolidar frete

### Parametros Configurados

| Parametro | Valor | Descricao |
|-----------|-------|-----------|
| COBERTURA_MINIMA_DOADOR | 90 | Dias minimos para poder doar |
| FAIXAS_PRIORIDADE | 4 faixas | RUPTURA, CRITICA, ALTA, MEDIA |
| Multiplo Embalagem | Variavel | Arredonda para baixo (caixas fechadas) |

### Restricoes

1. **Mesma loja nao pode enviar e receber** o mesmo produto
2. **Doador mantem minimo 90 dias** apos doacao
3. **Apenas lojas do mesmo grupo regional** podem transferir (V24)
4. **Lojas devem estar ativas** no grupo
5. **Apenas multiplos de embalagem** sao transferidos

## Integracao com Pedido CD

Quando um pedido para CD e processado:

1. Sistema consolida demanda de todas as lojas
2. Identifica produtos com desbalanceamento
3. **Calcula transferencias automaticamente**
4. Exibe badges na tela de pedido:
   - `Enviar X un` (laranja) - loja vai enviar
   - `Receber X un` (verde) - loja vai receber
5. Registra oportunidades para consulta posterior

### Visualizacao no Pedido

```
Fornecedor X
├── Loja A (doadora)
│   └── Produto 123 [Enviar 50 un -> Loja B]
└── Loja B (receptora)
    └── Produto 123 [Receber 50 un <- Loja A]
```

## Exportacao Excel (v6.11)

O arquivo exportado contem:

| Coluna | Descricao |
|--------|-----------|
| Cod Destino | Codigo da loja destino |
| Filial Dest | Nome abreviado da loja destino (GUS, IMB, etc.) |
| Codigo | SKU do produto |
| Descricao | Nome do produto |
| Curva ABC | Classificacao ABC |
| Cod Origem | Codigo da loja origem |
| Filial Orig | Nome abreviado da loja origem |
| Estoque Origem | Estoque atual do doador |
| Cobertura Origem | Cobertura do doador (dias) |
| Estoque Destino | Estoque atual do receptor |
| Cobertura Destino | Cobertura do receptor (dias) |
| Qtd Sugerida | Quantidade sugerida |
| Valor Estimado | Valor da transferencia |
| Urgencia | Faixa de prioridade |
| Data Calculo | Data/hora do calculo |

### Nomes Abreviados das Filiais

| Codigo | Abreviacao |
|--------|------------|
| 1 | GUS |
| 2 | IMB |
| 3 | PAL |
| 4 | TAM |
| 5 | AJU |
| 6 | JPA |
| 7 | PNG |
| 8 | CAU |
| 9 | BAR |
| 11 | FRT |
| 80 | MDC |
| 81 | OBC |
| 82 | OSAL |
| 91 | CA2 |
| 92 | CAB |
| 93 | ALH |
| 94 | LAU |

## API Endpoints

### GET /api/transferencias/oportunidades

Lista oportunidades de transferencia.

**Parametros:**
- `grupo_id` (opcional): Filtrar por grupo
- `horas` (opcional, default=24): Ultimas X horas

**Response:**
```json
{
  "success": true,
  "oportunidades": [...],
  "resumo": {
    "total": 45,
    "criticas": 5,
    "altas": 12,
    "valor_total": 15000.00,
    "produtos_unicos": 30
  }
}
```

### GET /api/transferencias/grupos

Lista grupos de transferencia disponiveis.

### GET /api/transferencias/exportar

Exporta oportunidades para Excel.

**Parametros:**
- `grupo_id` (opcional): Filtrar por grupo
- `horas` (opcional, default=24): Ultimas X horas

### DELETE /api/transferencias/limpar

Limpa historico de oportunidades.

## Configuracao de Grupos

### Criar Grupo via SQL

```sql
-- Criar grupo
INSERT INTO grupos_transferencia (nome, descricao, cd_principal, ativo)
VALUES ('Regiao Nordeste', 'Lojas do Nordeste', 1, TRUE);

-- Adicionar lojas ao grupo
INSERT INTO lojas_grupo_transferencia
(grupo_id, cod_empresa, nome_loja, pode_doar, pode_receber, prioridade_recebimento, ativo)
VALUES
(1, 1, 'CD Recife', TRUE, FALSE, 0, TRUE),
(1, 2, 'Loja Boa Viagem', TRUE, TRUE, 1, TRUE),
(1, 3, 'Loja Casa Forte', TRUE, TRUE, 2, TRUE);
```

### Campos da Configuracao

| Campo | Tipo | Descricao |
|-------|------|-----------|
| pode_doar | Boolean | Loja pode enviar estoque |
| pode_receber | Boolean | Loja pode receber estoque |
| prioridade_recebimento | Integer | Ordem de prioridade (menor = primeiro) |
| ativo | Boolean | Loja esta ativa no grupo |

## Requisitos de Banco

Execute `database/migration_v5.sql` para criar:

- `grupos_transferencia`
- `lojas_grupo_transferencia`
- `oportunidades_transferencia`

## Graceful Degradation

Se as tabelas nao existirem:

- Tela de transferencias mostra mensagem informativa
- Pedido CD funciona normalmente (sem calcular transferencias)
- API retorna lista vazia com aviso

## Boas Praticas

1. **Configure grupos regionais** com lojas que podem realmente transferir
2. **Defina CD principal** de cada grupo
3. **Revise oportunidades diariamente** para aproveitar desbalanceamentos
4. **Limpe historico periodicamente** para manter performance
5. **Priorize transferencias CRITICAS** para evitar rupturas
6. **Considere custo logistico** ao decidir executar transferencia
