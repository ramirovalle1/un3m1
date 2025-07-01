# coding=utf-8
import json
from datetime import datetime

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.hojadevida import HojaVidaPersonaSerializer
from sga.funciones import variable_valor, log
from sga.models import Inscripcion, Persona, PerfilUsuario
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class ActualizaDatoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        try:
            ahora = datetime.now()
            fecha_fin_cache = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
            tiempo_cache = fecha_fin_cache - ahora
            TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
            payload = request.auth.payload
            eInscripcionEnCache = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
            if eInscripcionEnCache:
                eInscripcion = eInscripcionEnCache
            else:
                if not Inscripcion.objects.db_manager("sga_select").values("id").filter(pk=encrypt(payload['inscripcion']['id'])).exists():
                    raise NameError(u"Inscripción no válida")
                eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=encrypt(payload['inscripcion']['id']))
                cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
            ePersona = eInscripcion.persona
            data = {}
            if variable_valor('VER_MODAL_DATOS_DOMICILIO'):
                if not cache.has_key(f"data_actualiza_datos_ubicacion_id_{encrypt(ePersona.pk)}_serializer_ubicacion"):
                    eCoordinacion = eInscripcion.carrera.coordinacion_set.all()[0]
                    ver_modal = False
                    persona_serializer = HojaVidaPersonaSerializer(ePersona)
                    if eCoordinacion.pk in [1, 2, 3, 4, 5]:
                        if ePersona.localizacionactualizada == False:
                            ver_modal = True
                    data = {
                        'ver_modal': ver_modal,
                        'ePersona': persona_serializer.data,

                    }
                    cache.set(f"data_actualiza_datos_ubicacion_id_{encrypt(ePersona.pk)}_serializer_ubicacion", data, TIEMPO_ENCACHE)
                else:
                    data = cache.get(f"data_actualiza_datos_ubicacion_id_{encrypt(ePersona.pk)}_serializer_ubicacion")

            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

class SaveActualizaDatosAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        TIEMPO_ENCACHE = 60 * 60 * 60
        with transaction.atomic():
            try:
                hoy = datetime.now()
                payload = request.auth.payload
                ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                if not ePerfilUsuario.es_estudiante():
                    raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                action = None
                ePersona = ePerfilUsuario.persona
                ePersona.pais_id = int(eRequest['pais'])
                if ePersona.pais_id == 1:
                    ePersona.provincia_id = int(eRequest['provincia'])
                    ePersona.canton_id = int(eRequest['canton'])
                    if 'parroquia' in eRequest:
                        ePersona.parroquia_id = int(eRequest['parroquia'])
                    else:
                        ePersona.parroquia = None
                else:
                    if 'provincia' in eRequest:
                        ePersona.provincia_id = int(eRequest['provincia'])
                    else:
                        ePersona.provincia = None
                    if 'canton' in eRequest:
                        ePersona.canton_id = int(eRequest['canton'])
                    else:
                        ePersona.canton = None
                    if 'parroquia' in eRequest:
                        ePersona.parroquia_id = int(eRequest['parroquia'])
                    else:
                        ePersona.parroquia = None

                ePersona.direccion = eRequest['direccion']
                ePersona.direccion2 = eRequest['direccion2']
                # ePersona.ciudadela = eRequest['eCiudadela']
                ePersona.num_direccion = eRequest['num_direccion']
                ePersona.referencia = eRequest['referencia']
                ePersona.sector = eRequest['sector']
                ePersona.telefono = eRequest['telefono']
                ePersona.zona = int(eRequest['sectorlugar'])
                ePersona.localizacionactualizada =True
                ePersona.save()
                log(u"Editó datos de domicilio: %s" % ePersona, request, "edit")

                return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
            except Exception as ex:
                transaction.set_rollback(True)
                return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
