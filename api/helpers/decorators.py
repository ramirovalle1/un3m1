# coding=utf-8
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from django.db.models import Q
from api.helpers.response_herlper import Helper_Response
from bd.funciones import log_store, enviar_notificacion_log_store_uxplora, action_registre_log_clic_api_sge
from bd.models import InventarioOpcionSistema
from core.cache import get_cache_ePerfilUsuario, get_cache_eCoordinacionInscripcion
from settings import ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID, DEBUG
from sga.funciones import variable_valor
from sga.models import PerfilUsuario, Modulo, Periodo
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache
from core.cache import CacheRedisProxy


def api_security(f):

    def new_f(view, request, *args, **kwargs):
        try:
            payload = request.auth.payload

            if not request.user.is_authenticated:
                raise NameError(u'Usuario no autentificado')

            site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
            if site_maintenance:
                raise NameError(u'Sitio en mantenimiento')
            if not 'perfilprincipal' in payload:
                raise NameError(u'Usuario no identificado')
            ePerfilUsuario = get_cache_ePerfilUsuario(int(encrypt(payload['perfilprincipal']['id'])))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Acceso no permitido')
            eInscripcion = ePerfilUsuario.inscripcion
            if eInscripcion.coordinacion.id != 7:
                if view.api_key_module:
                    if variable_valor('FICHASOC_OBLIGATORIA'):
                        if not eInscripcion.tiene_ficha_socioeconomica_confirmada() and view.api_key_module != 'ALUMNO_SOCIOECONOMICO':
                            return Helper_Response(isSuccess=False, redirect="alu_socioecon", module_access=False, token=False, message='Completar/Actualizar ficha socioeconomica', status=status.HTTP_200_OK)

            if view.api_key_module:
                eInscripcion = ePerfilUsuario.inscripcion
                if eInscripcion.persona.necesita_cambiar_clave():
                    return Helper_Response(isSuccess=False, redirect="changepass", module_access=False,
                                           message=f"Estimad{'a' if eInscripcion.persona.es_mujer() else 'o'} {eInscripcion.persona.nombre_completo()}, se recomienda cambiar contraseña",
                                           status=status.HTTP_200_OK)
                eCoordinacion = get_cache_eCoordinacionInscripcion(eInscripcion.id)
                if ePerfilUsuario.es_estudiante():
                    g = [ALUMNOS_GROUP_ID]
                elif ePerfilUsuario.es_profesor():
                    g = [PROFESORES_GROUP_ID]
                else:
                    g = [x.id for x in ePerfilUsuario.persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])]
                api_key_module = view.api_key_module
                eCache = CacheRedisProxy()
                if eCache.has_key_cache(key=f"modulos__{api_key_module}"):
                    eModules = eCache.get_cache(key=f"modulos__{api_key_module}")
                else:
                    eModules = Modulo.objects.values("id", "api").filter(modulogrupo__grupos__id__in=g, api_key=api_key_module, activo=True)
                    eCache.set_cache(key=f"modulos__{api_key_module}", value=eModules)
                frolvacio = Q(roles__isnull=True) | Q(roles='')
                if len(eModules) == 0:
                    raise NameError('Módulo no existente')
                #"""COMPROBAR ACCESO PARA ADMISIÓN"""
                if eCoordinacion.id == 9:
                    if not eModules.values("id").filter(frolvacio | Q(roles__icontains=1)).exists():
                        raise NameError('Acceso no permitido')
                #"""COMPROBAR ACCESO PARA POSGRADO"""
                elif eCoordinacion.id == 7:
                    if not eModules.values("id").filter(frolvacio | Q(roles__icontains=3)).exists():
                        raise NameError('Acceso no permitido')
                else:
                    if not eModules.values("id").filter(frolvacio | Q(roles__icontains=2)).exists():
                        raise NameError('Acceso no permitido')

                if variable_valor('HABILITAR_REGISTRO_CLIC'):
                    action_registre_log_clic_api_sge(request, view)
            return f(view, request, *args, **kwargs)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK, module_access=False)
    return new_f


