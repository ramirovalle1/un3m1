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

# cambiar tipo contador en crai
# for registro in ContadorActividadesMundoCrai.objects.all():
#     persona = registro.usuario_creacion.persona_set.all()[0]
#     if persona.es_profesor():
#         registro.tipoingreso = 1
#     else:
#         registro.tipoingreso = 2
#     registro.save()
#     print(registro)
# print('listo')
# lista_nueva = []
# lista_semanas = []
# silabocab = Silabo.objects.get(materia_id=32968)
# for dia in daterange(silabocab.materia.inicio, silabocab.materia.fin):
#     if (dia.isocalendar()[1]) not in lista_nueva:
#         lista_nueva.append(dia.isocalendar()[1])
#         print(dia.isocalendar()[1])
# print(datetime.today() - timedelta(days=datetime.today().isoweekday() % 7))
# fech = datetime.today() - timedelta(days=datetime.today().isoweekday() % 7)
#
# print(fech.isocalendar()[2])
# print(timedelta(days=datetime.today().isoweekday() % 7))
# print(datetime.today().isocalendar()[2])
# from datetime import datetime, date, timedelta, time
# today = datetime.today()
# fechalunes = today + timedelta(days=-today.weekday())
# print(fechalunes)
# print(fechalunes.isocalendar()[2])
# print(datetime.strptime('2020-05-31', '%Y-%m-%d').date())
# fechas = datetime.strptime('2020-05-29', '%Y-%m-%d').date()
# modified_date = fechalunes + timedelta(days=7)
# print(modified_date)
# # print(modified_date.isocalendar()[2])
#
#
# for dia in daterange(fechalunes, modified_date):
#     print(dia.date())

# lista =[]
# print(len(list(lista)))


# programa = ProgramaAnaliticoAsignatura.objects.filter(fecha_creacion__year=2020,asignaturamalla__malla__carrera__modalidad=3, activo=True, status=True)
#
# for pro in programa:
#     asig = pro.asignaturamalla
#     if not AutorprogramaAnalitico.objects.filter(asignatura=pro.asignaturamalla.asignatura, programaanalitico=pro, periodo_id__in=[89,90,96,110], status=True):
#         autor = AutorprogramaAnalitico(autor_id=None,
#                                        asignatura=pro.asignaturamalla.asignatura,
#                                        programaanalitico=pro,
#                                        periodo_id=110)
#         autor.save()
#     else:
#         print('s')


