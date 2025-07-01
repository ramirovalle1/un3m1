# -*- coding: UTF-8 -*-
import json
import os
from datetime import datetime, timedelta
from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms import ValidationError
from django.contrib.auth.models import Group, User, Permission
from django.db.models import Q
from django.forms.models import model_to_dict
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from django.db import models, connection, connections
from django.contrib.auth.models import Group

from api.forms.my_form import MY_Form
from sga.models import Materia, Profesor


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


class SolicitudTutorMateriaForm(MY_Form):
    materia = forms.ModelChoiceField(required=True, queryset=Materia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la materia (requerido)'})
    profesor = forms.ModelChoiceField(required=True, queryset=Profesor.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el profesor (requerido)'})
    tipo = forms.ChoiceField(choices=((2, u"ACADÉMICA"), ), required=True,  widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo (requerido)'})
    descripcion = forms.CharField(label=u'Descripcion de la solicitud', widget=forms.Textarea(), required=True, error_messages={'required': 'Ingrese una descripción (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba un archivo'})

    def initQuerySet(self, data):
        materia = int(data.get('materia', '0'))
        profesor = int(data.get('profesor', '0'))
        if materia:
            self.fields['materia'].queryset = Materia.objects.filter(pk=materia)
        if profesor:
            self.fields['profesor'].queryset = Profesor.objects.filter(pk=profesor)

    def clean(self):
        cleaned_data = super(SolicitudTutorMateriaForm, self).clean()
        archivo = self.files.get('archivo', None)
        if archivo:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class SolicitudTutorMatriculaForm(MY_Form):
    tipo = forms.ChoiceField(choices=((2, u"ACADÉMICA"), ), required=True,  widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo (requerido)'})
    descripcion = forms.CharField(label=u'Descripcion de la solicitud', widget=forms.Textarea(), required=True, error_messages={'required': 'Ingrese una descripción (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba un archivo'})

    def initQuerySet(self, data):
        pass

    def clean(self):
        cleaned_data = super(SolicitudTutorMatriculaForm, self).clean()
        archivo = self.files.get('archivo', None)
        if archivo:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


