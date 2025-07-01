#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import sys
import os
import queue
import threading
import calendar
import json
import time
import redis as Redis
import xlsxwriter
from datetime import datetime, time, date, timedelta
# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from sagest.models import *
from inno.models import CalendarioRecursoActividadAlumno, CalendarioRecursoActividad,\
    CalendarioRecursoActividadAlumnoMotificacion
from bd.models import PeriodoCrontab
from django.db import transaction
from settings import DEBUG, HILOS_MAXIMOS
from wpush.models import SubscriptionInfomation
from webpush.models import SubscriptionInfo, PushInformation
from webpush.utils import _send_notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from ws.funciones import notificar_usuario_notificaciones


ahora = datetime.now()
manana = ahora + timedelta(days=1)
pasadomanana = ahora + timedelta(days=2)
fecha_hoy = ahora.date()
hora_hoy = ahora.time()
fecha_siguiente = manana.date()
hora_siguiente = manana.time()
fecha_pasado_siguiente = pasadomanana.date()
hora_pasado_siguiente = pasadomanana.time()
dia_semana_ahora = fecha_hoy.isoweekday()
dia_semana_manana = fecha_siguiente.isoweekday()
numerosemana = datetime.today().isocalendar()[1]


def segundos_a_segundos_minutos_y_horas(segundos):
    horas = int(segundos / 60 / 60)
    segundos -= horas*60*60
    minutos = int(segundos/60)
    segundos -= minutos*60
    # return datetime(ahora.year, ahora.month, ahora.day, horas, minutos, segundos).strftime("%H:%M:%S")
    return f"{int(horas):02d}:{int(minutos):02d}:{int(segundos):02d}"


def actualizar_estado_matricula(periodo):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de actualizar estado de matricula a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {periodo}")
    eMatriculas = Matricula.objects.filter(status=True, cerrada=False, nivel__periodo=periodo)
    if DEBUG:
        eMatriculas = eMatriculas.filter(inscripcion_id=104493)
    total = eMatriculas.count()
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(u"** Total: %s" % total)
    print(u"****************************************************************************************************")
    count = 1
    for eMatricula in eMatriculas:
        print(u"*** %s de %s" % (count, total))
        with transaction.atomic():
            try:
                print(u"*** Matricula (ID: %s - %s)" % (eMatricula.id, eMatricula))
                eMatricula.actualiza_matricula()
                print(u"*** Estado de matricula actualizado Matricula (ID: %s)" % eMatricula.id)
            except Exception as ex:
                print(u"*** Estado de matricula no actualizado Matricula (ID: %s)" % eMatricula.id)
                print(u"*** Error" % ex.__str__())
                transaction.set_rollback(True)
        count += 1
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de actualizar estado de matricula del periodo {periodo}")


def actualizar_nivel_inscripcion(periodo):
    def run(eInscripcion):
        with transaction.atomic():
            try:
                eInscripcion.actualizar_creditos()
                eInscripcion.actualizar_niveles_records()
                eInscripcion.actualizar_nivel(isCron=True)
                eInscripcion.save()
            except Exception as ex:
                transaction.set_rollback(True)
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de actualizar nivel de inscripción a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {periodo}")
    inscripciones = Inscripcion.objects.filter(matricula__nivel__periodo_id=periodo, matricula__retiradomatricula=False, matricula__status=True)
    if DEBUG:
        inscripciones = inscripciones.filter(pk=104493)
    graduados = Graduado.objects.filter(inscripcion_id__in=inscripciones.values_list("id", flat=True).distinct())
    egresados = Egresado.objects.filter(inscripcion_id__in=inscripciones.values_list("id", flat=True).distinct())
    inscripciones = inscripciones.exclude(id__in=graduados.values_list("inscripcion_id", flat=True).distinct())
    inscripciones = inscripciones.exclude(id__in=egresados.values_list("inscripcion_id", flat=True).distinct())
    total = inscripciones.count()
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(u"** Total: %s" % total)
    print(u"****************************************************************************************************")
    count = 1
    for inscripcion in inscripciones:
        eInscripcionNivel = inscripcion.mi_nivel()
        if eInscripcionNivel.fecha_modificacion:
            if eInscripcionNivel.fecha_modificacion_cron is None:
                run(inscripcion)
                print(f"Se actualizo estados del estudiante: {inscripcion.__str__()}")
            elif eInscripcionNivel.fecha_modificacion > eInscripcionNivel.fecha_modificacion_cron:
                run(inscripcion)
                print(f"Se actualizo estados del estudiante: {inscripcion.__str__()}")
        # print(inscripcion.id)
        print(u"*** %s de %s" % (count, total))
        count += 1
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de actualizar nivel de inscripción del periodo {periodo}")


