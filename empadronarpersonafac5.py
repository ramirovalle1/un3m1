# coding=utf-8
#!/usr/bin/env python

import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from datetime import datetime, timedelta
from django.db import transaction
from sga.models import Materia, Clase, Leccion, LeccionGrupo, AsistenciaLeccion
from sga.funciones import variable_valor
from django.db import transaction
from django.db.models import Q, Case, When, Value, CharField
from sga.models import *
from sagest.models import Rubro
from voto.models import *
import xlrd


def empadronarFacultad(coordinacionid):
    try:
        sede_por_defecto = SedesElectoralesPeriodo.objects.get(pk=12)
        evento = CabPadronElectoral.objects.get(pk=3, status=True)
        empadronadosperiodo = DetPersonaPadronElectoral.objects.filter(status=True, cab=evento).values_list('persona_id', flat=True)
        total = 0
        fechaactual = datetime.now()
        coordinacion = Coordinacion.objects.get(pk=coordinacionid)
        print('EMPADRONAR {}'.format(coordinacion.alias))
        # condeudapersonas = Rubro.objects.filter(matricula__isnull=False, matricula__inscripcion__coordinacion=coordinacion, matricula__nivel__periodo=evento.periodo, matricula__nivelmalla__in=[3, 4, 5, 6, 7, 8, 9, 10], matricula__cerrada=False, status=True, cancelado=False, fechavence__lt=fechaactual).distinct('persona').values_list('persona__id', flat=True)
        matricula = Matricula.objects.select_related('inscripcion').filter(inscripcion__coordinacion=coordinacion, status=True, nivel__periodo=evento.periodo, nivelmalla__in=[3, 4, 5, 6, 7, 8, 9, 10], retiradomatricula=False, bloqueomatricula=False)
        lista_persona_excluidas = list(empadronadosperiodo)
        # lista_persona_excluidas = list(empadronadosperiodo) + list(condeudapersonas)
        sindeudapersonas = matricula.exclude(inscripcion__persona__in=(list(lista_persona_excluidas))).order_by('nivelmalla')
        print('TOTAL MATRICULADOS: {}'.format(matricula.count()))
        # print('TOTAL CON DEUDA: {}'.format(condeudapersonas.count()))
        print('TOTAL A EMPADRONAR: {}'.format(sindeudapersonas.count()))
        totalcargado = 0
        for per in sindeudapersonas:
            if not DetPersonaPadronElectoral.objects.filter(status=True, cab=evento, persona=per.inscripcion.persona).exists():
                # print('{} Carrera: {} Nivel: {}'.format(per.inscripcion.persona.__str__(), per.inscripcion.carrera, per.nivelmalla))
                padron = DetPersonaPadronElectoral(cab=evento, persona=per.inscripcion.persona, inscripcion=per.inscripcion, matricula=per, tipo=1)
                # lugarsede = PersonasSede.objects.filter(persona=per.inscripcion.persona).first()
                # if lugarsede:
                #     padron.lugarsede = lugarsede.sede
                # else:
                padron.lugarsede = sede_por_defecto
                padron.save()
                totalcargado += 1
        print('{} TOTAL EMPADRONADO: {}'.format(coordinacion.alias, totalcargado))
    except Exception as ex:
        print(ex)


empadronarFacultad(5)