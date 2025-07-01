import os

import sys
from random import random

from django.http import HttpResponse
import sys


SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")


application = get_wsgi_application()


from sga.models import PersonaDatosFamiliares, PerfilUsuario, Persona
from sga.templatetags.sga_extras import encrypt
from datetime import datetime, timedelta
from sga.tasks import send_html_mail
import sys
import zipfile

from openpyxl import workbook as openxl
from openpyxl.chart import ScatterChart, Reference, Series,PieChart, BarChart
from openpyxl.styles import Font as openxlFont
from openpyxl.styles.alignment import Alignment as alin

from xlwt import *

from sga.funciones import notificacion

import xlwt
from xlwt import *
from django.http import HttpResponse

response = HttpResponse(content_type="application/ms-excel")
response['Content-Disposition'] = 'attachment; filename=reporte.xls'
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
estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
nombre = "Lista" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
filename = os.path.join(output_folder, nombre)
columns = [
            (u"N°", 2000),
            (u"PERSONA", 9000),
            (u"CÉDULA", 4000),
            (u"HIJO/A", 7000),
            (u"FECHA NACIMIENTO", 10000),
            (u"", 10000),
        ]
row_num = 3
for col_num in range(len(columns)):
    ws.write(row_num, col_num, columns[col_num][0], font_style)
    ws.col(col_num).width = columns[col_num][1]
row_num = 4
personas=PersonaDatosFamiliares.objects.filter(status=True)
for persona in personas:
    if persona.es_administrativo() or persona.es_profesor():
        for familiar in familiares:
            print(familiar.nacimiento)
            numero += 1
        ws.write(row_num, 0, u'%s' % l.profesor, font_style2)
        ws.write(row_num, 1, u'%s' % l.revisor, font_style2)
        ws.write(row_num, 2, u'%s' % l.materia, font_style2)
        ws.write(row_num, 3, u'%s' % l.deber, font_style2)
        ws.write(row_num, 4, u'%s' % l.estudiantes, font_style2)
        ws.write(row_num, 5, u'%s' % l.hora(), font_style2)
        ws.write(row_num, 6, u'%s' % l.horaminima(), font_style2)
        ws.write(row_num, 7, u'%s' % l.horamaxima(), font_style2)
        row_num+=1
        print('%s' % (l))
wb.save(filename)
print("FIN: ", filename)


def reporte_hijos():
    try:
        fecha = datetime.strptime("2015-01-01", '%Y-%m-%d').date()
        fecha2 = datetime.strptime("2016-01-01", '%Y-%m-%d').date()
        __author__ = 'Unemi'
        title = easyxf(
            'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
        title2 = easyxf(
            'font: name Arial, color-index black, bold on , height 200; alignment: horiz centre')
        font_style = XFStyle()
        font_style.font.bold = True
        style1 = easyxf(num_format_str='D-MMM-YY')
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('Reporte de Solicitudes')
        ws.write_merge(0, 0, 0, 13, 'REPORTE', title)
        response = HttpResponse(content_type="application/ms-excel")
        response[
            'Content-Disposition'] = 'attachment; filename=Reporte.xls'

        columns = [
            (u"N°", 2000),
            (u"PERSONA", 9000),
            (u"CÉDULA", 4000),
            (u"HIJO/A", 7000),
            (u"FECHA NACIMIENTO", 10000),
            (u"", 10000),
        ]
        row_num = 2
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]


        mensaje = 'NO REGISTRA'
        row_num = 3
        numero = 0
        for persona in personas:
            if persona.es_administrativo() or persona.es_profesor():
                familiares=PersonaDatosFamiliares.objects.filter(persona=persona, nacimiento__gte=fecha, nacimiento__lte=fecha2)
                for familiar in familiares:
                    print(familiar.nacimiento)
                    numero += 1
                    ws.write(row_num, 0, numero, font_style2)
                    ws.write(row_num, 1, str(persona), font_style2)
                    ws.write(row_num, 2, persona.cedula, font_style2)
                    ws.write(row_num, 3, str(familiar).upper(), font_style2)
                    ws.write(row_num, 4, str(familiar.identificacion), font_style2)
                    ws.write(row_num, 5, str(familiar.nacimiento), font_style2)
                    row_num += 1
                    wb.save(response)
                    return response
    except Exception as ex:
        print(ex)

reporte_hijos()


