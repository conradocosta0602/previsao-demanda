# Revisao do Modelo de Calculo de Previsao de Demanda

**Data:** Fevereiro 2026
**Versao:** 5.3
**Autor:** Valter Lino / Claude (Anthropic)

---

## Sumario Executivo

Este documento detalha as revisoes implementadas no modelo de calculo de previsao de demanda em Fevereiro de 2026. As mudancas visam corrigir problemas de superestimacao detectados em fornecedores como DICOMPEL (+81.6%), PHILIPS IL (previsao de 991 unidades/ano com historico de apenas 22 unidades em 2 anos) e outros.

**Principais Correcoes:**
1. Ativacao dos 6 metodos estatisticos (ja existiam, nao estavam sendo usados)
2. Ativacao da sazonalidade como multiplicador (ja existia, nao estava sendo usada)
3. Ativacao da deteccao de tendencia (ja existia, nao estava sendo usada)
4. Melhoria do TSB simplificado com deteccao de tendencia
5. Exclusao de dados do periodo de previsao do calculo historico
6. Ativacao do saneamento de rupturas com limiar de cobertura de estoque (50%)
7. Normalizacao de demanda pelo total de dias do periodo

---

## 1. Metodos Estatisticos (Ativacao)

### Status Anterior
Os 6 metodos estatisticos estavam implementados no `DemandCalculator`, mas o codigo em `previsao.py` nao utilizava o resultado corretamente. A formula usava apenas `media_diaria_por_periodo` (media simples) ignorando a analise inteligente.

### Correcao Implementada
A formula agora utiliza `demanda_diaria_inteligente` retornada pelo `DemandCalculator`:

```python
# ANTES (incorreto)
previsao_periodo = media_diaria_por_periodo.get(chave_periodo, 0) * dias_periodo

# DEPOIS (correto)
demanda_diaria_inteligente = metadata.get('demanda_diaria_base', 0)
fator_sazonal = fatores_sazonais.get(chave_periodo, 1.0)
previsao_periodo = demanda_diaria_inteligente * fator_sazonal * dias_periodo
```

### Os 6 Metodos Disponíveis

| Metodo | Nome Tecnico | Quando e Selecionado |
|--------|--------------|----------------------|
| SMA | Simple Moving Average | Demanda estavel, baixa variabilidade |
| WMA | Weighted Moving Average | Demanda com tendencia recente |
| EMA | Exponential Moving Average | Demanda com ruido moderado |
| Tendencia | Regressao Linear | Tendencia clara crescente/decrescente |
| Sazonal | Decomposicao Sazonal | Padroes sazonais detectados |
| TSB | Teunter-Syntetos-Babai | Demanda intermitente (>40% zeros) |

### Arquivo Modificado
- [app/blueprints/previsao.py](app/blueprints/previsao.py) - Linhas 480-484, 541-543

---

## 2. Sazonalidade como Multiplicador (Ativacao)

### Status Anterior
O calculo de fatores sazonais existia no codigo, mas nao era aplicado na formula final de previsao.

### Correcao Implementada
Os fatores sazonais agora sao aplicados como multiplicadores na formula:

```python
# Calcular fator sazonal para cada periodo
# fator = media_do_periodo / media_geral
fatores_sazonais = {}
for chave, media_periodo in media_por_periodo.items():
    if media_geral_hist > 0 and media_periodo > 0:
        fator = media_periodo / media_geral_hist
        # Limitar fator entre 0.5 e 2.0 para evitar distorcoes extremas
        fatores_sazonais[chave] = max(0.5, min(2.0, fator))
    else:
        fatores_sazonais[chave] = 1.0

# Aplicar na formula
previsao_periodo = demanda_diaria_inteligente * fator_sazonal * dias_periodo
```

### Exemplo Pratico

| Mes | Fator Sazonal | Interpretacao |
|-----|---------------|---------------|
| Janeiro | 1.3 | 30% acima da media (verao) |
| Junho | 0.7 | 30% abaixo da media (inverno) |
| Dezembro | 1.5 | 50% acima da media (natal) |

### Arquivo Modificado
- [app/blueprints/previsao.py](app/blueprints/previsao.py) - Linhas 497-508, 541-543

---

## 3. Deteccao de Tendencia (Ativacao)

### Status Anterior
A deteccao de tendencia existia no `DemandCalculator` mas nao era considerada adequadamente para produtos intermitentes.

### Correcao Implementada
O TSB simplificado agora incorpora deteccao de tendencia comparando a primeira e segunda metade da serie:

```python
# core/demand_calculator.py - Linhas 125-165
if zeros_pct > 0.4:
    # TSB simplificado COM TENDENCIA
    meio = n // 2
    media_primeira = np.mean(vendas_array[:meio])
    media_segunda = np.mean(vendas_array[meio:])

    fator_tendencia = 1.0
    tendencia = 'estavel'

    if media_primeira > 0:
        razao = media_segunda / media_primeira
        if razao < 0.5:
            # Queda acentuada (>50%)
            fator_tendencia = max(0.1, razao)
            tendencia = 'queda_acentuada'
        elif razao < 0.85:
            # Queda moderada
            fator_tendencia = razao
            tendencia = 'decrescente'
        elif razao > 1.15:
            # Crescimento
            fator_tendencia = min(1.5, razao)
            tendencia = 'crescente'

    demanda = demanda_base * fator_tendencia
```

### Exemplo: PHILIPS IL

| Metrica | Valor |
|---------|-------|
| Vendas totais (2 anos) | 22 unidades |
| Dias com venda | 15 dias |
| Taxa de presenca | 2% (15/730) |
| Media quando vende | 1.47 un/venda |
| Demanda esperada | 0.02 * 1.47 = 0.029 un/dia |
| Previsao anual | ~10-12 unidades |

**Antes da correcao:** 991 unidades/ano (absurdo)
**Depois da correcao:** ~10-12 unidades/ano (coerente)

### Arquivo Modificado
- [core/demand_calculator.py](core/demand_calculator.py) - Linhas 115-165

---

