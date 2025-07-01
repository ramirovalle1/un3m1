from django import forms

from feria.models import CronogramaFeria
from sga.models import Carrera, Profesor


class CronogramaForm(forms.Form):
    objetivo = forms.CharField(max_length=100, label=u'Nombre', required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Inicio", required=True, input_formats=['%d-%m-%Y'], widget=forms.widgets.DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "separator2": True, "separatortitle": "Fecha del periodo académico", "formwidth": "span6"}))
    fechafin = forms.DateField(label=u"Fin", required=True, input_formats=['%d-%m-%Y'], widget=forms.widgets.DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span6"}))
    fechainicioinscripcion = forms.DateField(label=u"Inicio Inscripción", required=True, input_formats=['%d-%m-%Y'], widget=forms.widgets.DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "separator2": True, "separatortitle": "Fecha del periodo académico", "formwidth": "span6"}))
    fechafininscripcion = forms.DateField(label=u"Fin Inscripción", required=True, input_formats=['%d-%m-%Y'], widget=forms.widgets.DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span6"}))
    minparticipantes = forms.IntegerField(label=u"Min. Participantes", required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "text-align: center;", 'decimal': '0', 'formwidth': 'span6'}))
    maxparticipantes = forms.IntegerField(label=u"Max. Participantes", required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "text-align: center;", 'decimal': '0', 'formwidth': 'span6'}))
    #carreras = forms.ModelMultipleChoiceField(label=u'Coordinaciones', required=False, queryset=Carrera.objects.filter(status=True), widget=forms.SelectMultiple(attrs={'formwidth': 'span8'}), help_text=u'Carreras que se consideraran para el ingreso a la feria')

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class SolicitudFeriaForm(forms.Form):
    cronograma = forms.ModelChoiceField(label=u"Cronograma Feria", queryset=CronogramaFeria.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-75'}))
    tutor = forms.ModelChoiceField(label=u"Cronograma Feria", queryset=Profesor.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-75'}))
    titulo = forms.CharField(label=u"Titulo", widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    resumen = forms.CharField(label=u"Resumen", widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    objetivogeneral = forms.CharField(label=u"Objetivo General", widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    objetivoespecifico = forms.CharField(label=u"Objetivos Especificos", widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    materiales = forms.CharField(label=u"Materiales", widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    resultados = forms.CharField(label=u"Resultados", widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    estado = forms.BooleanField(initial=True, label=u"Estado", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))

    #carreras = forms.ModelMultipleChoiceField(label=u'Coordinaciones', required=False, queryset=Carrera.objects.filter(status=True), widget=forms.SelectMultiple(attrs={'formwidth': 'span8'}), help_text=u'Carreras que se consideraran para el ingreso a la feria')

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True
