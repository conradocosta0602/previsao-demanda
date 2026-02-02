"""
Sistema de Previsao de Demanda - Ponto de Entrada
Utiliza factory pattern para criar a aplicacao Flask com blueprints modulares.

Para executar:
    python app.py

Ou com Flask CLI:
    flask run --debug
"""

import os
from app import create_app


# Criar instancia da aplicacao usando factory pattern
app = create_app()


if __name__ == '__main__':
    # Configurar modo de debug baseado em variavel de ambiente
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

    # Executar servidor de desenvolvimento
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=debug_mode
    )
