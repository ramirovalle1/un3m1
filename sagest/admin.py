# -*- coding: UTF-8 -*-
from django import forms
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _

from helpdesk.models import BodegaPrimaria, BodegaKardex
from sagest.models import UnidadMedida, TipoProducto, Proveedor, Producto, DetalleIngresoProducto, IngresoProducto, \
    InventarioReal, \
    TipoDocumento, Departamento, CuentaContable, TipoCuentaContable, EstadoProducto, TipoProyecto, \
    TipoDocumentoRespaldo, ClaseDocumentoRespaldo, TipoBien, OrigenIngreso, Partida, SalidaProducto, \
    TipoPermiso, TipoPermisoDetalle, \
    CatalogoBien, MotivoSalida, OtroRegimenLaboral, DedicacionLaboral, \
    ActividadLaboral, DetalleEvaluacionRiesgo, EvaluacionRiesgo, AgenteRiesgoRiesgo, AgenteRiesgo, SubgrupoAgente, \
    GrupoAgente, RiesgoTrabajo, PlanAccionPreventiva, Bloque, SeccionDepartamento, TipoArriendo, \
    LugarContrato, UnidadMedidaPresupuesto, LugarRecaudacion, PuntoVenta, SecuenciaActivos, TrasladoMantenimiento, \
    TipoOtroRubro, IvaAplicado, FormaDePago, TipoCheque, TipoTransferencia, TipoTarjetaBanco, ProcesadorPagoTarjeta, \
    CuentaBanco, Pago, Factura, ProcedenciaTarjeta, Rubro, NotaCredito, Banco, TipoComprobanteRecaudacion, \
    NomencladorPresupuesto, TipoConceptoTransferenciaGobierno, TipoTramite, PodFactor, TipoArchivoPresupuestoObra, \
    SecuencialRecaudaciones, ComprobanteRecaudacion, CierreSesionCaja, PeriodoGastosPersonales, AccionesTramitePago, \
    TipoDocumentoTramitePago, TipoMovimientoConciliacion, Aseguradora, TipoRamo, MotivoAccionPersonal, \
    TipoAccionPersonal, IndiceGrupo, IndiceSesion, IndiceSerie, IndiceSeriePuesto, TramitePago, RenovacionKardex, \
    KardexVacacionesDetalle, FirmasComprobanteBodega, PeriodoRol, TipoParticipacionCongreso, TipoParticipante, Congreso, \
    PermisoInstitucional, OpcionSistema, EstadoSolicitud, TipoArchivoSolicitud, LogMarcada, LogDia, PeriodoPoa, \
    Informes, BitacoraActividadDiaria, TipoVacunaCovid, AnioEjercicio, PersonaDepartamentoFirmas, GrupoDepartamento

MANAGERS = (
    ('isaltosm', 'isaltosm@unemi.edu.ec'),
    ('kpalaciosz', 'kpalaciosz@unemi.edu.ec'),
    ('michaeloc_20', 'clockem@unemi.edu.ec'),
    ('ryseven', 'ryepezb1@unemi.edu.ec'),
    ('crodriguezn', 'crodriguezn@unemi.edu.ec'),
    ('ame_dam', 'jplacesc@unemi.edu.ec'),
    ('rviterib1', 'rviterib1@unemi.edu.ec'),
    ('isabel.gomez', 'igomezg@unemi.edu.ec '),
    ('wgavilanesr', 'wgavilanesr@unemi.edu.ec'),
    ('cgomezm3', 'cgomezm3@unemi.edu.ec '),
    ('jguachuns', 'jguachuns@unemi.edu.ec '),
    ('mleong2', 'mleong2@unemi.edu.ec '),
)
from sga.models import ConvenioPago, AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, \
    SubAreaEspecificaConocimientoTitulacion, VariablesGlobales, Persona, CuentaBancariaPersona, TipoRedPersona

from posgrado.models import InscripcionCohorte


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


admin.site.register(UnidadMedida, ModeloBaseAdmin)


class TipoProductoAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)

admin.site.register(TipoProducto, TipoProductoAdmin)

admin.site.register(TipoDocumento, ModeloBaseAdmin)

class TipoVacunaCovidAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


admin.site.register(TipoVacunaCovid, TipoVacunaCovidAdmin)


class ProveedorAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'alias', 'identificacion', 'pais', 'direccion', 'telefono', 'celular', 'email', 'fax')
    ordering = ('nombre',)
    search_fields = ('nombre', 'identificacion')


admin.site.register(Proveedor, ProveedorAdmin)


class ProductoAdmin(ModeloBaseAdmin):
    list_display = ('codigo', 'descripcion', 'unidadmedida', 'tipoproducto', 'codigobarra', 'alias', 'minimo', 'maximo')
    ordering = ('codigo', 'tipoproducto')
    search_fields = ('codigo', 'codigobarra', 'descripcion', 'tipoproducto__nombre', 'alias')


admin.site.register(Producto, ProductoAdmin)


class DetalleIngresoProductoAdmin(ModeloBaseAdmin):
    list_display = ('producto', 'cantidad', 'costo', 'subtotal', 'descuento', 'coniva', 'valoriva', 'total', 'estado')
    ordering = ('producto__codigo', 'producto__alias')
    search_fields = ('producto__nombre', 'producto__codigo')


admin.site.register(DetalleIngresoProducto, DetalleIngresoProductoAdmin)


class IngresoProductoAdmin(ModeloBaseAdmin):
    list_display = (
    'proveedor', 'tipodocumento', 'numerodocumento', 'fechadocumento', 'autorizacion', 'descripcion', 'fechaoperacion')
    ordering = ('proveedor__nombre', 'tipodocumento__nombre', 'fechadocumento', 'descripcion')
    search_fields = ('proveedor__nombre', 'tipodocumento__nombre', 'fechadocumento', 'descripcion')
    list_filter = ('proveedor', 'tipodocumento')


admin.site.register(IngresoProducto, IngresoProductoAdmin)


class InventarioRealAdmin(ModeloBaseAdmin):
    list_display = ('producto', 'cantidad', 'costo', 'valor')
    ordering = ('producto__codigo', 'producto__alias')
    search_fields = ('producto__nombre', 'producto__codigo')


admin.site.register(InventarioReal, InventarioRealAdmin)


class DepartamentoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'responsable')
    ordering = ('nombre', 'responsable')
    search_fields = ('nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')


admin.site.register(Departamento, DepartamentoAdmin)

class GrupoDepartamentoAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'alias')
    ordering = ('nombre', 'alias')
    search_fields = ('nombre', 'alias')


admin.site.register(GrupoDepartamento, GrupoDepartamentoAdmin)

class CuentaContableAdmin(ModeloBaseAdmin):
    list_display = ('cuenta', 'descripcion', 'naturaleza', 'tipo', 'asociaccosto')
    ordering = ('cuenta', 'tipo')
    search_fields = ('cuenta', 'descripcion', 'tipo__nombre')


class CaracteristicaTipobienAdmin(ModeloBaseAdmin):
    list_display = ('tipobien', 'caracteristica')
    ordering = ('tipobien', 'caracteristica')
    list_filter = ('tipobien',)


class TipoPermisoDetalleAdmin(ModeloBaseAdmin):
    list_display = ('tipopermiso', 'descripcion')
    ordering = ('tipopermiso', 'descripcion')
    search_fields = ('descripcion',)


class TipoPermisoAdmin(ModeloBaseAdmin):
    list_display = ('descripcion', 'observacion', 'regimenlaboral')
    ordering = ('regimenlaboral', 'descripcion')
    search_fields = ('descripcion',)


class TipoOtroRubroAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'partida', 'valor')
    ordering = ('nombre',)


class MyGroupAdminForm(forms.ModelForm):
    class Meta:
        model = AccionesTramitePago
        fields = '__all__'

    permiso = forms.ModelMultipleChoiceField(Permission.objects.exclude(name__startswith='Can'),
                                             widget=admin.widgets.FilteredSelectMultiple(_('permiso'), False),
                                             required=False)


