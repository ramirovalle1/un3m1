from datetime import datetime, timedelta
from django import forms
from django.forms import ValidationError, DateTimeInput, CheckboxInput
from django.db.models import Q
from unidecode import unidecode

from cita.models import Requisito, ServicioCita, TurnoCita, PRIORIDAD_SERVICIO, TIPO_RESPONSABLE, \
    ResponsableServicioCita, HorarioServicioCita, RequisitoServicioCita, ESTADOS_DOCUMENTOS_SOLICITUD, \
    ESTADO_SOLICITUD_SERVICIO, DepartamentoServicio, TIPO_ATENCION, TIPO_PROCESOS, ServicioConfigurado, MotivoCita, \
    TIPO_PUBLICACION, UBICACION, \
    NoticiasVinculacion, ResponsableGrupoServicio, CardInformativo, \
    Proceso, NIVEL_ACADEMICO, InformePsicologico, TIPO_INSTITUCION_LABORAL, TIPO_INFORME_PSICOLOGICO, EstructuraInforme, \
    TIPO_INFORME_PSICOLOGICO, CabRefuerzoAcademico, DetRefuerzoAcademico, TerminosCondicion, CargaImgvin, TIPO_WEBINAR, \
    CONF_SERVICIOS, TIPO_NIVEL_ACADEMICO
from sagest.models import Departamento, Bloque, SeccionDepartamento
from core.custom_forms import FormModeloBase
from sga.forms import ExtFileField
from sga.funciones import validarcedula, generar_nombre
from sga.models import Persona, DIAS_CHOICES, PerfilUsuario, PersonaDatosFamiliares, TIPOS_IDENTIFICACION, Sexo, Discapacidad, InstitucionBeca,ParentescoPersona,NivelTitulacion,CENTRO_CUIDADO, InstitucionesColegio
from utils.filtros_genericos import consultarPersona
from socioecon.models import FormaTrabajo

ESTADO_CULMINAR = (
    (2, u'Anulado'),
    (5, u'Finalizado'),
    (6, u'En trámite'),
)

TIPO_SEGMENTACION = (
    (1, u'Top izquierda'),
    (2, u'Top derecha'),
    (3, u'Centro'),
    (4, u'Centro combinado')

)

TIPO_INSTITUCION_LABORAL = (
    (0, u'--------'),
    (1, u"SECTOR PÚBLICO"),
    (2, u"SECTOR PRIVADO"),
)

class DepartamentoServicioForm(FormModeloBase):
    nombre = forms.CharField(label=u'Titulo', max_length=100, required=True, widget=forms.TextInput({'placeholder': 'Ejem. Servicios asistenciales', 'col': '6'}))
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.filter(tipo=1, status=True, integrantes__isnull=False).distinct().order_by('nombre'), required=True, label=u'Departamento',
                                          widget=forms.Select({'col': '6', 'class': 'select2'}))
    gestion = forms.ModelChoiceField(queryset=SeccionDepartamento.objects.select_related().
                                     filter(status=True), required=False,
                                     label=u'Gestión', widget=forms.Select({'col': '6', 'class': 'select2'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'separator3': True}))
    nombresistema = forms.CharField(required=False, label=u'Nombre del sistema', widget=forms.TextInput({'placeholder': 'Descripción del nombre', 'col': '6'}))
    tiposistema = forms.CharField(required=False, label=u'Tipo del sistema',
                                    widget=forms.TextInput({'placeholder': 'Descripción del tipo', 'col': '6'}))
    url_entrada = forms.CharField(required=False, label=u'Url del sistema',
                                  widget=forms.TextInput({'placeholder': 'Descripción del url', 'col': '6'}))
    logonavbar = forms.FileField(label=u'Logo del Navbar', required=False,
                                 help_text=u'Tamaño Máximo permitido 2Mb, en formato  png',
                                 widget=forms.FileInput(attrs={'class': 'dropify', 'data-max-file-size': '2M',
                                                               'accept': '.png, .jpg, .jpeg'}))

    logofooter = forms.FileField(label=u'Logo del Footer', required=False,
                                 help_text=u'Tamaño Máximo permitido 2Mb, en formato  png',
                                 widget=forms.FileInput(attrs={'class': 'dropify', 'data-max-file-size': '2M',
                                                               'accept': '.png, .jpg, .jpeg'}))

    def validador(self, id=0):
        ban, nombre = True, self.cleaned_data['nombre'].upper()
        if DepartamentoServicio.objects.filter(nombre__unaccent=nombre, status=True).exclude(id=id).exists():
            self.add_error('nombre', 'Registro que desea ingresar ya existe.')
            ban = False
        if DepartamentoServicio.objects.filter(gestion=self.cleaned_data['gestion'], status=True).exclude(
                id=id).exists():
            self.add_error('gestion', 'Registro con gestion ya existe.')
            ban = False
        return ban

class ServicioCitaForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'placeholder': 'Ejem. Asesoría .'}))
    # responsable = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True, ), required=True,
    #                                      label=u'Coordinador', widget=forms.Select(attrs={'col': '6','class': 'select2'}))

    responsable = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True, ), required=False,
                                         label=u'Coordinador', widget=forms.Select(attrs={'col': '6'}))

    tipo_atencion = forms.ChoiceField(choices=TIPO_ATENCION, required=True, label=u'Tipo atención',widget=forms.Select(attrs={'col': '6'}))
    link_atencion = forms.CharField(required=False, label=u'Enlace de atención', widget=forms.TextInput({'placeholder': 'Ejem. https://unemi-reunion.zoom','col':'6'}))
    bloque = forms.ModelChoiceField(queryset=Bloque.objects.filter(status=True).distinct().order_by('descripcion'), required=False, label=u'Bloque de atención', widget=forms.Select({'col':'6'}))
    lugar = forms.CharField(required=False, label=u'Ubicación dentro de bloque', widget=forms.TextInput({'placeholder': 'Ingresar en este formato - Planta | Oficina','col':'6'}))
    gestion_servicio = forms.ChoiceField(choices=CONF_SERVICIOS, required=False, label=u'Configuración extras servicio',
                                      widget=forms.Select(attrs={'col': '6'}))
    portada = ExtFileField(label=u'Portada', required=False,help_text=u'Tamaño maximo permitido 100kb, dimensión recomendada 740x500 píxeles en formato jpg, jpeg, png',ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=1124304, widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    descripcion = forms.CharField(required=False, label=u'Descripción',widget=forms.Textarea(attrs={'separator3': True , 'col': '6'}))
    cuerpodescripcion = forms.CharField(label=u'Contenido de servicio', required=False,
                                  widget=forms.Textarea(attrs={'separator3': True , 'col': '6'}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'2'}))
    motivos = forms.ModelMultipleChoiceField(label=u'Motivo de cita',
                                        queryset=MotivoCita.objects.filter(status=True),
                                        required=False, widget=forms.SelectMultiple(attrs={'col': '10', 'class': 'select2'}))

    #
    def validador(self, id=0):
        ban, nombre = True, self.cleaned_data['nombre'].upper()
        if ServicioCita.objects.filter(nombre__unaccent=nombre,status=True).exclude(id=id).exists():
            self.add_error('nombre', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban



class ServicioConfiguradoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre de configuración', max_length=100, required=True, widget=forms.TextInput({'placeholder': 'Ejem. Configuración #1','col':'6'}))
    # departamento = forms.ModelChoiceField(queryset=Departamento.objects.filter(status=True), required=True, label=u'Departamento', widget=forms.Select({'col':'6'}))
    prioridad = forms.ChoiceField(choices=PRIORIDAD_SERVICIO,initial=2, required=True, label=u'Prioridad', widget=forms.Select({'col':'6'}))
    # responsable = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True,), required=False, label=u'Responsable', widget=forms.Select(attrs={'col':'6'}))
    # portada = ExtFileField(label=u'Portada', required=False,help_text=u'Tamaño maximo permitido 100kb, dimensión recomendada 740x500 píxeles en formato jpg, jpeg, png',ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=1124304, widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    # descripcion = forms.CharField(required=False, label=u'Descripción',widget=forms.Textarea(attrs={'separator3': True}))
    numdiasinicio = forms.IntegerField(label=u'Inicios de dias para agendar', initial=0, required=True,
                                       widget=forms.TextInput(
                                           attrs={'class': 'input-number', 'number': 'True', 'decimal': '0', 'col': '6',
                                                  'controlwidth': '150px'}))
    numdias = forms.IntegerField(label=u'Fin de días para agendar', initial=1, required=True, widget=forms.TextInput(attrs={'class': 'input-number', 'number':'True', 'decimal': '0', 'col':'6','controlwidth':'150px'}))
    cupo = forms.IntegerField(label=u'Cupo por turno', initial=1, required=True, widget=forms.TextInput(attrs={'class': 'input-number', 'number':'True','decimal': '0', 'col': '6','controlwidth': '150px'}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'data-switchery': 'true','col':'6'}))
    soloadministrativo = forms.BooleanField(initial=False, required=False, label=u'Solo administrativos',
                                 widget=forms.CheckboxInput(attrs={'data-switchery': 'true', 'col': '6'}))
    def validador(self,id=0, ids=0):
        ban, nombre = True, self.cleaned_data['nombre']
        if ServicioConfigurado.objects.filter(nombre__unaccent=nombre,serviciocita_id=ids, status=True).exclude(id=id).exists():
            self.add_error('nombre', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban

class ResponsableServicioForm(FormModeloBase):
    responsable = forms.ModelChoiceField(label=u'Responsable', queryset=Persona.objects.select_related().filter(status=True,), required=True, widget=forms.Select(attrs={'col': '6'}))
    tipo = forms.ChoiceField(choices=TIPO_RESPONSABLE[1:], required=True, label=u'Tipo', widget=forms.Select(attrs={'col': '4'}))

class RequisitoServicioForm(FormModeloBase):
    requisito = forms.ModelChoiceField(label=u'Requisito', queryset=Requisito.objects.select_related().filter(status=True,), required=True, widget=forms.Select(attrs={'col': '10'}))
    # archivo = forms.BooleanField(initial=False, required=False, label=u'¿Subir Archivo?', widget=forms.CheckboxInput(attrs={'col': '3'}))
    # opcional = forms.BooleanField(initial=False, required=False, label=u'¿Opcional?', widget=forms.CheckboxInput(attrs={'col': '2'}))

    def validador(self, id=0):
        ban, requisito = True, self.cleaned_data['requisito']
        if RequisitoServicioCita.objects.filter(servicio_id=id,requisito=requisito, status=True).exclude(id=id).exists():
            self.add_error('requisito', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban

class TurnoCitaForm(FormModeloBase):
    comienza = forms.TimeField(label=u"Comienza", required=True, initial=str(datetime.now().time().strftime("%H:%M")),
                               widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','col':'6'}))
    termina = forms.TimeField(label=u"Termina", required=True, initial=str(datetime.now().time().strftime("%H:%M")),
                              widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','col':'6'}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'id':'id_mostrar','name':'mostrar', 'data-switchery': 'true'}))

    def validador(self, id=0):
        ban, comienza, termina = True, self.cleaned_data['comienza'], self.cleaned_data['termina']
        if comienza > termina:
            self.add_error('comienza', 'Campo inicio no tiene que ser mayo a campo final.')
            self.add_error('termina', 'Campo final no tiene que ser menor a campo inicio.')
            ban = False
        if comienza == termina:
            self.add_error('comienza', 'Inicio no tiene que ser igual a final.')
            self.add_error('termina', 'Final no tiene que ser igual a inicio.')
            ban = False
        if TurnoCita.objects.filter(status=True, comienza=comienza,termina=termina).exclude(id=id).exists():
            self.add_error('comienza', 'Registro que desea ingresar ya existe.')
            self.add_error('termina', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban

class RequisitoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'placeholder': 'Ejem. Cédula de identidad.'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'placeholder': 'Ejem. El tamaño de documento debe ser el real, no tamñano A4 u otros..'}))

    def validador(self, id=0):
        ban, nombre =True, self.cleaned_data['nombre'].upper()
        if Requisito.objects.filter(nombre__unaccent=nombre, status=True).exclude(id=id).exists():
            # raise forms.ValidationError('Registro que desea ingresar ya existe.')
            self.add_error('nombre', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban

class HorarioServicioForm(FormModeloBase):
    responsableservicio = forms.ModelChoiceField(label=u"Responsable", required=True,
                                        queryset=ResponsableServicioCita.objects.filter(status=True, activo=True),
                                        widget=forms.Select(attrs={}))
    fechainicio = forms.DateField(label=u"Fecha Inicio",
                                  widget=DateTimeInput(format='%d-%m-%Y',
                                                       attrs={'class': 'selectorfecha', 'col': '6'}))
    fechafin = forms.DateField(label=u"Fecha Fin",
                               widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '6'}))
    tipo_atencion = forms.ChoiceField(choices=TIPO_ATENCION, required=True, label=u'Tipo atenciónes',widget=forms.Select(attrs={'col': '6'}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'id':'id_mostrar','name':'mostrar', 'data-switchery': 'true','col':'6'}))

    def validador(self,id=0 ,idservicio=0, dia=0, turno=0):
        ban, fechainicio, fechafin, responsableservicio  = (True, self.cleaned_data['fechainicio'],
                                                            self.cleaned_data['fechafin'], self.cleaned_data['responsableservicio'])
        # if HorarioServicioCita.objects.filter(responsableservicio__servicio_id=idservicio,
        #                                       dia=dia,
        #                                       fechainicio=fechainicio,
        #                                       fechafin=fechafin,
        #                                       turno_id=turno,
        #                                       status=True).exclude(id=id).exists():

        if HorarioServicioCita.objects.filter(
                    Q(responsableservicio__servicio_id=idservicio) &
                    Q(responsableservicio=responsableservicio) &
                    Q(dia=dia, fechainicio=fechainicio, fechafin=fechafin, turno_id=turno),
                    status=True
            ).exclude(id=id).exists():
            self.add_error('fechainicio', 'Existe un horario con la misma fecha y turno.')
            self.add_error('fechafin', 'Existe un horario con la misma fecha y turno.')
            self.add_error('responsableservicio', 'Existe un horario con el mismo responsable asignado.')
            ban = False
        return ban

