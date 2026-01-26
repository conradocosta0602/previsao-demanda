# -*- coding: utf-8 -*-
"""
Script de Importacao de Parametros de Fornecedor
=================================================
Importa Lead Time, Ciclo de Pedido e Faturamento Minimo por fornecedor/loja.

Colunas esperadas no arquivo Excel:
- CNPJ: CNPJ do fornecedor
- FANTAS: Nome fantasia do fornecedor
- COD_EMPRESA: Codigo da loja/empresa
- TIPO_DESTINO: LOJA ou CD
- LEAD_TIME_DIAS: Tempo de entrega em dias
- CICLO_PEDIDO_DIAS: Ciclo de pedido em dias
- FAT_MINIMO: Faturamento minimo do pedido

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configuracao de encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIGURACOES
# ============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01'
}

# Caminho padrao do arquivo
ARQUIVO_FORNECEDOR = Path(__file__).parent.parent / 'dados_reais' / 'Cadastro de Fornecedores.xlsx'


# ============================================================================
# FUNCOES DE BANCO
# ============================================================================

def conectar_banco():
    """Conecta ao banco PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        return conn
    except Exception as e:
        print(f"ERRO ao conectar ao banco: {e}")
        sys.exit(1)


def criar_tabela_parametros_fornecedor(conn):
    """Cria tabela para armazenar parametros de fornecedor."""
    cur = conn.cursor()

    # Criar tabela
    cur.execute("""
        CREATE TABLE IF NOT EXISTS parametros_fornecedor (
            id SERIAL PRIMARY KEY,
            cnpj_fornecedor VARCHAR(20) NOT NULL,
            nome_fornecedor VARCHAR(200),
            cod_empresa INTEGER NOT NULL,
            tipo_destino VARCHAR(20) DEFAULT 'LOJA',
            lead_time_dias INTEGER DEFAULT 15,
            ciclo_pedido_dias INTEGER DEFAULT 7,
            pedido_minimo_valor DECIMAL(12,2) DEFAULT 0,
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ativo BOOLEAN DEFAULT TRUE,
            UNIQUE(cnpj_fornecedor, cod_empresa)
        )
    """)

    # Criar indices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_param_forn_cnpj ON parametros_fornecedor(cnpj_fornecedor)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_param_forn_empresa ON parametros_fornecedor(cod_empresa)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_param_forn_ativo ON parametros_fornecedor(ativo)")

    conn.commit()
    cur.close()
    print("Tabela parametros_fornecedor criada/verificada.")


# ============================================================================
# FUNCOES DE IMPORTACAO
# ============================================================================

