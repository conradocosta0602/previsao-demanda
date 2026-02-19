# ANÁLISE - Problema de Detecção de Sazonalidade Semestral

## Problema Relatado pelo Usuário

> "A linha ainda está muito linear... Claramente existe um comportamento de queda na demanda nos meses de Julho a dezembro de 2023 que estão totalmente ignorados na curva de 2024."

## Investigação

### Dados de Teste

Padrão semestral claro:
- **Jan-Jun**: Alta demanda (~120-125)
- **Jul-Dez**: Baixa demanda (~80-85)

### Resultados da Detecção

| Período | Força | P-value | Significativo? |
|---------|-------|---------|----------------|
| 2       | 0.0074 | 0.88   | ❌ Não        |
| 4       | 0.0367 | 0.57   | ❌ Não        |
| **6**   | **0.2152** | **0.998** | ❌ **Não** |
| 7       | 0.1190 | 0.98   | ❌ Não        |
| **12**  | **0.9860** | **0.000016** | ✅ **Sim** |

**Escolhido:** Período 12 (anual) com força 0.99

### Causa Raiz

O detector usa **dois critérios** para validar sazonalidade:

```python
# seasonality_detector.py:108
has_seasonality = (best['score'] > 0.3 and best['pvalue'] < 0.05)
```

1. **Força > 0.3** → Decomposição STL (✅ Funciona corretamente)
2. **P-value < 0.05** → Teste ANOVA (❌ PROBLEMA AQUI)

#### O Problema do ANOVA

O teste ANOVA usado (linhas 214-227 do `seasonality_detector.py`):

```python
# Agrupar dados por índice sazonal
seasonal_groups = []
for i in range(period):
    indices = np.arange(i, len(self.data), period)
    group = self.data[indices]
    if len(group) > 0:
        seasonal_groups.append(group)

# ANOVA one-way
if len(seasonal_groups) >= 2:
    f_stat, pvalue = stats.f_oneway(*seasonal_groups)
```

**Para período 6 com 24 dados:**
- Grupo 0: [mes1, mes7, mes13, mes19] = 4 valores
- Grupo 1: [mes2, mes8, mes14, mes20] = 4 valores
- ...
- Grupo 5: [mes6, mes12, mes18, mes24] = 4 valores

**ANOVA com apenas 4 valores por grupo** tem **baixíssimo poder estatístico**!

**Para período 12 com 24 dados:**
- Grupo 0: [mes1, mes13] = 2 valores
- Grupo 1: [mes2, mes14] = 2 valores
- ...
- Grupo 11: [mes12, mes24] = 2 valores

ANOVA ainda funciona porque há **correlação perfeita** entre anos (Janeiro 2023 ≈ Janeiro 2024).

### Por que Período 12 Vence?

Com padrão semestral:
- **Período 6**: Força moderada (0.22) mas p-value alto (não significativo)
- **Período 12**: Força ALTA (0.99) E p-value baixo (significativo)

Isso acontece porque período 12 captura **harmônico** do padrão semestral:
- Se há padrão a cada 6 meses, também há padrão a cada 12 meses
- Como Janeiro 2023 e Janeiro 2024 são ambos "altos", período 12 tem correlação forte

## Soluções Possíveis

### Opção 1: Ajustar Threshold do P-value

```python
# Atual
has_seasonality = (best['score'] > 0.3 and best['pvalue'] < 0.05)

# Proposta
has_seasonality = (best['score'] > 0.3 and best['pvalue'] < 0.10)
```

**Problema:** Aumenta falsos positivos em dados sem sazonalidade real.

### Opção 2: Usar Apenas Força (Sem ANOVA)

```python
has_seasonality = (best['score'] > 0.4)  # Threshold mais alto
```

**Problema:** Pode detectar padrões espúrios sem validação estatística.

### Opção 3: Preferir Períodos Fundamentais ✅ RECOMENDADA

Se período N tem força similar a período 2N, preferir N (mais fundamental):

```python
# Já implementado em seasonality_detector.py:105-113
for result in results[1:]:
    if (best['score'] - result['score']) / best['score'] < 0.10:
        if best['period'] % result['period'] == 0:
            best = result
            break
```

**Problema atual:** Diferença de força entre período 6 e 12 é **>10%**:
```
(0.9860 - 0.2152) / 0.9860 = 0.78 = 78%
```

Então a condição não se aplica.

### Opção 4: Usar Teste Estatístico Diferente

Substituir ANOVA por teste mais robusto para pequenas amostras:
- Teste de Kruskal-Wallis (não-paramétrico)
- Teste de permutação
- Análise de Fourier (detecta frequências dominantes)

### Opção 5: Combinar Força STL + Análise Espectral ✅ MELHOR SOLUÇÃO

1. **STL Decomposition** → Calcula força da sazonalidade
2. **FFT (Fast Fourier Transform)** → Identifica frequências dominantes
3. **Validação cruzada** → Se ambos concordam no período, alta confiança

## Recomendação Final

**Solução Pragmática Imediata:**

Reduzir threshold de força para período mais curto OU aceitar p-value mais alto quando força > 0.2:

```python
# seasonality_detector.py - linha 108
# ANTES
has_seasonality = (best['score'] > 0.3 and best['pvalue'] < 0.05)

# DEPOIS
# Critério mais flexível para períodos curtos com poucos ciclos
if best['period'] <= 6:
    # Períodos curtos: aceitar força moderada OU p-value mais relaxado
    has_seasonality = (best['score'] > 0.2 and best['pvalue'] < 0.15)
else:
    # Períodos longos: manter critério rigoroso
    has_seasonality = (best['score'] > 0.3 and best['pvalue'] < 0.05)
```

**Solução Robusta de Longo Prazo:**

Implementar análise espectral (FFT) como validação complementar.

## Próximos Passos

1. ✅ Implementar critério flexível para períodos curtos
2. Testar com dados reais do usuário
3. Se necessário, adicionar análise espectral (FFT)
4. Documentar comportamento em VALIDACAO_SEASONALITY_DETECTOR.md

## Status

🔧 **EM PROGRESSO** - Aguardando decisão do usuário sobre qual solução implementar.
