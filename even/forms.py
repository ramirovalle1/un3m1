# -*- coding: UTF-8 -*-
from datetime import datetime
from fileinput import FileInput

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms import DateTimeInput

from even.models import Evento,TipoEvento,TIPOS_PERFILES
from sga.models import Periodo, Canton
from sga.forms import ExtFileField, deshabilitar_campo,campo_modobloqueo


class MantenimientoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True, widget=forms.Textarea({'rows': '2',
                                                                                              'formwidth': '100%',
                                                                                              "tooltip": "NOMBRE DEL EVENTO"}))


class PeriodoEventoForm(forms.Form):
    aplicaperiodo = forms.BooleanField(initial=True, label=u'Rige a periodo académico?', required=False)
    periodo = forms.ModelChoiceField(Periodo.objects.filter(status=True), label=u"Periodo académico", required=False)
    evento = forms.ModelChoiceField(Evento.objects.filter(status=True), label=u"Evento", required=False)
    tipo = forms.ModelChoiceField(TipoEvento.objects.filter(status=True), label=u"Tipo de Evento", required=False)
    descripcionbreve = forms.CharField(label=u'Descripcion Breve', required=True, widget=forms.Textarea({'rows': '2',
                                                                                              'formwidth': '100%',
                                                                                              "tooltip": "DESCRIPCIÓN BREVE"}))
    cuerpo = forms.CharField(label=u"Información", required=False, widget=CKEditorUploadingWidget())
    iframemapa = forms.CharField(label=u'Iframe Evento', required=False, widget=forms.Textarea({'rows': '2'}))
    link = forms.CharField(label=u'Link de redireccionamiento', required=False, widget=forms.TextInput())
    fechainicio = forms.DateField(label=u"Fecha inicio del evento", initial=datetime.now().date(), required=False,
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number' ,'formwidth': '45%'}))
    fechafin = forms.DateField(label=u"Fecha fin del evento", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number','formwidth': '45%'}))
    horainicio = forms.TimeField(label=u"Hora Desde", required=False, initial=str(datetime.now().time()),
                                 input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','formwidth': '45%'}))
    horafin = forms.TimeField(label=u'Hora Hasta', required=False, initial=str(datetime.now().time()),input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','formwidth': '45%'}))

    fechainicioinscripcion = forms.DateField(label=u"Inicio inscripciones", initial=datetime.now().date(), required=False,
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number' ,'formwidth': '45%'}))
    fechafininscripcion = forms.DateField(label=u"Fin inscripciones", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number','formwidth': '45%'}))
    fechainicioconfirmar = forms.DateField(label=u"Inicio confirmación", initial=datetime.now().date(), required=False,
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number' ,'formwidth': '45%'}))
    fechafinconfirmar = forms.DateField(label=u"Fin confirmación", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number','formwidth': '45%'}))
    validacupo = forms.BooleanField(initial=False, label=u'Valida cupo?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '45%'}))
    cupo = forms.CharField(label=u"Cupo",initial=0,required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'class': 'imp-numbersmall', 'decimal': '0'}))
    publicar = forms.BooleanField(initial=False, label=u'Desea publicarlo?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    permiteregistro = forms.BooleanField(initial=False, label=u'Permite inscripciones?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    todos = forms.BooleanField(initial=False, label=u'Evento para todas las provincias', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    cantones = forms.ModelMultipleChoiceField(label=u'Cantones',
                                              queryset=Canton.objects.filter(provincia__pais=1,status=True).order_by(
                                                  'nombre'), required=False)
    tipoperfil = forms.ChoiceField(choices=TIPOS_PERFILES, required=False, label=u'Tipo de Usuario',
                                    widget=forms.Select(attrs={'class': 'imp-25'}))

    imagen = ExtFileField(label=u'Imagen', required=False, help_text=u'Tamaño maximo permitido 4Mb, en formato jpeg,jpg,png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)
    portada = ExtFileField(label=u'Portada', required=False, help_text=u'Tamaño maximo permitido 4Mb, en formato jpeg,jpg,png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)



    def bloquear_campos(self):
        deshabilitar_campo(self, 'aplicaperiodo')
        deshabilitar_campo(self, 'periodo')
        deshabilitar_campo(self, 'publicar')
        deshabilitar_campo(self, 'todos')
        deshabilitar_campo(self, 'cantones')

    def bloquear_cupo(self,valor):
        campo_modobloqueo(self, 'cupo',valor)

class PeriodoEvento2Form(forms.Form):
    evento = forms.ModelChoiceField(Evento.objects.filter(status=True), label=u"Evento", required=False)
    tipo = forms.ModelChoiceField(TipoEvento.objects.filter(status=True), label=u"Tipo de Evento", required=False)
    descripcionbreve = forms.CharField(label=u'Descripcion Breve', required=True, widget=forms.Textarea({'rows': '2',
                                                                                              'formwidth': '100%',
                                                                                              "tooltip": "DESCRIPCIÓN BREVE"}))
    cuerpo = forms.CharField(label=u"Información", required=False, widget=CKEditorUploadingWidget())
    fechainicio = forms.DateField(label=u"Fecha inicio del evento", initial=datetime.now().date(), required=False,
                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number' ,'formwidth': '35%'}))
    fechafin = forms.DateField(label=u"Fecha fin del evento", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number','formwidth': '35%'}))
    horainicio = forms.TimeField(label=u"Hora Desde", required=False, initial=str(datetime.now().time()),
                                 input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','formwidth': '35%'}))
    horafin = forms.TimeField(label=u'Hora Hasta', required=False, initial=str(datetime.now().time()),
                              input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','formwidth': '35%'}))
    cantones = forms.ModelMultipleChoiceField(label=u'Cantones',
                                              queryset=Canton.objects.filter(provincia__pais=1,status=True).order_by(
                                                  'nombre'), required=False)
    tipoperfil = forms.ChoiceField(choices=TIPOS_PERFILES, required=False, label=u'Tipo de Usuario',
                                    widget=forms.Select(attrs={'class': 'imp-25'}))


