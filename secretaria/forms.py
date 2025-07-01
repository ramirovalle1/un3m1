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

from sagest.models import TipoOtroRubro
from secretaria.models import CategoriaServicio, PROCESO_SERVICIO, ROLES_TIPO_CATEGORIA, TIPO_FORMATO_CERTIFICADO
from core.custom_forms import FormModeloBase
from sga.models import Periodo, Carrera, AsignaturaMalla, Administrativo
from posgrado.models import ActividadCronogramaTitulacion
ESTADO_INFORME = (
    (1, "Aprobado"),
    (2, "Rechazado"),
)

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


def deshabilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True
    form.fields[campo].widget.attrs['disabled'] = True

class ServicioForm(forms.Form):
    orden = forms.IntegerField(label=u'Orden', initial=0, widget=forms.TextInput(attrs={'class': 'form-control imp-number', 'col': '12'}), required=True)
    alias = forms.CharField(label=u'Alias', initial='', widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}), required=True)
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}), required=True)
    categoria = forms.ModelChoiceField(queryset=CategoriaServicio.objects.filter(status=True).none(), required=True, label=u'Categoria', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    tiporubro = forms.ModelChoiceField(queryset=TipoOtroRubro.objects.all().none(), required=True, label=u'Tipo de rubro', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    proceso = forms.ChoiceField(label=u'Proceso', required=True, choices=PROCESO_SERVICIO, widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    costo = forms.FloatField(label=u'Costo', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '12'}))
    activo = forms.BooleanField(initial=True, label=u"Activo", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))

    def edit(self, idp, idt):
        self.fields['categoria'].queryset = CategoriaServicio.objects.filter(pk=idp)
        self.fields['tiporubro'].queryset = TipoOtroRubro.objects.filter(pk=idt)
        self.fields['categoria'].initial = [idp]
        self.fields['tiporubro'].initial = [idt]


class CategoriaServicioForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}), required=True)
    roles = forms.MultipleChoiceField(required=True, choices=ROLES_TIPO_CATEGORIA, label=u'Roles', widget=forms.SelectMultiple(attrs={"formwidth": "100%",'col': '12'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=500, help_text=u"", required=True, widget=forms.Textarea({'rows': '10', 'class': 'form-control', 'col': '12', 'placeholder': 'Describa brevemente el producto...'}))
    grupos = forms.ModelMultipleChoiceField(label=u"Grupos", queryset=Group.objects.all(), required=True, widget=forms.SelectMultiple(attrs={'formwidth': '100%', 'col': '12'}))
    icono = forms.CharField(label=u'Icono (SVG)', max_length=1000000000, help_text=u"", required=True, widget=forms.Textarea({'rows': '10', 'class': 'form-control normal-input', 'col': '12', 'placeholder': 'SVG'}))
    activo = forms.BooleanField(initial=True, label=u"Activo", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))

class EntregaCertificadoForm(FormModeloBase):
    postulante = forms.CharField(label=u"Postulante", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    maestria = forms.CharField(label=u"Maestría", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    periodo = forms.CharField(label=u"Periodo", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    observacion = forms.CharField(label=u'Observación', max_length=500, help_text=u"", required=False, widget=forms.Textarea({'rows': '3', 'class': 'form-control', 'col': '12', 'placeholder': 'Describa brevemente el producto...'}))

class AprobarRechazarInformePertinenciaForm(FormModeloBase):
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))
    estado = forms.ChoiceField(label=u'Estado', required=True, choices=ESTADO_INFORME, widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))

class SubirCertificadoPersonalizadoForm(FormModeloBase):
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))
    archivo = ExtFileField(label=u'Subir Archivo', required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato pdf',
                               ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput())

class SubirInformeTecnicoPertinenciaForm(FormModeloBase):
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))
    archivo = ExtFileField(label=u'Subir Archivo', required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato word o pdf',
                               ext_whitelist=(".pdf", ".doc", ".docx"), max_upload_size=10485760, widget=forms.FileInput())
    carrera = forms.ModelChoiceField(queryset=Carrera.objects.filter(status=True).order_by('-id'), required=True, label=u'Carrera comparativa', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))

    def sin_archivo(self):
        del self.fields['archivo']

    def solo_carrera(self):
        del self.fields['observacion']
        del self.fields['archivo']

    def sin_carrera(self):
        del self.fields['carrera']

class SubirCronogramaTitulacionForm(FormModeloBase):
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))
    archivo = ExtFileField(label=u'Subir Archivo', required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato pdf',
                               ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput())
    # notificar = forms.BooleanField(initial=True, required=False, label=u'Notificar al maestrante?', widget=CheckboxInput(attrs={'formwidth': '25%'}))

