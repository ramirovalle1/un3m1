# -*- coding: latin-1 -*-
import sys
import time
from datetime import datetime
from api.helpers.response_herlper import Helper_Response
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.core.cache import cache
from django_q.tasks import async_task
from inno.models import LogIngresoAsistenciaLeccion
from sga.clases_threading import ActualizaAsistencia
from sga.funciones import log, variable_valor, null_to_numeric
from sga.models import Clase, MateriaAsignada, AlumnosPracticaMateria, Turno, PerfilUsuario, Periodo, LeccionGrupo, \
    AsistenciaLeccion, miinstitucion, CUENTAS_CORREOS, Leccion
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django_q.conf import logger


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def horario_alumno_presente_consulta(comienza, termina, fecha, dia, matricula, idperiodo):
    ahora = datetime.now()
    fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
    tiempo_cache = fecha_fin - ahora
    TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
    if cache.has_key(f"clases_matricula_id_{encrypt(matricula.id)}_horario"):
        eClases = cache.get(f"clases_matricula_id_{encrypt(matricula.id)}_horario")
    else:
        eClases = Clase.objects.db_manager("sga_select").filter(materia__nivel__periodo_id=idperiodo, materia__materiaasignada__matricula_id=matricula.id, materia__materiaasignada__status=True)
        # eTurnos = Turno.objects.db_manager("sga_select").filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct()
        # TIEMPO_ENCACHE = 7200
        # if eTurnos.values("id").exists():
        #     eTurnos_comienza = eTurnos.values_list("comienza", flat=True).filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct().order_by('comienza')[0]
        #     eTurnos_termina = eTurnos.values_list("termina", flat=True).filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct().order_by('-termina')[0]
        #     if datetime.now() < datetime.combine(datetime.now(), eTurnos_termina):
        #         TIEMPO_ENCACHE = ((datetime.combine(datetime.now(), eTurnos_termina)) - (datetime.combine(datetime.now(), eTurnos_comienza))).total_seconds()
        cache.set(f"clases_matricula_id_{encrypt(matricula.id)}_horario", eClases, TIEMPO_ENCACHE)
    clasessinpracticas = eClases.values_list('id').filter(turno__comienza=comienza, turno__termina=termina,
                                                          fin__gte=fecha, dia=dia, activo=True, status=True,
                                                          materia__status=True,
                                                          materia__materiaasignada__retiramateria=False,
                                                          materia__materiaasignada__status=True,
                                                          materia__materiaasignada__matricula=matricula,
                                                          materia__nivel__periodo_id=idperiodo).exclude(tipoprofesor_id__in=[2, 13]).distinct()
    materiasasignadas = MateriaAsignada.objects.db_manager("sga_select").filter(status=True, retiramateria=False,
                                                                                matricula_id=matricula.id,
                                                                                materia__clase__tipoprofesor_id__in=[2, 13],
                                                                                materia__clase__dia=dia,
                                                                                materia__clase__fin__gte=fecha,
                                                                                materia__clase__turno__comienza=comienza,
                                                                                materia__clase__turno__termina=termina)
    if materiasasignadas.values("id").exists():
        profesorespracticascongrupo = []
        for materiaasignada in materiasasignadas:
            if materiaasignada.alumnopracticamateria():
                if materiaasignada.alumnopracticamateria().grupoprofesor:
                    profesorespracticascongrupo.append(materiaasignada.alumnopracticamateria().grupoprofesor.id)

        clasespracticascongrupo = eClases.values_list('id').filter(turno__comienza=comienza, turno__termina=termina,
                                                                   fin__gte=fecha, dia=dia, activo=True, status=True,
                                                                   materia__status=True, tipoprofesor__in=[2, 13],
                                                                   grupoprofesor_id__in=profesorespracticascongrupo,
                                                                   materia__materiaasignada__retiramateria=False,
                                                                   materia__materiaasignada__status=True,
                                                                   materia__materiaasignada__matricula=matricula,
                                                                   materia__nivel__periodo_id=idperiodo).distinct()
        ids_c = clasessinpracticas | clasespracticascongrupo
        return eClases.filter(pk__in=ids_c).distinct().order_by('inicio')
    return eClases.filter(pk__in=clasessinpracticas).distinct().order_by('inicio')


