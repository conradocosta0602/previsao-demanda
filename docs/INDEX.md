# Documentacao do Sistema de Previsao de Demanda

## Estrutura de Pastas

```
docs/
├── metodologia/     # Documentos sobre metodologia de calculo
├── implementacao/   # Detalhes de implementacao e mudancas
├── guias/           # Guias de uso e manuais
└── validacao/       # Documentos de validacao e testes
```

## Metodologia (`metodologia/`)

| Documento | Descricao |
|-----------|-----------|
| `DOCUMENTACAO_CALCULO_REABASTECIMENTO.md` | Metodologia completa de calculo de reabastecimento |
| `DOCUMENTACAO_KPIS.md` | KPIs e metricas do sistema |
| `MELHORIAS_CALCULO_DEMANDA.md` | Melhorias implementadas no calculo de demanda |
| `NIVEL_SERVICO_POR_ITEM.md` | Configuracao de nivel de servico por item |
| `PADRONIZACAO_NOMENCLATURA_METODOS.md` | Padronizacao de nomes dos metodos estatisticos |
| `PROPOSTA_LEAD_TIME_POR_FILIAL.md` | Lead time diferenciado por filial |
| `SOLUCAO_SAZONALIDADE.md` | Tratamento de sazonalidade |
| `ABORDAGEM_HIBRIDA_RUPTURAS.md` | Abordagem para tratamento de rupturas |
| `COMPARATIVO_ABORDAGENS.md` | Comparativo entre abordagens de calculo |
| `ANALISE_PROBLEMA_SAZONALIDADE.md` | Analise de problemas com sazonalidade |

## Implementacao (`implementacao/`)

| Documento | Descricao |
|-----------|-----------|
| `IMPLEMENTACAO_CONCLUIDA.md` | Status de implementacoes concluidas |
| `STATUS_IMPLEMENTACAO_COMPLETO.md` | Status geral do sistema |
| `ALTERACOES_REABASTECIMENTO.md` | Alteracoes no modulo de reabastecimento |
| `CORRECAO_TRANSFERENCIAS.md` | Correcoes no modulo de transferencias |
| `INTEGRACAO_ARQUIVOS.md` | Integracao entre arquivos do sistema |
| `RESUMO_NOVOS_MODULOS_PEDIDO.md` | Resumo dos novos modulos de pedido |

## Guias de Uso (`guias/`)

| Documento | Descricao |
|-----------|-----------|
| `GUIA_MODOS_REABASTECIMENTO.md` | Como usar os modos de reabastecimento |
| `GUIA_USO_PEDIDOS_MANUAIS.md` | Guia para pedidos manuais |
| `PEDIDO_MANUAL_SIMPLIFICADO.md` | Fluxo simplificado de pedido manual |
| `ESPECIFICACAO_ABAS_POR_FLUXO.md` | Especificacao das abas por fluxo |

## Validacao (`validacao/`)

| Documento | Descricao |
|-----------|-----------|
| `VALIDACAO_*.md` | Documentos de validacao de modulos |
| `RESUMO_VALIDACOES.md` | Resumo das validacoes realizadas |
| `TESTES_SERIES_CURTAS.md` | Testes com series temporais curtas |

---

## Verificacoes de Conformidade (V01-V27)

O sistema possui 22 verificacoes automaticas de conformidade:

| Codigo | Verificacao |
|--------|-------------|
| V01 | Modulos carregam sem erro |
| V02 | 6 metodos estatisticos disponiveis |
| V03 | DemandCalculator retorna valores corretos |
| V04 | Sazonalidade em [0.5, 2.0] |
| V05 | Saneamento de rupturas funciona |
| V06 | Normalizacao por dias totais |
| V07 | Corte de data funciona |
| V08 | Pedido usa formula correta |
| V09 | Padrao de compra integrado |
| V10 | Estoque de seguranca por curva ABC |
| V11 | Limitador de tendencia |
| V12 | Fator de tendencia YoY |
| V13-V14 | Limites de variacao |
| V20-V25 | Validacoes de transferencias e arredondamento |
| V26 | Limitador de cobertura 90d para itens TSB |
| V27 | Completude de dados de embalagem por fornecedor |

---

*Ultima atualizacao: Fevereiro 2026*
