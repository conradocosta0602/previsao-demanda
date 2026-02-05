-- =====================================================
-- Migration V11: Indices para Performance
-- Resolve problema de timeout em queries de previsao
-- =====================================================

-- Indices na tabela historico_vendas_diario
-- (JOIN com cadastro_produtos usa h.codigo::text)

-- Indice para data (filtro de periodo)
CREATE INDEX IF NOT EXISTS idx_historico_vendas_data
ON historico_vendas_diario(data);

-- Indice para codigo (JOIN e filtros)
CREATE INDEX IF NOT EXISTS idx_historico_vendas_codigo
ON historico_vendas_diario(codigo);

-- Indice composto para queries frequentes
CREATE INDEX IF NOT EXISTS idx_historico_vendas_codigo_data
ON historico_vendas_diario(codigo, data);

-- Indices na tabela cadastro_produtos_completo

-- Indice para cod_produto (usado no JOIN)
CREATE INDEX IF NOT EXISTS idx_cadastro_produtos_cod
ON cadastro_produtos_completo(cod_produto);

-- Indice para cnpj_fornecedor (filtro por fornecedor)
CREATE INDEX IF NOT EXISTS idx_cadastro_produtos_cnpj
ON cadastro_produtos_completo(cnpj_fornecedor);

-- Indice para nome_fornecedor (filtro por nome)
CREATE INDEX IF NOT EXISTS idx_cadastro_produtos_nome_fornecedor
ON cadastro_produtos_completo(nome_fornecedor);

-- Indice para categoria (filtro por linha)
CREATE INDEX IF NOT EXISTS idx_cadastro_produtos_categoria
ON cadastro_produtos_completo(categoria);

-- Indices na tabela estoque_diario (se existir)

CREATE INDEX IF NOT EXISTS idx_estoque_diario_codigo
ON estoque_diario(codigo);

CREATE INDEX IF NOT EXISTS idx_estoque_diario_data
ON estoque_diario(data);

-- Analisar tabelas para atualizar estatisticas do planner
ANALYZE historico_vendas_diario;
ANALYZE cadastro_produtos_completo;
ANALYZE estoque_diario;

-- =====================================================
-- NOTA: Execute este script para melhorar performance
-- Tempo estimado de criacao: 1-5 minutos dependendo do volume
-- Melhoria esperada: 5-10x mais rapido
-- =====================================================
