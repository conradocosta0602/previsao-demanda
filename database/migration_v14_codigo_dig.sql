-- Migration v14: Tabela de Codigos DIG (sistema externo)
-- Data: 2026-02-19

-- Tabela para armazenar mapeamento codigo interno -> codigo DIG
CREATE TABLE IF NOT EXISTS codigo_dig (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    codigo_dig VARCHAR(20) NOT NULL,
    descricao VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indice para busca rapida por codigo
CREATE INDEX IF NOT EXISTS idx_codigo_dig_codigo ON codigo_dig(codigo);

-- Comentario na tabela
COMMENT ON TABLE codigo_dig IS 'Mapeamento de codigo interno para codigo DIG (sistema externo)';
COMMENT ON COLUMN codigo_dig.codigo IS 'Codigo interno do produto';
COMMENT ON COLUMN codigo_dig.codigo_dig IS 'Codigo DIG para sistema externo';