# proinactivas = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla_id__in=[5125],programaanalitico__activo=False, status=True).exclude(programaanalitico__asignaturamalla__malla__carrera__coordinacion=9)
# proactivas = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla_id__in=[5125],programaanalitico__activo=True, status=True).exclude(programaanalitico__asignaturamalla__malla__carrera__coordinacion=9)
# # proinactivas = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla_id__in=[5171,5248,5146,5646,5116,5238,5121,5100,5681,5647,5274,5148,5190,5641,5682,8229,5173,5223,5103,5202,5101,5142,5644,5089,5104,5159,5751,5140,5209,5196,5125,5179,5107,5180,5136,5154,5333,5152,5133,5226,5332,5185,5137,5643,5194,5131,5147,5642,5268,5139,5122,5162], status=True).exclude(programaanalitico__asignaturamalla__malla__carrera__coordinacion=9)
# # proactivas = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla_id__in=[5171,5248,5146,5646,5116,5238,5121,5100,5681,5647,5274,5148,5190,5641,5682,8229,5173,5223,5103,5202,5101,5142,5644,5089,5104,5159,5751,5140,5209,5196,5125,5179,5107,5180,5136,5154,5333,5152,5133,5226,5332,5185,5137,5643,5194,5131,5147,5642,5268,5139,5122,5162], status=True).exclude(programaanalitico__asignaturamalla__malla__carrera__coordinacion=9)
# # pro = ProgramaAnaliticoAsignatura.objects.filter(asignaturamalla_id__in=[5171,5248,5146,5646,5116,5238,5121,5100,5681,5647,5274,5148,5190,5641,5682,8229,5173,5223,5103,5202,5101,5142,5644,5089,5104,5159,5751,5140,5209,5196,5125,5179,5107,5180,5136,5154,5333,5152,5133,5226,5332,5185,5137,5643,5194,5131,5147,5642,5268,5139,5122,5162], status=True).exclude(asignaturamalla__malla__carrera__coordinacion=9)
# a=0
# for proinac in proinactivas:
#     a=a+1
#     activascopiar = proactivas.get(programaanalitico__asignaturamalla_id=proinac.programaanalitico.asignaturamalla.id)
#     for conte in proinac.programaanalitico.contenido_program_analitico():
#         if conte.unidadresultadoprogramaanalitico_set.filter(status=True):
#             for uni in conte.unidades_seleccionadas():
#                 # query = UnidadResultadoProgramaAnalitico.objects.filter(descripcion__iexact=uni.descripcion.upper(),contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True,contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla,status=True)
#                 # print(query.query)
#                 if UnidadResultadoProgramaAnalitico.objects.filter(descripcion__iexact=uni.descripcion.upper(),contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True,contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla,status=True):
#                     unidadactiva = UnidadResultadoProgramaAnalitico.objects.filter(descripcion__iexact=uni.descripcion.upper(), contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True)
#
#                     # copia lo de unidades
#                     for videos in uni.videounidadresultadoprogramaanalitico_set.filter(status=True).order_by('orden'):
#                         if not VideoUnidadResultadoProgramaAnalitico.objects.filter(unidad=unidadactiva,descripcion=videos.descripcion, video=videos.video,  orden=videos.orden, estado=videos.estado, aprueba=videos.aprueba,observacion=videos.observacion, fechacambioestado=videos.fechacambioestado):
#                             vid = VideoUnidadResultadoProgramaAnalitico(unidad=unidadactiva,
#                                                                         descripcion=videos.descripcion,
#                                                                         video=videos.video,
#                                                                         orden=videos.orden,
#                                                                         estado=2,
#                                                                         aprueba=videos.aprueba,
#                                                                         observacion=videos.observacion,
#                                                                         fechacambioestado=videos.fechacambioestado)
#                             vid.save()
#                     # uni.recursounidadprogramaanalitico_set.filter(status=True).delete()
#                     for recursos in uni.recursounidadprogramaanalitico_set.filter(status=True).order_by('orden'):
#                         if not RecursoUnidadProgramaAnalitico.objects.filter(unidad=unidadactiva,descripcion=recursos.descripcion,recurso=recursos.recurso,orden=recursos.orden,tiporecurso=recursos.tiporecurso, estado=recursos.estado,aprueba=recursos.aprueba,observacion=recursos.observacion, fechacambioestado=recursos.fechacambioestado):
#                             recur = RecursoUnidadProgramaAnalitico(unidad=unidadactiva,
#                                                                    descripcion=recursos.descripcion,
#                                                                    recurso=recursos.recurso,
#                                                                    orden=recursos.orden,
#                                                                    tiporecurso=recursos.tiporecurso,
#                                                                    estado=2,
#                                                                    aprueba=recursos.aprueba,
#                                                                    observacion=recursos.observacion,
#                                                                    fechacambioestado=recursos.fechacambioestado
#                                                                    )
#                             recur.save()
#                     # copia lo de temas
#                 for temas in uni.temas_seleccionadas():
#                     if TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(),descripcion__iexact=temas.descripcion.upper(), unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True):
#                         temaactivo = TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(),descripcion__iexact=temas.descripcion.upper(), unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True)[0]
#                         for videostemas in temas.videotemaprogramaanalitico_set.filter(status=True).order_by('orden'):
#                             if not VideoTemaProgramaAnalitico.objects.filter(tema=temaactivo,descripcion=videostemas.descripcion,video=videostemas.video,orden=videostemas.orden,estado=videostemas.estado,aprueba=videostemas.aprueba,observacion=videostemas.observacion,fechacambioestado=videostemas.fechacambioestado):
#                                 vid = VideoTemaProgramaAnalitico(tema=temaactivo,
#                                                                  descripcion=videostemas.descripcion,
#                                                                  video=videostemas.video,
#                                                                  orden=videostemas.orden,
#                                                                  estado=2,
#                                                                  aprueba=videostemas.aprueba,
#                                                                  observacion=videostemas.observacion,
#                                                                  fechacambioestado=videostemas.fechacambioestado)
#                                 vid.save()
#                         # temas.recursotemaprogramaanalitico_set.filter(status=True).delete()
#                         for recursotema in temas.recursotemaprogramaanalitico_set.filter(status=True).order_by('orden'):
#                             if not RecursoTemaProgramaAnalitico.objects.filter(tema=temaactivo,descripcion=recursotema.descripcion,recurso=recursotema.recurso,orden=recursotema.orden,tiporecurso=recursotema.tiporecurso,estado=recursotema.estado,aprueba=recursotema.aprueba,observacion=recursotema.observacion,fechacambioestado=recursotema.fechacambioestado):
#                                 recurtema = RecursoTemaProgramaAnalitico(tema=temaactivo,
#                                                                          descripcion=recursotema.descripcion,
#                                                                          recurso=recursotema.recurso,
#                                                                          orden=recursotema.orden,
#                                                                          tiporecurso=recursotema.tiporecurso,
#                                                                          estado=2,
#                                                                          aprueba=recursotema.aprueba,
#                                                                          observacion=recursotema.observacion,
#                                                                          fechacambioestado=recursotema.fechacambioestado)
#                                 recurtema.save()
#                     for subtemas in temas.subtemas_seleccionadas():
#                         if SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(),temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(), descripcion__iexact=subtemas.descripcion.upper(), temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True):
#                             subtemaactivo = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(),temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(), descripcion__iexact=subtemas.descripcion.upper(), temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True)
#                             for videossubtemas in subtemas.videosubtemaprogramaanalitico_set.filter(status=True).order_by('orden'):
#                                 if not VideoSubTemaProgramaAnalitico.objects.filter(subtema=subtemaactivo,descripcion=videossubtemas.descripcion,video=videossubtemas.video,orden=videossubtemas.orden,estado=videossubtemas.estado, aprueba=videossubtemas.aprueba,observacion=videossubtemas.observacion,fechacambioestado=videossubtemas.fechacambioestado):
#                                     vidsub = VideoSubTemaProgramaAnalitico(subtema=subtemaactivo,
#                                                                            descripcion=videossubtemas.descripcion,
#                                                                            video=videossubtemas.video,
#                                                                            orden=videossubtemas.orden,
#                                                                            estado=2,
#                                                                            aprueba=videossubtemas.aprueba,
#                                                                            observacion=videossubtemas.observacion,
#                                                                            fechacambioestado=videossubtemas.fechacambioestado)
#                                     vidsub.save()
#                             # subtemas.recursosubtemaprogramaanalitico_set.filter(status=True).delete()
#                             for recursosubtema in subtemas.recursosubtemaprogramaanalitico_set.filter(status=True).order_by('orden'):
#                                 if not RecursoSubTemaProgramaAnalitico.objects.filter(subtema=subtemaactivo,descripcion=recursosubtema.descripcion, recurso=recursosubtema.recurso, orden=recursosubtema.orden, tiporecurso=recursosubtema.tiporecurso,estado=recursosubtema.estado, aprueba=recursosubtema.aprueba,observacion=recursosubtema.observacion, fechacambioestado=recursosubtema.fechacambioestado):
#                                     recursubtema = RecursoSubTemaProgramaAnalitico(subtema=subtemaactivo,
#                                                                                    descripcion=recursubtema.descripcion,
#                                                                                    recurso=recursubtema.recurso,
#                                                                                    orden=recursubtema.orden,
#                                                                                    tiporecurso=recursubtema.tiporecurso,
#                                                                                    estado=2,
#                                                                                    aprueba=recursubtema.aprueba,
#                                                                                    observacion=recursubtema.observacion,
#                                                                                    fechacambioestado=recursubtema.fechacambioestado)
#                                     recursubtema.save()
#
#                     print(a)

