# -*- coding: utf-8 -*-
"""
Script para criar tabelas de grupos de transferencia e oportunidades
====================================================================
Cria estrutura para suportar transferencias regionais entre lojas.

IMPORTANTE: Este script NAO modifica tabelas existentes, apenas cria novas.

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import sys
import psycopg2
from datetime import datetime

# Configuracao de encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01'
}


def conectar_banco():
    """Conecta ao banco PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        print(f"ERRO ao conectar ao banco: {e}")
        sys.exit(1)


def criar_tabela_grupos_transferencia(conn):
    """Cria tabela de grupos regionais de transferencia"""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS grupos_transferencia (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(50) NOT NULL UNIQUE,
            descricao VARCHAR(100),
            cd_principal INTEGER NOT NULL,
            ativo BOOLEAN DEFAULT TRUE,
            data_criacao TIMESTAMP DEFAULT NOW()
        )
    """)

    # Criar indice
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_grupos_transf_cd
        ON grupos_transferencia(cd_principal)
    """)

    conn.commit()
    cur.close()
    print("Tabela grupos_transferencia criada/verificada.")


def criar_tabela_lojas_grupo(conn):
    """Cria tabela de lojas por grupo de transferencia"""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lojas_grupo_transferencia (
            id SERIAL PRIMARY KEY,
            grupo_id INTEGER REFERENCES grupos_transferencia(id) ON DELETE CASCADE,
            cod_empresa INTEGER NOT NULL,
            nome_loja VARCHAR(100),
            pode_doar BOOLEAN DEFAULT TRUE,
            pode_receber BOOLEAN DEFAULT TRUE,
            prioridade_recebimento INTEGER DEFAULT 5,
            ativo BOOLEAN DEFAULT TRUE,
            UNIQUE(grupo_id, cod_empresa)
        )
    """)

    # Criar indices
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_lojas_grupo_empresa
        ON lojas_grupo_transferencia(cod_empresa)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_lojas_grupo_grupo
        ON lojas_grupo_transferencia(grupo_id)
    """)

    conn.commit()
    cur.close()
    print("Tabela lojas_grupo_transferencia criada/verificada.")


def criar_tabela_oportunidades(conn):
    """Cria tabela de oportunidades de transferencia"""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS oportunidades_transferencia (
            id SERIAL PRIMARY KEY,
            data_calculo TIMESTAMP DEFAULT NOW(),
            sessao_pedido VARCHAR(50),
            grupo_id INTEGER REFERENCES grupos_transferencia(id),

            -- Produto
            cod_produto INTEGER NOT NULL,
            descricao_produto VARCHAR(300),
            curva_abc VARCHAR(1),

            -- Loja origem (excesso)
            loja_origem INTEGER NOT NULL,
            nome_loja_origem VARCHAR(100),
            estoque_origem INTEGER,
            transito_origem INTEGER DEFAULT 0,
            demanda_diaria_origem DECIMAL(10,2),
            cobertura_origem_dias DECIMAL(8,1),
            excesso_unidades INTEGER,

            -- Loja destino (falta)
            loja_destino INTEGER NOT NULL,
            nome_loja_destino VARCHAR(100),
            estoque_destino INTEGER,
            transito_destino INTEGER DEFAULT 0,
            demanda_diaria_destino DECIMAL(10,2),
            cobertura_destino_dias DECIMAL(8,1),
            necessidade_unidades INTEGER,

            -- Transferencia sugerida
            qtd_sugerida INTEGER NOT NULL,
            valor_estimado DECIMAL(12,2),
            cue DECIMAL(12,4),
            urgencia VARCHAR(10),

            -- Status
            status VARCHAR(20) DEFAULT 'SUGERIDA',

            UNIQUE(sessao_pedido, cod_produto, loja_origem, loja_destino)
        )
    """)

    # Criar indices
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_oport_transf_data
        ON oportunidades_transferencia(data_calculo)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_oport_transf_sessao
        ON oportunidades_transferencia(sessao_pedido)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_oport_transf_grupo
        ON oportunidades_transferencia(grupo_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_oport_transf_urgencia
        ON oportunidades_transferencia(urgencia)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_oport_transf_produto
        ON oportunidades_transferencia(cod_produto)
    """)

    conn.commit()
    cur.close()
    print("Tabela oportunidades_transferencia criada/verificada.")


def inserir_grupos_iniciais(conn):
    """Insere os grupos regionais de transferencia"""
    cur = conn.cursor()

    # Verificar se ja existem grupos
    cur.execute("SELECT COUNT(*) FROM grupos_transferencia")
    count = cur.fetchone()[0]

    if count > 0:
        print(f"Grupos ja existem ({count} registros). Pulando insercao inicial.")
        cur.close()
        return

    # Inserir grupos
    grupos = [
        ('NORDESTE_PE_PB_RN', 'Grupo CD Cabo - PE/PB/RN', 80),
        ('BA_SE', 'Grupo CD Lauro de Freitas - BA/SE', 81)
    ]

    for nome, descricao, cd in grupos:
        cur.execute("""
            INSERT INTO grupos_transferencia (nome, descricao, cd_principal)
            VALUES (%s, %s, %s)
            ON CONFLICT (nome) DO NOTHING
        """, (nome, descricao, cd))

    conn.commit()
    cur.close()
    print(f"Grupos regionais inseridos: {len(grupos)}")


