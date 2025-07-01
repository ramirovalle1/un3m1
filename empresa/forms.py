from datetime import datetime

from django import forms
from django.forms import DateTimeInput

from bd.forms import deshabilitar_campo
from core.custom_forms import FormModeloBase
from empleo.models import NIVEL_INSTRUCCION, MODALIDAD, DEDICACION, JORNADA, GENERO, TIEMPO, POSTULANTE, TIPO_SOLICITUD, OPCION_OBSERVACION_HOJAVIDA, OPCION_OBSERVACION_CONTRATO
from empresa.models import CargoEmpresa, RepresentantesEmpresa
from sagest.models import TipoContrato
from sga.forms import ExtFileField
from sga.models import TipoEmpresa, TIPO_INSTITUCION, SECTOR_ECONOMICO, Pais, Provincia, Canton, \
    TIPO_INSTITUCION_NACIONALIDAD, Parroquia, TipoSangre, Sexo, Carrera, Titulo



class EmpleadorForm(forms.Form):
    tiposolicitud = forms.ChoiceField(choices=TIPO_SOLICITUD, required=False,
                                                    label=u'Tipo de Solicitud', initial=0,
                                                    widget=forms.Select({'col': '12', 'class': 'form-control'}))
    tipoinstitucionnacionalidad = forms.ChoiceField(choices=TIPO_INSTITUCION_NACIONALIDAD, required=True, label=u'Nacionalidad Institución',
                                                    widget=forms.Select({'col': '12', 'class': 'form-control'}))
    ruc = forms.CharField(label=u'Ruc', max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula form-control', 'col': '12'}))
    documentoruc = ExtFileField(label=u'Certificado RUC', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '12', 'class': 'dropify'}))
    nombre = forms.CharField(label=u'Empresa', max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    nombrecorto = forms.CharField(label=u'Nombre corto', max_length=200,
                                  widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    tipoempresa = forms.ModelChoiceField(TipoEmpresa.objects.filter(status=True), label=u'Tipo de empresa', required=False,
                                     widget=forms.Select(attrs={'class': 'imp-75 form-control', 'col': '12'}))
    sectoreconomico = forms.ChoiceField(choices=SECTOR_ECONOMICO, required=False, label=u'Sector Económico',
                                        widget=forms.Select({'col': '12'}))
    email = forms.CharField(max_length=200, label=u"Email", required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50 form-control', 'col': '12'}))
    confi_correo = forms.CharField(max_length=200, label=u"Confirme el Email", required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50 form-control', 'col': '12'}))
    # representante = forms.CharField(max_length=200, label=u"Representante", required=False)
    # cargo = forms.CharField(max_length=200, label=u"Cargo", required=False)
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.filter(status=True), required=True,
                                  widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    provincia = forms.ModelChoiceField(label=u'Provincia-Estado', queryset=Provincia.objects.filter(status=True),
                                       required=False, widget=forms.Select(attrs={'class': 'imp-50 form-control', 'col': '12'}))
    canton = forms.ModelChoiceField(label=u'Cantón', queryset=Canton.objects.filter(status=True),
                                      required=False,
                                      widget=forms.Select(attrs={'class': 'imp-50 form-control', 'col': '12'}))
    direccion = forms.CharField(label=u'Dirección', max_length=200, widget=forms.TextInput(attrs={'class': 'form-control','col': '12'}))
    telefonos = forms.CharField(label=u'Teléfono móvil', max_length=100, widget=forms.TextInput(attrs={'class': 'imp-50 form-control', 'col': '6'}))
    telefonoconv = forms.CharField(label=u'Teléfono convencional', required=False, max_length=50, widget=forms.TextInput(attrs={'class': 'imp-50 form-control', 'col': '6'}))

    actividadprincipal = forms.CharField(label=u'Actividad principal', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control', 'col': '12'}), required=False)

    def editar(self, pais):
        provincia = Provincia.objects.filter(pais=pais)
        self.fields['provincia'].queryset = provincia
        self.fields['canton'].queryset = Canton.objects.filter(pais=pais)

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)

    # def bloquear(self):
    #     deshabilitar_campo(self, 'tipoconvenio')
    #
    # def desbloquear(self):
    #     habilitar_campo(self, 'tipoconvenio')


class RepresentanteForm(FormModeloBase):
    nombres = forms.CharField(label=u"Nombres", max_length=200, widget=forms.TextInput(attrs={'class':'form-control','col': '12'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, widget=forms.TextInput(attrs={'class':'form-control', 'col': '6'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False,
                                widget=forms.TextInput(attrs={'class':'form-control', 'col': '6'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=True,
                             widget=forms.TextInput(attrs={'class': 'imp-cedula form-control', 'col': '6'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-cedula form-control', 'col': '6'}))
    nacimiento = forms.DateField(label=u"Fecha Nacimiento", initial=datetime.now().date(),
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'col': '6'}),
                                 required=False)
    sexo = forms.ModelChoiceField(label=u"Sexo", queryset=Sexo.objects.all(), required=True,
                                  widget=forms.Select(attrs={'class':'form-control', 'col': '6'}))
    paisnacimiento = forms.ModelChoiceField(label=u"País nacimiento", queryset=Pais.objects.all(), required=False,
                                            widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    provincianacimiento = forms.ModelChoiceField(label=u"Provincia nacimiento", queryset=Provincia.objects.all(),
                                                 required=False, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    cantonnacimiento = forms.ModelChoiceField(label=u"Canton nacimiento", queryset=Canton.objects.all(), required=False,
                                              widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    parroquianacimiento = forms.ModelChoiceField(label=u"Parroquia nacimiento", queryset=Parroquia.objects.all(),
                                                 required=False, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=False,
                                   widget=forms.TextInput(attrs={'class':'form-control', 'col': '12'}))
    pais = forms.ModelChoiceField(label=u"País residencia", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    provincia = forms.ModelChoiceField(label=u"Provincia residencia", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    canton = forms.ModelChoiceField(label=u"Canton residencia", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia residencia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    sector = forms.CharField(label=u"Sector", max_length=100, required=False,
                             widget=forms.TextInput(attrs={'class': 'imp-50 form-control'}))
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False,
                                widget=forms.TextInput(attrs={'class': 'imp-75 form-control'}))
    direccion2 = forms.CharField(label=u"Calle Secundaria", max_length=100, required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-75 form-control'}))
    num_direccion = forms.CharField(label=u"Numero Domicilio", max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-25 form-control'}))
    telefono = forms.CharField(label=u"Teléfono Movil", max_length=100, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-25 form-control', 'col': '6'}))
    telefono_conv = forms.CharField(label=u"Teléfono Fijo", max_length=100, required=False,
                                    widget=forms.TextInput(attrs={'class': 'imp-25 form-control', 'col': '6'}))
    email = forms.CharField(label=u"Correo Electronico", max_length=240, required=False,
                            widget=forms.TextInput(attrs={'class': 'imp-50 form-control'}))
    sangre = forms.ModelChoiceField(label=u"Tipo de Sangre", queryset=TipoSangre.objects.all(), required=False,
                                    widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    cargo = forms.ModelChoiceField(label=u"Cargo", queryset=CargoEmpresa.objects.all(), required=True,
                                    widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))

    def adicionar(self):
        self.fields['provincianacimiento'].queryset = Provincia.objects.filter(pais=None)
        self.fields['cantonnacimiento'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquianacimiento'].queryset = Parroquia.objects.filter(canton=None)
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)
        # if EMAIL_INSTITUCIONAL_AUTOMATICO:
        #     del self.fields['emailinst']

    def editar(self, persona):
        deshabilitar_campo(self, 'cedula')
        deshabilitar_campo(self, 'pasaporte')
        self.fields['cedula'].required = False
        self.fields['provincianacimiento'].queryset = Provincia.objects.filter(pais=persona.paisnacimiento)
        self.fields['cantonnacimiento'].queryset = Canton.objects.filter(provincia=persona.provincianacimiento)
        self.fields['parroquianacimiento'].queryset = Parroquia.objects.filter(canton=persona.cantonnacimiento)
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)


class OfertaLaboralForm(FormModeloBase):
    encargado = forms.ModelChoiceField(label=u"Encargado de la oferta", queryset=RepresentantesEmpresa.objects.filter(status=True), required=True,
                                            widget=forms.Select(attrs={'class': 'select ', 'col': '12'}))
    finicio = forms.DateField(label=u"Fecha inicio del proceso", initial=datetime.now().date(),
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control ', 'col': '6'}),
                                 required=True)
    ffin = forms.DateField(label=u"Fecha fin del proceso", initial=datetime.now().date(),
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control ', 'col': '6'}),
                                 required=True)

    finiciopostulacion = forms.DateField(label=u"Fecha inicio de postulacion", initial=datetime.now().date(),
                              widget=DateTimeInput(format='%d-%m-%Y',
                                                   attrs={'class': 'selectorfecha form-control ', 'col': '6'}),
                              required=True)
    ffinpostlacion = forms.DateField(label=u"Fecha fin de postulacion", initial=datetime.now().date(),
                           widget=DateTimeInput(format='%d-%m-%Y',
                                                attrs={'class': 'selectorfecha form-control ', 'col': '6'}),
                           required=True)

    finiciorevision = forms.DateField(label=u"Fecha inicio de revisión de postulantes", initial=datetime.now().date(),
                                         widget=DateTimeInput(format='%d-%m-%Y',
                                                              attrs={'class': 'selectorfecha form-control ',
                                                                     'col': '6'}),
                                         required=True)
    ffinrevision = forms.DateField(label=u"Fecha fin de revisión de postulantes", initial=datetime.now().date(),
                                     widget=DateTimeInput(format='%d-%m-%Y',
                                                          attrs={'class': 'selectorfecha form-control ', 'col': '6'}),
                                     required=True)

    muestranombre = forms.BooleanField(label=u'¿Se muestra el nombre de la empresa?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '20%', 'col': '6'}), initial=True)
    titulo = forms.CharField(label=u"Nombre de la oferta", max_length=100, required=True, widget=forms.Textarea(attrs={'rows': '2', 'placeholder': 'Describa un nombre para la oferta', 'style': 'resize: none'}))
    #        forms.CharField(label=u"RMU", max_length=15, required=True,                  widget=forms.TextInput(attrs={'class': 'imp-25 form-control ', 'col': '6'}))
    quienpostula = forms.ChoiceField(label=u"¿Quién puede postular?", choices=POSTULANTE, required=True, widget=forms.Select(attrs={'class': 'form-control ', 'col': '6'}))
    nivel = forms.ChoiceField(label=u"Nivel mínimo de instrucción", choices=NIVEL_INSTRUCCION, initial=3, required=True, widget=forms.Select(attrs={'class': 'form-control ', 'col': '6', 'dcol': True}))
    carrera = forms.ModelMultipleChoiceField(label=u"Carrera", queryset=Carrera.objects.none(), widget=forms.Select(attrs={'class': 'select ', 'col': '12', 'multiple': True}))
    modalidad = forms.ChoiceField(label=u"Modalidad de trabajo", choices=MODALIDAD, required=True, widget=forms.Select(attrs={'col': '6'}))
    dedicacion = forms.ChoiceField(label=u"Dedicación", choices=((1, u'Tiempo Completo (40 Horas)'), (2, u'Medio tiempo (20 Horas)')), required=True, widget=forms.Select(attrs={'col': '6', 'dcol': '2'}))
    jornada = forms.ChoiceField(label=u"Jornada de trabajo", choices=JORNADA, required=True, widget=forms.Select(attrs={'class': 'form-control ', 'col': '12'}))
    requiereexpe = forms.BooleanField(label=u'¿Requiere experiencia?', required=False, initial=True, widget=forms.CheckboxInput(attrs={'formwidth': '20%', 'col': '6'}))
    tiempoexperiencia = forms.ChoiceField(label=u"Tiempo de experiencia", choices=TIEMPO, required=False,
                                widget=forms.Select(attrs={'col': '6', 'dcol': '4'}))
    muestrarmu = forms.BooleanField(label=u'¿Se muestra el R.M.U.?', required=False, initial=True,
                                       widget=forms.CheckboxInput(attrs={'formwidth': '100%', 'col': '6'}))
    rmu = forms.CharField(label=u"R.M.U.", max_length=15, initial=0.00, required=True, widget=forms.TextInput(attrs={'class': 'imp-25 ', 'type': 'number', 'col': '6', 'step': '0.01', 'min': 0.00, 'max': 1000000000}))
    tipocontrato = forms.ModelChoiceField(label=u"Tipo de contrato", queryset=TipoContrato.objects.all(), required=True,
                                            widget=forms.Select(attrs={'col': '6'}))
    vacantes = forms.CharField(label=u"N° de vacantes", max_length=15, required=True, initial=1,
                          widget=forms.TextInput(attrs={'class': 'imp-25 ', 'autocomplete': 'off', 'type': 'number',  'step': 1, 'min': 1, 'max': 1000, 'col': '6'}))
    sexo = forms.ChoiceField(label=u"¿Sexo a postular?", choices=GENERO, required=True, widget=forms.Select(attrs={'class': 'form-control ', 'col': '12'}))
    muestrapromedio = forms.BooleanField(label=u'¿Desea que muestren el promedio?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%', 'col': '6'}))
    discapacitados = forms.BooleanField(label=u'¿Personas con capacidades especiales?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%', 'col': '6'}))
    viajar = forms.BooleanField(label=u'¿Disponibilidad para viajar?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%', 'col': '6'}))
    carropropio = forms.BooleanField(label=u'¿Necesidad de vehículo propio?', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%', 'col': '6'}))
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=True,
                                  widget=forms.Select(attrs={'class': 'select ', 'col': '6'}))
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.none(), required=False,
                                       widget=forms.Select(attrs={'class': 'form-control select ', 'col': '6', 'dcol': '2'}))
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.none(), required=False,
                                    widget=forms.Select(attrs={'class': 'select ', 'col': '6'}))
    direccion = forms.CharField(label=u"Dirección", max_length=100, required=True,
                                widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa la dirección del lugar de trabajo', 'style': 'resize: none'}))
    areatrabajo = forms.CharField(label=u"¿Área de trabajo?", required=True,
                                 widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa el o las áreas de trabajo', 'style': 'resize: none'}))
    funciones = forms.CharField(label=u"Funciones principales", required=True,
                                 widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa la o las funciones a desempeñar', 'style': 'resize: none'}))
    conocimiento = forms.CharField(label=u"Conocimientos", required=True,
                                 widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa el o los conocimientos específicos requeridos', 'style': 'resize: none'}))
    habilidades = forms.CharField(label=u"Habilidades", required=True,
                                 widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa la o las habilidades especificas requeridas', 'style': 'resize: none'}))
    descripcion = forms.CharField(label=u"Descripción de la oferta", required=False,
                                  widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa más detalles de la oferta', 'style': 'resize: none'}))
    def adicionar(self, empresa):
        self.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion__lte=5)
        self.fields['encargado'].queryset = RepresentantesEmpresa.objects.filter(status=True, empresa=empresa)

    def editar(self, oferta, empresa):
        self.fields['carrera'].initial = oferta.carrera.all()
        self.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion__lte=5)
        self.fields['canton'].initial = oferta.canton
        self.fields['canton'].queryset = Canton.objects.filter(status=True, provincia=oferta.provincia)
        self.fields['provincia'].initial = oferta.provincia
        self.fields['provincia'].queryset = Provincia.objects.filter(status=True, pais=oferta.pais)
        self.fields['encargado'].queryset = RepresentantesEmpresa.objects.filter(status=True, empresa=empresa)

    def set_required_false(self, request):
        self.fields['carrera'].required = False
        self.fields['carrera'].initial = request.getlist('carrera')
        self.fields['canton'].required = False
        self.fields['provincia'].required = False

    def bloquear_fechainicio(self):
        self.fields['finicio'].widget.attrs['readonly'] = True


class CambioClaveFormEmpresa(forms.Form):
    anterior = forms.CharField(label=u'Clave actual', widget=forms.PasswordInput(attrs={'col': '12'}))
    nueva = forms.CharField(label=u'Nueva clave', widget=forms.PasswordInput(attrs={'class': 'validarclave', 'col': '12'}))
    repetir = forms.CharField(label=u'Repetir clave', widget=forms.PasswordInput(attrs={'class': 'validarclave', 'col': '12'}))

class ObservacionHojaVidaForm(FormModeloBase):
    opc_hojavida = forms.ChoiceField(label=u"Motivo de rechazo", choices=OPCION_OBSERVACION_HOJAVIDA, required=True, widget=forms.Select(attrs={'class': 'form-control ', 'col': '12'}))
    observacionhojavida = forms.CharField(label=u"Observación", widget=forms.Textarea(attrs={'rows': '5'}), required=False)

class GestionarContratoForm(FormModeloBase):
    opc_contrato = forms.ChoiceField(label=u"Motivo de rechazo", choices=OPCION_OBSERVACION_CONTRATO, required=True,
                                     widget=forms.Select(attrs={'class': 'form-control ', 'col': '12'}))
    observacioncontrato = forms.CharField(label=u"Observacion", widget=forms.Textarea(attrs={'rows': '5'}), required=False)