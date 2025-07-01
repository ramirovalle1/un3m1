from datetime import timedelta, datetime

from django import forms
from django.db.models import Q
from django.forms import DateTimeInput

from core.custom_forms import FormModeloBase
from unidecode import unidecode

from directivo.models import (MotivoSancion, IncidenciaSancion, PuntoControl, FaltaDisciplinaria,
                              RequisitoSancion, RequisitoMotivoSancion, ResponsableFirma)

from directivo.utils.strings import Strings
from sagest.funciones import choice_indice
from sagest.models import RegimenLaboral, TipoAccionPersonal, MotivoAccionPersonal, DenominacionPuesto, Departamento, \
    TIPO_PROCESO_TH
from sga.funciones import generar_nombre
from sga.models import Persona
from core.choices.models.sagest import (ESTADO_DESICION_AUDIENCIA, TIPO_REQUISITO,
                                        TIPO_DOCUMENTOS, ROL_FIRMA_DOCUMENTO, PUNTO_CONTROL,NOMBRE_FALTA_DISCIPLINARIA, NIVEL_GESTION)


class IncidenciaSancionForm(FormModeloBase):
    falta = forms.ModelChoiceField(label=u'Tipo de falta',
                                           queryset=FaltaDisciplinaria.objects.filter(status=True),
                                           required=True, widget=forms.Select({'col': '4', 'class': 'select2', 'icon': 'bi bi-ui-radios-grid'}))
    motivoprincipal = forms.ModelChoiceField(label=u'Clasificación',
                                    queryset=MotivoSancion.objects.filter(status=True, principal=True),
                                    required=True, widget=forms.Select({'col': '4', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))
    motivo = forms.ModelChoiceField(label=u'Sub clasificación',
                                    queryset=MotivoSancion.objects.filter(status=True, principal=False),
                                    required=True, widget=forms.Select({'col': '4', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))
    observacion = forms.CharField(label=u'Observación', max_length=300,
                                  required=False, widget=forms.Textarea({'col': '12', 'rows': 3, 'icon': 'bi bi-chat-left-text'}))

    def clean(self):
        cleaned_data = super().clean()
        codigo = cleaned_data.get('codigo')
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        incidencia = IncidenciaSancion.objects.filter(codigo__unaccent__iexact=codigo, status=True).exclude(id=id)
        if incidencia.exists():
            raise self.add_error('codigo', f'Ya existe una incidencia con el código {codigo}')
        return cleaned_data

class ValidarCasoForm(FormModeloBase):
    ESTADO_INCIDENCIA = ((3, 'Caso procedente'),(4, 'Archivado (No procedente)'))
    from directivo.models import FaltaDisciplinaria
    idincidencia = forms.CharField(widget=forms.HiddenInput())
    estado = forms.ChoiceField(label="Estado", choices=ESTADO_INCIDENCIA,required=True,
                              widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-filter'}))
    falta = forms.ModelChoiceField(label="Tipo de falta",
                                   queryset=FaltaDisciplinaria.objects.filter(status=True), required=True,
                           widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-filter'}))
    observacion = forms.CharField(max_length=300, label=u"Observación", required=True,
                                  widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text'}))
    motivoprincipal = forms.ModelChoiceField(label=u'Clasificación',
                                             queryset=MotivoSancion.objects.filter(status=True, principal=True),
                                             required=False, widget=forms.Select({'col': '6', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))
    motivo = forms.ModelChoiceField(label=u'Sub clasificación',
                                    queryset=MotivoSancion.objects.filter(status=True, principal=False),
                                    required=False, widget=forms.Select({'col': '6', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))
    archivo = forms.FileField(label=u'Seleccione Archivo',
                              help_text=u'Tamaño máximo permitido 4Mb, en formato pdf',required=False,
                              widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf',
                                                            'icon': 'bi bi-file-earmark-text'}))


class GenerarDocumentoForm(FormModeloBase):
    idincidencia = forms.CharField(widget=forms.HiddenInput(), required=False)
    persona_recepta = forms.ModelChoiceField(label="Para", queryset=Persona.objects.filter(status=True).order_by('apellido1'), required=True
                                                ,widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-people', 'api':'true'}))
    objeto = forms.CharField(max_length=4000, label=u"Objeto", required=True,
                                  widget=forms.Textarea({'rows': '3', 'col': '12',
                                                        'tooltip': Strings.tooltipObjetoForm,
                                                         'icon': 'bi bi-chat-right-text'}))
    antecedentes = forms.CharField(max_length=4000, label=u"Antecedentes", required=True,
                                  widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text',
                                                         'tooltip': Strings.tooltipAntecedentesForm,
                                                         'class':'ckeditors', 'ckeditor-text': '',
                                                         'editor-sm':'true'}))
    motivacion = forms.CharField(max_length=4000, label=u"Motivación técnica", required=True,
                                  widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text',
                                                         'class':'ckeditors', 'tooltip': Strings.tooltipMotivacionTecnicaForm, 'editor-sm':'true'}))
    conclusion = forms.CharField(max_length=4000, label=u"Conclusión", required=True,
                                   widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text',
                                                          'class':'ckeditors', 'ckeditor-text': Strings.ckeditorConclusionesForm,
                                                          'tooltip': Strings.tooltipConclusionesForm, 'editor-sm':'true'}))
    recomendacion = forms.CharField(max_length=4000, label=u"Recomendacion", required=True,
                                   widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text',
                                                          'class':'ckeditors', 'ckeditor-text': Strings.ckeditorRecomendacionesForm,
                                                          'tooltip': Strings.tooltipRecomendacionesForm, 'editor-sm':'true'}))


