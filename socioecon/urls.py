from django.urls import re_path
from socioecon import publicaciondonacion, adm_publicaciondonacion, donaciones
urlpatterns = [
    re_path(r'^publicaciondonacion$', publicaciondonacion.view, name='publicaciondonacion'),
    re_path(r'^adm_publicaciondonacion$', adm_publicaciondonacion.view, name='adm_publicaciondonacion'),
    re_path(r'^donaciones$', donaciones.view, name='donaciones'),
]