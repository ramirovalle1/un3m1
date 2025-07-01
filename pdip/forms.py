# -*- coding: UTF-8 -*-
from datetime import datetime
from fileinput import FileInput

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms import DateTimeInput
from django.db.models import Q
from core.custom_forms import FormModeloBase
from pdip.models import ESTADOS_PAGO_REQUISITO, PasoProcesoPago, RequisitoPasoPago, RequisitoPagoDip, PerfilPuestoDip, \
    PERFIL_CONTRATO, TIPO_CAMPO, PlantillaContratoDip, ContratoDip, CertificacionPresupuestariaDip, CampoContratoDip, \
    Gestion, TIPO_GRUPO, TIPO_PAGO, OrdenFirmaActaPago
from postulaciondip.models import ValorPorHoraInformeContratacion, Requisito, ResponsabilidadFirma
from sagest.models import DenominacionPuesto, IvaAplicado, SeccionDepartamento, AnioEjercicio, TIPO_SISTEMA, \
    Departamento
from sga.models import Periodo, Canton, Persona, ProfesorMateria, CuentaBancariaPersona, Carrera, DIAS_CHOICES, Turno, \
    Malla, TipoProfesor
from sga.forms import ExtFileField, deshabilitar_campo, campo_modobloqueo


def deshabilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True
    form.fields[campo].widget.attrs['disabled'] = True

def campo_requerido(form, campo):
    form.fields[campo].widget.attrs['required'] = True

def campo_no_requerido(form, campo):
    form.fields[campo].widget.attrs['required'] = False

def habilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = False
    form.fields[campo].widget.attrs['disabled'] = False


def campo_solo_lectura(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True


class RequisitoPagoDipForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True,
                             widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "Nombre"}))
    leyenda = forms.CharField(label=u'Leyenda', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Formato Solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png, docx',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png", ".docx"), max_upload_size=8194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg docx'}))


class PerfilPuestoDipForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True,
                             widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "Nombre"}))

class ActividadesForm(forms.Form):
    descripcion = forms.CharField(label=u'Actvidad', required=True,
                             widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "Actividad"}))
class SecuenciaMemoActPosgradoForm(forms.Form):
    secuencia = forms.CharField(label=u'Secuencia: ', required=True,
                             widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "Nombre"}))


class SolicitudPagoForm(forms.Form):
    cuentabancaria = forms.ModelChoiceField(label=u"Cuenta Bancaria donde desea recibir el dinero:",
                                            queryset=CuentaBancariaPersona.objects.filter(status=True).order_by(
                                                'banco__nombre'),
                                            required=True, widget=forms.Select(attrs={'formwidth': '100%'}))


