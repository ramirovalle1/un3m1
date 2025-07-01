# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta

from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput, TimeInput

from core.custom_forms import FormModeloBase
from investigacion.models import *
from sagest.models import Departamento, Ubicacion
from sga.forms import ExtFileField, deshabilitar_campo
from sga.models import Canton, Provincia, TIPO_PERSONA, Parroquia, Pais, Sexo, ProgramasInvestigacion, Coordinacion, TIPO_PROYECTO_ARTICULO, ProyectosInvestigacion, Modalidad, Titulo, RevistaInvestigacion, Persona, Bloque, ESTADO_PUBLICACION_ARTICULO


#-----------------------INVESTIGACION--------------------------

class CausaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción de la causa', widget=forms.Textarea(attrs={'rows': '9'}),
                                  required=True)


class RolesForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripcion', required=False)
    unico = forms.BooleanField(initial=False, required=False, label=u'Único?',
                                 widget=CheckboxInput(attrs={'formwidth': '25%'}))


class EfectoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción del Efecto', widget=forms.Textarea(attrs={'rows': '9'}),
                                  required=True)


class ImpactoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripcion', required=False)
    rangoinicio = forms.IntegerField(label=u"% Desde", initial=0,
                                    widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))
    rangofin = forms.IntegerField(label=u"% Hasta", initial=0,
                                    widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))


class CabAreasForm(forms.Form):
    nombre =  forms.CharField(label=u'Nombre', required=False)
    descripcion = forms.CharField(label=u'Descripción del Área', widget=forms.Textarea(attrs={'rows': '3'}),
                                  required=True)
    impacto = forms.ModelChoiceField(label=u"Impacto", queryset=InvImpacto.objects.filter(status=True), required=False)
    numinforme = forms.CharField(label=u"Número de Informe:", max_length=40, required=False, widget=forms.TextInput(attrs={'class': 'imp-25', 'formwidth': '100%'}),
                                  )
    archivoinformepdf = ExtFileField(label=u'Archivo Informe:', widget=FileInput(attrs={'formwidth': '100%'}),
                                     required=False,
                                     help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                     ext_whitelist=(".pdf"),
                                     max_upload_size=4194304)


class DetAreasCausasForm(forms.Form):
    causas = forms.IntegerField(initial=0, required=False, label=u'Causas',
                                widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '80%'}))

    def editar(self, area):
        self.fields['causas'].widget.attrs['descripcion'] = area.causas.descripcion if area.causas else ""
        self.fields['causas'].widget.attrs['value'] = area.causas.id if area.causas else ""


class ComisionAreaForm(forms.Form):
    persona = forms.IntegerField(initial=0, required=False, label=u'Persona',
                                 widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '80%'}))
    rol = forms.ModelChoiceField(label=u"Rol", queryset=InvRoles.objects.filter(status=True), required=True)

    def editar(self, area):
        self.fields['persona'].widget.attrs['descripcion'] = area.persona.flexbox_repr if area.persona else ""
        self.fields['persona'].widget.attrs['value'] = area.persona.id if area.persona else ""
        deshabilitar_campo(self, 'persona')


class CabComisionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre de la Comisión', widget=forms.Textarea(attrs={'rows': '3'}),
                                  required=True)


class ComisionObservacionForm(forms.Form):
    descripcion = forms.CharField(label=u'Observación de la Comisión', widget=forms.Textarea(attrs={'rows': '3'}),
                                  required=True)


class EstadoObservacionForm(forms.Form):
    estado = forms.ChoiceField(choices=ESTADOS_AREA, label=u'Estado', required=False, widget=forms.Select(attrs={'formwidth': '40%'}))
    descripcion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '6','value':'ninguna'}),
                                  required=True)
    archivoaprobado = ExtFileField(label=u'Archivo Aprobación:', widget=FileInput(attrs={'formwidth': '100%'}),
                                        required=False,
                                        help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                        ext_whitelist=(".pdf"),
                                        max_upload_size=4194304)


class EstadoObservacionAreasForm(forms.Form):
    estado = forms.ChoiceField(choices=ESTADOS_AREA, label=u'Estado', required=False, widget=forms.Select(attrs={'formwidth': '40%'}))
    descripcion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '6','value':'ninguna'}),
                                  required=True)
    numinforme = forms.CharField(label=u"Número de Informe:", max_length=40, required=False, widget=forms.TextInput(attrs={'class': 'imp-25', 'formwidth': '100%'}),)
    archivoaprobado = ExtFileField(label=u'Archivo Aprobación:', widget=FileInput(attrs={'formwidth': '100%'}),
                                        required=False,
                                        help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                        ext_whitelist=(".pdf"),
                                        max_upload_size=4194304)

class EstadoObservacionAreasComisionForm(forms.Form):
    numinforme = forms.CharField(label=u"Número de Resolución Ocas:", max_length=40, required=False, widget=forms.TextInput(attrs={'class': 'imp-25', 'formwidth': '100%'}),)
    archivoaprobado = ExtFileField(label=u'Archivo Resolución Ocas:', widget=FileInput(attrs={'formwidth': '100%'}),
                                        required=False,
                                        help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                        ext_whitelist=(".pdf"),
                                        max_upload_size=4194304)

class hojadevida(forms.Form):
    hojadevida = ExtFileField(label=u'Hoja de Vida:', widget=FileInput(attrs={'formwidth': '100%'}),
                                        required=False,
                                        help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                        ext_whitelist=(".pdf"),
                                        max_upload_size=4194304)


