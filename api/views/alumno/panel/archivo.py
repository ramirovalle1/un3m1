# coding=utf-8
from datetime import datetime
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.archivo import ArchivoSerializer
from sga.models import Noticia, Inscripcion, Archivo
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache
from settings import ALUMNOS_GROUP_ID, ARCHIVO_TIPO_MANUALES


class ArchivoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            # eInscripcionEnCache = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
            # if eInscripcionEnCache:
            #     eInscripcion = eInscripcionEnCache
            # else:
            #     if not Inscripcion.objects.db_manager("sga_select").values("id").filter(pk=encrypt(payload['inscripcion']['id'])).exists():
            #         raise NameError(u"Inscripción no válida")
            #     eInscripcion = Inscripcion.objects.get(pk=encrypt(payload['inscripcion']['id']))
            #     cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
            # eArchivosEnCache = cache.get(f"archivos_panel_{ALUMNOS_GROUP_ID}")
            # if eArchivosEnCache:
            #     eArchivos = eArchivosEnCache
            # else:
            #     grupos = eInscripcion.persona.usuario.groups.filter(id__in=[ALUMNOS_GROUP_ID])
            #     eArchivos = Archivo.objects.db_manager("sga_select").filter(tipo__id=ARCHIVO_TIPO_MANUALES, grupo__in=grupos, api=True, visible=True)
            #     cache.set(f"archivos_panel_{ALUMNOS_GROUP_ID}", eArchivos, TIEMPO_ENCACHE)
            # eArchivos_serializer = ArchivoSerializer(eArchivos, many=True)
            data = {
            #     'eFiles': eArchivos_serializer.data if eArchivos.values("id").exists() else [],
                'eFiles': [],
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
