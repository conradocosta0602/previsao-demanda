# Proposta de Implementacao: Lead Time Real por Fornecedor/Filial

**Data:** 26/01/2026
**Versao:** 1.2 (Consolidada)

---

## 1. Contexto e Objetivo

### Situacao Atual
- Lead times estavam configurados de forma **generica** (ex: 45 dias fixo para todas as lojas)
- Agora temos **lead times medios reais** por fornecedor e por filial (1.105 fornecedores, 6.205 registros)
- Exemplo HIDRO FILTROS: Loja 1 = 49d, Loja 7 = 40d, Loja 6 = 52d (variacao de 12 dias!)

### Objetivo
- **DESCONTINUAR** o lead time generico antigo em todas as telas e funcionalidades
- **ADOTAR EXCLUSIVAMENTE** o lead time real por fornecedor/filial
- **CENTRALIZAR** a gestao de lead times na tela de Parametros de Fornecedor

---

## 2. Mudanca Principal: Fonte Unica de Lead Time

### ANTES (Descontinuar)
```
┌─────────────────────────────────────────────────────────────────┐
│ Multiplas fontes de lead time:                                  │
│ - cadastro_fornecedores.lead_time_dias (generico)              │
│ - parametros_fornecedor.lead_time_dias (por loja)              │
│ - Fallback hardcoded de 15 dias                                │
│ - Inputs manuais em algumas telas                              │
└─────────────────────────────────────────────────────────────────┘
```

### DEPOIS (Nova Arquitetura)
```
┌─────────────────────────────────────────────────────────────────┐
│ FONTE UNICA: parametros_fornecedor (por CNPJ + Loja)           │
│                                                                 │
│ - Dados importados do arquivo lead_time_dias.xlsx              │
│ - Editavel APENAS na Tela de Parametros de Fornecedor          │
│ - Fallback: media do fornecedor ou 30 dias se nao cadastrado   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. O Que Sera Removido/Alterado

### 3.1 Remocoes de Tela

| Tela | O Que Remover |
|------|---------------|
| Pedido Reabastecimento | Campo de input "Lead Time" nos filtros (se existir) |
| Pedido Planejado | Campo "Data de Emissao" e qualquer input de lead time |
| Modal de Edicao Antigo | Campo lead time individual (sera substituido pela tabela) |
| Exportacoes Excel | Remover coluna de lead time editavel |

### 3.2 Alteracoes no Backend

| Local | Alteracao |
|-------|-----------|
| `app.py` - pedido_fornecedor_integrado | Buscar LT exclusivamente de parametros_fornecedor por (cnpj, loja) |
| `app.py` - pedido_planejado | Buscar LT por (cnpj, loja), remover calculo de data_emissao |
| `app.py` - transferencias | Adicionar busca de LT da loja destino |
| `core/pedido_fornecedor_integrado.py` | Remover fallback de 15 dias, usar media do fornecedor |

### 3.3 Hierarquia de Fallback (Nova)

```python
def obter_lead_time(cnpj, cod_empresa):
    # 1. Buscar lead time especifico da loja
    lt = parametros_fornecedor.get(cnpj, cod_empresa)
    if lt:
        return lt

    # 2. Buscar media do fornecedor (todas as lojas)
    lt_media = parametros_fornecedor.media(cnpj)
    if lt_media:
        return lt_media

    # 3. Fallback padrao (fornecedor sem cadastro)
    return 30  # dias
