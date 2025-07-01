from django.urls import re_path
from juventud import admisionjuventud, adm_formacion

urlpatterns = [
    re_path(r'^adm_formacion$', adm_formacion.view, name='adm_formacion_view'),
    re_path(r'^admisionjuventud$', admisionjuventud.view, name='admisionjuventud'),
]

