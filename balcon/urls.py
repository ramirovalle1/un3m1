from django.urls import re_path

from balcon import alu_solicitudbalcon, adm_solicitudbalcon, adm_balconservicios, adm_solicitudserviciosinformaticos, \
    p_registro_novedades, p_registro_novedades_add, p_registro_novedades_consult, alu_solicitudbalconexterno

urlpatterns = [
    re_path(r'^alu_solicitudbalcon$', alu_solicitudbalcon.view, name='alu_solicitudbalcon_view'),
    re_path(r'^alu_solicitudbalconexterno$', alu_solicitudbalconexterno.view, name='sga_alu_solicitudbalconexterno_view'),
    re_path(r'^adm_balconservicios$', adm_balconservicios.view, name='adm_balconservicios_view'),
    re_path(r'^adm_solicitudbalcon$', adm_solicitudbalcon.view, name='adm_solicitudbalcon_view'),
    re_path(r'^adm_solicitudpermisossistemas$', adm_solicitudserviciosinformaticos.view, name='adm_solicitudpermisossistemas_view'),
    re_path(r'^p_registro_novedades$', p_registro_novedades.view, name='p_registro_novedades_view'),
    re_path(r'^p_registro_novedades/add$', p_registro_novedades_add.view, name='p_registro_novedades_add_view'),
    re_path(r'^p_registro_novedades/consult$', p_registro_novedades_consult.view, name='p_registro_novedades_consult_view'),
]
