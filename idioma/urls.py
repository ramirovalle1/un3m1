from django.urls import re_path, include
from idioma import adm_idioma


urlpatterns = [
    re_path(r'^adm_idioma$', adm_idioma.view, name='adm_idioma_view'),
]