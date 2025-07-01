from django.contrib import admin
from admision.models import *

MANAGERS = (
    ('isaltosm', 'isaltosm@unemi.edu.ec'),
    ('kpalaciosz', 'kpalaciosz@unemi.edu.ec'),
    ('michaeloc_20', 'clockem@unemi.edu.ec'),
    ('ryseven', 'ryepezb1@unemi.edu.ec'),
    ('crodriguezn', 'crodriguezn@unemi.edu.ec'),
    ('ame_dam', 'jplacesc@unemi.edu.ec'),
    ('rviterib1', 'rviterib1@unemi.edu.ec'),
    ('isabel.gomez', 'igomezg@unemi.edu.ec '),
    ('cgomezm3', 'cgomezm3@unemi.edu.ec '),
    ('wgavilanesr', 'wgavilanesr@unemi.edu.ec '),
)


class ModeloBaseTabularAdmin(admin.TabularInline):
    exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion")


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


class CronogramaPeriodoAdmin(ModeloBaseTabularAdmin):
    model = CronogramaPeriodo


class PeriodoAdmin(ModeloBaseAdmin):
    inlines = [CronogramaPeriodoAdmin]
    list_display = ('periodo', 'nombre', 'inicio', 'fin', 'activo')
    ordering = ('inicio', 'fin', 'activo')
    search_fields = ('nombre',)
    list_filter = ('activo',)
    date_hierarchy = 'inicio'


# admin.site.register(Rubrica, ModeloBaseAdmin)
# admin.site.register(RubricaCriterio, ModeloBaseAdmin)
# admin.site.register(RubricaNivel, ModeloBaseAdmin)
# admin.site.register(RubricaRelleno, ModeloBaseAdmin)
# admin.site.register(AreaPreguntaEntrevista, ModeloBaseAdmin)
# admin.site.register(PreguntaEntrevista, ModeloBaseAdmin)
# admin.site.register(MatriculaProfesor, ModeloBaseAdmin)
# admin.site.register(CalificacionEntrevista, ModeloBaseAdmin)
admin.site.register(Periodo, PeriodoAdmin)
