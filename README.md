# Sistema de Previsao de Demanda V2

Sistema completo de previsao de demanda para varejo com multiplas lojas e Centro de Distribuicao (CD).

## Funcionalidades

- Upload de arquivo Excel com historico de vendas
- Tratamento automatico de rupturas de estoque (stockouts)
- Selecao automatica do melhor metodo estatistico por (Loja + SKU) e (CD + SKU)
- Previsoes mensais configuraves
- Exportacao de resultados em Excel com multiplas abas
- Interface web intuitiva (sem terminal)

## Estrutura do Projeto

```
Previsao de Demanda V2/
├── app.py                    # Aplicacao Flask principal
├── core/                     # Modulos de processamento
│   ├── data_loader.py       # Carrega e valida dados
│   ├── stockout_handler.py  # Trata rupturas de estoque
│   ├── forecasting_models.py # Modelos de previsao
│   ├── method_selector.py   # Selecao automatica de metodo
│   ├── aggregator.py        # Agregacao para CD
│   └── reporter.py          # Geracao de relatorios Excel
├── templates/               # Templates HTML
├── static/                  # CSS e JavaScript
├── uploads/                 # Arquivos enviados
├── outputs/                 # Resultados gerados
├── tests/                   # Dados de teste
│   └── dados_teste.xlsx
├── requirements.txt
└── README.md
```

## Instalacao

1. Clone ou baixe o projeto

2. Instale as dependencias:
```bash
pip install -r requirements.txt
```

## Como Usar

1. Execute o servidor:
```bash
python app.py
```

2. Acesse no navegador:
```
http://localhost:5000
```

3. Faca upload do seu arquivo Excel

4. Configure os parametros de previsao

5. Clique em "Processar Previsao"

6. Baixe o Excel com os resultados

## Formato do Arquivo de Entrada

O arquivo Excel deve conter as seguintes colunas:

| Coluna | Descricao | Exemplo |
|--------|-----------|---------|
| Mes | Periodo (YYYY-MM) | 2024-01 |
| Loja | Codigo da loja (L01-L09) | L01 |
| SKU | Codigo do produto | PROD_001 |
| Vendas | Quantidade vendida | 150 |
| Dias_Com_Estoque | Dias com produto disponivel | 28 |
| Origem | Origem do produto | CD ou DIRETO |

## Metodos de Previsao

O sistema seleciona automaticamente o melhor metodo:

| Metodo | Quando Usar |
|--------|-------------|
| Media Movel Simples | Demanda estavel |
| Suavizacao Exponencial | Demanda com volatilidade moderada |
| Holt | Demanda com tendencia |
| Holt-Winters | Demanda com tendencia e sazonalidade |
| Croston/SBA/TSB | Demanda intermitente |
| Regressao Linear | Tendencia linear forte |

## Saida do Sistema

O Excel gerado contem as seguintes abas:

1. **RESUMO_EXECUTIVO** - Visao geral dos resultados
2. **PREVISAO_LOJAS** - Previsoes por loja e SKU
3. **PREVISAO_CD** - Previsoes agregadas do CD
4. **METODOS_UTILIZADOS** - Detalhes dos metodos selecionados
5. **ANALISE_RUPTURAS** - Metricas de stockout
6. **CARACTERISTICAS_DEMANDA** - Analise das series temporais

## Testando com Dados de Exemplo

Use o arquivo `tests/dados_teste.xlsx` incluso para testar o sistema.

Para regenerar os dados de teste:
```bash
python gerar_dados_teste.py
```

## Requisitos

- Python 3.8+
- Flask 3.0.0
- pandas 2.1.3
- numpy 1.26.2
- openpyxl 3.1.2
- scipy 1.11.4
- scikit-learn 1.3.2
- matplotlib 3.8.2

## Troubleshooting

### Erro "Colunas faltantes"
Verifique se seu arquivo tem todas as colunas obrigatorias: Mes, Loja, SKU, Vendas, Dias_Com_Estoque, Origem

### Erro "Dados insuficientes"
O sistema precisa de pelo menos 3 meses de historico por combinacao Loja+SKU

### Erro de upload
Verifique se o arquivo e .xlsx ou .xls e tem menos de 16MB