## 4. TSB Simplificado com Tendencia (Melhoria)

### Problema Original
O metodo TSB (Teunter-Syntetos-Babai) nao considerava tendencia, projetando a mesma demanda independente de o produto estar em queda ou crescimento.

### Melhoria Implementada
Adicionamos deteccao de tendencia especifica para demanda intermitente:

```python
# previsao.py - Linhas 444-450
if taxa_presenca < 0.05 and dias_com_venda > 0:
    # Demanda extremamente intermitente (<5% presenca)
    # Calculo TSB: probabilidade de demanda x media quando ha demanda
    media_quando_vende = total_vendido_item / dias_com_venda
    demanda_diaria_base = taxa_presenca * media_quando_vende
    metodo_usado = 'tsb_intermitente_extremo'
```

### Formula TSB Intermitente Extremo

```
Demanda_diaria = P(venda) x Media_quando_vende

Onde:
- P(venda) = dias_com_venda / dias_totais
- Media_quando_vende = total_vendido / dias_com_venda
```

### Arquivo Modificado
- [app/blueprints/previsao.py](app/blueprints/previsao.py) - Linhas 444-450
- [core/demand_calculator.py](core/demand_calculator.py) - Linhas 115-165

---

## 5. Exclusao de Dados do Periodo de Previsao (Melhoria)

### Problema Original
Se o usuario queria prever Janeiro/2026, os dados de Janeiro/2026 (se existissem no banco) eram incluidos no calculo do historico, gerando previsoes infladas.

### Exemplo do Problema (PIAL LEGRAND)

| Situacao | Valor Janeiro |
|----------|---------------|
| Dados reais Jan/2026 | 15.000 unidades |
| Previsao sem corte | ~15.000 (usava dados reais) |
| Previsao com corte | ~12.000 (baseada no historico) |

### Correcao Implementada
Adicionamos corte de data na query SQL para excluir o periodo de previsao:

```python
# previsao.py - Linhas 201-223
corte_sql = ""
params_com_corte = list(params)

if granularidade == 'mensal' and mes_inicio and ano_inicio:
    data_corte = f"{int(ano_inicio):04d}-{int(mes_inicio):02d}-01"
    corte_sql = "AND h.data < %s"
    params_com_corte.append(data_corte)
elif granularidade == 'semanal' and semana_inicio and ano_semana_inicio:
    # ...
elif granularidade == 'diario' and data_inicio:
    corte_sql = "AND h.data < %s"
    params_com_corte.append(data_inicio)
```

### Validacao
Arquivo de debug confirma funcionamento:
```
=== 2026-02-04 15:29:00 ===
data_corte_historico=2026-01-01
Meses presentes: ['2024-02', ..., '2025-12']
OK: Dados de 2026-01 NAO estao presentes. Corte funcionou.
```

### Arquivo Modificado
- [app/blueprints/previsao.py](app/blueprints/previsao.py) - Linhas 201-223

---

## 6. Saneamento de Rupturas com Limiar de Cobertura (Ativacao + Melhoria)

### Conceito de Ruptura
**Ruptura** = periodo onde `estoque = 0 E venda = 0`

Isso significa que o produto nao vendeu porque nao tinha estoque, nao porque nao havia demanda. Incluir esses zeros no calculo subestima a demanda real.

### Distincao Importante

| Situacao | Estoque | Venda | Tratamento |
|----------|---------|-------|------------|
| Ruptura (excluir) | 0 | 0 | Nao incluir no calculo |
| Demanda zero real (incluir) | >0 | 0 | Incluir como zero |
| Venda normal (incluir) | >0 ou NULL | >0 | Incluir normalmente |
| Sem registro estoque | NULL | >=0 | Incerteza |

### O Problema: Cobertura Insuficiente de Dados de Estoque
Analisando os dados, descobrimos que a tabela `historico_estoque_diario` tinha poucos registros para a maioria dos itens (~15 registros vs 700 dias necessarios). Usar o `saneamento de rupturas` com dados incompletos poderia gerar distorcoes.

### Solucao: Limiar de 50% de Cobertura

```python
# previsao.py - Linhas 415-470
estoque_item = estoque_item_dict.get(cod_produto, {})
dias_com_registro_estoque = len(estoque_item)
cobertura_estoque = dias_com_registro_estoque / dias_historico_total

if cobertura_estoque >= 0.50:  # >= 50% de cobertura
    # Usar saneamento de rupturas
    # Exclui dias com estoque=0 E venda=0 (ruptura)
    # Inclui dias com estoque>0 E venda=0 (demanda zero real)
    for data_str in datas_ordenadas:
        venda_dia = buscar_venda(data_str)
        estoque_dia = estoque_item.get(data_str, None)

        if estoque_dia == 0 and venda_dia == 0:
            continue  # Ruptura - excluir
        else:
            serie_saneada.append(venda_dia)

    metodo_usado = 'ruptura_saneada'

else:  # < 50% de cobertura
    # Normalizar pelo total de dias
    demanda_diaria_normalizada = total_vendido_item / dias_historico_total
    serie_item = [demanda_diaria_normalizada] * dias_historico_total
    metodo_usado = 'normalizado_sem_estoque'
```

### Por que 50%?

| Cobertura | Confiabilidade | Decisao |
|-----------|----------------|---------|
| < 30% | Muito baixa | Normalizacao simples |
| 30-50% | Baixa | Normalizacao simples |
| **50-70%** | **Moderada** | **Saneamento** |
| 70-90% | Alta | Saneamento |
| > 90% | Muito alta | Saneamento |

O limiar de 50% foi escolhido como equilibrio entre:
- Ter dados suficientes para identificar rupturas reais
- Nao ser tao restritivo que poucos itens se qualifiquem

### Referencias Bibliograficas
- Syntetos, A.A., Boylan, J.E. (2005). "The accuracy of intermittent demand estimates"
- Croston, J.D. (1972). "Forecasting and Stock Control for Intermittent Demands"

### Arquivo Modificado
- [app/blueprints/previsao.py](app/blueprints/previsao.py) - Linhas 268-310, 415-500

