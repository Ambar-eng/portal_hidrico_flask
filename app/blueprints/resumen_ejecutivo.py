from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, session, jsonify, current_app
from app.utils.utils import generar_saludo

resumen_ej_bp = Blueprint('resumen_ejecutivo', __name__)


@resumen_ej_bp.route('/resumenejecutivo', methods=['GET', 'POST'])
def resumen_ejecutivo():

    return render_template('resumen_ejecutivo.html')