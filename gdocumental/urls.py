from django.urls import re_path
from gdocumental import adm_firmaec, adm_gestiondocumental, adm_archivosdepartamentales, adm_firmardocumentos, adm_firmardocumentos_superuser

urlpatterns = [
    re_path(r'^adm_firmardocumentosec$', adm_firmaec.view, name='adm_firmardocumentos'),
    re_path(r'^adm_firmardocumentos$', adm_firmardocumentos.view, name='adm_firmardocumentos'),
    re_path(r'^adm_firmardocumentosfecha$', adm_firmardocumentos_superuser.view, name='adm_firmardocumentosfecha'),
    re_path(r'^adm_archivosdepartamentales$', adm_archivosdepartamentales.view, name='adm_archivosdepartamentales'),
    re_path(r'^adm_gestiondocumental$', adm_gestiondocumental.view, name='adm_gestiondocumental'),
]
