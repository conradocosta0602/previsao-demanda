-- Migration V11: Permitir pedido automático para itens FF (Falta no Fornecedor)
-- Data: 2026-02-11
-- Autor: Valter Lino
--
-- Justificativa:
-- Itens com situação FF (Falta no Fornecedor) devem ter pedido calculado
-- automaticamente. O fato do fornecedor estar sem estoque não significa
-- que não devemos tentar comprar - o fornecedor pode regularizar a situação.
--
-- Mudança:
-- FF: bloqueia_compra_automatica = TRUE  → FALSE
-- FF: permite_compra_manual = FALSE → TRUE

-- Atualizar regra FF
UPDATE situacao_compra_regras
SET bloqueia_compra_automatica = FALSE,
    permite_compra_manual = TRUE
WHERE codigo_situacao = 'FF';

-- Verificar resultado
SELECT codigo_situacao, descricao, bloqueia_compra_automatica, permite_compra_manual
FROM situacao_compra_regras
WHERE ativo = TRUE
ORDER BY codigo_situacao;

-- Resumo das regras após migration:
-- CO (Compra Oportunidade): bloqueia=FALSE, manual=TRUE  → CALCULA PEDIDO
-- EN (Encomenda):           bloqueia=TRUE,  manual=TRUE  → NÃO CALCULA
-- FF (Falta Fornecedor):    bloqueia=FALSE, manual=TRUE  → CALCULA PEDIDO (alterado)
-- FL (Fora de Linha):       bloqueia=TRUE,  manual=FALSE → NÃO CALCULA
-- NC (Não Comprar):         bloqueia=TRUE,  manual=FALSE → NÃO CALCULA
