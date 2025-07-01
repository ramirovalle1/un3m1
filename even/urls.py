from django.urls import re_path
from even import adm_evento
from even import alu_eventos

urlpatterns = [
    re_path(r'^adm_evento$', adm_evento.view, name='adm_evento_view'),
    re_path(r'^alu_eventos$', alu_eventos.view, name='adm_evento_view'),
]
