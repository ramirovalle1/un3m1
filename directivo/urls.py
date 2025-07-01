from django.urls import path, re_path

from directivo.views import adm_directivos, adm_sanciones

urlpatterns = [
    # MÓDULO DIRECTIVOS
    re_path(r'^adm_directivos$', adm_directivos.view, name='directivo_adm_directivos'),
    re_path(r'^adm_sanciones$', adm_sanciones.view, name='directivo_adm_sanciones'),
]
