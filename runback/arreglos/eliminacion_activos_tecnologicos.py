#!/usr/bin/env python

import os
import sys
import time


SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from sagest.models import *

try:
    listacatalogo = CatalogoBien.objects.filter(clasificado=False).values_list('id')
    listaactivostecnologicos = ActivoTecnologico.objects.filter(status=True, activotecnologico__catalogo_id__in=listacatalogo)
    for activo in listaactivostecnologicos:
        activo.status = False
        activo.save()
        print("Se elimino el activo " + str(activo))

except Exception as ex:
    print('error: %s' % ex)