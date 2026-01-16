# Sistema de Demanda e Reabastecimento v5.0

Sistema completo para gestão de estoque multi-loja com Centro de Distribuição (CD), combinando previsão de demanda Bottom-Up com política de estoque baseada em curva ABC.

**Novidades v5.0:**
- Pedido Multi-Loja com layout hierarquico (Fornecedor > Loja > Itens)
- Transferencias inteligentes entre lojas do mesmo grupo regional
- Parametros de fornecedor (Lead Time, Ciclo, Faturamento Minimo)
- Graceful degradation para novas tabelas

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
8. [Estrutura do Projeto](#-estrutura-do-projeto)
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
- Limitadores de tendencia (queda >40% ignorada, alta >50% limitada)
- Sazonalidade anual (12 meses ou 52 semanas)
- Deteccao automatica de outliers (IQR + Z-Score)

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
| **Transferencias entre Lojas** | Balanceamento automatico de estoque | **Novo v5.0** |
| **Parametros Fornecedor** | Lead Time, Ciclo, Faturamento Minimo | **Novo v5.0** |
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
| Queda | > 40% | Tendencia ignorada |
| Alta | > 50% | Limitada a 50% |

**Exemplo:**
- Historico: 100 un/mes
- Tendencia detectada: -60% (queda)
- Resultado: Tendencia ignorada, previsao mantem 100 un/mes

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
|   |-- pedido_fornecedor_integrado.py  # NOVO - Calculo de pedidos ABC
|   |-- auto_logger.py                  # Logging automatico
|   |-- smart_alerts.py                 # Alertas inteligentes
|   |-- event_manager.py                # Gerenciador de eventos
|   |-- scenario_simulator.py           # Simulador de cenarios
|   |-- replenishment_calculator.py     # Calculos de reabastecimento
|   +-- flow_processor.py               # Processador de fluxos
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

### v5.0 (Janeiro 2026) - ATUAL

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
R: Quedas >40% sao ignoradas (protecao contra dados anomalos). Altas >50% sao limitadas a 50% (protecao contra otimismo excessivo).

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

**Versao:** 5.0
**Status:** Em Producao
**Ultima Atualizacao:** Janeiro 2026

**Se este projeto foi util, considere dar uma estrela!**
