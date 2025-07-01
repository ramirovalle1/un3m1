#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import calendar

from dateutil.rrule import rrule, MONTHLY
from django.db.models.functions import ExtractSecond, ExtractMonth

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from investigacion.models import BitacoraActividadDocente
import pyqrcode
from django.db import transaction
from django.http import HttpResponse


import xlrd
from time import sleep
from sga.models import *
from sagest.models import *
from posgrado.models import *
from Moodle_Funciones import *

from settings import PROFESORES_GROUP_ID, DEBUG, ADMINISTRADOR_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, \
    DIAS_MATRICULA_EXPIRA, MEDIA_ROOT
from sga.funciones import calculate_username, generar_usuario, fechatope, null_to_decimal, TruncMonth, mesesmenoresandias
import xlwt
from xlwt import *
import unicodedata
from bd.models import CHOICES_FUNCION_DETALLE_REQUISITO
periodo = Periodo.objects.filter(pk=177)
from sga.funcionesxhtml2pdf import download_html_to_pdf, conviert_html_to_pdfsaveqrsilabo

from inno.models import InformeMensualDocente, HistorialInforme, SolicitudTutoriaIndividual, GrupoTitulacionIC


def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()


from moodle import moodle


def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha
#
# def resetear_clavepostulante(persona):
#     if not persona.usuario.is_superuser:
#         if persona.cedula:
#             password = persona.cedula.strip()
#         elif persona.pasaporte:
#             password = persona.pasaporte.strip()
#         user = persona.usuario
#         user.set_password(password)
#         user.save()

#
# listado = PreInscripcion.objects.filter(carrera_id=113, status=True)
#
# # listado = PreInscripcion.objects.filter(carrera_id=167, status=True)
# # listado = PreInscripcion.objects.filter(carrera_id=176, status=True)
# # listado = PreInscripcion.objects.filter(pk=1666)
# print(listado.query)
#
#
# for listapre in listado:
#     lista = []
#     if listapre.persona.emailinst:
#         lista.append(listapre.persona.emailinst)
#     if listapre.persona.email:
#         lista.append(listapre.persona.email)
#     print(listapre.persona)
#     if not listapre.persona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
#         print('no es usuario activo')
#         resetear_clavepostulante(listapre.persona)
#         formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=listapre.carrera_id, status=True)[0]
#         if listapre.persona.cedula:
#             password = listapre.persona.cedula.strip()
#         elif listapre.persona.pasaporte:
#             password = listapre.persona.pasaporte.strip()
#         aspirante = InscripcionAspirante.objects.filter(persona=listapre.persona, status=True)[0]
#         asunto = u"ADMISIÓN POSGRADO"
#         send_html_mail(asunto, "emails/masivoregistroexito.html",
#                        {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
#                         'usuario': listapre.persona.usuario.username,
#                         'clave': password,
#                         'carrera': listapre.carrera.nombre,
#                         'formato': formatocorreo.banner},
#                        lista, [], [formatocorreo.archivo],
#                        cuenta=CUENTAS_CORREOS[18][1])
#         time.sleep(5)
#     else:
#         print('es usuario activo')
#         formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=listapre.carrera_id, status=True)[0]
#
#         if listapre.persona.cedula:
#             password = listapre.persona.cedula.strip()
#         elif listapre.persona.pasaporte:
#             password = listapre.persona.pasaporte.strip()
#         aspirante = InscripcionAspirante.objects.filter(persona=listapre.persona, status=True)[0]
#         asunto = u"ADMISIÓN POSGRADO"
#         send_html_mail(asunto, "emails/masivoregistroexitopersonal.html",
#                        {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
#                         'carrera': listapre.carrera.nombre,
#                         'formato': formatocorreo.banner},
#                        lista, [], [formatocorreo.archivo],
#                        cuenta=CUENTAS_CORREOS[18][1])
#         time.sleep(5)
#
#
# # #
# listado = InscripcionCohorte.objects.filter(cohortes_id=62, status=True)
# # listado = PreInscripcion.objects.filter(pk=1666)
# print(listado.count())
#
#
# for listapre in listado:
#     lista = []
#     if listapre.inscripcionaspirante.persona.emailinst:
#         lista.append(listapre.inscripcionaspirante.persona.emailinst)
#     if listapre.inscripcionaspirante.persona.email:
#         lista.append(listapre.inscripcionaspirante.persona.email)
#     print(listapre.inscripcionaspirante.persona)
#     if not listapre.inscripcionaspirante.persona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
#         print('no es usuario activo')
#         resetear_clavepostulante(listapre.inscripcionaspirante.persona)
#         formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=listapre.cohortes.maestriaadmision.carrera_id, status=True)[0]
#         if listapre.inscripcionaspirante.persona.cedula:
#             password = listapre.inscripcionaspirante.persona.cedula.strip()
#         elif listapre.inscripcionaspirante.persona.pasaporte:
#             password = listapre.inscripcionaspirante.persona.pasaporte.strip()
#         aspirante = InscripcionAspirante.objects.filter(persona=listapre.inscripcionaspirante.persona, status=True)[0]
#         asunto = u"ADMISIÓN POSGRADO"
#         send_html_mail(asunto, "emails/masivoregistroexito.html",
#                        {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
#                         'usuario': listapre.inscripcionaspirante.persona.usuario.username,
#                         'clave': password,
#                         'carrera': listapre.cohortes.maestriaadmision.carrera.nombre,
#                         'formato': formatocorreo.banner},
#                        lista, [], [formatocorreo.archivo],
#                        cuenta=CUENTAS_CORREOS[18][1])
#         time.sleep(5)
#     else:
#         print('es usuario activo')
#         formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=listapre.cohortes.maestriaadmision.carrera_id, status=True)[0]
#
#         if listapre.inscripcionaspirante.persona.cedula:
#             password = listapre.inscripcionaspirante.persona.cedula.strip()
#         elif listapre.inscripcionaspirante.persona.pasaporte:
#             password = listapre.inscripcionaspirante.persona.pasaporte.strip()
#         aspirante = InscripcionAspirante.objects.filter(persona=listapre.inscripcionaspirante.persona, status=True)[0]
#         asunto = u"ADMISIÓN POSGRADO"
#         send_html_mail(asunto, "emails/masivoregistroexitopersonal.html",
#                        {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
#                         'carrera': listapre.cohortes.maestriaadmision.carrera.nombre,
#                         'formato': formatocorreo.banner},
#                        lista, [], [formatocorreo.archivo],
#                        cuenta=CUENTAS_CORREOS[18][1])
#         time.sleep(5)

# import openpyxl
# workbook = openpyxl.load_workbook("todasmarcadasotro.xlsx")
# lista = workbook.get_sheet_by_name('Hoja1')
# linea = 0
# totallista = lista.rows
# for filas in totallista[:]:
#     linea += 1
#     if linea > 1:
#
#         idreloj = filas[2].value.split('_')
#         print(idreloj[1])
#         if Persona.objects.filter(identificacioninstitucion=str(idreloj[1])):
#             perso = Persona.objects.get(identificacioninstitucion=str(idreloj[1]))
#             print(perso)
#             filas[1].value = perso.apellido1 + perso.apellido2 + perso.nombres
#             filas[5].value = perso.cedula
#     linea += 1
# workbook.save("todasmarcadasotro.xlsx")

# from sga.models import TIPOFIRMA_EVENTO
# listA = TIPOFIRMA_EVENTO
#
# test_elem = ((1))
# #Given list
# print("Given list:\n",listA)
# print("Check value:\n",test_elem)
# # Uisng lambda and in
# # res = list(filter(lambda x:test_elem not in x, listA))
# res = list(filter(lambda x:test_elem not in x, listA))
# # printing res
# print("The tuples satisfying the conditions:\n ",res)


# from sga.models import TIPOFIRMA_EVENTO
# test_list = TIPOFIRMA_EVENTO
# print(TIPOFIRMA_EVENTO)
# tar_list = [1,3]
#
# print("The original list : " + str(test_list))
#
# res = [tup for tup in test_list if not any(i in tup for i in tar_list)]
#
# print("Filtered tuple from list are : " + str(res))

# def calculando_marcadasotro(fechai, fechaf, persona):
#     b = range(86400)
#     while fechai <= fechaf:
#         c = [[] for i in b]
#         if not DiasNoLaborable.objects.filter(fecha=fechai).exclude(periodo__isnull=False).exists():
#             if persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin__gte=fechai).exists():
#                 jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin__gte=fechai).order_by('fechainicio')[0]
#                 if jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday()).exists():
#                     jornadasdia = jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday())
#                     if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
#                         diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
#                         diajornada.jornada = jornada.jornada
#                         diajornada.totalsegundostrabajados = 0
#                         diajornada.totalsegundospermisos = 0
#                         diajornada.totalsegundosextras = 0
#                         diajornada.totalsegundosatrasos = 0
#                     else:
#                         diajornada = TrabajadorDiaJornada(persona=persona,
#                                                           fecha=fechai,
#                                                           anio=fechai.year,
#                                                           mes=fechai.month,
#                                                           jornada=jornada.jornada)
#                         diajornada.save()
#                     if persona.marcadasdia_set.filter(fecha=fechai).exists():
#                         marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
#                     else:
#                         marcadadia = MarcadasDia(persona=persona, fecha=fechai)
#                         marcadadia.save()
#                     totalsegundostrabajados = 0
#                     totalsegundosextras = 0
#                     totalsegundosatraso = 0
#                     totalpermisos = 0
#                     totalpermisosantes = 0
#                     for marcada in marcadadia.registromarcada_set.all():
#                         duracion = (marcada.salida - marcada.entrada).seconds
#                         inicio = (marcada.entrada.time().hour * 60 * 60) + (marcada.entrada.time().minute * 60) + marcada.entrada.time().second
#                         fin = (marcada.salida.time().hour * 60 * 60) + (marcada.salida.time().minute * 60) + marcada.salida.time().second
#                         while inicio <= fin:
#                             c[inicio].append('m')
#                             inicio += 1
#                     for jornadamarcada in jornadasdia:
#                         duracionjornada = (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horafin.hour, jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horainicio.hour, jornadamarcada.horainicio.minute, jornadamarcada.horainicio.second))).seconds
#                         iniciojornada = (jornadamarcada.horainicio.hour * 60 * 60) + (jornadamarcada.horainicio.minute * 60) + jornadamarcada.horainicio.second
#                         finjornada = (jornadamarcada.horafin.hour * 60 * 60) + (jornadamarcada.horafin.minute * 60) + jornadamarcada.horafin.second
#                         while iniciojornada <= finjornada:
#                             c[iniciojornada].append('j')
#                             iniciojornada += 1
#                     for permiso in PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=persona, fechainicio__lte=fechai, fechafin__gte=fechai, permisoinstitucional__estadosolicitud=3):
#                         # VACACIONES
#                         if permiso.permisoinstitucional.tiposolicitud == 3:
#                             horainicio = datetime(2016, 1, 0, 0, 0, 0)
#                             horafin = datetime(2016, 1, 1, 23, 0, 0)
#                             duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, horafin.hour, horafin.minute, horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, horainicio.hour, horainicio.minute, horainicio.second))).seconds
#                             iniciopermiso = (horainicio.hour * 60 * 60) + (horainicio.minute * 60) + horainicio.second
#                             finpermiso = (horafin.hour * 60 * 60) + (horafin.minute * 60) + horafin.second
#                         else:
#                             duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, permiso.horafin.hour, permiso.horafin.minute, permiso.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, permiso.horainicio.hour, permiso.horainicio.minute, permiso.horainicio.second))).seconds
#                             iniciopermiso = (permiso.horainicio.hour * 60 * 60) + (permiso.horainicio.minute * 60) + permiso.horainicio.second
#                             finpermiso = (permiso.horafin.hour * 60 * 60) + (permiso.horafin.minute * 60) + permiso.horafin.second
#                         while iniciopermiso <= finpermiso:
#                             c[iniciopermiso].append('p')
#                             iniciopermiso += 1
#                     for i in c:
#                         if len(i):
#                             if 'm' in i:
#                                 if 'j' in i:
#                                     totalsegundostrabajados += 1
#                                 else:
#                                     totalsegundosextras += 1
#                             elif 'j' in i:
#                                 if 'p' in i:
#                                     totalpermisos += 1
#                                 else:
#                                     totalsegundosatraso += 1
#                             else:
#                                 totalpermisosantes += 1
#                     diajornada.totalsegundosatrasos = totalsegundosatraso
#                     diajornada.totalsegundostrabajados = totalsegundostrabajados
#                     diajornada.totalsegundosextras = totalsegundosextras
#                     diajornada.totalsegundospermisos = totalpermisos
#                     diajornada.save()
#             elif persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None).exists():
#                 jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None)[0]
#                 if jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday()).exists():
#                     jornadasdia = jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday())
#                     if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
#                         diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
#                         diajornada.jornada = jornada.jornada
#                         diajornada.totalsegundostrabajados = 0
#                         diajornada.totalsegundospermisos = 0
#                         diajornada.totalsegundosextras = 0
#                         diajornada.totalsegundosatrasos = 0
#                     else:
#                         diajornada = TrabajadorDiaJornada(persona=persona,
#                                                           fecha=fechai,
#                                                           anio=fechai.year,
#                                                           mes=fechai.month,
#                                                           jornada=jornada.jornada)
#                         diajornada.save()
#                     if persona.marcadasdia_set.filter(fecha=fechai).exists():
#                         marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
#                     else:
#                         marcadadia = MarcadasDia(persona=persona, fecha=fechai)
#                         marcadadia.save()
#                     totalsegundostrabajados = 0
#                     totalsegundosextras = 0
#                     totalsegundosatraso = 0
#                     totalpermisos = 0
#                     totalpermisosantes = 0
#                     for marcada in marcadadia.registromarcada_set.all():
#                         duracion = (marcada.salida - marcada.entrada).seconds
#                         inicio = (marcada.entrada.time().hour * 60 * 60) + (marcada.entrada.time().minute * 60) + marcada.entrada.time().second
#                         fin = (marcada.salida.time().hour * 60 * 60) + (marcada.salida.time().minute * 60) + marcada.salida.time().second
#                         while inicio <= fin:
#                             c[inicio].append('m')
#                             inicio += 1
#                     for jornadamarcada in jornadasdia:
#                         duracionjornada = (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horafin.hour, jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horainicio.hour, jornadamarcada.horainicio.minute, jornadamarcada.horainicio.second))).seconds
#                         iniciojornada = (jornadamarcada.horainicio.hour * 60 * 60) + (jornadamarcada.horainicio.minute * 60) + jornadamarcada.horainicio.second
#                         finjornada = (jornadamarcada.horafin.hour * 60 * 60) + (jornadamarcada.horafin.minute * 60) + jornadamarcada.horafin.second
#                         while iniciojornada <= finjornada:
#                             c[iniciojornada].append('j')
#                             iniciojornada += 1
#                     for permiso in PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=persona, fechainicio__lte=fechai, fechafin__gte=fechai, permisoinstitucional__estadosolicitud=3):
#                         # VACACIONES
#                         if permiso.permisoinstitucional.tiposolicitud == 3:
#                             horainicio = datetime(2016, 1, 1, 0, 0, 0)
#                             horafin = datetime(2016, 1, 1, 23, 0, 0)
#                             duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, horafin.hour, horafin.minute, horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, horainicio.hour, horainicio.minute, horainicio.second))).seconds
#                             iniciopermiso = (horainicio.hour * 60 * 60) + (horainicio.minute * 60) + horainicio.second
#                             finpermiso = (horafin.hour * 60 * 60) + (horafin.minute * 60) + horafin.second
#                         else:
#                             duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, permiso.horafin.hour, permiso.horafin.minute, permiso.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, permiso.horainicio.hour, permiso.horainicio.minute, permiso.horainicio.second))).seconds
#                             iniciopermiso = (permiso.horainicio.hour * 60 * 60) + (permiso.horainicio.minute * 60) + permiso.horainicio.second
#                             finpermiso = (permiso.horafin.hour * 60 * 60) + (permiso.horafin.minute * 60) + permiso.horafin.second
#                         while iniciopermiso <= finpermiso:
#                             c[iniciopermiso].append('p')
#                             iniciopermiso += 1
#                     for i in c:
#                         if len(i):
#                             if 'm' in i:
#                                 if 'j' in i:
#                                     totalsegundostrabajados += 1
#                                 else:
#                                     totalsegundosextras += 1
#                             elif 'j' in i:
#                                 if 'p' in i:
#                                     totalpermisos += 1
#                                 else:
#                                     totalsegundosatraso += 1
#                             else:
#                                 totalpermisosantes += 1
#                     diajornada.totalsegundosatrasos = totalsegundosatraso
#                     diajornada.totalsegundostrabajados = totalsegundostrabajados
#                     diajornada.totalsegundosextras = totalsegundosextras
#                     diajornada.totalsegundospermisos = totalpermisos
#                     diajornada.save()
#         else:
#             if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
#                 jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None)[0]
#                 diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
#                 diajornada.jornada = jornada.jornada
#                 diajornada.totalsegundostrabajados = 0
#                 diajornada.totalsegundospermisos = 0
#                 diajornada.totalsegundosextras = 0
#                 diajornada.totalsegundosatrasos = 0
#                 diajornada.status = False
#                 diajornada.save()
#         fechai += timedelta(days=1)
# # # # # # # #
# # listadodias = LogDia.objects.filter(fecha__gte='2021-04-13',fecha__lt='2021-05-06' , status=True).order_by("fecha")
# listadodias = LogDia.objects.filter(fecha__gte='2021-04-01',fecha__lt='2021-06-22' , status=True).order_by("fecha")
#
# a = 0
# for l in listadodias:
#     a = a + 1
#     calculando_marcadasotro(l.fecha, l.fecha, l.persona)
#     print(str(a) + '/' + str(listadodias.count()))

# # for mat in DescuentoPosgradoMatricula.objects.filter(status=True):
# #     # persona = mat.matricula.inscripcion.persona
#         for rub in Rubro.objects.filter(matricula_id=218859,status=True,saldoanterior__gt=0):
#             if rub.idrubroepunemi > 0:
#                 updaterubroepunemi(rub.idrubroepunemi)

# for mat in Matricula.objects.filter(status=True, nivel__periodo_id=86).distinct():
#     # persona = mat.matricula.inscripcion.persona
#     for rub in Rubro.objects.filter(matricula=mat,status=True,saldoanterior__gt=0):
#         if rub.idrubroepunemi > 0:
#             updaterubroepunemi(rub.idrubroepunemi)


# ru = Rubro.objects.filter(matricula_id=185773,status=True,saldoanterior__gt=0)
# print(ru.query)

#
# listaclase = Clase.objects.filter(materia__profesormateria__profesor_id=15,materia__nivel__periodo_id=112, dia=1).order_by('-id')[0]
# print(listaclase)
#
# for lis in listaclase:
#     print(lis)
# tipoprofesores = (
#     (1, u'TEORIA'),
#     (2, u'PRACTICA'),
#     (7, u'VIRTUAL'),
#     (11, u'AUTOR 2'),
#     (12, u'AUTOR 1'),
#     (10, u'ORIENTACION')
# )
# listadias = DIAS_CHOICES
# # listadomateria = Materia.objects.filter(nivel__periodo_id=113,asignaturamalla__malla__carrera__coordinacion=1)
# listadomateria = Materia.objects.filter(nivel__periodo_id=113)
# # listadomateria = Materia.objects.filter(pk=38074)
# contador = listadomateria.count()
# con = 0
# for lismate in  listadomateria:
#     con = con + 1
#     for lisdia in listadias:
#         for tipo in tipoprofesores:
#             if Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]):
#                 listaclase = Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]).order_by('-id')
#                 clasetrue = Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]).order_by('-turno__comienza')[0]
#                 clasetrue.subirenlace = True
#                 clasetrue.save()
#                 for lclase in listaclase:
#                     if lclase.id != clasetrue.id:
#                         # print('si')
#                         lclase.subirenlace = False
#                         lclase.save()
#
#     print(str(con) + " de " +str(contador))
# lista = []
# print(len(lista))
# per = Persona.objects.get(cedula='0923363030')
# print(per.usuario)
## representacion de fecha y hora
# lista = CompendioSilaboSemanal.objects.values_list('id','fecha_creacion','silabosemanal_id').filter(pk=3816)
# for lis in lista:
#     # print(lis[1].date())
#     deta = DetalleSilaboSemanalTema.objects.values_list('temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden',flat=True).filter(silabosemanal_id=lis[0])[0]
#     print(deta)

# listadodescuento = DescuentoPosgradoMatricula.objects.filter(status=True)
# for descu in listadodescuento:
#     print(descu.matricula.id)
#     rub = Rubro.objects.filter(matricula=descu.matricula, saldoanterior__gt=0,status=True)
#     if rub:
#         for r in rub:
#             if r.idrubroepunemi > 0:
#                 codrubroepunemi = r.idrubroepunemi
#                 updaterubroepunemi(codrubroepunemi)
#                 print(descu)


