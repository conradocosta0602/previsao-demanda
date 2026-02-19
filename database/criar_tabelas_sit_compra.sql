-- ============================================================================
-- SCRIPT: Criar Tabelas de Situacao de Compra (SIT_COMPRA)
-- ============================================================================
-- Executa no banco: previsao_demanda
-- Data: Janeiro 2026
-- ============================================================================

-- Tabela: Regras de Situacao de Compra
CREATE TABLE IF NOT EXISTS situacao_compra_regras (
    codigo_situacao VARCHAR(5) PRIMARY KEY,
    descricao VARCHAR(100) NOT NULL,
    bloqueia_compra_automatica BOOLEAN DEFAULT TRUE,
    permite_compra_manual BOOLEAN DEFAULT FALSE,
    cor_alerta VARCHAR(20) DEFAULT '#FF6B6B',
    icone VARCHAR(50) DEFAULT 'block',
    ordem_exibicao INTEGER DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE situacao_compra_regras IS 'Regras de bloqueio por situacao de compra (SIT_COMPRA)';

-- Inserir regras padrao
INSERT INTO situacao_compra_regras (codigo_situacao, descricao, bloqueia_compra_automatica, permite_compra_manual, cor_alerta, icone, ordem_exibicao) VALUES
    ('FL', 'Fora de Linha', TRUE, FALSE, '#DC3545', 'ban', 1),
    ('NC', 'Nao Comprar', TRUE, FALSE, '#DC3545', 'times-circle', 2),
    ('EN', 'Encomenda', TRUE, TRUE, '#FFC107', 'clock', 3),
    ('CO', 'Compra Oportunidade', TRUE, TRUE, '#17A2B8', 'star', 4),
    ('FF', 'Falta no Fornecedor', TRUE, FALSE, '#6C757D', 'truck', 5)
ON CONFLICT (codigo_situacao) DO NOTHING;

-- ============================================================================

-- Tabela: Situacao de Compra por Item/Loja
CREATE TABLE IF NOT EXISTS situacao_compra_itens (
    id SERIAL PRIMARY KEY,
    cod_empresa INTEGER,
    codigo INTEGER,
    sit_compra VARCHAR(5) REFERENCES situacao_compra_regras(codigo_situacao),
    data_inicio DATE DEFAULT CURRENT_DATE,
    data_fim DATE,
    motivo TEXT,
    usuario_alteracao VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cod_empresa, codigo)
);

CREATE INDEX IF NOT EXISTS idx_sit_compra_loja ON situacao_compra_itens(cod_empresa);
CREATE INDEX IF NOT EXISTS idx_sit_compra_codigo ON situacao_compra_itens(codigo);
CREATE INDEX IF NOT EXISTS idx_sit_compra_situacao ON situacao_compra_itens(sit_compra);

COMMENT ON TABLE situacao_compra_itens IS 'Situacao de compra atual por item e loja';

-- ============================================================================

-- View: Itens Bloqueados para Compra Automatica
CREATE OR REPLACE VIEW vw_itens_bloqueados_compra AS
SELECT
    sci.cod_empresa,
    sci.codigo,
    sci.sit_compra,
    scr.descricao as descricao_situacao,
    scr.bloqueia_compra_automatica,
    scr.permite_compra_manual,
    scr.cor_alerta,
    scr.icone,
    sci.data_inicio,
    sci.motivo
FROM situacao_compra_itens sci
JOIN situacao_compra_regras scr ON sci.sit_compra = scr.codigo_situacao
WHERE scr.bloqueia_compra_automatica = TRUE
  AND scr.ativo = TRUE
  AND (sci.data_fim IS NULL OR sci.data_fim >= CURRENT_DATE);

COMMENT ON VIEW vw_itens_bloqueados_compra IS 'Itens bloqueados para compra automatica com detalhes da regra';

-- ============================================================================
-- Verificacao
-- ============================================================================
SELECT 'Tabelas criadas com sucesso!' as status;
SELECT * FROM situacao_compra_regras ORDER BY ordem_exibicao;
