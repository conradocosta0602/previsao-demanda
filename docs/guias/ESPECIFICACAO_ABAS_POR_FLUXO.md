# Especificação: Arquitetura com Abas Separadas por Fluxo

**Data:** 2024-12-29
**Versão:** 3.0 (Revisada)
**Abordagem:** Abas específicas por tipo de fluxo

---

## 🎯 NOVA VISÃO: ABAS SEPARADAS

### Problema da Abordagem Anterior
❌ Coluna `Tipo_Fluxo` mistura diferentes contextos na mesma aba
❌ Campos irrelevantes para cada tipo (ex: CD não tem exposição de gôndola)
❌ Validações complexas
❌ Usuário precisa lembrar valores válidos

### Solução Proposta (Revisada)
✅ **Cada tipo de fluxo = 1 aba específica**
✅ Campos específicos e relevantes por aba
✅ Validações naturais pela estrutura
✅ Interface intuitiva (usuário sabe onde preencher)

---

## 📂 ESTRUTURA DO ARQUIVO: exemplo_reabastecimento_completo.xlsx

### Visão Geral das Abas

| Aba | Finalidade | Quando Usar |
|-----|-----------|-------------|
| **PEDIDOS_FORNECEDOR** | Compras de fornecedor | CD ou Loja comprando |
| **PEDIDOS_CD** | Distribuição CD→Loja | Lojas pedindo do CD |
| **TRANSFERENCIAS** | Loja↔Loja | Balanceamento, emergências |
| **HISTORICO_VENDAS** | Dados históricos | Obrigatório (compartilhado) |
| **INSTRUCOES** | Guia de uso | Referência |

---

## 📋 DETALHAMENTO DAS ABAS

### ABA 1: PEDIDOS_FORNECEDOR

**Finalidade:** Compras diretas de fornecedores (tanto para CD quanto para Lojas)

#### Estrutura de Colunas

| Coluna | Tipo | Obrig | Descrição | Exemplo |
|--------|------|-------|-----------|---------|
| **Fornecedor** | Texto | ✅ Sim | Código do fornecedor | FORN_A |
| **SKU** | Texto | ✅ Sim | Código do produto | PROD_001 |
| **Destino** | Texto | ✅ Sim | Onde entregar | CD_PRINCIPAL, LOJA_MEGA |
| **Tipo_Destino** | Texto | ✅ Sim | CD ou LOJA | CD, LOJA |
| **Lead_Time_Dias** | Inteiro | ✅ Sim | Prazo de entrega | 15, 20 |
| **Ciclo_Pedido_Dias** | Inteiro | ⚠️ Não | Frequência de pedido | 30 (padrão: 30 para CD, 14 para LOJA) |
| **Lote_Minimo** | Inteiro | ⚠️ Não | Unidades por caixa | 12 |
| **Multiplo_Palete** | Inteiro | ⚠️ Não | Unidades por palete | 240 |
| **Multiplo_Carreta** | Inteiro | ⚠️ Não | Unidades por carreta | 4800 |
| **Custo_Unitario** | Decimal | ⚠️ Não | Custo por unidade | 10.50 |
| **Custo_Frete** | Decimal | ⚠️ Não | Custo fixo do frete | 500.00 |
| **Estoque_Disponivel** | Número | ✅ Sim | Estoque atual no destino | 5000 |
| **Estoque_Transito** | Número | ⚠️ Não | Em trânsito para destino | 2000 |
| **Pedidos_Abertos** | Número | ⚠️ Não | Pedidos em aberto | 0 |
| **Nivel_Servico** | Decimal | ⚠️ Não | 0.90-0.99 | 0.95 (padrão) |
| **Capacidade_Max_Armazenamento** | Número | ⚠️ Não | Capacidade do destino | 50000 |

#### Exemplos de Preenchimento

**Exemplo 1: CD comprando de Fornecedor**
```
Fornecedor: FORN_A
SKU: PROD_001
Destino: CD_PRINCIPAL
Tipo_Destino: CD
Lead_Time_Dias: 15
Ciclo_Pedido_Dias: 30
Lote_Minimo: 24
Multiplo_Palete: 240
Multiplo_Carreta: 4800
Estoque_Disponivel: 5000
Nivel_Servico: 0.95
```

