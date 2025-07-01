from datetime import datetime
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.malla import InscripcionSerializer, AsignaturaMallaSerializer, MallaSerializer, \
    RecordAcademicoSerializer, AsignaturaMallaPredecesoraSerializer
from sga.models import PerfilUsuario, Periodo, RecordAcademico
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class MallaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_MALLA'

    @api_security
    def post(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            print(payload)
            ePeriodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id'])))
            if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
            else:
                ePeriodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id'])))
                cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            eIncripcion = ePerfilUsuario.inscripcion
            ePersona = eIncripcion.persona
            aData = {}
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            aData = {}
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)

            if cache.has_key(f"data__inscripcion_id_{encrypt(ePerfilUsuario.inscripcion_id)}_serealizer_mi_malla"):
                aData = cache.get(f"data__inscripcion_id_{encrypt(ePerfilUsuario.inscripcion_id)}_serealizer_mi_malla")
            else:
                eInscripcion = ePerfilUsuario.inscripcion
                eMalla = eInscripcion.mi_malla()
                if not eMalla:
                    raise NameError(u"No tiene malla asignada.")

                eInscripcion_serializer = InscripcionSerializer(eInscripcion)
                eMalla_serializer = MallaSerializer(eMalla)
                eAsignaturasMalla = eMalla.asignaturamalla_set.filter(status=True)
                if eInscripcion.itinerario:
                    eAsignaturasMalla = eAsignaturasMalla.filter(Q(itinerario__isnull=True) | Q(itinerario=0) | Q(itinerario=eInscripcion.itinerario))
                aAsignaturasMalla = []
                for eAsignaturaMalla in eAsignaturasMalla:
                    eAsignaturasMalla_data = AsignaturaMallaSerializer(eAsignaturaMalla).data
                    eRecordAcdemico_data = None
                    if RecordAcademico.objects.values("id").filter(status=True, asignaturamalla=eAsignaturaMalla, inscripcion=eInscripcion, asignatura=eAsignaturaMalla.asignatura).exists():
                        eRecordAcdemico = RecordAcademico.objects.filter(status=True, asignaturamalla=eAsignaturaMalla, inscripcion=eInscripcion).first()
                        eRecordAcdemico_data = RecordAcademicoSerializer(eRecordAcdemico).data
                    eAsignaturasMalla_data.__setitem__('recordacademico', eRecordAcdemico_data)
                    eAsignaturaMallaPredecesoras_data = []
                    eAsignaturaMallaPredecesoras = eAsignaturaMalla.asignaturamallapredecesora_set.all()
                    if eAsignaturaMallaPredecesoras.values("id").exists():
                        eAsignaturaMallaPredecesoras_data = AsignaturaMallaPredecesoraSerializer(eAsignaturaMallaPredecesoras, many=True).data
                    eAsignaturasMalla_data.__setitem__('predecesoras', eAsignaturaMallaPredecesoras_data)
                    aAsignaturasMalla.append(eAsignaturasMalla_data)
                aData = {
                    'eInscripcion': eInscripcion_serializer.data,
                    'eMalla': eMalla_serializer.data,
                    'eAsignaturasMalla': aAsignaturasMalla
                }
                cache.set(f"data__inscripcion_id_{encrypt(ePerfilUsuario.inscripcion_id)}_serealizer_mi_malla", aData, TIEMPO_ENCACHE)
            aData['Title'] = "Mi Malla Académica"
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
