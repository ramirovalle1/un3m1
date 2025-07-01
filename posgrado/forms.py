# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta

from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q

from core.custom_forms import FormModeloBase
from sagest.models import CuentaBanco, FormaDePago, TIPO_COMPROBANTE
from sga.models import Persona, Carrera, Utensilios, Modalidad, Sede, Sesion, Profesor, CoordinacionImagenes, \
    TIPO_IMAGEN, Coordinacion, TIPO_IMAGEN_NOMBRE, Titulo, Provincia, Canton, Parroquia, AreaConocimientoTitulacion, \
    SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, NivelTitulacion, GradoTitulacion, \
    InstitucionEducacionSuperior, Pais, Periodo, Sexo, ItinerarioMallaEspecilidad, EtapaTemaTitulacionPosgrado, \
    MecanismoTitulacionPosgrado, Malla, PreguntaCaracteristicaEvaluacionAcreditacion, AsignaturaMalla, Materia, \
    ZONA_DOMICILIO
from posgrado.models import CohorteMaestria, TipoPreguntasPrograma, EvidenciasMaestrias, TIPO_ARCHIVO, TIPO_COHORTE, \
    RolAsesor, AsesorComercial, \
    MaestriasAdmision, ESTADO_ASESOR_COMERCIAL, ESTADO_PROYECTO_VINCULACION, TIPO_EVIDENCIA, Requisito, \
    TipoClasificacionRequisito, MOTIVO_RECHAZA_DESACTIVA, \
    TipoRespuestaProspecto, ConfigFinanciamientoCohorte, TipoPersonaRequisito, CanalInformacionMaestria, TIPO_INFORME, \
    SeccionInforme, TIPO_PREGUNTA, Pregunta, SeccionInformePregunta, ESTADO_DICTAMEN, Informe, MOTIVO_OFICIO, \
    SedeEncuestaTitulacionPosgrado, JornadaSedeEncuestaTitulacionPosgrado, MESES_CHOICES, ActividadPersonalPosgrado, \
    PreguntaEncuestaSatisfaccionDocente, EncuestaSatisfaccionDocente, HorariosProgramaMaestria, \
    ClasificadorPresupuestario, AsociacionPresupuestaria, CuentaContable
from inno.models import TipoFormaPagoPac
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from sagest.models import Rubro
from ckeditor_uploader.widgets import CKEditorUploadingWidget

filtered_choices = [choice for choice in PreguntaEncuestaSatisfaccionDocente.TipoPregunta.choices if choice[0] in {1}]
class CheckboxSelectMultipleCustom(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(CheckboxSelectMultipleCustom, self).render(*args, **kwargs)
        return mark_safe(output.replace(u'<ul>', u'<div class="custom-multiselect" style="width: 600px;overflow: scroll"><ul>').replace(u'</ul>', u'</ul></div>').replace(u'<li>', u'').replace(u'</li>', u'').replace(u'<label', u'<div style="width: 900px"><li').replace(u'</label>', u'</li></div>'))

def campo_requerido(form, campo):
    form.fields[campo].widget.attrs['required'] = True

CHOICES_RADIO_APROBAR_RECHAZAR =[('2','Aprobar'),('3','Rechazar')]
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


class RegistroRequisitosMaestriaForm(forms.Form):
    hojavida = ExtFileField(label=u'Hoja de vida:', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc',ext_whitelist=(".pdf", ".doc", "docx", ".DOC", "DOCX"), max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))
    copiavotacion = ExtFileField(label=u'Certificado de votación:', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))
    copiacedula = ExtFileField(label=u'Cédula de identidad:', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))
    senescyt = ExtFileField(label=u'Certificado Senescyt:', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))
    lenguaextranjera = ExtFileField(label=u'Certificado lengua extranjera (opcional):', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))

class RegistroRequisitosMaestriaForm1(forms.Form):
    hojavida = ExtFileField(label=u'Hoja de vida:', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc',ext_whitelist=(".pdf", ".doc", "docx", ".DOC", "DOCX"), max_upload_size=10485760)
    copiavotacion = ExtFileField(label=u'Certificado de votación:', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760)
    copiacedula = ExtFileField(label=u'Cédula de identidad:', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760)
    senescyt = ExtFileField(label=u'Certificado Senescyt:', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760)
    lenguaextranjera = ExtFileField(label=u'Certificado lengua extranjera (opcional):', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760)



class EvidenciasMaestriasForm(forms.Form):
    observaciones = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)


class PreInscripcionForm(forms.Form):
     carrera = forms.ModelChoiceField(label=u"Carrera",  queryset=Carrera.objects.filter(coordinacion=7, status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'class': 'imp-75'}))


class FormatoCarreraForm(forms.Form):
    carrera = forms.ModelChoiceField(label=u"Programa",  queryset=Carrera.objects.filter(coordinacion=7, status=True).order_by('nombre'), required=True, widget=forms.Select(attrs={'class': 'imp-75'}))
    correomaestria = forms.EmailField(label=u'Correo del programa',max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-100','style': 'text-transform:lowercase;'}))
    archivo = ExtFileField(label=u'Archivo PDF', required=False, help_text=u'Tamaño Maximo permitido 50Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf", ".doc", "docx", ".DOC", "DOCX"), max_upload_size=50485760, widget=FileInput({'accept': 'application/pdf'}))
    banner = ExtFileField(label=u'Banner', required=False,help_text=u'Tamaño Maximo permitido 20Mb, en formato jpg o png',ext_whitelist=(".jpeg", ".jpg", ".png"), max_upload_size=50485760)


class UtensiliosForm(forms.Form):
    utensilios = forms.ModelChoiceField(label=u"Utensilios", queryset=Utensilios.objects.filter(status=True), required=True, widget=forms.Select(attrs={'class': 'imp-75'}))
    cantidad = forms.IntegerField(label=u'Cantidad', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))


class AdmiPeriodoForm(FormModeloBase):
    carrera = forms.ModelChoiceField(label=u"Carrera",  queryset=Carrera.objects.filter(coordinacion__id__in=[7,13], status=True).order_by('nombre'), required=False, widget=forms.Select(attrs={'class': 'imp-100', 'col': '12'}))
    descripcion = forms.CharField(label=u'Nombre', widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=True)

    def editar(self):
        deshabilitar_campo(self, 'carrera')

class CopiarRequisitosForm(FormModeloBase):
    programa = forms.ModelChoiceField(label=u"Programa",  queryset=MaestriasAdmision.objects.filter(status=True).order_by('descripcion'), required=False, widget=forms.Select(attrs={'class': 'imp-100', 'col': '12'}))

class CohorteMaestriaForm(forms.Form):
    periodoacademico = forms.ModelChoiceField(label=u"Periodo", queryset=Periodo.objects.filter(tipo_id=3, status=True), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    coordinador = forms.ModelChoiceField(label=u"Coordinador", queryset=Persona.objects.select_related().filter(status=True).order_by('apellido1'), required=False, widget=forms.Select())
    descripcion = forms.CharField(label=u'Nombre', max_length=100, widget=forms.TextInput(attrs={'formwidth': '100%', 'placeholder': 'Nombre de la cohorte'}))
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.filter(status=True), required=True, widget=forms.Select(attrs={'formwidth': '50%'}))
    alias = forms.CharField(label=u'Alias', widget=forms.TextInput(attrs={'formwidth': '50%', 'placeholder': 'Iniciales del nombre de la cohorte'}))
    numerochorte = forms.IntegerField(label=u'Número de cohorte', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    cupodisponible = forms.IntegerField(label=u'Cupos asignados por el CES', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    # cuposlibres = forms.IntegerField(label=u'Cupos libres', initial=0, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    fechainiciocohorte = forms.DateField(label=u"Fecha inicio cohorte", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafincohorte = forms.DateField(label=u"Fecha fin cohorte", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechainicioinsp = forms.DateField(label=u"Fecha inicio inscripción", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafininsp = forms.DateField(label=u"Fecha fin inscripción", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    # fechainicioextraordinariainsp = forms.DateField(label=u"Fecha inicio extraordinaria de inscripción", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    # fechafinextraordinariainsp = forms.DateField(label=u"Fecha fin inicio extraordinaria de inscripción", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    finiciorequisitos = forms.DateField(label=u"Fecha inicio subida de subir evidencias", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    ffinrequisitos = forms.DateField(label=u"Fecha fin subida de evidencias", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafinrequisitobeca = forms.DateField(label=u"Fecha fin subida de requisitos becas", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '100%'}))
    fechainicioexamen = forms.DateField(label=u"Fecha inicio de exámene", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafinexamen = forms.DateField(label=u"Fecha fin exámen", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    notaminimaexa = forms.FloatField(label=u'Nota probación exámen', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))
    # notamaximaexa = forms.FloatField(label=u'Nota maxima exámen', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))
    notaminimatest = forms.FloatField(label=u'Nota admitido', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))
    # notamaximatest = forms.FloatField(label=u'Nota maxima test', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))
    # ponderacionminimaentrevista = forms.FloatField(label=u'Ponderacion minima de entevista', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))
    # ponderacionmaximaentrevista = forms.FloatField(label=u'Ponderacion maxima de entevista', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%'}))
    cantidadgruposexamen = forms.IntegerField(label=u'Cantidad de aspirantes para grupo de examen', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    cantidadgruposentrevista = forms.IntegerField(label=u'Cantidad de aspirantes para grupo de entrevista', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    minutosrango = forms.IntegerField(label=u'Minutos de entrevista', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    totaladmitidoscohorte = forms.IntegerField(label=u'Total admitidos por cohorte', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%'}))
    #tienecostoexamen = forms.BooleanField(label=u"Tiene costo el examen", required=False, initial=False)
    #valorexamen = forms.FloatField(label=u'Valor por pagar de examen', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '33%'}))
    #tienecostomatricula = forms.BooleanField(label=u"Tiene costo matricula", required=False, initial=False)
    #valormatricula = forms.FloatField(label=u'Valor de la matricula', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '34%'}))
    # tienecuota = forms.BooleanField(label=u"Tiene cuotas", required=False, initial=False)
    numerocuota = forms.FloatField(label=u'Numero de cuotas de la maestría', initial="", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right','decimal': '0', 'formwidth': '33%'}))
    valorcuota = forms.FloatField(label=u'Valor de cuotas de la maestría', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right','decimal': '2', 'formwidth': '33%'}))
    #costomaestria = forms.FloatField(label=u'Costo de maestría', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right','decimal': '2', 'formwidth': '34%'}))
    activo = forms.BooleanField(label=u"Activar cohorte", required=False, initial=True, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    tipo = forms.ChoiceField(label=u"Tipo", choices=TIPO_COHORTE, required=False,widget=forms.Select(attrs={'formwidth': '40%'}))
    tienecostotramite = forms.BooleanField(label=u"Tiene costo de trámite", required=False, initial=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    valortramite = forms.FloatField(label=u'Valor por pagar de trámite', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'formwidth': '33%'}))
    #def deshabilitar(self):
     #   deshabilitar_campo(self, 'costomaestria')


class AdmiRequisitosMaestriaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    activo = forms.BooleanField(label=u"Activo", required=False, initial=True)
    requerido = forms.BooleanField(label=u"Requerido", required=False, initial=True)
    archivo = ExtFileField(label=u'Archivo PDF', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))


class RequisitoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'class': 'imp-100'}))
    tipoarchivo = forms.ChoiceField(label=u"Itinerario", choices=TIPO_ARCHIVO, required=False,widget=forms.Select(attrs={'formwidth': '40%'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    clasificacion = forms.ModelMultipleChoiceField(label=u"Clasificación", queryset=TipoClasificacionRequisito.objects.filter(status=True), required=False)
    activo = forms.BooleanField(label=u"Activo", required=False, initial=True)
    archivo = ExtFileField(label=u'Archivo PDF', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf, docx, doc', ext_whitelist=(".pdf",".doc","docx",".DOC","DOCX"),max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))


class AdmiPreguntasMaestriaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=True)
    activo = forms.BooleanField(label=u"Activo", required=False, initial=True)


class RequisitosMaestriaForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Seleccione Archivo', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760)

class RequisitosMaestriaImgForm(forms.Form):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Archivo', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato jpg o png',ext_whitelist=(".jpeg", ".jpg", ".png", ".JPEG", ".JPG", ".PNG"), max_upload_size=10485760)


class AdmiCohorteMaestriaForm(forms.Form):
    maestria = forms.ModelChoiceField(label=u"Programa de Maestría", queryset=CohorteMaestria.objects.filter(status=True), required=False,widget=forms.Select(attrs={'class': 'imp-75'}))


class EntrevistadorCohorteForm(forms.Form):
    administrativo = forms.IntegerField(initial=0, required=False, label=u'Entrevistador', widget=forms.TextInput(attrs={'select2search': 'true'}))


class GrupoExamenForm(forms.Form):
    profesor = forms.ModelChoiceField(Profesor.objects.filter(status=True), required=True, label=u'Profesor', widget=forms.Select(attrs={'formwidth': '100%'}))
    lugar = forms.CharField(label=u'Lugar de examen', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=True)
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',attrs={'class': 'selectorfecha', 'formwidth': '35%'}), required=True)
    hora = forms.TimeField(label=u"Hora:", required=False, initial=datetime.now().time(), input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '40%'}))
    visible = forms.BooleanField(label=u"Visible", required=False, initial=True, widget=forms.CheckboxInput(attrs={'formwidth': '15%'}))
    urlzoom = forms.CharField(label=u'URL Zoom', widget=forms.Textarea(attrs={'rows': '1'}), required=False)
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '2'}), required=False)

    def editar(self):
        deshabilitar_campo(self, 'lugar')
        deshabilitar_campo(self, 'fecha')


class GrupoEntrevistaForm(forms.Form):
    administrativo = forms.IntegerField(initial=0, required=False, label=u'Entrevistador', widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    lugar = forms.CharField(label=u'Lugar de entrevista', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=False)
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '35%'}), required=True)
    horainicio = forms.TimeField(label=u"Hora Inicio:", required=False, initial=datetime.now().time(), input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': '40%'}))
    visible = forms.BooleanField(label=u"Visible", required=False, initial=True, widget=forms.CheckboxInput(attrs={'formwidth': '15%'}))
    urlzoom = forms.CharField(label=u'URL Zoom', widget=forms.Textarea(attrs={'rows': '1'}), required=False)
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '2'}), required=False)

    def editar(self):
        del self.fields['lugar']
        del self.fields['fecha']


class TipoPreguntaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=False)


class PreguntaForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    tipopregunta = forms.ModelChoiceField(label=u"Tipo Pregunta", queryset=TipoPreguntasPrograma.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-75'}))


class TablaEntrevistaMaestriaForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=True)


class AdmiPagoExamenForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    valor = forms.FloatField(label=u'Valor ', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class MatriculaPagoCuota(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    valor = forms.FloatField(label=u'Valor ', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class AdmiPagoMatriculaForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", required=True, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha'}))
    valor = forms.FloatField(label=u'Valor Matrícula', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2'}))


class EstadisticaCalificacionCabForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=True)


class EstadisticaCalificacionDetForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', widget=forms.TextInput(attrs={'class': 'imp-100'}), required=True)
    puntajeminimo = forms.FloatField(label=u"Nota Minima", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))
    puntajemaximo = forms.FloatField(label=u"Nota Maxima", initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2'}))

class MatrizInscritosEntrevistaForm(forms.Form):
    archivomatriz = ExtFileField(label=u'Fichero', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato xls, xlsx', ext_whitelist=(".xls", ".xlsx"), max_upload_size=4194304)


class MatrizInscritosEntrevistaNotasForm(forms.Form):
    archivomatriz = ExtFileField(label=u'Fichero', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato xls, xlsx', ext_whitelist=(".xls", ".xlsx"), max_upload_size=4194304)


class InscripcionCarreraForm(forms.Form):
    sede = forms.ModelChoiceField(label=u"Sede", queryset=Sede.objects.all(), required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.filter(coordinacion=7, status=True), required=False)
    modalidad = forms.ModelChoiceField(label=u"Modalidad", queryset=Modalidad.objects.all(), required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    sesion = forms.ModelChoiceField(label=u"Sesion", queryset=Sesion.objects.all(), required=False)


class RegistroAdmisionIpecForm(forms.Form):
    cedula = forms.CharField(label=u"Cédula", max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    telefono = forms.CharField(label=u"Teléfono", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-50'}))


class CoordinacionImagenesForm(forms.Form):
    tipoimagen = forms.ChoiceField(label=u"Tipo Imagen", choices=TIPO_IMAGEN, required=False,widget=forms.Select(attrs={'formwidth': '40%'}))
    tipoimagennombre = forms.ChoiceField(label=u"Utilización", choices=TIPO_IMAGEN_NOMBRE, required=False,widget=forms.Select(attrs={'formwidth': '40%'}))
    imagen = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 5MB, en formato jpg o png', ext_whitelist=(".jpeg", ".jpg", ".png", ".JPEG", ".JPG", ".PNG"), max_upload_size=5242880)

class RegistroPagoForm(forms.Form):
    telefono = forms.CharField(label=u"Teléfono Estudiante", max_length=10, required=True, widget=forms.TextInput(attrs={'class': 'imp-25', 'onKeyPress': "return soloNumeros(event)","tooltip": "CONFIRMAR NÚMERO TELEFONICO"}))
    email = forms.CharField(label=u"Correo Electronico Estudiante", max_length=240, required=True,widget=forms.TextInput(attrs={'class': 'imp-descripcion', "tooltip": "CONFIRMAR CORREO ELECTRONICO"}))
    fecha = forms.DateField(label=u"Fecha Deposito", required=True, initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha',  'formwidth': '50%', "tooltip": "INDICAR FECHA DEL DEPOSITO Y/O TRANSFERENCIA, SEGÚN CONSTA EN EL COMPROBANTE BANCARIO"}))
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=True,widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumerosPunto(event)", 'decimal': "2", 'formwidth': '50%',"tooltip": "INDICAR VALOR DEL DEPOSITO, SEGÚN CONSTA EN EL COMPROBANTE BANCARIO"}))
    #curso = forms.CharField(label=u"Curso a Pagar", max_length=600, required=True, widget=forms.TextInput(attrs={'class': 'imp-100', "tooltip": "IDENTIFICAR EL NOMBRE DEL CURSO AL QUE EFECTUA EL PAGO"}))
    #carrera = forms.CharField(label=u"Carrera", max_length=600, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', "tooltip": "REGISTRAR EN CASO DE SER ALUMNO DE UNEMI"}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2', 'formwidth': '100%', "tooltip": "DETALLAR INFORMACION RELEVANTE TALES COMO NÚMERO O MES DE CUOTA A PAGAR", 'class': 'form-control'}))
    tipocomprobante = forms.ChoiceField(choices=TIPO_COMPROBANTE, required=False, label=u'Tipo Comprobante', widget=forms.Select(attrs={'formwidth': '100%', 'separator': 'true',  "tooltip": "SELECCIONE MODALIDAD DE PAGO TRANSFERENCIA Y/O DEPÓSITO"}))
    activo = forms.BooleanField(required=False, label=u'Desea que los datos de factura salga a nombre de otra persona?',
                                widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    # DATOS DE FACTURACION
    nombres = forms.CharField(
        label=u"Nombres:", max_length=600, required=False,
        widget=forms.TextInput(
            attrs={'class': 'imp-100', 'formwidth': '50%', "tooltip": "Nombres para facturar", "separator": True,
                   "separatortitle": 'DATOS DE FACTURACION'})
    )
    apellidos = forms.CharField(
        label=u"Apellidos:", max_length=600, required=False,
        widget=forms.TextInput(
            attrs={'class': 'imp-100', 'formwidth': '50%', "tooltip": "Nombres para facturar", })
    )
    identificacion = forms.CharField(
        label=u"Identificacion:", max_length=13, required=False,
        widget=forms.TextInput(
            attrs={'class': 'imp-100', 'formwidth': '50%', "tooltip": "Identificacion para facturar"})
    )
    correo = forms.CharField(
        label=u"Email:", max_length=100, required=False,
        widget=forms.TextInput(
            attrs={'class': 'imp-100', 'formwidth': '50%', "tooltip": "Correo electronico para facturar"})
    )
    telefonofactura = forms.CharField(
        label=u"Telefono:", max_length=100, required=False,
        widget=forms.TextInput(
            attrs={'class': 'imp-100', 'formwidth': '50%', "tooltip": "Telefono para facturar"})
    )
    direccion = forms.CharField(
        label=u"Direccion:", max_length=600, required=False,
        widget=forms.TextInput(
            attrs={'class': 'imp-100', 'formwidth': '50%', "tooltip": "Direccion para facturar"})
    )
class RolForm(forms.Form):
    descripcion = forms.CharField(label=u"Nombre", required=True,
                                  widget=forms.TextInput(attrs={'class': 'imp-codigo', 'formwidth': '40%'}))

class AsesorComercialForm(FormModeloBase):
    from posgrado.models import GRUPO_ROL
    persona = forms.ModelChoiceField(label=u"Persona",  queryset=Persona.objects.filter(status=True, perfilusuario__administrativo__isnull=False).order_by('apellido1', 'apellido2', 'nombres'), required=True, widget=forms.Select(attrs={'class': 'imp-100', 'col': '6'}))
    rol = forms.ModelChoiceField(label=u"Rol", queryset=RolAsesor.objects.filter(status=True, id__in=[1, 4, 6]).order_by('descripcion'), required=True, widget=forms.Select(attrs={'class': 'imp-100', 'col': '6'}))
    gruporol = forms.ChoiceField(choices=GRUPO_ROL, required=True, label=u'Grupo Rol', widget=forms.Select(attrs={'class': 'imp-100', 'col': '6'}))
    fechadesdevig = forms.DateField(label=u"Fecha inicio de vigencia", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    fechahastavig = forms.DateField(label=u"Fecha fin de vigencia", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    telefono = forms.CharField(label=u"Teléfono", max_length=10, required=False, widget=forms.TextInput(attrs={'col':'6'}))
    activo = forms.BooleanField(initial=True, label=u"Activo", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))

    def sin_persona(self):
        del self.fields['persona']

class InscripcionCohorteForm(FormModeloBase):
    persona = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    maestria = forms.CharField(label=u"Maestría", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    cohorte = forms.CharField(label=u"Cohorte", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    asesoractual = forms.CharField(label=u"Asesor Actual", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    asesor = forms.ModelChoiceField(label=u"Nuevo Asesor", queryset=AsesorComercial.objects.filter(status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres'), help_text=mark_safe('<b>Nota:</b> La lista de asesor futuro ha sido validada para que se listen únicamente los asesores que tienen asignada la cohorte de maestría a la cual pertenece el lead seleccionado.'), required=True, widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control', 'col': '12'}), required=False)

class AsignarTerritorioForm(FormModeloBase):
    asesor = forms.CharField(label=u"Asesor", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    canton = forms.ModelChoiceField(label=u"Territorio", queryset=Canton.objects.filter(status=True).order_by('provincia__pais__id'),
                                    required=True, widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))

class FinanciamientoForm(FormModeloBase):
    persona = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    tipo = forms.ModelChoiceField(label=u"Forma de Pago", queryset=TipoFormaPagoPac.objects.filter(status=True), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    subirrequisitogarante = forms.BooleanField(label=u'Subir requisitos garante', required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))

    def sin_subirrequisitogarante(self):
        del self.fields['subirrequisitogarante']


class CambioCohorteMaestriaForm(FormModeloBase):
    cohorteactual = forms.CharField(label=u"Cohorte Actual", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    cohorte = forms.ModelChoiceField(label=u"Nueva Cohorte", queryset=CohorteMaestria.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '12'}))

class CambioConvenioMaestriaForm(FormModeloBase):
    from posgrado.models import Convenio
    convenio = forms.ModelChoiceField(label=u"Nuevo Convenio", queryset=Convenio.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12'}))

class CambioHomologacionMaestriaForm(FormModeloBase):
    from posgrado.models import IDENTIFICA_HOMOLOGADO
    homologado = forms.ChoiceField(label=u"Asignar Homologación", choices=IDENTIFICA_HOMOLOGADO, required=False, widget=forms.Select(attrs={'col': '12'}))

class AsignarTipoForm(FormModeloBase):
    persona = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '12'}))
    maestria = forms.CharField(label=u"Maestría", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '12'}))
    cohorte = forms.CharField(label=u"Cohorte", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '12'}))
    tipo = forms.ModelChoiceField(label=u"Tipo de Financiamiento", queryset=ConfigFinanciamientoCohorte.objects.filter(status=True), required=True, widget=forms.Select(attrs={'class': 'imp-100', 'col': '12'}))
    subirrequisitogarante = forms.BooleanField(label=u'Subir requisitos garante', required=False, widget=CheckboxInput(attrs={'formwidth': '25%'}))

    def sin_subir(self):
        del self.fields['subirrequisitogarante']

class HistorialRespuestaProspectoForm(FormModeloBase):
    prospecto = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    tiporespuesta = forms.ModelChoiceField(label=u'Tipo de Respuesta', queryset=TipoRespuestaProspecto.objects.filter(status=True).exclude(id=1).order_by('id'), required=True,
                               widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control', 'col': '12'}), required=False)


class ReservacionProspectoForm(FormModeloBase):
    prospecto = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False)

class MencionMaestriaForm(FormModeloBase):
    prospecto = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    maestria = forms.CharField(label=u"Maestría", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    cohorte = forms.CharField(label=u"Cohorte", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    mencion = forms.ModelChoiceField(label=u'Mención', queryset=ItinerarioMallaEspecilidad.objects.filter(status=True),required=True,
                               widget=forms.Select(attrs={'class': 'imp-100', 'col': '12'}))

class CanalInformacionForm(FormModeloBase):
    canal = forms.CharField(required=True, label=u'Canal', widget=forms.TextInput(attrs={'class': 'imp-100'}))
    valido = forms.BooleanField(initial=False, required=False, label=u'Valido para formulario externo?', widget=CheckboxInput(attrs={'formwidth': '25%'}))

class RechazoDesactivaForm(FormModeloBase):
    motivo = forms.ChoiceField(choices=MOTIVO_RECHAZA_DESACTIVA, required=True, label=u'Estado', widget=forms.Select())

class ConvenioForm(FormModeloBase):
    descripcion = forms.CharField(required=True, label=u'Descripcion', widget=forms.TextInput(attrs={'class': 'imp-100'}))
    fechaInicio = forms.DateField(label=u"Fecha inicio convenio",required=True,widget=DateTimeInput({'col': '6'}))
    porcentajedescuento = forms.FloatField(label=u'Porcentaje descuento', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%', 'col': '6'}))
    descripcionrequisito = forms.CharField(required=True, label=u'Descripcion requisito', widget=forms.TextInput(attrs={'class': 'imp-100','col':'6'}))
    archivo = ExtFileField(label=u'Subir Archivo', required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato pdf',
                               ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput())
    valido = forms.BooleanField(initial=False, required=False, label=u'Valido para formulario externo?', widget=CheckboxInput(attrs={'formwidth': '25%','col': '6'}))
    aplicadescuento = forms.BooleanField(initial=False, required=False, label=u'Aplica descuento?', widget=CheckboxInput(attrs={'formwidth': '25%','col': '6'}))
    suberequisito = forms.BooleanField(initial=False, required=False, label=u'Sube requisito?', widget=CheckboxInput(attrs={'formwidth': '25%','col': '6'}))

    def renombrar(self):
        self.fields['archivo'].widget.initial_text = "Anterior"
        self.fields['archivo'].widget.input_text = "Cambiar"

hoy = datetime.now().date()
class AsesorMetaForm(forms.Form):
    asesor = forms.CharField(label=u"Asesor", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    maestria = forms.ModelChoiceField(label=u"Maestria con Cohorte Abierta", queryset=MaestriasAdmision.objects.filter(cohortemaestria__procesoabierto=True, cohortemaestria__fechainicioinsp__lte=hoy, cohortemaestria__fechafininsp__gte=hoy).distinct(), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    cohorte = forms.ModelChoiceField(label=u"Cohorte Abierta",queryset=CohorteMaestria.objects.filter(procesoabierto=True, status=True), help_text=mark_safe('<br><b>Nota:</b> En función de asignar correctamente la fecha de inicio y de fin de la meta, tome en consideración el rango de fechas del periodo de inscripción de la cohorte seleccionada, contenidos en los campos presentados a continuación'),required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    espacio = forms.IntegerField(label=u"", widget=forms.HiddenInput({'value': '0'}))
    fechainicioins = forms.DateField(label=u"Fecha de Inicio de Inscripcion de la Cohorte", input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'readonly': 'true'}))
    fechafinins = forms.DateField(label=u"Fecha de Fin de Inscripcion de la Cohorte", input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%','readonly': 'true'}))
    cupo = forms.IntegerField(label=u'Cupos asignados por el CES', initial=0, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'readonly': 'true'}))
    cuposlibres = forms.IntegerField(label=u'Cupos libres', initial=0, help_text=mark_safe('<b>Nota:</b> Es importante asignar una meta que no sobrepase la cantidad de cupos libres o pendientes de asignacion en la cohorte seleccionada'), widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'readonly': 'true'}))
    fechainiciometa = forms.DateField(label=u"Fecha de inicio de la meta", input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    fechafinmeta = forms.DateField(label=u"Fecha de fin de la meta", input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    meta = forms.IntegerField(label=u'Meta', initial=0, required=True, help_text=mark_safe('<b>Nota:</b> Debe asegurarse que el rango de fecha asignado para que el asesor obtenga leads y cumpla con su meta no exceda el periodo de inscripcion de la cohorte seleccionada, ya que una vez este finalice no será capaz de registrar leads en el sistema'), widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))


#    cohortes = forms.ModelMultipleChoiceField(label=u'Maestrias con Cohortes Abiertas', queryset=MaestriasAdmision.objects.filter(cohortemaestria__procesoabierto=True),required=True)
#queryset=CohorteMaestria.objects.filter(procesoabierto=True


class ConfirmarPreAsignacionForm(forms.Form):
    persona = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    maestria = forms.CharField(label=u"Maestría", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    cohorte = forms.CharField(label=u"Cohorte", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    asesor_creacion = forms.CharField(label=u"Usuario de Creacion", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    asesor = forms.ModelChoiceField(label=u"Asesor", queryset=AsesorComercial.objects.filter(status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres'), help_text=mark_safe('<b>Nota:</b> El combo de asesor futuro ha sido validado para que se listen ùnicamente los asesores que tienen asignada la maestria a la cual pertenece el lead seleccionado.'), required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    estado_asesor = forms.ChoiceField(choices=ESTADO_ASESOR_COMERCIAL, required=True, label=u'Estado', widget=forms.Select())
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)


class ConfigurarFirmaAdmisionPosgradoForm(forms.Form):
    persona = forms.ChoiceField(label=u"Persona", required=True, widget=forms.Select(attrs={'class': 'imp-100'}))
    cargo = forms.CharField(label=u'Cargo', required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

    def editar(self, id, name):
        self.fields['persona'].choices = [(id, name)]
        self.fields['persona'].initial = [1]


class TitulacionPersonaPosgradoForm(forms.Form):
    titulo = forms.ModelChoiceField(label=u"Titulo", queryset=Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23, 30], status=True), required=False, widget=forms.Select())
    mostrarcampos = forms.BooleanField(label=u'Registrar campos adicionales', required=False, widget=CheckboxInput())
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=10, required=False,
                                  widget=forms.TextInput(attrs={'class': 'form-control'}))
    nivel = forms.ModelChoiceField(NivelTitulacion.objects.filter(status=True, tipo=1), label=u'Tipo de nivel',
                                   required=False, widget=forms.Select(attrs={'class': 'form-control nivel'}))
    grado = forms.ModelChoiceField(GradoTitulacion.objects.all(), label=u'Grado', required=False,
                                   widget=forms.Select(attrs={'class': 'form-control'}))
    institucion = forms.ModelChoiceField(label=u"Institución de educación superior",
                                         queryset=InstitucionEducacionSuperior.objects.all(), required=False,
                                         widget=forms.Select(attrs={'formwidth': '100%'}))
    registro = forms.CharField(label=u'Número de registro SENESCYT', max_length=50, required=False,
                               widget=forms.TextInput(attrs={'class': 'imp-25'}))
    registroarchivo = ExtFileField(label=u'Seleccione Archivo SENESCYT', required=False,
                                   help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                                   ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)
    pais = forms.ModelChoiceField(label=u"País", queryset=Pais.objects.all(), required=False,
                                  widget=forms.Select(attrs={'formwidth': '100%'}))
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    canton = forms.ModelChoiceField(label=u"Cantón", queryset=Canton.objects.all(), required=False,
                                    widget=forms.Select(attrs={'formwidth': '100%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.all(), required=False,
                                       widget=forms.Select(attrs={'formwidth': '100%'}))
    campoamplio = forms.ModelMultipleChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control', 'separator2': True, 'separatortitle': 'Datos del Título', }))
    campoespecifico = forms.ModelMultipleChoiceField(label=u"Campo Especifico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))
    campodetallado = forms.ModelMultipleChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control'}))

    def adicionar(self):
        self.fields['titulo'].queryset = Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23, 30], status=True)
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)
        self.fields['campoespecifico'].queryset = SubAreaConocimientoTitulacion.objects.filter(nombre=None)
        self.fields['campodetallado'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(nombre=None)

class TitulacionPersonaAdmisionPosgradoForm(forms.Form):
    titulo = forms.ModelChoiceField(label=u"Titulo", queryset=Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23, 30], status=True), required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=10, required=False,
                                  widget=forms.TextInput(attrs={'class': 'form-control'}))
    nivel = forms.ModelChoiceField(NivelTitulacion.objects.filter(id__in=[3, 4, 21, 22, 23, 30], status=True), label=u'Tipo de nivel',
                                   required=False, widget=forms.Select(attrs={'class': 'form-control imp-100 nivel'}))
    grado = forms.ModelChoiceField(GradoTitulacion.objects.all(), label=u'Grado', required=False,
                                   widget=forms.Select(attrs={'class': 'imp-100'}))
    institucion = forms.ModelChoiceField(label=u"Institución de educación superior",
                                         queryset=InstitucionEducacionSuperior.objects.all(), required=True,
                                         widget=forms.Select(attrs={'class': 'imp-100'}))
    registro = forms.CharField(label=u'Número de registro SENESCYT', max_length=50, required=True,
                               widget=forms.TextInput(attrs={'class': 'imp-50'}))
    registroarchivo = ExtFileField(label=u'Seleccione Archivo SENESCYT (Requisito de admisión)', required=False,
                                   # help_text=u'Tamaño maximo permitido 4Mb, en formato pdf, jpg, jpeg, png',
                                   ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png",), max_upload_size=4194304)
    # pais = forms.ModelChoiceField(label=u"País de obtención del título", queryset=Pais.objects.all(), required=True,
    #                               widget=forms.Select(attrs={'class': 'imp-100'}))
    campoamplio = forms.ModelMultipleChoiceField(label=u"Campo Amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control imp-100', 'separator2': True, 'separatortitle': 'Datos del Título', }))
    # provincia = forms.ModelChoiceField(label=u"Provincia de obtención del título", queryset=Provincia.objects.all(), required=True,
    #                                    widget=forms.Select(attrs={'class': 'imp-100'}))
    campoespecifico = forms.ModelMultipleChoiceField(label=u"Campo Especifico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control imp-100'}))
    # canton = forms.ModelChoiceField(label=u"Cantón de obtención del título", queryset=Canton.objects.all(), required=True,
    #                                 widget=forms.Select(attrs={'class': 'imp-100'}))
    campodetallado = forms.ModelMultipleChoiceField(label=u"Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True).order_by('codigo'), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control imp-100'}))
    # parroquia = forms.ModelChoiceField(label=u"Parroquia de obtención del título", queryset=Parroquia.objects.all(), required=True,
    #                                    widget=forms.Select(attrs={'class': 'imp-100'}))

    def adicionar(self):
        self.fields['titulo'].queryset = Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23, 30], status=True)
        # self.fields['provincia'].queryset = Provincia.objects.filter(pais=None)
        # self.fields['canton'].queryset = Canton.objects.filter(provincia=None)
        # self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=None)
        self.fields['campoespecifico'].queryset = SubAreaConocimientoTitulacion.objects.filter(nombre=None)
        self.fields['campodetallado'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.filter(nombre=None)

class numeroCuotasPagoForm(forms.Form):
    numcuotaspago = forms.IntegerField(label=mark_safe(u"<strong>Número de cuotas</strong>"), initial=1, required=True, widget=forms.NumberInput(attrs={'class': 'imp-number', 'formwidth': '50%','min':'1'}))

    def maximo(self, n):
        self.fields['numcuotaspago'].widget.attrs['max'] = str(n)

class GarantePagoMaestriaForm(FormModeloBase):
    cedula = forms.CharField(label=u"Cédula", max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'imp-cedula', 'col': '6', 'onKeyPress': "return soloNumeros(event)", 'placeholder':'Ingrese cédula del garante'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=True, widget=forms.TextInput(attrs={'class':'form-control', 'col': '6', 'placeholder':'Ingrese nombres completos'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=True, widget=forms.TextInput(attrs={'class':'form-control', 'col': '6', 'placeholder':'Ingrese apellido paterno'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class':'form-control', 'col': '6', 'placeholder':'Ingrese apellido materno'}))
    genero = forms.ModelChoiceField(label=u"Género", required=True, queryset=Sexo.objects.all(), widget=forms.Select(attrs={'class':'form-control', 'col': '6'}))
    telefono = forms.CharField(label=u"Teléfono", max_length=10, required=True, widget=forms.TextInput(attrs={'onKeyPress': "return soloNumeros(event)",'class':'form-control', 'col': '6', 'placeholder':'Ingrese número de teléfono'}))
    email = forms.CharField(label=u"Correo", max_length=200, required=True, widget=forms.TextInput(attrs={'class':'form-control', 'col': '6', 'placeholder':'Ingrese correo electónico'}))
    direccion = forms.CharField(label=u'Dirección Domicilio', max_length=100, required=True, widget=forms.TextInput(attrs={'class':'form-control', 'col': '6', 'placeholder':'Ingrese dirección del garante'}))

    def editar(self):
        deshabilitar_campo(self, 'cedula')

class ConfigFinanciamientoCohorteForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=400, required=True, widget=forms.TextInput(attrs={'formwidth': '100%'}))
    valortotalprograma = forms.FloatField(label=u'Valor total del programa', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'formwidth': '50%', 'col': '4'}))
    valormatricula = forms.FloatField(label=u'Valor de la matricula', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2','formwidth': '50%', 'col': '4'}))
    porcentajeminpagomatricula = forms.FloatField(label=u'Porcentaje mín pago matrícula', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '2', 'col': '4'}))
    valorarancel = forms.FloatField(label=u'Valor Arancel', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '2', 'col': '4'}))
    maxnumcuota = forms.IntegerField(initial="", label=u'Máx. número de cuotas', required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'onKeyPress': "return soloNumeros(event)", 'col': '4'}))
    fecha = forms.DateField(label=u"Fecha corte de cuotas", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '3'}))

class ContratoPagoMaestriaForm(FormModeloBase):
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3'}), required=False)
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760)

class RequisitoConvenioAspiranteForm(FormModeloBase):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760)

class OficioTerminacionContratoForm(FormModeloBase):
    motivo = forms.ChoiceField(label=u'Motivo de terminación', choices=MOTIVO_OFICIO, required=True, widget=forms.Select(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760)

class TipoClasificacionReqForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=500, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class ClasificacionRequisitoForm(forms.Form):
    requisito = forms.ModelChoiceField(label=u"Requisito", queryset=Requisito.objects.all(), required=True,
                                    widget=forms.Select(attrs={'class': 'imp-100'}))
    clasificacion = forms.ModelChoiceField(label=u"Clasificación", queryset=TipoClasificacionRequisito.objects.all(), required=True,
                                    widget=forms.Select(attrs={'class': 'imp-100'}))

    tipopersona = forms.ModelChoiceField(label=u"Tipo Persona", queryset=TipoPersonaRequisito.objects.filter(status=True), required=False,
                                    widget=forms.Select(attrs={'class': 'imp-100'}))
    def editar(self):
        deshabilitar_campo(self, 'requisito')

class TipoPersonaForm(forms.Form):
    requisito = forms.ModelChoiceField(label=u"Requisito", queryset=Requisito.objects.all(), required=True,
                                    widget=forms.Select(attrs={'class': 'imp-100'}))
    clasificacion = forms.ModelChoiceField(label=u"Clasificación", queryset=TipoClasificacionRequisito.objects.all(), required=True,
                                    widget=forms.Select(attrs={'class': 'imp-100'}))

    tipopersona = forms.ModelChoiceField(label=u"Tipo Persona", queryset=TipoPersonaRequisito.objects.filter(status=True), required=False,
                                    widget=forms.Select(attrs={'class': 'imp-100'}))

    def editar(self):
        deshabilitar_campo(self, 'requisito')
        deshabilitar_campo(self, 'clasificacion')

class ActualizarDatosPersonaForm(FormModeloBase):
    cedula = forms.CharField(label=u"Cédula", max_length=13, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    nombres = forms.CharField(label=u'Nombres', max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    apellido1 = forms.CharField(label=u"1er Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    apellido2 = forms.CharField(label=u"2do Apellido", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    telefono = forms.CharField(label=u"Teléfono", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    email = forms.CharField(label=u"Correo electrónico", max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'style': 'text-transform:lowercase;'}))


class ProyectoVinculacionForm(forms.Form):
    titulo = forms.CharField(label=u"Titulo", required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(label=u'Descripcion', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}), required=False)
    tipoevidencia = forms.ChoiceField(label=u'Tipo de evidencia', choices=TIPO_EVIDENCIA, required=True, widget=forms.Select(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    evidencia = ExtFileField(label=u'Evidencia', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=FileInput({'class': 'form-control', 'accept': 'application/pdf'}))


class DetalleAprobacionProyectoForm(forms.Form):
    proyecto = forms.MultipleChoiceField(label=u"Proyectos", choices=(), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'formwidth': '100%', 'placeholder': 'Seleccione uno o más proyectos...'}))
    estadoaprobacion = forms.ChoiceField(label=u'Estado', choices=((1, 'APROBADO'), (3, 'RECHAZADO')), initial=1, required=True, widget=forms.Select(attrs={'class': 'imp-100', 'formwidth': '100%'}))
    observacion = forms.CharField(label=u'Observación:', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '3', 'placeholder':'Ingrese una breve observación...'}), required=False)

    def individual(self):
        del self.fields['proyecto']

    def masivo(self, choices):
        self.fields['proyecto'].choices = choices

class ComprobanteArchivoEstudianteForm(forms.Form):
    telefono = forms.CharField(label=u"Teléfono Estudiante", max_length=10, required=True, widget=forms.TextInput(attrs={'class': 'imp-25', 'onKeyPress': "return soloNumeros(event)"}))
    email = forms.CharField(label=u"Correo Electronico Estudiante", max_length=240, required=True,widget=forms.TextInput(attrs={'class': 'imp-descripcion'}))
    fecha = forms.DateField(label=u"Fecha Deposito", required=True, initial=datetime.now().date(), input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha',  'formwidth': '50%'}))
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=True,widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumerosPunto(event)", 'decimal': "2", 'formwidth': '50%'}))
    # curso = forms.ModelChoiceField(queryset=Rubro.objects.all().none(), required=True, label=u'Curso a pagar', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    curso = forms.CharField(label=u"Curso a Pagar", max_length=600, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    carrera = forms.CharField(label=u"Carrera", max_length=600, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '2', 'formwidth': '100%', 'class': 'form-control'}))
    tipocomprobante = forms.ChoiceField(choices=TIPO_COMPROBANTE, required=False, label=u'Tipo Comprobante', widget=forms.Select(attrs={'formwidth': '100%'}))
    evidencia = ExtFileField(label=u'Comprobante', required=True, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                                                ext_whitelist=(".pdf",".png",".jpg"), max_upload_size=4194304)



class FormSolicitudProrrogaIngresoTemaMatricula(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'class': 'form-control', 'col': '12','rows': '4'}))
    estado = forms.ChoiceField(label=u'Estado de la solicitud',choices=CHOICES_RADIO_APROBAR_RECHAZAR, widget=forms.RadioSelect({'class': 'form-control', 'col': '12'}))
    fechainicioprorroga = forms.DateField(label=u"Fecha inicio prórroga",required=False,widget=DateTimeInput({'col': '6'}))
    fechafinprorroga = forms.DateField(label=u"Fecha fin prórroga",required=False,widget=DateTimeInput({'col': '6'}))

    def revisar(self,solicitud):
        self.fields['descripcion'].initial   = solicitud.observacion
        self.fields['descripcion'].widget.attrs['disabled'] = True


class EditarComprobantePagoForm(forms.Form):
    valor = forms.DecimalField(initial="0.00", label=u'Valor', required=True,widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumerosPunto(event)", 'decimal': "2", 'formwidth': '50%'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'rows': '7', 'formwidth': '100%', 'class': 'form-control'}))
    tipocomprobante = forms.ChoiceField(choices=TIPO_COMPROBANTE, required=False, label=u'Tipo Comprobante', widget=forms.Select(attrs={'formwidth': '100%'}))
    evidencia = ExtFileField(label=u'Comprobante', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf',
                                                                ext_whitelist=(".pdf",".png",".jpg"), max_upload_size=4194304)
    def renombrar(self):
        self.fields['evidencia'].widget.initial_text = "Anterior"
        self.fields['evidencia'].widget.input_text = "Cambiar"

class TipoDocumentoTitulacionForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=300, required=True, widget=forms.TextInput({'col': '12'}))

class EstadoDocumentoTitulacionForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', max_length=300, required=True, widget=forms.TextInput({'col': '12'}))
    nombrefirma = forms.CharField(label=u'Nombre firma', max_length=500, required=True, widget=forms.TextInput({'col': '12'}))
    orden = forms.IntegerField(label=u'Orden', required=True, widget=forms.NumberInput(attrs={'class': 'imp-number', 'col': '4', 'style': 'with:30%'}))
    habilitado = forms.BooleanField(initial=True, required=False, label=u'¿Habilitado?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '4', 'data-switchery': 'true'}))

class FormInforme(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'class': 'form-control', 'col': '12','rows': '4'}))
    tipo = forms.ChoiceField(label=u'Tipo Informe',choices=TIPO_INFORME, widget=forms.Select({'class': 'form-control', 'col': '12'}))

class FormConfiguracionInforme(FormModeloBase):
    informe = forms.ModelChoiceField(label=u'Informe', required=True, queryset=Informe.objects.filter(status=True,estado=True).order_by( 'id'), widget=forms.Select({'col': '12'}))
    mecanismotitulacionposgrado = forms.ModelChoiceField(label=u'Mecanismo', required=True, queryset=MecanismoTitulacionPosgrado.objects.filter(status=True).order_by( 'id'), widget=forms.Select({'col': '12'}))
    programa = forms.ModelChoiceField(label=u'Programa', required=True, queryset=Carrera.objects.filter(status=True, coordinacion__id__in=[7, 13]).order_by( 'id'), widget=forms.Select({'col': '12'}))
    estado = forms.BooleanField(label=u"¿Activo?", required = False, widget=forms.CheckboxInput(attrs={'class': 'form-controljs-switch', 'col': '12'}))

class FormSeccionInforme(FormModeloBase):
    seccion = forms.ModelChoiceField(label=u'Sección', required=True, queryset=EtapaTemaTitulacionPosgrado.objects.filter(status=True,clasificacion = 2).order_by( 'id'), widget=forms.Select({'col': '12'}))
    orden = forms.IntegerField(label=u"Orden", required=True, initial=0,widget=forms.TextInput(attrs={'col': '2'}))

    def add(self, idinforme):
        self.fields['seccion'].queryset = EtapaTemaTitulacionPosgrado.objects.filter(status=True,clasificacion = 2).exclude(pk__in = SeccionInforme.objects.values_list("seccion_id", flat=True).filter(status = True, informe__id = idinforme ))

    def edit(self,idinforme,id_etapa):
        self.fields['seccion'].queryset = EtapaTemaTitulacionPosgrado.objects.filter(status=True,clasificacion = 2).exclude(pk__in = SeccionInforme.objects.values_list("seccion_id", flat=True).filter(status = True,  informe__id = idinforme ).exclude(seccion__id=id_etapa))

class FormPreguntaInforme(FormModeloBase):
    descripcion = forms.CharField(label=u'Descripción', required=False, widget=forms.Textarea({'class': 'form-control', 'col': '12','rows': '4'}))


class FormSeccionInformePregunta(FormModeloBase):
    pregunta = forms.ModelChoiceField(label=u'Pregunta', required=True, queryset=Pregunta.objects.filter(status=True).order_by( 'id'), widget=forms.Select({'col': '12'}))
    tipo_pregunta = forms.ChoiceField(label=u'Tipo pregunta',choices=TIPO_PREGUNTA, widget=forms.Select({'class': 'form-control', 'col': '12'}))

    def add(self, id_informe):
        self.fields['pregunta'].queryset = Pregunta.objects.filter(status=True).exclude(pk__in = SeccionInformePregunta.objects.values_list("pregunta_id", flat=True).filter(status = True, seccion_informe__informe__id = id_informe ))

    def edit(self,id_informe,id_pregunta):
        self.fields['pregunta'].queryset = Pregunta.objects.filter(status=True).exclude(pk__in = SeccionInformePregunta.objects.values_list("pregunta_id", flat=True).filter(status = True,  seccion_informe__informe__id = id_informe ).exclude(pregunta__id=id_pregunta))


class FormDictamen(FormModeloBase):
    dictamen = forms.ChoiceField(label=u'Dictamen',choices=ESTADO_DICTAMEN, widget=forms.Select({'class': 'form-control', 'col': '12'}))

class EvidenciaRequisitoAdmisionForm(FormModeloBase):
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea({'rows': '2'}))
    archivo = ExtFileField(label=u'Subir Archivo', required=True, help_text=u'Tamaño máximo permitido 10Mb, en formato pdf',
                               ext_whitelist=(".pdf",), max_upload_size=10485760, widget=forms.FileInput())

class ValidarPerfilAdmisionForm(FormModeloBase):
    titulo = forms.CharField(label=u"Titulo", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    postulante = forms.CharField(label=u"Postulante", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    cantidad = forms.IntegerField(label=u'Cantidad de experiencia', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0'}))

    def sin_cantidad(self):
        del self.fields['cantidad']

    def sin_titulo(self):
        del self.fields['titulo']

class EditarRubroMaestriaForm(FormModeloBase):
    idinscripcion = forms.CharField(label=u"Id inscripción", required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    nombre = forms.CharField(label=u'Nombre del rubro', required=False, widget=forms.Textarea({'class': 'form-control', 'col': '12','rows': '4'}))
    cohorte = forms.ModelChoiceField(label=u'Cohorte de maestría', required=True, queryset=CohorteMaestria.objects.filter(status=True).order_by( '-id'), widget=forms.Select({'col': '12'}))
    valor = forms.FloatField(label=u'Valor', initial="0.00", required=False, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '2'}))
    fecha = forms.DateField(label=u"Vencimiento",required=False,widget=DateTimeInput({'col': '6'}))
    matricula = forms.BooleanField(initial=False, required=False, label=u'¿Es rubro de matrícula?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '4', 'data-switchery': 'true'}))

    def solo_cohorte(self):
        del self.fields['nombre']
        del self.fields['valor']
        del self.fields['fecha']
        del self.fields['matricula']

    def no_id(self):
        del self.fields['idinscripcion']

class AdicionarCuotaTablaAmortizacionForm(FormModeloBase):
    numerocuota = forms.CharField(label=u"Número de cuota", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    nombre = forms.CharField(label=u'Nombre de la cuota', required=True, widget=forms.Textarea({'class': 'form-control', 'col': '12','rows': '4'}))
    valor = forms.FloatField(label=u'Valor', initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '2'}))
    oculto = forms.CharField(label=u'', required=False, widget=forms.HiddenInput({'class': 'form-control', 'col': '10'}))
    inicio = forms.DateField(label=u"Fecha inicio de pago de la cuota",required=True,widget=DateTimeInput({'col': '6'}))
    fin = forms.DateField(label=u"Fecha fin de pago de la cuota",required=True,widget=DateTimeInput({'col': '6'}))


class ReasignarMasivoForm(FormModeloBase):
    asesor = forms.ModelChoiceField(label=u"Asesor a asignar", queryset=AsesorComercial.objects.filter(status=True),
                                    required=True, widget=forms.Select(attrs={'col': '12'}))
    observacion = forms.CharField(label=u'Observación', widget=forms.Textarea(attrs={'rows': '3', 'class': 'form-control', 'col': '12'}), required=False)

    def no_asesor(self):
        del self.fields['asesor']

class VentasMaestriasForm(FormModeloBase):
    persona = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    maestria = forms.CharField(label=u"Maestría", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    cohorte = forms.CharField(label=u"Cohorte", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    fecha = forms.DateField(label=u"Fecha de la venta", initial=datetime.now().date(), widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    facturado = forms.BooleanField(initial=True, label=u"¿Facturado?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    valida = forms.BooleanField(initial=True, label=u"¿Válida?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))


class RevisionExpedienteForm(FormModeloBase):
    observacion = forms.CharField(required=True, label=u'Observación', widget=forms.Textarea({'rows': '2'}))

class ArchivoInvitacionForm(forms.Form):
    archivo = ExtFileField(label=u'Seleccione Archivo', required=True, help_text=u'Tamaño Maximo permitido 6Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=6291456, widget=FileInput({'style':'width:100%;', 'class':'form-control', 'col': '12', 'accept': 'application/pdf'}))


class CambioMaestriaForm(FormModeloBase):
    persona = forms.CharField(label=u"Prospecto", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    maestria = forms.CharField(label=u"Maestría Actual", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    maestriacambio = forms.ModelChoiceField(label=u'Nueva Maestria', required=True, queryset=MaestriasAdmision.objects.filter(status=True), widget=forms.Select({'col': '12'}))




class SeleccionSedeForm(FormModeloBase):
    pais = forms.ModelChoiceField(required=True, queryset=Pais.objects.filter(pk=1), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el país de domicilio o residencia (requerido)'})
    provincia = forms.ModelChoiceField(required=False, queryset=Provincia.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })
    canton = forms.ModelChoiceField(required=False, queryset=Canton.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })


class JornadaEncuestaSedeForm(FormModeloBase):
    fecha = forms.DateField(label=u'Fecha', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '12'}))
    hora_inicio = forms.TimeField(label=u"Desde (Hora)", input_formats=['%H:%M'], initial=str(datetime.now().time()), widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': 'span3'}),required=True)
    hora_fin = forms.TimeField(label=u"Hasta (Hora)", input_formats=['%H:%M'], initial=str(datetime.now().time()),  widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'formwidth': 'span3'}), required=True)
    cupo = forms.IntegerField(label=u"Cupo", required=True, initial=0, widget=forms.TextInput(attrs={'col': '3', 'formwidth': '50%'}))

class CronogramaEncuestaForm(FormModeloBase):
    inicio = forms.DateField(label=u'Fecha inicio ', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '12'}))
    fin = forms.DateField(label=u'Fecha Fin', required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date', 'col': '12'}))
    activo = forms.BooleanField(label=u"Activo", required=False, initial=True)

class EncuestaSatisfaccionDocenteForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripcion", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    tipo = forms.ChoiceField(label=u'Tipo', choices=EncuestaSatisfaccionDocente.TipoEncuesta.choices, required=True, widget=forms.Select(attrs={'class': 'imp-50', 'col': '12'}))
    leyenda = forms.CharField(required=True, label=u'Leyenda', widget=forms.Textarea({'rows': '2', 'col':'12'}))
    activo = forms.BooleanField(initial=True, label=u"¿Activa?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))
    obligatoria = forms.BooleanField(initial=True, label=u"¿Obligatoria?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6'}))

class PreguntaEncuestaSatisfaccionDocenteForm(FormModeloBase):
    tipo = forms.ChoiceField(label=u'Tipo', choices=filtered_choices, required=True, widget=forms.Select(attrs={'class': 'imp-50', 'col': '12'}))
    descripcion = forms.CharField(label=u"Pregunta", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    observacionporno = forms.CharField(label=u"Pregunta por no", required=False, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    orden = forms.IntegerField(label=u'Orden', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '2'}))
    obligatoria = forms.BooleanField(initial=True, label=u"¿Obligatoria?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    pregunta = forms.ModelChoiceField(label=u"Opciones de pregunta?",required=False, queryset=PreguntaEncuestaSatisfaccionDocente.objects.none(),
                                      widget=forms.Select(attrs={'col':'12'}))

    def no_mostrar(self):
        del self.fields['observacionporno']

    def edit_pregunta(self, id):
        pregunta = PreguntaEncuestaSatisfaccionDocente.objects.filter(pk=id)
        self.fields['pregunta'].queryset = pregunta
        self.fields['pregunta'].initial = [id]

class OpcionCuadriculaSatisfaccionDocenteForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    valor = forms.IntegerField(label=u'Valor', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    orden = forms.IntegerField(label=u'Orden', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    otros = forms.BooleanField(initial=False, label=u"¿Es respuesta otros?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    archivo = forms.BooleanField(initial=False, label=u"Sube evidencia?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))
    secuenciapregunta = forms.ModelChoiceField(label=u'Pregunta de secuencia', required=False, queryset=PreguntaEncuestaSatisfaccionDocente.objects.filter(status=True), widget=forms.Select({'col': '12'}))

    def no_mostrar_col(self):
        del self.fields['otros']
        del self.fields['archivo']
        del self.fields['secuenciapregunta']

    def no_mostrar_fil(self):
        del self.fields['otros']
        del self.fields['archivo']
        del self.fields['secuenciapregunta']


class SeleleccionSedeJornadaForm(FormModeloBase):
    sedeencuestatitulacionposgrado = forms.ModelChoiceField(label=u"Sedes",required=True, queryset=SedeEncuestaTitulacionPosgrado.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', 'required': 'Seleccione el país de domicilio o residencia (requerido)'})
    jornadasedeencuestatitulacionposgrado = forms.ModelChoiceField(label=u"Jornadas",required=False, queryset=JornadaSedeEncuestaTitulacionPosgrado.objects.none(), widget=forms.Select(), error_messages={'invalid_choice': 'Seleccione una opción válida. Esa elección no es una de las opciones disponibles.', })

    def cargar_sedes(self,eEncuestaTitulacionPosgrado):
        eSedeEncuestaTitulacionPosgrado = SedeEncuestaTitulacionPosgrado.objects.filter(status=True,encuestatitulacionposgrado =eEncuestaTitulacionPosgrado)
        self.fields['sedeencuestatitulacionposgrado'].queryset =eSedeEncuestaTitulacionPosgrado


    def inicializar_campos_sede(self, sedeencuestatitulacionposgrado_id):
        self.fields['sedeencuestatitulacionposgrado'].initial = sedeencuestatitulacionposgrado_id

    def inicializar_campos_jornada(self,  jornadasedeencuestatitulacionposgrado_id):
        self.fields['jornadasedeencuestatitulacionposgrado'].initial = jornadasedeencuestatitulacionposgrado_id

class EvidenciaColorPreguntaEncuestaForm(FormModeloBase):
    pregunta = forms.CharField(label=u"Pregunta", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    tipo = forms.ChoiceField(label=u'Tipo de evidencia', choices=PreguntaCaracteristicaEvaluacionAcreditacion.TipoColor.choices, required=True, widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))


class FormObservacion(FormModeloBase):
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'class': 'form-control', 'col': '12','rows': '4'}))


class BalanceCostoForm(FormModeloBase):
    anio = forms.CharField(label=u"Año", required=False, widget=forms.TextInput(attrs={'class': 'imp-anio', 'col': '6'}))
    mes = forms.ChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES, widget=forms.Select(attrs={ 'col': '6'}))
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False, label=u"Descripción")

class InscribirMatricularForm(FormModeloBase):
    admitido = forms.CharField(label=u"Admitido", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '12'}))
    periodo = forms.CharField(label=u"Periodo", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '12'}))
    nivel = forms.CharField(label=u"Nivel", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '12'}))
    maestria = forms.CharField(label=u"Maestria", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '6'}))
    cohorte = forms.CharField(label=u"Cohorte", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '6'}))
    modalidad = forms.CharField(label=u"Modalidad", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '6'}))

