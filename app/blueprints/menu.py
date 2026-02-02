"""
Blueprint: Menu
Rotas principais do sistema: /, /menu, /download/<filename>
"""

import os
from flask import Blueprint, render_template, send_file, jsonify, current_app

menu_bp = Blueprint('menu', __name__)


@menu_bp.route('/menu')
def menu():
    """Menu principal - Capa do sistema"""
    return render_template('menu.html')


@menu_bp.route('/')
def index():
    """Pagina de previsao de demanda"""
    return render_template('index.html')


@menu_bp.route('/download/<filename>')
def download_file(filename):
    """Download do arquivo Excel gerado ou exemplo"""
    # Primeiro tenta na pasta de outputs
    filepath = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)

    # Se nao encontrar, tenta na raiz (arquivos de exemplo)
    if not os.path.exists(filepath):
        filepath = filename

    if not os.path.exists(filepath):
        return jsonify({'erro': 'Arquivo nao encontrado'}), 404

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