class GenerarActaReunionForm(FormModeloBase):
    from sagest.models import Bloque, Ubicacion
    idincidencia = forms.CharField(widget=forms.HiddenInput(), required=False)
    convocador = forms.ModelChoiceField(label=u"Convocado por",
                                      queryset=Persona.objects.filter(status=True).order_by('apellido1'), required=True,
                                      widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-people', 'api': 'true'}))
    organizador = forms.ModelChoiceField(label=u"Organizado por",
                                       queryset=Persona.objects.filter(status=True).order_by('apellido1'),
                                       required=True, widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-people', 'api': 'true'}))
    apuntador = forms.ModelChoiceField(label=u"Apuntador",
                                         queryset=Persona.objects.filter(status=True).order_by('apellido1'),
                                         required=True, widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-people', 'api': 'true'}))
    fecha = forms.DateField(label="Fecha", required=True, initial=datetime.now().date(),
                            widget=forms.DateInput(attrs={'col': '2', 'icon': 'bi bi-calendar-week'}))
    horainicio = forms.TimeField(label="Inicio", required=True,
                                 widget=forms.TimeInput(attrs={'col': '2', 'icon': 'bi bi-clock'}))
    horafin = forms.TimeField(label="Fin", required=True,
                              widget=forms.TimeInput(attrs={'col': '2', 'icon': 'bi bi-clock'}))
    bloque = forms.ModelChoiceField(label="Bloque", required=True,
                                    queryset=Bloque.objects.filter(status=True), widget=forms.Select(
                                    attrs={'col': '3', 'class': 'select2', 'icon': 'bi bi-bank', 'api': 'true'}))
    ubicacion = forms.ModelChoiceField(label="Ubicación", queryset=Ubicacion.objects.filter(status=True),
                                       required=False, widget=forms.Select(
                                        attrs={'col': '3', 'class': 'select2', 'icon': 'bi bi-geo-alt'}))
    referencia = forms.CharField(max_length=100, label=u"Referencia del lugar de audiencia",
                                 required=False, widget=forms.TextInput(
                                    {'col': '6', 'icon': 'bi bi-geo-alt', 'placeholder': 'Describa una referencia o nombre de lugar'}))
    tema = forms.CharField(max_length=100, label=u"Tema de la reunión", required=True,
                            widget=forms.TextInput({'col': '12', 'icon': 'bi bi-chat-right-text'}))
    desarrollo = forms.CharField(max_length=4000, label=u"Desarrollo de la reunión", required=True,
                                 widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text',
                                                        'class': 'ckeditors', 'editor-sm': 'true'}))

    conclusion = forms.CharField(max_length=4000, label=u"Conclusiones", required=True,
                                   widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text',
                                                          'class':'ckeditors', 'editor-sm':'true'}))


