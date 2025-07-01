# coding=utf-8
#!/usr/bin/env python

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
from datetime import datetime, timedelta
from django.db import transaction
from sga.models import Materia, Clase, Leccion, LeccionGrupo, AsistenciaLeccion
from sga.funciones import variable_valor
from sga.models import *
try:
    qs =GEDCRespuestas.objects.select_related('cab').filter(respcalificacion__isnull=False)
    print('Registros a procesar: {}'.format(qs.count()))
    count = 0
    for q in qs:
        print('{}: {}'.format(q.pregunta.indicador.indicador, q.respcalificacion))
        q.save()
        count += 1
    print('Total de respuestas procesadas: {}'.format(count))
except Exception as ex:
    print(ex)
