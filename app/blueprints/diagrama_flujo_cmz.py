from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, session, jsonify, current_app
from app.utils.utils import generar_saludo

diagflujo_cmz_bp = Blueprint('diagrama_flujo_cmz', __name__)


@diagflujo_cmz_bp.route('/diagramaflujocmz', methods=['GET', 'POST'])
def balance_agua_cmz():
    df_ph_cmz = obtener_datos_cosmos_diag_cmz()
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

    datos_cmz = procesar_datos_diag_cmz(fecha, cmz_temporalidad, cmz_medida)

    return render_template('diagrama_flujo_cmz.html', mensaje_fecha_cmz=mensaje_fecha_cmz, fecha=fecha, cmz_temporalidad=cmz_temporalidad, cmz_medida=cmz_medida,
                            datos_cmz=datos_cmz)


@diagflujo_cmz_bp.route('/toggle_rows_cmz', methods=['POST'])
def toggle_rows_cmz():
    data = request.json
    return toggle_rows_logic_cmz(data)


def obtener_datos_cosmos_diag_cmz():

    print(f"Momento Inicial 1: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

    app = current_app._get_current_object()
    cache = app.cache

    #Obtener los datos de la caché para Antucoya
    df_ph_cmz = cache.get('ph_cmz_data')
    if df_ph_cmz is None:
        cosmos_client = app.config['COSMOS_CLIENT']
        df_ph_cmz = cosmos_client.get_items_from_container(
            'PH_CMZ', 
            'amsa_datos_hidricos_web.dmt_cmz_reporte_hidrico_flujo'
        )
        print(f"Momento Inicial cache 1: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        cache.set('ph_cmz_data', df_ph_cmz, timeout=3600)
        print(f"Momento Inicial cache 2: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

    # Intentar obtener los datos actuales de la caché para combinarlos
    cached_data = cache.get('ph_cmz_data')

    # Si la caché no tiene datos, iniciamos una lista vacía
    if cached_data is None:
        cached_data = []

    # Filtrar duplicados antes de agregar los nuevos datos a la caché
    fechas_en_cache = {dato['fecha'] for dato in cached_data}
    df_ph_cmz = [dato for dato in df_ph_cmz if dato['fecha'] not in fechas_en_cache]

    # Guardar los datos combinados (actualizados) en la caché, sin duplicados
    cache.set('ph_cmz_data', cached_data + df_ph_cmz, timeout=3600)
    
    print(f"Momento Inicial 2: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")

    return cached_data + df_ph_cmz


#Función para obtener la fecha máxima
def obtener_fecha_maxima_diag_cmz(datos):
    if datos:
        # Obtener todas las fechas
        fechas = [dato['fecha'] for dato in datos if 'fecha' in dato]
        
        if fechas:
            # Convertir las fechas a objetos datetime y calcular la fecha máxima
            fecha_maxima = max(datetime.strptime(fecha, '%Y-%m-%d') for fecha in fechas)
            return fecha_maxima
    return None

#Función para actualizar la fecha de actualización
def obtener_mensaje_fecha_diag_cmz(fecha_maxima):
    if fecha_maxima:
        fecha_formateada = fecha_maxima.strftime('%d-%m-%Y')
        return f"Actualizado con datos hasta {fecha_formateada}"
    else:
        return "No se encontraron datos para mostrar"
    

def procesar_datos_diag_cmz(fecha, cmz_temporalidad, cmz_medida):
    app = current_app._get_current_object()

    # Validar que fecha no sea nula o vacía
    if not fecha:
        # Retornar valores predeterminados si los valores son nulos
        return tuple("0" for _ in range(210)) 

    # Consultar la caché
    df_ph_cmz = app.cache.get('ph_cmz_data')
    if not df_ph_cmz:
        df_ph_cmz = []

    print(f"Datos iniciales en caché: {len(df_ph_cmz)}")
    
    fecha_presente = any(item['fecha'] == fecha for item in df_ph_cmz) # Debería devolver true or false
    print(f'La fecha {fecha} está en caché inicial?: {fecha_presente}')  

    if not fecha_presente and fecha :
        print("Consultando datos cosmos")
        cosmos_client = app.config['COSMOS_CLIENT']
        nuevos_datos = cosmos_client.get_items_from_container(
            'PH_CMZ', 
            'amsa_datos_hidricos_web.dmt_cmz_reporte_hidrico_flujo',
            fecha,
            fecha
        ) 

        # Combinar datos nuevos con los existentes
        df_ph_cmz += nuevos_datos
        print(f"Nuevos datos a agregar a la caché: {len(nuevos_datos)}")

        # Actualizar la caché
        app.cache.set('ph_cmz_data', df_ph_cmz, timeout=3600)
        print(f'Actualización de caché realizada con {len(nuevos_datos)} nuevos registros.')

        df_ph_cmz = app.cache.get('ph_cmz_data')

    datos_filtrados = [
        dato for dato in df_ph_cmz
        if dato.get('fecha') == fecha
        and dato.get('temporalidad') == cmz_temporalidad
        and dato.get('medida') == cmz_medida
    ]

    # Función para obtener un valor específico de los datos filtrados
    def filtrar_valor(datos, flujo, plan):
        datos_filtrados = [
            dato for dato in datos
            if dato.get('flujo') == flujo
            and dato.get('plan') == plan
        ]
        return str(datos_filtrados[0]['valor']) if datos_filtrados else "0"

    #Tabla Flujo A 
    tb_agua_negrillar_a_agua_nueva_cmz = filtrar_valor(datos_filtrados, "A", "Real")
    tb_agua_negrillar_a_agua_nueva_proy_cmz = filtrar_valor(datos_filtrados, "A", "Proyectado")
    agua_negrillar_a_agua_nueva_cmz = tb_agua_negrillar_a_agua_nueva_cmz #Flujo

    #Tabla Flujo A.1
    tb_extrac_ls_p1_dga_cmz = filtrar_valor(datos_filtrados, "A.1", "Real")
    tb_extrac_ls_p1_dga_proy_cmz = filtrar_valor(datos_filtrados, "A.1", "Proyectado")

    #Tabla Flujo A.2
    tb_extrac_ls_p2_dga_cmz = filtrar_valor(datos_filtrados, "A.2", "Real")
    tb_extrac_ls_p2_dga_proy_cmz = filtrar_valor(datos_filtrados, "A.2", "Proyectado")
        
    #Tabla Flujo A.3
    tb_extrac_ls_p3_dga_cmz = filtrar_valor(datos_filtrados, "A.3", "Real")
    tb_extrac_ls_p3_dga_proy_cmz = filtrar_valor(datos_filtrados, "A.3", "Proyectado")

    #Tabla Flujo A.4
    tb_extrac_ls_p4_dga_cmz = filtrar_valor(datos_filtrados, "A.4", "Real")
    tb_extrac_ls_p4_dga_proy_cmz = filtrar_valor(datos_filtrados, "A.4", "Proyectado")

    #Tabla Flujo A.5
    tb_extrac_ls_p5_dga_cmz = filtrar_valor(datos_filtrados, "A.5", "Real")
    tb_extrac_ls_p5_dga_proy_cmz = filtrar_valor(datos_filtrados, "A.5", "Proyectado")

    #Tabla Flujo A.6
    tb_extrac_ls_p6_dga_cmz = filtrar_valor(datos_filtrados, "A.6", "Real")
    tb_extrac_ls_p6_dga_proy_cmz = filtrar_valor(datos_filtrados, "A.6", "Proyectado")

    #Tabla Flujo B
    tb_agua_mineral_a_area_seca_cmz = filtrar_valor(datos_filtrados, "B", "Real")
    tb_agua_mineral_a_area_seca_proy_cmz = filtrar_valor(datos_filtrados, "B", "Proyectado")
    agua_mineral_a_area_seca_cmz = tb_agua_mineral_a_area_seca_cmz #Flujo

    #Tabla Flujo B.1
    tb_humedad_mineral_hl_cmz = filtrar_valor(datos_filtrados, "B.1", "Real")
    tb_humedad_mineral_hl_proy_cmz = filtrar_valor(datos_filtrados, "B.1", "Proyectado")

    #Tabla Flujo B.2
    tb_humedad_mineral_dl_cmz = filtrar_valor(datos_filtrados, "B.2", "Real")
    tb_humedad_mineral_dl_proy_cmz = filtrar_valor(datos_filtrados, "B.2", "Proyectado")

    #Tabla Flujo B.3
    tb_humedad_chancado_terciario_cmz = filtrar_valor(datos_filtrados, "B.3", "Real")
    tb_humedad_chancado_terciario_proy_cmz = filtrar_valor(datos_filtrados, "B.3", "Proyectado")

    #Tabla Flujo C
    tb_aguas_halladas_a_control_polvo_cmz = filtrar_valor(datos_filtrados, "C", "Real")
    tb_aguas_halladas_a_control_polvo_proy_cmz = filtrar_valor(datos_filtrados, "C", "Proyectado")
    aguas_halladas_a_control_polvo_cmz = tb_aguas_halladas_a_control_polvo_cmz

    #Tabla Flujo C.1
    tb_pozo22_cmz = filtrar_valor(datos_filtrados, "C.1", "Real")
    tb_pozo22_proy_cmz = filtrar_valor(datos_filtrados, "C.1", "Proyectado")

    #Tabla Flujo C.2
    tb_pozo25_cmz = filtrar_valor(datos_filtrados, "C.2", "Real")
    tb_pozo25_proy_cmz = filtrar_valor(datos_filtrados, "C.2", "Proyectado")

    #Tabla Flujo C.3
    tb_pozo26_cmz = filtrar_valor(datos_filtrados, "C.3", "Real")
    tb_pozo26_proy_cmz = filtrar_valor(datos_filtrados, "C.3", "Proyectado")

    #Tabla Flujo C.4
    tb_pozo27_cmz = filtrar_valor(datos_filtrados, "C.4", "Real")
    tb_pozo27_proy_cmz = filtrar_valor(datos_filtrados, "C.4", "Proyectado")

    #Tabla Flujo C.5
    tb_pozo28_cmz = filtrar_valor(datos_filtrados, "C.5", "Real")
    tb_pozo28_proy_cmz = filtrar_valor(datos_filtrados, "C.5", "Proyectado")

    #Tabla Flujo C.6
    tb_pozo29_cmz = filtrar_valor(datos_filtrados, "C.6", "Real")
    tb_pozo29_proy_cmz = filtrar_valor(datos_filtrados, "C.6", "Proyectado")

    #Tabla Flujo C.7
    tb_pozo30_cmz = filtrar_valor(datos_filtrados, "C.7", "Real")
    tb_pozo30_proy_cmz = filtrar_valor(datos_filtrados, "C.7", "Proyectado")

    #Tabla Flujo C.8
    tb_pozo31_cmz = filtrar_valor(datos_filtrados, "C.8", "Real")
    tb_pozo31_proy_cmz = filtrar_valor(datos_filtrados, "C.8", "Proyectado")

    #Tabla Flujo D
    tb_tsf_a_retencion_cmz = filtrar_valor(datos_filtrados, "D", "Real")
    tb_tsf_a_retencion_proy_cmz = filtrar_valor(datos_filtrados, "D", "Proyectado")
    tsf_a_retencion_cmz = tb_tsf_a_retencion_cmz

    #Tabla Flujo E
    tb_area_seca_a_retencion_cmz = filtrar_valor(datos_filtrados, "E", "Real")
    tb_area_seca_a_retencion_proy_cmz = filtrar_valor(datos_filtrados, "E", "Proyectado")
    area_seca_a_retencion_cmz = tb_area_seca_a_retencion_cmz

    #Tabla Flujo E.1
    tb_retencion_hl_cmz = filtrar_valor(datos_filtrados, "E.1", "Real")
    tb_retencion_hl_proy_cmz = filtrar_valor(datos_filtrados, "E.1", "Proyectado")

    #Tabla Flujo E.2
    tb_retencion_dl_cmz = filtrar_valor(datos_filtrados, "E.2", "Real")
    tb_retencion_dl_proy_cmz = filtrar_valor(datos_filtrados, "E.2", "Proyectado")

    #Tabla Flujo E.3
    tb_retencion_ral_cmz = filtrar_valor(datos_filtrados, "E.3", "Real")
    tb_retencion_ral_proy_cmz = filtrar_valor(datos_filtrados, "E.3", "Proyectado")

    #Tabla Flujo E.4
    tb_perdidas_concentrado_cmz = filtrar_valor(datos_filtrados, "E.4", "Real")
    tb_perdidas_concentrado_proy_cmz = filtrar_valor(datos_filtrados, "E.4", "Proyectado")

    #Tabla Flujo F
    tb_tsf_a_evaporacion_cmz = filtrar_valor(datos_filtrados, "F", "Real")
    tb_tsf_a_evaporacion_proy_cmz = filtrar_valor(datos_filtrados, "F", "Proyectado")
    tsf_a_evaporacion_cmz = tb_tsf_a_evaporacion_cmz

    #Tabla Flujo G
    tb_area_seca_a_evaporacion_cmz = filtrar_valor(datos_filtrados, "G", "Real")
    tb_area_seca_a_evaporacion_proy_cmz = filtrar_valor(datos_filtrados, "G", "Proyectado")
    area_seca_a_evaporacion_cmz = tb_area_seca_a_evaporacion_cmz

    #Tabla Flujo G.1
    tb_evap_pilas_cmz = filtrar_valor(datos_filtrados, "G.1", "Real")
    tb_evap_pilas_proy_cmz = filtrar_valor(datos_filtrados, "G.1", "Proyectado")

    #Tabla Flujo G.1.1
    tb_evap_pila_hl_cmz = filtrar_valor(datos_filtrados, "G.1.1", "Real")
    tb_evap_pila_hl_proy_cmz = filtrar_valor(datos_filtrados, "G.1.1", "Proyectado")

    #Tabla Flujo G.1.2
    tb_evap_pila_dl_cmz = filtrar_valor(datos_filtrados, "G.1.2", "Real")
    tb_evap_pila_dl_proy_cmz = filtrar_valor(datos_filtrados, "G.1.2", "Proyectado")

    #Tabla Flujo G.1.3
    tb_evap_pila_ral_cmz = filtrar_valor(datos_filtrados, "G.1.3", "Real")
    tb_evap_pila_ral_proy_cmz = filtrar_valor(datos_filtrados, "G.1.3", "Proyectado")

    #Tabla Flujo G.2
    tb_evap_total_piscinas_cmz = filtrar_valor(datos_filtrados, "G.2", "Real")
    tb_evap_total_piscinas_proy_cmz = filtrar_valor(datos_filtrados, "G.2", "Proyectado")

    #Tabla Flujo G.2.1
    tb_evap_piscina_pls_cmz = filtrar_valor(datos_filtrados, "G.2.1", "Real")
    tb_evap_piscina_pls_proy_cmz = filtrar_valor(datos_filtrados, "G.2.1", "Proyectado")

    #Tabla Flujo G.2.2
    tb_evap_piscina_ils_cmz = filtrar_valor(datos_filtrados, "G.2.2", "Real")
    tb_evap_piscina_ils_proy_cmz = filtrar_valor(datos_filtrados, "G.2.2", "Proyectado")

    #Tabla Flujo G.2.3
    tb_evap_piscina_ref_superior_cmz = filtrar_valor(datos_filtrados, "G.2.3", "Real")
    tb_evap_piscina_ref_superior_proy_cmz = filtrar_valor(datos_filtrados, "G.2.3", "Proyectado")

    #Tabla Flujo G.2.4
    tb_evap_piscina_ref_inferior_cmz = filtrar_valor(datos_filtrados, "G.2.4", "Real")
    tb_evap_piscina_ref_inferior_proy_cmz = filtrar_valor(datos_filtrados, "G.2.4", "Proyectado")

    #Tabla Flujo G.2.5
    tb_evap_piscina_chancado_terciario_cmz = filtrar_valor(datos_filtrados, "G.2.5", "Real")
    tb_evap_piscina_chancado_terciario_proy_cmz = filtrar_valor(datos_filtrados, "G.2.5", "Proyectado")
    
    #Tabla Flujo G.2.6
    tb_evap_piscina_dl_cmz = filtrar_valor(datos_filtrados, "G.2.6", "Real")
    tb_evap_piscina_dl_proy_cmz = filtrar_valor(datos_filtrados, "G.2.6", "Proyectado")
    
    #Tabla Flujo G.2.7
    tb_evap_piscina_auxiliar_cmz = filtrar_valor(datos_filtrados, "G.2.7", "Real")
    tb_evap_piscina_auxiliar_proy_cmz = filtrar_valor(datos_filtrados, "G.2.7", "Proyectado")
    
    #Tabla Flujo G.2.8
    tb_evap_piscina_ral_cmz = filtrar_valor(datos_filtrados, "G.2.8", "Real")
    tb_evap_piscina_ral_proy_cmz = filtrar_valor(datos_filtrados, "G.2.8", "Proyectado")
    
    #Tabla Flujo H
    tb_control_polvo_a_evaporacion_cmz = filtrar_valor(datos_filtrados, "H", "Real")
    tb_control_polvo_a_evaporacion_proy_cmz = filtrar_valor(datos_filtrados, "H", "Proyectado")
    control_polvo_a_evaporacion_cmz = tb_control_polvo_a_evaporacion_cmz

    #Tabla Flujo I
    tb_agua_nueva_a_evaporacion_cmz = filtrar_valor(datos_filtrados, "I", "Real")
    tb_agua_nueva_a_evaporacion_proy_cmz = filtrar_valor(datos_filtrados, "I", "Proyectado")
    agua_nueva_a_evaporacion_cmz = tb_agua_nueva_a_evaporacion_cmz
    
    #Tabla Flujo J
    tb_tsf_a_infiltracion_cmz = filtrar_valor(datos_filtrados, "J", "Real")
    tb_tsf_a_infiltracion_proy_cmz = filtrar_valor(datos_filtrados, "J", "Proyectado")
    tsf_a_infiltracion_cmz = tb_tsf_a_infiltracion_cmz
    
    #Tabla Flujo a
    tb_agua_nueva_a_area_seca_cmz = filtrar_valor(datos_filtrados, "a", "Real")
    tb_agua_nueva_a_area_seca_proy_cmz = filtrar_valor(datos_filtrados, "a", "Proyectado")
    agua_nueva_a_area_seca_cmz = tb_agua_nueva_a_area_seca_cmz
    
    #Tabla Flujo a.1
    tb_piscina_zaldivar_tk_agua_fresca_cmz = filtrar_valor(datos_filtrados, "a.1", "Real")
    tb_piscina_zaldivar_tk_agua_fresca_proy_cmz = filtrar_valor(datos_filtrados, "a.1", "Proyectado")
    
    #Tabla Flujo a.2
    tb_rechazo_tk_agua_fresca_cmz = filtrar_valor(datos_filtrados, "a.2", "Real")
    tb_rechazo_tk_agua_fresca_proy_cmz = filtrar_valor(datos_filtrados, "a.2", "Proyectado")
    
    #Tabla Flujo a.3
    tb_piscina_neurara_a_refino_cmz = filtrar_valor(datos_filtrados, "a.3", "Real")
    tb_piscina_neurara_a_refino_proy_cmz = filtrar_valor(datos_filtrados, "a.3", "Proyectado")
    
    #Tabla Flujo b
    tb_agua_nueva_a_sxew_cmz = filtrar_valor(datos_filtrados, "b", "Real")
    tb_agua_nueva_a_sxew_proy_cmz = filtrar_valor(datos_filtrados, "b", "Proyectado")
    agua_nueva_a_sxew_cmz = tb_agua_nueva_a_sxew_cmz

    #Tabla Flujo c
    tb_agua_nueva_a_control_polvo_cmz = filtrar_valor(datos_filtrados, "c", "Real")
    tb_agua_nueva_a_control_polvo_proy_cmz = filtrar_valor(datos_filtrados, "c", "Proyectado")
    agua_nueva_a_control_polvo_cmz = tb_agua_nueva_a_control_polvo_cmz
    
    #Tabla Flujo c.1
    tb_agua_a_chancado_primario_cmz = filtrar_valor(datos_filtrados, "c.1", "Real")
    tb_agua_a_chancado_primario_proy_cmz = filtrar_valor(datos_filtrados, "c.1", "Proyectado")
    
    #Tabla Flujo c.2
    tb_cerro_las_antena_cmz = filtrar_valor(datos_filtrados, "c.2", "Real")
    tb_cerro_las_antena_proy_cmz = filtrar_valor(datos_filtrados, "c.2", "Proyectado")
    
    #Tabla Flujo c.3 
    tb_cachimba_mina_cmz = filtrar_valor(datos_filtrados, "c.3", "Real")
    tb_cachimba_mina_proy_cmz = filtrar_valor(datos_filtrados, "c.3", "Proyectado")
    
    #Tabla Flujo d
    tb_agua_nueva_a_servicios_cmz = filtrar_valor(datos_filtrados, "d", "Real")
    tb_agua_nueva_a_servicios_proy_cmz = filtrar_valor(datos_filtrados, "d", "Proyectado")
    agua_nueva_a_servicios_cmz = tb_agua_nueva_a_servicios_cmz
    
    #Tabla Flujo d.1
    tb_agua_gerencia_cmz = filtrar_valor(datos_filtrados, "d.1", "Real")
    tb_agua_gerencia_proy_cmz = filtrar_valor(datos_filtrados, "d.1", "Proyectado")
    
    #Tabla Flujo d.2
    tb_agua_potable_a_flotacion_cmz = filtrar_valor(datos_filtrados, "d.2", "Real")
    tb_agua_potable_a_flotacion_proy_cmz = filtrar_valor(datos_filtrados, "d.2", "Proyectado")

    #Tabla Flujo d.3
    tb_potable_a_operacion_cmz = filtrar_valor(datos_filtrados, "d.3", "Real")
    tb_potable_a_operacion_proy_cmz = filtrar_valor(datos_filtrados, "d.3", "Proyectado")

    #Tabla Flujo d.4
    tb_agua_incendio_cmz = filtrar_valor(datos_filtrados, "d.4", "Real")
    tb_agua_incendio_proy_cmz = filtrar_valor(datos_filtrados, "d.4", "Proyectado")

    #Tabla Flujo e
    tb_tsf_a_area_seca_cmz = filtrar_valor(datos_filtrados, "e", "Real")
    tb_tsf_a_area_seca_proy_cmz = filtrar_valor(datos_filtrados, "e", "Proyectado")
    tsf_a_area_seca_cmz = tb_tsf_a_area_seca_cmz

    #Tabla Flujo f
    tb_area_seca_a_tsf_cmz = filtrar_valor(datos_filtrados, "f", "Real")
    tb_area_seca_a_tsf_proy_cmz = filtrar_valor(datos_filtrados, "f", "Proyectado")
    area_seca_a_tsf_cmz = tb_area_seca_a_tsf_cmz
    
    #Tabla Flujo g
    tb_area_seca_a_sxew_cmz = filtrar_valor(datos_filtrados, "g", "Real")
    tb_area_seca_a_sxew_proy_cmz = filtrar_valor(datos_filtrados, "g", "Proyectado")
    area_seca_a_sxew_cmz = tb_area_seca_a_sxew_cmz
    
    #Tabla Flujo g.1
    tb_tren_a_a_flujo_pls_cmz = filtrar_valor(datos_filtrados, "g.1", "Real")
    tb_tren_a_a_flujo_pls_proy_cmz = filtrar_valor(datos_filtrados, "g.1", "Proyectado")
    
    #Tabla Flujo g.2
    tb_tren_b_a_flujo_pls_cmz = filtrar_valor(datos_filtrados, "g.2", "Real")
    tb_tren_b_a_flujo_pls_proy_cmz = filtrar_valor(datos_filtrados, "g.2", "Proyectado")
    
    #Tabla Flujo g.3
    tb_tren_c_a_flujo_pls_cmz = filtrar_valor(datos_filtrados, "g.3", "Real")
    tb_tren_c_a_flujo_pls_proy_cmz = filtrar_valor(datos_filtrados, "g.3", "Proyectado")
    
    #Tabla Flujo g.4
    tb_tren_d_a_flujo_pls_cmz = filtrar_valor(datos_filtrados, "g.4", "Real")
    tb_tren_d_a_flujo_pls_proy_cmz = filtrar_valor(datos_filtrados, "g.4", "Proyectado")

    #Tabla Flujo h
    tb_sxew_a_area_seca_cmz = filtrar_valor(datos_filtrados, "h", "Real")
    tb_sxew_a_area_seca_proy_cmz = filtrar_valor(datos_filtrados, "h", "Proyectado")
    sxew_a_area_seca_cmz = tb_sxew_a_area_seca_cmz
    
    #Tabla Flujo h.1
    tb_tren_a_a_refino_inferior_cmz = filtrar_valor(datos_filtrados, "h.1", "Real")
    tb_tren_a_a_refino_inferior_proy_cmz = filtrar_valor(datos_filtrados, "h.1", "Proyectado")
    
    #Tabla Flujo h.2
    tb_tren_b_a_refino_inferior_cmz = filtrar_valor(datos_filtrados, "h.2", "Real")
    tb_tren_b_a_refino_inferior_proy_cmz = filtrar_valor(datos_filtrados, "h.2", "Proyectado")
    
    #Tabla Flujo h.3
    tb_tren_c_a_refino_inferior_cmz = filtrar_valor(datos_filtrados, "h.3", "Real")
    tb_tren_c_a_refino_inferior_proy_cmz = filtrar_valor(datos_filtrados, "h.3", "Proyectado")
    
    #Tabla Flujo h.4
    tb_tren_d_a_refino_inferior_cmz = filtrar_valor(datos_filtrados, "h.4", "Real")
    tb_tren_d_a_refino_inferior_proy_cmz = filtrar_valor(datos_filtrados, "h.4", "Proyectado")
    
    #Tabla Flujo i
    tb_servicios_a_ptas_cmz = filtrar_valor(datos_filtrados, "i", "Real")
    tb_servicios_a_ptas_proy_cmz = filtrar_valor(datos_filtrados, "i", "Proyectado")
    servicios_a_ptas_cmz = tb_servicios_a_ptas_cmz
    
    #Tabla Flujo j
    tb_ptas_a_control_polvo_cmz = filtrar_valor(datos_filtrados, "j", "Real")
    tb_ptas_a_control_polvo_proy_cmz = filtrar_valor(datos_filtrados, "j", "Proyectado")
    ptas_a_control_polvo_cmz = tb_ptas_a_control_polvo_cmz
    
    #Tabla Flujo k
    tb_alimentacion_ro_cmz = filtrar_valor(datos_filtrados, "k", "Real")
    tb_alimentacion_ro_proy_cmz = filtrar_valor(datos_filtrados, "k", "Proyectado")

    #Tabla Flujo m
    tb_tk_agua_fresca_a_piscina_ch_iii_cmz = filtrar_valor(datos_filtrados, "m", "Real")
    tb_tk_agua_fresca_a_piscina_ch_iii_proy_cmz = filtrar_valor(datos_filtrados, "m", "Proyectado")

    #Tabla Flujo n
    tb_tk_agua_fresca_a_refino_cmz = filtrar_valor(datos_filtrados, "n", "Real")
    tb_tk_agua_fresca_a_refino_proy_cmz = filtrar_valor(datos_filtrados, "n", "Proyectado")

    #Tabla Flujo o
    tb_piscina_procesos_a_pilas_cmz = filtrar_valor(datos_filtrados, "o", "Real")
    tb_piscina_procesos_a_pilas_proy_cmz = filtrar_valor(datos_filtrados, "o", "Proyectado")

    #Tabla Flujo o.1
    tb_piscina_refinos_a_pilas_cmz = filtrar_valor(datos_filtrados, "o.1", "Real")
    tb_piscina_refinos_a_pilas_proy_cmz = filtrar_valor(datos_filtrados, "o.1", "Proyectado")

    #Tabla Flujo o.1.1
    tb_refino_superior_a_pila_hl_cmz = filtrar_valor(datos_filtrados, "o.1.1", "Real")
    tb_refino_superior_a_pila_hl_proy_cmz = filtrar_valor(datos_filtrados, "o.1.1", "Proyectado")

    #Tabla Flujo o.1.2
    tb_refino_inferior_a_pila_ral_cmz = filtrar_valor(datos_filtrados, "o.1.2", "Real")
    tb_refino_inferior_a_pila_ral_proy_cmz = filtrar_valor(datos_filtrados, "o.1.2", "Proyectado")

    #Tabla Flujo o.2
    tb_piscina_ipls_a_pila_hl_cmz = filtrar_valor(datos_filtrados, "o.2", "Real")
    tb_piscina_ipls_a_pila_hl_proy_cmz = filtrar_valor(datos_filtrados, "o.2", "Proyectado")

    #Tabla Flujo o.3
    tb_piscina_dl_a_pila_dl_cmz = filtrar_valor(datos_filtrados, "o.3", "Real")
    tb_piscina_dl_a_pila_dl_proy_cmz = filtrar_valor(datos_filtrados, "o.3", "Proyectado")

    #Tabla Flujo p
    tb_refino_inferior_a_refino_superior_cmz = filtrar_valor(datos_filtrados, "p", "Real")
    tb_refino_inferior_a_refino_superior_proy_cmz = filtrar_valor(datos_filtrados, "p", "Proyectado")

    #Tabla Flujo q
    tb_pilas_a_piscina_procesos_cmz = filtrar_valor(datos_filtrados, "q", "Real")
    tb_pilas_a_piscina_procesos_proy_cmz = filtrar_valor(datos_filtrados, "q", "Proyectado")

    #Tabla Flujo q.1
    tb_pila_hl_a_piscina_pls_ipls_cmz = filtrar_valor(datos_filtrados, "q.1", "Real")
    tb_pila_hl_a_piscina_pls_ipls_proy_cmz = filtrar_valor(datos_filtrados, "q.1", "Proyectado")

    #Tabla Flujo q.2
    tb_pila_dl_a_piscina_pls_ipls_cmz = filtrar_valor(datos_filtrados, "q.2", "Real")
    tb_pila_dl_a_piscina_pls_ipls_proy_cmz = filtrar_valor(datos_filtrados, "q.2", "Proyectado")
    
    #Tabla Flujo q.3
    tb_pila_ral_a_piscina_ral_cmz = filtrar_valor(datos_filtrados, "q.3", "Real")
    tb_pila_ral_a_piscina_ral_proy_cmz = filtrar_valor(datos_filtrados, "q.3", "Proyectado")
    
    #Tabla Flujo r
    tb_piscina_auxiliar_a_piscina_pls_ipls_cmz = filtrar_valor(datos_filtrados, "r", "Real")
    tb_piscina_auxiliar_a_piscina_pls_ipls_proy_cmz = filtrar_valor(datos_filtrados, "r", "Proyectado")
    
    #Tabla Flujo s
    tb_refino_superior_a_piscina_dl_cmz = filtrar_valor(datos_filtrados, "s", "Real")
    tb_refino_superior_a_piscina_dl_proy_cmz = filtrar_valor(datos_filtrados, "s", "Proyectado")
    
    #Tabla Flujo t
    tb_piscina_ral_a_piscina_auxiliar_cmz = filtrar_valor(datos_filtrados, "t", "Real")
    tb_piscina_ral_a_piscina_auxiliar_proy_cmz = filtrar_valor(datos_filtrados, "t", "Proyectado")
    
    #Tabla Flujo u
    tb_barreras_hidraulicas_a_piscina_ral_cmz = filtrar_valor(datos_filtrados, "u", "Real")
    tb_barreras_hidraulicas_a_piscina_ral_proy_cmz = filtrar_valor(datos_filtrados, "u", "Proyectado")
    
    #Tabla Flujo u.1
    tb_caudal_bh_1_cmz = filtrar_valor(datos_filtrados, "u.1", "Real")
    tb_caudal_bh_1_proy_cmz = filtrar_valor(datos_filtrados, "u.1", "Proyectado")

    #Tabla Flujo u.2
    tb_caudal_bh_2_cmz = filtrar_valor(datos_filtrados, "u.2", "Real")
    tb_caudal_bh_2_proy_cmz = filtrar_valor(datos_filtrados, "u.2", "Proyectado")
    
    #Tabla Flujo u.3
    tb_caudal_bh_3_cmz = filtrar_valor(datos_filtrados, "u.3", "Real")
    tb_caudal_bh_3_proy_cmz = filtrar_valor(datos_filtrados, "u.3", "Proyectado")
    
    #Tabla Flujo u.4
    tb_caudal_bh_4_cmz = filtrar_valor(datos_filtrados, "u.4", "Real")
    tb_caudal_bh_4_proy_cmz = filtrar_valor(datos_filtrados, "u.4", "Proyectado")
    
    #Tabla Flujo v
    tb_consumo_adicional_agua_potable_cmz = filtrar_valor(datos_filtrados, "v", "Real")
    tb_consumo_adicional_agua_potable_proy_cmz = filtrar_valor(datos_filtrados, "v", "Proyectado")

    datos_cmz = {
        'tb_agua_negrillar_a_agua_nueva_cmz': tb_agua_negrillar_a_agua_nueva_cmz,
        'tb_agua_negrillar_a_agua_nueva_proy_cmz': tb_agua_negrillar_a_agua_nueva_proy_cmz,
        'agua_negrillar_a_agua_nueva_cmz': agua_negrillar_a_agua_nueva_cmz,
        'tb_extrac_ls_p1_dga_cmz': tb_extrac_ls_p1_dga_cmz,
        'tb_extrac_ls_p1_dga_proy_cmz': tb_extrac_ls_p1_dga_proy_cmz,
        'tb_extrac_ls_p2_dga_cmz': tb_extrac_ls_p2_dga_cmz,
        'tb_extrac_ls_p2_dga_proy_cmz': tb_extrac_ls_p2_dga_proy_cmz,
        'tb_extrac_ls_p3_dga_cmz': tb_extrac_ls_p3_dga_cmz,
        'tb_extrac_ls_p3_dga_proy_cmz': tb_extrac_ls_p3_dga_proy_cmz,
        'tb_extrac_ls_p4_dga_cmz': tb_extrac_ls_p4_dga_cmz,
        'tb_extrac_ls_p4_dga_proy_cmz': tb_extrac_ls_p4_dga_proy_cmz,
        'tb_extrac_ls_p5_dga_cmz': tb_extrac_ls_p5_dga_cmz,
        'tb_extrac_ls_p5_dga_proy_cmz': tb_extrac_ls_p5_dga_proy_cmz,
        'tb_extrac_ls_p6_dga_cmz': tb_extrac_ls_p6_dga_cmz,
        'tb_extrac_ls_p6_dga_proy_cmz': tb_extrac_ls_p6_dga_proy_cmz,
        'tb_agua_mineral_a_area_seca_cmz': tb_agua_mineral_a_area_seca_cmz,
        'tb_agua_mineral_a_area_seca_proy_cmz': tb_agua_mineral_a_area_seca_proy_cmz,
        'agua_mineral_a_area_seca_cmz': agua_mineral_a_area_seca_cmz,
        'tb_humedad_mineral_hl_cmz': tb_humedad_mineral_hl_cmz,
        'tb_humedad_mineral_hl_proy_cmz': tb_humedad_mineral_hl_proy_cmz,
        'tb_humedad_mineral_dl_cmz': tb_humedad_mineral_dl_cmz,
        'tb_humedad_mineral_dl_proy_cmz': tb_humedad_mineral_dl_proy_cmz,
        'tb_humedad_chancado_terciario_cmz': tb_humedad_chancado_terciario_cmz,
        'tb_humedad_chancado_terciario_proy_cmz': tb_humedad_chancado_terciario_proy_cmz,
        'tb_aguas_halladas_a_control_polvo_cmz': tb_aguas_halladas_a_control_polvo_cmz,
        'tb_aguas_halladas_a_control_polvo_proy_cmz': tb_aguas_halladas_a_control_polvo_proy_cmz,
        'aguas_halladas_a_control_polvo_cmz': aguas_halladas_a_control_polvo_cmz,
        'tb_pozo22_cmz': tb_pozo22_cmz,
        'tb_pozo22_proy_cmz': tb_pozo22_proy_cmz,
        'tb_pozo25_cmz': tb_pozo25_cmz,
        'tb_pozo25_proy_cmz': tb_pozo25_proy_cmz,
        'tb_pozo26_cmz': tb_pozo26_cmz,
        'tb_pozo26_proy_cmz': tb_pozo26_proy_cmz,
        'tb_pozo27_cmz': tb_pozo27_cmz,
        'tb_pozo27_proy_cmz': tb_pozo27_proy_cmz,
        'tb_pozo28_cmz': tb_pozo28_cmz,
        'tb_pozo28_proy_cmz': tb_pozo28_proy_cmz,
        'tb_pozo29_cmz': tb_pozo29_cmz,
        'tb_pozo29_proy_cmz': tb_pozo29_proy_cmz,
        'tb_pozo30_cmz': tb_pozo30_cmz,
        'tb_pozo30_proy_cmz': tb_pozo30_proy_cmz,
        'tb_pozo31_cmz': tb_pozo31_cmz,
        'tb_pozo31_proy_cmz': tb_pozo31_proy_cmz,
        'tb_tsf_a_retencion_cmz': tb_tsf_a_retencion_cmz,
        'tb_tsf_a_retencion_proy_cmz': tb_tsf_a_retencion_proy_cmz,
        'tsf_a_retencion_cmz': tsf_a_retencion_cmz,
        'tb_area_seca_a_retencion_cmz': tb_area_seca_a_retencion_cmz,
        'tb_area_seca_a_retencion_proy_cmz': tb_area_seca_a_retencion_proy_cmz,
        'area_seca_a_retencion_cmz': area_seca_a_retencion_cmz,
        'tb_retencion_hl_cmz': tb_retencion_hl_cmz,
        'tb_retencion_hl_proy_cmz': tb_retencion_hl_proy_cmz,
        'tb_retencion_dl_cmz': tb_retencion_dl_cmz,
        'tb_retencion_dl_proy_cmz': tb_retencion_dl_proy_cmz,
        'tb_retencion_ral_cmz': tb_retencion_ral_cmz,
        'tb_retencion_ral_proy_cmz': tb_retencion_ral_proy_cmz,
        'tb_perdidas_concentrado_cmz': tb_perdidas_concentrado_cmz,
        'tb_perdidas_concentrado_proy_cmz': tb_perdidas_concentrado_proy_cmz,
        'tb_tsf_a_evaporacion_cmz': tb_tsf_a_evaporacion_cmz,
        'tb_tsf_a_evaporacion_proy_cmz': tb_tsf_a_evaporacion_proy_cmz,
        'tsf_a_evaporacion_cmz': tsf_a_evaporacion_cmz,
        'tb_area_seca_a_evaporacion_cmz': tb_area_seca_a_evaporacion_cmz,
        'tb_area_seca_a_evaporacion_proy_cmz': tb_area_seca_a_evaporacion_proy_cmz,
        'area_seca_a_evaporacion_cmz': area_seca_a_evaporacion_cmz,
        'tb_evap_pilas_cmz': tb_evap_pilas_cmz,
        'tb_evap_pilas_proy_cmz': tb_evap_pilas_proy_cmz,
        'tb_evap_pila_hl_cmz': tb_evap_pila_hl_cmz,
        'tb_evap_pila_hl_proy_cmz': tb_evap_pila_hl_proy_cmz,
        'tb_evap_pila_dl_cmz': tb_evap_pila_dl_cmz,
        'tb_evap_pila_dl_proy_cmz': tb_evap_pila_dl_proy_cmz,
        'tb_evap_pila_ral_cmz': tb_evap_pila_ral_cmz,
        'tb_evap_pila_ral_proy_cmz': tb_evap_pila_ral_proy_cmz,
        'tb_evap_total_piscinas_cmz': tb_evap_total_piscinas_cmz,
        'tb_evap_total_piscinas_proy_cmz': tb_evap_total_piscinas_proy_cmz,
        'tb_evap_piscina_pls_cmz': tb_evap_piscina_pls_cmz,
        'tb_evap_piscina_pls_proy_cmz': tb_evap_piscina_pls_proy_cmz,
        'tb_evap_piscina_ils_cmz': tb_evap_piscina_ils_cmz,
        'tb_evap_piscina_ils_proy_cmz': tb_evap_piscina_ils_proy_cmz,
        'tb_evap_piscina_ref_superior_cmz': tb_evap_piscina_ref_superior_cmz,
        'tb_evap_piscina_ref_superior_proy_cmz': tb_evap_piscina_ref_superior_proy_cmz,
        'tb_evap_piscina_ref_inferior_cmz': tb_evap_piscina_ref_inferior_cmz,
        'tb_evap_piscina_ref_inferior_proy_cmz': tb_evap_piscina_ref_inferior_proy_cmz,
        'tb_evap_piscina_chancado_terciario_cmz': tb_evap_piscina_chancado_terciario_cmz,
        'tb_evap_piscina_chancado_terciario_proy_cmz': tb_evap_piscina_chancado_terciario_proy_cmz,
        'tb_evap_piscina_dl_cmz': tb_evap_piscina_dl_cmz,
        'tb_evap_piscina_dl_proy_cmz': tb_evap_piscina_dl_proy_cmz,
        'tb_evap_piscina_auxiliar_cmz': tb_evap_piscina_auxiliar_cmz,
        'tb_evap_piscina_auxiliar_proy_cmz': tb_evap_piscina_auxiliar_proy_cmz,
        'tb_evap_piscina_ral_cmz': tb_evap_piscina_ral_cmz,
        'tb_evap_piscina_ral_proy_cmz': tb_evap_piscina_ral_proy_cmz,
        'tb_control_polvo_a_evaporacion_cmz': tb_control_polvo_a_evaporacion_cmz,
        'tb_control_polvo_a_evaporacion_proy_cmz': tb_control_polvo_a_evaporacion_proy_cmz,
        'control_polvo_a_evaporacion_cmz': control_polvo_a_evaporacion_cmz,
        'tb_agua_nueva_a_evaporacion_cmz': tb_agua_nueva_a_evaporacion_cmz,
        'tb_agua_nueva_a_evaporacion_proy_cmz': tb_agua_nueva_a_evaporacion_proy_cmz,
        'agua_nueva_a_evaporacion_cmz': agua_nueva_a_evaporacion_cmz,
        'tb_tsf_a_infiltracion_cmz': tb_tsf_a_infiltracion_cmz,
        'tb_tsf_a_infiltracion_proy_cmz': tb_tsf_a_infiltracion_proy_cmz,
        'tsf_a_infiltracion_cmz': tsf_a_infiltracion_cmz,
        'tb_agua_nueva_a_area_seca_cmz': tb_agua_nueva_a_area_seca_cmz,
        'tb_agua_nueva_a_area_seca_proy_cmz': tb_agua_nueva_a_area_seca_proy_cmz,
        'agua_nueva_a_area_seca_cmz': agua_nueva_a_area_seca_cmz,
        'tb_piscina_zaldivar_tk_agua_fresca_cmz': tb_piscina_zaldivar_tk_agua_fresca_cmz,
        'tb_piscina_zaldivar_tk_agua_fresca_proy_cmz': tb_piscina_zaldivar_tk_agua_fresca_proy_cmz,
        'tb_rechazo_tk_agua_fresca_cmz': tb_rechazo_tk_agua_fresca_cmz,
        'tb_rechazo_tk_agua_fresca_proy_cmz': tb_rechazo_tk_agua_fresca_proy_cmz,
        'tb_piscina_neurara_a_refino_cmz': tb_piscina_neurara_a_refino_cmz,
        'tb_piscina_neurara_a_refino_proy_cmz': tb_piscina_neurara_a_refino_proy_cmz,
        'tb_agua_nueva_a_sxew_cmz': tb_agua_nueva_a_sxew_cmz,
        'tb_agua_nueva_a_sxew_proy_cmz': tb_agua_nueva_a_sxew_proy_cmz,
        'agua_nueva_a_sxew_cmz': agua_nueva_a_sxew_cmz,
        'tb_agua_nueva_a_control_polvo_cmz': tb_agua_nueva_a_control_polvo_cmz,
        'tb_agua_nueva_a_control_polvo_proy_cmz': tb_agua_nueva_a_control_polvo_proy_cmz,
        'agua_nueva_a_control_polvo_cmz': agua_nueva_a_control_polvo_cmz,
        'tb_agua_a_chancado_primario_cmz': tb_agua_a_chancado_primario_cmz,
        'tb_agua_a_chancado_primario_proy_cmz': tb_agua_a_chancado_primario_proy_cmz,
        'tb_cerro_las_antena_cmz': tb_cerro_las_antena_cmz,
        'tb_cerro_las_antena_proy_cmz': tb_cerro_las_antena_proy_cmz,
        'tb_cachimba_mina_cmz': tb_cachimba_mina_cmz,
        'tb_cachimba_mina_proy_cmz': tb_cachimba_mina_proy_cmz,
        'tb_agua_nueva_a_servicios_cmz': tb_agua_nueva_a_servicios_cmz,
        'tb_agua_nueva_a_servicios_proy_cmz': tb_agua_nueva_a_servicios_proy_cmz,
        'agua_nueva_a_servicios_cmz': agua_nueva_a_servicios_cmz,
        'tb_agua_gerencia_cmz': tb_agua_gerencia_cmz,
        'tb_agua_gerencia_proy_cmz': tb_agua_gerencia_proy_cmz,
        'tb_agua_potable_a_flotacion_cmz': tb_agua_potable_a_flotacion_cmz,
        'tb_agua_potable_a_flotacion_proy_cmz': tb_agua_potable_a_flotacion_proy_cmz,
        'tb_potable_a_operacion_cmz': tb_potable_a_operacion_cmz,
        'tb_potable_a_operacion_proy_cmz': tb_potable_a_operacion_proy_cmz,
        'tb_agua_incendio_cmz': tb_agua_incendio_cmz,
        'tb_agua_incendio_proy_cmz': tb_agua_incendio_proy_cmz,
        'tb_tsf_a_area_seca_cmz': tb_tsf_a_area_seca_cmz,
        'tb_tsf_a_area_seca_proy_cmz': tb_tsf_a_area_seca_proy_cmz,
        'tsf_a_area_seca_cmz': tsf_a_area_seca_cmz,
        'tb_area_seca_a_tsf_cmz': tb_area_seca_a_tsf_cmz,
        'tb_area_seca_a_tsf_proy_cmz': tb_area_seca_a_tsf_proy_cmz,
        'area_seca_a_tsf_cmz': area_seca_a_tsf_cmz,
        'tb_area_seca_a_sxew_cmz': tb_area_seca_a_sxew_cmz,
        'tb_area_seca_a_sxew_proy_cmz': tb_area_seca_a_sxew_proy_cmz,
        'area_seca_a_sxew_cmz': area_seca_a_sxew_cmz,
        'tb_tren_a_a_flujo_pls_cmz': tb_tren_a_a_flujo_pls_cmz,
        'tb_tren_a_a_flujo_pls_proy_cmz': tb_tren_a_a_flujo_pls_proy_cmz,
        'tb_tren_b_a_flujo_pls_cmz': tb_tren_b_a_flujo_pls_cmz,
        'tb_tren_b_a_flujo_pls_proy_cmz': tb_tren_b_a_flujo_pls_proy_cmz,
        'tb_tren_c_a_flujo_pls_cmz': tb_tren_c_a_flujo_pls_cmz,
        'tb_tren_c_a_flujo_pls_proy_cmz': tb_tren_c_a_flujo_pls_proy_cmz,
        'tb_tren_d_a_flujo_pls_cmz': tb_tren_d_a_flujo_pls_cmz,
        'tb_tren_d_a_flujo_pls_proy_cmz': tb_tren_d_a_flujo_pls_proy_cmz,
        'tb_sxew_a_area_seca_cmz': tb_sxew_a_area_seca_cmz,
        'tb_sxew_a_area_seca_proy_cmz': tb_sxew_a_area_seca_proy_cmz,
        'sxew_a_area_seca_cmz': sxew_a_area_seca_cmz,
        'tb_tren_a_a_refino_inferior_cmz': tb_tren_a_a_refino_inferior_cmz,
        'tb_tren_a_a_refino_inferior_proy_cmz': tb_tren_a_a_refino_inferior_proy_cmz,
        'tb_tren_b_a_refino_inferior_cmz': tb_tren_b_a_refino_inferior_cmz,
        'tb_tren_b_a_refino_inferior_proy_cmz': tb_tren_b_a_refino_inferior_proy_cmz,
        'tb_tren_c_a_refino_inferior_cmz': tb_tren_c_a_refino_inferior_cmz,
        'tb_tren_c_a_refino_inferior_proy_cmz': tb_tren_c_a_refino_inferior_proy_cmz,
        'tb_tren_d_a_refino_inferior_cmz': tb_tren_d_a_refino_inferior_cmz,
        'tb_tren_d_a_refino_inferior_proy_cmz': tb_tren_d_a_refino_inferior_proy_cmz,
        'tb_servicios_a_ptas_cmz': tb_servicios_a_ptas_cmz,
        'tb_servicios_a_ptas_proy_cmz': tb_servicios_a_ptas_proy_cmz,
        'servicios_a_ptas_cmz': servicios_a_ptas_cmz,
        'tb_ptas_a_control_polvo_cmz': tb_ptas_a_control_polvo_cmz,
        'tb_ptas_a_control_polvo_proy_cmz': tb_ptas_a_control_polvo_proy_cmz,
        'ptas_a_control_polvo_cmz': ptas_a_control_polvo_cmz,
        'tb_alimentacion_ro_cmz': tb_alimentacion_ro_cmz,
        'tb_alimentacion_ro_proy_cmz': tb_alimentacion_ro_proy_cmz,
        'tb_tk_agua_fresca_a_piscina_ch_iii_cmz': tb_tk_agua_fresca_a_piscina_ch_iii_cmz,
        'tb_tk_agua_fresca_a_piscina_ch_iii_proy_cmz': tb_tk_agua_fresca_a_piscina_ch_iii_proy_cmz,
        'tb_tk_agua_fresca_a_refino_cmz': tb_tk_agua_fresca_a_refino_cmz,
        'tb_tk_agua_fresca_a_refino_proy_cmz': tb_tk_agua_fresca_a_refino_proy_cmz,
        'tb_piscina_procesos_a_pilas_cmz': tb_piscina_procesos_a_pilas_cmz,
        'tb_piscina_procesos_a_pilas_proy_cmz': tb_piscina_procesos_a_pilas_proy_cmz,
        'tb_piscina_refinos_a_pilas_cmz': tb_piscina_refinos_a_pilas_cmz,
        'tb_piscina_refinos_a_pilas_proy_cmz': tb_piscina_refinos_a_pilas_proy_cmz,
        'tb_refino_superior_a_pila_hl_cmz': tb_refino_superior_a_pila_hl_cmz,
        'tb_refino_superior_a_pila_hl_proy_cmz': tb_refino_superior_a_pila_hl_proy_cmz,
        'tb_refino_inferior_a_pila_ral_cmz': tb_refino_inferior_a_pila_ral_cmz,
        'tb_refino_inferior_a_pila_ral_proy_cmz': tb_refino_inferior_a_pila_ral_proy_cmz,
        'tb_piscina_ipls_a_pila_hl_cmz': tb_piscina_ipls_a_pila_hl_cmz,
        'tb_piscina_ipls_a_pila_hl_proy_cmz': tb_piscina_ipls_a_pila_hl_proy_cmz,
        'tb_piscina_dl_a_pila_dl_cmz': tb_piscina_dl_a_pila_dl_cmz,
        'tb_piscina_dl_a_pila_dl_proy_cmz': tb_piscina_dl_a_pila_dl_proy_cmz,
        'tb_refino_inferior_a_refino_superior_cmz': tb_refino_inferior_a_refino_superior_cmz,
        'tb_refino_inferior_a_refino_superior_proy_cmz': tb_refino_inferior_a_refino_superior_proy_cmz,
        'tb_pilas_a_piscina_procesos_cmz': tb_pilas_a_piscina_procesos_cmz,
        'tb_pilas_a_piscina_procesos_proy_cmz': tb_pilas_a_piscina_procesos_proy_cmz,
        'tb_pila_hl_a_piscina_pls_ipls_cmz': tb_pila_hl_a_piscina_pls_ipls_cmz,
        'tb_pila_hl_a_piscina_pls_ipls_proy_cmz': tb_pila_hl_a_piscina_pls_ipls_proy_cmz,
        'tb_pila_dl_a_piscina_pls_ipls_cmz': tb_pila_dl_a_piscina_pls_ipls_cmz,
        'tb_pila_dl_a_piscina_pls_ipls_proy_cmz': tb_pila_dl_a_piscina_pls_ipls_proy_cmz,
        'tb_pila_ral_a_piscina_ral_cmz': tb_pila_ral_a_piscina_ral_cmz,
        'tb_pila_ral_a_piscina_ral_proy_cmz': tb_pila_ral_a_piscina_ral_proy_cmz,
        'tb_piscina_auxiliar_a_piscina_pls_ipls_cmz': tb_piscina_auxiliar_a_piscina_pls_ipls_cmz,
        'tb_piscina_auxiliar_a_piscina_pls_ipls_proy_cmz': tb_piscina_auxiliar_a_piscina_pls_ipls_proy_cmz,
        'tb_refino_superior_a_piscina_dl_cmz': tb_refino_superior_a_piscina_dl_cmz,
        'tb_refino_superior_a_piscina_dl_proy_cmz': tb_refino_superior_a_piscina_dl_proy_cmz,
        'tb_piscina_ral_a_piscina_auxiliar_cmz': tb_piscina_ral_a_piscina_auxiliar_cmz,
        'tb_piscina_ral_a_piscina_auxiliar_proy_cmz': tb_piscina_ral_a_piscina_auxiliar_proy_cmz,
        'tb_barreras_hidraulicas_a_piscina_ral_cmz': tb_barreras_hidraulicas_a_piscina_ral_cmz,
        'tb_barreras_hidraulicas_a_piscina_ral_proy_cmz': tb_barreras_hidraulicas_a_piscina_ral_proy_cmz,
        'tb_caudal_bh_1_cmz': tb_caudal_bh_1_cmz,
        'tb_caudal_bh_1_proy_cmz': tb_caudal_bh_1_proy_cmz,
        'tb_caudal_bh_2_cmz': tb_caudal_bh_2_cmz,
        'tb_caudal_bh_2_proy_cmz': tb_caudal_bh_2_proy_cmz,
        'tb_caudal_bh_3_cmz': tb_caudal_bh_3_cmz,
        'tb_caudal_bh_3_proy_cmz': tb_caudal_bh_3_proy_cmz,
        'tb_caudal_bh_4_cmz': tb_caudal_bh_4_cmz,
        'tb_caudal_bh_4_proy_cmz': tb_caudal_bh_4_proy_cmz,
        'tb_consumo_adicional_agua_potable_cmz': tb_consumo_adicional_agua_potable_cmz,
        'tb_consumo_adicional_agua_potable_proy_cmz': tb_consumo_adicional_agua_potable_proy_cmz,
    }

    return (datos_cmz)


##############################################################################################

def toggle_rows_logic_cmz(data):
    # Estilos visibles y ocultos
    style_hidden = {"display": "none"}
    style_visible = {"display": "table-row"}
    style_selected = {"background-color": "rgb(168 225 235)"}

    # Inicializar estilos
    new_style_a = style_visible
    new_style_b = style_visible
    new_style_c = style_visible
    new_style_d = style_visible
    new_style_e = style_visible
    new_style_f = style_visible
    new_style_g = style_visible
    new_style_h = style_visible
    new_style_i = style_visible
    new_style_j = style_visible
    new_style_a_min = style_visible
    new_style_b_min = style_visible
    new_style_c_min = style_visible
    new_style_d_min = style_visible
    new_style_e_min = style_visible
    new_style_f_min = style_visible
    new_style_g_min = style_visible
    new_style_h_min = style_visible
    new_style_i_min = style_hidden
    new_style_j_min = style_hidden
    new_style_k_min = style_hidden
    new_style_m_min = style_hidden
    new_style_n_min = style_hidden
    new_style_o_min = style_hidden
    new_style_p_min = style_hidden
    new_style_q_min = style_hidden
    new_style_r_min = style_hidden
    new_style_s_min = style_hidden
    new_style_t_min = style_hidden
    new_style_u_min = style_hidden
    new_style_v_min = style_hidden
    
    new_img_a_src = "/static/img/logos/diag_flecha.png"
    new_img_b_src = "/static/img/logos/diag_flecha.png"
    new_img_c_src = "/static/img/logos/diag_flecha.png"
    new_img_e_src = "/static/img/logos/diag_flecha.png"
    new_img_g_src = "/static/img/logos/diag_flecha.png"
    new_img_a_min_src = "/static/img/logos/diag_flecha.png"
    new_img_c_min_src = "/static/img/logos/diag_flecha.png"
    new_img_d_min_src = "/static/img/logos/diag_flecha.png"
    new_img_g_min_src = "/static/img/logos/diag_flecha.png"
    new_img_h_min_src = "/static/img/logos/diag_flecha.png"
    new_img_o_min_src = "/static/img/logos/diag_flecha.png"
    new_img_q_min_src = "/static/img/logos/diag_flecha.png"
    new_img_u_min_src = "/static/img/logos/diag_flecha.png"

    new_style_cmz_sumin_agua_negr_style = {"background-color": "initial"}
    new_style_cmz_pisc_agua_mar_style = {"background-color": "initial"}
    new_style_cmz_aguas_halladas_style = {"background-color": "initial"}
    new_style_cmz_agua_mineral_style = {"background-color": "initial"}
    new_style_cmz_servicios_style = {"background-color": "initial"}
    new_style_cmz_cont_polvo_style = {"background-color": "initial"}
    new_style_cmz_sx_ew_style =  {"background-color": "initial"}
    new_style_cmz_area_seca_style = {"background-color": "initial"}
    new_style_cmz_ptas_style = {"background-color": "initial"}
    new_style_cmz_tsf_style = {"background-color": "initial"}
    new_style_cmz_evaporacion_style = {"background-color": "initial"}
    new_style_cmz_retencion_style = {"background-color": "initial"}
    new_style_cmz_infiltracion_style = {"background-color": "initial"}

    # Inicializar estilos para sub-filas
    new_style_sub_a = [style_hidden] * 6
    new_style_sub_b = [style_hidden] * 3
    new_style_sub_c = [style_hidden] * 8
    new_style_sub_e = [style_hidden] * 4
    new_style_sub_g = [style_hidden] * 13
    new_style_sub_a_min = [style_hidden] * 3
    new_style_sub_c_min = [style_hidden] * 3
    new_style_sub_d_min = [style_hidden] * 4
    new_style_sub_g_min = [style_hidden] * 4
    new_style_sub_h_min = [style_hidden] * 4
    new_style_sub_o_min = [style_hidden] * 5
    new_style_sub_q_min = [style_hidden] * 3
    new_style_sub_u_min = [style_hidden] * 4

    # Recuperar clics
    n_clicks_negr = data.get('n_clicks_negr', 0)
    n_clicks_mar = data.get('n_clicks_mar', 0)
    n_clicks_halladas = data.get('n_clicks_halladas', 0)
    n_clicks_mineral = data.get('n_clicks_mineral', 0)
    n_clicks_servicios = data.get('n_clicks_servicios', 0)
    n_clicks_cont_polvo = data.get('n_clicks_cont_polvo', 0)
    n_clicks_sx_ew = data.get('n_clicks_sx_ew', 0)
    n_clicks_area_seca = data.get('n_clicks_area_seca', 0)
    n_clicks_ptas = data.get('n_clicks_ptas', 0)
    n_clicks_tsf = data.get('n_clicks_tsf', 0)
    n_clicks_evaporacion = data.get('n_clicks_evaporacion', 0)
    n_clicks_retencion = data.get('n_clicks_retencion', 0)
    n_clicks_infiltracion = data.get('n_clicks_infiltracion', 0)

    n_clicks_main_a = data.get('n_clicks_main_a', 0)
    n_clicks_main_b = data.get('n_clicks_main_b', 0)
    n_clicks_main_c = data.get('n_clicks_main_c', 0)
    n_clicks_main_e = data.get('n_clicks_main_e', 0)
    n_clicks_main_g = data.get('n_clicks_main_g', 0)

    n_clicks_main_a_min = data.get('n_clicks_main_a_min', 0)
    n_clicks_main_c_min = data.get('n_clicks_main_c_min', 0)
    n_clicks_main_d_min = data.get('n_clicks_main_d_min', 0)
    n_clicks_main_g_min = data.get('n_clicks_main_g_min', 0)
    n_clicks_main_h_min = data.get('n_clicks_main_h_min', 0)
    n_clicks_main_o_min = data.get('n_clicks_main_o_min', 0)
    n_clicks_main_q_min = data.get('n_clicks_main_q_min', 0)
    n_clicks_main_u_min = data.get('n_clicks_main_u_min', 0)


    # Lógica de interacción para 'cmz-sumin-agua-negr'
    if n_clicks_negr % 2 == 1:
        new_style_a = style_visible
        new_style_k_min = style_visible
        new_style_cmz_sumin_agua_negr_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden
        
        # Subfilas de Fila A
        if n_clicks_main_a % 2 == 1:
            new_style_sub_a = [style_visible] * 6
            new_img_a_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a = [style_hidden] * 6
            new_img_a_src = "/static/img/logos/diag_flecha.png"

    # Lógica de interacción para 'cmz-agua-nueva'
    elif n_clicks_mar % 2 == 1:
        new_style_a = style_visible
        new_style_i = style_visible
        new_style_a_min = style_visible
        new_style_b_min = style_visible
        new_style_c_min = style_visible
        new_style_d_min = style_visible
        new_style_k_min = style_visible
        new_style_m_min = style_visible
        new_style_n_min = style_visible
        new_style_cmz_pisc_agua_mar_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_j = style_hidden
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden

        # Subfilas de Fila A
        if n_clicks_main_a % 2 == 1:
            new_style_sub_a = [style_visible] * 6
            new_img_a_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a = [style_hidden] * 6
            new_img_a_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila a
        if n_clicks_main_a_min % 2 == 1:
            new_style_sub_a_min = [style_visible] * 3
            new_img_a_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a_min = [style_hidden] * 3
            new_img_a_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila c
        if n_clicks_main_c_min % 2 == 1:
            new_style_sub_c_min = [style_visible] * 3
            new_img_c_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_c_min = [style_hidden] * 3
            new_img_c_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila d
        if n_clicks_main_d_min % 2 == 1:
            new_style_sub_d_min = [style_visible] * 4
            new_img_d_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_d_min = [style_hidden] * 4
            new_img_d_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-aguas-halladas'
    elif n_clicks_halladas % 2 == 1:
        new_style_c = style_visible
        new_style_cmz_aguas_halladas_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden
        
        # Subfilas de Fila C
        if n_clicks_main_c % 2 == 1:
            new_style_sub_c = [style_visible] * 8
            new_img_c_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_c_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-agua-mineral'
    elif n_clicks_mineral % 2 == 1:
        new_style_b = style_visible
        new_style_cmz_agua_mineral_style = style_selected
    
        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden
        
        # Subfilas de Fila B
        if n_clicks_main_b % 2 == 1:
            new_style_sub_b = [style_visible] * 3
            new_img_b_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_b_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-servicios'
    elif n_clicks_servicios % 2 == 1:
        new_style_d_min = style_visible
        new_style_i_min = style_visible
        new_style_cmz_servicios_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_j_min = style_hidden  
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden

        # Subfilas de Fila d
        if n_clicks_main_d_min % 2 == 1:
            new_style_sub_d_min = [style_visible] * 4
            new_img_d_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_d_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-cont-polvo'
    elif n_clicks_cont_polvo % 2 == 1:
        new_style_c = style_visible
        new_style_h = style_visible
        new_style_c_min = style_visible
        new_style_j_min = style_visible
        new_style_cmz_cont_polvo_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden

        # Subfilas de Fila C
        if n_clicks_main_c % 2 == 1:
            new_style_sub_c = [style_visible] * 6
            new_img_c_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_c_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila c
        if n_clicks_main_c_min % 2 == 1:
            new_style_sub_c_min = [style_visible] * 3
            new_img_c_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_c_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-sx-ew'
    elif n_clicks_sx_ew % 2 == 1:
        new_style_b_min = style_visible
        new_style_g_min = style_visible
        new_style_h_min = style_visible
        new_style_cmz_sx_ew_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden

        # Subfilas de Fila g
        if n_clicks_main_g_min % 2 == 1:
            new_style_sub_g_min = [style_visible] * 4
            new_img_g_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_g_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila h
        if n_clicks_main_h_min % 2 == 1:
            new_style_sub_h_min = [style_visible] * 4
            new_img_h_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_h_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-area-seca'
    elif n_clicks_area_seca % 2 == 1:
        new_style_b = style_visible
        new_style_e = style_visible
        new_style_g = style_visible
        new_style_a_min = style_visible
        new_style_e_min = style_visible
        new_style_f_min = style_visible
        new_style_g_min = style_visible
        new_style_h_min = style_visible
        new_style_m_min = style_visible
        new_style_n_min = style_visible
        new_style_o_min = style_visible
        new_style_p_min = style_visible
        new_style_q_min = style_visible
        new_style_r_min = style_visible
        new_style_s_min = style_visible
        new_style_t_min = style_visible
        new_style_u_min = style_visible
        new_style_v_min = style_visible
        new_style_cmz_area_seca_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_f = style_hidden
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden

        # Subfilas de Fila B
        if n_clicks_main_b % 2 == 1:
            new_style_sub_b = [style_visible] * 3
            new_img_b_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_b_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila E
        if n_clicks_main_e % 2 == 1:
            new_style_sub_e = [style_visible] * 4
            new_img_e_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_e_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila G
        if n_clicks_main_g % 2 == 1:
            new_style_sub_g = [style_visible] * 13
            new_img_g_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_g_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila a
        if n_clicks_main_a_min % 2 == 1:
            new_style_sub_a_min = [style_visible] * 3
            new_img_a_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_a_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila g
        if n_clicks_main_g_min % 2 == 1:
            new_style_sub_g_min = [style_visible] * 4
            new_img_g_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_g_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila h
        if n_clicks_main_h_min % 2 == 1:
            new_style_sub_h_min = [style_visible] * 4
            new_img_h_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_h_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila o
        if n_clicks_main_o_min % 2 == 1:
            new_style_sub_o_min = [style_visible] * 5
            new_img_o_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_o_min = [style_hidden] * 5
            new_img_o_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila q
        if n_clicks_main_q_min % 2 == 1:
            new_style_sub_q_min = [style_visible] * 3
            new_img_q_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_q_min = [style_hidden] * 3
            new_img_q_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila u
        if n_clicks_main_u_min % 2 == 1:
            new_style_sub_u_min = [style_visible] * 4
            new_img_u_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_u_min = [style_hidden] * 4
            new_img_u_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-ptas'
    elif n_clicks_ptas % 2 == 1:
        new_style_i_min = style_visible
        new_style_j_min = style_visible
        new_style_cmz_ptas_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden


    # Lógica de interacción para 'cmz-tsf'
    elif n_clicks_tsf % 2 == 1:
        new_style_d = style_visible
        new_style_f = style_visible
        new_style_j = style_visible
        new_style_e_min = style_visible
        new_style_f_min = style_visible
        new_style_cmz_tsf_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden


    # Lógica de interacción para 'cmz-evaporacion'
    elif n_clicks_evaporacion % 2 == 1:
        new_style_f = style_visible
        new_style_g = style_visible
        new_style_h = style_visible
        new_style_i = style_visible
        new_style_cmz_evaporacion_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden

        # Subfilas de Fila G
        if n_clicks_main_g % 2 == 1:
            new_style_sub_g = [style_visible] * 13
            new_img_g_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_g_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-retencion'
    elif n_clicks_retencion % 2 == 1:
        new_style_d = style_visible
        new_style_e = style_visible
        new_style_cmz_retencion_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_j = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden

        # Subfilas de Fila E
        if n_clicks_main_e % 2 == 1:
            new_style_sub_e = [style_visible] * 4
            new_img_e_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_img_e_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para 'cmz-infiltracion'
    elif n_clicks_infiltracion % 2 == 1:
        new_style_j = style_visible
        new_style_cmz_infiltracion_style = style_selected
            
        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 6
        new_style_b = style_hidden
        new_style_sub_b = [style_hidden] * 3 
        new_style_c = style_hidden
        new_style_sub_c = [style_hidden] * 8
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 4
        new_style_f = style_hidden
        new_style_g = style_hidden
        new_style_sub_g = [style_hidden] * 13
        new_style_h = style_hidden
        new_style_i = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 3
        new_style_b_min = style_hidden
        new_style_c_min = style_hidden
        new_style_sub_c_min = [style_hidden] * 3
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 4
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 4
        new_style_h_min = style_hidden
        new_style_sub_h_min = [style_hidden] * 4
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden  
        new_style_k_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_o_min = style_hidden
        new_style_sub_o_min = [style_hidden] * 5
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        new_style_sub_q_min = [style_hidden] * 3
        new_style_r_min = style_hidden
        new_style_s_min = style_hidden
        new_style_t_min = style_hidden
        new_style_u_min = style_hidden
        new_style_sub_u_min = [style_hidden] * 4
        new_style_v_min = style_hidden


    # Si ninguna de las cajas está activa, reiniciar los estilos.
    else:
        if n_clicks_main_a % 2 == 1:
            new_style_sub_a = [style_visible] * 6
            new_img_a_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a = [style_hidden] * 6
            new_img_a_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_b % 2 == 1:
            new_style_sub_b = [style_visible] * 3
            new_img_b_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_b = [style_hidden] * 3
            new_img_b_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_c % 2 == 1:
            new_style_sub_c = [style_visible] * 8
            new_img_c_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_c = [style_hidden] * 8
            new_img_c_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_e % 2 == 1:
            new_style_sub_e = [style_visible] * 4
            new_img_e_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_e = [style_hidden] * 4
            new_img_e_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_g % 2 == 1:
            new_style_sub_g = [style_visible] * 13
            new_img_g_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_g = [style_hidden] * 13
            new_img_g_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_a_min % 2 == 1:
            new_style_sub_a_min = [style_visible] * 3
            new_img_a_min_src= "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a_min = [style_hidden] * 3
            new_img_a_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_c_min % 2 == 1:
            new_style_sub_c_min = [style_visible] * 3
            new_img_c_min_src= "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_c_min = [style_hidden] * 3
            new_img_c_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_d_min % 2 == 1:
            new_style_sub_d_min = [style_visible] * 4
            new_img_d_min_src= "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_d_min = [style_hidden] * 4
            new_img_d_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_g_min % 2 == 1:
            new_style_sub_g_min = [style_visible] * 4
            new_img_g_min_src= "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_g_min = [style_hidden] * 4
            new_img_g_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_h_min % 2 == 1:
            new_style_sub_h_min = [style_visible] * 4
            new_img_h_min_src= "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_h_min = [style_hidden] * 4
            new_img_h_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_o_min % 2 == 1:
            new_style_sub_o_min = [style_hidden] * 5
            new_img_o_min_src= "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_o_min = [style_hidden] * 5
            new_img_o_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_q_min % 2 == 1:
            new_style_sub_q_min = [style_hidden] * 3
            new_img_q_min_src= "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_q_min = [style_hidden] * 3
            new_img_q_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_u_min % 2 == 1:
            new_style_sub_u_min = [style_hidden] * 4
            new_img_u_min_src= "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_u_min = [style_hidden] * 4
            new_img_u_min_src = "/static/img/logos/diag_flecha.png"  

    response = {
        "new_style_a": new_style_a,
        "new_style_b": new_style_b,
        "new_style_c": new_style_c,
        "new_style_d": new_style_d,
        "new_style_e": new_style_e,
        "new_style_f": new_style_f,
        "new_style_g": new_style_g,
        "new_style_h": new_style_h,
        "new_style_i": new_style_i,
        "new_style_j": new_style_j,
        "new_style_a_min": new_style_a_min,
        "new_style_b_min": new_style_b_min,
        "new_style_c_min": new_style_c_min,
        "new_style_d_min": new_style_d_min,
        "new_style_e_min": new_style_e_min,
        "new_style_f_min": new_style_f_min,
        "new_style_g_min": new_style_g_min,
        "new_style_h_min": new_style_h_min,
        "new_style_i_min": new_style_i_min,
        "new_style_j_min": new_style_j_min,
        "new_style_k_min": new_style_k_min,
        "new_style_m_min": new_style_m_min,
        "new_style_n_min": new_style_n_min,
        "new_style_o_min": new_style_o_min,
        "new_style_p_min": new_style_p_min,
        "new_style_q_min": new_style_q_min,
        "new_style_r_min": new_style_r_min,
        "new_style_s_min": new_style_s_min,
        "new_style_t_min": new_style_t_min,
        "new_style_u_min": new_style_u_min,
        "new_style_v_min": new_style_v_min,

        "new_style_sub_a": new_style_sub_a,
        "new_style_sub_b": new_style_sub_b,
        "new_style_sub_c": new_style_sub_c,
        "new_style_sub_e": new_style_sub_e,
        "new_style_sub_g": new_style_sub_g,
        "new_style_sub_a_min": new_style_sub_a_min,
        "new_style_sub_c_min": new_style_sub_c_min,
        "new_style_sub_d_min": new_style_sub_d_min,
        "new_style_sub_g_min": new_style_sub_g_min,
        "new_style_sub_h_min": new_style_sub_h_min,
        "new_style_sub_o_min": new_style_sub_o_min,
        "new_style_sub_q_min": new_style_sub_q_min,
        "new_style_sub_u_min": new_style_sub_u_min,
        
        "new_style_cmz_sumin_agua_negr_style": new_style_cmz_sumin_agua_negr_style,
        "new_style_cmz_pisc_agua_mar_style": new_style_cmz_pisc_agua_mar_style,
        "new_style_cmz_aguas_halladas_style": new_style_cmz_aguas_halladas_style,
        "new_style_cmz_agua_mineral_style": new_style_cmz_agua_mineral_style,
        "new_style_cmz_servicios_style": new_style_cmz_servicios_style,
        "new_style_cmz_cont_polvo_style": new_style_cmz_cont_polvo_style,
        "new_style_cmz_sx_ew_style":  new_style_cmz_sx_ew_style,
        "new_style_cmz_area_seca_style": new_style_cmz_area_seca_style,
        "new_style_cmz_ptas_style": new_style_cmz_ptas_style,
        "new_style_cmz_tsf_style": new_style_cmz_tsf_style,
        "new_style_cmz_evaporacion_style": new_style_cmz_evaporacion_style,
        "new_style_cmz_retencion_style": new_style_cmz_retencion_style,
        "new_style_cmz_infiltracion_style": new_style_cmz_infiltracion_style,

        "new_img_a_src": new_img_a_src,
        "new_img_b_src": new_img_b_src,
        "new_img_c_src": new_img_c_src,
        "new_img_e_src": new_img_e_src,
        "new_img_g_src": new_img_g_src,
        "new_img_a_min_src": new_img_a_min_src,
        "new_img_c_min_src": new_img_c_min_src,
        "new_img_d_min_src": new_img_d_min_src,
        "new_img_g_min_src": new_img_g_min_src,
        "new_img_h_min_src": new_img_h_min_src,
        "new_img_o_min_src": new_img_o_min_src,
        "new_img_q_min_src": new_img_q_min_src,
        "new_img_u_min_src": new_img_u_min_src,
    }

    return jsonify(response)