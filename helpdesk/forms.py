# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q

from sagest.models import ESTADO_ORDEN_TRABAJO, HdBloque, HdBloqueUbicacion, TIPO_USUARIO, ESTADO_PARTES, \
    GruposCategoria, UnidadMedidaPresupuesto, AnioEjercicio, ActivoTecnologico, Proveedor, ActivoFijo
from helpdesk.models import HdTipoIncidente, HdUrgencia, HdImpacto, HdPrioridad, HdCategoria, HdSubCategoria, \
    HdDetalle_SubCategoria, HdGrupo, HdDetalle_Grupo, \
    HdDetalle_Incidente_Ayudantes, HdMedioReporte, HdCausas, HdEstado, HdProceso, HdEstado_Proceso, HdPiezaPartes, \
    HdSolicitudesPiezaPartes, HdMateriales, HdPreguntas, \
    HdFechacierresolicitudes, DURACION, TIPO_MANTENIMIENTO, PROCESO, TIPO_BIEN, HdConfFrecuencia, HdBien, \
    ESTADO_APROBACION, HdGrupoSistemaEquipo, HdGruposCategoria, HdMantenimientoGruDanios, \
    DetalleJornadaImpresora, ConfiguracionCopia, DIAS_CHOICES, JornadaImpresora, Impresora, SolicitudCopia, \
    BodegaProducto, BodegaTipoTransaccion, BodegaUnidadMedida, FacturaCompra, BodegaProductoDetalle
from sga.models import TipoRespuesta, MONTH_CHOICES, Persona
from posgrado.models import CohorteMaestria, TipoPreguntasPrograma
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from core.custom_forms import FormModeloBase

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


#Help Desk
class HdGrupoForm(forms.Form):
    grupo = forms.CharField(label=u'Nombre del grupo', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=True)
    descripcion = forms.CharField(label=u'Descripción del grupo', widget=forms.Textarea(attrs={'rows': '2'}), required=True)
    tipoincidente = forms.ModelChoiceField(label=u'Tipo', queryset=HdTipoIncidente.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))


class HdDetalle_GrupoForm(forms.Form):
    agente = forms.CharField(label=u'Agente', widget=forms.TextInput(attrs={'class': 'imp-100'}))
    responsable = forms.BooleanField(label=u'Responsable del grupo', required=False, widget=CheckboxInput())

    def existe_responsable(self):
        deshabilitar_campo(self, 'responsable')


class HdUrgenciaForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre de urgencia', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    descripcion = forms.CharField(label=u'Descripción de urgencia', widget=forms.Textarea(attrs={'rows': '2'}),required=False)
    codigo = forms.CharField(label=u'Codigo',max_length=10, required=False)

    def editar(self):
        deshabilitar_campo(self, 'codigo')

class HdImpactoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre de impacto', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    descripcion = forms.CharField(label=u'Descripción de impacto', widget=forms.TextInput(attrs={'rows': '2'}),required=False)
    codigo = forms.CharField(label=u'Codigo', max_length=10, required=False)

    def editar(self):
        deshabilitar_campo(self, 'codigo')


class HdPrioridadForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre de prioridad', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    codigo = forms.CharField(label=u'codigo', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    hora = forms.CharField(label=u'Hora', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    minuto = forms.CharField(label=u'Minutos', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    segundo = forms.CharField(label=u'Segundos', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False,help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png',ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=4194304)

    def editar(self):
        deshabilitar_campo(self, 'codigo')

    def ocultarimagen(self):
        del self.fields['imagen']


class HdUrgencia_Impacto_PrioridadForm(forms.Form):
    urgencia = forms.ModelChoiceField(HdUrgencia.objects.filter(status=True), required=False, label=u'Urgencia', widget=forms.Select())
    impacto = forms.ModelChoiceField(HdImpacto.objects.filter(status=True), required=False, label=u'Impacto', widget=forms.Select())
    prioridad = forms.ModelChoiceField(HdPrioridad.objects.filter(status=True), required=False, label=u'Prioridad', widget=forms.Select())
    modificar = forms.BooleanField(label=u'Modificar tiempo de resolución', required=False, widget=CheckboxInput())
    hora = forms.CharField(label=u'Hora', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    minuto = forms.CharField(label=u'Minutos', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))
    segundo = forms.CharField(label=u'Segundos', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '30%'}))

    def editar(self):
        deshabilitar_campo(self, 'hora')
        deshabilitar_campo(self, 'minuto')
        deshabilitar_campo(self, 'segundo')

class HdCatrgoriaForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre de Categoria", max_length=50, widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    tipoincidente =  forms.ModelChoiceField(label=u'Tipo de incidente', queryset=HdTipoIncidente.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')
        # deshabilitar_campo(self, 'tipoincidente')


