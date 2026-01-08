# 📊 Entendendo Granularidade e Diferenças nas Previsões

## ⚠️ Aviso Importante

**Alterar a granularidade das previsões (mensal, semanal, diária) pode resultar em diferenças nos valores totais previstos, mesmo para o mesmo período de tempo.** Isso é **esperado e normal** devido à natureza dos métodos estatísticos utilizados.

---

## 🔍 Por Que as Previsões Variam com a Granularidade?

### 1. **Agregação de Dados Históricos**

Quando os dados são agregados em diferentes granularidades, pequenas diferenças podem ocorrer:

```
Exemplo Real:
- Mensal (25 meses): Total histórico = 3,913,728 unidades
- Semanal (105 semanas): Total histórico = 3,957,755 unidades
- Diferença: ~1.1%
```

**Causa:** `DATE_TRUNC('week')` no PostgreSQL agrupa semanas começando na segunda-feira, podendo incluir dias de meses adjacentes, enquanto `DATE_TRUNC('month')` agrupa por mês calendário completo.

### 2. **Janela Adaptativa dos Modelos Estatísticos**

Os modelos de média móvel usam janelas proporcionais ao número de períodos:

```
Fórmula: janela = max(3, total_períodos / 2)

Mensal:
- 25 períodos → janela de 12 períodos (12 meses)
- Calcula média sobre 12 valores mensais

Semanal:
- 105 períodos → janela de 52 períodos (52 semanas)
- Calcula média sobre 52 valores semanais
```

**Impacto:** Embora ambos usem ~1 ano de dados, o modelo semanal é mais sensível a flutuações recentes porque analisa 52 pontos de dados vs 12 pontos do mensal.

### 3. **Métricas de Acurácia (WMAPE, BIAS, MAE)**

Em granularidades mais finas, as métricas de erro tendem a ser **menores em valor absoluto** mas **mais variáveis**:

```
Exemplo Observado:
Mensal:
- WMAPE: 5.90%
- Valores previstos: 6 períodos
- Erro médio por período: maior

Semanal:
- WMAPE: 2.40%
- Valores previstos: 24 períodos
- Erro médio por período: menor

Motivo: Erros semanais se compensam parcialmente na agregação mensal
```

### 4. **Fatores Sazonais**

Diferentes granularidades capturam padrões sazonais diferentes:

```
Mensal:
- 12 fatores sazonais (um por mês)
- Variação: 0.931 - 1.054 (~13% amplitude)

Semanal:
- 4 fatores sazonais (ciclo de 4 semanas)
- Variação: 0.992 - 1.010 (~1.8% amplitude)
```

**Resultado:** Ajustes sazonais aplicam multiplicadores diferentes, afetando as previsões finais.

---

## 📈 Magnitude Esperada das Diferenças

### Diferenças Aceitáveis

| Comparação | Diferença Típica | Status |
|------------|------------------|--------|
| Mensal vs Semanal (mesmo período) | 5-15% | ✅ Normal |
| Mensal vs Diário (mesmo período) | 10-20% | ✅ Normal |
| Semanal vs Diário (mesmo período) | 5-10% | ✅ Normal |

### Diferenças Problemáticas

| Comparação | Diferença | Status |
|------------|-----------|--------|
| Mensal vs Semanal | >25% | ⚠️ Investigar |
| Dados históricos agregados | >5% | ⚠️ Verificar queries SQL |

---

## 🎯 Recomendações de Uso

### 1. **Escolha da Granularidade**

**Mensal:**
- ✅ Melhor para: Planejamento estratégico, orçamentos anuais
- ✅ Vantagens: Menos ruído, padrões mais claros, métricas mais estáveis
- ❌ Limitações: Menos detalhamento, não captura variações intra-mês

**Semanal:**
- ✅ Melhor para: Reabastecimento, gestão operacional
- ✅ Vantagens: Bom equilíbrio entre detalhe e estabilidade
- ⚠️ Atenção: Previsões mais sensíveis a eventos recentes

**Diária:**
- ✅ Melhor para: Operações day-to-day, promoções de curto prazo
- ✅ Vantagens: Máximo detalhe, captura sazonalidade semanal (dias da semana)
- ❌ Limitações: Mais ruído, requer mais dados históricos, previsões mais voláteis

### 2. **Comparação entre Granularidades**

**❌ NÃO faça:**
```
❌ Comparar totais absolutos e esperar valores idênticos
❌ Usar WMAPE mensal e semanal como diretamente comparáveis
❌ Trocar granularidade no meio de um ciclo de planejamento
```

