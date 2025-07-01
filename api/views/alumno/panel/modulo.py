# coding=utf-8
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.response_herlper import Helper_Response
from api.helpers.decorators import api_security
from api.serializers.alumno.modulo import ModuloSerializer
from bd.models import MenuFavoriteProfile
from core.cache import get_cache_ePerfilUsuario, get_cache_eInscripcion, get_cache_eCoordinacionInscripcion
from settings import ALUMNOS_GROUP_ID
from sga.models import Modulo, ModuloGrupo, PerfilUsuario, Matricula, Inscripcion
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class ModuloAPIView(APIView):
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
            use_api = False
            templatebasesetting = None
            if 'templatebasesetting' in payload:
                templatebasesetting = payload['templatebasesetting']
                use_api = templatebasesetting['use_api']
            eModules_serializer = []
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

            # eModulesFavorite_serializer = []
            # if templatebasesetting and 'use_menu_favorite_module' in templatebasesetting and templatebasesetting['use_menu_favorite_module']:
            #     eMenuFavoriteProfilesEnCache = cache.get(f"module_favorites_perfilprincipal_id_{encrypt(payload['perfilprincipal']['id'])}")
            #     if not eMenuFavoriteProfilesEnCache is None:
            #         eMenuFavorites = eMenuFavoriteProfilesEnCache
            #         if eMenuFavorites:
            #             eModulesFavorite_serializer = ModuloSerializer(eMenuFavorites, many=True)
            #     else:
            #         if 'id' in templatebasesetting:
            #             eMenuFavoriteProfiles = MenuFavoriteProfile.objects.filter(setting_id=encrypt(templatebasesetting['id']), profile=ePerfilUsuario)
            #             if eMenuFavoriteProfiles.values("id").exists():
            #                 eMenuFavoriteProfile = eMenuFavoriteProfiles[0]
            #                 eMenuFavorites = eMenuFavoriteProfile.mis_modulos()
            #                 if eMenuFavorites.values("id").exists():
            #                     cache.set(f"module_favorites_perfilprincipal_id_{encrypt(payload['perfilprincipal']['id'])}", eMenuFavorites, 60 * 60 * 12)
            #                     eModulesFavorite_serializer = ModuloSerializer(eMenuFavorites, many=True)
            #                 else:
            #                     cache.set(f"module_favorites_perfilprincipal_id_{encrypt(payload['perfilprincipal']['id'])}", [], 60 * 60 * 12)
            #             else:
            #                 cache.set(f"module_favorites_perfilprincipal_id_{encrypt(payload['perfilprincipal']['id'])}", [], 60 * 60 * 12)
            #         else:
            #             cache.set(f"module_favorites_perfilprincipal_id_{encrypt(payload['perfilprincipal']['id'])}", [], 60 * 60 * 12)
            #     eModules_serializer = ModuloSerializer(eModules, many=True).data if eModules else []
            #     return Helper_Response(isSuccess=True, data={'eModules': eModules_serializer, 'eModulesFavorite': eModulesFavorite_serializer}, status=status.HTTP_200_OK)
            # else:

            return Helper_Response(isSuccess=True, data=eModules_serializer, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


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
        eModules_serializer = ModuloSerializer(eModules, many=True).data if eModules else []
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        tiempo_cache = int(tiempo_cache.total_seconds())
        cache.set(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_pregrado_v1", eModules_serializer, tiempo_cache)
    if isReturn:
        return eModules_serializer