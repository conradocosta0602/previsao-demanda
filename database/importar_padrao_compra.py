# -*- coding: utf-8 -*-
"""
Script de Importacao de Padrao de Compra
========================================
Importa padrao de compra dos arquivos de demanda para a tabela padrao_compra_item.

O padrao de compra define para qual loja o pedido deve ser direcionado:
- Se padrao_compra = cod_empresa: compra direta (loja compra para si)
- Se padrao_compra != cod_empresa: compra centralizada (demanda vai para outra loja)

Colunas esperadas no arquivo de demanda:
- data: Data da venda
- cod_empresa: Codigo da loja de venda (origem)
- codigo: Codigo do produto
- padrao_compra: Codigo da loja destino do pedido

O script processa apenas a data mais recente de cada arquivo para extrair
o padrao de compra atual de cada item/loja.

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

# Batch size para insercao
BATCH_SIZE = 5000


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


# ============================================================================
# FUNCOES DE IMPORTACAO
# ============================================================================

def ler_arquivo_demanda(arquivo: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Le arquivo de demanda (CSV ou texto delimitado por virgula).

    Returns:
        Tupla (DataFrame, lista_erros)
    """
    erros = []

    try:
        # Tentar ler como CSV
        df = pd.read_csv(arquivo)
    except Exception as e:
        erros.append(f"Erro ao ler arquivo: {str(e)}")
        return pd.DataFrame(), erros

    # Verificar colunas obrigatorias
    colunas_obrigatorias = ['data', 'cod_empresa', 'codigo', 'padrao_compra']
    colunas_faltando = [col for col in colunas_obrigatorias if col not in df.columns]

    if colunas_faltando:
        erros.append(f"Colunas obrigatorias faltando: {', '.join(colunas_faltando)}")
        return pd.DataFrame(), erros

    return df, erros


