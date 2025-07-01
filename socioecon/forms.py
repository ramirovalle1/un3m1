# -*- coding: latin-1 -*-
import datetime

from django import forms

from sga.models import ParentescoPersona, Persona, Sexo
from sga.forms import ExtFileField
from socioecon.models import FormaTrabajo, TipoHogar, ACTIVIDADES_RECREACION, PersonaCubreGasto, NivelEstudio, \
    OcupacionJefeHogar, TipoViviendaPro, TipoVivienda, MaterialPared, MaterialPiso, CantidadBannoDucha, \
    TipoServicioHigienico, CantidadTVColorHogar, CantidadVehiculoHogar, CantidadCelularHogar, \
    REALIZA_TAREAS, SALUBRIDAD_VIDA, ESTADO_GENERAL, ProveedorServicio, \
    PublicacionDonacion, PoblacionDonacion, TipoDonacion, DetalleProductoPublicacion, Producto, TipoProducto, \
    ContribuidorDonacion, DetalleAprobacionPublicacionDonacion, PUBLICACION_DONACION_PRIORIDAD, PUBLICACION_DONACION_ESTADO, UnidadMedidaDonacion

from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput


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



#SUSTENTO DEL HOGAR FORM
class SustentoHogarForm(forms.Form):
    persona = forms.CharField(max_length=50, label='Persona que sustenta')
    parentesco = forms.ModelChoiceField(ParentescoPersona.objects, label='Parentesco')
    formatrabajo = forms.ModelChoiceField(FormaTrabajo.objects, label='Formas de Trabajo')
    ingresomensual = forms.FloatField(label='Ingreso Mensual')


class TipoHogarForm(forms.Form):
    tipohogar = forms.ModelChoiceField(TipoHogar.objects, label='Tipos de Hogar')


class PersonaCubreGastoForm(forms.Form):
    personacubregasto = forms.ModelChoiceField(PersonaCubreGasto.objects, label='Quien cubre los gastos')
    otroscubregasto = forms.CharField(label='Especifique OTROS', required=False)


class PersonaActRecreacionForm(forms.Form):
    tipoactividad = forms.ChoiceField(label=u'Tipo Actividad', choices=ACTIVIDADES_RECREACION, widget=forms.Select(attrs={'class': 'imp-50'}))
    otrosactividad = forms.CharField(label='Especifique OTROS', required=False)


class PersonaLugarTareaForm(forms.Form):
    tipotarea = forms.ChoiceField(label=u'Lugar', choices=REALIZA_TAREAS, widget=forms.Select(attrs={'class': 'imp-50'}))
    otrostarea = forms.CharField(label='Especifique OTROS', required=False)


class PersonaSalubridadVidaForm(forms.Form):
    salubridadvida = forms.ChoiceField(label=u'Condiciones de vida', choices=SALUBRIDAD_VIDA, widget=forms.Select(attrs={'class': 'imp-50'}))


class PersonaEstadoGeneralForm(forms.Form):
    estadogeneral = forms.ChoiceField(label=u'Estado General', choices=ESTADO_GENERAL, widget=forms.Select(attrs={'class': 'imp-50'}))


class NivelEstudioForm(forms.Form):
    niveljefehogar = forms.ModelChoiceField(NivelEstudio.objects, label='Nivel de Esudios')


class OcupacionJefeHogarForm(forms.Form):
    ocupacionjefehogar = forms.ModelChoiceField(OcupacionJefeHogar.objects, label='Ocupacion')


class TipoViviendaForm(forms.Form):
    tipovivienda = forms.ModelChoiceField(TipoVivienda.objects, label='Tipo de Vivienda')


class TipoViviendaproForm(forms.Form):
    tipoviviendapro = forms.ModelChoiceField(TipoViviendaPro.objects, label='Tipo de Vivienda Propia')


class MaterialParedForm(forms.Form):
    materialpared = forms.ModelChoiceField(MaterialPared.objects, label='Material de Paredes')


class MaterialPisoForm(forms.Form):
    materialpiso = forms.ModelChoiceField(MaterialPiso.objects, label='Material de Piso')


class CantidadBannoDuchaForm(forms.Form):
    cantbannoducha = forms.ModelChoiceField(CantidadBannoDucha.objects, label=u'Baños con ducha')