# def calculando_marcadas(fechai, fechaf, persona):
#     b = range(86400)
#     while fechai <= fechaf:
#         c = [[] for i in b]
#         if not DiasNoLaborable.objects.filter(fecha=fechai).exclude(periodo__isnull=False).exists():
#             if persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin__gte=fechai).exists():
#                 jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin__gte=fechai).order_by('fechainicio')[0]
#                 if jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday()).exists():
#                     jornadasdia = jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday())
#                     if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
#                         diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
#                         diajornada.jornada = jornada.jornada
#                         diajornada.totalsegundostrabajados = 0
#                         diajornada.totalsegundospermisos = 0
#                         diajornada.totalsegundosextras = 0
#                         diajornada.totalsegundosatrasos = 0
#                     else:
#                         diajornada = TrabajadorDiaJornada(persona=persona,
#                                                           fecha=fechai,
#                                                           anio=fechai.year,
#                                                           mes=fechai.month,
#                                                           jornada=jornada.jornada)
#                         diajornada.save()
#                     if persona.marcadasdia_set.filter(fecha=fechai).exists():
#                         marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
#                     else:
#                         marcadadia = MarcadasDia(persona=persona, fecha=fechai)
#                         marcadadia.save()
#                     totalsegundostrabajados = 0
#                     totalsegundosextras = 0
#                     totalsegundosatraso = 0
#                     totalpermisos = 0
#                     totalpermisosantes = 0
#                     for marcada in marcadadia.registromarcada_set.all():
#                         duracion = (marcada.salida - marcada.entrada).seconds
#                         inicio = (marcada.entrada.time().hour * 60 * 60) + (marcada.entrada.time().minute * 60) + marcada.entrada.time().second
#                         fin = (marcada.salida.time().hour * 60 * 60) + (marcada.salida.time().minute * 60) + marcada.salida.time().second
#                         while inicio <= fin:
#                             c[inicio].append('m')
#                             inicio += 1
#                     for jornadamarcada in jornadasdia:
#                         duracionjornada = (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horafin.hour, jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horainicio.hour, jornadamarcada.horainicio.minute, jornadamarcada.horainicio.second))).seconds
#                         iniciojornada = (jornadamarcada.horainicio.hour * 60 * 60) + (jornadamarcada.horainicio.minute * 60) + jornadamarcada.horainicio.second
#                         finjornada = (jornadamarcada.horafin.hour * 60 * 60) + (jornadamarcada.horafin.minute * 60) + jornadamarcada.horafin.second
#                         while iniciojornada <= finjornada:
#                             c[iniciojornada].append('j')
#                             iniciojornada += 1
#                     for permiso in PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=persona, fechainicio__lte=fechai, fechafin__gte=fechai, permisoinstitucional__estadosolicitud=3):
#                         # VACACIONES
#                         if permiso.permisoinstitucional.tiposolicitud == 3:
#                             horainicio = datetime(2016, 1, 0, 0, 0, 0)
#                             horafin = datetime(2016, 1, 1, 23, 0, 0)
#                             duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, horafin.hour, horafin.minute, horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, horainicio.hour, horainicio.minute, horainicio.second))).seconds
#                             iniciopermiso = (horainicio.hour * 60 * 60) + (horainicio.minute * 60) + horainicio.second
#                             finpermiso = (horafin.hour * 60 * 60) + (horafin.minute * 60) + horafin.second
#                         else:
#                             duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, permiso.horafin.hour, permiso.horafin.minute, permiso.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, permiso.horainicio.hour, permiso.horainicio.minute, permiso.horainicio.second))).seconds
#                             iniciopermiso = (permiso.horainicio.hour * 60 * 60) + (permiso.horainicio.minute * 60) + permiso.horainicio.second
#                             finpermiso = (permiso.horafin.hour * 60 * 60) + (permiso.horafin.minute * 60) + permiso.horafin.second
#                         while iniciopermiso <= finpermiso:
#                             c[iniciopermiso].append('p')
#                             iniciopermiso += 1
#                     for i in c:
#                         if len(i):
#                             if 'm' in i:
#                                 if 'j' in i:
#                                     totalsegundostrabajados += 1
#                                 else:
#                                     totalsegundosextras += 1
#                             elif 'j' in i:
#                                 if 'p' in i:
#                                     totalpermisos += 1
#                                 else:
#                                     totalsegundosatraso += 1
#                             else:
#                                 totalpermisosantes += 1
#                     diajornada.totalsegundosatrasos = totalsegundosatraso
#                     diajornada.totalsegundostrabajados = totalsegundostrabajados
#                     diajornada.totalsegundosextras = totalsegundosextras
#                     diajornada.totalsegundospermisos = totalpermisos
#                     diajornada.save()
#             elif persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None).exists():
#                 jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None)[0]
#                 if jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday()).exists():
#                     jornadasdia = jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday())
#                     if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
#                         diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
#                         diajornada.jornada = jornada.jornada
#                         diajornada.totalsegundostrabajados = 0
#                         diajornada.totalsegundospermisos = 0
#                         diajornada.totalsegundosextras = 0
#                         diajornada.totalsegundosatrasos = 0
#                     else:
#                         diajornada = TrabajadorDiaJornada(persona=persona,
#                                                           fecha=fechai,
#                                                           anio=fechai.year,
#                                                           mes=fechai.month,
#                                                           jornada=jornada.jornada)
#                         diajornada.save()
#                     if persona.marcadasdia_set.filter(fecha=fechai).exists():
#                         marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
#                     else:
#                         marcadadia = MarcadasDia(persona=persona, fecha=fechai)
#                         marcadadia.save()
#                     totalsegundostrabajados = 0
#                     totalsegundosextras = 0
#                     totalsegundosatraso = 0
#                     totalpermisos = 0
#                     totalpermisosantes = 0
#                     for marcada in marcadadia.registromarcada_set.all():
#                         duracion = (marcada.salida - marcada.entrada).seconds
#                         inicio = (marcada.entrada.time().hour * 60 * 60) + (marcada.entrada.time().minute * 60) + marcada.entrada.time().second
#                         fin = (marcada.salida.time().hour * 60 * 60) + (marcada.salida.time().minute * 60) + marcada.salida.time().second
#                         while inicio <= fin:
#                             c[inicio].append('m')
#                             inicio += 1
#                     for jornadamarcada in jornadasdia:
#                         duracionjornada = (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horafin.hour, jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horainicio.hour, jornadamarcada.horainicio.minute, jornadamarcada.horainicio.second))).seconds
#                         iniciojornada = (jornadamarcada.horainicio.hour * 60 * 60) + (jornadamarcada.horainicio.minute * 60) + jornadamarcada.horainicio.second
#                         finjornada = (jornadamarcada.horafin.hour * 60 * 60) + (jornadamarcada.horafin.minute * 60) + jornadamarcada.horafin.second
#                         while iniciojornada <= finjornada:
#                             c[iniciojornada].append('j')
#                             iniciojornada += 1
#                     for permiso in PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=persona, fechainicio__lte=fechai, fechafin__gte=fechai, permisoinstitucional__estadosolicitud=3):
#                         # VACACIONES
#                         if permiso.permisoinstitucional.tiposolicitud == 3:
#                             horainicio = datetime(2016, 1, 1, 0, 0, 0)
#                             horafin = datetime(2016, 1, 1, 23, 0, 0)
#                             duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, horafin.hour, horafin.minute, horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, horainicio.hour, horainicio.minute, horainicio.second))).seconds
#                             iniciopermiso = (horainicio.hour * 60 * 60) + (horainicio.minute * 60) + horainicio.second
#                             finpermiso = (horafin.hour * 60 * 60) + (horafin.minute * 60) + horafin.second
#                         else:
#                             duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, permiso.horafin.hour, permiso.horafin.minute, permiso.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, permiso.horainicio.hour, permiso.horainicio.minute, permiso.horainicio.second))).seconds
#                             iniciopermiso = (permiso.horainicio.hour * 60 * 60) + (permiso.horainicio.minute * 60) + permiso.horainicio.second
#                             finpermiso = (permiso.horafin.hour * 60 * 60) + (permiso.horafin.minute * 60) + permiso.horafin.second
#                         while iniciopermiso <= finpermiso:
#                             c[iniciopermiso].append('p')
#                             iniciopermiso += 1
#                     for i in c:
#                         if len(i):
#                             if 'm' in i:
#                                 if 'j' in i:
#                                     totalsegundostrabajados += 1
#                                 else:
#                                     totalsegundosextras += 1
#                             elif 'j' in i:
#                                 if 'p' in i:
#                                     totalpermisos += 1
#                                 else:
#                                     totalsegundosatraso += 1
#                             else:
#                                 totalpermisosantes += 1
#                     diajornada.totalsegundosatrasos = totalsegundosatraso
#                     diajornada.totalsegundostrabajados = totalsegundostrabajados
#                     diajornada.totalsegundosextras = totalsegundosextras
#                     diajornada.totalsegundospermisos = totalpermisos
#                     diajornada.save()
#         else:
#             if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
#                 jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None)[0]
#                 diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
#                 diajornada.jornada = jornada.jornada
#                 diajornada.totalsegundostrabajados = 0
#                 diajornada.totalsegundospermisos = 0
#                 diajornada.totalsegundosextras = 0
#                 diajornada.totalsegundosatrasos = 0
#                 diajornada.status = False
#                 diajornada.save()
#         fechai += timedelta(days=1)
#
# cedula = '1201222575'
# # cedula = ''
# fechalunes = datetime(2020, 12, 1)
# fechadomingo = datetime(2020, 12, 31)
# fechadomingo = fechadomingo + timedelta(days=1)
# categorias = []
# for fechadia in daterange(fechalunes, fechadomingo):
#     if int(fechadia.isocalendar()[2]) == 1 or int(fechadia.isocalendar()[2]) == 2 or int(fechadia.isocalendar()[2]) == 3 or int(fechadia.isocalendar()[2]) == 4 or int(fechadia.isocalendar()[2]) == 5:
#         # print(int(fechadia.isocalendar()[2]))
#         # print(fechadia.year)
#         # print(fechadia.month)
#         # print(fechadia.day)
#         if fechadia.day == 25:
#             d = 0
#         else:
#             horaentrada = random.randint(45, 59)
#             segundosentrada = random.randint(1, 59)
#             fecaregistroentrada = str(fechadia.day)+'/'+str(fechadia.month)+'/'+str(fechadia.year)+' 07:'+str(horaentrada)+':'+str(segundosentrada)
#             categorias.append(fecaregistroentrada)
#             horatarde1 = random.randint(0, 15)
#             segundost1 = random.randint(1, 59)
#             fecaregistrot1 = str(fechadia.day)+'/'+str(fechadia.month)+'/'+str(fechadia.year)+' 13:'+str(horatarde1)+':'+str(segundost1)
#             categorias.append(fecaregistrot1)
#             horatarde2 = random.randint(45, 59)
#             segundost2 = random.randint(1, 59)
#             fecaregistrot2 = str(fechadia.day)+'/'+str(fechadia.month)+'/'+str(fechadia.year)+' 13:'+str(horatarde2)+':'+str(segundost2)
#             categorias.append(fecaregistrot2)
#             horasalida = random.randint(1, 20)
#             segundossalida = random.randint(1, 59)
#             fecaregistrosalida = str(fechadia.day)+'/'+str(fechadia.month)+'/'+str(fechadia.year)+' 17:'+str(horasalida)+':'+str(segundossalida)
#             categorias.append(fecaregistrosalida)
# print(categorias)
# for cate in categorias:
#     if cedula != "":
#         if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
#             persona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).distinct()[0]
#             fecha = convertir_fecha(cate[:10])
#             time = datetime(fecha.year, fecha.month, fecha.day, int(cate.split(':')[0][10:13]), int(cate.split(':')[1]))
#             if persona.logdia_set.filter(fecha=fecha).exists():
#                 logdia = persona.logdia_set.filter(fecha=fecha)[0]
#                 if logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).exists():
#                     logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).order_by('fechainicio')[0].jornada
#                 elif logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None).exists():
#                     logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None)[0].jornada
#                 logdia.cantidadmarcadas += 1
#                 logdia.procesado = False
#             else:
#                 logdia = LogDia(persona=persona, fecha=fecha, cantidadmarcadas=1)
#             logdia.save()
#             if not logdia.logmarcada_set.filter(time=time).exists():
#                 registro = LogMarcada(logdia=logdia,
#                                       time=time,
#                                       secuencia=logdia.cantidadmarcadas)
#                 registro.save()
#             for l in LogDia.objects.filter(persona=persona,fecha=fecha, status=True, procesado=False).order_by("fecha"):
#                 if not l.jornada:
#                     if l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).exists():
#                         l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).order_by('fechainicio')[0].jornada
#                     elif l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None).exists():
#                         l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None)[0].jornada
#
#                 cm = l.logmarcada_set.filter(status=True).count()
#                 MarcadasDia.objects.filter(persona=l.persona, fecha=l.fecha).delete()
#                 l.cantidadmarcadas = cm
#                 if (cm % 2) == 0:
#                     marini = 1
#                     for dl in l.logmarcada_set.filter(status=True).order_by("time"):
#                         if marini == 2:
#                             salida = dl.time
#                             marini = 1
#                             if l.persona.marcadasdia_set.filter(fecha=l.fecha).exists():
#                                 marcadadia = l.persona.marcadasdia_set.filter(fecha=l.fecha)[0]
#                             else:
#                                 marcadadia = MarcadasDia(persona=l.persona,
#                                                          fecha=l.fecha,
#                                                          logdia=l,
#                                                          segundos=0)
#                                 marcadadia.save()
#                             if not marcadadia.registromarcada_set.filter(entrada=entrada).exists():
#                                 registro = RegistroMarcada(marcada=marcadadia,
#                                                            entrada=entrada,
#                                                            salida=salida,
#                                                            segundos=(salida - entrada).seconds)
#                                 registro.save()
#                             marcadadia.actualizar_marcadas()
#                         else:
#                             entrada = dl.time
#                             marini += 1
#                     l.procesado = True
#                 else:
#                     l.cantidadmarcadas = 0
#                 l.save()
#                 if l.procesado:
#                     calculando_marcadas(l.fecha, l.fecha, l.persona)
#                 print('resuelto')



# matriculas = Matricula.objects.filter(nivel__periodo_id=112, status=True)
# cursor = connections['moodle_db'].cursor()
# for matri in matriculas:
#     sql_enviados = "SELECT COUNT(*) " \
#                    "FROM mooc_user usuario " \
#                    "WHERE usuario.username='%s'" % (matri.inscripcion.persona.usuario.username)
#     cursor.execute(sql_enviados)
#     datos = cursor.fetchall()
# listapersonas = Persona.objects.filter(pk__in=ProfesorMateria.objects.values_list('profesor__persona_id').filter(materia__nivel__periodo_id=112).distinct(), status=True)
# listapersonas = Persona.objects.filter(pk__in=Matricula.objects.values_list('inscripcion__persona_id').filter(nivel__periodo_id=112).distinct(), status=True)
# cursor = connections['moodle_db'].cursor()
# a = 0
# for perso in listapersonas:
#     a = a + 1
#     sql_enviados = "SELECT usuario.id,usuario.idnumber  " \
#                    "FROM mooc_user usuario " \
#                    "WHERE usuario.username='%s'" % (perso.usuario.username)
#     cursor.execute(sql_enviados)
#     datosid = cursor.fetchall()
#     # print(datosid)
#     if datosid:
#         # print(datosid[0][0])
#         # print(datosid[0][1])
#         if not datosid[0][1]:
#             print(datosid[0][1])
#             sqlnumber = "update mooc_user " \
#                         "set idnumber='%s' WHERE id='%s'" % (perso.identificacion(), datosid[0][0])
#             cursor.execute(sqlnumber)
#             print('actualizado correctamente')
#     print(str(a) + ' de ' + str(listapersonas.count()))
#

# listadovidmagistral = VideoMagistralSilaboSemanal.objects.filter(silabosemanal__silabo__materia__nivel__periodo_id__in=[99,112], estado_id=4, urlcrai='')
# a =0
# for vidmagistral in listadovidmagistral:
#     a = a + 1
#     materia = vidmagistral.silabosemanal.silabo.materia
#     materia.actualizarhtml = True
#     materia.save()
#     if vidmagistral.urlcrai:
#         url = vidmagistral.urlcrai
#     else:
#         url = 'https://sga.unemi.edu.ec/media/' + str(vidmagistral.archivovideomagistral)
#     print(url)
#     instanceid = vidmagistral.idvidmagistralmoodle
#     cursoid = materia.idcursomoodle
#     cursor = None
#     if materia.coordinacion():
#         if materia.coordinacion().id == 9:
#             cursor = connections['db_moodle_virtual'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
#     else:
#         cursor = connections['moodle_db'].cursor()
#     sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
#     cursor.execute(sql)
#     buscar = cursor.fetchall()
#     instance = buscar[0][0]
#     sql = """update mooc_url
#                         set
#                             externalurl='%s'
#                         where course='%s' and id='%s'
#                         """ % (url, cursoid, instance)
#
#     cursor.execute(sql)
#     print(a)

# from Moodle_Funciones import CrearRecursoMoodle
# listadopresentaciones = DiapositivaSilaboSemanal.objects.filter(estado_id=4, silabosemanal__silabo__materia__nivel__periodo_id__in=[99,112], iddiapositivamoodle=0, status=True)
# for lis in listadopresentaciones:
#     CrearRecursoMoodle(lis.id, 34)
# print(listadopresentaciones.count())

# import openpyxl
# workbook = openpyxl.load_workbook("listadiapositivas.xlsx")
# lista = workbook.get_sheet_by_name('Hoja1')
# linea = 0
# totallista = lista.rows
#
# for filas in totallista[:]:
#     linea += 1
#     if linea > 1:
#         cursor = None
#         materia = Materia.objects.get(pk=filas[5].value)
#         cursoid = materia.idcursomoodle
#         nombrebusca = filas[2].value
#         if materia.coordinacion():
#             if materia.coordinacion().id == 9:
#                 cursor = connections['db_moodle_virtual'].cursor()
#             else:
#                 cursor = connections['moodle_db'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
# sql = """ select count(ur.id) from mooc_course_modules cou,mooc_url ur
#             where cou.instance=ur.id
#             and ur.course='%s'
#             and cou.module=20
#             and ur.name like '%s'
#             and cou.section = (select id from mooc_course_sections
#             WHERE course='%s' AND SECTION=7) """ % (cursoid, nombrebusca, cursoid)
# cursor.execute(sql)
# buscar = cursor.fetchall()
# instance = buscar[0][0]
# filas[6].value = instance
# if filas[6].value == 1 or filas[6].value == 2:
#     sql = """ select cou.id from mooc_course_modules cou,mooc_url ur
#                         where cou.instance=ur.id
#                         and ur.course='%s'
#                         and cou.module=20
#                         and TO_CHAR(TO_TIMESTAMP(ur.timemodified), 'YYYY-MM-DD') = '2021-01-08'
#                         and ur.name like '%s'
#                         and cou.section = (select id from mooc_course_sections
#                         WHERE course='%s' AND SECTION=7)""" % (cursoid, nombrebusca, cursoid)
#     cursor.execute(sql)
#     buscar = cursor.fetchall()
#     if buscar:
#         if buscar[0][0]:
#             instance = buscar[0][0]
#             filas[8].value = instance
# if filas[6].value == 1 or filas[6].value == 2:
#     sql = """ select cou.id from mooc_course_modules cou,mooc_url ur
#                         where cou.instance=ur.id
#                         and ur.course='%s'
#                         and cou.module=20
#                         and TO_CHAR(TO_TIMESTAMP(ur.timemodified), 'YYYY-MM-DD') != '2021-01-08'
#                         and ur.name like '%s'
#                         and cou.section = (select id from mooc_course_sections
#                         WHERE course='%s' AND SECTION=7)""" % (cursoid, nombrebusca, cursoid)
#     cursor.execute(sql)
#     buscar = cursor.fetchall()
#     if buscar:
#         if buscar[0][0]:
#             instance = buscar[0][0]
#             filas[9].value = instance
#         print(str(filas[7].value))
#     linea += 1
# workbook.save("listadiapositivas.xlsx")

# import openpyxl
# workbook = openpyxl.load_workbook("listadiapositivas.xlsx")
# lista = workbook.get_sheet_by_name('Hoja1')
# linea = 0
# totallista = lista.rows
#
# for filas in totallista[:]:
#     linea += 1
#     if linea > 1:
#         cursor = None
#         if filas[6].value == 2:
#             diapositiva = DiapositivaSilaboSemanal.objects.get(pk=filas[0].value)
#             diapositiva.iddiapositivamoodle = filas[9].value
#             diapositiva.save()
#             print(filas[7].value)
# from sga.funciones import calculate_username, generar_usuario
# persona = Persona.objects.get(cedula='0104732649')
# username = calculate_username(persona)
# generar_usuario(persona, username, variable_valor('INSTRUCTOR_GROUP_ID'))


# res = TestSilaboSemanal.objects.get(pk=7889)
# res.delete()


# profe = Profesor.objects.get(pk=614)
# peri = Periodo.objects.get(pk=113)
# distri = ProfesorDistributivoHoras.objects.filter(periodo=peri)
# print(distri.count())
# a = 0
# for profe in distri:
#     a = a + 1
#     profe.profesor.actualizar_todo_distributivo_docente(None ,peri)
#     print(a)
#
# sila = Silabo.objects.get(pk=16375)
# sila.delete()
#
# sila = PlanificacionClaseSilabo.objects.filter(tipoplanificacion_id=219)
#
# sila.delete()

# per = Persona.objects.get(pk=114647)
# per.delete()