class HorarioMaestriaAdmitidoForm(FormModeloBase):
    carrera = forms.ModelChoiceField(label=u"Maestría: ", queryset=Carrera.objects.filter(status=True, coordinacion__id=7, maestriasadmision__isnull=False), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    horario = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=True, label=u"Horario")
    paralelo = forms.CharField(label=u"Paralelo", widget=forms.TextInput(attrs={'col': '3', 'style': 'width:50%; text-align:center'}))

    def editar(self):
        deshabilitar_campo(self, 'carrera')

class AsignarHorarioAdmitidoForm(FormModeloBase):
    admitido = forms.CharField(label=u"Admitido", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '12'}))
    maestria = forms.CharField(label=u"Maestria", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '6'}))
    cohorte = forms.CharField(label=u"Cohorte", widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true', 'col': '6'}))
    horario = forms.ModelChoiceField(label=u"Horario: ", queryset=HorariosProgramaMaestria.objects.filter(status=True, activo=True), required=True, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))

class GestionHojaTrabajoForm(FormModeloBase):
    descripcion = forms.CharField(widget=forms.TextInput(attrs={'col': '12'}), required=True, label=u"Descripción")


class IntegranteGestionHojaTrabajoForm(FormModeloBase):
    persona = forms.ModelChoiceField(label=u" Persona: ", queryset=Persona.objects.none(), required=False, widget=forms.Select(attrs={'col': '7', 'style': 'width:100%', 'class': 'validate[required]'}))
    rmu = forms.FloatField(label=u"RMU", initial="0.00", required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '5'}))

    def edit(self, pk):
        persona = Persona.objects.filter(pk=pk)
        self.fields['persona'].queryset = persona
        self.fields['persona'].initial = persona.first()


