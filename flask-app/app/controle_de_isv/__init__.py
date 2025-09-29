from flask import Blueprint

controle_de_isv_bp = Blueprint('controle_de_isv', __name__,
                                template_folder='templates',
                                static_folder='static',
                                )
from . import routes
