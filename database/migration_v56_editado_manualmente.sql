-- Migration V56: Adicionar coluna editado_manualmente
-- Separa conceito de "protecao contra cronjob" (ajuste_manual) de "valor editado pelo usuario" (editado_manualmente)
-- ajuste_manual IS NOT NULL = protecao (cronjob nao sobrescreve)
-- editado_manualmente = TRUE = usuario REALMENTE mudou o valor (amarelo na UI)

-- 1. Adicionar coluna
ALTER TABLE demanda_pre_calculada
ADD COLUMN IF NOT EXISTS editado_manualmente BOOLEAN DEFAULT FALSE;

-- 2. Marcar registros existentes onde ajuste_manual difere significativamente de demanda_prevista
-- Isso detecta itens como 338802 que foram realmente editados (100, 150, 300...)
-- Se ajuste_manual == demanda_prevista, foi salvo sem edicao (apenas validacao)
UPDATE demanda_pre_calculada
SET editado_manualmente = TRUE
WHERE ajuste_manual IS NOT NULL
  AND ABS(COALESCE(ajuste_manual, 0) - COALESCE(demanda_prevista, 0)) > 0.5;

-- 3. Atualizar view para incluir editado_manualmente
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
    COALESCE(editado_manualmente, FALSE) as editado_manualmente,
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
    dias_historico,
    total_vendido_historico,
    data_calculo,
    ajuste_manual_data,
    ajuste_manual_usuario,
    ajuste_manual_motivo,
    taxa_disponibilidade,
    dias_ruptura,
    demanda_censurada_corrigida
FROM demanda_pre_calculada;

-- 4. Indice para queries de editado_manualmente (filtro na UI)
CREATE INDEX IF NOT EXISTS idx_demanda_editado_manualmente
ON demanda_pre_calculada (editado_manualmente)
WHERE editado_manualmente = TRUE;
