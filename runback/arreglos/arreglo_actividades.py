#!/usr/bin/env python
import csv
import os
import sys

import xlrd

from settings import USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA

# import urllib2
# Full path and name to your csv file
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
csv_filepathname3 = "problemas2021_corregido_g6.csv"
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

def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]),int(fecha[5:7]),int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()

def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha

matriculas = Matricula.objects.filter(nivel__periodo__id=112).order_by('-id')
cantidad = matriculas.count()
# cursor = connection.cursor()
for matricula in matriculas:
    print(matricula.id)
    print(cantidad)
    cantidad -= 1
    matricula.inscripcion.actualizar_nivel()
    matricula.calcula_nivel()
print('listo')