def horario_alumno_pasado_consulta(comienza, termina, fecha, dia, matricula, idperiodo):
    ahora = datetime.now()
    fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
    tiempo_cache = fecha_fin - ahora
    TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
    if cache.has_key(f"clases_matricula_id_{encrypt(matricula.id)}_horario"):
        eClases = cache.get(f"clases_matricula_id_{encrypt(matricula.id)}_horario")
    else:
        eClases = Clase.objects.db_manager("sga_select").filter(materia__nivel__periodo_id=idperiodo, materia__materiaasignada__matricula_id=matricula.id)
        # eTurnos = Turno.objects.db_manager("sga_select").filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct()
        # TIEMPO_ENCACHE = 7200
        # if eTurnos.values("id").exists():
        #     eTurnos_comienza = eTurnos.values_list("comienza", flat=True).filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct().order_by('comienza')[0]
        #     eTurnos_termina = eTurnos.values_list("termina", flat=True).filter(pk__in=eClases.values_list("turno_id", flat=True).distinct()).distinct().order_by('-termina')[0]
        #     if datetime.now() < datetime.combine(datetime.now(), eTurnos_termina):
        #         TIEMPO_ENCACHE = ((datetime.combine(datetime.now(), eTurnos_termina)) - (datetime.combine(datetime.now(), eTurnos_comienza))).total_seconds()
        cache.set(f"clases_matricula_id_{encrypt(matricula.id)}_horario", eClases, TIEMPO_ENCACHE)
    clasessinpracticas = eClases.values_list('id').filter(turno__comienza=comienza, turno__termina=termina,
                                                          fin__lt=fecha, dia=dia, activo=True, status=True,
                                                          materia__status=True,
                                                          materia__materiaasignada__retiramateria=False,
                                                          materia__materiaasignada__status=True,
                                                          materia__materiaasignada__matricula=matricula,
                                                          materia__nivel__periodo_id=idperiodo).distinct()
    profesorespracticascongrupo = AlumnosPracticaMateria.objects.db_manager("sga_select").values_list('grupoprofesor__id').filter(materiaasignada__matricula_id=matricula.id, materiaasignada__retiramateria=False, status=True, grupoprofesor__isnull=False)
    clasespracticascongrupo = eClases.values_list('id').filter(turno__comienza=comienza, turno__termina=termina,
                                                               fin__lt=fecha, dia=dia, activo=True, status=True,
                                                               materia__status=True, tipoprofesor__in=[2, 13],
                                                               grupoprofesor_id__in=profesorespracticascongrupo,
                                                               materia__materiaasignada__retiramateria=False,
                                                               materia__materiaasignada__status=True,
                                                               materia__materiaasignada__matricula_id=matricula.id,
                                                               materia__nivel__periodo_id=idperiodo).distinct()
    return eClases.filter(Q(id__in=clasessinpracticas) | Q(id__in=clasespracticascongrupo)).distinct().order_by('inicio')


