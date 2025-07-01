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
from sga.models import *
from sagest.models import *

@transaction.atomic()
def anular_solicitudes():
    try:
        solicitudes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2, estado=1).order_by('-fecha_creacion','administrativo__persona__apellido1')
        for solicitud in solicitudes.filter(estado=1):
            dias = (datetime.now() - solicitud.fecha_creacion).days
            if dias > 2:
                recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=solicitud,
                                                                 observacion='ANULACIÓN AUTOMÁTICA POR NO VALIDARSE EN EL PLAZO ESTABLECIDO',
                                                                 estado=20,
                                                                 fecha=datetime.now().date(),
                                                                 persona_id=1)
                recorridocap.save()
                solicitud.estado = 20
                solicitud.usuario_modificacion_id = 1
                solicitud.save()

                fechasolicitud = str(solicitud.fecha_creacion)[:10]
                fechasolicitud = fechasolicitud[8:] + "-" + fechasolicitud[5:7] + "-" + fechasolicitud[0:4]
                fechaanulacion = str(recorridocap.fecha)[:10]
                fechaanulacion = fechaanulacion[8:] + "-" + fechaanulacion[5:7] + "-" + fechaanulacion[0:4]
                tituloemail = "Solicitud de Capacitación ANULADA automáticamente"
                observacion = "Su Director no VALIDÓ la solicitud en el plazo establecido de 2 días."
                textoadicional = "Fecha de solicitud: " + fechasolicitud + "\n"
                textoadicional = textoadicional + "Fecha anulación: " + fechaanulacion + "\n"
                textoadicional = textoadicional + "Días transcurridos: " + str(dias)
                send_html_mail(tituloemail,
                               "emails/aprobacion_capadmtra.html",
                               {'sistema': u'SAGEST - UNEMI',
                                'administrativo': solicitud.administrativo.persona,
                                'numero': solicitud.id,
                                'estadoap': 20,
                                'observacionap': observacion,
                                'aprueba': 'el sistema',
                                'textoadicional': textoadicional,
                                'fecha': datetime.now().date(),
                                'hora': datetime.now().time(),
                                't': miinstitucion()},
                               solicitud.administrativo.persona.lista_emails_envio(),
                               [],
                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                               )

                # Director del departamento - envio de e-mail
                director = solicitud.obtenerdatosautoridad('DIRDEPA', 0)
                if director:
                    send_html_mail(tituloemail,
                                   "emails/notificacion_capadmtra.html",
                                   {'sistema': u'SAGEST - UNEMI',
                                    'fase': 'ANU',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'numero': solicitud.id,
                                    'administrativo': solicitud.administrativo.persona,
                                    'autoridad1': director.responsable,
                                    'textoadicional': textoadicional,
                                    't': miinstitucion()
                                    },
                                   director.responsable.lista_emails_envio(),
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )

    except Exception as ex:
        transaction.set_rollback(True)
        print('error: %s' % ex)


anular_solicitudes()
