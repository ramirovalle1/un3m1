# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q
from django.forms import DateInput

from pdip.models import PerfilPuestoDip, CertificacionPresupuestariaDip
from postulaciondip.models import TipoDocente, Convocatoria, PersonalAContratar, ActaParalelo, TipoPersonal, \
    TIPO_CONVOCATORIA, ESTADOS_PROCESO, ESTADO_REVISION, PasosProceso, TIPOREVISOR, TipoProceso, ActaSeleccionDocente, \
    Requisito, PersonalApoyo, RolPersonalApoyo, Periodo, ClasificacionDocumentoInvitacion, DocumentoInvitacion, \
    SecuenciaDocumentoInvitacion, ComiteAcademicoPosgrado, IntegranteComiteAcademicoPosgrado, InscripcionConvocatoria, \
    TIPO_CARGO_CHOICE, MensajePredeterminado, TIPO_FORMATO_ACTA, TiempoDedicacion, ResponsabilidadFirma, \
    OrdenFirmaInformeContratacion, VALOR_X_HORA, ESTADO_REVISION_PARALELO
from sagest.models import DenominacionPuesto, Banco, TipoCuentaBanco
from sga.models import Persona, ProfesorMateria, Paralelo, Administrativo, Carrera, Pais, Provincia, Canton, Parroquia, Titulo, InstitucionEducacionSuperior, TIPO_CELULAR, Discapacidad, InstitucionBeca, AreaConocimientoTitulacion, SubAreaConocimientoTitulacion,SubAreaEspecificaConocimientoTitulacion, TipoProfesor, PerfilUsuario, Materia, Malla, DIAS_CHOICES, Turno
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from inno.models import PerfilRequeridoPac
from django.core.exceptions import ValidationError
from sga.funciones import variable_valor

class CheckboxSelectMultipleCustom(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(CheckboxSelectMultipleCustom, self).render(*args, **kwargs)
        return mark_safe(output.replace(u'<ul>', u'<div class="custom-multiselect" style="width: 600px;overflow: scroll"><ul>').replace(u'</ul>', u'</ul></div>').replace(u'<li>', u'').replace(u'</li>', u'').replace(u'<label', u'<div style="width: 900px"><li').replace(u'</label>', u'</li></div>'))


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


class RegistroForm(forms.Form):
    cedula = forms.CharField(label=u"Cédula", max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellidos1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))


class RegistroForm1(forms.Form):
    cedula = forms.CharField(label=u"Cédula", max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellidos = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))


class RequisitosMaestriaForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760)


class RequisitosMaestriaImgForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato jpg o png', ext_whitelist=(".jpeg", ".jpg", ".png", ".JPEG", ".JPG", ".PNG"), max_upload_size=10485760)


class RegistroAdmisionIpecForm(forms.Form):
    cedula = forms.CharField(label=u"Cédula", max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefono = forms.CharField(label=u"Teléfono", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))


class RequisitosConvocatoriaInscripcionForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=FileInput({'style':'width:100%;', 'class':'form-control', 'col': '12', 'accept': 'application/pdf'}))

    def del_observacion(self):
        del self.fields['observacion']