class ActividadIntegranteGestionHojaTrabajoForm(FormModeloBase):
    carrera = forms.ModelChoiceField(label=u" Carrera: ", queryset=Carrera.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    actividadpersonalposgrado = forms.ModelChoiceField(label=u" Actividad: ", queryset=ActividadPersonalPosgrado.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12', 'style': 'width:100%'}))
    hora_de_trabajo = forms.FloatField(label=u"Horas de trabajo", initial="0.00",  required=True, widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '12','max':'8'}))

    def edit(self, carrera_id):
        carrera = Carrera.objects.filter(pk=carrera_id)
        self.fields['carrera'].queryset = carrera
        self.fields['carrera'].initial = carrera.first()


class ProfesorInvitadoValoresForm(FormModeloBase):
    cantidad_medio_tiempo = forms.IntegerField(label=u'Cantidad medio tiempo', initial=0, required=True, widget=forms.TextInput(  attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    medio_tiempo = forms.FloatField(label=u"Total medio tiempo", initial="0.00", required=True,widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '6'}))
    cantidad_tiempo_completo = forms.IntegerField(label=u'Cantidad tiempo completo', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    tiempo_completo = forms.FloatField(label=u"Total tiempo completo", initial="0.00", required=True,widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '6'}))

class CostoVariableValoresForm(FormModeloBase):
    costo_por_publicidad = forms.FloatField(label=u"Costo por publicidad", initial="0.00", required=True,widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '6'}))
    evento_promocionales = forms.FloatField(label=u"Evento promocionales", initial="0.00", required=True,widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '6'}))
    materiales_de_oficina = forms.FloatField(label=u"Materiales de oficina", initial="0.00", required=True,widget=forms.TextInput(attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '6'}))


