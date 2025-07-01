from django.contrib import admin
from med.models import PersonaEducacion, PersonaProfesion, IndicadorSobrepeso, InventarioMedico, InventarioMedicoLote, \
    Enfermedad, Parentesco, Cirugia, Vacuna, Alergia, TipoEnfermedad, LugarAnatomico, MetodoAnticonceptivo, Droga, Lesiones, \
    TipoActividad, TipoServicioBienestar, PsicologicoPreguntasBancoEscala, PsicologicoPreguntasBanco, \
    TestPsicologicoCalculoDiagnostico

from settings import MANAGERS


class ModeloBaseAdmin(admin.ModelAdmin):

    def get_actions(self, request):
        actions = super(ModeloBaseAdmin, self).get_actions(request)
        if request.user.username not in [x[0] for x in MANAGERS]:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return request.user.username in [x[0] for x in MANAGERS]

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.username in [x[0] for x in MANAGERS]

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion")
        form = super(ModeloBaseAdmin, self).get_form(request, obj, **kwargs)
        return form

    def save_model(self, request, obj, form, change):
        if request.user.username not in [x[0] for x in MANAGERS]:
            raise Exception('Sin permiso a modificacion')
        else:
            obj.save(request)


class PersonaEstadoCivilAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    ordering = ('nombre',)
    search_fields = ('nombre',)


class PersonaEducacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    ordering = ('nombre',)
    search_fields = ('nombre',)


class PersonaProfesionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', )
    ordering = ('nombre',)
    search_fields = ('nombre',)


class IndicadorSobrepesoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'minimohombre', 'maximohombre', 'minimomujer', 'maximomujer')
    ordering = ('minimohombre',)
    search_fields = ('nombre',)


class InventarioMedicoAdmin(ModeloBaseAdmin):
    list_display = ('codigobarra', 'nombre', 'descripcion', 'tipo')
    ordering = ('codigobarra',)
    search_fields = ('nombre', 'descripcion')
    list_filter = ('nombre',)


class InventarioMedicoLoteAdmin(ModeloBaseAdmin):
    list_display = ('inventariomedico', 'numero', 'fechaelabora', 'fechavence', 'costo', 'cantidad')
    ordering = ('-fechavence',)
    search_fields = ('numero', 'inventariomedico__nombre', 'inventariomedico__descripcion')


class EnfermedadAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class ParentescoAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class VacunaAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class AlergiaAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class TipoEnfermedadAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class CirugiaAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class LugarAnatomicoAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class MetodoAnticonceptivoAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class DrogaAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class LesionesAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class TipoActividadAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class TipoServicioBienestarAdmin(ModeloBaseAdmin):
    ordering = ('descripcion',)
    list_filter = ('descripcion',)


class PsicologicoPreguntasBancoEscalaAdmin(ModeloBaseAdmin):
    list_display = ('descripcion', 'leyenda')
    ordering = ('descripcion',)
    search_fields = ('descripcion',)


class PsicologicoPreguntasBancoAdmin(ModeloBaseAdmin):
    list_display = ('descripcion', 'leyenda')
    ordering = ('descripcion',)
    search_fields = ('descripcion',)


class TestPsicologicoCalculoDiagnosticoAdmin(ModeloBaseAdmin):
    list_display = ('test', 'nombreaccion')
    ordering = ('test',)
    search_fields = ('nombreaccion',)


admin.site.register(TipoServicioBienestar, TipoServicioBienestarAdmin)
admin.site.register(IndicadorSobrepeso, IndicadorSobrepesoAdmin)
admin.site.register(PersonaEducacion, PersonaEducacionAdmin)
admin.site.register(PersonaProfesion, PersonaProfesionAdmin)
admin.site.register(InventarioMedico, InventarioMedicoAdmin)
admin.site.register(InventarioMedicoLote, InventarioMedicoLoteAdmin)
admin.site.register(Vacuna, VacunaAdmin)
admin.site.register(Alergia, AlergiaAdmin)
admin.site.register(TipoEnfermedad, TipoEnfermedadAdmin)
admin.site.register(Enfermedad, EnfermedadAdmin)
admin.site.register(Parentesco, ParentescoAdmin)
admin.site.register(Cirugia, CirugiaAdmin)
admin.site.register(LugarAnatomico, LugarAnatomicoAdmin)
admin.site.register(MetodoAnticonceptivo, MetodoAnticonceptivoAdmin)
admin.site.register(Droga, DrogaAdmin)
admin.site.register(Lesiones, LesionesAdmin)
admin.site.register(TipoActividad, TipoActividadAdmin)
admin.site.register(PsicologicoPreguntasBancoEscala, PsicologicoPreguntasBancoEscalaAdmin)
admin.site.register(PsicologicoPreguntasBanco, PsicologicoPreguntasBancoAdmin)
admin.site.register(TestPsicologicoCalculoDiagnostico, TestPsicologicoCalculoDiagnosticoAdmin)