def ler_arquivo_fornecedor(arquivo: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Le arquivo Excel de cadastro de fornecedor.

    Returns:
        Tupla (DataFrame, lista_erros)
    """
    erros = []

    try:
        df = pd.read_excel(arquivo)
    except Exception as e:
        erros.append(f"Erro ao ler arquivo: {str(e)}")
        return pd.DataFrame(), erros

    # Verificar colunas obrigatorias
    colunas_obrigatorias = ['CNPJ', 'COD_EMPRESA', 'LEAD_TIME_DIAS']
    colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]

    if colunas_faltando:
        erros.append(f"Colunas obrigatorias faltando: {', '.join(colunas_faltando)}")
        return pd.DataFrame(), erros

    return df, erros


def validar_dados(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Valida dados do DataFrame e retorna dados validos + criticas.

    Returns:
        Tupla (DataFrame_valido, lista_criticas)
    """
    criticas = []
    registros_validos = []

    for idx, row in df.iterrows():
        linha = idx + 2  # +2 porque Excel comeca em 1 e tem header

        # Validar CNPJ
        cnpj_raw = row.get('CNPJ', '')
        # Converter para string e garantir 14 digitos (CNPJ padrao)
        cnpj = str(int(cnpj_raw)).strip() if pd.notna(cnpj_raw) else ''
        if cnpj and len(cnpj) < 14:
            cnpj = cnpj.zfill(14)  # Adicionar zeros a esquerda
        if not cnpj or cnpj == 'nan':
            criticas.append({
                'linha': linha,
                'tipo': 'ERRO',
                'mensagem': 'CNPJ vazio ou invalido'
            })
            continue

        # Validar COD_EMPRESA
        try:
            cod_empresa = int(row['COD_EMPRESA'])
        except (ValueError, TypeError):
            criticas.append({
                'linha': linha,
                'tipo': 'ERRO',
                'mensagem': f'COD_EMPRESA invalido: {row.get("COD_EMPRESA")}'
            })
            continue

        # Validar LEAD_TIME_DIAS
        try:
            lead_time = int(row.get('LEAD_TIME_DIAS', 15))
            if lead_time < 0:
                lead_time = 15
        except (ValueError, TypeError):
            lead_time = 15
            criticas.append({
                'linha': linha,
                'tipo': 'AVISO',
                'mensagem': f'Lead time invalido, usando padrao (15 dias)'
            })

        # Validar CICLO_PEDIDO_DIAS
        try:
            ciclo_pedido = int(row.get('CICLO_PEDIDO_DIAS', 7))
            if ciclo_pedido < 0:
                ciclo_pedido = 7
        except (ValueError, TypeError):
            ciclo_pedido = 7

        # Validar FAT_MINIMO
        try:
            pedido_minimo = float(row.get('FAT_MINIMO', 0))
            if pedido_minimo < 0:
                pedido_minimo = 0
        except (ValueError, TypeError):
            pedido_minimo = 0

        # Nome do fornecedor
        nome_forn = str(row.get('FANTAS', '')).strip()
        if nome_forn == 'nan':
            nome_forn = ''

        # Tipo destino
        tipo_destino = str(row.get('TIPO_DESTINO', 'LOJA')).strip().upper()
        if tipo_destino not in ['LOJA', 'CD']:
            tipo_destino = 'LOJA'

        registros_validos.append({
            'cnpj_fornecedor': cnpj,
            'nome_fornecedor': nome_forn,
            'cod_empresa': cod_empresa,
            'tipo_destino': tipo_destino,
            'lead_time_dias': lead_time,
            'ciclo_pedido_dias': ciclo_pedido,
            'pedido_minimo_valor': pedido_minimo
        })

    return pd.DataFrame(registros_validos), criticas


def gerar_resumo(df_validos: pd.DataFrame, criticas: List[Dict]) -> Dict:
    """
    Gera resumo da importacao para exibicao ao usuario.
    """
    resumo = {
        'total_registros': len(df_validos),
        'total_criticas': len(criticas),
        'erros': len([c for c in criticas if c['tipo'] == 'ERRO']),
        'avisos': len([c for c in criticas if c['tipo'] == 'AVISO']),
        'fornecedores_unicos': df_validos['cnpj_fornecedor'].nunique() if not df_validos.empty else 0,
        'lojas_unicas': df_validos['cod_empresa'].nunique() if not df_validos.empty else 0,
        'criticas': criticas[:20]  # Limitar a 20 primeiras
    }

    if not df_validos.empty:
        # Estatisticas por fornecedor
        resumo['por_fornecedor'] = df_validos.groupby('nome_fornecedor').agg({
            'cod_empresa': 'count',
            'lead_time_dias': 'mean',
            'pedido_minimo_valor': 'mean'
        }).reset_index().to_dict('records')[:10]  # Top 10

        # Estatisticas de lead time
        resumo['lead_time'] = {
            'minimo': int(df_validos['lead_time_dias'].min()),
            'maximo': int(df_validos['lead_time_dias'].max()),
            'media': round(df_validos['lead_time_dias'].mean(), 1)
        }

    return resumo


def importar_parametros(conn, df_validos: pd.DataFrame, modo: str = 'atualizar') -> Dict:
    """
    Importa parametros para o banco de dados.

    Args:
        conn: Conexao com o banco
        df_validos: DataFrame com dados validados
        modo: 'atualizar' (upsert) ou 'substituir' (truncate + insert)

    Returns:
        Dicionario com resultado da importacao
    """
    if df_validos.empty:
        return {'sucesso': False, 'mensagem': 'Nenhum registro valido para importar'}

    cur = conn.cursor()
    resultado = {
        'sucesso': True,
        'inseridos': 0,
        'atualizados': 0,
        'total': len(df_validos)
    }

    try:
        if modo == 'substituir':
            # Desativar todos os registros existentes
            cur.execute("UPDATE parametros_fornecedor SET ativo = FALSE")
            conn.commit()

        # Preparar dados para insercao
        dados = []
        for _, row in df_validos.iterrows():
            dados.append((
                row['cnpj_fornecedor'],
                row['nome_fornecedor'],
                row['cod_empresa'],
                row['tipo_destino'],
                row['lead_time_dias'],
                row['ciclo_pedido_dias'],
                row['pedido_minimo_valor']
            ))

        # Inserir/atualizar com upsert
        execute_values(cur, """
            INSERT INTO parametros_fornecedor
                (cnpj_fornecedor, nome_fornecedor, cod_empresa, tipo_destino,
                 lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor)
            VALUES %s
            ON CONFLICT (cnpj_fornecedor, cod_empresa) DO UPDATE SET
                nome_fornecedor = EXCLUDED.nome_fornecedor,
                tipo_destino = EXCLUDED.tipo_destino,
                lead_time_dias = EXCLUDED.lead_time_dias,
                ciclo_pedido_dias = EXCLUDED.ciclo_pedido_dias,
                pedido_minimo_valor = EXCLUDED.pedido_minimo_valor,
                data_importacao = CURRENT_TIMESTAMP,
                ativo = TRUE
        """, dados)

        conn.commit()
        resultado['mensagem'] = f'Importacao concluida: {len(dados)} registros processados'

    except Exception as e:
        conn.rollback()
        resultado['sucesso'] = False
        resultado['mensagem'] = f'Erro na importacao: {str(e)}'

    cur.close()
    return resultado


# ============================================================================
# FUNCOES DE CONSULTA
# ============================================================================

def buscar_parametros_fornecedor(conn, cnpj: str = None, cod_empresa: int = None) -> List[Dict]:
    """
    Busca parametros de fornecedor no banco.

    Args:
        conn: Conexao com o banco
        cnpj: CNPJ do fornecedor (opcional)
        cod_empresa: Codigo da empresa (opcional)

    Returns:
        Lista de dicionarios com parametros
    """
    cur = conn.cursor()

    query = """
        SELECT cnpj_fornecedor, nome_fornecedor, cod_empresa, tipo_destino,
               lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor, ativo
        FROM parametros_fornecedor
        WHERE 1=1
    """
    params = []

    if cnpj:
        query += " AND cnpj_fornecedor = %s"
        params.append(cnpj)

    if cod_empresa:
        query += " AND cod_empresa = %s"
        params.append(cod_empresa)

    query += " AND ativo = TRUE ORDER BY nome_fornecedor, cod_empresa"

    cur.execute(query, params)
    colunas = ['cnpj_fornecedor', 'nome_fornecedor', 'cod_empresa', 'tipo_destino',
               'lead_time_dias', 'ciclo_pedido_dias', 'pedido_minimo_valor', 'ativo']

    resultado = []
    for row in cur.fetchall():
        resultado.append(dict(zip(colunas, row)))

    cur.close()
    return resultado


def buscar_parametros_por_produto(conn, codigo_produto: int, cod_empresa: int) -> Optional[Dict]:
    """
    Busca parametros do fornecedor de um produto especifico.

    Args:
        conn: Conexao com o banco
        codigo_produto: Codigo do produto
        cod_empresa: Codigo da empresa destino

    Returns:
        Dicionario com parametros ou None se nao encontrado
    """
    cur = conn.cursor()

    # Buscar CNPJ do fornecedor do produto
    cur.execute("""
        SELECT cnpj_fornecedor
        FROM cadastro_produtos_completo
        WHERE cod_produto = %s::text
        LIMIT 1
    """, [codigo_produto])

    row = cur.fetchone()
    if not row or not row[0]:
        cur.close()
        return None

    cnpj_fornecedor = str(row[0]).strip()

    # Buscar parametros do fornecedor para a empresa
    cur.execute("""
        SELECT cnpj_fornecedor, nome_fornecedor, cod_empresa, tipo_destino,
               lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor
        FROM parametros_fornecedor
        WHERE cnpj_fornecedor = %s
          AND cod_empresa = %s
          AND ativo = TRUE
        LIMIT 1
    """, [cnpj_fornecedor, cod_empresa])

    row = cur.fetchone()
    cur.close()

    if not row:
        return None

    return {
        'cnpj_fornecedor': row[0],
        'nome_fornecedor': row[1],
        'cod_empresa': row[2],
        'tipo_destino': row[3],
        'lead_time_dias': row[4],
        'ciclo_pedido_dias': row[5],
        'pedido_minimo_valor': float(row[6]) if row[6] else 0
    }


def verificar_fornecedor_cadastrado(conn, cnpj: str) -> bool:
    """
    Verifica se um fornecedor esta cadastrado (ativo) no sistema.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM parametros_fornecedor
        WHERE cnpj_fornecedor = %s AND ativo = TRUE
    """, [cnpj])
    count = cur.fetchone()[0]
    cur.close()
    return count > 0


