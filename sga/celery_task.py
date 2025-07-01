# -*- coding: latin-1 -*-
import json
import os
import sys
from builtins import object
import threading

from django.db import transaction

from celery_setting import app
from sga.models import Materia, Notificacion, Periodo, Persona, SubirMatrizInscripcion, \
    ObservacionSubirMatrizInscripcion, HistorialSubirMatrizInscripcion, Carrera, Modalidad, Raza, Provincia, Canton, \
    Sede, Inscripcion, DocumentosDeInscripcion, Nivel, Sesion, Matricula, MateriaAsignada, \
    RegistroTareaSubirMatrizInscripcion
from sga.My_Model.SubirMatrizSENESCYT import My_SubirMatrizInscripcion, My_RegistroTareaSubirMatrizInscripcion, \
    My_ObservacionSubirMatrizInscripcion, My_HistorialSubirMatrizInscripcion, My_HistorialProcesoSubirMatrizInscripcion
from sga.My_Model.MatriculaPregrado import My_CarreraPregrado, My_MatriculaPregrado, My_ConfigMatriculacionPrimerNivel, \
    My_MatriculacionPrimerNivelCarrera
from clrncelery.models import BatchTasks
from celery.utils.log import get_task_logger
from openpyxl import load_workbook
# Celery-progress
# from celery_progress.backend import ProgressRecorder
from django.contrib.contenttypes.models import ContentType
from django.utils.crypto import get_random_string
from datetime import datetime, timedelta, date
import os, time, subprocess, re
from sga.funciones import log, convertir_fecha, puede_realizar_accion, puede_realizar_accion_afirmativo, \
    null_to_decimal, generar_nombre, fechatope, convertir_fecha_invertida, variable_valor, MiPaginador, \
    dia_semana_ennumero_fecha, null_to_numeric
from sga.funciones import cuenta_email_disponible
from sga.tasks import send_html_mail, conectar_cuenta

logger = get_task_logger(__name__)


# https://testdriven.io/blog/django-and-celery/
# http://blog.enriqueoriol.com/2014/06/integrando-celery-con-django-programar.html
# https://simpleisbetterthancomplex.com/tutorial/2017/08/20/how-to-use-celery-with-django.html
# http://nightdeveloper.net/celery-django/
# http://nightdeveloper.net/django-celery-4-0/


# @app.task
# def create_task(task_type):
#     print(f"INICIA PROCESO ")
#     time.sleep(int(task_type) * 10)
#     return True


# @app.task(name='process-close-subject', bind=True)
# def processCloseSubject(self, periodo_id, persona_id):
#     periodo = Periodo.objects.get(pk=periodo_id)
#     persona = Persona.objects.get(pk=persona_id)
#     tarea = BatchTasks(title='Proceso de cierre de actas',
#                        body='Correspondiente al periodo academico %s' % periodo.__str__(),
#                        person=persona,
#                        url=None,
#                        content_type=ContentType.objects.get(app_label='djcelery', model='taskmeta'),
#                        # object_id=celery_taskmeta[0][0],
#                        task_id=self.request.id,
#                        task_name='process-close-subject',
#                        app_label=1)
#     tarea.save(usuario_id=persona.usuario.id)
#     materias = Materia.objects.filter(nivel__periodo=periodo, cerrado=False).order_by('-id')
#     logger.info("EMPIEZA ACTUALIZAR MATERIAS %s" % materias.count())
#     for materia in materias:
#         materia.cerrado = True
#         materia.fechacierre = datetime.now().date()
#         materia.save(usuario_id=persona.usuario.id)
#         logger.info("ACTUALIZO MATERIA %s" % materia.__str__())
#         for asig in materia.asignados_a_esta_materia_aux():
#             asig.cerrado = True
#             asig.save(usuario_id=persona.usuario.id)
#             asig.actualiza_estado()
#             asig.cierre_materia_asignada()
#             logger.info("ACTUALIZO ASIGNATURA %s" % asig.__str__())
#     logger.info("ACTUALIZAR MATERIAS %s" % materias.count())
#     notificacion = Notificacion(titulo='Tiene un Proceso de Cierre de Materias',
#                                 cuerpo='Correspondiente al periodo academico %s' % periodo.__str__(),
#                                 destinatario=persona,
#                                 url=("/adm_tasks?id=%s" % str(tarea.id)),
#                                 content_type=ContentType.objects.get(app_label='clrncelery', model='batchtasks'),
#                                 object_id=tarea.id,
#                                 prioridad=2,
#                                 app_label='sga',
#                                 fecha_hora_visible=datetime.now() + timedelta(days=7),
#                                 )
#     notificacion.save(usuario_id=persona.usuario.id)
#
#     return 'Se realizó el cierre de actas de un total de %s' % materias.count()


