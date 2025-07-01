from django.core.cache import cache
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.evento import PeriodoEventoSerializer
from even.models import PeriodoEvento
from sga.models import PerfilUsuario
from sga.templatetags.sga_extras import encrypt


class PanelEventoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        action = ''
        try:
            if 'action' in request.data:
                action = request.data.get('action')

            if action == 'aceptarrechazarbeca':
                try:
                    aData = {}
                    return Helper_Response(isSuccess=True, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, message=ex.__str__(), status=status.HTTP_200_OK)
            else:
                try:
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    ePersona = ePerfilUsuario.inscripcion.persona
                    if not 'id' in payload['periodo']:
                        raise NameError(u'No existe periodo seleccionado.')

                    ePeriodoEventoDisponibleSinConfirmarEnCache = cache.get(f"periodoevento_disponible_sinconfirmar_persona_id{encrypt(ePersona.id)}")
                    if not ePeriodoEventoDisponibleSinConfirmarEnCache is None:
                        ePeriodoEventoDisponibleSinConfirmar = ePeriodoEventoDisponibleSinConfirmarEnCache
                    else:
                        filtrogeneral = Q(status=True,
                                          tipoperfil=1,
                                          publicar=True,
                                          cerrado=False)
                        ePeriodoEventoSinConfirmar = PeriodoEvento.objects.filter(filtrogeneral & Q(registroevento__estado_confirmacion=0,
                                                                                                    registroevento__participante_id=ePersona.id,
                                                                                                    registroevento__status=True)).distinct()

                        if ePeriodoEventoSinConfirmar.values_list('id', flat=True).exists():
                            ePeriodoEventoDisponibleSinConfirmar = ePeriodoEventoSinConfirmar.order_by('fecha_creacion').first()
                        else:
                            ePeriodoEventoDisponibleSinConfirmar = PeriodoEvento.objects.filter(filtrogeneral & ~Q(registroevento__participante_id=ePersona.id) & Q(Q(todos=True) |
                                                                                                                 Q(detalleperiodoevento__canton=ePersona.canton))).distinct().first()

                        if ePeriodoEventoDisponibleSinConfirmar is not None:
                            cache.set(f"periodoevento_disponible_sinconfirmar_persona_id{encrypt(ePersona.id)}", ePeriodoEventoDisponibleSinConfirmar, TIEMPO_ENCACHE)
                        else:
                            cache.set(f"periodoevento_disponible_sinconfirmar_persona_id{encrypt(ePersona.id)}", {}, TIEMPO_ENCACHE)

                    ePeriodoEventoDisponibleSinConfirmarseriaserializer = {}
                    if ePeriodoEventoDisponibleSinConfirmar:
                        ePeriodoEventoDisponibleSinConfirmarseriaserializer = PeriodoEventoSerializer(ePeriodoEventoDisponibleSinConfirmar, context={'participante_id': ePersona.id}).data
                    aData = {
                        'ePeriodoEventoDisponibleSinConfirmar': ePeriodoEventoDisponibleSinConfirmarseriaserializer
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, message=ex.__str__(), status=status.HTTP_200_OK)

        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=ex.__str__(), status=status.HTTP_200_OK)