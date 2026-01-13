# -*- coding: utf-8 -*-
"""
Script de Importação de Dados para o Banco de Dados
Importa dados de cadastros, histórico e situação atual
Aceita formatos: CSV, XLSX, XLS
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from datetime import datetime
import os

# ===========================================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ===========================================================================

DB_CONFIG = {
    'host': 'localhost',
    'database': 'demanda_reabastecimento',
    'user': 'postgres',
    'password': 'FerreiraCost@01',
    'port': 5432
}

# ===========================================================================
# CONFIGURAÇÃO DOS ARQUIVOS
# ===========================================================================

# Diretório onde você vai colocar os arquivos (CSV ou Excel)
DATA_DIR = Path(r'C:\Users\valter.lino\Desktop\Treinamentos\VS\previsao-demanda\data_import')

# Mapeamento: nome base do arquivo → configuração
# O script procura automaticamente por: .csv, .xlsx, .xls
MAPEAMENTO_ARQUIVOS = {
    # CADASTROS (Camada 1)
    'cadastro_produtos': {
        'tabela': 'cadastro_produtos',
        'tipo': 'cadastro',
        'colunas_obrigatorias': ['codigo', 'descricao'],
        'descricao': 'Cadastro de Produtos'
    },
    'cadastro_fornecedores': {
        'tabela': 'cadastro_fornecedores',
        'tipo': 'cadastro',
        'colunas_obrigatorias': ['codigo_fornecedor', 'nome_fornecedor'],
        'descricao': 'Cadastro de Fornecedores'
    },
    'cadastro_lojas': {
        'tabela': 'cadastro_lojas',
        'tipo': 'cadastro',
        'colunas_obrigatorias': ['cod_empresa', 'nome_loja'],
        'descricao': 'Cadastro de Lojas'
    },

    # SITUAÇÃO ATUAL (Camada 2)
    'estoque_atual': {
        'tabela': 'estoque_atual',
        'tipo': 'snapshot',
        'colunas_obrigatorias': ['cod_empresa', 'codigo', 'qtd_estoque'],
        'descricao': 'Estoque Atual'
    },
    'pedidos_abertos': {
        'tabela': 'pedidos_abertos',
        'tipo': 'snapshot',
        'colunas_obrigatorias': ['numero_pedido', 'tipo_pedido', 'data_pedido'],
        'descricao': 'Pedidos em Aberto'
    },
    'transito_atual': {
        'tabela': 'transito_atual',
        'tipo': 'snapshot',
        'colunas_obrigatorias': ['codigo', 'qtd_transito', 'data_chegada_prevista'],
        'descricao': 'Produtos em Trânsito'
    },

    # HISTÓRICO (Camada 3)
    'historico_vendas': {
        'tabela': 'historico_vendas_diario',
        'tipo': 'historico',
        'colunas_obrigatorias': ['data', 'cod_empresa', 'codigo', 'qtd_venda'],
        'descricao': 'Histórico de Vendas'
    },
    'historico_estoque': {
        'tabela': 'historico_estoque_diario',
        'tipo': 'historico',
        'colunas_obrigatorias': ['data', 'cod_empresa', 'codigo', 'estoque_diario'],
        'descricao': 'Histórico de Estoque'
    },
    'historico_precos': {
        'tabela': 'historico_precos',
        'tipo': 'historico',
        'colunas_obrigatorias': ['data', 'cod_empresa', 'codigo', 'preco_venda'],
        'descricao': 'Histórico de Preços'
    },
    'eventos_promocionais': {
        'tabela': 'eventos_promocionais',
        'tipo': 'calendario',
        'colunas_obrigatorias': ['nome_evento', 'data_inicio', 'data_fim'],
        'descricao': 'Eventos Promocionais'
    }
}

# ===========================================================================
# FUNÇÕES AUXILIARES
# ===========================================================================

def conectar_banco():
    """Conecta ao banco de dados PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"✅ Conectado ao banco '{DB_CONFIG['database']}'")
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        sys.exit(1)


def encontrar_arquivo(nome_base):
    """
    Procura por arquivo com o nome base em múltiplos formatos
    Retorna (caminho, extensão) ou (None, None) se não encontrado
    """
    extensoes = ['.csv', '.xlsx', '.xls']

    for ext in extensoes:
        caminho = DATA_DIR / f"{nome_base}{ext}"
        if caminho.exists():
            return caminho, ext

    return None, None


