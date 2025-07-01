#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.http import HttpResponse

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

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

from datetime import datetime
from sga.funciones import log
from sagest.models import ActivoFijo, ActivoTecnologico, ActivoFijoInventarioTecnologico


inventariotics = ActivoFijoInventarioTecnologico.objects.filter(status=True)

for inventario in inventariotics:
    activotecnologico = ActivoTecnologico.objects.filter(status=True, activotecnologico_id=inventario.activo_id)
    if activotecnologico:
        inventario.activotecnologico_id = activotecnologico[0].id
        inventario.save()
        print("Activo tecnológico" + str(activotecnologico[0].__str__()))
