# Especificação Técnica - Fase 1: Suporte a Múltiplos Fluxos

**Data:** 2024-12-29
**Versão:** 3.0 (Fase 1)
**Prazo:** 2 semanas
**Prioridade:** CRÍTICA

---

## 📋 OBJETIVO DA FASE 1

Adicionar suporte a diferentes tipos de fluxo de reabastecimento, permitindo que o sistema aplique regras específicas (principalmente ciclo de revisão) baseadas na origem e destino do pedido.

**Mudança Principal:**
- Ciclo de revisão deixa de ser GLOBAL (7 dias fixo)
- Passa a ser DINÂMICO baseado no tipo de fluxo

---

## 🎯 ESCOPO

### ✅ Incluído na Fase 1
- [x] Campo `Tipo_Fluxo` no arquivo de entrada
- [x] Campo `Ciclo_Revisao_Dias` (opcional) no arquivo de entrada
- [x] Lógica de ciclo padrão por tipo de fluxo
- [x] Backend adaptado para usar ciclo dinâmico
- [x] Relatório mostrando tipo de fluxo e ciclo usado
- [x] Arquivo exemplo atualizado
- [x] Documentação completa

### ❌ Excluído da Fase 1 (Fases futuras)
- Múltiplos de palete/carreta
- Parâmetros de exposição
- Múltiplas origens
- Transferências
- Validação de capacidade

---

## 📂 ESTRUTURA DO ARQUIVO DE ENTRADA (ATUALIZADA)

### Arquivo: exemplo_reabastecimento_multifluxo.xlsx

#### ABA 1: ESTOQUE_ATUAL (Modificada)

| Coluna | Tipo | Obrig | Novo? | Valores | Padrão | Descrição |
|--------|------|-------|-------|---------|--------|-----------|
| Loja | Texto | ✅ Sim | Não | - | - | Código da loja/CD |
| SKU | Texto | ✅ Sim | Não | - | - | Código do produto |
| **Tipo_Fluxo** | **Texto** | **✅ Sim** | **✅ SIM** | **Ver tabela** | **CD_LOJA** | **Tipo do fluxo** |
| Lead_Time_Dias | Inteiro | ✅ Sim | Não | 1-90 | - | Tempo reposição |
| Estoque_Disponivel | Número | ✅ Sim | Não | >= 0 | - | Estoque físico |
| Nivel_Servico | Decimal | ✅ Sim | Não | 0.80-0.99 | 0.95 | Nível serviço |
| **Ciclo_Revisao_Dias** | **Inteiro** | **⚠️ Não** | **✅ SIM** | **1-90** | **Auto** | **Período revisão** |
| Estoque_Transito | Número | ⚠️ Não | Não | >= 0 | 0 | Em trânsito |
| Pedidos_Abertos | Número | ⚠️ Não | Não | >= 0 | 0 | Em aberto |
| Lote_Minimo | Inteiro | ⚠️ Não | Não | >= 1 | 1 | Múltiplo caixa |

#### ABA 2: HISTORICO_VENDAS (Sem alteração)
Mantém estrutura atual (Loja, SKU, Mes, Vendas, Dias_Com_Estoque, Origem)

---

## 📊 VALORES PERMITIDOS PARA TIPO_FLUXO

| Valor | Descrição | Ciclo Padrão | Lead Time Típico | Uso |
|-------|-----------|--------------|------------------|-----|
| **FORNECEDOR_CD** | Fornecedor → Centro Distribuição | 30 dias | 10-30 dias | Compra upstream |
| **FORNECEDOR_LOJA** | Fornecedor → Loja Direta | 14 dias | 7-21 dias | Compra direta |
| **CD_LOJA** | CD → Loja | 2 dias | 1-3 dias | Distribuição |
| **LOJA_LOJA** | Loja → Loja (Transferência) | 1 dia | 0-1 dia | Transferência |

### Valores Aceitos (Backend)
```python
TIPOS_FLUXO_VALIDOS = [
    'FORNECEDOR_CD',
    'FORNECEDOR_LOJA',
    'CD_LOJA',
    'LOJA_LOJA'
]
```

### Tratamento de Valores Inválidos
- Se `Tipo_Fluxo` não informado: **assume `CD_LOJA`** (comportamento atual)
- Se `Tipo_Fluxo` inválido: **aviso no log + assume `CD_LOJA`**
- Se `Ciclo_Revisao_Dias` não informado: **usa padrão do `Tipo_Fluxo`**
- Se `Ciclo_Revisao_Dias` < 1: **usa 1 dia**
- Se `Ciclo_Revisao_Dias` > 90: **usa 90 dias**