def enterClassEstudiante_old(request):
    ahora = datetime.now()
    fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
    tiempo_cache = fecha_fin - ahora
    TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
    with transaction.atomic():
        try:
            hoy = datetime.now().date()
            horaactual = datetime.now().time()
            numerosemanaactual = datetime.today().isocalendar()[1]
            diaactual = hoy.isocalendar()[2]
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(
                    pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
            if not ePerfilUsuario.es_estudiante():
                NameError(u"Solo los perfiles de estudiantes pueden ingresar al modulo.")
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            if 'id' not in payload['periodo']:
                raise NameError(u"No se encontro periodo")
            if payload['periodo']['id'] is None:
                raise NameError(
                    f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}")

            if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
            else:
                try:
                    ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                except ObjectDoesNotExist:
                    raise NameError(
                        f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}")
                cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            ePeriodoAcademia = ePeriodo.get_periodoacademia()
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
            mensaje = None
            label_color = None
            mensaje = None
            label_color = None
            isWait = True
            isRedis = False
            data_redis = None
            clasesabiertas = LeccionGrupo.objects.none()
            if ePeriodoAcademia:
                if ePeriodoAcademia.utiliza_asistencia_redis:
                    isRedis = True
                    key = request.data.get('key', None)
                    if key is None:
                        raise NameError(u"Token de acceso no encontrado")
                    token = request.data['key']
                    if cache.has_key(token):
                        data_redis = cache.get(token)
                    else:
                        return Helper_Response(isSuccess=True, data={"isWait": isWait, "datos": {}, "mensaje": mensaje, "label_color": label_color}, status=status.HTTP_200_OK)

            try:
                eClase = Clase.objects.get(pk=request.data['idc'])
            except ObjectDoesNotExist:
                raise NameError(u"Clase no encontrada")
            if isRedis:
                if data_redis:
                    leccion_grupo_id = data_redis.get('leccion_grupo_id', 0)
                    clasesabiertas = LeccionGrupo.objects.filter(pk=leccion_grupo_id, abierta=True).order_by('-fecha', '-horaentrada')
            else:
                clasesabiertas = LeccionGrupo.objects.filter(status=True, fecha=hoy, turno=eClase.turno, dia=eClase.dia,
                                                             profesor_id=eClase.profesor.id, abierta=True).order_by(
                    '-fecha', '-horaentrada')

            if clasesabiertas.values("id").exists():
                if clasesabiertas[0].mis_leciones().values('id').filter(clase=eClase).exists():
                    leccion = clasesabiertas[0].mis_leciones().filter(clase=eClase)[0]
                    eMatricula = eInscripcion.mi_matricula_periodo(ePeriodo.id)
                    eMateriaAsignada = eMatricula.materiaasignada_set.get(materia=eClase.materia)
                    eAsistenciaLecciones = AsistenciaLeccion.objects.filter(leccion_id=leccion.id,
                                                                            materiaasignada_id=eMateriaAsignada.id)
                    disponible = eClase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia)
                    disponible_hora = eClase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                    if not eAsistenciaLecciones.values("id").exists():
                        if eMateriaAsignada.matricula.estado_matricula == 1:
                            log(u'Dio click en el botón en horario para ingresar en la clase: %s, pero no se registra asistencia por deuda' % eClase,
                                request, "add")
                            mensaje = u"Su asistencia no ha sido registrada por deuda pendiente. Revisar modulo de <a href='/alu_finanzas' target='_blank'>Mis Finanzas</a>"
                            return Helper_Response(isSuccess=True,
                                                   data={"isWait": False, "mensaje": mensaje, "label_color": "warning"},
                                                   status=status.HTTP_200_OK)
                        else:
                            if eClase.tipoprofesor.id == 2 and eClase.tipohorario in [1, 2, 8]:
                                if eClase.grupoprofesor:
                                    if eClase.grupoprofesor.paralelopractica:
                                        # grupoprofesor_id = clase.grupoprofesor.id
                                        if eClase.grupoprofesor.listado_inscritos_grupos_practicas().exists():
                                            listado_alumnos_practica = eClase.grupoprofesor.listado_inscritos_grupos_practicas()
                                            if ePeriodoAcademia.valida_asistencia_pago:
                                                asignados = MateriaAsignada.objects.filter(
                                                    pk__in=listado_alumnos_practica.values_list('materiaasignada_id',
                                                                                                flat=True).distinct(),
                                                    matricula__estado_matricula__in=[2, 3])
                                            else:
                                                asignados = MateriaAsignada.objects.filter(
                                                    pk__in=listado_alumnos_practica.values_list('materiaasignada_id',
                                                                                                flat=True).distinct())
                                            if not eMateriaAsignada.id in asignados.values_list("id", flat=True):
                                                log(u'Dio click en el botón en horario para ingresar en la clase: %s, pero no se registra asistencia porque al momento de iniciar la clase el profesor. El estudiante no tiene asignado grupo' % eClase,
                                                    request, "add")
                                                mensaje = u"Su asistencia no ha sido registrada porque no tiene asignado grupo de practica. Favor contactarse con director/a de carrera."
                                                lista = ['gestionacademica@unemi.edu.ec',
                                                         'planificacionacademica@unemi.edu.ec',
                                                         'kromanc1@unemi.edu.ec', ]
                                                send_html_mail("Estudiante si grupo de práctica",
                                                               "alu_horarios/emails/notificacion_sin_grupo_practica.html",
                                                               {
                                                                   'sistema': u'Sistema de Gestión Académica',
                                                                   'persona': ePersona,
                                                                   'inscripcion': eInscripcion,
                                                                   'clase': eClase,
                                                                   't': miinstitucion(),
                                                               }, lista, [],
                                                               cuenta=CUENTAS_CORREOS[0][1]
                                                               )
                                                return Helper_Response(isSuccess=True,
                                                                       data={"isWait": False, "mensaje": mensaje,
                                                                             "label_color": "warning"},
                                                                       status=status.HTTP_200_OK)
                    if eClase.tipohorario in [1]:
                        if not ePeriodoAcademia.valida_asistencia_in_home:
                            mensaje = f"Su asistencia no se ha registrado, por favor comunicar al docente de la clase para su registro de la misma. Usted ha ingresado a clases de modalidad presencial a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                            log(u'Ingresa a la clase y su asistencia no se ha registrado por motivo que el horario es presencial el docente debe registrar la asistencia: %s.' % eClase,
                                request, "add")
                            return Helper_Response(isSuccess=True,
                                                   data={"isWait": False, "mensaje": mensaje, "label_color": "warning"},
                                                   status=status.HTTP_200_OK)
                    if eAsistenciaLecciones.values("id").filter(asistio=False, virtual=False).exists():
                        eAsistenciaLecciones = eAsistenciaLecciones.filter(asistio=False, virtual=False)
                        if disponible:
                            eAsistenciaLecciones.update(asistio=True,
                                                        virtual=True,
                                                        virtual_fecha=hoy,
                                                        virtual_hora=horaactual,
                                                        ip_public=ip_public,
                                                        browser=navegador,
                                                        ops=ops,
                                                        screen_size=screen_size,
                                                        usuario_modificacion_id=request.user.id,
                                                        fecha_modificacion=hoy)
                            if variable_valor('ACTUALIZA_ASISTENCIA'):
                                if not eMateriaAsignada.sinasistencia:
                                    ActualizaAsistencia(eMateriaAsignada.id)
                            mensaje = u"Su asistencia ha sido registrada exitosamente."
                            label_color = 'success'
                            log(u'Adiciono asistencia en la clase: %s. Durante el tiempo establecido' % eClase, request,
                                "add")
                        elif disponible_hora:
                            eAsistenciaLecciones.update(asistio=False,
                                                        virtual=True,
                                                        virtual_fecha=hoy,
                                                        virtual_hora=horaactual,
                                                        ip_public=ip_public,
                                                        browser=navegador,
                                                        ops=ops,
                                                        screen_size=screen_size,
                                                        usuario_modificacion_id=request.user.id,
                                                        fecha_modificacion=hoy)
                            if variable_valor('ACTUALIZA_ASISTENCIA'):
                                if not eMateriaAsignada.sinasistencia:
                                    ActualizaAsistencia(eMateriaAsignada.id)
                            mensaje = f"Su asistencia no se ha registrado, usted ha ingresado a clases a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                            label_color = 'warning'
                            log(u'Ingresa a la clase pero no se adiciono asistencia: %s. Debe informar al docente' % eClase,
                                request, "add")
                    elif eAsistenciaLecciones.values("id").filter(asistio=True, virtual=False).exists():
                        eAsistenciaLecciones = eAsistenciaLecciones.filter(asistio=True, virtual=False)
                        eAsistenciaLecciones.update(virtual=True,
                                                    virtual_fecha=hoy,
                                                    virtual_hora=horaactual,
                                                    ip_public=ip_public,
                                                    browser=navegador,
                                                    ops=ops,
                                                    screen_size=screen_size,
                                                    usuario_modificacion_id=request.user.id,
                                                    fecha_modificacion=hoy)
                        if variable_valor('ACTUALIZA_ASISTENCIA'):
                            if not eMateriaAsignada.sinasistencia:
                                ActualizaAsistencia(eMateriaAsignada.id)
                        mensaje = u"Su asistencia ya fue registrada por el/la profesor/a."
                        label_color = 'warning'
                        log(u'Ingresa a la clase su asistencia ya fue registrada previamente: %s.' % eClase, request,
                            "add")
                    elif eAsistenciaLecciones.values("id").filter(asistio=False, virtual=True).exists():
                        mensaje = f"Su asistencia no se ha registrado, usted ha ingresado a clases a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                        label_color = 'warning'
                        log(u'Ingresa a la clase y su asistencia no se ha registrado por motivo de ingreso tarde: %s.' % eClase,
                            request, "add")
                    else:
                        mensaje = u"Su asistencia ya ha sido registrada con anterioridad."
                        label_color = 'success'
                    eAsistenciaLeccion = eAsistenciaLecciones.first()
                    logingreso = LogIngresoAsistenciaLeccion(asistencia=eAsistenciaLeccion,
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             ip_private=None,
                                                             ip_public=ip_public,
                                                             browser=navegador,
                                                             ops=ops,
                                                             screen_size=screen_size
                                                             )
                    logingreso.save(request)
                    """ SE COMENTO PORQUE EN EL SAVE DEL LOGINGRESO SE MANDA ACTUALIZAR"""
                    log(u'Dio click en el botón en horario para ingresar en la clase: %s' % logingreso, request, "add")
                    isWait = False
            datos = {}
            if not isWait:
                if eAsistenciaLecciones.values("id").filter(status=True).exists():
                    eAsistenciaLeccion = eAsistenciaLecciones.filter(status=True).first()
                    datos = {"id": eAsistenciaLeccion.id,
                             "leccion_id": eAsistenciaLeccion.leccion.id,
                             "materiaasignada": eAsistenciaLeccion.materiaasignada.id,
                             "asistenciafinal": null_to_numeric(eAsistenciaLeccion.materiaasignada.asistenciafinal, 0),
                             "porciento_requerido": eAsistenciaLeccion.materiaasignada.porciento_requerido(),
                             "asistenciajustificada": eAsistenciaLeccion.asistenciajustificada,
                             "asistio": eAsistenciaLeccion.asistio,
                             "virtual": eAsistenciaLeccion.virtual,
                             "virtual_fecha": eAsistenciaLeccion.virtual_fecha.__str__() if eAsistenciaLeccion.virtual_fecha else None,
                             "virtual_hora": eAsistenciaLeccion.virtual_hora.strftime(
                                 "%H:%M:%S") if eAsistenciaLeccion.virtual_hora else None,
                             "ip_private": eAsistenciaLeccion.ip_private,
                             "ip_public": eAsistenciaLeccion.ip_public,
                             "browser": eAsistenciaLeccion.browser,
                             "ops": eAsistenciaLeccion.ops,
                             "screen_size": eAsistenciaLeccion.screen_size
                             }
            return Helper_Response(isSuccess=True, data={"isWait": isWait, "datos": datos, "mensaje": mensaje,
                                                         "label_color": label_color}, status=status.HTTP_200_OK)
        except Exception as ex:
            transaction.set_rollback(True)
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)


