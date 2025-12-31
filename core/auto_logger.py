"""
Módulo de Logging para Seleção Automática (AUTO)

Registra todas as decisões do AUTO para auditoria e análise de performance.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import os


class AutoSelectionLogger:
    """
    Logger para registro de seleções do método AUTO

    Salva em banco SQLite para consulta posterior e auditoria.
    """

    def __init__(self, db_path: str = 'outputs/auto_selection_log.db'):
        """
        Inicializa o logger

        Args:
            db_path: Caminho para o arquivo do banco de dados
        """
        self.db_path = db_path

        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Criar tabela se não existir
        self._create_table()

    def _create_table(self):
        """Cria a tabela de log se não existir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_selection_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                sku TEXT,
                loja TEXT,
                metodo_selecionado TEXT NOT NULL,
                confianca REAL NOT NULL,
                razao TEXT NOT NULL,
                caracteristicas TEXT,
                alternativas TEXT,
                data_length INTEGER,
                data_mean REAL,
                data_std REAL,
                data_zeros_pct REAL,
                horizonte INTEGER,
                sucesso INTEGER DEFAULT 1,
                erro_msg TEXT
            )
        ''')

        # Criar índices para consultas rápidas
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON auto_selection_log(timestamp)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sku_loja
            ON auto_selection_log(sku, loja)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metodo
            ON auto_selection_log(metodo_selecionado)
        ''')

        conn.commit()
        conn.close()

    def log_selection(
        self,
        metodo_selecionado: str,
        confianca: float,
        razao: str,
        caracteristicas: Dict,
        alternativas: List[str] = None,
        data_stats: Dict = None,
        sku: str = None,
        loja: str = None,
        horizonte: int = None,
        sucesso: bool = True,
        erro_msg: str = None
    ) -> int:
        """
        Registra uma seleção do AUTO

        Args:
            metodo_selecionado: Nome do método escolhido
            confianca: Nível de confiança (0-1)
            razao: Razão da seleção
            caracteristicas: Características detectadas na série
            alternativas: Métodos alternativos sugeridos
            data_stats: Estatísticas dos dados (length, mean, std, zeros_pct)
            sku: Código do SKU (opcional)
            loja: Código da loja (opcional)
            horizonte: Horizonte de previsão (opcional)
            sucesso: Se a seleção foi bem-sucedida
            erro_msg: Mensagem de erro (se sucesso=False)

        Returns:
            ID do registro inserido
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Preparar dados
        timestamp = datetime.now().isoformat()
        caracteristicas_json = json.dumps(caracteristicas) if caracteristicas else None
        alternativas_json = json.dumps(alternativas) if alternativas else None

        # Extrair estatísticas dos dados
        data_length = data_stats.get('length') if data_stats else None
        data_mean = data_stats.get('mean') if data_stats else None
        data_std = data_stats.get('std') if data_stats else None
        data_zeros_pct = data_stats.get('zeros_percentage') if data_stats else None

        # Inserir registro
        cursor.execute('''
            INSERT INTO auto_selection_log (
                timestamp, sku, loja, metodo_selecionado, confianca, razao,
                caracteristicas, alternativas, data_length, data_mean, data_std,
                data_zeros_pct, horizonte, sucesso, erro_msg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, sku, loja, metodo_selecionado, confianca, razao,
            caracteristicas_json, alternativas_json, data_length, data_mean,
            data_std, data_zeros_pct, horizonte, 1 if sucesso else 0, erro_msg
        ))

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return record_id

    def get_recent_selections(self, limit: int = 100) -> List[Dict]:
        """
        Retorna seleções recentes

        Args:
            limit: Número máximo de registros

        Returns:
            Lista de seleções
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM auto_selection_log
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_selections_by_sku(self, sku: str, loja: str = None) -> List[Dict]:
        """
        Retorna histórico de seleções para um SKU

        Args:
            sku: Código do SKU
            loja: Código da loja (opcional)

        Returns:
            Lista de seleções
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if loja:
            cursor.execute('''
                SELECT * FROM auto_selection_log
                WHERE sku = ? AND loja = ?
                ORDER BY timestamp DESC
            ''', (sku, loja))
        else:
            cursor.execute('''
                SELECT * FROM auto_selection_log
                WHERE sku = ?
                ORDER BY timestamp DESC
            ''', (sku,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_method_statistics(self) -> Dict:
        """
        Retorna estatísticas sobre os métodos selecionados

        Returns:
            Dicionário com contagens por método
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Contagem por método
        cursor.execute('''
            SELECT metodo_selecionado, COUNT(*) as count
            FROM auto_selection_log
            WHERE sucesso = 1
            GROUP BY metodo_selecionado
            ORDER BY count DESC
        ''')

        method_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Total de seleções
        cursor.execute('SELECT COUNT(*) FROM auto_selection_log WHERE sucesso = 1')
        total = cursor.fetchone()[0]

        # Confiança média por método
        cursor.execute('''
            SELECT metodo_selecionado, AVG(confianca) as avg_confidence
            FROM auto_selection_log
            WHERE sucesso = 1
            GROUP BY metodo_selecionado
        ''')

        avg_confidence = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            'total_selections': total,
            'method_counts': method_counts,
            'method_percentages': {
                method: (count / total * 100) if total > 0 else 0
                for method, count in method_counts.items()
            },
            'avg_confidence_by_method': avg_confidence
        }

    def get_selections_by_date_range(
        self,
        start_date: str,
        end_date: str = None
    ) -> List[Dict]:
        """
        Retorna seleções em um período

        Args:
            start_date: Data inicial (ISO format: YYYY-MM-DD)
            end_date: Data final (opcional, padrão: hoje)

        Returns:
            Lista de seleções
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if end_date:
            cursor.execute('''
                SELECT * FROM auto_selection_log
                WHERE timestamp >= ? AND timestamp < ?
                ORDER BY timestamp DESC
            ''', (start_date, end_date))
        else:
            cursor.execute('''
                SELECT * FROM auto_selection_log
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (start_date,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def clear_old_logs(self, days: int = 90):
        """
        Remove logs antigos

        Args:
            days: Manter apenas logs dos últimos N dias
        """
        from datetime import timedelta

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calcular data de corte corretamente usando timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        cursor.execute('''
            DELETE FROM auto_selection_log
            WHERE timestamp < ?
        ''', (cutoff_str,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count


# Instância global do logger
_global_logger = None


def get_auto_logger() -> AutoSelectionLogger:
    """
    Retorna instância global do logger (singleton)

    Returns:
        AutoSelectionLogger
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = AutoSelectionLogger()

    return _global_logger
