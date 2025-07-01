# -*- coding: UTF-8 -*-
import json
import os
from datetime import datetime, timedelta
from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms import ValidationError
from django.contrib.auth.models import Group, User, Permission
from django.db.models import Q
from django.forms.models import ModelForm, ModelChoiceField, model_to_dict
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from django.db import models, connection, connections
from django.contrib.auth.models import Group

from api.forms.my_form import MY_Form
from sga.models import Persona, Raza, Pais, Provincia, Canton, Parroquia, Sexo, Discapacidad, InstitucionBeca, Credo, \
    PersonaEstadoCivil, ParentescoPersona, RANGO_EDAD_NINO, NivelTitulacion, TIPO_INSTITUCION_LABORAL, GRADO, \
    TIPO_CELULAR, SECTORLUGAR
from admision.models import Periodo
from sga.templatetags.sga_extras import encrypt
from socioecon.models import FormaTrabajo, TipoHogar, PersonaCubreGasto, NivelEstudio, OcupacionJefeHogar, TipoVivienda, \
    MaterialPared, TipoViviendaPro, MaterialPiso, CantidadBannoDucha, TipoServicioHigienico, CantidadTVColorHogar, \
    CantidadVehiculoHogar, CantidadCelularHogar, ProveedorServicio, ACTIVIDADES_RECREACION, REALIZA_TAREAS, \
    SALUBRIDAD_VIDA, ESTADO_GENERAL


class ExtFileField(forms.FileField):
    """
    * max_upload_size - a number indicating the maximum file size allowed for upload.
            500Kb - 524288
            1MB - 1048576
            2.5MB - 2621440
            5MB - 5242880
            10MB - 10485760
            20MB - 20971520
            50MB - 5242880
            100MB 104857600
            250MB - 214958080
            500MB - 429916160
    t = ExtFileField(ext_whitelist=(".pdf", ".txt"), max_upload_size=)
    """

    def __init__(self, *args, **kwargs):
        ext_whitelist = kwargs.pop("ext_whitelist")
        self.ext_whitelist = [i.lower() for i in ext_whitelist]
        self.max_upload_size = kwargs.pop("max_upload_size")
        super(ExtFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        upload = super(ExtFileField, self).clean(*args, **kwargs)
        if upload:
            size = upload.size
            filename = upload.name
            ext = os.path.splitext(filename)[1]
            ext = ext.lower()
            if size == 0 or ext not in self.ext_whitelist or size > self.max_upload_size:
                raise forms.ValidationError("Tipo de fichero o tamanno no permitido!")


class DatosPersonalesForm(MY_Form):
    estadocivil = forms.ModelChoiceField(required=True, queryset=PersonaEstadoCivil.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione estado civil (requerido)'})
    sexo = forms.ModelChoiceField(required=True, queryset=Sexo.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el sexo (requerido)'})
    nacimiento = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese su fecha de nacimiento (requerido)'})
    email = forms.CharField(required=True, max_length=500, widget=forms.TextInput(), error_messages={'required': 'Ingrese su correo electrónico personal (requerido)'})
    libretamilitar = forms.CharField(required=False, max_length=50, widget=forms.TextInput())
    lgtbi = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    eszurdo = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    documento_archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)
    papeleta_archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)
    libretamilitar_archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)

    def initQuerySet(self, data):
        if 'estadocivil' in data:
            self.fields['estadocivil'].queryset = PersonaEstadoCivil.objects.filter(pk=data.get('estadocivil'))
        if 'sexo' in data:
            self.fields['sexo'].queryset = Sexo.objects.filter(pk=data.get('sexo'))

    def clean(self):
        cleaned_data = super(DatosPersonalesForm, self).clean()
        return cleaned_data


