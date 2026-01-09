# Sistema de Previsão de Demanda e Reabastecimento v3.0

Sistema completo para gestão de estoque multi-loja com Centro de Distribuição (CD), combinando métodos estatísticos avançados, machine learning e cálculos de reabastecimento baseados em níveis de serviço.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 📋 Características Principais

### 🔮 Previsão de Demanda
- **6 Métodos Estatísticos:**
  - Simple Moving Average (SMA) com janela adaptativa
  - Weighted Moving Average (WMA) adaptativo
  - Simple Exponential Smoothing (SES)
  - Linear Regression Forecast
  - TSB (Trigg and Leach Smoothing with BIAS)
  - Decomposição Sazonal Mensal (Híbrida)

- **Seleção Automática Inteligente:**
  - **Modo AUTO:** Baseado em características da demanda (CV, tendência, sazonalidade)
  - **Modo ML:** Machine Learning (Random Forest) com 15+ features

### 🎯 Recursos Avançados

#### 🔍 Detecção Automática
- **Sazonalidade:** Autocorrelação com lag de 12 meses
- **Outliers:** Métodos IQR e Z-Score com substituição automática
- **Tendências:** Análise de slope e R²

#### 📊 Métricas e Alertas
- **WMAPE:** Weighted Mean Absolute Percentage Error (acurácia ponderada por volume)
- **BIAS:** Tendência sistemática de erro
- **Alertas Inteligentes:** 4 níveis (🔴 Crítico, 🟡 Alerta, 🔵 Atenção, 🟢 Normal)
- **YoY:** Comparação Year-over-Year

#### 🛠️ Funcionalidades Operacionais
- **Calendário Promocional:** Ajuste automático para eventos
- **Simulador de Cenários:** What-If Analysis
- **Logging Completo:** Auditoria de decisões
- **Séries Curtas:** Tratamento especializado

### 📦 Reabastecimento

#### 3 Fluxos Suportados
1. **Fornecedor → CD/Loja**
   - Lead time do fornecedor
   - Ciclo de pedido
   - Múltiplos de palete/carreta

2. **CD → Loja**
   - Lead time interno
   - Priorização por criticidade

3. **Transferências entre Lojas**
   - Identifica excesso vs ruptura
   - Otimiza redistribuição

#### Cálculos Implementados
- **Estoque de Segurança:** `SS = Z × σ × √LT`
- **Ponto de Pedido:** `ROP = (Demanda × LT) + SS`
- **Nível de Serviço ABC:**
  - Classe A (>500 un/mês): 98%
  - Classe B (100-500 un/mês): 95%
  - Classe C (<100 un/mês): 90%

## 🚀 Instalação Rápida

### Pré-requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo

1. **Clone o repositório:**
```bash
git clone https://github.com/conradocosta0602/previsao-demanda.git
cd previsao-demanda
```

2. **Instale as dependências:**
```bash
pip install flask pandas numpy scikit-learn statsmodels python-docx openpyxl
```

Ou usando requirements.txt (se disponível):
```bash
pip install -r requirements.txt
```

3. **Execute o sistema:**
```bash
python app.py
```

4. **Acesse no navegador:**
```
http://localhost:5000
```

## 📖 Como Usar

### 1️⃣ Previsão de Demanda

1. Acesse a tela principal
2. Faça upload do arquivo Excel com histórico de vendas
   - **Colunas necessárias:** `Local`, `SKU`, `Ano`, `Mes_Numero`, `Quantidade`
3. Configure meses de previsão (1-24)
4. Clique em "Processar"
5. Analise resultados: cards, tabela YoY, gráfico, alertas
6. Download do Excel com previsões

### 2️⃣ Cadastrar Eventos (Opcional)

1. Acesse "Gerenciar Eventos"
2. Cadastre eventos promocionais (Black Friday, Natal, etc.)
3. Configure impacto esperado (%)
4. Sistema ajusta previsões automaticamente

### 3️⃣ Calcular Pedidos

1. **Escolha o fluxo:**
   - Pedidos ao Fornecedor
   - Pedidos CD → Loja
   - Transferências entre Lojas

2. Upload do arquivo com estoque atual e parâmetros
3. Revise pedidos sugeridos
4. Download do Excel de pedidos

### 4️⃣ Simulador (Opcional)

1. Acesse "Simulador de Cenários"
2. Teste diferentes parâmetros
3. Compare resultados

