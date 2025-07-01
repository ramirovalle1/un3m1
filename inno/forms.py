# -*- coding: UTF-8 -*-
import os
from datetime import datetime, timedelta
from settings import SITE_STORAGE
from ckeditor.widgets import CKEditorWidget
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django import forms
from django.contrib.auth.models import Group
from django.db.models import Q, F, Count
from django.forms.models import ModelForm, ModelChoiceField
from django.forms.widgets import DateTimeInput, CheckboxInput, FileInput
from django.utils.safestring import mark_safe
from django.db import models, connection, connections

from core.custom_forms import FormModeloBase
from sagest.models import ActivoFijo
from sga.models import ProfesorMateria, MateriaAsignada, DetalleSilaboSemanalTema, Profesor, Materia, Matricula, \
    CamposTitulosPostulacion, \
    Carrera, Periodo, TIPO_SOLICITUDINCONVENIENTE, TIPO_MOTIVO, Aula, Modalidad, InstitucionEducacionSuperior, \
    Provincia, Canton, Parroquia, Titulo, NivelTitulacion, \
    GradoTitulacion, AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, \
    SedeVirtual, TipoAula, Bloque, LaboratorioVirtual, DetalleModeloEvaluativo, TIPO_RESPONSABLE_HORARIO_EXAMEN, \
    Coordinacion, Sesion, Malla, Paralelo, Persona, TIEMPO_DURACION, DIAS_CHOICES, TIPO_PRACTICA_PP, \
    ESTADO_PREINSCRIPCIONPPP, \
    ItinerariosMalla, DetallePreInscripcionPracticasPP, AcuerdoCompromiso, Pais, AsignacionEmpresaPractica, \
    EmpresaEmpleadora, \
    PracticasDepartamento, TIPO_INSTITUCION, SECTOR_ECONOMICO, CabPeriodoEvidenciaPPP, TIPOS_IDENTIFICACION, Sexo, \
    ParentescoPersona, \
    CENTRO_CUIDADO, TIPO_INSTITUCION_LABORAL, TemaUnidadResultadoProgramaAnalitico, MESES_CHOICES, \
    EvaluacionAprendizajeComponente, Sede
from sga.forms import ExtFileField
from posgrado.models import Requisito, ClaseRequisito
from inno.models import Criterio, HorarioTutoriaAcademica, TOPICO_SOLICITUD_TUTORIA, TIPO_SOLICITUD_TUTORIA, \
    ESTADO_SOLICITUD_TUTORIA, SolicitudTutoriaIndividualTema, TipoRecurso, FormatoArchivo, CampoAmplioPac, \
    CampoEspecificoPac, CampoDetalladoPac, CarreraPac, TipoInconvenienteClaseDiferido, \
    MotivoTipoInconvenienteClaseDiferido, NivelFormacionPac, TipoTramiteRediseno, TipoFormacionRediseno, \
    TitulacionPac, AprobacionTrabajoIntegracionCurricular, DetalleFuncionSustantivaDocenciaPac, TipoPersonalPac, \
    TIPO_FORMACION_REDISEÑO, AnexosPac, TipoProgramaPac, TipoProcesoPac, TipoFormaPagoPac, TipoNovedad, \
    ESTADO_CONSTATACION, TerminosCondiciones, ESTADO_APROBACION, TurnoPractica, ItinerarioAsignaturaMalla
from sga.models import CategoriaIes,TipoFinanciamiento,VALOR_SI_NO, Asignatura, CategorizacionDocente, NivelMalla, \
    ConvenioEmpresa, LaboratorioAcademia, AsignaturaMalla, EncuestaGrupoEstudiantes, Discapacidad, SubTipoDiscapacidad, \
    InstitucionBeca, GRADO, Inscripcion
from inno.models import PERIODO_ORDINARIO_CHOICES, SEMANA_PERIODO_ORDINARIO_CHOICES,PERIODO_EXTRAORDINARIO_CHOICES,\
    SEMANA_PERIODO_EXTRAORDINARIO_CHOICES, IndiceHoraPlanificacion, UNIDAD_ORGANIZACION_CURRICULAR,\
    HORAS_DEDICACIÓN_IES, TIPOPRESUPUESTO_PAC, HORAS_DEDICACIÓN_PROGRAMA, CLASE_NOVEDAD, EncuestaGrupoEstudianteSeguimientoSilabo, \
    ConfiguracionInscripcionPracticasPP, ROL_ACTIVIDAD, TIPO_ACTIVIDAD, ResponsableCentroSalud, ESTADO_CONFIGURACION_PRACTICAS
from sga.reportes import tipoparametro
from sga.funciones import validarcedula
from med.models import Enfermedad
from socioecon.models import FormaTrabajo


class CheckboxSelectMultipleCustom(forms.CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(CheckboxSelectMultipleCustom, self).render(*args, **kwargs)
        return mark_safe(output.replace(u'<ul>',
                                        u'<div class="custom-multiselect" style="width: 600px;overflow: scroll"><ul>').replace(
            u'</ul>', u'</ul></div>').replace(u'<li>', u'').replace(u'</li>', u'').replace(u'<label',
                                                                                           u'<div style="width: 900px"><li').replace(
            u'</label>', u'</li></div>'))


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


def campo_modolectura(form, campo, valor):
    form.fields[campo].widget.attrs['readonly'] = valor


def campo_modobloqueo(form, campo, valor):
    form.fields[campo].widget.attrs['disabled'] = valor


class SolicitudTutoriaIndividualForm(forms.Form):
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.filter(status=True), required=False)
    profesor = ModelChoiceField(label=u'Profesor', queryset=Profesor.objects.filter(id=None), required=False)
    horario = ModelChoiceField(label=u'Horario', queryset=HorarioTutoriaAcademica.objects.filter(id=None), required=False)
    topico = forms.ChoiceField(label=u'Tópico ', choices=TOPICO_SOLICITUD_TUTORIA, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    tema = ModelChoiceField(label=u'Tema', queryset=DetalleSilaboSemanalTema.objects.filter(id=None), required=False)
    observacion_estudiante = forms.CharField(label=u'Observación', max_length=10000, widget=forms.Textarea({'row': '3'}), required=False)

    def iniciar(self,periodo,matricula):
        hoy = datetime.now().date()
        if periodo.tipo_id in[3,4]:
            self.fields['materia'].queryset = Materia.objects.filter(
                id__in=MateriaAsignada.objects.values_list('materia_id').filter(
                    matricula=matricula,
                    materia__nivel__periodo=periodo,
                    materia__inicio__lte=hoy, materia__fin__gte=hoy,
                    retiramateria=False,
                ).exclude(materia__profesormateria__tipoprofesor_id__in=[16]).distinct()).exclude(asignaturamalla__malla_id__in=[353, 22])
            deshabilitar_campo(self, 'tema')
        else:
            self.fields['materia'].queryset = Materia.objects.filter(id__in=MateriaAsignada.objects.values_list('materia_id').filter(
                matricula=matricula,
                materia__nivel__periodo=periodo,
                retiramateria=False,
            ).exclude(materia__profesormateria__tipoprofesor_id__in=[16]).distinct()).exclude(asignaturamalla__malla_id__in=[353, 22])
            deshabilitar_campo(self, 'tema')

    def editar(self,periodo,matricula,solicitud):
        hoy = datetime.now().date()
        if periodo.tipo_id in [3, 4]:
            self.fields['materia'].queryset = Materia.objects.filter(id__in=MateriaAsignada.objects.values_list('materia_id').filter(matricula=matricula, materia__nivel__periodo=periodo, materia__inicio__lte=hoy, materia__fin__gte=hoy,retiramateria=False,).distinct()).exclude(asignaturamalla__malla_id__in=[353, 22])
        else:
            self.fields['materia'].queryset = Materia.objects.filter(id__in=MateriaAsignada.objects.values_list('materia_id').filter(matricula=matricula, materia__nivel__periodo=periodo, retiramateria=False).distinct()).exclude(asignaturamalla__malla_id__in=[353,22])

        self.fields['profesor'].queryset = Profesor.objects.filter(id=solicitud.profesor.id)
        self.fields['horario'].queryset = HorarioTutoriaAcademica.objects.filter(status=True, profesor=solicitud.profesor, periodo=periodo).distinct().order_by('dia')
        self.fields['tema'].queryset = DetalleSilaboSemanalTema.objects.filter(status=True,
                                                            silabosemanal__silabo__materia=solicitud.materiaasignada.materia,
                                                            silabosemanal__silabo__profesor=solicitud.profesor,
                                                            silabosemanal__silabo__status=True,
                                                            silabosemanal__fechainiciosemana__lte=datetime.now().date())
        deshabilitar_campo(self, 'tema')

class SolicitudTutoriaGrupalForm(forms.Form):
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.none(), required=False)
    profesor = ModelChoiceField(label=u'Profesor', queryset=Profesor.objects.filter(id=None), required=False)
    horario = ModelChoiceField(label=u'Horario', queryset=HorarioTutoriaAcademica.objects.filter(id=None), required=False)
    topico = forms.ChoiceField(label=u'Tópico ', choices=TOPICO_SOLICITUD_TUTORIA, required=False, widget=forms.Select(attrs={'class': 'imp-50'}))
    tema = ModelChoiceField(label=u'Tema', queryset=DetalleSilaboSemanalTema.objects.none(), required=False)
    estudiantes=forms.ModelMultipleChoiceField(label=u'Estudiantes', required=False, queryset=Matricula.objects.none())
    observacion_estudiante = forms.CharField(label=u'Observación', max_length=10000, widget=forms.Textarea({'row': '3'}), required=False)

    def iniciar(self,periodo,matricula):
        hoy = datetime.now().date()
        if periodo.tipo_id in [3, 4]:
            idmaterias=MateriaAsignada.objects.filter(matricula=matricula, materia__inicio__lte=hoy, materia__fin__gte=hoy,materia__nivel__periodo=periodo, retiramateria=False,).distinct()
            self.fields['materia'].queryset = Materia.objects.filter(id__in=idmaterias.values_list('materia_id')).exclude(asignaturamalla__malla_id__in=[353, 22])
            idm=MateriaAsignada.objects.values_list('matricula_id').filter(status=True, materia_id__in=idmaterias.values_list('materia_id')).distinct()
            self.fields['estudiantes'].queryset = Matricula.objects.filter(status=True, id__in=idm).order_by('inscripcion__persona')
            deshabilitar_campo(self, 'tema')
        else:
            idmaterias=MateriaAsignada.objects.filter( matricula=matricula, materia__nivel__periodo=periodo, retiramateria=False,).distinct()
            self.fields['materia'].queryset = Materia.objects.filter(id__in=idmaterias.values_list('materia_id')).exclude(asignaturamalla__malla_id__in=[353, 22])
            idm=MateriaAsignada.objects.values_list('matricula_id').filter(status=True, materia_id__in=idmaterias.values_list('materia_id')).distinct()
            self.fields['estudiantes'].queryset = Matricula.objects.filter(status=True, id__in=idm).order_by('inscripcion__persona')
            deshabilitar_campo(self, 'tema')


