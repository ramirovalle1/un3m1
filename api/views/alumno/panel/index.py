# coding=utf-8
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Max, Min
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.response_herlper import Helper_Response
from api.helpers.decorators import api_security
from api.serializers.alumno.modulo import ModuloSerializer
from api.serializers.alumno.noticia import NoticiaSerializer
from api.serializers.alumno.hoja_vida import DatosPersonalesSerializer
from bd.models import MenuFavoriteProfile
from core.cache import get_cache_ePerfilUsuario, get_cache_eInscripcion, get_cache_eCoordinacionInscripcion
from settings import ALUMNOS_GROUP_ID, DEBUG
from sga.funciones import convertir_fecha_invertida, variable_valor
from sga.models import Modulo, ModuloGrupo, PerfilUsuario, Matricula, Inscripcion, Noticia, Periodo, \
    NotificacionDeudaPeriodo, PeriodoActulizacionHojaVida, NoticiaMuestra, RespuestaEvaluacionAcreditacion, \
    ActividadDetalleDistributivoCarrera, Profesor,Provincia
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache
from inno.models import MatriculaSedeExamen


class PanelAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            payload = request.auth.payload
            ePerfilUsuario = get_cache_ePerfilUsuario(int(encrypt(payload['perfilprincipal']['id'])))
            eInscripcion = get_cache_eInscripcion(ePerfilUsuario.inscripcion_id)
            eCoordinacion = get_cache_eCoordinacionInscripcion(eInscripcion.id)
            if eCoordinacion.id != 7:
                if not eInscripcion.tiene_ficha_socioeconomica_confirmada():
                    return Helper_Response(isSuccess=False, redirect="alu_socioecon", module_access=False, token=False, message='Completar/Actualizar ficha socioeconomica', status=status.HTTP_200_OK)

            eMatricula = None
            if 'id' in payload['matricula'] and payload['matricula']['id']:
                if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                    eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
                else:
                    try:
                        eMatricula = Matricula.objects.db_manager("sga_select").get(pk=encrypt(payload['matricula']['id']))
                        cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, TIEMPO_ENCACHE)
                    except ObjectDoesNotExist:
                        eMatricula = None
            ePeriodo = None
            if eMatricula:
                ePeriodo = eMatricula.nivel.periodo
            else:
                if 'id' in payload['periodo']:
                    if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                        ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
                    else:
                        try:
                            ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                        except ObjectDoesNotExist:
                            ePeriodo = None
                        cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            use_api = False

            # comienza
            if eCoordinacion.id != 7 and eCoordinacion.id != 9:
                if variable_valor('EVALUACION_ALUMNOS_OBLIGATORIO'):
                    if ePeriodo:
                        proceso = ePeriodo.proceso_evaluativo()
                        if proceso.instrumentoheteroactivo:
                            if eMatricula:
                                for profesormateria in eMatricula.mis_profesores_acreditacion():
                                    profesortienerubricas = profesormateria.mis_rubricas_hetero()
                                    if not profesormateria.evaluado(
                                            eMatricula) and profesortienerubricas and profesormateria.pueden_evaluar_docente_acreditacion(
                                        eMatricula):
                                        return Helper_Response(isSuccess=False, redirect="pro_aluevaluacion",
                                                               module_access=False,
                                                               token=True, message='Realice la evaluación a sus docentes.',
                                                               status=status.HTTP_200_OK)

                                respuestaeval = RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=1,
                                                                                               proceso=proceso,
                                                                                               evaluador=eInscripcion.persona).order_by(
                                    'materiaasignada__materia')
                                docentesdirectores = ActividadDetalleDistributivoCarrera.objects.values_list(
                                    'actividaddetalle__criterio__distributivo__profesor_id', flat=True).filter(
                                    actividaddetalle__criterio__distributivo__periodo=ePeriodo,
                                    actividaddetalle__criterio__criteriogestionperiodo__isnull=False,
                                    actividaddetalle__criterio__hetero=True, actividaddetalle__criterio__status=True,
                                    carrera=eInscripcion.carrera, status=True).distinct()
                                for listadirectores in docentesdirectores:
                                    profe = Profesor.objects.get(pk=listadirectores)
                                    if profe.mis_rubricas_heterodirectivos(ePeriodo.id):
                                        if not respuestaeval.filter(profesor=profe, materia__isnull=True,
                                                                    materiaasignada__isnull=True).exists():
                                            return Helper_Response(isSuccess=False, redirect="pro_aluevaluacion",
                                                                   module_access=False,
                                                                   token=True,
                                                                   message='Realice la evaluación a sus docentes.',
                                                                   status=status.HTTP_200_OK)



            if 'templatebasesetting' in payload:
                templatebasesetting = payload['templatebasesetting']
                use_api = templatebasesetting['use_api']
            eModules = get_modules(use_api, eCoordinacion, eMatricula)
            eNews_data = get_news(eInscripcion, ePeriodo)
            eNews = eNews_data.get('eNews', [])
            eNewsBanner = eNews_data.get('eNewsBanner', [])
            tieneValoresPendientes = eNews_data.get('tieneValoresPendientes', False)
            tieneValoresVencidos = eNews_data.get('tieneValoresVencidos', False)
            mensajeValoresRubros = eNews_data.get('mensajeValoresRubros', '')
            eDataMessages = get_messages(eInscripcion)
            es_pregrado= eInscripcion.es_pregrado()
            eModalidad = eInscripcion.modalidad_id
            eDatosPersona = {}
            eSedes = []
            VER_ENCUESTA_SEDE_EXAMEN=variable_valor('VER_ENCUESTA_SEDE_EXAMEN')
            EDITAR_ENCUESTA_SEDE_EXAMEN = variable_valor('EDITAR_ENCUESTA_SEDE_EXAMEN')
            #print(eMatricula.id)
            contesto_encuesta_sede_examen= False
            ENCUESTA_SEDE_EXAMEN_OBLIGATORIA = variable_valor('ENCUESTA_SEDE_EXAMEN_OBLIGATORIA')
            if eMatricula and es_pregrado:
                if not MatriculaSedeExamen.objects.values('id').filter(matricula_id=eMatricula.id,status=True, aceptotermino=True).exists() and VER_ENCUESTA_SEDE_EXAMEN and eModalidad == 3:
                    eSedes = get_sedes(TIEMPO_ENCACHE)
                    eDatosPersona = get_datos_persona(eInscripcion, eMatricula, TIEMPO_ENCACHE)
                    contesto_encuesta_sede_examen = True
                if EDITAR_ENCUESTA_SEDE_EXAMEN and eModalidad == 3 and MatriculaSedeExamen.objects.values('id').filter(matricula_id=eMatricula.id,status=True, aceptotermino=True, matricula__nivel__periodo_id=ePeriodo.id):
                    eSedes = get_sedes(TIEMPO_ENCACHE)
                    eDatosPersona = get_datos_persona(eInscripcion, eMatricula, TIEMPO_ENCACHE)
            aData = {
                'eModules': eModules,
                'eNews': eNews,
                'eNewsBanner': eNewsBanner,
                'tieneValoresPendientes': tieneValoresPendientes,
                'tieneValoresVencidos': tieneValoresVencidos,
                'mensajeValoresRubros': mensajeValoresRubros,
                'eDataMessages': eDataMessages,
                'es_pregrado':es_pregrado,
                'eDatosPersona': eDatosPersona,
                'eSedes':eSedes,
                'contesto_encuesta_sede_examen':contesto_encuesta_sede_examen,
                'VER_ENCUESTA_SEDE_EXAMEN':VER_ENCUESTA_SEDE_EXAMEN,
                'eModalidad':eModalidad,
                'ENCUESTA_SEDE_EXAMEN_OBLIGATORIA':ENCUESTA_SEDE_EXAMEN_OBLIGATORIA,
                'EDITAR_ENCUESTA_SEDE_EXAMEN':EDITAR_ENCUESTA_SEDE_EXAMEN,
                'ePeriodo': ePeriodo.id
            }

            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