# ============================================================================
# FUNCAO PRINCIPAL
# ============================================================================

def verificar_importacao(conn):
    """Verifica estatisticas apos importacao"""
    cur = conn.cursor()

    print("\n" + "=" * 60)
    print("VERIFICACAO DA IMPORTACAO")
    print("=" * 60)

    # Total de registros
    cur.execute("SELECT COUNT(*) FROM parametros_fornecedor WHERE ativo = TRUE")
    total = cur.fetchone()[0]
    print(f"Total de registros ativos: {total:,}")

    # Fornecedores unicos
    cur.execute("SELECT COUNT(DISTINCT cnpj_fornecedor) FROM parametros_fornecedor WHERE ativo = TRUE")
    fornecedores = cur.fetchone()[0]
    print(f"Fornecedores unicos: {fornecedores:,}")

    # Lojas unicas
    cur.execute("SELECT COUNT(DISTINCT cod_empresa) FROM parametros_fornecedor WHERE ativo = TRUE")
    lojas = cur.fetchone()[0]
    print(f"Lojas atendidas: {lojas:,}")

    # Estatisticas de lead time
    cur.execute("""
        SELECT MIN(lead_time_dias), MAX(lead_time_dias), AVG(lead_time_dias)
        FROM parametros_fornecedor WHERE ativo = TRUE
    """)
    row = cur.fetchone()
    print(f"\nLead Time: Min={row[0]} dias, Max={row[1]} dias, Media={row[2]:.1f} dias")

    # Por tipo destino
    cur.execute("""
        SELECT tipo_destino, COUNT(*)
        FROM parametros_fornecedor WHERE ativo = TRUE
        GROUP BY tipo_destino
    """)
    print("\nPor tipo destino:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,} registros")

    # Amostra de dados
    cur.execute("""
        SELECT nome_fornecedor, cod_empresa, lead_time_dias, ciclo_pedido_dias, pedido_minimo_valor
        FROM parametros_fornecedor
        WHERE ativo = TRUE
        ORDER BY nome_fornecedor, cod_empresa
        LIMIT 5
    """)
    print("\nAmostra de registros:")
    for row in cur.fetchall():
        print(f"  {row[0]} (Loja {row[1]}): LT={row[2]}d, Ciclo={row[3]}d, Min=R${row[4]:,.2f}")

    cur.close()


