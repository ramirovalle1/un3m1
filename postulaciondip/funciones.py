from sga.models import AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, \
    SubAreaEspecificaConocimientoTitulacion, CamposTitulosPostulacion, Titulacion


def get_camposamplios(ids):
    return AreaConocimientoTitulacion.objects.filter(status=True, id__in=ids)

def get_camposespecificos(ids):
    return SubAreaConocimientoTitulacion.objects.filter(status=True, id__in=ids)

def get_camposdetallados(ids):
    return SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, id__in=ids)

def get_titulos_campos_amplios(ids):
    ids_camposamplios = get_camposamplios(ids).values_list('pk', flat=True)
    eTitulos_campoamplio_id = CamposTitulosPostulacion.objects.filter(status=True,campoamplio__in=ids_camposamplios).values_list('titulo_id', flat=True).distinct()
    return eTitulos_campoamplio_id

def get_titulos_campos_especificos(ids):
    ids_camposespecificos= get_camposespecificos(ids).values_list('pk',flat =True)
    eTitulos_campoespecifico_id = CamposTitulosPostulacion.objects.filter(status=True,campoespecifico__in=ids_camposespecificos).values_list('titulo_id', flat=True).distinct()
    return eTitulos_campoespecifico_id

def get_titulos_campos_detallados(ids):
    ids_camposdetallados= get_camposdetallados(ids).values_list('pk',flat =True)
    eTitulos_camposdetallados_id = CamposTitulosPostulacion.objects.filter(status=True,campodetallado__in=ids_camposdetallados).values_list('titulo_id', flat=True).distinct()
    return eTitulos_camposdetallados_id

def configurado_solo_campo_amplio(camposamplios_ids,camposespecificos_ids,camposdetallados_ids ):
    return True if get_camposamplios(camposamplios_ids).exists() and not get_camposespecificos(camposespecificos_ids).exists() and not get_camposdetallados(camposdetallados_ids).exists() else False


def configurado_solo_campo_especifico(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
    return True if get_camposespecificos(camposespecificos_ids).exists() and not get_camposamplios(camposamplios_ids).exists() and not get_camposdetallados(camposdetallados_ids).exists() else False


def configurado_solo_campo_detallado(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
    return True if get_camposdetallados(camposdetallados_ids).exists() and not get_camposamplios(camposamplios_ids).exists() and not get_camposespecificos(camposespecificos_ids).exists() else False


def configurado_solo_campo_amplio_and_campo_especifico(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
    return True if get_camposamplios(camposamplios_ids).exists() and get_camposespecificos(camposespecificos_ids).exists() and not get_camposdetallados(camposdetallados_ids).exists() else False


def configurado_solo_campo_amplio_and_campo_detallado(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
    return True if get_camposamplios(camposamplios_ids).exists() and get_camposdetallados(camposdetallados_ids).exists() and not get_camposespecificos(camposespecificos_ids).exists() else False


def configurado_campo_amplio_and_campo_especifico_and_campo_detallado(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
    return True if get_camposamplios(camposamplios_ids).exists() and get_camposespecificos(camposespecificos_ids).exists() and get_camposdetallados(camposdetallados_ids).exists() else False


def titulados_acorde_al_campo_del_perfil_requerido(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
    eTitulos_campoamplio_ids = None
    eTitulos_campoespecifico_ids = None
    eTitulos_camposdetallados_ids = None
    eTitulos_id= [0,]

    if configurado_solo_campo_amplio(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
        eTitulos_campoamplio_ids = get_titulos_campos_amplios(camposamplios_ids)
        # Obtener los IDs de los títulos que cumplen con el campo
        eTitulos_id = eTitulos_campoamplio_ids

    if configurado_solo_campo_especifico(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
        eTitulos_campoespecifico_ids = get_titulos_campos_especificos(camposespecificos_ids)
        # Obtener los IDs de los títulos que cumplen con el campo
        eTitulos_id = eTitulos_campoespecifico_ids

    if configurado_solo_campo_detallado(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
        eTitulos_camposdetallados_ids = get_titulos_campos_detallados(camposdetallados_ids)
        # Obtener los IDs de los títulos que cumplen con el campo
        eTitulos_id = eTitulos_camposdetallados_ids

    if configurado_solo_campo_amplio_and_campo_especifico(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
        eTitulos_campoamplio_ids = get_titulos_campos_amplios(camposamplios_ids)
        eTitulos_campoespecifico_ids = get_titulos_campos_especificos(camposespecificos_ids)
        # Obtener los IDs de los títulos que cumplen con ambos campos (intersección)
        eTitulos_id = set(eTitulos_campoamplio_ids) & set(eTitulos_campoespecifico_ids)

    if configurado_solo_campo_amplio_and_campo_detallado(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
        eTitulos_campoamplio_ids = get_titulos_campos_amplios(camposamplios_ids)
        eTitulos_camposdetallados_ids = get_titulos_campos_detallados(camposdetallados_ids)

        # Obtener los IDs de los títulos que cumplen con ambos campos (intersección)
        eTitulos_id = set(eTitulos_campoamplio_ids) & set(eTitulos_camposdetallados_ids)

    if configurado_campo_amplio_and_campo_especifico_and_campo_detallado(camposamplios_ids,camposespecificos_ids,camposdetallados_ids):
        eTitulos_campoamplio_ids = get_titulos_campos_amplios(camposamplios_ids)
        eTitulos_campoespecifico_ids = get_titulos_campos_especificos(camposespecificos_ids)
        eTitulos_camposdetallados_ids = get_titulos_campos_detallados(camposdetallados_ids)

        # Obtener los IDs de los títulos que cumplen con los campos (intersección)
        eTitulos_id = set(eTitulos_campoamplio_ids) & set(eTitulos_campoespecifico_ids) & set(eTitulos_camposdetallados_ids)

    # Filtrar las personas con el titulo que cumplen las condiciones de los campos
    eTitulacion = Titulacion.objects.filter(status=True, titulo_id__in=eTitulos_id, persona__status=True)

    return eTitulacion



def numero_a_letras_informe_contratacion_posgrado(numero):
    diccionario = {
        1: "Un", 2: "Dos", 3: "Tres", 4: "Cuatro", 5: "Cinco",
        6: "Seis", 7: "Siete", 8: "Ocho", 9: "Nueve", 10: "Diez",
        11: "Once", 12: "Doce", 13: "Trece", 14: "Catorce", 15: "Quince",
        16: "Dieciséis", 17: "Diecisiete", 18: "Dieciocho", 19: "Diecinueve", 20: "Veinte",
        21: "Veintiuno", 22: "Veintidós", 23: "Veintitrés", 24: "Veinticuatro", 25: "Veinticinco",
        26: "Veintiséis", 27: "Veintisiete", 28: "Veintiocho", 29: "Veintinueve", 30: "Treinta",
        31: "Treinta y Uno", 32: "Treinta y Dos", 33: "Treinta y Tres", 34: "Treinta y Cuatro", 35: "Treinta y Cinco",
        36: "Treinta y Seis", 37: "Treinta y Siete", 38: "Treinta y Ocho", 39: "Treinta y Nueve", 40: "Cuarenta",
        41: "Cuarenta y Uno", 42: "Cuarenta y Dos", 43: "Cuarenta y Tres", 44: "Cuarenta y Cuatro", 45: "Cuarenta y Cinco",
        46: "Cuarenta y Seis", 47: "Cuarenta y Siete", 48: "Cuarenta y Ocho", 49: "Cuarenta y Nueve", 50: "Cincuenta",
    }

    if numero in diccionario:
        return diccionario[numero]
    else:
        return "0"
