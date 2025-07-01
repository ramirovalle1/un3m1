#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import random

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

from sga.models import MateriaAsignada

try:
    materiasasig = MateriaAsignada.objects.filter(status=True, matricula__nivel__periodo_id=177,
                                                  matricula__inscripcion__coordinacion_id__in =[1,2,3,4,5]).exclude(materia__inglesepunemi=True)

    for materia in materiasasig:
        materia.visiblehorarioexamen = False
        materia.save()
        print(materia.matricula.inscripcion, materia.visiblehorarioexamen)

except Exception as ex:
    print(ex)

# from sga.models import Persona, HistorialPersonaPPL, Inscripcion, Matricula
#
#
# try:
#     personas = None
#     historial = None
#
#     #personas = Persona.objects.filter(status = True).exclude(ppl=True)
#     matriculas = Matricula.objects.filter(status=True, nivel_id__in=[1481,1482])
#     historiales = HistorialPersonaPPL.objects.filter(persona__id__in=matriculas.values_list('inscripcion__persona__id', flat=True))
#     c= 0
#     personas_act = []
#
#     # if DEBUG:
#     #     matriculas[:50000]
#
#     for histo in historiales:
#         person = histo.persona
#         # if HistorialPersonaPPL.objects.filter(persona=person).exists():
#         # histo = HistorialPersonaPPL.objects.filter(persona=person).last()
#         histo.save()
#         # print(person, 'es PPl', person.ppl )
#         c+=1
#         personas_act.append(person)
#         per = histo.persona
#         if per.ppl:
#             print(f"Es ppl")
#         else:
#             print(f"No es ppl")
#         # else:
#         #     print('NO PPL')
#
#     print('Total de personas ppl actualizadas ', c, personas_act)
#
# except Exception as ex:
#     print(ex)