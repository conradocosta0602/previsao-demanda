"""
Módulo de Gerenciamento de Eventos Sazonais

Permite cadastrar eventos futuros (Black Friday, Natal, etc.) e calcular
multiplicadores históricos para ajustar previsões automaticamente.

Funcionalidades:
1. Cadastro de eventos com data e tipo
2. Cálculo automático de multiplicadores baseado em histórico
3. Aplicação de ajustes nas previsões
4. Persistência em SQLite
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os


class EventManager:
    """
    Gerenciador de eventos sazonais

    Armazena eventos futuros e calcula multiplicadores históricos
    para ajustar previsões automaticamente.
    """

    # Tipos de eventos pré-definidos
    EVENT_TYPES = {
        'BLACK_FRIDAY': {
            'nome': 'Black Friday',
            'descricao': 'Última sexta-feira de novembro',
            'duracao_dias': 3,  # Sexta a domingo
            'icone': '🛍️'
        },
        'NATAL': {
            'nome': 'Natal',
            'descricao': '25 de dezembro',
            'duracao_dias': 7,  # Semana do Natal
            'icone': '🎄'
        },
        'ANO_NOVO': {
            'nome': 'Ano Novo',
            'descricao': '31 de dezembro e 1 de janeiro',
            'duracao_dias': 2,
            'icone': '🎆'
        },
        'DIAS_MAES': {
            'nome': 'Dia das Mães',
            'descricao': 'Segunda domingo de maio',
            'duracao_dias': 7,
            'icone': '💐'
        },
        'DIAS_PAIS': {
            'nome': 'Dia dos Pais',
            'descricao': 'Segunda domingo de agosto',
            'duracao_dias': 7,
            'icone': '👔'
        },
        'PASCOA': {
            'nome': 'Páscoa',
            'descricao': 'Data móvel (março/abril)',
            'duracao_dias': 7,
            'icone': '🐰'
        },
        'VOLTA_AULAS': {
            'nome': 'Volta às Aulas',
            'descricao': 'Janeiro/Fevereiro',
            'duracao_dias': 14,
            'icone': '📚'
        },
        'CUSTOM': {
            'nome': 'Evento Customizado',
            'descricao': 'Evento específico da empresa',
            'duracao_dias': 1,
            'icone': '📅'
        }
    }

    def __init__(self, db_path: str = 'outputs/events.db'):
        """
        Inicializa o gerenciador de eventos

        Args:
            db_path: Caminho do banco SQLite
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Cria tabela de eventos se não existir"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabela de eventos cadastrados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                nome TEXT NOT NULL,
                data_evento DATE NOT NULL,
                duracao_dias INTEGER DEFAULT 1,
                multiplicador_calculado REAL,
                multiplicador_manual REAL,
                usar_multiplicador_manual INTEGER DEFAULT 0,
                ativo INTEGER DEFAULT 1,
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabela de histórico de eventos (para cálculo de multiplicadores)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                ano INTEGER NOT NULL,
                mes INTEGER NOT NULL,
                data_evento DATE NOT NULL,
                demanda_evento REAL,
                demanda_normal REAL,
                multiplicador REAL,
                sku TEXT,
                loja TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tipo, ano, sku, loja)
            )
        ''')

        conn.commit()
        conn.close()

    def cadastrar_evento(self, tipo: str, data_evento: str,
                        multiplicador_manual: float = None,
                        nome_custom: str = None,
                        duracao_dias: int = None,
                        observacoes: str = None) -> int:
        """
        Cadastra um novo evento futuro

        Args:
            tipo: Tipo do evento (BLACK_FRIDAY, NATAL, etc)
            data_evento: Data do evento (YYYY-MM-DD)
            multiplicador_manual: Multiplicador customizado (opcional)
            nome_custom: Nome para eventos CUSTOM
            duracao_dias: Duração customizada (opcional)
            observacoes: Observações sobre o evento

        Returns:
            ID do evento cadastrado
        """
        if tipo not in self.EVENT_TYPES:
            raise ValueError(f"Tipo de evento inválido: {tipo}")

        event_info = self.EVENT_TYPES[tipo]
        nome = nome_custom if tipo == 'CUSTOM' and nome_custom else event_info['nome']
        duracao = duracao_dias if duracao_dias else event_info['duracao_dias']

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO eventos (tipo, nome, data_evento, duracao_dias,
                               multiplicador_manual, usar_multiplicador_manual, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (tipo, nome, data_evento, duracao,
              multiplicador_manual, 1 if multiplicador_manual else 0, observacoes))

        evento_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return evento_id

    def calcular_multiplicador_historico(self, tipo: str,
                                        historico_vendas: pd.DataFrame,
                                        datas_eventos_passados: List[str] = None) -> Dict:
        """
        Calcula multiplicador baseado em eventos passados similares

        Args:
            tipo: Tipo do evento
            historico_vendas: DataFrame com ['Mes', 'Vendas_Corrigidas', 'SKU', 'Loja']
            datas_eventos_passados: Lista de datas (YYYY-MM-DD) onde o evento ocorreu

        Returns:
            Dicionário com multiplicador médio e detalhes
        """
        if tipo not in self.EVENT_TYPES:
            raise ValueError(f"Tipo de evento inválido: {tipo}")

        # Se não informou datas, tentar detectar automaticamente
        if not datas_eventos_passados:
            datas_eventos_passados = self._detectar_eventos_automatico(tipo, historico_vendas)

        if not datas_eventos_passados:
            return {
                'multiplicador': 1.0,
                'confianca': 0.0,
                'eventos_analisados': 0,
                'metodo': 'PADRAO',
                'razao': 'Sem histórico de eventos similares'
            }

        # Converter datas
        datas_evento = [pd.to_datetime(d) for d in datas_eventos_passados]

        multiplicadores = []
        detalhes = []

        for data_evento in datas_evento:
            # Janela do evento
            duracao = self.EVENT_TYPES[tipo]['duracao_dias']
            inicio_evento = data_evento
            fim_evento = data_evento + timedelta(days=duracao)

            # Demanda durante o evento
            mask_evento = (historico_vendas['Mes'] >= inicio_evento) & \
                         (historico_vendas['Mes'] <= fim_evento)
            demanda_evento = historico_vendas[mask_evento]['Vendas_Corrigidas'].sum()

            # Demanda normal (mesmo período em outros meses)
            mes_evento = data_evento.month
            demanda_normal_list = []

            for ano in historico_vendas['Mes'].dt.year.unique():
                if ano == data_evento.year:
                    continue  # Pular ano do evento

                mes_inicio = pd.Timestamp(year=ano, month=mes_evento, day=1)
                mes_fim = mes_inicio + timedelta(days=duracao)

                mask_normal = (historico_vendas['Mes'] >= mes_inicio) & \
                             (historico_vendas['Mes'] <= mes_fim)

                demanda_mes = historico_vendas[mask_normal]['Vendas_Corrigidas'].sum()
                if demanda_mes > 0:
                    demanda_normal_list.append(demanda_mes)

            if demanda_normal_list:
                demanda_normal = np.mean(demanda_normal_list)
            else:
                continue  # Sem baseline para comparar

            if demanda_normal > 0:
                multiplicador = demanda_evento / demanda_normal
                multiplicadores.append(multiplicador)

                detalhes.append({
                    'ano': data_evento.year,
                    'data': data_evento.strftime('%Y-%m-%d'),
                    'demanda_evento': float(demanda_evento),
                    'demanda_normal': float(demanda_normal),
                    'multiplicador': float(multiplicador)
                })

        if not multiplicadores:
            return {
                'multiplicador': 1.0,
                'confianca': 0.0,
                'eventos_analisados': 0,
                'metodo': 'PADRAO',
                'razao': 'Não foi possível calcular multiplicador'
            }

        # Calcular multiplicador médio
        multiplicador_medio = np.mean(multiplicadores)
        desvio_padrao = np.std(multiplicadores)

        # Calcular confiança
        confianca = self._calcular_confianca(len(multiplicadores), desvio_padrao)

        return {
            'multiplicador': float(multiplicador_medio),
            'desvio_padrao': float(desvio_padrao),
            'confianca': float(confianca),
            'eventos_analisados': len(multiplicadores),
            'metodo': 'HISTORICO',
            'razao': f'Baseado em {len(multiplicadores)} evento(s) similar(es)',
            'detalhes': detalhes
        }

    def _detectar_eventos_automatico(self, tipo: str,
                                    historico_vendas: pd.DataFrame) -> List[str]:
        """
        Detecta automaticamente datas de eventos no histórico

        Args:
            tipo: Tipo do evento
            historico_vendas: DataFrame histórico

        Returns:
            Lista de datas detectadas (YYYY-MM-DD)
        """
        datas_detectadas = []

        # Estratégias de detecção por tipo
        if tipo == 'BLACK_FRIDAY':
            # Black Friday: última sexta de novembro
            for ano in historico_vendas['Mes'].dt.year.unique():
                # Último dia de novembro
                ultimo_dia = pd.Timestamp(year=ano, month=11, day=30)
                # Voltar até a última sexta
                while ultimo_dia.weekday() != 4:  # 4 = sexta
                    ultimo_dia -= timedelta(days=1)
                datas_detectadas.append(ultimo_dia.strftime('%Y-%m-%d'))

        elif tipo == 'NATAL':
            # Natal: 25 de dezembro
            for ano in historico_vendas['Mes'].dt.year.unique():
                datas_detectadas.append(f'{ano}-12-25')

        elif tipo == 'ANO_NOVO':
            # Ano Novo: 31 de dezembro
            for ano in historico_vendas['Mes'].dt.year.unique():
                datas_detectadas.append(f'{ano}-12-31')

        # Filtrar apenas datas que existem no histórico
        min_date = historico_vendas['Mes'].min()
        max_date = historico_vendas['Mes'].max()

        datas_validas = []
        for data_str in datas_detectadas:
            data = pd.to_datetime(data_str)
            if min_date <= data <= max_date:
                datas_validas.append(data_str)

        return datas_validas

    def _calcular_confianca(self, num_eventos: int, desvio_padrao: float) -> float:
        """
        Calcula confiança no multiplicador

        Args:
            num_eventos: Número de eventos analisados
            desvio_padrao: Desvio padrão dos multiplicadores

        Returns:
            Confiança (0-1)
        """
        confianca = 0.3  # Base

        # Fator 1: Número de eventos
        if num_eventos >= 3:
            confianca += 0.4
        elif num_eventos == 2:
            confianca += 0.2
        elif num_eventos == 1:
            confianca += 0.1

        # Fator 2: Consistência (baixo desvio)
        if desvio_padrao < 0.1:
            confianca += 0.3
        elif desvio_padrao < 0.2:
            confianca += 0.2
        elif desvio_padrao < 0.3:
            confianca += 0.1

        return min(1.0, confianca)

    def aplicar_eventos_na_previsao(self, previsoes: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica ajustes de eventos nas previsões

        Args:
            previsoes: DataFrame com ['Mes_Previsao', 'Previsao', 'SKU', 'Loja']

        Returns:
            DataFrame com previsões ajustadas e coluna 'Evento_Aplicado'
        """
        df_ajustado = previsoes.copy()
        df_ajustado['Evento_Aplicado'] = None
        df_ajustado['Multiplicador_Evento'] = 1.0
        df_ajustado['Previsao_Original'] = df_ajustado['Previsao']

        # Identificar qual coluna de data usar (Mes_Previsao ou Mes)
        coluna_data = 'Mes_Previsao' if 'Mes_Previsao' in df_ajustado.columns else 'Mes'

        if coluna_data not in df_ajustado.columns:
            print(f"[AVISO] Nenhuma coluna de data encontrada. Colunas disponíveis: {df_ajustado.columns.tolist()}")
            return df_ajustado

        # Buscar eventos ativos (não filtrar por futuros, pois a previsão pode incluir datas passadas)
        eventos_ativos = self.listar_eventos(apenas_ativos=True, apenas_futuros=False)

        for evento in eventos_ativos:
            data_evento = pd.to_datetime(evento['data_evento'])
            duracao = evento['duracao_dias']

            # Definir janela do evento
            inicio = data_evento
            fim = data_evento + timedelta(days=duracao)

            # Converter coluna de data para datetime
            datas_previsao = pd.to_datetime(df_ajustado[coluna_data])

            # Filtrar previsões que caem no mesmo MÊS/ANO do evento
            # Isso porque previsões são mensais, não diárias
            mask = (datas_previsao.dt.year == data_evento.year) & \
                   (datas_previsao.dt.month == data_evento.month)

            if mask.any():
                # Usar multiplicador manual se disponível, senão usar calculado
                multiplicador = evento['multiplicador_manual'] if evento['usar_multiplicador_manual'] \
                              else evento.get('multiplicador_calculado', 1.0)

                if multiplicador and multiplicador != 1.0:
                    df_ajustado.loc[mask, 'Previsao'] *= multiplicador
                    df_ajustado.loc[mask, 'Multiplicador_Evento'] = multiplicador
                    df_ajustado.loc[mask, 'Evento_Aplicado'] = evento['nome']

        return df_ajustado

    def listar_eventos(self, apenas_ativos: bool = True,
                      apenas_futuros: bool = False) -> List[Dict]:
        """
        Lista eventos cadastrados

        Args:
            apenas_ativos: Filtrar apenas eventos ativos
            apenas_futuros: Filtrar apenas eventos futuros

        Returns:
            Lista de eventos
        """
        conn = sqlite3.connect(self.db_path)

        query = "SELECT * FROM eventos WHERE 1=1"

        if apenas_ativos:
            query += " AND ativo = 1"

        if apenas_futuros:
            hoje = datetime.now().strftime('%Y-%m-%d')
            query += f" AND data_evento >= '{hoje}'"

        query += " ORDER BY data_evento"

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df.to_dict('records')

    def atualizar_multiplicador(self, evento_id: int,
                               multiplicador: float,
                               historico_vendas: pd.DataFrame = None):
        """
        Atualiza multiplicador de um evento

        Args:
            evento_id: ID do evento
            multiplicador: Novo multiplicador (ou None para recalcular)
            historico_vendas: DataFrame para recálculo automático
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if multiplicador is not None:
            # Atualizar com valor manual
            cursor.execute('''
                UPDATE eventos
                SET multiplicador_manual = ?,
                    usar_multiplicador_manual = 1,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (multiplicador, evento_id))
        else:
            # Recalcular automaticamente
            if historico_vendas is None:
                raise ValueError("histórico_vendas necessário para recálculo")

            cursor.execute("SELECT tipo FROM eventos WHERE id = ?", (evento_id,))
            tipo = cursor.fetchone()[0]

            resultado = self.calcular_multiplicador_historico(tipo, historico_vendas)

            cursor.execute('''
                UPDATE eventos
                SET multiplicador_calculado = ?,
                    usar_multiplicador_manual = 0,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (resultado['multiplicador'], evento_id))

        conn.commit()
        conn.close()

    def desativar_evento(self, evento_id: int):
        """Desativa um evento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE eventos
            SET ativo = 0, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (evento_id,))

        conn.commit()
        conn.close()

    def excluir_evento(self, evento_id: int):
        """Exclui permanentemente um evento do banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Excluir da tabela principal
        cursor.execute('DELETE FROM eventos WHERE id = ?', (evento_id,))

        conn.commit()
        conn.close()


def criar_evento(tipo: str, data_evento: str,
                multiplicador: float = None,
                nome_custom: str = None,
                db_path: str = 'outputs/events.db') -> int:
    """
    Helper function para criar evento rapidamente

    Args:
        tipo: Tipo do evento (BLACK_FRIDAY, NATAL, etc)
        data_evento: Data (YYYY-MM-DD)
        multiplicador: Multiplicador manual (opcional)
        nome_custom: Nome para eventos CUSTOM
        db_path: Caminho do banco

    Returns:
        ID do evento criado
    """
    manager = EventManager(db_path)
    return manager.cadastrar_evento(tipo, data_evento, multiplicador, nome_custom)