def extrair_padrao_compra_mais_recente(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrai o padrao de compra da data mais recente para cada item/loja.

    O padrao de compra pode mudar ao longo do tempo, entao usamos sempre
    o dado mais recente do arquivo.

    Returns:
        DataFrame com codigo, cod_empresa_venda, cod_empresa_destino, data_referencia
    """
    if df.empty:
        return pd.DataFrame()

    # Converter data para datetime se necessario
    df['data'] = pd.to_datetime(df['data'])

    # Converter padrao_compra para inteiro
    df['padrao_compra'] = df['padrao_compra'].fillna(df['cod_empresa'])  # Se nulo, usa a propria loja
    df['padrao_compra'] = df['padrao_compra'].astype(int)

    # Para cada combinacao item/loja, pegar o padrao da data mais recente
    idx = df.groupby(['codigo', 'cod_empresa'])['data'].idxmax()
    df_mais_recente = df.loc[idx, ['data', 'cod_empresa', 'codigo', 'padrao_compra']].copy()

    # Renomear colunas para clareza
    df_mais_recente = df_mais_recente.rename(columns={
        'cod_empresa': 'cod_empresa_venda',
        'padrao_compra': 'cod_empresa_destino',
        'data': 'data_referencia'
    })

    return df_mais_recente


def validar_padroes(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Valida os padroes de compra extraidos.

    Returns:
        Tupla (DataFrame_valido, lista_criticas)
    """
    criticas = []
    registros_validos = []

    for idx, row in df.iterrows():
        codigo = row['codigo']
        cod_venda = row['cod_empresa_venda']
        cod_destino = row['cod_empresa_destino']
        data_ref = row['data_referencia']

        # Validar codigo do produto
        try:
            codigo = int(codigo)
        except (ValueError, TypeError):
            criticas.append({
                'tipo': 'ERRO',
                'mensagem': f'Codigo do produto invalido: {codigo}'
            })
            continue

        # Validar cod_empresa_venda
        try:
            cod_venda = int(cod_venda)
        except (ValueError, TypeError):
            criticas.append({
                'tipo': 'ERRO',
                'mensagem': f'Cod empresa venda invalido: {cod_venda} (produto {codigo})'
            })
            continue

        # Validar cod_empresa_destino
        try:
            cod_destino = int(cod_destino)
        except (ValueError, TypeError):
            criticas.append({
                'tipo': 'AVISO',
                'mensagem': f'Padrao de compra invalido para produto {codigo}, loja {cod_venda}. Usando a propria loja.'
            })
            cod_destino = cod_venda

        registros_validos.append({
            'codigo': codigo,
            'cod_empresa_venda': cod_venda,
            'cod_empresa_destino': cod_destino,
            'data_referencia': data_ref.date() if hasattr(data_ref, 'date') else data_ref
        })

    return pd.DataFrame(registros_validos), criticas


def importar_padroes_compra(conn, df_validos: pd.DataFrame) -> Dict:
    """
    Importa padroes de compra para o banco de dados.

    Args:
        conn: Conexao com o banco
        df_validos: DataFrame com dados validados

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
        # Preparar dados para insercao
        dados = []
        for _, row in df_validos.iterrows():
            dados.append((
                row['codigo'],
                row['cod_empresa_venda'],
                row['cod_empresa_destino'],
                row['data_referencia']
            ))

        # Inserir/atualizar com upsert em batches
        for i in range(0, len(dados), BATCH_SIZE):
            batch = dados[i:i+BATCH_SIZE]
            execute_values(cur, """
                INSERT INTO padrao_compra_item
                    (codigo, cod_empresa_venda, cod_empresa_destino, data_referencia, data_atualizacao)
                VALUES %s
                ON CONFLICT (codigo, cod_empresa_venda) DO UPDATE SET
                    cod_empresa_destino = EXCLUDED.cod_empresa_destino,
                    data_referencia = EXCLUDED.data_referencia,
                    data_atualizacao = NOW(),
                    updated_at = NOW()
            """, [(d[0], d[1], d[2], d[3], ) for d in batch],
            template="(%s, %s, %s, %s, NOW())")

        conn.commit()
        resultado['mensagem'] = f'Importacao concluida: {len(dados)} registros processados'

    except Exception as e:
        conn.rollback()
        resultado['sucesso'] = False
        resultado['mensagem'] = f'Erro na importacao: {str(e)}'

    cur.close()
    return resultado


def gerar_estatisticas(conn) -> Dict:
    """
    Gera estatisticas da tabela padrao_compra_item.
    """
    cur = conn.cursor()
    stats = {}

    # Total de registros
    cur.execute("SELECT COUNT(*) FROM padrao_compra_item")
    stats['total_registros'] = cur.fetchone()[0]

    # Total de produtos unicos
    cur.execute("SELECT COUNT(DISTINCT codigo) FROM padrao_compra_item")
    stats['produtos_unicos'] = cur.fetchone()[0]

    # Total de lojas de venda
    cur.execute("SELECT COUNT(DISTINCT cod_empresa_venda) FROM padrao_compra_item")
    stats['lojas_venda'] = cur.fetchone()[0]

    # Total de lojas destino
    cur.execute("SELECT COUNT(DISTINCT cod_empresa_destino) FROM padrao_compra_item")
    stats['lojas_destino'] = cur.fetchone()[0]

    # Compras diretas vs centralizadas
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE cod_empresa_venda = cod_empresa_destino) as diretas,
            COUNT(*) FILTER (WHERE cod_empresa_venda != cod_empresa_destino) as centralizadas
        FROM padrao_compra_item
    """)
    row = cur.fetchone()
    stats['compras_diretas'] = row[0]
    stats['compras_centralizadas'] = row[1]

    # Top 5 lojas destino (centralizadoras)
    cur.execute("""
        SELECT cod_empresa_destino, COUNT(*) as qtd
        FROM padrao_compra_item
        WHERE cod_empresa_venda != cod_empresa_destino
        GROUP BY cod_empresa_destino
        ORDER BY qtd DESC
        LIMIT 5
    """)
    stats['top_centralizadoras'] = [(row[0], row[1]) for row in cur.fetchall()]

    cur.close()
    return stats


