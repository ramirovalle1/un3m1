from django.urls import re_path
from postulaciondip import commonviews, postulacion, postu_requisitos, adm_postulacion, pos_proceso, \
    adm_seleccionprevia

urlpatterns = [re_path(r'^loginpostulacion$', commonviews.login_user, name='LoginUser'),
               re_path(r'^postulacion$', postulacion.view, name='postulacion'),
               re_path(r'^adm_postulacion$', adm_postulacion.view, name='adm_postulacion'),
               re_path(r'^postular$', commonviews.registro_user, name='principal_registro_user'),
               re_path(r'^postu_requisitos$', postu_requisitos.view, name='principal_registro_user'),
               re_path(r'^pos_proceso$', pos_proceso.view, name='pos_proceso'),
               re_path(r'^seleccionprevia$', adm_seleccionprevia.view, name='seleccionprevia'),
]
