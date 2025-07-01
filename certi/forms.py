# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta
from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from certi.models import CLASIFICACION_CERTIFICADO, TIPO_CERTIFICACION_CERTIFICADO, TIPO_VALIDACION_CERTIFICADO, \
    TIPO_VIGENCIA_CERTIFICADO, TIPO_ORIGEN_CERTIFICADO, DESTINO_CERTIFICADO, FuncionAdjuntarArchivoCertificado
from secretaria.models import Servicio
from sga.forms import deshabilitar_campo
from sga.models import Reporte, Coordinacion, Persona, Carrera
from sagest.models import Departamento


class CheckboxSelectMultipleCustom(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(CheckboxSelectMultipleCustom, self).render(*args, **kwargs)
        return mark_safe(output.replace(u'<ul>',
                                        u'<div class="custom-multiselect" style="width: 600px;overflow: scroll"><ul>').replace(
            u'</ul>', u'</ul></div>').replace(u'<li>', u'').replace(u'</li>', u'').replace(u'<label',
                                                                                           u'<div style="width: 900px"><li').replace(
            u'</label>', u'</li></div>'))


class ExtFileField(forms.FileField):
    """
    * max_upload_size - a number indicating the maximum file size allowed for upload.
            500Kb - 524288
            1MB - 1048576
            2.5MB - 2621440
            5MB - 5242880
            10MB - 10485760
            20MB - 20971520
            50MB - 5242880
            100MB 104857600
            250MB - 214958080
            500MB - 429916160
    t = ExtFileField(ext_whitelist=(".pdf", ".txt"), max_upload_size=)
    """

    def __init__(self, *args, **kwargs):
        ext_whitelist = kwargs.pop("ext_whitelist")
        self.ext_whitelist = [i.lower() for i in ext_whitelist]
        self.max_upload_size = kwargs.pop("max_upload_size")
        super(ExtFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        upload = super(ExtFileField, self).clean(*args, **kwargs)
        if upload:
            size = upload.size
            filename = upload.name
            ext = os.path.splitext(filename)[1]
            ext = ext.lower()
            if size == 0 or ext not in self.ext_whitelist or size > self.max_upload_size:
                raise forms.ValidationError("Tipo de fichero o tamanno no permitido!")


class CertificadoForm(forms.Form):
    codigo = forms.CharField(label=u'Código', max_length=10, required=True, widget=forms.TextInput(attrs={'class': 'imp-60', 'formwidth': '20%'}))
    version = forms.FloatField(label=u'Versión', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '1', 'formwidth': '20%'}))
    tipo_origen = forms.ChoiceField(label=u'Origen', choices=TIPO_ORIGEN_CERTIFICADO, widget=forms.Select(attrs={'formwidth': '30%'}))
    clasificacion = forms.ChoiceField(label=u'Clasificacion', choices=CLASIFICACION_CERTIFICADO, widget=forms.Select(attrs={'formwidth': '30%'}))
    tipo_certificacion = forms.ChoiceField(label=u'Tipo Certificación', choices=TIPO_CERTIFICACION_CERTIFICADO, widget=forms.Select(attrs={'formwidth': '25%'}))
    tipo_validacion = forms.ChoiceField(label=u'Tipo Validación', choices=TIPO_VALIDACION_CERTIFICADO, widget=forms.Select(attrs={'formwidth': '25%'}))
    primera_emision = forms.DateField(label=u"Primera emisión", required=True, input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '25%'}))
    ultima_modificacion = forms.DateField(label=u"Ultima modificación", required=True, input_formats=['%d-%m-%Y'], initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '25%'}))
    certificacion = forms.CharField(label=u'Certificación', widget=forms.Textarea(attrs={'rows': '3', 'formwidth': '100%'}), required=True)
    reporte = forms.ModelChoiceField(queryset=Reporte.objects.filter(certificado=True, status=True), required=True, label=u'Reporte', widget=forms.Select(attrs={'formwidth': '100%'}))
    vigencia = forms.IntegerField(label=u'Vigencia', initial=0, widget=forms.NumberInput({"min": "0", "max": "12", 'formwidth': '25%'}))
    tipo_vigencia = forms.ChoiceField(label=u'Tipo de vigencia', choices=TIPO_VIGENCIA_CERTIFICADO, widget=forms.Select(attrs={'formwidth': '25%'}))
    visible = forms.BooleanField(label=u'Visible?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '25%'}))
    destino = forms.ChoiceField(label=u'Destino', choices=DESTINO_CERTIFICADO, widget=forms.Select(attrs={'formwidth': '25%'}))
    coordinacion = forms.ModelMultipleChoiceField(label=u'Coordinaciones', queryset=Coordinacion.objects.filter(status=True), required=False, widget=forms.SelectMultiple(attrs={'separator2': True, 'separatortitle': 'Coordinaciones disponibles', 'fieldbuttons': [{'id': 'select_all', 'tooltiptext': 'Seleccionar todas', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa fa-check-square-o'}, {'id': 'unselect_all', 'tooltiptext': 'Deseleccionar todas', 'btnclasscolor': 'btn-warning', 'btnfaicon': 'fa fa-minus'}, ]}))
    adjuntararchivo = forms.BooleanField(label=u'Adjuntar Archivo?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '25%'}))
    funcionadjuntar = forms.ModelChoiceField(queryset=FuncionAdjuntarArchivoCertificado.objects.filter(status=True), required=False, label=u'Función Adjuntar Archivo', widget=forms.Select(attrs={'formwidth': '75%'}))
    servicio = forms.ModelChoiceField(queryset=Servicio.objects.filter(proceso__in=[1, 2, 8, 10]), required=False, label=u'Servicio', widget=forms.Select(attrs={'separator2': True, 'separatortitle': 'Servicio de secretaría', 'formwidth': '60%'}))
    costo = forms.FloatField(label=u'Costo', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '20%'}))
    tiempo_cobro = forms.IntegerField(label=u'Tiempo de cobro en horas', initial=72, required=True, widget=forms.NumberInput(attrs={"min": "0",'class': 'form-control', 'formwidth': '20%'}))
    imagen_tarjeta = ExtFileField(label=u'Subir imagen de tarjeta', required=False, help_text=u'Tamaño Maximo permitido 20Mb, en formato png, jpg, jpeg', ext_whitelist=(".jpeg", ".png", ".jpg"), max_upload_size=20480000, widget=forms.FileInput(attrs={'formwidth': '100%', 'class': 'dropify'}))

    def editar(self, certificado):
        # self.fields['reporte'].widget.attrs['descripcion'] = f"{certificado.reporte.id} - {certificado.reporte.descripcion}"
        # self.fields['reporte'].initial = certificado.reporte.id
        if certificado.imagen_tarjeta:
            self.fields['imagen_tarjeta'].widget.initial_text = "Anterior"
            self.fields['imagen_tarjeta'].widget.input_text = "Cambiar"

    def set_coordinacion(self, coodinacion):
        self.fields['coordinacion'].queryset = coodinacion


class CertificadoUnidadCertificadoraForm(forms.Form):
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), required=False, label=u'Departamento', widget=forms.Select(attrs={'formwidth': '100%'}))
    coordinacion = forms.ModelChoiceField(queryset=Coordinacion.objects.filter(status=True, carrera__isnull=False).distinct(), required=False, label=u'Coordinación', widget=forms.Select(attrs={'formwidth': '100%'}))
    alias = forms.CharField(max_length=20, label=u"Nombre corto/alias", required=True, widget=forms.TextInput(attrs={'class': 'imp-20'}))
    responsable = forms.ModelChoiceField(label=u'Responsable', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    responsable_titulo = forms.CharField(max_length=250, label=u"Nombre del responsable con titulo", required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    responsable_denominacion = forms.CharField(max_length=350, label=u"Denominación del puesto del responsable", required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    compartir_responsabilidad = forms.BooleanField(label=u'Compartir responsabilidad con Facultad', initial=False, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))

    def tipo_validacion(self, certificado):
        if certificado.tipo_validacion == 1:
            self.fields['departamento'].required = True
            del self.fields['coordinacion']
            if certificado.tipo_origen == 1:
                del self.fields['compartir_responsabilidad']
        elif certificado.tipo_validacion == 2:
            self.fields['coordinacion'].required = True
            self.fields['departamento'].required = True
            del self.fields['compartir_responsabilidad']


class CertificadoAsistenteCertificadoraForm(forms.Form):
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), required=False, label=u'Departamento/Facultad', widget=forms.Select(attrs={'formwidth': '100%'}))
    asistente = forms.ModelChoiceField(label=u'Asistente', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    asistente_titulo = forms.CharField(max_length=250, label=u"Nombre de la asistente con titulo", required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    asistente_denominacion = forms.CharField(max_length=350, label=u"Denominación del puesto de la asistente", required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    coordinacion_compartida = forms.ModelChoiceField(queryset=Coordinacion.objects.filter(status=True),
                                                label=u'Coordinación responsabilidad compartida', required=False,
                                                     widget=forms.Select(attrs={'class': 'imp-100'}))
    carrera = forms.ModelMultipleChoiceField(label=u'Carreras', queryset=Carrera.objects.filter(status=True), required=False, widget=forms.SelectMultiple(attrs={'separator2': True, 'separatortitle': 'Carreras responsables', 'fieldbuttons': [{'id': 'select_all', 'tooltiptext': 'Seleccionar todas', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa fa-check-square-o'}, {'id': 'unselect_all', 'tooltiptext': 'Deseleccionar todas', 'btnclasscolor': 'btn-warning', 'btnfaicon': 'fa fa-minus'}, ]}))

    def set_departamento(self, unidad):
        deshabilitar_campo(self, 'departamento')
        self.fields['departamento'].initial = unidad.departamento
        if not unidad.compartir_responsabilidad:
            del self.fields['coordinacion_compartida']
            if unidad.certificado.tipo_validacion == 1:
                del self.fields['carrera']
            elif unidad.certificado.tipo_validacion == 2:
                self.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion=unidad.coordinacion)


# class CargarFotoCarnetForm(forms.Form):
#     foto = ExtFileField(label=u'Seleccione Imagen', required=True, help_text=u'Tamaño Maximo permitido 500Kb, en formato jpg', ext_whitelist=(".jpg"), max_upload_size=524288, widget=FileInput({'accept': 'image/jpg'}))


class ResponsableCertificadoUnidadCertificadoraForm(forms.Form):
    responsable = forms.ModelChoiceField(label=u'Responsable', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    responsable_titulo = forms.CharField(max_length=250, label=u"Nombre del responsable con titulo", required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    responsable_denominacion = forms.CharField(max_length=350, label=u"Denominación del puesto del responsable", required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))


class AsistenteCertificadoAsistenteCertificadoraForm(forms.Form):
    asistente = forms.ModelChoiceField(label=u'Asistente', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    asistente_titulo = forms.CharField(max_length=250, label=u"Nombre de la asistente con titulo", required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    asistente_denominacion = forms.CharField(max_length=350, label=u"Denominación del puesto de la asistente", required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))