class ValidarPruebaForm(FormModeloBase):
    from core.choices.models.sagest import ESTADO_PRUEBA_DESCARGO
    estado = forms.ChoiceField(label="Estado", choices=ESTADO_PRUEBA_DESCARGO[1:],required=True,
                              widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-filter'}))
    observacion = forms.CharField(max_length=300, label=u"Observación", required=True,
                                  widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text'}))

class RespuestaDescargoForm(FormModeloBase):
    descripcion = forms.CharField(max_length=100, label=u"Respuesta", required=True,
                                  widget=forms.TextInput({'col': '12', 'icon': 'bi bi-chat-right-text'}))
    archivo = forms.FileField(label=u'Seleccione Archivo', required=True,
                              help_text=u'Tamaño máximo permitido 5Mb, en formato pdf',
                              widget=forms.FileInput(attrs={'col': '12' ,'accept': '.png, .jpg, .jpeg, .pdf, .xls', 'icon': 'bi bi-file-earmark-text'}))
    def clean(self):
        from directivo.models import RespuestaDescargo
        cleaned_data = super().clean()
        descripcion = cleaned_data.get('descripcion')
        archivo = cleaned_data.get('archivo')
        instancia = self.instancia
        id = getattr(instancia, 'id', 0)
        if RespuestaDescargo.objects.filter(descripcion__unaccent__iexact=descripcion, status=True).exclude(id=id):
            self.add_error('descripcion', 'Registro con esta descripción que intenta guardar ya existe.')
        if archivo:
            max_tamano = 5 * 1024 * 1024  # 5 MB
            name_ = archivo._name
            ext = name_[name_.rfind("."):]
            if not ext.lower() in ['.png', '.jpg', '.jpeg', '.pdf']:
                self.add_error('archivo', f'Solo se permite formato .png, .jpg, .jpeg, .pdf')

            if archivo.size > max_tamano:
                self.add_error('archivo', f'Archivo supera los 5 megas permitidos')
            # Asignar un nombre personalizado al archivo
            idpersona = instancia.personasancion.id if instancia else ''
            name_archive = unidecode(descripcion[:8])
            archivo._name = generar_nombre(f"{idpersona}_{name_archive}", archivo._name)
        elif instancia:
            archivo = instancia.archivo
        cleaned_data['archivo'] = archivo
        return cleaned_data


class PlanificarAudienciaForm(FormModeloBase):
    from sagest.models import Bloque, Ubicacion
    id_incidencia = forms.IntegerField(label="id_incidencia", widget=forms.HiddenInput(), required=False)
    descripcion = forms.CharField(max_length=100, label=u"Descripción de la audiencia", required=True,
                                  widget=forms.TextInput({'col': '12', 'icon': 'bi bi-chat-text', 'placeholder':'Describa el motivo de la audiencia'}))
    fecha = forms.DateField(label="Fecha",required=True,
                               widget=forms.DateInput(attrs={'col': '4', 'icon': 'bi bi-calendar-week'}))
    horainicio = forms.TimeField(label="Hora de inicio",required=True, widget=forms.TimeInput(attrs={'col': '4', 'icon': 'bi bi-clock'}))
    horafin = forms.TimeField(label="Hora de fin",required=True, widget=forms.TimeInput(attrs={'col': '4', 'icon': 'bi bi-clock'}))
    bloque = forms.ModelChoiceField(label="Bloque", required=True, initial=13,
                                    queryset=Bloque.objects.filter(status=True), widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-bank', 'api': 'true'}))
    ubicacion = forms.ModelChoiceField(label="Ubicación", queryset=Ubicacion.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-geo-alt'}))
    referencia = forms.CharField(max_length=100, label=u"Referencia del lugar de audiencia", initial='Segundo piso (Consultorio Jurídico)', required=False, widget=forms.TextInput({'col': '12', 'icon': 'bi bi-geo-alt', 'placeholder':'Describa una referencia o nombre de lugar'}))
    notificar = forms.BooleanField(label="Notificar a los involucrados", required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'icon': 'bi bi-bell', 'data-switchery':True}))
    def clean(self):
        hoy = datetime.now()
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        horainicio = cleaned_data.get('horainicio')
        horafin = cleaned_data.get('horafin')
        instancia = self.instancia
        id = getattr(instancia, 'id', 0)
        id_incidencia = instancia.incidencia.id if instancia else cleaned_data.get('id_incidencia')
        if horainicio >= horafin:
            self.add_error('horainicio', 'La hora de inicio debe ser menor a la hora de fin')

        fecha_hasta = (hoy + timedelta(days=1)).date()
        if fecha <= fecha_hasta:
            self.add_error('fecha', 'La audiencia debe planificarse al menos un día después de la fecha actual')

        incidencia = IncidenciaSancion.objects.get(id=int(id_incidencia))
        if incidencia.audiencias().filter(fecha=fecha, horainicio=horainicio).exclude(id=id).exists():
            self.add_error('fecha', 'Ya existe una audiencia planificada para esta fecha y hora de inicio')
        return cleaned_data

class GenerarActaForm(FormModeloBase):
    from sagest.models import Bloque, Ubicacion
    id_audiencia = forms.IntegerField(label="id_audiencia", widget=forms.HiddenInput(), required=False)
    numerodelegacion = forms.CharField(max_length=50, label=u"Número de delegación", required=False,
                                    widget=forms.TextInput({'col': '12', 'icon': 'bi bi-chat-text', 'placeholder': 'Escriba el número de delegación'}))


class AccionPersonalForm(FormModeloBase):
    id_personasancion = forms.IntegerField(label="id_personasancion", widget=forms.HiddenInput(), required=False)
    # tipo = forms.ModelChoiceField(label=u"Tipo de acción",
    #                                 queryset=TipoAccionPersonal.objects.filter(status=True),
    #                                 widget=forms.Select(attrs={'col': '2', 'class': 'select2'}))
    motivoaccion = forms.ModelChoiceField(label=u"Motivo", queryset=MotivoAccionPersonal.objects.filter(status=True),
                                          required=True, widget=forms.Select(attrs={'col': '4', 'class': 'select2'}))
    procesoinstitucional = forms.ChoiceField(label="Proceso institucional", choices=TIPO_PROCESO_TH,
                                             required=True, initial=1, widget=forms.Select(
                                                attrs={'col': '4', 'class': 'select2', 'icon': 'bi bi-filter'}))
    # partidapresupuestariaactual = forms.CharField(max_length=150, label=u'Partida presupuestaria actual',
    #                                               widget=forms.TextInput(attrs={'col': '4', 'placeholder': '0.0',
    #                                                                             'input_group': '$', 'class': 'input_money'}), required=True)
    fechadesde = forms.DateField(label=u"Fecha rige desde", initial=datetime.now().date(), required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '2'}))
    fechahasta = forms.DateField(label=u"Fecha rige hasta", required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '2'}))
    denominacionpuesto = forms.ModelChoiceField(label=u"Denominacion de puesto",
                                                queryset=DenominacionPuesto.objects.filter(status=True),
                                                widget=forms.Select(attrs={'col': '5', 'class': 'select2'}))
    nivelgestion = forms.ChoiceField(label="Proceso institucional", choices=NIVEL_GESTION,
                                     required=True, initial=1, widget=forms.Select(
                                    attrs={'col': '3', 'class': 'select2', 'icon': 'bi bi-filter'}))
    declaracion = forms.BooleanField(label="¿Presento declaración juramentada?", required=False,
                                     widget=forms.CheckboxInput(attrs={'col': '4', 'icon': 'bi bi-person-fill-check',
                                                                       'data-switchery': True}))
    explicacion = forms.CharField(label=u'Explicación', widget=forms.Textarea(attrs={'rows': '5'}), required=False)

    subrogante = forms.BooleanField(label="Es subrogante", required=False, widget=forms.CheckboxInput(
        attrs={'col': '2', 'icon': 'bi bi-person-fill-check', 'data-switchery': True}))
    director = forms.ModelChoiceField(label=u"Director",
                                      queryset=Persona.objects.filter(status=True).order_by('apellido1'), required=True,
                                      widget=forms.Select(attrs={'col': '4', 'class': 'select2', 'icon': 'bi bi-people',
                                                                 'api': 'true'}))
    nominadordelegdo = forms.BooleanField(label="Es delegado", required=False, widget=forms.CheckboxInput(
        attrs={'col': '2', 'icon': 'bi bi-person-fill-check', 'data-switchery': True}))
    nominador = forms.ModelChoiceField(label=u"Autoridad nominadora",
                                       queryset=Persona.objects.filter(status=True).order_by('apellido1'),
                                       required=True,
                                       widget=forms.Select(
                                           attrs={'col': '4', 'class': 'select2', 'icon': 'bi bi-people',
                                                  'api': 'true'}))



