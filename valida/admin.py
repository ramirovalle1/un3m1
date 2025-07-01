from django.contrib import admin

# from valida.models import Blockchain, Block, ValidarCertificacion
#
# admin.site.register(Blockchain)
# admin.site.register(Block)
#
#
# class ModeloBaseTabularAdmin(admin.TabularInline):
#     exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion")
#
#
# class ValidarCertificaciondmin(admin.ModelAdmin):
#     list_display = ('app_label', 'content_type', 'object_id', 'url', 'verificador', 'encadenado')
#     ordering = ('encadenado',)
#     search_fields = ('persona',)
#
#
# admin.site.register(ValidarCertificacion, ValidarCertificaciondmin)