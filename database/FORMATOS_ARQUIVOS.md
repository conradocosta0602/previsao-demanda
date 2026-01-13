# 📋 Formatos de Arquivos para Importação

**Versão:** 1.0
**Data:** Janeiro 2026
**Formatos Aceitos:** CSV, XLSX, XLS

---

## 📁 Onde Colocar os Arquivos?

Coloque todos os seus arquivos na pasta:
```
C:\Users\valter.lino\Desktop\Treinamentos\VS\previsao-demanda\data_import\
```

---

## 📝 Regras Gerais

### Nomes dos Arquivos
O script aceita qualquer uma destas extensões para cada arquivo:
- `.csv` (recomendado para grandes volumes)
- `.xlsx` (Excel moderno)
- `.xls` (Excel antigo)

**Exemplo:**
- ✅ `cadastro_produtos.csv`
- ✅ `cadastro_produtos.xlsx`
- ✅ `cadastro_produtos.xls`

### Nomes das Colunas
- **Case insensitive:** Tanto `Codigo` quanto `codigo` funcionam
- **Espaços:** São convertidos automaticamente para `_`
  - `Cod Empresa` → `cod_empresa`
- **Obrigatórias:** Marcadas com ⭐ abaixo

### Datas
- Formato aceito: `YYYY-MM-DD` (2024-01-15)
- Também aceita: `DD/MM/YYYY` (será convertido)

### Valores Numéricos
- Use ponto `.` para decimais: `123.45`
- Vírgula será tratada automaticamente se for padrão BR

---

## 📦 Arquivos de Cadastro (Camada 1)

### 1. cadastro_produtos

**Nome do arquivo:** `cadastro_produtos.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ codigo | Inteiro | SIM | Código único do produto | 1001 |
| ⭐ descricao | Texto | SIM | Nome/descrição do produto | "Arroz Branco 5kg" |
| categoria | Texto | Não | Categoria do produto | "Alimentos" |
| subcategoria | Texto | Não | Subcategoria | "Grãos" |
| und_venda | Texto | Não | Unidade de venda | "UN", "KG", "CX" |
| curva_abc | Texto | Não | Classificação ABC | "A", "B", "C" |
| ean | Texto | Não | Código de barras | "7891234567890" |
| ncm | Texto | Não | Código NCM fiscal | "10063021" |

**Exemplo CSV:**
```csv
codigo,descricao,categoria,subcategoria,und_venda,curva_abc
1001,Arroz Branco 5kg,Alimentos,Grãos,UN,A
1002,Feijão Preto 1kg,Alimentos,Grãos,UN,B
1003,Macarrão Espaguete 500g,Alimentos,Massas,UN,A
```

**Exemplo Excel:**
| codigo | descricao | categoria | subcategoria | und_venda | curva_abc |
|--------|-----------|-----------|--------------|-----------|-----------|
| 1001 | Arroz Branco 5kg | Alimentos | Grãos | UN | A |
| 1002 | Feijão Preto 1kg | Alimentos | Grãos | UN | B |

---

### 2. cadastro_fornecedores

**Nome do arquivo:** `cadastro_fornecedores.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ codigo_fornecedor | Texto | SIM | Código único do fornecedor | "FORN001" |
| ⭐ nome_fornecedor | Texto | SIM | Razão social | "Distribuidora ABC Ltda" |
| categoria | Texto | Não | Categoria fornecida | "Alimentos" |
| lead_time_dias | Inteiro | Não | Tempo médio de entrega | 30 |
| cnpj | Texto | Não | CNPJ do fornecedor | "12.345.678/0001-90" |

**Exemplo CSV:**
```csv
codigo_fornecedor,nome_fornecedor,categoria,lead_time_dias
FORN001,Distribuidora ABC Ltda,Alimentos,30
FORN002,Atacado XYZ SA,Bebidas,14
FORN003,Importadora Global,Eletrônicos,60
```

---

### 3. cadastro_lojas

