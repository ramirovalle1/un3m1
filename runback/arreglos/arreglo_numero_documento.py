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
from sga.funciones import generar_codigo
from sga.models import *
from sagest.models import *
# from balcon.models import *
from moodle import moodle
print(u"Inicio")
PREFIX = 'UNEMI'
SUFFIX = 'VICEVIN-PPP'
c=0
for d in  DatosEmpresaPreInscripcionPracticasPP.objects.filter(fecha_creacion__year=2022):
    c+=1
    codsolicitud = generar_codigo(d.numerodocumento, PREFIX, SUFFIX)
    d.codigodocumento = codsolicitud
    d.save()
    print(c)

print("FIN")
