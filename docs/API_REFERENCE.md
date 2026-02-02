# API Reference - Sistema de Previsão de Demanda

## Visão Geral

O sistema expõe APIs REST organizadas em blueprints por domínio de negócio.

**Base URL:** `http://localhost:5000`

---

## Blueprints e Endpoints

### 1. Previsão de Demanda (`/api/`)

#### POST `/api/gerar_previsao_banco_v2`
Gera previsão de demanda para produtos do fornecedor.

**Request Body:**
```json
{
    "cod_empresa": 1,
    "fornecedor": "12345678000190",
    "linha1": "ELETRICA",
    "linha3": "INTERRUPTORES",
    "horizonte_dias": 90,
    "metodo": "auto",
    "granularidade": "semanal"
}
```

**Response:**
```json
{
    "success": true,
    "dados": [
        {
            "SKU": "PROD001",
            "Loja": "L001",
            "Metodo": "SMA",
            "Previsao_1": 120,
            "Previsao_2": 125,
            "Previsao_3": 130
        }
    ],
    "resumo": {
        "total_produtos": 50,
        "metodo_mais_usado": "SMA",
        "mape_medio": 12.5
    },
    "arquivo_excel": "previsao_demanda_20260202_100000.xlsx"
}
```

**Erros:**
- `400`: Parâmetros inválidos
- `500`: Erro interno

---

#### POST `/api/exportar_tabela_comparativa`
Exporta comparação de previsões para Excel.

**Request Body:**
```json
{
    "dados": [...],
    "formato": "xlsx"
}
```

**Response:** Arquivo Excel para download

---

### 2. Pedido Fornecedor (`/api/pedido_fornecedor_integrado`)

#### POST `/api/pedido_fornecedor_integrado`
Calcula pedido otimizado para fornecedor.

**Request Body:**
```json
{
    "cnpj_fornecedor": "12345678000190",
    "cod_empresa": 1,
    "cobertura_dias": 30,
    "incluir_estoque_seguranca": true
}
```

**Response:**
```json
{
    "success": true,
    "pedido": {
        "fornecedor": "Fornecedor Exemplo",
        "total_itens": 45,
        "valor_total": 15000.00,
        "itens": [
            {
                "codigo": "PROD001",
                "descricao": "Produto 1",
                "quantidade": 100,
                "valor_unitario": 15.00,
                "valor_total": 1500.00
            }
        ]
    },
    "arquivo_excel": "pedido_fornecedor_20260202.xlsx"
}
```

---

### 3. Transferências (`/api/transferencias/`)

#### GET `/api/transferencias/oportunidades`
Lista oportunidades de transferência entre lojas.

**Query Parameters:**
- `cod_empresa_origem` (int, opcional): Filtrar por loja de origem
- `cod_empresa_destino` (int, opcional): Filtrar por loja de destino
- `categoria` (string, opcional): Filtrar por categoria

**Response:**
```json
{
    "success": true,
    "oportunidades": [
        {
            "codigo": "PROD001",
            "origem": "Loja 01",
            "destino": "Loja 05",
            "quantidade": 50,
            "cobertura_origem": 45,
            "cobertura_destino": 5,
            "prioridade": "ALTA"
        }
    ],
    "resumo": {
        "total_itens": 120,
        "valor_potencial": 45000.00
    }
}
```

---

### 4. Parâmetros Fornecedor (`/api/parametros-fornecedor/`)

#### GET `/api/parametros-fornecedor`
Lista parâmetros de todos os fornecedores.

**Response:**
```json
{
    "success": true,
    "parametros": [
        {
            "cnpj": "12345678000190",
            "nome_fantasia": "Fornecedor A",
            "lead_time_dias": 7,
            "ciclo_pedido_dias": 14,
            "pedido_minimo": 500.00,
            "multiplo_embalagem": 6
        }
    ]
}
```

#### POST `/api/parametros-fornecedor/<cnpj>/salvar-lote`
Salva parâmetros para múltiplas lojas.

**Request Body:**
```json
{
    "parametros": [
        {
            "cod_empresa": 1,
            "lead_time_dias": 7,
            "ciclo_pedido_dias": 14
        }
    ]
}
```

---

### 5. KPIs e Dashboard (`/api/kpis/`)

#### GET `/api/kpis/dados`
Retorna dados para dashboard de KPIs.

**Query Parameters:**
- `periodo` (string): "7d", "30d", "90d", "1y"
- `fornecedor` (string, opcional): CNPJ do fornecedor
- `cod_empresa` (int, opcional): Código da loja

**Response:**
```json
{
    "success": true,
    "kpis": {
        "acuracidade_previsao": 87.5,
        "nivel_servico": 95.2,
        "giro_estoque": 4.5,
        "cobertura_media": 25,
        "ruptura_percentual": 2.3
    },
    "graficos": {
        "evolucao_acuracidade": [...],
        "distribuicao_abc": [...]
    }
}
```

---

### 6. Demanda Validada (`/api/demanda_validada/`)

#### POST `/api/demanda_validada/salvar`
Salva demanda validada/ajustada pelo usuário.

**Request Body:**
```json
{
    "codigo": "PROD001",
    "cod_empresa": 1,
    "periodo": "2026-02",
    "demanda_original": 100,
    "demanda_validada": 120,
    "justificativa": "Evento promocional"
}
```

---

### 7. Configurações (`/api/parametros-globais/`)

#### GET `/api/parametros-globais`
Lista todos os parâmetros globais do sistema.

**Response:**
```json
{
    "success": true,
    "parametros": {
        "nivel_servico_padrao": 95,
        "horizonte_previsao_dias": 90,
        "metodo_padrao": "auto",
        "cobertura_seguranca_abc": {
            "A": 2,
            "B": 4,
            "C": 6
        }
    }
}
```

#### PUT `/api/parametros-globais/<chave>`
Atualiza um parâmetro global.

**Request Body:**
```json
{
    "valor": 97
}
```

---

## Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 400 | Requisição inválida (parâmetros incorretos) |
| 401 | Não autorizado |
| 404 | Recurso não encontrado |
| 500 | Erro interno do servidor |

---

## Autenticação

Atualmente a API não requer autenticação. Em produção, implementar:
- JWT tokens
- API keys por fornecedor/sistema

---

## Rate Limiting

Não implementado. Considerar para produção:
- 100 requests/minuto por IP
- 1000 requests/hora por usuário

---

## Versionamento

API atual: v2 (implícito nas rotas)

Futuras versões usarão prefixo: `/api/v3/...`
