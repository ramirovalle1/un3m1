from django.urls import re_path

from vincula import adm_ayudantiasinvestigacion, adm_controlayudantias

urlpatterns = [
    re_path(r'^adm_ayudantiasinvestigacion$', adm_ayudantiasinvestigacion.view, name='adm_ayudantiasinvestigacion'),
    re_path(r'^adm_controlayudantias$', adm_controlayudantias.view, name='adm_controlayudantias'),
]