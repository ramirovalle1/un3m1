from django.urls import re_path, include
from empleo import commonviews, hojavida, postular, mispostulaciones

# adm_segundaetapa, adm_usuarios, postulate, commonviews, mispostulaciones, postular, adm_postulate, adm_configuraciontitulos, adm_revisionpostulacion

urlpatterns = [
    re_path(r'^loginempleo$', commonviews.login_user, name='loginempleo_view'),
    re_path(r'^emp_hojavida$', hojavida.view, name='emp_hojavida_view'),
    re_path(r'^emp_postulaciones', mispostulaciones.view, name='emp_postulacion_view'),
    re_path(r'^emp_postular$', postular.view, name='post_postular_view'),
    re_path(r'^notificaciones$', commonviews.notificaciones, name='notificaciones'),
    re_path(r'^empresa/', include('empresa.urls')),
]