class TipoServicioHigienicoForm(forms.Form):
    tiposervhig = forms.ModelChoiceField(TipoServicioHigienico.objects, label='Servicio Higienico')


class CantidadTVColorHogarForm(forms.Form):
    canttvcolor = forms.ModelChoiceField(CantidadTVColorHogar.objects, label='Cantidad TV a color')


class CantidadVehiculoHogarForm(forms.Form):
    cantvehiculos = forms.ModelChoiceField(CantidadVehiculoHogar.objects, label='Cantidad Vehiculos')


class CantidadCelularHogarForm(forms.Form):
    cantcelulares = forms.ModelChoiceField(CantidadCelularHogar.objects, label='Cantidad Celulares')


class ProveedorInternetForm(forms.Form):
    proveedorinternet = forms.ModelChoiceField(label=u"Proveedor de Internet", queryset=ProveedorServicio.objects.filter(status=True, tiposervicio=1).order_by('nombre'), required=False, widget=forms.Select(attrs={'formwidth': '100%', 'fieldbuttons': [{'id': 'add_proveedor_internet', 'tooltiptext': 'Agregar Nuevo Proveedor', 'btnclasscolor': 'btn-success','btnfaicon': 'fa-plus-square'}]  }))


class AgregarProveedorInternet(forms.Form):
    nombreproveedor = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'rows': '1'}), required=False)

