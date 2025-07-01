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
# sys.path.append(your_djangoproject_home)
# os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *
from sagest.models import *
import csv

import openpyxl
try:
    miarchivo = openpyxl.load_workbook('kardex.xlsx')

    print('INICIO KARDEX')
    kardex = miarchivo.get_sheet_by_name('kardex')
    listakardex = kardex.rows
    count = 1
    for filas in listakardex[:]:
        id = filas[0].value
        saldoinicialvalor = filas[1].value
        saldoinicialcantidad = filas[2].value
        valor = filas[3].value
        saldofinalvalor = filas[4].value
        saldofinalcantidad = filas[5].value
        print(filas[0].value)
        if count >= 2:
            filtro = KardexInventario.objects.filter(pk=int(id))
            if filtro.exists():
                f = filtro.first()
                f.saldoinicialvalor = saldoinicialvalor
                f.saldoinicialcantidad = saldoinicialcantidad
                f.valor = valor
                f.saldofinalvalor = saldofinalvalor
                f.saldofinalcantidad = saldofinalcantidad
                f.save()
            print(count)
        count += 1

    print('INICIO SALIDA')
    salida = miarchivo.get_sheet_by_name('salida')
    listasalida = salida.rows
    countsalida = 1
    for filas in listasalida[:]:
        id = filas[0].value
        valor = filas[1].value
        print(filas[0].value)
        if countsalida >= 2:
            filtro = DetalleSalidaProducto.objects.filter(pk=int(id))
            if filtro.exists():
                f = filtro.first()
                f.valor = valor
                f.save()
            print(countsalida)
        countsalida += 1

    print('INICIO INGRESO')
    ingreso = miarchivo.get_sheet_by_name('ingreso')
    listaingreso = ingreso.rows
    countingreso = 1
    for filas in listaingreso[:]:
        id = filas[0].value
        total = filas[1].value
        print(filas[0].value)
        if countingreso >= 2:
            filtro = DetalleIngresoProducto.objects.filter(pk=int(id))
            if filtro.exists():
                f = filtro.first()
                f.total = total
                f.save()
            print(countingreso)
        countingreso += 1

    print('TOTAL KARDEX {}'.format(count))
    print('TOTAL INGRESO {}'.format(countingreso))
    print('TOTAL SALIDA {}'.format(countsalida))


except Exception as ex:
    print(ex)
    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))



