# -*- coding: UTF-8 -*-
from django import forms

from core.custom_forms import FormModeloBase
from django.forms.widgets import DateTimeInput
from sga.forms import ExtFileField
from laboratorio.models import Perfil, ProcesoOpcionSistema
from sga.models import Profesor, Modulo

class PerfilForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput(attrs={'col': '12'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'placeholder': 'Describa el perfil a ingresar', 'col': '12', 'rows': '2'}), required=False)

class DetallePerfilForm(FormModeloBase):
    perfil = forms.ModelChoiceField(label=u"Perfil", queryset=Perfil.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '12'}))
    porcentajeacierto = forms.FloatField(initial=0, label=u'Porcentaje acierto', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'form-control', 'decimal': '2'}))
    niveldificultad = forms.IntegerField(label="Nivel dificultad", required=True, widget=forms.NumberInput(attrs={'class': 'imp-100', 'col': '6'}))
    segundosinteraccion = forms.IntegerField(label="Segundos interacción", required=True, widget=forms.NumberInput(attrs={'class': 'imp-100', 'col': '6'}))
    zurdo = forms.BooleanField(label=u'¿Zurdo? ', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '3', 'class': 'js-switch', 'help_text_switchery': True}))
    contraste = forms.BooleanField(label=u'¿Contraste? ', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '3', 'class': 'js-switch', 'help_text_switchery': True}))

class UsuarioPerfilForm(FormModeloBase):
    usuario = forms.IntegerField(initial=0, required=True, label=u'Usuario', widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%', 'col': '12'}))
    perfil = forms.ModelChoiceField(label=u"Perfil", queryset=Perfil.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '12'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    fechafin = forms.DateField(label=u"Fecha fin", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    tourguiado = forms.BooleanField(label=u'¿Tour Guiado? ', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'class': 'js-switch', 'help_text_switchery': True}))
    activo = forms.BooleanField(label=u'¿Activo? ', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'class': 'js-switch', 'help_text_switchery': True}))

class TestForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput(attrs={'col': '12'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'placeholder': 'Describa el perfil a ingresar', 'col': '12', 'rows': '2'}), required=False)
    fecha = forms.DateField(label=u"Fecha", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)

class DetalleTestForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'placeholder': 'Describa la pregunta', 'col': '12', 'rows': '2'}), required=False)
    respuesta = forms.IntegerField(label="Respuesta", required=True, widget=forms.NumberInput(attrs={'class': 'imp-100', 'col': '6'}))
    valor = forms.FloatField(initial=0, label=u'Valor', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'form-control', 'decimal': '2'}))
    rgb = forms.FloatField(initial=0, label=u'RGB', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'form-control', 'decimal': '3'}))
    rotacion = forms.CharField(label=u'Rotación', max_length=200, required=True, widget=forms.TextInput(attrs={'col': '12'}))
    orden = forms.IntegerField(label="Orden", required=True, widget=forms.NumberInput(attrs={'class': 'imp-100', 'col': '6'}))

class ProcesoOpcionSistemaForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'placeholder': 'Describa la opción del sistema', 'col': '12', 'rows': '2'}), required=False)

class LaboratorioOpcionSistemaForm(FormModeloBase):
    modulo = forms.ModelChoiceField(queryset=Modulo.objects.filter(status=True), required=True, label=u'Módulo', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '6'}))
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6'}), required=True)
    proceso = forms.ModelChoiceField(queryset=ProcesoOpcionSistema.objects.filter(status=True), required=False, label=u'Proceso', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '6'}))
    url = forms.CharField(label=u'URL', initial='', widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6', 'placeholder': '/sistemas?action=EjemploAction'}), required=True)
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '2', 'col': '6', 'placeholder': 'Describa brevemente la funcionalidad de la opción...'}), required=True)
    pregunta = forms.CharField(label=u"Pregunta", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '2', 'col': '6', 'placeholder': 'Escriba la pregunta ...'}), required=False)
    imagen = ExtFileField(label=u'Imagen', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png',
                           ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(
                           attrs={'accept':' image/jpeg, image/jpg, image/png', 'col': '12', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    activo = forms.BooleanField(label=u'¿Activo?', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))