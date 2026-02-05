-- =====================================================
-- Migration V12: Tabela de Demanda Pre-Calculada
-- =====================================================
-- Objetivo: Armazenar demanda calculada diariamente via cronjob
-- para garantir integridade entre Tela Demanda e Tela Pedido
-- =====================================================

-- 1. Tabela principal de demanda pre-calculada
CREATE TABLE IF NOT EXISTS demanda_pre_calculada (
    id SERIAL PRIMARY KEY,

    -- Identificadores
    cod_produto VARCHAR(20) NOT NULL,
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    cod_empresa INTEGER,                    -- NULL = consolidado todas as lojas

    -- Periodo (ano-mes)
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,                   -- 1-12

    -- Valores calculados pelo cronjob
    demanda_prevista NUMERIC(12,2) NOT NULL,        -- Demanda do mes (unidades)
    demanda_diaria_base NUMERIC(12,4) NOT NULL,     -- Demanda diaria base
    desvio_padrao NUMERIC(12,4),                    -- Desvio padrao
    fator_sazonal NUMERIC(6,4) DEFAULT 1.0,         -- Fator sazonal aplicado

    -- Ano anterior (para comparacao)
    valor_ano_anterior NUMERIC(12,2),               -- Venda real do mesmo mes ano anterior
    variacao_vs_aa NUMERIC(6,4),                    -- Variacao percentual vs AA
    limitador_aplicado BOOLEAN DEFAULT FALSE,       -- Se V11 foi aplicado

    -- Metodologia usada
    metodo_usado VARCHAR(50),                       -- sma, wma, ema, tendencia, sazonal, tsb
    categoria_serie VARCHAR(20),                    -- muito_curta, curta, media, longa

    -- Ajuste manual (sobrepoe calculo automatico)
    ajuste_manual NUMERIC(12,2),                    -- Valor ajustado manualmente (NULL = usar calculado)
    ajuste_manual_data TIMESTAMP,                   -- Data do ajuste
    ajuste_manual_usuario VARCHAR(100),             -- Usuario que ajustou
    ajuste_manual_motivo TEXT,                      -- Motivo do ajuste

    -- Metadata
    data_calculo TIMESTAMP NOT NULL DEFAULT NOW(),  -- Quando foi calculado
    dias_historico INTEGER,                         -- Dias de historico usados
    total_vendido_historico NUMERIC(12,2),          -- Total vendido no periodo base

    -- Constraints
    CONSTRAINT uk_demanda_pre_calc UNIQUE (cod_produto, cnpj_fornecedor, cod_empresa, ano, mes)
);

-- 2. Indices para performance
CREATE INDEX IF NOT EXISTS idx_demanda_pre_calc_fornecedor
ON demanda_pre_calculada(cnpj_fornecedor);

CREATE INDEX IF NOT EXISTS idx_demanda_pre_calc_produto
ON demanda_pre_calculada(cod_produto);

CREATE INDEX IF NOT EXISTS idx_demanda_pre_calc_periodo
ON demanda_pre_calculada(ano, mes);

CREATE INDEX IF NOT EXISTS idx_demanda_pre_calc_data
ON demanda_pre_calculada(data_calculo);

CREATE INDEX IF NOT EXISTS idx_demanda_pre_calc_ajuste
ON demanda_pre_calculada(ajuste_manual)
WHERE ajuste_manual IS NOT NULL;

