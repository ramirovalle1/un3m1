from django.contrib import admin
from .models import *
from sga.funciones import ModeloBase
from django import forms
from sga.admin import ModeloBaseAdmin
from sagest.admin import ModeloBaseTabularAdmin

class ListaGremioAdmin(ModeloBaseTabularAdmin):
    model = ListaGremio

class GremioPeriodoAdmin(ModeloBaseAdmin):
    inlines = [ListaGremioAdmin]
    list_display = ( 'periodo','gremio','tipo', 'coordinacion')
    ordering = ('gremio', '-periodo')
    search_fields = ('gremio__nombre', 'coordinacion__nombre', 'tipo')

class DetalleMesaAdmin(ModeloBaseTabularAdmin):
    model = DetalleMesa


class ConfiguracionMesaFormAdmin(forms.ModelForm):

    class Meta:
        model = ConfiguracionMesaResponsable
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ConfiguracionMesaFormAdmin, self).__init__(*args, **kwargs)
        self.fields['presidente'].queryset = DetPersonaPadronElectoral.objects.filter(status=True, enmesa=True).order_by('persona__apellido1','persona__apellido2','persona__nombres')
        self.fields['secretario'].queryset = DetPersonaPadronElectoral.objects.filter(status=True, enmesa=True).order_by('persona__apellido1','persona__apellido2','persona__nombres')
        self.fields['vocal'].queryset = DetPersonaPadronElectoral.objects.filter(status=True, enmesa=True).order_by('persona__apellido1','persona__apellido2','persona__nombres')

class ConfiguracionMesaResponsableAdmin(ModeloBaseAdmin):
    form = ConfiguracionMesaFormAdmin
    inlines = [DetalleMesaAdmin]
    list_display = ('mesa', 'periodo', 'tipo', 'presidente', 'secretario', 'vocal')
    ordering = ('mesa', '-periodo')
    search_fields = ('periodo__nombre', 'mesa__nombre', 'tipo')
    raw_id_fields = ('persona_cierre', 'mesa')

class SubDetalleMesaAdmin(ModeloBaseTabularAdmin):
    model = SubDetalleMesa



admin.site.register(MesasPadronElectoral, ModeloBaseAdmin)
admin.site.register(ListaElectoral, ModeloBaseAdmin)
admin.site.register(GremioElectoral, ModeloBaseAdmin)
admin.site.register(GremioPeriodo, GremioPeriodoAdmin)
admin.site.register(ConfiguracionMesaResponsable, ConfiguracionMesaResponsableAdmin)