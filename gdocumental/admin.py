from django.contrib import admin
from investigacion.admin import ModeloBaseAdmin
from .models import *

admin.site.register(DepartamentoArchivoDocumentos)
