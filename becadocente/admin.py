from django.contrib import admin
from becadocente.models import Requisito, Rubro, RubroConvocatoria, Documento, DocumentoConvocatoria, IntegranteComite
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


class RequisitoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'vigente')
    ordering = ('descripcion',)
    search_fields = ('descripcion', )


class RubroAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'vigente')
    ordering = ('descripcion',)
    search_fields = ('descripcion', )


class RubroConvocatoriaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'convocatoria', 'rubro', 'secuencia')
    ordering = ('secuencia',)
    search_fields = ('rubro', )


class DocumentoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'vigente')
    ordering = ('descripcion',)
    search_fields = ('descripcion', )


class DocumentoConvocatoriaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'convocatoria', 'documento')
    ordering = ('id',)
    search_fields = ('documento', )


admin.site.register(Requisito, RequisitoAdmin)
admin.site.register(Rubro, RubroAdmin)
admin.site.register(RubroConvocatoria, RubroConvocatoriaAdmin)
admin.site.register(Documento, DocumentoAdmin)
admin.site.register(DocumentoConvocatoria, DocumentoConvocatoriaAdmin)
