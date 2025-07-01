import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")


application = get_wsgi_application()

from poli.models import ReservacionPersonaPoli
from datetime import datetime, timedelta


def finalizar_reservas():
    try:
        hoy=datetime.now().date()
        reservaspersona = ReservacionPersonaPoli.objects.filter(status=True, finicialreserva__lte=hoy, estado=2)
        print('Inicia proceso de finalización')
        for reserva in reservaspersona:
            reserva.estado=4
            reserva.save()
        print('Cantidad de reservas finalizadas: {}'.format(len(reservaspersona)))
    except Exception as ex:
        print(ex)

finalizar_reservas()