def actualizar_nivel_matricula(periodo):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de actualizar nivel de matricula a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {periodo}")
    eMatriculas = Matricula.objects.filter(nivel__periodo_id=periodo, retiradomatricula=False, status=True)
    if DEBUG:
        eMatriculas = eMatriculas.filter(inscripcion_id=104493)
    total = eMatriculas.count()
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(u"** Total: %s" % total)
    print(u"****************************************************************************************************")
    count = 1
    for eMatricula in eMatriculas:
        with transaction.atomic():
            try:
                eMatricula.calcula_nivel()
            except Exception as ex:
                transaction.set_rollback(True)
        print(eMatricula)
        print(u"*** %s de %s" % (count, total))
        count += 1
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de actualizar nivel de matricula del periodo {periodo}")


def eliminar_lecciones_no_aperturada(periodo, fecha_hoy):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de eliminar lecciones no aperturadas a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {periodo}")
    # eProfesores = Profesor.objects.filter(profesormateria__materia__nivel__periodo=periodo, profesormateria__activo=True).distinct()
    # total_profesores = len(eProfesores)
    # contP = 1
    # for eProfesor in eProfesores:
    #     print(f"***** ({contP}/{total_profesores}) -> Profesor: {eProfesor.__str__()}")
    #     contP += 1
    # eLeccionGrupos = LeccionGrupo.objects.filter(status=False, fecha__lte=fecha_hoy, profesor=eProfesor, lecciones__clase__profesor=eProfesor, lecciones__fecha__lte=fecha_hoy)
    eLeccionGrupos = LeccionGrupo.objects.filter(status=False, fecha__lte=fecha_hoy, lecciones__fecha__lte=fecha_hoy, lecciones__clase__materia__nivel__periodo=periodo)
    with transaction.atomic():
        try:
            for eLeccionGrupo in eLeccionGrupos:
                eLecciones = eLeccionGrupo.lecciones.all()
                if eLecciones.values("id").filter(status=True).exists():
                    for eLeccion in eLecciones:
                        for eAsistenciaLeccion in eLeccion.asistencialeccion_set.all():
                            eAsistenciaLeccion.status = True
                            eAsistenciaLeccion.save()
                            eMateriaAsignada = eAsistenciaLeccion.materiaasignada
                            eMateriaAsignada.save(actualiza=True)
                        eLeccion.status = True
                        eLeccion.save()
                    eLeccionGrupo.status = True
                    eLeccionGrupo.save()
                else:
                    eLeccionGrupo.delete()
        except Exception as ex:
            transaction.set_rollback(True)
            print(f"Error al eliminar lección {ex.__str__()}")

    eLecciones = Leccion.objects.filter(status=False, fecha__lte=fecha_hoy, clase__materia__nivel__periodo=periodo)
    for eLeccion in eLecciones:
        with transaction.atomic():
            try:
                print(f"Elimina lección {eLeccion.__str__()}")
                eLeccion.delete()
            except Exception as ex:
                print(f"Error al eliminar lección {ex.__str__()}")
                transaction.set_rollback(True)
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de eliminar lecciones no aperturadas del periodo {periodo}")


