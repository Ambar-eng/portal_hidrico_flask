from datetime import datetime
from flask import Blueprint, render_template, request, session, jsonify, current_app
from app.utils.utils import generar_saludo

diagflujo_ant_bp = Blueprint('diagrama_flujo_ant', __name__)

def obtener_datos_cosmos_diag_ant():
    app = current_app._get_current_object()
    cache = app.cache

    #Obtener los datos de la caché para Antucoya
    df_ph_ant = cache.get('ph_ant_data')
    if df_ph_ant is None:
        cosmos_client = app.config['COSMOS_CLIENT']
        df_ph_ant = cosmos_client.get_items_from_container(
            'PH_ANT', 
            'amsa_datos_hidricos_web.dmt_ant_reporte_hidrico_flujo'
        )
        cache.set('ph_ant_data', df_ph_ant, timeout=3600)

    # Intentar obtener los datos actuales de la caché para combinarlos
    cached_data = cache.get('ph_ant_data')

    # Si la caché no tiene datos, iniciamos una lista vacía
    if cached_data is None:
        cached_data = []

    # Filtrar duplicados antes de agregar los nuevos datos a la caché
    fechas_en_cache = {dato['fecha'] for dato in cached_data}
    df_ph_ant = [dato for dato in df_ph_ant if dato['fecha'] not in fechas_en_cache]

    # Guardar los datos combinados (actualizados) en la caché, sin duplicados
    cache.set('ph_ant_data', cached_data + df_ph_ant, timeout=3600)

    return cached_data + df_ph_ant

#Función para obtener la fecha máxima
def obtener_fecha_maxima_diag_ant(datos):
    if datos:
        # Obtener todas las fechas
        fechas = [dato['fecha'] for dato in datos if 'fecha' in dato]
        
        if fechas:
            # Convertir las fechas a objetos datetime y calcular la fecha máxima
            fecha_maxima = max(datetime.strptime(fecha, '%Y-%m-%d') for fecha in fechas)
            return fecha_maxima
    return None


#Función para actualizar la fecha de actualización
def obtener_mensaje_fecha_diag_ant(fecha_maxima):
    if fecha_maxima:
        fecha_formateada = fecha_maxima.strftime('%d-%m-%Y')
        return f"Actualizado con datos hasta {fecha_formateada}"
    else:
        return "No se encontraron datos para mostrar"
    