class FaltaDisciplinariaForm(FormModeloBase):
    regimen_laboral = forms.ModelChoiceField(label=u'Regimen laboral',
                                    queryset=RegimenLaboral.objects.filter(status=True).order_by('descripcion'),
                                    required=True, widget=forms.Select(
                                    {'col': '12', 'class': 'select2', 'icon': 'bi bi-ui-radios-grid'}))
    nombre = forms.ChoiceField(label="Estado general", choices=NOMBRE_FALTA_DISCIPLINARIA,
                                        required=True, initial=0,
                                        widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-filter'}))
    descripcion = forms.CharField(max_length=4000, label=u"Descripción", required=True,
                                  widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text', 'tooltip': Strings.tooltipDesFalta }))
    articulo = forms.CharField(max_length=4000, label=u"Artículo", required=True,
                                    widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text', 'tooltip': Strings.tooltipArticuloFalta }))
    motivacionjuridica = forms.CharField(label=u"Motivacion juridica", required=True,
                                   widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text',
                                                          'class':'ckeditors','tooltip': Strings.tooltipFaltaDisciplinariaForm, 'editor-sm':'true'}))

    def clean(self):
        try:
            cleaned_data = super().clean()
            instancia = self.instancia
            id = getattr(self.instancia, 'id', 0)
            nombre = cleaned_data.get('nombre').strip().upper()
            falta =  FaltaDisciplinaria.objects.filter(nombre__unaccent__iexact=nombre, status=True).exclude(id=id)
            if falta.exists():
                self.add_error('nombre', 'Ya existe un tipo de falta con este nombre')
            cleaned_data['nombre'] = nombre
            return cleaned_data
        except Exception as e:
            print(e)

class MotivoSancionForm(FormModeloBase):
    falta = forms.ModelChoiceField(label=u'Tipo de falta',
                                             queryset=FaltaDisciplinaria.objects.filter(status=True),
                                             required=True, widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-ui-radios-grid'}))
    nombre = forms.CharField(max_length=300, label=u"Nombre", required=True,
                                    widget=forms.TextInput({'col': '12', 'icon': 'bi bi-chat-right-text'}))
    descripcion = forms.CharField(max_length=4000, label=u"Descripción", required=True,
                                    widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text'}))

    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        nombre = cleaned_data.get('nombre').strip().upper()
        motivo = MotivoSancion.objects.filter(nombre__unaccent__iexact=nombre, status=True, principal=True).exclude(id=id)
        if motivo.exists():
            self.add_error('nombre', 'Ya existe un motivo con este nombre')
        cleaned_data['nombre'] = nombre
        return cleaned_data

class SubMotivoSancionForm(FormModeloBase):
    motivoref = forms.ModelChoiceField(label=u'Clasificación',
                                    queryset=MotivoSancion.objects.filter(status=True, principal=True),
                                    required=True, widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))
    nombre = forms.CharField(max_length=300, label=u"Nombre", required=True,
                                    widget=forms.TextInput({'col': '12', 'icon': 'bi bi-chat-right-text'}))
    descripcion = forms.CharField(max_length=4000, label=u"Descripción", required=True,
                                    widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text'}))

    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        nombre = cleaned_data.get('nombre').strip().upper()
        motivoref = cleaned_data.get('motivoref')
        motivo = MotivoSancion.objects.filter(nombre__unaccent__iexact=nombre, status=True, principal=False, motivoref=motivoref).exclude(id=id)
        if motivo.exists():
            self.add_error('nombre', 'Ya existe un sub motivo con este nombre')
        cleaned_data['nombre'] = nombre
        return cleaned_data

class RequisitoSancionForm(FormModeloBase):
    nombre = forms.CharField(max_length=300, label=u"Nombre", required=True,
                                    widget=forms.TextInput({'col': '12', 'icon': 'bi bi-chat-right-text'}))
    descripcion = forms.CharField(max_length=300, label=u"Descripción", required=True,
                                    widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text'}))
    tiporequisto = forms.ChoiceField(label="Tipo de requisito", choices=TIPO_REQUISITO, required=True,
                                    widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))

    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        nombre = cleaned_data.get('nombre').strip().upper()
        requisito = RequisitoSancion.objects.filter(status=True, nombre=nombre).exclude(id=id)
        if requisito.exists():
            self.add_error('tiporequisto', 'Ya existe un requisito con este nombre')
        cleaned_data['nombre'] = nombre
        return cleaned_data

class RequisitoMotivoSancionForm(FormModeloBase):
    motivo = forms.ModelChoiceField(label=u'Sub clasificación',
                                    queryset=MotivoSancion.objects.filter(status=True, principal=False),
                                    required=True, widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))
    requisito = forms.ModelChoiceField(label=u'Requisito',
                                    queryset=RequisitoSancion.objects.filter(status=True),
                                    required=True, widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))
    punto_control = forms.ChoiceField(label="Punto de control", choices=choice_indice(PUNTO_CONTROL, (0, 2)), required=True,
                                     widget=forms.Select({'col': '12', 'class': 'select2', 'icon': 'bi bi-patch-exclamation'}))
    obligatorio = forms.BooleanField(label="¿Es obligatorio?", required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'icon': 'bi bi-patch-exclamation', 'data-switchery':True}))
    activo = forms.BooleanField(label="Activo", required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'icon': 'bi bi-patch-exclamation', 'data-switchery':True}))
    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        motivo = cleaned_data.get('motivo')
        requisito = cleaned_data.get('requisito')
        requisitomotivo = RequisitoMotivoSancion.objects.filter(motivo=motivo, requisito=requisito, status=True).exclude(id=id)
        if requisitomotivo.exists():
            self.add_error('requisito', 'Ya existe este requisito asociado a al motivo seleccionado')
        return cleaned_data

