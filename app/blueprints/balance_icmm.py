from datetime import datetime
from flask import Blueprint, render_template, request, session, jsonify, current_app
from app.utils.utils import generar_saludo

balance_icmm_bp = Blueprint('balance_icmm', __name__)

def obtener_datos_cosmos_icmm():
    app = current_app._get_current_object()  # Obtiene la instancia real de la app
    cache = app.cache

    # Intentar obtener los datos de la caché para Antucoya
    df_ph_ant = cache.get('ph_ant_data_icmm')
    if df_ph_ant is None:
        cosmos_client = app.config['COSMOS_CLIENT']
        df_ph_ant = cosmos_client.get_items_from_container(
            'PH_ANT', 
            'amsa_datos_hidricos_web.dmt_ant_reporte_hidrico_icmm'
        )
        cache.set('ph_ant_data_icmm', df_ph_ant, timeout=3600)

    # Intentar obtener datos de la caché para Los Pelambres
    df_ph_mlp = cache.get('ph_mlp_data_icmm')
    if df_ph_mlp is None:
        cosmos_client = app.config['COSMOS_CLIENT']
        df_ph_mlp = cosmos_client.get_items_from_container(
            'PH_MLP', 
            'amsa_datos_hidricos_web.dmt_mlp_reporte_hidrico_icmm'
        )
        cache.set('ph_mlp_data_icmm', df_ph_mlp, timeout=3600)

    # Intentar obtener datos de la caché para Zaldivar
    df_ph_cmz = cache.get('ph_cmz_data_icmm')
    if df_ph_cmz is None:
        cosmos_client = app.config['COSMOS_CLIENT']
        df_ph_cmz = cosmos_client.get_items_from_container(
            'PH_CMZ', 
            'amsa_datos_hidricos_web.dmt_cmz_reporte_hidrico_icmm'
        )
        cache.set('ph_cmz_data_icmm', df_ph_cmz, timeout=3600)

    # Combinar los DataFrames de los tres
    df_combined = df_ph_ant + df_ph_mlp + df_ph_cmz

    # Asegurarse de que la columna 'anio' sea de tipo cadena
    for dato in df_combined:
        if 'anio' in dato:
            dato['anio'] = str(dato['anio'])

    # Intentar obtener los datos actuales de la caché para combinarlos
    cached_data = cache.get('ph_data_icmm')

    # Si la caché no tiene datos, iniciamos una lista vacía
    if cached_data is None:
        cached_data = []

    # Filtrar duplicados antes de agregar los nuevos datos a la caché
    fechas_en_cache = {dato['fecha'] for dato in cached_data}
    df_combined = [dato for dato in df_combined if dato['fecha'] not in fechas_en_cache]

    # Guardar los datos combinados (actualizados) en la caché, sin duplicados
    cache.set('ph_data_icmm', cached_data + df_combined, timeout=3600)

    return cached_data + df_combined

#Función para obtener la fecha máxima
def obtener_fecha_maxima_icmm(datos):
    if datos:
        # Obtener todas las fechas
        fechas = [dato['fecha'] for dato in datos if 'fecha' in dato]
        
        if fechas:
            # Convertir las fechas a objetos datetime y calcular la fecha máxima
            fecha_maxima = max(datetime.strptime(fecha, '%Y-%m-%d') for fecha in fechas)
            return fecha_maxima
    return None


#Función para actualizar la fecha de actualización
def obtener_mensaje_fecha(fecha_maxima):
    if fecha_maxima:
        fecha_formateada = fecha_maxima.strftime('%d-%m-%Y')
        return f"Actualizado con datos hasta {fecha_formateada}"
    else:
        return "No se encontraron datos para mostrar"
    

