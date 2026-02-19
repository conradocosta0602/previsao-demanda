# CLAUDE.md - Guia de Contexto para IA

Este arquivo serve como "memoria" para assistentes de IA (Claude, etc.) entenderem rapidamente o projeto.

## Visao Geral

**Sistema de Demanda e Reabastecimento v6.10** - Sistema de previsao de demanda e gestao de pedidos para varejo multi-loja com Centro de Distribuicao (CD).

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
Lead Time Efetivo = Lead Time Fornecedor + Delay Operacional (5d)
Cobertura = Lead Time Efetivo + Ciclo (7d) + Seguranca ABC
```

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

**15 verificacoes** de conformidade com a metodologia documentada:
- V01-V12: Verificacoes de calculo de demanda e pedido
- V13: Logica Hibrida de Transferencias entre Lojas
- V14: Rateio Proporcional de Demanda Multi-Loja
- V20: Arredondamento Inteligente para Multiplo de Caixa

### 5. Transferencias entre Lojas (V13)

**Logica Hibrida** para transferencias entre filiais:

```
Cobertura Alvo = cobertura_dias (se informado) OU cobertura_necessaria_dias (default ABC)
```

**Regras de Identificacao**:
- **Doador**: cobertura_atual > cobertura_alvo (MARGEM_EXCESSO = 0)
- **Receptor**: quantidade_pedido > 0

**Quantidade Transferivel**:
```
excesso_em_dias = cobertura_atual - cobertura_alvo
qtd_transferivel = excesso_em_dias × demanda_diaria
```

**Niveis de Urgencia**:
- **CRITICA**: cobertura < 50% do alvo
- **ALTA**: cobertura < 75% do alvo
- **MEDIA**: cobertura < 100% do alvo
- **BAIXA**: demais casos

**Restricao**: Mesma loja nao pode ser doadora e receptora do mesmo item.

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
- **Uniforme**: Fallback quando nao ha historico (demanda / num_lojas)

**Beneficios**:
- Demanda reflete perfil real de vendas de cada loja
- Evita excesso em lojas de baixo giro
- Reducao de rupturas em lojas de alto giro
- Proporcao visivel no tooltip da interface

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

## Documentacao Complementar

- [README.md](README.md) - Documentacao completa
- [REVISAO_MODELO_PREVISAO_2026.md](REVISAO_MODELO_PREVISAO_2026.md) - Revisao do modelo
- [docs/PEDIDO_FORNECEDOR_INTEGRADO.md](docs/PEDIDO_FORNECEDOR_INTEGRADO.md) - Pedido multi-loja
- [docs/TRANSFERENCIAS_ENTRE_LOJAS.md](docs/TRANSFERENCIAS_ENTRE_LOJAS.md) - Transferencias

## Contato

- **Desenvolvedor**: Valter Lino
- **Repositorio**: github.com/conradocosta0602/previsao-demanda

---

**Ultima atualizacao**: Fevereiro 2026 (v6.10)