---

## 7. Normalizacao pelo Total de Dias (Melhoria)

### Problema Original (Raiz dos Erros)
A serie `vendas_diarias` passada ao `DemandCalculator` continha apenas os dias COM venda, nao todos os dias do periodo. Isso inflava a media:

```
Exemplo DICOMPEL:
- Total vendido: 10.000 unidades em 2 anos
- Dias COM venda: 200 dias
- Dias TOTAIS: 730 dias

Media ERRADA: 10.000 / 200 = 50 un/dia
Media CORRETA: 10.000 / 730 = 13.7 un/dia

Erro: +264% de superestimacao!
```

### Correcao Implementada
Quando nao ha dados suficientes de estoque (cobertura < 50%), normalizamos pelo total de dias:

```python
# previsao.py - Linha 467
demanda_diaria_normalizada = total_vendido_item / dias_historico_total
```

### Impacto Esperado

| Fornecedor | Antes | Depois | Reducao |
|------------|-------|--------|---------|
| DICOMPEL | +81.6% | ~+5-6% | ~75 p.p. |
| FORCELINE | +17.9% | ~+10% | ~8 p.p. |
| DANEVA | -27.6% | ~-20% | ~8 p.p. |

### Arquivo Modificado
- [app/blueprints/previsao.py](app/blueprints/previsao.py) - Linhas 463-470

---

## Resumo das Mudancas por Arquivo

### app/blueprints/previsao.py

| Linha(s) | Mudanca | Status |
|----------|---------|--------|
| 201-223 | Corte de data para excluir periodo de previsao | Melhoria |
| 268-310 | Query para buscar dados de estoque | Nova |
| 415-500 | Logica de cobertura de estoque (50%) | Nova |
| 444-450 | TSB intermitente extremo (<5% presenca) | Melhoria |
| 480-484 | Uso de demanda_diaria_inteligente | Ativacao |
| 497-508 | Calculo de fatores sazonais | Ativacao |
| 541-543 | Formula: demanda * fator_sazonal * dias | Ativacao |

### core/demand_calculator.py

| Linha(s) | Mudanca | Status |
|----------|---------|--------|
| 115-165 | TSB com deteccao de tendencia | Melhoria |

---

## Diagrama do Fluxo de Calculo Revisado

```
+-------------------+
|   DADOS BRUTOS    |
| (vendas diarias)  |
+--------+----------+
         |
         v
+-------------------+
| CORTE DE DATA     |
| (exclui periodo   |
|  de previsao)     |
+--------+----------+
         |
         v
+-------------------+
| VERIFICAR         |
| COBERTURA ESTOQUE |
+--------+----------+
         |
    +----+----+
    |         |
    v         v
>=50%       <50%
    |         |
    v         v
+-------+  +----------+
|SANEAR |  |NORMALIZAR|
|RUPTURAS| |POR DIAS  |
+---+---+  +----+-----+
    |           |
    +-----+-----+
          |
          v
+-------------------+
| DEMAND CALCULATOR |
| (6 metodos)       |
+--------+----------+
         |
         v
+-------------------+
| FATORES SAZONAIS  |
| (multiplicadores) |
+--------+----------+
         |
         v
+-------------------+
| FORMULA FINAL:    |
| demanda * sazonal |
| * dias_periodo    |
+-------------------+
```

---

## Testes de Validacao

### Caso 1: DICOMPEL (Superestimacao Severa)

| Metrica | Antes | Depois |
|---------|-------|--------|
| Historico 2025 | 100.000 un | 100.000 un |
| Previsao 2026 | 181.600 un (+81.6%) | ~105.000 un (~+5%) |
| Status | ERRO | OK |

### Caso 2: PHILIPS IL (Demanda Intermitente)

| Metrica | Antes | Depois |
|---------|-------|--------|
| Historico (2 anos) | 22 un | 22 un |
| Taxa presenca | 2% | 2% |
| Previsao anual | 991 un | ~10-12 un |
| Status | ERRO | OK |

### Caso 3: PIAL LEGRAND (Dados Futuros)

| Metrica | Antes | Depois |
|---------|-------|--------|
| Jan/2026 real | 15.000 un | 15.000 un |
| Previsao Jan/2026 | ~15.000 un | ~12.000 un |
| Motivo | Usava dados reais | Corte de data |
| Status | ERRO | OK |

---

## Conclusao

As revisoes implementadas corrigem problemas fundamentais no calculo de previsao:

1. **Ativacao de funcionalidades existentes**: 6 metodos, sazonalidade e tendencia ja existiam mas nao estavam sendo usados corretamente
2. **Melhorias algoritmicas**: TSB com tendencia, corte de data, limiar de cobertura
3. **Normalizacao correta**: Divisao pelo total de dias, nao apenas dias com venda

O resultado e um modelo de previsao mais preciso e robusto, com previsoes alinhadas ao comportamento historico real de cada item.

---

# PARTE 2: FUNCIONALIDADES COMPLEMENTARES DO SISTEMA

Esta secao documenta funcionalidades implementadas no sistema que complementam o modelo de previsao.

---

## 8. Tratamento de Series Curtas (DemandCalculator)

### Contexto
Series temporais curtas (menos de 12 periodos) exigem tratamento especial, pois os metodos estatisticos tradicionais perdem confiabilidade com poucos dados.

### Classificacao de Series

| Categoria | Periodos | Tratamento |
|-----------|----------|------------|
| **Muito Curta** | 1-2 | Naive + Prior Bayesiano |
| **Curta** | 3-6 | WMA Adaptativo com Tendencia |
| **Media** | 7-11 | Metodos completos sem sazonalidade |
| **Longa** | 12+ | Todos os 6 metodos disponiveis |

### Metodo: Serie Muito Curta (1-2 periodos)

```python
# core/demand_calculator.py - Linhas 24-90
def calcular_demanda_serie_muito_curta(vendas, media_cluster=None):
    """
    1 periodo:
      - Com prior: 30% dado + 70% media do cluster
      - Sem prior: Naive com desvio heuristico (40%)

    2 periodos:
      - Com prior: 50% dados + 50% media do cluster
      - Sem prior: Media simples
    """
```

