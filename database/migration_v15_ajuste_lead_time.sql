-- Migration v15: Ajuste de lead time - remover delay operacional + transit CD 10->15
-- Data: Marco 2026
-- Versao: v6.25
--
-- Contexto:
-- 1. Delay operacional de 5 dias foi removido do calculo de lead time (afetava todos os pedidos)
-- 2. Transit time CD->loja aumentado de 10 para 15 dias (absorve os 5 dias removidos)
-- Resultado: Pedido direto loja fica com LT real do fornecedor (sem +5d)
--            Pedido centralizado mantem o mesmo LT total (LT_forn + 15 = LT_forn + 5 + 10)

-- Atualizar transit time CD->loja de 10 para 15 dias
UPDATE parametros_globais
SET valor = '15',
    descricao = 'Dias de lead time para transferencia CD->loja (inclui 5d operacional)'
WHERE chave = 'dias_transferencia_padrao_compra';
