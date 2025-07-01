from datetime import datetime
from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.core.exceptions import ObjectDoesNotExist
from sga.templatetags.sga_extras import encrypt

VERSION_CACHE_REDIS = 1


class CacheRedisProxy:

    def __init__(self, key='', timeout=None, version=None):
        self.key = key
        self.version = version
        if self.version is None:
            self.version = VERSION_CACHE_REDIS
        self.timeout = timeout
        if self.timeout is None:
            ahora = datetime.now()
            fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
            tiempo_cache = fecha_fin - ahora
            self.timeout = int(tiempo_cache.total_seconds())

    def has_key_cache(self, key=None):
        return cache.has_key(key=self.key if key is None else key, version=self.version)

    def get_cache(self, key=None):
        return cache.get(key=self.key if key is None else key, version=self.version)

    def set_cache(self, value, timeout=None, key=None):
        cache.set(key=self.key if key is None else key, value=value, timeout=self.timeout if timeout is None else timeout, version=self.version)

    def delete_cache(self, key=None):
        return cache.delete(key=self.key if key is None else key, version=self.version)


def get_cache_ePerfilUsuario(pk):
    from sga.models import PerfilUsuario
    key = f"perfilprincipal_id_{encrypt(pk)}"
    eCache = CacheRedisProxy(key=key)
    if eCache.has_key_cache():
        return eCache.get_cache()
    ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=pk)
    eCache.set_cache(ePerfilUsuario)
    return ePerfilUsuario


def delete_cache_ePerfilUsuario(pk):
    key = f"perfilprincipal_id_{encrypt(pk)}"
    eCache = CacheRedisProxy(key=key)
    if eCache.has_key_cache():
        return eCache.delete_cache()
    return


def get_cache_eInscripcion(pk):
    from sga.models import Inscripcion
    key = f"inscripcion_id_{encrypt(pk)}"
    eCache = CacheRedisProxy(key=key)
    if eCache.has_key_cache():
        return eCache.get_cache()
    eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=pk)
    eCache.set_cache(eInscripcion)
    return eInscripcion


def delete_cache_eInscripcion(pk):
    key = f"inscripcion_id_{encrypt(pk)}"
    eCache = CacheRedisProxy(key=key)
    if eCache.has_key_cache():
        return eCache.delete_cache()
    return


def get_cache_eCoordinacionInscripcion(pk):
    from sga.models import Inscripcion
    key = f"inscripcion_id_{encrypt(pk)}__coordinacion"
    eCache = CacheRedisProxy(key=key)
    if eCache.has_key_cache():
        return eCache.get_cache()
    eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=pk)
    eCoordinacion = eInscripcion.carrera.coordinacion_set.all()[0]
    eCache.set_cache(eCoordinacion)
    return eCoordinacion


def delete_cache_eCoordinacionInscripcion(pk):
    key = f"inscripcion_id_{encrypt(pk)}__coordinacion"
    eCache = CacheRedisProxy(key=key)
    if eCache.has_key_cache():
        return eCache.delete_cache()
    return