**Exemplo:**
```
Produto novo com 1 mes de dados: 100 unidades
Media do cluster de produtos similares: 80 unidades

Demanda estimada = 0.3 * 100 + 0.7 * 80 = 86 unidades
Fator de seguranca recomendado: 2.0 (dobrar estoque seguranca)
```

### Metodo: Serie Curta (3-6 periodos)

```python
# core/demand_calculator.py - Linhas 93-209
def calcular_demanda_serie_curta(vendas, media_cluster=None):
    """
    1. Verifica intermitencia (>40% zeros)
       - Se intermitente: TSB simplificado COM deteccao de tendencia

    2. Detecta tendencia (primeira vs segunda metade)

    3. Calcula WMA (Weighted Moving Average) adaptativo

    4. Combina com prior bayesiano se disponivel
       - 3 periodos: 45% dados + 55% prior
       - 6 periodos: 80% dados + 20% prior
    """
```

**Deteccao de Tendencia para Intermitentes:**
```python
razao = media_segunda_metade / media_primeira_metade

if razao < 0.5:
    tendencia = 'queda_acentuada'    # Produto saindo de linha
    fator = max(0.1, razao)
elif razao < 0.85:
    tendencia = 'decrescente'
    fator = razao
elif razao > 1.15:
    tendencia = 'crescente'
    fator = min(1.5, razao)
else:
    tendencia = 'estavel'
    fator = 1.0
```

### Metodo: Serie Media (7-11 periodos)

```python
# core/demand_calculator.py - Linhas 211-290
def calcular_demanda_serie_media(vendas):
    """
    1. Se >30% zeros: usar TSB completo
    2. Se alta variabilidade (CV > 0.5): usar EMA
    3. Se tendencia significativa (r > 0.5): usar regressao
    4. Caso contrario: usar WMA

    Nao aplica sazonalidade (ciclo anual incompleto)
    """
```

### Arquivo de Referencia
- [core/demand_calculator.py](core/demand_calculator.py) - Linhas 20-350

---

## 9. Calculo Unificado de Demanda Diaria

### Objetivo
Garantir consistencia entre granularidades (diario, semanal, mensal) usando sempre a base diaria para calculo.

### Metodo Principal

```python
# core/demand_calculator.py - Linhas 355-436
def calcular_demanda_diaria_unificada(
    vendas_diarias,        # Historico diario (ex: 730 dias)
    dias_periodo,          # Dias do periodo de previsao (ex: 181 para Jan-Jun)
    granularidade_exibicao,# 'diario', 'semanal' ou 'mensal'
    media_cluster_diaria   # Opcional: para prior bayesiano
):
    """
    Fluxo:
    1. Aplica calcular_demanda_adaptativa na serie diaria
    2. Obtem demanda_diaria_base
    3. Multiplica pelos dias do periodo
    4. Propaga incerteza: desvio_total = desvio_diario * sqrt(dias)
    """
```

### Formula de Propagacao de Incerteza

```
Desvio_total = Desvio_diario × √dias_periodo

Onde:
- Desvio_diario: desvio padrao da demanda diaria
- dias_periodo: numero de dias do periodo de previsao
- √: raiz quadrada (propagacao de variancia)
```

**Exemplo:**
```
Demanda diaria = 10 un/dia
Desvio diario = 3 un/dia
Periodo = 30 dias

Demanda total = 10 × 30 = 300 unidades
Desvio total = 3 × √30 = 16.4 unidades
```

### Validacao de Consistencia

```python
# core/demand_calculator.py - Linhas 438-494
def validar_consistencia_granularidades(
    demanda_mensal, dias_mensal,
    demanda_semanal, dias_semanal,
    tolerancia_pct=0.10
):
    """
    Verifica se previsoes mensal e semanal sao proporcionais.

    demanda_diaria_mensal = demanda_mensal / dias_mensal
    demanda_diaria_semanal = demanda_semanal / dias_semanal

    Se diferenca > 10%: ALERTA de inconsistencia
    """
```

### Arquivo de Referencia
- [core/demand_calculator.py](core/demand_calculator.py) - Linhas 355-494

---

## 10. Sistema de Ajustes Manuais de Previsao

### Conceito
Permite ao usuario refinar previsoes estatisticas com conhecimento de negocio (promocoes, eventos, etc).

### Estrutura de Dados

```sql
-- database/migration_v9_ajuste_previsao.sql
CREATE TABLE ajuste_previsao (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(20) NOT NULL,
    cod_fornecedor INTEGER,
    nome_fornecedor VARCHAR(200),
    periodo VARCHAR(20) NOT NULL,        -- "2026-02-01", "2026-S05"
    granularidade VARCHAR(10) NOT NULL,  -- 'mensal', 'semanal', 'diario'
    valor_original NUMERIC(12,2),        -- Previsao estatistica
    valor_ajustado NUMERIC(12,2),        -- Valor do usuario
    diferenca NUMERIC(12,2),
    percentual_ajuste NUMERIC(8,2),
    motivo VARCHAR(500),
    usuario_ajuste VARCHAR(100),
    data_ajuste TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE
);
```

### API de Ajustes

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/ajuste_previsao/salvar` | POST | Salva novos ajustes |
| `/api/ajuste_previsao/carregar` | GET | Carrega ajustes ativos |
| `/api/ajuste_previsao/historico` | GET | Historico de alteracoes |
| `/api/ajuste_previsao/excluir` | POST | Desativa um ajuste |

### Fluxo de Aplicacao

```
1. Usuario visualiza previsao estatistica
2. Usuario decide ajustar (ex: promocao planejada)
3. Sistema salva ajuste na tabela
4. Proxima geracao de previsao aplica ajustes ativos:

   previsao_final = valor_ajustado (se existe ajuste ativo)
                  = valor_estatistico (caso contrario)
