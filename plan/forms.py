import os
from datetime import datetime, timedelta
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms import ValidationError, DateTimeInput

from core.custom_forms import FormModeloBase
from plan.models import *
from sagest.models import PeriodoPerfilPuesto, Departamento, DireccionPerfilPuesto, CompetenciaLaboral, \
    DenominacionPuesto
from sga.models import AreaConocimientoTitulacion


def deshabilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True
    form.fields[campo].widget.attrs['disabled'] = True

class PeriodoPlanThForm(FormModeloBase):
    fechainicio = forms.DateField(label=u"Fecha Inicio",
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '3'}))
    fechafin = forms.DateField(label=u"Fecha Fin",
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '3'}))

    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'col':'12', 'separator3': True}))

class ModeloOrganizacionPlanThForm(FormModeloBase):
    organizacion = forms.ModelChoiceField(ModeloGestionOrganizacionPlanTh.objects.filter(status=True,activo=True), required=True, label=u'Organización', widget=forms.Select())

class ModeloTrabajadorPlanThForm(FormModeloBase):
    trabajador = forms.ModelChoiceField(ModeloGestionTrabajadorPlanTh.objects.filter(status=True,activo=True), required=True, label=u'Trabajador', widget=forms.Select())

class DafoPersonaPlanThForm(FormModeloBase):
    tipo = forms.ChoiceField(label=u'Tipo', choices=MODELO_DAFO, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'col':'12', 'separator3': True}))

class PlanAccionPersonaPlanThForm(FormModeloBase):
    competencia = forms.ModelChoiceField(CompetenciaLaboral.objects.filter(status=True), required=True, label=u'Competencia', widget=forms.Select())
    medio = forms.ModelChoiceField(MedioPlanTh.objects.filter(status=True,activo=True), required=True, label=u'Medio', widget=forms.Select())
    porcentaje_medio = forms.DecimalField(initial='0.00', label=u"Porcentaje de medio", widget=forms.TextInput(attrs={'col':'3','class': 'imp-number'}))
    tematica = forms.CharField(required=False, label=u'Temática', widget=forms.Textarea(attrs={'col':'12', 'separator3': True}))
    validacionplan = forms.BooleanField(initial=False, required=False, label=u'¿Valida en el plan de desarrollo?', widget=forms.CheckboxInput(attrs={'class': 'js-switch','col':'6', 'data-switchery': 'true'}))
    evidencia = forms.BooleanField(initial=False, required=False, label=u'¿Sube evidencia?', widget=forms.CheckboxInput(attrs={'class': 'js-switch','col':'6', 'data-switchery': 'true'}))

class PerfilPuestoPeriodoForm(FormModeloBase):
    periodopuesto = forms.ModelChoiceField(PeriodoPerfilPuesto.objects.filter(status=True, activo=True), required=True, label=u'Período', widget=forms.Select(attrs={'col': '6', 'separator3': True}))
    direccion = forms.ModelChoiceField(DireccionPerfilPuesto.objects.filter(status=True, activo=True), required=True, label=u'Departamento', widget=forms.Select(attrs={'col': '6', 'separator3': True}))

    def editar(self):
        deshabilitar_campo(self, 'direccion')

class ModeloGestionGenericoPlanThForm(FormModeloBase):
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.TextInput())
    activo = forms.BooleanField(initial=False, required=False, label=u'¿Activo?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))

class MovilidadCarreraPlanThForm(FormModeloBase):
    areaconocimiento = forms.ModelChoiceField(AreaConocimientoTitulacion.objects.filter(status=True), required=True, label=u'Area conocimiento', widget=forms.Select())
    unidadorganizacional = forms.ModelChoiceField(Departamento.objects.filter(status=True,integrantes__isnull=False).distinct(), required=True, label=u'Unidad organizacional', widget=forms.Select())
    cargo = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True), required=True, label=u'Cargo', widget=forms.Select())

class MovilidadSucesionPlanThForm(FormModeloBase):
    competencia = forms.ModelChoiceField(CompetenciaLaboral.objects.filter(status=True), required=True, label=u'Competencia', widget=forms.Select())
    tipolinea = forms.ModelChoiceField(TipoLineaPlanTh.objects.filter(status=True,activo=True), required=True, label=u'Tipo de línea', widget=forms.Select())
    unidadorganizacional = forms.ModelChoiceField(Departamento.objects.filter(status=True,integrantes__isnull=False).distinct(), required=True, label=u'Unidad organizacional', widget=forms.Select())
    cargo = forms.ModelChoiceField(DenominacionPuesto.objects.filter(status=True), required=True, label=u'Cargo', widget=forms.Select())


