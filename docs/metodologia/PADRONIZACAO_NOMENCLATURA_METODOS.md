# Padronização de Nomenclatura dos Métodos

**Data:** 2024-12-29
**Objetivo:** Padronizar a nomenclatura dos métodos estatísticos conforme o documento "Sistema_Previsao_Demanda_Reabastecimento.docx"

---

## Mapeamento de Nomes

### Nome Técnico (Backend) → Nome Padronizado (Documento)

| Nome Técnico | Nome Padronizado (Exibição) | Seção do Documento |
|--------------|------------------------------|-------------------|
| `sma` | **SMA (Média Móvel Simples)** | 2.2. Método 1 |
| `wma` | **WMA (Média Móvel Ponderada)** | 2.3. Método 2 |
| `ema` | **EMA (Média Móvel Exponencial)** | 2.4. Método 3 |
| `tendencia` | **Regressão com Tendência** | 2.5. Método 4 |
| `sazonal` | **Decomposição Sazonal** | 2.6. Método 5 |
| `tsb` | **TSB (Teunter-Syntetos-Babai)** | 2.7. Método 6 |
| `ultimo` | **Última Venda** | - |
| `auto_estavel` | **AUTO (Seleção Automática)** | 2.8. Método 7 |
| `nenhum` | **Sem Dados** | - |

---

## Implementação

### Arquivo: [static/js/reabastecimento.js](static/js/reabastecimento.js:6-17)

```javascript
// Mapeamento de nomes técnicos para nomenclatura do documento
const METODOS_NOMENCLATURA = {
    'sma': 'SMA (Média Móvel Simples)',
    'wma': 'WMA (Média Móvel Ponderada)',
    'ema': 'EMA (Média Móvel Exponencial)',
    'tendencia': 'Regressão com Tendência',
    'sazonal': 'Decomposição Sazonal',
    'tsb': 'TSB (Teunter-Syntetos-Babai)',
    'ultimo': 'Última Venda',
    'auto_estavel': 'AUTO (Seleção Automática)',
    'nenhum': 'Sem Dados'
};
```

### Uso na Renderização: [static/js/reabastecimento.js](static/js/reabastecimento.js:220-222)

```javascript
// Formatar nome do método usando nomenclatura do documento
const metodoTecnico = (item.Metodo_Usado || 'nenhum').toLowerCase();
const metodoFormatado = METODOS_NOMENCLATURA[metodoTecnico] || item.Metodo_Usado || 'N/A';
```

---

## Descrição dos Métodos (conforme documento)

### 1. SMA (Média Móvel Simples)
**Quando usar:** Demanda estável sem tendência ou sazonalidade
- Calcula a média dos últimos N períodos
- Janela adaptativa baseada no tamanho do histórico
- Ideal para padrões regulares

### 2. WMA (Média Móvel Ponderada)
**Quando usar:** Demanda estável com necessidade de maior peso para dados recentes
- Atribui pesos maiores para períodos mais recentes
- Mais responsivo a mudanças do que SMA
- Mantém estabilidade

### 3. EMA (Média Móvel Exponencial)
**Quando usar:** Demanda com mudanças graduais
- Suavização exponencial
- Responde rapidamente a mudanças
- Mantém histórico completo com decaimento

### 4. Regressão com Tendência
**Quando usar:** Demanda com tendência clara (crescente ou decrescente)
- Ajusta linha de tendência linear
- Projeta crescimento/decrescimento
- Usa método de Holt (suavização dupla)

### 5. Decomposição Sazonal
**Quando usar:** Demanda com padrões sazonais
- Identifica componentes: nível + tendência + sazonalidade
- Requer mínimo de 12 períodos
- Usa Holt-Winters

### 6. TSB (Teunter-Syntetos-Babai)
**Quando usar:** Demanda intermitente (muitos zeros)
- Especializado para vendas esporádicas
- Calcula probabilidade de demanda
- Estima tamanho médio quando ocorre

### 7. AUTO (Seleção Automática)
**Quando usar:** Sempre que possível (modo recomendado)
- Sistema analisa o padrão de demanda
- Testa múltiplos métodos
- Escolhe o de melhor performance via validação cruzada

### Última Venda
**Quando usar:** Histórico muito limitado (< 3 períodos)
- Fallback quando não há dados suficientes
- Usa a última venda como previsão
- Desvio padrão baseado na própria venda

### Sem Dados
**Quando usar:** Nenhum histórico disponível
- Item novo sem vendas
- Demanda = 0, Desvio = 0
- Requer entrada manual ou aguardar histórico

---

## Exibição na Interface

### Tela de Reabastecimento

A coluna "Método" agora exibe:

**Antes (nome técnico):**
- `sma`
- `tendencia`
- `tsb`

**Depois (nome padronizado):**
- `SMA (Média Móvel Simples)`
- `Regressão com Tendência`
- `TSB (Teunter-Syntetos-Babai)`

### Formatação Visual

```html
<span style="background: #e3f2fd; padding: 2px 6px; border-radius: 4px; white-space: nowrap;">
    SMA (Média Móvel Simples)
</span>
```

- Fundo azul claro (`#e3f2fd`)
- Badge arredondado
- Texto compacto (0.75em)
- Sem quebra de linha

---

## Relatório Excel

O arquivo Excel de saída contém a coluna `Metodo_Usado` com o **nome técnico** (backend).

**Exemplo:**
```
| Loja    | SKU      | Metodo_Usado | Demanda_Media_Mensal | ... |
|---------|----------|--------------|----------------------|-----|
| LOJA_01 | PROD_001 | sma          | 125.5                | ... |
| LOJA_01 | PROD_002 | tendencia    | 89.3                 | ... |
| LOJA_02 | PROD_001 | tsb          | 15.2                 | ... |
```

**Observação:** O Excel mantém o nome técnico para compatibilidade e rastreabilidade. A conversão para nome padronizado ocorre apenas na interface web.

---

## Benefícios da Padronização

### 1. Alinhamento com Documentação
✅ Nomes exibidos correspondem exatamente ao documento oficial
✅ Facilita o entendimento para usuários que leram a documentação
✅ Elimina ambiguidade entre termos técnicos e nomes descritivos

### 2. Clareza para Usuários Finais
✅ Nomes completos são mais informativos
✅ Siglas acompanhadas de descrição completa
✅ Mais fácil para não-técnicos compreenderem

### 3. Rastreabilidade
✅ Backend mantém nomes técnicos (simples e consistentes)
✅ Frontend exibe nomes amigáveis
✅ Mapeamento claro e centralizado

### 4. Manutenibilidade
✅ Mudanças de nomenclatura em um único local (objeto METODOS_NOMENCLATURA)
✅ Fácil adicionar novos métodos
✅ Código limpo e organizado

---

## Compatibilidade

### Arquivos Antigos
✅ Relatórios Excel antigos continuam funcionando
✅ Coluna `Metodo_Usado` mantém formato técnico
✅ Interface converte automaticamente

### API
✅ Endpoint `/processar_reabastecimento` não foi alterado
✅ JSON retornado mantém campo `Metodo_Usado` com nome técnico
✅ Conversão ocorre apenas no JavaScript do frontend

---

**Status:** ✅ Implementado
**Impacto:** Frontend (JavaScript)
**Versão:** 2.1
