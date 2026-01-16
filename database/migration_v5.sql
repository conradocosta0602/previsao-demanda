-- ============================================================================
-- MIGRAÇÃO V5: Novas funcionalidades (Multi-Loja, Transferências, Parâmetros)
-- ============================================================================
-- Execute este script para adicionar as novas tabelas necessárias
-- Data: Janeiro 2026
-- ============================================================================

-- ============================================================================
-- 1. TABELA: Parâmetros de Fornecedor
-- Armazena Lead Time, Ciclo de Pedido e Pedido Mínimo por fornecedor/loja
-- ============================================================================

CREATE TABLE IF NOT EXISTS parametros_fornecedor (
    id SERIAL PRIMARY KEY,
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    nome_fornecedor VARCHAR(200),
    cod_empresa INTEGER NOT NULL,
    tipo_destino VARCHAR(10) DEFAULT 'Loja',
    lead_time_dias INTEGER DEFAULT 15,
    ciclo_pedido_dias INTEGER DEFAULT 7,
    pedido_minimo_valor DECIMAL(15,2) DEFAULT 0,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cnpj_fornecedor, cod_empresa)
);

CREATE INDEX IF NOT EXISTS idx_param_forn_cnpj ON parametros_fornecedor(cnpj_fornecedor);
CREATE INDEX IF NOT EXISTS idx_param_forn_empresa ON parametros_fornecedor(cod_empresa);

COMMENT ON TABLE parametros_fornecedor IS 'Parâmetros de compra por fornecedor e loja/CD';

-- ============================================================================
-- 2. TABELA: Oportunidades de Transferência
-- Armazena sugestões de transferência entre lojas
-- ============================================================================

CREATE TABLE IF NOT EXISTS oportunidades_transferencia (
    id SERIAL PRIMARY KEY,
    cod_produto VARCHAR(20) NOT NULL,
    descricao_produto VARCHAR(200),
    curva_abc VARCHAR(1) DEFAULT 'B',

    -- Origem (loja com excesso)
    loja_origem INTEGER NOT NULL,
    nome_loja_origem VARCHAR(100),
    estoque_origem INTEGER DEFAULT 0,
    cobertura_origem_dias INTEGER DEFAULT 0,

    -- Destino (loja com necessidade)
    loja_destino INTEGER NOT NULL,
    nome_loja_destino VARCHAR(100),
    estoque_destino INTEGER DEFAULT 0,
    cobertura_destino_dias INTEGER DEFAULT 0,

    -- Transferência sugerida
    qtd_sugerida INTEGER NOT NULL,
    valor_estimado DECIMAL(15,2) DEFAULT 0,
    cue DECIMAL(15,2) DEFAULT 0,
    urgencia VARCHAR(20) DEFAULT 'MEDIA',

    -- Controle
    data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado BOOLEAN DEFAULT FALSE,
    data_processamento TIMESTAMP,

    -- Contexto
    grupo_regional INTEGER,
    tipo_pedido VARCHAR(20) DEFAULT 'CD'
);

CREATE INDEX IF NOT EXISTS idx_transf_produto ON oportunidades_transferencia(cod_produto);
CREATE INDEX IF NOT EXISTS idx_transf_origem ON oportunidades_transferencia(loja_origem);
CREATE INDEX IF NOT EXISTS idx_transf_destino ON oportunidades_transferencia(loja_destino);
CREATE INDEX IF NOT EXISTS idx_transf_data ON oportunidades_transferencia(data_geracao);
CREATE INDEX IF NOT EXISTS idx_transf_urgencia ON oportunidades_transferencia(urgencia);

COMMENT ON TABLE oportunidades_transferencia IS 'Sugestões de transferência de estoque entre lojas';

-- ============================================================================
-- 3. TABELA: Regras de Situação de Compra
-- Define comportamento para cada código de situação (FL, NC, EN, etc.)
-- ============================================================================

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

COMMENT ON TABLE situacao_compra_regras IS 'Regras de bloqueio por situação de compra';

-- Inserir regras padrão (não sobrescreve se já existirem)
INSERT INTO situacao_compra_regras (codigo_situacao, descricao, bloqueia_compra_automatica, permite_compra_manual, cor_alerta, icone, ordem_exibicao) VALUES
    ('FL', 'Fora de Linha', TRUE, FALSE, '#DC3545', 'ban', 1),
    ('NC', 'Não Comprar', TRUE, FALSE, '#DC3545', 'times-circle', 2),
    ('EN', 'Encomenda', TRUE, TRUE, '#FFC107', 'clock', 3),
    ('CO', 'Compra Oportunidade', TRUE, TRUE, '#17A2B8', 'star', 4),
    ('FF', 'Falta no Fornecedor', TRUE, FALSE, '#6C757D', 'truck', 5)
ON CONFLICT (codigo_situacao) DO NOTHING;

-- ============================================================================
-- 4. TABELA: Situação de Compra por Item/Loja
-- Armazena a situação atual de cada item por loja
-- ============================================================================

CREATE TABLE IF NOT EXISTS situacao_compra_itens (
    id SERIAL PRIMARY KEY,
    cod_empresa INTEGER NOT NULL,
    codigo INTEGER NOT NULL,
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

COMMENT ON TABLE situacao_compra_itens IS 'Situação de compra atual por item e loja';

-- ============================================================================
-- 5. VIEW: Itens Bloqueados para Compra Automática
-- ============================================================================

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

COMMENT ON VIEW vw_itens_bloqueados_compra IS 'Itens bloqueados para compra automática';

-- ============================================================================
-- FIM DA MIGRAÇÃO V5
-- ============================================================================

-- Para verificar se a migração foi aplicada:
-- SELECT table_name FROM information_schema.tables WHERE table_name IN
--   ('parametros_fornecedor', 'oportunidades_transferencia', 'situacao_compra_regras', 'situacao_compra_itens');
