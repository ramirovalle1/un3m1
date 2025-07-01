from django.urls import re_path

from . import adm_configuracionproceso, pro_solicitudpago, adm_solicitudpago, adm_contratos, adm_certificacion, \
    dir_contrato, adm_marcadas_dip, adm_criteriosactividadesdocenteposgrado, pro_informepago, adm_solicitudpagoguest

urlpatterns = [
    re_path(r'^adm_configuracionproceso$', adm_configuracionproceso.view, name='adm_configuracionproceso_view'),
    re_path(r'^pro_solicitudpago', pro_solicitudpago.view, name='pro_solicitudpago_view'),
    re_path(r'^pro_informepago', pro_informepago.view, name='pro_informepago_view'),
    re_path(r'^adm_solicitudpago', adm_solicitudpago.view, name='adm_solicitudpago_view'),
    re_path(r'^guest_solicitudpagoguest', adm_solicitudpagoguest.view, name='adm_solicitudpagoguest_view'),
    re_path(r'^adm_contratodip', adm_contratos.view, name='adm_contratos_view'),
    re_path(r'^dir_contratodip', dir_contrato.view, name='dir_contratos_view'),
    re_path(r'^adm_certificacion', adm_certificacion.view, name='adm_certificacion_view'),
    re_path(r'^adm_marcadas_dip',adm_marcadas_dip.view, name='adm_marcadas_view'),
    re_path(r'^adm_criteriosactividadesdocente',adm_criteriosactividadesdocenteposgrado.view, name='adm_criteriosactividadesdocenteposgrado_view'),

]