class NotificarCronogramaTitulacionForm(FormModeloBase):
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))
    url = forms.CharField(label=u'Url de drive', max_length=5000, required=False)

class SubirFormatoCertificadoForm(FormModeloBase):
    certificacion = forms.CharField(required=True, label=u'Certificación', widget=forms.TextInput(attrs={'class': 'imp-100'}))
    tipo = forms.ChoiceField(label=u'Tipo de formato', required=True, choices=TIPO_FORMATO_CERTIFICADO, widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    # roles = forms.MultipleChoiceField(required=True, choices=ROLES_TIPO_CATEGORIA, label=u'Áreas', widget=forms.SelectMultiple(attrs={"formwidth": "100%",'col': '12'}))
    archivo = ExtFileField(label=u'Subir Archivo', required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato word',
                               ext_whitelist=(".doc", ".docx"), max_upload_size=10485760, widget=forms.FileInput())

class AdicionarActividadCronogramaForm(FormModeloBase):
    nombre = forms.CharField(required=True, label=u'Actividad', widget=forms.TextInput(attrs={'class': 'imp-100'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea({'rows': '2'}))

class ActividadCronogramaTitulacionForm(FormModeloBase):
    solicitante = forms.CharField(required=True, label=u'Solicitante', widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    periodo = forms.ModelChoiceField(queryset=Periodo.objects.filter(status=True, tipo__id=3, nombre__icontains='TITU').order_by('-id'), required=True, label=u'Periodo de titulación', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    actividad = forms.ModelChoiceField(queryset=ActividadCronogramaTitulacion.objects.filter(status=True).order_by('-id'), required=True, label=u'Actividad', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    inicio = forms.DateField(label=u"Inicio de Actividad", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    fin = forms.DateField(label=u"Fin de Actividad", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    observacion = forms.CharField(label=u'Responsable', max_length=500, help_text=u"", required=True, widget=forms.Textarea({'rows': '3', 'class': 'form-control', 'col': '12', 'placeholder': 'Añada una observación a la actividad...'}))

class IntegrantesTitulacionForm(FormModeloBase):
    solicitante = forms.CharField(required=True, label=u'Solicitante', widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    director = forms.ModelChoiceField(queryset=Administrativo.objects.all().none(), required=True, label=u'Director de escuela', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    cargodir = forms.CharField(label=u"Cargo del director", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    coordinador = forms.ModelChoiceField(queryset=Administrativo.objects.all().none(), required=True, label=u'Coordinador o Administrativo', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    cargocor = forms.CharField(label=u"Cargo del coordinador o administrativo", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))

    def edit_director(self, director_id):
        director = Administrativo.objects.filter(pk=director_id)
        self.fields['director'].queryset = director
        self.fields['director'].initial = [director_id]

    def edit_coordinador(self, coordinador_id):
        coordinador = Administrativo.objects.filter(pk=coordinador_id)
        self.fields['coordinador'].queryset = coordinador
        self.fields['coordinador'].initial = [coordinador_id]

class CarreraHomologableForm(FormModeloBase):
    carrera = forms.ModelChoiceField(label=u"Carrera a homologar", queryset=Carrera.objects.none(), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    asignatura = forms.ModelChoiceField(label=u"Asignatura (Ah)", queryset=AsignaturaMalla.objects.none(), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    creditos = forms.FloatField(initial=0, label=u'Créditos (Ah)', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right', 'style': 'width: 75px;', 'placeholder': '0.00'}))
    horas = forms.FloatField(initial=0, label=u'Horas (Ah)', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right', 'style': 'width: 75px;'}))

    carreraco = forms.ModelChoiceField(label=u"Carrera comparativa", queryset=Carrera.objects.none(), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12', 'separator2':True,'separatortitle':'Detalle de asignaturas homologables'}))
    asignaturaco = forms.ModelChoiceField(label=u"Asignatura compatible", queryset=AsignaturaMalla.objects.none(), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    creditosco = forms.FloatField(initial=0, label=u'Créditos (Ac)', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right', 'crearboton': True, 'classbuton': 'agregarbtn', 'style': 'width: 75px;', 'placeholder': '0.00'}))
    horasho = forms.FloatField(initial=0, label=u'Horas (Ac)', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right', 'style': 'width: 75px;'}))

    def editar(self):
        deshabilitar_campo(self, 'carrera')
        deshabilitar_campo(self, 'asignatura')
        deshabilitar_campo(self, 'creditos')
        deshabilitar_campo(self, 'horas')


