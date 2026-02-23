-- Migration V13: Corrigir duplicacao na demanda_pre_calculada
-- Data: 2026-02-23
-- Problema: UNIQUE constraint com NULL nao funciona no PostgreSQL (NULL != NULL)
--           Cada execucao do cronjob criava novos registros em vez de atualizar
--           219.132 registros -> 40.200 (5.45x duplicacao)

-- Passo 1: Limpar duplicados mantendo o mais recente
DELETE FROM demanda_pre_calculada a
USING (
    SELECT cod_produto, cnpj_fornecedor, COALESCE(cod_empresa, 0) as emp, ano, mes, MAX(id) as max_id
    FROM demanda_pre_calculada
    GROUP BY cod_produto, cnpj_fornecedor, COALESCE(cod_empresa, 0), ano, mes
    HAVING COUNT(*) > 1
) b
WHERE a.cod_produto = b.cod_produto
  AND a.cnpj_fornecedor = b.cnpj_fornecedor
  AND COALESCE(a.cod_empresa, 0) = b.emp
  AND a.ano = b.ano
  AND a.mes = b.mes
  AND a.id < b.max_id;

-- Passo 2: Remover constraint antiga (nao funciona com NULL)
ALTER TABLE demanda_pre_calculada DROP CONSTRAINT IF EXISTS uk_demanda_pre_calc;

-- Passo 3: Criar indice UNIQUE funcional com COALESCE
-- COALESCE(cod_empresa, 0) trata NULL como 0, permitindo unicidade correta
CREATE UNIQUE INDEX IF NOT EXISTS uk_demanda_pre_calc
ON demanda_pre_calculada (cod_produto, cnpj_fornecedor, COALESCE(cod_empresa, 0), ano, mes);