class ConvocatoriaForm(forms.Form):
    hoy = datetime.now().date()
    nombre = forms.CharField(label=u'Nombre de la Convocatoria', required=True, help_text="", widget=forms.Textarea(attrs={'rows': '5', 'class': 'form-control', 'col':'12'}))
    perfilrequeridopac = forms.ModelMultipleChoiceField(required=True, queryset=PerfilRequeridoPac.objects.filter(status=True), label=u'Perfil requerido',widget=forms.SelectMultiple(attrs={'class':'form-control', 'col':'12', 'style':'width:100%'}))
    carrera = forms.ModelChoiceField(label=u'Maestría ', required=False, queryset=Carrera.objects.filter(Q(Q(niveltitulacion_id=4) | Q(coordinacion__id=7)), status=True), widget=forms.Select(attrs={'class': '', 'col': '12'}))
    campoamplio = forms.ModelMultipleChoiceField(label=u"Campo amplio",queryset=AreaConocimientoTitulacion.objects.filter(status=True), required=True, widget=forms.SelectMultiple(attrs={'class': 'form-control', 'col':'12'}))
    campoespecifico = forms.ModelMultipleChoiceField(label=u"Campo especifico",queryset=SubAreaConocimientoTitulacion.objects.filter(status=True), required=False,widget=forms.SelectMultiple(attrs={'class': 'form-control', 'col':'12'}))
    campodetallado = forms.ModelMultipleChoiceField(label=u"Campo detallado",queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True), required=False,widget=forms.SelectMultiple(attrs={'class': 'form-control', 'col':'12'}))
    tipodocente = forms.ModelChoiceField(label=u'Tipo de Docente', required=False, queryset=TipoProfesor.objects.filter(status=True), widget=forms.Select(attrs={'class': 'imp-50', 'col':'12'}))
    tiempodedicacion = forms.ModelChoiceField(label=u'Tiempo dedicación', required=False, queryset=TiempoDedicacion.objects.filter(status=True), widget=forms.Select(attrs={'class': 'imp-50', 'col':'12'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", input_formats=['%d-%m-%Y'], initial=hoy, required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'form-control', 'autocomplete':'off', 'col':'6'}))
    fechafin = forms.DateField(label=u"Fecha Fin", input_formats=['%d-%m-%Y'], initial=hoy, required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'form-control', 'autocomplete':'off', 'col':'6'}))
    # activo = forms.BooleanField(label=u"Estado (Activo o Inactivo)", required=False, widget=forms.CheckboxInput(attrs={'class':'js-switch', 'col':'12'}))
    vacantes = forms.CharField(label=u"Vacantes", initial=1, required=False, widget=forms.NumberInput(attrs={'class':'form-control', 'col':'6'}))
    paralelos = forms.CharField(label=u"Cantidad de paralelos ", initial=1, required=False, widget=forms.NumberInput(attrs={'class':'form-control', 'col':'6'}))
    periodo = forms.ModelChoiceField(label=u'Cohorte', required=False, queryset=Periodo.objects.filter(status=True), widget=forms.Select(attrs={'class': 'imp-50', 'col': '12'}))
    # tipo = forms.ChoiceField(choices=TIPO_CONVOCATORIA, label=u'Tipo de convocatoria ', initial=1, required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    perfiles_cumplen = forms.IntegerField(initial=0, label=u'Perfil cumplen', required=False, widget=forms.TextInput(attrs={'class': 'imp-number ','disabled':'True', 'decimal': '0'}))
    fechainiciohorario = forms.DateField(label=u"Fecha Inicio horario", initial=hoy, required=False, widget=DateTimeInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'col': '6' , 'type':'date'}))
    fechafinhorario = forms.DateField(label=u"Fecha Fin horario", initial=hoy, required=False, widget=DateTimeInput(attrs={'class': 'form-control', 'autocomplete': 'off', 'col': '6', 'type':'date'}))

    def initial_values(self, tipo):
        if tipo == 1:
            del self.fields['carrera']
        elif tipo == 2:
            del self.fields['perfilrequeridopac']
            #del self.fields['tipo']

    def modificar(self, titulacion):
        self.fields['perfilrequeridopac'].widget.attrs['descripcion'] = titulacion.titulo
        self.fields['perfilrequeridopac'].initial = titulacion.id
        self.fields['perfilrequeridopac'].widget.attrs['value'] = titulacion.id

    def set_perfilrequerido(self, pk, init=None, carrera=None):
        prp = PerfilRequeridoPac.objects.filter(personalacademico__asignaturaimpartir__asignatura_id=pk, personalacademico__asignaturaimpartir__asignatura__status=True, personalacademico__asignaturaimpartir__status=True, personalacademico__status=True, titulacion__titulo__status=True, status=True)
        init = list(prp.values_list('id', flat=True)) if not init else None
        self.fields['perfilrequeridopac'].queryset = prp
        self.fields['perfilrequeridopac'].initial = init
        if carrera:
            self.fields['periodo'].queryset = Periodo.objects.filter(status=True, id__in=Materia.objects.filter(asignaturamalla__malla__carrera_id=carrera).values_list('nivel__periodo_id', flat=True))

        campo_amplio_set = set()
        campo_especifico_set = set()
        campo_detallado_set = set()

        if prp.exists():
            for ePerfilRequeridoPac in prp:
                campoamplios = ePerfilRequeridoPac.titulacion.campoamplio.filter(status=True,tipo=1)
                campoespecificos = ePerfilRequeridoPac.titulacion.campoespecifico.filter(status=True,tipo=1)
                campodetallados = ePerfilRequeridoPac.titulacion.campodetallado.filter(status=True,tipo=1)
                # Add campoamplios to the campo_amplio_set
                campo_amplio_set.update(campoamplios.values_list('id', flat=True))
                # Add campoespecificos to the campo_especifico_set
                campo_especifico_set.update(campoespecificos.values_list('id', flat=True))
                # Add campodetallados to the campo_detallado_set
                campo_detallado_set.update(campodetallados.values_list('id', flat=True))

            # Convert the sets to lists and assign them to the respective fields
            self.set_campo_amplio(list(campo_amplio_set))
            self.set_campo_especifico(list(campo_especifico_set))
            self.set_campo_detallado(list(campo_detallado_set))

    def set_campo_amplio(self, ids):
        unique_ids = set(ids)
        if not len(unique_ids) != len(ids):
            eAreaConocimientoTitulacion = AreaConocimientoTitulacion.objects.filter(pk__in=unique_ids).order_by('codigo')
            self.fields['campoamplio'].queryset = eAreaConocimientoTitulacion
            self.fields['campoamplio'].initial =eAreaConocimientoTitulacion

    def set_campo_especifico(self, ids):
        unique_ids = set(ids)
        if not len(unique_ids) != len(ids):
            eSubAreaConocimientoTitulacion = SubAreaConocimientoTitulacion.objects.filter(pk__in=unique_ids).order_by('codigo')
            self.fields['campoespecifico'].queryset = eSubAreaConocimientoTitulacion
            self.fields['campoespecifico'].initial = eSubAreaConocimientoTitulacion

    def set_campo_detallado(self, ids):
        unique_ids = set(ids)
        if not len(unique_ids) != len(ids):
            eSubAreaEspecificaConocimientoTitulacion = SubAreaEspecificaConocimientoTitulacion.objects.filter(pk__in=unique_ids).order_by('codigo')
            self.fields['campodetallado'].queryset = eSubAreaEspecificaConocimientoTitulacion
            self.fields['campodetallado'].initial = eSubAreaEspecificaConocimientoTitulacion

    def delete_tipo_docente(self):
        del self.fields['tipodocente']

    def quitar_campos_tipo_convocatoria_normal(self):
        del self.fields['tiempodedicacion']

    def quitar_campos_por_docente_invitado(self):
        del self.fields['perfiles_cumplen']
        del self.fields['perfilrequeridopac']
        del self.fields['campoamplio']
        del self.fields['campoespecifico']
        del self.fields['campodetallado']

    def establecer_requerido_false(self):
        self.fields['perfiles_cumplen'].required = False
        self.fields['perfilrequeridopac'].required = False
        self.fields['campoamplio'].required = False
        self.fields['campoespecifico'].required = False
        self.fields['campodetallado'].required = False

    def requeridos(self):
        self.fields['tiempodedicacion'].required = True

class RequisitoForm(forms.Form):
    nombre = forms.CharField(label=u'Título:', widget=forms.TextInput(attrs={'class': 'form-control', 'col':'12'}))
    observacion = forms.CharField(label=u'Observación:', widget=forms.Textarea(attrs={'rows': '3', 'col':'12'}), required=True)
    archivo = ExtFileField(label=u'Archivo:', required=False, help_text=u'Tamaño máximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf", ".doc", "docx", ".DOC", "DOCX", ), max_upload_size=10485760, widget=FileInput({'style': 'width:100%;', 'class': 'form-control', 'col': '12', 'accept':'.doc, .docx, application/pdf'}))
    activo = forms.BooleanField(label=u"¿Activo?", initial=True, required=False, widget=forms.CheckboxInput(attrs={'class':'js-switch', 'col':'12'}))
    #tipoarchivo = forms.ChoiceField(label=u"Tipo de archivo", choices=TIPO_ARCHIVO, required=False, widget=forms.Select(attrs={'col':'12', 'class':'form-control', 'style':'width:100%'}))

class RequisitoUpdateOpcionalForm(forms.Form):
    opcional = forms.BooleanField(label=u"¿opcional?", initial=True, required=False, widget=forms.CheckboxInput(attrs={'class':'js-switch', 'col':'12'}))


class ClasificacionACForm(forms.Form):
    codigo = forms.CharField(label=u'Código',required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(label=u'Descripción', required=True, widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control'}))
    nivel = forms.IntegerField(initial="", label=u'Nivel en número', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'decimal': '0', 'onKeyPress': "return soloNumeros(event)"}))
    activo = forms.BooleanField(label=u"¿Activo para postulante?", required=False, widget=forms.CheckboxInput())


class DatoPersonalForm(forms.Form):
    nombres = forms.CharField(label=u'Nombres', max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    apellido1 = forms.CharField(label=u'Apellido Paterno', max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'6'}))
    apellido2 = forms.CharField(label=u'Apellido Materno', max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'6'}))
    telefono = forms.CharField(label=u'Celular', max_length=10, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'6'}))
    email = forms.CharField(label=u"Correo Electronico Personal", max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'6'}))


