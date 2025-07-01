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
from moodle import moodle

def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]),int(fecha[5:7]),int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()

def calculate_username(persona, variant=1):
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    s = persona.nombres.lower().split(' ')
    while '' in s:
        s.remove('')
    if persona.apellido2:
        usernamevariant = s[0][0] + persona.apellido1.lower() + persona.apellido2.lower()[0]
    else:
        usernamevariant = s[0][0] + persona.apellido1.lower()
    usernamevariant = usernamevariant.replace(' ', '').replace(u'ñ', 'n').replace(u'á', 'a').replace(u'é', 'e').replace(u'í', 'i').replace(u'ó', 'o').replace(u'ú', 'u')
    usernamevariantfinal = ''
    for letra in usernamevariant:
        if letra in alfabeto:
            usernamevariantfinal += letra
    if variant > 1:
        usernamevariantfinal += str(variant)
    if not User.objects.values('id').filter(username=usernamevariantfinal).exclude(persona=persona).exists():
        return usernamevariantfinal
    else:
        return calculate_username(persona, variant + 1)

def generar_usuario(persona, usuario, group_id):
    password = DEFAULT_PASSWORD
    if CLAVE_USUARIO_CEDULA:
        password = persona.cedula
    user = User.objects.create_user(usuario, '', password)
    user.save()
    persona.usuario = user
    persona.save()
    persona.cambiar_clave()
    g = Group.objects.get(pk=group_id)
    g.user_set.add(user)
    g.save()

def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha

# #importacion de notas de moodle
#
# for materia in Materia.objects.filter(status=True, nivel__periodo__id=80, asignaturamalla__malla__carrera__coordinacion__id=9, nivel__id=383):
#     print(materia)
#     for alumno in materia.asignados_a_esta_materia_moodle().filter(retiramateria=False):
#         # Extraer datos de moodle
#
#         for notasmooc in materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
#             campo = alumno.campo(notasmooc[1].upper())
#             if type(notasmooc[0]) is Decimal:
#                 if null_to_decimal(campo.valor) != float(notasmooc[0]):
#                     actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
#                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=notasmooc[0])
#                     auditorianotas.save()
#             else:
#                 if null_to_decimal(campo.valor) != float(0):
#                     actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
#                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
#                     auditorianotas.save()
#
#         # for notasmooc in materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
#         #     if type(notasmooc[0]) is Decimal:
#         #         campo = alumno.campo(notasmooc[1].upper())
#         #         if null_to_decimal(campo.valor) != float(notasmooc[0]):
#         #             actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
# print('listo')


# alumnos del PRE nuevos ddd
# workbook = xlrd.open_workbook("lista alumnos con problemas asignaturas matricular moodle.xlsx")
# sheet = workbook.sheet_by_index(0)
# linea = 1
#
# periodo = Periodo.objects.get(pk=90)
# try:
#     for rowx in range(sheet.nrows):
#         if linea>1:
#             cols = sheet.row_values(rowx)
#             session_id = 13
#             cedula = cols[0].strip().upper()
#             pais=None
#             paisnac=None
#             provincia=None
#             canton=None
#             persona=None
#             email=None
#             mimalla=None
#             if Persona.objects.filter(cedula=cedula, status=True).exists():
#                 persona = Persona.objects.get(cedula=cedula, status=True)
#             if Persona.objects.filter(pasaporte=cedula, status=True).exists():
#                 persona = Persona.objects.get(pasaporte=cedula, status=True)
#             sesion = Sesion.objects.get(id=session_id)
#             idcarrera=int(cols[6])
#             carrera = Carrera.objects.get(pk=idcarrera)
#             modalidad = Modalidad.objects.get(pk=int(cols[8]))
#             sede = Sede.objects.get(pk=1)
#             inscripcion = Inscripcion.objects.filter(persona=persona,carrera=carrera)[0]
#             matricula = Matricula.objects.get(inscripcion=inscripcion, nivel__periodo=periodo)
#             for materiaasignada in MateriaAsignada.objects.filter(matricula=matricula):
#                 materiaasignada.materia.crear_actualizar_estudiantes_curso(moodle, 2, matricula)
#         linea += 1
#         print(linea)
# except Exception as ex:
#     print(ex)




periodo = Periodo.objects.get(pk=90)
matriculas = Matricula.objects.filter(inscripcion__carrera__id__in=[100, 99,101, 97, 98, 105,104],inscripcion__carrera__modalidad=3,nivel__periodo=periodo, estado_matricula__in=[2,3], status=True).distinct()
try:
    for matricula in matriculas:
        persona = matricula.inscripcion.persona
        idnumber_user = persona.identificacion()
        bestudiante = moodle.BuscarUsuario(periodo, 2, 'idnumber', idnumber_user)
        estudianteid = 0
        if not bestudiante:
            bestudiante = moodle.BuscarUsuario(periodo, 2, 'idnumber', idnumber_user)

        if bestudiante['users']:
            if 'id' in bestudiante['users'][0]:
                estudianteid = bestudiante['users'][0]['id']
        if estudianteid>0:
            moodle.EnrolarCurso(periodo, 2, periodo.rolestudiante, estudianteid, 945)
            print('************Estudiante: %s' % ( persona))
        else:
            print('************No se pudo encontrar: %s ' % (persona))
except Exception as ex:
    print(ex)



