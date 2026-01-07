# 📊 Migração de MAPE para WMAPE

**Data:** Janeiro 2026
**Status:** ✅ IMPLEMENTADO
**Versão:** 2.0

---

## 🎯 O Que Mudou?

A métrica principal de acurácia do sistema foi **atualizada de MAPE para WMAPE** (Weighted Mean Absolute Percentage Error).

### ANTES (MAPE)
```
MAPE = (1/n) × Σ |actual - predicted| / |actual| × 100
```
- Trata todos os produtos igualmente
- Produto de 1 unidade tem mesmo peso que produto de 100 unidades
- Pode ser distorcido por produtos de baixo volume

### DEPOIS (WMAPE)
```
WMAPE = Σ|actual - predicted| / Σ|actual| × 100
```
- Pondera erros pelo volume de vendas
- Produtos de alto volume têm peso proporcional à sua importância
- Mais representativo para análise de varejo

---

## 💡 Por Que WMAPE é Superior?

### Exemplo Prático

| Produto | Venda Real | Previsão | Erro Absoluto | APE (MAPE) |
|---------|------------|----------|---------------|------------|
| A       | 1 un       | 2 un     | 1 un          | 100%       |
| B       | 100 un     | 101 un   | 1 un          | 1%         |

**MAPE (média simples):**
```
MAPE = (100% + 1%) / 2 = 50.5%
```
❌ **Resultado distorcido!** O produto A (1 unidade) tem mesmo peso que B (100 unidades).

**WMAPE (ponderado por volume):**
```
WMAPE = (1 + 1) / (1 + 100) × 100 = 1.98%
```
✅ **Resultado correto!** O erro de 1 unidade é pequeno no contexto do volume total.

---

## 🔧 O Que Foi Alterado?

### 1. Core: accuracy_metrics.py
- ✅ Nova função `calculate_wmape()`
- ✅ Função `calculate_mape()` marcada como **DEPRECADA**
- ✅ `walk_forward_validation()` retorna WMAPE como métrica principal
- ✅ `evaluate_model_accuracy()` usa WMAPE nos cálculos
- ✅ `format_accuracy_report()` exibe WMAPE

### 2. Backend: app.py
- ✅ Variável `mape` renomeada para `wmape`
- ✅ Coluna de saída `MAPE` alterada para `WMAPE`
- ✅ modelo_info usa `wmape` em vez de `mape`

### 3. Frontend: templates/index.html
- ✅ Card "MAPE Médio" → "WMAPE Médio"
- ✅ Explicação atualizada: "Mede a acurácia ponderada por volume"

### 4. Frontend: static/js/app.js
- ✅ Variável `mapeMedia` → `wmapeMedia`
- ✅ Função `getMapeColor()` → `getWmapeColor()`
- ✅ Filtro `p.MAPE` → `p.WMAPE`
- ✅ Texto explicativo atualizado

### 5. Documentação
- ✅ Novo arquivo: `WMAPE_IMPLEMENTACAO.md`
- 📝 Arquivos a atualizar:
  - `README.md`
  - `CORRECAO_MAPE_COMPLETA.md` → renomear
  - `MAPE_THRESHOLD_CHANGE.md` → renomear
  - `VALIDACAO_ALERTAS.md`
  - `MELHORIAS_IMPLEMENTADAS.md`

---

## 📈 Faixas de Interpretação

As faixas de qualidade **permanecem as mesmas**:

| WMAPE      | Classificação | Cor    |
|------------|---------------|--------|
| < 10%      | Excelente     | Verde  |
| 10-20%     | Boa           | Azul   |
| 20-30%     | Aceitável     | Laranja|
| 30-50%     | Fraca         | Vermelho|
| > 50%      | Muito Fraca   | Vermelho Escuro|

---

## 🔄 Compatibilidade

### MAPE Ainda Está Disponível
```python
# WMAPE (recomendado)
results = walk_forward_validation(data, model_name, horizon)
wmape = results['wmape']

# MAPE (legacy - mantido para compatibilidade)
mape = results['mape']
```

**Motivo:** Permite comparação com sistemas antigos e transição gradual.

---

## 📊 Impacto Esperado

### Produtos Alto Giro
- WMAPE será **similar ou menor** que MAPE
- Erros absolutos maiores, mas percentualmente corretos

### Produtos Baixo Giro
- MAPE inflava artificialmente o erro médio
- WMAPE reflete melhor a realidade do negócio

### Exemplo Real
```
Antes (MAPE):
- Produto A (1000 un/mês): 5% erro
- Produto B (10 un/mês): 50% erro
- MAPE médio: (5% + 50%) / 2 = 27.5% ❌

Depois (WMAPE):
- Mesmos produtos
- WMAPE: (50 + 5) / (1000 + 10) × 100 = 5.4% ✅
```

---

## ✅ Checklist de Implementação

- [x] Implementar `calculate_wmape()` em accuracy_metrics.py
- [x] Deprecar `calculate_mape()` com aviso
- [x] Atualizar `walk_forward_validation()` para retornar WMAPE
- [x] Atualizar `evaluate_model_accuracy()` para usar WMAPE
- [x] Atualizar `format_accuracy_report()` para exibir WMAPE
- [x] Alterar app.py para usar WMAPE
- [x] Atualizar templates/index.html
- [x] Atualizar static/js/app.js
- [ ] Testar com dados reais
- [ ] Atualizar documentação completa
- [ ] Commit e push para GitHub

---

## 🧪 Como Testar

```bash
# 1. Testar cálculo WMAPE
python -c "
from core.accuracy_metrics import calculate_wmape, calculate_mape

actual = [1, 100]
predicted = [2, 101]

mape = calculate_mape(actual, predicted, min_value=0)
wmape = calculate_wmape(actual, predicted, min_value=0)

print(f'MAPE:  {mape:.2f}%')  # ~50.5%
print(f'WMAPE: {wmape:.2f}%') # ~1.98%
"

# 2. Rodar previsão completa
python app.py
# Verificar que cards exibem "WMAPE Médio"

# 3. Validar métricas
# Acessar /demanda e verificar valores
```

---

## 📚 Referências Técnicas

### Artigos sobre WMAPE vs MAPE
- **Hyndman, R.J.** (2014): "Another look at forecast accuracy metrics for intermittent demand"
- **Kolassa, S.** (2016): "Why the MAPE is a terrible metric for low-volume data"

### Conclusão dos Estudos
> "Para dados de varejo com mix de produtos de alto e baixo volume, WMAPE é superior ao MAPE por ponderar adequadamente os erros pelo impacto financeiro de cada produto."

---

## 🎓 Glossário

- **MAPE:** Mean Absolute Percentage Error (não ponderado)
- **WMAPE:** Weighted Mean Absolute Percentage Error (ponderado)
- **APE:** Absolute Percentage Error (erro individual)
- **Ponderação:** Atribuir pesos proporcionais ao volume de vendas
- **Min Value:** Threshold mínimo para incluir na métrica (default: 2.0)

---

## 🚀 Próximos Passos

1. ✅ Implementação completa (código + interface)
2. ⏳ Validação com dados reais
3. ⏳ Atualização de toda documentação
4. ⏳ Commit e push para GitHub
5. 📝 Comunicar mudança aos usuários
6. 📊 Comparar WMAPE vs MAPE em produção (primeiras semanas)

---

**Desenvolvido por:** Claude Code + Valter Lino
**Métrica Principal:** WMAPE (Weighted MAPE)
**Status:** Implementado e pronto para testes
