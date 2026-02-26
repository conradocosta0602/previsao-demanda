# CLAUDE.md - Guia de Contexto para IA

Este arquivo serve como "memoria" para assistentes de IA (Claude, etc.) entenderem rapidamente o projeto.

## Visao Geral

**Sistema de Demanda e Reabastecimento v6.18** - Sistema de previsao de demanda e gestao de pedidos para varejo multi-loja com Centro de Distribuicao (CD).

**Stack**: Python 3.8+, Flask, PostgreSQL 15+, Pandas, NumPy, SciPy

**Porta padrao**: 5001

## Estrutura de Pastas Principais

```
previsao-demanda/
├── app.py                    # App Flask principal (~4500 linhas)
├── app/
│   ├── blueprints/           # Rotas organizadas por modulo
│   │   ├── previsao.py       # API de previsao de demanda
│   │   ├── pedido_fornecedor.py  # API de pedido integrado
│   │   ├── demanda_job.py    # API de demanda pre-calculada
│   │   └── validacao.py      # API de checklist de conformidade
│   └── utils/
│       ├── db_connection.py  # Conexao PostgreSQL
│       └── demanda_pre_calculada.py  # Funcoes de demanda
├── core/                     # Logica de negocio
│   ├── demand_calculator.py  # Calculadora de demanda (6 metodos)
│   ├── pedido_fornecedor_integrado.py  # Processador de pedidos
│   ├── validador_conformidade.py  # Checklist de metodologia
│   └── event_manager_v2.py   # Eventos/promocoes
├── jobs/                     # Cronjobs
│   ├── calcular_demanda_diaria.py  # Cronjob 05:00 - demanda
│   └── checklist_diario.py   # Cronjob 06:00 - validacao
├── database/                 # Migrations SQL
├── static/js/app.js          # JavaScript frontend
└── templates/                # Templates HTML (Jinja2)
```

## Modulos Principais

### 1. Previsao de Demanda (Bottom-Up V2)

**Arquivo principal**: `core/demand_calculator.py`

**6 metodos estatisticos**:
- SMA (Simple Moving Average)
- WMA (Weighted Moving Average)
- EMA (Exponential Moving Average)
- Tendencia (Regressao Linear)
- Sazonal (Decomposicao)
- TSB (Demanda Intermitente)

**Limitadores**:
- Queda > 40% → limitada a -40%
- Alta > 50% → limitada a +50%
- Fator YoY: 0.7 a 1.4

### 2. Pedido ao Fornecedor

**Arquivo principal**: `core/pedido_fornecedor_integrado.py`

**Formula de cobertura**:
```
Lead Time Base = Lead Time Fornecedor + Transit Time CD (se centralizado)
Lead Time Efetivo = Lead Time Base + Delay Operacional (5d)
Cobertura = Lead Time Efetivo + Ciclo (7d) + Seguranca ABC
```

**Transit Time CD->Loja** (v6.18): Para pedidos centralizados (destino CD),
o transit time (parametro `dias_transferencia_padrao_compra`, default 10 dias)
e somado ao lead time do fornecedor no **backend**, incorporando-se ao calculo
de cobertura que desconta estoque existente. Antes era adicionado no frontend
como `demanda × dias`, o que inflava pedidos.

**Delay Operacional**: 5 dias adicionados ao lead time para compensar
tempo entre calculo do pedido e envio ao fornecedor (aprovacoes, consolidacao).

**Seguranca por curva**:
- A: +2 dias (Z=2.05, NS=98%)
- B: +4 dias (Z=1.65, NS=95%)
- C: +6 dias (Z=1.28, NS=90%)

**Estoque de Seguranca** (v6.8):
```
ES = Z × Sigma × sqrt(Lead Time Base)
```
- **Lead Time Base**: Lead time do fornecedor SEM delay operacional
- O delay operacional e para cobertura logistica, nao para variabilidade de demanda
- **Rateio do desvio**: Quando demanda consolidada e rateada por loja, o desvio usa sqrt()
  - Demanda: `demanda * proporcao_loja`
  - Desvio: `desvio * sqrt(proporcao_loja)` (propriedade estatistica da variancia)

