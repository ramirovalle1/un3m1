from core.custom_forms import FormModeloBase
from django import forms

from faceid.models import PersonaMarcada
from sagest.models import RegimenLaboral, Departamento, SeccionDepartamento, DenominacionPuesto
from sga.models import Persona

class ImportarFuncionariosForm(FormModeloBase):
    regimen = forms.ModelChoiceField(label=u'Regimen laboral',
                                   queryset=RegimenLaboral.objects.filter(status=True),
                                   required=True, widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-ui-radios-grid'}))
    departamento = forms.ModelChoiceField(label=u'Departamento',
                                    queryset=Departamento.objects.filter(status=True),
                                    required=False, widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-patch-exclamation', 'api':'true'}))
    cargos = forms.ModelMultipleChoiceField(label=u'Cargos', required=False,
                                           queryset=DenominacionPuesto.objects.filter(status=True),
                                           widget=forms.SelectMultiple({'col': '12', 'class': 'select2', 'icon': 'bi bi-briefcase'}))


class PersonaMarcadaForm(FormModeloBase):
    persona = forms.ModelChoiceField(label=u'Persona', required=True,
                                     queryset=Persona.objects.filter(status=True),
                                     widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-user', 'api':'true'}))
    # departamento = forms.ModelChoiceField(label=u'Departamento',
    #                                       queryset=Departamento.objects.filter(status=True),
    #                                       required=False, widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-patch-exclamation', 'api': 'true'}))
    activo = forms.BooleanField(label=u'Activo?', required=False,initial=True,
                                widget=forms.CheckboxInput({'col':'6', 'data-switchery': True}))
    externo = forms.BooleanField(label=u'¿Marcar externamente?', required=False,
                                widget=forms.CheckboxInput({'col': '6', 'data-switchery': True}))
    solo_pc = forms.BooleanField(label=u'¿Marcar solo en ordenador?', required=False, initial=True,
                                widget=forms.CheckboxInput({'col': '6', 'data-switchery': True}))

    def clean(self):
        cleaned_data = super().clean()
        persona = cleaned_data.get('persona')
        instancia = self.instancia
        id = instancia.id if instancia else 0
        persona_marcada = PersonaMarcada.objects.filter(status=True, persona=persona).exclude(id=id)
        if persona_marcada:
            self.add_error('persona', 'Persona que intenta agregar ya se encuentra registrado.')
        return cleaned_data


