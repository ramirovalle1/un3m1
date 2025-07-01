from django.urls import re_path

from cita import adm_agendamientocitas, alu_agendamientocitas, adm_gestorcitas
from cita.views import serviciosvinculacion_publico, serviciosvinculacion, sitevinculacion

urlpatterns = [
    re_path(r'^adm_agendamientocitas$', adm_agendamientocitas.view, name='adm_agendamientocitas'),
    re_path(r'^alu_agendamientocitas$', alu_agendamientocitas.view, name='alu_agendamientocitas'),
    re_path(r'^adm_gestorcitas$', adm_gestorcitas.view, name='adm_gestorcitas'),
    # re_path(r'^serviciosvinculacion$', serviciosvinculacion_publico.view, name='serviciosvinculacion'),
    # re_path(r'^serviciovinculacion$', serviciosvinculacion.view, name='serviciovinculacion'),
    re_path(r'^sites', serviciosvinculacion_publico.view, name='sites'),
    re_path(r'^site$', serviciosvinculacion.view, name='site'),
    re_path(r'^servicios$', sitevinculacion.view, name='servicios'),
    # re_path(r'^centropsicologico/(?P<departamentoservicio>\w+)$', serviciosvinculacion.view, name='centropsicologico'),

]
