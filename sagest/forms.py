# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.db.models import Q
from django.forms import DateTimeInput, ValidationError
from django.forms.widgets import CheckboxInput, FileInput, DateTimeBaseInput, DateInput
# from landscape.lib.cloud import MAX_LENGTH
from django.utils.safestring import mark_safe
from unidecode import unidecode

from core.choices.models.sagest import ESTADO_REVISION_EVIDENCIA, MY_TIPO_DOCUMENTO_EQUIPO_COMPUTO, ESTADO_JUSTIFICACION_PROCESO
from posgrado.models import MaestriasAdmision
from sagest.funciones import encrypt_id, choice_indice
from sagest.models import UnidadMedida, TipoProducto, TipoDocumento, Departamento, NATURALEZA_CUENTA, \
    ESTRUCTURA_ACTIVO, CLASE_BIEN, Banco, TipoCuentaBanco, \
    ClaseDocumentoRespaldo, OrigenIngreso, TipoDocumentoRespaldo, Ubicacion, TipoProyecto, TipoCuentaContable, \
    CuentaContable, EstadoProducto, TipoBien, PeriodoPoa, \
    ProgramaPoa, ObjetivoEstrategico, ObjetivoTactico, ObjetivoOperativo, TIPO_SOLICITUD_TRASPASO_BAJA, TraspasoActivo, \
    ActivoFijo, TipoParticipante, TipoBaja, \
    TallerMantenimiento, ORIGEN_REGISTRO, \
    TIPO_SOLICITUD_PERMISO, ESTADO_PERMISOS, ESTADO_BAJA, DenominacionPuesto, TipoPermiso, TipoPermisoDetalle, \
    UBICACION_HOJA_RUTA, TipoRol, GrupoAgente, SubgrupoAgente, TIPOS_INSTITUCION, MotivoSalida, OtroRegimenLaboral, \
    DedicacionLaboral, ActividadLaboral, TIPOS_USUARIO, \
    SeccionDepartamento, AgenteRiesgoRiesgo, \
    PROBABILIDAD_SEVERIDAD, TIPO_CAMPO, ESTADOS_ACCIONES, Color, ClaseVehiculo, TipoVehiculo, TIPO_ZONA, \
    Proveedor, Contratos, TipoArriendo, LugarContrato, Partida, TIPO_ACTIVIDAD_PRESUPUESTO, \
    UnidadMedidaPresupuesto, FormaDePago, TipoTarjetaBanco, ProcesadorPagoTarjeta, CuentaBanco, SesionCaja, \
    TipoCheque, TipoTransferencia, ProcedenciaTarjeta, TipoOtroRubro, TipoComprobanteRecaudacion, \
    PuntoVenta, TipoConceptoTransferenciaGobierno, TipoTramite, TipoDocumentoTramitePago, Jornada, PodFactor, \
    TIPO_FACTOR, TIPO_ANEXOS_RECURSOS, PresupuestoObra, TIPO_PANILLA, CompromisoClaseRegistro, \
    CompromisoClaseModificacion, CompromisoClaseGasto, \
    AnioEjercicio, PartidaEntidad, PartidaUnidadEjecutoria, PartidaUnidadDesconcentrada, PartidaOrganismo, \
    PartidaSubprograma, PartidaProyecto, PartidaObra, PartidaGeografico, PartidaCorrelativo, \
    PartidasSaldo, ReformaClaseRegistro, TipoArchivoPresupuestoObra, DetalleCertificacion, \
    PresupuestoTipoDocumentoRespaldo, PresupuestoClaseDocumentoRespaldo, IvaAplicado, AccionesTramitePago, \
    BeneficiariTramitePago, TIPO_CATALOGO, TipoRamo, Aseguradora, \
    TipoAccionPersonal, \
    MotivoAccionPersonal, CentroCostoSaldo, CertificacionPartida, TipoMovimientoConciliacion, ESTADO_POD, \
    ESTADO_REFORMA, IndicadorPoa, \
    AccionDocumento, PartidaPrograma, PartidaActividad, PartidaFuente, RegimenLaboral, NivelOcupacional, \
    ModalidadLaboral, EstadoPuesto, EscalaOcupacional, PuestoAdicional, EstructuraProgramatica, TIPO_GRADO, TIPO_ACCION, \
    MedioVerificacion, ProductosPac, RELACION_IES, TramitePago, CapPeriodo, CapEvento, CAPACITACION_FALICITADORES_TIPO, \
    CapTurno, CapEnfocada, QUIEN_APRUEBA, HdUrgencia, HdImpacto, HdPrioridad, HdCategoria, HdDetalle_SubCategoria, \
    HdEstado, HdGrupo, HdSubCategoria, HdMedioReporte, HdDetalle_Grupo, CapClase, HdProceso, HdEstado_Proceso, \
    VehiculoUnemi, ESTADO_VEHICULO, CapEventoIpec, CapEnfocadaIpec, CapPeriodoIpec, CapTurnoIpec, CapClaseIpec, \
    TIPO_PARTICIPANTE_INSCRIBIR, CapModeloEvaluativoTareaIpec, CapInstructorIpec, \
    TIPO_REPORTE_IPEC, CondicionBien, EstadoBien, TipoPermisoDetalleFamilia, DistributivoPersona, ESTADO_REGIMEN, \
    PermisoInstitucional, OPERACION, HdBloque, HdUbicacion, HdBloqueUbicacion, HdTipoIncidente, CategoriaRubroBeca, \
    FORMAS_PAGO, GruposCategoria, CajaChica, SolicitudCajaChica, PartidaCajaChica, ESTADO_PARTES, HdPiezaPartes, \
    HdSolicitudesPiezaPartes, HdCausas, HdPreguntas, TIPO_PRODUCTO_PAC, HdFechacierresolicitudes, ReqPrioridad, \
    ReqActividad, ReqHistoria, ESTADO_HISTORIA, TIPO_PRODUCTO_PAC_INGRESO, UbicacionProceso, \
    TIPO_TRAMITE, TipoResolucion, PerchaArchivo, FilaArchivo, TipoPagoArchivo, SubTipoPagoArchivo, ProveedorArchivo, \
    CasaSalud, TIPOS_MOVIMIENTO_INVENTARIO, ESTADO_ORDEN_TRABAJO, TipoActividadCrai, HdMateriales, ESTADO_USO, SINO, \
    AFECTATOTAL, ESTADOS_ACCIONESACTIVIDADES, RubricaPoa, TIPO_RUBRO, TIPO_FIRMAS, TIPO_USUARIO, CapEventoPeriodoIpec, \
    ESTADO_CAPACITACION, BaseLegalAccionPersonal, MotivoAccionPersonalDetalle, MantenimientoGruDanios, HdDepartament, \
    HdUndMedida_Material, HdUnidadMedida, PeligrosidadProducto, SeccionDepartamento, TIPO_SISTEMA, TIPO_CAPACITACION, \
    ESTADO_ARCHIVO, TIPO_COMPETENCIA, ESTADOS_SOLICITUD_PRODUCTOS, TIPO_PROCESO_TH, NIVEL_TERRITORIAL_TH, \
    TipoVacunaCovid, TIPO_PORTAFOLIOTH, NivelEscalaSalarial, Puesto, TipoCompetenciaLaboral, NIVEL_COMPETENCIA, \
    TipoParticipante, Congreso, TipoContrato, DenominacionPerfilPuesto, PuestoDenominacion, NIVEL_PERFIL_PUESTO, \
    DireccionPerfilPuesto, EscalaSalarial, TIPO_INDICE, ProductoServicioSeccion, TIPO_ANEXO_INFORME, TIPO_ARCHIVO, \
    TIPO_COMPROBANTE, PERMISOS_DEPARTAMENTO, \
    ESTADO_MOVIMIENTO, CategoriaTipoPermiso, ESTADO_UBICACION, ESTADO_FUNCIONAMIENTO, EstadosGeneralesInventarioAT, \
    InventarioATEstadosGenerales, LogMarcada, TIPO_SOLICITUD_JUST_MARCADA, TIPO_SECUENCIA_MARCADA, \
    TIPO_ACTIVIDAD_BITACORA, \
    ActivoTecnologico, ESTADO_USO_AT, Marca, RubroRol, ServicioModelo, Impuesto, ServicioCompra, ComponenteActivo, \
    CronogramaPersonaConstatacionAT, ESTADO_COMPROBANTE, TipoNotificacion, PeriodoRol, ContratoAT, ActividadInformeGC, \
    InformeActivoBaja, PeriodoGarantiaMantenimientoAT, FormatoPazSalvo, \
    DireccionFormatoPS, DetalleDireccionFormatoPS, TIPO_RELACION_LABORAL, PazSalvo, PeriodoConstatacionAF, \
    PeriodoGastosPersonales, GastosPersonales, MOTIVO_SALIDA, GestionProductoServicioTH, SELECCION_REGISTRO_DECIMO, \
    RequisitoPazSalvo, ESTADOS_DOCUMENTOS_PAZ_SALVO, ESTADO_PAZ_SALVO, \
    ESTADOS_DOCUMENTOS_REQUISITOS, ESTADO_CIERRE, GrupoDepartamento, EquipoComputo, ConfiguracionEquipoComputo, \
    TerminosCondicionesEquipoComputo, PreguntaEstadoEC, UsuarioEvidencia, MetaPoa, PeriodoPlanificacionTH, CabPlanificacionTH, GestionPlanificacionTH, ProcesoEleccion, \
    ESTADO_ACTA_CONSTATACION

from settings import IVA, PUESTO_ACTIVO_ID
from sga.forms import ExtFileField
from sga.funciones import validarcedula, generar_nombre
from sga.models import Pais, TIPO_CELULAR, Persona, Administrativo, Provincia, Canton, Parroquia, TipoSangre, \
    ParentescoPersona, \
    NacionalidadIndigena, Raza, MESES_CHOICES, Discapacidad, Titulo, AreaTitulo, \
    InstitucionEducacionSuperior, Colegio, \
    TipoCurso, TipoCertificacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, \
    AreaConocimientoTitulacion, TipoParticipacion, TipoCapacitacion, NivelTitulacion, ContextoCapacitacion, \
    DetalleContextoCapacitacion, PersonaEstadoCivil, TIPO_BECA, FinanciamientoBeca, GradoTitulacion, \
    TIPOS_IDENTIFICACION, TIPO_PERSONA, Carrera, MODALIDAD_CAPACITACION, TipoArchivo, Titulacion, Zona, TipoRespuesta, \
    TIPO_MUNDO_CRAI, TIPO_CAPACITACION_UATH, VALOR_SI_NO, TIPO_INSTITUCION, InstitucionBeca, TIPO_INSTITUCION_BECA, \
    RANGO_EDAD_NINO, DisciplinaDeportiva, CampoArtistico, ESTADO_REVISION_ARCHIVO, TIPO_DECLARACION, Modulo, TIPO_AREA, \
    TIPO_NIVEL_FORMACION, TipoNoticias, AreaConocimiento, RedPersona, TipoRedPersona, TIPO_CAPACITACION_P, \
    SubTipoDiscapacidad, GRADO, ZONA_DOMICILIO, TIPO_INSTITUCION_LABORAL, TipoTransporte, LugarCompraAlimentos, \
    OperadoraMovil, LugarAlimentacion, TipoGasto, CapEventoPeriodoDocente, CapModeloEvaluativoDocente, Materia, \
    MONTH_CHOICES, CENTRO_CUIDADO, RevistaInvestigacion, ParticipantesTipo, Sexo, Periodo
from socioecon.models import FormaTrabajo
from pdip.models import ActividadesPerfil,ActividadesContratoPerfil

from med.models import Enfermedad

from core.custom_forms import FormModeloBase

from core.choices.models.sagest import MY_ESTADO_SOLICITUD_EQUIPO_COMPUTO, ESTADO_SEGUIMIENTO_POA


class CustomDateInput(DateTimeBaseInput):
    def format_value(self, value):
        return str(value or '')

def deshabilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True
    form.fields[campo].widget.attrs['disabled'] = True


def habilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = False
    form.fields[campo].widget.attrs['disabled'] = False


def campo_solo_lectura(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True

class SagestImportarXLSForm(FormModeloBase):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 6Mb, en formato xls', ext_whitelist=(".xls", "xlsx"),
                           max_upload_size=6291456)

class CuentaContableForm(forms.Form):
    cuenta = forms.CharField(label=u'Cuenta', widget=forms.TextInput(attrs={'class': 'imp-25'}))
    descripcion = forms.CharField(label=u'Descripción', required=False)
    naturaleza = forms.ChoiceField(choices=NATURALEZA_CUENTA, label=u'Naturaleza', required=False,
                                   widget=forms.Select(attrs={'class': 'imp-25'}))
    tipo = forms.ModelChoiceField(TipoCuentaContable.objects.all(), label=u'Tipo',
                                  widget=forms.Select(attrs={'class': 'imp-50'}))
    partida = forms.ModelChoiceField(Partida.objects.filter(status=True), label=u'Partida',
                                     widget=forms.Select(attrs={'class': 'imp-50'}))
    bodega = forms.BooleanField(initial=False, label=u'Para Bodega?', required=False)
    activosfijos = forms.BooleanField(initial=False, label=u'Para Activo?', required=False)
    asociaccosto = forms.BooleanField(initial=False, label=u'Con CentroCosto', required=False)


class PeligrosidadProductoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'rows': '2'}))


class ProductoForm(forms.Form):
    cuenta = forms.ModelChoiceField(CuentaContable.objects.filter(bodega=True), label=u'Cuenta Contable',
                                    required=False, widget=forms.Select())
    codigo = forms.CharField(label=u'Código', required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    codigobarra = forms.CharField(max_length=20, label=u'Cod. Barra', required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-25'}))
    tipoproducto = forms.ModelChoiceField(TipoProducto.objects.all(), label=u'Categoría', required=False,
                                          widget=forms.Select(attrs={'class': 'imp-50'}))
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'rows': '2'}))
    alias = forms.CharField(max_length=20, label=u'Alias', required=False,
                            widget=forms.TextInput(attrs={'formwidth': '300px'}))
    unidadmedida = forms.ModelChoiceField(UnidadMedida.objects.all(), required=False, label=u'UM',
                                          widget=forms.Select(attrs={'formwidth': '350px', 'separator': 'true'}))
    minimo = forms.DecimalField(initial="0.0000", label=u'Cant.Mínima', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    maximo = forms.DecimalField(initial="0.0000", label=u'Cant.Máxima', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    consumo_minimo_diario = forms.DecimalField(initial="0.0000", label=u'Consumo Mínimo diario', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    consumo_medio_diario = forms.DecimalField(initial="0.0000", label=u'Consumo Medio diario', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    consumo_maximo_diario = forms.DecimalField(initial="0.0000", label=u'Consumo Máximo diario', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    tiempo_reposicion_inventario = forms.DecimalField(initial="0.0000", label=u'Tiempo de reposición de inv.', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-25'}))
    peligrosidad = forms.ModelChoiceField(PeligrosidadProducto.objects.filter(status=True),
                                          label=u'Peligrosidad del producto', required=False, widget=forms.Select())

    def add(self):
        del self.fields['codigo']

    def editar(self, producto):
        del self.fields['alias']
        del self.fields['codigobarra']
        del self.fields['cuenta']
        deshabilitar_campo(self, 'codigo')
        if producto.en_uso():
            deshabilitar_campo(self, 'tipoproducto')
            deshabilitar_campo(self, 'unidadmedida')
            deshabilitar_campo(self, 'descripcion')


class ProveedorForm(forms.Form):
    nombre = forms.CharField(max_length=200, label=u'Razón Social', required=False)
    identificacion = forms.CharField(max_length=200, label=u'Identificación', required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-ruc'}))
    alias = forms.CharField(max_length=100, label=u'Alias', required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-25'}))
    pais = forms.ModelChoiceField(Pais.objects.all(), required=False, label=u'País',
                                  widget=forms.Select(attrs={'class': 'imp-75'}))
    direccion = forms.CharField(max_length=200, label=u'Dirección', required=False)
    email = forms.CharField(max_length=200, label=u'Email', required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefono = forms.CharField(max_length=100, label=u'Teléfono', required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-25'}))
    celular = forms.CharField(max_length=100, label=u'Celular', required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-25'}))
    fax = forms.CharField(max_length=100, label=u'Fax', required=False,
                          widget=forms.TextInput(attrs={'class': 'imp-25'}))

    def editar(self):
        deshabilitar_campo(self, 'identificacion')
        deshabilitar_campo(self, 'nombre')

    def camposnoequeridos(self):
        del self.fields['alias']
        del self.fields['pais']
        del self.fields['telefono']
        del self.fields['celular']
        del self.fields['fax']


class DepartamentoForm(FormModeloBase):
    grupodepartamento = forms.ModelChoiceField(GrupoDepartamento.objects.filter(status=True).distinct(), required=False,
                                    label=u'Grupo Departamento',
                                    widget=forms.Select(attrs={'class': 'select2'}))
    nombre = forms.CharField(label=u'Departamento', required=True, widget=forms.TextInput(attrs={'col': '12','placeholder':'Describa el nombre del departamento'}))
    tipoindice = forms.ChoiceField(choices=TIPO_INDICE, label=u'Naturaleza', required=True,
                                   widget=forms.Select(attrs={'col': '12','class':'select2'}))
    codigoindice = forms.CharField(label=u'Codigo de Indice', required=False,
                                   widget=forms.TextInput(attrs={'col': '12','placeholder':'Ejem: 1.1'}))
    permisodepartamento = forms.ChoiceField(choices=PERMISOS_DEPARTAMENTO, label=u'Permisos Departamentales', required=False,
                                            widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    permisogeneral = forms.BooleanField(label=u'Revisa todos los permisos', required=False, widget=CheckboxInput(attrs={'data-switchery':True, 'col':'6'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')

    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        nombre = cleaned_data.get('nombre')
        id = getattr(instancia, 'id', 0)
        departamentos = Departamento.objects.filter(nombre__unaccent__iexact=nombre, status=True).exclude(id=id)
        if departamentos:
            self.add_error('nombre', 'Ya existe un departamento con este nombre')
        cleaned_data['nombre'] = nombre
        return cleaned_data

class ImportaProductosDirForm(FormModeloBase):

    unidad = forms.ModelChoiceField(Departamento.objects.filter(status=True).distinct(), required=False,
                                                   label=u'Unidad',
                                                   widget=forms.Select(attrs={'formwidth': '100%','class':'select2'}))


    def con_producto(self):
        ids = ProductoServicioSeccion.objects.values_list('seccion__departamento_id').filter(status=True).distinct()
        self.fields['unidad'].queryset = Departamento.objects.filter(id__in=ids)


class CarpetaForm(forms.Form):
    nombre = forms.CharField(max_length=200, label=u'Nombre', required=True)
    cantidadarchivos = forms.IntegerField(initial=0, label=u'Cantidad Archivos', required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))


class ConfigCarpetaForm(forms.Form):
    cantidad = forms.IntegerField(initial=0, label=u'Cantidad Archivos', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))


class CarpetaArchivoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True)
    tipoarchivo = forms.ChoiceField(choices=TIPO_ARCHIVO, label=u'Tipo Archivo', required=True,
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True,
                           help_text=u'Tamaño maximo permitido 50Mb, en formato pdf, doc, docx, xls, xlsx, ppt, pptx, zip, rar',
                           ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"),
                           max_upload_size=209715200, widget=forms.FileInput(attrs={'formwidth': '100%', 'class': 'dropify'}))


class EditCarpetaArchivoForm(forms.Form):
    nombre = forms.CharField(max_length=200, label=u'Nombre', required=True)


class AlmacenForm(forms.Form):
    nombre = forms.CharField(max_length=200, label=u'Almacen', required=False)
    responsable = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                         label=u'Responsable', widget=forms.Select(attrs={'class': 'imp-75'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')


class IngresoProductoForm(forms.Form):
    proveedor = forms.ModelChoiceField(Proveedor.objects.all(), label=u'Proveedor',
                                       widget=forms.Select(attrs={'formwidth': '50%'}))
    tipodocumento = forms.ModelChoiceField(TipoDocumento.objects.all(), label=u'Tipo Documento',
                                           widget=forms.Select(attrs={'formwidth': '500px', 'separator': 'true'}))
    numerodocumento = forms.CharField(label=u'Número Documento',
                                      widget=forms.TextInput(attrs={'class': 'imp-comprobantes', 'formwidth': '300px'}))
    fechadocumento = forms.DateField(label=u"Fecha documento", initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '200px'}))
    ordencompra = forms.CharField(label=u'Orden compra', required=False,
                                  widget=forms.TextInput(attrs={'formwidth': '400px', 'separator': 'true'}))
    solicitudcompra = forms.CharField(label=u'Solicitud compra', required=False,
                                      widget=forms.TextInput(attrs={'formwidth': '400px'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.TextInput(attrs={'formwidth': '100%'}))


class DetalleIngresoProductoForm(forms.Form):
    codigoprod = forms.CharField(max_length=30, label=u'Código',
                                 widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    cuenta = forms.CharField(max_length=50, label=u'Cuenta', widget=forms.TextInput(attrs={'formwidth': '50%'}))
    tipoprod = forms.CharField(max_length=100, label=u'Categoría', widget=forms.TextInput())
    descripcionprod = forms.CharField(label=u'Descripción', widget=forms.Textarea({'rows': '2'}))
    unidadmedidaprod = forms.CharField(max_length=30, label=u'UM',
                                       widget=forms.TextInput(attrs={'class': 'imp-codigo'}))
    cantidadprod = forms.DecimalField(initial='0.00', label=u'Cantidad',
                                      widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    costoprod = forms.DecimalField(initial='0.00', label=u'Costo',
                                   widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    subtotal = forms.DecimalField(initial='0.00', label=u'Subtotal',
                                  widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    valor_descuento = forms.DecimalField(initial='0.00', label=u'Valor descuento',
                                         widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%'}))
    coniva = forms.BooleanField(initial=False, label=u'Aplica Iva', widget=forms.CheckboxInput(
        attrs={'class': 'imp-moneda', 'formwidth': '20%', 'separator': 'true'}))
    iva = forms.DecimalField(initial=IVA, label=u'Porciento IVA',
                             widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '30%'}))
    valoriva = forms.DecimalField(initial='0.0000', label=u'Valor IVA',
                                  widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%'}))
    total = forms.DecimalField(initial='0.0000', label=u'Total', widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    estado = forms.ModelChoiceField(EstadoProducto.objects.all(), label=u"Estado",
                                    widget=forms.Select(attrs={'formwidth': '40%'}))
    fechacaducidad = forms.DateField(label=u"Fecha caducidad", initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selecto'
                                                                                                      'rfecha',
                                                                                             'formwidth': '200px'}))


class SalidaProductoForm(forms.Form):
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=False,
        label=u'Departamento', widget=forms.Select(attrs={'formwidth': '600px'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=False,
                                         label=u'Responsable',
                                         widget=forms.Select(attrs={'formwidth': '400px', 'labelwidth': '100px'}))
    descripcion = forms.CharField(label=u'Motivo Salida', required=False, widget=forms.Textarea(attrs={'rows': '1'}))
    observaciones = forms.CharField(label=u'Observaciones', required=False, widget=forms.Textarea(attrs={'rows': '1'}))

    def adicionar(self):
        self.fields['responsable'].queryset = Persona.objects.filter(administrativo__isnull=False).filter(id=None)

class SalidaProductoModalEditForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripcion', required=True, widget=forms.Textarea(attrs={'rows': '2'}))
    observaciones = forms.CharField(label=u'Observaciones', required=True, widget=forms.Textarea(attrs={'rows': '2'}))



class DetalleSalidaProductoForm(forms.Form):
    codigoprod = forms.CharField(max_length=30, label=u'Código',
                                 widget=forms.TextInput(attrs={'class': 'imp-50', 'codigo': ''}))
    descripcionprod = forms.CharField(label=u'Descripción', widget=forms.Textarea({'class': 'imp-100', 'rows': '2'}))
    stockprod = forms.DecimalField(initial="0.00", label=u'Stock',
                                   widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': "6"}))
    cantidadprod = forms.DecimalField(initial="0.00", label=u'Cantidad',
                                      widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': "6"}))

    def adicionar(self):
        deshabilitar_campo(self, 'descripcionprod')
        deshabilitar_campo(self, 'stockprod')


class AnulacionForm(forms.Form):
    numerodocumento = forms.IntegerField(initial=0, label=u'Número Documento', required=False,
                                         widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    detalle = forms.CharField(label=u'Detalle Documento', required=False,
                              widget=forms.Textarea({'class': 'imp-100', 'rows': '2'}))
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea({'class': 'imp-100', 'rows': '2'}))

    def adicionar(self):
        deshabilitar_campo(self, 'detalle')


class OrdenPedidoForm(forms.Form):
    codigodocumento = forms.CharField(label=u'Nro.', required=False, widget=forms.TextInput(attrs={'class': 'imp-100',
                                                                                                   'formwidth': '40%'}))
    fechaordenpedido = forms.DateField(label=u"Fecha Orden de Pedido", input_formats=['%d-%m-%Y'], required=False,
                                       widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha',
                                                                                      'labelwidth': '150px',
                                                                                      'formwidth': '40%'}))
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(),
        required=False, label=u'Departamento (*)',
        widget=forms.Select(attrs={'formwidth': '50%'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=False,
                                         label=u'Solicitante (*)',
                                         widget=forms.Select(attrs={'formwidth': '50%', 'labelwidth': '100px'}))
    descripcion = forms.CharField(label=u'Motivo de Pedido (*)', required=False,
                                  widget=forms.Textarea(attrs={'rows': '1'}))
    observaciones = forms.CharField(label=u'Observaciones (*)', required=False,
                                    widget=forms.Textarea(attrs={'rows': '1'}))

    def adicionar(self):
        self.fields['responsable'].queryset = Persona.objects.filter(administrativo__isnull=False).filter(id=None)

    def addOrdenTrabajo(self):
        deshabilitar_campo(self, 'codigodocumento')
        deshabilitar_campo(self, 'fechaordenpedido')
        deshabilitar_campo(self, 'descripcion')
        del self.fields['departamento']
        del self.fields['responsable']


class DetalleOrdenPedidoForm(forms.Form):
    codigoprod = forms.CharField(max_length=30, label=u'Código', widget=forms.TextInput(attrs={'class': 'imp-codigo',
                                                                                               'formwidth': '100%'}))
    cuentaprod = forms.CharField(max_length=50, label=u'Cuenta',
                                 widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    tipoprod = forms.CharField(max_length=100, label=u'Categoría',
                               widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    descripcionprod = forms.CharField(label=u'Descripción', widget=forms.Textarea({'rows': '2'}))
    unidadmedidaprod = forms.CharField(max_length=30, label=u'UM', widget=forms.TextInput(attrs={'class': 'imp-100'}))
    existenciaprod = forms.DecimalField(initial='0.00', label=u'Cantidad disponible',
                                        widget=forms.TextInput(attrs={'class': 'imp-moneda',
                                                                      'decimal': "4",
                                                                      'formwidth': '100%'}))
    costoprod = forms.DecimalField(initial='0.0000', label=u'Costo',
                                   widget=forms.TextInput(attrs={'class': 'imp-moneda',
                                                                 'decimal': "4",
                                                                 'formwidth': '100%'}))
    cantidadprod = forms.DecimalField(initial="0.00", label=u'Cantidad a solicitar',
                                      widget=forms.TextInput(attrs={'class': 'imp-moneda',
                                                                    'decimal': "4",
                                                                    'formwidth': '100%'}))

    def adicionar(self):
        deshabilitar_campo(self, 'cuentaprod')
        deshabilitar_campo(self, 'tipoprod')
        deshabilitar_campo(self, 'descripcionprod')
        deshabilitar_campo(self, 'unidadmedidaprod')
        deshabilitar_campo(self, 'existenciaprod')
        deshabilitar_campo(self, 'costoprod')


class IntegranteDepartamentoForm(forms.Form):
    persona = forms.CharField(label=u'Integrante', widget=forms.TextInput(attrs={'codigo': ''}))


class ResponsableDepartamentoForm(forms.Form):
    responsable = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                         label=u'Responsable', widget=forms.Select())
    responsable_subrogante = forms.ModelMultipleChoiceField(label=u"Responsables Subrogante",
                                                            queryset=Persona.objects.filter(
                                                                Q(perfilusuario__administrativo__isnull=False) | Q(
                                                                    perfilusuario__profesor__isnull=False)).distinct(),
                                                            required=False,
                                                            widget=forms.SelectMultiple(attrs={'formwidth': '94%'}))
    # responsable_subrogante = forms.ModelChoiceField(Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(), label=u'Responsable Subrogante', widget=forms.Select())


class UbicacionForm(forms.Form):
    codigo = forms.CharField(label=u'Código', required=False, max_length=10,
                             widget=forms.TextInput(attrs={'class': 'imp-25'}))
    nombre = forms.CharField(label=u'Descripción', required=False, max_length=250)
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=False,
                                         label=u'Responsable Bienes', widget=forms.Select(attrs={'formwidth': '75%'}))

    def solo_responsable(self):
        del self.fields['codigo']
        del self.fields['nombre']
        del self.fields['observacion']


class UbicacionesForm(FormModeloBase):
    from sga.models import Bloque
    codigo = forms.CharField(label=u'Código', required=True, max_length=10,
                             widget=forms.TextInput(attrs={'col': '3'}))
    nombre = forms.CharField(label=u'Nombre', required=True, max_length=250)
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'col': '12'}))
    bloquepertenece = forms.ModelChoiceField(label="Bloque", required=True,
                                     queryset=Bloque.objects.select_related().filter(status=True),
                                     widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    responsable = forms.ModelChoiceField(label="Responsable de bienes", required=True,
                                     queryset=Persona.objects.select_related().filter(status=True),
                                     widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

    def solo_responsable(self):
        del self.fields['codigo']
        del self.fields['nombre']
        del self.fields['bloque']
        del self.fields['observacion']


class CatalogoForm(forms.Form):
    tipocatalogo = forms.ChoiceField(choices=TIPO_CATALOGO, label=u'Tipo Catalogo', required=False,
                                     widget=forms.Select(attrs={'formwidth': '50%'}))
    identificador = forms.CharField(label=u'Identificador', required=False, max_length=15,
                                    widget=forms.TextInput(attrs={'class': 'imp-codigo'}))
    tipobien = forms.ModelChoiceField(TipoBien.objects.all(), required=False, label=u'Tipo de Bien',
                                      widget=forms.Select(attrs={'formwidth': '50%'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=250)
    item = forms.ModelChoiceField(Partida.objects.all(), required=False, label=u'Item',
                                  widget=forms.Select(attrs={'formwidth': '50%'}))

    def editar(self):
        deshabilitar_campo(self, 'tipocatalogo')
        deshabilitar_campo(self, 'identificador')


class ActasForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha ingreso", required=False, initial=datetime.now().date(),
                            input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                             attrs={'class': 'selectorfecha',
                                                                                    'formwidth': '190px',
                                                                                    'separator': 'true'}))
    numero = forms.CharField(label=u'Numero', required=False, max_length=15,
                             widget=forms.TextInput(attrs={'class': 'imp-codigo'}))
    tipobien = forms.ModelChoiceField(TipoBien.objects.all(), required=False, label=u'Tipo de Bien',
                                      widget=forms.Select(attrs={'formwidth': '50%'}))
    tipocomprobante = forms.ModelChoiceField(TipoDocumento.objects.all(), required=False, label=u'Tipo de Comprobante',
                                             widget=forms.Select(attrs={'formwidth': '50%'}))
    origeningreso = forms.ModelChoiceField(OrigenIngreso.objects.all(), required=False, label=u'Origen de ingreso',
                                           widget=forms.Select(attrs={'formwidth': '50%'}))
    proveedor = forms.CharField(label=u'Proveedor', required=False, max_length=250,
                                widget=forms.TextInput(attrs={'formwidth': '50%'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                         required=False, label=u'Responsable Bien',
                                         widget=forms.Select(attrs={'formwidth': '450px'}))
    custodio = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                      required=False, label=u'Custodio Bien',
                                      widget=forms.Select(attrs={'formwidth': '390px', 'labelwidth': '100px'}))
    ubicacion = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicación Bien',
                                       widget=forms.Select(attrs={'formwidth': '410px', 'labelwidth': '100px'}))

    def editar(self):
        deshabilitar_campo(self, 'numero')
        deshabilitar_campo(self, 'fecha')
        deshabilitar_campo(self, 'tipobien')
        deshabilitar_campo(self, 'origeningreso')
        deshabilitar_campo(self, 'ubicacion')
        deshabilitar_campo(self, 'responsable')


class TallerMantenimientoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=150)
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))


class ActivoFijoForm(forms.Form):
    tiempousado = forms.CharField(label=u"Tiempo de uso del bien", required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '400px'}))
    codigogobierno = forms.CharField(label=u"Código Gobierno", required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '400px'}))
    codigointerno = forms.CharField(label=u"Código Interno", required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '400px'}))
    estructuraactivo = forms.ChoiceField(choices=ESTRUCTURA_ACTIVO, required=False, label=u'Forma Ingreso',
                                         widget=forms.Select(attrs={'formwidth': '300px', 'separator': 'true'}))
    clasebien = forms.ChoiceField(choices=CLASE_BIEN, label=u'Clase Bien', required=False,
                                  widget=forms.Select(attrs={'formwidth': '320px', 'labelwidth': '100px'}))
    fechaingreso = forms.DateField(label=u"Fecha ingreso", required=False, initial=datetime.now().date(),
                                   input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                    attrs={'class': 'selectorfecha',
                                                                                           'formwidth': '190px',
                                                                                           'separator': 'true'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea({'rows': '3'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '3'}))
    origeningreso = forms.ModelChoiceField(OrigenIngreso.objects.all(), required=False, label=u'Origen Ingreso',
                                           widget=forms.Select(attrs={'formwidth': '400px'}))
    costo = forms.DecimalField(initial="0.00", label=u'Costo', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'formwidth': '200px', 'labelwidth': '100px', 'decimal': '2'}))
    serie = forms.CharField(label=u"Serie", required=False, widget=forms.TextInput(attrs={'class': 'imp-descripcion'}))
    modelo = forms.CharField(label=u"Modelo", required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-descripcion'}))
    marca = forms.CharField(label=u'Marca', max_length=250, widget=forms.TextInput(attrs={'class': 'imp-descripcion'}))
    tipodocumentorespaldo = forms.ModelChoiceField(TipoDocumentoRespaldo.objects.all(), required=False,
                                                   label=u'Tipo Doc. Respaldo', widget=forms.Select(
            attrs={'formwidth': '600px', 'separator': 'true'}))
    clasedocumentorespaldo = forms.ModelChoiceField(ClaseDocumentoRespaldo.objects.all(), required=False,
                                                    label=u'Clase Doc. Respaldo', widget=forms.Select(
            attrs={'formwidth': '600px', 'separator': 'true'}))
    numerocomprobante = forms.CharField(label=u'N° Comprobante', required=False, max_length=20,
                                        widget=forms.TextInput(attrs={'formwidth': '40%', 'class': 'imp-comprobantes'}))
    tipocomprobante = forms.ModelChoiceField(TipoDocumento.objects.all(), required=False, label=u'Tipo Comprobante',
                                             widget=forms.Select(attrs={'formwidth': '50%'}))
    fechacomprobante = forms.DateField(label=u"F. Comprobante", required=False, initial=datetime.now().date(),
                                       input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                        attrs={'class': 'selectorfecha',
                                                                                               'formwidth': '35%',
                                                                                               'separator': 'true'}))
    tipoproyecto = forms.ModelChoiceField(TipoProyecto.objects.all(), required=False, label=u'Tipo Proyeecto',
                                          widget=forms.Select(attrs={'formwidth': '600px', 'separator': 'true'}))
    estado = forms.ModelChoiceField(EstadoProducto.objects.all(), required=False, label=u'Estado',
                                    widget=forms.Select(attrs={'formwidth': '50%', 'separator': 'true'}))
    deprecia = forms.BooleanField(initial=True, required=False, label=u"Deprecia?")
    vidautil = forms.IntegerField(initial=0, label=u'Años de Vida útil', required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    cuentacontable = forms.ModelChoiceField(CuentaContable.objects.filter(activosfijos=True), required=False,
                                            label=u'Cuenta Contable', widget=forms.Select(attrs={}))
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable Bien',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    custodio = forms.IntegerField(initial=0, required=False, label=u'Custodio Bien',
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    ubicacion = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicación Bien',
                                       widget=forms.Select())
    catalogo = forms.IntegerField(initial=0, required=False, label=u'Catálogo Bien',
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    titulo = forms.CharField(required=False, label=u'Título', widget=forms.TextInput(attrs={'separator': 'true'}))
    autor = forms.CharField(required=False, label=u'Autor', widget=forms.TextInput())
    editorial = forms.CharField(required=False, label=u'Editorial', widget=forms.TextInput())
    fechaedicion = forms.DateField(label=u"Fecha edición", required=False, initial=datetime.now().date(),
                                   input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                    attrs={'class': 'selectorfecha',
                                                                                           'formwidth': '50%'}))
    numeroedicion = forms.CharField(label=u"Número de edición", required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    clasificacionbibliografica = forms.CharField(required=False, label=u'Clasificación Bibliográfica',
                                                 widget=forms.TextInput())
    color = forms.ModelChoiceField(Color.objects.all(), required=False, label=u'Color',
                                   widget=forms.Select(attrs={'separator': 'true', 'formwidth': '75%'}))
    material = forms.CharField(required=False, label=u'Material', widget=forms.TextInput(attrs={'formwidth': '75%'}))
    dimensiones = forms.CharField(required=False, label=u'Dimensiones',
                                  widget=forms.TextInput(attrs={'formwidth': '75%'}))
    clasevehiculo = forms.ModelChoiceField(ClaseVehiculo.objects.all(), required=False, label=u'Clase Vehículo',
                                           widget=forms.Select(attrs={'separator': 'true', 'formwidth': '50%'}))
    tipovehiculo = forms.ModelChoiceField(TipoVehiculo.objects.all(), required=False, label=u'Tipo Vehículo',
                                          widget=forms.Select(attrs={'formwidth': '50%'}))
    numeromotor = forms.CharField(label=u"Número de motor", required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    numerochasis = forms.CharField(label=u"Número de chasis", required=False,
                                   widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    placa = forms.CharField(label=u"Placa", required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    aniofabricacion = forms.IntegerField(label=u"Año de fabricación", initial=datetime.now().date().year,
                                         required=False, widget=forms.TextInput(
            attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    colorprimario = forms.ModelChoiceField(Color.objects.all(), required=False, label=u'Color Primario',
                                           widget=forms.Select(attrs={'formwidth': '75%'}))
    colorsecundario = forms.ModelChoiceField(Color.objects.all(), required=False, label=u'Color Secundario',
                                             widget=forms.Select(attrs={'formwidth': '75%'}))
    propietario = forms.CharField(required=False, label=u'Propietario',
                                  widget=forms.TextInput(attrs={'separator': 'true'}))
    codigocatastral = forms.CharField(label=u"Código catastral", required=False,
                                      widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    numeropredio = forms.CharField(label=u"Número predio", required=False,
                                   widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    valoravaluo = forms.DecimalField(initial="0.00", label=u'Valor Avalúo', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'formwidth': '50%', 'decimal': '2'}))
    anioavaluo = forms.IntegerField(label=u"Año de Avalúo", required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    areapredio = forms.DecimalField(initial="0.00", label=u'Área Predio(mts)', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    areaconstruccion = forms.DecimalField(initial="0.00", label=u'Área Construcción(mts)', required=False,
                                          widget=forms.TextInput(
                                              attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    pisos = forms.IntegerField(label=u"Número de pisos", required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    provincia = forms.ModelChoiceField(Provincia.objects.all(), required=False, label=u'Provincia',
                                       widget=forms.Select())
    canton = forms.ModelChoiceField(Canton.objects.all(), required=False, label=u'Cantón', widget=forms.Select())
    parroquia = forms.ModelChoiceField(Parroquia.objects.all(), required=False, label=u'Parroquia',
                                       widget=forms.Select())
    zona = forms.ChoiceField(choices=TIPO_ZONA, label=u'Zona', required=False,
                             widget=forms.Select(attrs={'formwidth': '50%'}))
    nomenclatura = forms.CharField(label=u"Nomenclatura", required=False,
                                   widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    sector = forms.CharField(required=False, label=u'Sector', widget=forms.TextInput())
    direccion = forms.CharField(required=False, label=u'Calle principal', widget=forms.TextInput())
    direccion2 = forms.CharField(required=False, label=u'Calle secundaria', widget=forms.TextInput())
    escritura = forms.CharField(label=u"Escritura", required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    fechaescritura = forms.DateField(label=u"Fecha escritura", required=False, initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '200px'}))
    notaria = forms.CharField(required=False, label=u'Notaría', widget=forms.TextInput())
    beneficiariocontrato = forms.CharField(required=False, label=u'Beneficiario contrato', widget=forms.TextInput())
    fechacontrato = forms.DateField(label=u"Fecha contrato", required=False, initial=datetime.now().date(),
                                    input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                     attrs={'class': 'selectorfecha',
                                                                                            'formwidth': '200px'}))
    duracioncontrato = forms.IntegerField(initial=0, label=u'Duración del contrato', required=False,
                                          widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    montocontrato = forms.DecimalField(initial="0.00", label=u'Monto contrato', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'formwidth': '50%', 'decimal': '2'}))
    ebye = forms.BooleanField(initial=True, required=False, label=u"eBYE?")
    fechainiciogarantia = forms.DateField(label=u"F. Inicio de garantía", required=False, input_formats=['%d-%m-%Y'],
                                          widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha',
                                                                                         'formwidth': '35%',
                                                                                         'separator': 'true'}))
    fechafingarantia = forms.DateField(label=u"F. Fin de garantía", required=False, input_formats=['%d-%m-%Y'],
                                          widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha',
                                                                                         'formwidth': '35%', }))

    def editar(self, activo, user):
        if activo.codigogobierno:
            deshabilitar_campo(self, 'codigogobierno')
        if activo.codigointerno:
            deshabilitar_campo(self, 'codigointerno')
        if not user.has_perm("sagest.puede_modificar_depreciacion"):
            if activo.en_uso():
                deshabilitar_campo(self, 'deprecia')
                deshabilitar_campo(self, 'vidautil')
                deshabilitar_campo(self, 'catalogo')
        if activo.en_uso() or activo.subidogobierno:
            deshabilitar_campo(self, 'fechaingreso')
            deshabilitar_campo(self, 'costo')
            deshabilitar_campo(self, 'fechacomprobante')
            deshabilitar_campo(self, 'responsable')
            deshabilitar_campo(self, 'custodio')
            # deshabilitar_campo(self, 'ubicacion')
            if activo.responsable:
                self.fields['responsable'].widget.attrs['descripcion'] = activo.responsable.nombre_completo()
                self.fields['responsable'].initial = activo.responsable.id
            else:
                habilitar_campo(self, 'responsable')

            if activo.custodio:
                self.fields['custodio'].widget.attrs['descripcion'] = activo.custodio.nombre_completo()

                self.fields['custodio'].initial = activo.custodio.id
            else:
                habilitar_campo(self, 'custodio')
        else:
            del self.fields['responsable']
            del self.fields['custodio']
            del self.fields['ubicacion']
        self.fields['catalogo'].widget.attrs['descripcion'] = activo.catalogo.descripcion
        self.fields['catalogo'].initial = activo.catalogo.id


class ActivoResponsableForm(forms.Form):
    usuariobien = forms.ModelChoiceField(Administrativo.objects.all(), required=False, label=u'Usuario bien',
                                         widget=forms.Select(attrs={'class': 'imp-50'}))
    custodio = forms.ModelChoiceField(Administrativo.objects.all(), required=False, label=u'Custodio',
                                      widget=forms.Select(attrs={'class': 'imp-50'}))
    ubicacion = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicación',
                                       widget=forms.Select(attrs={'class': 'imp-50'}))


class ActivoCustodioForm(forms.Form):
    custodio = forms.ModelChoiceField(Administrativo.objects.all(), required=False, label=u'Custodio',
                                      widget=forms.Select(attrs={'class': 'imp-50'}))


class ActivoUbicacionForm(forms.Form):
    ubicacion = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicación',
                                       widget=forms.Select(attrs={'class': 'imp-50'}))


class ImportarArchivoCSVForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 4Mb, en formato txt, csv',
                           ext_whitelist=(".txt", ".csv",), max_upload_size=4194304)


class ImportarArchivoPresupuestoObraForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=300, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-50', 'formwidth': '820px'}))
    tipoarchivo = forms.ModelChoiceField(TipoArchivoPresupuestoObra.objects.all(), required=False,
                                         label=u'Tipo de Archivo',
                                         widget=forms.Select(attrs={'class': 'imp-75', 'formwidth': '350px'}))
    archivo = ExtFileField(label=u'Seleccione Archivo',
                           help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"),
                           max_upload_size=12582912)


class ImportarArchivoXLSForm(forms.Form):
    tipobien = forms.ModelChoiceField(TipoBien.objects.all(), required=False, label=u"Tipo Bien")
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 12Mb, en formato xlsx',
                           ext_whitelist=(".xlsx",), max_upload_size=12582912)

    def editar(self):
        del self.fields['tipobien']


class ImportarArchivoForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 12Mb, en formato xlsx',
                           ext_whitelist=(".xlsx", ".xls"), max_upload_size=12582912)


class ExportacionForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    clasebien = forms.ChoiceField(choices=CLASE_BIEN, required=False, label=u'Clase Bien',
                                  widget=forms.Select(attrs={'formwidth': '75%'}))
    tipobien = forms.ModelChoiceField(TipoBien.objects.all(), required=False, label=u'Tipo Bien',
                                      widget=forms.Select(attrs={'formwidth': '100%'}))
    cuentacontable = forms.ModelChoiceField(CuentaContable.objects.all(), required=False, label=u'Cuenta Contable',
                                            widget=forms.Select(attrs={'formwidth': '100%'}))


class ProgramaForm(forms.Form):
    nombre = forms.CharField(label=u'Programa', max_length=100)


class PeriodoPoaForm(FormModeloBase):

    descripcion = forms.CharField(max_length=300, label=u"Descripción")
    anio = forms.IntegerField(initial=datetime.now().year, label=u"Año",
                              widget=forms.TextInput(attrs={'class': 'input_number', 'input_number': True, 'col': '4'}))
    diassubir = forms.IntegerField(initial=0, label=u"Días a subir",
                                   widget=forms.TextInput(attrs={'class': 'input_number','input_number': True, 'col':'4'}))
    diascorreccion = forms.IntegerField(initial=0, label=u"Días de corrección",
                                   widget=forms.TextInput(attrs={'class': 'input_number','input_number': True, 'col':'4'}))

    archivo = ExtFileField(label=u'Fichero', required=False, help_text=u'Tamaño Máximo permitido 10Mb, en formato pdf',
                           ext_whitelist=(".pdf",), max_upload_size=10485760)
    matrizvaloracion = forms.BooleanField(initial=False, label=u'Considerar matriz de valoración?', required=False,
                                 widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))
    matrizevaluacion = forms.BooleanField(initial=False, label=u'Considerar matriz de evaluación?', required=False,
                                          widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))
    mostrar = forms.BooleanField(initial=True, label=u'Mostrar', required=False,
                             widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))

    def clean(self):
        cleaned_data = super().clean()
        anio = cleaned_data.get('anio')
        if len(PeriodoPoa.objects.filter(anio=anio, status=True)) > 2:
            self.add_error('anio', 'Año registrado ya existe')
        return cleaned_data

class ObjetivoEstrategicoForm(forms.Form):
    periodopoa = forms.ModelChoiceField(PeriodoPoa.objects.all(), label=u"Periodo POA", required=False)
    # departamento = forms.ModelChoiceField(Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), label=u"Departamento", required=False)
    departamento = forms.ModelChoiceField(Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), label=u"Departamento",
                                          required=False)
    carrera = forms.ModelChoiceField(Carrera.objects.all(), label=u"Carrera", required=False)
    programa = forms.ModelChoiceField(ProgramaPoa.objects.all(), label=u"Programa", required=False)
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'cols': '3', 'rows': 3}))
    orden = forms.IntegerField(initial=0, label=u"Orden",
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))

    def editar(self):
        deshabilitar_campo(self, 'periodopoa')
        deshabilitar_campo(self, 'departamento')
        deshabilitar_campo(self, 'programa')
        deshabilitar_campo(self, 'carrera')


class ObjetivoTacticoForm(forms.Form):
    periodopoa = forms.ModelChoiceField(PeriodoPoa.objects.all(), label=u"Periodo POA", required=False)
    objetivoestrategico = forms.ModelChoiceField(queryset=ObjetivoEstrategico.objects.all(),
                                                 label=u"Objetivo Estrategico", required=False)
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'cols': '3', 'rows': 3}))
    orden = forms.IntegerField(initial=0, label=u"Orden",
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))

    def query(self):
        self.fields['objetivoestrategico'].queryset = ObjetivoEstrategico.objects.filter(pk=None)

    def editar(self):
        deshabilitar_campo(self, 'periodopoa')
        deshabilitar_campo(self, 'objetivoestrategico')


class UsuarioEvidenciaForm(forms.Form):
    userpermiso = forms.IntegerField(initial=0, required=False, label=u'Usuario', widget=forms.Select({'col': '12', }))
    # userpermiso = forms.ModelChoiceField(label=u"Usuario",
    #                                      queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'),
    #                                      required=False, widget=forms.Select({'col': '12', }))
    unidadorganica = forms.ModelChoiceField(Departamento.objects.filter(objetivoestrategico__periodopoa_id__gte=2,
                                                                        objetivoestrategico__status=True,
                                                                        integrantes__isnull=False).distinct(),required=False, label=u'Departamento', widget=forms.Select())
    carrera = forms.ModelChoiceField(Carrera.objects.filter(status=True).order_by('nombre'), required=False,
                                     label=u'Carrera', widget=forms.Select())
    tipousuario = forms.ChoiceField(choices=TIPOS_USUARIO, required=False, label=u'Tipo Usuario',
                                    widget=forms.Select(attrs={'class': 'imp-25'}))

    def editar(self):
        deshabilitar_campo(self, 'userpermiso')


class UsuarioConsultaEvidenciaForm(forms.Form):
    # userpermiso = forms.CharField(max_length=200, label=u'Usuario', required=False,
    #                               widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    userpermiso = forms.ModelChoiceField(label=u"Usuario", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'),
                                         required=False, widget=forms.Select({'col': '12', }))

    unidadorganica = forms.ModelChoiceField(Departamento.objects.filter(objetivoestrategico__periodopoa_id__gte=2,
                                                                        objetivoestrategico__status=True).distinct(),
                                            required=False, label=u'Departamento', widget=forms.Select())

    def editar(self):
        deshabilitar_campo(self, 'userpermiso')


class ObjetivoOperativoForm(forms.Form):
    periodopoa = forms.ModelChoiceField(PeriodoPoa.objects.all(), label=u"Periodo POA", required=False)
    objetivoestrategico = forms.ModelChoiceField(queryset=ObjetivoEstrategico.objects.all(),
                                                 label=u"Objetivo Estrategico", required=False)
    objetivotactico = forms.ModelChoiceField(queryset=ObjetivoTactico.objects.all(), label=u"Objetivo Táctico",
                                             required=False)
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'cols': '3', 'rows': 3}))
    orden = forms.IntegerField(initial=0, label=u"Orden",
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))

    def query(self):
        self.fields['objetivoestrategico'].queryset = ObjetivoEstrategico.objects.filter(pk=None)
        self.fields['objetivotactico'].queryset = ObjetivoTactico.objects.filter(pk=None)

    def editar(self):
        deshabilitar_campo(self, 'periodopoa')
        deshabilitar_campo(self, 'objetivoestrategico')
        deshabilitar_campo(self, 'objetivotactico')


class IndicadoresPoaForm(forms.Form):
    periodopoa = forms.ModelChoiceField(PeriodoPoa.objects.all(), label=u"Periodo POA", required=False)
    objetivoestrategico = forms.ModelChoiceField(queryset=ObjetivoEstrategico.objects.all(),
                                                 label=u"Objetivo Estrategico", required=False)
    objetivotactico = forms.ModelChoiceField(queryset=ObjetivoTactico.objects.all(), label=u"Objetivo Táctico",
                                             required=False)
    objetivooperativo = forms.ModelChoiceField(queryset=ObjetivoOperativo.objects.all(), label=u"Objetivo Operativo",
                                               required=False)
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'cols': '3', 'rows': 3}))
    orden = forms.IntegerField(initial=0, label=u"Orden",
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))

    def query(self):
        self.fields['objetivoestrategico'].queryset = ObjetivoEstrategico.objects.filter(pk=None)
        self.fields['objetivotactico'].queryset = ObjetivoTactico.objects.filter(pk=None)
        self.fields['objetivooperativo'].queryset = ObjetivoOperativo.objects.filter(pk=None)

    def editar(self):
        deshabilitar_campo(self, 'periodopoa')
        deshabilitar_campo(self, 'objetivoestrategico')
        deshabilitar_campo(self, 'objetivotactico')
        deshabilitar_campo(self, 'objetivooperativo')


class MedioVerificacionPoaForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'cols': '3', 'rows': 3}))


class InformeArchivoForm(forms.Form):
    fechamax = forms.DateField(label=u"Fecha Máxima", input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    archivo = ExtFileField(label=u'Informe Final', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato PDF', ext_whitelist=(".pdf",),
                           max_upload_size=10485760)


class AperturaInformeForm(forms.Form):
    fechaodl = forms.DateField(label=u"Fecha Máxima Anterior", required=False, input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechanew = forms.DateField(label=u"Fecha Máxima Nueva", input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    motivo = forms.CharField(required=False, label=u'Motivo del cambio', widget=forms.Textarea({'rows': '4'}))

    def editar(self):
        deshabilitar_campo(self, 'fechaodl')


class AccionDocumentoDetalleForm(forms.Form):
    observacion_envia = forms.CharField(required=False, label=u'Cambios realizados', widget=forms.Textarea({'rows': '4'}))
    archivo = ExtFileField(label=u'Evidencia', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato PDF', ext_whitelist=(".pdf",),
                           max_upload_size=10485760)

class AccionDocumentoDetalleNewForm(FormModeloBase):
    meta = forms.ModelChoiceField(MetaPoa.objects.filter(status=True), label=u"Meta planificada", required=False,
                                  widget=forms.Select({'col': '6', 'class': 'select2'}))
    numero = forms.DecimalField(label=u"Meta ejecutada", required=True, initial=0,
                                widget=forms.TextInput({'input_group': '%', 'col': '6', 'class': 'input_money', 'w': '50'}))
    logros = forms.CharField(required=True, label=u'Logros', widget=forms.Textarea({'rows': '3', 'col': '6', 'maxlength': 300}))
    nudos = forms.CharField(required=True, label=u'Nudos críticos', widget=forms.Textarea({'rows': '3', 'col': '6', 'maxlength': 300}))
    observacion_envia = forms.CharField(required=True, label=u'Ajustes / Observaciones', widget=forms.Textarea({'rows': '3', 'col': '12', 'maxlength': 300}))
    archivo = forms.FileField(label=u'Archivo de evidencia', required=True,
                              help_text=u'Tamaño Máximo permitido 4Mb, en formato pdf y solo 10 paginas en el archivo',
                              widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'}))

    def clean(self):
        cleaned_data=super().clean()
        archivo = cleaned_data.get('archivo')
        instancia=self.instancia
        if archivo:
            max_tamano = 10 * 1024 * 1024  # 4 MB
            name_ = archivo._name
            ext = name_[name_.rfind("."):]
            if not ext.lower() == '.pdf':
                self.add_error('archivo', f'Solo se permite formato .pdf')
            if archivo.size > max_tamano:
                self.add_error('archivo', f'Archivo supera los 10 megas permitidos')
            # Asignar un nombre personalizado al archivo
            archivo.name = unidecode(generar_nombre("archivo_evidencia_", archivo._name))
        elif instancia:
            archivo=instancia.archivo
        cleaned_data['archivo'] = archivo
        return cleaned_data


class PrevalidacionForm(FormModeloBase):
    estadorevision = forms.ChoiceField(label=u'Estado', choices=choice_indice(ESTADO_REVISION_EVIDENCIA,(9, 7, 2, 3, 4)),
                                        initial=9, required=True, widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    numero = forms.DecimalField(label=u'¿Meta Ejecutada?', required=True, widget=forms.TextInput({'input_group': '%', 'col': '6', 'class': 'input_money', 'w': '60'}))
    aplica_calculo = forms.BooleanField(label=u'¿Aplica cálculo evaluación?', initial=True, required=False, widget=CheckboxInput({'col': '12', 'data-switchery': True}))
    observacion_validador = forms.CharField(required=True, label=u'Observación / Recomendación', widget=forms.Textarea({'rows': '3', 'col': '12'}))
    notificar = forms.BooleanField(label=u'¿Actualizar estado principal y notificar validación?', required=False, widget=CheckboxInput({'col': '12', 'data-switchery': True}))

class ValidacionPOAForm(FormModeloBase):
    estadorevision = forms.ChoiceField(label=u'Estado', choices=choice_indice(ESTADO_REVISION_EVIDENCIA, (6, 8, 7)), required=True, widget=forms.Select(attrs={'col': '4', 'class': 'select2'}))
    mensaje = forms.CharField(required=False, label=u'Mensaje a trasmitir', widget=forms.TextInput(attrs={'col': '8', 'placeholder': 'Motivo de devolución...'}))
    observacion_aprobacion = forms.CharField(required=True, label=u'Observación / Recomendación', widget=forms.Textarea({'rows': '9', 'col': '12'}))

class SeguimientoPoaForm(FormModeloBase):
    notificatodos = forms.BooleanField(label='¿Notificar a todos los registradores?', required=False,
                                     widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))
    persona = forms.ModelChoiceField(required=True, label=u'Registrador asignado', queryset=Persona.objects.select_related().filter(status=True).order_by(
                                         'apellido1'), widget=forms.Select({'col': '5', 'class': 'select2'}))
    estado = forms.ChoiceField(choices=ESTADO_SEGUIMIENTO_POA, required=True, label=u'Estado', initial=2,
                               widget=forms.Select(attrs={'col': '3', 'class': 'select2'}))
    fecha = forms.DateField(label=u'Fecha', required=False,
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '2'}))
    hora = forms.TimeField(label=u'Hora', required=False,
                            widget=DateTimeInput(format='%H:%M', attrs={'class': 'selector', 'col': '2'}))
    detalle = forms.CharField(required=False, label=u'Detalle', widget=forms.Textarea({'rows': '3', 'col': '12'}))
    observacion = forms.CharField(required=False, label=u'Seguimiento DPI', widget=forms.Textarea({'rows': '3', 'col': '12'}))

class EditarSeguimientoPoaForm(FormModeloBase):
    detalle = forms.CharField(required=False, label=u'Detalle', widget=forms.Textarea({'rows': '3', 'col': '12'}))
    observacion = forms.CharField(required=False, label=u'Seguimiento DPI', widget=forms.Textarea({'rows': '3', 'col': '12'}))

class AgendarSeguimientoPoaForm(FormModeloBase):
    notificatodos = forms.BooleanField(label='¿Notificar a todos los registradores?', required=False,
                                       widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))
    detalle = forms.CharField(required=False, label=u'Detalle', widget=forms.Textarea({'rows': '3', 'col': '12'}))
    fecha = forms.DateField(label=u'Fecha', required=True,
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '2'}))
    hora = forms.TimeField(label=u'Hora', required=True,
                           widget=DateTimeInput(format='%H:%M', attrs={'class': 'selector', 'col': '2'}))
class SolicitudSeguimientoPoaForm(FormModeloBase):
    detalle = forms.CharField(required=True, label=u'Detalle', widget=forms.Textarea({'rows': '3', 'col': '12'}))
    sugeirfecha = forms.BooleanField(label='¿Sugerir fecha y hora?', required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))
    fechasugerida = forms.DateField(label=u'Fecha sugerida', required=False,
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    horasugerida = forms.TimeField(label=u'Hora sugerida', required=False,
                            widget=DateTimeInput(format='%H:%M', attrs={'class': 'selector', 'col': '6'}))


class AccionDocumentoEditaDuplicaForm(forms.Form):
    estado_accion = forms.ChoiceField(choices=ESTADOS_ACCIONES, required=False, label=u'Estado', widget=forms.Select())
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '6'}))
    duplica = forms.BooleanField(label=u'Duplicar registro?', required=False, widget=CheckboxInput())

    def tipo_sin_evidencia(self):
        self.fields['estado_accion'].choices = (
            (1, 'NO CUMPLE'), (2, 'NO APLICA'), (3, 'PENDIENTE'), (5, 'CUMPLIMIENTO PARCIAL'), (6, 'CUMPLIMIENTO TOTAL'),)

    def bloquea_duplicado(self):
        deshabilitar_campo(self, 'duplica')


class AccionDocumentoRevisaForm(forms.Form):
    estado_accion = forms.ChoiceField(choices=ESTADOS_ACCIONES, required=False, label=u'Estado', widget=forms.Select())
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '6'}))

    def tipo_sin_evidencia(self, tipo):
        self.fields['estado_accion'].choices = (
            (1, 'NO CUMPLE'), (2, 'NO APLICA'), (3, 'PENDIENTE'), (5, 'CUMPLIMIENTO PARCIAL'), (6, 'CUMPLIMIENTO TOTAL'),)


class AccionDocumentoRevisaActividadForm(forms.Form):
    rubrica = forms.ModelChoiceField(queryset=RubricaPoa.objects.filter(status=True), label=u"Rubrica", required=False)
    fecha_evidencia = forms.DateField(label=u"Fecha evidencia", required=False, initial=datetime.now().date(),
                                      input_formats=['%d-%m-%Y'],
                                      widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '6'}))

    def tipo_sin_evidencia(self):
        self.fields['rubrica'].queryset = RubricaPoa.objects.filter(muestraformulario=True, status=True)
        # self.fields['estado_accion'].choices = ((1, 'DEFICIENTE'), (2, 'NO APLICA'), (3, 'PENDIENTE'), (5, 'POCO SASTIFACTORIO'), (6, 'SASTIFACTORIO'),(8, 'REGULAR'), (9, 'CUASI SASTIFACTORIO'),)


class ConstatacionForm(forms.Form):
    numero = forms.CharField(label=u'Numero', max_length=15, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-25'}))
    usuariobienes = forms.IntegerField(initial=0, required=False, label=u'Usuario Bien',
                                       widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '350px'}))
    ubicacionbienes = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicación bien',
                                             widget=forms.Select(attrs={'formwidth': '460px'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))

    def adicionar(self):
        self.fields['ubicacionbienes'].queryset = Ubicacion.objects.filter(id=None)
        del self.fields['numero']

    def editar(self, constatacion):
        deshabilitar_campo(self, 'usuariobienes')
        deshabilitar_campo(self, 'ubicacionbienes')
        deshabilitar_campo(self, 'numero')
        self.fields['usuariobienes'].widget.attrs['descripcion'] = constatacion.usuariobienes.nombre_completo()
        self.fields['usuariobienes'].initial = constatacion.usuariobienes.id

    def cambiar(self, constatacion):
        self.fields['usuariobienes'].widget.attrs['descripcion'] = constatacion.usuariobienes.nombre_completo()
        self.fields['usuariobienes'].initial = constatacion.usuariobienes.id


class DocumentosIndicadorPoaForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'cols': '3', 'rows': 3}))
    tipo = forms.ChoiceField(choices=TIPO_ACCION, required=False, label=u'Tipo',
                             widget=forms.Select(attrs={'class': 'imp-25'}))
    medioverificacion = forms.ModelChoiceField(queryset=MedioVerificacion.objects.filter(status=True),
                                               label=u"Medio Verificación", required=False)
    observacion = forms.CharField(label=u"Observación", widget=forms.Textarea(attrs={'cols': '3', 'rows': 3}),
                                  required=False)
    enlace = forms.CharField(label=u'Enlace', max_length=500, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-25'}))
    orden = forms.IntegerField(initial=0, label=u"Orden",
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    porcentaje = forms.DecimalField(initial='0.00', label=u"Porcentaje",
                                    widget=forms.TextInput(attrs={'class': 'imp-number'}))


class DetallesDocumentosIndicadorPoaForm(forms.Form):
    inicio = forms.DateField(label=u"Inicio", input_formats=['%d-%m-%Y'],
                             widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fin = forms.DateField(label=u"Fin", input_formats=['%d-%m-%Y'],
                          widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    mostrar = forms.BooleanField(label=u'Mostrar', required=False, widget=CheckboxInput())

class AccionDocumentosDetallePoaForm(FormModeloBase):
    inicio = forms.DateField(label=u"Inicio",
                             widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fin = forms.DateField(label=u"Fin",
                          widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    mostrar = forms.BooleanField(label=u'Mostrar', required=False, widget=CheckboxInput(attrs={'data-switchery':True}))

    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get('inicio')
        fin = cleaned_data.get('fin')
        instancia = self.instancia
        documento = getattr(instancia, 'acciondocumento', '')
        id = instancia.id if documento else 0
        eDocumento = documento if documento else instancia
        if eDocumento.acciondocumentodetalle_set.filter(status=True).filter(Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__lte=inicio, fin__gte=inicio)).exclude(id=id).exists():
            self.add_error('inicio', 'Ya existen acciones documentos que dan conflicto con este rango de fechas.')
            self.add_error('fin', 'Ya existen acciones documentos que dan conflicto con este rango de fechas.')
        if inicio > fin:
            self.add_error('inicio', "La fecha de inicio es mayor que la fecha fin")
        return cleaned_data

class TraspasoActivoForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '300px'}))
    tiposolicitud = forms.ChoiceField(choices=TIPO_SOLICITUD_TRASPASO_BAJA, required=False, label=u'Tipo Solicitud',
                                      widget=forms.Select(
                                          attrs={'class': 'imp-75', 'formwidth': '300px', 'labelwidth': '100px'}))
    oficio = forms.CharField(required=False, label=u'Oficio',
                             widget=forms.TextInput(attrs={'formwidth': '300px', 'labelwidth': '100px'}))
    fechaoficio = forms.DateField(label=u"Fecha Oficio/Email", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '300px'}))
    solicitante = forms.ModelChoiceField(Persona.objects.filter(perfilusuario__administrativo__isnull=False),
                                         required=False, label=u'U. solicitante',
                                         widget=forms.Select(attrs={'formwidth': '450px', 'separator': 'true'}))
    ubicacionbienentrega = forms.ModelChoiceField(Ubicacion.objects.filter(activofijo__isnull=False).distinct(),
                                                  required=False, label=u'Ubicación entrega', widget=forms.Select(
            attrs={'formwidth': '490px', 'separator': 'true'}))
    usuariobienentrega = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                                required=False, label=u'Usuario entrega',
                                                widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    custodiobienentrega = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                                 required=False, label=u'Custodio entrega', widget=forms.Select(
            attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    ubicacionbienrecibe = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicación recibe',
                                                 widget=forms.Select(attrs={'formwidth': '490px', 'separator': 'true'}))
    usuariobienrecibe = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                               required=False, label=u'Usuario recibe',
                                               widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    custodiobienrecibe = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                                required=False, label=u'Custodio Recibe',
                                                widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))

    def adicionar(self):
        self.fields['usuariobienentrega'].queryset = Persona.objects.filter(id=None)
        self.fields['custodiobienentrega'].queryset = Persona.objects.filter(id=None)

    def editar(self):
        deshabilitar_campo(self, 'fecha')
        deshabilitar_campo(self, 'ubicacionbienentrega')
        deshabilitar_campo(self, 'usuariobienentrega')
        deshabilitar_campo(self, 'custodiobienentrega')


class ArchivoActivoBajaForm(FormModeloBase):
    archivobaja = ExtFileField(label=u'Subir Archivo', required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato pdf',
                               ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'class':'w-100 '}))

class TraspasoActivoCustodioForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '300px'}))
    tiposolicitud = forms.ChoiceField(choices=TIPO_SOLICITUD_TRASPASO_BAJA, required=False, label=u'Tipo Solicitud',
                                      widget=forms.Select(
                                          attrs={'class': 'imp-75', 'formwidth': '300px', 'labelwidth': '100px'}))
    oficio = forms.CharField(required=False, label=u'Oficio',
                             widget=forms.TextInput(attrs={'formwidth': '300px', 'labelwidth': '100px'}))
    fechaoficio = forms.DateField(label=u"Fecha Oficio/Email", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '300px'}))
    solicitante = forms.ModelChoiceField(Persona.objects.filter(perfilusuario__administrativo__isnull=False),
                                         required=False, label=u'U. solicitante',
                                         widget=forms.Select(attrs={'formwidth': '450px'}))
    custodiobienentrega = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                                 required=False, label=u'Custodio entrega', widget=forms.Select(
            attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    custodiobienrecibe = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                                required=False, label=u'Custodio Recibe',
                                                widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    ubicacionbienentrega = forms.ModelChoiceField(Ubicacion.objects.filter(activofijo__isnull=False).distinct(),
                                                  required=False, label=u'Ubicación entrega',
                                                  widget=forms.Select(attrs={'formwidth': '550px'}))

    usuariobienrecibe = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                               required=False, label=u'Usuario recibe',
                                               widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))

    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))

    def adicionarcustodio(self):
        self.fields['custodiobienentrega'].queryset = Persona.objects.filter(custodioactivo__isnull=False,
                                                                             custodioactivo__statusactivo=1).distinct()
        self.fields['ubicacionbienentrega'].queryset = Persona.objects.filter(id=None)

    def editarcustodio(self):
        deshabilitar_campo(self, 'fecha')
        deshabilitar_campo(self, 'ubicacionbienentrega')
        deshabilitar_campo(self, 'custodiobienentrega')


class AsignacionActivoForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '15%'}))
    custodiobienrecibe = forms.ModelChoiceField(Persona.objects.filter(perfilusuario__administrativo__isnull=False),
                                                required=False, label=u'Custodio',
                                                widget=forms.Select(attrs={'formwidth': '40%'}))
    usuariobienrecibe = forms.ModelChoiceField(Persona.objects.filter(perfilusuario__administrativo__isnull=False),
                                               required=False, label=u'Usuario recibe',
                                               widget=forms.Select(attrs={'formwidth': '40%', 'separator': 'true'}))
    ubicacionbienrecibe = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicación recibe',
                                                 widget=forms.Select(attrs={'formwidth': '60%'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))

    def adicionar(self):
        deshabilitar_campo(self, 'numero')


class ConsultacatalogoForm(forms.Form):
    catalogo = forms.IntegerField(initial=0, required=False, label=u'Catálogo Bien',
                                  widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '800px'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=False,
                                         label=u'Responsable Bienes',
                                         widget=forms.Select(attrs={'formwidth': '500px', 'separator': 'true'}))
    fechadesde = forms.DateField(label=u"Fecha Ingreso Desde", required=False, initial=datetime.now().date(),
                                 input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                  attrs={'class': 'selectorfecha',
                                                                                         'formwidth': '20%'}))
    fechahasta = forms.DateField(label=u"Fecha Ingreso Hasta", required=False, initial=datetime.now().date(),
                                 input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                  attrs={'class': 'selectorfecha',
                                                                                         'formwidth': '20%'}))


class ConsultausuarioForm(forms.Form):
    responsable = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False),
        responsableactivo__isnull=False).distinct(), required=False, label=u'Responsable Bienes',
                                         widget=forms.Select(attrs={'formwidth': '450px'}))
    ubicacion = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicacion Bienes',
                                       widget=forms.Select(attrs={'formwidth': '600px'}))


class ActivoTraspasoForm(forms.Form):
    activo = forms.ModelChoiceField(ActivoFijo.objects.filter(status=True, statusactivo=1).all(), required=False,
                                    label=u'Activo', widget=forms.Select(attrs={'class': 'imp-50'}))


class DetalleTraspasoActivoForm(forms.Form):
    codigotraspaso = forms.ModelChoiceField(TraspasoActivo.objects.all(), required=False, label=u'Código Traspaso',
                                            widget=forms.Select(attrs={'class': 'imp-50'}))
    activo = forms.ModelChoiceField(ActivoFijo.objects.filter(status=True, statusactivo=1).all(), required=False,
                                    label=u'Activo', widget=forms.Select(attrs={'class': 'imp-50'}))


class TipoBajaForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-75'}))


class BajaActivoForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '280px'}))
    tiposolicitud = forms.ChoiceField(choices=TIPO_SOLICITUD_TRASPASO_BAJA, required=False, label=u'Tipo Solicitud',
                                      widget=forms.Select(attrs={'formwidth': '300px', 'labelwidth': '130px'}))
    tipobaja = forms.ModelChoiceField(TipoBaja.objects.all(), required=False, label=u'Tipo Baja',
                                      widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    fechaoficio = forms.DateField(label=u"Fecha Oficio", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '280px',
                                                                                          'separator': 'true'}))
    oficio = forms.CharField(required=False, label=u'#',
                             widget=forms.TextInput(attrs={'formwidth': '300px', 'labelwidth': '130px'}))
    solicitante = forms.ModelChoiceField(Persona.objects.filter(perfilusuario__administrativo__isnull=False),
                                         required=False, label=u'Usuario solicitante',
                                         widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    ubicacionbienentrega = forms.ModelChoiceField(Ubicacion.objects.all(), required=False, label=u'Ubicación',
                                                  widget=forms.Select(
                                                      attrs={'formwidth': '490px', 'separator': 'true'}))
    usuariobienentrega = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                                required=False, label=u'Usuario',
                                                widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    custodioentrega = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                             required=False, label=u'Custodio',
                                             widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))
    usuarioejecuta = forms.ModelChoiceField(Persona.objects.filter(perfilusuario__administrativo__isnull=False),
                                            required=False, label=u'Analista Activo Fijo', widget=forms.Select(
            attrs={'formwidth': '380px', 'labelwidth': '80px', 'separator': 'true'}))
    # usuariorecibe = forms.CharField(max_length=100, label=u"Recibe", widget=forms.TextInput(attrs={'formwidth': '490px'}))
    # cargorecibe = forms.CharField(max_length=300, label=u"Cargo Recibe", widget=forms.TextInput(attrs={'formwidth': '490px', 'labelwidth': '80px'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))
    experto = forms.ModelChoiceField(Persona.objects.filter(perfilusuario__administrativo__isnull=False),
                                     required=False, label=u'Experto', widget=forms.Select(
            attrs={'formwidth': '380px', 'labelwidth': '80px', 'separator': 'true'}))
    contadorper = forms.ModelChoiceField(Persona.objects.filter(perfilusuario__administrativo__isnull=False),
                                         required=False, label=u'Contador',
                                         widget=forms.Select(attrs={'formwidth': '380px', 'labelwidth': '80px'}))

    def adicionar(self):
        deshabilitar_campo(self, 'fecha')
        # deshabilitar_campo(self, 'tiposolicitud')
        # deshabilitar_campo(self, 'tipobaja')
        # deshabilitar_campo(self, 'fechaoficio')
        # deshabilitar_campo(self, 'oficio')

        # deshabilitar_campo(self, 'usuariobienentrega')
        # deshabilitar_campo(self, 'custodioentrega')
        # deshabilitar_campo(self, 'ubicacionbienentrega')

        deshabilitar_campo(self, 'experto')
        deshabilitar_campo(self, 'contadorper')
        # deshabilitar_campo(self, 'usuarioejecuta')


class DetalleBajaActivoForm(forms.Form):
    activo = forms.ModelChoiceField(ActivoFijo.objects.filter(status=True, statusactivo=1).all(), required=False,
                                    label=u'Activo', widget=forms.Select(attrs={'class': 'imp-50'}))


class TrasladoMantenimientoForm(forms.Form):
    departamentosolicita = forms.ModelChoiceField(
        Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), required=False,
        label=u'Departamento solicitante', widget=forms.Select(attrs={'formwidth': '700px'}))
    asistentelogistica = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                                required=False, label=u'A.Logistica/Dir.Depar.',
                                                widget=forms.Select(attrs={'formwidth': '50%', 'separator': 'true'}))
    usuariobienes = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False),
        responsableactivo__isnull=False).distinct(), required=False, label=u'Usuario bien',
                                           widget=forms.Select(attrs={'formwidth': '50%'}))
    taller = forms.ModelChoiceField(TallerMantenimiento.objects.all(), required=False, label=u'Empresa o taller',
                                    widget=forms.Select(attrs={'formwidth': '50%'}))
    administradorcontrato = forms.ModelChoiceField(Persona.objects.filter(
        Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(),
                                                   required=False, label=u'Técnico que Reporto',
                                                   widget=forms.Select(attrs={'formwidth': '50%'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))

    def editar(self):
        deshabilitar_campo(self, 'usuariobienes')
        deshabilitar_campo(self, 'departamentosolicita')
        deshabilitar_campo(self, 'asistentelogistica')
        deshabilitar_campo(self, 'taller')
        deshabilitar_campo(self, 'administradorcontrato')


class DetalleTrasladoMantenimientoForm(forms.Form):
    activo = forms.ModelChoiceField(ActivoFijo.objects.filter(status=True, statusactivo=1).all(), required=False,
                                    label=u'Activo', widget=forms.Select(attrs={'class': 'imp-50'}))
    observaciondet = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))


class TarjetaControlForm(forms.Form):
    activo = forms.ModelChoiceField(ActivoFijo.objects.filter(status=True, statusactivo=1).all(), required=False,
                                    label=u'Activo', widget=forms.Select(attrs={'class': 'imp-50'}))
    origenregistro = forms.ChoiceField(choices=ORIGEN_REGISTRO, label=u'Origen de Registro', required=False,
                                       widget=forms.Select(attrs={'class': 'imp-50'}))


class DetalleTarjetaControlForm(forms.Form):
    codigobara = forms.CharField(required=False, label=u'Código de Barra',
                                 widget=forms.TextInput(attrs={'class': 'imp-comprobantes', 'formwidth': '300px'}))
    fechacompra = forms.DateField(label=u"Fecha Compra", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '200px'}))
    catalogo = forms.CharField(required=False, label=u'Catálogo', widget=forms.TextInput(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(required=False, label=u'Descripción',
                                  widget=forms.TextInput(attrs={'formwidth': '100%'}))
    traslado = forms.CharField(required=False, label=u'N° Traslado',
                               widget=forms.TextInput(attrs={'class': 'imp-comprobantes', 'formwidth': '300px'}))
    fechaentrega = forms.DateField(label=u"Fecha Entrega", required=False, initial=datetime.now().date(),
                                   input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                    attrs={'class': 'selectorfecha',
                                                                                           'formwidth': '200px'}))
    # taller = forms.CharField(required=False, label=u'Descripción', widget=forms.TextInput(attrs={'formwidth': '100%'}))
    fecharecepcion = forms.DateField(label=u"Fecha Recepción", required=False, initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '200px',
                                                                                             'separator': 'true'}))
    taller = forms.ModelChoiceField(TallerMantenimiento.objects.all(), required=False, label=u'Empresa o taller',
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    mantenimientorealizar = forms.CharField(required=False, label=u'Mantenimiento a Realizar',
                                            widget=forms.Textarea({'rows': '2'}))
    mantenimientorealizado = forms.CharField(required=False, label=u'Mantenimiento Realizado',
                                             widget=forms.Textarea({'rows': '2'}))
    observacion = forms.CharField(required=False, label=u'Observacion', widget=forms.Textarea({'rows': '2'}))
    aplicagarantia = forms.BooleanField(initial=True, required=False, label=u"Aplica Garantía")
    manodeobra = forms.BooleanField(initial=False, required=False, label=u"Mano de Obra")
    costomanodeobra = forms.DecimalField(initial='0.00', label=u'Costo Mano de Obra $', required=False,
                                         widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '300px'}))
    facturamanodeobra = forms.CharField(label=u'Factura Mano Obra', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-comprobantes', 'formwidth': '400px'}))
    repuestos = forms.BooleanField(initial=False, required=False, label=u"Repuestos")
    costomanodereparacion = forms.DecimalField(initial='0.00', label=u'Costo Repuesto $', required=False,
                                               widget=forms.TextInput(
                                                   attrs={'class': 'imp-moneda', 'formwidth': '300px'}))
    facturareparacion = forms.CharField(label=u'Factura Repuesto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-comprobantes', 'formwidth': '300px'}))

    def editar(self):
        deshabilitar_campo(self, 'mantenimientorealizar')
        deshabilitar_campo(self, 'codigobara')
        deshabilitar_campo(self, 'catalogo')
        deshabilitar_campo(self, 'descripcion')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'traslado')
        deshabilitar_campo(self, 'taller')
        deshabilitar_campo(self, 'fechaentrega')

    def agregar(self):
        deshabilitar_campo(self, 'codigobara')
        deshabilitar_campo(self, 'catalogo')
        deshabilitar_campo(self, 'descripcion')
        deshabilitar_campo(self, 'fechacompra')
        del self.fields['fecharecepcion']
        del self.fields['traslado']
        del self.fields['manodeobra']
        del self.fields['costomanodeobra']
        del self.fields['facturamanodeobra']
        del self.fields['repuestos']
        del self.fields['costomanodereparacion']
        del self.fields['facturareparacion']
        del self.fields['mantenimientorealizado']

    def ingreso(self):
        deshabilitar_campo(self, 'codigobara')
        deshabilitar_campo(self, 'catalogo')
        deshabilitar_campo(self, 'descripcion')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'traslado')
        deshabilitar_campo(self, 'taller')
        deshabilitar_campo(self, 'fechaentrega')
        deshabilitar_campo(self, 'mantenimientorealizar')


class DetalleNoIdentificadoForm(forms.Form):
    codigobarra = forms.CharField(required=False, label=u'Código de Barra',
                                  widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    catalogobien = forms.IntegerField(initial=0, required=False, label=u'Catálogo Bien',
                                      widget=forms.TextInput(attrs={'select2search': 'true'}))
    descripcion = forms.CharField(required=False, label=u'Descripción',
                                  widget=forms.Textarea(attrs={'rows': '3', 'formwidth': '100%'}))
    serie = forms.CharField(label=u"Serie", required=False, widget=forms.TextInput(attrs={'formwidth': '50%'}))
    modelo = forms.CharField(label=u"Modelo", required=False, widget=forms.TextInput(attrs={'formwidth': '50%'}))
    marca = forms.CharField(label=u"Marca", required=False, widget=forms.TextInput(attrs={'formwidth': '50%'}))
    estado = forms.ModelChoiceField(EstadoProducto.objects.all(), required=False, label=u'Estado',
                                    widget=forms.Select(attrs={'formwidth': '50%'}))

    def editar(self, detalle):
        self.fields['catalogobien'].widget.attrs['descripcion'] = detalle.catalogobien.descripcion
        self.fields['catalogobien'].initial = detalle.catalogobien.id


class DatosPersonalesForm(FormModeloBase):
    from sga.models import Sexo, Credo, PreferenciaPolitica
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False,
                              widget=forms.TextInput(attrs={'col': '12'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'col': '6'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'col': '6'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False,
                             widget=forms.TextInput(attrs={'col': '6'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, required=False,
                                widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Digite su número de pasaporte.'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=True, queryset=Sexo.objects.filter(status=True),
                                  widget=forms.Select(attrs={'col': '2','class':'select2'}))
    estadocivil = forms.ModelChoiceField(label=u'Estado civil', queryset=PersonaEstadoCivil.objects.filter(status=True), required=True,
                                         widget=forms.Select(attrs={'col': '4','class':'select2'}))
    nacimiento = forms.DateField(label=u"Fecha nacimiento", required=True,
                                 widget=DateTimeInput(format='%d-%m-%Y',
                                                      attrs={'col': '3'}))
    # nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=False,
    #                                widget=forms.TextInput(attrs={'class': 'imp-75', 'formwidth': '50%'}))
    anioresidencia = forms.IntegerField(initial=0, label=u'Años de residencia', required=False,
                                        widget=forms.TextInput(attrs={'col': '3', 'decimal': '0'}))
    email = forms.CharField(label=u"Correo electrónico personal", max_length=200, required=False,
                            widget=forms.TextInput(attrs={'col': '6'}))
    libretamilitar = forms.CharField(label=u"Libreta militar", max_length=20, required=False,
                                     widget=forms.TextInput(attrs={'col': '6'}))
    extension = forms.CharField(label=u'Extensión telefónica institucional', max_length=20, required=False,
                                widget=forms.TextInput(attrs={'col': '6'}))
    lgtbi = forms.BooleanField(label=u"¿Pertenece al Grupo LGTBI?", required=False,
                               widget=forms.CheckboxInput(attrs={'col': '4','data-switchery':True}))
    eszurdo = forms.BooleanField(label=u'¿Es Zurdo?', required=False,
                                 widget=forms.CheckboxInput(attrs={'col': '2','data-switchery':True}))
    raza = forms.ModelChoiceField(label=u"Etnia", queryset=Raza.objects.filter(status=True), required=True,
                                  widget=forms.Select(attrs={'col': '6','class':'select2'}))
    nacionalidadindigena = forms.ModelChoiceField(label=u"Nacionalidad indígena",
                                                  queryset=NacionalidadIndigena.objects.filter(status=True), required=False,
                                                  widget=forms.Select(attrs={'col': '6','class':'select2'}))
    # agendacitas = forms.CharField(label=u'Url de agenda de citas', max_length=200, required=False,
    #                             widget=forms.TextInput(attrs={'col': '12'}))
    archivocedula = ExtFileField(label=u'Documento Cédula', required=False,
                                 help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                 widget=forms.FileInput({'col': '6'}),
                                 max_upload_size=4194304)
    papeleta = ExtFileField(label=u'Documento Certificado Votación', required=False,
                            help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                            widget=forms.FileInput({'col': '6'}),
                            max_upload_size=4194304)
    archivolibretamilitar = ExtFileField(label=u'Documento Libreta militar', required=False,
                                         help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                         widget=forms.FileInput({'col': '6'}),
                                         ext_whitelist=(".pdf",), max_upload_size=4194304)
    archivoraza = ExtFileField(label=u'Documento que garantiza la nacionalidad indígena', required=False,
                               help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                               widget=forms.FileInput({'col': '6'}),
                               max_upload_size=4194304)

    # estadogestacion = forms.BooleanField(label = u'Se escuentra en estado de gestiación?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    # semanasembarazo = forms.IntegerField(initial=0, label=u'Semanas de Embarazo', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    # lactancia = forms.BooleanField(label = u'Se escuentra en estado de lactancia?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    # fechaparto = forms.DateField(label=u"Fecha de parto", required=False, input_formats=['%d-%m-%Y'],
    #                              widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    # credo = forms.ModelChoiceField(Credo.objects.filter(activo=True, status=True).order_by('nombre'), required=False, label=u'Seleccione Credo')
    # preferenciapolitica = forms.ModelChoiceField(PreferenciaPolitica.objects.filter(activo=True, status=True).order_by('nombre'), required=False, label=u'Seleccione Preferencia Política')

    def editar(self, sinnombres=True):
        if sinnombres:
            deshabilitar_campo(self, 'nombres')
            deshabilitar_campo(self, 'apellido1')
            deshabilitar_campo(self, 'apellido2')
        deshabilitar_campo(self, 'cedula')

    def es_estudiante(self):
        del self.fields['extension']

    def __init__(self, *args, **kwargs):
        super(DatosPersonalesForm, self).__init__(*args, **kwargs)  # Esto siempre hay que ponerlo
        for field in self.fields:
            self.fields[field].error_messages = {'required': f'Este campo es obligatorio'}

class DatosPersonalesAspiranteForm(FormModeloBase):
    from sga.models import Sexo, Credo, PreferenciaPolitica
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False, widget=forms.TextInput({'col': '12'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput({'col': '12'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput({'col': '12'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula', 'col':'6'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula', 'col':'6'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=True, queryset=Sexo.objects.all(), widget=forms.Select(attrs={'col': '6'}))
    estadocivil = forms.ModelChoiceField(label=u'Estado civil', queryset=PersonaEstadoCivil.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '6'}))
    nacimiento = forms.DateField(label=u"Fecha nacimiento", required=True, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    anioresidencia = forms.IntegerField(initial=0, label=u'Años de residencia', required=False,
                                        widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    email = forms.CharField(label=u"Correo electrónico personal", max_length=200, required=False,
                            widget=forms.TextInput(attrs={'col': '12'}))
    libretamilitar = forms.CharField(label=u"Libreta militar", max_length=20, required=False,
                                     widget=forms.TextInput(attrs={'col': '12'}))
    archivocedula = ExtFileField(label=u'Documento Cédula', required=False,
                                 help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                 max_upload_size=4194304,
                                 widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    papeleta = ExtFileField(label=u'Documento Certificado Votación', required=False,
                            help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                            max_upload_size=4194304,
                            widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    archivolibretamilitar = ExtFileField(label=u'Documento Libreta militar', required=False,
                                         help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                         ext_whitelist=(".pdf",), max_upload_size=4194304,
                                         widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    extension = forms.CharField(label=u'Extensión telefónica institucional', max_length=20, required=False,
                                widget=forms.TextInput(attrs={'col': '12'}))
    lgtbi = forms.BooleanField(label=u"Pertenece al Grupo LGTBI?", required=False,
                               widget=forms.CheckboxInput(attrs={'col': '12'}))
    eszurdo = forms.BooleanField(label=u'Es Zurdo?', required=False,
                                 widget=forms.CheckboxInput(attrs={'col': '12'}))

    def editar(self, sinnombres=True):
        if sinnombres:
            deshabilitar_campo(self, 'nombres')
            deshabilitar_campo(self, 'apellido1')
            deshabilitar_campo(self, 'apellido2')
        deshabilitar_campo(self, 'cedula')

    def es_estudiante(self):
        del self.fields['extension']

    def __init__(self, *args, **kwargs):
        super(DatosPersonalesAspiranteForm, self).__init__(*args, **kwargs)  # Esto siempre hay que ponerlo
        for field in self.fields:
            self.fields[field].error_messages = {'required': f'Este campo es obligatorio'}

class PersonaDetalleMaternidad(FormModeloBase):
    iniciogestacion = forms.DateField(label=u"Inicio de gestación", initial=None, required=True,
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '9'}))
    semanasembarazo = forms.IntegerField(initial=0, label=u'Semanas de Embarazo', required=False,
                                         widget=forms.TextInput(
                                             attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '4'}))
    estadogestacion = forms.BooleanField(label=u'¿Se escuentra en estado de gestación?', required=False,
                                         widget=forms.CheckboxInput(attrs={'col': '4','data-switchery':True}))

    fechaparto = forms.DateField(label=u"Fecha de parto", required=False,
                                 widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '9'}))
    lactancia = forms.BooleanField(label=u'Se escuentra en periodo de lactancia?', required=False,
                                   widget=forms.CheckboxInput(attrs={'col': '4','data-switchery':True}))

class PersonaDetalleMaternidadForm(FormModeloBase):
    fechainicioembarazo = forms.DateField(label=u"Inicio de gestación", initial=None, required=True,
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    semanasembarazo = forms.IntegerField(initial=0, label=u'Semanas de Embarazo', required=False,
                                         widget=forms.TextInput(
                                             attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    gestacion = forms.BooleanField(label=u'¿Se escuentra en estado de gestación?', required=False,
                                         widget=forms.CheckboxInput(attrs={'col': '6','data-switchery':True}))

    fechaparto = forms.DateField(label=u"Fecha de parto", required=False,
                                 widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    lactancia = forms.BooleanField(label=u'Se escuentra en periodo de lactancia?', required=False,
                                   widget=forms.CheckboxInput(attrs={'col': '6','data-switchery':True}))


class PersonaDetalleMaternidadAspiranteForm(FormModeloBase):
    estadogestacion = forms.BooleanField(label=u'Se escuentra en estado de gestación?', required=False,
                                         widget=forms.CheckboxInput(attrs={'col': '12'}))
    semanasembarazo = forms.IntegerField(initial=0, label=u'Semanas de Embarazo', required=False,
                                         widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '12'}))
    lactancia = forms.BooleanField(label=u'Se escuentra en estado de lactancia?', required=False,
                                   widget=forms.CheckboxInput(attrs={'col': '12'}))
    fechaparto = forms.DateField(label=u"Fecha de parto", required=False,
                                 widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))

class DatosNacimientoForm(FormModeloBase):
    paisnacimiento = forms.ModelChoiceField(label=u"País de nacimiento", queryset=Pais.objects.all(), required=False,
                                            widget=forms.Select({'col':'6', 'class':'select2'}))
    provincianacimiento = forms.ModelChoiceField(label=u"Provincia de nacimiento", queryset=Provincia.objects.all(),
                                                 required=False, widget=forms.Select({'col':'6', 'class':'select2'}))
    cantonnacimiento = forms.ModelChoiceField(label=u"Cantón de nacimiento", queryset=Canton.objects.all(),
                                              required=False, widget=forms.Select({'col':'6', 'class':'select2'}))
    parroquianacimiento = forms.ModelChoiceField(label=u"Parroquia de nacimiento", queryset=Parroquia.objects.all(),
                                                 required=False, widget=forms.Select({'col':'6', 'class':'select2'}))
    paisnacionalidad = forms.ModelChoiceField(label=u"País de nacionalidad", queryset=Pais.objects.all(), required=False,
                                            widget=forms.Select({'col': '12', 'class':'select2'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Modificar la etiqueta y el queryset para mostrar la combinación personalizada
        self.fields['paisnacionalidad'].label_from_instance = self.label_from_instance

    def label_from_instance(self, obj):
        if obj.nacionalidad:
            return f"{obj.nombre} ({obj.nacionalidad})"
        else:
            return f"{obj.nombre}"


    def editar(self, persona):
        self.fields['provincianacimiento'].queryset = Provincia.objects.filter(pais=persona.paisnacimiento)
        self.fields['cantonnacimiento'].queryset = Canton.objects.filter(provincia=persona.provincianacimiento)
        self.fields['parroquianacimiento'].queryset = Parroquia.objects.filter(canton=persona.cantonnacimiento)

class DatosNacimientoAspiranteForm(FormModeloBase):
    paisnacimiento = forms.ModelChoiceField(label=u"País de nacimiento", queryset=Pais.objects.all(), required=False,
                                            widget=forms.Select(attrs={'col': '12'}))
    provincianacimiento = forms.ModelChoiceField(label=u"Provincia de nacimiento", queryset=Provincia.objects.all(),
                                                 required=False, widget=forms.Select(attrs={'col': '12'}))
    cantonnacimiento = forms.ModelChoiceField(label=u"Cantón de nacimiento", queryset=Canton.objects.all(),
                                              required=False, widget=forms.Select(attrs={'col': '12'}))
    parroquianacimiento = forms.ModelChoiceField(label=u"Parroquia de nacimiento", queryset=Parroquia.objects.all(),
                                                 required=False, widget=forms.Select(attrs={'col': '12'}))
    nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=False,
                                   widget=forms.TextInput({'col': '12'}))

    def editar(self, persona):
        self.fields['provincianacimiento'].queryset = Provincia.objects.filter(pais=persona.paisnacimiento)
        self.fields['cantonnacimiento'].queryset = Canton.objects.filter(provincia=persona.provincianacimiento)
        self.fields['parroquianacimiento'].queryset = Parroquia.objects.filter(canton=persona.cantonnacimiento)

class DatosDomicilioForm(forms.Form):
    pais = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.all(), required=True,
                                  widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects.all(),
                                       required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    canton = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects.all(),
                                       required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    direccion = forms.CharField(label=u'Calle principal', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'6'}))
    direccion2 = forms.CharField(label=u'Calle secundaria', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'6'}))
    num_direccion = forms.CharField(label=u'Número de casa', max_length=15, required=True,
                                    widget=forms.TextInput(attrs={'col':'6'}))
    referencia = forms.CharField(label=u'Referencia', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'6'}))
    ciudadela = forms.CharField(label=u'Ciudadela', max_length=100, required=False, widget=forms.TextInput(attrs={'col':'6'}))
    sector = forms.CharField(label=u'Sector', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'6'}))
    telefono = forms.CharField(label=u'Teléfono celular', max_length=15, required=True,
                               widget=forms.TextInput(attrs={'col':'3'}))
    telefono_conv = forms.CharField(label=u'Teléfono domicilio (fijo)', max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'col':'3'}))
    tipocelular = forms.ChoiceField(label=u'Operadora móvil', choices=TIPO_CELULAR, required=True,
                                    widget=forms.Select(attrs={'col':'3','class':'select2'}))
    zona = forms.ChoiceField(label=u"Zona de residencia", choices=ZONA_DOMICILIO, required=True, widget=forms.Select(attrs={'col':'3','class':'select2'}))
    archivocroquis = ExtFileField(label=u'Croquis', required=False,
                                  help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                  widget=forms.FileInput(attrs={'col':'6','accept':'.pdf'}),
                                  max_upload_size=2194304)
    archivoplanillaluz = ExtFileField(label=u'Planilla de Luz', required=False,
                                  help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                  widget=forms.FileInput(attrs={'col': '6', 'accept': '.pdf'}),
                                  max_upload_size=2194304)
    serviciosbasico = ExtFileField(label=u'Servicios basicos', required=False,
                                  help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                  widget=forms.FileInput(attrs={'col': '6', 'accept': '.pdf'}),
                                  max_upload_size=2194304)
    def editar(self, persona):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)

class DatosDomicilioAdmisionForm(FormModeloBase):
    pais = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.all(), required=True,
                                  widget=forms.Select(attrs={'col': '12'}))
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects.all(),
                                       required=False, widget=forms.Select(attrs={'col': '12'}))
    canton = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'col': '12'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects.all(),
                                       required=False, widget=forms.Select(attrs={'col': '12'}))
    direccion = forms.CharField(label=u'Calle principal', max_length=100, required=True, widget=forms.TextInput({'col': '12'}))
    direccion2 = forms.CharField(label=u'Calle secundaria', max_length=100, required=True, widget=forms.TextInput({'col': '12'}))
    num_direccion = forms.CharField(label=u'Número de casa', max_length=15, required=True,
                                    widget=forms.TextInput({'col': '6'}))
    referencia = forms.CharField(label=u'Referencia', max_length=100, required=True, widget=forms.TextInput({'col': '12'}))
    ciudadela = forms.CharField(label=u'Ciudadela', max_length=100, required=False, widget=forms.TextInput({'col': '12'}))
    sector = forms.CharField(label=u'Sector', max_length=100, required=True, widget=forms.TextInput({'col': '12'}))
    telefono = forms.CharField(label=u'Teléfono celular', max_length=15, required=True,
                               widget=forms.TextInput({'col': '6'}))
    telefono_conv = forms.CharField(label=u'Teléfono domicilio (fijo)', max_length=15, required=False,
                                    widget=forms.TextInput({'col': '6'}))
    tipocelular = forms.ChoiceField(label=u'Operadora móvil', choices=TIPO_CELULAR, required=True,
                                    widget=forms.Select(attrs={'col': '12'}))
    archivocroquis = ExtFileField(label=u'Croquis', required=False,
                                  help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                  max_upload_size=2194304,
                                  widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    zona = forms.ChoiceField(label=u"Zona de residencia", choices=ZONA_DOMICILIO, required=True, widget=forms.Select(attrs={'col': '6'}))
    archivoplanillaluz = ExtFileField(label=u'Planilla de Luz', required=False,
                                  help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                  max_upload_size=2194304,
                                  widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    serviciosbasico = ExtFileField(label=u'Servicios basicos', required=False,
                                  help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                  max_upload_size=2194304,
                                  widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    def editar(self, persona):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)

class ContactoEmergenciaForm(FormModeloBase):
    contactoemergencia = forms.CharField(label=u'Nombre', max_length=200, required=True,
                                         widget=forms.TextInput({'col': '12'}))
    parentescoemergencia = forms.ModelChoiceField(label=u"Parentesco", queryset=ParentescoPersona.objects.all(),
                                                  required=True, widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    telefonoemergencia = forms.CharField(label=u'Teléfono de emergencia', max_length=10, required=True,
                                         widget=forms.TextInput({'col': '6'}))
    telefonoconvemergencia = forms.CharField(label=u'Teléfono conv. de emergencia', max_length=10, required=False,
                                         widget=forms.TextInput({'col': '6'}))
    correoemergencia = forms.CharField(label=u'Correo de emergencia', max_length=200, required=False,
                                         widget=forms.TextInput({'col': '12'}))

class ContactoEmergenciaAspiranteForm(FormModeloBase):
    contactoemergencia = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput({'col': '12'}))
    parentescoemergencia = forms.ModelChoiceField(label=u"Parentesco", queryset=ParentescoPersona.objects.all(),
                                                  required=True, widget=forms.Select(attrs={'col': '6'}))
    telefonoemergencia = forms.CharField(label=u'Teléfono de emergencia', max_length=10, required=True,
                                         widget=forms.TextInput({'col': '12'}))


class EtniaForm(forms.Form):
    raza = forms.ModelChoiceField(label=u"Etnia", queryset=Raza.objects.all(), required=True,
                                  widget=forms.Select(attrs={'formwidth': '60%'}))
    nacionalidadindigena = forms.ModelChoiceField(label=u"Nacionalidad indigena",
                                                  queryset=NacionalidadIndigena.objects.all(), required=False,
                                                  widget=forms.Select())
    archivoraza = ExtFileField(label=u'Documento garantiza', required=False,
                               help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                               max_upload_size=4194304)

class EtniaAspiranteForm(FormModeloBase):
    raza = forms.ModelChoiceField(label=u"Etnia", queryset=Raza.objects.all(), required=True,
                                  widget=forms.Select(attrs={'col': '12'}))
    nacionalidadindigena = forms.ModelChoiceField(label=u"Nacionalidad indigena",
                                                  queryset=NacionalidadIndigena.objects.all(), required=False,
                                                  widget=forms.Select(attrs={'col': '12'}))
    archivoraza = ExtFileField(label=u'Documento garantiza', required=False,
                               help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                               max_upload_size=4194304,
                               widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))

class DiscapacidadForm(FormModeloBase):
    tienediscapacidad = forms.BooleanField(label=u'Tiene Discapacidad?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad",
                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                              widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    subtipodiscapacidad = forms.ModelMultipleChoiceField(label=u"Sub Tipo de Discapacidad",
                                                              queryset=SubTipoDiscapacidad.objects.filter(status=True), required=False,
                                                              widget=forms.SelectMultiple(attrs={'multiple': 'multiple', 'class':'select2'}))
    grado = forms.ChoiceField(label=u"Grado de Discapacidad", choices=GRADO, required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    institucionvalida = forms.ModelChoiceField(label=u"Institución Valida",
                                               queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True),
                                               required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False,
                                             widget=forms.TextInput(attrs={'col':'6'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet Discapacitado', max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'col':'6'}))
    tienediscapacidadmultiple = forms.BooleanField(label=u'Tiene Discapacidad multiple?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    tipodiscapacidadmultiple = forms.ModelMultipleChoiceField(label=u"Tipo de Discapacidad Multiple",
                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                              widget=forms.SelectMultiple(attrs={'multiple': 'multiple','col':'6', 'class':'select2'}))
    archivovaloracion = ExtFileField(label=u'Documento de valoración médica', required=False,
                                     help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                     widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'pdf'}),
                                     max_upload_size=4194304)
    archivo = ExtFileField(label=u'Carnet de Discapacidad', required=False,
                           widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'pdf'}),
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304)

    def ocultarcampos(self):
        del self.fields['tienediscapacidad']

    def bloquearcampos(self):
        deshabilitar_campo(self, 'tipodiscapacidad')

class DiscapacidadAspiranteForm(FormModeloBase):
    tienediscapacidad = forms.BooleanField(label=u'Tiene Discapacidad?', required=False, widget=forms.CheckboxInput(attrs={'col': '12'}))
    archivovaloracion = ExtFileField(label=u'Documento de valoración médica', required=False,
                                     help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                     max_upload_size=4194304,
                                     widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad",
                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                              widget=forms.Select(attrs={'col': '12'}))
    subtipodiscapacidad = forms.ModelMultipleChoiceField(label=u"Sub Tipo de Discapacidad",
                                                              queryset=SubTipoDiscapacidad.objects.filter(status=True), required=False,
                                                              widget=forms.SelectMultiple(attrs={'col': '12'}))
    grado = forms.ChoiceField(label=u"Grado de Discapacidad", choices=GRADO, required=False, widget=forms.Select(attrs={'col': '12'}))
    institucionvalida = forms.ModelChoiceField(label=u"Institución Valida",
                                               queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True),
                                               required=False, widget=forms.Select(attrs={'col': '12'}))
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False,
                                             widget=forms.TextInput(attrs={'col': '12'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet Discapacitado', max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'col': '12'}))
    archivo = ExtFileField(label=u'Carnet de Discapacidad', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))

    tienediscapacidadmultiple = forms.BooleanField(label=u'Tiene Discapacidad multiple?', required=False, widget=forms.CheckboxInput(attrs={'col': '12'}))
    tipodiscapacidadmultiple = forms.ModelMultipleChoiceField(label=u"Tipo de Discapacidad Multiple",
                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                              widget=forms.SelectMultiple(attrs={'col': '12'}))

    def ocultarcampos(self):
        del self.fields['tienediscapacidad']

    def bloquearcampos(self):
        deshabilitar_campo(self, 'tipodiscapacidad')

class DiscapacidadForm2(forms.Form):
    tienediscapacidad = forms.BooleanField(label=u'Tiene Discapacidad?', required=False, widget=CheckboxInput())
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad",
                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                              widget=forms.Select())
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False,
                                             widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    carnetdiscapacidad = forms.CharField(label=u'Carnet Discapacitado', max_length=50, required=False,
                                         widget=forms.TextInput())
    archivo = ExtFileField(label=u'Subir Carnet de Discapacidad', required=False,
                           help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=2194304)
    verificadiscapacidad = forms.BooleanField(label=u'Verificado?', required=False, widget=CheckboxInput())


class FamiliarForm(FormModeloBase):
    # DATOS BÁSICOS
    tipoidentificacion = forms.ChoiceField(label=u"Documento", required=True,
                                            choices=[TIPOS_IDENTIFICACION[0], TIPOS_IDENTIFICACION[2]],
                                            widget=forms.Select(attrs={'col': '2', 'class':'select2'}))
    identificacion = forms.CharField(label=u"Número de identificación", max_length=10, required=True,
                                     widget=forms.TextInput(attrs={'col': '4', 'placeholder':'Digite su número de identificación'}))
    parentesco = forms.ModelChoiceField(label=u"Parentesco", queryset=ParentescoPersona.objects.filter(status=True), required=True,
                                        widget=forms.Select(attrs={'col': '4', 'class':'select2'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", queryset=Sexo.objects.filter(status=True), required=True,
                                        widget=forms.Select(attrs={'col': '2', 'class': 'select2'}))
    nombre = forms.CharField(max_length=200, label=u'Nombres', required=True,widget=forms.TextInput(attrs={'col':'6','placeholder':'Describa los nombres del familiar'}))
    apellido1 = forms.CharField(max_length=200, label=u'Primer apellido', required=True, widget=forms.TextInput(attrs={'col':'3', 'placeholder':'Describa el primer apellido'}))
    apellido2 = forms.CharField(max_length=200, label=u'Segundo apellido', required=True, widget=forms.TextInput(attrs={'col':'3', 'placeholder':'Describa el segundo apellido'}))
    nacimiento = forms.DateField(label=u"Fecha nacimiento", initial=None, required=True,
                                 # input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    telefono = forms.CharField(label=u'Celular', max_length=15, required=False,
                               widget=forms.TextInput(attrs={'col': '3','placeholder':'Digite el número de celular'}))
    telefono_conv = forms.CharField(label=u'Teléfono fijo', max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'col': '3','placeholder':'Digite el número de teléfono'}))
    # rangoedad = forms.ChoiceField(label=u'Rango edad', choices=RANGO_EDAD_NINO, required=False,
    #                               widget=forms.Select(attrs={'class': 'imp-50'}))
    fallecido = forms.BooleanField(label=u'¿Falleció?', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    convive = forms.BooleanField(label=u'¿Convive con usted?', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    esservidorpublico = forms.BooleanField(label=u'¿Es servidor público?', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    bajocustodia = forms.BooleanField(label=u'¿Esta bajo su custodia?', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    centrocuidado = forms.ChoiceField(label=u"Centro de cuidado", choices=CENTRO_CUIDADO, required=False,
                                      widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    centrocuidadodesc = forms.CharField(label=u"Descripción del centro de cuidado", required=False,
                                        widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Describa el centro de cuidado que tiene para su familiar.'}))
    cedulaidentidad = ExtFileField(label=u'Subir documento de identidad', required=False,
                                   help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                   widget=forms.FileInput(attrs={'col': '6', 'accept': '.pdf'}),
                                   max_upload_size=2194304)
    cartaconsentimiento = ExtFileField(label=u'Carta de consentimiento', required=False,
                                       help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                       widget=forms.FileInput(attrs={'col': '6',
                                                                     'doctitle': 'Formato de carta',
                                                                      'accept': '.pdf',
                                                                     'docurl':'https://sga.unemi.edu.ec/media/documentos/2023/07/12/documentogeneral_2023712114148.docx'}), max_upload_size=2194304)
    archivocustodia = ExtFileField(label=u'Archivo de respaldo de custodia', required=False,
                                       help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                       widget=forms.FileInput(attrs={'col': '6','accept': '.pdf'}), max_upload_size=2194304)
    # DATOS LABORALES
    niveltitulacion = forms.ModelChoiceField(label=u"Nivel titulación",
                                             queryset=NivelTitulacion.objects.filter(status=True),
                                             required=True, widget=forms.Select(attrs={'col':'6','class':'select2'}))
    tipoinstitucionlaboral = forms.ChoiceField(label=u"Tipo de institución laboral",
                                              choices=TIPO_INSTITUCION_LABORAL, required=False,
                                              widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    trabajo = forms.CharField(label=u'Lugar de trabajo', max_length=200, required=False, widget=forms.TextInput(attrs={'col':'6','placeholder':'Describa el lugar de trabajao'}))
    formatrabajo = forms.ModelChoiceField(label=u"Tipo trabajo", queryset=FormaTrabajo.objects.all(), required=False,
                                          widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    ingresomensual = forms.DecimalField(label='Ingreso mensual', initial=00,required=False, widget=forms.TextInput(attrs={'col':'3','placeholder':'00.00'}))
    sustentohogar = forms.BooleanField(label=u'¿Es sustento del hogar?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    tienenegocio = forms.BooleanField(label=u'¿Tiene negocio propio?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    negocio = forms.CharField(label=u'Descripción de negocio', max_length=100, required=False, widget=forms.TextInput(attrs={'col':'12','placeholder':'Describa el negocio que tenga'}))

    #DISCAPACIDAD
    tienediscapacidad = forms.BooleanField(label=u'¿Tiene discapacidad?', required=False, widget=CheckboxInput(attrs={'col':'4','data-switchery':True}))
    essustituto = forms.BooleanField(label=u'¿Es sustituto?', required=False, widget=CheckboxInput(attrs={'data-switchery':True,'col':'4'}))
    autorizadoministerio = forms.BooleanField(label=u'¿Es autorizado por el ministerio?', required=False,
                                              widget=CheckboxInput(attrs={'data-switchery':True,'col':'4'}))
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de discapacidad",
                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                              widget=forms.Select(attrs={'col':'6','class':'select2'}))
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'Porcentaje de discapacidad', required=False,
                                             widget=forms.TextInput(attrs={'col': '6'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet discapacitado', max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'col':'6','placeholder':'Digite el número del carnet de discapacida'}))
    institucionvalida = forms.ModelChoiceField(label=u"Institución que válida",
                                               queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True),
                                               required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2', 'placeholder':'Nombre de la institución que válida.'}))
    ceduladiscapacidad = ExtFileField(label=u'Subir carnet de discapacidad', required=False,
                                      help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                      max_upload_size=2194304, widget=forms.FileInput(attrs={'col': '6','accept': '.pdf'}))
    archivoautorizado = ExtFileField(label=u'Archivo autorizado', required=False,
                                     help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                     widget=forms.FileInput(attrs={'col': '6','accept': '.pdf'}),
                                     max_upload_size=2194304)
    def edit(self):
        self.fields['cedulaidentidad'].required=False

    def clean(self):
        cleaned_data=super().clean()
        cedula=cleaned_data.get('identificacion')
        tipoidentificacion=int(cleaned_data.get('tipoidentificacion'))
        if tipoidentificacion == 1:
            result=validarcedula(cedula)
            if result!='Ok':
                self.add_error('identificacion',result)
        return cleaned_data

class FamiliarAspiranteForm(FormModeloBase):
    identificacion = forms.CharField(label=u"Identificación", max_length=10, required=True,
                                     widget=forms.TextInput({'col': '12'}))
    cedulaidentidad = ExtFileField(label=u'Subir Cédula de Identidad', required=False,
                                   help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                   max_upload_size=2194304,
                                   widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    parentesco = forms.ModelChoiceField(label=u"Parentesco", queryset=ParentescoPersona.objects.all(), required=False,
                                        widget=forms.Select(attrs={'col': '12'}))
    nombre = forms.CharField(max_length=200, label=u'Nombres', required=True, widget=forms.TextInput({'col': '12'}))
    apellido1 = forms.CharField(max_length=200, label=u'Primer apellido', required=True, widget=forms.TextInput({'col': '12'}))
    apellido2 = forms.CharField(max_length=200, label=u'Segundo apellido', required=True, widget=forms.TextInput({'col': '12'}))
    nacimiento = forms.DateField(label=u"Fecha nacimiento", initial=None, required=False, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    rangoedad = forms.ChoiceField(label=u'Rango edad', choices=RANGO_EDAD_NINO, required=False,
                                  widget=forms.Select(attrs={'col': '6'}))
    fallecido = forms.BooleanField(label=u'Fallecio', required=False, widget=CheckboxInput(attrs={'col': '6'}))
    telefono = forms.CharField(label=u'Telefono celular', max_length=15, required=False,
                               widget=forms.TextInput(attrs={'col': '12'}))
    telefono_conv = forms.CharField(label=u'Telefono fijo', max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'col': '12'}))
    trabajo = forms.CharField(label=u'lugar de Trabajo', max_length=200, required=False, widget=forms.TextInput(attrs={'col': '12'}))
    convive = forms.BooleanField(label=u'Convive con usted', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    sustentohogar = forms.BooleanField(label=u'Es sustento del hogar', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    niveltitulacion = forms.ModelChoiceField(label=u"Nivel Titulacion",
                                             queryset=NivelTitulacion.objects.filter(status=True),
                                             required=False, widget=forms.Select(attrs={'col': '12'}))
    formatrabajo = forms.ModelChoiceField(label=u"Tipo Trabajo", queryset=FormaTrabajo.objects.all(), required=False,
                                          widget=forms.Select(attrs={'col': '12'}))
    ingresomensual = forms.DecimalField(label='Ingreso Mensual', initial=0, widget=forms.TextInput(attrs={'col': '12'}))
    tienediscapacidad = forms.BooleanField(label=u'Tiene Discapacidad?', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    ceduladiscapacidad = ExtFileField(label=u'Subir Carnet de Discapacidad', required=False,
                                      help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                      max_upload_size=2194304,
                                      widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    essustituto = forms.BooleanField(label=u'Es Sustituto?', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    autorizadoministerio = forms.BooleanField(label=u'Es Autorizado por el Ministerio?', required=False,
                                              widget=CheckboxInput(attrs={'col': '12'}))
    archivoautorizado = ExtFileField(label=u'Archivo Autorizado', required=False,
                                     help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                                     max_upload_size=2194304,
                                     widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad",
                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                              widget=forms.Select(attrs={'col': '12'}))
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False,
                                             widget=forms.TextInput(attrs={'col': '12'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet Discapacitado', max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'col': '12'}))
    institucionvalida = forms.ModelChoiceField(label=u"Institución Valida",
                                               queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True),
                                               required=False, widget=forms.Select(attrs={'col': '12'}))
    tipoinstitucionlaboral = forms.ChoiceField(label=u"Tipo de Institución Laboral",
                                              choices=TIPO_INSTITUCION_LABORAL, required=False,
                                              widget=forms.Select(attrs={'col': '12'}))
    tienenegocio = forms.BooleanField(label=u'Tiene Negocio Propio?', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    negocio=forms.CharField(label=u'Descripción de Negocio', max_length=100, required=False, widget=forms.TextInput(attrs={'col': '12'}))

    def edit(self):
        self.fields['cedulaidentidad'].required=False

class DeclaracionBienForm(FormModeloBase):
    tipodeclaracion = forms.ChoiceField(label=u"Tipo declaración", required=True, choices=TIPO_DECLARACION,
                                        widget=forms.Select(attrs={'col': '4', 'class':'select2'}))
    fecha = forms.DateField(label=u"Fecha generación", initial=datetime.now().date(), required=True,
                            widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '4'}))
    fechaperiodoinicio = forms.DateField(label=u"Fecha inicio periodo", initial=datetime.now().date(), required=False,
                            widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '4'}))
    archivo = ExtFileField(label=u'Subir constancia', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'pdf'}))
    codigobarra = forms.CharField(max_length=50, label=u'Código barra', required=True,
                                  widget=forms.TextInput({'col': '6'}))
    cargosvigentes = forms.BooleanField(label=u'¿Seleccionar un cargo actual?', required=False, initial=True,
                               widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))
    cargo = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True), required=True,
                                   label=u'Mi cargo',
                                   widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.filter(status=True, integrantes__isnull=False).distinct().order_by(
            'nombre'), required=False, label=u'Dirección',
        widget=forms.Select({'col': '6', 'class': 'select2'}))




class DeclaracionBienAspiranteForm(FormModeloBase):
    tipodeclaracion = forms.ChoiceField(label=u"Tipo Declaración", required=False, choices=TIPO_DECLARACION,
                                        widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    numero = forms.CharField(max_length=20, label=u'No. Notaria', required=False,
                             widget=forms.TextInput({'col': '12'}))
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    fecha = forms.DateField(label=u"Fecha declaración", initial=datetime.now().date(), required=False,
                            widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    codigobarra = forms.CharField(max_length=50, label=u'Código Barra', required=False,
                                  widget=forms.TextInput({'col': '12'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais__id=1)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)

    def ocultarcampos(self):
        del self.fields['numero']
        del self.fields['provincia']
        del self.fields['canton']
        del self.fields['parroquia']

class CuentaBancariaPersonaForm(FormModeloBase):
    tipocuentabanco = forms.ModelChoiceField(label=u"Tipo de cuenta", queryset=TipoCuentaBanco.objects.all(),
                                             required=False, widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    numero = forms.CharField(max_length=20, label=u'No. Cuenta', required=False,
                             widget=forms.TextInput(attrs={'col': '6'}))
    banco = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False,
                                   widget=forms.Select(attrs={'col': '12','class':'select2'}))
    activapago = forms.BooleanField(label=u'Activa para pago?', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)


class TitulacionPersonaForm(FormModeloBase):
    titulo = forms.ModelChoiceField(label=u"Titulo", queryset=Titulo.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col':'12','class':'select2'}))
    areatitulo = forms.ModelChoiceField(label=u"Area de titulalción", queryset=AreaTitulo.objects.filter(status=True), required=True,
                                        widget=forms.Select(attrs={'col':'6','class':'select2'}))
    fechainicio = forms.DateField(label=u"Inicio de estudios", initial=datetime.now().date(), required=True,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'3'}))
    educacionsuperior = forms.BooleanField(label=u'Educación superior', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    institucion = forms.ModelChoiceField(label=u"Institución de educación superior",
                                         queryset=InstitucionEducacionSuperior.objects.filter(status=True), required=False,
                                         widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    colegio = forms.ModelChoiceField(label=u"Colegio", queryset=Colegio.objects.filter(status=True), required=False,
                                     widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    cursando = forms.BooleanField(label=u'Cursando', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    fechaobtencion = forms.DateField(label=u"Fecha de obtención", initial=datetime.now().date(), required=False,
                                    widget=DateTimeInput(format='%d-%m-%Y',attrs={'col':'3'}))
    fechaegresado = forms.DateField(label=u"Fecha de egreso", initial=datetime.now().date(), required=False,
                                    widget=DateTimeInput(format='%d-%m-%Y',attrs={'col':'3'}))
    registro = forms.CharField(label=u'Número de registro SENESCYT', max_length=50, required=False,
                               widget=forms.TextInput(attrs={'col': '6'}))
    anios = forms.IntegerField(initial=0, label=u'Años cursados', required=True, widget=forms.NumberInput(
        attrs={'col': '3', 'decimal': '0'}))
    semestres = forms.IntegerField(initial=0, label=u'Semestres cursados', required=True, widget=forms.NumberInput(
        attrs={'col': '3', 'decimal': '0'}))
    registroarchivo = ExtFileField(label=u'Seleccione Archivo SENESCYT', required=False,
                                   widget=forms.FileInput(attrs={'col':'6'}),
                                   help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                                   ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)
    archivo = ExtFileField(label=u'Seleccione Archivo Título', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           widget=forms.FileInput(attrs={'col': '6'}),
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.filter(status=True), required=True,
                                  widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.filter(status=True), required=False,
                                       widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.filter(status=True), required=False,
                                    widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.filter(status=True), required=False,
                                       widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    aplicobeca = forms.BooleanField(label=u'Aplico a una beca', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    tipobeca = forms.ChoiceField(label=u"Tipo de beca", required=False, choices=TIPO_BECA,
                                 widget=forms.Select(attrs={'col': '6','class':'select2'}))
    financiamientobeca = forms.ModelChoiceField(label=u"Tipo de financiamiento de la beca", required=False,
                                                queryset=FinanciamientoBeca.objects.filter(status=True),
                                                widget=forms.Select(attrs={'col': '6','class':'select2'}))
    valorbeca = forms.DecimalField(initial="0.00", label=u'Valor beca', required=False,
                                   widget=forms.TextInput(attrs={'col': '6', 'decimal': '2'}))
    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.none()
        self.fields['canton'].queryset = Canton.objects.none()
        self.fields['parroquia'].queryset = Parroquia.objects.none()
        self.fields['titulo'].queryset = Titulo.objects.none()

    def editar(self, titulacion):
        self.fields['titulo'].queryset = Titulo.objects.filter(id=titulacion.titulo.id)
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=titulacion.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=titulacion.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=titulacion.canton)
        if titulacion.verificadosenescyt:
            self.fields['titulo'].widget.attrs['readonly'] = True
            self.fields['titulo'].widget.attrs['disabled'] = True
            self.fields['titulo'].widget.attrs['fieldbuttons'] = None
            self.fields['institucion'].widget.attrs['readonly'] = True
            self.fields['institucion'].widget.attrs['disabled'] = True
            self.fields['registro'].widget.attrs['readonly'] = True
            self.fields['registro'].widget.attrs['disabled'] = True
            self.fields['educacionsuperior'].widget.attrs['readonly'] = True
            self.fields['educacionsuperior'].widget.attrs['disabled'] = True
            self.fields['cursando'].widget.attrs['readonly'] = True
            self.fields['cursando'].widget.attrs['disabled'] = True

class DatosPersonalesMaestranteForm(FormModeloBase):
    paisori = forms.ModelChoiceField(label=u"País de origen", queryset=Pais.objects.filter(status=True), required=True,
                                  widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    provinciaori = forms.ModelChoiceField(label=u"Provincia de origen", queryset=Provincia.objects.filter(status=True), required=True,
                                       widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    cantonori = forms.ModelChoiceField(label=u"Cantón de origen", queryset=Canton.objects.filter(status=True), required=True,
                                    widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    paisresi = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.filter(status=True), required=True,
                                  widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    provinciaresi = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects.filter(status=True), required=True,
                                       widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    cantonresi = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects.filter(status=True), required=True,
                                    widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    tienediscapacidad = forms.BooleanField(label=u'Tiene Discapacidad?', required=False, widget=CheckboxInput(attrs={'col':'6', 'data-switchery':True}))
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad",
                                              queryset=Discapacidad.objects.filter(status=False), required=False,
                                              widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False,
                                             widget=forms.TextInput(attrs={'col':'6'}))
    carnetdiscapacidad = forms.CharField(label=u'N° CONADIS', max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'col':'6'}))
    archivo = ExtFileField(label=u'Carnet de Discapacidad', required=False,
                           widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'pdf'}),
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304)
    raza = forms.ModelChoiceField(label=u"Etnia", queryset=Raza.objects.filter(status=True), required=True,
                                  widget=forms.Select(attrs={'col': '6','class':'select2'}))
    nacionalidadindigena = forms.ModelChoiceField(label=u"Nacionalidad indígena",
                                                  queryset=NacionalidadIndigena.objects.filter(status=True), required=False,
                                                  widget=forms.Select(attrs={'col': '6','class':'select2'}))
    lgtbi = forms.BooleanField(label=u"¿Pertenece al Grupo LGTBI?", required=False,
                               widget=forms.CheckboxInput(attrs={'col': '4','data-switchery':True}))

class TitulacionPersonaAdmisionForm(FormModeloBase):
    # titulo = forms.ModelChoiceField(label=u"Titulo", queryset=Titulo.objects.all(), required=False, widget=forms.Select(attrs={'fieldbuttons': [
    #         {'col': '12', 'id': 'add_registro_titulo', 'tooltiptext': 'Agregar titulo', 'btnclasscolor': 'btn-success',
    #          'btnfaicon': 'fa-plus'}]}))
    titulo = forms.ModelChoiceField(label=u"Titulo", queryset=Titulo.objects.all(), required=False, widget=forms.Select())
    areatitulo = forms.ModelChoiceField(label=u"Area de titulación", queryset=AreaTitulo.objects.all(), required=False,
                                        widget=forms.Select(attrs={'col': '12'}))
    fechainicio = forms.DateField(label=u"Fecha inicio de estudios", initial=datetime.now().date(), required=False,
                                  widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    educacionsuperior = forms.BooleanField(label=u'Educación superior', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    institucion = forms.ModelChoiceField(label=u"Institución de educación superior",
                                         queryset=InstitucionEducacionSuperior.objects.all(), required=False,
                                         widget=forms.Select(attrs={'col': '12'}))
    colegio = forms.ModelChoiceField(label=u"Colegio", queryset=Colegio.objects.all(), required=False,
                                     widget=forms.Select(attrs={'col': '12'}))
    cursando = forms.BooleanField(label=u'Cursando', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    fechaobtencion = forms.DateField(label=u"Fecha de obtención", initial=datetime.now().date(), required=False,
                                     widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    fechaegresado = forms.DateField(label=u"Fecha de egreso", initial=datetime.now().date(), required=False,
                                    widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    registro = forms.CharField(label=u'Número de registro SENESCYT', max_length=50, required=False,
                               widget=forms.TextInput(attrs={'col': '12'}))
    registroarchivo = ExtFileField(label=u'Seleccione Archivo SENESCYT', required=False,
                                   help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                                   ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                                   widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    archivo = ExtFileField(label=u'Seleccione Archivo Título', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'col': '12'}))
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'col': '12'}))
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'col': '12'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'col': '12'}))

    campoamplio = forms.ModelMultipleChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'col': '12', 'class': 'form-control', 'separator2': True, 'separatortitle': 'Datos del Título', }))
    campoespecifico = forms.ModelMultipleChoiceField(label=u"Campo Especifico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'col': '12', 'class': 'form-control'}))
    campodetallado = forms.ModelMultipleChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'col': '12', 'class': 'form-control'}))

    anios = forms.IntegerField(initial=0, label=u'Años cursados', required=False, widget=forms.TextInput(
        attrs={'col': '6', 'decimal': '0', 'separator2': True}))
    semestres = forms.IntegerField(initial=0, label=u'Semestres cursados', required=False, widget=forms.TextInput(
        attrs={'col': '6', 'decimal': '0'}))
    aplicobeca = forms.BooleanField(label=u'Aplico a una beca', required=False, widget=CheckboxInput(attrs={'col': '12'}))
    tipobeca = forms.ChoiceField(label=u"Tipo de beca", required=False, choices=TIPO_BECA,
                                 widget=forms.Select(attrs={'col': '6'}))
    financiamientobeca = forms.ModelChoiceField(label=u"Tipo de financiamiento de la beca", required=False,
                                                queryset=FinanciamientoBeca.objects.all(),
                                                widget=forms.Select(attrs={'col':'6'}))
    valorbeca = forms.DecimalField(initial="0.00", label=u'Valor beca', required=False,
                                   widget=forms.TextInput(attrs={'col':'12', 'class': 'imp-moneda', 'decimal': '2'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)

    def editar(self, titulacion):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=titulacion.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=titulacion.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=titulacion.canton)
        if titulacion.verificadosenescyt:
            self.fields['titulo'].widget.attrs['readonly'] = True
            self.fields['titulo'].widget.attrs['disabled'] = True
            self.fields['titulo'].widget.attrs['fieldbuttons'] = None
            self.fields['institucion'].widget.attrs['readonly'] = True
            self.fields['institucion'].widget.attrs['disabled'] = True
            self.fields['registro'].widget.attrs['readonly'] = True
            self.fields['registro'].widget.attrs['disabled'] = True
            self.fields['educacionsuperior'].widget.attrs['readonly'] = True
            self.fields['educacionsuperior'].widget.attrs['disabled'] = True
            self.fields['cursando'].widget.attrs['readonly'] = True
            self.fields['cursando'].widget.attrs['disabled'] = True

class DetalleTitulacionBachillerForm(FormModeloBase):
    # titulacion = forms.CharField(required=False, label=u'Titulación', widget=forms.TextInput(attrs={'col': '12'}))
    calificacion = forms.FloatField(label=u"Calificación", initial="0.00", required=True,
                                    widget=forms.TextInput(attrs={'col': '4', 'decimal': '2'}))
    anioinicioperiodograduacion = forms.IntegerField(label=u"Año Inicio Periodo Graduación",
                                                     initial=datetime.now().date().year, required=True,
                                                     widget=forms.NumberInput(
                                                         attrs={'col': '4', 'decimal': '0'}))
    aniofinperiodograduacion = forms.IntegerField(label=u"Año Fin Periodo Graduación",
                                                  initial=datetime.now().date().year, required=True,
                                                  widget=forms.NumberInput( attrs={'col': '4', 'decimal': '0'}))
    archivo = ExtFileField(label=u'Acta Grado PDF', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=FileInput({'accept': '.pdf','col':'6'}))
    reconocimientoacademico = ExtFileField(label=u'Reconocimeinto Académico PDF', required=False,
                                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf',
                                           ext_whitelist=(".pdf",),
                                           max_upload_size=10485760, widget=FileInput({'accept': '.pdf','col':'6'}))

    # def deshabilitar(self, titulacion):
    #     deshabilitar_campo(self, 'titulacion')
    #     self.fields['titulacion'].widget.attrs['value'] = titulacion.nombre() if titulacion else "Sin Titulación"
        # self.fields['titulacion'].widget.attrs['value'] = titulacion.id if titulacion else ""

class DatosSituacionLaboralForm(FormModeloBase):
    disponetrabajo = forms.BooleanField(required=False, label='¿Dispone de empleo?', widget=forms.CheckboxInput(attrs={'data-switchery':True,'col':'6'}))
    buscaempleo = forms.BooleanField(required=False, label='¿Busca Empleo?',widget=forms.CheckboxInput(attrs={'data-switchery':True,'col':'6'}))
    tipoinstitucionlaboral = forms.ChoiceField(choices=TIPO_INSTITUCION_LABORAL, label='Tipo institución',
                                               widget=forms.Select(attrs={'col': '6','class':'select2'}), required=False)
    lugartrabajo = forms.CharField(required=False, max_length=200, label=u"Lugar de trabajo",widget=forms.TextInput(attrs={'col': '6'}))
    tienenegocio = forms.BooleanField(required=False, label='¿Dispone de negocio?', widget=forms.CheckboxInput(attrs={'data-switchery':True,'col':'6'}) )
    negocio=forms.CharField(required=False, max_length=200, label=u"Descripción de negocio",widget=forms.TextInput(attrs={'col': '6'}))

class DatosSituacionLaboralAspiranteForm(FormModeloBase):
    disponetrabajo = forms.BooleanField(required=False, label='¿Dispone de Empleo?', widget=forms.CheckboxInput(attrs={'col': '12'}))
    tipoinstitucionlaboral = forms.ChoiceField(choices=TIPO_INSTITUCION_LABORAL, label='Tipo Institución',
                                               widget=forms.Select(attrs={'col': '12'}), required=False)
    lugartrabajo = forms.CharField(required=False, max_length=200, label=u"Lugar de trabajo", widget=forms.TextInput({'col': '12'}))
    buscaempleo = forms.BooleanField(required=False, label='¿Busca Empleo?',widget=forms.CheckboxInput(attrs={'col': '12'}))
    tienenegocio = forms.BooleanField(required=False, label='¿Dispone de Negocio Propio?', widget=forms.CheckboxInput(attrs={'col': '12'}))
    negocio=forms.CharField(required=False, max_length=200, label=u"Descripción de negocio", widget=forms.TextInput({'col': '12'}))

class DatosMedicosForm(FormModeloBase):
    carnetiess = forms.CharField(label=u'Carnet IESS', max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'col': '6'}))
    sangre = forms.ModelChoiceField(label=u"Tipo de sangre", queryset=TipoSangre.objects.all(), required=False,
                                    widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    archivotiposangre = ExtFileField(label=u'Certificado Tipo Sangre', required=False,
                                     help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                     max_upload_size=4194304)
    peso = forms.FloatField(label=u'Peso(Kg)', initial=0, required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-number','col':'6'}))
    talla = forms.FloatField(label=u'Estatura(Mts)', initial=0, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-number','col':'6'}))

    def deshabilitar(self):
        deshabilitar_campo(self, 'sangre')
        deshabilitar_campo(self, 'peso')
        deshabilitar_campo(self, 'talla')


class ExperienciaLaboralForm(FormModeloBase):
    tipoinstitucion = forms.ChoiceField(label=u'Tipo', choices=TIPOS_INSTITUCION,required=True,
                                        widget=forms.Select(attrs={'col': '2','class':'select2'}))
    institucion = forms.CharField(label=u'Institución', required=True, max_length=200,widget=forms.TextInput(attrs={'col':'4'}))
    cargo = forms.CharField(label=u'Cargo', max_length=200, required=True, widget=forms.TextInput(attrs={'col':'6'}))
    departamento = forms.CharField(label=u'Departamento', max_length=200, required=True,widget=forms.TextInput(attrs={'col':'6'}))
    correo = forms.CharField(label=u'Correo Institucional', max_length=200, required=False, widget=forms.TextInput(attrs={'col': '6'}))
    vigente = forms.BooleanField(label=u'Experiencia Vigente', required=False, widget=CheckboxInput(attrs={'col': '6', 'data-switchery':True}))
    motivosalida = forms.ModelChoiceField(label=u"Motivo salida", queryset=MotivoSalida.objects.filter(status=True), required=False,
                                          widget=forms.Select(attrs={'col': '6','class':'select2'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=False, widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                                             attrs={'col': '3'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=False, widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                                       attrs={'col': '3'}))
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.filter(status=True), required=True,
                                  widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.filter(status=True), required=True,
                                       widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.filter(status=True), required=True,
                                    widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.filter(status=True), required=True,
                                       widget=forms.Select(attrs={'col': '6', 'class':'select2'}))

    regimenlaboral = forms.ModelChoiceField(label=u"Regimen laboral", queryset=OtroRegimenLaboral.objects.filter(status=True),
                                            required=False, widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    dedicacionlaboral = forms.ModelChoiceField(label=u"Dedicación laboral", queryset=DedicacionLaboral.objects.filter(status=True),
                                               required=False, widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    actividadlaboral = forms.ModelChoiceField(label=u"Actividad laboral", queryset=ActividadLaboral.objects.filter(status=True),
                                              required=False, widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    horassemanales = forms.FloatField(initial=0, label=u'Horas semanales', required=False,
                                      widget=forms.TextInput(attrs={'col': '3'}))
    observaciones = forms.CharField(label=u"Observaciones", widget=forms.Textarea(attrs={'rows': '4'}), required=False)
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png','col':'6'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)

    def editar(self, capacitacion):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=capacitacion.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=capacitacion.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=capacitacion.canton)


class PermisoInstitucionalDetalleForm(forms.Form):
    fechainicio = forms.DateField(label=u"Fecha Desde", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                                  required=False)
    fechafin = forms.DateField(label=u"Fecha Hasta", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                               required=False)
    horainicio = forms.TimeField(label=u"Hora Desde", required=False, initial=str(datetime.now().time()),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    horafin = forms.TimeField(label=u'Hora Hasta', required=False, initial=str(datetime.now().time()),
                              input_formats=['%H:%M'],
                              widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))


class IntegranteFamiliaForm(forms.Form):
    integrante = forms.CharField(label=u"Integrante", required=True,
                                 widget=forms.TextInput(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(required=True, label=u"Descripción",
                                  widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '500'}))


class DatosBecaForm(FormModeloBase):
    tipoinstitucion = forms.ChoiceField(label=u'Tipo Institución', choices=TIPO_INSTITUCION_BECA, required=True,
                                        widget=forms.Select(attrs={'col': '12','class':'select2'}))
    institucion = forms.ModelChoiceField(label="Institución",queryset=InstitucionBeca.objects.filter(status=True, tiporegistro=1),
                                         required=True, widget=forms.Select(attrs={'col':'12', 'class':'select2'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio",
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}), required=True)
    fechafin = forms.DateField(label=u"Fecha Finalización",
                               widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '6'}), required=False)
    archivo = ExtFileField(label=u'Certificado Beca', required=False,
                           widget=forms.FileInput(attrs={'col': '12'}),
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304)

    def borrar_fecha_fin(self):
        del self.fields['fechafin']

    def bloquear_campos(self):
        deshabilitar_campo(self, 'tipoinstitucion')
        deshabilitar_campo(self, 'institucion')
        deshabilitar_campo(self, 'archivo')
        deshabilitar_campo(self, 'fechainicio')


class InstitucionForm(forms.Form):
    nombreinstitucion = forms.CharField(label=u'Nombre', max_length=250, required=False)


class DeportistaForm(FormModeloBase):
    representapais = forms.ChoiceField(label=u'Representa al Ecuador', choices=VALOR_SI_NO, required=True,widget=forms.Select(attrs={'col': '6'}))
    disciplina = forms.ModelMultipleChoiceField(label=u'Disciplinas deportivas', queryset=DisciplinaDeportiva.objects.filter(status=True), required=True, widget=forms.SelectMultiple(attrs={'col':'6','class':'select2'}))
    evento = forms.CharField(label=u'Evento participación', widget=forms.Textarea(attrs={'rows': '4'}), required=True)
    equiporepresenta = forms.CharField(label=u'Equipo representa', max_length=300, required=True, widget=forms.TextInput(attrs={'col': '6'}))
    paisevento = forms.ModelChoiceField(label=u"País evento", queryset=Pais.objects.all().exclude(pk=1), required=True, widget=forms.Select(attrs={'col':'3','class':'select2'}))
    vigente = forms.ChoiceField(label=u'Vigente', choices=VALOR_SI_NO, required=False, widget=forms.Select(attrs={'col': '3'}))
    fechainicioevento = forms.DateField(label=u"Fecha Inicio Evento",widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '3'}),required=True)
    fechafinevento = forms.DateField(label=u"Fecha Fin Evento",widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '3'}), required=True)
    fechainicioentrena = forms.DateField(label=u"Fecha Inicio Entrena", widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '3'}),required=True)
    fechafinentrena = forms.DateField(label=u"Fecha Fin Entrena",widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '3'}),required=True)
    archivoevento = ExtFileField(label=u'Documento Evento', required=False,
                                 help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                 widget=forms.FileInput(attrs={'col': '6'}),
                                 max_upload_size=4194304)
    archivoentrena = ExtFileField(label=u'Documento Entrenamiento', required=False,
                                  help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                  widget=forms.FileInput(attrs={'col': '6'}),
                                  max_upload_size=4194304)

    def borrar_vigente(self):
        del self.fields['vigente']

    def bloquear_campos(self):
        deshabilitar_campo(self, 'disciplina')
        deshabilitar_campo(self, 'representapais')
        deshabilitar_campo(self, 'evento')
        deshabilitar_campo(self, 'paisevento')
        deshabilitar_campo(self, 'equiporepresenta')
        deshabilitar_campo(self, 'archivoevento')
        deshabilitar_campo(self, 'fechainicioevento')
        deshabilitar_campo(self, 'fechafinevento')
        deshabilitar_campo(self, 'archivoentrena')
        deshabilitar_campo(self, 'fechainicioentrena')
        deshabilitar_campo(self, 'fechafinentrena')


class MigranteForm(FormModeloBase):
    paisresidencia = forms.ModelChoiceField(label=u"País residencia", queryset=Pais.objects.all().exclude(pk=1),
                                            required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    fecharetorno = forms.DateField(label=u"Fecha salida",
                                   widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '6'}), required=False)
    anioresidencia = forms.IntegerField(initial=0, label=u'Años residencia', required=False, widget=forms.TextInput(
        attrs={'col': '6', 'decimal': '0'}))
    mesresidencia = forms.IntegerField(initial=0, label=u'Meses residencia', required=False, widget=forms.TextInput(
        attrs={'col': '6', 'decimal': '0'}))
    archivo = ExtFileField(label=u'Certificado extranjero', required=False,
                           help_text=u'Tamaño máximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304)


class ArtistaForm(FormModeloBase):
    campoartistico = forms.ModelMultipleChoiceField(label=mark_safe(u'Campo artístico'),
                                                    widget=forms.SelectMultiple(attrs={'col': '12','class':'select2'}),
                                                    queryset=CampoArtistico.objects.all(), required=False)
    grupopertenece = forms.CharField(label=u'Grupo pertenece', max_length=300, required=False,
                                     widget=forms.TextInput(attrs={'col': '12'}))
    vigente = forms.ChoiceField(label=u'Vigente', choices=VALOR_SI_NO, required=False,
                                widget=forms.Select(attrs={'col': '6'}))
    fechainicioensayo = forms.DateField(label=u"Fecha Inicio Ensayos",required=False,
                                        widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '6'}))
    fechafinensayo = forms.DateField(label=u"Fecha Fin Ensayos", required=False,
                                     widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '6'}))
    archivo = ExtFileField(label=u'Documento Grupo', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304)

    def borrar_vigente(self):
        del self.fields['vigente']

    def bloquear_campos(self):
        deshabilitar_campo(self, 'campoartistico')
        deshabilitar_campo(self, 'grupopertenece')
        deshabilitar_campo(self, 'archivo')
        deshabilitar_campo(self, 'fechainicioensayo')
        deshabilitar_campo(self, 'fechafinensayo')


class ArtistaValidacionForm(forms.Form):
    estadoartista = forms.ChoiceField(label=u'Estado Documento', choices=ESTADO_REVISION_ARCHIVO, required=False,
                                      widget=forms.Select(attrs={'formwidth': '50%'}))
    observacionartista = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}),
                                         required=False)

    def editar(self):
        if self.initial['estadoartista'] == 2:
            self.fields['observacionartista'].widget.attrs['disabled'] = True


class BecaValidacionForm(forms.Form):
    estadobecado = forms.ChoiceField(label=u'Estado Documento', choices=ESTADO_REVISION_ARCHIVO, required=False,
                                     widget=forms.Select(attrs={'formwidth': '50%'}))
    observacionbecado = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}),
                                        required=False)

    def editar(self):
        if self.initial['estadobecado'] == 2:
            self.fields['observacionbecado'].widget.attrs['disabled'] = True


class DeportistaValidacionForm(forms.Form):
    estadoarchivoevento = forms.ChoiceField(label=u'Estado Documento Evento', choices=ESTADO_REVISION_ARCHIVO,
                                            required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    estadoarchivoentrena = forms.ChoiceField(label=u'Estado Documento Entrenamiento', choices=ESTADO_REVISION_ARCHIVO,
                                             required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    observacionarchevento = forms.CharField(label=u'Observación Evento',
                                            widget=forms.Textarea(attrs={'rows': '2', 'formwidth': '50%'}),
                                            required=False)
    observacionarchentrena = forms.CharField(label=u'Observación Entrenamiento',
                                             widget=forms.Textarea(attrs={'rows': '2', 'formwidth': '50%'}),
                                             required=False)

    def editar(self):
        if self.initial['estadoarchivoevento'] == 2:
            self.fields['observacionarchevento'].widget.attrs['disabled'] = True
        if self.initial['estadoarchivoentrena'] == 2:
            self.fields['observacionarchentrena'].widget.attrs['disabled'] = True


class DiscapacidadValidacionForm(forms.Form):
    tipodiscapacidad = forms.ModelChoiceField(Discapacidad.objects.filter(status=True), label=u"Tipo de Discapacidad", required=False,
                                              widget=forms.Select(attrs={'class': 'imp-75'}))
    archivo = ExtFileField(label=u'Carnet de Discapacidad', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304)
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet Discapacitado', max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    subtipodiscapacidad = forms.ModelMultipleChoiceField(label=u"Sub Tipo de Discapacidad",
                                                         queryset=SubTipoDiscapacidad.objects.filter(status=True), required=False,
                                                         widget=forms.SelectMultiple(attrs={'multiple': 'multiple'}))
    grado = forms.ChoiceField(label=u"Grado de Discapacidad", choices=GRADO, required=False, widget=forms.Select())
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False,
                                             widget=forms.TextInput(attrs={'class': 'input-number'}))
    institucionvalida = forms.ModelChoiceField(label=u"Institución Valida",
                                               queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True),
                                               required=False, widget=forms.Select())
    tienediscapacidadmultiple = forms.BooleanField(label=u'Tiene Discapacidad multiple?', required=False, widget=CheckboxInput())
    tipodiscapacidadmultiple = forms.ModelMultipleChoiceField(label=u"Tipo de Discapacidad Multiple",
                                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                                              widget=forms.SelectMultiple(attrs={'multiple': 'multiple'}))
    estadodiscapacidad = forms.ChoiceField(label=u'Estado Documento', choices=ESTADO_REVISION_ARCHIVO, required=False,
                                           widget=forms.Select(attrs={'formwidth': '50%'}))
    observaciondiscapacidad = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}),
                                              required=False)

    def editar(self):
        if self.initial['estadodiscapacidad'] == 2:
            self.fields['observaciondiscapacidad'].widget.attrs['disabled'] = True


class EtniaValidacionForm(forms.Form):
    raza = forms.ModelChoiceField(label=u'Etnia', queryset=Raza.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '75%'}))
    estadoetnia = forms.ChoiceField(label=u'Estado Documento', choices=ESTADO_REVISION_ARCHIVO, required=False,
                                    widget=forms.Select(attrs={'formwidth': '50%'}))
    observacionetnia = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)

    def editar(self):
        if self.initial['estadoetnia'] == 2:
            self.fields['observacionetnia'].widget.attrs['disabled'] = True


class MigranteValidacionForm(forms.Form):
    estadomigrante = forms.ChoiceField(label=u'Estado Documento', choices=ESTADO_REVISION_ARCHIVO, required=False,
                                       widget=forms.Select(attrs={'formwidth': '50%'}))
    observacionmigrante = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}),
                                          required=False)

    def editar(self):
        if self.initial['estadomigrante'] == 2:
            self.fields['observacionmigrante'].widget.attrs['disabled'] = True


class PemisoInstitucionalArchivoForm(forms.Form):
    archivo = ExtFileField(label=u'Documento PDF soporte', required=False,
                           help_text=u'Tamaño máximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))


class PermisoInstitucionalFechaForm(forms.Form):
    fechasolicitud = forms.DateField(label=u"Fecha Solicitud", input_formats=['%d-%m-%Y'],
                                     widget=DateTimeInput(format='%d-%m-%Y',
                                                          attrs={'class': 'selectorfecha', 'formwidth': '20%'}),
                                     required=False)
    denominacionpuesto = forms.ModelChoiceField(label=u"Denominacion de Puesto",
                                                queryset=DenominacionPuesto.objects.filter(status=True), required=False,
                                                widget=forms.Select())
    tiposolicitud = forms.ChoiceField(label=u"Tipo de Solicitud", choices=TIPO_SOLICITUD_PERMISO[:1], required=False,
                                      widget=forms.Select(attrs={'separator': 'true'}))
    tipopermiso = forms.ModelChoiceField(label=u"Permiso", queryset=TipoPermiso.objects.filter(status=True,
                                                                                               tipopermisodetalle__isnull=False,
                                                                                               tipopermisodetalle__vigente=True).distinct(),
                                         required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    motivo = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                             label=u"Motivo")
    casasalud = forms.ModelChoiceField(label=u"Casa Salud", queryset=CasaSalud.objects.filter(status=True),
                                       required=False, widget=forms.Select())
    archivo = ExtFileField(label=u'Documento PDF soporte', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304, widget=FileInput({'accept': 'application/pdf'}))


    def editar_aprobar(self, persona):
        deshabilitar_campo(self, 'fechasolicitud')
        # deshabilitar_campo(self, 'denominacionpuesto')
        deshabilitar_campo(self, 'tiposolicitud')
        deshabilitar_campo(self, 'tipopermiso')
        deshabilitar_campo(self, 'motivo')
        deshabilitar_campo(self, 'casasalud')
        self.fields['denominacionpuesto'].queryset = DenominacionPuesto.objects.filter(
            distributivopersona__persona=persona, status=True,
            distributivopersona__estadopuesto__id=PUESTO_ACTIVO_ID).distinct()


class InformesPermisoForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 6Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=6291456)


class SubirPermisoMasivoForm(FormModeloBase):
    regimenlaboral = forms.ModelChoiceField(label=u"Regimen Laboral",
                                            queryset=RegimenLaboral.objects.filter(status=True), required=False,
                                            widget=forms.Select({'col': '12','class': 'select2'}))
    tipopermiso = forms.ModelChoiceField(label=u"Permiso", queryset=TipoPermiso.objects.filter(status=True,
                                                                                               tipopermisodetalle__isnull=False,
                                                                                               tipopermisodetalle__vigente=True).distinct(),
                                         required=False, widget=forms.Select({'col': '12','class': 'select2'}))
    tipopermisodetalle = forms.ModelChoiceField(label=u"Artículo",
                                                queryset=TipoPermisoDetalle.objects.filter(status=True, vigente=True),
                                                required=False, widget=forms.Select(attrs={'col': '12','class': 'select2'}))
    motivo = forms.CharField(widget=forms.Textarea({'rows': '3', 'col':'12'}), required=False,
                             label=u"Motivo")
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 6Mb, en formato xls', ext_whitelist=(".xls","xlsx"),
                           max_upload_size=6291456)


class PermisoInstitucionalForm(forms.Form):
    fechasolicitud = forms.DateField(label=u"Fecha Solicitud", input_formats=['%d-%m-%Y'],
                                     widget=DateTimeInput(format='%d-%m-%Y',
                                                          attrs={'class': 'selectorfecha', 'formwidth': '20%'}),
                                     required=False)
    denominacionpuesto = forms.ModelChoiceField(label=u"Denominacion de Puesto",
                                                queryset=DistributivoPersona.objects.filter(status=True),
                                                required=False, widget=forms.Select())
    tiposolicitud = forms.ChoiceField(label=u"Tipo de Solicitud", choices=TIPO_SOLICITUD_PERMISO[:1], required=False,
                                      widget=forms.Select(attrs={'separator': 'true'}))
    estadosolicitud = forms.ChoiceField(label=u"Estado", choices=ESTADO_PERMISOS, required=False,
                                        widget=forms.Select(attrs={'formwidth': '30%'}))
    tipopermiso = forms.ModelChoiceField(label=u"Permiso", queryset=TipoPermiso.objects.filter(status=True,
                                                                                               tipopermisodetalle__isnull=False,
                                                                                               tipopermisodetalle__vigente=True).distinct(),
                                         required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    categoriapermiso = forms.ModelChoiceField(label=u"Categoría de Permiso",
                                                queryset=CategoriaTipoPermiso.objects.filter(status=True, tipopermiso__isnull=False),
                                                required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    tipopermisodetalle = forms.ModelChoiceField(label=u"Artículo",
                                                queryset=TipoPermisoDetalle.objects.filter(status=True, vigente=True),
                                                required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    permisofamilia = forms.ModelChoiceField(label=u"Familiar",
                                            queryset=TipoPermisoDetalleFamilia.objects.filter(status=True),
                                            required=False, widget=forms.Select())
    motivo = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                             label=u"Motivo")
    casasalud = forms.ModelChoiceField(label=u"Casa Salud", queryset=CasaSalud.objects.filter(status=True),
                                       required=False, widget=forms.Select())
    archivo = ExtFileField(label=u'Documento PDF soporte', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))

    def adicionar(self, persona):
        deshabilitar_campo(self, 'fechasolicitud')
        self.fields['permisofamilia'].queryset = TipoPermisoDetalleFamilia.objects.filter(pk=None)
        self.fields['tipopermiso'].queryset = TipoPermiso.objects.filter(pk=None)
        del self.fields['estadosolicitud']
        self.fields['tipopermisodetalle'].queryset = TipoPermisoDetalle.objects.filter(tipopermiso=None, status=True,
                                                                                       vigente=True)
        self.fields['denominacionpuesto'].queryset = DistributivoPersona.objects.filter(persona=persona, status=True,
                                                                                        estadopuesto__id=PUESTO_ACTIVO_ID).distinct()

    def editar(self, permiso):
        deshabilitar_campo(self, 'fechasolicitud')
        del self.fields['estadosolicitud']
        self.fields['permisofamilia'].queryset = TipoPermisoDetalleFamilia.objects.filter(
            tipopermisodetalle=permiso.tipopermisodetalle)
        self.fields['tipopermisodetalle'].queryset = TipoPermisoDetalle.objects.filter(tipopermiso=permiso.tipopermiso,
                                                                                       status=True, vigente=True)
        self.fields['categoriapermiso'].queryset = CategoriaTipoPermiso.objects.filter(tipopermiso=permiso.tipopermiso,
                                                                                       status=True)
        self.fields['denominacionpuesto'].queryset = DistributivoPersona.objects.filter(persona=permiso.solicita,
                                                                                        status=True,
                                                                                        estadopuesto__id=PUESTO_ACTIVO_ID).distinct()

    def deshabilitar_permisofamilia(self):
        deshabilitar_campo(self, 'permisofamilia')


class PermisoInstitucionalAdicionarForm(forms.Form):
    fechasolicitud = forms.DateField(label=u"Fecha Solicitud", input_formats=['%d-%m-%Y'],
                                     widget=DateTimeInput(format='%d-%m-%Y',
                                                          attrs={'class': 'selectorfecha', 'formwidth': '20%'}),
                                     required=False)
    persona = forms.IntegerField(initial=0, required=True, label=u'Persona',
                                 widget=forms.TextInput(attrs={'select2search': 'true'}))
    denominacionpuesto = forms.ModelChoiceField(label=u"Denominacion de Puesto",
                                                queryset=DistributivoPersona.objects.filter(status=True),
                                                required=False, widget=forms.Select())
    tiposolicitud = forms.ChoiceField(label=u"Tipo de Solicitud", choices=TIPO_SOLICITUD_PERMISO[:1], required=False,
                                      widget=forms.Select(attrs={'separator': 'true'}))
    estadosolicitud = forms.ChoiceField(label=u"Estado", choices=((3, u'APROBADO')), required=False,
                                        widget=forms.Select(attrs={'formwidth': '60%'}))
    tipopermiso = forms.ModelChoiceField(label=u"Permiso", queryset=TipoPermiso.objects.filter(status=True,
                                                                                               tipopermisodetalle__isnull=False,
                                                                                               tipopermisodetalle__vigente=True).distinct(),
                                         required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    tipopermisodetalle = forms.ModelChoiceField(label=u"Artículo",
                                                queryset=TipoPermisoDetalle.objects.filter(status=True, vigente=True),
                                                required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    # permisofamilia = forms.ModelChoiceField(label=u"Familiar",queryset=TipoPermisoDetalleFamilia.objects.filter(status=True),required=False, widget=forms.Select())
    motivo = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                             label=u"Motivo")
    casasalud = forms.ModelChoiceField(label=u"Casa Salud", queryset=CasaSalud.objects.filter(status=True),
                                       required=False, widget=forms.Select())
    archivo = ExtFileField(label=u'Documento PDF soporte', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))

    def adicionar(self):
        deshabilitar_campo(self, 'fechasolicitud')
        deshabilitar_campo(self, 'denominacionpuesto')
        deshabilitar_campo(self, 'tipopermiso')
        # self.fields['permisofamilia'].queryset = TipoPermisoDetalleFamilia.objects.filter(pk=None)
        self.fields['persona'].widget.attrs['descripcion'] = "seleccione persona"
        self.fields['tipopermiso'].queryset = TipoPermiso.objects.filter(status=True)
        del self.fields['estadosolicitud']
        del self.fields['tiposolicitud']
        # del self.fields['permisofamilia']
        self.fields['tipopermisodetalle'].queryset = TipoPermisoDetalle.objects.filter(tipopermiso=None, status=True,
                                                                                       vigente=True)
        # self.fields['denominacionpuesto'].queryset = DistributivoPersona.objects.filter(persona=persona, status=True, estadopuesto__id=PUESTO_ACTIVO_ID).distinct()

    def editar(self, permiso):
        deshabilitar_campo(self, 'fechasolicitud')
        del self.fields['estadosolicitud']
        self.fields['permisofamilia'].queryset = TipoPermisoDetalleFamilia.objects.filter(
            tipopermisodetalle=permiso.tipopermisodetalle)
        self.fields['tipopermisodetalle'].queryset = TipoPermisoDetalle.objects.filter(tipopermiso=permiso.tipopermiso,
                                                                                       status=True, vigente=True)
        self.fields['denominacionpuesto'].queryset = DistributivoPersona.objects.filter(persona=permiso.solicita,
                                                                                        status=True,
                                                                                        estadopuesto__id=PUESTO_ACTIVO_ID).distinct()

    def deshabilitar_permisofamilia(self):
        deshabilitar_campo(self, 'permisofamilia')


class KardexVacacionesIndividualForm(forms.Form):
    persona = forms.IntegerField(initial=0, required=False, label=u'Persona',
                                 widget=forms.TextInput(attrs={'select2search': 'true'}))
    regimenlaboral = forms.ModelChoiceField(label=u"Regimen Laboral",
                                            queryset=RegimenLaboral.objects.filter(status=True), required=False,
                                            widget=forms.Select())
    fechaingreso = forms.DateField(label=u"Fecha Ingreso", input_formats=['%d-%m-%Y'],
                                   widget=DateTimeInput(format='%d-%m-%Y',
                                                        attrs={'class': 'selectorfecha', 'formwidth': '20%'}),
                                   required=False)
    fechasalida = forms.DateField(label=u"Fecha Salida", input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '20%'}),
                                  required=False)
    estado = forms.ChoiceField(label=u"Estado", choices=ESTADO_REGIMEN, required=False,
                               widget=forms.Select(attrs={'formwidth': '60%'}))
    nombramiento = forms.BooleanField(label=u'¿Tiene Nombramiento?', required=False, widget=CheckboxInput())
    contratoindefinido = forms.BooleanField(label=u'¿Tiene Contrato indefinido?', required=False,
                                            widget=CheckboxInput())

    def adicionar(self):
        self.fields['persona'].widget.attrs['descripcion'] = "seleccione persona"

    def editar(self, kardex):
        self.fields['persona'].widget.attrs['value'] = kardex.persona.id if kardex.persona else ""
        self.fields['persona'].widget.attrs['descripcion'] = kardex.persona.flexbox_repr() if kardex.persona else ""
        self.fields['regimenlaboral'].widget.attrs['value'] = kardex.regimenlaboral.id if kardex.regimenlaboral else ""
        self.fields['regimenlaboral'].widget.attrs[
            'descripcion'] = kardex.regimenlaboral.flexbox_repr() if kardex.regimenlaboral else ""
        deshabilitar_campo(self, 'persona')
        deshabilitar_campo(self, 'regimenlaboral')


class KardexVacacionesForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 4Mb, en formato xls, xlsx',
                           ext_whitelist=(".xls", ".xlsx"), max_upload_size=4194304)


class KardexVacacionesDetalleForm(FormModeloBase):
    operacion = forms.ChoiceField(label=u"Operación", choices=OPERACION, required=False,
                                  widget=forms.Select(attrs={'col': '4','class':'form-select'}))
    permiso = forms.ModelChoiceField(label=u"Permiso", queryset=PermisoInstitucional.objects.filter(status=True),
                                     required=False, widget=forms.Select(attrs={'col': '12','class':'form-select'}))
    fecha = forms.DateField(label=u"Fecha",initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y',
                                  attrs={'class': 'selectorfecha','col': '6','controlwidth': '300px'}), required=False)
    fechainicio = forms.DateField(label=u"Fecha inicio cálculo",required=False, widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'col': '3'}))
    fechafin = forms.DateField(label=u"Fecha fin cálculo",required=False, widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'col': '3'}))
    concepto = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                               label=u"Concepto")
    diava = forms.IntegerField(initial=0, label=u'Dias', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'formwidth': '33%', 'decimal': '0', 'labelwidth': '80',
               'col': '3'}))
    horava = forms.IntegerField(initial=0, label=u'Horas', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'formwidth': '33%', 'decimal': '0', 'labelwidth': '80',
               'col': '3'}))
    minva = forms.IntegerField(initial=0, label=u'Minutos', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'formwidth': '33%', 'decimal': '0', 'labelwidth': '80',
               'col': '3'}))

    def adicionardetalle(self, persona):
        deshabilitar_campo(self, 'fecha')
        self.fields['permiso'].queryset = PermisoInstitucional.objects.filter(solicita=persona, status=True,
                                                                              estadosolicitud=2).distinct()


class HojaRutaForm(forms.Form):
    fecha = forms.DateField(label=u"Hasta", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '110px'}),
                            required=False)
    tipodestino = forms.ChoiceField(label=u"Ubicación", choices=UBICACION_HOJA_RUTA, required=False,
                                    widget=forms.Select(attrs={'formwidth': '150px'}))
    destinointerno = forms.ModelChoiceField(
        Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), required=False,
        label=u'Departamento', widget=forms.Select())
    destinoexterno = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                                     label=u"Destino")
    solicitante = forms.ModelChoiceField(label=u'Autorizado por:', required=False,
                                         queryset=Persona.objects.filter(administrativo__isnull=False),
                                         widget=forms.Select())
    actividad = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                                label=u"Actividad")
    horasalida = forms.TimeField(label=u"Hora salida", required=False, initial=str(datetime.now().time())[:5],
                                 input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                               attrs={'class': 'selectorhora',
                                                                                      'formwidth': '100px'}))
    ingreso = forms.BooleanField(label=u'Hora Ingreso', required=False,
                                 widget=CheckboxInput({'class': 'imp-25', 'formwidth': '50px'}))
    horaingreso = forms.TimeField(label=u"Ingreso", required=False, initial=str(datetime.now().time())[:5],
                                  input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                                attrs={'class': 'selectorhora',
                                                                                       'formwidth': '100px'}))
    observacion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                                  label=u"Observaciones")

    def editar(self):
        deshabilitar_campo(self, 'fecha')
        deshabilitar_campo(self, 'ingreso')
        deshabilitar_campo(self, 'tipodestino')
        deshabilitar_campo(self, 'destinointerno')
        deshabilitar_campo(self, 'destinoexterno')
        deshabilitar_campo(self, 'solicitante')
        deshabilitar_campo(self, 'actividad')
        deshabilitar_campo(self, 'horasalida')


class PeriodoRolForm(forms.Form):
    # anio = forms.CharField(label=u"Año", required=False, widget=forms.TextInput(attrs={'class': 'imp-anio', 'formwidth': '20%'}))
    anio = forms.CharField(label=u"Año", required=False, widget=forms.TextInput(attrs={'class': 'imp-anio'}))
    mes = forms.ChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES,
                            widget=forms.Select(attrs={'formwidth': '50%'}))
    tiporol = forms.ModelChoiceField(TipoRol.objects.all(), required=False, label=u'Tipo Rol', widget=forms.Select())
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                                  label=u"Descripción")

    def editar(self):
        deshabilitar_campo(self, 'anio')
        deshabilitar_campo(self, 'mes')
        deshabilitar_campo(self, 'tiporol')


class TipoRolForm(forms.Form):
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400', 'formwidth': '100%', 'controlwidth': '100%'}), required=False, label=u"Descripción")


class CampoContratoForm(forms.Form):
    descripcion = forms.CharField(label=u"Nombre", required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '40%'}))
    fijo = forms.BooleanField(label=u'Fijo', required=False,
                              widget=CheckboxInput(attrs={'formwidth': '10%', 'labelwidth': '30px'}))
    tipo = forms.ChoiceField(label=u"Tipo", required=False, choices=TIPO_CAMPO,
                             widget=forms.Select(attrs={'formwidth': '35%'}))
    identificador = forms.CharField(label=u"Identificador", required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '100%'}))
    script = forms.CharField(widget=forms.Textarea(attrs={'rows': '5', 'maxlength': '400'}), required=False,
                             label=u"Script")

    def editar(self):
        deshabilitar_campo(self, 'descripcion')
        deshabilitar_campo(self, 'script')
        deshabilitar_campo(self, 'tipo')


class ContratosForm(FormModeloBase):
    explicacion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3','col':'12'}), required=True,
                                  label=u"Explicación")

    regimenlaboral = forms.ModelChoiceField(RegimenLaboral.objects.all(), required=False, label=u'Regimen Laboral',
                                            widget=forms.Select(attrs={'col': '12'}))
    relacionies = forms.ChoiceField(label=u'Relación Laboral', choices=RELACION_IES,
                                    widget=forms.Select(attrs={'class': 'imp-50','col': '12'}))

    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(),
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha form-control','col': '6'}),
                            required=False)
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(),
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha form-control','col': '6'}),
                            required=False)

class EditContratosForm(FormModeloBase):
    numerodocumento = forms.CharField(label=u'Número Contrato', required=False,
                             widget=forms.TextInput(attrs={'col': '6'}))
    remuneracion = forms.CharField(label=u'RMU', required=False,
                             widget=forms.TextInput(attrs={'col': '6'}))

    explicacion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3','col':'12'}), required=True,
                                  label=u"Explicación")
    unidadorganica = forms.ModelChoiceField(Departamento.objects.filter(status=True,integrantes__isnull=False).distinct(), required=True, label=u'Unidad orgánica',
                                            widget=forms.Select(attrs={'col': '12'}))
    regimenlaboral = forms.ModelChoiceField(RegimenLaboral.objects.filter(status=True), required=False, label=u'Regimen Laboral',
                                            widget=forms.Select(attrs={'col': '12'}))
    relacionies = forms.ChoiceField(label=u'Relación Laboral', choices=RELACION_IES,
                                    widget=forms.Select(attrs={'class': 'imp-50','col': '12'}))

    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(),
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha form-control','col': '6'}),
                            required=False)
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(),
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha form-control','col': '6'}),
                            required=False)
    denominacionpuesto = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True), required=False, label=u'Puesto',
                                            widget=forms.Select(attrs={'col': '12'}))


class ArchivoContratoForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño Maximo permitido 4Mb, en formato doc, docx',
                           ext_whitelist=(".doc", ".docx"), max_upload_size=4194304)


class ContratoPersonaForm(forms.Form):
    modelocontrato = forms.ModelChoiceField(Contratos.objects.filter(status=True, vigente=True), required=False,
                                            label=u'Modelo de contrato', widget=forms.Select())
    persona = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(administrativo__isnull=False), required=True,
                                     label=u'Persona', widget=forms.Select())
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '110px'}),
                            required=False)
    denominacionpuesto = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True), required=False,
                                                label=u'Denominación puesto',
                                                widget=forms.Select(attrs={'formwidth': '85%'}))
    unidadorganica = forms.ModelChoiceField(
        Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), required=False,
        label=u'Departamento', widget=forms.Select())
    rmu = forms.FloatField(initial='', label=u'RMU propuesto', required=False, widget=forms.TextInput(
        attrs={'formwidth': '400px', 'class': 'imp-numbersmall', 'decimal': '2'}))

    def adicionar(self, anio):
        self.fields['modelocontrato'].queryset = Contratos.objects.filter(anio=anio)


class ArchivoImportarContratoForm(forms.Form):
    modelocontrato = forms.ModelChoiceField(Contratos.objects.filter(status=True, vigente=True), required=False,
                                            label=u'Modelo de contrato', widget=forms.Select())
    fecha = forms.DateField(label=u"Fecha de contrato", initial=datetime.now().date(), required=False,
                            widget=DateTimeInput(
                                attrs={'seleccionafecha': 'True', 'class': 'selectorfecha', 'formwidth': '50%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 4Mb, en formato xls, xlsx',
                           ext_whitelist=(".xls", ".xlsx"), max_upload_size=4194304)


class ArchivoPeriodoRolForm(forms.Form):
    anio = forms.CharField(label=u"Año", required=False, widget=forms.TextInput(attrs={'class': 'imp-anio'}))
    mes = forms.ChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES,
                            widget=forms.Select(attrs={'class': 'imp-25'}))
    tiporol = forms.ModelChoiceField(TipoRol.objects.all(), required=False, label=u'Tipo Rol', widget=forms.Select())
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                                  label=u"Descripción")

    def acciones(self):
        deshabilitar_campo(self, 'anio')
        deshabilitar_campo(self, 'mes')
        deshabilitar_campo(self, 'tiporol')
        deshabilitar_campo(self, 'descripcion')


# Subnovedades
class SunovedadPeriodoRolForm(forms.Form):
    anio = forms.CharField(label=u"Año", required=False, widget=forms.TextInput(attrs={'class': 'imp-anio'}))
    mes = forms.ChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES, widget=forms.Select(attrs={'class': 'imp-25'}))
    tiporol = forms.ModelChoiceField(TipoRol.objects.filter(status=True), required=False, label=u'Tipo Rol', widget=forms.Select())
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False, label=u"Descripción")
    rubrorol = forms.ModelChoiceField(RubroRol.objects.filter(status=True, tiporubro=2), required=False, label=u'Novedades', widget=forms.Select())

    def acciones(self):
        deshabilitar_campo(self, 'anio')
        deshabilitar_campo(self, 'mes')
        deshabilitar_campo(self, 'tiporol')
        deshabilitar_campo(self, 'descripcion')


class ArchivoTitulacionForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo',
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))


class ArchivoIdiomaForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo',
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))


class ArchivoCapacitacionForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo',
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))


class ArchivoExperienciaForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo',
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))


class CapacitacionPersonaForm(FormModeloBase):
    institucion = forms.CharField(label=u'Institución', max_length=200, required=True, widget=forms.TextInput(attrs={'col': '6'}))
    nombre = forms.CharField(label=u'Nombre del evento', max_length=200, required=True, widget=forms.TextInput(attrs={'col': '6'}))
    descripcion = forms.CharField(label=u'Descripción del evento', required=False, widget=forms.Textarea({'rows': '3', 'col': '12'}))
    tipo = forms.ChoiceField(choices=TIPO_CAPACITACION_P, required=True, label=u'Tipo', widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    horas = forms.FloatField(initial=0, label=u'Horas', required=True,
                             widget=forms.TextInput(attrs={'col': '6'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=True,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=True,
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png', 'col': '6'}))
    tipocurso = forms.ModelChoiceField(label=u"Tipo de capacitación o actualización científica",
                                       queryset=TipoCurso.objects.filter(status=True), required=True,
                                       widget=forms.Select(attrs={'col':'6','class':'select2'}))
    tipoparticipacion = forms.ModelChoiceField(label=u"Tipo certificación", queryset=TipoParticipacion.objects.filter(status=True),
                                               required=True, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    tipocapacitacion = forms.ModelChoiceField(label=u"Programado plan Institucional",
                                              queryset=TipoCapacitacion.objects.all(), required=True,
                                              widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    modalidad = forms.ChoiceField(label=u"Modalidad", required=True, choices=MODALIDAD_CAPACITACION,
                                  widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    otramodalidad = forms.CharField(label=u'Otra Modalidad', max_length=600, required=False,
                                    widget=forms.TextInput(attrs={'col':'6'}))
    anio = forms.IntegerField(label=u"Año", initial=datetime.now().date().year, required=True, widget=forms.TextInput(attrs={'col':'6'}))
    contexto = forms.ModelChoiceField(label=u"Contexto de la capacitación/formación",
                                      queryset=ContextoCapacitacion.objects.all(), required=False,
                                      widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    detallecontexto = forms.ModelChoiceField(label=u"Detalle de contexto",
                                             queryset=DetalleContextoCapacitacion.objects.filter(status=True), required=False,
                                             widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    tipocertificacion = forms.ModelChoiceField(label=u"Tipo de planificación", queryset=TipoCertificacion.objects.all(),
                                               required=True, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento",
                                              queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False,
                                              widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento",
                                                 queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, vigente=True), required=False,
                                                 widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento",
                                                           queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, vigente=True),
                                                           required=False,
                                                           widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    auspiciante = forms.CharField(label=u'Auspiciante', max_length=200, required=False,
                                  widget=forms.TextInput(attrs={'col':'6'}))
    expositor = forms.CharField(label=u'Expositor', max_length=200, required=False,
                                widget=forms.TextInput(attrs={'col':'6'}))
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    provincia = forms.ModelChoiceField(label=u"Provincia / Estado", queryset=Provincia.objects.filter(status=True), required=False,
                                       widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    canton = forms.ModelChoiceField(label=u"Cantón / Ciudad", queryset=Canton.objects.filter(status=True), required=False,
                                    widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.filter(status=True), required=False,
                                       widget=forms.Select(attrs={'col':'6', 'class':'select2'}))


    # tiempo = forms.CharField(label=u'Tiempo', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=None,vigente=True, status=True)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=None,vigente=True, status=True)

    def editar(self, capacitacion):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=capacitacion.pais)
        self.fields['archivo'].required = False
        self.fields['canton'].queryset = Canton.objects.filter(provincia=capacitacion.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=capacitacion.canton)
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=capacitacion.areaconocimiento, vigente=True, status=True)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=capacitacion.subareaconocimiento, vigente=True, status=True)

    def quitar_campo_archivo(self):
        del self.fields['archivo']

class CapacitacionPersonaDocenteForm(forms.Form):
    institucion = forms.CharField(label=u'Institución', max_length=200, required=False, widget=forms.TextInput())
    nombre = forms.CharField(label=u'Nombre del evento', max_length=200, required=False, widget=forms.TextInput())
    descripcion = forms.CharField(label=u'Descripción del evento', required=False, widget=forms.Textarea({'rows': '3'}))
    tipocurso = forms.ModelChoiceField(label=u"Tipo de capacitación o actualización científica",
                                       queryset=TipoCurso.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '50%'}))
    tipoparticipacion = forms.ModelChoiceField(label=u"Tipo certificación",
                                               queryset=TipoParticipacion.objects.filter(pk__in=[1, 2, 3], status=True),
                                               required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    tipocapacitacion = forms.ModelChoiceField(label=u"Programado plan Institucional",
                                              queryset=TipoCapacitacion.objects.all(), required=False,
                                              widget=forms.Select(attrs={'formwidth': '50%'}))
    modalidad = forms.ChoiceField(label=u"Modalidad", required=False, choices=MODALIDAD_CAPACITACION,
                                  widget=forms.Select(attrs={'class': 'imp-25'}))
    otramodalidad = forms.CharField(label=u'Otra Modalidad', max_length=600, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-50'}))
    anio = forms.IntegerField(label=u"Año", initial=datetime.now().date().year, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%', 'labelwidth': '100px'}))
    # contexto = forms.ModelChoiceField(label=u"Contexto de la capacitación/formación", queryset=ContextoCapacitacion.objects.all(), required=False, widget=forms.Select())
    # detallecontexto = forms.ModelChoiceField(label=u"Detalle de contexto", queryset=DetalleContextoCapacitacion.objects.all(), required=False, widget=forms.Select())
    tipocertificacion = forms.ModelChoiceField(label=u"Tipo de planificación",
                                               queryset=TipoCertificacion.objects.filter(pk__in=[2, 3], status=True),
                                               required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Campo amplio de conocimiento",
                                              queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False,
                                              widget=forms.Select(attrs={'class': 'imp-75'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Campo específico de conocimiento",
                                                 queryset=SubAreaConocimientoTitulacion.objects.all(), required=False,
                                                 widget=forms.Select(attrs={'class': 'imp-75'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Campo detallado conocimiento",
                                                           queryset=SubAreaEspecificaConocimientoTitulacion.objects.all(),
                                                           required=False,
                                                           widget=forms.Select(attrs={'class': 'imp-75'}))
    # auspiciante = forms.CharField(label=u'Auspiciante', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    # expositor = forms.CharField(label=u'Expositor', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'formwidth': '80%'}))
    provincia = forms.ModelChoiceField(label=u"Provincia / Estado", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '80%'}))
    canton = forms.ModelChoiceField(label=u"Cantón / Ciudad", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'formwidth': '80%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '80%'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=False,
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '33%',
                                                                                          'labelwidth': '160px',
                                                                                          'controlwidth': '100px'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=False,
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'formwidth': '23%',
                                                                                       'labelwidth': '80',
                                                                                       'controlwidth': '100px'}))
    horas = forms.FloatField(initial=0, label=u'Horas', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'formwidth': '33%', 'decimal': '0', 'labelwidth': '80',
               'controlwidth': '100px'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))

    # tiempo = forms.CharField(label=u'Tiempo', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=None)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=None)

    def editar(self, capacitacion):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=capacitacion.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=capacitacion.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=capacitacion.canton)
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=capacitacion.areaconocimiento, vigente=True)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=capacitacion.subareaconocimiento, vigente=True)

    def quitar_campo_archivo(self):
        del self.fields['archivo']


class RiesgoTrabajoForm(forms.Form):
    codigo = forms.CharField(label=u'Código', required=False, max_length=5,
                             widget=forms.TextInput(attrs={'class': 'imp-25'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=150)

    def editar(self):
        deshabilitar_campo(self, 'codigo')


class DatosPersonaInstitucionForm(FormModeloBase):
    indicebiometrico = forms.CharField(label=u'Indice de Biométrico:', max_length=20, required=False,
                                       widget=forms.TextInput(attrs={'class': 'imp-codigo', 'col':'6'}))
    registro = forms.CharField(label=u'Nº Registro o certificación', max_length=20, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-codigo', 'col':'12'}))
    servidorcarrera = forms.BooleanField(label=u'Servidor de carrera', initial=False, required=False,
                                         widget=CheckboxInput(attrs={'col': '4', 'data-switchery':True}))
    concursomeritos = forms.BooleanField(label=u'Ingreso por concurso de meritos', initial=False, required=False,
                                         widget=CheckboxInput(attrs={'col': '8', 'data-switchery': True}))
    extension = forms.CharField(label=u'Extensión', max_length=20, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-number','col':'12'}))
    fechaingresoies = forms.DateField(label=u"Fecha ingreso IES", initial=datetime.now().date(), required=False,
                                     widget=DateTimeInput(format='%d-%m-%Y',
                                                          attrs={'col': '6'}))
    labora = forms.BooleanField(label=u'Labora actualmente', initial=False, required=False,
                                widget=CheckboxInput(attrs={'col': '6', 'data-switchery':True}))
    fechasalidaies = forms.DateField(label=u"Fecha salida IES", initial=datetime.now().date(), required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'col': '6'}))
    correoinstitucional = forms.CharField(label=u'Correo Institucional', max_length=200, required=False,
                                          widget=forms.TextInput(attrs={'col':'12'}))


class DatosInstitucionalesPersonaForm(forms.Form):
    extension = forms.CharField(label=u'Extensión telefónica', max_length=20, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-codigo'}))


class PlanAccionPreventivaForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '10%'}))
    periodo = forms.CharField(label=u'Periodo', max_length=150,
                              widget=forms.TextInput(attrs={'class': 'imp-descripcion', 'formwidth': '28%'}))
    responsablec = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), label=u'Responsable',
                                          required=False, widget=forms.Select(attrs={'formwidth': '30%'}))


class CabeceraPlanAccionPreventivaForm(forms.Form):
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=False,
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '30%'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=False,
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'formwidth': '30%'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), label=u'Responsable',
                                         widget=forms.Select(attrs={'class': 'imp-75'}))
    medida = forms.CharField(label=u'Medida', widget=forms.Textarea(attrs={'rows': '4', 'class': 'imp-100'}),
                             required=False)


class AgenteRiesgoForm(forms.Form):
    grupo = forms.ModelChoiceField(GrupoAgente.objects.filter(status=True), label=u'Grupo', required=False,
                                   widget=forms.Select(attrs={'formwidth': '50%'}))
    subgrupo = forms.ModelChoiceField(SubgrupoAgente.objects.filter(status=True), label=u'Subrupo', required=False,
                                      widget=forms.Select(attrs={'formwidth': '50%'}))
    apartado = forms.CharField(label=u'Apartado/Subapartado', required=False, max_length=250,
                               widget=forms.TextInput(attrs={'class': 'imp-100'}))
    codigo = forms.CharField(label=u'Código', required=False, max_length=5,
                             widget=forms.TextInput(attrs={'formwidth': '30%'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=250,
                                  widget=forms.TextInput(attrs={'formwidth': '70%'}))

    def editar(self):
        deshabilitar_campo(self, 'grupo')
        deshabilitar_campo(self, 'subgrupo')
        deshabilitar_campo(self, 'codigo')


class SubirEvidenciaForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Imagen', help_text=u'Tamaño Maximo permitido 10Mb, en formato jpg, png',
                           ext_whitelist=(".jpg", ".jpeg", ".png",), max_upload_size=10485760)


class EvaluacionRiesgoForm(forms.Form):
    from sagest.models import Bloque
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '100%'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=False,
                                         label=u'Responsable', widget=forms.Select(attrs={'formwidth': '60%'}))
    bloque = forms.ModelChoiceField(Bloque.objects.all(), label=u'Bloque', required=False,
                                    widget=forms.Select(attrs={'formwidth': '40%', 'labelwidth': '100px'}))
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), required=False,
        label=u'Departamento', widget=forms.Select())
    seccion = forms.ModelChoiceField(SeccionDepartamento.objects.all(), required=False, label=u'Seccion',
                                     widget=forms.Select(attrs={'formwidth': '60%'}))
    trabajador = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=False,
                                        label=u'Trabajador afectado', widget=forms.Select(attrs={'formwidth': '60%'}))
    trabajadoresexpuestos = forms.IntegerField(initial=0, label=u'N°. trabajadores', required=False,
                                               widget=forms.TextInput(
                                                   attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))

    def adicionar(self):
        self.fields['seccion'].queryset = SeccionDepartamento.objects.filter(departamento=None)


class DetalleEvaluacionRiesgoForm(forms.Form):
    agente = forms.ModelChoiceField(AgenteRiesgoRiesgo.objects.all(), label=u'Agente', required=False,
                                    widget=forms.Select())
    probabilidaddanio = forms.ChoiceField(choices=PROBABILIDAD_SEVERIDAD, label=u'Probabilidad que ocurra el daño',
                                          required=False,
                                          widget=forms.Select(attrs={'formwidth': '33%', 'labelwidth': '200px'}))
    severidaddanio = forms.ChoiceField(choices=PROBABILIDAD_SEVERIDAD, label=u'Severidad del daño', required=False,
                                       widget=forms.Select(attrs={'class': 'imp-75', 'formwidth': '33%'}))
    gradoriesgo = forms.CharField(label=u'Grado riesgo', max_length=250, required=False,
                                  widget=forms.TextInput(attrs={'formwidth': '33%'}))
    comentario = forms.CharField(label=u'Comentario', required=False, widget=forms.Textarea({'rows': '4'}))

    def adicionar(self):
        campo_solo_lectura(self, 'gradoriesgo')


class SeccionDepartamentoForm(forms.Form):
    descripcion = forms.CharField(label=u'Sección', required=False, widget=forms.TextInput())
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    responsablesubrogante = forms.IntegerField(initial=0, required=False, label=u'Responsable subrogante',
                                               widget=forms.TextInput(attrs={'select2search': 'true'}))
    codigoindice = forms.CharField(max_length=200, label=u'Codigo de Indice', required=False,
                                   widget=forms.TextInput(attrs={'class': 'imp-25'}))


class ProductoServicioSeccionForm(forms.Form):
    producto = forms.IntegerField(initial=0, required=False, label=u'Producto o servicio',
                                  widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '600px'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)


class ContratoRecaudacionForm(forms.Form):
    cliente = forms.IntegerField(initial=0, required=False, label=u'Arrendatario',
                                 widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '600px'}))
    tipoarriendo = forms.ModelChoiceField(TipoArriendo.objects.all(), label=u'Tipo de Arriendo', required=False,
                                          widget=forms.Select(attrs={'formwidth': '250px', 'labelwidth': '80px'}))
    lugar = forms.ModelChoiceField(LugarContrato.objects.all(), label=u'Lugar', required=False,
                                   widget=forms.Select(attrs={'formwidth': '400px', 'labelwidth': '80px'}))
    numero = forms.CharField(label=u'Número Contrato', required=False,
                             widget=forms.TextInput(attrs={'formwidth': '300px'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=False,
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '200px',
                                                                                          'labelwidth': '80px'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=False,
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'formwidth': '200px',
                                                                                       'labelwidth': '80px'}))
    diacobro = forms.IntegerField(initial=1, label=u"Día Cobro", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '200px', 'labelwidth': '80px'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=100,
                                  widget=forms.TextInput(attrs={'formwidth': '100%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato doc, docx, xlsx, pdf',
                           ext_whitelist=(".doc", ".docx", ".xlsx", ".pdf"), max_upload_size=10485760)

    def editar(self, contrato):
        deshabilitar_campo(self, 'cliente')
        self.fields['cliente'].widget.attrs['descripcion'] = contrato.cliente.nombre_completo()
        self.fields['cliente'].initial = contrato.cliente.id


class DetalleContratoRecaudacionForm(forms.Form):
    nombre = forms.ModelChoiceField(TipoOtroRubro.objects.all(), label=u'Nombre', required=False,
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    valor = forms.DecimalField(initial='0.00', label=u'Valor',
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%'}))
    iva = forms.BooleanField(label=u'Aplica IVA?', initial=False, required=False)
    recargo = forms.BooleanField(label=u'Tiene Recargo?', initial=False, required=False)
    porcientorecargo = forms.IntegerField(initial=0, label=u"Porciento Recargo", required=False,
                                          widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))

class ObservacionForm(FormModeloBase):
    observacion = forms.CharField(max_length=300, label=u"Observacion", required=True)

class TituloForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput(attrs={'col': '9'}))
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=10, required=True,
                                  widget=forms.TextInput(attrs={'col': '3'}))
    nivel = forms.ModelChoiceField(NivelTitulacion.objects.filter(status=True, tipo=1), label=u'Tipo de nivel',
                                   required=True,
                                   widget=forms.Select(attrs={'col': '6'}))
    grado = forms.ModelChoiceField(GradoTitulacion.objects.all(), label=u'Grado', required=False,
                                   widget=forms.Select(attrs={'col': '6'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento - Campo amplio",
                                              queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=True,
                                              widget=forms.Select())
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento - Campo específico",
                                                 queryset=SubAreaConocimientoTitulacion.objects.all(), required=True,
                                                 widget=forms.Select())
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especificaconocimiento - Campo Detallado",
                                                           queryset=SubAreaEspecificaConocimientoTitulacion.objects.all(),
                                                           required=True, widget=forms.Select())

    def editarvice(self, titulo):
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=titulo.areaconocimiento, vigente=True)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=titulo.subareaconocimiento, vigente=True)
        deshabilitar_campo(self, 'nombre')
        deshabilitar_campo(self, 'abreviatura')
        deshabilitar_campo(self, 'nivel')
        deshabilitar_campo(self, 'grado')

    def editartthh(self, titulo):
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=titulo.areaconocimiento, vigente=True)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=titulo.subareaconocimiento, vigente=True)
        deshabilitar_campo(self, 'areaconocimiento')
        deshabilitar_campo(self, 'subareaconocimiento')
        deshabilitar_campo(self, 'subareaespecificaconocimiento')


class PlanillaPresupuestoObraForm(forms.Form):
    tipoplanilla = forms.ChoiceField(choices=TIPO_PANILLA, required=False, label=u'Tipo Planilla', widget=forms.Select(
        attrs={'class': 'imp-75', 'formwidth': '310px', 'labelwidth': '160px'}))
    presupuestoobra = forms.ModelChoiceField(PresupuestoObra.objects.filter(estado=2).distinct(), required=False,
                                             label=u'Presupuesto',
                                             widget=forms.Select(attrs={'formwidth': '900px', 'labelwidth': '100px'}))
    periodoinicio = forms.DateField(label=u"Periodo inicio", required=False, initial=datetime.now().date(),
                                    input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                     attrs={'class': 'selectorfecha',
                                                                                            'formwidth': '310px',
                                                                                            'separator': 'true'}))
    periodofin = forms.DateField(label=u"Periodo fin", required=False, initial=datetime.now().date(),
                                 input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                  attrs={'class': 'selectorfecha',
                                                                                         'formwidth': '300px',
                                                                                         'labelwidth': '100px'}))
    mesplanilla = forms.ChoiceField(required=False, label=u'Mes Planilla', widget=forms.Select(
        attrs={'class': 'imp-75', 'formwidth': '310px', 'labelwidth': '160px'}))
    valoranticipo = forms.DecimalField(initial="0.00", label=u'Valor anticipo', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'formwidth': '310px', 'separator': 'true'}))
    monto = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'formwidth': '310px', 'labelwidth': '100px'}))

    def planilla_mes(self, duracion):
        self.fields['mesplanilla'].choices = [(i, i) for i in range(1, duracion + 1)]

    def adicionar(self):
        del self.fields['valoranticipo']
        del self.fields['monto']

    def complementaria(self):
        del self.fields['mesplanilla']

    def editar(self):
        deshabilitar_campo(self, 'tipoplanilla')
        deshabilitar_campo(self, 'mesplanilla')
        deshabilitar_campo(self, 'presupuestoobra')
        deshabilitar_campo(self, 'monto')
        deshabilitar_campo(self, 'periodoinicio')
        deshabilitar_campo(self, 'periodofin')


class AnexoRecursoForm(forms.Form):
    tipoanexo = forms.ChoiceField(label=u'Tipo', choices=TIPO_ANEXOS_RECURSOS,
                                  widget=forms.Select(attrs={'formwidth': '400px'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=250, widget=forms.TextInput())
    unidadmedida = forms.ModelChoiceField(UnidadMedidaPresupuesto.objects.filter(status=True),
                                          label=u'Unidad de medida', required=False,
                                          widget=forms.Select(attrs={'formwidth': '50%'}))
    costomaquinaria = forms.DecimalField(initial="0.00", label=u'Costo maquinaria', required=False,
                                         widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    costosalario = forms.DecimalField(initial="0.00", label=u'Costo salario', required=False,
                                      widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    costomateriale = forms.DecimalField(initial="0.00", label=u'Costo materiale', required=False,
                                        widget=forms.TextInput(attrs={'class': 'imp-moneda'}))


class NomencladorPresupuestoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=250, widget=forms.TextInput())
    unidadmedida = forms.ModelChoiceField(UnidadMedidaPresupuesto.objects.filter(status=True),
                                          label=u'Unidad de medida', required=False,
                                          widget=forms.Select(attrs={'formwidth': '50%'}))


class DetalleNomencladorForm(forms.Form):
    tiporecurso = forms.ChoiceField(label=u'Tipo', choices=TIPO_ACTIVIDAD_PRESUPUESTO,
                                    widget=forms.Select(attrs={'formwidth': '400px'}))
    rendimientoreferencia = forms.DecimalField(initial="0.0000", label=u'Rendimiento', required=False,
                                               widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=250, widget=forms.TextInput())
    unidadmedida = forms.ModelChoiceField(UnidadMedidaPresupuesto.objects.filter(status=True),
                                          label=u'Unidad de medida', required=False,
                                          widget=forms.Select(attrs={'formwidth': '50%'}))
    cantidadreferencia = forms.DecimalField(initial="0.0000", label=u'Cantidad', required=False,
                                            widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    preciomaterialunitario = forms.DecimalField(initial="0.0000", label=u'Precio unitario', required=False,
                                                widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    tarifareferencia = forms.DecimalField(initial="0.0000", label=u'Tarifa', required=False,
                                          widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    jornadareferencia = forms.DecimalField(initial="0.0000", label=u'Jornada', required=False,
                                           widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    costohorareferencia = forms.DecimalField(initial="0.0000", label=u'Costo hora', required=False,
                                             widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    otroindirecto = forms.DecimalField(initial="0.0000", label=u'Otro indirecto', required=False,
                                       widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    costoreferencia = forms.DecimalField(initial="0.0000", label=u'Costo', required=False,
                                         widget=forms.TextInput(attrs={'class': 'imp-moneda'}))

    def adicionar(self):
        deshabilitar_campo(self, 'costoreferencia')
        deshabilitar_campo(self, 'costohorareferencia')


class PresupuestoObraForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=300, required=False, widget=forms.TextInput())
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'rows': '3'}))
    porcentajeindirectoutilidad = forms.DecimalField(initial="0.00", label=u'Porcentaje Indirecto Utilidad',
                                                     required=False,
                                                     widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    duracion = forms.IntegerField(initial=0, label=u'Duración (Meses)', required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    ubicacion = forms.CharField(label=u'Ubicación', max_length=300, required=False, widget=forms.TextInput())


class AprobacionPresupuestoObraForm(forms.Form):
    contratonumero = forms.CharField(label=u'Número Contrato', required=True,
                                     widget=forms.TextInput(attrs={'formwidth': '400px'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=True,
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={
            'class': 'selectorfechainicio', 'formwidth': '200px', 'labelwidth': '80px'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=False,
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfechafin',
                                                                                       'formwidth': '200px',
                                                                                       'labelwidth': '80px'}))
    contratista = forms.IntegerField(initial=0, required=False, label=u'Contratista',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    fiscalizador = forms.IntegerField(initial=0, required=False, label=u'Fiscalizador',
                                      widget=forms.TextInput(attrs={'select2search': 'true'}))
    administradorcontrato = forms.IntegerField(initial=0, required=False, label=u'Administrador Contrato',
                                               widget=forms.TextInput(attrs={'select2search': 'true'}))


class RechazarPresupuestoObraForm(forms.Form):
    observacion = forms.CharField(max_length=300, label=u"Observacion", required=False)


class TipoOtroRubroForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=250, required=True,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    partida = forms.ModelChoiceField(Partida.objects.filter(status=True), required=False, label=u'Item',
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    programa = forms.ModelChoiceField(PartidaPrograma.objects.filter(status=True), required=False, label=u'Programa',
                                      widget=forms.Select(attrs={'formwidth': '100%'}))
    unidad_organizacional = forms.ModelChoiceField(Departamento.objects.filter(status=True), required=False,
                                                   label=u'Unidad Or.',
                                                   widget=forms.Select(attrs={'formwidth': '100%'}))
    tipo = forms.ChoiceField(choices=TIPO_RUBRO, required=False, label=u'Tipo Rubro',
                             widget=forms.Select(attrs={'formwidth': '100%'}))
    ivaaplicado = forms.ModelChoiceField(IvaAplicado.objects.filter(status=True), required=True, label=u'Iva Aplicado',
                                         widget=forms.Select(attrs={'formwidth': '50%'}))
    valor = forms.DecimalField(label=u"Valor por defecto", required=False, initial="0.00",
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    interface = forms.BooleanField(initial=False, label=u'Interface', required=False)
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)
    nofactura = forms.BooleanField(initial=False, label=u'No Emitir Factura', required=False)
    exportabanco = forms.BooleanField(initial=False, label=u'Se exporta', required=False)

    def edit(self, rubro, anio):
        if rubro.en_uso(anio):
            deshabilitar_campo(self, 'partida')


class CostosForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=250, required=False,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))


class TipoOtroRubroPartidaForm(FormModeloBase):
    partida = forms.ModelChoiceField(PartidasSaldo.objects.filter(status=True), required=False, label=u'Item',
                                     widget=forms.Select(attrs={'class': 'form-control'}))

    def adicionar(self, anio, partida):
        x = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio, partida=partida)
        self.fields['partida'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio,
                                                                       partida=partida)

    def edit(self, rubro, anio, partida):
        self.fields['partida'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio,
                                                                       partida=partida)
        self.fields['partida'].widget.attrs['descripcion'] = rubro.partidassaldo.codigo_todo
        self.fields['partida'].initial = rubro.partidassaldo.id


class CentroCostoSaldoForm(forms.Form):
    saldo = forms.ModelChoiceField(CentroCostoSaldo.objects.filter(status=True), required=False, label=u'Saldo',
                                   widget=forms.Select(attrs={'formwidth': '100%'}))

    def adicionar(self, anio):
        self.fields['partida'].queryset = CentroCostoSaldo.objects.filter(aniofiscal__anioejercicio=anio)

    def edit(self, costo, anio):
        self.fields['saldo'].queryset = CentroCostoSaldo.objects.filter(aniofiscal__anioejercicio=anio)
        self.fields['saldo'].widget.attrs['descripcion'] = costo.saldo_periodo()
        self.fields['saldo'].initial = costo.saldo_periodo().id


class ActividadPresupuestoObraForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'rows': '3'}))
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-moneda'}))


class PodPeriodoForm(forms.Form):
    anio = forms.IntegerField(initial=datetime.now().year, label=u"Año", required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    descripcion = forms.CharField(max_length=300, label=u"Descripción", required=False)
    inicio = forms.DateField(label=u"Fecha inicio Evaluación", required=False, input_formats=['%d-%m-%Y'],
                             widget=DateTimeInput(format='%d-%m-%Y',
                                                  attrs={'class': 'selectorfecha', 'formwidth': '40%'}))
    fin = forms.DateField(label=u"Fecha fin Evaluación", required=False, input_formats=['%d-%m-%Y'],
                          widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '40%'}))
    iniciopod = forms.DateField(label=u"Fecha Inicio POD", required=False, input_formats=['%d-%m-%Y'],
                                widget=DateTimeInput(format='%d-%m-%Y',
                                                     attrs={'class': 'selectorfecha', 'formwidth': '40%'}))
    finpod = forms.DateField(label=u"Fecha Fin POD", required=False, input_formats=['%d-%m-%Y'],
                             widget=DateTimeInput(format='%d-%m-%Y',
                                                  attrs={'class': 'selectorfecha', 'formwidth': '40%'}))
    inicioeval = forms.DateField(label=u"Fecha Inicio EVAL", required=False, input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y',
                                                      attrs={'class': 'selectorfecha', 'formwidth': '40%'}))
    fineval = forms.DateField(label=u"Fecha Fin EVAL", required=False, input_formats=['%d-%m-%Y'],
                              widget=DateTimeInput(format='%d-%m-%Y',
                                                   attrs={'class': 'selectorfecha', 'formwidth': '40%'}))
    publicacion = forms.DateField(label=u"Fecha Publicación", required=False, input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '40%'}))
    archivo = ExtFileField(label=u'Adjunto', required=False, help_text=u'Tamaño Maximo permitido 5Mb, en formato pdf',
                           ext_whitelist=(".pdf",), max_upload_size=5242880)

    def edit(self):
        deshabilitar_campo(self, 'anio')
        # deshabilitar_campo(self, 'descripcion')


class PodPeriodoFactorForm(forms.Form):
    podfactor = forms.ModelChoiceField(PodFactor.objects.filter(status=True), required=False, label=u'Factor',
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    minimo = forms.FloatField(label=u"Mínimo", required=False, initial="0.00",
                              widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    maximo = forms.FloatField(label=u"Máximo", required=False, initial="0.00",
                              widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    orden = forms.IntegerField(initial=0, label=u"Orden", required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))

    def adicionar(self):
        deshabilitar_campo(self, 'minimo')
        deshabilitar_campo(self, 'maximo')

    def edit(self):
        deshabilitar_campo(self, 'podfactor')


class PodFactorForm(forms.Form):
    descripcion = forms.CharField(max_length=300, label=u"Descripción", required=False)
    tipofactor = forms.ChoiceField(choices=TIPO_FACTOR, required=False, label=u'Tipo Factor',
                                   widget=forms.Select(attrs={'formwidth': '50%'}))
    minimo = forms.FloatField(label=u"Mínimo", required=False, initial="0.00",
                              widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    maximo = forms.FloatField(label=u"Máximo", required=False, initial="0.00",
                              widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class PodProductoForm(forms.Form):
    nombre = forms.CharField(label=u'Descripción', widget=forms.Textarea({'rows': '5'}))


class PodDiccionarioCompLaboralForm(forms.Form):
    tipo = forms.ChoiceField(choices=TIPO_COMPETENCIA, required=True, label=u'Tipo de Competencia',
                             widget=forms.Select(attrs={'formwidth': '50%'}))
    denominacion = forms.CharField(max_length=300, label=u"Denominación", required=True)
    definicion = forms.CharField(label=u'Definición', widget=forms.Textarea({'rows': '5'}))


class PagoForm(forms.Form):
    valor = forms.DecimalField(label=u"Valor", initial="0.00",
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    factura = forms.IntegerField(label=u"No. Factura")
    facturaruc = forms.CharField(label=u'RUC/Cedula', max_length=20)
    facturanombre = forms.CharField(label=u'Nombre', max_length=100)
    facturadireccion = forms.CharField(label=u"Dirección", max_length=100)
    facturatelefono = forms.CharField(label=u"Telefono", max_length=50)
    formadepago = forms.ModelChoiceField(label=u'Forma de Pago', queryset=FormaDePago.objects.all())
    # Efectivo
    # Cheque
    numero = forms.CharField(label=u'Numero Cheque', max_length=50, required=False)
    bancocheque = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False)
    fechacobro = forms.DateField(label=u"Fecha Cobro", input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                                 required=False)
    emite = forms.CharField(label=u"Emisor", max_length=100, required=False)
    # Tarjeta
    referencia = forms.CharField(label=u"Referencia", max_length=50, required=False)
    bancotarjeta = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False)
    tipo = forms.ModelChoiceField(label=u"Tipo", queryset=TipoTarjetaBanco.objects.all(), required=False)
    procedencia = forms.ModelChoiceField(label=u"Procedencia", queryset=ProcedenciaTarjeta.objects.all(),
                                         required=False)
    poseedor = forms.CharField(label=u'Poseedor', max_length=100, required=False)
    procesadorpago = forms.ModelChoiceField(label=u"Procesador de Pago", queryset=ProcesadorPagoTarjeta.objects.all(),
                                            required=False)
    # Transferencia/Deposito
    referenciatransferencia = forms.CharField(label=u'Referencia', max_length=50, required=False)
    cuentabanco = forms.ModelChoiceField(label=u"Cuenta", queryset=CuentaBanco.objects.all(), required=False)


class FormaPagoForm(forms.Form):
    valor = forms.DecimalField(label=u"Valor", initial="0.00",
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    formadepago = forms.ModelChoiceField(label=u'Forma de Pago', queryset=FormaDePago.objects.all())
    # EFECTIVO
    # CHEQUE
    cuentacheque = forms.CharField(label=u'Numero Cuenta', max_length=50, required=False)
    tipocheque = forms.ModelChoiceField(label=u'Tipo de cheque', queryset=TipoCheque.objects.all())
    numero = forms.CharField(label=u'Numero Cheque', max_length=50, required=False)
    bancocheque = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False)
    fechacobro = forms.DateField(label=u"Fecha Cobro", input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                                 required=False)
    emite = forms.CharField(label=u"Emisor", max_length=100, required=False)
    # TARJETA
    referencia = forms.CharField(label=u"Referencia", max_length=50, required=False)
    bancotarjeta = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False)
    tipo = forms.ModelChoiceField(label=u"Tipo", queryset=TipoTarjetaBanco.objects.all(), required=False)
    procedencia = forms.ModelChoiceField(label=u"Procedencia", queryset=ProcedenciaTarjeta.objects.all(),
                                         required=False)
    poseedor = forms.CharField(label=u'Poseedor', max_length=100, required=False)
    procesadorpago = forms.ModelChoiceField(label=u"Procesador de Pago", queryset=ProcesadorPagoTarjeta.objects.all(),
                                            required=False)
    # TRANSFERENCIA/DEPOSITO
    fechadep = forms.DateField(label=u"Fecha Cobro", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                               required=False)
    tipotransferencia = forms.ModelChoiceField(label=u'Tipo de Transf.', queryset=TipoTransferencia.objects.all())
    referenciatransferencia = forms.CharField(label=u'Referencia', max_length=50, required=False)
    cuentabanco = forms.ModelChoiceField(label=u"Cuenta", queryset=CuentaBanco.objects.all(), required=False)
    # ELECTRONICO
    referenciaelectronico = forms.CharField(label=u'Referencia', max_length=50, required=False)


class SesionCajaForm(forms.Form):
    fondo = forms.DecimalField(label=u"Fondo Inicial", initial='0.00',
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class CierreSesionCajaForm(forms.Form):
    bill100 = forms.IntegerField(label=u"Cant. Billetes de 100", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    mon1 = forms.IntegerField(label=u"Cant. Monedas de 1", initial=0, required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    bill50 = forms.IntegerField(label=u"Cant. Billetes de 50", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    mon50 = forms.IntegerField(label=u"Cant. Monedas de 50c", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    bill20 = forms.IntegerField(label=u"Cant. Billetes de 20", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    mon25 = forms.IntegerField(label=u"Cant. Monedas de 25c", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    bill10 = forms.IntegerField(label=u"Cant. Billetes de 10", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    mon10 = forms.IntegerField(label=u"Cant. Monedas de 10c", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    bill5 = forms.IntegerField(label=u"Cant. Billetes de 5", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    mon5 = forms.IntegerField(label=u"Cant. Monedas de 5c", initial=0, required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    bill2 = forms.IntegerField(label=u"Cant. Billetes de 2", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    mon1c = forms.IntegerField(label=u"Cant. Monedas de 1c", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    bill1 = forms.IntegerField(label=u"Cant. Billetes de 1", initial=0, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    deposito = forms.DecimalField(label=u"Total Depositos", initial="0.00", required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    cheques = forms.DecimalField(label=u"Total Cheques", initial="0.00", required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    transfer = forms.DecimalField(label=u"Total Transferencias", initial="0.00", required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    tarjeta = forms.DecimalField(label=u"Total Tarjetas de crédito/débito", initial="0.00", required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    electronico = forms.DecimalField(label=u"Total Dinero electrónico", initial="0.00", required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    recibocaja = forms.DecimalField(label=u"Total Recibo Caja", initial="0.00", required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    total = forms.DecimalField(label=u"Total", initial="0.00", required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class CajeroForm(FormModeloBase):
    persona = forms.ModelChoiceField(label="Cajero", required=True,
                                           queryset=Persona.objects.select_related().filter(status=True),
                                           widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    puntoventa = forms.ModelChoiceField(queryset=PuntoVenta.objects.select_related().filter(status=True), required=True, label=u'Punto de venta', widget=forms.Select(attrs={'col':'12', 'class': 'select2'}))
    nombre = forms.CharField(label=u'Caja:', required=True, widget=forms.TextInput({'placeholder': 'Describa el periodo de gastos  a crear'}))


class ReporteFacturaCajeroForm(FormModeloBase):
    from sagest.models import LugarRecaudacion
    TIPO_ARCHIVO_REPORTE = ((1, u'PDF'), (2, u'EXCEL'))
    tipoarchivo = forms.ChoiceField(choices=TIPO_ARCHIVO_REPORTE, label=u'Tipo de Archivo', required=True,
                                    widget=forms.Select(attrs={'col':'12', 'class':'select2'}))
    cajero = forms.ModelChoiceField(label="Cajero", required=True,
                                           queryset=LugarRecaudacion.objects.filter(status=True),
                                           widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    fecha = forms.DateField(label=u"Fecha", required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))


class FacturarBecaForm(forms.Form):
    factura = forms.IntegerField(label=u"No. Factura",
                                 widget=forms.TextInput(attrs={'class': 'imp-25', 'decimal': '0'}))
    tipoidentificacion = forms.ChoiceField(label=u'Tipo', choices=TIPOS_IDENTIFICACION,
                                           widget=forms.Select(attrs={'class': 'imp-25'}))
    facturaruc = forms.CharField(max_length=20, label=u'RUC/Cedula', widget=forms.TextInput(attrs={'class': 'imp-25'}))
    facturanombre = forms.CharField(max_length=100, label=u'Nombre')
    facturadireccion = forms.CharField(max_length=100, label=u"Dirección")
    facturatelefono = forms.CharField(max_length=50, label=u"Teléfono",
                                      widget=forms.TextInput(attrs={'class': 'imp-25'}))


class MoverFacturaForm(forms.Form):
    sesion = forms.ModelChoiceField(SesionCaja.objects.all().order_by('-fecha'), label=u'Sesión')

    def fechainicio(self, factura):
        cajero = factura.sesioncaja.caja
        fechainicio = factura.fecha - timedelta(days=15)
        fechafin = (datetime(factura.fecha.year, factura.fecha.month, factura.fecha.day, 0, 0, 0) + timedelta(
            days=15)).date()
        self.fields['sesion'].queryset = SesionCaja.objects.filter(fecha__gte=fechainicio, fecha__lte=fechafin,
                                                                   caja=cajero)


class CorreoFacturaForm(forms.Form):
    email = forms.CharField(label=u"Correo Electronico", max_length=240, required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50'}))


class FacturaCorreccionForm(forms.Form):
    email = forms.CharField(label=u"Correo Electronico", max_length=240, required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50'}))
    tipo = forms.ChoiceField(choices=TIPOS_IDENTIFICACION, required=False, label=u'Tipo Identificación',
                             widget=forms.Select(attrs={'formwidth': '50%'}))
    identificacion = forms.CharField(label=u"No. Identificación", max_length=15, required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-cedula', 'formwidth': '50%'}))


class EliminarRubroForm(forms.Form):
    motivo = forms.CharField(label=u'Motivo', max_length=200)

class PeriodoForm(FormModeloBase):
    periodo = forms.ModelChoiceField(Periodo.objects.filter(status=True), required=True,
                           label=u'Periodo',
                           widget=forms.Select(attrs={'formwidth': '100%','class': 'select2'}))


class RubroForm(forms.Form):
    fechavence = forms.DateField(label=u"Fecha Vencimiento", input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))


class RubroValorForm(forms.Form):
    valor = forms.DecimalField(label=u'Valor', initial="0.00",
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class NombreRubroForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=300, widget=forms.TextInput())


class LiquidarRubroForm(forms.Form):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea({'class': 'imp-100', 'rows': '2'}))


class DescuentoRecargoForm(forms.Form):
    porciento = forms.IntegerField(label=u'% aplicado',
                                   widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    motivo = forms.CharField(label=u'Motivo', max_length=100)


class ValeCajaForm(forms.Form):
    recibe = forms.CharField(label=u'Recibe', max_length=200, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    responsable = forms.CharField(label=u'Autoriza', max_length=200, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    referencia = forms.CharField(label=u'Referencia', max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-75'}))
    concepto = forms.CharField(label=u'Concepto', widget=forms.Textarea)
    valor = forms.DecimalField(label=u'Valor', initial="0.00",
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class ReciboCajaForm(forms.Form):
    persona = forms.IntegerField(initial=1, required=False, label=u'Entrega',
                                 widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '600px'}))
    partidassaldo = forms.ModelChoiceField(label=u"Partida", queryset=PartidasSaldo.objects.filter(partida__tipo=2),
                                           required=False)
    fechacomprobante = forms.DateField(label=u"Fecha Comprobante", required=True, widget=DateTimeInput(attrs={'class': 'form-control', 'formwidth': '50%'}))
    valor = forms.DecimalField(label=u'Valor', initial="0.00",
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    concepto = forms.CharField(label=u'Concepto', widget=forms.Textarea({'rows': '3'}))

    def adicionar(self, anio):
        self.fields['partidassaldo'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio,
                                                                             partida__tipo=2)

    def editar(self, recibo, anio):
        self.fields['partidassaldo'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio,
                                                                             partida__tipo=2)
        deshabilitar_campo(self, 'persona')
        self.fields['persona'].widget.attrs['descripcion'] = recibo.persona.nombre_completo()
        self.fields['persona'].initial = recibo.persona.id


class FacturaCanceladaForm(forms.Form):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea({'rows': '2'}))


class ReciboCajaPagoAnularForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)


class CancelacionCuentaForm(forms.Form):
    cuentabanco = forms.ModelChoiceField(label=u"Cuenta", queryset=CuentaBanco.objects.all(), required=False)
    fecha = forms.DateField(label=u"Fecha Comprobante", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    referenciadeposito = forms.CharField(label=u"Referencia Depósito", max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'class': 'imp-codigo'}))
    valor = forms.DecimalField(label=u"Valor", initial="0.00",
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class ChequeProtestadoForm(forms.Form):
    motivo = forms.CharField(label=u'Motivo', max_length=200)


class ChequeFechaCobroForm(forms.Form):
    fechacobro = forms.DateField(label=u"Fecha Cobro", input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))


class ClienteExternoForm(forms.Form):
    from sga.models import Sexo
    tipopersona = forms.ChoiceField(choices=TIPO_PERSONA, label=u'Tipo Persona', required=False,
                                    widget=forms.Select(attrs={'formwidth': '40%'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u"Nombres", max_length=100, required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-50'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(),
                                  widget=forms.Select(attrs={'formwidth': '40%'}))
    ruc = forms.CharField(label=u"RUC", max_length=13, required=False,
                          widget=forms.TextInput(attrs={'class': 'imp-ruc'}))
    nombreempresa = forms.CharField(label=u"Nombre Empresa", required=False, max_length=100,
                                    widget=forms.TextInput(attrs={'class': 'imp-100'}))
    nombrecomercial = forms.CharField(label=u"Nombre Comercial", required=False, max_length=200,
                                      widget=forms.TextInput(attrs={'class': 'imp-100'}))
    contribuyenteespecial = forms.BooleanField(initial=False, label=u"Es Contrib. Espec.", required=False)
    nacimiento = forms.DateField(label=u"Fecha Nacimiento o Constitución", initial=datetime.now().date(),
                                 input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                                 required=False)
    pais = forms.ModelChoiceField(label=u"País residencia", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'formwidth': '75%'}))
    provincia = forms.ModelChoiceField(label=u"Provincia residencia", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '75%'}))
    canton = forms.ModelChoiceField(label=u"Canton residencia", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'formwidth': '75%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia residencia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '75%'}))
    sector = forms.CharField(label=u"Sector", max_length=100, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-50'}))
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-75'}))
    direccion2 = forms.CharField(label=u"Calle Secundaria", max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-75'}))
    num_direccion = forms.CharField(label=u"Numero Domicilio", max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-25'}))
    telefono = forms.CharField(label=u"Telefono Movil", max_length=100, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-25'}))
    telefono_conv = forms.CharField(label=u"Telefono Fijo", max_length=100, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-25'}))
    email = forms.CharField(label=u"Correo Electronico", max_length=240, required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50'}))
    nombrecontacto = forms.CharField(label=u"Nombre Representante", required=False, max_length=200,
                                     widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefonocontacto = forms.CharField(label=u"Telefono Representante", max_length=100, required=False,
                                       widget=forms.TextInput(attrs={'class': 'imp-25'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)

    def editar(self, persona):
        deshabilitar_campo(self, 'tipopersona')
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)


class ClienteExternoCraiForm(forms.Form):
    from sga.models import Sexo
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u"Nombres", max_length=100, required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-50'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(),
                                  widget=forms.Select(attrs={'formwidth': '40%'}))
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-75'}))
    direccion2 = forms.CharField(label=u"Calle Secundaria", max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-75'}))


class ArchivoFirmado(forms.Form):
    archivo = forms.FileField()


class ComprobanteRecaudacionForm(forms.Form):
    tipocomprobante = forms.ModelChoiceField(queryset=TipoComprobanteRecaudacion.objects.all().order_by('id'),
                                             required=False, widget=forms.Select(attrs={'formwidth': '75%'}),
                                             label=u'Tipo Comprobante')
    puntoemision = forms.ModelChoiceField(queryset=PuntoVenta.objects.all(), required=False,
                                          widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Punto Emisión')
    fechacomp = forms.DateField(label=u"Fecha Comprobante", required=False, initial=datetime.now().date(),
                                input_formats=['%d-%m-%Y'],
                                widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fecha = forms.DateField(label=u"Fecha Recaudación", required=False, initial=datetime.now().date(),
                            input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechanotacredito = forms.DateField(label=u"Fecha Nota Credito", required=False, initial=datetime.now().date(),
                                       input_formats=['%d-%m-%Y'],
                                       widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    cuentadepositopac = forms.ModelChoiceField(label=u"Cuenta", required=False, queryset=CuentaBanco.objects.all(),
                                               widget=forms.Select())
    cuentadepositocent = forms.ModelChoiceField(label=u"Cuenta", required=False,
                                                queryset=CuentaBanco.objects.filter(banco__id=2), widget=forms.Select())
    depositante = forms.CharField(label=u"Depositante", required=False, max_length=300)
    conceptotrans = forms.ModelChoiceField(queryset=TipoConceptoTransferenciaGobierno.objects.all().order_by('id'),
                                           required=False, widget=forms.Select(attrs={'formwidth': '100%'}),
                                           label=u'Concepto Transferencia')
    concepto = forms.CharField(label=u'Concepto', required=False, widget=forms.Textarea({'rows': '2'}))
    referencia = forms.CharField(label=u'Referencia', required=False, widget=forms.Textarea({'rows': '2'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    montopresupuestado = forms.DecimalField(initial="0.00", label=u'Monto Presupuestado', required=False,
                                            widget=forms.TextInput(
                                                attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    diferencia = forms.DecimalField(initial="0.00", label=u'Diferencia', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '210px', 'labelwidth': '80px'}))
    numerocur = forms.IntegerField(initial="0", label=u'Número CUR', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '300px', 'labelwidth': '100px'}))
    cuota = forms.CharField(label=u"Cuota", required=False, max_length=300,
                            widget=forms.TextInput(attrs={'formwidth': '600px'}))
    valordeposito = forms.DecimalField(initial="0.00", label=u'Valor a depositar', required=False,
                                       widget=forms.TextInput(
                                           attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    valornotacredito = forms.DecimalField(initial="0.00", label=u'Valor nota credito', required=False,
                                          widget=forms.TextInput(
                                              attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    valorfactura = forms.DecimalField(initial="0.00", label=u'Valor documentos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '210px', 'labelwidth': '80px'}))
    valorotros = forms.DecimalField(initial="0.00", label=u'Otros Valores', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '210px', 'labelwidth': '80px'}))
    valortotal = forms.DecimalField(initial="0.00", label=u'Valor Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))

    def adicionar(self):
        deshabilitar_campo(self, 'valortotal')
        deshabilitar_campo(self, 'valordeposito')
        deshabilitar_campo(self, 'valornotacredito')
        deshabilitar_campo(self, 'valorfactura')
        deshabilitar_campo(self, 'diferencia')

    def editar(self):
        deshabilitar_campo(self, 'valortotal')
        deshabilitar_campo(self, 'valordeposito')
        deshabilitar_campo(self, 'valornotacredito')
        deshabilitar_campo(self, 'valorfactura')
        deshabilitar_campo(self, 'tipocomprobante')
        deshabilitar_campo(self, 'puntoemision')
        deshabilitar_campo(self, 'fechacomp')
        deshabilitar_campo(self, 'fecha')
        deshabilitar_campo(self, 'fechanotacredito')


class DevengarComprobanteForm(forms.Form):
    fechacomp = forms.DateField(label=u"Fecha Comprobante", required=False, initial=datetime.now().date(),
                                input_formats=['%d-%m-%Y'],
                                widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechabanco = forms.DateField(label=u"Fecha Banco Central", required=False, initial=datetime.now().date(),
                                 input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechaesigef = forms.DateField(label=u"Fecha Esigef", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    depositante = forms.CharField(label=u"Depositante", required=False, max_length=300)
    conceptodevengado = forms.CharField(label=u'Concepto', required=False, widget=forms.Textarea({'rows': '2'}))
    curdevengado = forms.IntegerField(initial="0", label=u'Número CUR', required=False,
                                      widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '300px'}))
    valortotal = forms.DecimalField(initial="0.00", label=u'Valor Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))

    def percibir(self):
        deshabilitar_campo(self, 'fechacomp')

    def bloquea_campo_total(self):
        campo_solo_lectura(self, 'valortotal')


class PercibirComprobanteForm(forms.Form):
    fechacomp = forms.DateField(label=u"Fecha Comprobante", required=False, initial=datetime.now().date(),
                                input_formats=['%d-%m-%Y'],
                                widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechaesigef = forms.DateField(label=u"Fecha Esigef", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    depositante = forms.CharField(label=u"Depositante", required=False, max_length=300)
    conceptopercibido = forms.CharField(label=u'Concepto', required=False, widget=forms.Textarea({'rows': '2'}))
    valortotal = forms.DecimalField(initial="0.00", label=u'Valor Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))

    def percibircomprobante(self):
        campo_solo_lectura(self, 'fechacomp')
        campo_solo_lectura(self, 'valortotal')

    def bloquearcomprobante(self):
        deshabilitar_campo(self, 'fechacomp')
        deshabilitar_campo(self, 'valortotal')
        deshabilitar_campo(self, 'fechaesigef')
        deshabilitar_campo(self, 'depositante')
        deshabilitar_campo(self, 'conceptopercibido')


class CurPercibirForm(forms.Form):
    afectatotal = forms.ChoiceField(label=u"Afecta al Total", choices=AFECTATOTAL, required=False,
                                    widget=forms.Select(attrs={'formwidth': '50%'}))
    fechabce = forms.DateField(label=u"Fecha BCE", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'formwidth': '300px'}))
    numerocur = forms.IntegerField(initial="0", label=u'Número CUR', required=False,
                                   widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '300px'}))
    valorcur = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    tipocobro = forms.ModelChoiceField(FormaDePago.objects.filter(status=True).order_by('id'), required=False,
                                       label=u'Tipo Recaudación', widget=forms.Select(attrs={'formwidth': '100%'}))


class PartidasDevengarForm(forms.Form):
    cuenta = forms.ModelChoiceField(
        CuentaContable.objects.filter((Q(cuenta__icontains='113') | Q(cuenta__icontains='112')), status=True),
        required=False, label=u'Item', widget=forms.Select(attrs={'formwidth': '100%'}))
    valor = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))


class ResumenComprobantePartidaForm(forms.Form):
    partida = forms.ModelChoiceField(PartidasSaldo.objects.filter(status=True, partida__tipo=2), required=False,
                                     label=u'Item', widget=forms.Select(attrs={'formwidth': '100%'}))
    valor = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))

    def adicionar(self, anio):
        self.fields['partida'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio,
                                                                       partida__tipo=2)

    def edit(self, partida, anio):
        self.fields['partida'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio,
                                                                       partida__tipo=2)
        self.fields['partida'].widget.attrs['descripcion'] = partida.partida.codigo_todo
        self.fields['partida'].initial = partida.partida.id


class TramitePagoForm(forms.Form):
    tipotramite = forms.ModelChoiceField(queryset=TipoTramite.objects.all().order_by('id'), required=False,
                                         widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Tipo Trámite')
    motivo = forms.CharField(label=u'Motivo', required=False, widget=forms.Textarea({'rows': '2'}))
    valortotal = forms.DecimalField(initial="0.00", label=u'Valor Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))

    def adicionar(self, persona):
        self.fields['tipotramite'].queryset = TipoTramite.objects.filter(grupo__in=persona.grupos())


class TraspasoTramiteForm(forms.Form):
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.filter(integrantes__isnull=False).distinct().order_by('id'), required=False,
        widget=forms.Select(attrs={'formwidth': '80%'}), label=u'Departamento')
    accion = forms.ModelChoiceField(queryset=AccionesTramitePago.objects, required=False,
                                    widget=forms.Select(attrs={'formwidth': '80%'}), label=u'Acción')


class RechazoTramiteForm(forms.Form):
    motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea(attrs={'rows': '2', 'controlwidth': '600px'}))


class DocumentoTramiteForm(forms.Form):
    tipodocumento = forms.ModelChoiceField(queryset=TipoDocumentoTramitePago.objects.all().order_by('id'),
                                           required=False, widget=forms.Select(attrs={'formwidth': '75%'}),
                                           label=u'Tipo Documento')
    beneficiario = forms.ModelChoiceField(queryset=BeneficiariTramitePago.objects, required=False,
                                          widget=forms.Select(attrs={'formwidth': '80%'}), label=u'Beneficiario')
    numero = forms.IntegerField(label=u"Número", initial=0, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-number'}))
    nombre = forms.CharField(label=u"Nombre", max_length=300, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))
    descripcion = forms.CharField(label=u'Descripcion', required=False, widget=forms.Textarea({'rows': '2'}))
    subtotal0 = forms.DecimalField(label=u"Subtotal0", initial="0.00", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '300px'}))
    subtotaliva = forms.DecimalField(initial="0.00", label=u'Subtotal IVA', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    baseimponible = forms.DecimalField(initial="0.00", label=u'Base Imponible', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    iva = forms.DecimalField(initial="0.00", label=u'IVA', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    descuento = forms.DecimalField(initial="0.00", label=u'Descuento', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    total = forms.DecimalField(initial="0.00", label=u'Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    archivo = ExtFileField(required=False, label=u'Seleccione Archivo',
                           help_text=u'Tamaño Maximo permitido 20Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"),
                           max_upload_size=20971520)

    def adicionar(self, tramite):
        deshabilitar_campo(self, 'total')
        deshabilitar_campo(self, 'baseimponible')
        self.fields['beneficiario'].queryset = BeneficiariTramitePago.objects.filter(
            id__in=tramite.beneficiaritramitepago_set.all()).distinct()

    def editar(self, documento):
        del self.fields['archivo']
        if not documento.tipodocumento.id == 1:
            del self.fields['subtotaliva']
            del self.fields['total']
        else:
            deshabilitar_campo(self, 'subtotal0')
            deshabilitar_campo(self, 'subtotaliva')
            deshabilitar_campo(self, 'total')

    def subir(self):
        del self.fields['tipodocumento']
        del self.fields['nombre']
        del self.fields['descripcion']
        del self.fields['subtotal0']
        del self.fields['subtotaliva']
        del self.fields['total']
        del self.fields['numero']
        del self.fields['beneficiario']
        del self.fields['baseimponible']
        del self.fields['iva']
        del self.fields['descuento']


class DocumentoXmlTramiteForm(forms.Form):
    numero = forms.CharField(label=u'Número Documento', widget=forms.TextInput(attrs={'class': 'imp-comprobantes'}))
    archivo = ExtFileField(required=False, label=u'Seleccione Archivo',
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato xml', ext_whitelist=(".xml", ".txt"),
                           max_upload_size=4194304)


class DocumentoPdfTramiteForm(forms.Form):
    archivo = ExtFileField(required=False, label=u'Seleccione Archivo',
                           help_text=u'Tamaño Maximo permitido 20Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=20971520)


class BeneficiariosForm(forms.Form):
    beneficiario = forms.IntegerField(required=False,
                                      widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '75%'}),
                                      label=u'Beneficiario')
    total = forms.DecimalField(initial="0.00", label=u'Valor', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))


class CentroCostoForm(forms.Form):
    detalle = forms.IntegerField(required=False,
                                 widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}),
                                 label=u'Costo')
    total = forms.DecimalField(initial="0.00", label=u'Valor', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))


class CertificacionTramiteForm(forms.Form):
    certificacion = forms.IntegerField(required=False,
                                       widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}),
                                       label=u'Certificacion')
    total = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))


class RetencionesDocumentoTramitePagoForm(forms.Form):
    codigo = forms.IntegerField(required=False, widget=forms.TextInput(attrs={'select2search': 'true'}),
                                label=u'Código Retención')
    valorretenido = forms.DecimalField(initial="0.00", label=u'Valor', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))

    def agregar(self):
        deshabilitar_campo(self, 'valorretenido')


class HistorialJornadaTrabajadorForm(forms.Form):
    jornada = forms.ModelChoiceField(label=u'Jornada', required=False, queryset=Jornada.objects.all(),
                                     widget=forms.Select(attrs={'class': 'imp-50'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    actual = forms.BooleanField(label=u'Actual', initial=True, required=False)
    fechafin = forms.DateField(label=u"Fecha fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    archivo = ExtFileField(label=u'Archivo autorización', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato PDF o DOC',
                               ext_whitelist=(".pdf", ".doc", ".docx", ), max_upload_size=10485760)

    def cerrar(self):
        deshabilitar_campo(self, 'jornada')
        deshabilitar_campo(self, 'fechainicio')
        deshabilitar_campo(self, 'actual')

    def editar(self):
        deshabilitar_campo(self, 'jornada')

    def ocultarcampos_archivo(self):
        del self.fields['archivo']

class JornadaLaboralForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=False, widget=forms.TextInput())

    def editar(self):
        deshabilitar_campo(self, 'nombre')

class CambiarMarcadaForm(forms.Form):
    hora = forms.TimeField(label=u'Hora', initial=str(datetime.now().time()), required=False,
                                  input_formats=["%H:%M"], widget=DateTimeInput(format='%H:%M',
                                                                                attrs={'class': 'selectorhora',
                                                                                       'formwidth': '50%'}))
class JustificarMarcadaForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(),
                                 input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    archivo = ExtFileField(label=u'Archivo justificación', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato PDF o DOC',
                           ext_whitelist=(".pdf", ".doc", ".docx",), max_upload_size=10485760)
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '4', 'class': 'normal-input'}))

    def bloqueofecha_observación(self):
        campo_solo_lectura(self, 'fecha')
        campo_solo_lectura(self, 'observacion')

    def ocultarcampos_archivo(self):
        del self.fields['archivo']

class PartidaDetallesForm(forms.Form):
    codigo = forms.CharField(label=u'Codigo', max_length=20, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-codigo'}))
    descripcion = forms.CharField(label=u'Descripcion', required=False, widget=forms.Textarea({'rows': '2'}))

    def editar(self):
        deshabilitar_campo(self, 'codigo')


class ComrpomisoPartidaForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    descripcion = forms.CharField(label=u'Descripcion', required=False, widget=forms.Textarea({'rows': '2'}))
    claseregistro = forms.ModelChoiceField(queryset=CompromisoClaseRegistro.objects.all().order_by('id'),
                                           required=False, widget=forms.Select(attrs={'formwidth': '33%'}),
                                           label=u'Clase Registro')
    clasemodificacion = forms.ModelChoiceField(queryset=CompromisoClaseModificacion.objects.all().order_by('id'),
                                               required=False, widget=forms.Select(attrs={'formwidth': '33%'}),
                                               label=u'Clase Modificación')
    clasegasto = forms.ModelChoiceField(queryset=CompromisoClaseGasto.objects.all().order_by('id'), required=False,
                                        widget=forms.Select(attrs={'formwidth': '33%'}), label=u'Clase Gasto')
    tipodoc = forms.ModelChoiceField(queryset=PresupuestoTipoDocumentoRespaldo.objects.all().order_by('id'),
                                     required=False, widget=forms.Select(attrs={'formwidth': '50%'}),
                                     label=u'Tipo Documento')
    clasedoc = forms.ModelChoiceField(queryset=PresupuestoClaseDocumentoRespaldo.objects.all().order_by('id'),
                                      required=False, widget=forms.Select(attrs={'formwidth': '50%'}),
                                      label=u'Clase Documento')

    def editar(self, cert):
        if not cert.local:
            deshabilitar_campo(self, 'fecha')
            deshabilitar_campo(self, 'descripcion')


class DetalleCertificacionForm(forms.Form):
    partidassaldo = forms.IntegerField(initial=0, required=False, label=u'Partida',
                                       widget=forms.TextInput(attrs={'select2search': 'true', 'formdwidth': '50%'}))
    monto = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))

    def adicionar(self, anio):
        self.fields['partidassaldo'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio)

    def adicionar_com(self, anio, cert):
        self.fields['partidassaldo'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio,
                                                                             detallecertificacion__certificacion=cert)


class DetalleCompromisoForm(forms.Form):
    partidassaldo = forms.IntegerField(initial=0, required=False, label=u'Partida',
                                       widget=forms.TextInput(attrs={'select2search': 'true', 'formdwidth': '50%'}))
    monto = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))

    def adicionar(self, anio):
        self.fields['partidassaldo'].queryset = DetalleCertificacion.objects.filter(
            partidassaldo__anioejercicio__anioejercicio=anio)

    def adicionar_com(self, anio, cert):
        self.fields['partidassaldo'].queryset = DetalleCertificacion.objects.filter(
            partidassaldo__anioejercicio__anioejercicio=anio, certificacion=cert)


class ComrpomisoCertificacionForm(forms.Form):
    certificacion = forms.ModelChoiceField(queryset=CertificacionPartida.objects.filter(estado=1).order_by('id'),
                                           required=False, widget=forms.Select(attrs={'formwidth': '100%'}),
                                           label=u'Certificación')
    descripcion = forms.CharField(label=u'Descripcion', required=False, widget=forms.Textarea({'rows': '2'}))
    claseregistro = forms.ModelChoiceField(queryset=CompromisoClaseRegistro.objects.all().order_by('id'),
                                           required=False, widget=forms.Select(attrs={'formwidth': '75%'}),
                                           label=u'Clase Registro')
    clasemodificacion = forms.ModelChoiceField(queryset=CompromisoClaseModificacion.objects.all().order_by('id'),
                                               required=False, widget=forms.Select(attrs={'formwidth': '75%'}),
                                               label=u'Clase Modificación')
    clasegasto = forms.ModelChoiceField(queryset=CompromisoClaseGasto.objects.all().order_by('id'), required=False,
                                        widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Clase Gasto')
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    nitnombre = forms.IntegerField(initial=0, required=False, label=u'Proveedor',
                                   widget=forms.TextInput(attrs={'select2search': 'true', 'formdwidth': '50%'}))

    # monto = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))

    def adicionar(self, anio, certificacion):
        if certificacion:
            self.fields['certificacion'].queryset = CertificacionPartida.objects.filter(id=certificacion.id)
        else:
            self.fields['certificacion'].queryset = CertificacionPartida.objects.filter(
                anioejercicio__anioejercicio=anio, saldo__gt=0)

    def editar(self, proveedor):
        deshabilitar_campo(self, 'certificacion')
        self.fields['nitnombre'].widget.attrs['descripcion'] = proveedor
        self.fields['nitnombre'].initial = proveedor.id


class ReformaPartidaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripcion', required=False, widget=forms.Textarea({'rows': '2'}))
    claseregistro = forms.ModelChoiceField(queryset=ReformaClaseRegistro.objects.all().order_by('id'), required=False,
                                           widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Clase Registro')
    fecimputacion = forms.DateField(label=u"Fecha imput.", required=False, initial=datetime.now().date(),
                                    input_formats=['%d-%m-%Y'],
                                    widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    disposicionlegal = forms.CharField(label=u'Disposicion legal', required=False, widget=forms.Textarea({'rows': '2'}))
    fecdisposicion = forms.DateField(label=u"Fecha Disposición", required=False, initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'],
                                     widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))

    def editar(self, cert):
        if not cert.local:
            deshabilitar_campo(self, 'fecimputacion')
            deshabilitar_campo(self, 'fecdisposicion')
            deshabilitar_campo(self, 'descripcion')


class DetalleReformaPartidaForm(forms.Form):
    partidassaldo = forms.IntegerField(initial=0, required=False, label=u'Partida',
                                       widget=forms.TextInput(attrs={'select2search': 'true'}))
    monto = forms.DecimalField(initial="0.00", label=u'Monto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))

    def adicionar(self, anio):
        self.fields['partidassaldo'].queryset = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio)


class PeriodoGastosForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Título', required=True, widget=forms.TextInput({'placeholder': 'Describa el periodo de gastos  a crear'}))
    anio = forms.IntegerField(initial=0, required=True, label=u'Año',
                              widget=forms.TextInput({'col': '4'}))
    fechadesde = forms.DateField(label=u"Fecha Desde.", required=True, initial=datetime.now().date(),
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '4'}))
    fechahasta = forms.DateField(label=u"Fecha Hasta", required=True, initial=datetime.now().date(),
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '4'}))
    formato = ExtFileField(label=u'Formato', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato PDF, XLS, XLSX',
                           widget=forms.FileInput(attrs={'col': '12','accept': '.xlsx, .xls','class':' w-100 '}),
                           ext_whitelist=(".xls", ".xlsx",), max_upload_size=10485760)
    mostrar = forms.BooleanField(initial=False, label=u'Mostrar?', required=False,
                                 widget=forms.CheckboxInput(attrs={'data-switchery':True,'col':'12',}))

    def editar(self):
        deshabilitar_campo(self, 'descripcion')
        deshabilitar_campo(self, 'anio')

class PoblacionForm(FormModeloBase):
    archivo = ExtFileField(label=u'Archivo', required=True,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato xlsx',
                           ext_whitelist=(".xlsx",), max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'accept': '.xlsx, .xls'}))

class GastosPersonalesForm(FormModeloBase):
    persona = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True,), required=True, label=u'Funcionario de gasto', widget=forms.Select(attrs={'col':'12'}))
    mes = forms.ChoiceField(choices=MESES_CHOICES, label=u'Mes de gasto', required=True, widget=forms.Select(attrs={'col':'12'}))
    archivo = ExtFileField(label=u'Documento de gastos personales firmado',
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato xlsx',
                           ext_whitelist=(".pdf",), max_upload_size=4194304,
                           required=False, widget=forms.FileInput(attrs={'accept': '.pdf, .PDF'}))

    def clean(self):
        cleaned_data=super().clean()
        persona = cleaned_data.get('persona')
        id = 0
        if hasattr(self.instancia, 'periodogastospersonales'):
            id = getattr(self.instancia, 'id', 0)
            idperiodo = getattr(self.instancia, 'periodogastospersonales_id', 0)
        else:
            idperiodo = getattr(self.instancia, 'id', 0)
        gasto = GastosPersonales.objects.filter(status=True, persona=persona, periodogastospersonales_id=idperiodo).exclude(id=id)
        if gasto.exists():
            self.add_error('persona', 'Registro que intenta guardar ya existe.')
        return cleaned_data

class DocumentosComprobanteRecaudacionForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    descripcion = forms.CharField(label=u'Descripcion', required=False, widget=forms.Textarea({'rows': '2'}))


class ComprobanteEgresoForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    tramite = forms.ModelChoiceField(queryset=TramitePago.objects.all(), required=False,
                                     widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Tramite')
    beneficiario = forms.ModelChoiceField(queryset=BeneficiariTramitePago.objects.all(), required=False,
                                          widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Beneficiario')
    identificacion = forms.CharField(label=u"Identificación", required=False, max_length=300)
    valordocumentos = forms.DecimalField(initial="0.00", label=u'Valor Documentos', required=False,
                                         widget=forms.TextInput(
                                             attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    totalretenidofuente = forms.DecimalField(initial="0.00", label=u'Total Reten. Fuente', required=False,
                                             widget=forms.TextInput(
                                                 attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    totalretenidoiva = forms.DecimalField(initial="0.00", label=u'Total Reten. Iva', required=False,
                                          widget=forms.TextInput(
                                              attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    totalotros = forms.DecimalField(initial="0.00", label=u'Total Otros', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    totalanticipos = forms.DecimalField(initial="0.00", label=u'Total Anticipos', required=False,
                                        widget=forms.TextInput(
                                            attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    totalmultas = forms.DecimalField(initial="0.00", label=u'Total Multas', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px'}))
    totalpagar = forms.DecimalField(initial="0.00", label=u'Valor Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))
    concepto = forms.CharField(label=u'Concepto', required=False, widget=forms.Textarea({'rows': '2'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))

    def adicionar(self, t):
        self.fields['beneficiario'].queryset = t.beneficiaritramitepago_set.filter(comprobante__isnull=True)
        deshabilitar_campo(self, 'tramite')
        deshabilitar_campo(self, 'valordocumentos')
        deshabilitar_campo(self, 'totalretenidofuente')
        deshabilitar_campo(self, 'totalretenidoiva')

    def editar(self):
        deshabilitar_campo(self, 'tramite')
        deshabilitar_campo(self, 'identificacion')
        deshabilitar_campo(self, 'beneficiario')
        deshabilitar_campo(self, 'valordocumentos')
        deshabilitar_campo(self, 'totalretenidofuente')
        deshabilitar_campo(self, 'totalretenidoiva')


class ConciliacionForm(forms.Form):
    tipomovimiento = forms.ModelChoiceField(queryset=TipoMovimientoConciliacion.objects.all(), required=False,
                                            widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Tipo')
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    referencia = forms.CharField(label=u"Referencia", max_length=50, required=False,
                                 widget=forms.TextInput(attrs={'formwidth': '50%'}))
    cuentabanco = forms.ModelChoiceField(label=u"Cuenta", required=False, queryset=CuentaBanco.objects.all(),
                                         widget=forms.Select())
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))

    def adicionar(self, cuenta):
        self.fields['cuentabanco'].queryset = CuentaBanco.objects.all().exclude(id=cuenta.id)

    def editar(self):
        deshabilitar_campo(self, 'tipomovimiento')
        deshabilitar_campo(self, 'fecha')


class GarantiasForm(forms.Form):
    numero = forms.CharField(label=u"Num. Contrato", max_length=50, required=False,
                             widget=forms.TextInput(attrs={'formwidth': '50%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    contratista = forms.IntegerField(initial=0, required=False, label=u'Contratista',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    concepto = forms.CharField(label=u"Concepto", max_length=300, required=False, widget=forms.TextInput(attrs={}))
    proceso = forms.CharField(label=u"Proceso", max_length=300, required=False, widget=forms.TextInput(attrs={}))
    aseguradora = forms.ModelChoiceField(queryset=Aseguradora.objects.all(), required=False,
                                         widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Aseguradora')
    monto = forms.DecimalField(initial="0.00", label=u'Monto Contrato', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))

    def editar(self, garantia):
        self.fields['contratista'].widget.attrs['descripcion'] = garantia.contratista.nombre_completo()
        self.fields['contratista'].initial = garantia.contratista.id
        if garantia.tiene_ramo():
            deshabilitar_campo(self, 'monto')
            deshabilitar_campo(self, 'fechainicio')
            deshabilitar_campo(self, 'fechafin')


class GarantiasComplementariasForm(forms.Form):
    numero = forms.CharField(label=u"Num. Contrato", max_length=50, required=False,
                             widget=forms.TextInput(attrs={'formwidth': '50%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    concepto = forms.CharField(label=u"Concepto", max_length=300, required=False, widget=forms.TextInput(attrs={}))
    monto = forms.DecimalField(initial="0.00", label=u'Monto Contrato', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))

    def editar(self, garantia):
        if garantia.tiene_ramo():
            deshabilitar_campo(self, 'monto')
            deshabilitar_campo(self, 'fechainicio')
            deshabilitar_campo(self, 'fechafin')


class RamoForm(forms.Form):
    tipo = forms.ModelChoiceField(queryset=TipoRamo.objects.all(), required=False,
                                  widget=forms.Select(attrs={'formwidth': '75%'}), label=u'Tipo')
    numero = forms.CharField(label=u"Num. Poliza", max_length=50, required=False,
                             widget=forms.TextInput(attrs={'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    porcentaje = forms.DecimalField(initial="0.00", label=u'Porcentaje', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))
    monto = forms.DecimalField(initial="0.00", label=u'Monto Asegurado', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))


class ExtenderGrantiaForm(forms.Form):
    motivo = forms.CharField(label=u"Motivo", max_length=300, required=False, widget=forms.TextInput(attrs={}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))


class PodEvaluacionDetCalificaForm(forms.Form):
    estado = forms.ChoiceField(choices=ESTADO_POD, required=False, label=u'Estado', widget=forms.Select())
    observacionaprobador = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '6'}))

    def aprobar_choise(self):
        self.fields['estado'].choices = ((3, 'ACEPTADO'), (4, 'RECHAZADO'),)


class MetasUnidadArchivoForm(forms.Form):
    nota = forms.DecimalField(initial="0.00", label=u'Nota', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))
    observacion = forms.CharField(required=False, max_length=500, label=u'Observación',
                                  widget=forms.Textarea({'rows': '3'}))
    archivo = ExtFileField(label=u'Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato PDF, XLS, XLSX',
                           ext_whitelist=(".pdf", ".xls", ".xlsx",), max_upload_size=10485760)

    def proyectado(self):
        deshabilitar_campo(self, 'nota')


class PodEvaluacionDetArchivoForm(forms.Form):
    observacionenvia = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '4'}))
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato PDF',
                           ext_whitelist=(".pdf",), max_upload_size=10485760)

    def editar(self):
        deshabilitar_campo(self, 'observacionenvia')


class PodProductoCompetenciaForm(forms.Form):
    productos = forms.IntegerField(initial=0, required=False, label=u'Productos',
                                   widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '80%'}))
    competenciastec = forms.IntegerField(initial=0, required=False, label=u'Competencias Tecnicas',
                                         widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '80%'}))
    competenciascon = forms.IntegerField(initial=0, required=False, label=u'Competencias Conductuales',
                                         widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '80%'}))


class PodEvaluacionDetArchivoMetaForm(forms.Form):
    observacionenvia = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '4'}))
    archivo = ExtFileField(label=u'Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato xls, xlsx, pdf',
                           ext_whitelist=(".xls", ".xlsx", ".pdf",), max_upload_size=10485760)

    def editar(self):
        deshabilitar_campo(self, 'observacionenvia')


class PodEvaluacionDetForm(forms.Form):
    evaluado = forms.IntegerField(initial=0, required=False, label=u'Servidor',
                                  widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))


class CaracteristicasForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'rows': '2'}))
    item = forms.ModelChoiceField(Partida.objects.filter(status=True), required=False, label=u'Item',
                                  widget=forms.Select(attrs={'formwidth': '100%'}))


class PeriodoPacForm(forms.Form):
    anio = forms.IntegerField(label=u"Año", initial=datetime.now().date().year, required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'rows': '2'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    permisoinicio = forms.DateField(label=u"Fecha inicio ingreso", required=False, initial=datetime.now().date(),
                                    input_formats=['%d-%m-%Y'],
                                    widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    permisofin = forms.DateField(label=u"Fecha fin ingreso", required=False, initial=datetime.now().date(),
                                 input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))

    def editar(self):
        deshabilitar_campo(self, 'anio')


class TopePeriodoPacForm(forms.Form):
    departamento = forms.ModelChoiceField(Departamento.objects.filter(status=True), required=False,
                                          label=u'Departamento', widget=forms.Select(attrs={'formwidth': '100%'}))
    valor = forms.DecimalField(initial="0.00", label=u'Valor Tope', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '300px', 'separator': 'true'}))
    estadotope = forms.BooleanField(label=u'Estado', required=False,
                                    widget=CheckboxInput({'class': 'imp-25', 'formwidth': '50px'}))

    def editar(self):
        deshabilitar_campo(self, 'departamento')

    def addtopeperiodo(self, periodopac):
        self.fields['departamento'].queryset = Departamento.objects.filter(status=True,
                                                                           integrantes__isnull=False).distinct()


class PacForm(forms.Form):
    caracteristicas = forms.IntegerField(initial=0, required=False, label=u'Productos',
                                         widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    cantidadenero = forms.IntegerField(label=u"Cantidad Enero", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadfebrero = forms.IntegerField(label=u"Cantidad Febrero", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadmarzo = forms.IntegerField(label=u"Cantidad Marzo", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadabril = forms.IntegerField(label=u"Cantidad Abril", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadmayo = forms.IntegerField(label=u"Cantidad Mayo", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadjunio = forms.IntegerField(label=u"Cantidad Junio", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadjulio = forms.IntegerField(label=u"Cantidad Julio", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadagosto = forms.IntegerField(label=u"Cantidad Agosto", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadseptiembre = forms.IntegerField(label=u"Cantidad Septiembre", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadoctubre = forms.IntegerField(label=u"Cantidad Octubre", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidadnoviembre = forms.IntegerField(label=u"Cantidad Noviembre", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    cantidaddiciembre = forms.IntegerField(label=u"Cantidad Diciembre", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '25%'}))
    unidadmedida = forms.ModelChoiceField(UnidadMedida.objects.filter(status=True), required=False,
                                          label=u'Unidad Medida', widget=forms.Select(attrs={'formwidth': '40%'}))
    costounitario = forms.DecimalField(initial="0.00", label=u'Costo Unitario', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '40%'}))
    subtotal = forms.DecimalField(initial="0.00", label=u'SubTotal', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '30%', 'separator': 'true'}))
    iva = forms.DecimalField(initial="0.00", label=u'IVA', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '30%', 'separator': 'true'}))
    total = forms.DecimalField(initial="0.00", label=u'Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '30%', 'separator': 'true'}))
    # fechaejecucion = forms.DateField(label=u"Fecha Ejecución", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))


class PacReformaForm(forms.Form):
    objetivooperativo = forms.ModelChoiceField(ObjetivoOperativo.objects.filter(status=True), required=False,
                                               label=u'Objetivo Operativo',
                                               widget=forms.Select(attrs={'formwidth': '100%'}))
    indicadorpoa = forms.ModelChoiceField(IndicadorPoa.objects.filter(status=True), required=False,
                                          label=u'Indicador Poa', widget=forms.Select(attrs={'formwidth': '100%'}))
    acciondocumento = forms.ModelChoiceField(AccionDocumento.objects.filter(status=True), required=False,
                                             label=u'Actividad/Proyecto',
                                             widget=forms.Select(attrs={'formwidth': '100%'}))
    caracteristicas = forms.IntegerField(initial=0, required=False, label=u'Caracteristicas',
                                         widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    cantidad = forms.IntegerField(label=u"Cantidad", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    unidadmedida = forms.ModelChoiceField(UnidadMedida.objects.filter(status=True), required=False,
                                          label=u'Unidad Medida', widget=forms.Select(attrs={'formwidth': '50%'}))
    costounitario = forms.DecimalField(initial="0.00", label=u'Costo Unitario', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%', 'separator': 'true'}))
    total = forms.DecimalField(initial="0.00", label=u'Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%', 'separator': 'true'}))
    fechaejecucion = forms.DateField(label=u"Fecha Ejecución", required=False, initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '50%'}))
    programa = forms.ModelChoiceField(PartidaPrograma.objects.filter(status=True), required=False, label=u'Programa',
                                      widget=forms.Select(attrs={'formwidth': '50%'}))
    actividad = forms.ModelChoiceField(PartidaActividad.objects.filter(status=True), required=False, label=u'Actividad',
                                       widget=forms.Select(attrs={'formwidth': '50%'}))
    fuente = forms.ModelChoiceField(PartidaFuente.objects.filter(status=True), required=False, label=u'Fuente',
                                    widget=forms.Select(attrs={'formwidth': '50%'}))

    def adicionar(self):
        self.fields['objetivooperativo'].queryset = ObjetivoOperativo.objects.filter(id=None, status=True)
        self.fields['indicadorpoa'].queryset = IndicadorPoa.objects.filter(id=None, status=True)
        self.fields['acciondocumento'].queryset = AccionDocumento.objects.filter(id=None, status=True)


class ReformaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'rows': '2'}))
    memorando = forms.CharField(label=u'Memorando', required=False, widget=forms.Textarea({'rows': '2'}))
    informe = forms.CharField(label=u'Informe', required=False, widget=forms.Textarea({'rows': '1'}))
    estadoreforma = forms.ChoiceField(choices=ESTADO_REFORMA, required=False, label=u'Estado Reforma',
                                      widget=forms.Select())
    departamento = forms.ModelChoiceField(Departamento.objects.filter(status=True), required=False,
                                          label=u'Departamento', widget=forms.Select(attrs={'formwidth': '100%'}))
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))

    def adicionar(self, departamentos):
        self.fields['departamento'].queryset = Departamento.objects.filter(id__in=departamentos, status=True)


class EjecucionPacForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    cantidad = forms.IntegerField(label=u"Cantidad", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    costounitario = forms.DecimalField(initial="0.00", label=u'Costo Unitario', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%', 'separator': 'true'}))
    total = forms.DecimalField(initial="0.00", label=u'Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%', 'separator': 'true'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato PDF',
                           ext_whitelist=(".pdf",), max_upload_size=10485760)


class SuministroForm(forms.Form):
    proveedor = forms.ModelChoiceField(Proveedor.objects.all(), label=u'Proveedor',
                                       widget=forms.Select(attrs={'formwidth': '50%'}))
    tipodocumento = forms.ModelChoiceField(TipoDocumento.objects.all(), label=u'Tipo Documento',
                                           widget=forms.Select(attrs={'formwidth': '500px', 'separator': 'true'}))
    numerodocumento = forms.CharField(label=u'Número Documento',
                                      widget=forms.TextInput(attrs={'class': 'imp-comprobantes', 'formwidth': '300px'}))
    fechadocumento = forms.DateField(label=u"Fecha documento", initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '200px'}))
    ordencompra = forms.CharField(label=u'Orden compra', required=False,
                                  widget=forms.TextInput(attrs={'formwidth': '400px', 'separator': 'true'}))
    solicitudcompra = forms.CharField(label=u'Solicitud compra', required=False,
                                      widget=forms.TextInput(attrs={'formwidth': '400px'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.TextInput(attrs={'formwidth': '100%'}))


class DetalleSuministroProductoForm(forms.Form):
    codigoprod = forms.CharField(max_length=30, label=u'Código',
                                 widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    tipoprod = forms.CharField(max_length=100, label=u'Categoría', widget=forms.TextInput())
    descripcionprod = forms.CharField(label=u'Descripción', widget=forms.Textarea({'rows': '2'}))
    unidadmedidaprod = forms.CharField(max_length=30, label=u'UM',
                                       widget=forms.TextInput(attrs={'class': 'imp-codigo'}))
    cantidadprod = forms.DecimalField(initial='0.00', label=u'Cantidad',
                                      widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    estado = forms.ModelChoiceField(EstadoProducto.objects.all(), label=u"Estado",
                                    widget=forms.Select(attrs={'formwidth': '40%'}))


class SuministroSalidaProductoForm(forms.Form):
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), label=u'Departamento',
        widget=forms.Select(attrs={'formwidth': '600px'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), label=u'Responsable',
                                         widget=forms.Select(attrs={'formwidth': '400px', 'labelwidth': '100px'}))
    descripcion = forms.CharField(label=u'Motivo Salida', widget=forms.Textarea(attrs={'rows': '1'}), required=False)
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea(attrs={'rows': '1'}), required=False)

    def adicionar(self):
        self.fields['responsable'].queryset = Persona.objects.filter(administrativo__isnull=False).filter(id=None)


class SuministroDetalleSalidaProductoForm(forms.Form):
    codigoprod = forms.CharField(max_length=30, label=u'Código',
                                 widget=forms.TextInput(attrs={'class': 'imp-50', 'codigo': ''}))
    descripcionprod = forms.CharField(label=u'Descripción', widget=forms.Textarea({'class': 'imp-100', 'rows': '2'}))
    cantidadprod = forms.DecimalField(initial="0.00", label=u'Cantidad',
                                      widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': "4"}))

    def adicionar(self):
        deshabilitar_campo(self, 'descripcionprod')

    fechaejecucion = forms.DateField(label=u"Fecha Ejecución", required=False, initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'],
                                     widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))


class AccionPersonalForm(forms.Form):
    persona = forms.IntegerField(initial=0, required=False, label=u'Persona',
                                 widget=forms.TextInput(attrs={'select2search': 'true'}))
    # subroganterector = forms.BooleanField(required=False, label=u'Delegado', widget=forms.CheckboxInput(attrs={'formwidth': '200px', 'separator': 'true'}))
    # personarector = forms.IntegerField(initial=0, required=False, label=u'Rector', widget=forms.TextInput(attrs={'formwidth': '450px', 'labelwidth': '100', 'select2search': 'true'}))
    subroganterrhh = forms.BooleanField(required=False, label=u'Director Subrogante',
                                        widget=forms.CheckboxInput(attrs={'formwidth': '200px', 'separator': 'true'}))
    personarrhh = forms.IntegerField(initial=0, required=False, label=u'Director Talento Humano',
                                     widget=forms.TextInput(
                                         attrs={'formwidth': '450px', 'labelwidth': '100px', 'select2search': 'true'}))
    personaregistrocontrol = forms.IntegerField(initial=0, required=False, label=u'Responsable Registro',
                                                widget=forms.TextInput(attrs={'select2search': 'true'}))
    numero = forms.IntegerField(label=u'Numero', widget=forms.TextInput(
        attrs={'formwidth': '30%', 'class': 'imp-numbersmall', 'decimal': '0'}))
    fechaaprobacion = forms.DateField(label=u"Fecha de aprobación", input_formats=['%d-%m-%Y'],
                                      widget=DateTimeInput(format='%d-%m-%Y',
                                                           attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    fechaelaboracion = forms.DateField(label=u"Fecha de elaboración", input_formats=['%d-%m-%Y'],
                                       widget=DateTimeInput(format='%d-%m-%Y',
                                                            attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    anio = forms.IntegerField(label=u'Año', widget=forms.TextInput(
        attrs={'formwidth': '30%', 'class': 'imp-numbersmall', 'decimal': '0'}))
    fechadesde = forms.DateField(label=u"Fecha rige desde", input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y',
                                                      attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    fechahasta = forms.DateField(label=u"Fecha rige hasta", input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y',
                                                      attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    abreviatura = forms.CharField(label=u"Abreviatura", max_length=100,
                                  widget=forms.TextInput(attrs={'class': 'imp-100'}))
    tipo = forms.ModelChoiceField(label=u"Tipo", queryset=TipoAccionPersonal.objects.all(), required=False,
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    documento = forms.CharField(label=u"Documento", max_length=100, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    explicacion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3'}), required=False, label=u"Explicación")
    regimenlaboral = forms.ModelChoiceField(label=u"Regimen Laboral", queryset=RegimenLaboral.objects.all(),
                                            required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    motivo = forms.ModelChoiceField(label=u"Motivo", queryset=MotivoAccionPersonalDetalle.objects.all(), required=False,
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    numeroactafinal = forms.IntegerField(initial=0, label=u'Numero Acta Final ', required=False, widget=forms.TextInput(
        attrs={'formwidth': '30%', 'class': 'imp-numbersmall', 'decimal': '0'}))
    fechaactafinal = forms.DateField(label=u"Fecha Acta Final", required=False, input_formats=['%d-%m-%Y'],
                                     widget=DateTimeInput(format='%d-%m-%Y',
                                                          attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    departamentoactual = forms.ModelChoiceField(Departamento.objects.all(), label=u'Departamento actual',
                                                widget=forms.Select(attrs={'formwidth': '400px', 'separator': 'true'}),
                                                required=False)
    departamento = forms.ModelChoiceField(Departamento.objects.all(), label=u'Departamento propuesto',
                                          widget=forms.Select(attrs={'formwidth': '400px'}), required=False)
    denominacionpuestoactual = forms.IntegerField(initial=0, required=False, label=u'Denominación puesto actual',
                                                  widget=forms.TextInput(
                                                      attrs={'select2search': 'true', 'formwidth': '400px',
                                                             'separator': 'true'}))
    denominacionpuesto = forms.IntegerField(initial=0, required=False, label=u'Denominación puesto propuesto',
                                            widget=forms.TextInput(
                                                attrs={'select2search': 'true', 'formwidth': '400px', }))
    escalaocupacionalactual = forms.ModelChoiceField(label=u"Escala ocupacional actual",
                                                     queryset=EscalaOcupacional.objects.all(), required=False,
                                                     widget=forms.Select(
                                                         attrs={'formwidth': '400px', 'separator': 'true'}))
    escalaocupacional = forms.CharField(initial='', max_length=50, label=u'Escala ocupacional propuesto',
                                        widget=forms.TextInput(attrs={'formwidth': '400px'}), required=False)
    tipogradoactual = forms.ChoiceField(choices=TIPO_GRADO, required=False, label=u'Grado ocupacional actual',
                                        widget=forms.Select(attrs={'formwidth': '400px', 'separator': 'true'}))
    tipogrado = forms.CharField(max_length=50, label=u'Grado ocupacional propuesto',
                                widget=forms.TextInput(attrs={'formwidth': '400px'}), required=False)
    lugartrabajoactual = forms.CharField(initial='MILAGRO', max_length=50, label=u'Lugar trabajo actual',
                                         widget=forms.TextInput(attrs={'formwidth': '400px', 'separator': 'true'}),
                                         required=False)
    lugartrabajo = forms.CharField(initial='MILAGRO', max_length=50, label=u'Lugar trabajo propuesto',
                                   widget=forms.TextInput(attrs={'formwidth': '400px'}), required=False)
    rmuactual = forms.FloatField(initial='', label=u'RMU actual', required=False, widget=forms.TextInput(
        attrs={'formwidth': '400px', 'class': 'imp-numbersmall', 'decimal': '2', 'separator': 'true'}))
    rmu = forms.FloatField(initial='', label=u'RMU propuesto', required=False, widget=forms.TextInput(
        attrs={'formwidth': '400px', 'class': 'imp-numbersmall', 'decimal': '2'}))
    partidapresupuestariaactual = forms.CharField(max_length=150, label=u'Partida presupuestaria actual',
                                                  widget=forms.TextInput(
                                                      attrs={'formwidth': '400px', 'separator': 'true'}),
                                                  required=False)
    partidapresupuestaria = forms.CharField(max_length=150, label=u'Partida presupuestaria propuesto',
                                            widget=forms.TextInput(attrs={'formwidth': '400px'}), required=False)
    cesafunciones = forms.BooleanField(required=False, label=u'Aplica Cesar Funciones',
                                       widget=forms.CheckboxInput(attrs={'separator': 'true'}))
    numerocaucion = forms.IntegerField(initial=0, label=u'Numero caución ', required=False, widget=forms.TextInput(
        attrs={'formwidth': '30%', 'class': 'imp-numbersmall', 'decimal': '0'}))
    fechacaucion = forms.DateField(label=u"Fecha caución", required=False, input_formats=['%d-%m-%Y'],
                                   widget=DateTimeInput(format='%d-%m-%Y',
                                                        attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    numeroaccion = forms.IntegerField(label=u'Numero acción registro', required=False, widget=forms.TextInput(
        attrs={'formwidth': '30%', 'class': 'imp-numbersmall', 'decimal': '0', 'separator': 'true'}))
    fecharegistroaccion = forms.DateField(label=u"Fecha registro acción", required=False, input_formats=['%d-%m-%Y'],
                                          widget=DateTimeInput(format='%d-%m-%Y',
                                                               attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    personareemplaza = forms.IntegerField(initial='', required=False, label=u'Reemplaza a', widget=forms.TextInput(
        attrs={'formwidth': '400px', 'select2search': 'true', 'separator': 'true'}))
    denominacionpuestoreemplazo = forms.IntegerField(initial='', required=False, label=u'Puesto reemplazo',
                                                     widget=forms.TextInput(
                                                         attrs={'formwidth': '400px', 'select2search': 'true'}))
    cesofunciones = forms.CharField(label=u"Descripcion Ceso de función", required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-100'}))
    colegioprofesionales = forms.CharField(label=u"Afiliación colegio de profesionales", required=False,
                                           widget=forms.TextInput(attrs={'class': 'imp-100'}))


class AccionPersonal2Form(forms.Form):
    # persona = forms.IntegerField(initial=0, required=False, label=u'Persona', widget=forms.TextInput(attrs={'select2search': 'true'}))
    subroganterrhh = forms.BooleanField(required=False, label=u'Director Subrogante',
                                        widget=forms.CheckboxInput(attrs={'formwidth': '200px'}))
    personarrhh = forms.IntegerField(initial=0, required=False, label=u'Director Talento Humano',
                                     widget=forms.TextInput(
                                         attrs={'formwidth': '450px', 'labelwidth': '100px', 'select2search': 'true'}))
    personaregistrocontrol = forms.IntegerField(initial=0, required=False, label=u'Responsable Registro',
                                                widget=forms.TextInput(attrs={'select2search': 'true'}))
    explicacion = forms.CharField(widget=forms.Textarea(attrs={'rows': '15'}), required=False, label=u"Explicación")
    partidapresupuestariaactual = forms.CharField(max_length=150, label=u'Partida presupuestaria actual',
                                                  widget=forms.TextInput(attrs={'formwidth': '100%'}), required=False)


class AccionPersonalArchivoForm(FormModeloBase):
    archivo = ExtFileField(label=u'Solicitud', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf',
                           ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput())


class MotivoAccionPersonalForm(FormModeloBase):
    nombre = forms.CharField(required=True, label=u"Nombre", max_length=1000,
                             widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    abreviatura = forms.CharField(required=True, label=u"Abreviatura", max_length=20,
                                    widget=forms.TextInput(attrs={'col': '4','class': 'imp-20', 'formwidth': '100%'}))
    orden = forms.IntegerField(label="Orden", min_value=1, required=True,
                               widget=forms.NumberInput(attrs={'col': '4', 'icon': 'bi bi-sort-numeric-up'}))
    activo = forms.BooleanField(label="¿Activo?", required=False, widget=forms.CheckboxInput(
        attrs={'col': '4', 'data-switchery': True}))

    # baselegal = forms.CharField(label=u'Base Legal', widget=forms.Textarea(attrs={'rows': '4'}), required=False, max_length=800)


class MotivoAccionPersonalDetalleForm(forms.Form):
    baselegal = forms.ModelChoiceField(BaseLegalAccionPersonal.objects.filter(status=True), required=False,
                                       label=u'Base Legal', widget=forms.Select(attrs={'formwidth': '100%'}))


class BaseLegalAccionPersonalForm(forms.Form):
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '800'}), required=False,
                                  label=u"Descripción")


class DistributivoPersonaForm(forms.Form):
    persona = forms.ModelChoiceField(label=u'Persona', queryset=Persona.objects.select_related().filter(status=True, ), required=True, widget=forms.Select(attrs={'api':'true'}))
    regimenlaboral = forms.ModelChoiceField(RegimenLaboral.objects.filter(status=True), required=False,
                                            label=u'Regimen Laboral', widget=forms.Select(attrs={'formwidth': '100%'}))
    nivelocupacional = forms.ModelChoiceField(NivelOcupacional.objects.filter(status=True), required=False,
                                              label=u'Nivel Ocupacional',
                                              widget=forms.Select(attrs={'formwidth': '100%'}))
    modalidadlaboral = forms.ModelChoiceField(ModalidadLaboral.objects.filter(status=True), required=False,
                                              label=u'Modalidad Laboral',
                                              widget=forms.Select(attrs={'formwidth': '100%'}))
    partidaindividual = forms.IntegerField(label=u"Partida Individual", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    estadopuesto = forms.ModelChoiceField(EstadoPuesto.objects.filter(status=True), required=False,
                                          label=u'Estado Puesto', widget=forms.Select(attrs={'formwidth': '100%'}))
    grado = forms.IntegerField(label=u"Grado", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    rmuescala = forms.DecimalField(initial="0.00", label=u'RMU Escala', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%', 'separator': 'true'}))
    rmupuesto = forms.DecimalField(initial="0.00", label=u'RMU Puesto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%', 'separator': 'true'}))
    rmusobrevalorado = forms.DecimalField(initial="0.00", label=u'RMU Sobrevalorado', required=False,
                                          widget=forms.TextInput(
                                              attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%',
                                                     'separator': 'true'}))
    escalaocupacional = forms.ModelChoiceField(EscalaOcupacional.objects.filter(status=True), required=False,
                                               label=u'Escala Ocupacional',
                                               widget=forms.Select(attrs={'formwidth': '100%'}))
    rucpatronal = forms.CharField(label=u'RUC Patronal', widget=forms.Textarea(attrs={'rows': '1'}), required=False,
                                  max_length=20)
    codigosucursal = forms.CharField(label=u'Código Sucursal', widget=forms.Textarea(attrs={'rows': '1'}),
                                     required=False, max_length=20)
    tipoidentificacion = forms.ChoiceField(choices=TIPOS_IDENTIFICACION, required=False, label=u'Tipo Identificación',
                                           widget=forms.Select())
    # provincia = forms.ModelChoiceField(Provincia.objects.filter(status=True), required=False, label=u'Provincia', widget=forms.Select(attrs={'formwidth': '100%'}))
    # canton = forms.ModelChoiceField(Canton.objects.filter(status=True), required=False, label=u'Cantón', widget=forms.Select(attrs={'formwidth': '100%'}))
    denominacionpuesto = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True), required=False,
                                                label=u'Denominacion Puesto',
                                                widget=forms.Select(attrs={'formwidth': '100%'}))
    puestoadicinal = forms.ModelChoiceField(PuestoAdicional.objects.filter(status=True), required=False,
                                            label=u'Puesto Adicional', widget=forms.Select(attrs={'formwidth': '100%'}))
    unidadorganica = forms.ModelChoiceField(Departamento.objects.filter(status=True), required=False,
                                            label=u'Unidad Organica', widget=forms.Select(attrs={'formwidth': '100%'}))
    aporteindividual = forms.DecimalField(initial="0.00", max_digits=30, label=u'Aporte Individual', required=False,
                                          widget=forms.TextInput(
                                              attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%',
                                                     'separator': 'true'}))
    aportepatronal = forms.DecimalField(initial="0.00", max_digits=30, label=u'Aporte Patronal', required=False,
                                        widget=forms.TextInput(
                                            attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%',
                                                   'separator': 'true'}))
    estructuraprogramatica = forms.ModelChoiceField(EstructuraProgramatica.objects.filter(status=True), required=False,
                                                    label=u'Estructura Programática',
                                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    comisioservicios = forms.CharField(label=u'Comision Servicios', widget=forms.Textarea(attrs={'rows': '1'}),
                                       required=False, max_length=300)

    def edit(self, distributivopersona):
        deshabilitar_campo(self, 'persona')
        self.fields['persona'].widget.attrs['descripcion'] = distributivopersona.persona.nombre_completo()
        self.fields['persona'].initial = distributivopersona.persona.id


class ArchivoProcesoForm(forms.Form):
    tipo = forms.ChoiceField(choices=TIPO_TRAMITE, required=False, label=u'Tipo Trámite',
                             widget=forms.Select(attrs={'formwidth': '30%'}))
    egring = forms.CharField(required=False, label=u"Ingreso/Egreso", max_length=10,
                             widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '30%'}))
    fechadocumento = forms.DateField(label=u"Fecha Ingreso/Egreso", initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '20%'}),
                                     required=False)
    codigo = forms.CharField(label=u"N° Trámite", max_length=50,
                             widget=forms.TextInput(attrs={'class': 'imp-25', 'formwidth': '50%'}))
    externo = forms.IntegerField(initial=0, required=False, label=u'Depositante',
                                 widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '50%'}))
    tipopago = forms.ModelChoiceField(TipoPagoArchivo.objects.filter(status=True), required=False, label=u'Tipo pago',
                                      widget=forms.Select(attrs={'formwidth': '50%'}))
    subtipopago = forms.ModelChoiceField(SubTipoPagoArchivo.objects.filter(status=True), required=False,
                                         label=u'Sub tipo pago', widget=forms.Select(attrs={'formwidth': '50%'}))
    descripcion = forms.CharField(label=u"Descripción", max_length=250,
                                  widget=forms.TextInput(attrs={'class': 'imp-100'}))
    ubicacion = forms.ModelChoiceField(UbicacionProceso.objects.filter(status=True), initial=1, required=False,
                                       label=u'Ubicación', widget=forms.Select(attrs={'formwidth': '100%'}))
    nombrepercha = forms.CharField(required=False, label=u"Nombre percha", max_length=1000,
                                   widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '40%'}))
    nopercha = forms.ModelChoiceField(PerchaArchivo.objects.filter(status=True), required=False, label=u'No. Percha',
                                      widget=forms.Select(attrs={'formwidth': '30%'}))
    nofila = forms.ModelChoiceField(FilaArchivo.objects.filter(status=True), required=False, label=u'Fila',
                                    widget=forms.Select(attrs={'formwidth': '30%'}))
    # folder = forms.CharField(required=False, label=u"Folder", max_length=1000, widget=forms.TextInput(attrs={'class': 'imp-50', 'formwidth': '50%'}))
    proveedor = forms.ModelChoiceField(ProveedorArchivo.objects.filter(status=True), required=False, label=u'Proveedor',
                                       widget=forms.Select(attrs={'formwidth': '50%'}))
    observacion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                                  label=u"Observación")

    # archivo = ExtFileField(label=u'Documento PDF soporte', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf", ), max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))

    def add(self):
        self.fields['externo'].widget.attrs['descripcion'] = "Selecionar depositante"

    def edit(self, externo):
        self.fields['externo'].initial = externo.id if externo else 0
        self.fields['externo'].widget.attrs[
            'descripcion'] = externo.flexbox_repr() if externo else "Seleccionar depositante"
        self.fields['externo'].widget.attrs['value'] = externo.id if externo else 0


class TipoPagoArchivoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)


class PaginaArchivoForm(forms.Form):
    # observacion = forms.CharField(required=False, label=u"Nombre", max_length=1000, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '50%'}))
    # fechadocumento = forms.DateField(label=u"Fecha Documento", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '20%'}), required=False)
    archivo = ExtFileField(label=u'Documento PDF soporte', required=False,
                           help_text=u'Tamaño Maximo permitido 50Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=429916160, widget=FileInput({'accept': 'application/pdf'}))


class NumeroForm(forms.Form):
    numero = forms.IntegerField(label=u"Numero", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))


class ComprobanteRecaudacionFechaForm(forms.Form):
    numero = forms.IntegerField(label=u"Número Comprobante", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '30%'}))
    fecha = forms.DateField(label=u"Fecha Comprobante", required=False, input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    # fechabanco = forms.DateField(label=u"Fecha Banco", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'formwidth': '30%', 'class': 'selectorfecha'}))
    fechaesigef = forms.DateField(label=u"Fecha eSIGEF", required=False, input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'formwidth': '30%', 'class': 'selectorfecha'}))

    def bloqueanumero(self):
        campo_solo_lectura(self, 'numero')

    def bloqueafechaesigef(self):
        campo_solo_lectura(self, 'fechaesigef')


class TotalPacAdministrativoForm(forms.Form):
    planificado = forms.DecimalField(initial="0.00", max_digits=30, label=u'Valor Planificado', required=False,
                                     widget=forms.TextInput(
                                         attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%',
                                                'separator': 'true'}))
    ejecutado = forms.DecimalField(initial="0.00", max_digits=30, label=u'Valor Ejecutado', required=False,
                                   widget=forms.TextInput(
                                       attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%',
                                              'separator': 'true'}))
    archivoejecutado = ExtFileField(label=u'Seleccione Archivo', required=False,
                                    help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                                    ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"),
                                    max_upload_size=12582912)


class TotalPacTesoreriaForm(forms.Form):
    fuente = forms.DecimalField(initial="0.00", max_digits=30, label=u'Valor Planificado', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%',
                                                              'separator': 'true'}))
    archivofuente = ExtFileField(label=u'Seleccione Archivo', required=False,
                                 help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                                 ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"),
                                 max_upload_size=12582912)


class PacDetalleGeneralForm(forms.Form):
    productospac = forms.ModelChoiceField(label=u"Productos", queryset=ProductosPac.objects.all(), required=False,
                                          widget=forms.Select(attrs={'formwidth': '75%'}))
    valorenero = forms.DecimalField(initial="0.00", label=u'Valor Enero', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valorfebrero = forms.DecimalField(initial="0.00", label=u'Valor Febrero', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valormarzo = forms.DecimalField(initial="0.00", label=u'Valor Marzo', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valorabril = forms.DecimalField(initial="0.00", label=u'Valor Abril', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valormayo = forms.DecimalField(initial="0.00", label=u'Valor Mayo', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valorjunio = forms.DecimalField(initial="0.00", label=u'Valor Junio', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valorjulio = forms.DecimalField(initial="0.00", label=u'Valor Julio', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valoragosto = forms.DecimalField(initial="0.00", label=u'Valor Agosto', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valorseptiembre = forms.DecimalField(initial="0.00", label=u'Valor Septiembre', required=False,
                                         widget=forms.TextInput(
                                             attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valoroctubre = forms.DecimalField(initial="0.00", label=u'Valor Octubre', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valornoviembre = forms.DecimalField(initial="0.00", label=u'Valor Noviembre', required=False,
                                        widget=forms.TextInput(
                                            attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    valordiciembre = forms.DecimalField(initial="0.00", label=u'Valor Diciembre', required=False,
                                        widget=forms.TextInput(
                                            attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))


class PacDetalleGeneralAprobadoForm(forms.Form):
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%', 'separator': 'true'}))
    aprobado = forms.BooleanField(initial=False, label=u'Aprobado', required=False)
    valorejecutado = forms.DecimalField(initial="0.00", label=u'Valor Certificado', required=False,
                                        widget=forms.TextInput(
                                            attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    fechaejecutado = forms.DateField(label=u"Fecha Certificación", initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '20%'}),
                                     required=False)
    observacionejecutado = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '600'}),
                                           required=False, label=u"Observación Certificado")
    valorajudicado = forms.DecimalField(initial="0.00", label=u'Valor Ajudicado', required=False,
                                        widget=forms.TextInput(
                                            attrs={'class': 'imp-moneda', 'decimal': "2", 'formwidth': '50%'}))
    fechaajudicado = forms.DateField(label=u"Fecha Ajudicado", initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '20%'}),
                                     required=False)
    observacionajudicado = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '600'}),
                                           required=False, label=u"Observación Ajudicado")


class PersonaContratosForm(FormModeloBase):
    numerodocumento = forms.CharField(label=u'Número de Documento',
                                      widget=forms.TextInput(attrs={'col': '6'}), required=True)
    contratacionrelacionada = forms.CharField(label=u'Contratación Relacionada',
                                              widget=forms.TextInput(attrs={'col': '12'}), required=False)
    relacionies = forms.ChoiceField(label=u'Relación Laboral', choices=RELACION_IES,
                                    widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    regimenlaboral = forms.ModelChoiceField(label=u"Regimen laboral",
                                            queryset=RegimenLaboral.objects.filter(status=True), required=False,
                                            widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    dedicacionlaboral = forms.ModelChoiceField(label=u"Dedicación laboral",
                                               queryset=DedicacionLaboral.objects.filter(status=True), required=False,
                                               widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    denominacionpuesto = forms.ModelChoiceField(label=u"Denominacion de puesto",
                                                queryset=DenominacionPuesto.objects.filter(status=True),
                                                widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    unidadorganica = forms.ModelChoiceField(Departamento.objects.filter(status=True).distinct(),
                                          label=u"Unidad orgánica", widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    remuneracion = forms.DecimalField(initial="0.00", label=u'Remuneración', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'col': '3'}))
    explicacion = forms.CharField(label=u'Explicación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    fechainicio = forms.DateField(label=u"Fecha de inicio", required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha de fin", required=False,
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                           ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=4194304, required=False)


class DescargarContratosForm(FormModeloBase):
    fechainicio = forms.DateField(label=u"Fecha de inicio", required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha de fin", required=False,
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))


class PersonaAccionesOldForm(FormModeloBase):
    numerodocumento = forms.CharField(label=u'Número de Documento',
                                      widget=forms.TextInput(attrs={'col': '6'}), required=True)
    tipo = forms.ModelChoiceField(label=u"Tipo de acción",
                                  queryset=TipoAccionPersonal.objects.filter(status=True),
                                  widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    motivo = forms.ModelChoiceField(label=u"Motivo", queryset=MotivoAccionPersonal.objects.all(), required=False,
                                          widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    cargo = forms.CharField(label=u'Cargo', widget=forms.TextInput(attrs={'col': '12','readonly': True}), required=False, )
    unidad = forms.CharField(label=u'Unidad / Facultad', widget=forms.TextInput(attrs={'col': '12','readonly': True}),
                             required=False)
    denominacionpuesto = forms.ModelChoiceField(label=u"Denominacion de puesto",
                                                queryset=DenominacionPuesto.objects.filter(status=True),
                                                widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    unidadorganica = forms.ModelChoiceField(Departamento.objects.filter( status=True).distinct(),
        label=u"Unidad orgánica", widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    remuneracion = forms.DecimalField(initial="0.00", label=u'Remuneración', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'col': '3'}))
    explicacion = forms.CharField(label=u'Explicación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    fecharige = forms.DateField(label=u"Fecha rige", required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    ubicacionfisico = forms.CharField(label=u'Ubicación archivo físico',
                                      widget=forms.TextInput(attrs={'col': '12'}), required=True)
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                           ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=4194304, required=False)


class PersonaAccionesForm(FormModeloBase):
    numerodocumento = forms.CharField(label=u'Número de Documento',
                                      widget=forms.TextInput(attrs={'col': '6'}), required=True)
    tipo = forms.ModelChoiceField(label=u"Tipo de acción",
                                                queryset=TipoAccionPersonal.objects.filter(status=True),
                                                widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    motivoaccion = forms.ModelChoiceField(label=u"Motivo", queryset=MotivoAccionPersonal.objects.all(), required=False,
                                    widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    denominacionpuesto = forms.ModelChoiceField(label=u"Denominacion de puesto",
                                                queryset=DenominacionPuesto.objects.filter(status=True),
                                                widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    unidadorganica = forms.ModelChoiceField(Departamento.objects.filter(status=True).distinct(),
        label=u"Unidad orgánica", widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    remuneracion = forms.DecimalField(initial="0.00", label=u'Remuneración', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': "2", 'col': '3'}))
    explicacion = forms.CharField(label=u'Explicación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    fechainicio = forms.DateField(label=u"Fecha rige", required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    documento = forms.CharField(label=u'Ubicación archivo físico',
                                      widget=forms.TextInput(attrs={'col': '12'}), required=True)
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                           ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=4194304, required=False)


class InformesProcesadosForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 6Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=6291456)


class TipoPermisoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.TextInput(attrs={'rows': '3', 'with': '100'}),
                                  required=True)
    observacion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '600'}), required=False,
                                  label=u"Observación")
    quienaprueba = forms.ChoiceField(label=u'Grupo aprobador', choices=QUIEN_APRUEBA,
                                     widget=forms.Select(attrs={'class': 'imp-50'}))


class TipoPermisoDetalleForm(forms.Form):
    tipopermiso = forms.ModelChoiceField(TipoPermiso.objects.filter(status=True), required=False, label=u'Tipo Permiso',
                                         widget=forms.Select())
    descripcion = forms.CharField(label=u'Descripción', widget=forms.TextInput(attrs={'rows': '3', 'with': '100'}),
                                  required=True)
    anios = forms.IntegerField(label=u"Años", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    meses = forms.IntegerField(label=u"Meses", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    dias = forms.IntegerField(label=u"Días", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    horas = forms.IntegerField(label=u"Horas", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    descuentovacaciones = forms.BooleanField(initial=False, label=u'Descuento a Vacaciones?', required=False)
    perdirarchivo = forms.BooleanField(initial=False, label=u'Archivo?', required=False)
    pagado = forms.BooleanField(initial=False, label=u'Pagado?', required=False)
    # aplicar = forms.IntegerField(label=u"Aplicar", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    diasplazo = forms.IntegerField(label=u"Días Plazo", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    vigente = forms.BooleanField(initial=False, label=u'Vigente?', required=False)

    def editar(self):
        deshabilitar_campo(self, 'tipopermiso')


class FechaCertificacionForm(forms.Form):
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))


# Help Desk
class HdGrupoForm(forms.Form):
    departamento = forms.ModelChoiceField(label=u"Departamento",
                                          queryset=HdDepartament.objects.filter(status=True, parent__isnull=True),
                                          required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    area = forms.ModelChoiceField(label=u'Área', queryset=HdDepartament.objects.filter(status=True), required=False,
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    grupo = forms.CharField(label=u'Nombre del grupo', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                            required=True)
    descripcion = forms.CharField(label=u'Descripción del grupo', widget=forms.Textarea(attrs={'rows': '2'}),
                                  required=True)
    tipoincidente = forms.ModelChoiceField(label=u'Tipo', queryset=HdTipoIncidente.objects.filter(status=True),
                                           required=False, widget=forms.Select(attrs={'formwidth': '100%'}))

    def cargarArea(self, departament):
        self.fields['area'].queryset = HdDepartament.objects.filter(parent=departament, status=True)

    def editar(self, grupo):
        # self.fields['area'].widget.attrs['descripcion'] = activo
        self.fields['area'].queryset = HdDepartament.objects.filter(
            parent=grupo.departament.parent if grupo.departament else None, status=True)
        self.fields['area'].initial = grupo.departament.id if grupo.departament else None
        self.fields['area'].widget.attrs['value'] = grupo.departament.id if grupo.departament else None


class HdDetalle_GrupoForm(forms.Form):
    agente = forms.IntegerField(initial=0, label=u'Agente', required=False,
                                widget=forms.TextInput(attrs={'select2search': 'true'}))
    responsable = forms.BooleanField(label=u'Responsable del grupo', required=False, widget=CheckboxInput())

    # isDirector = forms.BooleanField(label=u'Director del grupo', required=False, widget=CheckboxInput())
    # isExpert = forms.BooleanField(label=u'Experto del grupo', required=False, widget=CheckboxInput())

    def adicionar(self):
        self.fields['agente'].widget.attrs['descripcion'] = "seleccione administrativo"

    def editar(self, agente):
        self.fields['agente'].widget.attrs['descripcion'] = u"%s - %s" % (
            agente.persona, agente.denominacionpuesto.descripcion)
        self.fields['agente'].initial = agente.id
        self.fields['agente'].widget.attrs['value'] = agente.id

    def existe_responsable(self):
        deshabilitar_campo(self, 'responsable')

    def existe_director(self):
        deshabilitar_campo(self, 'isDirector')

    def existe_expert(self):
        deshabilitar_campo(self, 'isExpert')


class HdUrgenciaForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre de urgencia', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=False)
    descripcion = forms.CharField(label=u'Descripción de urgencia', widget=forms.Textarea(attrs={'rows': '2'}),
                                  required=False)
    codigo = forms.CharField(label=u'Codigo', max_length=10, required=False)

    def editar(self):
        deshabilitar_campo(self, 'codigo')


class HdImpactoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre de impacto', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=False)
    descripcion = forms.CharField(label=u'Descripción de impacto', widget=forms.TextInput(attrs={'rows': '2'}),
                                  required=False)
    codigo = forms.CharField(label=u'Codigo', max_length=10, required=False)

    def editar(self):
        deshabilitar_campo(self, 'codigo')


class HdPrioridadForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre de prioridad', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=False)
    codigo = forms.CharField(label=u'codigo', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    hora = forms.CharField(label=u'Hora', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    minuto = forms.CharField(label=u'Minutos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    segundo = forms.CharField(label=u'Segundos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False,
                          help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png',
                          ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)

    def editar(self):
        deshabilitar_campo(self, 'codigo')

    def ocultarimagen(self):
        del self.fields['imagen']


class HdUrgencia_Impacto_PrioridadForm(forms.Form):
    urgencia = forms.ModelChoiceField(HdUrgencia.objects.filter(status=True), required=False, label=u'Urgencia',
                                      widget=forms.Select())
    impacto = forms.ModelChoiceField(HdImpacto.objects.filter(status=True), required=False, label=u'Impacto',
                                     widget=forms.Select())
    prioridad = forms.ModelChoiceField(HdPrioridad.objects.filter(status=True), required=False, label=u'Prioridad',
                                       widget=forms.Select())
    modificar = forms.BooleanField(label=u'Modificar tiempo de resolución', required=False, widget=CheckboxInput())
    hora = forms.CharField(label=u'Hora', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    minuto = forms.CharField(label=u'Minutos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    segundo = forms.CharField(label=u'Segundos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))

    def editar(self):
        deshabilitar_campo(self, 'hora')
        deshabilitar_campo(self, 'minuto')
        deshabilitar_campo(self, 'segundo')


class HdCatrgoriaForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre de Categoria", max_length=50,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    tipoincidente = forms.ModelChoiceField(label=u'Tipo de incidente',
                                           queryset=HdTipoIncidente.objects.filter(status=True), required=False,
                                           widget=forms.Select(attrs={'formwidth': '100%'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')
        # deshabilitar_campo(self, 'tipoincidente')


class HdTipoIncidenteForm(forms.Form):
    nombre = forms.CharField(label=u"Tipo de incidente", max_length=50,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    descripcion = forms.CharField(label=u"Descripción", max_length=1000,
                                  widget=forms.Textarea(attrs={'rows': '2', 'with': '100%'}), required=False)

    def editar(self):
        deshabilitar_campo(self, 'nombre')


class HdSubCatrgoriaForm(forms.Form):
    categoria = forms.CharField(label=u"Nombre de Categoria", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-100'}))
    subcategoria = forms.CharField(label=u"Nombre Dispositivo", max_length=50,
                                   widget=forms.TextInput(attrs={'class': 'imp-100'}))

    def editar(self):
        deshabilitar_campo(self, 'categoria')


class HdDetalleSubCategoriaForm(forms.Form):
    subcategoria = forms.CharField(label=u"Sub Categoria", max_length=50, required=False,
                                   widget=forms.TextInput(attrs={'class': 'imp-100'}))
    detalle = forms.CharField(label=u"Nombre detalle", max_length=50,
                              widget=forms.TextInput(attrs={'class': 'imp-100'}))
    urgencia = forms.ModelChoiceField(label=u"Urgencia", queryset=HdUrgencia.objects.filter(status=True), required=True,
                                      widget=forms.Select(attrs={'formwidth': '50%'}))
    impacto = forms.ModelChoiceField(label=u"Impacto", queryset=HdImpacto.objects.filter(status=True), required=True,
                                     widget=forms.Select(attrs={'formwidth': '50%'}))
    prioridad = forms.CharField(label=u"Prioridad", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'formwidth': '60%'}))
    tiemporesolucion = forms.CharField(label=u"Hora resolución", max_length=50, required=False,
                                       widget=forms.TextInput(attrs={'formwidth': '40%'}))

    def editar(self):
        deshabilitar_campo(self, 'subcategoria')
        deshabilitar_campo(self, 'prioridad')
        deshabilitar_campo(self, 'tiemporesolucion')


class HdEstadoForm(forms.Form):
    nombre = forms.CharField(label=u"Estado de Help Desk", max_length=50, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False,
                          help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png',
                          ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)


class HdEstadoEditForm(forms.Form):
    nombre = forms.CharField(label=u"Estado de Help Desk", max_length=50, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')


class HdEstadoImagenForm(forms.Form):
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False,
                          help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png',
                          ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)


class HdPrioridadImagenForm(forms.Form):
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False,
                          help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png',
                          ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)


class HdMedioReporteForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=50, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))
    descripcion = forms.CharField(label=u"Descripción", max_length=300, required=False,
                                  widget=forms.Textarea(attrs={'rows': '3'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')
        deshabilitar_campo(self, 'descripcion')


class HdIncidenciaFrom(forms.Form):

    asunto = forms.CharField(label=u"Incidente", max_length=500, required=False,
                             widget=forms.Textarea(attrs={'rows': '3', 'with': '100'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}),
                                  required=False)
    persona = forms.IntegerField(initial=0, required=False, label=u'Solicitante',
                                 widget=forms.TextInput(attrs={'select2search': 'true'}))
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False,
                                    widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicacion", queryset=HdBloqueUbicacion.objects.filter(status=True),
                                       required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    # departamento = forms.IntegerField(initial=0, required=False, label=u'Departamento',widget=forms.TextInput(attrs={'select2search': 'true'}))
    tipoincidente = forms.ModelChoiceField(label=u"Tipo de grupo", queryset=HdTipoIncidente.objects.filter(status=True),
                                           required=False, widget=forms.Select(attrs={'formwidth': '50%'}))

    grupo = forms.ModelChoiceField(label=u"Grupos de agente", queryset=HdGrupo.objects.filter(status=True),
                                   required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    agente = forms.ModelChoiceField(label=u'Agente a reasignar',
                                    queryset=HdDetalle_Grupo.objects.filter(estado=True, status=True), required=False,
                                    widget=forms.Select(attrs={'formwidth': '50%'}))
    ayudantes = forms.ModelMultipleChoiceField(label=u'Agentes ayudantes', queryset=HdDetalle_Grupo.objects.all(),
                                               required=False)
    categoria = forms.ModelChoiceField(label=u"Categoria", queryset=HdCategoria.objects.filter(status=True),
                                       required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    subcategoria = forms.ModelChoiceField(label=u"Sub Categoria", queryset=HdSubCategoria.objects.filter(status=True),
                                          required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    detallesubcategoria = forms.ModelChoiceField(label=u"Detalle Sub Categoria",
                                                 queryset=HdDetalle_SubCategoria.objects.filter(status=True),
                                                 required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    revisionequipoexterno = forms.BooleanField(initial=False,
                                               label=u'Revisión de equipo personal que realiza gestión institucional',
                                               required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    revisionequiposincodigo = forms.BooleanField(initial=False,
                                                 label=u'Revisión de equipo institucional sin código de barra o sin registro en el sistema interno',
                                                 required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    serie = forms.CharField(label=u"Serie o código", max_length=250, required=False,
                            widget=forms.TextInput(attrs={'formwidth': '100%'}))
    activo = forms.IntegerField(initial=0, required=False, label=u'Activo Fijo',
                                widget=forms.TextInput(attrs={'select2search': 'true'}))

    fechacompra = forms.CharField(label=u"Fecha de Ingreso", widget=forms.TextInput(attrs={'formwidth': '35%'}),
                                  required=False)
    vidautil = forms.CharField(label=u"Vida Util", widget=forms.TextInput(attrs={'formwidth': '30%'}), required=False)
    tiemporestante = forms.CharField(label=u"Fecha de caducidad", widget=forms.TextInput(attrs={'formwidth': '35%'}),
                                     required=False)
    resolucion = forms.CharField(label=u'Resolución del incidente', required=False,
                                 widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}))

    medioreporte = forms.ModelChoiceField(label=u"Modo de Reporte", queryset=HdMedioReporte.objects.filter(status=True),
                                          required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    fechareporte = forms.DateField(label=u'Fecha de reporte', initial=datetime.now().date(), required=False,
                                   input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                    attrs={'class': 'selectorfecha',
                                                                                           'formwidth': '50%'}))
    horareporte = forms.TimeField(label=u'Hora de reporte ', initial=str(datetime.now().time()), required=False,
                                  input_formats=["%H:%M"], widget=DateTimeInput(format='%H:%M',
                                                                                attrs={'class': 'selectorhora',
                                                                                       'formwidth': '50%'}))
    estado = forms.ModelChoiceField(label=u"Estado Incidente", queryset=HdEstado.objects.filter(status=True),
                                    required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    proceso = forms.ModelChoiceField(label=u"Proceso", queryset=HdProceso.objects.filter(status=True), required=False,
                                     widget=forms.Select(attrs={'formwidth': '50%'}))
    estadobaja = forms.ModelChoiceField(label=u"Estado de proceso",
                                        queryset=HdEstado_Proceso.objects.filter(status=True), required=False,
                                        widget=forms.Select(attrs={'formwidth': '50%'}))
    causa = forms.ModelChoiceField(label=u"Causa de incidente",
                                   queryset=HdCausas.objects.filter(pk__in=[1, 4], status=True), required=False,
                                   widget=forms.Select(attrs={'formwidth': '50%'}))
    # fecharesolucion = forms.DateField(label=u'Fecha de resolución', initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha','formwidth': '50%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato  pdf, jpg, png, jpeg',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304)

    def cargarayudantes(self, grupo):
        self.fields['ayudantes'].queryset = HdDetalle_Grupo.objects.filter(grupo=grupo).order_by('persona__apellido1',
                                                                                                 'persona__apellido2')

    def editar(self, incidente):
        del self.fields['descripcion']
        del self.fields['archivo']
        del self.fields['proceso']
        del self.fields['estadobaja']
        del self.fields['resolucion']
        deshabilitar_campo(self, 'persona')
        # deshabilitar_campo(self, 'fechareporte')
        # deshabilitar_campo(self, 'horareporte')
        deshabilitar_campo(self, 'estado')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        self.fields['categoria'].queryset = HdCategoria.objects.filter(tipoincidente=incidente.tipoincidente)
        if incidente.tipoincidente.id == 3:
            del self.fields['revisionequiposincodigo']
            del self.fields['revisionequipoexterno']
            del self.fields['serie']
            del self.fields['causa']
        # deshabilitar_campo(self, 'fecharesolucion')

    def tiene_agente(self):
        deshabilitar_campo(self, 'tipoincidente')
        deshabilitar_campo(self, 'grupo')
        deshabilitar_campo(self, 'agente')
        deshabilitar_campo(self, 'ayudantes')

    def resolver(self):
        del self.fields['descripcion']
        del self.fields['archivo']
        # del self.fields['fechareporte']
        # del self.fields['horareporte']
        deshabilitar_campo(self, 'asunto')
        deshabilitar_campo(self, 'persona')
        deshabilitar_campo(self, 'tipoincidente')
        deshabilitar_campo(self, 'bloque')
        deshabilitar_campo(self, 'ubicacion')
        deshabilitar_campo(self, 'grupo')
        deshabilitar_campo(self, 'agente')
        # deshabilitar_campo(self, 'ayudantes')
        deshabilitar_campo(self, 'medioreporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        # deshabilitar_campo(self, 'categoria')
        # deshabilitar_campo(self, 'subcategoria')

    def add(self):
        del self.fields['descripcion']
        # deshabilitar_campo(self, 'fechareporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'activo')
        deshabilitar_campo(self, 'tiemporestante')

    def adicionar(self):
        del self.fields['descripcion']
        # deshabilitar_campo(self, 'fechareporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        # del self.fields['fecharesolucion']

    def adicionar_x_agente(self):
        del self.fields['descripcion']
        deshabilitar_campo(self, 'fechareporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        # del self.fields['fechareporte']
        del self.fields['horareporte']

    def reasignar(self):
        del self.fields['descripcion']
        del self.fields['archivo']
        del self.fields['estadobaja']
        del self.fields['proceso']
        del self.fields['estado']
        del self.fields['causa']
        del self.fields['horareporte']
        del self.fields['fechareporte']
        deshabilitar_campo(self, 'persona')
        deshabilitar_campo(self, 'tipoincidente')
        deshabilitar_campo(self, 'bloque')
        deshabilitar_campo(self, 'ubicacion')
        deshabilitar_campo(self, 'medioreporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        # deshabilitar_campo(self, 'ayudantes')

    def escalar(self):
        del self.fields['descripcion']
        del self.fields['archivo']
        del self.fields['estadobaja']
        del self.fields['proceso']
        del self.fields['estado']
        del self.fields['grupo']
        del self.fields['agente']
        # del self.fields['categoria']
        # del self.fields['detallesubcategoria']
        # del self.fields['subcategoria']
        del self.fields['causa']
        del self.fields['ayudantes']
        # del self.fields['revisionequipoexterno']
        # del self.fields['revisionequiposincodigo']
        # del self.fields['serie']
        deshabilitar_campo(self, 'asunto')
        deshabilitar_campo(self, 'persona')
        deshabilitar_campo(self, 'bloque')
        deshabilitar_campo(self, 'ubicacion')
        deshabilitar_campo(self, 'medioreporte')
        deshabilitar_campo(self, 'fechareporte')
        deshabilitar_campo(self, 'horareporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')


class HdSolicitarIncidenteFrom(forms.Form):
    #tipousuario = forms.ChoiceField(label=u'Registro de incidente como usuario con perfil', choices=TIPO_USUARIO, required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    #tercerapersona = forms.IntegerField(initial=0, required=False, label=u'Solicitante', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'imp-100'}))
    tipoincidente = forms.ModelChoiceField(label=u"Tipo de grupo", queryset=HdTipoIncidente.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%', 'style':'width:100%'}))
    # concodigo = forms.BooleanField(initial=True, label=u'Con Codigo?', required=False)
    activo = forms.IntegerField(initial=0, required=False, label=u'Activo Fijo', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'imp-100'}))
    # activosincodigo = forms.CharField(label=u"Activo  Sin Código", max_length=500, required=False,
    #                                   widget=forms.TextInput(attrs={'class': 'imp-100'}))
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicación", queryset=HdBloqueUbicacion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    asunto = forms.CharField(label=u"Asunto del incidente", max_length=500, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  pdf, jpg, png, jpeg', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304)

    def cargarubicacion(self, bloque):
        self.fields['ubicacion'].queryset = HdBloqueUbicacion.objects.filter(bloque=bloque, status=True)

    def es_docente(self):
        pass
        #del self.fields['tipoincidente']
        #del self.fields['tipousuario']
        # del self.fields['tercerapersona']

    def desactiva_tipousuario(self):
        pass
        #del self.fields['tipousuario']

    def desactivar(self):
        pass
        #del self.fields['tercerapersona']

    def editar(self, activo):
        self.fields['activo'].widget.attrs['descripcion'] = activo
        self.fields['activo'].initial = activo.id
        self.fields['activo'].widget.attrs['value'] = activo.id
    # def edit(self, concodigo):
    #
    #     deshabilitar_campo(self, 'activo')
    #
    # def desactivarcodigo(self, concodigo):
    #
    #     deshabilitar_campo(self, 'activosincodigo')


class HdDirectorForm(forms.Form):
    director = forms.CharField(label=u"Director", max_length=50, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-100'}))


class HdDepartamentForm(forms.Form):
    nombre = forms.CharField(label=u"Departamento", max_length=250, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))
    director = forms.IntegerField(initial=0, label=u'Director/a', required=False,
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))

    def adicionar(self):
        self.fields['director'].widget.attrs['descripcion'] = "seleccione administrativo"

    def editar(self, director):
        self.fields['director'].widget.attrs['descripcion'] = u"%s - %s" % (
            director.persona, director.denominacionpuesto.descripcion)
        self.fields['director'].initial = director.id
        self.fields['director'].widget.attrs['value'] = director.id


class HdDepartamentAreaForm(forms.Form):
    nombre = forms.CharField(label=u"Area", max_length=250, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))
    experto = forms.IntegerField(initial=0, label=u'Experto/a', required=False,
                                 widget=forms.TextInput(attrs={'select2search': 'true'}))

    def adicionar(self):
        self.fields['experto'].widget.attrs['descripcion'] = "seleccione administrativo"

    def editar(self, experto):
        self.fields['experto'].widget.attrs['descripcion'] = u"%s - %s" % (
            experto.persona, experto.denominacionpuesto.descripcion)
        self.fields['experto'].initial = experto.id
        self.fields['experto'].widget.attrs['value'] = experto.id


class CerrarOrdenForm(forms.Form):
    informe = forms.CharField(label=u"Informe", max_length=250, required=False,
                              widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}))
    estado = forms.ChoiceField(label=u'Estado', choices=ESTADO_ORDEN_TRABAJO, required=False,
                               widget=forms.Select(attrs={'class': 'imp-50'}))
    # calificacion = forms.FloatField(label=u"Calificación", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))
    archivo = ExtFileField(label=u'Seleccione Archivo',
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, png, jpeg',
                           ext_whitelist=(".pdf"), max_upload_size=4194304, required=False)

    def quitar_estado(self):
        del self.fields['estado']


class DetalleOrdenForm(forms.Form):
    repuesto = forms.CharField(label=u"Repuesto", max_length=250, required=False,
                               widget=forms.Textarea(attrs={'rows': '4', 'with': '100%'}))
    cantidad = forms.FloatField(label=u"Cantidad", initial="0.00", required=True,
                                widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))


class HdProcesoFrom(forms.Form):
    nombre = forms.CharField(label=u"Nombre Proceso", max_length=50, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))


class HdEstadoProcesoFrom(forms.Form):
    nombre = forms.CharField(label=u"Nombre del estado proceso", max_length=50, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))
    detalle = forms.CharField(label=u"Detalle", max_length=250, required=False,
                              widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}))
    proceso = forms.ModelChoiceField(label=u'Proceso', queryset=HdProceso.objects.filter(status=True), required=False,
                                     widget=forms.Select(attrs={'formwidth': '100%'}))

    def adcionarestados(self):
        del self.fields['proceso']


class HdDetalleIncidenteFrom(forms.Form):
    grupo = forms.ModelChoiceField(label=u"Grupos", queryset=HdGrupo.objects.filter(status=True), required=False,
                                   widget=forms.Select(attrs={'formwidth': '100%'}))
    agente = forms.ModelChoiceField(label=u'Agente', queryset=HdDetalle_Grupo.objects.filter(estado=True, status=True),
                                    required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    estado = forms.ModelChoiceField(label=u"Estado Incidente", queryset=HdEstado.objects.filter(status=True),
                                    required=False, widget=forms.Select(attrs={'formwidth': '100%'}))


class PlanificacionHorasExtrasForm(forms.Form):
    anio = forms.IntegerField(label=u"Año", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    mes = forms.ChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES,
                            widget=forms.Select(attrs={'formwidth': '30%'}))
    actividad = forms.CharField(label=u"Objetivo Institucional", widget=forms.Textarea(attrs={'rows': '2'}),
                                required=False)
    observacion = forms.CharField(label=u"Observación", widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    persona = forms.ModelChoiceField(Persona.objects.filter(status=True), label=u"Persona",
                                     widget=forms.Select(attrs={'formwidth': '100%'}), required=False)
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '40%'}))
    horadesde = forms.TimeField(label=u"Hora desde", required=False, initial=str(datetime.now().time())[:5],
                                input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                              attrs={'class': 'selectorhora',
                                                                                     'formwidth': '30%'}))
    horahasta = forms.TimeField(label=u"Hora Hasta", required=False, initial=str(datetime.now().time())[:5],
                                input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                              attrs={'class': 'selectorhora',
                                                                                     'formwidth': '30%'}))
    actividadplanificada = forms.CharField(label=u"Actividad Planificada", widget=forms.Textarea(attrs={'rows': '2'}),
                                           required=False)

    def adicionar(self, departamento):
        self.fields['persona'].queryset = Persona.objects.filter(status=True,
                                                                 distributivopersona__unidadorganica=departamento,
                                                                 distributivopersona__estadopuesto__id=PUESTO_ACTIVO_ID)

    def editar(self, departamento):
        deshabilitar_campo(self, 'anio')
        deshabilitar_campo(self, 'mes')
        self.fields['persona'].queryset = Persona.objects.filter(status=True,
                                                                 distributivopersona__unidadorganica=departamento,
                                                                 distributivopersona__estadopuesto__id=PUESTO_ACTIVO_ID)


class PlanificacionHorasExtrasVerificarForm(forms.Form):
    anio = forms.IntegerField(label=u"Año", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    mes = forms.ChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES,
                            widget=forms.Select(attrs={'formwidth': '30%'}))
    actividad = forms.CharField(label=u"Actividad Planificada", widget=forms.Textarea(attrs={'rows': '3'}),
                                required=False)
    observaciontthh = forms.CharField(label=u"Observación", widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    verificar = forms.BooleanField(initial=False, label=u'Verificar?', required=False)

    def verificacion(self):
        deshabilitar_campo(self, 'anio')
        deshabilitar_campo(self, 'mes')
        deshabilitar_campo(self, 'actividad')


class PlanificacionHorasExtrasAprobacionForm(forms.Form):
    anio = forms.IntegerField(label=u"Año", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    mes = forms.ChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES,
                            widget=forms.Select(attrs={'formwidth': '30%'}))
    actividad = forms.CharField(label=u"Actividad Planificada", widget=forms.Textarea(attrs={'rows': '3'}),
                                required=False)
    observacionaprobado = forms.CharField(label=u"Observación", widget=forms.Textarea(attrs={'rows': '3'}),
                                          required=False)
    aprobar = forms.BooleanField(initial=False, label=u'Aprobar?', required=False)

    def aprobacion(self):
        deshabilitar_campo(self, 'anio')
        deshabilitar_campo(self, 'mes')
        deshabilitar_campo(self, 'actividad')


# CURSOS FORMACION Y CAPACITACION GENERADO POR TALENTO HUMANO
class CapPeriodoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=True)
    descripcion = forms.CharField(label=u'Descripción', max_length=1000, widget=forms.Textarea(attrs={'rows': '3'}),
                                  required=True)
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=25,
                                  widget=forms.TextInput(attrs={'class': 'imp-100'}), required=True)
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'], required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], required=False,
                               widget=DateTimeInput(format='%d-%m-%Y',
                                                    attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    archivo = ExtFileField(label=u'Archivo',
                           help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"),
                           max_upload_size=12582912, required=False)

    def editar_grupo(self):
        deshabilitar_campo(self, 'fechainicio')
        deshabilitar_campo(self, 'fechafin')


class CapEventoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=True)
    tipocurso = forms.ModelChoiceField(label=u"Tipo Evento", queryset=TipoCurso.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '50%'}))

    def editar_grupo(self):
        deshabilitar_campo(self, 'tipocurso')


class CapEnfocadaForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=True)


class CapEventoPeriodoForm(forms.Form):
    from sga.models import Aula
    from ckeditor_uploader.widgets import CKEditorUploadingWidget
    periodo = forms.ModelChoiceField(label=u'Período', required=False, queryset=CapPeriodo.objects.filter(status=True),
                                     widget=forms.Select())
    capevento = forms.ModelChoiceField(label=u'Evento', queryset=CapEvento.objects.filter(status=True), required=True,
                                       widget=forms.Select())
    departamento = forms.ModelChoiceField(label=u'Dirección que confiere certificado',
                                          queryset=Departamento.objects.filter(status=True), required=True,
                                          widget=forms.Select())
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    provincia = forms.ModelChoiceField(label=u"Provincia / Estado", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    canton = forms.ModelChoiceField(label=u"Cantón / Ciudad", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Área Conocimiento",
                                              queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=True,
                                              widget=forms.Select(attrs={'class': 'imp-75'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub Área Conocimiento",
                                                 queryset=SubAreaConocimientoTitulacion.objects.all(), required=True,
                                                 widget=forms.Select(attrs={'class': 'imp-75'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub Área Especifica Conocimiento",
                                                           queryset=SubAreaEspecificaConocimientoTitulacion.objects.all(),
                                                           required=True,
                                                           widget=forms.Select(attrs={'class': 'imp-75'}))
    regimenlaboral = forms.ModelChoiceField(RegimenLaboral.objects.filter(status=True), required=False,
                                            label=u'Régimen Laboral', widget=forms.Select())
    contextocapacitacion = forms.ModelChoiceField(label=u"Contexto de la Capacitación/Formación",
                                                  queryset=ContextoCapacitacion.objects.all(), required=False,
                                                  widget=forms.Select())
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    aula = forms.ModelChoiceField(label=u'Aula', required=True, queryset=Aula.objects.filter(status=True),
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    enfoque = forms.ModelChoiceField(label=u'Enfoque', required=True, queryset=CapEnfocada.objects.filter(status=True),
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    modalidad = forms.ChoiceField(label=u"Modalidad Capacitación", required=False, choices=MODALIDAD_CAPACITACION,
                                  widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '50%'}))
    tipoparticipacion = forms.ModelChoiceField(label=u"Tipo Aprobación", queryset=TipoParticipacion.objects.all(),
                                               required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    tipocertificacion = forms.ModelChoiceField(label=u"Tipo Certificación", queryset=TipoCertificacion.objects.all(),
                                               required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    tipocapacitacion = forms.ModelChoiceField(label=u"Programado Plan Institucional",
                                              queryset=TipoCapacitacion.objects.all(), required=False,
                                              widget=forms.Select(attrs={'formwidth': '50%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                    attrs={
                                                                                                        'class': 'selectorfecha',
                                                                                                        'formwidth': '50%'}))
    horas = forms.IntegerField(label=u"Horas Académica", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    horaspropedeutica = forms.IntegerField(label=u"Horas Propedéuticas", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    horasautonoma = forms.IntegerField(label=u"Horas Autónomas", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    horastotal = forms.IntegerField(label=u"Horas Total", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    folder = forms.IntegerField(label=u"Nº Folder", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    cupo = forms.IntegerField(label=u"Cupo", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    minnota = forms.IntegerField(label=u"Mínimo Calificación", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    minasistencia = forms.IntegerField(label=u"Mínimo Asistencia", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    codigo = forms.IntegerField(label=u"Código", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    objetivo = forms.CharField(label=u'Objetivo General', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    contenido = forms.CharField(label=u"Cuerpo CHKEditor", required=False, widget=CKEditorUploadingWidget())
    abreviaturadepartamento = forms.CharField(label=u'Abreviatura del departamento', required=False, max_length=25,
                                              widget=forms.TextInput(attrs={'class': 'imp-100'}))
    revisado = forms.CharField(label=u'Revisador', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    aprobado1 = forms.CharField(label=u'Aprobador 1', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                required=False)
    aprobado2 = forms.CharField(label=u'Aprobador 2', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                required=False)
    aprobado3 = forms.CharField(label=u'Aprobador 3', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                required=False)
    visualizar = forms.BooleanField(initial=True, label=u'Visualizar Evento', required=False,
                                    widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    actualizar = forms.BooleanField(initial=False, label=u'Actualizar (Aprobadores,revisador,abreviatura)',
                                    required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    observacionreporte = forms.CharField(label=u'Observación reporte',
                                         widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '200'}), required=False)

    def editar_grupo(self):
        deshabilitar_campo(self, 'periodo')
        deshabilitar_campo(self, 'revisado')
        deshabilitar_campo(self, 'aprobado1')
        deshabilitar_campo(self, 'aprobado2')
        deshabilitar_campo(self, 'aprobado3')
        deshabilitar_campo(self, 'horastotal')
        deshabilitar_campo(self, 'abreviaturadepartamento')

    def editar_responsable(self, responsable):
        self.fields['responsable'].widget.attrs['descripcion'] = responsable.flexbox_repr() if responsable else ""
        self.fields['responsable'].widget.attrs['value'] = responsable.id if responsable else ""

    def editar_regimenlaboral(self):
        deshabilitar_campo(self, 'regimenlaboral')

    def adicionar(self, pais, provincia, canton):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=canton)
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=None)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=None)
        del self.fields['actualizar']

    def editar(self, capacitacion):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=capacitacion.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=capacitacion.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=capacitacion.canton)
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=capacitacion.areaconocimiento, vigente=True)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=capacitacion.subareaconocimiento, vigente=True)


class CapInstructorForm(forms.Form):
    instructor = forms.IntegerField(initial=0, required=False, label=u'Instructor',
                                    widget=forms.TextInput(attrs={'select2search': 'true'}))
    tipo = forms.ChoiceField(label=u"Tipo", required=False, choices=CAPACITACION_FALICITADORES_TIPO,
                             widget=forms.Select(attrs={'class': 'imp-25'}))
    instructorprincipal = forms.BooleanField(initial=False, label=u'Principal?', required=False)

    def editar(self, capinstructor):
        self.fields['instructor'].widget.attrs[
            'descripcion'] = capinstructor.instructor.flexbox_repr() if capinstructor.instructor else ""
        self.fields['instructor'].widget.attrs[
            'value'] = capinstructor.instructor.id if capinstructor.instructor else ""


class CapTurnoForm(forms.Form):
    turno = forms.IntegerField(label=u"Turno", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '33%'}))
    horainicio = forms.TimeField(label=u"Hora Inicio", required=True, initial=str("07:00"), input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    horafin = forms.TimeField(label=u'Hora Fin', required=True, initial=str("08:00"), input_formats=['%H:%M'],
                              widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    horas = forms.IntegerField(label=u"Horas", required=False, initial=1, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '33%'}))

    def editar_grupo(self):
        deshabilitar_campo(self, 'horas')

    def editar_turno(self):
        deshabilitar_campo(self, 'turno')


class CapClaseForm(forms.Form):
    from sga.models import DIAS_CHOICES
    capeventoperiodo = forms.CharField(label=u'Evento', max_length=500,
                                       widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    turno = forms.ModelChoiceField(CapTurno.objects.filter(status=True), required=False, label=u'Turno',
                                   widget=forms.Select())
    dia = forms.ChoiceField(label=u"Dia", required=False, choices=DIAS_CHOICES,
                            widget=forms.Select(attrs={'class': 'imp-25'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                    attrs={
                                                                                                        'class': 'selectorfecha',
                                                                                                        'formwidth': '50%'}))

    def editar_grupo(self):
        deshabilitar_campo(self, 'capeventoperiodo')

    def editar_turno(self):
        deshabilitar_campo(self, 'turno')
        deshabilitar_campo(self, 'dia')


class CapSolicitudForm(forms.Form):
    fechasolicitud = forms.DateField(label=u"Fecha Solicitud", input_formats=['%d-%m-%Y'],
                                     widget=DateTimeInput(format='%d-%m-%Y',
                                                          attrs={'class': 'selectorfecha', 'formwidth': '20%'}),
                                     required=False)
    solicito = forms.CharField(label=u'Solicito', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                               required=False)
    participante = forms.IntegerField(initial=0, required=False, label=u'Participante',
                                      widget=forms.TextInput(attrs={'select2search': 'true'}))
    observacion = forms.CharField(label="Observación", widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}),
                                  required=True)

    def editar(self, participante):
        deshabilitar_campo(self, 'fechasolicitud')
        deshabilitar_campo(self, 'solicito')
        deshabilitar_campo(self, 'capeventoperiodo')
        deshabilitar_campo(self, 'participante')
        self.fields['participante'].widget.attrs['descripcion'] = participante.flexbox_repr() if participante else ""
        self.fields['participante'].widget.attrs['value'] = participante.id if participante else ""

    def adicionar(self):
        deshabilitar_campo(self, 'fechasolicitud')
        deshabilitar_campo(self, 'solicito')

    def deshabilitar_observacion(self):
        deshabilitar_campo(self, 'observacion')


class CapInscribirForm(forms.Form):
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=False,
        label=u'Departamento', widget=forms.Select())
    participante = forms.IntegerField(initial=0, required=False, label=u'Participante',
                                      widget=forms.TextInput(attrs={'select2search': 'true'}))
    observacion = forms.CharField(label="Observación", widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}),
                                  required=True)


class CapConfiguracionForm(forms.Form):
    minasistencia = forms.IntegerField(label=u"Minimo Asistencia", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    minnota = forms.IntegerField(label=u"Minimo Calificación", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    abreviaturadepartamento = forms.CharField(label=u'Abreviatura del departamento', max_length=25,
                                              widget=forms.TextInput(attrs={'class': 'imp-100'}))
    revisado = forms.IntegerField(initial=0, required=False, label=u'Reporte y revisador',
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    aprobado1 = forms.IntegerField(initial=0, required=False, label=u'Aprobador TTHH',
                                   widget=forms.TextInput(attrs={'select2search': 'true'}))
    aprobado2 = forms.IntegerField(initial=0, required=False, label=u'Reporte y aprobador IPEC',
                                   widget=forms.TextInput(attrs={'select2search': 'true'}))
    aprobado3 = forms.IntegerField(initial=0, required=False, label=u'Reporte Secret. Gral.',
                                   widget=forms.TextInput(attrs={'select2search': 'true'}))

    def editar(self, revisador, aprobador1, aprobador2, aprobador3):
        self.fields['revisado'].widget.attrs['descripcion'] = revisador[0].flexbox_repr_con_cargo() if revisador else ""
        self.fields['revisado'].widget.attrs['value'] = revisador[0].id if revisador else ""
        self.fields['aprobado1'].widget.attrs['descripcion'] = aprobador1[
            0].flexbox_repr_con_cargo() if aprobador1 else ""
        self.fields['aprobado1'].widget.attrs['value'] = aprobador1[0].id if aprobador1 else ""
        self.fields['aprobado2'].widget.attrs['descripcion'] = aprobador2[
            0].flexbox_repr_con_cargo() if aprobador2 else ""
        self.fields['aprobado2'].widget.attrs['value'] = aprobador2[0].id if aprobador2 else ""
        self.fields['aprobado3'].widget.attrs['descripcion'] = aprobador3[
            0].flexbox_repr_con_cargo() if aprobador3 else ""
        self.fields['aprobado3'].widget.attrs['value'] = aprobador3[0].id if aprobador3 else ""


class CapAsistenciaForm(forms.Form):
    clase = forms.ModelChoiceField(CapClase.objects.filter(status=True), required=False, label=u'Horario',
                                   widget=forms.Select())
    fechaadicionar = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                      attrs={
                                                                                                          'class': 'selectorfecha',
                                                                                                          'formwidth': '20%'}),
                                     required=False)

    def adicionar(self, eventoperiodo):
        self.fields['clase'].queryset = CapClase.objects.filter(capeventoperiodo=eventoperiodo).order_by('dia')


# solicitud de vehiculo
class SolicitudVehiculoForm(forms.Form):
    cantonsalida = forms.ModelChoiceField(Canton.objects.filter(status=True), label=u"Cantón Salida",
                                          widget=forms.Select(attrs={'formwidth': '50%'}), required=False)
    cantondestino = forms.ModelChoiceField(Canton.objects.filter(status=True), label=u"Cantón Destino",
                                           widget=forms.Select(attrs={'formwidth': '50%'}), required=False)
    fechasalida = forms.DateField(label=u"Fecha de Salida", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '25%'}))
    fechallegada = forms.DateField(label=u"Fecha de LLegada", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                                   widget=DateTimeInput(format='%d-%m-%Y',
                                                        attrs={'class': 'selectorfecha', 'formwidth': '25%'}))
    horasalida = forms.TimeField(label=u"Hora de Salida desde", required=False, initial=str(datetime.now().time())[:5],
                                 input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                               attrs={'class': 'selectorhora',
                                                                                      'formwidth': '25%'}))
    horaingreso = forms.TimeField(label=u"Hora de LLegada", required=False, initial=str(datetime.now().time())[:5],
                                  input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                                attrs={'class': 'selectorhora',
                                                                                       'formwidth': '25%'}))
    finalidadviaje = forms.CharField(label=u"Finalidad y Objetivo del Viaje",
                                     widget=forms.Textarea(attrs={'rows': '2'}), required=False)
    tiempoviaje = forms.TimeField(label=u"Tiempo de Viaje", required=False, initial='00:00', input_formats=['%H:%M'],
                                  widget=DateTimeInput(format='%H:%M',
                                                       attrs={'class': 'selectorhora', 'formwidth': '50%'}))
    numeropersonas = forms.IntegerField(label=u"Número de Personas", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    responsablegira = forms.ModelChoiceField(
        Persona.objects.filter(Q(administrativo__isnull=False) | Q(profesor__isnull=False), status=True),
        label=u"Profesor o funcionario Responsable", widget=forms.Select(attrs={'formwidth': '100%'}), required=False)
    # departamentosolicitante = forms.ModelChoiceField(Departamento.objects.filter(integrantes__isnull=False,status=True).distinct(), label=u"Unidad Académica o Departamento", widget=forms.Select(attrs={'formwidth': '100%'}), required=False)


class SolicitudVehiculoObservacionForm(forms.Form):
    observacion = forms.CharField(widget=forms.Textarea, label=u'Observación', required=False)


class SolicitudVehiculo2Form(forms.Form):
    cantonsalida = forms.ModelChoiceField(Canton.objects.filter(status=True), label=u"Cantón Salida",
                                          widget=forms.Select(attrs={'formwidth': '50%'}), required=False)
    cantondestino = forms.ModelChoiceField(Canton.objects.filter(status=True), label=u"Cantón Destino",
                                           widget=forms.Select(attrs={'formwidth': '50%'}), required=False)
    fechasalida = forms.DateField(label=u"Fecha de Salida", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '25%'}))
    fechallegada = forms.DateField(label=u"Fecha de LLegada", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                                   widget=DateTimeInput(format='%d-%m-%Y',
                                                        attrs={'class': 'selectorfecha', 'formwidth': '25%'}))
    horasalida = forms.TimeField(label=u"Hora de Salida desde", required=False, initial=str(datetime.now().time())[:5],
                                 input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                               attrs={'class': 'selectorhora',
                                                                                      'formwidth': '25%'}))
    horaingreso = forms.TimeField(label=u"Hora de LLegada", required=False, initial=str(datetime.now().time())[:5],
                                  input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                                attrs={'class': 'selectorhora',
                                                                                       'formwidth': '25%'}))
    finalidadviaje = forms.CharField(label=u"Finalidad y Objetivo del Viaje",
                                     widget=forms.Textarea(attrs={'rows': '2'}), required=False)
    tiempoviaje = forms.TimeField(label=u"Tiempo de Viaje", required=False, initial='00:00', input_formats=['%H:%M'],
                                  widget=DateTimeInput(format='%H:%M',
                                                       attrs={'class': 'selectorhora', 'formwidth': '50%'}))
    numeropersonas = forms.IntegerField(label=u"Número de Personas", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    responsablegira = forms.ModelChoiceField(
        Persona.objects.filter(Q(administrativo__isnull=False) | Q(profesor__isnull=False), status=True),
        label=u"Profesor o funcionario Responsable", widget=forms.Select(attrs={'formwidth': '100%'}), required=False)
    departamentosolicitante = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(),
        label=u"Unidad Académica o Departamento", widget=forms.Select(attrs={'formwidth': '100%'}), required=False)


class SolicitudVehiculoDetalleForm(forms.Form):
    from sagest.models import DIAS
    transporteinstitucional = forms.BooleanField(initial=False, label=u'Transporte Institucional?', required=False)
    vehiculo = forms.ModelChoiceField(VehiculoUnemi.objects.filter(status=True, estado=1), label=u"Vehiculo",
                                      widget=forms.Select(attrs={'formwidth': '100%'}), required=False)
    conductor = forms.ModelChoiceField(
        Persona.objects.filter(status=True, distributivopersona__denominacionpuesto_id=112), label=u"Conductor",
        widget=forms.Select(attrs={'formwidth': '100%'}), required=False)
    fechainicio = forms.DateField(label=u"Fecha Inicio Autorizado", initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha de Caducidad", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y',
                                                    attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    laborable = forms.BooleanField(initial=False, label=u'Laborable?', required=False)
    dia = forms.ChoiceField(label=u"Dia", required=False, choices=DIAS,
                            widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '40%'}))
    horadesde = forms.TimeField(label=u"Hora Desde", required=False, initial=str(datetime.now().time())[:5],
                                input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                              attrs={'class': 'selectorhora',
                                                                                     'formwidth': '30%'}))
    horahasta = forms.TimeField(label=u"Hora Hasta", required=False, initial=str(datetime.now().time())[:5],
                                input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M',
                                                                              attrs={'class': 'selectorhora',
                                                                                     'formwidth': '30%'}))
    observacion = forms.CharField(label=u"Observación", widget=forms.Textarea(attrs={'rows': '2'}), required=False)
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 4Mb, en formato pdf',
                           ext_whitelist=(".pdf"), max_upload_size=4194304, required=False)


class VehiculoUnemiForm(forms.Form):
    vehiculo = forms.ModelChoiceField(ActivoFijo.objects.filter(status=True, catalogo_id__in=[2263, 2265, 2267]),
                                      label=u"Vehiculo", widget=forms.Select(attrs={'formwidth': '100%'}),
                                      required=False)
    descripcion = forms.CharField(label=u'Descripción', max_length=300,
                                  widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    matricula = forms.CharField(label=u'# Matrícula', max_length=50, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                required=False)
    aceite = forms.IntegerField(label=u"Cambio de Aceite", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    kilometraje = forms.IntegerField(label=u"Kilometraje", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    estado = forms.ChoiceField(label=u"Estado", required=False, choices=ESTADO_VEHICULO,
                               widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '50%'}))


class DocumentoInscripcionForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=200, required=False)
    tipo = forms.ModelChoiceField(label=u"Tipo Archivo", queryset=TipoArchivo.objects.filter(vigente=True),
                                  required=False, widget=forms.Select(attrs={'class': 'imp-75'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                           ext_whitelist=(".doc", ".docx", ".pdf", ".jpg", ".png"), max_upload_size=4194304)

    # archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 4Mb, en formato pdf',ext_whitelist=(".pdf"), max_upload_size=4194304)

    def ocultar_nombre(self):
        del self.fields['nombre']


class OtroMeritoForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre", max_length=300, widget=forms.TextInput(attrs={'col': '12','placeholder':'Describa el nombre del mérito'}), required=True)
    institucion = forms.CharField(label=u"Institución", max_length=300, widget=forms.TextInput(attrs={'col': '12', 'placeholder':'Describa la institución donde recibio el mérito'}),
                                  required=True)
    fecha = forms.DateField(label=u"Fecha", required=True,
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '12'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                           ext_whitelist=(".doc", ".docx", ".pdf", ".jpg", ".png"), max_upload_size=4194304,
                           required=False)

    def ocultar_nombre(self):
        del self.fields['nombre']


# CURSOS CAPACITACION GENERADO POR IPEC
class CapPeriodoIpecForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=True)
    descripcion = forms.CharField(label=u'Descripción', max_length=1000, widget=forms.Textarea(attrs={'rows': '3'}),
                                  required=True)
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'], required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], required=False,
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    archivo = ExtFileField(label=u'Archivo',
                           help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"),
                           max_upload_size=12582912, required=False)
    instructivo = ExtFileField(label=u'instructivo',
                           help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"),
                           max_upload_size=12582912, required=False)

    def editar_grupo(self):
        deshabilitar_campo(self, 'fechainicio')
        deshabilitar_campo(self, 'fechafin')

    def ocultar_nombre(self):
        del self.fields['nombre']


class CapEventoIpecForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=True)


class CapTurnoIpecForm(forms.Form):
    turno = forms.IntegerField(label=u"Turno", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '33%'}))
    horainicio = forms.TimeField(label=u"Hora Inicio", required=True, initial=str("07:00"), input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    horafin = forms.TimeField(label=u'Hora Fin', required=True, initial=str("08:00"), input_formats=['%H:%M'],
                              widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    horas = forms.IntegerField(label=u"Horas", required=False, initial=1, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '33%'}))

    def editar_grupo(self):
        deshabilitar_campo(self, 'horas')

    def editar_turno(self):
        deshabilitar_campo(self, 'turno')


class CapConfiguracionIpecForm(forms.Form):
    minnota = forms.IntegerField(label=u"Minimo Calificación", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    minasistencia = forms.IntegerField(label=u"Minimo Asistencia", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    aprobado2 = forms.IntegerField(initial=0, required=False, label=u'Valida IPEC',
                                   widget=forms.TextInput(attrs={'select2search': 'true'}))
    aprobado3 = forms.IntegerField(initial=0, required=False, label=u'Aprueba',
                                   widget=forms.TextInput(attrs={'select2search': 'true'}))

    def editar(self, aprobador2, aprobador3):
        self.fields['aprobado2'].widget.attrs['descripcion'] = aprobador2[
            0].flexbox_repr_con_cargo() if aprobador2 else ""
        self.fields['aprobado2'].widget.attrs['value'] = aprobador2[0].id if aprobador2 else ""
        self.fields['aprobado3'].widget.attrs['descripcion'] = aprobador3[
            0].flexbox_repr_con_cargo() if aprobador3 else ""
        self.fields['aprobado3'].widget.attrs['value'] = aprobador3[0].id if aprobador3 else ""


class CapEventoPeriodoIpecForm(forms.Form):
    from sga.models import Aula
    periodo = forms.ModelChoiceField(label=u'Período', required=False,
                                     queryset=CapPeriodoIpec.objects.filter(status=True), widget=forms.Select())
    capevento = forms.ModelChoiceField(label=u'Evento', queryset=CapEventoIpec.objects.filter(status=True),
                                       required=True, widget=forms.Select())
    tipootrorubro = forms.IntegerField(initial=0, required=False, label=u'Tipo Rubro',
                                       widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Área Conocimiento",
                                              queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=True,
                                              widget=forms.Select(attrs={'class': 'imp-75'}))
    contextocapacitacion = forms.ModelChoiceField(label=u"Contexto de la Capacitación/Formación",
                                                  queryset=ContextoCapacitacion.objects.all(), required=False,
                                                  widget=forms.Select())
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    aula = forms.ModelChoiceField(label=u'Aula', required=True, queryset=Aula.objects.filter(status=True),
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    enfoque = forms.ModelChoiceField(label=u'Enfoque', required=True,
                                     queryset=CapEnfocadaIpec.objects.filter(status=True),
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    modalidad = forms.ChoiceField(label=u"Modalidad Capacitación", required=False, choices=MODALIDAD_CAPACITACION,
                                  widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '50%'}))
    tipoparticipacion = forms.ModelChoiceField(label=u"Tipo Aprobación", queryset=TipoParticipacion.objects.all(),
                                               required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    tipocertificacion = forms.ModelChoiceField(label=u"Tipo Certificación", queryset=TipoCertificacion.objects.all(),
                                               required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    tipocapacitacion = forms.ModelChoiceField(label=u"Programado Plan Institucional",
                                              queryset=TipoCapacitacion.objects.all(), required=False,
                                              widget=forms.Select(attrs={'formwidth': '50%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                    attrs={
                                                                                                        'class': 'selectorfecha',
                                                                                                        'formwidth': '50%'}))
    fechainiinscripcion = forms.DateField(label=u"Fecha Inicio Inscripción", required=False, input_formats=['%d-%m-%Y'],
                                          widget=DateTimeInput(format='%d-%m-%Y',
                                                               attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafininscripcion = forms.DateField(label=u"Fecha Fin Inscripción", required=False, input_formats=['%d-%m-%Y'],
                                          widget=DateTimeInput(format='%d-%m-%Y',
                                                               attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechamaxpago = forms.DateField(label=u"Fecha Max Pago", input_formats=['%d-%m-%Y'],
                                   widget=DateTimeInput(format='%d-%m-%Y',
                                                        attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechacertificado = forms.CharField(label=u"Fecha certificado", required=False,
                                       widget=forms.TextInput(attrs={'formwidth': '50%'}))
    horas = forms.IntegerField(label=u"Horas Académica", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    cupo = forms.IntegerField(label=u"Cupo", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    minnota = forms.IntegerField(label=u"Mínimo Calificación", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    minasistencia = forms.IntegerField(label=u"Mínimo Asistencia", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    costo = forms.DecimalField(label=u'Costo Interno $', required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%'}))
    costoexterno = forms.DecimalField(label=u'Costo Externo $', required=False,
                                      widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '5'}), required=True)
    objetivo = forms.CharField(label=u'Objetivo General', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    # contenido = forms.CharField(label=u'Contenido', widget=forms.Textarea(attrs={'rows': '7'}), required=True)
    contenido = forms.CharField(label=u'Contenido', widget=CKEditorUploadingWidget(), required=True)
    aprobado2 = forms.CharField(label=u'Aprobador 2', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                required=False)
    aprobado3 = forms.CharField(label=u'Aprobador 3', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                required=False)
    visualizar = forms.BooleanField(initial=True, label=u'Visualizar Evento', required=False)
    publicarinscripcion = forms.BooleanField(initial=True, label=u'Inscripción Online', required=False)
    envionotaemail = forms.BooleanField(initial=False, label=u'Envío de nota al email', required=False)
    modeloevaludativoindividual = forms.BooleanField(initial=False, label=u'Modelo Evaluativo Individual?',
                                                     required=False)
    notificarubro = forms.BooleanField(initial=False, label=u'Notificar Rubro?',required=False)
    seguimientograduado = forms.BooleanField(initial=False, label=u'Seguimiento Graduado?',required=False)
    mes=forms.ChoiceField(choices=MESES_CHOICES,label=u"Mes Seleccionado", required=False,widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '40%'}))
    # imagen = ExtFileField(label=u'Seleccione imagen logo aval', required=False,  help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)
    imagen = ExtFileField(label=mark_safe(
        u'<a href="javascript:;" class="btn btn-info tu" title="Ver imagen logo aval" id="view_imagen"><i class="fa fa-picture-o"></i></a>&nbsp;Seleccione imagen logo aval'),
        required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png',
        ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)
    banner = ExtFileField(label=mark_safe(
        u'<a href="javascript:;" class="btn btn-info tu" title="Ver banner" id="view_banner"><i class="fa fa-picture-o"></i></a>&nbsp;Seleccione banner'),
        required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png',
        ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)
    brochure = ExtFileField(label=u'Brochure', help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                           ext_whitelist=(".doc", ".docx", ".pdf", ".jpg", ".png"), max_upload_size=4194304,
                           required=False)

    def editar_grupo(self):
        deshabilitar_campo(self, 'periodo')
        deshabilitar_campo(self, 'aprobado2')
        deshabilitar_campo(self, 'aprobado3')

    def editar_responsable(self, responsable):
        self.fields['responsable'].widget.attrs['descripcion'] = responsable.flexbox_repr() if responsable else ""
        self.fields['responsable'].widget.attrs['value'] = responsable.id if responsable else ""

    def editar_rubro_deshabilitar(self):
        campo_solo_lectura(self, 'costo')
        campo_solo_lectura(self, 'costoexterno')

    # def editar_rubro_habilitar(self):
    #     habilitar_campo(self, 'costo')
    #     habilitar_campo(self, 'costoexterno')

class ConfigurarcionMejoraContinuaForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=140, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    cargo = forms.CharField(label="Cargo", max_length=140, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    firma = ExtFileField(label=u'Archivo Firma', required=True, help_text=u'Tamaño Maximo permitido 6Mb, en formato  png', ext_whitelist=(".png",),max_upload_size=6291456)
    orden = forms.IntegerField(initial=0, label=u'Orden', required=True, widget=forms.NumberInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    curso = forms.ModelChoiceField(CapEventoPeriodoIpec.objects.filter(status=True), label=u'Evento', required=False,
                               widget=forms.Select(attrs={'formwidth': '100%'}))

    def deshabilitar(self):
        del self.fields['curso']

    def chek_file(self, file, file_n):
        if not file_n and file:
            del self.fields['firma']

class CapEventoPeriodoIpecFacturaTotalForm(forms.Form):
    from sga.models import Aula
    subtotal = forms.DecimalField(label=u'SubTotal $', required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '100%'}))
    iva = forms.DecimalField(label=u'Iva $', required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '100%'}))
    # total = forms.DecimalField(label=u'Total $',required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '100%'}))
    archivo = ExtFileField(label=u'Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png',
                           ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)

    # def deshabilitar(self):
    #     # deshabilitar_campo(self, 'total')


class CapEnfocadaIpecForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=True)


class CapInstructorIpecForm(forms.Form):
    instructor = forms.IntegerField(initial=0, required=False, label=u'Instructor',
                                    widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '95%'}))
    nombrecurso = forms.CharField(label=u'Nombre curso moodle', max_length=500,
                                  widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    instructorprincipal = forms.BooleanField(initial=False, label=u'Principal?', required=False)

    def editar(self, capinstructor):
        self.fields['instructor'].widget.attrs[
            'descripcion'] = capinstructor.instructor.flexbox_repr() if capinstructor.instructor else ""
        self.fields['instructor'].widget.attrs[
            'value'] = capinstructor.instructor.id if capinstructor.instructor else ""


class CapClaseIpecForm(forms.Form):
    from sga.models import DIAS_CHOICES
    capeventoperiodo = forms.CharField(label=u'Evento', max_length=500,
                                       widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    turno = forms.ModelChoiceField(CapTurnoIpec.objects.filter(status=True), required=False, label=u'Turno',
                                   widget=forms.Select())
    dia = forms.ChoiceField(label=u"Dia", required=False, choices=DIAS_CHOICES,
                            widget=forms.Select(attrs={'class': 'imp-25'}))
    instructor = forms.ModelChoiceField(label=u"Instructor", required=False,
                                        queryset=CapInstructorIpec.objects.filter(status=True).order_by('instructor'),
                                        widget=forms.Select(attrs={'formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                    attrs={
                                                                                                        'class': 'selectorfecha',
                                                                                                        'formwidth': '50%'}))

    def editar_grupo(self):
        deshabilitar_campo(self, 'capeventoperiodo')

    def editar_turno(self):
        deshabilitar_campo(self, 'turno')
        deshabilitar_campo(self, 'dia')

    def cargar_instructores(self, eventoperiodo):
        self.fields['instructor'].queryset = CapInstructorIpec.objects.filter(status=True,
                                                                              capeventoperiodo=eventoperiodo).order_by(
            'instructor__apellido1', 'instructor__apellido2', 'instructor__nombres')

    def editar_instructor(self):
        deshabilitar_campo(self, 'instructor')


class CapInscribirIpecForm(forms.Form):
    participante = forms.IntegerField(initial=0, required=False, label=u'Participante',
                                      widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '90%'}))


class CapInscribirIpecForm2(forms.Form):
    participante = forms.ModelChoiceField(label=u"Participante", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=True, widget=forms.Select())

class GenerarRubroDiferidoForm(forms.Form):
    participante = forms.CharField(label=u"Participante", required=True, widget=forms.TextInput(attrs={'formwidth':'100%', 'readonly': True}))
    valor = forms.CharField(label=u"Valor a diferir", required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%', 'readonly': True}))
    cuota = forms.IntegerField(initial=0, label=u'N° de cuotas', required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    fechavence = forms.DateField(label=u"Vencimiento", required=False, initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '100%'}))

class CapInscribirPersonaIpecForm(forms.Form):
    from sga.models import Sexo
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=True,
                             widget=forms.TextInput(attrs={'formwidth': '50%'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=True,
                              widget=forms.TextInput(attrs={'formwidth': '50%'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=True,
                                widget=forms.TextInput(attrs={'formwidth': '50%'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=True,
                                widget=forms.TextInput(attrs={'formwidth': '50%'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=True,
                            widget=forms.TextInput(attrs={'formwidth': '50%'}))
    telefono = forms.CharField(label=u"Teléfono móvil", max_length=50, required=True,
                               widget=forms.TextInput(attrs={'formwidth': '50%'}))
    telefono_conv = forms.CharField(label=u"Teléfono fijo", max_length=50, required=True,
                                    widget=forms.TextInput(attrs={'formwidth': '50%'}))
    nacimiento = forms.DateField(label=u"Fecha nacimiento", required=True, input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y',
                                                      attrs={'class': 'selectorfecha', 'formwidth': '33%'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", queryset=Sexo.objects.all(),
                                  widget=forms.Select(attrs={'formwidth': '50%'}))
    direccion = forms.CharField(label=u'Dirección', max_length=100, required=True,
                                widget=forms.TextInput(attrs={'formwidth': '50%'}))
    lugarestudio = forms.CharField(label=u'Lugar de estudio', max_length=300, required=False,
                                   widget=forms.TextInput(attrs={'formwidth': '50%'}))
    carrera = forms.CharField(label=u'Carrera', max_length=300, required=False,
                              widget=forms.TextInput(attrs={'formwidth': '50%'}))
    profesion = forms.CharField(label=u'Profesión', max_length=300, required=False,
                                widget=forms.TextInput(attrs={'formwidth': '50%'}))
    institucionlabora = forms.CharField(label=u'Institución donde labora', max_length=300, required=False,
                                        widget=forms.TextInput(attrs={'formwidth': '50%'}))
    cargodesempena = forms.CharField(label=u'Cargo que desempeña', max_length=300, required=False,
                                     widget=forms.TextInput(attrs={'formwidth': '50%'}))
    esparticular = forms.BooleanField(initial=True, label=u'Es particular?', required=False,
                                      widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))

    def adicionar_instructor(self):
        del self.fields['lugarestudio']
        del self.fields['carrera']
        del self.fields['profesion']
        del self.fields['cargodesempena']
        del self.fields['esparticular']
        del self.fields['institucionlabora']


class CapAsistenciaIpecForm(forms.Form):
    clase = forms.ModelChoiceField(CapClaseIpec.objects.filter(status=True), required=False, label=u'Horario',
                                   widget=forms.Select())
    profesor = forms.CharField(label=u'Profesor', max_length=500, required=False,
                               widget=forms.TextInput(attrs={'formwidth': '100%'}))
    fechaadicionar = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                      attrs={
                                                                                                          'class': 'selectorfecha',
                                                                                                          'formwidth': '20%'}),
                                     required=False)

    def adicionar(self, eventoperiodo):
        self.fields['clase'].queryset = CapClaseIpec.objects.filter(capeventoperiodo=eventoperiodo).order_by('dia')
        deshabilitar_campo(self, 'profesor')


class CapNotaIpecForm(forms.Form):
    profesor = forms.CharField(label=u'Profesor', max_length=500, required=False,
                               widget=forms.TextInput(attrs={'formwidth': '100%'}))
    modelo = forms.ModelChoiceField(label=u"Modelo Evaluativo", required=True,
                                    queryset=CapModeloEvaluativoTareaIpec.objects.filter(status=True),
                                    widget=forms.Select(attrs={'formwidth': '100%'}))

    def deshabilitar_profesor(self):
        deshabilitar_campo(self, 'profesor')


class CapNotaDocenteForm(forms.Form):
    profesor = forms.CharField(label=u'Profesor', max_length=500, required=False,
                               widget=forms.TextInput(attrs={'formwidth': '100%'}))
    modelo = forms.ModelChoiceField(label=u"Modelo Evaluativo", required=True,
                                    queryset=CapModeloEvaluativoDocente.objects.filter(status=True),
                                    widget=forms.Select(attrs={'formwidth': '100%'}))

    def deshabilitar_profesor(self):
        deshabilitar_campo(self, 'profesor')


class CapModeloEvaluativoTareaIpecForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=500, required=True,
                             widget=forms.TextInput(attrs={'formwidth': '75%'}))
    notaminima = forms.FloatField(label=u"Nota Minima", initial="0.00", required=True,
                                  widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))
    notamaxima = forms.FloatField(label=u"Nota Maxima", initial="0.00", required=True,
                                  widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))
    principal = forms.BooleanField(initial=False, label=u'Principal?', required=False)
    evaluacion = forms.BooleanField(initial=False, label=u'Es Evaluación?', required=False)


class CapDetalleModeloEvaluativoTareaIpecForm(forms.Form):
    modelo = forms.ModelChoiceField(label=u"Modelo Evaluativo", required=False,
                                    queryset=CapModeloEvaluativoTareaIpec.objects.filter(status=True),
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    nombre = forms.CharField(label=u"Nombre", max_length=10, required=True,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    notaminima = forms.FloatField(label=u"Nota Mínima", initial="0.00", required=True,
                                  widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))
    notamaxima = forms.FloatField(label=u"Nota Máxima", initial="0.00", required=True,
                                  widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))

    def deshabilitar(self):
        deshabilitar_campo(self, 'modelo')


class SeleccionarInstructorIpecForm(forms.Form):
    tipo = forms.ChoiceField(label=u"Tipo reporte", required=True, choices=TIPO_REPORTE_IPEC,
                             widget=forms.Select(attrs={'class': 'imp-90'}))
    instructor = forms.ModelChoiceField(label=u"Instructor", required=True,
                                        queryset=CapInstructorIpec.objects.filter(status=True).order_by('instructor'),
                                        widget=forms.Select(attrs={'formwidth': '100%'}))

    def seleccionar(self):
        self.fields['instructor'].queryset = CapInstructorIpec.objects.filter(status=None)


class CondicionBienForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=100, required=True,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea({'rows': '3'}))


class EstadoBienForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=100, required=True,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea({'rows': '3'}))


class EdificioForm(forms.Form):
    from sagest.models import Bloque

    codigobien = forms.CharField(label=u"Código Gobierno", required=False, max_length=50,
                                 widget=forms.TextInput(attrs={'formwidth': '50%'}))
    codigoanterior = forms.CharField(initial='', label=u"Código Interno", required=False, max_length=50,
                                     widget=forms.TextInput(attrs={'formwidth': '50%'}))
    identificador = forms.CharField(label=u"Identificador", required=False, max_length=50,
                                    widget=forms.TextInput(attrs={'formwidth': '50%'}))
    fechaingreso = forms.DateField(label=u"Fecha ingreso", required=False, initial=datetime.now().date(),
                                   input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                    attrs={'class': 'selectorfecha',
                                                                                           'formwidth': '30%'}))
    catalogo = forms.IntegerField(initial=0, required=False, label=u'Catalogo Bien',
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    identificacion = forms.ModelChoiceField(Bloque.objects.filter(status=True), required=False, label=u'Identificación',
                                            widget=forms.Select(attrs={'formwidth': '100%', 'separator': 'true'}))
    caracteristica = forms.CharField(label=u"Modelo/Cracteristica del Bien", max_length=200, required=False,
                                     widget=forms.Textarea({'rows': '3'}))
    propietario = forms.CharField(label=u"Propietario Registrado en el Municipio", max_length=200, required=False,
                                  widget=forms.Textarea({'rows': '2'}))
    critico = forms.BooleanField(initial=False, label=u'Crítico', required=False,
                                 widget=forms.CheckboxInput(attrs={'formwidth': '23%'}))
    valorcompra = forms.DecimalField(initial="0.00", label=u'Valor Compra', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'formwidth': '30%', 'decimal': '2'}))
    clavecatastral = forms.CharField(label=u"Clave Catastral", required=False, max_length=50,
                                     widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '18%'}))
    numeropredio = forms.CharField(label=u"Número predio", required=False, max_length=20,
                                   widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '70%'}))
    numeropiso = forms.IntegerField(initial=0, label=u'Número de piso', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    areaconstruccion = forms.DecimalField(initial="0.00", label=u'Área Construcción(mts)', required=False,
                                          widget=forms.TextInput(
                                              attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    numeroescritura = forms.CharField(label=u"Número Escritura", required=False, max_length=50,
                                      widget=forms.TextInput(attrs={'formwidth': '50%'}))
    fechaescritura = forms.DateField(label=u"Fecha escritura", required=False, initial=datetime.now().date(),
                                     input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'class': 'selectorfecha',
                                                                                             'formwidth': '50%'}))
    notaria = forms.CharField(required=False, label=u'Notaría', max_length=50, widget=forms.TextInput())
    condicionbien = forms.ModelChoiceField(CondicionBien.objects.filter(status=True), required=False,
                                           label=u'Condición del Bien', widget=forms.Select(attrs={'formwidth': '50%'}))
    estadobien = forms.ModelChoiceField(EstadoBien.objects.filter(status=True), required=False,
                                        label=u'Estado del Bien', widget=forms.Select(attrs={'formwidth': '50%'}))
    cuentacontable = forms.ModelChoiceField(CuentaContable.objects.filter(activosfijos=True), required=False,
                                            label=u'Cuenta Contable', widget=forms.Select(attrs={'formwidth': '50%'}))
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable Bien',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    custodio = forms.IntegerField(initial=0, required=False, label=u'Custodio Bien',
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    vidautil = forms.IntegerField(initial=0, label=u'Años de Vida útil', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '35%'}))
    depreciable = forms.BooleanField(initial=True, required=False, label=u"Deprecia",
                                     widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    valorcontable = forms.DecimalField(initial="0.00", label=u'Valor Contable', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'formwidth': '35%', 'decimal': '2'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '3'}))


class ReporteEdificioFrom(forms.Form):
    cuentacontable = forms.ModelChoiceField(CuentaContable.objects.filter(activosfijos=True), required=False,
                                            label=u'Cuenta Contable', widget=forms.Select(attrs={'formwidth': '50%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'formwidth': '50%'}))


# becas docente
class ProyectoBecasForm(forms.Form):
    proyecto = forms.CharField(label=u'Proyecto', max_length=300, required=False, widget=forms.Textarea({'rows': '2'}))
    garante = forms.ModelChoiceField(Persona.objects.filter(status=True, profesor__isnull=False), label=u'Garante',
                                     required=False, widget=forms.Select())
    universidad = forms.ModelChoiceField(InstitucionEducacionSuperior.objects.filter(status=True), label=u'Universidad',
                                         required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    titulo = forms.CharField(label=u'Título', max_length=300, required=False, widget=forms.Textarea({'rows': '2'}))
    formadepagos = forms.ChoiceField(label=u"Forma Pago", required=True, choices=FORMAS_PAGO,
                                     widget=forms.Select(attrs={'class': 'imp-90'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'formwidth': '50%'}))
    representantelegal = forms.ModelChoiceField(
        Persona.objects.filter(status=True, distributivopersona__estadopuesto__id=1,
                               distributivopersona__denominacionpuesto__id=113), label=u'Representante Legal',
        required=False, widget=forms.Select())


class CategoriaRubroBecaForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", required=False, widget=forms.TextInput(attrs={'formwidth': '100%'}))


class RubroBecaForm(forms.Form):
    nombre = forms.CharField(label=u"Descripción", required=False, widget=forms.TextInput())
    categoriarubrobeca = forms.ModelChoiceField(CategoriaRubroBeca.objects.filter(status=True), required=False,
                                                label=u'Categoria Rubro-Beca',
                                                widget=forms.Select(attrs={'formwidth': '100%'}))


class DetalleBecaDocenteForm(forms.Form):
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '40%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'formwidth': '40%'}))
    mesesviaje = forms.IntegerField(initial=0, label=u'Duración (Meses)', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '20%'}))


class DetalleBecaDocenteAdendumForm(forms.Form):
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '40%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'formwidth': '40%'}))
    mesesviaje = forms.IntegerField(initial=0, label=u'Duración (Meses)', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '20%'}))

    def editar(self):
        deshabilitar_campo(self, 'fechainicio')
        deshabilitar_campo(self, 'fechafin')
        deshabilitar_campo(self, 'mesesviaje')


class DetalleRubroBecaDocenteArchivoForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=300, required=False,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 40Mb, en formato doc, docx, xls, xlsx, pdf, ppt, pptx, rar, zip, txt',
                           ext_whitelist=(
                               ".doc", ".docx", ".xls", ".xlsx", ".pdf", ".ppt", ".pptx", ".zip", ".rar", ".txt"),
                           max_upload_size=41943040)


class ArchivoBecaDocenteForm(forms.Form):
    archivo = ExtFileField(label=u'Subir Archivo', required=True,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304, widget=FileInput({'accept': 'application/pdf'}))


class DetalleBecaDocenteLiquidacionForm(forms.Form):
    archivoliquidacion = ExtFileField(label=u'Seleccione Archivo', required=False,
                                      help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf',
                                      ext_whitelist=(".pdf",), max_upload_size=10485760)
    observacionliquidacion = forms.CharField(label="Observación",
                                             widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}),
                                             required=False)


class DetalleBecaDocentePresupuestoForm(forms.Form):
    archivopresupuesto = ExtFileField(label=u'Seleccione Archivo', required=False,
                                      help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf',
                                      ext_whitelist=(".pdf",), max_upload_size=10485760)
    observacionpresupuesto = forms.CharField(label="Observación",
                                             widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}),
                                             required=False)


class TareaMantenimientoFrom(forms.Form):
    categoria = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True), required=True, label=u'Categoria',
                                       widget=forms.Select(attrs={'formwidth': '50%'}))
    descripcion = forms.CharField(label=u"Descripción", required=True, widget=forms.TextInput())


class TareaMantenimientoDaniosForm(forms.Form):
    categoria = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True), required=True, label=u'Categoria',
                                       widget=forms.Select(attrs={'formwidth': '50%'}))
    descripcion = forms.CharField(label=u"Descripción", required=True, widget=forms.TextInput())


class PaisForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=100, required=True, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código SENESCYT", max_length=10, required=True, widget=forms.TextInput())
    codigosniese = forms.CharField(label=u"Código SNIESE", max_length=10, required=True, widget=forms.TextInput())
    nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=True, widget=forms.TextInput())
    codigonacionalidad = forms.CharField(label=u"Código Nacionalidad", max_length=10, required=True,
                                         widget=forms.TextInput())
    codigo_tthh = forms.IntegerField(initial=0, label=u'Código TTHH', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))


class AreaConocimientoTitulacionForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre", max_length=200, required=True, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código", max_length=10, required=True, widget=forms.TextInput())
    codigocaces = forms.CharField(label=u"Código CACES", max_length=10, required=True, widget=forms.TextInput())
    tipo = forms.ChoiceField(label=u"Tipo Área", required=True, choices=TIPO_AREA,
                             widget=forms.Select(attrs={'class': 'imp-90 '}))


class ProvinciaForm(forms.Form):
    pais = forms.ModelChoiceField(Pais.objects.filter(status=True), required=False, label=u'País',
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    nombre = forms.CharField(label=u"Nombre", max_length=100, required=True, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código SENESCYT", max_length=10, required=True, widget=forms.TextInput())
    codigosniese = forms.CharField(label=u"Código SNIESE", max_length=10, required=True, widget=forms.TextInput())
    codigo_tthh = forms.IntegerField(initial=0, label=u'Código TTHH', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))


class SubAreaConocimientoTitulacionForm(FormModeloBase):
    areaconocimiento = forms.ModelChoiceField(AreaConocimientoTitulacion.objects.filter(status=True, vigente=True), required=True,
                                              label=u'Área Conocimiento',
                                              widget=forms.Select(attrs={'formwidth': '100%'}))
    nombre = forms.CharField(label=u"Nombre", max_length=100, required=True, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código", max_length=10, required=True, widget=forms.TextInput())
    codigocaces = forms.CharField(label=u"Código CACES", max_length=10, required=True, widget=forms.TextInput())
    tipo = forms.ChoiceField(label=u"Tipo Área", required=True, choices=TIPO_AREA, widget=forms.Select(attrs={'class': 'imp-90 '}))
    vigente = forms.BooleanField(initial=True, label=u'Vigente?', required=False,
                                 widget=forms.CheckboxInput(attrs={'data-switchery':True,'col':'12',}))


class SubAreaEspecificaConocimientoTitulacionForm(FormModeloBase):
    areaconocimiento = forms.ModelChoiceField(SubAreaConocimientoTitulacion.objects.filter(status=True, vigente=True), required=True,
                                              label=u'Sub Área Conocimiento',
                                              widget=forms.Select(attrs={'formwidth': '100%'}))
    nombre = forms.CharField(label=u"Nombre", max_length=100, required=True, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código", max_length=10, required=True, widget=forms.TextInput())
    codigocaces = forms.CharField(label=u"Código CACES", max_length=10, required=True, widget=forms.TextInput())
    tipo = forms.ChoiceField(label=u"Tipo Área", required=True, choices=TIPO_AREA,
                             widget=forms.Select(attrs={'class': 'imp-90'}))
    vigente = forms.BooleanField(initial=True, label=u'Vigente?', required=False,
                                 widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '12', }))


class VersionMatizCineForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre", max_length=200, required=True, widget=forms.TextInput())
    anio = forms.CharField(label=u"anio", max_length=10, required=True, widget=forms.TextInput(attrs={'formwidth': '20%'}))
    vigente = forms.BooleanField(initial=True, required=False, label=u"¿Vigente?",
                                     widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
class CantonForm(forms.Form):
    provincia = forms.ModelChoiceField(Provincia.objects.filter(status=True), required=False, label=u'Provincia',
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    nombre = forms.CharField(label=u"Nombre", max_length=100, required=True, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código SENESCYT", max_length=10, required=True, widget=forms.TextInput())
    codigosniese = forms.CharField(label=u"Código SNIESE", max_length=10, required=True, widget=forms.TextInput())
    codigo_tthh = forms.IntegerField(initial=0, label=u'Código TTHH', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))
    codigo_distrito = forms.CharField(label=u"Código DISTRITO", max_length=10, required=False, widget=forms.TextInput())
    circuito = forms.CharField(label=u"Circuito", max_length=10, required=False, widget=forms.TextInput())
    zona = forms.ModelChoiceField(Zona.objects.filter(status=True), required=False, label=u'Zona',
                                  widget=forms.Select(attrs={'formwidth': '100%'}))


class ParroquiaForm(forms.Form):
    pais = forms.ModelChoiceField(Pais.objects.filter(status=True), required=False, label=u'Pais',
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    provincia = forms.ModelChoiceField(Provincia.objects.filter(status=True), required=False, label=u'Provincia',
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    canton = forms.ModelChoiceField(Canton.objects.filter(status=True), required=False, label=u'Canton',
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    nombre = forms.CharField(label=u"Nombre", max_length=100, required=True, widget=forms.TextInput())
    codigo = forms.CharField(label=u"Código SENESCYT", max_length=10, required=True, widget=forms.TextInput())
    codigosniese = forms.CharField(label=u"Código SNIESE", max_length=10, required=True, widget=forms.TextInput())
    codigonotaria = forms.CharField(label=u"Código Notaria", max_length=10, required=False, widget=forms.TextInput())
    codigo_tthh = forms.IntegerField(initial=0, label=u'Código TTHH', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '100%'}))

    def editar(self, parroquia):
        self.fields['provincia'].queryset = Provincia.objects.filter(status=True,
                                                                     pais_id=parroquia.canton.provincia.pais.id)
        self.fields['canton'].queryset = Canton.objects.filter(status=True, provincia_id=parroquia.canton.provincia.id)


# CAMBIOS ULTIMOS
class MantenimientosActivosGarantiaForm(forms.Form):
    # activofijo = forms.IntegerField(initial=0, required=True, label=u'Activo fijo', widget=forms.TextInput(attrs={'select2search': 'true'}))
    tipoactivo = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True), required=True,
                                        label=u'Tipo de Activo', widget=forms.Select(attrs={'formwidth': '100%'}))

    estusu = forms.BooleanField(label=u'Usuario entrego el equipo', required=False,
                                widget=CheckboxInput(attrs={'checked': 'True', 'formwidth': '50%'}))
    archivo = ExtFileField(label=u'Adjuntar archivo de evidencia de comunicado', required=False,
                           help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=2194304)
    arcusen = ExtFileField(label=u'Adjuntar ficha de mantenimiento', required=False,
                           help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=2194304)

    proveedor = forms.IntegerField(initial=0, required=True, label=u'Proveedor',
                                   widget=forms.TextInput(attrs={'select2search': 'true'}))
    numreporte = forms.CharField(label=u'Número secuencia reporte', required=False, max_length=500,
                                 widget=forms.TextInput())
    fechainicio = forms.DateField(label=u"Fecha de ejecución", initial=datetime.now().date(), required=False,
                                  input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'formwidth': '35%'}))
    # fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=False,input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '35%'}))
    valor = forms.DecimalField(label=u'Valor sin IVA', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'formwidth': '100%', 'placeholder': '0.00'}))
    # archivo = ExtFileField(label=u'Subir Archivo', required=False, help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=2194304)

    horamax = forms.CharField(label=u'Hora', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    minutomax = forms.CharField(label=u'Minutos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '70%'}))
    estfrec = forms.BooleanField(label=u'Funciona al recibir', required=False,
                                 widget=CheckboxInput(attrs={'formwidth': '50%'}))
    estfent = forms.BooleanField(label=u'Funciona al entregar', required=False,
                                 widget=CheckboxInput(attrs={'formwidth': '50%'}))
    observacion = forms.CharField(label=u'Observación', required=True, widget=forms.Textarea({'rows': '2'}))


class MantenimientosActivosPreventivosForm(forms.Form):
    tipoactivo = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True), required=True,
                                        label=u'Tipo de Activo', widget=forms.Select(attrs={'formwidth': '100%'}))
    estusu = forms.BooleanField(label=u'Usuario entrego el equipo', required=False,
                                widget=CheckboxInput(attrs={'formwidth': '50%'}))
    archivo = ExtFileField(label=u'Adjuntar archivo de evidencia de comunicado', required=False,
                           help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=2194304)
    fecha = forms.DateField(label=u"Fecha de mantenimiento", initial=datetime.now().date(), required=False,
                            input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',
                                                                             attrs={'class': 'selectorfecha',
                                                                                    'formwidth': '100%'}))
    horamax = forms.CharField(label=u'Hora', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    minutomax = forms.CharField(label=u'Minutos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '70%'}))
    estfrec = forms.BooleanField(label=u'Funciona al recibir', required=False,
                                 widget=CheckboxInput(attrs={'formwidth': '50%'}))
    estfent = forms.BooleanField(label=u'Funciona al entregar', required=False,
                                 widget=CheckboxInput(attrs={'formwidth': '50%'}))
    marca = forms.CharField(label=u"Marca", required=False, widget=forms.TextInput(attrs={'formwidth': '50%'}))
    modelo = forms.CharField(label=u"Modelo", required=False, widget=forms.TextInput(attrs={'formwidth': '50%'}))
    piezaparte = forms.ModelChoiceField(queryset=HdPiezaPartes.objects.filter(status=True).order_by('descripcion'),
                                        required=False, label=u'Pieza y Parte')
    danioenc = forms.ModelChoiceField(
        queryset=MantenimientoGruDanios.objects.filter(status=True).order_by('descripcion'), required=False,
        label=u'Daños encontrados')

    bsugiere = forms.BooleanField(label=u'Se sugiere baja del equipo', required=False,
                                  widget=CheckboxInput(attrs={'formwidth': '50%'}))
    dsugiere = forms.CharField(label=u"Sugerencia de baja", required=False,
                               widget=forms.TextInput(attrs={'formwidth': '100%'}))
    observacion = forms.CharField(label=u'Observación', required=True, widget=forms.Textarea({'rows': '2'}))

    def cargar_mantenimiento(self, mantenimiento):
        # self.fields['piezaparte'].queryset = HdPiezaPartes.objects.filter(id__in=list(mantenimiento.piezaparteactivospreventivos_set.filter(status=True).values_list('piezaparte_id', flat=True)))
        self.fields['piezaparte'].queryset = HdPiezaPartes.objects.filter(status=True,
                                                                          grupocategoria_id=mantenimiento.tipoactivo,
                                                                          estado=1)


# CAJA CHICA
class CajaChicaForm(forms.Form):
    descripcion = forms.CharField(required=False, label=u'Descripcion',
                                  widget=forms.TextInput(attrs={'class': 'imp', 'formwidth': '100%'}))
    valor = forms.DecimalField(initial="0.00", label=u'Valor ', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    valormaximo = forms.DecimalField(initial="0.00", label=u'Valor máximo por comprobante', required=False,
                                     widget=forms.TextInput(
                                         attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    custodio = forms.IntegerField(initial=0, required=True, label=u'Custodio',
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    verificador = forms.IntegerField(initial=0, required=True, label=u'Verificador',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    departamento = forms.ModelChoiceField(Departamento.objects.filter(status=True), required=False,
                                          label=u'Departamento', widget=forms.Select(attrs={'formwidth': '100%'}))

    def adicionar(self):
        self.fields['custodio'].widget.attrs['descripcion'] = "seleccione custodio"
        self.fields['verificador'].widget.attrs['descripcion'] = "seleccione verificador"
        departamentos = Departamento.objects.filter(status=True)
        lista = []
        for d in departamentos:
            if d.integrantes.count() < 1:
                lista.append(d.id)
        self.fields['departamento'].queryset = Departamento.objects.filter(status=True).exclude(id__in=lista)

    def editar(self, caja):
        self.fields['custodio'].widget.attrs['value'] = caja.custodio.id if caja.custodio else ""
        self.fields['custodio'].widget.attrs['descripcion'] = caja.custodio.flexbox_repr() if caja.custodio else ""
        self.fields['verificador'].widget.attrs['value'] = caja.verificador.id if caja.verificador else ""
        self.fields['verificador'].widget.attrs[
            'descripcion'] = caja.verificador.flexbox_repr() if caja.verificador else ""
        departamentos = Departamento.objects.filter(status=True)
        lista = []
        for d in departamentos:
            if d.integrantes.count() < 1:
                lista.append(d.id)
        self.fields['departamento'].queryset = Departamento.objects.filter(status=True).exclude(id__in=lista)


class PartidaCajaChicaForm(forms.Form):
    cajachica = forms.ModelChoiceField(CajaChica.objects.filter(status=True), required=False, label=u'Caja Chica',
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    partida = forms.ModelChoiceField(Partida.objects.filter(status=True), required=False, label=u'Partida',
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    valorinicial = forms.DecimalField(initial="0.00", label=u'Valor inicial', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))


class SolicitudCajaChicaForm(forms.Form):
    solicita = forms.ModelChoiceField(CajaChica.objects.filter(status=True), required=False, label=u'Solicita',
                                      widget=forms.Select(attrs={'formwidth': '100%'}))
    partidacajachica = forms.ModelChoiceField(PartidaCajaChica.objects.filter(status=True), required=False,
                                              label=u'Partida', widget=forms.Select(attrs={'formwidth': '100%'}))
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    concepto = forms.CharField(label=u'Concepto', required=False, widget=forms.Textarea({'rows': '2'}))

    def edit(self, solicita):
        self.fields['solicita'].initial = CajaChica.objects.filter(custodio=solicita)[0].id
        self.fields['solicita'].widget.attrs['value'] = CajaChica.objects.filter(custodio=solicita)[0].id
        self.fields['solicita'].widget.attrs['descripcion'] = CajaChica.objects.filter(custodio=solicita)[0]

    def addcustodio(self, persona):
        self.fields['partidacajachica'].queryset = PartidaCajaChica.objects.filter(status=True,
                                                                                   cajachica__custodio=persona)
        self.fields['valor'].initial = CajaChica.objects.filter(custodio=persona)[0].valor
        del self.fields['solicita']


class ComprobanteCajaChicaForm(forms.Form):
    cajachica = forms.ModelChoiceField(CajaChica.objects.filter(status=True), required=False, label=u'Solicita',
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    concepto = forms.CharField(label=u'Concepto', required=False, widget=forms.Textarea({'rows': '2'}))

    def edit(self, solicita):
        self.fields['cajachica'].initial = CajaChica.objects.filter(custodio=solicita)[0].id
        self.fields['cajachica'].widget.attrs['value'] = CajaChica.objects.filter(custodio=solicita)[0].id
        self.fields['cajachica'].widget.attrs['descripcion'] = CajaChica.objects.filter(custodio=solicita)[0]

    def addcustodio(self, porcentaje):
        self.fields['valor'].initial = porcentaje
        # self.fields['valor'].initial = CajaChica.objects.filter(custodio=solicita)[0].valormaximo
        del self.fields['cajachica']

    def editcustodio(self):
        del self.fields['cajachica']


class ComprobanteCajaChicaLiquidacionForm(forms.Form):
    numeroretencion = forms.CharField(label=u'N° Retención', required=False, max_length=20,
                                      widget=forms.TextInput(attrs={'formwidth': '40%', 'class': 'imp-comprobantes'}))
    numerofactura = forms.CharField(label=u'N° Factura', required=False, max_length=20,
                                    widget=forms.TextInput(attrs={'formwidth': '40%', 'class': 'imp-comprobantes'}))
    fecha = forms.DateField(label=u"Fecha documento", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '100%'}))
    base0 = forms.DecimalField(initial="0.00", label=u'Base 0', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    baseiva = forms.DecimalField(initial="0.00", label=u'Base Iva', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    ivacausado = forms.DecimalField(initial="0.00", label=u'Iva Causado', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    ivaretenido = forms.DecimalField(initial="0.00", label=u'Iva Retenido', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    impuestoretenido = forms.DecimalField(initial="0.00", label=u'Impuesto Retenido', required=False,
                                          widget=forms.TextInput(
                                              attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    total = forms.DecimalField(initial="0.00", label=u'Total', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    observacion = forms.CharField(label=u'Concepto', required=False, widget=forms.Textarea({'rows': '2'}))
    valorcomprobante = forms.DecimalField(initial="0.00", label=u'Valor Comprobante', required=False,
                                          widget=forms.TextInput(
                                              attrs={'class': 'imp-number', 'formwidth': '30%', 'decimal': '2'}))
    valorcumplido = forms.DecimalField(initial="0.00", label=u'Valor Cumplido', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '30%', 'decimal': '2'}))
    valorfaltante = forms.DecimalField(initial="0.00", label=u'Valor Faltante', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '40%', 'decimal': '2'}))

    def add(self, comprobante, valorcumplido):
        self.fields['valorcomprobante'].initial = comprobante.valor
        self.fields['valorcumplido'].initial = valorcumplido
        self.fields['valorfaltante'].initial = comprobante.valor - valorcumplido


class ReposicionCajaChicaForm(forms.Form):
    cajachica = forms.ModelChoiceField(CajaChica.objects.filter(status=True), required=False, label=u'Caja Chica',
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    solicitudcajachica = forms.ModelChoiceField(SolicitudCajaChica.objects.filter(status=True, estadosolicitud=3),
                                                required=False, label=u'Solicitud aprobada',
                                                widget=forms.Select(attrs={'formwidth': '100%'}))

    def porcustodio(self):
        del self.fields['cajachica']


class CertificadoPersonaForm(FormModeloBase):
    nombres = forms.CharField(label=u'Nombre de la certificación', max_length=500, required=True,
                              widget=forms.TextInput(attrs={'col':'6'}))
    autoridad_emisora = forms.CharField(label=u'Autoridad emisora de la certificación', required=True,
                                        widget=forms.TextInput(attrs={'col':'6'}))
    numerolicencia = forms.CharField(label=u'Número de la licencia', required=False, widget=forms.TextInput(attrs={'col':'6'}))
    enlace = forms.CharField(label=u'URL de la certificación', required=False, widget=forms.TextInput(attrs={'col':'6'}))
    vigente = forms.BooleanField(label=u'Esta certificación no vence', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    fechadesde = forms.DateField(label=u"Fecha Inicio", required=False, initial=datetime.now().date(),
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    fechahasta = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(),
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=2194304, widget=FileInput({'accept': 'application/pdf','col':'6'}))

    def editar(self, certificado):
        if certificado.vigente == True:
            deshabilitar_campo(self, 'fechahasta')


class HdPiezaPartesForm(forms.Form):
    grupocategoria = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True), required=True,
                                            label=u'Tipo de Activo', widget=forms.Select(attrs={}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '2'}), required=False)
    estado = forms.ChoiceField(label=u"Estado", required=True, choices=ESTADO_PARTES,
                               widget=forms.Select(attrs={'class': 'imp-90'}))
    archivo = ExtFileField(label=u'Imagen', required=False,
                           help_text=u'Tamaño Maximo permitido 2Mb, en formato jpg,jpeg,png',
                           ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=2194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))


class HdSolicitudPiezaPartesForm(forms.Form):
    grupocategoria = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True).order_by('descripcion'),
                                            required=False, label=u'Categoria', widget=forms.Select(attrs={}))
    piezaparte = forms.ModelChoiceField(HdPiezaPartes.objects.filter(status=True).order_by('descripcion'),
                                        required=True, label=u'Pieza y Parte', widget=forms.Select(attrs={}))
    tipo = forms.CharField(label=u'Tipo', max_length=300, required=False, widget=forms.TextInput())
    capacidad = forms.CharField(label=u'Capacidad', max_length=300, required=False, widget=forms.TextInput())
    velocidad = forms.CharField(label=u'Velocidad', max_length=300, required=False, widget=forms.TextInput())
    descripcion = forms.CharField(label=u"Especificaciones extras", max_length=1000,
                                  widget=forms.Textarea(attrs={'rows': '2', 'with': '100%'}), required=False)


class HdMaterialForm(forms.Form):
    codigo = forms.CharField(label=u"Codigo", max_length=100, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=False)
    nombre = forms.CharField(label=u'Nombre', max_length=300, required=True, widget=forms.TextInput())


class HdUnidadMedidaForm(forms.Form):
    name_key = forms.CharField(label=u"Nombre ID", max_length=100, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                               required=False)
    name = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput())


class HdUnidadMedidaMaterialForm(forms.Form):
    unidad_medida = forms.ModelChoiceField(HdUnidadMedida.objects.filter(status=True), required=True,
                                           label=u'Unidad de Medida', widget=forms.Select(attrs={}))


class HdRequerimientoPiezaPartesForm(forms.Form):
    tipoactivo = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True), required=True,
                                        label=u'Tipo de Activo', widget=forms.Select(attrs={'formwidth': '100%'}))
    solicitudes = forms.ModelChoiceField(HdPiezaPartes.objects.filter(status=True), required=True,
                                         label=u'Piezas y Partes', widget=forms.Select(attrs={}))
    # listasolicitudes = forms.ModelChoiceField(HdSolicitudesPiezaPartes.objects.filter(status=True), required=True, label=u'Descripción', widget=forms.Select(attrs={}))
    fecha = forms.DateField(label=u"Fecha", required=False, initial=datetime.now().date(),
                            input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))


class HdRequerimientosPiezaPartesForm(forms.Form):
    codigoresuelve = forms.CharField(label=u'Codigo', max_length=300, required=False, widget=forms.TextInput())
    observacionresuelve = forms.CharField(label=u'Observacion', widget=forms.Textarea(attrs={'rows': '3'}),
                                          required=False)


class HdCausasForm(forms.Form):
    tipoincidente = forms.ModelChoiceField(label=u'Tipo de incidente',
                                           queryset=HdTipoIncidente.objects.filter(status=True), required=False,
                                           widget=forms.Select(attrs={'formwidth': '100%'}))
    nombre = forms.CharField(label=u'Nombre', max_length=300, required=False, widget=forms.TextInput())


class HdCabEncuestasForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=50, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=False)
    descripcion = forms.CharField(label=u"Descripción", max_length=1000,
                                  widget=forms.Textarea(attrs={'rows': '2', 'with': '100%'}), required=False)
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)


class HdDetEncuestasForm(forms.Form):
    pregunta = forms.ModelChoiceField(label=u'Pregunta', queryset=HdPreguntas.objects.filter(status=True),
                                      required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    tiporespuesta = forms.ModelChoiceField(label=u'Tipo Respuesta', queryset=TipoRespuesta.objects.filter(status=True),
                                           required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)


class AprobacionMarcadasForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '2'}), required=False)


class InformeMensualForm(FormModeloBase):
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True, initial=datetime.now().date(),
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha fin", required=True, initial=datetime.now().date(),
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea(attrs={'rows': '2'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Máximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))


class BienesServiciosInsumosPacForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea(attrs={'rows': '2'}))
    tipo = forms.ChoiceField(label=u"Tipo", required=True, choices=TIPO_PRODUCTO_PAC_INGRESO,
                             widget=forms.Select(attrs={'class': 'imp-90'}))


class HdPreciosForm(forms.Form):
    cierresolicitudes = forms.ModelChoiceField(label=u'Fechas Activas',
                                               queryset=HdFechacierresolicitudes.objects.filter(activo=True,
                                                                                                status=True),
                                               required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    valor = forms.DecimalField(initial='0.0000', label=u'Precio Referencial', required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)


class HdFechacierreForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea(attrs={'rows': '5'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True, initial=datetime.now().date(),
                                  input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechafin = forms.DateField(label=u"Fecha fin", required=True, initial=datetime.now().date(),
                               input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)


class ModuloForm(forms.Form):
    # sistema = forms.ModelChoiceField(ReqSistema.objects.filter(status=True), required=True,label=u'Sistema', widget=forms.Select(attrs={}))
    url = forms.CharField(max_length=100, label=u'URL', required=False)
    nombre = forms.CharField(max_length=100, label=u'Nombre', required=False)
    icono = forms.CharField(max_length=200, label=u'Icono', required=False)
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    activo = forms.BooleanField(label=u'Activo', required=False)
    sga = forms.BooleanField(label=u'Activo para SGA', required=False)
    sagest = forms.BooleanField(label=u'Activo para SAGEST', required=False)
    posgrado = forms.BooleanField(label=u'Activo para POSGRADO', required=False)
    # estado = forms.ChoiceField(label=u"Estado", required=False, choices=ESTADO_MODULO, widget=forms.Select(attrs={'class': 'imp-90'}))

    # def adicionar(self):
    #     del self.fields['estado']


class ReqActividadForm(forms.Form):
    orden = forms.IntegerField(initial=0, label=u'Orden', required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    nombre = forms.CharField(max_length=100, label=u'Nombre', required=False)
    vigente = forms.BooleanField(label=u'Vigente', initial=True, required=False)


class AnexoInformeForm(forms.Form):
    tipoanexo = forms.ChoiceField(label=u"Tipo de Anexo", required=False, choices=TIPO_ANEXO_INFORME, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '50%'}))
    descripcion = forms.CharField(max_length=100, label=u'Descripción', required=False)
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))


class PrioridadForm(forms.Form):
    codigo = forms.CharField(label=u'Código', widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '30%'}),
                             required=False)
    nombre = forms.CharField(label=u'Nombre de prioridad',
                             widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '70%'}), required=False)
    hora = forms.CharField(label=u'Hora', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '33%'}))
    minuto = forms.CharField(label=u'Minutos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '33%'}))
    segundo = forms.CharField(label=u'Segundos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '33%'}))
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False,
                          help_text=u'Tamaño Máximo permitido 4Mb, en formato  jpg ,jpeg, png',
                          ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)

    def editar(self):
        deshabilitar_campo(self, 'codigo')

    def ocultarimagen(self):
        del self.fields['imagen']


class ReqHistoriaForm(forms.Form):
    modulo = forms.ModelChoiceField(queryset=Modulo.objects.filter(status=True), required=False, label=u'Módulo',
                                    widget=forms.Select(attrs={'formwidth': '60%'}))
    prioridad = forms.ModelChoiceField(queryset=ReqPrioridad.objects.filter(status=True), required=False,
                                       label=u'Prioridad', widget=forms.Select(attrs={'formwidth': '40%'}))
    solicita = forms.IntegerField(initial=0, label=u'Solicitante', required=False,
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    asunto = forms.CharField(label=u'Asunto', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    cuerpo = forms.CharField(label=u"Descripción", required=False, widget=CKEditorUploadingWidget())
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf',
                           ext_whitelist=(".pdf",), max_upload_size=10485760,
                           widget=FileInput({'accept': 'application/pdf'}))

    def adicionar(self):
        self.fields['solicita'].widget.attrs['descripcion'] = "seleccione administrativo"

    def editar(self, solicita):
        self.fields['solicita'].widget.attrs['descripcion'] = u"%s - %s" % (
            solicita.persona, solicita.denominacionpuesto.descripcion)
        self.fields['solicita'].initial = solicita.id
        self.fields['solicita'].widget.attrs['value'] = solicita.id

    def adicionarexperto(self):
        del self.fields['solicita']
        del self.fields['prioridad']


class ResponsableForm(forms.Form):
    responsable = forms.IntegerField(initial=0, required=True, label=u'Responsable',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))


class ResponsableActivoForm(forms.Form):
    persona = forms.ModelChoiceField(label=u"Responsable a asignar", queryset=Persona.objects.filter(Q(status=True) & (Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False))).distinct().order_by('apellido1', 'apellido2', 'nombres'), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    responsableactual = forms.CharField(initial=0,label=u'Responsable actual', required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%','disabled':True}))
    activo = forms.CharField(initial=0,label=u'Activo', required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%','disabled':True}))

class InventarioActivoForm(forms.Form):
    activotecnologico = forms.ModelChoiceField(label=u"Activos Tecnológicos", queryset=ActivoTecnologico.objects.filter(
                                                                                                                  Q(catalogo__equipoelectronico=True) &
                                                                                                                  Q(catalogo__status=True) &
                                                                                                                  Q(activotecnologico__statusactivo=1) &
                                                                                                                  Q(status=True)),
                                                                                        required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    responsableactual = forms.CharField(label=u'Responsable actual', required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%', 'disabled': True}))
    activo = forms.CharField(initial=0, label=u'Activo', required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%', 'disabled': True}))
    # movimiento = forms.ChoiceField(label=u"Movimiento", required=False, choices=ESTADO_MOVIMIENTO,
    #                            widget=forms.Select(attrs={'class': 'imp-90'}))
    estadoubicacion = forms.ChoiceField(label=u"Estado ubicación", required=False, choices=ESTADO_UBICACION,
                                   widget=forms.Select(attrs={'class': 'imp-90'}))
    estadofuncionamiento = forms.ChoiceField(label=u"Estado funcionamiento", required=False, choices=ESTADO_FUNCIONAMIENTO,
                                   widget=forms.Select(attrs={'class': 'imp-90'}))
    estadouso = forms.ChoiceField(label=u"Estado uso", required=False, choices=ESTADO_USO_AT, widget=forms.Select(attrs={'class': 'imp-90'}))
    estadogeneral = forms.ModelMultipleChoiceField(label=u"Requerimiento", queryset=EstadosGeneralesInventarioAT.objects.filter(status=True),
                                               required=False, widget=forms.SelectMultiple(attrs={'class': 'imp-100'}))
    observacion = forms.CharField(label=u'Observacion', required=False,
                                     widget=forms.Textarea(attrs={'rows': '5','class': 'imp-100', 'formwidth': '100%', 'placeholder':'Observación del activo'}))

    def editar(self):
        self.fields['activotecnologico'].widget = forms.HiddenInput()
        self.fields['activotecnologico'].label = ""
        self.fields['responsableactual'].widget = forms.HiddenInput()
        self.fields['responsableactual'].label = ""

    def editaractivo(self):
        self.fields['activo'].widget = forms.HiddenInput()
        self.fields['activo'].label = ""

    def editarobservacion(self):
        self.fields['observacion'].widget = forms.HiddenInput()
        self.fields['observacion'].label = ""
        
    def ocultarActivo(self):
        self.fields['activotecnologico'].widget = forms.HiddenInput()
        self.fields['activotecnologico'].label = ""
        # self.fields['responsableactual'].widget.attrs['disabled'] = True
        del self.fields['responsableactual']

    def cargarmultipleestadogeneral(self, id):
        estadosgenerales = InventarioATEstadosGenerales.objects.filter(status=True, inventarioat_id=id)
        idestados = []
        for estadogen in estadosgenerales:
            idestados.append(int(estadogen.estadogeneral_id))
        self.fields['estadogeneral'].initial = idestados
        # self.initial['estadogeneral'] = [2,3]


class PeriodoInventarioATForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre periodo', required=True,widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=True,widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha','col':'6'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=True,widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha','col':'6'}))
    estado = forms.ChoiceField(label=u"Estado", required=False, choices=ESTADO_CIERRE,
                                        widget=forms.Select(attrs={'class': 'select2'}))
    detalle = forms.CharField(label=u'Detalle', required=False,widget=forms.Textarea(attrs={'rows': '5', 'class': 'imp-100','placeholder': 'Detalle del periodo'}))

class EvidenciaPeriodoInventarioTecnologicoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre evidencia', required=True,widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    descripcion = forms.CharField(label=u'Descripción', required=False,widget=forms.Textarea(attrs={'rows': '5', 'class': 'imp-100', 'formwidth': '100%',
                                                               'placeholder': 'Descripción de la evidencia'}))
    evidencia = ExtFileField(label=u'Archivo de evidencia', required=True, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                                                ext_whitelist=(".pdf",), max_upload_size=4194304)

    def renombrar(self):
        self.fields['evidencia'].widget.initial_text = "Anterior"
        self.fields['evidencia'].widget.input_text = "Cambiar"

    def requerirevidencia(self):
        self.fields['evidencia'].required = False

class EstadosGeneralesInventarioATForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción estado general', required=True,widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))

class PrestamoActivoForm(FormModeloBase):
    activotecnologico = forms.IntegerField(initial=0, required=True, label=u'Activo tecnológico', widget=forms.TextInput(attrs={'select2search': 'true'}))
    personaentrega = forms.CharField(label=u'Persona entrega', required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'disabled': True, 'col': '6'}))
    personarecibe = forms.IntegerField(initial=0, required=True, label=u'Persona recibe', widget=forms.TextInput(attrs={'select2search': 'true','col': '6'}))
    desde = forms.DateField(label=u"Fecha desde", initial=datetime.now().date(), required=True,
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    hasta = forms.DateField(label=u"Fecha hasta", initial=datetime.now().date(), required=False,
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    observacion = forms.CharField(label=u'Observación', required=False,
                                     widget=forms.Textarea(attrs={'rows': '5','class': 'form-control', 'placeholder':'Observación del activo'}))

    def cargar_activotecnologico(self, activotecnologico):
        self.fields['activotecnologico'].widget.attrs['descripcion'] = activotecnologico
        self.fields['activotecnologico'].initial = activotecnologico.id
        self.fields['activotecnologico'].widget.attrs['value'] = activotecnologico.id
        self.fields['activotecnologico'].widget.attrs['disabled'] = True

    def cargar_personarecibe(self, personarecibe):
        self.fields['personarecibe'].widget.attrs['descripcion'] = personarecibe
        self.fields['personarecibe'].initial = personarecibe.id
        self.fields['personarecibe'].widget.attrs['value'] = personarecibe.id

    def clean(self):
        cleaned_data = super(PrestamoActivoForm, self).clean()
        activotecnologico =  self.cleaned_data['activotecnologico']
        personarecibe =  self.cleaned_data['personarecibe']
        if activotecnologico == 0:
            self.add_error('activotecnologico', 'Campo requerido')
        if personarecibe == 0:
            self.add_error('personarecibe', 'Campo requerido')
        return cleaned_data

class ReqHistoriaActividadForm(forms.Form):
    # historia = forms.ModelChoiceField(ReqHistoria.objects.filter(status=True), required=True, label=u'Historia', widget=forms.Select(attrs={}))
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable (*)',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    actividad = forms.ModelChoiceField(ReqActividad.objects.filter(status=True), required=False, label=u'Actividad (*)',
                                       widget=forms.Select(attrs={}))
    estado = forms.ChoiceField(label=u"Estado (*)", required=False, choices=ESTADO_HISTORIA,
                               widget=forms.Select(attrs={'class': 'imp-90'}))
    # fechainicio = forms.DateField(label=u"Fecha Inicio (*)", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    # fechafin = forms.DateField(label=u"Fecha Fin (*)", required=False, initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio (*)", required=False, input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechafin = forms.DateField(label=u"Fecha Fin (*)", required=False, input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    descripcion = forms.CharField(label=u'Descripción (*)', required=False, widget=forms.Textarea({'rows': '2'}))

    # def comboResponsable(self, responsable):
    #     self.fields['responsable'].widget.attrs['descripcion'] = u"%s - %s" % (responsable.persona, responsable.denominacionpuesto.descripcion)
    #     self.fields['responsable'].initial = responsable.id
    #     self.fields['responsable'].widget.attrs['value'] = responsable.id


class ResolucionForm(forms.Form):
    numeroresolucion = forms.CharField(label=u'Nº. Resolución', widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                       required=True)
    resuelve = forms.CharField(label=u'Resuelve', required=False, widget=forms.Textarea({'rows': '4'}))
    tipo = forms.ModelChoiceField(label=u'Tipo de resolución', queryset=TipoResolucion.objects.filter(status=True),
                                  required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    fecha = forms.DateField(label=u"Fecha", required=True, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760,
                           widget=FileInput({'accept': 'application/pdf', 'formwidth': '50%'}))


class SeleccionarActivoForm(forms.Form):
    activo = forms.IntegerField(initial=0, required=False, label=u'Seleccionar activo',
                                widget=forms.TextInput(attrs={'select2search': 'true'}))


class IngresoSalidaObrasForm(forms.Form):
    producto = forms.IntegerField(initial=0, required=False, label=u'Producto',
                                  widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'imp-100'}))
    tipomovimiento = forms.ChoiceField(label=u"Tipo Movimiento", required=False, choices=TIPOS_MOVIMIENTO_INVENTARIO,
                                       widget=forms.Select(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    cantidad = forms.DecimalField(initial='0.00', label=u'Cantidad',
                                  widget=forms.TextInput(attrs={'class': 'imp-moneda'}))


class MatrizRetencionForm(forms.Form):
    proveedor = forms.ModelChoiceField(Proveedor.objects.all(), label=u'Proveedor',
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    numerocur = forms.IntegerField(initial=0, label=u'Número cur', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%'}))
    montoretencion = forms.CharField(label=u'Monto retención',
                                     widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '50%'}),
                                     required=True)
    fechaemisionventa = forms.DateField(label=u"Fecha emisión venta", required=True, initial=datetime.now().date(),
                                        input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={
            'class': 'selectorfecha', 'formwidth': '30%'}))
    comprobanteventa = forms.CharField(label=u'Comprobante de venta',
                                       widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '70%'}),
                                       required=False)
    fechaemisionretencion = forms.DateField(label=u"Fecha emisión retención", required=True,
                                            initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                                            widget=DateTimeInput(format='%d-%m-%Y',
                                                                 attrs={'class': 'selectorfecha', 'formwidth': '30%'}))
    comprobanteretencion = forms.CharField(label=u'Comprobante de retención',
                                           widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '70%'}),
                                           required=False)
    archivopdf = ExtFileField(label=u'Archivo pdf', required=False,
                              help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                              max_upload_size=10485760,
                              widget=FileInput({'accept': 'application/pdf', 'formwidth': '50%'}))
    archivoxml = ExtFileField(label=u'Archivo xml', required=False,
                              help_text=u'Tamaño maximo permitido 12Mb, en formato xml', ext_whitelist=(".xml",),
                              max_upload_size=10485760,
                              widget=FileInput({'accept': 'application/pdf', 'formwidth': '50%'}))


# CURSOS FORMACION Y CAPACITACION GENERADO POR TALENTO HUMANO
class CapDocentePeriodoForm(forms.Form):
    tipo = forms.ChoiceField(label=u"Tipo Personal", choices=TIPO_CAPACITACION_UATH, required=False,
                             widget=forms.Select())
    descripcion = forms.CharField(label=u'Descripción', max_length=1000, widget=forms.Textarea(attrs={'rows': '3'}),
                                  required=True)
    resolucion = forms.CharField(label=u'N°Resolución', max_length=150, required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-100'}))
    fechaconvenio = forms.DateField(label=u"Fecha convenio devengación", input_formats=['%d-%m-%Y'], required=False,
                             widget=DateTimeInput(format='%d-%m-%Y',
                                                  attrs={'class': 'selectorfecha', 'formwidth': '100%'}))
    inicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'], required=False,
                             widget=DateTimeInput(format='%d-%m-%Y',
                                                  attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], required=False,
                          widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    monto = forms.DecimalField(initial="0.0000", label=u'Monto', required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    iniciocapacitacion = forms.DateField(label=u"Fecha Inicio Capacitación", input_formats=['%d-%m-%Y'], required=False,
                                         widget=DateTimeInput(format='%d-%m-%Y',
                                                              attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fincapacitacion = forms.DateField(label=u"Fecha Fin Capacitación", input_formats=['%d-%m-%Y'], required=False,
                                      widget=DateTimeInput(format='%d-%m-%Y',
                                                           attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    iniciocapacitaciontecdoc = forms.DateField(label=u"Fecha Inicio Capacitación tecnicos docentes",
                                               input_formats=['%d-%m-%Y'], required=False,
                                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha',
                                                                                              'formwidth': '50%'}))
    fincapacitaciontecdoc = forms.DateField(label=u"Fecha Fin Capacitación tecnicos docentes",
                                            input_formats=['%d-%m-%Y'], required=False,
                                            widget=DateTimeInput(format='%d-%m-%Y',
                                                                 attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    modeloinforme = ExtFileField(label=u'Modelo Informe', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato doc o docx', ext_whitelist=(".doc",".docx"), max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '50%'}))
    resolucionocas = ExtFileField(label=u'Resolución OCAS', required=False,
                                  help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                  max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '50%'}))
    instructivo = ExtFileField(label=u'Instructivo', required=False,
                               help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                               max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '50%'}))
    manualusuario = ExtFileField(label=u'Manual Registro de Solicitud', required=False,
                                 help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                                 max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '50%'}))
    manualregistroevidencia = ExtFileField(label=u'Manual Registro de Evidencia', required=False,
                                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                           ext_whitelist=(".pdf",), max_upload_size=4194304,
                                           widget=forms.FileInput(attrs={'formwidth': '50%'}))

    # conveniodevengacion = ExtFileField(label=u'Convenio Devengación', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato doc o docx', ext_whitelist=(".doc",".docx"), max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '50%'}))

    def editar(self):
        deshabilitar_campo(self, 'monto')
        deshabilitar_campo(self, 'tipo')

    def esparaacademico(self):
        self.fields['tipo'].choices = ((1, 'ACADÉMICOS'),)

    def esparaadministrativo(self):
        self.fields['tipo'].choices = ((2, 'ADMIN/TRAB'),)


class ArticuloInvestigacionForm(forms.Form):
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento",
                                              queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=True,
                                              widget=forms.Select())
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento",
                                                 queryset=SubAreaConocimientoTitulacion.objects.all(), required=True,
                                                 widget=forms.Select())
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento",
                                                           queryset=SubAreaEspecificaConocimientoTitulacion.objects.all(),
                                                           required=True, widget=forms.Select())

    def editar(self, articulo):
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=articulo.areaconocimiento, vigente=True)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=articulo.subareaconocimiento, vigente=True)


# crai
class IngresoActividadesCraiForm(forms.Form):
    tipoactividadcrai = forms.ModelChoiceField(TipoActividadCrai.objects.all(), label=u'Tipo', required=False,
                                               widget=forms.Select(attrs={'class': 'imp-50'}))
    inscripcion = forms.IntegerField(initial=0, required=False, label=u'Inscripcion',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    administrativo = forms.IntegerField(initial=0, required=False, label=u'Administrativo',
                                        widget=forms.TextInput(attrs={'select2search': 'true'}))
    profesor = forms.IntegerField(initial=0, required=False, label=u'Profesor',
                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    actividad = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'maxlength': '400'}), required=False,
                                label=u"Actividad")

    def add(self, tipo_mundo):
        self.fields['tipoactividadcrai'].queryset = TipoActividadCrai.objects.filter(tipo=tipo_mundo, status=True)

    def edit(self, tipo_mundo, ingresoactividadescrai):
        self.fields['tipoactividadcrai'].queryset = TipoActividadCrai.objects.filter(tipo=tipo_mundo, status=True)
        if ingresoactividadescrai.inscripcion:
            self.fields['inscripcion'].initial = ingresoactividadescrai.inscripcion.id
            self.fields['inscripcion'].widget.attrs['value'] = ingresoactividadescrai.inscripcion.id
            self.fields['inscripcion'].widget.attrs['descripcion'] = ingresoactividadescrai.inscripcion
            del self.fields['profesor']
            del self.fields['administrativo']
        else:
            if ingresoactividadescrai.profesor:
                self.fields['profesor'].initial = ingresoactividadescrai.profesor.id
                self.fields['profesor'].widget.attrs['value'] = ingresoactividadescrai.profesor.id
                self.fields['profesor'].widget.attrs['descripcion'] = ingresoactividadescrai.profesor
                del self.fields['inscripcion']
                del self.fields['administrativo']
            else:
                self.fields['administrativo'].initial = ingresoactividadescrai.administrativo.id
                self.fields['administrativo'].widget.attrs['value'] = ingresoactividadescrai.administrativo.id
                self.fields['administrativo'].widget.attrs['descripcion'] = ingresoactividadescrai.administrativo
                del self.fields['inscripcion']
                del self.fields['profesor']


class TipoActividadCraiForm(forms.Form):
    tipo = forms.ChoiceField(choices=TIPO_MUNDO_CRAI, label=u'Tipo', required=False,
                             widget=forms.Select(attrs={'class': 'imp-25'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=1000, widget=forms.Textarea(attrs={'rows': '2'}),
                                  required=True)

    def editar(self):
        deshabilitar_campo(self, 'tipo')


class HdMaterial_IncidenteForm(forms.Form):
    material = forms.ModelChoiceField(label=u"Material:", queryset=HdMateriales.objects.filter(status=True),
                                      required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    cantidad = forms.IntegerField(initial=0, label=u'Cantidad', required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))

class InformeBajaForm(forms.Form):

    solicita = forms.IntegerField(initial=0, required=False, label=u'Solicita',
                                  widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable',
                                     widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    detallerevision = forms.CharField(label=u'Detalle Revisión', required=False,
                                      widget=forms.Textarea(attrs={'rows': '4'}))
    bloque = forms.ModelChoiceField(HdBloque.objects.filter(status=True), label=u'Bloque',
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    estadouso = forms.ChoiceField(label=u"Mal Uso", choices=ESTADO_USO, required=False,
                                  widget=forms.Select(attrs={'formwidth': '60%'}))
    estado = forms.ChoiceField(label=u"Estado", choices=ESTADO_BAJA, required=False,
                               widget=forms.Select(attrs={'formwidth': '60%'}))
    conclusion = forms.CharField(label=u'Conclusión', required=False, widget=forms.Textarea(attrs={'rows': '8'}))

class InformeBajaForm2(forms.Form):

    solicita = forms.IntegerField(initial=0, required=False, label=u'Solicita',
                                  widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable',
                                     widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    detallerevision = forms.CharField(label=u'Detalle Revisión', required=False,
                                      widget=forms.Textarea(attrs={'rows': '4'}))
    bloque = forms.ModelChoiceField(HdBloque.objects.filter(status=True), label=u'Bloque',
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), label=u"departamento")
    gestion = forms.ModelChoiceField(SeccionDepartamento.objects.filter(status=True), label=u"Gestión")
    estadouso = forms.ChoiceField(label=u"Mal Uso", choices=ESTADO_USO, required=False,
                                  widget=forms.Select(attrs={'formwidth': '60%'}))
    estado = forms.ChoiceField(label=u"Estado", choices=ESTADO_BAJA, required=False,
                               widget=forms.Select(attrs={'formwidth': '60%'}))
    conclusion = forms.CharField(label=u'Conclusión', required=False, widget=forms.Textarea(attrs={'rows': '8'}))

class InformeBajaFormAF(FormModeloBase):

    solicita = forms.ModelChoiceField(required=True, label=u'Solicita',
                                      queryset=Persona.objects.select_related().filter(status=True),
                                      widget=forms.Select(attrs={'col':'6'}))
    responsable = forms.ModelChoiceField(required=True, label=u'Responsable de activo',
                                        queryset=Persona.objects.select_related().filter(status=True),
                                        widget=forms.Select(attrs={'col':'6'}))
    departamento = forms.ModelChoiceField(Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(),
                                          label=u"Departamento", widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    gestion = forms.ModelChoiceField(SeccionDepartamento.objects.filter(status=True), label=u"Gestión", required=False,
                                     widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    bloque = forms.ModelChoiceField(HdBloque.objects.filter(status=True), label=u'Bloque',
                                    widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    estadouso = forms.ChoiceField(label=u"Mal Uso", choices=ESTADO_USO, required=False,
                                  widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    estadoactivo = forms.ModelChoiceField(label=u'Estado del activo', required=True,
                                          queryset=EstadoProducto.objects.filter(status=True).exclude(id__in=[4, 5]).order_by('id'),
                                          widget=forms.Select(attrs={'col': '5', 'class': 'select2'}))
    estado = forms.ChoiceField(label=u"Condición del activo", choices=ESTADO_BAJA, required=False,
                               widget=forms.Select(attrs={'col': '5', 'class':'select2'}))
    enuso = forms.BooleanField(label=u'¿Está en uso?', required=False,
                               widget=forms.CheckboxInput(attrs={'col': '2', 'data-switchery': True}))
    detallerevision = forms.CharField(label=u'Detalle Revisión', required=False,
                                      widget=forms.Textarea(attrs={'rows': '4', 'col':'6'}))
    conclusion = forms.CharField(label=u'Conclusión', required=False,
                                 widget=forms.Textarea(attrs={'rows': '4','col':'6'}))


class VerificacionTecnicaForm(FormModeloBase):
    estadoactivo = forms.ModelChoiceField(label=u'Estado del activo', required=True,
                                          queryset=EstadoProducto.objects.filter(status=True).exclude(id__in=[4, 5]).order_by('id'),
                                          widget=forms.Select(attrs={'col': '5', 'class': 'select2'}))
    condicionestado = forms.ChoiceField(label=u"Condición del activo", choices=ESTADO_BAJA, required=True,
                               widget=forms.Select(attrs={'col': '5', 'class': 'select2'}))
    enuso = forms.BooleanField(label=u'¿Está en uso?', required=False,
                               widget=forms.CheckboxInput(attrs={'col': '2', 'data-switchery': True}))
    observacion = forms.CharField(label=u'Observación', required=True, widget=forms.Textarea(attrs={'rows': '2', 'col': '12'}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['observacion'] = cleaned_data.get('observacion').upper().strip()
        return cleaned_data


class ResponsableInformeBajaForm(FormModeloBase):
    responsable = forms.ModelChoiceField(required=True, label=u'Responsable',
                                         queryset=Persona.objects.select_related().filter(status=True),
                                         widget=forms.Select(attrs={'col': '12'}))
    departamento = forms.ModelChoiceField(Departamento.objects.filter(integrantes__isnull=False, status=True).distinct().order_by('id'), required=True,
                                          label=u'Departamento', widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    cargo = forms.CharField(label=u'Cargo', required=True, widget=forms.TextInput(attrs={'col': '12'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), input_formats=['%Y-%m-%d'],
                                  required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], required=False,
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}))
    actual = forms.BooleanField(label=u'¿Activo?', required=False,  widget=forms.CheckboxInput(attrs={'col': '4', 'data-switchery': True}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['cargo'] = cleaned_data.get('cargo').upper().strip()
        return cleaned_data


class DetalleInformeBajaForm(forms.Form):
    detalle = forms.CharField(label=u'Detalle', widget=forms.Textarea(attrs={'rows': '5'}), required=False)


class RamosDocumentoForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760)


class ActivosFijosForm(forms.Form):
    activosfijo = forms.IntegerField(initial=0, required=True, label=u'Activo Fijo',
                                     widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))


class EvidenciaDocumentalForm(FormModeloBase):
    evidencia = forms.CharField(label=u'Evidencia documental', widget=forms.Textarea(attrs={'rows': '5'}),
                                required=True)
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '5'}), required=True)


class InscritoEventoIpecForm(forms.Form):
    from sga.models import Sexo
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u"Nombres", max_length=100, required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-50'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(),
                                  widget=forms.Select(attrs={'formwidth': '40%'}))
    nacimiento = forms.DateField(label=u"Fecha Nacimiento o Constitución", initial=datetime.now().date(),
                                 input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                                 required=False)
    pais = forms.ModelChoiceField(label=u"País residencia", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'formwidth': '75%'}))
    provincia = forms.ModelChoiceField(label=u"Provincia residencia", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '75%'}))
    canton = forms.ModelChoiceField(label=u"Canton residencia", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'formwidth': '75%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia residencia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '75%'}))
    sector = forms.CharField(label=u"Sector", max_length=100, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-50'}))
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-75'}))
    direccion2 = forms.CharField(label=u"Calle Secundaria", max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-75'}))
    num_direccion = forms.CharField(label=u"Numero Domicilio", max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-25'}))
    telefono = forms.CharField(label=u"Telefono Movil", max_length=100, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-25'}))
    telefono_conv = forms.CharField(label=u"Telefono Fijo", max_length=100, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-25'}))
    email = forms.CharField(label=u"Correo Electronico", max_length=240, required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50'}))


class ObservacionInscritoEventoIpecForm(forms.Form):
    observacionmanual = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '3'}))
    archivo = ExtFileField(label=u'Fichero', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf',
                           ext_whitelist=(".pdf",), max_upload_size=10485760)


class MoverInscritoEventoIpecForm(forms.Form):
    # curso = forms.ModelChoiceField(CapEventoPeriodoIpec.objects.filter(status=True, periodo__fechainicio__lte=datetime.now().date(),periodo__fechafin__gte=datetime.now().date()), label=u'Evento', required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    curso = forms.ModelChoiceField(CapEventoPeriodoIpec.objects.filter(status=True), label=u'Evento', required=False,
                                   widget=forms.Select(attrs={'formwidth': '100%'}))
    observacion = forms.CharField(required=False, label=u'Motivo', widget=forms.Textarea({'rows': '3'}))


class MoverInscritoEventoCapacitacionForm(FormModeloBase):
    # curso = forms.ModelChoiceField(CapEventoPeriodoIpec.objects.filter(status=True, periodo__fechainicio__lte=datetime.now().date(),periodo__fechafin__gte=datetime.now().date()), label=u'Evento', required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    curso = forms.ModelChoiceField(CapEventoPeriodoDocente.objects.filter(status=True).distinct('capevento__nombre'), label=u'Evento', required=False,
                                   widget=forms.Select(attrs={'class':'form-control','col': '12'}))
    observacion = forms.CharField(required=False, label=u'Motivo', widget=forms.Textarea({'rows': '3', 'col': '12'}))


class TipoOtroRubroIpecForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=250, required=False,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    partida = forms.ModelChoiceField(Partida.objects.filter(pk=100), initial=100, required=False, label=u'Item',
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    programa = forms.ModelChoiceField(PartidaPrograma.objects.filter(pk=8), initial=8, required=False,
                                      label=u'Programa', widget=forms.Select(attrs={'formwidth': '100%'}))
    unidad_organizacional = forms.ModelChoiceField(Departamento.objects.filter(pk=115), initial=115, required=False,
                                                   label=u'Unidad Or.',
                                                   widget=forms.Select(attrs={'formwidth': '100%'}))
    tipo = forms.ChoiceField(choices=TIPO_RUBRO, initial=2, required=False, label=u'Tipo Rubro',
                             widget=forms.Select(attrs={'formwidth': '100%'}))
    ivaaplicado = forms.ModelChoiceField(IvaAplicado.objects.filter(status=True), required=False, label=u'Iva Aplicado',
                                         widget=forms.Select(attrs={'formwidth': '50%'}))
    valor = forms.DecimalField(label=u"Valor por defecto", required=False, initial="0.00",
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))

    # def editar_rubro_deshabilitar(self):
    #     campo_solo_lectura(self, 'valor')


class ExpertoMatrizValoracionForm(forms.Form):
    experto = forms.IntegerField(initial=0, required=False, label=u'Experto',
                                 widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    denominacion = forms.IntegerField(initial=0, required=False, label=u'Cargo',
                                      widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))


class ExpertoExternoMatrizValoracionForm(forms.Form):
    personaexterna = forms.CharField(label=u"Experto", max_length=500, required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-100'}))
    cargopersonaexterna = forms.CharField(label=u"Cargo", max_length=500, required=False,
                                          widget=forms.TextInput(attrs={'class': 'imp-100'}))


class ArchivoMatrizValoracionForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    archivomatrizvaloracion = ExtFileField(label=u'Subir Archivo', required=False,
                                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                           ext_whitelist=(".pdf",), max_upload_size=4194304,
                                           widget=FileInput({'accept': 'application/pdf'}))


class CongresoForm(FormModeloBase):
    tiporubro = forms.ModelChoiceField(TipoOtroRubro.objects.filter(status=True), label=u'Rubro', required=False,
                                       widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    nombre = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'12'}),
                             required=True)
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'col': '12'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False,
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'col': '12'}))
    fechainicioinscripcion = forms.DateField(label=u"Fecha inicio inscripcion",
                                             required=False,
                                             widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'col': '12', 'type': 'date'}))
    fechafininscripcion = forms.DateField(label=u"Fecha fin inscripcion", required=False,
                                          widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'col': '12', 'type': 'date'}))
    cupo = forms.IntegerField(label=u"Cupo", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%','col':'12'}))
    visualizar = forms.BooleanField(initial=True, label=u'Visualizar concurso', required=False,
                                    widget=forms.CheckboxInput(attrs={'formwidth': '50%', 'col':'12'}))
    gratuito = forms.BooleanField(initial=True, label=u'Es gratuito?', required=False,
                                  widget=forms.CheckboxInput(attrs={'formwidth': '50%', 'col': '12'}))
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf',
                           ext_whitelist=(".pdf",), max_upload_size=10485760,widget=forms.FileInput(attrs={'class':'p-1 text-secondary fs-6 ', 'col':'12'}))
    imagencertificado = ExtFileField(label=u'Imagen de Certificado', required=False,
                                     help_text=u'Tamaño maximo permitido 12Mb, en formato jpg, jpeg, png',
                                     ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=12582912,widget=forms.FileInput(attrs={'class':'p-1 text-secondary fs-6 ', 'col':'12'}))


class TipoParticipanteForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", widget=forms.TextInput(attrs={'class': 'form-control', 'col':'12'}))


class TipoParticipacionCongresoForm(forms.Form):
    tipoparticipante = forms.ModelChoiceField(TipoParticipante.objects.filter(status=True), required=False,
                                              label=u'Tipo Participante',
                                              widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    valor = forms.DecimalField(initial='0.00', label=u'Valor',
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%','col':'12'}))
    archivo = ExtFileField(label=u'Imagen de Certificado', required=False,
                           help_text=u'Tamaño maximo permitido 12Mb, en formato jpg, jpeg, png',
                           ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=12582912, widget=forms.FileInput(attrs={'class':'p-1 text-secondary fs-6 ', 'col':'12'}))


class InscritoCongresoForm(forms.Form):
    persona = forms.IntegerField(initial=0, required=True, label=u'Persona',
                                 widget=forms.TextInput(attrs={'select2search': 'true'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '3'}))


class TemaPonenciaForm(forms.Form):
    tema = forms.CharField(label=u"Tema Ponencia", required=False, widget=forms.TextInput())


class FirmasMatrizValoracionForm(forms.Form):
    personafirma = forms.IntegerField(initial=0, required=False, label=u'Persona',
                                      widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    tipofirma = forms.ChoiceField(choices=TIPO_FIRMAS, label=u'Tipo firma', required=False,
                                  widget=forms.Select(attrs={'class': 'imp-25'}))


class ArchivoMatrizForm(forms.Form):
    numeroinforme = forms.IntegerField(initial=0, label=u'Número informe', required=False,
                                       widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    numeroacta = forms.IntegerField(initial=0, label=u'Número acta', required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    fecha = forms.DateField(label=u"Fecha informe", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    archivo = ExtFileField(label=u'Subir Informe', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304, widget=FileInput({'accept': 'application/pdf'}))


class ArchivoMatrizEvaluacionForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    archivo = ExtFileField(label=u'Subir matriz evaluación', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304, widget=FileInput({'accept': 'application/pdf'}))


class EvaluacionPoaForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=100)
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=False,
                                  input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=False,
                               input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',
                                                                                attrs={'class': 'selectorfecha',
                                                                                       'col': '6'}))
    informeanual = forms.BooleanField(label=u"Informe anual", required=False, initial=True,
                                      widget=forms.CheckboxInput(attrs={'data-switchery': True}))
    # porcentajedesempeno = forms.FloatField(initial=0, label=u'% Desempeño', required=False,
    #                                        widget=forms.TextInput(attrs={'class': 'imp-numbersmall','formwidth': '50%'}))
    # porcentajemeta = forms.FloatField(initial=0, label=u'% Meta', required=False,
    #                                   widget=forms.TextInput(attrs={'class': 'imp-numbersmall','formwidth': '50%'}))


class TipoAccionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                             required=True)


class SecuenciaCapacitacionForm(forms.Form):
    descripcion = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                  required=True)
    secuencia = forms.IntegerField(initial=0, label=u'Secuencia', required=False,
                                   widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    anio = forms.IntegerField(initial=0, label=u'Año', required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    vigente = forms.BooleanField(initial=False, label=u'Vigente?', required=False)


class OpcionSistemaForm(forms.Form):
    descripcion = forms.CharField(label=u'Nombre', max_length=500, widget=forms.TextInput(attrs={'class': 'imp-100'}),
                                  required=True)
    modulo = forms.IntegerField(initial=0, required=False, label=u'Modulo',
                                widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '200px'}))
    visible = forms.BooleanField(initial=False, label=u'Visible?', required=False)

    def editar(self, modulo):
        self.fields['modulo'].widget.attrs['descripcion'] = modulo
        self.fields['modulo'].initial = modulo.id
        self.fields['modulo'].widget.attrs['value'] = modulo.id


class CabCapacitacionForm(forms.Form):
    # secuencia = forms.IntegerField(initial=0, required=False, label=u'Modulo', widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), label=u"departamento")
    seccion = forms.ModelChoiceField(SeccionDepartamento.objects.all(), label=u"Área")
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                            required=False)
    horainicio = forms.TimeField(label=u"Hora Inicio", required=True, initial=str("07:00"), input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    horafin = forms.TimeField(label=u'Hora Fin', required=True, initial=str("08:00"), input_formats=['%H:%M'],
                              widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    antecedente = forms.CharField(label=u'Antecedentes', max_length=500,
                                  widget=forms.TextInput(attrs={'class': 'imp-100'}), required=True)
    tiposistema = forms.ChoiceField(choices=TIPO_SISTEMA, label=u'Sistema', required=False,
                                    widget=forms.Select(attrs={'class': 'imp-25'}))
    tipocapacitacion = forms.ChoiceField(choices=TIPO_CAPACITACION, label=u'Tipo', required=False,
                                         widget=forms.Select(attrs={'class': 'imp-25'}))
    # elaborado = forms.IntegerField(initial=0, required=False, label=u'Elaborado', widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    # verificado =forms.IntegerField(initial=0, required=False, label=u'Verificado', widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    elaborado = forms.ModelChoiceField(Administrativo.objects.filter(status=True),
                                       required=False, label=u'Elaborado',
                                       widget=forms.Select(attrs={'formwidth': '600px'}))
    verificado = forms.ModelChoiceField(Persona.objects.filter(status=True,
                                                               id__in=DistributivoPersona.objects.values_list(
                                                                   'persona_id').filter(status=True, estadopuesto_id=1,
                                                                                        denominacionpuesto_id__in=(569,598,743)).distinct()).distinct(),
                                        required=False, label=u'Verificado',
                                        widget=forms.Select(attrs={'formwidth': '600px'}))
    aprobado = forms.ModelChoiceField(Persona.objects.filter(status=True,
                                                             id__in=DistributivoPersona.objects.values_list(
                                                                 'persona_id').filter(status=True, estadopuesto_id=1,
                                                                                      denominacionpuesto_id=598).distinct()).distinct(),
                                      required=False, label=u'Aprobado',
                                      widget=forms.Select(attrs={'formwidth': '600px'}))
    # responsableadm = forms.ModelMultipleChoiceField(Administrativo.objects.filter(status=True),
    #                                            required=False, label=u'Responsables')

    # def editarsistema(self, sistema):
    #     self.fields['sistema'].widget.attrs['descripcion'] = sistema
    #     self.fields['sistema'].initial = sistema.id
    #     self.fields['sistema'].widget.attrs['value'] = sistema.id
    #
    # def editartipoaccion(self, tipoaccion):
    #     self.fields['tipoaccion'].widget.attrs['descripcion'] = tipoaccion
    #     self.fields['tipoaccion'].initial = tipoaccion.id
    #     self.fields['tipoaccion'].widget.attrs['value'] = tipoaccion.id
    #
    # def editarelaborado(self, elaborado):
    #     self.fields['elaborado'].widget.attrs['descripcion'] = elaborado
    #     self.fields['elaborado'].initial = elaborado.persona.id
    #     self.fields['elaborado'].widget.attrs['value'] = elaborado.persona.id
    # def editarverificado(self, verificado):
    #     self.fields['verificado'].widget.attrs['descripcion'] = verificado
    #     self.fields['verificado'].initial = verificado.id
    #     self.fields['verificado'].widget.attrs['value'] = verificado.id


class ElaboradoForm(forms.Form):
    elaborado = forms.IntegerField(initial=0, required=False, label=u'Elaborado',
                                   widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))

    def editarelaborado(self, elaborado):
        self.fields['elaborado'].widget.attrs['descripcion'] = elaborado
        self.fields['elaborado'].initial = elaborado.id
        self.fields['elaborado'].widget.attrs['value'] = elaborado.id


class VerificadoForm(forms.Form):
    verificado = forms.IntegerField(initial=0, required=False, label=u'Verificado',
                                    widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))

    def editarverificado(self, verificado):
        self.fields['verificado'].widget.attrs['descripcion'] = verificado
        self.fields['verificado'].initial = verificado.id
        self.fields['verificado'].widget.attrs['value'] = verificado.id


class DetResponsableForm(forms.Form):
    # responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    responsable = forms.ModelChoiceField(Administrativo.objects.filter(status=True),
                                         required=False, label=u'Elaborado',
                                         widget=forms.Select(attrs={'formwidth': '600px'}))

    def editarresponsable(self, responsable):
        self.fields['responsable'].widget.attrs['descripcion'] = responsable
        self.fields['responsable'].initial = responsable.id
        self.fields['responsable'].widget.attrs['value'] = responsable.id


class DetParticipanteForm(forms.Form):
    participante = forms.IntegerField(initial=0, required=False, label=u'Participante',
                                      widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    cargo = forms.CharField(label=u'Cargo', required=False, widget=forms.Textarea({'rows': '4'}))

    # cargo = forms.ModelChoiceField(label=u'Cargo', required=False, queryset=DenominacionPuesto.objects.filter(status=True),
    #                                 widget=forms.Select())

    def editarparticipante(self, participante):
        self.fields['participante'].widget.attrs['descripcion'] = participante
        self.fields['participante'].initial = participante.id
        self.fields['participante'].widget.attrs['value'] = participante.id


class DetOpcionForm(forms.Form):
    # opcion = forms.IntegerField(initial=0, required=False, label=u'Opcion',widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    responsable = forms.ModelChoiceField(Administrativo.objects.filter(status=True),
                                         required=False, label=u'Elaborado',
                                         widget=forms.Select(attrs={'formwidth': '600px'}))
    # responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    modulo = forms.ModelChoiceField(label=u'Módulo', required=False, queryset=Modulo.objects.filter(status=True),
                                    widget=forms.Select())
    observacion = forms.CharField(label=u'Opción', required=False, widget=forms.Textarea({'rows': '4'}))

    # def editaropcion(self, opcion):
    #     self.fields['opcion'].widget.attrs['descripcion'] = opcion
    #     self.fields['opcion'].initial = opcion.id
    #     self.fields['opcion'].widget.attrs['value'] = opcion.id

    def editarresponsable(self, responsable):
        self.fields['responsable'].widget.attrs['descripcion'] = responsable
        self.fields['responsable'].initial = responsable.id
        self.fields['responsable'].widget.attrs['value'] = responsable.id

    def editarmodulo(self, modulo):
        self.fields['modulo'].widget.attrs['descripcion'] = modulo
        self.fields['modulo'].initial = modulo.id
        self.fields['modulo'].widget.attrs['value'] = modulo.id


class DetObservacionForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    # responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'controlwidth': '500px'}))
    responsable = forms.ModelChoiceField(Administrativo.objects.filter(status=True),
                                         required=False, label=u'Elaborado',
                                         widget=forms.Select(attrs={'formwidth': '600px'}))
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '100%'}))
    estado = forms.ChoiceField(choices=ESTADO_CAPACITACION, label=u'Estado', required=False,
                               widget=forms.Select(attrs={'class': 'imp-25'}))

    def editarresponsable(self, responsable):
        self.fields['responsable'].widget.attrs['descripcion'] = responsable
        self.fields['responsable'].initial = responsable.id
        self.fields['responsable'].widget.attrs['value'] = responsable.id


class ArchivoCapacitacionForm(forms.Form):
    archivo = ExtFileField(label=u'Archivo Capacitacion', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760)


class ValorMaestriaForm(forms.Form):
    from sga.models import Periodo, Carrera
    periodo = forms.ModelChoiceField(label=u'Período', required=False,
                                     queryset=Periodo.objects.filter(status=True, tipo_id=3), widget=forms.Select())
    carrera = forms.ModelChoiceField(label=u'Carrera', required=False,
                                     queryset=Carrera.objects.filter(status=True, coordinacion__id=7),
                                     widget=forms.Select())
    costo = forms.DecimalField(initial='0.00', label=u'Valor',
                               widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%'}))
    costomatricula = forms.DecimalField(initial='0.00', label=u'Valor matrícula',
                                        widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%'}))


class Formulario107Form(forms.Form):
    anio = forms.IntegerField(initial=datetime.now().year, required=False, label=u"Año",
                              widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    persona = forms.IntegerField(initial=0, required=False, label=u'Persona',
                                 widget=forms.TextInput(attrs={'select2search': 'true'}))
    archivo = ExtFileField(label=u'Formulario PDF', required=False,
                           help_text=u'Tamaño Maximo permitido 3Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=3145728, widget=FileInput({'accept': 'application/pdf'}))

    def editar(self, formulario):
        self.fields['persona'].widget.attrs['descripcion'] = formulario.persona.nombre_completo()
        self.fields['persona'].initial = formulario.persona.id

        deshabilitar_campo(self, 'anio')
        deshabilitar_campo(self, 'persona')


class ImportarFormulario107Form(forms.Form):
    anio = forms.IntegerField(initial=datetime.now().year, required=False, label=u"Año",
                              widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))


class CapacitacionTicsForm(forms.Form):
    departamento = forms.ModelChoiceField(Departamento.objects.all(), label=u"departamento")

    seccion = forms.ModelChoiceField(SeccionDepartamento.objects.all(), label=u"Área")

    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}),
                            required=False)
    horainicio = forms.TimeField(label=u"Hora inicio", input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M',
                                                      attrs={'class': 'selectorhora', 'formwidth': '35%'}))
    horafin = forms.TimeField(label=u"Hora fin", input_formats=['%H:%M'],
                              widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '35%'}))
    tiposistema = forms.ChoiceField(choices=TIPO_SISTEMA, label=u'Sistema', required=False,
                                    widget=forms.Select(attrs={'class': 'imp-25'}))
    tipocapacitacion = forms.ChoiceField(choices=TIPO_CAPACITACION, label=u'Tipo', required=False,
                                         widget=forms.Select(attrs={'class': 'imp-25'}))

    responsable = forms.IntegerField(initial=0, required=False, label=u'Persona Administrativo',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))

    antecedentes = forms.CharField(label=u'Antecedentes', required=False, widget=forms.Textarea({'rows': '2'}))
    opciones = forms.CharField(label=u'Opciones', required=False, widget=forms.Textarea({'rows': '2'}))

    archivo = ExtFileField(label=u'Formulario PDF', required=False,
                           help_text=u'Tamaño Maximo permitido 3Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=3145728, widget=FileInput({'accept': 'application/pdf'}))


class CapAdministrativoForm(forms.Form):
    administrativo = forms.CharField(label=u'Administrativo', required=False,
                                     widget=forms.TextInput({'class': 'imp-100'}))
    rol = forms.CharField(label=u'rol', required=False, widget=forms.TextInput({'class': 'imp-100'}))


class ArchivoDescargaForm(forms.Form):
    estadoacceso = forms.ChoiceField(choices=ESTADO_ARCHIVO, label=u'Accesibilidad', required=False,
                                     widget=forms.Select(attrs={'class': 'imp-25'}))
    nombreprograma = forms.CharField(label=u'Nombre del programa', max_length=100, required=True,
                                     widget=forms.TextInput(attrs={'class': 'imp-100'}))
    version = forms.CharField(label=u'Version', max_length=100, required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-100'}))
    estado = forms.BooleanField(label=u'Visibilidad', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    enlacedescarga = forms.CharField(label=u'Enlace de descarga', max_length=300, required=True,
                                     widget=forms.TextInput(attrs={'class': 'imp-100'}))
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False,
                          help_text=u'Tamaño Máximo permitido 4Mb, en formato  jpg, jpeg, png',
                          ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)


class SolicitudProductoForm(forms.Form):
    codigodocumento = forms.CharField(label=u'Nro.', required=False, widget=forms.TextInput(attrs={'class': 'imp-100',
                                                                                                   'formwidth': '40%'}))
    fechaordenpedido = forms.DateField(label=u"Fecha Orden de Pedido", input_formats=['%d-%m-%Y'], required=False,
                                       widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha',
                                                                                      'labelwidth': '150px',
                                                                                      'formwidth': '40%'}))
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=False,
        label=u'Departamento', widget=forms.Select(attrs={'formwidth': '600px'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=False,
                                         label=u'Responsable',
                                         widget=forms.Select(attrs={'formwidth': '400px', 'labelwidth': '100px'}))
    descripcion = forms.CharField(label=u'Motivo Solicitud', required=False, widget=forms.Textarea(attrs={'rows': '3'}))
    observaciones = forms.CharField(label=u'Observaciones', required=False, widget=forms.Textarea(attrs={'rows': '3'}))

    def adicionar(self):
        deshabilitar_campo(self, 'codigodocumento')
        deshabilitar_campo(self, 'fechaordenpedido')
        deshabilitar_campo(self, 'departamento')
        deshabilitar_campo(self, 'responsable')
        self.fields['responsable'].queryset = Persona.objects.filter(administrativo__isnull=False).filter(id=None)


class SolicitudObservacionForm(forms.Form):
    estados = forms.ChoiceField(label=u'Estado', choices=ESTADOS_SOLICITUD_PRODUCTOS, required=True,
                                widget=forms.Select(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class ModeloEvaluativoGeneralForm(forms.Form):
    orden = forms.IntegerField(initial=0, label=u"Orden", required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    modelo = forms.ModelChoiceField(CapModeloEvaluativoTareaIpec.objects.filter(status=True).order_by('-id'),
                                    required=True,
                                    label=u'Modelo Evaluativo', widget=forms.Select())


class InformeForm(forms.Form):
    codigo = forms.CharField(label=u'Código', widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '70%'}),
                             required=False)
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=False,
        label=u'Departamento al que se da servicio', widget=forms.Select(attrs={'formwidth': '100%'}))
    fecha = forms.DateField(label=u"Fecha de elaboración informe", required=False, initial=datetime.now().date(),
                            input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                             attrs={'class': 'selectorfecha',
                                                                                    'formwidth': '100%'}))
    objetivo = forms.CharField(label=u'Objeto', required=False, widget=forms.Textarea({'rows': '5'}))
    archivo = ExtFileField(label=u'Seleccione Archivo',
                           help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"),
                           required=False, max_upload_size=50485760)

    responsables = forms.ModelMultipleChoiceField(Administrativo.objects.filter(status=True), label=u'Responsables', required=False)

    experto = forms.ModelChoiceField(Persona.objects.filter(status=True, id__in=DistributivoPersona.objects.values_list(
        'persona_id').filter(status=True, estadopuesto_id=1, unidadorganica_id=93).distinct()).distinct(),
                                     required=False, label=u'Experto',
                                     widget=forms.Select(attrs={'formwidth': '600px'}))
    director = forms.ModelChoiceField(Persona.objects.filter(status=True,
                                                             id__in=DistributivoPersona.objects.values_list(
                                                                 'persona_id').filter(status=True, estadopuesto_id=1,
                                                                                      denominacionpuesto_id=598).distinct()).distinct(),
                                      required=False, label=u'Director',
                                      widget=forms.Select(attrs={'formwidth': '600px'}))


class SeguimientoInscripcionForm(forms.Form):
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u"Nombres", max_length=50, required=True,
                              widget=forms.TextInput(attrs={'class': 'imp-50'}))
    correo = forms.CharField(label=u"Correo", max_length=50, required=True,
                             widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefono = forms.CharField(label=u"Teléfono", max_length=50, required=True,
                               widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefono_adicional = forms.CharField(label=u"Teléfono Convencional", max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'class': 'imp-50'}))
    programa = forms.ModelChoiceField(MaestriasAdmision.objects.filter(status=True).distinct(),
                                      required=True, label=u'Programa Maestría',
                                      widget=forms.Select(attrs={'formwidth': '100%'}))
    observacion = forms.CharField(label=u'Detalle', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class SeguimientoHistorialForm(forms.Form):
    from posgrado.models import HISTORIAL_CHOICES

    accion = forms.ChoiceField(label=u'Acción', choices=HISTORIAL_CHOICES, required=True,
                               widget=forms.Select(attrs={'formwidth': '100%'}))
    detalle = forms.CharField(label=u'Detalle', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class BitacoraForm(forms.Form):
    actividades = forms.ModelChoiceField(ActividadesPerfil.objects.filter(status=True),required = False,label='Actividad', widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    tipoactividad = forms.ChoiceField(choices=TIPO_ACTIVIDAD_BITACORA, label=u'Tipo de Actividad',required=False, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    titulo = forms.CharField(max_length=500, label=u"Título", widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}),required=False)
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'col': '6', 'type':'date'}))
    hora = forms.CharField(label=u"Hora Inicio", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3', 'type':'time'}))
    horafin = forms.CharField(label=u"Hora Fín", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3', 'type': 'time', 'valid':False}))
    descripcion = forms.CharField(label=u'Descripción', max_length=10000, widget=forms.Textarea({'row': '3', 'col': '12'}),required=False)
    link = forms.CharField(max_length=1000, label=u"Link", widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}), required=False)
    tiposistema = forms.ChoiceField(choices=TIPO_SISTEMA, label=u'Sistema', required=False, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    departamento_requiriente = forms.ModelChoiceField(Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=False, label=u'Departamento solicita', widget=forms.Select(attrs={'class': 'select2', 'col': '12', 'style':'width:100%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png', ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"), required=False, max_upload_size=12582912, widget=FileInput({'style':'width:100%;', 'class':'form-control', 'col': '12', 'accept': '.doc, .docx,.xls, .xlsx, application/pdf, image/jpeg, image/jpg, image/png'}))

    def ocultarcampos_titulo(self):
        del self.fields['titulo']

    def ocultarcampos_horafin(self):
        del self.fields['horafin']

    def ocultarcampos_tipoactividad(self):
        del self.fields['tipoactividad']

    def ocultarcampos_actividades(self):
        del self.fields['actividades']

    def bloquear_fecha_hora(self):
        self.fields['fecha'].widget.attrs['readonly'] = True
        self.fields['hora'].widget.attrs['readonly'] = True

class VacunacionCovidForm(FormModeloBase):
    # recibiovacuna = forms.BooleanField(label=u'¿Recibió o no la vacuna contra el COVID-19?', required=False,
    #                                    widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    tipovacuna = forms.ModelChoiceField(TipoVacunaCovid.objects.filter(status=True), required=False,
                                        label=u'Tipo de Vacuna', widget=forms.Select(attrs={'formwidth': '100%'}))
    # recibiodosiscompleta = forms.BooleanField(initial=False, label=u'¿Recibió dosis completa?', required=False)
    # fecha_certificado = forms.DateField(label=u"Fecha Emisión Certificado", required=False, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'campofecha', 'formwidth': '100%', 'type': 'date'}))
    certificado = ExtFileField(label=u'Carnet de Vacunación', required=False,
                               help_text=u'Tamaño máximo permitido 4Mb, en formato pdf',
                               ext_whitelist=(".pdf", ".jpg", ".jpeg",), max_upload_size=4194304,
                               widget=forms.FileInput())
    # deseavacunarse = forms.BooleanField(label=u'¿Desea o no ser vacunado?', required=False,
    #                                     widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))

class VacunacionCovidAdmisionForm(FormModeloBase):
    recibiovacuna = forms.BooleanField(label=u'¿Recibió o no la vacuna contra el COVID-19?', required=False,
                                       widget=forms.CheckboxInput(attrs={'col': '12'}))
    tipovacuna = forms.ModelChoiceField(TipoVacunaCovid.objects.filter(status=True), required=False,
                                        label=u'Tipo de Vacuna', widget=forms.Select(attrs={'col': '12'}))
    recibiodosiscompleta = forms.BooleanField(initial=False, label=u'¿Recibió dosis completa?', required=False,
                                              widget=forms.CheckboxInput(attrs={'col': '12'}))
    # fecha_certificado = forms.DateField(label=u"Fecha Emisión Certificado", required=False, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'campofecha', 'formwidth': '100%', 'type': 'date'}))
    certificado = ExtFileField(label=u'Carnet de Vacunación', required=False,
                               help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg',
                               ext_whitelist=(".pdf", ".jpg", ".jpeg",), max_upload_size=4194304,
                               widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))
    deseavacunarse = forms.BooleanField(label=u'¿Desea o no ser vacunado?', required=False,
                                        widget=forms.CheckboxInput(attrs={'col': '12'}))

class PeriodoPlanificacionTHForm(FormModeloBase):
    anio = forms.IntegerField(label=u"Año", required=True,
                              widget=forms.TextInput(attrs={'col': '6'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)
    descripcion = forms.CharField(label=u'Descripción', max_length=10000, widget=forms.Textarea({'row': '3'}),
                                  required=True)
    valorcalculo = forms.DecimalField(initial="0.0000", label=u'Constante y % de impacto', required=True,
                                      widget=forms.TextInput(attrs={'col': '3', 'placeholder': '0.0000'}))


class CabPlanificacionTHForm(FormModeloBase):
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.filter(status=True, integrantes__isnull=False).order_by('id').distinct(),
                                          label=u"Departamento",widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    fecha = forms.DateField(label=u"Fecha",widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '4'}))
    nivelterritorial = forms.ChoiceField(label=u"Nivel territorial", choices=NIVEL_TERRITORIAL_TH, required=False,
                               widget=forms.Select(attrs={'col': '4', 'class': 'select2'}))

    tipoproceso = forms.ChoiceField(label=u'Tipo', choices=TIPO_PROCESO_TH, required=False,
                                    widget=forms.Select(attrs={'col': '4', 'class': 'select2'}))


class CopiarUnidadForm(FormModeloBase):
    periodo = forms.ModelChoiceField(queryset=PeriodoPlanificacionTH.objects.filter(status=True),label=u"Periodo",widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    unidad = forms.ModelChoiceField(queryset=CabPlanificacionTH.objects.filter(status=True),label=u"Unidad",widget=forms.Select(attrs={'col': '12', 'class':'select2'}))

class CambiarEstadoDepartamentoForm(FormModeloBase):
    ESTADOS_PLANTILLA_TH = (
        (1, u'EN PROCESO'),
        (3, u'ENVIADO A UATH'),
        (5, u'VALIDADO UATH'),
        (7, u'RECHAZADO UATH'),
    )
    estado = forms.ChoiceField(label=u"Estado", choices=ESTADOS_PLANTILLA_TH, required=False,
                                  widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
class CambiarAprobarUathForm(FormModeloBase):
    ESTADOS_APROBAR_UATH = (
        (5, u'VALIDAR'),
        (7, u'RECHAZAR'),
    )
    estado = forms.ChoiceField(label=u"Estado", choices=ESTADOS_APROBAR_UATH, required=False,
                                  widget=forms.Select(attrs={'col': '3', 'class':'select2'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea(attrs={'rows': '3','col':'12'}))


class CambiarEstadoGestionPlanificacionTHForm(FormModeloBase):
    ESTADOS_PLANTILLA_TH = (
        (1, u'EN PROCESO'),
        (2, u'ENVIADO A DIRECTOR/A'),
        (4, u'VALIDADO DIRECTOR/A'),
        (6, u'RECHAZADO DIRECTOR/A'),
    )
    estado = forms.ChoiceField(label=u"Estado", choices=ESTADOS_PLANTILLA_TH, required=False,
                               widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))


class MoverGestionForm(FormModeloBase):
    seccion = forms.ModelChoiceField(SeccionDepartamento.objects.filter(departamento__integrantes__isnull=False,departamento__status=True, status=True).distinct(), required=True,
        label=u'Gestión',  widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

    def set_seccion(self, id):
        from sagest.models import SeccionDepartamento
        self.fields['seccion'].initial = SeccionDepartamento.objects.filter(departamento__integrantes__isnull=False,departamento__status=True, status=True).exclude(departamento_id=id).distinct()

class  ImportarActividadesForm(FormModeloBase):
    periodo = forms.ModelChoiceField(queryset=PeriodoPlanificacionTH.objects.filter(status=True), label=u"Periodo", widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    unidad = forms.ModelChoiceField(queryset=CabPlanificacionTH.objects.filter(status=True), label=u"Unidad", widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    gestion = forms.ModelChoiceField(queryset=GestionPlanificacionTH.objects.filter(status=True), label=u"Gestión", widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    producto = forms.ModelChoiceField(queryset=GestionProductoServicioTH.objects.filter(status=True), label=u"Producto", widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))


class CambiarProductoForm(FormModeloBase):
    producto = forms.ModelChoiceField(ProductoServicioSeccion.objects.filter(status=True).distinct(), required=True,
        label=u'Producto/sección', widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

    def cambiar(self, gestionplan):
        gestion = gestionplan.gestion
        ids_exclude = list(gestionplan.gestion_productos().values_list('producto_id', flat=True))
        self.fields['producto'].queryset = ProductoServicioSeccion.objects.filter(seccion=gestion, activo=True, status=True).exclude(producto_id__in=ids_exclude)

class ResponsableGestionForm(FormModeloBase):
    # responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true'}))
    # subrogante = forms.IntegerField(initial=0, required=False, label=u'Responsable subrogante', widget=forms.TextInput(attrs={'select2search': 'true'}))
    responsable = forms.ModelChoiceField(label=u"Responsable",queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    subrogante = forms.ModelChoiceField(label=u"Responsable subrogante",queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

class VacunacionCovidEvidenciaForm(FormModeloBase):
    # fecha_certificado = forms.DateField(label=u"Fecha Emisión Certificado", required=True, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'campofecha', 'formwidth': '100%', 'type': 'date'}))
    certificado = ExtFileField(label=u'Carnet de Vacunación', required=True,
                               help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                               ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                               widget=forms.FileInput(
                                   attrs={'col': '12', 'accept': '.png, .pdf, .jpg, .jpeg'}))

class VacunacionCovidEvidenciaAdmisionForm(FormModeloBase):
    # fecha_certificado = forms.DateField(label=u"Fecha Emisión Certificado", required=True, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'campofecha', 'formwidth': '100%', 'type': 'date'}))
    certificado = ExtFileField(label=u'Carnet de Vacunación', required=True,
                               help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                               ext_whitelist=(".pdf",), max_upload_size=4194304,
                               widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}))

class DepartamentoProductosTHForm(forms.Form):
    nombre = forms.CharField(label=u'Descripción', widget=forms.Textarea({'rows': '5'}))
    tipo = forms.ChoiceField(label=u'Tipo', choices=TIPO_PORTAFOLIOTH, required=False,
                             widget=forms.Select(attrs={'formwidth': '100%'}))
    fechavigencia = forms.DateField(label=u"Fecha de vigencia", input_formats=['%d-%m-%Y'],
                                        widget=DateTimeInput(format='%d-%m-%Y',
                                                             attrs={'class': 'selectorfecha', 'formwidth': '50%'}))

class ConfiCohorteMaestriaForm(forms.Form):
    tienecostomatricula = forms.BooleanField(label=u"Tiene costo matrícula", required=False, initial=False)
    valormatricula = forms.FloatField(label=u'Valor de la matricula', initial="0.00", required=False,
                                      widget=forms.TextInput(
                                          attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '34%'}))
    tienecostomaestria = forms.BooleanField(
        label=u"Tiene costo maestría (Se activa en el caso de generar el rubro del costo total de la maestría)",
        required=False, initial=False)
    costomaestria = forms.FloatField(label=u'Costo de maestría', initial="0.00", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '34%'}))
    tipootrorubro = forms.IntegerField(initial=0, required=False,
                                       label=u'Tipo Rubro(Se escoge el rubro cuando  tiene costo de maestría)',
                                       widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    fechavencerubro = forms.DateField(label=u"Fecha vence Rubro", input_formats=['%d-%m-%Y'],
                                      widget=DateTimeInput(format='%d-%m-%Y',
                                                           attrs={'class': 'selectorfecha', 'formwidth': '100%'}))
    fechainiordinaria = forms.DateField(label=u"Fecha inicio matrícula ordinaria", input_formats=['%d-%m-%Y'],
                                        widget=DateTimeInput(format='%d-%m-%Y',
                                                             attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafinordinaria = forms.DateField(label=u"Fecha fin matrícula ordinaria", input_formats=['%d-%m-%Y'],
                                        widget=DateTimeInput(format='%d-%m-%Y',
                                                             attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechainiextraordinaria = forms.DateField(label=u"Fecha inicio matrícula extraordinaria", input_formats=['%d-%m-%Y'],
                                             widget=DateTimeInput(format='%d-%m-%Y',
                                                                  attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafinextraordinaria = forms.DateField(label=u"Fecha fin matrícula extraordinaria", input_formats=['%d-%m-%Y'],
                                             widget=DateTimeInput(format='%d-%m-%Y',
                                                                  attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    valorprogramacertificado = forms.FloatField(label=u'Costo de maestría (para certificado)', initial="0.00",
                                                required=False, widget=forms.TextInput(
            attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))
    presupuestobeca = forms.FloatField(label=u'Presupuesto para Becas', initial="0.00", required=False,
                                       widget=forms.TextInput(
                                           attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))

class ConfigFinanciamientoCohorteForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=400, required=True, widget=forms.TextInput(attrs={'formwidth': '100%'}))
    valortotalprograma = forms.FloatField(label=u'Valor total del programa', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))
    valormatricula = forms.FloatField(label=u'Valor de la matricula', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2','formwidth': '50%'}))
    porcentajeminpagomatricula = forms.FloatField(label=u'Porcentaje mín pago matrícula', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '2', 'formwidth': '50%'}))
    valorarancel = forms.FloatField(label=u'Valor Arancel', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2','formwidth': '50%'}))
    maxnumcuota = forms.IntegerField(initial="", label=u'Máx. número de cuotas', required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'onKeyPress': "return soloNumeros(event)",'formwidth': '50%'}))
    fecha = forms.DateField(label=u"Fecha corte de cuotas", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    porcentajedescuentoconvenio = forms.FloatField(label=u'Porcentaje descuento convenio', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '2', 'formwidth': '50%'}))

class TipoOtroRubroIpecRubForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=250, required=False,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    partida = forms.ModelChoiceField(Partida.objects.filter(pk=101), initial=101, required=False, label=u'Item',
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    programa = forms.ModelChoiceField(PartidaPrograma.objects.filter(pk=9), initial=9, required=False,
                                      label=u'Programa', widget=forms.Select(attrs={'formwidth': '100%'}))
    unidad_organizacional = forms.ModelChoiceField(Departamento.objects.filter(pk=115), initial=115, required=False,
                                                   label=u'Unidad Or.',
                                                   widget=forms.Select(attrs={'formwidth': '100%'}))
    tipo = forms.ChoiceField(choices=TIPO_RUBRO, initial=1, required=False, label=u'Tipo Rubro',
                             widget=forms.Select(attrs={'formwidth': '100%'}))


class ResponsableSolicitudForm(forms.Form):
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=False,
        label=u'Departamento', widget=forms.Select(attrs={'formwidth': '100%'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=False,
                                         label=u'Responsable', widget=forms.Select(attrs={'formwidth': '100%'}))
    estado = forms.BooleanField(label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class TituloHojaVidaForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput())
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=10, required=True,
                                  widget=forms.TextInput(attrs={'formwidth': '100%'}))
    nivel = forms.ModelChoiceField(NivelTitulacion.objects.filter(status=True, tipo=1), label=u'Tipo de nivel',
                                   required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    grado = forms.ModelChoiceField(GradoTitulacion.objects.all(), label=u'Grado', required=False,
                                   widget=forms.Select(attrs={'formwidth': '100%'}))

class TituloHojaVidaAdmisionForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput(attrs={'col': '12'}))
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=10, required=True,
                                  widget=forms.TextInput(attrs={'col': '12'}))
    nivel = forms.ModelChoiceField(NivelTitulacion.objects.filter(status=True, tipo=1), label=u'Tipo de nivel',
                                   required=True, widget=forms.Select(attrs={'col': '12'}))
    grado = forms.ModelChoiceField(GradoTitulacion.objects.all(), label=u'Grado', required=False,
                                   widget=forms.Select(attrs={'col': '12'}))

class TituloHojaVidaPostulacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput())
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=10, required=True,
                                  widget=forms.TextInput(attrs={'formwidth': '100%'}))
    nivel = forms.ModelChoiceField(NivelTitulacion.objects.filter(status=True, tipo=1), label=u'Tipo de nivel',
                                   required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    grado = forms.ModelChoiceField(GradoTitulacion.objects.all(), label=u'Grado', required=True,
                                   widget=forms.Select(attrs={'formwidth': '100%'}))
    # areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento",
    #                                           queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1), required=False,
    #                                           widget=forms.Select(attrs={'class': 'imp-75'}))
    # subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento",
    #                                              queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1), required=False,
    #                                              widget=forms.Select(attrs={'class': 'imp-75'}))
    # subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento",
    #                                                        queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1),
    #                                                        required=False,
    #                                                        widget=forms.Select(attrs={'class': 'imp-75'}))
class MantenimientoEscalaForm(forms.Form):
    codigo = forms.CharField(label=u'Código', required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-25', 'formwidth': '75%'}))
    descripcion = forms.CharField(label=u'Descripción', required=False,
                                  widget=forms.Textarea({'rows': '2', 'formwidth': '100%'}))


class NivelEscalaSalarialForm(forms.Form):
    descripcion = forms.CharField(label=u'Nivel en Letras', required=True,
                                  widget=forms.Textarea({'rows': '2', 'formwidth': '100%'}))
    nivel = forms.IntegerField(initial="", label=u'Nivel en número', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'onKeyPress': "return soloNumeros(event)"}))


class EscalaSalarialForm(forms.Form):
    regimenlaboral = forms.ModelChoiceField(
        RegimenLaboral.objects.filter(status=True).distinct().exclude(id__in=[3, 5]), required=True,
        label=u'Regimen Laboral', widget=forms.Select(attrs={'formwidth': '100%'}))
    rol = forms.ModelChoiceField(NivelOcupacional.objects.filter(status=True).distinct(), required=True, label=u'Rol',
                                 widget=forms.Select(attrs={'formwidth': '100%'}))
    grupoocupacional = forms.ModelChoiceField(EscalaOcupacional.objects.filter(status=True).distinct(), required=False,
                                              label=u'Grupo ocupacional',
                                              widget=forms.Select(attrs={'formwidth': '100%'}))
    nivel = forms.ModelChoiceField(NivelEscalaSalarial.objects.filter(status=True).distinct(), required=False,
                                   label=u'Nivel', widget=forms.Select(attrs={'formwidth': '100%'}))
    subnivel = forms.IntegerField(initial=0, label=u'Subnivel', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '30%'}))
    rmu = forms.FloatField(initial='', label=u'RMU', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '30%'}))


class GrupoBienForm(FormModeloBase):
    grupo = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True).distinct(), required=True,
                                   label=u'Grupo', widget=forms.Select(attrs={'formwidth': '100%', 'style':'width:100%'}))


class DenominacionPerfilPuestoForm(forms.Form):
    puesto = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True).distinct().exclude(id__in=[3, 5]), required=True,
                                    label=u'Puesto', widget=forms.Select(attrs={'formwidth': '100%'}))
    observacion = forms.CharField(label=u'Observacion', required=True,
                                  widget=forms.Textarea(attrs={'formwidth': '100%', 'rows': 2}))
    # niveltitulo = forms.ModelChoiceField(NivelTitulacion.objects.filter(status=True).distinct(), required=True, label=u'Nivel de instrucción', widget=forms.Select(attrs={'formwidth': '100%'}))
    # mesesexperiencia = forms.IntegerField(initial=0, label=u'Experiencia(meses)', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0','formwidth': '30%'}))


class NivelTituloForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True, widget=forms.TextInput(attrs={'formwidth': '100%'}))
    rango = forms.IntegerField(initial='', label=u'Rango', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '30%', 'onKeyPress': "return soloNumeros(event)"}))
    codigo_tthh = forms.IntegerField(initial='', label=u'Codigo Talento Humano', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '30%', 'onKeyPress': "return soloNumeros(event)"}))
    tipo = forms.ChoiceField(choices=TIPO_NIVEL_FORMACION, initial=1, required=False, label=u'Tipo',
                             widget=forms.Select(attrs={'formwidth': '100%'}))


class PeriodoPerfilPuestoForm(forms.Form):
    anio = forms.IntegerField(label=u"Año", required=True,
                              widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)
    descripcion = forms.CharField(label=u'Descripción', max_length=10000, widget=forms.Textarea({'row': '3'}),
                                  required=False)
    fechafin = forms.DateField(label=u"Fecha vigencia", initial=datetime.now().date(), required=False,
                               widget=DateTimeInput(attrs={'class': 'selectorfecha', 'formwidth': '50%'},
                                                    format='%Y-%m-%d'))

    # def editar(self):
    #     deshabilitar_campo(self, 'anio')
    #     deshabilitar_campo(self, 'activo')
    #     deshabilitar_campo(self, 'fechafin')


class PerfilPuestoForm(forms.Form):
    codigo = forms.CharField(label=u"Codigo", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'formwidth': '50%', 'readonly': True}))
    # denominacionpuesto = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True).distinct(),
    #                                             required=False, label=u'Denominacion del Puesto',
    #                                             widget=forms.Select(attrs={'formwidth': '100%'}))
    denominacionperfil = forms.ModelChoiceField(PuestoDenominacion.objects.filter(status=True, denominacionpuesto__isnull=False).distinct('denominacionpuesto'),
                                                required=False, label=u'Denominacion del Perfil',
                                                widget=forms.Select(attrs={'style': 'width:90%'}))
    nivel = forms.ChoiceField(choices=NIVEL_PERFIL_PUESTO, initial=1, required=False, label=u'Nivel',
                              widget=forms.Select(attrs={'formwidth': '100%'}))
    direccion = forms.ModelChoiceField(DireccionPerfilPuesto.objects.filter(status=True).distinct(), required=False,
                                       label=u'Unidad Administrativa', widget=forms.Select(attrs={'formwidth': '100%'}))
    escala = forms.ModelChoiceField(EscalaSalarial.objects.filter(status=True).distinct(), required=False,
                                    label=u'Unidad Administrativa',
                                    widget=forms.Select(attrs={'formwidth': '100%', 'rows': '19'}))
    mision = forms.CharField(label=u"Mision", required=True,
                             widget=forms.Textarea(attrs={'rows': '15', 'style': 'resize:none'}))
    especificidadexperiencia = forms.CharField(label=u"Especificidad de la experiencia", required=True,
                                               widget=forms.Textarea(
                                                   attrs={'cols': '19', 'rows': '2', 'style': 'resize:none'}))
    # notaextra = forms.CharField(label=u"Nota", required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    interfaz = forms.CharField(label=u"Interfaz", required=True,
                               widget=forms.Textarea(attrs={'formwidth': '100%', 'rows': '19', 'style': 'resize:none'}))
    capacitacionrequerida = forms.CharField(label=u"Capacitacion Requerida para el puesto", required=True,
                                            widget=forms.Textarea(
                                                attrs={'cols': '19', 'rows': '3', 'style': 'resize:none'}))
    areaconocimiento = forms.ModelChoiceField(
        SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, vigente=True).distinct('nombre'), required=True,
        label=u'Areas de conocimiento',
        widget=forms.Select(attrs={'formwidth': '100%', 'multiple': 'multiple'}), empty_label=None)
    notaextra = forms.CharField(label=u"Nota", required=True,
                                initial='Nota.-Colaborar en las demás funciones que le sean delegadas en relación a los productos y servicios que ofrece la Unidad en la que presta sus servicios, en beneficio de los usuarios y de la comunidad universitaria.',
                                widget=forms.Textarea(attrs={'rows': '4', 'style': 'resize:none'}))

    def set_areas(self, id):
        from sagest.models import PerfilPuestoTh
        self.fields['areaconocimiento'].initial = PerfilPuestoTh.objects.get(id=id).areas_de_conocimiento()


#         self.fields['custodio'].initial = activo.custodio.id

class DuplicarPeriodoPerfilPuestoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=10000,
                                  widget=forms.Textarea({'rows': '3', 'style': 'resize:none; width: 100%'}),
                                  required=False)
    fechafin = forms.DateField(label=u"Fecha vigencia", initial=datetime.now().date(), required=False,
                               widget=DateTimeInput(
                                   attrs={'class': 'selectorfecha', 'formwidth': '50%', 'id': 'id_fechaduplicar'},
                                   format='%Y-%m-%d'))


class MantenimientoNombreForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True, widget=forms.TextInput(attrs={'formwidth': '100%'}))


class CompetenciaLaboralForm(forms.Form):
    numero = forms.IntegerField(label=u"Número", required=True,
                                widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    tipo = forms.ModelChoiceField(TipoCompetenciaLaboral.objects.filter(status=True), required=False, label=u'Tipo',
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    denominacion = forms.CharField(label=u'Denominación', required=True,
                                   widget=forms.TextInput(attrs={'formwidth': '100%'}))
    definicion = forms.CharField(label=u'Definición', max_length=10000, widget=forms.Textarea({'row': '3'}),
                                 required=False)


class DetalleCompetenciaLaboralForm(forms.Form):
    numero = forms.IntegerField(label=u"Número", required=True,
                                widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    comportamiento = forms.CharField(label=u'Comportamiento', max_length=10000, widget=forms.Textarea({'row': '3'}),
                                     required=False)
    nivel = forms.ChoiceField(choices=NIVEL_COMPETENCIA, initial=1, required=False, label=u'Nivel',
                              widget=forms.Select(attrs={'formwidth': '100%'}))


class DirectorResponsableBajaForm(forms.Form):
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))
    cargo = forms.CharField(label=u'Cargo', required=True,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Fecha inicio de actividades", initial=datetime.now().date(), required=False,
                                  widget=DateTimeInput(
                                      attrs={'seleccionafecha': 'True', 'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha fin de actividades", initial=datetime.now().date(), required=False,
                               widget=DateTimeInput(
                                   attrs={'seleccionafecha': 'True', 'class': 'selectorfecha', 'formwidth': '50%'}))
    actual = forms.BooleanField(label=u'Actual', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class DirectorResponsableBaja2Form(forms.Form):
    cargo = forms.CharField(label=u'Cargo', required=True,
                            widget=forms.TextInput(attrs={'formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Fecha inicio de actividades", initial=datetime.now().date(), required=False,
                                  widget=DateTimeInput(
                                      attrs={'seleccionafecha': 'True', 'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha fin de actividades", initial=datetime.now().date(), required=False,
                               widget=DateTimeInput(
                                   attrs={'seleccionafecha': 'True', 'class': 'selectorfecha', 'formwidth': '50%'}))
    actual = forms.BooleanField(label=u'Actual', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class ManualUsuarioForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True,
                             widget=forms.TextInput(attrs={'formwidth': '100%'}))
    version = forms.CharField(label=u'Versión', required=True,
                              widget=forms.TextInput(attrs={'formwidth': '50%'}))
    fecha = forms.DateField(label=u"Fecha", required=False,
                            initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo',
                           help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                           ext_whitelist=(
                               ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png", ".ppt", ".pptx"),
                           required=False,
                           max_upload_size=12582912)

    archivofuente = ExtFileField(label=u'Seleccione Archivo Fuente',
                                 help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png',
                                 ext_whitelist=(
                                     ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png", ".ppt", ".pptx"),
                                 required=False,
                                 max_upload_size=12582912)

    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2'}))
    visible = forms.BooleanField(initial=False, label=u'Visible?', required=False)
    tipos = forms.ModelMultipleChoiceField(label=u"Tipos",
                                           queryset=TipoNoticias.objects.filter(status=True).distinct(), required=False,
                                           widget=forms.SelectMultiple(attrs={'formwidth': '100%'}))
    modulos = forms.ModelMultipleChoiceField(label=u"Modulos",
                                             queryset=Modulo.objects.filter(status=True).distinct(), required=False,
                                             widget=forms.SelectMultiple(attrs={'formwidth': '100%'}))

    def clean(self):
        cleaned_data = super(ManualUsuarioForm, self).clean()
        nombre = cleaned_data['nombre'] if 'nombre' in cleaned_data and cleaned_data['nombre'] else None
        version = int(cleaned_data['version']) if 'version' in cleaned_data and cleaned_data['version'] else 0
        fecha = cleaned_data['fecha'] if 'fecha' in cleaned_data and cleaned_data['fecha'] else None

        if not nombre:
            self.add_error('nombre', ValidationError('Favor ingrese un nombre'))
        if version <= 0:
            self.add_error('version', ValidationError('Favor ingrese una versión mayor a cero'))
        if not fecha:
            self.add_error('fecha', ValidationError('Favor seleccione una fecha'))
        return cleaned_data


class TutoriasTesisExternasPosgradoForm(forms.Form):
    universidad = forms.ModelChoiceField(label=u"Institución de Educación Superior",
                                         queryset=InstitucionEducacionSuperior.objects.filter(status=True),
                                         widget=forms.Select(attrs={'class': 'imp-50'}))
    nombreprograma = forms.CharField(label=u"Nombre del programa", max_length=1500, required=True)
    nombreproyecto = forms.CharField(label=u"Nombre del proyecto o tesis", max_length=1500, required=True)
    fechadireccion = forms.DateField(label=u"Fecha dirección o codirección de tesis", required=True,
                                     input_formats=['%d-%m-%Y'],
                                     widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))


class InscripcionesMaestriasForm(forms.Form):
    inscripcion = forms.IntegerField(initial=0, required=False, label=u'Personal',
                                     widget=forms.TextInput(attrs={'select2search': 'true'}))


class PartidaSaldoForm(forms.Form):
    entidad = forms.ModelChoiceField(label=u" Entidad",
                                     queryset=PartidaEntidad.objects.filter(status=True).order_by('id'),
                                     widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    anioejercicio = forms.ModelChoiceField(label=u"Año Ejercicio", queryset=AnioEjercicio.objects.filter(status=True).order_by('-id'),
                                           widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    partida = forms.ModelChoiceField(label=u"Recurso", queryset=Partida.objects.filter(status=True).order_by('id'),
                                     widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    unidadejecutoria = forms.ModelChoiceField(label=u" Unidad Ejecutoria",
                                              queryset=PartidaUnidadEjecutoria.objects.filter(status=True).order_by('id'),
                                              widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    unidaddesconcentrada = forms.ModelChoiceField(label=u" Unidad Desconcentrada",
                                                  queryset=PartidaUnidadDesconcentrada.objects.filter(status=True).order_by('id'),
                                                  widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    programa = forms.ModelChoiceField(label=u"Programa", queryset=PartidaPrograma.objects.filter(status=True).order_by('id'),
                                      widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))
    subprograma = forms.ModelChoiceField(label=u"Subprograma", queryset=PartidaSubprograma.objects.filter(status=True).order_by('id'),
                                         widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))
    proyecto = forms.ModelChoiceField(label=u"Proyecto", queryset=PartidaProyecto.objects.filter(status=True).order_by('id'),
                                      widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))
    actividad = forms.ModelChoiceField(label=u"Actividad", queryset=PartidaActividad.objects.filter(status=True).order_by('id'),
                                       widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))
    obra = forms.ModelChoiceField(label=u"Obra", queryset=PartidaObra.objects.filter(status=True).order_by('id'),
                                  widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))
    geografico = forms.ModelChoiceField(label=u"Ubicaciòn geogràfica", queryset=PartidaGeografico.objects.filter(status=True).order_by('id'),
                                        widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    fuente = forms.ModelChoiceField(label=u"Clase",
                                    queryset=PartidaFuente.objects.filter(status=True).order_by('id'),
                                    widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    organismo = forms.ModelChoiceField(label=u" Partida Organismo ",
                                       queryset=PartidaOrganismo.objects.filter(status=True).order_by('id'),
                                       widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    correlativo = forms.ModelChoiceField(label=u"Correlativo", queryset=PartidaCorrelativo.objects.filter(status=True).order_by('id'),
                                         widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))

    asignado = forms.FloatField(label=u'Asignado', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value': '0'}))
    # codificado =forms.FloatField( label=u'Codificado', required=False,
    # widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value':'0'}))
    # reservadonegativo =forms.FloatField( label=u'Reservado', required=False,
    # widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value':'0'}))
    # precompromiso =forms.FloatField( label=u'Precompromiso', required=False,
    # widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value':'0'}))
    # compromiso =forms.FloatField( label=u'Compromiso', required=False,
    # widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value':'0'}))
    devengado = forms.FloatField(label=u'Devengado', required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value': '0'}))
    # pagado =forms.FloatField( label=u'Pagado', required=False,
    # widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value':'0'}))
    # recaudado =forms.FloatField( label=u'Recaudado', required=False,
    # widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value':'0'}))
    # recaudadoesigef =forms.FloatField( label=u'Recaudadoesigef', required=False,
    # widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value':'0'}))
    # disponible =forms.FloatField( label=u'Disponible', required=False,
    # widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'value':'0'}))


class PodEvaluacionMetaForm(forms.Form):
    producto = forms.ModelChoiceField(label=u'Producto', queryset=ProductoServicioSeccion.objects.filter(status=True),
                                      required=True, widget=forms.Select(attrs={'class': 'select2-selection__rendered', 'formwidth': '100%', 'style': 'width:860px'}))
    indicador = forms.CharField(label=u"Indicador", max_length=1500, required=True)
    mproyectada = forms.CharField(label=u"Meta proyectada", max_length=1500, required=True)
    mcumplida = forms.DecimalField(label=u'Meta cumplida',
                                   widget=forms.TextInput(attrs={'class': 'imp-moneda', 'placeholder': '0.00', 'type': 'number', 'step': '0.01', 'min': '1', 'pattern': '^[0-9]+', 'decimal': "6", 'formwidth': '33%', }))
    porcentajecumplimiento = forms.DecimalField(label=u'% cumplimiento',
                                                widget=forms.TextInput(attrs={'class': 'imp-moneda', 'placeholder': '0.00', 'type': 'number', 'step': '0.01', 'min': '1', 'pattern': '^[0-9]+', 'decimal': "6", 'formwidth': '33%', }))
    observacion = forms.CharField(label=u'Observaciones', required=False, widget=forms.Textarea(attrs={'rows': '3'}))

    def adicionar(self, depa):
        self.fields['producto'].queryset = ProductoServicioSeccion.objects.filter(seccion__departamento=depa, status=True)

    def edit(self):
        deshabilitar_campo(self, 'producto')


class RedPersonaTipoForm(forms.Form):
    nombre = forms.CharField(label=u'Tipo de Red', max_length=300, required=True,
                             widget=forms.TextInput(attrs={'class': 'form-control', 'formwidth': '100%', 'style': 'width:100%'}))


class RedPersonaForm(forms.Form):
    tipo = forms.ModelChoiceField(label=u"Tipo Red", queryset=TipoRedPersona.objects.filter(status=True).exclude(pk__in=[1, 4]), required=True, widget=forms.Select(attrs={'class': 'select2-selection__rendered', 'formwidth': '100%', 'style': 'width:100%'}))
    enlace = forms.CharField(label=u'Enlace de Red', max_length=300, required=True, widget=forms.TextInput(attrs={'class': 'form-control normal-input', 'formwidth': '100%', 'style': 'width:100%', 'rid': 'textomin'}))


class CompartirCarpetaForm(forms.Form):
    persona = forms.IntegerField(initial=0, label=u"Compartir con", required=False, widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%', 'controlwidth': '100%'}))
    editar = forms.BooleanField(label=u'Puede Editar?', required=False, widget=CheckboxInput())

class BecaPersonaForm(forms.Form):
    persona = forms.IntegerField(initial=0, required=False, label=u'Beneficiario',
                                 widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%', 'controlwidth': '70%'}))
    tipoinstitucion = forms.ChoiceField(choices=TIPO_INSTITUCION_BECA, initial=1, required=False, label=u'Tipo Institución', widget=forms.Select(attrs={'formwidth': '100%', 'controlwidth': '70%'}))
    institucion = forms.ModelChoiceField(label=mark_safe(
        u'<a href="javascript:;" class="btn btn-success tu" title="Agregar Institución" id="add_institucion"><i class="fa fa-plus-square"></i></a>&nbsp; Institución'),
        queryset=InstitucionBeca.objects.filter(status=True),
        required=False, widget=forms.Select(attrs={'formwidth': '100%', 'controlwidth': '70%'}))
    archivo = ExtFileField(label=u'Certificado', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'formwidth': '100%', 'controlwidth': '70%', 'data-allowed-file-extensions': 'pdf'})
                           )
    fechainicio = forms.DateField(label=u"Fecha Rige", input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '50%'}),
                                  required=False)
    fechafin = forms.DateField(label=u"Fecha Finalización", input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y',
                                                    attrs={'class': 'selectorfecha', 'formwidth': '50%'}),
                               required=False)

class RegistroPagoForm(forms.Form):
    telefono = forms.CharField(label=u"Teléfono Estudiante", max_length=10, required=True, widget=forms.TextInput(attrs={'class': 'imp-25', 'onKeyPress': "return soloNumeros(event)","tooltip": "CONFIRMAR NÚMERO TELEFONICO"}))
    email = forms.CharField(label=u"Correo Electronico Estudiante", max_length=240, required=True,widget=forms.TextInput(attrs={'class': 'imp-descripcion', "tooltip": "CONFIRMAR CORREO ELECTRONICO"}))
    fecha = forms.DateField(label=u"Fecha Deposito", required=True, initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha',  'formwidth': '50%', "tooltip": "INDICAR FECHA DEL DEPOSITO Y/O TRANSFERENCIA, SEGÚN CONSTA EN EL COMPROBANTE BANCARIO"}))
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=True,widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumerosPunto(event)", 'decimal': "2", 'formwidth': '50%',"tooltip": "INDICAR VALOR DEL DEPOSITO, SEGÚN CONSTA EN EL COMPROBANTE BANCARIO"}))
    #curso = forms.CharField(label=u"Curso a Pagar", max_length=600, required=True, widget=forms.TextInput(attrs={'class': 'imp-100', "tooltip": "IDENTIFICAR EL NOMBRE DEL CURSO AL QUE EFECTUA EL PAGO"}))
    #carrera = forms.CharField(label=u"Carrera", max_length=600, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', "tooltip": "REGISTRAR EN CASO DE SER ALUMNO DE UNEMI"}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "DETALLAR INFORMACION RELEVANTE TALES COMO NÚMERO O MES DE CUOTA A PAGAR"}))
    tipocomprobante = forms.ChoiceField(choices=TIPO_COMPROBANTE, required=False, label=u'Tipo Comprobante', widget=forms.Select(attrs={'formwidth': '100%', 'separator': 'true',  "tooltip": "SELECCIONE MODALIDAD DE PAGO TRANSFERENCIA Y/O DEPÓSITO"}))

class PersonaTransporteForm(forms.Form):
    transporte = forms.ModelChoiceField(queryset=TipoTransporte.objects.filter(status=True), required=True, label=u'Tipo de Transporte', widget=forms.Select(attrs={'formwidth': '100%', 'controlwidth': '100%'}))

class PersonaAlimentacionUniversidadForm(forms.Form):
    lugar = forms.ModelChoiceField(queryset=LugarAlimentacion.objects.filter(status=True), required=True, label=u'Lugar donde se alimenta en la UNIVERSIDAD', widget=forms.Select(attrs={'formwidth': '100%', 'controlwidth': '100%'}))

class PersonaPlanTelefonicoForm(forms.Form):
    operadora = forms.ModelChoiceField(queryset=OperadoraMovil.objects.filter(status=True), required=True, label=u'Operadora', widget=forms.Select(attrs={'formwidth': '50%', 'controlwidth': '100%'}))
    tieneplan = forms.BooleanField(label=u'¿Dispone de Plan Teléfonico?', required=False, widget=CheckboxInput())
    descripcion =forms.CharField(label=u'Descripción de plan teléfonico u otro tipo de paquete de saldo', required=True, widget=forms.TextInput(attrs={'formwidth': '100%',"placeholder":"Descripción"}))

class PersonaCompraAlimentosForm(forms.Form):
    lugar = forms.ModelChoiceField(queryset=LugarCompraAlimentos.objects.filter(status=True), required=True, label=u'Lugar donde compra sus alimentos', widget=forms.Select(attrs={'formwidth': '100%', 'controlwidth': '100%'}))

class PersonaGastoMensualForm(forms.Form):
    tipogasto= forms.ModelChoiceField(queryset=TipoGasto.objects.filter(status=True), required=True, label=u'Tipo de Gasto', widget=forms.Select(attrs={'formwidth': '50%', 'controlwidth': '100%'}))
    valor =forms.FloatField(label=u'Gasto Semanal', required=True, widget=forms.TextInput(attrs={'style':'text-align:center','class': 'imp-number', 'onKeyPress': "return soloNumerosPunto(event)", 'decimal': "1", 'formwidth': '50%',"tooltip": "INDICAR EL COSTO DEL GASTO SELECCIONADO","placeholder":"00.0"}))

class PersonaEnfermedadForm(FormModeloBase):
    enfermedad= forms.ModelChoiceField(queryset=Enfermedad.objects.filter(status=True), required=True, label=u'Enfermedad', widget=forms.Select(attrs={'class': 'select2'}))
    archivomedico = ExtFileField(label=u'Archivo Médico', required=True,
                           help_text=u'Tamaño maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=2194304,
                           widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'})
                           )

class ComponenteActivoForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.TextInput(attrs={'class': 'imp-25', 'formwidth': '100%'}))


class ComponenteCatalogoActivoForm(FormModeloBase):
    componente = forms.ModelChoiceField(label=u'Componente', required=False, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '100%', 'style':'width:100%'}), queryset=ComponenteActivo.objects.filter(status=True))


class ArchivoHistorialContratoForm(FormModeloBase):
    archivo = ExtFileField(label=u'Contrato firmado', required=False,
                           help_text=u'Tamaño máximo permitido 12Mb, en formato pdf',
                           ext_whitelist=(".pdf",), max_upload_size=12582912,
                           widget=forms.FileInput(attrs={'class': 'w-100 '}))

ESTADOS_ARCHIVO_CONTRATO_PERSONAL = (
    (3, u'FINALIZADO'),
    (5, u'CORREGIR'),
)
class ArchivoHistorialContratoDirectorForm(FormModeloBase):
    archivo = ExtFileField(label=u'Contrato firmado', required=False,
                           help_text=u'Tamaño máximo permitido 12Mb, en formato pdf',
                           ext_whitelist=(".pdf",), max_upload_size=12582912,
                           widget=forms.FileInput(attrs={'class': 'w-100 '}))
    estado_archivo = forms.ChoiceField(choices=ESTADOS_ARCHIVO_CONTRATO_PERSONAL, label=u'Estado de contrato', required=False,
                                   widget=forms.Select(attrs={'col': '4'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea(attrs={'rows': '3','col':'6'}))

class CategoriaTipoPermisoForm(forms.Form):
    tipopermiso = forms.ModelChoiceField(queryset=TipoPermiso.objects.filter(status=True),label=u'Permisos',
                                         widget=forms.Select(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(label=u'Descripción', required=True, widget=forms.Textarea({'rows': '2'}))

class SolicitudJustificacionMarcadaForm(FormModeloBase):
    observacion = forms.CharField(label=u'Observación/motivo',required=True,widget=forms.Textarea({'col': '12','rows': '2'}))
    archivo = ExtFileField(required=False,
                                     help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg',
                                     ext_whitelist=(".pdf", ".jpg", ".jpeg",),
                                     max_upload_size=4194304, widget=forms.FileInput({'col': '12', 'class': 'dropify'}))
    tiposolicitu = forms.ChoiceField(choices=TIPO_SOLICITUD_JUST_MARCADA, label=u'Tipo solicitud', required=False,
                                     widget=forms.Select(attrs={'col': '4','separator2':True,'separatortitle':'Marcadas detalle'}))
    horaexistente = forms.IntegerField(label=u'Hora marcada', required=False, initial=0, widget=forms.Select(attrs={'col': '4'}))
    secuencia = forms.ChoiceField(choices=TIPO_SECUENCIA_MARCADA, label=u'Secuencia', required=False,
                                  widget=forms.Select(attrs={'col': '4'}))

    fecha = forms.DateField(label=u'Fecha',required=False,initial=datetime.now().date(),
                                     input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                      attrs={'col': '4'}))
    hora = forms.TimeField(label=u"Hora", required=False, initial=datetime.now().time().strftime('%H:%M'),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '4', 'crearboton': True, 'classbuton': 'agregarbtn'}))


class AccionPersonalDocumentoForm(FormModeloBase):
    """archivofirmado = ExtFileField(label=u'Accion de personal', required=True,
                               help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg',
                               ext_whitelist=(".pdf", ".jpg", ".jpeg",), max_upload_size=4194304,
                               widget=forms.FileInput(attrs={'formwidth': '100%', 'class': 'dropify'}))"""
    archivofirmado = ExtFileField(label=u'Accion de personal', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg',
                                  ext_whitelist=(".pdf", ".jpg", ".jpeg",), max_upload_size=4194304, widget=forms.FileInput())

class NotificacionactivoresponsableForm(FormModeloBase):
    tipo = forms.ModelChoiceField(queryset=TipoNotificacion.objects.filter(status=True), label="Tipo",
                                      widget=forms.Select( attrs={"class": "form-select select2", 'col': '6', "style": "width: 100%;", "idp": "producto-select"}), required=True, )
    asunto = forms.CharField(label=u"Asunto", max_length=300, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    # detalle = forms.CharField(label=u'Detalle', max_length=10000, widget=forms.Textarea({'cols': '40', 'rows': '7', 'class': 'validate[required]', 'style': "width: 100%;"}))
    detalle = forms.CharField(required=False, label=u'Detalle', widget=forms.Textarea(attrs={'col':'12', 'separator3': True}))

class TipoNotificacionForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripcion", max_length=400, required=True,
                              widget=forms.TextInput(attrs={'class': 'imp-100'}))


class ActivoTecnologicoForm(FormModeloBase):
    activofijo = forms.IntegerField(initial=0, required=False, label=u'Activos desactivados', widget=forms.TextInput(attrs={'select2search': 'true'}))
    codigogobierno = forms.CharField(label=u"Código gobierno", required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '400px'}))
    codigointerno = forms.CharField(label=u"Código interno", required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '400px'}))
    codigotics = forms.IntegerField(label=u"Código tics", required=False, widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '400px', 'disabled':True}))
    serie = forms.CharField(label=u"Serie", required=False, widget=forms.TextInput(attrs={'class': 'imp-descripcion'}))
    modelo = forms.CharField(label=u"Modelo", required=False, widget=forms.TextInput(attrs={'class': 'imp-descripcion'}))
    # marca = forms.ModelChoiceField(Marca.objects.filter(status=True), required=False, label=u'Marca', widget=forms.Select())
    marca = forms.CharField(label=u'Marca', max_length=250, required=False, widget=forms.TextInput(attrs={'class': 'imp-descripcion'}))
    cuentacontable = forms.CharField(label=u'Cuenta contable', max_length=250, required=False, widget=forms.TextInput(attrs={'class': 'imp-descripcion','disabled':True}))
    vidautil = forms.IntegerField(label=u'Años de Vida útil', required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0','disabled':True}))

    # marca = forms.CharField(label=u"Marca", required=False, widget=forms.TextInput(attrs={'class': 'imp-descripcion'}))
    ubicacion = forms.ModelChoiceField(Ubicacion.objects.filter(status=True),required=True, label=u'Ubicación Bien', widget=forms.Select())
    responsable = forms.IntegerField(initial=0, label=u'Responsable bien',required=True, widget=forms.TextInput(attrs={'select2search': 'true'}))
    custodio = forms.IntegerField(initial=0, label=u'Custodio del bien',required=True, widget=forms.TextInput(attrs={'select2search': 'true'}))
    fechacompra = forms.DateField(label=u"Fecha compra", required=False, widget=DateTimeInput(attrs={'class': 'selectorfecha','formwidth': '190px',}))
    #periodogarantiainicio = forms.DateField(label=u"Periodo de inico de garantía ", required=False,initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': ' w-25 selectorfecha', 'separator': 'true',}))
    #periodogarantiafin = forms.DateField(label=u"Periodo fin de garantía", required=False,initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'w-25 selectorfecha', }))
    periodogarantiainicio = forms.DateField(label=u"Periodo de inico de garantía ", required=True,widget=DateTimeInput(attrs={'class': 'imp-codigo', 'formwidth': '400px',}))
    periodogarantiafin = forms.DateField(label=u"Periodo fin de garantía",required=True, widget=DateTimeInput(attrs={'class': 'imp-codigo', 'formwidth': '400px'}))
    proveedor = forms.IntegerField(initial=0, label=u'Proveedor',required=True ,widget=forms.TextInput(attrs={'select2search': 'true',}))
    estado = forms.ModelChoiceField(EstadoProducto.objects.filter(status=True), required=True,label=u'Estado', widget=forms.Select(attrs={'formwidth': '50%'}))
    gruposcategoria = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True), label=u'Categorìa', widget=forms.Select())
    # status = forms.BooleanField(label=u'Activo', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    catalogodescripcion = forms.CharField(label=u'Catalogo', max_length=250, required=False, widget=forms.TextInput(attrs={'class': 'imp-descripcion',}))
    observacion = forms.CharField(label=u'Observaciòn', max_length=250, required=False, widget=forms.Textarea(attrs={'class': 'imp-descripcion'}))
    # estructuraactivo = forms.ChoiceField(choices=ESTRUCTURA_ACTIVO, required=False, label=u'Forma Ingreso',widget=forms.Select(attrs={'formwidth': '300px', 'separator': 'true'}))
    # clasebien = forms.ChoiceField(choices=CLASE_BIEN, label=u'Clase Bien', required=False,widget=forms.Select(attrs={'formwidth': '320px', 'labelwidth': '100px'}))
    #f echaingreso = forms.DateField(label=u"Fecha ingreso", required=False, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'selectorfecha','formwidth': '190px','separator': 'true'}))
    # descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea({'rows': '3'}))
    # observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '3'}))
    # origeningreso = forms.ModelChoiceField(OrigenIngreso.objects.filter(status=True), required=False, label=u'Origen Ingreso',widget=forms.Select(attrs={'formwidth': '400px'}))
    # costo = forms.DecimalField(initial="0.00", label=u'Costo', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '200px', 'labelwidth': '100px', 'decimal': '2'}))
    # tipodocumentorespaldo = forms.ModelChoiceField(TipoDocumentoRespaldo.objects.filter(status=True), required=False,label=u'Tipo Doc. Respaldo', widget=forms.Select(attrs={'formwidth': '600px', 'separator': 'true'}))
    # clasedocumentorespaldo = forms.ModelChoiceField(ClaseDocumentoRespaldo.objects.filter(status=True), required=False,label=u'Clase Doc. Respaldo', widget=forms.Select(attrs={'formwidth': '600px', 'separator': 'true'}))
    # numerocomprobante = forms.CharField(label=u'N° Comprobante', required=False, max_length=20,widget=forms.TextInput(attrs={'formwidth': '40%', 'class': 'imp-comprobantes'}))
    # tipocomprobante = forms.ModelChoiceField(TipoDocumento.objects.filter(status=True), required=False, label=u'Tipo Comprobante',widget=forms.Select(attrs={'formwidth': '50%'}))
    # fechacomprobante = forms.DateField(label=u"F. Comprobante", required=False, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'selectorfecha','formwidth': '35%', 'separator': 'true'}))
    # tipoproyecto = forms.ModelChoiceField(TipoProyecto.objects.filter(status=True), required=False, label=u'Tipo Proyecto', widget=forms.Select(attrs={'formwidth': '600px', 'separator': 'true'}))
    # deprecia = forms.BooleanField(initial=True, required=False, label=u"Deprecia?")
    # vidautil = forms.IntegerField(initial=0, label=u'Años de Vida útil', required=False,widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    # cuentacontable = forms.ModelChoiceField(CuentaContable.objects.filter(activosfijos=True), required=False,label=u'Cuenta Contable', widget=forms.Select(attrs={}))
    # custodio = forms.IntegerField(initial=0, required=False, label=u'Custodio Bien',widget=forms.TextInput(attrs={'select2search': 'true'}))
    # catalogo = forms.IntegerField(initial=0, required=False, label=u'Catálogo Bien',widget=forms.TextInput(attrs={'select2search': 'true'}))
    # titulo = forms.CharField(required=False, label=u'Título', widget=forms.TextInput(attrs={'separator': 'true'}))
    # autor = forms.CharField(required=False, label=u'Autor', widget=forms.TextInput())
    # editorial = forms.CharField(required=False, label=u'Editorial', widget=forms.TextInput())
    # fechaedicion = forms.DateField(label=u"Fecha edición", required=False, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'selectorfecha','formwidth': '50%'}))
    # numeroedicion = forms.CharField(label=u"Número de edición", required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    # clasificacionbibliografica = forms.CharField(required=False, label=u'Clasificación Bibliográfica',widget=forms.TextInput())
    # color = forms.ModelChoiceField(Color.objects.filter(status=True), required=False, label=u'Color',widget=forms.Select(attrs={'separator': 'true', 'formwidth': '75%'}))
    # material = forms.CharField(required=False, label=u'Material', widget=forms.TextInput(attrs={'formwidth': '75%'}))
    # dimensiones = forms.CharField(required=False, label=u'Dimensiones',widget=forms.TextInput(attrs={'formwidth': '75%'}))
    # clasevehiculo = forms.ModelChoiceField(ClaseVehiculo.objects.filter(status=True), required=False, label=u'Clase Vehículo',widget=forms.Select(attrs={'separator': 'true', 'formwidth': '50%'}))
    # tipovehiculo = forms.ModelChoiceField(TipoVehiculo.objects.filter(status=True), required=False, label=u'Tipo Vehículo',widget=forms.Select(attrs={'formwidth': '50%'}))
    # numeromotor = forms.CharField(label=u"Número de motor", required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    # numerochasis = forms.CharField(label=u"Número de chasis", required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    # placa = forms.CharField(label=u"Placa", required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    # aniofabricacion = forms.IntegerField(label=u"Año de fabricación", initial=datetime.now().date().year,required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    # colorprimario = forms.ModelChoiceField(Color.objects.filter(status=True), required=False, label=u'Color Primario',widget=forms.Select(attrs={'formwidth': '75%'}))
    # colorsecundario = forms.ModelChoiceField(Color.objects.filter(status=True), required=False, label=u'Color Secundario',widget=forms.Select(attrs={'formwidth': '75%'}))
    # propietario = forms.CharField(required=False, label=u'Propietario',widget=forms.TextInput(attrs={'separator': 'true'}))
    # codigocatastral = forms.CharField(label=u"Código catastral", required=False,widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    # numeropredio = forms.CharField(label=u"Número predio", required=False,widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    # valoravaluo = forms.DecimalField(initial="0.00", label=u'Valor Avalúo', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%', 'decimal': '2'}))
    # anioavaluo = forms.IntegerField(label=u"Año de Avalúo", required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    # areapredio = forms.DecimalField(initial="0.00", label=u'Área Predio(mts)', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    # areaconstruccion = forms.DecimalField(initial="0.00", label=u'Área Construcción(mts)', required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%', 'decimal': '2'}))
    # pisos = forms.IntegerField(label=u"Número de pisos", required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    # provincia = forms.ModelChoiceField(Provincia.objects.filter(status=True), required=False, label=u'Provincia',widget=forms.Select())
    # canton = forms.ModelChoiceField(Canton.objects.filter(status=True), required=False, label=u'Cantón', widget=forms.Select())
    # parroquia = forms.ModelChoiceField(Parroquia.objects.filter(status=True), required=False, label=u'Parroquia', widget=forms.Select())
    # zona = forms.ChoiceField(choices=TIPO_ZONA, label=u'Zona', required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    # nomenclatura = forms.CharField(label=u"Nomenclatura", required=False,widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '50%'}))
    # sector = forms.CharField(required=False, label=u'Sector', widget=forms.TextInput())
    # direccion = forms.CharField(required=False, label=u'Calle principal', widget=forms.TextInput())
    # direccion2 = forms.CharField(required=False, label=u'Calle secundaria', widget=forms.TextInput())
    # escritura = forms.CharField(label=u"Escritura", required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    # fechaescritura = forms.DateField(label=u"Fecha escritura", required=False, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'selectorfecha','formwidth': '200px'}))
    # notaria = forms.CharField(required=False, label=u'Notaría', widget=forms.TextInput())
    # beneficiariocontrato = forms.CharField(required=False, label=u'Beneficiario contrato', widget=forms.TextInput())
    # fechacontrato = forms.DateField(label=u"Fecha contrato", required=False, initial=datetime.now().date(), widget=DateTimeInput(attrs={'class': 'selectorfecha','formwidth': '200px'}))
    # duracioncontrato = forms.IntegerField(initial=0, label=u'Duración del contrato', required=False,widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    # montocontrato = forms.DecimalField(initial="0.00", label=u'Monto contrato', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%', 'decimal': '2'}))
    def soloRead(self, field_names):
        for field_name in field_names:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['disabled'] = True
                self.fields[field_name].widget.attrs['style'] = 'background-color: #EEEEEE;'


    def editar_proveedor(self, proveedor):
        self.fields['proveedor'].widget.attrs['descripcion'] = proveedor
        self.fields['proveedor'].initial = proveedor.id
        self.fields['proveedor'].widget.attrs['value'] = proveedor.id

    def editar_responsable(self, responsable):
        self.fields['responsable'].widget.attrs['descripcion'] = responsable
        self.fields['responsable'].initial = responsable.id
        self.fields['responsable'].widget.attrs['value'] = responsable.id

    def editar(self, activo, user):
        if activo.codigogobierno:
            deshabilitar_campo(self, 'codigogobierno')
        if activo.codigointerno:
            deshabilitar_campo(self, 'codigointerno')
        if not user.has_perm("sagest.puede_modificar_depreciacion"):
            if activo.en_uso():
                deshabilitar_campo(self, 'deprecia')
                deshabilitar_campo(self, 'vidautil')
                deshabilitar_campo(self, 'catalogo')
        if activo.en_uso() or activo.subidogobierno:
            deshabilitar_campo(self, 'fechaingreso')
            deshabilitar_campo(self, 'costo')
            deshabilitar_campo(self, 'fechacomprobante')
            deshabilitar_campo(self, 'responsable')
            deshabilitar_campo(self, 'custodio')
            # deshabilitar_campo(self, 'ubicacion')
            if activo.responsable:
                self.fields['responsable'].widget.attrs['descripcion'] = activo.responsable.nombre_completo()
                self.fields['responsable'].initial = activo.responsable.id
            else:
                habilitar_campo(self, 'responsable')

            if activo.responsable:
                self.fields['proveedor'].widget.attrs['descripcion'] = activo.proveedor.nombre_simple()
                self.fields['proveedor'].initial = activo.proveedor.id
            else:
                habilitar_campo(self, 'responsable')

            if activo.custodio:
                self.fields['custodio'].widget.attrs['descripcion'] = activo.custodio.nombre_completo()
                self.fields['custodio'].initial = activo.custodio.id
            else:
                habilitar_campo(self, 'custodio')
        else:
            del self.fields['responsable']
            del self.fields['custodio']
            del self.fields['ubicacion']
        self.fields['catalogo'].widget.attrs['descripcion'] = activo.catalogo.descripcion
        self.fields['catalogo'].initial = activo.catalogo.id
    def ocultar_activo_tecnologico(self):
        del self.fields['activotecnologico']


class ProcesoLiquidacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'class': 'imp-100'}))
    anio = forms.IntegerField(label=u"Año", initial=datetime.now().date().year,
                              required=False, widget=forms.TextInput(
            attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '40%'}))
    activo = forms.BooleanField(label=u"¿Activo?", required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))


class RequisitoLiquidacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True,
                             widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "Nombre"}))
    leyenda = forms.CharField(label=u'Leyenda', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    activo = forms.BooleanField(label=u"¿Activo?", required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    archivo = ExtFileField(label=u'Formato Solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png, docx, xlsx, xls, xlsxm',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx", ".xls", ".xlsxm"),
                           max_upload_size=8194304,
                           widget=forms.FileInput(attrs={'formwidth': '100%',
                                                         'data-allowed-file-extensions': 'png pdf jpg jpeg docx xlsx xls xlsxm'}))
    requerido = forms.BooleanField(label=u"¿Es Requerido?", required=False,
                                   widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))


class ReasignarSolicitudLiquidacionForm(forms.Form):
    departamento = forms.ModelChoiceField(Departamento.objects.filter(integrantes__isnull=False, status=True).distinct().order_by('id'), required=True, label=u'Departamento', widget=forms.Select())
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    archivo = ExtFileField(label=u'Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))


class FinalizarSolicitudLiquidacionForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    archivo = ExtFileField(label=u'Evidencia de pago', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))

class ServicioModeloForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class ServicioCompraForm(forms.Form):
    tiposervicio = forms.ModelChoiceField(ServicioModelo.objects.filter(status=True).distinct().order_by('id'), required=True, label=u'Servicio', widget=forms.Select(attrs={'style': 'width:100%'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3', 'cols': '3', 'style': 'width:100%'}), required=True)
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumerosPunto(event)", 'decimal': "2", 'formwidth': '25%'}))


class LiquidacionCompraForm(forms.Form):
    numerodocumento = forms.CharField(label=u'N° Comprobante', required=False, max_length=20, widget=forms.TextInput(attrs={'formwidth': '50%', 'class': '', 'readonly': True}))
    fechaemision = forms.DateField(label=u"Fecha Emisión", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                                                                                           attrs={'class': 'selectorfecha',
                                                                                                                                                                  'formwidth': '315px'}))
    proveedor = forms.ModelChoiceField(Proveedor.objects.filter(status=True), required=False, label=u'Proveedor', widget=forms.Select(attrs={'formwidth': '50%'}))
    # sustentotributario = forms.ModelChoiceField(SustentoTributario.objects.filter(status=True), required=False,
    #                                             label=u'Sustento', widget=forms.Select(attrs={'formwidth': '50%'}))
    # tipodocumento = forms.ModelChoiceField(TipoDocumento.objects.filter(status=True, id=3), required=False, label=u'Tipo Documento', initial = TipoDocumento.objects.get(status=True, id=3),
    #                                        widget=forms.Select(attrs={'formwidth': '50%'}))
    impuesto = forms.ModelChoiceField(Impuesto.objects.filter(status=True).order_by('-predeterminado'), required=True,  label=u'Impuesto', widget=forms.Select(attrs={'formwidth': '50%'}))
    # fecharegistro = forms.DateField(label=u"Fecha Registro", initial=datetime.now().date(), required=False,
    #                                 input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
    #                                                                                  attrs={'class': 'selectorfecha',
    #                                                                                         'formwidth': '315px'}))
    # fechavencimiento = forms.DateField(label=u"Fecha Vencimiento", initial=datetime.now().date(), required=False,
    #                                    input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
    #                                                                                     attrs={'class': 'selectorfecha',
    #                                                                                            'formwidth': '315px'}))
    #autorizacion = forms.CharField(label=u"No. Autorización", max_length=49, required=True, widget=forms.TextInput(attrs={'formwidth': '50%'}))
    # fechacaducidad = forms.DateField(label=u"Fecha Caducidad", initial=datetime.now().date(), required=False,
    #                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
    #                                                                                   attrs={'class': 'selectorfecha',
    #                                                                                          'formwidth': '250px'}))
    #secuencial = forms.CharField(label=u"Secuencial", max_length=15, required=False,  widget=forms.HiddenInput(attrs={'formwidth': '50%'}))
    #parterelacionada = forms.ChoiceField(choices=SINO, label=u'Parte Relacionada', required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    # centrocosto = forms.ModelChoiceField(CentroCosto.objects.filter(status=True), required=True,
    #                                      label=u'Centro de Costo', widget=forms.Select(attrs={'formwidth': '100%', }))
    cuentacontable = forms.IntegerField(initial=0, required=True, label=u'Cuenta Contable', widget=forms.TextInput(attrs={'select2search': 'true'}))


class CronogramaPersonaInventarioForm(FormModeloBase):
    persona = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True,), required=True, label=u'Funcionario', widget=forms.Select(attrs={'col':'12'}))
    fecha = forms.DateField(label=u"Fecha",widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '6'}))
    hora = forms.TimeField(label=u"Hora", required=True, initial=str(datetime.now().time().strftime("%H:%M")),widget=DateTimeInput(format='%H:%M', attrs={'col': '6'}))
    descripcion = forms.CharField(label=u'Descripción',required=False,widget=forms.Textarea({'col': '12','placeholder': 'Añade una descripción del evento'}))

    def validador(self,id=0, idperiodo=0):
        ban,idpersona,fecha,hora = True, self.cleaned_data['persona'].id,self.cleaned_data['fecha'],self.cleaned_data['hora']
        cronograma=CronogramaPersonaConstatacionAT.objects.filter(status=True,periodo_id=idperiodo).exclude(id=id)
        if idpersona != 0 and cronograma.filter(persona_id=idpersona).exists():
            self.add_error('persona', 'Registro que desea ingresar ya existe.')
            ban = False
        # if cronograma.filter(fecha=fecha,hora=hora).exists():
        #     self.add_error('hora', 'Registro que desea ingresar ya existe.')
        #     ban = False
        return ban

class ConstatacionFisicaATForm(FormModeloBase):
    usuariobienes = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True,), required=False, label=u'Usuario que utiliza el activo', widget=forms.Select(attrs={'col':'6'}))
    estadoactual= forms.ModelChoiceField(queryset=EstadoProducto.objects.select_related().filter(status=True,), required=True, label=u'Estado actual', widget=forms.Select(attrs={'col':'6','placeholder': 'Seleccione un estado'}))
    bloque = forms.ModelChoiceField(queryset=HdBloque.objects.select_related().filter(status=True,), required=False, label=u'Bloque', widget=forms.Select(attrs={'col':'6','placeholder': 'Seleccione una bloque'}))
    ubicacion = forms.ModelChoiceField(queryset=HdBloqueUbicacion.objects.select_related().filter(status=True,), required=False, label=u'Ubicación', widget=forms.Select(attrs={'col':'6','placeholder': 'Seleccione una ubicación'}))
    # ubicacionbienes = forms.ModelChoiceField(queryset=Ubicacion.objects.select_related().filter(status=True,), required=False, label=u'Ubicación', widget=forms.Select(attrs={'col':'6','placeholder': 'Seleccione una ubicación'}))
    observacion = forms.CharField(label=u'Observación',required=False,widget=forms.Textarea({'col': '12','rows':'3','placeholder': 'Añade una observación'}))
    encontrado = forms.BooleanField(initial=False, required=False, label=u'¿Fue encontrado?', widget=forms.CheckboxInput(attrs={'data_checkbox': True}))
    enuso = forms.BooleanField(initial=False, required=False, label=u'¿Esta en uso?', widget=forms.CheckboxInput(attrs={'data_checkbox': True}))
    perteneceusuario = forms.BooleanField(initial=False, required=False, label=u'¿Pertenece al usuario?', widget=forms.CheckboxInput(attrs={'data_checkbox': True}))
    requieretraspaso = forms.BooleanField(initial=False, required=False, label=u'¿Requiere traspaso?', widget=forms.CheckboxInput(attrs={'data_checkbox': True}))
    requieredarbaja = forms.BooleanField(initial=False, required=False, label=u'¿Requiere dar de baja?', widget=forms.CheckboxInput(attrs={'data_checkbox': True}))

class ReporteLiquidacionCompraFrom(forms.Form):
    #cuentacontable = forms.ModelChoiceField(CuentaContable.objects.filter(activosfijos=True), required=False,label=u'Cuenta Contable', widget=forms.Select(attrs={'formwidth': '100%'}))
    tipoarchivo = forms.ChoiceField(choices=[('' ,'SELECCIONE TIPO'), (1, 'PDF'), (2, 'EXCEL')], label=u'Tipo Archivo', required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    estado = forms.ChoiceField(choices=[('', "TODOS"), *ESTADO_COMPROBANTE], label=u'Estado', required=True, widget=forms.Select(attrs={'formwidth': '100%'}))

    fecha_desde = forms.DateField(label=u"Fecha desde", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'style': 'width:90%;'}))
    fecha_hasta = forms.DateField(label=u"Fecha hasta", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'style': 'width:90%;'}))

class SubirSubNovedadesForm(forms.Form):
    rubrorol = forms.ModelChoiceField(RubroRol.objects.filter(status=True, tiporubro=2), required=False, label=u'Novedades', widget=forms.Select())
    archivo = ExtFileField(label=u'Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato xlsx',
                           ext_whitelist=(".xlsx",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'xls xlsx'}))
    def cargar_rubrorol(self, responsable):
        self.fields['rubrorol'].queryset = RubroRol.objects.filter(status=True,responsablenovedad__persona=responsable)

class NotificarForm(FormModeloBase):
    mes = forms.ChoiceField(choices=MONTH_CHOICES, label=u'Mes', required=True, widget=forms.Select(attrs={'col': '6'}))
    anio = forms.ChoiceField(choices=[(a, str(a)) for a in PeriodoRol.objects.filter(status=True).values_list('anio', flat=True).distinct().order_by('-anio')], label=u'Año', required=True, widget=forms.Select(attrs={'col': '6'}))

class ResponsableNovedadForm(FormModeloBase):
    persona = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True,), required=False, label=u'Persona', widget=forms.Select(attrs={'col':'10'}))
    rubro = forms.ModelChoiceField(RubroRol.objects.filter(status=True, tiporubro=2), required=False, label=u'Novedades', widget=forms.Select())
    logo = ExtFileField(label=u'Logo', required=False,
                       help_text=u'Tamaño Maximo permitido 4Mb, en formato .jpeg,.jpg,.png',
                       ext_whitelist=(".xlsx",), max_upload_size=4194304,
                       widget=forms.FileInput(
                           attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))

class ComprobanteATForm(FormModeloBase):
    contrato = forms.ModelChoiceField(label=u"Contrato", queryset=ContratoAT.objects.filter(status=True), required=False,widget=forms.Select(attrs={'col':'12'}))
    # origeningreso = forms.ModelChoiceField(label=u"Origen de ingreso", queryset=OrigenIngreso.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col':'6'}))
    proveedor=forms.ModelChoiceField(label='Proveedor',queryset=Proveedor.objects.filter(status=True),required=True, widget=forms.Select(attrs={'col':'12'}))
    # tipocomprobante=forms.ModelChoiceField(label='Tipo de comprobante',queryset=TipoDocumento.objects.filter(status=True),required=True, widget=forms.Select(attrs={'col':'6'}))
    # numerocomprobante=forms.CharField(label='Número de comprobante', required=True,widget=forms.TextInput(attrs={'col':'6'}))
    # fechacompra = forms.DateField(label="Fecha de compra", required=True,widget=forms.DateInput(attrs={'col':'6'}))
    # cantidad = forms.IntegerField(label=u"Cantidad de productos cargados en el comprobante",widget=forms.NumberInput(attrs={'col':'6'}))
    descripcion = forms.CharField(label="Descripción", required=False,widget=forms.Textarea(attrs={'col':'12','rows':'4'}))

class ActividadInformeGCForm(FormModeloBase):
    descripcion = forms.CharField(label="Actividad", required=True,widget=forms.TextInput(attrs={'col':'10','placeholder':'Describa la actividad a agregar..'}))

    def validador(self,idgrupo):
        descripcion = self.cleaned_data['descripcion'].strip()
        if ActividadInformeGC.objects.filter(status=True, descripcion__unaccent=descripcion, grupocategoria_id=idgrupo).exists():
            self.add_error('descripcion', 'La actividad que desea guardar ya existe.')
            return False
        return True

class InformeBajaATForm(FormModeloBase):
    activofijo = forms.CharField(widget=forms.HiddenInput())
    solicita = forms.ModelChoiceField(required=True, label=u'Solicita',
                                      queryset=Persona.objects.select_related().filter(status=True),
                                      widget=forms.Select(attrs={'col':'6'}))
    responsable_ = forms.ModelChoiceField(required=True, label=u'Responsable de activo',
                                        queryset=Persona.objects.select_related().filter(status=True),
                                        widget=forms.Select(attrs={'col':'6'}))
    bloque = forms.ModelChoiceField(HdBloque.objects.filter(status=True), label=u'Bloque',
                                    widget=forms.Select(attrs={'col': '6'}))

    estadouso = forms.ChoiceField(label=u"Mal Uso", choices=ESTADO_USO, required=False,
                                  widget=forms.Select(attrs={'col': '6'}))
    estadoactivo = forms.ModelChoiceField(label=u'Estado del activo', required=True,
                                          queryset=EstadoProducto.objects.filter(status=True).exclude(id__in=[4, 5]).order_by('id'),
                                          widget=forms.Select(attrs={'col': '5', 'class': 'select2'}))
    estado = forms.ChoiceField(label=u"Condición del activo", choices=ESTADO_BAJA, required=False,
                               widget=forms.Select(attrs={'col': '5'}))
    enuso = forms.BooleanField(label=u'¿Está en uso?', required=False,
                               widget=forms.CheckboxInput(attrs={'col': '2', 'data-switchery': True}))
    detallerevision = forms.CharField(label=u'Detalle Revisión', required=False,
                                      widget=forms.Textarea(attrs={'rows': '4', 'col':'6'}))
    conclusion = forms.CharField(label=u'Conclusión', required=False,
                                 widget=forms.Textarea(attrs={'rows': '4','col':'6'}))

    # def clean(self):
    #     cleaned_data=super().clean()
    #     activofijo=cleaned_data.get('activofijo')
    #     if InformeActivoBaja.objects.filter(tipoinforme=1, status=True, activofijo_id=activofijo).exists():
    #         raise NameError('Registro de informe de baja ya existe.')
    #     return cleaned_data

class PeriodoGarantiaMantenimientoATForm(FormModeloBase):
    nombre = forms.CharField(label="Título", required=False, widget=forms.TextInput(attrs={'col': '12','placeholder':'Describa el título del periodo a crear'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=True,widget=DateTimeInput(format='%d-%m-%Y',attrs={'col':'6'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=True,widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    detalle = forms.CharField(label=u'Detalle', required=False,widget=forms.Textarea(attrs={'rows': '5','placeholder': 'Detalle del periodo'}))

    def clean(self):
        cleaned_data=super().clean()
        nombre=cleaned_data.get('nombre').capitalize().strip()
        id=getattr(self.instancia, 'id', 0)
        periodo=PeriodoGarantiaMantenimientoAT.objects.filter(status=True, nombre__unaccent=nombre).exclude(id=id)
        if periodo.exists():
            self.add_error('nombre','Registro que intenta guardar ya existe.')
        return cleaned_data

#-------------PAZ Y SALVO-------------

class FormatoPazSalvoForm(FormModeloBase):
    titulo = forms.CharField(label="Título", required=True, widget=forms.TextInput(attrs={'col': '12','placeholder':'Describa el título del formato a crear'}))
    descripcion = forms.CharField(label=u'Detalle', required=False,widget=forms.Textarea(attrs={'rows': '5','placeholder': 'Descripción del formato'}))
    activo = forms.BooleanField(initial=False, label=u'¿Activo?', required=False, widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'4'}))

    def clean(self):
        cleaned_data=super().clean()
        cleaned_data['titulo']=titulo=cleaned_data.get('titulo').upper().strip()
        id=getattr(self.instancia, 'id', 0)
        formato=FormatoPazSalvo.objects.filter(status=True, titulo__unaccent=titulo).exclude(id=id)
        if formato.exists():
            self.add_error('titulo','Registro que intenta guardar ya existe.')
        return cleaned_data

class DireccionFormatoPSForm(FormModeloBase):
    idformato = forms.CharField(widget=forms.HiddenInput())
    departamento = forms.ModelChoiceField(label="Dirección", required=True,
                                          queryset=Departamento.objects.select_related().filter(status=True,tipo=1),
                                          widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    orden = forms.IntegerField(label='Orden de aparición en el certificado',
                               required=True, initial=1,
                               widget=forms.NumberInput(attrs={'col': '12'}))

    def cargar_orden_siguiente(self, idformato):
        direccion=DireccionFormatoPS.objects.filter(status=True, formato_id=idformato).order_by('orden').last()
        if direccion:
            self.fields['orden'].initial = direccion.orden + 1

    def clean(self):
        cleaned_data = super().clean()
        departamento = cleaned_data.get('departamento')
        idformato = int(cleaned_data.get('idformato'))
        orden = int(cleaned_data.get('orden'))
        id = getattr(self.instancia, 'id', 0)
        direccion = DireccionFormatoPS.objects.filter(status=True, departamento=departamento, formato_id=idformato).exclude(id=id)
        if direccion.exists():
            self.add_error('departamento', 'Registro que intenta guardar ya existe.')
        # if direccion.filter(orden=orden):
        #     self.add_error('orden', 'Orden que intenta registrar ya se encuentra registrado.')
        return cleaned_data

class DetalleDireccionFormatoPSForm(FormModeloBase):
    cargo = forms.ModelChoiceField(label="Cargo de responsable", required=True,
                                  queryset=DenominacionPuesto.objects.select_related().filter(status=True),
                                  widget=forms.Select(attrs={'col': '6','class':'select2'}))
    descripcion = forms.CharField(label=u'Pregunta', required=True,widget=forms.TextInput(attrs={'col': '6','placeholder': 'Pregunta a realizar'}))

    def clean(self):
        cleaned_data=super().clean()
        cargo=cleaned_data.get('cargo')
        descripcion=cleaned_data.get('descripcion')
        id = 0
        if hasattr(self.instancia, 'direccionformato'):
            id = getattr(self.instancia, 'id', 0)
            iddireccion = getattr(self.instancia, 'direccionformato_id', 0)
        else:
            iddireccion = getattr(self.instancia, 'id', 0)
        detalle=DetalleDireccionFormatoPS.objects.filter(status=True, cargo=cargo, descripcion__unaccent__iexact=descripcion,direccionformato_id=iddireccion).exclude(id=id)
        if detalle.exists():
            self.add_error('descripcion','Registro que intenta guardar ya existe.')
        return cleaned_data

class PreguntaGeneralFormatoPSForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Pregunta', required=True,widget=forms.TextInput(attrs={'col': '12','placeholder': 'Pregunta a realizar'}))

    def clean(self):
        cleaned_data=super().clean()
        descripcion=cleaned_data.get('descripcion')
        id=0
        if hasattr(self.instancia, 'formato'):
            id = getattr(self.instancia, 'id', 0)
            idformato = getattr(self.instancia, 'formato_id', 0)
        else:
            idformato = getattr(self.instancia, 'id', 0)
        detalle=DetalleDireccionFormatoPS.objects.filter(status=True, descripcion__unaccent__iexact=descripcion, formato_id=idformato).exclude(id=id)
        if detalle.exists():
            self.add_error('descripcion','Registro que intenta guardar ya existe.')
        return cleaned_data

class PazSalvoFormHV(FormModeloBase):
    departamento = forms.ModelChoiceField(Departamento.objects.filter(status=True,integrantes__isnull=False).distinct(), required=True,
                                        label=u'Dirección a la que perteneció', widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    cargo = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True), required=True,
                                        label=u'Cargo que ocupó', widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    jefeinmediato = forms.ModelChoiceField(label="Jefe inmediato", required=True,
                                           queryset=Persona.objects.select_related().filter(status=True),
                                           widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    tiporelacion = forms.ChoiceField(choices=TIPO_RELACION_LABORAL, label=u'Relación laboral', required=True,
                                     widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    motivosalida = forms.ChoiceField(label="Motivo de salida", required=True,
                                     choices=MOTIVO_SALIDA,
                                     widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    ultimaremuneracion = forms.FloatField(label="Última remuneración", required=True,
                                          widget=forms.TextInput(attrs={'col': '6', 'placeholder': '0.00', 'input_group': '$'}))
    fecha = forms.DateField(label=u"Fecha de salida", required=True, widget=DateTimeInput(format='%d-%m-%Y',attrs={'col':'6'}))

    def clean(self):
        cleaned_data=super().clean()
        hoy=datetime.now()
        hoy_i=datetime.strptime(hoy.strftime("%Y-%m-%d 00:00:00"),"%Y-%m-%d %H:%M:%S")
        hoy_f=datetime.strptime(hoy.strftime("%Y-%m-%d 23:59:59"),"%Y-%m-%d %H:%M:%S")
        id = 0
        if hasattr(self.instancia, 'persona_id'):
            idpersona = getattr(self.instancia, 'persona_id', 0)
            id = getattr(self.instancia, 'id', 0)
        else:
            idpersona = getattr(self.instancia, 'id', 0)
        pazsalvo=PazSalvo.objects.filter(status=True, persona_id=idpersona, fecha_creacion__range=(hoy_i, hoy_f)).exclude(id=id)
        if pazsalvo.exists():
            raise NameError('Usted ya cuenta con un certificado de pz y salvo activo actualmente.')
        return cleaned_data

class PazSalvoForm(FormModeloBase):
    persona = forms.ModelChoiceField(label="Funcionario", required=True,
                                    queryset=Persona.objects.select_related().filter(status=True),
                                    widget=forms.Select(attrs={'col': '12'}))
    departamento = forms.ModelChoiceField(label="Dirección", required=True,
                                          queryset=Departamento.objects.select_related().filter(status=True, tipo=1),
                                          widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    cargo = forms.ModelChoiceField(label="Cargo de responsable", required=True,
                                   queryset=DenominacionPuesto.objects.select_related().filter(status=True),
                                   widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    jefeinmediato = forms.ModelChoiceField(label="Jefe inmediato", required=True,
                                            queryset=Persona.objects.select_related().filter(status=True),
                                            widget=forms.Select(attrs={'col': '12'}))
    tiporelacion = forms.ChoiceField(label="Tipo de relación", required=True,
                                   choices=TIPO_RELACION_LABORAL,
                                   widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    motivosalida = forms.ChoiceField(label="Motivo de salida", required=True,
                                     choices=MOTIVO_SALIDA,
                                     widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    ultimaremuneracion = forms.FloatField(label="Última remuneración", required=True,
                                           widget=forms.TextInput(attrs={'col': '6', 'placeholder': '0.00', 'input_group': '$'}))
    fecha = forms.DateField(label=u"Fecha de salida", required=True, widget=DateTimeInput(format='%d-%m-%Y',attrs={'col':'6'}))

    def clean(self):
        cleaned_data=super().clean()
        hoy=datetime.now()
        # hoy_i=datetime.strptime(hoy.strftime("%Y-%m-%d 00:00:00"), "%Y-%m-%d %H:%M:%S")
        # hoy_f=datetime.strptime(hoy.strftime("%Y-%m-%d 23:59:59"), "%Y-%m-%d %H:%M:%S")
        persona=cleaned_data.get('persona')
        fecha=cleaned_data.get('fecha')
        id=getattr(self.instancia, 'id', 0)
        # pazsalvo=PazSalvo.objects.filter(status=True, persona=persona, fecha_creacion__range=(hoy_i, hoy_f)).exclude(id=id)
        pazsalvo=PazSalvo.objects.filter(status=True, persona=persona, fecha=fecha).exclude(id=id)
        if pazsalvo.exists():
            self.add_error('persona', 'Registro que intenta guardar ya existe.')
        return cleaned_data


class MatrizTramitePazySalvoForm(FormModeloBase):
    archivo = ExtFileField(label=u'Archivo', required=True,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato xlsx',
                           ext_whitelist=(".xlsx",), max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'accept': '.xlsx, .xls'}))


class RequisitoPazSalvoForm(FormModeloBase):
    nombre = forms.CharField(label="Título", required=True, widget=forms.TextInput(attrs={'col': '12','placeholder':'Describa el nombre del requisito'}))
    descripcion = forms.CharField(label=u'Detalle', required=False,widget=forms.Textarea(attrs={'rows': '5','placeholder': 'Descripción o leyenda del requisito'}))
    link = forms.CharField(label="Enlace ", required=False, widget=forms.TextInput(attrs={'col': '12','placeholder':'Coloque un link que desee proporcionar para este requisito'}))
    archivo = forms.FileField(label=u'Archivo de guia', required=False,
                               help_text=u'Tamaño Máximo permitido 4Mb, en formato pdf',
                               widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'}))
    mostrar = forms.BooleanField(initial=False, label=u'¿Mostrar?', required=False, widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'6'}))
    opcional = forms.BooleanField(initial=False, label=u'¿Opcional?', required=False, widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'6'}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['nombre'] = nombre = cleaned_data.get('nombre').strip()
        instancia = self.instancia
        id = getattr(instancia, 'id', 0)
        requisito = RequisitoPazSalvo.objects.filter(status=True, nombre__unaccent=nombre).exclude(id=id)
        if requisito.exists():
            self.add_error('nombre', 'Registro que intenta guardar ya existe.')

        archivo = cleaned_data.get('archivo')
        if archivo:
            max_tamano = 4 * 1024 * 1024  # 4 MB
            name_ = archivo._name
            ext = name_[name_.rfind("."):]
            if not ext.lower() == '.pdf':
                self.add_error('archivo', f'Solo se permite formato .pdf')
            if archivo.size > max_tamano:
                self.add_error('archivo', f'Archivo supera los 4 megas permitidos')
            # Asignar un nombre personalizado al archivo
            archivo.name = unidecode(generar_nombre("archivo_requisito_", archivo._name))
        elif instancia:
            archivo=instancia.archivo
        cleaned_data['archivo'] = archivo
        return cleaned_data

class SubirRequisitoPSForm(FormModeloBase):
    archivo = forms.FileField(label=u'Archivo', required=True,
                             help_text=u'Tamaño máximo permitido 4Mb y formato de archivo .pdf',
                             widget=forms.FileInput(attrs={'class':'p-1 text-secondary fs-6 ', 'col':'9'}))
    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        archivo = cleaned_data.get('archivo')
        if archivo:
            max_tamano = 4 * 1024 * 1024  # 4 MB
            name_=archivo._name
            ext = name_[name_.rfind("."):]
            if not ext.lower() == '.pdf':
                self.add_error('archivo', f'Solo se permite formato .pdf')

            if archivo.size > max_tamano:
                self.add_error('archivo', f'Archivo supera los 4 megas permitidos')
            # Asignar un nombre personalizado al archivo
            archivo.name = unidecode(generar_nombre("documento_requisito_", archivo._name))
        elif instancia:
            archivo=instancia.archivo
        cleaned_data['archivo'] = archivo
        return cleaned_data

class ValidarRequisitoForm(FormModeloBase):
    estado = forms.ChoiceField(label=u'Estado', choices=[tupla for tupla in ESTADOS_DOCUMENTOS_PAZ_SALVO if tupla[0] in [1,2,4]], required=True, widget=forms.Select(attrs={'col': '3'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Describa una observación.'}))


class RegistraDecimoForm(FormModeloBase):
        tiporegistro = forms.ChoiceField(label="Tipo de registro", required=True,
                                     choices=SELECCION_REGISTRO_DECIMO,
                                     widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

class ObservacionPazSalvoForm(FormModeloBase):
    observacion = forms.CharField(label=u'Nueva observación',
                                  required=True,
                                  widget=forms.Textarea(attrs={'rows': '5','placeholder': 'Observación a trasmitir', 'icon':'fa fa-commenting-o'}))


#-------------PAZ Y SALVO-------------

class PeriodoConstatacionAFForm(FormModeloBase):
    nombre = forms.CharField(label=u'Título', required=True,widget=forms.TextInput(attrs={'placeholder':'Describa el título del periodo por crear..'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=True,widget=DateTimeInput(format='%d-%m-%Y',attrs={'col':'6'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=True,widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    anio = forms.IntegerField(label=u"Año", initial=datetime.now().date().year, required=True, widget=forms.TextInput(attrs={'col':'6'}))
    detalle = forms.CharField(label=u'Detalle', required=False,widget=forms.Textarea(attrs={'rows': '5','placeholder': 'Describa el motivo de la creación del periodo.'}))
    baselegal = forms.CharField(label=u'Base legal', required=False,widget=forms.Textarea(attrs={'rows': '5','placeholder': 'Describa la base legal proporcionado para este periodo.', 'class':'ckeditors'}))
    activo = forms.BooleanField(initial=False, label=u'Periodo activo?', required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'data-switchery':True}))

    def clean(self):
        cleaned_data=super().clean()
        hoy=datetime.now().date()
        nombre = cleaned_data.get('nombre')
        fechainicio = cleaned_data.get('fechainicio')
        fechafin = cleaned_data.get('fechafin')
        id = getattr(self.instancia, 'id', 0)
        periodo = PeriodoConstatacionAF.objects.filter(status=True, nombre__unaccent__iexact=nombre).exclude(id=id)
        if periodo.exists():
            self.add_error('nombre', 'Registro que intenta guardar ya existe.')
        return cleaned_data

class DescargarCompromidoForm(FormModeloBase):
    periodo=forms.ModelChoiceField(label="Periodo de gastos",
                                   queryset=PeriodoGastosPersonales.objects.filter(status=True),
                                   required=True,
                                   widget=forms.Select(attrs={'col': '12'}))

class DescagarCargasFechasForm(FormModeloBase):
    todos = forms.BooleanField(label=u"¿Todos?", required=False,
                               widget=forms.CheckboxInput(attrs={'col': '5', 'data-switchery': True}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False,widget=DateTimeInput(format='%d-%m-%Y',attrs={'col':'8'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=False,widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'8'}))

class DescargarBajasAniosForm(FormModeloBase):
    todos = forms.BooleanField(label=u"¿Todos?", required=False,
                               widget=forms.CheckboxInput(attrs={'col': '7', 'data-switchery': True}))
    anioinicio = forms.IntegerField(label='Año inicio',
                               required=True, initial=2016,
                               widget=forms.NumberInput(attrs={'col': '6'}))
    aniofin = forms.IntegerField(label='Año fin',
                               required=True, initial=datetime.now().year,
                               widget=forms.NumberInput(attrs={'col': '6'}))

class ConstatacionFisicaForm(FormModeloBase):
    usuariobienes = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True,), required=False, label=u'Usuario que utiliza el activo', widget=forms.Select(attrs={'col':'12'}))
    estadoactual= forms.ModelChoiceField(queryset=EstadoProducto.objects.select_related().filter(status=True).exclude(id__in=[4, 5]).order_by('id'), required=True, label=u'Estado actual', widget=forms.Select(attrs={'col':'6','placeholder': 'Seleccione un estado'}))
    condicionestado= forms.ChoiceField(choices=ESTADO_BAJA, required=True, label=u'Condición', widget=forms.Select(attrs={'col':'6','placeholder': 'Seleccione la condición del activo'}))
    ubicacionbienes = forms.ModelChoiceField(queryset=Ubicacion.objects.select_related().filter(status=True,), required=False, label=u'Ubicación', widget=forms.Select(attrs={'col':'12','placeholder': 'Seleccione una ubicación'}))
    observacion = forms.CharField(label=u'Observación',required=False,widget=forms.Textarea({'col': '12','rows':'3','placeholder': 'Añade una observación'}))
    encontrado = forms.BooleanField(initial=False, required=False, label=u'¿Fue encontrado?', widget=forms.CheckboxInput(attrs={'data_checkbox': True, 'class': 'check_d'}))
    enuso = forms.BooleanField(initial=False, required=False, label=u'¿Esta en uso?', widget=forms.CheckboxInput(attrs={'data_checkbox': True, 'class': 'check_d'}))
    # perteneceusuario = forms.BooleanField(initial=False, required=False, label=u'¿Pertenece al usuario?', widget=forms.CheckboxInput(attrs={'data_checkbox': True, 'class': 'check_d'}))
    requieretraspaso = forms.BooleanField(initial=False, required=False, label=u'¿Requiere traspaso?', widget=forms.CheckboxInput(attrs={'data_checkbox': True, 'class': 'check_d'}))
    requieredarbaja = forms.BooleanField(initial=False, required=False, label=u'¿Requiere dar de baja?', widget=forms.CheckboxInput(attrs={'data_checkbox': True, 'class': 'check_d'}))


class SubirPagoForm(FormModeloBase):
    archivo = ExtFileField(label=u'Subir Archivo', required=False, help_text=u'Tamaño máximo permitido 10Mb, en formato pdf',
                               ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'class':'w-100 '}))


class RedAcademicaForm(FormModeloBase):
    tipo = forms.ModelChoiceField(label=u"Tipo de Red", queryset=TipoRedPersona.objects.filter(status=True).exclude(pk__in=[1, 4]), widget=forms.Select(attrs={'col': '12', 'class':'select2'}))
    enlace = forms.CharField(label=u'Enlace de Red', max_length=300, widget=forms.TextInput(attrs={'col': '12'}))


class ParRevisorArticuloForm(FormModeloBase):
    revista = forms.ModelChoiceField(label=u"Revista", queryset=RevistaInvestigacion.objects.filter(status=True, borrador=False).order_by('nombre'), widget=forms.Select(attrs={'col': '12','class':'select2'}))
    titulo = forms.CharField(label=u'Título Artículo', widget=forms.Textarea({'rows': '3', 'col': '12'}))
    fecharevision = forms.DateField(label=u"Fecha Revisión", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    archivo = ExtFileField(label=u'Certificado', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))


class ProyectoInvestigacionExternoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Título del Proyecto', widget=forms.Textarea({'rows': '3', 'col': '12'}))
    rol = forms.ModelChoiceField(label=u"Rol Participante", queryset=ParticipantesTipo.objects.filter(tipo=2, status=True).order_by('nombre'), widget=forms.Select(attrs={'col': '12','class':'select2'}))
    institucion = forms.CharField(label=u'Institución', max_length=1000, widget=forms.TextInput(attrs={'col': '12'}))
    financiamiento = forms.CharField(label=u'Financiamiento', max_length=1000, widget=forms.TextInput(attrs={'col': '12'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    archivo = ExtFileField(label=u'Archivo PDF', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))

class SesionForm(FormModeloBase):
    orden = forms.IntegerField(label=u'Orden de aparición', initial=0, widget=forms.NumberInput(attrs={'class': 'input_number','input_number':True, 'col': '4', 'placeholder': '0', 'controlwidth': '50%'}))
    nombre = forms.CharField(label=u'Nombre de sesion', widget=forms.Textarea({'rows': '3', 'col': '12'}))

class ResolucionSesionForm(FormModeloBase):
    numeroresolucion = forms.CharField(label=u'Nº. Resolución', widget=forms.TextInput(attrs={'col': '12','placeholder':'Ejem. OCAS-SO-21-2023'}),
                                       required=True)
    orden = forms.IntegerField(label=u'Orden de aparición', initial=0, widget=forms.NumberInput(attrs={'class': 'input_number','input_number':True, 'col': '6', 'placeholder': '0', 'controlwidth': '50%'}))
    fecha = forms.DateField(label=u"Fecha", required=True, initial=datetime.now().date(),
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'class': 'selectorfecha', 'col': '6'}))
    resuelve = forms.CharField(label=u'Resuelve', required=True, widget=forms.Textarea({'rows': '4','placeholder':'Describa lo que resuelve esta resolución'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True,
                           help_text=u'Tamaño máximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760,
                           widget=FileInput({'accept': '.pdf'}))

class TipoResolucionForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', widget=forms.Textarea({'rows': '3', 'col': '12'}))


class FechaInicioFinForm(FormModeloBase):
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True, initial=datetime.now().date(),
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha fin", required=True, initial=datetime.now().date(),
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))

class ComprimidoForm(FormModeloBase):
    estado_pazsalvo = forms.ChoiceField(label='Estado de paz y salvo', required=False,
                               choices=(('', "Todos"),) + ESTADO_PAZ_SALVO,
                               widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    estado = forms.ChoiceField(label='Estado de requisitos', required=False,
                                choices=(('',"Todos"),)+ESTADOS_DOCUMENTOS_PAZ_SALVO[:4],
                                widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    fechainicio = forms.DateField(label=u"Fecha de salida inicio", required=False,
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha de salida fin", required=False,
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))


class GestionarBajaActivoForm(FormModeloBase):
    ubicacionbodega = forms.CharField(label=u'Ubicación en Bodega', required=True, widget=forms.Textarea(attrs={'col': '12', 'rows': '2'}))
    # estado = forms.ModelChoiceField(label=u"Estado", queryset=EstadoProducto.objects.filter(status=True, gestionbaja=True), widget=forms.Select(attrs={'col': '12', 'class':'select2'}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['ubicacionbodega'] = cleaned_data.get('ubicacionbodega').upper().strip()
        return cleaned_data


class PeriodoTTHHForm(FormModeloBase):
    nombre = forms.CharField(label="Nombre", required=True, widget=forms.TextInput(attrs={'col': '12','placeholder':'Describa el nombre del periodo de requisito'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha fin", required=True, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    activo = forms.BooleanField(label=u'Activo', required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))

class RequisitoPeriodoTTHHForm(FormModeloBase):
    nombre = forms.CharField(label="Título", required=True, widget=forms.TextInput(attrs={'col': '12','placeholder':'Describa el nombre del requisito'}))
    descripcion = forms.CharField(label=u'Detalle', required=False,widget=forms.Textarea(attrs={'rows': '5','placeholder': 'Descripción o leyenda del requisito'}))
    link = forms.CharField(label="Enlace ", required=False, widget=forms.TextInput(attrs={'col': '12','placeholder':'Coloque un link que desee proporcionar para este requisito'}))
    archivo = forms.FileField(label=u'Archivo de guia', required=False, help_text=u'Tamaño Máximo permitido 4Mb, en formato pdf', widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'}))
    mostrar = forms.BooleanField(initial=False, label=u'¿Mostrar?', required=False, widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'6'}))
    opcional = forms.BooleanField(initial=False, label=u'¿Opcional?', required=False, widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'6'}))

class CubiculoForm(FormModeloBase):
    from sagest.models import PisosChoice
    # nombre = forms.CharField(required=True, label=u'Nombre', widget=forms.TextInput(attrs={'placeholder':'Describa el nombre del cubículo'}))
    numero = forms.IntegerField(required=True,label=u'Número',initial=0, widget=forms.NumberInput(attrs={'input_number':True,'col':'4'}))
    piso = forms.ChoiceField(label=u'Piso', required=True,initial=3, choices=PisosChoice.choices, widget=forms.Select(attrs={'class':'select2','col':'4'}))
    tiempo = forms.TimeField(label=u'Tiempo de uso', required=True, widget=forms.TimeInput(attrs={'col':'4'}))
    activo = forms.BooleanField(label=u'Activo', required=False, widget=forms.CheckboxInput(attrs={'col':'12', 'data-switchery':True}))

    def clean(self):
        from sagest.models import CubiculoCrai
        cleaned_data = super().clean()
        instancia=self.instancia
        id = getattr(instancia, 'id', 0)
        numero = int(cleaned_data.get('numero'))
        # piso = cleaned_data.get('piso')
        # nombre = cleaned_data.get('nombre')
        # if CubiculoCrai.objects.filter(nombre__unaccent__iexact=nombre,status=True).exclude(id=id):
        #     self.add_error('nombre', 'Nombre que digito ya se encuentra asignado a otro cubículo.')
        if CubiculoCrai.objects.filter(numero=numero, status=True).exclude(id=id):
            self.add_error('numero', 'Numero que dígito ya se encuentra asignado a otro cubículo')
        return cleaned_data

class ValidarRequisitoTTHHForm(FormModeloBase):
    estado = forms.ChoiceField(label=u'Estado', choices=[tupla for tupla in ESTADOS_DOCUMENTOS_REQUISITOS if tupla[0] in [1,2,4]], required=True, widget=forms.Select(attrs={'col': '3'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Describa una observación.'}))

class ComprimidoIngresoForm(FormModeloBase):
    from sagest.models import RequisitoPeriodotthh
    estado = forms.ChoiceField(label='Estado de requisitos', required=False,
                                choices=(('', "Todos"),)+ESTADOS_DOCUMENTOS_REQUISITOS[:4],
                                widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    requisito = forms.ModelMultipleChoiceField(label=u"Requisito", required=False, queryset=RequisitoPeriodotthh.objects.filter(mostrar=True, status=True).order_by('nombre'), widget=forms.SelectMultiple(attrs={'col': '12','class':'select2'}))


class BancoForm(FormModeloBase):
    nombre = forms.CharField(required=True, label=u'Nombre', widget=forms.TextInput(attrs={'placeholder':'Describa el nombre del banco'}))
    # trasaprotesto = forms.CharField(required=True,label=u'Trasa Protesto',initial=0, widget=forms.NumberInput(attrs={'input_number':True,'col':'4'}))
    codigo = forms.CharField(label=u'Código', required=True, widget=forms.TextInput(attrs={'col':'6'}))
    codigo_tthh = forms.IntegerField(label=u'Código de talento humano', required=True, widget=forms.TextInput(attrs={'col':'6'}))

    def clean(self):
        from sagest.models import CubiculoCrai
        cleaned_data = super().clean()
        instancia=self.instancia
        id = getattr(instancia, 'id', 0)
        codigo = int(cleaned_data.get('codigo'))
        # piso = cleaned_data.get('piso')
        # nombre = cleaned_data.get('nombre')
        # if CubiculoCrai.objects.filter(nombre__unaccent__iexact=nombre,status=True).exclude(id=id):
        #     self.add_error('nombre', 'Nombre que digito ya se encuentra asignado a otro cubículo.')
        if Banco.objects.filter(codigo=codigo, status=True).exclude(id=id):
            self.add_error('codigo', 'Código de banco ya se encuentra registrado')
        return cleaned_data


#Equipos de computo
class TerminoyCondicionForm(FormModeloBase):
    titulo = forms.CharField(label=u"Título", widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12', 'placeholder': u'Ingrese el título...'}))
    descripcion = forms.CharField(required=True, label=u"Descripción", widget=forms.Textarea(attrs={'col': '12'}))
    activo = forms.BooleanField(label=u'¿Se encuentra activo?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['titulo'] = titulo = cleaned_data.get('titulo').upper().strip()
        id=getattr(self.instancia, 'id', 0)
        termino = TerminosCondicionesEquipoComputo.objects.filter(status=True, titulo__unaccent=titulo).exclude(id=id)
        if termino.exists():
            self.add_error('titulo','Registro que intenta guardar ya existe.')
        return cleaned_data

class ConfiguracionEquipoComputoForm(FormModeloBase):
    titulo = forms.CharField(required=True, label=u"Título", widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12', 'placeholder': u'Ingrese el título...'}))
    descripcion = forms.CharField(required=True, label=u"Descripción", widget=forms.Textarea(attrs={'class': 'form-control', 'col': '12',  'placeholder': u'Ingrese una descripción...', 'rows':'3'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", input_formats=['%Y-%m-%d'],widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    fechafin = forms.DateField(label=u"Fecha fin", input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    horainiciouso = forms.TimeField(label=u"Hora inicio de uso", required=True, widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'col': '4'}))
    horafinuso = forms.TimeField(label=u"Hora fin de uso", required=True, widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'col': '4'}))
    # tiempolimite = forms.TimeField(label=u"Tiempo Límite", required=True, widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'col': '4'}))
    activo = forms.BooleanField(label=u'¿Se encuentra activo?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['titulo'] = titulo = cleaned_data.get('titulo').upper().strip()
        cleaned_data['descripcion'] = cleaned_data.get('descripcion').upper().strip()
        id=getattr(self.instancia, 'id', 0)
        config = ConfiguracionEquipoComputo.objects.filter(status=True, titulo__unaccent=titulo).exclude(id=id)
        if config.exists():
            self.add_error('titulo','Registro que intenta guardar ya existe.')
        return cleaned_data


class EntregarEquipoComputoForm(FormModeloBase):
    solicitud = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    observacion = forms.CharField(required=False, label=u"Observación", widget=forms.Textarea(attrs={'col': '12', 'rows': '2', 'placeholder': 'Ingrese una observación...'}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['observacion'] = cleaned_data.get('observacion').upper().strip()
        return cleaned_data


class GestionSolicitudECForm(FormModeloBase):

    choices_filtrados = [choice for choice in MY_ESTADO_SOLICITUD_EQUIPO_COMPUTO if choice[0] not in {4}]

    solicitud = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    estadosolicitud = forms.ChoiceField(label=u"Estado", required=True, initial=2, choices=choices_filtrados, widget=forms.Select(attrs={'col': '12'}))
    equipocomputo = forms.ModelChoiceField(label=u"Asignar equipo", queryset=EquipoComputo.objects.filter(status=True, activo=True, estado=1), required=False, widget=forms.Select({'col': '12',}))
    tipodocumento = forms.ChoiceField(label=u"Documento recibido", choices=MY_TIPO_DOCUMENTO_EQUIPO_COMPUTO, initial=1, required=False, widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    descripciondocumento = forms.CharField(label=u"Descripción", required=False, widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Ingrese una descripción...'}))
    observacion = forms.CharField(required=False, label=u"Observación", widget=forms.Textarea(attrs={'col': '12', 'rows': '2', 'placeholder': 'Ingrese una observación...'}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['observacion'] = cleaned_data.get('observacion').upper().strip()
        cleaned_data['descripciondocumento'] = cleaned_data.get('descripciondocumento').upper().strip()
        return cleaned_data

class EquipoComputoForm(FormModeloBase):
    activo = forms.BooleanField(label=u'¿Disponible?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))


class SolicitudEquipoComputoForm(FormModeloBase):

    choices_filtrados = [choice for choice in MY_ESTADO_SOLICITUD_EQUIPO_COMPUTO if choice[0] not in {4, 5}]

    fechauso = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}))
    solicitante = forms.ModelChoiceField(label=u"Solicitante", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=True, widget=forms.Select({'col': '8',}))
    estadosolicitud = forms.ChoiceField(label=u"Estado de la solicitud", choices=choices_filtrados, initial=3, required=True, widget=forms.Select(attrs={'col': '4', 'class':'select2'}))
    equipocomputo = forms.ModelChoiceField(label=u"Equipo de computo", queryset=EquipoComputo.objects.filter(status=True, activo=True, estado=1), required=False, widget=forms.Select(attrs={'col': '8', 'class':'select2'}))
    tipodocumento = forms.ChoiceField(label=u"Documento recibido", choices=MY_TIPO_DOCUMENTO_EQUIPO_COMPUTO, initial=1, required=False, widget=forms.Select(attrs={'col': '4', 'class':'select2'}))
    descripciondocumento = forms.CharField(label=u"Descripción", required=False, widget=forms.TextInput(attrs={'col': '8', 'placeholder': 'Ingrese una descripción...'}))
    motivo = forms.CharField(label=u"Motivo", required=True, widget=forms.Textarea(attrs={'col': '12', 'rows': '2'}))
    # horainicio = forms.TimeField(label=u"Hora inicio", required=True, widget=DateTimeInput(format='%H:%M', attrs={'class': 'selector', 'col': '4'}))
    # horafin = forms.TimeField(label=u"Hora fin", required=True, widget=DateTimeInput(format='%H:%M', attrs={'class': 'selector', 'col': '4'}))
    observacion = forms.CharField(required=False, label=u"Observación", widget=forms.Textarea(attrs={'col': '12', 'rows': '2', 'placeholder': 'Ingrese una observación...'}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['observacion'] = cleaned_data.get('observacion').upper().strip()
        cleaned_data['motivo'] = cleaned_data.get('motivo').upper().strip()
        cleaned_data['descripciondocumento'] = cleaned_data.get('descripciondocumento').upper().strip()
        fecha_actual = datetime.now().date()
        fecha_uso = cleaned_data.get('fechauso')
        if fecha_uso < fecha_actual:
            self.add_error('fechauso', 'La fecha seleccionada no puede ser menor a la fecha actual.')
        return cleaned_data


class SolicitudPrestamoECForm(FormModeloBase):
    fechauso = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}))
    # horainicio = forms.TimeField(label=u"Hora inicio", required=True, widget=DateTimeInput(format='%H:%M', attrs={'class': 'selector', 'col': '4'}))
    # horafin = forms.TimeField(label=u"Hora fin", required=True, widget=DateTimeInput(format='%H:%M', attrs={'class': 'selector', 'col': '4'}))
    motivo = forms.CharField(label=u"Motivo", required=True, widget=forms.Textarea(attrs={'col': '12', 'rows': '2'}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['motivo'] = cleaned_data.get('motivo').upper().strip()
        fecha_actual = datetime.now().date()
        fecha_uso = cleaned_data.get('fechauso')
        if fecha_uso < fecha_actual:
            self.add_error('fechauso', 'La fecha seleccionada no puede ser menor a la fecha actual.')
        return cleaned_data

class PreguntaEstadoECForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", required=True, widget=forms.Textarea(attrs={'col': '12', 'rows': '2'}))
    activo = forms.BooleanField(label=u'¿Activo?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['descripcion'] = descripcion = cleaned_data.get('descripcion').upper().strip()
        id=getattr(self.instancia, 'id', 0)
        pregunta = PreguntaEstadoEC.objects.filter(status=True, descripcion__unaccent=descripcion).exclude(id=id)
        if pregunta.exists():
            self.add_error('descripcion','Registro que intenta guardar ya existe.')
        return cleaned_data



class UsuarioPermisoForm(FormModeloBase):
    persona = forms.ModelChoiceField(Persona.objects.filter(status=True), required=True, label=u'Funcionario',
                                         widget=forms.Select({'col': '12', 'class':'select2', 'api':'true'}))
    cargo_text = forms.CharField(label=u"Cargo de usuario externo", required=False, widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Solo para usuarios que no se encuentran bajo unemi...'}))
    unidadorganica = forms.ModelChoiceField(Departamento.objects.filter(objetivoestrategico__periodopoa_id__gte=2,
                                                                        objetivoestrategico__status=True,
                                                                        integrantes__isnull=False).order_by('-id').distinct(),
                                            required=True, label=u'Departamento',
                                            widget=forms.Select(attrs={'col': '12', 'class': 'select2', 'api':'true'}))
    gestion = forms.ModelChoiceField(SeccionDepartamento.objects.filter(status=True),
                                     required=False, label=u'Gestión',
                                     widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    carrera = forms.ModelChoiceField(Carrera.objects.filter(status=True).order_by('nombre'), required=False,
                                     label=u'Carrera', widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    tipousuario = forms.ChoiceField(choices=TIPOS_USUARIO, required=False, label=u'Tipo Usuario',
                                    widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    activo = forms.BooleanField(label=u'¿Se encuentra activo?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'data-switchery': True}))
    firmainforme = forms.BooleanField(label=u'¿Firma informe semestral?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'data-switchery': True}))


    def clean(self):
        cleaned_data = super().clean()
        instancia=self.instancia
        id = getattr(instancia, 'id', 0)
        usuario = cleaned_data.get('persona').usuario
        unidadorganica = cleaned_data.get('unidadorganica')
        gestion = cleaned_data.get('gestion')
        carrera = cleaned_data.get('carrera')
        tipousuario = int(cleaned_data.get('tipousuario'))
        activo = cleaned_data.get('activo')
        tipo = encrypt_id(self.data['idp']) if not instancia else instancia.tipopermiso
        filtro = Q(userpermiso=usuario, status=True, tipopermiso=tipo)
        name_attr=''
        if tipo in [2, 3]:
            name_attr = 'unidadorganica'
            if gestion:
                # filtro &= Q(gestion=gestion)
                name_attr = 'gestion'
            elif carrera:
                # filtro &= Q(carrera=carrera)
                name_attr = 'carrera'
            # else:
            filtro &= Q(unidadorganica=unidadorganica, gestion=gestion, carrera=carrera)
        # if tipo == 4 and tipousuario == 5 and activo:
        if tipo == 4 and activo:
            UsuarioEvidencia.objects.filter(tipopermiso=tipo, status=True, tipousuario=tipousuario, activo=True).exclude(id=id).update(activo=False)
        if UsuarioEvidencia.objects.filter(filtro).exclude(id=id):
            if name_attr:
                self.add_error(name_attr, 'Funcionario ya esta registrado en esta sección')
            self.add_error('persona', 'Funcionario que intenta adicionar ya esta registrado')
        return cleaned_data


class SeguimientoForm(FormModeloBase):
    detalle = forms.CharField(required=True, label=u'Motivo del seguimiento', widget=forms.Textarea({'rows': '3', 'col': '12', 'icon':'fa fa-comments'}))

    def clean(self):
        cleaned_data=super().clean()
        return cleaned_data

class ProcesoEleccionForm(FormModeloBase):
    descripcion = forms.CharField(max_length=1000, label=u"Nombre de proceso",  required=True,
                                  widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Describa el nombre del proceso de sufragio'}))
    periodoacademico = forms.ModelChoiceField(Periodo.objects.filter(status=True, visible=True).exclude(tipo_id__in=[1,3]),
                                        required=True, label=u'Periodo académico',
                                        widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    activo = forms.BooleanField(initial=True, label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))

    def clean(self):
        cleaned_data = super().clean()
        periodo = cleaned_data.get('periodoacademico')
        activo = cleaned_data.get('activo')
        instancia = self.instancia
        id = getattr(instancia, 'id', 0)
        # if ProcesoEleccion.objects.filter(periodoacademico=periodo, status=True).exclude(id=id).exists():
        #     self.add_error('periodoacademico', 'Ya existe un proceso de elección para el periodo seleccionado')
        if activo:
            ProcesoEleccion.objects.filter(status=True).update(activo=False)
        return cleaned_data

class ValidarSolicitudForm(FormModeloBase):
    estado = forms.ChoiceField(choices=ESTADO_JUSTIFICACION_PROCESO[1:], required=True, label=u'Estado',
                               widget=forms.Select(attrs={'col': '12', 'class': 'select2', 'w':'50', 'icon':'bi bi-filter'}))
    observacion = forms.CharField(max_length=1000, label=u"Observación", required=True, widget=forms.Textarea({'rows': '3', 'col': '12', 'icon':'bi bi-chat-right-text'}))


class ActivoBodegaVirtualForm(FormModeloBase):
    observacion = forms.CharField(max_length=1000, label=u"Observación", required=False,
                                  widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text'}))
    fotoactivo = forms.FileField(label=u'Agregar foto del activo', required=True,
                    help_text=u'Tamaño Máximo permitido 2Mb, en formato jpg, jpeg, png',
                    widget=forms.FileInput(attrs={'col': '12', 'accept': '.png, .jpg, .jpeg', 'dropify': True, 'icon': 'bi bi-file-image'}))

class DeclaracionesPersonalForm(FormModeloBase):
    ESTADO_PERSONAL_DEC = (
        (0, 'Todos'),
        (1, 'Activo'),
        (2, 'Inactivo'),
    )
    tipodeclaracion = forms.ChoiceField(label=u"Tipo Declaración", required=False, choices=TIPO_DECLARACION,
                                        widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    fachadesde = forms.DateField(label=u"Fecha generacion desde", input_formats=['%Y-%m-%d'], required=False,
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    fachahasta = forms.DateField(label=u"Fecha generacion hasta", input_formats=['%Y-%m-%d'], required=False,
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    estado = forms.ChoiceField(label=u"Estado", required=False, choices=ESTADO_PERSONAL_DEC,
                                 widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

class DescargarActasConstatacionForm(FormModeloBase):
    estado = forms.ChoiceField(label=u"Estado de acta", required=False, choices=ESTADO_ACTA_CONSTATACION,
                               widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))