**Exemplo 2: Loja MEGA comprando direto de Fornecedor**
```
Fornecedor: FORN_B
SKU: PROD_003
Destino: LOJA_MEGA
Tipo_Destino: LOJA
Lead_Time_Dias: 10
Ciclo_Pedido_Dias: 14
Lote_Minimo: 12
Multiplo_Palete: 144
Estoque_Disponivel: 200
Nivel_Servico: 0.98
```

#### Padrões e Validações

**Ciclo_Pedido_Dias padrão:**
- Se `Tipo_Destino = CD`: padrão = **30 dias** (mensal)
- Se `Tipo_Destino = LOJA`: padrão = **14 dias** (quinzenal)

**Validações:**
- `Tipo_Destino` deve ser: `CD` ou `LOJA`
- Se `Multiplo_Palete` ou `Multiplo_Carreta` > 0: só para `Tipo_Destino = CD`
- `Lead_Time_Dias` >= `Ciclo_Pedido_Dias` (warning se não)

---

### ABA 2: PEDIDOS_CD

**Finalidade:** Distribuição do CD para as lojas (fluxo mais frequente e fracionado)

#### Estrutura de Colunas

| Coluna | Tipo | Obrig | Descrição | Exemplo |
|--------|------|-------|-----------|---------|
| **CD_Origem** | Texto | ✅ Sim | Centro de distribuição | CD_PRINCIPAL |
| **Loja_Destino** | Texto | ✅ Sim | Código da loja | LOJA_01 |
| **SKU** | Texto | ✅ Sim | Código do produto | PROD_001 |
| **Lead_Time_Dias** | Inteiro | ✅ Sim | Prazo de entrega | 2, 3 |
| **Ciclo_Pedido_Dias** | Inteiro | ⚠️ Não | Frequência de pedido | 2 (padrão) |
| **Lote_Minimo** | Inteiro | ⚠️ Não | Unidades por caixa | 6 |
| **Estoque_Disponivel_Loja** | Número | ✅ Sim | Estoque atual na loja | 50 |
| **Estoque_Disponivel_CD** | Número | ⚠️ Não | Disponível no CD | 5000 |
| **Estoque_Transito** | Número | ⚠️ Não | Em trânsito para loja | 0 |
| **Pedidos_Abertos** | Número | ⚠️ Não | Pedidos em aberto | 0 |
| **Nivel_Servico** | Decimal | ⚠️ Não | 0.90-0.99 | 0.99 (padrão lojas) |
| **Estoque_Min_Gondola** | Inteiro | ⚠️ Não | Mínimo para exposição | 12 |
| **Numero_Frentes** | Inteiro | ⚠️ Não | Frentes de gôndola | 3 |
| **Capacidade_Max_Loja** | Número | ⚠️ Não | Cap. armazenamento loja | 500 |

#### Exemplos de Preenchimento

**Exemplo: Loja pedindo do CD**
```
CD_Origem: CD_PRINCIPAL
Loja_Destino: LOJA_01
SKU: PROD_001
Lead_Time_Dias: 2
Ciclo_Pedido_Dias: 2
Lote_Minimo: 6
Estoque_Disponivel_Loja: 15
Estoque_Disponivel_CD: 5000
Nivel_Servico: 0.99
Estoque_Min_Gondola: 12
Numero_Frentes: 3
```

#### Padrões e Validações

**Padrões:**
- `Ciclo_Pedido_Dias`: **2 dias** (2-3x por semana)
- `Nivel_Servico`: **0.99** (lojas precisam alto nível)
- `Numero_Frentes`: **1** (se não informado)

**Validações:**
- Se `Estoque_Disponivel_CD` informado: validar disponibilidade
- Se quantidade calculada > `Estoque_Disponivel_CD`: alerta "CD insuficiente"
- Validar `Capacidade_Max_Loja`

**Cálculo de Exposição:**
```
Estoque_Minimo_Real = MAX(
    Ponto_Pedido_Estatístico,
    Estoque_Min_Gondola × Numero_Frentes
)
```

