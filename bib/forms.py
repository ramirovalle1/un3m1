# -*- coding: latin-1 -*-

from django import forms
from django.db.models import Q
from django.forms import DateTimeInput
from django.forms.models import ModelForm
from bib.models import TipoDocumento, Idioma, DocumentoColeccion, TipoIngreso, AreaConocimiento, NivelLibro, \
    EstadoIntegridad
from settings import DOCUMENTOS_COLECCION
from sga.forms import ExtFileField, CheckboxSelectMultipleCustom
from sga.models import Persona, Sede, Carrera


class FixedForm(ModelForm):

    date_fields = []

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        for f in self.date_fields:
            self.fields[f].widget.format = '%d-%m-%Y'
            self.fields[f].input_formats = ['%d-%m-%Y']


class DocumentoForm(forms.Form):
    codigo = forms.CharField(label=u'Código Interno', required=False, max_length=20, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    codigoisbnissn = forms.CharField(label=u'Código (ISBN/ISSN)', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    codigodewey = forms.CharField(label=u'Código DEWEY', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    codigocutter = forms.CharField(label=u'Código CUTTER', max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'imp-25'}))
    tipo = forms.ModelChoiceField(label=u'Tipo de Documento', queryset=TipoDocumento.objects, widget=forms.Select(attrs={'class': 'imp-50'}))
    tipoingreso = forms.ModelChoiceField(label=u'Tipo de Ingreso', required=False, queryset=TipoIngreso.objects, widget=forms.Select(attrs={'class': 'imp-50'}))
    donadopor = forms.CharField(label=u'Donado por', required=False, max_length=300, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    nivel = forms.ModelChoiceField(label=u'Nivel de Libro', required=False, queryset=NivelLibro.objects, widget=forms.Select(attrs={'class': 'imp-50'}))
    estado = forms.ModelChoiceField(label=u'Estado de Integridad', required=False, queryset=EstadoIntegridad.objects, widget=forms.Select(attrs={'class': 'imp-50'}))
    areaconocimiento = forms.ModelChoiceField(label=u'Area de conocimiento', required=False, queryset=AreaConocimiento.objects, widget=forms.Select(attrs={'class': 'imp-75'}))
    fecha = forms.DateField(label=u'Fecha ingreso', input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    numerofactura = forms.IntegerField(label=u'Numero de Factura', required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    tutor = forms.CharField(label=u'Tutor tésis', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    nombre = forms.CharField(label=u'Título', max_length=400)
    nombre2 = forms.CharField(label=u'Título 2', max_length=400, required=False)
    ubicacionfisica = forms.CharField(label=u'Ubicación física', max_length=40, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    percha = forms.CharField(label=u'Percha', required=False, max_length=40, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    hilera = forms.CharField(label=u'Hilera', required=False, max_length=40, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    autor = forms.CharField(label=u'Autor(es)', max_length=200, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    autorcorporativo = forms.CharField(label=u'Autor corporativo', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    anno = forms.IntegerField(label=u'Año de publicacion', initial=1980, widget=forms.TextInput(attrs={'class': 'imp-10'}))
    emision = forms.CharField(label=u'Emisión', max_length=40, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    edicion = forms.CharField(label=u'Edición', max_length=40, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    editora = forms.CharField(label=u'Editora', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    volumen = forms.CharField(label=u'Volumen', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    tomo = forms.CharField(label=u'Tomo', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    lugarpublicacion = forms.CharField(label=u'Lugar de publicación', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    sede = forms.ModelChoiceField(label=u'Sede/Extensión', queryset=Sede.objects, widget=forms.Select(attrs={'class': 'imp-50'}))
    idioma = forms.ModelChoiceField(label=u'Idioma', queryset=Idioma.objects, widget=forms.Select(attrs={'class': 'imp-25'}))
    establecimientoresponsable = forms.CharField(label=u'Establecimiento responsable', max_length=200, required=False)
    descripcionfisica = forms.CharField(label=u'Descripción física', max_length=200, required=False)
    paginas = forms.IntegerField(label=u'No. páginas', initial=0, widget=forms.TextInput(attrs={'class': 'imp-10'}))
    copias = forms.IntegerField(label=u'Cantidad de ejemplares', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-10'}))
    prestamosala = forms.BooleanField(label=u'Prestamo solo en sala', required=False)
    preciocosto = forms.FloatField(label=u'Costo', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    digital = ExtFileField(label=u'Archivo digital', help_text=u'Tamano Maximo permitido 20Mb, en formato doc, docx, xls, xlsx, pdf, zip, rar', ext_whitelist=(".doc", ".docx", ".xls", ".xlsx", ".pdf", ".zip", ".rar"), max_upload_size=20971520, required=False)
    portada = ExtFileField(label=u'Imagen de portada', help_text=u'Tamano Maximo permitido 1Mb, en formato jpg, png', ext_whitelist=(".png", ".jpg"), max_upload_size=1048576, required=False)
    indice = ExtFileField(label=u'Imagen de indice', help_text=u'Tamano Maximo permitido 5Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=5242880, required=False)
    referencia = forms.BooleanField(label=u'Documento referencia', required=False)
    carrera = forms.ModelMultipleChoiceField(label=u'Carreras', queryset=Carrera.objects.all(), required=False)
    palabrasclaves = forms.CharField(label=u'Palabras claves', widget=forms.Textarea)
    resumen = forms.CharField(label=u'Resumen', widget=forms.Textarea, required=False)

    def es_coleccion(self):
        del self.fields['copias']

    def es_fisico(self):
        del self.fields['digital']

    def es_autonumerico(self):
        del self.fields['codigo']

    def editar_digital(self):
        del self.fields['digital']
        del self.fields['prestamosala']
        del self.fields['copias']
        del self.fields['descripcionfisica']
        del self.fields['ubicacionfisica']

    def editar_fisico(self):
        del self.fields['digital']
        if DOCUMENTOS_COLECCION:
            del self.fields['copias']


class PrestamoDocumentoForm(forms.Form):
    nombre = forms.CharField(label=u'Persona que solicita', max_length=400, widget=forms.TextInput(attrs={'class': 'imp-75', 'autocomplete': 'off'}))
    ejemplar = forms.ModelChoiceField(label=u'Ejemplar', required=False, queryset=DocumentoColeccion.objects, widget=forms.Select(attrs={'class': 'imp-25'}))
    tiempo = forms.IntegerField(label=u'Tiempo (Horas)', initial=24, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    prestamosala = forms.BooleanField(label=u'Préstamo en sala', required=False)
    retroactivo = forms.BooleanField(label=u'Préstamo retroactivo', required=False)

    def en_coleccion(self, documento):
        if DOCUMENTOS_COLECCION:
            prestados = [x.documentocoleccion.id for x in documento.prestamodocumento_set.filter(recibido=False)]
            self.fields['ejemplar'].queryset = documento.documentocoleccion_set.filter(habilitado=True).exclude(id__in=prestados)
        else:
            del self.fields['ejemplar']


class PrestamoDocumentoReservaForm(forms.Form):
    persona = forms.ModelChoiceField(label=u'Persona', required=False, queryset=Persona.objects.exclude(Q(perfilusuario__empleador__isnull=False) | Q(perfilusuario__externo__isnull=False)).distinct(), widget=forms.Select(attrs={'class': 'imp-100'}))
    ejemplar = forms.ModelChoiceField(label=u'Ejemplar', required=False, queryset=DocumentoColeccion.objects, widget=forms.Select(attrs={'class': 'imp-25'}))
    tiempo = forms.IntegerField(label=u'Tiempo (Horas)', initial=24, widget=forms.TextInput(attrs={'class': 'imp-number'}))
    prestamosala = forms.BooleanField(label=u'Prestamo en sala', required=False)
    retroactivo = forms.BooleanField(label=u'Préstamo retroactivo', required=False)

    def en_coleccion(self, documento):
        if DOCUMENTOS_COLECCION:
            prestados = [x.documentocoleccion.id for x in documento.prestamodocumento_set.filter(recibido=False)]
            self.fields['ejemplar'].queryset = documento.documentocoleccion_set.filter(habilitado=True).exclude(id__in=prestados)
        else:
            del self.fields['ejemplar']

    def solicita(self, persona):
        self.fields['persona'].queryset = Persona.objects.filter(id=persona.id)
        self.fields['persona'].widget.attrs['readonly'] = True
        self.fields['persona'].widget.attrs['disabled'] = True


class AdicionarDocumentoForm(forms.Form):
    codigo = forms.CharField(label=u'Código Interno', required=False, max_length=20, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    estado = forms.ModelChoiceField(queryset=EstadoIntegridad.objects, label=u'Estado integridad', widget=forms.Select(attrs={'class': 'imp-75'}))

    def editar(self):
        del self.fields['codigo']