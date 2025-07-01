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
from med.models import Enfermedad
from sagest.models import TipoVacunaCovid
from sga.models import Persona, Raza, Pais, Provincia, Canton, Parroquia, Sexo, Discapacidad, InstitucionBeca, Credo, \
    PersonaEstadoCivil, ParentescoPersona, RANGO_EDAD_NINO, NivelTitulacion, TIPO_INSTITUCION_LABORAL, GRADO, \
    TIPO_CELULAR, SECTORLUGAR, NacionalidadIndigena, TipoSangre, Titulo, Colegio, InstitucionEducacionSuperior, \
    AreaTitulo, TIPO_CAPACITACION_P, TipoCurso, TipoParticipacion, TipoCapacitacion, MODALIDAD_CAPACITACION, \
    TipoCertificacion, ContextoCapacitacion, DetalleContextoCapacitacion, AreaConocimientoTitulacion, \
    SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, Idioma, InstitucionCertificadora, \
    NivelSuficencia, VALOR_SI_NO, TIPO_INSTITUCION_BECA
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


class DatosPersonalesBasicoForm(MY_Form):
    estadocivil = forms.ModelChoiceField(required=True, queryset=PersonaEstadoCivil.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione estado civil (requerido)'})
    sexo = forms.ModelChoiceField(required=True, queryset=Sexo.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el sexo (requerido)'})
    nacimiento = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese su fecha de nacimiento (requerido)'})
    email = forms.CharField(required=True, max_length=500, widget=forms.TextInput(), error_messages={'required': 'Ingrese su correo electrónico personal (requerido)'})
    libretamilitar = forms.CharField(required=False, max_length=50, widget=forms.TextInput())
    lgtbi = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    eszurdo = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    paisnacionalidad = forms.ModelChoiceField(required=True, queryset=Pais.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el país de nacionalidad (requerido)'})
    documento_archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)
    papeleta_archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)
    libretamilitar_archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)

    def initQuerySet(self, data):
        if 'estadocivil' in data:
            self.fields['estadocivil'].queryset = PersonaEstadoCivil.objects.filter(pk=data.get('estadocivil'))
        if 'sexo' in data:
            self.fields['sexo'].queryset = Sexo.objects.filter(pk=data.get('sexo'))
        paisnacionalidad = data.get('paisnacionalidad', None)
        if paisnacionalidad:
            self.fields['paisnacionalidad'].queryset = Pais.objects.filter(pk=paisnacionalidad)

    def clean(self):
        cleaned_data = super(DatosPersonalesBasicoForm, self).clean()
        return cleaned_data



