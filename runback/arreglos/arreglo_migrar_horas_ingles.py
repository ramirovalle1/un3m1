#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import sys

import xlsxwriter
from django.db import transaction

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
import xlrd
from time import sleep
from med.funciones import actioncalculotestpsicologico
from med.models import *
from sga.models import *
from sagest.models import *
from Moodle_Funciones import *
from datetime import date
from settings import PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, NIVEL_MALLA_CERO, NIVEL_MALLA_UNO

horas = 100
year = 2019
coordinaciones = Coordinacion.objects.filter(pk__in=[1,2,3,4,5])
carreras = Carrera.objects.filter(status=True, coordinacion__in=coordinaciones)
mallasingles = Malla.objects.filter(pk__in=[353, 22]).distinct()
asignaturasingles = Asignatura.objects.filter(pk__in=AsignaturaMalla.objects.values_list('asignatura_id').filter(malla__in=mallasingles).distinct()).exclude(pk__in=[782])
inscripciones = Inscripcion.objects.filter(pk__in=RecordAcademico.objects.filter(inscripcion__inscripcionmalla__malla__in=Malla.objects.filter(inicio__year=year, carrera__in=carreras).exclude(pk__in=[215, 214, 198]), horas__lt=100, asignatura__in=asignaturasingles, aprobada=True).values_list('inscripcion_id', flat=True).distinct())
inscripciones = inscripciones.filter(inscripcionmalla__status=True, pk__in=inscripciones)
inscripciones = inscripciones.exclude(pk__in=PerfilUsuario.objects.filter(visible=False).values_list('inscripcion_id', flat=True).distinct())
#graduados = Graduado.objects.values_list('asignatura_id').filter(inscripcion__in=inscripciones).distinct()
#inscripciones = inscripciones.exclude(pk__in=graduados)
print("********************************************")
print("********************************************")
print("*********** TOTAL: %s" % inscripciones.count())
print("********************************************")
contador = 1
for inscripcion in inscripciones:
    print("*********** (%s) - %s" % (contador, inscripcion))
    records = inscripcion.recordacademico_set.filter(horas__lt=100, asignatura__in=asignaturasingles, aprobada=True)
    for record in records:
        print("************************************************** %s" % record.asignatura)
        record.horas = horas
        record.save()
    contador = contador +1
