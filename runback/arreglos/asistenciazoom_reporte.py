#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

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
from sga.models import *

cont = 0
coordinaciones = Coordinacion.objects.filter(pk__in=[2, 3, 4, 5])
total = 0

import xlwt
from xlwt import *
from django.http import HttpResponse

response = HttpResponse(content_type="application/ms-excel")
response['Content-Disposition'] = 'attachment; filename=asistencias_alumnos.xls'
style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
style1 = easyxf(num_format_str='D-MMM-YY')
font_style = XFStyle()
font_style.font.bold = True
font_style2 = XFStyle()
font_style2.font.bold = False
wb = xlwt.Workbook()
ws = wb.add_sheet('Sheetname')
estilo = xlwt.easyxf(
    'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
output_folder = os.path.join(os.path.join(SITE_STORAGE, '../../media'))
nombre = "LISTADOFINAL" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
filename = os.path.join(output_folder, nombre)
columns = [(u"Id", 6000),(u"Materia Asignada", 6000),
           (u"Porcentaje materia asignada", 6000),
           (u"Porcentaje calculo", 6000),
           ]
row_num = 3
for col_num in range(len(columns)):
    ws.write(row_num, col_num, columns[col_num][0], font_style)
    ws.col(col_num).width = columns[col_num][1]
row_num = 4
for coordinacion in coordinaciones:
    for car in coordinacion.carreras():
        materia = Materia.objects.filter(nivel__periodo_id=113, asignaturamalla__malla__carrera=car).exclude(nivel__modalidad_id=3)
        for mat in materia:
            for asignadomateria in mat.asignados_a_esta_materia():
                asis = []
                nuevo = 0
                actual = 0
                por = 0
                if asignadomateria.asistencias_zoom_valida() > 0:
                    asistvalida = asignadomateria.asistencias_zoom_valida()
                    asistotal = asignadomateria.cantidad_asistencias_zoom()
                    asisfaltantes = asistotal - asistvalida
                    por = round(((asistvalida * 100) / asistotal), 0)
                    if por >= 69.5 and por < 70:
                        por = 70
                if asignadomateria.asistenciafinal != por:
                    print(u"%s" % asignadomateria, por)
                    ws.write(row_num, 0, u'%s' % asignadomateria.id, font_style2)
                    ws.write(row_num, 1, u'%s' % asignadomateria, font_style2)
                    ws.write(row_num, 2, u'%s' % asignadomateria.asistenciafinal, font_style2)
                    ws.write(row_num, 3, u'%s' % por, font_style2)
                    row_num += 1
wb.save(filename)

print("FIN: ", filename)