class FinalizaCitaForm(FormModeloBase):
    estado = forms.ChoiceField(label=u"Estado", initial=6, choices=ESTADO_CULMINAR, required=True, widget=forms.Select(attrs={'col': '6'}))
    finalizar = forms.BooleanField(label=u"¿Finalizar cita principal?", required=False,  widget=forms.CheckboxInput(attrs={'col': '6', 'data-switchery': True, 'class': 'mt-2'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.Textarea(attrs={'formwidth': '100%', 'separator3': True, 'style':'resize:none'}))
    asistio = forms.BooleanField(initial=False, required=False, label=u'¿Asistió?', widget=forms.CheckboxInput(attrs={'col': '6', 'check': 'True','id':'id_asistio','class':'mt-2'}))
    noasistio = forms.BooleanField(initial=False, required=False, label=u'¿No Asistió?', widget=forms.CheckboxInput(attrs={'col': '6', 'check': 'True','class':'mt-2'}))

class ValidarCitaForm(FormModeloBase):
    estado = forms.ChoiceField(label=u'Estado', choices=ESTADOS_DOCUMENTOS_SOLICITUD[1:4], required=True, widget=forms.Select(attrs={'col': '3'}))
    observacion = forms.CharField(required=False, label=u'Observación', widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Describa una observación.'}))

class SubirRequisitoForm(FormModeloBase):
    archivo = ExtFileField(label=u'Archivo', required=True, help_text=u'Tamaño maximo permitido 4Mb y formato de archivo .pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'class':'p-1 text-secondary fs-6 ', 'col':'9'}))

    def validador(self, estado):
        ban=True
        if estado == 1:
            self.add_error('archivo', 'Archivo que intenta actualizar ya fue aprobado.')
            ban = False
        return ban

class GestionServicioCitaForm(FormModeloBase):
    observacion = forms.CharField(required=True, label=u'Observación', widget=forms.Textarea(attrs={'rows':'3', 'placeholder': 'Describa una observación.'}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?',
                                 widget=forms.CheckboxInput(attrs={'data-switchery': 'true', 'col': '3'}))
    archivo = ExtFileField(
        label=u'Archivo',
        required=False,
        help_text=u'Tamaño máximo permitido 10Mb y formato de archivo .pdf',
        ext_whitelist=(".pdf",),
        max_upload_size=10485760,  # 10 MB
        widget=forms.FileInput(attrs={'class': 'p-1 text-secondary fs-6 ', 'input_file': True})
    )
    # archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño maximo permitido 4Mb y formato de archivo .pdf', ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(attrs={'class':'p-1 text-secondary fs-6 ', 'input_file':True}))


class CitaEmergenteForm(FormModeloBase):
    persona = forms.ModelChoiceField(queryset=Persona.objects.filter(status=True),
                                     required=False, label='Persona', widget=forms.Select(attrs={'col':'12'}))
    perfil = forms.ModelChoiceField(queryset=PerfilUsuario.objects.filter(status=True),
                                     required=False, label=u'Perfil', widget=forms.Select(attrs={'col':'12','class':'select2'}))
    servicio = forms.ModelChoiceField(queryset=ServicioConfigurado.objects.filter(status=True).distinct(),
                                      required=True, label=u'Servicio',
                                      widget=forms.Select({'col': '12', 'class': 'select2'}))
    persona_responsable = forms.ModelChoiceField(queryset=Persona.objects.select_related().filter(status=True),
                                                 required=False, label=u'Responsable',
                                                 widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    tipo_atencion = forms.ChoiceField(choices=TIPO_ATENCION, initial=1, required=True, label=u'Tipo Atención',widget=forms.Select(attrs={'col': '6','class':'select2'}))
    comienza = forms.TimeField(label=u"Hora de la Cita", required=True, initial=str(datetime.now().time().strftime("%H:%M")),
                               widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'col': '3'}))

    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Has reservado para algún familiar?',
                                 widget=forms.CheckboxInput(attrs={ 'col': '6','data-switchery': True}))

    personafamiliar = forms.ModelChoiceField(queryset=PersonaDatosFamiliares.objects.select_related().filter(status=True),
                                             required=False, label=u'Seleccione Familiar',
                                             widget=forms.Select(
                                                 attrs={'col': '6', 'class': 'select2', 'disabled': ''}))

class CargaImgvinForm(FormModeloBase):
    imagen = forms.FileField(
        label='Agregar imagen',
        required=False,
        help_text='Tamaño Máximo permitido 2Mb, en formato jpg, jpeg, png',
        widget=forms.FileInput(attrs={'col': '12', 'accept': '.png, .jpg, .jpeg', 'dropify': True})
    )
    descripcion = forms.CharField(
        label='Descripción de la imagen',
        max_length=100,
        required=True,
        widget=forms.Textarea(attrs={'placeholder': 'Describa el título de imagen', 'col': '12'})
    )
    # enlace_imagen = forms.CharField(
    #     label='Enlace de la imagen',
    #     max_length=255,
    #     required=False,
    #     widget=forms.TextInput(attrs={'placeholder': 'Ingrese la ruta de la imagen', 'col': '12'})
    # )


    def validador(self, idpadre, id=0):
        ban, descripcion = True, self.cleaned_data['descripcion'].upper()
        if CargaImgvin.objects.filter(descripcion__icontains=descripcion, departamentoservicio_id=idpadre,status=True).exclude(
                id=id).exists():
            self.add_error('descripcion', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban


class MotivoCitaForm(FormModeloBase):
    # codigo = forms.CharField(label=u'Codigo', max_length=100, required=True,
    #                               widget=forms.TextInput({'placeholder': 'Describa el Codigo del motivo principal', 'col': '3'}))

    descripcion = forms.CharField(label=u'Motivo cita', max_length=300, required=True,
                             widget=forms.Textarea({'placeholder': 'Describa el motivo de consultas', 'col': '9'}))


    def validador(self, idpadre, id=0):
        ban, descripcion =True, self.cleaned_data['descripcion'].upper()
        if MotivoCita.objects.filter(descripcion__unaccent=descripcion, departamentoservicio_id=idpadre).exclude(id=id).exists():
            # raise forms.ValidationError('Registro que desea ingresar ya existe.')
            self.add_error('descripcion', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban

# class ServicioMotivoCitaForm(FormModeloBase):
#     motivocita = forms.ModelChoiceField(label=u'Motivo de cita', queryset=ServicioMotivoCita.objects.select_related().filter(status=True,), required=True, widget=forms.Select(attrs={'col': '10', 'class': 'select2'}))
#
#     def validador(self, id=0):
#         ban, motivocita = True, self.cleaned_data['motivocita']
#         if ServicioMotivoCita.objects.filter(servicio_id=id, motivocita=motivocita, status=True).exclude(
#                 id=id).exists():
#             self.add_error('motivocita', 'Registro que desea ingresar ya existe.')
#             ban = False
#         return ban


# class InformePsicologicoForm(FormModeloBase):
#
#     niveltitulacion = forms.ModelChoiceField(queryset=NivelTitulacion.objects.filter(status=True), required=True, label=u'Nivel Académico',
#                                        widget=forms.Select(attrs={'col': '6'}))
#
#     motivoconsulta = forms.ModelChoiceField(label=u"Motivo Consulta", queryset=MotivoCita.objects.filter(status=True), required=True,
#                                   widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
#
#     institucioneducativa = forms.ModelChoiceField(queryset=InstitucionesColegio.objects.filter(status=True),
#                                                   required=False,
#                                                   label=u'Institucion Educativa',
#                                                   widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
#
#     grado = forms.IntegerField(label=u'Grado', initial=0, required=False, widget=forms.NumberInput(
#         attrs={'class': 'input_number', 'input_number': True, 'col': '6', 'placeholder': '0', 'controlwidth': '50%'}))
#
#     descripcionmotivoconsulta = forms.CharField(label=u"Descripción de Consulta", required=True,
#                                      widget=forms.Textarea(attrs={'col': '12', 'rows': '3','placeholder':'Detallar Motivo de Consulta'}))
#
#     archivo = ExtFileField(label=u'Archivo de Consentimiento informado', required=False,
#                            help_text=u'Tamaño máximo permitido 4MB y formato de archivo .pdf',
#                            ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(
#             attrs={'class': 'p-1 text-secondary fs-6 ', 'input_file': True, 'col': '9'}),
#                            )
class InformePsicologicoForm(FormModeloBase):
    niveltitulacion = forms.ChoiceField(choices=TIPO_NIVEL_ACADEMICO, required=True, label=u'Nivel Académico',
                                             widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    # niveltitulacion = forms.ModelChoiceField(queryset=NivelTitulacion.objects.filter(status=True), required=True,
    #                                              label=u'Nivel Académico',
    #                                              widget=forms.Select(attrs={'col': '6'}))

    motivoconsulta = forms.ModelChoiceField(label=u"Motivo Consulta",
                                                queryset=MotivoCita.objects.filter(status=True), required=False,
                                                widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))

    institucioneducativa = forms.CharField(required=False,
                                           label=u'Institución Educativa',
                                           widget=forms.TextInput(attrs={'col': '6', 'class': 'input-text',
                                                                         'placeholder': 'Ingrese el nombre de la institución'}))
    # institucioneducativa = forms.ModelChoiceField(queryset=InstitucionesColegio.objects.filter(status=True),
    #                                                   required=False,
    #                                                   label=u'Institucion Educativa',
    #                                                   widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))

    grado = forms.IntegerField(label=u'Grado', initial=0, required=False, widget=forms.NumberInput(
            attrs={'class': 'input_number', 'input_number': True, 'col': '6', 'placeholder': '0',
                   'controlwidth': '50%'}))

    descripcionmotivoconsulta = forms.CharField(label=u"Descripción de Consulta", required=False,
                                                    widget=forms.Textarea(attrs={'col': '12', 'rows': '3',
                                                                                 'placeholder': 'Detallar Motivo de Consulta'}))

    archivo = ExtFileField(label=u'Archivo de Consentimiento informado', required=False,
                           help_text=u'Tamaño máximo permitido 4MB y formato de archivo .pdf',
                           ext_whitelist=(".pdf",), max_upload_size=4194304, widget=forms.FileInput(
            attrs={'class': 'p-1 text-secondary fs-6 ', 'input_file': True, 'col': '9'}))

    def __init__(self, *args, **kwargs):
        departamento_servicio_id = kwargs.pop('departamento_servicio_id', None)
        super(InformePsicologicoForm, self).__init__(*args, **kwargs)
        if departamento_servicio_id is not None:
            self.fields['motivoconsulta'].queryset = MotivoCita.objects.filter(
                departamentoservicio_id=departamento_servicio_id, status=True)

    def clean_seccion(self):
        grado = self.cleaned_data['grado']

        if grado < 1 or grado > 10:
            raise forms.ValidationError("La sección debe estar entre 1 y 6.")

        return grado


class RefuerzoAcademicoForm(FormModeloBase):
    grado_egb = forms.CharField(label=u'Año EGB/BGU', max_length=100, required=True,
                                widget=forms.TextInput(
                                    {'placeholder': 'Describa el titulo', 'col': '6'}))
    asignatura = forms.CharField(label=u'Asignatura', max_length=100, required=True,
                                  widget=forms.TextInput(
                                      {'placeholder': 'Describa el Asignatura', 'col': '6'}))
    archivo = ExtFileField(
        label=u'Archivo',
        required=False,
        help_text=u'Tamaño máximo permitido 8Mb y formato de archivo .pdf',
        ext_whitelist=(".pdf",),
        max_upload_size=8388608,  # 8 MB en bytes
        widget=forms.FileInput(attrs={'class': 'p-1 text-secondary fs-6 ', 'input_file': True})
    )

    destreza = forms.CharField(required=True, label=u'Destreza', widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa Destreza.'}))
    actividad = forms.CharField(required=True, label=u'Actividad', widget=forms.Textarea(attrs={'rows': '3', 'placeholder': 'Describa Actividad.'}))
    observacion = forms.CharField(required=True, label=u'Observación', widget=forms.Textarea(attrs={'rows':'3', 'placeholder': 'Describa una observación.'}))



class EstructuraInformeForm(FormModeloBase):
    tipoinforme = forms.ChoiceField(choices=TIPO_INFORME_PSICOLOGICO, required=True, label=u'Seleccione tipo de Informe',
                                     widget=forms.Select(attrs={'col': '4', 'class': 'select2'}))
    titulo = forms.CharField(label=u'Titulo', max_length=100, required=True,
                                  widget=forms.TextInput(
                                      {'placeholder': 'Describa el titulo', 'col': '5'}))
    orden = forms.IntegerField(label=u'Orden de aparición', initial=0, widget=forms.NumberInput(
        attrs={'class': 'input_number', 'input_number': True, 'col': '3', 'placeholder': '0', 'controlwidth': '50%'}))

    segmentacion = forms.ChoiceField(choices=TIPO_SEGMENTACION, required=False,
                                    label=u'Segmentación de ubicación',
                                    widget=forms.Select(attrs={'col': '4', 'class': 'select2'}))
    seccion = forms.IntegerField(label=u'Sección', initial=0, required=False, widget=forms.NumberInput(
        attrs={'class': 'input_number', 'input_number': True, 'col': '3', 'placeholder': '0', 'controlwidth': '50%'}))



    def clean_seccion(self):
        seccion = self.cleaned_data['seccion']
        informe = self.cleaned_data['tipoinforme']
        if (seccion < 1 or seccion > 6) and int(informe) == 2:
            raise forms.ValidationError("La sección debe estar entre 1 y 6.")

        return seccion

    def validador(self, id=0):
        ban, titulo = True, self.cleaned_data['titulo'].upper()

        # Validación para el título
        if EstructuraInforme.objects.filter(titulo__unaccent__iexact=titulo.strip(), servicio_id=id, status=True):
            self.add_error('titulo', 'Registro que desea ingresar ya existe.')
            ban = False

        # Validación para el orden
        orden = self.cleaned_data['orden']

        # Verificar si el orden ya existe pero está desactivado (activo=False)
        if EstructuraInforme.objects.filter(orden=orden, servicio_id=id, status=True, activo=True).exists():
            self.add_error('orden', 'Ya existe un registro activo con este orden.')
            ban = False

        return ban

class ProcesoForm(FormModeloBase):

    def __init__(self, *args, **kwargs):
        id_padre = kwargs.pop('id_padre', None)

        super(ProcesoForm, self).__init__(*args, **kwargs)

        if id_padre:
            self.fields['servicio'] = forms.ModelChoiceField(
                label=u"Servicio",
                queryset=ServicioCita.objects.filter(status=True, departamentoservicio_id=id_padre),
                required=True,
                widget=forms.Select(attrs={'col': '12', 'class': 'select2'})
            )

    servicio = forms.ModelChoiceField(label=u"Servicio", queryset=ServicioCita.objects.all(), required=True,
                                      widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))

    tipo_proceso = forms.ChoiceField(choices=TIPO_PROCESOS, required=True, label=u'Tipo Proceso',
                                     widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

    subtitulo = forms.CharField(label=u'Descripción 1', max_length=100, required=False,
                                  widget=forms.TextInput(
                                      {'placeholder': 'Describa el Titulo', 'col': '6'}))
    descripcion = forms.CharField(label=u'Descripción 2 ', max_length=100, required=True,
                                  widget=forms.TextInput(
                                      {'placeholder': 'Describa el Subtitulo', 'col': '6'}))
    # servicio = forms.ModelChoiceField(label=u"Servicio", queryset=ServicioCita.objects.filter(status=True, departamentoservicio_id=id_padre), required=True,
    #                                     widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    tipoinforme = forms.ChoiceField(choices=TIPO_INFORME_PSICOLOGICO, required=True, label=u'Tipo Informe',
                                    widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?',
                                 widget=forms.CheckboxInput(attrs={'data-switchery': 'true', 'col': '3'}))

    def validador(self, servicio, id=0):
        ban, descripcion =True, self.cleaned_data['descripcion'].upper()
        if Proceso.objects.filter(descripcion__unaccent=descripcion, servicio_id=servicio).exclude(id=id).exists():
            # raise forms.ValidationError('Registro que desea ingresar ya existe.')
            self.add_error('descripcion', 'Registro que desea ingresar ya existe.')
            ban = False
        return ban

class PersonaForm(FormModeloBase):
    # DATOS BÁSICOS
    tipoidentificacion = forms.ChoiceField(label=u"Documento", required=True,
                                            choices=[TIPOS_IDENTIFICACION[0], TIPOS_IDENTIFICACION[2]],
                                            widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    identificacion = forms.CharField(label=u"Número de identificación", max_length=10, required=True,
                                     widget=forms.TextInput(attrs={'col': '6', 'placeholder':'Digite su número de identificación'}))
    nombre = forms.CharField(max_length=200, label=u'Nombres', required=True,widget=forms.TextInput(attrs={'col':'12','placeholder':'Describa los nombres del familiar'}))
    apellido1 = forms.CharField(max_length=200, label=u'Primer apellido', required=True, widget=forms.TextInput(attrs={'col':'6', 'placeholder':'Describa el primer apellido'}))
    apellido2 = forms.CharField(max_length=200, label=u'Segundo apellido', required=True, widget=forms.TextInput(attrs={'col':'6', 'placeholder':'Describa el segundo apellido'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", queryset=Sexo.objects.filter(status=True), required=True,
                                        widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    nacimiento = forms.DateField(label=u"Fecha de nacimiento", initial=None, required=True,
                                 widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    telefono = forms.CharField(label=u'Celular', max_length=15, required=False,
                               widget=forms.TextInput(attrs={'col': '6','placeholder':'Digite el número de celular'}))
    telefono_conv = forms.CharField(label=u'Teléfono fijo', max_length=15, required=False,
                                    widget=forms.TextInput(attrs={'col': '6','placeholder':'Digite el número de teléfono'}))
    email = forms.EmailField(label=u'Correo electrónico', max_length=50, required=True,
                                    widget=forms.EmailInput(attrs={'col': '12', 'placeholder': 'Digite un correo electrónico'}))

    def edit(self):
        self.fields['cedulaidentidad'].required = False

    def clean(self):
        cleaned_data=super().clean()
        cedula=cleaned_data.get('identificacion').upper().strip()
        tipoidentificacion=int(cleaned_data.get('tipoidentificacion'))
        nacimiento = cleaned_data.get('nacimiento')
        # pers = consultarPersona(cedula)
        # if pers:
        #     self.add_error('identificacion', 'Identificación digitada ya se encuentra registrada.')
        if tipoidentificacion == 1:
            result = validarcedula(cedula)
            if result != 'Ok':
                self.add_error('identificacion', result)
        elif not cedula[:2] == u'VS':
            self.add_error('identificacion', 'Pasaporte mal ingresado, no olvide colocar VS al inicio.')
        if (datetime.now().year - nacimiento.year) < 18:
            self.add_error('nacimiento', 'Su año de nacimiento indica que es menor de edad.')
        return cleaned_data

class NoticiaVinculaForm(FormModeloBase):
    tipopuplicacion = forms.ChoiceField(choices=TIPO_PUBLICACION, required=True, label=u'Tipo publicación',widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    estadowebinar = forms.ChoiceField(choices=TIPO_WEBINAR, required=False, label=u'Tipo webinar',
                                        widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    titulo = forms.CharField(label=u'Título', max_length=300, required=True,
                              widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese su título'}))
    subtitulo = forms.CharField(label=u'Subtitulo', max_length=200, required=False,
                             widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese el subtitulo'}))
    portada = forms.FileField(label=u'Portada de la noticia', required=False, help_text=u'Tamaño Máximo permitido 5Mb, en formato jpg, jpeg, png',
                              widget=forms.FileInput(attrs={'col': '12', 'accept': '.png, .jpg, .jpeg', 'dropify': True}))
    principal = forms.BooleanField(label=u'¿Es noticia principal?', required=False,
                                   widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))
    publicado = forms.BooleanField(label=u'¿Publicado?', required=False,
                                        widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))
    archivo = ExtFileField(label=u'Archivo', required=False,
                           help_text=u'Tamaño maximo permitido 4Mb y formato de archivo .pdf', ext_whitelist=(".pdf",),
                           max_upload_size=4194304,widget=forms.FileInput(attrs={'class': 'p-1 text-secondary fs-6 ', 'input_file': True}))
    descripcion = forms.CharField(label=u'Contenido de noticia', required=True,
                                  widget=forms.Textarea(attrs={'col': '12'}))

    def __init__(self, *args, idpadre=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.idpadre = idpadre
    # def validador(self, idpadre, id=0):
    #     ban, descripcion = True, self.cleaned_data['descripcion'].upper()
    #     if NoticiasVinculacion.objects.filter(descripcion__unaccent=descripcion, departamentoservicio_id=idpadre).exclude(
    #             id=id).exists():
    #         # raise forms.ValidationError('Registro que desea ingresar ya existe.')
    #         self.add_error('descripcion', 'Registro que desea ingresar ya existe.')
    #         ban = False
    #     return ban
    def clean(self):
        cleaned_data = super().clean()
        instancia = self.instancia
        idpadre = self.idpadre
        id = getattr(self.instancia, 'id', 0)
        portada = cleaned_data.get('portada')
        titulo = cleaned_data.get('titulo')
        principal = cleaned_data.get('principal')
        if principal:
            noticias = NoticiasVinculacion.objects.filter(status=True, principal=True, publicado=True, departamentoservicio__id = idpadre).exclude(id=id)
            if len(noticias) >= 3:
                self.add_error('principal', 'No puede ser una noticia principal por que solo se admiten hasta 3 noticias principales y ya existen 3 noticias principales vigentes')
        if portada:
            max_tamano = 2 * 1024 * 1024  # 4 MB
            name_= portada._name
            ext = name_[name_.rfind("."):]
            if not ext.lower() in ['.png', '.jpg', '.jpeg']:
                self.add_error('portada', f'Solo se permite formato .png, .jpg, .jpeg')

            if portada.size > max_tamano:
                self.add_error('portada', f'Archivo supera los 4 megas permitidos')
            # Asignar un nombre personalizado al archivo
            portada.name = unidecode(generar_nombre(f"portada_noticia_{titulo.lower()[:3]}", portada._name))
        elif instancia:
            portada = instancia.portada
        cleaned_data['portada'] = portada
        return cleaned_data

class ResponsableServicioCitaForm(FormModeloBase):
    # responsable = forms.ModelChoiceField(queryset=Persona.objects.filter(status=True), required=True, label=u'Responsable del servicio', widget=forms.Select(attrs={'class': 'select2', 'col':'6'}))
    responsable = forms.ModelChoiceField(queryset=Persona.objects.filter(status=True), required=True, label=u'Responsable del servicio', widget=forms.Select(attrs={'class': 'select2', 'col':'6'}))
    cargo = forms.CharField(label=u'Cargo', max_length=50, required=False,
                                widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Describa el cargo del responsable'}))
    activo = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%', 'data-switchery': 'true', 'col':'6'}))
    abreviatura = forms.CharField(label=u'Abreviatura titulo', max_length=100, required=False,
                                  widget=forms.TextInput(
                                      attrs={'col': '6', 'placeholder': 'Describa abreviatura académico del responsable'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=10000,required=True,
                                  widget=forms.Textarea(attrs={'col': '12'}))

    # descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'col': '12','rows':'3'}))


class CardInformativoForm(FormModeloBase):
    titulo = forms.CharField(label=u'Título', max_length=500, required=True,
                             widget=forms.Textarea(attrs={'col': '12', 'placeholder': 'Ingrese su título de Información'}))
    subtitulo = forms.CharField(label=u'Subtitulo', max_length=1000, required=False,
                                widget=forms.Textarea(attrs={'col': '12', 'placeholder': 'Ingrese el subtitulo'}))
    imagen = forms.FileField(label=u'Imagen del Card', required=False,
                                 help_text=u'Tamaño Máximo permitido 2Mb, en formato  png',
                                 widget=forms.FileInput(attrs={'data-max-file-size': '2M',
                                                               'accept': '.png, .jpg, .jpeg'}))

    cuerpoinformativa = forms.CharField(label=u'Contenido de la Información', required=True,
                                  widget=forms.Textarea(attrs={'col': '12'}))
    fondo = forms.CharField(label=u'Color', max_length=500, required=True,
                            widget=forms.TextInput(attrs={'type': 'color'}))
    orden = forms.IntegerField(label=u'Orden de aparición', initial=0, widget=forms.NumberInput(
        attrs={'class': 'input_number', 'input_number': True, 'col': '4', 'placeholder': '0', 'controlwidth': '50%'}))

class TituloWebSiteServicioForm(FormModeloBase):
    titulo = forms.CharField(label=u'Título de cabecera', max_length=100, required=True,
                              widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese su título'}))
    subtitulo = forms.CharField(label=u'Subtitulo de cabecera', max_length=100, required=True,
                             widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese el subtitulo'}))
    fondotitulo = ExtFileField(label=u'Fondo', required=False, help_text=u'Tamaño Maximo permitido 2Mb, en formato jpg, jpeg, png',
                               max_upload_size=2194304, ext_whitelist=(".jpg", ".jpeg", ".png"),
                               widget=forms.FileInput(attrs={'col': '12', 'accept': '.png, .jpg, .jpeg'}))
    publicado = forms.BooleanField(label=u'¿Publicado?', required=False,
                                        widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '12'}))


class CuerpoWebSiteServicioForm(FormModeloBase):
    ubicacion = forms.ChoiceField(label='Ubicación', required=False, choices=UBICACION, widget=forms.HiddenInput())
    titulo = forms.CharField(label=u'Título', max_length=100, required=False,
                              widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Ingrese su título'}))

    descripcion = forms.CharField(label=u'Ingrese la descripción requerida',  max_length=80000, required=True,
                                  widget=forms.Textarea(attrs={'col': '12','class':'ckeditors'}))
    #
    # descripcion = forms.CharField(label=u'Descripción', max_length=1000, required=False,
    #                          widget=forms.Textarea(attrs={'col': '12','rows':'3', 'placeholder': 'Ingrese la descripción requerida'}))
    orden = forms.IntegerField(label=u'Orden de aparición', initial=0, widget=forms.NumberInput(attrs={'class': 'input_number','input_number':True, 'col': '4', 'placeholder': '0', 'controlwidth': '50%'}))
    publicado = forms.BooleanField(label=u'¿Publicado?', required=False,
                                        widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '6'}))


class TerminosCondicionForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=100, required=True, widget=forms.TextInput({'class': 'normal-input'}))
    descripcion = forms.CharField(required=False, label=u'Descripción', widget=forms.Textarea(attrs={'formwidth': 'span12', 'separator3': True}))
    mostrar = forms.BooleanField(initial=False, required=False, label=u'¿Mostrar?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))
    general = forms.BooleanField(initial=False, required=False, label=u'¿Es una condición general?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '6', 'data-switchery': 'true'}))
    servicio = forms.ModelMultipleChoiceField(queryset=ServicioCita.objects.filter(status=True), required=False, label=u'Servicios',
                                       widget=forms.SelectMultiple(attrs={}))