def procesar_datos_icmm(compania, mes, anio, mtd_ytd_switch):

    app = current_app._get_current_object()

    # Validar que mes y anio no sean nulos o vacíos
    if not mes or not anio:
        # Retornar valores predeterminados si los valores son nulos
        return tuple("0" for _ in range(89)) #return "0", "0", "0", "0", "0", "0"
        
    # Diccionario para convertir el mes a número
    meses_a_numeros = {
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
    }

    # Validar que el mes sea válido y convertirlo a número
    mes_numero = meses_a_numeros.get(mes, None)

    # Formatear la fecha
    fecha = f"{anio}-{mes_numero}-01" if mes_numero else None

    # Consultar la caché
    df_combined = app.cache.get('ph_data_icmm')
    if not df_combined:
        df_combined = []

    # print(f"Datos iniciales en caché: {len(df_combined)}")  

    fecha_presente = any(item.get('fecha') == fecha for item in df_combined)
    # print(f'La fecha {fecha} está en caché inicial?: {fecha_presente}')
    
    if not fecha_presente and fecha:
        # print("Consultando datos cosmos")
        cosmos_client = app.config['COSMOS_CLIENT']
        contenedores = [
            ('PH_CMZ', 'amsa_datos_hidricos_web.dmt_cmz_reporte_hidrico_icmm'),
            ('PH_ANT', 'amsa_datos_hidricos_web.dmt_ant_reporte_hidrico_icmm'),
            ('PH_MLP', 'amsa_datos_hidricos_web.dmt_mlp_reporte_hidrico_icmm')
        ]
        
        nuevos_datos_totales = []
        for db_name, container_name in contenedores:
            nuevos_datos = cosmos_client.get_items_from_container(
                db_name, container_name, fecha, fecha
            )
            nuevos_datos_totales.extend(nuevos_datos)
        
        df_combined += nuevos_datos_totales
        # print(f"Nuevos datos a agregar a la caché: {len(nuevos_datos_totales)}")

        for dato in df_combined:
            if 'anio' in dato:
                dato['anio'] = str(dato['anio'])

        app.cache.set('ph_data_icmm', df_combined, timeout=3600)
        # print(f"Datos almacenados en caché, cantidad total de registros: {len(df_combined)}")

        df_combined = app.cache.get('ph_data_icmm')
        # print(f"Datos después de almacenar en caché: {len(df_combined)}")

    # Filtrar los datos según los valores seleccionados
    datos_filtrados = [
        dato for dato in df_combined
        if dato.get('compania') == compania
        and dato.get('anio') == anio
        and dato.get('mes') == mes
        and dato.get('temporalidad') == mtd_ytd_switch
    ]

    # Función para obtener un valor específico de los datos filtrados
    def filtrar_valor(datos, tipo_agua, metrica, fuente_destino, calidad_agua):
        datos_filtrados = [
            dato for dato in datos
            if dato.get('tipo_agua') == tipo_agua
            and dato.get('metrica') == metrica
            and dato.get('fuente_destino') == fuente_destino
            and dato.get('calidad_agua') == calidad_agua
        ]
        return str(datos_filtrados[0]['valor']) if datos_filtrados else "0"

    #####AGUA OPERACIONAL - EXTRACCIÓN/CAPTACIÓN#####
    #Alta ML Agua Superficial
    ao_ext_asup_alta = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_superficial", "alta")

    #Baja ML Agua Superficial
    ao_ext_asup_baja = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_superficial", "baja"
                                         )
    #Total ML Agua Superficial
    ao_ext_asup_total = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_superficial", "total")

    #Alta ML Agua Subterránea
    ao_ext_asub_alta = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_subterranea", "alta")

    #Baja ML Agua Subterránea
    ao_ext_asub_baja = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_subterranea", "baja")

    #Total ML Agua Subterránea
    ao_ext_asub_total = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_subterranea", "total")

    #Alta ML Agua de Mar
    ao_ext_amar_alta = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_mar", "alta")

    #Baja ML Agua de Mar
    ao_ext_amar_baja = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_mar", "baja")

    #Total ML Agua de Mar
    ao_ext_amar_total = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_mar", "total")

    #Alta ML Agua de Terceros
    ao_ext_ater_alta = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_terceros", "alta")

    #Baja ML Agua de Terceros
    ao_ext_ater_baja = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_terceros", "baja")

    #Total ML Agua de Terceros
    ao_ext_ater_total = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "agua_terceros", "total")
    
    #Subtotal Alta ML Extracción/Captación
    ao_ext_subtotal_alta = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "total", "alta")

    #Subtotal Baja ML Extracción/Captación
    ao_ext_subtotal_baja = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "total", "baja")

    #Subtotal Total ML Extracción/Captación
    ao_ext_subtotal_total = filtrar_valor(datos_filtrados, "agua_operacional", "extraccion_captacion", "total", "total")

    #####AGUA OPERACIONAL - DESCARGA#####
    #Alta ML Agua Superficial
    ao_desc_asup_alta = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_superficial", "alta")

    #Baja ML Agua Superficial
    ao_desc_asup_baja = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_superficial", "baja")

    #Total ML Agua Superficial
    ao_desc_asup_total = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_superficial", "total")

    #Alta ML Agua Subterránea
    ao_desc_asub_alta = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_subterranea", "alta")

    #Baja ML Agua Subterránea
    ao_desc_asub_baja = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_subterranea", "baja")

    #Total ML Agua Subterránea
    ao_desc_asub_total = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_subterranea", "total")

    #Alta ML Agua de Mar
    ao_desc_amar_alta = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_mar", "alta")

    #Baja ML Agua de Mar
    ao_desc_amar_baja = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_mar", "baja")

    #Total ML Agua de Mar
    ao_desc_amar_total = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_mar", "total")

    #Alta ML Agua de Terceros
    ao_desc_ater_alta = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_terceros", "alta")

    #Baja ML Agua de Terceros
    ao_desc_ater_baja = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_terceros", "baja")

    #Total ML Agua de Terceros
    ao_desc_ater_total = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "agua_terceros", "total")

    #Subtotal Alta ML Descarga
    ao_desc_subtotal_alta = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "total", "alta")

    #Subtotal Baja ML Descarga
    ao_desc_subtotal_baja = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "total", "baja")

    #Subtotal Total ML Descarga
    ao_desc_subtotal_total = filtrar_valor(datos_filtrados, "agua_operacional", "descarga", "total", "total")

    #####AGUA OPERACIONAL - CONSUMO#####
    #Alta ML Evaporación
    ao_cons_evap_alta = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "evaporacion", "alta")

    #Baja ML Evaporación
    ao_cons_evap_baja = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "evaporacion", "baja")

    #Total ML Evaporación
    ao_cons_evap_total = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "evaporacion", "total")

    #Alta ML Retención
    ao_cons_ret_alta = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "retencion", "alta")

    #Baja ML Retención
    ao_cons_ret_baja = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "retencion", "baja")

    #Total ML Retención
    ao_cons_ret_total = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "retencion", "total")

    #Alta ML Evaporación control de polvo
    ao_cons_evcp_alta = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "evap_control_polvo", "alta")

    #Baja ML Evaporación control de polvo
    ao_cons_evcp_baja = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "evap_control_polvo", "baja")

    #Total ML Evaporación control de polvo
    ao_cons_evcp_total = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "evap_control_polvo", "total")

    #Alta ML Otras Pérdidas
    ao_cons_otpe_alta = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "otras_perdidas", "alta")

    #Baja ML Otras Pérdidas
    ao_cons_otpe_baja = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "otras_perdidas", "baja")

    #Total ML Otras Pérdidas
    ao_cons_otpe_total = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "otras_perdidas", "total")

    #Subtotal Alta ML Consumo
    ao_cons_subtotal_alta = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "total", "alta")

    #Subtotal Baja ML Consumo
    ao_cons_subtotal_baja = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "total", "baja")

    #Subtotal Total ML Consumo
    ao_cons_subtotal_total = filtrar_valor(datos_filtrados, "agua_operacional", "consumo", "total", "total")

    #Total ML Cambio Almac
    ao_cambio_almac_total = filtrar_valor(datos_filtrados, "agua_operacional", "cambio_almacenamiento", "cambio_almacenamiento", "total")

    #Total ML Reutilizacion y Rec
    ao_reut_recic_total = filtrar_valor(datos_filtrados, "agua_operacional", "reutilizacion_reciclaje", "reutilizacion_reciclaje", "total")

    #Total ML Uso Agua Op
    ao_uso_aoper_total = filtrar_valor(datos_filtrados, "agua_operacional", "uso_agua_operacional", "uso_agua_operacional", "total")

    #####OTRA AGUA GESTIONADA - EXTRACCIÓN/CAPTACIÓN#####
    #Alta ML Agua Superficial
    oag_ext_asup_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_superficial", "alta")

    #Baja ML Agua Superficial
    oag_ext_asup_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_superficial", "baja")

    #Total ML Agua Superficial
    oag_ext_asup_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_superficial", "total")

    #Alta ML Agua Subterránea
    oag_ext_asub_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_subterranea", "alta")

    #Baja ML Agua Subterránea
    oag_ext_asub_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_subterranea", "baja")

    #Total ML Agua Subterránea
    oag_ext_asub_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_subterranea", "total")

    #Alta ML Agua de Mar
    oag_ext_amar_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_mar", "alta")

    #Baja ML Agua de Mar
    oag_ext_amar_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_mar", "baja")

    #Total ML Agua de Mar
    oag_ext_amar_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_mar", "total")

    #Alta ML Agua de Terceros
    oag_ext_ater_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_terceros", "alta")

    #Baja ML Agua de Terceros
    oag_ext_ater_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_terceros", "baja")

    #Total ML Agua de Terceros
    oag_ext_ater_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "agua_terceros", "total")

    #Subtotal Alta ML Extracción/Captación
    oag_ext_subtotal_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "total", "alta")

    #Subtotal Baja ML Extracción/Captación
    oag_ext_subtotal_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "total", "baja")

    #Subtotal Total ML Extracción/Captación
    oag_ext_subtotal_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "extraccion_captacion", "total", "total")

    #####OTRA AGUA GESTIONADA - DESCARGA#####
    #Alta ML Agua Superficial
    oag_desc_asup_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_superficial", "alta")

    #Baja ML Agua Superficial
    oag_desc_asup_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_superficial", "baja")

    #Total ML Agua Superficial
    oag_desc_asup_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_superficial", "total")

    #Alta ML Agua Subterránea
    oag_desc_asub_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_subterranea", "alta")

    #Baja ML Agua Subterránea
    oag_desc_asub_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_subterranea", "baja")

    #Total ML Agua Subterránea
    oag_desc_asub_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_subterranea", "total")

    #Alta ML Agua de Mar
    oag_desc_amar_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_mar", "alta")

    #Baja ML Agua de Mar
    oag_desc_amar_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_mar", "baja")

    #Total ML Agua de Mar
    oag_desc_amar_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_mar", "total")

    #Alta ML Agua de Terceros
    oag_desc_ater_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_terceros", "alta")

    #Baja ML Agua de Terceros
    oag_desc_ater_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_terceros", "baja")

    #Total ML Agua de Terceros
    oag_desc_ater_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "agua_terceros", "total")

    #Subtotal Alta ML Descarga
    oag_desc_subtotal_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "total", "alta")

    #Subtotal Baja ML Descarga
    oag_desc_subtotal_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "total", "baja")

    #Subtotal Total ML Descarga
    oag_desc_subtotal_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "descarga", "total", "total")

    #####OTRA AGUA GESTIONADA - CONSUMO#####
    #Alta ML Evaporación
    oag_cons_evap_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "evaporacion", "alta")

    #Baja ML Evaporación
    oag_cons_evap_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "evaporacion", "baja")

    #Total ML Evaporación
    oag_cons_evap_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "evaporacion", "total")

    #Alta ML Otras Pérdidas
    oag_cons_otpe_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "otras_perdidas", "alta")

    #Baja ML Otras Pérdidas
    oag_cons_otpe_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "otras_perdidas", "baja")

    #Total ML Otras Pérdidas
    oag_cons_otpe_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "otras_perdidas", "total")

    #Subtotal Alta ML Consumo
    oag_cons_subtotal_alta = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "total", "alta")

    #Subtotal Baja ML Consumo
    oag_cons_subtotal_baja = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "total", "baja")

    #Subtotal Total ML Consumo
    oag_cons_subtotal_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "consumo", "total", "total")

    #Total ML Cambio Almac
    oag_cambio_almac_total = filtrar_valor(datos_filtrados, "otra_agua_gestionada", "cambio_almacenamiento", "cambio_almacenamiento", "total")

    #Valor 2 Delta Balance
    db_delta_balance_total = filtrar_valor(datos_filtrados, "delta_balance", "delta_balance", "delta_balance", "total")

    datos = {
        'ao_ext_asup_alta': ao_ext_asup_alta,
        'ao_ext_asup_baja': ao_ext_asup_baja,
        'ao_ext_asup_total': ao_ext_asup_total,
        'ao_ext_asub_alta': ao_ext_asub_alta,
        'ao_ext_asub_baja': ao_ext_asub_baja,
        'ao_ext_asub_total': ao_ext_asub_total,
        'ao_ext_amar_alta': ao_ext_amar_alta,
        'ao_ext_amar_baja': ao_ext_amar_baja,
        'ao_ext_amar_total': ao_ext_amar_total,
        'ao_ext_ater_alta': ao_ext_ater_alta,
        'ao_ext_ater_baja': ao_ext_ater_baja,
        'ao_ext_ater_total': ao_ext_ater_total,
        'ao_ext_subtotal_alta': ao_ext_subtotal_alta,
        'ao_ext_subtotal_baja': ao_ext_subtotal_baja,
        'ao_ext_subtotal_total': ao_ext_subtotal_total,
        'ao_desc_asup_alta': ao_desc_asup_alta,
        'ao_desc_asup_baja': ao_desc_asup_baja,
        'ao_desc_asup_total': ao_desc_asup_total,
        'ao_desc_asub_alta': ao_desc_asub_alta,
        'ao_desc_asub_baja': ao_desc_asub_baja,
        'ao_desc_asub_total': ao_desc_asub_total,
        'ao_desc_amar_alta': ao_desc_amar_alta,
        'ao_desc_amar_baja': ao_desc_amar_baja,
        'ao_desc_amar_total': ao_desc_amar_total,
        'ao_desc_ater_alta': ao_desc_ater_alta,
        'ao_desc_ater_baja': ao_desc_ater_baja,
        'ao_desc_ater_total': ao_desc_ater_total,
        'ao_desc_subtotal_alta': ao_desc_subtotal_alta,
        'ao_desc_subtotal_baja': ao_desc_subtotal_baja,
        'ao_desc_subtotal_total': ao_desc_subtotal_total,
        'ao_cons_evap_alta': ao_cons_evap_alta,
        'ao_cons_evap_baja': ao_cons_evap_baja,
        'ao_cons_evap_total': ao_cons_evap_total,
        'ao_cons_ret_alta': ao_cons_ret_alta,
        'ao_cons_ret_baja': ao_cons_ret_baja,
        'ao_cons_ret_total': ao_cons_ret_total,
        'ao_cons_evcp_alta': ao_cons_evcp_alta,
        'ao_cons_evcp_baja': ao_cons_evcp_baja,
        'ao_cons_evcp_total': ao_cons_evcp_total,
        'ao_cons_otpe_alta': ao_cons_otpe_alta,
        'ao_cons_otpe_baja': ao_cons_otpe_baja,
        'ao_cons_otpe_total': ao_cons_otpe_total,
        'ao_cons_subtotal_alta': ao_cons_subtotal_alta,
        'ao_cons_subtotal_baja': ao_cons_subtotal_baja,
        'ao_cons_subtotal_total': ao_cons_subtotal_total,
        'ao_cambio_almac_total': ao_cambio_almac_total,
        'ao_reut_recic_total': ao_reut_recic_total,
        'ao_uso_aoper_total': ao_uso_aoper_total,
        'oag_ext_asup_alta': oag_ext_asup_alta,
        'oag_ext_asup_baja': oag_ext_asup_baja,
        'oag_ext_asup_total': oag_ext_asup_total,
        'oag_ext_asub_alta': oag_ext_asub_alta,
        'oag_ext_asub_baja': oag_ext_asub_baja,
        'oag_ext_asub_total': oag_ext_asub_total,
        'oag_ext_amar_alta': oag_ext_amar_alta,
        'oag_ext_amar_baja': oag_ext_amar_baja,
        'oag_ext_amar_total': oag_ext_amar_total,
        'oag_ext_ater_alta': oag_ext_ater_alta,
        'oag_ext_ater_baja': oag_ext_ater_baja,
        'oag_ext_ater_total': oag_ext_ater_total,
        'oag_ext_subtotal_alta': oag_ext_subtotal_alta,
        'oag_ext_subtotal_baja': oag_ext_subtotal_baja,
        'oag_ext_subtotal_total': oag_ext_subtotal_total,
        'oag_desc_asup_alta': oag_desc_asup_alta,
        'oag_desc_asup_baja': oag_desc_asup_baja,
        'oag_desc_asup_total': oag_desc_asup_total,
        'oag_desc_asub_alta': oag_desc_asub_alta,
        'oag_desc_asub_baja': oag_desc_asub_baja,
        'oag_desc_asub_total': oag_desc_asub_total,
        'oag_desc_amar_alta': oag_desc_amar_alta,
        'oag_desc_amar_baja': oag_desc_amar_baja,
        'oag_desc_amar_total': oag_desc_amar_total,
        'oag_desc_ater_alta': oag_desc_ater_alta,
        'oag_desc_ater_baja': oag_desc_ater_baja,
        'oag_desc_ater_total': oag_desc_ater_total,
        'oag_desc_subtotal_alta': oag_desc_subtotal_alta,
        'oag_desc_subtotal_baja': oag_desc_subtotal_baja,
        'oag_desc_subtotal_total': oag_desc_subtotal_total,
        'oag_cons_evap_alta': oag_cons_evap_alta,
        'oag_cons_evap_baja': oag_cons_evap_baja,
        'oag_cons_evap_total': oag_cons_evap_total,
        'oag_cons_otpe_alta': oag_cons_otpe_alta,
        'oag_cons_otpe_baja': oag_cons_otpe_baja,
        'oag_cons_otpe_total': oag_cons_otpe_total,
        'oag_cons_subtotal_alta': oag_cons_subtotal_alta,
        'oag_cons_subtotal_baja': oag_cons_subtotal_baja,
        'oag_cons_subtotal_total': oag_cons_subtotal_total,
        'oag_cambio_almac_total': oag_cambio_almac_total,
        'db_delta_balance_total': db_delta_balance_total,
    }

    return datos