class ConfigurarCarreraProfesorInvitadoForm(FormModeloBase):
     carrera = forms.ModelMultipleChoiceField(Carrera.objects.filter(niveltitulacion_id=4, status=True, activa=True), required=False, label=u'Carrera', widget=forms.SelectMultiple(attrs={'formwidth': '100%', 'col': '12', 'style': 'width:100%'}))


class ConfigurarRmuForm(FormModeloBase):
    rmu = forms.FloatField(label=u"Rmu", initial="0.00", required=True, widget=forms.TextInput( attrs={'class': 'imp-moneda', 'decimal': '2', 'col': '12'}))


class DepartamentoAtencionBalconForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))


class GrupoAtencionBalconForm(FormModeloBase):
    from posgrado.models import DepartamentoAtencionBalcon
    # departamento_atencion = forms.ModelChoiceField(label=u'Departamento', required=True, queryset=DepartamentoAtencionBalcon.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12', 'readonly': 'readonly'}))
    nombre = forms.CharField(label="Nombre", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    lider = forms.ModelChoiceField(label='Lider', queryset=Persona.objects.none(), widget=forms.Select(attrs={'class': 'select2'}))
    integrantes = forms.ModelMultipleChoiceField(label='Integrantes', queryset=Persona.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'select2'}))


    # def set_departamento(self, departamento_id):
    #     from posgrado.models import DepartamentoAtencionBalcon
    #     self.fields['departamento_atencion'].queryset = DepartamentoAtencionBalcon.objects.filter(id=departamento_id)
    #     self.fields['departamento_atencion'].initial = [departamento_id]

    def edit(self, id_lider, id_integrantes=[]):
        self.fields['lider'].queryset = Persona.objects.filter(status=True, pk=id_lider)
        self.fields['lider'].initial = [id_lider]
        if id_integrantes:
            self.fields['integrantes'].queryset = Persona.objects.filter(status=True, pk__in=id_integrantes).exclude(pk=id_lider)
            self.fields['integrantes'].initial = id_integrantes

    def ocultar_edit(self):
        del self.fields['integrantes']


