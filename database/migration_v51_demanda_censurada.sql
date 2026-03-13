-- =====================================================
-- MIGRATION V51: Demanda Censurada - Metadata de Ruptura
-- =====================================================
-- Adiciona colunas para rastrear correcao de demanda
-- censurada (vendas=0 por falta de estoque, nao por
-- falta de demanda real).
-- =====================================================

-- PASSO 1: Novas colunas de metadata de censura
ALTER TABLE demanda_pre_calculada
  ADD COLUMN IF NOT EXISTS taxa_disponibilidade NUMERIC(5,4),
  ADD COLUMN IF NOT EXISTS dias_ruptura INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS demanda_censurada_corrigida BOOLEAN DEFAULT false;

-- PASSO 2: Atualizar registros existentes (todos sem correcao)
UPDATE demanda_pre_calculada
SET demanda_censurada_corrigida = false,
    dias_ruptura = 0
WHERE demanda_censurada_corrigida IS NULL;

-- PASSO 3: Recriar view com novas colunas
DROP VIEW IF EXISTS vw_demanda_efetiva CASCADE;

CREATE VIEW vw_demanda_efetiva AS
SELECT
    id,
    cod_produto,
    cnpj_fornecedor,
    cod_empresa,
    ano,
    mes,
    semana,
    tipo_granularidade,
    data_inicio_semana,
    -- Demanda efetiva: ajuste manual se existir, senao calculada
    COALESCE(ajuste_manual, demanda_prevista) as demanda_efetiva,
    demanda_prevista as demanda_calculada,
    ajuste_manual,
    (ajuste_manual IS NOT NULL) as tem_ajuste_manual,
    demanda_diaria_base,
    desvio_padrao,
    fator_sazonal,
    fator_tendencia_yoy,
    classificacao_tendencia,
    valor_ano_anterior,
    variacao_vs_aa,
    limitador_aplicado,
    metodo_usado,
    categoria_serie,
    data_calculo,
    ajuste_manual_data,
    ajuste_manual_usuario,
    ajuste_manual_motivo,
    dias_historico,
    total_vendido_historico,
    -- Demanda diaria efetiva: divide por 7 (semanal) ou 30 (mensal)
    CASE
        WHEN tipo_granularidade = 'semanal'
        THEN COALESCE(ajuste_manual, demanda_prevista) / 7.0
        ELSE COALESCE(ajuste_manual, demanda_prevista) / 30.0
    END AS demanda_diaria_efetiva,
    -- V51: Metadata de censura
    taxa_disponibilidade,
    dias_ruptura,
    demanda_censurada_corrigida
FROM demanda_pre_calculada;

-- PASSO 4: Comentarios
COMMENT ON COLUMN demanda_pre_calculada.taxa_disponibilidade IS
    'Taxa media de disponibilidade no historico (0.0 a 1.0). NULL = sem dados de estoque.';
COMMENT ON COLUMN demanda_pre_calculada.dias_ruptura IS
    'Total de dias com ruptura (vendas=0, estoque=0) nos ultimos 730 dias.';
COMMENT ON COLUMN demanda_pre_calculada.demanda_censurada_corrigida IS
    'True se a previsao usou serie historica corrigida por censura de ruptura.';

-- =====================================================
-- FIM DA MIGRATION V51
-- =====================================================
