from django.urls import re_path
from admision.views import adm_admision_panel, adm_admision_periodo_postulacion, adm_admision_test_vocacional

urlpatterns = [
    re_path(r'^nivelacion_admision$', adm_admision_panel.view, name='view_nivelacion_admision_panel'),
    re_path(r'^nivelacion_admision/periodo_postulacion$', adm_admision_periodo_postulacion.view, name='view_nivelacion_admision_periodo_postulacion'),
    re_path(r'^nivelacion_admision/test_vocacional$', adm_admision_test_vocacional.view, name='view_nivelacion_admision_test_vocacional'),
]