# from sga.funciones import calculate_username, generar_usuario
#
# for i in range(101):
#     if i > 50:
#         personaprofesor = Persona.objects.get(pk=114903)
#         personaprofesor.pk = None
#         personaprofesor.nombres = 'FACE' + str(i)
#         personaprofesor.apellido1 = 'TECNICO DOCENTE' + str(i)
#         personaprofesor.save()
#         username = calculate_username(personaprofesor)
#         generar_usuario(personaprofesor, username, PROFESORES_GROUP_ID)
#         if EMAIL_INSTITUCIONAL_AUTOMATICO:
#             personaprofesor.emailinst = username + '@' + EMAIL_DOMAIN
#             personaprofesor.save()
#         personaprofesor.datos_extension()
#         profesor = Profesor(persona=personaprofesor,
#                             activo=True,
#                             fechaingreso='2021-02-17',
#                             dedicacion_id=1,
#                             categoria_id=1,
#                             cargo_id=2,
#                             nivelcategoria_id=1,
#                             coordinacion_id=5)
#         profesor.save()
#         personaprofesor.crear_perfil(profesor=profesor)
#         personaprofesor.mi_ficha()
#         personaprofesor.mi_perfil()
#         personaprofesor.datos_extension()
#
#         configura = ProfesorConfigurarHoras(periodo_id=113,
#                             profesor=profesor,
#                             horaminima=3,
#                             horamaxima=16,
#                             dedicacion_id=1,
#                             horamaximaasignatura=3)
#         configura.save()
#
#         configuraotro = ProfesorConfigurarHoras(periodo_id=119,
#                                             profesor=profesor,
#                                             horaminima=3,
#                                             horamaxima=16,
#                                             dedicacion_id=1,
#                                             horamaximaasignatura=3)
#         configuraotro.save()
#
#
#         print(profesor)
#

# comple = ComplexivoTematica.objects.values_list('carrera__coordinacion__id','carrera__coordinacion__nombre').get(pk=1878)
# coor = Coordinacion.objects.filter(pk__in=comple[0])
# print(coor)


# import openpyxl
# workbook = openpyxl.load_workbook("graduadosadicionales.xlsx")
# lista = workbook.get_sheet_by_name('Hoja1')
# linea = 0
# totallista = lista.rows
#
# for filas in totallista[:]:
#     linea += 1
#     if linea > 1:
#         perso = Persona.objects.get(cedula=filas[3].value)
#         # if Inscripcion.objects.filter(persona=perso, coordinacion_id=7).exists():
#         #     if Inscripcion.objects.filter(persona=perso, coordinacion_id=7).count() == 1:
#         #         inscri = Inscripcion.objects.get(persona=perso, coordinacion_id=7)
#         #         filas[2].value = inscri.carrera.id
#         #         filas[3].value = inscri.carrera.nombre
#         perfil = perso.mi_perfil()
#         if perfil.tienediscapacidad:
#             filas[10].value = 'SI'
#         else:
#             filas[10].value = 'NO'
#         filas[12].value = perso.direccion + ' ' + perso.direccion2
#         filas[13].value = perso.email
#         filas[14].value = perso.emailinst
#         print(str(filas[3].value))
#     linea += 1
# workbook.save("graduadosadicionales.xlsx")

# respu = RespuestaEvaluacionAcreditacion.objects.filter(proceso_id=99,tipoinstrumento=1,fecha__lt='2021-03-17')
# conta = 0
# print(respu.count())
# for res in respu:
#     conta = conta + 1
#     res.delete()
#     print(conta)

# silsemanal =SilaboSemanal.objects.filter(silabo_id=16407).order_by('id')
# contador = 0
# for semanal in silsemanal:
#     contador = contador + 1
#     # print(contador)
#     semanal.numsemana = contador
#     semanal.save()
#     print(str(semanal.numsemana) + ' - ' + str(semanal.semana)+ ' - ' + str(semanal.fechainiciosemana)+ ' - ' + str(semanal.fechafinciosemana))
# print(str(semanal.numsemana) + ' - ' + str(semanal.fechainicio) + ' - ' + str(semanal.fechafin))

# plamateria = PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia_id=38078).order_by('id')
# print(plamateria.count())
# for plan in plamateria:
#     if SilaboSemanal.objects.filter(silabo_id=16407, numsemana=plan.semana):
#         silsemanal = SilaboSemanal.objects.get(silabo_id=16407, numsemana=plan.semana)
#         silsemanal.fechainiciosemana = plan.fechainicio
#         silsemanal.fechafinciosemana = plan.fechafin
#         silsemanal.semana = plan.fechainicio.isocalendar()[1]
#         silsemanal.save()
#     print(str(plan.semana) + ' - ' + str(plan.fechainicio) + ' - ' + str(plan.fechafin))

# listadistri = ProfesorDistributivoHoras.objects.filter(periodo_id=119)
# print(listadistri.count())
# contador = 0
# for distri in listadistri:
#     contador = contador + 1
#     if ProfesorConfigurarHoras.objects.filter(profesor=distri.profesor,periodo=distri.periodo):
#         confi = ProfesorConfigurarHoras.objects.get(profesor=distri.profesor, periodo=distri.periodo)
#         confi.nivelcategoria=distri.nivelcategoria
#         confi.save()
#     print(str(contador) + ' de ' + str(listadistri.count()))



# ESTADO_SOLICITUD_TUTOR = (
#     (1, u"SOLICITADO"),
#     (2, u"EN TRÁMITE"),
#     (3, u"CERRADO"),
#     (4, u"DEVUELTO"),
# )
# colores = ['','Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
# d=3
# print(ESTADO_SOLICITUD_TUTOR[d-1][1])



# valorrubro = Rubro.objects.filter(status=True, admisionposgradotipo=2, inscripcion_id=4826, cohortemaestria_id=84)
# print(valorrubro.aggregate(valor=Sum('valor'))['valor'])

# LEON CUZCO JONATHAN  JAVIER

# valorsaldo = Rubro.objects.filter(status=True, admisionposgradotipo=2, inscripcion_id=4826).aggregate(valor=Sum('saldo'))['valor']
# print(valorsaldo)

# listamatriculados = MateriaAsignada.objects.filter(materia__asignaturamalla__nivelmalla_id=5,matricula__inscripcion__coordinacion_id=4,matricula__nivel__periodo_id=112)
# print(listamatriculados.count())
# for lista in listamatriculados:
#     contador = lista.matricula.inscripcion.historicorecordacademico_set.filter(recordacademico__aprobada=False,asignatura_id=lista.materia.asignaturamalla.asignatura.id)
#     if contador.count() > 1:
#         print(lista.matricula.inscripcion)
#         print(contador.count())


# listamatriculados = RecordAcademico.objects.values_list('inscripcion_id',flat=True).filter(aprobada=False, status=True,materiaregular__nivel__periodo__tipo_id=2,materiaregular__nivel__periodo__cuentavecesmatricula=True).exclude(inscripcion__coordinacion_id__in=[6,7,8,9,10,11]).distinct()
#
# print(listamatriculados.count())
# contador = 0
# lista = []
# for lis in listamatriculados:
#     inscripcion = Inscripcion.objects.get(pk=lis)
#     if inscripcion.coordinacion_id not in [6,7,8,9,10,11]:
#         if inscripcion.perfil_inscripcion():
#             # if inscripcion.tiene_tercera_matriculasincontarotro():
#             malla = inscripcion.malla_inscripcion().malla
#             for record in RecordAcademico.objects.filter(inscripcion=inscripcion, aprobada=False, asignatura_id__in=[x.asignatura_id for x in malla.asignaturamalla_set.all()]):
#                 if record.historicorecordacademico_set.values("id").filter(status=True).exclude(recordacademico__materiaregular__nivel__periodo__cuentavecesmatricula=False).count() > 3:
#                     print(inscripcion)


# listamaterias = MateriaAsignada.objects.values_list('materia__asignaturamalla__asignatura_id').filter(matricula__inscripcion=inscripcion, estado_id__in=[2,3,4],materia__nivel__periodo__tipo_id=2,materia__nivel__periodo__cuentavecesmatricula=True,status=True).exclude(materia__asignaturamalla__malla__carrera__coordinacion__in=[6,7,8,9,10,11]).distinct()
#
# for mate in listamaterias:
#     numeromaterias =MateriaAsignada.objects.filter(materia__asignaturamalla__asignatura_id=mate,matricula__inscripcion=inscripcion, estado_id__in=[2, 3, 4], materia__nivel__periodo__tipo_id=2, status=True,materia__nivel__periodo__cuentavecesmatricula=True).exclude(materia__asignaturamalla__malla__carrera__coordinacion__in=[6,7,8,9,10,11]).count()
#     querymateria =MateriaAsignada.objects.filter(materia__asignaturamalla__asignatura_id=mate,matricula__inscripcion=inscripcion, estado_id__in=[2, 3, 4], materia__nivel__periodo__tipo_id=2, status=True).exclude(materia__nivel__periodo__cuentavecesmatricula=False,materia__asignaturamalla__malla__carrera__coordinacion__in=[6,7,8,9,10,11])
#     if numeromaterias>3:
#
#         lista.append(inscripcion.id)
#         print(inscripcion.id)
#         print(inscripcion)
#         print(inscripcion.carrera)
#         asig = Asignatura.objects.get(pk__in=mate)
#         print(asig.nombre)
#         print(querymateria.query)




# print(mate.materia.asignaturamalla.asignatura.nombre)
# print(numeromaterias)
# for listadoinscripcion in Inscripcion.objects.filter(pk__in=lista).distinct():
#     print(listadoinscripcion)

# print(contador)
# listamatriculados = MateriaAsignada.objects.values_list('matricula__inscripcion_id',flat=True).filter(estado_id__in=[2,3,4],materia__asignaturamalla__validarequisitograduacion=True, status=True,materia__nivel__periodo__tipo_id=2).exclude(materia__nivel__periodo__cuentavecesmatricula=False).distinct()
#
# print(listamatriculados.count())
# for lis in listamatriculados:
#     inscripcion = Inscripcion.objects.get(pk=lis)
#     if inscripcion.perfil_inscripcion():
#         numeromaterias = MateriaAsignada.objects.filter(materia__asignaturamalla__validarequisitograduacion=True,matricula__inscripcion=inscripcion, estado_id__in=[2,3,4],materia__nivel__periodo__tipo_id=2,status=True).exclude(materia__nivel__periodo__cuentavecesmatricula=False).count()
#         if numeromaterias>2:
#             print(inscripcion)
#             print(inscripcion.carrera)
#             print(numeromaterias)
#
# # listamatriculados = MateriaAsignada.objects.filter(materia__asignaturamalla__validarequisitograduacion=True)
#

# sila = Silabo.objects.get(pk=16580)
#
# print(sila.silabosemanal_set.get(numsemana=4))

# sila = SilaboSemanal.objects.filter(silabo_id__in=[16584])
# sila.delete()

# def aprendizajestemassilabo(lista_items1, idevaluacionaprendizaje,idsilabosemanal, ordenado):
#     if lista_items1:
#         if EvaluacionAprendizajeSilaboSemanal.objects.filter(evaluacionaprendizaje_id=idevaluacionaprendizaje, silabosemanal_id=idsilabosemanal, tipoactividadsemanal=1, status=True):
#             evaluaciontema = EvaluacionAprendizajeSilaboSemanal.objects.get(evaluacionaprendizaje_id=idevaluacionaprendizaje, silabosemanal_id=idsilabosemanal, tipoactividadsemanal=1, status=True)
#         else:
#             evaluaciontema = EvaluacionAprendizajeSilaboSemanal(evaluacionaprendizaje_id=idevaluacionaprendizaje, silabosemanal_id=idsilabosemanal, tipoactividadsemanal=1,numactividad=ordenado)
#             evaluaciontema.save()
#         if not EvaluacionAprendizajeTema.objects.filter(evaluacion=evaluaciontema, temasemanal_id=lista_items1, status=True):
#             ingresoaprendizaje = EvaluacionAprendizajeTema(evaluacion=evaluaciontema, temasemanal_id=lista_items1)
#             ingresoaprendizaje.save()
#
#
# silaporduplicar = Silabo.objects.values_list('profesor_id','materia__asignaturamalla__asignatura_id','materia__asignaturamalla__nivelmalla_id').filter(materia__nivel__periodo_id=113,versionsilabo=2,status=True).distinct()
# contador = 0
# for sila in silaporduplicar:
#     if Silabo.objects.filter(profesor_id=sila[0],materia__asignaturamalla__asignatura_id=sila[1],materia__asignaturamalla__nivelmalla_id=sila[2],materia__nivel__periodo_id=113,versionsilabo=2,status=True).count() > 1:
#         cuentallenostemassemanales = EvaluacionAprendizajeTema.objects.values_list('temasemanal__silabosemanal__silabo_id').filter(temasemanal__silabosemanal__silabo_id__in=Silabo.objects.values_list('id').filter(profesor_id=sila[0],materia__asignaturamalla__asignatura_id=sila[1],materia__asignaturamalla__nivelmalla_id=sila[2],materia__nivel__periodo_id=113,versionsilabo=2,status=True)).distinct().count()
#         if cuentallenostemassemanales == 1:
#             contador = contador + 1
#             print(cuentallenostemassemanales)
#         else:
#             print(Profesor.objects.get)
# print(contador)


# silaporduplicar = Silabo.objects.get(pk=16602)

# silaboxduplicar = Silabo.objects.get(pk=silaporduplicar.id)
# silaboaduplicar = Silabo.objects.get(pk=16604)
# idcarreradestino = silaboaduplicar.materia.asignaturamalla.malla.carrera.id
# listadostestmigrar = []
# if not silaboaduplicar.silabosemanal_set.filter(status=True).exists():
#     if silaboaduplicar.materia.tiene_cronograma():
#         planificacionsilaboact = PlanificacionClaseSilabo.objects.filter(
#             tipoplanificacion__planificacionclasesilabo_materia__materia=silaboaduplicar.materia, status=True).exclude(
#             semana=0).order_by('orden')
#         for pact in planificacionsilaboact:
#             pant = PlanificacionClaseSilabo.objects.filter(
#                 tipoplanificacion__planificacionclasesilabo_materia__materia=silaboxduplicar.materia, status=True,
#                 semana=pact.semana)[0]
#             if silaboxduplicar.silabosemanal_set.filter(status=True, fechainiciosemana__gte=pant.fechainicio,
#                                                         fechafinciosemana__lte=pant.fechafin).exists():
#                 semana = silaboxduplicar.silabosemanal_set.filter(status=True, fechainiciosemana__gte=pant.fechainicio,
#                                                                   fechafinciosemana__lte=pant.fechafin)[0]
#                 if semana:
#                     silabosemana = SilaboSemanal(silabo=silaboaduplicar,
#                                                  numsemana=pact.semana,
#                                                  semana=pact.fechainicio.isocalendar()[1],
#                                                  fechainiciosemana=pact.fechainicio,
#                                                  fechafinciosemana=pact.fechafin,
#                                                  objetivoaprendizaje=semana.objetivoaprendizaje,
#                                                  enfoque=semana.enfoque,
#                                                  enfoquedos=semana.enfoquedos,
#                                                  enfoquetres=semana.enfoquetres,
#                                                  recursos=semana.recursos,
#                                                  evaluacion=semana.evaluacion,
#                                                  horaspresencial=semana.horaspresencial,
#                                                  horaautonoma=semana.horaautonoma
#                                                  )
#                     silabosemana.save()
#
#                     if semana.detallesilabosemanalbibliografia_set.filter(status=True).exists():
#                         for blibliografiabasia in semana.detallesilabosemanalbibliografia_set.filter(status=True):
#                             idlibroacopiar = blibliografiabasia.bibliografiaprogramaanaliticoasignatura.librokohaprogramaanaliticoasignatura.id
#                             proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura
#                             if BibliografiaProgramaAnaliticoAsignatura.objects.filter(
#                                     librokohaprogramaanaliticoasignatura_id=idlibroacopiar,
#                                     programaanaliticoasignatura=proganaliticoasigdestino, status=True).exists():
#                                 detallebb = DetalleSilaboSemanalBibliografia(silabosemanal=silabosemana,
#                                                                              bibliografiaprogramaanaliticoasignatura=blibliografiabasia.bibliografiaprogramaanaliticoasignatura,
#                                                                              status=True)
#                                 detallebb.save()
#
#                     if semana.detallesilabosemanalbibliografiadocente_set.filter(status=True).exists():
#                         for bibliografiacomplementaria in semana.detallesilabosemanalbibliografiadocente_set.filter(
#                                 status=True):
#                             detallebc = DetalleSilaboSemanalBibliografiaDocente(silabosemanal=silabosemana,
#                                                                                 librokohaprogramaanaliticoasignatura=bibliografiacomplementaria.librokohaprogramaanaliticoasignatura,
#                                                                                 status=True)
#                             detallebc.save()
#
#                     temaprogramadestino = None
#
#                     listaunidadtema = []
#
#                     if semana.detallesilabosemanaltema_set.filter(status=True,
#                                                                   temaunidadresultadoprogramaanalitico__status=True).exists():
#                         for itemtema in semana.detallesilabosemanaltema_set.filter(status=True,
#                                                                                    temaunidadresultadoprogramaanalitico__status=True):
#                             numerotemaorigen = itemtema.temaunidadresultadoprogramaanalitico.orden
#                             textoorigen = itemtema.temaunidadresultadoprogramaanalitico.descripcion
#                             unidadorigen = itemtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden
#                             listaunidadtema.append([unidadorigen, numerotemaorigen])
#                             proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura
#                             proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura.asignaturamalla
#                             temaprogramadestino = TemaUnidadResultadoProgramaAnalitico.objects.filter(
#                                 unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=proganaliticoasigdestino,
#                                 unidadresultadoprogramaanalitico__orden=unidadorigen, orden=numerotemaorigen,
#                                 status=True, unidadresultadoprogramaanalitico__status=True,
#                                 unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__status=True,
#                                 unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__status=True,
#                                 unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True)
#
#                             if temaprogramadestino:
#                                 temadestino = temaprogramadestino[0]
#                                 if itemtema.objetivoaprendizaje:
#                                     obj = itemtema.objetivoaprendizaje
#                                 else:
#                                     obj = silabosemana.objetivoaprendizaje
#                                 tema = DetalleSilaboSemanalTema(silabosemanal=silabosemana,
#                                                                 temaunidadresultadoprogramaanalitico=temadestino,
#                                                                 objetivoaprendizaje=obj, status=True)
#                                 tema.save()
#                                 listadostestmigrar.append([itemtema.id, tema.id])
#
#
#                     if semana.bibliograbiaapasilabo_set.filter(status=True).exists():
#                         for bibliografiavirtual in semana.bibliograbiaapasilabo_set.filter(status=True):
#                             bibli = BibliograbiaAPASilabo(silabosemanal=silabosemana,
#                                                           bibliografia=bibliografiavirtual.bibliografia)
#                             bibli.save()
#
#                     if temaprogramadestino:
#                         temadestino = temaprogramadestino[0]
#
#                         if semana.detallesilabosemanalsubtema_set.filter(status=True,
#                                                                          subtemaunidadresultadoprogramaanalitico__status=True).exists():
#                             for itemsubtema in semana.detallesilabosemanalsubtema_set.filter(status=True,
#                                                                                              subtemaunidadresultadoprogramaanalitico__status=True):
#                                 numerosubtemaorigen = itemsubtema.subtemaunidadresultadoprogramaanalitico.orden
#                                 textosubtemaorigen = itemsubtema.subtemaunidadresultadoprogramaanalitico.descripcion
#                                 proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura
#                                 proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura.asignaturamalla
#
#                                 for itemtema in listaunidadtema:
#                                     unidadorigenlista = itemtema[0]
#                                     numerotemaorigenlista = itemtema[1]
#
#                                     if unidadorigenlista == 2 and numerotemaorigenlista == 3:
#                                         print("Hola")
#
#                                     subtemaprogramadestino = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(
#                                         temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=proganaliticoasigdestino,
#                                         temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=unidadorigenlista,
#                                         temaunidadresultadoprogramaanalitico__orden=numerotemaorigenlista,
#                                         temaunidadresultadoprogramaanalitico__status=True, orden=numerosubtemaorigen,
#                                         status=True,
#                                         temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__status=True,
#                                         temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__status=True,
#                                         temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__status=True,
#                                         temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True)
#
#                                     for subtemadestino in subtemaprogramadestino:
#                                         if not DetalleSilaboSemanalSubtema.objects.filter(silabosemanal=silabosemana,
#                                                                                           subtemaunidadresultadoprogramaanalitico=subtemadestino,
#                                                                                           status=True).exists():
#                                             subtema = DetalleSilaboSemanalSubtema(silabosemanal=silabosemana,
#                                                                                   subtemaunidadresultadoprogramaanalitico=subtemadestino,
#                                                                                   status=True)
#                                             subtema.save()
#
#                     if semana.recursosdidacticossemanal_set.filter(status=True).exists():
#                         for recurso in semana.recursosdidacticossemanal_set.filter(status=True):
#                             recurso = RecursosDidacticosSemanal(silabosemanal=silabosemana,
#                                                                 descripcion=recurso.descripcion, link=recurso.link)
#                             recurso.save()
#                     if semana.articulosilabosemanal_set.filter(status=True).exists():
#                         for articulo in semana.articulosilabosemanal_set.filter(status=True):
#                             a = ArticuloSilaboSemanal(silabosemanal=silabosemana, articulo=articulo.articulo)
#                             a.save()
#                     if silaboaduplicar.versionsilabo == 1:
#                         if semana.evaluacionaprendizajesilabosemanal_set.filter(status=True).exists():
#                             for articulo in semana.evaluacionaprendizajesilabosemanal_set.filter(status=True):
#                                 a = EvaluacionAprendizajeSilaboSemanal(silabosemanal=silabosemana,
#                                                                        evaluacionaprendizaje=articulo.evaluacionaprendizaje)
#                                 a.save()
#
#         if silaboaduplicar.versionsilabo == 2:
#             if listadostestmigrar:
#                 ordentest = 0
#                 listadoaprendizaje = EvaluacionAprendizajeComponente.objects.filter(status=True)
#                 for listami in listadostestmigrar:
#                     idtemaantiguo = listami[0]
#                     idtemaactual = ''
#                     for lisaprendizaje in listadoaprendizaje:
#                         if EvaluacionAprendizajeTema.objects.filter(temasemanal_id=listami[0],
#                                                                     evaluacion__evaluacionaprendizaje_id=lisaprendizaje.id,
#                                                                     evaluacion__tipoactividadsemanal=1, status=True):
#                             itentest = EvaluacionAprendizajeTema.objects.get(temasemanal_id=listami[0],
#                                                                              evaluacion__evaluacionaprendizaje_id=lisaprendizaje.id,
#                                                                              evaluacion__tipoactividadsemanal=1,
#                                                                              status=True)
#                             semanaactual = silaboaduplicar.silabosemanal_set.get(
#                                 numsemana=itentest.evaluacion.silabosemanal.numsemana)
#                             ordentest = itentest.evaluacion.numactividad
#                             aprendizajestemassilabo(listami[1], lisaprendizaje.id, semanaactual.id, ordentest)
#
# print('listo')
#
#
# listadosilabo = Silabo.objects.filter(materia__nivel__periodo_id=113,versionsilabo=2)
# for sila in listadosilabo:
#     if PlanificacionClaseSilabo.objects.values_list('tipoplanificacion__nombre').filter(tipoplanificacion_id=270,tipoplanificacion__planificacionclasesilabo_materia__materia=sila.materia, status=True):
#         plan = PlanificacionClaseSilabo.objects.values_list('tipoplanificacion__nombre').filter(tipoplanificacion__planificacionclasesilabo_materia__materia=sila.materia, status=True)[0]
#         totalplan = PlanificacionClaseSilabo.objects.values_list('tipoplanificacion__nombre').filter(tipoplanificacion__planificacionclasesilabo_materia__materia=sila.materia, status=True).count()
#         print(totalplan)
#         print(plan)
#         listasilabosemanal=SilaboSemanal.objects.filter(silabo=sila,numsemana__in=[8,16])
#         for lissemanal in listasilabosemanal:
#             lissemanal.delete()


