# 📊 Painel de KPIs - Documentação

**Status:** ✅ Implementado (com dados mockados)
**Próxima Etapa:** Integração com dados reais
**Acesso:** http://localhost:5001/kpis

---

## 🎯 Visão Geral

Painel de acompanhamento evolutivo de KPIs do sistema, dividido em duas seções principais:

### 1. KPIs de Acurácia de Demanda
- **WMAPE Médio**: Erro percentual ponderado por volume
- **BIAS Médio**: Viés direcional das previsões
- **Previsões Excelentes**: Quantidade de SKUs com WMAPE < 10%
- **SKUs Analisados**: Total de produtos no período

### 2. KPIs de Gestão de Reabastecimento
- **Taxa de Ruptura**: % de dias em ruptura
- **Cobertura Média**: Dias de estoque médio
- **Nível de Serviço**: % de atendimento da demanda
- **SKUs Críticos**: Produtos com ruptura > 20%

---

## 📅 Visões Temporais

### Visão Mensal
- **Período:** 12 a 24 meses
- **Gráficos:**
  - Evolução WMAPE - Mensal
  - Evolução BIAS - Mensal
  - Distribuição de Classificação (Excelente/Bom/Aceitável/Fraco)
  - Taxa de Ruptura - Mensal
  - Cobertura de Estoque - Mensal
  - Nível de Serviço - Mensal

### Visão Semanal
- **Período:** 6 a 12 meses (26 a 52 semanas)
- **Gráficos:**
  - Evolução WMAPE - Semanal
  - Evolução BIAS - Semanal
  - Taxa de Ruptura - Semanal
  - Cobertura de Estoque - Semanal

---

## 🔍 Filtros Disponíveis

- **Loja:** Filtrar por código de filial
- **Produto:** Filtrar por código de produto
- **Categoria:** Filtrar por categoria de produtos
- **Fornecedor:** Filtrar por fornecedor

Todos os filtros são opcionais e podem ser combinados.

---

## 🏗️ Estrutura de Arquivos

```
templates/
  └── kpis.html          # Interface HTML do painel

static/js/
  └── kpis.js            # Lógica JavaScript (gráficos, filtros)

app.py
  ├── /kpis              # Rota principal (renderiza HTML)
  ├── /api/kpis/filtros  # Endpoint de filtros
  └── /api/kpis/dados    # Endpoint de dados
```

---

## 📡 API Endpoints

### GET /api/kpis/filtros

Retorna opções para os filtros.

**Response:**
```json
{
  "lojas": [
    {"id": 1, "nome": "Loja 1"},
    {"id": 2, "nome": "Loja 2"}
  ],
  "produtos": [
    {"id": 1001, "nome": "Produto A"},
    {"id": 1002, "nome": "Produto B"}
  ],
  "categorias": [
    "Alimentos",
    "Bebidas"
  ],
  "fornecedores": [
    "Fornecedor 1",
    "Fornecedor 2"
  ]
}
```

### GET /api/kpis/dados

Retorna dados de KPIs baseado nos filtros.

**Query Parameters:**
- `visao`: 'mensal' ou 'semanal'
- `loja`: ID da loja (opcional)
- `produto`: ID do produto (opcional)
- `categoria`: Nome da categoria (opcional)
- `fornecedor`: Nome do fornecedor (opcional)

