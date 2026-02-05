# Sistema de Demanda e Reabastecimento v5.6

Sistema completo para gestao de estoque multi-loja com Centro de Distribuicao (CD), combinando previsao de demanda Bottom-Up com politica de estoque baseada em curva ABC.

**Novidades v5.6 - Demanda Pre-Calculada e Validacao (Fev/2026):**
- **Demanda Pre-Calculada**: Cronjob diario (05:00) calcula demanda para todos os itens, garantindo integridade entre Tela de Demanda e Pedido Fornecedor
- **Sistema de Validacao de Conformidade**: Checklist automatico verifica se calculos seguem a metodologia documentada
- **22.656 registros** pre-calculados para 25 fornecedores ativos
- **APIs de Gerenciamento**: Endpoints para recalculo manual, ajustes e consultas

**Novidades v5.3 - Revisao do Modelo de Calculo:**
- **Ativacao dos 6 Metodos Estatisticos**: SMA, WMA, EMA, Tendencia, Sazonal e TSB agora aplicados corretamente
- **Sazonalidade como Multiplicador**: Fatores sazonais (0.5 a 2.0) aplicados na formula de previsao
- **Deteccao de Tendencia para Demanda Intermitente**: TSB com analise de queda/crescimento
- **Exclusao de Dados do Periodo de Previsao**: Corte de data para evitar usar dados reais como previsao
- **Saneamento de Rupturas com Limiar de 50%**: Cobertura minima de dados de estoque para identificar rupturas
- **Normalizacao pelo Total de Dias**: Corrige superestimacao em itens com vendas esporadicas

> **Documentacao Completa da Revisao:** [REVISAO_MODELO_PREVISAO_2026.md](REVISAO_MODELO_PREVISAO_2026.md)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-15+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Indice

