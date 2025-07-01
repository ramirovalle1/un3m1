# -*- coding: latin-1 -*-
from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple

from inno.models import SolicitudTutoriaIndividualTema, PeriodoAcademia, SolicitudTutoriaIndividual, \
    RegistroClaseTutoriaDocente, HorarioTutoriaAcademica, ProcesoSolicitudClaseDiferido, \
    TipoInconvenienteClaseDiferido, MotivoTipoInconvenienteClaseDiferido, ResponsableActaAdmision, \
    AsignaturaActaAdmision, PeriodoActaAdmision, RequisitoIngresoUnidadIntegracionCurricular, ConfiguracionCalculoMatricula, \
    PeriodoMalla, DetallePeriodoMalla, BecaPeriodoResumen

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


class HorarioTutoriaAcademicaAdmin(admin.ModelAdmin):
    list_display = ('profesor', 'periodo', 'turno', 'dia',)
    ordering = ('id',)
    search_fields = ('profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres', 'periodo__nombre', 'dia',)
    fields = ('profesor', 'periodo', 'turno', 'dia',)
    raw_id_fields = ('profesor', 'turno', 'periodo',)


class RegistroClaseTutoriaDocenteAdmin(admin.ModelAdmin):
    list_display = ('horario', 'fecha', 'numerosemana','tipotutoria','profesor','periodo',)
    ordering = ('horario', 'fecha', 'numerosemana','tipotutoria')
    search_fields = ('horario__profesor__persona__nombres','horario__profesor__persona__apellido1','horario__profesor__persona__apellido2', 'fecha', 'numerosemana','profesor__persona__nombres','profesor__persona__apellido1','profesor__persona__apellido2',)
    fields = ('horario', 'fecha', 'numerosemana','tipotutoria','status','profesor','periodo',)
    raw_id_fields = ('horario','profesor','periodo',)


class SolicitudTutoriaIndividualAdmin(admin.ModelAdmin):
    list_display = ('horario', 'profesor','materiaasignada','estado','fechasolicitud')
    ordering = ('horario', 'profesor',)
    search_fields = ('profesor__persona__nombres','profesor__persona__apellido1','profesor__persona__apellido2', 'materiaasignada__matricula__inscripcion__persona__nombres','materiaasignada__matricula__inscripcion__persona__apellido1','materiaasignada__matricula__inscripcion__persona__apellido2',)
    fields = ('horario', 'profesor', 'materiaasignada','estado','fechatutoria','tutoriacomienza','tutoriatermina','status',)
    readonly_fields = ['id', 'materiaasignada']

    def idmateria(self,obj):
        return '%s' % (obj.materiaasignada_id)


class SolicitudTutoriaIndividualTemaAdmin(admin.ModelAdmin):
    list_display = ('solicitud', 'tema',)
    ordering = ('solicitud', 'tema',)
    search_fields = ('solicitud', 'tema',)
    fields = ('solicitud', 'tema',)


class PeriodoAcademiaAdmin(admin.ModelAdmin):
    list_display = ('periodo', 'fecha_limite_horario_tutoria', 'version_cumplimiento_recurso', 'cierra_materia',)
    ordering = ('periodo',)
    search_fields = ('periodo__nombre',)
    raw_id_fields = ('periodo',)
    fields = ('status', 'periodo', 'fecha_limite_horario_tutoria', 'version_cumplimiento_recurso', 'cierra_materia', 'tipo_modalidad')


class ProcesoSolicitudClaseDiferidoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'version', 'num_dias', 'activo',)
    ordering = ('nombre', 'version', )
    filter_horizonal = ('tipos',)
    fields = ('nombre', 'version', 'num_dias', 'activo', 'tipos', )


class MotivoTipoInconvenienteClaseDiferidoAdmin(ModeloBaseTabularAdmin):
    model = MotivoTipoInconvenienteClaseDiferido


class TipoInconvenienteClaseDiferidoAdmin(ModeloBaseAdmin):
    inlines = [MotivoTipoInconvenienteClaseDiferidoAdmin]
    list_display = ('nombre', 'activo', )
    ordering = ('nombre',)
    # list_filter = ('categoria', 'grupos')