def processar_arquivo(conn, filepath: str, nome_arquivo: str) -> Tuple[int, int, List[Dict]]:
    """
    Processa um arquivo de demanda e importa padroes de compra.

    Returns:
        Tupla (registros_processados, registros_validos, criticas)
    """
    # Ler arquivo
    df, erros_leitura = ler_arquivo_demanda(filepath)

    if erros_leitura:
        return 0, 0, [{'tipo': 'ERRO', 'mensagem': e} for e in erros_leitura]

    registros_arquivo = len(df)

    # Extrair padroes mais recentes
    df_padroes = extrair_padrao_compra_mais_recente(df)

    if df_padroes.empty:
        return registros_arquivo, 0, [{'tipo': 'AVISO', 'mensagem': 'Nenhum padrao de compra extraido'}]

    # Validar
    df_validos, criticas = validar_padroes(df_padroes)

    if df_validos.empty:
        return registros_arquivo, 0, criticas

    # Importar
    resultado = importar_padroes_compra(conn, df_validos)

    if not resultado['sucesso']:
        criticas.append({'tipo': 'ERRO', 'mensagem': resultado['mensagem']})

    return registros_arquivo, len(df_validos), criticas


def importar_de_diretorio(conn, diretorio: str, padrao: str = "demanda_*") -> Dict:
    """
    Importa padroes de compra de todos os arquivos de demanda em um diretorio.

    Args:
        conn: Conexao com o banco
        diretorio: Caminho do diretorio
        padrao: Padrao glob para filtrar arquivos (default: demanda_*)

    Returns:
        Dicionario com resultado da importacao
    """
    from glob import glob

    diretorio = Path(diretorio)
    arquivos = list(diretorio.glob(padrao))

    # Filtrar apenas arquivos (nao diretorios)
    arquivos = [f for f in arquivos if f.is_file()]

    if not arquivos:
        return {
            'sucesso': False,
            'mensagem': f'Nenhum arquivo encontrado com padrao "{padrao}" em {diretorio}'
        }

    resultado = {
        'sucesso': True,
        'arquivos_processados': 0,
        'total_registros_lidos': 0,
        'total_padroes_importados': 0,
        'criticas': []
    }

    print(f"Encontrados {len(arquivos)} arquivos para processar...")

    for arquivo in sorted(arquivos):
        print(f"  Processando: {arquivo.name}...", end=" ")

        registros, padroes, criticas = processar_arquivo(conn, str(arquivo), arquivo.name)

        resultado['arquivos_processados'] += 1
        resultado['total_registros_lidos'] += registros
        resultado['total_padroes_importados'] += padroes
        resultado['criticas'].extend(criticas)

        print(f"OK ({padroes} padroes)")

    resultado['mensagem'] = (
        f"Processados {resultado['arquivos_processados']} arquivos. "
        f"{resultado['total_padroes_importados']} padroes importados de "
        f"{resultado['total_registros_lidos']} registros lidos."
    )

    return resultado


# ============================================================================
# FUNCOES DE CONSULTA
# ============================================================================

def buscar_padrao_compra(conn, codigo: int, cod_empresa: int) -> Optional[Dict]:
    """
    Busca o padrao de compra de um item/loja especifico.

    Args:
        conn: Conexao com o banco
        codigo: Codigo do produto
        cod_empresa: Codigo da loja de venda (origem)

    Returns:
        Dicionario com padrao de compra ou None se nao encontrado
    """
    cur = conn.cursor()

    cur.execute("""
        SELECT codigo, cod_empresa_venda, cod_empresa_destino, data_referencia
        FROM padrao_compra_item
        WHERE codigo = %s AND cod_empresa_venda = %s
    """, [codigo, cod_empresa])

    row = cur.fetchone()
    cur.close()

    if not row:
        return None

    return {
        'codigo': row[0],
        'cod_empresa_venda': row[1],
        'cod_empresa_destino': row[2],
        'data_referencia': row[3],
        'tipo': 'Direto' if row[1] == row[2] else 'Centralizado'
    }


def buscar_padroes_por_destino(conn, cod_empresa_destino: int) -> List[Dict]:
    """
    Busca todos os padroes de compra que apontam para uma loja destino.

    Util para saber quais lojas/itens enviam pedidos para uma determinada loja.

    Args:
        conn: Conexao com o banco
        cod_empresa_destino: Codigo da loja destino

    Returns:
        Lista de dicionarios com os padroes
    """
    cur = conn.cursor()

    cur.execute("""
        SELECT codigo, cod_empresa_venda, cod_empresa_destino, data_referencia
        FROM padrao_compra_item
        WHERE cod_empresa_destino = %s
        ORDER BY codigo, cod_empresa_venda
    """, [cod_empresa_destino])

    resultado = []
    for row in cur.fetchall():
        resultado.append({
            'codigo': row[0],
            'cod_empresa_venda': row[1],
            'cod_empresa_destino': row[2],
            'data_referencia': row[3]
        })

    cur.close()
    return resultado