---

### ABA 3: TRANSFERENCIAS

**Finalidade:** Transferências entre lojas (balanceamento, emergências)

#### Estrutura de Colunas

| Coluna | Tipo | Obrig | Descrição | Exemplo |
|--------|------|-------|-----------|---------|
| **Loja_Origem** | Texto | ✅ Sim | Loja doadora | LOJA_02 |
| **Loja_Destino** | Texto | ✅ Sim | Loja receptora | LOJA_01 |
| **SKU** | Texto | ✅ Sim | Código do produto | PROD_001 |
| **Lead_Time_Dias** | Inteiro | ⚠️ Não | Prazo de transferência | 1 (padrão) |
| **Estoque_Origem** | Número | ✅ Sim | Disponível na origem | 80 |
| **Estoque_Destino** | Número | ✅ Sim | Disponível no destino | 5 |
| **Demanda_Diaria_Origem** | Decimal | ✅ Sim | Demanda origem | 3.0 |
| **Demanda_Diaria_Destino** | Decimal | ✅ Sim | Demanda destino | 8.0 |
| **Custo_Transferencia** | Decimal | ⚠️ Não | Custo por unidade | 0.50 |
| **Distancia_Km** | Decimal | ⚠️ Não | Distância entre lojas | 15.0 |

#### Lógica de Processamento

**Sistema identifica automaticamente:**
1. **Lojas doadoras** (excesso):
   - Cobertura > 2× média da rede
   - OU Estoque > Ponto_Pedido + 50%

2. **Lojas receptoras** (necessidade):
   - Cobertura < 3 dias
   - OU Estoque < Ponto_Pedido

3. **Calcula viabilidade:**
   - Quantidade disponível na origem
   - Quantidade necessária no destino
   - Custo vs pedido novo
   - Tempo vs urgência

**Relatório de Saída:**
- Todas as transferências viáveis
- Economia vs pedido novo
- Priorização por urgência

#### Exemplos de Preenchimento

**Exemplo: Balanceamento de estoque**
```
Loja_Origem: LOJA_02
Loja_Destino: LOJA_01
SKU: PROD_001
Lead_Time_Dias: 1
Estoque_Origem: 80
Estoque_Destino: 5
Demanda_Diaria_Origem: 3.0
Demanda_Diaria_Destino: 8.0
Custo_Transferencia: 0.50
Distancia_Km: 15
```

**Sistema analisa:**
```
LOJA_02 (origem):
- Estoque: 80
- Demanda: 3/dia
- Cobertura: 26.7 dias (EXCESSO!)
- Excesso: ~40 unidades

LOJA_01 (destino):
- Estoque: 5
- Demanda: 8/dia
- Cobertura: 0.6 dias (RUPTURA!)
- Falta: ~40 unidades

DECISÃO: Transferir 40 unidades
- Custo: 40 × R$ 0.50 = R$ 20
- Vs pedido novo: R$ 2.00/un = R$ 80
- Economia: R$ 60 (75%)
```

---

### ABA 4: HISTORICO_VENDAS (Sem alteração)

**Estrutura mantida:**
- Loja
- SKU
- Mes (YYYY-MM)
- Vendas
- Dias_Com_Estoque (opcional)
- Origem (opcional)

**Importante:** Esta aba é compartilhada por todos os fluxos!

---

## 🛠️ MÓDULOS DE PEDIDO MANUAL (ATUALIZAÇÃO)

### Módulo 1: Pedido por Quantidade (ATUALIZADO)

#### Novo Campo: Origem e Destino

**Arquivo: exemplo_pedido_quantidade.xlsx**