-- 3. Tabela de historico de calculos (auditoria)
CREATE TABLE IF NOT EXISTS demanda_pre_calculada_historico (
    id SERIAL PRIMARY KEY,

    -- Referencia ao registro original
    demanda_id INTEGER,                             -- ID na tabela principal (pode ser NULL se deletado)
    cod_produto VARCHAR(20) NOT NULL,
    cnpj_fornecedor VARCHAR(20) NOT NULL,
    cod_empresa INTEGER,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,

    -- Valores no momento do snapshot
    demanda_prevista NUMERIC(12,2),
    demanda_diaria_base NUMERIC(12,4),
    desvio_padrao NUMERIC(12,4),
    fator_sazonal NUMERIC(6,4),
    valor_ano_anterior NUMERIC(12,2),
    metodo_usado VARCHAR(50),
    ajuste_manual NUMERIC(12,2),

    -- Metadata do historico
    data_snapshot TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo_operacao VARCHAR(20) NOT NULL,             -- 'calculo_diario', 'ajuste_manual', 'recalculo'

    -- Indices
    CONSTRAINT idx_historico_produto_periodo
        CHECK (cod_produto IS NOT NULL AND ano IS NOT NULL AND mes IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_demanda_hist_produto
ON demanda_pre_calculada_historico(cod_produto, ano, mes);

CREATE INDEX IF NOT EXISTS idx_demanda_hist_data
ON demanda_pre_calculada_historico(data_snapshot);

-- 4. Tabela de controle de execucao do cronjob
CREATE TABLE IF NOT EXISTS demanda_calculo_execucao (
    id SERIAL PRIMARY KEY,
    data_execucao TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo VARCHAR(20) NOT NULL,                      -- 'cronjob_diario', 'manual', 'recalculo_fornecedor'
    status VARCHAR(20) NOT NULL,                    -- 'iniciado', 'sucesso', 'erro', 'parcial'

    -- Metricas
    total_itens_processados INTEGER DEFAULT 0,
    total_itens_erro INTEGER DEFAULT 0,
    total_fornecedores INTEGER DEFAULT 0,
    tempo_execucao_ms INTEGER,

    -- Filtros (se execucao parcial)
    cnpj_fornecedor_filtro VARCHAR(20),             -- Se recalculo de fornecedor especifico

    -- Detalhes
    detalhes JSONB,                                 -- Erros, warnings, etc

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 5. View para facilitar consultas (demanda efetiva = ajuste manual OU calculada)
CREATE OR REPLACE VIEW vw_demanda_efetiva AS
SELECT
    id,
    cod_produto,
    cnpj_fornecedor,
    cod_empresa,
    ano,
    mes,
    -- Demanda efetiva: ajuste manual se existir, senao calculada
    COALESCE(ajuste_manual, demanda_prevista) as demanda_efetiva,
    demanda_prevista as demanda_calculada,
    ajuste_manual,
    (ajuste_manual IS NOT NULL) as tem_ajuste_manual,
    demanda_diaria_base,
    desvio_padrao,
    fator_sazonal,
    valor_ano_anterior,
    variacao_vs_aa,
    limitador_aplicado,
    metodo_usado,
    categoria_serie,
    data_calculo,
    ajuste_manual_data,
    ajuste_manual_usuario,
    ajuste_manual_motivo
FROM demanda_pre_calculada;

-- 6. Funcao para registrar ajuste manual
CREATE OR REPLACE FUNCTION registrar_ajuste_demanda(
    p_cod_produto VARCHAR(20),
    p_cnpj_fornecedor VARCHAR(20),
    p_cod_empresa INTEGER,
    p_ano INTEGER,
    p_mes INTEGER,
    p_valor_ajuste NUMERIC(12,2),
    p_usuario VARCHAR(100),
    p_motivo TEXT
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Atualizar ou inserir na tabela principal
    INSERT INTO demanda_pre_calculada (
        cod_produto, cnpj_fornecedor, cod_empresa, ano, mes,
        demanda_prevista, demanda_diaria_base,
        ajuste_manual, ajuste_manual_data, ajuste_manual_usuario, ajuste_manual_motivo
    ) VALUES (
        p_cod_produto, p_cnpj_fornecedor, p_cod_empresa, p_ano, p_mes,
        p_valor_ajuste, p_valor_ajuste / 30.0,
        p_valor_ajuste, NOW(), p_usuario, p_motivo
    )
    ON CONFLICT (cod_produto, cnpj_fornecedor, cod_empresa, ano, mes)
    DO UPDATE SET
        ajuste_manual = p_valor_ajuste,
        ajuste_manual_data = NOW(),
        ajuste_manual_usuario = p_usuario,
        ajuste_manual_motivo = p_motivo
    RETURNING id INTO v_id;

    -- Registrar no historico
    INSERT INTO demanda_pre_calculada_historico (
        demanda_id, cod_produto, cnpj_fornecedor, cod_empresa, ano, mes,
        demanda_prevista, ajuste_manual, tipo_operacao
    ) VALUES (
        v_id, p_cod_produto, p_cnpj_fornecedor, p_cod_empresa, p_ano, p_mes,
        p_valor_ajuste, p_valor_ajuste, 'ajuste_manual'
    );

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- 7. Comentarios nas tabelas
COMMENT ON TABLE demanda_pre_calculada IS 'Demanda pre-calculada diariamente via cronjob. Fonte unica para Tela Demanda e Tela Pedido.';
COMMENT ON COLUMN demanda_pre_calculada.ajuste_manual IS 'Valor ajustado manualmente. Se preenchido, sobrepoe demanda_prevista.';
COMMENT ON COLUMN demanda_pre_calculada.limitador_aplicado IS 'True se o limitador V11 (-40% a +50% vs AA) foi aplicado.';
COMMENT ON VIEW vw_demanda_efetiva IS 'View que retorna demanda efetiva (ajuste manual se existir, senao calculada).';

-- =====================================================
-- FIM DA MIGRATION V12
-- =====================================================
