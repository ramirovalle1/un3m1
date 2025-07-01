#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import sys

import xlsxwriter
from django.db import transaction

from settings import DEBUG

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from datetime import date
from sga.models import *


def actualizar_inscripcion():
    print(u"****************************************************************************************************")

    periodos = PeriodoInscripcionVinculacion.objects.values_list('id',flat=True).filter(status = True)
    inscripciones = ProyectoVinculacionInscripcion.objects.filter(status = True, periodo__id__in = periodos, estado = 2)
    print(inscripciones.count())
    for inscrito in inscripciones:
        participante = ParticipantesMatrices.objects.filter(status=True, proyecto = inscrito.proyectovinculacion, inscripcion = inscrito.inscripcion)
        if participante.count() > 1:
            print(participante)
        else:
            participante = ParticipantesMatrices.objects.get(status=True, proyecto = inscrito.proyectovinculacion, inscripcion = inscrito.inscripcion)
            participante.preinscripcion = inscrito
            participante.save()
    print(u"FIN DEL PROCESO DE ACTUALIZAR INSCRIPCION")


def actualizar_estado():
    print("Inicio de cambio de estado")
    participantes = ParticipantesMatrices.objects.filter(status=True)
    print(participantes.count())
    for participante in participantes:
        if participante.horas > 0:
            participante.estado = 1
        else:
            participante.estado = 0
        participante.save()

        # (0, u'EN PROCESO'),
        # (1, u'CULMINADO'),
        # (2, u'RETIRADO'),
    print(u"FIN DEL PROCESO DE CAMBIO DE ESTADO")

actualizar_inscripcion()
actualizar_estado()

print(u"FIN DEL PROCESO")