**Limitador de Cobertura 90 dias (TSB)** (v6.12):
- Aplica-se APENAS a itens com metodo TSB (demanda intermitente)
- Se cobertura pos-pedido > 90 dias na loja, reduz quantidade do pedido
- Quantidade maxima: `COBERTURA_MAXIMA_POS_PEDIDO * demanda_diaria - estoque_efetivo`
- Arredonda para BAIXO no multiplo de caixa (para nao ultrapassar 90 dias)
- Garante minimo de 1 caixa APENAS quando cobertura atual < 90 dias
- Se cobertura atual >= 90 dias, pedido = 0 (estoque ja suficiente)
- Constante: `COBERTURA_MAXIMA_POS_PEDIDO = 90`

**Situacoes que BLOQUEIAM pedido automatico**:
- NC (Nao Comprar)
- FL (Fora de Linha)
- EN (Encomenda)

**Situacoes que PERMITEM pedido automatico**:
- ATIVO (item normal)
- CO (Compra Oportunidade)
- FF (Falta no Fornecedor) - fornecedor pode regularizar

### 3. Demanda Pre-Calculada

**Cronjob**: `jobs/calcular_demanda_diaria.py` (05:00)

**Tabela**: `demanda_pre_calculada`

Garante consistencia entre Tela de Demanda e Pedido Fornecedor.

### 4. Sistema de Validacao

**Arquivo**: `core/validador_conformidade.py`

**Cronjob**: `jobs/checklist_diario.py` (06:00)

**29 verificacoes** de conformidade com a metodologia documentada:
- V01-V12: Verificacoes de calculo de demanda e pedido
- V13: Logica Hibrida de Transferencias entre Lojas
- V14: Rateio Proporcional de Demanda Multi-Loja
- V20: Arredondamento Inteligente para Multiplo de Caixa
- V26: Limitador de Cobertura 90 dias para itens TSB
- V27: Completude de dados de embalagem por fornecedor
- V29: Distribuicao de estoque do CD para lojas (DRP)
- V30: Verificacao de estoque CD para pedidos direto loja
- V31: Bloqueio de itens sem vendas ha 12+ meses por loja
- V32: Rateio proporcional zero para lojas sem vendas historicas
- V33: Transit time CD->loja no backend (em vez de frontend)
- V34: Fair Share Allocation na distribuicao do CD
- V35: Semantica correta de qtd_pend_transf no CD

### 5. Transferencias entre Lojas (V13/V25)

**Logica Otimizada v6.11** para transferencias entre filiais:

**Regras de Identificacao**:
- **Doador**: cobertura_atual > 90 dias (COBERTURA_MINIMA_DOADOR = 90)
- **Receptor**: cobertura_atual <= 90 dias E quantidade_pedido > 0
- **Restricao**: Apenas entre lojas do MESMO grupo regional (V24)

**Quantidade Transferivel**:
```
excesso_dias = cobertura_atual - 90
qtd_bruta = excesso_dias × demanda_diaria
qtd_transferir = (qtd_bruta // multiplo_embalagem) * multiplo_embalagem  # Arredonda BAIXO
```

**Faixas de Prioridade (Receptores)**:
| Faixa | Cobertura | Prioridade | Recebe Primeiro? |
|-------|-----------|------------|------------------|
| RUPTURA | estoque = 0 | 0 | Sim (maxima) |
| CRITICA | 0-30 dias | 1 | Segunda |
| ALTA | 31-60 dias | 2 | Terceira |
| MEDIA | 61-90 dias | 3 | Quarta |
| > 90 dias | - | NAO RECEBE | Pode ser doadora |

**Algoritmo de Matching Otimizado**:
- Preferir 1 doador → 1 receptor (consolidar frete)
- Buscar doador que cobre 100% da necessidade antes de fragmentar
- Doadores ordenados por excesso (maior primeiro)
- Receptores ordenados por prioridade (ruptura primeiro)

**Restricoes Adicionais**:
- Transferencia apenas em multiplos de embalagem (caixas fechadas)
- Mesma loja nao pode ser doadora e receptora do mesmo item
- Grupos regionais: PE/PB/RN (lojas 1,2,4,6,7,8) e BA/SE (lojas 3,5,9)

**Badges na Tela de Pedido**:
Quando ha oportunidades de transferencia, o sistema exibe badges visuais na tela de Pedido ao Fornecedor:

