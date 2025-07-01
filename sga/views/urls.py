from django.urls import re_path, include

from sga.views.adm_capacitaciondocente import panel, gestion, formulario
from sga.views import p_capacitaciondocente

urlpatterns = [
    re_path(r'^adm_capacitaciondocente$', panel.view, name='sga_adm_capacitaciondocente_panel_view'),
    re_path(r'^adm_capacitaciondocente/gestion$', gestion.view, name='sga_adm_capacitaciondocente_gestion_view'),
    re_path(r'^adm_capacitaciondocente/formulario$', formulario.view, name='sga_adm_capacitaciondocente_formulario_view'),
    re_path(r'^p_capacitaciondocente/(?P<token>[\w-]+)/encuesta$', p_capacitaciondocente.encuesta, name='sga_p_capacitaciondocente_encuesta_view'),
    re_path(r'^p_capacitaciondocente/(?P<token>[\w-]+)/certificado$', p_capacitaciondocente.certificado, name='sga_p_capacitaciondocente_certificado_view'),
]
