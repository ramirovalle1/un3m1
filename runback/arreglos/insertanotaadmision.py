#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import openpyxl
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
print(u"Inicio")
try:
    miarchivo = openpyxl.load_workbook("NOTAS_ADMISION.xlsx")
    lista = miarchivo.get_sheet_by_name('TODOS')
    totallista = lista.rows
    a=0
    for filas in totallista:
        a += 1
        if a > 2:
            cedula = filas[0].value
            nota = filas[1].value
            carrera_nombre = filas[2].value
            datospersona=None
            if Persona.objects.filter(cedula=cedula).exists():
                datospersona = Persona.objects.get(cedula=cedula)
            if Persona.objects.filter(pasaporte=cedula).exists():
                datospersona = Persona.objects.get(pasaporte=cedula)
            if datospersona:
                if Carrera.objects.values('id').filter(status=True,nombre__icontains=carrera_nombre).exists():
                    for carrera in Carrera.objects.filter(status=True,activa=True, nombre__icontains=carrera_nombre):
                        if Inscripcion.objects.values('').filter(status=True,carrera=carrera,activo=True).exists():
                            inscripcion=Inscripcion.objects.filter(status=True,carrera=carrera,activo=True)[0]
                            if PerfilUsuario.objects.values('id').filter(status=True,inscripcion=inscripcion,visible=True).exists():
                                perfil=PerfilUsuario.objects.values('id').filter(status=True, inscripcion=inscripcion,visible=True)[0]
                                inscripcion.puntajesenescyt=nota
                                inscripcion.save()
                                print('Registro actualizado: %s (%s)' %(inscripcion,nota))
except Exception as ex:
        print('error: %s' % ex)



