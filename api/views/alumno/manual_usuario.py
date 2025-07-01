# coding=utf-8
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.manual_usuario import ManualUsuarioSerializer
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, ManualUsuario
from django.db.models import Q
from datetime import  datetime
from sga.templatetags.sga_extras import encrypt
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
ahora = datetime.now()
fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
tiempo_cache = fecha_fin - ahora
TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())


"""todo el día en caache"""
@method_decorator(cache_page(TIEMPO_ENCACHE), name='dispatch')
class ManualUsuarioAPIView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_MANUAL_USUARIO'
    default_limit = 10

    @api_security
    def get(self, request):
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')

            eSearch = None
            desde = hasta = ''
            date_format = "%Y-%m-%d"
            filtro = Q(status= True, tipos__id__in=[4, 1], visible=True)

            if 'search' in request.GET:
                eSearch = request.GET['search'].strip()
            if 'desde' in request.GET:
                desde = request.GET['desde']
            if 'hasta' in request.GET:
                hasta = request.GET['hasta']

            if eSearch:
                request.data['search'] = eSearch
                filtro = filtro & (Q(nombre__icontains =eSearch))

            if desde != 'undefined' and desde != '':
                desde_f = datetime.strptime(desde, date_format)

                filtro = filtro & Q(fecha__gte= desde_f)

            if hasta != 'undefined' and hasta != '':
                hasta_f = datetime.strptime(hasta, date_format)

                filtro = filtro & Q(fecha__lte=hasta_f)

            manuales = ManualUsuario.objects.filter(filtro).order_by('nombre')
            manuales_pag = self.paginate_queryset(manuales, request, view=self)

            manuales_serializer = ManualUsuarioSerializer(manuales_pag, many=True)
            data = {
                'eManualesUsuario': manuales_serializer.data if manuales.exists() else [],
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'count': self.count,
                'limit': self.default_limit
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