def get_modules(use_api, eCoordinacion, eMatricula):
    if cache.has_key(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_v1"):
        if eCoordinacion.id == 9:
            # Mostrar modulos  para la coordinación de Admisión
            if cache.has_key(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_admision_v1"):
                eModules = cache.get(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_admision_v1")
                eModules_serializer = eModules if eModules else []
            else:
                eModules_serializer = set_cache_module(eMatricula, eCoordinacion, use_api, True)
        elif eCoordinacion.id == 7:
            # Mostrar modulos  para la coordinación de Postgrado
            if cache.has_key(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_posgrado_v1"):
                eModules = cache.get(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_posgrado_v1")
                eModules_serializer = eModules if eModules else []
            else:
                eModules_serializer = set_cache_module(eMatricula, eCoordinacion, use_api, True)
        else:
            # Mostrar modulos  para la coordinación de Pregado
            if cache.has_key(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_pregrado_v1"):
                eModules = cache.get(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_pregrado_v1")
                eModules_serializer = eModules if eModules else []
            else:
                eModules_serializer = set_cache_module(eMatricula, eCoordinacion, use_api, True)
    else:
        eModules_serializer = set_cache_module(eMatricula, eCoordinacion, use_api, True)
    return eModules_serializer


def set_cache_module(eMatricula, eCoordinacion, use_api, isReturn=False):
    if cache.has_key(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_v1"):
        eModules = cache.get(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_v1")
    else:
        eModuloGrupos = ModuloGrupo.objects.db_manager("sga_select").filter(grupos__in=[ALUMNOS_GROUP_ID]).distinct()
        eModules_sga = Modulo.objects.db_manager("sga_select").filter(Q(modulogrupo__in=eModuloGrupos), sga=True,
                                                                      activo=True).order_by('nombre')
        eModules_api = Modulo.objects.db_manager("sga_select").filter(Q(modulogrupo__in=eModuloGrupos), api=True,
                                                                      activo=True).order_by('nombre')
        eModules = eModules_sga | eModules_api
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        tiempo_cache = int(tiempo_cache.total_seconds())
        cache.set(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_v1", eModules, tiempo_cache)
    frolvacio = Q(roles__isnull=True) | Q(roles='')
    eModules_serializer = []
    if eCoordinacion.id == 9:
        # Mostrar modulos  para la coordinación de Admisión
        eModules_sga = eModules.filter(frolvacio | Q(roles__icontains=1), sga=True, activo=True).order_by('nombre')
        eModules_api = eModules.filter(frolvacio | Q(roles__icontains=1), api=True, activo=True).order_by('nombre')
        eModules = eModules_sga | eModules_api
        if use_api:
            eModules = eModules.filter(api=True)
        eModules_serializer = ModuloSerializer(eModules, many=True).data if eModules else []
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        tiempo_cache = int(tiempo_cache.total_seconds())
        cache.set(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_admision_v1", eModules_serializer, tiempo_cache)
    elif eCoordinacion.id == 7:
        # Mostrar modulos  para la coordinación de Postgrado
        eModules_sga = eModules.filter(frolvacio | Q(roles__icontains=3), sga=True, activo=True).order_by('nombre')
        eModules_api = eModules.filter(frolvacio | Q(roles__icontains=3), api=True, activo=True).order_by('nombre')
        eModules = eModules_sga | eModules_api
        if use_api:
            eModules = eModules.filter(api=True)
        if eMatricula and eMatricula.bloqueomatricula:
            eModules = Modulo.objects.filter(pk__in=[4, 383]).distinct()
        eModules_serializer = ModuloSerializer(eModules, many=True).data if eModules else []
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        tiempo_cache = int(tiempo_cache.total_seconds())
        cache.set(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_posgrado_v1", eModules_serializer, tiempo_cache)
    else:
        # Mostrar modulos  para la coordinación de Pregado
        eModules_sga = eModules.filter(frolvacio | Q(roles__icontains=2), sga=True, activo=True).order_by('nombre')
        eModules_api = eModules.filter(frolvacio | Q(roles__icontains=2), api=True, activo=True).order_by('nombre')
        eModules = eModules_sga | eModules_api
        if use_api:
            eModules = eModules.filter(api=True)
        if eMatricula and eMatricula.bloqueomatricula:
            eModules = Modulo.objects.filter(pk__in=[4, 7]).distinct()
        eModules_serializer = ModuloSerializer(eModules, many=True).data if eModules else []
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        tiempo_cache = int(tiempo_cache.total_seconds())
        cache.set(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_pregrado_v1", eModules_serializer, tiempo_cache)
    if isReturn:
        return eModules_serializer


def get_news(eInscripcion, ePeriodo):
    ahora = datetime.now()
    fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
    tiempo_cache = fecha_fin - ahora
    TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
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
        eNoticias = Noticia.objects.db_manager("sga_select").filter(Q(desde__lte=ahora), Q(hasta__gte=ahora),
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
        eNoticias = Noticia.objects.db_manager("sga_select").filter(Q(desde__lte=ahora), Q(hasta__gte=ahora),
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
    #Noticia con muestra para banner
    noticias_con_muestra_ban = Noticia.objects.filter(Q(desde__lte=ahora), Q(hasta__gte=ahora),
                                                  Q(imagen=None), Q(publicacion__in=[1, 2]), tipos__in=[1, 4],
                                                  banerderecho=True, tiene_muestra=True).distinct().order_by('-desde',
                                                                                                              'id')[0:5]
    eNoticiasMuestraBan_list = NoticiaMuestra.objects.filter(
        noticia__id__in=noticias_con_muestra_ban.values_list('id', flat=True), persona=eInscripcion.persona)
    eNoticiasMuestraBan = Noticia.objects.filter(id__in=eNoticiasMuestraBan_list.values('noticia'))
    if eNoticiasMuestraBan:
        for notiban in NoticiaSerializer(eNoticiasMuestraBan, many=True).data:
            eNoticias_2_serializer.append(notiban)
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
        eNotificacionDeudas = NotificacionDeudaPeriodo.objects.filter(fechafinnotificacion__gte=datetime.now(),
                                                                      fechainicionotificacion__lte=datetime.now(),
                                                                      vigente=True)
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
        ePersona = eInscripcion.persona
        if cache.has_key(f"notificacion_deuda_persona_id_{encrypt(ePersona.id)}"):
            aData = cache.get(f"notificacion_deuda_persona_id_{encrypt(ePersona.id)}")
            tieneValoresPendientes = aData.get('tiene_valores_pendientes', False)
            tieneValoresVencidos = aData.get('tiene_valores_vencidos', False)
            mensajeValoresRubros = aData.get('msg_valores_rubros', '')
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

    return data


def get_messages(eInscripcion):
    ahora = datetime.now()
    eDataMessages = []
    if cache.has_key(f"periodoactulizacioneshojavida_inscripcion_id{encrypt(eInscripcion.id)}_mensajes"):
        eDataMessages = cache.get(f"periodoactulizacioneshojavida_inscripcion_id{encrypt(eInscripcion.id)}_mensajes")
    else:
        fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_transcurrido = fin - ahora
        tiempo_transcurrido = int(tiempo_transcurrido.total_seconds())
        eInscripcionesPeriodoActulizacionHojaVidas = eInscripcion.inscripcionesperiodoactulizacionhojavida_set.filter(status=True,
                                                                                                                      periodoactualizacion__fechainicio__lte=ahora,
                                                                                                                      periodoactualizacion__estado=1,
                                                                                                                      periodoactualizacion__fechafin__gte=ahora).distinct()
        eInscripcionesPeriodoActulizacionHojaVidas = eInscripcionesPeriodoActulizacionHojaVidas.exclude(estado=0, status=True)[:1]
        ePeriodoActulizacionHojaVidas = PeriodoActulizacionHojaVida.objects.filter(status=True, pk__in=eInscripcionesPeriodoActulizacionHojaVidas.values_list("periodoactualizacion__id", flat=True)).distinct()
        if ePeriodoActulizacionHojaVidas.values("id").exists():
            fechainicio = ePeriodoActulizacionHojaVidas.aggregate(fechainicio=Min('fechainicio'))['fechainicio']
            fechafin = ePeriodoActulizacionHojaVidas.aggregate(fechafin=Max('fechafin'))['fechafin']
            inicio = datetime(fechainicio.year, fechainicio.month, fechainicio.day, 0, 0, 1)
            fin = datetime(fechafin.year, fechafin.month, fechafin.day, 23, 59, 59)
            tiempo_transcurrido = fin - inicio
            tiempo_transcurrido = int(tiempo_transcurrido.total_seconds())
        for eInscripcionesPeriodoActulizacionHojaVida in eInscripcionesPeriodoActulizacionHojaVidas:
            eInscripcion = eInscripcionesPeriodoActulizacionHojaVida.inscripcion
            ePersona = eInscripcion.persona
            if eInscripcionesPeriodoActulizacionHojaVida.estado == 2:
                type = 'info'
                body = f"{'Estimada' if ePersona.es_mujer() else 'Estimado'} {'aspirante' if eInscripcion.coordinacion_id == 9 else 'estudiante'}, la Universidad Estatal de Milagro, a través de la Dirección de Bienestar Universitario, se encuentra realizando la actualización de la información que reposa en el módulo “Hoja de vida”, te invitamos a completar tus datos y ser parte de esta campaña."
                icon = f"""<svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="24"
                        height="24"
                        fill="currentColor"
                        class="bi bi-info-circle-fill me-2"
                        viewBox="0 0 16 16"
                >
                    <path
                            d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"
                    />"""
            else:
                type = 'danger'
                body = f"{'Estimada' if ePersona.es_mujer() else 'Estimado'} {'aspirante' if eInscripcion.coordinacion_id == 9 else 'estudiante'}, se rechazó la actualización de su hoja de vida por los siguientes motivos: {eInscripcionesPeriodoActulizacionHojaVida.observacionrechazo}"
                icon = f"""<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-exclamation-circle-fill" viewBox="0 0 16 16">
                                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM8 4a.905.905 0 0 0-.9.995l.35 3.507a.552.552 0 0 0 1.1 0l.35-3.507A.905.905 0 0 0 8 4zm.002 6a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>
                                    </svg>"""
            eDataMessages.append({'title': 'Campaña de Actualización de Hoja de Vida.',
                                  'body': body,
                                  'type': type,
                                  'icon': icon})
        cache.set(f"periodoactulizacioneshojavida_inscripcion_id{encrypt(eInscripcion.id)}_mensajes", eDataMessages, tiempo_transcurrido)

    return eDataMessages

def get_datos_persona(eInscripcion,eMatricula, time_cache):
    eDatosPersona = {}
    try:
        if eInscripcion.persona is not None:
            if cache.has_key(f"persona_encuesta_sede_id_{eInscripcion.pk}_{eMatricula.pk}"):
                eDatosPersona = cache.get(f"persona_encuesta_sede_id_{eInscripcion.pk}_{eMatricula.pk}")
            else:
                eDatosPersona = DatosPersonalesSerializer(eInscripcion.persona).data
                eDatosPersona['matricula'] = eMatricula.id
                cache.set(f"persona_encuesta_sede_id_{eInscripcion.pk}_{eMatricula.pk}", eDatosPersona, time_cache)
    except Exception as ex:
        print(ex)
    finally:
        return eDatosPersona


def get_sedes(tiempo_cache):
    from inno.models import SedeVirtual, SedeProvincia,Provincia
    resultado = []
    try:
        # Obtener todas las sedes activas
        if cache.has_key(f"sedes_examenes_virtuales"):
            sedes_activas = cache.get(f"sedes_examenes_virtuales")
        else:
            sedes_activas = SedeVirtual.objects.filter(activa=True)
            cache.set(f"sedes_examenes_virtuales",sedes_activas,tiempo_cache)

        if cache.has_key(f"todas_las_provincias_registradas"):
            todas_provincias = cache.get(f"todas_las_provincias_registradas")
        else:
            todas_provincias = list(Provincia.objects.all().values_list('id',flat=True))
            cache.set(f"todas_las_provincias_registradas",todas_provincias,tiempo_cache)

        for sede in sedes_activas:
            # Obtener las provincias asociadas a la sede desde la tabla intermedia SedeProvincia
            if cache.has_key(f"provincias_sede_{sede.id}"):
                provincias_ids = cache.get(f"provincias_sede_{sede.id}")
            else:
                provincias_ids = list(SedeProvincia.objects.filter(sede_virtual=sede.id).values_list('provincia_id', flat=True))
                cache.set(f"provincias_sede_{sede.id}", provincias_ids, tiempo_cache)

            #Si no hay provincias asociadas a la sede, se agregan todas las provincias, esto para sede Milagro y Virtual
            if not provincias_ids:
                provincias_ids = todas_provincias

            # Agregar la sede al resultado con las provincias asociadas
            resultado.append({
                'id': sede.id,
                'nombre': sede.nombre,
                'provincias': provincias_ids  # Lista de IDs de provincias
            })
    except Exception as ex:
        print(ex)
    finally:
        return resultado
