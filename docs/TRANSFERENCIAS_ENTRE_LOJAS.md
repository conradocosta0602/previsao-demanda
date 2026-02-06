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

### Loja Doadora vs Receptora

| Tipo | Criterio | Acao |
|------|----------|------|
| Doadora | Cobertura > cobertura_alvo_item | Pode enviar estoque excedente |
| Receptora | quantidade_pedido > 0 | Precisa receber estoque |

**Nota:** A cobertura alvo e determinada por item (ver secao "Logica Hibrida de Cobertura").

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

## Niveis de Urgencia

### CRITICA (Vermelho)
- Loja destino com **cobertura = 0 dias**
- Produto em ruptura efetiva
- Prioridade maxima de atendimento

### ALTA (Laranja)
- Loja destino com **cobertura 1-3 dias**
- Ruptura iminente
- Atender em ate 24h

### MEDIA (Amarelo)
- Loja destino com **cobertura 4-7 dias**
- Situacao de alerta
- Atender na proxima rota

### BAIXA (Verde)
- Loja destino com **cobertura > 7 dias**
- Preventiva/otimizacao
- Atender quando conveniente

## Regras de Calculo

### Logica Hibrida de Cobertura (v5.7+)

O sistema usa uma **logica hibrida** para determinar a cobertura alvo de cada item:

```python
# Para cada item/loja:
cobertura_alvo_item = cobertura_dias if cobertura_dias else item['cobertura_necessaria_dias']
```

#### Cenario 1: Cobertura Fixa (informada no filtro)

Quando o usuario define uma cobertura especifica (ex: 90 dias):
- **Todos os itens** usam a mesma cobertura alvo
- Independente da curva ABC do produto

```
Filtro: Cobertura = 90 dias
→ Item A (curva A): alvo = 90 dias
→ Item B (curva B): alvo = 90 dias
→ Item C (curva C): alvo = 90 dias
```

#### Cenario 2: Cobertura ABC (automatica)

Quando nao e informada cobertura (ou seleciona "ABC"):
- **Cada item usa sua propria cobertura** calculada
- Formula: `Lead Time + Ciclo (7d) + Seguranca ABC`

```
Filtro: Cobertura = ABC
→ Item A (LT=15): alvo = 15 + 7 + 2 = 24 dias
→ Item B (LT=15): alvo = 15 + 7 + 4 = 26 dias
→ Item C (LT=20): alvo = 20 + 7 + 6 = 33 dias
```

### Quantidade de Transferencia

```python
# Para cada item em cada loja:
cobertura_alvo = cobertura_dias if cobertura_dias else item['cobertura_necessaria_dias']

# Excesso do doador (apos manter cobertura alvo)
estoque_minimo = cobertura_alvo * demanda_diaria
excesso_doador = estoque_atual - estoque_minimo

# Quantidade a transferir
qtd_transferir = min(excesso_doador, necessidade_receptor)
```

### Parametros Configurados

| Parametro | Valor | Descricao |
|-----------|-------|-----------|
| MARGEM_EXCESSO | 0 | Qualquer excesso acima do alvo pode ser doado |
| COBERTURA_MINIMA_DOADOR | cobertura_alvo | Doador mantem exatamente a cobertura alvo |

**Nota:** A margem de excesso foi removida (MARGEM_EXCESSO = 0) para permitir transferencias mais agressivas, especialmente em coberturas altas (60+ dias).

### Restricoes

1. **Mesma loja nao pode enviar e receber** o mesmo produto
2. **Doador nao pode ficar em ruptura** apos doacao
3. **Apenas lojas do mesmo grupo** podem transferir
4. **Lojas devem estar ativas** no grupo

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

## Exportacao Excel

O arquivo exportado contem:

| Coluna | Descricao |
|--------|-----------|
| Codigo | SKU do produto |
| Descricao | Nome do produto |
| ABC | Curva ABC |
| Loja Origem | Nome da loja doadora |
| Estoque Origem | Estoque atual do doador |
| Cobertura Origem (dias) | Cobertura do doador |
| Loja Destino | Nome da loja receptora |
| Estoque Destino | Estoque atual do receptor |
| Cobertura Destino (dias) | Cobertura do receptor |
| Qtd Transferir | Quantidade sugerida |
| Valor Estimado | Valor da transferencia |
| Urgencia | Nivel de urgencia |
| Grupo Regional | Nome do grupo |

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
