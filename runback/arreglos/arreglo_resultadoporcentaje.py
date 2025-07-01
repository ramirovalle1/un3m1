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
import xlwt
from django.http import HttpResponse
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
from setuptools.windows_support import hide_file
from urllib3 import request
from docx import Document
from xlwt import easyxf

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
from django.template import Context
from sga.models import *
from sagest.models import *
from datetime import date
from settings import PROFESORES_GROUP_ID

from sga.funciones import calculate_username, generar_usuario

from django.http import HttpResponse
from xlwt import *

try:
    __author__ = 'Unemi'
    title = easyxf('font: name Times New Roman, color-index black, bold on , height 220; alignment: horiz left')
    title2 = easyxf('font: name Verdana, color-index black, bold on , height 170; alignment: horiz left')
    fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
    fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalneg = easyxf('font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
    fuentenormalder = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
    fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str=' "$" #,##0.00')
    fuentemonedaneg = easyxf('font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25', num_format_str=' "$" #,##0.00')
    fuentenumero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    wb = Workbook(encoding='utf-8')
    # ws = wb.add_sheet('Listado')
#
    output_folder = os.path.join(os.path.join(SITE_STORAGE, '../../media', 'maestriainformes'))
    nombre = "listadoporcntajesmaterias" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
    filename = os.path.join(output_folder, nombre)
    hoy = datetime.now().date()
    listadoperiodo = Periodo.objects.filter(pk__in=[95,96,97,99], status=True)
    for lisper in listadoperiodo:
        ws = wb.add_sheet(lisper.nombre[0:23] + '_' + str(lisper.id))
        ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
        listadodistributivomaterias = Materia.objects.values_list('asignaturamalla__malla__carrera_id', 'asignaturamalla__malla__carrera__nombre').filter(nivel__periodo_id=lisper.id, status=True).distinct()
        row_num = 2

        columns = [
            (u"CODIGO", 2000),
            (u"CARRERA", 15000),
            (u"TOTAL PLANIFICADAS", 3000),
            (u"TOTAL CON DOCENTE", 3000),
            (u"PORCENTAJE", 3000),
            (u"TOTAL CON HORARIO", 3000),
            (u"PORCENTAJE HORARIO", 3000)
        ]
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        sumaporcentaje = 0
        sumaporcentajehorario = 0
        porcentajetotal = 0
        porcentajetotalhorario = 0
        for lista in listadodistributivomaterias:
            listaasignaturas = Materia.objects.values_list('id').filter(asignaturamalla__malla__carrera_id=lista[0], nivel__periodo_id=lisper.id, status=True)

            listaconprofesor = ProfesorMateria.objects.values_list('materia_id').filter(materia_id__in=listaasignaturas, status=True).exclude(profesor__persona__apellido1__icontains='DEFINIR').exclude(profesor__persona__apellido1__icontains='VIRTUAL').exclude(profesor__persona__apellido1__icontains='APELLIDOVIRT').exclude(profesor__persona__nombres__icontains='DEFINIR').exclude(profesor__persona__nombres__icontains='VIRTUAL').exclude(profesor__persona__apellido2__icontains='VIRTUAL').distinct()
            listaconhorario = Clase.objects.values_list('materia_id').filter(materia_id__in=listaasignaturas, status=True).distinct()

            row_num += 1
            campo1 = lista[0]
            campo2 = lista[1]
            campo3 = listaasignaturas.count()
            campo4 = listaconprofesor.count()
            campo5 = round((listaconprofesor.count() * 100) / listaasignaturas.count(),2)
            campo6 = listaconhorario.count()
            campo7 = round((listaconhorario.count() * 100) / listaasignaturas.count(),2)

            sumaporcentaje += campo5
            sumaporcentajehorario += campo7
            ws.write(row_num, 0, campo1)
            ws.write(row_num, 1, campo2, fuentenormalder)
            ws.write(row_num, 2, campo3, fuentenormalder)
            ws.write(row_num, 3, campo4, fuentenormalder)
            ws.write(row_num, 4, campo5, fuentenormalder)
            ws.write(row_num, 5, campo6, fuentenormalder)
            ws.write(row_num, 6, campo7, fuentenormalder)
        row_num += 2
        porcentajetotal = round((sumaporcentaje / listadodistributivomaterias.count()), 2)
        porcentajetotalhorario = round((sumaporcentajehorario / listadodistributivomaterias.count()), 2)
        ws.write(row_num, 0, '')
        ws.write(row_num, 1, '', fuentenormalder)
        ws.write(row_num, 2, '', fuentenormalder)
        ws.write(row_num, 3, '', fuentenormalder)
        ws.write(row_num, 4, porcentajetotal, fuentenormalder)
        ws.write(row_num, 5, '', fuentenormalder)
        ws.write(row_num, 6, porcentajetotalhorario, fuentenormalder)




        listadodistributivomateriascoordinacion = Materia.objects.values_list('asignaturamalla__malla__carrera__coordinacion__id', 'asignaturamalla__malla__carrera__coordinacion__nombre').filter( nivel__periodo_id=lisper.id, status=True).distinct()

        columns = [
            (u"CODIGO", 2000),
            (u"COORDINACION", 15000),
            # (u"TOTAL PLANIFICADAS", 3000),
            # (u"TOTAL CON DOCENTE", 3000),
            (u"PORCENTAJE", 3000),
            # (u"TOTAL CON HORARIO", 3000),
            (u"PORCENTAJE HORARIO", 3000)
        ]
        row_num += 1
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
            ws.col(col_num).width = columns[col_num][1]
        sumaporcentaje = 0
        porcentajetotal = 0
        for lista in listadodistributivomateriascoordinacion:
            row_num += 1
            listaasignaturascoor = Materia.objects.values_list('id').filter(asignaturamalla__malla__carrera__coordinacion__id=lista[0], nivel__periodo_id=lisper.id, status=True)
            listaconprofesorcoor = ProfesorMateria.objects.values_list('materia_id').filter(materia_id__in=listaasignaturascoor, status=True).exclude( profesor__persona__apellido1__icontains='DEFINIR').exclude(
                profesor__persona__apellido1__icontains='VIRTUAL').exclude(
                profesor__persona__apellido1__icontains='APELLIDOVIRT').exclude(
                profesor__persona__nombres__icontains='DEFINIR').exclude(
                profesor__persona__nombres__icontains='VIRTUAL').exclude(
                profesor__persona__apellido2__icontains='VIRTUAL').distinct()
            listaconhorariocoor = Clase.objects.values_list('materia_id').filter(materia_id__in=listaasignaturascoor, status=True).distinct()

            campo1 = lista[0]
            campo2 = lista[1]
            campo3 = listaasignaturascoor.count()
            campo4 = listaconprofesorcoor.count()
            campo5 = round((listaconprofesorcoor.count() * 100) / listaasignaturascoor.count(), 2)
            # campo6 = listaconhorario.count()
            campo7 = round((listaconhorariocoor.count() * 100) / listaasignaturascoor.count(), 2)
            #
            # sumaporcentaje += campo5
            #
            ws.write(row_num, 0, campo1)
            ws.write(row_num, 1, campo2, fuentenormalder)
            # ws.write(row_num, 2, campo3, fuentenormalder)
            # ws.write(row_num, 3, campo4, fuentenormalder)
            ws.write(row_num, 2, campo5, fuentenormalder)
            # ws.write(row_num, 5, campo6, fuentenormalder)
            ws.write(row_num, 3, campo7, fuentenormalder)

        wb.save(filename)
except Exception as ex:
    pass

