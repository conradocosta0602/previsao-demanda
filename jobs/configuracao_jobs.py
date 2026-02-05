"""
Configuracao de Jobs Agendados
==============================
Parametros de configuracao para os jobs do sistema.

Autor: Valter Lino / Claude (Anthropic)
Data: Fevereiro 2026
"""

# =============================================================================
# CONFIGURACAO DE ALERTAS
# =============================================================================

CONFIGURACAO_ALERTAS = {
    'email': {
        'habilitado': True,
        'destinatarios': [
            'valter.lino@ferreiracosta.com.br',
            # Adicionar outros destinatarios conforme necessario
        ],
        'smtp_server': 'smtp.office365.com',  # Ajustar conforme ambiente
        'smtp_port': 587,
        'smtp_usuario': None,  # Configurar se necessario
        'smtp_senha': None,    # Configurar se necessario (usar variaveis de ambiente em producao)
        'remetente': 'sistema.demanda@ferreiracosta.com.br',
        'assunto_padrao': '[ALERTA] Desvio de Metodologia - Previsao Demanda'
    },

    'horario_execucao': '06:00',  # Horario do checklist diario (HH:MM)

    'criticidade': {
        # Verificacoes bloqueantes: sistema para se falhar
        'bloqueante': [
            'modulos_indisponiveis',
            'metodos_faltando',
            'demanda_negativa',
            'formula_incorreta'
        ],
        # Verificacoes de alerta: notifica mas nao para
        'alerta': [
            'sazonalidade_extrema',
            'cobertura_insuficiente',
            'desvio_alto'
        ],
        # Verificacoes informativas: apenas registra
        'info': [
            'tempo_execucao_alto',
            'variacao_detectada'
        ]
    }
}

# =============================================================================
# CONFIGURACAO DO BANCO DE DADOS
# =============================================================================

CONFIGURACAO_BANCO = {
    'host': 'localhost',
    'port': 5432,
    'database': 'previsao_demanda',
    'user': 'postgres',
    'password': 'FerreiraCost@01'
}

# Tentar carregar configuracao do arquivo principal do sistema
try:
    from app.utils.db_connection import DB_CONFIG
    CONFIGURACAO_BANCO = DB_CONFIG.copy()
except ImportError:
    pass

# =============================================================================
# CONFIGURACAO DE VERIFICACOES
# =============================================================================

CONFIGURACAO_VERIFICACOES = {
    'limiar_cobertura_saneamento': 0.50,  # 50%
    'range_indice_sazonal': (0.5, 2.0),
    'tolerancia_validacao': 0.05,  # 5%
    'z_scores_abc': {
        'A': 2.05,
        'B': 1.65,
        'C': 1.28
    },
    'metodos_obrigatorios': [
        'calcular_demanda_sma',
        'calcular_demanda_wma',
        'calcular_demanda_ema',
        'calcular_demanda_tendencia',
        'calcular_demanda_sazonal',
        'calcular_demanda_tsb'
    ]
}

# =============================================================================
# CONFIGURACAO DE LOGS
# =============================================================================

CONFIGURACAO_LOGS = {
    'nivel': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'formato': '%(asctime)s [%(levelname)s] %(message)s',
    'arquivo': 'logs/checklist_conformidade.log',
    'max_bytes': 10 * 1024 * 1024,  # 10 MB
    'backup_count': 5
}