def crear_lecciones(profesor, fecha, clases):
    puede_crear_clases = True
    for cl in clases:
        if cl.tipoprofesor.id in [2, 13] and cl.tipohorario in [1, 2, 8]:
            puede_crear_clases = False
            break
    if not puede_crear_clases:
        return False, "No existe clases a crear"
    with transaction.atomic():
        try:
            if LeccionGrupo.objects.values("id").filter(profesor=profesor, turno=clases[0].turno, fecha=fecha).exists():
                lecciongrupo = LeccionGrupo.objects.get(profesor=profesor, turno=clases[0].turno, fecha=fecha)
                lecciongrupo.status = False
                lecciongrupo.abierta = False
                lecciongrupo.turno = clases[0].turno
                lecciongrupo.aula = clases[0].aula
                lecciongrupo.dia = clases[0].dia
                lecciongrupo.fecha = fecha
                lecciongrupo.horaentrada = clases[0].turno.comienza
                lecciongrupo.horasalida = clases[0].turno.termina
                lecciongrupo.save()
            else:
                lecciongrupo = LeccionGrupo(profesor=profesor,
                                            turno=clases[0].turno,
                                            aula=clases[0].aula,
                                            dia=clases[0].dia,
                                            fecha=fecha,
                                            horaentrada=clases[0].turno.comienza,
                                            horasalida=clases[0].turno.termina,
                                            abierta=False,
                                            contenido='SIN CONTENIDO',
                                            estrategiasmetodologicas='SIN CONTENIDO',
                                            observaciones='SIN OBSERVACIONES',
                                            status=False
                                            )
                lecciongrupo.save()
            for cl in clases:
                if Leccion.objects.values("id").filter(clase=cl, fecha=fecha).exists():
                    leccion = Leccion.objects.get(clase=cl, fecha=fecha)
                    leccion.abierta = False
                    leccion.status = False
                    leccion.horaentrada = cl.turno.comienza
                    leccion.horasalida = cl.turno.termina
                    leccion.contenido = lecciongrupo.contenido
                    leccion.observaciones = lecciongrupo.observaciones
                    leccion.save()
                else:
                    leccion = Leccion(clase=cl,
                                      fecha=fecha,
                                      horaentrada=cl.turno.comienza,
                                      horasalida=cl.turno.termina,
                                      abierta=False,
                                      status=False,
                                      contenido=lecciongrupo.contenido,
                                      observaciones=lecciongrupo.observaciones
                                      )
                    leccion.save()
                if not lecciongrupo.lecciones.values("id").filter(pk=leccion.id).exists():
                    lecciongrupo.lecciones.add(leccion)
                materia = cl.materia
                asignados = materia.asignados_a_esta_materia()
                for materiaasignada in asignados:
                    if AsistenciaLeccion.objects.values("id").filter(leccion=leccion, materiaasignada=materiaasignada).exists():
                        asistencialeccion = AsistenciaLeccion.objects.filter(leccion=leccion, materiaasignada=materiaasignada)[0]
                        asistencialeccion.leccion = leccion
                        asistencialeccion.materiaasignada = materiaasignada
                        asistencialeccion.asistio = False
                        asistencialeccion.virtual = False
                        asistencialeccion.virtual_fecha = None
                        asistencialeccion.virtual_hora = None
                        asistencialeccion.ip_private = None
                        asistencialeccion.ip_public = None
                        asistencialeccion.browser = None
                        asistencialeccion.ops = None
                        asistencialeccion.screen_size = None
                        asistencialeccion.status = False
                    else:
                        asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                                              materiaasignada=materiaasignada,
                                                              asistio=False,
                                                              virtual=False,
                                                              virtual_fecha=None,
                                                              virtual_hora=None,
                                                              ip_private=None,
                                                              ip_public=None,
                                                              browser=None,
                                                              ops=None,
                                                              screen_size=None,
                                                              status=False,
                                                              )
                    asistencialeccion.save()
                    asistencialeccion
            lecciongrupo.save()
            return True, "Lección creada"
        except Exception as ex:
            transaction.set_rollback(True)
            return False, f"*** Error {ex.__str__()}"


