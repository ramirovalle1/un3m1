#!/usr/bin/env python
import os
import sys
import calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time as ET
from decimal import Decimal

from django.db.models import Sum, Q, F

from settings import SITE_STORAGE

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

from sga.models import SolicitudPagoBecaDetalle, Periodo, \
    miinstitucion, CUENTAS_CORREOS
from sga.funciones import cuenta_email_disponible_para_envio
from sga.tasks import send_html_mail


def notificar_becas_pendientes_pago_acreditacion_tesoreria():
    # Consulto los periodos que tengan solicitudes de pago de becas
    periodos = Periodo.objects.filter(status=True, solicitudpagobeca__status=True).distinct().order_by('id')
    notificar = False
    detalles = []

    # Verifico por periodo los detalles de solicitudes de pago
    for periodo in periodos:
        print(periodo)
        # Obtengo los detalles de las solicitudes de pagos
        becas = SolicitudPagoBecaDetalle.objects.filter(status=True, solicitudpago__periodo=periodo, solicitudpago__status=True)
        totalbecas = becas.count()
        totalpagado = becas.filter(pagado=True).count()
        totalxpagar = becas.filter(pagado=False).count()
        totalacreditado = becas.filter(pagado=True, acreditado=True).count()
        totalxacreditar = becas.filter(pagado=True, acreditado=False).count()

        print("Total de becas", totalbecas)
        print("Total pagadas", totalpagado)
        print("Total pendiente de pago", totalxpagar)
        print("Total acreditadas", totalacreditado)
        print("Total pendientes de acreditar", totalxacreditar)

        notificar = totalxpagar > 0 or totalxacreditar > 0

        if totalxpagar > 0 or totalxacreditar > 0:
            detalles.append([periodo.nombre, totalbecas, totalpagado, totalxpagar, totalacreditado, totalxacreditar])

    # Si existen becas por pagar o por acreditar se debe notificar a tesorería por e-mail
    if notificar:
        listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, etc # De donde sale el correo

        lista_email_envio = []
        lista_email_cco = []
        lista_adjuntos = []

        # lista_email_cco.append('isaltosm@unemi.edu.ec')
        lista_email_envio.append('tesoreria@unemi.edu.ec')
        # lista_email_envio.append('ivan_saltos_medina@hotmail.com')

        fechaenvio = datetime.now().date()
        horaenvio = datetime.now().time()
        cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

        tituloemail = "Novedades Pagos/Acreditaciones de Becas"
        tiponotificacion = "BECASXPAGARYACREDITAR"

        send_html_mail(tituloemail,
                       "emails/notificacion_becas_pregrado.html",
                       {'sistema': u'SGA-UNEMI',
                        'fecha': fechaenvio,
                        'hora': horaenvio,
                        'tiponotificacion': tiponotificacion,
                        'detalles': detalles,
                        't': miinstitucion()
                        },
                       lista_email_envio,
                       lista_email_cco,
                       lista_adjuntos,
                       cuenta=CUENTAS_CORREOS[cuenta][1]
                       )

        # Temporizador para evitar que se bloquee el servicio de gmail
        print("Enviando notificación por e-mail.....")
        # ET.sleep(3)


        print("Notificaciones finalizadas...")
    else:
        print("No existen becas pendientes de pago o acreditación")


notificar_becas_pendientes_pago_acreditacion_tesoreria()
