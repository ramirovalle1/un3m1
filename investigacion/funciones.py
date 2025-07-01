import collections
import os
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from django.db.models import Max, Q
from becadocente.models import InformeFactibilidad, ResolucionComite
from sagest.models import DistributivoPersona
from sga.funciones import variable_valor, cuenta_email_disponible_para_envio, validarcedula, dia_semana_enletras_fecha
from sga.models import Persona, ProfesorDistributivoHoras, Periodo, CUENTAS_CORREOS, ProfesorDistributivoHoras, ResponsableCoordinacion, MESES_CHOICES, Notificacion, CoordinadorCarrera
from sga.tasks import send_html_mail

# Formatos de xlsxwriter
titulo1 = {
    'align': 'center',
    'valign': 'vcenter',
    'bold': 1,
    'font_size': 14,
    'font_name': 'Times New Roman'
}

titulo2 = {
    'align': 'center',
    'valign': 'vcenter',
    'bold': 1,
    'font_size': 11,
    'font_name': 'Times New Roman'
}

titulo3 = {
    'align': 'center',
    'valign': 'vcenter',
    'bold': 1,
    'font_size': 9,
    'font_name': 'Times New Roman'
}

titulo1izq = {
    'align': 'left',
    'valign': 'vcenter',
    'bold': 1,
    'font_size': 14,
    'font_name': 'Times New Roman'
}

titulo2izq = {
    'align': 'left',
    'valign': 'vcenter',
    'bold': 1,
    'font_size': 11,
    'font_name': 'Times New Roman'
}

titulo3izq = {
    'align': 'left',
    'valign': 'vcenter',
    'bold': 1,
    'font_size': 9,
    'font_name': 'Times New Roman'
}