## 📁 Estrutura do Projeto

```
previsao-demanda/
├── app.py                          # Aplicação Flask principal
├── core/                           # Módulos principais
│   ├── forecasting_models.py      # 6 métodos de previsão
│   ├── method_selector.py         # Seleção automática
│   ├── ml_selector.py             # Machine Learning
│   ├── seasonality_detector.py    # Detecção de sazonalidade
│   ├── outlier_detector.py        # Detecção de outliers
│   ├── auto_logger.py             # Logging automático
│   ├── smart_alerts.py            # Alertas inteligentes
│   ├── event_manager.py           # Gerenciador de eventos
│   ├── scenario_simulator.py      # Simulador
│   └── replenishment_calculator.py # Reabastecimento
├── templates/                      # Templates HTML
│   ├── index.html                 # Previsão
│   ├── pedido_fornecedor.html     # Pedidos fornecedor
│   ├── pedido_cd.html             # Pedidos CD
│   ├── transferencias.html        # Transferências
│   ├── eventos_simples.html       # Eventos
│   └── simulador.html             # Simulador
├── static/
│   ├── css/style.css              # Estilos
│   └── js/                        # JavaScript
├── Documentacao_Sistema_Previsao_v3.0.docx  # Manual completo
├── Sugestoes_Melhoria_Sistema_Previsao_Atualizado.docx
└── README.md                       # Este arquivo
```

## 📊 Formato de Arquivos

### Histórico de Vendas
```
Local,SKU,Ano,Mes_Numero,Quantidade
LOJA_01,PROD001,2023,1,150
LOJA_01,PROD001,2023,2,180
```

### Pedidos ao Fornecedor
```
Fornecedor,SKU,Destino,Tipo_Destino,Lead_Time_Dias,Ciclo_Pedido_Dias,Custo_Unitario,Estoque_Disponivel
FORN_A,PROD001,CD_PRINCIPAL,CD,30,30,15.50,200
```

## 🔄 Changelog v3.1

### Melhorias Críticas Implementadas ✅

1. ✅ **Correção do Cálculo YoY** - Comparação correta mesmo período ano anterior
2. ✅ **Interface Reorganizada** - Layout executivo, tabela acima do gráfico
3. ✅ **Exibição de Custos** - Custo unitário sempre visível
4. ✅ **Modelo Sazonal Corrigido** - Híbrido (sazonalidade + tendência)
5. ✅ **Compatibilidade ML Selector** - Aliases completos
6. ✅ **Detecção Automática de Sazonalidade** - Autocorrelação lag 12
7. ✅ **Detecção de Outliers** - IQR e Z-Score
8. ✅ **Logging de Seleção AUTO** - Auditoria completa
9. ✅ **Alertas Inteligentes** - 4 níveis visuais
10. ✅ **Machine Learning** - Random Forest com 15+ features
11. ✅ **Calendário Promocional** - Ajuste automático
12. ✅ **Tratamento Séries Curtas** - Estratégias especializadas

### Novas Melhorias v3.1 (Janeiro 2026) ✅

13. ✅ **Escala Dinâmica de Gráficos** - Y-axis se ajusta automaticamente aos dados
14. ✅ **Ajuste Sazonal Baseado em Granularidade** - Fatores sazonais sempre calculados
15. ✅ **Correção de Previsões Planas** - Variação mês a mês garantida
16. ✅ **Ajuste Automático da Tabela YoY** - Períodos comparativos sincronizados
17. ✅ **Separação de Conceitos** - tamanho_validacao_futura vs meses_previsao
18. ✅ **Aplicação de Ajuste Sazonal no Teste** - Período de teste também ajustado
19. ✅ **Correção de Número de Períodos** - Conversão correta meses→semanas/dias (6 meses = 24 semanas)
20. ✅ **Cabeçalhos Dinâmicos na Tabela** - S1, S2 para semanal; Jan, Fev para mensal
21. ✅ **Queries SQL Consistentes** - Mesmo intervalo de datas entre granularidades
22. ✅ **Logging Detalhado de Previsões** - Total base, ajustes e previsão final
23. ✅ **Documentação de Granularidade** - Guia completo sobre diferenças esperadas
24. ✅ **🔴 CRÍTICO: Sazonalidade Anual Semanal (52 semanas)** - Semana 50 agora influenciada por semanas 50 históricas

## 📖 Documentação Completa