# @app.task(name='process-matriz-senescyt', bind=True)
# def processMatrizSENESCYT(self, persona_id, matriz_id, periodo_id):
#     persona = Persona.objects.get(pk=persona_id)
#     matriz = My_SubirMatrizInscripcion.objects.get(pk=matriz_id)
#     periodo = Periodo.objects.get(pk=periodo_id)
#     matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, estado=4).update(estado=1)
#     print(f"INICIA PROCESO ")
#     tarea = BatchTasks(title='Proceso de subir matriz de SENESCYT',
#                        body='Correspondiente al periodo academico %s' % periodo.__str__(),
#                        person=persona,
#                        url=None,
#                        # content_type=ContentType.objects.get(app_label='djcelery', model='taskmeta'),
#                        # object_id=celery_taskmeta[0][0],
#                        task_id=self.request.id,
#                        task_name='process-matriz-senescyt',
#                        app_label=1)
#     tarea.save(usuario_id=persona.usuario.id)
#     registrio_tarea = My_RegistroTareaSubirMatrizInscripcion(matriz=matriz, tarea=tarea, content_type=None, object_id=None, proceso=1)
#     registrio_tarea.save(usuario_id=persona.usuario.id)
#     procesos = matriz.procesos()
#     for proceso in procesos:
#         siguiente_proceso = matriz.siguiente_proceso()
#         if not siguiente_proceso:
#             break
#         if proceso.id == siguiente_proceso.id:
#             if proceso.estado == 1 or proceso.estado == 3:
#                 logger.info("PROCESO DE CONSULTA DE BD ID:%s, de la ACCIÓN:%s" % (proceso.id, proceso.proceso.accion))
#                 print("PROCESO DE CONSULTA DE BD ID:%s, de la ACCIÓN:%s" % (proceso.id, proceso.proceso.accion))
#                 veProcess = False
#                 vrProcess = False
#                 if 'VALIDA_MATRIZ' == proceso.proceso.accion:
#                     vrProcess = matriz.validar_matriz_senescyt(proceso, persona)
#                     print("Validar matrizas")
#                     print(vrProcess)
#                     veProcess = True
#                 elif 'CREA_PERSONA' == proceso.proceso.accion:
#                     vrProcess = matriz.crear_persona_senescyt(proceso, persona)
#                     print("crear personas")
#                     print(vrProcess)
#                     veProcess = True
#                 elif 'CREA_INSCRIPCION' == proceso.proceso.accion:
#                     vrProcess = matriz.crear_inscripcion_senescyt(proceso, persona)
#                     veProcess = True
#                 elif 'CREA_PERFIL' == proceso.proceso.accion:
#                     vrProcess = matriz.crear_inscripcion_perfil_senescyt(proceso, persona)
#                     veProcess = True
#                 if veProcess:
#                     proceso.estado = 3 if not vrProcess else 2
#                     proceso.save(usuario_id=persona.usuario.id)
#                     if not vrProcess:
#                         break
#     total = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True).count()
#     total_success = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, estado=2).count()
#     if total == total_success:
#         matriz.estado = 2
#         matriz.save(usuario_id=persona.usuario.id)
#     notificacion = Notificacion(titulo='Tiene un Proceso de subir matriz de SENESCYT',
#                                 cuerpo='Correspondiente al periodo academico %s' % periodo.__str__(),
#                                 destinatario=persona,
#                                 url=("/adm_tasks?id=%s" % str(tarea.id)),
#                                 content_type=ContentType.objects.get(app_label='clrncelery', model='batchtasks'),
#                                 object_id=tarea.id,
#                                 prioridad=2,
#                                 app_label='sga',
#                                 fecha_hora_visible=datetime.now() + timedelta(days=1),
#                                 )
#     notificacion.save(usuario_id=persona.usuario.id)
#     return 'Se realizó el proceso de subir matriz de SENESCYT'
#

