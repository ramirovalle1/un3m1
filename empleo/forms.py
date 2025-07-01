from datetime import datetime, timedelta
from django import forms
from django.db.models import Q
from django.forms.widgets import CheckboxInput, FileInput, DateTimeInput, TimeInput
from django.forms.widgets import DateTimeBaseInput
from inno.models import CampoAmplioPac, CampoEspecificoPac, CampoDetalladoPac, TitulacionPac, TIPO_ACADEMIA_NIVEL_FORMACION
from postulate.models import NIVEL_INSTRUCCION, MODALIDAD_PARTIDA, DEDICACION_PARTIDA, JORNADA_PARTIDA, Convocatoria, Partida, CARGOS_TRIBUNAL, FactorApelacion, CriterioApelacion, TIPO_TRIBUNAL,\
ModeloEvaluativoDisertacion
from sagest.models import TIPO_SOLICITUD_PUBLICACION, TipoContrato, ActividadLaboral, DenominacionPuesto
from sga.forms import ExtFileField
from sga.models import Pais, Provincia, Parroquia, Sexo, Canton, Raza, PersonaEstadoCivil, Discapacidad, \
    InstitucionBeca, Titulo, InstitucionEducacionSuperior, NivelTitulacion, GradoTitulacion, Idioma, NivelSuficencia, \
    InstitucionCertificadora, RevistaInvestigacion, ESTADO_PUBLICACION_ARTICULO, AreaConocimientoTitulacion, \
    SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, \
    LineaInvestigacion, SubLineaInvestigacion, TIPO_PROYECTO_ARTICULO, ProyectosInvestigacion, \
    ProyectoInvestigacionExterno, TIPO_REVISTA, BaseIndexadaInvestigacion, Carrera, Asignatura, TipoCurso, \
    TipoParticipacion, TipoCapacitacion, MODALIDAD_CAPACITACION, ContextoCapacitacion, DetalleContextoCapacitacion, \
    TipoCertificacion, TIPO_CAPACITACION_P, Persona, Inscripcion


class CustomDateInput(DateTimeBaseInput):
    def format_value(self, value):
        return str(value or '')


def deshabilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True
    form.fields[campo].widget.attrs['disabled'] = True


def habilitar_campo(form, campo):
    form.fields[campo].widget.attrs['readonly'] = False
    form.fields[campo].widget.attrs['disabled'] = False


def campo_solo_lectura(form, campo):
    form.fields[campo].widget.attrs['readonly'] = True


