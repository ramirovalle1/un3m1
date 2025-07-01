from django.contrib import admin
from .models import *
from sga.funciones import ModeloBase
from django import forms
from sga.admin import ModeloBaseAdmin
from sagest.admin import ModeloBaseTabularAdmin


class InformacionAdmin(ModeloBaseAdmin):
    list_display = ('get_tipo_display', 'informacion', 'mostrar', 'servicio',)
    search_fields = ('informacion', 'servicio',)
    # filter_horizontal = ('tipo',)


class ConfigInformacionExternoAdmin(ModeloBaseAdmin):
    list_display = ('fechaapertura', 'fechacierre', 'informacion', 'periodo', 'activo', 'agente_ok',)
    ordering = ('fechaapertura', 'fechacierre',)
    search_fields = ('informacion', 'periodo',)
    raw_id_fields = ('periodo', 'informacion', )
    # filter_horizontal = ('agenteregistro',)

class CategoriaEncuestaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'status', 'nombre', 'fecha_creacion', 'fecha_modificacion')
    ordering = ('fecha_creacion',)
    search_fields = ('nombre', )


admin.site.register(ConfigInformacionExterno, ConfigInformacionExternoAdmin)
admin.site.register(Informacion, InformacionAdmin)
admin.site.register(CategoriaEncuesta, CategoriaEncuestaAdmin)
