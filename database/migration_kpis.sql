-- Migration: Tabelas para KPIs
-- Data: 2026-02-04

-- ============================================================================
-- TABELA: historico_previsao
-- Armazena previsoes geradas para comparacao com realizado (WMAPE/BIAS)
-- ============================================================================

CREATE TABLE IF NOT EXISTS historico_previsao (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,                         -- Data da previsao
    cod_empresa INTEGER NOT NULL,               -- Filial (0 = todas)
    codigo INTEGER NOT NULL,                    -- Codigo do produto
    qtd_prevista NUMERIC(12,2) NOT NULL,        -- Quantidade prevista
    qtd_realizada NUMERIC(12,2),                -- Quantidade real (preenchida apos realizacao)
    tipo_previsao VARCHAR(20) DEFAULT 'diaria', -- 'diaria', 'semanal', 'mensal'
    modelo VARCHAR(50),                         -- Modelo usado (ex: 'media_movel', 'sazonalidade')
    versao INTEGER DEFAULT 1,                   -- Versao da previsao
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(data, cod_empresa, codigo, tipo_previsao, versao)
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_hist_prev_data ON historico_previsao(data);
CREATE INDEX IF NOT EXISTS idx_hist_prev_empresa ON historico_previsao(cod_empresa);
CREATE INDEX IF NOT EXISTS idx_hist_prev_codigo ON historico_previsao(codigo);
CREATE INDEX IF NOT EXISTS idx_hist_prev_tipo ON historico_previsao(tipo_previsao);

-- ============================================================================
-- TABELA: kpi_snapshot_diario
-- Snapshot diario de KPIs para historico rapido
-- ============================================================================

CREATE TABLE IF NOT EXISTS kpi_snapshot_diario (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    cod_empresa INTEGER,                        -- NULL = geral
    nome_fornecedor VARCHAR(200),               -- NULL = todos
    categoria VARCHAR(200),                     -- Linha1 - NULL = todas
    codigo_linha VARCHAR(10),                   -- Linha3 - NULL = todas

    -- Metricas de Ruptura
    total_skus INTEGER,
    skus_ruptura INTEGER,
    taxa_ruptura NUMERIC(8,4),                  -- Percentual
    dias_ruptura INTEGER,                       -- Dias com ruptura no periodo
    total_dias INTEGER,                         -- Total de dias do periodo

    -- Metricas de Cobertura
    cobertura_media NUMERIC(10,2),              -- Dias de cobertura
    cobertura_minima NUMERIC(10,2),
    cobertura_maxima NUMERIC(10,2),

    -- Metricas de Acuracia (WMAPE/BIAS)
    wmape NUMERIC(8,4),                         -- Percentual
    bias NUMERIC(8,4),                          -- Percentual (pode ser negativo)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_kpi_snap_data ON kpi_snapshot_diario(data);
CREATE INDEX IF NOT EXISTS idx_kpi_snap_empresa ON kpi_snapshot_diario(cod_empresa);
CREATE INDEX IF NOT EXISTS idx_kpi_snap_fornecedor ON kpi_snapshot_diario(nome_fornecedor);

-- ============================================================================
-- VIEW: vw_ruptura_diaria
-- Calcula ruptura diaria por item/loja
-- ============================================================================

CREATE OR REPLACE VIEW vw_ruptura_diaria AS
SELECT
    hed.data,
    hed.cod_empresa,
    hed.codigo,
    cpc.nome_fornecedor,
    cpc.categoria,
    cpc.codigo_linha,
    cpc.descricao_linha,
    hed.estoque_diario,
    CASE WHEN hed.estoque_diario <= 0 THEN 1 ELSE 0 END as em_ruptura,
    COALESCE(hvd.qtd_venda, 0) as qtd_venda
FROM historico_estoque_diario hed
LEFT JOIN cadastro_produtos_completo cpc ON hed.codigo::text = cpc.cod_produto
LEFT JOIN historico_vendas_diario hvd ON hed.data = hvd.data
    AND hed.cod_empresa = hvd.cod_empresa
    AND hed.codigo = hvd.codigo;

-- ============================================================================
-- COMENTARIOS
-- ============================================================================

COMMENT ON TABLE historico_previsao IS 'Armazena historico de previsoes para calculo de WMAPE e BIAS';
COMMENT ON TABLE kpi_snapshot_diario IS 'Snapshot diario de KPIs agregados para consultas rapidas';
COMMENT ON VIEW vw_ruptura_diaria IS 'View para calculo de ruptura diaria por item/loja';