class PartidaForm(forms.Form):
    codpartida = forms.CharField(label=u'Codigo', max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    titulo = forms.CharField(label=u'Titulo', max_length=1000, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(label=u'Descripcion', max_length=1000, required=False, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none', 'class': 'form-control'}))
    campoamplio = forms.ModelMultipleChoiceField(label=u"Campo amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('codigo'), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    campoespecifico = forms.ModelMultipleChoiceField(label=u"Campo especifico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    campodetallado = forms.ModelMultipleChoiceField(label=u"Campo detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    carrera = forms.ModelChoiceField(label=u"Carreras", queryset=Carrera.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    asignatura = forms.ModelMultipleChoiceField(label=u"Asignaturas", queryset=Asignatura.objects.filter(status=True), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    titulos = forms.ModelMultipleChoiceField(label=u"Titulos", queryset=Titulo.objects.filter(status=True), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    nivel = forms.ChoiceField(label=u'Nivel', choices=NIVEL_INSTRUCCION, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    modalidad = forms.ChoiceField(label=u'Modalidad', choices=MODALIDAD_PARTIDA, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    dedicacion = forms.ChoiceField(label=u'Dedicacion', choices=DEDICACION_PARTIDA, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    jornada = forms.ChoiceField(label=u'Jornada', choices=JORNADA_PARTIDA, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    rmu = forms.FloatField(initial='', label=u'RMU', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'decimal': '2', 'placeholder': '0.00'}))
    vigente = forms.BooleanField(label=u"Vigente?", required=False, widget=forms.CheckboxInput())

    def editar(self, partidaasignatura, partida):
        self.fields['asignatura'].queryset = Asignatura.objects.filter(id__in=partidaasignatura)
        self.fields['titulos'].queryset = partida.titulos.all()


class ConvocatoriaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripcion', max_length=100, required=True, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none', 'class': 'form-control'}))
    fechainicio = forms.DateField(label=u"Inicio", required=True, widget=DateTimeInput(attrs={'class': 'form-control', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fin", required=True, widget=DateTimeInput(attrs={'class': 'form-control', 'formwidth': '50%'}))
    tipocontrato = forms.ModelChoiceField(label=u"Tipo Contrato", queryset=TipoContrato.objects.filter(status=True).order_by('nombre'), required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    denominacionpuesto = forms.ModelChoiceField(label=u"Denominaciòn de Puesto", queryset=DenominacionPuesto.objects.filter(status=True).order_by('descripcion'), required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    modeloevaluativo = forms.ModelChoiceField(label=u"Modelo Evaluativo", queryset=ModeloEvaluativoDisertacion.objects.filter(status=True).order_by('descripcion'), required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    vigente = forms.BooleanField(label=u"Vigente?", required=False, widget=forms.CheckboxInput())
    valtercernivel = forms.IntegerField(initial=0, label=u'Valor Tercer Nivel', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '30%', 'separator2': True, 'separatortitle': 'Configuración Calificación'}))
    valposgrado = forms.IntegerField(initial=0, label=u'Valor Cuarto Nivel', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '30%'}))
    valdoctorado = forms.IntegerField(initial=0, label=u'Valor Doctorado Nivel', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '30%'}))
    valcapacitacionmin = forms.IntegerField(initial=0, label=u'Valor Minimo Capacitación', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '50%'}))
    valcapacitacionmax = forms.IntegerField(initial=0, label=u'Valor Máximo Capacitación', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '50%'}))
    valexpdocentemin = forms.IntegerField(initial=0, label=u'Valor Minimo Experiencia Docente', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '50%'}))
    valexpdocentemax = forms.IntegerField(initial=0, label=u'Valor Máximo Experiencia Docente', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '50%'}))
    valexpadminmin = forms.IntegerField(initial=0, label=u'Valor Minimo Experiencia Administrativo', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '50%'}))
    valexpadminmax = forms.IntegerField(initial=0, label=u'Valor Máximo Experiencia Administrativo', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', 'formwidth': '50%'}))


class ConvocatoriaTerminosForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripcion', max_length=1500, required=False, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none', 'class': 'form-control'}))


