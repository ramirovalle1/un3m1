from datetime import datetime
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.record_academico import NotaInscripcionSerializer, NotaRecorAcademicoSerializer, \
    NotaMallaSerializer, HistoricoRecordAcademicoSerializer
from sagest.models import Rubro
from sga.models import PerfilUsuario, Persona, Periodo, Reporte, Matricula, PeriodoGrupoSocioEconomico, Inscripcion
from settings import COBRA_COMISION_BANCO
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache

ahora = datetime.now()
fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
tiempo_cache = fecha_fin - ahora
TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())

"""4 horas en caache"""


@method_decorator(cache_page(14400), name='dispatch')
class NotasAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_NOTAS'

    @api_security
    def get(self, request, inscripcion_id):
        try:
            if inscripcion_id is None:
                raise NameError(u"Parametro no existe")
            if cache.has_key(f"inscripcion_id_{inscripcion_id}"):
                eInscripcion = cache.get(f"inscripcion_id_{inscripcion_id}")
            else:
                eInscripcion = Inscripcion.objects.get(pk=encrypt(f"inscripcion_id_{inscripcion_id}"))
                cache.set(f"inscripcion_id_{encrypt(eInscripcion.pk)}", eInscripcion, TIEMPO_ENCACHE)

            eMalla = eInscripcion.mi_malla()
            if not eMalla:
                raise NameError(u"No tiene malla asignada.")

            eInscripcion_serializer = NotaInscripcionSerializer(eInscripcion)
            eMalla_serializer = NotaMallaSerializer(eMalla)
            eRecordaAademicos = eInscripcion.recordacademico_set.filter(status=True).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
            eRecordaAademicos_serializer = NotaRecorAcademicoSerializer(eRecordaAademicos, many=True)
            aData = {
                'Title': "Registro Académico",
                'eInscripcion': eInscripcion_serializer.data,
                'eMalla': eMalla_serializer.data,
                'eRecordaAademicos': eRecordaAademicos_serializer.data if eRecordaAademicos.values("id").exists() else []
            }
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)


class NotaHistoricaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_NOTAS'

    @api_security
    def post(self, request, *args, **kwargs):
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']
            if action == 'detalle':
                try:

                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de incripción.')
                    id = encrypt(request.data['id'])
                    if not 'idre' in request.data:
                        raise NameError(u'No se encontro parametro de record academico.')
                    id = encrypt(request.data['id'])
                    idre = encrypt(request.data['idre'])

                    inscripcion = inscripcion = Inscripcion.objects.get(pk=int(id))
                    record = record = inscripcion.recordacademico_set.get(pk=int(idre))
                    historicos = record.historicorecordacademico_set.all().order_by('-fecha')
                    eRecordaAademicos_serializer = NotaRecorAcademicoSerializer(record)
                    eHistoricoRecord_serializer = HistoricoRecordAcademicoSerializer(historicos, many=True)

                    aData = {
                        'eRecordAcademico': eRecordaAademicos_serializer.data,
                        'eHistoricoRecord': eHistoricoRecord_serializer.data
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
