from django.contrib import admin

from inno.models import NivelFormacionPac
from .models import *
from sga.funciones import ModeloBase
from django import forms
from sga.admin import ModeloBaseAdmin
from sagest.admin import ModeloBaseTabularAdmin
from sagest.models import TipoContrato

admin.site.register(NivelFormacionPac, ModeloBaseAdmin)
admin.site.register(TipoContrato, ModeloBaseAdmin)
admin.site.register(Convocatoria, ModeloBaseAdmin)
admin.site.register(ConvocatoriaTerminosCondiciones, ModeloBaseAdmin)
admin.site.register(Partida, ModeloBaseAdmin)
admin.site.register(PartidaAsignaturas, ModeloBaseAdmin)
admin.site.register(CriterioApelacion, ModeloBaseAdmin)
admin.site.register(FactorApelacion, ModeloBaseAdmin)
admin.site.register(ParametrosDisertacion, ModeloBaseAdmin)
admin.site.register(ModeloEvaluativoDisertacion, ModeloBaseAdmin)


class AspectosFactorModeloEvaluativosAdmin(ModeloBaseTabularAdmin):
    model = AspectosFactorModeloEvaluativos


class AAspectosModeloEvaluativosFormAdmin(forms.ModelForm):

    class Meta:
        model = AspectosModeloEvaluativos
        fields = '__all__'


class ModeloEvaluativoAspectosFactoresAdmin(ModeloBaseAdmin):
    form = AAspectosModeloEvaluativosFormAdmin
    inlines = [AspectosFactorModeloEvaluativosAdmin]
    list_display = ('modeloevaluativo','descripcion', 'peso',)
    ordering = ('modeloevaluativo','descripcion', 'peso')


class DetalleRequisitoCompetenciaFormAdmin(ModeloBaseTabularAdmin):
    model = DetalleRequisitoCompetencia


class RequisitoCompetenciaAdmin(ModeloBaseAdmin):
    #form = AAspectosModeloEvaluativosFormAdmin
    raw_id_fields = ('content_type',)
    inlines = [DetalleRequisitoCompetenciaFormAdmin]
    #list_display = ('modeloevaluativo','descripcion', 'peso',)
    #ordering = ('modeloevaluativo','descripcion', 'peso')

admin.site.register(AspectosModeloEvaluativos, ModeloEvaluativoAspectosFactoresAdmin)
admin.site.register(RequisitoCompetencia, RequisitoCompetenciaAdmin)
admin.site.register(ArmonizacionNomenclaturaTitulo,ModeloBaseAdmin)
