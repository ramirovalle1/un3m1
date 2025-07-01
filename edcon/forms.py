from datetime import datetime, timedelta
from django import forms
from django.forms import ValidationError, DateTimeInput

from edcon.models import Requisito, TipoAnteproyecto, ComponenteAprendizaje, ConfigTipoAnteproyectoRequisito, ConfigTipoAnteComponenteApre, Modalidad, SolicitudAnteproyecto
from core.custom_forms import FormModeloBase
from sagest.models import Departamento
from sga.forms import ExtFileField
from edcon.models import TIPO_CERTIFICADO


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

class TipoAnteproyectoForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=100, required=True, widget=forms.TextInput({'placeholder': 'Ejem. CURSO'}))

    def validador(self, id=0):
        ban, descripcion = True, self.cleaned_data['descripcion'].upper()
        if TipoAnteproyecto.objects.filter(descripcion=descripcion, status=True).exclude(id=id).exists():
            self.add_error('descripcion', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban


class RequisitoForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=100, required=True,
                                  widget=forms.TextInput({'placeholder': 'Ejem. Ser docente y contar con experiencia profesional'}))

    def validador(self, id=0):
        ban, descripcion = True, self.cleaned_data['descripcion'].upper()
        if Requisito.objects.filter(descripcion=descripcion, status=True).exclude(id=id).exists():
            self.add_error('descripcion', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban


class ComponenteAprendizajeForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=500, required=True,
                                  widget=forms.TextInput({'placeholder': 'Ejem. Aprendizaje en contacto con el docente (CD)'}))

    def validador(self, id=0):
        ban, descripcion = True, self.cleaned_data['descripcion'].upper()
        if ComponenteAprendizaje.objects.filter(descripcion=descripcion, status=True).exclude(id=id).exists():
            self.add_error('descripcion', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban


class ConfigTipoAnteproyectoRequisitoForm(FormModeloBase):
    tipoanteproyecto = forms.ModelChoiceField(queryset=TipoAnteproyecto.objects.filter(status=True), required=True, label=u'Tipo anteproyecto', widget=forms.Select({'col':'8'}))
    requisitos = forms.ModelMultipleChoiceField(label=u'Requisitos', queryset=Requisito.objects.filter(status=True), required=True, widget=forms.SelectMultiple(attrs={'formwidth': '100%', 'col': '12', 'rows': '3'}))
    vigente = forms.BooleanField(initial=False, required=False, label=u'Vigente', widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'4'}))

    # Si ésta configuración está en uso, sólo permitir editar el campo vigente
    # def editar(self):
    #     campo_modobloqueo(self, 'tipoanteproyecto', True)
    #     self.fields['tipoanteproyecto'].required = False
    #     deshabilitar_campo(self, 'requisitos')

    def validador(self, id=0):
        ban, tipoanteproyecto, requisitos, vigente = True, self.cleaned_data['tipoanteproyecto'], self.cleaned_data['requisitos'], self.cleaned_data['vigente']
        # Validar que NO permita registros repetidos con el mismo tipo de anteproyecto y requisitos
        config_requisitos = ConfigTipoAnteproyectoRequisito.objects.filter(tipoanteproyecto=tipoanteproyecto,
                                             requisitos__in=requisitos.values_list('id', flat=True), status=True).exclude(id=id).distinct()
        if config_requisitos:
            for config_requisito in config_requisitos:
                if list(config_requisito.requisitos.all().values_list('id', flat=True)) == list(requisitos.values_list('id', flat=True)):
                    self.add_error('tipoanteproyecto', 'Registro que desea ingresar ya existe.')
                    self.add_error('requisitos', 'Registro que desea ingresar ya existe.')
                    return False
        # # Validar que por cada tipo de anteproyecto haya una configuracion vigente.
        # if not vigente:
        #     # Guardar y editar
        #     if not ConfigTipoAnteproyectoRequisito.objects.filter(status=True, tipoanteproyecto=tipoanteproyecto, vigente=True).exclude(id=id).distinct():
        #         self.add_error('vigente', f'Debe haber una configuración vigente por cada tipo de anteproyecto.')
        #         ban = False
        return ban

class ConfigTipoAnteComponenteApreForm(FormModeloBase):
    tipoanteproyecto = forms.ModelChoiceField(queryset=TipoAnteproyecto.objects.filter(status=True), required=True, label=u'Tipo anteproyecto', widget=forms.Select({'col': '10'}))
    componentesaprendizajes = forms.ModelMultipleChoiceField(label=u'Componente aprendizaje', queryset=ComponenteAprendizaje.objects.filter(status=True), required=True, widget=forms.SelectMultiple(attrs={'formwidth': '100%', 'col': '12', 'rows': '2'}))
    vigente = forms.BooleanField(initial=False, required=False, label=u'Vigente', widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'2'}))

    def validador(self, id=0):
        ban, tipoanteproyecto, componentesaprendizajes, vigente = True, self.cleaned_data['tipoanteproyecto'], self.cleaned_data['componentesaprendizajes'], self.cleaned_data['vigente']
        # Validar que permita registros repetidos con el mismo tipo de anteproyecto y componentes
        config_componentes = ConfigTipoAnteComponenteApre.objects.filter(tipoanteproyecto=tipoanteproyecto,
                                                                           componentesaprendizajes__in=componentesaprendizajes.values_list('id',
                                                                           flat=True), status=True).exclude(id=id).distinct()
        if config_componentes:
            for config_componente in config_componentes:
                if list(config_componente.componentesaprendizajes.all().values_list('id', flat=True)) == list(
                        componentesaprendizajes.values_list('id', flat=True)):
                    self.add_error('tipoanteproyecto', 'Registro que desea ingresar ya existe.')
                    self.add_error('componentesaprendizajes', 'Registro que desea ingresar ya existe.')
                    return False
        # # Validar que por cada tipo de anteproyecto haya una configuracion vigente.
        # if not vigente:
        #     # Guardar y editar
        #     if not ConfigTipoAnteComponenteApre.objects.filter(status=True, tipoanteproyecto=tipoanteproyecto,
        #                                                           vigente=True).exclude(id=id).distinct():
        #         self.add_error('vigente', f'Debe haber una configuración vigente por cada tipo de anteproyecto.')
        #         ban = False
        return ban

