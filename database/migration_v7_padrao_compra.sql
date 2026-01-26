-- ============================================================================
-- MIGRATION V7: Sistema de Padrão de Compra (Centralização de Pedidos)
-- ============================================================================
-- Criado: Janeiro 2026
-- Descricao: Adiciona tabelas para padrao de compra por item/loja
--            Permite centralizar pedidos de múltiplas lojas em uma loja destino
-- ============================================================================

-- ============================================================================
-- TABELA: padrao_compra_item
-- Armazena o padrão de compra (loja destino) por item e loja de venda
-- ============================================================================

CREATE TABLE IF NOT EXISTS padrao_compra_item (
    id SERIAL PRIMARY KEY,

    -- Identificação do item e loja de venda (origem)
    codigo INTEGER NOT NULL,                  -- Código do produto
    cod_empresa_venda INTEGER NOT NULL,       -- Loja onde o item é vendido (origem)

    -- Padrão de compra (loja destino)
    cod_empresa_destino INTEGER NOT NULL,     -- Loja que receberá o pedido (destino)

    -- Contexto da última atualização
    data_referencia DATE NOT NULL,            -- Data do arquivo de demanda que atualizou
    data_atualizacao TIMESTAMP DEFAULT NOW(), -- Quando foi atualizado no sistema

    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Chave única: apenas um padrão por item/loja de venda
    UNIQUE(codigo, cod_empresa_venda)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_padrao_compra_codigo ON padrao_compra_item(codigo);
CREATE INDEX IF NOT EXISTS idx_padrao_compra_venda ON padrao_compra_item(cod_empresa_venda);
CREATE INDEX IF NOT EXISTS idx_padrao_compra_destino ON padrao_compra_item(cod_empresa_destino);
CREATE INDEX IF NOT EXISTS idx_padrao_compra_data ON padrao_compra_item(data_referencia);

-- Índice composto para busca rápida
CREATE INDEX IF NOT EXISTS idx_padrao_compra_busca ON padrao_compra_item(codigo, cod_empresa_venda, cod_empresa_destino);

COMMENT ON TABLE padrao_compra_item IS 'Padrão de compra por item/loja - define para qual loja o pedido será direcionado';
COMMENT ON COLUMN padrao_compra_item.codigo IS 'Código do produto';
COMMENT ON COLUMN padrao_compra_item.cod_empresa_venda IS 'Loja onde o produto é vendido (origem da demanda)';
COMMENT ON COLUMN padrao_compra_item.cod_empresa_destino IS 'Loja que receberá o pedido (destino centralizado)';
COMMENT ON COLUMN padrao_compra_item.data_referencia IS 'Data do arquivo de demanda que definiu este padrão';

-- ============================================================================
-- TABELA: parametros_globais
-- Armazena parâmetros globais do sistema
-- ============================================================================

CREATE TABLE IF NOT EXISTS parametros_globais (
    id SERIAL PRIMARY KEY,
    chave VARCHAR(100) UNIQUE NOT NULL,       -- Identificador do parâmetro
    valor VARCHAR(255) NOT NULL,              -- Valor do parâmetro
    tipo VARCHAR(20) DEFAULT 'string',        -- Tipo: string, integer, decimal, boolean
    descricao TEXT,                           -- Descrição do parâmetro
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE parametros_globais IS 'Parâmetros globais do sistema';

-- Inserir parâmetro de dias de transferência (10 dias por padrão)
INSERT INTO parametros_globais (chave, valor, tipo, descricao)
VALUES ('dias_transferencia_padrao_compra', '10', 'integer', 'Dias adicionais ao lead time para itens com padrão de compra diferente da loja de venda (transferência entre filiais)')
ON CONFLICT (chave) DO UPDATE SET
    valor = EXCLUDED.valor,
    updated_at = NOW();

-- ============================================================================
-- VIEW: Visão completa do padrão de compra com detalhes das lojas
-- ============================================================================

CREATE OR REPLACE VIEW vw_padrao_compra_detalhado AS
SELECT
    pci.id,
    pci.codigo,
    cp.descricao as descricao_produto,
    pci.cod_empresa_venda,
    lv.nome_loja as loja_venda,
    pci.cod_empresa_destino,
    ld.nome_loja as loja_destino,
    CASE
        WHEN pci.cod_empresa_venda = pci.cod_empresa_destino THEN 'Direto'
        ELSE 'Centralizado'
    END as tipo_padrao,
    pci.data_referencia,
    pci.data_atualizacao
FROM padrao_compra_item pci
LEFT JOIN cadastro_produtos cp ON pci.codigo = cp.codigo
LEFT JOIN cadastro_lojas lv ON pci.cod_empresa_venda = lv.cod_empresa
LEFT JOIN cadastro_lojas ld ON pci.cod_empresa_destino = ld.cod_empresa;

COMMENT ON VIEW vw_padrao_compra_detalhado IS 'Visão detalhada do padrão de compra com nomes de produtos e lojas';

-- ============================================================================
-- VIEW: Itens sem padrão de compra definido
-- Usado para alertas/críticas
-- ============================================================================

CREATE OR REPLACE VIEW vw_itens_sem_padrao_compra AS
SELECT DISTINCT
    hvd.codigo,
    cp.descricao as descricao_produto,
    hvd.cod_empresa,
    cl.nome_loja,
    cf.nome_fornecedor,
    cf.cnpj as cnpj_fornecedor
FROM historico_vendas_diario hvd
LEFT JOIN cadastro_produtos cp ON hvd.codigo = cp.codigo
LEFT JOIN cadastro_lojas cl ON hvd.cod_empresa = cl.cod_empresa
LEFT JOIN cadastro_fornecedores cf ON cp.id_fornecedor = cf.id_fornecedor
WHERE NOT EXISTS (
    SELECT 1 FROM padrao_compra_item pci
    WHERE pci.codigo = hvd.codigo
      AND pci.cod_empresa_venda = hvd.cod_empresa
)
AND hvd.data >= CURRENT_DATE - INTERVAL '90 days';

COMMENT ON VIEW vw_itens_sem_padrao_compra IS 'Itens com vendas recentes mas sem padrão de compra definido';

-- ============================================================================
-- FUNÇÃO: Obter parâmetro global como inteiro
-- ============================================================================

CREATE OR REPLACE FUNCTION get_parametro_global_int(p_chave VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    v_valor VARCHAR;
BEGIN
    SELECT valor INTO v_valor
    FROM parametros_globais
    WHERE chave = p_chave AND ativo = TRUE;

    IF v_valor IS NULL THEN
        RETURN NULL;
    END IF;

    RETURN v_valor::INTEGER;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_parametro_global_int IS 'Retorna valor de parâmetro global como inteiro';

-- ============================================================================
-- FIM DA MIGRATION V7
-- ============================================================================

-- Para verificar se a migração foi aplicada:
-- SELECT table_name FROM information_schema.tables WHERE table_name IN
--   ('padrao_compra_item', 'parametros_globais');