# proinactivas = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla_id__in=[5171,5248,5146,5646,5116,5238,5121,5100,5681,5647,5274,5148,5190,5641,5682,8229,5173,5223,5103,5202,5101,5142,5644,5089,5104,5159,5751,5140,5209,5196,5125,5179,5107,5180,5136,5154,5333,5152,5133,5226,5332,5185,5137,5643,5194,5131,5147,5642,5268,5139,5122,5162],programaanalitico__activo=False, status=True).exclude(programaanalitico__asignaturamalla__malla__carrera__coordinacion=9)
# proactivas = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla_id__in=[5171,5248,5146,5646,5116,5238,5121,5100,5681,5647,5274,5148,5190,5641,5682,8229,5173,5223,5103,5202,5101,5142,5644,5089,5104,5159,5751,5140,5209,5196,5125,5179,5107,5180,5136,5154,5333,5152,5133,5226,5332,5185,5137,5643,5194,5131,5147,5642,5268,5139,5122,5162],programaanalitico__activo=True, status=True).exclude(programaanalitico__asignaturamalla__malla__carrera__coordinacion=9)
# # proinactivas = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla_id__in=[5171,5248,5146,5646,5116,5238,5121,5100,5681,5647,5274,5148,5190,5641,5682,8229,5173,5223,5103,5202,5101,5142,5644,5089,5104,5159,5751,5140,5209,5196,5125,5179,5107,5180,5136,5154,5333,5152,5133,5226,5332,5185,5137,5643,5194,5131,5147,5642,5268,5139,5122,5162], status=True).exclude(programaanalitico__asignaturamalla__malla__carrera__coordinacion=9)
# # proactivas = AutorprogramaAnalitico.objects.filter(programaanalitico__asignaturamalla_id__in=[5171,5248,5146,5646,5116,5238,5121,5100,5681,5647,5274,5148,5190,5641,5682,8229,5173,5223,5103,5202,5101,5142,5644,5089,5104,5159,5751,5140,5209,5196,5125,5179,5107,5180,5136,5154,5333,5152,5133,5226,5332,5185,5137,5643,5194,5131,5147,5642,5268,5139,5122,5162], status=True).exclude(programaanalitico__asignaturamalla__malla__carrera__coordinacion=9)
# # pro = ProgramaAnaliticoAsignatura.objects.filter(asignaturamalla_id__in=[5171,5248,5146,5646,5116,5238,5121,5100,5681,5647,5274,5148,5190,5641,5682,8229,5173,5223,5103,5202,5101,5142,5644,5089,5104,5159,5751,5140,5209,5196,5125,5179,5107,5180,5136,5154,5333,5152,5133,5226,5332,5185,5137,5643,5194,5131,5147,5642,5268,5139,5122,5162], status=True).exclude(asignaturamalla__malla__carrera__coordinacion=9)
# a=0
# for proinac in proinactivas:
#     a=a+1
#     activascopiar = proactivas.get(programaanalitico__asignaturamalla_id=proinac.programaanalitico.asignaturamalla.id)
#     for conte in proinac.programaanalitico.contenido_program_analitico():
#         if conte.unidadresultadoprogramaanalitico_set.filter(status=True):
#             for uni in conte.unidades_seleccionadas():
#                 # query = UnidadResultadoProgramaAnalitico.objects.filter(descripcion__iexact=uni.descripcion.upper(),contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True,contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla,status=True)
#                 # print(query.query)
#                 if UnidadResultadoProgramaAnalitico.objects.filter(descripcion__iexact=uni.descripcion.upper(),contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True,contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla,status=True):
#                     unidadactiva = UnidadResultadoProgramaAnalitico.objects.get(descripcion__iexact=uni.descripcion.upper(), contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True)
#
#                     # copia lo de unidades
#                     for videos in uni.videounidadresultadoprogramaanalitico_set.filter(status=True).order_by('orden'):
#                         if not VideoUnidadResultadoProgramaAnalitico.objects.filter(unidad=unidadactiva,descripcion=videos.descripcion, video=videos.video,  orden=videos.orden,  aprueba=videos.aprueba,observacion=videos.observacion, fechacambioestado=videos.fechacambioestado):
#                             vid = VideoUnidadResultadoProgramaAnalitico(unidad=unidadactiva,
#                                                                         descripcion=videos.descripcion,
#                                                                         video=videos.video,
#                                                                         orden=videos.orden,
#                                                                         estado=2,
#                                                                         aprueba=videos.aprueba,
#                                                                         observacion=videos.observacion,
#                                                                         fechacambioestado=videos.fechacambioestado)
#                             vid.save()
#                     # uni.recursounidadprogramaanalitico_set.filter(status=True).delete()
#                     for recursos in uni.recursounidadprogramaanalitico_set.filter(status=True).order_by('orden'):
#                         if not RecursoUnidadProgramaAnalitico.objects.filter(unidad=unidadactiva,descripcion=recursos.descripcion,recurso=recursos.recurso,orden=recursos.orden,tiporecurso=recursos.tiporecurso,aprueba=recursos.aprueba,observacion=recursos.observacion, fechacambioestado=recursos.fechacambioestado):
#                             recur = RecursoUnidadProgramaAnalitico(unidad=unidadactiva,
#                                                                    descripcion=recursos.descripcion,
#                                                                    recurso=recursos.recurso,
#                                                                    orden=recursos.orden,
#                                                                    tiporecurso=recursos.tiporecurso,
#                                                                    estado=2,
#                                                                    aprueba=recursos.aprueba,
#                                                                    observacion=recursos.observacion,
#                                                                    fechacambioestado=recursos.fechacambioestado
#                                                                    )
#                             recur.save()
#                     # copia lo de temas
#             for temas in TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico=conte,status=True):
#                 if TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion__iexact=temas.descripcion.upper(), unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True):
#                     temaactivo = TemaUnidadResultadoProgramaAnalitico.objects.filter(descripcion__iexact=temas.descripcion.upper(), unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True)[0]
#                     # print(temaactivo.query)
#                     for videostemas in temas.videotemaprogramaanalitico_set.filter(status=True).order_by('orden'):
#                         if not VideoTemaProgramaAnalitico.objects.filter(tema=temaactivo,descripcion=videostemas.descripcion,video=videostemas.video,orden=videostemas.orden,aprueba=videostemas.aprueba,observacion=videostemas.observacion,fechacambioestado=videostemas.fechacambioestado):
#                             vid = VideoTemaProgramaAnalitico(tema=temaactivo,
#                                                              descripcion=videostemas.descripcion,
#                                                              video=videostemas.video,
#                                                              orden=videostemas.orden,
#                                                              estado=2,
#                                                              aprueba=videostemas.aprueba,
#                                                              observacion=videostemas.observacion,
#                                                              fechacambioestado=videostemas.fechacambioestado)
#                             vid.save()
#                     # temas.recursotemaprogramaanalitico_set.filter(status=True).delete()
#                     for recursotema in temas.recursotemaprogramaanalitico_set.filter(status=True).order_by('orden'):
#                         if not RecursoTemaProgramaAnalitico.objects.filter(tema=temaactivo,descripcion=recursotema.descripcion,recurso=recursotema.recurso,orden=recursotema.orden,tiporecurso=recursotema.tiporecurso,aprueba=recursotema.aprueba,observacion=recursotema.observacion,fechacambioestado=recursotema.fechacambioestado):
#                             recurtema = RecursoTemaProgramaAnalitico(tema=temaactivo,
#                                                                      descripcion=recursotema.descripcion,
#                                                                      recurso=recursotema.recurso,
#                                                                      orden=recursotema.orden,
#                                                                      tiporecurso=recursotema.tiporecurso,
#                                                                      estado=2,
#                                                                      aprueba=recursotema.aprueba,
#                                                                      observacion=recursotema.observacion,
#                                                                      fechacambioestado=recursotema.fechacambioestado)
#                             recurtema.save()
#                     # for subtemas in temas.subtemas_seleccionadas():
#                     #     if SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(),temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(), descripcion__iexact=subtemas.descripcion.upper(), temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True):
#                     #         subtemaactivo = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(),temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__descripcion__iexact=uni.descripcion.upper(), descripcion__iexact=subtemas.descripcion.upper(), temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=activascopiar.programaanalitico.asignaturamalla, status=True)
#                     #         for videossubtemas in subtemas.videosubtemaprogramaanalitico_set.filter(status=True).order_by('orden'):
#                     #             if not VideoSubTemaProgramaAnalitico.objects.filter(subtema=subtemaactivo,descripcion=videossubtemas.descripcion,video=videossubtemas.video,orden=videossubtemas.orden,estado=videossubtemas.estado, aprueba=videossubtemas.aprueba,observacion=videossubtemas.observacion,fechacambioestado=videossubtemas.fechacambioestado):
#                     #                 vidsub = VideoSubTemaProgramaAnalitico(subtema=subtemaactivo,
#                     #                                                        descripcion=videossubtemas.descripcion,
#                     #                                                        video=videossubtemas.video,
#                     #                                                        orden=videossubtemas.orden,
#                     #                                                        estado=2,
#                     #                                                        aprueba=videossubtemas.aprueba,
#                     #                                                        observacion=videossubtemas.observacion,
#                     #                                                        fechacambioestado=videossubtemas.fechacambioestado)
#                     #                 vidsub.save()
#                     #         # subtemas.recursosubtemaprogramaanalitico_set.filter(status=True).delete()
#                     #         for recursosubtema in subtemas.recursosubtemaprogramaanalitico_set.filter(status=True).order_by('orden'):
#                     #             if not RecursoSubTemaProgramaAnalitico.objects.filter(subtema=subtemaactivo,descripcion=recursosubtema.descripcion, recurso=recursosubtema.recurso, orden=recursosubtema.orden, tiporecurso=recursosubtema.tiporecurso,estado=recursosubtema.estado, aprueba=recursosubtema.aprueba,observacion=recursosubtema.observacion, fechacambioestado=recursosubtema.fechacambioestado):
#                     #                 recursubtema = RecursoSubTemaProgramaAnalitico(subtema=subtemaactivo,
#                     #                                                                descripcion=recursubtema.descripcion,
#                     #                                                                recurso=recursubtema.recurso,
#                     #                                                                orden=recursubtema.orden,
#                     #                                                                tiporecurso=recursubtema.tiporecurso,
#                     #                                                                estado=2,
#                     #                                                                aprueba=recursubtema.aprueba,
#                     #                                                                observacion=recursubtema.observacion,
#                     #                                                                fechacambioestado=recursubtema.fechacambioestado)
#                     #                 recursubtema.save()
#
#                 print(a)
#
#

# d = [2,3,4,5,5]
# lis=''
# for u in d:
#     if lis:
#         lis = lis + ',' + str(u)
#     else:
#         lis = str(u)
# print(lis)
# cursor = connection.cursor()
# sql1 = "SELECT listchildren('ALEMAN');"
# cursor.execute(sql1)
# results = cursor.fetchall()
# print(results)