**Response:**
```json
{
  "metricas_atuais": {
    "wmape": 10.5,
    "bias": 0.8,
    "previsoes_excelentes": 145,
    "total_skus": 245,
    "taxa_ruptura": 4.2,
    "cobertura_media": 19.5,
    "nivel_servico": 95.3,
    "skus_criticos": 8,
    "wmape_tendencia": {"tipo": "down", "valor": "2.3%"},
    "bias_tendencia": {"tipo": "stable", "valor": "0.1%"},
    "excelentes_tendencia": {"tipo": "up", "valor": "5.2%"},
    "ruptura_tendencia": {"tipo": "down", "valor": "1.2%"},
    "cobertura_tendencia": {"tipo": "up", "valor": "0.5 dias"},
    "servico_tendencia": {"tipo": "up", "valor": "2.1%"},
    "criticos_tendencia": {"tipo": "down", "valor": "3 SKUs"}
  },
  "series_temporais": {
    "wmape_mensal": [
      {"mes": "Jan/26", "wmape": 12.3},
      {"mes": "Dez/25", "wmape": 11.5}
    ],
    "bias_mensal": [
      {"mes": "Jan/26", "bias": 0.8},
      {"mes": "Dez/25", "bias": 1.2}
    ],
    "classificacao": [
      {
        "mes": "Jan/26",
        "excelente": 65,
        "bom": 42,
        "aceitavel": 18,
        "fraca": 10
      }
    ],
    "ruptura_mensal": [
      {"mes": "Jan/26", "taxa_ruptura": 4.2}
    ],
    "cobertura_mensal": [
      {"mes": "Jan/26", "cobertura_media": 19.5}
    ],
    "servico_mensal": [
      {"mes": "Jan/26", "nivel_servico": 95.3}
    ]
  },
  "performers": [
    {
      "sku": "1001",
      "descricao": "Produto A",
      "loja": "Loja 1",
      "wmape": 5.2,
      "bias": 0.3,
      "taxa_ruptura": 1.5,
      "cobertura": 22.5
    }
  ]
}
```

---

## 🔌 Integração com Dados Reais

### Passo 1: Criar Modelo de Dados

Criar tabela ou view no banco de dados para armazenar KPIs calculados:

```sql
CREATE TABLE kpis_historico (
    id SERIAL PRIMARY KEY,
    data_ref DATE NOT NULL,
    tipo_periodo VARCHAR(10) NOT NULL, -- 'mensal' ou 'semanal'
    cod_empresa INT,
    codigo INT,
    categoria VARCHAR(100),
    fornecedor VARCHAR(100),

    -- KPIs de Demanda
    wmape DECIMAL(10,2),
    bias DECIMAL(10,2),
    mae DECIMAL(10,2),

    -- KPIs de Reabastecimento
    taxa_ruptura DECIMAL(10,2),
    cobertura_media DECIMAL(10,2),
    nivel_servico DECIMAL(10,2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_periodo UNIQUE (data_ref, tipo_periodo, cod_empresa, codigo)
);

CREATE INDEX idx_kpis_data ON kpis_historico(data_ref);
CREATE INDEX idx_kpis_loja ON kpis_historico(cod_empresa);
CREATE INDEX idx_kpis_produto ON kpis_historico(codigo);
```

### Passo 2: Criar Job de Cálculo

Criar script que roda diariamente/semanalmente/mensalmente para calcular e armazenar KPIs:

```python
# calcular_kpis_periodico.py

from datetime import datetime, timedelta
from core.daily_data_loader import DailyDataLoader
from core.accuracy_metrics import walk_forward_validation
import psycopg2

def calcular_kpis_mensal(mes_referencia):
    """
    Calcula KPIs mensais para todos os SKUs
    """
    # Buscar dados do mês
    loader = DailyDataLoader(f'demanda_{mes_referencia}')
    df = loader.carregar()

    kpis_list = []

    # Processar por SKU (loja + produto)
    for (loja, produto), grupo in df.groupby(['cod_empresa', 'codigo']):

        # Calcular WMAPE e BIAS
        vendas = grupo['qtd_venda'].tolist()

        if len(vendas) >= 9:  # Mínimo para validação
            try:
                accuracy = walk_forward_validation(
                    vendas,
                    'AUTO',  # Usar seleção automática
                    horizon=1
                )

                wmape = accuracy['wmape']
                bias = accuracy['bias']
                mae = accuracy['mae']
            except:
                wmape = None
                bias = None
                mae = None
        else:
            wmape = None
            bias = None
            mae = None

        # Calcular Rupturas (se tiver coluna estoque_diario)
        if 'estoque_diario' in grupo.columns:
            rupturas = loader.detectar_rupturas()
            rupturas_sku = rupturas[
                (rupturas['cod_empresa'] == loja) &
                (rupturas['codigo'] == produto)
            ]

            taxa_ruptura = (len(rupturas_sku) / len(grupo)) * 100

            # Nível de serviço
            nivel_servico = loader.calcular_nivel_servico()
            nivel_sku = nivel_servico.get((loja, produto), {}).get('nivel_servico', None)
        else:
            taxa_ruptura = None
            nivel_sku = None

        # Calcular Cobertura (se tiver dados de estoque)
        if 'estoque_diario' in grupo.columns and 'qtd_venda' in grupo.columns:
            grupo_com_venda = grupo[grupo['qtd_venda'] > 0]
            if len(grupo_com_venda) > 0:
                cobertura_media = (
                    grupo_com_venda['estoque_diario'] /
                    grupo_com_venda['qtd_venda']
                ).mean()
            else:
                cobertura_media = None
        else:
            cobertura_media = None

        # Adicionar à lista
        kpis_list.append({
            'data_ref': mes_referencia,
            'tipo_periodo': 'mensal',
            'cod_empresa': loja,
            'codigo': produto,
            'wmape': wmape,
            'bias': bias,
            'mae': mae,
            'taxa_ruptura': taxa_ruptura,
            'cobertura_media': cobertura_media,
            'nivel_servico': nivel_sku
        })

    # Salvar no banco
    salvar_kpis_banco(kpis_list)

    return len(kpis_list)


def salvar_kpis_banco(kpis_list):
    """
    Salva KPIs no banco de dados
    """
    # TODO: Configurar conexão com banco
    conn = psycopg2.connect(
        host='localhost',
        database='demanda',
        user='postgres',
        password='senha'
    )

    cursor = conn.cursor()

    for kpi in kpis_list:
        cursor.execute("""
            INSERT INTO kpis_historico (
                data_ref, tipo_periodo, cod_empresa, codigo,
                wmape, bias, mae, taxa_ruptura, cobertura_media, nivel_servico
            ) VALUES (
                %(data_ref)s, %(tipo_periodo)s, %(cod_empresa)s, %(codigo)s,
                %(wmape)s, %(bias)s, %(mae)s, %(taxa_ruptura)s,
                %(cobertura_media)s, %(nivel_servico)s
            )
            ON CONFLICT (data_ref, tipo_periodo, cod_empresa, codigo)
            DO UPDATE SET
                wmape = EXCLUDED.wmape,
                bias = EXCLUDED.bias,
                mae = EXCLUDED.mae,
                taxa_ruptura = EXCLUDED.taxa_ruptura,
                cobertura_media = EXCLUDED.cobertura_media,
                nivel_servico = EXCLUDED.nivel_servico,
                created_at = CURRENT_TIMESTAMP
        """, kpi)

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == '__main__':
    # Rodar para o mês anterior
    hoje = datetime.now()
    mes_anterior = hoje.replace(day=1) - timedelta(days=1)
    mes_ref = mes_anterior.strftime('%Y-%m-01')

    print(f"Calculando KPIs para {mes_ref}...")
    total = calcular_kpis_mensal(mes_ref)
    print(f"✅ {total} SKUs processados!")
```

### Passo 3: Atualizar Endpoint /api/kpis/dados

Modificar `app.py` para buscar dados reais:

```python
@app.route('/api/kpis/dados', methods=['GET'])
def kpis_dados():
    """Retorna dados de KPIs com base nos filtros"""
    try:
        visao = request.args.get('visao', 'mensal')
        loja = request.args.get('loja', '')
        produto = request.args.get('produto', '')
        categoria = request.args.get('categoria', '')
        fornecedor = request.args.get('fornecedor', '')

        # Conectar ao banco
        conn = psycopg2.connect(...)
        cursor = conn.cursor()

        # Query base
        query = """
            SELECT
                data_ref,
                AVG(wmape) as wmape_medio,
                AVG(bias) as bias_medio,
                AVG(taxa_ruptura) as ruptura_media,
                AVG(cobertura_media) as cobertura_media,
                AVG(nivel_servico) as servico_medio,
                COUNT(*) as total_skus,
                SUM(CASE WHEN wmape < 10 THEN 1 ELSE 0 END) as excelentes
            FROM kpis_historico
            WHERE tipo_periodo = %s
        """

        params = [visao]

        # Aplicar filtros
        if loja:
            query += " AND cod_empresa = %s"
            params.append(loja)

        if produto:
            query += " AND codigo = %s"
            params.append(produto)

        # Agrupar por período
        query += " GROUP BY data_ref ORDER BY data_ref"

        cursor.execute(query, params)
        resultados = cursor.fetchall()

        # Processar resultados...
        # (converter para formato JSON esperado pelo frontend)

        cursor.close()
        conn.close()

        return jsonify(resultado)

    except Exception as e:
        print(f"Erro ao buscar dados de KPIs: {e}")
        return jsonify({'erro': str(e)}), 500
```

---

## 🎨 Personalização

### Cores dos Gráficos

Editar em `static/js/kpis.js`:

```javascript
// WMAPE
borderColor: '#667eea',           // Roxo
backgroundColor: 'rgba(102, 126, 234, 0.1)',

// BIAS
borderColor: '#f59e0b',           // Laranja
backgroundColor: 'rgba(245, 158, 11, 0.1)',

// Ruptura
borderColor: '#ef4444',           // Vermelho
backgroundColor: 'rgba(239, 68, 68, 0.1)',

// Cobertura
borderColor: '#10b981',           // Verde
backgroundColor: 'rgba(16, 185, 129, 0.1)',
```

### Faixas de Classificação

Editar em `templates/kpis.html` e `static/js/kpis.js`:

```javascript
// WMAPE
< 10%:  Excelente (verde)
10-20%: Bom (azul)
20-30%: Aceitável (laranja)
> 30%:  Fraca (vermelho)

// Ruptura
< 5%:   Normal (verde)
5-10%:  Atenção (azul)
10-20%: Alerta (laranja)
> 20%:  Crítico (vermelho)
```

---

## 🚀 Melhorias Futuras

### 1. Export de Dados
- Botão para exportar gráficos em PDF
- Download de tabelas em Excel

### 2. Alertas Automáticos
- Email quando KPI crítico
- Notificações em tempo real

### 3. Comparações
- Comparar períodos (MoM, YoY)
- Benchmark entre lojas
- Ranking de produtos

### 4. Drill-Down
- Clicar em ponto do gráfico para ver detalhes
- Navegar de categoria → produto → loja

### 5. Metas
- Definir metas por KPI
- Visualizar distância da meta
- Semáforo (verde/amarelo/vermelho)

---

## 📝 Notas Importantes

### Status Atual: MOCKADO
Os dados atualmente são **gerados aleatoriamente** para demonstração. Para produção:

1. ✅ Criar tabela `kpis_historico` no banco
2. ✅ Implementar job de cálculo periódico
3. ✅ Substituir dados mockados por queries reais
4. ✅ Adicionar cache para performance
5. ✅ Implementar filtros dinâmicos

### Performance
- Considerar materializar views para queries complexas
- Usar cache Redis para dados recentes (últimos 30 dias)
- Implementar paginação na tabela de performers

### Segurança
- Validar todos os inputs de filtros
- Limitar range de datas consultadas
- Implementar rate limiting na API

---

## 🧪 Como Testar

1. **Iniciar servidor:**
   ```bash
   python app.py
   ```

2. **Acessar painel:**
   ```
   http://localhost:5001/kpis
   ```

3. **Testar filtros:**
   - Selecionar loja, produto, etc
   - Clicar em "Aplicar Filtros"
   - Verificar se gráficos atualizam

4. **Testar visões:**
   - Alternar entre "Visão Mensal" e "Visão Semanal"
   - Verificar se gráficos correspondentes aparecem

---

**Desenvolvido por:** Claude Code + Valter Lino
**Data:** Janeiro 2026
**Versão:** 1.0 (mockado - aguardando integração com dados reais)