def gestionar_asistencia(ahora, navegador, ops, screen_size, ip_public, eMateriaAsignada, eClase, eLecciones, eUser, isReturn=True):
    try:
        eMatricula = eMateriaAsignada.matricula
        ePeriodo = eMatricula.nivel.periodo
        ePeriodoAcademia = ePeriodo.get_periodoacademia()
        eInscripcion = eMatricula.inscripcion
        ePersona = eInscripcion.persona
        hoy = ahora.date()
        horaactual = ahora.time()
        mensaje = None
        label_color = None
        isWait = True
        if (eLeccion := eLecciones.filter(clase=eClase).first()) is not None:
            eAsistenciaLecciones = AsistenciaLeccion.objects.filter(leccion_id=eLeccion.id, materiaasignada_id=eMateriaAsignada.id)
            disponible = eClase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia, ahora=ahora)
            disponible_hora = eClase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia, ahora=ahora)
            if isReturn is False:
                logger.info('disponible: {}'.format(disponible))
                logger.info('disponible_hora: {}'.format(disponible_hora))
            if not eAsistenciaLecciones.values("id").exists():
                if eMatricula.estado_matricula == 1:
                    log(u'Dio click en el botón en horario para ingresar en la clase: %s, pero no se registra asistencia por deuda' % eClase, None, "add", eUser)
                    mensaje = u"Su asistencia no ha sido registrada por deuda pendiente. Revisar modulo de <a href='/alu_finanzas' target='_blank'>Mis Finanzas</a>"
                    if isReturn:
                        return True, {"isWait": False, "mensaje": mensaje, "label_color": "warning"}
                else:
                    if eClase.tipoprofesor.id == 2 and eClase.tipohorario in [1, 2, 8]:
                        if eClase.grupoprofesor:
                            if eClase.grupoprofesor.paralelopractica:
                                if eClase.grupoprofesor.listado_inscritos_grupos_practicas().exists():
                                    listado_alumnos_practica = eClase.grupoprofesor.listado_inscritos_grupos_practicas()
                                    if ePeriodoAcademia.valida_asistencia_pago:
                                        asignados = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True).distinct(), matricula__estado_matricula__in=[2, 3])
                                    else:
                                        asignados = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True).distinct())
                                    if not eMateriaAsignada.id in asignados.values_list("id", flat=True):
                                        log(u'Dio click en el botón en horario para ingresar en la clase: %s, pero no se registra asistencia porque al momento de iniciar la clase el profesor. El estudiante no tiene asignado grupo' % eClase, None, "add", eUser)
                                        mensaje = u"Su asistencia no ha sido registrada porque no tiene asignado grupo de practica. Favor contactarse con director/a de carrera."
                                        lista = ['gestionacademica@unemi.edu.ec',
                                                 'planificacionacademica@unemi.edu.ec',
                                                 'kromanc1@unemi.edu.ec', ]
                                        send_html_mail("Estudiante si grupo de práctica",
                                                       "alu_horarios/emails/notificacion_sin_grupo_practica.html",
                                                       {
                                                           'sistema': u'Sistema de Gestión Académica',
                                                           'persona': ePersona,
                                                           'inscripcion': eInscripcion,
                                                           'clase': eClase,
                                                           't': miinstitucion(),
                                                       }, lista, [],
                                                       cuenta=CUENTAS_CORREOS[0][1]
                                                       )
                                        if isReturn:
                                            return True, {"isWait": False, "mensaje": mensaje, "label_color": "warning"}
            if eClase.tipohorario in [1]:
                if not ePeriodoAcademia.valida_asistencia_in_home:
                    mensaje = f"Su asistencia no se ha registrado, por favor comunicar al docente de la clase para su registro de la misma. Usted ha ingresado a clases de modalidad presencial a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                    log(u'Ingresa a la clase y su asistencia no se ha registrado por motivo que el horario es presencial el docente debe registrar la asistencia: %s.' % eClase, None, "add", eUser)
                    if isReturn:
                        return True, {"isWait": False, "mensaje": mensaje, "label_color": "warning"}
            if eAsistenciaLecciones.values("id").filter(asistio=False, virtual=False).exists():
                eAsistenciaLecciones = eAsistenciaLecciones.filter(asistio=False, virtual=False)
                if disponible:
                    eAsistenciaLecciones.update(status=True,
                                                asistio=True,
                                                virtual=True,
                                                virtual_fecha=hoy,
                                                virtual_hora=horaactual,
                                                ip_public=ip_public,
                                                browser=navegador,
                                                ops=ops,
                                                screen_size=screen_size,
                                                usuario_modificacion_id=eUser.id,
                                                fecha_modificacion=hoy)
                    if variable_valor('ACTUALIZA_ASISTENCIA'):
                        if not eMateriaAsignada.sinasistencia:
                            ActualizaAsistencia(eMateriaAsignada.id)
                    mensaje = u"Su asistencia ha sido registrada exitosamente."
                    label_color = 'success'
                    log(u'Adiciono asistencia en la clase: %s. Durante el tiempo establecido' % eClase, None, "add", eUser)
                elif disponible_hora:
                    eAsistenciaLecciones.update(status=True,
                                                asistio=False,
                                                virtual=True,
                                                virtual_fecha=hoy,
                                                virtual_hora=horaactual,
                                                ip_public=ip_public,
                                                browser=navegador,
                                                ops=ops,
                                                screen_size=screen_size,
                                                usuario_modificacion_id=eUser.id,
                                                fecha_modificacion=hoy)
                    if variable_valor('ACTUALIZA_ASISTENCIA'):
                        if not eMateriaAsignada.sinasistencia:
                            ActualizaAsistencia(eMateriaAsignada.id)
                    mensaje = f"Su asistencia no se ha registrado, usted ha ingresado a clases a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                    label_color = 'warning'
                    log(u'Ingresa a la clase pero no se adiciono asistencia: %s. Debe informar al docente' % eClase, None, "add", eUser)
            elif eAsistenciaLecciones.values("id").filter(asistio=True, virtual=False).exists():
                eAsistenciaLecciones = eAsistenciaLecciones.filter(asistio=True, virtual=False)
                eAsistenciaLecciones.update(status=True,
                                            virtual=True,
                                            virtual_fecha=hoy,
                                            virtual_hora=horaactual,
                                            ip_public=ip_public,
                                            browser=navegador,
                                            ops=ops,
                                            screen_size=screen_size,
                                            usuario_modificacion_id=eUser.id,
                                            fecha_modificacion=hoy)
                if variable_valor('ACTUALIZA_ASISTENCIA'):
                    if not eMateriaAsignada.sinasistencia:
                        ActualizaAsistencia(eMateriaAsignada.id)
                mensaje = u"Su asistencia ya fue registrada por el/la profesor/a."
                label_color = 'warning'
                log(u'Ingresa a la clase su asistencia ya fue registrada previamente: %s.' % eClase, None, "add", eUser)
            elif eAsistenciaLecciones.values("id").filter(asistio=False, virtual=True).exists():
                mensaje = f"Su asistencia no se ha registrado, usted ha ingresado a clases a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                label_color = 'warning'
                log(u'Ingresa a la clase y su asistencia no se ha registrado por motivo de ingreso tarde: %s.' % eClase, None, "add", eUser)
            else:
                mensaje = u"Su asistencia ya ha sido registrada con anterioridad."
                label_color = 'success'
            if eAsistenciaLecciones.values("id").filter(status=True).exists():
                eAsistenciaLeccion = eAsistenciaLecciones.first()
                logingreso = LogIngresoAsistenciaLeccion(asistencia=eAsistenciaLeccion,
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         ip_private=None,
                                                         ip_public=ip_public,
                                                         browser=navegador,
                                                         ops=ops,
                                                         screen_size=screen_size
                                                         )
                logingreso.save(usuario_id=eUser.id)
                """ SE COMENTO PORQUE EN EL SAVE DEL LOGINGRESO SE MANDA ACTUALIZAR"""
                log(u'Dio click en el botón en horario para ingresar en la clase: %s' % logingreso, None, "add", eUser)
                key_cache_leccion = f'data_asistencias_leccion_id_{encrypt(eLeccion.id)}'
                if cache.has_key(key_cache_leccion):
                    c_data = cache.get(key_cache_leccion)
                    encontrado = False
                    for elemento in c_data:
                        if elemento["id"] == eAsistenciaLeccion.id:
                            encontrado = True
                            break
                    if encontrado is False:
                        c_data.append({"id": eAsistenciaLeccion.id,
                                       "leccion_id": eAsistenciaLeccion.leccion.id,
                                       "materiaasignada": eAsistenciaLeccion.materiaasignada.id,
                                       "asistenciafinal": null_to_numeric(eAsistenciaLeccion.materiaasignada.asistenciafinal, 0),
                                       "porciento_requerido": eAsistenciaLeccion.materiaasignada.porciento_requerido(),
                                       "asistenciajustificada": eAsistenciaLeccion.asistenciajustificada,
                                       "asistio": eAsistenciaLeccion.asistio,
                                       "virtual": eAsistenciaLeccion.virtual,
                                       "virtual_fecha": eAsistenciaLeccion.virtual_fecha.__str__() if eAsistenciaLeccion.virtual_fecha else None,
                                       "virtual_hora": eAsistenciaLeccion.virtual_hora.strftime("%H:%M:%S") if eAsistenciaLeccion.virtual_hora else None,
                                       "ip_private": eAsistenciaLeccion.ip_private,
                                       "ip_public": eAsistenciaLeccion.ip_public,
                                       "browser": eAsistenciaLeccion.browser,
                                       "ops": eAsistenciaLeccion.ops,
                                       "screen_size": eAsistenciaLeccion.screen_size
                                       })
                    d = eLeccion.fecha
                    d2 = datetime(d.year, d.month, d.day, eClase.turno.comienza.hour, eClase.turno.comienza.minute)
                    time_life_token = (time.mktime((datetime(d.year, d.month, d.day, eClase.turno.termina.hour, eClase.turno.termina.minute)).timetuple()) - time.mktime(d2.timetuple()))
                    """NO CAMBIAR, SI SE DESEA HACER PRUEBAS; PONGA SU MAQUINA EN AMBIENTE PRODUCCIÓN."""
                    cache.set(key_cache_leccion, c_data, int(time_life_token))
            isWait = False
        datos = {}
        if not isWait:
            if (eAsistenciaLeccion := AsistenciaLeccion.objects.filter(leccion_id=eLeccion.id, materiaasignada_id=eMateriaAsignada.id).first()) is not None:
                datos = {"id": eAsistenciaLeccion.id,
                         "leccion_id": eAsistenciaLeccion.leccion.id,
                         "materiaasignada": eAsistenciaLeccion.materiaasignada.id,
                         "asistenciafinal": null_to_numeric(eAsistenciaLeccion.materiaasignada.asistenciafinal, 0),
                         "porciento_requerido": eAsistenciaLeccion.materiaasignada.porciento_requerido(),
                         "asistenciajustificada": eAsistenciaLeccion.asistenciajustificada,
                         "asistio": eAsistenciaLeccion.asistio,
                         "virtual": eAsistenciaLeccion.virtual,
                         "virtual_fecha": eAsistenciaLeccion.virtual_fecha.__str__() if eAsistenciaLeccion.virtual_fecha else None,
                         "virtual_hora": eAsistenciaLeccion.virtual_hora.strftime("%H:%M:%S") if eAsistenciaLeccion.virtual_hora else None,
                         "ip_private": eAsistenciaLeccion.ip_private,
                         "ip_public": eAsistenciaLeccion.ip_public,
                         "browser": eAsistenciaLeccion.browser,
                         "ops": eAsistenciaLeccion.ops,
                         "screen_size": eAsistenciaLeccion.screen_size
                         }
        if isReturn:
            return True, {"isWait": isWait, "datos": datos, "mensaje": mensaje, "label_color": label_color}
        else:
            logger.info('isWait: {} - datos: {} - mensaje: {} - label_color: {}'.format(isWait, datos, mensaje, label_color))

    except Exception as ex:
        print('Error: {}'.format(ex.__str__()))
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
        if isReturn:
            return False, {}
        else:
            logger.error('Error: {}'.format(ex.__str__()))
            logger.error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))


