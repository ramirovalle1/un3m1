#!/usr/bin/env python

import os
import sys
import time

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
print(u"Inicio")

from helpdesk.models import *
from sagest import models
from django.db import transaction
from colorama import Back, init
from sga.models import RespuestaEvaluacionAcreditacion, VariablesGlobales
from sga.funciones import variable_valor


@transaction.atomic()
def eliminar_evaluacion_docente():
    with transaction.atomic():
        try:
            id_respuesta = variable_valor('ELIMINAR_EVALUACION_DOCENTE_PK')
            if id_respuesta:
                if type(id_respuesta) == int: id_respuesta = [id_respuesta]
                for model in RespuestaEvaluacionAcreditacion.objects.filter(pk__in=id_respuesta):
                    model.delete()
                    print(f'Registro <<{model}>> eliminado correctamente...')

                # vg = VariablesGlobales.objects.get(variable='ELIMINAR_EVALUACION_DOCENTE_PK')
                # vg.valor = '0'
                # vg.save()
        except Exception as ex:
            transaction.set_rollback(True)
            print('Error en la eliminación. %s ' % ex.__str__())

eliminar_evaluacion_docente()