class HdTipoIncidenteForm(forms.Form):
    nombre = forms.CharField(label=u"Tipo de incidente", max_length=50, widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    descripcion = forms.CharField(label=u"Descripción", max_length=1000, widget=forms.Textarea(attrs={'rows': '2', 'with': '100%'}), required=False)

    def editar(self):
        deshabilitar_campo(self, 'nombre')


class HdSubCatrgoriaForm(forms.Form):
    categoria = forms.CharField(label=u"Nombre de Categoria", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    subcategoria = forms.CharField(label=u"Nombre Dispositivo", max_length=50, widget=forms.TextInput(attrs={'class': 'imp-100'}))

    def editar(self):
        deshabilitar_campo(self, 'categoria')


class HdDetalleSubCategoriaForm(forms.Form):
    subcategoria = forms.CharField(label=u"Sub Categoria", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    detalle = forms.CharField(label=u"Nombre detalle", max_length=50, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    urgencia = forms.ModelChoiceField(label=u"Urgencia",queryset=HdUrgencia.objects.filter(status=True), required=True,widget=forms.Select(attrs={'formwidth': '50%'}))
    impacto = forms.ModelChoiceField(label=u"Impacto", queryset=HdImpacto.objects.filter(status=True), required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    prioridad = forms.CharField(label=u"Prioridad", max_length=50, required=False, widget=forms.TextInput(attrs={'formwidth': '60%'}))
    tiemporesolucion = forms.CharField(label=u"Hora resolución", max_length=50, required=False, widget=forms.TextInput(attrs={'formwidth': '40%'}))

    def editar(self):
        deshabilitar_campo(self, 'subcategoria')
        deshabilitar_campo(self, 'prioridad')
        deshabilitar_campo(self, 'tiemporesolucion')


class HdEstadoForm(forms.Form):
    nombre = forms.CharField(label=u"Estado de Help Desk", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"),max_upload_size=4194304)


class HdEstadoEditForm(forms.Form):
    nombre = forms.CharField(label=u"Estado de Help Desk", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')


class HdEstadoImagenForm(forms.Form):
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"),max_upload_size=4194304)


class HdPrioridadImagenForm(forms.Form):
    imagen = ExtFileField(label=u'Seleccione Imagen', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  jpg ,jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"),max_upload_size=4194304)


class HdMedioReporteForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=50, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))
    descripcion = forms.CharField(label=u"Descripción", max_length=300, required=False,widget=forms.Textarea(attrs={'rows': '3'}))

    def editar(self):
        deshabilitar_campo(self, 'nombre')
        deshabilitar_campo(self, 'descripcion')


class HdIncidenciaLicenciaFrom(forms.Form):
    asunto = forms.CharField(label=u"Incidente", max_length=500, required=False,
                             widget=forms.Textarea(attrs={'rows': '3', 'with': '100'}))


    resolucion = forms.CharField(label=u'Resolución del incidente',
                                 widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}), required=False)

    fechareporte = forms.DateField(label=u'Fecha de reporte', initial=datetime.now().date(), required=False,
                                   input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                    attrs={'class': 'selectorfecha',
                                                                                           'formwidth': '50%'}))
    horareporte = forms.TimeField(label=u'Hora de reporte ', initial=str(datetime.now().time()), required=False,
                                  input_formats=["%H:%M"], widget=DateTimeInput(format='%H:%M',
                                                                                attrs={'class': 'selectorhora',
                                                                                       'formwidth': '50%'}))

class HdDetalleIncidenciaProductoFrom(forms.Form):


    producto = forms.ModelChoiceField(queryset=BodegaProducto.objects.filter(status=True), label="Producto",
                                      widget=forms.Select(
                                          attrs={"class": "form-select select2", 'col': '5', "style": "width: 50%;",
                                                 "idp": "producto-select"}),
                                      required=True, )
    unidadmedida = forms.ModelChoiceField(BodegaProductoDetalle.objects.filter(status=True), label=u'Unidad de medida',
                                          required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    cantidad = forms.IntegerField(initial=1, label=u'Cantidad', required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'number': 'True', 'decimal': '0', 'col': '6', 'autocomplete': 'off',
               'controlwidth': '50%', 'onkeypress': 'return soloNumeros(event)'}))




class HdDetalleIncidenciaLicenciaFrom(forms.Form):
    activo = forms.IntegerField(initial=0, required=False, label=u'Activo tecnológico',
                                widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    persona = forms.IntegerField(initial=0, required=False, label=u'Responsable',
                                 widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))

    producto = forms.ModelChoiceField(queryset=BodegaProducto.objects.filter(status=True), label="Producto",
                                      widget=forms.Select(
                                          attrs={"class": "form-select select2", 'col': '5', "style": "width: 50%;",
                                                 "idp": "producto-select"}),
                                      required=True, )


class HdIncidenciaFrom(forms.Form):
    asunto = forms.CharField(label=u"Incidente", max_length=500, required=False, widget=forms.Textarea(attrs={'rows': '3', 'with': '100'}))
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}), required=False)
    persona = forms.IntegerField(initial=0, required=False, label=u'Solicitante',widget=forms.TextInput(attrs={'select2search': 'true'}))
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicacion", queryset=HdBloqueUbicacion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    # departamento = forms.IntegerField(initial=0, required=False, label=u'Departamento',widget=forms.TextInput(attrs={'select2search': 'true'}))
    tipoincidente = forms.ModelChoiceField(label=u"Tipo de grupo", queryset=HdTipoIncidente.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))

    grupo = forms.ModelChoiceField(label=u"Grupos de agente", queryset=HdGrupo.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    agente = forms.ModelChoiceField(label=u'Agente a reasignar', queryset=HdDetalle_Grupo.objects.filter(estado=True, status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    ayudantes = forms.ModelMultipleChoiceField(label=u'Agentes ayudantes', queryset=HdDetalle_Grupo.objects.all(), required=False)
    categoria = forms.ModelChoiceField(label=u"Categoria", queryset=HdCategoria.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    subcategoria = forms.ModelChoiceField(label=u"Sub Categoria", queryset=HdSubCategoria.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    detallesubcategoria = forms.ModelChoiceField(label=u"Detalle Sub Categoria", queryset=HdDetalle_SubCategoria.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    revisionequipoexterno = forms.BooleanField(initial=False, label=u'Revisión de equipo personal que realiza gestión institucional', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    revisionequiposincodigo = forms.BooleanField(initial=False, label=u'Revisión de equipo institucional sin código de barra o sin registro en el sistema interno', required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    serie = forms.CharField(label=u"Serie o código", max_length=250, required=False, widget=forms.TextInput(attrs={'formwidth': '100%'}))
    activo = forms.IntegerField(initial=0, required=False, label=u'Activo Fijo',widget=forms.TextInput(attrs={'select2search': 'true'}))

    fechacompra = forms.CharField(label=u"Fecha de Ingreso", widget=forms.TextInput(attrs={'formwidth': '35%'}), required=False)
    vidautil = forms.CharField(label=u"Vida Util", widget=forms.TextInput(attrs={'formwidth': '30%'}), required=False)
    tiemporestante = forms.CharField(label=u"Fecha de caducidad", widget=forms.TextInput(attrs={'formwidth': '35%'}), required=False)
    resolucion = forms.CharField(label=u'Resolución del incidente', widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}), required=False)

    medioreporte = forms.ModelChoiceField(label=u"Modo de Reporte", queryset=HdMedioReporte.objects.filter(status=True),required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    fechareporte = forms.DateField(label=u'Fecha de reporte', initial=datetime.now().date(),required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    horareporte = forms.TimeField(label=u'Hora de reporte ', initial=str(datetime.now().time()),required=False, input_formats=["%H:%M"], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '50%'}))
    estado = forms.ModelChoiceField(label=u"Estado Incidente", queryset=HdEstado.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    proceso = forms.ModelChoiceField(label=u"Proceso", queryset=HdProceso.objects.filter(  status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    estadobaja = forms.ModelChoiceField(label=u"Estado de proceso",queryset=HdEstado_Proceso.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    causa = forms.ModelChoiceField(label=u"Causa de incidente",queryset=HdCausas.objects.filter(  status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    # fecharesolucion = forms.DateField(label=u'Fecha de resolución', initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha','formwidth': '50%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  pdf, jpg, png, jpeg', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304)

    def cargarayudantes(self, grupo):
        self.fields['ayudantes'].queryset = HdDetalle_Grupo.objects.filter(grupo=grupo).order_by('persona__apellido1', 'persona__apellido2')

    def editar(self, incidente):
        del self.fields['descripcion']
        del self.fields['archivo']
        del self.fields['proceso']
        del self.fields['estadobaja']
        del self.fields['resolucion']
        deshabilitar_campo(self, 'persona')
        # deshabilitar_campo(self, 'fechareporte')
        # deshabilitar_campo(self, 'horareporte')
        deshabilitar_campo(self, 'estado')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        if incidente.tipoincidente.id  == 3:
            del self.fields['revisionequiposincodigo']
            del self.fields['revisionequipoexterno']
            del self.fields['serie']
            del self.fields['causa']
        # deshabilitar_campo(self, 'fecharesolucion')

    def tiene_agente(self):
        deshabilitar_campo(self, 'tipoincidente')
        deshabilitar_campo(self, 'grupo')
        deshabilitar_campo(self, 'agente')
        deshabilitar_campo(self, 'ayudantes')

    def resolver(self):
        del self.fields['descripcion']
        del self.fields['archivo']
        # del self.fields['fechareporte']
        # del self.fields['horareporte']
        deshabilitar_campo(self, 'asunto')
        deshabilitar_campo(self, 'persona')
        deshabilitar_campo(self, 'tipoincidente')
        deshabilitar_campo(self, 'bloque')
        deshabilitar_campo(self, 'ubicacion')
        deshabilitar_campo(self, 'grupo')
        deshabilitar_campo(self, 'agente')
        # deshabilitar_campo(self, 'ayudantes')
        deshabilitar_campo(self, 'medioreporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        # deshabilitar_campo(self, 'categoria')
        # deshabilitar_campo(self, 'subcategoria')

    def add(self):
        del self.fields['descripcion']
        # deshabilitar_campo(self, 'fechareporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'activo')
        deshabilitar_campo(self, 'tiemporestante')

    def adicionar(self):
        del self.fields['descripcion']
        # deshabilitar_campo(self, 'fechareporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        # del self.fields['fecharesolucion']

    def adicionar_x_agente(self):
        del self.fields['descripcion']
        deshabilitar_campo(self, 'fechareporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        # del self.fields['fechareporte']
        del self.fields['horareporte']

    def reasignar(self):
        del self.fields['descripcion']
        del self.fields['archivo']
        del self.fields['estadobaja']
        del self.fields['proceso']
        del self.fields['estado']
        del self.fields['causa']
        del self.fields['horareporte']
        del self.fields['fechareporte']
        deshabilitar_campo(self, 'persona')
        deshabilitar_campo(self, 'tipoincidente')
        deshabilitar_campo(self, 'bloque')
        deshabilitar_campo(self, 'ubicacion')
        deshabilitar_campo(self, 'medioreporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')
        #deshabilitar_campo(self, 'ayudantes')

    def escalar(self):
        del self.fields['descripcion']
        del self.fields['archivo']
        del self.fields['estadobaja']
        del self.fields['proceso']
        del self.fields['estado']
        del self.fields['grupo']
        del self.fields['agente']
        # del self.fields['categoria']
        # del self.fields['detallesubcategoria']
        # del self.fields['subcategoria']
        del self.fields['causa']
        del self.fields['ayudantes']
        # del self.fields['revisionequipoexterno']
        # del self.fields['revisionequiposincodigo']
        # del self.fields['serie']
        deshabilitar_campo(self, 'asunto')
        deshabilitar_campo(self, 'persona')
        deshabilitar_campo(self, 'bloque')
        deshabilitar_campo(self, 'ubicacion')
        deshabilitar_campo(self, 'medioreporte')
        deshabilitar_campo(self, 'fechareporte')
        deshabilitar_campo(self, 'horareporte')
        deshabilitar_campo(self, 'fechacompra')
        deshabilitar_campo(self, 'vidautil')
        deshabilitar_campo(self, 'tiemporestante')


class HdSolicitarIncidenteFrom(forms.Form):
    tipousuario = forms.ChoiceField(label=u'Registro de incidente como usuario con perfil', choices=TIPO_USUARIO, required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    tercerapersona = forms.IntegerField(initial=0, required=False, label=u'Solicitante', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'imp-100'}))
    tipoincidente = forms.ModelChoiceField(label=u"Tipo de grupo", queryset=HdTipoIncidente.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%', 'style':'width:100%', 'disabled':'disabled'}))
    #concodigo = forms.BooleanField(initial=True, label=u'Con Codigo?', required=False)
    activo = forms.IntegerField(initial=0, required=False, label=u'Activo fijo', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'imp-100'}))
    #activosincodigo = forms.IntegerField(initial=0, required=False, label=u'Activo sin Código', widget=forms.TextInput(attrs={'select2search': 'true', 'class': 'imp-100'}))
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicación", queryset=HdBloqueUbicacion.objects.filter(status=True),required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    asunto = forms.CharField(label=u"Asunto del incidente", max_length=500, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  pdf, jpg, png, jpeg', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304)

    def cargarubicacion(self, bloque):
        self.fields['ubicacion'].queryset = HdBloqueUbicacion.objects.filter(bloque=bloque, status=True)

    def es_docente(self):
        del self.fields['tipoincidente']
        del self.fields['tipousuario']
        # del self.fields['tercerapersona']

    def desactiva_tipousuario(self):
        del self.fields['tipousuario']

    def desactivar(self):
        del self.fields['tercerapersona']

    def editar(self, activo):
        self.fields['activo'].widget.attrs['descripcion'] = activo
        self.fields['activo'].initial = activo.id
        self.fields['activo'].widget.attrs['value'] = activo.id

    # def editaractivo(self, activosincodigo):
    #     self.fields['activosincodigo'].widget.attrs['descripcion'] = activosincodigo
    #     self.fields['activosincodigo'].initial = activosincodigo.id
    #     self.fields['activosincodigo'].widget.attrs['value'] = activosincodigo.id
    # def edit(self, concodigo):
    #
    #     deshabilitar_campo(self, 'activo')
    #
    # def desactivarcodigo(self, concodigo):
    #
    #     deshabilitar_campo(self, 'activosincodigo')



class HdDirectorForm(forms.Form):
    director = forms.CharField(label=u"Director", max_length=50, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))


class CerrarOrdenForm(forms.Form):
    informe = forms.CharField(label=u"Informe", max_length=250, required=False,widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}))
    estado = forms.ChoiceField(label=u'Estado', choices=ESTADO_ORDEN_TRABAJO, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    # calificacion = forms.FloatField(label=u"Calificación", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, png, jpeg', ext_whitelist=(".pdf"), max_upload_size=4194304, required=False)

    def quitar_estado(self):
        del self.fields['estado']

class DetalleOrdenForm(forms.Form):
    repuesto = forms.CharField(label=u"Repuesto", max_length=250, required=False,widget=forms.Textarea(attrs={'rows': '4', 'with': '100%'}))
    cantidad = forms.FloatField(label=u"Cantidad", initial="0.00", required=True,widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))

class HdProcesoFrom(forms.Form):
    nombre = forms.CharField(label=u"Nombre Proceso", max_length=50, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))


class HdEstadoProcesoFrom(forms.Form):
    nombre = forms.CharField(label=u"Nombre del estado proceso", max_length=50, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))
    detalle = forms.CharField(label=u"Detalle", max_length=250, required=False,widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}))
    proceso = forms.ModelChoiceField(label=u'Proceso', queryset=HdProceso.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))

    def adcionarestados(self):
        del self.fields['proceso']


class HdDetalleIncidenteFrom(forms.Form):
    grupo = forms.ModelChoiceField(label=u"Grupos", queryset=HdGrupo.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '100%'}))
    agente = forms.ModelChoiceField(label=u'Agente', queryset=HdDetalle_Grupo.objects.filter(estado=True, status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    estado = forms.ModelChoiceField(label=u"Estado Incidente", queryset=HdEstado.objects.filter(status=True),required=False, widget=forms.Select(attrs={'formwidth': '100%'}))

class HdRequerimientoPiezaPartesForm(forms.Form):
    solicitudes = forms.ModelChoiceField(HdPiezaPartes.objects.filter(status=True), required=True, label=u'Piezas y Partes', widget=forms.Select(attrs={}))
    listasolicitudes = forms.ModelChoiceField(HdSolicitudesPiezaPartes.objects.filter(status=True), required=True, label=u'Descripción', widget=forms.Select(attrs={}))

class HdRequerimientosPiezaPartesForm(forms.Form):
    codigoresuelve = forms.CharField(label=u'Codigo', max_length=300, required=False, widget=forms.TextInput())
    observacionresuelve = forms.CharField(label=u'Observacion', widget=forms.Textarea(attrs={'rows': '3'}),required=False)

class HdMaterial_IncidenteForm(forms.Form):
    material = forms.ModelChoiceField(label=u"Material:", queryset=HdMateriales.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    cantidad = forms.IntegerField(initial=0, label=u'Cantidad', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    unidadmedida = forms.ModelChoiceField(UnidadMedidaPresupuesto.objects.filter(status=True),label=u'Unidad de medida', required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
class SeleccionarActivoForm(forms.Form):
    activo = forms.IntegerField(initial=0, required=False, label=u'Seleccionar activo',widget=forms.TextInput(attrs={'select2search': 'true'}))
class HdPiezaPartesForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '2'}),required=False)
    estado = forms.ChoiceField(label=u"Estado", required=True, choices=ESTADO_PARTES, widget=forms.Select(attrs={'class': 'imp-90'}))
    archivo = ExtFileField(label=u'Imagen', required=False,help_text=u'Tamaño Maximo permitido 2Mb, en formato jpg,jpeg,png', ext_whitelist=(".jpg", ".jpeg", ".png"),max_upload_size=2194304, widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))
class HdSolicitudPiezaPartesForm(forms.Form):
    grupocategoria = forms.ModelChoiceField(GruposCategoria.objects.filter(status=True).order_by('descripcion'), required=False, label=u'Categoria', widget=forms.Select(attrs={}))
    piezaparte = forms.ModelChoiceField(HdPiezaPartes.objects.filter(status=True).order_by('descripcion'), required=True, label=u'Pieza y Parte', widget=forms.Select(attrs={}))
    tipo = forms.CharField(label=u'Tipo', max_length=300, required=False, widget=forms.TextInput())
    capacidad = forms.CharField(label=u'Capacidad', max_length=300, required=False, widget=forms.TextInput())
    velocidad = forms.CharField(label=u'Velocidad', max_length=300, required=False, widget=forms.TextInput())
    descripcion = forms.CharField(label=u"Especificaciones extras", max_length=1000, widget=forms.Textarea(attrs={'rows': '2', 'with': '100%'}), required=False)

class HdCausasForm(forms.Form):
    tipoincidente = forms.ModelChoiceField(label=u'Tipo de incidente', queryset=HdTipoIncidente.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    nombre = forms.CharField(label=u'Nombre', max_length=300, required=False, widget=forms.TextInput())

class HdCabEncuestasForm(forms.Form):
    nombre = forms.CharField(label=u"Nombre", max_length=50, widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    descripcion = forms.CharField(label=u"Descripción", max_length=1000, widget=forms.Textarea(attrs={'rows': '2', 'with': '100%'}), required=False)
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)

class HdDetEncuestasForm(forms.Form):
    pregunta = forms.ModelChoiceField(label=u'Pregunta', queryset=HdPreguntas.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    tiporespuesta = forms.ModelChoiceField(label=u'Tipo Respuesta', queryset=TipoRespuesta.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)
class HdPreciosForm(forms.Form):
    cierresolicitudes = forms.ModelChoiceField(label=u'Fechas Activas', queryset=HdFechacierresolicitudes.objects.filter(activo=True,status=True), required=False, widget=forms.Select(attrs={'formwidth': '100%'}))
    valor = forms.DecimalField(initial='0.0000', label=u'Precio Referencial', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)

class HdFechacierreForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea(attrs={'rows': '5'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    fechafin = forms.DateField(label=u"Fecha fin", required=True, initial=datetime.now().date(),input_formats=['%d-%m-%Y'],widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    activo = forms.BooleanField(initial=False, label=u'Activo', required=False)

class HdMaterialForm(forms.Form):
    codigo = forms.CharField(label=u"Codigo", max_length=100, widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    nombre = forms.CharField(label=u'Nombre', max_length=300, required=True, widget=forms.TextInput())

#planificacion
class HdGrupoSistemaEquipoForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", max_length=50, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))


class HdBienForm(forms.Form):
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicacion", queryset=HdBloqueUbicacion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    gruposistema= forms.IntegerField(initial=0, required=False, label=u'Grupo Sistema',widget=forms.TextInput(attrs={'select2search': 'true'}))
    sistemaequipo = forms.CharField(label=u"Sistema/Equipo", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    cantidad = forms.IntegerField(initial=0, label=u'Cantidad', required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    observacion = forms.CharField(label=u'Observacion', widget=forms.Textarea(attrs={'rows': '3'}),required=False)

    def editar(self, gruposistema):
        self.fields['gruposistema'].widget.attrs['descripcion'] = gruposistema
        self.fields['gruposistema'].initial = gruposistema.id
        self.fields['gruposistema'].widget.attrs['value'] = gruposistema.id

class HdConfFrecuenciaForm(forms.Form):
    duracion = forms.ChoiceField(label=u"Duración", required=True, choices=DURACION,widget=forms.Select(attrs={'class': 'imp-90'}))
    cantidad = forms.IntegerField(initial=0, label=u'Cantidad', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))


class HdFrecuenciaForm(forms.Form):
    gruposistema = forms.IntegerField(initial=0, required=False, label=u'Grupo Sistema/Equipo',widget=forms.TextInput(attrs={'select2search': 'true'}))
    bien = forms.IntegerField(initial=0, required=False, label=u'Sistema/Equipo',widget=forms.TextInput(attrs={'select2search': 'true'}))
    tipomantenimiento = forms.ChoiceField(label=u"Tipo Mantenimiento", required=True, choices=TIPO_MANTENIMIENTO,widget=forms.Select(attrs={'class': 'imp-90'}))
    proceso = forms.ChoiceField(label=u"Proceso", required=True, choices=PROCESO,widget=forms.Select(attrs={'class': 'imp-90'}))
    descripcion = forms.CharField(label=u"Descripción", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    frecuencia =forms.ModelChoiceField(label=u"Frecuencia", queryset=HdConfFrecuencia.objects.filter(status=True), required=False,
                                  widget=forms.Select(attrs={'formwidth': '75%'}))
    consideracion = forms.CharField(label=u"Consideraciones especiales", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))


    def editar(self, gruposistema):
        self.fields['gruposistema'].widget.attrs['descripcion'] = gruposistema
        self.fields['gruposistema'].initial = gruposistema.id
        self.fields['gruposistema'].widget.attrs['value'] = gruposistema.id

    def editarbien(self, bien):
        self.fields['bien'].widget.attrs['descripcion'] = bien
        self.fields['bien'].initial = bien.id
        self.fields['bien'].widget.attrs['value'] = bien.id

    def editarfrecuencia(self, frecuencia):
        self.fields['frecuencia'].widget.attrs['descripcion'] = frecuencia
        self.fields['frecuencia'].initial = frecuencia.id
        self.fields['frecuencia'].widget.attrs['value'] = frecuencia.id



class HdCronogramaMantenimientoSemForm(forms.Form):
    gruposistema = forms.IntegerField(initial=0, required=False, label=u'Grupo Sistema',widget=forms.TextInput(attrs={'select2search': 'true'}))
    mes = forms.ChoiceField(label=u"Mes", required=True, choices=MONTH_CHOICES,widget=forms.Select(attrs={'class': 'imp-90'}))

    def resolver(self):
        deshabilitar_campo(self, 'gruposistema')
        deshabilitar_campo(self, 'mes')


    def editar(self, gruposistema):
        self.fields['gruposistema'].widget.attrs['descripcion'] = gruposistema
        self.fields['gruposistema'].initial = gruposistema.id
        self.fields['gruposistema'].widget.attrs['value'] = gruposistema.id


class HdDetCronogramaMantenimientoSemForm(forms.Form):

    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False,
                                    widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicacion", queryset=HdBloqueUbicacion.objects.filter(status=True),
                                       required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    bien = forms.ModelChoiceField(HdBien.objects.filter(status=True),
                                  label=u'Sistemas/Equipos', required=False,
                                  widget=forms.Select(attrs={'formwidth': '50%'}))
    cantidad =forms.IntegerField(initial=0, label=u'Cantidad', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    fechainicio =forms.DateField(label=u"Fecha Inicio", required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'],widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha','formwidth': '50%'}))
    fechafin = forms.DateField(label=u"Fecha Fin", required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'],widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha','formwidth': '50%'}))


class HdCronogramaMantenimientoForm(forms.Form):
    gruposistema = forms.IntegerField(initial=0, required=False, label=u'Grupo Sistema',widget=forms.TextInput(attrs={'select2search': 'true'}))
    tipomantenimiento = forms.ChoiceField(label=u"Tipo Mantenimiento", required=True, choices=TIPO_MANTENIMIENTO,widget=forms.Select(attrs={'class': 'imp-90'}))
    proveedor = forms.IntegerField(initial=0, required=False, label=u'Proveedor',widget=forms.TextInput(attrs={'select2search': 'true'}))
    desde = forms.DateField(label=u"Fecha desde", required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    hasta = forms.DateField(label=u"Fecha hasta", required=True, initial=datetime.now().date(), input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))

    def editar(self, gruposistema):
        self.fields['gruposistema'].widget.attrs['descripcion'] = gruposistema
        self.fields['gruposistema'].initial = gruposistema.id
        self.fields['gruposistema'].widget.attrs['value'] = gruposistema.id

    def editar_proveedor(self, proveedor):
        self.fields['proveedor'].widget.attrs['descripcion'] = proveedor
        self.fields['proveedor'].initial = proveedor.id
        self.fields['proveedor'].widget.attrs['value'] = proveedor.id


class HdDetCronogramaMantenimientoForm(forms.Form):

    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicacion", queryset=HdBloqueUbicacion.objects.filter(status=True),required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    bien = forms.IntegerField(initial=0, required=False, label=u'Bien',widget=forms.TextInput(attrs={'select2search': 'true'}))
    mes = forms.ChoiceField(label=u"Mes", required=True, choices=MONTH_CHOICES,widget=forms.Select(attrs={'class': 'imp-90'}))
    descripcion = forms.CharField(label=u"Descripción del Trabajo", max_length=50, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))
    cantidad = forms.IntegerField(initial=0, label=u'Cantidad', required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0','formwidth': '50%'}))
    inventario = forms.DecimalField(initial='0.0000', label=u'Inventario', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda','formwidth': '50%'}))

    def editarbien(self, bien):
            self.fields['bien'].widget.attrs['descripcion'] = bien
            self.fields['bien'].initial = bien.id
            self.fields['bien'].widget.attrs['value'] = bien.id


class HdReparacionForm(forms.Form):

    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicacion", queryset=HdBloqueUbicacion.objects.filter(status=True),required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    gruposistema = forms.IntegerField(initial=0, required=False, label=u'Grupo Sistema', widget=forms.TextInput(attrs={'select2search': 'true'}))

    def editar(self, gruposistema):
        self.fields['gruposistema'].widget.attrs['descripcion'] = gruposistema
        self.fields['gruposistema'].initial = gruposistema.id
        self.fields['gruposistema'].widget.attrs['value'] = gruposistema.id

class HdDetalle_ReparacionForm(forms.Form):
    bien = forms.IntegerField(initial=0, required=False, label=u'Bien',widget=forms.TextInput(attrs={'select2search': 'true'}))
    cantidad = forms.IntegerField(initial=0, label=u'Cantidad', required=False,widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0'}))
    descripcion = forms.CharField(label=u"Descripción", max_length=50, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))
    def editarbien(self, bien):
                self.fields['bien'].widget.attrs['descripcion'] = bien
                self.fields['bien'].initial = bien.id
                self.fields['bien'].widget.attrs['value'] = bien.id

class HdMaterialMantenimientoForm(forms.Form):
    gruposistema = forms.IntegerField(initial=0, required=False, label=u'Grupo Sistema', widget=forms.TextInput(attrs={'select2search': 'true'}))
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicacion", queryset=HdBloqueUbicacion.objects.filter(status=True),required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    bien = forms.IntegerField(initial=0, required=False, label=u'Bien',widget=forms.TextInput(attrs={'select2search': 'true'}))
    tipomantenimiento = forms.ChoiceField(label=u"Tipo Mantenimiento", required=True, choices=TIPO_MANTENIMIENTO,widget=forms.Select(attrs={'class': 'imp-90'}))
    tipobien = forms.ChoiceField(label=u"Tipo Bien", required=True, choices=TIPO_BIEN, widget=forms.Select(attrs={'class': 'imp-90'}))
    proceso = forms.ChoiceField(label=u"Proceso", required=True, choices=PROCESO,widget=forms.Select(attrs={'class': 'imp-90'}))
    ayudantes = forms.ModelMultipleChoiceField(label=u'Técnicos', queryset=HdDetalle_Grupo.objects.all(),required=False)

    def cargarayudantes(self, grupo):
        self.fields['ayudantes'].queryset = HdDetalle_Grupo.objects.filter(grupo=grupo).order_by('persona__apellido1', 'persona__apellido2')

    def editarbien(self, bien):
        self.fields['bien'].widget.attrs['descripcion'] = bien
        self.fields['bien'].initial = bien.id
        self.fields['bien'].widget.attrs['value'] = bien.id

    def editar(self, gruposistema):
        self.fields['gruposistema'].widget.attrs['descripcion'] = gruposistema
        self.fields['gruposistema'].initial = gruposistema.id
        self.fields['gruposistema'].widget.attrs['value'] = gruposistema.id

    def resolver(self):

        deshabilitar_campo(self, 'gruposistema')
        deshabilitar_campo(self, 'ubicacion')
        deshabilitar_campo(self, 'bloque')
        deshabilitar_campo(self, 'bien')



class HdMaterialMantenimiento_MaterialForm(forms.Form):

    # material = forms.CharField(label=u"Material", max_length=250, required=False,widget=forms.Textarea(attrs={'rows': '4', 'with': '100'}))
    material = forms.CharField(label=u"Material", max_length=50, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-100'}))
    unidadmedida = forms.ModelChoiceField(UnidadMedidaPresupuesto.objects.filter(status=True),
                                          label=u'Unidad de medida', required=False,
                                          widget=forms.Select(attrs={'formwidth': '50%'}))
    cantidad = forms.IntegerField(initial=0, label=u'Cantidad', required=False,
                                  widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0','formwidth': '30%'}))
    precio =forms.DecimalField(initial='0.0000', label=u'Precio', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda','formwidth': '30%'}))
    total = forms.DecimalField(initial='0.0000', label=u'Total', required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda','formwidth': '30%'}))




class HdPlanAprobacionForm(forms.Form):
    periodo = forms.ModelChoiceField(AnioEjercicio.objects.filter(status=True).order_by('-anioejercicio'),
                                          label=u'Periodo', required=False,
                                          widget=forms.Select(attrs={'formwidth': '50%'}))
    fecharegistro =forms.DateField(label=u"Fecha Registro", required=True, initial=datetime.now().date(), input_formats=['%d-%m-%Y'],widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha','formwidth': '50%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato  pdf, jpg, png, jpeg', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,widget=forms.FileInput(attrs={'class': 'imp-90','formwidth': '100%'}))
    # estadoaprobacion = forms.ChoiceField(label=u"Estado Aprobación", required=True, choices=ESTADO_APROBACION,widget=forms.Select(attrs={'class': 'imp-90','formwidth': '50%'}))

    observacion = forms.CharField(label=u'Observacion', widget=forms.Textarea(attrs={'rows': '3'}),required=False)
    solicitarevision = forms.BooleanField(initial=True, label=u'Solicitar Revisión', required=False)


    def editar(self, periodo):
        self.fields['periodo'].widget.attrs['descripcion'] = periodo
        self.fields['periodo'].initial = periodo.id
        self.fields['periodo'].widget.attrs['value'] = periodo.id

class HdPlanificacionArchivoForm(forms.Form):
    archivo = ExtFileField(label=u'Documento PDF soporte', required=False,help_text=u'Tamaño máximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))


class HdPresupuestoRecursoForm(forms.Form):
    gruposistema = forms.ModelChoiceField(label=u"Grupo Sistema/Equipo", queryset=HdGrupoSistemaEquipo.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '100%'}))
    bien = forms.ModelChoiceField(label=u"Sistema/Equipo", queryset=HdBien.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '100%'}))
    presupuestoreq =forms.DecimalField(initial='0.0000', label=u'Presupuesto Requerido', required=False, widget=forms.TextInput(attrs={'class': 'imp-90','formwidth': '50%'}))
    presupuestoiva = forms.DecimalField(initial='0.0000', label=u'Presupuesto (+) Iva', required=False, widget=forms.TextInput(attrs={'class': 'imp-90','formwidth': '50%'}))
    presupuestototal = forms.DecimalField(initial='0.0000', label=u'Presupuesto Total', required=False, widget=forms.TextInput(attrs={'class': 'imp-90','formwidth': '50%'}))

    def editarbien(self, bien):
        self.fields['bien'].widget.attrs['descripcion'] = bien
        self.fields['bien'].initial = bien.id
        self.fields['bien'].widget.attrs['value'] = bien.id

    def editar(self, gruposistema):
        self.fields['gruposistema'].widget.attrs['descripcion'] = gruposistema
        self.fields['gruposistema'].initial = gruposistema.id
        self.fields['gruposistema'].widget.attrs['value'] = gruposistema.id


class HdMantenimientosActivosForm(FormModeloBase):
    activotecno = forms.IntegerField(initial=0, required=False, label=u'Bien',widget=forms.TextInput(attrs={'select2search': 'true','class':'form-control','col': '12'}))
    tipoactivo = forms.ModelChoiceField(HdGruposCategoria.objects.filter(status=True), required=True,
                                        label=u'Tipo de Activo', widget=forms.Select(attrs={'class':'form-control','col': '12'}))
    persona = forms.CharField(label=u"Responsable", required=False, widget=forms.TextInput(attrs={'class':'form-control','col': '12','crearboton':True,'classbuton':'addtraspaso'}))
    estusu = forms.BooleanField(label=u'Usuario entrego el equipo', required=False,
                                widget=CheckboxInput(attrs={'class':'form-control','col': '6'}))
    archivo = ExtFileField(label=u'Adjuntar archivo de evidencia de comunicado', required=False,
                           help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=2194304)
    fecha = forms.DateField(label=u"Fecha de mantenimiento", initial=datetime.now().date(), required=False,
                            input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',
                                                                             attrs={'class': 'selectorfecha form-control',
                                                                                    'col': '12'}))
    horamax = forms.CharField(label=u'Hora', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall form-control well', 'decimal': '0', 'col': '4'}))
    minutomax = forms.CharField(label=u'Minutos', required=False, widget=forms.TextInput(
        attrs={'class': 'imp-numbersmall form-control well', 'decimal': '0', 'col': '4'}))
    estfrec = forms.BooleanField(label=u'Funciona al recibir', required=False,
                                 widget=CheckboxInput(attrs={'col': '6'}))
    estfent = forms.BooleanField(label=u'Funciona al entregar', required=False,
                                 widget=CheckboxInput(attrs={'col': '6'}))
    marca = forms.CharField(label=u"Marca", required=False, widget=forms.TextInput(attrs={'col': '6'}))
    modelo = forms.CharField(label=u"Modelo", required=False, widget=forms.TextInput(attrs={'col': '6'}))
    piezaparte = forms.ModelChoiceField(queryset=HdPiezaPartes.objects.filter(status=True).order_by('descripcion'),
                                        required=False, label=u'Pieza y Parte',widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    danioenc = forms.ModelChoiceField(
        queryset=HdMantenimientoGruDanios.objects.filter(status=True).order_by('descripcion'), required=False,
        label=u'Daños encontrados',widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))

    bsugiere = forms.BooleanField(label=u'Se sugiere baja del equipo', required=False,
                                  widget=CheckboxInput(attrs={'col': '6'}))
    dsugiere = forms.CharField(label=u"Sugerencia de baja", required=False,
                               widget=forms.TextInput(attrs={'col': '12'}))
    observacion = forms.CharField(label=u'Observación', required=True, widget=forms.Textarea({'rows': '2','col':'12'}))

    def cargar_mantenimiento(self, mantenimiento):
        # self.fields['piezaparte'].queryset = HdPiezaPartes.objects.filter(id__in=list(mantenimiento.piezaparteactivospreventivos_set.filter(status=True).values_list('piezaparte_id', flat=True)))
        self.fields['piezaparte'].queryset = HdPiezaPartes.objects.filter(status=True,
                                                                          grupocategoria_id=mantenimiento.tipoactivoc,
                                                                          estado=1)

class TipoBienForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", max_length=500, required=True, widget=forms.TextInput({'col': '12'}))

class TareasMantenimientoForm(FormModeloBase):
    tipobien = forms.ModelChoiceField(queryset=HdGruposCategoria.objects.filter(status=True), required=True, label=u'Grupo de activo',widget=forms.Select(attrs={'class':'form-control', 'col': '6'}))
    descripcion = forms.CharField(label=u"Descripción", max_length=500, required=True, widget=forms.TextInput({'col': '6'}))

class HdMantenimientoGruDaniosForm(FormModeloBase):
    tipobien = forms.ModelChoiceField(queryset=HdGruposCategoria.objects.filter(status=True), required=True, label=u'Grupo de activo', widget=forms.Select(attrs={'class': 'form-control', 'col': '6'}))
    descripcion = forms.CharField(label=u"Descripción", max_length=500, required=True, widget=forms.TextInput({'col': '6'}))

class HdPiezaPartesForm(FormModeloBase):
    tipobien = forms.ModelChoiceField(queryset=HdGruposCategoria.objects.filter(status=True), required=True, label=u'Grupo de activo', widget=forms.Select(attrs={'class': 'form-control', 'col': '6'}))
    estado = forms.ChoiceField(choices=ESTADO_PARTES,label=u'Estado',required=True,initial=0,widget=forms.Select(attrs={'col':'6'}))
    descripcion = forms.CharField(label=u"Descripción", max_length=500, required=True, widget=forms.TextInput({'col': '12'}))
    imagen = ExtFileField(label=u'Imagen', required=False,help_text=u'Tamaño Maximo permitido 2Mb, en formato jpg,jpeg,png', ext_whitelist=(".jpg", ".jpeg", ".png"),max_upload_size=2194304, widget=FileInput({'accept': 'application/pdf, image/jpeg, image/jpg, image/png','col':'12'}))

class ResponsableActivoTraspasoForm(FormModeloBase):
    persona = forms.IntegerField(label=u"Responsable a asignar", initial=0, required=True,widget=forms.TextInput(attrs={'select2search': 'true','class':'form-control','col': '12'}))
    responsableactual = forms.CharField(initial=0,label=u'Responsable actual', required=False,
                                     widget=forms.TextInput(attrs={'col':'12','disabled':True}))
    activo = forms.CharField(initial=0,label=u'Activo', required=False, widget=forms.TextInput(attrs={'col':'12','disabled':True}))


# Proceso Solicitud copias
class ConfiguracionCopiaForm(FormModeloBase):
    cantidad = forms.IntegerField(label=u'Cantidad', initial=1, required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'number':'True', 'decimal': '0', 'col':'6',
               'controlwidth':'50%', 'onkeypress': 'return soloNumeros(event)'}))
    tiempo = forms.IntegerField(label=u'Tiempo en minutos', initial=1, required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'number':'True', 'decimal': '0', 'col':'6',
               'controlwidth':'50%', 'onkeypress': 'return soloNumeros(event)'}))

    def validador(self, id=0):
        ban, cantidad, tiempo = True, self.cleaned_data['cantidad'], self.cleaned_data['tiempo']
        if cantidad < 1:
            self.add_error('cantidad', 'Cantidad debe ser mayor a cero.')
        if tiempo < 1:
            self.add_error('tiempo', 'Tiempo debe ser mayor a cero minutos.')
        if ConfiguracionCopia.objects.filter(cantidad=cantidad, tiempo=tiempo, status=True).exclude(id=id).exists():
            self.add_error('cantidad', 'Registro que desea ingresar ya existe.')
            self.add_error('tiempo', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban


class ImpresoraForm(FormModeloBase):
    # ActivoTecnologico.objects.filter(status=True,
    #                                activotecnologico_catalogo_equipoelectronico=True,
    #                                activotecnologico_catalogostatus=True,
    #                                activotecnologico_statusactivo=1,
    #                                activotecnologico_status=True,
    #                                activotecnologicocatalogo_clasificado=True)
    impresora = forms.ModelChoiceField(queryset=ActivoTecnologico.objects.filter(Q(status=True, activotecnologico__statusactivo=1),
                                                                                 Q(Q(tipoactivo__id=4) | Q(grupocategoria__id = 4))
                                                                                ).order_by('activotecnologico__modelo'),
                                       required=True, label=u'Impresora', widget=forms.Select({'col':'12'}))
    configuracioncopia = forms.ModelChoiceField(queryset=ConfiguracionCopia.objects.filter(status=True
                                                                                           ), required=True,
                                                label=u'Velocidad de impresión', widget=forms.Select({'col': '12'}))

    def validador(self, id=0):
        ban, impresora, configuracioncopia = True, self.cleaned_data['impresora'], self.cleaned_data['configuracioncopia']
        if Impresora.objects.filter(impresora=impresora, configuracioncopia=configuracioncopia, status=True).exclude(id=id).exists():
            self.add_error('impresora', 'Registro que desea ingresar ya existe.')
            self.add_error('configuracioncopia', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban


class JornadaImpresoraForm(FormModeloBase):
    dia = forms.ChoiceField(label=u"Día", initial=1, choices=DIAS_CHOICES, required=True,
                               widget=forms.Select({'placeholder': 'Seleccione el día', 'col': '12'}))
    comienza = forms.TimeField(label=u"Comienza (hh:mm)", required=True, initial=str(datetime.now().time().strftime("%Hh:%Mm")),
                               widget=DateTimeInput(format='%Hh:%Mm', attrs={'class': 'selectorhora','col':'6'}))
    termina = forms.TimeField(label=u"Termina (hh:mm)", required=True, initial=str(datetime.now().time().strftime("%H\h:%M\m")),
                              widget=DateTimeInput(format='%Hh:%Mm', attrs={'class': 'selectorhora','col':'6'}))

    def validador(self, id=0):
        ban, dia, comienza, termina = True, self.cleaned_data['dia'], self.cleaned_data['comienza'], self.cleaned_data['termina']
        if comienza > termina:
            self.add_error('termina', 'Campo Termina debe ser mayor al campo Comienza.')
            ban = False
        elif comienza == termina:
                self.add_error('termina', 'Campos Comienza y Termina no deben ser iguales.')
                ban = False
        elif JornadaImpresora.objects.filter(status=True, dia=dia, comienza=comienza,termina=termina).exclude(id=id).exists():
            self.add_error('dia', 'Registro que desea ingresar ya existe.')
            self.add_error('comienza', 'Registro que desea ingresar ya existe.')
            self.add_error('termina', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban


class DetalleJornadaImpresoraForm(FormModeloBase):
    jornadaimpresora = forms.ModelChoiceField(queryset=JornadaImpresora.objects.filter(status=True
                 ), required=True, label=u'Jornada de disponibilidad', widget=forms.Select({'col':'12'}))

    def validador(self, id=0, idpadre=0):
        ban, jornadaimpresora = True, self.cleaned_data['jornadaimpresora']
        if DetalleJornadaImpresora.objects.filter(impresora_id=idpadre, jornadaimpresora=jornadaimpresora, status=True).exclude(id=id).exists():
            self.add_error('jornadaimpresora', 'Registro que desea ingresar ya existe.')
            ban = False

        elif DetalleJornadaImpresora.objects.filter(Q(impresora_id=idpadre, jornadaimpresora__dia=jornadaimpresora.dia) &
                                                    Q(Q(jornadaimpresora__comienza__range=(jornadaimpresora.comienza, jornadaimpresora.termina))
                                                    | Q(jornadaimpresora__termina__range=(jornadaimpresora.comienza, jornadaimpresora.termina) )),
                                                    status=True).exclude(id=id).exists():
            self.add_error('jornadaimpresora', 'Registro que desea ingresar presenta conflicto de horario con las jornadas asignadas.')
            ban = False

        return ban


class SolicitudCopiasForm(FormModeloBase):
    fechaagendada = forms.DateField(label=u"Fecha a agendar",
                                    # initial=datetime.now().date(),
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'col': '9', 'controlwidth': '50%'}), required=True)
    cantidadcopia = forms.IntegerField(
                                        # initial=1,
                                       label=u'Cantidad de copias', required=True,
                                       widget=forms.TextInput(
                                           attrs={'class': 'imp-number', 'number': 'True', 'decimal': '0', 'col': '3',
                                                  'controlwidth': '70%'}))
    horainicio = forms.TimeField(label=u"Hora inicio (hh:mm)", required=True,
                                 # initial=str(datetime.now().time().strftime("%H:%M")),
                               widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'col': '6'}))
    # , initial=str(datetime.now().time().strftime("%H:%M"))
    # horainicio = forms.TimeField(label=u"Hora Fin", required=False,
    #                           initial=(datetime.now() + timedelta(hours=2)).strftime('%H:%M'), input_formats=['%H:%M'],
    #                           widget=DateTimeInput(format='%H:%M', attrs={'readonly': 'true', 'col': '4'}))
    horafin = forms.TimeField(label=u"Hora fin (hh:mm)",
                              required = False, input_formats=['%H:%M'],
                              widget=DateTimeInput(format='%H:%M', attrs={'readonly': 'true', 'col': '6'}))
    # detallejornadaimpresora = forms.ModelChoiceField(label=u"Jornada",
    #                                                  queryset=DetalleJornadaImpresora.objects.select_related().filter(status=True),
    #                                                  required=True, widget=forms.Select(
    #         {'placeholder': 'Seleccione la jornada.', 'col': '12'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2','col':'12'}))

    def validador(self, id=0, profesor=None):
        ban = True
        if not self.cleaned_data['horafin']:
            self.add_error('horafin', 'Debe ingresar los campos fecha a agendar, cantidad de copias y hora de inicio para el cálculo automático del campo hora fin.')
            ban = False

        if self.cleaned_data['cantidadcopia'] < 1:
            self.add_error('cantidadcopia', 'La cantidad de copia debe ser mayor a cero.')
            ban = False

        if self.cleaned_data['fechaagendada'] < datetime.now().date():
            self.add_error('fechaagendada', 'La fecha a agendar debe ser igual o posterior a la fecha actual.')
            ban = False
        else:
            # fecha agendada y hora inicio ingresada en el formulario
            fagendarhorainicio = datetime.strptime(f"{self.cleaned_data['fechaagendada']} {self.cleaned_data['horainicio']}", "%Y-%m-%d %H:%M:%S")
            # eliminar segundos a fecha agendada y hora inicio ingresada en el formulario
            fagendarhorainicio = datetime(fagendarhorainicio.year, fagendarhorainicio.month, fagendarhorainicio.day, fagendarhorainicio.hour, fagendarhorainicio.minute, 0)
            # fecha hora actual con cero segundos
            fechahoraactual = datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour, datetime.now().minute, 0)
            if fagendarhorainicio.date() == fechahoraactual.date() and fagendarhorainicio.time() <= fechahoraactual.time():
                self.add_error('horainicio', 'La hora de inicio debe ser posterior a la hora actual.')
                ban = False

        # Validar que no se repita el registro en la misma fecha agendad e igual a hora de inicio (sólo igual, no mayor)
        fechaagendada, horainicio = self.cleaned_data['fechaagendada'], self.cleaned_data['horainicio']
        if SolicitudCopia.objects.filter(status=True, profesor=profesor, fechaagendada=fechaagendada, horainicio=horainicio).exclude(id=id).exists():
            self.add_error('fechaagendada', 'Registro con la fecha agendada que desea ingresar ya existe.')
            self.add_error('horainicio', 'Registro con la hora inicio que desea ingresar ya existe.')
            ban = False

        return ban

    # validador_calcularhorafin_disponibilidadhorario

    def adicionar(self):
        deshabilitar_campo(self, 'horafin')

    def editar(self):
        deshabilitar_campo(self, 'horafin')

class BodegaKardexForm(forms.Form):
    factura = forms.ModelChoiceField(FacturaCompra.objects.filter(status=True), label=u"Factura", required=True,
                                      widget=forms.Select(attrs={'formwidth': '50%'}))
    producto = forms.ModelChoiceField(BodegaProducto.objects.filter(status=True), label=u"Producto", required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    tipotransaccion = forms.ModelChoiceField(BodegaTipoTransaccion.objects.filter(status=True), label=u'Tipo de Transacción', required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    unidadmedida = forms.ModelChoiceField(BodegaUnidadMedida.objects.filter(status=True), label=u'Unidad de medida', required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    cantidad = forms.IntegerField(label=u'Cantidad', initial=1, required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'number': 'True', 'decimal': '0', 'col': '6',
               'controlwidth': '50%', 'onkeypress': 'return soloNumeros(event)'}))

class BodegaProductoForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", max_length=300, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    grupo = forms.ModelChoiceField(queryset=GruposCategoria.objects.filter(status=True), label="Categoria",
                           widget=forms.Select(attrs={"class": "form-select", 'col': '12', "style": "width: 100%;"}),
                           required=True, )

class BodegaUnidadMedidaForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", max_length=300, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class BodegaProductoDetalleForm(forms.Form):
    unidadmedida = forms.ModelChoiceField(queryset=BodegaUnidadMedida.objects.filter(status=True), label="Medida",
                                      widget=forms.Select(
                                          attrs={"class": "form-select", 'col': '12', "style": "width: 100%;"}),
                                      required=True, )
    valor = forms.IntegerField(label=u'Equivalencia',  required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'number': 'True', 'decimal': '0', 'col': '6', 'autocomplete':'off',
               'controlwidth': '100%', 'onkeypress': 'return soloNumeros(event)'}))


class GruposCategoriaForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", max_length=300, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    identificador = forms.CharField(label=u"Identificador", max_length=300, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class BodegaTipoTransaccionForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripción", max_length=300, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class Factura(forms.Form):
    codigo = forms.CharField(label="Código de factura", max_length=300, widget=forms.TextInput(attrs={"class": "form-control imp-100", 'autocomplete':'off', 'col': '5'}), required=True,)
    fecha = forms.DateField(label="Fecha de compra", widget=forms.DateTimeInput(attrs={"class": "form-control selectorfecha","type": "date", 'col': '5'},format="%d-%m-%Y",),
        required=True,)

    proveedor = forms.ModelChoiceField(queryset=Proveedor.objects.filter(status=True), label="Proveedor", widget=forms.Select(attrs={"class": "form-select",'col': '5', "style": "width: 50%;"}),
        required=True,)
    total = forms.DecimalField(label="Total", initial=0.00, widget=forms.TextInput(
            attrs={
                "class": "form-control imp-number imp-moneda",
                "type": "number",
                'col': '5',
                "readonly": True,
                'decimal': '2', "style": "text-align: left;"
            }
        ),
        required=True,
    )
    detalle = forms.CharField(label="Descripcion de factura", max_length=300, widget=forms.Textarea(attrs={"class": "form-control left", 'col': '5', 'style':'height: 20px;'}), required=True)

    archivo = ExtFileField(label=u'Archivo Factura', required=False,
                           help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                           ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304,
                           widget=forms.FileInput(
                               attrs={"class": "form-control", 'col': '5','formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))

    def adicionar(self):
        deshabilitar_campo(self, 'total')


class DetalleFactura(forms.Form):
    # factura = forms.ModelChoiceField(queryset=FacturaCompra.objects.filter(status=True), label="Factura", widget=forms.Select(attrs={"class": "form-select",'col': '5', "style": "width: 50%;"}),
    #     required=True,)
    producto = forms.ModelChoiceField(queryset=BodegaProducto.objects.filter(status=True), label="Producto",
                                     widget=forms.Select(
                                         attrs={"class": "form-select select2", 'col': '5', "style": "width: 50%;", "idp": "producto-select"}),
                                     required=True, )
    unidadmedida = forms.ModelChoiceField(BodegaProductoDetalle.objects.filter(status=True), label=u'Unidad de medida', required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    cantidad  = forms.IntegerField(label=u'Cantidad',  required=True, widget=forms.TextInput(
        attrs={'class': 'imp-number', 'number': 'True', 'decimal': '0', 'col': '6', 'autocomplete':'off', 'onkeypress': 'return soloNumeros(event)'}))
    costo = forms.DecimalField(label="Costo",  widget=forms.TextInput(
            attrs={
                "class": "form-control imp-number imp-moneda",
                'col': '5',
                'autocomplete': 'off',
                'decimal': '2', "style": "text-align: left;"
            }
        ),required=True,)


    # total = forms.DecimalField(label="Total", widget=forms.TextInput(
    #     attrs={
    #         "class": "form-control imp-number imp-moneda",
    #         'col': '5',
    #         'decimal': '2', "style": "text-align: left;"
    #     }
    # ), required=True, )


class IncidenteForm(FormModeloBase):
    persona = forms.IntegerField(label=u"Solicitante", initial=0, required=False, widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    activo = forms.IntegerField(label=u"Activo Fijo", initial=0, required=False, widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    tipogrupo = forms.ModelChoiceField(label=u"Tipo de grupo", queryset=HdTipoIncidente.objects.filter(status=True, pk=2), required=False, widget=forms.Select(attrs={'col': '6'}))
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=HdBloque.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'col': '6'}))
    ubicacion = forms.ModelChoiceField(label=u"Ubicación", queryset=HdBloqueUbicacion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    incidente = forms.CharField(label=u"Incidente", widget=forms.Textarea(attrs={'rows': '4', 'col': '12'}), required=False)
    fecha = forms.DateField(label=u"Fecha Reporta", required=False, initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    hora = forms.CharField(label=u"Hora Reporta", required=False, initial=datetime.now().time().strftime('%H:%M'), widget=forms.TextInput(attrs={'col': '6', 'type': 'time'}))
    archivo = ExtFileField(label=u'Evidencia', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png', ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304, widget=forms.FileInput(attrs={'col': '6'}))

    def editar(self, incidente):
        self.fields['ubicacion'].queryset = HdBloqueUbicacion.objects.filter(bloque=incidente.ubicacion.bloque, status=True)