#DONACIONES
class PublicacionDonacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre de donación', widget=forms.TextInput(attrs={'readonly': False, 'class': 'form-control', 'col': '12'}), required=False)
    objetivo = forms.CharField(label=u'Objetivo', widget=forms.Textarea(attrs={'readonly':False, 'class': 'form-control', 'rows': '4', 'placeholder':'Explique brevemente el objetivo de su solicitud...', 'col': '12'}), required=False)
    poblacion = forms.ModelMultipleChoiceField(label=u"Población", queryset=PoblacionDonacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.SelectMultiple(attrs={'disabled': False, 'class': 'form-control', 'col': '12'}))
    tipodonacion = forms.ModelChoiceField(label=u"Tipo de donación", queryset=TipoDonacion.objects.filter(status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'disabled': False, 'class': 'form-control', 'col': '12'}))
    mostrarfotoperfil = forms.BooleanField(label=u'¿Mostrar mi foto de perfil en la publicación?', required=False, widget=forms.CheckboxInput(attrs={'readonly': False, 'class': 'js-switch', 'col': '12'}))
    fechainiciorecepcion = forms.DateField(label=u"Inicio recepción", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'autocomplete':'off', 'col': '6'}))
    fechafinrecepcion = forms.DateField(label=u"Fin recepción", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha form-control', 'autocomplete':'off', 'col': '6'}))
    fechainicioentrega = forms.DateField(label=u"Inicio entrega", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'disabled': False, 'class': 'selectorfecha form-control', 'autocomplete':'off', 'col': '6'}))
    fechafinentrega = forms.DateField(label=u"Fin entrega", required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'disabled': False, 'class': 'selectorfecha form-control', 'autocomplete':'off', 'col': '6'}))
    evidencianecesidad = ExtFileField(label=u'Evidencia de necesidad', required=False,help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,widget=FileInput({'class':'form-control', 'col': '12', 'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))
    evidenciaejecucion = ExtFileField(label=u'Evidencia de ejecución', required=False,help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png"), max_upload_size=4194304,widget=FileInput({'class':'form-control', 'col': '12', 'accept': 'application/pdf, image/jpeg, image/jpg, image/png'}))
    # producto = forms.ModelMultipleChoiceField(label=u"Producto", queryset=Producto.objects.filter(status=True).order_by('-id'),required=False, widget=forms.SelectMultiple(attrs={'separator2': 'true', 'separatortitle':'<i id="btn_table_collapse" class="fa fa-angle-down"></i>&nbsp;Agregar productos', 'col': '12', 'fieldbuttons': [{'id': 'btn_adicionar_producto','tooltiptext': 'Agregar nuevo producto','btnclasscolor': 'btn-success','btnfaicon': 'fa-plus-circle'}]}))

    def es_agregar(self):
        del self.fields['evidenciaejecucion']

    def editar_aprobado(self):
        self.fields['nombre'].widget.attrs['readonly'] = "readonly"
        self.fields['objetivo'].widget.attrs['readonly'] = "readonly"
        self.fields['poblacion'].widget.attrs['disabled'] = "disabled"
        self.fields['tipodonacion'].widget.attrs['disabled'] = "disabled"
        self.fields['mostrarfotoperfil'].widget.attrs['readonly'] = "readonly"
        self.fields['fechainicioentrega'].widget.attrs['disabled'] = "disabled"
        self.fields['fechafinentrega'].widget.attrs['disabled'] = "disabled"
        #del self.fields['producto']


class TipoDonacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre:', widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

class TipoProductoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción:', widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

class PoblacionDonacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre:', widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

class ProductoForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción:', widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    tipoproducto = forms.ModelChoiceField(label=u"Tipo de producto", queryset=TipoProducto.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select(attrs={'class': 'span12'}))

class DetalleProductoPublicacionForm(forms.Form):
    producto = forms.ModelChoiceField(label=u"Producto", queryset=Producto.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select(attrs={'class': 'span12', 'v-model': 'producto'}))
    cantidad = forms.IntegerField(initial="", label=u'Cantidad', required=True, widget=forms.TextInput(attrs={'class': 'imp-number span12', 'decimal': '0', 'onKeyPress': "return soloNumeros(event)", 'v-model':'cantidadproducto'}))
    unidadmedida = forms.ModelChoiceField(label=u"Unidad de medida", queryset=UnidadMedidaDonacion.objects.filter(status=True).order_by('-id'), required=False, widget=forms.Select(attrs={'class': 'span12', 'v-model':'unidadmedida'}))

class DetalleAprobacionPublicacionDonacionForm(forms.Form):
    estadoprioridad = forms.ChoiceField(label=u'Prioridad', initial=3,  choices=PUBLICACION_DONACION_PRIORIDAD,widget=forms.Select(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    estado = forms.ChoiceField(label=u'Estado', initial=2, choices=((2, 'APROBADO'),(3, 'RECHAZADO')), widget=forms.Select(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'formwidth': '100%', 'class': 'form-control', 'rows': '3', 'placeholder': 'Detalle brevemente la observación de la solicitud.'}), required=False)

class UnidadMedidaDonacionForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    abreviatura = forms.CharField(label=u'Abreviatura', widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)


TIPO_DONANTE = ((1, 'Persona natural'), (1, 'Persona jurídica'))


class ContribuidorDonacionForm(forms.Form):
    tipodonante = forms.ChoiceField(label=u'Tipo de donante',  choices=TIPO_DONANTE,widget=forms.Select(attrs={'class': 'imp-100 select2', 'formwidth': '100%'}))
    esanonimo = forms.BooleanField(label=u'¿Permanecer anónimo?', required=False, widget=forms.CheckboxInput(attrs={'readonly': False, 'formwidth': '100%', 'class': 'js-switch'}))
    cedula = forms.CharField(label=u'Cedula', max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'decimal': '0', 'onKeyPress': "return soloNumeros(event)", 'maxlength':'10', 'autocomplete':'off'}))
    pasaporte = forms.CharField(label=u'Pasaporte', max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '15'}))
    nombre1 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control span12', 'placeholder':'Primer nombre'}))
    nombre2 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control span12', 'placeholder':'Segundo nombre'}))
    apellido1 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control span12', 'placeholder':'Apellido paterno'}))
    apellido2 = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control span12', 'placeholder':'Apellido materno'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", required=False, queryset=Sexo.objects.all(), widget=forms.Select(attrs={'class': 'form-select span12', "style":"width: 100%"}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False,widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'example@domain.com', 'type':'email'}))
    ruc = forms.CharField(label=u'RUC', max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'decimal': '0', 'onKeyPress': "return soloNumeros(event)"}))
    razonsocial = forms.CharField(label=u"Razón social", required=False, widget=forms.TextInput(attrs={'class': 'form-control span12'}))

    def es_pnatural(self):
        del self.fields['ruc']
        del self.fields['razonsocial']

    def es_pjuridica(self):
        del self.fields['cedula']
        del self.fields['nombre1']
        del self.fields['nombre2']
        del self.fields['apellido1']
        del self.fields['apellido2']




