from django.contrib import admin
from .models import *
from sga.funciones import ModeloBase
from django import forms
from sga.admin import ModeloBaseAdmin
from sagest.admin import ModeloBaseTabularAdmin

class PeriodoAdmin(ModeloBaseAdmin):
    list_display = ('idioma', 'descripcion', 'fecinicioinscripcion', 'fecfininscripcion','estado','status',)
    search_fields = ('descripcion',)

class GrupoAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'nombre', 'idcursomoodle', 'fecinicio','horainicio','fecfin','horafin','cupo','orden','status',)
    search_fields = ('nombre',)

class GrupoInscripcionAdmin(ModeloBaseAdmin):
    list_display = ('grupo', 'inscripcion', 'estado','status',)
    search_fields = ('inscripcion__persona__cedula','inscripcion__persona__apellido1','inscripcion__persona__apellido2','inscripcion__persona__nombres',)

admin.site.register(Periodo, PeriodoAdmin)
admin.site.register(Grupo,GrupoAdmin)
admin.site.register(GrupoInscripcion,GrupoInscripcionAdmin)