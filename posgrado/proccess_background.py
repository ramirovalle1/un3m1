import threading
from sga.models import *
from settings import DEBUG


class notificar_responder_encuesta_sede_graduacion_posgrado(threading.Thread):
    def __init__(self, request, eInscripcionEncuestaTitulacionPosgrado):
        self.request = request
        self.eInscripcionEncuestaTitulacionPosgrado = eInscripcionEncuestaTitulacionPosgrado
        threading.Thread.__init__(self)

    def run(self):
        try:
            print("start process notification eleccion de sede de graduacion posgrado")
            request, eInscripcionEncuestaTitulacionPosgrado = self.request, self.eInscripcionEncuestaTitulacionPosgrado

            titulonotificacion = f"Participar en la ceremonia de mi graduación."
            cuerponotificacion = f"Ingrese o de clic en la url para ingresar al módulo de proceso de titulación posgrado y seleccionar si desea participar en la ceremonia de su graduación selecionandola sede y jornada a asistir."

            for integrante in eInscripcionEncuestaTitulacionPosgrado:
                ePersona = integrante.inscripcion.persona
                ePerfilUsuario = PerfilUsuario.objects.filter(status=True, persona=ePersona, inscripcion=integrante.inscripcion)
                if ePerfilUsuario.exists():
                    cuerponotificacion = f"Participar en ceremonia de mi graduación."
                    url = f"/alu_tematitulacionposgrado"
                    notificacion = Notificacion(
                        titulo=titulonotificacion,
                        cuerpo=cuerponotificacion,
                        destinatario=ePersona,
                        url=url,
                        content_type=None,
                        object_id=None,
                        prioridad=1,
                        perfil=ePerfilUsuario.first(),
                        app_label='SIE',
                        fecha_hora_visible=datetime.now() + timedelta(days=4))
                    notificacion.save(request)
            print("End proccess notification encuesta sede graduacion")
        except Exception as ex:
            pass
