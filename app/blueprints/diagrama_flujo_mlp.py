from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, session, jsonify, current_app
from app.utils.utils import generar_saludo

diagflujo_mlp_bp = Blueprint('diagrama_flujo_mlp', __name__)


@diagflujo_mlp_bp.route('/diagramaflujomlp', methods=['GET', 'POST'])
def balance_agua_mlp():

    return render_template('diagrama_flujo_mlp.html')
