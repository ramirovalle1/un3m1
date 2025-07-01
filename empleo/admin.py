from django.contrib import admin

from inno.models import NivelFormacionPac
from .models import *
from sga.funciones import ModeloBase
from django import forms
from sga.admin import ModeloBaseAdmin
from sagest.admin import ModeloBaseTabularAdmin
from sagest.models import TipoContrato

# admin.site.register(NivelFormacionPac, ModeloBaseAdmin)
# admin.site.register(TipoContrato, ModeloBaseAdmin)
admin.site.register(OfertaLaboralEmpresa, ModeloBaseAdmin)

