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
from api.serializers.alumno.noticia import NoticiaSerializer
from settings import ALUMNOS_GROUP_ID
from sga.funciones import log, generar_nombre
from sga.models import Noticia, Inscripcion, NotificacionDeudaPeriodo, Periodo, InscripcionEncuestaGrupoEstudiantes, \
    EncuestaGrupoEstudiantes, PreguntaEncuestaGrupoEstudiantes, RespuestaPreguntaEncuestaGrupoEstudiantes, \
    RespuestaRangoEncuestaGrupoEstudiantes, RespuestaCuadriculaEncuestaGrupoEstudiantes, \
    RangoPreguntaEncuestaGrupoEstudiantes, OpcionCuadriculaEncuestaGrupoEstudiantes, \
    OpcionMultipleEncuestaGrupoEstudiantes, RespuestaMultipleEncuestaGrupoEstudiantes
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class EncuestaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        try:
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

            eEncuestas_x_contestar = []
            eEncuestas_x_contetsar_EnCache = cache.get(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}") if cache.get(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}") else None
            if not eEncuestas_x_contetsar_EnCache is None:
                eEncuestas_x_contestar = eEncuestas_x_contetsar_EnCache
            else:
                eAlumnoGrupoEncuestas = InscripcionEncuestaGrupoEstudiantes.objects.filter(inscripcion=eInscripcion, encuesta__tipoperfil=1, encuesta__activo=True, status=True, encuesta__status=True, respondio=False)
                if eAlumnoGrupoEncuestas.values("id").exists():
                    eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.filter(pk__in=eAlumnoGrupoEncuestas.values_list("encuesta_id", flat=True))
                    eEncuestas_x_contestar = GrupoEncuestaSerializer(eEncuestaGrupoEstudiantes, many=True).data
                cache.set(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}", eEncuestas_x_contestar, TIEMPO_ENCACHE)

            eEncuestas = []
            eEncuestas_EnCache = cache.get(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}")
            if not eEncuestas_EnCache is None:
                eEncuestas = eEncuestas_EnCache
            else:
                eAlumnoGrupoEncuestas = InscripcionEncuestaGrupoEstudiantes.objects.filter(inscripcion=eInscripcion, encuesta__tipoperfil=1, encuesta__activo=True, status=True, encuesta__status=True, respondio=True)
                if eAlumnoGrupoEncuestas.values("id").exists():
                    eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.filter(pk__in=eAlumnoGrupoEncuestas.values_list("encuesta_id", flat=True))
                    eEncuestas = GrupoEncuestaSerializer(eEncuestaGrupoEstudiantes, many=True).data
                cache.set(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}", eEncuestas, TIEMPO_ENCACHE)
            data = {
                'eQuizzes_to_answer': eEncuestas_x_contestar, # encuestas por contestar
                'eQuizzes_answered': eEncuestas # enucestas contestadas
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


class SaveEncuestaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):

        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        TIEMPO_ENCACHE = 60 * 60 * 60
        with transaction.atomic():
            try:
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
                if not 'id' in eRequest:
                    raise NameError(u"Parametro de encuesta no encontrado")
                if not 'respuestas' in eRequest:
                    raise NameError(u"Respuestas de encuesta no encontrada")
                eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.get(pk=encrypt(eRequest['id']))
                eInscripcionEncuestaGrupoEstudiantes = InscripcionEncuestaGrupoEstudiantes.objects.get(inscripcion_id=eInscripcion.id,
                                                                                                       encuesta__tipoperfil=1,
                                                                                                       encuesta__activo=True,
                                                                                                       encuesta=eEncuestaGrupoEstudiantes, status=True)
                eInscripcionEncuestaGrupoEstudiantes.respondio = True
                eInscripcionEncuestaGrupoEstudiantes.save(request)
                respuestas = json.loads(eRequest['respuestas'])
                for respuesta in respuestas:
                    # print(respuesta)
                    ePreguntaEncuestaGrupoEstudiantes = PreguntaEncuestaGrupoEstudiantes.objects.get(pk=encrypt(respuesta.get('id_pregunta')))
                    if respuesta.get('tipo') == 1:
                        for r in respuesta.get('respuestas'):
                            valor = r.get('valor')
                            eRespuestaPreguntaEncuestaGrupoEstudiantes = RespuestaPreguntaEncuestaGrupoEstudiantes(inscripcionencuesta=eInscripcionEncuestaGrupoEstudiantes,
                                                                                                                   pregunta=ePreguntaEncuestaGrupoEstudiantes,
                                                                                                                   respuesta='SI' if valor == 1 else 'NO',
                                                                                                                   respuestaporno='' if valor == 1 else r.get('observacion'))
                            eRespuestaPreguntaEncuestaGrupoEstudiantes.save(request)
                    if respuesta.get('tipo') == 2:
                        for r in respuesta.get('respuestas'):
                            opcionrango_id = encrypt(r.get('valor'))
                            eRangoPreguntaEncuestaGrupoEstudiantes = RangoPreguntaEncuestaGrupoEstudiantes.objects.get(pk=opcionrango_id)
                            eRespuestaRangoEncuestaGrupoEstudiantes = RespuestaRangoEncuestaGrupoEstudiantes(inscripcionencuesta=eInscripcionEncuestaGrupoEstudiantes,
                                                                                                             pregunta=ePreguntaEncuestaGrupoEstudiantes,
                                                                                                             opcionrango=eRangoPreguntaEncuestaGrupoEstudiantes,
                                                                                                             respuesta=eRangoPreguntaEncuestaGrupoEstudiantes.valor)
                            eRespuestaRangoEncuestaGrupoEstudiantes.save(request)
                    if respuesta.get('tipo') in [3, 4, 7]:
                        for r in respuesta.get('respuestas'):
                            valor = r.get('valor')
                            eRespuestaPreguntaEncuestaGrupoEstudiantes = RespuestaPreguntaEncuestaGrupoEstudiantes(inscripcionencuesta=eInscripcionEncuestaGrupoEstudiantes,
                                                                                                                   pregunta=ePreguntaEncuestaGrupoEstudiantes,
                                                                                                                   respuesta=valor)
                            eRespuestaPreguntaEncuestaGrupoEstudiantes.save(request)
                    if respuesta.get('tipo') == 5:
                        for r in respuesta.get('respuestas'):
                            opcioncuadricula_id = encrypt(r.get('valor'))
                            if 'archivo' in r:
                                eFiles.get(r.get('archivo'))

                            nfileDocumento = None
                            if eFiles.get(r.get('archivo')):
                                nfileDocumento = eFiles.get(r.get('archivo'))
                                extensionDocumento = nfileDocumento._name.split('.')
                                tamDocumento = len(extensionDocumento)
                                exteDocumento = extensionDocumento[tamDocumento - 1]
                                if nfileDocumento.size > 1500000:
                                    raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                                if not exteDocumento.lower() == 'pdf':
                                    raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                                nfileDocumento._name = generar_nombre("archivo_covid", nfileDocumento._name)

                            eOpcionCuadriculaEncuestaGrupoEstudiantes = OpcionCuadriculaEncuestaGrupoEstudiantes.objects.get(pk=opcioncuadricula_id)
                            eRespuestaCuadriculaEncuestaGrupoEstudiantes = RespuestaCuadriculaEncuestaGrupoEstudiantes(inscripcionencuesta=eInscripcionEncuestaGrupoEstudiantes,
                                                                                                                       pregunta=ePreguntaEncuestaGrupoEstudiantes,
                                                                                                                       opcioncuadricula=eOpcionCuadriculaEncuestaGrupoEstudiantes,
                                                                                                                       archivo = nfileDocumento,
                                                                                                                       respuesta=r.get('respuesta') if r.get('respuesta') else eOpcionCuadriculaEncuestaGrupoEstudiantes.valor)
                            eRespuestaCuadriculaEncuestaGrupoEstudiantes.save(request)
                    if respuesta.get('tipo') == 6:
                        for r in respuesta.get('respuestas'):
                            opcionmultiple_id = encrypt(r.get('valor'))
                            eOpcionMultipleEncuestaGrupoEstudiantes = OpcionMultipleEncuestaGrupoEstudiantes.objects.get(id=opcionmultiple_id)
                            eRespuestaMultipleEncuestaGrupoEstudiantes = RespuestaMultipleEncuestaGrupoEstudiantes(inscripcionencuesta=eInscripcionEncuestaGrupoEstudiantes,
                                                                                                                   pregunta=ePreguntaEncuestaGrupoEstudiantes,
                                                                                                                   opcionmultiple=eOpcionMultipleEncuestaGrupoEstudiantes,
                                                                                                                   respuesta=r.get('respuesta') if r.get('respuesta') else eOpcionMultipleEncuestaGrupoEstudiantes.valor)
                            eRespuestaMultipleEncuestaGrupoEstudiantes.save(request)

                log(u'Respondio encuesta: %s - %s' % (eEncuestaGrupoEstudiantes, eInscripcionEncuestaGrupoEstudiantes), request, "edit")

                eEncuestas_x_contestar_EnCache = cache.get(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}")
                if eEncuestas_x_contestar_EnCache:
                    cache.delete(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}")

                eEncuestas_EnCache = cache.get(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}")
                if eEncuestas_EnCache:
                    cache.delete(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}")
                return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
            except Exception as ex:
                transaction.set_rollback(True)
                return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


class DeleteEncuestaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        with transaction.atomic():
            try:
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
                if not 'id' in request.data:
                    raise NameError(u"Parametro de encuesta no encontrado")

                eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.get(pk=encrypt(request.data['id']))
                eDelete = eInscripcionEncuestaGrupoEstudiantes = InscripcionEncuestaGrupoEstudiantes.objects.get(inscripcion_id=eInscripcion.id, encuesta__tipoperfil=1, encuesta=eEncuestaGrupoEstudiantes)
                eInscripcionEncuestaGrupoEstudiantes.delete()
                log(u'Elimino encuesta: %s - %s' % (eEncuestaGrupoEstudiantes, eDelete), request, "del")
                if Inscripcion.objects.filter(pk=eInscripcion.id).exists():
                    inscripcion = InscripcionEncuestaGrupoEstudiantes.objects.filter(inscripcion_id=eInscripcion.id, encuesta=eEncuestaGrupoEstudiantes)
                    if inscripcion.exists():
                        for dato in inscripcion:
                            if not dato.status:
                                dato.status = True
                                dato.save(request)
                                log(u'(Estudiante) Se actualizo la inscripcion encuesta grupo: %s' % dato, request, "edit")
                    else:
                        registro = InscripcionEncuestaGrupoEstudiantes(
                            encuesta=eEncuestaGrupoEstudiantes,
                            inscripcion_id=eInscripcion.id
                        )
                        registro.save(request)
                        log(u'(Estudiante) Se guardo la inscripcion encuesta grupo: %s' % registro, request, "add")

                eEncuestas_x_contestar_EnCache = cache.get(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}")
                if eEncuestas_x_contestar_EnCache:
                    cache.delete(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}")

                eEncuestas_EnCache = cache.get(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}")
                if eEncuestas_EnCache:
                    cache.delete(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}")

                eEncuestas_x_contestar = []
                eEncuestas_x_contetsar_EnCache = cache.get(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}") if cache.get(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}") else None
                if not eEncuestas_x_contetsar_EnCache is None:
                    eEncuestas_x_contestar = eEncuestas_x_contetsar_EnCache
                else:
                    eAlumnoGrupoEncuestas = InscripcionEncuestaGrupoEstudiantes.objects.filter(inscripcion=eInscripcion, encuesta__tipoperfil=1, encuesta__activo=True, status=True, encuesta__status=True, respondio=False)
                    if eAlumnoGrupoEncuestas.values("id").exists():
                        eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.filter(pk__in=eAlumnoGrupoEncuestas.values_list("encuesta_id", flat=True))
                        eEncuestas_x_contestar = GrupoEncuestaSerializer(eEncuestaGrupoEstudiantes, many=True).data
                    cache.set(f"encuesta_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}", eEncuestas_x_contestar, TIEMPO_ENCACHE)

                eEncuestas = []
                eEncuestas_EnCache = cache.get(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}") if cache.get(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}") else None
                if not eEncuestas_EnCache is None:
                    eEncuestas = eEncuestas_EnCache
                else:
                    eAlumnoGrupoEncuestas = InscripcionEncuestaGrupoEstudiantes.objects.filter(inscripcion=eInscripcion, encuesta__tipoperfil=1, encuesta__activo=True, status=True, encuesta__status=True, respondio=True)
                    if eAlumnoGrupoEncuestas.values("id").exists():
                        eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.filter(pk__in=eAlumnoGrupoEncuestas.values_list("encuesta_id", flat=True))
                        eEncuestas = GrupoEncuestaSerializer(eEncuestaGrupoEstudiantes, many=True).data
                    cache.set(f"encuestas_alumnos_panel_{encrypt(eInscripcion.id)}", eEncuestas, TIEMPO_ENCACHE)
                data = {
                    'eQuizzes_to_answer': eEncuestas_x_contestar,  # encuestas por contestar
                    'eQuizzes_answered': eEncuestas  # enucestas contestadas
                }
                return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
            except Exception as ex:
                transaction.set_rollback(True)
                return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