# @app.task(name='process-matricula-matriz-senescyt', bind=True)
# def processMatriculaMatrizSENESCYT(self, persona_id, matriz_id, periodo_id, carrera_id):
#     print("entra al proceso")
#     persona = Persona.objects.get(pk=persona_id)
#     matriz = My_SubirMatrizInscripcion.objects.get(pk=matriz_id)
#     periodo = Periodo.objects.get(pk=periodo_id)
#     title = body = ''
#     carrera = None
#     content_type = None
#     object_id = None
#     proceso = 0
#     if not carrera_id:
#         title = "Proceso de matriculación masivo matriz de SENESCYT"
#         body = 'Correspondiente al periodo academico %s' % periodo.__str__()
#         proceso = 2
#     else:
#         carrera = Carrera.objects.get(pk=carrera_id)
#         content_type = ContentType.objects.get_for_models(carrera)
#         content_type = ContentType.objects.get(app_label='sga', model='carrera')
#         object_id = carrera.id
#         proceso = 3
#         title = "Proceso de matriculación por carrera de la matriz de SENESCYT"
#         body = 'Correspondiente a la carrera %s y periodo academico %s' % (carrera.nombre, periodo.__str__())
#     tarea = BatchTasks(title=title,
#                        body=body,
#                        person=persona,
#                        url=None,
#                        # content_type=ContentType.objects.get(app_label='djcelery', model='taskmeta'),
#                        # object_id=celery_taskmeta[0][0],
#                        task_id=self.request.id,
#                        task_name='process-matricula-matriz-senescyt',
#                        app_label=1)
#     tarea.save(usuario_id=persona.usuario.id)
#     if not carrera:
#         registrio_tarea = My_RegistroTareaSubirMatrizInscripcion(matriz=matriz, tarea=tarea, proceso=proceso)
#     else:
#         registrio_tarea = My_RegistroTareaSubirMatrizInscripcion(matriz=matriz, tarea=tarea, content_type=content_type, object_id=object_id, proceso=proceso)
#     registrio_tarea.save(usuario_id=persona.usuario.id)
#     print("guarda la tarea")
#     if carrera:
#         vrProcess = matriz.matriculacion_senescyt(periodo, persona, carrera)
#     else:
#         vrProcess = matriz.matriculacion_senescyt(periodo, persona)
#
#     notificacion = Notificacion(titulo='Tiene un %s' % title,
#                                 cuerpo=body,
#                                 destinatario=persona,
#                                 url=("/adm_tasks?id=%s" % str(tarea.id)),
#                                 content_type=ContentType.objects.get(app_label='clrncelery', model='batchtasks'),
#                                 object_id=tarea.id,
#                                 prioridad=2,
#                                 app_label='sga',
#                                 fecha_hora_visible=datetime.now() + timedelta(days=1),
#                                 )
#     notificacion.save(usuario_id=persona.usuario.id)
#     return 'Se realizó el %s' % title


# @app.task(name='process-active-profiles-user', bind=True)
# def processActiveProfilesUser(self, persona_id, matriz_id, periodo_id, carrera_id):
#     print("entra al proceso")
#     persona = Persona.objects.get(pk=persona_id)
#     matriz = My_SubirMatrizInscripcion.objects.get(pk=matriz_id)
#     periodo = Periodo.objects.get(pk=periodo_id)
#     title = body = ''
#     carrera = None
#     content_type = None
#     object_id = None
#     if not carrera_id:
#         title = "Proceso de activar perfiles de usuarios de admisión masivo"
#         body = 'Correspondiente al periodo academico %s' % periodo.__str__()
#     else:
#         carrera = Carrera.objects.get(pk=carrera_id)
#         content_type = ContentType.objects.get_for_models(carrera)
#         content_type = ContentType.objects.get(app_label='sga', model='carrera')
#         object_id = carrera.id
#         title = "Proceso de activar perfiles de usuarios de admisión por carrera"
#         body = 'Correspondiente a la carrera %s y periodo academico %s' % (carrera.nombre, periodo.__str__())
#     tarea = BatchTasks(title=title,
#                        body=body,
#                        person=persona,
#                        url=None,
#                        # content_type=ContentType.objects.get(app_label='djcelery', model='taskmeta'),
#                        # object_id=celery_taskmeta[0][0],
#                        task_id=self.request.id,
#                        task_name='process-active-profiles-user',
#                        app_label=1)
#     tarea.save(usuario_id=persona.usuario.id)
#     print("guarda la tarea")
#     if carrera:
#         print(carrera)
#         matriz.activar_perfiles_usuarios_admision(periodo, persona, oCarrera=carrera)
#     else:
#         matriz.activar_perfiles_usuarios_admision(periodo, persona)
#     notificacion = Notificacion(titulo='Tiene un %s' % title,
#                                 cuerpo=body,
#                                 destinatario=persona,
#                                 url=("/adm_tasks?id=%s" % str(tarea.id)),
#                                 content_type=ContentType.objects.get(app_label='clrncelery', model='batchtasks'),
#                                 object_id=tarea.id,
#                                 prioridad=2,
#                                 app_label='sga',
#                                 fecha_hora_visible=datetime.now() + timedelta(days=1),
#                                 )
#     notificacion.save(usuario_id=persona.usuario.id)
#     return 'Se realizó el %s' % title


