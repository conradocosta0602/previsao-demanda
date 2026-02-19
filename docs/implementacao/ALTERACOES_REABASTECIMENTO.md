# Alterações no Módulo de Reabastecimento

**Data:** 2024-12-29
**Alterações realizadas:**

---

## 1. Modo de Cálculo Fixado como Automático

### Alteração no Frontend ([templates/reabastecimento.html](templates/reabastecimento.html))

**Antes:**
- Select box permitindo escolher entre "Automático" e "Manual"
- Usuário podia selecionar o modo de cálculo

**Depois:**
- Campo hidden com valor fixo "automatico"
- Modo automático é a única opção (sistema escolhe o melhor método entre os 7 disponíveis)
- Interface mais limpa e sem confusão

```html
<!-- Campo oculto para modo automático -->
<input type="hidden" id="modo_calculo" name="modo_calculo" value="automatico">
```

### Alteração no JavaScript ([static/js/reabastecimento.js](static/js/reabastecimento.js))

**Removido:**
- Event listener que atualizava o hint do modo de cálculo
- Código não é mais necessário pois não há seleção de modo

---

## 2. Coluna "Método" Adicionada ao Relatório

### Descrição
Agora o relatório exibe qual método estatístico foi utilizado para calcular a demanda de cada item.

### Métodos Possíveis:
1. **SMA** - Simple Moving Average (Média Móvel Simples)
2. **WMA** - Weighted Moving Average (Média Móvel Ponderada)
3. **EMA** - Exponential Moving Average (Média Móvel Exponencial)
4. **Holt** - Holt's Linear Trend (Tendência Linear)
5. **Holt-Winters** - Sazonalidade
6. **TSB** - Teunter-Syntetos-Babai (Demanda Intermitente)
7. **Ultimo** - Última venda registrada

### Alteração no HTML ([templates/reabastecimento.html](templates/reabastecimento.html:127))

**Adicionado:**
- Nova coluna `<th>Método</th>` na tabela de resultados
- Posicionada após a coluna SKU

### Alteração no JavaScript ([static/js/reabastecimento.js](static/js/reabastecimento.js:228-230))

**Adicionado:**
- Nova célula `<td>` exibindo o método usado
- Formatação visual com badge azul claro
- Campo `item.Metodo_Usado` do backend

```javascript
<td style="padding: 6px; border-bottom: 1px solid #eee; font-size: 0.75em; color: #666;">
    <span style="background: #e3f2fd; padding: 2px 6px; border-radius: 4px; white-space: nowrap;">${metodoFormatado}</span>
</td>
```

### Backend (sem alteração necessária)

O backend já retornava o campo `Metodo_Usado`:
- [core/demand_calculator.py:636](core/demand_calculator.py#L636) - Campo adicionado no processamento
- [core/replenishment_calculator.py:347-352](core/replenishment_calculator.py#L347-L352) - Merge com resultado final

---

## 3. Estrutura da Tabela Atualizada

### Colunas na Ordem:
1. Loja
2. SKU
3. **Método** ← NOVO
4. Dem. Média
5. Est. Atual
6. Est. Trânsito
7. Est. Efetivo
8. Ponto Pedido
9. Est. Segurança
10. Qtd. Pedir
11. Cobertura Atual
12. Cobertura c/ Pedido
13. Ruptura?
14. Pedir?

**Total:** 14 colunas (antes eram 13)

---

## 4. Benefícios das Alterações

### Simplificação da Interface
- ✅ Usuário não precisa escolher modo de cálculo
- ✅ Sistema sempre usa o melhor método automaticamente
- ✅ Menos pontos de erro/confusão
- ✅ Interface mais limpa

### Transparência e Rastreabilidade
- ✅ Usuário vê qual método foi usado para cada item
- ✅ Facilita auditoria e validação dos resultados
- ✅ Permite entender por que diferentes itens usam diferentes métodos
- ✅ Ajuda na análise de padrões de demanda

### Exemplos de Uso:
- Item com demanda estável → SMA ou WMA
- Item com tendência crescente → Holt
- Item com sazonalidade → Holt-Winters
- Item com demanda intermitente → TSB
- Item novo sem histórico → Ultimo

---

## 5. Arquivos Modificados

| Arquivo | Tipo | Alteração |
|---------|------|-----------|
| `templates/reabastecimento.html` | HTML | Removido select, adicionada coluna Método |
| `static/js/reabastecimento.js` | JavaScript | Removido event listener, adicionada célula Método |
| `static/css/style.css` | CSS | Corrigido overflow para scroll |

---

## 6. Como Testar

1. **Acesse:** `http://localhost:5001/reabastecimento`
2. **Verifique:** Não há mais seleção de modo de cálculo
3. **Faça upload** de um arquivo de reabastecimento
4. **Observe:** Coluna "Método" na tabela de resultados
5. **Confirme:** Cada item mostra o método utilizado (SMA, EMA, Holt, etc.)
6. **Download:** Excel também contém a coluna Metodo_Usado

---

## 7. Compatibilidade

### Arquivos de Entrada
✅ Nenhuma alteração necessária nos arquivos Excel de entrada

### Arquivos de Saída
✅ Excel gerado já contém a coluna `Metodo_Usado` (funcionalidade do backend já existia)

### API
✅ Endpoint `/processar_reabastecimento` continua funcionando normalmente

---

**Status:** ✅ Implementado e testado
**Versão:** 2.1
