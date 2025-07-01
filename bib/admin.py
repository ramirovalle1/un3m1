# -*- coding: latin-1 -*-
from django.contrib import admin
from bib.models import TipoDocumento, ReferenciaWeb, PrestamoDocumento, Documento, ConsultaBiblioteca, OtraBibliotecaVirtual, Idioma, \
    AreaConocimiento, EstadoIntegridad, TipoIngreso, NivelLibro
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


class ReferenciaWebAdmin(ModeloBaseAdmin):
    list_display = ('url', 'nombre', 'logo')
    ordering = ('url', 'nombre')
    search_fields = ('nombre',)


class OtraBibliotecaVirtualAdmin(ModeloBaseAdmin):
    list_display = ('url', 'nombre', 'logo', 'descripcion')
    ordering = ('url', 'nombre')
    search_fields = ('nombre', 'descripcion')


class ConsultaBibliotecaAdmin(ModeloBaseAdmin):
    list_display = ('fecha', 'hora', 'persona', 'busqueda')
    ordering = ('fecha', 'hora')
    search_fields = ('persona__apellido1', 'persona__apellido2', 'persona__nombres')


class PrestamoDocumentoAdmin(ModeloBaseAdmin):
    list_display = ('documento', 'persona', 'entregado', 'tiempo', 'responsableentrega', 'fechaentrega', 'horaentrega', 'recibido', 'responsablerecibido', 'fecharecibido', 'horarecibido')
    ordering = ('fechaentrega', 'horaentrega')
    search_fields = ('persona__apellido1', 'persona__apellido2', 'persona__nombres', 'documento__codigo', 'documento__nombre', 'documento__autor')


class DocumentoAdmin(ModeloBaseAdmin):
    list_display = ('codigo', 'nombre', 'autor', 'tipo', 'anno', 'emision', 'palabrasclaves', 'digital', 'fisico', 'copias')
    ordering = ('codigo', 'autor', 'tipo')
    search_fields = ('codigo', 'nombre', 'autor')


admin.site.register(EstadoIntegridad, ModeloBaseAdmin)
admin.site.register(TipoIngreso, ModeloBaseAdmin)
admin.site.register(NivelLibro, ModeloBaseAdmin)
admin.site.register(TipoDocumento, ModeloBaseAdmin)
admin.site.register(Idioma, ModeloBaseAdmin)
admin.site.register(AreaConocimiento, ModeloBaseAdmin)
admin.site.register(ReferenciaWeb, ReferenciaWebAdmin)
admin.site.register(OtraBibliotecaVirtual, OtraBibliotecaVirtualAdmin)
admin.site.register(ConsultaBiblioteca, ConsultaBibliotecaAdmin)
admin.site.register(PrestamoDocumento, PrestamoDocumentoAdmin)
admin.site.register(Documento, DocumentoAdmin)