```

---

## 4. Proposta de Melhorias por Funcionalidade

### 4.1 Tela de Parametros de Fornecedor (PRINCIPAL)

**Proposta: Tabela editavel com parametros por loja no card do fornecedor**

```
+--------------------------------------------------------------------------------+
| HIDRO FILTROS                                                                   |
| CNPJ: 00.192.861/0001-19                                                       |
+--------------------------------------------------------------------------------+
|                                                                                 |
| Parametros por Filial                                          [Salvar Tudo]   |
| ┌─────────────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┬──────┐ |
| │             │ Lj 1  │ Lj 2  │ Lj 3  │ Lj 4  │ Lj 5  │ Lj 6  │ Lj 7  │ Lj 8 │ |
| ├─────────────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┼──────┤ |
| │ Lead Time   │[ 49 ]d│[ 47 ]d│[ 41 ]d│[ 47 ]d│[ 45 ]d│[ 52 ]d│[ 40 ]d│[ 47 ]│ |
| │ Ciclo Ped.  │[  7 ]d│[  7 ]d│[  7 ]d│[  7 ]d│[  7 ]d│[  7 ]d│[  7 ]d│[  7 ]│ |
| │ Ped. Minimo │[ 3k  ]│[ 3k  ]│[ 2.5k]│[ 3k  ]│[ 2.5k]│[ 4k  ]│[ 3k  ]│[ 3.5k│ |
| └─────────────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴──────┘ |
|                                                                                 |
| Cobertura Calculada (Lead Time + Ciclo + Seguranca ABC):                       |
| ┌─────────────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┬──────┐ |
| │ Curva A     │  58d  │  56d  │  50d  │  56d  │  54d  │  61d  │  49d  │  56d │ |
| │ Curva B     │  60d  │  58d  │  52d  │  58d  │  56d  │  63d  │  51d  │  58d │ |
| │ Curva C     │  62d  │  60d  │  54d  │  60d  │  58d  │  65d  │  53d  │  60d │ |
| └─────────────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴──────┘ |
|                                                                                 |
| Resumo: Lead Time Min: 40d | Media: 46d | Max: 52d                             |
+--------------------------------------------------------------------------------+
| [Salvar Alteracoes]                                    [Aplicar para Todas]    |
+--------------------------------------------------------------------------------+
```

**Funcionalidades:**
- Campos editaveis inline (clica e edita direto na tabela)
- Botao "Salvar Alteracoes" para persistir mudancas
- Botao "Aplicar para Todas" para copiar valores de uma loja para as demais
- Linha de cobertura calculada automaticamente (somente leitura)
- Resumo estatistico (min, media, max)

**Esta e a UNICA tela onde lead time pode ser editado.**

---

### 4.2 Pedido de Reabastecimento (pedido_fornecedor_integrado)

**Alteracoes:**
- Remover qualquer campo de input de lead time
- Exibir coluna "Lead Time" (somente leitura) mostrando o valor usado
- Buscar LT de `parametros_fornecedor` por (cnpj, cod_empresa)

| Codigo | Descricao | Loja | **Lead Time** | Cobertura | Qtd Pedido |
|--------|-----------|------|---------------|-----------|------------|
| 123456 | Produto A | 1    | 49d           | 58d (A)   | 100        |
| 123456 | Produto A | 7    | 40d           | 49d (A)   | 120        |

**Tooltip:** "Lead time de HIDRO FILTROS para Loja 1: 49 dias (fonte: parametros_fornecedor)"

---

### 4.3 Pedido Planejado (S&OP)

**Alteracoes:**
- Remover campo "Data de Emissao" da tela
- Remover qualquer input de lead time
- Calculos internos usam LT de `parametros_fornecedor` por (cnpj, cod_empresa)

**Exibicao simplificada:**
- Focar em: Itens, Quantidades, Valores
- Lead time e usado internamente para calculos de cobertura

---

### 4.4 Transferencias

**Alteracoes:**
- Buscar lead time da loja DESTINO de `parametros_fornecedor`
- Usar na formula de urgencia:

```
Urgencia = (Dias ate Ruptura) - (Lead Time da Loja Destino)

Se Urgencia < 0: CRITICO
Se Urgencia < 7: ALTA
Se Urgencia < 14: MEDIA
Senao: BAIXA
```

---

### 4.5 Eventos e Promocoes

**Alteracoes:**
- Alertas baseados no lead time real de cada loja
- Buscar de `parametros_fornecedor`

---

## 5. Sincronizacao de Dados

### 5.1 Migrar dados de cadastro_fornecedores para parametros_fornecedor

```sql
-- Script de sincronizacao inicial
INSERT INTO parametros_fornecedor (cnpj_fornecedor, cod_empresa, lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor, ativo)
SELECT
    cnpj as cnpj_fornecedor,
    cod_empresa::integer,
    lead_time_dias,
    COALESCE(ciclo_pedido_dias, 7),
    COALESCE(faturamento_minimo, 0),
    TRUE
FROM cadastro_fornecedores
WHERE cnpj IS NOT NULL
  AND cod_empresa IS NOT NULL
  AND lead_time_dias IS NOT NULL
ON CONFLICT (cnpj_fornecedor, cod_empresa)
DO UPDATE SET
    lead_time_dias = EXCLUDED.lead_time_dias,
    ciclo_pedido_dias = COALESCE(EXCLUDED.ciclo_pedido_dias, parametros_fornecedor.ciclo_pedido_dias),
    pedido_minimo_valor = COALESCE(EXCLUDED.pedido_minimo_valor, parametros_fornecedor.pedido_minimo_valor);
```

### 5.2 Manter cadastro_fornecedores como referencia (opcional)
- A tabela `cadastro_fornecedores` pode continuar existindo para outros dados
- Mas `lead_time_dias` sera ignorado - fonte unica e `parametros_fornecedor`

---

## 6. Endpoints de API

### 6.1 GET /api/parametros-fornecedor/{cnpj}/lojas

Retorna parametros de todas as lojas:

```json
{
  "cnpj": "00192861000119",
  "nome": "HIDRO FILTROS",
  "parametros": [
    {"cod_empresa": 1, "nome_loja": "Recife", "lead_time_dias": 49, "ciclo_pedido_dias": 7, "pedido_minimo_valor": 3000},
    {"cod_empresa": 7, "nome_loja": "Natal", "lead_time_dias": 40, "ciclo_pedido_dias": 7, "pedido_minimo_valor": 3000}
  ],
  "resumo": {
    "lead_time_min": 40,
    "lead_time_max": 52,
    "lead_time_medio": 45
  }
}
```

### 6.2 POST /api/parametros-fornecedor/{cnpj}/salvar-lote

Salva parametros de multiplas lojas:

```json
{
  "cnpj": "00192861000119",
  "parametros": [
    {"cod_empresa": 1, "lead_time_dias": 45, "ciclo_pedido_dias": 7, "pedido_minimo_valor": 3000},
    {"cod_empresa": 7, "lead_time_dias": 38, "ciclo_pedido_dias": 7, "pedido_minimo_valor": 3000}
  ]
}
```

### 6.3 GET /api/lead-time/{cnpj}/{cod_empresa}

Retorna lead time especifico (para uso interno):

```json
{
  "cnpj": "00192861000119",
  "cod_empresa": 1,
  "lead_time_dias": 49,
  "fonte": "parametros_fornecedor"
}
```

---

## 7. Prioridade de Implementacao

| Prioridade | Tarefa | Esforco | Impacto |
|------------|--------|---------|---------|
| **1** | Sincronizar dados cadastro_fornecedores → parametros_fornecedor | Baixo | **Critico** |
| **2** | Tela Parametros - tabela editavel por loja | Medio | **Alto** |
| **3** | Backend - refatorar para usar fonte unica | Medio | **Alto** |
| **4** | Pedido Reabastecimento - exibir LT (somente leitura) | Baixo | Medio |
| **5** | Pedido Planejado - remover campos de LT/data emissao | Baixo | Medio |
| **6** | Transferencias - urgencia com LT destino | Medio | Alto |
| **7** | Eventos - alertas de LT longo | Baixo | Medio |

---

## 8. Resumo Executivo

### O Que Muda

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Fonte de Lead Time | Multiplas (confuso) | **Unica: parametros_fornecedor** |
| Onde editar | Varios lugares | **Apenas Tela de Parametros** |
| Granularidade | Generico por fornecedor | **Por fornecedor E por loja** |
| Fallback | 15 dias hardcoded | Media do fornecedor ou 30 dias |

### Ganhos Esperados

1. **Simplicidade:** Uma unica fonte de verdade para lead time
2. **Precisao:** Lead time real por loja melhora todos os calculos
3. **Governanca:** Edicao centralizada evita inconsistencias
4. **Rastreabilidade:** Facil auditar de onde veio o lead time usado

### Proximo Passo

Aguardo validacao para iniciar implementacao na seguinte ordem:
1. Sincronizar dados no banco
2. Criar nova tela de parametros com tabela editavel
3. Refatorar backend para fonte unica
4. Atualizar demais telas (remover campos de LT)

---

**Preparado por:** Claude AI
**Para:** Equipe de Planejamento - Ferreira Costa
