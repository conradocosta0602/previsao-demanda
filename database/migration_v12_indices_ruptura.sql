-- Migration: Índices para otimização de queries de ruptura
-- Data: 2026-02-09

-- Índice para situacao_compra_itens
CREATE INDEX IF NOT EXISTS idx_sci_codigo_empresa
ON situacao_compra_itens(codigo, cod_empresa);

CREATE INDEX IF NOT EXISTS idx_sci_sit_compra
ON situacao_compra_itens(sit_compra);

-- Índice composto para historico_estoque_diario (busca de itens abastecidos)
CREATE INDEX IF NOT EXISTS idx_hed_codigo_empresa_estoque
ON historico_estoque_diario(codigo, cod_empresa, estoque_diario)
WHERE estoque_diario > 0;

-- Índice para busca por período
CREATE INDEX IF NOT EXISTS idx_hed_data_codigo_empresa
ON historico_estoque_diario(data, codigo, cod_empresa);

-- Comentário
COMMENT ON INDEX idx_sci_codigo_empresa IS 'Índice para filtro de situação de compra por item/empresa';
COMMENT ON INDEX idx_hed_codigo_empresa_estoque IS 'Índice parcial para itens já abastecidos (estoque > 0)';