def gestionar_asistencia_task(params):
    ids_lec = params.get('ids_lec', [])
    id_c = params.get('id_c', 0)
    id_ma = params.get('id_ma', 0)
    navegador = params.get('navegador', None)
    ops = params.get('os', None)
    screen_size = params.get('screensize', None)
    ip_public = params.get('ip_public', None)
    ahora = params.get('ahora', 0)
    ahora = datetime.fromtimestamp(ahora)
    logger.info('ahora: {}'.format(ahora))
    eClase = Clase.objects.get(pk=id_c)
    eMateriaAsignada = MateriaAsignada.objects.get(pk=id_ma)
    eLecciones = Leccion.objects.filter(pk__in=ids_lec)
    eUser = eMateriaAsignada.matricula.inscripcion.persona.usuario
    gestionar_asistencia(ahora, navegador, ops, screen_size, ip_public, eMateriaAsignada, eClase, eLecciones, eUser, False)


def gestionar_asistencia_admision(request, eInscripcion, ePeriodo, eClase, isRedis, data_redis):
    with transaction.atomic():
        try:
            ahora = datetime.now()
            hoy = ahora.date()
            eLeccionGrupos = LeccionGrupo.objects.none()
            if isRedis:
                if data_redis:
                    leccion_grupo_id = data_redis.get('leccion_grupo_id', 0)
                    eLeccionGrupos = LeccionGrupo.objects.filter(pk=leccion_grupo_id, abierta=True).order_by('-fecha', '-horaentrada')
            else:
                eLeccionGrupos = LeccionGrupo.objects.filter(status=True, fecha=hoy, turno=eClase.turno, dia=eClase.dia, profesor_id=eClase.profesor_id, abierta=True).order_by('-fecha', '-horaentrada')
            isWait = True
            mensaje = None
            label_color = None
            if not eLeccionGrupos.values("id").exists():
                return True, {"isWait": isWait, "datos": {}, "mensaje": mensaje, "label_color": label_color}
            eLeccionGrupo = eLeccionGrupos.first()
            eLecciones = eLeccionGrupo.mis_leciones()
            eMatricula = eInscripcion.mi_matricula_periodo(ePeriodo.id)
            eMateriaAsignada = eMatricula.materiaasignada_set.get(materia=eClase.materia)
            eUser = eMateriaAsignada.matricula.inscripcion.persona.usuario
            navegador = request.data.get('navegador', None)
            ops = request.data.get('os', None)
            screen_size = request.data.get('screensize', None)
            ip_public = get_client_ip(request)
            if eMateriaAsignada.sinasistencia:
                utiliza_q_cluster = variable_valor('UTILIZA_ASISTENCIA_QCLUSTER')
                if utiliza_q_cluster:
                    isWait = False
                    mensaje = f"Su ingreso a la clase ha sido registrado exitosamente a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>."
                    label_color = 'success'
                    group = f"group_gestionar_asistencia_{eClase.id}_{eClase.turno_id}_{eClase.dia}_{hoy.strftime('%d%m%Y')}"
                    name = f"name_gestionar_asistencia_{eClase.id}_{eClase.turno_id}_{eClase.dia}_{hoy.strftime('%d%m%Y')}_{eMateriaAsignada.matricula.inscripcion.persona.usuario_id}"
                    params = {
                        "ids_lec": [x.id for x in eLecciones],
                        "id_c": eClase.id,
                        "id_ma": eMateriaAsignada.id,
                        "navegador": navegador,
                        "ops": ops,
                        "screen_size": screen_size,
                        "ip_public": ip_public,
                        "ahora": ahora.timestamp(),
                    }
                    async_task(gestionar_asistencia_task, params, group=group, task_name=name)
                else:
                    isSuccess, data = gestionar_asistencia(ahora, navegador, ops, screen_size, ip_public, eMateriaAsignada, eClase, eLecciones, eUser, True)
                    if isSuccess is False:
                        raise NameError(u"Error al generar asistencia")
                    return True, data
            else:
                isSuccess, data = gestionar_asistencia(ahora, navegador, ops, screen_size, ip_public, eMateriaAsignada, eClase, eLecciones, eUser, True)
                if isSuccess is False:
                    raise NameError(u"Error al generar asistencia")
                return True, data
            return True, {"isWait": isWait, "datos": {}, "mensaje": mensaje, "label_color": label_color}
        except Exception as ex:
            print('Error: {}'.format(ex.__str__()))
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            transaction.set_rollback(True)
            return False, {}


