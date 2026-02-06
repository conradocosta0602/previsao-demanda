# CLAUDE.md - Guia de Contexto para IA

Este arquivo serve como "memoria" para assistentes de IA (Claude, etc.) entenderem rapidamente o projeto.

## Visao Geral

**Sistema de Demanda e Reabastecimento v5.8** - Sistema de previsao de demanda e gestao de pedidos para varejo multi-loja com Centro de Distribuicao (CD).

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
Cobertura = Lead Time + Ciclo (7d) + Seguranca ABC
```

**Seguranca por curva**:
- A: +2 dias (Z=2.05, NS=98%)
- B: +4 dias (Z=1.65, NS=95%)
- C: +6 dias (Z=1.28, NS=90%)

**Estoque de Seguranca**:
```
ES = Z × Sigma × sqrt(Lead Time)
```

### 3. Demanda Pre-Calculada

**Cronjob**: `jobs/calcular_demanda_diaria.py` (05:00)

**Tabela**: `demanda_pre_calculada`

Garante consistencia entre Tela de Demanda e Pedido Fornecedor.

### 4. Sistema de Validacao

**Arquivo**: `core/validador_conformidade.py`

**Cronjob**: `jobs/checklist_diario.py` (06:00)

**13 verificacoes** de conformidade com a metodologia documentada:
- V01-V12: Verificacoes de calculo de demanda e pedido
- V13: Logica Hibrida de Transferencias entre Lojas

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

## APIs Importantes

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/gerar_previsao_banco` | POST | Gera previsao de demanda |
| `/api/pedido_fornecedor_integrado` | POST | Calcula pedido |
| `/api/demanda_job/recalcular` | POST | Recalcula demanda |
| `/api/demanda_job/status/<cnpj>` | GET | Status do job |
| `/api/validacao/executar-checklist` | POST | Executa validacao |

## Tabelas Principais

- `historico_vendas_diario` - Vendas por dia/loja/produto
- `cadastro_produtos_completo` - Cadastro de produtos
- `estoque_atual` - Posicao de estoque
- `demanda_pre_calculada` - Demanda calculada pelo cronjob
- `demanda_calculo_execucao` - Log de execucoes
- `auditoria_conformidade` - Log de validacoes

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

- `e7d55ec` - perf: cache de produtos e EventManager reutilizavel
- `71e15ec` - fix: deteccao de conclusao do job Salvar Demanda
- Sistema de Validacao de Conformidade (v5.6)
- Fator de Tendencia YoY (v5.7)
- V13: Logica Hibrida de Transferencias (v5.8)

## Documentacao Complementar

- [README.md](README.md) - Documentacao completa
- [REVISAO_MODELO_PREVISAO_2026.md](REVISAO_MODELO_PREVISAO_2026.md) - Revisao do modelo
- [docs/PEDIDO_FORNECEDOR_INTEGRADO.md](docs/PEDIDO_FORNECEDOR_INTEGRADO.md) - Pedido multi-loja
- [docs/TRANSFERENCIAS_ENTRE_LOJAS.md](docs/TRANSFERENCIAS_ENTRE_LOJAS.md) - Transferencias

## Contato

- **Desenvolvedor**: Valter Lino
- **Repositorio**: github.com/conradocosta0602/previsao-demanda

---

**Ultima atualizacao**: Fevereiro 2026 (v5.8)