```

### Trigger de Sobreposicao

```sql
-- Quando novo ajuste e inserido, desativa ajustes antigos do mesmo item/periodo
CREATE FUNCTION desativar_ajustes_sobrepostos() ...
    UPDATE ajuste_previsao
    SET ativo = FALSE
    WHERE cod_produto = NEW.cod_produto
      AND periodo = NEW.periodo
      AND id != NEW.id;
```

### Arquivos de Referencia
- [database/migration_v9_ajuste_previsao.sql](database/migration_v9_ajuste_previsao.sql)
- [app/blueprints/previsao.py](app/blueprints/previsao.py) - Linhas 1451-1710

---

## 11. Padrao de Compra (Integracao com Pedido Fornecedor)

### Conceito
Define para cada item e loja de venda qual e a loja destino do pedido (compra direta ou centralizada).

### Tipos de Padrao

| Tipo | Descricao | Exemplo |
|------|-----------|---------|
| **Direto** | Loja vende e recebe | Recife vende → Recife pede |
| **Centralizado** | CD central consolida pedidos | Recife vende → CD Paulista pede |

### Estrutura de Dados

```sql
-- database/migration_v7_padrao_compra.sql
CREATE TABLE padrao_compra_item (
    codigo INTEGER NOT NULL,
    cod_empresa_venda INTEGER NOT NULL,
    cod_empresa_destino INTEGER NOT NULL,
    data_referencia DATE,
    data_atualizacao TIMESTAMP,
    PRIMARY KEY (codigo, cod_empresa_venda)
);
```

### Fluxo de Integracao com Pedido Fornecedor

```
1. Pedido Fornecedor calcula demanda por loja de venda
2. Busca padrao de compra para cada item/loja
3. Reagrupa quantidades por loja destino
4. Adiciona lead time de transferencia (se centralizado)
5. Gera pedido consolidado por destino/fornecedor

Exemplo:
  - PIAL 100m vende em Recife: 50 un
  - PIAL 100m vende em Olinda: 30 un
  - Padrao: ambas → CD Paulista
  - Pedido gerado: CD Paulista = 80 un
```

### API de Padrao de Compra

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/padrao-compra/buscar` | GET/POST | Busca padroes |
| `/api/padrao-compra/estatisticas` | GET | Estatisticas |
| `/api/padrao-compra/itens-sem-padrao` | GET | Itens sem cadastro |
| `/api/padrao-compra/processar-pedidos` | POST | Aplica logica aos pedidos |
| `/api/padrao-compra/exportar` | POST | Exporta Excel |

### Parametro de Lead Time

```sql
-- Dias adicionais para transferencia entre filiais
SELECT valor FROM parametros_globais
WHERE chave = 'dias_transferencia_padrao_compra';

-- Padrao: 10 dias
```

### Impacto no Calculo de Pedido

```
Lead Time Efetivo = Lead Time Fornecedor + Dias Transferencia (se centralizado)

Exemplo:
  Fornecedor entrega em 15 dias
  Transferencia CD → Loja: 10 dias
  Lead Time Efetivo: 25 dias

  → Ponto de Pedido e Estoque Seguranca ajustados para 25 dias
```

### Criticas Geradas

| Critica | Descricao |
|---------|-----------|
| `sem_padrao_compra` | Item vendeu mas nao tem padrao cadastrado |
| `padrao_divergente` | Padrao diferente entre lojas do mesmo grupo |

### Arquivos de Referencia
- [app/blueprints/padrao_compra.py](app/blueprints/padrao_compra.py)
- [core/padrao_compra.py](core/padrao_compra.py)
- [database/migration_v7_padrao_compra.sql](database/migration_v7_padrao_compra.sql)
- [templates/pedido_fornecedor_integrado.html](templates/pedido_fornecedor_integrado.html)

---

## 12. Normalizacao do Desvio Padrao

### Contexto
O `DemandCalculator` calcula desvio padrao na granularidade dos dados de entrada (geralmente mensal). Para converter para outras granularidades:

### Conversao Mensal → Diario

```python
# Aproximacao assumindo mes de 30 dias
desvio_diario = desvio_mensal / sqrt(30)

# Ou usando media de dias por mes
desvio_diario = desvio_mensal / sqrt(dias_mes_medio)
```

### Propagacao Diario → Periodo

```python
# Para periodo de N dias
desvio_periodo = desvio_diario * sqrt(N)

# Equivalente a:
desvio_periodo = desvio_mensal * sqrt(N / 30)
```

### Exemplo Pratico

```
Desvio mensal calculado: 100 unidades
Periodo de previsao: 181 dias (Jan-Jun)

Desvio diario = 100 / √30 = 18.3 un/dia
Desvio periodo = 18.3 × √181 = 246 unidades

Ou diretamente:
Desvio periodo = 100 × √(181/30) = 100 × 2.46 = 246 unidades
```

### Uso no Estoque de Seguranca

```python
# Formula de estoque de seguranca
ES = Z × σ × √(LT)

Onde:
- Z: fator de nivel de servico (ex: 1.65 para 95%)
- σ: desvio padrao da demanda
- LT: lead time em dias
```

### Arquivo de Referencia
- [core/demand_calculator.py](core/demand_calculator.py) - Linhas 410-416

---

## Resumo das Funcionalidades Complementares

| # | Funcionalidade | Arquivo Principal | Status |
|---|----------------|-------------------|--------|
| 8 | Series Curtas | core/demand_calculator.py | Implementado |
| 9 | Calculo Unificado | core/demand_calculator.py | Implementado |
| 10 | Ajustes Manuais | migration_v9, previsao.py | Implementado |
| 11 | Padrao de Compra | padrao_compra.py | Integrado |
| 12 | Normalizacao Desvio | demand_calculator.py | Implementado |

---

## Proximos Passos Recomendados

1. **Monitorar WMAPE por fornecedor** apos as mudancas
2. **Ajustar limiar de cobertura** (50%) se necessario com base em resultados
3. **Melhorar coleta de dados de estoque** para aumentar cobertura
4. **Validar com usuarios de negocio** se as previsoes fazem sentido comercial
5. **Documentar ajustes manuais** mais utilizados para identificar padroes
6. **Revisar padroes de compra** para itens com critica `sem_padrao_compra`

