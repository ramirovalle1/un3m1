# -*- coding: UTF-8 -*-
import json
import os
from datetime import datetime, timedelta
from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms.models import ModelForm, ModelChoiceField, model_to_dict
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from django.db import models, connection, connections

from bd.models import PeriodoGrupo
from matricula.models import TIPO_MATRICULA_CHOICES, PeriodoMatricula, MotivoMatriculaEspecial, \
    MOTIVO_MATRICULA_CHOICES, TIPO_ENTIDAD_MATRICULA_ESPECIAL_CHOICES, TIPO_VALIDACION_MATRICULA_ESPECIAL_CHOICES, \
    EstadoMatriculaEspecial, ACCION_MATRICULA_ESPECIAL_CHOICES, ProcesoMatriculaEspecial, \
    ACCION_ESTADO_MATRICULA_ESPECIAL_CHOICES
from sga.models import ProfesorMateria, MateriaAsignada, DetalleSilaboSemanalTema, Profesor, Materia, Modulo, Sexo, \
    Pais, Provincia, Canton, Parroquia, TIPO_PERSONA, Externo, Persona, Coordinacion, Carrera, TipoPeriodo, \
    Discapacidad, InstitucionBeca
from sagest.models import OpcionSistema, Departamento, TipoOtroRubro
from sga.forms import ExtFileField
from django.forms import ValidationError
from inno.models import HorarioTutoriaAcademica, TOPICO_SOLICITUD_TUTORIA


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


class FixedForm(ModelForm):
    date_fields = []

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        for f in self.date_fields:
            self.fields[f].widget.format = '%d-%m-%Y'
            self.fields[f].input_formats = ['%d-%m-%Y']


def deshabilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True
    form.fields[campo].widget.attrs['disabled'] = True


def habilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = False
    form.fields[campo].widget.attrs['disabled'] = False


def campo_modolectura(form, campo, valor):
    form.fields[campo].widget.attrs['readonly'] = valor


def campo_modobloqueo(form, campo, valor):
    form.fields[campo].widget.attrs['disabled'] = valor


class MatriculaEspecialActionForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))


class MatriculaAdmisionDiscapacidadForm(forms.Form):
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad", queryset=Discapacidad.objects.filter(status=True), required=True, widget=forms.Select())
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet Discapacitado', max_length=50, required=True, widget=forms.TextInput())
    archivo = ExtFileField(label=u'Carnet de Discapacidad', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf", ), max_upload_size=4194304)
    institucionvalida = forms.ModelChoiceField(label=u"Institución Valida", queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True), required=True, widget=forms.Select())

    def clean(self):
        cleaned_data = super(MatriculaAdmisionDiscapacidadForm, self).clean()
        tipodiscapacidad = cleaned_data['tipodiscapacidad'] if 'tipodiscapacidad' in cleaned_data and cleaned_data['tipodiscapacidad'] else None
        porcientodiscapacidad = cleaned_data['porcientodiscapacidad'] if 'porcientodiscapacidad' in cleaned_data and cleaned_data['porcientodiscapacidad'] else None
        carnetdiscapacidad = cleaned_data['carnetdiscapacidad'] if 'carnetdiscapacidad' in cleaned_data and cleaned_data['carnetdiscapacidad'] else None
        institucionvalida = cleaned_data['institucionvalida'] if 'institucionvalida' in cleaned_data and cleaned_data['institucionvalida'] else None

        if not tipodiscapacidad:
            self.add_error('tipodiscapacidad', ValidationError(u'Favor seleccione un tipo de discapacidad'))
        if not porcientodiscapacidad or porcientodiscapacidad <= 0:
            self.add_error('porcientodiscapacidad', ValidationError(u'Favor ingrese el porcentaje de discapacidad mayor a cero'))
        if not carnetdiscapacidad:
            self.add_error('carnetdiscapacidad', ValidationError(u'Favor ingrese el número de carné de discapacidad'))
        if not institucionvalida:
            self.add_error('institucionvalida', ValidationError(u'Favor seleccione una institución'))
        return cleaned_data


class MatriculaAdmisionPersonaPPLForm(forms.Form):
    fechaingresoppl = forms.DateField(label=u'Fecha de Ingreso', initial=datetime.now().date(), required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    centrorehabilitacion = forms.CharField(label=u'Centro de Rehabilitación Social', max_length=500, initial='', required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    lidereducativo = forms.CharField(label=u'Lider educativo', max_length=500, initial='', required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    correolidereducativo = forms.CharField(label=u'Correo electrónico del lider educativo', max_length=250, initial='', required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    telefonolidereducativo = forms.CharField(label=u'Teléfono del lider educativo', max_length=100, initial='', required=True, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    observacionppl = forms.CharField(label=u"Observación Persona Privada Libertad", max_length=500, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    archivoppl = ExtFileField(label=u'Archivo PPL', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304)

    def clean(self):
        cleaned_data = super(MatriculaAdmisionPersonaPPLForm, self).clean()
        fechaingresoppl = cleaned_data['fechaingresoppl'] if 'fechaingresoppl' in cleaned_data and cleaned_data['fechaingresoppl'] else None
        centrorehabilitacion = cleaned_data['centrorehabilitacion'] if 'centrorehabilitacion' in cleaned_data and cleaned_data['centrorehabilitacion'] else None
        lidereducativo = cleaned_data['lidereducativo'] if 'lidereducativo' in cleaned_data and cleaned_data['lidereducativo'] else None
        correolidereducativo = cleaned_data['correolidereducativo'] if 'correolidereducativo' in cleaned_data and cleaned_data['correolidereducativo'] else None
        telefonolidereducativo = cleaned_data['telefonolidereducativo'] if 'telefonolidereducativo' in cleaned_data and cleaned_data['telefonolidereducativo'] else None

        if not fechaingresoppl:
            self.add_error('fechaingresoppl', ValidationError(u'Favor ingrese la fecha de ingreso al centro de rehabilitación'))
        if not centrorehabilitacion:
            self.add_error('centrorehabilitacion', ValidationError(u'Favor ingrese el centro de rehabilitación'))
        if not lidereducativo:
            self.add_error('lidereducativo', ValidationError(u'Favor ingrese el lider educativo'))
        if not correolidereducativo:
            self.add_error('correolidereducativo', ValidationError(u'Favor ingrese el correo del lider educativo'))
        if not correolidereducativo:
            self.add_error('correolidereducativo', ValidationError(u'Favor ingrese el correo del lider educativo'))
        if not telefonolidereducativo:
            self.add_error('telefonolidereducativo', ValidationError(u'Favor ingrese el teléfono del lider educativo'))

        return cleaned_data