---

## 🔧 ALTERAÇÕES NO BACKEND

### Arquivo: core/replenishment_calculator.py

#### 1. Constantes de Ciclos Padrão (ADICIONAR no topo)

```python
# Ciclos de revisão padrão por tipo de fluxo (em dias)
CICLOS_PADRAO_POR_FLUXO = {
    'FORNECEDOR_CD': 30,      # Mensal - pedidos grandes, upstream
    'FORNECEDOR_LOJA': 14,    # Quinzenal - direto na loja
    'CD_LOJA': 2,             # 2-3x semana - distribuição rápida
    'LOJA_LOJA': 1            # Diário - transferências emergenciais
}

# Tipo de fluxo padrão se não informado
TIPO_FLUXO_PADRAO = 'CD_LOJA'

# Tipos de fluxo válidos
TIPOS_FLUXO_VALIDOS = [
    'FORNECEDOR_CD',
    'FORNECEDOR_LOJA',
    'CD_LOJA',
    'LOJA_LOJA'
]
```

#### 2. Função Auxiliar (ADICIONAR)

```python
def obter_ciclo_revisao(tipo_fluxo: str, ciclo_informado: float = None) -> int:
    """
    Obtém o ciclo de revisão adequado baseado no tipo de fluxo

    Args:
        tipo_fluxo: Tipo do fluxo de reabastecimento
        ciclo_informado: Ciclo informado pelo usuário (opcional)

    Returns:
        Ciclo de revisão em dias (inteiro)
    """
    # Se usuário informou ciclo explicitamente, usar esse valor
    if ciclo_informado is not None and pd.notna(ciclo_informado):
        ciclo = int(ciclo_informado)
        # Validar limites
        if ciclo < 1:
            print(f"[AVISO] Ciclo {ciclo} < 1, ajustando para 1 dia")
            return 1
        if ciclo > 90:
            print(f"[AVISO] Ciclo {ciclo} > 90, ajustando para 90 dias")
            return 90
        return ciclo

    # Se não informou, usar padrão do tipo de fluxo
    tipo_fluxo_upper = str(tipo_fluxo).upper().strip()

    # Validar tipo de fluxo
    if tipo_fluxo_upper not in TIPOS_FLUXO_VALIDOS:
        print(f"[AVISO] Tipo_Fluxo '{tipo_fluxo}' inválido, usando padrão: {TIPO_FLUXO_PADRAO}")
        tipo_fluxo_upper = TIPO_FLUXO_PADRAO

    return CICLOS_PADRAO_POR_FLUXO.get(tipo_fluxo_upper, CICLOS_PADRAO_POR_FLUXO[TIPO_FLUXO_PADRAO])
```

#### 3. Atualizar Função processar_reabastecimento_completo (MODIFICAR)

**Linha ~260-280 (onde processa cada item):**

```python
# CÓDIGO ATUAL (aproximado):
for idx, row in df_estoque.iterrows():
    # ... código existente ...

    # Usar nível de serviço específico do item, se disponível
    if 'Nivel_Servico' in row and pd.notna(row['Nivel_Servico']):
        calc = ReplenishmentCalculator(row['Nivel_Servico'])
    else:
        calc = ReplenishmentCalculator(nivel_servico_global)

    # Período de revisão
    revisao_dias = parametros.get('revisao_dias', 7)  # ← PROBLEMA: FIXO!
```

**NOVO CÓDIGO:**