| Badge | Cor | Significado |
|-------|-----|-------------|
| `Enviar X un` | Laranja | Loja pode enviar X unidades para outra |
| `Receber X un` | Verde | Loja vai receber X unidades de outra |

**Comportamento**:
- Badges aparecem ao lado de cada item/loja
- Ao receber transferencia, o `quantidade_pedido` e REDUZIDO automaticamente
- **Apos transferencia, quantidade e ARREDONDADA para multiplo de caixa** (funcao `arredondar_para_multiplo`)
- Se transferencia cobre toda a necessidade, `quantidade_pedido = 0`
- Transferencias sao salvas na tabela `oportunidades_transferencia`

**Arredondamento Pos-Transferencia** (v6.7):
```python
from core.pedido_fornecedor_integrado import arredondar_para_multiplo

# Exemplo: Pedido original 84 un, transferencia -29 un, multiplo 12
nova_qtd = max(0, 84 - 29)  # = 55
nova_qtd = arredondar_para_multiplo(55, 12, 'cima')  # = 60 (5 caixas)
```

**Importante**: As sugestoes de transferencia sao recalculadas a cada execucao do pedido. Dados antigos (>24h) sao automaticamente limpos.

### 5b. Distribuicao de Estoque do CD para Lojas (V29/V30)

**Arquivos**: `app/blueprints/pedido_fornecedor.py`, `core/pedido_fornecedor_integrado.py`

O sistema distribui estoque do CD para lojas com falta, reduzindo o pedido ao fornecedor.
Roda **ANTES** das transferencias loja<->loja (V25) — estoque no CD e improdutivo, prioriza-se esvaziá-lo.

**V30**: A verificacao de estoque do CD funciona para **todos os padroes de compra** (centralizado E direto loja). Mesmo fornecedores com padrao direto loja podem ter estoque nos CDs (negociacoes comerciais, compras de oportunidade).

**Fluxo Completo**:
```
1. Calcular pedido por LOJA (demanda rateada)
2. ETAPA 2: Distribuicao CD->LOJAS (V29/V30) - CD primeiro
3. ETAPA 3: Transferencias LOJA<->LOJA (V25, se multiloja) - lojas depois
4. Pedido = Sum(pedidos residuais)
```

**Deteccao de CDs**:
- **Modo centralizado** (`is_destino_cd`): mapeia todos itens ao CD destino selecionado
- **Modo direto loja** (V30): consulta `estoque_posicao_atual WHERE cod_empresa >= 80 AND estoque > 0`
- Suporta **multiplos CDs** (80, 81, 82, etc.) - cada item mapeado ao seu CD especifico
- Dict `cd_por_item`: {codigo_item: cod_cd}

**Estoque de Seguranca do CD (Risk Pooling)**:
```
sigma_total = sqrt(sum(sigma_loja^2))   # Chopra & Meindl, 2019
ES_cd = Z × sigma_total × sqrt(LT_fornecedor)
```
- Funcao: `calcular_es_pooling_cd()` em `core/pedido_fornecedor_integrado.py`
- Reducao tipica: ~65% vs soma dos ES individuais
- Usa `desvio_padrao_diario` de cada loja e `lead_time_usado` (LT base, sem delay)
- **Pedido centralizado** (`is_destino_cd`): ES pooling **desativado** — CD e ponto de passagem,
  prioridade e abastecer lojas; fornecedor repoe o CD. Todo estoque CD e distribuivel.
- **Pedido direto loja** (V30): ES pooling **ativo** — CD precisa manter reserva

**Distribuicao**:
- CD como "super-doador" sem restricao de grupo regional
- Distribui para lojas que tem pedido > 0
- Prioridade: RUPTURA > CRITICA > ALTA > MEDIA (mesma logica V25)
- Caixa fechada: arredonda para BAIXO (nao envia caixa incompleta)
- Pedido residual re-arredondado para CIMA (multiplo de caixa)
- Estoque distribuivel = estoque_CD - ES_pooling_CD

**Persistencia**:
- Transferencias CD->lojas sao salvas em `oportunidades_transferencia` (mesma tabela V25)
- Origem identificada como `loja_origem >= 80` (CD MDC, CD OBC, etc.)
- Aparecem na tela de transferencias e no arquivo Excel de exportacao

