from datetime import datetime, timedelta

from core.custom_forms import FormModeloBase
from django import forms
from django.forms import DateTimeInput

from homologa.models import ROLES_RESPONSABLE, RequisitosHomologacion, RequisitoPeriodoHomologacion, \
    ESTADO_VALIDACION_REQUISITOS, ESTADO_SOLICITUD, ResponsableHomologacion
from investigacion.models import ProyectoInvestigacion
from sga.models import Periodo, Persona, NivelMalla, Coordinacion, Carrera
from sga.forms import ExtFileField

class ResponsableHomologacionForm(FormModeloBase):
    persona = forms.ModelChoiceField(label=u'Responsable', queryset=Persona.objects.select_related().filter(status=True,), required=True,widget=forms.Select(attrs={}))
    rol = forms.ChoiceField(choices=ROLES_RESPONSABLE, required=True, label=u'Tipo', widget=forms.Select(attrs={'col': '6'}))
    estado = forms.BooleanField(initial=False, required=False, label=u'¿Activo?', widget=forms.CheckboxInput(attrs={'data-switchery': 'true', 'col': '6'}))
    coordinaciones = forms.ModelMultipleChoiceField(label=u'Facultades', queryset=Coordinacion.objects.select_related().filter(status=True, excluir=False), required=False,widget=forms.SelectMultiple(attrs={}))
    carrera = forms.ModelChoiceField(label=u'Carreras',queryset=Carrera.objects.select_related().filter(status=True,activa=True), required=False,widget=forms.Select(attrs={'placeholder': 'Seleccione una carrera','col': '12', 'style': 'height: 42px;'}))

    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        id = getattr(instancia, 'id', 0)
        persona = cleaned_data.get('persona')
        estado = cleaned_data.get('estado')
        rol = int(cleaned_data.get('rol'))
        responsables = ResponsableHomologacion.objects.filter(status=True, persona=persona).exclude(id=id)
        if responsables.exists():
            self.add_error('persona', 'Responsable que intenta agregar ya existe registrado actualmente')
        if estado and rol == 2:
            ids_coordinaciones = cleaned_data.get('coordinaciones').values_list('id', flat=True)
            asistentes = ResponsableHomologacion.objects.filter(status=True, estado=True, coordinaciones__id__in=ids_coordinaciones).exclude(id=id)
            if asistentes:
                self.add_error('coordinaciones', 'Coordinaciones seleccionadas ya se encuentra asignado a otro responsables que se encuentra activo')
        return cleaned_data

