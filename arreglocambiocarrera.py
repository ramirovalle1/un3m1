import os
import sys


SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")


application = get_wsgi_application()


from sga.models import AperturaPeriodoCambioCarrera, SolicitudCambioCarrera, Notificacion, CUENTAS_CORREOS
from sga.templatetags.sga_extras import encrypt
from datetime import datetime, timedelta
from sga.tasks import send_html_mail
from sga.models import Profesor


from sga.funciones import notificacion

def corregir_cupos():
    try:
        periodo_cambio = AperturaPeriodoCambioCarrera.objects.filter(status=True).first()
        for carrera in periodo_cambio.carreras_periodo():
            cupo = carrera.cupo
            solicitudes = carrera.total_solicitudes()
            if solicitudes > cupo:
                for solicitud in carrera.solicitudes():
                    if carrera.total_solicitudes() > cupo:
                        solicitud.estados = 2
                        solicitud.aprobacion_admision = 2
                        solicitud.observacion_admision = 'Estimad@ ciudadan@ Usted no ha alcanzado cupo en la carrera solicitada. Recuerde que los cupos van siendo asignados automáticamente en el sistema en el orden de solicitud registrada.'
                        solicitud.save()
                        # notificacion de sga
                        if solicitud.inscripcion:
                            para = solicitud.inscripcion.persona
                            asunto = u"SOLICITUD DE CAMBIO DE CARRERA {}".format(solicitud.get_estados_display())
                            noti = Notificacion(cuerpo=solicitud.observacion_admision, titulo=asunto,
                                                destinatario=para,
                                                url='/alu_solicitudcambiocarrera?action=verproceso&id={}'.format(
                                                    encrypt(solicitud.pk)), prioridad=1, app_label='SGA',
                                                fecha_hora_visible=datetime.now() + timedelta(days=1),
                                                tipo=2, en_proceso=False)
                            noti.save()
                        else:
                            para = solicitud.persona

        #                     correo electronico para notificar a los estudiantes
                        subject = 'SOLICITUD DE CAMBIO DE CARRERA'
                        template = 'emails/rechazarsolicitud.html'
                        datos_email = {'sistema': 'SGA UNEMI', 'filtro': solicitud,
                                        'mensaje':"Estimad@ ciudadan@ Usted no ha alcanzado cupo en la carrera solicitada. Recuerde que los cupos van siendo asignados automáticamente en el sistema en el orden de solicitud registrada.",
                                       'url_boton': 'sga.unemi.edu.ec/alu_solicitudcambiocarrera?action=verproceso&id={}'.format(encrypt(solicitud.pk))}
                        lista_email = para.lista_emails()
                        # lista_email = ['cgomezm3@unemi.edu.ec',]
                        send_html_mail(subject, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[4][1])
    except Exception as ex:
        print(ex)

def enviar_emails():
    try:
        titulo = u"Aprobación de matrícula especial."
        lista_email = ['jguachuns@unemi.edu.ec','btomalac@unemi.edu.ec']
        datos_email = {'sistema': 'SGA',
                       'mensaje':'Su petición de matrícula especial fue aprobada ',
                       'fecha': datetime.now().date(),
                       'hora': datetime.now().time(), }
        template = "emails/notificacion_agendamientocitas.html"
        send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
        print('Se completo el envio')
    except Exception as ex:
        print(str(ex))

# enviar_emails()