def crear_lecciones_previa_al_dia(periodo, fecha_siguiente):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} de crear lecciones del día {DIAS_CHOICES[dia_semana_manana - 1][1]} del periodo {periodo}")
    fechas = [fecha_siguiente]
    ePeriodoAcademia = periodo.get_periodoacademia()
    for fecha in fechas:
        dia = (fecha.weekday() + 1)
        profesores = Profesor.objects.filter(profesormateria__materia__nivel__periodo=periodo, profesormateria__activo=True).distinct()
        # if DEBUG:
        #     profesores = profesores.filter(profesormateria__profesor_id__in=[3170])
        total_profesores = len(profesores)
        print("*** FECHA A PROCESAR: " + fecha.__str__() + "\r")
        contP = 1
        for profesor in profesores:
            numClass = 0
            print(f"***** ({contP}/{total_profesores}) -> Profesor: {profesor.__str__()}")
            contP += 1
            clases = Clase.objects.filter(activo=True, inicio__lte=fecha, fin__gte=fecha, dia=dia, status=True,
                                          materia__nivel__periodo=periodo,
                                          materia__nivel__periodo__visible=True,
                                          materia__nivel__periodo__visiblehorario=True,
                                          materia__fechafinasistencias__gte=fecha,
                                          materia__profesormateria__profesor_id=profesor.id,
                                          profesor_id=profesor.id,
                                          materia__profesormateria__tipoprofesor_id__in=[1, 2, 5, 7, 8, 10, 11, 12, 13, 14, 15,16],
                                          tipoprofesor_id__in=[1, 2, 5, 7, 8, 10, 11, 12, 13, 14, 15,16])
            # clases = clases.filter(turno__comienza__gte=time(6, 0, 0), turno__termina__lte=time(23, 59, 00))
            clases = clases.distinct()
            clases_turnos = profesor.extraer_clases_y_turnos_practica(fecha_siguiente, periodo)
            sesiones = Sesion.objects.filter(Q(turno__id__in=clases.values_list('turno__id').distinct())).distinct()
            clases = clases.filter(Q(pk__in=clases.values_list('id')) | Q(pk__in=clases_turnos[0].values_list('id'))).distinct()
            for sesion in sesiones:
                for turno in sesion.turnos_clasehorario(clases):
                    aux_clasesactuales = turno.horario_profesor_actual_horario(dia, profesor, periodo)
                    total_clases = len(aux_clasesactuales)
                    for cl in aux_clasesactuales:
                        contC = 1
                        print(f"******** ({contC}/{total_clases}) -> Clase: {cl.__str__()}")
                        fechacompara = cl.compararfecha(numerosemana)
                        tieneferiado = periodo.es_feriado(fechacompara, cl.materia)
                        coordinacion = cl.materia.coordinacion()
                        modalidad = cl.materia.asignaturamalla.malla.modalidad
                        if not tieneferiado:
                            if coordinacion.id in [1, 2, 3, 4, 5, 12, 9]:
                                if cl.tipohorario == 1:
                                    if aux_clasesactuales[0].tipoprofesor.id != 8:
                                        isSuccess, msg = crear_lecciones(profesor, fecha, turno.horario_profesor_actual_horario(dia, profesor, periodo, False, False))
                                        if isSuccess:
                                            contC += 1
                                            numClass += 1
                                        else:
                                            print(msg)
                                    # 2 => CLASE VIRTUAL SINCRÓNICA
                                    # 8 => CLASE REFUERZO SINCRÓNICA
                                    # 7 => CLASE VIRTUAL ASINCRÓNICA
                                    # 9 => CLASE REFUERZO ASINCRÓNICA
                                elif cl.tipohorario in [2, 7, 8, 9]:
                                    if modalidad:
                                        if modalidad.id in [1, 2]:
                                            if cl.tipohorario in [2, 8]:
                                                isSuccess, msg = crear_lecciones(profesor, fecha, turno.horario_profesor_actual_horario(dia, profesor, periodo, False, False))
                                                if isSuccess:
                                                    contC += 1
                                                    numClass += 1
                                                else:
                                                    print(msg)
                                        elif modalidad.id in [3]:
                                            if cl.tipohorario in [2, 8]:
                                                isSuccess, msg = crear_lecciones(profesor, fecha, turno.horario_profesor_actual_horario(dia, profesor, periodo, False, False))
                                                if isSuccess:
                                                    contC += 1
                                                    numClass += 1
                                                else:
                                                    print(msg)
                                            elif cl.tipohorario in [7, 9]:
                                                if cl.subirenlace:
                                                    clasesactualesasincronica = cl.horario_profesor_actualasincronica(numerosemana)
                                                    if not clasesactualesasincronica.values("id").exists():
                                                        isSuccess, msg = crear_lecciones(profesor, fecha, turno.horario_profesor_actual_horario(dia, profesor, periodo, False, False))
                                                        if isSuccess:
                                                            contC += 1
                                                            numClass += 1
                                                        else:
                                                            print(msg)

            print(f"***** (Se crearon {numClass} lecciones) -> Profesor: {profesor.__str__()}")