class SolicitudAnteproyectoForm(FormModeloBase):
    tipoanteproyecto = forms.ModelChoiceField(queryset=TipoAnteproyecto.objects.filter(status=True), required=True, label=u'Tipo anteproyecto', widget=forms.Select({'col': '12'}), help_text=u'Sólo se muestran los tipos de anteproyectos configurados.')
    tema = forms.CharField(label=u'Tema', max_length=500, required=True, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))
    introduccion = forms.CharField(label=u"Introducción", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    metodologia = forms.CharField(label=u"Metodología", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    estudiopertinencia = forms.CharField(label=u"Estudio de pertinencia", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    problemasoluciona = forms.CharField(label=u"Problema soluciona", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    objetivogeneral = forms.CharField(label=u"Objetivo general", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    objetivoespecifico = forms.CharField(label=u"objetivo específico", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    dirigidoa = forms.CharField(label=u"Dirigido a", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    contenido = forms.CharField(label=u"Contenido", required=True, widget=forms.Textarea(attrs={'col': '12','separator3': True}))
    duracion = forms.CharField(label=u'Duración', required=True, max_length=500, widget=forms.TextInput(attrs={'col': '12'}))
    # fechainicio = forms.DateField(label=u"Fecha inicio", required=True, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    # fechafin = forms.DateField(label=u"Fecha fin", required=True, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    horario = forms.CharField(label=u"Horario", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    considerarhorasautonomas = forms.BooleanField(initial=False, label=u'¿Desea contabilizar las horas de trabajo autónomo, para la totalidad de horas del curso?', required=False, widget=forms.CheckboxInput(attrs={'col': '12'}))
    modalidad = forms.ModelChoiceField(queryset=Modalidad.objects.filter(status=True), required=True, label=u'Modalidad', widget=forms.Select({'col': '12'}))
    tipocertificado = forms.ChoiceField(label=u"Tipo certificado", initial=1, choices=TIPO_CERTIFICADO, required=True, widget=forms.Select({'placeholder': 'Seleccione el tipo de certificado', 'col': '12'}))
    conclusion = forms.CharField(label=u"Conclusión", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    recomendacion = forms.CharField(label=u"Recomendación", required=True, widget=forms.Textarea(attrs={'col': '12'}))
    # observacion = forms.CharField(label=u'Observación', max_length=500, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))

    # Cargar sólo los tipos de anteproyectos configurados o vigentes
    def cargartipoanteproyecto_vig(self):
        tiposanteproyecto_vig = []
        for tipoanteproyecto in TipoAnteproyecto.objects.filter(status=True):
            if tipoanteproyecto.configtipoanteproyectorequisito_set.filter(status=True, vigente=True) and tipoanteproyecto.configtipoantecomponenteapre_set.filter(status=True, vigente=True):
                tiposanteproyecto_vig.append(tipoanteproyecto.id)
        self.fields['tipoanteproyecto'].queryset = TipoAnteproyecto.objects.filter(status=True, id__in=tiposanteproyecto_vig)

    def validador(self, id=0, persona=None):
        ban = True
        # fechaagendada, horainicio = self.cleaned_data['fechaagendada'], self.cleaned_data['horainicio']
        #
        # if self.cleaned_data['fechaagendada'] < datetime.now().date():
        #     self.add_error('fechaagendada', 'La fecha a agendar debe ser igual o posterior a la fecha actual.')
        #     ban = False

        # # Validar que no se repita el registro en la misma fecha agendada e igual a hora de inicio (sólo igual, no mayor)
        # if SolicitudAnteproyecto.objects.filter(status=True, persona=persona, fechaagendada=fechaagendada, horainicio=horainicio).exclude(id=id).exists():
        #     self.add_error('fechaagendada', 'Registro con la fecha agendada que desea ingresar ya existe.')
        #     self.add_error('horainicio', 'Registro con la hora inicio que desea ingresar ya existe.')
        #     ban = False

        # if not Convocatoria.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].strip().upper()).exists():

        # if f.cleaned_data['finpos'] <= f.cleaned_data['iniciopos']:
        #     return JsonResponse({"result": "bad", "titulo": "Atención!!!",
        #                          "mensaje": u"La fecha de fin de postulación debe ser mayor a la fecha de inicio de postulación ",
        #                          "showSwal": "True", "swalType": "warning"})

        return ban

    # def editar(self, ponencia):
    #     self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=ponencia.areaconocimiento).order_by('nombre')
    #     self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=ponencia.subareaconocimiento).order_by('nombre')
    #     self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=ponencia.lineainvestigacion).order_by('nombre')
    #     if ponencia.provieneproyecto:
    #         if ponencia.tipoproyecto < 3:
    #             self.fields['proyectointerno'].queryset = ProyectosInvestigacion.objects.filter(status=True, tipo=ponencia.tipoproyecto).order_by('nombre')
    #         else:
    #             self.fields['proyectoexterno'].queryset = ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre')
