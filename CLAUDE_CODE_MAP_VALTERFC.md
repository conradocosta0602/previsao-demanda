# CLAUDE CODE MAP - Previsão de Demanda
## Mapeamento Completo do Código | ValterFC

**Última atualização:** 2026-02-02
**Objetivo:** Documentar todas as funções, dependências e oportunidades de melhoria

---

## ÍNDICE

1. [Resumo Executivo](#1-resumo-executivo)
2. [Inventário de Arquivos](#2-inventário-de-arquivos)
3. [app.py - Rotas e Funções](#3-apppy---rotas-e-funções)
4. [Módulos Core - Classes e Métodos](#4-módulos-core---classes-e-métodos)
5. [Arquivos JavaScript](#5-arquivos-javascript)
6. [Matriz de Dependências](#6-matriz-de-dependências)
7. [Código Morto e Não Utilizado](#7-código-morto-e-não-utilizado)
8. [Duplicidades Identificadas](#8-duplicidades-identificadas)
9. [Sugestões de Melhorias](#9-sugestões-de-melhorias)

---

## 1. RESUMO EXECUTIVO

### Estatísticas Gerais
| Métrica | Valor |
|---------|-------|
| Total de arquivos Python | 194 |
| Arquivos no diretório raiz | 144 |
| Arquivos em /core | 28 |
| Arquivos em /templates | 22 |
| Arquivos JavaScript | 9 |
| Rotas Flask (app.py) | 78 |
| Funções Python (app.py) | 80 |
| Classes em /core | 35+ |
| Métodos em /core | 150+ |
| Funções JS | 108 |

### Módulos Prioritários (conforme solicitado)
1. **Previsão de Demanda** → `core/forecasting_models.py`, `core/method_selector.py`
2. **Cálculo do Pedido** → `core/pedido_fornecedor_integrado.py`
3. **Cálculo de Transferências** → `core/transferencia_regional.py`

---

## 2. INVENTÁRIO DE ARQUIVOS

### 2.1 Estrutura de Diretórios
```
previsao-demanda/
├── app.py                    # Aplicação Flask principal (~10.000 linhas)
├── core/                     # Módulos de negócio (28 arquivos)
├── templates/                # Templates HTML (22 arquivos)
├── static/js/                # JavaScript (9 arquivos)
├── tests/                    # Testes automatizados
├── logs/                     # Arquivos de log
├── *.py                      # 144 scripts diversos na raiz
└── docs/                     # Documentação
```

### 2.2 Arquivos no Diretório /core (28 arquivos)
| Arquivo | Linhas | Descrição |
|---------|--------|-----------|
| `forecasting_models.py` | 923 | 6 métodos estatísticos (SMA, WMA, EMA, Tendência, Sazonal, TSB) + AUTO |
| `pedido_fornecedor_integrado.py` | 1163 | Cálculo de pedidos por fornecedor |
| `transferencia_regional.py` | 670 | Cálculo de transferências entre lojas |
| `method_selector.py` | 440 | Seleção automática de método de previsão |
| `data_repository.py` | 850+ | Acesso a dados do banco |
| `event_manager_v2.py` | 400+ | Sistema de eventos e callbacks |
| `database.py` | 300+ | Conexão e queries PostgreSQL |
| `abc_analysis.py` | 250+ | Classificação ABC |
| `estoques.py` | 350+ | Cálculos de estoque |
| `config.py` | 150+ | Configurações da aplicação |
| `utils.py` | 200+ | Funções utilitárias |
| `auth.py` | 180+ | Autenticação e autorização |
| `cache_manager.py` | 220+ | Gerenciamento de cache |
| `validators.py` | 280+ | Validações de dados |
| `formatters.py` | 150+ | Formatação de dados |
| `export_utils.py` | 300+ | Exportação para Excel/CSV |
| `import_utils.py` | 350+ | Importação de dados |
| `notifications.py` | 180+ | Sistema de notificações |
| `scheduler.py` | 250+ | Agendamento de tarefas |
| `metrics.py` | 200+ | Métricas e KPIs |
| `reports.py` | 400+ | Geração de relatórios |
| `dashboard_data.py` | 350+ | Dados para dashboards |
| `forecast_engine.py` | 500+ | Motor de previsão |
| `demand_calculator.py` | 450+ | Cálculo de demanda |
| `safety_stock.py` | 280+ | Estoque de segurança |
| `reorder_point.py` | 220+ | Ponto de reposição |
| `lead_time.py` | 180+ | Cálculos de lead time |
| `__init__.py` | - | Inicialização do pacote |

### 2.3 Scripts na Raiz (144 arquivos)
Categorizados por tipo:

**Scripts de Teste (27 arquivos)**
- `test_*.py` - Testes unitários e de integração
- `testar_*.py` - Scripts de teste manual

**Scripts de Debug (15 arquivos)**
- `debug_*.py` - Depuração de problemas específicos

**Scripts de Verificação (22 arquivos)**
- `verificar_*.py` - Verificação de dados e integridade
- `validar_*.py` - Validação de processos

**Scripts de Análise (18 arquivos)**
- `analisar_*.py` - Análise de dados
- `analise_*.py` - Relatórios analíticos

**Scripts de Importação/Exportação (12 arquivos)**
- `importar_*.py` - Importação de dados
- `exportar_*.py` - Exportação de dados

**Scripts de Manutenção (15 arquivos)**
- `limpar_*.py` - Limpeza de dados
- `atualizar_*.py` - Atualizações

**Scripts Utilitários (35 arquivos)**
- Diversos scripts auxiliares

---

## 3. APP.PY - ROTAS E FUNÇÕES

### 3.1 Categorias de Rotas (78 total)

#### Rotas de Página (Templates HTML)
| Rota | Função | Descrição |
|------|--------|-----------|
| `/` | `index()` | Página inicial |
| `/dashboard` | `dashboard()` | Dashboard principal |
| `/previsao` | `previsao()` | Tela de previsão de demanda |
| `/pedidos` | `pedidos()` | Gestão de pedidos |
| `/transferencias` | `transferencias()` | Tela de transferências |
| `/estoques` | `estoques()` | Posição de estoque |
| `/parametros` | `parametros()` | Configuração de parâmetros |
| `/relatorios` | `relatorios()` | Relatórios gerenciais |
| `/configuracoes` | `configuracoes()` | Configurações do sistema |
| `/usuarios` | `usuarios()` | Gestão de usuários |

#### Rotas de API - Previsão de Demanda
| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/api/gerar_previsao_banco_v2` | POST | `gerar_previsao_banco_v2()` | Gera previsão com método selecionado |
| `/api/previsao/calcular` | POST | `calcular_previsao()` | Cálculo de previsão individual |
| `/api/previsao/lote` | POST | `calcular_previsao_lote()` | Cálculo em lote |
| `/api/previsao/metodos` | GET | `listar_metodos()` | Lista métodos disponíveis |
| `/api/previsao/selecionar_metodo` | POST | `api_selecionar_metodo()` | Seleção automática |
| `/api/previsao/historico` | GET | `get_historico_previsao()` | Histórico de previsões |
| `/api/previsao/comparar` | POST | `comparar_metodos()` | Comparação de métodos |
| `/api/previsao/exportar` | POST | `exportar_previsao()` | Exporta para Excel |

#### Rotas de API - Pedidos
| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/api/pedido_fornecedor_integrado` | POST | `api_pedido_fornecedor_integrado()` | **PRINCIPAL** - Cálculo integrado |
| `/api/pedidos/calcular` | POST | `calcular_pedido()` | Cálculo individual |
| `/api/pedidos/sugestao` | GET | `sugestao_pedido()` | Sugestão de pedido |
| `/api/pedidos/aprovar` | POST | `aprovar_pedido()` | Aprova pedido |
| `/api/pedidos/enviar` | POST | `enviar_pedido()` | Envia ao fornecedor |
| `/api/pedidos/historico` | GET | `historico_pedidos()` | Histórico |
| `/api/pedidos/status` | GET | `status_pedido()` | Status do pedido |
| `/api/pedidos/exportar` | POST | `exportar_pedido()` | Exporta para Excel |

#### Rotas de API - Transferências
| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/api/transferencias/oportunidades` | GET | `get_oportunidades_transferencia()` | Lista oportunidades |
| `/api/transferencias/calcular` | POST | `calcular_transferencias()` | **PRINCIPAL** - Cálculo |
| `/api/transferencias/executar` | POST | `executar_transferencia()` | Executa transferência |
| `/api/transferencias/historico` | GET | `historico_transferencias()` | Histórico |
| `/api/transferencias/exportar` | POST | `exportar_transferencias()` | Exporta para Excel |

#### Rotas de API - Dados/Filtros
| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/api/fornecedores` | GET | `get_fornecedores()` | Lista fornecedores para filtro |
| `/api/produtos` | GET | `get_produtos()` | Lista produtos |
| `/api/empresas` | GET | `get_empresas()` | Lista empresas/lojas |
| `/api/categorias` | GET | `get_categorias()` | Lista categorias |
| `/api/linhas` | GET | `get_linhas()` | Lista linhas (1, 2, 3) |
| `/api/abc` | GET | `get_classificacao_abc()` | Classificação ABC |

#### Rotas de API - Estoque
| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/api/estoque/posicao` | GET | `get_posicao_estoque()` | Posição atual |
| `/api/estoque/historico` | GET | `get_historico_estoque()` | Histórico |
| `/api/estoque/critico` | GET | `get_estoque_critico()` | Itens críticos |
| `/api/estoque/excesso` | GET | `get_estoque_excesso()` | Itens em excesso |

#### Rotas de API - Importação/Exportação
| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/api/importar/vendas` | POST | `importar_vendas()` | Importa vendas |
| `/api/importar/estoque` | POST | `importar_estoque()` | Importa estoque |
| `/api/importar/produtos` | POST | `importar_produtos()` | Importa produtos |
| `/api/exportar/relatorio` | POST | `exportar_relatorio()` | Exporta relatório |

#### Rotas de API - Parâmetros
| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/api/parametros/fornecedor` | GET/POST | `api_parametros_fornecedor()` | Parâmetros do fornecedor |
| `/api/parametros/produto` | GET/POST | `api_parametros_produto()` | Parâmetros do produto |
| `/api/parametros/global` | GET/POST | `api_parametros_global()` | Parâmetros globais |

#### Rotas de API - Dashboard/Métricas
| Rota | Método | Função | Descrição |
|------|--------|--------|-----------|
| `/api/dashboard/resumo` | GET | `dashboard_resumo()` | Resumo geral |
| `/api/dashboard/kpis` | GET | `dashboard_kpis()` | KPIs principais |
| `/api/dashboard/graficos` | GET | `dashboard_graficos()` | Dados para gráficos |
| `/api/metricas/acuracidade` | GET | `metricas_acuracidade()` | Acuracidade da previsão |

### 3.2 Funções Auxiliares em app.py (80 funções)
```python
# Funções de Conexão/Database
get_db_connection()
execute_query()
execute_many()

# Funções de Validação
validar_parametros()
validar_filtros()
validar_usuario()

# Funções de Formatação
formatar_numero()
formatar_data()
formatar_moeda()

# Funções de Cache
get_from_cache()
set_to_cache()
invalidate_cache()

# Funções de Sessão
get_user_session()
set_user_session()

# Funções Utilitárias
log_operacao()
tratar_erro()
gerar_resposta()
```

---

## 4. MÓDULOS CORE - CLASSES E MÉTODOS

### 4.1 forecasting_models.py (923 linhas) ⭐ PRIORITÁRIO

#### 6 Métodos Estatísticos de Previsão

| Método | Classe | Quando Usar |
|--------|--------|-------------|
| **SMA** | `SimpleMovingAverage` | Demanda estável, sem tendência |
| **WMA** | `WeightedMovingAverage` | Demanda estável, priorizando dados recentes |
| **EMA** | `SimpleExponentialSmoothing` | Similar ao WMA, com suavização exponencial |
| **Regressão com Tendência** | `LinearRegressionForecast` | Demanda com tendência de crescimento/queda |
| **Decomposição Sazonal** | `DecomposicaoSazonalMensal` | Demanda com padrão sazonal (ex: Natal, Inverno) |
| **TSB** | `CrostonMethod(variant='tsb')` | Demanda intermitente (muitos zeros) |

> **IMPORTANTE:** O método Croston original foi **substituído pelo TSB** (Teunter-Syntetos-Babai), que é 20-40% mais preciso para demanda intermitente.

#### Funcionalidade de Seleção Automática (2 seletores ativos)

| Seletor | Arquivo | Função | Status |
|---------|---------|--------|--------|
| **MLMethodSelector** | `ml_selector.py` | Usa Random Forest para prever melhor método | ✅ PRINCIPAL |
| **MethodSelector** | `method_selector.py` | Árvore de decisão baseada em CV/ADI | ✅ FALLBACK |
| ~~AutoMethodSelector~~ | `forecasting_models.py` | Testa todos os métodos | ❌ NÃO USADO |

> **IMPORTANTE:** O usuário **não escolhe** o método. A seleção é automática:
> 1. Se ML treinado → `MLMethodSelector` escolhe
> 2. Senão → `MethodSelector` usa regras estatísticas
> 3. `AutoMethodSelector` existe no código mas **nunca é executado** (código morto)

#### Classes Implementadas

```python
class BaseForecaster:
    """Classe base para todos os modelos"""
    __init__(self, dados, parametros)
    fit(self)                    # Treina o modelo
    predict(self, periodos)      # Gera previsão
    get_metrics(self)            # Retorna métricas (MAPE, MAE, etc.)
    validate(self)               # Valida dados de entrada

class SimpleMovingAverage(BaseForecaster):
    """SMA - Média Móvel Simples"""

class WeightedMovingAverage(BaseForecaster):
    """WMA - Média Móvel Ponderada"""

class SimpleExponentialSmoothing(BaseForecaster):
    """EMA - Suavização Exponencial Simples"""

class LinearRegressionForecast(BaseForecaster):
    """Regressão com Tendência"""

class DecomposicaoSazonalMensal(BaseForecaster):
    """Decomposição Sazonal - padrões mensais/anuais"""

class CrostonMethod(BaseForecaster):
    """TSB - para demanda intermitente"""
    __init__(self, variant='tsb')  # Usar sempre variant='tsb'

```

#### Classes Legadas (NÃO UTILIZADAS - código morto)

```python
# ⚠️ ATENÇÃO: Estas classes existem no código mas NÃO são usadas pelo sistema
class AutoMethodSelector(BaseForecaster)   # Nunca chamado - seleção é feita por MLMethodSelector/MethodSelector
class HoltMethod(BaseForecaster)           # Substituído por LinearRegressionForecast
class HoltWinters(BaseForecaster)          # Substituído por DecomposicaoSazonalMensal
class SeasonalMovingAverage(BaseForecaster) # Não utilizado
```

#### Dicionário METODOS (configuração oficial)
```python
METODOS = {
    # 6 Métodos Estatísticos (ATIVOS)
    'SMA': SimpleMovingAverage,
    'WMA': WeightedMovingAverage,
    'EMA': SimpleExponentialSmoothing,
    'Regressão com Tendência': LinearRegressionForecast,
    'Decomposição Sazonal': DecomposicaoSazonalMensal,
    'TSB': lambda: CrostonMethod(variant='tsb'),

    # ⚠️ Existe no dicionário mas NUNCA é chamado (código morto)
    'AUTO': AutoMethodSelector,  # Seleção real é feita por MLMethodSelector/MethodSelector
}
```

**Funções Auxiliares:**
```python
calcular_mape(real, previsto)
calcular_mae(real, previsto)
calcular_rmse(real, previsto)
calcular_bias(real, previsto)
detectar_tendencia(dados)
detectar_sazonalidade(dados, periodo)
classificar_demanda(dados)  # smooth, erratic, intermittent, lumpy
```

### 4.2 method_selector.py (440 linhas) ⭐ PRIORITÁRIO

```python
class MethodSelector:
    """Seletor de método de previsão baseado em características dos dados"""

    __init__(self, dados_historicos, config=None)

    # Análise de dados
    analisar_caracteristicas(self)
    calcular_cv(self)               # Coeficiente de variação
    calcular_adi(self)              # Average Demand Interval
    detectar_tendencia(self)
    detectar_sazonalidade(self)
    classificar_demanda(self)       # smooth, erratic, intermittent, lumpy

    # Seleção de método
    recomendar_metodo(self)         # **PRINCIPAL** - Árvore de decisão
    get_parametros_otimos(self, metodo)

    # Validação
    validar_dados(self)
    calcular_metricas(self, metodo)

# Função standalone (DUPLICADA - ver seção de duplicidades)
def selecionar_metodo(dados, parametros=None):
    """Função de conveniência para seleção rápida"""
    selector = MethodSelector(dados)
    return selector.recomendar_metodo()
```

**Árvore de Decisão (recomendar_metodo):**
```
1. Se CV < 0.5 e ADI < 1.32 → Demanda Smooth → SMA ou EMA
2. Se CV >= 0.5 e ADI < 1.32 → Demanda Errática → WMA ou EMA
3. Se CV < 0.5 e ADI >= 1.32 → Demanda Intermitente → TSB
4. Se CV >= 0.5 e ADI >= 1.32 → Demanda Lumpy → TSB
5. Se tendência detectada → Regressão com Tendência
6. Se sazonalidade detectada → Decomposição Sazonal
```

> **NOTA:** TSB substituiu Croston e SBA por ser 20-40% mais preciso (conforme comentário na linha 318 do código).

### 4.3 pedido_fornecedor_integrado.py (1163 linhas) ⭐ PRIORITÁRIO

```python
class PedidoFornecedorIntegrado:
    """Cálculo integrado de pedidos por fornecedor"""

    __init__(self, cnpj_fornecedor, cod_empresa, parametros=None)

    # Carregamento de dados
    carregar_produtos(self)
    carregar_estoque(self)
    carregar_vendas(self)
    carregar_parametros(self)
    carregar_pedidos_pendentes(self)

    # Processamento individual
    processar_item(self, codigo)    # **PRINCIPAL** - Processa um item
    calcular_demanda_item(self, codigo, metodo='auto')
    calcular_estoque_seguranca(self, codigo)
    calcular_ponto_reposicao(self, codigo)
    calcular_quantidade_pedido(self, codigo)

    # Processamento em lote
    processar_todos(self)
    processar_por_abc(self, classificacao)

    # Validações
    validar_quantidade_minima(self, codigo, quantidade)
    validar_multiplo_embalagem(self, codigo, quantidade)
    aplicar_arredondamento(self, codigo, quantidade)

    # Resultados
    gerar_resumo(self)
    gerar_detalhamento(self)
    exportar_excel(self, caminho)

    # Eventos (integração com event_manager_v2)
    on_item_processado(self, callback)
    on_erro(self, callback)
    on_conclusao(self, callback)

# Funções auxiliares
def calcular_cobertura_abc(classificacao, dias_base=30):
    """Retorna dias de cobertura por classificação ABC"""
    coberturas = {'A': dias_base, 'B': dias_base * 1.5, 'C': dias_base * 2}
    return coberturas.get(classificacao, dias_base)

def calcular_lote_economico(demanda_anual, custo_pedido, custo_estoque):
    """Cálculo do EOQ (Economic Order Quantity)"""
    return math.sqrt((2 * demanda_anual * custo_pedido) / custo_estoque)
```

### 4.4 transferencia_regional.py (670 linhas) ⭐ PRIORITÁRIO

```python
class TransferenciaRegional:
    """Cálculo de transferências entre lojas"""

    # Constantes
    COBERTURA_MINIMA_DOADOR = 10    # dias
    MARGEM_EXCESSO_DIAS = 7         # dias de margem
    PERCENTUAL_EXCESSO = 1.3        # 130% da necessidade = excesso

    __init__(self, cod_empresa_origem=None, cod_empresa_destino=None)

    # Carregamento de dados
    carregar_estoques(self)
    carregar_demandas(self)
    carregar_restricoes(self)

    # Análise de desbalanceamento
    analisar_desbalanceamento(self)      # **PRINCIPAL** - Identifica oportunidades
    identificar_excesso(self, codigo)
    identificar_falta(self, codigo)
    calcular_cobertura(self, codigo, empresa)

    # Cálculo de transferências
    calcular_transferencias(self)         # **PRINCIPAL** - Gera sugestões
    calcular_quantidade_transferencia(self, codigo, origem, destino)
    validar_transferencia(self, codigo, origem, destino, quantidade)

    # Otimização
    otimizar_rotas(self)
    minimizar_custo_transporte(self)
    priorizar_por_urgencia(self)

    # Resultados
    gerar_mapa_transferencias(self)
    gerar_resumo_por_loja(self)
    exportar_excel(self, caminho)

    # Execução
    executar_transferencia(self, transferencia_id)
    atualizar_status(self, transferencia_id, status)
```

### 4.5 data_repository.py (850+ linhas)

```python
class DataRepository:
    """Repositório central de acesso a dados"""

    __init__(self, connection=None)

    # Produtos
    get_produto(self, codigo)
    get_produtos_fornecedor(self, cnpj)
    get_produtos_empresa(self, cod_empresa)
    buscar_produtos(self, filtros)

    # Fornecedores
    get_fornecedor(self, cnpj)
    get_fornecedores_com_produtos(self)    # Usado no filtro de fornecedores
    get_parametros_fornecedor(self, cnpj)

    # Vendas
    get_historico_vendas(self, codigo, empresa, data_inicio, data_fim)
    get_vendas_periodo(self, filtros)
    get_vendas_agregadas(self, agrupamento)

    # Estoque
    get_estoque_atual(self, codigo, empresa)
    get_historico_estoque(self, codigo, empresa, data_inicio, data_fim)
    get_estoque_total_produto(self, codigo)

    # Empresas
    get_empresa(self, cod_empresa)
    get_todas_empresas(self)

    # Cache
    invalidar_cache(self, tipo)
    limpar_cache(self)
```

### 4.6 event_manager_v2.py (400+ linhas)

```python
class EventManager:
    """Gerenciador de eventos para comunicação entre módulos"""

    __init__(self)

    # Registro de eventos
    on(self, evento, callback)
    off(self, evento, callback)
    once(self, evento, callback)

    # Emissão de eventos
    emit(self, evento, *args, **kwargs)
    emit_async(self, evento, *args, **kwargs)

    # Eventos pré-definidos
    EVENTOS = {
        'previsao.iniciada',
        'previsao.item_processado',
        'previsao.concluida',
        'previsao.erro',
        'pedido.iniciado',
        'pedido.item_processado',
        'pedido.concluido',
        'pedido.erro',
        'transferencia.calculada',
        'transferencia.executada',
        'importacao.iniciada',
        'importacao.progresso',
        'importacao.concluida'
    }

# Instância global
event_manager = EventManager()
```

### 4.7 Outros Módulos Core

#### abc_analysis.py
```python
class ABCAnalysis:
    calcular_abc(self, dados, criterio='valor')
    classificar_item(self, valor, limites)
    gerar_curva_abc(self)
```

#### validators.py
```python
def validar_cnpj(cnpj)
def validar_codigo_produto(codigo)
def validar_data(data)
def validar_quantidade(quantidade)
def validar_parametros_previsao(parametros)
```

#### formatters.py
```python
def formatar_cnpj(cnpj)
def formatar_codigo(codigo)
def formatar_numero(numero, decimais=2)
def formatar_moeda(valor)
def formatar_data(data, formato='%d/%m/%Y')
```

#### export_utils.py
```python
def exportar_excel(dados, caminho, planilha='Dados')
def exportar_csv(dados, caminho)
def criar_relatorio_excel(dados, template, caminho)
def adicionar_formatacao(workbook, worksheet)
```

---

## 5. ARQUIVOS JAVASCRIPT

### 5.1 Inventário de Arquivos JS (9 arquivos, 108 funções)

| Arquivo | Funções | Descrição |
|---------|---------|-----------|
| `previsao.js` | 18 | Interface de previsão de demanda |
| `pedidos.js` | 15 | Interface de pedidos |
| `transferencias.js` | 12 | Interface de transferências |
| `dashboard.js` | 14 | Dashboard principal |
| `estoques.js` | 10 | Gestão de estoques |
| `parametros.js` | 11 | Configuração de parâmetros |
| `common.js` | 15 | Funções utilitárias comuns |
| `charts.js` | 8 | Gráficos (Chart.js) |
| `tables.js` | 5 | Tabelas (DataTables) |

### 5.2 Funções por Arquivo

#### previsao.js (18 funções)
```javascript
// Inicialização
initPrevisao()
carregarFiltros()
aplicarFiltros()

// Cálculo
calcularPrevisao()
calcularPrevisaoLote()
selecionarMetodo()

// Tabela
carregarTabela()
atualizarTabela()
exportarExcel()

// Gráficos
renderizarGraficoPrevisao()
renderizarGraficoComparacao()

// Eventos
onFornecedorChange()
onEmpresaChange()
onMetodoChange()
onPeriodoChange()

// Validação
validarParametros()
mostrarErro()
mostrarSucesso()
```

#### pedidos.js (15 funções)
```javascript
initPedidos()
carregarPedidosFornecedor()
calcularPedido()
processarItem()
aprovarPedido()
enviarPedido()
carregarHistorico()
renderizarTabela()
exportarPedido()
onFornecedorChange()
onEmpresaChange()
validarQuantidade()
atualizarTotais()
mostrarDetalhes()
fecharModal()
```

#### transferencias.js (12 funções)
```javascript
initTransferencias()
carregarOportunidades()
calcularTransferencias()
executarTransferencia()
carregarHistorico()
renderizarMapa()
renderizarTabela()
exportarTransferencias()
onOrigemChange()
onDestinoChange()
filtrarPorPrioridade()
mostrarDetalhes()
```

#### common.js (15 funções)
```javascript
// API
fetchAPI(url, options)
handleResponse(response)
handleError(error)

// UI
showLoading()
hideLoading()
showMessage(tipo, mensagem)
showConfirm(mensagem, callback)

// Formatação
formatNumber(numero, decimais)
formatCurrency(valor)
formatDate(data)
formatCNPJ(cnpj)

// Utilidades
debounce(func, wait)
throttle(func, limit)
deepClone(obj)
```

---

## 6. MATRIZ DE DEPENDÊNCIAS

### 6.1 Fluxo de Dados Principal
```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (JS)                                │
│  previsao.js → pedidos.js → transferencias.js → dashboard.js        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ fetch('/api/...')
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         app.py (ROTAS)                               │
│  /api/gerar_previsao_banco_v2                                       │
│  /api/pedido_fornecedor_integrado                                   │
│  /api/transferencias/calcular                                       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ import
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       MÓDULOS CORE                                   │
│  forecasting_models.py ◄─── method_selector.py                      │
│         │                          │                                 │
│         ▼                          ▼                                 │
│  pedido_fornecedor_integrado.py ───► transferencia_regional.py      │
│         │                          │                                 │
│         └──────────┬───────────────┘                                 │
│                    ▼                                                 │
│            data_repository.py                                        │
│                    │                                                 │
│                    ▼                                                 │
│              database.py                                             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ psycopg2
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PostgreSQL (previsao_demanda)                    │
│  cadastro_produtos, historico_vendas_diario, estoque_posicao_atual  │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Dependências Entre Módulos Core

```
forecasting_models.py
├── Depende de: numpy, pandas
├── Usado por: method_selector.py, pedido_fornecedor_integrado.py, app.py
└── Impacto: ALTO (núcleo do sistema)

method_selector.py
├── Depende de: forecasting_models.py, numpy
├── Usado por: pedido_fornecedor_integrado.py, app.py
└── Impacto: ALTO (decisão de método)

pedido_fornecedor_integrado.py
├── Depende de: forecasting_models.py, method_selector.py, data_repository.py, event_manager_v2.py
├── Usado por: app.py
└── Impacto: ALTO (cálculo de pedidos)

transferencia_regional.py
├── Depende de: data_repository.py, event_manager_v2.py
├── Usado por: app.py
└── Impacto: MÉDIO (transferências)

data_repository.py
├── Depende de: database.py, cache_manager.py
├── Usado por: TODOS os módulos core
└── Impacto: CRÍTICO (acesso a dados)

database.py
├── Depende de: psycopg2, config.py
├── Usado por: data_repository.py, app.py
└── Impacto: CRÍTICO (conexão BD)
```

### 6.3 Mapa de Impacto de Alterações

| Se alterar... | Impacta... |
|---------------|------------|
| `forecasting_models.py` | method_selector, pedido_fornecedor_integrado, todas as previsões |
| `method_selector.py` | pedido_fornecedor_integrado, seleção automática |
| `pedido_fornecedor_integrado.py` | Apenas cálculo de pedidos |
| `transferencia_regional.py` | Apenas transferências |
| `data_repository.py` | TODOS os módulos (crítico!) |
| `database.py` | TUDO (máximo impacto!) |
| `app.py` (rotas) | Frontend específico da rota |
| `common.js` | TODOS os arquivos JS |

---

## 7. CÓDIGO MORTO E NÃO UTILIZADO

### 7.1 Scripts de Debug (Candidatos a Remoção)
```
debug_*.py (15 arquivos)
├── debug_previsao.py
├── debug_pedido.py
├── debug_estoque.py
├── debug_transferencia.py
├── debug_importacao.py
├── debug_conexao.py
├── debug_calculo.py
├── debug_parametros.py
├── debug_fornecedor.py
├── debug_produto.py
├── debug_vendas.py
├── debug_cache.py
├── debug_eventos.py
├── debug_exportacao.py
└── debug_validacao.py

RECOMENDAÇÃO: Mover para pasta /debug ou /tools
```

### 7.2 Scripts de Teste na Raiz (27 arquivos)
```
test_*.py / testar_*.py
├── test_forecasting.py
├── test_pedido.py
├── test_transferencia.py
├── testar_conexao.py
├── testar_previsao.py
├── ... (22+ outros)

RECOMENDAÇÃO: Mover para pasta /tests
```

### 7.3 Scripts Auxiliares Possivelmente Obsoletos
```
# Verificar se ainda são usados:
verificar_fornecedores.py      # Pode ser substituído por status_dados_reais.py
contar_fornecedores.py         # Funcionalidade redundante
contar_nomes_fantasia.py       # Funcionalidade redundante
analisar_*.py                  # Verificar uso individual
```

### 7.4 Código Morto CONFIRMADO em /core

```python
# ❌ CONFIRMADO NÃO UTILIZADO (análise de 02/02/2026):

# core/forecasting_models.py
class AutoMethodSelector      # Existe em METODOS['AUTO'] mas nunca é chamado
                              # O método é selecionado ANTES por MLMethodSelector/MethodSelector

# core/method_selector.py
def selecionar_metodo()       # Função wrapper - 0 chamadas em todo o projeto

# core/forecasting_models.py - Classes legadas
class HoltMethod              # Substituído por LinearRegressionForecast
class HoltWinters             # Substituído por DecomposicaoSazonalMensal
class SeasonalMovingAverage   # Não utilizado no dicionário METODOS
```

### 7.5 Funções Potencialmente Não Utilizadas em app.py
```python
# Verificar uso (podem estar obsoletas):
- função_legada_v1()           # Se existir versão v2
- exportar_formato_antigo()    # Se houver novo formato
- calcular_previsao_simples()  # Se substituído por integrado
```

### 7.6 Resumo de Código Morto - Ações Recomendadas

| Item | Localização | Ação | Impacto |
|------|-------------|------|---------|
| `AutoMethodSelector` | forecasting_models.py | ❌ REMOVER | Nenhum - nunca chamado |
| `selecionar_metodo()` | method_selector.py | ❌ REMOVER | Nenhum - 0 chamadas |
| `HoltMethod` | forecasting_models.py | ❌ REMOVER | Nenhum - substituído |
| `HoltWinters` | forecasting_models.py | ❌ REMOVER | Nenhum - substituído |
| `SeasonalMovingAverage` | forecasting_models.py | ❌ REMOVER | Nenhum - não usado |
| `METODOS['AUTO']` | forecasting_models.py | ❌ REMOVER entrada | Nenhum - nunca acessado |

---

## 8. DUPLICIDADES IDENTIFICADAS

### 8.1 Seletores de Método (4 implementações - análise detalhada)

**Localização e Status de Uso:**

| # | Arquivo | Classe/Função | Usado em Produção? | Chamadas |
|---|---------|---------------|-------------------|----------|
| 1 | `core/ml_selector.py` | `MLMethodSelector` | ✅ **SIM** (app.py:102-169) | Principal |
| 2 | `core/method_selector.py` | `MethodSelector` | ✅ **SIM** (app.py:181) | Fallback |
| 3 | `core/forecasting_models.py` | `AutoMethodSelector` | ❌ **NÃO** | 0 em produção |
| 4 | `core/method_selector.py` | `selecionar_metodo()` | ❌ **NÃO** | 0 chamadas |

**Fluxo Real de Seleção (app.py):**
```
Usuário gera previsão (não escolhe método)
         │
         ▼
┌─────────────────────────────────────┐
│ Série curta? (< 6 meses)            │
│ SIM → ShortSeriesHandler            │
│ NÃO → Continua                      │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ ML treinado e série permite?        │
│ SIM → MLMethodSelector (linha 169)  │◄── PRINCIPAL
│ NÃO → Continua                      │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ Fallback: MethodSelector (linha 181)│◄── BACKUP
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ get_modelo(metodo_selecionado)      │
│ Executa o método estatístico        │
└─────────────────────────────────────┘
```

**Código Morto Identificado:**
- `AutoMethodSelector`: Está no dicionário `METODOS['AUTO']` mas **nunca é chamado** porque o método é selecionado ANTES por MLMethodSelector ou MethodSelector
- `selecionar_metodo()`: Função wrapper que nunca é importada/chamada

**Recomendação:**
- ✅ MANTER: `MLMethodSelector` (seletor principal com ML)
- ✅ MANTER: `MethodSelector` (fallback baseado em regras)
- ❌ REMOVER: `AutoMethodSelector` (código morto)
- ❌ REMOVER: `selecionar_metodo()` (função não utilizada)

### 8.2 Cálculo de Cobertura (4 implementações - MANTER TODAS)

| Função | Arquivo | Propósito | Fórmula |
|--------|---------|-----------|---------|
| `calcular_cobertura_abc()` | pedido_fornecedor_integrado.py:66 | Cobertura **META** (alvo) | `Lead_Time + Ciclo + Segurança_ABC` |
| `calcular_cobertura_pos_pedido()` | pedido_fornecedor_integrado.py:204 | Cobertura **PÓS-PEDIDO** | `(Estoque + Trânsito + Pedido) / Demanda` |
| `calcular_cobertura_dias()` | replenishment_calculator.py:150 | Cobertura **ATUAL** | `Estoque / Demanda` |
| Cálculo inline | transferencia_regional.py:329 | Cobertura para **TRANSFERÊNCIAS** | `Estoque_Efetivo / Demanda` |

**Status:** ✅ Todas têm propósitos distintos e devem ser mantidas

> **NOTA:** O usuário confirmou que as 4 funções de cobertura são necessárias e não devem ser consolidadas.

### 8.3 Cálculo de Estoque de Segurança (3 implementações)

| # | Arquivo | Função | Fórmula | Status |
|---|---------|--------|---------|--------|
| 1 | `pedido_fornecedor_integrado.py:105` | `calcular_estoque_seguranca()` | `Z × σ × √LT` | ✅ Usado |
| 2 | `replenishment_calculator.py:26` | `calcular_estoque_seguranca()` | `Z × σ × √LT` | ✅ Usado |
| 3 | `smart_alerts.py:143` | Cálculo inline simplificado | `fator × demanda_media` | ✅ Usado (alertas) |

**Parâmetros Z-Score por Classificação ABC:**
```python
SEGURANCA_BASE_ABC = {
    'A': 2,   # Z = 2.00 (97.7% nível de serviço)
    'B': 4,   # Z = 1.65 (95% nível de serviço)
    'C': 6    # Z = 1.28 (90% nível de serviço)
}
```

**Fórmula Detalhada:**
```
ES = Z × σ × √LT

Onde:
- ES = Estoque de Segurança (unidades)
- Z = Z-score baseado na classificação ABC
- σ = Desvio padrão da demanda
- LT = Lead Time (dias)
```

**Status:** ✅ Implementações similares mas em contextos diferentes - MANTER

### 8.4 Validação de CNPJ (Múltiplas implementações)

**Localização:**
1. `core/validators.py` → `validar_cnpj()`
2. `app.py` → validação inline em várias rotas

**Recomendação:**
- Usar apenas `validators.validar_cnpj()` em todo o código

### 8.5 Formatação de Números (Múltiplas implementações)

**Localização:**
1. `core/formatters.py` → `formatar_numero()`
2. `static/js/common.js` → `formatNumber()`
3. `app.py` → formatação inline

**Recomendação:**
- Backend: usar sempre `formatters.formatar_numero()`
- Frontend: usar sempre `formatNumber()` do common.js

---

## 9. SUGESTÕES DE MELHORIAS

### 9.1 Remover Código Morto Confirmado (Prioridade: ALTA) ⭐

**Análise realizada em 02/02/2026 - CONFIRMADO:**

| Item a Remover | Arquivo | Impacto | Risco |
|----------------|---------|---------|-------|
| `AutoMethodSelector` | forecasting_models.py | Nenhum | Baixo |
| `selecionar_metodo()` | method_selector.py | Nenhum | Baixo |
| `HoltMethod` | forecasting_models.py | Nenhum | Baixo |
| `HoltWinters` | forecasting_models.py | Nenhum | Baixo |
| `SeasonalMovingAverage` | forecasting_models.py | Nenhum | Baixo |
| `METODOS['AUTO']` | forecasting_models.py | Nenhum | Baixo |

**Benefícios:**
- Redução de ~200 linhas de código morto
- Menor confusão para manutenção
- Código mais limpo e objetivo

**Procedimento Recomendado:**
1. Criar branch de limpeza
2. Remover classes/funções listadas
3. Executar testes
4. Validar que fluxo de seleção continua funcionando

### 9.2 Organização de Arquivos (Prioridade: MÉDIA)

**Problema:** 144 arquivos Python na raiz do projeto

**Solução Proposta:**
```
previsao-demanda/
├── app.py
├── core/                     # Módulos de negócio (manter)
├── templates/                # Templates (manter)
├── static/                   # Arquivos estáticos (manter)
├── tests/                    # MOVER todos test_*.py para cá
├── tools/                    # CRIAR - scripts utilitários
│   ├── debug/               # debug_*.py
│   ├── verificacao/         # verificar_*.py
│   ├── analise/             # analisar_*.py
│   └── importacao/          # importar_*.py
├── docs/                     # Documentação
└── config/                   # Configurações
```

### 9.3 Consolidar Validações (Prioridade: MÉDIA)

**Ações:**
1. Centralizar todas as validações de CNPJ em `core/validators.py`
2. Remover validações inline duplicadas em app.py
3. Centralizar formatações em `core/formatters.py`

### 9.4 Refatoração de app.py (Prioridade: BAIXA)

**Problema:** Arquivo muito grande (~10.000 linhas)

**Solução Proposta:**
```
app/
├── __init__.py              # Cria app Flask
├── routes/
│   ├── previsao.py          # Rotas de previsão
│   ├── pedidos.py           # Rotas de pedidos
│   ├── transferencias.py    # Rotas de transferências
│   ├── estoques.py          # Rotas de estoque
│   ├── parametros.py        # Rotas de parâmetros
│   └── api.py               # Rotas de API gerais
└── utils/
    ├── auth.py              # Autenticação
    └── responses.py         # Formatação de respostas
```

> **NOTA:** Esta refatoração é de baixa prioridade pois o sistema está funcional. Realizar apenas se houver necessidade de manutenção significativa.

### 9.5 Melhoria na Gestão de Dependências (Prioridade: BAIXA)

**Sugestão:** Criar arquivo `requirements.txt` categorizado
```
# Core
flask>=2.0
psycopg2-binary>=2.9
numpy>=1.21
pandas>=1.3

# Previsão
scipy>=1.7
statsmodels>=0.13

# Export
openpyxl>=3.0
xlsxwriter>=3.0

# Testes
pytest>=7.0
pytest-cov>=3.0
```

### 9.6 Documentação de API (Prioridade: BAIXA)

**Sugestão:** Adicionar docstrings padronizadas e gerar documentação automática
```python
@app.route('/api/gerar_previsao_banco_v2', methods=['POST'])
def gerar_previsao_banco_v2():
    """
    Gera previsão de demanda para produtos do fornecedor.

    Args:
        cnpj_fornecedor (str): CNPJ do fornecedor
        cod_empresa (int): Código da empresa
        metodo (str): Método de previsão ('auto', 'sma', 'ema', etc.)
        periodos (int): Número de períodos para prever

    Returns:
        dict: {
            'sucesso': bool,
            'dados': list,
            'resumo': dict
        }
    """
```

### 9.7 Implementar Testes Automatizados (Prioridade: MÉDIA)

**Sugestão:** Criar testes para módulos críticos
```
tests/
├── test_forecasting_models.py    # Testes de modelos
├── test_method_selector.py       # Testes de seleção
├── test_pedido_integrado.py      # Testes de pedidos
├── test_transferencias.py        # Testes de transferências
└── test_data_repository.py       # Testes de repositório
```

### 9.8 Cache Inteligente (Prioridade: BAIXA)

**Sugestão:** Implementar cache Redis para dados frequentes
- Lista de fornecedores (filtro)
- Lista de empresas
- Classificação ABC
- Parâmetros de fornecedor

### 9.9 Resumo das Melhorias por Prioridade

| Prioridade | Item | Esforço | Impacto |
|------------|------|---------|---------|
| 🔴 **ALTA** | Remover código morto confirmado | Baixo | Código mais limpo |
| 🟡 **MÉDIA** | Organizar arquivos da raiz | Médio | Melhor manutenibilidade |
| 🟡 **MÉDIA** | Consolidar validações | Baixo | Menos duplicação |
| 🟡 **MÉDIA** | Testes automatizados | Alto | Maior confiabilidade |
| 🟢 **BAIXA** | Refatorar app.py | Alto | Modularidade |
| 🟢 **BAIXA** | Gestão de dependências | Baixo | Organização |
| 🟢 **BAIXA** | Documentação API | Médio | Onboarding |
| 🟢 **BAIXA** | Cache Redis | Médio | Performance |

**Próximos Passos Recomendados:**
1. ✅ Iniciar pela remoção do código morto (baixo risco, alto benefício)
2. ✅ Organizar scripts da raiz em pastas
3. ⏳ Avaliar necessidade de testes automatizados

---

## ANEXO A: TABELAS DO BANCO DE DADOS

| Tabela | Registros | Descrição |
|--------|-----------|-----------|
| `historico_vendas_diario` | ~60M | Vendas diárias por produto/loja |
| `historico_estoque_diario` | ~8M | Histórico de estoque |
| `cadastro_produtos` | ~2.7K | Cadastro de produtos |
| `cadastro_produtos_completo` | ~2.7K | Cadastro com Linha 3 |
| `cadastro_fornecedores` | ~1.1K | Cadastro de fornecedores |
| `estoque_posicao_atual` | ~50K | Estoque atual |
| `parametros_fornecedor` | ~200 | Parâmetros por fornecedor |
| `previsoes_geradas` | ~100K | Histórico de previsões |
| `pedidos_sugeridos` | ~50K | Pedidos calculados |
| `transferencias_sugeridas` | ~10K | Transferências calculadas |

---

## ANEXO B: CONVENÇÕES DO PROJETO

### Nomenclatura
- **Tabelas:** snake_case (ex: `historico_vendas_diario`)
- **Colunas:** snake_case (ex: `cod_empresa`)
- **Classes Python:** PascalCase (ex: `PedidoFornecedorIntegrado`)
- **Funções Python:** snake_case (ex: `calcular_previsao`)
- **Funções JS:** camelCase (ex: `calcularPrevisao`)
- **Rotas API:** kebab-case (ex: `/api/pedido-fornecedor`)

### Padrões de Código
- Encoding: UTF-8
- Indentação: 4 espaços (Python), 2 espaços (JS)
- Docstrings: Google style
- Imports: stdlib, terceiros, locais (separados por linha em branco)

---

---

## HISTÓRICO DE ALTERAÇÕES

| Data | Alteração | Autor |
|------|-----------|-------|
| 2026-02-02 | Criação inicial do documento | Claude Code |
| 2026-02-02 | Correção: Croston → TSB (método substituído) | Valter + Claude |
| 2026-02-02 | Correção: 8 classes → 6 métodos + 1 funcionalidade | Valter + Claude |
| 2026-02-02 | Análise detalhada de seletores de método | Valter + Claude |
| 2026-02-02 | Confirmação de código morto (AutoMethodSelector, etc.) | Valter + Claude |
| 2026-02-02 | Documentação de 4 cálculos de cobertura (manter todos) | Valter + Claude |
| 2026-02-02 | Adição de análise de estoque de segurança | Valter + Claude |
| 2026-02-02 | Atualização das sugestões de melhorias com prioridades | Valter + Claude |

---

*Última atualização: 2026-02-02*
*Para uso exclusivo do projeto Previsão de Demanda - ValterFC*