| Coluna | Tipo | Obrig | Novo? | Descrição |
|--------|------|-------|-------|-----------|
| **Origem** | **Texto** | **✅ Sim** | **✅ SIM** | **FORNECEDOR_X, CD_Y, LOJA_Z** |
| **Destino** | **Texto** | **✅ Sim** | **✅ SIM** | **CD_Y, LOJA_Z** |
| **Tipo_Origem** | **Texto** | **✅ Sim** | **✅ SIM** | **FORNECEDOR, CD, LOJA** |
| **Tipo_Destino** | **Texto** | **✅ Sim** | **✅ SIM** | **CD, LOJA** |
| SKU | Texto | ✅ Sim | Não | Código do produto |
| Quantidade_Desejada | Número | ✅ Sim | Não | Quantidade a pedir |
| Unidades_Por_Caixa | Inteiro | ✅ Sim | Não | Múltiplo de embalagem |
| Demanda_Diaria | Decimal | ⚠️ Não | Não | Para cálculo de cobertura |
| Estoque_Disponivel | Número | ⚠️ Não | Não | Estoque atual destino |

**Exemplo:**
```
Origem: FORN_A
Destino: CD_PRINCIPAL
Tipo_Origem: FORNECEDOR
Tipo_Destino: CD
SKU: PROD_001
Quantidade_Desejada: 5000
Unidades_Por_Caixa: 24
```

**Validações adicionadas:**
- Se `Tipo_Origem = FORNECEDOR` e `Tipo_Destino = CD`: permitir múltiplos de palete/carreta
- Se `Tipo_Origem = CD` e `Tipo_Destino = LOJA`: validar disponibilidade no CD
- Se `Tipo_Origem = LOJA` e `Tipo_Destino = LOJA`: alertar sobre transferência

---

### Módulo 2: Pedido por Cobertura (ATUALIZADO)

#### Novo Campo: Origem e Destino

**Arquivo: exemplo_pedido_cobertura.xlsx**

| Coluna | Tipo | Obrig | Novo? | Descrição |
|--------|------|-------|-------|-----------|
| **Origem** | **Texto** | **✅ Sim** | **✅ SIM** | **FORNECEDOR_X, CD_Y** |
| **Destino** | **Texto** | **✅ Sim** | **✅ SIM** | **CD_Y, LOJA_Z** |
| **Tipo_Origem** | **Texto** | **✅ Sim** | **✅ SIM** | **FORNECEDOR, CD** |
| **Tipo_Destino** | **Texto** | **✅ Sim** | **✅ SIM** | **CD, LOJA** |
| SKU | Texto | ✅ Sim | Não | Código do produto |
| Demanda_Diaria | Decimal | ✅ Sim | Não | Demanda diária |
| Cobertura_Desejada_Dias | Inteiro | ✅ Sim | Não | Dias de cobertura |
| Unidades_Por_Caixa | Inteiro | ✅ Sim | Não | Múltiplo de embalagem |
| Estoque_Disponivel | Número | ⚠️ Não | Não | Estoque atual |

**Exemplo:**
```
Origem: CD_PRINCIPAL
Destino: LOJA_01
Tipo_Origem: CD
Tipo_Destino: LOJA
SKU: PROD_001
Demanda_Diaria: 8.0
Cobertura_Desejada_Dias: 7
Unidades_Por_Caixa: 6
Estoque_Disponivel: 15
```

---

## 🎨 INTERFACE WEB (ATUALIZAÇÃO)

### Tela Principal: Reabastecimento Inteligente

**ANTES (v2.2):**
```
[ Upload de arquivo único ]
→ Processa tudo misturado
```