class PersonaForm(forms.Form):
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False,
                              widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-cedula form-control'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, required=False,
                                help_text=u'Nota: Para ingresar el pasaporte digite VS al inicio de la numeracion. Ejemplo:VSA092',
                                widget=forms.TextInput(attrs={'class': 'imp-cedula form-control'}))
    nacimiento = forms.DateField(label=u"Fecha nacimiento", required=False, input_formats=['%d-%m-%Y'],
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control'}))
    # paisnacimiento = forms.ModelChoiceField(label=u"País de nacimiento", queryset=Pais.objects.all(), required=False,
    #                                         widget=forms.Select(attrs={'class': 'imp-75'}))
    # provincianacimiento = forms.ModelChoiceField(label=u"Provincia de nacimiento",
    #                                              queryset=Provincia.objects.all().order_by('nombre'), required=False,
    #                                              widget=forms.Select(attrs={'class': 'imp-75'}))
    # cantonnacimiento = forms.ModelChoiceField(label=u"Cantón de nacimiento", queryset=Canton.objects.order_by('nombre'),
    #                                           required=False, widget=forms.Select(attrs={'class': 'imp-75'}))
    # parroquianacimiento = forms.ModelChoiceField(label=u"Parroquia del nacimiento",
    #                                              queryset=Parroquia.objects.all().order_by('nombre'), required=False,
    #                                              widget=forms.Select(attrs={'class': 'imp-75'}))
    # nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=False,
    #                                widget=forms.TextInput(attrs={'class': 'imp-75'}))
    sexo = forms.ModelChoiceField(label=u"Genero", queryset=Sexo.objects.all(),
                                  widget=forms.Select(attrs={'class': 'form-control'}))
    pais = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'class': 'form-control'}))
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia",
                                       queryset=Provincia.objects.all().order_by('nombre'), required=False,
                                       widget=forms.Select(attrs={'class': ' form-control'}))
    canton = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects.order_by('nombre'),
                                    required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia",
                                       queryset=Parroquia.objects.all().order_by('nombre'), required=False,
                                       widget=forms.Select(attrs={'class': 'form-control'}))
    sector = forms.CharField(label=u"Sector", max_length=100, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-50 form-control'}))
    direccion = forms.CharField(label=u"Calle principal", max_length=100, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-75 form-control'}))
    direccion2 = forms.CharField(label=u"Calle secundaria", max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-75 form-control'}))
    num_direccion = forms.CharField(label=u"Numero residencia", max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-number form-control'}))
    telefono = forms.CharField(label=u"Teléfono móvil", max_length=50, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-50 form-control'}))
    telefono_conv = forms.CharField(label=u"Teléfono fijo", max_length=50, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-50 form-control'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50 form-control'}))
    emailinst = forms.CharField(label=u"Correo institucional", max_length=200, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-50 form-control'}))
    # sangre = forms.ModelChoiceField(label=u"Tipo de sangre", queryset=TipoSangre.objects.all().order_by('sangre'),
    #                                 required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    etnia = forms.ModelChoiceField(label=u'Etnia', queryset=Raza.objects, required=False,
                                   widget=forms.Select(attrs={'class': 'imp-50 form-group form-check'}))
    lgtbi = forms.BooleanField(label=u"Pertenece al Grupo LGTBI?", required=False,
                               widget=forms.CheckboxInput())
    estadocivil = forms.ModelChoiceField(label=u'Estado civil', queryset=PersonaEstadoCivil.objects, required=False,
                                         widget=forms.Select(attrs={'class': 'imp-50'}))

    tienediscapacidad = forms.BooleanField(label=u'Tiene Discapacidad?', required=False, widget=CheckboxInput())

    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad",
                                              queryset=Discapacidad.objects.filter(status=True), required=False,
                                              widget=forms.Select())
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False,
                                             widget=forms.TextInput(attrs={'class': 'form-control'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet Discapacitado', max_length=50, required=False,
                                         widget=forms.TextInput(attrs={'class': 'form-control'}))
    archivo = ExtFileField(label=u'Carnet de Discapacidad', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304, widget=forms.FileInput())
    institucionvalida = forms.ModelChoiceField(label=u"Institución Valida",
                                               queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True),
                                               required=False, widget=forms.Select())

    def editar(self, persona):
        deshabilitar_campo(self, 'nombres')
        deshabilitar_campo(self, 'apellido1')
        deshabilitar_campo(self, 'apellido2')
        deshabilitar_campo(self, 'cedula')
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)
        # self.fields['provincianacimiento'].queryset = Provincia.objects.filter(pais=persona.paisnacimiento)
        # self.fields['cantonnacimiento'].queryset = Canton.objects.filter(provincia=persona.provincianacimiento)
        # self.fields['parroquianacimiento'].queryset = Parroquia.objects.filter(canton=persona.cantonnacimiento)

    def sin_pasaporte(self):
        deshabilitar_campo(self, 'pasaporte')

    # def sin_fechanacimiento(self):
    #     deshabilitar_campo(self, 'nacimiento')

    def sin_emailinst(self):
        deshabilitar_campo(self, 'emailinst')

    def ocultarcampos(self):
        del self.fields['tienediscapacidad']

    def bloquearcampos(self):
        deshabilitar_campo(self, 'tipodiscapacidad')


class ExperienciaLaboralForm(forms.Form):
    lugar = forms.CharField(label=u'Lugar', max_length=250, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    cargo = forms.CharField(label=u'Cargo', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    actividadlaboral = forms.ModelChoiceField(label=u"Actividad Laboral", queryset=ActividadLaboral.objects.all(), required=True, widget=forms.Select(attrs={'class': 'formcontrol'}))
    fechainicio = forms.DateField(label=u"Inicio", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'form-control', 'formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fin", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'form-control', 'formwidth': '50%'}))
    vigente = forms.BooleanField(label=u"Experiencia Vigente", required=False, widget=forms.CheckboxInput())
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png', 'class': 'dropify'}))


class TitulacionPersonaForm(forms.Form):
    titulo = forms.ModelChoiceField(label=u"Titulo", queryset=Titulo.objects.filter(status=True), required=False, widget=forms.Select(attrs={
        'fieldbuttons': [{'id': 'add_registro_titulo', 'tooltiptext': 'Agregar titulo', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-plus'}]}))
    # areatitulo = forms.ModelChoiceField(label=u"Area de titulalción", queryset=AreaTitulo.objects.all(), required=False,
    #                                     widget=forms.Select(attrs={'class':'form-control'}))
    # fechainicio = forms.DateField(label=u"Fecha inicio de estudios", initial=datetime.now().date(), required=False,
    #                               input_formats=['%d-%m-%Y'],
    #                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number form-control'}))
    # educacionsuperior = forms.BooleanField(label=u'Educación superior', required=False, widget=CheckboxInput())
    institucion = forms.ModelChoiceField(label=u"Institución de educación superior",
                                         queryset=InstitucionEducacionSuperior.objects.all(), required=False,
                                         widget=forms.Select(attrs={'class': 'form-control'}))
    # colegio = forms.ModelChoiceField(label=u"Colegio", queryset=Colegio.objects.all(), required=False,
    #                                  widget=forms.Select(attrs={'class':'form-control'}))
    cursando = forms.BooleanField(label=u'Cursando', required=False, widget=CheckboxInput())
    # fechaobtencion = forms.DateField(label=u"Fecha de obtención", initial=datetime.now().date(), required=False,
    #                                  input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
    #                                                                                   attrs={'class': 'selectorfecha form-control','controlwidth':'25%'}))
    # fechaegresado = forms.DateField(label=u"Fecha de egreso", initial=datetime.now().date(), required=False,
    #                                 input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
    #                                                                                  attrs={'class': 'selectorfecha form-control', 'controlwidth':'25%'}))
    registro = forms.CharField(label=u'Número de registro SENESCYT', max_length=50, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-25 form-control'}))
    # registroarchivo = ExtFileField(label=u'Seleccione Archivo SENESCYT', required=False,
    #                                help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
    #                                ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)
    archivo = ExtFileField(label=u'Seleccione certificado del registro de titulo en la SENESCYT', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)
    # areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento - Campo amplio", queryset=AreaConocimientoTitulacion.objects.all(), required=False, widget=forms.Select())
    # subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento - Campo específico", queryset=SubAreaConocimientoTitulacion.objects.all(), required=False, widget=forms.Select())
    # subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especificaconocimiento - Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.all(), required=False, widget=forms.Select())
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.filter(status=True), required=False,
                                  widget=forms.Select())
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.filter(status=True), required=False,
                                       widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.filter(status=True), required=False,
                                    widget=forms.Select())
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.filter(status=True), required=False,
                                       widget=forms.Select())
    campoamplio = forms.ModelMultipleChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control', 'separator2': True, 'separatortitle': 'Datos del Título', }))
    campoespecifico = forms.ModelMultipleChoiceField(label=u"Campo Especifico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    campodetallado = forms.ModelMultipleChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))

    # anios = forms.IntegerField(initial=0, label=u'Años cursados', required=False, widget=forms.TextInput(
    #     attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    # semestres = forms.IntegerField(initial=0, label=u'Semestres cursados', required=False, widget=forms.TextInput(
    #     attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    # aplicobeca = forms.BooleanField(label=u'Aplico a una beca', required=False, widget=CheckboxInput())
    # tipobeca = forms.ChoiceField(label=u"Tipo de beca", required=False, choices=TIPO_BECA,
    #                              widget=forms.Select(attrs={'class': 'imp-25 form-control','controlwidth':'25%'}))
    # financiamientobeca = forms.ModelChoiceField(label=u"Tipo de financiamiento de la beca", required=False,
    #                                             queryset=FinanciamientoBeca.objects.all(),
    #                                             widget=forms.Select(attrs={'class': 'imp-50 form-control', 'controlwidth':'25%'}))
    # valorbeca = forms.DecimalField(initial="0.00", label=u'Valor beca', required=False,
    #                                widget=forms.TextInput(attrs={'class': 'imp-moneda form-control', 'decimal': '2', 'controlwidth':'25%'}))

    # archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304, widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)
        # self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=None)
        # self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=None)

    def editar(self, titulo):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=titulo.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=titulo.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=titulo.canton)
        # self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=titulo.areaconocimiento)
        # self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=titulo.subareaconocimiento)


class TituloHojaVidaForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=10, required=True,
                                  widget=forms.TextInput(attrs={'class': 'form-control'}))
    nivel = forms.ModelChoiceField(NivelTitulacion.objects.filter(status=True, tipo=1), label=u'Tipo de nivel',
                                   required=True, widget=forms.Select(attrs={'class': 'nivel'}))
    grado = forms.ModelChoiceField(GradoTitulacion.objects.all(), label=u'Grado', required=False, widget=forms.Select())
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento - Campo amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'class': 'select2'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento - Campo específico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'select2'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especificaconocimiento - Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'select2'}))


class CertificadoIdiomaForm(forms.Form):
    # nombres = forms.CharField(label=u"Nombre certificado", max_length=100, widget=forms.TextInput(attrs={'formwidth': '100%'}))
    institucion = forms.ModelChoiceField(label=u'Institución certificadora', required=False, queryset=InstitucionCertificadora.objects.all(),
                                         widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    validainst = forms.BooleanField(label=u'Otra institución', required=False, widget=CheckboxInput())
    otrainstitucion = forms.CharField(label=u"Digite institución", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'normal-input form-control'}))
    idioma = forms.ModelChoiceField(label=u'Idioma', required=True, queryset=Idioma.objects.all(),
                                    widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))

    nivel = forms.ModelChoiceField(label=u'Nivel de suficencia', required=True, queryset=NivelSuficencia.objects.all(),
                                   widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    fecha = forms.DateField(label=u"Fecha certificación", required=True, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],
                            widget=DateTimeInput(format='%d-%m-%Y',
                                                 attrs={'col': '12'}))
    archivo = ExtFileField(label=u'Seleccione archivo', required=False,
                           help_text=u'Tamaño máximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png',
                                             'class': 'dropify'}))


