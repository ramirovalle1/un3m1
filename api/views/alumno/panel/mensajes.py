from datetime import datetime

from django.db.models import Max, Min
from django.forms import model_to_dict
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from sga.models import PerfilUsuario, InscripcionesPeriodoActulizacionHojaVida, PeriodoActulizacionHojaVida
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class MessagesAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)

            eInscripcion = ePerfilUsuario.inscripcion
            eDataMessages = []
            if cache.has_key(f"periodoactulizacioneshojavida_inscripcion_id{encrypt(eInscripcion.id)}_mensajes"):
                eDataMessages = cache.get(f"periodoactulizacioneshojavida_inscripcion_id{encrypt(eInscripcion.id)}_mensajes")
            else:
                fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
                tiempo_transcurrido = fin - ahora
                tiempo_transcurrido = int(tiempo_transcurrido.total_seconds())
                eInscripcionesPeriodoActulizacionHojaVidas = eInscripcion.inscripcionesperiodoactulizacionhojavida_set.filter(status=True,
                                                                                                                              periodoactualizacion__fechainicio__lte=ahora,
                                                                                                                              periodoactualizacion__estado=1,
                                                                                                                              periodoactualizacion__fechafin__gte=ahora).distinct()
                eInscripcionesPeriodoActulizacionHojaVidas = eInscripcionesPeriodoActulizacionHojaVidas.exclude(estado=0, status=True)[:1]
                ePeriodoActulizacionHojaVidas = PeriodoActulizacionHojaVida.objects.filter(status=True, pk__in=eInscripcionesPeriodoActulizacionHojaVidas.values_list("periodoactualizacion__id", flat=True)).distinct()
                if ePeriodoActulizacionHojaVidas.values("id").exists():
                    fechainicio = ePeriodoActulizacionHojaVidas.aggregate(fechainicio=Min('fechainicio'))['fechainicio']
                    fechafin = ePeriodoActulizacionHojaVidas.aggregate(fechafin=Max('fechafin'))['fechafin']
                    inicio = datetime(fechainicio.year, fechainicio.month, fechainicio.day, 0, 0, 1)
                    fin = datetime(fechafin.year, fechafin.month, fechafin.day, 23, 59, 59)
                    tiempo_transcurrido = fin - inicio
                    tiempo_transcurrido = int(tiempo_transcurrido.total_seconds())
                for eInscripcionesPeriodoActulizacionHojaVida in eInscripcionesPeriodoActulizacionHojaVidas:
                    eInscripcion = eInscripcionesPeriodoActulizacionHojaVida.inscripcion
                    ePersona = eInscripcion.persona
                    if eInscripcionesPeriodoActulizacionHojaVida.estado == 2:
                        type = 'info'
                        body = f"{'Estimada' if ePersona.es_mujer() else 'Estimado'} {'aspirante' if eInscripcion.coordinacion_id == 9 else 'estudiante'}, la Universidad Estatal de Milagro, a través de la Dirección de Bienestar Universitario, se encuentra realizando la actualización de la información que reposa en el módulo “Hoja de vida”, te invitamos a completar tus datos y ser parte de esta campaña."
                        icon = f"""<svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="24"
                                height="24"
                                fill="currentColor"
                                class="bi bi-info-circle-fill me-2"
                                viewBox="0 0 16 16"
                        >
                            <path
                                    d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"
                            />"""
                    else:
                        type = 'danger'
                        body = f"{'Estimada' if ePersona.es_mujer() else 'Estimado'} {'aspirante' if eInscripcion.coordinacion_id == 9 else 'estudiante'}, se rechazó la actualización de su hoja de vida por los siguientes motivos: {eInscripcionesPeriodoActulizacionHojaVida.observacionrechazo}"
                        icon = f"""<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-exclamation-circle-fill" viewBox="0 0 16 16">
                                                <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM8 4a.905.905 0 0 0-.9.995l.35 3.507a.552.552 0 0 0 1.1 0l.35-3.507A.905.905 0 0 0 8 4zm.002 6a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>
                                            </svg>"""
                    eDataMessages.append({'title': 'Campaña de Actualización de Hoja de Vida.',
                                          'body': body,
                                          'type': type,
                                          'icon': icon})
                cache.set(f"periodoactulizacioneshojavida_inscripcion_id{encrypt(eInscripcion.id)}_mensajes", eDataMessages, tiempo_transcurrido)
            data = {
                'eDataMessages': eDataMessages,
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
