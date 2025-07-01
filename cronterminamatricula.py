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
from settings import PERIODO_ELIMINA_MATRICULA, HORAS_VIGENCIA
from django.contrib.auth.models import User
from sga.models import Matricula
from sagest.models import Rubro, Pago
from sga.funciones import log


@transaction.atomic()
def elimina_rubros(mat):
    eliminar = True
    rubros = Rubro.objects.filter(status=True, matricula=mat)
    if rubros.exists():
        for r in rubros:
            if Pago.objects.filter(rubro=r).exists():
                eliminar = False
    else:
        eliminar = False
    return eliminar

print("ELIMINADO MATRICULAS: " + datetime.now().__str__() + "\r")
for ma in Matricula.objects.filter(estado_matricula=1, nivel__periodo__id__in=PERIODO_ELIMINA_MATRICULA, status=True):
    fechavence = ma.fecha_creacion + timedelta(hours=HORAS_VIGENCIA)
    if datetime.now() > fechavence:
        if elimina_rubros(ma):
            ma.delete()
            log(u'Eliminación automatica de matricula CRON: %s' % ma, [], "del", user=User.objects.get(pk=1))
            print("SE ELIMINO LA MATRICULA: %s" % ma)

print("HECHO: " + datetime.now().__str__())