#
# tipoprofesores = (
#     (1, u'TEORIA'),
#     (2, u'PRACTICA'),
#     (7, u'VIRTUAL'),
#     (11, u'AUTOR 2'),
#     (12, u'AUTOR 1'),
#     (10, u'ORIENTACION')
# )
# listadias = DIAS_CHOICES
# listadomateria = Materia.objects.filter(nivel__periodo_id=113)
# # listadomateria = Materia.objects.filter(pk=38074)
# contador = listadomateria.count()
# con = 0
# for lismate in  listadomateria:
#     con = con + 1
#     for lisdia in listadias:
#         for tipo in tipoprofesores:
#             if Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]):
#                 listaclase = Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]).order_by('-id')
#                 clasetrue = Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]).order_by('-turno__comienza')[0]
#                 clasetrue.subirenlace = True
#                 clasetrue.save()
#                 for lclase in listaclase:
#                     if lclase.id != clasetrue.id:
#                         lclase.subirenlace = False
#                         lclase.save()
#
#     print(str(con) + " de " +str(contador))
# silalistado = Silabo.objects.filter(materia__nivel__periodo_id=113,codigoqr=True).exclude(materia__asignaturamalla__malla__carrera_id=139)
# for idsilabo in silalistado:
#     idsilabo.codigoqr=False
#     idsilabo.save()
#     elimi = AprobarSilabo.objects.filter(silabo_id=idsilabo.id)
#     elimi.delete()
# print(silalistado.query)
# print(silalistado.count())
#
# listadosilabo = Silabo.objects.filter(materia__nivel__periodo_id=113,status=True)
#
# for lista in listadosilabo:
#     if lista.aprobarsilabo_set.filter(estadoaprobacion=1,status=True):
#         aprobado=lista.aprobarsilabo_set.filter(status=True).order_by('-id')[0]
#         if aprobado.estadoaprobacion == 1:
#             # lista.codigoqr = False
#             # lista.save()
#             print(lista.id)
#             print(aprobado)
#             print(lista.codigoqr)



#PARA ACTUALIZAR Y ELMINAR  SEMANA DE EXAMENES SE SILABOS
#---------------------------------------
# listadosilabo = Silabo.objects.filter(materia__nivel__periodo_id=113,versionsilabo=2)
# for sila in listadosilabo:
#     if PlanificacionClaseSilabo.objects.values_list('tipoplanificacion__nombre').filter(tipoplanificacion_id=270,tipoplanificacion__planificacionclasesilabo_materia__materia=sila.materia, status=True):
#         plan = PlanificacionClaseSilabo.objects.values_list('tipoplanificacion__nombre').filter(tipoplanificacion__planificacionclasesilabo_materia__materia=sila.materia, status=True)[0]
#         totalplan = PlanificacionClaseSilabo.objects.values_list('tipoplanificacion__nombre').filter(tipoplanificacion__planificacionclasesilabo_materia__materia=sila.materia, status=True).count()
#         print(totalplan)
#         print(plan)
#         listasilabosemanal=SilaboSemanal.objects.filter(silabo=sila,numsemana__in=[8,16])
#         for lissemanal in listasilabosemanal:
#             lissemanal.delete()
#
# tipoprofesores = (
#     (1, u'TEORIA'),
#     (2, u'PRACTICA'),
#     (7, u'VIRTUAL'),
#     (11, u'AUTOR 2'),
#     (12, u'AUTOR 1'),
#     (10, u'ORIENTACION')
# )
# listadias = DIAS_CHOICES
# listadomateria = Materia.objects.filter(nivel__periodo_id=113)
# contador = listadomateria.count()
# con = 0
# for lismate in  listadomateria:
#     con = con + 1
#     for lisdia in listadias:
#         for tipo in tipoprofesores:
#             if Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]):
#                 listaclase = Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]).order_by('-id')
#                 clasetrue = Clase.objects.filter(materia=lismate, dia=lisdia[0], tipoprofesor_id=tipo[0]).order_by('-turno__comienza')[0]
#                 clasetrue.subirenlace = True
#                 clasetrue.save()
#                 for lclase in listaclase:
#                     if lclase.id != clasetrue.id:
#                         lclase.subirenlace = False
#                         lclase.save()
#
#     print(str(con) + " de " +str(contador))
#
#----------------------------------------
# silalistado = Silabo.objects.filter(materia__nivel__periodo_id=113,codigoqr=True).exclude(materia__asignaturamalla__malla__carrera_id=139)
# for idsilabo in silalistado:
#     idsilabo.codigoqr=False
#     idsilabo.save()
#     elimi = AprobarSilabo.objects.filter(silabo_id=idsilabo.id)
#     elimi.delete()
# print(silalistado.query)
# print(silalistado.count())
#
# TareaSilaboSemanal.objects.filter(silabosemanal__silabo__materia_id=43762).update(estado_id=1,idtareamoodle=0)
# TareaPracticaSilaboSemanal.objects.filter(silabosemanal__silabo__materia_id=43762).update(estado_id=1,idtareapracticamoodle=0)
# TestSilaboSemanal.objects.filter(silabosemanal__silabo__materia_id=43762).update(estado_id=1,idtestmoodle=0)
# ForoSilaboSemanal.objects.filter(silabosemanal__silabo__materia_id=43762).update(estado_id=1,idforomoodle=0)


# silabo = Silabo.objects.get(pk=18262)
# listado = Periodo.objects.filter(pk__gte=95, pk__lte=silabo.materia.nivel.periodo.id,tipo=silabo.materia.nivel.periodo.tipo,status=True).exclude(tipo_id__in=[3,4]).order_by('-inicio')
# print(listado.query)

# listadoabecedario = [[0, '-'],[1, 'A'], [2, 'B'], [2, 'C'], [3, 'D'], [4, 'E'], [5, 'F'], [6, 'G'], [7, 'H'], [8, 'I']]
# d = 1
# print(listadoabecedario[d][1])


# listamaterial = consulatamateriales.values_list('material_id', 'material__silabosemanal_id').annotate(
#   formatted_date=Func(
#     F('fecha_creacion'),
#     Value('yyyy-MM-dd'),
#     function='to_char',
#     output_field=DateField()
#   )
# ).distinct()
# listamaterial = listamaterial.extra(select={'fecha':"to_char(fecha_creacion, 'YYYY-MM-DD')"})

# print(listamaterial.count())
# import warnings
# warnings.filterwarnings('ignore', message='Unverified HTTPS request')
# listadomateria = Materia.objects.filter(nivel__periodo_id__in=[125,127,129,130], status=True)
# print(listadomateria.count())
# clave = 'docente'
# for materia in listadomateria:
#     materia.crear_actualizar_categoria_notas_curso_posgrado(clave)
#     print(materia)
#
# listado = RubricaTitulacion.objects.filter(rubrica_id=3)
# listadopon =  RubricaTitulacionCabPonderacion.objects.filter(rubrica_id=3)
# print(listado.count())
# for lis in listado:
#     for lispon in listadopon:
#         if lispon.id == 14:
#             rubponderacion = RubricaTitulacionPonderacion(detallerubrica=lis,
#                                                           ponderacionrubrica=lispon,
#                                                           leyenda=lis.leyendaexcelente,
#                                                           descripción=lis.excelente)
#             rubponderacion.save()
#         if lispon.id == 15:
#             rubponderacion = RubricaTitulacionPonderacion(detallerubrica=lis,
#                                                           ponderacionrubrica=lispon,
#                                                           leyenda=lis.leyendamuybueno,
#                                                           descripción=lis.muybueno)
#             rubponderacion.save()
#         if lispon.id == 16:
#             rubponderacion = RubricaTitulacionPonderacion(detallerubrica=lis,
#                                                           ponderacionrubrica=lispon,
#                                                           leyenda=lis.leyendabueno,
#                                                           descripción=lis.bueno)
#             rubponderacion.save()
#         if lispon.id == 17:
#             rubponderacion = RubricaTitulacionPonderacion(detallerubrica=lis,
#                                                           ponderacionrubrica=lispon,
#                                                           leyenda=lis.leyendasuficiente,
#                                                           descripción=lis.suficiente)
#             rubponderacion.save()
#         print(lispon.ponderacion)


# listacomple = ComplexivoDetalleGrupo.objects.filter(pk__in=CalificacionRubricaTitulacion.objects.values_list('complexivodetallegrupo_id').filter(status=True).distinct())
# for comple in listacomple:
#     print(comple)
#     if comple.rubrica and comple.actacerrada:
#         if comple.matricula.alternativa.tipotitulacion.tipo == 2:
#             if ((float(comple.notafinal()) + float(comple.calificacion)) / 2) >= 70:
#                 comple.estadotribunal = 2
#             else:
#                 comple.estadotribunal = 3
#             comple.save()
#         else:
#             if float(comple.calificacion) >= 70:
#                 comple.estadotribunal = 2
#             else:
#                 comple.estadotribunal = 3
#             comple.save()
# listado = SeguimientoTutor.objects.get(pk=6665)
# listado.delete()

# import jwt
# import requests
# import json
# from time import time
#
# # Enter your API key and your API secret
# API_KEY = 'OuGO0LD3Tp6pZ449pLJDqg'
# API_SEC = 'XkQv9cSJNwCYdnBnkpLaTa6sNGhlbSXOzZHP'
#
# meetingId = 83781439159
#
# userId = 'you can get your user Id by running the getusers()'
#
# # create a function to generate a token using the pyjwt library
# def generateToken():
#     token = jwt.encode(
#         # Create a payload of the token containing API Key & expiration time
#         {'iss': API_KEY, 'exp': time() + 5000},
#         # Secret used to generate token signature
#         API_SEC,
#         # Specify the hashing alg
#         algorithm='HS256'
#         # Convert token to utf-8
#     )
#     return token
#     # send a request with headers including a token
#
# #fetching zoom meeting info now of the user, i.e, YOU
# def getUsers():
#     headers = {'authorization': 'Bearer %s' % generateToken(),
#                'content-type': 'application/json'}
#
#     r = requests.get('https://api.zoom.us/v2/users/', headers=headers)
#     print("\n fetching zoom meeting info now of the user ... \n")
#     print(r.text)
#
#
# #fetching zoom meeting participants of the live meeting
#
# def getMeetingParticipants():
#     headers = {'authorization': 'Bearer %s' % generateToken(),
#                'content-type': 'application/json'}
#     r = requests.get(
#         f'https://api.zoom.us/v2/metrics/meetings/{meetingId}/participants', headers=headers)
#     print("\n fetching zoom meeting participants of the live meeting ... \n")
#
#     # you need zoom premium subscription to get this detail, also it might not work as i haven't checked yet(coz i don't have zoom premium account)
#
#     print(r.text)
#
#
# # this is the json data that you need to fill as per your requirement to create zoom meeting, look up here for documentation
# # https://marketplace.zoom.us/docs/api-reference/zoom-api/meetings/meetingcreate
#
#
# meetingdetails = {"topic": "The title of your zoom meeting",
#                   "type": 2,
#                   "start_time": "2019-06-14T10: 21: 57",
#                   "duration": "45",
#                   "timezone": "Europe/Madrid",
#                   "agenda": "test",
#
#                   "recurrence": {"type": 1,
#                                  "repeat_interval": 1
#                                  },
#                   "settings": {"host_video": "true",
#                                "participant_video": "true",
#                                "join_before_host": "False",
#                                "mute_upon_entry": "False",
#                                "watermark": "true",
#                                "audio": "voip",
#                                "auto_recording": "cloud"
#                                }
#                   }
#
# def createMeeting():
#     headers = {'authorization': 'Bearer %s' % generateToken(),
#                'content-type': 'application/json'}
#     r = requests.post(
#         f'https://api.zoom.us/v2/users/{userId}/meetings', headers=headers, data=json.dumps(meetingdetails))
#
#     print("\n creating zoom meeting ... \n")
#     print(r.text)
#
# getUsers()
# # getMeetingParticipants()
# createMeeting()
# matriculados = Matricula.objects.filter(nivel__periodo_id=86).order_by('inscripcion__persona__apellido1')
# i = 0
# for matri in matriculados:
#     i = i + 1
#     # if matri.id == 185769:
#     listarecord = matri.inscripcion.recordacademico_set.filter(asignatura_id__in=[4272,4278,4282,4274])
#     for record in listarecord:
#         record.valida = False
#         record.save()
#         historico = record.mi_historico()
#         if historico:
#             historico.valida = record.valida
#             historico.save()
#
#         record.validapromedio = False
#         record.save()
#         historico = record.mi_historico()
#         if historico:
#             historico.validapromedio = record.validapromedio
#             historico.save()
#     print(str(matriculados.count()) + ' - ' + str(i) + ' - ' + str(matri.inscripcion.id) + ' - ' + str(matri.id) + ' - ' + str(matri))
# #
# configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=13)
# periodo = configuracion.periodo
# carrera = configuracion.carrera
# listadotemas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, revisiontutoriastematitulacionposgradoprofesor__estado=2).distinct().order_by('-tribunaltematitulacionposgradomatricula__fechadefensa')
# print(listadotemas.count())
# for idtema in listadotemas:
#     idmaestrantegrupo = TemaTitulacionPosgradoMatricula.objects.get(pk=idtema.id)
#     idmaestrantegrupo.cerraracta_posgrado()
#     print(idtema)
import math

# perso = Persona.objects.get(cedula='0923363030')
# print(perso.cedula[2:])
#
# clase = Clase.objects.filter(materia_id=45283,activo=True).order_by('inicio','fin','dia','turno__comienza')
# print(clase)

from PyPDF2 import PdfFileReader
# pdf_path=r"D:\git\academico\0923363030.pdf"
# temp = open('0923363030.pdf', 'rb')
# pdfReader = PyPDF2.PdfFileReader(pdfFileObject)
# text=''
# for i in range(0,pdfReader.numPages):
#     # creating a page object
#     pageObj = pdfReader.getPage(i)
#     # extracting text from page
#     text=text+pageObj.extractText()
# print(text)
# temp = open('0923363030.pdf', 'rb')
# PDF_read = PdfFileReader(temp)
# first_page = PDF_read.getPage(0)
# second_page = PDF_read.getPage(1)
# print(first_page.extractText())
# print(second_page.extractText())

# invitacion = InscripcionInvitacion.objects.filter(status=True)
# invitacion.delete()
#
# rubro = Rubro.objects.get(pk=317513)
# fecha = datetime.strptime(str(rubro.fecha_creacion.date()),"%Y-%m-%d")
# rpago = rubro.pago_set.filter(status=True)[0]
# fechaabonorubro = datetime.strptime(str(rpago.fecha),"%Y-%m-%d")
#
# print(fecha)
# print(fechaabonorubro)
# print(fechaabonorubro-fecha)
#
# # navidad = datetime.strptime("2021-12-25", "%Y-%m-%d")
# # fin_anio = datetime.strptime("2021-12-31", "%Y-%m-%d")
# # diferencia = fin_anio-navidad
# # print(diferencia)
#
# print(int(encrypt('OPPQQRRSSTTUUVVSRVQU')))

# lista =PlanificacionClaseSilabo.objects.filter(
#                 tipoplanificacion__planificacionclasesilabo_materia__materia_id=54911, status=True,
#                 fechainicio__lte='2022-05-03', fechafin__gte='2022-05-27')
#
# print(lista.query)

# import pyqrcode
# url = pyqrcode.create('http://127.0.0.1:8000/')
# url.png('code.png', scale=5)

# import pyqrcode
# from pyqrcode import QRCode
#
# # URL string
# site = "http://127.0.0.1:8000/"
#
# # Generate QR code
# getqrcode = pyqrcode.create(site,
#                             error='H',
#                             version=20,
#                             mode='binary')
#
# # save in png file format
# getqrcode.png('siteQR.png', scale=2,
#               background=[0x00, 0xff, 0xbf])

# import pyqrcode
# url = pyqrcode.create('http://127.0.0.1:8000/')
# url.svg('uca-url.svg', scale=8)
# url.eps('uca-url.eps', scale=2)
# url.png_as_base64_str('siteQR.png', scale=1)
# print(url.terminal(quiet_zone=1))
# import qrcode
# img = qrcode.make('http://127.0.0.1:8000//media/qrcode/silabodocente/')
# type(img)  # qrcode.image.pil.PilImage
# img.save("some_file.png")

# Materia.objects.annotate(num_books=Count('book'))
# mate = Materia.objects.filter(nivel__periodo_id=112).count()
#
# mates = Materia.objects.annotate(num_books=Count('materiaasignada'))
# print(mates.query)
# for lista in mates:
#
#     print(lista.asignaturamalla.malla.carrera)
#     print(lista.id)
#     print(lista.num_books)
#     # print(mates[0])


# Nivel.objects.filter(nivellibrecoordinacion__coordinacion=coordinacion, periodo=periodo).annotate(nummatri=Count('materia__materiaasignada',distinct=True), matricula__estado_matricula__in=[2, 3], matricula__status=True, matricula__retiradomatricula=False)
# listamatri = Nivel.objects.filter(nivellibrecoordinacion__coordinacion_id=4, periodo_id=119).annotate(nummatri=Count('matricula',distinct=True, status=True, matricula__estado_matricula__in=[2, 3], matricula__status=True, matricula__retiradomatricula=False))
# listamatri = Nivel.objects.filter(nivellibrecoordinacion__coordinacion_id=4, periodo_id=119).annotate(nummatri=Count('matricula__id',distinct=True,  filter=Q(matricula__estado_matricula__in=[2, 3], matricula__status=True, matricula__retiradomatricula=False)))
# print(listamatri.query)
# for lista in listamatri:
#     print(lista)
#     print(lista.nummatri)


# listado = ProfesorMateria.objects.filter(activo=True, status=True, materia__nivel__periodo__visible=True, materia__nivel__periodo_id=126).annotate(de=F('materia__silabo', filter=Q(materia__status=True)))
# # listados = listado.annotate(nummatri=Count('materia__silabo__id'))
# print(listado.query)
# print(listado.query)
# print(listado.count())
# # .annotate(nummatri=Count('materia__silabo__id'))
# 3656

# nivel = Nivel.objects.get(pk=666)
# # materias = nivel.materia_set.filter(status=True, asignaturamalla__malla_id=228).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id').annotate(value=F('materiaasignada__materia',distinct=True))
# materias = nivel.materia_set.filter(status=True, asignaturamalla__malla_id=222).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id', 'materiaasignada__materia_id').annotate(nummatri=Count('materiaasignada__id',distinct=True, filter=Q(materiaasignada__materiaasignadaretiro__isnull=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__status=True))).annotate(sinretiradosinscritos=Count('materiaasignada__id',distinct=True, filter=Q(materiaasignada__materiaasignadaretiro__isnull=True, materiaasignada__matricula__estado_matricula=1, materiaasignada__status=True)))
#
# print(materias.query)
# print(materias.count())
# # for listamate in materias:
# #     print(listamate.tiene_matriculas())
#
#
# from django.contrib.postgres.aggregates import StringAgg, ArrayAgg
# from django.db.models.functions import Cast
# from django.db.models import TextField
#
# listadotipo = TipoProfesor.objects.filter(status=True).annotate(AggregatedType = StringAgg(Cast('nombre', TextField()),delimiter=','))
# # listadotipo.annotate(AggregatedType = StringAgg(Cast('nombre', TextField()),delimiter=','))
#
# queryset = TipoProfesor.objects.annotate(
#     phone_numbers=StringAgg('nombre', delimiter=',')
# ).order_by('nombre')
#
#
# # queryset = TipoProfesor.objects.filter(status=True)
# from django.db.models import Aggregate, CharField, Value
#
# class GroupConcat(Aggregate):
#     function = 'GROUP_CONCAT'
#     template = '%(function)s(%(expressions)s)'
#
#     def __init__(self, expression, delimiter, **extra):
#         output_field = extra.pop('output_field', CharField())
#         delimiter = Value(delimiter)
#         super(GroupConcat, self).__init__(
#             expression, delimiter, output_field=output_field, **extra)
#
#     def as_postgresql(self, compiler, connection):
#         self.function = 'STRING_AGG'
#         return super(GroupConcat, self).as_sql(compiler, connection)
#
# from django.contrib.postgres.aggregates import StringAgg
# from django.db.models.functions import Cast
# from django.db.models import TextField
# from django.db.models.functions import Concat
# # materias = nivel.materia_set.filter(status=True, asignaturamalla__malla_id=207).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id', 'materiaasignada__materia_id').annotate(nummatri=Count('materiaasignada__id',distinct=True, filter=Q(materiaasignada__materiaasignadaretiro__isnull=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__status=True))).annotate(sinretiradosinscritos=Count('materiaasignada__id',distinct=True, filter=Q(materiaasignada__materiaasignadaretiro__isnull=True, materiaasignada__matricula__estado_matricula=1, materiaasignada__status=True))).annotate(distinct_concatenation=StringAgg(Cast('clase__turno__turno',TextField()),delimiter=',', output_field=TextField(),distinct=True))
# materias = nivel.materia_set.filter(status=True, asignaturamalla__malla_id=207).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id', 'materiaasignada__materia_id').annotate(nummatri=Count('materiaasignada__id',distinct=True, filter=Q(materiaasignada__materiaasignadaretiro__isnull=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__status=True))).annotate(sinretiradosinscritos=Count('materiaasignada__id',distinct=True, filter=Q(materiaasignada__materiaasignadaretiro__isnull=True, materiaasignada__matricula__estado_matricula=1, materiaasignada__status=True))).annotate(distinct_concatenation=Concat('clase__turno__turno', Value('a string'), output_field=CharField()))