class PersonalExternoInvForm(forms.Form):
    from sga.models import Sexo
    institucionlabora = forms.CharField(label=u"Institucion donde labora", max_length=100, required=False,
                              widget=forms.TextInput(attrs={'class': 'imp-50'}))
    tipopersona = forms.ChoiceField(choices=TIPO_PERSONA, label=u'Tipo Persona', required=False, widget=forms.Select(attrs={'formwidth': '40%'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u"Nombres", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(), widget=forms.Select(attrs={'formwidth': '40%'}))
    ruc = forms.CharField(label=u"RUC", max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'imp-ruc'}))
    nombreempresa = forms.CharField(label=u"Nombre Empresa", required=False, max_length=100, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    nombrecomercial = forms.CharField(label=u"Nombre Comercial", required=False, max_length=200, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    contribuyenteespecial = forms.BooleanField(initial=False, label=u"Es Contrib. Espec.", required=False)
    nacimiento = forms.DateField(label=u"Fecha Nacimiento o Constitución", initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}), required=False)
    pais = forms.ModelChoiceField(label=u"País residencia", queryset=Pais.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '75%'}))
    provincia = forms.ModelChoiceField(label=u"Provincia residencia", queryset=Provincia.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '75%'}))
    canton = forms.ModelChoiceField(label=u"Canton residencia", queryset=Canton.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '75%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia residencia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': '75%'}))
    sector = forms.CharField(label=u"Sector", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    direccion = forms.CharField(label=u"Calle Principal", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    direccion2 = forms.CharField(label=u"Calle Secundaria", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    num_direccion = forms.CharField(label=u"Numero Domicilio", max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    telefono = forms.CharField(label=u"Telefono Movil", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    telefono_conv = forms.CharField(label=u"Telefono Fijo", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    email = forms.CharField(label=u"Correo Electronico", max_length=240, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    nombrecontacto = forms.CharField(label=u"Nombre Representante", required=False, max_length=200, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefonocontacto = forms.CharField(label=u"Telefono Representante", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    hojadevida = ExtFileField(label=u'Hoja de Vida:', widget=FileInput(attrs={'formwidth': '100%'}),
                                     required=False,
                                     help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                     ext_whitelist=(".pdf"),
                                     max_upload_size=4194304)
    def adicionar(self):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)

    def editar(self, persona):
        deshabilitar_campo(self, 'tipopersona')
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)


class AreaUnescoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.Textarea(attrs={'rows': '4'}), required=True)


class ConvocatoriaProyectoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=150, required=False, widget=forms.TextInput(attrs={'formwidth': '100%', 'autocomplete': 'off'}))
    apertura = forms.DateField(label=u"Apertura", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    cierre = forms.DateField(label=u"Cierre", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    minimoaprobacion = forms.IntegerField(label=u'Puntaje mínimo aprobación', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%', 'autocomplete': 'off', 'help_text2': 'Entre 0 y 100'}))
    periodocidad = forms.ModelChoiceField(label=u"Periodocidad para informes", queryset=Periodocidad.objects.filter(status=True, vigente=True).order_by('descripcion'), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    archivoresolucion = ExtFileField(label=u'Resolución OCS', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '50%'}))
    # archivoformatopresupuesto = ExtFileField(label=u'Formato Presupuesto Final', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato xls', ext_whitelist=(".xls", ".xlsx",), max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '50%'}))
    archivoconvocatoria = ExtFileField(label=u'Bases Convocatoria', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato xls', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '50%'}))
    inicioevalint = forms.DateField(label=u"Inicio", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Evaluación Interna de propuestas de proyectos'}), required=False)
    finevalint = forms.DateField(label=u"Fin", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    inicioreevalint = forms.DateField(label=u"Inicio", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Reevaluación Interna de propuestas de proyectos'}), required=False)
    finreevalint = forms.DateField(label=u"Fin", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    inicioevalext = forms.DateField(label=u"Inicio", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Evaluación Externa de propuestas de proyectos'}), required=False)
    finevalext = forms.DateField(label=u"Fin", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    inicioreevalext = forms.DateField(label=u"Inicio", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Reevaluación Externa de propuestas de proyectos'}), required=False)
    finreevalext = forms.DateField(label=u"Fin", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    inicioselapro = forms.DateField(label=u"Inicio", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Proceso de Selección y Aprobación'}), required=False)
    finselapro = forms.DateField(label=u"Fin", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    minintegranteu = forms.IntegerField(label=u'Mínimo integrantes', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%', 'autocomplete': 'off', 'separator2': True, 'separatortitle': 'Cantidad de Integrantes UNEMI para un proyecto'}))
    maxintegranteu = forms.IntegerField(label=u'Máximo integrantes', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%', 'autocomplete': 'off'}))
    minintegrantee = forms.IntegerField(label=u'Mínimo integrantes', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%', 'autocomplete': 'off', 'separator2': True, 'separatortitle': 'Cantidad de Integrantes EXTERNOS para un proyecto'}))
    maxintegrantee = forms.IntegerField(label=u'Máximo integrantes', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'formwidth': '50%', 'autocomplete': 'off'}))


class RubricaEvaluacionForm(forms.Form):
    categoria = forms.CharField(label=u'Categoría', max_length=150, required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'autocomplete': 'off', 'separator2': True, 'separatortitle': 'Datos de la Rúbrica'}))
    numero = forms.IntegerField(label=u"Número", required=False, widget=forms.TextInput(attrs={'decimal': '0', 'formwidth': '50%', 'autocomplete': 'off'}))
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea(attrs={'rows': '3'}))
    valoracion = forms.IntegerField(label=u'Valoración', required=False, widget=forms.TextInput(attrs={'decimal': '0', 'formwidth': '50%', 'autocomplete': 'off', 'help_text2': 'Entre 0 y 100'}))


class RegistroPropuestaProyectoInvestigacionForm(FormModeloBase):
    categoria = forms.ModelChoiceField(label=u"Tipo", queryset=Categoria.objects.filter(status=True, vigente=True, tipo=1).order_by('numero'), required=False, widget=forms.Select(attrs={'col': '12', 'separator2': True, 'separatortitle': 'Datos Generales'}))
    titulo = forms.CharField(label=u'Título', required=False, widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}))
    convocatoria = forms.CharField(label=u'Convocatoria', max_length=100, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento", queryset=SubAreaConocimientoTitulacion.objects.all(), required=False, widget=forms.Select(attrs={'col': '12'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento", queryset=SubAreaEspecificaConocimientoTitulacion.objects.all(), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    sublineainvestigacion = forms.ModelMultipleChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    programainvestigacion = forms.ModelChoiceField(label=u"Programa", queryset=ProgramasInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    industriapriorizada = forms.ModelChoiceField(label=u"Área prioritaria", queryset=IndustriaPriorizada.objects.filter(status=True, vigente=True).order_by('orden'), required=False, widget=forms.Select(attrs={'col': '12'}))
    requiereconvenio = forms.BooleanField(label=u"¿Requiere convenio?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'col': '12'}))
    especificaconvenio = forms.CharField(label=u'Especifique convenio', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))
    requierepermiso = forms.BooleanField(label=u"¿Necesita permiso del CEISH?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'col': '12'}))
    especificapermiso = forms.CharField(label=u'Especifique permisos', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))
    tiempomes = forms.IntegerField(label=u"Duración(Meses)", required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    # compraequipo = forms.ChoiceField(label=u"Contempla compra equipamiento", required=False, choices=TIPO_EQUIPAMIENTO, widget=forms.Select(attrs={'formwidth': '60%'}))


    # compraequipo = forms.ChoiceField(label=u"Tipo de financiamiento", required=False, choices=MONTO_PROYECTO, widget=forms.Select(attrs={'col': '6'}))
    porcentajeequipo = forms.CharField(label=u'% compra equipo', required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))

    montounemi = forms.FloatField(label=u'Monto UNEMI $', initial="0.00", required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'help_text2': 'Ej: 1234.56'}))
    montomaximounemi = forms.FloatField(label=u'Máximo a Financiar por la UNEMI $', initial="0.00", required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    montootrafuente = forms.FloatField(label=u'Monto otra fuente $', initial="0.00", required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'help_text2': 'Ej: 1234.56', 'fieldbuttons': [{'id': 'infootrafuente', 'tooltiptext': 'Financiamiento Externo', 'btnclasscolor': 'btn-info', 'btnfaicon': 'fa fa-question-circle'}]}))
    montototal = forms.FloatField(label=u'Monto Total $', initial="0.00", required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    tipocobertura = forms.ChoiceField(label=u"Tipo Cobertura", required=False, choices=TIPO_COBERTURA_EJECUCION, widget=forms.Select(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Localización Geográfica del proyecto'}))
    zonas = forms.ModelMultipleChoiceField(label=u'Zonas Planificación(Una o varias)', queryset=ZonaPlanificacion.objects.filter(status=True).order_by('numero'), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    provincias = forms.ModelMultipleChoiceField(label=u'Provincias(Una o varias)', queryset=Provincia.objects.filter(status=True, pais_id=1).order_by('nombre'), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    provincia = forms.ModelChoiceField(label=u'Provincia', queryset=Provincia.objects.filter(status=True, pais=1).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    canton = forms.ModelMultipleChoiceField(label=u'Cantones(Uno o varios)', queryset=Canton.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    requiereparroquia = forms.BooleanField(label=u"¿Ingresar parroquia?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'col': '6'}))
    parroquia = forms.CharField(label=u'Parroquia', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    nombreinsejec = forms.CharField(label=u'Institución', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Institución Participante Ejecutora'}))
    grupoinvestigacion = forms.ModelChoiceField(label=u"Grupo de investigación", queryset=GrupoInvestigacion.objects.filter(status=True, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    representanteinsejec = forms.CharField(label=u'Representante Legal', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    cedulainsejec = forms.CharField(label=u"Identificación", max_length=10, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    emailinsejec = forms.CharField(label=u'e-mail', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    telefonoinsejec = forms.CharField(label=u"Teléfonos", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    faxinsejec = forms.CharField(label=u"Fax", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    direccioninsejec = forms.CharField(label=u'Dirección', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    paginawebinsejec = forms.CharField(label=u'Página web', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    existeinscoejecutora = forms.ChoiceField(label=u"¿Existe institución co-ejecutora?", required=False, choices=VALOR_SI_NO, widget=forms.Select(attrs={'col': '6'}))

    def editar(self, proyecto):
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=proyecto.areaconocimiento, status=True, vigente=True).order_by('nombre')
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=proyecto.subareaconocimiento, status=True, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=proyecto.lineainvestigacion, status=True).order_by('nombre')
        self.fields['programainvestigacion'].queryset = ProgramasInvestigacion.objects.filter(status=True, convocatoriaprogramainvestigacion__convocatoria=proyecto.convocatoria, convocatoriaprogramainvestigacion__status=True).order_by('nombre')
        if proyecto.tipocobertura == 5:
            self.fields['canton'].queryset = Canton.objects.filter(provincia=proyecto.provincia).order_by('nombre')

    def cargarprogramas(self, convocatoria):
        self.fields['programainvestigacion'].queryset = ProgramasInvestigacion.objects.filter(status=True, convocatoriaprogramainvestigacion__convocatoria=convocatoria, convocatoriaprogramainvestigacion__status=True).order_by('nombre')


class ContenidoProyectoInvestigacionForm(FormModeloBase):
    titulo = forms.CharField(label=u'Título del Proyecto', required=False, widget=forms.Textarea(attrs={'col': '12', 'rows': '3', 'readonly': 'readonly'}))
    # resumenpropuesta = forms.CharField(label=u'Resumen Propuesta', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    # formulacion = forms.CharField(label=u'Formulación del Problema', widget=forms.Textarea(attrs={'rows': '5'}), required=False)
    # objetivogeneral = forms.CharField(label=u'Objetivo General', widget=forms.Textarea(attrs={'rows': '5'}), required=False)


class PresupuestoProyectoInvestigacionForm(forms.Form):
    titulo = forms.CharField(label=u'Proyecto', required=False, widget=forms.Textarea(attrs={'rows': '3', 'readonly': 'readonly', 'formwidth': '100%'}))
    director = forms.CharField(label=u'Director', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '50%', 'readonly': 'readonly'}))
    compraequipo = forms.CharField(label=u'Contempla compra equipos', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '50%', 'readonly': 'readonly'}))
    meses = forms.CharField(label=u'Tiempo Duración', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '25%', 'readonly': 'readonly'}))
    montototal = forms.FloatField(label=u'Monto Total Proyecto $', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '25%', 'readonly': 'readonly'}))
    totalpresupuesto = forms.FloatField(label=u'Total Presupuesto $', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '25%', 'readonly': 'readonly'}))
    minimocompraequipo = forms.FloatField(label=u'Monto Mínimo Compra Equipo $', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '25%', 'readonly': 'readonly'}))


class CronogramaActividadProyectoInvestigacionForm(forms.Form):
    titulo = forms.CharField(label=u'Proyecto', required=False, widget=forms.Textarea(attrs={'rows': '3', 'readonly': 'readonly', 'formwidth': '100%'}))
    director = forms.CharField(label=u'Director', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '25%', 'readonly': 'readonly'}))
    meses = forms.CharField(label=u'Tiempo Duración', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '25%', 'readonly': 'readonly'}))
    montototal = forms.FloatField(label=u'Monto Total Proyecto $', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '25%', 'readonly': 'readonly'}))
    totalpresupuesto = forms.FloatField(label=u'Total Presupuesto $', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '25%', 'readonly': 'readonly'}))
    objetivogeneral = forms.CharField(label=u'Objetivo General', widget=forms.Textarea(attrs={'rows': '3', 'readonly': 'readonly'}), required=False)
    ponderaciontotal = forms.FloatField(label=u'Ponderación Total', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '25%', 'readonly': 'readonly'}))


class ExternoForm(FormModeloBase):
    nombres = forms.CharField(label=u"Nombres", max_length=200, required=False, widget=forms.TextInput(attrs={'col': '12', 'separator2': True, 'separatortitle': 'Datos Generales', 'autocomplete': 'off'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    nacimiento = forms.DateField(label=u"Fecha Nacimiento", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(), widget=forms.Select(attrs={'col': '6'}))
    nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    email = forms.CharField(label=u"Correo electrónico personal", max_length=200, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    telefono = forms.CharField(label=u'Teléfono celular', max_length=15, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    institucionlabora = forms.CharField(label=u"Institución Labora", max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    cargodesempena = forms.CharField(label=u"Cargo que desempeña", max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))


class FinalizaEdicionForm(FormModeloBase):
    # contenido = forms.CharField(label=u"Contenido del correo", required=True, widget=CKEditorUploadingWidget())
    contenido = forms.CharField(label=u"Contenido del correo", required=False, widget=forms.Textarea(attrs={'col': '12'}))


class EvaluadorProyectoInvestigacionForm(forms.Form):
    titulo = forms.CharField(label=u'Proyecto', required=False, widget=forms.Textarea(attrs={'rows': '3', 'readonly': 'readonly', 'formwidth': '100%'}))
    inicioevalint = forms.DateField(label=u"Inicio", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Evaluación Interna'}), required=False)
    finevalint = forms.DateField(label=u"Fin", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    inicioevalext = forms.DateField(label=u"Inicio", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Evaluación Externa'}), required=False)
    finevalext = forms.DateField(label=u"Fin", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)


class InformeProyectoForm(forms.Form):
    numero = forms.CharField(label=u'Número', max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '50%', 'autocomplete': 'off', 'readonly': 'readonly'}))
    # fecha = forms.CharField(label=u'Fecha', max_length=10, required=False,widget=forms.TextInput(attrs={'class': 'imp-100', 'formwidth': '50%', 'autocomplete': 'off'}))
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    # conclusion = forms.CharField(label=u"Conclusiones", required=True, widget=CKEditorUploadingWidget())
    # recomendacion = forms.CharField(label=u"Recomendaciones", required=True, widget=CKEditorUploadingWidget())


class ResolucionAprobacionProyectoForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)
    numero = forms.CharField(label=u'Número', max_length=150, required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'autocomplete': 'off'}))
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'formwidth': '100%'}))
    resuelve = forms.CharField(label=u"Resuelve", required=True, widget=CKEditorUploadingWidget())
    fechanotificaaprobacion = forms.DateField(label=u"Fecha Notificación Proyectos Aprobados", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'readonly'}), required=False)

class EvaluadorExternoForm(forms.Form):
    nombres = forms.CharField(label=u"Nombres", max_length=200, widget=forms.TextInput(attrs={'formwidth': '100%', 'separator2': True, 'separatortitle': 'Datos Generales', 'autocomplete': 'off'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, widget=forms.TextInput(attrs={'formwidth': '50%', 'autocomplete': 'off'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'autocomplete': 'off'}))
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula', 'formwidth': '30%', 'autocomplete': 'off'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula', 'formwidth': '30%', 'autocomplete': 'off'}))
    identificadororcid = forms.CharField(label=u"Identificador ORCID", max_length=250, initial='', required=False, widget=forms.TextInput(attrs={'formwidth': '40%', 'autocomplete': 'off'}))
    nacimiento = forms.DateField(label=u"Fecha Nacimiento", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%'}), required=False)
    sexo = forms.ModelChoiceField(label=u"Sexo", queryset=Sexo.objects.all(), widget=forms.Select(attrs={'formwidth': '50%'}))
    nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'autocomplete': 'off'}))
    email = forms.CharField(label=u"Correo electrónico personal", max_length=200, required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'autocomplete': 'off'}))
    telefono = forms.CharField(label=u'Teléfono celular', max_length=15, required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'autocomplete': 'off'}))
    institucionlabora = forms.CharField(label=u"Institución Labora", max_length=250, required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'autocomplete': 'off'}))
    cargodesempena = forms.CharField(label=u"Cargo que desempeña", max_length=250, required=False, widget=forms.TextInput(attrs={'formwidth': '100%', 'autocomplete': 'off'}))
    propuestaproyecto = forms.BooleanField(label=u"Propuestas de proyectos", required=False, initial=False, widget=forms.CheckboxInput(attrs={'separator2': True, 'separatortitle': 'Perfil de Evaluación', 'formwidth': '50%', 'class': 'js-switch'}))
    obrarelevancia = forms.BooleanField(label=u"Obras de Relevancia", required=False, initial=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%', 'class': 'js-switch'}))


class EvaluadorProyectoInvestigacionFinalizadoForm(forms.Form):
    titulo = forms.CharField(label=u'Proyecto', required=False, widget=forms.Textarea(attrs={'rows': '3', 'readonly': 'readonly', 'formwidth': '100%'}))


class RegistroPropuestaProyectoInvestigacionExternoForm(FormModeloBase):
    categoria = forms.ModelChoiceField(label=u"Tipo", queryset=Categoria.objects.filter(status=True, vigente=True, tipo=2).order_by('numero'), required=False, widget=forms.Select(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Datos Generales'}))
    codigo = forms.CharField(label=u'Código', max_length=10, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    titulo = forms.CharField(label=u'Título', required=False, widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}))
    archivodocumento = ExtFileField(label=u'Documento Inscripción', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'fieldbuttonsright': [{'id': 'viewdocumento', 'tooltiptext': 'Visualizar Archivo cargado', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-eye'}]}))
    profesor = forms.ModelMultipleChoiceField(label=u'Director UNEMI', queryset=Profesor.objects.filter(pk=0), required=False, widget=forms.Select(attrs={'col': '12'}))
    convocatoria = forms.CharField(label=u'Convocatoria', max_length=100, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento", queryset=SubAreaConocimientoTitulacion.objects.all(), required=False, widget=forms.Select(attrs={'col': '12'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento", queryset=SubAreaEspecificaConocimientoTitulacion.objects.all(), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    sublineainvestigacion = forms.ModelMultipleChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    programainvestigacion = forms.ModelChoiceField(label=u"Programa", queryset=ProgramasInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    industriapriorizada = forms.ModelChoiceField(label=u"Área prioritaria", queryset=IndustriaPriorizada.objects.filter(status=True, vigente=True).order_by('orden'), required=False, widget=forms.Select(attrs={'col': '12'}))
    requiereconvenio = forms.BooleanField(label=u"¿Requiere convenio?", required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    especificaconvenio = forms.CharField(label=u'Especifique convenio', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'readonly': 'readonly'}))
    requierepermiso = forms.BooleanField(label=u"¿Necesita permiso del CEISH?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    especificapermiso = forms.CharField(label=u'Especifique permisos', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))
    tiempomes = forms.IntegerField(label=u"Duración(Meses)", required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    porcentajeequipo = forms.CharField(label=u'% compra equipo', required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    montounemi = forms.FloatField(label=u'Monto UNEMI $', initial="0.00", required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'help_text2': 'Ej: 1234.56'}))
    montomaximounemi = forms.FloatField(label=u'Máximo a Financiar por la UNEMI $', initial="0.00", required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    montootrafuente = forms.FloatField(label=u'Monto otra fuente $', initial="0.00", required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'help_text2': 'Ej: 1234.56', 'fieldbuttons': [{'id': 'infootrafuente', 'tooltiptext': 'Financiamiento Externo', 'btnclasscolor': 'btn-info', 'btnfaicon': 'fa fa-question-circle'}]}))
    montototal = forms.FloatField(label=u'Monto Total $', initial="0.00", required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    tipocobertura = forms.ChoiceField(label=u"Tipo Cobertura", required=False, choices=TIPO_COBERTURA_EJECUCION, widget=forms.Select(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Localización Geográfica del proyecto'}))
    zonas = forms.ModelMultipleChoiceField(label=u'Zonas Planificación(Una o varias)', queryset=ZonaPlanificacion.objects.filter(status=True).order_by('numero'), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    provincias = forms.ModelMultipleChoiceField(label=u'Provincias(Una o varias)', queryset=Provincia.objects.filter(status=True, pais_id=1).order_by('nombre'), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    provincia = forms.ModelChoiceField(label=u'Provincia', queryset=Provincia.objects.filter(status=True, pais=1).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    canton = forms.ModelMultipleChoiceField(label=u'Cantones(Uno o varios)', queryset=Canton.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    requiereparroquia = forms.BooleanField(label=u"¿Ingresar parroquia?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    parroquia = forms.CharField(label=u'Parroquia', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    nombreinsejec = forms.CharField(label=u'Institución', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Institución Participante Ejecutora'}))
    grupoinvestigacion = forms.ModelChoiceField(label=u"Grupo de investigación", queryset=GrupoInvestigacion.objects.filter(status=True, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    representanteinsejec = forms.CharField(label=u'Representante Legal', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    cedulainsejec = forms.CharField(label=u"Identificación", max_length=10, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    emailinsejec = forms.CharField(label=u'e-mail', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    telefonoinsejec = forms.CharField(label=u"Teléfonos", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    faxinsejec = forms.CharField(label=u"Fax", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    direccioninsejec = forms.CharField(label=u'Dirección', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    paginawebinsejec = forms.CharField(label=u'Página web', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    nombreinsejec2 = forms.CharField(label=u'Institución', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Institución Participante Ejecutora 2'}))
    representanteinsejec2 = forms.CharField(label=u'Representante Legal', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    cedulainsejec2 = forms.CharField(label=u"Identificación", max_length=10, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    emailinsejec2 = forms.CharField(label=u'e-mail', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    telefonoinsejec2 = forms.CharField(label=u"Teléfonos", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    faxinsejec2 = forms.CharField(label=u"Fax", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}))
    direccioninsejec2 = forms.CharField(label=u'Dirección', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    paginawebinsejec2 = forms.CharField(label=u'Página web', max_length=250, required=False, widget=forms.TextInput(attrs={'col': '12', 'readonly': 'readonly'}))
    existeinscoejecutora = forms.ChoiceField(label=u"¿Existe institución co-ejecutora?", required=False, choices=VALOR_SI_NO, widget=forms.Select(attrs={'col': '6'}))

    def editar(self, proyecto):
        self.fields['categoria'].queryset = Categoria.objects.filter(status=True, vigente=True, tipo=proyecto.convocatoria.tipo).order_by('numero')
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=proyecto.areaconocimiento, status=True, vigente=True).order_by('nombre')
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=proyecto.subareaconocimiento, status=True, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=proyecto.lineainvestigacion, status=True).order_by('nombre')
        self.fields['programainvestigacion'].queryset = ProgramasInvestigacion.objects.filter(status=True, convocatoriaprogramainvestigacion__convocatoria=proyecto.convocatoria, convocatoriaprogramainvestigacion__status=True).order_by('nombre')
        if proyecto.tipocobertura == 5:
            self.fields['canton'].queryset = Canton.objects.filter(provincia=proyecto.provincia).order_by('nombre')

    def cargarcategoria(self, convocatoria):
        self.fields['categoria'].queryset = Categoria.objects.filter(status=True, vigente=True, tipo=convocatoria.tipo).order_by('numero')

    def cargarprogramas(self, convocatoria):
        self.fields['programainvestigacion'].queryset = ProgramasInvestigacion.objects.filter(status=True, convocatoriaprogramainvestigacion__convocatoria=convocatoria, convocatoriaprogramainvestigacion__status=True).order_by('nombre')


class GrupoInvestigacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=150, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}))
    vigente = forms.BooleanField(label=u"Vigente", required=False, initial=True, widget=forms.CheckboxInput(attrs={'col': '6', 'class': 'js-switch'}))
    resolucionocs = forms.CharField(label=u"Resolución OCS", required=False,
                                 widget=forms.TextInput(attrs={'formwidth': '50%','col': '12'}))
    archivoresolucionocs = ExtFileField(label=u"Subir Resolución OCS", required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=forms.FileInput(attrs={'formwidth': '50%','col': '6'}))


class FinanciamientoPonenciaForm(FormModeloBase):
    nombre = forms.CharField(required=False, max_length=200, label=u'Nombre del Congreso', widget=forms.Textarea(attrs={'rows': '1', 'separator2': True, 'separatortitle': 'Datos de la Ponencia', 'col': '12'}))
    tema = forms.CharField(label=u'Tema de la ponencia', widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    pais = forms.ModelChoiceField(label=u"País del congreso", queryset=Pais.objects.all(), required=False, widget=forms.Select(attrs={'class': 'imp-100', 'col': '12'}))
    fechainicio = forms.DateField(label=u"Fecha Inicio", required=False, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), )
    fechafin = forms.DateField(label=u"Fecha Fin", required=False, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), )
    fechalimpago = forms.DateField(label=u"Fecha Límite Pago Inscripción", required=False, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), )
    costo = forms.FloatField(label=u'Costo Inscripción Congreso', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '6'}))
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.filter(status=True).order_by('id'), required=False, widget=forms.Select(attrs={'col': '6'}))
    link = forms.CharField(label=u'Link', widget=forms.Textarea(attrs={'rows': '2'}), required=False)
    justificacion = forms.CharField(label=u'Justificación', widget=forms.Textarea(attrs={'rows': '3', 'showmsginfo': True, 'msgloc': 'top', 'msgtitle': 'Justificación:', 'msgtext': '', 'msglist': ['¿Por qué considera importante asistir al congreso seleccionado?', '¿Qué logros va alcanzar?', '¿Qué investigación o grupo de investigación lo respalda para asistir?']}), required=False)
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    sublineainvestigacion = forms.ModelChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    provieneproyecto = forms.BooleanField(label=u"¿Proviene de un proyecto de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    tipoproyecto = forms.ChoiceField(label=u'Tipo de Proyecto', choices=TIPO_PROYECTO_ARTICULO, required=False, widget=forms.Select(attrs={'col': '6'}))
    proyectointerno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectosInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    proyectoexterno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    pertenecegrupoinv = forms.BooleanField(label=u"¿Pertenece a un Grupo de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    grupoinvestigacion = forms.ModelChoiceField(label=u"Grupo de investigación", queryset=GrupoInvestigacion.objects.filter(status=True, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    archivoabstract = ExtFileField(label=u'Abstract (Resumen)', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Documentos a subir'}))
    archivocartaaceptacion = ExtFileField(label=u'Carta de aceptación', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivocronograma = ExtFileField(label=u'Cronograma de actividades', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivocomite = ExtFileField(label=u'Comité Científico', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivojustifica = ExtFileField(label=u'Planificación justificar horas docencia', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivoindexacion = ExtFileField(label=u'Evidencia de indexación en Scopus/WoS', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))

    def editar(self, ponencia):
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=ponencia.areaconocimiento, vigente=True).order_by('nombre')
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=ponencia.subareaconocimiento, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=ponencia.lineainvestigacion).order_by('nombre')
        if ponencia.provieneproyecto:
            if ponencia.tipoproyecto < 3:
                self.fields['proyectointerno'].queryset = ProyectosInvestigacion.objects.filter(status=True, tipo=ponencia.tipoproyecto).order_by('nombre')
            else:
                self.fields['proyectoexterno'].queryset = ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre')


class PostulacionObraRelevanciaForm(FormModeloBase):
    tipo = forms.ChoiceField(label=u'Tipo de Obra', choices=TIPO_OBRA_RELEVANCIA, required=False, widget=forms.Select(attrs={'col': '12', 'separator2': True, 'separatortitle': 'Datos de la Postulación'}))
    titulolibro = forms.CharField(label=u'Título del libro', widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    titulocapitulo = forms.CharField(label=u'Título del capítulo de libro', widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    isbn = forms.CharField(label=u"ISBN", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}), required=False)
    aniopublicacion = forms.IntegerField(label=u"Año Publicación", widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}), required=False)
    editorial = forms.CharField(label=u"Editorial", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especifica conocimiento", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    archivolibro = ExtFileField(label=u'Libro', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Evidencias a subir'}))
    archivocapitulo = ExtFileField(label=u'Capítulo del libro', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'col': '6'}))
    archivoeditorial = ExtFileField(label=u'Certificado editorial', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivoinforme = ExtFileField(label=u'Informe Revisión pares', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))

    def editar(self, obrarelevancia):
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=obrarelevancia.areaconocimiento, vigente=True).order_by('nombre')
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=obrarelevancia.subareaconocimiento, vigente=True).order_by('nombre')


class EvaluadorObraRelevanciaForm(FormModeloBase):
    profesor = forms.CharField(label=u'Profesor', widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Datos de la Postulación'}), required=False)
    tipo = forms.CharField(label=u'Tipo de Obra', widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly'}), required=False)
    titulolibro = forms.CharField(label=u'Título del libro', widget=forms.Textarea(attrs={'rows': '3', 'col': '12', 'readonly': 'readonly'}), required=False)
    titulocapitulo = forms.CharField(label=u'Título del capítulo de libro', widget=forms.Textarea(attrs={'rows': '3', 'col': '12', 'readonly': 'readonly'}), required=False)


class ConvocatoriaObraRelevanciaForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    archivo = ExtFileField(label=u'Convocatoria', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivocga = ExtFileField(label=u'Resolución CGA', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    iniciopos = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Postulación'}), required=False)
    finpos = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    inicioevalint = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Evaluación Interna'}), required=False)
    finevalint = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    inicioevalext = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Evaluación Externa'}), required=False)
    finevalext = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)


class SolicitudRegArticuloPubForm(FormModeloBase):
    titulo = forms.CharField(label=u"Título del Artículo", widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    resumen = forms.CharField(label=u'Resumen (Asbtract)', widget=forms.Textarea(attrs={'rows': '5', 'col': '12'}), required=False)
    revista = forms.ModelChoiceField(label=u"Revista", queryset=RevistaInvestigacion.objects.filter(status=True, tiporegistro=1, borrador=False).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12', 'separator2': True, 'separatortitle': 'Datos de la Revista'}))
    baseindexada = forms.CharField(label=u"Base Indexada", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    existerevista = forms.BooleanField(label=u"¿La revista no consta en el listado anterior?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    nombrerevista = forms.CharField(label=u"Nombre de la Revista", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    # fecharecepcion = forms.DateField(label=u"Fecha Recepción", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4', 'separator2': True, 'separatortitle': 'Datos del Artículo'}), required=False)
    estadopublicacion = forms.ChoiceField(label=u'Estado de Publicación', choices=ESTADO_PUBLICACION_ARTICULO, required=False, widget=forms.Select(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Datos del Artículo'}))
    fechapublicacion = forms.DateField(label=u"Fecha Publicación", widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'disabled': 'disabled'}), required=False)
    fechaaceptacion = forms.DateField(label=u"Fecha Aceptación", widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'disabled': 'disabled'}), required=False)
    fechatentpublicacion = forms.DateField(label=u"Fecha Tentativa Publicación (Fecha de publicación según carta de aceptación)", widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'disabled': 'disabled'}), required=False)
    enlace = forms.CharField(label=u"Enlace Artículo", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'style': 'text-transform:lowercase', 'disabled': 'disabled'}), required=False)
    numerorevista = forms.CharField(label=u"Número de la Revista", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'disabled': 'disabled'}), required=False)
    volumenrevista = forms.CharField(label=u"Volumen de la Revista", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'disabled': 'disabled'}), required=False)
    paginaarticulorevista = forms.CharField(label=u"Páginas del artículo en la revista", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'disabled': 'disabled'}), required=False)
    campoamplio = forms.ModelChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    campoespecifico = forms.ModelChoiceField(label="Campo Específico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    campodetallado = forms.ModelChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    sublineainvestigacion = forms.ModelChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    provieneproyecto = forms.BooleanField(label=u"¿Proviene de un proyecto de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    tipoproyecto = forms.ChoiceField(label=u'Tipo de Proyecto', choices=TIPO_PROYECTO_ARTICULO, required=False, widget=forms.Select(attrs={'col': '6'}))
    proyectointerno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectosInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    proyectoexterno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    pertenecegrupoinv = forms.BooleanField(label=u"¿Pertenece a un Grupo de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    grupoinvestigacion = forms.ModelChoiceField(label=u"Grupo de investigación", queryset=GrupoInvestigacion.objects.filter(status=True, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    archivoportada = ExtFileField(label=u'Portada e índice', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'disabled': 'disabled'}))
    archivoarticulo = ExtFileField(label=u'Artículo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'col': '6', 'disabled': 'disabled'}))
    archivocarta = ExtFileField(label=u'Carta de aceptación', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf (Opcional)', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'disabled': 'disabled'}))

    def editar(self, solicitudpublicacion):
        if solicitudpublicacion.revistainvestigacion:
            baseindexada = ",".join([base.baseindexada.nombre for base in solicitudpublicacion.revistainvestigacion.revistainvestigacionbase_set.filter(status=True).order_by('baseindexada__nombre')])
            self.fields['baseindexada'].initial = baseindexada

        self.fields['campoespecifico'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.areaconocimiento, vigente=True).order_by('nombre')
        self.fields['campodetallado'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.subareaconocimiento, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=solicitudpublicacion.lineainvestigacion).order_by('nombre')

        if solicitudpublicacion.provieneproyecto:
            if solicitudpublicacion.tipoproyecto < 3:
                self.fields['proyectointerno'].queryset = ProyectosInvestigacion.objects.filter(status=True, tipo=solicitudpublicacion.tipoproyecto).order_by('nombre')
            else:
                self.fields['proyectoexterno'].queryset = ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre')


class SolicitudRegProceedingPubForm(FormModeloBase):
    titulo = forms.CharField(label=u"Título del Artículo", widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    resumen = forms.CharField(label=u'Resumen (Asbtract)', widget=forms.Textarea(attrs={'rows': '5', 'col': '12'}), required=False)
    congreso = forms.ModelChoiceField(label=u"Congreso", queryset=RevistaInvestigacion.objects.filter(status=True, tiporegistro=2, borrador=False).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12', 'separator2': True, 'separatortitle': 'Datos del Congreso'}))
    baseindexada = forms.CharField(label=u"Base Indexada", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    existecongreso = forms.BooleanField(label=u"¿El congreso no consta en el listado anterior?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    nombrecongreso = forms.CharField(label=u"Nombre del Congreso", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    fecharecepcion = forms.DateField(label=u"Fecha Recepción", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4', 'separator2': True, 'separatortitle': 'Datos del Artículo'}), required=False)
    fechaaprobacion = forms.DateField(label=u"Fecha Aprobación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}), required=False)
    fechapublicacion = forms.DateField(label=u"Fecha Publicación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}), required=False)
    enlace = forms.CharField(label=u"Enlace Artículo", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'style': 'text-transform:lowercase'}), required=False)
    edicioncongreso = forms.CharField(label=u"Edición del Congreso", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    volumenmemoria = forms.CharField(label=u"Volumen de Memoria", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    paginaarticulomemoria = forms.CharField(label=u"Páginas del artículo en la memoria", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    campoamplio = forms.ModelChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    campoespecifico = forms.ModelChoiceField(label="Campo Específico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    campodetallado = forms.ModelChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    sublineainvestigacion = forms.ModelChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    provieneproyecto = forms.BooleanField(label=u"¿Proviene de un proyecto de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    tipoproyecto = forms.ChoiceField(label=u'Tipo de Proyecto', choices=TIPO_PROYECTO_ARTICULO, required=False, widget=forms.Select(attrs={'col': '6'}))
    proyectointerno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectosInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    proyectoexterno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    pertenecegrupoinv = forms.BooleanField(label=u"¿Pertenece a un Grupo de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    grupoinvestigacion = forms.ModelChoiceField(label=u"Grupo de investigación", queryset=GrupoInvestigacion.objects.filter(status=True, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    archivoportada = ExtFileField(label=u'Portada e índice', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Evidencias Documentales'}))
    archivoarticulo = ExtFileField(label=u'Artículo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'col': '6'}))
    archivocarta = ExtFileField(label=u'Carta de aceptación (Opcional)', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf (Opcional)', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))

    def editar(self, solicitudpublicacion):
        if solicitudpublicacion.revistainvestigacion:
            baseindexada = ",".join([base.baseindexada.nombre for base in solicitudpublicacion.revistainvestigacion.revistainvestigacionbase_set.filter(status=True).order_by('baseindexada__nombre')])
            self.fields['baseindexada'].initial = baseindexada

        self.fields['campoespecifico'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.areaconocimiento, vigente=True).order_by('nombre')
        self.fields['campodetallado'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.subareaconocimiento, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=solicitudpublicacion.lineainvestigacion).order_by('nombre')

        if solicitudpublicacion.provieneproyecto:
            if solicitudpublicacion.tipoproyecto < 3:
                self.fields['proyectointerno'].queryset = ProyectosInvestigacion.objects.filter(status=True, tipo=solicitudpublicacion.tipoproyecto).order_by('nombre')
            else:
                self.fields['proyectoexterno'].queryset = ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre')


class SolicitudRegPonenciaPubForm(FormModeloBase):
    titulo = forms.CharField(label=u"Título de la Ponencia", widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    resumen = forms.CharField(label=u'Resumen (Asbtract)', widget=forms.Textarea(attrs={'rows': '5', 'col': '12'}), required=False)
    congreso = forms.CharField(label=u"Congreso", widget=forms.Textarea(attrs={'rows': '2', 'col': '12', 'separator2': True, 'separatortitle': 'Datos del Congreso'}), required=False)
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=False, widget=forms.Select(attrs={'col': '12'}))
    ciudad = forms.CharField(label=u"Ciudad", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'style': 'text-transform:uppercase'}), required=False)
    fechainicio = forms.DateField(label=u"Fecha Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    fechafin = forms.DateField(label=u"Fecha Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    enlace = forms.CharField(label=u"Enlace Congreso", max_length=1000, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'style': 'text-transform:lowercase'}), required=False)
    fechapublicacion = forms.DateField(label=u"Fecha Publicación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6', 'separator2': True, 'separatortitle': 'Datos de la Ponencia'}), required=False)
    campoamplio = forms.ModelChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    campoespecifico = forms.ModelChoiceField(label=u"Campo Específico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    campodetallado = forms.ModelChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    sublineainvestigacion = forms.ModelChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    provieneproyecto = forms.BooleanField(label=u"¿Proviene de un proyecto de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    tipoproyecto = forms.ChoiceField(label=u'Tipo de Proyecto', choices=TIPO_PROYECTO_ARTICULO, required=False, widget=forms.Select(attrs={'col': '6'}))
    proyectointerno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectosInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    proyectoexterno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    pertenecegrupoinv = forms.BooleanField(label=u"¿Pertenece a un Grupo de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    grupoinvestigacion = forms.ModelChoiceField(label=u"Grupo de investigación", queryset=GrupoInvestigacion.objects.filter(status=True, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    archivocongreso = ExtFileField(label=u'Memorias del congreso', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Evidencias Documentales'}))
    archivocarta = ExtFileField(label=u'Carta de aceptación o invitación', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivoparticipacion = ExtFileField(label=u'Certificado participación', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivocomite = ExtFileField(label=u'Comité organizador y científico', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivoprograma = ExtFileField(label=u'Programa del evento', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))

    def editar(self, solicitudpublicacion):
        self.fields['campoespecifico'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.areaconocimiento, vigente=True).order_by('nombre')
        self.fields['campodetallado'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.subareaconocimiento, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=solicitudpublicacion.lineainvestigacion).order_by('nombre')

        if solicitudpublicacion.provieneproyecto:
            if solicitudpublicacion.tipoproyecto < 3:
                self.fields['proyectointerno'].queryset = ProyectosInvestigacion.objects.filter(status=True, tipo=solicitudpublicacion.tipoproyecto).order_by('nombre')
            else:
                self.fields['proyectoexterno'].queryset = ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre')


class SolicitudRegLibroPubForm(FormModeloBase):
    titulo = forms.CharField(label=u"Título del Libro", widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    codigoisbn = forms.CharField(label=u"Código ISBN", max_length=80, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    editor = forms.CharField(label=u"Editor o compilador", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'style': 'text-transform:uppercase'}), required=False)
    fechapublicacion = forms.DateField(label=u"Fecha Publicación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    campoamplio = forms.ModelChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    campoespecifico = forms.ModelChoiceField(label=u"Campo Específico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    campodetallado = forms.ModelChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    sublineainvestigacion = forms.ModelChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    provieneproyecto = forms.BooleanField(label=u"¿Proviene de un proyecto de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    tipoproyecto = forms.ChoiceField(label=u'Tipo de Proyecto', choices=TIPO_PROYECTO_ARTICULO, required=False, widget=forms.Select(attrs={'col': '6'}))
    proyectointerno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectosInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    proyectoexterno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    pertenecegrupoinv = forms.BooleanField(label=u"¿Pertenece a un Grupo de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    grupoinvestigacion = forms.ModelChoiceField(label=u"Grupo de investigación", queryset=GrupoInvestigacion.objects.filter(status=True, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    revisadopar = forms.BooleanField(label=u"¿Revisado por pares?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    archivolibro = ExtFileField(label=u'Libro', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Evidencias Documentales'}))
    archivocertificado = ExtFileField(label=u'Certificado de publicación', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivorevision = ExtFileField(label=u'Certificado o matriz de revisión por pares', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))

    def editar(self, solicitudpublicacion):
        self.fields['campoespecifico'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.areaconocimiento, vigente=True).order_by('nombre')
        self.fields['campodetallado'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.subareaconocimiento, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=solicitudpublicacion.lineainvestigacion).order_by('nombre')


class SolicitudRegCapituloLibroPubForm(FormModeloBase):
    titulocapitulo = forms.CharField(label=u"Título del Capítulo de Libro", widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    titulolibro = forms.CharField(label=u"Título de Libro", widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)
    codigoisbn = forms.CharField(label=u"Código ISBN", max_length=80, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    pagina = forms.CharField(label=u"Páginas", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    editor = forms.CharField(label=u"Editor o compilador", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'style': 'text-transform:uppercase'}), required=False)
    totalcapitulo = forms.CharField(label=u"Total Capítulos en el libro", max_length=3, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}), required=False)
    fechapublicacion = forms.DateField(label=u"Fecha Publicación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    campoamplio = forms.ModelChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    campoespecifico = forms.ModelChoiceField(label=u"Campo Específico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    campodetallado = forms.ModelChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    lineainvestigacion = forms.ModelChoiceField(label=u"Línea Investigación", queryset=LineaInvestigacion.objects.filter(vigente=True, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    sublineainvestigacion = forms.ModelChoiceField(label=u"Sub-Línea Investigación", queryset=SubLineaInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    provieneproyecto = forms.BooleanField(label=u"¿Proviene de un proyecto de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    tipoproyecto = forms.ChoiceField(label=u'Tipo de Proyecto', choices=TIPO_PROYECTO_ARTICULO, required=False, widget=forms.Select(attrs={'col': '6'}))
    proyectointerno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectosInvestigacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    proyectoexterno = forms.ModelChoiceField(label=u"Proyecto", queryset=ProyectoInvestigacionExterno.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    pertenecegrupoinv = forms.BooleanField(label=u"¿Pertenece a un Grupo de Investigación?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    grupoinvestigacion = forms.ModelChoiceField(label=u"Grupo de investigación", queryset=GrupoInvestigacion.objects.filter(status=True, vigente=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    revisadopar = forms.BooleanField(label=u"¿Revisado por pares?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    archivolibro = ExtFileField(label=u'Libro', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Evidencias Documentales'}))
    archivocapitulo = ExtFileField(label=u'Capítulo de libro', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput(attrs={'col': '6'}))
    archivocertificado = ExtFileField(label=u'Certificado de publicación', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))
    archivorevision = ExtFileField(label=u'Certificado o matriz de revisión por pares', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))

    def editar(self, solicitudpublicacion):
        self.fields['campoespecifico'].queryset = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.areaconocimiento, vigente=True).order_by('nombre')
        self.fields['campodetallado'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento=solicitudpublicacion.subareaconocimiento, vigente=True).order_by('nombre')
        self.fields['sublineainvestigacion'].queryset = SubLineaInvestigacion.objects.filter(lineainvestigacion=solicitudpublicacion.lineainvestigacion).order_by('nombre')


class DocenteExternoForm(FormModeloBase):
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'separator2': True, 'separatortitle': 'Datos Generales'}))
    pasaporte = forms.CharField(label=u"Pasaporte", max_length=15, initial='', required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    nombres = forms.CharField(label=u"Nombres", max_length=200, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    nacimiento = forms.DateField(label=u"Fecha Nacimiento", initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(), widget=forms.Select(attrs={'col': '6'}))
    nacionalidad = forms.CharField(label=u"Nacionalidad", max_length=100, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    email = forms.CharField(label=u"Correo electrónico personal", max_length=200, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    telefono = forms.CharField(label=u'Teléfono celular', max_length=15, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    funcionproyecto = forms.CharField(label=u"Rol en el Proyecto", max_length=200, required=False, widget=forms.TextInput(attrs={'col': '6', 'readonly': 'readonly', 'autocomplete': 'off'}))
    institucionlabora = forms.CharField(label=u"Institución Labora", max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    cargodesempena = forms.CharField(label=u"Cargo que desempeña", max_length=250, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))


class UsuarioRevisaEvidenciaDocenteForm(forms.Form):
    personarevisa = forms.IntegerField(initial=0, required=False, label=u'Usuario', widget=forms.Select({'col': '6', }))
    rol = forms.ChoiceField(initial=1, choices=TIPO_ROL, required=False, label=u'Rol', widget=forms.Select({'col': '6', }))

    def ocultar_campo(self, field):
        self.fields['personarevisa'].widget.attrs['col'] = '12'
        if self.fields[field]:
            del self.fields[field]


class BitacoraActividadForm(FormModeloBase):
    titulo = forms.CharField(max_length=500, label=u"Título", widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}), required=False)
    fecha = forms.DateField(label=u"Fecha de inicio", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'col': '6', 'type':'date'}))
    fechafin = forms.DateField(label=u"Fecha fín", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'col': '6', 'type': 'date'}))
    hora = forms.CharField(label=u"Hora Inicio", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3', 'type':'time'}))
    horafin = forms.CharField(label=u"Hora Fín", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3', 'type': 'time', 'valid':False}))
    descripcion = forms.CharField(label=u'Descripción', max_length=10000, widget=forms.Textarea({'class': 'form-control', 'row': '2', 'col': '12'}),required=True)
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png', ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"), required=False, max_upload_size=12582912)
    link = forms.CharField(max_length=1000, label=u"Link", widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}), required=False)
    departamento = forms.ModelMultipleChoiceField(queryset=Departamento.objects.filter(objetivoestrategico__periodopoa_id__gte=2, objetivoestrategico__status=True, integrantes__isnull=False).distinct(), required=False, label=u'Dirección/Facultad', widget=forms.SelectMultiple(attrs={}))
    persona = forms.ModelMultipleChoiceField(label=u"Servidor/es", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=False, widget=forms.SelectMultiple(attrs={}))

    def __init__(self, *args, **kwargs):
        bitacora = kwargs.pop('bitacora', False)
        super(BitacoraActividadForm, self).__init__(*args, **kwargs)
        from sga.pro_cronograma import CRITERIO_ELABORA_ARTICULO_CIENTIFICO
        from inno.models import SubactividadDetalleDistributivo
        if bitacora and bitacora.criterio.es_actividadmacro():
            if bitacora.subactividad and bitacora.subactividad.subactividaddocenteperiodo.criterio.pk == CRITERIO_ELABORA_ARTICULO_CIENTIFICO:
                hoy = datetime.now().date()
                del self.fields['hora']
                del self.fields['link']
                del self.fields['horafin']
                del self.fields['archivo']
                del self.fields['persona']
                del self.fields['departamento']
                self.fields['titulo'].widget.attrs['readonly'] = True
                self.fields['fechafin'].initial = bitacora.fechafin.date()
                self.fields['titulo'].initial = f"Redacción de artículo científico periodo de evaluación {hoy.year}"
                self.fields['descripcion'].widget.attrs['placeholder'] = 'Ubique aquí todas las tareas desarrolladas en el mes para el cumplimiento de esta subactividad...'
        else:
            del self.fields['fechafin']

    def ocultarcampos(self):
        del self.fields['persona']


class SolicitudGrupoInvestigacionForm(FormModeloBase):
    coordinacion = forms.CharField(label=u'Facultad', max_length=150, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'disabled': 'disabled'}))
    carrera = forms.CharField(label=u'Carrera', max_length=150, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'disabled': 'disabled'}))
    nombre = forms.CharField(label=u'Nombre', max_length=150, required=False, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}))
    acronimo = forms.CharField(label=u'Acrónimo', max_length=50, required=False, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}))
    logotipo = ExtFileField(label=u'Logotipo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'fieldbuttonsright': [{'id': 'viewlogotipo', 'tooltiptext': 'Visualizar Archivo cargado', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-eye'}]}))
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea(attrs={'rows': '5', 'col': '12'}))
    objetivogeneral = forms.CharField(label=u'Objetivo General', required=False, widget=forms.Textarea(attrs={'rows': '5', 'col': '12'}))


class ConvocatoriaFinanciamientoPonenciaForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    iniciopos = forms.DateField(label=u"Inicio Postulación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    finpos = forms.DateField(label=u"Fin Postulación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    archivopolitica = ExtFileField(label=u'Políticas', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'fieldbuttonsright': [{'id': 'viewpolitica', 'tooltiptext': 'Visualizar Archivo cargado', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-eye'}]}))
    archivobase = ExtFileField(label=u'Bases Convocatoria', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6', 'fieldbuttonsright': [{'id': 'viewbase', 'tooltiptext': 'Visualizar Archivo cargado', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-eye'}]}))
    publicada = forms.BooleanField(label=u"Publicada", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))


class CronogramavaluacionInvestigacionForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    inicio = forms.DateField(label=u"Inicio Evaluación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    fin = forms.DateField(label=u"Fin Evaluación", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    instructivo = ExtFileField(label=u'Instructivo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '12', 'fieldbuttonsright': [{'id': 'viewinstructivo', 'tooltiptext': 'Visualizar Archivo cargado', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-eye'}]}))


class CitaAsesoriaForm(FormModeloBase):
    modalidad = forms.ChoiceField(label=u'Modalidad', choices=MODALIDAD_ATENCION, required=False, widget=forms.Select(attrs={'col': '6'}))
    gestion = forms.ModelChoiceField(label=u"Gestión", queryset=Gestion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '6'}))
    servicio = forms.ModelChoiceField(label=u"Servicio", queryset=ServicioGestion.objects.filter(status=True, tipo=1), required=False, widget=forms.Select(attrs={'col': '12'}))


class GestionCitaAsesoriaForm(FormModeloBase):
    gestiona = forms.CharField(label=u"Gestión", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Datos de la Cita'}), required=False)
    servicioa = forms.CharField(label=u"Servicio", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    responsable = forms.CharField(label=u"Responsable", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    fecha = forms.CharField(label=u"Fecha", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    modalidada = forms.CharField(label=u"Modalidad", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    horainicio = forms.CharField(label=u"Hora inicio", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    horafin = forms.CharField(label=u"Hora fin", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    solicitantea = forms.CharField(label=u"Solicitante", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    motivoa = forms.CharField(label=u"Motivo", widget=forms.Textarea(attrs={'rows': '4', 'col': '12', 'readonly': 'readonly'}), required=False)
    asistio = forms.BooleanField(label=u"¿Asisitió?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '4', 'separator2': True, 'separatortitle': 'Datos de la Asesoría'}))
    horainicioase = forms.TimeField(label=u"Hora inicio", widget=TimeInput(format='%H:%M', attrs={'col': '4'}), required=False)
    horafinase = forms.TimeField(label=u"Hora fin", widget=TimeInput(format='%H:%M', attrs={'col': '4'}), required=False)
    observacion = forms.CharField(label=u"Observaciones", widget=forms.Textarea(attrs={'rows': '4', 'col': '12'}), required=False)
    proxima = forms.BooleanField(label=u"¿Continúa con las asesorías?", required=False, initial=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    realizaproximaacti = forms.ChoiceField(label=u'¿Quién realiza próxima actividad?', choices=REALIZA_PROXIMA_ACTIVIDAD, required=False, widget=forms.Select(attrs={'col': '6'}))
    tipoactividad = forms.CharField(label=u"Tipo Actividad", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Datos de la próxima cita para asesoría / actividad'}), required=False)
    solicitante = forms.CharField(label=u"Solicitante", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    modalidad = forms.ChoiceField(label=u'Modalidad', choices=MODALIDAD_ATENCION, required=False, widget=forms.Select(attrs={'col': '6'}))
    gestion = forms.ModelChoiceField(label=u"Gestión", queryset=Gestion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '6'}))
    servicio = forms.ModelChoiceField(label=u"Servicio", queryset=ServicioGestion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12'}))


class ReagendamientoCitaAsesoriaForm(FormModeloBase):
    gestiona = forms.CharField(label=u"Gestión", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly', 'separator2': True, 'separatortitle': 'Datos de la Cita'}), required=False)
    servicioa = forms.CharField(label=u"Servicio", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    responsable = forms.CharField(label=u"Responsable", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    fechaa = forms.CharField(label=u"Fecha", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    modalidada = forms.CharField(label=u"Modalidad", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    horainicio = forms.CharField(label=u"Hora inicio", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    horafin = forms.CharField(label=u"Hora fin", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    solicitantea = forms.CharField(label=u"Solicitante", max_length=150, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off', 'readonly': 'readonly'}), required=False)
    motivoa = forms.CharField(label=u"Motivo", widget=forms.Textarea(attrs={'rows': '4', 'col': '12', 'readonly': 'readonly'}), required=False)
    modalidad = forms.ChoiceField(label=u'Modalidad', choices=MODALIDAD_ATENCION, required=False, widget=forms.Select(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Datos del Re-Agendamiento'}))
    gestion = forms.ModelChoiceField(label=u"Gestión", queryset=Gestion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '6', 'disabled': 'disabled'}))
    servicio = forms.ModelChoiceField(label=u"Servicio", queryset=ServicioGestion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12'}))


class HorarioServicioForm(FormModeloBase):
    responsable = forms.ModelChoiceField(label=u'Responsable', queryset=Persona.objects.filter(pk=0), required=False, widget=forms.Select(attrs={'col': '12'}))
    gestion = forms.ModelChoiceField(label=u"Gestión", queryset=Gestion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    servicio = forms.ModelMultipleChoiceField(label=u"Servicio", queryset=ServicioGestion.objects.filter(status=True, pk=0), required=False, widget=forms.SelectMultiple(attrs={'col': '12'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicación", queryset=Ubicacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '12'}))
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=Bloque.objects.filter(status=True).order_by('descripcion'), required=False, widget=forms.Select(attrs={'col': '12'}))
    oficina = forms.CharField(label=u"Oficina", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}), required=False)
    piso = forms.CharField(label=u"Piso", max_length=150, widget=forms.TextInput(attrs={'col': '6', 'autocomplete': 'off'}), required=False)
    desde = forms.DateField(label=u"Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)
    hasta = forms.DateField(label=u"Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}), required=False)

    def editar(self, horario):
        self.fields['servicio'].queryset = ServicioGestion.objects.filter(gestion=horario.mi_gestion(), status=True).order_by('nombre')


class EvidenciasCodigoForm(FormModeloBase):
    archivo = ExtFileField(label=u'Archivo Excel Códigos', required=True, help_text=u'Tamaño Maximo permitido 4Mb, en formato xlsx', ext_whitelist=(".xlsx", ), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))


class BaseInstitucionalForm(FormModeloBase):
    titulo = forms.CharField(label=u"Título", max_length=250, widget=forms.TextInput(attrs={'col': '12', 'autocomplete': 'off'}), required=False)
    contexto = forms.CharField(label=u"Contexto", required=False, widget=forms.Textarea(attrs={'col': '12'}))


class SolicitudBaseInstitucionalForm(FormModeloBase):
    tipotrabajo = forms.ModelChoiceField(label=u"Tipo de trabajo", queryset=TipoTrabajoBaseInstitucional.objects.filter(status=True).order_by('descripcion'), required=False, widget=forms.Select(attrs={'col': '6', 'separator2': True, 'separatortitle': 'Datos de la Solicitud'}))
    baseinstitucional = forms.ModelChoiceField(label=u"Base Institucional", queryset=BaseInstitucional.objects.filter(status=True).order_by('titulo'), required=False, widget=forms.Select(attrs={'col': '12'}))
    contexto = forms.CharField(label=u"Contexto", required=False, widget=forms.Textarea(attrs={'col': '12', 'readonly': 'readonly'}))
