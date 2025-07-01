# coding=utf-8
from datetime import datetime
from django.db import transaction
from operator import itemgetter
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.secretary import CategoriaServicioSerializer
from secretaria.models import Servicio, CategoriaServicio
from sga.models import PerfilUsuario, Periodo
from sga.templatetags.sga_extras import encrypt, traducir_mes


class CategoryAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_SECRETARY'

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']

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
            # eServicios = Servicio.objects.filter(activo=True, status=True)
            #eCategoriaServicios = CategoriaServicio.objects.filter(pk__in=eServicios.values_list("categoria__id", flat=True)).distinct()
            # ePeriodo = Periodo.objects.get(status=True, pk=int(encrypt(request.auth.payload['periodos'][0]['id'])))
            eCategoriaServicios = None
            if ePerfilUsuario.inscripcion.carrera.coordinacion_carrera().id == 9:
                eCategoriaServicios = CategoriaServicio.objects.filter(status=True,  roles=1, activo=True).distinct()
            elif ePerfilUsuario.inscripcion.carrera.coordinacion_carrera().id in [1, 2, 3, 4, 5]:
                eCategoriaServicios = CategoriaServicio.objects.filter(status=True,  roles=2, activo=True).distinct()
            elif ePerfilUsuario.inscripcion.carrera.coordinacion_carrera().id == 7:
                eCategoriaServicios = CategoriaServicio.objects.filter(status=True,  roles=3, activo=True).distinct()
            # if ePeriodo.tipo.id == 1:
            #     eCategoriaServicios = CategoriaServicio.objects.filter(status=True,  roles=1).distinct()
            # if ePeriodo.tipo.id == 2:
            #     eCategoriaServicios = CategoriaServicio.objects.filter(status=True,  roles=2).distinct()
            # if ePeriodo.tipo.id == 3:
            #     eCategoriaServicios = CategoriaServicio.objects.filter(status=True,  roles=3).distinct()
            data = {
                'eCategoriaServicios': CategoriaServicioSerializer(eCategoriaServicios, many=True).data if eCategoriaServicios.values("id").exists() else [],
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)