class TutoriaManualForm(forms.Form):
    tipo = forms.ChoiceField(label=u'Tipo ', choices=TIPO_SOLICITUD_TUTORIA, required=False,  widget=forms.Select(attrs={'class': 'imp-50'}))
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.none(), required=False)
    fechatutoria = forms.DateField(label=u"Fecha tutoría", initial=datetime.now().date(), required=False,
                          input_formats=['%d-%m-%Y'],
                          widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    hora = forms.TimeField(label=u"Hora", required=False, initial=str(datetime.now().time()),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    todos = forms.BooleanField(initial=False, label=u"¿Desea seleccionar a todos los matriculados en la asignatura?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    estudiantes=forms.ModelMultipleChoiceField(label=u'Estudiantes', required=False, queryset=Matricula.objects.none())
    topico = forms.ChoiceField(label=u'Tópico ', choices=TOPICO_SOLICITUD_TUTORIA, required=False,  widget=forms.Select(attrs={'class': 'imp-50'}))
    tema = ModelChoiceField(label=u'Tema', queryset=DetalleSilaboSemanalTema.objects.none(), required=False)
    observacion = forms.CharField(label=u'Observación', max_length=10000, widget=forms.Textarea({'row': '3'}), required=False)

    def iniciar(self,periodo,profesor):
        self.fields['materia'].queryset = Materia.objects.filter(id__in=ProfesorMateria.objects.values_list('materia_id').filter(
            profesor=profesor,
            materia__nivel__periodo=periodo,
        ).distinct()).exclude(asignaturamalla__malla_id__in=[353,22])
        idm=MateriaAsignada.objects.values_list('matricula_id').filter(status=True,materia_id__in=ProfesorMateria.objects.values_list('materia_id').filter(
            profesor=profesor,
            materia__nivel__periodo=periodo,
        ).distinct()).distinct()
        self.fields['estudiantes'].queryset = Matricula.objects.filter(status=True, id__in=idm).order_by('inscripcion__persona')
        deshabilitar_campo(self, 'tema')


class ProgramarTutoriasForm(forms.Form):
    horario = ModelChoiceField(label=u'Horario', queryset=HorarioTutoriaAcademica.objects.none(), required=False)
    tema = ModelChoiceField(label=u'Tema', queryset=DetalleSilaboSemanalTema.objects.none(), required=False)
    fechatutoria = forms.DateField(label=u"Fecha tutoría", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%', 'autocomplete':'off'}))
    tutoriacomienza = forms.TimeField(label=u"Hora inicia tutoría", required=False, initial=str(datetime.now().time()), input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    tutoriatermina = forms.TimeField(label=u"Hora finaliza tutoría", required=False, initial=str(datetime.now().time()), input_formats=['%H:%M'], widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))

    def iniciar(self,solicitudes):
        from datetime import timedelta
        self.fields['horario'].queryset =horario= HorarioTutoriaAcademica.objects.filter(status=True, id__in=solicitudes.values('horario_id')).distinct().order_by('dia')
        idt=SolicitudTutoriaIndividualTema.objects.values('tema_id').filter(solicitud_id__in=solicitudes)
        self.fields['tema'].queryset = DetalleSilaboSemanalTema.objects.filter(status=True,id__in=idt)
        hoy =fechaestimada= datetime.now().date()
        numerodia = horario[0].dia
        horaactual=datetime.now().time()
        horahorario=horario[0].turno.comienza
        carga=0
        if hoy.isoweekday() == numerodia:
            if horaactual.hour<=horahorario.hour:
                carga=1
        if hoy.isoweekday() != numerodia or carga==0:
            for days in range(8):
                hoy = hoy + timedelta(days=1)
                if hoy.isoweekday() == numerodia:
                    fechaestimada = hoy
                    break
        self.fields['fechatutoria'].initial = fechaestimada

    def iniciarsinhorario(self,solicitudes):
        from datetime import timedelta
        self.fields['horario'].queryset =horario= HorarioTutoriaAcademica.objects.filter(status=True, id__in=solicitudes.values('horario_id')).distinct().order_by('dia')
        idt=SolicitudTutoriaIndividualTema.objects.values('tema_id').filter(solicitud_id__in=solicitudes)
        self.fields['tema'].queryset = DetalleSilaboSemanalTema.objects.filter(status=True,id__in=idt)
        hoy =fechaestimada= datetime.now().date()
        # numerodia = horario[0].dia
        horaactual=datetime.now().time()
        # horahorario=horario[0].turno.comienza
        carga=0
        # if hoy.isoweekday() == numerodia:
        #     if horaactual.hour<=horahorario.hour:
        #         carga=1
        # if hoy.isoweekday() != numerodia or carga==0:
        #     for days in range(8):
        #         hoy = hoy + timedelta(days=1)
        #         if hoy.isoweekday() == numerodia:
        #             fechaestimada = hoy
        #             break
        self.fields['tutoriacomienza'].initial = solicitudes[0].tutoriacomienza
        self.fields['horario'].widget = forms.HiddenInput()
        self.fields['horario'].label = ""
        del self.fields['horario']
        self.fields['tutoriatermina'].initial = solicitudes[0].tutoriatermina
        self.fields['fechatutoria'].initial = fechaestimada


class ConvocarTutoriaManualForm(forms.Form):
    tipo = forms.ChoiceField(label=u'Tipo ', choices=TIPO_SOLICITUD_TUTORIA, required=False,  widget=forms.Select(attrs={'class': 'imp-50'}))
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.none(), required=False)
    fechatutoria = forms.DateField(label=u"Fecha tutoría", initial=datetime.now().date(), required=False,
                                   input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y',
                                                                                    attrs={'class': 'selectorfecha',
                                                                                           'formwidth': '50%'}))
    tutoriacomienza = forms.TimeField(label=u"Hora inicia tutoría", required=False, initial=str(datetime.now().time()),
                                      input_formats=['%H:%M'],
                                      widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    tutoriatermina = forms.TimeField(label=u"Hora finaliza tutoría", required=False, initial=str(datetime.now().time()),
                                     input_formats=['%H:%M'],
                                     widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora'}))
    todos = forms.BooleanField(initial=False, label=u"¿Desea seleccionar a todos los matriculados en la asignatura?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    estudiantes=forms.ModelMultipleChoiceField(label=u'Estudiantes', required=False, queryset=Matricula.objects.none())
    topico = forms.ChoiceField(label=u'Tópico ', choices=TOPICO_SOLICITUD_TUTORIA, required=False,  widget=forms.Select(attrs={'class': 'imp-50'}))
    tema = ModelChoiceField(label=u'Tema', queryset=DetalleSilaboSemanalTema.objects.none(), required=False)

    def iniciar(self,periodo,profesor):
        self.fields['materia'].queryset = Materia.objects.filter(id__in=ProfesorMateria.objects.values_list('materia_id').filter(
            profesor=profesor,
            materia__nivel__periodo=periodo,
        ).distinct()).exclude(asignaturamalla__malla_id__in=[353,22])
        idm=MateriaAsignada.objects.values_list('matricula_id').filter(status=True,materia_id__in=ProfesorMateria.objects.values_list('materia_id').filter(
            profesor=profesor,
            materia__nivel__periodo=periodo,
        ).distinct()).distinct()
        self.fields['estudiantes'].queryset = Matricula.objects.filter(status=True, id__in=idm).order_by('inscripcion__persona')
        deshabilitar_campo(self, 'tema')


class TipoRecursoForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripcion", widget=forms.TextInput())


class ListaVerificacionForm(forms.Form):
    descripcion = forms.CharField(label=u"Descripcion", widget=forms.TextInput())

class CamposPacForm(forms.Form):
    nivelformacion = forms.ModelChoiceField(NivelFormacionPac.objects.filter(status=True), required=True, label=u'Nivel Formación',widget=forms.Select(attrs={'formwidth': '100%'}))
    codigoamplio = forms.CharField(label=u"Código Campo Amplio", max_length=200, widget=forms.TextInput(attrs={'formwidth': '35%'}))
    descripcionamplio = forms.CharField(label=u"Descripción Campo Amplio", widget=forms.TextInput())
    codigoespecifico = forms.CharField(label=u"Código Campo Específico", max_length=200, widget=forms.TextInput(attrs={'formwidth': '35%'}))
    descripcionespecifico = forms.CharField(label=u"Descripción Campo Específico", widget=forms.TextInput())
    codigodetallado = forms.CharField(label=u"Código Campo Detallado", max_length=200,widget=forms.TextInput(attrs={'formwidth': '35%'}))
    descripciondetallado = forms.CharField(label=u"Descripción Campo Detallado", widget=forms.TextInput())
    codigocarrera = forms.CharField(label=u"Código Carrera", max_length=200,widget=forms.TextInput(attrs={'formwidth': '35%'}))
    abreviaturacarrera = forms.CharField(label=u"Abreviatura Carrera", max_length=10, required=False, widget=forms.TextInput(attrs={'formwidth': '35%'}))
    descripcioncarrera = forms.CharField(label=u"Descripción Carrera", widget=forms.TextInput())
    codigotitulacion = forms.CharField(label=u"Código Titulación", max_length=200,widget=forms.TextInput(attrs={'formwidth': '35%'}))
    tituloobtenidohombre = forms.CharField(label=u"Título obtenido hombre", widget=forms.TextInput())
    tituloobtenidomujer = forms.CharField(label=u"Título obtenido mujer", widget=forms.TextInput())
    # descripciontitulacion = forms.CharField(label=u"Descripción Titulación", widget=forms.TextInput())

class CampoAmplioPacForm(forms.Form):
    codigo = forms.CharField(label=u"Código", max_length=200, widget=forms.TextInput(attrs={'formwidth': '35%'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.TextInput())


class CampoEspecificoPacForm(forms.Form):
    campoampliopac = forms.ModelChoiceField(label=u"Campo Amplio", required=True, queryset=CampoAmplioPac.objects.filter(status=True), widget=forms.Select(attrs={'formwidth': '100%'}))
    codigo = forms.CharField(label=u"Código", max_length=200, widget=forms.TextInput(attrs={'formwidth': '35%'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.TextInput())


class CampoDetalladoPacForm(forms.Form):
    campoespecificopac = forms.ModelChoiceField(label=u"Campo Específico", required=True, queryset=CampoEspecificoPac.objects.filter(status=True))
    codigo = forms.CharField(label=u"Código", max_length=200, widget=forms.TextInput(attrs={'formwidth': '35%'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.TextInput())


class CarreraPacForm(forms.Form):
    campodetalladopac = forms.ModelChoiceField(label=u"Campo Detallado", required=True, queryset=CampoDetalladoPac.objects.filter(status=True))
    codigo = forms.CharField(label=u"Código", max_length=200, widget=forms.TextInput(attrs={'formwidth': '35%'}))
    descripcion = forms.CharField(label=u"Descripción", widget=forms.TextInput())
    abreviaturacarrera = forms.CharField(label=u"Abreviatura Carrera", max_length=10, widget=forms.TextInput(attrs={'formwidth': '35%'}))


class TitulacionPacForm(forms.Form):
    carrerapac = forms.ModelChoiceField(label=u"Carrera", required=True, queryset=CarreraPac.objects.filter(status=True))
    codigo = forms.CharField(label=u"Código", max_length=200, widget=forms.TextInput(attrs={'formwidth': '35%'}))
    tituloobtenidohombre = forms.CharField(label=u"Título obtenido hombre", widget=forms.TextInput())
    tituloobtenidomujer = forms.CharField(label=u"Título obtenido mujer", widget=forms.TextInput())
    # descripcion = forms.CharField(label=u"Descripción", widget=forms.TextInput())


class ConfiguracionRecursoForm(forms.Form):
    periodo = forms.ModelChoiceField(Periodo.objects.filter(status=True), required=False, label=u'Periodo',
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    carrera = forms.ModelChoiceField(Carrera.objects.filter(status=True, coordinacion__id__in=[1, 2, 3, 4, 5]),
                                     required=False, label=u'Carrera', widget=forms.Select(attrs={'formwidth': '100%'}))
    tiporecurso = forms.ModelChoiceField(TipoRecurso.objects.filter(status=True), required=False, label=u'Tipo de recurso', widget=forms.Select(attrs={'formwidth': '100%'}))
    formato = forms.ModelMultipleChoiceField(label=u'Formato archivo', queryset=FormatoArchivo.objects.all(), required=False)

    def inicializar(self,periodo,):
        self.fields['periodo'].initial = periodo.id

    def inicializar_carrera(self,carreras):
        self.fields['carrera'].queryset=Carrera.objects.filter(status=True,id__in=carreras.values_list('id',flat=True),coordinacion__in=[1, 2, 3, 4, 5])


class SolicitudAperturaClaseForm(forms.Form):
    # tiposolicitud = forms.ChoiceField(label=u'Tipo Solicitud', required=True, choices=TIPO_SOLICITUDINCONVENIENTE, widget=forms.Select(attrs={"formwidth": "span6"}))
    tipoincoveniente = forms.ModelChoiceField(label=u'Incoveniente', required=True, queryset=TipoInconvenienteClaseDiferido.objects.filter(status=True), widget=forms.Select(attrs={"formwidth": "span6"}))
    # tipomotivo = forms.ChoiceField(label=u'Tipo Motivo', required=True, choices=TIPO_MOTIVO, widget=forms.Select(attrs={"formwidth": "span6"}))
    tipomotivo = forms.ModelChoiceField(label=u'Motivo', required=True, queryset=MotivoTipoInconvenienteClaseDiferido.objects.filter(status=True), widget=forms.Select(attrs={"formwidth": "span6"}))
    fechainicioinasistencia = forms.DateField(label=u"Fecha Inicio Inasistencia", input_formats=['%d-%m-%Y'],  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span6"}), required=True)
    fechafininasistencia = forms.DateField(label=u"Fecha Fin Inasistencia", input_formats=['%d-%m-%Y'],  widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span6"}), required=True)
    especifique = forms.CharField(label=u'Especifique', widget=forms.Textarea(attrs={"formwidth": "span12", 'separator3': True}), required=False)
    materia = ModelChoiceField(label=u'Materia', queryset=Materia.objects.all(),  widget=forms.Select(attrs={"formwidth": "span12", "labelwidth": "250px", 'separator3': True}), required=True)
    aula = ModelChoiceField(label=u'Aula "opcional"', queryset=Aula.objects.filter(status=True), required=False, widget=forms.Select(attrs={"formwidth": "span12", 'separator3': True}))
    # motivo = forms.CharField(label=u'Motivo', widget=forms.Textarea, required=False, widget=forms.Select(attrs={"formwidth": "span12", "labelwidth": "250px", 'separator3': True}))
    # documento = ExtFileField(label=u'Adjunto', required=False, help_text=u'Tamaño Maximo permitido 5Mb, en formato pdf', ext_whitelist=(".pdf"), max_upload_size=5242880, widget=FileInput({'accept': 'application/pdf', "formwidth": "span6", 'separator3': True}))
    # documento = ExtFileField(label=u'Adjunto', help_text=u'Tamano Maximo permitido 5Mb, en formato pdf', ext_whitelist=(".pdf", ".PDF"), max_upload_size=5242880, required=False, widget=FileInput({"formwidth": "span6", 'separator3': True}))
    # documento = ExtFileField(label=u'Adjunto', required=False, help_text=u'Tamaño Maximo permitido 5Mb, en formato pdf', ext_whitelist=(".pdf"), max_upload_size=5242880, widget=FileInput({'accept': ' application/pdf', "formwidth": "span6", 'separator3': True}))
    # fechadiferido = forms.DateField(label=u"Fecha de clase a impartir", input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', "formwidth": "span6"}), required=True)
    documento = ExtFileField(label=u'Adjunto', required=False, help_text=u'Tamaño Maximo permitido 20Mb, en formato pdf',ext_whitelist=(".pdf",), max_upload_size=20480000)

    def set_materia(self, profesor, periodo):
        fecha = datetime.now().date()
        materias = []
        # profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 5, 6]).distinct().order_by('desde', 'materia__asignatura__nombre')
        profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo).distinct().order_by('desde', 'materia__asignatura__nombre')
        for profesormateria in profesormaterias:
            if profesormateria.esta_dia_con_horario(fecha):
                data = profesormateria.asistencia_docente(fecha, fecha, periodo)
                if data['total_asistencias_dias_feriados'] > 0 or data['total_asistencias_dias_suspension'] > 0 or data['total_asistencias_no_registradas'] > 0:
                    materias.append(profesormateria.materia.id)
        # if periodo.tipo.id in [3,4]:
        #     self.fields['tiposolicitudinconveniente'].choices = TIPO_SOLICITUDINCONVENIENTE[0:4]
        # else:
        #     self.fields['tiposolicitudinconveniente'].choices = TIPO_SOLICITUDINCONVENIENTE[4:5]
        self.fields['materia'].queryset = Materia.objects.filter(id__in=materias)

    def set_tipo(self, periodo):
        ePeriodoAcademia = periodo.get_periodoacademia()
        if ePeriodoAcademia.puede_solicitar_clase_diferido_pro and ePeriodoAcademia.proceso_solicitud_clase_diferido_pro and ePeriodoAcademia.proceso_solicitud_clase_diferido_pro.tiene_tipos():
            # tipos_solicitudes = []
            # for tipo in ePeriodoAcademia.tipos_solicitud_asistencias_pro.strip().split(','):
            #     tipos_solicitudes.append([int(tipo), TIPO_SOLICITUDINCONVENIENTE[int(tipo) - 1][1]])
            self.fields['tipoincoveniente'].queryset = tipoincoveniente = ePeriodoAcademia.proceso_solicitud_clase_diferido_pro.mis_tipos()
            self.fields['tipoincoveniente'].initial = tipoincoveniente[0]
            self.fields['tipomotivo'].queryset = MotivoTipoInconvenienteClaseDiferido.objects.filter(pk=None)
            if tipoincoveniente[0].tiene_motivos():
                self.fields['tipomotivo'].queryset = motivos = tipoincoveniente[0].mis_motivos()
                self.fields['tipomotivo'].initial = motivos[0].id
                self.fields['documento'].required = motivos[0].obligar_archivo
                self.fields['especifique'].required = motivos[0].es_otro

    def clean(self):
        cleaned_data = super(SolicitudAperturaClaseForm, self).clean()
        tipoincoveniente = cleaned_data['tipoincoveniente'] if 'tipoincoveniente' in cleaned_data and cleaned_data['tipoincoveniente'] else None
        tipomotivo = cleaned_data['tipomotivo'] if 'tipomotivo' in cleaned_data and cleaned_data['tipomotivo'] else None
        fechainicioinasistencia = cleaned_data['fechainicioinasistencia'] if 'fechainicioinasistencia' in cleaned_data and cleaned_data['fechainicioinasistencia'] else None
        fechafininasistencia = cleaned_data['fechafininasistencia'] if 'fechafininasistencia' in cleaned_data and cleaned_data['fechafininasistencia'] else None
        especifique = cleaned_data['especifique'] if 'especifique' in cleaned_data and cleaned_data['especifique'] else None
        materia = cleaned_data['materia'] if 'materia' in cleaned_data and cleaned_data['materia'] else None
        # fechadiferido = cleaned_data['fechadiferido'] if 'fechadiferido' in cleaned_data and cleaned_data['fechadiferido'] else None

        if not tipoincoveniente:
            self.add_error('tipoincoveniente', forms.ValidationError('Favor seleccione un incoveniente'))
        if not tipomotivo:
            self.add_error('tipomotivo', forms.ValidationError('Favor seleccione un motivo'))
        else:
            if not especifique and tipomotivo.es_otro:
                self.add_error('especifique', forms.ValidationError('Favor especifique el motivo'))
        if not fechainicioinasistencia:
            self.add_error('fechainicioinasistencia', forms.ValidationError('Favor seleccione una fecha inicio'))
        if not fechafininasistencia:
            self.add_error('fechafininasistencia', forms.ValidationError('Favor seleccione una fecha fin'))
        if fechainicioinasistencia > datetime.now().date():
            self.add_error('fechainicioinasistencia', forms.ValidationError('Fecha inicio no puede ser mayor a la fecha actual'))
        if fechafininasistencia > datetime.now().date():
            self.add_error('fechafininasistencia', forms.ValidationError('Fecha fin no puede ser mayor a la fecha actual'))
        if fechafininasistencia < fechainicioinasistencia:
            self.add_error('fechafininasistencia', forms.ValidationError('Fecha fin no puede ser mayor a la fecha inicio'))
        if not materia:
            self.add_error('materia', forms.ValidationError('Favor seleccione una materia'))
        # if not fechadiferido:
        #     self.add_error('fechadiferido', forms.ValidationError('Favor seleccione una fecha para el diferido'))

        return cleaned_data


class DatosGeneralForm(forms.Form):
    tipotramite = forms.ModelChoiceField(label=u"Tipo de trámite/Propuesta", queryset=TipoTramiteRediseno.objects.filter(status=True), required=False,widget=forms.Select())

    tipoproceso = forms.ModelChoiceField(label=u"Tipo de Proceso", queryset=TipoProcesoPac.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    tipoprograma = forms.ModelChoiceField(label=u"Tipo de Programa", queryset=TipoProgramaPac.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))

    codigosniese = forms.CharField(label=u'Código SNIESE de la carrera/ programa a rediseñar', max_length=100, required=False, widget=forms.TextInput(attrs={'formwidth': '50%'}))
    proyectoinnovador = forms.ChoiceField(label=u"Proyecto innovador", choices=VALOR_SI_NO, required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    tipoformacion = forms.ModelChoiceField(label=u"Tipo de formación",queryset=TipoFormacionRediseno.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    modalidad = forms.ModelChoiceField(label=u"Modalidad de estudios/aprendizaje",queryset=Modalidad.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    ejecucionmodalidad = forms.CharField(label=u"Descripción de la ejecución de la modalidad", required=False, widget=CKEditorUploadingWidget())
    proyectoenred = forms.ChoiceField(label=u"Proyecto en red", choices=VALOR_SI_NO, required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    integrantesred = forms.ModelMultipleChoiceField(label=u'Integrantes de la red', required=False,queryset=InstitucionEducacionSuperior.objects.filter(status=True))

    campostitulacion = forms.ModelChoiceField(label=u'Titulación', queryset=CamposTitulosPostulacion.objects.filter(status=True), required=False, widget=forms.Select())
    campoamplio = forms.CharField(label=u"Campo amplio", max_length=100, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))
    campoespecifico = forms.CharField(label=u"Campo específico", max_length=100, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))
    campodetallado = forms.CharField(label=u"Campo detallado", max_length=100, required=False,widget=forms.TextInput(attrs={'class': 'imp-100'}))

    carrera = forms.ModelChoiceField(label=u'Carrera/Programa a rediseñar', queryset=Carrera.objects.filter(status=True),required=False, widget=forms.Select())
    # titulacionpac = forms.ModelChoiceField(label=u'Titulación', queryset=TitulacionPac.objects.filter(status=True),required=False, widget=forms.Select())
    numeroperiodosordinario = forms.ChoiceField(label=u'Número de períodos académicos ordinarios',choices=PERIODO_ORDINARIO_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-numbersmall', 'formwidth': '50%',  'separator': 'true'}))
    periodoextraordinario = forms.ChoiceField(label=u"Periodo extraordinario", choices=VALOR_SI_NO, required=False, widget=forms.Select(attrs={'formwidth': '50%'}))
    numerosemanaordinario = forms.ChoiceField(label=u'Número de semanas por periodo académico  ', choices=SEMANA_PERIODO_ORDINARIO_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-numbersmall', 'formwidth': '50%'}))

    numeroperiodosextraordinario = forms.ChoiceField(label=u'Número de períodos extraordinarios', choices=PERIODO_EXTRAORDINARIO_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-numbersmall', 'formwidth': '50%'}))

    indicehoraplanificacion = forms.ModelChoiceField(label=u"Índice para cálculo de horas(Planificación de los Componentes de Aprendizaje)",queryset=IndiceHoraPlanificacion.objects.filter(status=True), required=False,widget=forms.Select(attrs={'formwidth': '50%'}))
    numerosemanaextraordinario = forms.ChoiceField(label=u'Número de semanas de períodos extraordinarios', choices=SEMANA_PERIODO_EXTRAORDINARIO_CHOICES, required=False, widget=forms.Select(attrs={'class': 'imp-numbersmall', 'formwidth': '50%'}))
    totalhoras = forms.FloatField(label=mark_safe(u"Total de horas del programa"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    totalhorasaprendizajecontactodocente = forms.FloatField(label=mark_safe(u"Total de horas de aprendizaje en contacto con el docente"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    totalhorasaprendizajepracticoexperimental = forms.FloatField(label=mark_safe(u"Total de horas del aprendizaje práctico-experimental"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    totalhorasaprendizajeautonomo = forms.FloatField(label=mark_safe(u"Total de horas del aprendizaje autónomo"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    totalhoraspracticasprofesionales = forms.FloatField(label=mark_safe(u"Total de horas de prácticas profesionales"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    totalhorasunidadtitulacion = forms.FloatField(label=mark_safe(u"Total de horas de la unidad de titulación"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    numerocohorte = forms.IntegerField(label=u'Número de cohortes', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%', 'separator': 'true'}))
    numeroparalelocohorte = forms.IntegerField(label=u'Número de paralelos por cohorte', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': '50%' }))
    numerototalasignatura = forms.IntegerField(label=u'Número total de asignaturas', initial=0, required=False,widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0','formwidth': '50%'}))
    numeroestudiantecohorte = forms.IntegerField(label=u'Número de estudiantes por cohorte', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0','formwidth': '50%'}))
    mencionitinerario = forms.ChoiceField(label=u"Con mención en/Itinerario", choices=VALOR_SI_NO, required=False, widget=forms.Select(attrs={'formwidth': '50%',
                                                'fieldbuttons': [{'id': 'add_itinerario', 'style': "float: right",
                                                'tooltiptext': 'Agregar', 'btnclasscolor': 'btn-success',
                                                'btnfaicon': 'fa-plus-square'}]}))
    numeroresolucion = forms.CharField(label=u'Número Resolución del Órgano Colegiado Superior de aprobación del programa (OCS)', max_length=100, required=False, widget=forms.TextInput(attrs={'formwidth': '50%', 'separator': 'true'}))
    fechaaprobacion = forms.DateField(label=u"Fecha de aprobación", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    sesionocs = forms.IntegerField(label=u'Número de de Sesión del OCS', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0','formwidth': '50%'}))
    # anexoresolucion = ExtFileField(label=u'Anexo resolución(OCS) PDF', required=False, help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))
    estructurainstitucional = forms.CharField(label=u'Estructura institucional', max_length=100, required=False,widget=forms.TextInput(attrs={'class': 'imp-100', 'separator': 'true'}))
    provincia = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.filter(pais_id=1, status=True).order_by('nombre'), required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    canton = forms.ModelChoiceField(label=u"Canton", queryset=Canton.objects.filter(status=True).order_by('nombre'), required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    parroquia = forms.ModelChoiceField(label=u"Parroquia", queryset=Parroquia.objects.filter(status=True).order_by('nombre'), required=True, widget=forms.Select(attrs={'formwidth': '100%'}))
    numeroresolucioncaces = forms.CharField( label=u'Número de Resolución de la IES/Resolución CACES/CES', max_length=100, required=False, widget=forms.TextInput(attrs={'formwidth': '50%'}))
    fechaaprobacioncaces = forms.DateField(label=u"Fecha de aprobación CACES", initial=datetime.now().date(), required=False, input_formats=['%d-%m-%Y'], widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'formwidth': '50%'}))
    # anexoresolucioncaces = ExtFileField(label=u'Anexo resolución(CACES) PDF', required=False,help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))

    def bloquearcampos(self):
        campo_modolectura(self, 'campoamplio', True)
        campo_modolectura(self, 'campoespecifico', True)
        campo_modolectura(self, 'campodetallado', True)

class DetalleItinerarioProgramaPacForm(forms.Form):
    nombreitinerario = forms.CharField(label=u'Nombre', max_length=200, required=True, widget=forms.TextInput())
    nivelitinerario = forms.ModelChoiceField(required=False, label=u'Itinerario', queryset=NivelMalla.objects.values_list('id', flat=True).filter(status=True, pk__in=[1,2,3,4,5,6,7,8,9]).order_by('id'), widget=forms.Select(attrs={'style': "width: 100%;"}))
    codigo = forms.CharField(label=u'Número de resolución del CES', max_length=500, required=True, widget=forms.TextInput())

class ConvenioPacForm(forms.Form):
    convenioinstitucional = forms.ModelChoiceField(required=False, label=u'Convenio', queryset=ConvenioEmpresa.objects.filter(status=True).order_by('empresaempleadora__nombre'), widget=forms.Select(attrs={'style': "width: 100%;"}))

class FuncionSustantivaDocenciaPacForm(forms.Form):
    objetivogeneral = forms.CharField(label=u'Objetivo General de la carrera/programa', required=False, widget=CKEditorUploadingWidget())
    objetivoespecifico = forms.CharField(label=u'Objetivos Específicos de la carrera/programa', required=False, widget=CKEditorUploadingWidget())
    # perfilingreso = forms.CharField(label=u'Perfil de ingreso', required=False, widget=CKEditorUploadingWidget(attrs={'separator': 'true'}))
    # requisitoingreso = forms.CharField(label=u'Requisitos de ingreso', required=False, widget=CKEditorUploadingWidget())
    perfilprofesional = forms.CharField(label=u'Perfil de profesional', required=False, widget=CKEditorUploadingWidget(attrs={'separator': 'true'}))
    requisitotitulacion = forms.CharField(label=u'Requisitos de titulación', required=False, widget=CKEditorUploadingWidget(attrs={'separator': 'true'}))
    aprobaciontrabajo = forms.ModelMultipleChoiceField(label=u'Opciones de aprobación del trabajo de la unidad de integración curricular / unidad de titulación. ', required=False, queryset=AprobacionTrabajoIntegracionCurricular.objects.filter(status=True))
    descripcionintegracioncurricular = forms.CharField(label=u'Breve descripción de las opciones de la unidad de integración curricular (¿Qué?,¿Cómo? y duración)', required=False, widget=CKEditorUploadingWidget())
    pertinencia = forms.CharField(label=u'Pertinencia', required=False, widget=CKEditorUploadingWidget(attrs={'separator': 'true'}))
    objetoestudio = forms.CharField(label=u'Objeto de estudio del proyecto',required=False, widget=CKEditorUploadingWidget(attrs={'separator': 'true'}))
    metodologiaambiente = forms.CharField(label=u'Metodologías y ambientes de aprendizaje', required=False, widget=CKEditorUploadingWidget())
    justificacion = forms.CharField(label=u'Justificación de la estructura curricular', required=False, widget=CKEditorUploadingWidget())

class DetallePerfilIngresoForm(forms.Form):
    alltitulos = forms.BooleanField(initial=False, label=u"¿Todo título de tercer nivel?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    titulo = forms.ModelMultipleChoiceField(label=u'Títulos', required=False, queryset=Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23, 30], status=True), widget=forms.SelectMultiple(attrs={
        'fieldbuttons': [{'id': 'add_titulo_perfil', 'tooltiptext': 'Agregar titulo', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-plus'}]}))
    experiencia = forms.BooleanField(initial=False, label=u"¿Necesita experiencia?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '100%'}))
    # cantidadexperiencia = forms.FloatField(label=mark_safe(u"Años de experiencia"), initial=0, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    cantidadexperiencia = forms.FloatField(label=mark_safe(u"Años de experiencia"), initial=0.0, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '1', 'formwidth': '50%'}))

class TituloPerfilIngresoForm(forms.Form):
    nombre = forms.CharField(label=u'Nombre', max_length=200, widget=forms.TextInput(attrs={'class': 'form-control','style':"width: 100%;"}))
    abreviatura = forms.CharField(label=u'Abreviatura', max_length=10,
                                  widget=forms.TextInput(attrs={'class': 'form-control', 'style':"width: 100%;"}))
    nivel = forms.ModelChoiceField(NivelTitulacion.objects.filter(status=True, tipo=1), label=u'Tipo de nivel',
                                  widget=forms.Select(attrs={'class': 'form-control nivel'}))
    grado = forms.ModelChoiceField(GradoTitulacion.objects.all(), required=False, label=u'Grado',
                                   widget=forms.Select(attrs={'class': 'form-control'}))
    areaconocimiento = forms.ModelChoiceField(label=u"Area conocimiento - Campo amplio", queryset=AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True),  widget=forms.Select(attrs={'class': 'select2'}))
    subareaconocimiento = forms.ModelChoiceField(label=u"Sub area conocimiento - Campo específico", queryset=SubAreaConocimientoTitulacion.objects.filter(status=True),  widget=forms.Select(attrs={'class': 'select2'}))
    subareaespecificaconocimiento = forms.ModelChoiceField(label=u"Sub area especificaconocimiento - Campo Detallado", queryset=SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True), widget=forms.Select(attrs={'class': 'select2'}))

    def adicionar(self):
        self.fields['subareaconocimiento'].queryset = SubAreaConocimientoTitulacion.objects.none()
        self.fields['subareaespecificaconocimiento'].queryset = SubAreaEspecificaConocimientoTitulacion.objects.none()


class DetalleRequisitoIngresoForm(forms.Form):
    requisito = forms.ModelMultipleChoiceField(label=u'Requisitos', required=False, queryset=Requisito.objects.filter(status=True))
    firmaelectronica = forms.BooleanField(initial=False, label=u"¿Firma electónica?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))

    def iniciar(self):
        requisitosadmision = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=2, status=True)
        self.fields['requisito'].queryset = Requisito.objects.filter(pk__in=requisitosadmision,status=True)

class DetallePreguntasPerfilegresoDocenciaPacForm(forms.Form):
    preguntaspac = forms.CharField(label=u'Pregunta', initial='¿ ?', required=True, widget=forms.Textarea(attrs={'rows': '4', 'class': 'imp-100'}))
    respuestapac = forms.CharField(label=u'Respuesta', required=False, widget=CKEditorUploadingWidget())

class DetalleFuncionSustantivaDocenciaPacForm(forms.Form):
    asignatura = forms.ModelChoiceField(label=u"Asignatura", queryset=Asignatura.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-50','style':"width: 100%;"}))
    nivelperiodoacademico = forms.ModelChoiceField(label=u'Periodo Académico Ordinario', required=False, queryset=NivelMalla.objects.filter(status=True).order_by('id'), widget=forms.Select(attrs={'class': 'imp-50','style':"width: 100%;"}))
    # itinerariomencion = forms.CharField(label=u'Nombre del Itinerario/Mención', max_length=200,
    #                                   required=False, widget=forms.TextInput())
    unidadorganizacioncurricular = forms.ChoiceField(label=u"Unidad de organización curricular", choices=UNIDAD_ORGANIZACION_CURRICULAR, required=False,widget=forms.Select(attrs={'class': 'imp-100','style':"width: 100%;"}))
    horas = forms.IntegerField(label=mark_safe(u"<strong>Horas Totales de la asignatura</strong>"), initial=0, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))
    creditos = forms.FloatField(label=mark_safe(u"<strong>Horas Créditos de la asignatura</strong>"), initial=0.0000, widget=forms.TextInput(attrs={'class': 'imp-numbermed-right', 'decimal': '4', 'formwidth': '50%'}))
    horasacdtotal = forms.FloatField(label=mark_safe(u"<strong>Horas Aprendizaje Contacto Docente (ACD) Totales</strong>"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasacdsemanal = forms.FloatField(label=mark_safe(u"<strong>Horas Aprendizaje Contacto Docente Semanales</strong>"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horaspresenciales = forms.FloatField(label=u"Horas ACD Presenciales Totales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horaspresencialessemanales = forms.FloatField(label=u"Horas ACD Presenciales Semanales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasvirtualtotal = forms.FloatField(label=u"Horas ACD Virtuales Totales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasvirtualsemanal = forms.FloatField(label=u"Horas ACD Virtuales Semanales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasapetotal = forms.FloatField(label=mark_safe(u"<strong>Horas Aprendizaje Práctico Experimental(APE) Totales</strong>"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasapesemanal = forms.FloatField(label=mark_safe(u"<strong>Horas Aprendizaje Práctico Experimental Semanales</strong>"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasapeasistotal = forms.FloatField(label=u"Horas APE asistidas Totales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasapeasissemanal = forms.FloatField(label=u"Horas APE asistidas Semanales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasapeautototal = forms.FloatField(label=u"Horas APE no asistidas Totales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasapeautosemanal = forms.FloatField(label=u"Horas APE no asistidas Semanales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasautonomas = forms.FloatField(label=mark_safe(u"<strong>Horas Aprendizaje Autónomo(AA) Totales</strong>"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasautonomassemanales = forms.FloatField(label=mark_safe(u"<strong>Horas Aprendizaje Autónomo Semanales</strong>"), initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasvinculaciontotal = forms.FloatField(label=u"Horas Vinculación Totales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasvinculacionsemanal = forms.FloatField(label=u"Horas Vinculación Semanales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horasppptotal = forms.FloatField(label=u"Horas Prácticas Pre-profesionales Totales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horaspppsemanal = forms.FloatField(label=u"Horas Prácticas Pre-profesionales semanales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    horascolaborativototal = forms.FloatField(label=u"Horas Aprendizaje colaborativo Totales", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))
    valorhoramodulo = forms.FloatField(label=u"Valor hora del módulo: ", initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '2', 'formwidth': '50%'}))

    def editar(self, valor):
        self.fields['nivelperiodoacademico'].queryset = NivelMalla.objects.values_list('id', flat=True).filter(status=True, id__lte=valor).order_by('id')

    # se filtro la asignatura que pertenezcan a una asignaturamalla, carrera y malla en especifico, con el siguiente queryset
    def masignatura(self, valor):
        self.fields['asignatura'].queryset = Asignatura.objects.filter(id__in=AsignaturaMalla.objects.values_list('asignatura_id', flat=True).filter(status=True, malla__carrera_id=valor))

    def bloquearcampocomponentehoracredito(self):
        # campo_modolectura(self, 'horasacdtotal', True)
        campo_modolectura(self, 'horasacdsemanal', True)
        # campo_modolectura(self, 'horasapetotal', True)
        campo_modolectura(self, 'horasapesemanal', True)
        campo_modolectura(self, 'horas', True)
        # campo_modolectura(self, 'creditos', True)
        campo_modolectura(self, 'horaspresenciales', True)
        campo_modolectura(self, 'horasapeasistotal', True)
        campo_modolectura(self, 'horasapeautototal', True)
        # campo_modolectura(self, 'horasautonomas', True)
        campo_modolectura(self, 'horasvirtualtotal', True)

    def bloquearasignatura(self):
        deshabilitar_campo(self, 'asignatura')

class FuncionSustantivaInvestigacionPacForm(forms.Form):
    investigacion = forms.CharField(label=u"investigacion", required=False, widget=CKEditorUploadingWidget())

class FuncionSustantivaVinculacionSociedadPacForm(forms.Form):
    componentevinculacion = forms.CharField(label=u'Componente de vinculación con la sociedad', required=False, widget=CKEditorUploadingWidget())
    modelopractica = forms.CharField(label=u'Modelo de prácticas pre profesionales de la carrera o prácticas profesionales del programa', required=False, widget=CKEditorUploadingWidget(attrs={'separator': 'true'}))

class InfraestructuraEquipamientoInformacionPacForm(forms.Form):
    descripcion = forms.CharField(label=u'Describa la plataforma tecnológica integral de infraestructura e infoestructura', required=False, widget=CKEditorUploadingWidget())

    aniosexperiencia = forms.CharField(label=u'Años de experiencia', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '35%', 'separator': 'true'}))
    numeropublicacion = forms.CharField(label=u'Cantidad de publicaciones', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '35%'}))
    dominiotics = forms.BooleanField(initial=False, label=u"¿Tiene dominio de TICS?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))

    # perfilprofesionaldirector= forms.CharField(label=u'Perfil profesional', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75', 'separator': 'true'}))
    cargofunciondirector= forms.CharField(label=u'Cargo / función', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    ciudaddirector= forms.CharField(label=u'Ciudad (Sede Matriz/ Sede/ Extensiones)', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    horassemanaies= forms.CharField(label=u'Horas de dedicación a la semana a la IES', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'style':"width: 15%;"}))
    tiporelacionlaboralies= forms.CharField(label=u'Tipo de relación laboral o vinculación a la IES', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class DetalleLaboratorioInfraestructuraPacForm(forms.Form):
    estructurainstitucional = forms.CharField(label=u'Estructura institucional', max_length=200, required=True, widget=forms.TextInput())
    # nombrelaboratorio = forms.ModelChoiceField(label=u"Nombre del laboratorio o taller", queryset=LaboratorioAcademia.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-50','style':"width: 100%;"}))
    aulalaboratorio = forms.ModelChoiceField(label=u"Laboratorio o taller", queryset=Aula.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-50','style':"width: 100%;"}))
    descripcion = forms.CharField(label=u"Descripción", max_length=200, required=False, widget=forms.TextInput())
    equipamiento = forms.CharField(label=u"Equipamiento", required=True, widget=CKEditorUploadingWidget())
    metroscuadrado = forms.CharField(label=u'Metros Cuadrados', max_length=30, initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "width: 15%;"}))
    puestotrabajo = forms.IntegerField(label=u'Puestos de trabajo', initial=0, required=True, widget=forms.NumberInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))

    # def iniciar(self):
    #     self.fields['aulalaboratorio'].queryset = Aula.objects.values_list('nombre', flat=True).filter(status=True).order_by('nombre')

class DetalleBibliotecaInfraestructuraPacForm(forms.Form):
    estructurainstitucional = forms.CharField(label=u'Estructura institucional', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    numerotitulo = forms.CharField(label=u'Número de títulos', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "width: 15%;"}))
    titulo = forms.CharField(label=u'Títulos', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    numerovolumen = forms.CharField(label=u'Número de volúmenes', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "width: 15%;"}))
    volumen = forms.CharField(label=u'Volúmenes', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    numerobasedatos = forms.CharField(label=u'Número de base de datos', max_length=30, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "width: 15%;"}))
    basedatos = forms.CharField(label=u'Base de datos', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    numerosuscripcion = forms.CharField(label=u'Número de suscripciones', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "width: 15%;"}))
    suscripcionrevista = forms.CharField(label=u'Suscripciones a revistas', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))

class DetalleAulaInfraestructuraPacForm(forms.Form):
    estructurainstitucional = forms.CharField(label=u'Estructura institucional', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-75'}))
    numeroaula = forms.CharField(label=u'Número de aulas', max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "width: 15%;" ,'title':'Cantidad extraída de total de aulas registradas en el sistema.'}))
    numeropuestotrabajoaula = forms.CharField(label=u'Número de puestos de trabajo por aula', initial=0, max_length=10, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'style': "width: 15%;"}))

    def numeroaulas(self):
        num = Aula.objects.filter(status=True, tipo_id=1).count()
        self.fields['numeroaula'].initial = num

class DetallePersonalAcademicoInfraestructuraPacForm(forms.Form):
    # perfildocente = forms.CharField(label=u'Perfil docente del Personal académico de la carrera/programa', required=True, widget=forms.Textarea(attrs={'rows': '3', 'class': 'imp-100'}))
    aniosexperiencia = forms.CharField(label=u'Años de experiencia', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '35%'}))
    numeropublicacion = forms.CharField(label=u'Cantidad de publicaciones', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'formwidth': '35%'}))
    dominiotics = forms.BooleanField(initial=False, label=u"¿Tiene dominio de TICS?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '30%'}))

    asignaturaimpartir = forms.ModelChoiceField(label=u"Asignatura a impartir", queryset=DetalleFuncionSustantivaDocenciaPac.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-50','style':"width: 100%;",'separator': 'True'}))
    ciudadpersonalacademico = forms.CharField(label=u'Ciudad (Sede Matriz/ Sede/ Extensiones)', max_length=200, required=False, widget=forms.TextInput())
    horadedicacionies = forms.ChoiceField(label=u"Horas de dedicación a la IES", choices=HORAS_DEDICACIÓN_IES, required=False,widget=forms.Select(attrs={'class': 'imp-100','style':"width: 100%;"}))
    horadedicacionsemanal = forms.CharField(label=u'Horas de dedicación semanal a la carrera/ programa', max_length=10, initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'style':"width: 15%;"}))
    tiempodedicacioncarrera = forms.ChoiceField(label=u'Tiempo de dedicación al carrera/ programa', choices=HORAS_DEDICACIÓN_PROGRAMA, required=False, widget=forms.Select(attrs={'class': 'imp-100','style':"width: 100%;"}))
    # tipopersonalcategoria = forms.ModelChoiceField(label=u"Tipo de personal académico/Categoría del docente", queryset=CategorizacionDocente.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-50','style':"width: 100%;"}))

    tipopersonalcategoria = forms.ModelChoiceField(label=u"Tipo de personal académico/Categoría del docente", queryset=TipoPersonalPac.objects.all(), required=False, widget=forms.Select(
    attrs = {'fieldbuttons': [
        {'id': 'add_registro_tipo_personal', 'tooltiptext': 'Agregar tipo personal', 'btnclasscolor': 'btn-success',
         'btnfaicon': 'fa-plus'}]}))

    def editar(self, funcion):
        self.fields['asignaturaimpartir'].queryset = DetalleFuncionSustantivaDocenciaPac.objects.filter(status=True, funcionsustantivadocenciapac=funcion).order_by('id')

class PerfilRequeridoPacForm(forms.Form):
    titulacion = forms.ModelChoiceField(label=u'Titulación', queryset=CamposTitulosPostulacion.objects.filter(status=True), required=False, widget=forms.Select())
    campoamplio = forms.CharField(label=u'Campo amplio', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    campoespecifico = forms.CharField(label=u'Campo especifico', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    campodetallado = forms.CharField(label=u'Campo detallado', max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'imp-100'}))

    def bloquearcampos(self):
        campo_modolectura(self, 'campoamplio', True)
        campo_modolectura(self, 'campoespecifico', True)
        campo_modolectura(self, 'campodetallado', True)

class TipoPersonalPacForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))


class TipoFormacionRedisenoForm(forms.Form):
    tipo = forms.ChoiceField(label=u"Tipo", choices=TIPO_FORMACION_REDISEÑO, required=True,widget=forms.Select(attrs={'class': 'imp-100','style':"width: 100%;"}))
    descripcion = forms.CharField(label=u'Descripción', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class PresupuestoPacColumnaForm(forms.Form):
    tipo = forms.ChoiceField(label=u"Tipo", choices=TIPOPRESUPUESTO_PAC, required=True,
                             widget=forms.Select(attrs={'class': 'imp-100', 'style': "width: 100%;"}))
    descripcioncol = forms.CharField(label=u'Descripcion Presupuesto', max_length=250, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    orden = forms.IntegerField(label=u'Orden', required=True,
                                widget=forms.NumberInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))

class PresupuestoPacFilaForm(forms.Form):
    descripcionfila = forms.CharField(label=u'Descripcion Presupuesto', max_length=250, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))
    orden = forms.IntegerField(label=u'Orden', required=True,
                                widget=forms.NumberInput(attrs={'class': 'imp-number', 'formwidth': '50%'}))

class TipoFormaPagoPacForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class FormaPagoPacForm(forms.Form):
    formapago = forms.ModelMultipleChoiceField(label=u'Forma de pago', required=False, queryset=TipoFormaPagoPac.objects.filter(status=True), widget=forms.SelectMultiple(attrs={
        'fieldbuttons': [{'id': 'add_forma_pago', 'tooltiptext': 'Agregar Forma de pago', 'btnclasscolor': 'btn-success', 'btnfaicon': 'fa-plus'}]}))

class AnexoPacForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripcion Anexo', max_length=300, required=True, widget=forms.Textarea(attrs={'rows': '3', 'class': 'imp-100'}))

class DetalleAnexoPacForm(forms.Form):
    # anexo = forms.ModelChoiceField(label=u"Anexo", queryset=AnexosPac.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    descripcion = forms.CharField(label=u'Descripción del Soporte', max_length=300, required=True, widget=forms.Textarea(attrs={'rows': '2', 'class': 'imp-100'}))

class DetalleAnexoPacForm(forms.Form):
    # anexo = forms.ModelChoiceField(label=u"Anexo", queryset=AnexosPac.objects.filter(status=True), required=False, widget=forms.Select(attrs={'class': 'imp-100'}))
    descripcion = forms.CharField(label=u'Descripción del Soporte', max_length=300, required=True, widget=forms.Textarea(attrs={'rows': '2', 'class': 'imp-100'}))
    archivo = ExtFileField(label=u'Anexo PDF', required=False,
                           help_text=u'Tamaño Maximo permitido 10Mb, en formato pdf', ext_whitelist=(".pdf",),
                           max_upload_size=10485760, widget=FileInput({'accept': 'application/pdf'}))

class CoordinadorPacForm(forms.Form):
    registro = forms.IntegerField(initial=0, required=True, label=u'Director/a o Coordinador/a', widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))

class TipoProcesoPacForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class TipoProgramaPacForm(forms.Form):
    descripcion = forms.CharField(label=u'Descripción', max_length=200, required=True, widget=forms.TextInput(attrs={'class': 'imp-100'}))

class JustificarTutoriaForm(forms.Form):
    horario = forms.ModelMultipleChoiceField(label=u'Horarios', required=True, queryset=HorarioTutoriaAcademica.objects.filter(status=True), widget=forms.SelectMultiple(attrs={'class': 'select2', 'multiple': 'multiple', 'style': 'width:100%'}))
    justificacionasistencia = forms.CharField(label=u'Observación', required=True, widget=forms.Textarea(attrs={'cols':10, 'rows': 10}))
    archivoevidencia = ExtFileField(label=u'Evidencia', required=False, ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png", ".docx"), max_upload_size=15000000,
                                    widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg docx'}))

    def asignar_horarios(self, horarios):
        self.fields['horario'].queryset = horarios


class SedeVirtualForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=300, required=True, widget=forms.TextInput({'col': '12'}))
    activa = forms.BooleanField(initial=True, label=u"Activo?", required=False, widget=forms.CheckboxInput(attrs={'col': '6'}))
    principal = forms.BooleanField(initial=False, label=u"Principal?", required=False, widget=forms.CheckboxInput(attrs={'col': '6'}))
    foto = ExtFileField(label=u'Foto', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato jpg, jpeg, png', ext_whitelist=(".jpg", ".jpeg", ".png"), max_upload_size=8194304, widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'png pdf jpg jpeg'}))
    referencias = forms.CharField(label=u'Dirección o Referencias', max_length=5000, required=False, widget=forms.Textarea(attrs={'col': '12', 'rows': '5'}))
    latitud = forms.FloatField(initial=0, label=u'Latitud', required=False, widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right'}))
    longitud = forms.FloatField(initial=0, label=u'Longitud', required=False, widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right'}))


class SedeVirtualPeriodoForm(FormModeloBase):
    periodo = forms.ModelChoiceField(label=u'Periodo académico', queryset=Periodo.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '12'}))


class LaboratorioVirtualForm(FormModeloBase):
    sedevirtual = forms.ModelChoiceField(label=u'Sede', queryset=SedeVirtual.objects.filter(status=True, activa=True), required=True, widget=forms.Select(attrs={'col': '12'}))
    tipo = forms.ModelChoiceField(label=u'Tipo', queryset=TipoAula.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '6'}))
    bloque = forms.ModelChoiceField(label=u'Bloque', queryset=Bloque.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '6'}))
    nombre = forms.CharField(label=u'Nombre del aula', max_length=100, required=True, widget=forms.TextInput({'col': '6'}))
    capacidad = forms.IntegerField(initial=25, required=True, label=u'Capacidad', widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    activo = forms.BooleanField(initial=True, label=u"Activo?", required=False, widget=forms.CheckboxInput(attrs={'col': '6'}))


class FechaPlanificacionSedeVirtualExamenForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha de planificación", initial=datetime.now().date(), required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'col': '12', 'pattern':"\d{4}-\d{2}-\d{2}"}))
    supervisor = forms.ModelChoiceField(label=u'Supervisor', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct().none(), required=False, widget=forms.Select(attrs={'col': '12'}))

    def edit(self, supervisor):
        if supervisor:
            self.fields['supervisor'].queryset = Persona.objects.filter(pk=supervisor)
            self.fields['supervisor'].initial = [supervisor]


class HorarioPlanificacionSedeVirtualExamenForm(forms.Form):
    horainicio = forms.TimeField(label=u"Hora inicio", required=True, initial=str(datetime.now().time()), input_formats=['%H:%M:%S'], widget=DateTimeInput(format='%H:%M:%S', attrs={'class': 'form-control selectorhora', 'col': '6'}))
    horafin = forms.TimeField(label=u"Hora fin", required=True, initial=str(datetime.now().time()), input_formats=['%H:%M:%S'], widget=DateTimeInput(format='%H:%M:%S', attrs={'class': 'form-control selectorhora', 'col': '6'}))


class AulaPlanificacionSedeVirtualExamenForm(forms.Form):
    aula = forms.ModelChoiceField(label=u'Aula', queryset=LaboratorioVirtual.objects.filter(status=True, activo=True), required=True, widget=forms.Select(attrs={'col': '12'}))
    supervisor = forms.ModelChoiceField(label=u'Supervisor', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct().none(), required=False, widget=forms.Select(attrs={'col': '12'}))
    responsable = forms.ModelChoiceField(label=u'Aplicador', queryset=Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct().none(), required=False, widget=forms.Select(attrs={'col': '12'}))
    # password = forms.CharField(label=u'Clave', max_length=10, required=False, widget=forms.TextInput(attrs={'col': '12'}))

    def filter_sede(self, sede, exclude_aulas=[]):
        eLaboratorioVirtuales = LaboratorioVirtual.objects.filter(status=True, sedevirtual=sede, activo=True)
        if len(exclude_aulas):
            eLaboratorioVirtuales = eLaboratorioVirtuales.exclude(pk__in=exclude_aulas)
        self.fields['aula'].queryset = eLaboratorioVirtuales

    def edit(self, supervisor, responsable):
        if supervisor:
            self.fields['supervisor'].queryset = Persona.objects.filter(pk=supervisor)
            self.fields['supervisor'].initial = [supervisor]
        if responsable:
            self.fields['responsable'].queryset = Persona.objects.filter(pk=responsable)
            self.fields['responsable'].initial = [responsable]


class HorarioExamenForm(forms.Form):
    coordinacion = forms.ModelChoiceField(label=u"Coordinacion", queryset=Coordinacion.objects.filter(status=True), required=True, widget=forms.Select(attrs={'formwidth': 'span8'}))#'class': 'imp-100', 'formwidth': '70%'
    sesion = forms.ModelChoiceField(label=u"Sesión", queryset=Sesion.objects.all(), widget=forms.Select(attrs={'formwidth': 'span4'}), required=False)#'class': 'imp-100', 'formwidth': '40%'
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Malla.objects.all(), required=False, widget=forms.Select(attrs={'formwidth': 'span6'}))
    nivel = forms.ModelChoiceField(label=u'Nivel', required=False, queryset=NivelMalla.objects.filter(status=True).order_by('id'), widget=forms.Select(attrs={'formwidth': 'span3'}))
    paralelo = forms.ModelChoiceField(label=u'Paralelo', required=False, queryset=Paralelo.objects.filter(status=True).order_by('id'), widget=forms.Select(attrs={'formwidth': 'span3'}))
    materia = forms.IntegerField(initial=0, required=False, label=u'Materia', widget=forms.TextInput(attrs={'select2search': 'true'}))
    aula = forms.CharField(label=u'Aula', max_length=300, required=True, widget=forms.TextInput({'formwidth': 'span6'}))
    fecha = forms.CharField(label=u'Fecha', max_length=300, required=True, widget=forms.TextInput({'formwidth': 'span2'}))
    horainicio = forms.CharField(label=u'Hora inicio', max_length=300, required=True, widget=forms.TextInput({'formwidth': 'span2'}))
    horafin = forms.CharField(label=u'Hora fin', max_length=300, required=True, widget=forms.TextInput({'formwidth': 'span2'}))
    tiporesponsable = forms.ChoiceField(label=u'Tipo ', choices=TIPO_RESPONSABLE_HORARIO_EXAMEN, required=False, widget=forms.Select(attrs={'formwidth': 'span3'}))
    responsable = forms.IntegerField(initial=0, required=False, label=u'Responsable', widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': 'span6'}))
    modelo = forms.ModelChoiceField(queryset=DetalleModeloEvaluativo.objects.all(), label=u"Modelo Evaluativo",  widget=forms.Select(attrs={'formwidth': 'span3'}))
    cantalumnos = forms.IntegerField(initial=0, required=True, label=u'Cantidad alumno:', widget=forms.NumberInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'formwidth': 'span3'}))
    validahorario = forms.BooleanField(initial=True, label=u"Validar Horario?", required=False, widget=forms.CheckboxInput(attrs={'formwidth': 'span3'}))

    def view(self):
        for field in self.fields:
            self.fields[field].widget.attrs['readonly'] = True
            self.fields[field].widget.attrs['disabled'] = True

    def bloquearcampos(self):
        campo_modolectura(self, 'aula', True)
        campo_modolectura(self, 'fecha', True)
        campo_modolectura(self, 'horainicio', True)
        campo_modolectura(self, 'horafin', True)
        campo_modolectura(self, 'sesion', True)
        campo_modolectura(self, 'carrera', True)
        campo_modolectura(self, 'nivel', True)


class AccesoExamenForm(forms.Form):
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), required=False, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'selectorfecha', 'col': '6', 'pattern': "\d{4}-\d{2}-\d{2}"}))
    limite = forms.ChoiceField(label=u"Duración del test(minutos)", choices=TIEMPO_DURACION, required=False, widget=forms.Select(attrs={'col': '6'}))
    horainicio = forms.TimeField(label=u"Hora inicio", required=True, initial=str(datetime.now().time()), input_formats=['%H:%M:%S'], widget=DateTimeInput(format='%H:%M:%S', attrs={'class': 'form-control selectorhora', 'col': '6'}))
    horafin = forms.TimeField(label=u"Hora fin", required=True, initial=str(datetime.now().time()), input_formats=['%H:%M:%S'], widget=DateTimeInput(format='%H:%M:%S', attrs={'class': 'form-control selectorhora', 'col': '6'}))
    password = forms.CharField(label=u'Clave', max_length=10, required=True, widget=forms.TextInput(attrs={'col': '6'}))
    intentos = forms.IntegerField(label=u'Intentos', initial=1, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))

    def clean(self):
        cleaned_data = super(AccesoExamenForm, self).clean()
        intentos = cleaned_data['intentos'] if 'intentos' in cleaned_data and cleaned_data['intentos'] else False
        if not intentos:
            self.add_error('intentos', forms.ValidationError('Favor ingrese números de intentos'))
        if intentos == 0:
            self.add_error('intentos', forms.ValidationError('Favor ingrese mayor a cero el números de intentos'))
        if intentos > 2:
            self.add_error('intentos', forms.ValidationError('Favor ingrese únicamente hasta dos intentos'))
        return cleaned_data

class ConfiguracionAfinidadForm(forms.Form):
    periodo = forms.ModelChoiceField(Periodo.objects.filter(status=True).order_by('-inicio'), required=True, label=u'Periodo',
                                     widget=forms.Select(attrs={'formwidth': '100%'}))
    def iniciar(self, periodosexcluir):
        self.fields['periodo'].queryset = Periodo.objects.filter(status=True).order_by('-inicio').distinct().exclude(pk__in=periodosexcluir)

class DetalleAfinidadForm(forms.Form):
    malla = forms.ModelChoiceField(Malla.objects.filter(status=True).order_by('-inicio'), required=True, label=u'Malla',
                                   widget=forms.Select(attrs={'formwidth': '100%'}))

class ResultadoAfinidadForm(forms.Form):
    asignaturamalla = forms.ModelChoiceField(AsignaturaMalla.objects.filter(status=True), required=True, label=u'Asignatura Malla', widget=forms.Select(attrs={'formwidth': '100%'}))
    profesor = ModelChoiceField(Profesor.objects.filter(status=True), required=True, label=u'Docente', widget=forms.Select(attrs={'select2search': 'true', 'formwidth': '100%'}))
    campoamplio = forms.BooleanField(required=False, label=u'¿Cumple Campo Amplio?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '4', 'data-switchery': 'true'}))
    campoespecifico = forms.BooleanField(required=False, label=u'¿Cumple Campo Específico?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '4', 'data-switchery': 'true'}))
    campodetallado = forms.BooleanField(required=False, label=u'¿Cumple Campo Detallado?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'col': '4', 'data-switchery': 'true'}))
    orden = forms.IntegerField(initial=0, label=u'Orden', required=True, widget=forms.NumberInput(attrs={'class': 'imp-number', 'col': '6', 'style': 'with:30%'}))

    def iniciar(self, malla):
        self.fields['asignaturamalla'].queryset = AsignaturaMalla.objects.filter(malla=malla).distinct()
        # campo_modolectura(self, 'orden', True)

    def editar(self, result):
        self.fields['asignaturamalla'].queryset = AsignaturaMalla.objects.filter(malla=result.detafinidad.malla).distinct()
        # campo_modolectura(self, 'orden', True)
        # self.fields['profesor'].queryset = Profesor.objects.filter(id=result.docente.id)

class MasivoAsignaturaResultadoForm(forms.Form):
    asignaturamalla = forms.ModelChoiceField(AsignaturaMalla.objects.filter(status=True), required=True, label=u'Asignatura', widget=forms.Select(attrs={'formwidth': '100%'}))

    def iniciar(self, idmalla):
        self.fields['asignaturamalla'].queryset = AsignaturaMalla.objects.filter(malla__id=idmalla).distinct()


class HorariosAulasLaboratoriosForm(FormModeloBase):
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=Bloque.objects.filter(status=True, tiene_lab=True).order_by('id'), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    aula = forms.ModelChoiceField(label=u"Aula", queryset=Aula.objects.filter(status=True, clasificacion=1).order_by('-id'), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    persona = forms.ModelChoiceField(queryset=Persona.objects.all().none(), required=True, label=u'Persona', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    concepto = forms.CharField(label=u"Concepto", max_length=500, widget=forms.Textarea(attrs={'col': '12', 'row': '2'}), required=True)
    tienemateria = forms.BooleanField(initial=False, label=u"¿Va a impartir una materia?", required=False, widget=forms.CheckboxInput(attrs={'col': '12'}))
    periodo = forms.ModelChoiceField(Periodo.objects.filter(status=True), required=False, label=u'Periodo', widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    carrera = forms.ModelChoiceField(label=u'Carrera', queryset=Carrera.objects.all().none(), required=False, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    nivel = forms.ModelChoiceField(label=u'Nivel', queryset=NivelMalla.objects.all().none(), required=False, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    # asignatura = forms.ModelChoiceField(label=u'Asignatura', queryset=Asignatura.objects.all().none(), required=False, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    materia = forms.ModelChoiceField(label=u'Paralelo', queryset=Materia.objects.all().none(), required=False, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    inicio = forms.DateField(label=u"Fecha de inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6','separator2':True,'separatortitle':'Detalle de Horarios'}), required=True)
    fin = forms.DateField(label=u"Fecha de fin", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    # dia = forms.CharField(label=u"Día", max_length=200, widget=forms.TextInput(attrs={'class':'form-control','col': '6'}), required=True)
    horainicio = forms.TimeField(label=u"Hora de Inicio", required=True, initial=str(datetime.now().time().strftime('%H:%M')),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '6'}))
    horafin = forms.TimeField(label=u"Hora de Fin", required=True, initial=str(datetime.now().time().strftime('%H:%M')),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '6'}))
    dia = forms.ChoiceField(label=u"Día", choices=DIAS_CHOICES, required=True, widget=forms.Select(attrs={'col': '6','crearboton': True, 'classbuton': 'agregarbtn'}))
    examen = forms.BooleanField(label=u'¿Examen?', required= False, widget=forms.CheckboxInput(attrs={'col':6}))


    def edit_per(self, idp):
        self.fields['persona'].queryset = Persona.objects.filter(pk=idp)
        self.fields['persona'].initial = [idp]

    def edit_mat(self, idm, idc, idn):
        self.fields['materia'].queryset = Materia.objects.filter(pk=idm)
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=idc)
        self.fields['nivel'].queryset = NivelMalla.objects.filter(pk=idn)
        self.fields['materia'].initial = [idm]
        self.fields['carrera'].initial = [idc]
        self.fields['nivel'].initial = [idn]

    def deshabilitar_campo(form, campo):
        form.fields[campo].widget.attrs['readonly'] = True

class HorariosAulasLabEditForm(FormModeloBase):
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=Bloque.objects.filter(status=True, tiene_lab=True).order_by('id'), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    aula = forms.ModelChoiceField(label=u"Aula", queryset=Aula.objects.filter(status=True, clasificacion=1).order_by('-id'), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    persona = forms.ModelChoiceField(queryset=Persona.objects.all().none(), required=True, label=u'Persona', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    concepto = forms.CharField(label=u"Concepto", max_length=500, widget=forms.Textarea(attrs={'col': '12', 'row': '2'}), required=True)
    tienemateria = forms.BooleanField(initial=False, label=u"¿Va a impartir una materia?", required=False, widget=forms.CheckboxInput(attrs={'col': '12'}))
    periodo = forms.ModelChoiceField(Periodo.objects.filter(status=True), required=False, label=u'Periodo', widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    carrera = forms.ModelChoiceField(label=u'Carrera', queryset=Carrera.objects.all().none(), required=False, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    materia = forms.ModelChoiceField(label=u'Materia', queryset=Materia.objects.all().none(), required=False, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    inicio = forms.DateField(label=u"Fecha de inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    fin = forms.DateField(label=u"Fecha de fin", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    horainicio = forms.TimeField(label=u"Hora de Inicio", required=True, initial=str(datetime.now().time().strftime('%H:%M')),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '6'}))
    horafin = forms.TimeField(label=u"Hora de Fin", required=True, initial=str(datetime.now().time().strftime('%H:%M')),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '6'}))
    dia = forms.ChoiceField(label=u"Día", choices=DIAS_CHOICES, required=True, widget=forms.Select(attrs={'col': '6'}))


    def edit_per(self, idp):
        self.fields['persona'].queryset = Persona.objects.filter(pk=idp)
        self.fields['persona'].initial = [idp]

    def edit_mat(self, idm, idc):
        self.fields['materia'].queryset = Materia.objects.filter(pk=idm)
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=idc)
        self.fields['materia'].initial = [idm]
        self.fields['carrera'].initial = [idc]

class NovedadAulaForm(FormModeloBase):
    horario = forms.CharField(label=u"Horario de Reservación", widget=forms.TextInput(attrs={'readonly': 'true'}))
    tiponovedad = forms.ModelChoiceField(queryset=TipoNovedad.objects.filter(status=True).order_by('id'), required=True, label=u'Tipo de Novedad:', widget=forms.Select(attrs={'formwidth': '100%'}))
    observacion = forms.CharField(label=u"Observacion", max_length=500, widget=forms.Textarea(attrs={'col': '12', 'row': '3'}), required=True)

class DistribucionPersonalAulasForm(FormModeloBase):
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=Bloque.objects.filter(status=True, tiene_lab=True).order_by('id'), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    persona = forms.ModelChoiceField(queryset=Persona.objects.filter(status=True, perfilusuario__administrativo__isnull=False), required=True, label=u'Encargado', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    aula = forms.ModelChoiceField(label=u"Aula", queryset=Aula.objects.filter(status=True, clasificacion=1).order_by('-id'), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12','separator2':True,'separatortitle':'Detalle de Distribución'}))
    inicio = forms.DateField(label=u"Fecha de inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    fin = forms.DateField(label=u"Fecha de fin", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    horainicio = forms.TimeField(label=u"Hora de Inicio", required=True, initial=str(datetime.now().time().strftime('%H:%M')),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '6','crearboton': True, 'classbuton': 'agregarbtn'}))
    horafin = forms.TimeField(label=u"Hora de Fin", required=True, initial=str(datetime.now().time().strftime('%H:%M')),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '6'}))

class DistribucionPersonalAulasEditForm(FormModeloBase):
    bloque = forms.ModelChoiceField(label=u"Bloque", queryset=Bloque.objects.filter(status=True, tiene_lab=True).order_by('id'), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    persona = forms.ModelChoiceField(queryset=Persona.objects.filter(status=True, perfilusuario__administrativo__isnull=False), required=True, label=u'Encargado', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '12'}))
    aula = forms.ModelChoiceField(label=u"Aula", queryset=Aula.objects.filter(status=True, clasificacion=1).order_by('-id'), required=True, widget=forms.Select(attrs={'class':'form-control', 'col': '12'}))
    inicio = forms.DateField(label=u"Fecha de inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    fin = forms.DateField(label=u"Fecha de fin", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    horainicio = forms.TimeField(label=u"Hora de Inicio", required=True, initial=str(datetime.now().time().strftime('%H:%M')),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '6'}))
    horafin = forms.TimeField(label=u"Hora de Fin", required=True, initial=str(datetime.now().time().strftime('%H:%M')),
                                 input_formats=['%H:%M'],
                                 widget=DateTimeInput(format='%H:%M', attrs={'col': '6'}))

class PantallaAulaForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", required=True, widget=forms.Textarea(attrs={'rows':'2'}))
    aula = forms.ModelMultipleChoiceField(queryset=Aula.objects.filter(status=True).distinct(), required=True, label=u'Aulas', widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'col': '12'}))

class TipoNovedadForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", required=True, max_length=400 ,widget=forms.TextInput(attrs={'rows':'2'}))

class ReportesFechas(FormModeloBase):
    desde = forms.DateField(label=u"Desde", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    hasta = forms.DateField(label=u"Hasta", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    tiponovedad = forms.ModelMultipleChoiceField(label=u"Tipo novedad",queryset=TipoNovedad.objects.filter(status=True).order_by('descripcion'),required=False, widget=forms.SelectMultiple(attrs={'class': 'form-control select2', 'col': '12'}))
    aula = forms.ModelChoiceField(label=u"Aula", queryset=Aula.objects.filter(status=True, clasificacion=1).order_by('-id'), required=False, widget=forms.Select(attrs={'class': 'form-control', 'col': '12'}))

    def reservas_horarios(self):
        #del self.fields['aula']
        del self.fields['tiponovedad']

class CierreIngresoForm(FormModeloBase):
    observacion = forms.CharField(label=u"Observacion", required=True, widget=forms.Textarea(attrs={'rows':'2'}))
    tiponovedad = forms.ModelChoiceField(queryset=TipoNovedad.objects.filter(status=True,), required=True, label=u'Tipo novedad', widget=forms.Select(attrs={'class': 'form-control select2', 'col': '6'}))
    clasenovedad = forms.ChoiceField(label=u"Clase novedad", choices=CLASE_NOVEDAD, required=True, widget=forms.Select(attrs={'col': '6',}))

class CronogramaDiaNoLaborableForm(FormModeloBase):
    motivo = forms.CharField(label=u'Motivo', required=True, widget=forms.TextInput())
    fini = forms.DateField(label=u"F. Inicio", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    ffin = forms.DateField(label=u"F. Fin", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)


class PlanificacionParaleloForm(FormModeloBase):
    periodo = forms.ModelChoiceField(Periodo.objects.filter(status=True, clasificacion=2, activo=True), required=False, label=u'Periodo: ', widget=forms.Select(attrs={'formwidth': '100%', 'col':'12', 'style':'width:100%'}))
    paralelos = forms.CharField(label=u"Paralelos: ", initial=1, widget=forms.TextInput(attrs={'class': 'imp-100', 'col':'6', 'type':'number', 'min':'0', 'controlwidth':'100%', 'formwidth': '50%'}))
    fechalimiteplanificacion = forms.DateField(label=u"F. limite planificación", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'class': 'form-control','col': '6'}), required=True)

    def _init(self, **kwargs):
        self.fields['periodo'].initial = [kwargs.pop('periodo')]

class ConstatacionFisicaLaboratoriosForm(FormModeloBase):
    activo = forms.IntegerField(initial=0, required=False, label=u'Activo',widget=forms.TextInput(attrs={'select2search': True,'class':'form-control','col': '12'}))
    aula = forms.ModelChoiceField(Aula.objects.filter(status=True, clasificacion=1), required=True, label=u'Aula',widget=forms.Select(attrs={'formwidth': '50%', 'col':'6', 'style':'width:100%'}))
    estado = forms.ChoiceField(choices=ESTADO_CONSTATACION,required=True,label=u'Estado', widget=forms.Select(attrs={'col': '6'}))
    fecha_constata = forms.DateField(label=u"Fecha constata", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=True)
    hora_constata = forms.TimeField(label=u"Hora constata", required=True, initial=str(datetime.now().time().strftime('%H:%M:%S')),
                                 input_formats=['%H:%M:%S'], widget=DateTimeInput(format='%H:%M:%S', attrs={'col': '6'}))
    observacion = forms.CharField(label=u'Observación', max_length=10000, widget=forms.Textarea({'rows': '3'}), required=True)


class PresidenteCursoForm(FormModeloBase):
    from inno.models import EstudiantesCandidatosaPresidentesdeCurso
    # presidente = forms.IntegerField(initial=0, required=False, label=u'Presidente',widget=forms.TextInput(attrs={'select2search': True,'class':'form-control','col': '12'}))
    presidente = forms.ModelChoiceField(label=u"Representante de curso", queryset=EstudiantesCandidatosaPresidentesdeCurso.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12', 'class': 'select2', 'placeholder': u'Seleccione el representante estudiantil'}))
    desde = forms.DateField(label=u"Desde", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=False)
    hasta = forms.DateField(label=u"Hasta", initial=datetime.now().date(), widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}), required=False)
    # activo = forms.BooleanField(initial=False, label=u"Activo", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '10%'}))
    def __init__(self, *args, **kwargs):
        # Obtener el `id` del período desde los parámetros
        periodo_id = kwargs.pop('periodo_id', None)
        # Llamar al constructor de la superclase (FormModeloBase)
        super(PresidenteCursoForm, self).__init__(*args, **kwargs)
        # Si el `periodo_id` está presente, realizar la consulta a la tabla `Periodo`
        if periodo_id:
                # Obtener el período con el id proporcionado
                periodo = Periodo.objects.get(pk=periodo_id, status=True)
                # Agregar las restricciones de min y max a los widgets
                self.fields['desde'].widget.attrs['min'] = periodo.inicio.strftime('%Y-%m-%d')
                self.fields['desde'].widget.attrs['max'] = periodo.fin.strftime('%Y-%m-%d')
                self.fields['hasta'].widget.attrs['min'] = periodo.inicio.strftime('%Y-%m-%d')
                self.fields['hasta'].widget.attrs['max'] = periodo.fin.strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        desde = cleaned_data.get('desde')
        hasta = cleaned_data.get('hasta')
        # Validación: 'Hasta' no puede ser menor que 'Desde'
        if desde and hasta and hasta < desde:
            raise NameError("La fecha 'Hasta' no puede ser anterior a la fecha 'Desde'.")
        return cleaned_data

class FirmaGrupoTitulacionForm(forms.Form):
    profesor = forms.IntegerField(initial=0, required=False, label=u'Profesor', widget=forms.Select({'col': '12', }))


class InsumoInformeInternadoRotativoForm(FormModeloBase):
    motivacionjuridica = forms.CharField(label=u'Marco Jurídico', widget=forms.Textarea({'rows': '3', 'class': 'ckeditor ', 'col': '12'}), required=True)
    activo = forms.BooleanField(initial=True, label=u"Activo", required=False, widget=forms.CheckboxInput(attrs={'formwidth': '10%', 'class':'js-switch'}))


class TecnicoAsociadoProyectoVinculacionForm(FormModeloBase):
    persona = forms.ModelChoiceField(label=u" Persona responsable:", queryset=Persona.objects.none(), required=True, widget=forms.Select(attrs={'col': '6', 'style': 'width:100%', 'class': 'validate[required]'}))
    cargo = forms.CharField(label=u"Cargo: ", widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6', 'placeholder': u'Ingrese el cargo...'}))
    reemplaza_lider = forms.BooleanField(label=u'¿Reemplaza al lider del proyecto?', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'class': 'js_switch'}))

    def delpersona(self):
        del self.fields['persona']


class SolictudAperturaClaseVirtualForm(FormModeloBase):
    descripcion = forms.CharField(label="Descripción", required=True, widget=forms.Textarea(attrs={'cols': 50, 'rows': 4, 'col': '12', 'style': 'resize: none'}))
    archivo = ExtFileField(label='Archivo', required=False, help_text='Tamaño máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf', 'class': 'dropify'}), max_upload_size=2194304)


class TerminosCondicionesForm(FormModeloBase):
    titulo = forms.CharField(label=u"Título: ", widget=forms.TextInput(attrs={'class': 'form-control', 'col': '12', 'placeholder': u'Ingrese el título...'}))
    detalle = forms.CharField(label=u"Detalle: ", widget=forms.Textarea({'rows': '3', 'class': 'ckeditor ', 'col': '12'}))
    visible = forms.BooleanField(label=u'¿Se encuentra visible?: ', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'class': 'js_switch'}))
    legalizar = forms.BooleanField(label=u'¿Se debe legalizar?: ', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '12', 'class': 'js_switch'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


ESTADO_SOLICITUD = (
    (2, u"APROBADO"),
    (3, u"RECHAZADO"),
)


class GestionarAperturaClaseVirtualForm(FormModeloBase):
    estadosolicitud = forms.ChoiceField(label=u'Estado', required=True, choices=ESTADO_SOLICITUD, widget=forms.Select(attrs={'class': 'form-control'}))
    todoperiodo = forms.BooleanField(label=u'¿Aplica para todo el periodo? ', initial=True, required=False,
                                     widget=forms.CheckboxInput(attrs={'col': '6', 'class': 'js-switch', 'help_text_switchery': True }))
    fechainicio = forms.DateField(label=u"Desde", initial=datetime.now().date(), required=False,
                                  input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',
                                                                                   attrs={'class': 'selectorfecha',
                                                                                          'col': '3'}))
    fechafin = forms.DateField(label=u"Hasta", initial=datetime.now().date(), required=False,
                            input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',
                                                                             attrs={'class': 'selectorfecha',
                                                                                    'col': '3'}))
    descripcionaprobador = forms.CharField(label=u'Observacion', max_length=2000, required=True, widget=forms.Textarea(attrs={'rows': '3', 'style': 'text-transform:none; resize: none;', 'class': 'form-control'}))


class ActaResponsabilidadForm(FormModeloBase):
    actaresponsabilidad = ExtFileField(label='Archivo', required=True, help_text='Tamaño máximo permitido 2Mb, en formato .pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf', 'class': 'dropify'}), max_upload_size=2194304)
    observacion = forms.CharField(label=u'Observación', max_length=750, help_text=u'Puede ingresar como máximo 750 caracteres' ,required=False, widget=forms.Textarea(attrs={'rows': '7', 'style': 'text-transform:none; resize: none;', 'class': 'form-control'}))


class PracticasPreprofesionalesInscripcionSaludForm(forms.Form):
    inscripcion = forms.IntegerField(initial=0, required=False, label=u'Alumno/Carrera', widget=forms.TextInput(attrs={'select2search': 'true', 'col': '12'}))
    itinerario = forms.ModelChoiceField(label=u"Itinerario", queryset=ItinerariosMalla.objects.none(), required=False, widget=forms.Select(attrs={'col': '12'}))
    confippp = forms.ModelChoiceField(label=u"Configuración oferta", queryset=ConfiguracionInscripcionPracticasPP.objects.none(), required=False, widget=forms.Select(attrs={'col': '12'}))
    fechadesde = forms.DateField(label=u"Fecha desde", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6', 'type': 'date'}), required=True)
    fechahasta = forms.DateField(label=u"Fecha hasta", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6', 'type': 'date'}), required=True)
    estadopreinscripcion = forms.ChoiceField(label=u'Estado Pre Incripción', choices=ESTADO_PREINSCRIPCIONPPP, widget=forms.Select(attrs={'col': '6'}), required=False)
    numerohora = forms.IntegerField(label=u'Número Hora', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'col': '6'}))
    tutorunemi = forms.ModelChoiceField(label=u"Tutor UNEMI", queryset=Profesor.objects.none(), required=False, widget=forms.Select(attrs={'col': '6'}))
    supervisor = forms.IntegerField(initial=0, required=True, label=u'Supervisor UNEMI', widget=forms.TextInput(attrs={'select2search': 'true', 'col': '6'}))
    asignacionempresapractica = forms.ModelChoiceField(label=u"Asignación de empresa", queryset=AsignacionEmpresaPractica.objects.none(), required=True, widget=forms.Select(attrs={'col': '12'}))
    otraempresaempleadora = forms.CharField(label=u"Otra Empresa Empleadora", max_length=600, required=False, widget=forms.TextInput(attrs={'col': '6'}))
    convenio = forms.IntegerField(initial=0, required=False, label=u'Convenio de la empresa', widget=forms.TextInput(attrs={'select2search': 'true', 'col': '6'}))
    lugarpractica = forms.ModelChoiceField(label=u"Lugar de la práctica", queryset=Canton.objects.filter(status=True, provincia__pais_id=1), required=True, widget=forms.Select(attrs={'col':'6'}))
    tipoinstitucion = forms.ChoiceField(choices=TIPO_INSTITUCION, required=False, label=u'Tipo Institución', widget=forms.Select(attrs={'col':'6'}))
    periodoevidencia = forms.ModelChoiceField(label=u"Periodo de evidencias", queryset=CabPeriodoEvidenciaPPP.objects.none(), required=True, widget=forms.Select(attrs={'col':'12'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea(attrs={'rows': '2', 'col': '12'}))

    def iniciar(self, pre):
        self.fields['inscripcion'].widget.attrs['descripcion'] = pre.inscripcion.persona.nombre_completo()
        self.fields['inscripcion'].initial = pre.inscripcion.id
        deshabilitar_campo(self, 'inscripcion')
        if pre.itinerariomalla:
            self.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(pk=pre.itinerariomalla.id)
            self.fields['itinerario'].initial = pre.itinerariomalla.id
            deshabilitar_campo(self, 'itinerario')
            # self.fields['confippp'].queryset = ConfiguracionInscripcionPracticasPP.objects.filter(itinerariomalla__id=pre.itinerariomalla.id, estado=2)
            self.fields['confippp'].queryset = ConfiguracionInscripcionPracticasPP.objects.annotate(inscritos=Count('historialinscricionoferta__id', filter=F('historialinscricionoferta__status'))
                                                                                                    ).filter(itinerariomalla__id=pre.itinerariomalla.id, estado=2, cupo__gt=F('inscritos'))
        else:
            self.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(malla__carrera=pre.inscripcion.carrera)

    def ocultarcampos(self):
        del self.fields['fechadesde']
        del self.fields['fechahasta']
        del self.fields['numerohora']
        del self.fields['supervisor']
        del self.fields['convenio']
        del self.fields['otraempresaempleadora']
        del self.fields['lugarpractica']
        del self.fields['tipoinstitucion']
        self.fields['periodoevidencia'].required = False

    def init(self, iti, tutor, asigemp, perevi, confippp):
        self.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(pk=iti)
        self.fields['tutorunemi'].queryset = Profesor.objects.filter(pk=tutor)
        self.fields['confippp'].queryset = ConfiguracionInscripcionPracticasPP.objects.filter(pk=confippp)
        self.fields['asignacionempresapractica'].queryset = AsignacionEmpresaPractica.objects.filter(pk=asigemp)
        self.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(pk=perevi)
        self.fields['itinerario'].initial = iti
        self.fields['tutorunemi'].initial = tutor
        self.fields['asignacionempresapractica'].initial = asigemp
        self.fields['periodoevidencia'].initial = perevi

    def cargar_estado(self):
        lista = []
        for est in ESTADO_PREINSCRIPCIONPPP:
            if not est[0] in [1, 5]:
                lista.append([est[0], est[1]])
        self.fields['estadopreinscripcion'].choices = lista


class PracticasPreprofesionalesInscripcionMasivoEstudianteSaludForm(FormModeloBase):
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.none(), required=False, widget=forms.Select())
    itinerario = forms.ModelChoiceField(label=u"Itinerario", queryset=ItinerariosMalla.objects.none(), required=False, widget=forms.Select())
    inscripciones = forms.ModelChoiceField(label=u"Alumnos", queryset=DetallePreInscripcionPracticasPP.objects.none(), required=False, empty_label=None, widget=forms.Select(attrs={'multiple': 'multiple'}))
    confippp = forms.ModelChoiceField(label=u"Configuración oferta", queryset=ConfiguracionInscripcionPracticasPP.objects.none(), required=False, widget=forms.Select(attrs={'col': '12'}))
    estadopreinscripcion = forms.ChoiceField(label=u'Estado PreInscripción', choices=ESTADO_PREINSCRIPCIONPPP, widget=forms.Select(attrs={'col': '6'}), required=False)
    numerohora = forms.IntegerField(label=u'Número Hora', initial=0, required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'col': '6'}))
    fechadesde = forms.DateField(label=u"Fecha desde", widget=DateTimeInput(attrs={'class': 'selectorfecha',  'col': '6'}), required=True)
    fechahasta = forms.DateField(label=u"Fecha hasta", widget=DateTimeInput(attrs={'class': 'selectorfecha',  'col': '6'}), required=True)
    tutorunemi = forms.ModelChoiceField(label=u"Tutor UNEMI", queryset=Profesor.objects.none(), required=False, widget=forms.Select(attrs={'col': '6'}))
    supervisor = forms.IntegerField(initial=0, required=False, label=u'Supervisor UNEMI', widget=forms.TextInput(attrs={'select2search': 'true', 'col': '6'}))
    asignacionempresapractica = forms.ModelChoiceField(label=u"Asignación de empresa", queryset=AsignacionEmpresaPractica.objects.none(), required=True, widget=forms.Select(attrs={'col': '12'}))
    otraempresaempleadora = forms.CharField(label=u"Otra Empresa Empleadora", max_length=600, required=False, widget=forms.TextInput(attrs={'col': '6'}))
    convenio = forms.IntegerField(initial=0, required=False, label=u'Convenio de la empresa', widget=forms.TextInput(attrs={'select2search': 'true', 'col': '6'}))
    lugarpractica = forms.ModelChoiceField(label=u"Lugar de la práctica", queryset=Canton.objects.filter(status=True, provincia__pais_id=1), required=True, widget=forms.Select(attrs={'col': '6'}))
    tipoinstitucion = forms.ChoiceField(choices=TIPO_INSTITUCION, required=False, label=u'Tipo Institución', widget=forms.Select(attrs={'col': '6'}))
    periodoevidencia = forms.ModelChoiceField(label=u"Periodo de evidencias", queryset=CabPeriodoEvidenciaPPP.objects.none(), required=True, widget=forms.Select(attrs={'col': '12'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea(attrs={'rows': '2', 'col': '12'}))

    def init(self, carr, iti, insc, tutor, cant, asigemp, perevi, confippp):
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=carr)
        self.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(pk=iti)
        self.fields['inscripciones'].queryset = DetallePreInscripcionPracticasPP.objects.filter(pk__in=insc)
        self.fields['tutorunemi'].queryset = Profesor.objects.filter(pk=tutor)
        self.fields['lugarpractica'].queryset = Canton.objects.filter(pk=cant)
        self.fields['asignacionempresapractica'].queryset = AsignacionEmpresaPractica.objects.filter(pk=asigemp)
        self.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(pk=perevi)
        self.fields['confippp'].queryset = ConfiguracionInscripcionPracticasPP.objects.filter(pk=confippp)

        self.fields['carrera'].initial = carr
        self.fields['itinerario'].initial = iti
        self.fields['inscripciones'].initial = insc
        self.fields['tutorunemi'].initial = tutor
        self.fields['lugarpractica'].initial = cant
        self.fields['asignacionempresapractica'].initial = asigemp
        self.fields['periodoevidencia'].initial = perevi

    def iniciarform(self, qscarreras):
        self.fields['carrera'].queryset = Carrera.objects.filter(status=True, id__in=qscarreras).order_by('nombre')

    def cargar_estado(self):
        lista = []
        for est in ESTADO_PREINSCRIPCIONPPP:
            if not est[0] in [1, 5]:
                lista.append([est[0], est[1]])
        self.fields['estadopreinscripcion'].choices = lista

    def ocultarcampos(self):
        del self.fields['fechadesde']
        del self.fields['fechahasta']
        del self.fields['numerohora']
        del self.fields['supervisor']
        del self.fields['convenio']
        del self.fields['otraempresaempleadora']
        del self.fields['tipoinstitucion']
        self.fields['lugarpractica'].required = False
        self.fields['periodoevidencia'].required = False

    def asignarmasivo(self, tipo):
        del self.fields['estadopreinscripcion']
        del self.fields['fechadesde']
        del self.fields['fechahasta']
        del self.fields['numerohora']
        if tipo == 1:
            del self.fields['tutorunemi']
            self.fields['supervisor'].widget.attrs['col'] = "12"
        else:
            del self.fields['supervisor']
            self.fields['tutorunemi'].widget.attrs['col'] = "12"
        del self.fields['asignacionempresapractica']
        del self.fields['convenio']
        del self.fields['otraempresaempleadora']
        del self.fields['lugarpractica']
        del self.fields['tipoinstitucion']
        del self.fields['periodoevidencia']
        del self.fields['observacion']


class AsignacionMasivoSaludForm(FormModeloBase):
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.none(), required=False, widget=forms.Select())
    itinerario = forms.ModelChoiceField(label=u"Itinerario", queryset=ItinerariosMalla.objects.none(), required=False, widget=forms.Select())
    estado = forms.ChoiceField(choices=ESTADO_PREINSCRIPCIONPPP, required=False, label=u'Estado', widget=forms.Select(attrs={'col': '12'}))
    inscripciones = forms.ModelChoiceField(label=u"Alumnos", queryset=DetallePreInscripcionPracticasPP.objects.none(), required=False, empty_label=None, widget=forms.Select(attrs={'multiple': 'multiple'}))
    tutorunemi = forms.IntegerField(initial=0, required=False, label=u'Tutor UNEMI', widget=forms.TextInput(attrs={'select2search': 'true', 'col': '12'}))
    supervisor = forms.IntegerField(initial=0, required=False, label=u'Supervisor UNEMI', widget=forms.TextInput(attrs={'select2search': 'true', 'col': '12'}))
    responsable = forms.ModelChoiceField(label=u"Responsable centro salud", queryset=ResponsableCentroSalud.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12'}))

    def iniciarform(self, qscarreras):
        self.fields['carrera'].queryset = Carrera.objects.filter(status=True, id__in=qscarreras).order_by('nombre')

    def asignarmasivo(self, tipo):
        if tipo == 1:
            del self.fields['tutorunemi']
            del self.fields['responsable']
            self.fields['supervisor'].required = True
        if tipo == 2:
            del self.fields['supervisor']
            del self.fields['responsable']
            self.fields['tutorunemi'].required = True
        if tipo == 3:
            del self.fields['estado']
            del self.fields['tutorunemi']
            del self.fields['supervisor']
            self.fields['responsable'].required = True

    def cargar_estado(self):
        lista = []
        for est in ESTADO_PREINSCRIPCIONPPP:
            if not est[0] in [3, 5, 6]:
                lista.append([est[0], est[1]])
        self.fields['estado'].choices = lista

    def init(self, carr, iti, insc):
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=carr)
        self.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(pk=iti)
        self.fields['inscripciones'].queryset = DetallePreInscripcionPracticasPP.objects.filter(pk__in=insc)
        self.fields['carrera'].initial = carr
        self.fields['itinerario'].initial = iti
        self.fields['inscripciones'].initial = insc

class MasivoPreinscripcionSaludForm(FormModeloBase):
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.none(), required=False, widget=forms.Select())
    inscripciones = forms.ModelChoiceField(label=u"Alumnos", queryset=Inscripcion.objects.none(), required=False, empty_label=None, widget=forms.Select(attrs={'multiple': 'multiple'}))
    itinerariomalla = forms.ModelMultipleChoiceField(label=u"Itinerarios", queryset=ItinerariosMalla.objects.none(), required=False, widget=forms.SelectMultiple(attrs={'multiple': 'multiple'}))
    estado = forms.ChoiceField(label=u'Estado', choices=ESTADO_PREINSCRIPCIONPPP, widget=forms.Select(attrs={'formwidth': '100%'}), required=False)

    def iniciarform(self, qscarreras):
        self.fields['carrera'].queryset = Carrera.objects.filter(status=True, id__in=qscarreras).order_by('nombre')

    def cargar_estado(self):
        lista = []
        for est in ESTADO_PREINSCRIPCIONPPP:
            if not est[0] in [3, 5, 6]:
                lista.append([est[0], est[1]])
        self.fields['estado'].choices = lista

    def init(self, carr, iti, insc):
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=carr)
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(pk__in=iti)
        self.fields['inscripciones'].queryset = Inscripcion.objects.filter(pk__in=insc)
        self.fields['carrera'].initial = carr
        self.fields['itinerariomalla'].initial = iti
        self.fields['inscripciones'].initial = insc

class MasivoEmpresaSaludForm(FormModeloBase):
    carrera = forms.ModelChoiceField(label=u"Carrera", queryset=Carrera.objects.none(), required=False, widget=forms.Select())
    inscripciones = forms.ModelChoiceField(label=u"Alumnos", queryset=DetallePreInscripcionPracticasPP.objects.none(), required=False, empty_label=None, widget=forms.Select(attrs={'multiple': 'multiple'}))
    itinerariomalla = forms.ModelChoiceField(label=u"Itinerarios", queryset=ItinerariosMalla.objects.none(), required=False, empty_label=None, widget=forms.Select(attrs={'multiple': 'multiple'}))
    asignacionempresapractica = forms.ModelChoiceField(label=u"Asignación de empresa", queryset=AsignacionEmpresaPractica.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '12'}))

    def iniciarform(self, qscarreras):
        self.fields['carrera'].queryset = Carrera.objects.filter(status=True, id__in=qscarreras).order_by('nombre')

    def init(self, carr, iti, insc):
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=carr)
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(pk__in=iti)
        self.fields['inscripciones'].queryset = DetallePreInscripcionPracticasPP.objects.filter(pk__in=insc)
        self.fields['carrera'].initial = carr
        self.fields['itinerariomalla'].initial = iti
        self.fields['inscripciones'].initial = insc

class ConfiguracionInscripcionPracticasPPForm(FormModeloBase):
    carrera = forms.ModelMultipleChoiceField(label=u"Carrera", queryset=Carrera.objects.none(), required=False, widget=forms.SelectMultiple(attrs={'multiple': 'multiple'}))
    itinerariomalla = forms.ModelMultipleChoiceField(label=u"Itinerarios", queryset=ItinerariosMalla.objects.none(), required=False, widget=forms.SelectMultiple(attrs={'multiple': 'multiple'}))
    fechainicio = forms.DateField(label=u"Fecha inicio práctica", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    fechafin = forms.DateField(label=u"Fecha fin práctica", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    asignacionempresapractica = forms.ModelChoiceField(label=u"Asignación de empresa", queryset=AsignacionEmpresaPractica.objects.none(), required=True, widget=forms.Select())
    # otraempresaempleadora = forms.CharField(label=u"Otra Empresa Empleadora", max_length=600, required=False, widget=forms.TextInput(attrs={'col': '6'}))
    lugarpractica = forms.ModelChoiceField(label=u"Lugar de la práctica", queryset=Canton.objects.filter(status=True, provincia__pais_id=1), required=True, widget=forms.Select(attrs={'col': '6'}))
    tipoinstitucion = forms.ChoiceField(choices=TIPO_INSTITUCION, required=False, label=u'Tipo Institución', widget=forms.Select(attrs={'col': '6'}))
    numerohora = forms.IntegerField(label=u'Número Hora', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'col': '3'}))
    cupo = forms.IntegerField(label=u'Cupos', initial=1, required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'decimal': '0', 'col': '3'}))
    dia = forms.ChoiceField(choices=DIAS_CHOICES, required=False, label=u'Día académico', widget=forms.Select(attrs={'col': '6'}))
    tutorunemi = forms.ModelChoiceField(label=u"Tutor UNEMI", queryset=Profesor.objects.none(), required=False, widget=forms.Select(attrs={'col': '6'}))
    supervisor = forms.IntegerField(initial=0, required=False, label=u'Supervisor UNEMI', widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%', 'col': '6'}))
    responsable = forms.ModelChoiceField(label=u"Responsable centro salud", queryset=ResponsableCentroSalud.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '6'}))
    periodoevidencia = forms.ModelChoiceField(label=u"Periodo de evidencias", queryset=CabPeriodoEvidenciaPPP.objects.none(), required=True, widget=forms.Select(attrs={'col': '6'}))
    convenio = forms.IntegerField(initial=0, required=False, label=u'Convenio de la empresa', widget=forms.TextInput(attrs={'select2search': 'true', 'formwidth': '100%'}))
    fechainiciooferta = forms.DateField(label=u"Fecha inicio oferta", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    fechafinoferta = forms.DateField(label=u"Fecha fin oferta", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)

    def init(self, list_carr, iti, tutor, asigemp, perevi):
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(status=True, malla__carrera_id__in=list_carr, malla__vigente=True)
        self.fields['tutorunemi'].queryset = Profesor.objects.filter(pk=tutor)
        self.fields['carrera'].queryset = Carrera.objects.filter(pk__in=list_carr)
        self.fields['asignacionempresapractica'].queryset = AsignacionEmpresaPractica.objects.filter(status=True)
        self.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(status=True, periodoevidenciapracticaprofesionales__carrera__in=list_carr).distinct('id').order_by('id')
        self.fields['responsable'].queryset = ResponsableCentroSalud.objects.filter(status=True, asignacionempresapractica__id=asigemp)

        self.fields['carrera'].initial = list_carr
        self.fields['itinerariomalla'].initial = iti
        self.fields['tutorunemi'].initial = tutor
        self.fields['asignacionempresapractica'].initial = asigemp
        self.fields['periodoevidencia'].initial = perevi

    def bloqueo(self):
        self.fields['carrera'].required = False
        # self.fields['itinerariomalla'].required = False
        self.fields['carrera'].widget.attrs = {'disabled': 'disabled'}
        # self.fields['itinerariomalla'].widget.attrs = {'disabled': 'disabled'}

    def editar(self, configuracion):
        self.fields['fechainicio'].initial = (configuracion.fechainicio).date()
        self.fields['fechafin'].initial = (configuracion.fechafin).date()
        self.fields['numerohora'].initial = configuracion.numerohora
        self.fields['cupo'].initial = configuracion.cupo
        # self.fields['otraempresaempleadora'].initial = configuracion.otraempresaempleadora
        self.fields['lugarpractica'].initial = configuracion.lugarpractica
        self.fields['responsable'].initial = configuracion.responsable
        self.fields['tipoinstitucion'].initial = configuracion.tipoinstitucion
        self.fields['dia'].initial = configuracion.dia
        self.fields['fechainiciooferta'].initial = (configuracion.fechainiciooferta).date()
        self.fields['fechafinoferta'].initial = (configuracion.fechafinoferta).date()
        if configuracion.itinerariomalla.all():
            self.bloqueo()

    def iniciarform(self, qscarreras):
        self.fields['carrera'].queryset = Carrera.objects.filter(status=True, id__in=qscarreras).order_by('nombre')

    def iniciarfechas(self, extconfi):
        self.fields['fechainicio'].initial = (extconfi.finiciopractica).date() if extconfi.finiciopractica else datetime.now().date()
        self.fields['fechafin'].initial = (extconfi.ffinpractica).date() if extconfi.ffinpractica else datetime.now().date()
        self.fields['fechainiciooferta'].initial = (extconfi.finicioconvocatoria).date() if extconfi.finicioconvocatoria else datetime.now().date()
        self.fields['fechafinoferta'].initial = (extconfi.ffinconvocatoria).date() if extconfi.ffinconvocatoria else datetime.now().date()

class FechasConvocatoriaPPPForm(FormModeloBase):
    finiciopractica = forms.DateField(label=u"Fecha inicio", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6','separator': 'true', 'separatortitle': 'FECHAS DE INICIO Y FIN DE LAS PRÁCTICAS PRE PROFESIONALES'}), required=True)
    ffinpractica = forms.DateField(label=u"Fecha fin", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    finicioconvocatoria = forms.DateField(label=u"Fecha inicio", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6', 'separator': 'true', 'separatortitle': 'FECHAS DE INICIO Y FIN DE OFERTAS'}), required=True)
    ffinconvocatoria = forms.DateField(label=u"Fecha fin", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    periodoevidencia = forms.ModelChoiceField(label=u"Periodo de evidencias", queryset=CabPeriodoEvidenciaPPP.objects.none(), required=False, widget=forms.Select(attrs={'col': '12', 'separator': 'true', 'separatortitle': 'PERIODO DE SUBIDA DE EVIDENCIAS'}))

    def init(self, perevi):
        self.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(status=True, pk=perevi)
        self.fields['periodoevidencia'].initial = perevi

    def iniciar(self, extconfi):
        self.fields['finiciopractica'].initial = (extconfi.finiciopractica).date() if extconfi.finiciopractica else datetime.now().date()
        self.fields['ffinpractica'].initial = (extconfi.ffinpractica).date() if extconfi.ffinpractica else datetime.now().date()
        self.fields['finicioconvocatoria'].initial = (extconfi.finicioconvocatoria).date() if extconfi.finicioconvocatoria else datetime.now().date()
        self.fields['ffinconvocatoria'].initial = (extconfi.ffinconvocatoria).date() if extconfi.ffinconvocatoria else datetime.now().date()
        self.fields['periodoevidencia'].queryset = CabPeriodoEvidenciaPPP.objects.filter(status=True, periodoevidenciapracticaprofesionales__carrera__in=extconfi.preinscripcion.carrera.all())
        self.fields['periodoevidencia'].initial = extconfi.periodoevidencia

class ResponsableCentroSaludForm(FormModeloBase):
    tipoidentificacion = forms.ChoiceField(label=u"Documento", required=True, choices=[TIPOS_IDENTIFICACION[0], TIPOS_IDENTIFICACION[2]], widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    identificacion = forms.CharField(label=u"Número de identificación", max_length=10, required=True, widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Digite su número de identificación'}))
    nombre = forms.CharField(max_length=200, label=u'Nombres', required=True, widget=forms.TextInput(attrs={'col': '12', 'placeholder': 'Nombres'}))
    apellido1 = forms.CharField(max_length=200, label=u'Primer apellido', required=True, widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Primer apellido'}))
    apellido2 = forms.CharField(max_length=200, label=u'Segundo apellido', required=True, widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Segundo apellido'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", queryset=Sexo.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    nacimiento = forms.DateField(label=u"Fecha de nacimiento", initial=None, required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    telefono = forms.CharField(label=u'Celular', max_length=15, required=False, widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Digite el número de celular'}))
    telefono_conv = forms.CharField(label=u'Teléfono fijo', max_length=15, required=False, widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Digite el número de teléfono'}))
    email = forms.EmailField(label=u'Correo electrónico', max_length=50, required=True, widget=forms.EmailInput(attrs={'col': '12', 'placeholder': 'Digite un correo electrónico'}))
    asignacionempresapractica = forms.ModelChoiceField(label=u"Asignación de empresa", queryset=AsignacionEmpresaPractica.objects.filter(status=True).order_by('nombre'), required=True, widget=forms.Select())
    # otraempresaempleadora = forms.CharField(label=u"Otra Empresa Empleadora", max_length=600, required=False, widget=forms.TextInput(attrs={'col': '12'}))
    cargo = forms.CharField(label=u"Cargo", max_length=600, required=False, widget=forms.TextInput(attrs={'col': '6'}))
    telefono_ofi = forms.CharField(label=u'Teléfono Oficina', max_length=15, required=False, widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Digite el número de teléfono'}))
    generaperfil = forms.BooleanField(label=u'¿Crear Perfil Externo? ', initial=False, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'class': 'js-switch', 'help_text_switchery': True}))

    def clean(self):
        cleaned_data=super().clean()
        cedula=cleaned_data.get('identificacion').upper().strip()
        tipoidentificacion=cleaned_data.get('tipoidentificacion')
        nacimiento = cleaned_data.get('nacimiento')
        if tipoidentificacion and int(tipoidentificacion) == 1:
            result = validarcedula(cedula)
            if result != 'Ok':
                self.add_error('identificacion', result)
        elif cedula[:2] and not cedula[:2] == u'VS':
            self.add_error('identificacion', 'Pasaporte mal ingresado, no olvide colocar VS al inicio.')
        if nacimiento and (datetime.now().year - nacimiento.year) < 18:
            self.add_error('nacimiento', 'Su año de nacimiento indica que es menor de edad.')
        return cleaned_data

    def habilita(self, estado):
        self.fields['nombre'].required = estado
        self.fields['apellido1'].required = estado
        self.fields['apellido2'].required = estado
        self.fields['sexo'].required = estado
        self.fields['nacimiento'].required = estado

    def habilita2(self):
        self.fields['tipoidentificacion'].required = False
        self.fields['tipoidentificacion'].widget.attrs = {'disabled': 'disabled', 'col': '6'}
        self.fields['identificacion'].required = False
        self.fields['identificacion'].widget.attrs = {'disabled': 'disabled', 'col': '6'}

    def editar(self, responsable):
        self.fields['tipoidentificacion'].initial = 1 if responsable.persona.cedula else 3
        self.fields['identificacion'].initial = responsable.persona.cedula if responsable.persona.cedula else responsable.persona.pasaporte
        self.fields['generaperfil'].initial = True if not responsable.persona.tiene_usuario_externo() else False
        self.habilita2()

class ActualizaConfiguracionInscripcionPracticasPPForm(FormModeloBase):
    estado = forms.ChoiceField(choices=ESTADO_CONFIGURACION_PRACTICAS, required=False, label=u'Estado', widget=forms.Select(attrs={'col': '12'}))
    # fechainiciooferta = forms.DateField(label=u"Fecha inicio oferta", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    # fechafinoferta = forms.DateField(label=u"Fecha fin oferta", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    #
    # def iniciar(self, configuracion):
    #     self.fields['fechainiciooferta'].initial = (configuracion.fechainiciooferta).date()
    #     self.fields['fechafinoferta'].initial = (configuracion.fechafinoferta).date()

class BitacoraActividadPppForm(FormModeloBase):
    titulo = forms.CharField(max_length=500, label=u"Título", widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}),required=True)
    fecha = forms.DateField(label=u"Fecha", initial=datetime.now().date(), required=True, input_formats=['%Y-%m-%d'], widget=DateTimeInput(format='%Y-%m-%d',attrs={'class': 'form-control', 'col': '6', 'type':'date'}))
    hora = forms.CharField(label=u"Hora Inicio", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3', 'type':'time'}))
    horafin = forms.CharField(label=u"Hora Fin", required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'col': '3', 'type': 'time', 'valid':False}))
    rol = forms.ChoiceField(choices=ROL_ACTIVIDAD, required=False, label=u'Rol Actividad', widget=forms.Select(attrs={'col': '6'}))
    tipo = forms.ChoiceField(choices=TIPO_ACTIVIDAD, required=False, label=u'Tipo Actividad', widget=forms.Select(attrs={'col': '6'}))
    descripcion = forms.CharField(label=u'Descripción', max_length=10000, widget=forms.Textarea({'class': 'form-control', 'row': '2', 'col': '12'}),required=True)
    # resultado = forms.CharField(label=u'Producto/Resultado', max_length=10000, widget=forms.Textarea({'class': 'form-control', 'row': '2', 'col': '6'}),required=True)
    link = forms.CharField(max_length=1000, label=u"Link", widget=forms.TextInput(attrs={'class': 'form-control', 'col': '6'}), required=False)
    archivo = ExtFileField(label=u'Archivo', help_text=u'Tamaño maximo permitido 12Mb, en formato pdf, doc, docx, xls, xlsx, jpg, jpeg, png', ext_whitelist=(".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"), required=False, max_upload_size=12582912, widget=forms.FileInput(attrs={'class': 'form-control', 'col': '6'}))

    def iniciar(self, carrera, bitacora=None):
        if carrera.id in [112]:
            self.fields['rol'].required = False
            self.fields['rol'].widget.attrs = {'disabled': 'disabled'}
            self.fields['tipo'].required = False
            self.fields['tipo'].widget.attrs = {'disabled': 'disabled'}
        elif carrera.id in [111]:
            self.fields['rol'].required = False
            self.fields['rol'].widget.attrs = {'disabled': 'disabled'}
            self.fields['tipo'].initial = bitacora.tipo if bitacora else 0
        else:
            self.fields['rol'].initial = bitacora.rol if bitacora else 0
            self.fields['tipo'].initial = bitacora.tipo if bitacora else 0

class validarDocumentoPPPForm(FormModeloBase):
    estado = forms.ChoiceField(label=u'Estado', choices=ESTADO_APROBACION, required=True, widget=forms.Select(attrs={'col': '6'}))
    observacion = forms.CharField(label=u'Observación', max_length=10000, required=False, widget=forms.Textarea({'class': 'form-control', 'rows': '2', 'col': '12'}))

    def bloqueo(self):
        self.fields['estado'].required = False
        self.fields['observacion'].required = False
        self.fields['estado'].widget.attrs = {'disabled': 'disabled'}
        self.fields['observacion'].widget.attrs = {'disabled': 'disabled'}

class FormatoPppForm(FormModeloBase):
    nombre = forms.CharField(max_length=500, label=u"Nombre", widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}),required=True)
    htmlnombre = forms.CharField(max_length=500, label=u"Archivo html", widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}),required=True)
    carrera = forms.ModelChoiceField(label=u'Carrera', queryset=Carrera.objects.filter(status=True, coordinacion__id=1), required=True)
    itinerariomalla = forms.ModelMultipleChoiceField(label=u"Itinerarios", queryset=ItinerariosMalla.objects.none(), required=False, widget=forms.SelectMultiple(attrs={'multiple': 'multiple'}))
    activo = forms.BooleanField(label=u'¿Activo? ', initial=True, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'class': 'js-switch', 'help_text_switchery': True}))

    def iniciar(self, carr, itis):
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(status=True, malla__vigente=True, malla__carrera_id=carr) #malla__vigente=True,
        self.fields['itinerariomalla'].initial = itis

    def editar(self, formato):
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(status=True,  malla__carrera=formato.carrera)
        self.fields['itinerariomalla'].initial = formato.itinerariomalla.values_list('id', flat=True).all()
        # self.fields['itinerariomalla'].initial = ItinerariosMalla.objects.filter(pk__in=formato.itinerariomalla.values_list('id', flat=True).all())

class DiscapacidadSaludForm(FormModeloBase):
    tienediscapacidad = forms.BooleanField(label=u'Tiene Discapacidad?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de Discapacidad", queryset=Discapacidad.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    subtipodiscapacidad = forms.ModelMultipleChoiceField(label=u"Sub Tipo de Discapacidad", queryset=SubTipoDiscapacidad.objects.filter(status=True), required=False, widget=forms.SelectMultiple(attrs={'multiple': 'multiple', 'class':'select2'}))
    grado = forms.ChoiceField(label=u"Grado de Discapacidad", choices=GRADO, required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    institucionvalida = forms.ModelChoiceField(label=u"Institución Valida", queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True), required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'% de Discapacidad', required=False, widget=forms.TextInput(attrs={'col':'6'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet Discapacitado', max_length=50, required=False, widget=forms.TextInput(attrs={'col':'6'}))
    tienediscapacidadmultiple = forms.BooleanField(label=u'Tiene Discapacidad multiple?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    tipodiscapacidadmultiple = forms.ModelMultipleChoiceField(label=u"Tipo de Discapacidad Multiple", queryset=Discapacidad.objects.filter(status=True), required=False, widget=forms.SelectMultiple(attrs={'multiple': 'multiple','col':'6', 'class':'select2'}))
    archivovaloracion = ExtFileField(label=u'Documento de valoración médica', required=False, help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'pdf'}), max_upload_size=4194304)
    archivocarnet = ExtFileField(label=u'Carnet de Discapacidad', required=False, widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'pdf'}), help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304)

    def ocultarcampos(self):
        del self.fields['tienediscapacidad']

    def bloquearcampos(self):
        deshabilitar_campo(self, 'tipodiscapacidad')

class PersonaEnfermedadSaludForm(FormModeloBase):
    enfermedad = forms.ModelChoiceField(queryset=Enfermedad.objects.filter(status=True), required=True, label=u'Enfermedad', widget=forms.Select(attrs={'class': 'select2'}))
    archivoenfermedad = ExtFileField(label=u'Archivo Médico', required=True, help_text=u'Tamaño máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=2194304, widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'}))

class PersonaDetalleMaternidadSaludForm(FormModeloBase):
    fechainicioembarazo = forms.DateField(label=u"Inicio de gestación", initial=None, required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    semanasembarazo = forms.IntegerField(initial=0, label=u'Semanas de Embarazo', required=False, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'decimal': '0', 'col': '6'}))
    gestacion = forms.BooleanField(label=u'¿Se encuentra en estado de gestación?', required=False, widget=forms.CheckboxInput(attrs={'col': '6','data-switchery':True}))
    fechaparto = forms.DateField(label=u"Fecha de parto", required=False, widget=DateTimeInput(format='%Y-%m-%d', attrs={'col': '6'}))
    lactancia = forms.BooleanField(label=u'Se encuentra en periodo de lactancia?', required=False, widget=forms.CheckboxInput(attrs={'col': '6','data-switchery':True}))
    archivo = ExtFileField(label=u'Certificado (MSP)', required=False, widget=forms.FileInput(attrs={'col': '6', 'data-allowed-file-extensions': 'pdf'}), help_text=u'Tamaño Maximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304)

class FamiliarSaludForm(FormModeloBase):
    # DATOS BÁSICOS
    tipoidentificacion = forms.ChoiceField(label=u"Documento", required=True, choices=[TIPOS_IDENTIFICACION[0], TIPOS_IDENTIFICACION[2]], widget=forms.Select(attrs={'col': '2', 'class':'select2'}))
    identificacion = forms.CharField(label=u"Número de identificación", max_length=10, required=True, widget=forms.TextInput(attrs={'col': '4', 'placeholder':'Digite su número de identificación'}))
    parentesco = forms.ModelChoiceField(label=u"Parentesco", queryset=ParentescoPersona.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '4', 'class':'select2'}))
    sexo = forms.ModelChoiceField(label=u"Sexo", queryset=Sexo.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '2', 'class': 'select2'}))
    nombre = forms.CharField(max_length=200, label=u'Nombres', required=True,widget=forms.TextInput(attrs={'col':'6','placeholder':'Describa los nombres del familiar'}))
    apellido1 = forms.CharField(max_length=200, label=u'Primer apellido', required=True, widget=forms.TextInput(attrs={'col':'3', 'placeholder':'Describa el primer apellido'}))
    apellido2 = forms.CharField(max_length=200, label=u'Segundo apellido', required=True, widget=forms.TextInput(attrs={'col':'3', 'placeholder':'Describa el segundo apellido'}))
    nacimiento = forms.DateField(label=u"Fecha nacimiento", initial=None, required=True, widget=DateTimeInput(format='%d-%m-%Y', attrs={'col': '6'}))
    telefono = forms.CharField(label=u'Celular', max_length=15, required=False, widget=forms.TextInput(attrs={'col': '3','placeholder':'Digite el número de celular'}))
    telefono_conv = forms.CharField(label=u'Teléfono fijo', max_length=15, required=False, widget=forms.TextInput(attrs={'col': '3','placeholder':'Digite el número de teléfono'}))
    fallecido = forms.BooleanField(label=u'¿Falleció?', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    convive = forms.BooleanField(label=u'¿Convive con usted?', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    esservidorpublico = forms.BooleanField(label=u'¿Es servidor público?', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    bajocustodia = forms.BooleanField(label=u'¿Esta bajo su custodia?', required=False, widget=CheckboxInput(attrs={'col':'3','data-switchery':True}))
    centrocuidado = forms.ChoiceField(label=u"Centro de cuidado", choices=CENTRO_CUIDADO, required=False, widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    centrocuidadodesc = forms.CharField(label=u"Descripción del centro de cuidado", required=False, widget=forms.TextInput(attrs={'col': '6', 'placeholder': 'Describa el centro de cuidado que tiene para su familiar.'}))
    cedulaidentidad = ExtFileField(label=u'Subir documento de identidad', required=False, help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '6', 'accept': '.pdf'}), max_upload_size=2194304)
    cartaconsentimiento = ExtFileField(label=u'Carta de consentimiento', required=False, help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '6', 'doctitle': 'Formato de carta', 'accept': '.pdf', 'docurl':'https://sga.unemi.edu.ec/media/documentos/2023/07/12/documentogeneral_2023712114148.docx'}), max_upload_size=2194304)
    archivocustodia = ExtFileField(label=u'Archivo de respaldo de custodia', required=False, help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '6','accept': '.pdf'}), max_upload_size=2194304)

    # DATOS LABORALES
    niveltitulacion = forms.ModelChoiceField(label=u"Nivel titulación", queryset=NivelTitulacion.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col':'6','class':'select2'}))
    tipoinstitucionlaboral = forms.ChoiceField(label=u"Tipo de institución laboral", choices=TIPO_INSTITUCION_LABORAL, required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2'}))
    trabajo = forms.CharField(label=u'Lugar de trabajo', max_length=200, required=False, widget=forms.TextInput(attrs={'col':'6','placeholder':'Describa el lugar de trabajao'}))
    formatrabajo = forms.ModelChoiceField(label=u"Tipo trabajo", queryset=FormaTrabajo.objects.all(), required=False, widget=forms.Select(attrs={'col':'3', 'class':'select2'}))
    ingresomensual = forms.DecimalField(label='Ingreso mensual', initial=00,required=False, widget=forms.TextInput(attrs={'col':'3','placeholder':'00.00'}))
    sustentohogar = forms.BooleanField(label=u'¿Es sustento del hogar?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    tienenegocio = forms.BooleanField(label=u'¿Tiene negocio propio?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    negocio = forms.CharField(label=u'Descripción de negocio', max_length=100, required=False, widget=forms.TextInput(attrs={'col':'12','placeholder':'Describa el negocio que tenga'}))

    #DISCAPACIDAD
    tienediscapacidad = forms.BooleanField(label=u'¿Tiene discapacidad?', required=False, widget=CheckboxInput(attrs={'col':'4','data-switchery':True}))
    essustituto = forms.BooleanField(label=u'¿Es sustituto?', required=False, widget=CheckboxInput(attrs={'data-switchery':True,'col':'4'}))
    autorizadoministerio = forms.BooleanField(label=u'¿Es autorizado por el ministerio?', required=False, widget=CheckboxInput(attrs={'data-switchery':True,'col':'4'}))
    tipodiscapacidad = forms.ModelChoiceField(label=u"Tipo de discapacidad", queryset=Discapacidad.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col':'6','class':'select2'}))
    porcientodiscapacidad = forms.FloatField(initial=0, label=u'Porcentaje de discapacidad', required=False, widget=forms.TextInput(attrs={'col': '6'}))
    carnetdiscapacidad = forms.CharField(label=u'N° Carnet discapacitado', max_length=50, required=False, widget=forms.TextInput(attrs={'col':'6','placeholder':'Digite el número del carnet de discapacida'}))
    institucionvalida = forms.ModelChoiceField(label=u"Institución que válida", queryset=InstitucionBeca.objects.filter(tiporegistro=2, status=True), required=False, widget=forms.Select(attrs={'col':'6', 'class':'select2', 'placeholder':'Nombre de la institución que válida.'}))
    ceduladiscapacidad = ExtFileField(label=u'Subir carnet de discapacidad', required=False, help_text=u'Tamaño Maximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=2194304, widget=forms.FileInput(attrs={'col': '6','accept': '.pdf'}))
    archivoautorizado = ExtFileField(label=u'Archivo sustituto(MIES)', required=False, help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '6','accept': '.pdf'}), max_upload_size=2194304)

    def edit(self):
        self.fields['cedulaidentidad'].required = False

    def clean(self):
        cleaned_data=super().clean()
        cedula=cleaned_data.get('identificacion')
        tipoidentificacion=int(cleaned_data.get('tipoidentificacion'))
        if tipoidentificacion == 1:
            result=validarcedula(cedula)
            if result!='Ok':
                self.add_error('identificacion',result)
        return cleaned_data

class FamiliarEnfermedadSaludForm(FormModeloBase):
    essustituto = forms.BooleanField(label=u'¿Es sustituto?', required=False, widget=CheckboxInput(attrs={'data-switchery': True, 'col': '12'}))
    archivoautorizado = ExtFileField(label=u'Archivo sustituto(MIES)', required=False, help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'}), max_upload_size=2194304)
    enfermedad = forms.ModelChoiceField(queryset=Enfermedad.objects.filter(status=True), required=True, label=u'Enfermedad', widget=forms.Select(attrs={'class': 'select2'}))
    archivoenfermedad = ExtFileField(label=u'Archivo Médico', required=False, help_text=u'Tamaño máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=2194304, widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'}))

class FamiliarNinioSaludForm(FormModeloBase):
    bajocustodia = forms.BooleanField(label=u'¿Esta bajo su custodia?', required=False, widget=CheckboxInput(attrs={'col':'6','data-switchery':True}))
    parentesco = forms.ModelChoiceField(label=u"Parentesco", queryset=ParentescoPersona.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    cedulaidentidad = ExtFileField(label=u'Subir documento de identidad o partida de nacimiento', required=False, help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'}), max_upload_size=2194304)
    archivocustodia = ExtFileField(label=u'Archivo de respaldo de custodia', required=False, help_text=u'Tamaño Máximo permitido 2Mb, en formato pdf', ext_whitelist=(".pdf",), widget=forms.FileInput(attrs={'col': '12', 'accept': '.pdf'}), max_upload_size=2194304)

    # def edit(self, familiar):
    #     if familiar.cedulaidentidad:
    #         self.fields['cedulaidentidad'].required = False
    #     if familiar.archivocustodia:
    #         self.fields['archivocustodia'].required = False

class RequisitoPPPSaludForm(FormModeloBase):
    archivo = ExtFileField(label=u'Requisito', required=False, widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'pdf'}), help_text=u'Tamaño máximo permitido 4Mb, en formato pdf', ext_whitelist=(".pdf",), max_upload_size=4194304)
    observacion = forms.CharField(label=u'Observación', max_length=10000, required=False, widget=forms.Textarea({'class': 'form-control', 'rows': '2', 'col': '12'}))

class ItinerarioAsignaturaSaludForm(FormModeloBase):
    carrera = forms.ModelChoiceField(Carrera.objects.filter(status=True, coordinacion__id=1), required=False, label=u'Carrera', widget=forms.Select(attrs={'col': '12'}))
    itinerariomalla = forms.ModelChoiceField(ItinerariosMalla.objects.none(), required=False, label=u"Itinerario", widget=forms.Select(attrs={'col': '12'}))
    todasasignaturas = forms.BooleanField(label=u'¿Todas?', required=False, widget=CheckboxInput(attrs={'data-switchery': True, 'col': '1'}))
    asignaturamalla = forms.ModelChoiceField(AsignaturaMalla.objects.none(), required=True, label=u'Asignatura', widget=forms.Select(attrs={'col': '11'}))

    def iniciar(self, itis, asig):
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(status=True, pk=itis)
        self.fields['itinerariomalla'].initial = itis
        self.fields['asignaturamalla'].queryset = AsignaturaMalla.objects.filter(status=True, pk=asig)
        self.fields['asignaturamalla'].initial = asig

    def iniciar_editar(self, registro):
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(status=True,  malla__carrera=registro.itinerariomalla.malla.carrera)
        self.fields['itinerariomalla'].initial = registro.itinerariomalla
        self.fields['asignaturamalla'].queryset = AsignaturaMalla.objects.filter(status=True, pk=registro.asignaturamalla.id)
        self.fields['asignaturamalla'].initial = registro.asignaturamalla.id

class UbicacionEmpresaPracticaForm(FormModeloBase):
    asignacionempresapractica = forms.ModelChoiceField(label=u"Asignación de empresa", queryset=AsignacionEmpresaPractica.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12'}))
    latitud = forms.FloatField(initial=0, label=u'Latitud', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right'}))
    longitud = forms.FloatField(initial=0, label=u'Longitud', required=True, widget=forms.TextInput(attrs={'col': '6', 'class': 'imp-numbermed-right'}))

class TurnoPracticaForm(FormModeloBase):
    turno = forms.IntegerField(label=u'Turno', initial=0, required=True, widget=forms.TextInput(attrs={'class': 'imp-numbersmall', 'onKeyPress': "return soloNumeros(event)", 'decimal': '0', 'col':'3'}))
    comienza = forms.TimeField(label=u"Comienza", required=True, initial=str(datetime.now().time().strftime("%H:%M")), widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'col':'3'}))
    termina = forms.TimeField(label=u"Termina", required=True, initial=str(datetime.now().time().strftime("%H:%M")), widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora', 'col':'3'}))
    activo = forms.BooleanField(initial=False, required=False, label=u'¿Activo?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'id':'id_activo', 'name':'activo', 'col':'3', 'data-switchery': 'true'}))

class PlanificacionMensualForm(FormModeloBase):
    carrera = forms.ModelChoiceField(Carrera.objects.none(), required=True, label=u'Carrera', widget=forms.Select(attrs={'col': '12'}))
    itinerariomalla = forms.ModelChoiceField(ItinerariosMalla.objects.none(), required=False, label=u"Itinerario", widget=forms.Select(attrs={'col': '12'}))
    mes = forms.ChoiceField(label=u'Mes', choices=MESES_CHOICES, initial=datetime.now().date().month, required=True, widget=forms.Select(attrs={'col': '6'}))

    def inicio(self, carreras):
        self.fields['carrera'].queryset = Carrera.objects.filter(pk__in=carreras)

    def iniciar(self, carr, itis):
        self.fields['carrera'].queryset = Carrera.objects.filter(pk=carr)
        self.fields['carrera'].initial = carr
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(status=True, malla__vigente=True, malla__carrera_id=carr)
        self.fields['itinerariomalla'].initial = itis

    def editar(self, carreras, registro):
        self.fields['carrera'].queryset = Carrera.objects.filter(pk__in=carreras)
        self.fields['carrera'].initial = registro.itinerariomalla.malla.carrera
        self.fields['itinerariomalla'].queryset = ItinerariosMalla.objects.filter(status=True, malla__carrera=registro.itinerariomalla.malla.carrera)
        self.fields['itinerariomalla'].initial = registro.itinerariomalla

class InformePlanificacionMensualForm(FormModeloBase):
    archivo = forms.FileField(label=u'Informe planificación', required=False,
                             help_text=u'Tamaño Máximo permitido 4Mb, en formato  pdf',
                             widget=forms.FileInput(attrs={'class': 'dropify', 'data-max-file-size': '4M',
                                                           'accept': '.pdf'}))

class DetallePlanificacionMensualForm(FormModeloBase):
    carrera = forms.ModelChoiceField(Carrera.objects.filter(status=True, coordinacion__id=1), required=True, label=u'Carrera', widget=forms.Select(attrs={'col': '12'}))
    itinerariomalla = forms.ModelChoiceField(ItinerariosMalla.objects.none(), required=False, label=u"Itinerario", widget=forms.Select(attrs={'col': '12'}))
    asignaturamalla = forms.ModelChoiceField(AsignaturaMalla.objects.none(), required=True, label=u'Asignatura', widget=forms.Select(attrs={'col': '11'}))
    fechainicio = forms.DateField(label=u"Fecha inicio", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    fechafin = forms.DateField(label=u"Fecha fin", widget=DateTimeInput(attrs={'class': 'selectorfecha', 'col': '6'}), required=True)
    tema = forms.ModelChoiceField(label=u'Tema', queryset=TemaUnidadResultadoProgramaAnalitico.objects.filter(status=True), required=False, widget=forms.Select(attrs={'col': '12'}))

class TurnoEstudianteForm(FormModeloBase):
    turno = forms.ModelChoiceField(label=u"Turno", queryset=TurnoPractica.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '12'}))
    nombre = forms.CharField(label=u'Nombre', max_length=300, required=False, widget=forms.TextInput({'col': '5'}))
    abreviatura = forms.CharField(label=u"Abreviatura", max_length=10, required=False, widget=forms.TextInput(attrs={'col': '3'}))
    horas = forms.IntegerField(label=u'Horas', required=False, widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumeros(event)", 'col': '2'}))
    color = forms.CharField(label=u'Color', required=False, widget=forms.TextInput(attrs={'type': 'color', 'col': '2'}))
    descripcion = forms.CharField(label=u'Descripcion', max_length=10000, required=False, widget=forms.Textarea({'class': 'form-control', 'rows': '2', 'col': '12'}))
    carrera = forms.ModelChoiceField(Carrera.objects.filter(status=True, coordinacion__id=1), required=True, label=u'Carrera', widget=forms.Select(attrs={'col': '12'}))
    activo = forms.BooleanField(initial=False, required=False, label=u'¿Activo?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'id':'id_activo', 'name':'activo', 'col':'3', 'data-switchery': 'true'}))

class RegisitroSupervisarPracticaForm(FormModeloBase):
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'class': 'form-control', 'rows': '3', 'col': '12'}))

class InformePlanificacionSemanalForm(FormModeloBase):
    # semana = forms.ModelMultipleChoiceField(label=u"Semana", required=False, widget=forms.SelectMultiple(attrs={'multiple': 'multiple'}))
    observacion = forms.CharField(label=u'Observación', required=False, widget=forms.Textarea({'class': 'form-control', 'rows': '3', 'col': '12'}))

class DetallePlanificacionMensual2Form(FormModeloBase):
    from django.forms import DateInput
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True, widget=DateInput(attrs={'class': 'form-control', 'col': '5', 'formwidth': '50%', 'type': 'date'}))
    fechafin = forms.DateField(label=u"Fecha fín", required=True, widget=DateInput(attrs={'class': 'form-control', 'col': '5', 'formwidth': '50%', 'type': 'date'}))
    numerosemana = forms.IntegerField(label=u'N semana', required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumeros(event)", 'col': '2'}))
    tema = forms.CharField(max_length=600, label=u"Tema", widget=forms.TextInput(attrs={'class': 'imp-100', 'col': '12'}), required=True)
    objetivo = forms.CharField(label=u'Objetivo del aprendizaje', required=True, widget=forms.Textarea({'class': 'form-control', 'rows': '2', 'col': '12'}))
    enfoque = forms.CharField(label=u'Enfoque metodológico', required=True, widget=forms.Textarea({'class': 'form-control', 'rows': '2', 'col': '12'}))
    evaluacion = forms.CharField(label=u'Evaluación del Aprendizaje', help_text='Mantener el formato del registro. separar por punto y coma(;)', required=True, widget=forms.Textarea({'class': 'form-control', 'rows': '2', 'col': '12'}))
    horas = forms.IntegerField(label=u'Horas', required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumeros(event)", 'col': '2'}))

class DetalleEvaluacionComponentePeriodoForm(FormModeloBase):
    actividad = forms.ModelChoiceField(label=u"Actividad", queryset=EvaluacionAprendizajeComponente.objects.none(), required=True, widget=forms.Select(attrs={'col': '12'}))
    cantidad = forms.IntegerField(label=u'Cantidad', required=True, widget=forms.TextInput(attrs={'class': 'imp-number', 'onKeyPress': "return soloNumeros(event)", 'col': '2'}))
    obligatorio = forms.BooleanField(initial=False, required=False, label=u'¿Obligatorio?', widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'id':'id_activo', 'name':'activo', 'col':'3', 'data-switchery': 'true'}))

    def iniciar(self, registro):
        self.fields['actividad'].queryset = EvaluacionAprendizajeComponente.objects.filter(status=True, componente=registro.componente)

    def editar(self, registro):
        self.fields['actividad'].queryset = EvaluacionAprendizajeComponente.objects.filter(status=True, componente=registro.evaluacioncomponenteperiodo.componente)
        self.fields['actividad'].initial = registro.actividad

class InscripcionEncuestaEstudianteSeguimientoSilaboForm(FormModeloBase):
    encuesta = forms.ModelChoiceField(label=u"Encuesta", queryset=EncuestaGrupoEstudiantes.objects.filter(
        id__in=EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list('encuestagrupoestudiantes_id',
                                                                           flat=True).filter(categoria=True, status = True),
        status=True), required=True,
                                      widget=forms.Select(attrs={'class': 'select ', 'col': '12'}))
    fechainicioencuesta = forms.DateField(label=u"Fecha inicio encuesta", initial=datetime.now().date(),
                           widget=DateTimeInput(format='%d-%m-%Y',
                                                attrs={'col': '6'}),
                           required=True)
    fechafinencuesta = forms.DateField(label=u"Fecha fin encuesta", initial=datetime.now().date(),
                           widget=DateTimeInput(format='%d-%m-%Y',
                                                attrs={'col': '6'}),
                           required=True)
    def deshabilitar_campo(form, campo):
        form.fields[campo].widget.attrs['readonly'] = True
        form.fields[campo].widget.attrs['disabled'] = True
        form.fields[campo].required = False


class CapEncuestaPeriodoForm(FormModeloBase):
    nombre = forms.CharField(label=u'Nombre', max_length=300, widget=forms.TextInput({'class': 'form-control', 'col': '12'}), required=True)
    # valoracion = forms.IntegerField(label=u'Cantidad de estrellas', widget=forms.NumberInput(attrs={'class': 'valor text-center ', 'col': '3', 'placeholder': '0', 'input_group': '<i class="fa fa-star"></i>', 'controlwidth': '50%'}))
    isVigente = forms.BooleanField(label=u'¿Esta vigente?', required=False, widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '12'}))

class CapPreguntaEncuestaPeriodoForm(FormModeloBase):
    descripcion = forms.CharField(label=u'Pregunta', widget=forms.Textarea({'rows': '1', 'class': 'form-control', 'col': '8'}), required=True)
    # valoracion = forms.IntegerField(label=u'Cantidad de estrellas', widget=forms.NumberInput(attrs={'class': 'valor text-center ', 'col': '3', 'placeholder': '0', 'input_group': '<i class="fa fa-star"></i>', 'controlwidth': '50%'}))
    isActivo = forms.BooleanField(label=u'¿Esta activa?', required=False, widget=forms.CheckboxInput(attrs={'data-switchery': True, 'col': '4'}))

class CriterioForm(FormModeloBase):
    nombre = forms.CharField(label=u"Nombre", widget=forms.Textarea({'rows': '1', 'class': 'form-control', 'col': '12', 'style': 'width:100%!important'}))


class SubactividadDocentePeriodoForm(FormModeloBase):
    from django.forms import DateInput
    from inno.models import SubactividadDocentePeriodo
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True, widget=DateInput(attrs={'class': 'form-control', 'col':'6', 'formwidth':'50%', 'type':'date'}))
    fechafin = forms.DateField(label=u"Fecha fín", required=True, widget=DateInput(attrs={'class': 'form-control', 'col':'6', 'formwidth':'50%', 'type':'date'}))
    criterio = forms.ModelChoiceField(label=u"Sub actividad", queryset=Criterio.objects.filter(tipo=2, status=True), required=True, widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))
    tipoevidencia = forms.ChoiceField(label=u"Tipo de evidencia", choices=SubactividadDocentePeriodo.TipoEvidencia.choices, required=True, widget=forms.Select(attrs={'col': '6', 'class':'select2'}))
    nombrehtml = forms.CharField(label=u'Plantilla HTML', max_length=500, widget=forms.TextInput({'placeholder': 'Escriba el nombre de la plantilla...', 'autocomplete': 'off', 'class': 'form-control', 'col': '6', 'list': 'template-options', 'disabled': True}), required=False)
    cargaevidencia = forms.BooleanField(label=u'¿El docente carga evidencia?', initial=True, required=False, widget=forms.CheckboxInput(attrs={'col': '6', 'class': 'js_switch'}))
    validacion = forms.BooleanField(label=u'¿Requiere validación?', required=False, widget=forms.CheckboxInput(attrs={'info':f'Si desactiva esta opción no se considerará esta subactividad en el calculo del porcentaje total', 'col': '6', 'class': 'js_switch'}))

    def __init__(self, *args, **kwargs):
        super(SubactividadDocentePeriodoForm, self).__init__(*args, **kwargs)
        self.template_choices = self.get_template_choices()

    def ocultar_plantilla(self):
        del self.fields['nombrehtml']

    def get_template_choices(self):
        try:
            template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'adm_criteriosactividadesdocente', 'subactividades')
            choices = [f"{folder}".replace('.html', '') for folder in os.listdir(template_dir) if os.path.isdir(template_dir)]
            return choices
        except Exception as ex:
            pass


