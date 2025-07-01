from datetime import datetime, timedelta

from core.custom_forms import FormModeloBase
from django import forms
from django.forms import DateTimeInput

from investigacion.models import ProyectoInvestigacion
from sga.models import Periodo
from vincula.models import ESTADO_SOLICITUD_DOCENTE


class ActividadAyudantiaForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', required=True, widget=forms.Textarea(attrs={'separator2': True}))

class PeriodoInvestigacionForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', required=True, widget=forms.TextInput(attrs={'placeholder': 'Ejem. Primer periodo de apertura', 'col': '6'}))
    periodolectivo = forms.ModelChoiceField( queryset=Periodo.objects.filter(status=True, fin__gte=datetime.now().date()).exclude(tipo_id__in=[1,3]), required=True, label=u'Periodo lectivo', widget=forms.Select({'col': '6'}))
    finicio = forms.DateField(label=u"Fecha Inicio", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    ffin = forms.DateField(label=u"Fecha Finaliza", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    freceptarsolicitud = forms.DateField(label=u"Fecha limite para receptar solicitudes", widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    fregistroactividad = forms.DateField(label=u"Fecha límite para registrar actividades", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    descripcion = forms.CharField(label=u'Motivo', required=False, widget=forms.Textarea(attrs={'placeholder': 'Describir el motivo de apertura...','rows': '3'}))
    publico = forms.BooleanField(initial=False, required=False, label=u'¿Publicar?', widget=forms.CheckboxInput(attrs={'data-switchery': 'true'}))

class SolicitudDocenteForm(FormModeloBase):
    proyecto = forms.ModelChoiceField( queryset=ProyectoInvestigacion.objects.filter(status=True, aprobado=1), required=True, label=u'Proyecto de investigación', widget=forms.Select({'col': '9'}))
    cantidad = forms.IntegerField(label=u'Cantidad de ayudantes', initial=1, required=True, widget=forms.TextInput(attrs={'class': 'input-number', 'number': 'True', 'decimal': '0', 'col': '3', 'controlwidth': '150px'}))
    mensaje = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea(attrs={'placeholder': 'Describir el motivo por el cual requiere ayudantes...','rows': '3'}))

    def get_fields(self, idpersona):
        self.fields['proyecto'].queryset=ProyectoInvestigacion.objects.filter(status=True, aprobado=1, profesor__persona=idpersona)



class GestionarSolicitudForm(FormModeloBase):
    estado = forms.ChoiceField(label=u"Estado", choices=((1, u'Aprobado'), (2, u'Rechazado')), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    observacion = forms.CharField(label=u"Observación", max_length=550, widget=forms.Textarea(attrs={'class': 'imp-50', 'cols':'40', 'rows': '4'}))