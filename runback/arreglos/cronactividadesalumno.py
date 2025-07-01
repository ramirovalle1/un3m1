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


from datetime import datetime
from django.db import transaction
from django.db.models import Q
# Full path and name to your csv file
from sga.models import Matricula, Periodo

periodo=Periodo.objects.get(pk=82)
@transaction.atomic()
def migrar():
    cont=1
    # for matricula in Matricula.objects.filter(status=True, nivel__periodo=periodo, inscripcion__carrera__coordinacion__id=9, inscripcion__carrera__modalidad__in=[1,2]).distinct().order_by('inscripcion__carrera'):
    for matricula in Matricula.objects.filter(status=True, nivel__periodo=periodo, inscripcion__carrera__id__in=[133, 134, 129, 127, 135, 131, 130, 126, 128, 132]).distinct().order_by('inscripcion__carrera'):
        try:
            matricula.migrar_gestion_moodle(periodo)
            print(" %s Se guardaron datos de : %s" % (cont , matricula.inscripcion.persona.nombre_completo_inverso() + " - " + str(matricula.inscripcion.carrera) + " \r"))
            cont+=1
        except Exception as ex:
            pass

print("Importando datos: " + datetime.now().__str__() + "\r")

migrar()

print("HECHO: " + datetime.now().__str__())

