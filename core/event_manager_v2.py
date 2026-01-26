"""
Modulo de Gerenciamento de Eventos V2
=====================================

Sistema completo para cadastro e aplicacao de eventos que impactam a demanda.

Funcionalidades:
1. Cadastro por item, fornecedor, linha1, linha3, filial
2. Vigencia com data inicio/fim
3. Impacto positivo (+%) ou negativo (-%)
4. Eventos recorrentes anuais
5. Conflito de eventos: multiplicacao (Opcao C)
6. Historico de eventos expirados
7. Importacao em massa via Excel/CSV
8. Auditoria de alteracoes
9. Alertas de eventos proximos/expirados

Autor: Sistema de Previsao de Demanda
Data: Janeiro 2026
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple, Union
import os
import json


class EventManagerV2:
    """
    Gerenciador de Eventos V2 - Sistema completo de gestao de eventos
    """

    # Tipos de eventos
    TIPOS_EVENTO = {
        'PROMOCAO': {'nome': 'Promocao', 'icone': '🏷️', 'cor': '#28a745'},
        'SAZONAL': {'nome': 'Sazonal', 'icone': '📅', 'cor': '#17a2b8'},
        'REDUCAO': {'nome': 'Reducao', 'icone': '📉', 'cor': '#dc3545'},
        'CAMPANHA': {'nome': 'Campanha', 'icone': '📢', 'cor': '#ffc107'},
        'FERIADO': {'nome': 'Feriado', 'icone': '🎉', 'cor': '#6f42c1'},
        'CUSTOM': {'nome': 'Customizado', 'icone': '⚙️', 'cor': '#6c757d'}
    }

    # Status possiveis
    STATUS = {
        'ATIVO': 'Evento ativo, influenciando calculos',
        'EXPIRADO': 'Vigencia encerrada, apenas historico',
        'CANCELADO': 'Cancelado manualmente pelo usuario',
        'PENDENTE': 'Aguardando inicio da vigencia'
    }

    def __init__(self, db_path: str = 'outputs/events_v2.db'):
        """
        Inicializa o gerenciador de eventos V2

        Args:
            db_path: Caminho do banco SQLite
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Cria estrutura do banco de dados"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabela principal de eventos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Identificacao
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL DEFAULT 'CUSTOM',
                descricao TEXT,

                -- Impacto (positivo = aumento, negativo = reducao)
                impacto_percentual REAL NOT NULL,

                -- Vigencia
                data_inicio DATE NOT NULL,
                data_fim DATE NOT NULL,

                -- Recorrencia
                recorrente_anual INTEGER DEFAULT 0,

                -- Status
                status TEXT DEFAULT 'ATIVO',

                -- Auditoria
                criado_por TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_por TEXT,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabela de filtros do evento (relacionamento N:N)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evento_filtros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL,

                -- Filtros (NULL = aplica a todos)
                codigo_item INTEGER,
                cod_fornecedor INTEGER,
                linha1 TEXT,
                linha3 TEXT,
                cod_empresa INTEGER,

                -- Auditoria
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
            )
        ''')

        # Tabela de historico/auditoria
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evento_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL,
                acao TEXT NOT NULL,
                dados_anteriores TEXT,
                dados_novos TEXT,
                usuario TEXT,
                data_acao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
            )
        ''')

        # Tabela para analise de acuracia
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evento_acuracia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL,
                codigo_item INTEGER,
                cod_empresa INTEGER,
                demanda_prevista REAL,
                demanda_real REAL,
                impacto_previsto REAL,
                impacto_real REAL,
                data_calculo DATE,

                FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
            )
        ''')

        # Indices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_eventos_status ON eventos(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_eventos_vigencia ON eventos(data_inicio, data_fim)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filtros_evento ON evento_filtros(evento_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filtros_item ON evento_filtros(codigo_item)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filtros_fornecedor ON evento_filtros(cod_fornecedor)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_filtros_empresa ON evento_filtros(cod_empresa)')

        conn.commit()
        conn.close()

    # ==========================================================================
    # CADASTRO DE EVENTOS
    # ==========================================================================

    def cadastrar_evento(
        self,
        nome: str,
        impacto_percentual: float,
        data_inicio: str,
        data_fim: str,
        tipo: str = 'CUSTOM',
        descricao: str = None,
        recorrente_anual: bool = False,
        filtros: List[Dict] = None,
        usuario: str = None
    ) -> int:
        """
        Cadastra um novo evento

        Args:
            nome: Nome do evento
            impacto_percentual: Impacto em % (positivo=aumento, negativo=reducao)
            data_inicio: Data inicio da vigencia (YYYY-MM-DD)
            data_fim: Data fim da vigencia (YYYY-MM-DD)
            tipo: Tipo do evento (PROMOCAO, SAZONAL, REDUCAO, etc)
            descricao: Descricao detalhada
            recorrente_anual: Se True, replica para proximos anos
            filtros: Lista de filtros, cada um com:
                     {codigo_item, cod_fornecedor, linha1, linha3, cod_empresa}
                     Se None ou vazio, aplica a todos
            usuario: Usuario que esta cadastrando

        Returns:
            ID do evento cadastrado
        """
        if tipo not in self.TIPOS_EVENTO:
            tipo = 'CUSTOM'

        # Validar datas
        dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()

        if dt_fim < dt_inicio:
            raise ValueError("Data fim deve ser maior ou igual a data inicio")

        # Status inicial sempre ATIVO
        # O evento é válido enquanto não for CANCELADO
        # A aplicação depende apenas das datas de vigência
        hoje = datetime.now().date()
        if dt_fim < hoje:
            status = 'EXPIRADO'  # Já passou
        else:
            status = 'ATIVO'  # Válido (presente ou futuro)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Inserir evento
            cursor.execute('''
                INSERT INTO eventos (
                    nome, tipo, descricao, impacto_percentual,
                    data_inicio, data_fim, recorrente_anual, status,
                    criado_por, atualizado_por
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                nome, tipo, descricao, impacto_percentual,
                data_inicio, data_fim, 1 if recorrente_anual else 0, status,
                usuario, usuario
            ))

            evento_id = cursor.lastrowid

            # Inserir filtros
            if filtros:
                for filtro in filtros:
                    cursor.execute('''
                        INSERT INTO evento_filtros (
                            evento_id, codigo_item, cod_fornecedor,
                            linha1, linha3, cod_empresa
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        evento_id,
                        filtro.get('codigo_item'),
                        filtro.get('cod_fornecedor'),
                        filtro.get('linha1'),
                        filtro.get('linha3'),
                        filtro.get('cod_empresa')
                    ))

            # Registrar no historico
            self._registrar_historico(
                cursor, evento_id, 'CRIADO',
                None, {'nome': nome, 'impacto': impacto_percentual},
                usuario
            )

            conn.commit()
            return evento_id

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def cadastrar_evento_item(
        self,
        codigo_item: int,
        cod_empresa: int,
        nome: str,
        impacto_percentual: float,
        data_inicio: str,
        data_fim: str,
        cod_fornecedor: int = None,
        linha1: str = None,
        linha3: str = None,
        tipo: str = 'PROMOCAO',
        descricao: str = None,
        recorrente_anual: bool = False,
        usuario: str = None
    ) -> int:
        """
        Cadastra evento para item especifico (atalho para cadastro simplificado)

        Formato: item x filial x vigencia x nome x impacto x fornecedor x linha1 x linha3

        Args:
            codigo_item: Codigo do item
            cod_empresa: Codigo da filial/empresa
            nome: Nome do evento
            impacto_percentual: Impacto em %
            data_inicio: Data inicio (YYYY-MM-DD)
            data_fim: Data fim (YYYY-MM-DD)
            cod_fornecedor: Codigo do fornecedor (opcional)
            linha1: Linha 1 (opcional)
            linha3: Linha 3 (opcional)
            tipo: Tipo do evento
            descricao: Descricao
            recorrente_anual: Se recorrente
            usuario: Usuario

        Returns:
            ID do evento
        """
        filtros = [{
            'codigo_item': codigo_item,
            'cod_empresa': cod_empresa,
            'cod_fornecedor': cod_fornecedor,
            'linha1': linha1,
            'linha3': linha3
        }]

        return self.cadastrar_evento(
            nome=nome,
            impacto_percentual=impacto_percentual,
            data_inicio=data_inicio,
            data_fim=data_fim,
            tipo=tipo,
            descricao=descricao,
            recorrente_anual=recorrente_anual,
            filtros=filtros,
            usuario=usuario
        )

    # ==========================================================================
    # CONSULTA DE EVENTOS
    # ==========================================================================

    def listar_eventos(
        self,
        status: str = None,
        incluir_expirados: bool = True,
        data_referencia: str = None
    ) -> List[Dict]:
        """
        Lista eventos cadastrados

        Args:
            status: Filtrar por status (ATIVO, EXPIRADO, CANCELADO)
            incluir_expirados: Se False, exclui eventos expirados
            data_referencia: Data para verificar vigencia (YYYY-MM-DD)

        Returns:
            Lista de eventos com seus filtros
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM eventos WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        elif not incluir_expirados:
            query += " AND status != 'EXPIRADO'"

        query += " ORDER BY data_inicio DESC, nome"

        cursor = conn.cursor()
        cursor.execute(query, params)
        eventos_raw = cursor.fetchall()

        eventos = []
        for row in eventos_raw:
            evento = dict(row)

            # Buscar filtros do evento
            cursor.execute('''
                SELECT * FROM evento_filtros WHERE evento_id = ?
            ''', (evento['id'],))
            filtros = [dict(f) for f in cursor.fetchall()]
            evento['filtros'] = filtros

            # Adicionar info do tipo
            tipo_info = self.TIPOS_EVENTO.get(evento['tipo'], self.TIPOS_EVENTO['CUSTOM'])
            evento['tipo_nome'] = tipo_info['nome']
            evento['tipo_icone'] = tipo_info['icone']
            evento['tipo_cor'] = tipo_info['cor']

            eventos.append(evento)

        conn.close()
        return eventos

    def buscar_evento(self, evento_id: int) -> Optional[Dict]:
        """Busca evento por ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute('SELECT * FROM eventos WHERE id = ?', (evento_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        evento = dict(row)

        # Buscar filtros
        cursor.execute('SELECT * FROM evento_filtros WHERE evento_id = ?', (evento_id,))
        evento['filtros'] = [dict(f) for f in cursor.fetchall()]

        # Buscar historico
        cursor.execute('''
            SELECT * FROM evento_historico
            WHERE evento_id = ?
            ORDER BY data_acao DESC
        ''', (evento_id,))
        evento['historico'] = [dict(h) for h in cursor.fetchall()]

        conn.close()
        return evento

    def buscar_eventos_para_item(
        self,
        codigo: int,
        cod_empresa: int,
        cod_fornecedor: int = None,
        linha1: str = None,
        linha3: str = None,
        data_referencia: date = None
    ) -> List[Dict]:
        """
        Busca eventos ATIVOS que se aplicam a um item especifico

        Esta e a funcao principal para integracao com calculo de demanda/pedidos.

        Args:
            codigo: Codigo do item
            cod_empresa: Codigo da empresa/filial
            cod_fornecedor: Codigo do fornecedor (opcional)
            linha1: Linha 1 do item (opcional)
            linha3: Linha 3 do item (opcional)
            data_referencia: Data para verificar vigencia (default: hoje)

        Returns:
            Lista de eventos aplicaveis, ordenados por data
        """
        if data_referencia is None:
            data_referencia = datetime.now().date()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Buscar eventos válidos na data de referencia
        # Um evento é válido se: não foi cancelado E a data está dentro da vigência
        # O status não impede a aplicação - apenas as datas importam
        query = '''
            SELECT DISTINCT e.*
            FROM eventos e
            LEFT JOIN evento_filtros f ON e.id = f.evento_id
            WHERE e.status != 'CANCELADO'
              AND e.data_inicio <= ?
              AND e.data_fim >= ?
              AND (
                  -- Evento sem filtros (aplica a todos)
                  NOT EXISTS (SELECT 1 FROM evento_filtros WHERE evento_id = e.id)
                  OR
                  -- Evento com filtros que correspondem
                  (
                      (f.codigo_item IS NULL OR f.codigo_item = ?)
                      AND (f.cod_empresa IS NULL OR f.cod_empresa = ?)
                      AND (f.cod_fornecedor IS NULL OR f.cod_fornecedor = ?)
                      AND (f.linha1 IS NULL OR f.linha1 = ?)
                      AND (f.linha3 IS NULL OR f.linha3 = ?)
                  )
              )
            ORDER BY e.data_inicio
        '''

        cursor = conn.cursor()
        cursor.execute(query, (
            data_referencia.isoformat(),
            data_referencia.isoformat(),
            codigo,
            cod_empresa,
            cod_fornecedor,
            linha1,
            linha3
        ))

        eventos = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return eventos

    def calcular_fator_eventos(
        self,
        codigo: int,
        cod_empresa: int,
        cod_fornecedor: int = None,
        linha1: str = None,
        linha3: str = None,
        data_inicio: date = None,
        data_fim: date = None
    ) -> Dict:
        """
        Calcula o fator multiplicador combinado de todos os eventos aplicaveis

        Usa MULTIPLICACAO para combinar eventos (Opcao C):
        Se evento1 = +80% e evento2 = +30%, fator = 1.8 * 1.3 = 2.34

        Args:
            codigo: Codigo do item
            cod_empresa: Codigo da empresa
            cod_fornecedor: Codigo do fornecedor
            linha1: Linha 1
            linha3: Linha 3
            data_inicio: Inicio do periodo de cobertura
            data_fim: Fim do periodo de cobertura

        Returns:
            Dicionario com:
            - fator_total: Fator multiplicador final
            - eventos_aplicados: Lista de eventos que contribuiram
            - impacto_total_percentual: Impacto total em %
        """
        if data_inicio is None:
            data_inicio = datetime.now().date()
        if data_fim is None:
            data_fim = data_inicio

        fator_total = 1.0
        eventos_aplicados = []

        # Verificar cada dia do periodo
        data_atual = data_inicio
        dias_no_periodo = (data_fim - data_inicio).days + 1
        fatores_diarios = []

        while data_atual <= data_fim:
            eventos_dia = self.buscar_eventos_para_item(
                codigo=codigo,
                cod_empresa=cod_empresa,
                cod_fornecedor=cod_fornecedor,
                linha1=linha1,
                linha3=linha3,
                data_referencia=data_atual
            )

            fator_dia = 1.0
            for evento in eventos_dia:
                fator_evento = 1 + (evento['impacto_percentual'] / 100)
                fator_dia *= fator_evento

                # Registrar evento (evitar duplicatas)
                if evento['id'] not in [e['id'] for e in eventos_aplicados]:
                    eventos_aplicados.append(evento)

            fatores_diarios.append(fator_dia)
            data_atual += timedelta(days=1)

        # Fator medio do periodo
        if fatores_diarios:
            fator_total = sum(fatores_diarios) / len(fatores_diarios)

        impacto_total = (fator_total - 1) * 100

        return {
            'fator_total': round(fator_total, 4),
            'impacto_total_percentual': round(impacto_total, 2),
            'eventos_aplicados': eventos_aplicados,
            'dias_analisados': dias_no_periodo
        }

    # ==========================================================================
    # ATUALIZACAO E EXCLUSAO
    # ==========================================================================

    def atualizar_evento(
        self,
        evento_id: int,
        nome: str = None,
        impacto_percentual: float = None,
        data_inicio: str = None,
        data_fim: str = None,
        tipo: str = None,
        descricao: str = None,
        recorrente_anual: bool = None,
        usuario: str = None
    ) -> bool:
        """Atualiza dados de um evento"""
        evento_atual = self.buscar_evento(evento_id)
        if not evento_atual:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Preparar dados para update
            campos = []
            valores = []
            dados_anteriores = {}
            dados_novos = {}

            if nome is not None:
                campos.append('nome = ?')
                valores.append(nome)
                dados_anteriores['nome'] = evento_atual['nome']
                dados_novos['nome'] = nome

            if impacto_percentual is not None:
                campos.append('impacto_percentual = ?')
                valores.append(impacto_percentual)
                dados_anteriores['impacto'] = evento_atual['impacto_percentual']
                dados_novos['impacto'] = impacto_percentual

            if data_inicio is not None:
                campos.append('data_inicio = ?')
                valores.append(data_inicio)
                dados_anteriores['data_inicio'] = evento_atual['data_inicio']
                dados_novos['data_inicio'] = data_inicio

            if data_fim is not None:
                campos.append('data_fim = ?')
                valores.append(data_fim)
                dados_anteriores['data_fim'] = evento_atual['data_fim']
                dados_novos['data_fim'] = data_fim

            if tipo is not None:
                campos.append('tipo = ?')
                valores.append(tipo)
                dados_anteriores['tipo'] = evento_atual['tipo']
                dados_novos['tipo'] = tipo

            if descricao is not None:
                campos.append('descricao = ?')
                valores.append(descricao)

            if recorrente_anual is not None:
                campos.append('recorrente_anual = ?')
                valores.append(1 if recorrente_anual else 0)

            if not campos:
                return True  # Nada para atualizar

            campos.append('atualizado_em = CURRENT_TIMESTAMP')
            campos.append('atualizado_por = ?')
            valores.append(usuario)
            valores.append(evento_id)

            query = f"UPDATE eventos SET {', '.join(campos)} WHERE id = ?"
            cursor.execute(query, valores)

            # Registrar historico
            self._registrar_historico(
                cursor, evento_id, 'EDITADO',
                dados_anteriores, dados_novos, usuario
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def atualizar_filtros_evento(
        self,
        evento_id: int,
        filtros: List[Dict],
        usuario: str = None
    ) -> bool:
        """Substitui todos os filtros de um evento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Remover filtros antigos
            cursor.execute('DELETE FROM evento_filtros WHERE evento_id = ?', (evento_id,))

            # Inserir novos filtros
            for filtro in filtros:
                cursor.execute('''
                    INSERT INTO evento_filtros (
                        evento_id, codigo_item, cod_fornecedor,
                        linha1, linha3, cod_empresa
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    evento_id,
                    filtro.get('codigo_item'),
                    filtro.get('cod_fornecedor'),
                    filtro.get('linha1'),
                    filtro.get('linha3'),
                    filtro.get('cod_empresa')
                ))

            self._registrar_historico(
                cursor, evento_id, 'FILTROS_ATUALIZADOS',
                None, {'num_filtros': len(filtros)}, usuario
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def cancelar_evento(self, evento_id: int, usuario: str = None) -> bool:
        """Cancela um evento (mantem no historico)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE eventos
                SET status = 'CANCELADO', atualizado_em = CURRENT_TIMESTAMP, atualizado_por = ?
                WHERE id = ?
            ''', (usuario, evento_id))

            self._registrar_historico(cursor, evento_id, 'CANCELADO', None, None, usuario)

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def excluir_evento(self, evento_id: int, usuario: str = None) -> bool:
        """Exclui permanentemente um evento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Registrar antes de excluir
            self._registrar_historico(cursor, evento_id, 'EXCLUIDO', None, None, usuario)

            cursor.execute('DELETE FROM eventos WHERE id = ?', (evento_id,))
            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    # ==========================================================================
    # STATUS E RECORRENCIA
    # ==========================================================================

    def atualizar_status_eventos(self) -> Dict:
        """
        Atualiza status de todos os eventos baseado na vigencia

        Deve ser chamado periodicamente (ex: diariamente)

        Returns:
            Estatisticas de atualizacao
        """
        hoje = datetime.now().date().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {'expirados': 0, 'replicados': 0}

        try:
            # Marcar como expirados os eventos ATIVOS que já passaram da data fim
            cursor.execute('''
                UPDATE eventos
                SET status = 'EXPIRADO', atualizado_em = CURRENT_TIMESTAMP
                WHERE status = 'ATIVO' AND data_fim < ?
            ''', (hoje,))
            stats['expirados'] = cursor.rowcount

            # Replicar eventos recorrentes
            stats['replicados'] = self._replicar_eventos_recorrentes(cursor)

            conn.commit()

        finally:
            conn.close()

        return stats

    def _replicar_eventos_recorrentes(self, cursor) -> int:
        """Replica eventos recorrentes para o proximo ano"""
        hoje = datetime.now().date()
        ano_atual = hoje.year

        # Buscar eventos recorrentes que expiraram e nao tem replica no proximo ano
        cursor.execute('''
            SELECT * FROM eventos
            WHERE recorrente_anual = 1
              AND status = 'EXPIRADO'
              AND strftime('%Y', data_fim) < ?
        ''', (str(ano_atual),))

        eventos_para_replicar = cursor.fetchall()
        replicados = 0

        for evento in eventos_para_replicar:
            # Verificar se ja existe replica
            dt_inicio_original = datetime.strptime(evento[5], '%Y-%m-%d').date()
            dt_fim_original = datetime.strptime(evento[6], '%Y-%m-%d').date()

            nova_data_inicio = dt_inicio_original.replace(year=ano_atual)
            nova_data_fim = dt_fim_original.replace(year=ano_atual)

            cursor.execute('''
                SELECT id FROM eventos
                WHERE nome = ? AND data_inicio = ?
            ''', (evento[1], nova_data_inicio.isoformat()))

            if cursor.fetchone():
                continue  # Ja existe

            # Criar replica
            cursor.execute('''
                INSERT INTO eventos (
                    nome, tipo, descricao, impacto_percentual,
                    data_inicio, data_fim, recorrente_anual, status,
                    criado_por
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDENTE', 'SISTEMA')
            ''', (
                evento[1], evento[2], evento[3], evento[4],
                nova_data_inicio.isoformat(), nova_data_fim.isoformat(), 1
            ))

            novo_id = cursor.lastrowid

            # Copiar filtros
            cursor.execute('''
                INSERT INTO evento_filtros (
                    evento_id, codigo_item, cod_fornecedor, linha1, linha3, cod_empresa
                )
                SELECT ?, codigo_item, cod_fornecedor, linha1, linha3, cod_empresa
                FROM evento_filtros WHERE evento_id = ?
            ''', (novo_id, evento[0]))

            replicados += 1

        return replicados

    # ==========================================================================
    # IMPORTACAO EM MASSA
    # ==========================================================================

    def importar_eventos_excel(
        self,
        arquivo: str,
        usuario: str = None
    ) -> Dict:
        """
        Importa eventos de arquivo Excel/CSV

        Formato esperado:
        | nome | tipo | impacto_percentual | data_inicio | data_fim | codigo_item | cod_empresa | cod_fornecedor | linha1 | linha3 | recorrente |

        Args:
            arquivo: Caminho do arquivo Excel ou CSV
            usuario: Usuario que esta importando

        Returns:
            Estatisticas de importacao
        """
        # Ler arquivo
        if arquivo.endswith('.csv'):
            df = pd.read_csv(arquivo)
        else:
            df = pd.read_excel(arquivo)

        stats = {
            'total_linhas': len(df),
            'importados': 0,
            'erros': 0,
            'detalhes_erros': []
        }

        # Colunas obrigatorias
        colunas_obrigatorias = ['nome', 'impacto_percentual', 'data_inicio', 'data_fim']
        for col in colunas_obrigatorias:
            if col not in df.columns:
                stats['detalhes_erros'].append(f"Coluna obrigatoria ausente: {col}")
                return stats

        # Processar cada linha
        for idx, row in df.iterrows():
            try:
                # Montar filtro
                filtro = {}
                if pd.notna(row.get('codigo_item')):
                    filtro['codigo_item'] = int(row['codigo_item'])
                if pd.notna(row.get('cod_empresa')):
                    filtro['cod_empresa'] = int(row['cod_empresa'])
                if pd.notna(row.get('cod_fornecedor')):
                    filtro['cod_fornecedor'] = int(row['cod_fornecedor'])
                if pd.notna(row.get('linha1')):
                    filtro['linha1'] = str(row['linha1'])
                if pd.notna(row.get('linha3')):
                    filtro['linha3'] = str(row['linha3'])

                filtros = [filtro] if filtro else None

                # Converter datas
                data_inicio = pd.to_datetime(row['data_inicio']).strftime('%Y-%m-%d')
                data_fim = pd.to_datetime(row['data_fim']).strftime('%Y-%m-%d')

                # Cadastrar evento
                self.cadastrar_evento(
                    nome=str(row['nome']),
                    impacto_percentual=float(row['impacto_percentual']),
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    tipo=str(row.get('tipo', 'CUSTOM')),
                    descricao=str(row.get('descricao', '')) if pd.notna(row.get('descricao')) else None,
                    recorrente_anual=bool(row.get('recorrente', False)),
                    filtros=filtros,
                    usuario=usuario
                )

                stats['importados'] += 1

            except Exception as e:
                stats['erros'] += 1
                stats['detalhes_erros'].append(f"Linha {idx + 2}: {str(e)}")

        return stats

    def exportar_eventos_excel(self, arquivo: str) -> int:
        """
        Exporta eventos para Excel

        Args:
            arquivo: Caminho do arquivo de saida

        Returns:
            Numero de eventos exportados
        """
        eventos = self.listar_eventos(incluir_expirados=True)

        # Preparar dados para export
        dados = []
        for evento in eventos:
            filtros = evento.get('filtros', [])

            if filtros:
                for filtro in filtros:
                    dados.append({
                        'id': evento['id'],
                        'nome': evento['nome'],
                        'tipo': evento['tipo'],
                        'impacto_percentual': evento['impacto_percentual'],
                        'data_inicio': evento['data_inicio'],
                        'data_fim': evento['data_fim'],
                        'status': evento['status'],
                        'recorrente': evento['recorrente_anual'],
                        'codigo_item': filtro.get('codigo_item'),
                        'cod_empresa': filtro.get('cod_empresa'),
                        'cod_fornecedor': filtro.get('cod_fornecedor'),
                        'linha1': filtro.get('linha1'),
                        'linha3': filtro.get('linha3')
                    })
            else:
                dados.append({
                    'id': evento['id'],
                    'nome': evento['nome'],
                    'tipo': evento['tipo'],
                    'impacto_percentual': evento['impacto_percentual'],
                    'data_inicio': evento['data_inicio'],
                    'data_fim': evento['data_fim'],
                    'status': evento['status'],
                    'recorrente': evento['recorrente_anual'],
                    'codigo_item': None,
                    'cod_empresa': None,
                    'cod_fornecedor': None,
                    'linha1': None,
                    'linha3': None
                })

        df = pd.DataFrame(dados)
        df.to_excel(arquivo, index=False)

        return len(eventos)

    # ==========================================================================
    # ALERTAS E NOTIFICACOES
    # ==========================================================================

    def obter_alertas(self, dias_antecedencia: int = 7) -> Dict:
        """
        Obtem alertas de eventos proximos e expirados

        Args:
            dias_antecedencia: Dias para considerar "proximo"

        Returns:
            Dicionario com alertas
        """
        hoje = datetime.now().date()
        data_limite = hoje + timedelta(days=dias_antecedencia)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        # Eventos que vao iniciar em breve
        # Eventos ATIVOS que vão iniciar em breve (data_inicio > hoje)
        cursor.execute('''
            SELECT * FROM eventos
            WHERE status = 'ATIVO'
              AND data_inicio <= ?
              AND data_inicio > ?
            ORDER BY data_inicio
        ''', (data_limite.isoformat(), hoje.isoformat()))
        proximos = [dict(row) for row in cursor.fetchall()]

        # Eventos que expiraram recentemente (ultimos 7 dias)
        data_expiracao = hoje - timedelta(days=dias_antecedencia)
        cursor.execute('''
            SELECT * FROM eventos
            WHERE status = 'EXPIRADO'
              AND data_fim >= ?
            ORDER BY data_fim DESC
        ''', (data_expiracao.isoformat(),))
        expirados_recentes = [dict(row) for row in cursor.fetchall()]

        # Eventos ativos
        cursor.execute('''
            SELECT * FROM eventos
            WHERE status = 'ATIVO'
            ORDER BY data_fim
        ''')
        ativos = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'proximos': proximos,
            'expirados_recentes': expirados_recentes,
            'ativos': ativos,
            'total_proximos': len(proximos),
            'total_ativos': len(ativos)
        }

    # ==========================================================================
    # RELATORIO DE ACURACIA
    # ==========================================================================

    def registrar_acuracia(
        self,
        evento_id: int,
        codigo_item: int,
        cod_empresa: int,
        demanda_prevista: float,
        demanda_real: float
    ):
        """Registra dados para calculo de acuracia"""
        impacto_previsto = self.buscar_evento(evento_id)['impacto_percentual']

        # Calcular impacto real (comparando com periodo sem evento)
        if demanda_prevista > 0:
            impacto_real = ((demanda_real / demanda_prevista) - 1) * 100
        else:
            impacto_real = 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO evento_acuracia (
                evento_id, codigo_item, cod_empresa,
                demanda_prevista, demanda_real,
                impacto_previsto, impacto_real, data_calculo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            evento_id, codigo_item, cod_empresa,
            demanda_prevista, demanda_real,
            impacto_previsto, impacto_real,
            datetime.now().date().isoformat()
        ))

        conn.commit()
        conn.close()

    def obter_relatorio_acuracia(self) -> List[Dict]:
        """
        Obtem relatorio de acuracia dos eventos

        Returns:
            Lista com acuracia por evento
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                e.id,
                e.nome,
                e.tipo,
                e.data_inicio,
                e.data_fim,
                e.impacto_percentual as impacto_previsto,
                AVG(a.impacto_real) as impacto_real_medio,
                COUNT(a.id) as num_registros,
                ABS(e.impacto_percentual - AVG(a.impacto_real)) as erro_absoluto
            FROM eventos e
            LEFT JOIN evento_acuracia a ON e.id = a.evento_id
            WHERE e.status = 'EXPIRADO'
            GROUP BY e.id
            HAVING num_registros > 0
            ORDER BY e.data_fim DESC
        ''')

        resultados = []
        for row in cursor.fetchall():
            r = dict(row)
            # Calcular acuracia percentual
            if r['impacto_previsto'] != 0:
                r['acuracia'] = 100 - abs((r['impacto_real_medio'] - r['impacto_previsto']) / r['impacto_previsto'] * 100)
            else:
                r['acuracia'] = 100 if r['impacto_real_medio'] == 0 else 0
            r['acuracia'] = max(0, min(100, r['acuracia']))
            resultados.append(r)

        conn.close()
        return resultados

    # ==========================================================================
    # PREVIEW DE IMPACTO
    # ==========================================================================

    def preview_impacto(
        self,
        nome: str,
        impacto_percentual: float,
        data_inicio: str,
        data_fim: str,
        filtros: List[Dict],
        conn_postgres=None
    ) -> Dict:
        """
        Calcula preview do impacto antes de salvar o evento

        Args:
            nome: Nome do evento
            impacto_percentual: Impacto em %
            data_inicio: Data inicio
            data_fim: Data fim
            filtros: Filtros do evento
            conn_postgres: Conexao com PostgreSQL para buscar dados

        Returns:
            Preview do impacto
        """
        if not conn_postgres:
            return {
                'itens_afetados': 'N/A (sem conexao com banco)',
                'demanda_atual': 0,
                'demanda_com_evento': 0,
                'diferenca': 0
            }

        # Montar query para contar itens afetados
        query_base = "SELECT COUNT(DISTINCT codigo) FROM produtos WHERE 1=1"
        params = []

        if filtros:
            for filtro in filtros:
                if filtro.get('codigo_item'):
                    query_base += " AND codigo = %s"
                    params.append(filtro['codigo_item'])
                if filtro.get('cod_fornecedor'):
                    query_base += " AND cod_fornecedor = %s"
                    params.append(filtro['cod_fornecedor'])
                if filtro.get('linha1'):
                    query_base += " AND linha1 = %s"
                    params.append(filtro['linha1'])
                if filtro.get('linha3'):
                    query_base += " AND linha3 = %s"
                    params.append(filtro['linha3'])

        try:
            import pandas as pd
            df = pd.read_sql(query_base, conn_postgres, params=params)
            itens_afetados = int(df.iloc[0, 0])
        except Exception:
            itens_afetados = 'Erro ao consultar'

        fator = 1 + (impacto_percentual / 100)

        return {
            'evento': nome,
            'periodo': f"{data_inicio} a {data_fim}",
            'impacto': f"{'+' if impacto_percentual > 0 else ''}{impacto_percentual}%",
            'itens_afetados': itens_afetados,
            'fator_multiplicador': round(fator, 4)
        }

    # ==========================================================================
    # APLICACAO EM PREVISOES (TELA DE DEMANDA)
    # ==========================================================================

    def aplicar_eventos_na_previsao(self, previsoes: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica ajustes de eventos nas previsoes da tela de demanda.

        Procura eventos ativos que se aplicam ao mes/ano de cada previsao
        e multiplica o valor pelo fator do evento.

        Args:
            previsoes: DataFrame com colunas:
                       - 'Mes' ou 'Mes_Previsao': data da previsao
                       - 'Previsao': valor previsto
                       - Opcionais: 'SKU', 'Loja', 'cod_fornecedor', 'linha1', 'linha3'

        Returns:
            DataFrame com previsoes ajustadas e colunas adicionais:
            - 'Evento_Aplicado': nome do evento (ou None)
            - 'Multiplicador_Evento': fator aplicado
            - 'Previsao_Original': valor antes do ajuste
        """
        df_ajustado = previsoes.copy()
        df_ajustado['Evento_Aplicado'] = None
        df_ajustado['Multiplicador_Evento'] = 1.0
        df_ajustado['Previsao_Original'] = df_ajustado['Previsao'].copy()

        # Identificar coluna de data
        coluna_data = 'Mes_Previsao' if 'Mes_Previsao' in df_ajustado.columns else 'Mes'

        if coluna_data not in df_ajustado.columns:
            print(f"[EVENTOS V2] Coluna de data nao encontrada. Colunas: {df_ajustado.columns.tolist()}")
            return df_ajustado

        # Buscar eventos ativos e pendentes
        eventos = self.listar_eventos(incluir_expirados=False)
        # Filtrar eventos não cancelados
        eventos_ativos = [e for e in eventos if e['status'] != 'CANCELADO']

        if not eventos_ativos:
            return df_ajustado

        print(f"[EVENTOS V2] Aplicando {len(eventos_ativos)} evento(s) nas previsoes...")

        for evento in eventos_ativos:
            try:
                data_inicio = datetime.strptime(evento['data_inicio'], '%Y-%m-%d').date()
                data_fim = datetime.strptime(evento['data_fim'], '%Y-%m-%d').date()
                impacto = evento['impacto_percentual']
                fator = 1 + (impacto / 100)

                # Converter coluna de data para datetime
                datas_previsao = pd.to_datetime(df_ajustado[coluna_data])

                # Verificar filtros do evento
                filtros = evento.get('filtros', [])
                tem_filtros = len(filtros) > 0 and any(
                    f.get('codigo_item') or f.get('cod_empresa') or
                    f.get('cod_fornecedor') or f.get('linha1') or f.get('linha3')
                    for f in filtros
                )

                # Mascara base: previsoes que caem dentro da vigencia do evento
                # Compara ano e mes da previsao com o periodo do evento
                mask_periodo = (
                    (datas_previsao >= pd.Timestamp(data_inicio)) &
                    (datas_previsao <= pd.Timestamp(data_fim))
                )

                # Se evento tem filtros, aplicar restricoes
                if tem_filtros:
                    mask_filtros = pd.Series([False] * len(df_ajustado))

                    for filtro in filtros:
                        mask_f = pd.Series([True] * len(df_ajustado))

                        if filtro.get('codigo_item') and 'SKU' in df_ajustado.columns:
                            mask_f &= (df_ajustado['SKU'] == filtro['codigo_item'])

                        if filtro.get('cod_empresa') and 'Loja' in df_ajustado.columns:
                            mask_f &= (df_ajustado['Loja'] == filtro['cod_empresa'])

                        if filtro.get('cod_fornecedor') and 'cod_fornecedor' in df_ajustado.columns:
                            mask_f &= (df_ajustado['cod_fornecedor'] == filtro['cod_fornecedor'])

                        if filtro.get('linha1') and 'linha1' in df_ajustado.columns:
                            mask_f &= (df_ajustado['linha1'] == filtro['linha1'])

                        if filtro.get('linha3') and 'linha3' in df_ajustado.columns:
                            mask_f &= (df_ajustado['linha3'] == filtro['linha3'])

                        mask_filtros |= mask_f

                    mask_final = mask_periodo & mask_filtros
                else:
                    # Sem filtros = aplica a todos
                    mask_final = mask_periodo

                # Aplicar multiplicador
                if mask_final.any():
                    # Multiplicar fatores se ja houver evento aplicado
                    df_ajustado.loc[mask_final, 'Previsao'] *= fator
                    df_ajustado.loc[mask_final, 'Multiplicador_Evento'] *= fator

                    # Registrar nome do evento (concatenar se varios)
                    for idx in df_ajustado[mask_final].index:
                        evento_atual = df_ajustado.loc[idx, 'Evento_Aplicado']
                        if evento_atual:
                            df_ajustado.loc[idx, 'Evento_Aplicado'] = f"{evento_atual} + {evento['nome']}"
                        else:
                            df_ajustado.loc[idx, 'Evento_Aplicado'] = evento['nome']

                    print(f"   - {evento['nome']}: {mask_final.sum()} previsoes ajustadas ({'+' if impacto > 0 else ''}{impacto}%)")

            except Exception as e:
                print(f"[EVENTOS V2] Erro ao aplicar evento {evento.get('nome')}: {e}")
                continue

        # Resumo
        total_ajustados = df_ajustado['Evento_Aplicado'].notna().sum()
        print(f"[EVENTOS V2] Total de previsoes ajustadas: {total_ajustados}")

        return df_ajustado

    # ==========================================================================
    # UTILIDADES INTERNAS
    # ==========================================================================

    def _registrar_historico(
        self,
        cursor,
        evento_id: int,
        acao: str,
        dados_anteriores: dict,
        dados_novos: dict,
        usuario: str
    ):
        """Registra acao no historico"""
        cursor.execute('''
            INSERT INTO evento_historico (
                evento_id, acao, dados_anteriores, dados_novos, usuario
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            evento_id,
            acao,
            json.dumps(dados_anteriores) if dados_anteriores else None,
            json.dumps(dados_novos) if dados_novos else None,
            usuario
        ))


# ==============================================================================
# FUNCOES HELPER
# ==============================================================================

def criar_event_manager_v2(db_path: str = 'outputs/events_v2.db') -> EventManagerV2:
    """Factory function para criar instancia do EventManagerV2"""
    return EventManagerV2(db_path)
