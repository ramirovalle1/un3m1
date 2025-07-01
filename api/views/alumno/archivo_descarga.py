# coding=utf-8
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.archivo_descarga import ArchivoDescargaSerializer
from api.serializers.alumno.manual_usuario import ManualUsuarioSerializer
from sagest.models import ArchivoDescarga
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, ManualUsuario
from sga.templatetags.sga_extras import encrypt
from django.db.models import Q


class ArchivoDescargaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_ARCHIVO_DESCARGA'

    @api_security
    def get(self, request):
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            procesos = ArchivoDescarga.objects.filter(Q(estado=True) & Q(estadoacceso=2)).order_by('id')
            eArchivos_serializer = ArchivoDescargaSerializer(procesos, many=True)

            data = {
                'eArchivoDescarga': eArchivos_serializer.data if procesos.exists() else []
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
