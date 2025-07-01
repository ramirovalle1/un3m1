from django.contrib import admin

# Register your models here.
from directivo.models import (ManualFuncion, ManualFuncionActividad, RequisitoSancion, MotivoSancion,
                               RequisitoMotivoSancion, PuntoControl, FaltaDisciplinaria, ResponsableFirma)
from sga.admin import ModeloBaseAdmin

class PuntoControlAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre')
class MotivoSancionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre')
class RequisitoSancionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'tiporequisto')
class RequisitoMotivoSancionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'requisito', 'motivo', 'activo', 'obligatorio')

class FaltaDisciplinariaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'status')

class ResponsableFirmaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'persona','status')

admin.site.register(PuntoControl, PuntoControlAdmin)
admin.site.register(MotivoSancion, MotivoSancionAdmin)
admin.site.register(RequisitoSancion, RequisitoSancionAdmin)
admin.site.register(RequisitoMotivoSancion, RequisitoMotivoSancionAdmin)
admin.site.register(FaltaDisciplinaria, FaltaDisciplinariaAdmin)
admin.site.register(ResponsableFirma, ResponsableFirmaAdmin)