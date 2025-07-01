#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time

import openpyxl

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from inno.models import *
d = datetime.now()
try:
    for solicitud in SolicitudTutoriaIndividual.objects.filter(status=True, estado=1, fechatutoria__isnull=True,manual=True):
        if solicitud.horario.dia < d.isoweekday():
            solicitud.fechatutoria = d
            solicitud.estado = 2
            solicitud.tutoriacomienza = solicitud.horario.turno.comienza
            solicitud.tutoriatermina = solicitud.horario.turno.termina
            solicitud.save()
        elif solicitud.horario.dia == d.isoweekday():
            if solicitud.horario.turno:
                if time.localtime().tm_hour >= solicitud.horario.turno.comienza.hour and time.localtime().tm_hour <= solicitud.horario.turno.termina.hour:
                    solicitud.fechatutoria = d
                    solicitud.estado = 2
                    solicitud.tutoriacomienza = solicitud.horario.turno.comienza
                    solicitud.tutoriatermina = solicitud.horario.turno.termina
                    solicitud.save()
except Exception as ex:
    print('error: %s' % ex)
