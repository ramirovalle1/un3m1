import os
import random
import calendar
import zipfile
from _decimal import Decimal
from datetime import datetime
from django.db.models import Q, Case, When, Value
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.ver_resoluciones import *
from django.core.cache import cache
from sga.templatetags.sga_extras import encrypt
from sga.models import PerfilUsuario
ahora = datetime.now()
fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
tiempo_cache = fecha_fin - ahora
TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())


"""todo el día en caache"""
@method_decorator(cache_page(TIEMPO_ENCACHE), name='dispatch')
class VerResolucionesAPIView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    default_limit = 20
    #page_size = 20
    api_key_module = 'ALUMNO_RESOLUCIONES'

    @api_security
    def get(self, request):
        try:
            TIEMPO_ENCACHE = 60 * 60 * 60
            hoy = datetime.now()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario,
                          TIEMPO_ENCACHE)
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            # valida si esta matriculado -dbg
            if payload['matricula']['id'] is None:
                raise NameError(u'No se encuentra matriculado.')

            eSearch = None
            tipo = 0
            desde = hasta= ''
            date_format = "%Y-%m-%d"
            filtro = Q(status=True)

            if 'search' in request.GET:
                eSearch = request.GET['search']

            if 'tipore' in request.GET:
                vtipore = request.GET['tipore']
                if vtipore == '0' or vtipore == 'undefined':
                    tipo = int(request.GET['tipore'])
                else:
                    tipo = int(encrypt(request.GET['tipore']))

            if 'desde' in request.GET:
                desde = request.GET['desde']
            if 'hasta' in request.GET:
                hasta = request.GET['hasta']

            if 'url_vars' in request.GET:
                url_vars = request.GET['url_vars']
            else:
                url_vars = ''

            if eSearch:
                request.data['search'] = eSearch
                filtro = filtro & (Q(numeroresolucion__icontains=eSearch) | Q(resuelve__icontains=eSearch))
                url_vars += "&search={}".format(eSearch)

            if tipo > 0:
                request.data['tipo'] = tipo
                filtro = filtro & Q(tipo__id=tipo)
                url_vars += "&tipo={}".format(tipo)

            if desde != 'undefined' and desde != '':
                desde_f = datetime.strptime(desde, date_format)
                filtro = filtro & Q(fecha__gte=desde_f)
                url_vars += "&desde={}".format(desde)

            if hasta != 'undefined' and hasta !='':
                hasta_f = datetime.strptime(hasta, date_format)
                filtro = filtro & Q(fecha__lte=hasta_f)
                url_vars += "&hasta={}".format(hasta)

            eResoluciones = Resoluciones.objects.filter(filtro).order_by('-fecha')

            coordinacion = ePerfilUsuario.inscripcion.carrera.coordinacion_carrera().id if ePerfilUsuario.inscripcion else None
            if coordinacion == 7:
                eResoluciones = eResoluciones.annotate(
                    tipo_ordenado=Case(When(tipo=4, then=Value(0)), default=Value(1))).order_by('tipo_ordenado',
                                                                                                '-fecha_creacion')
            else:
                eResoluciones = eResoluciones.annotate(
                    tipo_ordenado=Case(When(tipo=4, then=Value(1)), default=Value(0))).order_by('tipo_ordenado',
                                                                                                '-fecha_creacion')
                
            #Paginado LimitOffsetPagination
            results = self.paginate_queryset( eResoluciones,request, view= self)
            eResoluciones_serializer = ResolucionesSerializer(results,many=True)

            eTipoResoluciones = TipoResolucion.objects.all()
            eTipoResoluciones_serializer = TipoResolucionesSerializer(eTipoResoluciones, many=True)

            #Data LimitOffsetPagination
            data = {
                'eTipoResoluciones': eTipoResoluciones_serializer.data,
                'eResoluciones': eResoluciones_serializer.data,
                'search': eSearch if eSearch else "",
                'count': self.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'url_vars': url_vars,
            }

            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)

        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)






