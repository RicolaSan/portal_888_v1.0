from flask import render_template, jsonify, request
from . import main
from app.controle_de_isv.routes import get_isv_data

@main.route('/')
def index():
    return render_template('base.html')

@main.route('/api/controle-isv')
def api_controle_isv():
    """
    Endpoint para obter dados ISV usando a função centralizada do controle_de_isv
    """
    # Obter parâmetros de filtro da requisição
    search = request.args.get('search', '')
    dias_filter = request.args.get('dias', '3')
    
    # Chamar a função centralizada
    resultado = get_isv_data(search=search, dias_filter=dias_filter)
    
    # Retornar resposta baseada no resultado
    if resultado['success']:
        return jsonify(resultado)
    else:
        return jsonify({'error': resultado['error']}), 500

