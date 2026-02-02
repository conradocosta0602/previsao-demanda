# CLAUDE PROJECT - VALTER FC
## Sistema de Previsão de Demanda - Ferreira Costa

**Documento de Referência para Claude Code**
**Versão:** 1.0
**Data:** 02/02/2026
**Projeto:** previsao-demanda

---

# ÍNDICE

1. [Visão Geral](#1-visão-geral)
2. [Estrutura do Banco de Dados](#2-estrutura-do-banco-de-dados)
3. [Arquitetura da Aplicação](#3-arquitetura-da-aplicação)
4. [Rotas e APIs](#4-rotas-e-apis)
5. [Funcionalidades Principais](#5-funcionalidades-principais)
6. [Módulos Python (Core)](#6-módulos-python-core)
7. [Frontend (Templates e JavaScript)](#7-frontend-templates-e-javascript)
8. [Convenções e Padrões](#8-convenções-e-padrões)
9. [Fluxos de Dados](#9-fluxos-de-dados)
10. [Parâmetros e Configurações](#10-parâmetros-e-configurações)
11. [Histórico de Decisões](#11-histórico-de-decisões)
12. [Referência Rápida](#12-referência-rápida)

---

# 1. VISÃO GERAL

## 1.1 O que é o Sistema

Sistema completo de **Previsão de Demanda** para a rede Ferreira Costa, contemplando:
- Previsão estatística de vendas (múltiplos algoritmos)
- Gestão de pedidos ao fornecedor
- Transferências entre lojas
- Simulador de cenários
- Gestão de eventos (promoções, feriados)
- KPIs e dashboards

## 1.2 Stack Tecnológico

| Camada | Tecnologia |
|--------|------------|
| Backend | Flask (Python 3.x) |
| Banco de Dados | PostgreSQL (principal) + SQLite (eventos) |
| Frontend | HTML5 + CSS3 + JavaScript (Vanilla) |
| Gráficos | Chart.js |
| Processamento | NumPy, Pandas, SciPy, scikit-learn |
| Excel | openpyxl |

## 1.3 Localização do Projeto

```
C:\Users\valter.lino\OneDrive - FERREIRA COSTA E CIA LTDA\Área de Trabalho\Treinamentos\VS\previsao-demanda
```

## 1.4 Conexão com Banco de Dados

```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}
```

---

# 2. ESTRUTURA DO BANCO DE DADOS

## 2.1 Resumo das Tabelas

| Tabela | Registros | Propósito |
|--------|-----------|-----------|
| `cadastro_categorias` | 13 | Linhas/categorias de produtos (Linha 3) |
| `cadastro_fornecedores` | 6.379 | Fornecedores por empresa (duplicado por loja) |
| `cadastro_fornecedores_completo` | 11 | Fornecedores consolidados |
| `cadastro_lojas` | 16 | Filiais/lojas da rede |
| `cadastro_produtos` | 1.838 | Produtos ativos |
| `cadastro_produtos_completo` | 2.696 | Produtos com linha 3 e fornecedor |
| `demanda_validada` | 619 | Previsões validadas |
| `embalagem_arredondamento` | 2.630 | Múltiplos de caixa |
| `estoque_posicao_atual` | 42.803 | Estoque atual por loja/produto |
| `grupos_transferencia` | 2 | Grupos de lojas para transferência |
| `historico_estoque_diario` | 6.260.259 | Histórico de estoque (particionado) |
| `historico_vendas_diario` | 28.222.323 | Histórico de vendas (particionado) |
| `lojas_grupo_transferencia` | 9 | Lojas por grupo |
| `oportunidades_transferencia` | 116 | Sugestões de transferência |
| `padrao_compra_item` | 9.476 | Padrão de compra centralizado |
| `parametros_fornecedor` | 6.374 | Lead time, ciclo por fornecedor/loja |
| `parametros_globais` | 1 | Configurações globais |
| `situacao_compra_itens` | 12.781 | Status de compra de itens |
| `situacao_compra_regras` | 5 | Regras de situação de compra |

## 2.2 Tabelas Principais Detalhadas

### cadastro_produtos_completo (IMPORTANTE - Linha 3)
```sql
cod_produto       VARCHAR  -- Código do produto (PK)
descricao         VARCHAR  -- Descrição
cnpj_fornecedor   VARCHAR  -- CNPJ do fornecedor
nome_fornecedor   VARCHAR  -- Nome do fornecedor
categoria         VARCHAR  -- Categoria (Linha 1)
codigo_linha      VARCHAR  -- Código da Linha 3 (ex: UAA, UAB)
descricao_linha   VARCHAR  -- Descrição da Linha 3 (ex: Chuveiros)
ativo             BOOLEAN  -- Flag ativo
```

### historico_vendas_diario (28M registros - Particionado)
```sql
id           BIGINT    -- ID único
data         DATE      -- Data da venda
cod_empresa  INTEGER   -- Código da loja
codigo       INTEGER   -- Código do produto
qtd_venda    NUMERIC   -- Quantidade vendida
valor_venda  NUMERIC   -- Valor total
dia_semana   INTEGER   -- 1-7
semana_ano   INTEGER   -- ISO week
mes          INTEGER   -- 1-12
ano          INTEGER   -- 2023-2026
```

### estoque_posicao_atual
```sql
id              INTEGER  -- ID único
codigo          INTEGER  -- Código do produto
cod_empresa     INTEGER  -- Código da loja
estoque         NUMERIC  -- Quantidade disponível
qtd_pendente    NUMERIC  -- Em pedido
qtd_pend_transf NUMERIC  -- Em transferência
cue             NUMERIC  -- Custo unitário
preco_venda     NUMERIC  -- Preço de venda
sit_venda       VARCHAR  -- Situação de venda
curva_abc       VARCHAR  -- Classificação ABC
sit_compra      VARCHAR  -- Situação de compra
```

### parametros_fornecedor
```sql
id                  INTEGER  -- ID único
cnpj_fornecedor     VARCHAR  -- CNPJ (UK com empresa)
nome_fornecedor     VARCHAR  -- Nome
cod_empresa         INTEGER  -- Loja
tipo_destino        VARCHAR  -- LOJA ou CD
lead_time_dias      INTEGER  -- Lead time (default: 15)
ciclo_pedido_dias   INTEGER  -- Ciclo (default: 7)
pedido_minimo_valor NUMERIC  -- Valor mínimo
ativo               BOOLEAN  -- Flag ativo
```

## 2.3 Relacionamentos Principais

```
cadastro_produtos.id_fornecedor → cadastro_fornecedores.id
cadastro_produtos_completo.cnpj_fornecedor → cadastro_fornecedores.cnpj
parametros_fornecedor.cnpj_fornecedor → cadastro_fornecedores.cnpj
padrao_compra_item.codigo → cadastro_produtos.codigo
situacao_compra_itens.sit_compra → situacao_compra_regras.codigo_situacao
lojas_grupo_transferencia.grupo_id → grupos_transferencia.id
```

## 2.4 Filtro de Linha 3 (Sublinha)

A **Linha 3** é obtida da tabela `cadastro_produtos_completo`:
- Campo `codigo_linha`: código (ex: UAA, UAB, UBI)
- Campo `descricao_linha`: descrição (ex: Chuveiros, Resistências elétricas)

**API que popula o filtro:**
```
GET /api/sublinhas?linha=[categoria]
```

**Retorna:**
```json
[
  {"codigo_linha": "UAA", "descricao_linha": "Chuveiros"},
  {"codigo_linha": "UAB", "descricao_linha": "Resistências elétricas"}
]
```

---

# 3. ARQUITETURA DA APLICAÇÃO

## 3.1 Estrutura de Diretórios

```
previsao-demanda/
├── app.py                    # Aplicação Flask principal (~10.000 linhas)
├── requirements.txt          # Dependências
├── core/                     # Módulos de processamento
│   ├── data_adapter.py
│   ├── daily_data_loader.py
│   ├── forecasting_models.py
│   ├── method_selector.py
│   ├── aggregator.py
│   ├── stockout_handler.py
│   ├── outlier_detector.py
│   ├── seasonality_detector.py
│   ├── validation.py
│   ├── reporter.py
│   ├── replenishment_calculator.py
│   ├── smart_alerts.py
│   ├── event_manager_v2.py
│   ├── pedido_fornecedor_integrado.py
│   ├── order_processor.py
│   ├── scenario_simulator.py
│   ├── transferencia_regional.py
│   ├── flow_processor.py
│   ├── ml_selector.py
│   ├── padrao_compra.py
│   └── accuracy_metrics.py
├── templates/                # HTML
│   ├── index.html           # Previsão de demanda
│   ├── menu.html            # Menu principal
│   ├── simulador.html       # Simulador de cenários
│   ├── eventos_v2.html      # Gestão de eventos
│   ├── pedido_fornecedor_integrado.html
│   ├── transferencias.html
│   ├── kpis.html
│   └── ...
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js           # JavaScript principal
│       ├── simulador.js
│       ├── pedido_fornecedor.js
│       ├── transferencias.js
│       ├── kpis.js
│       └── multi-select.js
├── uploads/                  # Arquivos enviados
└── outputs/                  # Relatórios gerados
```

---

# 4. ROTAS E APIs

## 4.1 Páginas (GET)

| Rota | Descrição |
|------|-----------|
| `/menu` | Menu principal |
| `/` | Previsão de demanda |
| `/simulador` | Simulador de cenários |
| `/eventos_v2` | Gestão de eventos |
| `/pedido_fornecedor_integrado` | Pedidos ao fornecedor |
| `/transferencias` | Transferências entre lojas |
| `/kpis` | Dashboard de KPIs |
| `/visualizacao` | Visualização de demanda |

## 4.2 APIs de Dados (GET)

| Rota | Descrição |
|------|-----------|
| `/api/lojas` | Lista de lojas |
| `/api/fornecedores` | Lista de fornecedores |
| `/api/linhas` | Lista de categorias (Linha 1) |
| `/api/sublinhas` | Lista de sublinhas (Linha 3) |
| `/api/produtos_completo` | Produtos com todos atributos |
| `/api/vendas` | Histórico de vendas |

## 4.3 APIs de Processamento (POST)

| Rota | Descrição |
|------|-----------|
| `/api/gerar_previsao_banco_v2` | Gera previsão V2 |
| `/api/pedido_fornecedor_integrado` | Gera pedidos |
| `/api/pedido_fornecedor_integrado/exportar` | Exporta pedidos |
| `/api/exportar_tabela_comparativa` | Exporta comparativo |
| `/simulador/aplicar` | Aplica cenário |
| `/simulador/exportar` | Exporta cenário |

## 4.4 APIs de Eventos

| Rota | Método | Descrição |
|------|--------|-----------|
| `/eventos/v2/listar` | GET | Lista eventos |
| `/eventos/v2/cadastrar` | POST | Cria evento |
| `/eventos/v2/atualizar` | POST | Atualiza evento |
| `/eventos/v2/cancelar` | POST | Cancela evento |
| `/eventos/v2/exportar` | GET | Exporta eventos |
| `/eventos/v2/importar` | POST | Importa eventos |

## 4.5 APIs de Transferências

| Rota | Método | Descrição |
|------|--------|-----------|
| `/api/transferencias/oportunidades` | GET | Lista oportunidades |
| `/api/transferencias/grupos` | GET | Lista grupos |
| `/api/transferencias/exportar` | GET | Exporta oportunidades |

## 4.6 APIs de Parâmetros

| Rota | Método | Descrição |
|------|--------|-----------|
| `/api/parametros-fornecedor` | GET | Lista parâmetros |
| `/api/parametros-globais` | GET | Parâmetros globais |
| `/api/padrao-compra/buscar` | GET/POST | Padrão de compra |

---

# 5. FUNCIONALIDADES PRINCIPAIS

## 5.1 Previsão de Demanda

**O que faz:** Gera previsões estatísticas de vendas futuras

**Fluxo:**
1. Carrega histórico de vendas (2 anos)
2. Detecta características da série (tendência, sazonalidade)
3. Seleciona melhor método (Média Móvel, Exponencial, etc)
4. Gera previsão para N períodos
5. Aplica eventos (promoções, feriados)
6. Calcula métricas (WMAPE, BIAS)

**Tabelas:** `historico_vendas_diario`, `cadastro_produtos_completo`

**Arquivos:**
- Backend: `app.py`, `core/forecasting_models.py`, `core/method_selector.py`
- Frontend: `templates/index.html`, `static/js/app.js`

## 5.2 Relatório Detalhado por Fornecedor/Item

**O que faz:** Exibe tabela detalhada com previsão por produto

**Colunas da tabela:**
- Código, Descrição
- Previsão por período (Fev/2026, Mar/2026, etc)
- Total Previsão, Ano Anterior
- Variação %, Alerta, Situação

**NOTA:** Atualmente NÃO tem coluna de Linha 3. Para adicionar:
1. Modificar query para incluir `cadastro_produtos_completo.descricao_linha`
2. Adicionar coluna no frontend
3. Incluir na exportação Excel

## 5.3 Pedido ao Fornecedor Integrado

**O que faz:** Gera pedidos de reposição baseados em previsão

**Cálculo de cobertura:**
```
Cobertura = Lead_Time + Ciclo_Pedido + Segurança_ABC

Segurança_ABC:
- A: 2 dias (98% nível serviço)
- B: 4 dias (95% nível serviço)
- C: 6 dias (90% nível serviço)
```

**Fórmula:**
```
Quantidade = (Demanda_Diária × Cobertura) - Estoque_Atual
```

**Tabelas:** `historico_vendas_diario`, `estoque_posicao_atual`, `parametros_fornecedor`, `embalagem_arredondamento`

## 5.4 Transferências entre Lojas

**O que faz:** Identifica oportunidades de transferência de estoque

**Lógica:**
- Detecta lojas com EXCESSO (cobertura > 30 dias)
- Detecta lojas com FALTA (cobertura < 10 dias)
- Sugere transferência quando ambas estão no mesmo grupo

**Tabelas:** `grupos_transferencia`, `lojas_grupo_transferencia`, `oportunidades_transferencia`, `estoque_posicao_atual`

## 5.5 Simulador de Cenários

**O que faz:** Permite testar impacto de ajustes na previsão

**Tipos de ajuste:**
- Predefinido: Otimista (+20%), Pessimista (-20%)
- Global: % aplicado a tudo
- Por Loja: % por loja específica
- Por SKU: % por produto
- Por Período: % por mês

## 5.6 Gestão de Eventos

**O que faz:** Cadastra eventos que impactam demanda

**Tipos:** Promoção, Sazonal, Redução, Campanha, Feriado, Custom

**Campos:** nome, impacto_percentual (ex: +30%), data_inicio, data_fim, recorrente_anual

**Banco:** SQLite em `outputs/events_v2.db`

---

# 6. MÓDULOS PYTHON (CORE)

| Módulo | Classe/Função Principal | Propósito |
|--------|------------------------|-----------|
| `data_adapter.py` | `DataAdapter` | Carrega e valida dados |
| `forecasting_models.py` | `BaseForecaster` | Modelos de previsão |
| `method_selector.py` | `MethodSelector` | Seleção automática de método |
| `stockout_handler.py` | `StockoutHandler` | Tratamento de rupturas |
| `outlier_detector.py` | `auto_clean_outliers()` | Detecção de outliers |
| `aggregator.py` | `CDAggregator` | Agregação para CD |
| `reporter.py` | `ExcelReporter` | Geração de relatórios Excel |
| `event_manager_v2.py` | `EventManagerV2` | CRUD de eventos |
| `pedido_fornecedor_integrado.py` | `PedidoFornecedorIntegrado` | Geração de pedidos |
| `scenario_simulator.py` | `ScenarioSimulator` | Simulação de cenários |
| `transferencia_regional.py` | `TransferenciaRegional` | Transferências |
| `padrao_compra.py` | - | Padrão de compra centralizado |

---

# 7. FRONTEND (TEMPLATES E JAVASCRIPT)

## 7.1 Templates HTML

| Template | Funcionalidade |
|----------|----------------|
| `index.html` | Previsão de demanda (principal) |
| `menu.html` | Menu de navegação |
| `simulador.html` | Simulador de cenários |
| `eventos_v2.html` | Gestão de eventos |
| `pedido_fornecedor_integrado.html` | Pedidos ao fornecedor |
| `transferencias.html` | Transferências |
| `kpis.html` | Dashboard de KPIs |

## 7.2 JavaScript

| Arquivo | Funcionalidade |
|---------|----------------|
| `app.js` | Lógica principal, gráficos Chart.js |
| `simulador.js` | Lógica do simulador |
| `pedido_fornecedor.js` | Lógica de pedidos |
| `transferencias.js` | Lógica de transferências |
| `kpis.js` | Dashboard de KPIs |
| `multi-select.js` | Componente de multi-seleção |

## 7.3 Funções JavaScript Importantes (app.js)

```javascript
// Popula filtro de Linha 3
async function carregarSublinhas() {
    const url = '/api/sublinhas?linha=' + encodeURIComponent(JSON.stringify(linhasSelecionadas));
    // ...
}

// Exibe relatório detalhado
function exibirRelatorioDetalhado(dados) {
    // Renderiza tabela de fornecedor/item
}

// Exporta para Excel
async function exportarTabelaComparativa() {
    // POST /api/exportar_tabela_comparativa
}
```

---

# 8. CONVENÇÕES E PADRÕES

## 8.1 Banco de Dados

- **Nomenclatura:** snake_case (ex: `cod_empresa`, `nome_fantasia`)
- **Chaves primárias:** `id` (integer) ou campo natural (ex: `codigo`)
- **Timestamps:** `created_at`, `updated_at`
- **Flags:** `ativo` (boolean, default true)
- **Datas:** formato DATE ou TIMESTAMP

## 8.2 Python

- **Encoding:** UTF-8 (`# -*- coding: utf-8 -*-`)
- **Conexão DB:** `psycopg2` com `RealDictCursor`
- **Retorno API:** `jsonify({'success': True/False, 'data': ...})`
- **Erros:** try/except com traceback

## 8.3 JavaScript

- **Fetch API:** para chamadas AJAX
- **JSON:** para envio/recebimento de dados
- **Multi-select:** componente customizado

## 8.4 Nomes de Campos Importantes

| Campo no Código | Significado |
|-----------------|-------------|
| `cod_empresa` | Código da loja/filial |
| `codigo` | Código do produto (SKU) |
| `cnpj` ou `cnpj_fornecedor` | CNPJ do fornecedor |
| `nome_fantasia` | Nome do fornecedor |
| `codigo_linha` | Código da Linha 3 |
| `descricao_linha` | Descrição da Linha 3 |
| `lead_time_dias` | Lead time em dias |
| `ciclo_pedido_dias` | Ciclo de pedido em dias |
| `curva_abc` | Classificação ABC (A, B, C) |

---

# 9. FLUXOS DE DADOS

## 9.1 Fluxo de Previsão

```
1. Frontend: Seleciona filtros (loja, fornecedor, período)
2. POST /api/gerar_previsao_banco_v2
3. Backend:
   - Carrega historico_vendas_diario (2 anos)
   - Agrega por granularidade (semanal/mensal)
   - Para cada loja/SKU:
     - Detecta características (tendência, sazonalidade)
     - Seleciona método
     - Gera previsão
   - Agrega para CD
   - Aplica eventos
   - Gera relatório Excel
4. Retorna JSON + salva arquivo em /outputs
5. Frontend: Renderiza gráficos e tabelas
```

## 9.2 Fluxo de Pedido ao Fornecedor

```
1. Frontend: Seleciona fornecedor, destino, cobertura
2. POST /api/pedido_fornecedor_integrado
3. Backend:
   - Carrega previsão V2
   - Busca estoque atual
   - Calcula cobertura (ABC ou manual)
   - Calcula quantidade = (demanda × cobertura) - estoque
   - Arredonda para múltiplo de caixa
   - Agrupa por fornecedor
4. Retorna JSON ou Excel
```

---

# 10. PARÂMETROS E CONFIGURAÇÕES

## 10.1 Parâmetros de Cobertura ABC

```python
COBERTURA_ABC = {
    'A': {'seguranca': 2, 'nivel_servico': 0.98},
    'B': {'seguranca': 4, 'nivel_servico': 0.95},
    'C': {'seguranca': 6, 'nivel_servico': 0.90}
}
CICLO_PEDIDO_PADRAO = 7  # dias
```

## 10.2 Limites de Previsão

```python
TENDENCIA_QUEDA_MAX = -0.40  # -40% (ignorada)
TENDENCIA_ALTA_MAX = 0.50    # +50% (limitada)
WMAPE_MAX_ACEITAVEL = 0.50   # 50%
```

## 10.3 Parâmetros Globais (tabela parametros_globais)

| Chave | Valor | Descrição |
|-------|-------|-----------|
| `dias_transferencia` | 3 | Dias de trânsito entre lojas |

---

# 11. HISTÓRICO DE DECISÕES

## 11.1 Estrutura de Fornecedores

**Problema:** 6.379 registros em `cadastro_fornecedores` vs 1.108 fornecedores únicos

**Decisão:** A tabela armazena um registro por FORNECEDOR × EMPRESA (loja). Para contar fornecedores únicos, usar:
```sql
SELECT COUNT(DISTINCT cnpj) FROM cadastro_fornecedores
-- ou
SELECT COUNT(DISTINCT nome_fantasia) FROM cadastro_fornecedores
```

## 11.2 Filtro de Fornecedores na Aplicação

**Problema:** Filtro mostra ~25 fornecedores, mas banco tem 1.108

**Explicação:** O filtro mostra apenas fornecedores que têm produtos vinculados (`id_fornecedor` preenchido em `cadastro_produtos`). A maioria dos 1.108 está cadastrada mas sem produtos vinculados.

```sql
-- Fornecedores com produtos vinculados
SELECT COUNT(DISTINCT f.nome_fantasia)
FROM cadastro_fornecedores f
INNER JOIN cadastro_produtos p ON f.id = p.id_fornecedor
-- Resultado: ~20-25
```

## 11.3 Linha 3 (Sublinha)

**Problema:** Como incluir Linha 3 na exportação Excel

**Solução:** Usar tabela `cadastro_produtos_completo`:
- Campo `codigo_linha`: código da linha 3
- Campo `descricao_linha`: descrição da linha 3

**JOIN:**
```sql
SELECT p.*, pc.descricao_linha as linha3
FROM cadastro_produtos p
LEFT JOIN cadastro_produtos_completo pc ON p.codigo::text = pc.cod_produto
```

---

# 12. REFERÊNCIA RÁPIDA

## 12.1 Queries Úteis

```sql
-- Fornecedores únicos
SELECT COUNT(DISTINCT nome_fantasia) FROM cadastro_fornecedores;

-- Fornecedores com produtos
SELECT DISTINCT f.nome_fantasia
FROM cadastro_fornecedores f
INNER JOIN cadastro_produtos p ON f.id = p.id_fornecedor
ORDER BY f.nome_fantasia;

-- Linha 3 (sublinhas)
SELECT DISTINCT codigo_linha, descricao_linha
FROM cadastro_produtos_completo
WHERE codigo_linha IS NOT NULL
ORDER BY descricao_linha;

-- Produto com linha 3
SELECT p.codigo, p.descricao, pc.descricao_linha
FROM cadastro_produtos p
LEFT JOIN cadastro_produtos_completo pc ON p.codigo::text = pc.cod_produto;

-- Estoque atual por loja
SELECT cod_empresa, COUNT(*) as produtos, SUM(estoque) as total_estoque
FROM estoque_posicao_atual
GROUP BY cod_empresa
ORDER BY cod_empresa;

-- Vendas últimos 30 dias
SELECT codigo, SUM(qtd_venda) as total
FROM historico_vendas_diario
WHERE data >= CURRENT_DATE - 30
GROUP BY codigo
ORDER BY total DESC;
```

## 12.2 Arquivos para Modificar

| Funcionalidade | Arquivos |
|----------------|----------|
| Adicionar coluna na tabela | `app.py` (query), `static/js/app.js` (renderização) |
| Nova rota API | `app.py` |
| Novo módulo de processamento | `core/` + import em `app.py` |
| Modificar exportação Excel | `app.py` (função de exportação) |
| Modificar filtros | `static/js/app.js` + `templates/index.html` |

## 12.3 Comandos Úteis

```bash
# Iniciar aplicação
cd previsao-demanda
python app.py

# Verificar banco
psql -U postgres -d previsao_demanda

# Instalar dependências
pip install -r requirements.txt
```

---

# CHANGELOG

| Data | Versão | Alteração |
|------|--------|-----------|
| 02/02/2026 | 1.0 | Criação do documento |

---

**Este documento deve ser consultado no início de cada sessão para contexto completo do projeto.**