class IntegranteGrupoAtencionBalconForm(FormModeloBase):
    from posgrado.models import GrupoAtencionBalcon
    # grupo_atencion = forms.ModelChoiceField(label='Grupo de atención', required=True, queryset=GrupoAtencionBalcon.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    integrantes = forms.ModelMultipleChoiceField(label='Añadir Integrantes', queryset=Persona.objects.none(), widget=forms.SelectMultiple(attrs={'class': 'select2'}))


    def edit(self, id_integrantes):
        self.fields['integrantes'].queryset = Persona.objects.filter(status=True, pk__in=id_integrantes)
        self.fields['integrantes'].initial = id_integrantes

class GestionSolicitudBalconForm(FormModeloBase):
    from posgrado.models import GrupoAtencionBalcon, SolicitudBalcon, DepartamentoAtencionBalcon
    # solicitud = forms.ModelChoiceField(label=u'Solicitud', required=True, queryset=SolicitudBalcon.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    grupo_atencion = forms.ModelChoiceField(label='Departamento', required=True, queryset=GrupoAtencionBalcon.objects.all(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    detalle_gestion = forms.CharField(label='Detalle Adicional para la gestión', required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'col': '12', 'rows': '4'}))
    # adjunto = forms.FileField(label=u'Archivo Adicional', required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'col': '12', 'multiple': 'multiple'}))
    archivo = ExtFileField(label=u'Archivo Adicional', required=False, help_text=u'Tamaño Maximo permitido 5Mb, en formato pdf, jpg o png', ext_whitelist=(".pdf", ".jpeg", ".jpg", ".png"),max_upload_size=5242880, widget=forms.FileInput())


    def set_queryset(self, solicitud_id, grupo_id):
        from posgrado.models import SolicitudBalcon, GrupoAtencionBalcon
        # self.fields['solicitud'].queryset = SolicitudBalcon.objects.filter(pk=solicitud_id)
        # self.fields['solicitud'].initial = solicitud_id
        self.fields['grupo_atencion'].queryset = GrupoAtencionBalcon.objects.filter(pk=grupo_id)
        self.fields['grupo_atencion'].initial = grupo_id