def ler_arquivo(caminho, extensao):
    """
    Lê arquivo CSV ou Excel e retorna DataFrame
    """
    try:
        if extensao == '.csv':
            # Tentar diferentes encodings
            for encoding in ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']:
                try:
                    df = pd.read_csv(caminho, encoding=encoding)
                    print(f"✅ Lido: {len(df)} registros (CSV - {encoding})")
                    return df
                except UnicodeDecodeError:
                    continue
            raise Exception("Não foi possível decodificar o CSV com os encodings testados")

        elif extensao in ['.xlsx', '.xls']:
            # Ler Excel (primeira planilha)
            df = pd.read_excel(caminho, engine='openpyxl' if extensao == '.xlsx' else None)
            print(f"✅ Lido: {len(df)} registros (Excel)")
            return df

        else:
            raise Exception(f"Formato não suportado: {extensao}")

    except Exception as e:
        raise Exception(f"Erro ao ler arquivo: {e}")


def processar_datas(df, colunas_data):
    """Converte colunas de data para datetime"""
    for col in colunas_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    return df


def preparar_cadastro_produtos(df):
    """Prepara DataFrame de cadastro de produtos"""
    # Colunas esperadas
    colunas_map = {
        'codigo': 'codigo',
        'descricao': 'descricao',
        'categoria': 'categoria',
        'subcategoria': 'subcategoria',
        'und_venda': 'und_venda',
        'curva_abc': 'curva_abc'
    }

    # Renomear se necessário
    df_prep = df.copy()

    # Garantir que tem código e descrição
    if 'codigo' not in df_prep.columns:
        raise ValueError("Coluna 'codigo' é obrigatória em cadastro_produtos.csv")

    # Adicionar colunas padrão se não existirem
    if 'ativo' not in df_prep.columns:
        df_prep['ativo'] = True

    return df_prep


def preparar_historico_vendas(df):
    """Prepara DataFrame de histórico de vendas"""
    df_prep = df.copy()

    # Converter data
    df_prep = processar_datas(df_prep, ['data'])

    # Extrair componentes da data
    df_prep['dia_semana'] = df_prep['data'].dt.dayofweek + 1  # 1=Segunda
    df_prep['dia_mes'] = df_prep['data'].dt.day
    df_prep['semana_ano'] = df_prep['data'].dt.isocalendar().week
    df_prep['mes'] = df_prep['data'].dt.month
    df_prep['ano'] = df_prep['data'].dt.year

    # Detectar fim de semana
    df_prep['fim_semana'] = df_prep['dia_semana'].isin([6, 7])

    # Garantir tipos corretos
    df_prep['cod_empresa'] = df_prep['cod_empresa'].astype(int)
    df_prep['codigo'] = df_prep['codigo'].astype(int)
    df_prep['qtd_venda'] = df_prep['qtd_venda'].astype(float)

    return df_prep


def preparar_historico_estoque(df):
    """Prepara DataFrame de histórico de estoque"""
    df_prep = df.copy()

    # Converter data
    df_prep = processar_datas(df_prep, ['data'])

    # Garantir tipos corretos
    df_prep['cod_empresa'] = df_prep['cod_empresa'].astype(int)
    df_prep['codigo'] = df_prep['codigo'].astype(int)
    df_prep['estoque_diario'] = df_prep['estoque_diario'].astype(float)

    return df_prep


def preparar_eventos_promocionais(df):
    """Prepara DataFrame de eventos promocionais"""
    df_prep = df.copy()

    # Converter datas
    df_prep = processar_datas(df_prep, ['data_inicio', 'data_fim'])

    # Adicionar flag ativo
    if 'ativo' not in df_prep.columns:
        df_prep['ativo'] = True

    return df_prep


# Mapeamento de funções de preparação
FUNCOES_PREPARACAO = {
    'cadastro_produtos': preparar_cadastro_produtos,
    'historico_vendas_diario': preparar_historico_vendas,
    'historico_estoque_diario': preparar_historico_estoque,
    'eventos_promocionais': preparar_eventos_promocionais
}


def inserir_dataframe(conn, df, tabela, batch_size=1000):
    """
    Insere DataFrame no banco usando INSERT em lote
    """
    if len(df) == 0:
        print(f"⚠️  DataFrame vazio, nada a inserir em {tabela}")
        return 0

    cursor = conn.cursor()

    # Obter colunas do DataFrame que existem
    colunas = list(df.columns)
    colunas_str = ', '.join(colunas)
    placeholders = ', '.join(['%s'] * len(colunas))

    # Preparar valores
    valores = df[colunas].values.tolist()

    # Converter NaN para None
    valores = [[None if pd.isna(v) else v for v in row] for row in valores]

    # SQL de insert
    sql = f"""
        INSERT INTO {tabela} ({colunas_str})
        VALUES %s
        ON CONFLICT DO NOTHING
    """

    try:
        # Inserir em lotes
        total_inserido = 0
        for i in range(0, len(valores), batch_size):
            batch = valores[i:i + batch_size]
            execute_values(cursor, sql, batch)
            total_inserido += len(batch)
            print(f"  ⏳ Inseridos {total_inserido}/{len(valores)} registros...", end='\r')

        conn.commit()
        print(f"\n  ✅ {total_inserido} registros inseridos em {tabela}")
        cursor.close()
        return total_inserido

    except Exception as e:
        conn.rollback()
        cursor.close()
        print(f"\n  ❌ Erro ao inserir em {tabela}: {e}")
        raise


