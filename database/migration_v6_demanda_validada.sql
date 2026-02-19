-- ============================================================================
-- MIGRATION V6: Sistema de Demanda Validada e Pedido Planejado
-- ============================================================================
-- Criado: Janeiro 2026
-- Descricao: Adiciona tabelas para validacao de demanda e pedidos planejados
-- ============================================================================

-- ============================================================================
-- TABELA: demanda_validada
-- Armazena a demanda validada pelo usuario para periodos especificos
-- ============================================================================

CREATE TABLE IF NOT EXISTS demanda_validada (
    id SERIAL PRIMARY KEY,

    -- Identificacao do SKU
    cod_produto VARCHAR(20) NOT NULL,
    cod_loja INTEGER NOT NULL,
    cod_fornecedor INTEGER,

    -- Periodo da validacao
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    semana_ano VARCHAR(10),              -- Ex: "2026-S27" para referencia rapida

    -- Valores de demanda
    demanda_diaria NUMERIC(12,4),        -- Demanda media diaria do periodo
    demanda_total_periodo NUMERIC(12,2), -- Demanda total do periodo

    -- Controle de validacao
    data_validacao TIMESTAMP DEFAULT NOW(),
    usuario_validacao VARCHAR(100),

    -- Versionamento e status
    versao INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'validado', -- rascunho, validado, utilizado
    ativo BOOLEAN DEFAULT TRUE,            -- FALSE = sobrescrito por nova validacao

    -- Observacoes
    observacao TEXT,

    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_demanda_validada_produto ON demanda_validada(cod_produto);
CREATE INDEX IF NOT EXISTS idx_demanda_validada_loja ON demanda_validada(cod_loja);
CREATE INDEX IF NOT EXISTS idx_demanda_validada_fornecedor ON demanda_validada(cod_fornecedor);
CREATE INDEX IF NOT EXISTS idx_demanda_validada_periodo ON demanda_validada(data_inicio, data_fim);
CREATE INDEX IF NOT EXISTS idx_demanda_validada_semana ON demanda_validada(semana_ano);
CREATE INDEX IF NOT EXISTS idx_demanda_validada_ativo ON demanda_validada(ativo) WHERE ativo = TRUE;

-- Indice composto para busca rapida
CREATE INDEX IF NOT EXISTS idx_demanda_validada_busca ON demanda_validada(cod_produto, cod_loja, data_inicio, data_fim) WHERE ativo = TRUE;

COMMENT ON TABLE demanda_validada IS 'Demanda validada pelo usuario para periodos especificos - usada em pedidos planejados';
COMMENT ON COLUMN demanda_validada.demanda_diaria IS 'Demanda media diaria calculada para o periodo';
COMMENT ON COLUMN demanda_validada.demanda_total_periodo IS 'Demanda total do periodo (demanda_diaria * dias)';
COMMENT ON COLUMN demanda_validada.ativo IS 'FALSE indica que foi sobrescrito por nova validacao do mesmo periodo';

-- ============================================================================
-- TABELA: pedido_planejado_log
-- Log de pedidos planejados gerados (para rastreabilidade)
-- ============================================================================

CREATE TABLE IF NOT EXISTS pedido_planejado_log (
    id SERIAL PRIMARY KEY,

    -- Identificacao
    cod_fornecedor INTEGER,
    nome_fornecedor VARCHAR(200),

    -- Datas do calculo
    data_emissao_real DATE,              -- Data real em que o pedido foi gerado
    data_emissao_calculada DATE,         -- Data "simulada" de emissao (com offset de lead time)

    -- Periodo de demanda coberto
    periodo_demanda_inicio DATE,
    periodo_demanda_fim DATE,

    -- Resumo
    qtd_itens INTEGER,
    valor_total NUMERIC(14,2),

    -- Usuario e controle
    usuario_geracao VARCHAR(100),
    data_geracao TIMESTAMP DEFAULT NOW(),

    -- Parametros utilizados (snapshot)
    parametros_utilizados JSONB,

    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pedido_planejado_fornecedor ON pedido_planejado_log(cod_fornecedor);
CREATE INDEX IF NOT EXISTS idx_pedido_planejado_periodo ON pedido_planejado_log(periodo_demanda_inicio, periodo_demanda_fim);
CREATE INDEX IF NOT EXISTS idx_pedido_planejado_data ON pedido_planejado_log(data_geracao);

COMMENT ON TABLE pedido_planejado_log IS 'Log de pedidos planejados gerados pelo sistema';

-- ============================================================================
-- FUNCAO: Desativar validacoes antigas quando nova validacao sobrepoe periodo
-- ============================================================================

CREATE OR REPLACE FUNCTION desativar_validacoes_sobrepostas()
RETURNS TRIGGER AS $$
BEGIN
    -- Desativa validacoes anteriores que se sobrepoem ao novo periodo
    UPDATE demanda_validada
    SET ativo = FALSE,
        updated_at = NOW()
    WHERE cod_produto = NEW.cod_produto
      AND cod_loja = NEW.cod_loja
      AND ativo = TRUE
      AND id != NEW.id
      AND (
          -- Sobreposicao: novo periodo contem ou intersecta o antigo
          (NEW.data_inicio <= data_inicio AND NEW.data_fim >= data_fim)  -- Contem
          OR (NEW.data_inicio >= data_inicio AND NEW.data_inicio <= data_fim)  -- Intersecta inicio
          OR (NEW.data_fim >= data_inicio AND NEW.data_fim <= data_fim)  -- Intersecta fim
      );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para executar apos insercao
DROP TRIGGER IF EXISTS trg_desativar_validacoes_sobrepostas ON demanda_validada;
CREATE TRIGGER trg_desativar_validacoes_sobrepostas
    AFTER INSERT ON demanda_validada
    FOR EACH ROW
    EXECUTE FUNCTION desativar_validacoes_sobrepostas();

-- ============================================================================
-- VIEW: Demanda validada ativa (somente registros ativos)
-- ============================================================================

CREATE OR REPLACE VIEW vw_demanda_validada_ativa AS
SELECT
    id,
    cod_produto,
    cod_loja,
    cod_fornecedor,
    data_inicio,
    data_fim,
    semana_ano,
    demanda_diaria,
    demanda_total_periodo,
    data_validacao,
    usuario_validacao,
    versao,
    status,
    observacao
FROM demanda_validada
WHERE ativo = TRUE
  AND status = 'validado';

COMMENT ON VIEW vw_demanda_validada_ativa IS 'Demanda validada ativa - apenas registros validos e nao sobrescritos';

-- ============================================================================
-- FIM DA MIGRATION V6
-- ============================================================================
