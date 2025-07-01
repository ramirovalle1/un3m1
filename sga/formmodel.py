from fileinput import FileInput
from django import forms
from django.contrib.auth.models import Permission
from sga.models import AgendaPracticasTutoria, PracticasPreprofesionalesInscripcion, EstudiantesAgendaPracticasTutoria, Turno, HorarioTutoriaPacticasPP
from django.utils.safestring import mark_safe
from django.forms.widgets import DateTimeBaseInput

from voto.models import GremioPeriodo, ListaElectoral, ListaGremio


class CustomDateInput(DateTimeBaseInput):
    def format_value(self, value):
        return str(value or '')


class FormError(Exception):
    def __init__(self, form):
        super().__init__("Error en el formulario")
        if isinstance(form, list) or isinstance(form, tuple):
            self.errors = []
            for x in form:
                for k, v in x.errors.items():
                    self.errors.append({k: v[0]})
        else:
            self.errors = [{k: v[0]} for k, v in form.errors.items()]
        self.dict_error = {
            'error': True,
            "form": self.errors,
            "message": "Los datos enviados son inconsistentes"
        }


class ModeloBaseFormularios(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.ver = kwargs.pop('ver') if 'ver' in kwargs else False
        self.editando = 'instance' in kwargs
        super(ModeloBaseFormularios, self).__init__(*args, **kwargs)
        Modelo = self.Meta.model
        nombre_app, nombre_model = Modelo._meta.app_label, Modelo._meta.model_name
        for k, v in self.fields.items():
            field = self.fields[k]
            if isinstance(field, forms.TimeField):
                self.fields[k].widget = CustomDateInput(attrs={'type': 'time'})
            if isinstance(field, forms.DateField):
                self.fields[k].widget = CustomDateInput(attrs={'type': 'date'})
            elif isinstance(field, forms.BooleanField):
                self.fields[k].widget.attrs['class'] = "js-switch"
                self.fields[k].widget.attrs['data-render'] = "switchery"
                self.fields[k].widget.attrs['data-theme'] = "default"
            else:
                self.fields[k].widget.attrs['class'] = "form-control"
            # if self.fields[k].required and self.fields[k].label:
            #     self.fields[k].label = mark_safe(
            #         self.fields[k].label + '<span style="color:red;margin-left:2px;"><strong>*</strong></span>')
            self.fields[k].widget.attrs['data-nameinput'] = k
            if self.ver:
                self.fields[k].widget.attrs['readonly'] = "readonly"


class AgendaPracticasTutoriaForm(ModeloBaseFormularios):
    estudiantes = forms.ModelMultipleChoiceField(queryset=PracticasPreprofesionalesInscripcion.objects.filter(status=True), label="Estudiantes")
    # turno = forms.ModelMultipleChoiceField(queryset=Turno.objects.filter(status=True), label='Turno')
    class Meta:
        model = AgendaPracticasTutoria
        fields = ('asunto', 'fecha', 'turno', 'hora_inicio', 'hora_fin', 'observacion', 'url_reunion', 'estudiantes')

    def __init__(self, *args, **kwargs):
        ver = kwargs.pop('ver') if 'ver' in kwargs else False
        instancia = kwargs["instance"] if 'instance' in kwargs else None
        periodo = kwargs.pop('periodo') if 'periodo' in kwargs else None
        super(AgendaPracticasTutoriaForm, self).__init__(*args, **kwargs)
        for k, v in self.fields.items():
            self.fields[k].widget.attrs['class'] = "form-control"
            self.fields[k].widget.attrs['required'] = "true"
            self.fields[k].label = mark_safe(self.fields[k].label + '<span style="color:red;margin-left:2px;"><strong>*</strong></span>')
            if k in ('estudiantes', 'turno', ):
                self.fields[k].widget.attrs['class'] = "form-control select2"
            if k in ('hora_inicio', 'hora_fin'):
                self.fields[k].widget.attrs['formwidth'] = "50%"
                self.fields[k].widget.attrs['required'] = "false"
            if k in ('observacion', 'url_reunion'):
                self.fields[k].widget.attrs['rows'] = "3"
            if ver:
                self.fields[k].widget.attrs['class'] = "form-control"
                self.fields[k].widget.attrs['disabled'] = True
        if instancia:
            agenda = AgendaPracticasTutoria.objects.get(pk=self.instance.id)
            estudiantes = EstudiantesAgendaPracticasTutoria.objects.filter(status=True,  cab=agenda).values_list('estudiante_id',flat=True)
            self.initial['estudiantes'] = PracticasPreprofesionalesInscripcion.objects.filter(status=True, pk__in=estudiantes)
            # horariosturno = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=self.instance.docente, periodo=periodo, dia=self.instance.fecha.weekday() + 1).values_list('turno_id', flat=True)
            # self.initial['turno'] = Turno.objects.filter(status=True, id__in=horariosturno)
            if instancia.turno:
                del self.fields['hora_inicio']
                del self.fields['hora_fin']
            #     # form.fields['turno'].initial = Turno.objects.get(id=instancia.turno)
            #     form.fields['turno'].queryset = Turno.objects.filter(id__in=horariosturno)
            else:
                del self.fields['turno']
            # form.fields['turno'].queryset = Turno.objects.filter(id__in=horariosturno)


class ReAgendarAgendaPracticasTutoriasForm(ModeloBaseFormularios):

    class Meta:
        model = AgendaPracticasTutoria
        fields = ('fecha', 'hora_inicio', 'hora_fin',)

    def __init__(self, *args, **kwargs):
        ver = kwargs.pop('ver') if 'ver' in kwargs else False
        instancia = kwargs["instance"] if 'instance' in kwargs else None
        super(ReAgendarAgendaPracticasTutoriasForm, self).__init__(*args, **kwargs)
        for k, v in self.fields.items():
            self.fields[k].widget.attrs['class'] = "form-control"
            self.fields[k].widget.attrs['required'] = "true"
            if not k in ('fecha', 'hora_inicio', 'hora_fin', ):
                self.fields[k].label = mark_safe(self.fields[k].label + '<span style="color:red;margin-left:2px;"><strong>*</strong></span>')
            if ver:
                self.fields[k].widget.attrs['class'] = "form-control"
                self.fields[k].widget.attrs['readonly'] = 'readonly'
                self.fields[k].widget.attrs['disabled'] = 'true'


class FinalizarAgendaTutoriaForm(ModeloBaseFormularios):

    class Meta:
        model = AgendaPracticasTutoria
        fields = ('conclusion',)

    def __init__(self, *args, **kwargs):
        ver = kwargs.pop('ver') if 'ver' in kwargs else False
        instancia = kwargs["instance"] if 'instance' in kwargs else None
        super(FinalizarAgendaTutoriaForm, self).__init__(*args, **kwargs)
        for k, v in self.fields.items():
            self.fields[k].widget.attrs['class'] = "form-control"
            self.fields[k].widget.attrs['required'] = "true"
            self.fields[k].label = mark_safe(self.fields[k].label + '<span style="color:red;margin-left:2px;"><strong>*</strong></span>')
            if k in ('conclusion'):
                self.fields[k].widget.attrs['rows'] = "2"
            if ver:
                self.fields[k].widget.attrs['class'] = "form-control"
                self.fields[k].widget.attrs['readonly'] = 'readonly'
                self.fields[k].widget.attrs['disabled'] = 'true'


class GremioPeriodoForm(ModeloBaseFormularios):
    listas = forms.ModelMultipleChoiceField(queryset=ListaElectoral.objects.filter(status=True), label="Listas")

    class Meta:
        model = GremioPeriodo
        fields = ('gremio', 'tipo', 'coordinacion')

    def __init__(self, *args, **kwargs):
        ver = kwargs.pop('ver') if 'ver' in kwargs else False
        instancia = kwargs["instance"] if 'instance' in kwargs else None
        super(GremioPeriodoForm, self).__init__(*args, **kwargs)
        for k, v in self.fields.items():
            self.fields[k].widget.attrs['class'] = "form-control"
            if not k in ('coordinacion',):
                self.fields[k].widget.attrs['required'] = "true"
                self.fields[k].label = mark_safe(self.fields[k].label + '<span style="color:red;margin-left:2px;"><strong>*</strong></span>')
            if k in ('coordinacion', 'gremio', 'tipo', 'listas'):
                self.fields[k].widget.attrs['class'] = "form-control select2combo"
            if k in ('gremio', 'tipo'):
                self.fields[k].widget.attrs['formwidth'] = "50%"
            if ver:
                self.fields[k].widget.attrs['class'] = "form-control"
                self.fields[k].widget.attrs['readonly'] = 'readonly'
        if instancia:
            gremio = GremioPeriodo.objects.get(pk=self.instance.id)
            listaids = ListaGremio.objects.filter(status=True,  gremio_periodo=gremio).values_list('lista__id',flat=True)
            self.initial['listas'] = ListaElectoral.objects.filter(status=True, pk__in=listaids)

