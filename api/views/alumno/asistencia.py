# coding=utf-8
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.asistencia import AistenciaInscripcionSerializer, AsistenciaMallaSerializer, MatriculaSerializer, AsistenciaMateriaAsignada, AsistenciaLeccionSerializer, LogIngresoAsistenciaLeccionSerializer, AsistenciaLeccionSerializer2
from api.serializers.alumno.miscitas import ProximaCitaSerializer
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, AsistenciaLeccion, MateriaAsignada
from med.models import ProximaCita
from sga.templatetags.sga_extras import encrypt, traducir_mes


"""2 horas en cache"""
@method_decorator(cache_page(7200), name='dispatch')
class AsistenciasAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_ASISTENCIAS'

    @api_security
    def get(self, request, matricula_id):
        try:
            try:
                eMatricula = Matricula.objects.get(pk=encrypt(matricula_id))
            except ObjectDoesNotExist:
                raise NameError(u"No existe matricula")
            bloqueomatricula = eMatricula.bloqueomatricula
            eIncripcion = eMatricula.inscripcion
            eInscripcion_serializer = AistenciaInscripcionSerializer(eIncripcion)
            eMalla = eIncripcion.mi_malla()
            if not eMalla:
                raise NameError(u"No tiene malla asignada.")
            eMalla_serializer = AsistenciaMallaSerializer(eMalla)
            # lista = []
            mismaterias = eMatricula.materiaasignada_set.filter(status=True).order_by('materia__asignatura')
            materiaasignada_serializer = AsistenciaMateriaAsignada(mismaterias, many=True)
            anios_meses_ordenados = mismaterias.filter(asistencialeccion__leccion__fecha__isnull=False).order_by('asistencialeccion__leccion__fecha__year', 'asistencialeccion__leccion__fecha__month').distinct('asistencialeccion__leccion__fecha__month', 'asistencialeccion__leccion__fecha__year').values('asistencialeccion__leccion__fecha__year', 'asistencialeccion__leccion__fecha__month')
            meses = {
                1: "Enero",
                2: "Febrero",
                3: "Marzo",
                4: "Abril",
                5: "Mayo",
                6: "Junio",
                7: "Julio",
                8: "Agosto",
                9: "Septiembre",
                10: "Octubre",
                11: "Noviembre",
                12: "Diciembre",
            }
            lista_final = [
                [meses[item['asistencialeccion__leccion__fecha__month']], #Nombre de mes
                 item['asistencialeccion__leccion__fecha__year'], #Número de año
                 item['asistencialeccion__leccion__fecha__month'] #Número de mes
                 ] for item in anios_meses_ordenados]

            cantidadmaxima = 0

            data = {
                'Title': "Mis Asistencias",
                'eInscripcion': eInscripcion_serializer.data,
                'eMalla': eMalla_serializer.data,
                'materiasasiganadas': materiaasignada_serializer.data if mismaterias.values("id").exists() else [],
                'cantidad': cantidadmaxima,
                'bloqueomatricula': bloqueomatricula,
                'listameses': lista_final,

            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


class AsistenciaDetalleAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_ASISTENCIAS'

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']
            if action == 'detalleAsistencia':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        id = int(encrypt(request.data['id']))
                        asistencia = AsistenciaLeccion.objects.get(pk=id)
                        nombremate = asistencia.materiaasignada.materia.nombre_mostrar()
                        nombre_horario = asistencia.leccion.clase.turno.nombre_horario()
                        nombres = nombremate + " " + nombre_horario
                        log_acc = asistencia.log_acceso()
                        serializer_asistencia = LogIngresoAsistenciaLeccionSerializer(log_acc, many = True)
                        aData = {
                            'nombres': nombres,
                            'detalle_leccion': serializer_asistencia.data if log_acc else [],

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'ListarAsistencia':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        if not 'mes' in request.data:
                            raise NameError(u"Parametro mes no encontrado")
                        id = int(encrypt(request.data['id']))
                        materiasignada = MateriaAsignada.objects.get(pk=id)
                        nombremate = materiasignada.materia.nombre_mostrar()
                        mes = int(request.data['mes'])
                        asistencia = AsistenciaLeccion.objects.filter(materiaasignada=materiasignada, leccion__fecha__month = mes ,status=True).order_by('leccion__fecha')
                        serializer_asistencia = AsistenciaLeccionSerializer2(asistencia, many=True)
                        aData = {
                            'asistencias' : serializer_asistencia.data if asistencia.exists() else [],
                            'nombre': nombremate

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