def gestionar_asistencia_pregrado(request, eInscripcion, ePeriodo, eClase, isRedis, data_redis):
    with transaction.atomic():
        try:
            ahora = datetime.now()
            hoy = ahora.date()
            eLeccionGrupos = LeccionGrupo.objects.none()
            if isRedis:
                if data_redis:
                    leccion_grupo_id = data_redis.get('leccion_grupo_id', 0)
                    eLeccionGrupos = LeccionGrupo.objects.filter(pk=leccion_grupo_id, abierta=True).order_by('-fecha', '-horaentrada')
            else:
                eLeccionGrupos = LeccionGrupo.objects.filter(status=True, fecha=hoy, turno=eClase.turno, dia=eClase.dia, profesor_id=eClase.profesor_id, abierta=True).order_by('-fecha', '-horaentrada')
            isWait = True
            mensaje = None
            label_color = None
            if not eLeccionGrupos.values("id").exists():
                return True, {"isWait": isWait, "datos": {}, "mensaje": mensaje, "label_color": label_color}
            eLeccionGrupo = eLeccionGrupos.first()
            eLecciones = eLeccionGrupo.mis_leciones()
            eMatricula = eInscripcion.mi_matricula_periodo(ePeriodo.id)
            eMateriaAsignada = eMatricula.materiaasignada_set.get(materia=eClase.materia)
            eUser = eMateriaAsignada.matricula.inscripcion.persona.usuario
            navegador = request.data.get('navegador', None)
            ops = request.data.get('os', None)
            screen_size = request.data.get('screensize', None)
            ip_public = get_client_ip(request)
            if eMateriaAsignada.sinasistencia:
                isWait = False
                mensaje = f"Su ingreso a la clase ha sido registrado exitosamente a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>."
                label_color = 'success'
                group = f"group_gestionar_asistencia_{eClase.id}_{eClase.turno_id}_{eClase.dia}_{hoy.strftime('%d%m%Y')}"
                name = f"name_gestionar_asistencia_{eClase.id}_{eClase.turno_id}_{eClase.dia}_{hoy.strftime('%d%m%Y')}_{eMateriaAsignada.matricula.inscripcion.persona.usuario_id}"
                params = {
                    "ids_lec": [x.id for x in eLecciones],
                    "id_c": eClase.id,
                    "id_ma": eMateriaAsignada.id,
                    "navegador": navegador,
                    "ops": ops,
                    "screen_size": screen_size,
                    "ip_public": ip_public,
                    "ahora": ahora.timestamp(),
                }
                async_task(gestionar_asistencia_task, params, group=group, task_name=name)
            else:
                isSuccess, data = gestionar_asistencia(ahora, navegador, ops, screen_size, ip_public, eMateriaAsignada, eClase, eLecciones, eUser, True)
                if isSuccess is False:
                    raise NameError(u"Error al generar asistencia")
                return True, data
            return True, {"isWait": isWait, "datos": {}, "mensaje": mensaje, "label_color": label_color}
        except Exception as ex:
            print('Error: {}'.format(ex.__str__()))
            print('Error en la funcion gestionar_asistencia_pregrado: {}'.format(sys.exc_info()[-1].tb_lineno))
            transaction.set_rollback(True)
            return False, {}


