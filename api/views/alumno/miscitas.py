# coding=utf-8
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.miscitas import ProximaCitaSerializer
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula
from med.models import ProximaCita
from sga.templatetags.sga_extras import encrypt


class MisCitasAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_MIS_CITAS'

    @api_security
    def get(self, request):
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            if not 'id' in payload['matricula']:
                raise NameError(u'No se encuentra matriculado.')
            if payload['matricula']['id'] is None:
                raise NameError(u'No se encuentra matriculado.')
            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
            eIncripcion = eMatricula.inscripcion
            ePersona = eIncripcion.persona
            proxima_cita = ProximaCita.objects.filter(persona=ePersona)
            miscitas_serializer = ProximaCitaSerializer(proxima_cita, many=True)
            data = {
                'eMisCitas': miscitas_serializer.data if proxima_cita.exists() else []
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