class SubactividadDetalleDistributivoForm(FormModeloBase):
    from django.forms import DateInput
    from inno.models import SubactividadDocentePeriodo
    fechainicio = forms.DateField(label=u"Fecha inicio", required=True, widget=DateInput(attrs={'class': 'form-control', 'col':'6', 'formwidth':'50%', 'type':'date'}))
    fechafin = forms.DateField(label=u"Fecha fín", required=True, widget=DateInput(attrs={'class': 'form-control', 'col':'6', 'formwidth':'50%', 'type':'date'}))
    subactividaddocenteperiodo = forms.ModelChoiceField(label=u"Sub actividad", queryset=SubactividadDocentePeriodo.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '12', 'class': 'select2'}))

    def __init__(self, *args, **kwargs):
        super(SubactividadDetalleDistributivoForm, self).__init__(*args, **kwargs)

    def ocultar_campo(self, obj):
        if self.fields[obj]:
            del self.fields[obj]


class DisertacionExamenComplexivoForm(forms.Form):
    class Grupos(forms.ChoiceField):
        choices = [
            (0, 'NINGUNO'),
            (1, 'GRUPO 1'),
            (2, 'GRUPO 2'),
            (3, 'GRUPO 3'),
            (4, 'GRUPO 4'),
            (5, 'GRUPO 5'),
            (6, 'GRUPO 6'),
            (7, 'GRUPO 7'),
            (8, 'GRUPO 8'),
            (9, 'GRUPO 9'),
            (10, 'GRUPO 10'),
            (11, 'GRUPO 11'),
            (12, 'GRUPO 12'),
            (13, 'GRUPO 13'),
            (14, 'GRUPO 14')
        ]
        sede =[(0, 'NINGUNO'),
               (1, 'UNIVERSIDAD ESTATAL DE MILAGRO'),
               (11, 'VIRTUAL')]

        default = 0
    fecha = forms.DateField(label=u"Fecha", input_formats=['%d-%m-%Y'], required=False, widget=DateTimeInput(format='%d-%m-%Y', attrs={'class': 'selectorfecha', 'col': '4'}))
    horainicio = forms.TimeField(label=u"Hora inicio",initial=str(datetime.now().time()), input_formats=['%H:%M'],widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','col': '4'}))
    horafin = forms.TimeField(label=u"Hora fin", initial=str(datetime.now().time()),input_formats=['%H:%M'],widget=DateTimeInput(format='%H:%M', attrs={'class': 'selectorhora','col': '4'}))
    profesor1 = forms.ModelChoiceField(queryset=Persona.objects.none(), required=False, label=u'Profesor1', widget=forms.Select({'col': '6', }))
    profesor2 = forms.ModelChoiceField(queryset=Persona.objects.none(), required=False, label=u'Profesor2', widget=forms.Select({'col': '6', }))
    profesor3 = forms.ModelChoiceField(queryset=Persona.objects.none(), required=False, label=u'Profesor3', widget=forms.Select({'col': '6', }))
    profesor4 = forms.ModelChoiceField(queryset=Persona.objects.none(), required=False, label=u'Profesor4', widget=forms.Select({'col': '6', }))
    sede = forms.ChoiceField(label=u"Sede", choices=Grupos.sede,initial=Grupos.default, widget=forms.Select(attrs={'class': 'imp-50','col': '6'}))
    aula = forms.ModelChoiceField(label=u"Aula", queryset=LaboratorioVirtual.objects.all(), widget=forms.Select(attrs={'class': 'imp-100','col': '6'}))
    grupo = forms.ChoiceField(choices=Grupos.choices,initial=Grupos.default,label="Grupo",widget=forms.Select(attrs={'class': 'selectorgrupo', 'col': '6'}))


    def edit(self, profesores):
        for i, profesor in enumerate(profesores, start=1):
            if profesor:
                self.fields[f'profesor{i}'].queryset = Persona.objects.filter(id=profesor.id)
            else:
                self.fields[f'profesor{i}'].queryset = Persona.objects.none()

class ItinerarioAsignaturaMallaForm(FormModeloBase):
    asignaturamalla = forms.ModelChoiceField(AsignaturaMalla.objects.none(), required=True, label=u'Asignatura', widget=forms.Select(attrs={'col': '12'}))

    def iniciar(self, iti):
        registradas = ItinerarioAsignaturaMalla.objects.values_list('asignaturamalla_id').filter(status=True).distinct()
        self.fields['asignaturamalla'].queryset = AsignaturaMalla.objects.filter(status=True, malla=iti.malla).exclude(pk__in=registradas)

class FormatoPlanificacionRecursoForm(FormModeloBase):
    descripcion = forms.CharField(label=u"Descripción", widget=forms.Textarea(attrs={'rows': '2', 'col': '12', 'placeholder': 'Describa brevemente la funcionalidad de la opción...'}), required=True)
    archivo = ExtFileField(label=u'Archivo', required=False, help_text=u'Tamaño Maximo permitido 4Mb',
                          ext_whitelist=(".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx", ".pdf", ".ppt", ".pptx"), max_upload_size=8194304, widget=forms.FileInput(
                          attrs={'accept': 'image/jpeg, image/jpg, image/png', 'col': '12', 'data-allowed-file-extensions': 'png pdf jpg jpeg docx doc xls xlsx ppt pptx'}))
    modalidad = forms.ModelMultipleChoiceField(label=u"Modalidad", queryset=Modalidad.objects.filter(status=True), required=True, widget=forms.SelectMultiple(attrs={'multiple': 'multiple'}))
    activo = forms.BooleanField(label=u'¿Activo?', required=False, widget=forms.CheckboxInput(attrs={'class': 'js-switch', 'formwidth': '50%'}))

class EditFotoEstudiante(forms.Form):
    foto = ExtFileField(label=u'Foto', required=False, help_text=u'Tamaño Maximo permitido 8Mb, en formato .jpg o .jpeg', ext_whitelist=(".jpg", ".jpeg"), max_upload_size=8194304, widget=forms.FileInput(attrs={'col': '12', 'data-allowed-file-extensions': 'jpg jpeg','accept':'.jpg,.jpeg'}))

# class ContenidoMinimoForm(forms.Form):
#     contenido_minimo = forms.CharField(
#         label="Contenido mínimo:",
#         widget=forms.Textarea(attrs={
#             'rows': '1',
#             'style': 'resize: none; overflow: hidden;',
#             'placeholder': 'Ingrese el contenido mínimo',
#             'oninput': 'this.style.height = "auto"; this.style.height = (this.scrollHeight) + "px"; if (this.value.includes("\\n")) this.value = this.value.replace(/\\n/g, "");',
#             'onfocus': 'this.style.height = "auto"; this.style.height = (this.scrollHeight) + "px";',
#             'onkeydown': 'if(event.key === "Enter") {event.preventDefault();}',
#             'onkeypress': 'if(event.key === "Enter") {event.preventDefault();}',
#             'onkeyup': 'if(event.key === "Enter") {event.preventDefault();}'
#         }),
#         required=True
#     )
DETALLES_AUDITORIA=[
    (1,u'Acceso no autorizado al sistema'),
    (2,u'Notas alteradas test/examen'),
    (3,u'Notas alteradas actividades'),
    (4,u'Manipulación banco de preguntas'),
    (5,u'Eliminar/Habilitar intento de Test/Examen'),
    (6,u'Otros')
]

class AuditoriaInformaticaForm(forms.Form):
    detalle = forms.ChoiceField(label=u"Sede", choices=DETALLES_AUDITORIA, initial=1, widget=forms.Select(attrs={'class': 'imp-50','col': '6'}))
    observacion = forms.CharField(label=u'Observación', max_length=10000, widget=forms.Textarea({'row': '3'}), required=False)
    evidencia =  ExtFileField(label=u'Evidencia', required=False, ext_whitelist=(".pdf", ".jpg", ".jpeg", ".png", ".docx"), max_upload_size=15000000,
                                    widget=forms.FileInput(attrs={'formwidth': '100%', 'data-allowed-file-extensions': 'png pdf jpg jpeg docx'}))

class SedeProvinciasForm(forms.Form):
    sede_virtual=forms.ModelChoiceField(label=u"Sede de Examen Activa", queryset=SedeVirtual.objects.filter(status=True, activa=True), required=True, widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))
    provincias = forms.ModelChoiceField(label=u"Provincia", queryset=Provincia.objects.filter(status=True), required=True, widget=forms.Select(attrs={'col': '6', 'class': 'select2'}))