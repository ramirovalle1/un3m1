from datetime import datetime
from django.db.models import Q
from rest_framework.views import APIView
from api.helpers.decorators import api_security
from rest_framework.pagination import LimitOffsetPagination
from rest_framework import status
from api.helpers.response_herlper import Helper_Response
from sga.models import PerfilUsuario, ConvenioEmpresa, ConvenioCarrera
from sga.templatetags.sga_extras import encrypt
from api.serializers.alumno.convenioempresa import ConvenioEmpresaSerializer, ConvenioCarreraSerializer
class ConvenioEmpresaAPIView(APIView, LimitOffsetPagination):
    default_limit = 20
    api_key_module = 'ALUMNO_CONVENIOS_EMPRESA'

    @api_security
    def post(self, request):

        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']

            if action == 'detalleobjetivo':
                try:
                    if 'id' in request.data:
                        objetivo = ConvenioEmpresa.objects.filter(id=int(encrypt(request.data['id'])))
                        objetivo_serializer = ConvenioEmpresaSerializer(objetivo, many=True)

                        aData = {'detalleobjetivo': objetivo_serializer.data}

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'vercarreras':
                try:
                    convenio = ConvenioEmpresa.objects.get(id=int(encrypt(request.data['id'])))
                    carreras = ConvenioCarrera.objects.filter(convenioempresa=convenio, status=True)
                    carreras_serializer = ConvenioCarreraSerializer(carreras, many=True)

                    aData = {
                        'carreras': carreras_serializer.data,
                        'total': len(carreras)
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)


            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            TIEMPO_ENCACHE = 60 * 60 * 60
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            eIncripcion = ePerfilUsuario.inscripcion
            ePersona = eIncripcion.persona

            fecha_actual = datetime.now().date()

            filtro = Q(status=True)
            id = request.data.get('id', '')
            estado = request.GET.get('estado','')
            tipo = request.GET.get('tipo', '')
            desde = request.GET.get('desde', '')
            hasta = request.GET.get('hasta', '')
            search = request.GET.get('search', '')
            vars_url = ''
            date_format = "%Y-%m-%d"


            if estado != '0' and estado != '':
                estado = int(estado)
                vars_url += "&estado={}".format(estado)
                if estado == 1:
                    filtro = filtro & Q(fechafinalizacion__gte=fecha_actual)

                elif estado == 2:
                    filtro = filtro & Q(fechafinalizacion__lte=fecha_actual)


            if tipo!= '0' and tipo != '':
                tipo = int(tipo)
                vars_url += "&tipo={}".format((tipo))
                if tipo == 1:
                    filtro = filtro & Q(para_practicas=True)
                if tipo == 2:
                    filtro = filtro & Q(para_pasantias=True)
                if tipo == 3:
                    filtro = filtro & Q(para_practicas=True) | Q(para_pasantias=True)

            if desde != 'undefined' and desde != '':
                desde_f = datetime.strptime(desde, date_format).date()
                filtro = filtro & Q(fechainicio__gte=desde_f)
                vars_url = "&desde={}".format(desde_f)
            else:
                if desde == 'undefined':
                    desde = ''
                    vars_url += "&desde={}".format(desde)

            if hasta != 'undefined' and hasta != '':
                hasta_f = datetime.strptime(hasta, date_format).date()
                filtro = filtro & Q(fechafinalizacion__lte=hasta_f)
                vars_url = "&desde={}".format(hasta_f)
            else:
                if hasta == 'undefined':
                    hasta = ''
                    vars_url += "&hasta={}".format(hasta)

            if search != 'undefined':
                request.data['search'] = search
                filtro = filtro & (Q(empresaempleadora__nombre__icontains=search) | Q(tipoconvenio__nombre__icontains=search))


            eConvenio = ConvenioEmpresa.objects.filter(filtro).order_by('-pk')
            convenio_pag = self.paginate_queryset(eConvenio, request, view=self)
            convenio_serializer = ConvenioEmpresaSerializer(convenio_pag, many=True)

            data = {
                'convenios': convenio_serializer.data,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'limit': self.default_limit,
                'count': self.count,
                'vars_url': vars_url,
            }

            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
