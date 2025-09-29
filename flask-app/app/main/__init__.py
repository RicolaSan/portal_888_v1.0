from flask import Blueprint

# Configurar o blueprint com static_url_path específico
main = Blueprint('main', __name__, 
                template_folder='templates',
                static_folder='static',
                static_url_path='/main/static')

from app.main import routes