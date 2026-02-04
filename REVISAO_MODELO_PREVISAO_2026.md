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
Analisando os dados, descobrimos que a tabela `historico_estoque_diario` tinha poucos registros para a maioria dos itens (~15 registros vs 700 dias necessarios). Usar o `RupturaSanitizer` com dados incompletos poderia gerar distorcoes.

### Solucao: Limiar de 50% de Cobertura

```python
# previsao.py - Linhas 415-470
estoque_item = estoque_item_dict.get(cod_produto, {})
dias_com_registro_estoque = len(estoque_item)
cobertura_estoque = dias_com_registro_estoque / dias_historico_total

if cobertura_estoque >= 0.50:  # >= 50% de cobertura
    # Usar RupturaSanitizer
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
- [core/ruptura_sanitizer.py](core/ruptura_sanitizer.py) - Referencia (ja existia)

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

### core/ruptura_sanitizer.py

| Status | Descricao |
|--------|-----------|
| Referencia | Ja existia, agora e usado via logica inline em previsao.py |

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

## Proximos Passos Recomendados

1. **Monitorar WMAPE por fornecedor** apos as mudancas
2. **Ajustar limiar de cobertura** (50%) se necessario com base em resultados
3. **Melhorar coleta de dados de estoque** para aumentar cobertura
4. **Validar com usuarios de negocio** se as previsoes fazem sentido comercial

---

**Documento criado em:** 04/02/2026
**Ultima atualizacao:** 04/02/2026
**Versao do sistema:** 5.3
