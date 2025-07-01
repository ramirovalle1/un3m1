# coding=utf-8
import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from operator import itemgetter
from django.contrib.contenttypes.fields import ContentType, GenericForeignKey
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.secretary import ServicioSerializer, CategoriaServicioSerializer
from certi.models import Certificado
from sagest.models import Rubro
from secretaria.funciones import generar_codigo_solicitud
from secretaria.models import Servicio, CategoriaServicio, Solicitud, HistorialSolicitud
from sga.funciones import generar_codigo
from sga.models import PerfilUsuario
from sga.templatetags.sga_extras import encrypt, traducir_mes
from django.core.cache import cache


class ServiceAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_SECRETARY'

    @api_security
    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        TIEMPO_ENCACHE = 60 * 15
        try:
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
            if not 'action' in eRequest:
                raise NameError(u'Acción no permitida')
            action = eRequest.get('action', None)
            if not action:
                raise NameError(u'Acción no permitida')

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            if not 'id' in request.query_params:
                raise NameError(u"Categoría no encontrada")
            id = int(encrypt(request.query_params.get('id', '')))
            eCategoriaServicios = CategoriaServicio.objects.filter(pk=id)
            if not eCategoriaServicios.values("id").exists():
                raise NameError(u"Categoría no encontrado")
            eCategoriaServicio = eCategoriaServicios.first()
            eServicios = Servicio.objects.filter(activo=True, status=True, categoria=eCategoriaServicio).order_by('orden')
            eSolicitudCont = Solicitud.objects.filter(perfil=ePerfilUsuario, estado__in=(1, 3))
            data = {
                'cont': len(eSolicitudCont),
                'eServicios': ServicioSerializer(eServicios, many=True).data if eServicios.values("id").exists() else [],
                'eCategoriaServicio': CategoriaServicioSerializer(eCategoriaServicio).data if eCategoriaServicio else None
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