def gestionar_asistencia_posgrado(request, eInscripcion, ePeriodo, eClase, isRedis, data_redis):
    with transaction.atomic():
        try:
            ahora = datetime.now()
            hoy = ahora.date()
            eLeccionGrupos = LeccionGrupo.objects.none()
            if isRedis:
                if data_redis:
                    leccion_grupo_id = data_redis.get('leccion_grupo_id', 0)
                    eLeccionGrupos = LeccionGrupo.objects.filter(pk=leccion_grupo_id, abierta=True).order_by('-fecha', '-horaentrada')
            else:
                eLeccionGrupos = LeccionGrupo.objects.filter(status=True, fecha=hoy, turno=eClase.turno, dia=eClase.dia, profesor_id=eClase.profesor_id, abierta=True).order_by('-fecha', '-horaentrada')
            isWait = True
            mensaje = None
            label_color = None
            if not eLeccionGrupos.values("id").exists():
                return True, {"isWait": isWait, "datos": {}, "mensaje": mensaje, "label_color": label_color}
            eLeccionGrupo = eLeccionGrupos.first()
            eLecciones = eLeccionGrupo.mis_leciones()
            eMatricula = eInscripcion.mi_matricula_periodo(ePeriodo.id)
            eMateriaAsignada = eMatricula.materiaasignada_set.get(materia=eClase.materia)
            eUser = eMateriaAsignada.matricula.inscripcion.persona.usuario
            navegador = request.data.get('navegador', None)
            ops = request.data.get('os', None)
            screen_size = request.data.get('screensize', None)
            ip_public = get_client_ip(request)
            if eMateriaAsignada.sinasistencia:
                isWait = False
                mensaje = f"Su ingreso a la clase ha sido registrado exitosamente a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>."
                label_color = 'success'
                group = f"group_gestionar_asistencia_{eClase.id}_{eClase.turno_id}_{eClase.dia}_{hoy.strftime('%d%m%Y')}"
                name = f"name_gestionar_asistencia_{eClase.id}_{eClase.turno_id}_{eClase.dia}_{hoy.strftime('%d%m%Y')}_{eMateriaAsignada.matricula.inscripcion.persona.usuario_id}"
                params = {
                    "ids_lec": [x.id for x in eLecciones],
                    "id_c": eClase.id,
                    "id_ma": eMateriaAsignada.id,
                    "navegador": navegador,
                    "ops": ops,
                    "screen_size": screen_size,
                    "ip_public": ip_public,
                    "ahora": ahora.timestamp(),
                }
                async_task(gestionar_asistencia_task, params, group=group, task_name=name)
            else:
                isSuccess, data = gestionar_asistencia(ahora, navegador, ops, screen_size, ip_public, eMateriaAsignada, eClase, eLecciones, eUser, True)
                if isSuccess is False:
                    raise NameError(u"Error al generar asistencia")
                return True, data
            return True, {"isWait": isWait, "datos": {}, "mensaje": mensaje, "label_color": label_color}
        except Exception as ex:
            print('Error: {}'.format(ex.__str__()))
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            transaction.set_rollback(True)
            return False, {}


