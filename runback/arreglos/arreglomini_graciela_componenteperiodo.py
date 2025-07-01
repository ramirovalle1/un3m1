import os
import sys
import time

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))

SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
print(u"Inicio")

from sga.models import EvaluacionComponentePeriodo
from django.db import transaction

componente = EvaluacionComponentePeriodo.objects.filter(status=True, periodo_id=153)

for comp in componente:
    aux = EvaluacionComponentePeriodo(periodo_id=177,componente= comp.componente, parcial= comp.parcial, cantidad=comp.cantidad)
    aux.save()