**DEPOIS (v3.0):**
```
┌─────────────────────────────────────────────┐
│  REABASTECIMENTO INTELIGENTE (v3.0)        │
├─────────────────────────────────────────────┤
│                                             │
│  📤 Upload do Arquivo Completo              │
│  [ exemplo_reabastecimento_completo.xlsx ]  │
│                                             │
│  O arquivo deve conter:                     │
│  ✓ Aba PEDIDOS_FORNECEDOR (opcional)        │
│  ✓ Aba PEDIDOS_CD (opcional)                │
│  ✓ Aba TRANSFERENCIAS (opcional)            │
│  ✓ Aba HISTORICO_VENDAS (obrigatória)       │
│                                             │
│  [ Fazer Upload e Processar ]               │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  RESULTADOS POR TIPO DE FLUXO               │
├─────────────────────────────────────────────┤
│                                             │
│  📦 PEDIDOS PARA FORNECEDOR (3 itens)       │
│  [Ver Detalhes] [Download Excel]            │
│                                             │
│  🏢 PEDIDOS DO CD PARA LOJAS (15 itens)     │
│  [Ver Detalhes] [Download Excel]            │
│                                             │
│  🔄 TRANSFERÊNCIAS SUGERIDAS (2 itens)      │
│  [Ver Detalhes] [Download Excel]            │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📊 RELATÓRIOS DE SAÍDA (ATUALIZADOS)

### Relatório 1: pedido_fornecedor_YYYYMMDD.xlsx

**Aba 1: PEDIDOS**
- Fornecedor
- SKU
- Destino
- Tipo_Destino
- Quantidade_Pedido
- Numero_Caixas
- Numero_Paletes (se aplicável)
- Numero_Carretas (se aplicável)
- Custo_Total (se informado)
- Cobertura_Dias
- Ciclo_Usado
- Metodo_Usado

**Aba 2: CONSOLIDACAO** (nova)
- Fornecedor
- Destino
- Total_Unidades
- Total_Caixas
- Total_Paletes
- Total_Carretas
- Custo_Total
- Economia_Frete (vs pedidos individuais)

---

### Relatório 2: pedido_cd_lojas_YYYYMMDD.xlsx

**Aba 1: PEDIDOS**
- CD_Origem
- Loja_Destino
- SKU
- Quantidade_Pedido
- Numero_Caixas
- Cobertura_Dias
- Frentes_Cobertas (se aplicável)
- Alertas (ex: "CD insuficiente")
- Ciclo_Usado
- Metodo_Usado

**Aba 2: ALERTAS_CD** (nova)
- CD_Origem
- SKU
- Estoque_Disponivel
- Total_Solicitado
- Diferenca (negativo = insuficiente)
- Acao_Sugerida ("Pedir de fornecedor")

---

### Relatório 3: transferencias_sugeridas_YYYYMMDD.xlsx

**Aba 1: TRANSFERENCIAS**
- Loja_Origem
- Loja_Destino
- SKU
- Quantidade_Transferir
- Custo_Transferencia
- Custo_Pedido_Novo (comparação)
- Economia
- Prioridade (ALTA, MEDIA, BAIXA)
- Tempo_Resolucao

**Aba 2: ANALISE_ORIGEM**
- Loja_Origem
- SKU
- Estoque_Antes
- Estoque_Apos
- Cobertura_Antes
- Cobertura_Apos
- Status_Apos ("Balanceado")

**Aba 3: ANALISE_DESTINO**
- Loja_Destino
- SKU
- Estoque_Antes
- Estoque_Apos
- Cobertura_Antes
- Cobertura_Apos
- Ruptura_Evitada (Sim/Não)

---

## 🔧 ALTERAÇÕES NO BACKEND

### Arquivo: app.py

**Nova rota para processamento unificado:**

```python
@app.route('/processar_reabastecimento_v3', methods=['POST'])
def processar_reabastecimento_v3():
    """
    Processa arquivo com múltiplas abas de fluxos diferentes
    Versão 3.0 - Abas separadas
    """
    arquivo = request.files['arquivo']

    # Ler todas as abas
    excel_file = pd.ExcelFile(arquivo)
    abas_disponiveis = excel_file.sheet_names

    resultados = {}

    # 1. Processar PEDIDOS_FORNECEDOR (se existe)
    if 'PEDIDOS_FORNECEDOR' in abas_disponiveis:
        df_fornecedor = pd.read_excel(arquivo, sheet_name='PEDIDOS_FORNECEDOR')
        df_historico = pd.read_excel(arquivo, sheet_name='HISTORICO_VENDAS')

        resultado_fornecedor = processar_pedidos_fornecedor(
            df_fornecedor,
            df_historico
        )
        resultados['fornecedor'] = resultado_fornecedor

    # 2. Processar PEDIDOS_CD (se existe)
    if 'PEDIDOS_CD' in abas_disponiveis:
        df_cd = pd.read_excel(arquivo, sheet_name='PEDIDOS_CD')
        df_historico = pd.read_excel(arquivo, sheet_name='HISTORICO_VENDAS')

        resultado_cd = processar_pedidos_cd(
            df_cd,
            df_historico
        )
        resultados['cd_lojas'] = resultado_cd

    # 3. Processar TRANSFERENCIAS (se existe)
    if 'TRANSFERENCIAS' in abas_disponiveis:
        df_transf = pd.read_excel(arquivo, sheet_name='TRANSFERENCIAS')
        df_historico = pd.read_excel(arquivo, sheet_name='HISTORICO_VENDAS')

        resultado_transf = processar_transferencias(
            df_transf,
            df_historico
        )
        resultados['transferencias'] = resultado_transf

    return jsonify(resultados)
