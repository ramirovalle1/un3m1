# coding=utf-8
import json
from datetime import datetime

from django.db import transaction
from django.db.models import Q, Count, PROTECT, Sum, Avg, Min, Max, F
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.encuesta import AlumnoGrupoEncuestaSerializer, GrupoEncuestaSerializer
from api.serializers.alumno.insignias import InsigniaPersonaSerializer
from api.serializers.alumno.noticia import NoticiaSerializer
from settings import ALUMNOS_GROUP_ID
from sga.funciones import log, generar_nombre
from sga.models import Noticia, Inscripcion, NotificacionDeudaPeriodo, Periodo, InscripcionEncuestaGrupoEstudiantes, \
    EncuestaGrupoEstudiantes, PreguntaEncuestaGrupoEstudiantes, RespuestaPreguntaEncuestaGrupoEstudiantes, \
    RespuestaRangoEncuestaGrupoEstudiantes, RespuestaCuadriculaEncuestaGrupoEstudiantes, \
    RangoPreguntaEncuestaGrupoEstudiantes, OpcionCuadriculaEncuestaGrupoEstudiantes, \
    OpcionMultipleEncuestaGrupoEstudiantes, RespuestaMultipleEncuestaGrupoEstudiantes, InsigniaPersona
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class InsigniasView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        action = ''
        try:
            if 'action' in request.data:
                action = request.data.get('action')
            if action == 'insigniavisto':
                payload = request.auth.payload
                idinsignia = encrypt(request.data.get('id'))
                if InsigniaPersona.objects.filter(status=True, visto=False,id = int(idinsignia)).order_by('-id').exists():
                    insignia = InsigniaPersona.objects.filter(status=True, visto=False,id = int(idinsignia)).order_by('-id').first()
                    insignia.visto = True
                    insignia.save(request)
                    log(u'Insignia visto %s'%(insignia.__str__()),request,'edit')
                cache.delete(f"insignia_id_{payload['inscripcion']['id']}")
                return Helper_Response(isSuccess=True, status=status.HTTP_200_OK)
            else:
                hoy = datetime.now()
                payload = request.auth.payload
                eInscripcionEnCache = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
                if eInscripcionEnCache:
                    eInscripcion = eInscripcionEnCache
                else:
                    if not Inscripcion.objects.db_manager("sga_select").values("id").filter(pk=encrypt(payload['inscripcion']['id'])).exists():
                        raise NameError(u"Inscripción no válida")
                    eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=encrypt(payload['inscripcion']['id']))
                    cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
                # ePersona = eInscripcion.persona
                traerInsignia_ = None
                eInnsigniaEnCache = cache.get(f"insignia_id_{encrypt(eInscripcion.id)}")
                if eInnsigniaEnCache:
                    traerInsignia_ = eInnsigniaEnCache
                else:
                    if InsigniaPersona.objects.values('id').filter(status=True,visto=False, persona = eInscripcion.persona).exists():
                        traerInsignia_ = InsigniaPersona.objects.filter(status=True, visto=False, persona=eInscripcion.persona).order_by('-id').first()
                        cache.set(f"insignia_id_{encrypt(eInscripcion.id)}", traerInsignia_, TIEMPO_ENCACHE)
                traerInsigniaSerializer_ = InsigniaPersonaSerializer(traerInsignia_)
                data = {
                    'eInsignia': traerInsigniaSerializer_.data if traerInsignia_ else {},
                    'activo': True if traerInsignia_ else False
                }
                return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
