# -*- coding: latin-1 -*-
import json
import time
import redis as Redis
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from inno.models import PeriodoAcademia, LogIngresoAsistenciaLeccion
from matricula.funciones import valid_intro_module_estudiante
from matricula.models import PeriodoMatricula
from settings import CLASES_APERTURA_ANTES, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_BD, DEBUG
from sga.clases_threading import ActualizaAsistencia
from sga.commonviews import adduserdata
from sga.funciones import log, variable_valor
from sga.models import Sesion, Clase, SesionZoom, MateriaAsignada, DesactivarSesionZoom, DetalleSesionZoom, Leccion, \
    AsistenciaLeccion, LeccionGrupo, miinstitucion, CUENTAS_CORREOS
from sga.commonviews import get_client_ip
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    hoy = datetime.now().date()
    horaactual = datetime.now().time()

    # automatricula de pregrado
    confirmar_automatricula_pregrado = inscripcion.tiene_automatriculapregrado_por_confirmar(periodo)
    if confirmar_automatricula_pregrado:
        mat = inscripcion.mi_matricula_periodo(periodo.id)
        if mat.nivel.fechainicioagregacion > datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado estudiante, se informa que el proceso de aceptación de matrícula empieza %s" % mat.nivel.fechainicioagregacion.__str__())
        if mat.nivel.fechafinagregacion < datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado estudiante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
        if PeriodoMatricula.objects.values("id").filter(periodo=periodo, status=True).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=periodo, status=True)[0]
            if not ePeriodoMatricula.activo:
                return HttpResponseRedirect("/?info=Estimado aspirante, se informa que el proceso de matrícula se encuentra inactivo")
        return HttpResponseRedirect("/alu_matricula/pregrado")

    # automatricula de admisión
    confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
    if confirmar_automatricula_admision:
        mat = inscripcion.mi_matricula_periodo(periodo.id)
        if mat.nivel.fechainicioagregacion > datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado aspirante, se informa que el proceso de aceptación de matrícula empieza %s" % mat.nivel.fechainicioagregacion.__str__())
        if mat.nivel.fechafinagregacion < datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
        if PeriodoMatricula.objects.values("id").filter(periodo=periodo, status=True).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=periodo, status=True)[0]
            if not ePeriodoMatricula.activo:
                return HttpResponseRedirect("/?info=Estimado estudiante, se informa que el proceso de matrícula se encuentra inactivo")
        return HttpResponseRedirect("/alu_matricula/admision")

    ePeriodoAcademia = periodo.get_periodoacademia()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadInitialData':
            try:
                aSesiones = []
                numerosemanaactual = datetime.today().isocalendar()[1]
                diaactual = hoy.isocalendar()[2]
                semana = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                matricula = inscripcion.mi_matricula_periodo(periodo.id)
                materias = matricula.materiaasignada_set.all()
                clases = Clase.objects.db_manager("sga_select").filter(fin__gte=hoy, activo=True, materia__materiaasignada__matricula_id=matricula.id, materia__materiaasignada__retiramateria=False).distinct().order_by('inicio')
                clases2 = Clase.objects.db_manager("sga_select").filter(fin__lt=hoy, activo=True, materia__materiaasignada__matricula_id=matricula.id, materia__materiaasignada__retiramateria=False).distinct().order_by('inicio')
                sesiones = Sesion.objects.db_manager("sga_select").filter(turno__clase__in=clases.values_list("id").distinct() | clases2.values_list("id").distinct()).distinct()
                for sesion in sesiones:
                    turnos = []
                    for turno in sesion.turnos_clase2(clases):
                        semana_turno = []
                        for dia in semana:
                            # if dia[0] == 4 and turno.id == 12:
                            #     # print("para hacer una pausa")
                            clasesactuales = []
                            for clase in turno.horario_alumno_presente_consulta(hoy, dia[0], matricula, periodo.id):
                                grupoprofesor = None
                                disponible = clase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia)
                                disponible_hora = clase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                                if clase.tipoprofesor and clase.grupoprofesor and clase.tipoprofesor.id == 2 and clase.grupoprofesor.paralelopractica:
                                    grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                                action_button = {}
                                # 1 => PRESENCIAL
                                # 2 => CLASE VIRTUAL SINCRÓNICA
                                # 7 => CLASE VIRTUAL ASINCRÓNICA
                                # 8 => CLASE REFUERZO SINCRÓNICA
                                if clase.tipohorario == 2 or clase.tipohorario == 8 or clase.tipohorario == 7:
                                    if clase.dia == diaactual and hoy >= clase.inicio and hoy <= clase.fin:
                                        if clase.tipohorario == 2 or clase.tipohorario == 8:
                                            if disponible_hora:
                                                """SOLO PARA ADMISIÓN Y QUE SEA PROPEDÉUTICO"""
                                                if clase.materia.coordinacion().id == 9 and clase.materia.asignatura.id == 4837:
                                                    url = f"https://www.facebook.com/groups/aspirantes2021.unemioficial"
                                                    style = u"background-color: #2d8cff !important;"
                                                    action_button = {"action": "go_class",
                                                                     "url": url,
                                                                     "wait": False,
                                                                     "disponible": disponible,
                                                                     "verbose": u"Entrar a clase" if disponible else u"Ir a clase",
                                                                     "icon": u"fa fa-facebook-square",
                                                                     "style": style if disponible else u"background-color: #F46839 !important;",
                                                                     "key": f'c_id:{encrypt(clase.id)};t_id:{encrypt(clase.turno.id)};usu_id:{encrypt(persona.usuario.id)};day:{encrypt(dia[0])};date:{hoy.strftime("%d-%m-%Y")}',
                                                                     }
                                                else:
                                                    url = None
                                                    style = None
                                                    if clase.profesor:
                                                        if clase.materia.tieneurlwebex(clase.profesor):
                                                            url = f"https://unemi.webex.com/meet/{ clase.profesor.persona.usuario }"
                                                            style = u"background-color: #2d8cff !important;"
                                                        elif clase.profesor.urlzoom:
                                                            url = clase.profesor.urlzoom
                                                            style = u"background-color: #2d8cff !important;"
                                                    action_button = {"action": "go_class",
                                                                     "url": url,
                                                                     "wait": True,
                                                                     "disponible": disponible,
                                                                     "verbose": u"Entrar a clase" if disponible else u"Ir a clase",
                                                                     "icon": u"fa fa-video-camera",
                                                                     "style": style if disponible else u"background-color: #F46839 !important;",
                                                                     "key": f'c_id:{encrypt(clase.id)};t_id:{encrypt(clase.turno.id)};usu_id:{encrypt(persona.usuario.id)};day:{encrypt(dia[0])};date:{hoy.strftime("%d-%m-%Y")}',
                                                                     }
                                        elif clase.tipohorario == 7:
                                            clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                            url = None
                                            if clasesactualesasincronica.exists():
                                                url = f"https://aulagrado.unemi.edu.ec/mod/forum/view.php?id={ clasesactualesasincronica[0].idforomoodle }"
                                            action_button = {"action": "go_class",
                                                             "url": url,
                                                             "wait": False,
                                                             "disponible": False,
                                                             "verbose": u"Ir a la clase",
                                                             "icon": u"fa fa-comments",
                                                             "style": None,
                                                             }

                                clasesactuales.append({"id": clase.id,
                                                       "asignatura": clase.materia.asignatura.nombre,
                                                       "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                                       "paralelo": clase.materia.paralelo,
                                                       "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                                       "aula": clase.aula.nombre,
                                                       "sede": clase.aula.sede.nombre,
                                                       "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                                       "fin": clase.fin.strftime("%d-%m-%Y"),
                                                       "tipoprofesor_id": clase.tipoprofesor.id if clase.tipoprofesor else None,
                                                       "tipoprofesor": clase.tipoprofesor.__str__() if clase.tipoprofesor else None,
                                                       "profesor": clase.profesor.__str__() if clase.profesor else None,
                                                       "profesor_sexo_id": clase.profesor.persona.sexo.id if clase.profesor and clase.profesor.persona.sexo else 2,
                                                       "tipohorario": clase.tipohorario,
                                                       "tipohorario_display": clase.get_tipohorario_display(),
                                                       "grupoprofesor": grupoprofesor,
                                                       "action_button": action_button,
                                                       })
                            semana_turno.append({"dia": dia[0],
                                                 "clases": clasesactuales})
                        turnos.append({"id": turno.id,
                                       "verbose": turno.__str__(),
                                       "comienza": turno.comienza.strftime("%H:%M"),
                                       "termina": turno.termina.strftime("%H:%M"),
                                       "semana": semana_turno,
                                       "activo": horaactual >= turno.comienza and horaactual <= turno.termina,
                                       })
                    turnos_old = []
                    for turno in sesion.turnos_clase2(clases2):
                        semana_turno = []
                        for dia in semana:
                            clasespasadas = []
                            for clase in turno.horario_alumno_pasado_consulta(hoy, dia[0], matricula, periodo.id):
                                disponible = clase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia)
                                disponible_hora = clase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                                grupoprofesor = None
                                if clase.tipoprofesor and clase.grupoprofesor and clase.tipoprofesor == 2 and clase.dia == diaactual and disponible_hora and clase.grupoprofesor.paralelopractica:
                                    grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                                clasespasadas.append({"id": clase.id,
                                                       "asignatura": clase.materia.asignatura.nombre,
                                                       "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                                       "paralelo": clase.materia.paralelo,
                                                       "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                                       "aula": clase.aula.nombre,
                                                       "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                                       "fin": clase.fin.strftime("%d-%m-%Y"),
                                                       "tipoprofesor": clase.tipoprofesor.__str__() if clase.tipoprofesor else None,
                                                       "profesor": clase.profesor.__str__() if clase.profesor else None,
                                                       "tipohorario": clase.tipohorario,
                                                       "tipohorario_display": clase.get_tipohorario_display(),
                                                       "grupoprofesor": grupoprofesor,
                                                       })
                            semana_turno.append({"dia": dia[0],
                                                 "clases": clasespasadas})
                        turnos_old.append({"id": turno.id,
                                           "verbose": turno.__str__(),
                                           "comienza": turno.comienza.strftime("%H:%M"),
                                           "termina": turno.termina.strftime("%H:%M"),
                                           "semana": semana_turno,
                                           "activo": horaactual >= turno.comienza and horaactual <= turno.termina,
                                           })

                    aSesiones.append({"id": sesion.id,
                                      "verbose": sesion.nombre if inscripcion and inscripcion.coordinacion.id == 9 else sesion.__str__(),
                                      "nombre": sesion.nombre,
                                      "turnos": turnos,
                                      "turnos_old": turnos_old,
                                      })

                return JsonResponse({"result": "ok", "diaactual": diaactual, "semana": semana, "aSesiones": aSesiones})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        if action == 'enterClass':
            try:
                if not 'idc' in request.POST:
                    raise NameError(u"Clase no encontrada")
                if not Clase.objects.db_manager("sga_select").values("id").filter(pk=int(request.POST['idc'])).exists():
                    raise NameError(u"Clase no encontrada")
                if not 'navegador' in request.POST:
                    raise NameError(u"Navegador no identificado")
                if not 'os' in request.POST:
                    raise NameError(u"Sistema Operativo no identificado")
                if not 'screensize' in request.POST:
                    raise NameError(u"Tamaño de la pantalla no identificado")
                navegador = request.POST['navegador']
                ops = request.POST['os']
                screen_size = request.POST['screensize']
                ip_public = get_client_ip(request)
                mensaje = None
                label_color = None
                clase = Clase.objects.db_manager("sga_select").filter(pk=request.POST['idc'])[0]
                isWait = True
                isRedis = False
                data_redis = None
                clasesabiertas = None
                if ePeriodoAcademia:
                    if ePeriodoAcademia.utiliza_asistencia_redis and (ePeriodoAcademia.es_virtual() or ePeriodoAcademia.es_hibrida()):
                        isRedis = True
                        if not 'key' in request.POST:
                            raise NameError(u"Token de acceso no encontrado")
                        token = request.POST['key']
                        redis = Redis.StrictRedis(host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_BD)
                        token_data = redis.get(token)
                        if token_data:
                            data_redis = json.loads(token_data)

                if isRedis:
                    if data_redis:
                        leccion_grupo_id = data_redis['leccion_grupo_id'] if 'leccion_grupo_id' in data_redis and data_redis['leccion_grupo_id'] else 0
                        clasesabiertas = LeccionGrupo.objects.db_manager("sga_select").filter(pk=leccion_grupo_id, abierta=True).order_by('-fecha', '-horaentrada')
                else:
                    clasesabiertas = LeccionGrupo.objects.filter(status=True, fecha=hoy, turno=clase.turno, dia=clase.dia, profesor_id=clase.profesor.id, abierta=True).order_by('-fecha', '-horaentrada')
                if clasesabiertas and clasesabiertas.values("id").exists():
                    if clasesabiertas[0].mis_leciones().values('id').filter(clase=clase).exists():
                        leccion = clasesabiertas[0].mis_leciones().filter(clase=clase)[0]
                        matricula = inscripcion.mi_matricula_periodo(periodo.id)
                        materiaasignada = matricula.materiaasignada_set.filter(materia=clase.materia)[0]
                        asistencias = AsistenciaLeccion.objects.filter(leccion=leccion, materiaasignada=materiaasignada)
                        disponible = clase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia)
                        disponible_hora = clase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                        if not asistencias.values("id").exists():
                            if materiaasignada.matricula.estado_matricula == 1:
                                log(u'Dio click en el botón en horario para ingresar en la clase: %s, pero no se registra asistencia por deuda' % clase, request, "add")
                                mensaje = u"Su asistencia no ha sido registrada por deuda pendiente. Revisar modulo de <a href='/alu_finanzas' target='_blank'>Mis Finanzas</a>"
                                return JsonResponse({"result": "ok", "isWait": False, "mensaje": mensaje, "label_color": "warning"})
                            else:
                                if clase.tipoprofesor.id == 2 and clase.tipohorario in [1, 2, 8]:
                                    if clase.grupoprofesor:
                                        if clase.grupoprofesor.paralelopractica:
                                            # grupoprofesor_id = clase.grupoprofesor.id
                                            if clase.grupoprofesor.listado_inscritos_grupos_practicas().exists():
                                                listado_alumnos_practica = clase.grupoprofesor.listado_inscritos_grupos_practicas()
                                                if ePeriodoAcademia.valida_asistencia_pago:
                                                    asignados = MateriaAsignada.objects.db_manager("sga_select").filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True).distinct(), matricula__estado_matricula__in=[2, 3])
                                                else:
                                                    asignados = MateriaAsignada.objects.db_manager("sga_select").filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True).distinct())
                                                if not materiaasignada.id in asignados.values_list("id", flat=True):
                                                    log(u'Dio click en el botón en horario para ingresar en la clase: %s, pero no se registra asistencia porque al momento de iniciar la clase el profesor. El estudiante no tiene asignado grupo' % clase, request, "add")
                                                    mensaje = u"Su asistencia no ha sido registrada porque no tiene asignado grupo de practica. Favor contactarse con director/a de carrera."
                                                    lista = ['gestionacademica@unemi.edu.ec',
                                                             'planificacionacademica@unemi.edu.ec',
                                                             'kromanc1@unemi.edu.ec',]
                                                    send_html_mail("Estudiante si grupo de práctica",
                                                                   "alu_horarios/emails/notificacion_sin_grupo_practica.html",
                                                                   {'sistema': request.session['nombresistema'],
                                                                    'persona': persona,
                                                                    'inscripcion': inscripcion,
                                                                    'clase': clase,
                                                                    't': miinstitucion(),
                                                                    }, lista, [],
                                                                   cuenta=CUENTAS_CORREOS[0][1])
                                                    return JsonResponse({"result": "ok", "isWait": False, "mensaje": mensaje, "label_color": "warning"})
                        if asistencias.values("id").filter(asistio=False, virtual=False).exists():
                            asistencialeccion = asistencias.filter(asistio=False, virtual=False)[0]
                            if disponible:
                                asistencialeccion.asistio = True
                                asistencialeccion.virtual = True
                                asistencialeccion.virtual_fecha = hoy
                                asistencialeccion.virtual_hora = horaactual
                                asistencialeccion.ip_public = ip_public
                                asistencialeccion.browser = navegador
                                asistencialeccion.ops = ops
                                asistencialeccion.screen_size = screen_size
                                asistencialeccion.save(request)
                                if variable_valor('ACTUALIZA_ASISTENCIA'):
                                    if not asistencialeccion.materiaasignada.sinasistencia:
                                        ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                                mensaje = u"Su asistencia ha sido registrada exitosamente."
                                label_color = 'success'
                                log(u'Adiciono asistencia en la clase: %s. Durante el tiempo establecido' % clase, request, "add")
                            elif disponible_hora:
                                asistencialeccion.asistio = False
                                asistencialeccion.virtual = True
                                asistencialeccion.virtual_fecha = hoy
                                asistencialeccion.virtual_hora = horaactual
                                asistencialeccion.ip_public = ip_public
                                asistencialeccion.browser = navegador
                                asistencialeccion.ops = ops
                                asistencialeccion.screen_size = screen_size
                                asistencialeccion.save(request)
                                if variable_valor('ACTUALIZA_ASISTENCIA'):
                                    if not asistencialeccion.materiaasignada.sinasistencia:
                                        ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                                mensaje = f"Su asistencia no se ha registrado, usted ha ingresado a clases a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                                label_color = 'warning'
                                log(u'Ingresa a la clase pero no se adiciono asistencia: %s. Debe informar al docente' % clase, request, "add")
                        elif asistencias.values("id").filter(asistio=True, virtual=False).exists():
                            asistencialeccion = asistencias.filter(asistio=True, virtual=False)[0]
                            asistencialeccion.virtual = True
                            asistencialeccion.virtual_fecha = hoy
                            asistencialeccion.virtual_hora = horaactual
                            asistencialeccion.ip_public = ip_public
                            asistencialeccion.browser = navegador
                            asistencialeccion.ops = ops
                            asistencialeccion.screen_size = screen_size
                            asistencialeccion.save(request)
                            if variable_valor('ACTUALIZA_ASISTENCIA'):
                                if not asistencialeccion.materiaasignada.sinasistencia:
                                    ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                            mensaje = u"Su asistencia ya fue registrada por el/la profesor/a."
                            label_color = 'warning'
                            log(u'Ingresa a la clase su asistencia ya fue registrada previamente: %s.' % clase, request, "add")
                        elif asistencias.values("id").filter(asistio=False, virtual=True).exists():
                            mensaje = f"Su asistencia no se ha registrado, usted ha ingresado a clases a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                            label_color = 'warning'
                            log(u'Ingresa a la clase y su asistencia no se ha registrado por motivo de ingreso tarde: %s.' % clase, request, "add")
                        else:
                            mensaje = u"Su asistencia ya ha sido registrada con anterioridad."
                            label_color = 'success'
                        asistencia = asistencias[0]
                        logingreso = LogIngresoAsistenciaLeccion(asistencia=asistencia,
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
                        # logingreso.actualizar(request)
                        log(u'Dio click en el botón en horario para ingresar en la clase: %s' % logingreso, request, "add")
                        isWait = False
                return JsonResponse({"result": "ok", "isWait": isWait, "mensaje": mensaje, "label_color": label_color})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:

        if 'action' in request.GET:
            action = request.GET['action']

            HttpResponseRedirect("/")
        else:
            try:
                data['title'] = u'Horario de estudiante'
                if not periodo:
                    raise NameError(u"No tiene periodo asignado.")
                matricula = inscripcion.mi_matricula_periodo(periodo.id)
                if not matricula:
                    raise NameError(u"Ud. no se encuentra matriculado")
                # ePeriodoAcademia = None
                # if PeriodoAcademia.objects.values("id").filter(periodo=periodo, status=True).exists():
                #     ePeriodoAcademia = PeriodoAcademia.objects.filter(periodo=periodo, status=True)[0]
                data['ePeriodoAcademia'] = ePeriodoAcademia
                data['matricula'] = matricula
                data['inscripcion'] = inscripcion = matricula.inscripcion
                data['mi_malla'] = inscripcion.mi_malla()
                data['minivel'] = inscripcion.mi_nivel().nivel
                data['fichasocioeconomicainec'] = persona.fichasocioeconomicainec()
                return render(request, "alu_horarios/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "alu_horarios/error.html", data)



def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
