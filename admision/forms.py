from datetime import datetime, timedelta
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms import ValidationError
from django.db.models import Q
from django.forms import DateTimeInput
from django.forms.widgets import CheckboxInput, FileInput
# from landscape.lib.cloud import MAX_LENGTH
from django.utils.safestring import mark_safe
from admision.models import TestVocacionalOpcion


class PeriodoForm(forms.Form):
    from sga.models import Periodo
    periodo = forms.ModelChoiceField(queryset=Periodo.objects.none(), required=True, label=u'Periodo', widget=forms.Select(attrs={'class': 'form-select', 'col': '12'}), error_messages={'required': 'Por favor seleccione el periodo académico (requerido)'})
    nombre = forms.CharField(label=u'Nombre', max_length=200, help_text=u"", required=True, widget=forms.TextInput({'class': 'form-control', 'col': '12', 'placeholder': 'Describa el nombre del periodo...'}), error_messages={'required': 'Por favor ingrese una descripción (requerido)'})
    inicio = forms.DateField(label=u"Inicio", required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha form-control', "separatortitle": "Fecha del periodo académico", 'col': '4', 'pattern':"\d{4}-\d{2}-\d{2}"}), error_messages={'required': 'Por favor seleccione una fecha de inicio (requerido)'})
    fin = forms.DateField(label=u"Fin", required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha form-control', 'col': '4', 'pattern':"\d{4}-\d{2}-\d{2}"}), error_messages={'required': 'Por favor seleccione una fecha fin (requerido)'})
    activo = forms.BooleanField(label=u"Activo?", required=False, initial=True, widget=forms.CheckboxInput({'class': '', 'col': '4'}))

    def set_periodo(self, periodo):
        from sga.models import Periodo
        if periodo:
            self.fields['periodo'].queryset = Periodo.objects.filter(pk=periodo)
            self.fields['periodo'].initial = [periodo]

    def clean(self):
        cleaned_data = super(PeriodoForm, self).clean()
        inicio = cleaned_data.get('inicio', None)
        fin = cleaned_data.get('fin', None)
        if inicio and fin:
            if fin < inicio:
                self.add_error('fin', ValidationError('Campo de fecha fin debe ser mayor a fecha de inicio'))
        return cleaned_data


class TestVocacionalForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, help_text=u"", required=True, widget=forms.TextInput({'class': 'form-control', 'col': '12', 'placeholder': 'Describa el nombre del test vocacional...'}), error_messages={'required': 'Por favor ingrese un nombre para el test (requerido)'})
    descripcion = forms.CharField(label=u'Descripción', help_text=u"", required=True, widget=forms.Textarea({'rows': '5', 'class': 'form-control', 'col': '12', 'placeholder': 'Describa el nombre del periodo...'}), error_messages={'required': 'Por favor ingrese una descripción (requerido)'})
    activo = forms.BooleanField(label=u"Activo?", required=False, initial=True, widget=forms.CheckboxInput({'class': '', 'col': '12'}))

    def clean(self):
        cleaned_data = super(TestVocacionalForm, self).clean()
        return cleaned_data


class TestVocacionalOpcionForm(forms.Form):
    literal = forms.CharField(label=u'Literal', max_length=10, help_text=u"", required=True, widget=forms.TextInput({'class': 'form-control', 'col': '4', 'placeholder': 'Escriba el literal de la opción del test'}), error_messages={'required': 'Por favor ingrese un literal (requerido)'})
    descripcion = forms.CharField(label=u'Descripción', required=True, widget=forms.TextInput({'class': 'form-control', 'col': '6', 'placeholder': 'Escriba la descripción de la opción del test'}), error_messages={'required': 'Por favor ingrese una descripción (requerido)'})

    def clean(self):
        cleaned_data = super(TestVocacionalOpcionForm, self).clean()
        return cleaned_data


class TestVocacionalPreguntaForm(forms.Form):
    orden = forms.IntegerField(label=u'Orden', help_text=u"", required=True, widget=forms.TextInput({'class': 'form-control', 'col': '4', 'placeholder': '0...'}), error_messages={'required': 'Por favor ingrese un orden (requerido)'})
    activo = forms.BooleanField(label=u"Activo?", required=False, initial=True, widget=forms.CheckboxInput({'class': 'form-check-input', 'col': '4'}))
    validar = forms.BooleanField(label=u"Validar?", required=False, initial=True, widget=forms.CheckboxInput({'class': 'form-check-input', 'col': '4'}))
    descripcion = forms.CharField(label=u'Pregunta', required=True, widget=forms.Textarea({'rows': '5', 'class': 'form-control', 'col': '12', 'placeholder': 'Escriba la pregunta del test vocacional'}), error_messages={'required': 'Por favor ingrese una pregunta (requerido)'})

    def clean(self):
        cleaned_data = super(TestVocacionalPreguntaForm, self).clean()
        return cleaned_data


class TestVocacionalAlternativaForm(forms.Form):
    orden = forms.IntegerField(label=u'Orden', initial=0, help_text=u"", required=True, widget=forms.TextInput({'class': 'form-control', 'col': '12', 'placeholder': '0...'}), error_messages={'required': 'Por favor ingrese un orden (requerido)'})
    opcion = forms.ModelChoiceField(queryset=TestVocacionalOpcion.objects.none(), required=True, label=u'Opción', widget=forms.Select(attrs={'class': 'form-select', 'col': '12'}), error_messages={'required': 'Por favor seleccione la opción (requerido)'})
    valor = forms.FloatField(label=u'Valor', initial=0, help_text=u"", required=True, widget=forms.TextInput({'class': 'form-control', 'col': '12', 'placeholder': '0...'}), error_messages={'required': 'Por favor ingrese un valor (requerido)'})

    def set_opcion(self, test):
        self.fields['opcion'].queryset = TestVocacionalOpcion.objects.filter(test_id=test)
        self.fields['opcion'].initial = [test]

    def clean(self):
        cleaned_data = super(TestVocacionalAlternativaForm, self).clean()
        return cleaned_data


class RubricaForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.Textarea(),max_length=500)


class RubricaCriterioForm(forms.Form):
    orden = forms.IntegerField(label=u"Órden", min_value=1, widget=forms.NumberInput({"min":"1"}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(),max_length=500)


class RubricaNivelForm(forms.Form):
    calificacion = forms.FloatField(label=u"Calificación", min_value=0)
    descripcion = forms.CharField(label=u"Descripción del Nivel", widget=forms.Textarea(), max_length=500)