**Badge na Tela**:
- Badge verde `CD X un` quando loja recebe distribuicao do CD
- Exibido na visualizacao "Por Padrao de Compra (Destino)"

### 6. Rateio Proporcional de Demanda (V14)

**Arquivos**: `app/utils/demanda_pre_calculada.py`, `app/blueprints/pedido_fornecedor.py`, `app/blueprints/pedido_planejado.py`

Quando demanda e calculada de forma consolidada e precisa ser distribuida entre lojas, o sistema usa **rateio proporcional** baseado no historico de vendas de cada loja.

**Formula**:
```
proporcao_loja = vendas_loja / vendas_total
demanda_loja = demanda_consolidada × proporcao_loja
```

**Funcao principal**: `calcular_proporcoes_vendas_por_loja()`

**Metodos de Rateio**:
- **Proporcional**: Quando ha historico de vendas (usa ultimos 365 dias)
- **Proporcional Zero** (V32): Loja sem vendas recebe demanda=0 quando outras lojas tem proporcao
- **Uniforme**: Fallback quando NENHUMA loja tem historico (demanda / num_lojas)

**V32 - Protecao contra rateio uniforme indevido**:
Quando um item tem proporcoes calculadas para algumas lojas (soma=100%), lojas sem vendas
nao devem receber rateio uniforme (1/N), pois isso inflaria a demanda total acima de 100%.
O sistema forca `proporcao_loja=0.0` para essas lojas, resultando em demanda zero.

**Beneficios**:
- Demanda reflete perfil real de vendas de cada loja
- Evita excesso em lojas de baixo giro
- Reducao de rupturas em lojas de alto giro
- Proporcao visivel no tooltip da interface
- Evita inflacao de demanda total por rateio uniforme indevido (V32)

**Verificacao V14**: Valida calculo de proporcoes, soma = 1.0, e preservacao do total.

### 7. Filtro de Itens Bloqueados EN/FL (V16)

**Arquivos**: `jobs/calcular_demanda_diaria.py`, `app/blueprints/previsao.py`

Itens com situacao de compra **EN (Em Negociacao)** ou **FL (Fora de Linha)** sao automaticamente excluidos do calculo de demanda.

**Comportamento**:
- Itens bloqueados **nao** tem demanda calculada
- Itens bloqueados **aparecem** na tabela detalhada com:
  - Demanda = 0
  - Metodo = "BLOQUEADO"
  - Coluna "Situacao" mostrando EN ou FL

**Filtro por Loja**:
- O filtro verifica a situacao de compra **por loja especifica**
- Um item pode estar FL em uma loja e ATIVO em outra
- Apenas itens bloqueados em **TODAS** as lojas sao ignorados no cronjob

**Funcoes adicionadas**:
```python
# jobs/calcular_demanda_diaria.py
buscar_itens_bloqueados(conn, cnpj_fornecedor) -> Dict[int, set]
buscar_total_lojas(conn) -> int
```

**Situacoes de Compra**:
| Codigo | Descricao | Calcula Demanda? |
|--------|-----------|------------------|
| ATIVO  | Item ativo | Sim |
| NC     | Nao comprado | Sim |
| EN     | Em Negociacao | **Nao** |
| FL     | Fora de Linha | **Nao** |
| CO     | Compra obrigatoria | Sim |
| FF     | Fora de fabricacao | Sim |

### 8. Arredondamento Inteligente de Pedidos (V19)

**Arquivo**: `core/pedido_fornecedor_integrado.py`

O sistema usa **arredondamento inteligente** para multiplos de caixa, evitando excesso de estoque quando a necessidade e muito inferior ao multiplo.

**Problema Resolvido**:
- Necessidade: 2 unidades, Caixa: 12 unidades
- Arredondamento tradicional: pediria 12 (excesso de 10 unidades = 500%)
- Arredondamento inteligente: nao pede agora, aguarda proximo ciclo

**Logica Hibrida**:
```
1. Se fracao >= 50% do multiplo → arredonda para CIMA (regra padrao literatura)
2. Se fracao < 50%:
   - Calcula se estoque aguenta ate proximo ciclo (com 20% margem)
   - Se aguenta → NAO arredonda (deixa para proximo ciclo)
   - Se nao aguenta → arredonda para CIMA (evita ruptura)
```