class DatosPersonalesNacimientoForm(MY_Form):
    paisnacimiento = forms.ModelChoiceField(required=True, queryset=Pais.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el país de nacimiento (requerido)'})
    provincianacimiento = forms.ModelChoiceField(required=False, queryset=Provincia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    cantonnacimiento = forms.ModelChoiceField(required=False, queryset=Canton.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    parroquianacimiento = forms.ModelChoiceField(required=False, queryset=Parroquia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })

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
        cleaned_data = super(DatosPersonalesNacimientoForm, self).clean()
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


class DatosPersonalesDomicilioForm(MY_Form):
    pais = forms.ModelChoiceField(required=True, queryset=Pais.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el país de domicilio o residencia (requerido)'})
    provincia = forms.ModelChoiceField(required=False, queryset=Provincia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    canton = forms.ModelChoiceField(required=False, queryset=Canton.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    parroquia = forms.ModelChoiceField(required=False, queryset=Parroquia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    direccion = forms.CharField(required=True, initial='', max_length=300, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 300 caracteres', 'required': 'Ingrese la calle principal de su domicilio o residencia (requerido)'})
    direccion2 = forms.CharField(required=True, initial='', max_length=300, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 300 caracteres', 'required': 'Ingrese la calle secundaria de su domicilio o residencia (requerido)'})
    num_direccion = forms.CharField(required=True, initial='', max_length=15, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 15 caracteres', 'required': 'Ingrese el número de casa/departamento de su domicilio o residencia (requerido)'})
    sector = forms.CharField(required=True, initial='', max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres', 'required': 'Ingrese el sector de su domicilio o residencia (requerido)'})
    referencia = forms.CharField(required=True, initial='', max_length=100, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 100 caracteres', 'required': 'Ingrese una referencia de su domicilio o residencia (requerido)'})
    ciudadela = forms.CharField(required=True, initial='', max_length=300, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 300 caracteres', 'required': 'Ingrese la ciudadela de su domicilio o residencia (requerido)'})
    tipocelular = forms.ChoiceField(choices=TIPO_CELULAR, required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione su operador de celular (requerido)'})
    telefono = forms.CharField(required=True, initial='', max_length=20, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 20 caracteres', 'required': 'Ingrese su número de teléfono celular (requerido)'})
    telefono_conv = forms.CharField(required=True, initial='', max_length=20, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 20 caracteres', 'required': 'Ingrese su número de teléfono de domicilio o residencia (requerido)'})
    sectorlugar = forms.ChoiceField(choices=SECTORLUGAR, required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la zona de domicilio o residencia (requerido)'})
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
        cleaned_data = super(DatosPersonalesDomicilioForm, self).clean()
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


class DatosPersonalesFamiliarForm(MY_Form):
    identificacion = forms.CharField(required=True, max_length=20, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 20 caracteres', 'required': 'Ingrese la identificación (requerido)'})
    nombre = forms.CharField(required=True, max_length=250, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 250 caracteres', 'required': 'Ingrese nombres y apellidos (requerido)'})
    cedulaidentidad = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000)
    parentesco = forms.ModelChoiceField(required=True, queryset=ParentescoPersona.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el parentesco (requerido)'})
    nacimiento = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese fecha de nacimiento (requerido)'})
    rangoedad = forms.ChoiceField(choices=RANGO_EDAD_NINO, required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    fallecido = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    telefono = forms.CharField(required=False, max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres'})
    telefono_conv = forms.CharField(required=False, max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres'})
    trabajo = forms.CharField(required=False, max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres'})
    convive = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    sustentohogar = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    niveltitulacion = forms.ModelChoiceField(required=False, queryset=NivelTitulacion.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    formatrabajo = forms.ModelChoiceField(required=False, queryset=FormaTrabajo.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    ingresomensual = forms.FloatField(required=False, initial=0.0, widget=forms.TextInput())
    tipoinstitucionlaboral = forms.ChoiceField(choices=TIPO_INSTITUCION_LABORAL, required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    tienenegocio = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    negocio = forms.CharField(required=False, max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres'})
    tienediscapacidad = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tipodiscapacidad = forms.ModelChoiceField(required=False, queryset=Discapacidad.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    porcientodiscapacidad = forms.IntegerField(required=False, initial=0, widget=forms.TextInput())
    carnetdiscapacidad = forms.CharField(required=False, initial='', max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres'})
    institucionvalida = forms.ModelChoiceField(required=False, queryset=InstitucionBeca.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
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
        cleaned_data = super(DatosPersonalesFamiliarForm, self).clean()
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


class DatosPersonalesDiscapacidadForm(MY_Form):
    tienediscapacidad = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tipodiscapacidad = forms.ModelChoiceField(required=False, queryset=Discapacidad.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    grado = forms.ChoiceField(choices=GRADO, required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    carnetdiscapacidad = forms.CharField(required=False, initial='', max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres'})
    porcientodiscapacidad = forms.IntegerField(required=False, initial=0, widget=forms.TextInput(), error_messages={})
    institucionvalida = forms.ModelChoiceField(required=False, queryset=InstitucionBeca.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
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
        cleaned_data = super(DatosPersonalesDiscapacidadForm, self).clean()
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


class DatosPersonalesEtniaForm(MY_Form):
    raza = forms.ModelChoiceField(required=True, queryset=Raza.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la étnia (requerido)'})
    nacionalidadindigena = forms.ModelChoiceField(required=False, queryset=NacionalidadIndigena.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la nacionalidad indigena (requerido)'})
    archivoraza = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba un archivo (requerido)'})

    def initQuerySet(self, data):
        raza = data.get('raza', None)
        nacionalidadindigena = data.get('nacionalidadindigena', None)
        if raza:
            self.fields['raza'].queryset = Raza.objects.filter(pk=raza)
            if int(raza) == 1:
                self.fields['nacionalidadindigena'].required = True
        if nacionalidadindigena:
            self.fields['nacionalidadindigena'].queryset = NacionalidadIndigena.objects.filter(pk=nacionalidadindigena)

    def clean(self):
        cleaned_data = super(DatosPersonalesEtniaForm, self).clean()
        archivoraza = self.files.get('archivoraza', None)
        if archivoraza is not None:
            # self.add_error('archivo', ValidationError(u'Subir archivo del carné su discapacidad (requerido)'))
            if archivoraza.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivoraza.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))

        return cleaned_data


class DatosPersonalesMigranteForm(MY_Form):
    paisresidencia = forms.ModelChoiceField(required=True, queryset=Pais.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el país de residencia (requerido)'})
    fecharetorno = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese fecha de retorno (requerido)'})
    anioresidencia = forms.IntegerField(required=True, initial=0, widget=forms.TextInput(), error_messages={ 'required': 'Ingrese los años de residencia (requerido)'})
    mesresidencia = forms.IntegerField(required=True, initial=0, widget=forms.TextInput(), error_messages={ 'required': 'Ingrese los meses de residencia (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba un archivo (requerido)'})

    def initQuerySet(self, data):
        paisresidencia = data.get('paisresidencia', None)
        if paisresidencia:
            self.fields['paisresidencia'].queryset = Pais.objects.filter(pk=paisresidencia)

    def clean(self):
        cleaned_data = super(DatosPersonalesMigranteForm, self).clean()
        archivo = self.files.get('archivo', None)
        paisresidencia = cleaned_data.get('paisresidencia', None)
        anioresidencia = cleaned_data.get('anioresidencia', 0)
        mesresidencia = cleaned_data.get('mesresidencia', 0)
        if anioresidencia == 0 and mesresidencia == 0:
            self.add_error('mesresidencia', ValidationError(u'Ingrese mayor a cero meses (requerido)'))
            self.add_error('anioresidencia', ValidationError(u'Ingrese mayor a cero años (requerido)'))
        if mesresidencia > 12:
            self.add_error('mesresidencia', ValidationError(u'Ingrese un valor mayor a cero y menor a doce meses (requerido)'))
        if paisresidencia:
            if paisresidencia.pk == 1:
                self.add_error('paisresidencia', ValidationError(u'País no permitido (requerido)'))
        if archivo is not None:
            # self.add_error('archivo', ValidationError(u'Subir archivo del carné su discapacidad (requerido)'))
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))

        return cleaned_data


class DatosPersonalesEmbarazoForm(MY_Form):
    gestacion = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    lactancia = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    fechainicioembarazo = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese fecha inicio de embarazo (requerido)'})
    fechaparto = forms.DateField(required=False, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese fecha de parto (requerido)'})
    semanasembarazo = forms.IntegerField(required=False, initial=0, widget=forms.TextInput(), error_messages={'required': 'Ingrese los años de residencia (requerido)'})

    def clean(self):
        cleaned_data = super(DatosPersonalesEmbarazoForm, self).clean()
        return cleaned_data


class DatosPersonalesSituacionLaboralForm(MY_Form):
    disponetrabajo = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tipoinstitucionlaboral = forms.ChoiceField(choices=TIPO_INSTITUCION_LABORAL, required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo de institución/empresa (requerido)'})
    lugartrabajo = forms.CharField(required=False, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Describa la institución o empresa (requerido)'})
    buscaempleo = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    tienenegocio = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    negocio = forms.CharField(required=False, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Describa el nombre del negocio (requerido)'})

    def initQuerySet(self, data):
        disponetrabajo = (data.get('disponetrabajo', 'false')) == 'true'
        tienenegocio = (data.get('tienenegocio', 'false')) == 'true'
        if disponetrabajo:
            self.fields['tipoinstitucionlaboral'].required = True
            self.fields['lugartrabajo'].required = True
        if tienenegocio:
            self.fields['negocio'].required = True

    def clean(self):
        cleaned_data = super(DatosPersonalesSituacionLaboralForm, self).clean()
        disponetrabajo = cleaned_data.get('disponetrabajo', False)
        tipoinstitucionlaboral = int(cleaned_data.get('tipoinstitucionlaboral', '0'))
        if disponetrabajo:
            if tipoinstitucionlaboral == 0:
                self.add_error('tipoinstitucionlaboral', ValidationError('Seleccione el tipo de institución/empresa (requerido)'))
        return cleaned_data


class DatosPersonalesMedicosForm(MY_Form):
    carnetiess = forms.CharField(required=False, initial='', max_length=20, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 20 caracteres', 'required': 'Ingrese el número del IESS (requerido)'})
    peso = forms.FloatField(required=True, widget=forms.TextInput(), error_messages={'required': 'Ingrese el peso en kilogramos (requerido)'})
    talla = forms.FloatField(required=True, widget=forms.TextInput(), error_messages={'required': 'Ingrese la talla en metros (requerido)'})
    sangre = forms.ModelChoiceField(required=True, queryset=TipoSangre.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo de sangre (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el certificado de sangre (requerido)'})

    def initQuerySet(self, data):
        sangre = data.get('sangre', None)
        if sangre:
            self.fields['sangre'].queryset = TipoSangre.objects.filter(pk=sangre)

    def clean(self):
        cleaned_data = super(DatosPersonalesMedicosForm, self).clean()
        archivo = self.files.get('archivo', None)
        if archivo is not None:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class DatosMedicContactoEmergenciaForm(MY_Form):
    contactoemergencia = forms.CharField(required=True, initial='', max_length=200, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Ingrese nombre del contacto de emergencia (requerido)'})
    telefonoemergencia = forms.CharField(required=True, initial='', max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres', 'required': 'Ingrese teléfono del contacto de emergencia (requerido)'})
    parentescoemergencia = forms.ModelChoiceField(required=True, queryset=ParentescoPersona.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el parentesco del contacto de emergencia (requerido)'})

    def initQuerySet(self, data):
        parentescoemergencia = data.get('parentescoemergencia', None)
        if parentescoemergencia:
            self.fields['parentescoemergencia'].queryset = ParentescoPersona.objects.filter(pk=parentescoemergencia)

    def clean(self):
        cleaned_data = super(DatosMedicContactoEmergenciaForm, self).clean()
        return cleaned_data


class DatosMedicosEnfermedadForm(MY_Form):
    enfermedad = forms.ModelChoiceField(required=True, queryset=Enfermedad.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la enfermedad (requerido)'})
    archivomedico = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba la valoración médica (requerido)'})

    def initQuerySet(self, data):
        enfermedad = data.get('enfermedad', None)
        if enfermedad:
            self.fields['enfermedad'].queryset = Enfermedad.objects.filter(pk=enfermedad)

    def clean(self):
        cleaned_data = super(DatosMedicosEnfermedadForm, self).clean()
        archivomedico = self.files.get('archivomedico', None)
        if archivomedico is not None:
            if archivomedico.content_type != 'application/pdf':
                self.add_error('archivomedico', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivomedico.size > 15000000:
                self.add_error('archivomedico', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class DatosMedicosCovidForm(MY_Form):
    recibiovacuna = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    recibiodosiscompleta = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    deseavacunarse = forms.BooleanField(required=False, initial=False, widget=forms.CheckboxInput())
    tipovacuna = forms.ModelChoiceField(required=False, queryset=TipoVacunaCovid.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo de vacuna (requerido)'})
    certificado = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el certificado de vacunación (requerido)'})

    def initQuerySet(self, data):
        tipovacuna = data.get('tipovacuna', None)
        if tipovacuna:
            self.fields['tipovacuna'].queryset = TipoVacunaCovid.objects.filter(pk=tipovacuna)

    def clean(self):
        cleaned_data = super(DatosMedicosCovidForm, self).clean()
        certificado = self.files.get('certificado', None)
        if certificado is not None:
            if certificado.content_type != 'application/pdf':
                self.add_error('certificado', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif certificado.size > 15000000:
                self.add_error('certificado', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class FormacionAcademicaBachillerForm(MY_Form):
    titulo = forms.ModelChoiceField(required=True, queryset=Titulo.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione un titulo (requerido)'})
    colegio = forms.ModelChoiceField(required=True, queryset=Colegio.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione un titulo (requerido)'})
    calificacion = forms.FloatField(required=True, widget=forms.TextInput(), error_messages={'required': 'Ingrese la calificación con la que se graduo (requerido)'})
    anioinicioperiodograduacion = forms.IntegerField(required=True, widget=forms.TextInput(), error_messages={'required': 'Ingrese el año que ingreso a estudiar (requerido)'})
    aniofinperiodograduacion = forms.IntegerField(required=False, widget=forms.TextInput(), error_messages={'required': 'Ingrese el año que finalizo (requerido)'})
    actagrado = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba la acta de grado (requerido)'})
    reconocimientoacademico = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el acta de reconocimiento académico (requerido)'})

    def initQuerySet(self, data):
        titulo = data.get('titulo', None)
        colegio = data.get('colegio', None)
        if titulo:
            self.fields['titulo'].queryset = Titulo.objects.filter(pk=titulo)
        if colegio:
            self.fields['colegio'].queryset = Colegio.objects.filter(pk=colegio)

    def clean(self):
        cleaned_data = super(FormacionAcademicaBachillerForm, self).clean()
        actagrado = self.files.get('actagrado', None)
        if actagrado is not None:
            if actagrado.content_type != 'application/pdf':
                self.add_error('actagrado', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif actagrado.size > 15000000:
                self.add_error('actagrado', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        reconocimientoacademico = self.files.get('reconocimientoacademico', None)
        if reconocimientoacademico is not None:
            if reconocimientoacademico.content_type != 'application/pdf':
                self.add_error('reconocimientoacademico', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif reconocimientoacademico.size > 15000000:
                self.add_error('reconocimientoacademico', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        calificacion = cleaned_data.get('calificacion', 0)
        if calificacion <= 0 or calificacion > 100:
            self.add_error('calificacion', ValidationError(u'La calificación debe ser mayor a cero y menor a 100'))
        return cleaned_data


class FormacionAcademicaSuperiorForm(MY_Form):
    titulo = forms.ModelChoiceField(required=True, queryset=Titulo.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione un titulo (requerido)'})
    institucion = forms.ModelChoiceField(required=True, queryset=InstitucionEducacionSuperior.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la IES (requerido)'})
    areatitulo = forms.ModelChoiceField(required=True, queryset=AreaTitulo.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione una área (requerido)'})
    pais = forms.ModelChoiceField(required=True, queryset=Pais.objects.none(), widget=forms.Select(), error_messages={'required': 'Seleccione el país (requerido)'})
    provincia = forms.ModelChoiceField(required=False, queryset=Provincia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    canton = forms.ModelChoiceField(required=False, queryset=Canton.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    parroquia = forms.ModelChoiceField(required=False, queryset=Parroquia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    fechainicio = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese una fecha de inicio de estudios (requerido)'})
    cursando = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    fechaobtencion = forms.DateField(required=False, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese una fecha de obtención (requerido)'})
    fechaegresado = forms.DateField(required=False, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese una fecha de egresado (requerido)'})
    registro = forms.CharField(required=False, initial='', max_length=50, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 50 caracteres', 'required': 'Ingrese el número de registro que emite la SENESCYT (requerido)'})
    fecharegistro = forms.DateField(required=False, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha de registro de la SENESCYT (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el titulo (requerido)'})
    registroarchivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba certificado de SENESCYT (requerido)'})

    def initQuerySet(self, data):
        titulo = data.get('titulo', None)
        institucion = data.get('institucion', None)
        areatitulo = data.get('areatitulo', None)
        pais = data.get('pais', None)
        provincia = data.get('provincia', None)
        canton = data.get('canton', None)
        parroquia = data.get('parroquia', None)
        cursando = data.get('cursando', 'false') == 'true'
        if titulo:
            self.fields['titulo'].queryset = Titulo.objects.filter(pk=titulo)
        if institucion:
            self.fields['institucion'].queryset = InstitucionEducacionSuperior.objects.filter(pk=institucion)
        if areatitulo:
            self.fields['areatitulo'].queryset = AreaTitulo.objects.filter(pk=areatitulo)
        if pais:
            self.fields['pais'].queryset = Pais.objects.filter(pk=pais)
        if provincia:
            self.fields['provincia'].queryset = Provincia.objects.filter(pk=provincia)
        if canton:
            self.fields['canton'].queryset = Canton.objects.filter(pk=canton)
        if parroquia:
            self.fields['parroquia'].queryset = Parroquia.objects.filter(pk=parroquia)
        if cursando is False:
            self.fields['fechaobtencion'].required = False
            self.fields['fechaegresado'].required = False
            self.fields['registro'].required = True
            self.fields['fecharegistro'].required = True

    def clean(self):
        cleaned_data = super(FormacionAcademicaSuperiorForm, self).clean()
        pais = cleaned_data.get('pais', None)
        provincia = cleaned_data.get('provincia', None)
        canton = cleaned_data.get('canton', None)
        parroquia = cleaned_data.get('parroquia', None)
        archivo = self.files.get('archivo', None)
        registroarchivo = self.files.get('registroarchivo', None)
        if archivo is not None:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        if registroarchivo is not None:
            if registroarchivo.content_type != 'application/pdf':
                self.add_error('registroarchivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif registroarchivo.size > 15000000:
                self.add_error('registroarchivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        if pais is None:
            self.add_error('pais', ValidationError('Seleccione el pais (requerido)'))
        else:
            if pais.pk == 1:
                if provincia is None:
                    self.add_error('provincia', ValidationError(u'Seleccione la provincia (requerido)'))
                if canton is None:
                    self.add_error('canton', ValidationError(u'Seleccione el canton (requerido)'))
                if parroquia is None:
                    self.add_error('parroquia', ValidationError(u'Seleccione la parroquia (requerido)'))
        return cleaned_data


class FormacionAcademicaCapacitacionForm(MY_Form):
    institucion = forms.CharField(max_length=200, required=True, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Ingrese la institución (requerido)'})
    nombre = forms.CharField(max_length=200, required=True, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Ingrese el nombre del evento (requerido)'})
    descripcion = forms.CharField(required=True, widget=forms.Textarea(), error_messages={'required': 'Ingrese una descripción del evento (requerido)'})
    tipo = forms.ChoiceField(choices=TIPO_CAPACITACION_P, required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo de evento (requerido)'})
    tipocurso = forms.ModelChoiceField(queryset=TipoCurso.objects.none(), required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo de capacitación o actualización científica (requerido)'})
    tipoparticipacion = forms.ModelChoiceField(queryset=TipoParticipacion.objects.none(), required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo de certificación (requerido)'})
    tipocapacitacion = forms.ModelChoiceField(queryset=TipoCapacitacion.objects.none(), required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione Programado plan Institucional (requerido)'})
    modalidad = forms.ChoiceField(required=True, choices=MODALIDAD_CAPACITACION, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la modalidad (requerido)'})
    otramodalidad = forms.CharField(label=u'Otra Modalidad', max_length=600, required=False, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 600 caracteres', 'required': 'Ingrese otra modalidad (requerido)'})
    tipocertificacion = forms.ModelChoiceField(queryset=TipoCertificacion.objects.none(), required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione tipo de planificación (requerido)'})
    contexto = forms.ModelChoiceField(queryset=ContextoCapacitacion.objects.none(), required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione Contexto de la capacitación/formación (requerido)'})
    detallecontexto = forms.ModelChoiceField(queryset=DetalleContextoCapacitacion.objects.none(), required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione Detalle de contexto (requerido)'})
    areaconocimiento = forms.ModelChoiceField(queryset=AreaConocimientoTitulacion.objects.none(), required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione Area de conocimiento (requerido)'})
    subareaconocimiento = forms.ModelChoiceField(queryset=SubAreaConocimientoTitulacion.objects.none(), required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione Sub area de conocimiento (requerido)'})
    subareaespecificaconocimiento = forms.ModelChoiceField(queryset=SubAreaEspecificaConocimientoTitulacion.objects.none(), required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione Sub area especifica conocimiento (requerido)'})
    auspiciante = forms.CharField(max_length=200, required=False, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Ingrese el auspiciante (requerido)'})
    expositor = forms.CharField(max_length=200, required=False, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 200 caracteres', 'required': 'Ingrese el expositor (requerido)'})
    pais = forms.ModelChoiceField(queryset=Pais.objects.none(), required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el país (requerido)'})
    provincia = forms.ModelChoiceField(queryset=Provincia.objects.none(), required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la provincia o estado (requerido)'})
    canton = forms.ModelChoiceField(queryset=Canton.objects.none(), required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el Cantón / Ciudad (requerido)'})
    parroquia = forms.ModelChoiceField(queryset=Parroquia.objects.none(), required=False, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la Parroquia (requerido)'})
    fechainicio = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese una fecha de inicio (requerido)'})
    fechafin = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese una fecha fin (requerido)'})
    horas = forms.FloatField(required=True, widget=forms.TextInput({}), error_messages={'required': 'Ingrese el número de horas (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el archivo del evento (requerido)'})

    def initQuerySet(self, data):
        tipocurso = int(data.get('tipocurso', '0'))
        if tipocurso:
            self.fields['tipocurso'].queryset = TipoCurso.objects.filter(pk=tipocurso)
        tipoparticipacion = int(data.get('tipoparticipacion', '0'))
        if tipoparticipacion:
            self.fields['tipoparticipacion'].queryset = TipoParticipacion.objects.filter(pk=tipoparticipacion)
        tipocapacitacion = int(data.get('tipocapacitacion', '0'))
        if tipocapacitacion:
            self.fields['tipocapacitacion'].queryset = TipoCapacitacion.objects.filter(pk=tipocapacitacion)
        tipocertificacion = int(data.get('tipocertificacion', '0'))
        if tipocertificacion:
            self.fields['tipocertificacion'].queryset = TipoCertificacion.objects.filter(pk=tipocertificacion)
        contexto = int(data.get('contexto', '0'))
        if contexto:
            self.fields['contexto'].queryset = ContextoCapacitacion.objects.filter(pk=contexto)
        detallecontexto = int(data.get('detallecontexto', '0'))
        if detallecontexto:
            self.fields['detallecontexto'].queryset = DetalleContextoCapacitacion.objects.filter(pk=detallecontexto)
        areaconocimiento = int(data.get('areaconocimiento', '0'))
        if areaconocimiento:
            self.fields['areaconocimiento'].queryset = AreaConocimientoTitulacion.objects.filter(pk=areaconocimiento)
        subareaconocimiento = int(data.get('subareaconocimiento', '0'))
        if subareaconocimiento:
            self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(pk=subareaconocimiento)
        subareaespecificaconocimiento = int(data.get('subareaespecificaconocimiento', '0'))
        if subareaespecificaconocimiento:
            self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(pk=subareaespecificaconocimiento)
        pais = int(data.get('pais', '0'))
        if pais:
            self.fields['pais'].queryset = Pais.objects.filter(pk=pais)
        provincia = int(data.get('provincia', '0'))
        if provincia:
            self.fields['provincia'].queryset = Provincia.objects.filter(pk=provincia)
        canton = int(data.get('canton', '0'))
        if canton:
            self.fields['canton'].queryset = Canton.objects.filter(pk=canton)
        parroquia = int(data.get('parroquia', '0'))
        if parroquia:
            self.fields['parroquia'].queryset = Parroquia.objects.filter(pk=parroquia)
        modalidad = int(data.get('modalidad', '0'))
        if modalidad:
            # if type(modalidad) is not int:
            #     modalidad = int(modalidad)
            if modalidad == 4:
                self.fields['otramodalidad'].required = True

    def clean(self):
        cleaned_data = super(FormacionAcademicaCapacitacionForm, self).clean()
        archivo = self.files.get('archivo', None)
        if archivo is not None:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class FormacionAcademicaCertificacionForm(MY_Form):
    nombres = forms.CharField(max_length=500, required=True, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 500 caracteres', 'required': 'Ingrese el Nombre de la certificación (requerido)'})
    autoridad_emisora = forms.CharField(max_length=500, required=True, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 500 caracteres', 'required': 'Ingrese la Autoridad emisora de la certificación (requerido)'})
    numerolicencia = forms.CharField(max_length=500, required=True, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 500 caracteres', 'required': 'Ingrese el Número de la licencia (requerido)'})
    enlace = forms.CharField(max_length=500, required=True, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 500 caracteres', 'required': 'Ingrese URL de la certificación (requerido)'})
    fechadesde = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha desde (requerido)'})
    fechahasta = forms.DateField(required=False, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha hasta (requerido)'})
    vigente = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el archivo de la certificación (requerido)'})

    def initQuerySet(self, data):
        vigente = data.get('vigente', 'false') == 'true'
        if vigente is False:
            self.fields['fechahasta'].required = True

    def clean(self):
        cleaned_data = super(FormacionAcademicaCertificacionForm, self).clean()
        archivo = self.files.get('archivo', None)
        if archivo is not None:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class FormacionAcademicaIdiomaForm(MY_Form):
    idioma = forms.ModelChoiceField(required=True, queryset=Idioma.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el idioma (requerido)'})
    institucioncerti = forms.ModelChoiceField(required=False, queryset=InstitucionCertificadora.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la institución certificadora (requerido)'})
    nivelsuficencia = forms.ModelChoiceField(required=True, queryset=NivelSuficencia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el nivel de suficiencia  (requerido)'})
    validainst = forms.BooleanField(required=False, widget=forms.CheckboxInput())
    otrainstitucion = forms.CharField(required=False, widget=forms.Textarea(), error_messages={'required': 'Ingrese la institución certificadora (requerido)'})
    fechacerti = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha de certificación (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el archivo de la certificación (requerido)'})

    def initQuerySet(self, data):
        validainst = data.get('validainst', 'false') == 'true'
        if validainst:
            self.fields['otrainstitucion'].required = True
            self.fields['institucioncerti'].required = False
        else:
            self.fields['otrainstitucion'].required = False
            self.fields['institucioncerti'].required = True
        institucioncerti = int(data.get('institucioncerti', '0'))
        if institucioncerti:
            self.fields['institucioncerti'].queryset = InstitucionCertificadora.objects.filter(pk=institucioncerti)
        idioma = int(data.get('idioma', '0'))
        if idioma:
            self.fields['idioma'].queryset = Idioma.objects.filter(pk=idioma)
        nivelsuficencia = int(data.get('nivelsuficencia', '0'))
        if nivelsuficencia:
            self.fields['nivelsuficencia'].queryset = NivelSuficencia.objects.filter(pk=nivelsuficencia)

    def clean(self):
        cleaned_data = super(FormacionAcademicaIdiomaForm, self).clean()
        archivo = self.files.get('archivo', None)
        if archivo:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class DeporteCulturaArtistaForm(MY_Form):
    grupopertenece = forms.CharField(required=True, widget=forms.Textarea(), error_messages={'required': 'Ingrese al grupo que pertenece (requerido)'})
    fechainicioensayo = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha de inicio de ensayos (requerido)'})
    fechafinensayo = forms.DateField(required=False, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha fin de ensayos (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el archivo de la certificación (requerido)'})

    def initQuerySet(self, data):
        pass

    def clean(self):
        cleaned_data = super(DeporteCulturaArtistaForm, self).clean()
        fechainicioensayo = cleaned_data.get('fechainicioensayo', None)
        fechafinensayo = cleaned_data.get('fechafinensayo', None)
        if fechainicioensayo and fechafinensayo:
            if fechainicioensayo > fechafinensayo:
                self.add_error('fechainicioensayo', ValidationError(u'La fecha de inicio de ensayo debe ser menor o igual a la fecha de fin'))
        archivo = self.files.get('archivo', None)
        if archivo:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class DeporteCulturaDeportistaForm(MY_Form):
    representapais = forms.ChoiceField(choices=VALOR_SI_NO, required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Representa al ecuador (requerido)'})
    evento = forms.CharField(max_length=300, required=True, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 300 caracteres', 'required': 'Ingrese el nombre del evento (requerido)'})
    paisevento = forms.ModelChoiceField(queryset=Pais.objects.none(), required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el país (requerido)'})
    equiporepresenta = forms.CharField(max_length=300, required=True, widget=forms.TextInput(), error_messages={'max_length': 'Múmero máximo de 300 caracteres', 'required': 'Ingrese el nombre del equipo o institución que representa (requerido)'})
    fechainicioevento = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha de inicio de evento (requerido)'})
    fechafinevento = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha fin de evento (requerido)'})
    fechainicioentrena = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha de inicio entrenar (requerido)'})
    fechafinentrena = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha fin entrenar (requerido)'})
    archivoevento = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el archivo de la certificación (requerido)'})
    archivoentrena = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el archivo de la certificación (requerido)'})

    def initQuerySet(self, data):
        paisevento = int(data.get('paisevento', '0'))
        if paisevento:
            self.fields['paisevento'].queryset = Pais.objects.filter(pk=paisevento)

    def clean(self):
        cleaned_data = super(DeporteCulturaDeportistaForm, self).clean()
        fechainicioevento = cleaned_data.get('fechainicioevento', None)
        fechafinevento = cleaned_data.get('fechafinevento', None)
        if fechainicioevento and fechafinevento:
            if fechainicioevento > fechafinevento:
                self.add_error('fechainicioevento', ValidationError(u'La fecha de inicio de evento debe ser menor o igual a la fecha de fin'))
        fechainicioentrena = cleaned_data.get('fechainicioentrena', None)
        fechafinentrena = cleaned_data.get('fechafinentrena', None)
        if fechainicioentrena and fechafinentrena:
            if fechainicioentrena > fechafinentrena:
                self.add_error('fechainicioentrena', ValidationError(u'La fecha de inicio de entrenar debe ser menor o igual a la fecha de fin'))

        archivoevento = self.files.get('archivoevento', None)
        if archivoevento:
            if archivoevento.content_type != 'application/pdf':
                self.add_error('archivoevento', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivoevento.size > 15000000:
                self.add_error('archivoevento', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        archivoentrena = self.files.get('archivoentrena', None)
        if archivoentrena:
            if archivoentrena.content_type != 'application/pdf':
                self.add_error('archivoentrena', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivoentrena.size > 15000000:
                self.add_error('archivoentrena', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data


class FormacionAcademicaBecaExternaForm(MY_Form):
    tipoinstitucion = forms.ChoiceField(choices=TIPO_INSTITUCION_BECA, required=True, widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione tipo de institución de beca (requerido)'})
    institucion = forms.ModelChoiceField(required=True, queryset=InstitucionBeca.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione la institución (requerido)'})
    fechainicio = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha de inicio (requerido)'})
    fechafin = forms.DateField(required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d'), error_messages={'required': 'Ingrese la fecha fin (requerido)'})
    archivo = ExtFileField(required=False, ext_whitelist=(".pdf",), max_upload_size=15000000, error_messages={'required': 'Suba el certificado (requerido)'})

    def initQuerySet(self, data):
        institucion = int(data.get('institucion', '0'))
        if institucion:
            self.fields['institucion'].queryset = InstitucionBeca.objects.filter(pk=institucion)

    def clean(self):
        cleaned_data = super(FormacionAcademicaBecaExternaForm, self).clean()
        fechainicio = cleaned_data.get('fechainicio', None)
        fechafin = cleaned_data.get('fechafin', None)
        if fechainicio and fechafin:
            if fechainicio > fechafin:
                self.add_error('fechainicio', ValidationError(u'La fecha de inicio debe ser menor o igual a la fecha de fin'))
        archivo = self.files.get('archivo', None)
        if archivo:
            if archivo.content_type != 'application/pdf':
                self.add_error('archivo', ValidationError(u'Archivo, solo se permiten archivos formato pdf (requerido)'))
            elif archivo.size > 15000000:
                self.add_error('archivo', ValidationError(u'Archivo, el tamaño del archivo es mayor a 15 Mb (requerido)'))
        return cleaned_data
