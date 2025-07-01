from django.urls import re_path

from becadocente import adm_becadocente, pro_becadocente

urlpatterns = [
    re_path(r'^adm_becadocente$', adm_becadocente.view, name='becadocente_adm_becadocente_view'),
    re_path(r'^pro_becadocente$', pro_becadocente.view, name='becadocente_pro_becadocente_view'),
    ]
