from flask import Flask
from app.main import main as main_blueprint
from app.controle_de_isv import controle_de_isv_bp as controle_de_isv_blueprint
from app.controle_vencimento import controle_vencimento as controle_vencimento_blueprint
from app.controle_de_perdas import controle_de_perdas as controle_perdas_blueprint
from app.controle_ruptura import controle_ruptura as controle_ruptura_blueprint



def create_app():
    app = Flask(__name__)
    
    app.register_blueprint(main_blueprint)
    app.register_blueprint(controle_de_isv_blueprint, url_prefix='/controle-isv')
    app.register_blueprint(controle_vencimento_blueprint, url_prefix='/controle-vencimento')
    app.register_blueprint(controle_perdas_blueprint, url_prefix='/controle-perdas')
    app.register_blueprint(controle_ruptura_blueprint, url_prefix='/controle-ruptura')
    
    return app