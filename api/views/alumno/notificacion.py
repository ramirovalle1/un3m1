# coding=utf-8
from datetime import datetime
from django.db.models import Q, Sum
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.miscitas import ProximaCitaSerializer
from api.serializers.alumno.notificacion import NotificacionSerializer
from matricula.models import PeriodoMatricula
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, Notificacion, PRIORIDAD_NOTIFICACION
from sga.templatetags.sga_extras import encrypt
from sga.funciones import log
from django.core.cache import cache
from rest_framework.pagination import LimitOffsetPagination



class NotificacionesAPIView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_NOTIFICACIONES'
    default_limit = 10

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']
            if action == 'VerNotificacion':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        id = int(encrypt(request.data['id']))
                        eNotificacion = Notificacion.objects.get(pk=id)
                        eNotificacion.leido = True
                        eNotificacion.visible = False
                        eNotificacion.fecha_hora_leido = datetime.now()
                        eNotificacion.save(request)
                        log(u'Leo el mensaje: %s' % eNotificacion, request, "edit")
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                        eNotificacionEnCache = cache.get(f"notificaciones_perfilusuario_id_{encrypt(ePerfilUsuario.id)}")
                        if eNotificacionEnCache:
                            cache.delete(f"notificaciones_perfilusuario_id_{encrypt(ePerfilUsuario.id)}")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

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
            #eNotificacionEnCache = cache.get(f"notificaciones_perfilusuario_id_{encrypt(ePerfilUsuario.id)}")

            prioridad = 0
            filtro = Q(app_label='SIE', perfil=ePerfilUsuario, status=True)

            if 'prioridad' in request.GET:
                d_prio = request.GET['prioridad']
                if d_prio != '0' and d_prio != 'undefined':
                    prioridad = int(request.GET['prioridad'])
            if prioridad > 0:
                request.data['prioridad'] = prioridad
                filtro = filtro & Q(prioridad= prioridad)

            eNotificacionEnCache = cache.get(f"filtro")

            if eNotificacionEnCache:
                eNotificaciones = eNotificacionEnCache
                #eNotificaciones = Notificacion.objects.filter(filtro).order_by('leido', 'prioridad')

            else:
                eNotificaciones = Notificacion.objects.filter(filtro).order_by('leido', 'prioridad')
                cache.set(f"notificaciones_perfilusuario_id_{encrypt(ePerfilUsuario.id)}", eNotificaciones, TIEMPO_ENCACHE)

            notificaciones_pag = self.paginate_queryset(eNotificaciones, request, view=self)
            notificaciones_serializer = NotificacionSerializer(notificaciones_pag, many=True)
            data = {
                'eNotificaciones': notificaciones_serializer.data if eNotificaciones.values("id").exists() else [],
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'count': self.count,
                'limit': self.default_limit

            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