class ResponsableFirmaForm(FormModeloBase):
    persona = forms.ModelChoiceField(label="Persona", queryset=Persona.objects.filter(status=True).order_by('apellido1'), required=True,
                                    widget=forms.Select(attrs={'col': '12', 'class': 'select2', 'icon': 'bi bi-people', 'api':'true'}))
    tipo_doc = forms.ChoiceField(label="Tipo de documento", choices=TIPO_DOCUMENTOS, required=True,
                                 widget=forms.Select(attrs={'col': '12', 'class': 'select2', 'icon': 'bi bi-file-earmark-text'}))
    rol_doc = forms.ChoiceField(label="Rol en el documento", choices=ROL_FIRMA_DOCUMENTO, required=True,
                                widget=forms.Select(attrs={'col': '12', 'class': 'select2', 'icon': 'bi bi-file-earmark-text'}))
    orden = forms.IntegerField(label="Orden", min_value=1, max_value=10, required=True, widget=forms.NumberInput(attrs={'col': '6', 'icon': 'bi bi-sort-numeric-up'}))
    firma_doc = forms.BooleanField(label="¿Firma el documento?", initial=True, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'icon': 'bi bi-pen', 'data-switchery':True}))

    def clean(self):
        cleaned_data = super().clean()
        persona = cleaned_data.get('persona')
        tipo_doc = cleaned_data.get('tipo_doc')
        rol_doc = cleaned_data.get('rol_doc')
        orden = cleaned_data.get('orden')
        firma_doc = cleaned_data.get('firma_doc')
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        if orden < 1:
            self.add_error('orden', 'El orden debe ser mayor a 0')
        if orden > 10:
            self.add_error('orden', 'El orden no debe ser mayor a 10')
        # responsable = ResponsableFirma.objects.filter(persona=persona, tipo_doc=tipo_doc,  status=True).exclude(id=id)
        # if responsable.exists():
        #     self.add_error('persona', 'Ya existe un responsable con estos datos')
        tiporoloren = ResponsableFirma.objects.filter(status=True, tipo_doc=tipo_doc, orden=orden, firma_doc=True).exclude(id=id)
        if firma_doc and tiporoloren.exists():
            self.add_error('orden', 'Este orden ya esta asignado a otro responsable')
        return cleaned_data


