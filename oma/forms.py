from core.custom_forms import FormModeloBase
# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta
from typing import Union

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms import ValidationError
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from django.db import models, connection, connections
from sga.models import Inscripcion, Asignatura, Periodo
from oma.models import ModeloEvaluativo


class CheckboxSelectMultipleCustom(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(CheckboxSelectMultipleCustom, self).render(*args, **kwargs)
        return mark_safe(output.replace(u'<ul>', u'<div class="custom-multiselect" style="width: 600px;overflow: scroll"><ul>').replace(u'</ul>', u'</ul></div>').replace(u'<li>', u'').replace(u'</li>', u'').replace(u'<label', u'<div style="width: 900px"><li').replace(u'</label>', u'</li></div>'))


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

class CursoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', required=True, widget=forms.TextInput(attrs={'col': '8'}))
    codigo = forms.CharField(label=u'Código', required=True, widget=forms.TextInput(attrs={'col': '4'}))
    modeloevaluativo = forms.ModelChoiceField(label=u"Mod. Evaluativo", queryset=ModeloEvaluativo.objects.filter(status=True), widget=forms.Select(attrs={'col': '12'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=True, widget=DateTimeInput({'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=True, widget=DateTimeInput({'col': '6'}))
    horas = forms.IntegerField(label=u"Cantidad Horas", required=True, initial=2,widget=forms.TextInput(attrs={'col': '6'}))
    creditos = forms.IntegerField(label=u"Creditos", required=True, initial=2,widget=forms.TextInput(attrs={'col': '6'}))
    enlacereuniondocente = forms.CharField(label=u'Enlace Zoom Docente', required=True, widget=forms.TextInput(attrs={'col': '12'}))
    enlacegrabacion = forms.CharField(label=u'Enlace grabación', required=True, widget=forms.TextInput(attrs={'col': '12'}))
    enlacepresentacioncurso = forms.CharField(label=u'Enlace presentación curso', required=True, widget=forms.TextInput(attrs={'col': '12'}))
    idcursomoodle = forms.CharField(label=u'Id curso moodle', required=False, widget=forms.TextInput(attrs={'col': '4'}))

class InscripcionCursoForm(FormModeloBase):
    inscripcion = forms.ModelChoiceField(label=u"Estudiante", queryset=Inscripcion.objects.select_related().filter(status=True, activo=True), widget=forms.Select(attrs={'col': '12'}))
    correo = forms.EmailField(label=u"Correo", max_length=1000, required=False,
                              widget=forms.TextInput(attrs={'col': '12', 'class': 'email-input'}))

#Se filtro las asignaturas con que tengan la palabra modulo en el nombre y tengo en estado TRUE el campo 'Modulo'
#Para la obtencion de las dos unicas asignaturas de modulos de ofimatica (de momento)
class AsignaturaCursoForm(FormModeloBase):
    asignatura = forms.ModelChoiceField(label=u"Asignatura", queryset=Asignatura.objects.select_related().filter(status=True, modulo=True, nombre__icontains='Modulo'), widget=forms.Select(attrs={'col': '12'}))

class MigrarInscripcionCursoForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 6Mb, en formato excel', ext_whitelist=(".excel",),
                           max_upload_size=6291456)

class ModeloEvaluativoForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre", max_length=100)
    principal = forms.BooleanField(label=u"Principal", required=False, initial=False)
    activo = forms.BooleanField(label=u"Activo", required=False, initial=True)
    notamaxima = forms.FloatField(label=u"Nota Maxima", initial="0.00", required=False,
                                  widget=forms.TextInput(attrs={'col': '6','class': 'imp-numbermed-right', 'decimal': '2'}))
    notaaprobar = forms.FloatField(label=u"Nota para Aprobar", initial="0.00", required=False,
                                   widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right', 'decimal': '2'}))
    notarecuperacion = forms.FloatField(label=u"Nota para Recup.", initial="0.00", required=False,
                                        widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right', 'decimal': '2'}))
    asistenciaaprobar = forms.IntegerField(label=u"% Asist. para Aprobar.", initial=0, required=False,
                                           widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbersmall', 'decimal': '0'}))
    asistenciarecuperacion = forms.IntegerField(label=u"% Asist. para Recup.", initial=0, required=False,
                                                widget=forms.TextInput(
                                                    attrs={'col': '6', 'class': 'imp-numbersmall', 'decimal': '0'}))
    notafinaldecimales = forms.IntegerField(label=u"Decimales N.Final", initial=0, required=False,
                                            widget=forms.TextInput(attrs={'col': '6','class': 'imp-numbersmall', 'decimal': '0'}))
    observaciones = forms.CharField(label=u'Observaciones', widget=forms.Textarea, required=False)

class DetalleModeloEvaluativoForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre", max_length=10, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-25'}))
    orden = forms.IntegerField(label=u"Orden en Acta", required=False, initial=0,
                               widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbersmall', 'decimal': '0'}))
    decimales = forms.IntegerField(label=u"Decimales", initial=0, required=False,
                                   widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbersmall', 'decimal': '0'}))
    notaminima = forms.FloatField(label=u"Nota Minima", initial="0.00", required=False,
                                  widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right', 'decimal': '2'}))
    notamaxima = forms.FloatField(label=u"Nota Maxima", initial="0.00", required=False,
                                  widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right', 'decimal': '2'}))
    migrarmoodle = forms.BooleanField(label=u"Migrar Moodle?", required=False, initial=False,widget=forms.CheckboxInput(attrs={'col': '6'}))
    dependiente = forms.BooleanField(label=u"Campo Dependiente?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'col':'6'}))
    determinaestadofinal = forms.BooleanField(label=u"Determina Estado final?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'col':'6'}))
    dependeasistencia = forms.BooleanField(label=u"Depende de asisencia?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'col':'6'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')

class LogicaModeloEvaluativoForm(FormModeloBase):
    logica = forms.CharField(label=u'Lógica', widget=forms.Textarea(attrs={'rows': '15'}), required=False)

class MasivoInscripcionForm(FormModeloBase):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 6Mb, en formato excel', ext_whitelist=(".xlsx",".xls"),
                           max_upload_size=6291456, widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'xlsx xls'}))