class AsignarResponsableGestionForm(FormModeloBase):
    from posgrado.models import IntegranteGrupoAtencionBalcon
    responsable = forms.ModelChoiceField(label='Responsable', required=True, queryset=IntegranteGrupoAtencionBalcon.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    fecha_inicio_gestion = forms.DateField(label='Fecha de inicio de la gestión', required=True, widget=forms.DateInput(attrs={'class': 'form-control', 'col': '12', 'type': 'date'}))
    fecha_finaliza_gestion = forms.DateField(label='Fecha de finalización de la gestión', required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'col': '12', 'type': 'date'}))

    def init_queryset(self, id_grupo):
        from posgrado.models import IntegranteGrupoAtencionBalcon
        self.fields['responsable'].queryset = integrates = IntegranteGrupoAtencionBalcon.objects.filter(status=True,
                                                                                           grupo_atencion_id=id_grupo,
                                                                                           activo=True)
        self.fields['responsable'].initial = integrates.values_list('pk', flat=True)
        self.fields['fecha_inicio_gestion'].initial = datetime.now().date()

    def set_responsable(self, responsable_id):
        from posgrado.models import IntegranteGrupoAtencionBalcon
        self.fields['responsable'].queryset = IntegranteGrupoAtencionBalcon.objects.filter(pk=responsable_id)
        self.fields['responsable'].initial = responsable_id


class ResponderSolicitudGestionForm(FormModeloBase):
    respuesta = forms.CharField(label='Respuesta', required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'col': '12', 'rows': '4'}))
    archivo_respuesta = forms.FileField(label=u'Archivo Respuesta', required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'col': '12'}))


class TipoSolicitudBalconForm(FormModeloBase):
    nombre = forms.CharField(label="Nombre", required=True, widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}))
    descripcion = forms.CharField(label="Descripción", required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'col': '12', 'rows': '4'}))

class AsignaCoordinadorForm(FormModeloBase):
    coordinador = forms.ModelChoiceField(label='Coordinador', required=True, queryset=Persona.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))

    def set_coordinador(self, id_person):
        self.fields['coordinador'].queryset = Persona.objects.filter(pk=id_person)
        self.fields['coordinador'].initial = id_person


class EditarFechasEvaluacionForm(FormModeloBase):
    encuesta = forms.ModelChoiceField(queryset=EncuestaSatisfaccionDocente.objects.filter(status=True, activo=True).order_by('-id'),
                                      required=True, label=u'Encuesta de satisfacción',
                                      widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    materia = forms.CharField(required=True, label=u'Materia', widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    director = forms.CharField(required=True, label=u'Director', widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    coordinador = forms.CharField(required=True, label=u'Coordinador', widget=forms.TextInput(attrs={'class': 'imp-100', 'readonly': 'true'}))
    inicio = forms.DateField(label=u"Inicio", initial=datetime.now().date(), required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))
    fin = forms.DateField(label=u"Fin", initial=datetime.now().date(), required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col':'6'}))

    def editar(self):
        del self.fields['encuesta']
        del self.fields['director']
        del self.fields['coordinador']

    def editar_2(self):
        del self.fields['encuesta']


    def editar_3(self):
        del self.fields['director']
        del self.fields['coordinador']

TIPO_EVAL = (
    (0, u"--------------"),
    (1, u"Heteroevaluación"),
    (2, u"Autoevaluación"),
    (3, u"Evaluación de directivos"),
    (4, u"Encuesta de satisfacción"),
)

class AsignarFechasMasivoForm(FormModeloBase):
    tipo = forms.ChoiceField(choices=TIPO_EVAL, required=True, label=u'Tipo de evaluacion', widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))
    config = forms.BooleanField(initial=False, label=u"¿Click aquí si desea configurar por días?", required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '12'}))
    encuesta = forms.ModelChoiceField(queryset=EncuestaSatisfaccionDocente.objects.filter(status=True, activo=True).order_by('-id'),
                                      required=False, label=u'Encuesta de satisfacción',
                                      widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    inicio = forms.DateField(label=u"Inicio", required=False, widget=DateTimeInput({'col': '6'}))
    fin = forms.DateField(label=u"Fin", required=False, widget=DateTimeInput({'col': '6'}))
    dias = forms.IntegerField(label=u'Plazo en días', required=False, widget=forms.NumberInput(attrs={'class': 'imp-number', 'col': '4', 'style': 'with:30%'}))
    detalle = forms.CharField(required=False, label=u'Detalle de materias', widget=forms.Textarea({'rows': '5', 'readonly': 'true'}))

class ProcesarResultadosMasivoForm(FormModeloBase):
    detalle = forms.CharField(required=False, label=u'Detalle de materias', widget=forms.Textarea({'rows': '5', 'readonly': 'true'}))

class CatalogoClasificadorPresupuestarioFORM(FormModeloBase):
    descripcion = forms.CharField(label="Descripción", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    activo = forms.BooleanField(label="Activo", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))

class ClasificadorPresupuestarioFORM(FormModeloBase):
    from .models import CatalogoClasificadorPresupuestario
    catalogo = forms.ModelChoiceField(label="Catalogo", required=True, queryset=CatalogoClasificadorPresupuestario.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12',}))
    codigo_naturaleza = forms.CharField(label="Código Naturaleza", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3'}))
    codigo_grupo = forms.CharField(label="Código Grupo", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3'}))
    codigo_subgrupo = forms.CharField(label="Código Subgrupo", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3'}))
    codigo_rubro = forms.CharField(label="Código Rubro", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3'}))
    nombre = forms.CharField(label="Nombre", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    descripcion = forms.CharField(label="Descripción", required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'col': '12', 'rows': '4'}))

    def init_codigo_naturaleza(self, codigo_naturaleza):
        self.fields['codigo_naturaleza'].initial = codigo_naturaleza
        # self.fields['catalogo'].widget.attrs['readonly'] = True

    def init_codigo_grupo(self,codigo_naturaleza, codigo_grupo):
        pass
        # self.fields['codigo_naturaleza'].initial = codigo_naturaleza
        # self.fields['codigo_grupo'].initial = codigo_grupo
        # self.fields['catalogo'].widget.attrs['readonly'] = True
        # self.fields['codigo_naturaleza'].widget.attrs['readonly'] = True

    def set_queryset_catalogo(self, id_cat):
        from .models import CatalogoClasificadorPresupuestario
        self.fields['catalogo'].queryset = CatalogoClasificadorPresupuestario.objects.filter(pk=id_cat)
        self.fields['catalogo'].initial = id_cat

    def set_codigos(self, codigo_naturaleza, codigo_grupo='', codigo_subgrupo='', codigo_rubro=''):
        self.fields['codigo_naturaleza'].initial = codigo_naturaleza
        self.fields['codigo_grupo'].initial = codigo_grupo
        self.fields['codigo_subgrupo'].initial = codigo_subgrupo
        self.fields['codigo_rubro'].initial = codigo_rubro

    def clean(self):
        cleaned_data = super(ClasificadorPresupuestarioFORM, self).clean()
        codigo_naturaleza = cleaned_data.get('codigo_naturaleza', None)
        codigo_grupo = cleaned_data.get('codigo_grupo', None)
        codigo_subgrupo = cleaned_data.get('codigo_subgrupo', None)
        codigo_rubro = cleaned_data.get('codigo_rubro', None)
        if codigo_naturaleza is None:
            self.add_error('codigo_naturaleza', 'El código de naturaleza es requerido')
        if int(codigo_naturaleza) <= 0:
            self.add_error('codigo_naturaleza', 'El código de naturaleza debe ser un numero valido')
        if codigo_grupo:
            if int(codigo_grupo) <= 0:
                self.add_error('codigo_grupo', 'El código de grupo debe ser un numero valido')
        if codigo_subgrupo:
            if int(codigo_subgrupo) <= 0:
                self.add_error('codigo_subgrupo', 'El código de subgrupo debe ser un numero valido')
        if codigo_rubro:
            if int(codigo_rubro) <= 0:
                self.add_error('codigo_rubro', 'El código de rubro debe ser un numero valido')
        return cleaned_data

class CatalogoCuentaContableForm(FormModeloBase):
    descripcion = forms.CharField(label="Descripción", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    activo = forms.BooleanField(label="Activo", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '50%'}))


class CuentaContableFORM(FormModeloBase):
    from .models import CatalogoCuentaContable, CuentaContable
    catalogocuentacontable = forms.ModelChoiceField(label="Catalogo", required=True, queryset=CatalogoCuentaContable.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12',}))
    tipo = forms.ChoiceField(label="Tipo", required=True,  choices=[('', '---------')] + list(CuentaContable.TipoCuenta.choices), widget=forms.Select(attrs={'class': 'form-control', 'col': '2'}))
    codigo_categoria = forms.CharField(label="Código Categoria", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '2'}))
    codigo_grupo = forms.CharField(label="Código Grupo", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '2'}))
    codigo_subgrupo = forms.CharField(label="Código Subgrupo", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '2'}))
    codigo_rubro = forms.CharField(label="Código Rubro", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '2'}))
    codigo_subrubro = forms.CharField(label="Código Subrubro", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '2'}))
    nombre = forms.CharField(label="Nombre", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12'}))
    descripcion = forms.CharField(label="Descripción", required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'col': '12', 'rows': '3'}))
    carrera = forms.ModelChoiceField(label="Carrera", required=False, queryset=Carrera.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))


    def set_queryset_catalogo(self, id_cat):
        from .models import CatalogoCuentaContable
        self.fields['catalogocuentacontable'].queryset = CatalogoCuentaContable.objects.filter(pk=id_cat)
        self.fields['catalogocuentacontable'].initial = id_cat
        self.fields['catalogocuentacontable'].widget.attrs['readonly'] = True
        # self.fields['catalogocuentacontable'].widget.attrs['disabled'] = True

    def set_codigos(self, codigo_categoria, codigo_grupo='', codigo_subgrupo='', codigo_rubro='', codigo_subrubro=''):
        self.fields['codigo_categoria'].initial = codigo_categoria
        self.fields['codigo_grupo'].initial = codigo_grupo
        self.fields['codigo_subgrupo'].initial = codigo_subgrupo
        self.fields['codigo_rubro'].initial = codigo_rubro
        self.fields['codigo_subrubro'].initial = codigo_subrubro

    def set_carrera(self, id_carrera):
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=id_carrera)
        self.fields['carrera'].initial = id_carrera

    def clean(self):
        cleaned_data = super(CuentaContableFORM, self).clean()
        codigo_categoria = cleaned_data.get('codigo_categoria', None)
        codigo_grupo = cleaned_data.get('codigo_grupo', None)
        codigo_subgrupo = cleaned_data.get('codigo_subgrupo', None)
        codigo_rubro = cleaned_data.get('codigo_rubro', None)
        codigo_subrubro = cleaned_data.get('codigo_subrubro', None)
        if codigo_categoria is None:
            self.add_error('codigo_categoria', 'Debe ingresar un código de categoria')
            raise forms.ValidationError('Debe ingresar un código de categoria')
        if int(codigo_categoria) <= 0:
            self.add_error('codigo_categoria', 'Debe ingresar un código de categoria valido')
        if codigo_grupo:
            if int(codigo_grupo) <= 0:
                self.add_error('codigo_grupo', 'Debe ingresar un código de grupo valido')
        if codigo_subgrupo:
            if int(codigo_subgrupo) <= 0:
                self.add_error('codigo_subgrupo', 'Debe ingresar un código de subgrupo valido')
        if codigo_rubro:
            if int(codigo_rubro) <= 0:
                self.add_error('codigo_rubro', 'Debe ingresar un código de rubro valido')
        if codigo_subrubro:
            if int(codigo_subrubro) <= 0:
                self.add_error('codigo_subrubro', 'Debe ingresar un código de subrubro valido')
        return cleaned_data


