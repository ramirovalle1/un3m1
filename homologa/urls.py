from django.urls import re_path

from homologa import adm_homologacion, alu_homologacion

urlpatterns = [
    re_path(r'^adm_homologacion$', adm_homologacion.view, name='adm_homologacion'),
    re_path(r'^alu_homologacion$', alu_homologacion.view, name='alu_homologacion'),
]