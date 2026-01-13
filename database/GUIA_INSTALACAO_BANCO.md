

# 🗄️ Guia de Instalação e Configuração do Banco de Dados

**Objetivo:** Estruturar dados (CSV/Excel) em banco de dados PostgreSQL

**Formatos Aceitos:** CSV, XLSX, XLS

---

## 📋 Índice

1. [Por Que Usar Banco de Dados?](#por-que-usar-banco-de-dados)
2. [Instalação do PostgreSQL](#instalação-do-postgresql)
3. [Criação do Banco](#criação-do-banco)
4. [Preparação dos Arquivos](#preparação-dos-arquivos)
5. [Importação dos Dados](#importação-dos-dados)
6. [Validação](#validação)
7. [Integração com a Ferramenta](#integração-com-a-ferramenta)

---

## 🎯 Por Que Usar Banco de Dados?

### Problemas dos CSVs:
❌ Lento para grandes volumes (>100MB)
❌ Dados duplicados (mesmos cadastros em vários arquivos)
❌ Difícil manter consistência
❌ Não tem relacionamentos
❌ Não tem índices (busca lenta)
❌ Memória: carrega tudo de uma vez

### Vantagens do PostgreSQL:
✅ **Performance:** Queries otimizadas com índices
✅ **Escalabilidade:** Milhões de registros sem problemas
✅ **Relacionamentos:** Integridade referencial
✅ **Particionamento:** Histórico dividido por ano
✅ **Views Materializadas:** Cache de agregações
✅ **Backup/Restore:** Ferramentas nativas
✅ **Concurrent:** Múltiplos processos acessando

---

## 💿 Instalação do PostgreSQL

### Windows:

1. **Download:**
   - Acesse: https://www.postgresql.org/download/windows/
   - Baixe o instalador (versão 14 ou superior)

2. **Instalação:**
   - Execute o instalador
   - **Senha do superusuário (postgres):** Anote bem!
   - Porta padrão: `5432`
   - Locale: `Portuguese, Brazil`

3. **Verificar Instalação:**
   ```cmd
   psql --version
   ```
   Deve retornar: `psql (PostgreSQL) 14.x`

### Ferramentas Opcionais:

**pgAdmin 4** (Interface Gráfica)
- Já vem com o instalador do PostgreSQL
- Permite visualizar tabelas, executar queries, etc

**DBeaver** (Alternativa)
- Download: https://dbeaver.io/
- Mais leve que pgAdmin

---

## 🏗️ Criação do Banco

### Opção 1: Via pgAdmin (Gráfico)

1. Abrir pgAdmin 4
2. Conectar ao servidor local (senha que você criou)
3. Right-click em "Databases" → Create → Database
4. Nome: `demanda_reabastecimento`
5. Encoding: `UTF8`
6. OK

### Opção 2: Via Terminal (Linha de Comando)

```cmd
# Conectar ao PostgreSQL
psql -U postgres

# Criar banco
CREATE DATABASE demanda_reabastecimento
    WITH
    ENCODING = 'UTF8'
    LC_COLLATE = 'Portuguese_Brazil.1252'
    LC_CTYPE = 'Portuguese_Brazil.1252';

# Sair
\q
```

### Criar as Tabelas:

```cmd
# Navegar até a pasta do projeto
cd C:\Users\valter.lino\Desktop\Treinamentos\VS\previsao-demanda

# Executar script SQL
psql -U postgres -d demanda_reabastecimento -f database\schema.sql
```

✅ Isso cria TODAS as tabelas, índices e views!

---

## 📂 Preparação dos Arquivos

### 📋 Formatos Aceitos

O script de importação aceita **três formatos**:
- ✅ **CSV** (`.csv`) - Recomendado para grandes volumes
- ✅ **Excel Moderno** (`.xlsx`) - Excel 2007+
- ✅ **Excel Antigo** (`.xls`) - Excel 97-2003

Você pode misturar formatos! Exemplo:
- `cadastro_produtos.xlsx` (Excel)
- `historico_vendas.csv` (CSV)
- `estoque_atual.xls` (Excel antigo)

### 📁 Estrutura de Pastas

A pasta `data_import` já foi criada. Coloque seus arquivos lá:

```
C:\Users\valter.lino\Desktop\Treinamentos\VS\previsao-demanda\
└── data_import\
    ├── cadastro_produtos.[csv|xlsx|xls]
    ├── cadastro_fornecedores.[csv|xlsx|xls]
    ├── cadastro_lojas.[csv|xlsx|xls]
    ├── estoque_atual.[csv|xlsx|xls]
    ├── pedidos_abertos.[csv|xlsx|xls]
    ├── transito_atual.[csv|xlsx|xls]
    ├── historico_vendas.[csv|xlsx|xls]
    ├── historico_estoque.[csv|xlsx|xls]
    ├── historico_precos.[csv|xlsx|xls]
    └── eventos_promocionais.[csv|xlsx|xls]
```

💡 **Importante:** Você NÃO precisa ter todos os arquivos! O script importa apenas os que encontrar.

### 📋 Formatos Detalhados

Para ver o formato detalhado de cada arquivo (colunas obrigatórias, exemplos, etc), consulte:

**👉 [FORMATOS_ARQUIVOS.md](FORMATOS_ARQUIVOS.md)**

### Resumo Rápido:

#### 1. **cadastro_produtos.csv**
```csv
codigo,descricao,categoria,subcategoria,und_venda,curva_abc
1001,Produto A,Alimentos,Grãos,UN,A
1002,Produto B,Bebidas,Refrigerantes,UN,B
```

**Colunas obrigatórias:**
- `codigo` (INTEGER)
- `descricao` (TEXT)

**Colunas opcionais:**
- `categoria`, `subcategoria`, `und_venda`, `curva_abc`

---

#### 2. **cadastro_fornecedores.csv**
```csv
codigo_fornecedor,nome_fornecedor,categoria,lead_time_dias
FORN001,Fornecedor ABC Ltda,Alimentos,30
FORN002,Distribuidora XYZ,Bebidas,14
```

**Colunas obrigatórias:**
- `codigo_fornecedor` (TEXT)
- `nome_fornecedor` (TEXT)

---

#### 3. **estoque_atual.csv**
```csv
cod_empresa,codigo,qtd_estoque,localizacao
1,1001,150,Gôndola
1,1002,80,Depósito
```

**Colunas obrigatórias:**
- `cod_empresa` (INTEGER) - código da loja
- `codigo` (INTEGER) - código do produto
- `qtd_estoque` (DECIMAL)

---

#### 4. **historico_vendas.csv**
```csv
data,cod_empresa,codigo,qtd_venda,valor_venda
2024-01-01,1,1001,25,125.50
2024-01-01,1,1002,18,90.00
```

**Colunas obrigatórias:**
- `data` (DATE no formato YYYY-MM-DD)
- `cod_empresa` (INTEGER)
- `codigo` (INTEGER)
- `qtd_venda` (DECIMAL)

**Colunas opcionais:**
- `valor_venda` (DECIMAL)

⚠️ **IMPORTANTE:** Este pode ser o maior arquivo! O script importa em lotes (batch).

---

#### 5. **historico_estoque.csv**
```csv
data,cod_empresa,codigo,estoque_diario
2024-01-01,1,1001,150
2024-01-01,1,1002,80
```

**Colunas obrigatórias:**
- `data` (DATE)
- `cod_empresa` (INTEGER)
- `codigo` (INTEGER)
- `estoque_diario` (DECIMAL)

---

#### 6. **eventos_promocionais.csv**
```csv
nome_evento,tipo_evento,data_inicio,data_fim,impacto_estimado
Black Friday 2024,BlackFriday,2024-11-24,2024-11-30,35.5
Natal 2024,Natal,2024-12-15,2024-12-25,28.0
```

**Colunas obrigatórias:**
- `nome_evento` (TEXT)
- `data_inicio` (DATE)
- `data_fim` (DATE)

**Colunas opcionais:**
- `tipo_evento`, `impacto_estimado`

---

## 🚀 Importação dos Dados

### Passo 1: Configurar Conexão

Editar `database\importar_csvs.py` (linha 21-27):

```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'demanda_reabastecimento',
    'user': 'postgres',
    'password': 'SUA_SENHA_AQUI',  # ALTERAR!
    'port': 5432
}
```

### Passo 2: Instalar Dependências

```cmd
pip install psycopg2-binary pandas openpyxl xlrd
```

**O que cada biblioteca faz:**
- `psycopg2-binary`: Conectar ao PostgreSQL
- `pandas`: Manipular dados
- `openpyxl`: Ler arquivos Excel modernos (.xlsx)
- `xlrd`: Ler arquivos Excel antigos (.xls)

### Passo 3: Rodar Importação

```cmd
cd C:\Users\valter.lino\Desktop\Treinamentos\VS\previsao-demanda

python database\importar_csvs.py
```

**O que acontece:**
1. ✅ Procura arquivos em CSV, XLSX ou XLS
2. ✅ Detecta encoding automaticamente (CSV)
3. ✅ Valida colunas obrigatórias
4. ✅ Processa/transforma dados
5. ✅ Insere em lotes de 1000 registros
6. ✅ Mostra progresso em tempo real

**Saída esperada:**
```
============================================================
   IMPORTAÇÃO DE DADOS PARA BANCO DE DADOS
============================================================

📁 Diretório de dados: C:\...\data_import
🗄️  Banco: demanda_reabastecimento@localhost
📋 Formatos aceitos: CSV, XLSX, XLS

✅ Conectado ao banco 'demanda_reabastecimento'

============================================================
📂 Processando: cadastro_produtos.csv
============================================================
✅ Lido: 245 registros
🔧 Preparando dados...
💾 Inserindo em 'cadastro_produtos'...
  ✅ 245 registros inseridos em cadastro_produtos
✅ Importação concluída: 245 registros

...

============================================================
   RESUMO DA IMPORTAÇÃO
============================================================
Total de arquivos configurados: 9
✅ Importados com sucesso: 7
⚠️  Pulados (não encontrados): 2
❌ Erros: 0
============================================================

🎉 Importação concluída!
```

---

## ✅ Validação

### Via pgAdmin:

1. Abrir pgAdmin 4
2. Navegar: Servers → PostgreSQL → Databases → demanda_reabastecimento → Schemas → public → Tables
3. Right-click em `cadastro_produtos` → View/Edit Data → All Rows
4. Verificar se os dados estão lá!

### Via SQL (Terminal):

```cmd
psql -U postgres -d demanda_reabastecimento
```

```sql
-- Contar registros em cada tabela
SELECT 'cadastro_produtos' as tabela, COUNT(*) FROM cadastro_produtos
UNION ALL
SELECT 'historico_vendas_diario', COUNT(*) FROM historico_vendas_diario
UNION ALL
SELECT 'historico_estoque_diario', COUNT(*) FROM historico_estoque_diario
UNION ALL
SELECT 'eventos_promocionais', COUNT(*) FROM eventos_promocionais;

-- Ver amostra de vendas
SELECT * FROM historico_vendas_diario
ORDER BY data DESC
LIMIT 10;

-- Ver estoque atual
SELECT
    e.cod_empresa,
    e.codigo,
    p.descricao,
    e.qtd_estoque
FROM estoque_atual e
JOIN cadastro_produtos p ON e.codigo = p.codigo
LIMIT 10;
```

### Atualizar Views Materializadas:

```sql
REFRESH MATERIALIZED VIEW vw_estoque_total;
REFRESH MATERIALIZED VIEW vw_vendas_mensais;

-- Verificar
SELECT * FROM vw_estoque_total LIMIT 10;
```

---

## 🔌 Integração com a Ferramenta

Agora que os dados estão no banco, precisamos conectar a ferramenta.

### 1. Instalar Biblioteca de Conexão

```cmd
pip install psycopg2-binary sqlalchemy
```

### 2. Criar Módulo de Conexão

Criar `core/database.py`:

```python
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from sqlalchemy import create_engine

DB_CONFIG = {
    'host': 'localhost',
    'database': 'demanda_reabastecimento',
    'user': 'postgres',
    'password': 'SUA_SENHA',
    'port': 5432
}

def get_connection():
    """Retorna conexão ao banco"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def query_to_dataframe(sql, params=None):
    """Executa query e retorna DataFrame"""
    engine = create_engine(
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return pd.read_sql(sql, engine, params=params)

# Exemplo de uso
def buscar_vendas_produto(cod_empresa, codigo, data_inicio, data_fim):
    """Busca histórico de vendas de um produto"""
    sql = """
        SELECT data, qtd_venda, valor_venda
        FROM historico_vendas_diario
        WHERE cod_empresa = %s
          AND codigo = %s
          AND data BETWEEN %s AND %s
        ORDER BY data
    """
    return query_to_dataframe(sql, (cod_empresa, codigo, data_inicio, data_fim))
```

### 3. Modificar `daily_data_loader.py`

Em vez de ler CSV, buscar do banco:

```python
from core.database import query_to_dataframe

class DailyDataLoader:
    def carregar_do_banco(self, data_inicio, data_fim, lojas=None, produtos=None):
        """Carrega dados diários do banco"""
        sql = """
            SELECT
                data,
                cod_empresa,
                codigo,
                qtd_venda,
                estoque_diario
            FROM historico_vendas_diario v
            LEFT JOIN historico_estoque_diario e
              ON v.data = e.data
             AND v.cod_empresa = e.cod_empresa
             AND v.codigo = e.codigo
            WHERE v.data BETWEEN %s AND %s
        """

        params = [data_inicio, data_fim]

        if lojas:
            sql += " AND v.cod_empresa = ANY(%s)"
            params.append(lojas)

        if produtos:
            sql += " AND v.codigo = ANY(%s)"
            params.append(produtos)

        sql += " ORDER BY v.data, v.cod_empresa, v.codigo"

        return query_to_dataframe(sql, params)
```

### 4. Atualizar Endpoint de KPIs

No `app.py`, substituir dados mockados:

```python
from core.database import query_to_dataframe

@app.route('/api/kpis/dados', methods=['GET'])
def kpis_dados():
    visao = request.args.get('visao', 'mensal')

    # Buscar KPIs do banco
    if visao == 'mensal':
        sql = """
            SELECT
                TO_CHAR(data_ref, 'Mon/YY') as mes,
                AVG(wmape) as wmape,
                AVG(bias) as bias,
                AVG(taxa_ruptura) as taxa_ruptura,
                AVG(cobertura_media) as cobertura_media
            FROM kpis_historico
            WHERE tipo_periodo = 'mensal'
              AND data_ref >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY data_ref
            ORDER BY data_ref
        """
        df = query_to_dataframe(sql)

        wmape_mensal = df[['mes', 'wmape']].to_dict('records')
        bias_mensal = df[['mes', 'bias']].to_dict('records')
        # ...

    return jsonify({
        'metricas_atuais': {...},
        'series_temporais': {
            'wmape_mensal': wmape_mensal,
            'bias_mensal': bias_mensal,
            ...
        }
    })
```

---

## 📊 Performance e Manutenção

### Indexes (já criados no schema.sql):

✅ Todas as colunas de data têm índice
✅ Chaves estrangeiras têm índice
✅ Combinações freq

uentes (loja+produto+data) têm índice composto

### Particionamento:

✅ `historico_vendas_diario` particionado por ANO
✅ `historico_estoque_diario` particionado por ANO
✅ Queries automáticas usam apenas partições necessárias

### Views Materializadas:

Atualizar diariamente (via cron/job):

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY vw_estoque_total;
REFRESH MATERIALIZED VIEW CONCURRENTLY vw_vendas_mensais;
```

### Backup:

```cmd
# Backup completo
pg_dump -U postgres -d demanda_reabastecimento > backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres -d demanda_reabastecimento < backup_20260107.sql
```

---

## 🎯 Resumo - Checklist

- [ ] PostgreSQL instalado e rodando
- [ ] Banco `demanda_reabastecimento` criado
- [ ] Schema SQL executado (tabelas criadas)
- [ ] CSVs preparados na pasta `data_import`
- [ ] Script `importar_csvs.py` configurado (senha)
- [ ] Importação executada com sucesso
- [ ] Dados validados (queries de teste)
- [ ] Views materializadas atualizadas
- [ ] Módulo `core/database.py` criado
- [ ] Ferramenta integrada ao banco

---

## 💡 Próximos Passos

1. **Job de Atualização Diária:**
   - Script que importa vendas/estoque do dia anterior
   - Roda automaticamente todo dia às 6h

2. **Cálculo Automático de KPIs:**
   - Job semanal/mensal que calcula e armazena KPIs
   - Alimenta tabela `kpis_historico`

3. **API REST:**
   - Endpoints para inserção de dados via API
   - Integração com sistemas existentes

4. **Dashboard Tempo Real:**
   - WebSocket para atualização em tempo real
   - Alertas automáticos

---

**Criado por:** Claude Code + Valter Lino
**Data:** Janeiro 2026
**Versão:** 1.0