cabeceracolumna = {
    'bold': 1,
    'align': 'center',
    'valign': 'vcenter',
    'bg_color': 'silver',
    'text_wrap': 1,
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdageneral = {
    'valign': 'vcenter',
    'text_wrap': 1,
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdageneralneg = {
    'valign': 'vcenter',
    'bold': 1,
    'text_wrap': 1,
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdageneralcent = {
    'align': 'center',
    'valign': 'vcenter',
    'text_wrap': 1,
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdafecha = {
    'num_format': 'yyyy-mm-dd',
    'align': 'center',
    'valign': 'vcenter',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdafechaDMA = {
    'num_format': 'dd-mm-yyyy',
    'align': 'center',
    'valign': 'vcenter',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdahora = {
    'num_format': 'h:mm:ss',
    'align': 'center',
    'valign': 'vcenter',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdamoneda = {
    'num_format': '$ #,##0.00',
    'align': 'right',
    'valign': 'vcenter',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdanumerodecimal = {
    'num_format': '#,##0.00',
    'align': 'right',
    'valign': 'vcenter',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdanumerodecimal4dec = {
    'num_format': '#,##0.0000',
    'align': 'right',
    'valign': 'vcenter',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdaporcentaje = {
    'num_format': '0.00%',
    'align': 'right',
    'valign': 'vcenter',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

textonegrita = {
    'bold': 1,
    'font_size': 8,
    'font_name': 'Verdana',
    'text_wrap': 1,
    'valign': 'vcenter',
}

formatomoneda = {
    'num_format': '$ #,##0.00',
    'align': 'right',
    'font_size': 8,
    'font_name': 'Verdana'
}

celdanegritacent = {
    'bold': 1,
    'align': 'center',
    'valign': 'vcenter',
    'bg_color': 'silver',
    'text_wrap': 1,
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdanegritaizq = {
    'bold': 1,
    'align': 'left',
    'valign': 'vcenter',
    'bg_color': 'silver',
    'text_wrap': 1,
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdanegritageneral = {
    'bold': 1,
    'valign': 'vcenter',
    'bg_color': 'silver',
    'text_wrap': 1,
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdamonedapie = {
    'bold': 1,
    'num_format': '$ #,##0.00',
    'align': 'right',
    'valign': 'vcenter',
    'bg_color': 'silver',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdanumerodecimal4decpie = {
    'bold': 1,
    'num_format': '#,##0.0000',
    'align': 'right',
    'valign': 'vcenter',
    'bg_color': 'silver',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

celdaporcentajepie = {
    'bold': 1,
    'num_format': '0.00%',
    'align': 'right',
    'valign': 'vcenter',
    'bg_color': 'silver',
    'border': 1,
    'font_size': 8,
    'font_name': 'Verdana'
}

FORMATOS_CELDAS_EXCEL = {
    "titulo1": titulo1,
    "titulo2": titulo2,
    "titulo3": titulo3,
    "titulo1izq": titulo1izq,
    "titulo2izq": titulo2izq,
    "titulo3izq": titulo3izq,
    "cabeceracolumna": cabeceracolumna,
    "celdageneral": celdageneral,
    "celdageneralneg": celdageneralneg,
    "celdageneralcent": celdageneralcent,
    "celdafecha": celdafecha,
    "celdafechaDMA": celdafechaDMA,
    "celdahora": celdahora,
    "celdamoneda": celdamoneda,
    "textonegrita": textonegrita,
    "formatomoneda": formatomoneda,
    "celdanumerodecimal": celdanumerodecimal,
    "celdanumerodecimal4dec": celdanumerodecimal4dec,
    "celdanegritacent": celdanegritacent,
    "celdanegritaizq": celdanegritaizq,
    "celdanegritageneral": celdanegritageneral,
    "celdamonedapie": celdamonedapie,
    "celdanumerodecimal4decpie": celdanumerodecimal4decpie,
    "celdaporcentaje": celdaporcentaje,
    "celdaporcentajepie": celdaporcentajepie
}

DIAS_SEMANA = [
    {"numero": 1, "nombre": "LUNES"},
    {"numero": 2, "nombre": "MARTES"},
    {"numero": 3, "nombre": "MIÉRCOLES"},
    {"numero": 4, "nombre": "JUEVES"},
    {"numero": 5, "nombre": "VIERNES"},
    {"numero": 6, "nombre": "SÁBADO"},
    {"numero": 7, "nombre": "DOMINGO"}
]

DIAS_FERIADOS = [
    datetime.strptime("2024-05-03", '%Y-%m-%d').date(),
    datetime.strptime("2024-05-24", '%Y-%m-%d').date(),
    datetime.strptime("2024-08-09", '%Y-%m-%d').date(),
    datetime.strptime("2024-11-01", '%Y-%m-%d').date(),
    datetime.strptime("2024-12-25", '%Y-%m-%d').date()
]

def analista_investigacion():
    idcargo = variable_valor('ID_CARGO_ANALISTA_INV')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1, persona_id=29119).exists():
        analista = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1, persona_id=29119).order_by('estadopuesto_id')[0].persona
    else:
        analista = None

    return analista


def analista_verifica_informe_docente_invitado():
    idpersona = variable_valor('ID_PERSONA_VIDII')
    if DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).exists():
        analista = DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        analista = None

    return analista


def director_escuela_investigacion():
    idpersona = variable_valor('ID_PERSONA_DEFI')
    if DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).exists():
        analista = DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        analista = None

    return analista


def tecnico_escuela_investigacion_auxiliar():
    idpersona = variable_valor('ID_PERSONA_TARC')
    if DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).exists():
        analista = DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        analista = None

    return analista


def decano_investigacion():
    idpersona = variable_valor('ID_PERSONA_DECINV')
    if DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).exists():
        decano = DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        decano = None

    return decano


def analista_uath_valida_asistencia():
    idpersona = variable_valor('ID_PERSONA_VADII')
    if DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).exists():
        analista = DistributivoPersona.objects.filter(status=True, persona_id=idpersona, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        analista = None

    return analista


def experto_uath_revisa_asistencia():
    idcargo = variable_valor('ID_CARGO_ETHYR')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        experto = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        experto = None

    return experto


def director_uath():
    idcargo = variable_valor('ID_CARGO_DTH')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        director = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        director = None

    return director


def experto_investigacion():
    idcargo = variable_valor('ID_CARGO_EXPERTO_INV')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        experto = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        experto = None

    return experto


def experto_becas_docentes():
    idcargo = variable_valor('ID_CARGO_EXPERTO_BECAS')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        experto = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        experto = None

    return experto


def coordinador_investigacion():
    idcargo = variable_valor('ID_CARGO_COORDINADOR_INV')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        coordinador = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        coordinador = None

    return coordinador


def vicerrector_investigacion_posgrado():
    idcargo = variable_valor('ID_CARGO_VICERRECTOR_INV')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        director = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        director = None

    return director


def rector_institucion():
    idcargo = variable_valor('ID_CARGO_RECTOR')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        rector = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        rector = None

    return rector


def director_juridico():
    idcargo = variable_valor('ID_CARGO_DIRECTOR_JUR')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        director = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        director = None

    return director


def experto_juridico():
    idcargo = variable_valor('ID_CARGO_EXPERTO_JUR')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        experto = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        experto = None

    return experto


def asistente_direccion_cee():
    idcargo = variable_valor('ID_CARGO_ADCEE')
    if DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).exists():
        asistente = DistributivoPersona.objects.filter(status=True, denominacionpuesto_id=idcargo, estadopuesto_id=1).order_by('estadopuesto_id')[0].persona
    else:
        asistente = None

    return asistente


def tecnicos_investigacion():
    # return Persona.objects.filter(status=True, cedula__in=['0925007189', '0926475971', '0919304907', '0929718419']).order_by('apellido1', 'apellido2', 'nombres')
    return Persona.objects.filter(status=True, cedula__in=['0942054024', '0941335531']).order_by('apellido1', 'apellido2', 'nombres')


def tecnico_investigacion():
    return Persona.objects.filter(status=True, cedula='0919304907')[0]


def tecnico_revisor_grupoinvestigacion():
    return Persona.objects.filter(status=True, cedula='0929718419')[0]


def secretaria_comite_becas(convocatoria):
    return convocatoria.comite_institucional_becas().filter(secretario=True, vigente=True)[0].persona


def nombre_archivo_cedula(documento):
    return os.path.basename(documento.cedula.name)


def nombre_archivo_papeleta_votacion(documento):
    return os.path.basename(documento.papeleta.name)


def diff_month(inicio, fin):
    return (fin.year - inicio.year) * 12 + fin.month - inicio.month


def diff_hours(inicio, fin):
    diff = fin - inicio
    return diff.total_seconds() / 3600


def getdaterangefromweek(anio, semana):
    import datetime
    firstdayofweek = datetime.datetime.strptime(f'{anio}-W{int(semana)}-1', "%Y-W%W-%w").date()
    lastdayofweek = firstdayofweek + datetime.timedelta(days=6.9)
    return firstdayofweek, lastdayofweek


def getmonthname(fecha):
    return MESES_CHOICES[fecha.month - 1][1]


def getlastdayofmonth(fecha):
    from datetime import time, datetime, timedelta, date
    last_day_of_month = date(fecha.year, fecha.month, 1) + timedelta(days=32)
    return last_day_of_month - timedelta(days=last_day_of_month.day)


def isvalidurl(url):
    url_regex = re.compile(r'https?://(?:www\.)?[a-zA-Z0-9./]+')
    return bool(url_regex.match(url))


def secuencia_informe_factibilidad(tipo):
    reg = InformeFactibilidad.objects.filter(status=True, tipo=tipo).aggregate(secuencia=Max('secuencia') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def secuencia_informe_grupoinvestigacion():
    from investigacion.models import GrupoInvestigacionInforme
    reg = GrupoInvestigacionInforme.objects.filter(status=True).aggregate(secuencia=Max('secuencia') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def secuencia_solicitud_beca(convocatoria):
    reg = convocatoria.solicitud_set.filter(status=True).aggregate(secuencia=Max('numero') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def secuencia_resolucion_comite(anio):
    reg = ResolucionComite.objects.filter(status=True, fecha__year=anio).aggregate(secuencia=Max('secuencia') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def secuencia_codigo_proyecto(convocatoria, lineainvestigacion):
    from investigacion.models import ProyectoInvestigacion
    reg = ProyectoInvestigacion.objects.filter(status=True, convocatoria=convocatoria, lineainvestigacion=lineainvestigacion).aggregate(secuencia=Max('secuencia') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def secuencia_asesoria(tipo):
    from investigacion.models import CitaAsesoria
    reg = CitaAsesoria.objects.filter(status=True, tipo=tipo).aggregate(secuencia=Max('secuencia') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def secuencia_informe_docente_invitado(anio, tipo):
    from investigacion.models import InformeDocenteInvitado
    reg = InformeDocenteInvitado.objects.filter(status=True, inicio__year=anio, tipo=tipo).aggregate(secuencia=Max('secuencia') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']

    return secuencia


def secuencia_solicitud_validacion_asistencia(anio):
    from investigacion.models import AsistenciaDocenteInvitado
    reg = AsistenciaDocenteInvitado.objects.filter(status=True, fechavalida__year=anio).aggregate(secuencia=Max('secuencia') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def secuencia_reporte_validacion_asistencia(anio):
    from investigacion.models import AsistenciaDocenteInvitado
    reg = AsistenciaDocenteInvitado.objects.filter(status=True, fecharep__year=anio).aggregate(secuenciarep=Max('secuenciarep') + 1)
    if reg['secuenciarep'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuenciarep']
    return secuencia


def secuencia_solicitud_base_institucional():
    from investigacion.models import SolicitudBaseInstitucional
    reg = SolicitudBaseInstitucional.objects.filter(status=True).aggregate(secuencia=Max('secuencia') + 1)
    return reg['secuencia'] if reg['secuencia'] else 1


def secuencia_acuerdo_confidencialidad():
    from investigacion.models import SolicitudBaseInstitucional
    reg = SolicitudBaseInstitucional.objects.filter(status=True).aggregate(secuenciaacuerdo=Max('secuenciaacuerdo') + 1)
    return reg['secuenciaacuerdo'] if reg['secuenciaacuerdo'] else 1


def secuencia_acta_reunion_solicitud_base():
    from investigacion.models import SolicitudBaseInstitucional
    reg = SolicitudBaseInstitucional.objects.filter(status=True).aggregate(secuenciaacta=Max('secuenciaacta') + 1)
    return reg['secuenciaacta'] if reg['secuenciaacta'] else 1


def numero_criterio_evaluacion(convocatoria):
    from investigacion.models import RubricaEvaluacion
    reg = RubricaEvaluacion.objects.filter(status=True, convocatoria=convocatoria).aggregate(numero=Max('numero') + 1)
    return reg['numero'] if reg['numero'] else 1


def aplica_para_director_proyecto(profesor, convocatoria):
    from investigacion.models import ProyectoInvestigacionExclusionValidacion
    if ProyectoInvestigacionExclusionValidacion.objects.values("id").filter(status=True, convocatoria=convocatoria, persona=profesor.persona).exists():
        return {"puedeaplicar": True}
    elif profesor.proyectoinvestigacion_set.values("id").filter(status=True, convocatoria=convocatoria).exists():
        return {"puedeaplicar": False, "mensaje": "", "clase": ""}
    elif profesor.persona.distributivopersona_set.filter(status=True, denominacionpuesto_id__in=[795, 1030, 72], estadopuesto_id=1).exists() or profesor.persona.distributivopersona_set.filter(status=True, persona_id__in=variable_valor('IDS_PERSONAL_PROY_GRUP_INV'), estadopuesto_id=1).exists():
        return {"puedeaplicar": False, "mensaje": "No podrán participar en los proyectos de investigación personal del Vicerrectorado de Investigación y Posgrado", "clase": "alert alert-warning"}
    elif not profesor.categoria:
        return {"puedeaplicar": False, "mensaje": "El director de proyecto será un profesor o investigador titular u ocasional de la institución o profesor investigador invitado", "clase": "alert alert-warning"}
    elif not profesor.categoria.profesortipo.id in [1, 2, 4] or profesor.categoria.id == 9:
        return {"puedeaplicar" : False, "mensaje": "El director de proyecto será un profesor o investigador titular u ocasional de la institución o profesor investigador invitado", "clase": "alert alert-warning"}
    elif not profesor.dedicacion.id == 1:
        return {"puedeaplicar": False, "mensaje": "El director de proyecto será un Profesor, Investigador titular u ocasional de la institución con dedicación a tiempo completo", "clase": "alert alert-warning"}
    elif profesor.categoria.profesortipo.id == 4 and profesor.coordinacion.id not in [7, 10]:
        return {"puedeaplicar": False, "mensaje": "El director de proyecto podrá ser un profesor investigador invitado que pertenezca al Vicerrectorado de Investigación y Posgrado ", "clase": "alert alert-warning"}
    elif not profesor.persona.tiene_titulo_cuarto_nivel():
        return {"puedeaplicar": False, "mensaje": "El director de proyecto debe tener título de cuarto nivel acorde a la temática del proyecto de investigación debidamente registrado en SENESCYT", "clase": "alert alert-warning"}
    elif profesor.persona.proyectoinvestigacionintegrante_set.filter(status=True, funcion=1, proyecto__estado__valor=20).exists():
        tituloproyecto = profesor.persona.proyectoinvestigacionintegrante_set.filter(status=True, funcion=1, proyecto__estado__valor=20)[0].proyecto.titulo
        return {"puedeaplicar": False, "mensaje": f"Usted actualmente consta como director de un proyecto de investigación en ejecución. Título del proyecto: {tituloproyecto}", "clase": "alert alert-danger"}
    else:
        return {"puedeaplicar": True}


def aplica_para_codirector_proyecto(profesor, convocatoria):
    from investigacion.models import ProyectoInvestigacionExclusionValidacion
    if ProyectoInvestigacionExclusionValidacion.objects.values("id").filter(status=True, convocatoria=convocatoria, persona=profesor.persona).exists():
        return {"puedeaplicar": True}
    elif profesor.persona.distributivopersona_set.filter(status=True, denominacionpuesto_id__in=[795, 1030, 72], estadopuesto_id=1).exists() or profesor.persona.distributivopersona_set.filter(status=True, persona_id__in=variable_valor('IDS_PERSONAL_PROY_GRUP_INV'), estadopuesto_id=1).exists():
        return {"puedeaplicar": False, "mensaje": "No podrán participar en los proyectos de investigación personal del Vicerrectorado de Investigación y Posgrado", "clase": "alert alert-warning"}
    elif not profesor.categoria:
        return {"puedeaplicar": False, "mensaje": "El co-director de proyecto será un profesor o investigador titular u ocasional de la institución o profesor investigador invitado", "clase": "alert alert-warning"}
    elif not profesor.categoria.profesortipo.id in [1, 2, 4] or profesor.categoria.id == 9:
        return {"puedeaplicar" : False, "mensaje": "El co-director de proyecto será un profesor o investigador titular u ocasional de la institución o profesor investigador invitado", "clase": "alert alert-warning"}
    elif not profesor.dedicacion.id == 1:
        return {"puedeaplicar": False, "mensaje": "El co-director de proyecto será un Profesor, Investigador titular u ocasional de la institución con dedicación a tiempo completo", "clase": "alert alert-warning"}
    elif profesor.categoria.profesortipo.id == 4 and profesor.coordinacion.id not in [7, 10]:
        return {"puedeaplicar": False, "mensaje": "El co-director de proyecto podrá ser un profesor investigador invitado que pertenezca al Vicerrectorado de Investigación y Posgrado ", "clase": "alert alert-warning"}
    elif not profesor.persona.tiene_titulo_cuarto_nivel():
        return {"puedeaplicar": False, "mensaje": "El co-director de proyecto debe tener título de cuarto nivel acorde a la temática del proyecto de investigación debidamente registrado en SENESCYT", "clase": "alert alert-warning"}
    elif profesor.persona.proyectoinvestigacionintegrante_set.filter(status=True, funcion=2, proyecto__estado__valor=20).exists():
        tituloproyecto = profesor.persona.proyectoinvestigacionintegrante_set.filter(status=True, funcion=2, proyecto__estado__valor=20)[0].proyecto.titulo
        return {"puedeaplicar": False, "mensaje": f"La persona actualmente consta como co-director de un proyecto de investigación en ejecución. Título del proyecto: {tituloproyecto}", "clase": "alert alert-danger"}
    else:
        return {"puedeaplicar": True}


def aplica_para_ayudante_investigacion_proyecto(inscripcion, convocatoria):
    from investigacion.models import ProyectoInvestigacionExclusionValidacion
    if ProyectoInvestigacionExclusionValidacion.objects.values("id").filter(status=True, convocatoria=convocatoria, persona=inscripcion.persona).exists():
        return {"puedeaplicar": True}
    elif inscripcion.persona.distributivopersona_set.filter(status=True, denominacionpuesto_id__in=[795, 1030, 72], estadopuesto_id=1).exists() or inscripcion.persona.distributivopersona_set.filter(status=True, persona_id__in=variable_valor('IDS_PERSONAL_PROY_GRUP_INV'), estadopuesto_id=1).exists():
        return {"puedeaplicar": False, "mensaje": "No podrán participar en los proyectos de investigación personal del Vicerrectorado de Investigación y Posgrado", "clase": "alert alert-warning"}
    elif inscripcion.egresado() or inscripcion.es_graduado():
        return {"puedeaplicar": False, "mensaje": "Los ayudantes de investigación son estudiantes regulares de grado (desde quinto semestre en adelante) o de posgrado de la institución", "clase": "alert alert-warning"}
    elif inscripcion.carrera.niveltitulacion.nivel == 3:
        ultimamatricula = inscripcion.ultima_matricula()
        if not ultimamatricula:
            return {"puedeaplicar": False, "mensaje": "Los ayudantes de investigación son estudiantes regulares de grado (desde quinto semestre en adelante) o de posgrado de la institución", "clase": "alert alert-warning"}
        elif not ultimamatricula.nivelmalla.orden > 4 or ultimamatricula.tipomatriculalumno() != 'REGULAR':
            return {"puedeaplicar": False, "mensaje": "Los ayudantes de investigación son estudiantes regulares de grado (desde quinto semestre en adelante) o de posgrado de la institución", "clase": "alert alert-warning"}
        else:
            return {"puedeaplicar": True}
    elif inscripcion.persona.proyectoinvestigacionintegrante_set.filter(status=True, proyecto__convocatoria__tipo__in=[1, 2], proyecto__estado__valor__in=[20, 21, 26]).count() >= 2:
        return {"puedeaplicar": False, "mensaje": f"Cada miembro del equipo solo podrá integrar hasta dos proyectos de UNEMI con financiamiento interno o en conjunto, independiente de la convocatoria.", "clase": "alert alert-danger"}
    else:
        return {"puedeaplicar": True}


def aplica_para_investigador_asociado_investigacion_proyecto(persona, convocatoria):
    from investigacion.models import ProyectoInvestigacionExclusionValidacion
    if ProyectoInvestigacionExclusionValidacion.objects.values("id").filter(status=True, convocatoria=convocatoria, persona=persona).exists():
        return {"puedeaplicar": True}
    elif persona.distributivopersona_set.filter(status=True, denominacionpuesto_id__in=[795, 1030, 72], estadopuesto_id=1).exists() or persona.distributivopersona_set.filter(status=True, persona_id__in=variable_valor('IDS_PERSONAL_PROY_GRUP_INV'), estadopuesto_id=1).exists():
        return {"puedeaplicar": False, "mensaje": "No podrán participar en los proyectos de investigación personal del Vicerrectorado de Investigación y Posgrado", "clase": "alert alert-warning"}
    elif persona.proyectoinvestigacionintegrante_set.filter(status=True, proyecto__convocatoria__tipo__in=[1, 2], proyecto__estado__valor__in=[20, 21, 26]).count() >= 2:
        return {"puedeaplicar": False, "mensaje": f"Cada miembro del equipo solo podrá integrar hasta dos proyectos de UNEMI con financiamiento interno o en conjunto, independiente de la convocatoria.", "clase": "alert alert-danger"}
    else:
        return {"puedeaplicar": True}


def aplica_para_investigador_colaborador_proyecto(persona, convocatoria):
    from investigacion.models import ProyectoInvestigacionExclusionValidacion
    if ProyectoInvestigacionExclusionValidacion.objects.values("id").filter(status=True, convocatoria=convocatoria, persona=persona).exists():
        return {"puedeaplicar": True}
    elif persona.distributivopersona_set.filter(status=True, denominacionpuesto_id__in=[795, 1030, 72], estadopuesto_id=1).exists() or persona.distributivopersona_set.filter(status=True, persona_id__in=variable_valor('IDS_PERSONAL_PROY_GRUP_INV'), estadopuesto_id=1).exists():
        return {"puedeaplicar": False, "mensaje": "No podrán participar en los proyectos de investigación personal del Vicerrectorado de Investigación y Posgrado", "clase": "alert alert-warning"}
    elif persona.proyectoinvestigacionintegrante_set.filter(status=True, proyecto__convocatoria__tipo__in=[1, 2], proyecto__estado__valor__in=[20, 21, 26]).count() >= 2:
        return {"puedeaplicar": False, "mensaje": f"Cada miembro del equipo solo podrá integrar hasta dos proyectos de UNEMI con financiamiento interno o en conjunto, independiente de la convocatoria.", "clase": "alert alert-danger"}
    else:
        return {"puedeaplicar": True}


def mensaje_consideraciones_integrantes(proyecto):
    lista = []
    integrantes = proyecto.integrantes_proyecto()
    if len(integrantes) > 1:
        if not integrantes.filter(profesor__categoria__profesortipo__id=1, profesor__dedicacion__id=1).exclude(funcion=1).exists():
            lista.append({"mensaje": "Para aprobación del proyecto, este deberá contar con un profesor titular a tiempo completo de manera obligatoria, que pueda asumir el rol de Director en caso de ausencia temporal o permanente del mismo."})

        if not integrantes.filter(funcion=4).count() >= 2:
            lista.append({"mensaje": "El proyecto deberá contar con mínimo 2 ayudantes de investigación."})

    return lista


def periodo_vigente_distributivo_docente_investigacion(profesor):
    periodovigente = None
    # fechaactual = datetime.strptime('2023' + '-' + '04' + '-' + '13', '%Y-%m-%d').date()
    fechaactual = datetime.now().date()

    # Consulto los id de los periodos donde tiene registrado distributivo el docente
    periodosid = ProfesorDistributivoHoras.objects.values_list('periodo__id').filter(profesor=profesor, periodo__visible=True, periodo__status=True)
    if periodosid:
        # Consulto los periodos
        periodosdocente = Periodo.objects.select_related('tipo').filter(id__in=periodosid).order_by('-inicio')

        # Consulto el periodo vigente
        periodovigente = periodosdocente.filter(inicio__lte=fechaactual, fin__gte=fechaactual).order_by('-marcardefecto')[0] if periodosdocente.filter(inicio__lte=fechaactual, fin__gte=fechaactual).exists() else None

        # Verifico que tenga horas de investigación asignadas en el periodo
        if periodovigente:
            distributivo = profesor.profesordistributivohoras_set.filter(status=True, periodo=periodovigente)[0]

            if not distributivo.detalledistributivo_set.filter(status=True, criterioinvestigacionperiodo__isnull=False):
                periodovigente = None

        return periodovigente
    else:
        return periodovigente


def periodo_vigente_distributivo_docente(profesor):
    periodovigente = None
    fechaactual = datetime.now().date()

    # Consulto los id de los periodos donde tiene registrado distributivo el docente
    periodosid = ProfesorDistributivoHoras.objects.values_list('periodo__id').filter(profesor=profesor, periodo__visible=True, periodo__status=True)
    if periodosid:
        # Consulto los periodos
        periodosdocente = Periodo.objects.select_related('tipo').filter(id__in=periodosid).order_by('-inicio')

        # Consulto el periodo vigente
        periodovigente = periodosdocente.filter(inicio__lte=fechaactual, fin__gte=fechaactual).order_by('-marcardefecto')[0] if periodosdocente.filter(inicio__lte=fechaactual, fin__gte=fechaactual).exists() else None

        return periodovigente
    else:
        return periodovigente


def coordinacion_carrera_distributivo_docente(profesor):
    periodovigente = periodo_vigente_distributivo_docente(profesor)
    if periodovigente:
        distributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodovigente, profesor=profesor)[0]
        return {"idcoordinacion": distributivo.coordinacion.id,
                "coordinacion": distributivo.coordinacion.nombre,
                "aliascoordinacion": distributivo.coordinacion.alias,
                "idcarrera": distributivo.carrera.id if distributivo.carrera else 0,
                "carrera": distributivo.carrera.nombre if distributivo.carrera else '',
                "aliascarrera": distributivo.carrera.alias if distributivo.carrera else ''}
    else:
        return {"idcoordinacion": 0,
                "coordinacion": "",
                "aliascoordinacion": "",
                "idcarrera": 0,
                "carrera": "",
                "aliascarrera": ""}


def es_director_carrera(profesor):
    periodovigente = periodo_vigente_distributivo_docente(profesor)
    if periodovigente:
        return CoordinadorCarrera.objects.values("id").filter(status=True, periodo=periodovigente, persona=profesor.persona, tipo=3).exists()
    else:
        return False


def tiene_horas_docencia(profesor):
    periodovigente = periodo_vigente_distributivo_docente(profesor)
    if periodovigente:
        return ProfesorDistributivoHoras.objects.values("id").filter(status=True, periodo=periodovigente, profesor=profesor, horasdocencia__gt=0).exists()
    else:
        return False


def salto_linea_nombre_firma_encontrado(texto):
    lista = texto.split("\n")
    c = 0

    for item in lista:
        if item not in ["", " "]:
            c += 1

    return c == 2


def reemplazar_fuente_para_informe(texto):
    soup = BeautifulSoup(texto, 'html.parser')
    p_tags = soup.find_all('span')
    for p_tag in p_tags:
        p_tag['style'] = 'font-family: "Berlin Sans FB Demi"; font-size: 14px;'

    soup.prettify()

    p_tags = soup.find_all('p')
    for p_tag in p_tags:
        p_tag['style'] = 'margin-left:0px; margin-right:0px; text-align:justify'

    p_tags = soup.find_all('table')
    for p_tag in p_tags:
        p_tag['style'] = 'width: "100%"; border: 0.5px solid #000000; font-size:11px; line-height:15px; vertical-align:top; padding:3px; font-family: "Berlin Sans FB Demi"'

    return soup.prettify()


def reemplazar_fuente_para_formato_inscripcion(texto, fuente, tamanio):
    soup = BeautifulSoup(texto, 'html.parser')
    p_tags = soup.find_all('span')
    for p_tag in p_tags:
        p_tag['style'] = f'font-family: "{fuente}"; font-size: {tamanio}px;'

    soup.prettify()

    p_tags = soup.find_all('p')
    for p_tag in p_tags:
        p_tag['style'] = 'margin-left:0px; margin-right:0px; text-align:justify'

    p_tags = soup.find_all('table')
    for p_tag in p_tags:
        p_tag['style'] = f'width: "100%"; border: 0.5px solid #000000; font-size:11px; line-height:15px; vertical-align:top; padding:3px; font-family: "{fuente}"'

    return soup.prettify()


def elemento_repetido_lista(lista):
    listado = [elemento.strip().upper() for elemento in lista]
    repetido = [x for x, y in collections.Counter(listado).items() if y > 1]
    return repetido


def extension_archivo(nombrearchivo):
    return f'.{nombrearchivo.split(".")[-1].lower()}'


def secuencia_solicitud_certificacion(convocatoria):
    reg = convocatoria.certificacionpresupuestaria_set.filter(status=True).aggregate(secuencia=Max('numero') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def secuencia_solicitud_grupo_investigacion():
    from investigacion.models import GrupoInvestigacion
    reg = GrupoInvestigacion.objects.filter(status=True).aggregate(secuencia=Max('numero') + 1)
    if reg['secuencia'] is None:
        secuencia = 1
    else:
        secuencia = reg['secuencia']
    return secuencia


def responsable_coordinacion(periodo, coordinacion):
    if ResponsableCoordinacion.objects.values("id").filter(status=True, periodo=periodo, coordinacion=coordinacion, tipo=1).exists():
        return ResponsableCoordinacion.objects.get(status=True, periodo=periodo, coordinacion=coordinacion, tipo=1)
    else:
        return None


def identificacion_valida(cedula, pasaporte):
    if cedula:
        resp = validarcedula(cedula)
        if resp.lower() != "ok":
            return {"estado": "error", "mensaje": resp}

        if Persona.objects.values('id').filter(Q(cedula=cedula) | Q(pasaporte=cedula), status=True).exists():
            return {"estado": "error", "mensaje": "La persona ya está registrada en la base de datos"}

    if pasaporte:
        if pasaporte[:2] != 'VS':
            return {"estado": "error", "mensaje": "Pasaporte mal ingresado, no olvide colocar <b>VS</b> al inicio"}

        if Persona.objects.values('id').filter(Q(cedula=pasaporte) | Q(pasaporte=pasaporte), status=True).exists():
            return {"estado": "error", "mensaje": "La persona ya está registrada en la base de datos"}

    return {"estado": "OK"}


def url_atencion_virtual(persona):
    from investigacion.models import EnlaceAtencionVirtualPersona
    if EnlaceAtencionVirtualPersona.objects.values("id").filter(persona=persona, status=True).exists():
        return EnlaceAtencionVirtualPersona.objects.filter(persona=persona, status=True)[0].url
    else:
        return None


def tipo_vista_gestion_asesoria(persona):
    from investigacion.models import Gestion, ResponsableServicio
    if persona.es_coordinador_investigacion() or persona == director_escuela_investigacion():
        return 'CI'
    elif Gestion.objects.values("id").filter(status=True, responsable=persona).exists() or persona == tecnico_escuela_investigacion_auxiliar():
        return 'RG'
    elif ResponsableServicio.objects.values("id").filter(status=True, responsable=persona, servicioresponsableservicio__isnull=False, servicioresponsableservicio__status=True).exists():
        return 'RS'
    else:
        return 'SL'


def codigo_publicacion_valido(codigo, tipo):
    if tipo in ['CAP', 'LIB', 'ART']:
        return codigo[0].isdigit() and codigo.count(' ') == 1
    else:
        return codigo[0].isdigit() and codigo.count('-') == 1 and ' ' not in codigo


def iniciales_nombres_apellidos(persona):
    iniciales = ''
    if ' ' in persona.nombres:
        iniciales = f'{persona.nombres.split(" ")[0][0]}{persona.nombres.split(" ")[1][0]}'
    else:
        iniciales = persona.nombres[0]

    if persona.apellido2:
        iniciales = f'{iniciales}{persona.apellido1[0]}{persona.apellido2[0]}'
    else:
        iniciales = f'{iniciales}{persona.apellido1[0]}'

    return iniciales


def guardar_recorrido_informe_docente_invitado(informe, estado, observacion, request):
    from investigacion.models import RecorridoInformeDocenteInvitado
    recorrido = RecorridoInformeDocenteInvitado(
        informe=informe,
        fecha=datetime.now(),
        observacion=observacion if observacion else estado.observacion,
        estado=estado
    )
    recorrido.save(request)


def guardar_recorrido_solicitud_base_institucional(solicitud, estado, observacion, request):
    from investigacion.models import RecorridoSolicitudBaseInstitucional
    recorrido = RecorridoSolicitudBaseInstitucional(
        solicitud=solicitud,
        fecha=datetime.now(),
        observacion=observacion if observacion else estado.observacion,
        estado=estado
    )
    recorrido.save(request)


def guardar_historial_archivo_proyectos_investigacion(proyecto, tipodocumento, archivo, request):
    from investigacion.models import ProyectoInvestigacionHistorialArchivo

    # Quitar vigencia de archivos anteriores
    ProyectoInvestigacionHistorialArchivo.objects.filter(status=True, vigente=True, proyecto=proyecto, tipodocumento=tipodocumento).update(vigente=False)

    # Crea el historial del archivo
    historialarchivo = ProyectoInvestigacionHistorialArchivo(
        proyecto=proyecto,
        tipo=1,
        descripcion=tipodocumento.descripcion,
        archivo=archivo,
        tipodocumento=tipodocumento,
        vigente=True
    )
    historialarchivo.save(request)


def existen_informes_conformidad_pendiente_firmar():
    from investigacion.models import InformeDocenteInvitado
    if InformeDocenteInvitado.objects.values("id").filter(status=True, tipo=2, firmaelabora=True, firmavalida=False, firmaaprueba=False).exists():
        return {"icsinfirma": True, "mensaje": "Existen Informes de Conformidad de Resultados pendientes de firmar por parte del usuario validador y del usuario aprobador"}
    elif InformeDocenteInvitado.objects.values("id").filter(status=True, tipo=2, firmaelabora=True, firmavalida=True, firmaaprueba=False).exists():
        return {"icsinfirma": True, "mensaje": "Existen Informes de Conformidad de Resultados pendientes de firmar por parte del usuario aprobador"}
    elif InformeDocenteInvitado.objects.values("id").filter(status=True, tipo=2, firmaelabora=True, firmavalida=False).exists():
        return {"icsinfirma": True, "mensaje": "Existen Informes de Conformidad de Resultados pendientes de firmar por parte del usuario validador"}
    else:
        return {"icsinfirma": False, "mensaje": ""}


def actualizar_permiso_edicion_rubros_presupuesto(proyecto, tiporegistro, tipopersona, request):
    # Si está en EJECUCIÓN
    if proyecto.estado.valor == 20:
        permiso = proyecto.permiso_edicion_vigente(tiporegistro, tipopersona)
        if permiso:
            if permiso.estado == 1:
                permiso.inicioedi = datetime.now().date()
                permiso.estado = 2
                permiso.save(request)


def notificar_revision_solicitud_produccion_cientifica(solicitudpublicacion):
    # Si no es pre-aprobado se notifica a solicitante
    if solicitudpublicacion.estado.valor != 6:
        persona = solicitudpublicacion.persona
    else:
        persona = coordinador_investigacion()

    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
    listacuentascorreo = [29]  # investigacion.dip@unemi.edu.ec
    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()

    # E-mail del destinatario
    lista_email_envio = persona.lista_emails_envio()
    lista_email_cco = []
    lista_adjuntos = []

    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    titulo = "Producción Científica"

    if solicitudpublicacion.estado.valor == 2:  # VALIDADO
        tiponotificacion = 'SOLVAL'
        tituloemail = u"Solicitud de Registro de Producción Científica Validada"
    elif solicitudpublicacion.estado.valor == 3:  # NOVEDADES
        tiponotificacion = 'NOVSOL'
        tituloemail = u"Novedades Solicitud de Registro de Producción Científica"
    elif solicitudpublicacion.estado.valor == 4:  # RECHAZADO
        tiponotificacion = 'RECSOL'
        tituloemail = u"Solicitud de Registro de Producción Científica Rechazada"
    elif solicitudpublicacion.estado.valor == 6:  # PRE-APROBADO
        tiponotificacion = 'SOLPREAPRO'
        tituloemail = u"Solicitud de Registro de Producción Científica Pre-Aprobada"
    else:  # RECHAZADO
        tiponotificacion = 'SOLAPRO'
        tituloemail = u"Solicitud de Registro de Producción Científica Aprobada"

    # Notificar por e-mail
    send_html_mail(tituloemail,
                   "emails/solicitudpublicacion.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion,
                    'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                    'nombrepersona': persona.nombre_completo_inverso(),
                    'solicitudpublicacion': solicitudpublicacion
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )


def notificar_grupo_investigacion(grupoinvestigacion, tiponotificacion):
    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
    if tiponotificacion in ['REGSOL', 'REGDEC', 'REVSOL', 'NOVSOL', 'APRFAC', 'NOTVICE']:
        listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec
    else:
        listacuentascorreo = [29]  # investigacion@unemi.edu.ec

    titulo = "Grupos de Investigación"
    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    if tiponotificacion == 'REGSOL':
        asuntoemail = "Solicitud de Propuesta para Creación de Grupo de Investigación"
        persona = grupoinvestigacion.profesor.persona
    elif tiponotificacion == 'REGDEC':
        asuntoemail = "Solicitud de Propuesta para Creación de Grupo de Investigación"
        persona = responsable_coordinacion(grupoinvestigacion.periodo, grupoinvestigacion.coordinacion).persona
    elif tiponotificacion == 'REVSOL':
        asuntoemail = "Solicitud de Propuesta para Creación de Grupo de Investigación Revisada"
        persona = grupoinvestigacion.profesor.persona
    elif tiponotificacion == 'NOVSOL':
        asuntoemail = "Novedades Solicitud de Propuesta para Creación de Grupo de Investigación"
        persona = grupoinvestigacion.profesor.persona
    elif tiponotificacion == 'APRFAC':
        asuntoemail = "Aprobación Consejo de Facultad para la Propuesta de Creación de Grupo de Investigación"
        persona = grupoinvestigacion.profesor.persona
    elif tiponotificacion == 'NOTVICE':
        asuntoemail = "Aprobación Consejo de Facultad para la Propuesta de Creación de Grupo de Investigación"
        persona = vicerrector_investigacion_posgrado()
    elif tiponotificacion in ['NOTCOORD', 'NOTANL']:
        asuntoemail = "Reasignación para Análisis de Propuesta de Creación de Grupo de Investigación"
        persona = coordinador_investigacion() if tiponotificacion == 'NOTCOORD' else tecnico_revisor_grupoinvestigacion()
    elif tiponotificacion == 'VALSOL':
        asuntoemail = "Solicitud de Propuesta para Creación de Grupo de Investigación Analizada y Validada"
        persona = grupoinvestigacion.profesor.persona
    elif tiponotificacion == 'NOVANLSOL':
        asuntoemail = "Novedades detectadas en la etapa de Análisis de la Solicitud de Propuesta para Creación de Grupo de Investigación"
        persona = coordinador_investigacion()
    elif tiponotificacion in ['DEVVICE', 'DEVSOL']:
        asuntoemail = "Devolución de Requerimiento de Propuesta de Creación de Grupo de Investigación"
        persona = vicerrector_investigacion_posgrado() if tiponotificacion == 'DEVVICE' else grupoinvestigacion.profesor.persona
    elif tiponotificacion == 'INFOELA':
        asuntoemail = "Informe Técnico de Creación de Grupo de Investigación Elaborado"
        persona = experto_investigacion()
    elif tiponotificacion == 'INFONOV':
        asuntoemail = "Novedades en Informe Técnico de Creación de Grupo de Investigación"
        persona = grupoinvestigacion.informe().elabora
    elif tiponotificacion == 'INFOVAL':
        asuntoemail = "Informe Técnico de Creación de Grupo de Investigación Revisado"
        persona = coordinador_investigacion()
    elif tiponotificacion == 'INFOAPR':
        asuntoemail = "Informe Técnico de Creación de Grupo de Investigación Aprobado"
        persona = vicerrector_investigacion_posgrado()
    elif tiponotificacion in ['APROCS', 'NOTVICEOCS', 'NOTCOORDOCS']:
        asuntoemail = "Propuesta de Creación de Grupo de Investigación Aprobada por OCS"
        if tiponotificacion == 'APROCS':
            persona = grupoinvestigacion.profesor.persona
        elif tiponotificacion == 'NOTVICEOCS':
            persona = vicerrector_investigacion_posgrado()
        else:
            persona = coordinador_investigacion()

    # E-mail del destinatario
    lista_email_envio = persona.lista_emails_envio()
    lista_email_cco = ['ivan_saltos_medina@hotmail.com']
    lista_archivos_adjuntos = []

    send_html_mail(asuntoemail,
                   "emails/propuestagrupoinvestigacion.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion,
                    'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                    'nombrepersona': persona.nombre_completo_inverso(),
                    'grupoinvestigacion': grupoinvestigacion,
                    'nombredocente': grupoinvestigacion.profesor.persona.nombre_completo_inverso(),
                    'saludodocente': 'la docente' if grupoinvestigacion.profesor.persona.sexo_id == 1 else 'el docente',
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_archivos_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )


def notificar_docente_invitado(registro, tiponotificacion):
    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
    if tiponotificacion in ['REGHOR', 'ENVINF', 'VALASIS', 'NOVASIS', 'REVASIS', 'APRASIS']:
        listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec
    else:
        listacuentascorreo = [29]  # investigacion@unemi.edu.ec

    titulo = "Profesores Invitados Investigación"
    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    if tiponotificacion == 'REGHOR':
        asuntoemail = "Horario de Actividades de Profesor Invitado Registrado"
        analista = analista_verifica_informe_docente_invitado()
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        personae = registro.docente.profesor.persona
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'
    elif tiponotificacion in ['APRHOR', 'NOVHOR']:
        asuntoemail = "Horario de Actividades de Profesor Invitado Aprobado" if tiponotificacion == 'APRHOR' else "Novedades con Horario de Actividades de Profesor Invitado"
        analista = None
        personae = registro.docente.profesor.persona
        lista_email_envio = personae.lista_emails_envio()
        saludo = 'Estimada' if personae.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'ENVINF':
        asuntoemail = "Informe de Actividades de Profesor Invitado Enviado"
        analista = analista_verifica_informe_docente_invitado()
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        personae = registro.docente.profesor.persona
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'VALINF':
        asuntoemail = "Informe de Actividades de Profesor Invitado Validado"
        analista = None
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        personae = registro.docente.profesor.persona
        lista_email_envio = personae.lista_emails_envio()
        saludo = 'Estimada' if personae.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'FIRSOLASIS':
        asuntoemail = "Firmar Solicitud de Validación de Asistencias de Profesores Invitados"
        analista = decano_investigacion()
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        personae = analista
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'SOLASIS':
        asuntoemail = "Solicitud de Validación de Asistencia de Profesor Invitados"
        analista = analista_uath_valida_asistencia()
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        personae = analista
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'
    elif tiponotificacion in ['VALASIS', 'NOVASIS']:
        asuntoemail = "Asistencia de Profesor Invitado Validada" if tiponotificacion == 'VALASIS' else "Novedades Validación Asistencia de Profesor Invitado"
        if tiponotificacion == 'VALASIS':
            analista = experto_uath_revisa_asistencia()
        else:
            analista = analista_verifica_informe_docente_invitado()

        personae = registro.informe.docente.profesor.persona
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'REVASIS':
        asuntoemail = "Asistencia de Profesor Invitado Revisada"
        analista = director_uath()
        personae = registro.informe.docente.profesor.persona
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'APRASIS':
        asuntoemail = "Solicitud de Validación de Asistencia de Profesores Invitados Aprobada"
        analista = analista_verifica_informe_docente_invitado()
        personae = analista
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'VALINFCONF':
        asuntoemail = "Firmar Informe de Conformidad de Resultados de Profesores Invitados"
        analista = director_escuela_investigacion()
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        personae = analista
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'APRINFCONF':
        asuntoemail = "Firmar Informe de Conformidad de Resultados de Profesores Invitados"
        analista = decano_investigacion()
        lista_email_envio = analista.lista_emails_envio()
        # lista_email_envio = ['isaltosm@unemi.edu.ec']
        personae = analista
        saludo = 'Estimada' if analista.sexo_id == 1 else 'Estimado'


    # E-mail del destinatario
    # lista_email_cco = []
    lista_email_cco = []
    lista_archivos_adjuntos = []

    send_html_mail(asuntoemail,
                   "emails/docenteinvitadoinvestigacion.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion,
                    'saludo': saludo,
                    'nombreanalista': analista.nombre_completo_inverso() if analista else '',
                    'nombredocente': personae.nombre_completo_inverso(),
                    'saludodocente': 'la docente' if personae.sexo_id == 1 else 'el docente',
                    'registro': registro
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_archivos_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )


def notificar_asesoria_investigacion(citaasesoria, tiponotificacion, request):
    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
    if tiponotificacion in ['AGECIT', 'AGECITSOL', 'REACIT', 'CANCIT']:
        listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec
    else:
        listacuentascorreo = [29]  # investigacion@unemi.edu.ec

    titulo = "Asesorías en Investigación"
    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    # Obtener fecha en letras
    dialetras = dia_semana_enletras_fecha(citaasesoria.fecha)
    fechadialetras = dialetras + " " + str(citaasesoria.fecha.day) + " de " + MESES_CHOICES[citaasesoria.fecha.month - 1][1].capitalize() + " del " + str(citaasesoria.fecha.year)
    mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + citaasesoria.horainicio.strftime('%H:%M') + " a " + citaasesoria.horafin.strftime('%H:%M') + "</b>"

    if tiponotificacion == 'AGECIT':
        asuntoemail = "Agendamiento de Cita para Asesoría en Investigación"
        responsable = citaasesoria.responsable
        solicitante = citaasesoria.solicitante

        if citaasesoria.tiposolicitante == 1:
            saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        elif citaasesoria.tiposolicitante == 2:
            saludosolicitante = 'la servidora' if solicitante.sexo_id == 1 else 'el servidor'
        else:
            saludosolicitante = 'la estudiante' if solicitante.sexo_id == 1 else 'el estudiante'

        lista_email_envio = responsable.lista_emails_envio()
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'AGECITSOL':
        asuntoemail = "Agendamiento de Cita para Asesoría en Investigación"
        responsable = citaasesoria.responsable
        solicitante = citaasesoria.solicitante

        if citaasesoria.tiposolicitante == 1:
            saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        elif citaasesoria.tiposolicitante == 2:
            saludosolicitante = 'la servidora' if solicitante.sexo_id == 1 else 'el servidor'
        else:
            saludosolicitante = 'la estudiante' if solicitante.sexo_id == 1 else 'el estudiante'
        lista_email_envio = solicitante.lista_emails_envio()
        saludo = 'Estimada' if solicitante.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'REACIT':
        asuntoemail = "Re-Agendamiento de Cita para Asesoría en Investigación"
        responsable = citaasesoria.responsable
        solicitante = citaasesoria.solicitante

        if citaasesoria.tiposolicitante == 1:
            saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        elif citaasesoria.tiposolicitante == 2:
            saludosolicitante = 'la servidora' if solicitante.sexo_id == 1 else 'el servidor'
        else:
            saludosolicitante = 'la estudiante' if solicitante.sexo_id == 1 else 'el estudiante'

        lista_email_envio = responsable.lista_emails_envio()
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'

    elif tiponotificacion == 'REACITSOL':
        asuntoemail = "Re-Agendamiento de Cita para Asesoría en Investigación"
        responsable = citaasesoria.responsable
        solicitante = citaasesoria.solicitante

        if citaasesoria.tiposolicitante == 1:
            saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        elif citaasesoria.tiposolicitante == 2:
            saludosolicitante = 'la servidora' if solicitante.sexo_id == 1 else 'el servidor'
        else:
            saludosolicitante = 'la estudiante' if solicitante.sexo_id == 1 else 'el estudiante'
        lista_email_envio = solicitante.lista_emails_envio()
        saludo = 'Estimada' if solicitante.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'CANCIT':
        asuntoemail = "Cita para Asesoría en Investigación Cancelada"
        responsable = citaasesoria.responsable
        solicitante = citaasesoria.solicitante

        if citaasesoria.tiposolicitante == 1:
            saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        elif citaasesoria.tiposolicitante == 2:
            saludosolicitante = 'la servidora' if solicitante.sexo_id == 1 else 'el servidor'
        else:
            saludosolicitante = 'la estudiante' if solicitante.sexo_id == 1 else 'el estudiante'

        lista_email_envio = responsable.lista_emails_envio()
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'CANCITSOL':
        asuntoemail = "Cita para Asesoría en Investigación Cancelada"
        responsable = citaasesoria.responsable
        solicitante = citaasesoria.solicitante

        if citaasesoria.tiposolicitante == 1:
            saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        elif citaasesoria.tiposolicitante == 2:
            saludosolicitante = 'la servidora' if solicitante.sexo_id == 1 else 'el servidor'
        else:
            saludosolicitante = 'la estudiante' if solicitante.sexo_id == 1 else 'el estudiante'

        lista_email_envio = responsable.lista_emails_envio()
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'

    # E-mail del destinatario
    lista_email_cco = []
    lista_archivos_adjuntos = []

    send_html_mail(asuntoemail,
                   "emails/asesoriainvestigacion.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion,
                    'citaasesoria': citaasesoria,
                    'saludo': saludo,
                    'responsable': responsable.nombre_completo_inverso(),
                    'solicitante': solicitante.nombre_completo_inverso(),
                    'saludosolicitante': saludosolicitante,
                    'mensajehorario': mensajehorario
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_archivos_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )

    # Notificación Push
    app_label = "sga"
    if tiponotificacion == 'AGECIT':
        titulo = "Agendamiento de Cita para Asesoría en Investigación"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> {saludosolicitante} " \
                 f"<b>{solicitante}</b> agendó con usted para el {mensajehorario} una cita para el " \
                 f"servicio de <b>{citaasesoria.servicio.nombre}</b> por el siguiente motivo: {citaasesoria.motivo}"
        destinatario = citaasesoria.responsable
        url = "/adm_asesoriainvestigacion"
        object_id = citaasesoria.id
        prioridad = 1
    elif tiponotificacion == 'AGECITSOL':
        titulo = "Agendamiento de Cita para Asesoría en Investigación"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted " \
                 f"agendó con <b>{responsable}</b> para el {mensajehorario} una cita para el " \
                 f"servicio de <b>{citaasesoria.servicio.nombre}</b> por el siguiente motivo: {citaasesoria.motivo}"
        destinatario = citaasesoria.solicitante
        url = "/pro_asesoriainvestigacion"
        object_id = citaasesoria.id
        prioridad = 1
    elif tiponotificacion == 'REACIT':
        titulo = "Re-Agendamiento de Cita para Asesoría en Investigación"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> {saludosolicitante} " \
                 f"<b>{solicitante}</b> re-agendó con usted para el {mensajehorario} una cita para el " \
                 f"servicio de <b>{citaasesoria.servicio.nombre}</b> por el siguiente motivo: {citaasesoria.motivo}"
        destinatario = citaasesoria.responsable
        url = "/adm_asesoriainvestigacion"
        object_id = citaasesoria.id
        prioridad = 1
    elif tiponotificacion == 'REACITSOL':
        titulo = "Re-Agendamiento de Cita para Asesoría en Investigación"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted " \
                 f"re-agendó con <b>{responsable}</b> para el {mensajehorario} una cita para el " \
                 f"servicio de <b>{citaasesoria.servicio.nombre}</b> por el siguiente motivo: {citaasesoria.motivo}"
        destinatario = citaasesoria.solicitante
        url = "/pro_asesoriainvestigacion"
        object_id = citaasesoria.id
        prioridad = 1
    elif tiponotificacion == 'CANCIT':
        titulo = "Cita para Asesoría en Investigación Cancelada"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> {saludosolicitante} " \
                 f"<b>{solicitante}</b> canceló la cita agendada con usted para el {mensajehorario} para el " \
                 f"servicio de <b>{citaasesoria.servicio.nombre}</b> por el siguiente motivo: {citaasesoria.observacion}"
        destinatario = citaasesoria.responsable
        url = "/adm_asesoriainvestigacion"
        object_id = citaasesoria.id
        prioridad = 1
    elif tiponotificacion == 'CANCITSOL':
        titulo = "Cita para Asesoría en Investigación Cancelada"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted " \
                 f"canceló la cita agendada para el {mensajehorario} " \
                 f"con {responsable} para el servicio de <b>{citaasesoria.servicio.nombre}</b> por el siguiente motivo: {citaasesoria.observacion}"
        destinatario = citaasesoria.solicitante
        url = "/pro_asesoriainvestigacion"
        object_id = citaasesoria.id
        prioridad = 1


    notificar_push(titulo, cuerpo, destinatario, url, object_id, prioridad, app_label, request)


def notificar_gestion_dato(registro, tiponotificacion, request):
    # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
    # if tiponotificacion in ['REGSOL', 'REGSOLPRO', 'REASOL', 'REASOLPRO', 'CANSOL', 'CANSOLPRO']:
    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec
    # else:
    #     listacuentascorreo = [29]  # investigacion@unemi.edu.ec

    titulo = "Bases Institucionales para Artículos Científicos"
    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    # Obtener fecha en letras
    dialetras = dia_semana_enletras_fecha(registro.fechacita)
    fechadialetras = dialetras + " " + str(registro.fechacita.day) + " de " + MESES_CHOICES[registro.fechacita.month - 1][1].capitalize() + " del " + str(registro.fechacita.year)
    mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + registro.iniciocita.strftime('%H:%M') + " a " + registro.fincita.strftime('%H:%M') + "</b>"

    if tiponotificacion == 'REGSOL':
        asuntoemail = "Solicitud de Base Institucional para Artículos Científicos"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'

        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'REGSOLPRO':
        asuntoemail = "Solicitud de Base Institucional para Artículos Científicos"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = solicitante.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if solicitante.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'REASOL':
        asuntoemail = "Re-Agendamiento de Cita - Solicitud de Base Institucional para Artículos Científicos"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'REASOLPRO':
        asuntoemail = "Re-Agendamiento de Cita - Solicitud de Base Institucional para Artículos Científicos"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = solicitante.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if solicitante.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'CANSOL':
        asuntoemail = "Solicitud de Base Institucional para Artículos Científicos Cancelada"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'CANSOLPRO':
        asuntoemail = "Solicitud de Base Institucional para Artículos Científicos Cancelada"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion in ['VALSOL', 'NEGSOL']:
        asuntoemail = "Solicitud de Base Institucional para Artículos Científicos Validada" if tiponotificacion == 'VALSOL' else 'Solicitud de Base Institucional para Artículos Científicos Negada'
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion in ['VALSOLPRO', 'NEGSOLPRO']:
        asuntoemail = "Solicitud de Base Institucional para Artículos Científicos Validada" if tiponotificacion == 'VALSOL' else 'Solicitud de Base Institucional para Artículos Científicos Negada'
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'FIRACT':
        asuntoemail = "Acta de Reunión para Solicitud de Base Institucional Firmada y Enviada"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'

        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'FIRACTPRO':
        asuntoemail = "Acta de Reunión para Solicitud de Base Institucional Firmada y Enviada"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = solicitante.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if solicitante.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'FIRASEACT':
        asuntoemail = "Acta de Reunión para Solicitud de Base Institucional Firmada por Asesor"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'

        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'FIRASEACTPRO':
        asuntoemail = "Acta de Reunión para Solicitud de Base Institucional Firmada por Asesor"
        responsable = asistente_direccion_cee()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = solicitante.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if solicitante.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'FIRSOL':
        asuntoemail = "Acuerdo de Confidencialidad para Solicitud de Base Institucional Firmado y Enviado"
        responsable = vicerrector_investigacion_posgrado()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'

        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'FIRSOLPRO':
        asuntoemail = "Acuerdo de Confidencialidad para Solicitud de Base Institucional Firmado y Enviado"
        responsable = vicerrector_investigacion_posgrado()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'
        lista_email_envio = solicitante.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if solicitante.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'APRSOL':
        asuntoemail = "Solicitud de Base Institucional para Artículos Científicos Aprobada"
        responsable = vicerrector_investigacion_posgrado()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'

        lista_email_envio = responsable.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if responsable.sexo_id == 1 else 'Estimado'
    elif tiponotificacion == 'APRSOLPRO':
        asuntoemail = "Solicitud de Base Institucional para Artículos Científicos Aprobada"
        responsable = vicerrector_investigacion_posgrado()
        solicitante = registro.solicita
        saludosolicitante = 'la docente' if solicitante.sexo_id == 1 else 'el docente'

        lista_email_envio = solicitante.lista_emails_envio()
        # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
        saludo = 'Estimada' if solicitante.sexo_id == 1 else 'Estimado'

    # E-mail del destinatario
    lista_email_cco = ['isaltosm@unemi.edu.ec']
    lista_archivos_adjuntos = []

    send_html_mail(asuntoemail,
                   "emails/gestiondato.html",
                   {'sistema': u'SGA - UNEMI',
                    'titulo': titulo,
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'tiponotificacion': tiponotificacion,
                    'registro': registro,
                    'saludo': saludo,
                    'responsable': responsable.nombre_completo_inverso(),
                    'solicitante': solicitante.nombre_completo_inverso(),
                    'saludosolicitante': saludosolicitante,
                    'mensajehorario': mensajehorario
                    },
                   lista_email_envio,
                   lista_email_cco,
                   lista_archivos_adjuntos,
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )

    # Notificación Push
    app_label = "sga"
    if tiponotificacion == 'REGSOL':
        titulo = "Solicitud de Base Institucional para Artículos Científicos"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> {saludosolicitante} " \
                 f"<b>{solicitante}</b> registró una solicitud de Base institucional por lo cuál se agendó una cita de asesoramiento y validación para el {mensajehorario}."
        destinatario = asistente_direccion_cee()
        url = "/adm_gestiondato?action=solicitudes"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'REGSOLPRO':
        titulo = "Solicitud de Base Institucional para Artículos Científicos"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> " \
                 f"usted registró una solicitud de Base institucional para Artículos científicos y a su vez agendó con el <b>Centro de Estudios Estadísticos</b> una cita para el asesoramiento y validación para el {mensajehorario}."
        destinatario = registro.solicita
        url = "/pro_gestiondato"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'REASOL':
        titulo = "Re-Agendamiento de Cita para Solicitud de Base Institucional para Artículos Científicos"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> {saludosolicitante} " \
                 f"<b>{solicitante}</b> re-agendó una cita de asesoramiento y validación de una solicitud de Base institucional para el {mensajehorario}."
        destinatario = asistente_direccion_cee()
        url = "/adm_gestiondato?action=solicitudes"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'REASOLPRO':
        titulo = "Re-Agendamiento de Cita para Solicitud de Base Institucional para Artículos Científicos"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> " \
                 f"usted re-agendó con el <b>Centro de Estudios Estadísticos</b> una cita para el asesoramiento y validación de una solicitud de Base institucional para el {mensajehorario}."
        destinatario = registro.solicita
        url = "/pro_gestiondato"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'CANSOL':
        titulo = "Solicitud de Base Institucional para Artículos Científicos Cancelada"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> {saludosolicitante} " \
                 f"<b>{solicitante}</b> canceló la solicitud de Base institucional y cita agendada con el <b>Centro de Estudios Estadísticos</b> para el {mensajehorario} " \
                 f"por el siguiente motivo: {registro.observacion}"
        destinatario = asistente_direccion_cee()
        url = "/adm_gestiondato?action=solicitudes"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'CANSOLPRO':
        titulo = "Solicitud de Base Institucional para Artículos Científicos Cancelada"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted " \
                 f"canceló la solicitud de Base institucional y la cita agendada con el <b>Centro de Estudios Estadísticos</b> para el {mensajehorario} " \
                 f"por el siguiente motivo: {registro.observacion}"
        destinatario = registro.solicita
        url = "/pro_gestiondato"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion in ['VALSOL', 'NEGSOL']:
        if tiponotificacion == 'VALSOL':
            titulo = "Solicitud de Base Institucional para Artículos Científicos Validada"
            cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted asignó el estado <b>validado</b> a la solicitud de Base institucional {saludosolicitante} " \
                     f"<b>{solicitante}</b>."
        else:
            titulo = "Solicitud de Base Institucional para Artículos Científicos Negada"
            cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted asignó el estado <b>negado</b> a la solicitud de Base institucional {saludosolicitante} " \
                     f"<b>{solicitante}</b> por el siguiente motivo: {registro.observacion}."

        destinatario = asistente_direccion_cee()
        url = "/adm_gestiondato?action=solicitudes"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion in ['VALSOLPRO', 'NEGSOLPRO']:
        if tiponotificacion == 'VALSOLPRO':
            titulo = "Solicitud de Base Institucional para Artículos Científicos Validada"
            cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> se asignó el estado <b>validado</b> a su solicitud de Base institucional. " \
                     f"Usted deberá imprimir y firmar el acta de reunión, luego deberá imprimir y firmar el acuerdo de confidencialidad en el SGA para poder continuar con el proceso."
        else:
            titulo = "Solicitud de Base Institucional para Artículos Científicos Negada"
            cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> se asignó el estado <b>negado</b> a su solicitud de Base institucional " \
                     f"por el siguiente motivo: {registro.observacion}."

        destinatario = registro.solicita
        url = "/pro_gestiondato"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'FIRACT':
        titulo = "Acta de Reunión para Solicitud de Base Institucional Firmada y Enviada"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> {saludosolicitante} " \
                 f"<b>{solicitante}</b> firmó y envió el acta de reunión para la solicitud de Base institucional por lo que se le solicita estampar su firma como asesor."
        destinatario = asistente_direccion_cee()
        url = "/adm_gestiondato?action=solicitudes"
        object_id = registro.id
        prioridad = 3
    elif tiponotificacion == 'FIRACTPRO':
        titulo = "Acta de Reunión para Solicitud de Base Institucional Firmada y Enviada"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted " \
                 f"firmó y envió el acta de reunión para la solicitud de Base institucional."
        destinatario = registro.solicita
        url = "/pro_gestiondato"
        object_id = registro.id
        prioridad = 3
    elif tiponotificacion == 'FIRASEACT':
        titulo = "Acta de Reunión para Solicitud de Base Institucional Firmada por Asesor"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted firmó el acta de reunión " \
                 f"para la solicitud de Base institucional {saludosolicitante} <b>{solicitante}</b>."
        destinatario = asistente_direccion_cee()
        url = "/adm_gestiondato?action=solicitudes"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'FIRASEACTPRO':
        titulo = "Acta de Reunión para Solicitud de Base Institucional Firmada por Asesor"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> " \
                 f"el asesor firmó el acta de reunión para su solicitud de Base institucional por lo cual deberá imprimir y firmar el acuerdo de confidencialidad para posteriormente poder realizar la descarga del archivo solicitado en el SGA."
        destinatario = registro.solicita
        url = "/pro_gestiondato"
        object_id = registro.id
        prioridad = 1


    elif tiponotificacion == 'FIRSOL':
        titulo = "Acuerdo de Confidencialidad para Solicitud de Base Institucional Firmado"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> {saludosolicitante} " \
                 f"<b>{solicitante}</b> firmó y envió el acuerdo de confidencialidad para la solicitud de Base institucional por lo cuál se le solicita realizar la revisión y aprobación correspondiente."
        destinatario = vicerrector_investigacion_posgrado()
        url = "/adm_gestiondato?action=solicitudes"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'FIRSOLPRO':
        titulo = "Acuerdo de Confidencialidad para Solicitud de Base Institucional Firmado"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted " \
                 f"firmó y envió el acuerdo de confidencialidad para la solicitud de Base institucional por lo que deberá esperar a que se realice la revisión y aprobación correspondiente."
        destinatario = registro.solicita
        url = "/pro_gestiondato"
        object_id = registro.id
        prioridad = 1
    elif tiponotificacion == 'APRSOL':
        titulo = "Solicitud de Base Institucional para Artículos Científicos Aprobada"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> usted firmó el acuerdo de confidencialidad y <b>aprobó</b> " \
                 f"la solicitud de Base institucional {saludosolicitante} <b>{solicitante}</b>."
        destinatario = vicerrector_investigacion_posgrado()
        url = "/adm_gestiondato?action=solicitudes"
        object_id = registro.id
        prioridad = 3
    elif tiponotificacion == 'APRSOLPRO':
        titulo = "Solicitud de Base Institucional para Artículos Científicos Aprobada"
        cuerpo = f"Se le comunica que el <b>{fechaenvio.strftime('%d-%m-%Y')}</b> a las <b>{horaenvio.strftime('%H:%M')}</b> " \
                 f"se <b>aprobó</b> su solicitud de Base institucional por lo cual ya podrá realizar la descarga de los archivos en el SGA."
        destinatario = registro.solicita
        url = "/pro_gestiondato"
        object_id = registro.id
        prioridad = 3

    notificar_push(titulo, cuerpo, destinatario, url, object_id, prioridad, app_label, request)


def notificar_push(titulo, cuerpo, destinatario, url, object_id, prioridad, app_label, request):
    # Guardar la notificación
    notificacion = Notificacion(
        titulo=titulo,
        cuerpo=cuerpo,
        destinatario=destinatario,
        url=url,
        object_id=object_id,
        prioridad=prioridad,
        app_label=app_label,
        fecha_hora_visible=datetime.now() + timedelta(days=1),
    )
    notificacion.save(request)