class AccionesTramitePagoAdmin(admin.ModelAdmin):
    form = MyGroupAdminForm
    search_fields = ('permiso',)
    ordering = ('permiso',)

    def get_actions(self, request):
        actions = super(AccionesTramitePagoAdmin, self).get_actions(request)
        if request.user.username not in [x[0] for x in MANAGERS]:
            del actions['delete_selected']
        return actions

    def has_add_permission(self, request):
        return request.user.username in [x[0] for x in MANAGERS]

    def has_change_permission(self, request, obj=None):
        if request.user.username in [x[0] for x in MANAGERS]:
            pass
        else:
            self.readonly_fields = [x.name for x in self.model._meta.local_fields]
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.username in [x[0] for x in MANAGERS]

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("usuario_creacion", "fecha_creacion", "usuario_modificacion", "fecha_modificacion")
        form = super(AccionesTramitePagoAdmin, self).get_form(request, obj, **kwargs)
        return form

    def save_model(self, request, obj, form, change):
        if request.user.username not in [x[0] for x in MANAGERS]:
            raise Exception('Sin permiso a modificacion')
        else:
            return super(AccionesTramitePagoAdmin, self).save_model(request, obj, form, change)


class MotivoAccionPersonalAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


class TipoAccionPersonalAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


class IndiceGrupoAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


class IndiceSesionAdmin(ModeloBaseAdmin):
    list_display = ('indicegrupo', 'nombre')
    ordering = ('indicegrupo', 'nombre',)
    search_fields = ('indicegrupo', 'nombre',)


class IndiceSerieAdmin(ModeloBaseAdmin):
    list_display = ('indicesesion', 'nombre')
    ordering = ('indicesesion', 'nombre',)
    search_fields = ('indicesesion', 'nombre',)


class IndiceSeriePuestoAdmin(ModeloBaseAdmin):
    list_display = ('indiceserie', 'denominacionpuesto', 'escalaocupacional', 'tipogrado', 'codificacion', 'rmu')
    ordering = ('indiceserie', 'denominacionpuesto', 'escalaocupacional', 'tipogrado', 'codificacion', 'rmu')
    search_fields = ('indiceserie', 'denominacionpuesto', 'escalaocupacional', 'tipogrado', 'codificacion', 'rmu')


class AreaConocimientoTitulacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo','tipo','status',)
    ordering = ('nombre', 'codigo','tipo','status',)
    search_fields = ('nombre', 'codigo','tipo','status',)

class SubAreaConocimientoTitulacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'areaconocimiento','tipo','status',)
    ordering = ('nombre', 'codigo', 'areaconocimiento','tipo','status',)
    search_fields = ('nombre', 'codigo', 'areaconocimiento','tipo','status',)
    raw_id_fields = ('areaconocimiento',)

class SubAreaEspecificaConocimientoTitulacionAdmin(ModeloBaseAdmin):
    list_display = ('nombre', 'codigo', 'areaconocimiento','tipo','status',)
    ordering = ('nombre', 'codigo', 'areaconocimiento','tipo','status',)
    search_fields = ('nombre', 'codigo', 'areaconocimiento__nombre','tipo','status',)
    raw_id_fields = ('areaconocimiento',)

class VariablesGlobalesAdmin(ModeloBaseAdmin):
    list_display = ('referencia', 'descripcion', 'variable', 'tipodato', 'valor')
    ordering = ('referencia', 'variable')
    search_fields = ('referencia', 'variable')


class RenovacionKardexAdmin(ModeloBaseAdmin):
    list_display = ('fecharenovacion', 'cantdias')
    ordering = ('fecharenovacion', 'cantdias')
    search_fields = ('fecharenovacion', 'cantdias')


class KardexVacacionesDetalleAdmin(ModeloBaseAdmin):
    list_display = ('kardex', 'fecha', 'diasal', 'horasal', 'minsal')
    ordering = ('kardex', 'fecha')
    search_fields = ('kardex__persona__apellido1', 'kardex__persona__apellido2', 'kardex__persona__nombres')


class FirmasComprobanteBodegaAdmin(ModeloBaseAdmin):
    list_display = ('persona', 'tipo', 'fechainicio', 'fechafin', 'denominacionpuesto')
    ordering = ('fechainicio', 'tipo')
    search_fields = ('fechainicio', 'tipo')
    raw_id_fields = ('persona', 'denominacionpuesto',)


class PeriodoRolAdmin(ModeloBaseAdmin):
    list_display = ('anio', 'mes', 'tiporol', 'descripcion', 'estado')
    ordering = ('anio', 'mes')
    search_fields = ('descripcion', 'anio', 'mes')


class TipoParticipanteAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


class TipoParticipacionCongresoAdmin(ModeloBaseAdmin):
    list_display = ('congreso', 'tipoparticipante', 'valor', 'status',)
    ordering = ('tipoparticipante',)
    search_fields = ('tipoparticipante', 'congreso',)


class CongresoAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


class RubroAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


class InscripcionCohorteAdmin(ModeloBaseAdmin):
    list_display = ('inscripcionaspirante', 'cohortes',)
    ordering = ('inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2', 'cohortes',)
    search_fields = (
    'inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2', 'cohortes',)


class PermisoInstitucionalAdmin(ModeloBaseAdmin):
    list_display = ('secuencia', 'solicita',)
    ordering = ('secuencia', 'solicita',)
    search_fields = ('secuencia', 'solicita',)


admin.site.register(TipoParticipacionCongreso, TipoParticipacionCongresoAdmin)
admin.site.register(TipoParticipante, TipoParticipanteAdmin)
admin.site.register(Congreso, CongresoAdmin)

admin.site.register(PeriodoRol, PeriodoRolAdmin)
admin.site.register(CuentaContable, CuentaContableAdmin)
admin.site.register(TipoCuentaContable, ModeloBaseAdmin)
admin.site.register(EstadoProducto, ModeloBaseAdmin)

admin.site.register(VariablesGlobales, VariablesGlobalesAdmin)

# Talento Humano
admin.site.register(TipoPermiso, TipoPermisoAdmin)
admin.site.register(TipoPermisoDetalle, TipoPermisoDetalleAdmin)

# Activoa Fijoa
admin.site.register(TipoProyecto, ModeloBaseAdmin)
admin.site.register(DetalleEvaluacionRiesgo, ModeloBaseAdmin)
admin.site.register(EvaluacionRiesgo, ModeloBaseAdmin)
admin.site.register(AgenteRiesgoRiesgo, ModeloBaseAdmin)
admin.site.register(AgenteRiesgo, ModeloBaseAdmin)
admin.site.register(SubgrupoAgente, ModeloBaseAdmin)
admin.site.register(GrupoAgente, ModeloBaseAdmin)
admin.site.register(RiesgoTrabajo, ModeloBaseAdmin)
admin.site.register(TipoDocumentoRespaldo, ModeloBaseAdmin)
admin.site.register(ClaseDocumentoRespaldo, ModeloBaseAdmin)
admin.site.register(TipoBien, ModeloBaseAdmin)
admin.site.register(OrigenIngreso, ModeloBaseAdmin)
admin.site.register(Partida, ModeloBaseAdmin)
admin.site.register(SalidaProducto, ModeloBaseAdmin)
admin.site.register(MotivoSalida, ModeloBaseAdmin)
admin.site.register(PlanAccionPreventiva, ModeloBaseAdmin)
admin.site.register(OtroRegimenLaboral, ModeloBaseAdmin)
admin.site.register(DedicacionLaboral, ModeloBaseAdmin)
admin.site.register(Bloque, ModeloBaseAdmin)
admin.site.register(SeccionDepartamento, ModeloBaseAdmin)
admin.site.register(ActividadLaboral, ModeloBaseAdmin)
admin.site.register(CatalogoBien, ModeloBaseAdmin)
admin.site.register(UnidadMedidaPresupuesto, ModeloBaseAdmin)
admin.site.register(TipoArchivoPresupuestoObra, ModeloBaseAdmin)
admin.site.register(SecuenciaActivos, ModeloBaseAdmin)
admin.site.register(SecuencialRecaudaciones, ModeloBaseAdmin)
admin.site.register(ComprobanteRecaudacion, ModeloBaseAdmin)
admin.site.register(CierreSesionCaja, ModeloBaseAdmin)
admin.site.register(TrasladoMantenimiento, ModeloBaseAdmin)
admin.site.register(NomencladorPresupuesto, ModeloBaseAdmin)

