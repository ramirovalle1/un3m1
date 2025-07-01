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
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *
import openpyxl
import xlwt
from xlwt import *
from django.http import HttpResponse
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


def eliminar_todo(periodo):
    LogDeberes.objects.filter(periodo=periodo).delete()

def ejecutar_proceso(periodo):
    cursor = connections['moodle_db'].cursor()
    for materia in Materia.objects.filter(nivel__periodo=periodo, status=True, idcursomoodle__gt=0,
                                       asignaturamalla__malla__carrera__coordinacion__id__in=[1,2,3,4,5]):
        cursomoodle = materia.idcursomoodle
        profesor = materia.profesor_principal()
        revisor = None
        if materia.profesormateria_set.values('id').filter(status=True, activo=True, tipoprofesor__id=8).exists():
            revisor = materia.profesormateria_set.filter(status=True, activo=True, tipoprofesor__id=8)[0].profesor.persona
        estudiantes = materia.cantidad_matriculas_materia()
        sql = "SELECT b.name, u.idnumber FROM mooc_assign AS b INNER JOIN mooc_assign_grades AS c ON c.ASSIGNMENT=b.id " \
              " INNER JOIN mooc_user as u ON c.grader=u.id WHERE b.course="+ str(cursomoodle) +" GROUP by b.name, u.idnumber"
        cursor.execute(sql)
        results = cursor.fetchall()
        # cedula = ''
        for r in results:
            # if cedula != str(r[1]):
            #     cedula = str(r[1])
                # revisoraux = Persona.objects.filter(Q(cedula=str(r[1])) or Q(pasaporte=str(r[1])))
                # revisor = None
                # if revisoraux:
                #     revisor = revisoraux[0]
            sql1 = "SELECT TO_TIMESTAMP(c.timemodified) FROM mooc_assign AS b " \
            " INNER JOIN mooc_assign_grades AS c ON c.ASSIGNMENT=b.id WHERE b.course="+ str(cursomoodle) +" and b.name='"+ str(r[0]) +"' order by b.name, c.timemodified"
            cursor.execute(sql1)
            resultaux = cursor.fetchall()
            #esto me ayudara a sacar la desviacion estandar

            cantidad = resultaux.__len__()
            suma = 0
            i = 0
            acumulador = 0
            minimo = 500
            maximo = 0
            arreglo = []
            while i < cantidad-1:
                fecha = (resultaux[i][0]).date()
                tiempo = resultaux[i][0]
                tiemposiguiente = resultaux[i+1][0]
                i += 1
                restar = (tiemposiguiente - tiempo).seconds
                if restar <= 300:
                    acumulador = acumulador + restar
                else:
                    restar=300
                    acumulador = acumulador + restar
                if minimo > restar:
                    minimo = restar
                if maximo < restar:
                    maximo = restar
                arreglo.append(restar)
            # desviacionestandar = 0
            # try:
            #     desviacionestandar=int(round(stats.pstdev(arreglo),2))
            # except:
            #     raise
            # # desviacionestandar=0

            l = LogDeberes(periodo=periodo,
                           profesor=profesor,
                           revisor=revisor,
                           materia=materia,
                           deber=str(r[0]),
                           estudiantes=estudiantes,
                           tiempo=acumulador,
                           tiempominimo=minimo,
                           tiempomaximo=maximo,
                           fecha=fecha)
            l.save()
        print(materia)
    print("FIN")

def reporte_proceso(periodo):
    response = HttpResponse(content_type="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=tiempo_calificacion.xls'
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
    columns = [(u"Docente", 6000),
               (u"Revisor", 6000),
               (u"Materia", 6000),
               (u"Deber", 6000),
               (u"Matriculados", 6000),
               (u"Tiempo", 6000),
               (u"Tiempo mínimo", 6000),
               (u"Tiempo máximo", 6000),
               ]
    row_num = 3
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0], font_style)
        ws.col(col_num).width = columns[col_num][1]
    row_num = 4

    for l in LogDeberes.objects.filter(periodo=periodo):
        try:
            ws.write(row_num, 0, u'%s' % l.profesor, font_style2)
            ws.write(row_num, 1, u'%s' % l.revisor, font_style2)
            ws.write(row_num, 2, u'%s' % l.materia, font_style2)
            ws.write(row_num, 3, u'%s' % l.deber, font_style2)
            ws.write(row_num, 4, u'%s' % l.estudiantes, font_style2)
            ws.write(row_num, 5, u'%s' % l.hora(), font_style2)
            ws.write(row_num, 6, u'%s' % l.horaminima(), font_style2)
            ws.write(row_num, 7, u'%s' % l.horamaxima(), font_style2)
            row_num += 1
            print('%s' % (l.id))
        except Exception as ex:
            print('error: %s' % (ex))
            pass
    wb.save(filename)
    print("FIN: ", filename)
periodo = Periodo.objects.get(pk=119)
# eliminar_todo(periodo)
# ejecutar_proceso(periodo)
reporte_proceso(periodo)