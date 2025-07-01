from datetime import datetime

from django import forms
from django.forms import DateTimeInput, TimeInput

from bd.forms import deshabilitar_campo
from core.custom_forms import FormModeloBase
from empleo.models import NIVEL_INSTRUCCION, MODALIDAD, DEDICACION, JORNADA, GENERO, TIEMPO, POSTULANTE, TIPO_SOLICITUD, OPCION_OBSERVACION_HOJAVIDA, OPCION_OBSERVACION_CONTRATO
from empresa.models import CargoEmpresa, RepresentantesEmpresa
from sagest.models import TipoContrato
from sga.forms import ExtFileField
from sga.models import Idioma, Asignatura, AsignaturaMalla,Persona,Inscripcion

class PeriodoForm(FormModeloBase):
    idioma = forms.ModelChoiceField(label=u"Idioma", queryset=Idioma.objects.filter(status=True), required=True,
                                            widget=forms.Select(attrs={'class': 'select ', 'col': '12'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    fecinicioinscripcion = forms.DateField(label=u"Fecha inicio de inscripción", initial=datetime.now().date(),
                           widget=DateTimeInput(format='%d-%m-%Y',
                                                attrs={'col': '6'}),
                           required=True)
    fecfininscripcion = forms.DateField(label=u"Fecha fin de inscripción", initial=datetime.now().date(),
                           widget=DateTimeInput(format='%d-%m-%Y',
                                                attrs={'col': '6'}),
                           required=True)
    estado = forms.BooleanField(label=u'Activo', required=False, initial=True,
                                       widget=forms.CheckboxInput(attrs={'formwidth': '100%', 'col': '6'}))


class GrupoForm(FormModeloBase):
    grupo = forms.CharField(label=u'Grupo', max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '8'}))
    cursomoodle = forms.IntegerField(label=u'Curso de Moodle', widget=forms.TextInput(attrs={'class': 'form-control', 'col': '4'}))
    fecinicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(),
                           widget=DateTimeInput(format='%d-%m-%Y',
                                                attrs={'col': '6'}),
                           required=True)
    horainicio = forms.TimeField(label=u"Hora inicio", initial=datetime.now().time().strftime('%H:%M'),
                           widget=TimeInput(format='%H:%M', attrs={'col': '6'}),
                           required=True)
    fecfin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(),
                                widget=DateTimeInput(format='%d-%m-%Y',
                                                     attrs={'col': '6'}),
                                required=True)
    horafin = forms.TimeField(label=u"Hora fin", initial=datetime.now().time().strftime('%H:%M'),
                                 widget=TimeInput(format='%H:%M',
                                                      attrs={'col': '6'}),
                                 required=True)
    cupo = forms.IntegerField(label=u'Cupo', widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6'}), required=True)
    orden = forms.IntegerField(label=u'Orden',
                              widget=TimeInput(attrs={'col': '6'}), required= True)


class PeriodoAsignaturaForm(FormModeloBase):
    asignatura = forms.ModelChoiceField(label=u"Asignatura",
                                        queryset=Asignatura.objects.filter(status=True, asignaturamalla__malla_id = 353).order_by('id'),
                                        widget=forms.Select(attrs={'col': '12'}))

class InscripcionAlumno(FormModeloBase):
    inscripcion = forms.ModelChoiceField(label=u"Estudiante", queryset=Inscripcion.objects.select_related().filter(status=True, activo=True), widget=forms.Select(attrs={'col': '12'}))
