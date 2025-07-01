import os
from datetime import datetime, timedelta
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms import ValidationError, DateTimeInput

from automatiza.models import PRIORIDAD, RequerimientoPlanificacionAutomatiza, TIPO_REQUERIMIENTO_AUTOMATIZA
from core.custom_forms import FormModeloBase
from sagest.models import SeccionDepartamento, Departamento

from sga.models import Persona


class PlanificacionAutomatizaForm(FormModeloBase):
    departamento = forms.ModelChoiceField(Departamento.objects.filter(status=True,integrantes__isnull=False).distinct(), label=u"Dirección")
    nombre = forms.CharField(required=False, label=u'Nombre', widget=forms.TextInput(attrs={'col':'12'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio",
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}))
    fechafin = forms.DateField(label=u"Fecha Fin",
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}))
    mostrar = forms.BooleanField(label=u'Mostrar', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%','col': '4'}))
    detalle = forms.CharField(required=False, label=u'Detalle', widget=forms.Textarea(attrs={'col':'12', 'separator3': True}))


class RequerimientoPlanificacionAutomatizaForm(FormModeloBase):
    gestion = forms.ModelChoiceField(SeccionDepartamento.objects.filter(status=True, departamento__integrantes__isnull=False).distinct(), label=u"Gestión", widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    prioridad = forms.ChoiceField(choices=PRIORIDAD, initial=1, required=True, label=u'Prioridad', widget=forms.Select({'col': '6', 'class': 'select2'}))
    tiporequerimiento = forms.ChoiceField(choices=TIPO_REQUERIMIENTO_AUTOMATIZA, initial=1, required=True, label=u'Tipo', widget=forms.Select({'col': '6', 'class': 'select2'}))
    responsable = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True, ), required=True, label=u'Responsable que emite el requerimiento', widget=forms.Select(attrs={'col': '12'}))
    # orden = forms.IntegerField(label=u"Orden", initial=1, widget=forms.TextInput(attrs={'input_number':True, 'decimal': '0', 'col': '4'}), required=True)
    procedimiento = forms.CharField(required=True, label=u'Título', widget=forms.TextInput(attrs={'col': '12'}))
    detalle = forms.CharField(required=True, label=u'Detalle', widget=forms.Textarea(attrs={'col': '12', 'separator3': True}))

    def filtro_gestion(self, iddepartamento):
        self.fields['gestion'].queryset = SeccionDepartamento.objects.filter(status=True, departamento_id__in=iddepartamento).distinct()

    # def validador(self, periodo=0, id=0):
    #     ban, orden = True, self.cleaned_data['orden']
    #     req = RequerimientoPlanificacionAutomatiza.objects.filter(status=True, orden=orden, periodo_id=periodo).exclude(id=id).exists()
    #     if req:
    #         self.add_error('orden', 'Campo orden ya esta asignado a otro registro.')
    #         ban = False
    #     return ban


class RequerimientoPlanificacionGestorForm(FormModeloBase):
    departamento = forms.ModelChoiceField(Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), label=u"Dirección",
                                          widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    gestion = forms.ModelChoiceField(SeccionDepartamento.objects.select_related().filter(status=True, departamento__integrantes__isnull=False).distinct(), label=u"Gestión",
                                     widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    prioridad = forms.ChoiceField(choices=PRIORIDAD, initial=1, required=True, label=u'Prioridad', widget=forms.Select({'col': '3', 'class': 'select2'}))
    responsable = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True, ), required=True, label=u'Responsable',
                                         widget=forms.Select(attrs={'col': '9', 'class': 'select2'}))
    # orden = forms.IntegerField(label=u"Orden", initial=1, widget=forms.TextInput(attrs={'input_number': True, 'decimal': '0', 'col': '3'}), required=True)
    procedimiento = forms.CharField(required=True, label=u'Título', widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Describa el título de del requerimiento...'}))
    detalle = forms.CharField(required=True, label=u'Detalle', widget=forms.Textarea(attrs={'col': '12', 'placeholder': 'Describa a detalle lo que se requiere...'}))

    def filtro_gestion(self, iddepartamento):
        self.fields['gestion'].queryset = SeccionDepartamento.objects.filter(status=True, departamento_id=iddepartamento).distinct()

    # def validador(self, periodo=0, id=0):
    #     ban, orden = True, self.cleaned_data['orden']
    #     req = RequerimientoPlanificacionAutomatiza.objects.filter(status=True, orden=orden, periodo_id=periodo).exclude(id=id).exists()
    #     if req:
    #         self.add_error('orden', 'Campo orden ya esta asignado a otro registro.')
    #         ban = False
    #     return ban


class RequerimientoPlanificacionAForm(FormModeloBase):
    gestion = forms.ModelChoiceField(SeccionDepartamento.objects.filter(status=True, departamento__integrantes__isnull=False).distinct(), label=u"Gestión", widget=forms.Select(attrs={'col': '8'}))
    prioridad = forms.ChoiceField(choices=PRIORIDAD, initial=1, required=True, label=u'Prioridad', widget=forms.Select({'col': '4'}))
    responsable = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True, ), required=True, label=u'Responsable', widget=forms.Select(attrs={'col': '8'}))
    orden = forms.IntegerField(label=u"Orden", initial=1, widget=forms.TextInput(attrs={'class': 'imp-number', 'number': 'True', 'decimal': '0', 'controlwidth': '200px', 'col': '4'}), required=True)
    procedimiento = forms.CharField(required=False, label=u'Procedimiento', widget=forms.TextInput(attrs={'col': '12'}))
    detalle = forms.CharField(required=False, label=u'Detalle', widget=forms.Textarea(attrs={'col': '12', 'separator3': True}))

    def filtro_gestion(self, iddepartamento):
        self.fields['gestion'].queryset = SeccionDepartamento.objects.filter(status=True, departamento_id=iddepartamento).distinct()

    def validador(self, periodo=0, id=0):
        ban, orden = True, self.cleaned_data['orden']
        req = RequerimientoPlanificacionAutomatiza.objects.filter(status=True, orden=orden, periodo_id=periodo).exclude(id=id).exists()
        if req:
            self.add_error('orden', 'Campo orden ya esta asignado a otro registro.')
            ban = False
        return ban
