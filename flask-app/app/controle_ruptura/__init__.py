from flask import Blueprint

controle_ruptura = Blueprint('controle_ruptura', __name__,
                                template_folder='templates',
                                static_folder='static',)

from . import routes