```

### Novo arquivo: core/flow_processor.py

```python
"""
Processador de Fluxos de Reabastecimento
Versão 3.0 - Abas separadas por tipo de fluxo
"""

import pandas as pd
from core.replenishment_calculator import ReplenishmentCalculator
from core.demand_calculator import processar_demandas_dataframe

# Ciclos padrão por tipo de fluxo e destino
CICLOS_PADRAO = {
    ('FORNECEDOR', 'CD'): 30,      # Mensal
    ('FORNECEDOR', 'LOJA'): 14,    # Quinzenal
    ('CD', 'LOJA'): 2,             # 2-3x semana
    ('LOJA', 'LOJA'): 1            # Diário
}

def processar_pedidos_fornecedor(df_fornecedor: pd.DataFrame,
                                   df_historico: pd.DataFrame) -> dict:
    """
    Processa aba PEDIDOS_FORNECEDOR

    Args:
        df_fornecedor: DataFrame com pedidos de fornecedor
        df_historico: DataFrame com histórico de vendas

    Returns:
        Dicionário com resultados e relatórios
    """
    # 1. Calcular demandas
    df_demandas = processar_demandas_dataframe(df_historico, modo='automatico')

    resultados = []

    for idx, row in df_fornecedor.iterrows():
        # 2. Obter ciclo adequado
        tipo_origem = 'FORNECEDOR'
        tipo_destino = row.get('Tipo_Destino', 'CD').upper()
        ciclo_key = (tipo_origem, tipo_destino)

        ciclo_padrao = CICLOS_PADRAO.get(ciclo_key, 30)
        ciclo_dias = row.get('Ciclo_Pedido_Dias', ciclo_padrao)

        # 3. Obter demanda calculada
        demanda_info = df_demandas[
            (df_demandas['Loja'] == row['Destino']) &
            (df_demandas['SKU'] == row['SKU'])
        ].iloc[0]

        # 4. Calcular reabastecimento
        nivel_servico = row.get('Nivel_Servico', 0.95)
        calc = ReplenishmentCalculator(nivel_servico)

        resultado = calc.analisar_item(
            loja=row['Destino'],
            sku=row['SKU'],
            demanda_media_mensal=demanda_info['demanda_media_mensal'],
            desvio_padrao_mensal=demanda_info['desvio_padrao_mensal'],
            lead_time_dias=row['Lead_Time_Dias'],
            estoque_disponivel=row['Estoque_Disponivel'],
            estoque_transito=row.get('Estoque_Transito', 0),
            pedidos_abertos=row.get('Pedidos_Abertos', 0),
            lote_minimo=row.get('Lote_Minimo', 1),
            revisao_dias=ciclo_dias
        )

        # 5. Ajustar para consolidação (palete/carreta)
        quantidade_base = resultado['quantidade_pedido']

        if tipo_destino == 'CD':
            # Ajustar para palete/carreta se informado
            multiplo_palete = row.get('Multiplo_Palete', 0)
            multiplo_carreta = row.get('Multiplo_Carreta', 0)

            quantidade_final = ajustar_para_consolidacao(
                quantidade_base,
                row.get('Lote_Minimo', 1),
                multiplo_palete,
                multiplo_carreta
            )
        else:
            quantidade_final = quantidade_base

        # 6. Adicionar informações do fluxo
        resultado.update({
            'Fornecedor': row['Fornecedor'],
            'Destino': row['Destino'],
            'Tipo_Destino': tipo_destino,
            'Ciclo_Usado': ciclo_dias,
            'Quantidade_Original': quantidade_base,
            'Quantidade_Final': quantidade_final,
            'Foi_Consolidado': quantidade_final > quantidade_base
        })

        resultados.append(resultado)

    df_resultado = pd.DataFrame(resultados)

    return {
        'pedidos': df_resultado,
        'consolidacao': calcular_consolidacao(df_resultado),
        'total_itens': len(df_resultado),
        'total_unidades': df_resultado['Quantidade_Final'].sum()
    }


