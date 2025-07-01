#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.db import transaction

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


try:
    with transaction.atomic():
        practicas = DetallePreInscripcionPracticasPP.objects.values('preinscripcion_id', 'itinerariomalla_id', 'inscripcion_id').filter(status=True, preinscripcion_id=11).annotate(cantidad=Count('inscripcion_id'))
        for a in practicas:
            print("Inicio de Proceso")
            if a['cantidad'] > 1:
                print('Encontrado '+str(a['cantidad'])+' registos')
                for r in range(0, int(a['cantidad'])):
                    delet = DetallePreInscripcionPracticasPP.objects.filter(status=True, preinscripcion_id=11, inscripcion_id=a['inscripcion_id'], itinerariomalla_id=a['itinerariomalla_id']).first()
                    if r == int(a['cantidad'])-1:
                        print('Registro conservado ' + str(delet)+' Estudiante:  '+str(delet.inscripcion)+' Pk: '+str(delet.pk)+'\n\n')
                    else:
                        print('Regristro eliminado ' + str(delet)+' Estudiante:   '+str(delet.inscripcion)+ 'Pk: '+str(delet.pk)+'\n\n')
                        delet.delete()
except Exception as e:
    transaction.set_rollback(True)
    print(e)