**Constantes**:
```python
PERCENTUAL_MINIMO_ARREDONDAMENTO = 0.50  # 50% - padrao literatura
MARGEM_SEGURANCA_PROXIMO_CICLO = 1.20    # 20% margem de seguranca
```

**Referencias**: Silver, Pyke & Peterson (2017), APICS, SAP, Oracle

**Campos Retornados**:
- `arredondamento_decisao`: Motivo da decisao (multiplo_exato, fracao_acima_minimo, risco_ruptura_proximo_ciclo, sem_risco_proximo_ciclo)
- `fracao_caixa`: Fracao da caixa necessaria (0.0 a 1.0)
- `arredondou_para_cima`: Se arredondou ou nao

**Decisoes Possiveis**:
| Decisao | Descricao |
|---------|-----------|
| multiplo_exato | Necessidade e multiplo exato da caixa |
| fracao_acima_minimo | Fracao >= 50%, arredonda para cima |
| risco_ruptura_proximo_ciclo | Fracao < 50% mas ha risco, arredonda |
| sem_risco_proximo_ciclo | Fracao < 50% e sem risco, nao arredonda |
| minimo_1_caixa | Garante minimo de 1 caixa quando necessario |

### 9. Dashboard de KPIs (V15)

**Arquivos**: `app/blueprints/kpis.py`, `static/js/kpis.js`, `templates/kpis.html`

Dashboard para monitoramento de indicadores de performance do sistema.

**KPIs Disponiveis**:
- **Ruptura**: % de pontos de abastecimento sem estoque (meta: < 5%)
- **Cobertura Ponderada**: Dias de cobertura de estoque (meta: 30 dias)
- **WMAPE**: Erro percentual ponderado da previsao (meta: < 20%)

**Definicoes**:
- **Item Ativo para Ruptura**: NAO esta em NC, FL, CO ou EN na situacao de compra
- **FF (Falta Fornecedor)**: INCLUIDO na ruptura (problema externo mas afeta cliente)
- **Ponto de Abastecimento**: Item ativo × Loja × Dia
- **Ruptura**: Pontos sem estoque / Total pontos × 100

**Filtros**:
- Por filial, fornecedor, categoria e linha
- Periodo configuravel
- Granularidade: diaria, semanal ou mensal

**Graficos**:
- Evolucao temporal de Ruptura e Cobertura
- Linha de meta para referencia

### 10. Relatorio de Itens Bloqueados na Exportacao

**Arquivo**: `app/blueprints/pedido_fornecedor.py`

O relatorio de exportacao de pedido ao fornecedor agora inclui **aba separada** para itens bloqueados por situacao de compra.

**Abas do Excel Exportado**:
1. **Resumo**: Estatisticas gerais + contagem por situacao de bloqueio
2. **Itens Pedido**: Itens com pedido calculado (formato original)
3. **Itens Bloqueados**: Itens que NAO tiveram pedido calculado

**Colunas da Aba "Itens Bloqueados"**:
| Coluna | Descricao |
|--------|-----------|
| Cod Filial | Codigo da loja |
| Nome Filial | Nome da loja |
| Cod Item | Codigo do produto |
| Descricao Item | Descricao do produto |
| Nome Fornecedor | Fornecedor do item |
| Situacao | Codigo da situacao (FL, NC, EN, etc.) |
| Motivo Bloqueio | Descricao do motivo |
| Estoque Atual | Estoque atual na loja |

**Motivos de Bloqueio**:
| Situacao | Motivo |
|----------|--------|
| FL | Fora de Linha - Item descontinuado |
| NC | Nao Comprar - Bloqueado para compras |
| EN | Encomenda - Apenas sob demanda |
| FF | Falta no Fornecedor |
| CO | Compra Oportunidade |

**Beneficios**:
- Visibilidade completa dos itens nao calculados
- Identificacao rapida de itens a serem ajustados
- Auditoria de por que certos itens nao tem pedido
- Contagem por situacao no resumo

### 11. Scripts de Importacao de Dados

**Pasta**: Raiz do projeto

Scripts utilitarios para importacao de dados de fornecedores a partir de arquivos CSV exportados do Soprano (sistema legado).

**Scripts Disponiveis**:

