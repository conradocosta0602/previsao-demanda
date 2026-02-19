-- ============================================================================
-- MIGRATION V8: Embalagem de Arredondamento por Produto
-- ============================================================================
-- Criado: Janeiro 2026
-- Descricao: Adiciona tabela para armazenar embalagem de arredondamento por produto
--            Esta informação será usada futuramente para arredondar quantidades
--            de pedido para o múltiplo da embalagem do fornecedor
-- ============================================================================

-- ============================================================================
-- TABELA: embalagem_arredondamento
-- Armazena a embalagem de arredondamento (quantidade por caixa) de cada produto
-- ============================================================================

CREATE TABLE IF NOT EXISTS embalagem_arredondamento (
    id SERIAL PRIMARY KEY,

    -- Identificação do produto
    codigo INTEGER NOT NULL UNIQUE,              -- Código do produto

    -- Informações da embalagem
    unidade_compra VARCHAR(10),                  -- Unidade de compra (ex: CX, FD, PC)
    qtd_embalagem DECIMAL(10,2) NOT NULL,        -- Quantidade por embalagem
    unidade_menor VARCHAR(10),                   -- Unidade menor (ex: UN, CA, MT)

    -- Metadados
    data_atualizacao TIMESTAMP DEFAULT NOW(),    -- Quando foi atualizado
    fonte VARCHAR(100),                          -- Arquivo de origem da informação
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para busca por código
CREATE INDEX IF NOT EXISTS idx_embalagem_codigo ON embalagem_arredondamento(codigo);

-- Comentários
COMMENT ON TABLE embalagem_arredondamento IS 'Embalagem de arredondamento por produto - define múltiplo para pedidos';
COMMENT ON COLUMN embalagem_arredondamento.codigo IS 'Código do produto';
COMMENT ON COLUMN embalagem_arredondamento.unidade_compra IS 'Unidade de compra (CX=Caixa, FD=Fardo, PC=Pacote)';
COMMENT ON COLUMN embalagem_arredondamento.qtd_embalagem IS 'Quantidade de unidades menores por embalagem (múltiplo de arredondamento)';
COMMENT ON COLUMN embalagem_arredondamento.unidade_menor IS 'Unidade menor (UN=Unidade, CA=Cartela, MT=Metro)';
COMMENT ON COLUMN embalagem_arredondamento.fonte IS 'Arquivo de origem da informação para rastreabilidade';

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration V8 - Embalagem de Arredondamento criada com sucesso!';
    RAISE NOTICE 'Tabela: embalagem_arredondamento';
    RAISE NOTICE 'Campos: codigo, unidade_compra, qtd_embalagem, unidade_menor';
END $$;
