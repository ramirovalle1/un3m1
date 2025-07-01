# -*- coding: latin-1 -*-
from django.db import models, transaction
from django.db.models import Q, Sum
from django.db.models.aggregates import Max, Min
from dateutil.relativedelta import relativedelta
from django.forms import model_to_dict
from datetime import datetime, timedelta, date
import calendar
import time
from sga.funciones import ModeloBase, remover_caracteres_especiales_unicode, null_to_decimal, null_to_numeric, \
    variable_valor
from posgrado.models import Requisito
from sga.models import Inscripcion, Matricula, ProfesorMateria, MateriaAsignada, Materia, Silabo, \
    DetalleSilaboSemanalTema, DIAS_CHOICES, Periodo, TareaSilaboSemanal, ForoSilaboSemanal, TestSilaboSemanal, \
    DiapositivaSilaboSemanal, GuiaEstudianteSilaboSemanal, GuiaDocenteSilaboSemanal, MaterialAdicionalSilaboSemanal, \
    TareaPracticaSilaboSemanal, CompendioSilaboSemanal, VideoMagistralSilaboSemanal, HistorialaprobacionTarea, \
    HistorialaprobacionForo, HistorialaprobacionCompendio, HistorialaprobacionTest, HistorialaprobacionGuiaEstudiante, \
    HistorialaprobacionGuiaDocente, HistorialaprobacionDiapositiva, HistorialaprobacionMaterial, \
    HistorialaprobacionTareaPractica, HistorialaprobacionVideoMagistral, AsistenciaLeccion, \
    TIPO_SOLICITUDINCONVENIENTE, Modalidad, InstitucionEducacionSuperior, VALOR_SI_NO, AMBIENTE_APRENDIZAJE, UBICACION_APRENDIZAJE, Asignatura, \
    CategorizacionDocente, NivelMalla, ConvenioEmpresa, LaboratorioAcademia, TIPO_CALCULO_MATRICULA, Notificacion, \
    Carrera, CamposTitulosPostulacion, Titulo, Aula, DetalleModeloEvaluativo, SedeVirtual, HorarioExamenDetalleAlumno, \
    Sede, LaboratorioVirtual, RequisitoTitulacionMalla, AsignaturaMalla, Malla, Profesor, ProfesorDistributivoHoras, \
    Persona, Paralelo, MateriaTitulacion, MESES_CHOICES, RespuestaEvaluacionAcreditacion, ProcesoEvaluativoAcreditacion, EncuestaGrupoEstudiantes, PreguntaEncuestaGrupoEstudiantes, \
    CabPeriodoEvidenciaPPP, EmpresaEmpleadora, ItinerariosMalla, \
    PreInscripcionPracticasPP, TIPO_INSTITUCION, TIPO_PRACTICA_PP, Pais, Provincia, Canton, AcuerdoCompromiso, \
    PracticasPreprofesionalesInscripcion, EvidenciaPracticasProfesionales, PersonaDatosFamiliares, PersonaDetalleMaternidad, PerfilInscripcion, PersonaEnfermedad, \
    ActividadDetalleDistributivo, TemaUnidadResultadoProgramaAnalitico, DetalleSilaboSemanalSubtema, SilaboSemanal, SubTemaAdicionalesSilabo, EvaluacionComponentePeriodo, \
    EvaluacionAprendizajeComponente, EvaluacionAprendizajeSilaboSemanal, ResponsableCoordinacion, CoordinadorCarrera, Sesion, Turno, GPGuiaPracticaSemanal, LibrosOdiloSilaboSemanal, \
    DetallePreInscripcionPracticasPP, ProyectoVinculacionInscripcion, UnidadResultadoProgramaAnalitico
from investigacion.models import UserCriterioRevisor
from sagest.models import DistributivoPersona
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from settings import DEBUG
from django.core.cache import cache


class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_crear_configuracion_acta_calificacion_admision", "Puede Crear Acta de  Calificacion Admisión"),
            ("puede_editar_configuracion_acta_calificacion_admision", "Puede Modificar Acta de  Calificacion Admisión"),
            ("puede_editar_horarioexamen", "Puede Modificar Horario de Examenes"),
            ("puede_eliminar_horarioexamen", "Puede Eliminar Horario de Examenes"),
            ("puede_crear_horarioexamen", "Puede agregrar Horario de Examenes"),
            ("puede_clonar_horarioexamen", "Puede clonar Horario de Examenes"),
            ("puede_crear_sedevirtual", "Puede Crear Sede Virtual"),
            ("puede_editar_sedevirtual", "Puede Modificar Sede Virtual"),
            ("puede_eliminar_sedevirtual", "Puede Eliminar Sede Virtual"),
            ("puede_crear_aulavirtual", "Puede Crear Aula Virtual"),
            ("puede_editar_aulavirtual", "Puede Modificar Aula Virtual"),
            ("puede_eliminar_aulavirtual", "Puede Eliminar Aula Virtual"),
            ("puede_crear_planificacionexamenvirtual", "Puede Crear Planificación de Examenes Virtual"),
            ("puede_editar_planificacionexamenvirtual", "Puede Modificar Planificación de Examenes Virtual"),
            ("puede_eliminar_planificacionexamenvirtual", "Puede Eliminar Planificación de Examenes Virtual"),
            ("puede_resetearclaveusuario_examenvirtual", "Puede Resetear Clave de Usuario en Inicio de Sesión de Examenes Virtual"),
            ("puede_crear_materiaasignadaplanificacion_examenvirtual", "Puede Adicionar Alumno a la planificación de sede"),
            ("puede_editar_materiaasignadaplanificacion_examenvirtual", "Puede Editar Alumno a la planificación de sede"),
            ("puede_eliminar_materiaasignadaplanificacion_examenvirtual", "Puede Eliminar Alumno a la planificación de sede"),
            ("puede_ver_clave_examen_sede", "Puede ver clave de examen en sede"),
            ("puede_evaluar_videos_clases_virtuales", "Puede ver evaluar videos de clases virtuales"),
            ("puede_ver_seguimiento_silabo", "Puede ver seguimiento al silabo"),
            ("puede_configurar_componente_periodo", "Puede configurar componente periodo"),
            ("puede_visualizar_detalle_informe_facultades", "Puede visualizar el cumplimiento de informes mensuales de todas las facultades"),
            ("puede_adicionar_cupo_materia", "Puede adicionar cupos de la materia para matricula estudiante"),
            ("puede_aprobar_cupo_materia", "Puede aprobar cupos de la materia para matricula estudiante"),
            ("puede_eliminar_inscripcion_vinculacion", "Puede eliminar inscripcion del estudiante de vinculación"),
            ("puede_gestionar_presidentes_curso", "Puede gestionar presidentes de curso"),
        )


