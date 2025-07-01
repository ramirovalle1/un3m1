from api.forms.my_form import MY_Form
from django import forms
from django.forms import ValidationError
from posgrado.models import TipoSolicitudBalcon, SolicitudBalcon, AdjuntoSolicitudBalcon
from sga.models import MateriaAsignada
from sga.templatetags.sga_extras import encrypt


class SolicitudBalconPosgradoForm(MY_Form):
    tipo_solicitud = forms.ModelChoiceField(required=True, queryset=TipoSolicitudBalcon.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el tipo de solicitud (requerido)'})
    titulo = forms.CharField(label=u'Título de la solicitud', widget=forms.TextInput(), required=True, error_messages={'required': 'Ingrese un título (requerido)'})
    detalle = forms.CharField(label=u'Detalle de la solicitud', widget=forms.Textarea(), required=True, error_messages={'required': 'Ingrese un detalle (requerido)'})
    # materia_asignada = forms.ModelChoiceField(required=False, queryset=MateriaAsignada.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione una materia (requerido)'})

    def initQuerySet(self, data):
        tipo_solicitud = data.get('tipo_solicitud', '0')
        if tipo_solicitud != '' and tipo_solicitud != '0' and tipo_solicitud != 'undefined' and tipo_solicitud != 'null':
            tipo_solicitud = int(tipo_solicitud)
            self.fields['tipo_solicitud'].queryset = TipoSolicitudBalcon.objects.filter(pk=tipo_solicitud)
            self.fields['tipo_solicitud'].initial = [tipo_solicitud]
        # id_materia = data.get('materia_asignada', '0')
        # if id_materia != '' and id_materia != '0' and id_materia != 'undefined' and id_materia != 'null':
        #     id_materia = int(encrypt(id_materia))
        #     self.fields['materia_asignada'].queryset = MateriaAsignada.objects.filter(pk=id_materia)
        #     self.fields['materia_asignada'].initial = [id_materia]


    def clean(self):
        cleaned_data = super(SolicitudBalconPosgradoForm, self).clean()
        titulo = cleaned_data.get('titulo', None)
        detalle = cleaned_data.get('detalle', None)
        if not titulo or titulo == '':
            self.add_error('titulo', ValidationError(u'Título, ingrese un título (requerido)'))
        if not detalle or detalle == '':
            self.add_error('detalle', ValidationError(u'Detalle, ingrese un detalle (requerido)'))
        return cleaned_data

class AdjuntoSolicitudBalconForm(MY_Form):
    # solicitud = forms.ModelChoiceField(required=True, queryset=SolicitudBalcon.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione una solicitud (requerido)'})
    archivo = forms.FileField(label=u'Adjunto', widget=forms.FileInput(), required=True, error_messages={'required': 'Seleccione un archivo (requerido)'})

    def initQuerySet(self, id_solicitud):
        # if id_solicitud:
        #     id_solicitud_ = int(id_solicitud)
        #     self.fields['solicitud'].queryset = SolicitudBalcon.objects.filter(pk=id_solicitud_)
        #     self.fields['solicitud'].initial = [id_solicitud_]
        pass

    def clean(self):
        cleaned_data = super(AdjuntoSolicitudBalconForm, self).clean()
        archivos = self.files.getlist('archivo')
        # if not archivos:
        #     self.add_error('archivo', ValidationError(u'Archivo, seleccione un archivo (requerido)'))
        for archivo in archivos:
            size = archivo.size
            filename = archivo.name
            ext = filename.split('.')[-1]
            ext = ext.lower()
            if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                self.add_error('archivo', ValidationError(u'Archivo, tipo de documento no permitido'))
            if size > 5242880:
                self.add_error('archivo', ValidationError(u'Archivo, tamaño máximo permitido 5MB'))
        return cleaned_data


