#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from django.db import transaction
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *
from Moodle_Funciones import crearhtmlphpmoodle, crearhtmlphpmoodleadmision

for materia in Materia.objects.filter(actualizarhtml=True, status=True, modelotarjeta=True, nivel__periodo_id=336, asignaturamalla__malla__carrera__coordinacion__id__in=[1, 2, 3, 4, 5]):
    #print("%s" % materia)
    crearhtmlphpmoodle(materia)

for materia in Materia.objects.filter(actualizarhtml=True,status=True,  nivel__periodo_id=336, asignaturamalla__malla__carrera__coordinacion__id=9):
    print("%s" % materia)
    crearhtmlphpmoodleadmision(materia)

# materia = Materia.objects.get(pk=35023)
# print("%s" % materia)
# crearhtmlphpmoodleadmision(materia)

