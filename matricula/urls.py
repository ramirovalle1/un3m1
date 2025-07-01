from django.urls import re_path
from matricula import alu_matricula, alu_matricula_admision, alu_matricula_posgrado, alu_matricula_pregrado, \
    alu_addremove_matricula, alu_addremove_matricula_admision, alu_addremove_matricula_pregrado, \
    alu_addremove_matricula_posgrado, alu_addremove_matricula_pregrado_demo, alu_matricula_pregrado_demo,\
    alu_solicitudmatricula_ultima, adm_solicitudmatricula, adm_solicitudmatricula_ultima, alu_solicitudmatricula, \
    alu_solicitudmatricula_especial, adm_solicitudmatricula_especial, api

urlpatterns = [
    re_path(r'^matricula/pregrado/add/api$', api.view_matriculacion_pregrado, name='alu_matriculacion_api_pregrado_view'),
    re_path(r'^matricula/pregrado/addremove/api$', api.view_addremove_matricula_pregrado, name='alu_addremove_matricula_api_pregrado_view'),
    re_path(r'^alu_matricula$', alu_matricula.view, name='alu_matricula_view'),
    re_path(r'^alu_matricula/admision$', alu_matricula_admision.view, name='alu_matricula_admision_view'),
    re_path(r'^alu_matricula/pregrado$', alu_matricula_pregrado.view, name='alu_matricula_pregrado_view'),
    # re_path(r'^alu_matricula/pregrado/demo$', alu_matricula_pregrado_demo.view, name='alu_matricula_pregrado_demo_view'),
    re_path(r'^alu_matricula/posgrado$', alu_matricula_posgrado.view, name='alu_matricula_posgrado_view'),
    re_path(r'^alu_addremove_matricula$', alu_addremove_matricula.view, name='alu_addremove_matricula_view'),
    re_path(r'^alu_addremove_matricula/admision$', alu_addremove_matricula_admision.view, name='alu_addremove_matricula_admision_view'),
    re_path(r'^alu_addremove_matricula/pregrado$', alu_addremove_matricula_pregrado.view, name='alu_addremove_matricula_pregrado_view'),
    # re_path(r'^alu_addremove_matricula/pregrado/demo$', alu_addremove_matricula_pregrado_demo.view, name='alu_addremove_matricula_pregrado_demo_view'),
    re_path(r'^alu_addremove_matricula/posgrado$', alu_addremove_matricula_posgrado.view, name='alu_addremove_matricula_posgrado_view'),
    re_path(r'^alu_solicitudmatricula$', alu_solicitudmatricula.view, name='matricula_alu_solicitudmatricula_view'),
    re_path(r'^alu_solicitudmatricula/ultima$', alu_solicitudmatricula_ultima.view, name='matricula_alu_solicitudmatricula_ultima_view'),
    re_path(r'^alu_solicitudmatricula/especial$', alu_solicitudmatricula_especial.view, name='matricula_alu_solicitudmatricula_especial_view'),
    re_path(r'^adm_solicitudmatricula$', adm_solicitudmatricula.view, name='matricula_adm_solicitudmatricula_view'),
    re_path(r'^adm_solicitudmatricula/ultima$', adm_solicitudmatricula_ultima.view, name='matricula_adm_solicitudmatricula_ultima_view'),
    re_path(r'^adm_solicitudmatricula/especial$', adm_solicitudmatricula_especial.view, name='matricula_adm_solicitudmatricula_especial_view'),
    # re_path(r'^alu_prematriculamodulocomputacion$', alu_solicitudmatricula.view, name='sga_alu_prematriculamodulocomputacion_view'),
    # re_path(r'^alu_prematriculamodulocomputacion$', alu_solicitudmatricula.view, name='sga_alu_solicitudmatricula_view'),
]