def notify_student_activities_admision(ePeriodo):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de notificar actividades de estudiantes a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {ePeriodo}")

    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de notificar actividades de estudiantes del periodo {ePeriodo}")


def notify_student_activities_pregrado(ePeriodo):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de notificar actividades de estudiantes a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {ePeriodo}")
    # calendario = calendar.Calendar()
    eActividades = CalendarioRecursoActividad.objects.filter(Q(fechahorahasta__date__lte=fecha_siguiente) |
                                                             Q(fechahorahasta__date__lte=fecha_pasado_siguiente),
                                                             fechahoradesde__date__gte=fecha_hoy,
                                                             materia__nivel__periodo=ePeriodo,
                                                             materia__status=True, materia__cerrado=False,
                                                             materia__nivel__cerrado=False,
                                                             materia__inicio__lte=fecha_hoy,
                                                             materia__fin__gte=fecha_hoy, status=True
                                                             )
    if DEBUG:
        eActividades = eActividades.filter(materia_id__in=MateriaAsignada.objects.values_list("materia_id", flat=True).filter(matricula_id__in=[472781, 464865]))
    totalActividades = len(eActividades)
    cotA = 0
    for eActividad in eActividades:
        cotA += 1
        print(f"{totalActividades}/{cotA} --> {eActividad.__str__()}")
        eMateria = eActividad.materia
        segundos = (eActividad.fechahorahasta - datetime.now()).total_seconds()
        SITE_URL_SIE = 'https://sgaestudiante.unemi.edu.ec'
        if DEBUG:
            SITE_URL_SIE = 'http://127.0.0.1:3000'
        url = f"{SITE_URL_SIE}/alu_documentos"
        titulo = f'Tiene una actividad: {eActividad.get_tipo_display()}'
        convertido = segundos_a_segundos_minutos_y_horas(segundos)
        tiempo = f"en {convertido}"
        cuerpo = f'Su actividad {eActividad.get_tipo_display()} fue aperturada desde {eActividad.fechahoradesde.strftime("%d-%m-%Y")} se cierra {tiempo} ({eActividad.fechahorahasta.strftime("%d-%m-%Y")} a las {eActividad.fechahorahasta.strftime("%H:%M")})'
        eAsignados = eMateria.asignados_a_esta_materia()
        if DEBUG:
            eAsignados = eAsignados.filter(matricula_id__in=[472781, 464865])
        for eMateriaAsignada in eAsignados:
            eInscripcion = eMateriaAsignada.matricula.inscripcion
            ePersona = eInscripcion.persona
            _eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno.objects.filter(materiaasignada=eMateriaAsignada, recurso=eActividad, status=True)
            if not _eCalendarioRecursoActividadAlumno.values("id").exists():
                eCalendarioRecursoActividadAlumno = CalendarioRecursoActividadAlumno(recurso=eActividad,
                                                                                     materiaasignada=eMateriaAsignada)
                eCalendarioRecursoActividadAlumno.save()
            else:
                eCalendarioRecursoActividadAlumno = _eCalendarioRecursoActividadAlumno[0]

            ePerfilUsuario = PerfilUsuario.objects.filter(status=True, persona=ePersona, inscripcion=eInscripcion, visible=True)

            #     else:
            eCalendarioRecursoActividadAlumnoMotificaciones = CalendarioRecursoActividadAlumnoMotificacion.objects.filter(actividadalumno=eCalendarioRecursoActividadAlumno)
            if not eCalendarioRecursoActividadAlumnoMotificaciones.values("id").exists():
                if ePerfilUsuario.values("id").exists():
                    eNotificacion = Notificacion(titulo=titulo,
                                                 cuerpo=cuerpo,
                                                 destinatario=ePersona,
                                                 perfil=ePerfilUsuario[0],
                                                 url=url,
                                                 prioridad=1,
                                                 app_label='SIE',
                                                 fecha_hora_visible=datetime.now() + timedelta(seconds=segundos),
                                                 tipo=1,
                                                 en_proceso=False,
                                                 content_type=ContentType.objects.get_for_model(eActividad),
                                                 object_id=eActividad.id,
                                                 )
                    eNotificacion.save()
                    if segundos <= 86400:
                        segundos_nueva = 86400
                    elif segundos > 86400 and segundos <= 172800:
                        segundos_nueva = 172800
                    else:
                        segundos_nueva = 259200
                    eCalendarioRecursoActividadAlumnoMotificacion = CalendarioRecursoActividadAlumnoMotificacion(notificacion=eNotificacion,
                                                                                                                 segundos=segundos_nueva,
                                                                                                                 actividadalumno=eCalendarioRecursoActividadAlumno)
                    eCalendarioRecursoActividadAlumnoMotificacion.save()
            else:
                for eCalendarioRecursoActividadAlumnoMotificacion in eCalendarioRecursoActividadAlumnoMotificaciones:
                    segundos_nueva = 0
                    if segundos <= 86400:
                        segundos_nueva = 86400
                    elif segundos > 86400 and segundos <= 172800:
                        segundos_nueva = 172800
                    elif segundos > 172800 and segundos <= 259200:
                        segundos_nueva = 259200

                    bandera = segundos_nueva > 0 and segundos_nueva < eCalendarioRecursoActividadAlumnoMotificacion.segundos
                    if DEBUG:
                        bandera = True
                    if bandera:
                        if ePerfilUsuario.values("id").exists():
                            eNotificacion = Notificacion(titulo=titulo,
                                                         cuerpo=cuerpo,
                                                         destinatario=ePersona,
                                                         perfil=ePerfilUsuario[0],
                                                         url=url,
                                                         prioridad=1,
                                                         app_label='SIE',
                                                         fecha_hora_visible=datetime.now() + timedelta(seconds=segundos),
                                                         tipo=1,
                                                         en_proceso=False,
                                                         content_type=ContentType.objects.get_for_model(eActividad),
                                                         object_id=eActividad.id,
                                                         )
                            eNotificacion.save()
                            # segundos_nueva = 86400
                            eCalendarioRecursoActividadAlumnoMotificacion = CalendarioRecursoActividadAlumnoMotificacion(notificacion=eNotificacion,
                                                                                                                         segundos=segundos_nueva,
                                                                                                                         actividadalumno=eCalendarioRecursoActividadAlumno)
                            eCalendarioRecursoActividadAlumnoMotificacion.save()

                subscriptions = ePersona.usuario.webpush_info.select_related("subscription")
                push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=2, status=True).select_related("subscription")
                for device in push_infos:
                    payload = {
                        "head": titulo,
                        "body": cuerpo,
                        "url": url,
                        "action": "loadNotifications",
                    }
                    try:
                        _send_notification(device.subscription, json.dumps(payload), ttl=500)
                    except Exception as exep:
                        print(f"Fallo de envio del push notification: {exep.__str__()}")

    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de notificar actividades de estudiantes del periodo {ePeriodo}")


