# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from becadocente.models import *
from core.custom_forms import FormModeloBase
from sga.forms import ExtFileField, deshabilitar_campo


class ConvocatoriaBecaForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=150, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))
    archivoresolucion = ExtFileField(label=u'Resolución OCS', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'fieldbuttonsright': [{'id': 'viewresolucion', 'tooltiptext': 'Visualizar Archivo cargado', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-eye'}]}))
    archivoconvocatoria = ExtFileField(label=u'Bases Convocatoria', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'fieldbuttonsright': [{'id': 'viewconvocatoria', 'tooltiptext': 'Visualizar Archivo cargado', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-eye'}]}))
    iniciopos = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Postulación'}), required=False)
    finpos = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    # mensajepos = forms.CharField(label=u"Mensaje informativo", required=False, widget=forms.Textarea(attrs={'col': '12'}))
    inicioveri = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Verificación de Requisitos'}), required=False)
    finveri = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    # mensajeveri = forms.CharField(label=u"Mensaje informativo", required=False, widget=forms.Textarea(attrs={'col': '12'}))
    iniciosel = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Calificación y Selección'}), required=False)
    finsel = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    # mensajesel = forms.CharField(label=u"Mensaje informativo", required=False, widget=forms.Textarea(attrs={'col': '12'}))
    inicioadj = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Adjudicación'}), required=False)
    finadj = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    # mensajeadj = forms.CharField(label=u"Mensaje informativo", required=False, widget=forms.Textarea(attrs={'col': '12'}))
    inicionoti = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Notificación'}), required=False)
    finnoti = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    # mensajenoti = forms.CharField(label=u"Mensaje informativo", required=False, widget=forms.Textarea(attrs={'col': '12'}))