def processMatriculacionPrimerNivel(persona_id, periodoadmision_id, carreraadmision_id, periodopregrado_id, carrerapregrado_id):
    PrimerNivelMatriculacion(persona_id=persona_id,
                             periodoadmision_id=periodoadmision_id,
                             carreraadmision_id=carreraadmision_id,
                             periodopregrado_id=periodopregrado_id,
                             carrerapregrado_id=carrerapregrado_id,
                             ).start()


class PrimerNivelMatriculacion(threading.Thread):

    def __init__(self, persona_id, periodoadmision_id, carreraadmision_id, periodopregrado_id, carrerapregrado_id):
        self.persona_id = persona_id
        self.periodoadmision_id = periodoadmision_id
        self.carreraadmision_id = carreraadmision_id
        self.periodopregrado_id = periodopregrado_id
        self.periodopregrado_id = periodopregrado_id
        self.carrerapregrado_id = carrerapregrado_id
        threading.Thread.__init__(self)

    def run(self):
        persona = Persona.objects.get(pk=self.persona_id)
        periodoadmision = Periodo.objects.get(pk=self.periodoadmision_id)
        carreraadmision = My_CarreraPregrado.objects.get(pk=self.carreraadmision_id)
        periodopregrado = Periodo.objects.get(pk=self.periodopregrado_id)
        carrerapregrado = My_CarreraPregrado.objects.get(pk=self.carrerapregrado_id)
        # tarea = BatchTasks(title='Proceso de matriculacion primer nivel',
        #                    body='Correspondiente al periodo academico %s de la carrera %s' % (periodopregrado.__str__(), carrerapregrado.__str__()),
        #                    person=persona,
        #                    url=None,
        #                    content_type=ContentType.objects.get(app_label='djcelery', model='taskmeta'),
        #                    # object_id=celery_taskmeta[0][0],
        #                    task_id=self.request.id,
        #                    task_name='process-matriculacion-primer-nivel',
        #                    app_label=1)
        # tarea.save(usuario_id=persona.usuario.id)
        config = My_ConfigMatriculacionPrimerNivel.objects.get(periodoadmision=periodoadmision,
                                                               periodopregrado=periodopregrado)
        detalle = My_MatriculacionPrimerNivelCarrera.objects.get(configuracion=config, carreraadmision=carreraadmision,
                                                                 carrerapregrado=carrerapregrado)
        detalle.ejecutoaccion = True
        detalle.save(usuario_id=persona.usuario.id)
        with transaction.atomic():
            try:
                detalle.matricular_primer_nivel_by_carrera(persona)
                notificacion = Notificacion(titulo='Tiene un Proceso de matriculacion primer nivel',
                                            cuerpo='Correspondiente al periodo academico %s de la carrera %s' % (
                                                periodopregrado.__str__(), carrerapregrado.__str__()),
                                            destinatario=persona,
                                            url=("/niveles"),
                                            content_type=None,
                                            object_id=None,
                                            prioridad=2,
                                            app_label='sga',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            )
                notificacion.save(usuario_id=persona.usuario.id)
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                transaction.set_rollback(True)
                notificacion = Notificacion(titulo='Error en el proceso de matriculacion primer nivel',
                                            cuerpo=f"{ex.__str__()}",
                                            destinatario=persona,
                                            url=("/niveles"),
                                            content_type=None,
                                            object_id=None,
                                            prioridad=2,
                                            app_label='sga',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            )
                notificacion.save(usuario_id=persona.usuario.id)