class ResponsableActaAdmisionAdmin(ModeloBaseAdmin):
    # inlines = [MotivoTipoInconvenienteClaseDiferidoAdmin]
    list_display = ('persona', 'tipoprofesor', 'tipo', 'cargo', )
    raw_id_fields = ('persona',)
    # ordering = ('nombre',)
    list_filter = ('tipo',)

class AsignaturaActaAdmisionInline(ModeloBaseTabularAdmin):
    model = AsignaturaActaAdmision.responsables.through

class AsignaturaActaAdmisionAdmin(ModeloBaseAdmin):
    inlines = [AsignaturaActaAdmisionInline]
    # model = AsignaturaActaAdmision
    exclude = ('responsables',)
    list_display = ('asignatura', 'get_responsables')
    raw_id_fields = ('asignatura',)
    # ordering = ('nombre',)
    # list_filter = ('categoria', 'grupos')
    def get_responsables(self, obj):
        return str([o.__str__() for o in obj.responsables.all()])


class AsignaturaActaAdmisionInline(ModeloBaseTabularAdmin):
    model = PeriodoActaAdmision.responsablesasignaturas.through


class PeriodoActaAdmisionAdmin(ModeloBaseAdmin):
    # inlines = (
    #     AsignaturaActaAdmisionInline,
    #            )
    list_display = ('periodo', 'get_responsablesasignaturas',)
    raw_id_fields = ('periodo',)
    exclude = ('responsablesasignaturas',)
    # ordering = ('nombre',)
    # list_filter = ('categoria', 'grupos')

    def get_responsablesasignaturas(self, obj):
        return str([o.__str__() for o in obj.responsablesasignaturas.all()])


class RequisitoIngresoUnidadIntegracionCurricularAdmin(ModeloBaseAdmin):
    list_display = ('asignaturamalla', 'orden', 'requisito', 'activo', 'obligatorio')
    raw_id_fields = ('asignaturamalla',)

class ConfiguracionCalculoMatriculaAdmin(ModeloBaseAdmin):
    list_display = ('presupuesto', 'tipocalculo', 'totalestudiante', 'anio', 'semestre_anio')
    ordering = ('anio',)

class DetallePeriodoMallaAdminInline(ModeloBaseTabularAdmin):
    model = DetallePeriodoMalla

class PeriodoMallaAdmin(ModeloBaseAdmin):
    inlines = [DetallePeriodoMallaAdminInline]
    list_display = ('tipocalculo', 'periodo', 'malla', 'configuracion')
    raw_id_fields = ('periodo','malla')

class BecaPeriodoResumenAdmin(ModeloBaseAdmin):
    list_display = ('periodo', 'matriculados', 'matriculados_regulares', 'preseleccionados_becas', 'preseleccionados_becasaceptados', 'preseleccionados_becasadjudicados', 'preseleccionados_becaspagados')
    raw_id_fields = ('periodo',)


admin.site.register(HorarioTutoriaAcademica, HorarioTutoriaAcademicaAdmin)
admin.site.register(RegistroClaseTutoriaDocente, RegistroClaseTutoriaDocenteAdmin)
admin.site.register(SolicitudTutoriaIndividual, SolicitudTutoriaIndividualAdmin)
admin.site.register(SolicitudTutoriaIndividualTema, SolicitudTutoriaIndividualTemaAdmin)
admin.site.register(PeriodoAcademia, PeriodoAcademiaAdmin)
admin.site.register(ProcesoSolicitudClaseDiferido, ProcesoSolicitudClaseDiferidoAdmin)
admin.site.register(TipoInconvenienteClaseDiferido, TipoInconvenienteClaseDiferidoAdmin)
admin.site.register(ResponsableActaAdmision, ResponsableActaAdmisionAdmin)
admin.site.register(AsignaturaActaAdmision, AsignaturaActaAdmisionAdmin)
admin.site.register(PeriodoActaAdmision, PeriodoActaAdmisionAdmin)
admin.site.register(RequisitoIngresoUnidadIntegracionCurricular, RequisitoIngresoUnidadIntegracionCurricularAdmin)
admin.site.register(ConfiguracionCalculoMatricula, ConfiguracionCalculoMatriculaAdmin)
admin.site.register(PeriodoMalla, PeriodoMallaAdmin)
admin.site.register(BecaPeriodoResumen, BecaPeriodoResumenAdmin)