1. [Caracteristicas Principais](#-caracteristicas-principais)
2. [Arquitetura do Sistema](#-arquitetura-do-sistema)
3. [Instalacao Rapida](#-instalacao-rapida)
4. [Como Usar](#-como-usar)
5. [Modulo de Previsao de Demanda](#-modulo-de-previsao-de-demanda)
6. [Modulo de Pedido ao Fornecedor](#-modulo-de-pedido-ao-fornecedor)
7. [Politica de Estoque ABC](#-politica-de-estoque-abc)
8. [Padrao de Compra](#-padrao-de-compra-centralizacao-de-pedidos)
9. [Estrutura do Projeto](#-estrutura-do-projeto)
9. [Formato dos Arquivos](#-formato-dos-arquivos)
10. [Changelog](#-changelog)
11. [FAQ](#-faq)
12. [Documentacao Completa](#-documentacao-completa)

---

## Caracteristicas Principais

### Previsao de Demanda V2 (Bottom-Up)

O sistema utiliza uma abordagem **Bottom-Up** que analisa cada produto individualmente e seleciona o melhor metodo estatistico:

| Metodo | Descricao | Quando e Usado |
|--------|-----------|----------------|
| **SMA** | Simple Moving Average | Demanda estavel, baixa variabilidade |
| **WMA** | Weighted Moving Average | Demanda com tendencia recente |
| **SES** | Simple Exponential Smoothing | Demanda com ruido moderado |
| **Linear Regression** | Regressao Linear | Tendencia clara de crescimento/queda |
| **TSB** | Trigg-Leach Smoothing | Demanda intermitente |
| **Decomposicao Sazonal** | Hibrida | Padroes sazonais detectados |

**Diferenciais:**
- Selecao automatica do melhor metodo por SKU
- Limitadores de tendencia (queda >40% limitada a -40%, alta >50% limitada a +50%)
- Sazonalidade anual (12 meses ou 52 semanas)
- Deteccao automatica de outliers (IQR + Z-Score)
- **Saneamento de rupturas**: Substitui zeros de ruptura por valores estimados via interpolacao sazonal

### Pedido ao Fornecedor Integrado

Novo modulo que integra previsao de demanda com calculo de pedidos:

- **Cobertura ABC**: Lead Time + Ciclo (7d) + Seguranca ABC
- **Estoque de Seguranca**: ES = Z x Sigma x Raiz(LT)
- **Arredondamento**: Multiplo de caixa automatico
- **Destino Configuravel**: Lojas (direto) ou CD (centralizado)

### Modulos Disponiveis

| Modulo | Descricao | Status |
|--------|-----------|--------|
| Previsao de Demanda | Forecasting Bottom-Up multi-metodo | Ativo |
| Simulador | Cenarios what-if | Ativo |
| Eventos | Calendario promocional | Ativo |
| KPIs e Metricas | Dashboard de performance | Ativo |
| **Pedido ao Fornecedor** | Calculo integrado multi-loja | **Atualizado v5.0** |
| **Padrao de Compra** | Centralizacao de pedidos por destino | **Novo v5.1** |
| **Transferencias entre Lojas** | Balanceamento automatico de estoque | **Novo v5.0** |
| **Parametros Fornecedor** | Lead Time, Ciclo, Faturamento Minimo | **Novo v5.0** |
| **Demanda Pre-Calculada** | Cronjob diario para integridade entre telas | **Novo v5.6** |
| **Validacao Conformidade** | Checklist automatico de metodologia | **Novo v5.6** |
| Pedido Manual | Entrada manual de pedidos | Ativo |

---

## Arquitetura do Sistema

```
+------------------+     +-------------------+     +------------------+
|                  |     |                   |     |                  |
|  BANCO DE DADOS  |---->|  PREVISAO V2      |---->|  PEDIDO          |
|  PostgreSQL      |     |  (Bottom-Up)      |     |  FORNECEDOR      |
|                  |     |                   |     |                  |
+------------------+     +-------------------+     +------------------+
        |                        |                        |
        v                        v                        v
+------------------+     +-------------------+     +------------------+
| - Historico      |     | - 6 Metodos       |     | - Cobertura ABC  |
| - Cadastros      |     | - Sazonalidade    |     | - Estoque Seg.   |
| - Estoques       |     | - Limitadores     |     | - Multiplo Caixa |
| - Parametros     |     | - Outliers        |     | - Agregacao      |
+------------------+     +-------------------+     +------------------+
```

---

## Instalacao Rapida

### Pre-requisitos

- Python 3.8 ou superior
- PostgreSQL 15 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo

**1. Clone o repositorio:**
```bash
git clone https://github.com/conradocosta0602/previsao-demanda.git
cd previsao-demanda
```

**2. Crie o ambiente virtual (recomendado):**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

**3. Instale as dependencias:**
```bash
pip install flask pandas numpy scipy scikit-learn statsmodels psycopg2-binary openpyxl
```

Ou usando requirements.txt:
```bash
pip install -r requirements.txt
```

**4. Configure o banco de dados PostgreSQL:**

Crie o banco de dados:
```sql
CREATE DATABASE demanda_reabastecimento;
```

Configure a conexao em `app.py` (linha ~1265):
```python
conn = psycopg2.connect(
    host="localhost",
    database="demanda_reabastecimento",
    user="postgres",
    password="sua_senha",
    port="5432"
)
```

**5. Execute o sistema:**
```bash
python app.py
```

**6. Acesse no navegador:**
```
http://localhost:5001/menu
```

---

## URLs de Acesso

Todas as telas do sistema estao disponiveis nas seguintes URLs (servidor rodando na porta 5001):

| Modulo | URL | Descricao |
|--------|-----|-----------|
| **Menu Principal** | `http://localhost:5001/menu` | Pagina inicial com acesso a todos os modulos |
| **Previsao de Demanda** | `http://localhost:5001/` | Geracao de previsoes de vendas (Bottom-Up V2) |
| **Pedido ao Fornecedor** | `http://localhost:5001/pedido_fornecedor_integrado` | Pedido multi-loja com calculo ABC |
| **Transferencias** | `http://localhost:5001/transferencias` | Gestao de transferencias entre lojas |
| **Simulador** | `http://localhost:5001/simulador` | Simulacao de cenarios what-if |
| **Eventos** | `http://localhost:5001/eventos` | Calendario promocional |
| **KPIs e Metricas** | `http://localhost:5001/kpis` | Dashboard de indicadores |
| **Pedido Manual** | `http://localhost:5001/pedido_manual` | Entrada manual de pedidos |

### APIs Disponiveis

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/gerar_previsao_banco` | POST | Gera previsao de demanda (Bottom-Up V2) |
| `/api/pedido_fornecedor_integrado` | POST | Calcula pedido ao fornecedor |
| `/api/transferencias/oportunidades` | GET | Lista oportunidades de transferencia |
| `/api/transferencias/grupos` | GET | Lista grupos de transferencia |
| `/api/transferencias/exportar` | GET | Exporta transferencias para Excel |
| `/api/demanda_validada/salvar` | POST | Salva demanda validada |
| `/api/demanda_validada/listar` | GET | Lista demandas validadas |
| `/api/pedido_planejado` | POST | Gera pedido planejado com demanda validada |
| `/api/demanda_job/status` | GET | Status do job de calculo de demanda |
| `/api/demanda_job/recalcular` | POST | Inicia recalculo de demanda |
| `/api/demanda_job/ajustar` | POST | Registra ajuste manual de demanda |
| `/api/demanda_job/consultar` | GET | Consulta demanda pre-calculada |
| `/api/validacao/executar-checklist` | POST | Executa checklist de conformidade |
| `/api/validacao/dashboard` | GET | Dashboard de metricas de conformidade |
| `/api/fornecedores` | GET | Lista fornecedores cadastrados |
| `/api/lojas` | GET | Lista lojas cadastradas |
| `/api/linhas` | GET | Lista linhas de produtos |
| `/api/sublinhas` | GET | Lista sublinhas de produtos |

---

## Como Usar

### 1. Menu Principal

Acesse `http://localhost:5001/menu` para ver todos os modulos disponiveis:

- **Previsao de Demanda** - Gere previsoes de vendas
- **Simulador** - Simule cenarios
- **Eventos** - Cadastre eventos promocionais
- **KPIs e Metricas** - Acompanhe indicadores
- **Pedido ao Fornecedor -> CD/Loja** - **NOVO** - Gere pedidos integrados
- **Transferencias** - Gerencie redistribuicoes
- **Pedido Manual** - Crie pedidos manualmente

### 2. Fluxo Tipico de Uso

```
1. Gerar Previsao de Demanda
   |
   v
2. (Opcional) Cadastrar Eventos Promocionais
   |
   v
3. Gerar Pedido ao Fornecedor
   |
   v
4. Analisar KPIs
```

---

## Modulo de Previsao de Demanda

### Funcionamento

O sistema utiliza a abordagem **Bottom-Up V2** que:

1. **Busca dados** do banco PostgreSQL (historico de vendas)
2. **Limpa outliers** usando IQR e Z-Score
3. **Detecta sazonalidade** por autocorrelacao
4. **Avalia 6 metodos** estatisticos
5. **Seleciona o melhor** baseado em WMAPE historico
6. **Aplica limitadores** de tendencia
7. **Gera previsao** para o periodo solicitado

### Limitadores de Tendencia

Para evitar previsoes irrealistas:

| Tipo | Limite | Acao |
|------|--------|------|
| Queda | > 40% | Limitada a -40% |
| Alta | > 50% | Limitada a +50% |

**Exemplo:**
- Historico: 100 un/mes
- Tendencia detectada: -60% (queda)
- Resultado: Tendencia limitada a -40%, previsao ajustada para 60 un/mes

### Saneamento de Rupturas

O sistema detecta automaticamente periodos de ruptura (quando venda=0 E estoque=0) e substitui por valores estimados para evitar distorcao na previsao.

**Hierarquia de Estimacao:**

| Prioridade | Metodo | Descricao |
|------------|--------|-----------|
| 1 | Interpolacao Sazonal | Usa valor do mesmo periodo do ano anterior |
| 2 | Media Adjacentes | Media dos periodos imediatamente antes e depois |
| 3 | Mediana do Periodo | Mediana dos periodos com venda > 0 |

**Exemplo:**
- Ruptura em: Janeiro/2025
- Busca: Janeiro/2024 → encontrou 95 unidades
- Resultado: Substitui o zero por 95 (metodo: sazonal_ano_anterior)

**Rastreabilidade:**
- Cada registro saneado e marcado com flag `foi_saneado = true`
- Metodo utilizado e registrado em `metodo_saneamento`
- Estatisticas de saneamento sao retornadas na API

### Granularidades Suportadas

| Granularidade | Periodos | Historico Minimo | Uso Recomendado |
|---------------|----------|------------------|-----------------|
| Mensal | 1-24 meses | 12 meses | Planejamento estrategico |
| Semanal | 4-104 semanas | 52 semanas | Reabastecimento |
| Diario | 7-365 dias | 365 dias | Operacoes day-to-day |

### Metricas de Acuracia

- **WMAPE**: Weighted Mean Absolute Percentage Error
- **BIAS**: Tendencia sistematica de erro
- **YoY**: Comparacao com mesmo periodo ano anterior

---

## Modulo de Pedido ao Fornecedor

### Nova Abordagem Integrada (v4.0)

O modulo de Pedido ao Fornecedor foi completamente reformulado para integrar com a previsao de demanda V2:

**Antes (v3.x):**
- Upload de arquivo Excel
- Calculos isolados da previsao
- Cobertura fixa

**Agora (v4.0):**
- Dados do banco PostgreSQL
- Previsao V2 em tempo real
- Cobertura baseada em ABC

### Formula de Cobertura

```
Cobertura (dias) = Lead Time + Ciclo Pedido + Seguranca ABC
```

Onde:
- **Lead Time**: Tempo de entrega do fornecedor (cadastro)
- **Ciclo Pedido**: 7 dias (pedido semanal)
- **Seguranca ABC**: Dias adicionais por classificacao

| Curva ABC | Seguranca (dias) | Justificativa |
|-----------|------------------|---------------|
| A | +2 dias | Alto giro, reposicao frequente |
| B | +4 dias | Medio giro, equilibrio |
| C | +6 dias | Baixo giro, maior variabilidade |

**Exemplo:**
- Lead Time: 15 dias
- Ciclo: 7 dias
- Curva ABC: B (+4 dias)
- **Cobertura Total**: 15 + 7 + 4 = **26 dias**

### Estoque de Seguranca

```
ES = Z x Sigma x Raiz(LT)
```

Onde:
- **Z**: Fator Z do nivel de servico (por curva ABC)
- **Sigma**: Desvio padrao diario da demanda
- **LT**: Lead time em dias

| Curva ABC | Nivel Servico | Fator Z |
|-----------|---------------|---------|
| A | 98% | 2.05 |
| B | 95% | 1.65 |
| C | 90% | 1.28 |

### Calculo da Quantidade a Pedir

```
Qtd Pedido = (Demanda x Cobertura) + ES - Estoque Disponivel - Estoque Transito
```

Com arredondamento para o multiplo de caixa mais proximo (para cima).

### Filtros Disponiveis

- **Destino**: Lojas (direto) ou CD (centralizado)
- **Empresa**: Loja/CD especifico ou todas
- **Fornecedor**: Fornecedor especifico ou todos
- **Categoria**: Categoria especifica ou todas
- **Cobertura**: Automatica (ABC) ou fixa (15, 21, 30, 45 dias)

---

## Politica de Estoque ABC

### Classificacao ABC

A classificacao ABC e definida no cadastro de produtos e reflete a importancia de cada item:

| Curva | Caracteristica | % SKUs (tipico) | % Faturamento (tipico) |
|-------|----------------|-----------------|------------------------|
| A | Alto giro | 20% | 80% |
| B | Medio giro | 30% | 15% |
| C | Baixo giro | 50% | 5% |

### Impacto da Curva ABC

A classificacao ABC influencia:

1. **Nivel de Servico**: A=98%, B=95%, C=90%
2. **Dias de Seguranca**: A=+2d, B=+4d, C=+6d
3. **Prioridade de Atencao**: Itens A recebem mais foco

### Por que nao usamos CV (Coeficiente de Variacao)?

Na versao v3.x, o sistema usava uma formula hibrida ABC + CV. Na v4.0, simplificamos para apenas ABC. Motivos:

1. **Previsao V2 ja captura variabilidade**: Os 6 metodos estatisticos, limitadores de tendencia e deteccao de outliers ja tratam a variabilidade da demanda
2. **Redundancia**: Calcular CV sobre dados que ja foram processados pela previsao V2 adiciona complexidade sem ganho proporcional
3. **Simplicidade operacional**: ABC e uma classificacao conhecida e usada pela equipe de compras

---

## Padrao de Compra (Centralizacao de Pedidos)

### O que e o Padrao de Compra?

O **Padrao de Compra** e um mecanismo de centralizacao de pedidos. Para cada SKU, define-se uma **loja destino** (ex: filial 80) que recebera o pedido ao fornecedor, mesmo que o produto seja vendido em diversas outras lojas. O sistema agrega automaticamente a demanda de todas as lojas vendedoras em um unico pedido destinado ao ponto de recebimento definido.

### Estrutura de Dados

**Tabela `padrao_compra_item`:**
```sql
CREATE TABLE padrao_compra_item (
    id SERIAL PRIMARY KEY,
    codigo INTEGER NOT NULL,           -- SKU do produto
    cod_empresa_venda INTEGER NOT NULL, -- Loja onde o produto e vendido
    cod_empresa_destino INTEGER NOT NULL -- Loja que recebe o pedido
);
```

**Tabela `parametros_globais`:**
```sql
-- Parametro de dias adicionais de cobertura para transferencia
INSERT INTO parametros_globais (chave, valor, descricao)
VALUES ('dias_transferencia_padrao_compra', '10',
        'Dias adicionais de cobertura para transferencia entre filiais no padrao de compra');
```

### Visualizacao na Tela de Pedido ao Fornecedor

A tela de **Pedido ao Fornecedor** possui um seletor de visualizacao com duas opcoes:

| Visualizacao | Descricao |
|-------------|-----------|
| **Por Padrao de Compra (Destino)** | **Padrao.** Agrupa pedidos pela loja destino definida no padrao de compra |
| Por Fornecedor (Padrao) | Exibe pedidos separados por loja, sem agregacao |

Quando a visualizacao "Por Padrao de Compra" esta ativa:

1. O sistema consulta a tabela `padrao_compra_item` para identificar quais SKUs possuem centralizacao
2. Agrupa os itens por `codigo + destino + fornecedor`, somando quantidades de pedido, valores, estoques e demandas de todas as lojas de origem
3. Exibe a hierarquia: **Destino > Fornecedor > Itens**
4. Cada item mostra um badge com as lojas de origem (ex: "Lojas: 10, 20, 30")

### Ajuste de Cobertura para Transferencia

Para itens centralizados (loja destino diferente das lojas de venda), o sistema adiciona **10 dias extras de cobertura** para cobrir o tempo de transferencia da mercadoria entre filiais. Esse valor e configuravel na tabela `parametros_globais` com a chave `dias_transferencia_padrao_compra`.

### Arquivos Relacionados

| Arquivo | Funcao |
|---------|--------|
| `core/padrao_compra.py` | Logica de negocio do padrao de compra |
| `database/migration_v7_padrao_compra.sql` | Criacao das tabelas |
| `database/importar_padrao_compra.py` | Importacao de dados via Excel/CSV |
| `templates/pedido_fornecedor_integrado.html` | Interface integrada com toggle de visualizacao |
| `app.py` (rota `/api/padrao-compra/buscar`) | API que retorna mapeamento de centralizacao |
| `app.py` (rota `/api/padrao-compra/exportar`) | API de exportacao Excel |

### FAQ - Padrao de Compra

**P: Todo SKU precisa ter Padrao de Compra cadastrado?**
R: Nao. Apenas SKUs que devem ser centralizados. Itens sem cadastro aparecem normalmente na visualizacao por fornecedor.

**P: Um mesmo SKU pode ter multiplas lojas de venda com destinos diferentes?**
R: Sim. Cada combinacao `codigo + cod_empresa_venda` pode ter um `cod_empresa_destino` diferente.

**P: O ajuste de +10 dias de transferencia e configuravel?**
R: Sim. Altere o valor na tabela `parametros_globais` com a chave `dias_transferencia_padrao_compra`.

**P: A demanda de cada loja de origem e calculada individualmente?**
R: Sim. O sistema calcula a previsao de demanda de cada loja de venda usando os mesmos 6 metodos estatisticos (Bottom-Up V2). Depois, soma as quantidades para gerar o pedido centralizado.

---

## Estrutura do Projeto

```
previsao-demanda/
|
|-- app.py                              # Aplicacao Flask principal (~4500 linhas)
|
|-- core/                               # Modulos de negocio
|   |-- forecasting_models.py           # 6 metodos de previsao
|   |-- method_selector.py              # Selecao automatica de metodo
|   |-- ml_selector.py                  # Machine Learning (Random Forest)
|   |-- seasonality_detector.py         # Deteccao de sazonalidade
|   |-- outlier_detector.py             # Deteccao de outliers
|   |-- pedido_fornecedor_integrado.py  # Calculo de pedidos ABC
|   |-- demand_calculator.py            # Calculador de demanda unificado
|   |-- validador_conformidade.py       # NOVO v5.6 - Validador de metodologia
|   |-- auto_logger.py                  # Logging automatico
|   |-- padrao_compra.py                # Logica de Padrao de Compra
|   |-- smart_alerts.py                 # Alertas inteligentes
|   |-- event_manager.py                # Gerenciador de eventos
|   |-- scenario_simulator.py           # Simulador de cenarios
|   |-- replenishment_calculator.py     # Calculos de reabastecimento
|   +-- flow_processor.py               # Processador de fluxos
|
|-- jobs/                               # Jobs agendados
|   |-- calcular_demanda_diaria.py      # NOVO v5.6 - Cronjob de demanda
|   |-- checklist_diario.py             # NOVO v5.6 - Checklist de conformidade
|   +-- configuracao_jobs.py            # Configuracao de agendamentos
|
|-- templates/                          # Templates HTML
|   |-- menu.html                       # Menu principal
|   |-- index.html                      # Previsao de demanda
|   |-- pedido_fornecedor_integrado.html # NOVO - Pedido integrado
|   |-- simulador.html                  # Simulador
|   |-- eventos_simples.html            # Eventos
|   |-- kpis.html                       # KPIs
|   |-- transferencias.html             # Transferencias
|   +-- pedido_manual.html              # Pedido manual
|
|-- static/
|   |-- css/style.css                   # Estilos CSS
|   +-- js/app.js                       # JavaScript principal
|
|-- database/
|   |-- migration_v7_padrao_compra.sql  # Tabelas do Padrao de Compra
|   |-- migration_v10_auditoria.sql     # NOVO v5.6 - Tabelas de auditoria
|   |-- migration_v12_demanda_pre.sql   # NOVO v5.6 - Demanda pre-calculada
|   |-- importar_padrao_compra.py       # Importacao de dados de centralizacao
|   +-- ...                             # Outras migrations e importadores
|
|-- docs/                               # Documentacao
|   |-- GRANULARIDADE_E_PREVISOES.md    # Guia de granularidades
|   +-- CORRECAO_SAZONALIDADE_ANUAL.md  # Correcao v3.1.2
|
+-- README.md                           # Este arquivo
```

---

## Formato dos Arquivos

### Tabelas do Banco de Dados

**historico_vendas_diario:**
```sql
CREATE TABLE historico_vendas_diario (
    id SERIAL PRIMARY KEY,
    codigo INTEGER NOT NULL,
    cod_empresa INTEGER NOT NULL,
    data DATE NOT NULL,
    qtd_venda NUMERIC(12,2)
);
```

**cadastro_produtos:**
```sql
CREATE TABLE cadastro_produtos (
    id SERIAL PRIMARY KEY,
    codigo INTEGER UNIQUE NOT NULL,
    descricao VARCHAR(200),
    categoria VARCHAR(100),
    subcategoria VARCHAR(100),
    curva_abc CHAR(1),  -- 'A', 'B' ou 'C'
    und_venda VARCHAR(20),
    id_fornecedor INTEGER,
    ativo BOOLEAN DEFAULT TRUE
);
```

**cadastro_fornecedores:**
```sql
CREATE TABLE cadastro_fornecedores (
    id_fornecedor SERIAL PRIMARY KEY,
    codigo_fornecedor VARCHAR(20),
    nome_fornecedor VARCHAR(200),
    lead_time_dias INTEGER DEFAULT 15,
    pedido_minimo NUMERIC(12,2)
);
```

**estoque_atual:**
```sql
CREATE TABLE estoque_atual (
    id SERIAL PRIMARY KEY,
    codigo INTEGER NOT NULL,
    cod_empresa INTEGER NOT NULL,
    qtd_disponivel NUMERIC(12,2)
);
```

**parametros_gondola:**
```sql
CREATE TABLE parametros_gondola (
    id SERIAL PRIMARY KEY,
    codigo INTEGER NOT NULL,
    cod_empresa INTEGER NOT NULL,
    multiplo INTEGER DEFAULT 1,
    lote_minimo INTEGER DEFAULT 1,
    estoque_seguranca NUMERIC(12,2) DEFAULT 0
);
```

---

## Changelog

### v5.6 (Fevereiro 2026) - ATUAL

**Sistema de Demanda Pre-Calculada:**

Esta versao resolve o problema de inconsistencia entre a Tela de Demanda e a Tela de Pedido Fornecedor, que utilizavam metodos de calculo diferentes.

**1. Cronjob de Calculo Diario (05:00):**
- Processa todos os itens de todos os fornecedores ativos
- Aplica os 6 metodos estatisticos (SMA, WMA, EMA, Tendencia, Sazonal, TSB)
- Aplica limitador V11 (-40% a +50% vs ano anterior)
- Aplica fatores sazonais (0.5 a 2.0)
- Salva na tabela `demanda_pre_calculada`
- Processamento paralelo com ThreadPoolExecutor (4 workers)

**2. Resultado da Primeira Execucao:**
- 25 fornecedores processados
- 2.696 itens calculados
- 22.656 registros salvos (12 meses x item)
- 0 erros
- Tempo: 55 minutos

**3. APIs de Gerenciamento:**
- `/api/demanda_job/status` - Status e estatisticas
- `/api/demanda_job/recalcular` - Recalculo manual (por fornecedor ou todos)
- `/api/demanda_job/ajustar` - Ajustes manuais de demanda
- `/api/demanda_job/consultar` - Consulta demanda pre-calculada

**4. Sistema de Validacao de Conformidade:**
- Checklist diario automatico (06:00)
- 10 verificacoes de integridade da metodologia
- Alertas por email em caso de desvios
- Dashboard de metricas de qualidade
- Auditoria completa de todas as execucoes

**Arquivos Criados:**
- `jobs/calcular_demanda_diaria.py` - Cronjob principal
- `database/migration_v12_demanda_pre_calculada.sql` - Tabelas
- `app/blueprints/demanda_job.py` - APIs de gerenciamento
- `app/utils/demanda_pre_calculada.py` - Funcoes utilitarias
- `core/validador_conformidade.py` - Validador de metodologia
- `jobs/checklist_diario.py` - Checklist automatico

**Tabelas Criadas:**
- `demanda_pre_calculada` - Demanda pre-calculada por item/mes
- `demanda_pre_calculada_historico` - Historico de calculos
- `demanda_calculo_execucao` - Log de execucoes do job
- `auditoria_conformidade` - Log de validacoes
- `auditoria_calculos` - Auditoria de calculos individuais

**Documentacao:**
- [REVISAO_MODELO_PREVISAO_2026.md - Secao 15](REVISAO_MODELO_PREVISAO_2026.md)

---

### v5.3 (Fevereiro 2026)

**Revisao Completa do Modelo de Calculo de Previsao:**

Esta versao corrige problemas fundamentais no calculo de previsao que causavam superestimacao (ex: DICOMPEL +81.6%, PHILIPS IL 991 un previstas com historico de 22 un).

**1. Ativacao dos 6 Metodos Estatisticos:**
- SMA, WMA, EMA, Tendencia, Sazonal e TSB ja existiam no `DemandCalculator` mas nao estavam sendo usados
- Agora a formula usa `demanda_diaria_inteligente` retornada pelo calculador

**2. Sazonalidade como Multiplicador:**
- Fatores sazonais (0.5 a 2.0) aplicados na formula de previsao
- Ex: fator 1.3 para dezembro = 30% acima da media

**3. Deteccao de Tendencia para Demanda Intermitente:**
- TSB simplificado agora detecta queda/crescimento comparando primeira e segunda metade da serie
- Produtos em declinio tem previsao ajustada proporcionalmente

**4. Exclusao de Dados do Periodo de Previsao:**
- Corte de data para evitar usar dados reais (ex: Jan/2026) como base para previsao do mesmo periodo
- Resolve inflacao de previsao quando dados futuros ja existem no banco

**5. Saneamento de Rupturas com Limiar de 50%:**
- Se cobertura de dados de estoque >= 50%: saneamento de rupturas ativo (exclui rupturas reais)
- Se cobertura < 50%: normaliza demanda pelo total de dias do periodo
- Distingue corretamente entre "ruptura" (estoque=0, venda=0) e "demanda zero real" (estoque>0, venda=0)

**6. Normalizacao pelo Total de Dias:**
- Corrige o erro de calcular media apenas sobre dias com venda
- Ex: 10.000 un em 200 dias de venda / 730 dias totais = 13.7 un/dia (nao 50 un/dia)

**Arquivos Modificados:**
- `app/blueprints/previsao.py` - Logica principal de calculo revisada
- `core/demand_calculator.py` - TSB com deteccao de tendencia

**Documentacao:**
- [REVISAO_MODELO_PREVISAO_2026.md](REVISAO_MODELO_PREVISAO_2026.md) - Documentacao completa da revisao

### v5.2 (Fevereiro 2026)

**Melhorias na Tabela Comparativa:**
- **Detalhamento por Fornecedor**: Tabela comparativa agora mostra linhas separadas para cada fornecedor quando multiplos sao selecionados
- **Variacao % Mes a Mes**: Nova linha de variacao percentual por periodo para cada fornecedor (Prev vs Ano Ant)
- **Total Consolidado**: Linha de totalizacao com variacao % por periodo para todos os fornecedores

**Sistema de Ajuste Manual de Demanda:**
- **Persistencia de Ajustes**: Ajustes manuais salvos no banco de dados sao aplicados automaticamente ao recarregar previsao
- **Atualizacao em Tempo Real**: Ao salvar ajuste, valores sao atualizados na:
  - Tabela de itens detalhados (celula amarela)
  - Linha do fornecedor na tabela comparativa
  - Linha do Total Consolidado na tabela comparativa
  - Grafico principal de previsao
- **Rastreabilidade**: Historico completo de ajustes por item/periodo

**Tabelas Utilizadas:**
- `ajuste_previsao` - Armazena ajustes ativos por item/periodo/granularidade
- `ajuste_previsao_historico` - Historico de todas as alteracoes

**Arquivos Modificados:**
- `static/js/app.js` - Funcoes `preencherTabelaComparativaV2` e `salvarAjustesItem` com data-attributes para atualizacao em tempo real
- `app/blueprints/previsao.py` - Carregamento de ajustes do banco ao gerar previsao

### v5.1 (Janeiro 2026)

**Novas Funcionalidades:**
- **Padrao de Compra**: Centralizacao de pedidos por loja destino, integrando demanda de multiplas lojas vendedoras em um unico pedido
- **Visualizacao por Destino**: Toggle na tela de Pedido ao Fornecedor para alternar entre visao padrao e visao por Padrao de Compra
- **Ajuste de Cobertura por Transferencia**: +10 dias configuravel para cobrir tempo de transferencia entre filiais
- **Agregacao Automatica**: Soma quantidades, estoques e demandas de todas as lojas de origem por SKU
- **Central de Parametros**: Coluna de Padrao de Compra na tabela de produtos do fornecedor

**Tabelas Criadas:**
- `padrao_compra_item` - Mapeamento SKU > Loja Venda > Loja Destino
- `parametros_globais` - Parametros configuravel como dias de transferencia

**APIs Adicionadas:**
- `POST /api/padrao-compra/buscar` - Consulta mapeamento de centralizacao por lista de codigos
- `POST /api/padrao-compra/exportar` - Exportacao Excel agrupada por destino

### v5.0 (Janeiro 2026)

**Novas Funcionalidades:**
- **Pedido Multi-Loja**: Layout hierarquico Fornecedor > Loja > Itens com multi-selecao
- **Transferencias entre Lojas**: Identificacao automatica de oportunidades de balanceamento
- **Parametros de Fornecedor**: Importacao de Lead Time, Ciclo de Pedido e Faturamento Minimo
- **Graceful Degradation**: Sistema funciona mesmo sem tabelas novas (migration_v5.sql)

**Melhorias de Interface:**
- Multi-selecao em filtros (Lojas, Fornecedores, Categorias)
- Badges visuais para transferencias (Enviar/Receber)
- Ordenacao do Excel por Codigo Filial e CNPJ Fornecedor
- Botao "Limpar Historico" na tela de transferencias
- Ordenacao por criticidade de alertas na tabela de previsao detalhada

**Remocoes:**
- Upload de arquivo Excel na tela de Previsao de Demanda (agora somente via banco de dados)

**Seguranca:**
- Credenciais do banco via variaveis de ambiente
- Arquivo .env.example para configuracao

**Documentacao:**
- docs/PEDIDO_FORNECEDOR_INTEGRADO.md
- docs/TRANSFERENCIAS_ENTRE_LOJAS.md

### v4.0 (Janeiro 2026)

**Novas Funcionalidades:**
- Modulo de Pedido ao Fornecedor Integrado com previsao V2
- Politica de estoque baseada exclusivamente em curva ABC
- Formula de cobertura simplificada: Lead Time + Ciclo + Seguranca ABC
- Interface unificada no menu principal

**Remocoes:**
- Modulo de Reabastecimento antigo (upload Excel)
- Modulo de Pedido por Fornecedor antigo
- Modulo de Pedido CD antigo
- Calculo de CV (Coeficiente de Variacao) - substituido por ABC puro

**Melhorias:**
- Renomeacao do sistema para "Sistema de Demanda e Reabastecimento"
- Consolidacao do botao V2 no botao "Gerar Previsao" principal
- Limpeza de codigo e rotas nao utilizadas

### v3.1.2 (Janeiro 2026)

**Correcao Critica:**
- Sazonalidade semanal agora usa 52 semanas (anual) em vez de 4 semanas (ciclo artificial)
- Amplitude dos fatores sazonais aumentou de 1.8% para 31.27%

### v3.1 (Janeiro 2026)

**Melhorias de Previsao:**
- Escala dinamica de graficos
- Ajuste sazonal baseado em granularidade
- Correcao de previsoes planas
- Logging detalhado de previsoes
- Documentacao sobre granularidades

### v3.0 (Dezembro 2025)

**Lancamento Inicial:**
- Previsao de demanda com 6 metodos
- Selecao automatica (AUTO) e Machine Learning (ML)
- Reabastecimento com 3 fluxos
- Calendario promocional
- Simulador de cenarios

---

## FAQ

### Previsao de Demanda

**P: Qual a diferenca entre AUTO e ML na selecao de metodo?**
R: AUTO usa regras baseadas em caracteristicas da demanda (CV, tendencia, sazonalidade). ML usa Random Forest com 15+ features para selecionar o metodo. ML tende a ser mais preciso, AUTO e mais rapido.

**P: Quantos meses de historico preciso?**
R:
- Mensal: Minimo 12 meses. Ideal: 24+ meses
- Semanal: Minimo 52 semanas. Ideal: 104 semanas
- Diario: Minimo 365 dias. Ideal: 730 dias

**P: Por que previsoes mensais e semanais dao resultados diferentes?**
R: Diferencas de 5-15% sao normais devido a janelas adaptativas, agregacao e fatores sazonais distintos. Consulte a documentacao de granularidade para detalhes.

**P: O que significam os limitadores de tendencia?**
R: Quedas >40% sao limitadas a -40% (protecao contra dados anomalos). Altas >50% sao limitadas a +50% (protecao contra otimismo excessivo).

**P: Como a ferramenta trata rupturas (falta de estoque) no historico?**
R: O sistema detecta automaticamente rupturas (venda=0 E estoque=0) e substitui por valores estimados usando interpolacao sazonal. A hierarquia de estimacao e: (1) mesmo periodo do ano anterior, (2) media dos periodos adjacentes, (3) mediana do periodo. Isso evita que zeros de ruptura subestimem a previsao de demanda.

**P: Preciso da coluna de estoque para o saneamento funcionar?**
R: Sim. A tabela `historico_estoque_diario` deve estar preenchida. Se nao houver dados de estoque, o sistema nao consegue distinguir entre "nao vendeu porque nao teve demanda" e "nao vendeu porque nao tinha estoque".

### Pedido ao Fornecedor

**P: Por que a cobertura e calculada com ABC e nao com CV?**
R: A previsao V2 ja captura a variabilidade da demanda atraves dos 6 metodos estatisticos, limitadores e deteccao de outliers. Adicionar CV seria redundante.

**P: Posso usar uma cobertura fixa?**
R: Sim. O filtro "Cobertura (dias)" permite escolher entre automatica (ABC) ou valores fixos de 15, 21, 30 ou 45 dias.

**P: Como funciona o arredondamento para multiplo de caixa?**
R: A quantidade calculada e arredondada para cima ate o proximo multiplo de caixa. Se o multiplo e 12 e a necessidade e 15, o pedido sera de 24.

**P: Qual a diferenca entre destino Loja e CD?**
R: "Lojas" processa pedidos para lojas que compram diretamente do fornecedor. "CD" processa pedidos para o Centro de Distribuicao que depois distribui para as lojas.

### Politica de Estoque

**P: Como a curva ABC e definida?**
R: A curva ABC deve estar cadastrada no campo `curva_abc` da tabela `cadastro_produtos`. Valores aceitos: 'A', 'B' ou 'C'.

**P: O que acontece se um produto nao tem curva ABC cadastrada?**
R: O sistema assume curva 'B' como padrao (nivel de servico 95%, +4 dias de seguranca).

**P: Os parametros de nivel de servico podem ser alterados?**
R: Sim. No arquivo `core/pedido_fornecedor_integrado.py`, edite as constantes `NIVEL_SERVICO_ABC` e `SEGURANCA_BASE_ABC`.

---

## Documentacao Completa

- **[REVISAO_MODELO_PREVISAO_2026.md](REVISAO_MODELO_PREVISAO_2026.md)** - **NOVO** - Revisao completa do modelo de calculo (Fev/2026)
- **[docs/PEDIDO_FORNECEDOR_INTEGRADO.md](docs/PEDIDO_FORNECEDOR_INTEGRADO.md)** - Guia completo do pedido multi-loja
- **[docs/TRANSFERENCIAS_ENTRE_LOJAS.md](docs/TRANSFERENCIAS_ENTRE_LOJAS.md)** - Sistema de transferencias regionais
- **[GRANULARIDADE_E_PREVISOES.md](GRANULARIDADE_E_PREVISOES.md)** - Guia sobre diferencas entre granularidades
- **[CORRECAO_SAZONALIDADE_ANUAL_SEMANAL.md](CORRECAO_SAZONALIDADE_ANUAL_SEMANAL.md)** - Correcao critica v3.1.2
- **[README_ABORDAGEM_HIBRIDA.md](README_ABORDAGEM_HIBRIDA.md)** - Documentacao tecnica da abordagem

---

## Requisitos Tecnicos

```
Python 3.8+
Flask 3.0.0
Pandas 2.1.3
NumPy 1.26.2
SciPy 1.11.4
Scikit-learn 1.3.2
Statsmodels 0.14.0
psycopg2-binary 2.9.9
openpyxl 3.1.2
```

---

## Contribuicao

Contribuicoes sao bem-vindas!

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudancas (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

---

## Licenca

Este projeto esta sob licenca MIT. Veja [LICENSE](LICENSE) para mais detalhes.

---

## Autores

- **Valter Lino** ([@valterlino01](https://github.com/valterlino01)) - Desenvolvedor Principal
- **Conrado Costa** ([@conradocosta0602](https://github.com/conradocosta0602)) - Co-desenvolvedor
- **Consultoria Tecnica:** Claude (Anthropic)

---

## Suporte

Para duvidas ou problemas:
- Consulte a documentacao completa
- Abra uma [issue](https://github.com/conradocosta0602/previsao-demanda/issues)
- Entre em contato via GitHub

---

## Features Planejadas

- [ ] API REST para integracao com ERP
- [ ] Dashboard Power BI
- [ ] Pedido CD -> Lojas integrado
- [ ] Transferencias automaticas
- [ ] Exportacao de graficos
- [ ] Modo batch para grandes volumes

---

**Versao:** 5.6
**Status:** Em Producao
**Ultima Atualizacao:** Fevereiro 2026

**Se este projeto foi util, considere dar uma estrela!**
