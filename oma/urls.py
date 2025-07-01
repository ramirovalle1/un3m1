from django.urls import re_path
from oma import oma_curso, oma_modelosevaluativos

urlpatterns = [
    re_path(r'^oma_curso$', oma_curso.view, name='oma_curso_view'),
    re_path(r'^oma_modelosevaluativos$', oma_modelosevaluativos.view, name='oma_modelosevaluativos_view'),
]