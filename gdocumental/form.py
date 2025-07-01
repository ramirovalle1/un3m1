# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms import ValidationError
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe

from core.custom_forms import FormModeloBase
from gdocumental.models import ROLES_USUARIOS_DOCUMENTAL, DocumentosPlantillas, RequisitosPlantillaProcesos, \
    CategoriaPlantillas, TIPO_CARPETA_PROCESO, ESTADO_SOLICITUD_DOCUMENTAL, PlantillaProcesos, \
    DepartamentoArchivosGestiones
from sga.forms import ExtFileField
from sga.funciones import variable_valor
from sagest.models import Departamento, DenominacionPuesto

from sga.My_Model.SubirMatrizSENESCYT import My_CriterioSubirMatrizInscripcion, My_TituloProcesoSubirMatrizInscripcion

from django.db import models, connection, connections

from sga.models import Persona
from voto.models import SedesElectoralesPeriodo, DignidadesElectorales


class SolicitudFirmaDocumentoForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input'}))
    archivo_original = ExtFileField(label=u'Archivo', required=False,
                                    help_text=u'Tamaño máximo permitido 10Mb, en formato pdf',
                                    ext_whitelist=(".pdf",), max_upload_size=1055555194304,
                                    widget=forms.FileInput(attrs={'formwidth': '100%', 'class': 'dropify'}))


class FirmarDocumentoForm(FormModeloBase):
    numpagina = forms.IntegerField(label=u'Número de página a firmar', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    posx = forms.IntegerField(label=u'Pos. X', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    posy = forms.IntegerField(label=u'Pos. Y', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    posw = forms.IntegerField(label=u'Pos. Width', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    posh = forms.IntegerField(label=u'Pos. Height', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    password = forms.CharField(label=u'Contraseña', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input'}))
    firmap12 = ExtFileField(label=u'Firma Digital', required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato p12', ext_whitelist=(".p12",),
                            max_upload_size=10194304, widget=forms.FileInput(attrs={'formwidth': '100%', 'accept': ".p12", 'class': 'filep12'}))


class DepartamentoArchivosForm(FormModeloBase):
    nomslug = forms.CharField(label=u'Codigo Departamento', max_length=100, required=True, widget=forms.TextInput({'col': '6', 'onKeyPress': 'return soloNomenclaturas(event)'}))
    departamento = forms.ModelChoiceField(label=u"Departamento", queryset=Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=True, widget=forms.Select({'col': '6'}))
    responsable = forms.ModelChoiceField(label=u"Responsable", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=True, widget=forms.Select({'col': '12',}))
    filesize = forms.FloatField(label=u"Tamaño de Archivos (MB)", initial="00.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '4', 'col': '6', 'onKeyPress': "return soloNumerosValor(event)", }))
    storagesizegb = forms.FloatField(label=u"Espacio Disponible (GB)", initial="00.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '4', 'col': '6', 'onKeyPress': "return soloNumerosValor(event)", }))


class DepartamentoGestionArchivosForm(FormModeloBase):
    nomslug = forms.CharField(label=u'Codigo Gestión', max_length=100, required=True, widget=forms.TextInput({'col': '6','onKeyPress': 'return soloNomenclaturas(event)'}))
    responsable = forms.ModelChoiceField(label=u"Responsable", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=True, widget=forms.Select())


class DocuPlantillaForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '5'}), required=True)


class CatPlantillaForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '5'}), required=True)


class PlantillaProcesoForm(FormModeloBase):
    categoria = forms.ModelChoiceField(label=u"Categoría", queryset=CategoriaPlantillas.objects.filter(status=True).order_by('descripcion'), required=True, widget=forms.Select({'col': '6'}))
    nomenclatura = forms.CharField(label=u'Nomenclatura', max_length=1000, required=True, widget=forms.TextInput({'col': '6'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '5'}), required=True)
    version = forms.CharField(label=u'Versión', max_length=100, required=True, widget=forms.TextInput({'col': '6'}))
    vigente = forms.BooleanField(initial=False, label=u"Vigente?", required=False, widget=forms.CheckboxInput(attrs={'col': '6'}))


class RequisitoPlantillaProcesoForm(FormModeloBase):
    ref = forms.ModelChoiceField(label=u"Depende de", queryset=RequisitosPlantillaProcesos.objects.filter(status=True).order_by('orden'), required=False, widget=forms.Select())
    orden = forms.IntegerField(label=u'Orden', initial=0, required=True, widget=forms.TextInput(attrs={'col': '6', 'decimal': '0'}))
    horas = forms.IntegerField(label=u'Num. Horas', initial=0, required=True, widget=forms.TextInput(attrs={'col': '6', 'decimal': '0'}))
    documento = forms.ModelChoiceField(label=u"Documento", queryset=DocumentosPlantillas.objects.filter(status=True).order_by('descripcion'), required=True, widget=forms.Select())
    responsable = forms.ModelChoiceField(label=u"Responsable", queryset=DenominacionPuesto.objects.filter(status=True).order_by('descripcion'), required=True, widget=forms.Select({'col': '6'}))
    obligatorio = forms.BooleanField(initial=False, label=u"Obligatorio?", required=False, widget=forms.CheckboxInput(attrs={'col': '6'}))
    departamentoreponsable = forms.ModelChoiceField(label="Departamento Responsable", queryset=Departamento.objects.filter(integrantes__isnull=False, status=True).distinct(), required=True, widget=forms.Select({'col': '12'}))


class AperturaProcesoForm(FormModeloBase):
    gestion= forms.ModelChoiceField(label=u'Gestión', required=True, queryset=DepartamentoArchivosGestiones.objects, widget=forms.Select({'col':'12'}))
    tipo = forms.ChoiceField(choices=TIPO_CARPETA_PROCESO, required=True, label=u'Tipo de Proceso', widget=forms.Select(attrs={'col': '6'}))
    finicio = forms.DateField(label=u"F. Inicio", required=True, widget=DateTimeInput({'col': '6'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '5'}), required=True)
    archivo = ExtFileField(label=u'Solicitud', required=False, help_text=u'Tamaño máximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput())

    def desactivar(self):
        self.fields['gestion'].required=False


class ValidarAperturaProcesoForm(FormModeloBase):
    estado = forms.ChoiceField(choices=ESTADO_SOLICITUD_DOCUMENTAL[1:], required=True, label=u'Estado', widget=forms.Select(attrs={'col': '6'}))
    finicio = forms.DateField(label=u"F. Inicio", required=True, widget=DateTimeInput({'col': '6'}))
    nombre = forms.CharField(label=u'Nombre Proceso', max_length=100, required=True, widget=forms.TextInput({'col': '12'}))
    observacion_validacion = forms.CharField(label=u"Observación", widget=forms.Textarea(attrs={'rows': '5'}), required=True)

    def desactivar(self):
        self.fields['finicio'].requires = False
        self.fields['nombre'].requires = False


class ValidarAperturaProcesoEstructuradoForm(FormModeloBase):
    estado = forms.ChoiceField(choices=ESTADO_SOLICITUD_DOCUMENTAL[1:], required=True, label=u'Estado', widget=forms.Select(attrs={'col': '6'}))
    categoria = forms.ModelChoiceField(label=u"Categoría", queryset=CategoriaPlantillas.objects.filter(status=True).order_by('descripcion'), required=True, widget=forms.Select({'col': '6'}))
    plantilla = forms.ModelChoiceField(label=u"Plantilla", queryset=PlantillaProcesos.objects.filter(status=True).order_by('descripcion'), required=True, widget=forms.Select({'col': '6'}))
    finicio = forms.DateField(label=u"F. Inicio", required=True, widget=DateTimeInput({'col': '6'}))
    nombre = forms.CharField(label=u'Nombre Proceso', max_length=100, required=True, widget=forms.TextInput({'col': '12'}))
    observacion_validacion = forms.CharField(label=u"Observación", widget=forms.Textarea(attrs={'rows': '5'}), required=True)

    def desactivar(self):
        self.fields['categoria'].required = False
        self.fields['plantilla'].required = False
        self.fields['finicio'].required = False
        self.fields['nombre'].required = False


class CarpetaPrincipalForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'formwidth': '100%'}))


class CarpetaForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre Proceso', required=True, widget=forms.Textarea({'formwidth': '100%', 'rows': '2'}))


class CompartirCarpetaForm(FormModeloBase):
    personas = forms.ModelMultipleChoiceField(label=u'Compartir con', queryset=Persona.objects.select_related().filter(status=True,), required=True, widget=forms.SelectMultiple(attrs={'col': '8'}))
    rol = forms.ChoiceField(choices=ROLES_USUARIOS_DOCUMENTAL[1:-1], required=True, label=u'Rol', widget=forms.Select(attrs={'col': '4'}))
    # esproceso = forms.BooleanField(initial=False, label=u"Tiene Responsables?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6'}))


class DepartamentoValidarDirectorForm(FormModeloBase):
    propietario = forms.ModelChoiceField(label=u"Asignar Propietario", queryset=Persona.objects.none(), required=True, widget=forms.Select({'col': '6'}))
    validar_director = forms.ChoiceField(choices=ESTADO_SOLICITUD_DOCUMENTAL, label=u"Validar Documento", required=True, widget=forms.Select(attrs={'col': '6'}))


class DepartamentoValidarArchivoForm(FormModeloBase):
    archivo = ExtFileField(label=u'Documento Solicitado', required=True, help_text=u'Tamaño máximo permitido 4Mb, en formato .pdf',
                           ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput())
