import os
import io
import logging
from flask import Flask, render_template, session, request, redirect, jsonify, send_file, Response
from flask_cors import CORS
from flask_caching import Cache
from flask_login import LoginManager, UserMixin, login_user, login_required
from dotenv import load_dotenv
from datetime import datetime
from app.database.cosmos_client import CosmosClientWrapper
from app.blueprints.home import home_bp
from app.blueprints.balance_icmm import balance_icmm_bp
from app.blueprints.diagrama_flujo_ant import diagflujo_ant_bp
from app.blueprints.diagrama_flujo_cmz import diagflujo_cmz_bp
from app.blueprints.diagrama_flujo_mlp import diagflujo_mlp_bp

# Cargar variables de entorno desde el archivo .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path, override=True)

# Definir el modelo de usuario
class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

def create_flask_app():
    try:
        # Inicializar la aplicación Flask
        app = Flask(__name__)
        app.secret_key = os.getenv('SECRET_KEY') or os.urandom(24)

        # Habilitar CORS
        CORS(app)

        # Configurar la caché
        cache_config = {
            'CACHE_TYPE': os.getenv('CACHE_TYPE', 'SimpleCache'),
            'CACHE_DEFAULT_TIMEOUT': int(os.getenv('CACHE_TIMEOUT', 300))
        }
        cache = Cache(config=cache_config)
        cache.init_app(app)
        app.cache = cache

        # Configurar logging
        logger = logging.getLogger(__name__)
        log_level = logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO
        logger.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Archivo de log
        file_handler = logging.FileHandler('app.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info("Initializing the Flask application.")

        # Configuración de autenticación
        login_manager = LoginManager()
        login_manager.init_app(app)

        # Definir un user_loader
        @login_manager.user_loader
        def load_user(user_id):
            user_email = session.get('user_email')
            if user_email:
                return User(user_id, user_email)
            return None

        # Definir un request_loader
        @login_manager.request_loader
        def load_user_from_request(request):
            user_email = request.headers.get('X-MS-CLIENT-PRINCIPAL-NAME')
            if user_email:
                user_id = user_email.split('@')[0]
                return User(user_id, user_email)
            return None
        
        # Registra Blueprints
        app.register_blueprint(home_bp)
        app.register_blueprint(balance_icmm_bp)
        app.register_blueprint(diagflujo_ant_bp)
        app.register_blueprint(diagflujo_cmz_bp)
        app.register_blueprint(diagflujo_mlp_bp)

        @app.context_processor
        def inject_href():
            if request.method == 'POST':
                selected_company = request.form.get('persisted-compania')
                session['persisted-compania'] = selected_company  # Guardamos la selección en la sesión
            else:
                selected_company = session.get('persisted-compania', 'Antucoya')  

            # Mapear href
            href_mapping = {
                'Antucoya': '/diagramaflujoant',
                'Centinela Oxido': '/',
                'Centinela Sulfuro': '/',
                'Los Pelambres': '/diagramaflujomlp',
                'Zaldivar': '/diagramaflujocmz',
            }
            href = href_mapping.get(selected_company, '/')

            # Inyectar el href como variable global
            return {'href_layout': href}
        


        # Descarga Excel
        # @app.route('/download/excel', methods=['GET'])
        # def download_excel():
        #     import xlsxwriter
            
        #     # Obtener la compañía seleccionada del formulario
        #     if request.method == 'POST':
        #         selected_company = request.form.get('persisted-compania')
        #         session['persisted-compania'] = selected_company  # Guardamos la selección en la sesión
        #     else:
        #         selected_company = session.get('persisted-compania', 'Antucoya')  

        #     # Obtener los datos desde CosmosDB
        #     df_combined = obtener_datos_cosmos_icmm(app)
            
        #     # Obtener valores seleccionados desde el formulario
        #     compania = selected_company
        #     mes = request.form.get('filtro_mes', '')
        #     anio = request.form.get('filtro_anio', '')
        #     mtd_ytd_switch = request.form.get('filtro_temp', '')  # "on" si está activado, "" si no
        #     temporalidad = 'YTD' if mtd_ytd_switch == "on" else 'MTD'

        #     print(compania)
        #     print(mes)
        #     print(anio)
        #     print(temporalidad)

        #     # Filtrar los datos según los criterios seleccionados
        #     datos_filtrados = [
        #         row for row in df_combined
        #         if (not compania or row.get('compania') == compania) and
        #         (not mes or row.get('mes', '') == mes) and
        #         (not anio or row.get('anio', '') == anio) and 
        #         (not temporalidad or row.get('temporalidad') == mtd_ytd_switch)
        #     ]

        #     # Crear archivo Excel
        #     excel_io = io.BytesIO()
        #     workbook = xlsxwriter.Workbook(excel_io, {'in_memory': True})
        #     worksheet = workbook.add_worksheet('TablaICMM')

        #     # Escribir los encabezados
        #     headers = ['fecha', 'compania', 'tipo_agua', 'metrica', 'fuente_destino', 'calidad_agua', 'valor', 'temporalidad']
        #     for col_num, header in enumerate(headers):
        #         worksheet.write(0, col_num, header)

        #     # Escribir los datos filtrados
        #     for row_num, row in enumerate(datos_filtrados, start=1):
        #         worksheet.write(row_num, 0, row.get('fecha', ''))
        #         worksheet.write(row_num, 1, row.get('compania', ''))
        #         worksheet.write(row_num, 2, row.get('tipo_agua', ''))
        #         worksheet.write(row_num, 3, row.get('metrica', ''))
        #         worksheet.write(row_num, 4, row.get('fuente_destino', ''))
        #         worksheet.write(row_num, 5, row.get('calidad_agua', ''))
        #         worksheet.write(row_num, 6, row.get('valor', ''))
        #         worksheet.write(row_num, 7, row.get('temporalidad', ''))

        #     # Guardar el archivo y devolverlo
        #     workbook.close()
        #     excel_io.seek(0)

        #     return send_file(
        #         excel_io,
        #         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        #         as_attachment=True,
        #         download_name='tablaicmm.xlsx'
        #     )

        #Script de descarga excel modificado.
        # @app.route('/download/excel')
        # def download_excel():
        #     import xlsxwriter

        #     # Crear archivo Excel
        #     excel_io = io.BytesIO()
        #     workbook = xlsxwriter.Workbook(excel_io, {'in_memory': True})
        #     worksheet = workbook.add_worksheet('TablaICMM')

        #     # Escribir encabezados y datos
        #     headers = ['Tipo de Agua', 'Métrica', 'Fuente/Destino', 'Calidad Alta', 'Calidad Baja', 'Total']
        #     data = [
        #         ['Agua Operacional', 'Extracción/Captación', 'Agua Superficial', 1, 2, 3],
        #         ['Agua Operacional', 'Extracción/Captación', 'Agua Subterránea', '', '', ''],
        #         ['Agua Operacional', 'Extracción/Captación', 'Agua de Mar', '', '', ''],
        #         ['Agua Operacional', 'Extracción/Captación', 'Agua de Terceros', '', '', ''],
        #     ]

        #     for col_num, header in enumerate(headers):
        #         worksheet.write(0, col_num, header)

        #     for row_num, row_data in enumerate(data, start=1):
        #         for col_num, cell_data in enumerate(row_data):
        #             worksheet.write(row_num, col_num, cell_data)

        #     workbook.close()
        #     excel_io.seek(0)

        #     return send_file(excel_io, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='tablaicmm.xlsx')


        # Configurar conexión a Cosmos DB (si las credenciales están disponibles)
        cosmos_credentials = {
            "COSMOSDB_URI": os.getenv("COSMOSDB_URI"),
            "COSMOSDB_KEY": os.getenv("COSMOSDB_KEY"),
            "DATABASE_NAME": os.getenv("DATABASE_NAME"),
            "PH_CMZ": os.getenv("PH_CMZ"),
            "PH_MLP": os.getenv("PH_MLP"),
            "PH_ANT": os.getenv("PH_ANT")
        }

        if cosmos_credentials["COSMOSDB_URI"] and cosmos_credentials["COSMOSDB_KEY"]:
            cosmos_client_wrapper = CosmosClientWrapper(
                cosmosdb_uri=cosmos_credentials["COSMOSDB_URI"],
                cosmosdb_key=cosmos_credentials["COSMOSDB_KEY"],
                database_name=cosmos_credentials["DATABASE_NAME"],
                ph_cmz=cosmos_credentials["PH_CMZ"],
                ph_mlp=cosmos_credentials["PH_MLP"],
                ph_ant=cosmos_credentials["PH_ANT"],
            )
            app.config['COSMOS_CLIENT'] = cosmos_client_wrapper
        else:
            logger.warning("Cosmos DB credentials not found. DB features may not work.")

        app.config['COSMOS_CREDENTIALS'] = cosmos_credentials

        return app

    except Exception as e:
        logger.exception("An error occurred while creating the Flask app.")
        raise e