# query = TipoProfesor.objects.filter(status=True).annotate(
#         AggregatedType = StringAgg(Cast('nombre', TextField()),delimiter=',', output_field=TextField())
#     )
# lista = Persona.objects.filter(pk=813,status=True).annotate(distinct_concatenation=StringAgg('inscripcion__carrera__alias',delimiter=','))
# print(lista.query)

# materia = Materia.objects.get(pk=54453, status=True)
# materia.crear_materia_categoria_notas_curso_pregrado()
# import warnings
# warnings.filterwarnings('ignore', message='Unverified HTTPS request')
#
#
# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
# your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# sys.path.append(your_djangoproject_home)
#
# from django.core.wsgi import get_wsgi_application
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# application = get_wsgi_application()
#
# from sga.models import *
# from moodle import moodle
#
# # from django.db import connections
# # cursor = connections['moodle_db'].cursor()
# from Moodle_Funciones import crearhtmlphpmoodle
# #servidor
# AGREGAR_ESTUDIANTE = True
# AGREGAR_DOCENTE = True
# AGREGAR_SILABO = True
# AGREGAR_MODELO_NOTAS = True
# TIPO_AULA_VIRTUAL = True
# parent_grupoid = 0
# tipourl = 1
# #ID:121 ABRIL- MAYO 2021
# periodo = Periodo.objects.get(pk=126)
# bcursoc = moodle.BuscarCursos(periodo, 1, 'idnumber', 5169)
# print(bcursoc)
# bcurso = moodle.BuscarCursoModulo(periodo, 1, 18)
# print(bcurso)
# # bgrupo = moodle.BuscarCategoriasid(periodo, 1, 2)
# # print(bgrupo)
#
#
# sila = Silabo.objects.get(pk=21939)
# lsemana = sila.silabosemanal_set.filter(status=True).annotate(nummatri=Count('diapositivasilabosemanal',distinct=True,  filter=Q(diapositivasilabosemanal__status=False)))
# print(lsemana.query)
# silaboact = Silabo.objects.get(status=True, pk=int(request.POST['ida']))
# sila = Silabo.objects.filter(status=True, programaanaliticoasignatura_id=2714, materia__asignaturamalla__id=5134, materia__nivel__periodo__id=119)


# print(sila.count())

import datetime
# fecha = '2018-06-29'
# hor = '08:30:00'
# date_time_str = fecha + ' ' + hor
# date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')



# comple = ComplexivoGrupoTematica.objects.get(pk=4)
#
# date_time_str = str(comple.fechadefensa) + ' ' + str(comple.horadefensa)
# date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
# # print(str(date_time_obj.time())[:5])
#
# listatur = TurnoTitulacion.objects.filter(status=True).order_by('id')
# hora = '08:30:00'
# print(listatur.values('comienza'))

# print(encrypt(4837))
# print(int(encrypt('OPPQQRRSSTTUUVVSNWVP')))

# print(date_time_str.day())
#
# print('Date:', date_time_obj.date())
# print('Time:', date_time_obj.time())

# lista=EvaluacionAprendizajeTema.objects.filter(temasemanal__silabosemanal_id=337243)
# print(lista.count())
# lisin = EvaluacionAprendizajeTema.objects.filter(evaluacion__silabosemanal_id=337243,evaluacion__silabosemanal__status=True, evaluacion__tipoactividadsemanal=1, temasemanal__silabosemanal__status=True, temasemanal__silabosemanal__silabo__status=True, temasemanal__status=True, status=True).distinct()
# print(lisin.count())


# listadocod = EvaluacionAprendizajeTema.objects.values_list('id','evaluacion_id').filter(pk__in=[276855,276856])
# for cod in listadocod:
# print(cod[0])
# print(cod[1])
# print(cod.temasemanal.silabosemanal.numsemana)

# listadoeval = EvaluacionAprendizajeTema.objects.filter(evaluacion__silabosemanal__silabo_id=23299, evaluacion__tipoactividadsemanal=1)
#
# for lisev in listadoeval:
#     print(lisev.status)
# incripciones_mallas = []
# # silasemanal = SilaboSemanal.objects.filter(pk__in=[332038,357393])
# silasemanal = SilaboSemanal.objects.get(pk=332038)
# silasemanal.__setattr__('promediototal', '45765')
# silasemanal.__setattr__('ted', 'fecs')
# incripciones_mallas.append(silasemanal)
# inscripciones = sorted(incripciones_mallas, key=lambda silasemanal: silasemanal.promediototal, reverse=True)
# print(inscripciones)
# for sila in silasemanal:
#     print(sila.id)
#     print(sila.numsemana)
#     print(sila.silabo.materia)

#
# diasclas = Clase.objects.values_list('dia',flat=True).filter(activo=True, materia_id=49130, profesor_id=45,tipoprofesor_id=14)
# print(diasclas)
#
# # import datetime
# from datetime import datetime, timedelta, date
# # from datetime import date
#
# dt = datetime.strptime("2022-06-01", "%Y-%m-%d")
# end = datetime.strptime("2022-06-30", "%Y-%m-%d")
# print(dt.date())
#
#
# # dt = datetime.datetime(2022, 6, 1)
# # end = datetime.datetime(2022, 6, 30)
# step = timedelta(days=1)
#
# result = []
# while dt <= end:
#     # print(dt.isocalendar()[2])
#     if dt.isocalendar()[2] in diasclas:
#         result.append(dt.strftime('%Y-%m-%d'))
#     dt += step
# print(len(result))

# fechaini='2022-06-01'
# fechaini='2022-06-01'
# from datetime import datetime, timedelta, date
# fechaini=datetime.strptime("2022-06-01", "%Y-%m-%d").date()
# # print(fechaini)
# fechafin=datetime.strptime("2022-06-30", "%Y-%m-%d").date()
# listado = []
# listadosilabos = Silabo.objects.filter(materia_id__in=ProfesorMateria.objects.values_list('materia_id').filter(profesor_id=45, materia__nivel__periodo=126,
#                                                                                                              tipoprofesor_id__in=[1, 2, 5, 6, 10, 11, 12, 14, 15],
#                                                                                                              activo=True).exclude(materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct())
# totalsilabos = listadosilabos.count()
# totalsilabosplanificados = listadosilabos.filter(codigoqr=True).count()
# porcentaje = round(((100 * totalsilabosplanificados) / totalsilabos), 2)
# totaldiapositivaplanificada = 0
# totaldiapositivasmoodle = 0
# totalunidades = 0
# for lsilabo in listadosilabos:
#     listaunidadterminadas = []
#     silabosemanaluni = lsilabo.silabosemanal_set.values_list('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden','fechafinciosemana').filter(status=True).distinct('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').order_by('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden','-fechafinciosemana')
#
#     for sise in silabosemanaluni:
#         if sise[1] >= fechaini and sise[1] <= fechafin:
#             listaunidadterminadas.append(sise[0])
#         # sila = silabosemanaluni.filter(fechafinciosemana__range=(fechaini, fechafin),status=True)
#         # print(sila)
#     print(silabosemanaluni)
#     silabosemanal = lsilabo.silabosemanal_set.filter(fechafinciosemana__range=(fechaini, fechafin),detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden__in=listaunidadterminadas,status=True)
#     # totalunidades = silabosemanal.values_list('detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').distinct().count()
#     totaldiapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal_id__in=silabosemanal.values_list('id'), iddiapositivamoodle__gt=0, status=True).count()
#     totaldiapositivaplan = lsilabo.materia.nivel.periodo.lineamientorecursoperiodo_set.filter(tipoprofesor_id__in=lsilabo.materia.profesormateria_set.values_list('tipoprofesor').filter(status=True), tiporecurso=2, status=True)[0].cantidad * len(listaunidadterminadas)
#     totaldiapositivaplanificada += totaldiapositivaplan
#     if totaldiapositivas > totaldiapositivaplan:
#         totaldiapositivasmoodle += totaldiapositivaplan
#     else:
#         totaldiapositivasmoodle += totaldiapositivas
# porcentajediapositivas = round(((100 * totaldiapositivasmoodle) / totaldiapositivaplanificada), 2)
# listado.append([totalsilabos,totalsilabosplanificados,porcentaje])
# listado.append([totaldiapositivaplanificada,totaldiapositivasmoodle,porcentajediapositivas])
#
# print(listado)
# print(len(listado))
# profesor = Profesor.objects.get(pk=903)
# grupostitulacion = ComplexivoGrupoTematica.objects.filter(status=True, tematica__tutor__participante__persona=profesor.persona, complexivoacompanamiento__fecha__range=(fechaini, fechafin)).distinct().order_by('tematica__tematica__tema')
#
#
# print(grupostitulacion)
#
#
# d=0
# v=2
# cv=round((d/v), 2)
# print(cv)

# comple = ComplexivoAcompanamiento.objects.filter(grupo__tematica__tutor__participante__persona=38, grupo__status=True).aggregate(totalhoras=Sum('horas'))['horas']
# print(comple)
# from datetime import datetime
#
# date_str = '1-10-2020'
#
# dto = datetime.strptime(date_str, '%d-%m-%Y').date()
# # print(type(dto))
# print(dto)
#
# listado = DetalleDistributivo.objects.filter(criteriodocenciaperiodo_id__isnull=True,
#                                              criterioinvestigacionperiodo_id__isnull=True,
#                                              criteriogestionperiodo_id__isnull=True)
# for itemlis in listado:
#     itemlis.delete()

# import openpyxl
# workbook = openpyxl.load_workbook("presupuesto.xlsx")
# sheet = workbook._sheets[0]
# # lista = workbook.get_sheet_by_name('hoja1')
# linea = 0
# totallista = sheet.rows
# print(totallista)
# for filas in totallista:
#     linea += 1
#     print(str(sheet.cell(row=linea, column=1).value))


#     print(filas[1].value)

# d = 'ss dffgf'
#
# a = None
#
# periodo = Periodo.objects.get(pk=126)
# dias_nolaborables = periodo.dias_nolaborables('2022-08-12')
# if not dias_nolaborables:
#     print('no feriado')
# else:
#     print('feriado')

# evidencias = EvidenciaActividadDetalleDistributivo.objects.filter(status=True)[:10]
# suma = 0
# for evi in evidencias:
#     suma = suma + 1
# print(suma)

# para poner el parcial en silabosemanal
# listadosilabo = Silabo.objects.filter(materia__nivel__periodo_id=177,status=True)
# i=0
# for silabo in listadosilabo:
#     i=i+1
#     listaplanificacion = PlanificacionClaseSilabo_Materia.objects.filter(materia=silabo.materia, status=True)[0]
#     listaplanclase = PlanificacionClaseSilabo.objects.filter(tipoplanificacion=listaplanificacion.tipoplanificacion,status=True)
#     for lis in listaplanclase:
#         silasemanal = silabo.silabosemanal_set.filter(status=True)
#         for semanal in silasemanal:
#             if semanal.numsemana == lis.semana:
#                 semanal.parcial = lis.parcial
#                 semanal.save()
#                 # print(silasemanal.count())
#     print(str(i)+' de '+str(listadosilabo.count()))


# peri = Periodo.objects.filter(pk__lte=280)
# print(peri.query)
#
# listaprofesores = ProfesorMateria.objects.values_list('profesor__id', 'profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres', 'materia__asignaturamalla__malla__carrera__nombre', 'materia__asignaturamalla__malla__carrera__id', 'profesor__coordinacion__alias', 'profesor__categoria__nombre').filter(materia__nivel__periodo=126).distinct().annotate(prom=Sum('hora')).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', '-prom')
#
# print(listaprofesores[4])
# fechaini='2022-09-01'
# fechafin='2022-09-30'
# mate = Materia.objects.get(pk=49098)
# itemalumnos = mate.ids_matriculados_alumnos_matriculados()
# if mate.asignados_a_esta_materia_moodle():
#     totalasignados = mate.asignados_a_esta_materia_moodle().count()
# else:
#     totalasignados = 0
# print(itemalumnos)
# for tarea in mate.tareas_asignatura_moodlequery(fechaini, fechafin, itemalumnos):
#     print(tarea)

# insi = Inscripcion.objects.filter(persona__cedula='0915010425')
# print(insi.query)
# matri = Matricula.objects.get(pk=542645)
# print(matri.inscripcion.id)
# eInscripcion = Inscripcion.objects.get(pk=int(76372))
#
# eMalla = eInscripcion.mi_malla()
# if not eMalla:
#     print('a')
# eAsignaturas = eInscripcion.recordacademico_set.filter(asignatura_id__in=AsignaturaMalla.objects.values('asignatura_id').filter(malla_id=32), aprobada=True)
# if not eAsignaturas.values("id").exists():
#     print('b')
# total = Decimal(null_to_decimal(eAsignaturas.aggregate(total=Sum('creditos'))['total'])).quantize(Decimal('.01'))
# print('malla de alumno')
# print(eMalla)
# print('computacion')
# print('creditos en malla')
# print(Decimal(null_to_decimal(eMalla.creditos_computacion)).quantize(Decimal('.01')))
# print('creditos aprobados')
# print(total)
# print('vinculacion')
# print('creditos en malla')
# print(eMalla.horas_vinculacion)
# print('creditos aprobados')
# print(eInscripcion.numero_horas_proyectos_vinculacion())
#
# print('pre profesionales')
# print('creditos en malla')
# print(eMalla.horas_practicas)
# print('creditos aprobados')
# print(eInscripcion.numero_horas_practicas_pre_profesionales())
#
# print('ingles')
# ingles = ModuloMalla.objects.filter(malla=eMalla, status=True).exclude(asignatura_id=782)
# print('modulos de aprobar')
# print(len(ingles))
# records = eInscripcion.recordacademico_set.filter(asignatura_id__in=ingles.values('asignatura_id'), aprobada=True)
# print('numero aprobados')
# print(len(records))
# print('Asignaturas aprobadas del primer el penúltimo nivel')
# print('modulos de aprobar')
# print(eInscripcion.cantidad_asig_aprobar_penultimo_malla())
# print('numero aprobados')
# print(eInscripcion.cantidad_asig_aprobada_penultimo_malla())
#
#


# response = HttpResponse(content_type="application/ms-excel")
# response['Content-Disposition'] = 'attachment; filename=tiempo_calificacion.xls'
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
# # ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
# output_folder = os.path.join(os.path.join(SITE_STORAGE))
# nombre = "Listadoadmisionmaestria.xls"
# filename = os.path.join(output_folder, nombre)
# columns = [(u"N.", 2000),
#            (u"COHORTE", 10000),
#            (u"CEDULA", 4000),
#            (u"NOMBRES", 10000),
#            (u"EMAIL", 6000),
#            (u"TELEFONO", 4000),
#            (u"RUBRO GENERADO", 4000),
#            (u"RUBRO CANCELADO", 4000),
#            (u"VALOR", 4000),
#            (u"SALDO", 4000),
#            (u"RUBRO", 4000),
#            (u"FECHA ASIGNACION RUBRO", 4000),
#            (u"FECHA ABONO RUBRO", 4000),
#            (u"DIAS", 4000),
#            ]
# row_num = 0
# for col_num in range(len(columns)):
#     ws.write(row_num, col_num, columns[col_num][0], font_style)
#     ws.col(col_num).width = columns[col_num][1]
# date_format = xlwt.XFStyle()
# date_format.num_format_str = 'yyyy/mm/dd'
#
# listados2 = InscripcionCohorte.objects.filter(cohortes_id__in=CohorteMaestria.objects.values_list('id').filter(tipo=2, status=True), cohortes__tipo=2, estado_aprobador=2, integrantegrupoexamenmsc__estado=2, status=True)
# listados3 = InscripcionCohorte.objects.filter(cohortes_id__in=CohorteMaestria.objects.values_list('id').filter(tipo=3, status=True), estado_aprobador=2, status=True)
# linstadoinscripcion = InscripcionCohorte.objects.filter(cohortes_id__in=CohorteMaestria.objects.values_list('id').filter(status=True), tipocobro__in=[2, 3], status=True)
# listadoadmitidossinproceso = listados2 | listados3 | linstadoinscripcion
#
# row_num = 0
# idrubro = 0
# for lista in listadoadmitidossinproceso:
#     try:
#         fechaabonorubro = None
#         fechacreacionrubro = None
#         row_num += 1
#         if lista.inscripcionaspirante.persona.cedula:
#             campo2 = lista.inscripcionaspirante.persona.cedula
#         if lista.inscripcionaspirante.persona.pasaporte:
#             campo2 = lista.inscripcionaspirante.persona.pasaporte
#         campo5 = lista.inscripcionaspirante.persona.apellido1 + ' ' + lista.inscripcionaspirante.persona.apellido2 + ' ' + lista.inscripcionaspirante.persona.nombres
#         campo9 = lista.inscripcionaspirante.persona.email
#         campo10 = lista.inscripcionaspirante.persona.telefono
#         campo11 = 'NO'
#         campo12 = 'NO'
#         valorrubro = 0
#         valorsaldo = 0
#         if lista.tipocobro == 2:
#             if lista.genero_rubro_matricula():
#                 campo11 = 'SI'
#             if lista.cancelo_rubro_matricula():
#                 campo12 = 'SI'
#
#             if Rubro.objects.filter(status=True, admisionposgradotipo=2, inscripcion=lista):
#                 fechacreacionrubro = Rubro.objects.filter(status=True, admisionposgradotipo=2, inscripcion=lista)[0]
#                 idrubro = fechacreacionrubro.id
#                 if fechacreacionrubro.pago_set.filter(status=True):
#                     rpago = fechacreacionrubro.pago_set.filter(status=True)[0]
#                     fechaabonorubro = rpago.fecha
#                 valorrubro = Rubro.objects.filter(status=True, admisionposgradotipo=2, inscripcion=lista).aggregate(valor=Sum('valor'))['valor']
#                 valorsaldo = Rubro.objects.filter(status=True, admisionposgradotipo=2, inscripcion=lista).aggregate(valor=Sum('saldo'))['valor']
#
#         if lista.tipocobro == 3:
#             if lista.genero_rubro_programa():
#                 campo11 = 'SI'
#             if lista.cancelo_rubro_programa():
#                 campo12 = 'SI'
#
#             if Rubro.objects.filter(status=True, admisionposgradotipo=3, inscripcion=lista):
#                 fechacreacionrubro = Rubro.objects.filter(status=True, admisionposgradotipo=3, inscripcion=lista)[0]
#                 idrubro = fechacreacionrubro.id
#                 if fechacreacionrubro.pago_set.filter(status=True):
#                     rpago = fechacreacionrubro.pago_set.filter(status=True)[0]
#                     fechaabonorubro = rpago.fecha
#                 valorrubro = Rubro.objects.filter(status=True, admisionposgradotipo=3, inscripcion=lista).aggregate(valor=Sum('valor'))['valor']
#                 valorsaldo = Rubro.objects.filter(status=True, admisionposgradotipo=3, inscripcion=lista).aggregate(valor=Sum('saldo'))['valor']
#
#         ws.write(row_num, 0, row_num, font_style2)
#         ws.write(row_num, 1, lista.cohortes.descripcion + ' ' + lista.cohortes.maestriaadmision.carrera.nombre, font_style2)
#         ws.write(row_num, 2, campo2, font_style2)
#         ws.write(row_num, 3, campo5, font_style2)
#         ws.write(row_num, 4, campo9, font_style2)
#         ws.write(row_num, 5, campo10, font_style2)
#         ws.write(row_num, 6, campo11, font_style2)
#         ws.write(row_num, 7, campo12, font_style2)
#         ws.write(row_num, 8, valorrubro, font_style2)
#         ws.write(row_num, 9, valorsaldo, font_style2)
#         ws.write(row_num, 10, idrubro, font_style2)
#         if fechacreacionrubro:
#             ws.write(row_num, 11, fechacreacionrubro.fecha_creacion, date_format)
#         else:
#             ws.write(row_num, 11, '', font_style2)
#         if fechaabonorubro:
#             ws.write(row_num, 12, fechaabonorubro, date_format)
#         else:
#             ws.write(row_num, 12, '', font_style2)
#         if fechacreacionrubro and fechaabonorubro:
#             fechacreacionrubro = datetime.datetime.strptime(str(fechacreacionrubro.fecha_creacion.date()), "%Y-%m-%d")
#             fechaabonorubro = datetime.datetime.strptime(str(fechaabonorubro), "%Y-%m-%d")
#             diasresta = fechaabonorubro - fechacreacionrubro
#             ws.write(row_num, 13, diasresta.days, font_style2)
#         print('%s de %s' % (row_num,listadoadmitidossinproceso.count()))
#     except Exception as ex:
#         print('error: %s' % (ex))
#         pass
# wb.save(filename)
# print("FIN: ", filename)
#
# import openpyxl
# workbook = openpyxl.load_workbook("todasmarcadasotro.xlsx")
# lista = workbook.get_sheet_by_name('Hoja1')
# linea = 0
# totallista = lista.rows
# for filas in totallista[:]:
#     linea += 1
#     if linea > 1:
#
#         idreloj = filas[2].value.split('_')
#         print(idreloj[1])
#         if Persona.objects.filter(identificacioninstitucion=str(idreloj[1])):
#             perso = Persona.objects.get(identificacioninstitucion=str(idreloj[1]))
#             print(perso)
#             filas[1].value = perso.apellido1 + perso.apellido2 + perso.nombres
#             filas[5].value = perso.cedula
#     linea += 1
# workbook.save("todasmarcadasotro.xlsx")
#
#
#
#
# fechaini='2022-10-01'
# fechafin='2022-06-30'
# from datetime import datetime, timedelta, date
# fechaini=datetime.strptime("2022-10-01", "%Y-%m-%d").date()
# fechafin=datetime.strptime("2022-10-30", "%Y-%m-%d").date()
#
# # fechafin=datetime.strptime("2022-06-30", "%Y-%m-%d").date()
# listado = CapCabeceraSolicitudDocente.objects.filter(capeventoperiodo__fechainicio__lte=fechaini,capeventoperiodo__fechafin__gte=fechafin)
# listado = CapCabeceraSolicitudDocente.objects.filter(capeventoperiodo__fechainicio__gte=fechaini,capeventoperiodo__fechafin__lte=fechafin)
# listado = CapCabeceraSolicitudDocente.objects.filter(capeventoperiodo__fechainicio__gte=fechaini,capeventoperiodo__fechafin__lte=fechafin)
# print(listado.query)