**Nome do arquivo:** `cadastro_lojas.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ cod_empresa | Inteiro | SIM | Código único da loja | 1 |
| ⭐ nome_loja | Texto | SIM | Nome da loja | "Loja Centro" |
| cidade | Texto | Não | Cidade | "São Paulo" |
| estado | Texto | Não | UF | "SP" |
| regiao | Texto | Não | Região | "Sudeste" |
| tipo_loja | Texto | Não | Tipo/formato | "Hipermercado", "Express" |

**Exemplo CSV:**
```csv
cod_empresa,nome_loja,cidade,estado,regiao,tipo_loja
1,Loja Centro,São Paulo,SP,Sudeste,Hipermercado
2,Loja Norte,Campinas,SP,Sudeste,Supermercado
3,Loja Sul,Curitiba,PR,Sul,Express
```

---

## 📸 Arquivos de Situação Atual (Camada 2)

### 4. estoque_atual

**Nome do arquivo:** `estoque_atual.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ cod_empresa | Inteiro | SIM | Código da loja | 1 |
| ⭐ codigo | Inteiro | SIM | Código do produto | 1001 |
| ⭐ qtd_estoque | Decimal | SIM | Quantidade em estoque | 150.00 |
| localizacao | Texto | Não | Local físico | "Gôndola", "Depósito" |
| data_contagem | Data | Não | Data da contagem | 2026-01-07 |

**Exemplo CSV:**
```csv
cod_empresa,codigo,qtd_estoque,localizacao
1,1001,150.50,Gôndola
1,1002,80.00,Depósito
2,1001,200.00,Gôndola
```

---

### 5. pedidos_abertos

**Nome do arquivo:** `pedidos_abertos.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ numero_pedido | Texto | SIM | Número do pedido | "PED20260107001" |
| ⭐ tipo_pedido | Texto | SIM | Tipo do pedido | "Fornecedor", "CD", "Transferência" |
| ⭐ data_pedido | Data | SIM | Data do pedido | 2026-01-05 |
| cod_empresa | Inteiro | Não | Loja destino | 1 |
| codigo | Inteiro | Não | Produto | 1001 |
| quantidade | Decimal | Não | Quantidade pedida | 100.00 |
| data_entrega_prevista | Data | Não | Previsão de entrega | 2026-01-15 |
| codigo_fornecedor | Texto | Não | Fornecedor | "FORN001" |

**Exemplo CSV:**
```csv
numero_pedido,tipo_pedido,data_pedido,cod_empresa,codigo,quantidade,data_entrega_prevista,codigo_fornecedor
PED001,Fornecedor,2026-01-05,1,1001,100,2026-01-15,FORN001
PED002,CD,2026-01-06,2,1002,50,2026-01-10,
PED003,Transferência,2026-01-07,3,1001,30,2026-01-09,
```

---

### 6. transito_atual

**Nome do arquivo:** `transito_atual.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ codigo | Inteiro | SIM | Código do produto | 1001 |
| ⭐ qtd_transito | Decimal | SIM | Quantidade em trânsito | 50.00 |
| ⭐ data_chegada_prevista | Data | SIM | Previsão de chegada | 2026-01-15 |
| cod_empresa | Inteiro | Não | Loja destino | 1 |
| numero_pedido | Texto | Não | Número do pedido | "PED001" |
| origem | Texto | Não | Origem | "CD Principal", "Fornecedor" |

**Exemplo CSV:**
```csv
codigo,qtd_transito,data_chegada_prevista,cod_empresa,numero_pedido,origem
1001,50,2026-01-15,1,PED001,Fornecedor
1002,30,2026-01-10,1,PED002,CD Principal
```

---

## 📊 Arquivos de Histórico (Camada 3)

### 7. historico_vendas

**Nome do arquivo:** `historico_vendas.[csv|xlsx|xls]`

⚠️ **ATENÇÃO:** Pode ser um arquivo GRANDE! O script importa em lotes.

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ data | Data | SIM | Data da venda | 2024-01-01 |
| ⭐ cod_empresa | Inteiro | SIM | Código da loja | 1 |
| ⭐ codigo | Inteiro | SIM | Código do produto | 1001 |
| ⭐ qtd_venda | Decimal | SIM | Quantidade vendida | 25.50 |
| valor_venda | Decimal | Não | Valor total da venda | 125.75 |

**Exemplo CSV:**
```csv
data,cod_empresa,codigo,qtd_venda,valor_venda
2024-01-01,1,1001,25.50,125.75
2024-01-01,1,1002,18.00,90.00
2024-01-02,1,1001,30.00,148.50
2024-01-02,2,1001,22.00,108.90
```

💡 **Dica:** Se você tem vendas por hora, agrupe por dia antes de importar.

---

### 8. historico_estoque