# Recaudacion Contratos
admin.site.register(TipoArriendo, ModeloBaseAdmin)
admin.site.register(LugarContrato, ModeloBaseAdmin)
admin.site.register(LugarRecaudacion, ModeloBaseAdmin)
admin.site.register(PuntoVenta, ModeloBaseAdmin)
admin.site.register(TipoOtroRubro, TipoOtroRubroAdmin)
admin.site.register(IvaAplicado, ModeloBaseAdmin)
admin.site.register(FormaDePago, ModeloBaseAdmin)
admin.site.register(TipoCheque, ModeloBaseAdmin)
admin.site.register(TipoTransferencia, ModeloBaseAdmin)
admin.site.register(TipoTarjetaBanco, ModeloBaseAdmin)
admin.site.register(ProcedenciaTarjeta, ModeloBaseAdmin)
admin.site.register(ProcesadorPagoTarjeta, ModeloBaseAdmin)
admin.site.register(CuentaBanco, ModeloBaseAdmin)
admin.site.register(Pago, ModeloBaseAdmin)
admin.site.register(Rubro, ModeloBaseAdmin)
admin.site.register(Factura, ModeloBaseAdmin)
admin.site.register(NotaCredito, ModeloBaseAdmin)
admin.site.register(Banco, ModeloBaseAdmin)
admin.site.register(TipoComprobanteRecaudacion, ModeloBaseAdmin)
admin.site.register(TipoConceptoTransferenciaGobierno, ModeloBaseAdmin)
admin.site.register(TipoTramite, ModeloBaseAdmin)
admin.site.register(PodFactor, ModeloBaseAdmin)
admin.site.register(PeriodoGastosPersonales, ModeloBaseAdmin)
admin.site.register(TipoMovimientoConciliacion, ModeloBaseAdmin)
admin.site.register(TipoDocumentoTramitePago, ModeloBaseAdmin)
admin.site.register(TramitePago, ModeloBaseAdmin)
admin.site.register(Aseguradora, ModeloBaseAdmin)
admin.site.register(TipoRamo, ModeloBaseAdmin)
admin.site.register(ConvenioPago, ModeloBaseAdmin)
admin.site.register(AccionesTramitePago, AccionesTramitePagoAdmin)
admin.site.register(MotivoAccionPersonal, MotivoAccionPersonalAdmin)
admin.site.register(TipoAccionPersonal, TipoAccionPersonalAdmin)
admin.site.register(IndiceGrupo, IndiceGrupoAdmin)
admin.site.register(IndiceSesion, IndiceSesionAdmin)
admin.site.register(IndiceSerie, IndiceSerieAdmin)
admin.site.register(IndiceSeriePuesto, IndiceSeriePuestoAdmin)
admin.site.register(AreaConocimientoTitulacion, AreaConocimientoTitulacionAdmin)
admin.site.register(SubAreaConocimientoTitulacion, SubAreaConocimientoTitulacionAdmin)
admin.site.register(SubAreaEspecificaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacionAdmin)
# KARDEX RENOVACION
admin.site.register(RenovacionKardex, RenovacionKardexAdmin)
admin.site.register(KardexVacacionesDetalle, KardexVacacionesDetalleAdmin)
admin.site.register(FirmasComprobanteBodega, FirmasComprobanteBodegaAdmin)
admin.site.register(InscripcionCohorte, InscripcionCohorteAdmin)
admin.site.register(PermisoInstitucional, PermisoInstitucionalAdmin)
admin.site.register(BodegaPrimaria)


# OPCIONES DE SISTEMAS
class OpcionSistemaAdmin(ModeloBaseAdmin):
    list_display = ('modulo', 'descripcion')
    ordering = ('modulo', 'descripcion')
    search_fields = ('modulo', 'descripcion')


admin.site.register(OpcionSistema, OpcionSistemaAdmin)


# ESTADOS DE SOLICITUDES VARIAS
class EstadoSolicitudAdmin(ModeloBaseAdmin):
    list_display = ('id', 'opcion', 'descripcion', 'observacion', 'valor', 'clase')
    ordering = ('opcion', 'valor', 'descripcion')
    search_fields = ('opcion', 'descripcion')


admin.site.register(EstadoSolicitud, EstadoSolicitudAdmin)


# TIPOS DE ARCHIVOS DE LAS SOLICITUDES
class TipoArchivoSolicitudAdmin(ModeloBaseAdmin):
    list_display = ('id', 'opcion', 'descripcion', 'observacion', 'valor')
    ordering = ('opcion', 'valor', 'descripcion')
    search_fields = ('opcion', 'descripcion')