class SolicitudPublicacionForm(forms.Form):
    tiposolicitud = forms.ChoiceField(label=u'Tipo', choices=TIPO_SOLICITUD_PUBLICACION, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    nombre = forms.CharField(label=u'Nombre', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    motivo = forms.CharField(label=u'Detalle de la publicación', widget=forms.Textarea(attrs={'class': 'form-control'}), required=False)
    revista2 = forms.ModelChoiceField(label=u'Revista', queryset=RevistaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'separator2': True, 'separatortitle': 'Datos de la Revista', 'fieldbuttons': [{'id': 'add_revista', 'tooltiptext': 'Agregar', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-plus-square'}], 'class': 'form-control'}))
    # revista2 = forms.ModelChoiceField(label=u'Revista', queryset=RevistaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'separator2': True, 'separatortitle': 'Datos de la Revista', 'fieldbuttons': [{'id': 'add_revista', 'tooltiptext': 'Agregar', 'btnclasscolor': 'btn-success', 'btnfaicon':'fa-plus-square'}, {'id': 'edit_revista', 'tooltiptext': 'Editar', 'btnclasscolor': 'btn-warning', 'btnfaicon':'fa-edit'}]}))
    # revista2 = forms.ModelChoiceField(label=u'Revista', queryset=RevistaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'separator2': True, 'separatortitle': 'Datos de la Revista'}))
    revista = forms.CharField(label=u'Revista', widget=forms.TextInput(attrs={'rows': '2', 'class': 'form-control'}), required=False)
    base = forms.CharField(label=u'Base Indexada', widget=forms.TextInput(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    evento = forms.CharField(label=u'Congreso', widget=forms.TextInput(attrs={'rows': '3', 'separator2': True, 'separatortitle': 'Datos del Congreso', 'class': 'form-control'}), required=False)
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    ciudad = forms.CharField(label=u'Ciudad', widget=forms.TextInput(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    estadopublicacion = forms.ChoiceField(label=u'Estado de Publicación', choices=ESTADO_PUBLICACION_ARTICULO, required=False, widget=forms.Select(attrs={'class': 'form-control', 'separator2': True, 'separatortitle': 'Datos del Artículo'}))
    fecharecepcion = forms.DateField(label=u"Fecha Recepción", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control'}))
    fechaaprobacion = forms.DateField(label=u"Fecha Aprobación", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control'}))
    fechapublicacion = forms.DateField(label=u"Fecha Publicación", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control'}))
    enlace = forms.CharField(label='Enlace Artículo', widget=forms.TextInput(attrs={'rows': '3', 'style': 'text-transform:lowercase', 'class': 'form-control'}), required=False)
    numero = forms.CharField(label=u'Número de la Revista', widget=forms.TextInput(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    volumen = forms.CharField(label=u'Volumen de Revista', widget=forms.TextInput(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    paginas = forms.CharField(label=u'Páginas del artículo en la Revista', widget=forms.TextInput(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    estadopublicacionponencia = forms.ChoiceField(label=u'Estado de Publicación', choices=ESTADO_PUBLICACION_ARTICULO, required=False, widget=forms.Select(attrs={'class': 'imp-50 form-control', 'separator2': True, 'separatortitle': 'Datos de la Ponencia'}))
    fechapublicacionponencia = forms.DateField(label=u"Fecha Publicación", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select())
    sublineainvestigacion = forms.ModelChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select())
    provieneproyecto = forms.BooleanField(label=u"¿Proviene de un proyecto de Investigación?", required=False, initial=False, widget=forms.CheckboxInput())
    tipoproyecto = forms.ChoiceField(label=u'Tipo de Proyecto', choices=TIPO_PROYECTO_ARTICULO, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    proyectointerno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectosInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select())
    proyectoexterno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select())
    comitecientifico = forms.BooleanField(label=u"¿Existe Comité científico evaluador?", required=False, initial=False, widget=forms.CheckboxInput())

    # archivocertificado = ExtFileField(label=u'Carta Aceptación', required=False, help_text=u'(Certificado de publicación/Certificado de aceptación/Carta de aceptación de la ponencia), Tamaño Maximo permitido 10Mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=10485760, widget=forms.FileInput(attrs={'formwidth': '100%', 'separator2': True, 'separatortitle': 'Evidencias'}))
    archivocertificado = ExtFileField(label=u'Carta Aceptación', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=10485760, widget=forms.FileInput(attrs={'formwidth': '100%', 'separator2': True, 'separatortitle': 'Evidencias', 'class': 'form-control'}))
    # archivo = ExtFileField(label=u'Artículo Publicado', required=False, help_text=u'(Libro / Capítulo Libro/Artículo en revista / Ponencia), Tamaño Maximo permitido 10Mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=10485760, widget=forms.FileInput(attrs={'formwidth': '100%', 'separator2': True, 'separatortitle': 'Evidencias'}))
    archivo = ExtFileField(label=u'Publicación', required=False, help_text=u'(Libro / Capítulo Libro/Artículo en revista / Ponencia), Tamaño Maximo permitido 10Mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=10485760, )
    archivoparticipacion = ExtFileField(label=u'Certificado Participación', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=10485760, widget=forms.FileInput(attrs={'class': 'form-control dropify'}))
    archivocomite = ExtFileField(label=u'Comité Científico evaluador', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=10485760, widget=forms.FileInput(attrs={'class': 'form-control dropify'}))

    def editar(self, solicitud):
        deshabilitar_campo(self, 'tiposolicitud')

        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=solicitud.areaconocimiento, vigente=True).order_by('nombre')
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=solicitud.subareaconocimiento, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=solicitud.lineainvestigacion).order_by('nombre')
        if solicitud.provieneproyecto:
            if solicitud.tipoproyecto < 3:
                self.fields['proyectointerno'].queryset = ProyectosInvestigacion.objects.filter(status=True, tipo=solicitud.tipoproyecto).order_by('nombre')
            else:
                self.fields['proyectoexterno'].queryset = ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre')

        # self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
        #     areaconocimiento=solicitud.areaconocimiento)
        # self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
        #     areaconocimiento=solicitud.subareaconocimiento)


class PublicacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}), required=True)
    tiposolicitud = forms.ChoiceField(label=u'Tipo de Solicitud', choices=TIPO_SOLICITUD_PUBLICACION, required=True, widget=forms.Select(attrs={'class': 'form-control', 'formwidth': '50%'}))
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'formwidth': '50%'}))
    archivo = ExtFileField(label=u'Publicación', required=False, help_text=u'(Libro / Capítulo Libro/Artículo en revista / Ponencia), Tamaño Maximo permitido 10Mb, en formato doc, docx, pdf', ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=10485760,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png', 'class': 'dropify'}))


class RevistaInvestigacionForm(forms.Form):
    codigoissn = forms.CharField(label=u'Código ISSN', widget=forms.TextInput(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    nombrerevista = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    institucion = forms.CharField(label=u'Institución', widget=forms.TextInput(attrs={'rows': '3', 'class': 'form-control'}), required=False)
    enlacerevista = forms.CharField(label=u'Enlace', widget=forms.TextInput(attrs={'rows': '1', 'style': 'text-transform:lowercase', 'class': 'form-control'}), required=False)
    baseindexada = forms.ModelMultipleChoiceField(label=u'Base(s) Indexada(s)', queryset=BaseIndexadaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False)
    tipo = forms.ChoiceField(label=u'Tipo', required=False, choices=TIPO_REVISTA, widget=forms.Select(attrs={'class': 'form-control'}))


class CamposTitulosPostulacionForm(forms.Form):
    titulo = forms.ModelChoiceField(label=u"Titulo", queryset=Titulo.objects.filter(status=True).distinct().order_by('nombre'), required=True, widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    campoamplio = forms.ModelMultipleChoiceField(label=u'Campo Amplio', queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control cap', 'col': '12'}))
    campoespecifico = forms.ModelMultipleChoiceField(label=u'Campo Especifico', queryset=SubAreaConocimientoTitulacion.objects.filter(status=True).order_by('nombre'), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control', 'col': '12'}))
    campodetallado = forms.ModelMultipleChoiceField(label=u'Campo Detallado)', queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True).order_by('nombre'), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control', 'col': '12'}))


class CapacitacionPersonaPostulateForm(forms.Form):
    institucion = forms.CharField(label=u'Institución', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    nombre = forms.CharField(label=u'Nombre del evento', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(label=u'Descripción del evento', required=False, widget=forms.Textarea({'rows': '3', 'class': 'form-control'}))
    tipo = forms.ChoiceField(label=u'Tipo', required=True, choices=TIPO_CAPACITACION_P, widget=forms.Select(attrs={'class': 'form-control'}))
    tipocurso = forms.ModelChoiceField(label=u"Tipo de capacitación o actualización científica", queryset=TipoCurso.objects.filter(status=True), required=False,
                                       widget=forms.Select(attrs={'class': 'form-control'}))
    tipoparticipacion = forms.ModelChoiceField(label=u"Tipo certificación", queryset=TipoParticipacion.objects.all(),
                                               required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    tipocapacitacion = forms.ModelChoiceField(label=u"Programado plan Institucional", queryset=TipoCapacitacion.objects.filter(status=True), required=False,
                                              widget=forms.Select(attrs={'class': 'form-control'}))
    modalidad = forms.ChoiceField(label=u"Modalidad", required=False, choices=MODALIDAD_CAPACITACION,
                                  widget=forms.Select(attrs={'class': 'form-control', }))
    otramodalidad = forms.CharField(label=u'Otra Modalidad', max_length=600, required=False,
                                    widget=forms.TextInput(attrs={'class': 'form-control'}))
    anio = forms.IntegerField(label=u"Año", initial=datetime.now().date().year, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'decimal': '0'}))
    contexto = forms.ModelChoiceField(label=u"Contexto de la capacitación/formación", queryset=ContextoCapacitacion.objects.all(), required=False,
                                      widget=forms.Select(attrs={'formwidth': '100%'}))
    detallecontexto = forms.ModelChoiceField(label=u"Detalle de contexto", queryset=DetalleContextoCapacitacion.objects.all(), required=False,
                                             widget=forms.Select(attrs={'formwidth': '100%'}))
    tipocertificacion = forms.ModelChoiceField(label=u"Tipo de planificación", queryset=TipoCertificacion.objects.all(),
                                               required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False,
                                              widget=forms.Select(attrs={'class': 'form-control'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento",
                                                 queryset=SubAreaConocimientoTitulacion.objects.all(), required=False,
                                                 widget=forms.Select(attrs={'class': 'form-control'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento", queryset=SubAreaEspecificaConocimientoTitulacion.objects.all(),
                                                           required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    auspiciante = forms.CharField(label=u'Auspiciante', max_length=200, required=False,
                                  widget=forms.TextInput(attrs={'class': 'form-control'}))
    expositor = forms.CharField(label=u'Expositor', max_length=200, required=False,
                                widget=forms.TextInput(attrs={'class': 'form-control'}))
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    provincia = forms.ModelChoiceField(label=u"Provincia / Estado", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    canton = forms.ModelChoiceField(label=u"Cantón / Ciudad", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", initial=datetime.now().date(), required=False, widget=DateTimeInput(attrs={'class': 'selectorfecha form-control', }))
    fechafin = forms.DateField(label=u"Fecha fin", initial=datetime.now().date(), required=False, widget=DateTimeInput(attrs={'class': 'selectorfecha form-control'}))
    horas = forms.FloatField(initial=0, label=u'Horas', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall form-control', 'decimal': '0', }))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,
                           widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=None)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=None)

    def editar(self, capacitacion):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=capacitacion.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=capacitacion.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=capacitacion.canton)
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(
            areaconocimiento=capacitacion.areaconocimiento, vigente=True)
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(
            areaconocimiento=capacitacion.subareaconocimiento, vigente=True)

    def quitar_campo_archivo(self):
        del self.fields['archivo']


class TribunalForm(forms.Form):
    tipo = forms.ChoiceField(label=u'Tipo Tribunal', required=True, choices=TIPO_TRIBUNAL, widget=forms.Select(attrs={'class': 'form-control'}))
    partida = forms.ModelMultipleChoiceField(label=u"Partida", queryset=Partida.objects.none(), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'style': 'width:100%', 'multiple': 'multiple'}))
    persona = forms.ModelChoiceField(label=u"Persona", queryset=Persona.objects.none(), required=True, widget=forms.Select(attrs={'class': 'form-control select2', 'style': 'width:100%'}))
    cargo = forms.ChoiceField(label=u'Cargo', required=True, choices=CARGOS_TRIBUNAL, widget=forms.Select(attrs={'class': 'form-control'}))
    firma = forms.BooleanField(label=u"¿Firma?", required=False, widget=forms.CheckboxInput())

    def cargar_partidas(self, convocatoria):
        self.fields['partida'].queryset = Partida.objects.filter(status=True, convocatoria=convocatoria)


class SolicitudApelacionForm(forms.Form):
    criterio = forms.ModelMultipleChoiceField(label=u'Elije el criterio de apelación', queryset=CriterioApelacion.objects.filter(status=True, factorapelacion__isnull=False).distinct().order_by('descripcion'), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control cap', 'col': '12'}))
    factor = forms.ModelMultipleChoiceField(label=u'Elija un factor de apelación', queryset=FactorApelacion.objects.filter(status=True).order_by('descripcion'), required=False, widget=forms.CheckboxSelectMultiple())
    observacion = forms.CharField(label=u'Observación', max_length=10000, required=True, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none', 'class': 'form-control'}))
    archivo = ExtFileField(label=u'Evidencia', required=True, help_text=u'Tamaño Maximo permitido 20Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=20194304, widget=forms.FileInput({'class': 'filepdf'}))


class AgendaDisertacionForm(forms.Form):
    tema = forms.CharField(label=u'Tema de Disertación', max_length=1000, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    fechaasistencia = forms.DateField(label=u"Inicio", required=True, widget=DateTimeInput(attrs={'class': 'form-control', 'formwidth': '50%'}))
    horasistencia = forms.TimeField(label=u"Hora", required=True, widget=TimeInput(attrs={'class': 'form-control', 'formwidth': '50%'}))
    lugar = forms.CharField(label=u'Lugar', max_length=100, required=True, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none', 'class': 'form-control'}))
    observacion = forms.CharField(label=u'Observación', max_length=2000, required=True, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none', 'class': 'form-control'}))


class SolicitudRevisionTituloForm(forms.Form):
    inscripcion = forms.ModelChoiceField(label=u"Carrera a valdiar",
                                         help_text=u'Recuerde elegir la carrera a la cual desea validar el título de tercer nivel',
                                         queryset=Inscripcion.objects.filter(status=True), required=True, widget=forms.Select(attrs={'class': 'form-control select2', 'style': 'width:100%'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=2000, required=True, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none; resize: none;', 'class': 'form-control'}))
    evidencia = ExtFileField(label=u'Certificado de inscripción de titulo (SENESCYT)', required=False,
                           help_text=u'Evidencia de su titulación. Tamaño Maximo permitido 10Mb, en formato doc, docx, pdf',
                           ext_whitelist=(".doc", ".docx", ".pdf"), max_upload_size=10485760,
                           widget=FileInput({'accept': 'application/pdf', 'class': 'dropify filepdf'}))

    def cargar_inscripciones(self, inscripciones):
        # self.fields['inscripcion'].queryset = Inscripcion.objects.filter(id__in=inscripciones)
        self.fields['inscripcion'].widget = forms.Select(
            attrs={'class': 'select2'},
            choices=self.get_inscripciones_choices(inscripciones)
        )

    def get_inscripciones_choices(self, inscripciones):
        inscripciones = Inscripcion.objects.filter(id__in=inscripciones)
        return [(inscripcion.id, inscripcion.carrera.nombre) for inscripcion in inscripciones]


    class Meta:
        model = Inscripcion
        fields = ['id', 'carrera']


ESTADO = (
    (1, u'Aprobar'),
    (2, u'Rechazar')
)


class GestionarSolicitudRevisionTituloForm(forms.Form):
    estado = forms.ChoiceField(label=u'Estado', required=True, choices=ESTADO, widget=forms.Select(attrs={'class': 'form-control'}))
    observacion = forms.CharField(label=u'Observacion', max_length=2000, required=True, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none; resize: none;', 'class': 'form-control'}))

