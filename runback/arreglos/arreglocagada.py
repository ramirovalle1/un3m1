#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
from xlwt import easyxf

from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, PROFESORES_GROUP_ID, \
    RESPONSABLE_BIENES_ID, ALUMNOS_GROUP_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA, \
    CLAVE_USUARIO_CEDULA, CHEQUEAR_CONFLICTO_HORARIO

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))



csv_filepathname2 = "egresadofalta.csv"

# your_djangoproject_home=os.path.split(SITE_ROOT)[0]
#
# sys.path.append(your_djangoproject_home)
# os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'



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

# from bib.models import *
# from med.models import *

# from sga.docentes import calculate_username
import csv

dataWriter = csv.writer(open(csv_filepathname2,'ab'), delimiter=';')
# dataReader = csv.reader(open(csv_filepathname,"rU"), delimiter=';')
# dataReader2 = csv.reader(open(csv_filepathname2,"rU"), delimiter=';')





import openpyxl
a = 0
miarchivo = openpyxl.load_workbook('cagada.xlsx')
lista = miarchivo.get_sheet_by_name('Hoja1')
totallista = lista.rows
for filas in totallista[:]:
    a += 1
    if a > 1:
        matricula = Matricula.objects.filter(pk=filas[0].value, status=True)
        bandera = False
        for materiaasignada in MateriaAsignada.objects.filter(matricula=matricula, materia__asignatura__id=filas[1].value).order_by('materia__paralelo'):
            materia = materiaasignada.materia
            if materia.materiaasignada_set.filter(status=True).count() <= 45:
                if bandera == False:
                    paralelo = materia.paralelo
                    bandera = True
        MateriaAsignada.objects.filter(matricula=matricula, materia__asignatura__id=filas[1].value).exclude(materia__paralelo=paralelo).delete()
    print(filas[0].value)
    print(a)



