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
from balcon.models import Solicitud, Proceso, Categoria, Requisito, Tipo, Servicio, Informacion, TIPO_INFORMACION, \
    ProcesoServicio, ESTADOS_SOLICITUD_INFORMATICOS, ESTADO_SOLICITUD_BALCON
from django.db import models, connection, connections

from sagest.models import OpcionSistema, Departamento, ESTADOS_SOLICITUD_PRODUCTOS
from sga.forms import ExtFileField, deshabilitar_campo
from sga.models import Persona, Coordinacion
from core.custom_forms import FormModeloBase


class SolicitudBalconExternoForm(forms.Form):
    proceso = forms.ModelChoiceField(required=True, label=u'Proceso',
                                     queryset=Proceso.objects.filter(status=True, activoadmin=True, externo=True),
                                     widget=forms.Select(attrs={'class': 'form-control'}))
    servicio = forms.ModelChoiceField(required=True, label=u'Servicio',
                                      queryset=Informacion.objects.filter(mostrar=True, tipo=2, status=True),
                                      widget=forms.Select(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(label=u'Descripción',
                                  widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=True)


class SolicitudBalconForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Archivo solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg",), max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'formwidth': '50%'}))


class ProcesoForm(FormModeloBase):
    sigla = forms.CharField(label=u'Siglas', max_length=100, required=True,
                            widget=forms.TextInput(attrs={'class': 'imp-100 form-control', 'col':'12'}))
    descripcion = forms.CharField(label=u'Nombre', required=True,
                                  widget=forms.Textarea({'class': 'form-control', 'rows': '2', 'formwidth': '100%' }))
    # tiempoestimado = forms.CharField(label=u'Tiempo estimado', max_length=100, required=True,
    #                                  widget=forms.TextInput(attrs={'class': 'imp-50'}))
    tipo = forms.ModelChoiceField(Tipo.objects.filter(estado=True, status=True).order_by('id'), required=True,
                                  label=u'Tipo', widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    categoria = forms.ModelChoiceField(Categoria.objects.filter(estado=True, status=True).order_by('id'), required=True,
                                       label=u'Categoría', widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct().order_by('id'), required=True,
        label=u'Dirección', widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    # servicio = forms.ModelMultipleChoiceField(label=u'Servicios',
    #                                           queryset=Servicio.objects.filter(status=True, estado=True).order_by(
    #                                               'descripcion'), required=False)
    # responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable',
    #                                  widget=forms.TextInput(attrs={'select2search': 'true'}))
    subesolicitud = forms.BooleanField(label=u'¿Sube solicitud?', required=False,
                                       widget=forms.CheckboxInput(attrs={'formwidth': '100%', 'col':'12'}))
    interno = forms.BooleanField(label=u'Para Internos', required=False,
                                 widget=forms.CheckboxInput(attrs={'formwidth': '50%', 'col':'6'}))
    externo = forms.BooleanField(label=u'Para Externos', required=False,
                                 widget=forms.CheckboxInput(attrs={'formwidth': '50%', 'col':'6'}))


class RequisitoServicioForm(forms.Form):
    requisito = forms.ModelChoiceField(label=u'Requisito', widget=forms.Select(),
                                       queryset=Requisito.objects.filter(status=True, estado=True).order_by(
                                           'descripcion'), required=True)
    obligatorio = forms.BooleanField(label=u'¿Es Obligatorio?', required=False
                                     , widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    # leyenda = forms.CharField(label=u'Leyenda', widget=forms.Textarea(attrs={'rows': '3', 'class': 'normal-input'}), required=False)
    activo = forms.BooleanField(label=u'Activo', required=False
                                , widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class TipoProcesoServicioForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True, widget=forms.Textarea({'rows': '2', 'formwidth': '100%'}))
    descripcion = forms.CharField(label=u"Descripción", required=True, widget=CKEditorUploadingWidget())
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct().order_by('id'), required=True,
        label=u'Dirección', widget=forms.Select())
    mostrar = forms.BooleanField(label=u'Mostrar', required=False,
                                 widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class CategoriaBalconForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripcion', required=True, widget=forms.Textarea({'rows': '2',
                                                                                              'formwidth': '100%',
                                                                                              "tooltip": "DETALLAR LA CATEGORIA"}))
    coordinaciones = forms.ModelMultipleChoiceField(label=u"Coordinaciones",
                                                    queryset=Coordinacion.objects.filter(status=True),
                                                    required=False,
                                                    widget=forms.SelectMultiple(attrs={'formwidth': '100%'}))

    estado = forms.BooleanField(label=u'Activo', required=False
                                , widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class RequisitoBalconForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripcion', required=True, widget=forms.Textarea({'rows': '2',
                                                                                              'formwidth': '100%',
                                                                                              "tooltip": "DETALLAR LA CATEGORIA"}))
    estado = forms.BooleanField(label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class ConfiguraServicioBalconForm(FormModeloBase):
    servicio = forms.ModelChoiceField(Servicio.objects.filter(status=True).order_by('id'), required=True,
                                      label=u'Servicio', widget=forms.Select())
    minimo = forms.IntegerField(initial="0", label=u'Tiempo Mínimo', required=False,
                                widget=forms.NumberInput(
                                    attrs={'class': 'numeric form-control', 'min': '0', 'col': '6'}))
    maximo = forms.IntegerField(initial="0", label=u'Tiempo Máximo', required=False,
                                widget=forms.NumberInput(
                                    attrs={'class': 'numeric form-control', 'min': '0', 'col': '6'}))
    minutos = forms.IntegerField(label=u"Tiempo en minutos", required=False, initial=0,
                                 widget=forms.NumberInput(
                                     attrs={'class': 'numeric form-control', 'min': '0'}))
    opcsistema = forms.ModelChoiceField(label=u'Opción Sistema', widget=forms.Select(),
                                        queryset=OpcionSistema.objects.filter(status=True).order_by('descripcion'),
                                        required=False)
    url = forms.CharField(label=u'Url', required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))


class TipoBalconForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripcion', required=True, widget=forms.Textarea({'rows': '2',
                                                                                              'formwidth': '100%',
                                                                                              "tooltip": "DETALLAR LA CATEGORIA"}))
    estado = forms.BooleanField(label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class ServicioBalconForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True,
                             widget=forms.TextInput(attrs={'class': 'imp-100'}))
    descripcion = forms.CharField(label=u'Descripcion', required=True,
                                  widget=forms.Textarea({'rows': '2', 'formwidth': '100%'}))
    opcsistema = forms.ModelMultipleChoiceField(label=u'Opciones', queryset=OpcionSistema.objects.all(), required=False)
    estado = forms.BooleanField(label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class InformacionBalconForm(FormModeloBase):
    tipo = forms.ChoiceField(label=u'Tipo de Respuesta', choices=TIPO_INFORMACION, required=False,
                             widget=forms.Select(attrs={'class': 'form-control', 'style': 'width:100%;'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3', 'col':'12'}), required=False)
    informacion = forms.CharField(label=u"Información", required=False,widget=forms.Textarea(attrs={'col':'12', 'separator3': True}))
    archivomostrar = ExtFileField(label=u'Archivo para mostrar', required=False, max_upload_size=4194304,
                                  help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                                  ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"),
                                  widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))
    archivodescargar = ExtFileField(label=u'Archivo a descargar', required=False, max_upload_size=4194304,
                                    help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                                    ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"),
                                    widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))
    # proceso = forms.ModelChoiceField(Proceso.objects.filter(activo=True, status=True).order_by('id'), required=False,
    #                                  label=u'Proceso', widget=forms.Select())
    # servicio = forms.IntegerField(initial=0, required=False, label=u'Servicio',
    #                               widget=forms.TextInput(attrs={'select2search': 'true'}))
    # servicio = forms.ModelChoiceField(ProcesoServicio.objects.filter(status=True).order_by('id'), required=True,
    #                                   label=u'Servicio', widget=forms.Select())
    mostrar = forms.BooleanField(label=u'Mostrar', required=False,
                                 widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class AgenteForm(FormModeloBase):
    persona = forms.ModelChoiceField(required=False, label=u'Personal',
                                     queryset=Persona.objects.select_related().filter(status=True).order_by(
                                         'apellido1'), widget=forms.Select({'col': '12', }))
    admin = forms.BooleanField(label=u'¿Es Administrador?', required=False,
                               widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    estado = forms.BooleanField(label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class AgenteEditForm(forms.Form):
    admin = forms.BooleanField(label=u'¿Es Administrador?', required=False,
                               widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    estado = forms.BooleanField(label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class ResponsableForm(FormModeloBase):
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct().order_by('id'), required=True,
        label=u'Dirección', widget=forms.Select(attrs={'formwidth': '100%'}))

    responsable = forms.ModelChoiceField(required=False, label=u'Responsable',
                                         queryset=Persona.objects.select_related().filter(status=True).order_by(
                                             'apellido1'), widget=forms.Select(attrs={'formwidth': '100%'}))

    estado = forms.BooleanField(label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class AsignarServicioForm(forms.Form):
    proceso = forms.ModelChoiceField(Proceso.objects.filter(activo=True, status=True).order_by('id'), required=True,
                                     label=u'Proceso', widget=forms.Select())
    servicio = forms.ModelChoiceField(ProcesoServicio.objects.filter(status=True).order_by('id'), required=True,
                                      label=u'Servicio', widget=forms.Select())


class RespuestaRapidaSolicitudForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class SolicitudBalconForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    # archivo = ExtFileField(label=u'Archivo solicitud', required=True,
    #                        help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
    #                        ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
    #                        widget=forms.FileInput(
    #                            attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))


class SolicitudManualBalconForm(forms.Form):
    persona = forms.IntegerField(initial=0, required=False, label=u'Persona',
                                 widget=forms.TextInput(attrs={'select2search': 'true'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    # archivo = ExtFileField(label=u'Archivo solicitud', required=True,
    #                        help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
    #                        ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
    #                        widget=forms.FileInput(
    #                            attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))


class SolicitudBalconEditForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class SolicitudBalconRespuestaRapidaForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)

class SolicitudBalconRespuestaRechazarForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class SolicitudBalconResolverForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'class': 'editor', 'name': 'observacion'}), required=True)
    archivo = ExtFileField(label=u'Archivo solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))


class SolicitudBalconGestionarForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3', 'class': 'ckeditor'}), required=True)
    estado = forms.ChoiceField(label=u'Estado', choices=ESTADO_SOLICITUD_BALCON, required=True,
                               widget=forms.Select(attrs={'formwidth': '100%'}))
    archivo = ExtFileField(label=u'Archivo solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))


class SolicitudBalconCerrarForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    archivo = ExtFileField(label=u'Archivo solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))


class SolicitudBalconReasignarForm(forms.Form):
    # departamento = forms.ModelChoiceField(Departamento.objects.filter(integrantes__isnull=False, status=True).distinct().order_by('id'), required=True,
    #   label=u'Dirección', widget=forms.Select())
    asignadorecibe = forms.IntegerField(initial=0, required=False, label=u'Persona',
                                        widget=forms.TextInput(attrs={'select2search': 'true'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    archivo = ExtFileField(label=u'Archivo solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))


class SolicitudBalconReasignarInternoForm(forms.Form):
    asignadorecibe = forms.IntegerField(initial=0, required=False, label=u'Persona',
                                        widget=forms.TextInput(attrs={'select2search': 'true'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    archivo = ExtFileField(label=u'Archivo solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))


class SolicitudInformacionServicioForm(forms.Form):
    codigodocumento = forms.CharField(label=u'Nro.', required=False,
                                      widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '33%'}))
    fechaoperacion = forms.DateField(label=u"Fecha Solicitud", input_formats=['%d-%m-%Y'], required=False,
                                     widget=DateTimeInput(format='%d-%m-%Y',
                                                          attrs={'class': 'selectorfecha', 'formwidth': '33%'}))
    departamento = forms.ModelChoiceField(
        Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=True,
        label=u'Dirección', widget=forms.Select(attrs={'formwidth': '100%'}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(administrativo__isnull=False), required=True,
                                         label=u'Responsable', widget=forms.Select(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(label=u'Motivo Solicitud', required=True, widget=forms.Textarea(attrs={'rows': '3'}))
    archivo = ExtFileField(label=u'Archivo solicitud', required=True,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg",), max_upload_size=4194304,
                           widget=forms.FileInput(attrs={'formwidth': '100%'}))

    def adicionar(self):
        deshabilitar_campo(self, 'codigodocumento')
        deshabilitar_campo(self, 'fechaoperacion')
        self.fields['responsable'].queryset = Persona.objects.filter(administrativo__isnull=False).filter(id=None)


class SolicitudObservacionServiciosForm(forms.Form):
    estados = forms.ChoiceField(label=u'Estado', choices=ESTADOS_SOLICITUD_PRODUCTOS, required=True,
                                widget=forms.Select(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)


class EncuestaPreguntasBalconForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    estado = forms.BooleanField(label=u'Activo', required=False,
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class EstrellasEncuestaForm(forms.Form):
    cantidad = forms.IntegerField(
        label=u'Cantidad de estrellas',
        widget=forms.NumberInput(attrs={'class': 'numeric form-control', 'max': '10', 'min': '0'}),
        initial=0,
        required=True
    )