def notify_student_activities_posgrado(ePeriodo):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de notificar actividades de estudiantes a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {ePeriodo}")

    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de notificar actividades de estudiantes del periodo {ePeriodo}")


def bloqueo_desbloqueo_matricula(ePeriodo):
    if ePeriodo.tipo_id in (1, 2):
        # eMatriculas = Matricula.objects.filter(status=True, bloqueomatricula=True, nivel__periodo=ePeriodo)
        eMatriculas = Matricula.objects.filter(status=True, retiradomatricula=False, nivel__periodo=ePeriodo).exclude(persona__usuario__is_superuser=True)
        for eMatricula in eMatriculas:
            with transaction.atomic():
                try:
                    # rubrospagados = eMatricula.rubro_set.values('id').filter(cancelado=True, status=True).count()
                    # rubrosdebe = eMatricula.rubro_set.values('id').filter(status=True).count()
                    # if rubrospagados == rubrosdebe:
                    eMatricula.bloqueomatricula = False
                    if eMatricula.estado_matricula == 1:
                        eMatricula.bloqueomatricula = True
                    eMatricula.save()
                    usermoodle = eMatricula.inscripcion.persona.usuario.username
                    if eMatricula.inscripcion.carrera.mi_coordinacion2() == 9:
                        cursor = connections['db_moodle_virtual'].cursor()
                    else:
                        cursor = connections['moodle_db'].cursor()
                    if cursor:
                        if usermoodle:
                            # Consulta en mooc_user
                            sql = """SELECT id FROM mooc_user WHERE username='%s'""" % (usermoodle)
                            cursor.execute(sql)
                            registro = cursor.fetchall()
                            if registro:
                                sql = """UPDATE mooc_user SET suspended=%s WHERE username='%s'""" % (1 if eMatricula.bloqueomatricula else 0, usermoodle)
                                cursor.execute(sql)
                except Exception as ex:
                    transaction.set_rollback(True)
                    print(f"Error en matricula: {eMatricula.__str__()} - Error: {ex.__str__()}")


