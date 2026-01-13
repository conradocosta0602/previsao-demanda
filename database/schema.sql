-- ============================================================================
-- SCHEMA DO BANCO DE DADOS - SISTEMA DE PREVISÃO E REABASTECIMENTO
-- ============================================================================
-- Database: demanda_reabastecimento
-- PostgreSQL 12+
-- Criado: Janeiro 2026
-- ============================================================================

-- ============================================================================
-- CAMADA 1: CADASTROS (Dados Mestres)
-- ============================================================================

-- Tabela: Cadastro de Lojas/Filiais
CREATE TABLE IF NOT EXISTS cadastro_lojas (
    cod_empresa INTEGER PRIMARY KEY,
    nome_loja VARCHAR(100) NOT NULL,
    regiao VARCHAR(50),
    tipo VARCHAR(50), -- 'Loja', 'CD', 'Hub'
    ativo BOOLEAN DEFAULT TRUE,
    capacidade_estoque DECIMAL(12,2),

    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lojas_regiao ON cadastro_lojas(regiao);
CREATE INDEX idx_lojas_tipo ON cadastro_lojas(tipo);

COMMENT ON TABLE cadastro_lojas IS 'Cadastro de lojas, filiais e centros de distribuição';

-- ============================================================================

-- Tabela: Cadastro de Fornecedores
CREATE TABLE IF NOT EXISTS cadastro_fornecedores (
    id_fornecedor SERIAL PRIMARY KEY,
    codigo_fornecedor VARCHAR(20) UNIQUE NOT NULL,
    nome_fornecedor VARCHAR(200) NOT NULL,
    cnpj VARCHAR(18),
    categoria VARCHAR(100),

    -- Parâmetros operacionais
    lead_time_dias INTEGER DEFAULT 30,
    pedido_minimo DECIMAL(12,2),
    multiplo_palete INTEGER,

    -- Status
    ativo BOOLEAN DEFAULT TRUE,

    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_fornecedor_codigo ON cadastro_fornecedores(codigo_fornecedor);
CREATE INDEX idx_fornecedor_categoria ON cadastro_fornecedores(categoria);

COMMENT ON TABLE cadastro_fornecedores IS 'Cadastro de fornecedores com parâmetros operacionais';

-- ============================================================================

-- Tabela: Cadastro de Produtos
CREATE TABLE IF NOT EXISTS cadastro_produtos (
    codigo INTEGER PRIMARY KEY,
    descricao VARCHAR(200) NOT NULL,
    categoria VARCHAR(100),
    subcategoria VARCHAR(100),

    -- Fornecedor principal
    id_fornecedor INTEGER REFERENCES cadastro_fornecedores(id_fornecedor),

    -- Unidades
    und_venda VARCHAR(10), -- 'UN', 'KG', 'LT', etc
    fator_conversao DECIMAL(10,4) DEFAULT 1,

    -- Parâmetros físicos
    peso_kg DECIMAL(10,3),
    volume_m3 DECIMAL(10,6),
    pereciveis BOOLEAN DEFAULT FALSE,
    shelf_life_dias INTEGER,

    -- Parâmetros comerciais
    curva_abc VARCHAR(1), -- 'A', 'B', 'C'
    margem_contribuicao DECIMAL(5,2),

    -- Status
    ativo BOOLEAN DEFAULT TRUE,

    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_produto_categoria ON cadastro_produtos(categoria);
CREATE INDEX idx_produto_fornecedor ON cadastro_produtos(id_fornecedor);
CREATE INDEX idx_produto_curva ON cadastro_produtos(curva_abc);

COMMENT ON TABLE cadastro_produtos IS 'Cadastro de produtos com parâmetros físicos e comerciais';

-- ============================================================================

-- Tabela: Parâmetros de Loja x Produto (gôndola)
CREATE TABLE IF NOT EXISTS parametros_gondola (
    id SERIAL PRIMARY KEY,
    cod_empresa INTEGER REFERENCES cadastro_lojas(cod_empresa),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Parâmetros de exposição
    capacidade_gondola INTEGER, -- Unidades que cabem na gôndola
    estoque_seguranca INTEGER, -- Dias ou unidades de segurança

    -- Parâmetros de pedido
    lote_minimo INTEGER DEFAULT 1,
    multiplo INTEGER DEFAULT 1,

    -- Status
    ativo BOOLEAN DEFAULT TRUE,

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(cod_empresa, codigo)
);

CREATE INDEX idx_gondola_loja ON parametros_gondola(cod_empresa);
CREATE INDEX idx_gondola_produto ON parametros_gondola(codigo);

COMMENT ON TABLE parametros_gondola IS 'Parâmetros específicos de produto por loja (capacidade, lote mínimo, etc)';

-- ============================================================================
-- CAMADA 2: SITUAÇÃO ATUAL (Snapshots)
-- ============================================================================

-- Tabela: Estoque Atual
CREATE TABLE IF NOT EXISTS estoque_atual (
    id SERIAL PRIMARY KEY,
    cod_empresa INTEGER REFERENCES cadastro_lojas(cod_empresa),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Quantidades
    qtd_estoque DECIMAL(12,2) NOT NULL,
    qtd_reservada DECIMAL(12,2) DEFAULT 0,
    qtd_disponivel DECIMAL(12,2) GENERATED ALWAYS AS (qtd_estoque - qtd_reservada) STORED,

    -- Localização
    localizacao VARCHAR(50), -- Ex: 'Gôndola', 'Depósito', 'CD'

    -- Controle
    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(cod_empresa, codigo, localizacao)
);

CREATE INDEX idx_estoque_loja ON estoque_atual(cod_empresa);
CREATE INDEX idx_estoque_produto ON estoque_atual(codigo);
CREATE INDEX idx_estoque_data ON estoque_atual(data_atualizacao);

COMMENT ON TABLE estoque_atual IS 'Posição atual de estoque (snapshot diário)';

-- ============================================================================

-- Tabela: Pedidos em Aberto
CREATE TABLE IF NOT EXISTS pedidos_abertos (
    id_pedido SERIAL PRIMARY KEY,
    numero_pedido VARCHAR(50) UNIQUE NOT NULL,
    tipo_pedido VARCHAR(20) NOT NULL, -- 'Fornecedor', 'CD', 'Transferencia'

    -- Origem/Destino
    cod_empresa_destino INTEGER REFERENCES cadastro_lojas(cod_empresa),
    cod_empresa_origem INTEGER REFERENCES cadastro_lojas(cod_empresa), -- Para transferências
    id_fornecedor INTEGER REFERENCES cadastro_fornecedores(id_fornecedor), -- Para compras

    -- Datas
    data_pedido DATE NOT NULL,
    data_entrega_prevista DATE NOT NULL,

    -- Status
    status VARCHAR(30) NOT NULL, -- 'Aberto', 'EmTransito', 'Recebido', 'Cancelado'

    -- Valores
    valor_total DECIMAL(12,2),

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pedidos_destino ON pedidos_abertos(cod_empresa_destino);
CREATE INDEX idx_pedidos_status ON pedidos_abertos(status);
CREATE INDEX idx_pedidos_entrega ON pedidos_abertos(data_entrega_prevista);

COMMENT ON TABLE pedidos_abertos IS 'Pedidos em aberto (não recebidos)';

-- ============================================================================

-- Tabela: Itens dos Pedidos em Aberto
CREATE TABLE IF NOT EXISTS pedidos_itens (
    id SERIAL PRIMARY KEY,
    id_pedido INTEGER REFERENCES pedidos_abertos(id_pedido) ON DELETE CASCADE,
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Quantidades
    qtd_pedida DECIMAL(12,2) NOT NULL,
    qtd_recebida DECIMAL(12,2) DEFAULT 0,
    qtd_pendente DECIMAL(12,2) GENERATED ALWAYS AS (qtd_pedida - qtd_recebida) STORED,

    -- Valores
    preco_unitario DECIMAL(10,2),
    valor_item DECIMAL(12,2) GENERATED ALWAYS AS (qtd_pedida * preco_unitario) STORED,

    UNIQUE(id_pedido, codigo)
);

CREATE INDEX idx_pedidos_itens_pedido ON pedidos_itens(id_pedido);
CREATE INDEX idx_pedidos_itens_produto ON pedidos_itens(codigo);

COMMENT ON TABLE pedidos_itens IS 'Itens dos pedidos em aberto';

-- ============================================================================

-- Tabela: Trânsito Atual
CREATE TABLE IF NOT EXISTS transito_atual (
    id SERIAL PRIMARY KEY,
    id_pedido INTEGER REFERENCES pedidos_abertos(id_pedido),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Quantidades
    qtd_transito DECIMAL(12,2) NOT NULL,

    -- Origem/Destino
    origem VARCHAR(100),
    destino VARCHAR(100),

    -- Previsão
    data_saida DATE,
    data_chegada_prevista DATE NOT NULL,

    -- Status
    status VARCHAR(30), -- 'EmTransito', 'Aguardando', 'AtrasoDespachante'

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transito_pedido ON transito_atual(id_pedido);
CREATE INDEX idx_transito_produto ON transito_atual(codigo);
CREATE INDEX idx_transito_chegada ON transito_atual(data_chegada_prevista);

COMMENT ON TABLE transito_atual IS 'Mercadorias em trânsito';

-- ============================================================================

-- Tabela: Preços Vigentes
CREATE TABLE IF NOT EXISTS precos_vigentes (
    id SERIAL PRIMARY KEY,
    cod_empresa INTEGER REFERENCES cadastro_lojas(cod_empresa),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Preços
    preco_venda DECIMAL(10,2) NOT NULL,
    preco_custo DECIMAL(10,2),
    preco_promocional DECIMAL(10,2),

    -- Vigência
    data_inicio DATE NOT NULL,
    data_fim DATE,

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(cod_empresa, codigo, data_inicio)
);

CREATE INDEX idx_precos_loja ON precos_vigentes(cod_empresa);
CREATE INDEX idx_precos_produto ON precos_vigentes(codigo);
CREATE INDEX idx_precos_vigencia ON precos_vigentes(data_inicio, data_fim);

COMMENT ON TABLE precos_vigentes IS 'Preços vigentes (venda, custo, promocional)';

-- ============================================================================
-- CAMADA 3: HISTÓRICO (Séries Temporais)
-- ============================================================================

-- Tabela: Histórico de Vendas Diário
-- PARTICIONADA por ANO para performance
CREATE TABLE IF NOT EXISTS historico_vendas_diario (
    id BIGSERIAL,
    data DATE NOT NULL,
    cod_empresa INTEGER REFERENCES cadastro_lojas(cod_empresa),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Vendas
    qtd_venda DECIMAL(12,2) NOT NULL,
    valor_venda DECIMAL(12,2),

    -- Contexto
    dia_semana INTEGER, -- 1=Segunda, 7=Domingo
    dia_mes INTEGER,
    semana_ano INTEGER,
    mes INTEGER,
    ano INTEGER,

    -- Flags
    feriado BOOLEAN DEFAULT FALSE,
    fim_semana BOOLEAN DEFAULT FALSE,
    promocao BOOLEAN DEFAULT FALSE,

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (data, cod_empresa, codigo, id)
) PARTITION BY RANGE (data);

-- Criar partições por ano (exemplo para 2023-2026)
CREATE TABLE historico_vendas_diario_2023 PARTITION OF historico_vendas_diario
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE historico_vendas_diario_2024 PARTITION OF historico_vendas_diario
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE historico_vendas_diario_2025 PARTITION OF historico_vendas_diario
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE historico_vendas_diario_2026 PARTITION OF historico_vendas_diario
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

-- Indexes nas partições principais
CREATE INDEX idx_vendas_data ON historico_vendas_diario(data);
CREATE INDEX idx_vendas_loja ON historico_vendas_diario(cod_empresa);
CREATE INDEX idx_vendas_produto ON historico_vendas_diario(codigo);
CREATE INDEX idx_vendas_combo ON historico_vendas_diario(cod_empresa, codigo, data);

COMMENT ON TABLE historico_vendas_diario IS 'Histórico diário de vendas (particionado por ano)';

-- ============================================================================

-- Tabela: Histórico de Estoque Diário
CREATE TABLE IF NOT EXISTS historico_estoque_diario (
    id BIGSERIAL,
    data DATE NOT NULL,
    cod_empresa INTEGER REFERENCES cadastro_lojas(cod_empresa),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Estoque
    estoque_diario DECIMAL(12,2) NOT NULL,
    estoque_inicial DECIMAL(12,2),
    estoque_final DECIMAL(12,2),

    -- Movimentações
    entrada DECIMAL(12,2) DEFAULT 0,
    saida DECIMAL(12,2) DEFAULT 0,

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (data, cod_empresa, codigo, id)
) PARTITION BY RANGE (data);

-- Partições por ano
CREATE TABLE historico_estoque_diario_2023 PARTITION OF historico_estoque_diario
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE historico_estoque_diario_2024 PARTITION OF historico_estoque_diario
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE historico_estoque_diario_2025 PARTITION OF historico_estoque_diario
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE historico_estoque_diario_2026 PARTITION OF historico_estoque_diario
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

CREATE INDEX idx_estoque_hist_data ON historico_estoque_diario(data);
CREATE INDEX idx_estoque_hist_loja ON historico_estoque_diario(cod_empresa);
CREATE INDEX idx_estoque_hist_produto ON historico_estoque_diario(codigo);

COMMENT ON TABLE historico_estoque_diario IS 'Histórico diário de posições de estoque';

-- ============================================================================

-- Tabela: Histórico de Preços
CREATE TABLE IF NOT EXISTS historico_precos (
    id BIGSERIAL PRIMARY KEY,
    data DATE NOT NULL,
    cod_empresa INTEGER REFERENCES cadastro_lojas(cod_empresa),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Preços
    preco_venda DECIMAL(10,2) NOT NULL,
    preco_custo DECIMAL(10,2),
    preco_promocional DECIMAL(10,2),

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_precos_hist_data ON historico_precos(data);
CREATE INDEX idx_precos_hist_combo ON historico_precos(cod_empresa, codigo, data);

COMMENT ON TABLE historico_precos IS 'Histórico de variação de preços';

-- ============================================================================

-- Tabela: Eventos Promocionais (Calendário)
CREATE TABLE IF NOT EXISTS eventos_promocionais (
    id_evento SERIAL PRIMARY KEY,
    nome_evento VARCHAR(100) NOT NULL,
    tipo_evento VARCHAR(50), -- 'BlackFriday', 'Natal', 'DiaDosNamorados', etc

    -- Período
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,

    -- Impacto
    impacto_estimado DECIMAL(5,2), -- % de aumento esperado

    -- Abrangência
    nacional BOOLEAN DEFAULT TRUE,
    regioes TEXT[], -- Array de regiões afetadas

    -- Status
    ativo BOOLEAN DEFAULT TRUE,

    -- Observações
    descricao TEXT,

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_eventos_periodo ON eventos_promocionais(data_inicio, data_fim);
CREATE INDEX idx_eventos_tipo ON eventos_promocionais(tipo_evento);

COMMENT ON TABLE eventos_promocionais IS 'Calendário de eventos promocionais e sazonais';

-- ============================================================================
-- CAMADA 4: KPIs E RESULTADOS (Cache/Materializado)
-- ============================================================================

-- Tabela: KPIs Histórico
CREATE TABLE IF NOT EXISTS kpis_historico (
    id SERIAL PRIMARY KEY,
    data_ref DATE NOT NULL,
    tipo_periodo VARCHAR(10) NOT NULL, -- 'diario', 'semanal', 'mensal'

    -- Filtros (NULL = agregado geral)
    cod_empresa INTEGER REFERENCES cadastro_lojas(cod_empresa),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),
    categoria VARCHAR(100),

    -- KPIs de Demanda (Acurácia)
    wmape DECIMAL(10,2),
    bias DECIMAL(10,2),
    mae DECIMAL(10,2),
    n_skus INTEGER, -- Quantidade de SKUs no cálculo
    n_previsoes_excelentes INTEGER, -- WMAPE < 10%

    -- KPIs de Reabastecimento
    taxa_ruptura DECIMAL(10,2), -- %
    cobertura_media DECIMAL(10,2), -- dias
    nivel_servico DECIMAL(10,2), -- %
    giro_estoque DECIMAL(10,2),

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar índice único composto (sem COALESCE na constraint)
CREATE UNIQUE INDEX idx_kpis_unique ON kpis_historico(
    data_ref,
    tipo_periodo,
    COALESCE(cod_empresa, 0),
    COALESCE(codigo, 0)
);

CREATE INDEX idx_kpis_data ON kpis_historico(data_ref);
CREATE INDEX idx_kpis_periodo ON kpis_historico(tipo_periodo);
CREATE INDEX idx_kpis_loja ON kpis_historico(cod_empresa);
CREATE INDEX idx_kpis_produto ON kpis_historico(codigo);

COMMENT ON TABLE kpis_historico IS 'KPIs calculados e armazenados para consulta rápida';

-- ============================================================================

-- Tabela: Previsões Geradas
CREATE TABLE IF NOT EXISTS previsoes_geradas (
    id BIGSERIAL PRIMARY KEY,
    data_geracao TIMESTAMP NOT NULL,

    -- SKU
    cod_empresa INTEGER REFERENCES cadastro_lojas(cod_empresa),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Previsão
    data_referencia DATE NOT NULL, -- Data para qual a previsão foi feita
    periodo_previsao DATE NOT NULL, -- Período previsto
    granularidade VARCHAR(10) NOT NULL, -- 'diario', 'semanal', 'mensal'

    -- Valores
    qtd_prevista DECIMAL(12,2) NOT NULL,
    metodo_usado VARCHAR(50), -- 'SMA', 'WMA', 'AUTO', 'HOLTWINTERS', etc
    confianca DECIMAL(5,2), -- % de confiança

    -- Métricas
    wmape DECIMAL(10,2),
    bias DECIMAL(10,2),

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_previsoes_geracao ON previsoes_geradas(data_geracao);
CREATE INDEX idx_previsoes_periodo ON previsoes_geradas(periodo_previsao);
CREATE INDEX idx_previsoes_combo ON previsoes_geradas(cod_empresa, codigo, periodo_previsao);

COMMENT ON TABLE previsoes_geradas IS 'Registro de todas as previsões geradas pelo sistema';

-- ============================================================================

-- Tabela: Pedidos Calculados (Sugestões)
CREATE TABLE IF NOT EXISTS pedidos_calculados (
    id BIGSERIAL PRIMARY KEY,
    data_calculo TIMESTAMP NOT NULL,

    -- Tipo
    tipo_pedido VARCHAR(20) NOT NULL, -- 'Fornecedor', 'CD', 'Transferencia'
    status VARCHAR(30) DEFAULT 'Calculado', -- 'Calculado', 'Aprovado', 'Processado'

    -- Origem/Destino
    cod_empresa_destino INTEGER REFERENCES cadastro_lojas(cod_empresa),
    cod_empresa_origem INTEGER REFERENCES cadastro_lojas(cod_empresa),
    id_fornecedor INTEGER REFERENCES cadastro_fornecedores(id_fornecedor),
    codigo INTEGER REFERENCES cadastro_produtos(codigo),

    -- Quantidade
    qtd_sugerida DECIMAL(12,2) NOT NULL,
    qtd_ajustada DECIMAL(12,2), -- Se usuário ajustou manualmente

    -- Justificativa
    motivo TEXT, -- Ex: 'Ruptura prevista', 'Estoque baixo', etc

    -- Controle
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP
);

CREATE INDEX idx_pedidos_calc_data ON pedidos_calculados(data_calculo);
CREATE INDEX idx_pedidos_calc_status ON pedidos_calculados(status);
CREATE INDEX idx_pedidos_calc_destino ON pedidos_calculados(cod_empresa_destino);

COMMENT ON TABLE pedidos_calculados IS 'Pedidos calculados pelo sistema (sugestões de reabastecimento)';

-- ============================================================================
-- VIEWS MATERIALIZADAS (Para Performance)
-- ============================================================================

-- View: Estoque + Trânsito por SKU
CREATE MATERIALIZED VIEW IF NOT EXISTS vw_estoque_total AS
SELECT
    e.cod_empresa,
    e.codigo,
    e.qtd_disponivel as estoque_disponivel,
    COALESCE(SUM(t.qtd_transito), 0) as qtd_transito,
    e.qtd_disponivel + COALESCE(SUM(t.qtd_transito), 0) as estoque_total,
    e.data_atualizacao
FROM estoque_atual e
LEFT JOIN transito_atual t ON e.cod_empresa = t.destino::INTEGER
                            AND e.codigo = t.codigo
GROUP BY e.cod_empresa, e.codigo, e.qtd_disponivel, e.data_atualizacao;

CREATE UNIQUE INDEX idx_vw_estoque_total ON vw_estoque_total(cod_empresa, codigo);

COMMENT ON MATERIALIZED VIEW vw_estoque_total IS 'Estoque disponível + trânsito = estoque total projetado';

-- ============================================================================

-- View: Vendas Mensais Agregadas (Cache)
CREATE MATERIALIZED VIEW IF NOT EXISTS vw_vendas_mensais AS
SELECT
    DATE_TRUNC('month', data) as mes,
    cod_empresa,
    codigo,
    SUM(qtd_venda) as qtd_total,
    AVG(qtd_venda) as qtd_media,
    COUNT(*) as dias_venda,
    SUM(valor_venda) as valor_total
FROM historico_vendas_diario
GROUP BY DATE_TRUNC('month', data), cod_empresa, codigo;

CREATE INDEX idx_vw_vendas_mes ON vw_vendas_mensais(mes);
CREATE INDEX idx_vw_vendas_combo ON vw_vendas_mensais(cod_empresa, codigo, mes);

COMMENT ON MATERIALIZED VIEW vw_vendas_mensais IS 'Agregação mensal de vendas para consultas rápidas';

-- ============================================================================
-- GRANTS E PERMISSÕES
-- ============================================================================

-- Criar usuário da aplicação (ajustar senha!)
-- CREATE USER app_demanda WITH PASSWORD 'sua_senha_aqui';

-- Permissões de leitura em todas tabelas
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_demanda;

-- Permissões de escrita em tabelas específicas
-- GRANT INSERT, UPDATE ON estoque_atual, pedidos_abertos, pedidos_itens TO app_demanda;
-- GRANT INSERT ON historico_vendas_diario, kpis_historico, previsoes_geradas TO app_demanda;

-- ============================================================================
-- FIM DO SCHEMA
-- ============================================================================