**Nome do arquivo:** `historico_estoque.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ data | Data | SIM | Data do snapshot | 2024-01-01 |
| ⭐ cod_empresa | Inteiro | SIM | Código da loja | 1 |
| ⭐ codigo | Inteiro | SIM | Código do produto | 1001 |
| ⭐ estoque_diario | Decimal | SIM | Estoque no final do dia | 150.00 |

**Exemplo CSV:**
```csv
data,cod_empresa,codigo,estoque_diario
2024-01-01,1,1001,150.00
2024-01-01,1,1002,80.00
2024-01-02,1,1001,125.00
2024-01-02,1,1002,62.00
```

---

### 9. historico_precos

**Nome do arquivo:** `historico_precos.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ data | Data | SIM | Data do preço | 2024-01-01 |
| ⭐ cod_empresa | Inteiro | SIM | Código da loja | 1 |
| ⭐ codigo | Inteiro | SIM | Código do produto | 1001 |
| ⭐ preco_venda | Decimal | SIM | Preço de venda | 5.99 |
| preco_custo | Decimal | Não | Preço de custo | 3.50 |
| em_promocao | Booleano | Não | Em promoção? | TRUE/FALSE |

**Exemplo CSV:**
```csv
data,cod_empresa,codigo,preco_venda,preco_custo,em_promocao
2024-01-01,1,1001,5.99,3.50,FALSE
2024-01-15,1,1001,4.99,3.50,TRUE
2024-02-01,1,1001,5.99,3.50,FALSE
```

---

## 🎉 Arquivo de Eventos (Camada Promocional)

### 10. eventos_promocionais

**Nome do arquivo:** `eventos_promocionais.[csv|xlsx|xls]`

**Colunas:**

| Coluna | Tipo | Obrigatório | Descrição | Exemplo |
|--------|------|-------------|-----------|---------|
| ⭐ nome_evento | Texto | SIM | Nome do evento | "Black Friday 2024" |
| ⭐ data_inicio | Data | SIM | Data de início | 2024-11-24 |
| ⭐ data_fim | Data | SIM | Data de término | 2024-11-30 |
| tipo_evento | Texto | Não | Tipo/categoria | "BlackFriday", "Natal", "Páscoa" |
| impacto_estimado | Decimal | Não | % de aumento estimado | 35.5 |
| descricao | Texto | Não | Descrição detalhada | "Promoção de fim de ano" |

**Exemplo CSV:**
```csv
nome_evento,data_inicio,data_fim,tipo_evento,impacto_estimado
Black Friday 2024,2024-11-24,2024-11-30,BlackFriday,35.5
Natal 2024,2024-12-15,2024-12-25,Natal,28.0
Volta às Aulas 2025,2025-01-15,2025-02-05,Escolar,15.0
Páscoa 2025,2025-03-25,2025-04-05,Páscoa,20.0
```

---

## 🚀 Checklist de Preparação

Antes de importar, verifique:

- [ ] Todos os arquivos estão na pasta `data_import`
- [ ] Nomes dos arquivos estão corretos (sem espaços, sem acentos)
- [ ] Colunas obrigatórias (⭐) estão presentes
- [ ] Datas no formato `YYYY-MM-DD` ou `DD/MM/YYYY`
- [ ] Números decimais usam ponto (`.`) ou vírgula (`,`) consistentemente
- [ ] Produtos referenciados existem em `cadastro_produtos`
- [ ] Lojas referenciadas existem em `cadastro_lojas`
- [ ] Fornecedores referenciados existem em `cadastro_fornecedores`

---

## 📝 Dicas de Preparação

### Converter Excel para CSV
Se preferir CSV para grandes volumes:
1. Abrir arquivo Excel
2. Arquivo → Salvar Como
3. Tipo: CSV (separado por vírgulas)
4. Salvar

### Verificar Encoding do CSV
Se tiver acentos, use **UTF-8**:
- Excel: Salvar Como → Ferramentas → Opções da Web → Codificação: UTF-8
- Notepad++: Codificação → Converter para UTF-8

### Consolidar Múltiplos Arquivos
Se você tem vendas em vários arquivos (um por mês):
- Opção 1: Usar Python para consolidar antes
- Opção 2: Importar manualmente arquivo por arquivo

---

## ❓ FAQ

**P: Posso ter colunas extras além das listadas?**
R: Sim! O script ignora colunas extras. Apenas as obrigatórias são validadas.

**P: E se eu não tiver alguns arquivos opcionais?**
R: Sem problema! O script pula arquivos que não existem.

**P: Meus CSVs usam ponto-e-vírgula (`;`) como separador**
R: O pandas detecta automaticamente. Se não funcionar, me avise.

**P: Posso importar de novo para atualizar os dados?**
R: Sim! Use `ON CONFLICT DO NOTHING` ou `TRUNCATE` antes.

**P: Quanto tempo leva para importar?**
R: Depende do volume:
- Cadastros (milhares): segundos
- Histórico (milhões): minutos (importa em lotes)

---

**Criado por:** Claude Code
**Data:** Janeiro 2026
**Versão:** 1.0