class ExperienciaLaboralForm(forms.Form):
    institucion = forms.CharField(label=u'Lugar', max_length=250, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'12'}))
    cargo = forms.CharField(label=u'Cargo', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'12'}))
    fechainicio = forms.DateField(label=u"Inicio", widget=DateInput(attrs={'class': 'form-control', 'col':'6', 'formwidth':'50%', 'type':'date'}))
    fechafin = forms.DateField(label=u"Fin", required=False, widget=DateInput(attrs={'class': 'form-control', 'col':'6', 'formwidth':'50%', 'type':'date'}))
    vigente = forms.BooleanField(label=u"¿Actualmente trabaja aquí?", required=False, widget=forms.CheckboxInput(attrs={'class':'js-switch'}))


class TitulacionPersonaForm(forms.Form):
    titulo = forms.ModelChoiceField(label=u"Titulo", queryset=Titulo.objects.all(), required=False, widget=forms.Select(attrs={'fieldbuttons': [{'id': 'add_registro_titulo', 'tooltiptext': 'Agregar titulo', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-plus'}]}))
    # areatitulo = forms.ModelChoiceField(label=u"Area de titulalción", queryset=AreaTitulo.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '80%'}))
    # fechainicio = forms.DateField(label=u"Fecha inicio de estudios", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'imp-number'}))
    # educacionsuperior = forms.BooleanField(label=u'Educación superior', required=False, widget=CheckboxInput())
    institucion = forms.ModelChoiceField(label=u"Institución de educación superior", queryset=InstitucionEducacionSuperior.objects.all(), required=False, widget=forms.Select())
    # colegio = forms.ModelChoiceField(label=u"Colegio", queryset=Colegio.objects.all(), required=False, widget=forms.Select())
    # cursando = forms.BooleanField(label=u'Cursando', required=False, widget=CheckboxInput())
    fechaobtencion = forms.DateField(label=u"Fecha de obtención", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    # fechaegresado = forms.DateField(label=u"Fecha de egreso", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    registro = forms.CharField(label=u'Número de registro SENESCYT', max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    # registroarchivo = ExtFileField(label=u'Seleccione Archivo SENESCYT', required=False, help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)
    archivo = ExtFileField(label=u'Seleccione Archivo Título', required=False, help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '80%'}))
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '80%'}))
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '80%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '80%'}))
    # semestres = forms.IntegerField(initial=0, label=u'Semestres cursados', required=False, widget=forms.TextInput( attrs={'class': 'imp-numbersmall', 'formwidth': '25%', 'decimal': '0'}))
    # aplicobeca = forms.BooleanField(label=u'Aplico a una beca', required=False, widget=CheckboxInput())
    # tipobeca = forms.ChoiceField(label=u"Tipo de beca", required=False, choices=TIPO_BECA, widget=forms.Select(attrs={'class': 'imp-25', 'formwidth': '40%'}))
    # financiamientobeca = forms.ModelChoiceField(label=u"Tipo de financiamiento de la beca", required=False, queryset=FinanciamientoBeca.objects.all(), widget=forms.Select(attrs={'class': 'imp-50', 'formwidth': '70%'}))
    # valorbeca = forms.DecimalField(initial="0.00", label=u'Valor beca', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))
    areaconocimiento = forms.ModelMultipleChoiceField(label=u"Campo Amplio",
                                                    queryset=AreaConocimientoTitulacion.objects.filter(
                                                        status=True, tipo=1, vigente=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(
                                                    attrs={'style':'text-transform:capitalize;',  'class': 'form-control', 'separator2': True, 'separatortitle': 'Datos del Título', }))
    subareaconocimiento = forms.ModelMultipleChoiceField(label=u"Campo Especifico",
                                                     queryset=SubAreaConocimientoTitulacion.objects.filter(
                                                         status=True).order_by('codigo'), required=False,
                                                     widget=forms.SelectMultiple(attrs={'style':'text-transform:capitalize;', 'class': 'form-control'}))
    subareaespecificaconocimiento = forms.ModelMultipleChoiceField(label=u"Campo Detallado",
                                                    queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(
                                                        status=True).order_by('codigo'), required=False,
                                                    widget=forms.SelectMultiple(attrs={'style':'text-transform:capitalize;', 'class': 'form-control'}))

    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)

    def editar(self, titulo):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=titulo.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=titulo.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=titulo.canton)


class DatosDomicilioForm(forms.Form):
    pais = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.all(), required=True, widget=forms.Select())
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects.all(), required=False, widget=forms.Select())
    canton = forms.ModelChoiceField(label=u"Cantón de residencia", queryset=Canton.objects.all(), required=False,  widget=forms.Select())
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select())
    direccion = forms.CharField(label=u'Calle principal', max_length=100, required=True, widget=forms.TextInput())
    direccion2 = forms.CharField(label=u'Calle secundaria', max_length=100, required=True, widget=forms.TextInput())
    num_direccion = forms.CharField(label=u'Número de casa', max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    referencia = forms.CharField(label=u'Referencia', max_length=100, required=True, widget=forms.TextInput())
    sector = forms.CharField(label=u'Sector', max_length=100, required=True, widget=forms.TextInput())
    telefono = forms.CharField(label=u'Teléfono celular', max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    telefono_conv = forms.CharField(label=u'Teléfono domicilio (fijo)', max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    tipocelular = forms.ChoiceField(label=u'Operadora móvil', choices=TIPO_CELULAR, required=True, widget=forms.Select(attrs={'class': 'imp-50'}))
    archivocroquis = ExtFileField(label=u'Croquis', required=False, help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=2194304)

    def editar(self, persona):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)


class DiscapacidadForm(forms.Form):
    tienediscapacidad = forms.BooleanField(label=u'Tiene Discapacidad?', required=False, widget=CheckboxInput())
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad", queryset=Discapacidad.objects.filter(status=True), required=False, widget=forms.Select())
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet Discapacitado', max_length=50, required=False, widget=forms.TextInput())
    archivo = ExtFileField(label=u'Carnet de Discapacidad', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304)
    institucionvalida = forms.ModelChoiceField(label=u"Institución Valida", queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True), required=False, widget=forms.Select())

    def ocultarcampos(self):
        del self.fields['tienediscapacidad']

    def bloquearcampos(self):
        deshabilitar_campo(self, 'tipodiscapacidad')

class ArchivoInvitacionForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True, help_text=u'Tamaño Maximo permitido 6Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=6291456, widget=FileInput({'style':'width:100%;', 'class':'form-control', 'col': '12', 'accept': 'application/pdf'}))

class RequisitosInscripcionForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=FileInput({'style':'width:100%;', 'class':'form-control', 'col': '12', 'accept': 'application/pdf'}))

class RequisitosPersonalContratarForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=FileInput({'style':'width:100%;', 'class':'form-control', 'col': '12', 'accept': 'application/pdf'}))
    fecha_caducidad = forms.DateField(label=u'Fecha caducidad', required=False, widget=forms.TextInput(attrs={'class': 'form-control flatpickr', 'type': 'date', 'col': '12'}))

    def del_field(self, field):
        del self.fields[field]


class RequisitosPagoPosgradoForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=FileInput({'style':'width:100%;', 'class':'form-control', 'col': '12', 'accept': 'application/pdf'}))
    fecha_caducidad = forms.DateField(label=u'Fecha caducidad', required=False, widget=forms.TextInput(attrs={'class': 'form-control flatpickr', 'type': 'date', 'col': '12'}))

    def del_field(self, field):
        del self.fields[field]

class ValidarRequisitoPersonalContratarForm(forms.Form):
    estado = forms.ChoiceField(choices=ESTADO_REVISION, label=u"Estado", widget=forms.Select(attrs={'class': 'select2 form-control', 'style': 'width:100%'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea( attrs={'rows': '4', 'class': 'form-control ckeditor', 'placeholder': 'Ingrese una breve observación...'}), required=False)


def del_field(self, field):
        del self.fields[field]

class RequisitoProcesoForm(forms.Form):
    nombre = forms.ModelChoiceField(label=u"Requisitos",
                                    queryset=Requisito.objects.filter(status=True).order_by('nombre'),
                                    required=True, widget=forms.Select(attrs={'formwidth': '50%'}))


class ProcesoForm(forms.Form):
    perfil = forms.ModelChoiceField(label=u"Perfil",
                                    queryset=PerfilPuestoDip.objects.filter(status=True).order_by('nombre'),
                                    required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    tipo = forms.ModelChoiceField(label=u"Proceso",
                                    queryset=TipoProceso.objects.filter(status=True).order_by('nombre'),
                                    required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    version = forms.IntegerField(label=u'Versión', required=False,
                                 widget=forms.TextInput(attrs={'class': 'imp-10', 'decimal': '0', 'formwidth': '50%'}))
    nombre = forms.CharField(label=u'Nombre', required=True,
                             widget=forms.Textarea({'rows': '1', 'formwidth': '100%', "tooltip": "Nombre"}))
    activo = forms.BooleanField(label=u"Desea mostrarlo?", required=False,
                                 widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))


class PasosProcesoForm(forms.Form):
    pasoanterior = forms.ModelChoiceField(label=u"Paso Anterior", queryset=PasosProceso.objects.filter(status=True).order_by('numeropaso'), required=False, widget=forms.Select(attrs={'formwidth': '40%'}))
    estadovalida = forms.ChoiceField(choices=ESTADOS_PROCESO, label=u'Estado de validación', required=False, widget=forms.Select(attrs={'formwidth': '30%'}))
    estadorechazado = forms.ChoiceField(choices=ESTADOS_PROCESO, label=u'Estado de rechazado', required=False, widget=forms.Select(attrs={'formwidth': '30%'}))
    tiporevisor = forms.ChoiceField(choices=TIPOREVISOR, label=u'Revisor', required=False, widget=forms.Select(attrs={'formwidth': '30%'}))
    valida = forms.ModelChoiceField(label=u"Validado Por", queryset=DenominacionPuesto.objects.filter(status=True).order_by('descripcion'), required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    carga = forms.ModelChoiceField(label=u"Cargado Por", queryset=DenominacionPuesto.objects.filter(status=True).order_by('descripcion'), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    numeropaso = forms.IntegerField(label=u'Nro. de paso', required=False, widget=forms.TextInput(attrs={'class': 'imp-10', 'formwidth': '40%', 'decimal': '0'}))
    tiempoalerta_carga = forms.IntegerField(label=u'Tiempo de Alerta Carga (Horas)', required=True,widget=forms.TextInput(attrs={'class': 'imp-10', 'formwidth': '30%', 'decimal': '0'}))
    tiempoalerta_validacion = forms.IntegerField(label=u'Tiempo de Alerta Validación (Horas)', required=True,widget=forms.TextInput(attrs={'class': 'imp-10', 'formwidth': '30%', 'decimal': '0'}))
    finaliza = forms.BooleanField(label=u"¿Último paso?", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    habilitacontrato = forms.BooleanField(label=u"¿Habilita contrato?", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    beneficiario = forms.BooleanField(label=u"¿Muestra a beneficiario?", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    genera_informe = forms.BooleanField(label=u"¿Genera Informe?", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    carga_archivo = forms.BooleanField(label=u"¿Carga Archivo?", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    valida_archivo = forms.BooleanField(label=u"¿Valida Archivo?", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    activo = forms.BooleanField(label=u"¿Activo?", required=False,widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))
    nombre = forms.CharField(label=u'Nombre', required=True,widget=forms.Textarea({'rows': '1', 'formwidth': '100%', "tooltip": "Nombre"}))
    leyenda = forms.CharField(label=u'Mensaje de Ayuda', widget=forms.Textarea(attrs={'rows': '1'}), required=False)


class MantenimientoNombreForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', required=True, widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "Nombre"}))


class DatosPersonalesForm(forms.Form):
    from sga.models import Sexo, PersonaEstadoCivil
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula', 'formwidth': '50%'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula', 'formwidth': '50%'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(), widget=forms.Select(attrs={'formwidth': '50%'}))
    estadocivil = forms.ModelChoiceField(label=u'Estado civil', queryset=PersonaEstadoCivil.objects, required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    nacimiento = forms.DateField(label=u"Fecha nacimiento", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75', 'formwidth': '50%'}))
    anioresidencia = forms.IntegerField(initial=0, label=u'Años de residencia', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    email = forms.CharField(label=u"Correo electrónico personal", max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    libretamilitar = forms.CharField(label=u"Libreta militar", max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    archivocedula = ExtFileField(label=u'Documento Cédula', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304)
    papeleta = ExtFileField(label=u'Documento Certificado Votación', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304)
    archivolibretamilitar = ExtFileField(label=u'Documento Libreta militar', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304)


    def editar(self, sinnombres=True):
        if sinnombres:
            deshabilitar_campo(self, 'nombres')
            deshabilitar_campo(self, 'apellido1')
            deshabilitar_campo(self, 'apellido2')
        deshabilitar_campo(self, 'cedula')


class CuentaBancariaPersonaForm(forms.Form):
    numero = forms.CharField(max_length=20, label=u'No. Cuenta', required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    banco = forms.ModelChoiceField(label=u"Banco", queryset=Banco.objects.all(), required=False, widget=forms.Select())
    tipocuentabanco = forms.ModelChoiceField(label=u"Tipo de cuenta", queryset=TipoCuentaBanco.objects.all(), required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)


class InscripcionConvocatoriaForm(forms.Form):
    estado = forms.ChoiceField(choices=ESTADO_REVISION, label=u"Estado", widget=forms.Select(attrs={'class':'select2 form-control', 'style':'width:100%'}))
    # mensajepredeterminado = forms.ModelChoiceField(label=u"Mensaje predeterminado", queryset=MensajePredeterminado.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    tipoPersonal = forms.ModelChoiceField(label=u" Tipo: ", queryset=TipoPersonal.objects.filter(status=True).order_by('id'), required=False, widget=forms.Select(attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))
    observacioncon = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '4', 'class':'form-control ckeditor', 'placeholder':'Ingrese una breve observación...'}), required=False)

    def estados_revision_inscrito(self):
        self.fields['tipoPersonal'].widget = forms.HiddenInput()
        estados_permitidos = [estado for estado in ESTADO_REVISION if estado[0] in (1,3, 11,12)]
        self.fields['estado'].choices = estados_permitidos

    def estados_revision_inscrito_por_comite(self):
        self.fields['tipoPersonal'].widget = forms.HiddenInput()
        estados_permitidos = [estado for estado in ESTADO_REVISION if estado[0] in (2, 3, 11)]
        self.fields['estado'].choices = estados_permitidos

    def add_class(self):
        self.fields['tipoPersonal'].widget = forms.Select( attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'})
        self.fields['tipoPersonal'].queryset =TipoPersonal.objects.filter(status=True).order_by('id')
        self.fields['estado'].widget.attrs['class'] = 'select2 form-control estado_comite_revision_seleccion estado_mensaje_predeterminado'

    def edit_personalcontratar(self,estado_id):
        self.fields['tipoPersonal'].initial = estado_id

    def por_analista(self):
        self.fields['tipoPersonal'].widget = forms.HiddenInput()
        self.fields['estado'].widget.attrs['class'] = 'select2 form-control estado_mensaje_predeterminado'

class PersonalApoyoMaestriaForm(forms.Form):
    personalapoyo = forms.ModelChoiceField(label=u"Personal de Apoyo", queryset=PersonalApoyo.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    fechainicio = forms.DateField(label=u'Fecha Inicio', required=False, widget=forms.TextInput(attrs={'class': 'form-control flatpickr', 'type':'date', 'col':'6'}))
    fechafin = forms.DateField(label=u'Fecha Fín', required=False, widget=forms.TextInput(attrs={'class': 'form-control flatpickr', 'type':'date', 'col':'6'}))
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.filter((Q(niveltitulacion_id=4) | Q(coordinacion__id=7)) & Q(status=True)), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    cohorte = forms.ModelMultipleChoiceField(label=u"Cohorte", queryset=Periodo.objects.filter(status=True), required=False, widget=forms.SelectMultiple(attrs={'col': '12', 'style': '100%'}))

    def edit(self, pk, idc=None):
        if idc:
            mallas = Malla.objects.values_list('id').filter(carrera_id=idc, vigente=True, status=True)
            periodos = Materia.objects.values_list('nivel__periodo_id', flat=True).filter(asignaturamalla__malla__in=mallas, asignaturamalla__malla__status=True, asignaturamalla__status=True,status=True)
            self.fields['cohorte'].queryset = Periodo.objects.filter(id__in=periodos, clasificacion=2)
        else:
            self.fields['cohorte'].queryset = Periodo.objects.filter(id__in=pk)

        self.fields['cohorte'].initial = pk


class PersonalApoyoForm(forms.Form):
    persona = forms.ModelChoiceField(label=u"Persona", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': '100%'}))

    def edit(self, pk):
        self.fields['persona'].queryset = Persona.objects.filter(id=pk)
        self.fields['persona'].initial = [pk]


class RolPersonalApoyoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'12'}))


class ClasificacionDocumentoInvitacionForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '8'}))
    abreviatura = forms.CharField(label=u'Abreviatura: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '4'}))

class DocumentoInvitacionForm(forms.Form):
    codigo = forms.CharField(label=u'Código', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    secuenciadocumento = forms.ModelChoiceField(label=u"Secuencia", queryset=SecuenciaDocumentoInvitacion.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    #estado = forms.ChoiceField(choices=ESTADO_REVISION, label=u"Estado", widget=forms.Select(attrs={'class': 'select2 form-control', 'style': 'width:100%'}))
    clasificacion = forms.ModelChoiceField(label=u"Clasificación",queryset=ClasificacionDocumentoInvitacion.objects.filter(status=True),required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    #archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=FileInput({'style': 'width:100%;', 'class': 'form-control', 'col': '12', 'accept': 'application/pdf'}))

class SecuenciaDocumentoInvitacionForm(forms.Form):
    from sagest.models import AnioEjercicio
    anioejercicio = forms.ModelChoiceField(label=u"Año de Ejercicio", queryset=AnioEjercicio.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class':'validate[required]'}))
    secuencia = forms.CharField(label=u'Código', required=True, widget=forms.TextInput(attrs={'class': 'form-control validate[required]', 'col': '12'}))
    tipo = forms.ModelChoiceField(label=u"Típo de documento", queryset=ClasificacionDocumentoInvitacion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))


class FirmasDocumentoInvitacionForm(forms.Form):
    persona = forms.ModelChoiceField(label=u" Persona Responsable: ", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    documentoinvitacion = forms.ModelChoiceField(label=u" Documento: ", queryset=ClasificacionDocumentoInvitacion.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    cargo = forms.ModelChoiceField(label=u" Cargo: ", queryset=PerfilPuestoDip.objects.filter(status=True).order_by('-id'),required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    firma = ExtFileField(label=u'Seleccione Archivo: ', required=False, help_text=u'Tamaño Maximo permitido 6Mb, en formato de imagen.', ext_whitelist=(".jpg",".png", ".jpeg"), max_upload_size=6291456, widget=FileInput({'style': 'width:100%;', 'class': 'form-control', 'col': '12', 'accept': '.jpg, .png, .jpeg'}))
    responsabilidad = forms.CharField(label=u'Responsabilidad', required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12', 'placeholder':'P. Ej. Validado por'}))

    def edit(self, pk):
        persona = Persona.objects.filter(pk=pk)
        self.fields['persona'].queryset = persona
        self.fields['persona'].initial = persona.first()


class ComiteAcademicoPosgradoForm(forms.ModelForm):
    class Meta:
        model = ComiteAcademicoPosgrado
        fields = ('nombre', 'abreviatura', 'tipodocente', 'apuntador')
        widgets = {
            'abreviatura': forms.TextInput(attrs={'class': 'form-control', 'col': '2'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'col': '10'}),
            'tipodocente': forms.Select(attrs={'class': 'form-control', 'col': '12'}),
            'apuntador': forms.Select(attrs={'class': 'form-control', 'col': '12'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['apuntador'].queryset = Administrativo.objects.filter(activo=True, status=True)
        self.fields['tipodocente'].label = u"Tipo de comité"
        self.fields['tipodocente'].queryset = PerfilPuestoDip.objects.filter(status=True)



class IntegranteComiteAcademicoPosgradoForm(forms.Form):
    persona = forms.ModelChoiceField(label=u" Persona: ", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    cargo = forms.ModelChoiceField(label=u" Cargo: ", queryset=PerfilPuestoDip.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select(attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))
    tipo_cargo = forms.ChoiceField(choices = TIPO_CARGO_CHOICE ,label=u" Tipo cargo: ", required=False, widget=forms.Select(attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))
    tipo = forms.ModelChoiceField(label=u" Tipo de integrante: ", queryset=TipoPersonal.objects.filter(status=True).order_by('id'), required=False, widget=forms.Select(attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))

    def edit(self, pk):
        persona = Persona.objects.filter(pk=pk)
        self.fields['persona'].queryset = persona
        self.fields['persona'].initial = persona.first()


class ActaSeleccionDocenteForm(forms.Form):
    tipo_formato_acta = forms.ChoiceField(choices = TIPO_FORMATO_ACTA ,label=u" Tipo formato acta: ", required=True, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    comite = forms.ModelChoiceField(label=u'Comité académico', queryset=ComiteAcademicoPosgrado.objects.filter(status=True),  widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth':'100%'}))
    lugar = forms.CharField(label=u'Lugar', widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12', 'controlwidth': '100%', 'placeholder':'Ingrese la dirección de donde se emite el acta...'}))
    #paralelos = forms.IntegerField(label=u'Cantidad de paralelos', widget=forms.NumberInput(attrs={'col': '12', 'class': 'form-control', 'controlwidth': '100%', 'placeholder': 'Ingrese el número de paralelos...'}))
    observacion_ep = forms.CharField(label=u"Evaluación de perfil (observación):", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 2}))

    def read_only(self):
        deshabilitar_campo(self, 'comite')
        deshabilitar_campo(self, 'lugar')


class PlanAccionForm(forms.Form):
    integrantecomiteacademico = forms.ModelChoiceField(label=u'Dirigido a:', queryset=IntegranteComiteAcademicoPosgrado.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    resolucion = forms.CharField(label=u"Acción", widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 2}))

    def _init(self, pk):
        self.fields['integrantecomiteacademico'].queryset = IntegranteComiteAcademicoPosgrado.objects.filter(comite_id=pk, status=True)


class HorarioClasesForm(forms.Form):
    dia = forms.ChoiceField(choices=DIAS_CHOICES, label=u"Día:", widget=forms.Select(attrs={'class':'select2 form-control', 'style':'width:100%', 'col': '12'}))
    inicio = forms.DateField(label=u'Fecha inicio:', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    fin = forms.DateField(label=u'Fecha fín:', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    turno = forms.ModelMultipleChoiceField(required=True, queryset=Turno.objects.filter(status=True, sesion_id=19), label=u'Turno:', widget=forms.SelectMultiple(attrs={'class':'form-control', 'col':'12', 'style':'width:100%'}))


class TipoPersonalForm(forms.ModelForm):
    class Meta:
        model = TipoPersonal
        fields = ('descripcion',)
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'col': '12'}),
        }


def fecha_minima_inicio_modulo():
    plazo = variable_valor('PLAZO_GENERAR_ACTA_SELECCION') if variable_valor('PLAZO_GENERAR_ACTA_SELECCION') else 10
    t = datetime.now().date() + timedelta(plazo)
    return t


class ActaParaleloForm(forms.Form):
    convocatoria = forms.ModelChoiceField(label=u'Asignatura:', queryset=Convocatoria.objects.filter(inscripcionconvocatoria__status=True, status=True).distinct(), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required] load_inicio_fin_convocatoria', 'controlwidth':'100%'}))
    paralelo = forms.ModelChoiceField(label=u'Paralelo:', queryset=Paralelo.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth':'100%'}))
    inicio = forms.DateField(label=u'Fecha inicio:', initial=fecha_minima_inicio_modulo(), help_text=u"La fecha de inicio del módulo no puede ser menor a la fecha %s" % fecha_minima_inicio_modulo().strftime("%d/%m/%Y"), required=False, input_formats=['%Y-%m-%d'], widget=DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    fin = forms.DateField(label=u'Fecha fín:', required=False, input_formats=['%Y-%m-%d'], widget=DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inicio'].help_text = u"La fecha de inicio del módulo no puede ser menor a la fecha %s" % fecha_minima_inicio_modulo().strftime("%d/%m/%Y")
        self.fields['inicio'].initial = fecha_minima_inicio_modulo()

    def clean(self):
        cleaned_data = super().clean()
        inicio_value = self.cleaned_data.get('inicio')
        fin_value = self.cleaned_data.get('fin')
        nDias = variable_valor('PLAZO_GENERAR_ACTA_SELECCION') if variable_valor('PLAZO_GENERAR_ACTA_SELECCION') else 10
        plazo = datetime.now().date() + timedelta(nDias)
        if inicio_value < plazo: self.add_error('inicio', f"La fecha de inicio del módulo no puede ser menor a la fecha %s" % plazo.strftime("%d/%m/%Y"))
        if inicio_value > fin_value: self.add_error("inicio", f"La fecha de inicio no puede ser mayor a la fecha de finalizacón.")
        if fin_value < inicio_value: self.add_error("fin", f"La fecha de finalización no puede ser menor a la fecha de inicio.")

    def del_field(self, field):
        del self.fields[field]

    def set_required_field(self, field,required):
        self.fields[field].required = required

class PersonalAContratarForm(forms.ModelForm):
    class Meta:
        model = PersonalAContratar
        fields = ('inscripcion', 'tipo', 'observacion')
        widgets = {
            'inscripcion': forms.Select(attrs={'class': 'form-control', 'col': '12', 'style':'width:100%;'}),
            'tipo': forms.Select(attrs={'class': 'form-control', 'col': '12', 'style':'width:100%;'}),
            'observacion': forms.Textarea(attrs={'class': 'form-control', 'col': '12', 'style':'width:100%;', 'row': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].queryset = TipoPersonal.objects.filter(status=True)

    def _init(self, **kwargs):
        self.fields['inscripcion'].queryset = InscripcionConvocatoria.objects.filter(estado=2, convocatoria=kwargs.pop('convocatoria'), status=True)

    def cargar_banco_elegible_editar(self, **kwargs):
        query =  InscripcionConvocatoria.objects.filter(estado=2, convocatoria=kwargs.pop('convocatoria'), status=True)
        query2 = InscripcionConvocatoria.objects.filter(pk=kwargs.pop('pk'), status=True)
        self.fields['inscripcion'].queryset =query|query2

    def cargar_banco_de_elegibles(self, **kwargs):
        self.fields['inscripcion'].queryset = InscripcionConvocatoria.objects.filter(estado=11, convocatoria__carrera_id=kwargs.get('carrera_id', 0), convocatoria__asignaturamalla__asignatura_id=kwargs.get('asignatura_id', 0), status=True)
        self.fields['inscripcion'].label = "Banco de elegibles"

    def cargar_inscrito_seleccionado(self, **kwargs):
        self.fields['inscripcion'].queryset = eInscripcionConvocatoria = InscripcionConvocatoria.objects.filter(pk=int(kwargs.get('pk', 0)))
        self.fields['inscripcion'].initial = eInscripcionConvocatoria.first().pk

    def del_field(self,field):
        del self.fields[field]


class FirmaElectronicaIndividualForm(forms.Form):
    firma = ExtFileField(label=u'Firma electrónica: ', help_text=u'Solo archivos con formato .p12', ext_whitelist=(".p12",), max_upload_size=6291456, widget=FileInput({'style': 'width:100%;', 'class': 'form-control', 'col': '12', 'accept': '.p12'}))
    password = forms.CharField(label=u'Contraseña', widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12', 'controlwidth': '100%', 'placeholder': 'Contraseña', 'type':'password'}))


class CerrarActaForm(forms.Form):
    estado = forms.ChoiceField(choices=((1, 'APROBADO'), (2, 'CORREGIR')), label=u"Día:", widget=forms.Select(attrs={'class': 'select2 form-control', 'style': 'width:100%', 'col': '12'}))
    fecharequisitos = forms.DateField(label=u'Fecha máxima para carga de requisitos', required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '12'}))

    def del_field(self, field):
        del self.fields[field]


class ConfiguracionPlazosActaSeleccion(forms.Form):
    valor = forms.CharField(label=u'Valor', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col':'12', 'type':'number'}))

class ConfiguracionGeneralActaSeleccionDocenteForm(forms.Form):
    convocado_por = forms.ModelChoiceField(label=u" Convocado por: ", queryset=Administrativo.objects.filter(status=True), required=False, widget=forms.Select( attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))
    cargo_convocado_por = forms.ModelChoiceField(label=u" Cargo convocado por: ", queryset=PerfilPuestoDip.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select( attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))
    tipo_cargo_convocado_por = forms.ChoiceField(choices=TIPO_CARGO_CHOICE, label=u" Tipo cargo: ", required=False,  widget=forms.Select(attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))
    organizado_por = forms.ModelChoiceField(label=u" organizado por: ", queryset=Administrativo.objects.filter(status=True), required=False,widget=forms.Select( attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))
    cargo_organizado_por = forms.ModelChoiceField(label=u" Cargo organizado por: ", queryset=PerfilPuestoDip.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select( attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))
    tipo_cargo_organizado_por = forms.ChoiceField(choices=TIPO_CARGO_CHOICE, label=u" Tipo cargo: ", required=False,  widget=forms.Select(attrs={'col': '4', 'style': 'width:100%', 'class': 'validate[required]'}))

class ConfiguracionInformeForm(forms.Form):
    para = forms.ModelChoiceField(label=u" Para: ", queryset=Administrativo.objects.filter(status=True),required=False, widget=forms.Select( attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    de = forms.ModelChoiceField(label=u" De: ", queryset=Administrativo.objects.filter(status=True), required=False, widget=forms.Select( attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    antecedentes = forms.CharField(label=u"Antecedentes", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))
    motivacionjuridica = forms.CharField(label=u"Motivación juridica", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))
    recomendaciones = forms.CharField(label=u"Recomendaciones", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

class PlanificacionMateriaForm(forms.Form):
    from .models import ESTADO_ADMINISTRATIVO_MATERIA,DENOMINACION,TIPO
    estado = forms.ChoiceField(choices=ESTADO_ADMINISTRATIVO_MATERIA, label=u"Estado: ", widget=forms.Select(attrs={'class': 'select2 form-control', 'style': 'width:100%', 'col': '12'}))
    tipodocente = forms.ModelChoiceField(label=u'Tipo de docente:', queryset=TipoDocente.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))
    denominacion = forms.ChoiceField(choices=DENOMINACION, label=u"Denominación: ", widget=forms.Select(attrs={'class': 'select2 form-control', 'style': 'width:100%', 'col': '12'}))
    tipo = forms.ChoiceField(choices=TIPO, label=u"Tipo: ", widget=forms.Select(attrs={'class': 'select2 form-control', 'style': 'width:100%', 'col': '12'}))
    pagado = forms.BooleanField(label=u"Pagado", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    fecha = forms.DateField(label=u'Fecha contrato', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    fechapago = forms.DateField(label=u'Fecha reporte pago', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    observacion = forms.CharField(label=u'Observación:', initial = 'CONVENIO CON EPUNEMI', widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}),  required=False)
    # profesormateria = forms.ModelChoiceField(label=u'Tipo de docente:', queryset=ProfesorMateria.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))


class DuplicarHorarioForm(forms.Form):
    paralelo = forms.ModelChoiceField(label=u'Paralelo', required=True , queryset=ActaParalelo.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth':'100%'}))

    def buscar_paralelo(self,queryset):
        self.fields['paralelo'].queryset = queryset



class PlanificacionMateriaPosgradoForm(forms.Form):
    paralelos = forms.CharField(label=u"Paralelos: ", initial=1, widget=forms.TextInput(attrs={'class': 'imp-100', 'col':'6', 'type':'number', 'min':'0', 'controlwidth':'100%', 'formwidth': '50%'}))
    fechalimiteplanificacion = forms.DateField(label=u"F. limite planificación", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control','col': '6'}), required=True)

class AdministrativoActaSeleccionDocenteForm(forms.Form):
    administrativo = forms.ModelChoiceField(label=u" Administrativo: ", queryset=Administrativo.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))

    def edit(self, pk):
        administrativo = Administrativo.objects.filter(pk=pk)
        self.fields['administrativo'].queryset = administrativo
        self.fields['administrativo'].initial = administrativo.first()


class PlanificacionMateriaSolicitudForm(forms.Form):
    profesor = forms.BooleanField(label=u"¿Requiere profesor?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    autor = forms.BooleanField(label=u"¿Requiere profesor autor?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    invitado = forms.BooleanField(label=u"invitado", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    inicio_profesor = forms.DateField(label=u'Fecha inicio profesor', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    inicio_autor = forms.DateField(label=u'Fecha inicio autor', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    fin_profesor = forms.DateField(label=u'Fecha fin profesor', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    fin_autor = forms.DateField(label=u'Fecha fin autor', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    observacionsolicitud = forms.CharField(label=u'Observación:', initial='', widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    lanzar_convocatoria = forms.BooleanField(label=u"¿Lanzar convocatoria?", required=False,  widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    inicio_invitado = forms.DateField(label=u'Fecha inicio autor', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    fin_invitado = forms.DateField(label=u'Fecha fin profesor', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))


class OrdenFirmaActaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6'}))
    orden = forms.CharField(label=u'Orden: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6'}))
    funcion = forms.CharField(label=u'Funcion: ', required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'col': '12'}))


class InformeContratacionIntegrantesFirmaForm(forms.Form):
    responsabilidadfirma = forms.ModelChoiceField(label=u'Responsabilidad:', queryset=OrdenFirmaInformeContratacion.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))
    persona = forms.ModelChoiceField(label=u'Persona:', queryset=Persona.objects.none(), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))

    def edit(self, pk):
        persona = Persona.objects.filter(pk=pk)
        self.fields['persona'].queryset = persona
        self.fields['persona'].initial = persona.first()

class OrdenFirmaInformeContratacionForm(forms.Form):
    responsabilidadfirma = forms.ModelChoiceField(label=u'Responsabilidad:', queryset=ResponsabilidadFirma.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))
    orden = forms.CharField(label=u'Orden: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6'}))


class MensajePredeterminadoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))


class VotacionComiteForm(forms.Form):
    inscrito = forms.ModelChoiceField(label=u" Inscrito: ", queryset=InscripcionConvocatoria.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))
    tipoPersonal = forms.ModelChoiceField(label=u" Tipo: ", queryset=TipoPersonal.objects.filter(status=True).order_by('id'), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]'}))

    def load_inscrito(self,eInscripcionConvocatoria):
        self.fields['inscrito'].queryset = InscripcionConvocatoria.objects.filter(pk=eInscripcionConvocatoria.pk)
        self.fields['inscrito'].initial = eInscripcionConvocatoria.pk



class ResponsabilidadFirmaForm(forms.Form):
    responsabilidad = forms.CharField(label=u'Descripción: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))


class ConvocatoriaMasivaForm(forms.Form):
    hoy = datetime.now().date()
    fechainicio = forms.DateField(label=u'Fecha inicio', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))
    fechafin = forms.DateField(label=u'Fecha fin', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '6'}))


class CertificacionPresupuestariaInformeContratacionForm(forms.Form):
    certificacionpresupuestaria = forms.ModelChoiceField(label=u'Certificación:', queryset=CertificacionPresupuestariaDip.objects.filter(status=True), widget=forms.Select(attrs={'col': '12', 'style': 'width:100%', 'class': 'validate[required]', 'controlwidth': '100%'}))


class PrerevisionActaParaleloPosgradoForm(forms.Form):
    estado = forms.ChoiceField(choices=ESTADO_REVISION_PARALELO, label=u"Estado: ", widget=forms.Select(attrs={'class': 'select2 form-control', 'style': 'width:100%', 'col': '12'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea( attrs={'rows': '4', 'class': 'form-control ckeditor', 'placeholder': 'Ingrese una breve observación...'}), required=False)


class ConfiguracionConclusionesInformeContratacionForm(forms.Form):
    conclusiones = forms.CharField(label=u"conclusiones", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["conclusiones"].initial = objeto


class ConfiguracionRecomendacionesInformeContratacionForm(forms.Form):
    recomendaciones = forms.CharField(label=u"recomendaciones", required=False, widget=forms.Textarea(attrs={'class': 'form-control ckeditor', 'col': '12', 'row': 5}))

    def initial(self,objeto):
        self.fields["recomendaciones"].initial = objeto


class RubricaSeleccionDocenteForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    activo = forms.BooleanField(label=u"Estado (Activo o Inactivo)", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))

class DetalleItemRubricaSeleccionDocenteForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    orden = forms.IntegerField(label=u'Orden', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))

class DetalleSubItemRubricaSeleccionDocenteForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción: ', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    orden = forms.IntegerField(label=u'Orden', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    puntaje = forms.IntegerField(label=u"Puntaje", initial=0, widget=forms.TextInput(attrs={'class': 'imp-number', 'col': '6'}))


class LinkVideoForm(forms.Form):
    link = forms.CharField(label=u'Link', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))

class DatoPersonalExtraForm(forms.Form):
    link = forms.CharField(label=u'Link', max_length=300, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    archivo = ExtFileField(label=u'Hoja de vida', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf", ".PDF"), max_upload_size=4194304)

    def del_archivo(self):
        del self.fields['archivo']