# ===========================================================================
# FUNÇÃO PRINCIPAL DE IMPORTAÇÃO
# ===========================================================================

def importar_arquivo(nome_base, config, conn):
    """
    Importa um arquivo (CSV ou Excel) para o banco
    """
    print(f"\n{'='*60}")
    print(f"📂 Processando: {config['descricao']}")
    print(f"{'='*60}")

    # Procurar arquivo em diferentes formatos
    caminho, extensao = encontrar_arquivo(nome_base)

    if caminho is None:
        print(f"⚠️  Arquivo não encontrado: {nome_base}.[csv|xlsx|xls]")
        print(f"   Procurado em: {DATA_DIR}")
        print(f"   Pulando...")
        return False

    print(f"📄 Arquivo encontrado: {caminho.name}")

    # Ler arquivo
    try:
        df = ler_arquivo(caminho, extensao)
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return False

    # Limpar nomes de colunas (remover espaços extras, converter para minúsculas)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

    # Validar colunas obrigatórias
    colunas_obrig = config['colunas_obrigatorias']
    faltando = [col for col in colunas_obrig if col not in df.columns]

    if faltando:
        print(f"❌ Colunas obrigatórias faltando: {faltando}")
        print(f"   Colunas encontradas: {list(df.columns)}")
        print(f"   💡 Dica: As colunas do arquivo devem ter exatamente esses nomes")
        return False

    # Preparar dados (função específica se existir)
    tabela = config['tabela']
    if tabela in FUNCOES_PREPARACAO:
        print(f"🔧 Preparando dados...")
        try:
            df = FUNCOES_PREPARACAO[tabela](df)
        except Exception as e:
            print(f"❌ Erro ao preparar dados: {e}")
            return False

    # Inserir no banco
    print(f"💾 Inserindo em '{tabela}'...")
    try:
        total = inserir_dataframe(conn, df, tabela)
        print(f"✅ Importação concluída: {total} registros")
        return True
    except Exception as e:
        print(f"❌ Erro na importação: {e}")
        return False


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    """Função principal"""
    print("="*60)
    print("   IMPORTAÇÃO DE DADOS PARA BANCO DE DADOS")
    print("="*60)
    print()
    print(f"📁 Diretório de dados: {DATA_DIR}")
    print(f"🗄️  Banco: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print(f"📋 Formatos aceitos: CSV, XLSX, XLS")
    print()

    # Criar diretório se não existir
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Conectar ao banco
    conn = conectar_banco()

    # Estatísticas
    total_arquivos = len(MAPEAMENTO_ARQUIVOS)
    importados = 0
    pulados = 0
    erros = 0

    # Processar cada arquivo
    for nome_base, config in MAPEAMENTO_ARQUIVOS.items():
        try:
            sucesso = importar_arquivo(nome_base, config, conn)
            if sucesso:
                importados += 1
            else:
                pulados += 1
        except Exception as e:
            print(f"❌ ERRO FATAL ao processar {nome_base}: {e}")
            erros += 1

    # Fechar conexão
    conn.close()

    # Resumo
    print()
    print("="*60)
    print("   RESUMO DA IMPORTAÇÃO")
    print("="*60)
    print(f"Total de arquivos configurados: {total_arquivos}")
    print(f"✅ Importados com sucesso: {importados}")
    print(f"⚠️  Pulados (não encontrados): {pulados}")
    print(f"❌ Erros: {erros}")
    print("="*60)

    if importados > 0:
        print()
        print("🎉 Importação concluída!")
        print()
        print("📊 Próximos passos:")
        print("  1. Verificar dados importados no banco")
        print("  2. Rodar queries de validação")
        print("  3. Atualizar views materializadas:")
        print("     REFRESH MATERIALIZED VIEW vw_estoque_total;")
        print("     REFRESH MATERIALIZED VIEW vw_vendas_mensais;")
    elif pulados == total_arquivos:
        print()
        print("⚠️  Nenhum arquivo encontrado!")
        print()
        print("📝 Instruções:")
        print(f"  1. Coloque seus arquivos (CSV ou Excel) na pasta:")
        print(f"     {DATA_DIR}")
        print(f"  2. Os arquivos devem ter um destes nomes:")
        for nome in MAPEAMENTO_ARQUIVOS.keys():
            print(f"     - {nome}.csv (ou .xlsx ou .xls)")
        print(f"  3. Execute este script novamente")


if __name__ == '__main__':
    main()