def inserir_lojas_grupos(conn):
    """Insere lojas nos grupos de transferencia baseado no cadastro existente"""
    cur = conn.cursor()

    # Verificar se ja existem lojas nos grupos
    cur.execute("SELECT COUNT(*) FROM lojas_grupo_transferencia")
    count = cur.fetchone()[0]

    if count > 0:
        print(f"Lojas ja cadastradas nos grupos ({count} registros). Pulando insercao.")
        cur.close()
        return

    # Buscar lojas do cadastro
    cur.execute("""
        SELECT cod_empresa, nome_loja, regiao
        FROM cadastro_lojas
        WHERE ativo = TRUE AND cod_empresa < 80
        ORDER BY cod_empresa
    """)
    lojas = cur.fetchall()

    if not lojas:
        print("Nenhuma loja encontrada no cadastro. Inserindo manualmente...")
        # Inserir lojas manualmente baseado nos nomes mencionados
        lojas_grupo_cabo = [
            # (cod_empresa estimado, nome, grupo_id=1)
            # Sera necessario ajustar os codigos conforme cadastro real
        ]
        cur.close()
        return

    # Buscar IDs dos grupos
    cur.execute("SELECT id, nome, cd_principal FROM grupos_transferencia")
    grupos = {row[2]: row[0] for row in cur.fetchall()}  # {cd_principal: id}

    # Mapeamento de lojas por nome (ajustar conforme cadastro real)
    # Grupo CD Cabo (80): Imbiribeira, Tamarineira, Garanhuns, Joao Pessoa, Ponta Negra, Caruaru
    # Grupo CD Lauro de Freitas (81): Barris, Aracaju, Paralela

    lojas_nordeste = ['IMBIRIBEIRA', 'TAMARINEIRA', 'GARANHUNS', 'JOAO PESSOA', 'PONTA NEGRA', 'CARUARU']
    lojas_ba_se = ['BARRIS', 'ARACAJU', 'PARALELA']

    inseridos = 0
    for cod_empresa, nome_loja, regiao in lojas:
        nome_upper = nome_loja.upper() if nome_loja else ''

        # Determinar grupo
        grupo_id = None
        if any(l in nome_upper for l in lojas_nordeste):
            grupo_id = grupos.get(80)
        elif any(l in nome_upper for l in lojas_ba_se):
            grupo_id = grupos.get(81)

        if grupo_id:
            cur.execute("""
                INSERT INTO lojas_grupo_transferencia
                (grupo_id, cod_empresa, nome_loja, pode_doar, pode_receber, prioridade_recebimento)
                VALUES (%s, %s, %s, TRUE, TRUE, 5)
                ON CONFLICT (grupo_id, cod_empresa) DO NOTHING
            """, (grupo_id, cod_empresa, nome_loja))
            inseridos += 1

    conn.commit()
    cur.close()
    print(f"Lojas inseridas nos grupos: {inseridos}")


def verificar_estrutura(conn):
    """Verifica a estrutura criada"""
    cur = conn.cursor()

    print("\n" + "=" * 60)
    print("VERIFICACAO DA ESTRUTURA")
    print("=" * 60)

    # Grupos
    cur.execute("""
        SELECT id, nome, descricao, cd_principal
        FROM grupos_transferencia
        WHERE ativo = TRUE
    """)
    grupos = cur.fetchall()
    print(f"\nGrupos de transferencia: {len(grupos)}")
    for g in grupos:
        print(f"  [{g[0]}] {g[1]} - CD {g[3]}: {g[2]}")

    # Lojas por grupo
    cur.execute("""
        SELECT
            gt.nome as grupo,
            COUNT(lgt.id) as total_lojas,
            STRING_AGG(lgt.nome_loja, ', ' ORDER BY lgt.cod_empresa) as lojas
        FROM grupos_transferencia gt
        LEFT JOIN lojas_grupo_transferencia lgt ON gt.id = lgt.grupo_id AND lgt.ativo = TRUE
        WHERE gt.ativo = TRUE
        GROUP BY gt.id, gt.nome
    """)
    lojas_grupo = cur.fetchall()
    print(f"\nLojas por grupo:")
    for lg in lojas_grupo:
        print(f"  {lg[0]}: {lg[1]} lojas")
        if lg[2]:
            print(f"    -> {lg[2]}")

    # Oportunidades (deve estar vazia inicialmente)
    cur.execute("SELECT COUNT(*) FROM oportunidades_transferencia")
    count = cur.fetchone()[0]
    print(f"\nOportunidades de transferencia: {count}")

    cur.close()


def main():
    """Funcao principal"""
    print("=" * 60)
    print("CRIACAO DE TABELAS - TRANSFERENCIAS REGIONAIS")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Conectar
    print("Conectando ao banco de dados...")
    conn = conectar_banco()
    print("Conectado com sucesso!")

    # Criar tabelas
    print("\n--- Criando tabelas ---")
    criar_tabela_grupos_transferencia(conn)
    criar_tabela_lojas_grupo(conn)
    criar_tabela_oportunidades(conn)

    # Inserir dados iniciais
    print("\n--- Inserindo dados iniciais ---")
    inserir_grupos_iniciais(conn)
    inserir_lojas_grupos(conn)

    # Verificar
    verificar_estrutura(conn)

    # Fechar
    conn.close()

    print("\n" + "=" * 60)
    print("CRIACAO CONCLUIDA!")
    print("=" * 60)


if __name__ == '__main__':
    main()
