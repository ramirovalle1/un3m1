from django.contrib import admin
from .models import *
from sga.funciones import ModeloBase
from django import forms
from sga.admin import ModeloBaseAdmin
from sagest.admin import ModeloBaseTabularAdmin


class PasoProcesoAdmin(ModeloBaseTabularAdmin):
    model = PasoProcesoPago


class ConfiguracionProcesoPago(ModeloBaseAdmin):
    inlines = [PasoProcesoAdmin]
    list_display = ('version', 'nombre', 'mostrar')
    ordering = ('nombre', '-version')
    search_fields = ('nombre',)
class PlantillaInformeAdmin(ModeloBaseAdmin):
    list_display= ('nombre','tipo','archivo','vigente','anio')
    ordering = ('nombre',)
    search_files = ('nombre',)
admin.site.register(RequisitoPagoDip, ModeloBaseAdmin)
admin.site.register(PerfilPuestoDip, ModeloBaseAdmin)
admin.site.register(ProcesoPago, ConfiguracionProcesoPago)
admin.site.register(RequisitoPasoPago, ModeloBaseAdmin)
admin.site.register(PlantillaInformes,PlantillaInformeAdmin)