- **[Documentacao_Sistema_Previsao_v3.0.docx](Documentacao_Sistema_Previsao_v3.0.docx)** - Manual completo (30+ páginas)
  - Visão geral do sistema
  - Métodos estatísticos detalhados
  - Telas e funcionalidades
  - Conceitos de reabastecimento
  - FAQ completo

- **[GRANULARIDADE_E_PREVISOES.md](GRANULARIDADE_E_PREVISOES.md)** - ⚠️ **LEITURA OBRIGATÓRIA**
  - Por que previsões variam entre granularidades (mensal/semanal/diária)
  - Diferenças esperadas e aceitáveis
  - Recomendações de uso por caso de negócio
  - Validação e interpretação de resultados

- **[CORRECAO_SAZONALIDADE_ANUAL_SEMANAL.md](CORRECAO_SAZONALIDADE_ANUAL_SEMANAL.md)** - 🔴 **CORREÇÃO CRÍTICA v3.1.2**
  - Mudança de ciclo artificial de 4 semanas para sazonalidade anual de 52 semanas
  - Amplitude aumentou de 1.8% para 31.27%
  - Cada semana agora tem seu próprio padrão histórico
  - Requer mínimo de 52 semanas (1 ano) de dados históricos

- **[Sugestoes_Melhoria_Sistema_Previsao_Atualizado.docx](Sugestoes_Melhoria_Sistema_Previsao_Atualizado.docx)** - Status das melhorias

## 🛠️ Requisitos Técnicos

```
Python 3.8+
Flask 3.0.0
Pandas 2.1.3
NumPy 1.26.2
Scikit-learn 1.3.2
Statsmodels 0.14.0
python-docx 1.1.0
openpyxl 3.1.2
```

## ❓ FAQ

**P: Qual método devo usar: AUTO ou ML?**
R: Use ML para melhor precisão. AUTO é mais rápido para análises exploratórias.

**P: Quantos meses de histórico preciso?**
R:
- Mensal: Mínimo 12 meses. Ideal: 24+ meses para detecção de sazonalidade.
- Semanal: Mínimo 52 semanas (1 ano). Recomendado: 104 semanas (2 anos) para melhor qualidade.
- Diária: Mínimo 365 dias. Ideal: 730+ dias.

**P: Como funciona a classificação ABC?**
R: Automática baseada na demanda mensal média.

**P: Por que previsões mensais e semanais dão resultados diferentes?**
R: ⚠️ **IMPORTANTE:** Diferenças de 5-15% são normais e esperadas ao mudar granularidade. Consulte [GRANULARIDADE_E_PREVISOES.md](GRANULARIDADE_E_PREVISOES.md) para detalhes.

**P: Qual granularidade devo usar?**
R: Mensal para planejamento estratégico, Semanal para reabastecimento, Diária para operações day-to-day.

## 🤝 Contribuição

Contribuições são bem-vindas!

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob licença MIT. Veja [LICENSE](LICENSE) para mais detalhes.

## 👥 Autores