class ProcesoBackGroundGestionarLecciones(threading.Thread):

    def __init__(self, ePeriodoCrontab, fecha_hoy, fecha_siguiente):
        self.ePeriodoCrontab = ePeriodoCrontab
        self.fecha_hoy = fecha_hoy
        self.fecha_siguiente = fecha_siguiente
        threading.Thread.__init__(self)

    def run(self):
        # ELIMINA LECCIONES PREVIA AL DÍA
        if ePeriodoCrontab.delete_lesson_previa:
            eliminar_lecciones_no_aperturada(ePeriodoCrontab.periodo, self.fecha_hoy)
        # CREA LECCIONES PREVIA AL DÍA
        if ePeriodoCrontab.create_lesson_previa:
            crear_lecciones_previa_al_dia(ePeriodoCrontab.periodo, self.fecha_siguiente)


class ProcesoBackGroundActualizarNivelInscripcion(threading.Thread):

    def __init__(self, periodo):
        self.periodo = periodo
        threading.Thread.__init__(self)

    def run(self):
        actualizar_nivel_inscripcion(self.periodo)


class ProcesoBackGroundBloqueoMatricula(threading.Thread):

    def __init__(self, periodo):
        self.periodo = periodo
        threading.Thread.__init__(self)

    def run(self):
        bloqueo_desbloqueo_matricula(self.periodo)