```python
for idx, row in df_estoque.iterrows():
    # ... código existente ...

    # 1. Obter tipo de fluxo
    tipo_fluxo = row.get('Tipo_Fluxo', TIPO_FLUXO_PADRAO)
    if pd.isna(tipo_fluxo):
        tipo_fluxo = TIPO_FLUXO_PADRAO

    # 2. Obter ciclo de revisão (específico do item ou padrão do tipo)
    ciclo_informado = row.get('Ciclo_Revisao_Dias', None)
    revisao_dias = obter_ciclo_revisao(tipo_fluxo, ciclo_informado)

    # 3. Usar nível de serviço específico do item, se disponível
    if 'Nivel_Servico' in row and pd.notna(row['Nivel_Servico']):
        calc = ReplenishmentCalculator(row['Nivel_Servico'])
    else:
        calc = ReplenishmentCalculator(nivel_servico_global)

    # 4. Análise do item (agora usa revisao_dias dinâmico)
    resultado = calc.analisar_item(
        loja=row['Loja'],
        sku=row['SKU'],
        demanda_media_mensal=demanda_info['demanda_media_mensal'],
        desvio_padrao_mensal=demanda_info['desvio_padrao_mensal'],
        lead_time_dias=row['Lead_Time_Dias'],
        estoque_disponivel=row['Estoque_Disponivel'],
        estoque_transito=row.get('Estoque_Transito', 0),
        pedidos_abertos=row.get('Pedidos_Abertos', 0),
        lote_minimo=row.get('Lote_Minimo', 1),
        revisao_dias=revisao_dias  # ← AGORA É DINÂMICO!
    )

    # 5. Adicionar informações do tipo de fluxo ao resultado
    resultado['Tipo_Fluxo'] = tipo_fluxo
    resultado['Ciclo_Revisao_Dias'] = revisao_dias
```

---

## 📊 ALTERAÇÕES NO RELATÓRIO DE SAÍDA

### Colunas do Excel Gerado (ordem)

**Colunas Existentes (manter):**
1. Loja
2. SKU
3. Demanda_Media_Mensal
4. Desvio_Padrao_Mensal
5. Lead_Time_Dias
6. Estoque_Disponivel
7. Estoque_Transito
8. Estoque_Efetivo
9. Ponto_Pedido
10. Estoque_Seguranca
11. Quantidade_Pedir
12. Cobertura_Dias_Atual
13. Cobertura_Dias_Apos_Pedido
14. Risco_Ruptura
15. Deve_Pedir
16. Metodo_Usado

**Colunas Novas (adicionar):**
17. **Tipo_Fluxo** ← NOVO
18. **Ciclo_Revisao_Dias** ← NOVO
19. **Demanda_Durante_Revisao** ← NOVO (para análise)

### Formatação no Excel

**Coluna Tipo_Fluxo:**
- Formatação condicional:
  - `FORNECEDOR_CD`: fundo azul claro
  - `FORNECEDOR_LOJA`: fundo verde claro
  - `CD_LOJA`: fundo amarelo claro
  - `LOJA_LOJA`: fundo laranja claro

**Coluna Ciclo_Revisao_Dias:**
- Formato: número inteiro
- Destaque: negrito se foi auto-detectado (não informado pelo usuário)

---

## 🌐 ALTERAÇÕES NO FRONTEND

### Arquivo: templates/reabastecimento.html

**Seção de Configurações (REMOVER campo revisao_dias global):**

```html
<!-- REMOVER ESTE BLOCO: -->
<div class="config-compact">
    <label for="revisao_dias">Revisão (dias):</label>
    <input type="number" id="revisao_dias" name="revisao_dias" value="7" min="1" max="30">
    <p style="font-size: 0.7em; color: #666; margin-top: 4px;">
        Período de revisão de estoque
    </p>
</div>
```

**ADICIONAR aviso informativo:**

```html
<div style="padding: 10px; background: #e3f2fd; border-left: 3px solid #2196f3; border-radius: 4px; margin-bottom: 12px; font-size: 0.8em;">
    <strong>🔄 Ciclo de Revisão:</strong><br>
    Agora definido por tipo de fluxo no arquivo de entrada (coluna Tipo_Fluxo).
    <br>
    <small>
        • FORNECEDOR_CD: 30 dias<br>
        • FORNECEDOR_LOJA: 14 dias<br>
        • CD_LOJA: 2 dias<br>
        • LOJA_LOJA: 1 dia
    </small>
</div>
```

### Arquivo: static/js/reabastecimento.js

**Adicionar coluna Tipo_Fluxo na tabela de resultados:**

```javascript
// Mapeamento de nomes de tipo de fluxo para exibição
const TIPOS_FLUXO_NOMES = {
    'FORNECEDOR_CD': 'Fornecedor → CD',
    'FORNECEDOR_LOJA': 'Fornecedor → Loja',
    'CD_LOJA': 'CD → Loja',
    'LOJA_LOJA': 'Loja → Loja'
};

// Cores por tipo de fluxo
const TIPOS_FLUXO_CORES = {
    'FORNECEDOR_CD': '#bbdefb',      // Azul claro
    'FORNECEDOR_LOJA': '#c8e6c9',    // Verde claro
    'CD_LOJA': '#fff9c4',            // Amarelo claro
    'LOJA_LOJA': '#ffe0b2'           // Laranja claro
};
```

