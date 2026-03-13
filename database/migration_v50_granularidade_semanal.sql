-- =====================================================
-- Migration V50: Granularidade Semanal em demanda_pre_calculada
-- Data: Marco 2026
-- Adiciona suporte a previsao semanal (ISO week) na tabela
-- de demanda pre-calculada, mantendo compatibilidade com
-- registros mensais existentes.
-- =====================================================

-- PASSO 1: Adicionar novas colunas
ALTER TABLE demanda_pre_calculada
    ADD COLUMN IF NOT EXISTS semana INTEGER,
    ADD COLUMN IF NOT EXISTS tipo_granularidade VARCHAR(10) DEFAULT 'mensal',
    ADD COLUMN IF NOT EXISTS data_inicio_semana DATE;

-- PASSO 2: Preencher tipo_granularidade para registros existentes
UPDATE demanda_pre_calculada
SET tipo_granularidade = 'mensal'
WHERE tipo_granularidade IS NULL;

-- PASSO 3: Tornar tipo_granularidade NOT NULL
ALTER TABLE demanda_pre_calculada
    ALTER COLUMN tipo_granularidade SET NOT NULL,
    ALTER COLUMN tipo_granularidade SET DEFAULT 'mensal';

-- PASSO 4: Permitir mes NULL (para registros semanais)
ALTER TABLE demanda_pre_calculada
    ALTER COLUMN mes DROP NOT NULL;

-- PASSO 5: Recriar indice UNIQUE funcional
-- O indice antigo era: (cod_produto, cnpj_fornecedor, COALESCE(cod_empresa,0), ano, mes)
-- O novo inclui semana para suportar ambas as granularidades sem colisao:
--   Mensal: COALESCE(semana,0)=0, COALESCE(mes,0)=1..12  -> 12 slots/ano
--   Semanal: COALESCE(semana,0)=1..53, COALESCE(mes,0)=0 -> 53 slots/ano
DROP INDEX IF EXISTS uk_demanda_pre_calc;

CREATE UNIQUE INDEX uk_demanda_pre_calc
ON demanda_pre_calculada (
    cod_produto,
    cnpj_fornecedor,
    COALESCE(cod_empresa, 0),
    ano,
    COALESCE(semana, 0),
    COALESCE(mes, 0)
);

-- PASSO 6: Constraint de consistencia
-- Garante que registros mensais tem mes e nao tem semana, e vice-versa
ALTER TABLE demanda_pre_calculada
    DROP CONSTRAINT IF EXISTS chk_granularidade_consistente;

ALTER TABLE demanda_pre_calculada
    ADD CONSTRAINT chk_granularidade_consistente CHECK (
        (tipo_granularidade = 'mensal'  AND semana IS NULL AND mes BETWEEN 1 AND 12)
        OR
        (tipo_granularidade = 'semanal' AND semana BETWEEN 1 AND 53 AND mes IS NULL)
    );

-- PASSO 7: Indices de performance para queries semanais
CREATE INDEX IF NOT EXISTS idx_demanda_pre_calc_semanal
ON demanda_pre_calculada (cnpj_fornecedor, ano, semana)
WHERE tipo_granularidade = 'semanal';

CREATE INDEX IF NOT EXISTS idx_demanda_pre_calc_tipo_gran
ON demanda_pre_calculada (tipo_granularidade, ano);

-- PASSO 8: Recriar view vw_demanda_efetiva com colunas novas
CREATE OR REPLACE VIEW vw_demanda_efetiva AS
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
    END AS demanda_diaria_efetiva
FROM demanda_pre_calculada;

-- PASSO 9: Comentarios
COMMENT ON COLUMN demanda_pre_calculada.semana IS
    'Semana ISO-8601 (1-53). NULL para registros mensais.';
COMMENT ON COLUMN demanda_pre_calculada.tipo_granularidade IS
    'Granularidade do registro: mensal ou semanal.';
COMMENT ON COLUMN demanda_pre_calculada.data_inicio_semana IS
    'Primeiro dia (segunda-feira) da semana ISO. NULL para registros mensais.';

-- =====================================================
-- FIM DA MIGRATION V50
-- =====================================================