- **Valter Lino** ([@valterlino01](https://github.com/valterlino01)) - Desenvolvedor Principal
- **Conrado Costa** ([@conradocosta0602](https://github.com/conradocosta0602)) - Co-desenvolvedor
- **Consultoria Técnica:** Claude Sonnet 4.5 (Anthropic)

## 📞 Suporte

Para dúvidas ou problemas:
- 📖 Consulte a documentação completa
- 🐛 Abra uma [issue](https://github.com/conradocosta0602/previsao-demanda/issues)
- 💬 Entre em contato via GitHub

## 🌟 Features Planejadas

- [ ] API REST para integração
- [ ] Dashboard Power BI
- [ ] Exportação de gráficos
- [ ] Versionamento de previsões
- [ ] Modo batch para grandes volumes

---

## 📝 Detalhamento das Melhorias v3.1

### 1. Escala Dinâmica de Gráficos
**Problema resolvido:** Gráficos com escala fixa iniciando em zero desperdiçavam espaço visual e dificultavam a leitura de variações.

**Solução implementada:**
- Cálculo automático de min/max com margem de 10%
- Aplicado em 3 gráficos: Previsão, Agregação de Demanda, Comparação YoY
- Arquivo: `static/js/app.js` (linhas 1440-1509, 349-459, 491-587)

### 2. Ajuste Sazonal Baseado em Granularidade
**Problema resolvido:** Previsões mostravam valores idênticos para todos os meses quando sazonalidade não era estatisticamente significativa.

**Solução implementada:**
- Fatores sazonais SEMPRE calculados baseado na granularidade solicitada
- Mensal: 12 fatores (um por mês)
- Semanal: 7 fatores (um por dia da semana)
- Diário: 7 fatores (um por dia da semana)
- Arquivo: `app.py` (linhas 2511-2568)

**Resultado:**
- Alimentos (6 meses): Variação de 92.210 a 100.179 (amplitude: 8.64%)
- TODAS (12 meses): Variação de 309.229 a 350.062 (amplitude: 13.20%)

### 3. Correção de Previsões Planas
**Problema resolvido:** Condição `if periodo_sazonal == 12 and granularidade == 'mensal'` era muito restritiva, resultando em `fatores_sazonais = {}`.

**Solução implementada:**
- Lógica alterada para calcular fatores independente da detecção estatística
- Ajuste sazonal aplicado também no período de teste
- Proteção contra index out of range com `min(len(datas), len(serie))`

### 4. Ajuste Automático da Tabela YoY
**Problema resolvido:** Tabela comparativa mostrava todos os 12 meses do ano anterior mesmo quando previsão era de 6 meses.

**Solução implementada:**
- Loop limitado a `numPeriodos` (número de períodos de previsão)
- Arquivo: `static/js/app.js` (linhas 1323-1333)
- Sincronização automática entre previsão e dados reais

### 5. Separação de Conceitos
**Problema resolvido:** Confusão entre períodos de validação histórica e períodos de previsão futura.

**Solução implementada:**
- `tamanho_validacao_futura`: Períodos restantes nos dados históricos para comparação YoY
- `meses_previsao`: Períodos futuros a prever além dos dados históricos
- Arquivo: `app.py` (linhas 2459-2471)

### 6. Aplicação de Ajuste Sazonal no Teste
**Problema resolvido:** Ajuste sazonal só era aplicado às previsões futuras, não ao período de teste.

**Solução implementada:**
- Ajuste sazonal aplicado também às previsões do período de teste
- Garante consistência entre teste e previsão futura
- Arquivo: `app.py` (linhas 2591-2623)

### 7. Correção de Número de Períodos por Granularidade
**Problema resolvido:** Ao solicitar "6 meses" com granularidade semanal, sistema gerava apenas 6 semanas em vez de 24 semanas (~6 meses).

**Solução implementada:**
```python
# Conversão de meses para períodos baseado na granularidade
if granularidade == 'semanal':
    periodos_previsao = meses_previsao * 4  # 4 semanas por mês
elif granularidade == 'diario':
    periodos_previsao = meses_previsao * 30  # ~30 dias por mês
else:  # mensal
    periodos_previsao = meses_previsao
```
- Arquivo: `app.py` (linhas 2258-2268)
- Substituição de `meses_previsao` por `periodos_previsao` em 7 locais críticos
- Log: "Periodos de previsao: 24 (6 meses em granularidade semanal)"

**Resultado:** 6 meses agora gera corretamente 6 períodos mensais, 24 períodos semanais ou 180 períodos diários.

### 8. Cabeçalhos Dinâmicos na Tabela Comparativa
**Problema resolvido:** Tabela YoY sempre mostrava nomes de meses (Jan, Fev) independente da granularidade.

**Solução implementada:**
```javascript
if (granularidade === 'semanal') {
    const semanaAno = getWeekNumber(data);
    nomePeriodo = `S${semanaAno}`;  // S1, S2, S3...
} else if (granularidade === 'diaria') {
    nomePeriodo = `${data.getDate()}/${data.getMonth() + 1}`;  // 15/01
} else {
    nomePeriodo = meses[data.getMonth()];  // Jan, Fev
}
```
- Arquivo: `static/js/app.js` (linhas 1287-1321)
- Adicionada função `getWeekNumber` para cálculo ISO de semana
- Tabela agora exibe corretamente S1-S52 para semanal, dias para diário

### 9. Queries SQL Consistentes entre Granularidades
**Problema resolvido:** `DATE_TRUNC('week')` e `DATE_TRUNC('month')` capturavam intervalos diferentes de datas, resultando em totais históricos divergentes (3,913k vs 3,957k = 1.1% diferença).

**Solução implementada:**
```sql
-- Query semanal agora usa CTE para garantir mesmo intervalo
WITH dados_diarios AS (
    SELECT h.data, SUM(h.qtd_venda) as qtd_venda
    FROM historico_vendas_diario h
    WHERE h.data >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY h.data
)
SELECT DATE_TRUNC('week', data)::date as data,
       SUM(qtd_venda) as qtd_venda
FROM dados_diarios
GROUP BY DATE_TRUNC('week', data)
```
- Arquivo: `app.py` (linhas 2311-2334, 2388-2408)
- Garante que agregação semanal usa apenas dias dentro do intervalo de 2 anos
- Mesma lógica aplicada para query do ano anterior

### 10. Logging Detalhado de Previsões e Ajustes
**Problema resolvido:** Difícil diagnosticar diferenças entre granularidades sem visibilidade dos valores intermediários.

**Solução implementada:**
```python
# Logs adicionados em pontos críticos
print(f"Total dados históricos (últimos 2 anos): {total:,.2f} em {n} períodos")
print(f"Total da série completa: {total:,.2f}")
print(f"Valores dos fatores mensais: {dict(sorted(fatores_sazonais.items()))}")
print(f"Previsão base (sem ajuste): Total={total:,.2f}, Média={media:,.2f}")
print(f"Total previsto para {n} períodos: {total:,.2f}")
```
- Arquivo: `app.py` (linhas 2352-2355, 2490-2494, 2547, 2569, 2698-2701, 2744-2746)
- Rastreamento completo: dados históricos → série limpa → previsão base → ajustes sazonais → previsão final

**Resultado:** Possibilita análise detalhada do fluxo de previsão e identificação precisa de divergências.

### 11. Documentação Completa sobre Granularidade
**Problema resolvido:** Usuários não entendiam por que previsões mensais e semanais divergiam em 5-15%.

**Solução implementada:**
- Criado documento [GRANULARIDADE_E_PREVISOES.md](GRANULARIDADE_E_PREVISOES.md) com:
  - Explicação técnica das causas (janelas adaptativas, agregação, fatores sazonais)
  - Tabelas de diferenças esperadas vs problemáticas
  - Recomendações por caso de uso (estratégico, operacional, day-to-day)
  - FAQ e exemplos práticos
- Adicionado FAQ no README sobre granularidade
- Marcado como "LEITURA OBRIGATÓRIA" na seção de documentação

**Resultado:** Transparência total sobre comportamento do sistema e expectativas corretas para usuários.

### 12. 🔴 CRÍTICO: Sazonalidade Anual Semanal (52 semanas) - v3.1.2
**Problema resolvido:** Previsões semanais usavam ciclo artificial de 4 semanas em vez de sazonalidade anual de 52 semanas. Semana 50 da previsão era comparada com semanas 2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46 (semana % 4).

**Solução implementada:**
```python
# ANTES (INCORRETO)
posicao_ciclo = semana_ano % 4  # 0, 1, 2 ou 3
chave_sazonal = posicao_ciclo

# DEPOIS (CORRETO)
semana_ano = data_previsao.isocalendar()[1]  # 1-52/53
chave_sazonal = semana_ano  # Usar semana do ano diretamente
```
- Mudança de 4 fatores sazonais para 52 fatores (um por semana do ano)
- Análogo à granularidade mensal: 12 meses → 12 fatores | 52 semanas → 52 fatores
- Arquivo: `app.py` (linhas 2581-2601, 2663-2668, 2750-2755)
- Requisito mínimo aumentado de 4 para 52 semanas de dados históricos

**Métricas ANTES vs DEPOIS:**
| Métrica | ANTES (4 semanas) | DEPOIS (52 semanas) | Melhoria |
|---------|-------------------|---------------------|----------|
| Fatores sazonais | 4 | 52 | +1200% |
| Amplitude dos fatores | 1.8% | 31.27% | +17x |
| Valores únicos (48 períodos) | ~4 | 43 | +975% |
| Realismo | Linear/Artificial | Natural/Histórico | ✅ |

**Resultado:** Semana 50 da previsão agora é influenciada pela média histórica de TODAS as semanas 50 dos anos anteriores, respeitando tendências e sazonalidades reais. Documentação completa: [CORRECAO_SAZONALIDADE_ANUAL_SEMANAL.md](CORRECAO_SAZONALIDADE_ANUAL_SEMANAL.md)

---

**Versão:** 3.1.2
**Status:** Em Produção
**Última Atualização:** Janeiro 2026

**⭐ Se este projeto foi útil, considere dar uma estrela!**
