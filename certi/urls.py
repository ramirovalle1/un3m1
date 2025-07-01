from django.urls import re_path
from certi.views import p_valida_certificado, adm_certificados, alu_carnet, adm_carnet, pro_carnet, \
    alu_carnet_demo, p_valida_carnet_digital

urlpatterns = [
    re_path('^adm_certificados$', adm_certificados.view, name='certi_adm_certificados_view'),
    # re_path('^alu_certificados$', alu_certificados.view, name='certi_alu_certificados_view'),
    re_path('^p_valida_certificado$', p_valida_certificado.view, name='certi_p_valida_certificado_view'),
    re_path('^p_valida_carnet/digital$', p_valida_carnet_digital.view, name='certi_p_valida_carnet_view'),
    re_path('^alu_carnet$', alu_carnet.view, name='certi_alu_carnet_view'),
    re_path('^alu_carnet/demo$', alu_carnet_demo.view, name='certi_alu_carnet_demo_view'),
    re_path('^adm_carnet$', adm_carnet.view, name='certi_adm_carnet_view'),
    re_path('^pro_carnet$', pro_carnet.view, name='certi_doc_carnet_view'),
    #re_path('^adm_carnet/docente$', adm_carnet.view, name='certi_adm_carnet_docente_view'),
    #re_path('^adm_carnet/demo$', alu_carnet_demo.view, name='certi_adm_carnet_demo_view'),
]