**✅ FAÇA:**
```
✅ Use a MESMA granularidade para comparações ao longo do tempo
✅ Entenda que diferenças de 5-15% são normais e esperadas
✅ Escolha a granularidade apropriada para seu caso de uso
✅ Valide previsões com dados reais independente da granularidade
```

### 3. **Validação de Resultados**

Para validar se as diferenças estão dentro do esperado:

```python
# Exemplo de validação
previsao_mensal_total = 1_979_447  # 6 meses
previsao_semanal_total = 1_772_337  # 24 semanas (~6 meses)

diferenca_percentual = abs(previsao_mensal_total - previsao_semanal_total) / previsao_mensal_total * 100
# Resultado: 10.46%

if diferenca_percentual < 15:
    status = "✅ Dentro do esperado"
elif diferenca_percentual < 25:
    status = "⚠️ Revisar parâmetros"
else:
    status = "❌ Investigar problema"
```

---

## 🔧 Mitigação de Diferenças

### Melhorias Já Implementadas

1. ✅ **Queries SQL Consistentes**: CTEs garantem mesmo intervalo de datas base
2. ✅ **Logging Detalhado**: Totais históricos, previsões base e ajustes são registrados
3. ✅ **Fatores Sazonais por Granularidade**: Calculados apropriadamente para cada nível

### Melhorias Futuras (Roadmap)

- [ ] **Janela de Tempo Fixa**: Modificar modelos para usar janelas baseadas em tempo real (ex: sempre 12 meses) em vez de número de períodos
- [ ] **Modo de Comparação**: Agregar previsões semanais/diárias para facilitar comparação com mensais
- [ ] **Alerta de Divergência**: Avisar quando diferenças entre granularidades excedem thresholds esperados

---

## 📚 Exemplos Práticos

### Caso de Uso 1: Planejamento de Compras

```
Cenário: Planejar compras para próximo trimestre

✅ Recomendação: Use granularidade MENSAL
   - Previsão: 3 meses
   - Motivo: Ciclos de compra geralmente mensais
   - WMAPE esperado: 5-8%
```

### Caso de Uso 2: Reabastecimento CD → Loja

```
Cenário: Pedidos semanais de reabastecimento

✅ Recomendação: Use granularidade SEMANAL
   - Previsão: 4-8 semanas
   - Motivo: Ciclo de reabastecimento semanal
   - WMAPE esperado: 2-5%
```

### Caso de Uso 3: Gestão de Promoções

```
Cenário: Promoção de 7 dias

✅ Recomendação: Use granularidade DIÁRIA
   - Previsão: 7-14 dias
   - Motivo: Impacto dia a dia é relevante
   - WMAPE esperado: 8-15%
```

---

## ❓ FAQ

**P: Por que a previsão mensal deu 1.979.447 e a semanal 1.772.337 para o mesmo período?**

R: Diferença de 10.46% é normal e esperada. Causas:
- Janelas adaptativas diferentes (12 meses vs 52 semanas)
- Agregação de dados ligeiramente diferente (1.1% nos históricos)
- Fatores sazonais com amplitudes diferentes (13% vs 1.8%)

**P: Qual granularidade é mais "correta"?**

R: Nenhuma é intrinsecamente mais correta. Escolha baseado em:
- Seu caso de uso (estratégico = mensal, operacional = semanal/diário)
- Frequência de decisões (compras mensais = mensal, reabastecimento semanal = semanal)
- Disponibilidade de dados históricos (diário requer mais dados)

**P: Como saber se a diferença está muito alta?**

R: Use as faixas de referência:
- < 15%: ✅ Normal
- 15-25%: ⚠️ Revisar parâmetros, verificar outliers
- > 25%: ❌ Investigar dados históricos e configurações

**P: Posso converter previsões semanais em mensais somando?**

R: Sim, mas atenção:
```
✅ Correto: Somar 4 semanas completas dentro de um mês
❌ Errado: Assumir que 4 semanas = 1 mês exato

Melhor prática:
- Use 4.33 semanas/mês em média (52 semanas / 12 meses)
- Ou faça previsão diretamente na granularidade desejada
```

---

## 📞 Suporte

Se você observar diferenças que excedem os valores esperados (>25%), verifique:

1. ✅ Dados históricos estão completos para ambas granularidades
2. ✅ Mesmos filtros (loja, categoria, produto) foram aplicados
3. ✅ Mesmo período de previsão foi solicitado
4. ✅ Logs do sistema (`app.log`) não mostram erros

Para mais informações, consulte:
- [Documentacao_Sistema_Previsao_v3.0.docx](Documentacao_Sistema_Previsao_v3.0.docx)
- [README.md](README.md)

---

**Versão:** 1.0
**Última Atualização:** Janeiro 2026
**Status:** Documentação Oficial
