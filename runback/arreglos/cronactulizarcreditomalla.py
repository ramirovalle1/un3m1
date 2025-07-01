## prueba de recalcular creditos y nivel malla
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
from sga.models import Matricula,Inscripcion


def actualizar_creditos_malla():
    try:
        # matriculados = Matricula.objects.filter(status=True,
        #                                         inscripcion__carrera_id=110,
        #                                         nivel__periodo_id=126,
        #                                         retiradomatricula=False).order_by('inscripcion__carrera','inscripcion__persona')
        incripciones=Inscripcion.objects.filter(id__in=[77885,
                            77824,
                            77825,
                            77828,
                            77829,
                            77830,
                            77831,
                            85193,
                            77887,
                            77889,
                            77832,
                            77833,
                            77890,
                            77835,
                            77836,
                            77891,
                            77837,
                            77841,
                            77838,
                            85354,
                            77892,
                            77839,
                            77840,
                            77842,
                            77894,
                            77843,
                            77896,
                            104962,
                            77844,
                            77846,
                            84678,
                            85276,
                            85195,
                            77849,
                            77897,
                            85391,
                            77899,
                            77852,
                            85104,
                            77900,
                            77853,
                            77854,
                            77855,
                            85356,
                            77856,
                            84389,
                            77858,
                            85452,
                            77860,
                            77861,
                            77901,
                            77865,
                            77868,
                            85173,
                            77869,
                            77870,
                            77872,
                            77873,
                            77875,
                            77876,
                            77902,
                            85625,
                            77904,
                            84843,
                            85011,
                            77906,
                            77907,
                            103782,
                            85212,
                            77909,
                            77877,
                            77878,
                            77910,
                            77879,
                            84791,
                            85076,
                            77880,
                            77911,
                            77912,
                            85234,
                            85071,
                            77882,
                            77914,
                            84526,
                            84931,
                            77916,
                            84168,
                            77884])
        for inscripcion in incripciones:
            inscripcion.actualizar_creditos()
            inscripcion.actualizar_nivel()
            print(inscripcion)
        print(str(incripciones.count())+' Registros finalizados')
    except Exception as ex:
        pass
        print(ex)


actualizar_creditos_malla()