| Script | Descricao |
|--------|-----------|
| `importar_soprano.py` | Importacao completa do fornecedor Soprano |
| `importar_cadastros.py` | Importacao generica de cadastros |
| `importar_demanda_geral.py` | Importacao de demanda historica |

**Uso Tipico**:
```bash
# Importar dados do fornecedor
python importar_soprano.py

# Apos importar, recalcular demanda para todos
python jobs/calcular_demanda_diaria.py --manual
```

**Arquivos CSV Esperados** (padrao Soprano):
- `Cadastro de Fornecedores_[Nome]_[Data].csv` - Parametros do fornecedor
- `Cadastro de Produtos_[Nome]_[Data].csv` - Produtos e categorias
- `Embalagem_[Nome]_[Data].csv` - Multiplos de embalagem
- `Relatorio de Posicao de Estoque_[Nome]_[Data].csv` - Estoque atual
- `demanda_[Nome]_[Ano].csv` - Historico de vendas diarias

**Tabelas Atualizadas**:
- `parametros_fornecedor` - Lead time, ciclo, pedido minimo
- `cadastro_produtos_completo` - Produtos e categorias
- `embalagem_arredondamento` - Multiplos de caixa
- `estoque_posicao_atual` - Posicao de estoque
- `historico_vendas_diario_XXXX` - Vendas por ano (particionada)

**Importante**: Apos importar dados, sempre executar o job de recalculo de demanda para atualizar a tabela `demanda_pre_calculada`.

### 12. Tabela de Custo (CUE) na Tela de Demanda (V28)

**Arquivos**: `app/blueprints/previsao.py`, `static/js/app.js`, `templates/index.html`

Tabela espelhada abaixo da tabela de quantidade na Tela de Demanda, exibindo valores em R$ (quantidade x CUE).

**CUE (Custo Unitario de Estoque)**:
- Armazenado em `estoque_posicao_atual.cue` por item x loja
- Para dados multi-loja: **media ponderada pelo estoque** (`SUM(cue * estoque) / SUM(estoque)`)
- Se estoque = 0 em todas as lojas: usa `MAX(cue)` como fallback

**Comportamento**:
- Tabela de custo (cabecalho azul) aparece abaixo da tabela de quantidade (cabecalho verde)
- Valores = previsao_periodo x CUE unitario do item
- **Somente leitura** - nao ha edicao direta na tabela de custo
- Ajustes manuais na tabela de quantidade refletem automaticamente na tabela de custo
- Celulas ajustadas ficam amarelas em ambas as tabelas
- Itens sem CUE mostram "-" nos valores

**Excel Exportado**:
- Aba "Relatorio Detalhado": tabela de quantidade + coluna CUE unitario
- Aba "Custo (CUE)": tabela espelhada com valores em R$

**Ordenacao**: Ambas as tabelas ordenam itens por codigo decrescente (maior para menor).

## APIs Importantes

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/gerar_previsao_banco` | POST | Gera previsao de demanda |
| `/api/pedido_fornecedor_integrado` | POST | Calcula pedido |
| `/api/demanda_job/recalcular` | POST | Recalcula demanda |
| `/api/demanda_job/status/<cnpj>` | GET | Status do job |
| `/api/validacao/executar-checklist` | POST | Executa validacao |
| `/api/kpis/dashboard` | GET | Dashboard de KPIs |
| `/api/kpis/evolucao` | GET | Evolucao temporal dos KPIs |
| `/api/kpis/ranking` | GET | Ranking de itens por ruptura |

## Tabelas Principais

### Tabelas de Historico (Particionadas por Ano)
- `historico_vendas_diario` - Vendas por dia/loja/produto (particionada: _2023, _2024, _2025, _2026)
- `historico_estoque_diario` - Estoque diario por loja/produto (particionada)

### Tabelas de Cadastro
- `cadastro_produtos_completo` - Cadastro principal de produtos (3.576 itens)
- `cadastro_fornecedores` - Fornecedor x Loja (1.110 CNPJs unicos)
- `cadastro_lojas` - 16 lojas
- `embalagem_arredondamento` - Qtd por embalagem para arredondamento de pedidos

### Tabelas de Demanda
- `demanda_pre_calculada` - Demanda calculada pelo cronjob
- `demanda_validada` - Demanda aprovada pelo usuario
- `demanda_calculo_execucao` - Log de execucoes

### Tabelas de Estoque
- `estoque_posicao_atual` - Posicao atual de estoque por loja
- `situacao_compra_itens` - Status de compra por item/loja (NC, FL, CO, EN, FF)

### Tabelas de Auditoria
- `auditoria_conformidade` - Log de validacoes do checklist

### Notas sobre Estrutura
- **Particionamento**: Tabelas de historico sao particionadas por ano para performance
- **codigo vs cod_produto**: `codigo` e INTEGER, `cod_produto` e VARCHAR - JOINs usam CAST
- **cadastro_produtos**: Tabela legada - usar `cadastro_produtos_completo` no sistema atual
- **embalagem**: Tabela removida em v6.1 - usar apenas `embalagem_arredondamento`

## Padroes de Codigo

### Cache e Performance

O sistema usa caches para evitar queries repetidas:

```python
# Em PedidoFornecedorIntegrado
self._cache_produtos = None
self._cache_estoque = None
self._cache_historico = None

