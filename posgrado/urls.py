from django.urls import re_path
from posgrado import commonviews, adm_admision, alu_requisitosmaestria, interesadosmaestria, admision, interesados, \
    admitidos, seguimientointeresados, comercial, adm_vinculacion_pos, alu_vinculacion_pos, adm_firmardocumentos_pos, \
    contabilidadposgrado, finanzasposgrado, adm_balcon_posgrado, adm_evaluacionposgrado, adm_evaluaciondirectivos, \
    seguimientograduado

urlpatterns = [re_path(r'^loginposgrado$', commonviews.login_user, name='LoginUser'),
               re_path(r'^interesadosmaestria$', interesadosmaestria.view, name='interesadosmaestria'),
               re_path(r'^admision$', admision.view, name='admision'),
               re_path(r'^interesados$', interesados.view, name='interesados'),
               re_path(r'^seguimientointeresado$', seguimientointeresados.view, name='seguimientointeresados'),
               # # ADMINISTRATIVOS
               re_path(r'^registro$', commonviews.registro_user, name='principal_registro_user'),
               re_path(r'^adm_admision$', adm_admision.view, name='administrativos_view'),
               re_path(r'^alu_requisitosmaestria$', alu_requisitosmaestria.view, name='principal_registro_user'),
               re_path(r'^requisitosmaestria$', interesadosmaestria.requisitos_maestria_archivos, name='requisitos_maestria'),
               re_path(r'^admitidos$', admitidos.view, name='admitidos'),
               re_path(r'^firmardocumentosposgrado$', adm_firmardocumentos_pos.view, name='firmar_documentos_posgrado'),
               re_path(r'^comercial$', comercial.view, name='comercial'),
               re_path(r'^adm_vinculacion_pos$', adm_vinculacion_pos.view, name='admivinculacion'),
               re_path(r'^alu_vinculacion_pos$', alu_vinculacion_pos.view, name='aluvinculacion'),
               re_path(r'^contabilidadposgrado$', contabilidadposgrado.view, name='contabilidadposgrado'),
               re_path(r'^finanzasposgrado$', finanzasposgrado.view, name='finanzasposgrado'),
               # re_path(r'^adm_formacionejecutiva$', adm_formacionejecutiva.view, name='adm_formacionejecutiva'),
               re_path(r'^adm_balcon_pos$', adm_balcon_posgrado.view, name='adm_balcon_posgrado'),
               re_path(r'^adm_evaluacionposgrado$', adm_evaluacionposgrado.view, name='adm_evaluacionposgrado'),
               re_path(r'^adm_evaluaciondirectivos$', adm_evaluaciondirectivos.view, name='adm_evaluaciondirectivos'),
               re_path(r'^seguimientograduadoposgrado$', seguimientograduado.view, name='seguimientograduadoposgrado'),
               re_path(r'^actualizadatosgraduadoposgrado$', seguimientograduado.view_actualizadato, name='view_actualizadato'),
               ]
