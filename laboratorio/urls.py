from django.urls import re_path
from laboratorio import pro_laboratoriocronograma, adm_perfillaboratorio

urlpatterns = [
    re_path(r'^pro_laboratoriocronograma$', pro_laboratoriocronograma.view, name='pro_laboratoriocronograma_view'),
    re_path(r'^adm_perfillaboratorio$', adm_perfillaboratorio.view, name='adm_perfillaboratorio_view'),
]