def processar_pedidos_cd(df_cd: pd.DataFrame,
                         df_historico: pd.DataFrame) -> dict:
    """
    Processa aba PEDIDOS_CD

    Inclui validação de:
    - Disponibilidade no CD
    - Parâmetros de exposição
    - Capacidade da loja
    """
    # Similar ao processar_pedidos_fornecedor
    # Mas com validações específicas de CD→Loja
    pass  # Implementação similar


def processar_transferencias(df_transf: pd.DataFrame,
                             df_historico: pd.DataFrame) -> dict:
    """
    Processa aba TRANSFERENCIAS

    Identifica oportunidades de transferência:
    - Lojas com excesso
    - Lojas com necessidade
    - Viabilidade econômica
    """
    # Implementação de lógica de transferências
    pass


def ajustar_para_consolidacao(quantidade: float,
                              lote_minimo: int,
                              multiplo_palete: int,
                              multiplo_carreta: int) -> int:
    """
    Ajusta quantidade para múltiplos de consolidação

    Ordem de ajuste:
    1. Lote mínimo (caixa)
    2. Palete (se informado)
    3. Carreta (se informado)
    """
    import numpy as np

    # 1. Ajustar para caixa
    if lote_minimo > 0:
        quantidade = np.ceil(quantidade / lote_minimo) * lote_minimo

    # 2. Ajustar para palete
    if multiplo_palete > 0:
        quantidade = np.ceil(quantidade / multiplo_palete) * multiplo_palete

    # 3. Ajustar para carreta
    if multiplo_carreta > 0:
        quantidade = np.ceil(quantidade / multiplo_carreta) * multiplo_carreta

    return int(quantidade)
```

---

## ✅ VANTAGENS DA ABORDAGEM COM ABAS

### 1. Usabilidade
✅ Usuário sabe exatamente onde preencher cada tipo de pedido
✅ Campos específicos e relevantes por contexto
✅ Menos chance de erro (não precisa lembrar valores de `Tipo_Fluxo`)

### 2. Manutenibilidade
✅ Código mais limpo (cada aba = uma função específica)
✅ Validações específicas por tipo
✅ Fácil adicionar novos tipos de fluxo (nova aba)

### 3. Flexibilidade
✅ Usuário pode processar apenas os fluxos relevantes
✅ Não precisa preencher todas as abas
✅ Relatórios separados por tipo

### 4. Escalabilidade
✅ Fácil adicionar novos fluxos (ex: TRANSFERENCIA_CD)
✅ Campos específicos não poluem outras abas
✅ Performance melhor (processa só o necessário)

---

## 📅 CRONOGRAMA REVISADO

### FASE 1 - Estrutura de Abas (2 semanas)
- [ ] Criar processamento de aba PEDIDOS_FORNECEDOR
- [ ] Criar processamento de aba PEDIDOS_CD
- [ ] Adicionar Origem/Destino nos pedidos manuais
- [ ] Atualizar interface para upload unificado
- [ ] Gerar relatórios separados por fluxo
- [ ] Criar arquivo exemplo completo
- [ ] Documentação

### FASE 2 - Consolidação e Exposição (1 semana)
- [ ] Implementar ajuste para palete/carreta
- [ ] Implementar parâmetros de exposição
- [ ] Relatório de consolidação
- [ ] Validação de disponibilidade CD

### FASE 3 - Transferências (2 semanas)
- [ ] Processamento de aba TRANSFERENCIAS
- [ ] Lógica de identificação de oportunidades
- [ ] Análise de viabilidade
- [ ] Relatório de transferências

---

**Status:** 📋 Especificação revisada - Abordagem com abas separadas
**Próximo Passo:** Aprovação e implementação

