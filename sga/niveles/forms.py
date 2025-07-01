# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta
from typing import Union

from django import forms
from django.db.models import Q
from django.forms import ValidationError
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from sga.models import Modalidad, Sesion, Coordinacion, CLASIFICACION_PERIODO, Periodo, Persona
from django.db import models, connection, connections


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


class NivelLibreForm(forms.Form):
    coordinacion = forms.ModelChoiceField(label=u"Coordinación", queryset=Coordinacion.objects.all(), required=True, widget=forms.Select(attrs={'class': 'form-select', 'col': '12'}))
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), widget=forms.Select(attrs={'class': 'form-select', 'col': '6'}), required=True)
    sesion = forms.ModelChoiceField(label=u"Sección", queryset=Sesion.objects.filter(status=True), widget=forms.Select(attrs={'class': 'form-select', 'col': '6'}), required=True)
    paralelo = forms.CharField(label=u"Jornada", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    inicio = forms.DateField(label=u"Fecha Inicio", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    fin = forms.DateField(label=u"Fecha Fin", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    fechainicioagregacion = forms.DateField(label=u"Fecha inicio agregación (Matrícula)", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    fechatopematricula = forms.DateField(label=u"Fecha limite ordinaria (Matrícula)", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    fechatopematriculaext = forms.DateField(label=u"Fecha limite extraordinaria (Matrícula)", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    fechatopematriculaesp = forms.DateField(label=u"Fecha limite especial (Matrícula)", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    fechafinagregacion = forms.DateField(label=u"Fecha fin agregación (Matrícula)", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    fechafinquitar = forms.DateField(label=u"Fecha fin quitar (Matrícula)", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    nivelgrado = forms.BooleanField(label=u"Costo Fijo", required=False, initial=False)

    def new(self):
        del self.fields['paralelo']
        deshabilitar_campo(self, 'coordinacion')
        self.fields['coordinacion'].required = False

    def edit(self):
        deshabilitar_campo(self, 'coordinacion')
        deshabilitar_campo(self, 'modalidad')
        deshabilitar_campo(self, 'sesion')
        self.fields['coordinacion'].required = False
        self.fields['modalidad'].required = False
        self.fields['sesion'].required = False

    def set_sesion(self, coordinacion):
        if coordinacion:
            if coordinacion.id in [1, 2, 3, 4, 5]:
                self.fields['sesion'].queryset = Sesion.objects.filter(status=True, clasificacion=1, tipo=1)
            elif coordinacion.id in [9]:
                self.fields['sesion'].queryset = Sesion.objects.filter(Q(clasificacion=3, tipo=1) | Q(pk=13), status=True)
            elif coordinacion.id in [7, 10, 13]:
                self.fields['sesion'].queryset = Sesion.objects.filter(Q(status=True) & Q(nombre__icontains='POSGRADO') & ~Q(pk=19))
            else:
                self.fields['sesion'].queryset = Sesion.objects.filter(Q(status=True) & (~Q(nombre__icontains='POSGRADO') | Q(pk=19)))
        else:
            self.fields['sesion'].queryset = Sesion.objects.filter(status=True)


class PeriodoCalificacionForm(forms.Form):
    clasificacion = forms.ChoiceField(label=u'Tipo', choices=CLASIFICACION_PERIODO, required=True, widget=forms.Select(attrs={'class': 'form-select', 'col': '6'}), error_messages={'invalid_choice': 'Complete campo de clasificación', 'required': 'Complete campo de clasificación'})
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), required=True, widget=forms.Select(attrs={'class': 'form-select', 'col': '6'}), error_messages={'invalid_choice': 'Complete campo de modalidad', 'required': 'Complete campo de modalidad'})
    periodo = forms.ModelChoiceField(label=u"Período académico", queryset=Periodo.objects.none(), required=True, widget=forms.Select(attrs={'class': 'form-select', 'col': '12'}), error_messages={'invalid_choice': 'Complete campo de periodo', 'required': 'Complete campo de periodo'})

    def set_periodo(self, id):
        self.fields['periodo'].queryset = Periodo.objects.filter(pk=id)

    def clean(self):
        cleaned_data = super(PeriodoCalificacionForm, self).clean()
        return cleaned_data



FORMATOS = (
    ('', u'SIN CLASIFICACIÓN'),
    ('xlsx', u'EXCEL'),
    ('pdf', u'PDF'),
)


class EstudianteMatriculadoPosgradoForm(forms.Form):
    rt = forms.ChoiceField(label=u'Formato', choices=FORMATOS, required=True, widget=forms.Select(attrs={'class': 'form-select', 'col': '12'}), error_messages={'invalid_choice': 'Complete campo de formato', 'required': 'Complete campo de formato'})
    ffin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '12', 'pattern': "\d{4}-\d{2}-\d{2}"}), error_messages={'required': 'Complete campo de fecha fin'})

    def clean(self):
        cleaned_data = super(EstudianteMatriculadoPosgradoForm, self).clean()
        return cleaned_data


class FiltroCoordinacionForm(forms.Form):
    aplica = forms.BooleanField(initial=True, label=u"¿Aplica filtro?", required=False, widget=forms.CheckboxInput(attrs={'col': '12'}))
    coordinacion = forms.ModelChoiceField(label=u"Coordinación", queryset=Coordinacion.objects.none(), required=True, widget=forms.Select(attrs={'class': 'form-select', 'col': '12'}), error_messages={'invalid_choice': 'Complete campo de coordinación', 'required': 'Complete campo de coordinación'})

    def set_coordinacion_facultad(self):
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(pk__in=[1, 2, 3, 4, 5])

    def set_required_coordinacion(self, aplica):
        self.fields['coordinacion'].required = aplica

    def clean(self):
        cleaned_data = super(FiltroCoordinacionForm, self).clean()
        return cleaned_data


class FiltroMultipleCoordinacionForm(forms.Form):
    coordinacion = forms.ModelMultipleChoiceField(label=u"Coordinaciones", queryset=Coordinacion.objects.none(), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-select', 'col': '12'}), error_messages={'invalid_choice': 'Complete campo de coordinación', 'required': 'Complete campo de coordinación'})

    def set_coordinacion_facultad(self):
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(pk__in=[1, 2, 3, 4, 5])

    def clean(self):
        cleaned_data = super(FiltroMultipleCoordinacionForm, self).clean()
        return cleaned_data


class FiltroFechaForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control form-date', 'col': '12', 'pattern': "\d{4}-\d{2}-\d{2}"}), error_messages={'required': 'Complete campo de fecha'})

    def clean(self):
        cleaned_data = super(FiltroFechaForm, self).clean()
        return cleaned_data


class ReporteMatriculadoForm(forms.Form):
    periodo = forms.ModelChoiceField(label=u"Periodo", queryset=Periodo.objects.none(), required=True, widget=forms.Select(attrs={'class': 'form-select', 'col': '12'}), error_messages={'invalid_choice': 'Complete campo de periodo', 'required': 'Complete campo de periodo'})
    coordinacion = forms.ModelMultipleChoiceField(label=u"Facultad", queryset=Coordinacion.objects.none(), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-select', 'col': '12'}), error_messages={'invalid_choice': 'Complete campo de facultad', 'required': 'Complete campo de facultad'})
    persona = forms.ModelMultipleChoiceField(label=u"Dirigir a", queryset=Persona.objects.none(), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-select', 'col': '12'}), error_messages={'invalid_choice': 'Complete campo de dirigir a', 'required': 'Complete campo de dirigir a'})

    def set_periodo(self, id):
        self.fields['periodo'].queryset = Periodo.objects.filter(pk=id)

    def set_coordinacion(self, eCoordinaciones):
        self.fields['coordinacion'].queryset = eCoordinaciones

    def set_persona(self, ePersonas):
        self.fields['persona'].queryset = ePersonas

    def clean(self):
        cleaned_data = super(ReporteMatriculadoForm, self).clean()
        return cleaned_data


class NivelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.pk} - {obj.paralelo} {obj.carrera if obj.carrera else ""} {obj.sesion.nombre} Desde: {obj.inicio} | Hasta: {obj.fin}'


class NivelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.pk} - {obj.paralelo} {obj.carrera if obj.carrera else ""} {obj.sesion.nombre} Desde: {obj.inicio} | Hasta: {obj.fin}'


class NivelesMatriculaModulosInglesForm(forms.Form):
    from sga.models import Nivel, NivelMalla
    matriculacionactivaingles = forms.BooleanField(label=u"Matriculacion activa", required=False, initial=False,  widget=forms.CheckboxInput())
    validanivelesanterioresingles = forms.BooleanField(label=u"Valida niveles anteriores", required=False, initial=False,  widget=forms.CheckboxInput())
    nivelesanterioresingles = NivelMultipleChoiceField(label=u"Niveles anteriores", required=False, queryset=Nivel.objects.filter(materia__asignaturamalla__malla_id=353).distinct(), widget=forms.SelectMultiple(attrs={'class': 'form-select select2', 'multiple': 'multiple', 'style': 'width:100%', 'disabled': True}))
    nivelactualingles = NivelChoiceField(label=u"Nivel actual", required=True, queryset=Nivel.objects.filter(materia__asignaturamalla__malla_id=353).distinct(), widget=forms.Select(attrs={'class': 'form-select select2 ', 'style': 'width:100%', 'col': '12'}))
    nivelminimo = forms.ModelChoiceField(label=u"Nivel minimo", queryset=NivelMalla.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'form-select select2', 'style': 'width:100%', 'col': '12'}), error_messages={'invalid_choice': 'Complete campo de nivel actual', 'required': 'Complete campo de nivel actual'})

    def clean(self):
        return super(NivelesMatriculaModulosInglesForm, self).clean()


class NivelesMatriculaModulosInformaticaForm(forms.Form):
    from sga.models import Nivel
    matriculacionactivainformatica = forms.BooleanField(label=u"Matriculacion activa", required=False, initial=False, widget=forms.CheckboxInput())
    validanivelesanterioresinformatica = forms.BooleanField(label=u"Valida niveles anteriores", required=False, initial=False,  widget=forms.CheckboxInput())
    nivelesanterioresinformatica = NivelMultipleChoiceField(label=u"Niveles anteriores", required=False, queryset=Nivel.objects.filter(materia__asignaturamalla__malla_id=32).distinct(), widget=forms.SelectMultiple(attrs={'class': 'form-select select2', 'style': 'width:100%', 'multiple': 'multiple', 'disabled': True}))
    nivelactualinformatica = NivelChoiceField(label=u"Nivel actual", queryset=Nivel.objects.filter(materia__asignaturamalla__malla_id=32).distinct(), required=True, widget=forms.Select(attrs={'class': 'form-select select2', 'style': 'width:100%',  'col': '12'}), error_messages={'invalid_choice': 'Complete campo de nivel actual', 'required': 'Complete campo de nivel actual'})

    def clean(self):
        return super(NivelesMatriculaModulosInformaticaForm, self).clean()