class BackGroundProcessMatrizSENESCYT(threading.Thread):

    def __init__(self, persona_id, matriz_id, periodo_id, request):
        self.persona_id = persona_id
        self.matriz_id = matriz_id
        self.periodo_id = periodo_id
        self.request = request
        threading.Thread.__init__(self)

    def run(self):
        persona_id = self.persona_id
        matriz_id = self.matriz_id
        periodo_id = self.periodo_id
        request = self.request
        persona = Persona.objects.get(pk=persona_id)
        matriz = My_SubirMatrizInscripcion.objects.get(pk=matriz_id)
        periodo = Periodo.objects.get(pk=periodo_id)
        matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, estado=4).update(estado=1)
        print(f"INICIA PROCESO ")
        tarea = BatchTasks(title='Proceso de subir matriz de SENESCYT',
                           body='Correspondiente al periodo academico %s' % periodo.__str__(),
                           person=persona,
                           url=None,
                           # content_type=ContentType.objects.get(app_label='djcelery', model='taskmeta'),
                           # object_id=celery_taskmeta[0][0],
                           # task_id=self.request.id,
                           task_name='process-matriz-senescyt',
                           app_label=1)
        if request:
            tarea.save(request)
        else:
            tarea.save()
        registrio_tarea = My_RegistroTareaSubirMatrizInscripcion(matriz=matriz, tarea=tarea, content_type=None, object_id=None, proceso=1)
        if request:
            registrio_tarea.save(request)
        else:
            registrio_tarea.save()

        procesos = matriz.procesos()
        for proceso in procesos:
            siguiente_proceso = matriz.siguiente_proceso()
            if not siguiente_proceso:
                break
            if proceso.id == siguiente_proceso.id:
                if proceso.estado == 1 or proceso.estado == 3:
                    logger.info("PROCESO DE CONSULTA DE BD ID:%s, de la ACCIÓN:%s" % (proceso.id, proceso.proceso.accion))
                    print("PROCESO DE CONSULTA DE BD ID:%s, de la ACCIÓN:%s" % (proceso.id, proceso.proceso.accion))
                    veProcess = False
                    vrProcess = False
                    if 'VALIDA_MATRIZ' == proceso.proceso.accion:
                        vrProcess = matriz.validar_matriz_senescyt(proceso, persona)
                        print("Validar matrizas")
                        print(vrProcess)
                        veProcess = True
                    elif 'CREA_PERSONA' == proceso.proceso.accion:
                        vrProcess = matriz.crear_persona_senescyt(proceso, persona)
                        print("crear personas")
                        print(vrProcess)
                        veProcess = True
                    elif 'CREA_INSCRIPCION' == proceso.proceso.accion:
                        vrProcess = matriz.crear_inscripcion_senescyt(proceso, persona)
                        veProcess = True
                    elif 'CREA_PERFIL' == proceso.proceso.accion:
                        vrProcess = matriz.crear_inscripcion_perfil_senescyt(proceso, persona)
                        veProcess = True
                    if veProcess:
                        proceso.estado = 3 if not vrProcess else 2
                        proceso.save(request)
                        if not vrProcess:
                            break
        total = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True).count()
        total_success = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, estado=2).count()
        if total == total_success:
            matriz.estado = 2
            if request:
                matriz.save(request)
            else:
                matriz.save()
        notificacion = Notificacion(titulo='Tiene un Proceso de subir matriz de SENESCYT',
                                    cuerpo='Correspondiente al periodo academico %s' % periodo.__str__(),
                                    destinatario=persona,
                                    url=("/adm_tasks?id=%s" % str(tarea.id)),
                                    content_type=ContentType.objects.get(app_label='clrncelery', model='batchtasks'),
                                    object_id=tarea.id,
                                    prioridad=2,
                                    app_label='sga',
                                    fecha_hora_visible=datetime.now() + timedelta(days=1),
                                    )
        if request:
            notificacion.save(request)
        else:
            notificacion.save()
        print('Se realizó el proceso de subir matriz de SENESCYT')


