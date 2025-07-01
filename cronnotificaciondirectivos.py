import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")


application = get_wsgi_application()

from datetime import datetime, timedelta
from sga.funciones import notificacion, notificacion2
from sga.models import SolicitudCambioCarrera, AperturaPeriodoCambioCarrera, Persona

hoy = datetime.now().date()
def periodoactual():
    return AperturaPeriodoCambioCarrera.objects.get(publico=True, status=True, fechacierre__gte=hoy, fechaapertura__lte=hoy)

def notificaciondirectivos():
    ayer=hoy-timedelta(days=1)
    apertura=periodoactual()
    if apertura:
        if hoy >= apertura.fechainicioremitirdecano:
            filtro= SolicitudCambioCarrera.objects.filter(periodocambiocarrera=apertura, status=True, estados=3)
            if filtro.exists():
                subject = 'SOLICITUDES DE CAMBIO DE CARRERA/IES-MODALIDAD PENDIENTE DE REVISIÓN'
                lista=[]
                for solicitud in filtro:
                    decano_facultad = solicitud.get_decano()
                    lista.append(decano_facultad.persona.id)
                    lista = list(set(lista))
                for id in lista:
                    decano_facultad=Persona.objects.get(pk=id)
                    cont=0
                    for soli in filtro:
                        if soli.get_decano().persona.id == decano_facultad.id:
                            cont+=1
                    print(decano_facultad.__str__() +" "+ cont.__str__())
                    asuntodecano = 'Estimado(a) Decano(a) Saludos cordiales, tiene {} solicitudes de cambio de carrera para su revisión'.format(cont.__str__())
                    notificacion2(subject, asuntodecano,decano_facultad, None,
                                 '/alu_cambiocarrera?action=solicitantes&id={}&estsolicitud={}'.format(apertura.id.__str__(),'3'), apertura.pk, 1,
                                 'sga', AperturaPeriodoCambioCarrera)
                print('Notificacion enviada')

        # if hoy >= apertura.fechainiciovaldirector:
        #     filtro = SolicitudCambioCarrera.objects.filter(periodocambiocarrera=apertura, status=True, estados=7)
        #     if filtro:
        #         subject = 'SOLICITUDES DE CAMBIO DE CARRERA/IES-MODALIDAD PENDIENTE DE REVISIÓN'
        #         asuntodirector = 'Estimado(a) Director(a) Saludos cordiales, tiene {} solicitudes de cambio de carrera para su revisión'.format(
        #             len(filtro).__str__())
        #         director_facultad = filtro.last().get_director()
        #         notificacion2(subject, asuntodirector, director_facultad.persona, None,
        #                      '/alu_cambiocarrera?action=solicitantes&id={}&estsolicitud={}'.format(apertura.id.__str__(),'7'), filtro.last().pk, 1,
        #                      'sga', SolicitudCambioCarrera)
        #         print('envia notificacion a director de carrera')

print('Inicia orden de envio de notificacion.............')
notificaciondirectivos()