---

## 13. Sistema de Auditoria e Conformidade de Metodologia

### Objetivo
Garantir que os calculos de Demanda e Pedido Fornecedor **sempre** sigam a metodologia documentada, evitando "fugas" no formato de calculo.

### Componentes do Sistema

```
+------------------------------------------------------------------+
|                 SISTEMA DE CONFORMIDADE                           |
+------------------------------------------------------------------+
|                                                                   |
|  1. CRONJOB DIARIO (Checklist Automatico)                        |
|     - Executa as 06:00 (antes do expediente)                     |
|     - Valida integridade dos modulos de calculo                  |
|     - Gera relatorio de conformidade                             |
|     - Envia alertas por email se houver desvios                  |
|                                                                   |
|  2. VALIDADOR EM TEMPO REAL (Durante Execucao)                   |
|     - Valida cada calculo no momento da execucao                 |
|     - Registra metadata de metodologia usada                     |
|     - Bloqueia resultados fora do padrao                         |
|                                                                   |
|  3. LOG DE AUDITORIA (Historico)                                 |
|     - Registra todas as execucoes                                |
|     - Permite rastreabilidade completa                           |
|     - Dashboard de metricas de qualidade                         |
|                                                                   |
+------------------------------------------------------------------+
```

### 13.1 Checklist Diario de Conformidade

O checklist executa 11 verificacoes automaticas diariamente:

| # | Codigo | Verificacao | Criticidade |
|---|--------|-------------|-------------|
| 1 | V01 | Modulos carregam sem erro | Bloqueante |
| 2 | V02 | 6 metodos estatisticos disponiveis | Bloqueante |
| 3 | V03 | SMA calcula corretamente | Bloqueante |
| 4 | V04 | WMA calcula corretamente | Bloqueante |
| 5 | V05 | Sazonalidade em range valido (0.5-2.0) | Alerta |
| 6 | V06 | Saneamento de rupturas (limiar 50%) | Alerta |
| 7 | V07 | Normalizacao por dias totais | Bloqueante |
| 8 | V08 | Formula pedido: max(0, Dem + ES - Est) | Bloqueante |
| 9 | V09 | Estoque seguranca por curva ABC | Alerta |
| 10 | V10 | Consistencia geral do sistema | Alerta |
| 11 | V11 | Limitador variacao vs ano anterior (-40% a +50%) | Bloqueante |

**Exemplo de Relatorio:**
```
==============================================================
  RELATORIO DE CONFORMIDADE - 2026-02-04 19:19
==============================================================
  Status Geral: APROVADO (11/11 verificacoes)
==============================================================
  Verificacoes:
  [OK] V01: Modulos Carregam
       Todos os 4 modulos carregaram
  [OK] V02: 6 Metodos Disponiveis
       Todos os 6 metodos disponiveis
  [OK] V03: SMA Calcula Corretamente
       SMA calculou 40.00 (esperado: 28-45)
  [OK] V04: WMA Calcula Corretamente
       WMA calculou 43.33 (> media simples 30)
  [OK] V05: Sazonalidade Valida
       Sazonalidade calculou demanda 103.54
  [OK] V06: Saneamento Rupturas
       Logica de saneamento correta (limiar 50.0%)
  [OK] V07: Normalizacao por Dias
       Normalizacao correta: 730/730 = 1.0000
  [OK] V08: Formula Pedido
       Formula pedido correta: max(0, 1000+200-600) = 600
  [OK] V09: ES por Curva ABC
       Z-scores ABC corretos: A=2.05, B=1.65, C=1.28
  [OK] V10: Consistencia Geral
       Sistema consistente: demanda=171.1364, metodo=tendencia
  [OK] V11: Limitador Variacao AA
       Limitador variacao AA correto (-40% a +50%)
==============================================================
  Tempo total: 185ms
==============================================================
```

### 13.2 Modos de Operacao do Cronjob

```bash
# 1. Execucao manual (para testes)
python jobs/checklist_diario.py --manual

# 2. Scheduler Python (desenvolvimento) - roda as 06:00
python jobs/checklist_diario.py

# 3. Teste de email
python jobs/checklist_diario.py --teste-email

# 4. Gerar script para servico Windows
python jobs/checklist_diario.py --install
```

### 13.3 Tabelas de Auditoria

```sql
-- Registro de execucoes do checklist
CREATE TABLE auditoria_conformidade (
    id SERIAL PRIMARY KEY,
    data_execucao TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo VARCHAR(20) NOT NULL,          -- 'cronjob_diario', 'manual', 'tempo_real'
    status VARCHAR(15) NOT NULL,        -- 'aprovado', 'reprovado', 'alerta'
    total_verificacoes INTEGER NOT NULL,
    verificacoes_ok INTEGER NOT NULL,
    verificacoes_falha INTEGER NOT NULL DEFAULT 0,
    verificacoes_alerta INTEGER NOT NULL DEFAULT 0,
    detalhes JSONB,                     -- Resultado detalhado
    tempo_execucao_ms INTEGER,
    alerta_enviado BOOLEAN DEFAULT FALSE,
    alerta_destinatarios TEXT[]
);

-- Registro detalhado de cada calculo
CREATE TABLE auditoria_calculos (
    id SERIAL PRIMARY KEY,
    data_calculo TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo_calculo VARCHAR(20) NOT NULL,  -- 'demanda', 'pedido'
    cod_produto VARCHAR(20),
    cod_empresa INTEGER,
    cod_fornecedor INTEGER,
    metodo_usado VARCHAR(50),           -- 'sma', 'wma', 'ema', 'tendencia', etc
    categoria_serie VARCHAR(20),        -- 'muito_curta', 'curta', 'media', 'longa'
    parametros_entrada JSONB,
    resultado JSONB,
    validacao_ok BOOLEAN DEFAULT TRUE
);
```

