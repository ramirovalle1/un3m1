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
from .models import *
from django.db import models, connection, connections
from sga.forms import ExtFileField, deshabilitar_campo
from sga.models import Persona


class BancoPreguntasForm(forms.Form):
    enunciado = forms.CharField(label=u'Enunciado', widget=forms.Textarea(attrs={'rows': '2', 'class': 'normal-input'}), required=False)
    ayuda = forms.CharField(label=u'Retroalimentación General', widget=forms.Textarea(attrs={'rows': '2', 'class': 'normal-input'}), required=False)
    tiporespuesta = forms.ChoiceField(label=u'Tipo de Respuesta', choices=TIPO_PREGUNTA, required=True, widget=forms.Select(attrs={'formwidth': '100%'}))


class EvaluacionForm(forms.Form):
    from ckeditor_uploader.widgets import CKEditorUploadingWidget
    nombre = forms.CharField(label=u'Nombre', max_length=1500, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    detalle = forms.CharField(label=u"Detalle", required=True, widget=CKEditorUploadingWidget())
    password = forms.CharField(label=u'Contraseña', max_length=250, required=True, widget=forms.TextInput(attrs={'class': 'normal-input'}))
    verresultados = forms.ChoiceField(label=u'Mostrar Resultados', choices=CONFIGURACION_RESULTADOS, required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    notamin = forms.FloatField(label=u"Nota Minima", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%'}))
    notamax = forms.FloatField(label=u"Nota Máxima", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '50%'}))
    numpreguntas = forms.IntegerField(label=u"Número de Preguntas", required=True, initial=0, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '35%'}))
    numintentos = forms.IntegerField(label=u"Número de Intentos", required=True, initial=0, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '35%'}))
    minevaluacion = forms.IntegerField(label=u"Minutos a Evaluar", required=True, initial=0, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    publicar = forms.BooleanField(label=u'¿Publicado?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%', 'class': 'js-switch'}))


class EvaluacionPreguntaForm(forms.Form):
    pregunta = forms.ModelChoiceField(BancoPreguntas.objects.filter(status=True).order_by('-id'), required=True, label=u'Pregunta', widget=forms.Select())
    valor = forms.FloatField(label=u"Valor Pregunta", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '35%'}))


class EvaluacionPreguntaEditForm(forms.Form):
    valor = forms.FloatField(label=u"Valor Pregunta", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '35%'}))


class PersonaEvaluacionForm(forms.Form):
    persona = forms.ModelChoiceField(label=u"Persona", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=True, widget=forms.Select())
    numintentos = forms.IntegerField(label=u"Número de Intentos", required=True, initial=0, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '35%'}))
