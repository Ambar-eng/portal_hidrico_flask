from datetime import datetime
from flask import Blueprint, render_template, request, session, jsonify
from app.utils.utils import generar_saludo
from app.utils.utils import get_href_mapping

home_bp = Blueprint('home', __name__)

@home_bp.route('/', methods=['GET', 'POST'])
def home():
    companias = ['Antucoya', 'Centinela Oxido', 'Centinela Sulfuro', 'Los Pelambres', 'Zaldivar']
    current_date = datetime.now().strftime("%d/%m/%Y")
    saludo = generar_saludo()

    # Obtener la compañía seleccionada del formulario
    if request.method == 'POST':
        selected_company = request.form.get('persisted-compania')
        session['persisted-compania'] = selected_company  # Guardamos la selección en la sesión
    else:
        # Si no se ha seleccionado, se conserva lo que está en la sesión
        # Si no hay valor en la sesión, se asigna el valor por defecto "Antucoya"
        selected_company = session.get('persisted-compania', 'Antucoya')  

    # Determinar el href basado en la compañía seleccionada
    href = get_href_mapping().get(selected_company, '/')

    return render_template('home.html', companias=companias, current_date=current_date, saludo=saludo, href=href, selected_company=selected_company)


@home_bp.route('/actualizar-compania', methods=['POST'])
def actualizar_compania():
    data = request.get_json()  # Leer los datos enviados por fetch
    if 'compania' in data:
            session['persisted-compania'] = data['compania']  # Actualizar la sesión
            return jsonify({"success": True}), 200
    return jsonify({"error": "Compañía no especificada"}), 400