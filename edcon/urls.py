from django.urls import re_path

from edcon import pro_solicitudanteproyecto, adm_gestionsolicitudanteproyecto


urlpatterns = [
    re_path(r'^edcon_pro_solicitudanteproyecto$', pro_solicitudanteproyecto.view, name='pro_solicitudanteproyecto'),
    re_path(r'^edcon_adm_gestionsolicitudanteproyecto$', adm_gestionsolicitudanteproyecto.view, name='adm_gestionsolicitudanteproyecto'),
]