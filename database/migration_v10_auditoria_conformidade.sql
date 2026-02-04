-- ============================================================================
-- MIGRATION V10: Sistema de Auditoria e Conformidade de Metodologia
-- ============================================================================
-- Criado: Fevereiro 2026
-- Descricao: Tabelas para auditoria de conformidade do modelo de calculo
-- ============================================================================

-- ============================================================================
-- TABELA: auditoria_conformidade
-- Armazena resultados do checklist diario de conformidade
-- ============================================================================

CREATE TABLE IF NOT EXISTS auditoria_conformidade (
    id SERIAL PRIMARY KEY,

    -- Identificacao da execucao
    data_execucao TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo VARCHAR(20) NOT NULL,          -- 'cronjob_diario', 'manual', 'tempo_real'

    -- Resultado geral
    status VARCHAR(15) NOT NULL,        -- 'aprovado', 'reprovado', 'alerta'
    total_verificacoes INTEGER NOT NULL,
    verificacoes_ok INTEGER NOT NULL,
    verificacoes_falha INTEGER NOT NULL DEFAULT 0,
    verificacoes_alerta INTEGER NOT NULL DEFAULT 0,

    -- Detalhes das verificacoes (JSON)
    detalhes JSONB,
    /*
    Estrutura do JSONB detalhes:
    {
        "verificacoes": [
            {
                "id": 1,
                "nome": "modulos_carregam",
                "descricao": "Módulos carregam sem erro",
                "status": "ok|falha|alerta",
                "tempo_ms": 123,
                "mensagem": "Todos os módulos carregaram corretamente",
                "valor_esperado": "sem_erro",
                "valor_obtido": "sem_erro"
            },
            ...
        ],
        "resumo": {
            "tempo_total_ms": 2300,
            "memoria_mb": 45.2
        }
    }
    */

    -- Metricas de execucao
    tempo_execucao_ms INTEGER,

    -- Alerta enviado?
    alerta_enviado BOOLEAN DEFAULT FALSE,
    alerta_destinatarios TEXT[],

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_audit_conf_data ON auditoria_conformidade(data_execucao);
CREATE INDEX IF NOT EXISTS idx_audit_conf_status ON auditoria_conformidade(status);
CREATE INDEX IF NOT EXISTS idx_audit_conf_tipo ON auditoria_conformidade(tipo);

COMMENT ON TABLE auditoria_conformidade IS 'Registro de execucoes do checklist de conformidade de metodologia';

-- ============================================================================
-- TABELA: auditoria_calculos
-- Armazena detalhes de cada calculo realizado (demanda ou pedido)
-- ============================================================================

CREATE TABLE IF NOT EXISTS auditoria_calculos (
    id SERIAL PRIMARY KEY,

    -- Identificacao do calculo
    data_calculo TIMESTAMP NOT NULL DEFAULT NOW(),
    tipo_calculo VARCHAR(20) NOT NULL,  -- 'demanda', 'pedido', 'transferencia'

    -- Contexto do calculo
    cod_produto VARCHAR(20),
    cod_empresa INTEGER,
    cod_fornecedor INTEGER,
    nome_fornecedor VARCHAR(200),

    -- Metodologia usada
    metodo_usado VARCHAR(50),           -- 'sma', 'wma', 'ema', 'tendencia', 'sazonal', 'tsb', etc
    categoria_serie VARCHAR(20),        -- 'muito_curta', 'curta', 'media', 'longa'
    confianca VARCHAR(20),              -- 'muito_baixa', 'baixa', 'media', 'alta'

    -- Parametros de entrada (resumo)
    parametros_entrada JSONB,
    /*
    Estrutura:
    {
        "dias_historico": 730,
        "granularidade": "mensal",
        "cobertura_estoque": 0.65,
        "saneamento_rupturas": true,
        "fator_sazonal": 1.2
    }
    */

    -- Resultado do calculo
    resultado JSONB,
    /*
    Estrutura para demanda:
    {
        "demanda_diaria": 10.5,
        "desvio_padrao": 3.2,
        "tendencia": "estavel",
        "zeros_pct": 15.5
    }

    Estrutura para pedido:
    {
        "quantidade_pedido": 500,
        "estoque_seguranca": 120,
        "cobertura_dias": 30,
        "valor_pedido": 5000.00
    }
    */

    -- Validacao
    validacao_ok BOOLEAN DEFAULT TRUE,
    validacao_detalhes JSONB,
    /*
    Estrutura:
    {
        "regras_validadas": ["demanda_positiva", "desvio_valido", "metodo_consistente"],
        "regras_violadas": [],
        "alertas": []
    }
    */

    -- Observacoes
    observacoes TEXT,

    -- Usuario/processo que executou
    executado_por VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_audit_calc_data ON auditoria_calculos(data_calculo);
CREATE INDEX IF NOT EXISTS idx_audit_calc_tipo ON auditoria_calculos(tipo_calculo);
CREATE INDEX IF NOT EXISTS idx_audit_calc_produto ON auditoria_calculos(cod_produto);
CREATE INDEX IF NOT EXISTS idx_audit_calc_fornecedor ON auditoria_calculos(cod_fornecedor);
CREATE INDEX IF NOT EXISTS idx_audit_calc_metodo ON auditoria_calculos(metodo_usado);
CREATE INDEX IF NOT EXISTS idx_audit_calc_validacao ON auditoria_calculos(validacao_ok);

-- Indice composto para buscas frequentes
CREATE INDEX IF NOT EXISTS idx_audit_calc_busca
    ON auditoria_calculos(cod_fornecedor, data_calculo DESC);

COMMENT ON TABLE auditoria_calculos IS 'Registro detalhado de cada calculo de demanda ou pedido para rastreabilidade';

-- ============================================================================
-- TABELA: configuracao_checklist
-- Define as verificacoes do checklist de conformidade
-- ============================================================================

CREATE TABLE IF NOT EXISTS configuracao_checklist (
    id SERIAL PRIMARY KEY,

    -- Identificacao da verificacao
    codigo VARCHAR(50) NOT NULL UNIQUE,  -- 'V01_MODULOS', 'V02_METODOS', etc
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,

    -- Configuracao
    ativo BOOLEAN DEFAULT TRUE,
    ordem_execucao INTEGER DEFAULT 0,
    criticidade VARCHAR(20) DEFAULT 'alerta',  -- 'bloqueante', 'alerta', 'info'

    -- Criterios de validacao (JSON)
    criterios JSONB,
    /*
    Estrutura:
    {
        "tipo": "import_check|valor_esperado|range_check|funcao_custom",
        "modulo": "core.demand_calculator",
        "classe": "DemandCalculator",
        "metodo": "calcular_demanda_sma",
        "entrada_teste": [10, 20, 30],
        "saida_esperada": {"min": 18, "max": 22},
        "tolerancia": 0.05
    }
    */

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir verificacoes padrao
INSERT INTO configuracao_checklist (codigo, nome, descricao, ordem_execucao, criticidade, criterios) VALUES
('V01_MODULOS', 'Modulos Carregam', 'Verifica se todos os modulos core carregam sem erro', 1, 'bloqueante',
 '{"tipo": "import_check", "modulos": ["core.demand_calculator", "core.forecasting_models", "core.seasonality_detector", "core.validation"]}'),

('V02_METODOS_6', '6 Metodos Disponiveis', 'Verifica se os 6 metodos estatisticos estao disponiveis', 2, 'bloqueante',
 '{"tipo": "metodo_check", "classe": "DemandCalculator", "metodos": ["calcular_demanda_sma", "calcular_demanda_wma", "calcular_demanda_ema", "calcular_demanda_tendencia", "calcular_demanda_sazonal", "calcular_demanda_tsb"]}'),

('V03_SMA_TESTE', 'SMA Calcula Corretamente', 'Testa SMA com serie conhecida', 3, 'bloqueante',
 '{"tipo": "valor_esperado", "metodo": "calcular_demanda_sma", "entrada": [10, 20, 30, 40, 50], "saida_esperada": {"demanda_min": 30, "demanda_max": 45}}'),

('V04_SAZONALIDADE', 'Indices Sazonais Validos', 'Verifica se indices sazonais estao em range aceitavel', 4, 'alerta',
 '{"tipo": "range_check", "parametro": "indice_sazonal", "min": 0.5, "max": 2.0}'),

('V05_SANEAMENTO', 'Saneamento Rupturas', 'Verifica logica de cobertura >= 50%', 5, 'alerta',
 '{"tipo": "logica_check", "condicao": "cobertura >= 0.50 implica saneamento_ativo"}'),

('V06_NORMALIZACAO', 'Normalizacao por Dias', 'Verifica divisao pelo total de dias', 6, 'bloqueante',
 '{"tipo": "valor_esperado", "formula": "total_vendido / dias_totais", "exemplo": {"total": 730, "dias": 730, "esperado": 1.0}}'),

('V07_CORTE_DATA', 'Corte de Data Funciona', 'Verifica exclusao de dados do periodo de previsao', 7, 'bloqueante',
 '{"tipo": "logica_check", "condicao": "dados_periodo_previsao excluidos do historico"}'),

('V08_PEDIDO_FORMULA', 'Formula Pedido Correta', 'Verifica Qtd = max(0, Demanda + ES - Estoque)', 8, 'bloqueante',
 '{"tipo": "formula_check", "formula": "max(0, demanda_periodo + estoque_seguranca - estoque_atual)"}'),

('V09_PADRAO_COMPRA', 'Padrao Compra Integrado', 'Verifica integracao com padrao de compra', 9, 'alerta',
 '{"tipo": "integracao_check", "tabela": "padrao_compra_item"}'),

('V10_ES_ABC', 'ES por Curva ABC', 'Verifica Z correto para A, B, C', 10, 'alerta',
 '{"tipo": "valor_esperado", "valores": {"A": 2.05, "B": 1.65, "C": 1.28}, "tolerancia": 0.01}')

ON CONFLICT (codigo) DO NOTHING;

COMMENT ON TABLE configuracao_checklist IS 'Configuracao das verificacoes do checklist de conformidade';

-- ============================================================================
-- VIEW: Resumo diario de conformidade
-- ============================================================================

CREATE OR REPLACE VIEW vw_resumo_conformidade_diario AS
SELECT
    DATE(data_execucao) as data,
    COUNT(*) as total_execucoes,
    COUNT(*) FILTER (WHERE status = 'aprovado') as aprovadas,
    COUNT(*) FILTER (WHERE status = 'reprovado') as reprovadas,
    COUNT(*) FILTER (WHERE status = 'alerta') as alertas,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'aprovado') / NULLIF(COUNT(*), 0), 2) as taxa_conformidade,
    AVG(tempo_execucao_ms) as tempo_medio_ms
FROM auditoria_conformidade
WHERE data_execucao >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(data_execucao)
ORDER BY data DESC;

COMMENT ON VIEW vw_resumo_conformidade_diario IS 'Resumo diario de conformidade dos ultimos 30 dias';

-- ============================================================================
-- VIEW: Metodos mais utilizados
-- ============================================================================

CREATE OR REPLACE VIEW vw_metodos_utilizados AS
SELECT
    metodo_usado,
    COUNT(*) as total_usos,
    COUNT(*) FILTER (WHERE validacao_ok = TRUE) as validacoes_ok,
    ROUND(100.0 * COUNT(*) FILTER (WHERE validacao_ok = TRUE) / NULLIF(COUNT(*), 0), 2) as taxa_sucesso,
    DATE(MIN(data_calculo)) as primeiro_uso,
    DATE(MAX(data_calculo)) as ultimo_uso
FROM auditoria_calculos
WHERE data_calculo >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY metodo_usado
ORDER BY total_usos DESC;

COMMENT ON VIEW vw_metodos_utilizados IS 'Estatisticas de uso dos metodos de calculo';

-- ============================================================================
-- FIM DA MIGRATION V10
-- ============================================================================
