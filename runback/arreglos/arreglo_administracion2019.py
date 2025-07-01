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

# cambio de malla del 2019 al 2012
# administracion = 140

id_carrera19= 140
id_malla = 212

#proceso 1
asignatura1 = 941
equivalenciaasignatura1 = (666,947,846)
inscripciontodo = Inscripcion.objects.filter(status=True, carrera_id=id_carrera19, recordacademico__asignatura_id=asignatura1, recordacademico__aprobada=True).distinct()
cantidad = inscripciontodo.count()
print ("Cantidad: %s" % cantidad)
for inscripcion in inscripciontodo:
    print (cantidad)
    cantidad=cantidad-1
    # sacar la nota de la materia principal
    record = inscripcion.recordacademico_set.get(status=True, aprobada=True, asignatura_id=asignatura1)
    for e in equivalenciaasignatura1:
        if int(e) > 0:
            if not inscripcion.recordacademico_set.filter(status=True, asignatura_id=int(e)):
                asignaturamalla = AsignaturaMalla.objects.get(asignatura_id=int(e), status=True, malla_id=id_malla)
                record1 = RecordAcademico(inscripcion=inscripcion,
                                          asignatura=asignaturamalla.asignatura,
                                          nota=record.nota,
                                          asistencia=record.asistencia,
                                          fecha=datetime.now().date(),
                                          convalidacion=False,
                                          aprobada=True,
                                          pendiente=False,
                                          creditos=asignaturamalla.creditos,  # preguntar
                                          horas=asignaturamalla.horas,  # preguntar
                                          homologada=False,
                                          valida=True,
                                          observaciones="PROCESO ADMINISTRACION 2019 A 40 MATERIAS - "+record.asignatura.nombre)
                record1.save()
                record1.actualizar()


#proceso 2
asignatura2 = 210
equivalenciaasignatura2 = (2237,0)
inscripciontodo = Inscripcion.objects.filter(status=True, carrera_id=id_carrera19, recordacademico__asignatura_id=asignatura2, recordacademico__aprobada=True).distinct()
cantidad = inscripciontodo.count()
print ("Cantidad: %s" % cantidad)
for inscripcion in inscripciontodo:
    print (cantidad)
    cantidad=cantidad-1
    # sacar la nota de la materia principal
    record = inscripcion.recordacademico_set.get(status=True, aprobada=True, asignatura_id=asignatura2)
    for e in equivalenciaasignatura2:
        if int(e) > 0:
            if not inscripcion.recordacademico_set.filter(status=True, asignatura_id=int(e)):
                asignaturamalla = AsignaturaMalla.objects.get(asignatura_id=int(e), status=True, malla_id=id_malla)
                record1 = RecordAcademico(inscripcion=inscripcion,
                                          asignatura=asignaturamalla.asignatura,
                                          nota=record.nota,
                                          asistencia=record.asistencia,
                                          fecha=datetime.now().date(),
                                          convalidacion=False,
                                          aprobada=True,
                                          pendiente=False,
                                          creditos=asignaturamalla.creditos,  # preguntar
                                          horas=asignaturamalla.horas,  # preguntar
                                          homologada=False,
                                          valida=True,
                                          observaciones="PROCESO ADMINISTRACION 2019 A 40 MATERIAS - "+record.asignatura.nombre)
                record1.save()
                record1.actualizar()




