# coding=utf-8
from datetime import datetime
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.congreso import InscritoCongresoSerializer
from api.serializers.alumno.manual_usuario import ManualUsuarioSerializer
from sagest.models import Rubro, InscritoCongreso
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, ManualUsuario
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache
from django.db import connections
from sga.funciones import log


class CongresoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_CONGRESO'

    @api_security
    def post(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']
            if action == 'confirmarEliminarCongreso':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        if not 'idins' in request.data:
                            raise NameError(u"Inscripción no encontrada")
                        id = int(encrypt(request.data['id']))
                        eInscritoCongreso = InscritoCongreso.objects.get(pk=id)
                        ePersona = eInscritoCongreso.participante
                        if eInscritoCongreso.cancelo_rubro():
                            raise NameError(u'No puede eliminar, el inscrito ya cuenta rubros cancelados.')
                        log(u'Elimino Incrito de congreso : %s [%s]' % (eInscritoCongreso, eInscritoCongreso.id), request, "del")
                        eInscritoCongreso.status = False
                        eInscritoCongreso.save(request)
                        if eInscritoCongreso.congreso.tiporubro:
                            if Rubro.objects.filter(persona=eInscritoCongreso.participante, tipo=eInscritoCongreso.congreso.tiporubro, cancelado=False, status=True).exists():
                                listarubros = Rubro.objects.filter(persona=eInscritoCongreso.participante, tipo=eInscritoCongreso.congreso.tiporubro, cancelado=False, status=True)
                                for rubro in listarubros:
                                    rubro.status = False
                                    rubro.save(request)
                                    log(u'Elimino Rubro en congreso : %s [%s]' % (eInscritoCongreso, eInscritoCongreso.congreso), request, "del")
                                    if rubro.epunemi and rubro.idrubroepunemi > 0:
                                        cursor = connections['epunemi'].cursor()
                                        sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id=" + str(rubro.idrubroepunemi)
                                        cursor.execute(sql)
                                        cursor.close()

                        eInscritoCongresos = ePersona.inscritocongreso_set.filter(status=True).distinct()
                        aData = {
                            'eCongresos': InscritoCongresoSerializer(eInscritoCongresos, many=True).data if eInscritoCongresos.values("id").exists() else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            payload = request.auth.payload
            id_persona = payload['persona']['id']
            if cache.has_key(f"data__persona_id_{id_persona}_serializer_congresos"):
                aData = cache.get(f"data__persona_id_{id_persona}_serializer_congresos")
            else:
                if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                    ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
                else:
                    ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                    cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
                if not ePerfilUsuario.es_estudiante():
                    raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                ePersona = ePerfilUsuario.persona
                eInscripcion = ePerfilUsuario.inscripcion
                if eInscripcion is None:
                    raise NameError(u"No existe perfil de alumno")
                eInscritoCongresos = ePersona.inscritocongreso_set.filter(status=True).distinct()
                eInscritoCongresos_serializer = []
                if eInscritoCongresos.values("id").exists():
                    eInscritoCongresos_serializer = InscritoCongresoSerializer(eInscritoCongresos, many=True).data
                aData = {
                    'eCongresos': eInscritoCongresos_serializer
                }
                cache.set(f"data__persona_id_{id_persona}_serializer_congresos", aData, TIEMPO_ENCACHE)
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
