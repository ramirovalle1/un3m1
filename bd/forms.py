# -*- coding: UTF-8 -*-
import json
import os
from datetime import datetime, timedelta
from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib.auth.models import Group, User, Permission
from django.db.models import Q
from django.forms.models import ModelForm, ModelChoiceField, model_to_dict
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from django.db import models, connection, connections

from automatiza.models import PRIORIDAD, TIPO_REQUERIMIENTO_AUTOMATIZA
from bd.models import PeriodoGrupo, TIPO_PERIODO_CRONTAB_CHOICES, PeriodoCrontab, APP_LABEL_TEMPLATE, CategoriaIndice, \
    ContenidoDocumento, ContenidoIndice, ProcesoSCRUM, APP_LABEL, PRIORIDAD_REQUERIMIENTO, IncidenciaSCRUM, \
    ComentarioIncidenciaSCRUM, \
    ProcesoOpcionSistema, TipoOpcionSistema, EquipoSCRUM, TIPO_EJECUTOR, PythonProcess, ESTADO_REQUERIMIENTO, \
    ESTADO_INDICADOR_POA
from certi.models import ConfiguracionCarnet, TIPO_PERFIL, TIPO_VALIDACION_CARNET, TIPO_CARNET
from core.custom_forms import FormModeloBase
from matricula.models import TIPO_MATRICULA_CHOICES, PeriodoMatricula, MotivoMatriculaEspecial, \
    MOTIVO_MATRICULA_CHOICES, TIPO_ENTIDAD_MATRICULA_ESPECIAL_CHOICES, TIPO_VALIDACION_MATRICULA_ESPECIAL_CHOICES, \
    EstadoMatriculaEspecial, ACCION_MATRICULA_ESPECIAL_CHOICES, ProcesoMatriculaEspecial, \
    ACCION_ESTADO_MATRICULA_ESPECIAL_CHOICES, ACCION_ESTADO_RETIRO_MATRICULA_CHOICES, MotivoRetiroMatricula, \
    TIPO_VALIDACION_RETIRO_MATRICULA_CHOICES, TIPO_ENTIDAD_RETIRO_MATRICULA_CHOICES, EstadoRetiroMatricula, \
    ACCION_RETIRO_MATRICULA_CHOICES, TIPO_TIEMPO_ATENCION, ConfiguracionUltimaMatricula
from sga.models import ProfesorMateria, MateriaAsignada, DetalleSilaboSemanalTema, Profesor, Materia, Modulo, Sexo, \
    Pais, Provincia, Canton, Parroquia, TIPO_PERSONA, Externo, Persona, Coordinacion, Carrera, TipoPeriodo, Reporte, \
    Periodo, TIPO_SOLICITUDINCONVENIENTE, TIPOS_PARAMETRO_VARIABLE, NivelMalla, TYPE_DAYS_NO_WORKING, \
    TYPE_ACTION_NO_WORKING, ROLES_MODULO_SISTEMA, TIPO_CALCULO_MATRICULA, Malla, CategoriaReporte, ModuloCategorias, \
    Sesion
from sagest.models import OpcionSistema, Departamento, TipoOtroRubro, CuentaBanco, SeccionDepartamento
from django.contrib.auth.models import Group
from sga.forms import ExtFileField
from django.forms import ValidationError
from inno.models import HorarioTutoriaAcademica, TOPICO_SOLICITUD_TUTORIA, TIPO_PERIODO_MODALIDAD_CHOICES, \
    PeriodoAcademia, ProcesoSolicitudClaseDiferido, ConfiguracionCalculoMatricula
from soap.models import TIPO_SERVICIO_SOAP, TIPO_AMBIENTE