#listadoasignados = MateriaAsignada.objects.filter(pk__in=[2468257,2446283,2434438,2439710,2442081,2442806,2457054,2457688,2458146,2458346,2448963,2454179,2455222,2645950,2562520,2464687,2456413,2464953,2465018,2465025,2465365,2457906,2465396,2465436,2458272,2458280,2465591,2459011,2459154,2459172,2459589,2459809,2449557,2460045,2460104,2460170,2460191,2460350,2461114,2461199,2461482,2461707,2462117,2452821,2462423,2462869,2463569,2476334,2463624,2463661,2454931,2463872,2464031,2464079,2464320,2476813,2464511,2456377,2456698,2456825,2458401,2448234,2449624,2450946,2452112,2453217,2475934,2455737,2476874,2456985,2457418,2475139,2465808,2448294,2459109,2459291,2459340,2459424,2459692,2459785,2466333,2460095,2460636,2466849,2460809,2460905,2461198,2461375,2461614,2475794,2463092,2454438,2463389,2454777,2474441,2455588,2482425,2525304,2556714,2395974,2374109,2376628,2496045,2534143,2607586,2375695,2519253,2575303,2397503,2494769,2582017,2399784,2607049,2607064,2515234,2576918,2610139,2473189,2605948,2445079,2445692,2496461,2397162,2397552,2397926,2398253,2398352,2446193,2405113,2391614,2466938,2428308,2429245,2396299,2397044,2541249,2542098,2567710,2584338,2585882,2604483,2441314,2397281,2398242,2431399,2432019,2395714,2513532,2543349,2566611,2605436])
#cuenta = 0
#for lasig in listadoasignados:
#    cuenta = cuenta + 1
#    lasig.delete()
#    print(str(cuenta) + ' de ' + str(listadoasignados.count()))


# delmateriatitulacion = MateriaTitulacion.objects.filter(materiaasignada__materia_id=59876,materiaasignada__estado_id=3)
# for delma in delmateriatitulacion:
#     delma.delete()
#
# mateasig = MateriaAsignada.objects.filter(materia_id=59876,estado_id=3)
# cuenta = 0
# for masig in mateasig:
#     cuenta =cuenta + 1
#     print(str(cuenta) +  ' de ' + str(mateasig.count()) )
#     masig.delete()
#
# print(mateasig.count())
#
# tablaponderativa = TablaPonderacionInstrumento.objects.get(pk=23)
# configuraciones = tablaponderativa.tablaponderacionconfiguracion_set.filter(periodo_id=153, status=True).order_by('criteriodocenciaperiodo__criterio__tipo', 'criteriodocenciaperiodo_id', 'criterioinvestigacionperiodo', 'criteriogestionperiodo_id')
# listadodocencia = configuraciones.values_list('criteriodocenciaperiodo_id', flat=True).filter(criteriodocenciaperiodo_id__isnull=False).order_by('criteriodocenciaperiodo_id')
#
# print(str(list(listadodocencia)))
# print(tuple(list(listadodocencia)))
# print(str(tuple(list(listadodocencia))))
# lista = []
#
# lista1='19986,19652'
# for l in lista1.split(','):
#     lista.append(l)
# print(lista)
# lst_new = [str(a) for a in lista1]
# lista = "'" . join(lst_new)
# print(lista)

# listamatri = ProfesorDistributivoHoras.objects.filter(detalledistributivo__criteriodocenciaperiodo__isnull=False,detalledistributivo__rubricacriteriodocencia__isnull=False, periodo_id=153).annotate(nummatri=Count('matricula',distinct=True, status=True, matricula__estado_matricula__in=[2, 3], matricula__status=True, matricula__retiradomatricula=False))
# listamatri = ProfesorDistributivoHoras.objects.annotate(book_ids=GroupConcat("detalledistributivo__criteriodocenciaperiodo__id")).filter(detalledistributivo__criteriodocenciaperiodo_id__isnull=False,periodo_id=153)
# print(listamatri.query)

# lpersona = Persona.objects.annotate(book_id=GroupConcat("profesor__id")).filter(status=True)

# listadistributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=153).order_by('profesor__persona_apellido1', 'profesor__persona_apellido2', 'profesor__persona_nombres')
# for lista in listadistributivo:
#     if not RubricaCriterioDocencia.objects.filter(rubrica__para_auto=False,rubrica__para_par=False,rubrica__para_directivo=False, rubrica__proceso__periodo_id=153, criterio_id__in=lista.detalledistributivo_set.values_list('criteriodocenciaperiodo_id').filter(criteriodocenciaperiodo_id__isnull=False, status=True)).exclude(rubrica__para_auto=True).exclude(rubrica__para_par=True).exclude(rubrica__para_directivo=True):
#         listas = RubricaCriterioDocencia.objects.filter(rubrica__para_auto=False,rubrica__para_par=False,rubrica__para_directivo=False,rubrica__proceso__periodo_id=153, criterio_id__in=lista.detalledistributivo_set.values_list('criteriodocenciaperiodo_id').filter(criteriodocenciaperiodo_id__isnull=False, status=True)).exclude(rubrica__para_auto=True).exclude(rubrica__para_par=True).exclude(rubrica__para_directivo=True)
#         for li in listas:
#             print(li.rubrica)

# niveles = Nivel.objects.filter(periodo_id=153).annotate(sumatoria = Sum('modalidad_id') + Sum('id'))
#
# print(niveles.query)
from django.db.models import F, Value, Func, CharField, ExpressionWrapper, TimeField
# from django.db.models.functions import Concat
# listadomodalidadesperiodo = ProfesorMateria.objects. \
#                         values_list('materia__nivel__modalidad_id',
#                                     'materia__nivel__modalidad__nombre',
#                                     'tipoprofesor_id',
#                                     'tipoprofesor__nombre'). \
#                         annotate(sumatoria = Concat('materia__nivel__modalidad_id','tipoprofesor_id')).\
#     filter(materia__nivel__periodo_id=153, materia__nivel__status=True, materia__status=True, status=True).\
#     order_by('materia__nivel__modalidad_id','tipoprofesor_id').distinct()
#
# print(listadomodalidadesperiodo.query)
#
# rubrica = Rubrica.objects.get(pk=1066)
# rubricalistadomodalidades = rubrica.rubricamodalidadtipoprofesor_set.\
#     annotate(sumatoria = Concat('modalidad_id','tipoprofesor_id')).\
#     filter(status=True)
#
# print(rubricalistadomodalidades.query)
#
#

# listado = RubricaModalidadTipoProfesor.objects.values_list('modalidad_id', 'tipoprofesor_id').filter(rubrica__proceso__periodo_id=153, rubrica__para_hetero=True, status=True).distinct()
#
# print(listado.query)
#
# from django.core.paginator import Paginator
#
#

# Author.objects.annotate(book_ids=GroupConcat("books__id", ordering="asc"))
#
# listado = RubricaModalidadTipoProfesor.objects.annotate(modalidad_ids=GroupConcat("modalidad__id"))

# print(listado.query)
#
# depa=Departamento.objects.filter(integrantes__isnull=False, status=True).order_by('nombre').distinct()
#
# print(depa.query)

# peri = Periodo.objects.get(pk=153)
# print(peri.periodoacademia_set.filter(status=True)[0].versioninstrumento)
#
# listado = ResumenFinalEvaluacionAcreditacion.objects.filter(distributivo__periodo_id=153,
#                                                             distributivo__profesor__persona__cedula='0913439543')
# total = listado.count()
# cuenta = 0
# for lis in listado:
#     cuenta = cuenta + 1
#     lis.actualizar_resumen()
#     print(str(cuenta) + ' de ' + str(total))

# Para calcular las horas de docencia,investigacion,gestion y vinculacion
# listado = ProfesorDistributivoHoras.objects.filter(periodo_id=153)
# total = listado.count()
# cuenta = 0
# for lis in listado:
#     cuenta = cuenta + 1
#     lis.calcular_ponderaciones()
#     print(str(cuenta) + ' de ' + str(total))
#


#
# listadoact = ActividadDetalleDistributivo.objects.filter(criterio__distributivo__periodo_id=177,
#                                                          criterio__criteriodocenciaperiodo__criterio_id=118 ,
#                                                          status=True)
# totalborrar = listadoact.count()
# contador = 0
# for lista in listadoact:
#     contador = contador + 1
#     print('eliminando ' + str(contador) + ' de ' + str(totalborrar))
#     # print(lista.id)
#     # print(lista.criterio.distributivo.profesor)
#     # print(lista.criterio.total_claseactividades())
#     # print(lista.nombre)
#     lista.delete()
#
# listadodistributivo = DetalleDistributivo.objects.filter(distributivo__periodo_id=177,
#                                                          criteriodocenciaperiodo__criterio_id=118 ,
#                                                          status=True)
#
# totaldistri = listadodistributivo.count()
# cuenta = 0
# for ldis in listadodistributivo:
#     cuenta = cuenta + 1
#     ldis.verifica_actividades()
#     print('actualiza ' + str(cuenta) + ' de ' + str(totaldistri))
#

# listado = DistributivoPersona.objects.filter(denominacionpuesto_id=70, estadopuesto_id=1, status=True).order_by('-id')[0]
#
# print(listado.persona)


# listado = DetalleDistributivo.objects.values_list('criteriodocenciaperiodo_id', flat=True).filter(criteriodocenciaperiodo_id__in=[686]).order_by('criteriodocenciaperiodo_id').distinct()
#
# print(listado)
# mi_lista = [2, 'manzana', 3.5]
# print(mi_lista)

# listado = RespuestaEvaluacionAcreditacion.objects.values("profesor_id","evaluador_id").filter(proceso_id=133, tipoinstrumento=4).distinct().count()
# print(listado)
# Nivel.objects.filter(nivellibrecoordinacion__coordinacion=coordinacion, periodo=periodo).annotate(nummatri=Count('materia__materiaasignada',distinct=True), matricula__estado_matricula__in=[2, 3], matricula__status=True, matricula__retiradomatricula=False)
# listadomalla = AsignaturaMalla.objects.values_list('materia__nivel__periodo__nombre','malla__carrera__coordinacion__nombre','malla__carrera__nombre','nivelmalla__nombre','asignatura__nombre').filter(materia__nivel__periodo_id=177,programaanaliticoasignatura__activo=True,status=True).distinct().annotate(sumatoria = Count('programaanaliticoasignatura__bibliografiaprogramaanaliticoasignatura__id',distinct=True))
# listadomalla = Materia.objects.values_list('nivel__periodo__nombre','asignaturamalla__malla__carrera__coordinacion__nombre','asignaturamalla__malla__carrera__nombre','asignaturamalla__nivelmalla__nombre','asignaturamalla__asignatura__nombre').filter(nivel__periodo_id=177,asignaturamalla__programaanaliticoasignatura__activo=True,status=True).distinct().annotate(sumatoria = Count('asignaturamalla__programaanaliticoasignatura__bibliografiaprogramaanaliticoasignatura__id',distinct=True))
# print(listadomalla.query)

# listadomalla = Materia.objects.values_list('nivel__periodo__nombre','asignaturamalla__malla__carrera__coordinacion__nombre','id',
#                                            'asignaturamalla__malla__carrera__nombre','asignaturamalla__nivelmalla__nombre',
#                                            'asignaturamalla__asignatura__nombre','profesormateria__profesor__persona__apellido1',
#                                            'profesormateria__profesor__persona__apellido2','profesormateria__profesor__persona__nombres',
#                                            'profesormateria__tipoprofesor__nombre').filter(nivel__periodo_id=177,
#                                                                                            asignaturamalla__asignatura_id=4881,
#                                                                                            status=True).distinct().exclude(pk__in=[66383,66386,66389])
# print(listadomalla.query)
#
#
# listadomalla = Materia.objects.values_list('nivel__periodo__nombre',
#                                            'asignaturamalla__malla__carrera__coordinacion__nombre',
#                                            'asignaturamalla__malla__carrera__nombre',
#                                            'asignaturamalla__nivelmalla__nombre',
#                                            'asignaturamalla__programaanaliticoasignatura__id',
#                                            'asignaturamalla__programaanaliticoasignatura__activo',
#                                            'asignaturamalla__asignatura__nombre'). \
#     filter(nivel__periodo_id=177,
#            asignaturamalla__programaanaliticoasignatura__activo=True,
#            asignaturamalla__asignatura_id=4881,
#            status=True).exclude(pk__in=[66383,66386,66389]).distinct()
# print(listadomalla.query)
# periodo = Periodo.objects.get(pk=153)
#
# periodo = Periodo.objects.get(pk=1)  # Suponiendo que obtienes el periodo deseado
#
# # Obtener las fechas mensuales dentro del rango
# fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.fecha_inicio, until=periodo.fecha_fin))
#
# # Recorrer las fechas y obtener los nombres de los meses y los años
# for fecha in fechas_mensuales:
#     nombre_mes = fecha.strftime("%B")
#     anio = fecha.year
#     print(nombre_mes, anio)

# yaevaluaron = RespuestaEvaluacionAcreditacion.objects.values_list('profesor_id').filter(proceso__periodo=periodo, tipoinstrumento=2)
#
#
# profe = ProfesorMateria.objects.values_list('profesor_id').filter(materia__nivel__periodo=periodo,materia__nivel__modalidad_id__in=[1,2], profesor__persona__real=True).distinct().exclude(profesor_id__in=yaevaluaron).exclude(materia__asignaturamalla__malla__carrera__coordinacion=9)
#
# print(profe.query)
#
#
# profe = ProfesorMateria.objects.values_list('profesor_id').filter(materia__nivel__periodo=periodo,materia__nivel__modalidad_id=3, profesor__persona__real=True).distinct().exclude(profesor_id__in=yaevaluaron).exclude(materia__asignaturamalla__malla__carrera__coordinacion=9)
#
# print(profe.query)
#
# listadoprofesormateria = ProfesorMateria.objects.values_list('profesor_id').filter(materia__nivel__periodo=periodo, profesor__persona__real=True).distinct().exclude(materia__asignaturamalla__malla__carrera__coordinacion=9)
# profe = ProfesorDistributivoHoras.objects.values_list('profesor_id').filter(periodo=periodo, profesor__persona__real=True, status=True).exclude(profesor_id__in=listadoprofesormateria).exclude(profesor_id__in=yaevaluaron)
# print(profe.query)
#
# for lista in profe:
#     print(lista)
#
#
#
#
#
# profe = Profesor.objects.filter(profesormateria__materia__nivel__periodo=periodo,
#                                                   profesormateria__materia__nivel__modalidad_id=3).distinct().\
#     exclude(pk__in=yaevaluaron)
#     # exclude(pk__in=yaevaluaron).exclude(profesormateria__materia__asignaturamalla__malla__carrera__coordinacion=9)
#
# # for lista in profe:
# #     print(lista)
#
# # listaprofe = ProfesorMateria.objects.values_list('profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres','materia__asignaturamalla__malla__carrera__coordinacion').filter(materia__nivel__periodo=periodo,materia__nivel__modalidad_id=3).exclude(profesor_id__in=yaevaluaron).exclude(materia__asignaturamalla__malla__carrera__coordinacion=9)
# listaprofe = ProfesorMateria.objects.values_list('profesor_id').filter(materia__nivel__periodo=periodo,materia__nivel__modalidad_id=3).distinct().exclude(profesor_id__in=yaevaluaron).exclude(materia__asignaturamalla__malla__carrera__coordinacion=9)
# # for lista in listaprofe:
# #     print(lista)
#     # print(lista.materia.asignaturamalla.malla.carrera.coordinacion_set.all()[0].id)
#     # print(lista.materia.asignaturamalla.malla.carrera.coordinacion_set.all()[0])
# print(lista.profesor)
#
# import locale
# from dateutil.rrule import rrule, MONTHLY
# locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
# periodo = Periodo.objects.get(pk=177)
#
# # periodo = Periodo.objects.get(pk=1)  # Suponiendo que obtienes el periodo deseado
#
# # Obtener las fechas mensuales dentro del rango
# fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.inicio, until=periodo.fin))
#
# # Recorrer las fechas y obtener los nombres de los meses y los años
# for fecha in fechas_mensuales:
#     nombre_mes = fecha.strftime("%B")
#     numeromes = fecha.month
#     anio = fecha.year
#     ultimo_dia = fecha.replace(day=calendar.monthrange(fecha.year, fecha.month)[1])
#     print(nombre_mes, anio, '01',str(numeromes), str(ultimo_dia.day))

# from datetime import datetime, timedelta

# Definir las dos horas
# hora_inicio = datetime.strptime("08:30", "%H:%M")
# hora_fin = datetime.strptime("10:15", "%H:%M")
#
# # Calcular la diferencia de tiempo
# diferencia_tiempo = hora_fin - hora_inicio
#
# # Obtener la cantidad de horas
# cantidad_horas = diferencia_tiempo.total_seconds() / 3600
#
# # Imprimir el resultado
# # print(cantidad_horas)
#
# mesbitacora=BitacoraActividadDocente.objects.get(pk=9)
#
# listadodetalle = mesbitacora.detallebitacoradocente_set.filter(status=True).annotate(
#                     diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())
#                 )
#
# total_diferencia = listadodetalle.filter(status=True).aggregate(
#     total=Sum('diferencia')
# )['total']
# print(total_diferencia)
# for lisdetalle in listadodetalle:
#     print(lisdetalle.diferencia)


# BitacoraActividadDocente.objects.filter(status=True).delete()
# from datetime import timedelta
# from django.db.models import F, ExpressionWrapper, DateTimeField
# detalledistributivo = DetalleDistributivo.objects.get(pk=168296, status=True)
# # registrobitacoras = detalledistributivo.bitacoraactividaddocente_set.filter(status=True).order_by('fechaini').annotate(fechamaxima=F('fechafin') + timedelta(days=7))
# # registrobitacoras = detalledistributivo.bitacoraactividaddocente_set.filter(status=True).annotate(fechamaxima=F('fechafin') + timedelta(days=7))
# registrobitacoras = detalledistributivo.bitacoraactividaddocente_set.filter(status=True).order_by('fechaini').annotate(
#     fechamaxima=ExpressionWrapper(F('fechafin') + timedelta(days=7), output_field=DateTimeField())
# ).order_by('fechaini')
# for reg in registrobitacoras:
#     print(reg.fechamaxima)
# fecha_objeto = datetime.strptime('2023-06-30', '%Y-%m-%d')
# fecha_texto = str(fecha_objeto.strftime('%d-%m-%Y'))
# print(fecha_texto)
# from sga.templatetags.sga_extras import encrypt, diaenletra, nombremes
# from dateutil.rrule import MONTHLY, rrule
# # registros = MiModelo.objects.annotate(month=TruncMonth('fecha')).order_by('month', 'fecha')
#
# # listadoevidencias = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor_id=1671, criterio__criteriogestionperiodo_id=1194 , status=True)
# #
# # mesesevidencia = list(listadoevidencias.values_list('desde__month', flat=True))
# periodol = Periodo.objects.get(pk=177)
#
# listamesesperiodo = []
# fechas_mensuales = list(rrule(MONTHLY, dtstart=periodol.inicio, until=periodol.fin))
# print(fechas_mensuales)
# for fecha in fechas_mensuales:
#     # if fecha <= fecha_objeto:
#     listamesesperiodo.append(fecha.month)
#     print(nombremes(fecha.month).upper())
#
# listadoinforme = InformeMensualDocente.objects.filter(fechafin__month__in=['5','6'], status=True)
# print(listadoinforme)
#
# listadoinformes = HistorialInforme.objects.values_list('informe__fechafin__month', flat=True).filter(
#     informe__distributivo__periodo=periodol,
#     firmado=True,
#     estado=4,
#     status=True
# )
# for lista in listadoinformes:
#     print(lista)
#
# print(str(nombremes(5)))
#
# from datetime import datetime, timedelta
# import calendar
#
# start_date = datetime.strptime('24-04-2023', '%d-%m-%Y')
# end_date = datetime.strptime('24-08-2023', '%d-%m-%Y')
#
# current_date = start_date
# months_less_than_10_days = []
#
# while current_date <= end_date:
#     _, days_in_month = calendar.monthrange(current_date.year, current_date.month)
#     days_in_month -= current_date.day - 1 if current_date == start_date else 0
#     days_in_month -= end_date.day if current_date == end_date else 0
#     # if days_in_month < 10:
#     months_less_than_10_days.append((current_date.month, days_in_month))
#     current_date = current_date.replace(day=1) + timedelta(days=32)
#
# print(months_less_than_10_days)


