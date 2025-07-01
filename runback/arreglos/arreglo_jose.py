#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

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


# print(u"Inicio")
#
# InscripcionActividadConvalidacionPPV.objects.filter(actividad__id__in= [590, 589,588,587,586,585]).delete()
# print(u"fin")
# try:
#     print(u"Inicio")
#
#     qs =InscripcionActividadConvalidacionPPV.objects.all().filter(status=True, actividad__periodo_id = 119)
#     print('Registros a procesar: {}'.format(qs.count()))
#     count = 0
#     for q in qs:
#          if not q.inscripcion.perfil_inscripcion():
#              actividad = ActividadConvalidacionPPV.objects.get(pk=q.actividad.id)
#              carreraid = actividad.carrera.all().values_list('id', flat=True)
#
#              print('Inscripción {} - {} - Actividad: {} con Id: {} '.format(q.inscripcion.persona, q.inscripcion.carrera.nombre, q.actividad.titulo, q.actividad.id))
#
#              # print(q)
#              qs2 = PerfilUsuario.objects.filter(persona = q.inscripcion.persona, inscripcion__carrera__in=carreraid)
#              for q2 in qs2:
#                  print('{} - {} - {}'.format(q2.persona, q2.inscripcion.carrera.nombre, q2.visible))
#
#
#     print('Total de respuestas procesadas: {}'.format(count))
# except Exception as ex:
#     print(ex)


#
# import xlwt
# from xlwt import *
# from django.http import HttpResponse
#
# response = HttpResponse(content_type="application/ms-excel")
# response['Content-Disposition'] = 'attachment; filename=reporte_moulos_ingles.xls'
# style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
# style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
# style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
# title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
# style1 = easyxf(num_format_str='D-MMM-YY')
# font_style = XFStyle()
# font_style.font.bold = True
# font_style2 = XFStyle()
# font_style2.font.bold = False
# wb = xlwt.Workbook()
# ws = wb.add_sheet('Sheetname')
# estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
# ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
# output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
# nombre = "Lista" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
# filename = os.path.join(output_folder, nombre)
# columns = [
#         (u"N°", 700),
#         (u"ID INSCRIPCIÓN°", 700),
#         (u"NOMBRE", 8300),
#         (u"CEDULA", 3500),
#         (u"CARRERA", 8300),
#         (u"ACTIVIDAD", 3500),
#         (u"ID ACTIVIDAD", 8300),
#         (u"VISIBLE", 9300),
#     ]
# row_num = 3
#
# for col_num in range(len(columns)):
#     ws.write(row_num, col_num, columns[col_num][0], font_style)
#     ws.col(col_num).width = columns[col_num][1]
# row_num = 4
# contador=1
#
# qs =InscripcionActividadConvalidacionPPV.objects.all().filter(status=True, actividad__periodo_id = 119)
# count = 0
# secuencia = 0
#
# for q in qs:
#          if not q.inscripcion.perfil_inscripcion():
#
#              secuencia += 1
#
#
#              actividad = ActividadConvalidacionPPV.objects.get(pk=q.actividad.id)
#              carreraid = actividad.carrera.all().values_list('id', flat=True)
#
#              # print('Inscripción {} - {} - Actividad: {} con Id: {} '.format(q.inscripcion.persona, q.inscripcion.carrera.nombre, q.actividad.titulo, q.actividad.id))
#              ws.write(row_num, 0, secuencia, font_style2)
#              ws.write(row_num, 1, u'%s' % q.inscripcion.id, font_style2)
#              ws.write(row_num, 2, u'%s' % q.inscripcion.persona, font_style2)
#              ws.write(row_num, 3, u'%s' % q.inscripcion.persona.cedula, font_style2)
#              ws.write(row_num, 4, u'%s' % q.inscripcion.carrera.nombre, font_style2)
#              ws.write(row_num, 5, u'%s' % q.actividad.titulo, font_style2)
#              ws.write(row_num, 6, u'%s' % q.actividad.id, font_style2)
#
#              # print(q)
#              qs2 = PerfilUsuario.objects.filter(persona = q.inscripcion.persona, inscripcion__carrera__in=carreraid)
#              for q2 in qs2:
#                  row_num += 1
#                  secuencia += 1
#                  ws.write(row_num, 0, secuencia, font_style2)
#                  ws.write(row_num, 1, u'%s' % q2.inscripcion.id, font_style2)
#                  ws.write(row_num, 2, u'%s' % q2.persona, font_style2)
#                  ws.write(row_num, 4, u'%s' % q2.inscripcion.carrera.nombre, font_style2)
#                  ws.write(row_num, 7, u'%s' % q2.visible, font_style2)
#
#                  # print('{} - {} - {}'.format(q2.persona, q2.inscripcion.carrera.nombre, q2.visible))
#              row_num += 1
#              print(u"%s - %s" % (secuencia, q.inscripcion.persona))
#
# wb.save(filename)
# print("FIN: ", filename)

