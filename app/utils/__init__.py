"""
Utilitarios compartilhados entre os blueprints
"""

from app.utils.db_connection import get_db_connection, DB_CONFIG
from app.utils.previsao_helper import processar_previsao, ultima_previsao_data
from app.utils.demanda_pre_calculada import (
    buscar_demanda_pre_calculada,
    buscar_demanda_proximos_meses,
    obter_demanda_diaria_efetiva,
    verificar_dados_disponiveis,
    registrar_ajuste_manual,
    limpar_ajuste_manual
)

__all__ = [
    'get_db_connection',
    'DB_CONFIG',
    'processar_previsao',
    'ultima_previsao_data',
    # Demanda pre-calculada
    'buscar_demanda_pre_calculada',
    'buscar_demanda_proximos_meses',
    'obter_demanda_diaria_efetiva',
    'verificar_dados_disponiveis',
    'registrar_ajuste_manual',
    'limpar_ajuste_manual'
]
