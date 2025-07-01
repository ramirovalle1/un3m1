#!/usr/bin/env python
import os
import sys
import openpyxl
# import urllib2

# Full path and name to your csv file
import unicodedata
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record

import xlrd
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
from django.http import HttpResponse
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
from setuptools.windows_support import hide_file
from urllib3 import request
from docx import Document

from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, PROFESORES_GROUP_ID, \
    RESPONSABLE_BIENES_ID, ALUMNOS_GROUP_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA, \
    CLAVE_USUARIO_CEDULA, CHEQUEAR_CONFLICTO_HORARIO

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

# arregla hora semanal en materia
id_carreras = [76,24,22,94,77,81]
#
# for asi in AsignaturaMalla.objects.filter(malla__carrera__id__in=id_carreras):
#     horaaux = null_to_numeric(asi.horaspresencialessemanales,0)
#     if horaaux == 0:
#         AsignaturaMalla.objects.filter(pk=asi.id).update(horaspresencialessemanales=null_to_numeric((asi.horas/16),0))
#     print(asi)


for materia in Materia.objects.filter(nivel__periodo__id=82, asignaturamalla__malla__carrera_id__in=id_carreras):
    horamalla = null_to_numeric(materia.asignaturamalla.horaspresencialessemanales,0) + null_to_numeric(materia.asignaturamalla.horaspracticassemanales,0)
    Materia.objects.filter(pk=materia.id).update(horassemanales=horamalla)
    ProfesorMateria.objects.filter(materia=materia).update(hora=horamalla)
    print(materia.asignaturamalla)
    print(materia.horassemanales)

