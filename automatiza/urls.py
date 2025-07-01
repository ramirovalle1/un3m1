from django.urls import re_path
from automatiza import adm_ingresarequerimiento,adm_gestionarequerimiento
urlpatterns = [
    re_path(r'^adm_ingresarequerimiento$', adm_ingresarequerimiento.view, name='adm_ingresarequerimiento'),

    re_path(r'^adm_gestionarequerimiento$', adm_gestionarequerimiento.view, name='adm_gestionarequerimiento'),
]