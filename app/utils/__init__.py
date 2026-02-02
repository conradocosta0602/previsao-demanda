"""
Utilitarios compartilhados entre os blueprints
"""

from app.utils.db_connection import get_db_connection, DB_CONFIG
from app.utils.previsao_helper import processar_previsao, ultima_previsao_data

__all__ = [
    'get_db_connection',
    'DB_CONFIG',
    'processar_previsao',
    'ultima_previsao_data'
]
