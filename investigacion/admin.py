from django.contrib import admin

from investigacion.models import TipoRecursoPresupuesto, IndustriaPriorizada, ZonaPlanificacion, \
    TipoResultadoCompromiso, ConvocatoriaProyecto, ConvocatoriaMontoFinanciamiento, ConvocatoriaProgramaInvestigacion, \
    Periodocidad, Categoria, GrupoInvestigacion, ConvocatoriaObraRelevancia, RubricaObraRelevancia, RubricaObraRelevanciaConvocatoria, ObraRelevanciaEvaluador, GrupoInvestigacionRequisitoIntegrante, CriterioEvaluacionInvestigacion, PeriodoEvaluacionInvestigacion, ConvocatoriaTipoRecurso, \
    InstitucionConvenio, TurnoCita, Gestion, ServicioGestion, CriterioDocenteInvitado
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

# Tipos de Recursos de Presupuesto
class TipoRecursoPresupuestoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'abreviatura', 'orden', 'vigente')
    ordering = ('descripcion', 'orden')
    search_fields = ('descripcion', )


class IndustriaPriorizadaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'tipo', 'nombre', 'orden', 'vigente')
    ordering = ('nombre', 'orden')
    search_fields = ('nombre',)


class ZonaPlanificacionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'numero', 'nombre', 'miembroszona')
    ordering = ('numero', 'nombre')
    search_fields = ('nombre', 'miembroszona', )


class TipoResultadoCompromisoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'numero', 'fijo', 'convocatoria')
    ordering = ('numero', 'descripcion')
    search_fields = ('descripcion', )


class PeriodocidadAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'valor', 'tipo')
    ordering = ('descripcion',)
    search_fields = ('descripcion', )


class CategoriaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'numero', 'vigente', 'tipo', )
    ordering = ('numero',)
    search_fields = ('descripcion', )


class GrupoInvestigacionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'vigente',)
    ordering = ('nombre',)
    search_fields = ('nombre', )


class ConvocatoriaProyectoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'apertura', 'cierre')
    ordering = ('id', 'descripcion', 'apertura', 'cierre')
    search_fields = ('descripcion', )


class ConvocatoriaMontoFinanciamientoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'tipoproyecto', 'tipoequipamiento', 'maximo', 'porcentajecompra', 'convocatoria')
    ordering = ('id', )
    # search_fields = ('descripcion', )


class ConvocatoriaProgramaInvestigacionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'programainvestigacion', 'convocatoria')
    ordering = ('id', )


class ConvocatoriaTipoRecursoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'convocatoria', 'tiporecurso', 'secuencia')
    ordering = ('id', 'convocatoria')
    search_fields = ('convocatoria', )


class ConvocatoriaObraRelevanciaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'iniciopos', 'finpos', 'publicada')
    ordering = ('id', 'descripcion', 'iniciopos', 'finpos')
    search_fields = ('descripcion', )


class RubricaObraRelevanciaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'vigente')
    ordering = ('id', 'descripcion',)
    search_fields = ('descripcion', )


class RubricaObraRelevanciaConvocatoriaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'convocatoria', 'rubrica', 'secuencia')
    ordering = ('id',)
    search_fields = ('rubrica', )


class ObraRelevanciaEvaluadorAdmin(ModeloBaseAdmin):
    list_display = ('id', 'obrarelevancia', 'persona', 'tipo')
    ordering = ('obrarelevancia',)
    search_fields = ('obrarelevancia',)


class GrupoInvestigacionRequisitoIntegranteAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'vigente')
    ordering = ('descripcion',)
    search_fields = ('descripcion', )


class CriterioEvaluacionInvestigacionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'numero', 'descripcion', 'medioverificacion', 'tipo')
    ordering = ('id', 'numero', 'descripcion',)
    search_fields = ('descripcion', )


class PeriodoEvaluacionInvestigacionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'periodo', 'vigente')
    ordering = ('id', 'periodo')
    search_fields = ('periodo', )


class InstitucionConvenioAdmin(ModeloBaseAdmin):
    list_display = ('id', 'origen', 'nombre', 'tipo')
    ordering = ('id', 'nombre')
    search_fields = ('nombre',)


class TurnoCitaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'orden', 'comienza', 'termina')
    ordering = ('id', 'orden')
    search_fields = ('orden',)


class GestionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'nombre', 'responsable', 'abreviatura')
    ordering = ('id', 'nombre')
    search_fields = ('nombre',)


class ServicioGestionAdmin(ModeloBaseAdmin):
    list_display = ('id', 'gestion', 'nombre', 'descripcion', 'abreviatura', 'tipo')
    ordering = ('id', 'nombre')
    search_fields = ('nombre',)


class CriterioDocenteInvitadoAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion')
    ordering = ('id', 'descripcion')
    search_fields = ('descripcion',)


admin.site.register(TipoRecursoPresupuesto, TipoRecursoPresupuestoAdmin)
admin.site.register(IndustriaPriorizada, IndustriaPriorizadaAdmin)
admin.site.register(ZonaPlanificacion, ZonaPlanificacionAdmin)
admin.site.register(TipoResultadoCompromiso, TipoResultadoCompromisoAdmin)
admin.site.register(ConvocatoriaProyecto, ConvocatoriaProyectoAdmin)
admin.site.register(ConvocatoriaMontoFinanciamiento, ConvocatoriaMontoFinanciamientoAdmin)
admin.site.register(ConvocatoriaProgramaInvestigacion, ConvocatoriaProgramaInvestigacionAdmin)
admin.site.register(Periodocidad, PeriodocidadAdmin)
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(GrupoInvestigacion, GrupoInvestigacionAdmin)
admin.site.register(ConvocatoriaObraRelevancia, ConvocatoriaObraRelevanciaAdmin)
admin.site.register(RubricaObraRelevancia, RubricaObraRelevanciaAdmin)
admin.site.register(RubricaObraRelevanciaConvocatoria, RubricaObraRelevanciaConvocatoriaAdmin)
admin.site.register(ObraRelevanciaEvaluador, ObraRelevanciaEvaluadorAdmin)
admin.site.register(GrupoInvestigacionRequisitoIntegrante, GrupoInvestigacionRequisitoIntegranteAdmin)
admin.site.register(CriterioEvaluacionInvestigacion, CriterioEvaluacionInvestigacionAdmin)
admin.site.register(PeriodoEvaluacionInvestigacion, PeriodoEvaluacionInvestigacionAdmin)
admin.site.register(ConvocatoriaTipoRecurso, ConvocatoriaTipoRecursoAdmin)
admin.site.register(InstitucionConvenio, InstitucionConvenioAdmin)
admin.site.register(TurnoCita, TurnoCitaAdmin)
admin.site.register(Gestion, GestionAdmin)
admin.site.register(ServicioGestion, ServicioGestionAdmin)
admin.site.register(CriterioDocenteInvitado, CriterioDocenteInvitadoAdmin)
