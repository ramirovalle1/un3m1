from django.urls import re_path
from feria import adm_feria
from feria import solicitudes

urlpatterns = [
    re_path(r'^adm_feria$', adm_feria.view, name='adm_feria_view'),
    re_path(r'^adm_feria/solicitudes$', solicitudes.view, name='adm_solicitud_view'),
]
