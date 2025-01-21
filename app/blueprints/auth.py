import base64
import json
from flask import request, g, Blueprint, session

# Se define un Blueprint en Flask para organizar las rutas y funciones relacionadas con la autenticación.
login_manager_bp = Blueprint('login_manager_bp', __name__)

# Función que se ejecuta antes de cada solicitud para obtener información del usuario de las cabeceras HTTP
@login_manager_bp.before_app_request
def get_microsoft_user_info():

    # Se inicializa una cadena de logs para depuración
    g.logs = ""

    # Se obtiene el correo electrónico del usuario desde las cabeceras de la solicitud
    g.user_email = request.headers.get('X-MS-CLIENT-PRINCIPAL-NAME')
    g.logs += f"User email from headers: {g.user_email}\n" # Se agrega al log el correo del usuario

    # Se obtiene la cabecera con la información codificada del usuario
    user_info_encoded = request.headers.get('X-MS-CLIENT-PRINCIPAL')
    user_name = None # Variable para almacenar el nombre del usuario

    # Si se encuentra información del usuario en la cabecera
    if user_info_encoded:
        try:
            # Se decodifica la información codificada en base64 y se convierte a formato JSON
            user_info_json = base64.b64decode(user_info_encoded).decode('utf-8')
            user_info = json.loads(user_info_json) # Se convierte la cadena JSON en un diccionario
            g.logs += f"Full decoded user info: {user_info}\n" # Se agrega al log la información decodificada

            # Se busca el nombre del usuario en las "claims" (afirmaciones) dentro de la información del usuario
            for claim in user_info.get('claims', []):
                if claim['typ'] in ['name', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name']:
                    user_name = claim['val'] # Se asigna el nombre encontrado en la claim
                    g.logs += f"Found user name in claims: {user_name}\n" # Se agrega al log el nombre encontrado
                    break # Se termina el ciclo una vez encontrado el nombre

            # Si no se encuentra un nombre válido en las claims, se informa en los logs
            if not user_name:
                g.logs += "No valid name found in claims, falling back to email prefix.\n"

        # Si ocurre un error durante la decodificación o procesamiento de la información, se maneja la excepción
        except (ValueError, base64.binascii.Error) as e:
            g.logs += f"Error decoding user info header: {e}\n" # Se registra el error en los logs

    # Si no se encuentra un nombre de usuario en las claims, se utiliza el prefijo del correo electrónico
    if g.user_email and not user_name:
        user_name = g.user_email.split('@')[0] # Se usa la parte antes del "@" como nombre de usuario
        g.logs += f"Using email prefix as user name: {user_name}\n" # Se agrega al log el nombre generado

    # Se almacena el nombre de usuario en la sesión, para que esté disponible en otras partes de la aplicación
    session['username'] = user_name or "Invitado" # Si no se obtuvo nombre, se usa "Invitado"

    # Se retorna una tupla con el nombre de usuario y el correo del usuario (o "Invitado" si no se obtuvo nombre)
    return user_name or "Invitado", g.user_email