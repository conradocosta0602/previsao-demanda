# -*- coding: utf-8 -*-
"""
Modulo de Padrao de Compra
==========================
Gerencia a logica de padrao de compra centralizado.

O padrao de compra define para qual loja o pedido deve ser direcionado:
- Se padrao_compra = cod_empresa: compra direta (loja compra para si)
- Se padrao_compra != cod_empresa: compra centralizada (demanda vai para outra loja)

Logica de calculo:
1. Coleta demandas de todas as lojas que apontam para a mesma loja destino
2. Analisa estoque INDIVIDUAL de cada loja de venda
3. Se loja tem estoque suficiente: nao entra no pedido
4. Se loja tem estoque parcial: diferenca entra no pedido
5. Se loja sem estoque: demanda completa entra no pedido
6. Soma das necessidades = pedido da loja destino
7. Lead time = lead time da loja destino + dias de transferencia (parametro global)
8. Dados (CUE, preco) = da loja destino

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta, date
from dataclasses import dataclass

# ============================================================================
# CLASSES DE DADOS
# ============================================================================

@dataclass
class DemandaLoja:
    """Representa a demanda de uma loja para um item."""
    codigo: int
    cod_empresa_venda: int
    demanda_periodo: float
    estoque_disponivel: float
    estoque_transito: float
    estoque_efetivo: float
    necessidade: float  # max(0, demanda - estoque)
    contribui_pedido: bool  # True se precisa pedir


@dataclass
class PedidoCentralizado:
    """Representa um pedido centralizado para uma loja destino."""
    cod_empresa_destino: int
    codigo: int
    quantidade_total: float  # Soma das necessidades
    lead_time_efetivo: int  # Lead time destino + dias transferencia
    lojas_origem: List[DemandaLoja]
    valor_total: float
    cue_destino: float
    tem_criticas: bool
    criticas: List[Dict]


# ============================================================================
# FUNCOES DE ACESSO AO BANCO
# ============================================================================

def buscar_parametro_global(conn, chave: str, valor_padrao: str = None) -> str:
    """
    Busca um parametro global do sistema.

    Args:
        conn: Conexao com o banco
        chave: Chave do parametro
        valor_padrao: Valor padrao se nao encontrado

    Returns:
        Valor do parametro ou valor_padrao
    """
    try:
        query = """
            SELECT valor FROM parametros_globais
            WHERE chave = %s AND ativo = TRUE
        """
        df = pd.read_sql(query, conn, params=[chave])

        if df.empty:
            return valor_padrao

        return df.iloc[0]['valor']

    except Exception:
        return valor_padrao


def get_dias_transferencia(conn) -> int:
    """
    Retorna o parametro global de dias de transferencia.

    Args:
        conn: Conexao com o banco

    Returns:
        Numero de dias de transferencia (padrao: 10)
    """
    valor = buscar_parametro_global(conn, 'dias_transferencia_padrao_compra', '10')
    try:
        return int(valor)
    except (ValueError, TypeError):
        return 10


def buscar_padrao_compra_item(conn, codigo: int, cod_empresa_venda: int) -> Optional[int]:
    """
    Busca o padrao de compra de um item/loja especifico.

    Args:
        conn: Conexao com o banco
        codigo: Codigo do produto
        cod_empresa_venda: Codigo da loja de venda (origem)

    Returns:
        Codigo da loja destino ou None se nao definido
    """
    try:
        query = """
            SELECT cod_empresa_destino FROM padrao_compra_item
            WHERE codigo = %s AND cod_empresa_venda = %s
        """
        df = pd.read_sql(query, conn, params=[codigo, cod_empresa_venda])

        if df.empty:
            return None

        return int(df.iloc[0]['cod_empresa_destino'])

    except Exception:
        return None


def buscar_padroes_compra_lote(conn, codigos: List[int], cod_empresas: List[int]) -> Dict[Tuple[int, int], int]:
    """
    Busca padroes de compra em lote para otimizar performance.

    Args:
        conn: Conexao com o banco
        codigos: Lista de codigos de produtos
        cod_empresas: Lista de codigos de lojas

    Returns:
        Dicionario (codigo, cod_empresa_venda) -> cod_empresa_destino
    """
    if not codigos or not cod_empresas:
        return {}

    try:
        placeholders_cod = ','.join(['%s'] * len(codigos))
        placeholders_emp = ','.join(['%s'] * len(cod_empresas))

        query = f"""
            SELECT codigo, cod_empresa_venda, cod_empresa_destino
            FROM padrao_compra_item
            WHERE codigo IN ({placeholders_cod})
              AND cod_empresa_venda IN ({placeholders_emp})
        """
        params = list(codigos) + list(cod_empresas)
        df = pd.read_sql(query, conn, params=params)

        resultado = {}
        for _, row in df.iterrows():
            key = (int(row['codigo']), int(row['cod_empresa_venda']))
            resultado[key] = int(row['cod_empresa_destino'])

        return resultado

    except Exception:
        return {}


def buscar_lojas_origem_para_destino(conn, cod_empresa_destino: int, codigo: int = None) -> List[Tuple[int, int]]:
    """
    Busca todas as lojas que enviam pedidos para uma loja destino.

    Args:
        conn: Conexao com o banco
        cod_empresa_destino: Codigo da loja destino
        codigo: Codigo do produto (opcional, se None busca todos)

    Returns:
        Lista de tuplas (codigo, cod_empresa_venda)
    """
    try:
        if codigo is not None:
            query = """
                SELECT codigo, cod_empresa_venda
                FROM padrao_compra_item
                WHERE cod_empresa_destino = %s AND codigo = %s
            """
            params = [cod_empresa_destino, codigo]
        else:
            query = """
                SELECT codigo, cod_empresa_venda
                FROM padrao_compra_item
                WHERE cod_empresa_destino = %s
            """
            params = [cod_empresa_destino]

        df = pd.read_sql(query, conn, params=params)

        return [(int(row['codigo']), int(row['cod_empresa_venda'])) for _, row in df.iterrows()]

    except Exception:
        return []


def buscar_itens_sem_padrao(conn, codigos: List[int] = None, cod_empresas: List[int] = None) -> List[Dict]:
    """
    Busca itens que nao tem padrao de compra definido.

    Args:
        conn: Conexao com o banco
        codigos: Lista de codigos para filtrar (opcional)
        cod_empresas: Lista de lojas para filtrar (opcional)

    Returns:
        Lista de dicionarios com itens sem padrao
    """
    try:
        # Base query
        query = """
            SELECT DISTINCT
                hvd.codigo,
                cp.descricao as descricao_produto,
                hvd.cod_empresa,
                cl.nome_loja
            FROM historico_vendas_diario hvd
            LEFT JOIN cadastro_produtos cp ON hvd.codigo = cp.codigo
            LEFT JOIN cadastro_lojas cl ON hvd.cod_empresa = cl.cod_empresa
            WHERE NOT EXISTS (
                SELECT 1 FROM padrao_compra_item pci
                WHERE pci.codigo = hvd.codigo
                  AND pci.cod_empresa_venda = hvd.cod_empresa
            )
            AND hvd.data >= CURRENT_DATE - INTERVAL '90 days'
        """

        params = []

        if codigos:
            query += f" AND hvd.codigo IN ({','.join(['%s'] * len(codigos))})"
            params.extend(codigos)

        if cod_empresas:
            query += f" AND hvd.cod_empresa IN ({','.join(['%s'] * len(cod_empresas))})"
            params.extend(cod_empresas)

        query += " ORDER BY hvd.codigo, hvd.cod_empresa"

        df = pd.read_sql(query, conn, params=params if params else None)

        return df.to_dict('records')

    except Exception:
        return []


# ============================================================================
# CLASSE PRINCIPAL
# ============================================================================

class PadraoCompraCalculator:
    """
    Calculador de pedidos com logica de padrao de compra.

    Esta classe coordena a logica de centralizacao de pedidos,
    agregando demandas de multiplas lojas em uma unica loja destino.
    """

    def __init__(self, conn):
        """
        Args:
            conn: Conexao com o banco PostgreSQL
        """
        self.conn = conn
        self._cache_padroes = None
        self._cache_estoque = None
        self._dias_transferencia = None

    @property
    def dias_transferencia(self) -> int:
        """Retorna dias de transferencia (com cache)."""
        if self._dias_transferencia is None:
            self._dias_transferencia = get_dias_transferencia(self.conn)
        return self._dias_transferencia

    def precarregar_padroes(self, codigos: List[int], cod_empresas: List[int]) -> None:
        """
        Pre-carrega padroes de compra em lote para otimizar performance.

        Args:
            codigos: Lista de codigos de produtos
            cod_empresas: Lista de codigos de lojas
        """
        self._cache_padroes = buscar_padroes_compra_lote(self.conn, codigos, cod_empresas)
        print(f"  [CACHE] Padroes de compra pre-carregados: {len(self._cache_padroes)} registros")

    def precarregar_estoque(self, codigos: List[int], cod_empresas: List[int]) -> None:
        """
        Pre-carrega estoque de todos os produtos/lojas em lote.

        Args:
            codigos: Lista de codigos de produtos
            cod_empresas: Lista de codigos de lojas
        """
        if not codigos or not cod_empresas:
            self._cache_estoque = {}
            return

        try:
            placeholders_cod = ','.join(['%s'] * len(codigos))
            placeholders_emp = ','.join(['%s'] * len(cod_empresas))

            query = f"""
                SELECT
                    codigo, cod_empresa,
                    COALESCE(estoque, 0) as estoque_disponivel,
                    COALESCE(qtd_pendente, 0) as qtd_pendente,
                    COALESCE(qtd_pend_transf, 0) as qtd_pend_transf,
                    COALESCE(cue, 0) as cue
                FROM estoque_posicao_atual
                WHERE codigo IN ({placeholders_cod})
                  AND cod_empresa IN ({placeholders_emp})
            """
            params = list(codigos) + list(cod_empresas)
            df = pd.read_sql(query, self.conn, params=params)

            self._cache_estoque = {}
            for _, row in df.iterrows():
                key = (int(row['codigo']), int(row['cod_empresa']))
                self._cache_estoque[key] = {
                    'estoque_disponivel': float(row['estoque_disponivel']),
                    'estoque_transito': float(row['qtd_pendente']) + float(row['qtd_pend_transf']),
                    'cue': float(row['cue'])
                }

            print(f"  [CACHE] Estoque pre-carregado: {len(self._cache_estoque)} registros")

        except Exception as e:
            print(f"  [CACHE] Erro ao pre-carregar estoque: {e}")
            self._cache_estoque = {}

    def get_padrao_compra(self, codigo: int, cod_empresa_venda: int) -> int:
        """
        Retorna o padrao de compra de um item/loja.

        Args:
            codigo: Codigo do produto
            cod_empresa_venda: Codigo da loja de venda

        Returns:
            Codigo da loja destino (ou a propria loja se nao definido)
        """
        # Usar cache se disponivel
        if self._cache_padroes is not None:
            key = (codigo, cod_empresa_venda)
            destino = self._cache_padroes.get(key)
            if destino is not None:
                return destino
            # Se nao encontrado no cache, assume compra direta
            return cod_empresa_venda

        # Fallback: query individual
        destino = buscar_padrao_compra_item(self.conn, codigo, cod_empresa_venda)
        if destino is not None:
            return destino

        # Se nao definido, assume compra direta
        return cod_empresa_venda

    def get_estoque(self, codigo: int, cod_empresa: int) -> Dict:
        """
        Retorna estoque de um item/loja.

        Args:
            codigo: Codigo do produto
            cod_empresa: Codigo da loja

        Returns:
            Dicionario com estoque_disponivel, estoque_transito, cue
        """
        default = {'estoque_disponivel': 0, 'estoque_transito': 0, 'cue': 0}

        # Usar cache se disponivel
        if self._cache_estoque is not None:
            key = (codigo, cod_empresa)
            return self._cache_estoque.get(key, default)

        # Fallback: query individual
        try:
            query = """
                SELECT
                    COALESCE(estoque, 0) as estoque_disponivel,
                    COALESCE(qtd_pendente, 0) + COALESCE(qtd_pend_transf, 0) as estoque_transito,
                    COALESCE(cue, 0) as cue
                FROM estoque_posicao_atual
                WHERE codigo = %s AND cod_empresa = %s
            """
            df = pd.read_sql(query, self.conn, params=[codigo, cod_empresa])

            if df.empty:
                return default

            row = df.iloc[0]
            return {
                'estoque_disponivel': float(row['estoque_disponivel']),
                'estoque_transito': float(row['estoque_transito']),
                'cue': float(row['cue'])
            }
        except Exception:
            return default

    def calcular_necessidade_loja(
        self,
        codigo: int,
        cod_empresa: int,
        demanda_periodo: float
    ) -> DemandaLoja:
        """
        Calcula a necessidade de pedido de uma loja especifica.

        Analisa estoque individual da loja e determina quanto precisa pedir.

        Args:
            codigo: Codigo do produto
            cod_empresa: Codigo da loja
            demanda_periodo: Demanda prevista para o periodo

        Returns:
            DemandaLoja com analise da necessidade
        """
        estoque = self.get_estoque(codigo, cod_empresa)
        estoque_disp = estoque['estoque_disponivel']
        estoque_trans = estoque['estoque_transito']
        estoque_efetivo = estoque_disp + estoque_trans

        # Calcular necessidade
        necessidade = max(0, demanda_periodo - estoque_efetivo)
        contribui = necessidade > 0

        return DemandaLoja(
            codigo=codigo,
            cod_empresa_venda=cod_empresa,
            demanda_periodo=demanda_periodo,
            estoque_disponivel=estoque_disp,
            estoque_transito=estoque_trans,
            estoque_efetivo=estoque_efetivo,
            necessidade=necessidade,
            contribui_pedido=contribui
        )

    def calcular_pedido_item(
        self,
        codigo: int,
        demandas_por_loja: Dict[int, float],
        lead_time_destino: int,
        cod_empresa_destino: int = None
    ) -> Dict[int, PedidoCentralizado]:
        """
        Calcula pedidos para um item, agrupando por loja destino.

        Args:
            codigo: Codigo do produto
            demandas_por_loja: Dicionario cod_empresa -> demanda_periodo
            lead_time_destino: Lead time base (da loja destino)
            cod_empresa_destino: Forcar destino especifico (opcional)

        Returns:
            Dicionario cod_empresa_destino -> PedidoCentralizado
        """
        # Agrupar demandas por loja destino
        demandas_por_destino: Dict[int, List[Tuple[int, float]]] = {}

        for cod_empresa_venda, demanda in demandas_por_loja.items():
            if cod_empresa_destino is not None:
                destino = cod_empresa_destino
            else:
                destino = self.get_padrao_compra(codigo, cod_empresa_venda)

            if destino not in demandas_por_destino:
                demandas_por_destino[destino] = []
            demandas_por_destino[destino].append((cod_empresa_venda, demanda))

        # Calcular pedido para cada destino
        pedidos = {}
        for destino, lojas_demandas in demandas_por_destino.items():
            lojas_origem = []
            quantidade_total = 0

            for cod_empresa_venda, demanda in lojas_demandas:
                necessidade = self.calcular_necessidade_loja(codigo, cod_empresa_venda, demanda)
                lojas_origem.append(necessidade)
                quantidade_total += necessidade.necessidade

            # Buscar CUE da loja destino
            estoque_destino = self.get_estoque(codigo, destino)
            cue_destino = estoque_destino['cue']

            # Calcular lead time efetivo
            # Se alguma loja de origem != destino, adicionar dias de transferencia
            tem_transferencia = any(lo.cod_empresa_venda != destino for lo in lojas_origem)
            if tem_transferencia:
                lead_time_efetivo = lead_time_destino + self.dias_transferencia
            else:
                lead_time_efetivo = lead_time_destino

            # Verificar criticas (itens sem padrao)
            criticas = []
            for lo in lojas_origem:
                padrao_definido = self._cache_padroes.get((codigo, lo.cod_empresa_venda)) if self._cache_padroes else None
                if padrao_definido is None:
                    padrao_banco = buscar_padrao_compra_item(self.conn, codigo, lo.cod_empresa_venda)
                    if padrao_banco is None:
                        criticas.append({
                            'tipo': 'SEM_PADRAO_COMPRA',
                            'codigo': codigo,
                            'cod_empresa': lo.cod_empresa_venda,
                            'mensagem': f'Item {codigo} loja {lo.cod_empresa_venda} sem padrao de compra definido'
                        })

            pedidos[destino] = PedidoCentralizado(
                cod_empresa_destino=destino,
                codigo=codigo,
                quantidade_total=quantidade_total,
                lead_time_efetivo=lead_time_efetivo,
                lojas_origem=lojas_origem,
                valor_total=quantidade_total * cue_destino,
                cue_destino=cue_destino,
                tem_criticas=len(criticas) > 0,
                criticas=criticas
            )

        return pedidos

    def processar_itens_com_padrao(
        self,
        itens_processados: List[Dict],
        lead_times: Dict[int, int] = None
    ) -> Dict:
        """
        Processa lista de itens aplicando logica de padrao de compra.

        Esta funcao recebe os itens ja calculados pelo PedidoFornecedorIntegrado
        e reagrupa por loja destino considerando o padrao de compra.

        Args:
            itens_processados: Lista de itens com demanda calculada
            lead_times: Dicionario cod_empresa -> lead_time (opcional)

        Returns:
            Dicionario com pedidos agrupados por destino
        """
        if not itens_processados:
            return {
                'sucesso': False,
                'mensagem': 'Nenhum item para processar',
                'pedidos_por_destino': {},
                'criticas': []
            }

        # Coletar codigos e empresas unicos
        codigos = list(set(item.get('codigo') for item in itens_processados if item.get('codigo')))
        empresas = list(set(item.get('cod_empresa') for item in itens_processados if item.get('cod_empresa')))

        # Pre-carregar dados
        if self._cache_padroes is None:
            self.precarregar_padroes(codigos, empresas)
        if self._cache_estoque is None:
            self.precarregar_estoque(codigos, empresas)

        # Agrupar itens por codigo
        itens_por_codigo: Dict[int, List[Dict]] = {}
        for item in itens_processados:
            codigo = item.get('codigo')
            if codigo:
                if codigo not in itens_por_codigo:
                    itens_por_codigo[codigo] = []
                itens_por_codigo[codigo].append(item)

        # Processar cada codigo
        pedidos_por_destino: Dict[int, List[Dict]] = {}
        todas_criticas = []

        for codigo, itens in itens_por_codigo.items():
            # Montar demandas por loja
            demandas_por_loja = {}
            for item in itens:
                cod_empresa = item.get('cod_empresa')
                demanda = item.get('demanda_prevista', 0)
                if cod_empresa:
                    demandas_por_loja[cod_empresa] = demanda

            # Obter lead time (usar do primeiro item ou padrao)
            lead_time = lead_times.get(itens[0].get('cod_empresa'), 15) if lead_times else 15

            # Calcular pedidos
            pedidos = self.calcular_pedido_item(codigo, demandas_por_loja, lead_time)

            for destino, pedido in pedidos.items():
                if destino not in pedidos_por_destino:
                    pedidos_por_destino[destino] = []

                # Montar item do pedido
                item_pedido = {
                    'codigo': codigo,
                    'descricao': itens[0].get('descricao', ''),
                    'categoria': itens[0].get('categoria', ''),
                    'cod_empresa_destino': destino,
                    'quantidade_pedido': pedido.quantidade_total,
                    'lead_time_efetivo': pedido.lead_time_efetivo,
                    'cue': pedido.cue_destino,
                    'valor_pedido': pedido.valor_total,
                    'lojas_origem': [
                        {
                            'cod_empresa': lo.cod_empresa_venda,
                            'demanda': lo.demanda_periodo,
                            'estoque': lo.estoque_efetivo,
                            'necessidade': lo.necessidade,
                            'contribui': lo.contribui_pedido
                        }
                        for lo in pedido.lojas_origem
                    ],
                    'tem_criticas': pedido.tem_criticas,
                    'criticas': pedido.criticas,
                    # Manter dados originais para referencia
                    'codigo_fornecedor': itens[0].get('codigo_fornecedor', ''),
                    'nome_fornecedor': itens[0].get('nome_fornecedor', ''),
                    'curva_abc': itens[0].get('curva_abc', 'B')
                }

                pedidos_por_destino[destino].append(item_pedido)
                todas_criticas.extend(pedido.criticas)

        return {
            'sucesso': True,
            'mensagem': f'Processados {len(itens_processados)} itens para {len(pedidos_por_destino)} destinos',
            'pedidos_por_destino': pedidos_por_destino,
            'total_destinos': len(pedidos_por_destino),
            'total_itens': sum(len(itens) for itens in pedidos_por_destino.values()),
            'criticas': todas_criticas,
            'total_criticas': len(todas_criticas),
            'dias_transferencia': self.dias_transferencia
        }


# ============================================================================
# FUNCOES DE CONVENIENCIA
# ============================================================================

def agregar_pedidos_por_destino_fornecedor(pedidos_por_destino: Dict[int, List[Dict]]) -> Dict:
    """
    Agrega pedidos por destino e depois por fornecedor.

    Estrutura final:
    - Nivel 1: Fornecedor (codigo_fornecedor)
    - Nivel 2: Loja destino (cod_empresa_destino)
    - Nivel 3: Itens

    Args:
        pedidos_por_destino: Dicionario cod_empresa_destino -> lista de itens

    Returns:
        Dicionario com agregacao hierarquica
    """
    agregado = {}

    for destino, itens in pedidos_por_destino.items():
        for item in itens:
            cnpj_fornecedor = item.get('codigo_fornecedor', 'SEM_FORNECEDOR')
            nome_fornecedor = item.get('nome_fornecedor', 'Sem Fornecedor')

            if cnpj_fornecedor not in agregado:
                agregado[cnpj_fornecedor] = {
                    'codigo_fornecedor': cnpj_fornecedor,
                    'nome_fornecedor': nome_fornecedor,
                    'destinos': {},
                    'total_valor': 0,
                    'total_itens': 0
                }

            if destino not in agregado[cnpj_fornecedor]['destinos']:
                agregado[cnpj_fornecedor]['destinos'][destino] = {
                    'cod_empresa_destino': destino,
                    'itens': [],
                    'total_valor': 0,
                    'total_itens': 0
                }

            agregado[cnpj_fornecedor]['destinos'][destino]['itens'].append(item)
            agregado[cnpj_fornecedor]['destinos'][destino]['total_valor'] += item.get('valor_pedido', 0)
            agregado[cnpj_fornecedor]['destinos'][destino]['total_itens'] += 1

            agregado[cnpj_fornecedor]['total_valor'] += item.get('valor_pedido', 0)
            agregado[cnpj_fornecedor]['total_itens'] += 1

    # Converter destinos de dict para list para facilitar iteracao
    for cnpj in agregado:
        agregado[cnpj]['destinos'] = list(agregado[cnpj]['destinos'].values())

    return {
        'fornecedores': list(agregado.values()),
        'total_fornecedores': len(agregado),
        'total_destinos': sum(len(f['destinos']) for f in agregado.values()),
        'total_itens': sum(f['total_itens'] for f in agregado.values()),
        'valor_total': sum(f['total_valor'] for f in agregado.values())
    }


def formatar_pedido_para_excel(pedidos_por_destino: Dict[int, List[Dict]]) -> List[Dict]:
    """
    Formata pedidos para exportacao Excel (item x filial destino por linha).

    Args:
        pedidos_por_destino: Dicionario cod_empresa_destino -> lista de itens

    Returns:
        Lista de dicionarios com uma linha por item x destino
    """
    linhas = []

    for destino, itens in pedidos_por_destino.items():
        for item in itens:
            linha = {
                'codigo': item.get('codigo'),
                'descricao': item.get('descricao', ''),
                'categoria': item.get('categoria', ''),
                'curva_abc': item.get('curva_abc', 'B'),
                'codigo_fornecedor': item.get('codigo_fornecedor', ''),
                'nome_fornecedor': item.get('nome_fornecedor', ''),
                'cod_empresa_destino': destino,
                'quantidade_pedido': item.get('quantidade_pedido', 0),
                'cue': item.get('cue', 0),
                'valor_pedido': item.get('valor_pedido', 0),
                'lead_time_efetivo': item.get('lead_time_efetivo', 0),
                'lojas_origem': ', '.join([
                    f"{lo['cod_empresa']}({lo['necessidade']:.0f})"
                    for lo in item.get('lojas_origem', [])
                    if lo.get('contribui')
                ]),
                'criticas': '; '.join([c['mensagem'] for c in item.get('criticas', [])])
            }
            linhas.append(linha)

    return linhas
