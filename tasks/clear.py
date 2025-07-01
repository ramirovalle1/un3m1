from django.core.cache import cache
from django_q.tasks import async_task


@async_task
def limpiar_cache():
    cache.clear()