class CheckboxSelectMultipleCustom(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(CheckboxSelectMultipleCustom, self).render(*args, **kwargs)
        return mark_safe(output.replace(u'<ul>',
                                        u'<div class="custom-multiselect" style="width: 600px;overflow: scroll"><ul>').replace(
            u'</ul>', u'</ul></div>').replace(u'<li>', u'').replace(u'</li>', u'').replace(u'<label',
                                                                                           u'<div style="width: 900px"><li').replace(
            u'</label>', u'</li></div>'))


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


class FixedForm(ModelForm):
    date_fields = []

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        for f in self.date_fields:
            self.fields[f].widget.format = '%d-%m-%Y'
            self.fields[f].input_formats = ['%d-%m-%Y']


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



BASE_CONEXION = (
    (1, u'SGA'),
    (2, u'EPUNEMI'),
    (3, u'MOODLE PREGRADO A'),
    (11, u'MOODLE PREGRADO B'),
    (4, u'MOODLE ADMISIÓN'),
    (5, u'MOODLE POSGRADO'),
    (6, u'POSTULATE'),
    (7, u'DEVA'),
    (8, u'ADMISIÓN'),
    (9, u'MOODLE PREINSCRIPCION ADMISIÓN'),
    (10, u'UXPLORA'),
)


class QueryForm(forms.Form):
    base = forms.ChoiceField(label=u'Conexión', choices=BASE_CONEXION, required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    query = forms.CharField(label=u'Query', max_length=1000000000, required=True, widget=forms.Textarea({'rows': '20', 'class': 'normal-input'}))


class UserSystemForm(forms.Form):
    username = forms.CharField(label=u'Usuario', max_length=150, required=True, widget=forms.TextInput(attrs={'formwidth': 'span6'}))
    email = forms.CharField(label=u'Correo', max_length=250, required=False, widget=forms.TextInput(attrs={'formwidth': 'span6'}))
    first_name = forms.CharField(label=u'Nombres', max_length=30, required=False, widget=forms.TextInput(attrs={'formwidth': 'span6'}))
    last_name = forms.CharField(label=u'Apellidos', max_length=30, required=False, widget=forms.TextInput(attrs={'formwidth': 'span6'}))
    is_staff = forms.BooleanField(initial=False, label=u"Es Personal?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6'}))
    is_active = forms.BooleanField(initial=True, label=u"Activo?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6'}))

    def set_initial(self, eUser):
        if Persona.objects.filter(usuario=eUser).exists():
            ePersona = Persona.objects.get(usuario=eUser)
            if ePersona.emailinst:
                eUser.email = ePersona.emailinst if not eUser.email else eUser.email
            elif ePersona.email:
                eUser.email = ePersona.email if not eUser.email else eUser.email
            eUser.first_name = ePersona.nombres if not eUser.first_name else eUser.first_name
            eUser.last_name = f"{ePersona.apellido1} {ePersona.apellido2}".strip() if not eUser.last_name else eUser.last_name

        self.initial = model_to_dict(eUser)

    def edit(self):
        self.fields['username'].widget.attrs['readonly'] = True
        self.fields['username'].widget.attrs['disabled'] = True

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class UserPasswordForm(forms.Form):
    password = forms.CharField(label=u'Contraseña', max_length=128, required=True, widget=forms.PasswordInput(attrs={'formwidth': 'span6'}))
    password2 = forms.CharField(label=u'Corfimar contraseña', max_length=128, required=True, widget=forms.PasswordInput(attrs={'formwidth': 'span6'}))


class ModuloForm(forms.Form):
    categorias = forms.ModelMultipleChoiceField(label=u'Categorias', queryset=ModuloCategorias.objects.all(), required=False, widget=forms.SelectMultiple(attrs={'formwidth': '100%'}))
    url = forms.CharField(max_length=100, label=u'URL', required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    nombre = forms.CharField(max_length=100, label=u'Nombre', required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    icono = forms.CharField(max_length=200, label=u'Icono', required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    roles = forms.MultipleChoiceField(required=False, choices=ROLES_MODULO_SISTEMA, label=u'Roles', widget=forms.SelectMultiple(attrs={"formwidth": "100%"}))
    activo = forms.BooleanField(label=u'Activo', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    sga = forms.BooleanField(label=u'Activo para SGA', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    sagest = forms.BooleanField(label=u'Activo para SAGEST', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    posgrado = forms.BooleanField(label=u'Activo para POSGRADO', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    api = forms.BooleanField(label=u'Activo para API', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    api_key = forms.CharField(max_length=100, label=u'API KEY', required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '50%'}))

    def __init__(self, *args, **kwargs):
        super(ModuloForm, self).__init__(*args, **kwargs)
        roles = self.fields['roles'].initial
        idm = args[0].get('id') if args else None

        if not roles and idm:
            del self.fields['roles']

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class GrupoForm(forms.Form):
    name = forms.CharField(max_length=100, label=u'Nombre', required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '100%'}))

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class ModuloGrupoForm(forms.Form):
    nombre = forms.CharField(max_length=100, label=u'Nombre', required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '35%'}))
    descripcion = forms.CharField(max_length=200, label=u"Descripción", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '65%'}))
    modulos = forms.ModelMultipleChoiceField(label=u'Módulos', required=False, queryset=Modulo.objects.all(), widget=forms.CheckboxSelectMultiple(attrs={'class': 'js-switch', 'formwidth': '50%', 'separator': 'true', 'separatortitle': 'Relacione módulos y grupos', 'searchMultipleCheckbox': 'true'}))
    grupos = forms.ModelMultipleChoiceField(label=u'Grupos', required=False, queryset=Group.objects.all(), widget=forms.CheckboxSelectMultiple(attrs={'class': 'js-switch', 'formwidth': '50%', 'searchMultipleCheckbox': 'true'}))

    def deleteFields(self):
        del self.fields['modulos']
        del self.fields['grupos']

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True
            # if field in ['grupos', 'modulos']:
            #     self.fields[field].widget.attrs = {'checked': 'checked', 'readonly': 'readonly', 'style': 'display:none;'}
            #     self.fields[field].help_text = ''



TIPO_DOCUMENTO = (
    (1, u'CEDULA'),
    (2, u'PASAPORTE'),
    (3, u"RUC"),
)


class PersonSystemForm(forms.Form):
    tipo_documento = forms.ChoiceField(label=u'Tipo de documento ', choices=TIPO_DOCUMENTO, required=False, widget=forms.Select(attrs={}))
    documento = forms.CharField(label=u"Documento", max_length=20, required=False, widget=forms.TextInput(attrs={}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(), widget=forms.Select(attrs={}))
    nacimiento = forms.DateField(label=u"Fecha Nacimiento", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), required=False)
    contribuyenteespecial = forms.BooleanField(initial=False, label=u"Es Contrib. Espec.", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', }))
    nombreempresa = forms.CharField(label=u"Nombre Empresa", max_length=100, required=False, widget=forms.TextInput(attrs={}))
    nombrecomercial = forms.CharField(label=u"Nombre Comercial", max_length=200, required=False, widget=forms.TextInput(attrs={}))
    nombres = forms.CharField(label=u"Nombres", max_length=100, required=False, widget=forms.TextInput(attrs={}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={}))
    paisnacimiento = forms.ModelChoiceField(label=u"País nacimiento", queryset=Pais.objects.all(), required=False, widget=forms.Select(attrs={}))
    provincianacimiento = forms.ModelChoiceField(label=u"Provincia nacimiento", queryset=Provincia.objects.all(), required=False, widget=forms.Select(attrs={}))
    cantonnacimiento = forms.ModelChoiceField(label=u"Canton nacimiento", queryset=Canton.objects.all(), required=False, widget=forms.Select(attrs={}))
    parroquianacimiento = forms.ModelChoiceField(label=u"Parroquia nacimiento", queryset=Parroquia.objects.all(), required=False, widget=forms.Select(attrs={}))
    pais = forms.ModelChoiceField(label=u"País residencia", queryset=Pais.objects.all(), required=False, widget=forms.Select(attrs={}))
    provincia = forms.ModelChoiceField(label=u"Provincia residencia", queryset=Provincia.objects.all(), required=False, widget=forms.Select(attrs={}))
    canton = forms.ModelChoiceField(label=u"Canton residencia", queryset=Canton.objects.all(), required=False, widget=forms.Select(attrs={}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia residencia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select(attrs={}))
    ciudad = forms.CharField(label=u"Ciudad", max_length=50, required=False, widget=forms.TextInput(attrs={}))
    sector = forms.CharField(label=u"Sector", max_length=100, required=False, widget=forms.TextInput(attrs={}))
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False, widget=forms.TextInput(attrs={}))
    direccion2 = forms.CharField(label=u"Calle Secundaria", max_length=100, required=False, widget=forms.TextInput(attrs={}))
    num_direccion = forms.CharField(label=u"Numero Domicilio", max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefono = forms.CharField(label=u"Telefono Movil", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    telefono_conv = forms.CharField(label=u"Telefono Fijo", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    email = forms.CharField(label=u"Correo Electronico", max_length=240, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    nombrecontacto = forms.CharField(label=u"Nombre Representante", required=False, max_length=200, widget=forms.TextInput(attrs={}))
    telefonocontacto = forms.CharField(label=u"Telefono Representante", max_length=100, required=False, widget=forms.TextInput(attrs={}))

    def tipo_persona(self, tipo):
        # NATURAL
        if tipo == 1:
            self.fields['tipo_documento'].choices = TIPO_DOCUMENTO[0:2]
            self.fields['tipo_documento'].widget.attrs['separator2'] = True
            self.fields['tipo_documento'].widget.attrs['separatortitle'] = 'Datos personales'
            self.fields['tipo_documento'].widget.attrs['formwidth'] = 'span3'
            self.fields['tipo_documento'].required = True
            self.fields['documento'].widget.attrs['formwidth'] = 'span3'
            self.fields['documento'].required = True
            self.fields['sexo'].widget.attrs['formwidth'] = 'span3'
            self.fields['sexo'].required = True
            self.fields['nacimiento'].widget.attrs['formwidth'] = 'span3'
            self.fields['nacimiento'].required = True
            self.fields['nombres'].widget.attrs['formwidth'] = 'span4'
            self.fields['nombres'].required = True
            self.fields['apellido1'].widget.attrs['formwidth'] = 'span4'
            self.fields['apellido1'].required = True
            self.fields['apellido2'].widget.attrs['formwidth'] = 'span4'
            self.fields['paisnacimiento'].widget.attrs['formwidth'] = 'span3'
            self.fields['paisnacimiento'].required = True
            self.fields['provincianacimiento'].widget.attrs['formwidth'] = 'span3'
            self.fields['provincianacimiento'].required = True
            self.fields['cantonnacimiento'].widget.attrs['formwidth'] = 'span3'
            self.fields['parroquianacimiento'].widget.attrs['formwidth'] = 'span3'
            self.fields['pais'].widget.attrs['formwidth'] = 'span3'
            self.fields['pais'].widget.attrs['separator2'] = True
            self.fields['pais'].widget.attrs['separatortitle'] = 'Dirección de domicilio'
            self.fields['pais'].required = True
            self.fields['provincia'].widget.attrs['formwidth'] = 'span3'
            self.fields['provincia'].required = True
            self.fields['canton'].widget.attrs['formwidth'] = 'span3'
            self.fields['parroquia'].widget.attrs['formwidth'] = 'span3'
            self.fields['sector'].widget.attrs['formwidth'] = 'span2'
            self.fields['sector'].required = True
            self.fields['ciudad'].widget.attrs['formwidth'] = 'span2'
            self.fields['ciudad'].required = True
            self.fields['direccion'].widget.attrs['formwidth'] = 'span3'
            self.fields['direccion'].required = True
            self.fields['direccion2'].widget.attrs['formwidth'] = 'span3'
            self.fields['direccion2'].required = True
            self.fields['num_direccion'].widget.attrs['formwidth'] = 'span2'
            self.fields['num_direccion'].required = True
            self.fields['telefono'].widget.attrs['formwidth'] = 'span3'
            self.fields['telefono_conv'].widget.attrs['formwidth'] = 'span3'
            self.fields['email'].widget.attrs['formwidth'] = 'span6'
            self.fields['email'].required = True
            del self.fields['nombreempresa']
            del self.fields['nombrecomercial']
            del self.fields['contribuyenteespecial']
            del self.fields['nombrecontacto']
            del self.fields['telefonocontacto']
        else:
            self.fields['tipo_documento'].choices = TIPO_DOCUMENTO[2:3]
            self.fields['tipo_documento'].widget.attrs['separator2'] = True
            self.fields['tipo_documento'].widget.attrs['separatortitle'] = 'Datos de la empresa'
            self.fields['tipo_documento'].widget.attrs['formwidth'] = 'span3'
            self.fields['documento'].widget.attrs['formwidth'] = 'span3'
            self.fields['documento'].required = True
            self.fields['nacimiento'].widget.attrs['formwidth'] = 'span3'
            self.fields['nacimiento'].label = u"Fecha de Constitución"
            self.fields['contribuyenteespecial'].widget.attrs['formwidth'] = 'span3'
            self.fields['nombreempresa'].required = True
            self.fields['nombreempresa'].widget.attrs['separator'] = True
            self.fields['nombreempresa'].widget.attrs['formwidth'] = 'span6'
            self.fields['nombrecomercial'].widget.attrs['formwidth'] = 'span6'
            self.fields['pais'].widget.attrs['formwidth'] = 'span3'
            self.fields['pais'].widget.attrs['separator2'] = True
            self.fields['pais'].widget.attrs['separatortitle'] = 'Dirección de domicilio'
            self.fields['pais'].required = True
            self.fields['provincia'].widget.attrs['formwidth'] = 'span3'
            self.fields['provincia'].required = True
            self.fields['canton'].widget.attrs['formwidth'] = 'span3'
            self.fields['parroquia'].widget.attrs['formwidth'] = 'span3'
            self.fields['ciudad'].widget.attrs['formwidth'] = 'span2'
            self.fields['ciudad'].required = True
            self.fields['sector'].widget.attrs['formwidth'] = 'span2'
            self.fields['sector'].required = True
            self.fields['direccion'].widget.attrs['formwidth'] = 'span3'
            self.fields['direccion'].required = True
            self.fields['direccion2'].widget.attrs['formwidth'] = 'span3'
            self.fields['direccion2'].required = True
            self.fields['num_direccion'].widget.attrs['formwidth'] = 'span2'
            self.fields['num_direccion'].required = True
            self.fields['telefono'].widget.attrs['formwidth'] = 'span3'
            self.fields['telefono_conv'].widget.attrs['formwidth'] = 'span3'
            self.fields['email'].widget.attrs['formwidth'] = 'span6'
            self.fields['email'].required = True
            self.fields['nombrecontacto'].widget.attrs['formwidth'] = 'span6'
            self.fields['nombrecontacto'].required = True
            self.fields['nombrecontacto'].widget.attrs['separator2'] = True
            self.fields['nombrecontacto'].widget.attrs['separatortitle'] = 'Representante legal'
            self.fields['telefonocontacto'].widget.attrs['formwidth'] = 'span6'
            self.fields['telefonocontacto'].required = True
            del self.fields['nombres']
            del self.fields['apellido1']
            del self.fields['apellido2']
            del self.fields['sexo']
            del self.fields['paisnacimiento']
            del self.fields['provincianacimiento']
            del self.fields['cantonnacimiento']
            del self.fields['parroquianacimiento']

    def set_initial(self, ePersona):
        self.fields['nacimiento'].initial = ePersona.nacimiento
        self.fields['pais'].initial = ePersona.pais
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=ePersona.pais)
        self.fields['provincia'].initial = ePersona.provincia
        self.fields['canton'].queryset = Canton.objects.filter(provincia=ePersona.provincia)
        self.fields['canton'].initial = ePersona.canton
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=ePersona.canton)
        self.fields['parroquia'].initial = ePersona.parroquia
        self.fields['sector'].initial = ePersona.sector
        self.fields['direccion'].initial = ePersona.direccion
        self.fields['direccion2'].initial = ePersona.direccion2
        self.fields['num_direccion'].initial = ePersona.num_direccion
        self.fields['telefono'].initial = ePersona.telefono
        self.fields['telefono_conv'].initial = ePersona.telefono_conv
        self.fields['email'].initial = ePersona.email
        self.fields['ciudad'].initial = ePersona.ciudad

        if ePersona.tipopersona == 1:
            self.fields['tipo_documento'].initial = 1 if ePersona.cedula else 2
            self.fields['documento'].initial = ePersona.cedula if ePersona.cedula else ePersona.pasaporte
            self.fields['sexo'].initial = ePersona.sexo
            self.fields['nombres'].initial = ePersona.nombres
            self.fields['apellido1'].initial = ePersona.apellido1
            self.fields['apellido2'].initial = ePersona.apellido2
            self.fields['paisnacimiento'].initial = ePersona.paisnacimiento
            self.fields['provincianacimiento'].queryset = Provincia.objects.filter(pais=ePersona.paisnacimiento)
            self.fields['provincianacimiento'].initial = ePersona.provincianacimiento
            self.fields['cantonnacimiento'].queryset = Canton.objects.filter(provincia=ePersona.provincianacimiento)
            self.fields['cantonnacimiento'].initial = ePersona.cantonnacimiento
            self.fields['parroquianacimiento'].queryset = Parroquia.objects.filter(canton=ePersona.cantonnacimiento)
            self.fields['parroquianacimiento'].initial = ePersona.parroquianacimiento
        else:
            eExterno = None
            if Externo.objects.filter(persona=ePersona).exists():
                eExterno = Externo.objects.get(persona=ePersona)
            self.fields['tipo_documento'].initial = 3
            self.fields['documento'].initial = ePersona.ruc
            self.fields['contribuyenteespecial'].initial = ePersona.contribuyenteespecial
            self.fields['nombreempresa'].initial = ePersona.nombres
            self.fields['nombrecomercial'].initial = eExterno.nombrecomercial if eExterno.nombrecomercial else None
            self.fields['nombrecontacto'].initial = eExterno.nombrecontacto if eExterno.nombrecontacto else None
            self.fields['telefonocontacto'].initial = eExterno.telefonocontacto if eExterno.telefonocontacto else None

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class PerfilAccesoUsuarioForm(forms.Form):
    grupo = forms.ModelChoiceField(label=u'Grupo', queryset=Group.objects.all(), required=True, widget=forms.Select(attrs={"formwidth": "span12"}))
    coordinacion = forms.ModelChoiceField(label=u'Coordinación', queryset=Coordinacion.objects.all(), required=True, widget=forms.Select(attrs={"formwidth": "span12"}))
    carrera = forms.ModelMultipleChoiceField(label=u'Carrera', queryset=Carrera.objects.all(), required=True, widget=forms.SelectMultiple(attrs={"formwidth": "span12"}))

    def cleanCarrera(self):
        self.fields['carrera'].queryset = Carrera.objects.filter()

    def loadCarrera(self, ePerfilUser):
        self.fields['carrera'].queryset = Carrera.objects.filter(coordinacion=ePerfilUser.coordinacion)

    def set_init(self, ePerfilUser):
        self.fields['grupo'].initial = ePerfilUser.grupo
        self.fields['coordinacion'].initial = ePerfilUser.coordinacion
        self.fields['carrera'].initial = ePerfilUser.carreras_grupos_perfil_acceso_usuario()

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class PeriodoForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", required=True, max_length=200, widget=forms.TextInput({"formwidth": "span12"}))
    tipo = forms.ModelChoiceField(label=u"Tipo de periodo", queryset=TipoPeriodo.objects.all(), widget=forms.Select(attrs={'class': 'imp-50', "formwidth": "span6", "separator2": True}))
    inicio = forms.DateField(label=u"Inicio", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "separatortitle": "Fecha del periodo académico", "formwidth": "span3"}))
    fin = forms.DateField(label=u"Fin", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span3"}))
    valida_asistencia = forms.BooleanField(label=u"Validar asistencias", required=False, initial=True, widget=forms.CheckboxInput({'class': 'js-switch', "formwidth": "span4", "separator": True}))
    visiblehorario = forms.BooleanField(label=u"Visible horario", required=False, initial=True, widget=forms.CheckboxInput({'class': 'js-switch', "formwidth": "span4"}))
    marcardefecto = forms.BooleanField(label=u"Principal (Marca)", required=False, initial=False, widget=forms.CheckboxInput({'class': 'js-switch', "formwidth": "span4"}))
    inicio_agregacion = forms.DateField(label=u"Inicio agregación (Secretaria)", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4",  "separator": True}))
    limite_agregacion = forms.DateField(label=u"Limite agregación (Secretaria)", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4"}))
    limite_retiro = forms.DateField(label=u"Limite retiro (Secretaria)", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4"}))
    fecha_inicio_agregacion = forms.DateField(label=u"Inicio agregación (Estudiante)", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4", "separator": True}))
    fecha_fin_agregacion = forms.DateField(label=u"Fin agregación (Estudiante)", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4"}))
    fecha_fin_quitar = forms.DateField(label=u"Fin quitar (Estudiante)", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4"}))
    porcentaje_gratuidad = forms.IntegerField(label=u"Porcentaje Gratuidad", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', "formwidth": "span6",  "separator": True}))
    valor_maximo = forms.FloatField(label=u'Valor Maximo', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', "formwidth": "span6"}))
    visible = forms.BooleanField(label=u"Visible", required=False, initial=True, widget=forms.CheckboxInput({'class': 'js-switch', "formwidth": "span12",  'separator': 'true', 'separatortitle': 'Relacione módulos y grupos'}))
    grupos = forms.ModelMultipleChoiceField(label=u'Grupos', required=False, queryset=Group.objects.all(), widget=forms.CheckboxSelectMultiple(attrs={'class': 'js-switch', 'formwidth': 'span12', 'searchMultipleCheckbox': 'true'}))

    def set_delete(self):
        self.fields['visible'].required = False
        self.fields['grupos'].required = False
        del self.fields['visible']
        del self.fields['grupos']

    def set_delete_grupos(self):
            self.fields['nombre'].required = False
            self.fields['inicio'].required = False
            self.fields['fin'].required = False
            self.fields['tipo'].required = False
            self.fields['valida_asistencia'].required = False
            self.fields['visiblehorario'].required = False
            self.fields['inicio_agregacion'].required = False
            self.fields['limite_agregacion'].required = False
            self.fields['limite_retiro'].required = False
            self.fields['fecha_inicio_agregacion'].required = False
            self.fields['fecha_fin_agregacion'].required = False
            self.fields['fecha_fin_quitar'].required = False
            self.fields['porcentaje_gratuidad'].required = False
            self.fields['valor_maximo'].required = False
            self.fields['marcardefecto'].required = False
            del self.fields['nombre']
            del self.fields['inicio']
            del self.fields['fin']
            del self.fields['tipo']
            del self.fields['valida_asistencia']
            del self.fields['visiblehorario']
            del self.fields['inicio_agregacion']
            del self.fields['limite_agregacion']
            del self.fields['limite_retiro']
            del self.fields['porcentaje_gratuidad']
            del self.fields['valor_maximo']
            del self.fields['fecha_inicio_agregacion']
            del self.fields['fecha_fin_agregacion']
            del self.fields['fecha_fin_quitar']
            del self.fields['marcardefecto']

    def set_initial(self, ePeriodo=None, typeForm=None):
        if typeForm is None:
            if ePeriodo:
                self.fields['nombre'].initial = ePeriodo.nombre
                self.fields['inicio'].initial = ePeriodo.inicio
                self.fields['fin'].initial = ePeriodo.fin
                self.fields['tipo'].initial = ePeriodo.tipo
                self.fields['valida_asistencia'].initial = ePeriodo.valida_asistencia
                self.fields['visiblehorario'].initial = ePeriodo.visiblehorario
                self.fields['inicio_agregacion'].initial = ePeriodo.inicio_agregacion
                self.fields['limite_agregacion'].initial = ePeriodo.limite_agregacion
                self.fields['limite_retiro'].initial = ePeriodo.limite_retiro
                self.fields['porcentaje_gratuidad'].initial = ePeriodo.porcentaje_gratuidad
                self.fields['valor_maximo'].initial = ePeriodo.valor_maximo
                self.fields['fecha_inicio_agregacion'].initial = ePeriodo.fechainicioagregacion
                self.fields['fecha_fin_agregacion'].initial = ePeriodo.fechafinagregacion
                self.fields['fecha_fin_quitar'].initial = ePeriodo.fechafinquitar
                self.fields['marcardefecto'].initial = ePeriodo.marcardefecto
            else:
                self.fields['inicio'].initial = datetime.now().date()
                self.fields['fin'].initial = (datetime.now() + timedelta(days=180)).date()
                self.fields['valida_asistencia'].initial = True
                self.fields['inicio_agregacion'].initial = (datetime.now() + timedelta(days=15)).date()
                self.fields['limite_agregacion'].initial = (datetime.now() + timedelta(days=30)).date()
                self.fields['limite_retiro'].initial = (datetime.now() + timedelta(days=30)).date()
                self.fields['fecha_inicio_agregacion'].initial = (datetime.now() + timedelta(days=30)).date()
                self.fields['fecha_fin_agregacion'].initial = (datetime.now() + timedelta(days=30)).date()
                self.fields['fecha_fin_quitar'].initial = (datetime.now() + timedelta(days=60)).date()
        elif typeForm == 'grupos':
            if PeriodoGrupo.objects.filter(periodo=ePeriodo).exists():
                periodogrupo = PeriodoGrupo.objects.get(periodo=ePeriodo)
                self.fields['visible'].initial = periodogrupo.visible
                self.fields['grupos'].initial = periodogrupo.grupos.all()

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True

    def clean(self):
        cleaned_data = super(PeriodoForm, self).clean()
        validGrupos = False
        if 'visible' in cleaned_data and 'grupos' in cleaned_data:
            validGrupos = True
        if not validGrupos:
            inicio_agregacion = cleaned_data['inicio_agregacion'] if 'inicio_agregacion' in cleaned_data and cleaned_data['inicio_agregacion'] else None
            limite_agregacion = cleaned_data['limite_agregacion'] if 'limite_agregacion' in cleaned_data and cleaned_data['limite_agregacion'] else None
            limite_retiro = cleaned_data['limite_retiro'] if 'limite_retiro' in cleaned_data and cleaned_data['limite_retiro'] else None
            fecha_inicio_agregacion = cleaned_data['fecha_inicio_agregacion'] if 'fecha_inicio_agregacion' in cleaned_data and cleaned_data['fecha_inicio_agregacion'] else None
            fecha_fin_agregacion = cleaned_data['fecha_fin_agregacion'] if 'fecha_fin_agregacion' in cleaned_data and cleaned_data['fecha_fin_agregacion'] else None
            fecha_fin_quitar = cleaned_data['fecha_fin_quitar'] if 'fecha_fin_quitar' in cleaned_data and cleaned_data['fecha_fin_quitar'] else None
            if not inicio_agregacion:
                self.add_error('inicio_agregacion', ValidationError('Favor ingrese una fecha de inicio de agregación'))
            if not limite_agregacion:
                self.add_error('limite_agregacion', ValidationError('Favor ingrese una fecha de limite de agregación'))
            if not limite_retiro:
                self.add_error('limite_retiro', ValidationError('Favor ingrese una fecha de limite de retiro'))
            if not fecha_inicio_agregacion:
                self.add_error('fecha_inicio_agregacion', ValidationError('Favor ingrese una fecha de inicio de agregación'))
            if not fecha_fin_agregacion:
                self.add_error('fecha_fin_agregacion', ValidationError('Favor ingrese una fecha de fin de agregación'))
            if not fecha_fin_quitar:
                self.add_error('fecha_fin_quitar', ValidationError('Favor ingrese una fecha de fin de retiro'))
            if inicio_agregacion == limite_agregacion or inicio_agregacion == limite_retiro:
                self.add_error('inicio_agregacion', ValidationError('Favor ingrese una fecha de inicio de agregación diferente a de limite de agregación o limite de retiro'))
            if limite_agregacion == inicio_agregacion or limite_agregacion == limite_retiro:
                self.add_error('limite_agregacion', ValidationError('Favor ingrese una fecha de limite de agregación diferente a de inicio de agregación o limite de retiro'))
            if limite_retiro == inicio_agregacion or limite_retiro == limite_agregacion:
                self.add_error('limite_retiro', ValidationError('Favor ingrese una fecha de limite de retiro diferente a de inicio de agregación o limite de agregación'))
            if limite_agregacion < inicio_agregacion:
                self.add_error('limite_agregacion', ValidationError('Favor ingrese una fecha de limite de agregación mayor a de inicio de agregación'))
            if limite_retiro < inicio_agregacion:
                self.add_error('limite_retiro', ValidationError('Favor ingrese una fecha de limite de retiro mayor a de inicio de agregación'))
            if fecha_inicio_agregacion == fecha_fin_agregacion:
                self.add_error('fecha_fin_agregacion', ValidationError('Favor ingrese la fecha fin agregación diferente a fecha inicio de agregación'))
            if fecha_fin_agregacion == fecha_fin_quitar:
                self.add_error('fecha_fin_quitar', ValidationError('Favor ingrese la fecha fin quitar diferente a fecha fin de agregación'))
            if fecha_fin_quitar < fecha_fin_agregacion:
                self.add_error('fecha_fin_quitar', ValidationError('Favor ingrese la fecha fin quitar mayor a fecha fin de agregación'))

        return cleaned_data


class PeriodoMatriculaForm(forms.Form):
    inicio_agregacion = forms.DateField(label=u"Inicio agregaciones", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4", "labelwidth": "250px", 'separator2': True, "separatortitle": "Fecha para Administrativos"}))
    limite_agregacion = forms.DateField(label=u"Limite agregaciones", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4"}))
    limite_retiro = forms.DateField(label=u"Limite retiro", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4"}))
    fecha_inicio_agregacion = forms.DateField(label=u"Inicio de agregación", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4", "labelwidth": "250px", 'separator2': True, "separatortitle": "Fecha para Estudiantes", 'showmsginfo': True, 'msgloc': 'top', 'msgtitle': 'Aviso:', 'msgtext': '', 'msglist': ['Fechas son referenciales para los niveles de la planificación del distributivo, en el caso que no haya configurado las fechas en niveles. Favor configurar']}))
    fecha_fin_agregacion = forms.DateField(label=u"Fin de agregación", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4"}))
    fecha_fin_quitar = forms.DateField(label=u"Fin de retiro", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4"}))
    tipo = forms.ChoiceField(label=u'Tipo', choices=TIPO_MATRICULA_CHOICES, required=True, widget=forms.Select(attrs={'formwidth': 'span3', 'separator3': True}))
    tipocalculo = forms.ChoiceField(label=u'Tipo calculo', choices=TIPO_CALCULO_MATRICULA, required=True, widget=forms.Select(attrs={'formwidth': 'span3'}))
    activo = forms.BooleanField(initial=True, required=False, label=u'Activo', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'Para activar el proceso de matricula considerar activar')
    valida_envio_mail = forms.BooleanField(initial=True, required=False, label=u'Envio de correo', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, se enviara correo cada acción que el estudiante realice')
    valida_gratuidad = forms.BooleanField(initial=False, required=False, label=u'Valida gratuidad', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator2': True, "separatortitle": "Gestión de gratuidad"}), help_text=u'En caso de activar, se validara la gratuidad')
    porcentaje_perdidad_parcial_gratuidad = forms.IntegerField(initial=60, required=False, label=u'% Perdidad Parcial', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span4'}), help_text=u'Valor minimo de porciento para perdida de gratuidad parcial (en funcion de las materias a seleccionar en el periodo)')
    porcentaje_perdidad_total_gratuidad = forms.IntegerField(initial=30, required=False, label=u'% Perdidad Total', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span4'}), help_text=u'Valor minimo de porciento para perdida de gratuidad total (en funcion de las horas de materias reprobadas / total horas malla)')
    valida_materia_carrera = forms.BooleanField(initial=False, required=False, label=u'Valida materia de la carrera', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator2': True, "separatortitle": "Metodos de validación"}), help_text=u'En caso de activar, solo filtrara asignaturas que sean de la carrera')
    valida_seccion = forms.BooleanField(initial=False, required=False, label=u'Valida sección', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, solo filtrara asignaturas que sean de la sección de la inscripción del estudiante')
    valida_cupo_materia = forms.BooleanField(initial=False, required=False, label=u'Valida cupo de materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, valida cupo de la materia con su disponibilidad')
    valida_horario_materia = forms.BooleanField(initial=False, required=False, label=u'Valida horario de materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator3': True}), help_text=u'En caso de activar, valida horario de la materia para seleccionar')
    valida_conflicto_horario = forms.BooleanField(initial=False, required=False, label=u'Valida conflicto horario de materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, valida conflicto de horario de la materia')
    ver_cupo_materia = forms.BooleanField(initial=False, required=False, label=u'Ver cupo de materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, se veran los cupo de la materia y la disponibilidad')
    ver_horario_materia = forms.BooleanField(initial=False, required=False, label=u'Ver horario de materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator3': True}), help_text=u'En caso de activar, se veran los horarios de la materia')
    ver_profesor_materia = forms.BooleanField(initial=False, required=False, label=u'Ver profesor de materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, se veran los profesor de la materia')
    fecha_vencimiento_rubro = forms.DateField(label=u"Fecha vencimiento de rubro", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4", "labelwidth": "250px"}))
    valida_deuda = forms.BooleanField(initial=False, required=False, label=u'Valida deuda', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3', 'separator3': True}), help_text=u'En caso de activar, valida deuda anteriores que únicamente sean de la carrera del estudiante')
    ver_deduda = forms.BooleanField(initial=False, required=False, label=u'Ver deuda', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, se veran el detalle de la deuda al estudiante')
    bloquea_por_deuda = forms.BooleanField(initial=False, required=False, label=u'Bloquear por deuda', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, se bloquea por deuda y no podra acceder a la matrícula el estudiante')
    tiporubros = forms.ModelMultipleChoiceField(queryset=TipoOtroRubro.objects.all(), required=False, label=u'Tipos de rubro', widget=forms.SelectMultiple({'formwidth': 'span3'}), help_text=u'Favor seleccionar los tipos de rubros a validar deuda')
    valida_materias_maxima = forms.BooleanField(initial=True, required=False, label=u'Valida materias máxima', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator3': True}), help_text=u'En caso de activar, valida número máxima de materias a elegir')
    num_materias_maxima = forms.IntegerField(initial=10, required=False, label=u'Número de materias máxima', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span4'}), help_text=u'Número máximo de materias a elegir')
    num_matriculas = forms.IntegerField(initial=3, required=False, label=u'Número de matrículas', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span4'}), help_text=u'Número máximo de validar matrículas')
    num_materias_maxima_ultima_matricula = forms.IntegerField(initial=3, required=False, label=u'Número de matrículas a elegir en última matrícula', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span4', 'separator2': True, "separatortitle": "Gestión de última matrícula"}), help_text=u'Número máximo de validar en última matricula')
    valida_configuracion_ultima_matricula = forms.BooleanField(initial=True, required=False, label=u'Valida configuración de casos', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, elegir configuración de casos')
    configuracion_ultima_matricula = forms.ModelChoiceField(queryset=ConfiguracionUltimaMatricula.objects.all(), required=False, label=u'Configuración', widget=forms.Select({'formwidth': 'span4'}), help_text=u'Favor seleccionar la configuración de casos de última matrícula')
    ver_eliminar_matricula = forms.BooleanField(initial=False, required=False, label=u'Ver botón eliminar matricula', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator2': True, "separatortitle": "Gestión del módulo de Agregar, quitar materia"}), help_text=u'En caso de activar, se vera el botón de eliminar matricula')
    puede_agregar_materia = forms.BooleanField(initial=False, required=False, label=u'Valida agregar materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, se podra agregar materias (Se considera fecha de agregación del nivel como segunda validación)')
    seguridad_remove_materia = forms.BooleanField(initial=False, required=False, label=u'Seguridad quitar materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, se implentara seguridad de token al quitar la materia (materia por materia)')
    puede_agregar_materia_rubro_pagados = forms.BooleanField(initial=False, required=False, label=u'Validar agregar materia con rubros pagados', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3', 'separator3': True}), help_text=u'En caso de activar, validara que el alumno no pueda agregar materias con valores pagados')
    puede_eliminar_materia_rubro_pagados = forms.BooleanField(initial=False, required=False, label=u'Validar quitar materia con rubros pagados', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, validara que el alumno no pueda quitar materias con valores pagados')
    puede_agregar_materia_rubro_diferidos = forms.BooleanField(initial=False, required=False, label=u'Validar agregar materia con rubros diferidos', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, validara que el alumno no pueda quitar materias con valores diferidos')
    puede_eliminar_materia_rubro_diferidos = forms.BooleanField(initial=False, required=False, label=u'Validar quitar materia con rubros diferidos', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, validara que el alumno no pueda quitar materias con valores diferidos')
    valida_proceos_matricula_especial = forms.BooleanField(initial=False, required=False, label=u'Validar proceso de matrícula especial', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span6', 'separator2': True, "separatortitle": "Matriculación especial (proceso)"}), help_text=u'En caso de activar, validara que ingrese las solicitudes del proceso de matrícula especial por el modulo')
    proceso_matricula_especial = forms.ModelChoiceField(queryset=ProcesoMatriculaEspecial.objects.all(), required=False, label=u'Proceso', widget=forms.Select({'formwidth': 'span6'}), help_text=u'Favor seleccionar el proceso de matrícula especial')
    valida_uso_carnet = forms.BooleanField(initial=False, required=False, label=u'Validar uso de carné', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span6', 'separator2': True, "separatortitle": "Carné estudiantil"}), help_text=u'En caso de activar, el proceso de matrícula creara el carné estudiantil')
    configuracion_carnet = forms.ModelChoiceField(queryset=ConfiguracionCarnet.objects.filter(tipo=1, tipo_perfil=1), required=False, label=u'Proceso', widget=forms.Select({'formwidth': 'span6'}), help_text=u'Favor seleccionar la configuración del carné estudiantil')
    valida_coordinacion = forms.BooleanField(initial=False, required=False, label=u'Validar coordinación', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator2': True, "separatortitle": "Habilitar por coordinaciones"}), help_text=u'En caso de activar, validara que solo ingresen a la matricula en las coordinaciones registradas')
    coordinaciones = forms.ModelMultipleChoiceField(label=u'Coordinaciones', required=False, queryset=Coordinacion.objects.filter(status=True), widget=forms.SelectMultiple(attrs={'formwidth': 'span8'}), help_text=u'Coordinaciones que se consideraran para el ingreso a la matricula')
    valida_cronograma = forms.BooleanField(initial=False, required=False, label=u'Validar cronograma', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator2': True, "separatortitle": "Cronograma"}), help_text=u'En caso de activar, validara que solo ingresen a la matricula en las coordinaciones registradas según el cronograma detallado')
    valida_login = forms.BooleanField(initial=False, required=False, label=u'Validar inicio de sesión', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, validara en el inicio de sesión que solo ingresen las coordinaciones registradas según el cronograma detallado')
    valida_redirect_panel = forms.BooleanField(initial=False, required=False, label=u'Redirigir despues del login', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, validara despues del inicio de sesión que se redireccione al modulo de matriculación')
    valida_cuotas_rubro = forms.BooleanField(initial=False, required=False, label=u'Validar cuotas de rubro', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3', 'separator2': True, "separatortitle": "Cuotas de rubro"}), help_text=u'En caso de activar, se validara las cuotas definidas')
    monto_rubro_cuotas = forms.IntegerField(initial=30, required=False, label=u'Monto Base a diferir', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': 'span3'}))
    num_cuotas_rubro = forms.IntegerField(initial=3, required=False, label=u'Número de cuotas', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span3'}))
    valida_rubro_acta_compromiso = forms.BooleanField(initial=False, required=False, label=u'Validar acta de compromiso', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, se generará una acta de compromiso')
    valida_terminos = forms.BooleanField(initial=True, required=False, label=u'Validar terminos', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span12', 'separator2': True, "separatortitle": "Terminos y Condiciones"}), help_text=u'En caso de activar, obligara al estudiante aceptar los terminos')
    terminos = forms.CharField(required=False, label=u'Listar terminos', widget=forms.Textarea(attrs={'formwidth': 'span12', 'separator3': True}))
    mostrar_terminos_examenes = forms.BooleanField(initial=True, required=False, label=u'Mostrar terminos examenes', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span12', 'separator2': True, "separatortitle": "Terminos y Condiciones"}), help_text=u'En caso de activar, obligara al estudiante aceptar los terminos')
    terminos_examenes = forms.CharField(required=False, label=u'Listar terminos Examenes', widget=forms.Textarea(attrs={'formwidth': 'span12', 'separator3': True}))

    def set_initial(self, ePeriodo):
        self.fields['inicio_agregacion'].initial = ePeriodo.inicio_agregacion
        self.fields['limite_agregacion'].initial = ePeriodo.limite_agregacion
        self.fields['limite_retiro'].initial = ePeriodo.limite_retiro
        self.fields['fecha_inicio_agregacion'].initial = ePeriodo.fechainicioagregacion
        self.fields['fecha_fin_agregacion'].initial = ePeriodo.fechafinagregacion
        self.fields['fecha_fin_quitar'].initial = ePeriodo.fechafinquitar
        self.fields['tipocalculo'].initial = ePeriodo.tipocalculo if ePeriodo.tipocalculo else 1
        if PeriodoMatricula.objects.filter(periodo=ePeriodo).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.get(periodo=ePeriodo)
            self.fields['tipo'].initial = ePeriodoMatricula.tipo
            self.fields['activo'].initial = ePeriodoMatricula.activo
            self.fields['valida_coordinacion'].initial = ePeriodoMatricula.valida_coordinacion
            self.fields['coordinaciones'].initial = ePeriodoMatricula.coordinaciones
            self.fields['valida_cronograma'].initial = ePeriodoMatricula.valida_cronograma
            self.fields['valida_materia_carrera'].initial = ePeriodoMatricula.valida_materia_carrera
            self.fields['valida_seccion'].initial = ePeriodoMatricula.valida_seccion
            self.fields['valida_cupo_materia'].initial = ePeriodoMatricula.valida_cupo_materia
            self.fields['valida_horario_materia'].initial = ePeriodoMatricula.valida_horario_materia
            self.fields['valida_conflicto_horario'].initial = ePeriodoMatricula.valida_conflicto_horario
            self.fields['valida_deuda'].initial = ePeriodoMatricula.valida_deuda
            self.fields['tiporubros'].initial = ePeriodoMatricula.tiposrubros
            self.fields['ver_cupo_materia'].initial = ePeriodoMatricula.ver_cupo_materia
            self.fields['ver_horario_materia'].initial = ePeriodoMatricula.ver_horario_materia
            self.fields['ver_profesor_materia'].initial = ePeriodoMatricula.ver_profesor_materia
            self.fields['ver_deduda'].initial = ePeriodoMatricula.ver_deduda
            self.fields['bloquea_por_deuda'].initial = ePeriodoMatricula.bloquea_por_deuda
            self.fields['valida_cuotas_rubro'].initial = ePeriodoMatricula.valida_cuotas_rubro
            self.fields['num_cuotas_rubro'].initial = ePeriodoMatricula.num_cuotas_rubro if ePeriodoMatricula.num_cuotas_rubro else 0
            self.fields['monto_rubro_cuotas'].initial = ePeriodoMatricula.monto_rubro_cuotas if ePeriodoMatricula.monto_rubro_cuotas else 0
            self.fields['valida_gratuidad'].initial = ePeriodoMatricula.valida_gratuidad
            self.fields['porcentaje_perdidad_parcial_gratuidad'].initial = ePeriodoMatricula.porcentaje_perdidad_parcial_gratuidad
            self.fields['porcentaje_perdidad_total_gratuidad'].initial = ePeriodoMatricula.porcentaje_perdidad_total_gratuidad
            self.fields['valida_materias_maxima'].initial = ePeriodoMatricula.valida_materias_maxima
            self.fields['num_materias_maxima'].initial = ePeriodoMatricula.num_materias_maxima if ePeriodoMatricula.num_materias_maxima else 10
            self.fields['valida_terminos'].initial = ePeriodoMatricula.valida_terminos
            self.fields['terminos'].initial = ePeriodoMatricula.terminos
            self.fields['valida_login'].initial = ePeriodoMatricula.valida_login
            self.fields['valida_redirect_panel'].initial = ePeriodoMatricula.valida_redirect_panel
            self.fields['valida_envio_mail'].initial = ePeriodoMatricula.valida_envio_mail
            self.fields['ver_eliminar_matricula'].initial = ePeriodoMatricula.ver_eliminar_matricula
            self.fields['puede_agregar_materia'].initial = ePeriodoMatricula.puede_agregar_materia
            self.fields['seguridad_remove_materia'].initial = ePeriodoMatricula.seguridad_remove_materia
            self.fields['num_matriculas'].initial = ePeriodoMatricula.num_matriculas
            self.fields['num_materias_maxima_ultima_matricula'].initial = ePeriodoMatricula.num_materias_maxima_ultima_matricula
            self.fields['puede_agregar_materia_rubro_pagados'].initial = ePeriodoMatricula.puede_agregar_materia_rubro_pagados
            self.fields['puede_eliminar_materia_rubro_pagados'].initial = ePeriodoMatricula.puede_eliminar_materia_rubro_pagados
            self.fields['puede_agregar_materia_rubro_diferidos'].initial = ePeriodoMatricula.puede_agregar_materia_rubro_diferidos
            self.fields['puede_eliminar_materia_rubro_diferidos'].initial = ePeriodoMatricula.puede_eliminar_materia_rubro_diferidos
            self.fields['valida_proceos_matricula_especial'].initial = ePeriodoMatricula.valida_proceos_matricula_especial
            self.fields['proceso_matricula_especial'].initial = ePeriodoMatricula.proceso_matricula_especial
            self.fields['valida_uso_carnet'].initial = ePeriodoMatricula.valida_uso_carnet
            self.fields['configuracion_carnet'].initial = ePeriodoMatricula.configuracion_carnet
            self.fields['valida_configuracion_ultima_matricula'].initial = ePeriodoMatricula.valida_configuracion_ultima_matricula
            self.fields['configuracion_ultima_matricula'].initial = ePeriodoMatricula.configuracion_ultima_matricula
            self.fields['fecha_vencimiento_rubro'].initial = ePeriodoMatricula.fecha_vencimiento_rubro
            self.fields['valida_rubro_acta_compromiso'].initial = ePeriodoMatricula.valida_rubro_acta_compromiso
            self.fields['mostrar_terminos_examenes'].initial = ePeriodoMatricula.mostrar_terminos_examenes
            self.fields['terminos_examenes'].initial = ePeriodoMatricula.terminos_examenes

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True

    def clean(self):
        fechas = json.loads(self.data['fechas']) if 'fechas' in self.data and self.data['fechas'] else None
        cronograma = json.loads(self.data['cronograma']) if 'cronograma' in self.data and self.data['cronograma'] else []
        coordinacioness = json.loads(self.data['coordinacioness']) if 'coordinacioness' in self.data and self.data['coordinacioness'] else []
        tiporubross = json.loads(self.data['tiporubross']) if 'tiporubross' in self.data and self.data['tiporubross'] else []
        cleaned_data = super(PeriodoMatriculaForm, self).clean()
        valida_cuotas_rubro = cleaned_data['valida_cuotas_rubro'] if 'valida_cuotas_rubro' in cleaned_data and cleaned_data['valida_cuotas_rubro'] else None
        num_cuotas_rubro = cleaned_data['num_cuotas_rubro'] if 'num_cuotas_rubro' in cleaned_data and cleaned_data['num_cuotas_rubro'] else 0
        monto_rubro_cuotas = cleaned_data['monto_rubro_cuotas'] if 'monto_rubro_cuotas' in cleaned_data and cleaned_data['monto_rubro_cuotas'] else 0
        valida_cronograma = cleaned_data['valida_cronograma'] if 'valida_cronograma' in cleaned_data and cleaned_data['valida_cronograma'] else None
        valida_coordinacion = cleaned_data['valida_coordinacion'] if 'valida_coordinacion' in cleaned_data and cleaned_data['valida_coordinacion'] else None
        valida_deuda = cleaned_data['valida_deuda'] if 'valida_deuda' in cleaned_data and cleaned_data['valida_deuda'] else None
        valida_gratuidad = cleaned_data['valida_gratuidad'] if 'valida_gratuidad' in cleaned_data and cleaned_data['valida_gratuidad'] else None
        porcentaje_perdidad_parcial_gratuidad = cleaned_data['porcentaje_perdidad_parcial_gratuidad'] if 'porcentaje_perdidad_parcial_gratuidad' in cleaned_data and cleaned_data['porcentaje_perdidad_parcial_gratuidad'] else None
        porcentaje_perdidad_total_gratuidad = cleaned_data['porcentaje_perdidad_total_gratuidad'] if 'porcentaje_perdidad_total_gratuidad' in cleaned_data and cleaned_data['porcentaje_perdidad_total_gratuidad'] else None
        valida_materias_maxima = cleaned_data['valida_materias_maxima'] if 'valida_materias_maxima' in cleaned_data and cleaned_data['valida_materias_maxima'] else None
        num_materias_maxima = cleaned_data['num_materias_maxima'] if 'num_materias_maxima' in cleaned_data and cleaned_data['num_materias_maxima'] else None
        valida_terminos = cleaned_data['valida_terminos'] if 'valida_terminos' in cleaned_data and cleaned_data['valida_terminos'] else None
        mostrar_terminos_examenes = cleaned_data['mostrar_terminos_examenes'] if 'mostrar_terminos_examenes' in cleaned_data and cleaned_data['mostrar_terminos_examenes'] else None
        terminos_examenes = cleaned_data['terminos_examenes'] if 'terminos_examenes' in cleaned_data and cleaned_data['terminos_examenes'] else None
        valida_login = cleaned_data['valida_login'] if 'valida_login' in cleaned_data and cleaned_data['valida_login'] else None
        # valida_redirect_panel = cleaned_data['valida_redirect_panel'] if 'valida_redirect_panel' in cleaned_data and cleaned_data['valida_redirect_panel'] else None
        terminos = cleaned_data['terminos'] if 'terminos' in cleaned_data and cleaned_data['terminos'] else None
        inicio_agregacion = cleaned_data['inicio_agregacion'] if 'inicio_agregacion' in cleaned_data and cleaned_data['inicio_agregacion'] else None
        limite_agregacion = cleaned_data['limite_agregacion'] if 'limite_agregacion' in cleaned_data and cleaned_data['limite_agregacion'] else None
        limite_retiro = cleaned_data['limite_retiro'] if 'limite_retiro' in cleaned_data and cleaned_data['limite_retiro'] else None
        fecha_inicio_agregacion = cleaned_data['fecha_inicio_agregacion'] if 'fecha_inicio_agregacion' in cleaned_data and cleaned_data['fecha_inicio_agregacion'] else None
        fecha_fin_agregacion = cleaned_data['fecha_fin_agregacion'] if 'fecha_fin_agregacion' in cleaned_data and cleaned_data['fecha_fin_agregacion'] else None
        fecha_fin_quitar = cleaned_data['fecha_fin_quitar'] if 'fecha_fin_quitar' in cleaned_data and cleaned_data['fecha_fin_quitar'] else None
        num_matriculas = cleaned_data['num_matriculas'] if 'num_matriculas' in cleaned_data else None
        num_materias_maxima_ultima_matricula = cleaned_data['num_materias_maxima_ultima_matricula'] if 'num_materias_maxima_ultima_matricula' in cleaned_data else None
        valida_proceos_matricula_especial = cleaned_data['valida_proceos_matricula_especial'] if 'valida_proceos_matricula_especial' in cleaned_data and cleaned_data['valida_proceos_matricula_especial'] else None
        proceso_matricula_especial = cleaned_data['proceso_matricula_especial'] if 'proceso_matricula_especial' in cleaned_data and cleaned_data['proceso_matricula_especial'] else None
        valida_uso_carnet = cleaned_data['valida_uso_carnet'] if 'valida_uso_carnet' in cleaned_data and cleaned_data['valida_uso_carnet'] else None
        configuracion_carnet = cleaned_data['configuracion_carnet'] if 'configuracion_carnet' in cleaned_data and cleaned_data['configuracion_carnet'] else None
        valida_configuracion_ultima_matricula = cleaned_data['valida_configuracion_ultima_matricula'] if 'valida_configuracion_ultima_matricula' in cleaned_data and cleaned_data['valida_configuracion_ultima_matricula'] else None
        configuracion_ultima_matricula = cleaned_data['configuracion_ultima_matricula'] if 'configuracion_ultima_matricula' in cleaned_data and cleaned_data['configuracion_ultima_matricula'] else None
        fecha_vencimiento_rubro = cleaned_data['fecha_vencimiento_rubro'] if 'fecha_vencimiento_rubro' in cleaned_data and cleaned_data['fecha_vencimiento_rubro'] else None
        if not inicio_agregacion:
            self.add_error('inicio_agregacion', ValidationError('Favor ingrese una fecha de inicio de agregación'))
        if not limite_agregacion:
            self.add_error('limite_agregacion', ValidationError('Favor ingrese una fecha de limite de agregación'))
        if not limite_retiro:
            self.add_error('limite_retiro', ValidationError('Favor ingrese una fecha de limite de retiro'))
        if not fecha_inicio_agregacion:
            self.add_error('fecha_inicio_agregacion', ValidationError('Favor ingrese una fecha de inicio de agregación'))
        if not fecha_fin_agregacion:
            self.add_error('fin_agregacion', ValidationError('Favor ingrese una fecha de fin de agregación'))
        if not fecha_fin_quitar:
            self.add_error('fin_quitar', ValidationError('Favor ingrese una fecha de fin de retiro'))
        if inicio_agregacion == limite_agregacion or inicio_agregacion == limite_retiro:
            self.add_error('inicio_agregacion', ValidationError('Favor ingrese una fecha de inicio de agregación diferente a de limite de agregación o limite de retiro'))
        if limite_agregacion == inicio_agregacion or limite_agregacion == limite_retiro:
            self.add_error('limite_agregacion', ValidationError('Favor ingrese una fecha de limite de agregación diferente a de inicio de agregación o limite de retiro'))
        if limite_retiro == inicio_agregacion or limite_retiro == limite_agregacion:
            self.add_error('limite_retiro', ValidationError('Favor ingrese una fecha de limite de retiro diferente a de inicio de agregación o limite de agregación'))
        if limite_agregacion < inicio_agregacion:
            self.add_error('limite_agregacion', ValidationError('Favor ingrese una fecha de limite de agregación mayor a de inicio de agregación'))
        if limite_retiro < inicio_agregacion:
            self.add_error('limite_retiro', ValidationError('Favor ingrese una fecha de limite de retiro mayor a de inicio de agregación'))
        if fecha_fin_agregacion == fecha_inicio_agregacion:
            self.add_error('fecha_fin_agregacion', ValidationError('Favor ingrese la fecha fin de agregación diferente a fecha inicio de agregación'))
        if fecha_fin_agregacion == fecha_fin_quitar:
            self.add_error('fecha_fin_quitar', ValidationError('Favor ingrese la fecha fin quitar diferente a fecha fin de agregación'))
        if fecha_fin_quitar < fecha_fin_agregacion:
            self.add_error('fecha_fin_quitar', ValidationError('Favor ingrese la fecha fin quitar mayor a fecha fin de agregación'))
        if valida_gratuidad:
            if not porcentaje_perdidad_parcial_gratuidad or porcentaje_perdidad_parcial_gratuidad > 100 or porcentaje_perdidad_parcial_gratuidad < 0:
                self.add_error('porcentaje_perdidad_parcial_gratuidad', ValidationError('Favor ingrese el porcentaje de perdidad pacial de gratuidad y que no sea mayor a 100 o menor a 0'))
            if not porcentaje_perdidad_total_gratuidad or porcentaje_perdidad_total_gratuidad > 100 or porcentaje_perdidad_total_gratuidad < 0:
                self.add_error('porcentaje_perdidad_total_gratuidad', ValidationError('Favor ingrese el porcentaje de perdidad total de gratuidad y que no sea mayor a 100 o menor a 0'))
        if valida_deuda:
            if not tiporubross or len(tiporubross) == 0:
                self.add_error('tiporubros', ValidationError('Favor registre al menos un tipo de rubro'))
        if valida_materias_maxima:
            if not num_materias_maxima or num_materias_maxima == 0:
                self.add_error('num_materias_maxima', ValidationError('Favor ingrese número de materias mayor a cero'))
        if valida_cronograma:
            if not cronograma or len(cronograma) == 0:
                self.add_error('valida_cronograma', ValidationError('Favor ingrese al menos un registro en el cronograma'))
        if valida_coordinacion:
            if not coordinacioness or len(coordinacioness) == 0:
                self.add_error('valida_coordinacion', ValidationError('Favor registre al menos una coordinación'))
        if valida_cuotas_rubro:
            if num_cuotas_rubro != 3:
                self.add_error('num_cuotas_rubro', ValidationError('Favor ingrese número de cuotas únicamente de 3'))
            elif not fechas:
                self.add_error('num_cuotas_rubro', ValidationError('Número de cuotas no coinciden con cantidad de fechas ingresadas'))
            elif not fechas or len(fechas) != num_cuotas_rubro:
                self.add_error('num_cuotas_rubro', ValidationError('Número de cuotas no coinciden con cantidad de fechas ingresadas'))
            elif monto_rubro_cuotas == 0:
                self.add_error('monto_rubro_cuotas', ValidationError('Valor referencial debe ser mayor a cero'))
        if valida_terminos:
            if not terminos:
                self.add_error('terminos', ValidationError('Favor registros los terminos a validar'))
        if mostrar_terminos_examenes:
            if not terminos_examenes:
                self.add_error('terminos_examenes', ValidationError('Favor registros los terminos examenes a validar'))
        # if valida_login:
        #     if not valida_cronograma:
        #         self.add_error('valida_cronograma', ValidationError('Favor active validar cronograma para validar inicio de sesión'))
        if not num_matriculas or num_matriculas < 1:
            self.add_error('num_matriculas', ValidationError('Favor ingrese número de matrículas mayor a 1'))
        if not num_materias_maxima_ultima_matricula or num_materias_maxima_ultima_matricula < 1:
            self.add_error('num_materias_maxima_ultima_matricula', ValidationError('Favor ingrese número de matrículas a elegir en última matrícula mayor a 1'))
        if valida_proceos_matricula_especial:
            if not proceso_matricula_especial:
                self.add_error('proceso_matricula_especial', ValidationError('Favor seleccione un proceso de matrícula especial'))
        if valida_uso_carnet:
            if not configuracion_carnet:
                self.add_error('configuracion_carnet', ValidationError('Favor seleccione una configuración del carné estudiantil'))
        if valida_configuracion_ultima_matricula:
            if not configuracion_ultima_matricula:
                self.add_error('configuracion_ultima_matricula', ValidationError('Favor seleccione una configuración de casos'))
        if not fecha_vencimiento_rubro:
            self.add_error('fecha_vencimiento_rubro', ValidationError('Favor ingrese una fecha de vencimiento de rubro'))
        return cleaned_data


class CronogramaCoordinacionForm(forms.Form):
    coordinacion = forms.ModelChoiceField(label=u"Coordinacion", queryset=Coordinacion.objects.filter(status=True), required=True, widget=forms.Select({'formwidth': '100%'}))
    fechainicio = forms.DateField(label=u"Desde", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '33.33%'}), required=True)
    fechafin = forms.DateField(label=u"Hasta", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '33.33%'}), required=True)
    activo = forms.BooleanField(initial=True, required=False, label=u'Activo', widget=forms.CheckboxInput({'formwidth': '33.33%'}))

    def editar(self, cronograma):
        # deshabilitar_campo(self, 'coordinacion')
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(pk=cronograma.coordinacion.id)

    def adicionar(self, detalle):
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(status=True).exclude(pk__in=detalle.cronogramas().values_list('coordinacion__id', flat=True))

    def eliminar_coordinacion(self):
        del self.fields['coordinacion']


class PeriodoFinancieroForm(forms.Form):
    porcentaje_gratuidad = forms.IntegerField(label=u"Porcentaje de gratuidad", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', "formwidth": "span6",  "separator": True}))
    valor_maximo = forms.FloatField(label=u'Valor máximo', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', "formwidth": "span6"}))

    def set_initial(self, ePeriodo):
        self.fields['porcentaje_gratuidad'].initial = ePeriodo.porcentaje_gratuidad
        self.fields['valor_maximo'].initial = ePeriodo.valor_maximo

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class ProcesoMatriculaEspecialForm(forms.Form):
    version = forms.IntegerField(label=u"Versión", initial=0, widget=forms.TextInput(attrs={'class': 'imp-number'}), required=True)
    sufijo = forms.CharField(label=u"Sufijo", initial='', max_length=25, widget=forms.TextInput(attrs={'class': 'imp-50'}), required=True)
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={}), required=True)
    activo = forms.BooleanField(label=u'Activo?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    motivos = forms.ModelMultipleChoiceField(label=u'Motivos', queryset=MotivoMatriculaEspecial.objects.filter(status=True), required=False)

    def set_initial(self, eProcesoMatriculaEspecial):
        self.fields['version'].initial = eProcesoMatriculaEspecial.version
        self.fields['sufijo'].initial = eProcesoMatriculaEspecial.sufijo
        self.fields['nombre'].initial = eProcesoMatriculaEspecial.nombre
        self.fields['activo'].initial = eProcesoMatriculaEspecial.activo
        self.fields['motivos'].initial = eProcesoMatriculaEspecial.motivos()


class MotivoMatriculaEspecialForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={}), required=True)
    detalle = forms.CharField(widget=forms.Textarea, label=u'Detalle', required=False)
    activo = forms.BooleanField(label=u'Activo?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    tipo = forms.ChoiceField(label=u'Tipo', choices=MOTIVO_MATRICULA_CHOICES, widget=forms.Select())

    def set_initial(self, eMotivoMatriculaEspecial):
        self.fields['nombre'].initial = eMotivoMatriculaEspecial.nombre
        self.fields['activo'].initial = eMotivoMatriculaEspecial.activo
        self.fields['detalle'].initial = eMotivoMatriculaEspecial.detalle
        self.fields['tipo'].initial = eMotivoMatriculaEspecial.tipo


class EstadoMatriculaEspecialForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=100, widget=forms.TextInput(attrs={}), required=True)
    color = forms.CharField(label=u"Class color", max_length=100, widget=forms.TextInput(attrs={}), required=True)
    editable = forms.BooleanField(label=u'Editable?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    accion = forms.ChoiceField(label=u'Acción', choices=ACCION_ESTADO_MATRICULA_ESPECIAL_CHOICES, widget=forms.Select())

    def set_initial(self, eEstadoMatriculaEspecial):
        self.fields['nombre'].initial = eEstadoMatriculaEspecial.nombre
        self.fields['color'].initial = eEstadoMatriculaEspecial.color
        self.fields['editable'].initial = eEstadoMatriculaEspecial.editable
        self.fields['accion'].initial = eEstadoMatriculaEspecial.accion


class ConfigProcesoMatriculaEspecialForm(forms.Form):
    orden = forms.IntegerField(label=u"Orden", initial=0, widget=forms.TextInput(attrs={'class': 'imp-number'}), required=True)
    nombre = forms.CharField(label=u"Nombre", required=True, max_length=200, widget=forms.TextInput({"formwidth": "100%"}))
    tipo_validacion = forms.ChoiceField(label=u'Tipo de validación', choices=TIPO_VALIDACION_MATRICULA_ESPECIAL_CHOICES, widget=forms.Select(), required=True)
    tipo_entidad = forms.ChoiceField(label=u'Tipo de entidad', choices=TIPO_ENTIDAD_MATRICULA_ESPECIAL_CHOICES, widget=forms.Select(), required=True)
    obligar_archivo = forms.BooleanField(label=u'Obligar archivo', required=False, widget=forms.CheckboxInput(attrs={}))
    obligar_observacion = forms.BooleanField(label=u'Obligar observación', required=False, widget=forms.CheckboxInput(attrs={}))
    estado_ok = forms.ModelChoiceField(queryset=EstadoMatriculaEspecial.objects.filter(status=True), required=True, label=u'Estado aceptado', widget=forms.Select(attrs={'formwidth': '50%'}))
    accion_ok = forms.ChoiceField(label=u'Acción aceptada', choices=ACCION_MATRICULA_ESPECIAL_CHOICES, widget=forms.Select(attrs={'formwidth': '50%'}), required=True)
    boton_ok_verbose = forms.CharField(label=u"Nombre boton aceptado", required=True, max_length=100, widget=forms.TextInput({"formwidth": "50%"}))
    boton_ok_label = forms.CharField(label=u"Color boton aceptado", required=True, max_length=100, widget=forms.TextInput({"formwidth": "50%"}))
    estado_nok = forms.ModelChoiceField(queryset=EstadoMatriculaEspecial.objects.filter(status=True), required=True, label=u'Estado no aceptado', widget=forms.Select(attrs={'formwidth': '50%'}))
    accion_nok = forms.ChoiceField(label=u'Acción no aceptada', choices=ACCION_MATRICULA_ESPECIAL_CHOICES, widget=forms.Select(attrs={'formwidth': '50%'}), required=True)
    boton_nok_verbose = forms.CharField(label=u"Nombre boton no aceptado", required=True, max_length=100, widget=forms.TextInput({"formwidth": "50%"}))
    boton_nok_label = forms.CharField(label=u"Color boton no aceptado", required=True, max_length=100, widget=forms.TextInput({"formwidth": "50%"}))

    def set_initial(self, eConfigProcesoMatriculaEspecial):
        self.fields['orden'].initial = eConfigProcesoMatriculaEspecial.orden
        self.fields['nombre'].initial = eConfigProcesoMatriculaEspecial.nombre
        self.fields['tipo_validacion'].initial = eConfigProcesoMatriculaEspecial.tipo_validacion
        self.fields['tipo_entidad'].initial = eConfigProcesoMatriculaEspecial.tipo_entidad
        self.fields['obligar_archivo'].initial = eConfigProcesoMatriculaEspecial.obligar_archivo
        self.fields['obligar_observacion'].initial = eConfigProcesoMatriculaEspecial.obligar_observacion
        self.fields['estado_ok'].initial = eConfigProcesoMatriculaEspecial.estado_ok
        self.fields['accion_ok'].initial = eConfigProcesoMatriculaEspecial.accion_ok
        self.fields['boton_ok_verbose'].initial = eConfigProcesoMatriculaEspecial.boton_ok_verbose
        self.fields['boton_ok_label'].initial = eConfigProcesoMatriculaEspecial.boton_ok_label
        self.fields['estado_nok'].initial = eConfigProcesoMatriculaEspecial.estado_nok
        self.fields['accion_nok'].initial = eConfigProcesoMatriculaEspecial.accion_nok
        self.fields['boton_nok_verbose'].initial = eConfigProcesoMatriculaEspecial.boton_nok_verbose
        self.fields['boton_nok_label'].initial = eConfigProcesoMatriculaEspecial.boton_nok_label

    def clean(self):
        cleaned_data = super(ConfigProcesoMatriculaEspecialForm, self).clean()
        nombre = cleaned_data['nombre'] if 'nombre' in cleaned_data and cleaned_data['nombre'] else ''
        tipo_validacion = int(cleaned_data['tipo_validacion']) if 'tipo_validacion' in cleaned_data and cleaned_data['tipo_validacion'] else None
        tipo_entidad = int(cleaned_data['tipo_entidad']) if 'tipo_entidad' in cleaned_data and cleaned_data['tipo_entidad'] else None
        boton_ok_verbose = cleaned_data['boton_ok_verbose'] if 'boton_ok_verbose' in cleaned_data and cleaned_data['boton_ok_verbose'] else None
        boton_ok_label = cleaned_data['boton_ok_label'] if 'boton_ok_label' in cleaned_data and cleaned_data['boton_ok_label'] else None
        boton_nok_verbose = cleaned_data['boton_nok_verbose'] if 'boton_nok_verbose' in cleaned_data and cleaned_data['boton_nok_verbose'] else None
        boton_nok_label = cleaned_data['boton_nok_label'] if 'boton_nok_label' in cleaned_data and cleaned_data['boton_nok_label'] else None
        if not tipo_validacion:
            self.add_error('tipo_validacion', ValidationError('Favor seleccione un tipo de validación'))
        if not nombre:
            self.add_error('nombre', ValidationError('Favor ingrese un nombre'))
        if not tipo_entidad:
            self.add_error('tipo_entidad', ValidationError('Favor seleccione un tipo de entidad'))
        if not boton_ok_verbose:
            self.add_error('boton_ok_verbose', ValidationError('Favor ingrese un nombre del boton aceptado'))
        if not boton_ok_label:
            self.add_error('boton_ok_label', ValidationError('Favor ingrese un color del boton aceptado'))
        if not boton_nok_verbose:
            self.add_error('boton_nok_verbose', ValidationError('Favor ingrese un nombre del boton no aceptado'))
        if not boton_nok_label:
            self.add_error('boton_nok_label', ValidationError('Favor ingrese un color del boton no aceptado'))
        return cleaned_data


class ConfigProcesoMatriculaEspecialAsistenteForm(forms.Form):
    tipo_entidad = forms.ChoiceField(label=u'Tipo de entidad', choices=TIPO_ENTIDAD_MATRICULA_ESPECIAL_CHOICES, widget=forms.Select(), required=True)
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), required=False, label=u'Departamento', widget=forms.Select(attrs={'formwidth': '100%'}))
    coordinacion = forms.ModelChoiceField(queryset=Coordinacion.objects.filter(status=True, carrera__isnull=False).distinct(), required=False, label=u'Coordinación', widget=forms.Select(attrs={'formwidth': '100%'}))
    responsable = forms.ModelChoiceField(label=u'Responsable', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(), required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    carrera = forms.ModelMultipleChoiceField(label=u'Carrera', required=False, queryset=Carrera.objects.filter(status=True), widget=forms.SelectMultiple(attrs={'separator2': True, 'separatortitle': 'Carreras responsables', 'fieldbuttons': [{'id': 'select_all', 'tooltiptext': 'Seleccionar todas', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa fa-check-square-o'}, {'id': 'unselect_all', 'tooltiptext': 'Deseleccionar todas', 'btnclasscolor': 'btn-warning', 'btnfaicon': 'fa fa-minus'}, ]}))

    def tipo(self, tipo):
        self.fields['tipo_entidad'].initial = tipo

    def set_initial(self, eConfigProcesoMatriculaEspecialAsistente):
        self.fields['tipo_entidad'].initial = eConfigProcesoMatriculaEspecialAsistente.configuracion.tipo_entidad
        self.fields['departamento'].initial = eConfigProcesoMatriculaEspecialAsistente.departamento
        self.fields['coordinacion'].initial = eConfigProcesoMatriculaEspecialAsistente.coordinacion
        self.fields['responsable'].initial = eConfigProcesoMatriculaEspecialAsistente.responsable
        if eConfigProcesoMatriculaEspecialAsistente.configuracion.tipo_entidad == 2:
            self.fields['carrera'].queryset = eConfigProcesoMatriculaEspecialAsistente.coordinacion.carreras()
            self.fields['carrera'].initial = eConfigProcesoMatriculaEspecialAsistente.carreras()

    def clean(self):
        cleaned_data = super(ConfigProcesoMatriculaEspecialAsistenteForm, self).clean()
        tipo_entidad = int(cleaned_data['tipo_entidad']) if 'tipo_entidad' in cleaned_data and cleaned_data['tipo_entidad'] else None
        departamento = cleaned_data['departamento'] if 'departamento' in cleaned_data and cleaned_data['departamento'] else None
        responsable = cleaned_data['responsable'] if 'responsable' in cleaned_data and cleaned_data['responsable'] else None
        coordinacion = cleaned_data['coordinacion'] if 'coordinacion' in cleaned_data and cleaned_data['coordinacion'] else None
        carrera = cleaned_data['carrera'] if 'carrera' in cleaned_data and cleaned_data['carrera'] else None

        if tipo_entidad == 1:
            if not departamento:
                self.add_error('departamento', ValidationError('Favor seleccione un departamento'))
            else:
                if not responsable:
                    self.add_error('responsable', ValidationError('Favor seleccione un responsable'))
        elif tipo_entidad == 2:
            if not coordinacion:
                self.add_error('coordinacion', ValidationError('Favor seleccione una coordinación'))
            if not carrera:
                self.add_error('carrera', ValidationError('Favor ingrese al menos una carrera'))

        return cleaned_data


class ConfiguracionCarnetForm(forms.Form):
    version = forms.IntegerField(label=u"Versión", initial=0, widget=forms.TextInput(attrs={'class': 'imp-number'}), required=True)
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={}), required=True)
    tipo = forms.ChoiceField(label=u'Tipo de carné', choices=TIPO_CARNET, widget=forms.Select(), required=True)
    tipo_perfil = forms.ChoiceField(label=u'Tipo de perfil', choices=TIPO_PERFIL, widget=forms.Select(), required=True)
    tipo_validacion = forms.ChoiceField(label=u'Tipo de carné', choices=TIPO_VALIDACION_CARNET, widget=forms.Select(), required=True)
    base_anverso = ExtFileField(label=u'Base anversa', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=10485760, widget=FileInput({'accept':' image/jpeg, image/jpg, image/png'}))
    base_reverso = ExtFileField(label=u'Base reversa', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=10485760, widget=FileInput({'accept':' image/jpeg, image/jpg, image/png'}))
    reporte = forms.ModelChoiceField(queryset=Reporte.objects.filter(status=True), required=True, label=u'Reporte', widget=forms.Select(attrs={'formwidth': '100%'}))
    activo = forms.BooleanField(label=u'Activo?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    puede_cargar_foto = forms.BooleanField(label=u'Puede subir foto?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    puede_eliminar_carne = forms.BooleanField(label=u'Puede eliminar carnet?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    puede_subir_foto = forms.BooleanField(label=u'Puede volver a subir foto?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))

    def set_initial(self, eConfiguracionCarnet):
        self.fields['version'].initial = eConfiguracionCarnet.version
        self.fields['nombre'].initial = eConfiguracionCarnet.nombre
        self.fields['tipo'].initial = eConfiguracionCarnet.tipo
        self.fields['tipo_perfil'].initial = eConfiguracionCarnet.tipo_perfil
        self.fields['tipo_validacion'].initial = eConfiguracionCarnet.tipo_validacion
        self.fields['reporte'].initial = eConfiguracionCarnet.reporte
        self.fields['activo'].initial = eConfiguracionCarnet.activo
        self.fields['puede_cargar_foto'].initial = eConfiguracionCarnet.puede_cargar_foto
        self.fields['puede_eliminar_carne'].initial = eConfiguracionCarnet.puede_eliminar_carne
        self.fields['puede_subir_foto'].initial = eConfiguracionCarnet.puede_subir_foto

    def clean(self):
        cleaned_data = super(ConfiguracionCarnetForm, self).clean()
        id = int(self.data['id']) if 'id' in self.data and self.data['id'] else None
        version = int(cleaned_data['version']) if 'version' in cleaned_data and cleaned_data['version'] else None
        nombre = cleaned_data['nombre'] if 'nombre' in cleaned_data and cleaned_data['nombre'] else None
        # tipo_perfil = int(cleaned_data['tipo_perfil']) if 'tipo_perfil' in cleaned_data and cleaned_data['tipo_perfil'] else None
        # tipo_validacion = int(cleaned_data['tipo_validacion']) if 'tipo_validacion' in cleaned_data and cleaned_data['tipo_validacion'] else None
        # base_anverso = cleaned_data['base_anverso'] if 'base_anverso' in cleaned_data and cleaned_data['base_anverso'] else None
        # base_reverso = cleaned_data['base_reverso'] if 'base_reverso' in cleaned_data and cleaned_data['base_reverso'] else None
        reporte = cleaned_data['reporte'] if 'reporte' in cleaned_data and cleaned_data['reporte'] else None

        if not version:
            self.add_error('version', ValidationError(u'Favor ingrese una versión mayor a cero'))
        if not nombre:
            self.add_error('nombre', ValidationError(u'Favor ingrese un nombre a la configuración del carné'))
        # if tipo_validacion == 1 and not id:
        #     if not base_anverso:
        #         self.add_error('base_anverso', ValidationError('Favor ingrese una base anversa'))
        # elif tipo_validacion == 2 and not id:
        #     if not base_reverso:
        #         self.add_error('base_reverso', ValidationError('Favor ingrese una base reversa'))
        # else:
        #     if not base_anverso and not id:
        #         self.add_error('base_anverso', ValidationError('Favor ingrese una base anversa'))
        #     if not base_reverso and not id:
        #         self.add_error('base_reverso', ValidationError('Favor ingrese una base reversa'))
        if not reporte:
            self.add_error('reporte', ValidationError('Favor seleccione un reporte para el carnét'))

        return cleaned_data


class PeriodoAcademiaForm(forms.Form):
    fecha_limite_horario_tutoria = forms.DateField(label=u"Fecha limite", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span4", "labelwidth": "250px"}), help_text=u'Fecha limite ingreso horario tutoria docente')
    version_cumplimiento_recurso = forms.IntegerField(initial=0, required=True, label=u'Versión cumplimiento silabo', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span4'}), help_text=u'Para version de informes de cumplimiento de recurso silabos en aprobar silabo')
    cierra_materia = forms.BooleanField(initial=True, required=False, label=u'Cierre de materia', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, es obligatorio cerrar las materias ofertadas')
    periodos_relacionados = forms.ModelMultipleChoiceField(required=False, queryset=Periodo.objects.filter(status=True), label=u'Periodos relacionados', widget=forms.SelectMultiple(attrs={'formwidth': 'span12', 'separator3': True}), help_text=u'Periodos que llevan relación en tema de actividades del docente')
    tipo_modalidad = forms.ChoiceField(label=u'Tipo', choices=TIPO_PERIODO_MODALIDAD_CHOICES, required=True, widget=forms.Select(attrs={'formwidth': 'span3', 'separator2': True, "separatortitle": "Control de asistencia"}))
    utiliza_asistencia_redis = forms.BooleanField(initial=True, required=False, label=u'Asistencia con REDIS', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, la asistencia utilizara REDIS')
    utiliza_asistencia_ws = forms.BooleanField(initial=True, required=False, label=u'Asistencia con WebSocket', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, la asistencia utilizara WEBSOCKET')
    puede_cerrar_clase = forms.BooleanField(initial=True, required=False, label=u'Puede cerrar clase', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, el docente puede cerrar la clase abierta')
    puede_eliminar_clase = forms.BooleanField(initial=True, required=False, label=u'Puede eliminar clase', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, el docente puede eliminar la clase abierta')
    puede_editar_contenido_academico_clase = forms.BooleanField(initial=True, required=False, label=u'Puede editar contenido de clase', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, el docente puede editar contenido académico de la clase')
    puede_cambiar_asistencia_clase = forms.BooleanField(initial=False, required=False, label=u'Puede registrar asistencia en clase cerrada', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, se activara opción de registro de asistencia en clase cerrada')
    num_dias_cambiar_asistencia_clase = forms.IntegerField(initial=0, required=False, label=u'Días', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span3'}), help_text=u'Número de días que pueda registrar asistencia en clase cerrada')
    valida_asistencia_pago = forms.BooleanField(initial=False, required=False, label=u'Validar asistencia con deuda', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, validara alumnos que no adeuden')
    valida_asistencia_in_home = forms.BooleanField(initial=False, required=False, label=u'Valida IP para registro de asistencia dentro del CAMPUS', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3'}), help_text=u'En caso de activar, el/la docente de clase presencial y carrera presencial podra podra registrar únicamente dentro del CAMPUS UNIVERSITARIO')
    puede_solicitar_clase_diferido_pro = forms.BooleanField(initial=True, required=False, label=u'Solicitar registro de asistencias (Profesor)', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span3', 'separator3': True}), help_text=u'En caso de activar, el/la docente podra solicitar registros de asistencias')
    proceso_solicitud_clase_diferido_pro = forms.ModelChoiceField(queryset=ProcesoSolicitudClaseDiferido.objects.filter(status=True), required=False, label=u'Proceso de diferido', widget=forms.Select(attrs={'formwidth': 'span6'}))
    valida_clases_horario_estricto = forms.BooleanField(label=u"Validar clase con horario estricto", required=False,  widget=CheckboxInput(attrs={'class': 'js-switch', "formwidth": "span12", "labelwidth": "250px", 'separator2': True, "separatortitle": "Gestión de horario", 'showmsginfo': True, 'msgloc': 'top', 'msgtitle': 'Aviso:', 'msgtext': '', 'msglist': ['En caso de activar se validara minutos antes y despues de apertura tanto para docentes y alumnos']}))
    min_clases_apertura_antes_pro = forms.IntegerField(initial=15, required=False, label=u'Minutos antes de la apertura para el docente', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span6', "labelwidth": "350px"}), help_text=u'Valida que se cumpla los minutos antes de la apertura de la clase')
    min_clases_apertura_despues_pro = forms.IntegerField(initial=45, required=False, label=u'Minutos despues de la apertura para el docente', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span6', "labelwidth": "350px"}), help_text=u'Valida que se cumpla los minutos despues de la apertura de la clase')
    min_clases_apertura_antes_alu = forms.IntegerField(initial=15, required=False, label=u'Minutos antes de la apertura para el estudiante', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span6', "labelwidth": "350px"}), help_text=u'Valida que se cumpla los minutos antes de la apertura de la clase')
    min_clases_apertura_despues_alu = forms.IntegerField(initial=45, required=False, label=u'Minutos despues de la apertura para el estudiante', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span6', "labelwidth": "350px"}), help_text=u'Valida que se cumpla los minutos despues de la apertura de la clase')

    def set_initial(self, ePeriodo):
        if PeriodoAcademia.objects.filter(periodo=ePeriodo).exists():
            ePeriodoAcademia = PeriodoAcademia.objects.get(periodo=ePeriodo)
            self.fields['fecha_limite_horario_tutoria'].initial = ePeriodoAcademia.fecha_limite_horario_tutoria
            self.fields['version_cumplimiento_recurso'].initial = ePeriodoAcademia.version_cumplimiento_recurso
            self.fields['cierra_materia'].initial = ePeriodoAcademia.cierra_materia
            if ePeriodoAcademia.periodos_relacionados:
                self.fields['periodos_relacionados'].initial = Periodo.objects.filter(pk__in=ePeriodoAcademia.periodos_relacionados.strip().split(','))
            self.fields['tipo_modalidad'].initial = ePeriodoAcademia.tipo_modalidad
            self.fields['utiliza_asistencia_ws'].initial = ePeriodoAcademia.utiliza_asistencia_ws
            self.fields['utiliza_asistencia_redis'].initial = ePeriodoAcademia.utiliza_asistencia_redis
            self.fields['puede_cerrar_clase'].initial = ePeriodoAcademia.puede_cerrar_clase
            self.fields['puede_eliminar_clase'].initial = ePeriodoAcademia.puede_eliminar_clase
            self.fields['puede_editar_contenido_academico_clase'].initial = ePeriodoAcademia.puede_editar_contenido_academico_clase
            self.fields['puede_cambiar_asistencia_clase'].initial = ePeriodoAcademia.puede_cambiar_asistencia_clase
            self.fields['num_dias_cambiar_asistencia_clase'].initial = ePeriodoAcademia.num_dias_cambiar_asistencia_clase if ePeriodoAcademia.num_dias_cambiar_asistencia_clase else 0
            self.fields['valida_clases_horario_estricto'].initial = ePeriodoAcademia.valida_clases_horario_estricto
            self.fields['min_clases_apertura_antes_pro'].initial = ePeriodoAcademia.min_clases_apertura_antes_pro
            self.fields['min_clases_apertura_despues_pro'].initial = ePeriodoAcademia.min_clases_apertura_despues_pro
            self.fields['min_clases_apertura_antes_alu'].initial = ePeriodoAcademia.min_clases_apertura_antes_alu
            self.fields['min_clases_apertura_despues_alu'].initial = ePeriodoAcademia.min_clases_apertura_despues_alu
            self.fields['valida_asistencia_pago'].initial = ePeriodoAcademia.valida_asistencia_pago
            self.fields['puede_solicitar_clase_diferido_pro'].initial = ePeriodoAcademia.puede_solicitar_clase_diferido_pro
            self.fields['proceso_solicitud_clase_diferido_pro'].initial = ePeriodoAcademia.proceso_solicitud_clase_diferido_pro
            self.fields['valida_asistencia_in_home'].initial = ePeriodoAcademia.valida_asistencia_in_home

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True

    def clean(self):
        cleaned_data = super(PeriodoAcademiaForm, self).clean()
        fecha_limite_horario_tutoria = cleaned_data['fecha_limite_horario_tutoria'] if 'fecha_limite_horario_tutoria' in cleaned_data and cleaned_data['fecha_limite_horario_tutoria'] else None
        version_cumplimiento_recurso = cleaned_data['version_cumplimiento_recurso'] if 'version_cumplimiento_recurso' in cleaned_data and cleaned_data['version_cumplimiento_recurso'] else 0
        tipo_modalidad = cleaned_data['tipo_modalidad'] if 'tipo_modalidad' in cleaned_data and cleaned_data['tipo_modalidad'] else None
        puede_cambiar_asistencia_clase = cleaned_data['puede_cambiar_asistencia_clase'] if 'puede_cambiar_asistencia_clase' in cleaned_data and cleaned_data['puede_cambiar_asistencia_clase'] else None
        num_dias_cambiar_asistencia_clase = cleaned_data['num_dias_cambiar_asistencia_clase'] if 'num_dias_cambiar_asistencia_clase' in cleaned_data and cleaned_data['num_dias_cambiar_asistencia_clase'] else 0
        valida_clases_horario_estricto = cleaned_data['valida_clases_horario_estricto'] if 'valida_clases_horario_estricto' in cleaned_data and cleaned_data['valida_clases_horario_estricto'] else False
        min_clases_apertura_antes_pro = cleaned_data['min_clases_apertura_antes_pro'] if 'min_clases_apertura_antes_pro' in cleaned_data and cleaned_data['min_clases_apertura_antes_pro'] else None
        min_clases_apertura_despues_pro = cleaned_data['min_clases_apertura_despues_pro'] if 'min_clases_apertura_despues_pro' in cleaned_data and cleaned_data['min_clases_apertura_despues_pro'] else None
        min_clases_apertura_antes_alu = cleaned_data['min_clases_apertura_antes_alu'] if 'min_clases_apertura_antes_alu' in cleaned_data and cleaned_data['min_clases_apertura_antes_alu'] else None
        min_clases_apertura_despues_alu = cleaned_data['min_clases_apertura_despues_alu'] if 'min_clases_apertura_despues_alu' in cleaned_data and cleaned_data['min_clases_apertura_despues_alu'] else None
        puede_solicitar_clase_diferido_pro = cleaned_data['puede_solicitar_clase_diferido_pro'] if 'puede_solicitar_clase_diferido_pro' in cleaned_data and cleaned_data['puede_solicitar_clase_diferido_pro'] else False
        proceso_solicitud_clase_diferido_pro = cleaned_data['proceso_solicitud_clase_diferido_pro'] if 'proceso_solicitud_clase_diferido_pro' in cleaned_data and cleaned_data['proceso_solicitud_clase_diferido_pro'] else None

        if not fecha_limite_horario_tutoria:
            self.add_error('fecha_limite_horario_tutoria', ValidationError('Favor ingrese una fecha limite'))
        if not version_cumplimiento_recurso:
            self.add_error('version_cumplimiento_recurso', ValidationError('Favor ingrese una versión mayor a cero'))
        if not tipo_modalidad:
            self.add_error('tipo_modalidad', ValidationError('Favor seleccione una modalidad'))
        if puede_cambiar_asistencia_clase:
            if num_dias_cambiar_asistencia_clase <= 0 or num_dias_cambiar_asistencia_clase > 30:
                self.add_error('num_dias_cambiar_asistencia_clase', ValidationError('Favor ingrese número de días mayor a 0 y menor a 30'))
        if valida_clases_horario_estricto:
            if min_clases_apertura_antes_pro is None:
                self.add_error('min_clases_apertura_antes_pro', ValidationError('Favor ingrese minutos de apertura antes del profesor'))
            if min_clases_apertura_antes_pro <= 0 or min_clases_apertura_antes_pro >= 60:
                self.add_error('min_clases_apertura_antes_pro', ValidationError('Favor ingrese minutos mayor a cero y menor a sesenta de apertura antes del profesor'))

            if min_clases_apertura_despues_pro is None:
                self.add_error('min_clases_apertura_despues_pro', ValidationError('Favor ingrese minutos de apertura despues del profesor'))
            if min_clases_apertura_despues_pro <= 0 or min_clases_apertura_despues_pro >= 60:
                self.add_error('min_clases_apertura_despues_pro', ValidationError('Favor ingrese minutos mayor a cero y menor a sesenta de apertura despues del profesor'))

            if min_clases_apertura_antes_alu is None:
                self.add_error('min_clases_apertura_antes_alu', ValidationError('Favor ingrese minutos de apertura antes del alumno'))
            if min_clases_apertura_antes_alu <= 0 or min_clases_apertura_antes_alu >= 60:
                self.add_error('min_clases_apertura_antes_alu', ValidationError('Favor ingrese minutos mayor a cero y menor a sesenta de apertura antes del alumno'))

            if min_clases_apertura_despues_alu is None:
                self.add_error('min_clases_apertura_despues_alu', ValidationError('Favor ingrese minutos de apertura despues del alumno'))
            if min_clases_apertura_despues_alu <= 0 or min_clases_apertura_despues_alu >= 60:
                self.add_error('min_clases_apertura_despues_alu', ValidationError('Favor ingrese minutos mayor a cero y menor a sesenta de apertura despues del alumno'))

        if puede_solicitar_clase_diferido_pro:
            if not proceso_solicitud_clase_diferido_pro:
                self.add_error('proceso_solicitud_clase_diferido_pro', ValidationError('Favor seleccione un proceso de solicitud de apertura de clase por diferido'))

        return cleaned_data


class PeriodoCrontabForm(forms.Form):
    type = forms.ChoiceField(label=u'Tipo', choices=TIPO_PERIODO_CRONTAB_CHOICES, required=True, widget=forms.Select(attrs={'formwidth': 'span6'}))
    is_activo = forms.BooleanField(initial=False, required=False, label=u'Activo?', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span6'}), help_text=u'En caso de activar, se considera para el cron en segundo plano')
    upgrade_level_inscription = forms.BooleanField(initial=False, required=False, label=u'Actualizar nivel inscripción', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4', 'separator3': True}), help_text=u'En caso de activar, se considera para actualizar el nivel de inscripción')
    upgrade_level_enrollment = forms.BooleanField(initial=False, required=False, label=u'Actualizar nivel matrícula', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, se considera para actualizar el nivel de matrícula')
    upgrade_state_enrollment = forms.BooleanField(initial=False, required=False, label=u'Actualizar estado matrícula', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span4'}), help_text=u'En caso de activar, se considera para actualizar el estado de matrícula')
    create_lesson_previa = forms.BooleanField(initial=False, required=False, label=u'Crear lecciones previa', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span6', 'separator2': True, 'separatortitle': 'Lecciones (clases)'}), help_text=u'En caso de activar, se creara lecciones previa a la apertura')
    delete_lesson_previa = forms.BooleanField(initial=False, required=False, label=u'Eliminar lecciones previa', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span6'}), help_text=u'En caso de activar, se eliminara lecciones previa a la apertura que no se hayan aperturado')
    notify_student_activities = forms.BooleanField(initial=False, required=False, label=u'Notificar actividades estudiantes', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span6', 'separator2': True, 'separatortitle': 'Notificaciones'}), help_text=u'En caso de activar, se notificaran las activdades de los estudiantes')
    bloqueo_state_enrollment = forms.BooleanField(initial=False, required=False, label=u'Bloqueo de matrícula', widget=forms.CheckboxInput({'class': 'js-switch', 'formwidth': 'span6', 'separator2': True, 'separatortitle': 'Bloqueo/Desbloqueo de matriculas'}), help_text=u'En caso de activar, se actualizara el estado de matrícula de los estudiantes')

    def set_initial(self, ePeriodo):
        if PeriodoCrontab.objects.filter(periodo=ePeriodo).exists():
            ePeriodoCrontab = PeriodoCrontab.objects.get(periodo=ePeriodo)
            self.fields['type'].initial = ePeriodoCrontab.type
            self.fields['is_activo'].initial = ePeriodoCrontab.is_activo
            self.fields['upgrade_level_inscription'].initial = ePeriodoCrontab.upgrade_level_inscription
            self.fields['upgrade_level_enrollment'].initial = ePeriodoCrontab.upgrade_level_enrollment
            self.fields['upgrade_state_enrollment'].initial = ePeriodoCrontab.upgrade_state_enrollment
            self.fields['create_lesson_previa'].initial = ePeriodoCrontab.create_lesson_previa
            self.fields['delete_lesson_previa'].initial = ePeriodoCrontab.delete_lesson_previa
            self.fields['notify_student_activities'].initial = ePeriodoCrontab.notify_student_activities
            self.fields['bloqueo_state_enrollment'].initial = ePeriodoCrontab.bloqueo_state_enrollment

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class SettingWSDLForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre del servicio", max_length=250, widget=forms.TextInput(attrs={'formwidth': '100%'}), required=True)
    cuenta = forms.ModelChoiceField(queryset=CuentaBanco.objects.filter(status=True), required=False, label=u'Cuenta de banco', widget=forms.Select(attrs={'formwidth': '50%'}))
    tipo = forms.ChoiceField(label=u'Tipo', choices=TIPO_SERVICIO_SOAP, required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    activo = forms.BooleanField(label=u'Activo?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    tipo_ambiente = forms.ChoiceField(label=u'Ambiente', choices=TIPO_AMBIENTE, required=True, widget=forms.Select(attrs={'formwidth': '50%'}))

    def set_initial(self, eSetting):
        self.initial = model_to_dict(eSetting)


class VariablesGlobalesForm(forms.Form):
    referencia = forms.CharField(label=u"Referencia o módulo", max_length=100, widget=forms.TextInput(attrs={}), required=True)
    descripcion = forms.CharField(label=u"Descripcion", max_length=200, widget=forms.TextInput(attrs={}), required=True)
    variable = forms.CharField(label=u"Variable", max_length=50, widget=forms.TextInput(attrs={}), required=True)
    # tipodato = forms.ChoiceField(label=u'Tipo de parametro (dato)', choices=TIPOS_PARAMETRO_VARIABLE, widget=forms.Select(), required=True)
    # TEXTO
    valor_1 = forms.CharField(label=u'Valor', widget=forms.Textarea(attrs={}), required=False)
    # NUMERO ENTERO
    valor_2 = forms.IntegerField(label=u'Valor', initial=0, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}), required=False)
    # NUMERO DECIMAL
    valor_3 = forms.DecimalField(label=u'Valor', initial='0.000', widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}), required=False)
    # VERDADERO O FALSO
    valor_4 = forms.BooleanField(label=u'Valor', initial=True, required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch'}))
    # FECHA
    valor_5 = forms.DateField(label=u"Valor", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), required=True)
    # LISTA
    valor_6 = forms.CharField(label=u'Valor', widget=forms.Textarea(attrs={}), required=False)

    def set_initial(self, eVariable):
        self.fields['referencia'].initial = eVariable.referencia
        self.fields['descripcion'].initial = eVariable.descripcion
        self.fields['variable'].initial = eVariable.variable
        # self.fields['tipodato'].initial = eVariable.tipodato
        field_valor = f"valor_{eVariable.tipodato}"
        self.fields[field_valor].initial = eVariable.valor
        if eVariable.tipodato == 4:
            self.fields["valor_4"].initial = eVariable.valor and eVariable.valor.lower() in ['true']

    def set_type_form(self, type):
        for i in range(1, 7):
            if i != type:
                del self.fields[f"valor_{i}"]
            else:
                if i == 4:
                    self.fields[f"valor_{i}"].required = False
                else:
                    self.fields[f"valor_{i}"].required = True

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True

    def clean(self):
        tipodato = int(self.data['tipodato']) if 'tipodato' in self.data and self.data['tipodato'] else None
        cleaned_data = super(VariablesGlobalesForm, self).clean()
        referencia = cleaned_data['referencia'] if 'referencia' in cleaned_data and cleaned_data['referencia'] else None
        descripcion = cleaned_data['descripcion'] if 'descripcion' in cleaned_data and cleaned_data['descripcion'] else None
        variable = cleaned_data['variable'] if 'variable' in cleaned_data and cleaned_data['variable'] else None
        # tipodato = cleaned_data['tipodato'] if 'tipodato' in cleaned_data and cleaned_data['tipodato'] else None
        valor_1 = cleaned_data['valor_1'] if 'valor_1' in cleaned_data and cleaned_data['valor_1'] else None
        valor_2 = cleaned_data['valor_2'] if 'valor_2' in cleaned_data else None
        valor_3 = cleaned_data['valor_3'] if 'valor_3' in cleaned_data else None
        # valor_4 = cleaned_data['valor_4'] if 'valor_4' in cleaned_data and cleaned_data['valor_4'] else None
        valor_5 = cleaned_data['valor_5'] if 'valor_5' in cleaned_data and cleaned_data['valor_5'] else None
        valor_6 = cleaned_data['valor_6'] if 'valor_6' in cleaned_data and cleaned_data['valor_6'] else False
        if not referencia:
            self.add_error('referencia', ValidationError('Favor ingrese una referencia o módulo'))
        if not descripcion:
            self.add_error('descripcion', ValidationError('Favor ingrese una descripción'))
        if not variable:
            self.add_error('variable', ValidationError('Favor ingrese la variable'))
        if not tipodato:
            self.add_error('tipodato', ValidationError('Favor seleccione el tipo de dato'))
        else:
            if tipodato == 1 and valor_1 is None:
                self.add_error('valor_1', ValidationError('Favor ingrese parametro de la variable'))
            if tipodato == 2 and valor_2 is None:
                self.add_error('valor_2', ValidationError('Favor ingrese parametro de la variable'))
            if tipodato == 3 and valor_3 is None:
                self.add_error('valor_3', ValidationError('Favor ingrese parametro de la variable'))
            # if tipodato == 4 and valor_4 is None:
            #     self.add_error('valor_4', ValidationError('Favor ingrese parametro de la variable'))
            if tipodato == 5 and valor_5 is None:
                self.add_error('valor_5', ValidationError('Favor ingrese parametro de la variable'))
            if tipodato == 6 and valor_6 is None:
                self.add_error('valor_6', ValidationError('Favor ingrese parametro de la variable'))
        return cleaned_data


class TemplateBaseSettingForm(forms.Form):
    name_system = forms.CharField(max_length=500, label=u'Nombre', required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '70%'}))
    app = forms.ChoiceField(label=u'Tipo', choices=APP_LABEL_TEMPLATE, required=True, widget=forms.Select(attrs={'formwidth': '30%'}))
    use_menu_favorite_module = forms.BooleanField(label=u'Use menu favorito', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    use_menu_notification = forms.BooleanField(label=u'Use menu notificación', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    use_menu_user_manual = forms.BooleanField(label=u'Use menu manual de usuario', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    use_api = forms.BooleanField(label=u'Use API', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True

    def set_initial(self, eTemplateBaseSetting):
        self.fields['name_system'].initial = eTemplateBaseSetting.name_system
        self.fields['app'].initial = eTemplateBaseSetting.app
        self.fields['use_menu_favorite_module'].initial = eTemplateBaseSetting.use_menu_favorite_module
        self.fields['use_menu_notification'].initial = eTemplateBaseSetting.use_menu_notification
        self.fields['use_menu_user_manual'].initial = eTemplateBaseSetting.use_menu_user_manual
        self.fields['use_api'].initial = eTemplateBaseSetting.use_api

    def clean(self):
        cleaned_data = super(TemplateBaseSettingForm, self).clean()
        name_system = cleaned_data['name_system'] if 'name_system' in cleaned_data and cleaned_data['name_system'] else None
        if not name_system:
            self.add_error('name_system', ValidationError('Favor ingrese el nombre del sistema'))
        return cleaned_data


class DiasNoLaborableForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=True, initial=str(datetime.now().date().strftime('%d-%m-%Y')), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '30%'}))
    desde = forms.TimeField(label=u"Desde", required=True, initial=str(datetime.now().time()), input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '30%'}))
    hasta = forms.TimeField(label=u"Hasta", required=True, initial=str(datetime.now().time()), input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '30%'}))
    tipo_accion = forms.ChoiceField(label=u'Dirigido a:', choices=TYPE_ACTION_NO_WORKING, required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    activo = forms.BooleanField(label=u'Activo', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    periodo = forms.ModelChoiceField(queryset=Periodo.objects.filter(status=True), required=True, label=u'Periodo académico', widget=forms.Select(attrs={'formwidth': '100%'}))
    coordinacion = forms.ModelChoiceField(queryset=Coordinacion.objects.filter(status=True), required=False, label=u'Coordinación', widget=forms.Select(attrs={'formwidth': '100%'}))
    carrera = forms.ModelChoiceField(queryset=Carrera.objects.filter(status=True), required=False, label=u'Carrera', widget=forms.Select(attrs={'formwidth': '100%'}))
    nivelmalla = forms.ModelChoiceField(queryset=NivelMalla.objects.filter(status=True), required=False, label=u'Nivel', widget=forms.Select(attrs={'formwidth': '100%'}))
    valida_coordinacion = forms.BooleanField(label=u'Validar coordinación', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '100%'}))
    motivo = forms.ChoiceField(label=u'Motivo', choices=TYPE_DAYS_NO_WORKING, required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    observaciones = forms.CharField(label=u'Observaciones', required=True, widget=forms.TextInput(attrs={'formwidth': '50%', 'class': 'imp-100'}))

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True

    def set_initial(self, eDiasNoLaborable):
        self.fields['tipo_accion'].initial = eDiasNoLaborable.tipo_accion
        self.fields['activo'].initial = eDiasNoLaborable.activo
        self.fields['fecha'].initial = eDiasNoLaborable.fecha
        self.fields['desde'].initial = eDiasNoLaborable.desde
        self.fields['hasta'].initial = eDiasNoLaborable.hasta
        self.fields['periodo'].initial = eDiasNoLaborable.periodo
        self.fields['coordinacion'].initial = eDiasNoLaborable.coordinacion
        self.fields['carrera'].initial = eDiasNoLaborable.carrera
        self.fields['nivelmalla'].initial = eDiasNoLaborable.nivelmalla
        self.fields['motivo'].initial = eDiasNoLaborable.motivo
        self.fields['observaciones'].initial = eDiasNoLaborable.observaciones
        self.fields['valida_coordinacion'].initial = eDiasNoLaborable.valida_coordinacion

    def set_version(self, version):
        if version != 1:
            del self.fields['coordinacion']
            del self.fields['carrera']
            del self.fields['nivelmalla']

    def clean(self):
        cleaned_data = super(DiasNoLaborableForm, self).clean()
        tipo_accion = cleaned_data['tipo_accion'] if 'tipo_accion' in cleaned_data and cleaned_data['tipo_accion'] else None
        periodo = cleaned_data['periodo'] if 'periodo' in cleaned_data and cleaned_data['periodo'] else None
        motivo = cleaned_data['motivo'] if 'motivo' in cleaned_data and cleaned_data['motivo'] else None
        fecha = cleaned_data['fecha'] if 'fecha' in cleaned_data and cleaned_data['fecha'] else None
        desde = cleaned_data['desde'] if 'desde' in cleaned_data and cleaned_data['desde'] else None
        hasta = cleaned_data['hasta'] if 'hasta' in cleaned_data and cleaned_data['hasta'] else None
        observaciones = cleaned_data['observaciones'] if 'observaciones' in cleaned_data and cleaned_data['observaciones'] else None

        if not tipo_accion:
            self.add_error('tipo_accion', ValidationError('Favor seleccione a quien va dirigido'))
        else:
            if int(tipo_accion) == 1:
                if not periodo:
                    self.add_error('periodo', ValidationError('Favor seleccione un periodo académico'))

        if not motivo:
            self.add_error('motivo', ValidationError('Favor seleccione un motivo'))

        if not fecha:
            self.add_error('fecha', ValidationError('Favor seleccione una fecha'))

        if not desde:
            self.add_error('desde', ValidationError('Favor seleccione la hora desde'))

        if not hasta:
            self.add_error('hasta', ValidationError('Favor seleccione la hora hasta'))

        if not observaciones:
            self.add_error('observaciones', ValidationError('Favor ingrese una observación'))

        return cleaned_data


class DiasNoLaborableCoordinacionForm(forms.Form):
    coordinacion = forms.ModelChoiceField(queryset=Coordinacion.objects.filter(status=True), required=False, label=u'Coordinación', widget=forms.Select(attrs={'formwidth': '100%'}))
    activo = forms.BooleanField(label=u'Activo', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    valida_carrera = forms.BooleanField(label=u'Validar carrera', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))

    def set_initial(self, eDiasNoLaborableCoordinacion):
        self.fields['coordinacion'].initial = eDiasNoLaborableCoordinacion.coordinacion
        self.fields['activo'].initial = eDiasNoLaborableCoordinacion.activo
        self.fields['valida_carrera'].initial = eDiasNoLaborableCoordinacion.valida_carrera

    def clean(self):
        cleaned_data = super(DiasNoLaborableCoordinacionForm, self).clean()
        coordinacion = cleaned_data['coordinacion'] if 'coordinacion' in cleaned_data and cleaned_data['coordinacion'] else None

        if not coordinacion:
            self.add_error('coordinacion', ValidationError('Favor seleccione una coordinación'))

        return cleaned_data


class DiasNoLaborableCoordinacionCarreraForm(forms.Form):
    carrera = forms.ModelChoiceField(queryset=Carrera.objects.filter(status=True), required=False, label=u'Carrera', widget=forms.Select(attrs={'formwidth': '100%'}))
    activo = forms.BooleanField(label=u'Activo', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    valida_nivel = forms.BooleanField(label=u'Validar nivel', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    niveles = forms.ModelMultipleChoiceField(queryset=NivelMalla.objects.filter(status=True), required=False, label=u'Nivel', widget=forms.SelectMultiple(attrs={'formwidth': '100%'}))

    def set_initial(self, eDiasNoLaborableCoordinacionCarrera):
        self.fields['carrera'].initial = eDiasNoLaborableCoordinacionCarrera.carrera
        self.fields['activo'].initial = eDiasNoLaborableCoordinacionCarrera.activo
        self.fields['valida_nivel'].initial = eDiasNoLaborableCoordinacionCarrera.valida_nivel
        self.fields['niveles'].initial = eDiasNoLaborableCoordinacionCarrera.nivel.all()

    def set_carrera(self, eCoordinacion):
        self.fields['carrera'].queryset = eCoordinacion.carrera.all()

    def clean(self):
        cleaned_data = super(DiasNoLaborableCoordinacionCarreraForm, self).clean()
        carrera = cleaned_data['carrera'] if 'carrera' in cleaned_data and cleaned_data['carrera'] else None
        valida_nivel = cleaned_data['valida_nivel'] if 'valida_nivel' in cleaned_data else False
        niveles = cleaned_data['niveles'] if 'niveles' in cleaned_data and cleaned_data['niveles'] else None

        if not carrera:
            self.add_error('carrera', ValidationError('Favor seleccione una carrera'))
        if valida_nivel:
            if not niveles:
                self.add_error('niveles', ValidationError('Favor seleccione al menos un nivel'))

        return cleaned_data


class MotivoRetiroMatriculaForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={}), required=True)
    detalle = forms.CharField(widget=forms.Textarea, label=u'Detalle', required=False)
    activo = forms.BooleanField(label=u'Activo?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    tipo = forms.ChoiceField(label=u'Tipo', choices=MOTIVO_MATRICULA_CHOICES, widget=forms.Select())

    def set_initial(self, eMotivoRetiroMatricula):
        self.fields['nombre'].initial = eMotivoRetiroMatricula.nombre
        self.fields['activo'].initial = eMotivoRetiroMatricula.activo
        self.fields['detalle'].initial = eMotivoRetiroMatricula.detalle
        self.fields['tipo'].initial = eMotivoRetiroMatricula.tipo


class EstadoRetiroMatriculaForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=100, widget=forms.TextInput(attrs={}), required=True)
    color = forms.CharField(label=u"Class color", max_length=100, widget=forms.TextInput(attrs={}), required=True)
    editable = forms.BooleanField(label=u'Editable?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    accion = forms.ChoiceField(label=u'Acción', choices=ACCION_ESTADO_RETIRO_MATRICULA_CHOICES, widget=forms.Select())

    def set_initial(self, eEstadoRetiroMatricula):
        self.fields['nombre'].initial = eEstadoRetiroMatricula.nombre
        self.fields['color'].initial = eEstadoRetiroMatricula.color
        self.fields['editable'].initial = eEstadoRetiroMatricula.editable
        self.fields['accion'].initial = eEstadoRetiroMatricula.accion


class ProcesoRetiroMatriculaForm(forms.Form):
    version = forms.IntegerField(label=u"Versión", initial=0, widget=forms.TextInput(attrs={'class': 'imp-number'}), required=True)
    sufijo = forms.CharField(label=u"Sufijo", initial='', max_length=25, widget=forms.TextInput(attrs={'class': 'imp-50'}), required=True)
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={}), required=True)
    activo = forms.BooleanField(label=u'Activo?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    motivos = forms.ModelMultipleChoiceField(label=u'Motivos', queryset=MotivoRetiroMatricula.objects.filter(status=True), required=False)

    def set_initial(self, eProcesoRetiroMatricula):
        self.fields['version'].initial = eProcesoRetiroMatricula.version
        self.fields['sufijo'].initial = eProcesoRetiroMatricula.sufijo
        self.fields['nombre'].initial = eProcesoRetiroMatricula.nombre
        self.fields['activo'].initial = eProcesoRetiroMatricula.activo
        self.fields['motivos'].initial = eProcesoRetiroMatricula.motivos()


class ConfigProcesoRetiroMatriculaForm(forms.Form):
    orden = forms.IntegerField(label=u"Orden", initial=0, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '33.33%'}), required=True)
    tiempo_atencion = forms.IntegerField(label=u"Tiempo de respuesta", initial=0, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '33.33%'}), required=True)
    tipo_tiempo_atencion = forms.ChoiceField(label=u"Tipo del tiempo de respuesta", choices=TIPO_TIEMPO_ATENCION, initial=0, widget=forms.Select(attrs={'formwidth': '33.33%'}), required=True)
    nombre = forms.CharField(label=u"Nombre", required=True, max_length=200, widget=forms.TextInput({"formwidth": "100%"}))
    tipo_validacion = forms.ChoiceField(label=u'Tipo de validación', choices=TIPO_VALIDACION_RETIRO_MATRICULA_CHOICES, widget=forms.Select(), required=True)
    tipo_entidad = forms.ChoiceField(label=u'Tipo de entidad', choices=TIPO_ENTIDAD_RETIRO_MATRICULA_CHOICES, widget=forms.Select(), required=True)
    obligar_archivo = forms.BooleanField(label=u'Obligar archivo', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    obligar_observacion = forms.BooleanField(label=u'Obligar observación', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    estado_ok = forms.ModelChoiceField(queryset=EstadoRetiroMatricula.objects.filter(status=True), required=True, label=u'Estado aceptado', widget=forms.Select(attrs={'formwidth': '50%'}))
    accion_ok = forms.ChoiceField(label=u'Acción aceptada', choices=ACCION_RETIRO_MATRICULA_CHOICES, widget=forms.Select(attrs={'formwidth': '50%'}), required=True)
    boton_ok_verbose = forms.CharField(label=u"Nombre boton aceptado", required=True, max_length=100, widget=forms.TextInput({"formwidth": "50%"}))
    boton_ok_label = forms.CharField(label=u"Color boton aceptado", required=True, max_length=100, widget=forms.TextInput({"formwidth": "50%"}))
    estado_nok = forms.ModelChoiceField(queryset=EstadoRetiroMatricula.objects.filter(status=True), required=True, label=u'Estado no aceptado', widget=forms.Select(attrs={'formwidth': '50%'}))
    accion_nok = forms.ChoiceField(label=u'Acción no aceptada', choices=ACCION_RETIRO_MATRICULA_CHOICES, widget=forms.Select(attrs={'formwidth': '50%'}), required=True)
    boton_nok_verbose = forms.CharField(label=u"Nombre boton no aceptado", required=True, max_length=100, widget=forms.TextInput({"formwidth": "50%"}))
    boton_nok_label = forms.CharField(label=u"Color boton no aceptado", required=True, max_length=100, widget=forms.TextInput({"formwidth": "50%"}))

    def set_initial(self, eConfigProcesoRetiroMatricula):
        self.fields['orden'].initial = eConfigProcesoRetiroMatricula.orden
        self.fields['nombre'].initial = eConfigProcesoRetiroMatricula.nombre
        self.fields['tipo_validacion'].initial = eConfigProcesoRetiroMatricula.tipo_validacion
        self.fields['tipo_entidad'].initial = eConfigProcesoRetiroMatricula.tipo_entidad
        self.fields['obligar_archivo'].initial = eConfigProcesoRetiroMatricula.obligar_archivo
        self.fields['obligar_observacion'].initial = eConfigProcesoRetiroMatricula.obligar_observacion
        self.fields['estado_ok'].initial = eConfigProcesoRetiroMatricula.estado_ok
        self.fields['accion_ok'].initial = eConfigProcesoRetiroMatricula.accion_ok
        self.fields['boton_ok_verbose'].initial = eConfigProcesoRetiroMatricula.boton_ok_verbose
        self.fields['boton_ok_label'].initial = eConfigProcesoRetiroMatricula.boton_ok_label
        self.fields['estado_nok'].initial = eConfigProcesoRetiroMatricula.estado_nok
        self.fields['accion_nok'].initial = eConfigProcesoRetiroMatricula.accion_nok
        self.fields['boton_nok_verbose'].initial = eConfigProcesoRetiroMatricula.boton_nok_verbose
        self.fields['boton_nok_label'].initial = eConfigProcesoRetiroMatricula.boton_nok_label
        self.fields['tiempo_atencion'].initial = eConfigProcesoRetiroMatricula.tiempo_atencion
        self.fields['tipo_tiempo_atencion'].initial = eConfigProcesoRetiroMatricula.tipo_tiempo_atencion

    def clean(self):
        cleaned_data = super(ConfigProcesoRetiroMatriculaForm, self).clean()
        nombre = cleaned_data['nombre'] if 'nombre' in cleaned_data and cleaned_data['nombre'] else ''
        tipo_validacion = int(cleaned_data['tipo_validacion']) if 'tipo_validacion' in cleaned_data and cleaned_data['tipo_validacion'] else None
        tipo_entidad = int(cleaned_data['tipo_entidad']) if 'tipo_entidad' in cleaned_data and cleaned_data['tipo_entidad'] else None
        boton_ok_verbose = cleaned_data['boton_ok_verbose'] if 'boton_ok_verbose' in cleaned_data and cleaned_data['boton_ok_verbose'] else None
        boton_ok_label = cleaned_data['boton_ok_label'] if 'boton_ok_label' in cleaned_data and cleaned_data['boton_ok_label'] else None
        boton_nok_verbose = cleaned_data['boton_nok_verbose'] if 'boton_nok_verbose' in cleaned_data and cleaned_data['boton_nok_verbose'] else None
        boton_nok_label = cleaned_data['boton_nok_label'] if 'boton_nok_label' in cleaned_data and cleaned_data['boton_nok_label'] else None
        tiempo_atencion = cleaned_data['tiempo_atencion'] if 'tiempo_atencion' in cleaned_data else None
        tipo_tiempo_atencion = cleaned_data['tipo_tiempo_atencion'] if 'tipo_tiempo_atencion' in cleaned_data else None
        if not tipo_validacion:
            self.add_error('tipo_validacion', ValidationError('Favor seleccione un tipo de validación'))
        if not nombre:
            self.add_error('nombre', ValidationError('Favor ingrese un nombre'))
        if not tipo_entidad:
            self.add_error('tipo_entidad', ValidationError('Favor seleccione un tipo de entidad'))
        if not boton_ok_verbose:
            self.add_error('boton_ok_verbose', ValidationError('Favor ingrese un nombre del boton aceptado'))
        if not boton_ok_label:
            self.add_error('boton_ok_label', ValidationError('Favor ingrese un color del boton aceptado'))
        if not boton_nok_verbose:
            self.add_error('boton_nok_verbose', ValidationError('Favor ingrese un nombre del boton no aceptado'))
        if not boton_nok_label:
            self.add_error('boton_nok_label', ValidationError('Favor ingrese un color del boton no aceptado'))
        if not tipo_tiempo_atencion:
            self.add_error('tipo_tiempo_atencion', ValidationError('Favor seleccione el tipo de tiempo de respuesta'))
        else:
            if not tiempo_atencion:
                self.add_error('tiempo_atencion', ValidationError('Favor ingrese el valor del tiempo de respuesta'))
            elif int(tiempo_atencion) < 0:
                self.add_error('tiempo_atencion', ValidationError('Favor ingrese el valor mayor a cero del tiempo de respuesta'))
            else:
                if int(tipo_tiempo_atencion) == 1:
                    if int(tiempo_atencion) > 24:
                        self.add_error('tiempo_atencion', ValidationError('Favor ingrese el valor menor a 24 del tiempo de respuesta'))
                elif int(tipo_tiempo_atencion) == 2:
                    if int(tiempo_atencion) > 365:
                        self.add_error('tiempo_atencion', ValidationError('Favor ingrese el valor menor a 365 del tiempo de respuesta'))
                elif int(tipo_tiempo_atencion) == 3:
                    if int(tiempo_atencion) > 12:
                        self.add_error('tiempo_atencion', ValidationError('Favor ingrese el valor menor a 12 del tiempo de respuesta'))

        return cleaned_data


class ConfigProcesoRetiroMatriculaAsistenteForm(forms.Form):
    tipo_entidad = forms.ChoiceField(label=u'Tipo de entidad', choices=TIPO_ENTIDAD_RETIRO_MATRICULA_CHOICES, widget=forms.Select(), required=True)
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), required=False, label=u'Departamento', widget=forms.Select(attrs={'formwidth': '100%'}))
    coordinacion = forms.ModelChoiceField(queryset=Coordinacion.objects.filter(status=True, carrera__isnull=False).distinct(), required=False, label=u'Coordinación', widget=forms.Select(attrs={'formwidth': '100%'}))
    responsable = forms.ModelChoiceField(label=u'Responsable', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct(), required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    carrera = forms.ModelMultipleChoiceField(label=u'Carrera', required=False, queryset=Carrera.objects.filter(status=True), widget=forms.SelectMultiple(attrs={'separator2': True, 'separatortitle': 'Carreras responsables', 'fieldbuttons': [{'id': 'select_all', 'tooltiptext': 'Seleccionar todas', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa fa-check-square-o'}, {'id': 'unselect_all', 'tooltiptext': 'Deseleccionar todas', 'btnclasscolor': 'btn-warning', 'btnfaicon': 'fa fa-minus'}, ]}))

    def tipo(self, tipo):
        self.fields['tipo_entidad'].initial = tipo

    def set_initial(self, eConfigProcesoRetiroMatriculaAsistente):
        self.fields['tipo_entidad'].initial = eConfigProcesoRetiroMatriculaAsistente.configuracion.tipo_entidad
        self.fields['departamento'].initial = eConfigProcesoRetiroMatriculaAsistente.departamento
        self.fields['coordinacion'].initial = eConfigProcesoRetiroMatriculaAsistente.coordinacion
        self.fields['responsable'].initial = eConfigProcesoRetiroMatriculaAsistente.responsable
        if eConfigProcesoRetiroMatriculaAsistente.configuracion.tipo_entidad == 2:
            self.fields['carrera'].queryset = eConfigProcesoRetiroMatriculaAsistente.coordinacion.carreras()
            self.fields['carrera'].initial = eConfigProcesoRetiroMatriculaAsistente.carreras()

    def clean(self):
        cleaned_data = super(ConfigProcesoRetiroMatriculaAsistenteForm, self).clean()
        tipo_entidad = int(cleaned_data['tipo_entidad']) if 'tipo_entidad' in cleaned_data and cleaned_data['tipo_entidad'] else None
        departamento = cleaned_data['departamento'] if 'departamento' in cleaned_data and cleaned_data['departamento'] else None
        responsable = cleaned_data['responsable'] if 'responsable' in cleaned_data and cleaned_data['responsable'] else None
        coordinacion = cleaned_data['coordinacion'] if 'coordinacion' in cleaned_data and cleaned_data['coordinacion'] else None
        carrera = cleaned_data['carrera'] if 'carrera' in cleaned_data and cleaned_data['carrera'] else None

        if tipo_entidad == 1:
            if not departamento:
                self.add_error('departamento', ValidationError('Favor seleccione un departamento'))
            else:
                if not responsable:
                    self.add_error('responsable', ValidationError('Favor seleccione un responsable'))
        elif tipo_entidad == 2:
            if not coordinacion:
                self.add_error('coordinacion', ValidationError('Favor seleccione una coordinación'))
            if not carrera:
                self.add_error('carrera', ValidationError('Favor ingrese al menos una carrera'))

        return cleaned_data


class MatriculaCronogramaCoordinacionForm(forms.Form):
    coordinacion = forms.ModelChoiceField(label=u"Coordinacion", queryset=Coordinacion.objects.filter(status=True), required=True, widget=forms.Select({'formwidth': 'span12'}))
    fechainicio = forms.DateField(label=u"Desde (Fecha)", input_formats=['%d-%m-%Y'], initial=datetime.now().date().strftime('%d-%m-%Y'), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': 'span3'}), required=True)
    horainicio = forms.TimeField(label=u"Desde (Hora)", input_formats=['%H:%M'], initial=str(datetime.now().time()), widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': 'span3'}), required=True)
    fechafin = forms.DateField(label=u"Hasta (Fecha)", input_formats=['%d-%m-%Y'], initial=datetime.now().date().strftime('%d-%m-%Y'), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': 'span3'}), required=True)
    horafin = forms.TimeField(label=u"Hasta (Hora)", input_formats=['%H:%M'], initial=str(datetime.now().time()), widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': 'span3'}), required=True)
    activo = forms.BooleanField(initial=True, required=False, label=u'Activo', widget=forms.CheckboxInput({'formwidth': 'span12', 'class': 'js-switch'}))

    def set_initial(self, eCronogramaCoordinacion):
        self.fields['coordinacion'].initial = eCronogramaCoordinacion.coordinacion
        self.fields['fechainicio'].initial = eCronogramaCoordinacion.fechainicio
        self.fields['horainicio'].initial = eCronogramaCoordinacion.horainicio if eCronogramaCoordinacion.horainicio else datetime.now().time()
        self.fields['fechafin'].initial = eCronogramaCoordinacion.fechafin
        self.fields['horafin'].initial = eCronogramaCoordinacion.horafin if eCronogramaCoordinacion.horafin else datetime.now().time()
        self.fields['activo'].initial = eCronogramaCoordinacion.activo

    def editar(self, eCronogramaCoordinacion):
        self.fields['coordinacion'].queryset = Coordinacion.objects.filter(pk=eCronogramaCoordinacion.coordinacion.id)

    def clean(self):
        cleaned_data = super(MatriculaCronogramaCoordinacionForm, self).clean()
        fechainicio = cleaned_data['fechainicio'] if 'fechainicio' in cleaned_data and cleaned_data['fechainicio'] else False
        horainicio = cleaned_data['horainicio'] if 'horainicio' in cleaned_data and cleaned_data['horainicio'] else False
        fechafin = cleaned_data['fechafin'] if 'fechafin' in cleaned_data and cleaned_data['fechafin'] else None
        horafin = cleaned_data['horafin'] if 'horafin' in cleaned_data and cleaned_data['horafin'] else None

        if not fechainicio:
            self.add_error('fechainicio', ValidationError('Favor seleccione una fecha inicio'))
        if not fechafin:
            self.add_error('fechainicio', ValidationError('Favor seleccione una fecha fin'))
        if not horainicio:
            self.add_error('horainicio', ValidationError('Favor seleccione una hora inicio'))
        if not horafin:
            self.add_error('horafin', ValidationError('Favor seleccione una hora fin'))
        fechahorainicio = datetime.combine(fechainicio, horainicio)
        fechahorafin = datetime.combine(fechafin, horafin)
        if fechahorainicio > fechahorafin:
            self.add_error('fechainicio', ValidationError('Favor seleccione una fecha y hora inicio menor a fin'))

        return cleaned_data


class MatriculaCronogramaCarreraForm(forms.Form):
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.filter(status=True), required=True, widget=forms.Select({'formwidth': 'span12'}))
    niveles = forms.ModelMultipleChoiceField(queryset=NivelMalla.objects.filter(status=True), required=False, label=u'Nivel',
                                             widget=forms.SelectMultiple(attrs={'formwidth': 'span12', 'buttons': [{'id': 'btn_nivel_all', 'label': 'Seleccionar todos', 'class': 'btn btn-primary', 'style': 'margin-right: 2px'},
                                                                                                                   {'id': 'btn_nivel_delete', 'label': 'Deseleccionar todos', 'class': 'btn btn-danger'}]}))
    sesiones = forms.ModelMultipleChoiceField(queryset=Sesion.objects.filter(status=True, clasificacion__in=[1,3], tipo=1), required=False, label=u'Sección', widget=forms.SelectMultiple(attrs={'formwidth': 'span12'}))
    fechainicio = forms.DateField(label=u"Desde (Fecha)", input_formats=['%d-%m-%Y'], initial=datetime.now().date().strftime('%d-%m-%Y'), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': 'span3'}), required=True)
    horainicio = forms.TimeField(label=u"Desde (Hora)", input_formats=['%H:%M'], initial=str(datetime.now().time()), widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': 'span3'}), required=True)
    fechafin = forms.DateField(label=u"Hasta (Fecha)", input_formats=['%d-%m-%Y'], initial=datetime.now().date().strftime('%d-%m-%Y'), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': 'span3'}), required=True)
    horafin = forms.TimeField(label=u"Hasta (Hora)", input_formats=['%H:%M'], initial=str(datetime.now().time()), widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': 'span3'}), required=True)
    activo = forms.BooleanField(initial=True, required=False, label=u'Activo', widget=forms.CheckboxInput({'formwidth': 'span12', 'class': 'js-switch'}))

    def set_initial(self, eCronogramaCarrera):
        self.fields['carrera'].initial = eCronogramaCarrera.carrera
        self.fields['fechainicio'].initial = eCronogramaCarrera.fechainicio
        self.fields['horainicio'].initial = eCronogramaCarrera.horainicio if eCronogramaCarrera.horainicio else datetime.now().time()
        self.fields['fechafin'].initial = eCronogramaCarrera.fechafin
        self.fields['horafin'].initial = eCronogramaCarrera.horafin if eCronogramaCarrera.horafin else datetime.now().time()
        self.fields['activo'].initial = eCronogramaCarrera.activo
        self.fields['niveles'].initial = eCronogramaCarrera.nivel.all()
        self.fields['sesiones'].initial = eCronogramaCarrera.sesion.all()

    def editar(self, eCronogramaCarrera):
        # deshabilitar_campo(self, 'coordinacion')
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=eCronogramaCarrera.carrera.id)

    def adicionar(self, eCronogramaCoordinacion):
        # self.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion=eCronogramaCoordinacion.coordinacion).exclude(pk__in=eCronogramaCoordinacion.cronogramacarreras().values_list("carrera_id", flat=True))
        self.fields['carrera'].queryset = Carrera.objects.filter(status=True, coordinacion=eCronogramaCoordinacion.coordinacion)

    def clean(self):
        cleaned_data = super(MatriculaCronogramaCarreraForm, self).clean()
        fechainicio = cleaned_data['fechainicio'] if 'fechainicio' in cleaned_data and cleaned_data['fechainicio'] else False
        horainicio = cleaned_data['horainicio'] if 'horainicio' in cleaned_data and cleaned_data['horainicio'] else False
        fechafin = cleaned_data['fechafin'] if 'fechafin' in cleaned_data and cleaned_data['fechafin'] else None
        horafin = cleaned_data['horafin'] if 'horafin' in cleaned_data and cleaned_data['horafin'] else None

        if not fechainicio:
            self.add_error('fechainicio', ValidationError('Favor seleccione una fecha inicio'))
        if not fechafin:
            self.add_error('fechainicio', ValidationError('Favor seleccione una fecha fin'))
        if not horainicio:
            self.add_error('horainicio', ValidationError('Favor seleccione una hora inicio'))
        if not horafin:
            self.add_error('horafin', ValidationError('Favor seleccione una hora fin'))
        fechahorainicio = datetime.combine(fechainicio, horainicio)
        fechahorafin = datetime.combine(fechafin, horafin)
        if fechahorainicio > fechahorafin:
            self.add_error('fechainicio', ValidationError('Favor seleccione una fecha y hora inicio menor a fin'))

        return cleaned_data


class PeriodoFinancieroForm2(forms.Form):
    porcentaje_gratuidad = forms.IntegerField(label=u"Porcentaje de gratuidad", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', "formwidth": "span6",  "separator": True}))
    valor_maximo = forms.FloatField(label=u'Valor máximo', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', "formwidth": "span6"}))

    def set_initial(self, ePeriodo):
        self.fields['porcentaje_gratuidad'].initial = ePeriodo.porcentaje_gratuidad
        self.fields['valor_maximo'].initial = ePeriodo.valor_maximo

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True


class PeriodoMallaForm(forms.Form):
    malla = forms.ModelChoiceField(queryset=Malla.objects.filter(status=True), required=False, label=u'Malla', widget=forms.Select(attrs={'formwidth': '100%'}))
    configuracion = forms.ModelChoiceField(queryset=ConfiguracionCalculoMatricula.objects.filter(status=True), required=False, label=u'Configuración', widget=forms.Select(attrs={'formwidth': 'span6'}))
    tipocalculo = forms.ChoiceField(label=u'Tipo', choices=TIPO_CALCULO_MATRICULA, widget=forms.Select(attrs={'formwidth': 'span3'}))
    vct = forms.FloatField(label=u'VCT', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', "formwidth": "span3"}))#span6

    def clean(self):
        cleaned_data = super(PeriodoMallaForm, self).clean()
        tipocalculo = int(cleaned_data['tipocalculo']) if 'tipocalculo' in cleaned_data and cleaned_data['tipocalculo'] else None
        vct = float(cleaned_data['vct']) if 'vct' in cleaned_data and cleaned_data['vct'] else None
        cleaned_data['tipocalculo'] = tipocalculo
        cleaned_data['vct'] = vct
        return cleaned_data

    def set_initial(self, ePeriodoMalla):
        self.fields['tipocalculo'].initial = ePeriodoMalla.tipocalculo
        self.fields['malla'].initial = ePeriodoMalla.malla
        self.fields['configuracion'].initial = ePeriodoMalla.configuracion
        self.fields['vct'].initial = ePeriodoMalla.vct

    def deshabilitar_campo(form, campo):
        form.fields[campo].widget.attrs['readonly'] = True
        form.fields[campo].widget.attrs['disabled'] = True

    def habilitar_campo(form, campo):
        form.fields[campo].widget.attrs['readonly'] = False
        form.fields[campo].widget.attrs['disabled'] = False


class GestionPermisosForm(forms.Form):
    modulo = forms.ModelChoiceField(queryset=Modulo.objects.filter(status=True).none(), required=False, label=u'Módulo', widget=forms.Select(attrs={'formwidth': '100%', 'class':'form-control select2', 'col': '12'}))
    permiso = forms.ModelChoiceField(queryset=Permission.objects.all().none(), required=False, label=u'Permiso', widget=forms.Select(attrs={'formwidth': '100%', 'class':'form-control select2', 'col': '12'}))
    descripcion = forms.CharField(label=u'¿Qué hace?', max_length=500, help_text=u"", required=False, widget=forms.Textarea({'rows': '10', 'class': 'form-control', 'col': '12', 'placeholder':'Describa brevemente la funcionalidad del permiso...'}))
    foto = ExtFileField(label=u'Ubicación en el sistema', required=False,help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304, widget=FileInput({'accept':' image/jpeg, image/jpg, image/png', 'col': '12'}))

    def edit(self, modulo, permiso):
        self.fields['modulo'].queryset = Modulo.objects.filter(pk=modulo)
        self.fields['permiso'].queryset = Permission.objects.filter(pk=permiso)
        self.fields['modulo'].initial = [modulo]
        self.fields['permiso'].initial = [permiso]


class EstandaresDesarrolloForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=200, required=False, widget=forms.Textarea({'rows': '10', 'class': 'form-control', 'col': '12', 'placeholder': 'Escriba su descripción aquí...'}))


class ContenidoIndiceForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=200, required=False, widget=forms.Textarea({'rows': '10', 'class': 'form-control', 'col': '12', 'placeholder': 'Escriba su descripción aquí...'}))
    categoriaindice = forms.ModelChoiceField(label='Categoria', queryset=CategoriaIndice.objects.filter(status=True), widget=forms.Select(attrs={'formwidth': '100%', 'class':'form-control select2', 'col': '12'}))


class ContenidoDocumentoForm(forms.Form):
    titulo = forms.CharField(label=u'Título', max_length=500, help_text=u"", required=True, widget=forms.TextInput({'class': 'form-control', 'col': '12', 'placeholder':'Describa el nombre del reporte...'}))
    texto = forms.CharField(label=u'Texto', max_length=200, required=False, widget=forms.Textarea({'rows': '10', 'class': 'form-control', 'col': '12', 'placeholder': 'Escriba su descripción aquí...'}))
    contenidoindice = forms.ModelChoiceField(label='Contenido', queryset=ContenidoIndice.objects.filter(status=True), widget=forms.Select(attrs={'formwidth': '100%', 'class':'form-control select2', 'col': '12'}))


class ReportesForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=500, help_text=u"", required=True, widget=forms.TextInput({'class': 'form-control', 'col': '12', 'placeholder':'Describa el nombre del reporte...'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=500, help_text=u"", required=True, widget=forms.Textarea({'rows': '3', 'class': 'form-control', 'col': '12', 'placeholder':'Describa la descripción...'}))
    detalle = forms.CharField(label=u'Detalle', max_length=500, help_text=u"", required=True, widget=forms.Textarea({'rows': '3', 'class': 'form-control', 'col': '12', 'placeholder':'Describa el detalle...'}))
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 20Mb, en formato jrxml', ext_whitelist=(".jrxml",), max_upload_size=20480000)
    categoria = forms.ModelChoiceField(queryset=CategoriaReporte.objects.filter(status=True), required=True, label=u'Categoría', widget=forms.Select(attrs={'formwidth': '100%', 'class':'form-control select2', 'col': '12'}))
    grupos = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=True, label=u'Grupos', widget=forms.SelectMultiple(attrs={'formwidth': '100%', 'class':'form-control select2', 'col': '12'}))
    interface = forms.BooleanField(initial=False, label=u"Interface", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    formatoxls = forms.BooleanField(initial=False, label=u"Formato xls", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    formatocsv = forms.BooleanField(initial=False, label=u"Formato csv", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    formatoword = forms.BooleanField(initial=False, label=u"Formato word", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    formatopdf = forms.BooleanField(initial=False, label=u"Formato pdf", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    certificado = forms.BooleanField(initial=False, label=u"Certificado", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    vista = forms.CharField(label=u'Vista', max_length=5000, help_text=u"", required=False, widget=forms.Textarea({'rows': '6', 'class': 'form-control', 'col': '12', 'placeholder':'Describa la descripción...'}))
    html = forms.CharField(label=u'Html', max_length=10000, help_text=u"", required=False, widget=forms.Textarea({'rows': '6', 'class': 'form-control', 'col': '12', 'placeholder':'Describa la descripción...'}))
    activosga = forms.BooleanField(initial=False, label=u"Activo para SGA", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    activosagest = forms.BooleanField(initial=False, label=u"Activo para SAGEST", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    activoposgrado = forms.BooleanField(initial=False, label=u"Activo para POSGRADO", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    versionreporte = forms.IntegerField(label=u'Versión de reporte', initial="1", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall','type':'number', 'min':'0','decimal': '0', "formwidth": "span3",'style': 'float:left;width:10%;margin-left:-25%;position:absolute'}))  # span6
    ejecutarcomoproceso = forms.BooleanField(initial=False, label=u"Ejecutar como proceso", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))
    enviarporcorreo = forms.BooleanField(initial=False, label=u"Enviar por correo", required=False,widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': 'span6','style': 'float:left;margin-left:-50%'}))

    def renombrar(self):
        self.fields['archivo'].widget.initial_text = "Anterior"
        self.fields['archivo'].widget.input_text = "Cambiar"

    def archivorequerido(self):
        self.fields['archivo'].required = True

    # def edit(self, modulo, permiso):
    #     self.fields['modulo'].queryset = Modulo.objects.filter(pk=modulo)
    #     self.fields['permiso'].queryset = Permission.objects.filter(pk=permiso)
    #     self.fields['modulo'].initial = [modulo]
    #     self.fields['permiso'].initial = [permiso]


class ImagenMoodleForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción de la foto', max_length=500, help_text=u"", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    imagen = ExtFileField(label=u'Ubicación en el sistema', required=False,help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304, widget=FileInput({'accept':' image/jpeg, image/jpg, image/png', 'col': '12'}))


class CodeTwoStepVerificationForm(forms.Form):
    code_1 = forms.CharField(label=u'Código 1', max_length=1, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    code_2 = forms.CharField(label=u'Código 2', max_length=1, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    code_3 = forms.CharField(label=u'Código 3', max_length=1, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    code_4 = forms.CharField(label=u'Código 4', max_length=1, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    code_5 = forms.CharField(label=u'Código 5', max_length=1, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    code_6 = forms.CharField(label=u'Código 6', max_length=1, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def codigo(self):
        return f"{self.cleaned_data['code_1']}{self.cleaned_data['code_2']}{self.cleaned_data['code_3']}{self.cleaned_data['code_4']}{self.cleaned_data['code_5']}{self.cleaned_data['code_6']}"

#------------------------------------------------------------------
class ProcesoSCRUMForm(FormModeloBase):
    direccion = forms.ModelChoiceField(label=u"Dirección responsable del proceso", queryset=Departamento.objects.filter(status=True,integrantes__isnull=False).distinct(), required=True, widget=forms.Select({'col': '12', 'class':'select2'}))
    gestion_recepta = forms.ModelChoiceField(label=u"Gestión que recepta los requisitos", queryset=SeccionDepartamento.objects.filter(status=True).distinct(), required=True, widget=forms.Select({'col': '12', 'class':'select2'}))
    descripcion = forms.CharField(label=u'Proceso', required=True, widget=forms.Textarea({'col': '12', 'rows': '2', 'placeholder':'Describa el proceso que se vincula a la dirección...'}))
    equipos = forms.ModelMultipleChoiceField(label='Equipos', required=True, queryset=EquipoSCRUM.objects.filter(status=True), widget=forms.SelectMultiple(attrs={'class': 'select2'}))
    # estado = forms.ChoiceField(label=u'Estado', choices=((1, u'Activa'), (2, u'Inactiva')), required=True, widget=forms.Select(attrs={'class': 'imp-100', 'col': '6'}))
#                                )
    def clean(self):
        cleaned_data = super().clean()
        descripcion = cleaned_data.get('descripcion')
        id = getattr(self.instancia, 'id', 0)
        if ProcesoSCRUM.objects.filter(descripcion__unaccent__iexact=descripcion, status=True).exclude(id=id):
            self.add_error('descripcion', 'Ya existe un proceso con el mismo nombre.')
        return cleaned_data
#------------------------------------------------------------------
class IncidenciaSCRUMForm(FormModeloBase):
    categoria = forms.ModelChoiceField(label=u"Proceso", queryset=ProcesoSCRUM.objects.filter(status=True).distinct(), required=True, widget=forms.Select({'col': '12', 'class':'select2'}))
    titulo = forms.CharField(label=u'Título', required=True, widget=forms.TextInput({'col': '12', 'placeholder': 'Describa un título a su tarea'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa a detalle lo requerido...'}), required=False)
    asignadoa = forms.ModelChoiceField(label=u"Asignado a",queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    finicioactividad = forms.DateTimeField(label=u"F. inicio de la actividad", required=False, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '3','type':'date'}))
    ffinactividad = forms.DateTimeField(label=u"F. fin de la actividad", required=False, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '3', 'type':'date'}))
    app = forms.ChoiceField(choices=APP_LABEL, required=True, label=u'Sistema', widget=forms.Select(attrs={'col': '3', 'class': 'select2'}))
    prioridad = forms.ChoiceField(choices=PRIORIDAD_REQUERIMIENTO, required=True, label=u'Prioridad',widget=forms.Select(attrs={'col': '3',  'class': 'select2'}))
    #asignadopor = forms.ModelChoiceField('sga.Persona', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Asignado por', related_name='+')


    def set_fechas(self, obj):
        self.fields['finicioactividad'].initial = obj.finicioactividad.strftime('%d-%m-%Y') if obj.finicioactividad else ''
        self.fields['ffinactividad'].initial = obj.ffinactividad.strftime('%d-%m-%Y') if obj.ffinactividad else ''


class CrearSolicitudForm(FormModeloBase):
    asignadopor = forms.ModelChoiceField(label=u"Asignado por", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), widget=forms.Select(attrs={'col': '12'}))
    categoria = forms.ModelChoiceField(label=u"Proceso", queryset=ProcesoSCRUM.objects.filter(status=True).distinct(), required=False, widget=forms.Select({'col': '12'}))
    titulo = forms.CharField(label=u'Título', max_length=100, required=True, widget=forms.TextInput({'col': '12'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    app = forms.ChoiceField(choices=APP_LABEL, required=False, label=u'Sistema', widget=forms.Select(attrs={'col': '3'}))
    finicioactividad = forms.DateField(label=u"Fecha que inicio la actividad", required=True, widget=DateTimeInput({'col': '4'}))
    prioridad = forms.ChoiceField(choices=PRIORIDAD_REQUERIMIENTO, required=True, label=u'Prioridad', widget=forms.Select(attrs={'col': '4'}))


class CrearComentarioForm(FormModeloBase):
    incidencia = forms.ModelChoiceField(queryset=IncidenciaSCRUM.objects.filter(status=True).distinct(), required=True, widget=forms.HiddenInput())
    categoria = forms.ModelChoiceField(label=u"Proceso", queryset=ProcesoSCRUM.objects.filter(status=True).distinct(), required=False, widget=forms.Select({'col': '12', 'class':'select2'}))
    asignadoa = forms.ModelChoiceField(label=u"Asignado a",queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=False, widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    observacion = forms.CharField(label=u"Comentario", widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    archivo = ExtFileField(label=u'Archivo solicitud', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",".doc",".docx",".xls",".xlsx"), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))




class CrearActvSecundariaForm(FormModeloBase):
    incidencia = forms.ModelChoiceField(queryset=IncidenciaSCRUM.objects.filter(status=True).distinct(),required=False,widget=forms.HiddenInput())
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    asignadoa = forms.ModelChoiceField(label=u"Asignado a",queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), widget=forms.Select(attrs={'col': '12'}))
    prioridad = forms.ChoiceField(choices=PRIORIDAD_REQUERIMIENTO, required=True, label=u'Prioridad', widget=forms.Select(attrs={'col': '6'}))
    finicioactividad = forms.DateField(label=u"Fecha que inicio la actividad", required=True, widget=forms.DateInput(attrs={'col': '6','type': 'date', 'min': datetime.now().strftime('%Y-%m-%d')}))

    def set_fecha(self, obj):
        self.fields['finicioactividad'].initial = datetime.now().date()

    def clean_finicioactividad(self):
        finicioactividad = self.cleaned_data['finicioactividad']
        if finicioactividad < datetime.now().date():
            raise ValidationError("La fecha de inicio no puede ser anterior a la fecha actual")
        return finicioactividad

class OpcionSistemaForm(forms.Form):
    modulo = forms.ModelChoiceField(queryset=Modulo.objects.filter(status=True), required=True,
                                       label=u'Módulo',
                                       widget=forms.Select(attrs={'class': 'form-control select2', 'col': '6'}))
    nombre = forms.CharField(label=u"Nombre", max_length=200,
                             widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6'}), required=True)
    proceso = forms.ModelChoiceField(queryset=ProcesoOpcionSistema.objects.filter(status=True), required=False,
                                     label=u'Proceso',
                                     widget=forms.Select(attrs={'class': 'form-control select2', 'col': '6'}))
    tipo = forms.ModelChoiceField(queryset=TipoOpcionSistema.objects.filter(status=True), required=False,
                                  label=u'Tipo',
                                  widget=forms.Select(attrs={'class': 'form-control select2', 'col': '6'}))
    url = forms.CharField(label=u'URL', initial='',
                            widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6', 'placeholder':'/sistemas?action=EjemploAction'}), required=True)
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '3', 'col': '6', 'placeholder':'Describa brevemente la funcionalidad de la opción...'}), required=True)
    archivo = ExtFileField(label=u'Imagen', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png',
                           ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(
                           attrs={'accept':' image/jpeg, image/jpg, image/png', 'col': '12', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    preguntauxplora = forms.CharField(label=u"Pregunta auxplora", widget=forms.Textarea(attrs={'class': 'form-control', 'col': '12', 'placeholder':'Escriba la pregunta para uxplora ...'}), required=False)
    activo = forms.BooleanField(label=u'Activo para uxplora', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))
    posicion_x = forms.FloatField(label=u'Posición X de la opcion en imagen uxplora', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'col': '4'}))
    posicion_y = forms.FloatField(label=u'Posición Y de la opcion en imagen uxplora', required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'col': '4'}))
    ratio = forms.IntegerField(label=u'Ratio de la opcion en imagen uxplora', required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'col': '4'}))

class TipoOpcionSistemaForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}), required=True)

class ProcesoOpcionSistemaForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}), required=True)

class EquipoForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={'placeholder': 'Describa el nombre del equipos', 'col': '12'}), required=True)
    descripcion = forms.CharField(label=u"Descripción", max_length=200, widget=forms.Textarea(attrs={'placeholder': 'Describa a que se dedica su equipo', 'col': '12', 'rows':'2'}), required=True)
    lider = forms.ModelChoiceField(label='Lider', queryset=Persona.objects.filter(status=True), widget=forms.Select(attrs={'class': 'select2'}))
    integrantes = forms.ModelMultipleChoiceField(label='Integrantes', queryset=Persona.objects.filter(status=True), widget=forms.SelectMultiple(attrs={'class': 'select2'}))
    esgestor = forms.BooleanField(label='Es equipo gestor', required=False, widget=forms.CheckboxInput(attrs={'data-switchery': True}))

class AsignarActividadForm(FormModeloBase):
    categoria = forms.ModelChoiceField(label=u"Proceso", queryset=ProcesoSCRUM.objects.filter(status=True).distinct(), required=True, widget=forms.Select({'col': '12', 'class':'select2'}))
    asignadoa = forms.ModelChoiceField(label=u"Asignado a",queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    finicioactividad = forms.DateField(label=u"Inicio", input_formats=['%Y-%m-%d'],required=False, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '4'}))
    ffinactividad = forms.DateField(label=u"Fin", input_formats=['%Y-%m-%d'], required=False, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '4'}))
    app = forms.ChoiceField(choices=APP_LABEL, required=True, label=u'Sistema', widget=forms.Select(attrs={'col': '4', 'class': 'select2'}))


class ProcesoPythonForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', required=True, widget=forms.TextInput({'placeholder':'Nombre del proceso'}))
    descripcion = forms.CharField(label=u'Descripción', required=True, widget=forms.Textarea({'col': '12', 'rows': '2', 'placeholder':'Describa la funcionalidad del proceso'}))
    tipo = forms.ChoiceField(label='Tipo de ejecución', required=True, choices=TIPO_EJECUTOR, widget=forms.Select(attrs={'class': 'select2'}))
    code = forms.CharField(widget=forms.Textarea(attrs={'rows': 5, 'cols': 40, 'placeholder':'Escriba aquí el código de python, recuerde revisar '
    'cada accion que el proceso ejecutará, si desea utilizar el archivo anexo, utlice la variable "path_anexo" en lugar del nombre del archivo, si va ejecutar más de una '
    'una funcion, utilice la siguiente sintaxis para llamar a la o las funciones:   funcionlocal.get("nombre de la funcion")()  no es necesario agregar la variable funcionlocal'}))
    archivo = ExtFileField(label=u'Archivo', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato py',
                           ext_whitelist=".py", max_upload_size=8388608, widget=forms.FileInput(
            attrs={'accept': 'py', 'col': '12', 'data-allowed-file-extensions': 'py'}))
    anexo = ExtFileField(label=u'Archivo anexo al proceso', required=False,
                         help_text=u'Tamaño Maximo permitido 25Mb, en formato xls, xlsx',
                         ext_whitelist=".xls, .xlsx", max_upload_size=26214400, widget=forms.FileInput(
            attrs={'accept': 'py', 'col': '12', 'data-allowed-file-extensions': '.xls, .xlsx'}))

    def edit(self, id):
        instancia = PythonProcess.objects.get(id=id)
        if instancia.anexo:
            self.fields['anexo'].widget.attrs['value'] = instancia.anexo.path
        if instancia.archivo:
            self.fields['archivo'].widget.attrs['value'] = instancia.archivo.path
        if instancia.code:
            self.fields['code'].widget.attrs['value'] = instancia.code

    # def clean(self):
    #     cleaned_data = super().clean()
    #     descripcion = cleaned_data.get('descripcion')
    #     id = getattr(self.instancia, 'id', 0)
    #     if ProcesoSCRUM.objects.filter(descripcion__unaccent__iexact=descripcion, status=True).exclude(id=id):
    #         self.add_error('descripcion', 'Ya existe un proceso con el mismo nombre.')
    #     return cleaned_data


class PlanificacionForm(FormModeloBase):
    departamento = forms.ModelChoiceField(label='Dirección', queryset=Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), widget=forms.Select(attrs={'class': 'select2'}), required=True)
    nombre = forms.CharField(label=u"Nombre", max_length=200, widget=forms.TextInput(attrs={'placeholder': 'Describa el nombre de la planificación', 'col': '12'}), required=True)
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%Y-%m-%d'], required=True, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%Y-%m-%d'], required=True, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    mostrar = forms.BooleanField(label='¿Mostrar?', required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'data-switchery': True}))
    detalle = forms.CharField(label=u"Detalle", max_length=200, widget=forms.Textarea(attrs={'placeholder': 'Describa un detalle de la planificación', 'col': '12', 'rows': '5'}), required=True)


class RequerimientoForm(FormModeloBase):
    departamento = forms.ModelChoiceField(label='Dirección', queryset=Departamento.objects.filter(status=True, integrantes__isnull=False).distinct(), widget=forms.Select(attrs={'col': '6','class': 'select2'}), required=True)
    gestion = forms.ModelChoiceField(label=u'Gestión', queryset=SeccionDepartamento.objects.select_related().filter(status=True, departamento__integrantes__isnull=False).distinct(), widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    prioridad = forms.ChoiceField(label=u'Prioridad', choices=PRIORIDAD, initial=1, required=True, widget=forms.Select({'col': '6', 'class': 'select2'}))
    tiporequerimiento = forms.ChoiceField(choices=TIPO_REQUERIMIENTO_AUTOMATIZA, initial=1, required=True, label=u'Tipo', widget=forms.Select({'col': '6', 'class': 'select2'}))
    responsable = forms.ModelChoiceField(label=u'Responsable', queryset=Persona.objects.select_related().filter(status=True), required=True, widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    procedimiento = forms.CharField(label=u'Título', required=True, widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Describa el título de del requerimiento...'}))
    detalle = forms.CharField(label=u'Detalle', required=True, widget=forms.Textarea(attrs={'col': '12', 'placeholder': 'Describa a detalle lo que se requiere...'}))

    def filtro_gestion(self, iddepartamento):
        self.fields['gestion'].queryset = SeccionDepartamento.objects.filter(status=True, departamento_id=iddepartamento).distinct()

class InformeRequerimientosPoaForm(FormModeloBase):
    INDICADOR_POA = [choice for choice in ESTADO_INDICADOR_POA if choice[0] != 3]

    fechadesde = forms.DateField(label=u"Desde", input_formats=['%Y-%m-%d'], required=False, initial='2024-01-01',
                                  widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '3'}))
    fechahasta = forms.DateField(label=u"Hasta", input_formats=['%Y-%m-%d'], required=False, initial=datetime.now().date(),
                               widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '3'}))
    estado = forms.MultipleChoiceField(choices=ESTADO_REQUERIMIENTO, required=True, label=u'Estado',
                                       initial=[choice[0] for choice in ESTADO_REQUERIMIENTO],
                                       widget=forms.SelectMultiple(attrs={'class': 'select2', 'col': '6'}))
    indicador = forms.MultipleChoiceField(choices=INDICADOR_POA, required=True, label=u'Indicador',
                                          initial=[choice[0] for choice in INDICADOR_POA],
                                        widget=forms.SelectMultiple(attrs={'class': 'select2', 'col': '12'}))
    responsable = forms.ModelChoiceField(label=u'Responsable de firma', queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=False,
                                     widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

    def clean(self):
        cleaned_data = super().clean()
        fecha_desde = cleaned_data.get('fechadesde')
        fecha_hasta = cleaned_data.get('fechahasta')
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            self.add_error('fechahasta', 'El rango de fechas no es válido')
        return cleaned_data