-- =====================================================
-- Migration V13: Fator de Tendencia YoY (Year-over-Year)
-- =====================================================
-- Data: Fevereiro 2026
-- Autor: Valter Lino / Claude (Anthropic)
--
-- Objetivo: Adicionar colunas para armazenar fator de tendencia
-- baseado no crescimento Year-over-Year, corrigindo subestimacao
-- em itens com crescimento historico consistente.
--
-- Problema identificado: Fornecedor ZAGONEL com crescimento real
-- de +29% (2024->2025) estava sendo projetado com -18% de queda
-- porque os metodos estatisticos (SMA, WMA, EMA) nao capturam
-- tendencias de crescimento em series sazonais.
--
-- Solucao: Fator de tendencia YoY calculado via media geometrica
-- (CAGR simplificado) com amortecimento de 70% e limites 0.7-1.4.
-- =====================================================

-- 1. Adicionar coluna fator_tendencia_yoy
ALTER TABLE demanda_pre_calculada
ADD COLUMN IF NOT EXISTS fator_tendencia_yoy NUMERIC(6,4) DEFAULT 1.0;

COMMENT ON COLUMN demanda_pre_calculada.fator_tendencia_yoy IS
'Fator de tendencia Year-over-Year. Valores: 0.7 (forte queda) a 1.4 (forte crescimento). 1.0 = estavel.';

-- 2. Adicionar coluna classificacao_tendencia
ALTER TABLE demanda_pre_calculada
ADD COLUMN IF NOT EXISTS classificacao_tendencia VARCHAR(30) DEFAULT 'nao_calculado';

COMMENT ON COLUMN demanda_pre_calculada.classificacao_tendencia IS
'Classificacao da tendencia: forte_crescimento (>1.15), crescimento (>1.05), estavel, queda (<0.95), forte_queda (<0.85), nao_calculado, dados_insuficientes.';

-- 3. Adicionar indice para consultas por classificacao de tendencia
CREATE INDEX IF NOT EXISTS idx_demanda_pre_calc_tendencia
ON demanda_pre_calculada(classificacao_tendencia);

-- 4. Adicionar coluna na tabela de historico tambem
ALTER TABLE demanda_pre_calculada_historico
ADD COLUMN IF NOT EXISTS fator_tendencia_yoy NUMERIC(6,4);

ALTER TABLE demanda_pre_calculada_historico
ADD COLUMN IF NOT EXISTS classificacao_tendencia VARCHAR(30);

-- 5. Atualizar a view vw_demanda_efetiva para incluir as novas colunas
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
    fator_tendencia_yoy,          -- NOVO: Fator de tendencia YoY
    classificacao_tendencia,       -- NOVO: Classificacao da tendencia
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

-- 6. Comentario na view atualizada
COMMENT ON VIEW vw_demanda_efetiva IS
'View que retorna demanda efetiva (ajuste manual se existir, senao calculada). Inclui fator_tendencia_yoy (v5.7).';

-- 7. View de analise de tendencias por fornecedor
CREATE OR REPLACE VIEW vw_tendencia_fornecedor AS
SELECT
    cnpj_fornecedor,
    classificacao_tendencia,
    COUNT(*) as qtd_itens,
    AVG(fator_tendencia_yoy) as fator_medio,
    MIN(fator_tendencia_yoy) as fator_min,
    MAX(fator_tendencia_yoy) as fator_max
FROM demanda_pre_calculada
WHERE data_calculo >= CURRENT_DATE - INTERVAL '7 days'
  AND classificacao_tendencia != 'nao_calculado'
GROUP BY cnpj_fornecedor, classificacao_tendencia
ORDER BY cnpj_fornecedor, classificacao_tendencia;

COMMENT ON VIEW vw_tendencia_fornecedor IS
'Resumo de tendencias por fornecedor. Util para identificar fornecedores com itens em crescimento ou queda.';

-- =====================================================
-- FIM DA MIGRATION V13
-- =====================================================
