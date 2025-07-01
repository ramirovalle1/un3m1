#!/usr/bin/env python

import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()


from datetime import datetime
from django.db import transaction
from django.db.models import Q
# Full path and name to your csv file
from sagest.rec_finanzas import envio_recibocaja_cliente
from sagest.models import PagoReciboCaja


@transaction.atomic()
def generarrecibo(id):
    envio_recibocaja_cliente(id)

print("Generando Recibos de Caja: " + datetime.now().__str__() + "\r")

for recibo in PagoReciboCaja.objects.values_list('id', flat=True).filter(status=True, enviadocliente=False).order_by('id'):
    print("Generando recibo ID ", recibo, "...")
    generarrecibo(recibo)

print("Proceso finalizado: " + datetime.now().__str__())