class ProcesoBackGroundNotificarActividadesEstudiante(threading.Thread):

    def __init__(self, ePeriodoCrontab):
        self.ePeriodoCrontab = ePeriodoCrontab
        threading.Thread.__init__(self)

    def run(self):
        ePeriodo = self.ePeriodoCrontab.periodo
        if self.ePeriodoCrontab.type == 1:
            notify_student_activities_admision(ePeriodo)
        elif self.ePeriodoCrontab.type == 2:
            notify_student_activities_pregrado(ePeriodo)
        elif self.ePeriodoCrontab.type == 3:
            notify_student_activities_posgrado(ePeriodo)


exitFlag = 0


class myThreadCronTab (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name + "\r")
        process_data(self.name, self.q)
        print("Exiting " + self.name + "\r")


def process_data(threadName, q):
    while not exitFlag:
        queueLock.acquire()
        if not workQueue.empty():
            ePeriodoCrontab = q.get()
            queueLock.release()
            print("%s PROCESANDO PERIODO %s" % (threadName, ePeriodoCrontab.periodo))
            # ACTUALIZAR ESTADO DE MATRICULA
            if ePeriodoCrontab.upgrade_state_enrollment:
                actualizar_estado_matricula(ePeriodoCrontab.periodo)
            # BLOQUEO DE MATRICULA
            if ePeriodoCrontab.bloqueo_state_enrollment:
                ProcesoBackGroundBloqueoMatricula(periodo=ePeriodoCrontab.periodo).start()
            # ACTUALIZAR NIVEL DE MATRICULA
            if ePeriodoCrontab.upgrade_level_enrollment:
                actualizar_nivel_matricula(ePeriodoCrontab.periodo)
            # ELIMINA LECCIONES PREVIA AL DÍA  O CREA LECCIONES PREVIA AL DÍA
            if ePeriodoCrontab.delete_lesson_previa or ePeriodoCrontab.create_lesson_previa:
                ProcesoBackGroundGestionarLecciones(ePeriodoCrontab, fecha_hoy, fecha_siguiente).start()
            # NOTIFICAR ACTIVIDADES DE ESTUDIANTES
            if ePeriodoCrontab.notify_student_activities:
                ProcesoBackGroundNotificarActividadesEstudiante(ePeriodoCrontab=ePeriodoCrontab).start()
            # ACTUALIZAR NIVEL DE INSCRIPCION
            if ePeriodoCrontab.upgrade_level_inscription:
                ProcesoBackGroundActualizarNivelInscripcion(periodo=ePeriodoCrontab.periodo).start()


        else:
            queueLock.release()


threadList = ["Thread-CronTab-"+str(id) for id in range(0, HILOS_MAXIMOS)]
nameList = range(0, 1000)
queueLock = threading.Lock()
workQueue = queue.Queue(PeriodoCrontab.objects.filter(status=True, is_activo=True).count())
threads = []
threadID = 1

# Create new threads
for tName in threadList:
    thread = myThreadCronTab(threadID, tName, workQueue)
    thread.start()
    threads.append(thread)
    threadID += 1


# Fill the queue
queueLock.acquire()
print(u"INICIO DEL PROCESO A CONSULTAR PERIODOS CRONTAB")
if PeriodoCrontab.objects.filter(status=True, is_activo=True):
    for ePeriodoCrontab in PeriodoCrontab.objects.filter(status=True, is_activo=True):
        workQueue.put(ePeriodoCrontab)
else:
    print(u"FIN DEL PROCESO A CONSULTAR PERIODOS CRONTAB -> NO SE ENCONTRO PERIODOS")
queueLock.release()

# Wait for queue to empty
while not workQueue.empty():
    pass

# Notify threads it's time to exit
exitFlag = 1

# Wait for all threads to complete
for t in threads:
    t.join()
print("HECHO" + datetime.now().__str__())