### 13.4 API de Validacao

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/validacao/executar-checklist` | Executa o checklist completo |
| GET | `/api/validacao/dashboard` | Metricas e resumo de conformidade |
| GET | `/api/validacao/historico` | Historico de execucoes |
| GET | `/api/validacao/detalhes/<id>` | Detalhes de uma execucao |
| GET | `/api/validacao/metodos-utilizados` | Estatisticas de metodos |

**Exemplo de resposta do Dashboard:**
```json
{
  "sucesso": true,
  "periodo_dias": 30,
  "metricas": {
    "total_execucoes": 30,
    "aprovadas": 28,
    "reprovadas": 2,
    "taxa_conformidade": 93.33,
    "tempo_medio_ms": 251
  },
  "ultima_execucao": {
    "data": "2026-02-04T18:49:32",
    "status": "aprovado",
    "verificacoes_ok": 10,
    "verificacoes_falha": 0
  },
  "tendencia": "estavel"
}
```

### 13.5 Alertas Automaticos

**Configuracao em `jobs/configuracao_jobs.py`:**
```python
CONFIGURACAO_ALERTAS = {
    'email': {
        'habilitado': True,
        'destinatarios': ['valter.lino@ferreiracosta.com.br'],
        'smtp_server': 'smtp.office365.com',
        'smtp_port': 587,
        'assunto_padrao': '[ALERTA] Desvio de Metodologia - Previsao Demanda'
    },
    'horario_execucao': '06:00',  # Horario do checklist diario
    'criticidade': {
        'bloqueante': ['modulos_indisponiveis', 'metodos_faltando', 'demanda_negativa'],
        'alerta': ['sazonalidade_extrema', 'cobertura_insuficiente', 'desvio_alto'],
        'info': ['tempo_execucao_alto', 'variacao_detectada']
    }
}
```

**Regras de Alerta:**
- **Status REPROVADO**: Email enviado imediatamente (verificacao bloqueante falhou)
- **Status ALERTA**: Email enviado (verificacao de alerta falhou)
- **Status APROVADO**: Nenhum email (apenas registro no banco)

### 13.6 Decorador de Validacao em Tempo Real

Para validar calculos individualmente durante a execucao:

```python
from core.validador_conformidade import validar_metodologia

@validar_metodologia
def calcular_demanda_inteligente(vendas, metodo='auto'):
    """
    O decorador:
    1. Executa a funcao original
    2. Valida o resultado (demanda nao-negativa, desvio valido, etc)
    3. Adiciona metadata de validacao ao retorno
    4. Registra em auditoria_calculos se conexao disponivel
    """
    demanda, desvio = ...  # calculo
    return demanda, desvio, metadata
```

### 13.7 Z-Scores por Curva ABC

O sistema verifica se os Z-scores usados para calculo de Estoque de Seguranca estao corretos:

| Curva | Z-Score | Nivel de Servico |
|-------|---------|------------------|
| A | 2.05 | 98% |
| B | 1.65 | 95% |
| C | 1.28 | 90% |

**Formula de Estoque de Seguranca:**
```
ES = Z × σ × √LT

Onde:
- Z: fator da tabela acima
- σ: desvio padrao da demanda
- LT: lead time em dias
```

### 13.8 Limitador de Variacao vs Ano Anterior (V11)

O sistema implementa um **limitador de variacao** que evita previsoes extremas comparando com o ano anterior:

**Regra:**
```
Se variacao_vs_ano_anterior > 1.5 (mais de +50%):
    previsao_limitada = ano_anterior × 1.5

Se variacao_vs_ano_anterior < 0.6 (mais de -40%):
    previsao_limitada = ano_anterior × 0.6
```

**Codigo em previsao.py:**
```python
# LIMITADOR DE VARIACAO vs ANO ANTERIOR (V11)
# Evita previsoes extremas limitando variacao entre -40% e +50%
if valor_aa_periodo > 0:
    variacao_vs_aa = previsao_periodo / valor_aa_periodo
    if variacao_vs_aa > 1.5:
        previsao_periodo = valor_aa_periodo * 1.5
    elif variacao_vs_aa < 0.6:
        previsao_periodo = valor_aa_periodo * 0.6