#proceso 3
asignatura3 = 2055
equivalenciaasignatura3 = (126,3880)
inscripciontodo = Inscripcion.objects.filter(status=True, carrera_id=id_carrera19, recordacademico__asignatura_id=asignatura3, recordacademico__aprobada=True).distinct()
cantidad = inscripciontodo.count()
print ("Cantidad: %s" % cantidad)
for inscripcion in inscripciontodo:
    print (cantidad)
    cantidad=cantidad-1
    # sacar la nota de la materia principal
    record = inscripcion.recordacademico_set.get(status=True, aprobada=True, asignatura_id=asignatura3)
    for e in equivalenciaasignatura3:
        if int(e) > 0:
            if not inscripcion.recordacademico_set.filter(status=True, asignatura_id=int(e)):
                asignaturamalla = AsignaturaMalla.objects.get(asignatura_id=int(e), status=True, malla_id=id_malla)
                record1 = RecordAcademico(inscripcion=inscripcion,
                                          asignatura=asignaturamalla.asignatura,
                                          nota=record.nota,
                                          asistencia=record.asistencia,
                                          fecha=datetime.now().date(),
                                          convalidacion=False,
                                          aprobada=True,
                                          pendiente=False,
                                          creditos=asignaturamalla.creditos,  # preguntar
                                          horas=asignaturamalla.horas,  # preguntar
                                          homologada=False,
                                          valida=True,
                                          observaciones="PROCESO ADMINISTRACION 2019 A 40 MATERIAS - "+record.asignatura.nombre)
                record1.save()
                record1.actualizar()


#proceso 4
asignatura4 = 2051
equivalenciaasignatura4 = (612,0)
inscripciontodo = Inscripcion.objects.filter(status=True, carrera_id=id_carrera19, recordacademico__asignatura_id=asignatura4, recordacademico__aprobada=True).distinct()
cantidad = inscripciontodo.count()
print ("Cantidad: %s" % cantidad)
for inscripcion in inscripciontodo:
    print (cantidad)
    cantidad=cantidad-1
    # sacar la nota de la materia principal
    record = inscripcion.recordacademico_set.get(status=True, aprobada=True, asignatura_id=asignatura4)
    for e in equivalenciaasignatura4:
        if int(e) > 0:
            if not inscripcion.recordacademico_set.filter(status=True, asignatura_id=int(e)):
                asignaturamalla = AsignaturaMalla.objects.get(asignatura_id=int(e), status=True, malla_id=id_malla)
                record1 = RecordAcademico(inscripcion=inscripcion,
                                          asignatura=asignaturamalla.asignatura,
                                          nota=record.nota,
                                          asistencia=record.asistencia,
                                          fecha=datetime.now().date(),
                                          convalidacion=False,
                                          aprobada=True,
                                          pendiente=False,
                                          creditos=asignaturamalla.creditos,  # preguntar
                                          horas=asignaturamalla.horas,  # preguntar
                                          homologada=False,
                                          valida=True,
                                          observaciones="PROCESO ADMINISTRACION 2019 A 40 MATERIAS - "+record.asignatura.nombre)
                record1.save()
                record1.actualizar()



#proceso 5
asignatura5 = 3778
equivalenciaasignatura5 = (4725,0)
inscripciontodo = Inscripcion.objects.filter(status=True, carrera_id=id_carrera19, recordacademico__asignatura_id=asignatura5, recordacademico__aprobada=True).distinct()
cantidad = inscripciontodo.count()
print ("Cantidad: %s" % cantidad)
for inscripcion in inscripciontodo:
    print (cantidad)
    cantidad=cantidad-1
    # sacar la nota de la materia principal
    record = inscripcion.recordacademico_set.get(status=True, aprobada=True, asignatura_id=asignatura5)
    for e in equivalenciaasignatura5:
        if int(e) > 0:
            if not inscripcion.recordacademico_set.filter(status=True, asignatura_id=int(e)):
                asignaturamalla = AsignaturaMalla.objects.get(asignatura_id=int(e), status=True, malla_id=id_malla)
                record1 = RecordAcademico(inscripcion=inscripcion,
                                          asignatura=asignaturamalla.asignatura,
                                          nota=record.nota,
                                          asistencia=record.asistencia,
                                          fecha=datetime.now().date(),
                                          convalidacion=False,
                                          aprobada=True,
                                          pendiente=False,
                                          creditos=asignaturamalla.creditos,  # preguntar
                                          horas=asignaturamalla.horas,  # preguntar
                                          homologada=False,
                                          valida=True,
                                          observaciones="PROCESO ADMINISTRACION 2019 A 40 MATERIAS - "+record.asignatura.nombre)
                record1.save()
                record1.actualizar()

