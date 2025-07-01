# coding=utf-8
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Count, PROTECT, Sum, Avg, Min, Max, F
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.noticia import NoticiaSerializer, NotificacionDeudaPeriodoSerializer
from settings import ALUMNOS_GROUP_ID
from sga.funciones import convertir_fecha_invertida
from sga.models import Noticia, Inscripcion, NotificacionDeudaPeriodo, Periodo
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class NoticiaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            if cache.has_key(f"inscripcion_id_{payload['inscripcion']['id']}"):
                eInscripcion = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
            else:
                try:
                    eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=encrypt(payload['inscripcion']['id']))
                except ObjectDoesNotExist:
                    raise NameError(u"Inscripción no válida")
                cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
            ePersona = eInscripcion.persona
            nombreNoticiaCache = f"noticia_panel_{ALUMNOS_GROUP_ID}"
            nombreBannerCache = f"banner_panel_{ALUMNOS_GROUP_ID}"
            if eInscripcion.es_admision():
                nombreNoticiaCache = f"{nombreNoticiaCache}_admision_serializer"
                nombreBannerCache = f"{nombreBannerCache}_admision_serializer"
            elif eInscripcion.es_pregrado():
                nombreNoticiaCache = f"{nombreNoticiaCache}_pregrado_serializer"
                nombreBannerCache = f"{nombreBannerCache}_pregrado_serializer"
            elif eInscripcion.es_posgrado():
                nombreNoticiaCache = f"{nombreNoticiaCache}_posgrado_serializer"
                nombreBannerCache = f"{nombreBannerCache}_posgrado_serializer"
            else:
                nombreNoticiaCache = f"noticia_panel_{ALUMNOS_GROUP_ID}_serializer"
                nombreBannerCache = f"banner_panel_{ALUMNOS_GROUP_ID}_serializer"

            if cache.has_key(nombreNoticiaCache):
                eNoticias_1_serializer = cache.get(nombreNoticiaCache)
                eNoticias_1_serializer_aux = []
                if len(eNoticias_1_serializer):
                    for eNoticia in eNoticias_1_serializer:
                        desde = eNoticia.get('desde', None)
                        if desde is None:
                            desde = datetime.now().date()
                        else:
                            desde = convertir_fecha_invertida(desde)
                        hasta = eNoticia.get('hasta', None)
                        if hasta is None:
                            hasta = datetime.now().date()
                        else:
                            hasta = convertir_fecha_invertida(hasta)
                        if desde <= datetime.now().date() <= hasta:
                            eNoticias_1_serializer_aux.append(eNoticia)
                    eNoticias_1_serializer = eNoticias_1_serializer_aux
            else:
                eNoticias = Noticia.objects.db_manager("sga_select").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy),
                                                                            Q(imagen=None), Q(publicacion__in=[1, 2]),
                                                                            banerderecho=False, tipos__in=[1, 4],
                                                                            carreras__id=eInscripcion.carrera_id).distinct().order_by('-desde', 'id')[0:5]
                eNoticias_1_serializer = []
                if eNoticias.values("id").exists():
                    eNoticias_1_serializer = NoticiaSerializer(eNoticias, many=True).data
                ahora = datetime.now()
                fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
                tiempo_cache = fecha_fin - ahora
                tiempo_cache = int(tiempo_cache.total_seconds())
                cache.set(nombreNoticiaCache, eNoticias_1_serializer, tiempo_cache)

            if cache.has_key(nombreBannerCache):
                eNoticias_2_serializer = cache.get(nombreBannerCache)
                eNoticias_2_serializer_aux = []
                if len(eNoticias_2_serializer):
                    for eNoticia in eNoticias_2_serializer:
                        desde = eNoticia.get('desde', None)
                        if desde is None:
                            desde = datetime.now().date()
                        else:
                            desde = convertir_fecha_invertida(desde)
                        hasta = eNoticia.get('hasta', None)
                        if hasta is None:
                            hasta = datetime.now().date()
                        else:
                            hasta = convertir_fecha_invertida(hasta)
                        if desde <= datetime.now().date() <= hasta:
                            eNoticias_2_serializer_aux.append(eNoticia)
                    eNoticias_2_serializer = eNoticias_2_serializer_aux
            else:
                eNoticias = Noticia.objects.db_manager("sga_select").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy),
                                                                            Q(publicacion__in=[1, 2]),
                                                                            banerderecho=True,
                                                                            tipos__in=[1, 4],
                                                                            carreras__id=eInscripcion.carrera_id).distinct().order_by('-desde', 'id', 'fecha_creacion')[0:5]
                eNoticias_2_serializer = []
                if eNoticias.values("id").exists():
                    eNoticias_2_serializer = NoticiaSerializer(eNoticias, many=True).data
                ahora = datetime.now()
                fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
                tiempo_cache = fecha_fin - ahora
                tiempo_cache = int(tiempo_cache.total_seconds())
                cache.set(nombreBannerCache, eNoticias_2_serializer, tiempo_cache)

            ePeriodo = None
            if 'id' in payload['periodo']:
                if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                    ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
                else:
                    try:
                        ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                    except ObjectDoesNotExist:
                        ePeriodo = None
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            tieneValoresPendientes = False
            tieneValoresVencidos = False
            mensajeValoresRubros = ''
            if cache.has_key(f"notificacion_deuda"):
                eNotificacionDeuda = cache.get(f"notificacion_deuda")
            else:
                eNotificacionDeuda = None
                ahora = datetime.now()
                fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
                tiempo_cache = fecha_fin - ahora
                tiempo_cache = int(tiempo_cache.total_seconds())
                eNotificacionDeudas = NotificacionDeudaPeriodo.objects.filter(fechafinnotificacion__gte=datetime.now(), fechainicionotificacion__lte=datetime.now(), vigente=True)
                if eNotificacionDeudas.values("id").exists():
                    eNotificacionDeuda = eNotificacionDeudas.first()
                    fechafinnotificacion = eNotificacionDeuda.fechafinnotificacion
                    tiempo_cache = fechafinnotificacion - ahora
                    tiempo_cache = int(tiempo_cache.total_seconds())
                elif ePeriodo:
                    eNotificacionDeudas = eNotificacionDeudas.filter(Q(periodo=ePeriodo))
                    if eNotificacionDeudas.values("id").exists():
                        eNotificacionDeuda = eNotificacionDeudas.first()
                        fechafinnotificacion = eNotificacionDeuda.fechafinnotificacion
                        tiempo_cache = fechafinnotificacion - ahora
                        tiempo_cache = int(tiempo_cache.total_seconds())
                cache.set(f"notificacion_deuda", eNotificacionDeuda, tiempo_cache)
            if eNotificacionDeuda:
                if cache.has_key(f"notificacion_deuda_persona_id_{encrypt(ePersona.id)}"):
                    aData = cache.get(f"notificacion_deuda_persona_id_{encrypt(ePersona.id)}")
                    tieneValoresPendientes = aData.get('tiene_valores_pendientes', False)
                    tiene_valores_vencidos = aData.get('tiene_valores_vencidos', False)
                    msg_valores_rubros = aData.get('msg_valores_rubros', '')
                else:
                    aData = {
                        'tiene_valores_pendientes': False,
                        'tiene_valores_vencidos': False,
                        'msg_valores_rubros': '',

                    }
                    eCoordinaciones = eNotificacionDeuda.coordinaciones
                    if eInscripcion.coordinacion_id in eNotificacionDeuda.coordinaciones.values_list('id', flat=True):
                        eTipoOtroRubros = eNotificacionDeuda.tiposrubros.all()
                        if datetime.now().date() >= eNotificacionDeuda.fechainicionotificacion.date() and datetime.now().date() <= eNotificacionDeuda.fechafinnotificacion.date():
                            variables = locals()
                            exec(eNotificacionDeuda.logicanotificacion, globals(), variables)
                            aData = variables['descifrar_notificacion'](ePersona, None, eTipoOtroRubros)
                            tieneValoresPendientes = aData['tiene_valores_pendientes']
                            tieneValoresVencidos = aData['tiene_valores_vencidos']
                            mensajeValoresRubros = aData['msg_valores_rubros']
                    ahora = datetime.now()
                    fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
                    tiempo_cache = fecha_fin - ahora
                    tiempo_cache = int(tiempo_cache.total_seconds())
                    cache.set(f"notificacion_deuda_persona_id_{encrypt(ePersona.id)}", aData, tiempo_cache)

            data = {
                'eNews': eNoticias_1_serializer,
                'eNewsBanner': eNoticias_2_serializer,
                'tieneValoresPendientes': tieneValoresPendientes,
                'tieneValoresVencidos': tieneValoresVencidos,
                'mensajeValoresRubros': mensajeValoresRubros
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
