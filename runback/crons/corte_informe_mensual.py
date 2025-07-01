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

from inno.models import CalendarioRecursoActividadAlumno, CalendarioRecursoActividad, \
    CalendarioRecursoActividadAlumnoMotificacion, InformeMensualDocente, HistorialInformeMensual
from bd.models import PeriodoCrontab
from django.db import transaction
from settings import DEBUG, HILOS_MAXIMOS
from wpush.models import SubscriptionInfomation
from webpush.models import SubscriptionInfo, PushInformation
from webpush.utils import _send_notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from ws.funciones import notificar_usuario_notificaciones
from sga.models import *
from sagest.models import *


def calcularPorcentajeInformeMensual():
    try:
        cron_activo = variable_valor('CRON_INFORME_MENSUAL')
        if cron_activo:
            id_periodo = variable_valor('ID_PERIODO_CRON_INFORME_MENSUAL')
            periodo = Periodo.objects.get(id=id_periodo)
            qsdistributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor__in=[214, 11, 268]).order_by('-id')
            for distributivo in qsdistributivo:
                profesor = distributivo.profesor
                count, count1, count2, count3, count4 = 0, 0, 0, 0, 0
                totalporcentaje, totalhdocentes, totalhinvestigacion, totalhgestion, totalhvinculacion = 0, 0, 0, 0, 0
                fechames = datetime.now().date()
                now = datetime.now()
                yearini = now.year
                year = now.year
                dayini = 1
                # month = now.month
                dia = int(now.day)
                if dia >= 28:
                    month = now.month
                    monthini = now.month
                else:
                    if int(now.month) == 1:
                        month = int(now.month)
                        monthini = int(now.month)
                    else:
                        month = int(now.month) - 1
                        monthini = int(now.month) - 1
                        if InformeMensualDocente.objects.filter(status=True, fechafin__year=now.year, fechafin__month=month, estado=4).values('id'):
                            month = now.month
                            monthini = now.month
                last_day = calendar.monthrange(year, month)[1]
                calendar.monthrange(year, month)
                start = date(yearini, monthini, dayini)
                fini = str(start.day) + '-' + str(start.month) + '-' + str(start.year)
                end = date(year, month, last_day)
                ffin = str(end.day) + '-' + str(end.month) + '-' + str(end.year)
                data = profesor.informe_actividades_mensual_docente_v4(periodo, fini, ffin, 'FACULTAD')
                print(f"Calculando: {profesor} {fini} - {ffin}")
                # DETALLE HORAS DOCENTES

                adicional_json = []
                # print(f'--------------DOCENTES--------------')
                horasdocencia = data['distributivo'].detalle_horas_docencia(data['fini'], data['ffin'])
                if horasdocencia:
                    dicDocencia = {'tipo': 'Horas Docencia'}
                    listDocencia = []
                    for actividad in horasdocencia:
                        if actividad.criteriodocenciaperiodo.nombrehtmldocente():
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'impartirclase':
                                totalimpartir = actividad.criteriodocenciaperiodo.totalimparticlase(data['distributivo'].profesor, data['fini'], data['ffin'], data['asignaturas'])
                                totitem1 = 0
                                if totalimpartir[0][0]:
                                    totitem1 += totalimpartir[0][2]
                                    totalhdocentes += totitem1
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem1))
                                    # print(f" 2 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem1}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'evidenciamoodle':
                                listadoevidencias = actividad.criteriodocenciaperiodo.horario_evidencia_moodle(data['distributivo'].profesor, data['finicresta'], data['ffincresta'])
                                totitem2 = 0
                                if listadoevidencias:
                                    if listadoevidencias[-1][11] == 4:
                                        pass
                                    else:
                                        totitem2 += listadoevidencias[-1][10]
                                        totalhdocentes += totitem2
                                        count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem2))
                                # print(f" 3 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem2}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'materialsilabo':
                                actividadhor = actividad.criteriodocenciaperiodo.horarios_actividad_profesor(data['distributivo'].profesor, data['fini'], data['ffin'])
                                totitem3 = 0
                                if actividadhor:
                                    totitem3 += actividadhor[-1][3]
                                    totalhdocentes += totitem3
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem3))
                                # print(f" 4 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem3}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'cursonivelacion':
                                actividadnivelacioncarrera = actividad.criteriodocenciaperiodo.horarios_nivelacioncarrera_profesor(data['distributivo'].profesor, data['fini'], data['ffin'])
                                totitem4 = 0
                                if actividadnivelacioncarrera:
                                    totitem4 += 100
                                    totalhdocentes += 100
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem4))
                                # print(f" 5 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem4}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'planificarcontenido':
                                contenidohor = actividad.criteriodocenciaperiodo.horarios_contenido_profesor(data['distributivo'].profesor, data['fini'], data['ffin'])
                                totitem5 = 0
                                if contenidohor:
                                    totitem5 += contenidohor[-1][3]
                                    totalhdocentes += totitem5
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem5))
                                # print(f" 6 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem5}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'tutoriaacademica':
                                tutoriasacademicas = actividad.criteriodocenciaperiodo.horarios_tutoriasacademicas_profesor(data['distributivo'].profesor, data['fini'], data['ffin'])
                                totitem6 = 0
                                if tutoriasacademicas:
                                    totitem6 += tutoriasacademicas[0][3]
                                    totalhdocentes += totitem6
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem6))
                                    # print(f" 7 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem6}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'seguimientoplataforma':
                                listadoseguimientos = actividad.criteriodocenciaperiodo.horario_seguimiento_tutor_fecha(data['distributivo'].profesor, data['fini'], data['ffin'])
                                totitem7 = 0
                                if listadoseguimientos:
                                    totitem7 += listadoseguimientos[-1][9]
                                    totalhdocentes += totitem7
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem7))
                                # print(f" 8 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem7}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'nivelacioncarrera':
                                actividadgestion = actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(data['distributivo'], data['fini'], data['ffin'])
                                totitem8 = 0
                                if actividadgestion.listadoevidencias:
                                    totitem8 += actividadgestion.listadoevidencias[-1][2]
                                    totalhdocentes += totitem8
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem8))
                                # print(f" 9 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem8}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'seguimientotransversal':
                                listadoseguimientos = actividad.criteriodocenciaperiodo.horario_seguimiento_transaversal_fecha(data['distributivo'].profesor, data['fini'], data['ffin'])
                                totitem9 = 0
                                if listadoseguimientos:
                                    totitem9 += listadoseguimientos[-1][9]
                                    totalhdocentes += totitem9
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem9))
                                # print(f" 10 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem9}")
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'apoyovicerrectorado':
                                actividadapoyo = actividad.criteriodocenciaperiodo.horarios_apoyo_profesor(data['distributivo'].profesor, data['fini'], data['ffin'])
                                totitem10 = 0
                                if actividadapoyo:
                                    totitem10 += 100
                                    totalhdocentes += 100
                                    count += 1
                                    listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem10))
                                # print(f" 12 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem10}")
                    dicDocencia['actividades'] = listDocencia
                    adicional_json.append(dicDocencia)
                # DETALLE HORAS DE INVESTIGACIÓN
                # print(f'--------------INVESTIGACIÓN--------------')
                if data['distributivo'].detalle_horas_investigacion():
                    docInvestigacion = {'tipo': 'Horas Investigación'}
                    listInvestigacion = []
                    for actividad in data['distributivo'].detalle_horas_investigacion():
                        if actividad.criterioinvestigacionperiodo.nombrehtmldocente():
                            if actividad.criterioinvestigacionperiodo.nombrehtmldocente() == 'actividadinvestigacion':
                                actividadgestion = actividad.criterioinvestigacionperiodo.horarios_informesinvestigacion_profesor(data['distributivo'], data['fini'], data['ffin'])
                                totitem11 = 0
                                if actividadgestion.listadoevidencias:
                                    totitem11 += actividadgestion.listadoevidencias[-1][2]
                                    totalhinvestigacion += actividadgestion.listadoevidencias[-1][2]
                                    count1 += 1
                                # print(f" 13 - {actividad.criterioinvestigacionperiodo.criterio}", f"{totitem11}")
                                    listDocencia.append((actividad.criterioinvestigacionperiodo.criterio.nombre, totitem11))
                    docInvestigacion['actividades'] = listInvestigacion
                    adicional_json.append(docInvestigacion)
                # DETALLE HORAS DE GESTIÓN
                # print(f'--------------GESTIÓN--------------')
                horasgestion = data['distributivo'].detalle_horas_gestion(data['fini'], data['ffin'])
                if horasgestion:
                    docGestion = {'tipo': 'Horas Gestión'}
                    listGestion = []
                    for actividad in horasgestion:
                        if actividad.criteriogestionperiodo.nombrehtmldocente():
                            if actividad.criteriogestionperiodo.nombrehtmldocente() == 'actividadgestion':
                                actividadgestion = actividad.criteriogestionperiodo.horarios_actividadgestion_profesor(data['distributivo'].profesor, data['fini'], data['ffin'])
                                totitem12 = 0
                                if actividadgestion:
                                    totitem12 += 100
                                    totalhgestion += 100
                                    count2 += 1
                                    listDocencia.append((actividad.criteriogestionperiodo.criterio.nombre, totitem12))
                                    # print(f" 14 - {actividad.criteriogestionperiodo.criterio}", f"{totitem12}")
                    docGestion['actividades'] = listGestion
                    adicional_json.append(docGestion)
                # DETALLE HORAS DE VINCULACIÓN
                # print(f'--------------VINCULACIÓN--------------')
                if data['distributivo'].detalle_horas_vinculacion():
                    docVinculacion = {'tipo': 'Horas Vinculacion'}
                    listVinculacion = []
                    for actividad in data['distributivo'].detalle_horas_vinculacion():
                        if actividad.criteriodocenciaperiodo.nombrehtmldocente():
                            if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'actividadvinculacion':
                                actividadgestion = actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(data['distributivo'], data['fini'], data['ffin'])
                                totitem13 = 0
                                if actividadgestion.listadoevidencias:
                                    totitem13 += actividadgestion.listadoevidencias[-1][2]
                                    totalhvinculacion += actividadgestion.listadoevidencias[-1][2]
                                    count3 += 1
                                    listVinculacion.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem13))

                                    # print(f" 16 - {actividad.criteriodocenciaperiodo.criterio}", f"{totitem13}")
                    docVinculacion['actividades'] = listVinculacion
                    adicional_json.append(docVinculacion)
                # TOTALES INFORME
                print(adicional_json)
                totalporcentaje = totalhdocentes + totalhinvestigacion + totalhgestion + totalhvinculacion
                count4 = count + count1 + count2 + count3
                total_porcentaje = round(totalporcentaje / count4 if count4 else totalporcentaje, 2)
                print(f"--- DOCENTES: {round(totalhdocentes / count if count else totalhdocentes, 2)}%")
                print(f"--- INVESTIGACIÓN: {round(totalhinvestigacion / count1 if count1 else totalhinvestigacion, 2)}%")
                print(f"--- GESTIÓN: {round(totalhgestion / count2 if count2 else totalhgestion, 2)}%")
                print(f"--- VINCULACIÓN: {round(totalhvinculacion / count3 if count3 else totalhvinculacion, 2)}%")
                print(f"--- TOTAL: {total_porcentaje}%")
                if not HistorialInformeMensual.objects.values('id').filter(distributivo=distributivo, status=True, fecha_creacion__month=now.month, fecha_creacion__year=now.year, fecha_creacion__day=now.day).exists():
                    instance = HistorialInformeMensual(distributivo=distributivo, finicioreporte=start, ffinreporte=end, total_porcentaje=total_porcentaje)
                    instance.datos_json = json.dumps(adicional_json, default=instance.json_serializable)
                    instance.save()
    except Exception as ex:
        msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
        print(msg_ex)


calcularPorcentajeInformeMensual()
