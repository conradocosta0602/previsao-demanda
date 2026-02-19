-- ============================================================================
-- MIGRATION V9: Sistema de Ajuste Manual de Previsao
-- ============================================================================
-- Criado: Fevereiro 2026
-- Descricao: Adiciona tabelas para ajustes manuais de previsao por item/periodo
-- ============================================================================

-- ============================================================================
-- TABELA: ajuste_previsao
-- Armazena ajustes manuais feitos pelo usuario em previsoes especificas
-- ============================================================================

CREATE TABLE IF NOT EXISTS ajuste_previsao (
    id SERIAL PRIMARY KEY,

    -- Identificacao do item
    cod_produto VARCHAR(20) NOT NULL,
    cod_fornecedor INTEGER,
    nome_fornecedor VARCHAR(200),

    -- Periodo do ajuste (granularidade: mensal, semanal ou diario)
    periodo VARCHAR(20) NOT NULL,          -- Ex: "2026-02-01" (mensal), "2026-S05" (semanal), "2026-02-15" (diario)
    granularidade VARCHAR(10) NOT NULL,    -- 'mensal', 'semanal', 'diario'

    -- Valores
    valor_original NUMERIC(12,2) NOT NULL, -- Valor da previsao estatistica
    valor_ajustado NUMERIC(12,2) NOT NULL, -- Valor ajustado pelo usuario
    diferenca NUMERIC(12,2),               -- valor_ajustado - valor_original
    percentual_ajuste NUMERIC(8,2),        -- ((valor_ajustado - valor_original) / valor_original) * 100

    -- Contexto do ajuste
    motivo VARCHAR(500),                   -- Motivo/justificativa do ajuste

    -- Auditoria
    usuario_ajuste VARCHAR(100),           -- Quem fez o ajuste
    data_ajuste TIMESTAMP DEFAULT NOW(),   -- Quando foi feito

    -- Controle de versao
    versao INTEGER DEFAULT 1,
    ativo BOOLEAN DEFAULT TRUE,            -- FALSE = sobrescrito por novo ajuste

    -- Metadados da previsao original
    metodo_estatistico VARCHAR(50),        -- Metodo usado na previsao original (EMA, WMA, etc)

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_ajuste_previsao_produto ON ajuste_previsao(cod_produto);
CREATE INDEX IF NOT EXISTS idx_ajuste_previsao_fornecedor ON ajuste_previsao(cod_fornecedor);
CREATE INDEX IF NOT EXISTS idx_ajuste_previsao_periodo ON ajuste_previsao(periodo);
CREATE INDEX IF NOT EXISTS idx_ajuste_previsao_ativo ON ajuste_previsao(ativo) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_ajuste_previsao_data ON ajuste_previsao(data_ajuste);

-- Indice composto para busca rapida
CREATE INDEX IF NOT EXISTS idx_ajuste_previsao_busca
    ON ajuste_previsao(cod_produto, periodo, granularidade) WHERE ativo = TRUE;

-- Indice para buscar ajustes de um fornecedor em um periodo
CREATE INDEX IF NOT EXISTS idx_ajuste_previsao_fornecedor_periodo
    ON ajuste_previsao(cod_fornecedor, periodo) WHERE ativo = TRUE;

COMMENT ON TABLE ajuste_previsao IS 'Ajustes manuais de previsao por item/periodo - permite ao usuario refinar previsoes estatisticas';
COMMENT ON COLUMN ajuste_previsao.periodo IS 'Identificador do periodo no formato da granularidade (YYYY-MM-DD, YYYY-SWW, etc)';
COMMENT ON COLUMN ajuste_previsao.ativo IS 'FALSE indica que foi sobrescrito por novo ajuste do mesmo item/periodo';

-- ============================================================================
-- TABELA: ajuste_previsao_historico
-- Historico de todos os ajustes (para auditoria completa)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ajuste_previsao_historico (
    id SERIAL PRIMARY KEY,

    -- Referencia ao ajuste
    ajuste_id INTEGER REFERENCES ajuste_previsao(id),

    -- Snapshot dos dados no momento da alteracao
    cod_produto VARCHAR(20) NOT NULL,
    periodo VARCHAR(20) NOT NULL,
    granularidade VARCHAR(10) NOT NULL,
    valor_original NUMERIC(12,2),
    valor_ajustado NUMERIC(12,2),
    motivo VARCHAR(500),

    -- Auditoria
    usuario_acao VARCHAR(100),
    tipo_acao VARCHAR(20),                 -- 'criacao', 'alteracao', 'exclusao'
    data_acao TIMESTAMP DEFAULT NOW(),

    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ajuste_historico_ajuste ON ajuste_previsao_historico(ajuste_id);
CREATE INDEX IF NOT EXISTS idx_ajuste_historico_produto ON ajuste_previsao_historico(cod_produto);
CREATE INDEX IF NOT EXISTS idx_ajuste_historico_data ON ajuste_previsao_historico(data_acao);

COMMENT ON TABLE ajuste_previsao_historico IS 'Historico completo de ajustes para auditoria';

-- ============================================================================
-- FUNCAO: Desativar ajustes antigos quando novo ajuste sobrepoe
-- ============================================================================

CREATE OR REPLACE FUNCTION desativar_ajustes_sobrepostos()
RETURNS TRIGGER AS $$
BEGIN
    -- Desativa ajustes anteriores do mesmo item/periodo/granularidade
    UPDATE ajuste_previsao
    SET ativo = FALSE,
        updated_at = NOW()
    WHERE cod_produto = NEW.cod_produto
      AND periodo = NEW.periodo
      AND granularidade = NEW.granularidade
      AND ativo = TRUE
      AND id != NEW.id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para executar apos insercao
DROP TRIGGER IF EXISTS trg_desativar_ajustes_sobrepostos ON ajuste_previsao;
CREATE TRIGGER trg_desativar_ajustes_sobrepostos
    AFTER INSERT ON ajuste_previsao
    FOR EACH ROW
    EXECUTE FUNCTION desativar_ajustes_sobrepostos();

-- ============================================================================
-- FUNCAO: Registrar historico de ajustes
-- ============================================================================

CREATE OR REPLACE FUNCTION registrar_historico_ajuste()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO ajuste_previsao_historico (
            ajuste_id, cod_produto, periodo, granularidade,
            valor_original, valor_ajustado, motivo,
            usuario_acao, tipo_acao
        ) VALUES (
            NEW.id, NEW.cod_produto, NEW.periodo, NEW.granularidade,
            NEW.valor_original, NEW.valor_ajustado, NEW.motivo,
            NEW.usuario_ajuste, 'criacao'
        );
    ELSIF TG_OP = 'UPDATE' AND OLD.valor_ajustado != NEW.valor_ajustado THEN
        INSERT INTO ajuste_previsao_historico (
            ajuste_id, cod_produto, periodo, granularidade,
            valor_original, valor_ajustado, motivo,
            usuario_acao, tipo_acao
        ) VALUES (
            NEW.id, NEW.cod_produto, NEW.periodo, NEW.granularidade,
            NEW.valor_original, NEW.valor_ajustado, NEW.motivo,
            NEW.usuario_ajuste, 'alteracao'
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para registrar historico
DROP TRIGGER IF EXISTS trg_registrar_historico_ajuste ON ajuste_previsao;
CREATE TRIGGER trg_registrar_historico_ajuste
    AFTER INSERT OR UPDATE ON ajuste_previsao
    FOR EACH ROW
    EXECUTE FUNCTION registrar_historico_ajuste();

-- ============================================================================
-- VIEW: Ajustes ativos com informacoes completas
-- ============================================================================

CREATE OR REPLACE VIEW vw_ajustes_previsao_ativos AS
SELECT
    a.id,
    a.cod_produto,
    a.cod_fornecedor,
    a.nome_fornecedor,
    a.periodo,
    a.granularidade,
    a.valor_original,
    a.valor_ajustado,
    a.diferenca,
    a.percentual_ajuste,
    a.motivo,
    a.usuario_ajuste,
    a.data_ajuste,
    a.metodo_estatistico,
    a.versao
FROM ajuste_previsao a
WHERE a.ativo = TRUE;

COMMENT ON VIEW vw_ajustes_previsao_ativos IS 'Ajustes de previsao ativos - apenas registros validos e nao sobrescritos';

-- ============================================================================
-- FIM DA MIGRATION V9
-- ============================================================================