class HorarioTutoriaAcademica(ModeloBase):
    profesor = models.ForeignKey('sga.Profesor', blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    turno = models.ForeignKey('sga.Turno', blank=True, null=True, verbose_name=u'Turno', on_delete=models.CASCADE)
    dia = models.IntegerField(choices=DIAS_CHOICES, default=0, verbose_name=u'Dia')
    fecha_inicio_horario_tutoria = models.DateField(verbose_name=u'Fecha inicia horario tutoria docente', blank=True, null=True)
    fecha_fin_horario_tutoria = models.DateField(verbose_name=u'Fecha finaliza horario tutoria docente', blank=True, null=True)
    profesormateria = models.ForeignKey('sga.ProfesorMateria', verbose_name=u'Materia', blank=True, null=True, on_delete=models.CASCADE)
    claseactividad = models.ForeignKey('sga.ClaseActividad', verbose_name=u'Horario de Actividades', blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.get_dia_display() if not self.dia == 0 else 'DOMINGO', self.turno)

    class Meta:
        verbose_name = u'Horario tutoria académica'
        verbose_name_plural = u'Horarios tutorias académicas'
        ordering = ('profesor', )

    def en_uso(self):
        return self.solicitudtutoriaindividual_set.filter(status=True).exists()
            # return True
        # if self.registroclasetutoriadocente_set.exists():
        #     return True
        # return False

    def disponibletutoria(self):
        d = datetime.now()
        materias = Materia.objects.filter(pk__in=ProfesorMateria.objects.values_list("materia_id", flat=True).filter(profesor=self.profesor, materia__nivel__periodo=self.periodo, status=True).distinct())
        contador = 0
        for materia in materias:
            if self.periodo.tiene_dias_nolaborables(d, materia):
                contador += 1
        if materias.count() != contador:
            # if self.periodo.diasnolaborable_set.filter(fecha=d.date(), status=True, activo=True).exists():
            #     return False
            if self.dia == d.isoweekday():
                if self.turno:
                    d2 = datetime(d.year, d.month, d.day, self.turno.comienza.hour, self.turno.comienza.minute)
                    turnocomienza = (d2 - timedelta(minutes=10))
                    if d.time() >= turnocomienza.time() and d.time() <= self.turno.termina:
                        return True
        return False

    # def disponibletutoria(self):
    #     d = datetime.now()
    #     if self.dia == d.isoweekday():
    #         if self.turno:
    #             if time.localtime().tm_hour >= self.turno.comienza.hour and time.localtime().tm_hour <= self.turno.termina.hour:
    #                 return True
    #     return False

    def tiene_registro(self):
        return self.registroclasetutoriadocente_set.filter(horario=self, numerosemana=datetime.today().isocalendar()[1], status=True).exists()

    def dia_semana(self):
        return DIAS_CHOICES[self.dia - 1][1]

    def save(self, *args, **kwargs):
        super(HorarioTutoriaAcademica, self).save(*args, **kwargs)


ESTADO_SOLICITUD_TUTORIA = (
    (1, u"SOLICITADO"),
    (2, u"PROGRAMADO"),
    (3, u"EJECUTADO"),
    (4, u"CANCELADO"),
)

ESTADO_INFORME = (
    (1, u"GENERADO"),
    (2, u"FIRMADO"),
    (3, u"REVISADO"),
    (4, u"APROBADO"),
)

TIPO_RUBRICA = (
    (1, u"NINGUNA"),
    (2, u"SIN PROCESO DE TITULACIÓN"),
    (3, u"MODELO EVALUATIVO"),
    (4, u"PROMEDIO ASIGNATURAS"),
)

TOPICO_SOLICITUD_TUTORIA = (
    (0, u"NINGUNO"),
    (1, u"REFUERZO ACADÉMICO"),
    (2, u"CONSULTAS SOBRE ACTIVIDADES ACADÉMICAS"),
)

TIPO_SOLICITUD_TUTORIA = (
    (0, u"NINGUNO"),
    (1, u"INDIVIDUAL"),
    (2, u"GRUPAL"),
)

TIPO_TUTORIA = (
    (0, u"-"),
    (1, u"SOLICITADA"),
    (2, u"CONVOCADA DIRECTA"),
    (3, u"CONVOCADA CALCULADA"),
    (4, u"MANUAL"),
)

CLASE_NOVEDAD = (
    (0, u"-------"),
    (1, u"INGRESO"),
    (2, u"SALIDA"),
)

TIPO_ACCION = (
    (1, 'GENERACIÓN'),
    (2, 'MODIFICACION'),
    (3, 'ELIMINACIÓN'),
)

RESPONSABILIDAD_FIRMA = (
    (1, 'REVISADO POR'),
    (2, 'APROBADO POR'),
    (3, 'VALIDADO POR'),
)

TIPO_INFORME = (
    (1, 'TUTOR PRÁCTICAS PRE-PROFESIONALES (INTERNADO ROTATIVO) - SALUD'),
    (2, 'APOYO A VICERRECTORADO ACADÉMICO DE FORMACIÓN DE GRADO'),
)

TIPO_INDICADOR_PP = (
    (0, u"-------"),
    (1, u"OBSERVACIONES"),
    (2, u"SUGERENCIAS"),
    (3, u"ANTECEDENTES"),
    (4, u"MARCO JURIDICO"),
)

ESTADO_JUSTIFICACION_TUTORIA = ((0, '-----'), (1, 'SOLICITADO'), (2, 'APROBADO'), (3, 'RECHAZADO'))


class RegistroClaseTutoriaDocente(ModeloBase):
    horario = models.ForeignKey(HorarioTutoriaAcademica, blank=True, null=True, verbose_name=u'Horario', on_delete=models.CASCADE)
    tipotutoria = models.IntegerField(choices=TIPO_TUTORIA, default=0, blank=True, null=True, verbose_name=u"Tipo tutoria")
    profesor = models.ForeignKey('sga.Profesor', blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')
    numerosemana = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de la semana')
    justificada = models.BooleanField(default=False, verbose_name=u'Tutoria Justuficada')
    justificacionasistencia = models.TextField(default='', max_length=1000, verbose_name=u"Justificacion asistencia")
    archivoevidencia = models.FileField(upload_to='evidenciajustificaciontutoria', blank=True, null=True, verbose_name=u'Archivo Evidencia')
    fechajustificacion = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de justificacion')
    estadojustificacion = models.IntegerField(choices=ESTADO_JUSTIFICACION_TUTORIA, default=0, verbose_name=u'Estado')
    enlaceuno = models.TextField(default='', verbose_name=u'Enlace 1')

    def __str__(self):
        return u'%s - %s - %s' % (self.horario, self.fecha, self.numerosemana)

    class Meta:
        verbose_name = u'Registro clase tutoria docente'
        verbose_name_plural = u'Registros clases tutorias docente'
        ordering = ('horario', )


class SolicitudTutoriaIndividual(ModeloBase):
    horario = models.ForeignKey(HorarioTutoriaAcademica, blank=True, null=True, verbose_name=u'Horario', on_delete=models.CASCADE)
    profesor = models.ForeignKey('sga.Profesor', blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, blank=True, null=True, verbose_name=u'Materia alumno', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_TUTORIA,default=1, blank=True, null=True,  verbose_name=u"Estado solicitud")
    topico = models.IntegerField(choices=TOPICO_SOLICITUD_TUTORIA,default=0, blank=True, null=True,  verbose_name=u"Tópico solicitud")
    fechasolicitud = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha solicitud')
    fechatutoria = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha tutoria')
    tutoriacomienza = models.TimeField(blank=True, null=True, verbose_name=u'Comienza')
    tutoriatermina = models.TimeField(blank=True, null=True, verbose_name=u'Termina')
    asistencia = models.BooleanField(default=False, verbose_name=u"Asitencia")
    observacion = models.TextField(default='', max_length=1000, verbose_name=u"Observación")
    respuestapregunta = models.BooleanField(default=False, verbose_name=u"¿Los inconvenientes en el aprendizaje del estudiante, responde a factores que no están asociados a lo académico.?")
    tipo = models.IntegerField(choices=TIPO_SOLICITUD_TUTORIA, default=0, blank=True, null=True, verbose_name=u"Tipo de solicitud de tutoria grupal o individual")
    manual = models.BooleanField(default=False, verbose_name=u"Registra tutoria manual")
    observacion_estudiante = models.TextField(default='',blank=True, null=True, max_length=1000, verbose_name=u"Observación ingresada por el estudiante")
    tipotutoria = models.IntegerField(choices=TIPO_TUTORIA, default=0, blank=True, null=True, verbose_name=u"Tipo tutoria")
    resultadoencuesta = models.IntegerField(blank=True, null=True, verbose_name=u"Resultado de realizar encuestas")
    promedio_actividad = models.FloatField(default=0, blank=True, null=True,  verbose_name=u'promedio de actividadaes tutoria calculada')
    justificacionasistencia = models.TextField(default='', max_length=1000, verbose_name=u"Justificacion asistencia manual")
    asistenciamanual = models.BooleanField(default=False, verbose_name=u"Registro asistencia manual")

    def __str__(self):
        return u'%s - %s - %s' % (self.horario if not self.manual else self.fechatutoria ,self.materiaasignada.matricula.inscripcion.persona.nombre_completo_inverso(),self.get_estado_display())

    class Meta:
        verbose_name = u'Solicitud tutoria individual'
        verbose_name_plural = u'Solicitudes tutoria individuales'
        ordering = ('horario', )

    def temas(self):
        return self.solicitudtutoriaindividualtema_set.filter(status=True)

    def disponibletutoria(self):
        d = datetime.now()
        if self.fechatutoria:
            if self.fechatutoria.isoweekday() == d.isoweekday() and self.fechatutoria.date() == d.date():
                # if time.localtime().tm_hour >= self.tutoriacomienza.hour and time.localtime().tm_hour<=self.tutoriatermina.hour:
                #     return True
                if d.time() >= self.tutoriacomienza and d.time() <= self.tutoriatermina:
                    return True
        return False

    def tutoria_pasada_fecha(self):
        d = datetime.now()
        if self.fechatutoria:
            if d.date() > self.fechatutoria.date():
                return True
            elif self.fechatutoria.date() == d.date():
                if d.time() > self.tutoriatermina:
                    return True
                else:
                    return False
            else:
                return False
        return False

    def registros_relacionados(self,profesor, periodo):
        return SolicitudTutoriaIndividual.objects.filter(status=True,
                                                         estado=2,
                                                         tipotutoria=self.tipotutoria,
                                                         fechatutoria=self.fechatutoria,
                                                         tutoriacomienza=self.tutoriacomienza,
                                                         tutoriatermina=self.tutoriatermina,
                                                         profesor=profesor,
                                                         materiaasignada__matricula__nivel__periodo=periodo).order_by('materiaasignada__materia','topico')

    def mis_temas_registros_relacionados(self,profesor,periodo):
        return SolicitudTutoriaIndividualTema.objects.values('tema__temaunidadresultadoprogramaanalitico__descripcion').filter(status=True, solicitud__status=True,
                                                                                                                               solicitud__estado=2,
                                                                                                                               solicitud__tipotutoria=self.tipotutoria,
                                                                                                                               solicitud__fechatutoria=self.fechatutoria,
                                                                                                                               solicitud__tutoriacomienza=self.tutoriacomienza,
                                                                                                                               solicitud__tutoriatermina=self.tutoriatermina,
                                                                                                                               solicitud__profesor=profesor,
                                                                                                                               solicitud__materiaasignada__matricula__nivel__periodo=periodo).order_by('tema').distinct()

    def fechatoperep(self):
        fechatutoria = datetime(self.fechatutoria.year, self.fechatutoria.month, self.fechatutoria.day, self.tutoriacomienza.hour, self.tutoriacomienza.minute) - timedelta(days=1)
        return datetime.now()-timedelta(days=1)<=fechatutoria

    def save(self, *args, **kwargs):
        super(SolicitudTutoriaIndividual, self).save(*args, **kwargs)


class SolicitudTutoriaIndividualTema(ModeloBase):
    solicitud = models.ForeignKey(SolicitudTutoriaIndividual, blank=True, null=True, verbose_name=u'Solicitud', on_delete=models.CASCADE)
    tema = models.ForeignKey(DetalleSilaboSemanalTema, blank=True, null=True, verbose_name=u'Tema', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.tema

    class Meta:
        verbose_name = u'Solicitud tutoria individual tema'
        verbose_name_plural = u'Solicitudes tutoria individuales con temas'
        ordering = ('solicitud', )


class TipoRecurso(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u"Descripción")

    def __str__(self):
        return u'%s ' % self.descripcion

    class Meta:
        verbose_name = u'Tipo de recurso'
        verbose_name_plural = u'Tipos de recursos'
        ordering = ('descripcion', )
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion= self.descripcion.upper()
        super(TipoRecurso, self).save(*args, **kwargs)


TIPO_ARCHIVO = (
    (1, u'WORD'),
    (2, u'PDF'),
)


class EtapaProyectoCurricular(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u"Descripción")

    def __str__(self):
        return u'%s ' % self.descripcion

    class Meta:
        verbose_name = u'Etapa Proyecto Curricular'
        verbose_name_plural = u'Etapas Proyecto Curricular'
        ordering = ('descripcion', )
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion= self.descripcion.upper()
        super(EtapaProyectoCurricular, self).save(*args, **kwargs)


# class SubElementoProyectoCurricular(ModeloBase):
#     elementoproyectocurricular = models.ForeignKey(ElementoProyectoCurricular, blank=True, null=True, verbose_name=u'Elemento Proyecto Curricular')
#     descripcion = models.TextField(default='', verbose_name=u"Descripción")
#
#     def __str__(self):
#         return u'%s ' % (self.descripcion)
#
#     class Meta:
#         verbose_name = u'Sub Elemento Proyecto Curricular'
#         verbose_name_plural = u'Sub Elemento Proyecto Curricular'
#         ordering = ('descripcion', )
#
#     def save(self, *args, **kwargs):
#         self.descripcion = self.descripcion.upper()
#         super(SubElementoProyectoCurricular, self).save(*args, **kwargs)



TIPO_ACADEMIA_NIVEL_FORMACION = (
    (1, u'PREGRADO'),
    (2, u'POSGRADO'),
)


class NivelFormacionPac(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u"DescripciÃ³n")
    tipo = models.IntegerField(default=1, choices=TIPO_ACADEMIA_NIVEL_FORMACION, verbose_name=u'Tipo')

    def __str__(self):
        return u'%s ' % self.descripcion

    class Meta:
        verbose_name = u'Nivel FormaciÃ³n'
        verbose_name_plural = u'Niveles FormaciÃ³n'
        ordering = ('descripcion', )
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion= self.descripcion.upper()
        super(NivelFormacionPac, self).save(*args, **kwargs)


class CampoAmplioPac(ModeloBase):
    codigo = models.CharField(blank=True, null=True, max_length=50, verbose_name=u'Codigo')
    descripcion = models.TextField(default='', verbose_name=u"Descripción")
    nivelformacion = models.ForeignKey(NivelFormacionPac, blank=True, null=True,verbose_name= u'Nivel Formacion', on_delete=models.CASCADE)

    def __str__(self):
        return "[{}] {}".format(self.codigo, self.descripcion)

    def enuso(self):
        return CampoEspecificoPac.objects.filter(campoampliopac=self, status=True).exists()

    class Meta:
        verbose_name = u'Campo Amplio'
        verbose_name_plural = u'Campos Amplios'
        ordering = ('descripcion', )

    def save(self, *args, **kwargs):
        self.codigo= self.codigo.upper()
        self.descripcion= self.descripcion.upper()
        super(CampoAmplioPac, self).save(*args, **kwargs)


class CampoEspecificoPac(ModeloBase):
    campoampliopac = models.ForeignKey(CampoAmplioPac, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Campo Amplio')
    codigo = models.CharField(blank=True, null=True, max_length=50, verbose_name=u'Codigo')
    descripcion = models.TextField(default='', verbose_name=u"Descripción")
    nivelformacion = models.ForeignKey(NivelFormacionPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Nivel Formacion')

    def __str__(self):
        return "[{}] {}".format(self.codigo, self.descripcion)

    def enuso(self):
        return CampoDetalladoPac.objects.filter(campoespecificopac=self, status=True).exists()

    class Meta:
        verbose_name = u'Campo Especifico'
        verbose_name_plural = u'Campos Especificos'
        ordering = ('descripcion', )

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper()
        self.descripcion = self.descripcion.upper()
        super(CampoEspecificoPac, self).save(*args, **kwargs)


class CampoDetalladoPac(ModeloBase):
    campoespecificopac = models.ForeignKey(CampoEspecificoPac, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Campo Especifico')
    codigo = models.CharField(blank=True, null=True, max_length=50, verbose_name=u'Codigo')
    descripcion = models.TextField(default='', verbose_name=u"Descripción")
    nivelformacion = models.ForeignKey(NivelFormacionPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Nivel Formacion')

    def __str__(self):
        return "[{}] {}".format(self.codigo, self.descripcion)

    def enuso(self):
        return CarreraPac.objects.filter(campodetalladopac=self, status=True).exists()

    class Meta:
        verbose_name = u'Campo Detallado'
        verbose_name_plural = u'Campos Detallados'
        ordering = ('descripcion', )

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper()
        self.descripcion = self.descripcion.upper()
        super(CampoDetalladoPac, self).save(*args, **kwargs)


class CarreraPac(ModeloBase):
    campodetalladopac = models.ForeignKey(CampoDetalladoPac, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Campo Detallado')
    codigo = models.CharField(blank=True, null=True, max_length=50, verbose_name=u'Codigo')
    descripcion = models.TextField(default='', verbose_name=u"Descripción")
    abreviaturacarrera = models.CharField(blank=True, null=True, max_length=10, verbose_name=u'Abreviatura')
    nivelformacion = models.ForeignKey(NivelFormacionPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Nivel Formacion')

    def __str__(self):
        return u'%s ' % self.descripcion

    def enuso(self):
        return TitulacionPac.objects.filter(carrerapac=self, status=True).exists()

    class Meta:
        verbose_name = u'Carrera'
        verbose_name_plural = u'Carreras'
        ordering = ('descripcion', )

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper()
        self.descripcion= self.descripcion.upper()
        self.abreviaturacarrera = self.abreviaturacarrera.upper()
        super(CarreraPac, self).save(*args, **kwargs)


class TitulacionPac(ModeloBase):
    carrerapac = models.ForeignKey(CarreraPac, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Carrera')
    codigo = models.CharField(blank=True, null=True, max_length=50, verbose_name=u'Codigo')
    tituloobtenidohombre = models.TextField(blank=True, null=True, verbose_name=u'Titulo obtenido hombre')
    tituloobtenidomujer = models.TextField(blank=True, null=True, verbose_name=u'Titulo obtenido mujer')
    nivelformacion = models.ForeignKey(NivelFormacionPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Nivel Formacion')

    def __str__(self):
        return u'%s ' % self.tituloobtenidohombre

    class Meta:
        verbose_name = u'Titulacion'
        verbose_name_plural = u'Titulaciones'

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper()
        self.tituloobtenidohombre= self.tituloobtenidohombre.upper()
        self.tituloobtenidomujer= self.tituloobtenidomujer.upper()
        super(TitulacionPac, self).save(*args, **kwargs)


class TituloGradoAcademicoPac(ModeloBase):
    campoampliopac = models.ForeignKey(CampoAmplioPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Campo Amplio')
    campoespecificopac = models.ForeignKey(CampoEspecificoPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Campo Especifico')
    campodetalladopac = models.ForeignKey(CampoDetalladoPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Campo Detallado')
    carrerapac = models.ForeignKey(CarreraPac, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Carrera')
    titulacionpac = models.ForeignKey(TitulacionPac, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Titulacion')

    class Meta:
        verbose_name = u'Titulo Grado Academico'
        verbose_name_plural = u'Titulo Grados Academicos'

    def save(self, *args, **kwargs):
        super(TituloGradoAcademicoPac, self).save(*args, **kwargs)


class TipoTramiteRediseno(ModeloBase):
    descripcion = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"Descripcion")

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoTramiteRediseno, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Tipo trámite Redisenio'
        verbose_name_plural = u'Tipos trámites Redisenio'
        ordering = ('descripcion',)


TIPO_FORMACION_REDISEÑO = (
    (1, u'PREGRADO'),
    (2, u'POSGRADO'),
)


class TipoFormacionRediseno(ModeloBase):
    descripcion = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"Descripcion")
    tipo = models.IntegerField(choices=TIPO_FORMACION_REDISEÑO, default=1, blank=True, null=True, verbose_name=u'tipo de formación')

    def __str__(self):
        return u'%s - %s' % (self.descripcion,self.get_tipo_display())

    def en_uso(self):
        return self.programapac_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoFormacionRediseno, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Tipo formación Redisenio'
        verbose_name_plural = u'Tipos formación Redisenio'
        ordering = ('descripcion',)


class IndiceHoraPlanificacion(ModeloBase):
    valor = models.FloatField(default=0.00, verbose_name=u'Indice Hora planificacion')

    def __str__(self):
        return u'%s ' % self.valor

    class Meta:
        verbose_name = u'Indice hora planificación PAC'
        verbose_name_plural = u'Indices hora planificación PAC'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        super(IndiceHoraPlanificacion, self).save(*args, **kwargs)


class TipoProcesoPac(ModeloBase):
    descripcion = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"Descripcion")

    def __str__(self):
        return u'%s' % self.descripcion

    def en_uso(self):
        return self.programapac_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoProcesoPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Tipo proceso Pac'
        verbose_name_plural = u'Tipos de procesos Pac'
        ordering = ('descripcion',)


class TipoProgramaPac(ModeloBase):
    descripcion = models.CharField(max_length=200, blank=True, null=True, verbose_name=u"Descripcion")

    def __str__(self):
        return u'%s' % self.descripcion

    def en_uso(self):
        return self.programapac_set.filter(status=True)

    class Meta:
        verbose_name = u'Tipo Programa'
        verbose_name_plural = u'Programas'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoProgramaPac, self).save(*args, **kwargs)

# CHOICES PAC
PERIODO_ORDINARIO_CHOICES = (
    (0, u'0'),
    (1, u'1'),
    (2, u'2'),
    (3, u'3'),
    (4, u'4'),
    (5, u'5'),
    (6, u'6'),
    (7, u'7'),
    (8, u'8'),
    (9, u'9'),
    (10, u'10')
)
SEMANA_PERIODO_ORDINARIO_CHOICES = (
    (0, u'0'),
    (1, u'1'),
    (2, u'2'),
    (3, u'3'),
    (4, u'4'),
    (5, u'5'),
    (6, u'6'),
    (7, u'7'),
    (8, u'8'),
    (9, u'9'),
    (10, u'10'),
    (11, u'11'),
    (12, u'12'),
    (13, u'13'),
    (14, u'14'),
    (15, u'15'),
    (16, u'16'),
    (17, u'17'),
    (18, u'18'),
    (19, u'19'),
    (20, u'20'),
    (21, u'21'),
    (22, u'22'),
    (23, u'23'),
    (24, u'24')
)
PERIODO_EXTRAORDINARIO_CHOICES = (
    (0, u'0'),
    (1, u'1'),
    (2, u'2'),
    (3, u'3'),
    (4, u'4'),
    (5, u'5'),
    (6, u'6'),
    (7, u'7'),
    (8, u'8'),
    (9, u'9'),
    (10, u'10')
)

SEMANA_PERIODO_EXTRAORDINARIO_CHOICES = (
    (0, u'0'),
    (1, u'1'),
    (2, u'2'),
    (3, u'3'),
    (4, u'4'),
    (5, u'5'),
    (6, u'6'),
    (7, u'7'),
    (8, u'8'),
    (9, u'9'),
    (10, u'10'),
    (11, u'11'),
    (12, u'12'),
    (13, u'13'),
    (14, u'14'),
    (15, u'15')
)

UNIDAD_ORGANIZACION_CURRICULAR = (
    ('', u'--Seleccione--'),
    (1, u'UNIDAD BÁSICA'),
    (2, u'UNIDAD PROFESIONAL'),
    (3, u'UNIDAD DE TITULACIÓN'),
    (4, u'UNIDAD DE FORMACIÓN DISCIPLINAR AVANZADA'),
    (5, u'UNIDAD DE INVESTIGACIÓN'),
    (6, u'MULTIDISCIPLINAR'),
    (7, u'INTERDISCIPLINAR'),
    (8, u'UNIDAD DISCIPLINAR, MULTIDISCIPLINAR Y/O INTERDISCIPLINAR AVANZADA')
)

HORAS_DEDICACIÓN_IES = (
    ('', u'--Seleccione--'),
    (40, u'40 HORAS'),
    (20, u'20 HORAS'),
    (10, u'10 HORAS')
)

HORAS_DEDICACIÓN_PROGRAMA = (
    ('', u'--Seleccione--'),
    (40, u'TIEMPO COMPLETO'),
    (20, u'MEDIO TIEMPO'),
    (10, u'TIEMPO PARCIAL')
)

# Datos generales de la carrera/programa


class ProgramaPac(ModeloBase):
    #DATOS GENERALES.
    tipotramite = models.ForeignKey(TipoTramiteRediseno, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo Trámite')
    tipoproceso = models.ForeignKey(TipoProcesoPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de Proceso')
    tipoprograma = models.ForeignKey(TipoProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de Programa')
    codigosniese = models.CharField(blank=True, null=True, max_length=50, verbose_name=u'Codigo SNIESE')
    proyectoinnovador = models.IntegerField(choices=VALOR_SI_NO,blank=True, null=True, default=0, verbose_name=u'Proyecto Innovador')
    tipoformacion = models.ForeignKey(TipoFormacionRediseno, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo formación re diseño')
    modalidad = models.ForeignKey(Modalidad, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Modalidad')
    ejecucionmodalidad = models.TextField(default='', blank=True, null=True, verbose_name=u"Descripcion de la ejecucion de la modalidad")
    proyectoenred = models.IntegerField(choices=VALOR_SI_NO, blank=True, null=True, default=0,verbose_name=u'Proyecto en red')
    integrantesred = models.ManyToManyField(InstitucionEducacionSuperior, verbose_name=u'Integrantes de la Red')
    campostitulacion = models.ForeignKey(CamposTitulosPostulacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Campos Títulos')
    # campoampliopac = models.ForeignKey(CampoAmplioPac, blank=True, null=True, verbose_name=u'Campo Amplio', on_delete=models.CASCADE)
    # campoespecificopac = models.ForeignKey(CampoEspecificoPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Campo Especifico')
    # campodetalladopac = models.ForeignKey(CampoDetalladoPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Campo Detallado')
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Carrera')
    # titulacionpac = models.ForeignKey(TitulacionPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Titulacion')
    #RESUMEN DE LA DESCRIPCIÓN MICROCURRICULAR
    numeroperiodosordinario = models.IntegerField(choices=PERIODO_ORDINARIO_CHOICES, default=0, blank=True, null=True, verbose_name=u'Periodo Académico Ordinario')
    numerosemanaordinario = models.IntegerField(choices=SEMANA_PERIODO_ORDINARIO_CHOICES, default=0, blank=True, null=True, verbose_name=u'Semana Periodo Académico')
    periodoextraordinario = models.IntegerField(choices=VALOR_SI_NO, blank=True, null=True, default=0, verbose_name=u'Periodo Extraordinario')
    numeroperiodosextraordinario = models.IntegerField(choices=PERIODO_EXTRAORDINARIO_CHOICES, default=0,blank=True, null=True, verbose_name=u'Periodo Extraordinario')
    numerosemanaextraordinario = models.IntegerField(choices=SEMANA_PERIODO_EXTRAORDINARIO_CHOICES, blank=True, null=True, default=0,  verbose_name=u'Periodo Extraordinario')
    totalhoras = models.DecimalField(default=0.00, max_digits=30, null=True, blank=True, decimal_places=2, verbose_name=u'Total Horas') #ya existia, se lo calculaba
    totalhorasaprendizajecontactodocente = models.DecimalField(default=0.00, max_digits=30, null=True, blank=True, decimal_places=2, verbose_name=u'Total de horas de aprendizaje en contacto con el docente')
    totalhorasaprendizajepracticoexperimental = models.DecimalField(default=0.00, max_digits=30, null=True, blank=True, decimal_places=2, verbose_name=u'Total de horas del aprendizaje práctico-experimental')
    totalhorasaprendizajeautonomo = models.DecimalField(default=0.00, max_digits=30, null=True, blank=True, decimal_places=2, verbose_name=u'Total de horas del aprendizaje autónomo')
    totalhoraspracticasprofesionales = models.DecimalField(default=0.00, max_digits=30, null=True, blank=True, decimal_places=2, verbose_name=u'Total de horas de prácticas profesionales')
    totalhorasunidadtitulacion = models.DecimalField(default=0.00, max_digits=30, null=True, blank=True, decimal_places=2, verbose_name=u'Total de horas de la unidad de titulación')
    numerocohorte = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de cohortes')
    numeroparalelocohorte = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de paralelos por cohorte')
    numeroestudiantecohorte = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de estudiantes por cohorte')
    numerototalasignatura = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número total de asignaturas')
    totalcreditos = models.DecimalField(default=0.0000, max_digits=30, null=True, blank=True, decimal_places=4, verbose_name=u'Total Créditos') #se lo calcula, estan en el documento
    indicehoraplanificacion = models.ForeignKey(IndiceHoraPlanificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Indice Hora Planificacion')
    mencionitinerario = models.IntegerField(choices=VALOR_SI_NO, blank=True, null=True, default=1, verbose_name=u'Con mención Itinerario')
    # Resolución del Órgano Colegiado Superior de aprobación del programa (OCS)
    fechaaprobacion = models.DateField(verbose_name=u'Fecha de aprobación', blank=True, null=True)
    numeroresolucion = models.TextField(default='', blank=True, null=True, verbose_name=u'Número Resolución (OCS)')
    sesion = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Sesión del OCS')
    # anexoresolucion = models.FileField(upload_to='anexoresolucion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Anexo de resolución (OCS)')
    numeroresolucioncaces = models.TextField(default='', blank=True, null=True, verbose_name=u'Número Resolución (CACES/CES)')
    fechaaprobacioncaces = models.DateField(verbose_name=u'Fecha de aprobación CACES', blank=True, null=True)
    # anexoresolucioncaces = models.FileField(upload_to='anexoresolucion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Anexo de resolución (CACES/CES)')
    #LUGAR(ES) DE LA EJECUCIÓN DE LA CARRERA/PROGRAMA
    estructurainstitucional = models.TextField(default='', blank=True, null=True, verbose_name=u'Estructura institucional')
    provincia = models.ForeignKey('sga.Provincia', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Provincia")
    canton = models.ForeignKey('sga.Canton', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Canton")
    parroquia = models.ForeignKey('sga.Parroquia', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Parroquia")
    finalizado = models.BooleanField(default=False, verbose_name=u"finalizado?")

    def __str__(self):
        return u'%s ' % self.carrera

    # def download_link_ocs(self):
    #     return self.anexoresolucion.url
    #
    # def download_link_caces(self):
    #     return self.anexoresolucioncaces.url

    def numero_sesion(self):
        sesiones = {
            1: 'PRIMERA', 2: 'SEGUNDA', 3: 'TERCERA', 4: 'CUARTA', 5: 'QUINTA',
            6: 'SEXTA', 7: 'SÉPTIMA', 8: 'OCTAVA', 9: 'NOVENA', 10: 'DÉCIMA',
            11: 'UNDÉCIMA', 12: 'DUODÉCIMA', 13: 'DECIMOTERCERA', 14: 'DECIMOCUARTA',
            15: 'DECIMOQUINTA', 16: 'DECIMOSEXTA', 17: 'DECIMOSÉPTIMA', 18: 'DECIMOCTAVA',
            19: 'DECIMONOVENA', 20: 'VIGÉSIMA', 21: 'VIGÉSIMA PRIMERA', 22: 'VIGÉSIMA SEGUNDA',
            23: 'VIGÉSIMA TERCERA', 24: 'VIGÉSIMA CUARTA', 25: 'VIGÉSIMA QUINTA',
            26: 'VIGÉSIMA SEXTA', 27: 'VIGÉSIMA SÉPTIMA', 28: 'VIGÉSIMA OCTAVA',
            29: 'VIGÉSIMA NOVENA', 30: 'TRIGÉSIMA', 31: 'TRIGÉSIMA PRIMERA',
            32: 'TRIGÉSIMA SEGUNDA', 33: 'TRIGÉSIMA TERCERA', 34: 'TRIGÉSIMA CUARTA',
            35: 'TRIGÉSIMA QUINTA', 36: 'TRIGÉSIMA SEXTA', 37: 'TRIGÉSIMA SÉPTIMA',
            38: 'TRIGÉSIMA OCTAVA', 39: 'TRIGÉSIMA NOVENA', 40: 'CUADRAGÉSIMA',
            41: 'CUADRAGÉSIMA PRIMERA', 42: 'CUADRAGÉSIMA SEGUNDA', 43: 'CUADRAGÉSIMA TERCERA',
            44: 'CUADRAGÉSIMA CUARTA', 45: 'CUADRAGÉSIMA QUINTA', 46: 'CUADRAGÉSIMA SEXTA',
            47: 'CUADRAGÉSIMA SÉPTIMA', 48: 'CUADRAGÉSIMA OCTAVA', 49: 'CUADRAGÉSIMA NOVENA',
            50: 'QUINCUAGÉSIMA', 51: 'QUINCUAGÉSIMA PRIMERA', 52: 'QUINCUAGÉSIMA SEGUNDA',
            53: 'QUINCUAGÉSIMA TERCERA', 54: 'QUINCUAGÉSIMA CUARTA', 55: 'QUINCUAGÉSIMA QUINTA',
            56: 'QUINCUAGÉSIMA SEXTA', 57: 'QUINCUAGÉSIMA SÉPTIMA', 58: 'QUINCUAGÉSIMA OCTAVA',
            59: 'QUINCUAGÉSIMA NOVENA', 60: 'SEXAGÉSIMA', 61: 'SEXAGÉSIMA PRIMERA',
            62: 'SEXAGÉSIMA SEGUNDA', 63: 'SEXAGÉSIMA TERCERA', 64: 'SEXAGÉSIMA CUARTA',
            65: 'SEXAGÉSIMA QUINTA', 66: 'SEXAGÉSIMA SEXTA', 67: 'SEXAGÉSIMA SÉPTIMA',
            68: 'SEXAGÉSIMA OCTAVA', 69: 'SEXAGÉSIMA NOVENA', 70: 'SEPTUAGÉSIMA',
            71: 'SEPTUAGÉSIMA PRIMERA', 72: 'SEPTUAGÉSIMA SEGUNDA', 73: 'SEPTUAGÉSIMA TERCERA',
            74: 'SEPTUAGÉSIMA CUARTA', 75: 'SEPTUAGÉSIMA QUINTA', 76: 'SEPTUAGÉSIMA SEXTA',
            77: 'SEPTUAGÉSIMA SÉPTIMA', 78: 'SEPTUAGÉSIMA OCTAVA', 79: 'SEPTUAGÉSIMA NOVENA',
            80: 'OCTOGÉSIMA', 81: 'OCTOGÉSIMA PRIMERA', 82: 'OCTOGÉSIMA SEGUNDA',
            83: 'OCTOGÉSIMA TERCERA', 84: 'OCTOGÉSIMA CUARTA', 85: 'OCTOGÉSIMA QUINTA',
            86: 'OCTOGÉSIMA SEXTA', 87: 'OCTOGÉSIMA SÉPTIMA', 88: 'OCTOGÉSIMA OCTAVA',
            89: 'OCTOGÉSIMA NOVENA', 90: 'NONAGÉSIMA', 91: 'NONAGÉSIMA PRIMERA',
            92: 'NONAGÉSIMA SEGUNDA', 93: 'NONAGÉSIMA TERCERA', 94: 'NONAGÉSIMA CUARTA',
            95: 'NONAGÉSIMA QUINTA', 96: 'NONAGÉSIMA SEXTA', 97: 'NONAGÉSIMA SÉPTIMA',
            98: 'NONAGÉSIMA OCTAVA', 99: 'NONAGÉSIMA NOVENA', 100: 'CENTÉSIMA'
        }
        return sesiones.get(self.sesion, '')

    class Meta:
        verbose_name = u'Programa'
        verbose_name_plural = u'Programas'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        # self.ejecucionmodalidad = self.ejecucionmodalidad.upper()
        self.estructurainstitucional = self.estructurainstitucional.upper()
        self.totalcreditos = self.totalcreditos.__round__(4)
        super(ProgramaPac, self).save(*args, **kwargs)


class InformacionInstitucionalPac(ModeloBase):
    nombreinstitucion = models.TextField(default='', verbose_name=u'Valor', blank=True)
    codigoiess = models.TextField(default='', verbose_name=u'Valor', blank=True)
    categoriaies = models.ForeignKey('sga.CategoriaIes', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Categoria Ies')
    tipofinanciamiento = models.ForeignKey('sga.TipoFinanciamiento', on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Tipo Financiamiento')
    siglas = models.TextField(default='', verbose_name=u'Siglas', blank=True)
    mision = models.TextField(default='', verbose_name=u'Misión', blank=True)
    vision = models.TextField(default='', verbose_name=u'Visión', blank=True)
    direccion = models.TextField(default='', verbose_name=u'Dirección', blank=True)
    rector = models.ForeignKey('sga.Profesor', on_delete=models.CASCADE, blank=True, related_name='+', null=True, verbose_name=u'Rector')
    extrector = models.CharField(default='', verbose_name=u'Extensión Rector', max_length=10)
    decano = models.ForeignKey('sga.Profesor', on_delete=models.CASCADE, blank=True, related_name='+', null=True, verbose_name=u'Decano')
    extdecano = models.CharField(default='', verbose_name=u'Extensión Decano', max_length=10)
    coordinador = models.ForeignKey('sga.Profesor', on_delete=models.CASCADE, blank=True, related_name='+', null=True, verbose_name=u'Director/a o coordinador/a')
    programapac = models.ForeignKey(ProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Programa pac')

    def __str__(self):
        return u"%s" % self.coordinador

    class Meta:
        verbose_name = u'Informacion Institucional Pac'
        verbose_name_plural = u'Informaciones Institucionales Pac'
        ordering = ('id',)


class DetalleItinerarioProgramaPac(ModeloBase):
    programaPac = models.ForeignKey(ProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Detalle Programa Pac")
    nombreitinerario = models.TextField(default='', blank=True, null=True, verbose_name=u"Nombre de Itinerario")
    nivelitinerario = models.ForeignKey(NivelMalla, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Nivel de Itinerario")
    codigo = models.TextField(default='', blank=True, null=True, verbose_name=u"Codigo de Itinerario")

    def __str__(self):
        return u"%s - %s" % (self.nombreitinerario, self.nivelitinerario)

    def save(self, *args, **kwargs):
        self.nombreitinerario = self.nombreitinerario.upper()
        super(DetalleItinerarioProgramaPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Detalle Itinerario Programa Pac'
        verbose_name_plural = u'Detalles Itinerarios Programa Pac'
        ordering = ('id',)


class AprobacionTrabajoIntegracionCurricular(ModeloBase):
    descripcion = models.TextField(default='',blank=True, null=True, verbose_name=u"Aprobación del trabajo de la unidad de integración curricular / unidad de titulación")

    def __str__(self):
        return u'%s ' % self.descripcion

    def en_uso(self):
        return self.funcionsustantivadocenciapac_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(AprobacionTrabajoIntegracionCurricular, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Aprobacion Trabajo Integracion Curricular'
        verbose_name_plural = u'Aprobaciones Trabajos Integracion Curricular'
        ordering = ('descripcion',)


class ConveniosPac(ModeloBase):
    programapac = models.ForeignKey(ProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'ProgramaPac')
    convenioinstitucional = models.ForeignKey(ConvenioEmpresa, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Convenio Institucional')

    def __str__(self):
        return u'%s ' % self.convenioinstitucional.empresaempleadora.nombre

    class Meta:
        verbose_name = u'Convenio Pac'
        verbose_name_plural = u'Convenios Pac'
        ordering = ('id',)


class PreguntasPac(ModeloBase):
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u"Preguntas de Perfil de egreso")

    def __str__(self):
        return u'%s ' % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(PreguntasPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Pregunta Pac'
        verbose_name_plural = u'Preguntas Pac'
        ordering = ('descripcion',)


class FuncionSustantivaDocenciaPac(ModeloBase):
    programapac = models.ForeignKey(ProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'ProgramaPac')
    objetivogeneral = models.TextField(default='', blank=True, null=True, verbose_name=u"Objetivo general de la carrera")
    objetivoespecifico = models.TextField(default='', blank=True, null=True, verbose_name=u"Objetivos específicos")
    perfilingreso = models.TextField(default='', blank=True, null=True, verbose_name=u"Perfil de ingreso")
    requisitoingreso = models.TextField(default='', blank=True, null=True, verbose_name=u"Requisitos de ingreso")
    perfilprofesional = models.TextField(default='', blank=True, null=True, verbose_name=u"Perfil Profesional")
    requisitotitulacion = models.TextField(default='', blank=True, null=True, verbose_name=u"Requisitos de titulación")
    aprobaciontrabajo = models.ManyToManyField(AprobacionTrabajoIntegracionCurricular)
    descripcionintegracioncurricular = models.TextField(default='', blank=True, null=True, verbose_name=u"Opciones de la unidad de integración curricular/ unidad de titulación")
    pertinencia = models.TextField(default='', blank=True, null=True, verbose_name=u"Pertinencia")
    objetoestudio = models.TextField(default='', blank=True, null=True, verbose_name=u"Objeto de estudio del proyecto")
    metodologiaambiente = models.TextField(default='', blank=True, null=True, verbose_name=u"Metodología y ambientes de aprendizaje")
    justificacion = models.TextField(default='', blank=True, null=True, verbose_name=u"Justificación de la estructura curricular")

    def __str__(self):
        return u'%s' % self.objetivogeneral

    class Meta:
        verbose_name = u'Funcion Sustantiva Docencia Pac'
        verbose_name_plural = u'Funciones Sustantivas Docencia Pac'
        ordering = ('id',)

class DetallePerfilIngreso(ModeloBase):
    funcionsustantiva = models.ForeignKey(FuncionSustantivaDocenciaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Funcion Sustantiva Docencia Pac")
    alltitulos = models.BooleanField(default=False, verbose_name=u"¿Todos los títulos de tercer nivel?")
    titulo = models.ManyToManyField(Titulo, verbose_name=u'Títulos')
    experiencia = models.BooleanField(default=False, verbose_name=u"¿Necesita experiencia?")
    cantidadexperiencia = models.FloatField(default=0.0, blank=True, null=True, verbose_name=u'Años de experiencia')

    def __str__(self):
        return u"%s" % self.funcionsustantiva

    class Meta:
        verbose_name = u'Detalle Perfil Ingreso'
        verbose_name_plural = u'Detalles Perfil Ingreso'
        ordering = ('id',)

class DetalleRequisitoIngreso(ModeloBase):
    funcionsustantiva = models.ForeignKey(FuncionSustantivaDocenciaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Funcion Sustantiva Docencia Pac")
    requisito = models.ManyToManyField(Requisito, verbose_name=u'Requisito')
    firmaelectronica = models.BooleanField(default=False, verbose_name=u"¿Firma electrónica?")

    def __str__(self):
        return u"%s" % self.funcionsustantiva

    class Meta:
        verbose_name = u'Detalle Requisito de Ingreso'
        verbose_name_plural = u'Detalles Requisitos de Ingreso'
        ordering = ('id',)


class DetallePreguntasPerfilegresoDocenciaPac(ModeloBase):
    funcionsustantivadocenciapac = models.ForeignKey(FuncionSustantivaDocenciaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Funcion Sustantiva Docencia Pac")
    preguntaspac = models.ForeignKey(PreguntasPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Preguntas Pac")
    respuestapac = models.TextField(default='', blank=True, null=True, verbose_name=u"Respuestas de Perfil de egreso")

    def __str__(self):
        return u"%s" % self.preguntaspac.descripcion

    class Meta:
        verbose_name = u'Detalle Pregunta Perfil egreso Docencia Pac'
        verbose_name_plural = u'Detalles Preguntas Perfiles egreso Docencia Pac'
        ordering = ('id',)

class DetalleFuncionSustantivaDocenciaPac(ModeloBase):
    funcionsustantivadocenciapac = models.ForeignKey(FuncionSustantivaDocenciaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Funcion Sustantiva Docencia Pac")
    codigo = models.CharField(blank=True, null=True, max_length=100, verbose_name=u'Abreviatura')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Asignatura")
    nivelperiodoacademico = models.ForeignKey(NivelMalla, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Periodo Académico Nivel")
    itinerariomencion = models.TextField(default='', blank=True, null=True, verbose_name=u"Nombre del Itinerario/Mención")
    unidadorganizacioncurricular = models.IntegerField(choices=UNIDAD_ORGANIZACION_CURRICULAR, default=0, blank=True, null=True, verbose_name=u'Unidad de organización curricular')
    horas = models.FloatField(default=0.0, blank=True, null=True, verbose_name=u'Horas')
    creditos = models.FloatField(default=0.0000, blank=True, null=True, verbose_name=u'Creditos')
    horasacdtotal = models.FloatField(default=0, verbose_name=u'Horas Aprendizaje en contacto con el docente totales', blank=True, null=True)
    horasacdsemanal = models.FloatField(default=0, verbose_name=u'Horas Aprendizaje en contacto con el docente semanales', blank=True, null=True)
    horaspresenciales = models.FloatField(default=0, verbose_name=u'Horas Presenciales', blank=True, null=True)
    horaspresencialessemanales = models.FloatField(default=0, verbose_name=u'Horas Presenciales Semanales', blank=True, null=True)
    horasvirtualtotal = models.FloatField(default=0, verbose_name=u'Horas ACD virtual totales', blank=True, null=True)
    horasvirtualsemanal = models.FloatField(default=0, verbose_name=u'Horas ACD virtual semanales', blank=True, null=True)
    horasapetotal = models.FloatField(default=0, verbose_name=u'Horas aprendizaje práctico experimental totales', blank=True, null=True)
    horasapesemanal = models.FloatField(default=0, verbose_name=u'Horas aprendizaje práctico experimental semanales', blank=True, null=True)
    horasapeasistotal = models.FloatField(default=0, verbose_name=u'Horas aprendizaje práctico experimental asistida totales', blank=True, null=True)
    horasapeasissemanal = models.FloatField(default=0, verbose_name=u'Horas aprendizaje práctico experimental asistida semanales', blank=True, null=True)
    horasapeautototal = models.FloatField(default=0, verbose_name=u'Horas aprendizaje práctico experimental autónomas totales', blank=True, null=True)
    horasapeautosemanal = models.FloatField(default=0, verbose_name=u'Horas aprendizaje práctico experimental autónomas semanales', blank=True, null=True)
    horasautonomas = models.FloatField(default=0, verbose_name=u'Horas Autónomas', blank=True, null=True)
    horasautonomassemanales = models.FloatField(default=0, verbose_name=u'Horas Autonomas Semanales', blank=True, null=True)
    horasvinculaciontotal = models.FloatField(default=0, verbose_name=u'Horas de vinculación totales', blank=True, null=True)
    horasvinculacionsemanal = models.FloatField(default=0, verbose_name=u'Horas de vinculación semanales', blank=True, null=True)
    horasppptotal = models.FloatField(default=0, verbose_name=u'Horas de prácticas pre-profesionales totales', blank=True, null=True)
    horaspppsemanal = models.FloatField(default=0, verbose_name=u'Horas de prácticas pre-profesionales semanales', blank=True, null=True)
    horascolaborativototal = models.FloatField(default=0, verbose_name=u'Horas aprendizaje colaborativo totales', blank=True, null=True)
    valorhoramodulo = models.FloatField(default=0, verbose_name=u'Valor por hora del módulo', blank=True, null=True)

    def __str__(self):
        return u"%s - %s" % (self.asignatura.nombre, self.nivelperiodoacademico)

    def total_contenidomicro(self):
        return self.detallemicrocurricularpac_set.filter(status=True).order_by('detallefuncionsustantivadocenciapac__asignatura')

    class Meta:
        verbose_name = u'Detalle Funcion Sustantiva Docencia Pac'
        verbose_name_plural = u'Detalles Funciones Sustantivas Docencia Pac'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.itinerariomencion = self.itinerariomencion.upper()
        super(DetalleFuncionSustantivaDocenciaPac, self).save(*args, **kwargs)

    def cantidad_asignaturas_planificadas_periodo(self, periodo):
        plan = self.planificacionparalelo_set.filter(periodo=periodo, status=True).first()
        return plan.paralelos if plan else 0


class DetalleMicrocurricularPac(ModeloBase):
    detallefuncionsustantivadocenciapac = models.ForeignKey(DetalleFuncionSustantivaDocenciaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Detalle Función Sustantiva Docencia Pac")
    contenidominimo = models.TextField(default='', blank=True, null=True, verbose_name=u"Contenidos mínimos")
    resultadoaprendizaje = models.TextField(default='', blank=True, null=True, verbose_name=u"Resultados de Aprendizaje")

    def __str__(self):
        return u"%s - %s" % (self.contenidominimo, self.resultadoaprendizaje)

    def save(self, *args, **kwargs):
        self.contenidominimo = self.contenidominimo.upper()
        self.resultadoaprendizaje = self.resultadoaprendizaje.upper()
        super(DetalleMicrocurricularPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Detalle Microcurricular Pac'
        verbose_name_plural = u'Detalles Microcurriculares Pac'
        ordering = ('id',)


class FuncionSustantivaInvestigacionPac(ModeloBase):
    programapac = models.ForeignKey(ProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'ProgramaPac')
    investigacion = models.TextField(default='', blank=True, null=True, verbose_name=u"Investigación")

    def __str__(self):
        return u"%s" % self.investigacion

    class Meta:
        verbose_name = u'Función Sustantiva Investigación Sociedad Pac'
        verbose_name_plural = u'Funciónes Sustantivas Investigación Sociedad Pac'
        ordering = ('investigacion',)


class FuncionSustantivaVinculacionSociedadPac(ModeloBase):
    programapac = models.ForeignKey(ProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'ProgramaPac')
    componentevinculacion = models.TextField(default='', blank=True, null=True, verbose_name=u"Componente de vinculación con la sociedad.")
    modelopractica = models.TextField(default='', blank=True, null=True, verbose_name=u"Modelo de prácticas pre profesionales de la carrera o prácticas profesionales del programa.")

    def __str__(self):
        return u"%s" % self.componentevinculacion

    class Meta:
        verbose_name = u'Función Sustantiva Vinculación Sociedad Pac'
        verbose_name_plural = u'Funciónes Sustantivas Vinculación Sociedad Pac'
        ordering = ('componentevinculacion',)

class TipoFormaPagoPac(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u'Tipo Forma Pago Pac'
        verbose_name_plural = u'Tipos de Forma Pago Pac'
        ordering = ('descripcion',)


class InfraestructuraEquipamientoInformacionPac(ModeloBase):
    programapac = models.ForeignKey(ProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'ProgramaPac')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u"Describa la plataforma tecnológica integral de infraestructura e infoestructura")
    aniosexperiencia = models.TextField(default='', blank=True, null=True, verbose_name=u"Años de experiencia")
    numeropublicacion = models.TextField(default='', blank=True, null=True, verbose_name=u"Cantidad de publicaciones")
    dominiotics = models.BooleanField(default=False, verbose_name=u"¿Dominio de TICS?")
    cargofunciondirector = models.TextField(default='', blank=True, null=True, verbose_name=u"Cargo / función")
    ciudaddirector = models.TextField(default='', blank=True, null=True, verbose_name=u"Ciudad (Sede Matriz/ Sede/ Extensiones)")
    horassemanaies = models.TextField(default='', blank=True, null=True, verbose_name=u"Horas de dedicación a la semana a la IES")
    tiporelacionlaboralies = models.TextField(default='', blank=True, null=True, verbose_name=u"Tipo de relación laboral o vinculación a la IES")
    valormatricula = models.FloatField(default=0, blank=True, null=True,  verbose_name=u'Valor Matricula')
    valorarancel = models.FloatField(default=0, blank=True, null=True,  verbose_name=u'Valor Arancel')
    valortotalprograma = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Valor total del programa')
    porcentajeminpagomatricula = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Porcentaje mín pago matrícula')
    maxnumcuota = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Máx número de cuotas')
    formapagopac = models.ManyToManyField(TipoFormaPagoPac)

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u'Infraestructura Equipamiento Información Pac'
        verbose_name_plural = u'Infraestructuras Equipamientos Información Pac'
        ordering = ('descripcion',)

    def save(self, *args, **kwargs):
        self.cargofunciondirector = self.cargofunciondirector.upper()
        self.ciudaddirector = self.ciudaddirector.upper()
        self.tiporelacionlaboralies = self.tiporelacionlaboralies.upper()
        super(InfraestructuraEquipamientoInformacionPac, self).save(*args, **kwargs)

    def perfilacademico(self):
        return self.perfilrequeridodirectorpac_set.filter(status=True)


class DetalleLaboratorioInfraestructuraPac(ModeloBase):
    infraestructuraequipamientopac = models.ForeignKey(InfraestructuraEquipamientoInformacionPac, blank=True, null=True, verbose_name=u"Detalle Laboratorio Infraestructura Pac", on_delete=models.CASCADE)
    estructurainstitucional = models.TextField(default='', blank=True, null=True, verbose_name=u"Estructura institucional Laboratorios y/o talleres")
    # nombrelaboratorio = models.ForeignKey(LaboratorioAcademia, blank=True, null=True, verbose_name=u"Nombre del laboratorio o taller Pac", on_delete=models.CASCADE)
    aulalaboratorio = models.ForeignKey(Aula, blank=True, null=True, verbose_name=u"Nombre del laboratorio o taller Pac", on_delete=models.CASCADE)
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u"Descripción")
    equipamiento = models.TextField(default='', blank=True, null=True, verbose_name=u"Equipamiento")
    metroscuadrado = models.FloatField(default=0, blank=True, null=True, verbose_name=u"Metros cuadrados del laboratorio o taller")
    puestotrabajo = models.TextField(default='', blank=True, null=True, verbose_name=u"Puesto de trabajo")

    def __str__(self):
        return u"%s: %s" % (self.infraestructuraequipamientopac.descripcion, self.estructurainstitucional)

    def save(self, *args, **kwargs):
        self.estructurainstitucional = self.estructurainstitucional.upper()
        self.descripcion = self.descripcion.upper()
        super(DetalleLaboratorioInfraestructuraPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Detalle Laboratorio Infraestructura Pac'
        verbose_name_plural = u'Detalles Laboratorios Infraestructura Pac'
        ordering = ('id',)


class DetalleBibliotecaInfraestructuraPac(ModeloBase):
    infraestructuraequipamientopac = models.ForeignKey(InfraestructuraEquipamientoInformacionPac, blank=True, null=True, verbose_name=u"Detalle Biblioteca Infraestructura Pac", on_delete=models.CASCADE)
    estructurainstitucional = models.TextField(default='', blank=True, null=True, verbose_name=u"Estructura institucional Biblioteca Específica")
    numerotitulo = models.TextField(default='', blank=True, null=True, verbose_name=u"Número de títulos ")
    titulo = models.TextField(default='', blank=True, null=True, verbose_name=u"Títulos")
    numerovolumen = models.TextField(default='', blank=True, null=True, verbose_name=u"Número de volúmenes")
    volumen = models.TextField(default='', blank=True, null=True, verbose_name=u"Volúmenes")
    numerobasedatos = models.TextField(default='', blank=True, null=True, verbose_name=u"Número de base de datos")
    basedatos = models.TextField(default='', blank=True, null=True, verbose_name=u"Base de datos")
    numerosuscripcion = models.TextField(default='', blank=True, null=True, verbose_name=u"Número de suscripciones")
    suscripcionrevista = models.TextField(default='', blank=True, null=True, verbose_name=u"Suscripciones a revistas")

    def __str__(self):
        return u"%s: %s" % (self.infraestructuraequipamientopac.descripcion, self.estructurainstitucional)

    def save(self, *args, **kwargs):
        self.estructurainstitucional = self.estructurainstitucional.upper()
        self.titulo = self.titulo.upper()
        self.volumen = self.volumen.upper()
        self.basedatos = self.basedatos.upper()
        self.suscripcionrevista = self.suscripcionrevista.upper()
        super(DetalleBibliotecaInfraestructuraPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Detalle Biblioteca Infraestructura Pac'
        verbose_name_plural = u'Detalles Bibliotecas Infraestructura Pac'
        ordering = ('id',)


class DetalleAulaInfraestructuraPac(ModeloBase):
    infraestructuraequipamientopac = models.ForeignKey(InfraestructuraEquipamientoInformacionPac, blank=True, null=True, verbose_name=u"Detalle Aula Infraestructura Pac", on_delete=models.CASCADE)
    estructurainstitucional = models.TextField(default='', blank=True, null=True, verbose_name=u"Estructura institucional Aula")
    numeroaula = models.TextField(default='', blank=True, null=True, verbose_name=u"Número de aulas")
    numeropuestotrabajoaula = models.TextField(default='', blank=True, null=True, verbose_name=u"Número de puestos de trabajo por aula")

    def __str__(self):
        return u"%s: %s" % (self.infraestructuraequipamientopac.descripcion, self.estructurainstitucional)

    def save(self, *args, **kwargs):
        self.estructurainstitucional = self.estructurainstitucional.upper()
        super(DetalleAulaInfraestructuraPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Detalle Aula Infraestructura Pac'
        verbose_name_plural = u'Detalles Aulas Infraestructura Pac'
        ordering = ('id',)


class TipoPersonalPac(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u"Descripcion")

    def __str__(self):
        return u"%s"%self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoPersonalPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Tipo de personal Pac'
        verbose_name_plural = u'Tipos de personal Pac'
        ordering = ('descripcion',)


class DetallePersonalAcademicoInfraestructuraPac(ModeloBase):
    infraestructuraequipamientopac = models.ForeignKey(InfraestructuraEquipamientoInformacionPac, blank=True, null=True, verbose_name=u"Detalle Personal Académico Infraestructura Pac", on_delete=models.CASCADE)
    aniosexperiencia = models.TextField(default='', blank=True, null=True, verbose_name=u"Años de experiencia")
    numeropublicacion = models.TextField(default='', blank=True, null=True, verbose_name=u"Cantidad de publicaciones")
    dominiotics = models.BooleanField(default=False, verbose_name=u"¿Dominio de TICS?")
    asignaturaimpartir = models.ForeignKey(DetalleFuncionSustantivaDocenciaPac, blank=True, null=True, verbose_name=u"Asignatura a impartir", on_delete=models.CASCADE)
    ciudadpersonalacademico = models.TextField(default='', blank=True, null=True, verbose_name=u"Ciudad (Sede Matriz/ Sede/ Extensiones)")
    horadedicacionies = models.IntegerField(choices=HORAS_DEDICACIÓN_IES, blank=True, null=True, default=0, verbose_name=u'Horas de dedicación a la IES')
    horadedicacionsemanal = models.TextField(default='', blank=True, null=True, verbose_name=u"Horas de dedicación semanal a la carrera/ programa")
    tiempodedicacioncarrera = models.IntegerField(choices=HORAS_DEDICACIÓN_PROGRAMA, blank=True, null=True, default=0, verbose_name=u"Tiempo de dedicación al carrera/ programa")
    tipopersonalcategoria = models.ForeignKey(TipoPersonalPac, blank=True, null=True, verbose_name=u"Tipo de personal académico/Categoría del docente", on_delete=models.CASCADE)
    # tipopersonalcategoria = models.IntegerField(choices=TIPO_PERSONAL_PAC, default=0, verbose_name=u'Tipo de personal académico/Categoría del docente')

    def __str__(self):
        return u"%s" % self.asignaturaimpartir

    def save(self, *args, **kwargs):
        self.ciudadpersonalacademico = self.ciudadpersonalacademico.upper()
        super(DetallePersonalAcademicoInfraestructuraPac, self).save(*args, **kwargs)

    def perfilacademico(self):
        return self.perfilrequeridopac_set.filter(status=True)

    class Meta:
        verbose_name = u'Detalle Personal Académico Infraestructura Pac'
        verbose_name_plural = u'Detalles Personal Académico Infraestructura Pac'
        ordering = ('id',)


class PerfilRequeridoDirectorPac(ModeloBase):
    infraestructuradirector = models.ForeignKey(InfraestructuraEquipamientoInformacionPac, blank=True, null=True, verbose_name=u"Infraestructura Pac", on_delete=models.CASCADE)
    titulacion = models.ForeignKey(CamposTitulosPostulacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Campos Títulos')

    def __str__(self):
        return u"%s"%self.titulacion

    class Meta:
        verbose_name = u'Perfil Requerido Director Pac'
        verbose_name_plural = u'Perfiles Requeridos Director Pac'
        ordering = ('id',)


class PerfilRequeridoPac(ModeloBase):
    personalacademico = models.ForeignKey(DetallePersonalAcademicoInfraestructuraPac, blank=True, null=True, verbose_name=u"Detalle Personal Académico Infraestructura Pac", on_delete=models.CASCADE)
    titulacion = models.ForeignKey(CamposTitulosPostulacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Campos Títulos')

    def __str__(self):
        return u"%s"%self.titulacion

    class Meta:
        verbose_name = u'Perfil Requerido Pac'
        verbose_name_plural = u'Perfiles Requeridos Pac'
        ordering = ('id',)


TIPOPRESUPUESTO_PAC = (
    (1, u"GASTOS CORRIENTES"),
    (2, u'INVERSIÓN'),
)


class PresupuestoPacColumna(ModeloBase):
    # infraestructuraequipamientopac = models.ForeignKey(InfraestructuraEquipamientoInformacionPac, blank=True, null=True, verbose_name=u"Infraestructura Pac", on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TIPOPRESUPUESTO_PAC, blank=True, null=True, default=0, verbose_name=u'Tipo de Presupuesto')
    descripcioncol = models.TextField(default='', blank=True, null=True, verbose_name=u"Descripción Presupuesto")
    orden = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Orden')

    def __str__(self):
        return u"%s"%self.descripcioncol

    def en_uso(self):
        return self.informacionfinancierapac_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.descripcioncol = self.descripcioncol.upper()
        super(PresupuestoPacColumna, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Presupuesto Pac Columna'
        verbose_name_plural = u'Presupuestos Pac Columnas'
        ordering = ('orden',)


class PresupuestoPacFila(ModeloBase):
    # infraestructuraequipamientopac = models.ForeignKey(InfraestructuraEquipamientoInformacionPac, blank=True, null=True, verbose_name=u"Infraestructura Pac", on_delete=models.CASCADE)
    descripcionfila = models.TextField(default='', blank=True, null=True, verbose_name=u"Descripción")
    orden = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Orden')

    def __str__(self):
        return u"%s"%self.descripcionfila

    def en_uso(self):
        return self.informacionfinancierapac_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.descripcionfila = self.descripcionfila.upper()
        super(PresupuestoPacFila, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Presupuesto Pac Fila'
        verbose_name_plural = u'Presupuestos Pac Filas'
        ordering = ('orden',)

    def filapresupuesto(self):
        return self.informacionfinancierapac_set.filter(status=True)


class InformacionfinancieraPac(ModeloBase):
    infraestructurapac = models.ForeignKey(InfraestructuraEquipamientoInformacionPac, blank=True, null=True, verbose_name=u"Infraestructura Pac", on_delete=models.CASCADE)
    presupuestoColumna = models.ForeignKey(PresupuestoPacColumna, blank=True, null=True, verbose_name=u"Presupuesto Pac Columna", on_delete=models.CASCADE)
    presupuestoFila = models.ForeignKey(PresupuestoPacFila, blank=True, null=True, verbose_name=u"Presupuesto Pac Columna", on_delete=models.CASCADE)
    valorpresupuesto = models.FloatField(default=0, blank=True, null=True,  verbose_name=u'Valor')

    def __str__(self):
        return u"%s - %s: %s"%(self.presupuestoColumna.descripcioncol,self.presupuestoFila.descripcionfila, self.valorpresupuesto )

    def save(self, *args, **kwargs):
        self.valorpresupuesto = self.valorpresupuesto.__round__(2)
        super(InformacionfinancieraPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Información financiera'
        verbose_name_plural = u'Informaciónes financieras'
        ordering = ('id',)


class AnexosPac(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=300, verbose_name=u"Descripcion Anexo")

    def __str__(self):
        return u"%s" % self.descripcion

    def en_uso(self):
        return self.detalleanexospac_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(AnexosPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Anexo Pac'
        verbose_name_plural = u'Anexos Pac'
        ordering = ('descripcion',)


class DetalleAnexosPac(ModeloBase):
    anexo = models.ForeignKey(AnexosPac, blank=True, null=True, verbose_name=u"Anexos Pac", on_delete=models.CASCADE)
    descripcion = models.CharField(default='', blank=True, null=True, max_length=300, verbose_name=u"Descripción Detalle Anexo")

    def __str__(self):
        return u"%s" % self.descripcion

    def en_uso(self):
        return self.archivoanexopac_set.filter(status=True)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(DetalleAnexosPac, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Detalle Anexo'
        verbose_name_plural = u'Detalles Anexos'
        ordering = ('descripcion',)


class ArchivoAnexoPac(ModeloBase):
    programapac = models.ForeignKey(ProgramaPac, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'ProgramaPac')
    anexo = models.ForeignKey(DetalleAnexosPac, blank=True, null=True, verbose_name=u"Anexos Pac", on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='archivoanexo/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo Anexo')

    def download_link(self):
        return self.archivo.url

    class Meta:
        verbose_name = u'Archivo Anexo'
        verbose_name_plural = u'Archivos Anexos'
        ordering = ('id', )


class ExtensionArchivo(ModeloBase):
    nombre = models.CharField(default='', max_length=30, verbose_name=u"Nombre")

    class Meta:
        verbose_name = u'Extensión archivo'
        verbose_name_plural = u'Extensiones de archivos'
        ordering = ('nombre',)


class FormatoArchivo(ModeloBase):
    nombre = models.CharField(default='',max_length=30, verbose_name=u"Nombre")
    extension = models.ManyToManyField(ExtensionArchivo)

    def __str__(self):
        return u'%s' % (self.nombre)

    class Meta:
        verbose_name = u'Formato de archivo'
        verbose_name_plural = u'Formatos de archivos'
        ordering = ('nombre', )
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre= self.nombre.upper()
        super(FormatoArchivo, self).save(*args, **kwargs)


class ConfiguracionRecurso(ModeloBase):
    tiporecurso = models.ForeignKey(TipoRecurso, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de recurso')
    carrera = models.ForeignKey('sga.Carrera', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Carrera')
    periodo = models.ForeignKey(Periodo, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Periodo')
    # tipoarchivo = models.IntegerField(choices=TIPO_ARCHIVO, default=0, verbose_name=u'Tipo de archivo')
    formato = models.ManyToManyField(FormatoArchivo)

    def __str__(self):
        return u'%s %s %s' % (self.periodo ,self.carrera,self.tiporecurso)

    class Meta:
        verbose_name = u'Configuración de recuso'
        verbose_name_plural = u'Configuración de recursos'
        ordering = ('tiporecurso', )

    def save(self, *args, **kwargs):
        super(ConfiguracionRecurso, self).save(*args, **kwargs)


class ListaVerificacion(ModeloBase):
    tiporecurso = models.ForeignKey(TipoRecurso,on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de recurso')
    descripcion = models.TextField(default='', verbose_name=u"Lista Verificacion")

    def __str__(self):
        return u'%s ' % (self.descripcion)

    class Meta:
        verbose_name = u'Lista de Verificacion'
        verbose_name_plural = u'Listas de Verificacion'
        ordering = ('descripcion', )

    def tiene_ingreso_tarea(self,id_recurso):
        if DetalleListaVerificacionTarea.objects.values('id').filter(status=True,tareasilabosemanal_id=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionTarea.objects.filter(status=True,tareasilabosemanal_id=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_foro(self,id_recurso):
        if DetalleListaVerificacionForo.objects.values('id').filter(status=True,forosilabosemanal_id=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionForo.objects.filter(status=True,forosilabosemanal_id=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_test(self,id_recurso):
        if DetalleListaVerificacionTest.objects.values('id').filter(status=True,testsilabosemanal_id=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionTest.objects.filter(status=True,testsilabosemanal_id=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_diapositiva(self,id_recurso):
        if DetalleListaVerificacionDiapositiva.objects.values('id').filter(status=True,diapositivasilabosemanal_id=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionDiapositiva.objects.filter(status=True,diapositivasilabosemanal_id=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_guia_estudiante(self,id_recurso):
        if DetalleListaVerificacionGuiaEstudiante.objects.values('id').filter(status=True,guiaestudiantesilabosemanal_id=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionGuiaEstudiante.objects.filter(status=True,guiaestudiantesilabosemanal_id=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_guia_docente(self,id_recurso):
        if DetalleListaVerificacionGuiaDocente.objects.values('id').filter(status=True,guiadocentesilabosemanal_id=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionGuiaDocente.objects.filter(status=True,guiadocentesilabosemanal_id=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_material_adicional(self,id_recurso):
        if DetalleListaVerificacionMaterialAdicional.objects.values('id').filter(status=True,materialadicionalsilabosemanal_id=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionMaterialAdicional.objects.filter(status=True,materialadicionalsilabosemanal_id=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_tarea_practica(self,id_recurso):
        if DetalleListaVerificacionTareaPractica.objects.values('id').filter(status=True,tareapracticasilabosemanal=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionTareaPractica.objects.filter(status=True,tareapracticasilabosemanal=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_compendio(self,id_recurso):
        if DetalleListaVerificacionCompendio.objects.values('id').filter(status=True,compendiosilabosemanal=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionCompendio.objects.filter(status=True,compendiosilabosemanal=id_recurso,listaverificacion=self)[0]
        return None

    def tiene_ingreso_video_magistral(self,id_recurso):
        if DetalleListaVerificacionVideoMagistral.objects.values('id').filter(status=True,videomagistralsilabosemanal=id_recurso,listaverificacion=self).exists():
            return DetalleListaVerificacionVideoMagistral.objects.filter(status=True,videomagistralsilabosemanal=id_recurso,listaverificacion=self)[0]
        return None

    def save(self, *args, **kwargs):
        self.descripcion= self.descripcion.upper()
        super(ListaVerificacion, self).save(*args, **kwargs)


class DetalleListaVerificacionTarea(ModeloBase):
    tareasilabosemanal = models.ForeignKey(TareaSilaboSemanal,  on_delete=models.CASCADE,blank=True, null=True, verbose_name='tarea silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion'
        verbose_name_plural = u'Detalle Listas de Verificacion'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionTarea, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionTarea(ModeloBase):
    historialaprobaciontarea = models.ForeignKey(HistorialaprobacionTarea, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion tarea')
    tareasilabosemanal = models.ForeignKey(TareaSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='tarea silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Tarea'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Tarea'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionTarea, self).save(*args, **kwargs)


class DetalleListaVerificacionForo(ModeloBase):
    forosilabosemanal = models.ForeignKey(ForoSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='foro silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Foro'
        verbose_name_plural = u'Detalle Listas de Verificacion Foro'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionForo, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionForo(ModeloBase):
    historialaprobacionforo = models.ForeignKey(HistorialaprobacionForo, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion foro')
    forosilabosemanal = models.ForeignKey(ForoSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='foro silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Foro'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Foro'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionForo, self).save(*args, **kwargs)


class DetalleListaVerificacionCompendio(ModeloBase):
    compendiosilabosemanal = models.ForeignKey(CompendioSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='compendio silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, blank=True,  on_delete=models.CASCADE, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Compendio'
        verbose_name_plural = u'Detalle Listas de Verificacion Compendio'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionCompendio, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionCompendio(ModeloBase):
    historialaprobacioncompendio = models.ForeignKey(HistorialaprobacionCompendio, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion compendio')
    compendiosilabosemanal = models.ForeignKey(CompendioSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='compendio silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Compendio'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Compendio'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionCompendio, self).save(*args, **kwargs)


class DetalleListaVerificacionTest(ModeloBase):
    testsilabosemanal = models.ForeignKey(TestSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='test silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Test'
        verbose_name_plural = u'Detalle Listas de Verificacion Test'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionTest, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionTest(ModeloBase):
    historialaprobaciontest = models.ForeignKey(HistorialaprobacionTest, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion test')
    testsilabosemanal = models.ForeignKey(TestSilaboSemanal, blank=True, on_delete=models.CASCADE, null=True, verbose_name='test silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Test'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Test'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionTest, self).save(*args, **kwargs)


class DetalleListaVerificacionDiapositiva(ModeloBase):
    diapositivasilabosemanal = models.ForeignKey(DiapositivaSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='diapositiva silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Diapositiva'
        verbose_name_plural = u'Detalle Listas de Verificacion Diapositiva'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionDiapositiva, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionDiapositiva(ModeloBase):
    historialaprobaciondiapositiva = models.ForeignKey(HistorialaprobacionDiapositiva, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion diapositiva')
    diapositivasilabosemanal = models.ForeignKey(DiapositivaSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='diapositiva silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Diapositiva'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Diapositiva'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionDiapositiva, self).save(*args, **kwargs)


class DetalleListaVerificacionGuiaEstudiante(ModeloBase):
    guiaestudiantesilabosemanal = models.ForeignKey(GuiaEstudianteSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='guía estudiante silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Guia Estudiante'
        verbose_name_plural = u'Detalle Listas de Verificacion Guia Estudiante'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionGuiaEstudiante, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionGuiaEstudiante(ModeloBase):
    historialaprobacionguiaestudiante = models.ForeignKey(HistorialaprobacionGuiaEstudiante, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion guia estudiante')
    guiaestudiantesilabosemanal = models.ForeignKey(GuiaEstudianteSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='guía estudiante silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Guia Estudiante'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Guia Estudiante'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionGuiaEstudiante, self).save(*args, **kwargs)


class DetalleListaVerificacionGuiaDocente(ModeloBase):
    guiadocentesilabosemanal = models.ForeignKey(GuiaDocenteSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='guía docente silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Guia Docente'
        verbose_name_plural = u'Detalle Listas de Verificacion Guia Docente'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionGuiaDocente, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionGuiaDocente(ModeloBase):
    historialaprobacionguiadocente = models.ForeignKey(HistorialaprobacionGuiaDocente, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion guia docente')
    guiadocentesilabosemanal = models.ForeignKey(GuiaDocenteSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='guía docente silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Guia Docente'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Guia Docente'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionGuiaDocente, self).save(*args, **kwargs)


class DetalleListaVerificacionMaterialAdicional(ModeloBase):
    materialadicionalsilabosemanal = models.ForeignKey(MaterialAdicionalSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='material adicional silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Material Adicional'
        verbose_name_plural = u'Detalle Listas de Verificacion Material Adicional'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionMaterialAdicional, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionMaterialAdicional(ModeloBase):
    historialaprobacionmaterial = models.ForeignKey(HistorialaprobacionMaterial, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion material adicional')
    materialadicionalsilabosemanal = models.ForeignKey(MaterialAdicionalSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='material adicional silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Material Adicional'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Material Adicional'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionMaterialAdicional, self).save(*args, **kwargs)


class DetalleListaVerificacionTareaPractica(ModeloBase):
    tareapracticasilabosemanal = models.ForeignKey(TareaPracticaSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='tarea practica silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Tarea Práctica'
        verbose_name_plural = u'Detalle Listas de Verificacion Tarea Práctica'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionTareaPractica, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionTareaPractica(ModeloBase):
    historialaprobaciontareapractica = models.ForeignKey(HistorialaprobacionTareaPractica, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion tarea practica ')
    tareapracticasilabosemanal = models.ForeignKey(TareaPracticaSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='tarea practica silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % (self.observacion)

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Tarea Practica'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Tarea Practica'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionTareaPractica, self).save(*args, **kwargs)


class DetalleListaVerificacionVideoMagistral(ModeloBase):
    videomagistralsilabosemanal = models.ForeignKey(VideoMagistralSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='video magistral silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    cumple = models.BooleanField(default=False, verbose_name=u'Cumple con la lista de verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s' % self.observacion

    class Meta:
        verbose_name = u'Detalle Lista de Verificacion Video Magistral'
        verbose_name_plural = u'Detalle Listas de Verificacion Video Magistral'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(DetalleListaVerificacionVideoMagistral, self).save(*args, **kwargs)


class HistorialDetalleListaVerificacionVideoMagistral(ModeloBase):
    historialaprobacionvideomagistral = models.ForeignKey(HistorialaprobacionVideoMagistral, on_delete=models.CASCADE, blank=True, null=True, verbose_name='historial detalle lista verificacion video magistral')
    videomagistralsilabosemanal = models.ForeignKey(VideoMagistralSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name='video magistral silabo semanal')
    listaverificacion = models.ForeignKey(ListaVerificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Lista de Verificación')
    observacion = models.TextField(default='', verbose_name=u"Observación")

    def __str__(self):
        return u'%s ' % self.observacion

    class Meta:
        verbose_name = u' Historial Detalle Lista de Verificacion Video Magistral'
        verbose_name_plural = u'Historial Detalle Listas de Verificacion Video Magistral'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(HistorialDetalleListaVerificacionVideoMagistral, self).save(*args, **kwargs)


class TipoInconvenienteClaseDiferido(ModeloBase):
    nombre = models.CharField(max_length=500, verbose_name=u'Nombre del tipo de incoveniente')
    activo = models.BooleanField(default=True, verbose_name=u"Activo?")

    def __str__(self):
        return f"{self.nombre}"

    def mis_motivos(self):
        return self.motivotipoinconvenienteclasediferido_set.filter(status=True)

    def tiene_motivos(self):
        return self.mis_motivos().exists()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        super(TipoInconvenienteClaseDiferido, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Tipo de incoveniente de clases por diferido'
        verbose_name_plural = u'Tipos de incovenientes de clases por diferido'
        ordering = ('nombre', )


class MotivoTipoInconvenienteClaseDiferido(ModeloBase):
    tipo = models.ForeignKey(TipoInconvenienteClaseDiferido, on_delete=models.CASCADE, verbose_name=u'Tipo de incoveniente')
    nombre = models.CharField(max_length=500, verbose_name=u'Nombre del motivo')
    activo = models.BooleanField(default=True, verbose_name=u"Activo?")
    es_otro = models.BooleanField(default=False, verbose_name=u"Es otro?")
    obligar_archivo = models.BooleanField(default=False, verbose_name=u"Obligar subir archivo?")
    aprobar_direccion = models.BooleanField(default=False, verbose_name=u"Aprobar dirección?")

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            if q is None or q == '':
                return eval('MotivoTipoInconvenienteClaseDiferido.objects.filter(%s).distinct()[:%s]' % (extra, limit))
            else:
                return eval('MotivoTipoInconvenienteClaseDiferido.objects.filter(Q(nombre__contains="%s")).filter(%s).distinct()[:%s]' % (q, extra, limit))
        if q is None or q == '':
            return MotivoTipoInconvenienteClaseDiferido.objects.all().distinct()[:limit]
        else:
            return MotivoTipoInconvenienteClaseDiferido.objects.filter(Q(nombre__contains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return self.__str__()

    def __str__(self):
        return f"{self.nombre}"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        super(MotivoTipoInconvenienteClaseDiferido, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Motivo del tipo de incoveniente de clases por diferido'
        verbose_name_plural = u'Motivos del tipo de incoveniente de clases por diferido'
        ordering = ('tipo', 'nombre', )


class ProcesoSolicitudClaseDiferido(ModeloBase):
    nombre = models.CharField(max_length=500, verbose_name=u'Nombre del proceso')
    version = models.IntegerField(default=1, verbose_name=u'Versión')
    num_dias = models.IntegerField(default=200, verbose_name=u"Número de días que puede solicitar")
    activo = models.BooleanField(default=True, verbose_name=u"Activo?")
    tipos = models.ManyToManyField(TipoInconvenienteClaseDiferido)

    def __str__(self):
        return f"{self.nombre} - V.{self.id}"

    def mis_tipos(self):
        return self.tipos.all()

    def tiene_tipos(self):
        return self.mis_tipos().values("id").exists()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        if self.num_dias <= 0:
            raise NameError(u"Número de días debe ser mayor a cero")
        if not self.id:
            if ProcesoSolicitudClaseDiferido.objects.values("id").filter(nombre=self.nombre, version=self.version).exists():
                raise NameError(u"Nombre del proceso y versión ya existe")
        else:
            if ProcesoSolicitudClaseDiferido.objects.values("id").filter(nombre=self.nombre, version=self.version).exclude(pk=self.id).exists():
                raise NameError(u"Nombre del proceso y versión ya existe")
        super(ProcesoSolicitudClaseDiferido, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Proceso de solicitud por incoveniente de clases'
        verbose_name_plural = u'Procesos de solicitud por incoveniente de clases'
        ordering = ('nombre', 'version',)
        unique_together = ('nombre', 'version',)


TIPO_PERIODO_MODALIDAD_CHOICES = (
    (1, "PRESENCIAL"),
    (2, "VIRTUAL"),
    (3, "HIBRIDA"),
)


class PeriodoAcademia(ModeloBase):
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE,  blank=True, null=True, verbose_name=u'Periodo')
    fecha_limite_horario_tutoria = models.DateField(verbose_name=u'Fecha limite ingreso horario tutoria docente', blank=True, null=True)
    fecha_fin_horario_tutoria = models.DateField(verbose_name=u'Fecha limite de tutorias docentes', blank=True, null=True)
    fecha_maxima_solicitud=models.DateField(verbose_name=u'Fecha maxima para generar solicitud con respecto a tutorias academica por parte del estudiante', blank=True, null=True)
    version_cumplimiento_recurso = models.IntegerField(default=2, blank=True, null=True, verbose_name=u'Para version de informes de cumplimiento de recurso silabos en aprobar silabo')
    cierra_materia = models.BooleanField(default=True, verbose_name=u"En ese periodo es obligatorio cerrar las materias ofertadas")
    periodos_relacionados = models.TextField(default='', blank=True, null=True, verbose_name=u'Periodos que llevan relación en tema de actividades del docente')
    tipo_modalidad = models.IntegerField(default=1, blank=True, null=True, choices=TIPO_PERIODO_MODALIDAD_CHOICES, verbose_name=u'Tipo de modalidad del periodo')
    utiliza_asistencia_ws = models.BooleanField(default=False, verbose_name=u"Utiliza asistencia con websocket")
    utiliza_asistencia_redis = models.BooleanField(default=False, verbose_name=u"Utiliza asistencia con redis")
    puede_cerrar_clase = models.BooleanField(default=False, verbose_name=u"Puede cerrar clase")
    puede_eliminar_clase = models.BooleanField(default=False, verbose_name=u"Puede eliminar clase")
    puede_editar_contenido_academico_clase = models.BooleanField(default=False, verbose_name=u"Puede editar contenido academico de clase")
    puede_cambiar_asistencia_clase = models.BooleanField(default=False, verbose_name=u"Puede cambiar asistencia en clase cerrada")
    num_dias_cambiar_asistencia_clase = models.IntegerField(default=0, null=True, blank=True, verbose_name=u"Número de días que puede cambiar asistencia en clase cerrada")
    valida_asistencia_pago = models.BooleanField(default=False, verbose_name=u"Validar asistencia con pago")
    valida_clases_horario_estricto = models.BooleanField(default=True, verbose_name=u"Validar clases con horario escricto")
    min_clases_apertura_antes_pro = models.IntegerField(default=15, blank=True, null=True, verbose_name=u'Minutos antes de apertura para el profesor')
    min_clases_apertura_despues_pro = models.IntegerField(default=45, blank=True, null=True, verbose_name=u'Minutos despues de apertura para el profesor')
    min_clases_apertura_antes_alu = models.IntegerField(default=5, blank=True, null=True, verbose_name=u'Minutos antes de apertura para el alumno')
    min_clases_apertura_despues_alu = models.IntegerField(default=15, blank=True, null=True, verbose_name=u'Minutos despues de apertura para el alumno')
    puede_solicitar_clase_diferido_pro = models.BooleanField(default=True, verbose_name=u"Puede solicitar registros de asistencias")
    proceso_solicitud_clase_diferido_pro = models.ForeignKey(ProcesoSolicitudClaseDiferido,default=1, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Proceso de solicitud de clases por diferido profesor")
    fecha_limite_ingreso_act = models.DateField(verbose_name=u'Fecha limite ingreso actividades docente', blank=True, null=True)
    valida_asistencia_in_home = models.BooleanField(default=False, verbose_name=u"Validar IP dentro del CAMPUS UNIVERSITARIO")
    versioninstrumento = models.IntegerField(default=2, blank=True, null=True, verbose_name=u'version 1 trabajo con docencia,inv,gest, version 2 doc,inv,ges,vin')
    nuevocalculoeva = models.BooleanField(default=False, verbose_name=u"Calcular ponderaciones sin Evaluacion")
    # tipos_solicitud_asistencias_pro = models.TextField(default='1,2,3,4', blank=True, null=True, verbose_name=u'Tipos de solicitudes de registros de asistencias')
    # num_dias_solicitar_asistencias_pro = models.IntegerField(default=200, null=True, blank=True, verbose_name=u"Número de días que puede solicitar asistencias")
    # puede_gestionar_solicitud_asistencias_pro = models.BooleanField(default=True, verbose_name=u"Puede gestionar solicitud de asistencias")

    def __str__(self):
        if not self.fecha_limite_horario_tutoria:
            return u'%s' % self.periodo
        else:
            return u'%s %s' % (self.periodo, self.fecha_limite_horario_tutoria)

    class Meta:
        verbose_name = u'Periodo academia'
        verbose_name_plural = u'Periodos academia'
        ordering = ('periodo', )
        unique_together = ('periodo',)

    def puede_enviar_solicitud(self):
        if self.fecha_maxima_solicitud:
            return self.fecha_maxima_solicitud>=datetime.now().date()
        return True

    def es_presencial(self):
        return self.tipo_modalidad == 1

    def es_virtual(self):
        return self.tipo_modalidad == 2

    def es_hibrida(self):
        return self.tipo_modalidad == 3

    def puede_registrar_asistencia(self, fecha_clase):
        d = datetime.now().date()
        return d <= fecha_clase + timedelta(days=self.num_dias_cambiar_asistencia_clase)

    def actualizar_fechas_tutorias(self):
        HorarioTutoriaAcademica.objects.filter(periodo=self.periodo, status=True).update(fecha_fin_horario_tutoria=self.fecha_fin_horario_tutoria)
        # for horario in horarios:
        #     if horario.fecha_fin_horario_tutoria is None:
        #         horario.fecha_fin_horario_tutoria = self.fecha_fin_horario_tutoria
        #         horario.save()
        #     elif horario.fecha_fin_horario_tutoria <= self.fecha_fin_horario_tutoria

    def tipos_incovenientes_por_diferido(self):
        # if self.puede_solicitar_asistencias_pro and self.tipos_solicitud_asistencias_pro:
        #     tipos = []
        #     for tipo in self.tipos_solicitud_asistencias_pro.strip().split(','):
        #         tipos.append([int(tipo), TIPO_SOLICITUDINCONVENIENTE[int(tipo)-1][1]])
        #     return tuple(tipos)
        # return None
        if self.puede_solicitar_clase_diferido_pro and self.proceso_solicitud_clase_diferido_pro.tiene_tipos():
            return self.proceso_solicitud_clase_diferido_pro.mis_tipos()
        return None

    def save(self, *args, **kwargs):
        super(PeriodoAcademia, self).save(*args, **kwargs)


class AsistenciaLeccionObservacion(ModeloBase):
    asistencia = models.ForeignKey(AsistenciaLeccion, on_delete=models.CASCADE, related_name='+', verbose_name=u'Asistencia lección')
    observacion = models.TextField(verbose_name=u'Observación')
    fecha = models.DateField(verbose_name=u'Fecha')
    hora = models.TimeField(verbose_name=u'Hora')

    def __str__(self):
        return f"{self.asistencia.materiaasignada.matricula.inscripcion.persona.nombre_completo_inverso()}-{self.asistencia.materiaasignada.materia.__str__()}-{self.fecha.strftime('%Y-%m-%d')} {self.hora.strftime('%H:%m')}"

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.strip()
        super(AsistenciaLeccionObservacion, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Observación de asistencia lección'
        verbose_name_plural = u'Observaciones de asistencia lección'
        ordering = ('fecha', 'hora')


class LogIngresoAsistenciaLeccion(ModeloBase):
    asistencia = models.ForeignKey(AsistenciaLeccion, on_delete=models.CASCADE, related_name='+', verbose_name=u'Asistencia lección')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha')
    hora = models.TimeField(blank=True, null=True, verbose_name=u'Hora')
    ip_private = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name=u"IP Privada")
    ip_public = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name=u"IP Publica")
    browser = models.CharField(default='', max_length=100, blank=True, null=True, db_index=True, verbose_name=u"Browser")
    ops = models.CharField(default='', max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Sistema Operativo")
    screen_size = models.CharField(default='', max_length=50, blank=True, null=True, db_index=True, verbose_name=u"Tamaño de Pantalla")

    def __str__(self):
        return f"{self.asistencia.materiaasignada.matricula.inscripcion.persona.nombre_completo_inverso()}-{self.asistencia.materiaasignada.materia.__str__()}-{self.fecha.strftime('%Y-%m-%d')} {self.hora.strftime('%H:%m')}"

    def save(self, *args, **kwargs):
        self.actualizar()
        super(LogIngresoAsistenciaLeccion, self).save(*args, **kwargs)

    def actualizar(self, request=None):
        asistencia = self.asistencia
        logs = LogIngresoAsistenciaLeccion.objects.filter(asistencia=asistencia)
        if logs.values("id").exists():
            ultimo = logs.last()
            asistencia.virtual_fecha = ultimo.fecha
            asistencia.virtual_hora = ultimo.hora
            asistencia.ip_private = ultimo.ip_private
            asistencia.ip_public = ultimo.ip_public
            asistencia.browser = ultimo.browser
            asistencia.ops = ultimo.ops
            asistencia.screen_size = ultimo.screen_size
            if request:
                asistencia.save(request)
            else:
                asistencia.save(usuario_id=self.usuario_creacion_id)

    class Meta:
        verbose_name = u'Registro de ingreso de asistencia'
        verbose_name_plural = u'Registros de ingresos de asistencia'
        ordering = ('fecha', 'hora')


STATES = (
    (0, 'PENDIENTE'),
    (1, 'ACEPTADO'),
    (2, 'RECHAZADO')
)


class DetalleSolicitudHorarioTutoria(ModeloBase):
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo Academia', on_delete=models.PROTECT)
    profesor = models.ForeignKey('sga.Profesor', blank=True, null=True, verbose_name=u'Profesor', on_delete=models.PROTECT)
    director = models.ForeignKey('sga.CoordinadorCarrera', blank=True, null=True, verbose_name=u'Coordinador de carrera', on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha autorizada', blank=True, null=True)
    observacion = models.TextField(default="", blank=True, null=True, verbose_name=u'Motivo de docente')
    repuestadirector = models.TextField(default="", blank=True, null=True, verbose_name=u'Observacion de director de carrera')
    estadosolicitud = models.IntegerField(choices=STATES, default=0, verbose_name=u'Estado solicitud')

    def __str__(self):
        return u'%s %s ' % (self.periodo, self.fecha)

    class Meta:
        verbose_name = u'Detalle Solicitud Horario tutorias'
        verbose_name_plural = u'Detalle Solicitudes de horario tutorias academicas'
        ordering = ('periodo', )

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        self.repuestadirector = self.repuestadirector.upper()
        super(DetalleSolicitudHorarioTutoria, self).save(*args, **kwargs)


TIPO_RESPONSABLE = (
    (1, 'DOCENTE'),
    (2, 'EXPERTO')
)


class ResponsableActaAdmision(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    tipoprofesor = models.ForeignKey('sga.TipoProfesor', blank=True, null=True, verbose_name=u'Tipo Profesor',
                                     on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TIPO_RESPONSABLE, blank=True, null=True, verbose_name=u'Tipo')
    cargo = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u"Cargo")
    firmadigital = models.BooleanField(default=True, verbose_name=u"Firma Digital")

    def __str__(self):
        cadena = ''
        if self.tipo == 1:
            cadena = u'%s'%(self.tipoprofesor)
        else:
            cadena = u'%s  - %s'%(self.persona, self.cargo)
        return u'%s (%s)' % (cadena, self.get_tipo_display())

    def esta_en_uso(self):
        return self.asignaturaactaadmision_set.values('id').exists()

    def save(self, *args, **kwargs):
        self.cargo = self.cargo.upper()
        super(ResponsableActaAdmision, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Responsable Acta Admisión'
        verbose_name_plural = u'Responsables Actas Admisión'
        ordering = ('fecha_creacion', )


class AsignaturaActaAdmision(ModeloBase):
    asignatura = models.ForeignKey('sga.Asignatura', blank=True, null=True, verbose_name=u'Asignatura', on_delete=models.CASCADE)
    responsables = models.ManyToManyField(ResponsableActaAdmision, verbose_name=u'Responsables', blank=True)

    def __str__(self):
        # datarespo = ''# str([o.__str__() for o in self.responsables.all()])
        # for o in self.responsables.all():
        #     datarespo += u' %s'%o.__str__()
        return u'%s' % (self.asignatura)

    class Meta:
        verbose_name = u'Asignatura Acta Admisión'
        verbose_name_plural = u'Asignaturas Actas Admisión'
        ordering = ('fecha_creacion',)


class PeriodoActaAdmision(ModeloBase):
    periodo = models.ForeignKey('sga.Periodo', blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    responsablesasignaturas = models.ManyToManyField(AsignaturaActaAdmision, verbose_name=u'Responsables Asignatura', blank=True)

    def __str__(self):
        return u'%s' % self.periodo


    def  get_responsables_asignatura(self, asignatura):
        data = self.responsablesasignaturas.filter(asignatura=asignatura).first()
        return data.responsables.all() if data else []

    class Meta:
        verbose_name = u'Periodo Acta Admisión'
        verbose_name_plural = u'Periodos Actas Admisión'
        ordering = ('fecha_creacion',)


class RequisitoIngresoUnidadIntegracionCurricular(ModeloBase):
    from bd.models import FuncionRequisitoIngresoUnidadIntegracionCurricular
    asignaturamalla = models.ForeignKey(AsignaturaMalla, null=True, on_delete=models.CASCADE, verbose_name=u'Asignatura Malla')
    requisito = models.ForeignKey(FuncionRequisitoIngresoUnidadIntegracionCurricular, on_delete=models.CASCADE, verbose_name=u'Requisito')
    orden = models.IntegerField(default=1, verbose_name=u'Orden')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    obligatorio = models.BooleanField(default=True, verbose_name=u'Inscripción')
    enlineamatriculacion = models.BooleanField(default=False, verbose_name=u'Valida en la matriculación en linea')

    def __str__(self):
        return u'%s: %s' % (self.orden, self.requisito.nombre)

    def run(self, eInscripcion):
        from inno.funciones import estar_matriculado_todas_asignaturas_ultimo_periodo_academico, \
            asignaturas_aprobadas_primero_penultimo_nivel, ficha_estudiantil_actualizada_completa, \
            haber_aprobado_modulos_ingles, haber_aprobado_modulos_computacion, \
            haber_cumplido_horas_creditos_practicas_preprofesionales, haber_cumplido_horas_creditos_vinculacion, \
            no_adeudar_institucion, tiene_certificacion_segunda_lengua_sin_aprobar_director_carrera, \
            tiene_certificacion_segunda_lengua_aprobado_director_carrera, asignaturas_aprobadas_primero_septimo_nivel, \
            asignaturas_aprobadas_primero_ultimo_nivel, tener_certificado_inglesb2
        funcion = self.requisito.nombre_funcion()
        if self.requisito.funcion in (6, 7):
            return eval(u'%s(%s, %s)' % (funcion, eInscripcion, self.asignaturamalla.nivelmalla_id))
        return eval(u'%s(%s)' % (funcion, eInscripcion))

    class Meta:
        verbose_name = u'Requisito Ingreso Unidad Integracion Curricular'
        verbose_name_plural = u'Requisitos Ingreso Unidad Integracion Curricular'
        ordering = ('orden',)
        unique_together = ('asignaturamalla', 'requisito', )


class RequisitoMateriaUnidadIntegracionCurricular(ModeloBase):
    from bd.models import FuncionRequisitoIngresoUnidadIntegracionCurricular
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, verbose_name=u'Materia')
    requisito = models.ForeignKey(FuncionRequisitoIngresoUnidadIntegracionCurricular, on_delete=models.CASCADE, verbose_name=u'Requisito')
    orden = models.IntegerField(default=1, verbose_name=u'Orden')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    obligatorio = models.BooleanField(default=True, verbose_name=u'Obligatorio')
    enlineamatriculacion = models.BooleanField(default=False, verbose_name=u'Valida en la matriculación en linea')
    inscripcion = models.BooleanField(default=False, verbose_name=u'Para inscripción')
    titulacion = models.BooleanField(default=False, verbose_name=u'Para titulación')

    def __str__(self):
        return u'%s: %s' % (self.orden, self.requisito.nombre)

    def run(self, eInscripcion):
        from inno.funciones import estar_matriculado_todas_asignaturas_ultimo_periodo_academico, \
            asignaturas_aprobadas_primero_penultimo_nivel, ficha_estudiantil_actualizada_completa, \
            haber_aprobado_modulos_ingles, haber_aprobado_modulos_computacion, \
            haber_cumplido_horas_creditos_practicas_preprofesionales, haber_cumplido_horas_creditos_vinculacion, \
            no_adeudar_institucion, tiene_certificacion_segunda_lengua_sin_aprobar_director_carrera, \
            tiene_certificacion_segunda_lengua_aprobado_director_carrera, asignaturas_aprobadas_primero_ultimo_nivel, \
            asignaturas_aprobadas_primero_septimo_nivel, tener_certificado_inglesb2
        funcion = self.requisito.nombre_funcion()
        if self.requisito.funcion in (6, 7):
            return eval(u'%s(%s, %s)' % (funcion, eInscripcion, self.materia.asignaturamalla.nivelmalla_id))
        return eval(u'%s(%s)' % (funcion, eInscripcion))

    def detarequisitos(self, eInscripcion):
        from inno.funciones import detalle_aprobado_modulos_ingles, detalle_aprobado_modulos_computacion, \
            detalle_aprobadas_primero_penultimo_nivel, detalle_cumplido_horas_creditos_practicas_preprofesionales, \
            detalle_cumplido_horas_creditos_vinculacion, detalle_ficha_estudiantil_actualizada_completa, \
            detalle_aprobadas_primero_ultimo_nivel
        funcion = self.requisito.nombre_funcionrequisito()
        if not funcion:
            return None
        else:
            return eval(u'%s(%s)' % (funcion, eInscripcion))

    class Meta:
        verbose_name = u'Requisito de titulación en Unidad Integracion Curricular'
        verbose_name_plural = u'Requisitos de titulación en Unidad Integracion Curricular'
        ordering = ('orden',)
        unique_together = ('materia', 'requisito', )


class ConfiguracionCalculoMatricula(ModeloBase):
    presupuesto = models.FloatField(default=0, blank=True, null=True, verbose_name=u'presupuesto')
    tipocalculo = models.IntegerField(choices=TIPO_CALCULO_MATRICULA, default=1, verbose_name=u'porcentaje de calculo')
    totalestudiante = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de estudiantes por año', help_text='Este valor debe ser calculado')
    anio = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Año')
    semestre_anio = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Semestre por año')
    archivo = models.FileField(upload_to='holacalculosvct/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de calculos')

    def __str__(self):
        return u'%s - %s - %s - %s -%s' % (self.presupuesto,self.get_tipocalculo_display(),self.totalestudiante,self.anio, self.semestre_anio)

    class Meta:
        verbose_name = u'Configuracion calculo matricula'
        verbose_name_plural = u'Configuraciones calculo matricula'
        ordering = ('anio',)


class PeriodoMalla(ModeloBase):
    tipocalculo = models.IntegerField(choices=TIPO_CALCULO_MATRICULA, default=1, verbose_name=u'porcentaje de calculo')
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    malla = models.ForeignKey('sga.Malla', verbose_name=u'Malla', on_delete=models.CASCADE)
    configuracion = models.ForeignKey(ConfiguracionCalculoMatricula, blank=True, null=True, verbose_name=u'Configuración de calculo', on_delete=models.CASCADE)
    vct = models.DecimalField(max_digits=30, default=0, decimal_places=2, verbose_name=u"VCT")

    def __str__(self):
        return u'%s - %s - %s - %s' % (self.get_tipocalculo_display(), self.periodo, self.malla, self.configuracion)

    class Meta:
        verbose_name = u'Periodo malla calculo matricula'
        verbose_name_plural = u'Periodos malla calculo matricula'
        ordering = ('periodo',)


class DetallePeriodoMalla(ModeloBase):
    periodomalla = models.ForeignKey(PeriodoMalla, verbose_name=u'Periodo malla', on_delete=models.CASCADE)
    gruposocioeconomico = models.ForeignKey('socioecon.GrupoSocioEconomico', verbose_name=u'Grupo Socio Economico', on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=30, default=0, decimal_places=2, verbose_name=u"Valor credito")

    def __str__(self):
        return u'%s - %s - %s' % (self.periodomalla, self.gruposocioeconomico, self.valor)

    class Meta:
        verbose_name = u'Detalle Periodo malla calculo matricula'
        verbose_name_plural = u'Detalles Periodos malla calculo matricula'
        ordering = ('gruposocioeconomico',)


CHOICES_TIPO_ACTIVIDADES = (
    (1, 'TEST'),
    (2, 'EXPOSICIÓN'),
    (3, 'TALLER'),
    (4, 'TAREA'),
    (5, 'TRABAJO DE INVESTIGACIÓN'),
    (6, 'ANÁLISIS DE CASOS'),
    (7, 'FORO'),
    (8, 'TRABAJO PRÁCTICO EXPERIMENTAL'),
)

CHOICES_TIPO_ACTIVIDADES_COLOURS = (
    (1, u'TEST', '#89C0B7', '#000000'),
    (2, u'EXPOSICIÓN', '#6F91B5', '#000000'),
    (3, u'TALLER', '#F2CACB', '#000000'),
    (4, u'TAREA', '#FDBB75', '#000000'),
    (5, u'TRABAJO DE INVESTIGACIÓN', "#EF8F88", '#000000'),
    (6, u'ANÁLISIS DE CASOS', '#B7E1E4', '#000000'),
    (7, u'FORO', '#FB938F', '#000000'),
    (8, u'TRABAJO PRÁCTICO EXPERIMENTAL', '#C36B85', '#000000'),
)


class CalendarioRecursoActividad(ModeloBase):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, verbose_name=u'Materia')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name=u'content type', blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True, verbose_name=u'object id')
    content_object = GenericForeignKey('content_type', 'object_id')
    tipo = models.IntegerField(choices=CHOICES_TIPO_ACTIVIDADES, blank=True, null=True, verbose_name=u'Tipo de actividad')
    url = models.URLField(verbose_name=u"URL Moodle", blank=True, null=True, max_length=500)
    fechahoradesde = models.DateTimeField(verbose_name='Fecha hora desde', blank=True, null=True)
    fechahorahasta = models.DateTimeField(verbose_name='Fecha hora hasta', blank=True, null=True)
    cambio = models.BooleanField(default=False, verbose_name=u'Cambio de fecha')

    def __str__(self):
        eActividad = self.actividad()
        eMateria = eActividad.silabosemanal.silabo.materia
        return f"Materia: {eMateria.__str__()} - Actividad >>> [{eActividad.nombre_actividad()}]"

    def actividad(self):
        return self.content_object

    class Meta:
        verbose_name = u'Calendario de recursos de actividades'
        verbose_name_plural = u'Calendarios de recursos de actividades'
        ordering = ('materia', 'fechahoradesde', 'fechahorahasta',)
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]


class CalendarioRecursoActividadAlumno(ModeloBase):
    recurso = models.ForeignKey(CalendarioRecursoActividad, verbose_name=u'Recurso', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u'Materia Asignada', on_delete=models.CASCADE)

    def __str__(self):
        return f"Estudiante: {self.materiaasignada.matricula.inscripcion.persona.__str__()} - {self.recurso.__str__()}"

    class Meta:
        verbose_name = u'Calendario de recursos de actividades del alumno'
        verbose_name_plural = u'Calendario de recursos de actividades de los alumnos'
        ordering = ('recurso', 'materiaasignada',)


class CalendarioRecursoActividadAlumnoMotificacion(ModeloBase):
    actividadalumno = models.ForeignKey(CalendarioRecursoActividadAlumno, verbose_name=u'Actividad Alumno', on_delete=models.CASCADE)
    segundos = models.FloatField(default=0, verbose_name=u'Segundos')
    notificacion = models.ForeignKey(Notificacion, verbose_name=u'Notificación', on_delete=models.CASCADE)

    def __str__(self):
        return f"Estudiante: {self.actividadalumno.materiaasignada.matricula.inscripcion.persona.__str__()} - {self.actividadalumno.recurso.__str__()}"

    class Meta:
        verbose_name = u'Notificación de recursos de actividades del alumno'
        verbose_name_plural = u'Notificaciones de recursos de actividades de los alumnos'
        ordering = ('actividadalumno', 'segundos',)


def upload_matricula_sede_examen_documento_identidad_directory_path(instance, filename):
    ahora = datetime.now()
    documento = instance.matricula.inscripcion.persona.documento()
    return 'matricula/sede/examen/{0}/documento/{1}/{2}/{3}/{4}'.format(f'{documento}', f'{str(ahora.year)}', f'{ahora.month:02d}', f'{ahora.day:02d}', filename)


def upload_matricula_sede_examen_foto_identidad_directory_path(instance, filename):
    ahora = datetime.now()
    documento = instance.matricula.inscripcion.persona.documento()
    return 'matricula/sede/examen/{0}/foto/{1}/{2}/{3}/{4}'.format(f'{documento}', f'{str(ahora.year)}', f'{ahora.month:02d}', f'{ahora.day:02d}', filename)

class SedeProvincia(ModeloBase):
    sede_virtual = models.ForeignKey('sga.SedeVirtual', verbose_name=u'Sede Virtual', on_delete=models.CASCADE)
    provincia = models.ForeignKey('sga.Provincia', verbose_name=u'Provincia', on_delete=models.CASCADE)

    def __str__(self):
        return f"Sede:{self.sede_virtual} - Provincia:{self.provincia}"

    class Meta:
        verbose_name = u'Sedes de examen según provincia cercana'
        verbose_name_plural = u'Sedes de examen según provincia cercana'


class MatriculaSedeExamen(ModeloBase):
    matricula = models.ForeignKey(Matricula, verbose_name=u'Matricula', on_delete=models.CASCADE)
    sede = models.ForeignKey(SedeVirtual, verbose_name=u'Sede', on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativo, verbose_name=u'Modelo evaluativo', on_delete=models.CASCADE, blank=True, null=True,)
    archivoidentidad = models.FileField(upload_to=upload_matricula_sede_examen_documento_identidad_directory_path, blank=True, null=True, verbose_name=u'Archivo')
    archivofoto = models.FileField(upload_to=upload_matricula_sede_examen_foto_identidad_directory_path, blank=True, null=True, verbose_name=u'Archivo')
    aceptotermino = models.BooleanField(default=False, blank=True, null=True, verbose_name=u'¿Acepto terminos?')
    migrargsbucket = models.BooleanField(default=False, blank=True, null=True, verbose_name=u'¿Acepto terminos?')
    fechaaceptotermino = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de aceptación de terminos')
    urltermino = models.URLField(verbose_name=u"URL PDF", blank=True, null=True, max_length=1000)

    def __str__(self):
        return f"Periodo: {self.matricula.nivel.periodo.__str__()} - Examen: {self.detallemodeloevaluativo.nombre} - {self.matricula.inscripcion.info()} - {self.sede.__str__()}"

    class Meta:
        verbose_name = u'Sede de matricula de examen'
        verbose_name_plural = u'Sedes de matricula de examen'
        ordering = ('detallemodeloevaluativo', 'matricula', 'sede')
        unique_together = ('detallemodeloevaluativo', 'matricula', 'sede')

    def en_uso(self):
        eHorarioExamenDetalleAlumnos = HorarioExamenDetalleAlumno.objects.values("id").filter(status=True, horarioexamendetalle__horarioexamen__detallemodelo=self.detallemodeloevaluativo, materiaasignada__matricula=self.matricula).exists()
        eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(status=True, materiaasignada__materia__modeloevaluativo__detallemodeloevaluativo=self.detallemodeloevaluativo, materiaasignada__matricula=self.matricula).exists()
        return eHorarioExamenDetalleAlumnos or eMateriaAsignadaPlanificacionSedeVirtualExamenes

    def puede_editar(self):
        return self.en_uso() == False

    def puede_eliminar(self):
        return self.en_uso() == False
    
    def delete(self, *args, **kwargs):
        self.matricula.delete_cache()
        super(MatriculaSedeExamen, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.matricula.delete_cache()
        if self.id and self.migrargsbucket == False:
            self.migrargsbucket = True
        super(MatriculaSedeExamen, self).save(*args, **kwargs)


class FechaPlanificacionSedeVirtualExamen(ModeloBase):
    fecha = models.DateField(verbose_name=u'Fecha examen')
    sede = models.ForeignKey(SedeVirtual, verbose_name=u'Sede', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    supervisor = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)

    def __str__(self):
        return f"Periodo: {self.periodo.__str__()} - Fecha: {self.fecha.__str__()} - {self.sede.__str__()}"

    class Meta:
        verbose_name = u'Fecha planificación sede de examen'
        verbose_name_plural = u'Fechas de planificación de sedes de examen'
        ordering = ('periodo', 'fecha', 'sede')
        unique_together = ('fecha', 'sede', 'periodo')

    def get_horasplanificadas(self, persona=None):
        if persona is None:
            eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(status=True, turnoplanificacion__fechaplanificacion=self)
        else:
            if persona.usuario.is_superuser:
                eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(status=True, turnoplanificacion__fechaplanificacion=self)
            else:
                idsindividual = AulaPlanificacionSedeVirtualExamen.objects.filter(Q(responsable=persona) | Q(turnoplanificacion__fechaplanificacion__supervisor=persona) | Q(supervisor=persona), status=True, turnoplanificacion__fechaplanificacion=self).distinct().values_list('id', flat=True)
                idsgrupal = SupervisorAulaPlanificacionSedeVirtualExamen.objects.filter(Q(responsable=persona) | Q(supervisor=persona), status=True, aulaplanificacion__turnoplanificacion__fechaplanificacion=self).distinct().values_list('aulaplanificacion_id', flat=True)
                eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(Q(id__in=idsindividual) | Q(id__in=idsgrupal))
        eTurnoPlanificacionSedeVirtualExamenes = TurnoPlanificacionSedeVirtualExamen.objects.filter(pk__in=eAulaPlanificacionSedeVirtualExamenes.values_list("turnoplanificacion__id", flat=True), status=True)
        return eTurnoPlanificacionSedeVirtualExamenes if eTurnoPlanificacionSedeVirtualExamenes.values("id").exists() else []

    def save(self, *args, **kwargs):
        super(FechaPlanificacionSedeVirtualExamen, self).save(*args, **kwargs)

    def enuso(self):
        return self.turnoplanificacionsedevirtualexamen_set.values("id").exists()


class TurnoPlanificacionSedeVirtualExamen(ModeloBase):
    fechaplanificacion = models.ForeignKey(FechaPlanificacionSedeVirtualExamen, verbose_name=u'Fecha planificación', on_delete=models.CASCADE)
    horainicio = models.TimeField(verbose_name=u'Hora Inicio')
    horafin = models.TimeField(verbose_name=u'Hora Fin')
    horas = models.IntegerField(verbose_name=u"Cantidad Horas", default=1)

    def __str__(self):
        return f"{self.fechaplanificacion.__str__()} - Tiempo: {self.horainicio.__str__()} - {self.horafin.__str__()}"

    class Meta:
        verbose_name = u'Horario de planificación sede de examen'
        verbose_name_plural = u'Horarios de planificación de sedes de examen'
        ordering = ('horainicio', 'horafin')
        unique_together = ('fechaplanificacion', 'horainicio', 'horafin')

    def get_aulasplanificadas(self, persona=None):
        filtro = Q(turnoplanificacion=self) & Q(status=True)
        if persona:
            if not persona.usuario.is_superuser:
                filtro = filtro & Q(Q(responsable=persona) | Q(turnoplanificacion__fechaplanificacion__supervisor=persona) | Q(supervisor=persona))
        idsindividual = AulaPlanificacionSedeVirtualExamen.objects.filter(filtro)
        idsgrupal = SupervisorAulaPlanificacionSedeVirtualExamen.objects.filter(Q(responsable=persona) | Q(supervisor=persona), status=True, aulaplanificacion__turnoplanificacion=self).distinct().values_list('aulaplanificacion_id', flat=True)
        eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(Q(id__in=idsindividual) | Q(id__in=idsgrupal))
        return eAulaPlanificacionSedeVirtualExamenes if eAulaPlanificacionSedeVirtualExamenes.values("id").exists() else []

    def save(self, *args, **kwargs):
        super(TurnoPlanificacionSedeVirtualExamen, self).save(*args, **kwargs)

    def enuso(self):
        return self.aulaplanificacionsedevirtualexamen_set.values("id").exists()


class AulaPlanificacionSedeVirtualExamen(ModeloBase):
    turnoplanificacion = models.ForeignKey(TurnoPlanificacionSedeVirtualExamen, verbose_name=u'Horario planificación', on_delete=models.CASCADE)
    aula = models.ForeignKey(LaboratorioVirtual, verbose_name=u'Aula sede', on_delete=models.CASCADE)
    responsable = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Aplicador', related_name='+', on_delete=models.CASCADE)
    supervisor = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Supervisor', related_name='+', on_delete=models.CASCADE)
    password = models.CharField(default='', max_length=100, blank=True, null=True, verbose_name=u'Clave de acceso')
    fecha_registrohabilitacion = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha y hora habilitación de examen')
    token = models.CharField(default='', blank=True, null=True, max_length=500, verbose_name=u'Token', db_index=True)
    url_video = models.TextField(default='', blank=True, null=True, max_length=1000, verbose_name=u'Url_video')

    def __str__(self):
        return f"{self.turnoplanificacion.__str__()} - Aula: {self.aula.__str__()}"

    class Meta:
        verbose_name = u'Aula de planificación sede de examen'
        verbose_name_plural = u'Aulas de planificación de sedes de examen'
        ordering = ('turnoplanificacion', 'aula')
        unique_together = ('turnoplanificacion', 'aula')

    def save(self, *args, **kwargs):
        super(AulaPlanificacionSedeVirtualExamen, self).save(*args, **kwargs)

    def cantidadad_planificadas(self):
        return len(self.materiaasignadaplanificacionsedevirtualexamen_set.values("id").filter(status=True))

    def cupo_disponible(self):
        return self.aula.capacidad - self.cantidadad_planificadas()

    def cantidadad_planificadas_materias(self):
        from django.db.models import Sum
        from django.db.models.functions import Coalesce
        return self.materiaplanificacionsedevirtualexamen_set.filter(status=True).aggregate(total=Coalesce(Sum('cupo'), 0)).get('total')

    def materiaasignadaplanificadas(self):
        return self.materiaasignadaplanificacionsedevirtualexamen_set.all()

    def create_update_password(self):
        from inno.funciones import generar_clave_aleatoria
        if not self.password or self.password == '':
            self.password = generar_clave_aleatoria(10, True)

    def enuso(self):
        return self.materiaasignadaplanificacionsedevirtualexamen_set.values("id").exists()

    def generate_token(self):
        from hashlib import md5
        from sga.templatetags.sga_extras import encrypt
        if self.token:
            return self.token
        fecha = datetime.now().date()
        hora = datetime.now().time()
        fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
        token = md5(str(encrypt(self.id) + fecha_hora).encode("utf-8")).hexdigest()
        return token

    def save(self, *args, **kwargs):
        self.create_update_password()
        if self.password:
            self.password = self.password.strip()
        super(AulaPlanificacionSedeVirtualExamen, self).save(*args, **kwargs)


class SupervisorAulaPlanificacionSedeVirtualExamen(ModeloBase):
    aulaplanificacion = models.ForeignKey(AulaPlanificacionSedeVirtualExamen, verbose_name=u'Aula planificación', on_delete=models.CASCADE)
    responsable = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Aplicador', related_name='+', on_delete=models.CASCADE)
    supervisor = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Supervisor', related_name='+', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.aulaplanificacion.__str__()} - Responsable: {self.responsable.__str__()} - Supervisor: {self.supervisor.__str__()}"

    class Meta:
        verbose_name = u'Responsable de aula de planificación sede de examen'
        verbose_name_plural = u'Responsable de aula de planificación sede de examen'
        ordering = ('aulaplanificacion','responsable',)


# class AulaPlanificacionSedeVirtualExamenToken(ModeloBase):
#     from bd.models import UserToken
#     aulaplanificacion = models.ForeignKey(AulaPlanificacionSedeVirtualExamen, verbose_name=u'Aula planificación', on_delete=models.CASCADE)
#     user_token = models.ForeignKey(UserToken, verbose_name=u'Token', on_delete=models.CASCADE)
#     isActive = models.BooleanField(default=True, verbose_name=u"Activo?")
#
#     def __str__(self):
#         return f"{self.aulaplanificacion} - {self.user_token}"
#
#     def isValidoCodigo(self, codigo):
#         if not self.user_token.isValidoToken():
#             return False
#         return self.codigo == codigo
#
#     def inactiveToken(self):
#         self.isActive = False
#         self.save()
#
#     class Meta:
#         verbose_name = u"Token Aula planificación"
#         verbose_name_plural = u"Tokens de aulas de planificación"
#         ordering = ('aulaplanificacion', 'user_token', )
#         # unique_together = ('token',)

class MateriaPlanificacionSedeVirtualExamen(ModeloBase):
    aulaplanificacion = models.ForeignKey(AulaPlanificacionSedeVirtualExamen, verbose_name=u'Aula planificación', on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, verbose_name=u'MateriaAsignada', on_delete=models.CASCADE)
    asignaturamalla = models.ForeignKey(AsignaturaMalla, verbose_name=u'Asignatura malla',null=True, blank=True, on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativo, null=True, blank=True, verbose_name=u'Modelo evaluativo', on_delete=models.CASCADE)
    cupo = models.IntegerField(default=0, verbose_name=u'Cupo de la materia')

    def __str__(self):
        return f"{self.aulaplanificacion.__str__()} - Materia: {self.materia.__str__()}"

    class Meta:
        verbose_name = u'Materia de planificación sede de examen'
        verbose_name_plural = u'Materia de planificación de sedes de examen'
        ordering = ('aulaplanificacion', 'materia', 'detallemodeloevaluativo')
        unique_together = 'aulaplanificacion', 'materia', 'detallemodeloevaluativo'

    def save(self, *args, **kwargs):
        super(MateriaPlanificacionSedeVirtualExamen, self).save(*args, **kwargs)


class MateriaAsignadaPlanificacionSedeVirtualExamen(ModeloBase):
    aulaplanificacion = models.ForeignKey(AulaPlanificacionSedeVirtualExamen, verbose_name=u'Aula planificación', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u'MateriaAsignada', on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativo, null=True, blank=True, verbose_name=u'Modelo evaluativo', on_delete=models.CASCADE)
    asistencia = models.BooleanField(default=False, verbose_name=u'Asistencia al examen')
    fecha_asistencia = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de la asistencia al aexamen')
    habilitadoexamen = models.BooleanField(default=False, verbose_name=u'Habilita examen en moodle')
    aviability = models.TextField(default="", blank=True, null=True, verbose_name=u'Texto habilitante examen')
    idtestmoodle = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'id del test de moodle')
    password = models.CharField(default='', max_length=100, blank=True, null=True, verbose_name=u'Clave de acceso')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')
    calificacion = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Calificación')
    archivo = models.FileField(upload_to='planificacion/sede/examen/materiaasignada', blank=True, null=True, verbose_name=u'Archivo')
    utilizar_qr = models.BooleanField(default=False, verbose_name=u'Uitliza QR')
    fecha_qr = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de generación del QR')
    url_qr = models.URLField(verbose_name=u"URL QR", blank=True, null=True, max_length=1000)
    codigo_qr = models.CharField(default='', verbose_name=u"Código QR", blank=True, null=True, max_length=50, db_index=True)

    def __str__(self):
        return f"{self.aulaplanificacion.__str__()} - MateriaAsignada: {self.materiaasignada.__str__()}"

    class Meta:
        verbose_name = u'MateriaAsignada de planificación sede de examen'
        verbose_name_plural = u'MateriaAsignadas de planificación de sedes de examen'
        ordering = ('aulaplanificacion', 'materiaasignada', 'detallemodeloevaluativo',)
        unique_together = ('materiaasignada', 'detallemodeloevaluativo', )

    def generaraviability(self):
        # {"type":"profile","sf":"email","op":"isequalto","v":"crodriguezn@unemi.edu.ec"},{"type":"date","d":">=","t":1659985200},{"type":"date","d":"<","t":1659992400}
        fecha=self.aulaplanificacion.turnoplanificacion.fechaplanificacion.fecha
        horainicio=self.aulaplanificacion.turnoplanificacion.horainicio
        horafin=self.aulaplanificacion.turnoplanificacion.horafin
        fechadesde = datetime(fecha.year,fecha.month,fecha.day, horainicio.hour, horainicio.minute,horainicio.second)
        fechadesde = int(time.mktime(fechadesde.timetuple()))
        fechahasta = datetime(fecha.year, fecha.month, fecha.day, horafin.hour, horafin.minute, horafin.second)
        fechahasta = int(time.mktime(fechahasta.timetuple()))
        return {"op":"&",
                "c":[{"type":"profile",
                      "sf":"email",
                      "op":"isequalto",
                      "v":f"{self.materiaasignada.matricula.inscripcion.persona.emailinst}"},
                     {"type":"date",
                      "d":">=",
                      "t":fechadesde},
                     {"type":"date",
                      "d":"<",
                      "t":fechahasta}
                     ]}

    def create_update_password(self):
        from inno.funciones import generar_clave_aleatoria
        if self.detallemodeloevaluativo.password:
            if not self.aulaplanificacion.password or self.aulaplanificacion.password == '':
                eAulaPlanificacionSedeVirtualExamen = self.aulaplanificacion
                eAulaPlanificacionSedeVirtualExamen.password = generar_clave_aleatoria(10)
                eAulaPlanificacionSedeVirtualExamen.save()
                self.password = eAulaPlanificacionSedeVirtualExamen.password
            else:
                self.password = self.aulaplanificacion.password
        else:
            if self.aulaplanificacion.password or self.aulaplanificacion.password != '':
                self.password = self.aulaplanificacion.password

        return self.password

    def acceso_examen_moodle(self):
        from django.db import connections
        from Moodle_Funciones import buscarUsuario
        lista = []
        if self.materiaasignada.materia.coordinacion():
            # fecha = int(time.mktime(datetime.now().timetuple()))
            if self.materiaasignada.materia.coordinacion().id == 9:
                conexion = connections['db_moodle_virtual']
                # cursor_verbose = 'db_moodle_virtual'
            else:
                conexion = connections['moodle_db']
                # cursor_verbose = 'moodle_db'
            cursor = conexion.cursor()
            user_id = buscarUsuario(self.materiaasignada.matricula.inscripcion.persona.usuario.username, cursor)
            sql = """
                    SELECT TO_TIMESTAMP(att.timestart), TO_TIMESTAMP(att.timefinish),
                    ( CASE WHEN att.timestart=0 THEN 0 ELSE 1 END) AS inicia,
                    ( CASE WHEN att.timefinish=0 THEN 0 ELSE 1 END) AS finaliza
                    FROM mooc_quiz_attempts att
                    INNER JOIN mooc_quiz quiz ON quiz.id=att.quiz
                    INNER JOIN mooc_course cou ON cou.id=quiz.course
                    INNER JOIN  mooc_grade_items gi ON gi.courseid=cou.id AND gi.itemmodule='quiz' AND quiz.id=gi.iteminstance
                    INNER JOIN  mooc_grade_categories ct ON ct.courseid=cou.id
                    WHERE cou.id=%s AND att.userid=%s AND ct.fullname='%s'
                    AND ct.courseid=%s AND ct.depth=2 AND ct.id=gi.categoryid
                    """ % (
                self.materiaasignada.materia.idcursomoodle, user_id, self.detallemodeloevaluativo.nombre, self.materiaasignada.materia.idcursomoodle)
            cursor.execute(sql)
            row = cursor.fetchall()
            for r in row:
                lista.append(r)
        return lista

    def ip_log_rango_examen(self):
        from django.db import connections
        from Moodle_Funciones import buscarUsuario
        lista = []
        if self.materiaasignada.materia.coordinacion():
            if self.materiaasignada.materia.coordinacion().id == 9:
                conexion = connections['db_moodle_virtual']
                # cursor_verbose = 'db_moodle_virtual'
            else:
                conexion = connections['moodle_db']
                # cursor_verbose = 'moodle_db'
            cursor = conexion.cursor()
            id_usuario_moodle = buscarUsuario(self.materiaasignada.matricula.inscripcion.persona.usuario.username, cursor)
            id_curso_moodle = self.materiaasignada.materia.idcursomoodle
            fecha = self.aulaplanificacion.turnoplanificacion.fechaplanificacion.fecha
            fecha_hora_inicio = datetime(fecha.year, fecha.month, fecha.day, 0, 1)
            fecha_hora_fin = datetime(fecha.year, fecha.month, fecha.day, 23, 59)

            sql = f"""
                    SELECT l1.ip, TO_TIMESTAMP(l1.timecreated)
                    FROM mooc_logstore_standard_log l1
                    WHERE l1.userid={id_usuario_moodle} AND l1.courseid={id_curso_moodle} 
                    AND TO_TIMESTAMP(l1.timecreated) BETWEEN '{fecha_hora_inicio}' AND '{fecha_hora_fin}'
                    AND l1.objectid IN (
                        SELECT quiz.id
                        FROM mooc_quiz_attempts att
                        INNER JOIN mooc_quiz quiz ON quiz.id=att.quiz
                        INNER JOIN mooc_course cou ON cou.id=quiz.course
                        INNER JOIN mooc_grade_items gi ON gi.courseid=cou.id AND gi.itemmodule='quiz' AND quiz.id=gi.iteminstance
                        INNER JOIN mooc_grade_categories ct ON ct.courseid=cou.id
                        WHERE cou.id={id_curso_moodle} AND att.userid={id_usuario_moodle} AND ct.fullname='{self.detallemodeloevaluativo.nombre}' 
                        AND ct.courseid={id_curso_moodle} AND ct.depth=2 AND ct.id=gi.categoryid
                        LIMIT 1
                    )
                    ORDER BY - l1.timecreated
                    """
            cursor.execute(sql)
            lista = cursor.fetchall()
        return lista

    def get_quiz_attempts(self):
        from django.db import connections
        from moodle.moodle import BuscarUsuario
        from Moodle_Funciones import buscarUsuario
        lista = []
        if self.materiaasignada.materia.coordinacion():
            if self.materiaasignada.materia.coordinacion().id == 9:
                conexion = connections['db_moodle_virtual']
                tipourl = 2
            else:
                conexion = connections['moodle_db']
                tipourl = 1
            cursor = conexion.cursor()
            periodo = self.materiaasignada.materia.nivel.periodo
            username = self.materiaasignada.matricula.inscripcion.persona.usuario.username
            id_usuario_moodle = buscarUsuario(username, cursor)
            id_curso_moodle = self.materiaasignada.materia.idcursomoodle
            id_quiz_moodle = self.idtestmoodle
            if DEBUG:
                id_usuario_moodle = 5
                id_quiz_moodle = 4
                bestudiante = BuscarUsuario(periodo, tipourl, 'username', username)
                if not bestudiante:
                    bestudiante = BuscarUsuario(periodo, 1, 'username', username)
                if bestudiante['users']:
                    if 'id' in bestudiante['users'][0]:
                        id_usuario_moodle = bestudiante['users'][0]['id']
            if id_usuario_moodle and id_quiz_moodle:
                sql = f"""  SELECT *
                            FROM mooc_quiz_attempts
                            WHERE quiz = {id_quiz_moodle} AND userid = {id_usuario_moodle} AND preview = 0
                            ORDER BY quiz, attempt ASC
                            """
                cursor.execute(sql)
                lista = cursor.fetchall()
        return lista

    def get_grade_items(self):
        from django.db import connections
        from Moodle_Funciones import buscarUsuario
        from moodle.moodle import ObtenerGradeItems, BuscarUsuario

        id_quiz_moodle = self.idtestmoodle
        if not id_quiz_moodle:
            examenplanificado = self.materiaasignada.materia.examenplanificadosilabo(self.detallemodeloevaluativo)
            if examenplanificado:
                id_quiz_moodle = int(examenplanificado.get('idtestmoodle'))
            else:
                return None
        id_curso_moodle = self.materiaasignada.materia.idcursomoodle
        periodo = self.materiaasignada.materia.nivel.periodo
        username = self.materiaasignada.matricula.inscripcion.persona.usuario.username
        cursor = None
        # if DEBUG:
        #     id_curso_moodle = 6959
        #     id_quiz_moodle = 44512
        tipourl = 1
        if self.materiaasignada.materia.coordinacion():
            if self.materiaasignada.materia.coordinacion().id == 9:
                conexion = connections['db_moodle_virtual']
                tipourl = 2
            else:
                conexion = connections['moodle_db']
                tipourl = 1
            cursor = conexion.cursor()
            id_usuario_moodle = buscarUsuario(username, cursor)
            if DEBUG:
                id_usuario_moodle = 10123
                bestudiante = BuscarUsuario(periodo, tipourl, 'username', username)
                if not bestudiante:
                    bestudiante = BuscarUsuario(periodo, tipourl, 'username', username)
                if bestudiante['users']:
                    if 'id' in bestudiante['users'][0]:
                        id_usuario_moodle = bestudiante['users'][0]['id']
        if not id_usuario_moodle:
            return None
        items = ObtenerGradeItems(periodo, tipourl, id_curso_moodle, id_usuario_moodle)
        if items:
            if 'usergrades' in items and items['usergrades']:
                usergrades = items['usergrades'][0]
                if 'gradeitems' in usergrades and usergrades['gradeitems']:
                    for item in usergrades['gradeitems']:
                        if id_quiz_moodle == item['iteminstance']:
                            return item
        # sql = f"""SELECT id FROM mooc_grade_items WHERE courseid=%s AND iteminstance=%s LIMIT 1""" % (id_curso_moodle, id_quiz_moodle)
        # cursor.execute(sql)
        # row = cursor.fetchone()
        # if row:
        #     return row[0]
        return None

    def get_grade_grades(self):
        from django.db import connections
        from moodle.moodle import ObtenerGrades, BuscarUsuario
        from Moodle_Funciones import buscarUsuario
        item = self.get_grade_items()
        # print(f"Item: {item}")
        if item:
            if self.materiaasignada.materia.coordinacion():
                if self.materiaasignada.materia.coordinacion().id == 9:
                    conexion = connections['db_moodle_virtual']
                    tipourl = 2
                else:
                    conexion = connections['moodle_db']
                    tipourl = 1
                cursor = conexion.cursor()
                id_curso_moodle = self.materiaasignada.materia.idcursomoodle
                periodo = self.materiaasignada.materia.nivel.periodo
                username = self.materiaasignada.matricula.inscripcion.persona.usuario.username
                id_usuario_moodle = buscarUsuario(username, cursor)
                id_item = item['id']
                id_quiz = item['iteminstance']
                id_activity = item['cmid']
                if DEBUG:
                    # id_usuario_moodle = 5
                    bestudiante = BuscarUsuario(periodo, tipourl, 'username', username)
                    if not bestudiante:
                        bestudiante = BuscarUsuario(periodo, tipourl, 'username', username)
                    if bestudiante['users']:
                        if 'id' in bestudiante['users'][0]:
                            id_usuario_moodle = bestudiante['users'][0]['id']
                    # id_quiz_moodle = 4
                if not id_usuario_moodle:
                    return None
                grades = ObtenerGrades(periodo, tipourl, id_curso_moodle, 'mod_quiz', id_activity, [id_usuario_moodle])
                if grades and 'items' in grades and grades['items']:
                    return grades['items'][0]
                # sql = f"""SELECT id, ROUND(finalgrade,2), feedback, itemid, rawgrade, rawgrademax, rawgrademin FROM mooc_grade_grades WHERE itemid=%s AND userid=%s LIMIT 1""" % (item, id_usuario_moodle)
                # # print(sql)
                # cursor.execute(sql)
                # row = cursor.fetchone()
                # if row:
                #     return {'id': row[0], 'finalgrade': row[1], 'feedback': row[2], 'itemid': row[3], 'rawgrade': row[4], 'rawgrademax': row[5], 'rawgrademin': row[6]}
        return None

    def update_grade_grades(self):
        from django.db import connections
        from moodle.moodle import ActualizarGrades, BuscarUsuario
        from Moodle_Funciones import buscarUsuario
        item = self.get_grade_items()
        if not item:
            return False, u'No se encontro actividad con cuadro de calificación'
        id_item = item['id']
        id_quiz = item['iteminstance']
        id_activity = item['cmid']
        id_curso_moodle = self.materiaasignada.materia.idcursomoodle
        periodo = self.materiaasignada.materia.nivel.periodo
        if self.materiaasignada.materia.coordinacion():
            if self.materiaasignada.materia.coordinacion().id == 9:
                conexion = connections['db_moodle_virtual']
                tipourl = 2
            else:
                conexion = connections['moodle_db']
                tipourl = 1
            cursor = conexion.cursor()
            username = self.materiaasignada.matricula.inscripcion.persona.usuario.username
            id_usuario_moodle = buscarUsuario(username, cursor)
            if DEBUG:
                # id_usuario_moodle = 5
                bestudiante = BuscarUsuario(periodo, tipourl, 'username', username)
                if not bestudiante:
                    bestudiante = BuscarUsuario(periodo, tipourl, 'username', username)
                if bestudiante['users']:
                    if 'id' in bestudiante['users'][0]:
                        id_usuario_moodle = bestudiante['users'][0]['id']
            grades = [{'studentid': id_usuario_moodle,
                       'grade': null_to_numeric(self.calificacion, 5),
                       'str_feedback': self.observacion
                       }]
            itemdetails = []
            result = ActualizarGrades(periodo, tipourl, 'aggregation', id_curso_moodle, 'mod_quiz', id_activity, 0, grades, itemdetails)
            if result == 0:
                result = ActualizarGrades(periodo, tipourl, 'aggregation', id_curso_moodle, 'mod_quiz', id_activity, 0, grades, itemdetails)
                if result == 0:
                    if id_usuario_moodle and id_item:
                        sql = f"""SELECT id FROM mooc_grade_grades WHERE itemid=%s AND userid=%s LIMIT 1""" % (id_item, id_usuario_moodle)
                        cursor.execute(sql)
                        row = cursor.fetchone()
                        if row:
                            id_grade = row[0]
                            overridden = int(time.mktime(datetime.now().timetuple()))
                            timemodified = int(time.mktime(datetime.now().timetuple()))
                            feedback = self.observacion
                            sql = """   update mooc_grade_grades
                                        set timemodified='%s',
                                        feedback='%s',
                                        overridden='%s'
                                        where id=%s
                                    """ % (timemodified, feedback, overridden, id_grade)
                            cursor.execute(sql)
                return True, 'Se guardo correctamente la calificación'
            else:
                return False, 'No se pudo guardar la calificación en moodle'
        return False, u'No se encontro coordinación definida'

    def save(self, *args, **kwargs):
        updatePassword = False
        for key, value in kwargs.items():
            if 'updatePassword' == key:
                updatePassword = value
        if not updatePassword:
            self.create_update_password()
        if self.password:
            self.password = self.password.strip()
        super(MateriaAsignadaPlanificacionSedeVirtualExamen, self).save(*args, **kwargs)


class AuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen(ModeloBase):
    materiaasignadaplanificacion = models.ForeignKey(MateriaAsignadaPlanificacionSedeVirtualExamen, verbose_name=u'MateriAsignada planificación', on_delete=models.CASCADE)
    manual = models.BooleanField(default=False, verbose_name=u'Agregado manualmente')
    calificacion = models.FloatField(default=0, verbose_name=u'Calificación')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    archivo = models.URLField(verbose_name=u"Archivo", blank=True, null=True)

    def __str__(self):
        return f"{self.materiaasignadaplanificacion.__str__()}"

    class Meta:
        verbose_name = u'Auditoria de MateriaAsignada de planificación sede de examen'
        verbose_name_plural = u'Auditoria de MateriaAsignadas de planificación de sedes de examen'


class BecaPeriodoResumen(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)
    matriculados = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de matriculados')
    matriculados_regulares = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de matriculados regulares')
    preseleccionados_becas = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de preseleccionados a becas')
    preseleccionados_becasaceptados = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de preseleccionados a becas')
    preseleccionados_becasadjudicados = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de preseleccionados a becas adjuudicados')
    preseleccionados_becaspagados = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de preseleccionados a becas pagados')
    fecha_cohorte = models.DateField(verbose_name='Fecha cohorte', blank=True, null=True)
    archivo = models.FileField(upload_to='becaperiodoresumen', blank=True, null=True, verbose_name=u'Archivo Evidencia')

    def __str__(self):
        return f"{self.periodo} - Matriculados: {self.matriculados}"

    class Meta:
        verbose_name = u'Beca periódo resumen'
        verbose_name_plural = u'Becas periódos resumenes'
        ordering = ('periodo',)

    def porcentaje_de_cumplimiento_preseleccionados(self):
        try:
            return null_to_decimal((self.preseleccionados_becas*100)/self.matriculados_regulares, 2)
        except ZeroDivisionError:
            return 0.0

    def porcentaje_de_cumplimiento_preseleccionados_aceptados(self):
        try:
            return null_to_decimal((self.preseleccionados_becasaceptados*100)/self.matriculados_regulares, 2)
        except ZeroDivisionError:
            return 0.0

    def porcentaje_de_cumplimiento_preseleccionados_adjudicadas(self):
        try:
            return null_to_decimal((self.preseleccionados_becasadjudicados*100)/self.matriculados_regulares, 2)
        except ZeroDivisionError:
            return 0.0

    def porcentaje_de_cumplimiento_preseleccionados_pagados(self):
        try:
            return null_to_decimal((self.preseleccionados_becaspagados*100)/self.matriculados_regulares, 2)
        except ZeroDivisionError:
            return 0.0

# # Afinidad
class ConfiguracionAfinidad(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.periodo}"

    class Meta:
        verbose_name = u'Configuracion Afinidad'
        verbose_name_plural = u'Configuraciones Afinidad'
        ordering = ('periodo',)

    def detalle_afinidad(self):
        return self.detalleafinidad_set.filter(status=True)

    def en_uso(self):
        return True if self.detalleafinidad_set.values('id').filter(status=True).exists() else False

class DetalleAfinidad(ModeloBase):
    configafinidad = models.ForeignKey(ConfiguracionAfinidad, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Configuracion Afinidad')
    malla = models.ForeignKey(Malla, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Malla')

    def __str__(self):
        return f"{self.malla} - {self.configafinidad}"

    class Meta:
        verbose_name = u'DetalleAfinidad'
        verbose_name_plural = u'Detalles Afinidad'
        ordering = ('configafinidad',)

    def en_uso(self):
        return True if self.resultadoafinidad_set.values('id').filter(status=True).exists() else False

class ResultadoAfinidad(ModeloBase):
    detafinidad = models.ForeignKey(DetalleAfinidad, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Afinidad del periodo')
    docente = models.ForeignKey(Profesor, blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    asignaturamalla = models.ForeignKey(AsignaturaMalla, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Asignatura Malla')
    orden = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Orden')
    cumplecampoamplio = models.BooleanField(default=False, verbose_name=u'Cumple con campo amplio')
    cumplecampodetallado = models.BooleanField(default=False, verbose_name=u'Cumple con campo detallado')
    cumplecampoespecifico = models.BooleanField(default=False, verbose_name=u'Cumple con campo especifico')
    fecha = models.DateField(blank=True, null=True, verbose_name=u"Fecha")

    def __str__(self):
        return f"{self.docente} - Malla: {self.asignaturamalla}"

    class Meta:
        verbose_name = u'Resultado de Afinidad'
        verbose_name_plural = u'Resultados de Afinidad'
        ordering = ('orden',)

    # def cantidad_docentes_afinidad(self, detafinidad, asignaturamalla):
    #     if ResultadoAfinidad.objects.values("docente").filter(status=True, detafinidad=detafinidad, asignaturamalla=asignaturamalla).exists():
    #         return ResultadoAfinidad.objects.values("docente").filter(status=True, detafinidad=detafinidad, asignaturamalla=asignaturamalla).order_by("-docente").distinct().count()
    #     return 0

    def save(self, *args, **kwargs):
        super(ResultadoAfinidad, self).save(*args, **kwargs)

class HorariosAulasLaboratorios(ModeloBase):
    aula = models.ForeignKey('sga.Aula', verbose_name=u"Aula", blank=True, null=True, on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u"Persona que Reserva", blank=True, null=True, on_delete=models.CASCADE)
    materia = models.ForeignKey('sga.Materia', verbose_name=u"Materia", blank=True, null=True, on_delete=models.CASCADE)
    concepto = models.TextField(verbose_name=u"Concepto", blank=True, null=True)

    def __str__(self):
        return u'%s - %s' % (self.aula.__str__(), self.persona.__str__())

    class Meta:
        verbose_name = u"Reservacion Aula Laboratorio"
        verbose_name_plural = u"Reservaciones Aulas Laboratorios"
        ordering = ['-id']

class DetalleReservacionAulas(ModeloBase):
    horario = models.ForeignKey(HorariosAulasLaboratorios, verbose_name=u"Horario de Reserva", blank=True, null=True, on_delete=models.CASCADE)
    inicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Inicio')
    fin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Fin')
    comienza = models.TimeField(verbose_name=u'Hora Inicio', blank=True, null=True)
    termina = models.TimeField(verbose_name=u'Hora Fin', blank=True, null=True)
    dia = models.IntegerField(choices=DIAS_CHOICES, default=0, verbose_name=u'Dia')
    inactivo = models.BooleanField(verbose_name=u'¿Inactivo?', blank = True, null=True)
    oculto = models.BooleanField(verbose_name=u'¿Oculto?',default=False,blank=True, null=True)
    examen = models.BooleanField(verbose_name=u'¿Examen?', default=False, blank=True, null=True)

    def __str__(self):
        return u'%s - horario: %s - %s' % (self.horario.aula.__str__(), self.comienza, self.termina)

    class Meta:
        verbose_name = u"Detalle Horario Reservacion"
        verbose_name_plural = u"Detalles Horario Reservacion"
        ordering = ['-id']

    def estado_aula(self, fecha):
        estado = 0

        if fecha == datetime.now().date():
            horaactual = datetime.now().time()
            fechaactual = datetime.now().date()
            diaactual = datetime.now().date().isoweekday()

            if fechaactual >= self.inicio.date() and fechaactual <= self.fin.date() and diaactual == self.dia:
                if horaactual >= self.comienza and horaactual <= self.termina:
                    estado = 1
                elif horaactual > self.comienza and horaactual > self.termina:
                    estado = 2
                elif horaactual < self.comienza and horaactual < self.termina:
                    estado = 3
        else:
            if fecha < datetime.now().date():
                estado = 2
            else:
                estado= 3

        # elif fechaactual > self.fin.date():
        #     estado = 2
        # elif fechaactual < self.fin.date():
        #     estado = 3

        return estado

    def ultimo_ingreso(self):
        return self.detalleusoaula_set.filter(status=True,clasenovedad=1).order_by('-id').first()

    def ultimo_salida(self):
        return self.detalleusoaula_set.filter(status=True,clasenovedad=2).order_by('-id').first()

    def ultimo_ingreso_dia_actual(self):
        fecha = datetime.now().date()
        return self.detalleusoaula_set.filter(status=True,clasenovedad=1,fecha_creacion__date = fecha).order_by('-id').first()

    def ultimo_salida_dia_actual(self):
        fecha = datetime.now().date()
        return self.detalleusoaula_set.filter(status=True,clasenovedad=2,fecha_creacion__date = fecha).order_by('-id').first()

class DistribucionPersonalLaboratorio(ModeloBase):
    bloque = models.ForeignKey('sga.Bloque', verbose_name=u"Bloque", blank=True, null=True, on_delete=models.CASCADE)
    encargado = models.ForeignKey('sga.Persona', verbose_name=u"Encargado", blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.bloque.__str__(), self.encargado.__str__())

    class Meta:
        verbose_name = u"Distribución de Personal de Laboratorio"
        verbose_name_plural = u"Distribuciones de Personal de Laboratorio"
        ordering = ['-id']

class DetalleDistribucionPersonal(ModeloBase):
    distribucion = models.ForeignKey(DistribucionPersonalLaboratorio, verbose_name=u"Distribución del Personal", blank=True, null=True, on_delete=models.CASCADE)
    aula = models.ForeignKey('sga.Aula', verbose_name=u"Aula", blank=True, null=True, on_delete=models.CASCADE)
    inicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Inicio')
    fin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Fin')
    comienza = models.TimeField(verbose_name=u'Hora Inicio', blank=True, null=True)
    termina = models.TimeField(verbose_name=u'Hora Fin', blank=True, null=True)

    def __str__(self):
        return u'%s - fecha: %s - %s - %s - horario: %s - %s' % (self.aula.__str__(), self.inicio, self.fin, self.distribucion.encargado, self.comienza, self.termina)

    class Meta:
        verbose_name = u"Detalle de Distribución de Personal"
        verbose_name_plural = u"Detalles de Distribución de Personal"
        ordering = ['-id']

    def estado_distribucion(self):
        try:
            estado = 0
            fechaactual = datetime.now().date()

            if fechaactual >= self.inicio.date() and fechaactual <= self.fin.date():
                estado = 1
            elif fechaactual > self.fin.date():
                estado = 2
            elif fechaactual < self.inicio.date():
                estado = 3

            return estado
        except Exception as ex:
            pass

class TipoNovedad(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=400, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u'Tipo de Novedad'
        verbose_name_plural = u'Tipos de Novedades'
        ordering = ('descripcion',)

class DetalleUsoAula(ModeloBase):
    horario = models.ForeignKey(HorariosAulasLaboratorios, verbose_name=u"Horario de Reserva", blank=True, null=True, on_delete=models.CASCADE)
    detallehorario = models.ForeignKey(DetalleReservacionAulas, verbose_name=u"Detalle horario de reservacion", blank=True, null=True, on_delete=models.CASCADE)
    clasenovedad = models.IntegerField(choices=CLASE_NOVEDAD, default=0, verbose_name=u'Clase de novedad')
    tiponovedad = models.ForeignKey(TipoNovedad, verbose_name=u"Tipo de Novedad", blank=True, null=True, on_delete=models.CASCADE)
    observacion = models.TextField(verbose_name=u"Observacion", blank=True, null=True)
    oculto = models.BooleanField(verbose_name=u'Ocultar',default=False,blank=True,null=True)

    def __str__(self):
        return u'%s - %s' % (self.horario.aula.__str__(), self.tiponovedad)

    def detalle_salida(self):
        salida = DetalleUsoAula.objects.filter(horario=self.horario,detallehorario=self.detallehorario,fecha_creacion__date=self.fecha_creacion.date(),clasenovedad=2).order_by('-id').first()
        return salida

    def detalle_ingreso(self):
        ingreso = DetalleUsoAula.objects.filter(horario=self.horario,detallehorario=self.detallehorario,fecha_creacion__date=self.fecha_creacion.date(),clasenovedad=1).order_by('-id').first()
        return ingreso

    class Meta:
        verbose_name = u"Detalle Uso Aula"
        verbose_name_plural = u"Detalles Uso Aula"
        ordering = ['-id']

class PantallaAula(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=400, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    def totalpaulas(self):
        return len(self.detallepantallaaula_set.filter(status=True))

    class Meta:
        verbose_name = u"Pantalla aula"
        verbose_name_plural = u"Pantallas aulas"
        ordering = ['-id']

class DetallePantallaAula(ModeloBase):
    pantallaaula = models.ForeignKey(PantallaAula, verbose_name=u"Pantalla aula", on_delete=models.CASCADE)
    aula = models.ForeignKey(Aula, verbose_name=u"Aula", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.pantallaaula,self.aula.__str__())


    class Meta:
        verbose_name = u"Detalle Pantalla aula"
        verbose_name_plural = u"Detalle Pantallas aulas"
        ordering = ['-id']


class CronogromaDiaNoLaborable(ModeloBase):
    motivo = models.TextField(verbose_name='Motivo')
    fini = models.DateField(blank=True, null=True, verbose_name=u'Fecha de Inicio')
    ffin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Fin')
    activo = models.BooleanField(blank=True,null=True,verbose_name=u'Activo')

    def __str__(self):
        return u"%s Desde: %s - Hasta: %s" % (self.motivo,self.fini,self.ffin)

    class Meta:
        verbose_name = u"Cronograma dia no laborable"
        verbose_name_plural = u"Cronograma dias no laborables"
        ordering = ['-id']

ESTADO_CONSTATACION = (
    (1, u'Bueno'),
    (2, u'Baja'),
    (3, u'Malo'),
)

class ConstatacionFisicaLaboratorios(ModeloBase):
    activo = models.ForeignKey("sagest.ActivoFijo",verbose_name=u'Activo fijo', null=True, blank=True, on_delete=models.CASCADE)
    aula = models.ForeignKey("sga.Aula", verbose_name=u"Aula", null=True, blank=True, on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_CONSTATACION,default=1,null=True, blank=True, verbose_name=u"Estado")
    fecha_constata = models.DateField(verbose_name=u"Fecha constata", null=True, blank=True)
    hora_constata = models.TimeField(verbose_name=u"Hora constata", null=True, blank=True)
    observacion = models.TextField(verbose_name=u"Observación",null=True, blank=True)

    def __str__(self):
        return u"%s - %s -%s"%(self.activo,self.aula,self.get_estado_display())

    class Meta:
        verbose_name = u"Constatacion fisica laboratorio"
        verbose_name_plural = u"Constataciones fisica laboratorios"
        ordering = ['id']

    def get_estado_label(self):
        if self.estado==1:
            return 'bg-success'
        elif self.estado == 2:
            return 'bg-warning'
        else:
            return 'bg-danger'


class PlanificacionParalelo(ModeloBase):
    detallefuncionsustantivadocencia = models.ForeignKey(DetalleFuncionSustantivaDocenciaPac, verbose_name=u"Detalle Funcion Sustantiva Docencia", blank=True, null=True, on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u"Carrera", blank=True, null=True, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u"Periodo", blank=True, null=True, on_delete=models.CASCADE)
    paralelos = models.IntegerField(verbose_name=u"Paralelos", blank=True, null=True, default=0)
    fechalimiteplanificacion = models.DateField(verbose_name=u'Fecha limite planificacion',blank=True, null=True)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u"Asignatura")

    def __str__(self):
        if self.detallefuncionsustantivadocencia:
            return u"%s" % self.detallefuncionsustantivadocencia.asignatura
        else:
            return u"%s" % self.asignatura

    def get_por_planificar(self):
        planificacion_apertura = 0
        creadas = 0
        planificacion_apertura = null_to_decimal( PlanificacionParalelo.objects.filter(periodo=self.periodo, asignatura=self.asignatura, status=True).aggregate( paralelo=Max('paralelos'))['paralelo'])
        creadas = self.get_creadas()
        return planificacion_apertura - creadas

    def get_creadas(self):
        from postulaciondip.models import PlanificacionMateria
        creadas = 0
        eMaterias = Materia.objects.values_list('id', flat=True).filter(asignaturamalla__asignatura=self.asignatura, nivel__periodo=self.periodo, status=True)
        creadas = PlanificacionMateria.objects.filter(status=True, materia__in=eMaterias, estado=1).count()
        return creadas

    def get_paralelos_planificados(self):
        planificadas=0
        eMaterias = Materia.objects.filter(asignaturamalla__asignatura=self.asignatura, nivel__periodo=self.periodo,inicio__isnull=False,fin__isnull=False,fechafinasistencias__isnull=False, status=True)
        for materia in eMaterias:
            if materia.existe_horario():
                planificadas+=1
        return planificadas

    class Meta:
        verbose_name = u"Planificacion"
        verbose_name_plural = u"Planificacion"
        ordering = ['-id']

class InformeMensualDocente(ModeloBase):
    distributivo = models.ForeignKey(ProfesorDistributivoHoras, verbose_name=u"Distributivo", blank=True, null=True, on_delete=models.CASCADE)
    fechainicio = models.DateField(verbose_name=u'Fecha inicio informe', blank=True, null=True)
    fechafin = models.DateField(verbose_name=u'Fecha fin informe', blank=True, null=True)
    promedio = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Promedio del informe mensual')
    estado = models.IntegerField(choices=ESTADO_INFORME, default=1, blank=True, null=True, verbose_name=u"Estado solicitud")
    archivo = models.FileField(upload_to='informemensualdocente', blank=True, null=True, verbose_name=u'Archivo informe')
    automatico = models.BooleanField(default=False, verbose_name=u"Si el informe fue generado automatico desde un cron o el docente lo genero")

    def __str__(self):
        return u"%s" % self.distributivo

    def download_linkarchivogenerado(self):
        return self.archivo.url

    def listado_justificado(self):
        return self.historialjustificainforme_set.filter(status=True)

    def load_criterios(self):
        from sga.models import DetalleDistributivo
        return DetalleDistributivo.objects.filter(status=True, distributivo=self.distributivo)

class HorasInformeMensualDocente(ModeloBase):
    informe = models.ForeignKey(InformeMensualDocente, verbose_name='Informe mensual docente', null=True, blank=True, on_delete=models.SET_NULL)
    criteriodocenciaperiodo = models.ForeignKey('sga.CriterioDocenciaPeriodo', blank=True, null=True, on_delete=models.SET_NULL)
    criterioinvestigacionperiodo = models.ForeignKey('sga.CriterioInvestigacionPeriodo', blank=True, null=True, on_delete=models.SET_NULL)
    criteriogestionperiodo = models.ForeignKey('sga.CriterioGestionPeriodo', blank=True, null=True, on_delete=models.SET_NULL)
    criteriovinculacionperiodo = models.ForeignKey('sga.CriterioVinculacionPeriodo', blank=True, null=True, on_delete=models.SET_NULL)
    hpm = models.IntegerField(verbose_name='Horas planificadas en el mes', null=True, blank=True, default=0)
    hem = models.IntegerField(verbose_name='Horas ejecutadas en el mes', null=True, blank=True, default=0)
    pcm = models.DecimalField(verbose_name='Porcentaje de cumplimiento en el mes', null=True, blank=True, default=0, decimal_places=2, max_digits=10)

    class Meta:
        verbose_name = 'Horas iforme mensual docente'
        verbose_name_plural = 'Horas informes mensuales docente'
        ordering = ('id',)

    def __str__(self):
        return f'{self.informe} hpm: {self.hpm} hem: {self.hem} pcm: {self.pcm}'

class HistorialInforme(ModeloBase):
    informe = models.ForeignKey(InformeMensualDocente, verbose_name=u"Informe mensual", blank=True, null=True, on_delete=models.CASCADE)
    personafirmas = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_INFORME, default=1, blank=True, null=True, verbose_name=u"Estado solicitud")
    archivo = models.FileField(upload_to='informemensualdocente', blank=True, null=True, verbose_name=u'Archivo informe')
    fechafirma = models.DateField(verbose_name=u'Fecha que firma archivo', blank=True, null=True)
    firmado = models.BooleanField(default=False, verbose_name=u"Si el archio ya ha sido firmado o no")

    def __str__(self):
        return u"%s" % self.informe

class HistorialJustificaInforme(ModeloBase):
    informe = models.ForeignKey(InformeMensualDocente, verbose_name=u"Informe mensual", blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateField(verbose_name=u'Fecha que justifica informe', blank=True, null=True)
    descripcion = models.TextField(default='', max_length=1000, blank=True, null=True, verbose_name='Descripción de justificación')
    archivo = models.FileField(upload_to='justificacioninformedocente', blank=True, null=True, verbose_name=u'Archivo justificación')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona justifica', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Historial de justificación informe mensual'
        verbose_name_plural = 'Historial de justificaciones informe mensual'
        ordering = ('id',)

    def __str__(self):
        return u"%s" % self.informe


class PresidenteCurso(ModeloBase):
    carrera = models.ForeignKey(Carrera, verbose_name=u'Carrera',blank=True, null=True, on_delete=models.CASCADE)
    nivel = models.ForeignKey(NivelMalla, verbose_name=u'Nivel',blank=True, null=True, on_delete=models.CASCADE)
    paralelo = models.ForeignKey(Paralelo, verbose_name=u'Paralelo', blank=True, null=True, on_delete=models.CASCADE)
    matricula = models.ForeignKey(Matricula, verbose_name=u'Paralelo',blank=True, null=True, on_delete=models.CASCADE)
    desde = models.DateField(verbose_name=u'Fecha inicio',blank=True, null=True)
    hasta = models.DateField(verbose_name=u'Fecha fin', blank=True, null=True )
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s %s %s' % (self.carrera)

    class Meta:
        verbose_name = u"Presidente de curso"
        verbose_name_plural = u"Presidentes de cursos"


class GrupoTitulacionIC(ModeloBase):
    materia = models.ForeignKey(Materia, verbose_name=u'Materia', blank=True, null=True, on_delete=models.CASCADE)
    tiporubrica = models.IntegerField(choices=TIPO_RUBRICA, default=1, blank=True, null=True, verbose_name=u"Tipo de rubrica de calificacion")

    def __str__(self):
        return u"%s" % self.materia

    def profesores_firmanactivos(self):
        return FirmaGrupoTitulacion.objects.filter(grupofirma__grupo=self, grupofirma__activo=True, status=True)

    def materia_asignada_horarioexamen(self):
        asignada = MateriaAsignada.objects.filter(materia_id=self.materia.id)
        todos_true = all(obj.visiblehorarioexamen for obj in asignada)
        if todos_true:
            return True
        else:
            return False


class GrupoFirma(ModeloBase):
    grupo = models.ForeignKey(GrupoTitulacionIC, verbose_name=u'Grupo', blank=True, null=True, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u"Activo?")
    orden = models.IntegerField(default=1, verbose_name=u'Orden')

    def profesoresgrupo_firman(self):
        return self.firmagrupotitulacion_set.filter(status=True).order_by('orden')

    def totalprofesoresgrupo_firman(self):
        return self.firmagrupotitulacion_set.filter(status=True).count()

    def tieneactafirmada(self, idmateriatitulacion, profesor):
        if MateriaTitulacionFirma.objects.values('id').filter(materiatitulacion_id=idmateriatitulacion, firmadocente__grupofirma=self, firmadocente__profesor=profesor).exists():
            return True
        else:
            return False

    def en_uso(self):
        return self.materiatitulacion_set.values('id').filter(status=True).exists()

class FirmaGrupoTitulacion(ModeloBase):
    grupofirma = models.ForeignKey(GrupoFirma, verbose_name=u'GrupoFirma', blank=True, null=True, on_delete=models.CASCADE)
    profesor = models.ForeignKey(Profesor, verbose_name=u'Profesor', blank=True, null=True, on_delete=models.CASCADE)
    orden = models.IntegerField(default=1, verbose_name=u'Orden')

    def __str__(self):
        return u"%s" % self.profesor

class MateriaTitulacionFirma(ModeloBase):
    materiatitulacion = models.ForeignKey(MateriaTitulacion, verbose_name=u'Materia titulacion', blank=True, null=True, on_delete=models.CASCADE)
    firmadocente = models.ForeignKey(FirmaGrupoTitulacion, verbose_name=u'Firma grupo titulacion', blank=True, null=True, on_delete=models.CASCADE)
    archivofirmado = models.FileField(upload_to='qrcode/actatitulacion', blank=True, null=True, verbose_name=u'Archivo de acta de titulación firmado')
    orden = models.IntegerField(default=1, verbose_name=u'Orden')

    def __str__(self):
        return u"%s" % self.materiatitulacion

class MateriaGrupoTitulacion(ModeloBase):
    grupo = models.ForeignKey(GrupoTitulacionIC, verbose_name=u'Grupo', blank=True, null=True, on_delete=models.CASCADE)
    asignaturamalla = models.ForeignKey(AsignaturaMalla, verbose_name=u'AsignaturaMalla', blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=1000, verbose_name=u'Nombre seccion')
    puntaje = models.IntegerField(default=0, verbose_name=u'puntaje')
    orden = models.IntegerField(default=0, verbose_name=u'Orden')

    def __str__(self):
        return u"%s" % self.grupo

class MateriaTitulacionNota(ModeloBase):
    materiatitulacion = models.ForeignKey(MateriaTitulacion, blank=True, null=True, verbose_name=u'Materia Titulación', on_delete=models.CASCADE)
    materiagrupo = models.ForeignKey(MateriaGrupoTitulacion, blank=True, null=True, verbose_name=u'Materia Grupo', on_delete=models.CASCADE)
    notafinal = models.FloatField(default=0, verbose_name=u"Nota rúbrica")


class SecuenciaInformeMensualActividades(ModeloBase):
    anioejercicio = models.ForeignKey("sagest.AnioEjercicio", verbose_name=u'Año ejercicio', on_delete=models.CASCADE, blank=True, null=True)
    secuencia = models.IntegerField(verbose_name=u'Secuencia', default=0, blank=True, null=True)
    tipo = models.IntegerField(choices=TIPO_INFORME, default=1, blank=True, null=True, verbose_name=u"Tipo de documento")

    def __str__(self):
        return u'%s-%s' % (self.secuencia, self.anioejercicio)

    class Meta:
        verbose_name = u"Secuencia Documento"
        verbose_name_plural = u"Secuencia de los Documentos"
        ordering = ['-id']

    def save(self, *args, **kwargs):
        super(SecuenciaInformeMensualActividades, self).save(*args, **kwargs)

    def set_secuencia(self):
        return self.secuencia

    def get_secuencia_anio(self):
        return f'{self.set_secuencia()}-{self.anioejercicio}'

    def get_anio_secuencia(self):
        return f'{self.anioejercicio}-{self.set_secuencia()}'


class InsumoInformeInternadoRotativo(ModeloBase):
    motivacionjuridica = models.TextField(default='', verbose_name=u'Marco Jurídico', blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name=u'Principal')
    informe = models.IntegerField(choices=TIPO_INFORME, default=1, blank=True, null=True, verbose_name=u"Tipo de documento")

    def __str__(self):
        return f"{self.activo}"

    class Meta:
        verbose_name = u"Insumo de Informe de Internado Rotativo"
        verbose_name_plural = u"Insumos de Informe de Internado Rotativo"
        ordering = ['id']

    def get_firmas(self):
        return self.firmainformemensualactividades_set.filter(informe=self.informe, status=True)


class HistorialInsumoInformeInternadoRotativo(ModeloBase):
    insumo = models.ForeignKey(InsumoInformeInternadoRotativo, blank=True, null=True, verbose_name=u'Insumo', on_delete=models.CASCADE)
    tipoaccion = models.IntegerField(choices=TIPO_ACCION, default=1, blank=True, null=True, verbose_name=u"Tipo de acción")

    def __str__(self):
        return f"{self.get_tipoaccion_display()}"

    class Meta:
        verbose_name = u"Historial Insumo de Informe para Internado Rotativo"
        verbose_name_plural = u"Historial de Insumos de Informe para Internado Rotativo"
        ordering = ['id']

    def get_cantidad_informes_generados(self):
        from sga.models import InformeMensualDocentesPPP
        data = self.insumo.configuracioninformepracticaspreprofesionales_set.filter(status=True).values_list('id', flat=True)
        filtro = Q(configuracion__id__in=data, fecha_creacion__gte=self.fecha_creacion, status=True)
        historial = HistorialInsumoInformeInternadoRotativo.objects.filter(insumo=self.insumo, status=True)
        for i, obj in enumerate(historial):
            if obj.pk == self.pk:
                if i < len(historial) - 1:
                    filtro &= Q(fecha_creacion__lte=historial[i+1].fecha_creacion)
                    break

        return InformeMensualDocentesPPP.objects.filter(filtro).count()


class FirmaInformeMensualActividades(ModeloBase):
    informe = models.IntegerField(choices=TIPO_INFORME, default=1, blank=True, null=True, verbose_name=u"Tipo de documento")
    insumo = models.ForeignKey(InsumoInformeInternadoRotativo, blank=True, null=True, verbose_name=u'Insumo', on_delete=models.CASCADE)
    cargo = models.ForeignKey("sagest.DenominacionPuesto", blank=True, null=True, verbose_name=u'Cargo', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona Responsable', on_delete=models.CASCADE)
    responsabilidad = models.IntegerField(choices=RESPONSABILIDAD_FIRMA, default=1, blank=True, null=True, verbose_name=u"Responsabilidad")

    def __str__(self):
        return "%s - %s" % (self.persona, self.cargo)

    class Meta:
        verbose_name = u"Firma para informe mensual de actividades"
        verbose_name_plural = u"Firmas para informe mensual de actividades"
        ordering = ['id']

class TipoActaFirma(ModeloBase):
    tipoacta = models.ForeignKey('sga.TipoActa', verbose_name=u'Tipo Acta', blank=True, null=True, on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    archivofirmado = models.FileField(upload_to='actasgraduados', blank=True, null=True, verbose_name=u'Archivo firmado')
    orden = models.IntegerField(default=1, verbose_name=u'Orden')
    fechafirma = models.DateField(verbose_name=u'Fecha firma', blank=True, null=True)
    firmado = models.BooleanField(default=False, verbose_name=u"Si el archio ya ha sido firmado o no")
    turnofirmar = models.BooleanField(default=False, verbose_name=u'Persona que le toca firmar')

    def totalfirmados(self):
        return TipoActaFirma.objects.values('id').filter(tipoacta=self.tipoacta, firmado=True, status=True).count()


class TecnicoAsociadoProyectoVinculacion(ModeloBase):
    persona = models.ForeignKey("sga.Persona", blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    persona_elimina = models.ForeignKey("sga.Persona", blank=True, null=True, verbose_name=u'Persona que eliminó el registro', related_name="+", on_delete=models.CASCADE)
    cargo = models.TextField(default='', verbose_name=u'Cargo', blank=True, null=True)
    proyecto = models.ForeignKey("sga.ProyectosInvestigacion", blank=True, null=True, verbose_name=u'Proyecto', on_delete=models.CASCADE)
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Periodo gestion desde')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Periodo gestion hasta')
    activo = models.BooleanField(default=True, verbose_name=u'Estado activo')
    reemplaza_lider = models.BooleanField(default=True, verbose_name=u'¿Reemplaza al lider del proyecto?')

    def __str__(self):
        return u'%s' % self.persona.nombre_completo()


class HistorialInformeMensual(ModeloBase):
    distributivo = models.ForeignKey('sga.ProfesorDistributivoHoras', verbose_name=u'Distributivo', blank=True, null=True, on_delete=models.CASCADE)
    finicioreporte = models.DateField(verbose_name=u'Fecha Inicio', blank=True, null=True)
    ffinreporte = models.DateField(verbose_name=u'Fecha Fin', blank=True, null=True)
    datos_json = models.TextField(verbose_name="Datos en json", null=True, blank=True)
    datos_lista = models.TextField(verbose_name="Datos en lista", null=True, blank=True)
    total_porcentaje = models.DecimalField(default=0.00, max_digits=5, null=True, blank=True, decimal_places=2, verbose_name=u'Total Informe') #ya existia, se lo calculaba

    def json_serializable(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type '{type(obj).__name__}' is not JSON serializable.")

    class Meta:
        verbose_name = u"Historial Porcentaje para informe mensual de actividades"
        verbose_name_plural = u"Historial Porcentaje para informe mensual de actividades"


class ConfiguracionInformeMensualActividades(ModeloBase):
    profesor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name=u"Supervisor/Docente", on_delete=models.CASCADE)
    anio = models.IntegerField(default=0, blank=True, null=True, verbose_name='Año')
    mes = models.IntegerField(choices=MESES_CHOICES, default=0, verbose_name=u'Mes')
    informe = models.IntegerField(choices=TIPO_INFORME, default=0, blank=True, null=True, verbose_name=u"Tipo de documento")
    objetivo = models.TextField(blank=True, null=True, verbose_name=u'Objetivo')
    evidencia = models.ForeignKey("sga.EvidenciaActividadDetalleDistributivo", blank=True, null=True, verbose_name=u"Evidencia de actividad", on_delete=models.CASCADE)
    # insumo = models.ForeignKey("inno.InsumoInformeInternadoRotativo", blank=True, null=True, verbose_name=u"Insumo", on_delete=models.CASCADE) # Esta mal el nombre, se usa para N actividades

    def __str__(self):
        return "%s" % self.profesor.persona

    class Meta:
        verbose_name = u"Configuracion del informe mensual de actividades"
        verbose_name_plural = u"Configuraciones del informe mensual de actividades"

    def get_mes(self): return dict(MESES_CHOICES)[self.mes]

    def total_observaciones(self): return DetalleConfiguracionInformeMensualActividades.objects.filter(status=True, cab=self, tipo=1).count()

    def total_sugerencias(self): return DetalleConfiguracionInformeMensualActividades.objects.filter(status=True, cab=self, tipo=2).count()

    def observaciones(self): return DetalleConfiguracionInformeMensualActividades.objects.filter(status=True, cab=self, tipo=1).order_by('pk')

    def sugerencias(self): return DetalleConfiguracionInformeMensualActividades.objects.filter(status=True, cab=self, tipo=2).order_by('pk')

    def get_antecedentes(self): return DetalleConfiguracionInformeMensualActividades.objects.filter(status=True, cab=self, tipo=3).order_by('pk')

    def get_marcojuridico(self): return DetalleConfiguracionInformeMensualActividades.objects.filter(status=True, cab=self, tipo=4).order_by('pk')

    def get_evidencia(self): return self.evidencia


class DetalleConfiguracionInformeMensualActividades(ModeloBase):
    cab = models.ForeignKey(ConfiguracionInformeMensualActividades, blank=True, null=True, verbose_name=u"Configuracion Informe Mensual Actividades", on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TIPO_INDICADOR_PP, default=0, verbose_name=u'Tipo Indicador')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')

    def __str__(self):
        return '{} ({} - {})'.format(self.tipo, self.cab.mes, self.cab.anio)

    class Meta:
        verbose_name = u"Detalle configuracion del informe mensual de actividades"
        verbose_name_plural = u"Detalle configuracion del informe mensual de actividades"


class UserCriterioRevisorIntegrantes(ModeloBase):
    usuariorevisor = models.ForeignKey(UserCriterioRevisor, blank=True, null=True, verbose_name=u"Usuario revisor", on_delete=models.CASCADE)
    profesor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name=u'Persona que carga la evidencia', on_delete=models.CASCADE)

    def __str__(self):
        return "%s" % self.profesor.persona

    class Meta:
        verbose_name = u"Usuario revisor de actividad y su integrante"
        verbose_name_plural = u"Usuario revisor de actividad y sus integrante"


class TerminosCondiciones(ModeloBase):
    titulo = models.TextField(blank=True, null=True, verbose_name='Título')
    detalle = models.TextField(blank=True, null=True, verbose_name='Descripción')
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    visible = models.BooleanField(default=False, verbose_name=u'¿Visible?')
    legalizar = models.BooleanField(default=False, verbose_name=u'¿Legalizar?')

    def __str__(self):
        return "%s" % self.titulo

    class Meta:
        verbose_name = u"Terminos  y condiciones"
        verbose_name_plural = u"Terminos  y condiciones"

    def en_uso(self):
        return self.terminoscondicionesprofesordistributivo_set.filter(status=True).values('id').exists()


class TerminosCondicionesProfesorDistributivo(ModeloBase):
    distributivo = models.ForeignKey(ProfesorDistributivoHoras, blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    terminos = models.ForeignKey(TerminosCondiciones, blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='terminoscondiciones/profesor', blank=True, null=True, verbose_name=u'Archivo de terminos y condiciones')
    aceptado = models.BooleanField(default=False, verbose_name=u'¿Aceptado?')
    fechaaceptacion = models.DateTimeField(verbose_name=u'Fecha firma', blank=True, null=True)
    legalizado = models.BooleanField(default=False, verbose_name=u'¿Legalizado?')
    fechalegalizacion = models.DateTimeField(verbose_name=u'Fecha firma', blank=True, null=True)

    def __str__(self):
        return "%s" % self.distributivo.profesor.persona

    class Meta:
        verbose_name = u"Terminos  y condiciones personal docente"
        verbose_name_plural = u"Terminos  y condiciones personal docente"

    def firmado(self):
        try:
            from core.firmar_documentos import verificarFirmasPDF
            valido, _, diccionario = verificarFirmasPDF(self.archivo)
            return diccionario['firmasValidas'] if diccionario else False
        except Exception as ex:
            return 0

# class ConfiguracionInformeMensualActividadesEvidenciaActividad(ModeloBase):
#     configuracion = models.ForeignKey(ConfiguracionInformeMensualActividades, blank=True, null=True, verbose_name=u"Configuracion", on_delete=models.CASCADE)
#     profesor = models.ForeignKey(EvidenciaActividadDetalleDistributivo, blank=True, null=True, verbose_name=u"Supervisor/Docente", on_delete=models.CASCADE)


ESTADO_SOLICITUD = (
    (1, u"SOLICITADO"),
    (2, u"APROBADO"),
    (3, u"RECHAZADO"),
)


class SolicitudAperturaClaseVirtual(ModeloBase):
    profesor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name='Profesor', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name='Periodo de solicitud', on_delete=models.CASCADE)
    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name='Fecha inicio')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name='Fecha limite')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    archivo = models.FileField(upload_to='solicitudes/docentes', blank=True, null=True, verbose_name='Archivo solicitud')
    aprobador = models.ForeignKey(Persona, blank=True, null=True, verbose_name='Aprobador', on_delete=models.CASCADE)
    fechaaprobacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha aprobacion o rechazo')
    descripcionaprobador = models.TextField(blank=True, null=True, verbose_name='Descripción del aprobador')
    estadosolicitud = models.IntegerField(choices=ESTADO_SOLICITUD, verbose_name='Estado solicitud', default=1)
    totalperiodo = models.BooleanField(verbose_name='Aplica para todo el periodo', default=True)

    def __str__(self):
        return "{} {} - {} {}".format(self.profesor.persona, self.periodo, self.fechafin.strftime('%Y%m%d_%H%M%S'), self.get_estadosolicitud_display())

    class Meta:
        verbose_name = "Solicitud de apertura de clase virtual"
        verbose_name_plural = "Solicitudes de apertura de clases virtuales"

    def esta_gestionada(self):
        return self.fechaaprobacion and self.aprobador and self.estadosolicitud > 1


class ActaResponsabilidad(ModeloBase):
    malla = models.ForeignKey(Malla, blank=True, null=True, verbose_name='Malla', on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name='Persona', on_delete=models.CASCADE)
    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name='Fecha inicio')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Fin')
    archivoresponsabilidad = models.FileField(upload_to='actas/actasderesponsabilidad', blank=True, null=True,
                               verbose_name='Acta de Responsabilidad')
    observacion = models.TextField(blank=True, null=True, verbose_name='Observación')

class HistorialRecordatorioGenerarInforme(ModeloBase):
    distributivo = models.ForeignKey(ProfesorDistributivoHoras, blank=True, null=True, verbose_name='Distributivo', on_delete=models.CASCADE)
    fechanotificacion = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de notificación')
    fechainicioinforme = models.DateField(verbose_name=u'Fecha inicio informe', blank=True, null=True)
    fechafininforme = models.DateField(verbose_name=u'Fecha fin informe', blank=True, null=True)

    def __str__(self):
        return "{} - {} - {}".format(self.malla, self.persona, self.fechainicio.strftime('%Y%m%d_%H%M%S'))

    class Meta:
        verbose_name = "Acta de responsabilidad"
        verbose_name_plural = "Actas de responsabilidad"


    def __str__(self):
        return "%s" % self.distributivo.profesor.persona

    class Meta:
        verbose_name = "Historial de Recordatorio para Generar Informe"
        verbose_name_plural = "Historial de Recordatorio para Generar Informe"


TIPO_ACTIVIDAD_EVALUACION = (
    (0, 'NINGUNA'),
    (2, "INVESTIGACIÓN"),
    (3, "VINCULACIÓN"),
)


class ParesInvestigacionVinculacion(ModeloBase):
    proceso = models.ForeignKey(ProcesoEvaluativoAcreditacion, blank=True, null=True, verbose_name=u"Proceso", on_delete=models.CASCADE)
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name='Persona', on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TIPO_ACTIVIDAD_EVALUACION, default=0, verbose_name=u'Tipo de actividad a evaluar')
    activo = models.BooleanField(default=False, null=True, blank=True, verbose_name=u'Evaluador activo?')

    def __str__(self):
        return "%s" % self.persona

    class Meta:
        verbose_name = "Evaluador de actividades de docentes"
        verbose_name_plural = "Evaluadores de actividades de docentes"


PREGUNTA_DOCENTE = (
    (1, 'Tomarías nuevamente y/o recomendaría recibir clases con el profesor evaluado'),
)

class RespuestaAlumnoDocente(ModeloBase):
    respuestaevaluacion = models.ForeignKey(RespuestaEvaluacionAcreditacion, blank=True, null=True, verbose_name='RespuestaEvaluacionAcreditacion', on_delete=models.CASCADE)
    id_pregunta = models.IntegerField(choices=PREGUNTA_DOCENTE, default=0, verbose_name=u'Pregunta para saber si contratar o no al docente')
    nombrerespuesta = models.TextField(default='', verbose_name=u'Nombre respuesta')
    comentario = models.TextField(default='', verbose_name=u'Comentario')
    valor = models.FloatField(default=0)

    def __str__(self):
        return "%s" % self.respuestaevaluacion

    class Meta:
        verbose_name = "Respuesta alumno al docente"
        verbose_name_plural = "Respuestas de alumnos al docente"


class EncuestaGrupoEstudianteSeguimientoSilabo(ModeloBase):
    encuestagrupoestudiantes = models.ForeignKey("sga.EncuestaGrupoEstudiantes", blank=True, null=True, verbose_name='EncuestaGrupoEstudiantes', on_delete=models.CASCADE)
    fechainicioencuesta = models.DateField(verbose_name=u'Fecha inicio encuesta', blank=True, null=True)
    fechafinencuesta = models.DateField(verbose_name=u'Fecha fin encuesta', blank=True, null=True)
    categoria = models.BooleanField(default=False, null=True, blank=True, verbose_name=u'Es seguimiento al sílabo?')
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE, blank=True, null=True)
    encuesta_practica = models.BooleanField(default=False, null=True, blank=True, verbose_name=u'Es encuesta para asignaturas practicas?')
    def __str__(self):
        return "%s" % self.encuestagrupoestudiantes

    class Meta:
        verbose_name = "Categorización Encuesta"
        verbose_name_plural = "Categorización Encuestas"

    def cantidad_encuestados(self):
        return self.encuestagrupoestudiantes.inscripcionencuestaestudianteseguimientosilabo_set.only("id").filter(status=True).count()

    def cantidad_respondidos(self):
        return self.encuestagrupoestudiantes.inscripcionencuestaestudianteseguimientosilabo_set.only("id").filter(status=True, respondio=True).count()




class InscripcionEncuestaEstudianteSeguimientoSilabo(ModeloBase):
    encuesta = models.ForeignKey(EncuestaGrupoEstudiantes, on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Encuesta")
    inscripcion = models.ForeignKey("sga.Inscripcion", on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Inscripcion Estudiantes")
    materia = models.ForeignKey("sga.Materia", null=True, blank=True, on_delete=models.CASCADE, verbose_name=u'Materia')
    respondio = models.BooleanField(default=False, verbose_name=u"Respondido")


    def __str__(self):
        if self.es_inscripcion():
            return u'Encuesta: %s - Estudiante: %s' % (self.encuesta, self.inscripcion)
        return u'Encuesta: %s' % self.encuesta

    class Meta:
        verbose_name = u"Muestra de encuesta"
        verbose_name_plural = u"Muestra de encuestas"
        ordering = ['encuesta']

    def es_inscripcion(self):
        return int(null_to_numeric(self.inscripcion_id)) > 0
    #
    # def delete_cache(self):
    #     from sga.templatetags.sga_extras import encrypt
    #     if self.es_inscripcion():
    #         eEncuestas_x_contestar_EnCache = cache.has_key(f"encuesta_silabo_alumnos{encrypt(self.inscripcion_id)}{encrypt(self.materia_id)}")
    #         if not eEncuestas_x_contestar_EnCache is None:
    #             cache.delete(f"encuesta_silabo_alumnos{encrypt(self.inscripcion_id)}{encrypt(self.materia_id)}")
    #         eEncuestas_EnCache = cache.has_key(f"encuesta_silabo_alumnos_contestadas_{encrypt(self.inscripcion_id)}{encrypt(self.materia_id)}")
    #         if not eEncuestas_EnCache is None:
    #             cache.delete(f"encuesta_silabo_alumnos_contestadas_{encrypt(self.inscripcion_id)}{encrypt(self.materia_id)}")

    def delete(self, *args, **kwargs):
        # self.delete_cache()
        super(InscripcionEncuestaEstudianteSeguimientoSilabo, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        # self.delete_cache()
        super(InscripcionEncuestaEstudianteSeguimientoSilabo, self).save(*args, **kwargs)


class RespuestaPreguntaEncuestaSilaboGrupoEstudiantes(ModeloBase):
    inscripcionencuestasilabo = models.ForeignKey(InscripcionEncuestaEstudianteSeguimientoSilabo, on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Inscripcion Encuesta Silabo")
    pregunta = models.ForeignKey("sga.PreguntaEncuestaGrupoEstudiantes", on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Pregunta")
    respuesta = models.TextField(default='', verbose_name=u'Respuesta', blank=True, null=True)
    respuestaporno = models.TextField(default='', verbose_name=u'Respuesta por No', blank=True, null=True)

    def __str__(self):
        return u'Inscripcion Encuesta Silabo: %s - Pregunta: %s - Respuesta: %s' % (self.inscripcionencuestasilabo, self.pregunta, self.respuesta)


ESTADO_CONFIGURACION_PRACTICAS = (
    (1, u"POR DEFINIR"),
    (2, u"HABILITADO"),
    (3, u"DESHABILITADO"),
)

ESTADO_APROBACION = (
    (1, u"PENDIENTE"),
    (2, u'APROBADO'),
    (3, u'RECHAZADO'),
)

TIPO_ACTIVIDAD = (
    (0, u" --- "),
    (1, u"INTRAMURAL"),
    (2, u'EXTRAMURAL'),
)

ROL_ACTIVIDAD = (
    (0, u" --- "),
    (1, u"ASISTENCIAL"),
    (2, u'INVESTIGATIVO'),
    (3, u'EDUCATIVO'),
    (4, u'ADMINISTRATIVO'),
)

ESTADO_REVISION = (
    (1, u"PENDIENTE"),
    (2, u'SOLICITADO'),
    (3, u'REVISADO'),
)

TIPO_DOCUMENTO = (
    (1, u"SIN DEFINIR"),
    (2, u'DISCAPACIDAD'),
    (3, u'ENFERMEDAD'),
    (31, u'FAMILIAR DISCAPACIDAD'),
    (32, u'FAMILIAR ENFERMEDAD'),
    (4, u'EMBARAZO'),
    (5, u"NINIOS MENORES 5AÑOS"),
    (6, u"REQUISITOS"),
)

GRUPO_ORDEN = (
    (1, u"PROMEDIO"),
    (2, u"DISCAPACIDAD"),
    (3, u"EMBARAZO"),
    (4, u"NIÑOS MENORES 5AÑOS"),
    (5, u"TODOS"),
)

class ExtPreInscripcionPracticasPP(ModeloBase):
    preinscripcion = models.ForeignKey(PreInscripcionPracticasPP, blank=True, null=True, verbose_name=u'Pre-inscripción', on_delete=models.CASCADE)
    vinculacion = models.BooleanField(default=False, verbose_name=u"¿Horas completas de Vinculación?")
    finiciopractica = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha inicio prácticas')
    ffinpractica = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha fin prácticas')
    finicioconvocatoria = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha inicio convocatoria')
    ffinconvocatoria = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha fin convocatoria')
    periodoevidencia = models.ForeignKey(CabPeriodoEvidenciaPPP, blank=True, null=True, verbose_name=u"Periodo evidencia", on_delete=models.CASCADE)

    def habilita_eliminar(self):
        return self.finicioconvocatoria <= datetime.now() <= self.ffinconvocatoria

class ResponsableCentroSalud(ModeloBase):
    persona = models.ForeignKey(Persona, verbose_name=u"Persona", on_delete=models.CASCADE)
    asignacionempresapractica = models.ForeignKey('sga.AsignacionEmpresaPractica', verbose_name=u"Asignación de empresa", blank=True, null=True, on_delete=models.CASCADE)
    cargodesempena = models.CharField(default='', blank=True, null=True, max_length=800, verbose_name=u'Cargo que desempeña')
    telefonooficina = models.CharField(default='', blank=True, null=True, max_length=100, verbose_name=u'Teléfono oficina')

    def __str__(self):
        return u'%s - %s' % (self.persona, self.asignacionempresapractica if self.asignacionempresapractica else self.otraempresaempleadora)

    @staticmethod
    def flexbox_query(q, extra=None, limit=10):
        s = q.split(" ")
        if s.__len__() == 2:
            return ResponsableCentroSalud.objects.filter(Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])).distinct()[:limit]
        return ResponsableCentroSalud.objects.filter(Q(persona__nombres__contains=s[0]) | Q(persona__apellido1__contains=s[0]) | Q(persona__apellido2__contains=s[0]) | Q(persona__cedula__contains=s[0])).distinct()[:limit]

    def flexbox_repr(self):
        return self.persona.cedula + " - " + self.persona.nombre_completo_inverso() + " - " + self.persona_id.__str__()

    class Meta:
        verbose_name = u"Responsable Centro Salud"
        verbose_name_plural = u"Responsables Centros Salud"
        unique_together = ('persona',)

    def en_uso(self):
        return self.configuracioninscripcionpracticaspp_set.values_list('id').filter(status=True).exists()

    def save(self, *args, **kwargs):
        self.cargodesempena = self.cargodesempena.upper().strip()
        super(ResponsableCentroSalud, self).save(*args, **kwargs)

class ConfiguracionInscripcionPracticasPP(ModeloBase):
    preinscripcion = models.ForeignKey(PreInscripcionPracticasPP, blank=True, null=True, verbose_name=u'Pre-inscripción', on_delete=models.CASCADE)
    # itinerariomalla = models.ForeignKey(ItinerariosMalla, verbose_name=u"Itinerario malla", blank=True, null=True, on_delete=models.CASCADE)

    itinerariomalla = models.ManyToManyField(ItinerariosMalla, verbose_name=u'Itinerarios malla', blank=True)

    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')
    tutorunemi = models.ForeignKey(Profesor, verbose_name=u"Profesor", blank=True, null=True, on_delete=models.CASCADE)
    supervisor = models.ForeignKey(Profesor, blank=True, null=True, related_name='Supervisorconf_set', verbose_name=u"Supervisor", on_delete=models.CASCADE)
    responsable = models.ForeignKey(ResponsableCentroSalud, blank=True, null=True, verbose_name=u"Responsable", on_delete=models.CASCADE)
    numerohora = models.IntegerField(default=0, verbose_name=u'Numero de Hora')
    cupo = models.IntegerField(default=0, verbose_name=u'Cupos')
    convenio = models.ForeignKey('sga.ConvenioEmpresa', blank=True, null=True, verbose_name='Convenio', on_delete=models.CASCADE)
    tipoinstitucion = models.IntegerField(default=1, choices=TIPO_INSTITUCION, verbose_name=u"Tipo Institucion")
    asignacionempresapractica = models.ForeignKey('sga.AsignacionEmpresaPractica', verbose_name=u"Asignación de empresa", blank=True, null=True, on_delete=models.CASCADE)
    otraempresaempleadora = models.CharField(max_length=600, default='', blank=True, null=True, verbose_name=u"Otra Empresa Empleadora")
    lugarpractica = models.ForeignKey(Canton, verbose_name=u"Lugar practica", blank=True, null=True, on_delete=models.CASCADE)
    dia = models.IntegerField(choices=DIAS_CHOICES, default=0, verbose_name=u'Dia')
    direccion = models.CharField(max_length=600, default='', null=True, blank=True, verbose_name=u"Direccion Empresa")
    periodoppp = models.ForeignKey(CabPeriodoEvidenciaPPP, blank=True, null=True, verbose_name=u"Periodo", on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_CONFIGURACION_PRACTICAS, default=1, verbose_name=u"Estado configuracion practicas pre-profecionales")
    fechainiciooferta = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')
    fechafinoferta = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')

    def __str__(self):
        return "{} - ({} - {}) - {} - {} (Disp. {})".format(self.asignacionempresapractica if self.asignacionempresapractica else self.otraempresaempleadora, self.fechainicio.strftime('%Y/%m/%d'), self.fechafin.strftime('%Y/%m/%d'), self.get_dia_display(), self.get_estado_display(), self.cupos_disponibles())

    class Meta:
        verbose_name = "Configuración de oferta para inscripciónn PracticasPP"
        verbose_name_plural = "Configuraciones de ofertas para inscripciónn PracticasPP"

    def cantidad_inscritos_oferta(self):
        return len(self.historialinscricionoferta_set.values("id").filter(status=True).distinct())

    def inscritos_oferta(self):
        return self.historialinscricionoferta_set.filter(status=True).distinct().order_by('practicasppinscripcion__inscripcion__persona__apellido1')

    def cantidad_total_ofertas(self, preinsc):
        return len(preinsc.configuracioninscripcionpracticaspp_set.filter(status=True, estado=2, fechainiciooferta__lte=datetime.now().date(), fechafinoferta__gte=datetime.now().date()))

    def cantidad_total_ofertas_itinerario(self, preinsc, itinerario):
        return len(preinsc.configuracioninscripcionpracticaspp_set.filter(status=True, itinerariomalla=itinerario, estado=2, fechainiciooferta__lte=datetime.now().date(), fechafinoferta__gte=datetime.now().date()))

    def cupos_disponibles(self):
        cant_inscritos = self.cantidad_inscritos_oferta()
        cupos_disponibles = self.cupo - cant_inscritos
        return cupos_disponibles

    def color_dinamico_cupos(self):
        cupos_ofertados = self.cupo
        cant_inscritos = self.cantidad_inscritos_oferta()
        cupos_disponibles = cupos_ofertados - cant_inscritos
        if cupos_disponibles == 0:
            color = 3
        elif cupos_disponibles <= cupos_ofertados / 2:
            color = 2
        else:
            color = 1
        return color

class ConfiguracionOrdenPrioridadInscripcion(ModeloBase):
    preinscripcion = models.ForeignKey(PreInscripcionPracticasPP, blank=True, null=True, verbose_name=u'Pre-inscripción', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha', blank=True, null=True)
    grupoorden = models.IntegerField(choices=GRUPO_ORDEN, default=0, verbose_name=u"Grupo orden")
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.preinscripcion.__str__()} - {self.get_grupoorden_display()}'

    class Meta:
        verbose_name = "Configuración Orden Prioridad Inscripción"
        verbose_name_plural = "Configuraciones Orden Prioridad Inscripciones"


class OrdenPrioridadInscripcion(ModeloBase):
    configuracionorden = models.ForeignKey(ConfiguracionOrdenPrioridadInscripcion, null=True, blank=True, verbose_name="Configuracion Orden Prioridad Inscripción", on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    orden = models.IntegerField(default=0, verbose_name=u'Orden')
    grupoorden = models.IntegerField(choices=GRUPO_ORDEN, default=0, verbose_name=u"Grupo orden")
    nota = models.FloatField(blank=True, null=True, verbose_name=u'nota')
    etiqueta = models.TextField(blank=True, null=True, verbose_name=u'Etiqueta')
    activo = models.BooleanField(default=True, verbose_name="¿Turno activo?")
    excluirdato = models.TextField(default='', verbose_name=u'Valor', blank=True)

    def __str__(self):
        return f'{self.inscripcion.__str__()} - {self.orden} - {self.get_grupoorden_display()}'

    class Meta:
        verbose_name = "Orden Prioridad Inscripción"
        verbose_name_plural = "Orden Prioridad Inscripciones"

    def obtenerturnoinscripcion(self, grupoorden, preinsc):
        return self.inscripcion.ordenprioridadinscripcion_set.filter(status=True, grupoorden=grupoorden, configuracionorden__preinscripcion=preinsc).last()

    def seleccionturnoanterior(self, grupoorden, configuracionorden, orden, itinerariomalla):
        resultado = OrdenPrioridadInscripcion.objects.filter(status=True, grupoorden=grupoorden, configuracionorden=configuracionorden, orden=orden).last()
        exclusiones = resultado.excluirdato.split(',') if resultado else []
        for e in exclusiones:
            if e and int(e) in list(itinerariomalla):
                return []
        return resultado


class HistorialAsignacionTurno(ModeloBase):
    ordenprioridad = models.ForeignKey(OrdenPrioridadInscripcion, blank=True, null=True, verbose_name=u'Orden Prioridad Inscripción', on_delete=models.CASCADE)
    nota = models.FloatField(blank=True, null=True, verbose_name=u'nota')
    observacion = models.TextField(blank=True, null=True, verbose_name=u'observación')
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.ordenprioridad.inscripcion.__str__()}, {self.fecha_creacion.date()}'

    class Meta:
        verbose_name = "Historial de asignación de orden"
        verbose_name_plural = "Historial de asignaciónes de orden"


class HistorialInscricionOferta(ModeloBase):
    configinscppp = models.ForeignKey(ConfiguracionInscripcionPracticasPP, blank=True, null=True, verbose_name=u'Configuración Inscripción PracticasPP', on_delete=models.CASCADE)
    practicasppinscripcion = models.ForeignKey(PracticasPreprofesionalesInscripcion, blank=True, null=True, verbose_name=u'Practicas Pre profesionales Inscripción', on_delete=models.CASCADE)
    ordenprioridad = models.ForeignKey(OrdenPrioridadInscripcion, blank=True, null=True, verbose_name=u'Orden Prioridad Inscripción', on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')

    def __str__(self):
        return f'{self.practicasppinscripcion.preinscripcion.__str__()}, {self.fecha_creacion.date()}'

    class Meta:
        verbose_name = "Historial de inscrición en la oferta"
        verbose_name_plural = "Historial de inscriciones en las ofertas"


class PracticasPreprofesionalesInscripcionExtensionSalud(ModeloBase):
    practicasppinscripcion = models.ForeignKey(PracticasPreprofesionalesInscripcion, blank=True, null=True, verbose_name=u'Practicas Pre profesionales Inscripción', on_delete=models.CASCADE)
    dia = models.IntegerField(choices=DIAS_CHOICES, default=0, verbose_name=u'Dia')
    responsable = models.ForeignKey(ResponsableCentroSalud, blank=True, null=True, verbose_name=u"Responsable", on_delete=models.CASCADE)
    fechaasigresponsable = models.DateField(verbose_name=u'Fecha Asignación de Responsable', blank=True, null=True)
    configinscppp = models.ForeignKey(ConfiguracionInscripcionPracticasPP, blank=True, null=True, verbose_name=u'Configuración Inscripción PracticasPP', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.practicasppinscripcion.preinscripcion.__str__()}, {self.get_dia_display() if not self.dia == 0 else "NINGUNO"}'

    class Meta:
        verbose_name = "Practicas Preprofesionales Inscripcion Extension"
        verbose_name_plural = "Practicas Preprofesionales Inscripciones Extension"

class PerfilInscripcionExtensionSalud(ModeloBase):
    perfilinscripcion = models.ForeignKey(PerfilInscripcion, blank=True, null=True, verbose_name=u'Perfil Inscripcion', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha', blank=True, null=True)
    estadoaprobacion = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación")
    archivodiscapacidad = models.FileField(upload_to='discapacidad/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo discapacidad')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return u'%s - %s' % (self.perfilinscripcion, self.get_estadoaprobacion_display())

    class Meta:
        verbose_name = u"Perfil Inscripcion Extensión Salud"
        verbose_name_plural = u"Perfiles Inscripciones Extensión Salud"
        ordering = ['perfilinscripcion']

class PersonaDatosFamiliaresExtensionSalud(ModeloBase):
    personafamiliar = models.ForeignKey(PersonaDatosFamiliares, blank=True, null=True, verbose_name=u'Persona familiar', on_delete=models.CASCADE)
    fechaninio = models.DateTimeField(verbose_name=u'Fecha ninio', blank=True, null=True)
    estadoaprobacionninio = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación ninio")
    observacionninio = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación ninio')
    fechadiscapacidad = models.DateTimeField(verbose_name=u'Fecha discapacidad', blank=True, null=True)
    estadoaprobaciondiscapacidad = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación discapacidad")
    observaciondiscapacidad = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación discapacidad')
    # fechaenfermedad = models.DateTimeField(verbose_name=u'Fecha enfermedad', blank=True, null=True)
    # estadoaprobacionenfermedad = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación enfermedad")
    # observacionenfermedad = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación enfermedad')

    def __str__(self):
        return u'%s' % (self.personafamiliar)

    def listado_enfermedades(self):
        return self.enfermedadfamiliarsalud_set.filter(status=True)

    def cantidad_enfermedades_aprobadas(self):
        return len(self.enfermedadfamiliarsalud_set.objects.filter(estadoaprobacion=2, status=True))

    def validar_edad_ninio(self, fecha=datetime.now().date()):
        if self.personafamiliar.nacimiento:
            diferencia = relativedelta(fecha, self.personafamiliar.nacimiento)
            edad_anios = diferencia.years
            edad_meses = diferencia.months
            edad_dias = diferencia.days
            if edad_anios < 5 or (edad_anios == 5 and edad_meses == 0 and edad_dias == 0):
                return True
        return False

    class Meta:
        verbose_name = u"Persona Datos Familiares Extensión Salud"
        verbose_name_plural = u"Personas Datos Familiares Extensión Salud"
        ordering = ['personafamiliar']

class EnfermedadFamiliarSalud(ModeloBase):
    personafamiliarext = models.ForeignKey(PersonaDatosFamiliaresExtensionSalud, blank=True, null=True, verbose_name=u'Persona familiar ext', on_delete=models.CASCADE)
    enfermedad = models.ForeignKey("med.Enfermedad", null=True, blank=True, verbose_name=u'Tipo de Enfermedad', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha', blank=True, null=True)
    archivoenfermedad = models.FileField(upload_to='enfermedad/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo enfermedad')
    estadoaprobacion = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación")
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return u'%s - %s' % (self.personafamiliarext, self.enfermedad)

    def cantidad_aprobadas(self):
        return len(EnfermedadFamiliarSalud.objects.filter(estadoaprobacion=2, status=True))

    class Meta:
        verbose_name = u"Enfermedad Familiar Salud"
        verbose_name_plural = u"Enfermedades Familiares Salud"
        ordering = ['personafamiliarext']

class PersonaDetalleMaternidadExtensionSalud(ModeloBase):
    personamaternidad = models.ForeignKey(PersonaDetalleMaternidad, blank=True, null=True, verbose_name=u'Persona Maternidad', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha', blank=True, null=True)
    estadoaprobacion = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación")
    archivoembarazo = models.FileField(upload_to='embarazo/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo embarazo')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return u'%s - %s' % (self.personamaternidad, self.get_estadoaprobacion_display())

    class Meta:
        verbose_name = u"Persona Detalle Maternidad Extensión Salud"
        verbose_name_plural = u"Personas Detalles Maternidad Extensión Salud"
        ordering = ['personamaternidad']

class PersonaEnfermedadExtensionSalud(ModeloBase):
    personaenfermedad = models.ForeignKey(PersonaEnfermedad, blank=True, null=True, verbose_name=u'Persona Enfermedad', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha', blank=True, null=True)
    estadoaprobacion = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación")
    archivoenfermedad = models.FileField(upload_to='enfermedad/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo enfermedad')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return u'%s - %s' % (self.personaenfermedad, self.get_estadoaprobacion_display())

    class Meta:
        verbose_name = u"Persona Detalle Enfermedad Extensión Salud"
        verbose_name_plural = u"Personas Detalles Enfermedad Extensión Salud"
        ordering = ['personaenfermedad']

class RequisitoPracticappSalud(ModeloBase):
    persona = models.ForeignKey(Persona, blank=True, null=True, verbose_name='Persona', on_delete=models.CASCADE)
    fecha = models.DateTimeField(verbose_name=u'Fecha', blank=True, null=True)
    estadoaprobacion = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación")
    archivo = models.FileField(upload_to='requisitosalud/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return u'%s - %s' % (self.persona, self.get_estadoaprobacion_display())

    class Meta:
        verbose_name = u"Requisito Practica pre profesional Salud"
        verbose_name_plural = u"Requisitos Practicas pre profesionales Salud"
        ordering = ['persona']

class HistorialDocumentosPPPSalud(ModeloBase):
    personaperfilext = models.ForeignKey(PerfilInscripcionExtensionSalud, blank=True, null=True, verbose_name=u'Persona perfil extension', on_delete=models.CASCADE)
    personaenfermedadext = models.ForeignKey(PersonaEnfermedadExtensionSalud, blank=True, null=True, verbose_name=u'Persona Enfermedad extension', on_delete=models.CASCADE)
    personafamiliarext = models.ForeignKey(PersonaDatosFamiliaresExtensionSalud, blank=True, null=True, verbose_name=u'Persona familiar extension', on_delete=models.CASCADE)
    enfermedadfamiliar = models.ForeignKey(EnfermedadFamiliarSalud, blank=True, null=True, verbose_name=u'Enfermedad familiar', on_delete=models.CASCADE)
    personamaternidadext = models.ForeignKey(PersonaDetalleMaternidadExtensionSalud, blank=True, null=True, verbose_name=u'Persona Maternidad extension', on_delete=models.CASCADE)
    personarequisito = models.ForeignKey(RequisitoPracticappSalud, blank=True, null=True, verbose_name=u'Persona Requisito Salud', on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TIPO_DOCUMENTO, default=1, verbose_name=u"Tipo documento")
    fecha = models.DateTimeField(verbose_name=u'Fecha', blank=True, null=True)
    estadoaprobacion = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación")
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona aprueba/valida', on_delete=models.CASCADE)
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        persona = None
        if self.personaperfilext:
            persona = self.personaperfilext
        if self.personafamiliarext:
            persona = self.personafamiliarext
        if self.personamaternidadext:
            persona = self.personamaternidadext
        if self.personarequisito:
            persona = self.personarequisito
        return u'%s - %s (%s)' % (persona, self.get_tipo_display(), self.get_estadoaprobacion_display())

    def genera_notificacion_estudiante(self, ePersona, eEstudiante, idpreins, tab):
        titulo = f'Actualización de datos: {self.get_tipo_display()}'
        cuerpo = f"Estimad{'a' if ePersona.es_mujer() else 'o'} {ePersona.__str__()}, el estudiante {eEstudiante.__str__()} ha actualizado su información de {self.get_tipo_display()} para su validación(Prácticas pre profesionales)."
        eNotificacion = Notificacion(titulo=titulo,
                                     cuerpo=cuerpo,
                                     destinatario=ePersona,
                                     # url=f'/pro_revisionactividadevidencia?action=validardocumentossalud&id={idpreins}&tab={tab}',
                                     url=f'/alu_practicassalud?action=confpreinscripciones',
                                     prioridad=1,
                                     app_label='sga',
                                     fecha_hora_visible=datetime.now() + timedelta(days=2),
                                     tipo=1,
                                     content_type=None,
                                     object_id=None,
                                     )
        eNotificacion.save()

    def genera_notificacion_administrativo(self, eEstudiante, idalu, tab):
        titulo = f'Resultado de validación: {self.get_tipo_display()}'
        estadoaprobacion = 'Aprobado' if int(self.estadoaprobacion) == 2 else 'Rechazado' if int(self.estadoaprobacion) == 3 else 'Pendiente'
        cuerpo = f"Estimad{'a' if eEstudiante.es_mujer() else 'o'} {eEstudiante.__str__()}, se ha validado su información de {self.get_tipo_display()} para las prácticas pre profesionales. Estado: {estadoaprobacion}; Observación: {self.observacion} "
        eNotificacion = Notificacion(titulo=titulo,
                                     cuerpo=cuerpo,
                                     destinatario=eEstudiante,
                                     url=f'/alu_practicassaludinscripcion?action=actualizardatossalud&idalu={idalu}&tab={tab}',
                                     prioridad=1,
                                     app_label='SIE',
                                     fecha_hora_visible=datetime.now() + timedelta(days=2),
                                     tipo=1,
                                     content_type=None,
                                     object_id=None,
                                     )
        eNotificacion.save()

    class Meta:
        verbose_name = u"Historial Documento PPP Saludd"
        verbose_name_plural = u"Historial Documentos PPP Salud"
        ordering = ['personafamiliarext']

class BitacoraActividadEstudiantePpp(ModeloBase):
    practicasppinscripcion = models.ForeignKey(PracticasPreprofesionalesInscripcion, blank=True, null=True, verbose_name=u'Practicas Pre profesionales Inscripcion', on_delete=models.CASCADE)
    nombre = models.TextField(default='', blank=True, null=True, verbose_name=u'Nombre mes de bitacora')
    fechaini = models.DateTimeField(verbose_name=u'Fecha inicio', blank=True, null=True)
    fechafin = models.DateTimeField(verbose_name=u'Fecha fin', blank=True, null=True)
    resultado = models.TextField(default='', blank=True, null=True, verbose_name=u'Producto/Resultado')
    planaccion = models.TextField(default='', blank=True, null=True, verbose_name=u'Plan de acción')
    estadorevision = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u"Estado de revisión")

    def __str__(self):
        return u'%s - %s' % (self.practicasppinscripcion.inscripcion, self.practicasppinscripcion.preinscripcion.preinscripcion)

    def pendientes_revision(self):
        return self.detallebitacoraestudianteppp_set.filter(estadoaprobacion=1, status=True).count()

    def get_detallebitacora(self):
        return self.detallebitacoraestudianteppp_set.filter(status=True)

    def obtener_fechas_por_semana(self):
        # Obtén las fechas desde la base de datos
        try:
            registros = self.detallebitacoraestudianteppp_set.filter(status=True)
            if registros.exists():
                # Encuentra la fecha más temprana y la fecha más tardía
                fecha_inicial = registros.aggregate(Min('fecha'))['fecha__min']
                fecha_final = registros.aggregate(Max('fecha'))['fecha__max']

                # Genera las semanas dentro del rango de fechas, evitando fines de semana
                fechas_por_semana = []
                fecha_actual = fecha_inicial
                while fecha_actual <= fecha_final:
                    # Ignora sábados (día 5) y domingos (día 6)
                    if fecha_actual.weekday() != 5 and fecha_actual.weekday() != 6:
                        fin_semana = min(fecha_actual + timedelta(days=4), fecha_final)
                        fechas_por_semana.append((fecha_actual, fin_semana))
                        fecha_actual = fin_semana + timedelta(days=1)
                    else:
                        fecha_actual += timedelta(days=1)

                return fechas_por_semana
            else:
                return None
        except Exception as ex:
            return None

    def obtener_actividades_por_rol_tipo(self, fecha_inicio, fecha_fin):
        try:
            # Obtener actividades desde la base de datos en el rango de fechas especificado
            registros = self.detallebitacoraestudianteppp_set.filter(status=True, fecha__range=(fecha_inicio, fecha_fin))

            if registros.exists():
                # Estructura para almacenar actividades por rol y tipo
                actividades_por_rol_y_tipo = {}

                for actividad in registros:
                    rol = actividad.get_rol_display()
                    tipo = actividad.get_tipo_display()

                    # Crear una entrada para el rol si no existe
                    if rol not in actividades_por_rol_y_tipo:
                        actividades_por_rol_y_tipo[rol] = {}

                    # Crear una entrada para el tipo si no existe
                    if tipo not in actividades_por_rol_y_tipo[rol]:
                        actividades_por_rol_y_tipo[rol][tipo] = []

                    # Agregar la descripción a la entrada correspondiente
                    actividades_por_rol_y_tipo[rol][tipo].append({
                        'fecha': actividad.fecha,
                        'descripcion': actividad.descripcion,
                        # Agrega otros campos necesarios según tus necesidades
                    })

                return actividades_por_rol_y_tipo
            else:
                return {}
        except Exception as ex:
            return {}

    def obtener_actividades_por_rol(self, fecha_inicio, fecha_fin):
        try:
            registros = self.detallebitacoraestudianteppp_set.filter(status=True, fecha__range=(fecha_inicio, fecha_fin))
            if registros.exists():
                actividades_por_rol = {}
                for actividad in registros:
                    rol = actividad.get_rol_display()
                    if rol not in actividades_por_rol:
                        actividades_por_rol[rol] = []
                    actividades_por_rol[rol].append({
                        'fecha': actividad.fecha,
                        'rol': actividad.get_rol_display(),
                        'descripcion': actividad.descripcion,
                    })
                return actividades_por_rol
            else:
                return {}
        except Exception as ex:
            return {}

    def obtener_actividades_por_tipo(self, fecha_inicio, fecha_fin):
        try:
            registros = self.detallebitacoraestudianteppp_set.filter(status=True, fecha__range=(fecha_inicio, fecha_fin))
            if registros.exists():
                actividades_por_tipo = {}
                for actividad in registros:
                    tipo = actividad.get_tipo_display()
                    if tipo not in actividades_por_tipo:
                        actividades_por_tipo[tipo] = []
                    actividades_por_tipo[tipo].append({
                        'fecha': actividad.fecha,
                        'tipo': actividad.get_tipo_display(),
                        'descripcion': actividad.descripcion,
                    })
                return actividades_por_tipo
            else:
                return {}
        except Exception as ex:
            return {}

    class Meta:
        verbose_name = u"Bitácora de Práctica pre profesional"
        verbose_name_plural = u"Bitácora de Prácticas pre profesionales"
        ordering = ['fechaini']


class DetalleBitacoraEstudiantePpp(ModeloBase):
    bitacorapractica = models.ForeignKey(BitacoraActividadEstudiantePpp, blank=True, null=True, verbose_name=u'Bitacora practicas', on_delete=models.CASCADE)
    titulo = models.TextField(default='', blank=True, null=True, verbose_name=u'Titulo')
    fecha = models.DateTimeField(verbose_name=u'Fecha', blank=True, null=True)
    horainicio = models.TimeField(verbose_name=u'Hora Inicio', blank=True, null=True)
    horafin = models.TimeField(verbose_name=u'Hora Fin', blank=True, null=True)
    tipo = models.IntegerField(choices=TIPO_ACTIVIDAD, default=0, verbose_name=u"Tipo de actividad")
    rol = models.IntegerField(choices=ROL_ACTIVIDAD, default=0, verbose_name=u"Rol de actividad")
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripción')
    link = models.TextField(default='', blank=True, null=True, verbose_name=u'Link')
    archivo = models.FileField(upload_to='bitacoraactividadppp/%Y/%m/%d', blank=True, null=True,  verbose_name=u'archivo de actividad')
    estadoaprobacion = models.IntegerField(choices=ESTADO_APROBACION, default=1, verbose_name=u"Estado de aprobación")
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return u'%s - %s' % (self.bitacorapractica, self.descripcion)

    def download_link(self):
        return self.archivo.url

    class Meta:
        verbose_name = u"Detalle de Bitácora de Prácticas pre profesionales"
        verbose_name_plural = u"Detalles de Bitácora de Prácticas pre profesionales"
        ordering = ['fecha']


class HistorialBitacoraActividadEstudiante(ModeloBase):
    bitacora = models.ForeignKey(BitacoraActividadEstudiantePpp, blank=True, null=True, verbose_name=u'Bitacora practicas', on_delete=models.CASCADE)
    estadorevision = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u"Estado de revisión")
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona aprueba/valida', on_delete=models.CASCADE)

    def __str__(self):
        des = ''
        if d := self.bitacora.practicasppinscripcion.preinscripcion:
            des = d.preinscripcion
        return f"{self.persona} - {des}"

    class Meta:
        verbose_name = u"Historial de bitácora de actividades Ppp"
        verbose_name_plural = u"Historiales de bitácora de actividades Ppp"

class FormatoPracticaPreprofesionalSalud(ModeloBase):
    nombre = models.TextField(default='', blank=True, null=True, verbose_name=u'Nombre formato')
    htmlnombre = models.TextField(default='', blank=True, null=True, verbose_name=u"Nombre del html")
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Carrera')
    itinerariomalla = models.ManyToManyField(ItinerariosMalla, verbose_name=u'Itinerarios malla', blank=True)
    activo = models.BooleanField(default=False, verbose_name="¿Formato activo?")

    def __str__(self):
        return u'%s (%s)' %(self.nombre, 'Activo' if self.activo else 'Inactivo')

    class Meta:
        verbose_name = u"Formato Prácticas pre profesionales Salud"
        verbose_name_plural = u"Formatos Prácticas pre profesionales Salud"
        ordering = ['nombre']

class ItinerarioAsignaturaSalud(ModeloBase):
    itinerariomalla = models.ForeignKey(ItinerariosMalla, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Itinerario Malla')
    asignaturamalla = models.ForeignKey(AsignaturaMalla, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Asignatura Malla')

    def __str__(self):
        return u'%s - %s' %(self.itinerariomalla, self.asignaturamalla)

    class Meta:
        verbose_name = u"Itinerario Asignatura Salud"
        verbose_name_plural = u"Itinerarios Asignaturas Salud"

class EvidenciaFormatoPpp(ModeloBase):
    evidencia = models.ForeignKey(EvidenciaPracticasProfesionales, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Evidencia práctica')
    formato = models.ForeignKey(FormatoPracticaPreprofesionalSalud, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Formato')
    fecha = models.DateTimeField(verbose_name=u'Fecha formato', blank=True, null=True)

    def __str__(self):
        return u'%s - %s - %s' %(self.evidencia.nombre, self.formato, self.fecha.strftime('%Y-%m-%d'))

    class Meta:
        verbose_name = u"Formato de Evidencia Prácticas pre profesionales"
        verbose_name_plural = u"Formatos de Evidencias Prácticas pre profesionales"
        ordering = ['formato', 'fecha']


class SecuenciaEvidenciaSalud(ModeloBase):
    periodoppp = models.ForeignKey(CabPeriodoEvidenciaPPP, blank=True, null=True, verbose_name=u"Periodo", on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    secuenciainforme = models.IntegerField(default=0, verbose_name=u'Secuencia Informe')

    class Meta:
        verbose_name = u"Secuencia de evidencia"
        verbose_name_plural = u"Secuencias de evidencias"

    def save(self, *args, **kwargs):
        super(SecuenciaEvidenciaSalud, self).save(*args, **kwargs)

class UbicacionEmpresaPractica(ModeloBase):
    asignacionempresapractica = models.ForeignKey('sga.AsignacionEmpresaPractica', blank=True, null=True, verbose_name=u'Empresa práctica', on_delete=models.CASCADE)
    latitud = models.FloatField(default=0, blank=True, verbose_name="Latitud")
    longitud = models.FloatField(default=0, null=True, verbose_name="Longitud")
    actual = models.BooleanField(default=False, verbose_name=u"Ubicación Actual")

    def __str__(self):
        return u'%s - Lat: %s | Long: %s' % (self.asignacionempresapractica.nombre, self.latitud, self.longitud)

    def latitudstr(self):
        return str(self.latitud)

    def longitudstr(self):
        return str(self.longitud)

    class Meta:
        verbose_name = u"Ubicación Empresa Práctica"
        verbose_name_plural = u"Ubicación Empresas Prácticass"

class TurnoPractica(ModeloBase):
    turno = models.IntegerField(default=0, verbose_name=u'Turno')
    comienza = models.TimeField(verbose_name=u'Comienza', blank=True, null=True)
    termina = models.TimeField(verbose_name=u'Termina', blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'Comienza: %s - Termina: %s' % (self.comienza, self.termina)

    def nombre_horario(self):
        return self.comienza.strftime("%H:%M") + ' a ' + self.termina.strftime("%H:%M")

    def en_uso(self):
        return self.turnoestudiantepractica_set.values('id').filter(status=True).exists()

    def horas_entre_dos_horas(self):
        try:
            if self.comienza and self.termina:
                comienza_datetime = datetime.combine(datetime.now(), self.comienza)
                termina_datetime = datetime.combine(datetime.now(), self.termina)

                if termina_datetime < comienza_datetime:  # Si termina es anterior a comienza, añade un día
                    termina_datetime += timedelta(days=1)

                diferencia = termina_datetime - comienza_datetime
                return int(round(diferencia.total_seconds() / 3600))
                # return diferencia.total_seconds() / 3600  # Convierte segundos a horas
            else:
                return 0
        except Exception as ex:
            return 0

    class Meta:
        verbose_name = u"Turno Práctica"
        verbose_name_plural = u"Turnos Prácticas"
        unique_together = ('comienza', 'termina',)

class TurnoEstudiantePractica(ModeloBase):
    turno = models.ForeignKey(TurnoPractica, blank=True, null=True, verbose_name=u'Turno Supervision Practica', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u"Carrera", blank=True, null=True, on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=500, blank=True, null=True, verbose_name='Nombre')
    horas = models.IntegerField(blank=True, null=True, verbose_name=u'Horas')
    abreviatura = models.CharField(default='', max_length=100, blank=True, null=True, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    color = models.CharField(default='', max_length=50, blank=True, null=True, verbose_name='Color')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s %s' % (self.nombre, self.turno.nombre_horario())

    def en_uso(self):
        return self.detallesupervisarpracticasalud_set.values('id').filter(status=True).exists()

    class Meta:
        verbose_name = u"Turno Estudiante Práctica"
        verbose_name_plural = u"Turnos Estudiantes Prácticas"

    def save(self, *args, **kwargs):
        if self.color == '#000000':
            self.color = None
        super(TurnoEstudiantePractica, self).save(*args, **kwargs)

class PlanificacionMensualSalud(ModeloBase):
    supervisor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name=u"Supervisor", on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    mes = models.IntegerField(choices=MESES_CHOICES, null=True, blank=True, verbose_name=u'Mes')
    itinerariomalla = models.ForeignKey(ItinerariosMalla, verbose_name=u"Itinerario malla", blank=True, null=True, on_delete=models.CASCADE)
    totalhoras = models.IntegerField(default=0, verbose_name=u"Total horas")
    archivo = models.FileField(upload_to='planificacionmensual/%Y/%m', blank=True, null=True, verbose_name=u'Informe planificacion mensual')

    def get_mes(self): return dict(MESES_CHOICES)[self.mes]

    def __str__(self):
        return u'%s - %s' % (self.get_mes(), self.itinerariomalla.nombre)

    def get_inicio_mes(self):
        _anio, inicio_anio, fin_anio = self.periodo.fin.year, self.periodo.inicio.year, self.periodo.fin.year
        if inicio_anio == fin_anio or self.mes >= self.periodo.inicio.month: _anio = self.periodo.inicio.year
        return date(_anio, self.mes, 1)

    def get_fin_mes(self):
        _anio, inicio_anio, fin_anio = self.periodo.fin.year, self.periodo.inicio.year, self.periodo.fin.year
        if inicio_anio == fin_anio or self.mes >= self.periodo.inicio.month: _anio = self.periodo.inicio.year
        ultimo_dia = calendar.monthrange(_anio, self.mes)[1]
        return date(_anio, self.mes, ultimo_dia)

    def en_uso(self):
        return self.detalleplanificacionmensualsalud_set.values_list('id').filter(status=True).exists()

    def get_estado_aprobacion(self):
        return self.estadoevidenciasalud_set.filter(status=True).first()

    class Meta:
        verbose_name = u"Estudiante Supervisar Practica Salud"
        verbose_name_plural = u"Estudiantes Supervisar Practicas Salud"


class InformePlanificacionSemanalSalud(ModeloBase):
    planificacionmensual = models.ForeignKey(PlanificacionMensualSalud, blank=True, null=True, verbose_name='Planificacion Mensual Salud', on_delete=models.CASCADE)
    nombre = models.TextField(default='', blank=True, null=True, verbose_name=u'Nombre semana')
    numerosemana = models.IntegerField(blank=True, null=True, verbose_name=u"Numero de semana")
    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha inicio')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha fin')
    archivo = models.FileField(upload_to='planificacionsemanal/%Y/%m', blank=True, null=True, verbose_name=u'Informe planificacion semanal')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observacion')

    def __str__(self):
        return u'%s %s' % (self.planificacionmensual, self.nombre)

    class Meta:
        verbose_name = u"Informe Planificación Semanal Salud"
        verbose_name_plural = u"Informes Planificación Semanales Salud"

class DetallePlanificacionMensualSalud(ModeloBase):
    planificacionmensual = models.ForeignKey(PlanificacionMensualSalud, blank=True, null=True, verbose_name='Planificacion Mensual Salud', on_delete=models.CASCADE)
    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')
    silabosemanal = models.ForeignKey(SilaboSemanal, blank=True, null=True, verbose_name=u'silabo semanal', on_delete=models.CASCADE)
    numerosemana = models.IntegerField(blank=True, null=True, verbose_name=u"Numero de semana")
    tema = models.ForeignKey(TemaUnidadResultadoProgramaAnalitico, blank=True, null=True, verbose_name=u'Tema Unidad Resultado Programa Analitico', on_delete=models.CASCADE)
    descripciontema = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripcion tema')
    objetivo = models.TextField(default='', blank=True, null=True, verbose_name=u'Objetivo')
    enfoque = models.TextField(default='', blank=True, null=True, verbose_name=u'Enfoque')
    evaluacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Evaluacion')
    horas = models.IntegerField(default=0, verbose_name=u"Cantidad de horas")

    def __str__(self):
        return u'%s %s' % (self.planificacionmensual, self.tema)

    def descripcion_detalle(self):
        return u'%s (%s | %s)' % (self.descripciontema, self.fechainicio.strftime('%Y-%m-%d'), self.fechafin.strftime('%Y-%m-%d'))
    
    def lista_subtemas(self):
        return self.detalletemaplanificacionmensualsalud_set.filter(status=True, subtema__isnull=False)

    def lista_subtemas_all(self):
        return self.detalletemaplanificacionmensualsalud_set.filter(status=True)

    def lista_subtemas_adicional(self):
        return self.detalletemaplanificacionmensualsalud_set.filter(status=True, subtemaadicional__isnull=False)

    def horas_semanales(self, numerosemana):
        registros = DetallePlanificacionMensualSalud.objects.filter(status=True, numerosemana=numerosemana)
        return {'horasemana':registros.first().horas if registros else 0, 'cantidadsemana':registros.count()}

    class Meta:
        verbose_name = u"Detalle Planificación Mensual Salud"
        verbose_name_plural = u"Detalles Planificación Mensual Salud"

class DetalleTemaPlanificacionMensualSalud(ModeloBase):
    detalleplanificacionmensual = models.ForeignKey(DetallePlanificacionMensualSalud, blank=True, null=True, verbose_name='Detalle Planificacion Mensual Salud', on_delete=models.CASCADE)
    subtema = models.ForeignKey(DetalleSilaboSemanalSubtema, blank=True, null=True, verbose_name=u'Sub Tema Unidad Resultado Programa Analitico', on_delete=models.CASCADE)
    descripcionsubtema = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripcion Sub tema')
    subtemaadicional = models.ForeignKey(SubTemaAdicionalesSilabo, blank=True, null=True, verbose_name=u'Sub Tema Adicional Unidad Resultado Programa Analitico', on_delete=models.CASCADE)
    descripcionsubtemaadicional = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripcion Sub tema adicional')

    def __str__(self):
        return u'%s %s' % (self.detalleplanificacionmensual.tema, self.subtema if self.subtema else self.subtemaadicional)

    class Meta:
        verbose_name = u"Detalle Tema Planificación Mensual Salud"
        verbose_name_plural = u"Detalles Tema Planificación Mensual Salud"

class SupervisarDocentePracticaSalud(ModeloBase):
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name='Periodo de solicitud', on_delete=models.CASCADE)
    supervisor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name=u"Supervisor", on_delete=models.CASCADE)
    empresapractica = models.ForeignKey('sga.AsignacionEmpresaPractica', verbose_name=u"Asignación de empresa", blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name='Fecha')

    def __str__(self):
        return u'%s - %s' % (self.supervisor.persona, self.empresapractica.nombre)

    def en_uso(self):
        return self.estudiantesupervisarpracticasalud_set.values_list('id').filter(status=True).exists()

    def listado_estudiantes_supervisar(self):
        return self.estudiantesupervisarpracticasalud_set.filter(status=True)

    class Meta:
        verbose_name = u"Supervisar Docente Práctica Salud"
        verbose_name_plural = u"Supervisar Docente Prácticas Salud"

class EstudianteSupervisarPracticaSalud(ModeloBase):
    supervisarpractica = models.ForeignKey(SupervisarDocentePracticaSalud, blank=True, null=True, verbose_name='Supervisar Docente Practica Salud', on_delete=models.CASCADE)
    practicappp = models.ForeignKey(PracticasPreprofesionalesInscripcion, blank=True, null=True, verbose_name=u'Practica Pre profesional Inscripción', on_delete=models.CASCADE)
    cargodepartamentoest = models.TextField(default='', blank=True, null=True, verbose_name=u"Cargo / Departamento")

    def __str__(self):
        return u'%s - %s' % (self.supervisarpractica, self.practicappp.inscripcion.persona)

    def en_uso(self):
        return self.detallesupervisarpracticasalud_set.values_list('id').filter(status=True).exists()

    def listado_registros_supervisar(self):
        return self.detallesupervisarpracticasalud_set.filter(status=True).order_by('-fecha')

    def metahoras(self, fi, ff):
        try:
            from sga.templatetags.sga_extras import diaisoweekday
            diaacademico = self.practicappp.practicaspreprofesionalesinscripcionextensionsalud_set.filter(status=True).first().dia
            diasemana = ['LU', 'MA', 'MI', 'JU', 'VI', 'SA', 'DO']
            listadiasmes = []
            fecha_actual = fi
            while fecha_actual <= ff:
                if not diasemana[diaisoweekday(fecha_actual) - 1] in [diasemana[diaacademico - 1], 'SA', 'DO']:
                    listadiasmes.append(fecha_actual)
                fecha_actual += timedelta(days=1)
            return len(listadiasmes) * 8
        except Exception as ex:
            return 0

    def totalhoras(self, fi, ff):
        suma_horas = self.detallesupervisarpracticasalud_set.filter(status=True, fecha__gte=fi, fecha__lte=ff).exclude(~Q(turno__abreviatura='')).aggregate(total_horas=Sum('turno__horas'))
        return suma_horas['total_horas'] or 0

    class Meta:
        verbose_name = u"Estudiante Supervisar Practica Salud"
        verbose_name_plural = u"Estudiantes Supervisar Practicas Salud"

class DetalleSupervisarPracticaSalud(ModeloBase):
    estudiantesupervisar = models.ForeignKey(EstudianteSupervisarPracticaSalud, blank=True, null=True, verbose_name='Estudiante Supervisar Practica Salud', on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name='Fecha')
    hora = models.TimeField(blank=True, null=True, verbose_name=u'Hora')
    turno = models.ForeignKey(TurnoEstudiantePractica, blank=True, null=True, verbose_name=u'Turno Supervision Practica', on_delete=models.CASCADE)
    detalletemapm = models.ForeignKey(DetallePlanificacionMensualSalud, blank=True, null=True, verbose_name='Detalle Planificacion Mensual Salud', on_delete=models.CASCADE)
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return u'%s %s' % (self.estudiantesupervisar, self.turno)

    class Meta:
        verbose_name = u"Detalle Supervisar Practica Salud"
        verbose_name_plural = u"Detalles Supervisar Practicas Salud"

class EstadoEvidenciaSalud(ModeloBase):
    class EstadoAprobacion(models.IntegerChoices):
        DEFAULT = 0, u'PENDIENTE'
        A = 1, u'GENERADO'
        B = 2, u'SOLICITADO'
        C = 3, u'APROBADA'
        D = 4, u'RECHAZADA'
        E = 5, u'FIRMA_EN_CURSO'
        F = 6, u'FIRMADA'
        G = 7, u'LEGALIZADA'
    planificacionmensual = models.ForeignKey(PlanificacionMensualSalud, blank=True, null=True, verbose_name='Planificación Mensual Salud', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=EstadoAprobacion.choices, default=EstadoAprobacion.DEFAULT, verbose_name=u'Estado aprobación')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona aprueba/rechaza', on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name='Fecha aprobación')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')
    archivorespaldo = models.FileField(upload_to='respaldoactividadsalud/%Y/%m', blank=True, null=True, verbose_name=u'Respaldo archivo actividad salud')

    firma_tutor = models.BooleanField(default=False, verbose_name=u'Firma Tutor')
    firma_coordinador = models.BooleanField(default=False, verbose_name=u'Firma Coordinador')
    firma_docentes = models.BooleanField(default=False, verbose_name=u'Firma Docentes')
    firma_director = models.BooleanField(default=False, verbose_name=u'Firma Director')
    firma_decano = models.BooleanField(default=False, verbose_name=u'Firma Decano')

    def __str__(self):
        return f'{self.nombre_evidencia()} - {self.get_estado_display()}'

    def nombre_evidencia(self):
        nombre = ''
        if null_to_numeric(self.planificacionmensual_id) > 0:
            nombre = f'PLANIFICACIÓN MENSUAL - {self.planificacionmensual.supervisor}'
        return nombre

    def indicador_evidencia(self):
        indicador = None
        if null_to_numeric(self.planificacionmensual_id) > 0:
            indicador = 1
        return indicador

    def todas_firmas_docentes(self):
        firmas = self.firmaevidenciadocente_set.filter(status=True)
        for firma in firmas:
            if not firma.firmado:
                return False
        return True

    def actualizar_estado(self):
        if not self.firma_coordinador:
            self.estado = 2
        elif self.firma_coordinador and self.estado == 2:
            self.estado = 3
        elif self.firma_coordinador and self.todas_firmas_docentes() and self.firma_director and self.firma_decano:
            self.estado = 6
        elif self.firma_coordinador and self.todas_firmas_docentes() and (self.firma_director or self.firma_decano):
            if self.indicador_evidencia() == 1 and self.firma_director: #legaliza el director la planificacion mensual
                self.estado = 7
            elif self.indicador_evidencia() == 2 and self.firma_director: #legaliza el decano la xxxx xxxxx
                self.estado = 7
            else: self.estado = 5
        elif self.firma_coordinador and (not self.todas_firmas_docentes() or not (self.firma_director and self.firma_decano)):
            self.estado = 5
        else:
            self.estado = 3 # o el estado que corresponda según el flujo de trabajo
        self.save()

    def rol_firma(self, rol, docente_id=None):
        if rol == 'coordinador':
            self.firma_coordinador = True
        elif rol == 'docente' and docente_id:
            firma_docente = self.firmaevidenciadocente_set.filter(status=True, docente_id=docente_id).first()
            if firma_docente:
                firma_docente.firmado = True
                firma_docente.save()
            # else:
            #     FirmaEvidenciaDocente.objects.create(evidencia_estado=self, docente_id=docente_id, firmado=True)
        elif rol == 'director':
            self.firma_director = True
        elif rol == 'decano':
            self.firma_decano = True

        self.actualizar_estado()
        self.save()

    def es_docente(self, persona_id, tipo, periodo_id):
        fecha = datetime.now().date()
        anio = fecha.year
        es_docente, eItinerario = False, None
        periodo = Periodo.objects.get(pk=periodo_id)
        fecha_inicio, fecha_fin = periodo.inicio, periodo.fin
        if tipo == 1:
            eItinerario = self.planificacionmensual.itinerariomalla
            fecha_inicio = date(anio, self.planificacionmensual.mes, 1)
            fecha_fin = date(anio, self.planificacionmensual.mes, calendar.monthrange(anio, self.planificacionmensual.mes)[1])
        if eItinerario:
            asignaturas = eItinerario.itinerarioasignaturasalud_set.filter(status=True)
            for a in asignaturas:
                materia = a.asignaturamalla.materia_set.filter(status=True, nivel__periodo=periodo
                                                               , silabo__silabosemanal__fechafinciosemana__gte=fecha_inicio,
                                                               silabo__silabosemanal__fechainiciosemana__lte=fecha_fin
                                                               ).first()
                docente = materia.profesor_principal()
                if docente: es_docente = docente.persona_id == persona_id
        return es_docente

    def es_coordinador(self, persona_id):
        es_coordinador = False
        coordinadorpp = DistributivoPersona.objects.get(denominacionpuesto_id=169, estadopuesto_id=1)
        if coordinadorpp: es_coordinador = coordinadorpp.persona_id == persona_id
        return es_coordinador

    def es_decano(self, coordinacion_id, persona_id, periodo_id):
        es_decano = False
        decano = ResponsableCoordinacion.objects.filter(coordinacion_id=coordinacion_id, periodo_id=periodo_id, tipo=1).first()
        if decano: es_decano = decano.persona_id == persona_id
        return es_decano


    def es_directorcarrera(self, carrera_id, persona_id, periodo_id):
        es_directorcarrera = False
        directorcarrera = CoordinadorCarrera.objects.filter(carrera_id=carrera_id, tipo=3, periodo_id=periodo_id, status=True).first()
        if directorcarrera: es_directorcarrera = directorcarrera.persona_id == persona_id
        return es_directorcarrera

    class Meta:
        verbose_name = u'Estado evidencia Salud'
        verbose_name_plural = u'Estados de evidencias de Salud'

    def save(self, *args, **kwargs):
        super(EstadoEvidenciaSalud, self).save(*args, **kwargs)

class FirmaEvidenciaDocente(ModeloBase):
    evidencia_estado = models.ForeignKey(EstadoEvidenciaSalud, blank=True, null=True, verbose_name='Estado Evidencia Salud', on_delete=models.CASCADE)
    docente = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona firma', on_delete=models.CASCADE)
    firmado = models.BooleanField(default=False)

    def __str__(self):
        return u'%s %s' % (self.evidencia_estado, self.docente)

    class Meta:
        verbose_name = u"Firma Evidencia Docente"
        verbose_name_plural = u"Firmas de evidencias Docente"

class DetalleEstadoEvidenciaSalud(ModeloBase):
    class EstadoAprobacion(models.IntegerChoices):
        DEFAULT = 0, u'PENDIENTE'
        A = 1, u'GENERADO'
        B = 2, u'SOLICITADO'
        C = 3, u'APROBADA'
        D = 4, u'RECHAZADA'
        E = 5, u'FIRMADA'
        F = 6, u'FIRMADA'
        G = 7, u'LEGALIZADA'
    evidencia_estado = models.ForeignKey(EstadoEvidenciaSalud, blank=True, null=True, verbose_name='Estado Evidencia Salud', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=EstadoAprobacion.choices, default=EstadoAprobacion.DEFAULT, verbose_name=u'Estado aprobación')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona aprueba/rechaza', on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name='Fecha aprobacion')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')

    def __str__(self):
        return  f'{self.evidencia_estado.nombre_evidencia()} - {self.estado}'

    class Meta:
        verbose_name = u'Detalle estado evidencia Salud'
        verbose_name_plural = u'Detalles estado de evidencia de Salud'

    def save(self, *args, **kwargs):
        super(DetalleEstadoEvidenciaSalud, self).save(*args, **kwargs)

class DetalleEvaluacionComponentePeriodo(ModeloBase):
    evaluacioncomponenteperiodo = models.ForeignKey(EvaluacionComponentePeriodo, blank=True, null=True, verbose_name='Evaluacion Componente Periodo', on_delete=models.CASCADE)
    actividad = models.ForeignKey(EvaluacionAprendizajeComponente, blank=True, null=True, verbose_name='Evaluacion Aprendizaje Componente', on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=0, verbose_name=u'Cantidad')
    obligatorio = models.BooleanField(default=False, verbose_name=u"Estado obligatorio")

    def __str__(self):
        return f"{self.evaluacioncomponenteperiodo.__str__()} - {self.actividad.__str__()} - {self.cantidad.__str__()} - {'Obligatorio' if self.obligatorio else ''}"

    def validapendientedetalle(self, silabo, componente):
        if silabo.materia.planificacionclasesilabo_materia_set.filter(status=True).exists():
            planificacion = silabo.materia.planificacionclasesilabo_materia_set.filter(status=True)[0]
            listadosemanas = planificacion.tipoplanificacion.planificacionclasesilabo_set.values_list('semana', flat=False).filter(parcial=componente.parcial, status=True)
            registros = EvaluacionAprendizajeSilaboSemanal.objects.filter(evaluacionaprendizaje__componente=componente.componente_id, silabosemanal__silabo_id=silabo,
                                                                     silabosemanal__silabo__status=True, silabosemanal__numsemana__in=listadosemanas,
                                                                     silabosemanal__status=True, tipoactividadsemanal=1, status=True)

            noobligatorio = componente.detalleevaluacioncomponenteperiodo_set.filter(status=True, obligatorio=False).values_list('actividad_id', flat=True).exclude(actividad=self.actividad)
            _obligatorio = componente.detalleevaluacioncomponenteperiodo_set.filter(status=True, obligatorio=True).values_list('actividad_id', flat=True)
            actividades_noobligatorio = registros.filter(evaluacionaprendizaje_id__in=noobligatorio).count()
            actividades_obligatorio = registros.filter(evaluacionaprendizaje_id__in=_obligatorio).count()
            resgistroactividad = registros.filter(evaluacionaprendizaje=self.actividad).count()
            if self.obligatorio: return resgistroactividad
            else:
                if not resgistroactividad > 0 and actividades_noobligatorio >= self.cantidad:
                    return -1
                elif resgistroactividad > 0:
                    return resgistroactividad
                elif actividades_obligatorio >= componente.cantidad:
                    return -1
                elif not resgistroactividad > 0 and not actividades_noobligatorio > 0:
                    return resgistroactividad
                elif not resgistroactividad > 0 or not actividades_noobligatorio >= self.cantidad:
                    return resgistroactividad
                else:
                    return -1
        else:
            return 0

    class Meta:
        verbose_name = u'Detalle Evaluacion Componente Periodo'
        verbose_name_plural = u'Detalles Evaluaciones Componentes Periodo'

class FormatoPlanificacionRecurso(ModeloBase):
    descripcion = models.CharField(max_length=250, default='', verbose_name=u'Descripción')
    archivo = models.FileField(upload_to='formatoplanificacion/%Y/%m', blank=True, null=True, verbose_name=u'Archivo del formato')
    modalidad = models.ManyToManyField(Modalidad, verbose_name=u'Modalidad', blank=True)
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s - %s' % (self.descripcion, 'ACTIVO' if self.activo else 'INACTIVO')

    class Meta:
        verbose_name = u"Formato planificacion recurso"
        verbose_name_plural = u"Formatos de planificacion recurso"

    def tipo_archivo(self):
        if self.archivo and self.archivo.name.endswith('.pdf'):
            return 'pdf'
        elif self.archivo and self.archivo.name.endswith(('.jpg', '.jpeg', '.png')):
            return 'image'
        else:
            return 'other'

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(FormatoPlanificacionRecurso, self).save(*args, **kwargs)

class AsistenciaMatriculadoPeriodo(ModeloBase):
    class IndicadorAsistencia(models.IntegerChoices):
        DEFAULT = 0, u'NINGUNA'
        A = 1, u'ASISTENCIAS DE MATRICULADOS POR FECHA CORTE'
        B = 2, u'ASISTENCIAS DE MATRICULADOS POR TURNO CORTE'
    indicador = models.IntegerField(choices=IndicadorAsistencia.choices, default=IndicadorAsistencia.DEFAULT, verbose_name=u'Indicador Asistencia')
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name='Periodo de solicitud', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u"Carrera", blank=True, null=True, on_delete=models.CASCADE)
    sesion = models.ForeignKey(Sesion, blank=True, null=True, verbose_name=u'Sesión', on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name='Fecha')
    turno = models.ForeignKey(Turno, blank=True, null=True, verbose_name=u'Turno', on_delete=models.CASCADE)
    docentesturno = models.IntegerField(default=0, verbose_name=u'Docentes turno')
    matriculados = models.IntegerField(default=0, verbose_name=u'Matriculados')
    asistieron = models.IntegerField(default=0, verbose_name=u'Asistieron')
    noasistieron = models.IntegerField(default=0, verbose_name=u'No Asistieron')

    def __str__(self):
        return u'%s - %s - %s - %s' % (self.carrera.nombre, self.sesion.nombre, self.fecha.__str__(), self.matriculados)

    class Meta:
        verbose_name = u"Asistencia Matriculado Periodo"
        verbose_name_plural = u"Asistencia Matriculados del periodo"

    def save(self, *args, **kwargs):
        super(AsistenciaMatriculadoPeriodo, self).save(*args, **kwargs)

class DisertacionFechaPlanificacion(ModeloBase):
    fecha = models.DateField(verbose_name=u'Fecha examen')
    sede = models.ForeignKey(SedeVirtual, verbose_name=u'Sede', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, verbose_name=u'Periodo', on_delete=models.CASCADE)

    def __str__(self):
        return f"Periodo: {self.periodo.__str__()} - Fecha: {self.fecha.__str__()} - {self.sede.__str__()}"

    class Meta:
        verbose_name = u'Fecha de disertación de planificación'
        verbose_name_plural = u'Fechas de disertación de planificación'
        ordering = ('periodo', 'fecha', 'sede')
        unique_together = ('fecha', 'sede', 'periodo')

    def enuso(self):
        return self.disertacionturnoplanificacion_set.values("id").exists()

    def es_virtual(self):
        return self.sede_id == 11

    def save(self, *args, **kwargs):
        super(DisertacionFechaPlanificacion, self).save(*args, **kwargs)


class DisertacionTurnoPlanificacion(ModeloBase):
    fechaplanificacion = models.ForeignKey(DisertacionFechaPlanificacion, verbose_name=u'Fecha', on_delete=models.CASCADE)
    horainicio = models.TimeField(verbose_name=u'Hora Inicio')
    horafin = models.TimeField(verbose_name=u'Hora Fin')

    def __str__(self):
        return f"{self.fechaplanificacion.__str__()} - Tiempo: {self.horainicio.__str__()} - {self.horafin.__str__()}"

    class Meta:
        verbose_name = u'Horario de disertación de planificación'
        verbose_name_plural = u'Horarios de disertación de planificación'
        ordering = ('horainicio', 'horafin')
        unique_together = ('fechaplanificacion', 'horainicio', 'horafin')

    def enuso(self):
        return self.aulaplanificacionsedevirtualexamen_set.values("id").exists()

    def save(self, *args, **kwargs):
        super(DisertacionTurnoPlanificacion, self).save(*args, **kwargs)


class DisertacionAulaPlanificacion(ModeloBase):
    turnoplanificacion = models.ForeignKey(DisertacionTurnoPlanificacion, verbose_name=u'Horario', on_delete=models.CASCADE)
    aula = models.ForeignKey(LaboratorioVirtual, verbose_name=u'Aula sede', on_delete=models.CASCADE)
    # supervisor = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Supervisor', related_name='+', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.turnoplanificacion.__str__()} - Aula: {self.aula.__str__()}"

    class Meta:
        verbose_name = u'Aula de disertación de planificación'
        verbose_name_plural = u'Aulas de disertación de planificación'
        ordering = ('turnoplanificacion', 'aula')
        unique_together = ('turnoplanificacion', 'aula')

    def save(self, *args, **kwargs):
        super(DisertacionAulaPlanificacion, self).save(*args, **kwargs)


class DisertacionGrupoPlanificacion(ModeloBase):
    class Grupos(models.IntegerChoices):
        DEFAULT = 0, u'NINGUNO'
        A = 1, u'GRUPO A'
        B = 2, u'GRUPO B'
        C = 3, u'GRUPO C'
        D = 4, u'GRUPO D'
        E = 5, u'GRUPO E'
        F = 6, u'GRUPO F'
        G = 7, u'GRUPO G'
        H = 8, u'GRUPO H'
        I = 9, u'GRUPO I'
        J = 10, u'GRUPO J'
        K = 11, u'GRUPO K'
        L = 12, u'GRUPO L'
        M = 13, u'GRUPO M'
        N = 14, u'GRUPO N'
    aulaplanificacion = models.ForeignKey(DisertacionAulaPlanificacion, verbose_name=u'Aula planificación', on_delete=models.CASCADE)
    grupo = models.IntegerField(choices=Grupos.choices, default=Grupos.DEFAULT, verbose_name=u'Grupo')
    responsable = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Aplicador', related_name='+', on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, verbose_name=u'MateriaAsignada', on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativo, verbose_name=u'Modelo evaluativo', on_delete=models.CASCADE)
    cupo = models.IntegerField(default=0, verbose_name=u'Cupo')

    def __str__(self):
        return f"{self.aulaplanificacion.__str__()} - Materia: {self.materia.__str__()}"

    class Meta:
        verbose_name = u'Grupo de disertación de planificación'
        verbose_name_plural = u'Grupos de disertación de planificación'
        ordering = ('aulaplanificacion', 'materia', 'detallemodeloevaluativo')
        unique_together = ('aulaplanificacion', 'materia', 'detallemodeloevaluativo', 'grupo')

    def tribunal(self):
        return self.disertaciontribunalplanificacion_set.filter(status=True)

    def estudiantes(self):
        return self.disertacionmateriaasignadaplanificacion_set.filter(status=True)

    def save(self, *args, **kwargs):
        super(DisertacionGrupoPlanificacion, self).save(*args, **kwargs)


class DisertacionTribunalPlanificacion(ModeloBase):
    grupoplanificacion = models.ForeignKey(DisertacionGrupoPlanificacion, verbose_name=u'Grupo planificación', on_delete=models.CASCADE)
    responsable = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Responsable', related_name='+', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.grupoplanificacion.__str__()} - Tribunal: {self.responsable.__str__()}"

    class Meta:
        verbose_name = u'Tribunal de disertación de planificación'
        verbose_name_plural = u'Tribunales de disertación de planificación'
        ordering = ('grupoplanificacion', 'responsable')
        unique_together = ('grupoplanificacion', 'responsable')

    def save(self, *args, **kwargs):
        super(DisertacionTribunalPlanificacion, self).save(*args, **kwargs)


class DisertacionMateriaAsignadaPlanificacion(ModeloBase):
    grupoplanificacion = models.ForeignKey(DisertacionGrupoPlanificacion, verbose_name=u'Grupo planificación', on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey(MateriaAsignada, verbose_name=u'MateriaAsignada', on_delete=models.CASCADE)
    asistencia = models.BooleanField(default=False, verbose_name=u'Asistencia al examen')
    fecha_asistencia = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de la asistencia al aexamen')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name=u'Observación')
    calificacion = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Calificación')

    def __str__(self):
        return f"{self.grupoplanificacion.__str__()} - MateriaAsignada: {self.materiaasignada.__str__()}"

    class Meta:
        verbose_name = u'MateriaAsignada de disertación de planificación'
        verbose_name_plural = u'MateriaAsignadas de disertación de planificación'
        ordering = ('grupoplanificacion', 'materiaasignada',)
        unique_together = ('materiaasignada', )

    def save(self, *args, **kwargs):
        super(DisertacionMateriaAsignadaPlanificacion, self).save(*args, **kwargs)


class CapEncuestaPeriodo(ModeloBase):
    periodo = models.ForeignKey('sga.CapPeriodoDocente', verbose_name=u'Periodo', on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=300, verbose_name='Nombre')
    # descripcion = models.TextField(default='', blank=True, null=True, verbose_name='Descripción')
    # valoracion = models.IntegerField(default=0, verbose_name=u"Cantidad de estrellas")
    isVigente = models.BooleanField(default=False, verbose_name=u'¿Está Vigente?')

    def __str__(self):
        return u"%s" % self.nombre

    class Meta:
        verbose_name = u'Encuesta satisfacción de capacitación docente'
        verbose_name_plural = u'Encuestas satisfacción de capacitación docente'
        unique_together = ('periodo', 'nombre',)

    def en_uso(self):
        return CapPreguntaEncuestaPeriodo.objects.values("id").filter(encuesta=self).exists()


class CapPreguntaEncuestaPeriodo(ModeloBase):
    encuesta = models.ForeignKey(CapEncuestaPeriodo, verbose_name=u'Encuesta', on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripción', blank=True)
    isActivo = models.BooleanField(default=False, verbose_name=u'¿Está Activo?')

    def __str__(self):
        return u"%s" % self.encuesta.__str__()

    class Meta:
        verbose_name = u'Pregunta encuesta satisfacción de capacitación docente'
        verbose_name_plural = u'Preguntas de encuesta satisfacción de capacitación docente'

    def en_uso(self):
        return CapRespuestaEncuestaSatisfaccion.objects.values("id").filter(pregunta=self).exists() or CapOpcionPreguntaEncuestaPeriodo.objects.values("id").filter(pregunta=self).exists()

    def opciones(self):
        return CapOpcionPreguntaEncuestaPeriodo.objects.filter(pregunta=self, status=True)


class CapOpcionPreguntaEncuestaPeriodo(ModeloBase):
    pregunta = models.ForeignKey(CapPreguntaEncuestaPeriodo, verbose_name=u'Pregunta', on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripción', blank=True)
    valoracion = models.IntegerField(default=0, verbose_name=u"Cantidad de estrellas")
    isActivo = models.BooleanField(default=False, verbose_name=u'¿Está Activo?')

    def __str__(self):
        return u"%s - %s" % (self.pregunta.descripcion, self.descripcion)

    class Meta:
        verbose_name = u'Opción de pregunta encuesta satisfacción de capacitación docente'
        verbose_name_plural = u'Opciones de pregunta de encuesta satisfacción de capacitación docente'

    def en_uso(self):
        return CapRespuestaEncuestaSatisfaccion.objects.values("id").filter(opcion=self).exists()


class CapRespuestaEncuestaSatisfaccion(ModeloBase):
    pregunta = models.ForeignKey(CapPreguntaEncuestaPeriodo, verbose_name=u'Pregunta Encuesta', on_delete=models.CASCADE)
    opcion = models.ForeignKey(CapOpcionPreguntaEncuestaPeriodo, verbose_name=u'Opción Encuesta', on_delete=models.CASCADE, blank=True, null=True)
    solicitud = models.ForeignKey('sga.CapCabeceraSolicitudDocente', verbose_name=u'Solicitud', on_delete=models.CASCADE)
    valoracion = models.IntegerField(default=0, verbose_name=u"Cantidad de estrellas, seleccionada")
    observacion = models.TextField(default='', verbose_name=u'Observación', blank=True)

    def __str__(self):
        return u"%s - (%s: %s)" % (self.pregunta, self.solicitud, self.valoracion)

    class Meta:
        verbose_name = u'Respuesta encuesta satisfacción de capacitación docente'
        verbose_name_plural = u'Respuestas encuesta satisfacción de capacitación docente'


class MigracionEvidenciaActividad(ModeloBase):
    evidencia = models.ForeignKey("sga.EvidenciaActividadDetalleDistributivo", verbose_name=u"Evidencia", on_delete=models.CASCADE, blank=True, null=True)
    informevinculacion = models.ForeignKey("sga.ConfiguracionInformeVinculacion", verbose_name=u"Configuracion Informe Vinculación", on_delete=models.CASCADE, blank=True, null=True)
    proyectoinvestigacion = models.ForeignKey("investigacion.ProyectoInvestigacion", verbose_name=u"Proyecto de investigacion", on_delete=models.CASCADE, blank=True, null=True)
    evidenciabase = models.ForeignKey("sga.EvidenciaActividadDetalleDistributivo", verbose_name=u"Evidencia de la que se propagan evidencias", on_delete=models.CASCADE, blank=True, null=True, related_name="+")
    parrevisor = models.ForeignKey("sga.ParRevisorProduccionCientifica", verbose_name=u"Par revisor de producción científica", on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return u"%s" % self.evidencia.actividad

    class Meta:
        verbose_name = u'Migracion de evidencias criterios varios'
        verbose_name_plural = u'Migracion de evidencias criterios varios'

    def delete(self, *args, **kwargs):
        super(MigracionEvidenciaActividad, self).delete(*args, **kwargs)


TIPO_ACTIVIDAD = ((1, 'ACTIVIDADES'), (2, 'SUB ACTIVIDADES'), (3, 'SUB ACTIVIDADES ADICIONALES'))
TIPO_CRITERIO = ((1, 'DOCENCIA'), (2, 'INVESTIGACION'), (3, 'GESTION'), (4, 'VINCULACION'))


class Criterio(ModeloBase):
    nombre = models.TextField(default='', verbose_name=u'Nombre', blank=True)
    tipo = models.IntegerField(choices=TIPO_ACTIVIDAD, default=1, verbose_name=u"Tipo de actividad")
    tipocriterio = models.IntegerField(choices=TIPO_CRITERIO, default=1, verbose_name=u"Tipo de actividad")

    def __str__(self):
        return u"%s" % self.nombre

    class Meta:
        verbose_name = u'Criterio'
        verbose_name_plural = u'Criterios'
        ordering = ('nombre',)

    def en_uso(self):
        return SubactividadDetalleDistributivo.objects.values('id').filter(subactividaddocenteperiodo__criterio=self, status=True).exists()


class ActividadDocentePeriodo(ModeloBase):
    criterio = models.ForeignKey(Criterio, verbose_name=u"Criterio", on_delete=models.CASCADE, blank=True, null=True)
    criteriodocenciaperiodo = models.ForeignKey("sga.CriterioDocenciaPeriodo", verbose_name=u"Criterio docencia / vinculación", on_delete=models.CASCADE, blank=True, null=True)
    criterioinvestigacionperiodo = models.ForeignKey("sga.CriterioInvestigacionPeriodo", verbose_name=u"Criterio investigacion", on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return u"%s" % self.criterio.nombre

    class Meta:
        verbose_name = u'Actividad Docente Periodo'
        verbose_name_plural = u'Actividades Docente Periodo'
        ordering = ('criterio__nombre',)

    def get_subactividades(self):
        return self.subactividaddocenteperiodo_set.filter(status=True)

    def get_num_subactividades(self):
        return self.subactividaddocenteperiodo_set.filter(status=True).values('id').count()


class SubactividadDocentePeriodo(ModeloBase):
    class TipoEvidencia(models.IntegerChoices):
        NINGUNO  = 0, u"NINGUNO"
        INFORME  = 1, u"INFORME"
        BITACORA = 2, u"BITÁCORA"
        PRODUCTO = 3, u"PRODUCTO INV"
    criterio = models.ForeignKey(Criterio, verbose_name=u"Criterio", on_delete=models.CASCADE, blank=True, null=True)
    actividad = models.ForeignKey(ActividadDocentePeriodo, verbose_name=u"Actividad", on_delete=models.CASCADE, blank=True, null=True)
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha de fin')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha de inicio')
    es_extra = models.BooleanField("Actividad extra", blank=True, null=True, default=False)
    validacion = models.BooleanField("¿Requiere validación?", blank=True, null=True, default=True)
    nombrehtml = models.CharField(default='', max_length=100, verbose_name='Nombre html', blank=True, null=True)
    tipoevidencia = models.IntegerField(choices=TipoEvidencia.choices, default=TipoEvidencia.NINGUNO, blank=True, null=True, verbose_name=u"Tipo de evidencia")
    cargaevidencia = models.BooleanField("¿El docente carga evidencia?", blank=True, null=True, default=True)

    def __str__(self):
        return u"%s" % self.criterio.nombre

    class Meta:
        verbose_name = u'Sub Actividad Docente Periodo'
        verbose_name_plural = u'Sub Actividades Docente Periodo'
        ordering = ('criterio__nombre',)

    def get_total_revisores(self):
        return self.usercriteriorevisor_set.filter(status=True).count()

    def htmldocente(self):
        return f'adm_criteriosactividadesdocente/subactividades/{self.nombrehtml}.html' if self.nombrehtml else ''


class SubactividadDetalleDistributivo(ModeloBase):
    actividaddetalledistributivo = models.ForeignKey(ActividadDetalleDistributivo, verbose_name=u"Actividad Detalle Distributivo", on_delete=models.CASCADE, blank=True, null=True)
    subactividaddocenteperiodo = models.ForeignKey(SubactividadDocentePeriodo, verbose_name=u"Subactividad Periodo", on_delete=models.CASCADE, blank=True, null=True)
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha de fin')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha de inicio')

    def __str__(self):
        return u"%s" % self.subactividaddocenteperiodo.criterio.nombre

    class Meta:
        verbose_name = u'Subactividad Detalle Distributivo'
        verbose_name_plural = u'Subactividades Detalle Distributivo'
        ordering = ('subactividaddocenteperiodo__criterio__nombre',)

    def total_evidencias(self):
        try:
            if self.subactividaddocenteperiodo.tipoevidencia == 2:
                return self.bitacoraactividaddocente_set.filter(detallebitacoradocente__status=True, status=True).distinct().count()
            if self.subactividaddocenteperiodo.tipoevidencia == 1:
                return self.evidenciaactividaddetalledistributivo_set.filter(status=True).count()
            return 0
        except Exception as ex:
            return 0

    def get_evidencias(self):
        return self.evidenciaactividaddetalledistributivo_set.filter(status=True)

    def get_porcentaje_informe(self, ev, fecha):
        _response, flat = 100, False
        fini, ffin = ev.hasta, fecha
        if ev.historialaprobacionevidenciaactividad_set.filter(estadoaprobacion=3, status=True).values('id').exists():
            for historial in ev.historialaprobacionevidenciaactividad_set.filter(status=True).order_by('fecha_creacion').values_list('estadoaprobacion', 'fecha_creacion'):
                if historial[0] == 3:
                    fini, flat = historial[1], True
                    continue

                if flat and not historial[0] == 3:
                    ffin = historial[1]
                    break

            for loop in range(fini.month, ffin.month):
                _response = _response * 0.5

        return _response

    def tiene_registro_bitacora(self, fechafin=None):
        from investigacion.models import DetalleBitacoraDocente
        filtro = Q(bitacoradocente__subactividad=self, bitacoradocente__status=True, status=True)
        if fechafin:
            filtro &= Q(fecha__month=fechafin.month, fecha__year=fechafin.year)
        return DetalleBitacoraDocente.objects.filter(filtro).values('id').exists()

    def horarios_informesinvestigacion_profesor(self, detalledistributivo, fechaini, fechafin, esautomatico=False):
        import calendar
        from dateutil.rrule import rrule, MONTHLY
        from sga.funciones import mesesmenoresandias
        from sga.models import ClaseActividad, EvidenciaActividadDetalleDistributivo
        from sga.pro_cronograma import CRITERIO_DIRECTOR_PROYECTO, CRITERIO_ASOCIADO_PROYECTO, CRITERIO_CODIRECTOR_PROYECTO_INV, CRITERIO_DIRECTOR_GRUPOINVESTIGACION, CRITERIO_INTEGRANTE_GRUPOINVESTIGACION
        try:
            if self.fechafin < fechafin: fechafin = self.fechafin
            distributivo = detalledistributivo.distributivo
            periodo = detalledistributivo.distributivo.periodo
            profesor = detalledistributivo.distributivo.profesor
            claseactividad = detalledistributivo.claseactividad_set.filter(detalledistributivo__distributivo__profesor=profesor, status=True).order_by('inicio', 'dia', 'turno__comienza')
            result = []
            if claseactividad:
                diasclas = claseactividad.values_list('dia', 'turno_id')
                dt, end, step = fechaini, fechafin, timedelta(days=1)
                while dt <= end:
                    if not self.actividaddetalledistributivo.criterio.distributivo.periodo.dias_nolaborables(dt):
                        for dclase in diasclas:
                            if dt.isocalendar()[2] == dclase[0]:
                                result.append(dt.strftime('%Y-%m-%d'))
                    dt += step
            listaevidencias = []
            listamesesperiodo = []
            listadoevidencias = self.evidenciaactividaddetalledistributivo_set.filter(criterio__distributivo__profesor=profesor, hasta__lte=fechafin, status=True).order_by('hasta')
            mesesevidencia = list(listadoevidencias.values_list('hasta__month', flat=True))
            fechas_mensuales = list(rrule(MONTHLY, dtstart=self.fechainicio, until=self.fechafin))
            for fecha in fechas_mensuales:
                if fecha.date() <= fechafin:
                    listamesesperiodo.append(fecha.month)
            mfaltantes = list(set(listamesesperiodo) - set(mesesevidencia))
            mesesmenores = mesesmenoresandias(periodo.inicio, periodo.fin)
            meses_faltantes = list(set(mfaltantes) - set(mesesmenores))
            listafechasmesesfaltantes = []
            # recorro de nuevo para sacar fechas de meses faltantes
            for fecha in fechas_mensuales:
                if fecha.month in meses_faltantes:
                    primer_dia = fecha.replace(day=1)
                    ultimo_dia = fecha.replace(day=calendar.monthrange(fecha.year, fecha.month)[1])
                    listafechasmesesfaltantes.append([primer_dia, ultimo_dia])
            cuentaevi, sumaporcentaje, porcentajefinal = 0, 0, 0
            for evi in listadoevidencias:
                cuentaevi = cuentaevi + 1
                porcentaje = 100
                if not (evi.hasta.month == fechafin.month and evi.hasta.year == fechafin.year):
                    porcentaje = self.get_porcentaje_informe(evi, fechafin)
                sumaporcentaje = sumaporcentaje + porcentaje
                listaevidencias.append([1, evi, porcentaje])

            if self.subactividaddocenteperiodo.validacion:
                for mesfalta in listafechasmesesfaltantes:
                    criterioactual, etiqueta = self.subactividaddocenteperiodo.criterio.pk, ''
                    tipointegrante = profesor.persona.proyectoinvestigacionintegrante_set.values_list('funcion', flat=True).filter(tiporegistro__in=[1, 3, 4], proyecto__estado_id=37, status=True).exclude(proyecto__in=variable_valor('EXCLUIR_PROYECTOS_INVESTIGACION'))
                    tipointegrantegrupo = profesor.persona.grupoinvestigacionintegrante_set.values_list('funcion', flat=True).filter(grupo__vigente=True, grupo__status=True, status=True)
                    if criterioactual == CRITERIO_DIRECTOR_PROYECTO and not 1 in tipointegrante:
                        etiqueta = u'Ya no cuenta con el rol de director'
                    if criterioactual == CRITERIO_ASOCIADO_PROYECTO and not 3 in tipointegrante:
                        etiqueta = u'Ya no cuenta con el rol de asociado'
                    if criterioactual == CRITERIO_CODIRECTOR_PROYECTO_INV and not 2 in tipointegrante:
                        etiqueta = u'Ya no cuenta con el rol de co-director'
                    if criterioactual == CRITERIO_DIRECTOR_GRUPOINVESTIGACION and not 1 in tipointegrantegrupo:
                        etiqueta = u'Ya no cuenta con el rol de director'
                    if criterioactual == CRITERIO_INTEGRANTE_GRUPOINVESTIGACION and not (2 in tipointegrantegrupo or 3 in tipointegrantegrupo):
                        etiqueta = u'Ya no cuenta con el rol de integrante'

                    porcentajemes = '-' if etiqueta else 0
                    if not porcentajemes:
                        cuentaevi += 1
                    listaevidencias.append([3, mesfalta[0], mesfalta[1], etiqueta, porcentajemes])

            if cuentaevi:
                porcentajefinal = sumaporcentaje / cuentaevi

            # if not self.subactividaddocenteperiodo.validacion:
            #     porcentajefinal = 100

            listaevidencias.append([2, 'RESUMEN', porcentajefinal])
            claseactividad.__setattr__('totalplanificadas', len(result))
            claseactividad.__setattr__('listadoevidencias', listaevidencias)
            if esautomatico:
                if not listaevidencias:
                    totalmensual = '-'
                    promedio = 0
                else:
                    totalmensual = len(result)
                    promedio = porcentajefinal
                claseactividad = [totalmensual, promedio]
            return claseactividad
        except Exception as ex:
            return False

    def get_ponencias(self, fechafin=None):
        try:
            from sga.models import PlanificarPonencias
            if not fechafin:
                fechafin = self.fechafin
            profesor = self.actividaddetalledistributivo.criterio.distributivo.profesor
            return PlanificarPonencias.objects.filter(profesor=profesor, fecha_inicio__gte=self.fechainicio, fecha_fin__lte=fechafin, estado=3, status=True).order_by('-fecha_creacion')
        except Exception as ex:
            return []

# class CronogramaPresidentesCurso(ModeloBase):
#     periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, verbose_name=u'Periodo', blank=True, null=True)
#     coordinacion = models.ForeignKey('sga.Coordinacion', on_delete=models.CASCADE, verbose_name=u'Coordinación', blank=True, null = True)
#     fechainicio = models.DateField(verbose_name=u'Fecha inicio', null=True, blank=True)
#     horainicio = models.TimeField(verbose_name=u'Hora inicio', null=True, blank=True)
#     fechafin = models.DateField(verbose_name=u'Fecha fin', null=True, blank=True)
#     horafin = models.TimeField(verbose_name=u'Hora fin', null=True, blank=True)
#     activo = models.BooleanField(default=False, verbose_name=u'Activo')
#
#     def __str__(self):
#         return u'%s: %s - %s' % (self.coordinacion, self.fechainicio, self.fechafin)
#
#     class Meta:
#         verbose_name = u"Cronograma de presidentes de curso"
#         verbose_name_plural = u"Cronogramas de presidentes de curso"
#         ordering = ['coordinacion', 'fechainicio', 'fechafin']
#
# class DetalleCronogramaPresidentesCurso(ModeloBase):
#     cronograma = models.ForeignKey(CronogramaPresidentesCurso, on_delete=models.CASCADE, verbose_name=u'Cronograma Presidentes Curso', blank=True, null = True)
#     carrera = models.ForeignKey(Carrera, verbose_name=u'Carrera', blank=True, null=True, on_delete=models.CASCADE)
#     activo = models.BooleanField(default=False, verbose_name=u'Activo')
#
#     def __str__(self):
#         return u'%s: %s - %s' % (self.cronograma, self.carrera, self.activo)
#
#     class Meta:
#         verbose_name = u"Detalle cronograma de presidentes de curso"
#         verbose_name_plural = u"Detalles cronograma de presidentes de curso"
#         ordering = ['cronograma', 'carrera', 'activo']

class EstudiantesCandidatosaPresidentesdeCurso(ModeloBase):
    periodo_id = models.IntegerField(default=0, verbose_name=u'Id del periodo', blank=True, null = True)
    periodo_nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre del periodo', blank=True, null=True)
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripcion',blank=True, null=True, on_delete=models.CASCADE)
    matricula = models.IntegerField(default=0, verbose_name=u'Id de la matricula', blank=True, null = True)
    cedula = models.CharField(default='', max_length=20, verbose_name=u"Cedula", blank=True, null = True)
    nombres = models.CharField(default='', max_length=100, verbose_name=u'Nombres Completos', blank=True, null = True)
    correo = models.CharField(default='', max_length=200, verbose_name=u"Correo electronico", blank=True, null = True)
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Telefono movil", blank=True, null = True)
    sexo = models.CharField(default='', max_length=50, verbose_name=u"Sexo", blank=True, null = True)
    carrera_id = models.IntegerField(default=0, verbose_name=u'Id de la carrera', blank=True, null=True)
    carrera = models.CharField(default='', max_length=100, verbose_name=u"Carrera", blank=True, null = True)
    nivel = models.CharField(default='', max_length=50, verbose_name=u"Nivel", blank=True, null = True)
    orden = models.IntegerField(default=0, verbose_name=u'Orden de Nivel Malla', blank=True, null = True)
    paralelo = models.CharField(default='', max_length=50, verbose_name=u"Paralelo", blank=True, null = True)
    promedio_final = models.CharField(default='', max_length=50, verbose_name=u"Promedio", blank=True, null = True)

    def __str__(self):
        return u"%s" % (self.nombres)
    class Meta:
        verbose_name = u'Estudiante Candidato a Presidente de Curso'
        verbose_name_plural = u'Estudiantes Candidatos a Presidentes de Curso'
    def save(self, *args, **kwargs):
        super(EstudiantesCandidatosaPresidentesdeCurso, self).save(*args, **kwargs)

class CabeceraPresidenteCurso(ModeloBase):
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    carrera = models.ForeignKey(Carrera, verbose_name=u'Carrera',blank=True, null=True, on_delete=models.CASCADE)
    director_carrera = models.ForeignKey(Persona, blank=True, null=True, verbose_name=u'Persona Responsable', on_delete=models.CASCADE)
    def __str__(self):
        return u"%s (%s - %s)" % (self.periodo, self.carrera, self.director_carrera)

    class Meta:
        verbose_name = u"Cabecera presidente de curso"
        verbose_name_plural = u"Cabeceras presidentes de cursos"


class DetallePresidenteCurso(ModeloBase):
    cabecerapresidentecurso = models.ForeignKey(CabeceraPresidenteCurso, verbose_name=u'Cabecera Presidente de Curso',blank=True, null=True, on_delete=models.CASCADE)
    nivel = models.ForeignKey(NivelMalla, verbose_name=u'Nivel',blank=True, null=True, on_delete=models.CASCADE)
    paralelo = models.ForeignKey(Paralelo, verbose_name=u'Paralelo', blank=True, null=True, on_delete=models.CASCADE)
    # matricula = models.ForeignKey(Matricula, verbose_name=u'Matricula',blank=True, null=True, on_delete=models.CASCADE)
    estudiante_candidato = models.ForeignKey(EstudiantesCandidatosaPresidentesdeCurso,verbose_name=u'Estudiante Candidato', blank=True, null=True,on_delete=models.CASCADE)
    desde = models.DateField(verbose_name=u'Fecha inicio',blank=True, null=True)
    hasta = models.DateField(verbose_name=u'Fecha fin', blank=True, null=True )
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u"%s (%s)" % (self.cabecerapresidentecurso, self.estudiante_candidato)

    class Meta:
        verbose_name = u"Representante de curso"
        verbose_name_plural = u"Representantes de cursos"

class TemaImpartidoDocente(ModeloBase):
    materia_id = models.IntegerField(default=0, verbose_name=u'Id de la materia', blank=True, null = True)
    periodo_id = models.IntegerField(default=0, verbose_name=u'Id del periodo', blank=True, null=True)
    periodo_nombre = models.CharField(default='', max_length=255, verbose_name=u'Nombre del periodo', blank=True,null=True)
    semana = models.IntegerField(default=0, verbose_name=u'Numero de semana', blank=True, null=True)
    fecha_inicio_semana = models.DateField(verbose_name=u'Fecha de inicio de la semana', blank=True, null=True)
    fecha_fin_semana = models.DateField(verbose_name=u'Fecha de inicio de la semana', blank=True, null=True)
    tema_descripcion = models.TextField(default='', verbose_name=u'Nombre del tema', blank=True,null=True)
    procentaje_tema = models.CharField(default='-', max_length=100, verbose_name=u'Porcentaje del tema', blank=True,null=True)

    def __str__(self):
        return u"%s - %s (%s)" % (self.periodo_nombre, self.materia_id, self.tema_descripcion)
    class Meta:
        verbose_name = u'Tema impartido por el docente'
        verbose_name_plural = u'Temas impartidos por los docentes'
    def save(self, *args, **kwargs):
        super(TemaImpartidoDocente, self).save(*args, **kwargs)

    @classmethod
    def calculo_total(cls, materia_id, periodo):
        # Obtener todos los temas que coincidan con materia_id y periodo_id
        temas = cls.objects.filter(materia_id=materia_id, periodo_id=periodo.pk, status=True)

        total_porcentaje = 0.0
        total_elementos = 0

        for tema in temas:
            # Sumar el porcentaje del tema si no es nulo o vacío
            if tema.procentaje_tema != '-':
                total_elementos += 1
                total_porcentaje += float(tema.procentaje_tema)

            # Obtener subtemas del tema
            subtemas = SubtemaImpartidoDocente.objects.filter(tema=tema, status=True)
            for subtema in subtemas:
                if subtema.procentaje_subtema != '-':
                    total_elementos += 1
                    total_porcentaje += float(subtema.procentaje_subtema)

        if total_elementos == 0:
            return 0.0, 0.0

        promedio = round((total_porcentaje / total_elementos),2)
        sobre30 = round(((promedio * 30) / 100), 2)
        return promedio, sobre30

class SubtemaImpartidoDocente(ModeloBase):
    tema = models.ForeignKey(TemaImpartidoDocente, verbose_name=u"Tema Impartido Docente",on_delete=models.CASCADE, blank=True, null=True)
    subtema_descripcion = models.TextField(default='', verbose_name=u'Nombre del subtema', blank=True,null=True)
    procentaje_subtema = models.CharField(default='-', max_length=100, verbose_name=u'Porcentaje del subtema',blank=True, null=True)

    def __str__(self):
        return u"%s - %s (%s)" % (self.tema.tema_descripcion, self.subtema_descripcion, self.procentaje_subtema)
    class Meta:
        verbose_name = u'Subtema impartido por el docente'
        verbose_name_plural = u'Subtemas impartidos por los docentes'
    def save(self, *args, **kwargs):
        super(SubtemaImpartidoDocente, self).save(*args, **kwargs)

class MallaHorasSemanalesComponentes(ModeloBase):
    malla = models.ForeignKey(Malla, verbose_name=u"Tema Impartido Docente",on_delete=models.CASCADE, blank=True, null=True)
    nivelmalla = models.ForeignKey(NivelMalla, verbose_name=u"Nivel", blank=True, null=True, on_delete=models.CASCADE)
    acd_horassemanales = models.FloatField(default=0, verbose_name=u"Horas semanales del componente ACD", blank=True, null=True)
    ape_aa_horassemanales = models.FloatField(default=0, verbose_name=u"Horas semanales del componente AA y APE", blank=True, null=True)
    total_horassemanales = models.FloatField(default=0, verbose_name=u"Horas semanales totales",blank=True, null=True)
    tiene_itinerario = models.BooleanField(verbose_name=u"Tiene itinerario en el nivel", blank=True, null=True, default=False)

    def __str__(self):
        return u"%s - %s (%s)" % (self.malla.carrera.nombre, self.nivelmalla.nombre, self.total_horassemanales)
    class Meta:
        verbose_name = u'Hora semanal de la malla por nivel'
        verbose_name_plural = u'Horas semanales de la malla por niveles'

    def acd_horastotales(self):
        acd_totales = 0
        ape_aa_horassemanales_totales = 0
        total_horas_componentes = 0
        if horas_acd :=  MallaHorasSemanalesComponentes.objects.values_list('acd_horassemanales',flat=True).filter(status = True, malla_id = self.malla_id):
            for hora_acd in horas_acd:
                acd_totales += hora_acd

        if horas_ape_aa :=  MallaHorasSemanalesComponentes.objects.values_list('ape_aa_horassemanales',flat=True).filter(status = True, malla_id = self.malla_id):
            for hora_ape_aa in horas_ape_aa:
                ape_aa_horassemanales_totales += hora_ape_aa

        if horas_totales :=  MallaHorasSemanalesComponentes.objects.values_list('total_horassemanales',flat=True).filter(status = True, malla_id = self.malla_id):
            for hora_total in horas_totales:
                total_horas_componentes += hora_total

        return acd_totales, ape_aa_horassemanales_totales, total_horas_componentes

    def save(self, *args, **kwargs):
        super(MallaHorasSemanalesComponentes, self).save(*args, **kwargs)

class ExtraPreInscripcionPracticasPP(ModeloBase):
    preinscripcion = models.ForeignKey(PreInscripcionPracticasPP, blank=True, null=True, verbose_name=u'Pre-inscripción', on_delete=models.CASCADE)
    enlinea = models.BooleanField(default=False, verbose_name=u'¿Es en línea?')

    def __str__(self):
        return f"{self.preinscripcion}"

    def save(self, *args, **kwargs):
        super(ExtraPreInscripcionPracticasPP, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Extra Pre Inscripción Prácticas PP"
        verbose_name_plural = u"Extra Pre Inscripciones Prácticas PP"

class ExtraDetallePreInscripcionPracticasPP(ModeloBase):
    detallepreins = models.ForeignKey(DetallePreInscripcionPracticasPP, blank=True, null=True, verbose_name=u'Detalle pre-inscripción', on_delete=models.CASCADE)
    actacompromisopracticas = models.FileField(upload_to='preinscripcion/actacompromiso/', blank=True, null=True, verbose_name=u'Archivo firmado')
    migradomatricula = models.BooleanField(default=False, verbose_name=u'¿Migrado por matriculación?')

    def __str__(self):
        return f"{self.detallepreins}"

    def save(self, *args, **kwargs):
        super(ExtraDetallePreInscripcionPracticasPP, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Extra Detalle Pre Inscripción Prácticas PP"
        verbose_name_plural = u"Extra Detalles Pre Inscripciones Prácticas PP"

class ItinerarioAsignaturaMalla(ModeloBase):
    itinerariomalla = models.ForeignKey(ItinerariosMalla, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Itinerario Malla')
    asignaturamalla = models.ForeignKey(AsignaturaMalla, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Asignatura Malla')

    def __str__(self):
        return u'%s - %s' %(self.itinerariomalla, self.asignaturamalla)

    class Meta:
        verbose_name = u"Itinerario Asignatura malla"
        verbose_name_plural = u"Itinerarios Asignaturas malla"

class ExtraProyectoVinculacionInscripcion(ModeloBase):
    proyectoinscripcion = models.ForeignKey(ProyectoVinculacionInscripcion, blank=True, null=True, verbose_name=u'Detalle pre-inscripción', on_delete=models.CASCADE)
    actacompromisovinculacion = models.FileField(upload_to='proyectovinculacion/actacompromiso/', blank=True, null=True, verbose_name=u'Archivo firmado')

    def __str__(self):
        return f"{self.proyectoinscripcion}"

    def save(self, *args, **kwargs):
        super(ExtraProyectoVinculacionInscripcion, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Extra Proyecto Vinculacion Inscripcion"
        verbose_name_plural = u"Extra Proyecto Vinculacion Inscripciones"

class HistoricoCambioFotoPerfil(ModeloBase):
    cedula = models.CharField(default='', max_length=20, verbose_name=u'Cedula del estudiante',blank=True, null=True)
    nombres = models.CharField(default='', max_length=600, verbose_name=u'Nombres del estudiante',blank=True, null=True)
    facultad_id = models.IntegerField(default=0, verbose_name=u'Id de la facultad', blank=True, null=True)
    facultad = models.CharField(default='', max_length=600, verbose_name=u'Facultad del estudiante',blank=True, null=True)
    carrera_id = models.IntegerField(default=0, verbose_name=u'Id de la carrera', blank=True, null=True)
    carrera = models.CharField(default='', max_length=600, verbose_name=u'Carrera del estudiante',blank=True, null=True)
    nivel = models.CharField(default='', max_length=600, verbose_name=u'Nivel del estudiante',blank=True, null=True)
    cedula_persona_registro = models.CharField(default='', max_length=20, verbose_name=u'Cedula de la persona que registro',blank=True, null=True)
    persona_registro = models.CharField(default='', max_length=600, verbose_name=u'Nombres de la persona que registro',blank=True, null=True)
    periodo_id = models.IntegerField(default=0, verbose_name=u'Id del periodo', blank=True, null=True)
    periodo = models.CharField(default='', max_length=600, verbose_name=u'Periodo',blank=True, null=True)
    fecha = models.DateField(verbose_name=u'Fecha de registro', blank=True, null=True)
    foto = models.CharField(default='', max_length=600, verbose_name=u'Foto',blank=True, null=True)

    def __str__(self):
        return u"%s - %s (%s)" % (self.nombres, self.carrera, self.fecha)
    class Meta:
        verbose_name = u'Registro historico de la actualizacion de foto'
        verbose_name_plural = u'Registros historicos de la actualizacion de fotos'

    def save(self, *args, **kwargs):
        super(HistoricoCambioFotoPerfil, self).save(*args, **kwargs)


class RequerimientoInternoPractica(ModeloBase):
    class TipoRequerimiento(models.IntegerChoices):
        NINGUNO  = 0, u"NINGUNO"
        EQUIPOS  = 1, u"EQUIPOS O INSTRUMENTOS"
        INSUMOS  = 2, u"MATERIALES O INSUMOS"

    tipo = models.IntegerField(choices=TipoRequerimiento.choices, default=TipoRequerimiento.NINGUNO, verbose_name=u"Tipo de requerimiento", blank=True, null=True)
    detalle = models.TextField(default='', max_length=300, verbose_name=u"Descripción", blank=True, null=True)
    ubicacion = models.IntegerField(choices=UBICACION_APRENDIZAJE, default=1, verbose_name=u"Tipo de actividad")
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Carrera')

    def __str__(self):
        return f"{self.detalle}"

    class Meta:
        verbose_name = u'Requerimiento interno para la practica'
        verbose_name_plural = u'Requerimiento interno para las practicas'
        ordering = ('detalle',)


class GPRequerimientoPractica(ModeloBase):
    guiapractica = models.ForeignKey(GPGuiaPracticaSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Guia de práctica')
    requerimiento = models.ForeignKey(RequerimientoInternoPractica, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Requerimiento de practica')
    cantidad = models.IntegerField(default=1, verbose_name=u"Cantidad", blank=True, null=True)

    def __str__(self):
        return f"{self.requerimiento.detalle}"

    class Meta:
        verbose_name = u'Requerimiento de la guía practica'
        verbose_name_plural = u'Requerimientos de la guia practica'
        ordering = ('id', )


class GPLibrosOdilo(ModeloBase):
    guiapractica = models.ForeignKey(GPGuiaPracticaSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Guia de práctica')
    libroodilo = models.ForeignKey(LibrosOdiloSilaboSemanal, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Libros UTECA')

    def __str__(self):
        return f"{self.libroodilo.titulo}"

    class Meta:
        verbose_name = u'Bibliografía UTECA'
        verbose_name_plural = u'Bibliografías UTECA'
        ordering = ('id', )


ANALISTAS_DISPONIBLES = [
    (1, u'POR ASIGNAR'),
    (2, u'Analista 1'),
    (3, u'Analista 2'),
    (4, u'Analista 3'),
    (5, u'Analista 4'),
]

ESTADOS_AUDITORIA = [
    (1, u'INGRESADO'),
    (2, u'EN REVISIÓN'),
    (3, u'FINALIZADO'),
    (4, u'RECHAZADO'),
]

DETALLES_AUDITORIA = [
    (1, u'Acceso no autorizado al sistema'),
    (2, u'Notas alteradas test/examen'),
    (3, u'Notas alteradas actividades'),
    (4, u'Manipulación banco de preguntas'),
    (5, u'Eliminar/Habilitar intento de Test/Examen'),
    (6, u'Otros')
]


class Auditoria(ModeloBase):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, verbose_name=u'Solicitante de auditoria', blank=True,
                                null=True)
    fecha = models.DateField(verbose_name=u'Fecha de ingreso de la auditoria', blank=True, null=True)
    estado = models.IntegerField(choices=ESTADOS_AUDITORIA, default=1, verbose_name=u'Estado de la Auditoria',
                                 blank=True, null=True)
    analista = models.IntegerField(choices=ANALISTAS_DISPONIBLES, default=1, verbose_name=u'Analista Asignado',
                                   blank=True, null=True)
    observaciones = models.CharField(default='', max_length=700, verbose_name=u'observaciones', blank=True, null=True)
    detalle = models.IntegerField(choices=DETALLES_AUDITORIA, default=6, verbose_name=u'Incidencia reportada',
                                  blank=True, null=True)
    evidencia = models.FileField(upload_to='auditoriaevidencia/%Y/%m/%d', blank=True, null=True,
                                 verbose_name=u'Evidencia de auditoria')

    def __str__(self):
        return f"{self.persona},detalle: {self.detalle}"

    class Meta:
        verbose_name = u'Auditoria Informatica'
        verbose_name_plural = u'Auditorias Informaticas'

class AsignaturamallaContenidoMinimo(ModeloBase):
    asignaturamalla = models.ForeignKey(AsignaturaMalla, verbose_name=u'Asignatura malla', on_delete=models.CASCADE)
    descripcioncontenido = models.TextField(default='', max_length=1000, verbose_name=u"Contenido Minimo", blank=True, null=True)

    def __str__(self):
        return u"%s (%s)" % (self.asignaturamalla, self.descripcioncontenido)

    class Meta:
        verbose_name = u'Contenido minimo de asignatura'
        verbose_name_plural = u'Contenidos minimos de asignaturas'


class UnidadResultadoProgramaAnaliticoContenidoMinimo(ModeloBase):
    unidadresultadoprogramaanalitico = models.ForeignKey(UnidadResultadoProgramaAnalitico, verbose_name=u'Unidad de resultado de programa analitico', on_delete=models.CASCADE,blank=True, null=True,)
    asignaturamallacontenidominimo = models.ForeignKey(AsignaturamallaContenidoMinimo, verbose_name=u'Contenido minimo de la asignatura malla', on_delete=models.CASCADE,blank=True, null=True,)

    def __str__(self):
        return u"%s (%s)" % (self.unidadresultadoprogramaanalitico.descripcion, self.asignaturamallacontenidominimo.descripcioncontenido)
    class Meta:
        verbose_name = u'Contenido minimo en la unidad de resultado de programa analitico'
        verbose_name_plural = u'Contenidos minimos en las unidades de resultado de programas analiticos'

class SancionSenescyt(ModeloBase):
    inscripcion = models.ForeignKey("sga.Inscripcion", on_delete=models.CASCADE, null=True, blank=True,verbose_name=u"Inscripcion Estudiantes")
    periodo = models.ForeignKey('sga.Periodo', blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u'Observación', blank=True, null=True)