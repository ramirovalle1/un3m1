from django.urls import re_path
from investigacion import adm_investigacion, adm_proyectoinvestigacion, pro_proyectoinvestigacion, eva_proyectoinvestigacion, pro_investigacion, ges_investigacion, ges_grupoinvestigacion, pro_financiamientoponencia, adm_financiamientoponencia, pro_obrarelevancia, adm_obrarelevancia, \
    pro_produccioncientifica, adm_revisioncriteriosactividades, pro_fgrupoinvestigacion, adm_produccioncientifica, adm_evaluacioninvestigacion, pro_evaluacioninvestigacion, adm_asesoriainvestigacion, pro_asesoriainvestigacion, adm_docenteinvitado, pro_docenteinvitado, publicaciones, adm_gestiondato, pro_gestiondato

urlpatterns = [
    re_path(r'^inv_modulo$', adm_investigacion.view, name='investigacion_adm_investigacion_view'),
    re_path(r'^adm_proyectoinvestigacion$', adm_proyectoinvestigacion.view, name='investigacion_adm_proyectoinvestigacion_view'),
    re_path(r'^pro_proyectoinvestigacion$', pro_proyectoinvestigacion.view, name='investigacion_pro_proyectoinvestigacion_view'),
    re_path(r'^eva_proyectoinvestigacion$', eva_proyectoinvestigacion.view, name='investigacion_eva_proyectoinvestigacion_view'),
    re_path(r'^pro_investigacion$', pro_investigacion.view, name='investigacion_pro_investigacion_view'),
    re_path(r'^ges_investigacion$', ges_investigacion.view, name='investigacion_ges_investigacion_view'),
    re_path(r'^ges_grupoinvestigacion$', ges_grupoinvestigacion.view, name='investigacion_ges_grupoinvestigacion_view'),
    re_path(r'^pro_fgrupoinvestigacion$', pro_fgrupoinvestigacion.view, name='investigacion_pro_fgrupoinvestigacion_view'),
    re_path(r'^pro_financiamientoponencia$', pro_financiamientoponencia.view, name='investigacion_pro_financiamientoponencia_view'),
    re_path(r'^adm_financiamientoponencia$', adm_financiamientoponencia.view, name='investigacion_adm_financiamientoponencia_view'),
    re_path(r'^pro_obrarelevancia$', pro_obrarelevancia.view, name='investigacion_pro_obrarelevancia_view'),
    re_path(r'^adm_obrarelevancia$', adm_obrarelevancia.view, name='investigacion_adm_obrarelevancia_view'),
    re_path(r'^pro_produccioncientifica$', pro_produccioncientifica.view, name='investigacion_pro_produccioncientifica_view'),
    re_path(r'^adm_produccioncientifica$', adm_produccioncientifica.view, name='investigacion_adm_produccioncientifica_view'),
    re_path(r'^adm_evaluacioninvestigacion$', adm_evaluacioninvestigacion.view, name='investigacion_adm_evaluacioninvestigacion_view'),
    re_path(r'^pro_evaluacioninvestigacion$', pro_evaluacioninvestigacion.view, name='investigacion_pro_evaluacioninvestigacion_view'),
    re_path(r'^adm_asesoriainvestigacion$', adm_asesoriainvestigacion.view, name='investigacion_adm_asesoriainvestigacion_view'),
    re_path(r'^pro_asesoriainvestigacion$', pro_asesoriainvestigacion.view, name='investigacion_pro_asesoriainvestigacion_view'),
    re_path(r'^adm_docenteinvitado$', adm_docenteinvitado.view, name='investigacion_adm_docenteinvitado_view'),
    re_path(r'^pro_docenteinvitado$', pro_docenteinvitado.view, name='investigacion_pro_docenteinvitado_view'),
    re_path(r'^adm_gestiondato$', adm_gestiondato.view, name='investigacion_adm_gestiondato_view'),
    re_path(r'^pro_gestiondato$', pro_gestiondato.view, name='investigacion_pro_gestiondato_view'),
    re_path(r'^adm_revisioncriteriosactividades$', adm_revisioncriteriosactividades.view, name='investigacion_adm_revisioncriteriosactividades_view'),
    re_path(r'^publicaciones$', publicaciones.view, name='publicaciones'),
    ]
