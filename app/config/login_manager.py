import base64
import json
import requests
from flask import Blueprint, request, g, current_app
from flask_login import LoginManager, login_user, UserMixin

login_manager_bp = Blueprint('login_manager_bp', __name__)
login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, id, name, email, last_sign_in, role):
        self.id = id
        self.name = name
        self.email = email
        self.last_sign_in = last_sign_in
        self.role = role

    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@login_manager_bp.before_app_request
def get_user_email():
    g.user_email = request.headers.get('X-MS-CLIENT-PRINCIPAL-NAME')
    user_info_encoded = request.headers.get('X-MS-CLIENT-PRINCIPAL')

    if user_info_encoded:
        user_info_json = base64.b64decode(user_info_encoded).decode('utf-8')
        user_info = json.loads(user_info_json)
        user_name = user_info.get('name', 'Invitado')

    else:
        user_name = "Invitado"

    if g.user_email:
        user_info = get_user_info(g.user_email)
        if user_info:
            user = User(
                id=user_info["id"],
                name=user_info["name"],
                email=user_info["email"],
                last_sign_in=user_info["last_sign_in"],
                role=user_info["role"]
            )
        else:
            user = User(
                id="0",
                name=user_name,
                email="guest@example.com",
                last_sign_in="None",
                role="guest"
            )
        login_user(user)
    else:
        # Handle guest user case
        user = User(
            id="0",
            name=user_name,
            email="guest@example.com",
            last_sign_in="None",
            role="guest"
        )
        login_user(user)

def get_user_info(email):
    backend_url = current_app.config.get('BACKEND_URL')
    if not backend_url:
        return None
    try:
        response = requests.get(f'{backend_url}/users/email/{email}')
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, ValueError):
        return None