# from datetime import datetime, timedelta
# start_date = datetime.strptime('10-04-2023', '%d-%m-%Y')
# end_date = datetime.strptime('24-08-2023', '%d-%m-%Y')
# current_date = start_date
# months_less_than_10_days = []
#
# while current_date <= end_date:
#     next_month = current_date.replace(day=28) + timedelta(days=4)
#     days_in_month = (next_month - timedelta(days=next_month.day)).day
#
#     if current_date == start_date:
#         days_in_month -= start_date.day - 1
#
#     if current_date.month == end_date.month:
#         days_in_month = end_date.day
#         print('ee')
#
#     if days_in_month < 10:
#         months_less_than_10_days.append(current_date.month)
#
#     current_date = next_month.replace(day=1)
#
# print(months_less_than_10_days)
#
# from datetime import datetime
# listaevi = EvidenciaActividadDetalleDistributivo.objects.filter(pk=93322)
#
# fecha_str = '2023-30-06'
# fecha_obj = datetime.strptime(fecha_str, '%Y-%d-%m')
# fecha_obj = fecha_obj.replace(hour=23, minute=0)
# for evi in listaevi:
#  print(evi.porcentaje_informemensual(fecha_obj))
#
#  listaevi = EvidenciaActividadDetalleDistributivo.objects.get(pk=93322)
#  historial = listaevi.historialaprobacionevidenciaactividad_set.filter(fecha_creacion__lte=fecha_obj, status=True).annotate(month=TruncMonth('fecha_creacion')).order_by('month', '-fecha_creacion')
#
#  print(historial.query)
#  registro = historial.distinct('month')
#  totalrechazados = 0
#  for reg in registro:
#      if int(reg.estadoaprobacion) == 3:
#          totalrechazados = totalrechazados + 1
#
#  porcentaje = 100
#  for descontar in range(totalrechazados):
#      porcentaje = porcentaje / 2
# listado1 = Materia.objects.filter(asignaturamalla__validarequisitograduacion=True, nivel__periodo_id=177, asignaturamalla__status=True, status=True).annotate(sumatoria = Count('grupotitulacion__materiagrupotitulacion__id')).order_by('asignaturamalla__malla__carrera__nombre', 'paralelo')
# listado2 = Materia.objects.filter(asignaturamalla__malla_id=383, nivel__periodo_id=177, asignaturamalla__status=True, status=True).annotate(sumatoria = Count('grupotitulacion__materiagrupotitulacion__id')).order_by('asignaturamalla__malla__carrera__nombre', 'paralelo')
# listado = listado1 | listado2
#
# for lista in listado:
#     print(lista.sumatoria)

# informe = InformeMensualDocente.objects.filter(distributivo__periodo_id=177, fechafin__month=6)
# print(informe)
#
# listado = CoordinadorCarrera.objects.filter(periodo_id=177, status=True, tipo=3).order_by('persona__apellido1', 'persona__apellido1', 'persona__nombres').distinct('persona__apellido1', 'persona__apellido1', 'persona__nombres')
# print(listado.count())

# listado = GrupoTitulacionIC.objects.filter(status=True)
# listado.delete()
# print(listado.query)
#
# listado = Malla.objects.filter(pk__in=[205,207,201,208,200,198,204,202,206,199])
# for mate in listado:
#     print(mate.carrera.nombre + ' https://sga.unemi.edu.ec/adm_complexivotematica?action=reportasignatura&conrequisitos=1&idmalla=' + encrypt(mate.id))

#
# fechaini='2022-06-01'
# fechaini='2022-06-01'
# from datetime import datetime, timedelta, date
# fechaini=datetime.strptime("2023-07-01", "%Y-%m-%d").date()
# # print(fechaini)
# fechafin=datetime.strptime("2023-07-30", "%Y-%m-%d").date()
# listamateria = ProfesorMateria.objects.filter(pk=117725)
# for lmate in listamateria:
#     print(lmate.horas_del_profesortotal(fechaini,fechafin))
#     print(lmate.tipoprofesor_id)
#
#
# malla = Malla.objects.get(pk=214)
# listadomalla = malla.requisitotitulacionmalla_set.filter(status=True)
#
# for idmalla in listadomalla:
#     print(idmalla.requisito.id)
#     print(idmalla.requisito.nombre)
# directorcarrera = CoordinadorCarrera.objects.filter(carrera_id=131,tipo=3,periodo_id=177,status=True)
# if directorcarrera:
#     print(directorcarrera[0].persona)
#
#
# gradu = Graduado.objects.get(pk=20212)
# gradu.delete()


# peri = Periodo.objects.get(pk=177)
#
# recoreperiodo1 = Periodo.objects.filter(tipo_id__in=[2], inicio__year=2018, status=True)
# recoreperiodo2 = Periodo.objects.filter(tipo_id__in=[2], inicio__year=2019, status=True)
# recoreperiodo3 = Periodo.objects.filter(tipo_id__in=[2], inicio__year=2020, status=True)
# recoreperiodo4 = Periodo.objects.filter(tipo_id__in=[2], inicio__year=2021, status=True)
# recoreperiodo5 = Periodo.objects.filter(tipo_id__in=[2], inicio__year=2022, status=True)
# recoreperiodo6 = Periodo.objects.filter(tipo_id__in=[2], inicio__year=2023, status=True)
#
# recoreperiodo = recoreperiodo1 | recoreperiodo2 |  recoreperiodo3 | recoreperiodo4 | recoreperiodo5 | recoreperiodo6
#
#
#
# # print(recoreperiodo.query)
#
#
# for idperiodo in  recoreperiodo:
#     listadocarreramate = Materia.objects.values_list('asignaturamalla__malla__carrera').filter(nivel__periodo=idperiodo,asignaturamalla__malla__carrera__coordinacion=4)
#     listadocarrera = Carrera.objects.filter(pk__in=listadocarreramate)
#     for lcar in  listadocarrera:
#         listado = Matricula.objects.values("id").filter(nivel__periodo=idperiodo, inscripcion__carrera=lcar,estado_matricula__in=[2, 3], status=True).exclude(inscripcion__carrera__coordinacion__id=9).exclude(retiradomatricula=True).count()
#         listadodocentes = ProfesorMateria.objects.values("profesor_id").filter(materia__nivel__periodo=idperiodo, materia__asignaturamalla__malla__carrera=lcar).exclude(materia__asignaturamalla__malla__carrera__coordinacion__id=9).distinct().count()
#
#
#         solomodulos = Matricula.objects.values("id").filter(nivel__periodo=idperiodo,inscripcion__carrera=lcar,
#                                                                     materiaasignada__materia__asignatura__modulo=True,
#                                                                     estado_matricula__in=[2, 3], status=True) \
#                     .extra(
#                     where=["(select count(mta.id) from sga_materiaasignada mta where mta.matricula_id=sga_matricula.id) = %s"],
#                     params=[1]) \
#                     .exclude(inscripcion__carrera__coordinacion__id=9) \
#                     .exclude(inscripcion__carrera__id=7) \
#                     .exclude(retiradomatricula=True).distinct().count()
#
#
#
#         print(idperiodo.nombre + ' - carrera: ' + str(lcar.nombre) + ' - total alumnos ' + str((listado - solomodulos)) + ' - total docentes ' + str((listadodocentes)))
# #
# # for list in listado:
# #     print(list.materia)


#
# semanal = SilaboSemanal.objects.filter(silabo_id=35931)
# semanal.delete()

#
# listadistri = Profesor.objects.filter(persona__cedula__in=['0916691199',
#                                                            '1206280289','0921323291',
#                                                            '0927158188','1205897950',
#                                                            '0921071270',
#                                                            '0921188074',
#                                                            '0925004970','0921368890',
#                                                            '0924186265','0925008344',
#                                                            '0941150476','0927311969',
#                                                            '0924775786','0917717688',
#                                                            '0940384159','0941511222',
#                                                            '0917038218','0928541556',
#                                                            '1205907601','0922870936',
#                                                            '0918305483','1204613333',
#                                                            '0916785538','0920027471',
#                                                            '0923489819','0922665724',
#                                                            '0603767534','0917712127',
#                                                            '0921366852','0920344793',
#                                                            '1204833923','0929747301',
#                                                            '0918306788','0917035800',
#                                                            '0929212884','0920895620',
#                                                            '0927576504','0924888530',
#                                                            '0916365786','0921764296',
#                                                            '0941603540','0925568941',
#                                                            '0922876529','0909388001',
#                                                            '0926619453','0923489710',
#                                                            '1756528384','0922330501',
#                                                            '1204374753','0917712911',
#                                                            '0940323496',
#                                                            '0923363030',
#                                                            '0929749497','0918865114',
#                                                            '0926407669','0928422831',
#                                                            '0923601827','0921283834',
#                                                            '0919412510','0919871020',
#                                                            '0929857597','0915536791',
#                                                            '0916188782','0926402769',
#                                                            '1310297393','0918808940',
#                                                            '0920180783','0912500212',
#                                                            '0925566184','0705377299',
#                                                            '0921148748','0921071437',
#                                                            '1203704190','0916368418',
#                                                            '0942129735','0917626350',
#                                                            '0922663943','0929803005',
#                                                            '1713028916','0922666383',
#                                                            '0916754591','0913716809',
#                                                            '0920011665','0909442543',
#                                                            '0912690013','1202788764',
#                                                            '0913754412','0920736642',
#                                                            '0925716979','0942121708',
#                                                            '0921148300','0925851115',
#                                                            '0920847670','0919106385',
#                                                            '1203113855','0922629431',
#                                                            '0918566647','1204180648',
#                                                            '0930434659','0919085993',
#                                                            '0929762433','0916300171',
#                                                            '0603972456','0915787303',
#                                                            '0917621864','0931266159',
#                                                            '0911573467','0941344731',
#                                                            '0928472836','0919414524',
#                                                            '0924773799','0914186390',
#                                                            '0804024693','0919871038',
#                                                            '0302435102','0926613076',
#                                                            '0940367386','0920544830',
#                                                            '0920022456','0921610408',
#                                                            '0918566167','0927311324',
#                                                            '0913824983','0927313056',
#                                                            '0927423574','0922569306',
#                                                            '0920198439','0929608818',
#                                                            '0928323765',
#                                                            '0927738146',
#                                                            '1204164014','0918087438',
#                                                            '0925714628','0916304041',
#                                                            '1203235179','0920994027',
#                                                            '0921561908','0924507254',
#                                                            '0914192141'
#                                                            ])
# #
#
#
#
# for profesorid in listadistri:
#     print(profesorid)
#     if ProfesorDistributivoHoras.objects.filter(profesor=profesorid, periodo_id=177):
#         distrinuevo = ProfesorDistributivoHoras.objects.filter(profesor=profesorid, periodo_id=177)[0]
#
#
#         # distriejemplo = ProfesorDistributivoHoras.objects.filter(profesor__persona__cedula='0921071270', periodo_id=177)[0]
#         distriejemplo = ProfesorDistributivoHoras.objects.filter(profesor__persona__cedula='0923363030', periodo_id=177)[0]
#
#         detadistriejemplo = DetalleDistributivo.objects.filter(distributivo=distriejemplo,criteriodocenciaperiodo__id__isnull=False)
#
#         detadistrinuevo = DetalleDistributivo.objects.filter(distributivo=distrinuevo,criteriodocenciaperiodo__id__isnull=False)[0]
#         detadistrinuevoges = DetalleDistributivo.objects.filter(distributivo=distrinuevo,criteriogestionperiodo__id__isnull=False)[0]
#
#         ClaseActividad.objects.filter(detalledistributivo=detadistrinuevoges).delete()
#         ClaseActividad.objects.filter(detalledistributivo=detadistrinuevo).delete()
#
#         for detejemplo in detadistriejemplo:
#             print('n1' + str(detejemplo.criteriodocenciaperiodo))
#             detalleclase = ClaseActividad.objects.filter(detalledistributivo=detejemplo)
#
#             for dclase in detalleclase:
#                 vigentenew = detadistrinuevo.detalleactividadcriterio()
#                 print(vigentenew)
#                 nuevaclaedoce = dclase
#                 nuevaclaedoce.id = None
#                 nuevaclaedoce.detalledistributivo = detadistrinuevo
#                 nuevaclaedoce.actividaddetallehorario = vigentenew
#                 nuevaclaedoce.save()
#                 print(dclase)
#
#         detadistriejemplo = DetalleDistributivo.objects.filter(distributivo=distriejemplo, criteriogestionperiodo__id__isnull=False)
#
#         for detejemplo in detadistriejemplo:
#             print(detejemplo.criteriogestionperiodo)
#             detalleclase = ClaseActividad.objects.filter(detalledistributivo=detejemplo)
#             for dclase in detalleclase:
#                 vigentenew = detadistrinuevoges.detalleactividadcriterio()
#                 nuevaclaegest = dclase
#                 nuevaclaegest.id = None
#                 nuevaclaegest.detalledistributivo = detadistrinuevoges
#                 nuevaclaegest.actividaddetallehorario = vigentenew
#                 nuevaclaegest.save()
#
#                 print(dclase)
#         actividad = ClaseActividadEstado(periodo_id=177,
#                                          profesor=profesorid,
#                                          personaaprueba_id=1,
#                                          obseaprueba='migracion',
#                                          estadosolicitud=2)
#         actividad.save()
        # distrinuevo = ProfesorDistributivoHoras.objects.filter(profesor=profesorid, periodo_id=177)[0]
        # detadistri = DetalleDistributivo.objects.filter(distributivo=distrinuevo)




    # if not ProfesorDistributivoHoras.objects.filter(profesor=profesorid, periodo_id=177):
    #     distrinuevo = ProfesorDistributivoHoras(profesor=profesorid,
    #                                              periodo_id=177,
    #                                              # dedicacion=profesorid.dedicacion,
    #                                              dedicacion_id=2,
    #                                              horasdocencia=10,
    #                                              horasinvestigacion=0,
    #                                              horasgestion=10,
    #                                              horasvinculacion=0,
    #                                              coordinacion=profesorid.coordinacion,
    #                                              categoria=profesorid.categoria,
    #                                              nivelcategoria=profesorid.nivelcategoria,
    #                                              cargo=profesorid.cargo,
    #                                              nivelescalafon=profesorid.nivelescalafon)
    #     distrinuevo.save()
    #
    #     distriejemplo = ProfesorDistributivoHoras.objects.filter(profesor__persona__cedula='0923363030', periodo_id=177)[0]
    #
    #     if not distrinuevo.detalle_horas_docencia():
    #         detalledoc = distriejemplo.detalle_horas_docencia()
    #         detalleges = distriejemplo.detalle_horas_gestion()
    #         for detadoc in detalledoc:
    #             indetalledoc = detadoc
    #             indetalledoc.id = None
    #             indetalledoc.distributivo = distrinuevo
    #             indetalledoc.save()
    #             print(indetalledoc)
    #             acti = ActividadDetalleDistributivo(criterio=indetalledoc,
    #                                                 nombre=indetalledoc.criteriodocenciaperiodo.criterio.nombre,
    #                                                 desde='2023-08-01',
    #                                                 hasta='2023-08-31',
    #                                                 horas=10,
    #                                                 vigente=True)
    #             acti.save()
    #
    #             print('ni 1' + str(detadoc.criteriodocenciaperiodo))
    #         for detages in detalleges:
    #             indetalleges = detages
    #             indetalleges.id = None
    #             indetalleges.distributivo = distrinuevo
    #             indetalleges.save()
    #             print(indetalleges)
    #             acti = ActividadDetalleDistributivo(criterio=indetalleges,
    #                                                 nombre=indetalleges.criteriogestionperiodo.criterio.nombre,
    #                                                 desde='2023-08-01',
    #                                                 hasta='2023-08-31',
    #                                                 horas=10,
    #                                                 vigente=True)
    #             acti.save()
    #             print('ni 1' + str(detages.criteriogestionperiodo))
    # else:
    #
    #     distriejemplo = ProfesorDistributivoHoras.objects.filter(profesor__persona__cedula='0923363030', periodo_id=177)[0]
    #
    #     distrinuevo = ProfesorDistributivoHoras.objects.filter(profesor=profesorid, periodo_id=177)[0]
    #     distrinuevo.horasdocencia=10
    #     distrinuevo.horasgestion=10
    #     distrinuevo.dedicacion_id=2
    #     distrinuevo.save()
    #
    #     DetalleDistributivo.objects.filter(distributivo=distrinuevo).delete()
    #
    #     if not distrinuevo.detalle_horas_docencia():
    #         detalledoc = distriejemplo.detalle_horas_docencia()
    #         detalleges = distriejemplo.detalle_horas_gestion()
    #         for detadoc in detalledoc:
    #             indetalledoc = detadoc
    #             indetalledoc.id = None
    #             indetalledoc.distributivo = distrinuevo
    #             indetalledoc.save()
    #             print(indetalledoc)
    #             acti = ActividadDetalleDistributivo(criterio=indetalledoc,
    #                                                 nombre=indetalledoc.criteriodocenciaperiodo.criterio.nombre,
    #                                                 desde='2023-08-01',
    #                                                 hasta='2023-08-31',
    #                                                 horas=10,
    #                                                 vigente=True)
    #             acti.save()
    #
    #             print('ni 1' + str(detadoc.criteriodocenciaperiodo))
    #         for detages in detalleges:
    #             indetalleges = detages
    #             indetalleges.id = None
    #             indetalleges.distributivo = distrinuevo
    #             indetalleges.save()
    #             print(indetalleges)
    #             acti = ActividadDetalleDistributivo(criterio=indetalleges,
    #                                                 nombre=indetalleges.criteriogestionperiodo.criterio.nombre,
    #                                                 desde='2023-08-01',
    #                                                 hasta='2023-08-31',
    #                                                 horas=10,
    #                                                 vigente=True)
    #             acti.save()
    #             print('ni 1' + str(detages.criteriogestionperiodo))


# ricardo

#


