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
from sga.models import *
from sagest.models import *


def calcular_evaluaciondocente():
    try:
        listado=RespuestaEvaluacionAcreditacion.objects.filter(procesada=False, status=True)
        totales = listado.count()
        cuenta = 0
        if listado:
            for recorrelis in listado:
                cuenta = cuenta + 1
                listadores = RespuestaRubrica.objects.filter(respuestaevaluacion=recorrelis, status=True)
                for lrespuesta in listadores:
                    lrespuesta.valor = lrespuesta.actualizar_valor()
                    lrespuesta.save()

                recorrelis.procesada=True
                recorrelis.valortotaldocencia = recorrelis.calcula_valor_total_docencia()
                recorrelis.valortotalinvestigacion = recorrelis.calcula_valor_total_investigacion()
                recorrelis.valortotalgestion = recorrelis.calcula_valor_total_gestion()
                recorrelis.save()
                print(str(cuenta) + ' de ' + str(totales))
        else:
            print('No existen registros a calcular evaluación docente')
    except Exception as ex:
        msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
        print(msg_ex)


calcular_evaluaciondocente()
