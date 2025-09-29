from flask import Blueprint

controle_de_perdas = Blueprint('controle_de_perdas', __name__,
                                template_folder='templates',
                                static_folder='static',)
from . import routes

