from django.contrib import admin
from .models import *
from sga.funciones import ModeloBase
from django import forms
from sga.admin import ModeloBaseAdmin
from sagest.admin import ModeloBaseTabularAdmin

# class CursoAdmin(ModeloBaseAdmin):
#     list_display = ('nombre', 'codigo', 'fecha_inicio', 'fecha_fin','modeloevaluativo','','status',)
#     search_fields = ('descripcion',)
#
# class AsignaturaCursoAdmin(ModeloBaseAdmin):
#     list_display = ('periodo', 'nombre', 'idcursomoodle', 'fecinicio','horainicio','fecfin','horafin','cupo','orden','status',)
#     search_fields = ('nombre',)
#
# class InscripcionCursoAdmin(ModeloBaseAdmin):
#     list_display = ('grupo', 'inscripcion', 'estado','status',)
#     search_fields = ('inscripcion__persona__cedula','inscripcion__persona__apellido1','inscripcion__persona__apellido2','inscripcion__persona__nombres',)

class DetalleModeloEvaluativoAdmin(ModeloBaseAdmin):
    list_display = ('modelo', 'nombre', 'notaminima', 'notamaxima', 'decimales')
    ordering = ('modelo', 'orden',)
    list_filter = ('modelo',)

admin.site.register(Curso, ModeloBaseAdmin)
admin.site.register(AsignaturaCurso, ModeloBaseAdmin)
admin.site.register(InscripcionCurso, ModeloBaseAdmin)
admin.site.register(AsignaturaInscripcionCurso, ModeloBaseAdmin)
admin.site.register(ModeloEvaluativo, ModeloBaseAdmin)
admin.site.register(DetalleModeloEvaluativo, DetalleModeloEvaluativoAdmin)