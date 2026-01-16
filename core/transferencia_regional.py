# -*- coding: utf-8 -*-
"""
Modulo de Transferencia Regional entre Lojas
============================================
Calcula oportunidades de transferencia entre lojas do mesmo grupo regional,
identificando lojas com excesso de estoque que podem abastecer lojas em falta.

IMPORTANTE: Este modulo NAO modifica logicas existentes de pedido.
            Apenas adiciona funcionalidade de identificacao de oportunidades.

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal


class TransferenciaRegional:
    """
    Classe para calculo de oportunidades de transferencia regional.

    Identifica desbalanceamentos de estoque entre lojas do mesmo grupo
    e sugere transferencias para otimizar a distribuicao.
    """

    # Parametros de configuracao
    COBERTURA_MINIMA_DOADOR = 10  # Dias minimos que doador deve manter apos doacao
    MARGEM_EXCESSO_DIAS = 7      # Dias acima da cobertura alvo para considerar excesso
    COBERTURA_ALVO_PADRAO = 21   # Cobertura alvo padrao (dias)

    def __init__(self, conn):
        """
        Inicializa o calculador de transferencias.

        Args:
            conn: Conexao com banco de dados PostgreSQL
        """
        self.conn = conn
        self._cache_grupos = None
        self._cache_lojas_grupo = {}

    def _get_grupos_transferencia(self) -> List[Dict]:
        """Retorna lista de grupos de transferencia ativos."""
        if self._cache_grupos is not None:
            return self._cache_grupos

        cur = self.conn.cursor()
        cur.execute("""
            SELECT id, nome, descricao, cd_principal
            FROM grupos_transferencia
            WHERE ativo = TRUE
        """)
        self._cache_grupos = [
            {'id': r[0], 'nome': r[1], 'descricao': r[2], 'cd_principal': r[3]}
            for r in cur.fetchall()
        ]
        cur.close()
        return self._cache_grupos

    def _get_lojas_grupo(self, grupo_id: int) -> List[Dict]:
        """Retorna lista de lojas de um grupo."""
        if grupo_id in self._cache_lojas_grupo:
            return self._cache_lojas_grupo[grupo_id]

        cur = self.conn.cursor()
        cur.execute("""
            SELECT cod_empresa, nome_loja, pode_doar, pode_receber, prioridade_recebimento
            FROM lojas_grupo_transferencia
            WHERE grupo_id = %s AND ativo = TRUE
            ORDER BY cod_empresa
        """, (grupo_id,))
        lojas = [
            {
                'cod_empresa': r[0],
                'nome_loja': r[1],
                'pode_doar': r[2],
                'pode_receber': r[3],
                'prioridade': r[4]
            }
            for r in cur.fetchall()
        ]
        cur.close()
        self._cache_lojas_grupo[grupo_id] = lojas
        return lojas

    def _get_grupo_por_cd(self, cd_principal: int) -> Optional[Dict]:
        """Retorna grupo pelo codigo do CD."""
        grupos = self._get_grupos_transferencia()
        for g in grupos:
            if g['cd_principal'] == cd_principal:
                return g
        return None

    def _calcular_urgencia(self, cobertura_dias: float) -> str:
        """
        Calcula nivel de urgencia baseado na cobertura.

        Returns:
            'CRITICA': Ruptura atual (estoque = 0)
            'ALTA': Ruptura em ate 3 dias
            'MEDIA': Ruptura em ate 7 dias
            'BAIXA': Preventivo
        """
        if cobertura_dias <= 0:
            return 'CRITICA'
        elif cobertura_dias < 3:
            return 'ALTA'
        elif cobertura_dias < 7:
            return 'MEDIA'
        else:
            return 'BAIXA'

    def consolidar_posicao_item(
        self,
        cod_produto: int,
        grupo_id: int,
        cd_principal: int
    ) -> Dict:
        """
        Consolida posicao de estoque de um item em todas as lojas do grupo + CD.

        Args:
            cod_produto: Codigo do produto
            grupo_id: ID do grupo de transferencia
            cd_principal: Codigo do CD do grupo

        Returns:
            Dict com posicao consolidada do CD e de cada loja
        """
        lojas = self._get_lojas_grupo(grupo_id)
        cod_lojas = [l['cod_empresa'] for l in lojas]

        cur = self.conn.cursor()

        # Buscar estoque do CD
        cur.execute("""
            SELECT
                COALESCE(estoque, 0) as estoque,
                COALESCE(qtd_pendente, 0) as pedido_pendente,
                COALESCE(qtd_pend_transf, 0) as transito,
                COALESCE(cue, 0) as cue
            FROM estoque_posicao_atual
            WHERE codigo = %s AND cod_empresa = %s
        """, (cod_produto, cd_principal))
        row_cd = cur.fetchone()

        posicao_cd = {
            'cod_empresa': cd_principal,
            'estoque': float(row_cd[0]) if row_cd else 0,
            'pedido_pendente': float(row_cd[1]) if row_cd else 0,
            'transito': float(row_cd[2]) if row_cd else 0,
            'cue': float(row_cd[3]) if row_cd else 0
        }
        posicao_cd['estoque_efetivo'] = (
            posicao_cd['estoque'] +
            posicao_cd['transito'] +
            posicao_cd['pedido_pendente']
        )

        # Buscar estoque das lojas
        if cod_lojas:
            placeholders = ','.join(['%s'] * len(cod_lojas))
            cur.execute(f"""
                SELECT
                    cod_empresa,
                    COALESCE(estoque, 0) as estoque,
                    COALESCE(qtd_pendente, 0) as pedido_pendente,
                    COALESCE(qtd_pend_transf, 0) as transito,
                    COALESCE(cue, 0) as cue
                FROM estoque_posicao_atual
                WHERE codigo = %s AND cod_empresa IN ({placeholders})
            """, [cod_produto] + cod_lojas)
            rows_lojas = cur.fetchall()
        else:
            rows_lojas = []

        # Montar dicionario de lojas
        estoque_por_loja = {r[0]: {
            'estoque': float(r[1]),
            'pedido_pendente': float(r[2]),
            'transito': float(r[3]),
            'cue': float(r[4])
        } for r in rows_lojas}

        # Completar com lojas que nao tem registro (estoque zero)
        posicao_lojas = []
        for loja in lojas:
            cod = loja['cod_empresa']
            est = estoque_por_loja.get(cod, {
                'estoque': 0, 'pedido_pendente': 0, 'transito': 0, 'cue': 0
            })
            est['cod_empresa'] = cod
            est['nome_loja'] = loja['nome_loja']
            est['pode_doar'] = loja['pode_doar']
            est['pode_receber'] = loja['pode_receber']
            est['prioridade'] = loja['prioridade']
            est['estoque_efetivo'] = (
                est['estoque'] + est['transito'] + est['pedido_pendente']
            )
            posicao_lojas.append(est)

        cur.close()

        # CUE: usar o maior valor encontrado
        cue = posicao_cd['cue']
        for p in posicao_lojas:
            if p['cue'] > cue:
                cue = p['cue']

        return {
            'cod_produto': cod_produto,
            'posicao_cd': posicao_cd,
            'posicao_lojas': posicao_lojas,
            'cue': cue,
            'estoque_total': (
                posicao_cd['estoque_efetivo'] +
                sum(p['estoque_efetivo'] for p in posicao_lojas)
            )
        }

    def analisar_desbalanceamento(
        self,
        posicao: Dict,
        demanda_por_loja: Dict[int, float],
        cobertura_alvo: int = None
    ) -> Dict:
        """
        Analisa desbalanceamento de estoque entre lojas.

        Args:
            posicao: Resultado de consolidar_posicao_item
            demanda_por_loja: Dict {cod_empresa: demanda_diaria}
            cobertura_alvo: Cobertura alvo em dias (default: COBERTURA_ALVO_PADRAO)

        Returns:
            Dict com analise de cada loja (excesso, falta, ok)
        """
        if cobertura_alvo is None:
            cobertura_alvo = self.COBERTURA_ALVO_PADRAO

        analise_lojas = []

        for loja in posicao['posicao_lojas']:
            cod = loja['cod_empresa']
            demanda = demanda_por_loja.get(cod, 0)

            # Calcular cobertura
            if demanda > 0:
                cobertura_dias = loja['estoque_efetivo'] / demanda
            else:
                cobertura_dias = 999 if loja['estoque_efetivo'] > 0 else 0

            # Determinar status
            if cobertura_dias > cobertura_alvo + self.MARGEM_EXCESSO_DIAS:
                status = 'EXCESSO'
                excesso_dias = cobertura_dias - cobertura_alvo
                excesso_unidades = int(excesso_dias * demanda) if demanda > 0 else 0
                necessidade_unidades = 0
            elif cobertura_dias < self.COBERTURA_MINIMA_DOADOR:
                status = 'FALTA'
                excesso_dias = 0
                excesso_unidades = 0
                falta_dias = cobertura_alvo - cobertura_dias
                necessidade_unidades = int(falta_dias * demanda) if demanda > 0 else 0
            else:
                status = 'OK'
                excesso_dias = 0
                excesso_unidades = 0
                necessidade_unidades = 0

            analise_lojas.append({
                **loja,
                'demanda_diaria': demanda,
                'cobertura_dias': round(cobertura_dias, 1),
                'status': status,
                'excesso_unidades': excesso_unidades,
                'necessidade_unidades': necessidade_unidades,
                'urgencia': self._calcular_urgencia(cobertura_dias) if status == 'FALTA' else None
            })

        # Ordenar: FALTA primeiro (por urgencia), depois EXCESSO
        prioridade_status = {'FALTA': 1, 'EXCESSO': 2, 'OK': 3}
        prioridade_urgencia = {'CRITICA': 1, 'ALTA': 2, 'MEDIA': 3, 'BAIXA': 4, None: 5}
        analise_lojas.sort(key=lambda x: (
            prioridade_status.get(x['status'], 3),
            prioridade_urgencia.get(x['urgencia'], 5),
            -x.get('necessidade_unidades', 0)
        ))

        return {
            'cod_produto': posicao['cod_produto'],
            'analise_lojas': analise_lojas,
            'lojas_excesso': [l for l in analise_lojas if l['status'] == 'EXCESSO'],
            'lojas_falta': [l for l in analise_lojas if l['status'] == 'FALTA'],
            'lojas_ok': [l for l in analise_lojas if l['status'] == 'OK'],
            'tem_desbalanceamento': any(l['status'] in ('EXCESSO', 'FALTA') for l in analise_lojas)
        }

    def calcular_transferencias(
        self,
        posicao: Dict,
        analise: Dict,
        cobertura_alvo: int = None
    ) -> List[Dict]:
        """
        Calcula transferencias sugeridas entre lojas.

        Args:
            posicao: Resultado de consolidar_posicao_item
            analise: Resultado de analisar_desbalanceamento
            cobertura_alvo: Cobertura alvo em dias

        Returns:
            Lista de transferencias sugeridas
        """
        if cobertura_alvo is None:
            cobertura_alvo = self.COBERTURA_ALVO_PADRAO

        transferencias = []
        lojas_excesso = [l for l in analise['lojas_excesso'] if l['pode_doar']]
        lojas_falta = [l for l in analise['lojas_falta'] if l['pode_receber']]

        if not lojas_excesso or not lojas_falta:
            return []

        # Para cada loja em falta, buscar doadores
        for destino in lojas_falta:
            necessidade = destino['necessidade_unidades']
            if necessidade <= 0:
                continue

            # Buscar doadores com excesso
            for origem in lojas_excesso:
                if origem['excesso_unidades'] <= 0:
                    continue

                # Calcular quantidade a transferir
                # Nao pode deixar origem abaixo da cobertura minima
                estoque_minimo_origem = (
                    origem['demanda_diaria'] * self.COBERTURA_MINIMA_DOADOR
                    if origem['demanda_diaria'] > 0 else 0
                )
                disponivel_origem = max(0, origem['estoque_efetivo'] - estoque_minimo_origem)

                qtd_transferir = min(
                    necessidade,
                    origem['excesso_unidades'],
                    int(disponivel_origem)
                )

                if qtd_transferir <= 0:
                    continue

                # Criar registro de transferencia
                transferencias.append({
                    'cod_produto': posicao['cod_produto'],
                    'loja_origem': origem['cod_empresa'],
                    'nome_loja_origem': origem['nome_loja'],
                    'estoque_origem': int(origem['estoque']),
                    'transito_origem': int(origem['transito']),
                    'demanda_diaria_origem': origem['demanda_diaria'],
                    'cobertura_origem_dias': origem['cobertura_dias'],
                    'excesso_unidades': origem['excesso_unidades'],

                    'loja_destino': destino['cod_empresa'],
                    'nome_loja_destino': destino['nome_loja'],
                    'estoque_destino': int(destino['estoque']),
                    'transito_destino': int(destino['transito']),
                    'demanda_diaria_destino': destino['demanda_diaria'],
                    'cobertura_destino_dias': destino['cobertura_dias'],
                    'necessidade_unidades': destino['necessidade_unidades'],

                    'qtd_sugerida': qtd_transferir,
                    'valor_estimado': round(qtd_transferir * posicao['cue'], 2),
                    'cue': posicao['cue'],
                    'urgencia': destino['urgencia']
                })

                # Atualizar controles
                necessidade -= qtd_transferir
                origem['excesso_unidades'] -= qtd_transferir

                if necessidade <= 0:
                    break

        return transferencias

    def salvar_oportunidades(
        self,
        transferencias: List[Dict],
        grupo_id: int,
        sessao_pedido: str,
        descricao_produto: str = None,
        curva_abc: str = None
    ) -> int:
        """
        Salva oportunidades de transferencia no banco.

        Args:
            transferencias: Lista de transferencias calculadas
            grupo_id: ID do grupo de transferencia
            sessao_pedido: Identificador da sessao do pedido
            descricao_produto: Descricao do produto
            curva_abc: Curva ABC do produto

        Returns:
            Numero de registros salvos
        """
        if not transferencias:
            return 0

        cur = self.conn.cursor()
        salvos = 0

        for t in transferencias:
            try:
                cur.execute("""
                    INSERT INTO oportunidades_transferencia (
                        sessao_pedido, grupo_id,
                        cod_produto, descricao_produto, curva_abc,
                        loja_origem, nome_loja_origem, estoque_origem, transito_origem,
                        demanda_diaria_origem, cobertura_origem_dias, excesso_unidades,
                        loja_destino, nome_loja_destino, estoque_destino, transito_destino,
                        demanda_diaria_destino, cobertura_destino_dias, necessidade_unidades,
                        qtd_sugerida, valor_estimado, cue, urgencia
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (sessao_pedido, cod_produto, loja_origem, loja_destino)
                    DO UPDATE SET
                        qtd_sugerida = EXCLUDED.qtd_sugerida,
                        valor_estimado = EXCLUDED.valor_estimado,
                        urgencia = EXCLUDED.urgencia,
                        data_calculo = NOW()
                """, (
                    sessao_pedido, grupo_id,
                    t['cod_produto'], descricao_produto, curva_abc,
                    t['loja_origem'], t['nome_loja_origem'], t['estoque_origem'], t['transito_origem'],
                    t['demanda_diaria_origem'], t['cobertura_origem_dias'], t['excesso_unidades'],
                    t['loja_destino'], t['nome_loja_destino'], t['estoque_destino'], t['transito_destino'],
                    t['demanda_diaria_destino'], t['cobertura_destino_dias'], t['necessidade_unidades'],
                    t['qtd_sugerida'], t['valor_estimado'], t['cue'], t['urgencia']
                ))
                salvos += 1
            except Exception as e:
                print(f"Erro ao salvar oportunidade: {e}")

        self.conn.commit()
        cur.close()
        return salvos

    def gerar_sessao_pedido(self) -> str:
        """Gera identificador unico para sessao de pedido."""
        return f"PED_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def limpar_sessao_antiga(self, sessao_pedido: str) -> int:
        """Remove oportunidades de uma sessao anterior."""
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM oportunidades_transferencia WHERE sessao_pedido = %s",
            (sessao_pedido,)
        )
        deletados = cur.rowcount
        self.conn.commit()
        cur.close()
        return deletados

    def buscar_oportunidades_recentes(
        self,
        grupo_id: int = None,
        limite_horas: int = 24
    ) -> List[Dict]:
        """
        Busca oportunidades de transferencia recentes.

        Args:
            grupo_id: Filtrar por grupo (None = todos)
            limite_horas: Buscar oportunidades das ultimas X horas

        Returns:
            Lista de oportunidades
        """
        cur = self.conn.cursor()

        query = """
            SELECT
                ot.id, ot.data_calculo, ot.sessao_pedido,
                gt.nome as grupo_nome, gt.cd_principal,
                ot.cod_produto, ot.descricao_produto, ot.curva_abc,
                ot.loja_origem, ot.nome_loja_origem, ot.estoque_origem,
                ot.cobertura_origem_dias,
                ot.loja_destino, ot.nome_loja_destino, ot.estoque_destino,
                ot.cobertura_destino_dias,
                ot.qtd_sugerida, ot.valor_estimado, ot.urgencia, ot.status
            FROM oportunidades_transferencia ot
            JOIN grupos_transferencia gt ON ot.grupo_id = gt.id
            WHERE ot.data_calculo >= NOW() - INTERVAL '%s hours'
        """
        params = [limite_horas]

        if grupo_id:
            query += " AND ot.grupo_id = %s"
            params.append(grupo_id)

        query += " ORDER BY ot.data_calculo DESC, ot.urgencia, ot.valor_estimado DESC"

        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()

        # Mapear urgencia para ordenacao
        prioridade_urgencia = {'CRITICA': 1, 'ALTA': 2, 'MEDIA': 3, 'BAIXA': 4}

        oportunidades = []
        for r in rows:
            oportunidades.append({
                'id': r[0],
                'data_calculo': r[1].isoformat() if r[1] else None,
                'sessao_pedido': r[2],
                'grupo_nome': r[3],
                'cd_principal': r[4],
                'cod_produto': r[5],
                'descricao_produto': r[6],
                'curva_abc': r[7],
                'loja_origem': r[8],
                'nome_loja_origem': r[9],
                'estoque_origem': r[10],
                'cobertura_origem_dias': float(r[11]) if r[11] else 0,
                'loja_destino': r[12],
                'nome_loja_destino': r[13],
                'estoque_destino': r[14],
                'cobertura_destino_dias': float(r[15]) if r[15] else 0,
                'qtd_sugerida': r[16],
                'valor_estimado': float(r[17]) if r[17] else 0,
                'urgencia': r[18],
                'status': r[19],
                'urgencia_ordem': prioridade_urgencia.get(r[18], 5)
            })

        # Ordenar por urgencia
        oportunidades.sort(key=lambda x: (x['urgencia_ordem'], -x['valor_estimado']))

        return oportunidades

    def resumo_oportunidades(self, oportunidades: List[Dict]) -> Dict:
        """
        Gera resumo das oportunidades de transferencia.

        Args:
            oportunidades: Lista de oportunidades

        Returns:
            Dict com estatisticas
        """
        if not oportunidades:
            return {
                'total': 0,
                'criticas': 0,
                'altas': 0,
                'medias': 0,
                'baixas': 0,
                'valor_total': 0,
                'produtos_unicos': 0
            }

        return {
            'total': len(oportunidades),
            'criticas': sum(1 for o in oportunidades if o['urgencia'] == 'CRITICA'),
            'altas': sum(1 for o in oportunidades if o['urgencia'] == 'ALTA'),
            'medias': sum(1 for o in oportunidades if o['urgencia'] == 'MEDIA'),
            'baixas': sum(1 for o in oportunidades if o['urgencia'] == 'BAIXA'),
            'valor_total': sum(o['valor_estimado'] for o in oportunidades),
            'produtos_unicos': len(set(o['cod_produto'] for o in oportunidades))
        }
