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

## 🔄 Changelog v3.0

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

## 📖 Documentação Completa

- **[Documentacao_Sistema_Previsao_v3.0.docx](Documentacao_Sistema_Previsao_v3.0.docx)** - Manual completo (30+ páginas)
  - Visão geral do sistema
  - Métodos estatísticos detalhados
  - Telas e funcionalidades
  - Conceitos de reabastecimento
  - FAQ completo

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
R: Mínimo 12 meses. Ideal: 24+ meses para detecção de sazonalidade.

**P: Como funciona a classificação ABC?**
R: Automática baseada na demanda mensal média.

**P: Posso usar dados diários?**
R: Não. Agregue para mensal antes do upload.

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

**Versão:** 3.0
**Status:** Em Produção
**Última Atualização:** Dezembro 2024

**⭐ Se este projeto foi útil, considere dar uma estrela!**
