from django.contrib import admin
from matricula.models import PeriodoMatricula, MotivoMatriculaEspecial, CasoUltimaMatricula, ArticuloUltimaMatricula, ConfiguracionUltimaMatricula

from sga.admin import MANAGERS



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

    def has_module_permission(self, request):
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


class PeriodoMatriculaAdmin(ModeloBaseAdmin):
    # search_fields = ['periodo__nombre', ]
    # list_display = ['periodo__nombre', 'periodo__inicio', 'periodo__fin', 'periodo__activo', 'periodo__matriculacionactiva', 'get_tipo_display',]
    list_display = ('periodo', 'get_tipo_display', )
    ordering = ('periodo__anio', )
    search_fields = ('periodo__nombre', 'periodo__anio', )
    list_filter = ('periodo__anio', )
    # date_hierarchy = 'fecha'
    raw_id_fields = ('periodo',)


class MotivoMatriculaEspecialAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'get_tipo_display', 'activo',)
    ordering = ('nombre',)
    list_filter = ('tipo',)


class CasoUltimaMatriculaAdmin(ModeloBaseTabularAdmin):
    model = CasoUltimaMatricula


class ArticuloUltimaMatriculaAdmin(ModeloBaseAdmin):
    inlines = [CasoUltimaMatriculaAdmin]
    list_display = ('descripcion', 'activo')
    ordering = ('descripcion',)
    search_fields = ('descripcion',)


class ConfiguracionUltimaMatriculaAdmin(ModeloBaseAdmin):
    list_display = ('tipo', 'nombre', 'activo')
    ordering = ('tipo',)
    search_fields = ('tipo', 'nombre',)


admin.site.register(PeriodoMatricula, PeriodoMatriculaAdmin)
admin.site.register(MotivoMatriculaEspecial, MotivoMatriculaEspecialAdmin)
admin.site.register(ArticuloUltimaMatricula, ArticuloUltimaMatriculaAdmin)
admin.site.register(ConfiguracionUltimaMatricula, ConfiguracionUltimaMatriculaAdmin)
