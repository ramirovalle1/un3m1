import json
import sys
import redis as Redis
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.horario import PeriodoAcademiaSerializer, PersonaSerializer, MatriculaSerializer, \
    MallaSerializer, NivelMallaSerializer, InscripcionSerializer, ClaseSerializer
from api.views.alumno.horario.functions import horario_alumno_presente_consulta, horario_alumno_pasado_consulta, \
    get_client_ip, enterClassEstudiante
from inno.models import LogIngresoAsistenciaLeccion
from matricula.models import PeriodoMatricula
from sagest.models import Rubro
from sga.clases_threading import ActualizaAsistencia
from sga.funciones import log, null_to_numeric, variable_valor
from sga.models import PerfilUsuario, Persona, Periodo, Reporte, Matricula, RecordAcademico, Clase, Turno, LeccionGrupo, \
    AsistenciaLeccion, MateriaAsignada, miinstitucion, CUENTAS_CORREOS, TIPOHORARIO_COLOURS
from settings import COBRA_COMISION_BANCO
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache
from settings import EMAIL_DOMAIN, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_BD


class HorarioAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_HORARIOS_CLASES'

    @api_security
    def post(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']

            if action == 'loadInit':
                try:
                    hoy = datetime.now().date()
                    horaactual = datetime.now().time()
                    numerosemanaactual = datetime.today().isocalendar()[1]
                    diaactual = hoy.isocalendar()[2]
                    aSemana = [
                                  {"numero": 1, "dia": 'Lunes', "activo": 1 == diaactual},
                                  {"numero": 2, "dia": 'Martes', "activo": 2 == diaactual},
                                  {"numero": 3, "dia": 'Miércoles', "activo": 3 == diaactual},
                                  {"numero": 4, "dia": 'Jueves', "activo": 4 == diaactual},
                                  {"numero": 5, "dia": 'Viernes', "activo": 5 == diaactual},
                                  {"numero": 6, "dia": 'Sábado', "activo": 6 == diaactual},
                                  {"numero": 7, "dia": 'Domingo', "activo": 7 == diaactual},
                        ]
                    payload = request.auth.payload
                    if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                        ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
                    else:
                        ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                        cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)

                    if cache.has_key(f"inscripcion_id_{encrypt(ePerfilUsuario.inscripcion_id)}"):
                        eInscripcion = cache.get(f"inscripcion_id_{encrypt(ePerfilUsuario.inscripcion_id)}")
                    else:
                        eInscripcion = ePerfilUsuario.inscripcion
                        cache.set(f"inscripcion_id_{encrypt(ePerfilUsuario.inscripcion_id)}", eInscripcion, TIEMPO_ENCACHE)

                    if cache.has_key(f"persona_id_{encrypt(eInscripcion.persona_id)}"):
                        ePersona = cache.get(f"persona_id_{encrypt(eInscripcion.persona_id)}")
                    else:
                        ePersona = eInscripcion.persona
                        cache.set(f"persona_id_{encrypt(eInscripcion.persona_id)}", ePersona, TIEMPO_ENCACHE)

                    eMalla = eInscripcion.mi_malla()
                    es_admision = eInscripcion.es_admision()
                    if not eMalla:
                        raise NameError(u"No tiene malla asignada.")
                    if 'id' not in payload['periodo']:
                        raise NameError(u"No se encontro periodo")
                    if payload['periodo']['id'] is None:
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}")

                    if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                        ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
                    else:
                        try:
                            ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                        except ObjectDoesNotExist:
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}")
                        cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)

                    ePeriodoAcademia = ePeriodo.get_periodoacademia()
                    ePeriodoMatricula = None
                    ePeriodoMatriculas = ePeriodo.periodomatricula_set.filter(status=True)
                    if ePeriodoMatriculas.values("id").exists():
                        ePeriodoMatricula = ePeriodoMatriculas[0]

                    eMatricula = eInscripcion.mi_matricula_periodo(ePeriodo.id)
                    if not eMatricula:
                        raise NameError(u"No tiene se encuentra matriculada.")
                    # eMateriasAsignadas = eMatricula.materiaasignada_set.filter(status=True)
                    if cache.has_key(f"clases_matricula_id_{encrypt(eMatricula.id)}_horario"):
                        eClases = cache.get(f"clases_matricula_id_{encrypt(eMatricula.id)}_horario")
                    else:
                        eClases = Clase.objects.db_manager("sga_select").filter(materia__nivel__periodo_id=ePeriodo.id, materia__materiaasignada__matricula_id=eMatricula.id, materia__materiaasignada__status=True)
                        # eTurnos = Turno.objects.db_manager("sga_select").filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct()
                        # if eTurnos.values("id").exists():
                        #     eTurnos_comienza = eTurnos.values_list("comienza", flat=True).filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct().order_by('comienza')[0]
                        #     eTurnos_termina = eTurnos.values_list("termina", flat=True).filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct().order_by('-termina')[0]
                        #     if datetime.now() < datetime.combine(datetime.now(), eTurnos_termina):
                        #         TIEMPO_ENCACHE = ((datetime.combine(datetime.now(), eTurnos_termina)) - (datetime.combine(datetime.now(), eTurnos_comienza))).total_seconds()
                        cache.set(f"clases_matricula_id_{encrypt(eMatricula.id)}_horario", eClases, TIEMPO_ENCACHE)
                    eClases_1 = eClases.filter(status=True, fin__gte=hoy, activo=True, materia__materiaasignada__matricula_id=eMatricula.id, materia__materiaasignada__retiramateria=False, materia__materiaasignada__status=True).distinct().order_by('inicio')
                    eClases_2 = eClases.filter(status=True, fin__lt=hoy, activo=True, materia__materiaasignada__matricula_id=eMatricula.id, materia__materiaasignada__retiramateria=False, materia__materiaasignada__status=True).distinct().order_by('inicio')
                    eTurnos = Turno.objects.db_manager("sga_select").values("comienza", "termina", "horas").filter(pk__in=eClases_1.values_list("turno_id", flat=True).distinct() | eClases_2.values_list("turno_id", flat=True).distinct()).distinct().order_by('comienza')
                    aTurnos = []
                    contadorActuales = 0
                    contadorPasadas = 0
                    aTipoHorarioClasesActuales = []
                    aTipoHorarioClasesPasadas = []
                    for eTurno in eTurnos:
                        comienza = eTurno.get("comienza")
                        termina = eTurno.get("termina")
                        horas = eTurno.get("horas")
                        aSemanaTurnoActuales = []
                        aSemanaTurnoPasadas = []
                        for semana in aSemana:
                            aClasesActuales = []
                            for eClase in horario_alumno_presente_consulta(comienza, termina, hoy, semana.get("numero"), eMatricula, ePeriodo.id):
                                if eClase.id == 244397 and semana.get("numero")==3:
                                    print("236435")
                                if not eClase.tipohorario in [x[0] for x in aTipoHorarioClasesActuales]:
                                    for num in TIPOHORARIO_COLOURS:
                                        if num[0] == eClase.tipohorario:
                                            aTipoHorarioClasesActuales.append(num)
                                contadorActuales += 1
                                grupoprofesor = None
                                style_card = f"background-color: {eClase.get_display_background_tipohorario_colours()} !important; color: {eClase.get_display_color_text_tipohorario_colours()} !important;"
                                disponible = eClase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia)
                                disponible_hora = eClase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                                if eClase.tipoprofesor and eClase.grupoprofesor and eClase.tipoprofesor.id in [2, 13] and eClase.grupoprofesor.paralelopractica:
                                    grupoprofesor = eClase.grupoprofesor.get_paralelopractica_display()
                                action_button = {}
                                # 1 => PRESENCIAL
                                # 2 => CLASE VIRTUAL SINCRÓNICA
                                # 7 => CLASE VIRTUAL ASINCRÓNICA
                                # 8 => CLASE REFUERZO SINCRÓNICA
                                # 9 => CLASE REFUERZO ASINCRÓNICA
                                if eClase.tipohorario in [1]:
                                    if not ePeriodoAcademia.valida_asistencia_in_home:
                                        if eClase.dia == diaactual and hoy >= eClase.inicio and hoy <= eClase.fin:
                                            if disponible_hora:
                                                url = None
                                                style = None
                                                style_class = u"btn-warning text-white"
                                                if eClase.profesor:
                                                    if eClase.materia.tieneurlwebex(eClase.profesor):
                                                        url = f"https://unemi.webex.com/meet/{eClase.profesor.persona.usuario}"
                                                        style = u"background-color: #2d8cff !important;"
                                                        style_class = u"btn-primary text-white"
                                                    elif eClase.profesor.urlzoom:
                                                        url = eClase.profesor.urlzoom
                                                        style = u"background-color: #2d8cff !important;"
                                                        style_class = u"btn-primary text-white"
                                                action_button = {"action": "go_class",
                                                                 "url": url,
                                                                 "wait": True,
                                                                 "disponible": disponible,
                                                                 "verbose": u"Entrar a clase" if disponible else u"Ir a clase",
                                                                 "icon": u"camera-video-fill",
                                                                 "style": style if disponible else u"background-color: #F46839 !important;",
                                                                 "style_class": style_class,
                                                                 "key": f'{encrypt(eClase.id)}{encrypt(eClase.turno.id)}{encrypt(ePersona.usuario.id)}{encrypt(semana.get("numero"))}{hoy.strftime("%d%m%Y")}',
                                                                 "key_room": f'{eClase.turno.id}{eClase.profesor.id}{semana.get("numero")}{hoy.strftime("%d%m%Y")}' if ePeriodoAcademia.utiliza_asistencia_ws else ""}
                                elif eClase.tipohorario in [2, 8, 7, 9]:
                                    if eClase.tipohorario in [2, 8]:
                                        if eClase.dia == diaactual and hoy >= eClase.inicio and hoy <= eClase.fin:
                                            if disponible_hora:
                                                url = None
                                                style = None
                                                style_class = u"btn-warning text-white"
                                                if eClase.profesor:
                                                    if eClase.materia.tieneurlwebex(eClase.profesor):
                                                        url = f"https://unemi.webex.com/meet/{eClase.profesor.persona.usuario}"
                                                        style = u"background-color: #2d8cff !important;"
                                                        style_class = u"btn-primary text-white"
                                                    elif eClase.profesor.urlzoom:
                                                        url = eClase.profesor.urlzoom
                                                        style = u"background-color: #2d8cff !important;"
                                                        style_class = u"btn-primary text-white"
                                                action_button = {"action": "go_class",
                                                                 "url": url,
                                                                 "wait": True,
                                                                 "disponible": disponible,
                                                                 "verbose": u"Entrar a clase" if disponible else u"Ir a clase",
                                                                 "icon": u"camera-video-fill",
                                                                 "style": style if disponible else u"background-color: #F46839 !important;",
                                                                 "style_class": style_class,
                                                                 "key": f'{encrypt(eClase.id)}{encrypt(eClase.turno.id)}{encrypt(ePersona.usuario.id)}{encrypt(semana.get("numero"))}{hoy.strftime("%d%m%Y")}' if ePeriodoAcademia.utiliza_asistencia_redis else '',
                                                                 "key_room": f'{eClase.turno.id}{eClase.profesor.id}{semana.get("numero")}{hoy.strftime("%d%m%Y")}' if ePeriodoAcademia.utiliza_asistencia_ws else ""}
                                    elif eClase.tipohorario in [7, 9]:
                                        eCoordinacion = eClase.materia.coordinacion()
                                        eModalidad = eClase.materia.asignaturamalla.malla.modalidad
                                        clasesactualesasincronica = eClase.horario_profesor_actualasincronica(numerosemanaactual)
                                        url = None
                                        wait = False
                                        action = "go_class"
                                        verbose = u"Ir a la clase"
                                        key = ""
                                        key_room = ""
                                        style = f"background-color: #603D4D !important;"
                                        style_class = u"btn-primary text-white"
                                        if eCoordinacion.id in [1, 2, 3, 4, 5, 12]:
                                            if eModalidad:
                                                if eModalidad.id in [1, 2]:
                                                    if eClase.dia == diaactual and hoy >= eClase.inicio and hoy <= eClase.fin and clasesactualesasincronica.values("id").exists():
                                                        url = f"https://aulagradoa.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                        action_button = {
                                                            "action": action,
                                                            "url": url,
                                                            "wait": wait,
                                                            "disponible": False,
                                                            "verbose": verbose,
                                                            "icon": u"box-arrow-right",
                                                            "style": style,
                                                            "style_class": style_class,
                                                            "key": key,
                                                            "key_room": key_room
                                                            }
                                                elif eModalidad.id in [3]:
                                                    if not eClase.materia.nivel.periodo.es_feriado(datetime.now(), eClase.materia):
                                                        if semana.get("numero") >= diaactual and hoy >= eClase.inicio and hoy <= eClase.fin and eClase.dia >= semana.get("numero") and eClase.turno.comienza >= comienza:
                                                            url = None
                                                            if clasesactualesasincronica.values("id").exists():
                                                                url = f"https://aulagradob.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                            wait = True
                                                            action = "go_class_asincronica"
                                                            verbose = u"Ir a la clase"
                                                            action_button = {
                                                                "action": action,
                                                                "url": url,
                                                                "wait": wait,
                                                                "disponible": False,
                                                                "verbose": verbose,
                                                                "icon": u"box-arrow-right",
                                                                "style": style,
                                                                "style_class": style_class,
                                                                "key": key,
                                                                "key_room": key_room
                                                                }
                                        elif eCoordinacion.id in [9]:
                                            if eClase.dia == diaactual and hoy >= eClase.inicio and hoy <= eClase.fin and clasesactualesasincronica.values("id").exists():
                                                url = f"https://aulanivelacion.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                action_button = {
                                                    "action": action,
                                                    "url": url,
                                                    "wait": wait,
                                                    "disponible": False,
                                                    "verbose": "Ir a la clase",
                                                    "icon": u"box-arrow-right",
                                                    "style": style,
                                                    "style_class": style_class,
                                                    "key": key,
                                                    "key_room": key_room
                                                    }
                                        elif eCoordinacion.id in [7, 10]:
                                            if eClase.dia == diaactual and hoy >= eClase.inicio and hoy <= eClase.fin and clasesactualesasincronica.values("id").exists():
                                                url = f"https://posgrado.unemi.edu.ec/mod/forum/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                action_button = {
                                                    "action": action,
                                                    "url": url,
                                                    "wait": wait,
                                                    "disponible": False,
                                                    "verbose": "Ir a la clase",
                                                    "icon": u"box-arrow-right",
                                                    "style": style,
                                                    "style_class": style_class,
                                                    "key": key,
                                                    "key_room": key_room
                                                    }
                                eProfesor = None
                                if ePeriodoMatricula and ePeriodoMatricula.ver_profesor_materia:
                                    if eClase.profesor:
                                        eProfesor = eClase.profesor
                                aClasesActuales.append({"id": eClase.id,
                                                        "asignatura": eClase.materia.asignatura.nombre,
                                                        "nivelmalla": eClase.materia.asignaturamalla.nivelmalla.__str__(),
                                                        "paralelo": eClase.materia.paralelo,
                                                        "alias": eClase.materia.asignaturamalla.malla.carrera.alias,
                                                        "aula": eClase.aula.nombre,
                                                        "sede": eClase.aula.sede.nombre,
                                                        "inicio": eClase.inicio.strftime("%d-%m-%Y"),
                                                        "fin": eClase.fin.strftime("%d-%m-%Y"),
                                                        "tipoprofesor_id": eClase.tipoprofesor.id if eClase.tipoprofesor else None,
                                                        "tipoprofesor": eClase.tipoprofesor.__str__() if eClase.tipoprofesor else None,
                                                        "profesor": eProfesor.__str__() if eProfesor else None,
                                                        "profesor_sexo_id": eClase.profesor.persona.sexo.id if eClase.profesor and eClase.profesor.persona.sexo else 2,
                                                        "tipohorario": eClase.tipohorario,
                                                        "tipohorario_display": eClase.get_tipohorario_display(),
                                                        "grupoprofesor": grupoprofesor,
                                                        "style_card": style_card,
                                                        "action_button": action_button})
                            aSemanaTurnoActuales.append({"dia": semana.get("numero"), "aClases": aClasesActuales})
                            aClasesPasadas = []
                            for eClase in horario_alumno_pasado_consulta(comienza, termina, hoy, semana.get("numero"), eMatricula, ePeriodo.id):
                                if not eClase.tipohorario in [x[0] for x in aTipoHorarioClasesPasadas]:
                                    for num in TIPOHORARIO_COLOURS:
                                        if num[0] == eClase.tipohorario:
                                            aTipoHorarioClasesPasadas.append(num)
                                contadorPasadas += 1
                                style_card = f"background-color: {eClase.get_display_background_tipohorario_colours()} !important; color: {eClase.get_display_color_text_tipohorario_colours()} !important;"
                                disponible_hora = eClase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                                grupoprofesor = None
                                if eClase.tipoprofesor and eClase.grupoprofesor and eClase.tipoprofesor == 2 and eClase.dia == diaactual and disponible_hora and eClase.grupoprofesor.paralelopractica:
                                    grupoprofesor = eClase.grupoprofesor.get_paralelopractica_display()
                                eProfesor = None
                                if ePeriodoMatricula and ePeriodoMatricula.ver_profesor_materia:
                                    if eClase.profesor:
                                        eProfesor = eClase.profesor
                                aClasesPasadas.append({"id": eClase.id,
                                                       "asignatura": eClase.materia.asignatura.nombre,
                                                       "nivelmalla": eClase.materia.asignaturamalla.nivelmalla.__str__(),
                                                       "paralelo": eClase.materia.paralelo,
                                                       "alias": eClase.materia.asignaturamalla.malla.carrera.alias,
                                                       "aula": eClase.aula.nombre,
                                                       "sede": eClase.aula.sede.nombre,
                                                       "inicio": eClase.inicio.strftime("%d-%m-%Y"),
                                                       "fin": eClase.fin.strftime("%d-%m-%Y"),
                                                       "tipoprofesor": eClase.tipoprofesor.__str__() if eClase.tipoprofesor else None,
                                                       "profesor": eProfesor.__str__() if eProfesor else None,
                                                       "tipohorario": eClase.tipohorario,
                                                       "tipohorario_display": eClase.get_tipohorario_display(),
                                                       "style_card": style_card,
                                                       "grupoprofesor": grupoprofesor})
                            aSemanaTurnoPasadas.append({"dia": semana.get("numero"), "aClases": aClasesPasadas})
                        aTurnos.append({"comienza": comienza,
                                        "termina": termina,
                                        "horas": horas,
                                        "activo": comienza <= horaactual <= termina,
                                        "aSemanaTurnoActuales": aSemanaTurnoActuales,
                                        "aSemanaTurnoPasadas": aSemanaTurnoPasadas})
                    aData = {"aSemana": aSemana,
                             "isClasesActuales": contadorActuales > 0,
                             "isClasesPasadas": contadorPasadas > 0,
                             "aTurnos": aTurnos,
                             "aTipoHorarioClasesActuales": aTipoHorarioClasesActuales,
                             "aTipoHorarioClasesPasadas": aTipoHorarioClasesPasadas,
                             "eMalla":eMalla.modalidad_id,
                             "es_admision":es_admision,
                             'admision_visualiza_materias': variable_valor('ADMISION_VISUALIZA_MATERIAS'),

                             "VER_BOTON_VER_CLASE_EN_LINEA":variable_valor('VER_BOTON_VER_CLASE_EN_LINEA')}
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'enterClassEstudiante':
                try:
                    isSuccess = False
                    data = {}
                    isSuccess, data = enterClassEstudiante(request)
                    if isSuccess is False:
                        message = data.get('message', None)
                        if message:
                            raise NameError(message)
                    return Helper_Response(isSuccess=isSuccess, data=data, status=status.HTTP_200_OK)
                except Exception as ex:
                    print('Error en la funcion enterClassEstudiante: {}'.format(sys.exc_info()[-1].tb_lineno))
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'enterClassAsincroncaEstudiante':
                with transaction.atomic():
                    try:
                        import calendar
                        hoy = datetime.now().date()
                        horaactual = datetime.now().time()
                        numerosemanaactual = datetime.today().isocalendar()[1]
                        diaactual = hoy.isocalendar()[2]
                        payload = request.auth.payload
                        if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                            ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
                        else:
                            ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                            cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
                        if not ePerfilUsuario.es_estudiante():
                            NameError(u"Solo los perfiles de estudiantes pueden ingresar al modulo.")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = eInscripcion.persona
                        if 'id' not in payload['periodo']:
                            raise NameError(u"No se encontro periodo")
                        if payload['periodo']['id'] is None:
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}")

                        if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                            ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
                        else:
                            try:
                                ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                            except ObjectDoesNotExist:
                                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}")
                            cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
                        eMatricula = eInscripcion.mi_matricula_periodo(ePeriodo.id)
                        if not 'idc' in request.data:
                            raise NameError(u"Clase no encontrada")
                        if not 'navegador' in request.data:
                            raise NameError(u"Navegador no identificado")
                        if not 'os' in request.data:
                            raise NameError(u"Sistema Operativo no identificado")
                        if not 'screensize' in request.data:
                            raise NameError(u"Tamaño de la pantalla no identificado")
                        navegador = request.data['navegador']
                        ops = request.data['os']
                        screen_size = request.data['screensize']
                        ip_public = get_client_ip(request)
                        # if not Clase.objects.db_manager("sga_select").values("id").filter(pk=int(request.data['idc'])).exists():
                        #     raise NameError(u"Clase no encontrada")
                        # eClase = Clase.objects.filter(pk=request.data['idc'])[0]
                        try:
                            eClase = Clase.objects.get(pk=request.data['idc'])
                        except ObjectDoesNotExist:
                            raise NameError(u"Clase no encontrada")
                        clasesactualesasincronica = eClase.horario_profesor_actualasincronica(numerosemanaactual)
                        if not clasesactualesasincronica.values("id").exists():
                            raise NameError(f"{'La profesora' if eClase.profesor.persona.es_mujer() else 'El profesor'} {eClase.profesor.persona.__str__()} no creado la clase, vuelva a intertarlo más tarde")
                        calendario = calendar.Calendar()
                        dia = eClase.dia
                        fecha = None
                        for semanas in calendario.monthdatescalendar(hoy.year, hoy.month):
                            for f in semanas:
                                if f.isocalendar()[1] == numerosemanaactual:
                                    if f.isocalendar()[2] == dia:
                                        fecha = f
                        eLeccionGrupos = LeccionGrupo.objects.filter(status=True, fecha=fecha, lecciones__clase=eClase, lecciones__fecha=fecha, turno=eClase.turno, dia=eClase.dia, profesor_id=eClase.profesor.id).order_by('-fecha', '-horaentrada')
                        if not eLeccionGrupos.values("id").exists():
                            raise NameError(f"{'La profesora' if eClase.profesor.persona.es_mujer() else 'El profesor'} {eClase.profesor.persona.__str__()} no creado la clase lección, vuelva a intertarlo más tarde")
                        if eLeccionGrupos.values("id").exists():
                            if eLeccionGrupos[0].mis_leciones().values('id').filter(clase=eClase).exists():
                                leccion = eLeccionGrupos[0].mis_leciones().filter(clase=eClase)[0]
                                eMateriaAsignada = eMatricula.materiaasignada_set.filter(materia=eClase.materia)[0]
                                eAsistenciaLecciones = AsistenciaLeccion.objects.filter(leccion=leccion, materiaasignada=eMateriaAsignada)
                                if eAsistenciaLecciones.values("id").exists():
                                    eAsistencia = eAsistenciaLecciones[0]
                                    eAsistenciaLecciones.update(asistio=True,
                                                                virtual=True,
                                                                virtual_fecha=hoy,
                                                                virtual_hora=horaactual,
                                                                ip_public=ip_public,
                                                                browser=navegador,
                                                                ops=ops,
                                                                screen_size=screen_size,
                                                                usuario_modificacion_id=request.user.id,
                                                                fecha_modificacion=hoy
                                                                )
                                    if variable_valor('ACTUALIZA_ASISTENCIA'):
                                        if not eMateriaAsignada.sinasistencia:
                                            ActualizaAsistencia(eMateriaAsignada.id)
                                    log(u'Adiciono asistencia en la clase: %s. Durante el tiempo establecido' % eClase, request, "add")
                                    logingreso = LogIngresoAsistenciaLeccion(asistencia=eAsistencia,
                                                                             fecha=datetime.now().date(),
                                                                             hora=datetime.now().time(),
                                                                             ip_private=None,
                                                                             ip_public=ip_public,
                                                                             browser=navegador,
                                                                             ops=ops,
                                                                             screen_size=screen_size
                                                                             )
                                    logingreso.save(request)
                                    log(u'Dio click en el botón en horario para ingresar en la clase: %s' % logingreso, request, "add")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'seeClassroomLocation':
                try:
                    if not 'idc' in request.data:
                        raise NameError(u"Clase no encontrada")
                    idc = int(request.data['idc'])
                    if not Clase.objects.values("id").filter(pk=idc).exists():
                        raise NameError(u"Clase no encontrada")
                    eClase = ClaseSerializer(Clase.objects.get(pk=idc)).data
                    return Helper_Response(isSuccess=True, data={'eClase': eClase}, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            aData = {}
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)

            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            eMalla = eInscripcion.mi_malla()
            if not eMalla:
                raise NameError(u"No tiene malla asignada.")

            if 'id' not in payload['periodo']:
                raise NameError(u"No se encontro periodo")
            if payload['periodo']['id'] is None:
                return Helper_Response(isSuccess=False, data={},
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}",
                                       status=status.HTTP_200_OK, module_access=False)

            if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
            else:
                try:
                    ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                except ObjectDoesNotExist:
                    return Helper_Response(isSuccess=False, data={}, message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}", status=status.HTTP_200_OK, module_access=False)
                cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)

            eMatricula = eInscripcion.mi_matricula_periodo(ePeriodo.id)
            # automatricula de pregrado
            confirmar_automatricula_pregrado = eInscripcion.tiene_automatriculapregrado_por_confirmar(ePeriodo)
            if confirmar_automatricula_pregrado:
                if eMatricula.nivel.fechainicioagregacion > datetime.now().date():
                    return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de aceptación de matrícula empieza {eMatricula.nivel.fechainicioagregacion.__str__()}",
                                           status=status.HTTP_200_OK)
                if eMatricula.nivel.fechafinagregacion < datetime.now().date():
                    return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado",
                                           status=status.HTTP_200_OK)
                if PeriodoMatricula.objects.values("id").filter(periodo=ePeriodo, status=True).exists():
                    ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=ePeriodo, status=True).first()
                    if not ePeriodoMatricula.activo:
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de matrícula se encuentra inactivo",
                                               status=status.HTTP_200_OK)
                return Helper_Response(isSuccess=False, redirect="alu_matricula", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de matrícula se encuentra activo debe aceptar la automatricula",
                                       status=status.HTTP_200_OK)

            # automatricula de admisión
            confirmar_automatricula_admision = eInscripcion.tiene_automatriculaadmision_por_confirmar(ePeriodo)
            if confirmar_automatricula_admision:
                if eMatricula.nivel.fechainicioagregacion > datetime.now().date():
                    return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de aceptación de matrícula empieza {eMatricula.nivel.fechainicioagregacion.__str__()}",
                                           status=status.HTTP_200_OK)
                if eMatricula.nivel.fechafinagregacion < datetime.now().date():
                    return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado",
                                           status=status.HTTP_200_OK)
                if PeriodoMatricula.objects.values("id").filter(periodo=ePeriodo, status=True).exists():
                    ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=ePeriodo, status=True).first()
                    if not ePeriodoMatricula.activo:
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de matrícula se encuentra inactivo",
                                               status=status.HTTP_200_OK)
                return Helper_Response(isSuccess=False, redirect="alu_matricula", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de matrícula se encuentra activo debe aceptar la automatricula",
                                       status=status.HTTP_200_OK)
            # ePeriodoAcademia = ePeriodo.get_periodoacademia()
            if cache.has_key(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_horario"):
                eMalla_s = cache.get(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_horario")
            else:
                eMalla = eInscripcion.mi_malla()
                if not eMalla:
                    raise NameError(u"Malla no identificada")
                eMalla_s = MallaSerializer(eMalla).data
                cache.set(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_horario", eMalla_s, TIEMPO_ENCACHE)
            if cache.has_key(f"inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_horario"):
                eInscripcion_s = cache.get(f"inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_horario")
            else:
                eInscripcion_s = InscripcionSerializer(eInscripcion).data
                cache.set(f"inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_horario", eInscripcion_s, TIEMPO_ENCACHE)
            # eMatricula_data = None
            # if eMatricula:
            #     eMatricula_data = MatriculaSerializer(eMatricula).data
            # ePeriodoAcademia_data = PeriodoAcademiaSerializer(ePeriodoAcademia).data
            # eNivelMalla_data = NivelMallaSerializer(eInscripcion.mi_nivel().nivel).data
            aData = {
                'Title': "Mi horario de clases",
                'eInscripcion': eInscripcion_s,
                'eMalla': eMalla_s,
                # 'eMatricula': eMatricula_data,
                # 'ePeriodoAcademia': ePeriodoAcademia_data,
                # 'eNivelMalla': eNivelMalla_data
            }
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)