# practica = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion__perfilusuario__visible=False)
# print('Inicio')
# for q2 in practica:
#     if InscripcionActividadConvalidacionPPV.objects.filter(status=True, inscripcion= q2.inscripcion).exists():
#         print('{} - {} - ESTADO: {} '.format(q2.inscripcion.persona, q2.inscripcion.carrera.nombre, q2.inscripcion))
# print('Fin')
#
# actividad = ActividadConvalidacionPPV.objects.filter(status = True, estado__in=[1, 2, 3, 4, 5, 7, 8], director=17496)
# row_num = 0
# for q2 in actividad:
#     row_num += 1
#     print('{} - {} - ID: {} - {} - {} - {} - ESTADO: {} '.format(row_num, q2.director, q2.director.id, q2.titulo, q2.periodo,  q2.carrera.all(), q2.estado))
#
# print('CANTIDAD: {} '.format(actividad.count()))
# print('FIN')

#
# #
# actividad = ActividadConvalidacionPPV.objects.filter(status = True, estado__in=[1, 2, 3, 4, 5, 7, 8], director=26936)
# person = Persona.objects.get(pk=17496)
# row_num = 0
# for q2 in actividad:
#     q2.director = person
#     q2.save()
#
# print('CANTIDAD: {} '.format(actividad.count()))
# print('FIN')

# actividad = ActividadConvalidacionPPV.objects.get(pk=33)
# person = Persona.objects.get(pk=26936)
#
# actividad.director = person
# actividad.save()
# print(actividad.director)
# print('FIN')

# import xlwt
# from xlwt import *
# from django.http import HttpResponse
#
# response = HttpResponse(content_type="application/ms-excel")
# response['Content-Disposition'] = 'attachment; filename=reporte_moulos_ingles.xls'
# style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
# style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
# style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
# title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
# style1 = easyxf(num_format_str='D-MMM-YY')
# font_style = XFStyle()
# font_style.font.bold = True
# font_style2 = XFStyle()
# font_style2.font.bold = False
# wb = xlwt.Workbook()
# ws = wb.add_sheet('Sheetname')
# estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
# ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
# output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
# nombre = "Actividad" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
# filename = os.path.join(output_folder, nombre)
# columns = [
#         (u"N°", 700),
#         (u"DIRECTOR CARRERA", 11000),
#         (u"DIRECTOR ID", 11000),
#         (u"ACTIVIDAD", 11000),
#         (u"ACTIVIDAD ID", 11000),
#         (u"LIDER", 11000),
#         (u"CARRERA", 11000),
#         (u"PERIODO", 11000),
#         (u"ESTADO", 11000)
#     ]
# row_num = 3
#
# for col_num in range(len(columns)):
#     ws.write(row_num, col_num, columns[col_num][0], font_style)
#     ws.col(col_num).width = columns[col_num][1]
# row_num = 4
# contador=1
#
# qs =ActividadConvalidacionPPV.objects.filter(status = True, estado__in=[1, 2, 3, 4, 5, 7, 8] , director=26936)
#
# count = 0
# secuencia = 0
#
# for q in qs:
#              secuencia += 1
#
#              # actividad = ActividadConvalidacionPPV.objects.get(pk=q.id)
#              # carreraid = actividad.carrera.all().values_list('name', flat=True)
#
#              # print('Inscripción {} - {} - Actividad: {} con Id: {} '.format(q.inscripcion.persona, q.inscripcion.carrera.nombre, q.actividad.titulo, q.actividad.id))
#              ws.write(row_num, 0, secuencia, font_style2)
#              ws.write(row_num, 1, u'%s' % q.director, font_style2)
#              ws.write(row_num, 2, u'%s' % q.director.id, font_style2)
#              ws.write(row_num, 3, u'%s' % q.titulo, font_style2)
#              ws.write(row_num, 4, u'%s' % q.id, font_style2)
#              ws.write(row_num, 5, u'%s' % q.profesor.persona, font_style2)
#              ws.write(row_num, 6, u'%s' % q.carrera.all(), font_style2)
#              ws.write(row_num, 7, u'%s' % q.periodo, font_style2)
#              ws.write(row_num, 8, u'%s' % q.get_estado_display(), font_style2)
#
#              row_num += 1
#              # print(u"%s - %s" % (secuencia, q.inscripcion.persona))
#
# wb.save(filename)
# print("FIN: ", filename)

# reque = InscripcionRequisitosActividadConvalidacionPPV.objects.filter(status = True, actividad__actividad__estado=1)
# for q2 in reque:
#     print(q2.actividad.actividad.profesor)

# print('INICIO')
# listagrupo = [13, 1]
# # administrativos = Administrativo.objects.all()
# # administrativos = administrativos.filter(activo=True, persona__usuario__groups__in=listagrupo).distinct()
#
# # certificados = CertificadoIdioma.objects.all()
# certificados = CertificadoIdioma.objects.filter(status = True,persona__usuario__groups__in=listagrupo )
#
# for q2 in certificados:
#     print(u"%s - %s" % (q2.persona, q2.persona.usuario.groups.name))
#
# print(certificados.query)
#
# print('FIN')

# def demo_unidad_integracion_curricular():
#     from bd.models import FuncionRequisitoIngresoUnidadIntegracionCurricular
#     from inno.models import RequisitoIngresoUnidadIntegracionCurricular
#     eRequisitos = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(malla_id=52)
#     inscripcion = Inscripcion.objects.get(pk=83876)
#     for eRequisito in eRequisitos:
#         print(eRequisito.run(29208))
#
#
# demo_unidad_integracion_curricular()

def reporte_integracion():
    asignaturas_curri = Materia.objects.filter(nivel__periodo_id=126, asignaturamalla__validarequisitograduacion = True, status=True)
    print(asignaturas_curri.query)
reporte_integracion()