#Función para actualizar la fecha de actualización
def obtener_mensaje_fecha(fecha_maxima):
    if fecha_maxima:
        fecha_formateada = fecha_maxima.strftime('%d-%m-%Y')
        return f"Actualizado con datos hasta {fecha_formateada}"
    else:
        return "No se encontraron datos para mostrar"
    

def procesar_datos_icmm_delta_perc(compania, mes, anio, mtd_ytd_switch):

    app = current_app._get_current_object()

    if not mes or not anio:
        return "0", {'color': '#1B9D56', 'font-weight': 'bold'}  # Retorno predeterminado
    
    # Diccionario para convertir el mes a número
    meses_a_numeros = {
        "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
        "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
        "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
    }

    # Validar que el mes sea válido y convertirlo
    mes_numero = meses_a_numeros.get(mes, None)
    if not mes_numero:
        return f"Error: mes inválido '{mes}'", {'color': '#D22630', 'font-weight': 'bold'}

    try:
        fecha = f"{anio}-{mes_numero}-01"
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return f"Error: Fecha inválida con año '{anio}' y mes '{mes}'", {'color': '#D22630', 'font-weight': 'bold'}

    temporalidad = 'YTD' if mtd_ytd_switch == "on" else 'MTD'

    # Consultar la caché
    df_combined = app.cache.get('ph_data_icmm')
    if not df_combined:
        df_combined = []

    # Verificar si la fecha ya está en la caché
    fecha_presente = any(item.get('fecha') == fecha for item in df_combined)

    if not fecha_presente:
        # Obtener datos desde CosmosDB si la fecha no está en caché
        cosmos_client = app.config['COSMOS_CLIENT']
        contenedores = [
            ('PH_CMZ', 'amsa_datos_hidricos_web.dmt_cmz_reporte_hidrico_icmm'),
            ('PH_ANT', 'amsa_datos_hidricos_web.dmt_ant_reporte_hidrico_icmm'),
        ]
        
        nuevos_datos_totales = []
        for db_name, container_name in contenedores:
            nuevos_datos = cosmos_client.get_items_from_container(db_name, container_name, fecha, fecha)
            nuevos_datos_totales.extend(nuevos_datos)
        
        df_combined += nuevos_datos_totales

        for dato in df_combined:
            if 'anio' in dato:
                dato['anio'] = str(dato['anio'])
        
        app.cache.set('ph_data_icmm', df_combined, timeout=3600)

    # Filtrar datos para delta balance baja
    datos_filtrados = [
        dato for dato in df_combined
        if dato.get('compania') == compania
        and dato.get('anio') == anio
        and dato.get('mes') == mes
        and dato.get('temporalidad') == temporalidad
    ]
    
    datos_delta_balance_baja = [
        dato for dato in datos_filtrados
        if dato.get('tipo_agua') == "delta_balance"
        and dato.get('metrica') == "delta_balance"
        and dato.get('fuente_destino') == "delta_balance"
        and dato.get('calidad_agua') == "baja"
    ]

    if not datos_delta_balance_baja:
        return "0", {'color': '#1B9D56', 'font-weight': 'bold'}

    # Calcular porcentaje
    valor = datos_delta_balance_baja[0].get('valor', 0)
    valor_porcentaje = valor * 100
    db_delta_balance_baja = f"{valor_porcentaje:.0f}%"

    # Determinar color
    if -5 <= valor_porcentaje <= 5:
        color = '#1B9D56'  # Verde
    elif 5 < valor_porcentaje <= 10 or -10 <= valor_porcentaje < -5:
        color = '#F88B1D'  # Naranja
    else:
        color = '#D22630'  # Rojo

    style = {'color': color, 'background-color': '#ebebeb', 'font-weight': 'bold'}
    style_string = "; ".join(f"{key}: {value}" for key, value in style.items())

    return db_delta_balance_baja, style_string

@balance_icmm_bp.route('/balanceicmm', methods=['GET', 'POST'])
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
    df_combined = obtener_datos_cosmos_icmm()
    fecha_maxima = obtener_fecha_maxima_icmm(df_combined)
    mensaje_fecha = obtener_mensaje_fecha(fecha_maxima)

    # Obtener valores seleccionados desde el formulario
    compania = selected_company
    mes = request.form.get('filtro_mes', '')
    anio = request.form.get('filtro_anio', '')
    mtd_ytd_switch = request.form.get('filtro_temp', '')  # "on" si está activado, "" si no
    temporalidad = 'YTD' if mtd_ytd_switch == "on" else 'MTD'

    # Llamar a la función de utils.py para procesar los datos
    datos = procesar_datos_icmm(compania, mes, anio, temporalidad)

    # Procesar datos para delta balance baja
    db_delta_balance_baja, style_delta = procesar_datos_icmm_delta_perc(compania, mes, anio, temporalidad)

    return render_template('balance_icmm.html', selected_company=selected_company, meses=meses, anios=anios, saludo=saludo, href=href, mensaje_fecha=mensaje_fecha, 
                        datos=datos, db_delta_balance_baja=db_delta_balance_baja, style_delta=style_delta)