class PeriodoHomologacionForm(FormModeloBase):
    periodo = forms.ModelChoiceField( queryset=Periodo.objects.filter(status=True).exclude(tipo_id__in=[1,3]), required=True, label=u'Periodo lectivo', widget=forms.Select())
    fechaapertura = forms.DateField(label=u"Fecha Apertura", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    fechacierre = forms.DateField(label=u"Fecha Cierre", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    fechainiciorecepciondocumentos = forms.DateField(label=u"Fecha inicio recepción", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    fechacierrerecepciondocumentos  = forms.DateField(label=u"Fecha cierre recepción", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    fechainiciorevisiongacademica = forms.DateField(label=u"Fecha inicio revisión gestión", widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    fechacierrerevisiongacademica = forms.DateField(label=u"Fecha cierre revisión gestión", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    fechainiciovaldirector = forms.DateField(label=u"Fecha inicio revisión director", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    fechacierrevaldirector = forms.DateField(label=u"Fecha cierre revisión director", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    fechainicioremitiraprobados= forms.DateField(label=u"Fecha inicio remitir aprobados", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    fechacierreremitiraprobados = forms.DateField(label=u"Fecha cierre remitir aprobados", widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'col': '6'}))
    motivo = forms.CharField(label=u'Motivo', required=False, widget=forms.Textarea(attrs={'placeholder': 'Describir el motivo de apertura...','rows': '3'}))
    numdias = forms.IntegerField(label=u'Dias corregir documentos', initial=1, required=True, widget=forms.TextInput(attrs={'class': 'input-number', 'number': 'True', 'decimal': '0', 'col': '6', 'controlwidth': '150px'}))
    publico = forms.BooleanField(initial=False, required=False, label=u'¿Publicar?', widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col': '6'}))

    def __init__(self, *args, **kwargs):
        super(PeriodoHomologacionForm, self).__init__(*args, **kwargs)  # Esto siempre hay que ponerlo
        for field in self.fields:
            self.fields[field].error_messages = {'required': f'Este campo es obligatorio'}

    def clean(self):
        cleaned_data = super().clean()
        periodo = cleaned_data.get("periodo")
        inicio=periodo.inicio
        fin=periodo.fin
        fechaapertura = cleaned_data.get("fechaapertura")
        fechacierre = cleaned_data.get("fechacierre")
        fechainiciorecepciondocumentos = cleaned_data.get("fechainiciorecepciondocumentos")
        fechacierrerecepciondocumentos = cleaned_data.get("fechacierrerecepciondocumentos")
        fechainiciorevisiongacademica = cleaned_data.get("fechainiciorevisiongacademica")
        fechacierrerevisiongacademica = cleaned_data.get("fechacierrerevisiongacademica")
        fechainiciovaldirector = cleaned_data.get("fechainiciovaldirector")
        fechacierrevaldirector = cleaned_data.get("fechacierrevaldirector")
        fechainicioremitiraprobados = cleaned_data.get("fechainicioremitiraprobados")
        fechacierreremitiraprobados = cleaned_data.get("fechacierreremitiraprobados")
        fechas_apertura = [('fechaapertura',fechaapertura),
                           ('fechainiciorecepciondocumentos',fechainiciorecepciondocumentos),
                           ('fechainiciorevisiongacademica',fechainiciorevisiongacademica),
                           ('fechainiciovaldirector',fechainiciovaldirector),
                           ('fechainicioremitiraprobados',fechainicioremitiraprobados)]
        fechas_cierre = [('fechacierre',fechacierre),
                         ('fechacierrerecepciondocumentos',fechacierrerecepciondocumentos),
                         ('fechacierrerevisiongacademica',fechacierrerevisiongacademica),
                         ('fechacierrevaldirector',fechacierrevaldirector),
                         ('fechacierreremitiraprobados',fechacierreremitiraprobados)]
        for fecha in fechas_apertura:
            if fecha[1] < inicio:
                msg = f"Fecha actual tiene que ser mayor o igual a {inicio}, que corresponde al periodo seleccionado"
                self.add_error(fecha[0], msg)
            if not fecha[0] == 'fechaapertura' and fecha[1] < fechaapertura:
                msg = f"Fecha actual tiene que ser mayor o igual que fecha de apertura"
                self.add_error(fecha[0], msg)
        for fecha in fechas_cierre:
            """if fecha[1] > fin:
                msg = f"Fecha actual tiene que ser menor o igual a {fin}, que corresponde al periodo seleccionado"
                self.add_error(fecha[0], msg)"""
            if not fecha[0] == 'fechacierre' and fecha[1] > fechacierre:
                msg = f"Fecha actual tiene que ser menor o igual a fecha de cierre"
                self.add_error(fecha[0], msg)
        if fechacierre == fechaapertura or fechacierre < fechaapertura:
            msg = "Fecha de cierre tiene que ser mayor que la fecha de apertura"
            self.add_error('fechacierre', msg)
            self.add_error('fechaapertura', msg)
        if fechainiciorecepciondocumentos >= fechacierrerecepciondocumentos:
            msg = "Fechas de recepción de documentos fuera de rango"
            self.add_error('fechainiciorecepciondocumentos', msg)
            self.add_error('fechacierrerecepciondocumentos', msg)
        if fechainiciorevisiongacademica >= fechacierrerevisiongacademica:
            msg = "Fechas de revisión de gestión academica fuera de rango"
            self.add_error('fechainiciorevisiongacademica', msg)
            self.add_error('fechacierrerevisiongacademica', msg)
        if fechainiciovaldirector >= fechacierrevaldirector:
            msg = "Fechas de validación de director fuera de rango"
            self.add_error('fechainiciovaldirector', msg)
            self.add_error('fechacierrevaldirector', msg)
        if fechainicioremitiraprobados >= fechacierreremitiraprobados:
            msg = "Fecha de remisión directivo fuera de rango"
            self.add_error('fechainicioremitiraprobados', msg)
            self.add_error('fechacierreremitiraprobados', msg)

class SolicitudDocenteForm(FormModeloBase):
    proyecto = forms.ModelChoiceField( queryset=ProyectoInvestigacion.objects.filter(status=True, aprobado=1), required=True, label=u'Proyecto de investigación', widget=forms.Select({'col': '9'}))
    cantidad = forms.IntegerField(label=u'Cantidad de ayudantes', initial=1, required=True, widget=forms.TextInput(attrs={'class': 'input-number', 'number': 'True', 'decimal': '0', 'col': '3', 'controlwidth': '150px'}))
    mensaje = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea(attrs={'placeholder': 'Describir el motivo por el cual requiere ayudantes...','rows': '3'}))

    def get_fields(self, idpersona):
        self.fields['proyecto'].queryset=ProyectoInvestigacion.objects.filter(status=True, aprobado=1, profesor__persona=idpersona)

class RequisitosHomologacionForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'placeholder': 'Ejem. Cédula de identidad.'}))
    leyenda = forms.CharField(label='Leyenda', required=False, widget=forms.Textarea(attrs={'placeholder': 'Describir una guia del archivo a subir...', 'rows': '3'}))
    archivo = ExtFileField(label=u'Archivo', required=False,help_text=u'Tamaño maximo permitido 2MB, en formato .pdf',ext_whitelist=(".pdf"), max_upload_size=2194304, widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'pdf'}))

class RequisitosPeriodoForm(FormModeloBase):
    requisito = forms.ModelChoiceField(label=u'Requisito',queryset=RequisitosHomologacion.objects.select_related().filter(status=True, ), required=True,widget=forms.Select(attrs={'col': '10'}))

    def validador(self, id=0):
        ban, requisito = True, self.cleaned_data['requisito']
        if RequisitoPeriodoHomologacion.objects.filter(periodo_h_id=id, requisito=requisito, status=True).exists():
            self.add_error('requisito', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban

class ValidarRequisitosForm(FormModeloBase):
    estado = forms.ChoiceField(label=u'Estado', choices=ESTADO_VALIDACION_REQUISITOS[1:4], required=True, widget=forms.Select(attrs={'col': '3'}))
    observacion = forms.CharField(required=True, label=u'Observación', widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Describa una observación.'}))

class ValidarDirectorForm(FormModeloBase):
    revision_director = forms.ChoiceField(label=u'Estado', choices=ESTADO_SOLICITUD[1:3], required=True, widget=forms.Select(attrs={'col':'6'}))
    archivo = ExtFileField(label=u'Informe final de asignaturas homologadas', required=True,help_text=u'Tamaño maximo permitido 2MB, en formato .pdf', ext_whitelist=('.pdf',), max_upload_size=2194304, widget=forms.FileInput(attrs={'col': '6', 'archivo_':'True'}))
    observacion_director = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea(attrs={'rows':'3','placeholder': 'Describa una observación...','style':'resize:none'}))

class SubirResolucionForm(FormModeloBase):
    revision_directivo = forms.ChoiceField(label=u'Estado', choices=ESTADO_SOLICITUD[1:3], required=True, widget=forms.Select(attrs={'col': '2'}))
    archivo_r = ExtFileField(label=u'Resolución de aprobación de consejo directivo', required=True,help_text=u'Tamaño maximo permitido 2MB, en formato .pdf', ext_whitelist=('.pdf',), max_upload_size=2194304, widget=forms.FileInput(attrs={'col': '5','archivo_':'True'}))
    imgevidencia = ExtFileField(label=u'Evidencia de datos subidos al sistema', required=True,help_text=u'Tamaño maximo permitido 2MB, en formato .png, .jpg, .jpeg', ext_whitelist=('.png','.jpg','.jpeg'), max_upload_size=2194304, widget=forms.FileInput(attrs={'col': '5','archivo_':'True'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea(attrs={'rows':'3','placeholder': 'Describa una observación...','style':'resize:none'}))

class SubirDocumentoForm(FormModeloBase):
    nivel = forms.ModelChoiceField(queryset=NivelMalla.objects.filter(status=True).order_by('orden'), required=True, label=u'Nivel', widget=forms.Select({'placeholder': 'Seleccione el nivel de sílabo...'}))
    descripcion = forms.CharField(required=True, label=u'Nombre de la asignatura', widget=forms.TextInput(attrs={'placeholder': 'Ejem. Ecuaciones diferenciales...'}))
    archivo = ExtFileField(label=u'Archivo', required=True,help_text=u'Tamaño máximo permitido 4MB, en formato .pdf', ext_whitelist=('.pdf',), max_upload_size=4194304, widget=forms.FileInput(attrs={'class':'w-100 '}))

    def solo_multiple(self):
        self.fields['nivel'].required=False

    def individual(self):
        self.fields['nivel'].required = False
        self.fields['descripcion'].required = False