class BackGroundProcessAdmision(threading.Thread):

    def __init__(self, persona_id, matriz_id, periodo_id, request):
        self.persona_id = persona_id
        self.matriz_id = matriz_id
        self.periodo_id = periodo_id
        self.request = request
        threading.Thread.__init__(self)

    def run(self):
        persona_id = self.persona_id
        matriz_id = self.matriz_id
        periodo_id = self.periodo_id
        request = self.request
        persona = Persona.objects.get(pk=persona_id)
        matriz = My_SubirMatrizInscripcion.objects.get(pk=matriz_id)
        periodo = Periodo.objects.get(pk=periodo_id)
        matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, estado=4).update(estado=1)
        print(f"INICIA PROCESO ")
        tarea = BatchTasks(title='Proceso de subir matriz de SENESCYT',
                           body='Correspondiente al periodo academico %s' % periodo.__str__(),
                           person=persona,
                           url=None,
                           # content_type=ContentType.objects.get(app_label='djcelery', model='taskmeta'),
                           # object_id=celery_taskmeta[0][0],
                           # task_id=self.request.id,
                           task_name='process-matriz-senescyt',
                           app_label=1)
        if request:
            tarea.save(request)
        else:
            tarea.save()
        registrio_tarea = My_RegistroTareaSubirMatrizInscripcion(matriz=matriz, tarea=tarea, content_type=None, object_id=None, proceso=1)
        if request:
            registrio_tarea.save(request)
        else:
            registrio_tarea.save()
        procesos = matriz.procesos()
        for proceso in procesos:
            siguiente_proceso = matriz.siguiente_proceso()
            if not siguiente_proceso:
                break
            if proceso.id == siguiente_proceso.id:
                if proceso.estado == 1 or proceso.estado == 3:
                    logger.info("PROCESO DE CONSULTA DE BD ID:%s, de la ACCIÓN:%s" % (proceso.id, proceso.proceso.accion))
                    print("PROCESO DE CONSULTA DE BD ID:%s, de la ACCIÓN:%s" % (proceso.id, proceso.proceso.accion))
                    veProcess = False
                    vrProcess = False
                    if 'VALIDA_MATRIZ' == proceso.proceso.accion:
                        vrProcess = matriz.validar_matriz_senescyt(proceso, persona)
                        print("Validar matriz")
                        print(vrProcess)
                        veProcess = True
                    elif 'CREA_PERSONA' == proceso.proceso.accion:
                        vrProcess = matriz.crear_persona_senescyt(proceso, persona)
                        print("crear personas")
                        print(vrProcess)
                        veProcess = True
                    elif 'CREA_INSCRIPCION' == proceso.proceso.accion:
                        vrProcess = matriz.crear_inscripcion_senescyt(proceso, persona)
                        veProcess = True
                    elif 'CREA_PERFIL' == proceso.proceso.accion:
                        vrProcess = matriz.crear_inscripcion_perfil_senescyt(proceso, persona)
                        veProcess = True
                    if veProcess:
                        proceso.estado = 3 if not vrProcess else 2
                        if request:
                            proceso.save(request)
                        else:
                            proceso.save()
                        if not vrProcess:
                            break
        total = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True).count()
        total_success = matriz.historialprocesosubirmatrizinscripcion_set.filter(status=True, estado=2).count()
        if total == total_success:
            matriz.estado = 2
            if request:
                matriz.save(request)
            else:
                matriz.save()
        notificacion = Notificacion(titulo='Tiene un Proceso de subir matriz de SENESCYT',
                                    cuerpo='Correspondiente al periodo academico %s' % periodo.__str__(),
                                    destinatario=persona,
                                    url=("/adm_tasks?id=%s" % str(tarea.id)),
                                    content_type=ContentType.objects.get(app_label='clrncelery', model='batchtasks'),
                                    object_id=tarea.id,
                                    prioridad=2,
                                    app_label='sga',
                                    fecha_hora_visible=datetime.now() + timedelta(days=1),
                                    )
        if request:
            notificacion.save(request)
        else:
            notificacion.save()
        print('Se realizó el proceso de subir matriz de SENESCYT')

