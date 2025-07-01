from django.urls import re_path

from ejecuform import adm_ejecuform, adm_formacionejecutiva, commonviews, coursesfe

urlpatterns = [
    re_path(r'^adm_formejecuperiodo$',adm_ejecuform.view,name="ejecuform_adm_formejecuperiodo"),
    re_path(r'^loginformacionejecutiva$', commonviews.login_user, name='loginformacionejecutiva'),
    re_path(r'^registroformacionejecutiva$', commonviews.registro_user, name='registroformacionejecutiva'),
    re_path(r'^adm_formacionejecutiva$', adm_formacionejecutiva.view, name='adm_formacionejecutiva'),
    re_path(r'^index_formacion_ejecutiva$', commonviews.index, name='eventosformacion'),
    re_path(r'^index_ejecutiva$', coursesfe.view, name='index_ejecutiva'),
]