"""
Sistema de Previsao de Demanda - Aplicacao Flask
Factory Pattern para criacao da aplicacao com blueprints modulares
"""

import os
from flask import Flask


def create_app(config=None):
    """
    Factory function para criar a aplicacao Flask.

    Args:
        config: Dicionario de configuracoes opcionais

    Returns:
        Instancia da aplicacao Flask configurada
    """
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')

    # Configuracoes padrao
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['OUTPUT_FOLDER'] = 'outputs'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB maximo

    # Aplicar configuracoes customizadas se fornecidas
    if config:
        app.config.update(config)

    # Criar pastas necessarias
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

    # Registrar blueprints
    _register_blueprints(app)

    return app


def _register_blueprints(app):
    """
    Registra todos os blueprints na aplicacao.

    Args:
        app: Instancia da aplicacao Flask
    """
    # Blueprint: Menu (rotas principais)
    from app.blueprints.menu import menu_bp
    app.register_blueprint(menu_bp)

    # Blueprint: Simulador de Cenarios
    from app.blueprints.simulador import simulador_bp
    app.register_blueprint(simulador_bp, url_prefix='/simulador')

    # Blueprint: Eventos V2
    from app.blueprints.eventos import eventos_bp
    app.register_blueprint(eventos_bp)

    # Blueprint: Pedido ao Fornecedor Integrado
    from app.blueprints.pedido_fornecedor import pedido_fornecedor_bp
    app.register_blueprint(pedido_fornecedor_bp)

    # Blueprint: Transferencias entre Lojas
    from app.blueprints.transferencias import transferencias_bp
    app.register_blueprint(transferencias_bp)

    # Blueprint: Pedido Manual
    from app.blueprints.pedido_manual import pedido_manual_bp
    app.register_blueprint(pedido_manual_bp)

    # Blueprint: KPIs
    from app.blueprints.kpis import kpis_bp
    app.register_blueprint(kpis_bp)

    # Blueprint: Visualizacao de Demanda
    from app.blueprints.visualizacao import visualizacao_bp
    app.register_blueprint(visualizacao_bp)

    # Blueprint: Previsao de Demanda (APIs)
    from app.blueprints.previsao import previsao_bp
    app.register_blueprint(previsao_bp)

    # Blueprint: Parametros de Fornecedor
    from app.blueprints.parametros import parametros_bp
    app.register_blueprint(parametros_bp)

    # Blueprint: Demanda Validada
    from app.blueprints.demanda_validada import demanda_validada_bp
    app.register_blueprint(demanda_validada_bp)

    # Blueprint: Pedido Planejado
    from app.blueprints.pedido_planejado import pedido_planejado_bp
    app.register_blueprint(pedido_planejado_bp)

    # Blueprint: Padrao de Compra
    from app.blueprints.padrao_compra import padrao_compra_bp
    app.register_blueprint(padrao_compra_bp)

    # Blueprint: Configuracao (Parametros Globais)
    from app.blueprints.configuracao import configuracao_bp
    app.register_blueprint(configuracao_bp)