def procesar_datos_diag_ant(fecha, ant_temporalidad, ant_medida):

    app = current_app._get_current_object()

    # Validar que fecha no sea nula o vacía
    if not fecha:
        # Retornar valores predeterminados si los valores son nulos
        return tuple("0" for _ in range(100)) 

    # Consultar la caché
    df_ph_ant = app.cache.get('ph_ant_data')
    if not df_ph_ant:
        df_ph_ant = []

    print(f"Datos iniciales en caché: {len(df_ph_ant)}")
    
    fecha_presente = any(item['fecha'] == fecha for item in df_ph_ant) # Debería devolver true or false
    print(f'La fecha {fecha} está en caché inicial?: {fecha_presente}')  

    if not fecha_presente and fecha :
        print("Consultando datos cosmos")
        cosmos_client = app.config['COSMOS_CLIENT']
        nuevos_datos = cosmos_client.get_items_from_container(
            'PH_ANT', 
            'amsa_datos_hidricos_web.dmt_ant_reporte_hidrico_flujo',
            fecha,
            fecha
        ) 

        # Combinar datos nuevos con los existentes
        df_ph_ant += nuevos_datos
        print(f"Nuevos datos a agregar a la caché: {len(nuevos_datos)}")

        # Actualizar la caché
        app.cache.set('ph_ant_data', df_ph_ant, timeout=3600)
        print(f'Actualización de caché realizada con {len(nuevos_datos)} nuevos registros.')

        df_ph_ant = app.cache.get('ph_ant_data')

    datos_filtrados = [
        dato for dato in df_ph_ant
        if dato.get('fecha') == fecha
        and dato.get('temporalidad') == ant_temporalidad
        and dato.get('medida') == ant_medida
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
    tb_agua_mar_a_agua_nueva_ant = filtrar_valor(datos_filtrados, "A", "Real")
    tb_agua_mar_a_agua_nueva_proy_ant = filtrar_valor(datos_filtrados, "A", "Proyectado")

    #Tabla Flujo A.1
    tb_alimentacion_ro_i_ant = filtrar_valor(datos_filtrados, "A.1", "Real")
    tb_alimentacion_ro_i_proy_ant = filtrar_valor(datos_filtrados, "A.1", "Proyectado")

    #Tabla Flujo A.2
    tb_reposicion_piscina_agua_mar_ant = filtrar_valor(datos_filtrados, "A.2", "Real")
    tb_reposicion_piscina_agua_mar_proy_ant = filtrar_valor(datos_filtrados, "A.2", "Proyectado")

    #Tabla Flujo B
    tb_agua_mineral_a_area_seca_ant = filtrar_valor(datos_filtrados, "B", "Real")
    tb_agua_mineral_a_area_seca_proy_ant = filtrar_valor(datos_filtrados, "B", "Proyectado")
    
    #Tabla Flujo C
    tb_agua_nueva_a_evaporacion_ant = filtrar_valor(datos_filtrados, "C", "Real")
    tb_agua_nueva_a_evaporacion_proy_ant = filtrar_valor(datos_filtrados, "C", "Proyectado")
    
    #Tabla Flujo D
    tb_control_polvo_a_evaporacion_ant = filtrar_valor(datos_filtrados, "D", "Real")
    tb_control_polvo_a_evaporacion_proy_ant = filtrar_valor(datos_filtrados, "D", "Proyectado")
    
    #Tabla Flujo E
    tb_area_seca_a_evaporacion_ant = filtrar_valor(datos_filtrados, "E", "Real")
    tb_area_seca_a_evaporacion_proy_ant = filtrar_valor(datos_filtrados, "E", "Proyectado")
    
    #Tabla Flujo E.1
    tb_evaporacion_pilas_ant = filtrar_valor(datos_filtrados, "E.1", "Real")
    tb_evaporacion_pilas_proy_ant = filtrar_valor(datos_filtrados, "E.1", "Proyectado")
    
    #Tabla Flujo E.2
    tb_evaporacion_piscinas_ant = filtrar_valor(datos_filtrados, "E.2", "Real")
    tb_evaporacion_piscinas_proy_ant = filtrar_valor(datos_filtrados, "E.2", "Proyectado")
    
    #Tabla Flujo E.2.1
    tb_evap_piscinas_ils_ant = filtrar_valor(datos_filtrados, "E.2.1", "Real")
    tb_evap_piscinas_ils_proy_ant = filtrar_valor(datos_filtrados, "E.2.1", "Proyectado")
    
    #Tabla Flujo E.2.2
    tb_evap_piscinas_pls_ant = filtrar_valor(datos_filtrados, "E.2.2", "Real")
    tb_evap_piscinas_pls_proy_ant = filtrar_valor(datos_filtrados, "E.2.2", "Proyectado")
    
    #Tabla Flujo E.2.3
    tb_evap_piscinas_rr_ant = filtrar_valor(datos_filtrados, "E.2.3", "Real")
    tb_evap_piscinas_rr_proy_ant = filtrar_valor(datos_filtrados, "E.2.3", "Proyectado")
    
    #Tabla Flujo E.2.4
    tb_evap_piscinas_rp_ant = filtrar_valor(datos_filtrados, "E.2.4", "Real")
    tb_evap_piscinas_rp_proy_ant = filtrar_valor(datos_filtrados, "E.2.4", "Proyectado")
    
    #Tabla Flujo F
    tb_area_seca_a_retencion_ant = filtrar_valor(datos_filtrados, "F", "Real")
    tb_area_seca_a_retencion_proy_ant = filtrar_valor(datos_filtrados, "F", "Proyectado")
    
    #Tabla Flujo a
    tb_agua_nueva_a_area_seca_humeda_ant = filtrar_valor(datos_filtrados, "a", "Real")
    tb_agua_nueva_a_area_seca_humeda_proy_ant = filtrar_valor(datos_filtrados, "a", "Proyectado")
    
    #Tabla Flujo a.1
    tb_agua_nueva_a_area_seca_ant = filtrar_valor(datos_filtrados, "a.1", "Real")
    tb_agua_nueva_a_area_seca_proy_ant = filtrar_valor(datos_filtrados, "a.1", "Proyectado")
    
    #Tabla Flujo a.1.1
    tb_agua_desalada_a_chancado_i_ant = filtrar_valor(datos_filtrados, "a.1.1", "Real")
    tb_agua_desalada_a_chancado_i_proy_ant = filtrar_valor(datos_filtrados, "a.1.1", "Proyectado")
    
    #Tabla Flujo a.1.2
    tb_agua_desalada_a_chancado_ii_iii_ant = filtrar_valor(datos_filtrados, "a.1.2", "Real")
    tb_agua_desalada_a_chancado_ii_iii_proy_ant = filtrar_valor(datos_filtrados, "a.1.2", "Proyectado")
    
    #Tabla Flujo a.2
    tb_agua_nueva_a_area_humeda_ant = filtrar_valor(datos_filtrados, "a.2", "Real")
    tb_agua_nueva_a_area_humeda_proy_ant = filtrar_valor(datos_filtrados, "a.2", "Proyectado")
    
    #Tabla Flujo a.2.1
    tb_agua_desalada_a_aglomeracion_ant = filtrar_valor(datos_filtrados, "a.2.1", "Real")
    tb_agua_desalada_a_aglomeracion_proy_ant = filtrar_valor(datos_filtrados, "a.2.1", "Proyectado")
    
    #Tabla Flujo a.2.2
    tb_agua_mar_a_tambores_aglo_ant = filtrar_valor(datos_filtrados, "a.2.2", "Real")
    tb_agua_mar_a_tambores_aglo_proy_ant = filtrar_valor(datos_filtrados, "a.2.2", "Proyectado")
    
    #Tabla Flujo a.2.3
    tb_reposicion_am_a_refino_rp_rr_ant = filtrar_valor(datos_filtrados, "a.2.3", "Real")
    tb_reposicion_am_a_refino_rp_rr_proy_ant = filtrar_valor(datos_filtrados, "a.2.3", "Proyectado")
    
    #Tabla Flujo a.2.4
    tb_reposicion_am_a_piscina_ils_ant = filtrar_valor(datos_filtrados, "a.2.4", "Real")
    tb_reposicion_am_a_piscina_ils_proy_ant = filtrar_valor(datos_filtrados, "a.2.4", "Proyectado")
    
    #Tabla Flujo a.2.5
    tb_rechazo_a_refino_ant = filtrar_valor(datos_filtrados, "a.2.5", "Real")
    tb_rechazo_a_refino_proy_ant = filtrar_valor(datos_filtrados, "a.2.5", "Proyectado")
    
    #Tabla Flujo b
    tb_agua_nueva_a_sx_ew_ant = filtrar_valor(datos_filtrados, "b", "Real")
    tb_agua_nueva_a_sx_ew_proy_ant = filtrar_valor(datos_filtrados, "b", "Proyectado")
    
    #Tabla Flujo b.1
    tb_agua_desmineralizada_a_sx_ew_ant = filtrar_valor(datos_filtrados, "b.1", "Real")
    tb_agua_desmineralizada_a_sx_ew_proy_ant = filtrar_valor(datos_filtrados, "b.1", "Proyectado")
    
    #Tabla Flujo b.1.1
    tb_agua_desmineralizada_a_sx_ant = filtrar_valor(datos_filtrados, "b.1.1", "Real")
    tb_agua_desmineralizada_a_sx_proy_ant = filtrar_valor(datos_filtrados, "b.1.1", "Proyectado")
    
    #Tabla Flujo b.1.2
    tb_agua_desmineralizada_a_ew_ant = filtrar_valor(datos_filtrados, "b.1.2", "Real")
    tb_agua_desmineralizada_a_ew_proy_ant = filtrar_valor(datos_filtrados, "b.1.2", "Proyectado")
    
    #Tabla Flujo b.2
    tb_agua_desalada_a_sx_ew_ant = filtrar_valor(datos_filtrados, "b.2", "Real")
    tb_agua_desalada_a_sx_ew_proy_ant = filtrar_valor(datos_filtrados, "b.2", "Proyectado")
    
    #Tabla Flujo c
    tb_agua_nueva_a_control_polvo_ant = filtrar_valor(datos_filtrados, "c", "Real")
    tb_agua_nueva_a_control_polvo_proy_ant = filtrar_valor(datos_filtrados, "c", "Proyectado")
    
    #Tabla Flujo d
    tb_agua_nueva_a_servicios_ant = filtrar_valor(datos_filtrados, "d", "Real")
    tb_agua_nueva_a_servicios_proy_ant = filtrar_valor(datos_filtrados, "d", "Proyectado")
    
    #Tabla Flujo d.1
    tb_agua_desalada_a_taller_camiones_ant = filtrar_valor(datos_filtrados, "d.1", "Real")
    tb_agua_desalada_a_taller_camiones_proy_ant = filtrar_valor(datos_filtrados, "d.1", "Proyectado")
    
    #Tabla Flujo d.2
    tb_agua_potable_ant = filtrar_valor(datos_filtrados, "d.2", "Real")
    tb_agua_potable_proy_ant = filtrar_valor(datos_filtrados, "d.2", "Proyectado")
    
    #Tabla Flujo e
    tb_area_seca_a_sx_ew_ant = filtrar_valor(datos_filtrados, "e", "Real")
    tb_area_seca_a_sx_ew_proy_ant = filtrar_valor(datos_filtrados, "e", "Proyectado")
    
    #Tabla Flujo f
    tb_sx_ew_a_area_seca_ant = filtrar_valor(datos_filtrados, "f", "Real")
    tb_sx_ew_a_area_seca_proy_ant = filtrar_valor(datos_filtrados, "f", "Proyectado")

    #Tabla Flujo g
    tb_servicios_a_ptas_ant = filtrar_valor(datos_filtrados, "g", "Real")
    tb_servicios_a_ptas_proy_ant = filtrar_valor(datos_filtrados, "g", "Proyectado")
    
    #Tabla Flujo g.1
    tb_taller_camiones_a_ptas_ant = filtrar_valor(datos_filtrados, "g.1", "Real")
    tb_taller_camiones_a_ptas_proy_ant = filtrar_valor(datos_filtrados, "g.1", "Proyectado")
    
    #Tabla Flujo g.2
    tb_campamento_a_ptas_ant = filtrar_valor(datos_filtrados, "g.2", "Real")
    tb_campamento_a_ptas_proy_ant = filtrar_valor(datos_filtrados, "g.2", "Proyectado")
    
    #Tabla Flujo h
    tb_ptas_a_control_polvo_ant = filtrar_valor(datos_filtrados, "h", "Real")
    tb_ptas_a_control_polvo_proy_ant = filtrar_valor(datos_filtrados, "h", "Proyectado")
    
    #Tabla Flujo i
    tb_ro_primario_a_tk_desalada_ant = filtrar_valor(datos_filtrados, "i", "Real")
    tb_ro_primario_a_tk_desalada_proy_ant = filtrar_valor(datos_filtrados, "i", "Proyectado")
    
    #Tabla Flujo j
    tb_tk_desalada_a_ro_secundario_ant = filtrar_valor(datos_filtrados, "j", "Real")
    tb_tk_desalada_a_ro_secundario_proy_ant = filtrar_valor(datos_filtrados, "j", "Proyectado")
    
    #Tabla Flujo k
    tb_ro_secundario_a_tk_desmineralizada_ant = filtrar_valor(datos_filtrados, "k", "Real")
    tb_ro_secundario_a_tk_desmineralizada_proy_ant = filtrar_valor(datos_filtrados, "k", "Proyectado")
    
    #Tabla Flujo l
    tb_ro_secundario_a_tk_rechazo_ant = filtrar_valor(datos_filtrados, "l", "Real")
    tb_ro_secundario_a_tk_rechazo_proy_ant = filtrar_valor(datos_filtrados, "l", "Proyectado")
    
    #Tabla Flujo m
    tb_ro_primario_a_tk_rechazo_ant = filtrar_valor(datos_filtrados, "m", "Real")
    tb_ro_primario_a_tk_rechazo_proy_ant = filtrar_valor(datos_filtrados, "m", "Proyectado")
    
    #Tabla Flujo n
    tb_pilas_a_piscinas_ils_pls_ant = filtrar_valor(datos_filtrados, "n", "Real")
    tb_pilas_a_piscinas_ils_pls_proy_ant = filtrar_valor(datos_filtrados, "n", "Proyectado")
    
    #Tabla Flujo n.1
    tb_pilas_a_piscinas_ils_ant = filtrar_valor(datos_filtrados, "n.1", "Real")
    tb_pilas_a_piscinas_ils_proy_ant = filtrar_valor(datos_filtrados, "n.1", "Proyectado")
    
    #Tabla Flujo n.2
    tb_pilas_a_piscinas_pls_ant = filtrar_valor(datos_filtrados, "n.2", "Real")
    tb_pilas_a_piscinas_pls_proy_ant = filtrar_valor(datos_filtrados, "n.2", "Proyectado")
    
    #Tabla Flujo o
    tb_pilas_hl_rom_a_ripios_ant = filtrar_valor(datos_filtrados, "o", "Real")
    tb_pilas_hl_rom_a_ripios_proy_ant = filtrar_valor(datos_filtrados, "o", "Proyectado")
    
    #Tabla Flujo p
    tb_piscinas_refino_a_pilas_ant = filtrar_valor(datos_filtrados, "p", "Real")
    tb_piscinas_refino_a_pilas_proy_ant = filtrar_valor(datos_filtrados, "p", "Proyectado")
    
    #Tabla Flujo q
    tb_piscinas_ils_pls_a_pilas_ant = filtrar_valor(datos_filtrados, "q", "Real")
    tb_piscinas_ils_pls_a_pilas_proy_ant = filtrar_valor(datos_filtrados, "q", "Proyectado")

    datos_ant = {
        'tb_agua_mar_a_agua_nueva_ant': tb_agua_mar_a_agua_nueva_ant,
        'tb_agua_mar_a_agua_nueva_proy_ant': tb_agua_mar_a_agua_nueva_proy_ant,
        'tb_alimentacion_ro_i_ant': tb_alimentacion_ro_i_ant,
        'tb_alimentacion_ro_i_proy_ant': tb_alimentacion_ro_i_proy_ant,
        'tb_reposicion_piscina_agua_mar_ant': tb_reposicion_piscina_agua_mar_ant,
        'tb_reposicion_piscina_agua_mar_proy_ant': tb_reposicion_piscina_agua_mar_proy_ant,
        'tb_agua_mineral_a_area_seca_ant': tb_agua_mineral_a_area_seca_ant,
        'tb_agua_mineral_a_area_seca_proy_ant': tb_agua_mineral_a_area_seca_proy_ant,
        'tb_agua_nueva_a_evaporacion_ant': tb_agua_nueva_a_evaporacion_ant,
        'tb_agua_nueva_a_evaporacion_proy_ant': tb_agua_nueva_a_evaporacion_proy_ant,
        'tb_control_polvo_a_evaporacion_ant': tb_control_polvo_a_evaporacion_ant,
        'tb_control_polvo_a_evaporacion_proy_ant': tb_control_polvo_a_evaporacion_proy_ant,
        'tb_area_seca_a_evaporacion_ant': tb_area_seca_a_evaporacion_ant,
        'tb_area_seca_a_evaporacion_proy_ant': tb_area_seca_a_evaporacion_proy_ant,
        'tb_evaporacion_pilas_ant': tb_evaporacion_pilas_ant,
        'tb_evaporacion_pilas_proy_ant': tb_evaporacion_pilas_proy_ant,
        'tb_evaporacion_piscinas_ant': tb_evaporacion_piscinas_ant,
        'tb_evaporacion_piscinas_proy_ant': tb_evaporacion_piscinas_proy_ant,
        'tb_evap_piscinas_ils_ant': tb_evap_piscinas_ils_ant,
        'tb_evap_piscinas_ils_proy_ant': tb_evap_piscinas_ils_proy_ant,
        'tb_evap_piscinas_pls_ant': tb_evap_piscinas_pls_ant,
        'tb_evap_piscinas_pls_proy_ant': tb_evap_piscinas_pls_proy_ant,
        'tb_evap_piscinas_rr_ant': tb_evap_piscinas_rr_ant,
        'tb_evap_piscinas_rr_proy_ant': tb_evap_piscinas_rr_proy_ant,
        'tb_evap_piscinas_rp_ant': tb_evap_piscinas_rp_ant,
        'tb_evap_piscinas_rp_proy_ant': tb_evap_piscinas_rp_proy_ant,
        'tb_area_seca_a_retencion_ant': tb_area_seca_a_retencion_ant,
        'tb_area_seca_a_retencion_proy_ant': tb_area_seca_a_retencion_proy_ant,
        'tb_agua_nueva_a_area_seca_humeda_ant': tb_agua_nueva_a_area_seca_humeda_ant,
        'tb_agua_nueva_a_area_seca_humeda_proy_ant': tb_agua_nueva_a_area_seca_humeda_proy_ant,
        'tb_agua_nueva_a_area_seca_ant': tb_agua_nueva_a_area_seca_ant,
        'tb_agua_nueva_a_area_seca_proy_ant': tb_agua_nueva_a_area_seca_proy_ant,
        'tb_agua_desalada_a_chancado_i_ant': tb_agua_desalada_a_chancado_i_ant,
        'tb_agua_desalada_a_chancado_i_proy_ant': tb_agua_desalada_a_chancado_i_proy_ant,
        'tb_agua_desalada_a_chancado_ii_iii_ant': tb_agua_desalada_a_chancado_ii_iii_ant,
        'tb_agua_desalada_a_chancado_ii_iii_proy_ant': tb_agua_desalada_a_chancado_ii_iii_proy_ant,
        'tb_agua_nueva_a_area_humeda_ant': tb_agua_nueva_a_area_humeda_ant,
        'tb_agua_nueva_a_area_humeda_proy_ant': tb_agua_nueva_a_area_humeda_proy_ant,
        'tb_agua_desalada_a_aglomeracion_ant': tb_agua_desalada_a_aglomeracion_ant,
        'tb_agua_desalada_a_aglomeracion_proy_ant': tb_agua_desalada_a_aglomeracion_proy_ant,
        'tb_agua_mar_a_tambores_aglo_ant': tb_agua_mar_a_tambores_aglo_ant,
        'tb_agua_mar_a_tambores_aglo_proy_ant': tb_agua_mar_a_tambores_aglo_proy_ant,
        'tb_reposicion_am_a_refino_rp_rr_ant': tb_reposicion_am_a_refino_rp_rr_ant,
        'tb_reposicion_am_a_refino_rp_rr_proy_ant': tb_reposicion_am_a_refino_rp_rr_proy_ant,
        'tb_reposicion_am_a_piscina_ils_ant': tb_reposicion_am_a_piscina_ils_ant,
        'tb_reposicion_am_a_piscina_ils_proy_ant': tb_reposicion_am_a_piscina_ils_proy_ant,
        'tb_rechazo_a_refino_ant': tb_rechazo_a_refino_ant,
        'tb_rechazo_a_refino_proy_ant': tb_rechazo_a_refino_proy_ant,
        'tb_agua_nueva_a_sx_ew_ant': tb_agua_nueva_a_sx_ew_ant,
        'tb_agua_nueva_a_sx_ew_proy_ant': tb_agua_nueva_a_sx_ew_proy_ant,
        'tb_agua_desmineralizada_a_sx_ew_ant': tb_agua_desmineralizada_a_sx_ew_ant,
        'tb_agua_desmineralizada_a_sx_ew_proy_ant': tb_agua_desmineralizada_a_sx_ew_proy_ant,
        'tb_agua_desmineralizada_a_sx_ant': tb_agua_desmineralizada_a_sx_ant,
        'tb_agua_desmineralizada_a_sx_proy_ant': tb_agua_desmineralizada_a_sx_proy_ant,
        'tb_agua_desmineralizada_a_ew_ant': tb_agua_desmineralizada_a_ew_ant,
        'tb_agua_desmineralizada_a_ew_proy_ant': tb_agua_desmineralizada_a_ew_proy_ant,
        'tb_agua_desalada_a_sx_ew_ant': tb_agua_desalada_a_sx_ew_ant,
        'tb_agua_desalada_a_sx_ew_proy_ant': tb_agua_desalada_a_sx_ew_proy_ant,
        'tb_agua_nueva_a_control_polvo_ant': tb_agua_nueva_a_control_polvo_ant,
        'tb_agua_nueva_a_control_polvo_proy_ant': tb_agua_nueva_a_control_polvo_proy_ant,
        'tb_agua_nueva_a_servicios_ant': tb_agua_nueva_a_servicios_ant,
        'tb_agua_nueva_a_servicios_proy_ant': tb_agua_nueva_a_servicios_proy_ant,
        'tb_agua_desalada_a_taller_camiones_ant': tb_agua_desalada_a_taller_camiones_ant,
        'tb_agua_desalada_a_taller_camiones_proy_ant': tb_agua_desalada_a_taller_camiones_proy_ant,
        'tb_agua_potable_ant': tb_agua_potable_ant,
        'tb_agua_potable_proy_ant': tb_agua_potable_proy_ant,
        'tb_area_seca_a_sx_ew_ant': tb_area_seca_a_sx_ew_ant,
        'tb_area_seca_a_sx_ew_proy_ant': tb_area_seca_a_sx_ew_proy_ant,
        'tb_sx_ew_a_area_seca_ant': tb_sx_ew_a_area_seca_ant,
        'tb_sx_ew_a_area_seca_proy_ant': tb_sx_ew_a_area_seca_proy_ant,
        'tb_servicios_a_ptas_ant': tb_servicios_a_ptas_ant,
        'tb_servicios_a_ptas_proy_ant': tb_servicios_a_ptas_proy_ant,
        'tb_taller_camiones_a_ptas_ant': tb_taller_camiones_a_ptas_ant,
        'tb_taller_camiones_a_ptas_proy_ant': tb_taller_camiones_a_ptas_proy_ant,
        'tb_campamento_a_ptas_ant': tb_campamento_a_ptas_ant,
        'tb_campamento_a_ptas_proy_ant': tb_campamento_a_ptas_proy_ant,
        'tb_ptas_a_control_polvo_ant': tb_ptas_a_control_polvo_ant,
        'tb_ptas_a_control_polvo_proy_ant': tb_ptas_a_control_polvo_proy_ant,
        'tb_ro_primario_a_tk_desalada_ant': tb_ro_primario_a_tk_desalada_ant,
        'tb_ro_primario_a_tk_desalada_proy_ant': tb_ro_primario_a_tk_desalada_proy_ant,
        'tb_tk_desalada_a_ro_secundario_ant': tb_tk_desalada_a_ro_secundario_ant,
        'tb_tk_desalada_a_ro_secundario_proy_ant': tb_tk_desalada_a_ro_secundario_proy_ant,
        'tb_ro_secundario_a_tk_desmineralizada_ant': tb_ro_secundario_a_tk_desmineralizada_ant,
        'tb_ro_secundario_a_tk_desmineralizada_proy_ant': tb_ro_secundario_a_tk_desmineralizada_proy_ant,
        'tb_ro_secundario_a_tk_rechazo_ant': tb_ro_secundario_a_tk_rechazo_ant,
        'tb_ro_secundario_a_tk_rechazo_proy_ant': tb_ro_secundario_a_tk_rechazo_proy_ant,
        'tb_ro_primario_a_tk_rechazo_ant': tb_ro_primario_a_tk_rechazo_ant,
        'tb_ro_primario_a_tk_rechazo_proy_ant': tb_ro_primario_a_tk_rechazo_proy_ant,
        'tb_pilas_a_piscinas_ils_pls_ant': tb_pilas_a_piscinas_ils_pls_ant,
        'tb_pilas_a_piscinas_ils_pls_proy_ant': tb_pilas_a_piscinas_ils_pls_proy_ant,
        'tb_pilas_a_piscinas_ils_ant': tb_pilas_a_piscinas_ils_ant,
        'tb_pilas_a_piscinas_ils_proy_ant': tb_pilas_a_piscinas_ils_proy_ant,
        'tb_pilas_a_piscinas_pls_ant': tb_pilas_a_piscinas_pls_ant,
        'tb_pilas_a_piscinas_pls_proy_ant': tb_pilas_a_piscinas_pls_proy_ant,
        'tb_pilas_hl_rom_a_ripios_ant': tb_pilas_hl_rom_a_ripios_ant,
        'tb_pilas_hl_rom_a_ripios_proy_ant': tb_pilas_hl_rom_a_ripios_proy_ant,
        'tb_piscinas_refino_a_pilas_ant': tb_piscinas_refino_a_pilas_ant,
        'tb_piscinas_refino_a_pilas_proy_ant': tb_piscinas_refino_a_pilas_proy_ant,
        'tb_piscinas_ils_pls_a_pilas_ant': tb_piscinas_ils_pls_a_pilas_ant,
        'tb_piscinas_ils_pls_a_pilas_proy_ant': tb_piscinas_ils_pls_a_pilas_proy_ant,
    }

    return(datos_ant)


##############################################################################################

def toggle_rows_logic_ant(data):
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
    new_style_l_min = style_hidden
    new_style_m_min = style_hidden
    new_style_n_min = style_hidden
    new_style_o_min = style_hidden
    new_style_p_min = style_hidden
    new_style_q_min = style_hidden
    
    new_img_a_src = "/static/img/logos/diag_flecha.png"
    new_img_e_src = "/static/img/logos/diag_flecha.png"
    new_img_a_min_src = "/static/img/logos/diag_flecha.png"
    new_img_b_min_src = "/static/img/logos/diag_flecha.png"
    new_img_d_min_src = "/static/img/logos/diag_flecha.png"
    new_img_g_min_src = "/static/img/logos/diag_flecha.png"
    new_img_n_min_src = "/static/img/logos/diag_flecha.png"

    new_style_ant_agua_nueva_style = {"background-color": "initial"}
    new_style_ant_servicios_style = {"background-color": "initial"}
    new_style_ant_sumin_terceros_style = {"background-color": "initial"}
    new_style_ant_agua_mineral_style = {"background-color": "initial"}
    new_style_ant_cont_polvo_style = {"background-color": "initial"}
    new_style_ant_sx_ew_style = {"background-color": "initial"}
    new_style_ant_area_seca_style = {"background-color": "initial"}
    new_style_ant_ptas_style = {"background-color": "initial"}
    new_style_ant_evaporacion_style = {"background-color": "initial"}
    new_style_ant_retencion_style = {"background-color": "initial"}

    # Inicializar estilos para sub-filas
    new_style_sub_a = [style_hidden] * 2
    new_style_sub_e = [style_hidden] * 6
    new_style_sub_a_min = [style_hidden] * 9
    new_style_sub_b_min = [style_hidden] * 4
    new_style_sub_d_min = [style_hidden] * 2
    new_style_sub_g_min = [style_hidden] * 2
    new_style_sub_n_min = [style_hidden] * 2

    # Recuperar clics
    n_clicks_agua_nueva = data.get('n_clicks_agua_nueva', 0)
    n_clicks_serv = data.get('n_clicks_serv', 0)
    n_clicks_sumin = data.get('n_clicks_sumin', 0)
    n_clicks_mineral = data.get('n_clicks_mineral', 0)
    n_clicks_polvo = data.get('n_clicks_polvo', 0)
    n_clicks_sx_ew = data.get('n_clicks_sx_ew', 0)
    n_clicks_seca = data.get('n_clicks_seca', 0)
    n_clicks_ptas = data.get('n_clicks_ptas', 0)
    n_clicks_evap = data.get('n_clicks_evap', 0)
    n_clicks_reten = data.get('n_clicks_reten', 0)

    n_clicks_main_a = data.get('n_clicks_main_a', 0)
    n_clicks_main_e = data.get('n_clicks_main_e', 0)
    n_clicks_main_a_min = data.get('n_clicks_main_a_min', 0)
    n_clicks_main_b_min = data.get('n_clicks_main_b_min', 0)
    n_clicks_main_d_min = data.get('n_clicks_main_d_min', 0)
    n_clicks_main_g_min = data.get('n_clicks_main_g_min', 0)
    n_clicks_main_n_min = data.get('n_clicks_main_n_min', 0)


    # Lógica de interacción para ant-agua-nueva
    if n_clicks_agua_nueva % 2 == 1:
        new_style_a = style_visible
        new_style_c = style_visible
        new_style_a_min = style_visible
        new_style_b_min = style_visible
        new_style_c_min = style_visible
        new_style_d_min = style_visible
        new_style_i_min = style_visible
        new_style_j_min = style_visible
        new_style_k_min = style_visible
        new_style_l_min = style_visible
        new_style_m_min = style_visible
        # new_style_n_min = style_visible #solo de prueba
        new_style_ant_agua_nueva_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_b = style_hidden
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 6
        new_style_f = style_hidden
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 2
        new_style_h_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_o_min = style_hidden
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden
        
        # Subfilas de Fila A
        if n_clicks_main_a % 2 == 1:
            new_style_sub_a = [style_visible] * 2
            new_img_a_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a = [style_hidden] * 2
            new_img_a_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila a
        if n_clicks_main_a_min % 2 == 1:
            new_style_sub_a_min = [style_visible] * 9
            new_img_a_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a_min = [style_hidden] * 9
            new_img_a_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila b
        if n_clicks_main_b_min % 2 == 1:
            new_style_sub_b_min = [style_visible] * 4
            new_img_b_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_b_min = [style_hidden] * 4
            new_img_b_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila d
        if n_clicks_main_d_min % 2 == 1:
            new_style_sub_d_min = [style_visible] * 2
            new_img_d_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_d_min = [style_hidden] * 2
            new_img_d_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila n - SÓLO DE PRUEBA
        # if n_clicks_main_n_min % 2 == 1:
        #     new_style_sub_n_min = [style_visible] * 2
        #     new_img_n_min_src = "/static/img/logos/diag_flecha_abajo.png"
        # else:
        #     new_style_sub_n_min = [style_hidden] * 2
        #     new_img_n_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para ant-servicios
    elif n_clicks_serv % 2 == 1:
        new_style_d_min = style_visible
        new_style_g_min = style_visible
        new_style_ant_servicios_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 2
        new_style_b = style_hidden
        new_style_c = style_hidden
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 6
        new_style_f = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 9
        new_style_b_min = style_hidden
        new_style_sub_b_min = [style_hidden] * 4
        new_style_c_min = style_hidden
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_h_min = style_hidden
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden
        new_style_l_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_o_min = style_hidden
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden

        # Subfilas de Fila d
        if n_clicks_main_d_min % 2 == 1:
            new_style_sub_d_min = [style_visible] * 2
            new_img_d_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_d_min = [style_hidden] * 2
            new_img_d_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila g
        if n_clicks_main_g_min % 2 == 1:
            new_style_sub_g_min = [style_visible] * 2
            new_img_g_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_g_min = [style_hidden] * 2
            new_img_g_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para ant-sumin-terceros
    elif n_clicks_sumin % 2 == 1:
        new_style_a = style_visible
        new_style_ant_sumin_terceros_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_b = style_hidden
        new_style_c = style_hidden
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 6
        new_style_f = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 9
        new_style_b_min = style_hidden
        new_style_sub_b_min = [style_hidden] * 4
        new_style_c_min = style_hidden
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 2
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 2
        new_style_h_min = style_hidden
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden
        new_style_l_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_o_min = style_hidden
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden

        # Subfilas de Fila A
        if n_clicks_main_a % 2 == 1:
            new_style_sub_a = [style_visible] * 2
            new_img_a_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a = [style_hidden] * 2
            new_img_a_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para ant-agua-mineral
    elif n_clicks_mineral % 2 == 1:
        new_style_b = style_visible
        new_style_ant_agua_mineral_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 2
        new_style_c = style_hidden
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 6
        new_style_f = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 9
        new_style_b_min = style_hidden
        new_style_sub_b_min = [style_hidden] * 4
        new_style_c_min = style_hidden
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 2
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 2
        new_style_h_min = style_hidden
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden
        new_style_l_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_o_min = style_hidden
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden


    # Lógica de interacción para ant-cont-polvo
    elif n_clicks_polvo % 2 == 1:
        new_style_d = style_visible
        new_style_c_min = style_visible
        new_style_h_min = style_visible
        new_style_ant_cont_polvo_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 2
        new_style_b = style_hidden
        new_style_c = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 6
        new_style_f = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 9
        new_style_b_min = style_hidden
        new_style_sub_b_min = [style_hidden] * 4
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 2
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 2
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden
        new_style_l_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_o_min = style_hidden
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden


    # Lógica de interacción para ant-sx-ew
    elif n_clicks_sx_ew % 2 == 1:
        new_style_b_min = style_visible
        new_style_e_min = style_visible
        new_style_f_min = style_visible
        new_style_ant_sx_ew_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 2
        new_style_b = style_hidden
        new_style_c = style_hidden
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 6
        new_style_f = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 9
        new_style_c_min = style_hidden
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 2
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 2
        new_style_h_min = style_hidden
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden
        new_style_l_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_o_min = style_hidden
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden

        # Subfilas de Fila b
        if n_clicks_main_b_min % 2 == 1:
            new_style_sub_b_min = [style_visible] * 4
            new_img_b_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_b_min = [style_hidden] * 4
            new_img_b_min_src = "/static/img/logos/diag_flecha.png"

    
    # Lógica de interacción para ant-area-seca
    elif n_clicks_seca % 2 == 1:
        new_style_b = style_visible
        new_style_e = style_visible
        new_style_f = style_visible
        new_style_a_min = style_visible
        new_style_e_min = style_visible
        new_style_f_min = style_visible
        new_style_i_min = style_visible
        new_style_j_min = style_visible
        new_style_k_min = style_visible
        new_style_l_min = style_visible
        new_style_m_min = style_visible
        new_style_n_min = style_visible
        new_style_o_min = style_visible
        new_style_p_min = style_visible
        new_style_q_min = style_visible
        new_style_ant_area_seca_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 2
        new_style_c = style_hidden
        new_style_d = style_hidden
        new_style_b_min = style_hidden
        new_style_sub_b_min = [style_hidden] * 4
        new_style_c_min = style_hidden
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 2
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 2
        new_style_h_min = style_hidden

        # Subfilas de Fila E
        if n_clicks_main_e % 2 == 1:
            new_style_sub_e = [style_visible] * 6
            new_img_e_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_e = [style_hidden] * 6
            new_img_e_src = "/static/img/logos/diag_flecha.png"
            
        # Subfilas de Fila a
        if n_clicks_main_a_min % 2 == 1:
            new_style_sub_a_min = [style_visible] * 9
            new_img_a_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a_min = [style_hidden] * 9
            new_img_a_min_src = "/static/img/logos/diag_flecha.png"

        # Subfilas de Fila n
        if n_clicks_main_n_min % 2 == 1:
            new_style_sub_n_min = [style_visible] * 2
            new_img_n_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_n_min = [style_hidden] * 2
            new_img_n_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para ant-ptas
    elif n_clicks_ptas % 2 == 1:
        new_style_g_min = style_visible
        new_style_h_min = style_visible
        new_style_ant_ptas_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 2 
        new_style_b = style_hidden
        new_style_c = style_hidden
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 6
        new_style_f = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 9
        new_style_b_min = style_hidden
        new_style_sub_b_min = [style_hidden] * 4
        new_style_c_min = style_hidden
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 2
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden
        new_style_l_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_o_min = style_hidden
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden

        # Subfilas de Fila g
        if n_clicks_main_g_min % 2 == 1:
            new_style_sub_g_min = [style_visible] * 2
            new_img_g_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_g_min = [style_hidden] * 2
            new_img_g_min_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para ant-evaporacion
    elif n_clicks_evap % 2 == 1:
        new_style_c = style_visible
        new_style_d = style_visible
        new_style_e = style_visible
        new_style_ant_evaporacion_style = style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 2 
        new_style_b = style_hidden 
        new_style_f = style_hidden
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 9
        new_style_b_min = style_hidden
        new_style_sub_b_min = [style_hidden] * 4
        new_style_c_min = style_hidden
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 2
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 2
        new_style_h_min = style_hidden
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden
        new_style_l_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_o_min = style_hidden
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden

        # Subfilas de Fila E
        if n_clicks_main_e % 2 == 1:
            new_style_sub_e = [style_visible] * 6
            new_img_e_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_e = [style_hidden] * 6
            new_img_e_src = "/static/img/logos/diag_flecha.png"


    # Lógica de interacción para ant-retencion
    elif n_clicks_reten % 2 == 1:
        new_style_f = style_visible
        new_style_o_min = style_visible
        new_style_ant_retencion_style= style_selected

        # Ocultar el resto de las filas y subfilas que no son parte del flujo.
        new_style_a = style_hidden
        new_style_sub_a = [style_hidden] * 2 
        new_style_b = style_hidden 
        new_style_c = style_hidden
        new_style_d = style_hidden
        new_style_e = style_hidden
        new_style_sub_e = [style_hidden] * 6
        new_style_a_min = style_hidden
        new_style_sub_a_min = [style_hidden] * 9
        new_style_b_min = style_hidden
        new_style_sub_b_min = [style_hidden] * 4
        new_style_c_min = style_hidden
        new_style_d_min = style_hidden
        new_style_sub_d_min = [style_hidden] * 2
        new_style_e_min = style_hidden
        new_style_f_min = style_hidden
        new_style_g_min = style_hidden
        new_style_sub_g_min = [style_hidden] * 2
        new_style_h_min = style_hidden
        new_style_i_min = style_hidden
        new_style_j_min = style_hidden
        new_style_k_min = style_hidden
        new_style_l_min = style_hidden
        new_style_m_min = style_hidden
        new_style_n_min = style_hidden
        new_style_sub_n_min = [style_hidden] * 2
        new_style_p_min = style_hidden
        new_style_q_min = style_hidden


    # Si ninguna de las cajas está activa, reiniciar los estilos.
    else:
        if n_clicks_main_a % 2 == 1:
            new_style_sub_a = [style_visible] * 2
            new_img_a_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a = [style_hidden] * 2
            new_img_a_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_e % 2 == 1:
            new_style_sub_e = [style_visible] * 6
            new_img_e_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_e = [style_hidden] * 6
            new_img_e_src = "/static/img/logos/diag_flecha.png"
        
        if n_clicks_main_a_min % 2 == 1:
            new_style_sub_a_min = [style_visible] * 9
            new_img_a_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_a_min = [style_hidden] * 9
            new_img_a_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_b_min % 2 == 1:
            new_style_sub_b_min = [style_visible] * 4
            new_img_b_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_b_min = [style_hidden] * 4
            new_img_b_min_src = "/static/img/logos/diag_flecha.png"

        if n_clicks_main_d_min % 2 == 1:
            new_style_sub_d_min = [style_visible] * 2
            new_img_d_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_d_min = [style_hidden] * 2
            new_img_d_min_src = "/static/img/logos/diag_flecha.png"  

        if n_clicks_main_g_min % 2 == 1:
            new_style_sub_g_min = [style_visible] * 4
            new_img_g_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_g_min = [style_hidden] * 4
            new_img_g_min_src = "/static/img/logos/diag_flecha.png"  

        if n_clicks_main_n_min % 2 == 1:
            new_style_sub_n_min = [style_hidden] * 2
            new_img_n_min_src = "/static/img/logos/diag_flecha_abajo.png"
        else:
            new_style_sub_n_min = [style_hidden] * 2
            new_img_n_min_src = "/static/img/logos/diag_flecha.png"    

    response = {
        "new_style_a": new_style_a,
        "new_style_b": new_style_b,
        "new_style_c": new_style_c,
        "new_style_d": new_style_d,
        "new_style_e": new_style_e,
        "new_style_f": new_style_f,
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
        "new_style_l_min": new_style_l_min,
        "new_style_m_min": new_style_m_min,
        "new_style_n_min": new_style_n_min,
        "new_style_o_min": new_style_o_min,
        "new_style_p_min": new_style_p_min,
        "new_style_q_min": new_style_q_min,

        "new_style_sub_a": new_style_sub_a,
        "new_style_sub_e": new_style_sub_e,
        "new_style_sub_a_min": new_style_sub_a_min,
        "new_style_sub_b_min": new_style_sub_b_min,
        "new_style_sub_d_min": new_style_sub_d_min,
        "new_style_sub_g_min": new_style_sub_g_min,
        "new_style_sub_n_min": new_style_sub_n_min,

        "new_style_ant_agua_nueva_style": new_style_ant_agua_nueva_style,
        "new_style_ant_servicios_style": new_style_ant_servicios_style,
        "new_style_ant_sumin_terceros_style": new_style_ant_sumin_terceros_style,
        "new_style_ant_agua_mineral_style": new_style_ant_agua_mineral_style,
        "new_style_ant_cont_polvo_style": new_style_ant_cont_polvo_style,
        "new_style_ant_sx_ew_style": new_style_ant_sx_ew_style,
        "new_style_ant_area_seca_style": new_style_ant_area_seca_style,
        "new_style_ant_ptas_style": new_style_ant_ptas_style,
        "new_style_ant_evaporacion_style": new_style_ant_evaporacion_style,
        "new_style_ant_retencion_style": new_style_ant_retencion_style,

        "new_img_a_src": new_img_a_src,
        "new_img_e_src": new_img_e_src,
        "new_img_a_min_src": new_img_a_min_src,
        "new_img_b_min_src": new_img_b_min_src,
        "new_img_d_min_src": new_img_d_min_src,
        "new_img_g_min_src": new_img_g_min_src,
        "new_img_n_min_src": new_img_n_min_src,
    }

    return jsonify(response)



@diagflujo_ant_bp.route('/toggle_rows_ant', methods=['POST'])
def toggle_rows_ant():
    data = request.json
    return toggle_rows_logic_ant(data)



@diagflujo_ant_bp.route('/diagramaflujoant', methods=['GET', 'POST'])
def balance_agua_ant():
    df_ph_ant = obtener_datos_cosmos_diag_ant()
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

    datos_ant = procesar_datos_diag_ant(fecha, ant_temporalidad, ant_medida)

    return render_template('diagrama_flujo_ant.html', mensaje_fecha_ant=mensaje_fecha_ant, fecha=fecha, ant_temporalidad=ant_temporalidad, ant_medida=ant_medida,
                            datos_ant=datos_ant)