-- ============================================================================
-- MIGRATION V13: Otimização da Estrutura do Banco de Dados
-- Data: 2026-02-10
-- Autor: Claude + Valter Lino
-- ============================================================================
--
-- ALTERAÇÕES:
-- 1. Remove tabela 'embalagem' (dados incompletos, não utilizada)
-- 2. Padroniza cod_empresa em cadastro_fornecedores para INTEGER
-- 3. Adiciona índices em demanda_validada para performance
-- 4. Adiciona índices em embalagem_arredondamento
--
-- ============================================================================

-- ============================================================================
-- 1. REMOVER TABELA EMBALAGEM
-- ============================================================================
-- Justificativa:
--   - Contém apenas 619 registros com dados pobres (tipo vazio, qtd sempre 1.00)
--   - embalagem_arredondamento tem 2.630 registros com dados completos
--   - Não é utilizada no sistema principal
-- ============================================================================

-- Backup antes de remover (opcional - descomentar se necessário)
-- CREATE TABLE embalagem_backup_20260210 AS SELECT * FROM embalagem;

DROP TABLE IF EXISTS embalagem;

-- ============================================================================
-- 2. PADRONIZAR TIPO DE cod_empresa EM cadastro_fornecedores
-- ============================================================================
-- Problema: cod_empresa está como VARCHAR mas deveria ser INTEGER
-- Impacto: JOINs com outras tabelas podem ter problemas de tipo
-- ============================================================================

-- Criar coluna temporária
ALTER TABLE cadastro_fornecedores ADD COLUMN cod_empresa_int INTEGER;

-- Converter dados (tratando valores nulos e inválidos)
UPDATE cadastro_fornecedores
SET cod_empresa_int = CASE
    WHEN cod_empresa IS NULL THEN NULL
    WHEN cod_empresa ~ '^\d+$' THEN cod_empresa::INTEGER
    ELSE NULL
END;

-- Remover coluna antiga e renomear nova
ALTER TABLE cadastro_fornecedores DROP COLUMN cod_empresa;
ALTER TABLE cadastro_fornecedores RENAME COLUMN cod_empresa_int TO cod_empresa;

-- Recriar índice único (se existia constraint)
-- A constraint original era: cadastro_fornecedores_cnpj_cod_empresa_key
ALTER TABLE cadastro_fornecedores
    DROP CONSTRAINT IF EXISTS cadastro_fornecedores_cnpj_cod_empresa_key;

ALTER TABLE cadastro_fornecedores
    ADD CONSTRAINT cadastro_fornecedores_cnpj_cod_empresa_key
    UNIQUE (cnpj, cod_empresa);

-- ============================================================================
-- 3. ADICIONAR ÍNDICES EM demanda_validada
-- ============================================================================
-- Tabela não tinha índices além da PK
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_demanda_validada_produto
    ON demanda_validada(cod_produto);

CREATE INDEX IF NOT EXISTS idx_demanda_validada_loja
    ON demanda_validada(cod_loja);

CREATE INDEX IF NOT EXISTS idx_demanda_validada_periodo
    ON demanda_validada(data_inicio, data_fim);

CREATE INDEX IF NOT EXISTS idx_demanda_validada_fornecedor
    ON demanda_validada(cod_fornecedor);

CREATE INDEX IF NOT EXISTS idx_demanda_validada_status
    ON demanda_validada(status) WHERE status = 'validado';

-- ============================================================================
-- 4. ADICIONAR ÍNDICE COMPOSTO EM embalagem_arredondamento
-- ============================================================================
-- Para buscas por código + unidade
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_embalagem_arr_codigo_unidade
    ON embalagem_arredondamento(codigo, unidade_compra);

-- ============================================================================
-- 5. ANÁLISE DE ESTATÍSTICAS
-- ============================================================================
-- Atualizar estatísticas das tabelas modificadas para otimizar queries
-- ============================================================================

ANALYZE cadastro_fornecedores;
ANALYZE demanda_validada;
ANALYZE embalagem_arredondamento;

-- ============================================================================
-- VERIFICAÇÃO PÓS-MIGRATION
-- ============================================================================
-- Executar estas queries para verificar o sucesso da migration:
--
-- 1. Verificar se embalagem foi removida:
--    SELECT COUNT(*) FROM information_schema.tables
--    WHERE table_name = 'embalagem' AND table_schema = 'public';
--    (deve retornar 0)
--
-- 2. Verificar tipo de cod_empresa:
--    SELECT column_name, data_type FROM information_schema.columns
--    WHERE table_name = 'cadastro_fornecedores' AND column_name = 'cod_empresa';
--    (deve retornar 'integer')
--
-- 3. Verificar índices criados:
--    SELECT indexname FROM pg_indexes
--    WHERE tablename = 'demanda_validada';
--    (deve mostrar os novos índices)
--
-- ============================================================================
