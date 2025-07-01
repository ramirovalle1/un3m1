import os
from datetime import datetime, timedelta
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.db.models import Q
from django.forms import ValidationError, DateTimeInput, CheckboxInput
from unidecode import unidecode

from core.custom_forms import FormModeloBase
from poli.models import InstructorActividadPolideportivo, SeccionPolideportivo, TurnoPolideportivo, \
    ActividadPolideportivo, ESTADO_RESERVA_POLIDEPORTIVO, AreaPolideportivo, TIPO_INTEGRANTE, TIPO_ACTIVIDAD, UBICACION, NoticiaDeportiva, InstitucionEscuela, PlanificacionActividad
from sga.forms import ExtFileField, deshabilitar_campo
from sga.funciones import validarcedula, generar_nombre
from sga.models import Utensilios, DisciplinaDeportiva, TIPOS_PERFILES, Carrera, Persona, ParentescoPersona, Sexo


class DisciplinaDeportivaForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input','col':'12'}))

class ImplementoForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input','col':'6'}))
    cantidad = forms.IntegerField(label=u'Cantidad', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'controlwidth': '50px','col':'6'}))

class SancionPolideportivoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'col':'12', 'separator3': True}))
    valor = forms.DecimalField(initial='0.00', label=u'Valor', widget=forms.TextInput(attrs={'class': 'imp-moneda','controlwidth': '50px', 'col':'6'}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))

class PoliticaPolideportivoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'formwidth': 'span12', 'separator3': True}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))
    general = forms.BooleanField(initial=False, required=False, label=u'¿Es una política general?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))
    area = forms.ModelMultipleChoiceField(queryset=AreaPolideportivo.objects.filter(status=True), required=False, label=u'Area',
                                       widget=forms.SelectMultiple(attrs={}))
class AreaPolideportivoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input','col':'12'}))
    portada = ExtFileField(label=u'Portada', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(attrs={'col':'6', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    fondo = ExtFileField(label=u'Fondo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(attrs={'col':'6', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'col':'12', 'separator3': True}))
    numdias = forms.IntegerField(label=u'Número de días para reservación', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col':'6','controlwidth':'50px'}))
    en_mantenimiento = forms.BooleanField(initial=False, required=False, label=u'¿En Mantenimiento?', widget=forms.CheckboxInput(attrs={'class': 'js-switch','col':'6', 'data-switchery': 'true'}))

class FotoAreaPolideportivoForm(FormModeloBase):
    orden = forms.IntegerField(label=u'Orden', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'controlwidth': '50px','col':'6'}))
    visible = forms.BooleanField(initial=False, required=False, label=u'¿Visible?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))
    foto = ExtFileField(label=u'Foto', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))

class TurnoPolideportivoForm(FormModeloBase):
    turno = forms.IntegerField(label=u'Número de turno', initial=0, required=True,
                                 widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0','col':'4','controlwidth':'50px'}))
    comienza = forms.TimeField(label=u"Comienza", required=True, initial=str(datetime.now().time().strftime("%H:%M")),
                               widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','col':'4','controlwidth':'100px'}))
    termina = forms.TimeField(label=u"Termina", required=True, initial=str(datetime.now().time().strftime("%H:%M")),
                              widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','col':'4','controlwidth':'100px'}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'id':'id_mostrar','name':'mostrar','col':'12', 'data-switchery': 'true'}))

class ActividadPolideportivoForm(FormModeloBase):
    disciplina = forms.ModelChoiceField(DisciplinaDeportiva.objects.filter(status=True), required=True, label=u'Disciplina', widget=forms.Select({'col':'6'}))
    tipoactividad = forms.ChoiceField(choices=TIPO_ACTIVIDAD, required=True, label=u'Tipo de actividad', widget=forms.Select({'col':'6'}))
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'formwidth': 'span12', 'separator3': True}))
    responsable = forms.ModelChoiceField(Persona.objects.filter(status=True), required=False, label=u'Responsable', widget=forms.Select(attrs={'select2search': 'true','formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio",
                                  # input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '3'}))
    fechafin = forms.DateField(label=u"Fecha Fin",
                               # input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha','col': '3'}))
    cupo = forms.IntegerField(label=u'Cupo máximo por turno', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '3','controlwidth': '50px'}))
    numacompanantes = forms.IntegerField(label=u'N° de acompañantes', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '3','controlwidth': '50px'}))
    valor = forms.DecimalField(initial='0.00', label=u'Valor de reserva', widget=forms.TextInput(attrs={'class': 'imp-moneda','col': '3','controlwidth': '50px'}))

    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '3', 'data-switchery': 'true'}))
    interno = forms.BooleanField(initial=False, required=False, label=u'¿Para internos?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '3', 'data-switchery': 'true'}))
    externo = forms.BooleanField(initial=False, required=False, label=u'¿Para externos?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '3', 'data-switchery': 'true'}))

    portada = ExtFileField(label=u'Portada', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    carrera=forms.ModelMultipleChoiceField(queryset=Carrera.objects.filter(status=True), required=False, label=u'Carreras', widget=forms.SelectMultiple(attrs={}))

    def validar_tipo(self):
        if not int(self.data['tipoactividad']) == 1:
            self.fields['fechainicio'].required = False
            self.fields['fechafin'].required = False
            self.fields['cupo'].required = False
            self.fields['numacompanantes'].required = False
            self.fields['valor'].required = False



class SeccionPolideportivoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input'}))
    fondo = ExtFileField(label=u'Fondo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    icono = ExtFileField(label=u'Icono', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    cupo = forms.IntegerField(label=u'Cupo máximo por turno', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall','controlwidth': '50px', 'decimal': '0', 'col': '6'}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'data-switchery': 'true','col':'6'}))

class InstructorPolideportivoForm(FormModeloBase):
    persona = forms.ModelChoiceField(queryset=Persona.objects.filter(status=True), required=True, label=u'Instructor', widget=forms.Select(attrs={'class': 'select2', 'col':'6'}))
    activo = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%', 'data-switchery': 'true', 'col':'6'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'col': '12','rows':'3'}))

class InstructorActividadPolideportivoForm(FormModeloBase):
    instructor = forms.IntegerField(initial=0, required=False, label=u'Instructor', widget=forms.Select(attrs={'select2search': 'true','formwidth': '100%', }))
    activo = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%', 'data-switchery': 'true'}))

class HorarioActividadPolideportivoForm(FormModeloBase):
    from sga.models import DIAS_CHOICES
    turno = forms.ModelChoiceField(TurnoPolideportivo.objects.filter(status=True), required=False, label=u'Turno',
                                   widget=forms.Select({'col': '12'}))
    instructor = forms.ModelChoiceField(label=u"Instructor", required=False,
                                        queryset=InstructorActividadPolideportivo.objects.filter(status=True,activo=True).order_by('instructor'),
                                        widget=forms.Select(attrs={'formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio",
                                  # input_formats=['%d-%m-%Y'],
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha Fin",
                               # input_formats=['%d-%m-%Y'],
                               widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha','col': '6'}))
    dia = forms.ChoiceField(label=u"Dia", required=False, choices=DIAS_CHOICES,
                            widget=forms.Select(attrs={'class': 'imp-25', 'col': '6'}))
    mostrar = forms.BooleanField(required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'col': '6', 'data-switchery': True}))

    def cargar_instructores(self, actividad):
        self.fields['instructor'].queryset = InstructorActividadPolideportivo.objects.filter(status=True, activo=True,
                                                                              actividad=actividad).order_by(
            'instructor__persona__apellido1', 'instructor__persona__apellido2', 'instructor__persona__nombres')

    # def editar_instructor(self):
    #     deshabilitar_campo(self, 'instructor')

class ImplementosActividadForm(FormModeloBase):
    utensilio = forms.ModelChoiceField(Utensilios.objects.filter(status=True), required=True, label=u'Implemento',
                                   widget=forms.Select())
    cantidad = forms.IntegerField(label=u'Cantidad', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))

    activo = forms.BooleanField(initial=False, required=False, label=u'¿Activo?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))

    def cargar_instructores(self, actividad):
        self.fields['instructor'].queryset = InstructorActividadPolideportivo.objects.filter(status=True,
                                                                              actividad=actividad).order_by(
            'instructor__persona__apellido1', 'instructor__persona__apellido2', 'instructor__persona__nombres')
        self.fields['secciones'].queryset = SeccionPolideportivo.objects.filter(status=True,area = actividad.area)

    def editar_instructor(self):
        deshabilitar_campo(self, 'instructor')


class PerfilesActividadForm(FormModeloBase):
    perfil = forms.ChoiceField(label=u"Perfil", choices=TIPOS_PERFILES, required=False, widget=forms.Select(attrs={'class': 'imp-25','col':'6'}))
    activo = forms.BooleanField(initial=False, required=False, label=u'¿Activo?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))
    familiares= forms.ModelMultipleChoiceField(queryset=ParentescoPersona.objects.filter(status=True), required=False, widget=forms.SelectMultiple())

# Choise unicamente muestra dos opciones en el formulario
ESTADO_RESERVA_POLIDEPORTIVO_FORM = ((4, u'FINALIZADO'), (3, u'ANULADO'))


class FinalizaReservaForm(forms.Form):
    estado = forms.ChoiceField(label=u"Estado", initial=4, choices=ESTADO_RESERVA_POLIDEPORTIVO_FORM[:1], required=False, widget=forms.Select(attrs={'class': 'imp-25'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea(attrs={'formwidth': '100%', 'separator3': True}))
    asistio = forms.BooleanField(initial=False, required=False, label=u'¿Asistió?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true','id':'id_asistio'}))
    noasistio = forms.BooleanField(initial=False, required=False, label=u'¿No Asistió?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))

# CLUBES
class ClubPoliForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput())
    finicio = forms.DateField(label='Fecha Inicio',required=True, widget=DateTimeInput(attrs={'col':'6'}))
    ffin = forms.DateField(label='Fecha Fin',required=True, widget=DateTimeInput(attrs={'col':'6'}))
    responsable = forms.ModelChoiceField(label='Responsable', queryset=Persona.objects.filter(status=True), required=True, widget=forms.Select(attrs={'select2search': 'true','formwidth': '100%'}))
    disciplina = forms.ModelChoiceField(label='Disciplina', queryset=DisciplinaDeportiva.objects.filter(status=True), required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'col': '12', 'separator3': True}))

class IntegranteClubForm(FormModeloBase):
    integrante = forms.ModelChoiceField(label='Integrante', queryset=Persona.objects.filter(status=True), required=True, widget=forms.Select(attrs={'select2search': 'true','col':'6'}))
    tipointegrante= forms.ChoiceField(label='Tipo de Integrante', choices=TIPO_INTEGRANTE, required=True, widget=forms.Select(attrs={'col':'6'}))

# DESCUENTOS
class DescuentoValorActividadForm(FormModeloBase):
    porcentaje = forms.IntegerField(label=u'Porcentaje', widget=forms.NumberInput(attrs={'class': 'valor text-center ','col': '4','placeholder':'0%', 'input_group':True}))
    valor_descuento = forms.DecimalField(label=u'Descuento', widget=forms.TextInput(attrs={'class': 'valor text-center ','col': '4','placeholder':'0.00', 'input_group':True}))
    valor_final = forms.DecimalField(label=u'Valor Final', widget=forms.TextInput(attrs={'class': 'valor text-center ','col': '4','placeholder':'0.00', 'input_group':True}))
    aplicavigencia = forms.BooleanField(label=u'¿Aplica con limite de tiempo?', required=False,
                                        widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '4'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio",required=True,
                                  widget=DateTimeInput(format='%d-%m-%Y',attrs={ 'col': '4'}))
    fechafin = forms.DateField(label=u"Fecha Fin",required=True,
                               widget=DateTimeInput(format='%d-%m-%Y',attrs={'col': '4'}))

class RegistroUsuarioExternoForm(FormModeloBase):
    tipoidentificacion=forms.ChoiceField(label="Tipo de identificación",initial=1, choices=((1,'Cédula'),(2,'Pasaporte')),
                                         widget=forms.Select(attrs={'col':'6','icon':'fa fa-address-card'}))
    identificacion = forms.CharField(label=u"Identificación", max_length=13, required=True,
                             widget=forms.TextInput(attrs={'col': '6', 'icon':'fa fa-address-card','placeholder': 'Ingresa tu identificación según su tipo seleccionado.'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=True,
                              widget=forms.TextInput(attrs={'col': '12','icon':'fa fa-signature', 'placeholder': 'Ingresa tus nombres'}))
    apellido1 = forms.CharField(label=u"Primer apellido", max_length=50, required=True,
                                widget=forms.TextInput(attrs={'col': '6','icon':'fa fa-signature', 'placeholder': 'Ingresa tu primer apellido'}))
    apellido2 = forms.CharField(label=u"Segundo apellido", max_length=50, required=True,
                                widget=forms.TextInput(attrs={'col': '6','icon':'fa fa-signature', 'placeholder': 'Ingresa tu segundo apellido'}))
    nacimiento = forms.DateField(label=u'Fecha nacimiento', required=True,
                                       widget=forms.DateTimeInput(attrs={'col': '6','icon':'fa fa-calendar'}))
    sexo = forms.ModelChoiceField(label=u"Genero", required=True,
                                  queryset=Sexo.objects.filter(status=True),
                                  widget=forms.Select(attrs={'col': '6','icon':'fa fa-venus-mars'}))
    celular = forms.CharField(label=u"Teléfono celular", max_length=50, required=True,
                              widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Ingresa tu teléfono celular', 'icon': 'fa fa-phone'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=True,
                            widget=forms.EmailInput(attrs={'col': '6', 'placeholder': 'Ingresa tu correo electrónico', 'icon': 'fa fa-envelope'}))

    def clean(self):
        cleaned_data = super().clean()
        tipoidentificacion = cleaned_data.get('tipoidentificacion')
        nombres = cleaned_data.get('nombres').upper()
        apellido1 = cleaned_data.get('apellido1').upper()
        apellido2 = cleaned_data.get('apellido2').upper()
        email = cleaned_data.get('email').lower()
        identificacion = cleaned_data.get('identificacion').strip()
        celular = cleaned_data.get('celular')
        if len(nombres.split()) < 2 :
            self.add_error('nombres', 'Por favor digite sus nombres completos.')
        if Persona.objects.filter(Q(email=email) | Q(usuario__email=email), status=True).exists():
            self.add_error('email','El email ingresado ya esta en uso en otra cuenta.')
        if tipoidentificacion == 1 and not validarcedula(identificacion) == 'Ok':
            self.add_error('identificacion', validarcedula(identificacion))
        if Persona.objects.filter(Q(pasaporte=identificacion) | Q(cedula=identificacion) | Q(pasaporte=('VS'+identificacion)) | Q(cedula=identificacion[2:]),usuario__isnull=False, status=True).exists():
            self.add_error('identificacion', 'Usuario que desea registrar con los datos proporcionados ya existe')
        return cleaned_data

class EncuestaPreguntaForm(FormModeloBase):
    valoracion = forms.IntegerField(label=u'Cantidad de estrellas', widget=forms.NumberInput(attrs={'class': 'valor text-center ', 'col': '6', 'placeholder': '0', 'input_group': '<i class="fa fa-star"></i>', 'controlwidth': '50%'}))
    vigente = forms.BooleanField(label=u'¿Vigente?', required=False,
                                        widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))


# SITIO WEB UNEMI DEPORTE FORMULARIOS
class TituloWebSiteForm(FormModeloBase):
    titulo = forms.CharField(label=u'Título de cabecera', max_length=100, required=True,
                              widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese su título'}))
    subtitulo = forms.CharField(label=u'Subtitulo de cabecera', max_length=100, required=True,
                             widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese el subtitulo'}))
    fondotitulo = ExtFileField(label=u'Fondo', required=False, help_text=u'Tamaño Maximo permitido 2Mb, en formato jpg, jpeg, png',
                               max_upload_size=2194304, ext_whitelist=(".jpg", ".jpeg", ".png"),
                               widget=forms.FileInput(attrs={'col': '12', 'accept': '.png, .jpg, .jpeg'}))
    publicado = forms.BooleanField(label=u'¿Publicado?', required=False,
                                        widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '12'}))

class CuerpoWebSiteForm(FormModeloBase):
    ubicacion = forms.ChoiceField(label='Ubicación', required=False, choices=UBICACION, widget=forms.HiddenInput())
    titulo = forms.CharField(label=u'Título', max_length=100, required=False,
                              widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese su título'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=100, required=False,
                             widget=forms.Textarea(attrs={'col': '12','rows':'3', 'placeholder': 'Ingrese la descripción requerida'}))
    orden = forms.IntegerField(label=u'Orden de aparición', initial=0, widget=forms.NumberInput(attrs={'class': 'input_number','input_number':True, 'col': '4', 'placeholder': '0', 'controlwidth': '50%'}))
    publicado = forms.BooleanField(label=u'¿Publicado?', required=False,
                                        widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))

class NoticiaDeportivaForm(FormModeloBase):
    titulo = forms.CharField(label=u'Título', max_length=200, required=True,
                              widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese su título'}))
    subtitulo = forms.CharField(label=u'Subtitulo', max_length=200, required=True,
                             widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese el subtitulo'}))
    portada = forms.FileField(label=u'Portada de la noticia', required=False, help_text=u'Tamaño Máximo permitido 2Mb, en formato jpg, jpeg, png',
                              widget=forms.FileInput(attrs={'col': '12', 'accept': '.png, .jpg, .jpeg', 'dropify': True}))
    principal = forms.BooleanField(label=u'¿Es noticia principal?', required=False,
                                   widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))
    publicado = forms.BooleanField(label=u'¿Publicado?', required=False,
                                        widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))
    descripcion = forms.CharField(label=u'Contenido de noticia', required=True,
                                  widget=forms.Textarea(attrs={'col': '12'}))
    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        portada = cleaned_data.get('portada')
        titulo = cleaned_data.get('titulo')
        principal = cleaned_data.get('principal')
        if principal:
            noticias = NoticiaDeportiva.objects.filter(status=True, principal=True, publicado=True).exclude(id=id)
            if len(noticias) >= 3:
                self.add_error('principal', 'No puede ser una noticia principal por que solo se admiten hasta 3 noticias principales y ya existen 3 noticias principales vigentes')
        if portada:
            max_tamano = 2 * 1024 * 1024  # 4 MB
            name_= portada._name
            ext = name_[name_.rfind("."):]
            if not ext.lower() in ['.png', '.jpg', '.jpeg']:
                self.add_error('portada', f'Solo se permite formato .png, .jpg, .jpeg')

            if portada.size > max_tamano:
                self.add_error('portada', f'Archivo supera los 4 megas permitidos')
            # Asignar un nombre personalizado al archivo
            portada.name = unidecode(generar_nombre(f"portada_noticia_{titulo.lower()[:3]}", portada._name))
        elif instancia:
            portada = instancia.portada
        cleaned_data['portada'] = portada
        return cleaned_data

class PersonaPrimariaForm(FormModeloBase):
    escuela = forms.ModelChoiceField(label=u"Escuela", queryset=InstitucionEscuela.objects.filter(status=True),
                                     required=False, widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    anios = forms.IntegerField(initial=0, label=u'Años cursados', required=True,
                               widget=forms.NumberInput(attrs={'col': '6', 'decimal': '0', 'class': 'input_number'}))
    cursando = forms.BooleanField(label=u'Cursando', required=False,
                                  widget=CheckboxInput(attrs={'col': '6', 'data-switchery': True}))
    inicio = forms.DateField(label=u"Inicio de estudios", initial=datetime.now().date(),
                             required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    fin = forms.DateField(label=u"Fecha de obtención", initial=datetime.now().date(),
                          required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))

class PlanificacionActividadForm(FormModeloBase):
    nombre = forms.CharField(label=u'Título de planificación', max_length=100, required=True, widget=forms.TextInput({'placeholder':'Ejemplo: 1PF-2024'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio",
                                  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha Fin",
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    cupo = forms.IntegerField(label=u'Cupos', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'input_number','input_number':True, 'decimal': '0', 'col': '6', 'controlwidth': '50px'}))
    costo = forms.DecimalField(initial='0.00', label=u'Costo de inscripción', widget=forms.TextInput(attrs={'class': 'input_money', 'col': '6', 'input_group': '<i class="fa fa-dollar"></i>'}))
    activo = forms.BooleanField(initial=False, required=False, label=u'¿Activo?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': True}))

    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        fechainicio = cleaned_data.get('fechainicio')
        nombre = cleaned_data.get('nombre')
        fechafin = cleaned_data.get('fechafin')
        if instancia:
            planificaciones = PlanificacionActividad.objects.filter(status=True, actividad=instancia.actividad, nombre__unaccent__iexact=nombre).exclude(id=instancia.id)
            if planificaciones:
                self.add_error('nombre', 'Título de planificación ya existe')
        if fechainicio > fechafin:
            self.add_error('fechainicio', 'Fecha de inicio tiene que ser menor a fecha de finalización')
        return cleaned_data

class SubirComprobanteForm(FormModeloBase):
    archivo = forms.FileField(label=u'Fondo', required=True, help_text=u'Tamaño Maximo permitido 2Mb, en formato .png, .jpg, .jpeg, .pdf',
                               widget=forms.FileInput(attrs={'col': '12', 'accept': '.png, .jpg, .jpeg, .pdf'}))
    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        archivo = cleaned_data.get('archivo')
        if archivo:
            max_tamano = 2 * 1024 * 1024  # 2 MB
            name_= archivo._name
            ext = name_[name_.rfind("."):]
            if not ext.lower() in ['.png', '.jpg', '.jpeg', '.pdf']:
                self.add_error('portada', f'Solo se permite formato .png, .jpg, .jpeg, .pdf')

            if archivo.size > max_tamano:
                self.add_error('portada', f'Archivo supera los 2 megas permitidos')
            # Asignar un nombre personalizado al archivo
            archivo.name = unidecode(generar_nombre(f"comprobante{id}_", archivo._name))
        elif instancia:
            archivo = instancia.archivo
        cleaned_data['archivo'] = archivo
        return cleaned_data