# -*- coding: UTF-8 -*-
from django import forms

from core.custom_forms import FormModeloBase
from juventud.models import ESTADO_APROBACION

class RegistroProgramaForm(forms.Form):
    cedula = forms.CharField(label=u"Cédula", max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefono = forms.CharField(label=u"Teléfono", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))

class PostulacionPersonaForm(FormModeloBase):
    estado = forms.ChoiceField(label=u"Estado", choices=ESTADO_APROBACION, required=False, widget=forms.Select(attrs={'formwidth': '60%'}))
    observacion = forms.CharField(label=u'Observación:', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    envioemail = forms.BooleanField(label=u"Eviar email", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '40%'}))