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
from sagest.models import *
from bd.models import PeriodoCrontab


def actualizar_estado_matricula(periodo):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de actualizar estado de matricula a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {periodo}")
    matriculas = Matricula.objects.filter(status=True, cerrada=False, nivel__periodo=periodo)
    if DEBUG:
        matriculas = matriculas.filter(inscripcion_id=104493)
    total = matriculas.count()
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(u"** Total: %s" % total)
    print(u"****************************************************************************************************")
    count = 1
    for matricula in matriculas:
        print(u"*** %s de %s" % (count, total))
        with transaction.atomic():
            try:
                print(u"*** Matricula (ID: %s - %s)" % (matricula.id, matricula))
                matricula.actualiza_matricula()
                print(u"*** Estado de matricula actualizado Matricula (ID: %s)" % matricula.id)
            except Exception as ex:
                print(u"*** Estado de matricula no actualizado Matricula (ID: %s)" % matricula.id)
                print(u"*** Error" % ex.__str__())
                transaction.set_rollback(True)
        count += 1
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de actualizar estado de matricula del periodo {periodo}")


def actualizar_nivel_inscripcion(periodo):
    def run(eInscripcion):
        eInscripcion.actualizar_creditos()
        eInscripcion.actualizar_niveles_records()
        eInscripcion.actualizar_nivel(isCron=True)
        eInscripcion.save()
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de actualizar nivel de inscripción a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {periodo}")
    inscripciones = Inscripcion.objects.filter(matricula__nivel__periodo_id=periodo, matricula__retiradomatricula=False, matricula__status=True)
    if DEBUG:
        inscripciones = inscripciones.filter(pk=104493)
    graduados = Graduado.objects.filter(inscripcion_id__in=inscripciones.values_list("id", flat=True).distinct())
    egresados = Egresado.objects.filter(inscripcion_id__in=inscripciones.values_list("id", flat=True).distinct())
    inscripciones = inscripciones.exclude(id__in=graduados.values_list("inscripcion_id", flat=True).distinct())
    inscripciones = inscripciones.exclude(id__in=egresados.values_list("inscripcion_id", flat=True).distinct())
    total = inscripciones.count()
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(u"** Total: %s" % total)
    print(u"****************************************************************************************************")
    count = 1
    for inscripcion in inscripciones:
        eInscripcionNivel = inscripcion.mi_nivel()
        if eInscripcionNivel.fecha_modificacion:
            if eInscripcionNivel.fecha_modificacion_cron is None:
                run(inscripcion)
                print(f"Se actualizo estados del estudiante: {inscripcion.__str__()}")
            elif eInscripcionNivel.fecha_modificacion > eInscripcionNivel.fecha_modificacion_cron:
                run(inscripcion)
                print(f"Se actualizo estados del estudiante: {inscripcion.__str__()}")
        # print(inscripcion.id)
        print(u"*** %s de %s" % (count, total))
        count += 1
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de actualizar nivel de inscripción del periodo {periodo}")


def actualizar_nivel_matricula(periodo):
    print(u"****************************************************************************************************")
    print(f"Inicia proceso de actualizar nivel de matricula a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {periodo}")
    matriculas = Matricula.objects.filter(nivel__periodo_id=periodo, retiradomatricula=False, status=True)
    if DEBUG:
        matriculas = matriculas.filter(inscripcion_id=104493)
    total = matriculas.count()
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(u"** Total: %s" % total)
    print(u"****************************************************************************************************")
    count = 1
    for matricula in matriculas:
        matricula.calcula_nivel()
        print(matricula)
        print(u"*** %s de %s" % (count, total))
        count += 1
    print(u"****************************************************************************************************")
    print(u"****************************************************************************************************")
    print(f"** Finaliza proceso de actualizar nivel de matricula del periodo {periodo}")


print(u"INICIO DEL PROCESO A CONSULTAR PERIODOS CRONTAB")
if PeriodoCrontab.objects.filter(status=True, is_activo=True):
    for ePeriodoCrontab in PeriodoCrontab.objects.filter(status=True, is_activo=True):
        # ACTUALIZAR ESTADO DE MATRICULA
        if ePeriodoCrontab.upgrade_state_enrollment:
            actualizar_estado_matricula(ePeriodoCrontab.periodo)
        # ACTUALIZAR NIVEL DE MATRICULA
        if ePeriodoCrontab.upgrade_level_enrollment:
            actualizar_nivel_matricula(ePeriodoCrontab.periodo)
        # ACTUALIZAR NIVEL DE INSCRIPCION
        if ePeriodoCrontab.upgrade_level_inscription:
            actualizar_nivel_inscripcion(ePeriodoCrontab.periodo)
else:
    print(u"FIN DEL PROCESO A CONSULTAR PERIODOS CRONTAB -> NO SE ENCONTRO PERIODOS")
