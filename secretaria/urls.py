from django.urls import re_path
from secretaria.views import adm_secretaria

urlpatterns = [
    re_path('^adm_secretaria$', adm_secretaria.view, name='secretaria_adm_secretaria_view'),
    #re_path('^adm_carnet/demo$', alu_carnet_demo.view, name='certi_adm_carnet_demo_view'),
]
