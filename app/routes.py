# from flask import Blueprint, render_template
# from datetime import datetime

# # Crear un Blueprint para las rutas principales
# main_bp = Blueprint('main', __name__)

# @main_bp.route('/')
# def menu_principal():
#     companias = ['Antucoya', 'Centinela Oxido', 'Centinela Sulfuro', 'Los Pelambres', 'Zaldivar']
#     current_date = datetime.now().strftime("%d/%m/%Y")
#     return render_template('menu_principal.html', companias=companias, current_date=current_date)