def main():
    """Funcao principal para execucao via linha de comando"""
    print("=" * 60)
    print("IMPORTACAO DE PARAMETROS DE FORNECEDOR")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Verificar se arquivo existe
    if not ARQUIVO_FORNECEDOR.exists():
        print(f"ERRO: Arquivo nao encontrado: {ARQUIVO_FORNECEDOR}")
        sys.exit(1)

    # Conectar
    print("Conectando ao banco de dados...")
    conn = conectar_banco()
    print("Conectado com sucesso!")

    # Criar tabela
    criar_tabela_parametros_fornecedor(conn)

    # Ler arquivo
    print(f"\nLendo arquivo: {ARQUIVO_FORNECEDOR}")
    df, erros_leitura = ler_arquivo_fornecedor(str(ARQUIVO_FORNECEDOR))

    if erros_leitura:
        for erro in erros_leitura:
            print(f"ERRO: {erro}")
        conn.close()
        sys.exit(1)

    print(f"Total de registros no arquivo: {len(df)}")

    # Validar dados
    print("\nValidando dados...")
    df_validos, criticas = validar_dados(df)

    # Mostrar resumo
    resumo = gerar_resumo(df_validos, criticas)
    print(f"\nResumo da validacao:")
    print(f"  Registros validos: {resumo['total_registros']}")
    print(f"  Fornecedores unicos: {resumo['fornecedores_unicos']}")
    print(f"  Lojas unicas: {resumo['lojas_unicas']}")
    print(f"  Criticas: {resumo['erros']} erros, {resumo['avisos']} avisos")

    if criticas:
        print("\nPrimeiras criticas:")
        for c in criticas[:5]:
            print(f"  Linha {c['linha']} [{c['tipo']}]: {c['mensagem']}")

    # Importar
    if not df_validos.empty:
        print("\nImportando dados...")
        resultado = importar_parametros(conn, df_validos)
        print(f"  {resultado['mensagem']}")

        # Verificar
        verificar_importacao(conn)
    else:
        print("\nNenhum registro valido para importar.")

    # Fechar
    conn.close()

    print("\n" + "=" * 60)
    print("IMPORTACAO CONCLUIDA!")
    print("=" * 60)


if __name__ == '__main__':
    main()