class ProcesoPagoForm(forms.Form):
    perfil = forms.ChoiceField(choices=PERFIL_CONTRATO, label=u'Perfil', required=False,
                               widget=forms.Select(attrs={'formwidth': '50%'}))
    version = forms.IntegerField(label=u'Versión', required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-10', 'decimal': '0', 'formwidth': '50%'}))
    nombre = forms.CharField(label=u'Nombre', required=True,
                             widget=forms.Textarea({'rows': '1', 'formwidth': '100%', "tooltip": "Nombre"}))
    descripcion = forms.CharField(label=u'Descripción', required=True,
                                  widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "Descripción"}))
    activo = forms.BooleanField(label=u"Desea mostrarlo?", required=False,
                                 widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class PasoProcesoPagoForm(forms.Form):
    pasoanterior = forms.ModelChoiceField(label=u"Paso Anterior",
                                          queryset=PasoProcesoPago.objects.filter(status=True).order_by('numeropaso'),
                                          required=False, widget=forms.Select(attrs={'formwidth': '40%'}))
    estadovalida = forms.ChoiceField(choices=ESTADOS_PAGO_REQUISITO, label=u'Estado de validación', required=False,
                                     widget=forms.Select(attrs={'formwidth': '30%'}))
    estadorechazado = forms.ChoiceField(choices=ESTADOS_PAGO_REQUISITO, label=u'Estado de rechazado', required=False,
                                        widget=forms.Select(attrs={'formwidth': '30%'}))
    valida = forms.ModelChoiceField(label=u"Validado Por",
                                    queryset=DenominacionPuesto.objects.filter(status=True).order_by('descripcion'),
                                    required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    carga = forms.ModelChoiceField(label=u"Cargado Por",
                                   queryset=DenominacionPuesto.objects.filter(status=True).order_by('descripcion'),
                                   required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    numeropaso = forms.IntegerField(label=u'Nro. de paso', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-10', 'formwidth': '40%', 'decimal': '0'}))
    tiempoalerta_carga = forms.IntegerField(label=u'Tiempo de Alerta Carga (Horas)', required=True,
                                            widget=forms.TextInput(
                                                attrs={'class': 'imp-10', 'formwidth': '30%', 'decimal': '0'}))
    tiempoalerta_validacion = forms.IntegerField(label=u'Tiempo de Alerta Validación (Horas)', required=True,
                                                 widget=forms.TextInput(
                                                     attrs={'class': 'imp-10', 'formwidth': '30%', 'decimal': '0'}))
    finaliza = forms.BooleanField(label=u"¿Último paso?", required=False,
                                  widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    beneficiario = forms.BooleanField(label=u"¿Muestra a beneficiario?", required=False,
                                      widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    genera_informe = forms.BooleanField(label=u"¿Genera Informe?", required=False,
                                        widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    carga_archivo = forms.BooleanField(label=u"¿Carga Archivo?", required=False,
                                       widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    valida_archivo = forms.BooleanField(label=u"¿Valida Archivo?", required=False,
                                        widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    descripcion = forms.CharField(label=u'Descripción', required=True,
                                  widget=forms.Textarea({'rows': '1', 'formwidth': '100%', "tooltip": "Descripción"}))
    leyenda = forms.CharField(label=u'Mensaje de Ayuda', widget=forms.Textarea(attrs={'rows': '1'}), required=False)
    requisitos = forms.ModelMultipleChoiceField(label=u'Requisitos',
                                                queryset=RequisitoPagoDip.objects.filter(status=True).order_by(
                                                    'nombre'), required=False)


class ReemplazarDocumentoRequisitoSolicitudForm(forms.Form):
    archivo = ExtFileField(label=u'Archivo solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png, docx',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png", ".docx"), max_upload_size=8194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg docx'}))


class CampoContratoDipForm(forms.Form):
    descripcion = forms.CharField(label=u"Nombre", required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '40%'}))
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

    def add(self):
        campo_requerido(self, 'descripcion')
        campo_requerido(self, 'tipo')
        campo_requerido(self, 'identificador')


class PlantillaContratoDipForm(forms.Form):
    perfil = forms.ModelChoiceField(label=u"Perfil",
                                    queryset=PerfilPuestoDip.objects.filter(status=True).order_by('nombre'),
                                    required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(label=u"Descripción", required=False,
                                  widget=forms.TextInput(attrs={'class': 'form-control', 'formwidth': '100%'}))
    anio = forms.IntegerField(initial=datetime.now().year, label=u"Año",
                              widget=forms.TextInput(attrs={'class': ' form-control', 'decimal': '0', 'formwidth': '50%'}))
    vigente = forms.BooleanField(label=u"¿Usa actualmente?", required=False,
                                 widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    archivo = ExtFileField(label=u'Plantilla', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato doc,docx',
                           ext_whitelist=(".docx", ".doc",), max_upload_size=4194304)
class GestionarContratoDipForm(forms.Form):
    codigocontrato = forms.CharField(label=u"Código de contrato", required=False,
                                     widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '40%'}))
    plantilla = forms.ModelChoiceField(label=u'Plantilla',
                                       queryset=PlantillaContratoDip.objects.filter(status=True, vigente=True).order_by(
                                           'anio'), required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    certificacion = forms.ModelChoiceField(CertificacionPresupuestariaDip.objects.filter(status=True), required=True, label=u'Certificación',widget=forms.Select(attrs={'formwidth': '50%'}))


    fechainicio = forms.DateField(label=u"Fecha Inicio", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'formwidth': '50%'}),
                                  required=False)
    fechafin = forms.DateField(label=u"Fecha Fin", initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y',
                                                    attrs={'class': 'selectorfecha', 'formwidth': '50%'}),
                               required=False)
    rmu = forms.FloatField(label=u"Valor", initial="0.00", required=True,widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%'}))
    ivaAplicado = forms.ModelChoiceField(IvaAplicado.objects.filter(status=True), required=True, label=u'Aplica Iva',widget=forms.Select(attrs={'formwidth': '50%'}))
    valorIva = forms.DecimalField(label=u"Iva calculado", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', 'readonly': 'readonly'}))
    valorTotal = forms.DecimalField(initial='0.00', label=u'Total Valor', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%', 'readonly': 'readonly'}))
    numeroCuota = forms.IntegerField(label=u" Nùmero de pagos", initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '50%', 'type': 'number', 'min': '0'}))
    descripcion = forms.CharField(label=u'Observación para historial', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class ContratoDipForm(FormModeloBase):
    codigocontrato = forms.CharField(label=u"Código de contrato", required=True,widget=forms.TextInput(attrs={'class': 'imp-codigo', 'col': '3'}))
    seccion = forms.ModelChoiceField(queryset=Gestion.objects.select_related().filter(status=True), required=True,label=u'Departamento', widget=forms.Select(attrs={ 'col': '9'}))
    responsable = forms.CharField(label='Responsable',required=False, widget=forms.TextInput(attrs={ 'col': '6','readonly':True}))
    responsablesub = forms.CharField(label='Responsable Sub',required=False, widget=forms.TextInput(attrs={ 'col': '6','readonly':True}))
    persona = forms.IntegerField(initial=0, required=False, label=u'Profesional',widget=forms.TextInput(attrs={'select2search': 'true', 'col': '12'}))
    validadorgp = forms.IntegerField(initial=0, required=False, label=u'Analista Validador',widget=forms.TextInput(attrs={'select2search': 'true', 'col': '12'}))
    tipogrupo = forms.ChoiceField(choices=TIPO_GRUPO, label=u'Tipo grupo', required=False, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    tipopago = forms.ChoiceField(choices=TIPO_PAGO, label=u'Tipo pago', required=False, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    cargo = forms.ModelChoiceField(queryset=PerfilPuestoDip.objects.select_related().filter(status=True), required=True,label=u'Cargo', widget=forms.Select(attrs={'col': '12'}))
    plantilla = forms.ModelChoiceField(label=u'Tipo Contratación',queryset=PlantillaContratoDip.objects.filter(status=True, vigente=True).order_by('anio'), required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    nombreareaprograma = forms.ModelMultipleChoiceField(Gestion.objects.select_related().filter(status=True), required=False, label=u'Area o programa', widget=forms.SelectMultiple(attrs={'formwidth': '100%', 'col': '12', 'style': 'width:100%'}))
    carrera = forms.ModelMultipleChoiceField(Carrera.objects.filter(niveltitulacion_id=4, status=True, activa=True), required=False, label=u'Carrera', widget=forms.SelectMultiple(attrs={'formwidth': '100%', 'col': '12', 'style': 'width:100%'}))
    certificacion = forms.ModelChoiceField(CertificacionPresupuestariaDip.objects.filter(status=True), required=True, label=u'Certificación',widget=forms.Select(attrs={'col': '12'}))
    fechapartida = forms.CharField(label=u"Fecha de partida", required=False,widget=forms.TextInput(attrs={'class': 'imp-codigo', 'col': '6','readonly':True}))
    codigopartida = forms.CharField(label=u"Código de partida", required=False,widget=forms.TextInput(attrs={'class': 'imp-codigo', 'col': '6','readonly':True}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", initial=datetime.now().date() ,widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}),required=True)
    fechafin = forms.DateField(label=u"Fecha Fin", initial=datetime.now().date() ,widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}),required=True)
    rmu = forms.FloatField(label=u"RMU", initial="0.00", required=True,widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '6'}))
    ivaAplicado = forms.ModelChoiceField(IvaAplicado.objects.filter(status=True), required=True, label=u'Aplica Iva',widget=forms.Select(attrs={'col': '6'}))
    valorIva = forms.DecimalField(label=u"Iva calculado", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '6', 'readonly': 'readonly'}))
    valorTotal = forms.DecimalField(initial='0.00', label=u'Total Valor', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'col': '6', 'readonly': 'readonly'}))
    #numeroCuota = forms.IntegerField(label=u" Nùmero de pagos", initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'formwidth': '50%', 'type': 'number', 'min': '0'}))
    descripcion = forms.CharField(label=u'Observación para historial', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Contrato legalizado ambas partes', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=forms.FileInput(attrs={'accept': 'application/pdf', 'formwidth': '100%', 'data-allowed-file-extensions': 'pdf'}))

    def del_fields(self, field):
        del self.fields[field]

class DisponerContratoDipForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class ContratoMetodoPago(forms.Form):
    contratodip = forms.ModelChoiceField(label=u"Contrato", queryset=ContratoDip.objects.filter(status=True),
                                         required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    numerocuota = forms.IntegerField(label=u"Número de Cuota", required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall', 'value': '1', 'decimal': '0', 'formwidth': '25%'}))
    valorcuota = forms.FloatField(label=u"Valor Cuota", initial="0.00", required=True, widget=forms.TextInput(
        attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '25%'}))
    cancelado = forms.BooleanField(label=u"¿Cuota Cancelada?", required=False,
                                   widget=forms.CheckboxInput(attrs={'formwidth': '25%'}))


class CertificacionPresupuestariaDipForm(forms.Form):
    codigo = forms.CharField(label=u"Codigo", required=True, widget=forms.TextInput(attrs={ 'formwidth': '30%'}))
    descripcion = forms.CharField(label=u"Descripción", required=False, widget=forms.TextInput(attrs={ 'formwidth': '100%'}))
    partida = forms.CharField(label=u"Partida", required=False, widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '30%'}))
    valor = forms.FloatField(label=u"Valor", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '25%'}))
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '35%'}), required=False)
    archivo = ExtFileField(label=u'Soporte', required=False,
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png", ".docx"), max_upload_size=8194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg docx'}))

class ArchivoInformesForm(forms.Form):
    archivo = ExtFileField(label=u'Subir Archivo', required=True,
                               help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                               max_upload_size=10485760, widget=forms.FileInput(attrs={'accept': 'application/pdf', 'formwidth': '100%', 'data-allowed-file-extensions': 'pdf'}))


class DocumentoContratosForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", required=True, widget=forms.TextInput(attrs={ 'formwidth': '50%'}))
    codigo = forms.CharField(label=u"Codigo", required=True, widget=forms.TextInput(attrs={ 'formwidth': '50%'}))
    campo = forms.ModelChoiceField(label=u"Campo",
                                            queryset=CampoContratoDip.objects.filter(status=True).order_by(
                                                'descripcion'),
                                            required=True, widget=forms.Select(attrs={'formwidth': '100%'}))

class HorarioClasesContratoForm(FormModeloBase):
    dia = forms.ChoiceField(choices=DIAS_CHOICES, label=u"Día:", widget=forms.Select(attrs={'class':'select2 form-control', 'style':'width:100%', 'col': '12'}))
    inicio = forms.DateField(label=u'Fecha inicio:', required=False, widget=DateTimeInput( attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    fin = forms.DateField(label=u'Fecha fín:', required=False, widget=DateTimeInput( attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    turno = forms.ModelMultipleChoiceField(required=True, queryset=Turno.objects.filter(status=True, sesion_id=19), label=u'Turno:', widget=forms.SelectMultiple(attrs={'class':'form-control', 'col':'12', 'style':'width:100%'}))

class FechaMaximoBitacoraForm(FormModeloBase):
    fechaaplazo = forms.DateField(label=u"Fecha aplazado", required=True,
                                 widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))

class GrupoRevisionPagoContratoForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre grupo", required=True, widget=forms.TextInput(attrs={'col': '12'}))
    persona = forms.ModelChoiceField(label=u"Persona", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': '100%'}))
    personacontrato = forms.ModelMultipleChoiceField(label=u"Persona contratado", queryset=Persona.objects.none(), required=False, widget=forms.SelectMultiple(attrs={'col': '12', 'style': '100%'}))
    def edit(self, pk):
        self.fields['persona'].queryset = Persona.objects.filter(id=pk)
        self.fields['persona'].initial = [pk]

    def edit_personacontrato(self,pks):
        self.fields['personacontrato'].queryset = Persona.objects.filter(id__in=pks)
        self.fields['personacontrato'].initial = pks

class DepartamentoPosgradoForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre departamento", required=True, widget=forms.TextInput(attrs={'col': '12'}))
    responsable = forms.ModelChoiceField(label=u"Responsable", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': '100%'}))
    responsable_subrogante = forms.ModelMultipleChoiceField(label=u"Responsable subrogante", queryset=Persona.objects.none(), required=False, widget=forms.SelectMultiple(attrs={'col': '12', 'style': '100%'}))

    def edit(self, pk):
        self.fields['responsable'].queryset = Persona.objects.filter(id=pk)
        self.fields['responsable'].initial = [pk]

    def res_subrogante(self,pks):
        self.fields['responsable_subrogante'].queryset = Persona.objects.filter(id__in=pks)
        self.fields['responsable_subrogante'].initial = pks

class GestionPosgradoForm(FormModeloBase):
    gestion = forms.CharField(label=u"Nombre de gestion", required=True, widget=forms.TextInput(attrs={'col': '12'}))
    cargo = forms.CharField(label=u"Nombre de cargo", required=True, widget=forms.TextInput(attrs={'col': '12'}))
    responsable = forms.ModelChoiceField(label=u"Responsable", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': '100%'}))
    responsablesubrogante = forms.ModelChoiceField(label=u"Responsable subrogante", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': '100%'}))

    def edit(self, pk):
        self.fields['responsable'].queryset = Persona.objects.filter(id=pk)
        self.fields['responsable'].initial = [pk]

    def res_subrogante(self,pk):
        self.fields['responsablesubrogante'].queryset = Persona.objects.filter(id=pk)
        self.fields['responsablesubrogante'].initial = [pk]

class SolicitudInformePagoForm(FormModeloBase):
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True,widget=DateTimeInput(attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha fin", required=True,widget=DateTimeInput(attrs={'col': '6'}))

class BitacoraActividadDiariaFixedForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=10000, widget=forms.Textarea({'row': '3', 'col': '12'}), required=False)
    link = forms.CharField(max_length=1000, label=u"Link", widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}), required=False)
    tiposistema = forms.ChoiceField(choices=TIPO_SISTEMA, label=u'Sistema', required=False, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    departamento_requiriente = forms.ModelChoiceField(Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=False, label=u'Departamento solicita', widget=forms.Select(attrs={'class': 'select2', 'col': '12', 'style': 'width:100%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png', ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"), required=False, max_upload_size=12582912, widget=forms.FileInput({'style': 'width:100%;', 'class': 'form-control', 'col': '12', 'accept': '.doc, .docx,.xls, .xlsx, application/pdf, image/jpeg, image/jpg, image/png'}))


class RecursoPresupuestarioForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=10000, widget=forms.Textarea({'row': '3', 'col': '12'}), required=False)


class CabeceraRecursoPresupuestarioPosgradoForm(FormModeloBase):
    malla = forms.ModelChoiceField(label=u"Malla", queryset=Malla.objects.filter(Q(carrera__niveltitulacion_id=4) | Q(carrera__coordinacion__id=7) & Q(status=True)), required=True, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    periodo = forms.ModelChoiceField(label=u"Periodo", queryset=Periodo.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))


class DetalleRecursoPresupuestarioPosgradoForm(FormModeloBase):
    desglosemoduloadictar = forms.IntegerField(initial=0, label=u'Desgloce módulo a dictar', required=True, widget=forms.TextInput(attrs={'class': 'imp-number ','type':'number','min':'0','col':'4', 'decimal': '0'}))
    horaspormodulo = forms.IntegerField(initial=0, label=u'Horas por módulo', required=True, widget=forms.TextInput(attrs={'class': 'imp-number ','type':'number','min':'0','col':'4', 'decimal': '0'}))
    valor_x_hora = forms.ModelChoiceField(label="Valor por hora", required=True, queryset=ValorPorHoraInformeContratacion.objects.filter(status=True), widget=forms.Select(attrs={'class': 'imp-50', 'col':'4'}))
    categoriadocente = forms.ModelChoiceField(label=u'Tipo de Docente', required=True, queryset=TipoProfesor.objects.filter(status=True), widget=forms.Select(attrs={'class': 'imp-50', 'col':'4'}))


class ItemRecursoPresupuestarioPosgradoForm(FormModeloBase):
    total_paralelos = forms.IntegerField(initial=0, label=u'Total Paralelos', required=True, widget=forms.TextInput(attrs={'class': 'imp-number ','type':'number','min':'0','col':'6', 'decimal': '0'}))
    modulos_a_dictar = forms.IntegerField(initial=0, label=u'Modulos a dictar', required=True, widget=forms.TextInput(attrs={'class': 'imp-number ','type':'number','min':'0','col':'6', 'decimal': '0'}))




class ContratacionConfiguracionRequisitoForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre ", required=True, widget=forms.TextInput(attrs={'col': '12'}))
    activo = forms.BooleanField(label=u"activo", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class ContratacionGestionRequisitoForm(FormModeloBase):
    from pdip.models import TIPO_REQUISITO
    requisito = forms.ModelChoiceField(label=u'Requisito',queryset=Requisito.objects.filter(status=True).order_by('nombre'),widget=forms.Select(attrs={'class': 'imp-50', 'col':'12'}))
    tipo = forms.ChoiceField(choices=TIPO_REQUISITO, label=u'Tipo', required=True, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    opcional = forms.BooleanField(label=u"opcional", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class RequisitoContratoForm(forms.Form):
    archivo = ExtFileField(label=u'Requisito', required=True, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',ext_whitelist=(".pdf",), max_upload_size=8194304,widget=forms.FileInput( attrs={'formwidth': '100%', 'accept': 'application/pdf'}))
    fecha_caducidad = forms.DateField(label=u'Fecha caducidad', required=False, widget=forms.DateTimeInput(attrs={'class': 'form-control flatpickr', 'type': 'date', 'col': '12'}))

    def del_field(self, field):
        del self.fields[field]

class RequisitoPagoDipForm(forms.Form):
    requisito = forms.ModelChoiceField(label=u'Requisito', queryset=RequisitoPagoDip.objects.filter(status=True).order_by('nombre'), widget=forms.Select(attrs={'class': 'imp-50', 'col': '12'}))
    orden = forms.CharField(label=u'Orden: ', required=True,widget=forms.TextInput(attrs={'class': 'form-control', 'type':'numbre','min':'0', 'col': '6'}))
    opcional = forms.BooleanField(label=u"opcional", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    def del_field(self, field):
        del self.fields[field]

class RequisitoPagoDipOrdenForm(forms.Form):
    orden = forms.CharField(label=u'Orden: ', required=True,widget=forms.TextInput(attrs={'class': 'form-control', 'type':'numbre','min':'0', 'col': '6'}))
    opcional = forms.BooleanField(label=u"opcional", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    def del_field(self, field):
        del self.fields[field]


class ConfiguracionGrupoPagoForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Nombre ", required=True, widget=forms.TextInput(attrs={'col': '12'}))
    tipogrupo = forms.ChoiceField(choices=TIPO_GRUPO, label=u'Tipo grupo', required=True, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    activo = forms.BooleanField(label=u"Activo?", required=False,   widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))

class RequisitoPagoSolicitudForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760,  widget=forms.FileInput(attrs={'class':'dropify ', 'col': '12', 'data-allowed-file-extensions': 'pdf'}))



class OrdenFirmaInformeActaPagoForm(forms.Form):
    responsabilidadfirma = forms.ModelChoiceField(label=u'Responsabilidad:', queryset=ResponsabilidadFirma.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))
    orden = forms.CharField(label=u'Orden: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6'}))



class ConfiguracionActaPagoSolicitadoPorForm(forms.Form):
    solicitadopor = forms.ModelChoiceField(label=u" Solicitado por: ", queryset =Persona.objects.none(),required=False, widget=forms.Select( attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))

    def initial(self,objeto):
        self.fields["solicitadopor"].initial = objeto

    def edit(self, pk=0):
        self.fields['solicitadopor'].queryset = Persona.objects.filter(id=pk)
        self.fields['solicitadopor'].initial = [pk]

class ConfiguracionActaPagoMarcoJuridicoReferencialForm(forms.Form):
    marcojuridicoreferencial = forms.CharField(label=u"Marco jurídico referencial", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["marcojuridicoreferencial"].initial = objeto

class ConfiguracionActaPagoConclusionesForm(forms.Form):
    conclusiones = forms.CharField(label=u"Conclusiones", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["conclusiones"].initial = objeto

class ConfiguracionActaPagoRecomendacionesForm(forms.Form):
    recomendaciones = forms.CharField(label=u"Recomendaciones", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["recomendaciones"].initial = objeto

class ConfiguracionActaPagoObjetivoForm(forms.Form):
    objetivo = forms.CharField(label=u'objetivo', required=True, widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "Titulo"}))

    def initial(self,objeto):
        self.fields["objetivo.initial"] = objeto

class ConfiguracionActaPagoTituloForm(forms.Form):
    titulo = forms.CharField(label=u"Titulo ", required=True, widget=forms.TextInput(attrs={'col': '12'}))

    def initial(self,objeto):
        self.fields["titulo.initial"] = objeto

class ConfiguracionActaPagoForm(forms.Form):
    titulo = forms.CharField(label=u"Titulo ", required=True, widget=forms.TextInput(attrs={'col': '12'}))



class ConfiguracionActaPagoParaForm(forms.Form):
    para = forms.ModelChoiceField(label=u" Para: ", queryset =Persona.objects.none(),required=False, widget=forms.Select( attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))

    def initial(self,objeto):
        self.fields["para"].initial = objeto

    def edit(self, pk=0):
        self.fields['para'].queryset = Persona.objects.filter(id=pk)
        self.fields['para'].initial = [pk]



class ActaPagoIntegrantesFirmaForm(forms.Form):
    responsabilidadfirma = forms.ModelChoiceField(label=u'Responsabilidad:', queryset=OrdenFirmaActaPago.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))
    persona = forms.ModelChoiceField(label=u'Persona:', queryset=Persona.objects.none(), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))

    def edit(self, pk):
        persona = Persona.objects.filter(pk=pk)
        self.fields['persona'].queryset = persona
        self.fields['persona'].initial = persona.first()


class PersonaActaPagoForm(forms.Form):
    persona = forms.ModelChoiceField(label=u" Persona: ", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))

    def edit(self, pk):
        persona = Persona.objects.filter(pk=pk)
        self.fields['persona'].queryset = persona
        self.fields['persona'].initial = persona.first()



class ActaPagoConclusionesForm(forms.Form):
    conclusion = forms.CharField(label=u"Conclusiones", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["conclusion"].initial = objeto

class ActaPagoDetalleMemoPosgradoForm(forms.Form):
    detallememoposgrado = forms.CharField(label=u"detallememoposgrado", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["conclusion"].initial = objeto

class ActaPagoRecomendacionesForm(forms.Form):
    descripcion = forms.CharField(label=u"Recomendaciones", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["descripcion"].initial = objeto

class ActaPagoMarcoJuridicoForm(forms.Form):
    descripcion = forms.CharField(label=u"Marco juridico", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["descripcion"].initial = objeto


class SubirArchivoForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=forms.FileInput(
            attrs={'class': 'dropify ', 'col': '12', 'data-allowed-file-extensions': 'pdf'}))
class DetalleActaPagoValoresForm(forms.Form):
    rmu = forms.FloatField(label=u"Valor", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%'}))
    valorIva = forms.DecimalField(label=u"Iva calculado", required=False, initial="0.00", widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%', }))
    valorTotal = forms.DecimalField(initial='0.00', label=u'Total Valor', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'formwidth': '50%'}))

class DetalleItemsActaPagoPosgradoForm(forms.Form):
    detallecontrato = forms.CharField(label=u'Detalle contrato', required=True,widget=forms.Textarea({'rows': '2', 'formwidth': '100%'}))
    documentohabilitante = forms.CharField(label=u'Documento habilitante', required=True,widget=forms.Textarea({'rows': '2', 'formwidth': '100%'}))
    observacion = forms.CharField(label=u'Observación', required=True,widget=forms.Textarea({'rows': '2', 'formwidth': '100%'}))


class FirmaElectronicaIndividualForm(forms.Form):
    firma = ExtFileField(label=u'Firma electrónica: ', help_text=u'Solo archivos con formato .p12', ext_whitelist=(".p12",), max_upload_size=6291456, widget=FileInput({'style': 'width:100%;', 'class': 'form-control', 'col': '12', 'accept': '.p12'}))
    password = forms.CharField(label=u'Contraseña', widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12', 'controlwidth': '100%', 'placeholder': 'Contraseña', 'type':'password'}))

class ContratoDipValidadorAnalistaForm(FormModeloBase):
    validadorgp = forms.ModelChoiceField(label=u" Analista validador: ", queryset =Persona.objects.none(),required=False, widget=forms.Select( attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    tipogrupo = forms.ChoiceField(choices=TIPO_GRUPO, label=u'Tipo grupo', required=False, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    tipopago = forms.ChoiceField(choices=TIPO_PAGO, label=u'Tipo pago', required=False, widget=forms.Select(attrs={'class': 'select2', 'col': '12'}))
    certificacion = forms.ModelChoiceField(CertificacionPresupuestariaDip.objects.filter(status=True), required=True, label=u'Certificación',widget=forms.Select(attrs={'col': '12'}))

    def del_fields(self, field):
        del self.fields[field]
    def edit(self, pk):
        persona = Persona.objects.filter(pk=pk)
        self.fields['validadorgp'].queryset = persona
        self.fields['validadorgp'].initial = persona.first()