def enterClassEstudiante(request):
    ahora = datetime.now()
    fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
    tiempo_cache = fecha_fin - ahora
    TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
    try:
        payload = request.auth.payload
        if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
            ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
        else:
            ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
            cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u"Solo los perfiles de estudiantes pueden ingresar al modulo.")
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
        idc = request.data.get('idc', None)
        navegador = request.data.get('navegador', None)
        ops = request.data.get('os', None)
        screen_size = request.data.get('screensize', None)
        if idc is None:
            raise NameError(u"Clase no encontrada")
        if navegador is None:
            raise NameError(u"Navegador no identificado")
        if ops is None:
            raise NameError(u"Sistema Operativo no identificado")
        if screen_size is None:
            raise NameError(u"Tamaño de la pantalla no identificado")

        ePeriodoAcademia = ePeriodo.get_periodoacademia()
        data_redis = None
        isRedis = False
        if ePeriodoAcademia:
            if ePeriodoAcademia.utiliza_asistencia_redis:
                isRedis = True
                key = request.data.get('key', None)
                if key is None:
                    raise NameError(u"Token de acceso no encontrado")
                token = request.data['key']
                if cache.has_key(token):
                    data_redis = cache.get(token)
                else:
                    return True, {"isWait": True, "datos": {}, "mensaje": None, "label_color": None}
        try:
            eClase = Clase.objects.get(pk=idc)
        except ObjectDoesNotExist:
            raise NameError(u"Clase no encontrada")
        es_admision = eInscripcion.es_admision()
        es_pregrado = eInscripcion.es_pregrado()
        es_posgrado = eInscripcion.es_posgrado()
        isSuccess = False
        data = {}
        if es_admision or es_pregrado or es_posgrado:
            if es_admision:
                isSuccess, data = gestionar_asistencia_admision(request, eInscripcion, ePeriodo, eClase, isRedis, data_redis)
            elif es_pregrado:
                isSuccess, data = gestionar_asistencia_pregrado(request, eInscripcion, ePeriodo, eClase, isRedis, data_redis)
            elif es_posgrado:
                isSuccess, data = gestionar_asistencia_posgrado(request, eInscripcion, ePeriodo, eClase, isRedis, data_redis)
        return isSuccess, data
    except Exception as ex:
        print(f"Error funcion enterClassEstudiante: {sys.exc_info()[-1].tb_lineno}")
        return False, {'message': ex.__str__()}