def verificar_importacao(conn):
    """Exibe estatisticas da importacao"""
    stats = gerar_estatisticas(conn)

    print("\n" + "=" * 60)
    print("ESTATISTICAS DA IMPORTACAO - PADRAO DE COMPRA")
    print("=" * 60)

    print(f"Total de registros: {stats['total_registros']:,}")
    print(f"Produtos unicos: {stats['produtos_unicos']:,}")
    print(f"Lojas de venda (origem): {stats['lojas_venda']:,}")
    print(f"Lojas destino: {stats['lojas_destino']:,}")
    print()
    print(f"Compras diretas (loja = destino): {stats['compras_diretas']:,}")
    print(f"Compras centralizadas (loja != destino): {stats['compras_centralizadas']:,}")

    if stats['top_centralizadoras']:
        print("\nTop 5 lojas centralizadoras (recebem pedidos de outras lojas):")
        for loja, qtd in stats['top_centralizadoras']:
            print(f"  Loja {loja}: {qtd:,} itens")


# ============================================================================
# FUNCAO PRINCIPAL
# ============================================================================

def main():
    """Funcao principal para execucao via linha de comando"""
    import argparse

    parser = argparse.ArgumentParser(description='Importa padroes de compra dos arquivos de demanda')
    parser.add_argument('--arquivo', '-a', help='Arquivo especifico para importar')
    parser.add_argument('--diretorio', '-d', help='Diretorio com arquivos de demanda')
    parser.add_argument('--padrao', '-p', default='demanda_*', help='Padrao glob para arquivos (default: demanda_*)')

    args = parser.parse_args()

    print("=" * 60)
    print("IMPORTACAO DE PADRAO DE COMPRA")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Conectar
    print("Conectando ao banco de dados...")
    conn = conectar_banco()
    print("Conectado com sucesso!")

    if args.arquivo:
        # Importar arquivo especifico
        arquivo = Path(args.arquivo)
        if not arquivo.exists():
            print(f"ERRO: Arquivo nao encontrado: {arquivo}")
            conn.close()
            sys.exit(1)

        print(f"\nProcessando arquivo: {arquivo}")
        registros, padroes, criticas = processar_arquivo(conn, str(arquivo), arquivo.name)
        print(f"  Registros lidos: {registros:,}")
        print(f"  Padroes importados: {padroes:,}")

        if criticas:
            print(f"  Criticas: {len(criticas)}")
            for c in criticas[:5]:
                print(f"    [{c['tipo']}] {c['mensagem']}")

    elif args.diretorio:
        # Importar de diretorio
        diretorio = Path(args.diretorio)
        if not diretorio.exists():
            print(f"ERRO: Diretorio nao encontrado: {diretorio}")
            conn.close()
            sys.exit(1)

        print(f"\nImportando de: {diretorio}")
        print(f"Padrao de arquivos: {args.padrao}")

        resultado = importar_de_diretorio(conn, str(diretorio), args.padrao)
        print(f"\n{resultado['mensagem']}")

        if resultado['criticas']:
            erros = [c for c in resultado['criticas'] if c['tipo'] == 'ERRO']
            if erros:
                print(f"\nErros ({len(erros)}):")
                for e in erros[:5]:
                    print(f"  {e['mensagem']}")

    else:
        # Usar diretorio padrao
        diretorio = Path(__file__).parent.parent
        print(f"\nBuscando arquivos de demanda em: {diretorio}")
        resultado = importar_de_diretorio(conn, str(diretorio), "demanda_*")
        print(f"\n{resultado['mensagem']}")

    # Verificar importacao
    verificar_importacao(conn)

    # Fechar
    conn.close()

    print("\n" + "=" * 60)
    print("IMPORTACAO CONCLUIDA!")
    print("=" * 60)


if __name__ == '__main__':
    main()