class ValidarAudienciaForm(FormModeloBase):
    from directivo.models import FaltaDisciplinaria
    id_audiencia = forms.CharField(widget=forms.HiddenInput())
    estado_desicion = forms.ChoiceField(label="Estado general", choices=ESTADO_DESICION_AUDIENCIA[1:],
                                        required=True, initial=2,
                                        widget=forms.Select(attrs={'col': '6', 'class': 'select2', 'icon': 'bi bi-filter'}))
    observacion = forms.CharField(max_length=300, label=u"Observación", required=False,
                                  widget=forms.Textarea({'rows': '2', 'col': '12', 'icon': 'bi bi-chat-right-text'}))

class JustificacionPersonaAudienciaForm(FormModeloBase):
    justificacion = forms.CharField(label=u"Justificación", required=True,
                                    widget=forms.Textarea(attrs={'col': '12', 'rows': 3, 'icon': 'bi bi-chat-right-text'}))
    archivo = forms.FileField(label=u'Seleccione Archivo', required=False,
                                help_text=u'Tamaño máximo permitido 5Mb, en formato pdf',
                                widget=forms.FileInput(attrs={'col': '12' ,'accept': '.png, .jpg, .jpeg, .pdf', 'icon': 'bi bi-file-earmark-text'}))
    def clean(self):
        from directivo.models import RespuestaDescargo
        cleaned_data = super().clean()
        descripcion = cleaned_data.get('justificacion')
        archivo = cleaned_data.get('archivo')
        instancia = self.instancia
        id = getattr(instancia, 'id', 0)
        if not instancia and not archivo:
            self.add_error('archivo', 'Debe adjuntar un archivo')
            return cleaned_data
        if archivo:
            max_tamano = 5 * 1024 * 1024  # 5 MB
            name_ = archivo._name
            ext = name_[name_.rfind("."):]
            if not ext.lower() in ['.png', '.jpg', '.jpeg', '.pdf']:
                self.add_error('archivo', f'Solo se permite formato .png, .jpg, .jpeg, .pdf')

            if archivo.size > max_tamano:
                self.add_error('archivo', f'Archivo supera los 5 megas permitidos')
            # Asignar un nombre personalizado al archivo
            idpersona = instancia.personasancion.id if instancia else ''
            name_archive = 'justificacion'
            archivo._name = generar_nombre(f"{idpersona}_{name_archive}", archivo._name)
            cleaned_data['archivo'] = archivo

        return cleaned_data

class MotivoNoFirmaAccionPersonalForm(FormModeloBase):
    motivo = forms.CharField(label=u"Motivo", required=True,
                                    widget=forms.Textarea(attrs={'col': '12', 'rows': 3, 'icon': 'bi bi-chat-right-text'}))
    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        id = getattr(self.instancia, 'id', 0)
        return cleaned_data
