from django.urls import re_path
from postulate import adm_segundaetapa, adm_usuarios, postulate, commonviews, mispostulaciones, postular, adm_postulate, \
    adm_configuraciontitulos, adm_revisionpostulacion, adm_periodoplanificacion, adm_legalizacionactas
from postulate import adm_periodoconvocatoria, adm_bancoelegible, adm_bancohabilitado
from sga import notificacion

urlpatterns = [
    re_path(r'^loginpostulate$', commonviews.login_user, name='loginpostulate_view'),
    re_path(r'^post_hojavida$', postulate.view, name='post_hojavida_view'),
    re_path(r'^post_postulacion', mispostulaciones.view, name='post_postulacion_view'),
    re_path(r'^post_postular$', postular.view, name='post_postular_view'),
    #ADMINISTRATIVO
    re_path(r'^adm_usuarios$', adm_usuarios.view, name='adm_usuarios_view'),
    re_path(r'^adm_periodoconvocatoria$', adm_periodoconvocatoria.view, name='adm_periodoconvocatoria_view'),
    re_path(r'^adm_postulate$', adm_postulate.view, name='adm_postulate_view'),
    re_path(r'^adm_configuraciontitulos$', adm_configuraciontitulos.view, name='adm_configuraciontitulos_view'),
    re_path(r'^adm_revisionpostulacion$', adm_revisionpostulacion.view, name='adm_revisionpostulacion_view'),
    re_path(r'^adm_segundaetapa$', adm_segundaetapa.view, name='adm_segundaetapa_view'),
    re_path(r'^adm_periodoplanificacion$', adm_periodoplanificacion.view, name='adm_periodoplanificacion_view'),
    re_path(r'^adm_bancoelegible$', adm_bancoelegible.view, name='adm_bancoelegible_view'),
    re_path(r'^adm_bancohabilitado$', adm_bancohabilitado.view, name='adm_bancohabilitado_view'),
    re_path(r'^notificaciones$', notificacion.view, name='notificaciones'),
    re_path(r'^adm_legalizacionactas$', adm_legalizacionactas.view, name='adm_legalizacionactas_view'),

]