admin.site.register(TipoArchivoSolicitud, TipoArchivoSolicitudAdmin)


# class LogMarcadaAdmin(ModeloBaseTabularAdmin):
#     model = LogMarcada
#
#
# class LogDiaAdmin(ModeloBaseAdmin):
#     inlines = [LogMarcadaAdmin]
#     list_display = ('persona', 'fecha', 'procesado')
#     ordering = ('persona', '-fecha')
#     search_fields = ('persona__cedula', 'persona__apellido1', 'persona__apellido2')
#     raw_id_fields = ('persona',)
#     date_hierarchy = 'fecha'


class PeriodoPoaAdmin(ModeloBaseAdmin):
    list_display = ('id', 'descripcion', 'versionpoa', 'status')
    ordering = ('descripcion',)
    search_fields = ('descripcion',)
    fields = ['descripcion', 'mostrar', 'ingresar', 'edicion', 'activo', 'diassubir', 'versionpoa', 'status']

# class ResponsablesInformesInline(admin.TabularInline):
#     model = Informes.responsables.through
#     raw_id_fields = ('responsables',)
#     extra = 1

class InformesAdmin(ModeloBaseAdmin):
    list_display = ('codigo', 'fecha', 'objetivo', 'archivo',)
    ordering = ('codigo',)
    search_fields = ('codigo','objetivo','departamento__nombre','responsables__nombres','responsables__apellido1','responsables__apellido2',)
    fields = ['codigo', 'departamento', 'fecha', 'objetivo', 'archivo', 'experto','director', 'responsables', ]
    raw_id_fields = ('experto', 'director', 'responsables', )
    #exclude = ('responsables',)
    #inlines = (ResponsablesInformesInline,)


class BitacoraActividadDiariaAdmin(ModeloBaseAdmin):
    list_display = ('departamento', 'fecha', 'persona', 'descripcion','tiposistema',)
    ordering = ('fecha',)
    search_fields = ('departamento__nombre','descripcion','persona__nombres','persona__apellido1','persona__apellido2',)
    fields = ['departamento', 'fecha', 'persona', 'descripcion', 'link', 'tiposistema','archivo', ]
    raw_id_fields = ('persona', 'departamento', )

class AnioEjercicioAdmin(ModeloBaseAdmin):
    list_display = ('anioejercicio', 'sbu', )
    ordering = ('anioejercicio', 'sbu', )
    search_fields = ('anioejercicio', 'sbu', )
    fields = ['persona', 'sbu', 'status', ]


class CuentaBancariaPersonaAdmin(ModeloBaseAdmin):
    list_display = ('persona','banco','tipocuentabanco','numero','personarevisa','estadorevision',)
    ordering = ('-fecha_creacion',)
    list_filter = ('tipocuentabanco','banco','activapago',)
    raw_id_fields = ('persona', 'personarevisa', )
    search_fields = ('persona__cedula','persona__nombres','persona__apellido1','persona__apellido2','numero',)

class RedPersonaTipoAdmin(ModeloBaseAdmin):
    list_display = ('nombre',)
    ordering = ('nombre',)
    search_fields = ('nombre',)


admin.site.register(CuentaBancariaPersona, CuentaBancariaPersonaAdmin)
# admin.site.register(LogDia, LogDiaAdmin)
admin.site.register(PeriodoPoa, PeriodoPoaAdmin)
admin.site.register(Informes, InformesAdmin)
admin.site.register(BitacoraActividadDiaria, BitacoraActividadDiariaAdmin)
admin.site.register(AnioEjercicio, AnioEjercicioAdmin)
admin.site.register(TipoRedPersona,RedPersonaTipoAdmin)

class PersonaDepartamentoFirmasAdmin(ModeloBaseAdmin):
    list_display = ('personadepartamento','tipopersonadepartamento','denominacionpuesto',
                    'departamento','departamentofirma','tiposubrogante','fechainicio','fechafin','activo','actualidad')
    ordering = ('personadepartamento',)
    search_fields = ('personadepartamento',)
    raw_id_fields = ('personadepartamento',)

admin.site.register(PersonaDepartamentoFirmas,PersonaDepartamentoFirmasAdmin)