# POA DUPLICADO
# periodopoa = PeriodoPoa.objects.get(pk=12)
# periodopoa.ingresar = False
# periodopoa.save()
# periodopoa.id = None
# periodopoa.mostrar = True
# periodopoa.archivo = None
# periodopoa.edicion = True
# periodopoa.activo = True
# periodopoa.descripcion = 'TRASPASO, EDITE LA DESCRIPCION'
# periodopoa.save()
# a = PeriodoPoa.objects.get(pk=12)
# for i in InformeGenerado.objects.filter(periodopoa=a):
#     i.id = None
#     i.periodopoa = periodopoa
#     i.save()
#
# for evperpoa in EvaluacionPeriodoPoa.objects.filter(periodopoa=a):
#     matrizval = evperpoa.matrizvaloracionpoa_set.filter(status=True)
#     evperiodopoa = evperpoa
#     evperiodopoa.id = None
#     evperiodopoa.periodopoa = periodopoa
#     evperiodopoa.save()
#
#     for mval in matrizval:
#         march = mval.matrizarchivospoa_set.filter(status=True)
#         maexpoa = mval.matrizvaloracionexpertospoa_set.filter(status=True)
#         mafirpoa = mval.matrizevaluacionfirmaspoa_set.filter(status=True)
#         matrizvalp = mval
#         matrizvalp.id = None
#         matrizvalp.evaluacionperiodo = evperiodopoa
#         matrizvalp.save()
#         print('matrices valoraciones poa')
#         for archpoa in march:
#             marchivopoa = archpoa
#             marchivopoa.id = None
#             marchivopoa.matrizvaloracionpoa = matrizvalp
#             marchivopoa.save()
#             print('matrices archivo valoracion poa')
#         for expoa in maexpoa:
#             mexperpoa = expoa
#             mexperpoa.id = None
#             mexperpoa.matrizvaloracionpoa = matrizvalp
#             mexperpoa.save()
#             print('matrices expertos valoracion poa')
#         for fir in mafirpoa:
#             mfirmas = fir
#             mfirmas.id = None
#             mfirmas.matrizvaloracionpoa = matrizvalp
#             mfirmas.save()
#             print('matrices firmas valoracion poa')
#
#
# for p in PeriodoPoa.objects.filter(pk=12):
#     periodoobjestrategico = p.objetivoestrategico_set.filter(status=True)
#     for oe in periodoobjestrategico:
#         aux_oe = oe.objetivotactico_set.filter(status=True)
#         # print(aux_oe)
#         objestra = oe
#         objestra.id = None
#         objestra.periodopoa = periodopoa
#         objestra.save()
#         print('nivel obj estrategico')
#         print(aux_oe)
#         for ot in aux_oe:
#             aux_ot = ot.objetivooperativo_set.filter(status=True)
#             objtac = ot
#             objtac.id = None
#             objtac.objetivoestrategico = objestra
#             objtac.save()
#             print('nivel obj operativo')
#             print(aux_ot)
#             for oo in aux_ot:
#                 objmeta = oo.id
#                 aux_oo = oo.indicadorpoa_set.filter(status=True)
#                 objopera = oo
#                 objopera.id = None
#                 objopera.objetivotactico = objtac
#                 objopera.save()
#                 print('nivel indicador')
#                 print(aux_oo)
#
#                 if MetaPoa.objects.filter(objetivooperativo_id=objmeta, status=True):
#                     obmeta = ObjetivoOperativo.objects.get(pk=objmeta)
#                     listaobmeta = obmeta.metapoa_set.filter(status=True)
#                     for copimeta in listaobmeta:
#                         evalumeta = EvaluacionPeriodoPoa.objects.filter(periodopoa=periodopoa, descripcion=copimeta.evaluacionperiodo.descripcion, status=True)[0]
#                         newmeta = copimeta
#                         newmeta.id = None
#                         newmeta.objetivooperativo = objopera
#                         newmeta.evaluacionperiodo = evalumeta
#                         newmeta.save()
#
#                 for i in aux_oo:
#                     indimatriz = i.id
#                     aux_i = i.acciondocumento_set.filter(status=True)
#                     indicador = i
#                     indicador.id = None
#                     indicador.objetivooperativo = objopera
#                     indicador.save()
#                     print(indimatriz)
#                     if DetalleMatrizValoracionPoa.objects.filter(actividad_id=indimatriz, status=True):
#                         indimatrizcopi = IndicadorPoa.objects.get(pk=indimatriz)
#                         copiardetallematriz = indimatrizcopi.detallematrizvaloracionpoa_set.filter(status=True)
#                         print('tiene detalle matriz')
#                         for cdetallematriz in copiardetallematriz:
#
#                             copideta = cdetallematriz
#                             matrizactual = MatrizValoracionPoa.objects.filter(evaluacionperiodo__periodopoa=periodopoa,
#                                                                               evaluacionperiodo__descripcion=cdetallematriz.matrizvaloracion.evaluacionperiodo.descripcion,
#                                                                               departamento=cdetallematriz.matrizvaloracion.departamento, status=True)[0]
#                             copideta.id = None
#                             copideta.matrizvaloracion = matrizactual
#                             copideta.actividad = indicador
#                             copideta.save()
#                             print('detalle matriz valoracion poa')
#
#
#                         print('si tiene')
#                     if DetalleMatrizEvaluacionPoa.objects.filter(actividad_id=indimatriz, status=True):
#                         indimatrizcopi = IndicadorPoa.objects.get(pk=indimatriz)
#                         copiardetallematriz = indimatrizcopi.detallematrizevaluacionpoa_set.filter(status=True)
#                         print('tiene detalle matriz')
#                         for cdetallematriz in copiardetallematriz:
#
#                             copidetavalo = cdetallematriz
#                             matrizactual = MatrizValoracionPoa.objects.filter(evaluacionperiodo__periodopoa=periodopoa,
#                                                                               evaluacionperiodo__descripcion=cdetallematriz.matrizvaloracion.evaluacionperiodo.descripcion,
#                                                                               departamento=cdetallematriz.matrizvaloracion.departamento, status=True)[0]
#                             copidetavalo.id = None
#                             copidetavalo.matrizvaloracion = matrizactual
#                             copidetavalo.actividad = indicador
#                             copidetavalo.save()
#                             print('detalle matriz evaluacion poa')
#
#
#                         print('si tiene')
#                     print('nivel accion documento')
#                     print(aux_i)
#                     for ad in aux_i:
#                         aux_ad = ad.acciondocumentodetalle_set.filter(status=True)
#                         acciondoc = ad
#                         acciondoc.id = None
#                         acciondoc.indicadorpoa = indicador
#                         acciondoc.save()
#                         print('nivel detalle accion documento')
#                         print(aux_ad)
#                         for acd in aux_ad:
#                             evidaccion = acd.id
#                             aux_acd = acd.acciondocumentodetallerecord_set.filter(status=True)
#                             acciondocdetalle = acd
#                             acciondocdetalle.id = None
#                             acciondocdetalle.acciondocumento = acciondoc
#                             acciondocdetalle.save()
#                             print('nivel accion detalle record')
#                             print(aux_acd)
#
#                             if EvidenciaDocumentalPoa.objects.filter(acciondocumentodetalle_id=evidaccion, status=True):
#                                 acddocdeta = AccionDocumentoDetalle.objects.get(pk=evidaccion)
#                                 listacodmeta = acddocdeta.evidenciadocumentalpoa_set.filter(status=True)
#                                 for copidocument in listacodmeta:
#
#                                     newevidocumento = copidocument
#                                     newevidocumento.id = None
#                                     newevidocumento.acciondocumentodetalle = acciondocdetalle
#                                     if copidocument.evaluacionperiodo:
#                                         if EvaluacionPeriodoPoa.objects.filter(periodopoa=periodopoa, descripcion=copidocument.evaluacionperiodo.descripcion, status=True):
#                                             evalumetadocu = EvaluacionPeriodoPoa.objects.filter(periodopoa=periodopoa, descripcion=copidocument.evaluacionperiodo.descripcion, status=True)[0]
#                                             newevidocumento.evaluacionperiodo = evalumetadocu
#
#                                     newevidocumento.save()
#
#                             for adr in aux_acd:
#                                 acciondetallerecord = adr
#                                 acciondetallerecord.id = None
#                                 acciondetallerecord.acciondocumentodetalle = acciondocdetalle
#                                 acciondetallerecord.save()
#                                 print('nivel guardando record')



# import openpyxl
# workbook = openpyxl.load_workbook("archivodistri.xlsx")
# # worksheet = workbook.active
# # worksheet = workbook.get_sheet_by_name("Hoja2")
# worksheet = workbook["Hoja2"]
# periodolec = Periodo.objects.get(pk=224)
# # columna_verificacion = worksheet['Hoja2']
# for fila in worksheet.iter_rows(min_row=2, values_only=True):
#     if not fila[0]:  # Verifica si la primera columna no está vacía
#         break
#     valor_celda = fila[4]
#
#     print(valor_celda)
#     if Profesor.objects.filter(persona__cedula=fila[3]):
#         profesor = Profesor.objects.filter(persona__cedula=fila[3])[0]
#         distributivo = profesor.distributivohoras(periodolec)
#         distributivo.bloqueardistributivo=False
#         distributivo.save()
#
#         # if int(fila[0]) == 1:
#         #     if not DetalleDistributivo.objects.filter(distributivo=distributivo, criteriodocenciaperiodo_id=fila[2]):
#         #         detalle = DetalleDistributivo(distributivo=distributivo,
#         #                                       criteriodocenciaperiodo_id=fila[2],
#         #                                       horas=fila[5])
#         #         detalle.save()
#         #         detalle.actualiza_padre()
#         #         ad = ActividadDetalleDistributivo(criterio=detalle,
#         #                                           nombre=detalle.criteriodocenciaperiodo.criterio.nombre,
#         #                                           desde=distributivo.periodo.inicio,
#         #                                           hasta=distributivo.periodo.fin,
#         #                                           horas=detalle.horas)
#         #         ad.save()
#         if int(fila[0]) == 2:
#             if not DetalleDistributivo.objects.filter(distributivo=distributivo, criterioinvestigacionperiodo_id=fila[2]):
#                 detalle = DetalleDistributivo(distributivo=distributivo,
#                                               criterioinvestigacionperiodo_id=fila[2],
#                                               horas=fila[5])
#                 detalle.save()
#                 # detalle.actualiza_padre()
#                 ad = ActividadDetalleDistributivo(criterio=detalle,
#                                                   nombre=detalle.criterioinvestigacionperiodo.criterio.nombre,
#                                                   desde=distributivo.periodo.inicio,
#                                                   hasta=distributivo.periodo.fin,
#                                                   horas=detalle.horas)
#                 ad.save()
#
#                 distributivo.bloqueardistributivo = True
#                 distributivo.save()

#
# codigosmateriainvestigacion = [836,
# 1026,
# 1832,
# 1876,
# 2186,
# 2236,
# 3274,
# 3282,
# 3288,
# 3337,
# 3350,
# 3441,
# 3739,
# 10088,
# 10123
# ]
# listadopm = ProfesorMateria.objects.filter(materia__nivel__periodo_id=224, tipoprofesor_id=16,materia__modeloevaluativo_id=27,materia__asignaturamalla__asignatura_id__in=codigosmateriainvestigacion)
#
# listadopromateria = ProfesorMateria.objects.filter(materia__nivel__periodo_id=224, tipoprofesor_id=16,materia__modeloevaluativo_id=27,materia__id=72247)
#
# materia = Materia.objects.get(pk=72247)
# if materia.profesormateria_set.values('id').filter(tipoprofesor_id=16, status=True).exists():
#     l= materia.profesormateria_set.filter(tipoprofesor_id=16, status=True)
# else:
#     l= materia.profesormateria_set.filter(tipoprofesor__firmasilabo=True, status=True)
#
# for proma in listadopromateria:
#     silabo = Silabo.objects.filter(materia=proma.materia, status=True)[0]
#     if silabo.versionsilabo == 2 and silabo.materia.nivel.periodo.tipo.id in [1, 2]:
#         qrname = 'qr_silabo_' + str(encrypt(silabo.id))
#         folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'silabodocente', 'qr'))
#         # folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'silabodocente', ''))
#         rutapdf = folder + qrname + '.pdf'
#         rutaimg = folder + qrname + '.png'
#         if os.path.isfile(rutapdf):
#             os.remove(rutapdf)
#         if os.path.isfile(rutaimg):
#             os.remove(rutaimg)
#         url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/silabodocente/' + qrname + '.pdf')
#         # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/silabodocente/' + qrname + '.pdf')
#         imageqr = url.png(folder + qrname + '.png', 16, '#000000')
#         imagenqr = 'qr' + qrname
#         valida = conviert_html_to_pdfsaveqrsilabo(
#             'pro_planificacion/silabovs2_pdf.html',
#             {'datos': silabo.silabodetalletemas_pdf(),
#              'data': silabo.silabovdos_pdf(),
#              'imprimeqr': True,
#              'qrname': imagenqr
#              }, qrname + '.pdf'
#         )
#         if valida:
#             os.remove(rutaimg)
#             silabo.codigoqr = True
#             silabo.save()
#

# inscripcion = Inscripcion.objects.get(pk=56415)
#
# inscrimalla = inscripcion.inscripcionmalla_set.filter(status=True).first()
#
#
# requisitotitulacion = inscrimalla.malla.requisitotitulacionmalla_set.filter(status=True)
# print(requisitotitulacion.query)
# # print(requisitotitulacion)
# from django.db.models import Case, When, Value, IntegerField
# listado = CapCabeceraSolicitudDocente.objects.filter(status=True).annotate(
#     estado=Case(
#         When(capdetallesolicituddocente__status=True, then=F('capdetallesolicituddocente__estado')),
#         default=Value(None, output_field=IntegerField())
#     )
# )
#
# print(listado)
#
# for lista in listado:
#     print(lista)
#     print(lista.estado)

# listado = SagResultadoEncuesta.objects.filter(inscripcion_id=79135, status=True)
# listado.delete()
#
# inscri = Inscripcion.objects.get(pk=79135)
# cache.delete(f"encuestaegresado_por_contestar_alumnos_panel_{encrypt(inscri.id)}")
#
#

# lista_odilo_libros = request.session['lista_odilo_libros']
# if lista_odilo_libros:
#     for odil in lista_odilo_libros:
# listadoperiodo = Periodo.objects.filter(pk=85)
# print(listadoperiodo.query)
# for peri in listadoperiodo:
#     print('comenzando')
#     peri.delete()
#     print(peri)
#     print('terminado')

# print(encrypt(74001))
# print(encrypt(70629))

# gradu = Graduado.objects.get(pk=23383)
# gradu.delete()


# periodoid = Periodo.objects.get(pk=177)
# profe = Profesor.objects.filter(persona__cedula='0960578094')[0]
# print(profe)
# distributivo = profe.distributivohoraseval(periodoid)
# resumen = distributivo.resumen_evaluacion_acreditacion()
# resumen.actualizar_resumen()

# listadores = RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=4, proceso__periodo_id=177)
# listadores = RespuestaEvaluacionAcreditacion.objects.filter(pk__in=[2203221],tipoinstrumento=3, proceso__periodo_id=177)
# totales = listadores.count()
# cuenta = 0
# for res in listadores:
#     cuenta = cuenta + 1
#     res.delete()
#     print(str(cuenta) + ' de ' + str(totales))
# ins = Inscripcion.objects.get(pk=79150)
# mimalla = ins.mi_malla()
# ultimonivel = mimalla.ultimo_nivel_malla()
#
# print(mimalla.id)
# niveles = NivelMalla.objects.filter(pk__in=mimalla.asignaturamalla_set.values_list("nivelmalla_id", flat=True).filter(status=True).distinct())
# print(niveles.query)
# print(ultimonivel)
#
#
#
# from openpyxl import load_workbook, workbook as openxl
# from openpyxl.styles import Font as openxlFont
# from openpyxl.styles.alignment import Alignment as alin
# from datetime import datetime, timedelta, date
# hoy = datetime.now().date()
# # nombre_archivo = generar_nombre("reporte_auditoria", '') + '.xlsx'
# url = ''
# directory = os.path.join(SITE_STORAGE, 'media', 'auditoria')
# try:
#     os.stat(directory)
# except:
#     os.mkdir(directory)
#
#
# listadoperiodos = Periodo.objects.filter(pk__in=[110,112,113,119,126,153,177])
#
# totalperiodos = listadoperiodos.count()
# cuentaperiodo = 0
# for lper in listadoperiodos:
#     cuentaperiodo += 1
#     nombre_archivo = str(lper.id) + '.xlsx'
#     directory = os.path.join(MEDIA_ROOT, 'auditoria', nombre_archivo)
#     folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'auditoria',''))
#     rutaexcell = folder + str(nombre_archivo)
#     if os.path.isfile(rutaexcell):
#         os.remove(rutaexcell)
#     # Inicializo cabecera de  excel
#     __author__ = 'Unemi'
#     wb = openxl.Workbook()
#     ws = wb.active
#     style_title = openxlFont(name='Arial', size=14, bold=True)
#     style_cab = openxlFont(name='Arial', size=10, bold=True)
#     alinear = alin(horizontal="center", vertical="center")
#     response = HttpResponse(content_type="application/ms-excel")
#     response['Content-Disposition'] = f'attachment; filename={lper.id}' + '-' + random.randint(1, 10000).__str__() + '.xlsx'
#     ws.merge_cells('A1:E1')
#     ws.merge_cells('A2:E2')
#     ws['A1'] = 'UNIVERSIDAD ESTATAL DE MILAGRO'
#     ws['A2'] = 'REPORTE DE AUDITORIA'
#     celda1 = ws['A1']
#     celda1.font = style_title
#     celda1.alignment = alinear
#     celda2 = ws['A2']
#     celda2.font = style_title
#     celda2.alignment = alinear
#     columns = ['periodo',
#                'carrera',
#                'modalidad',
#                'cedula',
#                'genero',
#                'alumno',
#                'edad',
#                'nivel_socio',
#                'ppl',
#                'provincia',
#                'dis',
#                'materia',
#                'paralelo',
#                'nivel',
#                'exa1',
#                'exa2',
#                'nota_final',
#                ]
#     row_num = 3
#     for col_num in range(0, len(columns)):
#         celda = ws.cell(row=row_num, column=(col_num + 1), value=columns[col_num])
#         celda.font = style_cab
#     row_num = 4
#
#     #Obtencion de directorio y varibles requeridas
#     # directory = os.path.join(MEDIA_ROOT, 'auditoria', nombre_archivo)
#
#     listadoalumnos = MateriaAsignada.objects.filter(materia__nivel__periodo_id=lper.id,
#                                                     # matricula__inscripcion__persona__cedula='0942486861',
#                                                     retiromanual=False,
#                                                     matricula__retiradomatricula=False,
#                                                     matricula__status=True,
#                                                     materia__status=True,
#                                                     materia__asignaturamalla__status=True,
#                                                     materia__asignaturamalla__asignatura__modulo=False,
#                                                     status=True).\
#         exclude(materia__asignaturamalla__malla__carrera__coordinacion__id=9).\
#         order_by('materia__nivel__periodo','materia__asignaturamalla__malla__carrera__nombre',
#                  'materia__asignaturamalla__nivelmalla__id', 'matricula__inscripcion__persona__apellido1',
#                  'matricula__inscripcion__persona__apellido2','materia__asignaturamalla__asignatura__nombre')
#
#     # baseDate = datetime.today()
#     totales = listadoalumnos.count()
#     cuentamatri=0
#     for lmatri in listadoalumnos:
#         esppl = 'NO'
#         nombreprovincia = ''
#         if lmatri.matricula.inscripcion.persona.provincia:
#             nombreprovincia = lmatri.matricula.inscripcion.persona.provincia.nombre
#         if lmatri.matricula.inscripcion.persona.ppl:
#             esppl = 'SI'
#         nivelsocio = ''
#         if lmatri.matricula.matriculagruposocioeconomico():
#             nivelsocio=lmatri.matricula.matriculagruposocioeconomico().nombre
#
#         disca = ''
#         if lmatri.matricula.inscripcion.persona.tiene_discapasidad():
#             disca=lmatri.matricula.inscripcion.persona.tiene_discapasidad()[0].tipodiscapacidad.nombre
#         fechanace = ''
#         if lmatri.matricula.inscripcion.persona.nacimiento:
#             fechanacimiento = lmatri.matricula.inscripcion.persona.nacimiento
#             if  fechanacimiento < hoy:
#                 edad = hoy.year - fechanacimiento.year - ((hoy.month, hoy.day) < (fechanacimiento.month, fechanacimiento.day))
#                 # print(edad)
#         genero = ''
#         if lmatri.matricula.inscripcion.persona.sexo:
#             if lmatri.matricula.inscripcion.persona.sexo.id == 1:
#                 genero = 'MUJER'
#             else:
#                 genero = 'HOMBRE'
#         exa1=0
#         exa2 = ''
#         if lmatri.evaluaciongenerica_set.values("valor").filter(detallemodeloevaluativo__alternativa_id=20,status=True):
#             listaexa1 = lmatri.evaluaciongenerica_set.filter(detallemodeloevaluativo__alternativa_id=20,status=True).order_by('detallemodeloevaluativo__nombre')[0]
#             # print(lmatri.evaluaciongenerica_set.values("valor").filter(detallemodeloevaluativo__alternativa_id=20,status=True).query)
#             exa1=listaexa1.valor
#             idexa1=listaexa1.id
#
#             if lmatri.evaluaciongenerica_set.values("valor").filter(detallemodeloevaluativo__alternativa_id=20,status=True).exclude(pk=idexa1):
#
#                 listaexa2 = lmatri.evaluaciongenerica_set.filter(detallemodeloevaluativo__alternativa_id=20,status=True).exclude(pk=idexa1).order_by('-detallemodeloevaluativo__nombre')[0]
#
#                 exa2 = listaexa2.valor
#         ws.cell(row=row_num, column=1, value=lmatri.materia.nivel.periodo.__str__())
#         ws.cell(row=row_num, column=2, value=lmatri.materia.asignaturamalla.malla.carrera.__str__())
#         ws.cell(row=row_num, column=3, value=lmatri.materia.nivel.modalidad.__str__())
#         ws.cell(row=row_num, column=4, value=lmatri.matricula.inscripcion.persona.cedula.__str__())
#         ws.cell(row=row_num, column=5, value=genero)
#         ws.cell(row=row_num, column=6, value=lmatri.matricula.inscripcion.persona.__str__())
#         ws.cell(row=row_num, column=7, value=edad)
#         ws.cell(row=row_num, column=8, value=nivelsocio.__str__())
#         ws.cell(row=row_num, column=9, value=esppl.__str__())
#         ws.cell(row=row_num, column=10, value=nombreprovincia.__str__())
#         ws.cell(row=row_num, column=11, value=disca.__str__())
#         ws.cell(row=row_num, column=12, value=lmatri.materia.asignaturamalla.asignatura.nombre)
#         ws.cell(row=row_num, column=13, value=lmatri.materia.paralelo)
#         ws.cell(row=row_num, column=14, value=lmatri.materia.asignaturamalla.nivelmalla.__str__())
#         ws.cell(row=row_num, column=15, value=exa1)
#         ws.cell(row=row_num, column=16, value=exa2)
#         ws.cell(row=row_num, column=17, value=lmatri.notafinal)
#         # ws.cell(row=row_num, column=2, value=xItem[0].time())
#         # ws.cell(row=row_num, column=3, value=accion)
#         # ws.cell(row=row_num, column=4, value=xItem[3])
#         # ws.cell(row=row_num, column=5, value=l.get_data_message())
#         row_num += 1
#         cuentamatri += 1
#         print('periodo: ' + str(cuentaperiodo) + ' de ' + str(totalperiodos) + ' periodos | registros: ' + str(cuentamatri) + ' de ' + str(totales))
#     wb.save(directory)


#
# listadoniveles = Nivel.objects.filter(periodo_id=258)
#
#
# conta = 0
# for lni in listadoniveles:
#     conta = conta + 1
#     print('ff')
#     lismate = lni.materia_set.filter(status=True)
#     lnivelcoor = lni.nivellibrecoordinacion_set.filter(status=True)
#     lni.id = None
#     lni.periodo_id = 317
#     lni.save()
#     print('copiando niveles')
#     print(lismate)
#     for nico in lnivelcoor:
#         nico.id = None
#         nico.nivel = lni
#         nico.save()
#         print('copiando nicelcoord')
#     for lmate in lismate:
#         print('aa')
#         lproma = lmate.profesormateria_set.filter(status=True)
#         lmate.id = None
#         lmate.nivel = lni
#         lmate.save()
#         print('copiando materias')
#         for lpm in lproma:
#             lpm.id = None
#             lpm.materia = lmate
#             lpm.save()
#             print('copiando promate')
