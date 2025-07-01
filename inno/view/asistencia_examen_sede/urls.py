from django.urls import re_path
from inno.view.asistencia_examen_sede import manual, index, automatica, cogs, keys_access


urlpatterns = [
    re_path(r'^$', index.view, name='inno_adm_asistenciaexamensede_index_view'),
    re_path(r'^automatica$', automatica.view, name='inno_adm_asistenciaexamensede_automatica_view'),
    re_path(r'^manual$', manual.view, name='inno_adm_asistenciaexamensede_manual_view'),
    re_path(r'^cogs$', cogs.view, name='inno_adm_asistenciaexamensede_cogs_view'),
    re_path(r'^keys_access$', keys_access.view, name='inno_adm_asistenciaexamensede_keys_access_view'),
]
