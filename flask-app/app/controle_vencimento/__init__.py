from flask import Blueprint

controle_vencimento = Blueprint('controle_vencimento', __name__,
                                template_folder='templates',
                                static_folder='static',)

from . import routes