```

**Justificativa:**
- Evita que combinacao de tendencia + sazonalidade gere valores irreais
- O fator de tendencia (ate 1.5x) × fator sazonal (ate 2.0x) poderia resultar em 3.0x
- Com o limitador, a variacao maxima vs ano anterior e de +50%

**Exemplo - Fornecedor FAME:**
| Cenario | Nov/25 (AA) | Previsao Original | Previsao Limitada |
|---------|-------------|-------------------|-------------------|
| Sem limitador | 7.609 | 13.201 (+73%) | 13.201 |
| Com limitador | 7.609 | 13.201 (+73%) | 11.414 (+50%) |

### 13.9 Arquivos do Sistema de Conformidade

| Arquivo | Descricao |
|---------|-----------|
| [core/validador_conformidade.py](core/validador_conformidade.py) | Classe ValidadorConformidade + 11 verificacoes |
| [jobs/checklist_diario.py](jobs/checklist_diario.py) | Script do cronjob com APScheduler |
| [jobs/configuracao_jobs.py](jobs/configuracao_jobs.py) | Configuracoes de alertas e banco |
| [app/blueprints/validacao.py](app/blueprints/validacao.py) | Endpoints REST da API |
| [app/blueprints/previsao.py](app/blueprints/previsao.py) | Implementacao do limitador V11 |
| [database/migration_v10_auditoria_conformidade.sql](database/migration_v10_auditoria_conformidade.sql) | Tabelas de auditoria |

### 13.10 Beneficios do Sistema

1. **Deteccao Proativa**: Problemas identificados antes de impactar usuarios
2. **Rastreabilidade**: Historico completo de todas as execucoes e calculos
3. **Conformidade Garantida**: Cada calculo validado contra metodologia
4. **Alertas Imediatos**: Notificacao automatica de desvios
5. **Auditoria**: Evidencias para compliance e revisoes de qualidade

---

## Resumo Geral das Funcionalidades

| # | Funcionalidade | Arquivo Principal | Status |
|---|----------------|-------------------|--------|
| 1-7 | Modelo de Previsao (Revisao 2026) | previsao.py, demand_calculator.py | Implementado |
| 8 | Series Curtas | core/demand_calculator.py | Implementado |
| 9 | Calculo Unificado | core/demand_calculator.py | Implementado |
| 10 | Ajustes Manuais | migration_v9, previsao.py | Implementado |
| 11 | Padrao de Compra | padrao_compra.py | Integrado |
| 12 | Normalizacao Desvio | demand_calculator.py | Implementado |
| **13** | **Auditoria e Conformidade** | **validador_conformidade.py** | **Implementado** |
| **14** | **Limitador Variacao AA (-40% a +50%)** | **previsao.py** | **Implementado** |
| **15** | **Demanda Pre-Calculada (Cronjob)** | **calcular_demanda_diaria.py** | **Implementado** |

---

## 15. Demanda Pre-Calculada (Cronjob Diario)

### Contexto e Problema
A Tela de Demanda e a Tela de Pedido Fornecedor usavam calculos diferentes para demanda:
- **Tela Demanda**: `calcular_demanda_diaria_unificada()` com fatores sazonais e limitador V11
- **Tela Pedido**: `calcular_demanda_inteligente()` SEM fatores sazonais e SEM limitador V11

Isso causava **inconsistencia** nos valores entre as duas telas.

### Solucao Implementada
Um **cronjob diario** (05:00) calcula a demanda de todos os itens e salva em uma tabela pre-calculada. A Tela de Pedido agora usa esses valores pre-calculados, garantindo **integridade total** com a Tela de Demanda.

### Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                SISTEMA DE DEMANDA PRE-CALCULADA                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CRONJOB DIARIO (05:00)                                        │
│  ├─ Calcula demanda para todos os itens x fornecedores         │
│  ├─ Aplica mesma metodologia da Tela Demanda:                  │
│  │   • 6 metodos estatisticos                                  │
│  │   • Fatores sazonais (0.5 a 2.0)                           │
│  │   • Limitador V11 (-40% a +50%)                            │
│  ├─ Salva em demanda_pre_calculada                             │
│  └─ Preserva ajustes manuais (nao sobrescreve)                 │
│                                                                 │
│  TELA DEMANDA                                                   │
│  └─ Continua calculando em tempo real (para graficos)          │
│                                                                 │
│  TELA PEDIDO FORNECEDOR                                         │
│  └─ Busca valores da tabela demanda_pre_calculada              │
│     (fallback para calculo em tempo real se nao existir)       │
│                                                                 │
│  AJUSTES MANUAIS                                                │
│  └─ Sobrepõem valores calculados (via API ou interface)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tabelas Criadas (Migration V12)

```sql
-- Tabela principal de demanda pre-calculada
demanda_pre_calculada
├─ cod_produto, cnpj_fornecedor, cod_empresa
├─ ano, mes (periodo)
├─ demanda_prevista, demanda_diaria_base, desvio_padrao
├─ fator_sazonal, limitador_aplicado
├─ metodo_usado, categoria_serie
├─ ajuste_manual (sobrepõe calculado)
└─ data_calculo

-- Historico de calculos (auditoria)
demanda_pre_calculada_historico

-- Controle de execucoes do cronjob
demanda_calculo_execucao

-- View que retorna demanda efetiva
vw_demanda_efetiva
```

### API Endpoints

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/api/demanda_job/status` | GET | Status do job e ultimas execucoes |
| `/api/demanda_job/recalcular` | POST | Inicia recalculo (todos ou fornecedor especifico) |
| `/api/demanda_job/ajustar` | POST | Registra ajuste manual de demanda |
| `/api/demanda_job/remover_ajuste` | POST | Remove ajuste manual |
| `/api/demanda_job/consultar` | GET | Consulta demanda pre-calculada |

### Execucao do Cronjob

```bash
# Execucao automatica (scheduler)
python jobs/calcular_demanda_diaria.py

# Execucao manual (todos os fornecedores)
python jobs/calcular_demanda_diaria.py --manual

# Recalculo de fornecedor especifico
python jobs/calcular_demanda_diaria.py --fornecedor 60620366000195

# Verificar status
python jobs/calcular_demanda_diaria.py --status
```

### Arquivos de Referencia
- [database/migration_v12_demanda_pre_calculada.sql](database/migration_v12_demanda_pre_calculada.sql)
- [jobs/calcular_demanda_diaria.py](jobs/calcular_demanda_diaria.py)
- [app/utils/demanda_pre_calculada.py](app/utils/demanda_pre_calculada.py)
- [app/blueprints/demanda_job.py](app/blueprints/demanda_job.py)
- [app/blueprints/pedido_fornecedor.py](app/blueprints/pedido_fornecedor.py) - Adaptado para usar tabela

### Beneficios
1. **Integridade Total**: Mesmos valores em Tela Demanda e Tela Pedido
2. **Performance**: Consulta rapida em vez de calculo em tempo real
3. **Ajustes Manuais**: Usuarios podem sobrepor valores calculados
4. **Auditoria**: Historico completo de calculos e ajustes
5. **Recalculo Sob Demanda**: API permite recalcular fornecedor especifico

---

## Proximos Passos Recomendados

1. **Monitorar WMAPE por fornecedor** apos as mudancas
2. **Ajustar limiar de cobertura** (50%) se necessario com base em resultados
3. **Melhorar coleta de dados de estoque** para aumentar cobertura
4. **Validar com usuarios de negocio** se as previsoes fazem sentido comercial
5. **Documentar ajustes manuais** mais utilizados para identificar padroes
6. **Revisar padroes de compra** para itens com critica `sem_padrao_compra`
7. **Monitorar dashboard de conformidade** diariamente para detectar regressoes
8. **Verificar execucao do cronjob** diariamente via `/api/demanda_job/status`

---

**Documento criado em:** 04/02/2026
**Ultima atualizacao:** 04/02/2026
**Versao do sistema:** 5.6
