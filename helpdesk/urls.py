from django.urls import re_path
from helpdesk import adm_hdincidente, adm_hdusuario, adm_hdagente,adm_planificacion,aprobar_planificacion,solicitud_aprobacion,aprobar_planificacion_v, pro_solicitudcopia, adm_gestionsolicitudcopia, adm_bodegainventario

urlpatterns = [#Help Desk
               re_path(r'^helpdesk_hdincidente$', adm_hdincidente.view, name=u'helpdesk_adm_hdincidente_view'),
               re_path(r'^helpdesk_hdusuario$', adm_hdusuario.view, name=u'helpdesk_adm_hdusuario_view'),
               re_path(r'^helpdesk_hdagente$', adm_hdagente.view, name=u'helpdesk_adm_hdagente_view'),
               re_path(r'^helpdesk_hdplanificacion$', adm_planificacion.view, name=u'helpdesk_adm_planificacion_view'),
               re_path(r'^helpdesk_hdaprobar$', aprobar_planificacion.view, name=u'helpdesk_hdaprobar_view'),
               re_path(r'^helpdesk_hdaprobarv$', aprobar_planificacion_v.view, name=u'helpdesk_hdaprobarv_view'),
               re_path(r'^helpdesk_hdsolicitud$', solicitud_aprobacion.view, name=u'helpdesk_hdaprobar_view'),
               # Solicitud Copias
               re_path(r'^helpdesk_pro_solicitudcopia$', pro_solicitudcopia.view, name=u"helpdesk_pro_solicitudcopia_view"),
               re_path(r'^helpdesk_adm_gestionsolicitudcopia$', adm_gestionsolicitudcopia.view, name=u"helpdesk_adm_gestionsolicitudcopia_view"),
               # bodega inventario
               re_path(r'^helpdesk_adm_bodegainventario$', adm_bodegainventario.view, name=u"helpdesk_adm_bodegainventario_view"),
]