def precarregar_produtos(self, codigos):
    # Carrega todos de uma vez
```

### Conexao com Banco

```python
from app.utils.db_connection import get_db_connection
conn = get_db_connection()
# usar conn
conn.close()
```

### Variaveis de Ambiente

Credenciais em `.env`:
```
DB_HOST=localhost
DB_NAME=demanda_reabastecimento
DB_USER=postgres
DB_PASSWORD=...
DB_PORT=5432
```

## Decisoes Tecnicas Importantes

1. **ABC > CV**: Nao usamos Coeficiente de Variacao porque os 6 metodos ja capturam variabilidade

2. **Normalizacao por dias totais**: Dividir vendas pelo total de dias (730), nao apenas dias com venda

3. **Saneamento de rupturas**: Limiar de 50% de cobertura de dados de estoque

4. **Demanda pre-calculada**: Cronjob diario garante mesmos valores em todas as telas

5. **Fator YoY**: Corrige subestimacao em fornecedores com crescimento historico

6. **Rateio proporcional**: Em pedidos multi-loja, demanda e distribuida proporcional ao historico de vendas. Desvio padrao usa sqrt() da proporcao (v6.8)

7. **Demanda sazonal no pedido** (v6.9): O calculo de pedido usa `demanda_prevista / 30` (demanda mensal COM sazonalidade) em vez de `demanda_diaria_base` (media anual SEM sazonalidade). Isso garante que o pedido reflita a demanda real do mes, considerando picos e vales sazonais.

8. **Tabelas legadas**: `cadastro_produtos` e `embalagem` sao legadas - usar `cadastro_produtos_completo` e `embalagem_arredondamento`

9. **Tipos padronizados**: `codigo` e `cod_empresa` devem ser INTEGER em todo o sistema

10. **Delay operacional**: 5 dias adicionados ao lead time para compensar tempo entre calculo e envio do pedido

11. **Arredondamento inteligente**: Multiplo de caixa usa 50% como threshold (Silver, Pyke & Peterson) com verificacao de risco de ruptura

## Fluxo de Trabalho Tipico

```
1. Usuario acessa Tela de Demanda (/index)
2. Seleciona fornecedor, periodo
3. Sistema usa demanda pre-calculada (ou calcula em tempo real)
4. Usuario pode salvar demanda (botao "Salvar Demanda")
5. Usuario acessa Pedido Fornecedor (/pedido_fornecedor_integrado)
6. Sistema usa demanda salva para calcular pedido
7. Exporta Excel com itens a pedir
```

## Problemas Comuns e Solucoes

### Status "Processando" nao atualiza para "Concluido"

**Causa**: Backend salva `status='sucesso'` mas frontend esperava `status='concluido'`

**Solucao**: `demanda_job.py` aceita 'sucesso', 'parcial', 'concluido' como estados finais

### Calculo de pedido lento

**Causa**: Queries individuais para cada produto

**Solucao**: `precarregar_produtos()` carrega todos de uma vez

### Previsao muito alta ou baixa

**Causas possiveis**:
- Dados de ruptura nao saneados
- Fator sazonal extremo
- Tendencia nao limitada

**Verificar**: Executar checklist de conformidade (`/api/validacao/executar-checklist`)

## Commits Recentes Relevantes

- `97341c7` - feat(pedido): adicionar delay operacional de 5 dias ao lead time (v6.4)
- `e2d9886` - fix(pedido): permitir pedido automatico para itens FF (v6.3)
- `4de6895` - fix(kpis): incluir itens FF na medicao de ruptura (v6.3)
- `f4a59da` - feat(demanda): filtrar itens EN/FL do calculo de demanda (v6.2)
- `51ab4e4` - feat(database): migrations para KPIs e indices de ruptura
- `9c0c1ff` - perf(kpis): otimizar queries de ruptura com filtro de itens abastecidos
- `79d174f` - feat(demanda): suporte a multiplos fornecedores no Salvar Demanda + timeout 10min
- `e7d55ec` - perf: cache de produtos e EventManager reutilizavel
- Sistema de Validacao de Conformidade (v5.6)
- Fator de Tendencia YoY (v5.7)
- V13: Logica Hibrida de Transferencias (v5.8)
- V14: Rateio Proporcional de Demanda Multi-Loja (v5.9)
- V15: Dashboard de KPIs (Ruptura, Cobertura, WMAPE) (v6.0)
- Migration V13: Otimizacao do banco - remocao de tabelas legadas, padronizacao de tipos, indices (v6.1)
- V16: Filtro de Itens Bloqueados EN/FL (v6.2)
- V17: Itens FF incluidos em ruptura e pedido (v6.3)
- V18: Delay operacional de 5 dias no lead time (v6.4)
- V19: Arredondamento inteligente de pedidos para multiplo de caixa (v6.5)
- V20: Scripts de importacao de dados Soprano + badges de transferencia (v6.6)
- V21: Arredondamento pos-transferencia + importacao padrao de compra (v6.7)
- V22: Correcao do calculo de Estoque de Seguranca - rateio de desvio usa sqrt() e ES usa LT sem delay (v6.8)
- V23: Correcao demanda sazonal no pedido - usar demanda_prevista/30 em vez de demanda_diaria_base (v6.9)
- V24: Transferencias respeitam grupos regionais - PE/PB/RN (lojas 1,2,4,6,7,8) e BA/SE (lojas 3,5,9) (v6.10)
- V25: Transferencias otimizadas - doador >90d, faixas prioridade, multiplo embalagem, matching 1:1 (v6.11)
- V26: Limitador de cobertura 90 dias para itens TSB - evita excesso em demanda intermitente (v6.12)
- V27: Completude de dados de embalagem - alerta fornecedores sem multiplo de caixa cadastrado (v6.12)
- V28: Tabela de Custo (CUE) na Tela de Demanda - tabela espelhada em R$ + coluna CUE no Excel (v6.13)
- V29: Distribuicao de estoque CD para lojas - DRP multiplos CDs, caixa fechada, sem ES pooling para centralizado (v6.14)
- V30: Verificacao de estoque CD para pedidos direto loja - CD distribui antes de V25, salva em oportunidades_transferencia (v6.16)
- V31: Bloqueio de itens sem vendas ha 12+ meses por loja - evita reposicao de itens obsoletos localmente (v6.16)
- V32: Rateio proporcional zero - lojas sem vendas recebem demanda 0 em vez de rateio uniforme (v6.17)
- V33: Transit time CD->loja no backend - incorporado ao lead time em vez de ajuste no frontend (v6.18)
- V34: Fair Share Allocation na distribuicao do CD - proporcional por faixa em vez de sequencial (v6.18)
- V35: Semantica qtd_pend_transf no CD - subtrair do estoque (mercadoria comprometida) em vez de somar (v6.18)

## Documentacao Complementar

- [README.md](README.md) - Documentacao completa
- [REVISAO_MODELO_PREVISAO_2026.md](REVISAO_MODELO_PREVISAO_2026.md) - Revisao do modelo
- [docs/PEDIDO_FORNECEDOR_INTEGRADO.md](docs/PEDIDO_FORNECEDOR_INTEGRADO.md) - Pedido multi-loja
- [docs/TRANSFERENCIAS_ENTRE_LOJAS.md](docs/TRANSFERENCIAS_ENTRE_LOJAS.md) - Transferencias

## Contato

- **Desenvolvedor**: Valter Lino
- **Repositorio**: github.com/conradocosta0602/previsao-demanda

---

**Ultima atualizacao**: Fevereiro 2026 (v6.18)