**Na função de renderização da tabela, adicionar colunas:**

```javascript
// Após coluna SKU, adicionar:
<td style="padding: 6px; border-bottom: 1px solid #eee; font-size: 0.75em;">
    <span style="background: ${TIPOS_FLUXO_CORES[item.Tipo_Fluxo] || '#eee'};
                 padding: 2px 6px;
                 border-radius: 4px;
                 white-space: nowrap;">
        ${TIPOS_FLUXO_NOMES[item.Tipo_Fluxo] || item.Tipo_Fluxo}
    </span>
</td>
<td style="padding: 6px; border-bottom: 1px solid #eee; text-align: center;">
    ${item.Ciclo_Revisao_Dias} dias
</td>
```

**Atualizar cabeçalho da tabela:**

```html
<tr>
    <th>Loja</th>
    <th>SKU</th>
    <th>Tipo Fluxo</th>          <!-- NOVO -->
    <th>Ciclo</th>               <!-- NOVO -->
    <th>Dem. Média</th>
    <!-- ... demais colunas ... -->
</tr>
```

---

## 📄 ARQUIVO EXEMPLO ATUALIZADO

### Script: gerar_exemplo_reabastecimento_multifluxo.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera arquivo de exemplo para Reabastecimento com Múltiplos Fluxos
Versão 3.0 - Fase 1
"""

import pandas as pd
from datetime import datetime, timedelta
import random

def gerar_exemplo_multifluxo():
    """
    Gera exemplo com diferentes tipos de fluxo
    """

    # ============================================================
    # ABA 1: ESTOQUE_ATUAL (COM MÚLTIPLOS FLUXOS)
    # ============================================================

    dados_estoque = [
        # CD comprando de Fornecedor
        {
            'Loja': 'CD_PRINCIPAL',
            'SKU': 'PROD_001',
            'Tipo_Fluxo': 'FORNECEDOR_CD',
            'Lead_Time_Dias': 15,
            'Estoque_Disponivel': 5000,
            'Estoque_Transito': 2000,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.95,
            'Ciclo_Revisao_Dias': 30,  # Mensal (explícito)
            'Lote_Minimo': 24
        },
        {
            'Loja': 'CD_REGIONAL',
            'SKU': 'PROD_002',
            'Tipo_Fluxo': 'FORNECEDOR_CD',
            'Lead_Time_Dias': 20,
            'Estoque_Disponivel': 3000,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.95,
            # Ciclo_Revisao_Dias NÃO informado: usa padrão 30 dias
            'Lote_Minimo': 12
        },

        # Loja comprando direto de Fornecedor
        {
            'Loja': 'LOJA_MEGA',
            'SKU': 'PROD_003',
            'Tipo_Fluxo': 'FORNECEDOR_LOJA',
            'Lead_Time_Dias': 10,
            'Estoque_Disponivel': 200,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.98,
            'Ciclo_Revisao_Dias': 14,  # Quinzenal
            'Lote_Minimo': 12
        },

        # Lojas comprando de CD (distribuição regular)
        {
            'Loja': 'LOJA_01',
            'SKU': 'PROD_001',
            'Tipo_Fluxo': 'CD_LOJA',
            'Lead_Time_Dias': 2,
            'Estoque_Disponivel': 50,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.99,
            # Ciclo_Revisao_Dias NÃO informado: usa padrão 2 dias
            'Lote_Minimo': 6
        },
        {
            'Loja': 'LOJA_02',
            'SKU': 'PROD_001',
            'Tipo_Fluxo': 'CD_LOJA',
            'Lead_Time_Dias': 3,
            'Estoque_Disponivel': 30,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 20,
            'Nivel_Servico': 0.99,
            'Ciclo_Revisao_Dias': 3,  # 2x semana (explícito)
            'Lote_Minimo': 6
        },
        {
            'Loja': 'LOJA_03',
            'SKU': 'PROD_002',
            'Tipo_Fluxo': 'CD_LOJA',
            'Lead_Time_Dias': 2,
            'Estoque_Disponivel': 15,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.95,
            'Lote_Minimo': 10
        },

        # Transferência Loja → Loja (emergencial)
        {
            'Loja': 'LOJA_04',
            'SKU': 'PROD_001',
            'Tipo_Fluxo': 'LOJA_LOJA',
            'Lead_Time_Dias': 1,
            'Estoque_Disponivel': 5,
            'Estoque_Transito': 0,
            'Pedidos_Abertos': 0,
            'Nivel_Servico': 0.90,
            # Ciclo_Revisao_Dias NÃO informado: usa padrão 1 dia
            'Lote_Minimo': 1  # Sem restrição de embalagem
        },
    ]

    df_estoque = pd.DataFrame(dados_estoque)

    # ============================================================
    # ABA 2: HISTORICO_VENDAS (mesmo padrão anterior)
    # ============================================================

    # ... gerar histórico de vendas similar ao script anterior ...
    # (código omitido por brevidade)

    # ============================================================
    # ABA 3: INSTRUCOES
    # ============================================================

    instrucoes = [
        ['INSTRUÇÕES - REABASTECIMENTO MULTIFLUXO (v3.0)', ''],
        ['', ''],
        ['NOVIDADE - Versão 3.0:', 'Suporte a múltiplos tipos de fluxo!'],
        ['', ''],
        ['ABA 1: ESTOQUE_ATUAL', ''],
        ['', ''],
        ['NOVAS COLUNAS (obrigatórias):', ''],
        ['  Tipo_Fluxo', 'Tipo do fluxo de reabastecimento'],
        ['', ''],
        ['Valores aceitos:', ''],
        ['  FORNECEDOR_CD', 'Fornecedor → Centro de Distribuição (ciclo: 30 dias)'],
        ['  FORNECEDOR_LOJA', 'Fornecedor → Loja Direta (ciclo: 14 dias)'],
        ['  CD_LOJA', 'CD → Loja (ciclo: 2 dias)'],
        ['  LOJA_LOJA', 'Loja → Loja Transferência (ciclo: 1 dia)'],
        ['', ''],
        ['NOVAS COLUNAS (opcionais):', ''],
        ['  Ciclo_Revisao_Dias', 'Período de revisão em dias'],
        ['  ', 'Se não informado: usa padrão do Tipo_Fluxo'],
        ['  ', 'Se informado: sobrescreve o padrão'],
        ['', ''],
        ['IMPORTANTE:', ''],
        ['  • Ciclo correto = Quantidade adequada ao fluxo'],
        ['  • CD tem ciclos longos (30 dias) = pedidos maiores'],
        ['  • Lojas têm ciclos curtos (2 dias) = pedidos menores'],
        ['', ''],
        # ... resto das instruções ...
    ]

    df_instrucoes = pd.DataFrame(instrucoes, columns=['Campo', 'Descrição'])

    # ============================================================
    # SALVAR ARQUIVO
    # ============================================================

    caminho = 'exemplo_reabastecimento_multifluxo.xlsx'

    with pd.ExcelWriter(caminho, engine='openpyxl') as writer:
        df_estoque.to_excel(writer, sheet_name='ESTOQUE_ATUAL', index=False)
        df_vendas.to_excel(writer, sheet_name='HISTORICO_VENDAS', index=False)
        df_instrucoes.to_excel(writer, sheet_name='INSTRUCOES', index=False)

    print(f"[OK] Criado: {caminho}")
    print()
    print("Exemplo contém:")
    print("  - 1 CD comprando de fornecedor (ciclo 30 dias)")
    print("  - 1 loja comprando direto de fornecedor (ciclo 14 dias)")
    print("  - 3 lojas comprando de CD (ciclo 2-3 dias)")
    print("  - 1 transferência loja-loja (ciclo 1 dia)")

    return caminho


if __name__ == '__main__':
    print("=" * 60)
    print("  GERADOR DE EXEMPLO - MULTIFLUXO v3.0")
    print("=" * 60)
    print()

    gerar_exemplo_multifluxo()

    print()
    print("Pronto para uso!")
```

---

## ✅ CHECKLIST DE IMPLEMENTAÇÃO

### Backend
- [ ] Adicionar constantes `CICLOS_PADRAO_POR_FLUXO`, `TIPOS_FLUXO_VALIDOS`
- [ ] Criar função `obter_ciclo_revisao()`
- [ ] Modificar `processar_reabastecimento_completo()`:
  - [ ] Ler campo `Tipo_Fluxo`
  - [ ] Ler campo `Ciclo_Revisao_Dias`
  - [ ] Chamar `obter_ciclo_revisao()`
  - [ ] Passar `revisao_dias` dinâmico para `analisar_item()`
  - [ ] Adicionar `Tipo_Fluxo` e `Ciclo_Revisao_Dias` ao resultado
- [ ] Adicionar colunas ao Excel de saída

### Frontend
- [ ] Remover campo global `revisao_dias` do HTML
- [ ] Adicionar aviso sobre ciclo por tipo de fluxo
- [ ] Adicionar constantes `TIPOS_FLUXO_NOMES` e `TIPOS_FLUXO_CORES` no JS
- [ ] Adicionar coluna "Tipo Fluxo" na tabela de resultados
- [ ] Adicionar coluna "Ciclo" na tabela de resultados
- [ ] Formatação colorida por tipo de fluxo

### Arquivo Exemplo
- [ ] Criar `gerar_exemplo_reabastecimento_multifluxo.py`
- [ ] Gerar exemplos dos 4 tipos de fluxo
- [ ] Adicionar aba de instruções completa
- [ ] Testar geração do arquivo

### Documentação
- [ ] Atualizar `NIVEL_SERVICO_POR_ITEM.md` (mencionar multifluxo)
- [ ] Criar `GUIA_MULTIFLUXO.md` (guia do usuário)
- [ ] Atualizar `ALTERACOES_REABASTECIMENTO.md`
- [ ] Atualizar documento Word (seção 7.2)

### Testes
- [ ] Teste 1: Arquivo sem `Tipo_Fluxo` (deve usar padrão)
- [ ] Teste 2: `FORNECEDOR_CD` sem ciclo (deve usar 30 dias)
- [ ] Teste 3: `CD_LOJA` com ciclo explícito (deve respeitar)
- [ ] Teste 4: Tipo inválido (deve avisar e usar padrão)
- [ ] Teste 5: Ciclo < 1 ou > 90 (deve ajustar)
- [ ] Teste 6: Relatório mostra colunas novas
- [ ] Teste 7: Interface exibe tipos corretamente

---

## 🧪 CASOS DE TESTE

### Caso 1: CD comprando de Fornecedor
**Entrada:**
```
Tipo_Fluxo: FORNECEDOR_CD
Ciclo_Revisao_Dias: (não informado)
Demanda_Media_Mensal: 3000
```

**Esperado:**
```
Ciclo usado: 30 dias (padrão)
Demanda_Durante_Revisao: 3000 (100/dia × 30)
Quantidade maior que sistema atual (7 dias)
```

### Caso 2: Loja comprando de CD
**Entrada:**
```
Tipo_Fluxo: CD_LOJA
Ciclo_Revisao_Dias: (não informado)
Demanda_Media_Mensal: 120
```

**Esperado:**
```
Ciclo usado: 2 dias (padrão)
Demanda_Durante_Revisao: 8 (4/dia × 2)
Quantidade menor que sistema atual (7 dias)
```

### Caso 3: Retrocompatibilidade
**Entrada:**
```
(arquivo antigo sem Tipo_Fluxo nem Ciclo_Revisao_Dias)
```

**Esperado:**
```
Tipo_Fluxo: CD_LOJA (padrão)
Ciclo usado: 2 dias (padrão de CD_LOJA)
Aviso no log: "Tipo_Fluxo não informado"
```

---

## 📈 MÉTRICAS DE SUCESSO

| Métrica | Antes (v2.2) | Meta (v3.0) |
|---------|--------------|-------------|
| **Pedidos CD sub-dimensionados** | 40% | < 10% |
| **Pedidos Loja super-dimensionados** | 30% | < 10% |
| **Usuários ajustando manualmente** | 45% | < 20% |
| **Confiança na ferramenta** | 6/10 | 8/10 |

---

## 📅 CRONOGRAMA

| Atividade | Responsável | Prazo | Status |
|-----------|-------------|-------|--------|
| **Semana 1** | | | |
| Backend: Constantes e função | Dev | 2 dias | ⬜ |
| Backend: Modificar processamento | Dev | 2 dias | ⬜ |
| Frontend: HTML + JS | Dev | 1 dia | ⬜ |
| **Semana 2** | | | |
| Script exemplo | Dev | 1 dia | ⬜ |
| Testes unitários | Dev | 1 dia | ⬜ |
| Testes integração | QA | 1 dia | ⬜ |
| Documentação | Dev | 1 dia | ⬜ |
| Revisão final | Tech Lead | 1 dia | ⬜ |

---

**Status:** 📋 Especificação completa - Pronto para implementação
**Próximo Passo:** Aprovação e início do desenvolvimento
