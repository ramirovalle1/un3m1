from django.urls import re_path, include

from api.views.telefonia.directorio import DistributivoPersonaLista

urlpatterns = [
    re_path(r'^directorio$', DistributivoPersonaLista.as_view(), name='api_view_telefonia_directorio'),

]
