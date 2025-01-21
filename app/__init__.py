import os
import io
import logging
from flask import Flask, render_template, session, request, redirect, jsonify, send_file, Response
from flask_cors import CORS
from flask_caching import Cache
from flask_login import LoginManager, UserMixin, login_user, login_required
from dotenv import load_dotenv
from datetime import datetime
# from app.blueprints.auth import get_microsoft_user_info
# from app.blueprints.auth import login_manager_bp
from app.utils.utils import generar_saludo
from app.utils.utils import get_href_mapping
from app.utils.utils import obtener_datos_cosmos_icmm
from app.utils.utils import obtener_fecha_maxima_icmm
from app.utils.utils import obtener_mensaje_fecha
from app.utils.utils import procesar_datos_icmm
from app.utils.utils import procesar_datos_icmm_delta_perc
from app.utils.utils_diagflujo_ant import toggle_rows_logic_ant
from app.utils.utils_diagflujo_ant import obtener_datos_cosmos_diag_ant
from app.utils.utils_diagflujo_ant import obtener_fecha_maxima_diag_ant
from app.utils.utils_diagflujo_ant import obtener_mensaje_fecha_diag_ant
from app.utils.utils_diagflujo_ant import procesar_datos_diag_ant
from app.utils.utils_diagflujo_cmz import toggle_rows_logic_cmz
from app.utils.utils_diagflujo_cmz import obtener_datos_cosmos_diag_cmz
from app.utils.utils_diagflujo_cmz import obtener_fecha_maxima_diag_cmz
from app.utils.utils_diagflujo_cmz import obtener_mensaje_fecha_diag_cmz
from app.utils.utils_diagflujo_cmz import procesar_datos_diag_cmz
from app.database.cosmos_client import CosmosClientWrapper

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
    
        # Página Home (/)
        @app.route('/', methods=['GET', 'POST'])
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
        

        @app.route('/actualizar-compania', methods=['POST'])
        def actualizar_compania():
            data = request.get_json()  # Leer los datos enviados por fetch
            if 'compania' in data:
                session['persisted-compania'] = data['compania']  # Actualizar la sesión
                return jsonify({"success": True}), 200
            return jsonify({"error": "Compañía no especificada"}), 400
        


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


        # Página Balance ICMM
        @app.route('/balanceicmm', methods=['GET', 'POST'])
        def tabla_icmm():
            meses = ['Enero', 'Febrero','Marzo','Abril', 'Mayo', 'Junio', 'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
            anios = ['2023', '2024', '2025']
            saludo = generar_saludo()
            
            # Obtener la compañía seleccionada del formulario
            if request.method == 'POST':
                selected_company = request.form.get('persisted-compania')
                session['persisted-compania'] = selected_company  # Guardamos la selección en la sesión
            else:
                # Si no se ha seleccionado, se conserva lo que está en la sesión
                # Si no hay valor en la sesión, se asigna el valor por defecto "Antucoya"
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
                
            # selected_company = session.get('persisted-compania')
            df_combined = obtener_datos_cosmos_icmm(app)
            fecha_maxima = obtener_fecha_maxima_icmm(df_combined)
            mensaje_fecha = obtener_mensaje_fecha(fecha_maxima)

            # Obtener valores seleccionados desde el formulario
            compania = selected_company
            mes = request.form.get('filtro_mes', '')
            anio = request.form.get('filtro_anio', '')
            mtd_ytd_switch = request.form.get('filtro_temp', '')  # "on" si está activado, "" si no
            temporalidad = 'YTD' if mtd_ytd_switch == "on" else 'MTD'

            # Llamar a la función de utils.py para procesar los datos
            datos = procesar_datos_icmm(app, compania, mes, anio, temporalidad)

            # Procesar datos para delta balance baja
            db_delta_balance_baja, style_delta = procesar_datos_icmm_delta_perc(app, compania, mes, anio, mtd_ytd_switch)

            return render_template('balance_icmm.html', selected_company=selected_company, meses=meses, anios=anios, saludo=saludo, href=href, mensaje_fecha=mensaje_fecha, 
                                datos=datos, db_delta_balance_baja=db_delta_balance_baja, style_delta=style_delta)
        
        
        @app.route('/toggle_rows_ant', methods=['POST'])
        def toggle_rows_ant():
            data = request.json
            return toggle_rows_logic_ant(data)
        
        @app.route('/toggle_rows_cmz', methods=['POST'])
        def toggle_rows_cmz():
            data = request.json
            return toggle_rows_logic_cmz(data)
        
        
        # Página Balance Agua ANT
        @app.route('/diagramaflujoant', methods=['GET', 'POST'])
        def balance_agua_ant():
            df_ph_ant = obtener_datos_cosmos_diag_ant(app)
            fecha_maxima_ant = obtener_fecha_maxima_diag_ant(df_ph_ant)
            mensaje_fecha_ant = obtener_mensaje_fecha_diag_ant(fecha_maxima_ant)

            # Obtener valores seleccionados desde el formulario
            fecha = request.form.get('filtro_fecha_ant', None)

            # Si la fecha no está seleccionada, permanece como None
            if fecha:
                try:
                    # Validar el formato de la fecha
                    fecha = datetime.strptime(fecha, '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    # Si la fecha no tiene el formato correcto, manejar el error (opcional)
                    fecha = None

            ant_temp_switch = request.form.get('filtro_temp_ant', '')  # "on" si está activado, "" si no
            ant_temporalidad = 'Mes' if ant_temp_switch == "on" else 'Dia'
            ant_medida_switch = request.form.get('filtro_medida_ant', '')
            ant_medida= 'l/s' if ant_medida_switch == "on" else 'm3/h'

            # print("Fecha:", fecha)
            # print("Temp:", ant_temporalidad)
            # print("Medida:", ant_medida)

            datos_ant = procesar_datos_diag_ant(app, fecha, ant_temporalidad, ant_medida)

            return render_template('diagrama_flujo_ant.html', mensaje_fecha_ant=mensaje_fecha_ant, fecha=fecha, ant_temporalidad=ant_temporalidad, ant_medida=ant_medida,
                                   datos_ant=datos_ant)
        

        # Página Balance Agua CMZ
        @app.route('/diagramaflujocmz', methods=['GET', 'POST'])
        def balance_agua_cmz():
            df_ph_cmz = obtener_datos_cosmos_diag_cmz(app)
            fecha_maxima_cmz = obtener_fecha_maxima_diag_cmz(df_ph_cmz)
            mensaje_fecha_cmz = obtener_mensaje_fecha_diag_cmz(fecha_maxima_cmz)

            # Obtener valores seleccionados desde el formulario
            fecha = request.form.get('filtro_fecha_cmz', None)

            # Si la fecha no está seleccionada, permanece como None
            if fecha:
                try:
                    # Validar el formato de la fecha
                    fecha = datetime.strptime(fecha, '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    # Si la fecha no tiene el formato correcto, manejar el error (opcional)
                    fecha = None

            cmz_temp_switch = request.form.get('filtro_temp_cmz', '')  # "on" si está activado, "" si no
            cmz_temporalidad = 'Mes' if cmz_temp_switch == "on" else 'Dia'
            cmz_medida_switch = request.form.get('filtro_medida_cmz', '')
            cmz_medida= 'l/s' if cmz_medida_switch == "on" else 'm3/h'

            datos_cmz = procesar_datos_diag_cmz(app, fecha, cmz_temporalidad, cmz_medida)
         
			#print("Fecha:", fecha)
            #print("Temp:", cmz_temporalidad)
            #print("Medida:", cmz_medida)

            return render_template('diagrama_flujo_cmz.html', mensaje_fecha_cmz=mensaje_fecha_cmz, fecha=fecha, cmz_temporalidad=cmz_temporalidad, cmz_medida=cmz_medida,
                                   datos_cmz=datos_cmz)
        

        
        # Página Balance Agua MLP
        @app.route('/diagramaflujomlp', methods=['GET', 'POST'])
        def balance_agua_mlp():
            # df_ph_mlp = obtener_datos_cosmos_diag_mlp(app)
            # fecha_maxima_mlp = obtener_fecha_maxima_diag_mlp(df_ph_mlp)
            # mensaje_fecha_mlp = obtener_mensaje_fecha_diag_mlp(fecha_maxima_mlp)

            # Obtener valores seleccionados desde el formulario
            fecha = request.form.get('filtro_fecha_mlp', None)

            # Si la fecha no está seleccionada, permanece como None
            if fecha:
                try:
                    # Validar el formato de la fecha
                    fecha = datetime.strptime(fecha, '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    # Si la fecha no tiene el formato correcto, manejar el error (opcional)
                    fecha = None

            mlp_temp_switch = request.form.get('filtro_temp_mlp', '')  # "on" si está activado, "" si no
            mlp_temporalidad = 'Mes' if mlp_temp_switch == "on" else 'Dia'
            mlp_medida_switch = request.form.get('filtro_medida_mlp', '')
            mlp_medida= 'l/s' if mlp_medida_switch == "on" else 'm3/h'
         
			#print("Fecha:", fecha)
            #print("Temp:", mlp_temporalidad)
            #print("Medida:", mlp_medida)

            return render_template('diagrama_flujo_mlp.html', #mensaje_fecha_mlp=mensaje_fecha_mlp, 
                                   fecha=fecha, mlp_temporalidad=mlp_temporalidad, mlp_medida=mlp_medida)

        # @app.route('/download/png')
        # def download_png():
        #     from PIL import Image, ImageDraw

        #     # Generar imagen PNG
        #     img = Image.new('RGB', (600, 400), color='white')
        #     d = ImageDraw.Draw(img)
        #     d.text((10, 10), "Tabla ICMM - Imagen de ejemplo", fill=(0, 0, 0))

        #     # Guardar en memoria
        #     img_io = io.BytesIO()
        #     img.save(img_io, 'PNG')
        #     img_io.seek(0)

        #     return send_file(img_io, mimetype='image/png', as_attachment=True, download_name='tablaicmm.png')

        @app.route('/download/excel', methods=['GET'])
        def download_excel():
            import xlsxwriter
            
            # Obtener la compañía seleccionada del formulario
            if request.method == 'POST':
                selected_company = request.form.get('persisted-compania')
                session['persisted-compania'] = selected_company  # Guardamos la selección en la sesión
            else:
                selected_company = session.get('persisted-compania', 'Antucoya')  

            # Obtener los datos desde CosmosDB
            df_combined = obtener_datos_cosmos_icmm(app)
            
            # Obtener valores seleccionados desde el formulario
            compania = selected_company
            mes = request.form.get('filtro_mes', '')
            anio = request.form.get('filtro_anio', '')
            mtd_ytd_switch = request.form.get('filtro_temp', '')  # "on" si está activado, "" si no
            temporalidad = 'YTD' if mtd_ytd_switch == "on" else 'MTD'

            print(compania)
            print(mes)
            print(anio)
            print(temporalidad)

            # Filtrar los datos según los criterios seleccionados
            datos_filtrados = [
                row for row in df_combined
                if (not compania or row.get('compania') == compania) and
                (not mes or row.get('mes', '') == mes) and
                (not anio or row.get('anio', '') == anio) and 
                (not temporalidad or row.get('temporalidad') == mtd_ytd_switch)
            ]

            # Crear archivo Excel
            excel_io = io.BytesIO()
            workbook = xlsxwriter.Workbook(excel_io, {'in_memory': True})
            worksheet = workbook.add_worksheet('TablaICMM')

            # Escribir los encabezados
            headers = ['fecha', 'compania', 'tipo_agua', 'metrica', 'fuente_destino', 'calidad_agua', 'valor', 'temporalidad']
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header)

            # Escribir los datos filtrados
            for row_num, row in enumerate(datos_filtrados, start=1):
                worksheet.write(row_num, 0, row.get('fecha', ''))
                worksheet.write(row_num, 1, row.get('compania', ''))
                worksheet.write(row_num, 2, row.get('tipo_agua', ''))
                worksheet.write(row_num, 3, row.get('metrica', ''))
                worksheet.write(row_num, 4, row.get('fuente_destino', ''))
                worksheet.write(row_num, 5, row.get('calidad_agua', ''))
                worksheet.write(row_num, 6, row.get('valor', ''))
                worksheet.write(row_num, 7, row.get('temporalidad', ''))

            # Guardar el archivo y devolverlo
            workbook.close()
            excel_io.seek(0)

            return send_file(
                excel_io,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='tablaicmm.xlsx'
            )

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

        # Registrar los blueprints (si es necesario)
        # app.register_blueprint(login_manager_bp)

        return app

    except Exception as e:
        logger.exception("An error occurred while creating the Flask app.")
        raise e