class FlujoEfectivoForm(FormModeloBase):
    anio = forms.CharField(label=u"Año", required=False,  widget=forms.TextInput(attrs={'class': 'imp-anio', 'col': '6'}))
    mes = forms.ChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES, widget=forms.Select(attrs={ 'col': '6'}))
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False, label=u"Descripción")

    def cargar_meses_aprobados(self,anio_actual):
        from posgrado.models import BalanceCosto,MESES_CHOICES
        self.fields['anio'].widget.attrs['readonly'] = True
        eBalanceCosto = BalanceCosto.objects.filter(status=True, anio=anio_actual, estado=1).values_list('mes',flat=True).distinct().order_by('mes')
        # Set the choices for the 'mes' field
        MESES_CHOICES = [(mes, dict(MESES_CHOICES).get(mes)) for mes in eBalanceCosto if mes in dict(MESES_CHOICES).keys()]
        self.fields['mes'].choices = MESES_CHOICES

class AsociarCuentaFlujoEfectivoTotalForm(FormModeloBase):
    configuracioncampo = forms.ChoiceField(label="Tipo", required=True, choices=CuentaContable.ConfiguracionCampoValor.choices, widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))

class CuentaEstadoResultadoIntegralForm(FormModeloBase):
    cuentacontable =  forms.ModelChoiceField(label="Cuenta contable", required=True, queryset=CuentaContable.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))

    def set_cuentacontable(self, id_cuenta):
        self.fields['cuentacontable'].queryset = CuentaContable.objects.filter(pk=id_cuenta)
        self.fields['cuentacontable'].initial = id_cuenta


class EstadoResultadoIntegralFORM(FormModeloBase):

    anio = forms.CharField(label=u"Año", required=False, widget=forms.TextInput(attrs={'class': 'imp-anio', 'col': '6'}))
    mes = forms.MultipleChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES,widget=forms.SelectMultiple(attrs={'col': '6', 'class': 'select2'}))

    def init_meses(self):
        self.fields['mes'].choices = [(0, 'Todos')] + list(MESES_CHOICES)

    def init_meses_x_anio(self, anio):
        from .models import FlujoEfectivoMensual
        query_meses = FlujoEfectivoMensual.objects.filter(status=True, anio=anio, estado=FlujoEfectivoMensual.TipoEstado.VALIDADO).values_list('mes', flat=True).distinct()
        meses_filter = [(id_mes, mes) for id_mes, mes in MESES_CHOICES if id_mes in query_meses]
        self.fields['mes'].choices = [(0, 'Todos')] + meses_filter
        self.fields['anio'].widget.attrs['readonly'] = True


    def set_meses(self):
        meses_seleccionados = self.cleaned_data.get('mes')
        if '0' in meses_seleccionados:
            return [choice[0] for choice in MESES_CHOICES if choice[0] != '0']
        return meses_seleccionados

    def set_meses_f(self, meses):
        self.fields['mes'].choices = meses + [(0, 'Todos')]
        self.fields['mes'].initial = meses

    def clean(self):
        cleaned_data = super(EstadoResultadoIntegralFORM, self).clean()
        anio = cleaned_data.get('anio', None)
        if anio is None:
            self.add_error('anio', 'Debe ingresar un año')
        if int(anio) <= 2015:
            self.add_error('anio', 'Debe ingresar un año valido')
        return cleaned_data


class CuentaEjecucionPresupuestariaFORM(FormModeloBase):
    cuentacontable =  forms.ModelChoiceField(label="Cuenta contable", required=True, queryset=CuentaContable.objects.none(), widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))

    def set_cuentacontable(self, id_cuenta):
        self.fields['cuentacontable'].queryset = CuentaContable.objects.filter(pk=id_cuenta)
        self.fields['cuentacontable'].initial = id_cuenta

class EjecucionPresupuestariaFORM(FormModeloBase):
    anio = forms.CharField(label=u"Año", required=False, widget=forms.TextInput(attrs={'class': 'imp-anio', 'col': '6'}))
    mes = forms.MultipleChoiceField(label=u"Mes", required=False, choices=MESES_CHOICES,widget=forms.SelectMultiple(attrs={'col': '6', 'class': 'select2'}))

    def init_meses_x_anio(self, anio):
        from .models import FlujoEfectivoMensual
        query_meses = FlujoEfectivoMensual.objects.filter(status=True, anio=anio, estado=FlujoEfectivoMensual.TipoEstado.VALIDADO).values_list('mes', flat=True).distinct()
        meses_filter = [(id_mes, mes) for id_mes, mes in MESES_CHOICES if id_mes in query_meses]
        self.fields['mes'].choices = [(0, 'Todos')] + meses_filter
        self.fields['anio'].widget.attrs['readonly'] = True

    def set_meses(self):
        meses_seleccionados = self.cleaned_data.get('mes')
        if '0' in meses_seleccionados:
            return [choice[0] for choice in MESES_CHOICES if choice[0] != '0']
        return meses_seleccionados

    def set_meses_f(self, meses):
        self.fields['mes'].choices = meses + [(0, 'Todos')]
        self.fields['mes'].initial = meses

    def clean(self):
        cleaned_data = super(EjecucionPresupuestariaFORM, self).clean()
        anio = cleaned_data.get('anio', None)
        if anio is None:
            self.add_error('anio', 'Debe ingresar un año')
        if int(anio) <= 2015:
            self.add_error('anio', 'Debe ingresar un año valido')
        return cleaned_data


class PreguntaSeguimientoGraduadoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False, label=u"Descripción")


class PeriodoEncuestaForm(FormModeloBase):
    from posgrado.models import SagPosgradoPeriodo
    anio = forms.CharField(label=u"Año", required=True, widget=forms.TextInput(attrs={'class': 'imp-anio', 'col': '6'}))
    tipo = forms.ChoiceField(label="Tipo", required=True, choices=SagPosgradoPeriodo.TipoPeriodoEncuesta.choices, widget=forms.Select(attrs={'class': 'form-control', 'col': '6'}))
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False, label=u"Descripción")
    fechaInicio = forms.DateField(label=u"Fecha inicio", required=True, widget=DateTimeInput({'col': '6'}))
    fechaFin = forms.DateField(label=u"Fecha fin", required=True, widget=DateTimeInput({'col': '6'}))
    estado = forms.BooleanField(label=u"¿Activo?", required=False, widget=forms.CheckboxInput(attrs={'class': 'form-controljs-switch', 'col': '12'}))



class GrupoEncuestaForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    descripcion = forms.CharField(widget=forms.Textarea(attrs={'rows': '3', 'col': '12'}), required=False, label=u"Descripción")
    orden = forms.IntegerField(label=u'Orden', required=True, widget=forms.NumberInput(attrs={'class': 'imp-number', 'col': '4', 'style': 'with:30%'}))



class DatosDataGraduadoForm(forms.Form):
    pais = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.all(), required=True,  widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects.all(), required=False, widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    canton = forms.ModelChoiceField(label=u"Ciudad  de residencia", queryset=Canton.objects.all(), required=False, widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    direccion = forms.CharField(label=u'Calle principal', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'4'}))
    direccion2 = forms.CharField(label=u'Calle secundaria', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'4'}))
    ciudadela = forms.CharField(label=u'Ciudadela', max_length=100, required=False, widget=forms.TextInput(attrs={'col': '4'}))
    num_direccion = forms.CharField(label=u'Número de casa', max_length=15, required=True,   widget=forms.TextInput(attrs={'col':'3'}))
    referencia = forms.CharField(label=u'Referencia', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'9'}))
    telefono_conv = forms.CharField(label=u'Teléfono domicilio (fijo)', max_length=15, required=False, widget=forms.TextInput(attrs={'col':'3'}))
    telefono = forms.CharField(label=u'Teléfono celular', max_length=15, required=True, widget=forms.TextInput(attrs={'col':'3'}))
    sector = forms.CharField(label=u'Sector', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'3'}))
    zona = forms.ChoiceField(label=u"Zona de residencia", choices=ZONA_DOMICILIO, required=True, widget=forms.Select(attrs={'col':'3','class':'select2'}))
    email = forms.CharField(label=u"Email personal", max_length=240, required=True,widget=forms.TextInput(attrs={'col':'12'}))

    def editar(self, persona):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)



class PersonaNuevaDatosDataGraduadoForm(forms.Form):
    pais = forms.ModelChoiceField(label=u"País de residencia", queryset=Pais.objects.all(), required=True,  widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    provincia = forms.ModelChoiceField(label=u"Provincia de residencia", queryset=Provincia.objects.all(), required=False, widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    canton = forms.ModelChoiceField(label=u"Ciudad  de residencia", queryset=Canton.objects.all(), required=False, widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia de residencia", queryset=Parroquia.objects.all(), required=False, widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    direccion = forms.CharField(label=u'Calle principal', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'4'}))
    direccion2 = forms.CharField(label=u'Calle secundaria', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'4'}))
    ciudadela = forms.CharField(label=u'Ciudadela', max_length=100, required=False, widget=forms.TextInput(attrs={'col': '4'}))
    num_direccion = forms.CharField(label=u'Número de casa', max_length=15, required=True,   widget=forms.TextInput(attrs={'col':'3'}))
    referencia = forms.CharField(label=u'Referencia', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'9'}))
    telefono_conv = forms.CharField(label=u'Teléfono domicilio (fijo)', max_length=15, required=False, widget=forms.TextInput(attrs={'col':'3'}))
    telefono = forms.CharField(label=u'Teléfono celular', max_length=15, required=True, widget=forms.TextInput(attrs={'col':'3'}))
    sector = forms.CharField(label=u'Sector', max_length=100, required=True, widget=forms.TextInput(attrs={'col':'3'}))
    zona = forms.ChoiceField(label=u"Zona de residencia", choices=ZONA_DOMICILIO, required=True, widget=forms.Select(attrs={'col':'3','class':'select2'}))
    email = forms.CharField(label=u"Email personal", max_length=240, required=True,widget=forms.TextInput(attrs={'col':'12'}))

    def editar(self, persona):
        self.fields['provincia'].queryset = Provincia.objects.filter(pais=persona.pais)
        self.fields['canton'].queryset = Canton.objects.filter(provincia=persona.provincia)
        self.fields['parroquia'].queryset = Parroquia.objects.filter(canton=persona.canton)