class DatosFamiliarForm(MY_Form):
    identificacion = forms.CharField(required=True, max_length=20, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 20 caracteres', 'required': 'Ingrese la identificación (requerido)'})
    nombre = forms.CharField(required=True, max_length=250, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 250 caracteres', 'required': 'Ingrese nombres y apellidos (requerido)'})
    cedulaidentidad = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)
    parentesco = forms.ModelChoiceField(required=True, queryset=ParentescoPersona.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el parentesco (requerido)'})
    nacimiento = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese fecha de nacimiento (requerido)'})
    rangoedad = forms.ChoiceField(choices=RANGO_EDAD_NINO, required=False, widget=forms.Select())
    fallecido = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    telefono = forms.CharField(required=False, max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres'})
    telefono_conv = forms.CharField(required=False, max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres'})
    trabajo = forms.CharField(required=False, max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres'})
    convive = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    sustentohogar = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    niveltitulacion = forms.ModelChoiceField(required=False, queryset=NivelTitulacion.objects.none(), widget=forms.Select())
    formatrabajo = forms.ModelChoiceField(required=False, queryset=FormaTrabajo.objects.none(), widget=forms.Select())
    ingresomensual = forms.FloatField(required=False, initial=0.0, widget=forms.TextInput())
    tipoinstitucionlaboral = forms.ChoiceField(choices=TIPO_INSTITUCION_LABORAL, required=False, widget=forms.Select())
    tienenegocio = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    negocio = forms.CharField(required=False, max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres'})
    tienediscapacidad = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tipodiscapacidad = forms.ModelChoiceField(required=False, queryset=Discapacidad.objects.none(), widget=forms.Select())
    porcientodiscapacidad = forms.IntegerField(required=False, initial=0, widget=forms.TextInput())
    carnetdiscapacidad = forms.CharField(required=False, initial='', max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres'})
    institucionvalida = forms.ModelChoiceField(required=False, queryset=InstitucionBeca.objects.none(), widget=forms.Select())
    ceduladiscapacidad = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)
    essustituto = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    autorizadoministerio = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)

    def initQuerySet(self, data):
        if 'parentesco' in data:
            self.fields['parentesco'].queryset = ParentescoPersona.objects.filter(pk=data.get('parentesco'))
        if 'niveltitulacion' in data:
            self.fields['niveltitulacion'].queryset = NivelTitulacion.objects.filter(pk=data.get('niveltitulacion'))
        if 'formatrabajo' in data:
            self.fields['formatrabajo'].queryset = FormaTrabajo.objects.filter(pk=data.get('formatrabajo'))
        if 'tipodiscapacidad' in data:
            self.fields['tipodiscapacidad'].queryset = Discapacidad.objects.filter(pk=data.get('tipodiscapacidad'))
        if 'institucionvalida' in data:
            self.fields['institucionvalida'].queryset = InstitucionBeca.objects.filter(pk=data.get('institucionvalida'))

    def clean(self):
        cleaned_data = super(DatosFamiliarForm, self).clean()
        tienediscapacidad = cleaned_data.get('tienediscapacidad', False)
        tienenegocio = cleaned_data.get('tienenegocio', False)
        negocio = cleaned_data.get('negocio', None)
        tipodiscapacidad = cleaned_data.get('tipodiscapacidad', None)
        porcientodiscapacidad = cleaned_data.get('porcientodiscapacidad', 0)
        carnetdiscapacidad = cleaned_data.get('carnetdiscapacidad', None)
        institucionvalida = cleaned_data.get('institucionvalida', None)
        if tienenegocio:
            if negocio is None:
                self.add_error('negocio', ValidationError(u'Ingrese descripción del negocio (requerido)'))
        if tienediscapacidad:
            if tipodiscapacidad is None:
                self.add_error('tipodiscapacidad', ValidationError(u'Seleccione el tipo de discapacidad (requerido)'))
            if porcientodiscapacidad <= 0 or porcientodiscapacidad > 100:
                self.add_error('porcientodiscapacidad', ValidationError(u'Ingrese el porcentaje de discapacidad mayor a cero y menro a 100 (requerido)'))
            if carnetdiscapacidad is None:
                self.add_error('carnetdiscapacidad', ValidationError(u'Ingrese número de carné de discapacidad (requerido)'))
            if institucionvalida is None:
                self.add_error('institucionvalida', ValidationError(u'Seleccione entidad que valida su discapacidad (requerido)'))

        return cleaned_data


class DatosDiscapacidadForm(MY_Form):
    tienediscapacidad = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tipodiscapacidad = forms.ModelChoiceField(required=False, queryset=Discapacidad.objects.none(), widget=forms.Select(), error_messages={})
    grado = forms.ChoiceField(choices=GRADO, required=False, widget=forms.Select(), error_messages={})
    carnetdiscapacidad = forms.CharField(required=False, initial='', max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres'})
    porcientodiscapacidad = forms.IntegerField(required=False, initial=0, widget=forms.TextInput(), error_messages={})
    institucionvalida = forms.ModelChoiceField(required=False, queryset=InstitucionBeca.objects.none(), widget=forms.Select(), error_messages={})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba un archivo del carné (requerido)'})
    tienediscapacidadmultiple = forms.BooleanField(required=False, widget=forms.CheckboxInput())

    def initQuerySet(self, data):
        tipodiscapacidad = data.get('tipodiscapacidad', None)
        institucionvalida = data.get('institucionvalida', None)
        if tipodiscapacidad:
            self.fields['tipodiscapacidad'].queryset = Discapacidad.objects.filter(pk=tipodiscapacidad)
        if institucionvalida:
            self.fields['institucionvalida'].queryset = InstitucionBeca.objects.filter(pk=institucionvalida)

    def clean(self):
        cleaned_data = super(DatosDiscapacidadForm, self).clean()
        tienediscapacidad = cleaned_data.get('tienediscapacidad', False)
        tipodiscapacidad = cleaned_data.get('tipodiscapacidad', None)
        try:
            grado = int(cleaned_data.get('grado', None))
        except:
            grado = 0

        carnetdiscapacidad = cleaned_data.get('carnetdiscapacidad', '')
        try:
            porcientodiscapacidad = int(cleaned_data.get('porcientodiscapacidad', '0'))
        except:
            porcientodiscapacidad = 0
        institucionvalida = cleaned_data.get('institucionvalida', None)
        archivo = self.files.get('archivo', None)
        tienediscapacidadmultiple = cleaned_data.get('tienediscapacidadmultiple', False)
        if tienediscapacidad:
            if tipodiscapacidad is None:
                self.add_error('tipodiscapacidad', ValidationError('Seleccione el tipo de discapacidad (requerido)'))
            if grado == 0:
                self.add_error('grado', ValidationError('Seleccione el grado de discapacidad (requerido)'))
            if carnetdiscapacidad == '' or carnetdiscapacidad is None:
                self.add_error('carnetdiscapacidad', ValidationError(u'Ingrese el número del carné de discapacidad (requerido)'))
            if porcientodiscapacidad <= 0 or porcientodiscapacidad > 100:
                self.add_error('porcientodiscapacidad', ValidationError(u'Ingrese el porcentaje de discapacidad mayor a cero y menor a 100 (requerido)'))
            if institucionvalida is None:
                self.add_error('institucionvalida', ValidationError(u'Seleccione la entidad que valida su discapacidad (requerido)'))
            if archivo is not None:
                # self.add_error('archivo', ValidationError(u'Subir archivo del carné su discapacidad (requerido)'))
                if archivo.content_type != 'application/pdf':
                    self.add_error('archivo', ValidationError(u'Archivo de discapacidad, solo se permiten archivos formato pdf (requerido)'))
                elif archivo.size > 15000000:
                    self.add_error('archivo', ValidationError(u'Archivo de discapacidad, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        if tienediscapacidadmultiple:
            tipodiscapacidadmultiple = self.data.get('tipodiscapacidadmultiple', None)
            tipodiscapacidadmultiple = json.loads(tipodiscapacidadmultiple)
            if len(tipodiscapacidadmultiple) == 0:
                self.add_error('tipodiscapacidadmultiple', ValidationError('Seleccione al menos una discapacidad multiple (requerido)'))
        return cleaned_data


class DatosNacimientoForm(MY_Form):
    paisnacimiento = forms.ModelChoiceField(required=True, queryset=Pais.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el país de nacimiento (requerido)'})
    provincianacimiento = forms.ModelChoiceField(required=False, queryset=Provincia.objects.none(), widget=forms.Select(), error_messages={})
    cantonnacimiento = forms.ModelChoiceField(required=False, queryset=Canton.objects.none(), widget=forms.Select(), error_messages={})
    parroquianacimiento = forms.ModelChoiceField(required=False, queryset=Parroquia.objects.none(), widget=forms.Select(), error_messages={})

    def initQuerySet(self, data):
        paisnacimiento = data.get('paisnacimiento', None)
        provincianacimiento = data.get('provincianacimiento', None)
        cantonnacimiento = data.get('cantonnacimiento', None)
        parroquianacimiento = data.get('parroquianacimiento', None)
        if paisnacimiento:
            self.fields['paisnacimiento'].queryset = Pais.objects.filter(pk=paisnacimiento)
        if provincianacimiento:
            self.fields['provincianacimiento'].queryset = Provincia.objects.filter(pk=provincianacimiento)
        if cantonnacimiento:
            self.fields['cantonnacimiento'].queryset = Canton.objects.filter(pk=cantonnacimiento)
        if parroquianacimiento:
            self.fields['parroquianacimiento'].queryset = Parroquia.objects.filter(pk=parroquianacimiento)

    def clean(self):
        cleaned_data = super(DatosNacimientoForm, self).clean()
        paisnacimiento = cleaned_data.get('paisnacimiento', None)
        provincianacimiento = cleaned_data.get('provincianacimiento', None)
        cantonnacimiento = cleaned_data.get('cantonnacimiento', None)
        parroquianacimiento = cleaned_data.get('parroquianacimiento', None)
        if paisnacimiento is None:
            self.add_error('paisnacimiento', ValidationError('Seleccione el pais de nacimiento (requerido)'))
        else:
            if paisnacimiento.pk == 1:
                if provincianacimiento is None:
                    self.add_error('provincianacimiento', ValidationError(u'Seleccione la provincia de nacimiento (requerido)'))
                if cantonnacimiento is None:
                    self.add_error('cantonnacimiento', ValidationError(u'Seleccione el canton de nacimiento (requerido)'))
                if parroquianacimiento is None:
                    self.add_error('parroquianacimiento', ValidationError(u'Seleccione la parroquia de nacimiento (requerido)'))
        return cleaned_data


class DatosDomicilioForm(MY_Form):
    pais = forms.ModelChoiceField(required=True, queryset=Pais.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el país de domicilio o residencia (requerido)'})
    provincia = forms.ModelChoiceField(required=False, queryset=Provincia.objects.none(), widget=forms.Select(), error_messages={})
    canton = forms.ModelChoiceField(required=False, queryset=Canton.objects.none(), widget=forms.Select(), error_messages={})
    parroquia = forms.ModelChoiceField(required=False, queryset=Parroquia.objects.none(), widget=forms.Select(), error_messages={})
    direccion = forms.CharField(required=True, initial='', max_length=300, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 300 caracteres', 'required': 'Ingrese la calle principal de su domicilio o residencia (requerido)'})
    direccion2 = forms.CharField(required=True, initial='', max_length=300, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 300 caracteres', 'required': 'Ingrese la calle secundaria de su domicilio o residencia (requerido)'})
    num_direccion = forms.CharField(required=True, initial='', max_length=15, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 15 caracteres', 'required': 'Ingrese el número de casa/departamento de su domicilio o residencia (requerido)'})
    sector = forms.CharField(required=True, initial='', max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres', 'required': 'Ingrese el sector de su domicilio o residencia (requerido)'})
    referencia = forms.CharField(required=True, initial='', max_length=100, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 100 caracteres', 'required': 'Ingrese una referencia de su domicilio o residencia (requerido)'})
    tipocelular = forms.ChoiceField(choices=TIPO_CELULAR, required=True, widget=forms.Select(), error_messages={'required': 'Seleccione su operador de celular (requerido)'})
    telefono = forms.CharField(required=True, initial='', max_length=20, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 20 caracteres', 'required': 'Ingrese su número de teléfono celular (requerido)'})
    telefono_conv = forms.CharField(required=True, initial='', max_length=20, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 20 caracteres', 'required': 'Ingrese su número de teléfono de domicilio o residencia (requerido)'})
    sectorlugar = forms.ChoiceField(choices=SECTORLUGAR, required=True, widget=forms.Select(), error_messages={'required': 'Seleccione la zona de domicilio o residencia (requerido)'})
    archivocroquis = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba un archivo del croquis (requerido)'})
    archivoplanillaluz = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba un archivo de la planilla de energia (requerido)'})

    def initQuerySet(self, data):
        pais = data.get('pais', None)
        provincia = data.get('provincia', None)
        canton = data.get('canton', None)
        parroquia = data.get('parroquia', None)
        if pais:
            self.fields['pais'].queryset = Pais.objects.filter(pk=pais)
        if provincia:
            self.fields['provincia'].queryset = Provincia.objects.filter(pk=provincia)
        if canton:
            self.fields['canton'].queryset = Canton.objects.filter(pk=canton)
        if parroquia:
            self.fields['parroquia'].queryset = Parroquia.objects.filter(pk=parroquia)

    def clean(self):
        cleaned_data = super(DatosDomicilioForm, self).clean()
        pais = cleaned_data.get('pais', None)
        provincia = cleaned_data.get('provincia', None)
        canton = cleaned_data.get('canton', None)
        parroquia = cleaned_data.get('parroquia', None)
        archivocroquis = self.files.get('archivocroquis', None)
        archivoplanillaluz = self.files.get('archivoplanillaluz', None)
        if pais is None:
            self.add_error('pais', ValidationError('Seleccione el pais de domicilio o residencia (requerido)'))
        else:
            if pais.pk == 1:
                if provincia is None:
                    self.add_error('provincia', ValidationError(u'Seleccione la provincia de domicilio o residencia (requerido)'))
                if canton is None:
                    self.add_error('canton', ValidationError(u'Seleccione el canton de domicilio o residencia (requerido)'))
                if parroquia is None:
                    self.add_error('parroquia', ValidationError(u'Seleccione la parroquia de domicilio o residencia (requerido)'))
        if archivocroquis is not None:
            if archivocroquis.content_type != 'application/pdf':
                self.add_error('archivocroquis', ValidationError(u'Archivo de croquis, solo se permiten archivos formato pdf (requerido)'))
            elif archivocroquis.size > 15000000:
                self.add_error('archivocroquis', ValidationError(u'Archivo de croquis, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        if archivoplanillaluz is not None:
            if archivoplanillaluz.content_type != 'application/pdf':
                self.add_error('archivoplanillaluz', ValidationError(u'Archivo de planilla de luz, solo se permiten archivos formato pdf (requerido)'))
            elif archivoplanillaluz.size > 15000000:
                self.add_error('archivoplanillaluz', ValidationError(u'Archivo de planilla de luz, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class DatosEstructuraFamiliarForm(MY_Form):
    tipohogar = forms.ModelChoiceField(required=False, queryset=TipoHogar.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el tipo de hogar (requerido)'})
    escabezafamilia = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    esdependiente = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    personacubregasto = forms.ModelChoiceField(required=False, queryset=PersonaCubreGasto.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione persona que cubre gasto del hogar (requerido)'})
    otroscubregasto = forms.CharField(required=False, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Ingrese quien cubre gasto del hogar (requerido)'})

    def initQuerySet(self, data):
        tipohogar = data.get('tipohogar', None)
        personacubregasto = data.get('personacubregasto', None)
        if tipohogar:
            self.fields['tipohogar'].queryset = TipoHogar.objects.filter(pk=tipohogar)
            self.fields['tipohogar'].required = True
        if personacubregasto:
            self.fields['personacubregasto'].queryset = PersonaCubreGasto.objects.filter(pk=personacubregasto)
            self.fields['personacubregasto'].required = True
            if int(personacubregasto) == 7:
                self.fields['otroscubregasto'].required = True

    def clean(self):
        cleaned_data = super(DatosEstructuraFamiliarForm, self).clean()
        # tipohogar = cleaned_data.get('tipohogar', None)
        return cleaned_data


class DatosNivelEducacionForm(MY_Form):
    niveljefehogar = forms.ModelChoiceField(required=False, queryset=NivelEstudio.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el tipo de hogar (requerido)'})
    alguienafiliado = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    alguienseguro = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    ocupacionjefehogar = forms.ModelChoiceField(required=False, queryset=OcupacionJefeHogar.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione persona que cubre gasto del hogar (requerido)'})

    def initQuerySet(self, data):
        niveljefehogar = data.get('niveljefehogar', None)
        ocupacionjefehogar = data.get('ocupacionjefehogar', None)
        if niveljefehogar:
            self.fields['niveljefehogar'].queryset = NivelEstudio.objects.filter(pk=niveljefehogar)
            self.fields['niveljefehogar'].required = True
        if ocupacionjefehogar:
            self.fields['ocupacionjefehogar'].queryset = OcupacionJefeHogar.objects.filter(pk=ocupacionjefehogar)
            self.fields['ocupacionjefehogar'].required = True

    def clean(self):
        cleaned_data = super(DatosNivelEducacionForm, self).clean()
        return cleaned_data


class DatosCaracteristicaViviendaForm(MY_Form):
    tipovivienda = forms.ModelChoiceField(required=True, queryset=TipoVivienda.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el tipo de vivienda (requerido)'})
    tipoviviendapro = forms.ModelChoiceField(required=True, queryset=TipoViviendaPro.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione su vivenda el tipo (requerido)'})
    materialpared = forms.ModelChoiceField(required=True, queryset=MaterialPared.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el Material Predominante en las paredes  (requerido)'})
    materialpiso = forms.ModelChoiceField(required=True, queryset=MaterialPiso.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el Material Predominante en el piso  (requerido)'})
    cantbannoducha = forms.ModelChoiceField(required=True, queryset=CantidadBannoDucha.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione la cantidad de cuartos de baño con ducha tiene el hogar (requerido)'})
    tiposervhig = forms.ModelChoiceField(required=True, queryset=TipoServicioHigienico.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el tipo de servicio higiénico con que cuenta el hogar (requerido)'})

    def initQuerySet(self, data):
        tipovivienda = data.get('tipovivienda', None)
        tipoviviendapro = data.get('tipoviviendapro', None)
        materialpared = data.get('materialpared', None)
        materialpiso = data.get('materialpiso', None)
        cantbannoducha = data.get('cantbannoducha', None)
        tiposervhig = data.get('tiposervhig', None)
        self.fields['tipovivienda'].required = False
        self.fields['tipoviviendapro'].required = False
        self.fields['materialpared'].required = False
        self.fields['materialpiso'].required = False
        self.fields['cantbannoducha'].required = False
        self.fields['tiposervhig'].required = False
        if tipovivienda:
            self.fields['tipovivienda'].queryset = TipoVivienda.objects.filter(pk=tipovivienda)
            self.fields['tipovivienda'].required = True
        if tipoviviendapro:
            self.fields['tipoviviendapro'].queryset = TipoViviendaPro.objects.filter(pk=tipoviviendapro)
            self.fields['tipoviviendapro'].required = True
        if materialpared:
            self.fields['materialpared'].queryset = MaterialPared.objects.filter(pk=materialpared)
            self.fields['materialpared'].required = True
        if materialpiso:
            self.fields['materialpiso'].queryset = MaterialPiso.objects.filter(pk=materialpiso)
            self.fields['materialpiso'].required = True
        if cantbannoducha:
            self.fields['cantbannoducha'].queryset = CantidadBannoDucha.objects.filter(pk=cantbannoducha)
            self.fields['cantbannoducha'].required = True
        if tiposervhig:
            self.fields['tiposervhig'].queryset = TipoServicioHigienico.objects.filter(pk=tiposervhig)
            self.fields['tiposervhig'].required = True

    def clean(self):
        cleaned_data = super(DatosCaracteristicaViviendaForm, self).clean()
        return cleaned_data


class DatosHabitoConsumoForm(MY_Form):
    compravestcc = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    usainternetseism = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    usacorreonotrab = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    registroredsocial = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    leidolibrotresm = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())

    def clean(self):
        cleaned_data = super(DatosHabitoConsumoForm, self).clean()
        return cleaned_data


class DatosPosesionBienesForm(MY_Form):
    tienetelefconv = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienecocinahorno = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienerefrig = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienelavadora = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienemusica = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    canttvcolor = forms.ModelChoiceField(required=False, queryset=CantidadTVColorHogar.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione cuantos TV a color tienen en el hogar (requerido)'})
    cantvehiculos = forms.ModelChoiceField(required=False, queryset=CantidadVehiculoHogar.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione cuantos vehículos de uso exclusivo tienen en el hogar (requerido)'})

    def initQuerySet(self, data):
        canttvcolor = data.get('canttvcolor', None)
        cantvehiculos = data.get('cantvehiculos', None)
        if canttvcolor:
            self.fields['canttvcolor'].queryset = CantidadTVColorHogar.objects.filter(pk=canttvcolor)
            self.fields['canttvcolor'].required = True
        if cantvehiculos:
            self.fields['cantvehiculos'].queryset = CantidadVehiculoHogar.objects.filter(pk=cantvehiculos)
            self.fields['cantvehiculos'].required = True

    def clean(self):
        cleaned_data = super(DatosPosesionBienesForm, self).clean()
        return cleaned_data


class DatosAccesoTecnologiaForm(MY_Form):
    tieneinternet = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    internetpanf = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienedesktop = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    equipotienecamara = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienelaptop = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    cantcelulares = forms.ModelChoiceField(required=False, queryset=CantidadCelularHogar.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione cuantos celulares de uso exclusivo tienen en el hogar (requerido)'})
    proveedorinternet = forms.ModelChoiceField(required=False, queryset=ProveedorServicio.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el proveedor de internet (requerido)'})

    def initQuerySet(self, data):
        cantcelulares = data.get('cantcelulares', None)
        proveedorinternet = data.get('proveedorinternet', None)
        if cantcelulares:
            self.fields['cantcelulares'].queryset = CantidadCelularHogar.objects.filter(pk=cantcelulares)
            self.fields['cantcelulares'].required = True
        if proveedorinternet:
            self.fields['proveedorinternet'].queryset = ProveedorServicio.objects.filter(pk=proveedorinternet)
            self.fields['proveedorinternet'].required = True

    def clean(self):
        cleaned_data = super(DatosAccesoTecnologiaForm, self).clean()
        return cleaned_data


class DatosInstalacionesForm(MY_Form):
    tienesala = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienecomedor = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienecocina = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienebanio = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tieneluz = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tieneagua = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienetelefono = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienealcantarilla = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())

    def clean(self):
        cleaned_data = super(DatosInstalacionesForm, self).clean()
        return cleaned_data


class DatosActividadExtracurricularesForm(MY_Form):
    horastareahogar = forms.IntegerField(required=False, initial=0, widget=forms.TextInput(), error_messages={'required': 'Ingrese la cantidad de horas que emplea (requerido)'})
    horastrabajodomestico = forms.IntegerField(required=False, initial=0, widget=forms.TextInput(), error_messages={'required': 'Ingrese la cantidad de horas que emplea (requerido)'})
    horastrabajofuera = forms.IntegerField(required=False, initial=0, widget=forms.TextInput(), error_messages={'required': 'Ingrese la cantidad de horas que emplea (requerido)'})
    horashacertareas = forms.IntegerField(required=False, initial=0, widget=forms.TextInput(), error_messages={'required': 'Ingrese la cantidad de horas que emplea (requerido)'})
    tipoactividad = forms.ChoiceField(choices=ACTIVIDADES_RECREACION, required=False, widget=forms.Select(), error_messages={'required': 'Seleccione el tipo de actividad de recreación (requerido)'})
    otrosactividad = forms.CharField(required=False, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Registre otra actividad (requerido)'})
    tipotarea = forms.ChoiceField(choices=REALIZA_TAREAS, required=False, widget=forms.Select(), error_messages={'required': 'Seleccione donde realiza las tareas (requerido)'})
    otrostarea = forms.CharField(required=False, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Registre otra forma (requerido)'})

    def initQuerySet(self, data):
        horastareahogar = data.get('horastareahogar', None)
        horastrabajodomestico = data.get('horastrabajodomestico', None)
        horastrabajofuera = data.get('horastrabajofuera', None)
        horashacertareas = data.get('horashacertareas', None)
        tipoactividad = data.get('tipoactividad', None)
        # otrosactividad = data.get('otrosactividad', None)
        tipotarea = data.get('tipotarea', None)
        # otrostarea = data.get('otrostarea', None)
        if horastareahogar:
            self.fields['horastareahogar'].required = True
        if horastrabajodomestico:
            self.fields['horastrabajodomestico'].required = True
        if horastrabajofuera:
            self.fields['horastrabajofuera'].required = True
        if horashacertareas:
            self.fields['horashacertareas'].required = True
        if tipoactividad:
            self.fields['tipoactividad'].required = True
            if tipoactividad == '7':
                self.fields['otrosactividad'].required = True
        if tipotarea:
            self.fields['tipotarea'].required = True
            if tipotarea == '8':
                self.fields['otrostarea'].required = True

    def clean(self):
        cleaned_data = super(DatosActividadExtracurricularesForm, self).clean()
        horastareahogar = cleaned_data.get('horastareahogar', None)
        horastrabajodomestico = cleaned_data.get('horastrabajodomestico', None)
        horastrabajofuera = cleaned_data.get('horastrabajofuera', None)
        horashacertareas = cleaned_data.get('horashacertareas', None)
        # tipoactividad = cleaned_data.get('tipoactividad', None)
        # tipotarea = cleaned_data.get('tipotarea', None)
        # otrosactividad = cleaned_data.get('otrosactividad', None)
        # otrostarea = cleaned_data.get('otrostarea', None)
        if horastareahogar is not None:
            if horastareahogar < 0:
                self.add_error('horastareahogar', ValidationError('Ingrese el número valid '))
        if horastrabajodomestico is not None:
            if horastrabajodomestico < 0:
                self.add_error('horastrabajodomestico', ValidationError('Ingrese el número valid '))
        if horastrabajofuera is not None:
            if horastrabajofuera < 0:
                self.add_error('horastrabajofuera', ValidationError('Ingrese el número valid '))
        if horashacertareas is not None:
            if horashacertareas < 0:
                self.add_error('horashacertareas', ValidationError('Ingrese el número valido'))
        return cleaned_data


class DatosRecursosEstudioForm(MY_Form):
    tienefolleto = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienecomputador = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tieneenciclopedia = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    otrosrecursos = forms.CharField(required=True, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Describa otros recursos (requerido)'})
    tienecyber = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienebiblioteca = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienemuseo = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienearearecreacion = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    otrossector = forms.CharField(required=True, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Describa otros sectores (requerido)'})

    def initQuerySet(self, data):
        otrosrecursos = data.get('otrosrecursos', None)
        otrossector = data.get('otrossector', None)
        if otrosrecursos is None:
            self.fields['otrosrecursos'].required = False
        if otrossector is None:
            self.fields['otrossector'].required = False

    def clean(self):
        cleaned_data = super(DatosRecursosEstudioForm, self).clean()
        return cleaned_data


class DatosSaludEstudianteForm(MY_Form):
    tienediabetes = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienehipertencion = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tieneparkinson = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienecancer = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienealzheimer = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienevitiligo = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienedesgastamiento = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienepielblanca = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tienesida = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    otrasenfermedades = forms.CharField(required=True, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Describa otras enfermedades (requerido)'})
    enfermedadescomunes = forms.CharField(required=True, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Describa enfermedades comunes (requerido)'})
    salubridadvida = forms.ChoiceField(choices=SALUBRIDAD_VIDA, required=False, widget=forms.Select(), error_messages={'required': 'Seleccione la condición de vida (requerido)'})
    estadogeneral = forms.ChoiceField(choices=ESTADO_GENERAL, required=False, widget=forms.Select(), error_messages={'required': 'Seleccione el estado de salud de vida (requerido)'})
    tratamientomedico = forms.CharField(required=True, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Describa el tratamiento médico (requerido)'})

    def initQuerySet(self, data):
        tratamientomedico = data.get('tratamientomedico', None)
        enfermedadescomunes = data.get('enfermedadescomunes', None)
        otrasenfermedades = data.get('otrasenfermedades', None)
        salubridadvida = data.get('salubridadvida', None)
        estadogeneral = data.get('estadogeneral', None)
        if tratamientomedico is None:
            self.fields['tratamientomedico'].required = False
        if enfermedadescomunes is None:
            self.fields['enfermedadescomunes'].required = False
        if otrasenfermedades is None:
            self.fields['otrasenfermedades'].required = False
        if salubridadvida is not None:
            self.fields['salubridadvida'].required = True
        if estadogeneral is not None:
            self.fields['estadogeneral'].required = True

    def clean(self):
        cleaned_data = super(DatosSaludEstudianteForm, self).clean()
        return cleaned_data