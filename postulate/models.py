from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from sga.funciones import ModeloBase, rangomeses, null_to_decimal, null_to_numeric
from inno.models import CampoDetalladoPac
from sagest.models import RegimenLaboral, TipoContrato, Jornada, TIPO_SOLICITUD_PUBLICACION, DetalleCompetenciaLaboral, \
    DenominacionPuesto
from sga.models import Carrera, MODALIDAD_CARRERA, AsignaturaMalla, Asignatura, TIPO_BECA, FinanciamientoBeca, Persona, \
    InstitucionEducacionSuperior, Colegio, Parroquia, Canton, Provincia, Pais, Titulo, AreaTitulo, TIPO_CAPACITACION_P, \
    MODALIDAD_CAPACITACION, Titulacion, TIPOS_PARAMETRO_REPORTE, NivelTitulacion, DIAS_CHOICES
import os
from django.db.models import Q, FloatField, Sum, F, ExpressionWrapper, DateTimeField, When, Case
from django.db.models.functions import Coalesce, Extract

MODALIDAD_PARTIDA = (
    (1, u'PRESENCIAL'),
    (2, u'EN LINEA'),
    (3, u'SEMIPRESENCIAL'),
    (4, u'VIRTUAL'),
    (5, u'INTENSIVA'),
)

DEDICACION_PERIODO_REQUISITOS = (
    (1, u'TIEMPO COMPLETO'),
    (2, u'MEDIO TIEMPO'),
    (3, u'TIEMPO PARCIAL'),
)

DEDICACION_PARTIDA = (
    (1, u'TIEMPO COMPLETO (40 HORAS)'),
    (2, u'MEDIO TIEMPO (20 HORAS)'),
    (3, u'TIEMPO PARCIAL (18 HORAS)'),
    (4, u'TIEMPO PARCIAL (10 HORAS)'),
)

JORNADA_PARTIDA = (
    (1, u'MATUTINA'),
    (2, u'NOCTURNA'),
    (3, u'MATUTINA Y NOCTURNA'),
    (4, u'EN LINEA'),
    (5, u'FIN DE SEMANA'),
    (6, u'MATUTINA VESPERTINA NOCTURNA'),
    (7, u'MATUTINA VESPERTINA'),
    (8, u'VESPERTINA NOCTURNA'),
    (9, u'VESPERTINA'),
)

CARGOS_TRIBUNAL = (
    (1, u'DECANO DE LA FACULTAD O SU DELEGADO (A)'),
    (2, u'DIRECTOR DE CARRERA O SU DELEGADO (A)'),
    (3, u'PROFESOR (A) A FIN AL CARGO'),
    (4, u'RECTOR (A) O SU DELEGADO (A)'),
    (5, u'VICERRECTOR (A) ACADÉMICA DE FORMACIÓN DE GRADO O SU DELEGADO (A)'),
    (7, u'VICERRECTOR (A) DE VINCULACIÓN O SU DELEGADO (A)'),
    (8, u'VICERRECTOR (A) DE INVESTIGACIÓN Y POSGRADO O SU DELEGADO (A)'),
    (6, u'DIRECTOR (A) DE TALENTO HUMANO O SU DELEGADO (A)'),
    (9, u'DIRECTOR (A) DE UNIDAD O SU DELEGADO (A)')
)

TIPO_TRIBUNAL = (
    (1, u'PRIMERA ETAPA'),
    (2, u'SEGUNDA ETAPA'),
)


class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_entrar_usuario_postulate", "Puede entrar usuario postulate"),
            ("puede_ver_bancos_postulate", "Puede entrar banco elegible y banco habilitado postulate"),
            ("puede_aprobar_partida_postulate", "Puede aprobar/rechazar partidas en planificación"),
            ("puede_revisar_todas_las_actas", "Puede revisar todas las actas"),
            ("puede_ver_todos_bancos", "Puede ver todos los registros tanto de banco habilitado como de elegible"),
        )

class TurnoConvocatoria(ModeloBase):
    turno = models.IntegerField(default=0, verbose_name=u'Turno')
    comienza = models.TimeField(verbose_name=u'Comienza')
    termina = models.TimeField(verbose_name=u'Termina')
    mostrar = models.BooleanField(default=True, verbose_name=u"Mostrar")

    def __str__(self):
        return u'Comienza: %s - Termina: %s' % (self.comienza, self.termina)

    def nombre_horario(self):
        return self.comienza.strftime("%H:%M") + ' a ' + self.termina.strftime("%H:%M")

    def fechas_horarios(self):
        return self.comienza.strftime('%d-%m-%Y') + " al " + self.fechafin.strftime('%d-%m-%Y')

    def puede_eliminar(self):
        return not self.horarioconvocatoria_set.filter(status=True).exists()

    class Meta:
        verbose_name = u"Turno de convocatoria"
        verbose_name_plural = u"Turnos de convocatorias"
        unique_together = ('comienza', 'termina',)

class TipoTurnoConvocatoria(ModeloBase):
    nombre = models.TextField(null=True, blank=True, default='', verbose_name=u'Nombre')
    mostrar = models.BooleanField(default=True, verbose_name=u"Mostrar")

    def __str__(self):
        return u'%s ' % (self.nombre)

    def puede_eliminar(self):
        if not self.horarioconvocatoria_set.filter(status=True).exists():
            return True
        if not self.detallemodeloevaluativoconvocatoria_set.filter(status=True).exists():
            return True
        return False

class ModeloEvaluativoConvocatoria(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    fecha = models.DateField(verbose_name=u"Fecha")
    principal = models.BooleanField(default=False, verbose_name=u"Principal")
    notamaxima = models.FloatField(default=0, verbose_name=u'Nota maxima')
    notaaprobar = models.FloatField(default=0, verbose_name=u'Nota para aprobar')
    notarecuperacion = models.FloatField(default=0, verbose_name=u'Nota para recuperación')
    observaciones = models.TextField(default='', max_length=200, verbose_name=u'Observaciones')
    logicamodelo = models.TextField(default='', verbose_name=u'logica')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Modelo evaluativo de convocatoria"
        verbose_name_plural = u"Modelos evaluativos de convocatorias"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def campos(self):
        return self.detallemodeloevaluativoconvocatoria_set.filter(status=True).order_by('orden')

    def campos_editables(self):
        return self.detallemodeloevaluativoconvocatoria_set.filter(dependiente=False)

    # def puede_modificarse(self):
    #     return not EvaluacionGenerica.objects.values("id").filter(detallemodeloevaluativo__modelo=self,
    #                                                               valor__gt=0).exists()

    def campo(self, nombre):
        return self.detallemodeloevaluativoconvocatoria_set.filter(status=True,nombre=nombre)[0] if self.detallemodeloevaluativoconvocatoria_set.values(
            "id").filter(status=True,nombre=nombre).exists() else None

    def campos_dependientes(self):
        return self.detallemodeloevaluativoconvocatoria_set.filter(dependiente=True)

    def cantidad_campos(self):
        return self.detallemodeloevaluativoconvocatoria_set.values("id").count()


class DetalleModeloEvaluativoConvocatoria(ModeloBase):
    modelo = models.ForeignKey(ModeloEvaluativoConvocatoria, verbose_name=u"Modelo", on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=10, verbose_name=u"Nombre campo")
    descripcion = models.TextField(default='', max_length=200, verbose_name=u'Descripcion')
    notaminima = models.FloatField(default=0, verbose_name=u'Nota minima')
    notamaxima = models.FloatField(default=0, verbose_name=u'Nota maxima')
    decimales = models.IntegerField(default=0, verbose_name=u'lugares decimales')
    actualizaestado = models.BooleanField(default=False, verbose_name=u"Actualiza el estado")
    subearchivo = models.BooleanField(default=False, verbose_name=u"Sube archivo")
    determinaestadofinal = models.BooleanField(default=False, verbose_name=u"Determina estado final")
    dependiente = models.BooleanField(default=False, verbose_name=u"Campo dependiente")
    orden = models.IntegerField(default=0, verbose_name=u"Orden en acta")
    tipo = models.ForeignKey(TipoTurnoConvocatoria, verbose_name=u"Modelo",null=True, blank=True, on_delete=models.CASCADE)
    cargo = models.IntegerField(choices=CARGOS_TRIBUNAL, null=True, blank=True, verbose_name=u'Cargos')

    def __str__(self):
        return u'%s (%s a %s)' % (self.nombre, self.notaminima.__str__(), self.notamaxima.__str__())

    def htmlid(self):
        return self.nombre.replace('.', '_')

    class Meta:
        verbose_name = u"Modelo evaluativo convocatoria - Detalle "
        verbose_name_plural = u"Modelos evaluativos convocatorias - Detalles"
        ordering = ['orden']
        unique_together = ('modelo', 'nombre',)

class ConfiguraRenuncia(ModeloBase):
    MOTIVO_SALIDA = (
        (1, u"Renuncia Voluntaria"),
        (2, u"Terminación de Contrato"),
    )
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")
    meses = models.FloatField(default=0, verbose_name=u'Tiempo en meses')
    cargos = models.ManyToManyField(DenominacionPuesto, verbose_name=u'Cargos')
    motivo = models.IntegerField(choices=MOTIVO_SALIDA,null=True, blank=True, verbose_name=u'Motivo de salida')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Modelo evaluativo de convocatoria"
        verbose_name_plural = u"Modelos evaluativos de convocatorias"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def campos(self):
        return self.detallemodeloevaluativoconvocatoria_set.filter(status=True).order_by('orden')

    def campos_editables(self):
        return self.detallemodeloevaluativoconvocatoria_set.filter(dependiente=False)

    # def puede_modificarse(self):
    #     return not EvaluacionGenerica.objects.values("id").filter(detallemodeloevaluativo__modelo=self,
    #                                                               valor__gt=0).exists()

    def campo(self, nombre):
        return self.detallemodeloevaluativoconvocatoria_set.filter(status=True,nombre=nombre)[0] if self.detallemodeloevaluativoconvocatoria_set.values(
            "id").filter(status=True,nombre=nombre).exists() else None

    def campos_dependientes(self):
        return self.detallemodeloevaluativoconvocatoria_set.filter(dependiente=True)

    def cantidad_campos(self):
        return self.detallemodeloevaluativoconvocatoria_set.values("id").count()


class CriterioApelacion(ModeloBase):
    descripcion = models.TextField(null=True, blank=True, default='', verbose_name=u'Descripción')
    mensaje = models.TextField(null=True, blank=True, default='', verbose_name=u'Mensaje')

    def factores(self):
        return self.factorapelacion_set.filter(status=True).order_by('descripcion')

    def __str__(self):
        return u'%s ' % (self.descripcion)

    class Meta:
        verbose_name = u"Criterio Apelación"
        verbose_name_plural = u"Criterios Apelación"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(CriterioApelacion, self).save(*args, **kwargs)


class FactorApelacion(ModeloBase):
    criterio = models.ForeignKey(CriterioApelacion, blank=True, null=True, verbose_name='Criterio', on_delete=models.CASCADE)
    descripcion = models.TextField(null=True, blank=True, default='', verbose_name=u'Descripción')

    def __str__(self):
        return u'%s ' % (self.descripcion)

    class Meta:
        verbose_name = u"Factor Apelación"
        verbose_name_plural = u"Factores Apelación"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(FactorApelacion, self).save(*args, **kwargs)


CARGA_HORARIA = (
    (1, u'MEDIO TIEMPO (20 HORAS)'),
    (2, u'TIEMPO COMPLETO (40 HORAS) ')
)


class ModeloEvaluativoDisertacion(ModeloBase):
    descripcion = models.TextField(null=True, blank=True, default='', verbose_name=u'Descripción')
    ponderacion = models.FloatField(default=0, verbose_name='Ponderación')
    vigente = models.BooleanField(default=False, verbose_name='Vigente')
    archivo = models.BooleanField(default=False, verbose_name='¿Sube Archivo?')

    def traer_aspectos(self):
        return self.aspectosmodeloevaluativos_set.filter(status=True).order_by('orden')

    def str_vigente(self):
        return 'fa fa-check-circle text-success' if self.vigente else 'fa fa-times-circle text-danger'

    def __str__(self):
        return u'%s ' % (self.descripcion)

    class Meta:
        verbose_name = u"Modelo Evaluativo Disertación"
        verbose_name_plural = u"Modelo Evaluativo Disertación"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(ModeloEvaluativoDisertacion, self).save(*args, **kwargs)


TIPO_REQUISITO = (
    (1,'Legales'),
    (2,'Generales'),
    (3,'Especiales'),
)


class RequisitosConvocatoriaPostulate(ModeloBase):
    titulo = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Titulo')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    varchivo = models.BooleanField(default=True, verbose_name='Guarda Archivo?')
    vdescripcion = models.BooleanField(default=False, verbose_name='Guarda Descripcion?')
    formato = models.FileField(upload_to='requisitoconvocatoriaformatos', blank=True, null=True, verbose_name=u'Formato')

    def __str__(self):
        return f"{self.titulo}"

    class Meta:
        verbose_name = u"Tipo Persona Convocatoria"
        verbose_name_plural = u"Tipo Persona Convocatoria"


class TipoPersonaConvocatoria(ModeloBase):
    descripcion = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Descripción')

    def __str__(self):
        return "{}".format(self.descripcion)

    class Meta:
        verbose_name = u"Tipo Persona Convocatoria"
        verbose_name_plural = u"Tipo Persona Convocatoria"


class GrupoConvocatoria(ModeloBase):
    version = models.IntegerField(default=0, verbose_name=u"Versión")
    grupo = models.ForeignKey(TipoPersonaConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo')
    vigente = models.BooleanField(default=True, verbose_name='Vigente')

    def traerrequisitos(self):
        return self.gruporequisitoconvocatoria_set.filter(status=True).order_by('tipo')

    def __str__(self):
        return '{} v{}'.format(self.grupo.__str__(), self.version)

    class Meta:
        verbose_name = u"Convocatoria Grupo"
        verbose_name_plural = u"Convocatoria Grupo"


class GrupoRequisitoConvocatoria(ModeloBase):
    grupo = models.ForeignKey(GrupoConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Grupo')
    tipo = models.IntegerField(default=0,verbose_name='Tipo', choices=TIPO_REQUISITO)
    requisito = models.ManyToManyField(RequisitosConvocatoriaPostulate, verbose_name=u'Requisito')

    def __str__(self):
        return '{} {}'.format(self.grupo.__str__(), self.get_tipo_display())

    class Meta:
        verbose_name = u"Convocatoria Grupo de Requisitos"
        verbose_name_plural = u"Convocatoria Grupo de Requisitos"


class PeriodoConvocatoria(ModeloBase):
    periodoacademico = models.ForeignKey('sga.Periodo', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Periodo")
    descripcion = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Descripción')
    grupo = models.ForeignKey(TipoPersonaConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo')
    requisitos = models.ForeignKey(GrupoConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Requisitos')
    finicio = models.DateField(verbose_name=u'Fecha Inicio Convocatoria', blank=True, null=True)
    ffin = models.DateField(verbose_name=u'Fecha Fin Convocatoria', blank=True, null=True)
    vigente = models.BooleanField(default=False, verbose_name='¿Vigente?')

    def total_postulantes(self):
        return self.personaperiodoconvocatoria_set.filter(status=True).count()

    def vigente_str(self):
        return 'fa fa-check-circle text-success' if self.vigente else 'fa fa-times-circle text-error'

    def puede_eliminar(self):
        return True

    def __str__(self):
        return "{} ({} - {})".format(self.descripcion, str(self.finicio), str(self.ffin))

    class Meta:
        verbose_name = u"Periodo Convocatoria Requisitos de Ingreso"
        verbose_name_plural = u"Periodo Convocatoria Requisitos de Ingreso"


ESTADO_POSTULANTE_CONVOCATORIA = (
    (0, u'PENDIENTE'),
    (1, u'ARCHIVOS CARGADOS'),
    (2, u'ACEPTADO'),
    (3, u'RECHAZADO'),
)


class PersonaPeriodoConvocatoria(ModeloBase):
    periodo = models.ForeignKey(PeriodoConvocatoria, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Periodo")
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    carrera = models.ForeignKey("sga.Carrera", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Departamento')
    coordinacion = models.ForeignKey("sga.Coordinacion", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Departamento')
    denominacionpuesto = models.ForeignKey('sagest.DenominacionPuesto', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Denominación de Puesto')
    modalidad = models.IntegerField(choices=MODALIDAD_PARTIDA, null=True, blank=True, verbose_name=u'Modalidad')
    dedicacion = models.IntegerField(choices=DEDICACION_PERIODO_REQUISITOS, null=True, blank=True, verbose_name=u'Dedicación')
    estado = models.IntegerField(choices=ESTADO_POSTULANTE_CONVOCATORIA, null=True, blank=True, verbose_name=u'Estado')
    observacion_validacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación Revisor')
    fecha_validacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Subida')

    def estado_color(self):
        label = 'label label-default'
        if self.estado == 0:
            label = 'label label-default'
        elif self.estado == 1:
            label = 'label label-primary'
        elif self.estado == 2:
            label = 'label label-success'
        elif self.estado == 3:
            label = 'label label-danger'
        return label

    def totalarchivoscargar(self):
        return self.personarequisitosconvocatoria_set.filter(status=True).count()

    def totalarchivoscargados(self):
        return self.personarequisitosconvocatoria_set.filter(status=True, estado=1).count()

    def subiotodoslosarchivos(self):
        return self.totalarchivoscargados() == self.totalarchivoscargar()

    def traerrequisitos(self):
        return self.personarequisitosconvocatoria_set.filter(status=True).order_by('tipo', 'id')

    def traer_cabecera(self):
        return self.personarequisitosconvocatoria_set.filter(status=True).order_by('tipo').distinct('tipo')

    def obtener_requisito_detalle(self,tipo):
        return self.personarequisitosconvocatoria_set.filter(status=True,tipo=tipo).order_by('tipo', 'id')

    def traerrequisitospendiente(self):
        return self.personarequisitosconvocatoria_set.filter(status=True,estado=0).order_by('tipo', 'id')

    def ver_historial(self):
        return self.historialpersonaperiodoconvocatoria_set.filter(status=True).order_by('id')

    def __str__(self):
        return '{} {}'.format(self.periodo.__str__(), self.persona.__str__())

    def save(self, *args, **kwargs):
        super(PersonaPeriodoConvocatoria, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Persona Periodo"
        verbose_name_plural = u"Persona Periodo"


class HistorialPersonaPeriodoConvocatoria(ModeloBase):
    personaperiodo = models.ForeignKey(PersonaPeriodoConvocatoria, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona periodo")
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación Revisor')
    estado = models.IntegerField(choices=ESTADO_POSTULANTE_CONVOCATORIA, null=True, blank=True, verbose_name=u'Estado')

    def __str__(self):
        return '{} {}'.format(self.personaperiodo.__str__())

    class Meta:
        verbose_name = u"Historial Persona Periodo"
        verbose_name_plural = u"Historial Persona Periodo"


ESTADO_REQUISITO = (
    (0, u'PENDIENTE'),
    (1, u'CARGADO'),
    (2, u'ACEPTADO'),
    (3, u'RECHAZADO'),
)


class PersonaRequisitosConvocatoria(ModeloBase):
    participacion = models.ForeignKey(PersonaPeriodoConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Postulación')
    tipo = models.IntegerField(default=0,verbose_name='Tipo', choices=TIPO_REQUISITO)
    requisito = models.ForeignKey(RequisitosConvocatoriaPostulate, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Requisito')
    archivo = models.FileField(upload_to='requisitoconvocatoria', blank=True, null=True, verbose_name=u'Archivo')
    numhojas = models.IntegerField(default=0, verbose_name='Número de hojas PDF')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    estado = models.IntegerField(choices=ESTADO_REQUISITO, null=True, blank=True, verbose_name=u'Estado')
    fecha_subida = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Subida')
    revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Revisado por')
    observacion_revisor = models.TextField(default='', blank=True, null=True, verbose_name='Observación Revisor')
    fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión')

    def tiempo_subida(self):
        cal=relativedelta(datetime.now().date(), self.fecha_subida.date())
        anios= cal.years
        meses= cal.months
        dias = cal.days

        tiempo = datetime.now() - self.fecha_subida
        segundos = tiempo.seconds
        horas, segundos = divmod(segundos, 3600)
        minutos, segundos = divmod(segundos, 60)

        principal = str(segundos) + ' segundos' if segundos > 1 else str(segundos) + ' segundo'
        secundario = ''
        if anios > 0:
            principal = str(anios) + ' años' if anios > 1 else str(anios) + ' año'
            if not meses == 0:
                secundario = str(meses) + ' meses'if meses > 1 else str(meses) + ' mes'
        elif meses > 0 and anios == 0:
            principal = str(meses) + ' meses' if meses > 1 else str(meses) + ' mes'
            if dias > 0:
                secundario = str(dias) + ' días' if int(dias) > 1 else str(dias) + ' día'
        elif meses == 0 and anios == 0 and dias > 0:
            principal = str(dias) + ' días' if dias > 1 else str(dias) + ' día'
            if not horas == 0:
                secundario = str(horas) + ' horas' if horas > 1 else str(horas) + ' hora'
        elif meses == 0 and anios == 0 and dias == 0 and horas > 0:
            principal = str(horas) + ' horas'if horas > 1 else str(horas) + ' hora'
            if not minutos == 0:
                secundario=str(minutos) + ' minutos' if minutos > 1 else str(minutos) + ' minuto'
        elif meses == 0 and anios == 0 and dias == 0 and horas == 0 and minutos > 0:
            principal = str(minutos) + ' minutos 'if minutos > 1 else str(minutos) + ' minuto'
            if not segundos == 0:
                secundario=str(segundos) + ' segundos' if segundos > 1 else str(segundos) + ' segundo'
        tiemponatural = "{} {} ".format(principal, secundario)
        return tiemponatural

    def estado_color(self):
        label = 'label label-default'
        if self.estado == 0:
            label = 'label label-default'
        elif self.estado == 1:
            label = 'label label-primary'
        elif self.estado == 2:
            label = 'label label-success'
        elif self.estado == 3:
            label = 'label label-danger'
        return label

    def tipo_color(self):
        label = '#2e75b5'
        if self.tipo == 1:
            label = '#2e75b5'
        elif self.tipo == 2:
            label = '#2e75b5'
        elif self.tipo == 3:
            label = '#222a35'
        return label

    def __str__(self):
        return '{} - {} - {}'.format(self.participacion, self.get_estado_display(), self.requisito.__str__())

class PeriodoAcademicoConvocatoria(ModeloBase):
    #periodoacademico = models.ForeignKey('sga.Periodo', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Periodo")
    nombre = models.CharField(max_length=1000, verbose_name=u'Nombre del Periodo', null=True, blank=True)
    vigente = models.BooleanField(default=False, verbose_name='¿Vigente?')

    def __str__(self):
        return '{} '.format(self.nombre)

    def total_convocatorias(self):
        return len(self.periodoplanificacion_set.values('id').filter(status=True))

    def total_convocatorias_vigentes(self):
        return len(self.periodoplanificacion_set.values('id').filter(status=True, vigente=True))

    def total_partidas_vigentes(self):
        return len(Partida.objects.values('id').filter(status=True, periodoplanificacion__periodo=self, periodoplanificacion__vigente=True).distinct())

    def total_partidas(self):
        return len(Partida.objects.values('id').filter(status=True, periodoplanificacion__periodo=self).distinct())

    def preguntas(self):
        return self.preguntaperiodoplanificacion_set.filter(status=True)

    def configuracion_tipocompetencias(self):
        return self.requisitocompetenciaperiodo_set.filter(status=True)

class Convocatoria(ModeloBase):

    # modeloevaluativo = models.ForeignKey(ModeloEvaluativoConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Periodo académico configurado')
    descripcion = models.CharField(max_length=1000, blank=True, null=True, verbose_name='Descripción')
    finicio = models.DateField(verbose_name=u'Fecha Inicio Convocatoria', blank=True, null=True)
    ffin = models.DateField(verbose_name=u'Fecha Fin Convocatoria', blank=True, null=True)
    tipocontrato = models.ForeignKey(TipoContrato, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de Contrato')
    denominacionpuesto = models.ForeignKey('sagest.DenominacionPuesto', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Denominación de Puesto')
    modeloevaluativo = models.ForeignKey(ModeloEvaluativoDisertacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Modelo Evaluativo Disertacion')
    modeloevaluativoconvocatoria = models.ForeignKey(ModeloEvaluativoConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Modelo Evaluativo')
    vigente = models.BooleanField(default=False, verbose_name='¿Vigente?')
    muestracalificacion = models.BooleanField(default=False, verbose_name='¿Muestra calificaciones?')
    mostrarestado = models.BooleanField(default=False, verbose_name='¿Muestra estado?')
    apelacion = models.BooleanField(default=False, verbose_name='¿Apelación?')
    segundaetapa = models.BooleanField(default=False, verbose_name='¿Disertación/Apelación?')
    valtercernivel = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Tercer Nivel')
    valposgrado = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Cuarto Nivel')
    valdoctorado = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Doctorado')
    valcapacitacionmin = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Minimo Capacitación')
    valcapacitacionmax = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Máximo Capacitación')
    valexpdocentemin = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Minimo Experiencia Docente')
    valexpdocentemax = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Máximo Experiencia Docente')
    valexpadminmin = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Minimo Experiencia Administrativo')
    valexpadminmax = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor Máximo Experiencia Administrativo')
    departamento = models.ForeignKey("sagest.Departamento", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Departamento')
    archivo = models.FileField(upload_to='convocatoria', blank=True, null=True, verbose_name=u'Archivo de soporte para aperturar convocatoria')
    nummejorespuntuados = models.IntegerField(default=3, blank=True, null=True, verbose_name='Numero de mejores puntuados')

    def total_partidas(self):
        return len(self.partida_set.values('id').filter(status=True))

    def total_postulantes(self):
        return len(PersonaAplicarPartida.objects.values('id').filter(status=True, partida__convocatoria=self))

    def terminosycondiciones(self):
        return self.convocatoriaterminoscondiciones_set.filter(status=True).order_by('descripcion')

    def vigente_str(self):
        return 'fa fa-check-circle text-success' if self.vigente else 'fa fa-times-circle text-error'

    def puede_eliminar(self):
        if self.partida_set.filter(status=True):
            return False
        return True

    def horarios_activos(self, dia, turno):
        return HorarioConvocatoria.objects.filter(dia=dia, turno=turno, convocatoria=self,
                                                             status=True).order_by('turno__turno') if HorarioConvocatoria.objects.filter(
            dia=dia, convocatoria=self, status=True).exists() else ""

    def horarios_activos_postulante(self, dia, turno):
        return HorarioConvocatoria.objects.filter(dia=dia, turno=turno, convocatoria=self,
                                                             status=True).order_by('turno__turno') if HorarioConvocatoria.objects.filter(
            dia=dia, convocatoria=self, status=True).exists() else ""

    def existe_partida_armonizacion(self):
        if self.partida_set.values('id').filter(status=True, partidaarmonizacionnomenclaturatitulo__isnull=True).distinct().exists():
            return None
        return self.partida_set.filter(status=True, partidaarmonizacionnomenclaturatitulo__isnull=False).distinct()

    def __str__(self):
        return "{} ({} - {})".format(self.descripcion, str(self.finicio), str(self.ffin))

    class Meta:
        verbose_name = u"Convocatoria"
        verbose_name_plural = u"Convocatoria"


class ConvocatoriaTerminosCondiciones(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Convocatoria')
    descripcion = models.CharField(max_length=1200, blank=True, null=True, verbose_name='Titulo')

    def __str__(self):
        return '{}: {}'.format(self.convocatoria.descripcion, self.descripcion)

    class Meta:
        verbose_name = u"Convocatoria Terminos"
        verbose_name_plural = u"Convocatoria Terminos"


TIPO_CALIFICACION = (
    (1, u'GRADO ACADEMICO'),
    (2, u'EXPERIENCIA'),
    (3, u'CAPACITACIÓN'),
)


NIVEL_INSTRUCCION = (
    # (1, u'PRIMARIA'),
    # (2, u'SECUNDARIA'),
    (3, u'TERCER NIVEL'),
    (4, u'CUARTO NIVEL'),
    (5, u'PHD'),
)


TIEMPO_CALIFICACION_CONV = (
    (1, u'MESES'),
    (2, u'HORAS'),
)

ESTADO_PLANIFICACION = (
    (1, u'PENDIENTE'),
    (2, u'ENVIADO'),
    (3, u'APROBADO'),
    (4, u'RECHAZADO'),
)

class PeriodoPlanificacion(ModeloBase):
    periodo = models.ForeignKey(PeriodoAcademicoConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Periodo académico configurado')
    nombre = models.CharField(max_length=1000, verbose_name=u'Nombre Periodo Planificacion')
    finicio = models.DateField(verbose_name=u'Fecha Inicio Planificacion', blank=True, null=True)
    ffin = models.DateField(verbose_name=u'Fecha Fin Planificacion', blank=True, null=True)
    vigente = models.BooleanField(default=False, verbose_name='¿Vigente?')

    def total_periodos(self):
        return self.periodoplanificacion_set.filter(status=True).count()

    def total_partidas(self):
        return len(self.partida_set.values('id').filter(status=True))

    def total_postulantes(self):
        return len(PersonaAplicarPartida.objects.values('id').filter(status=True, partida__periodoplanificacion=self))

    def vigente_str(self):
        return 'fa fa-check-circle text-success' if self.vigente else 'fa fa-times-circle text-error'

    def puede_eliminar(self):
        if self.partida_set.filter(status=True):
            return False
        return True

    def __str__(self):
        return "{} ({} - {})".format(self.nombre, str(self.finicio), str(self.ffin))

    class Meta:
        verbose_name = u"Periodo Planificacion"
        verbose_name_plural = u"Periodos Planificacion"

class PreguntaPeriodoPlanificacion(ModeloBase):
    periodo = models.ForeignKey(PeriodoAcademicoConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Periodo académico configurado')
    pregunta = models.TextField(default='',verbose_name=u'Pregunta a realizar')
    requerido = models.BooleanField(default=True,verbose_name=u'La pregunta es requerida')

    def __str__(self):
        return f'{self.periodo}-{self.pregunta}'

    class Meta:
        verbose_name = u"Pregunta Periodo Planificacion"
        verbose_name_plural = u"Pregunta Periodos Planificacion"

class ConvocatoriaCalificacion(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Convocatoria')
    descripcion = models.CharField(max_length=1200, blank=True, null=True, verbose_name='Titulo')
    tipo = models.IntegerField(choices=TIPO_CALIFICACION, null=True, blank=True, verbose_name=u'Tipo')
    valor = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor')
    max = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor')
    min = models.IntegerField(default=0, blank=True, null=True, verbose_name='Valor')
    nivel = models.IntegerField(choices=NIVEL_INSTRUCCION, null=True, blank=True, verbose_name=u'Nivel de Instrucción')
    tiempo = models.IntegerField(choices=TIEMPO_CALIFICACION_CONV, null=True, blank=True, verbose_name=u'Tiempo')

    def __str__(self):
        return '{}: {}'.format(self.convocatoria.descripcion, self.descripcion)

    class Meta:
        verbose_name = u"Convocatoria Calificación"
        verbose_name_plural = u"Convocatoria Calificación"


class Partida(ModeloBase):
    convocatoria = models.ForeignKey(Convocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Convocatoria')
    denominacionpuesto = models.ForeignKey('sagest.DenominacionPuesto', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Denominacion Puesto')
    periodoplanificacion = models.ForeignKey(PeriodoPlanificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Periodo Planificacion')
    codpartida = models.CharField(max_length=500, blank=True, null=True, verbose_name='Código Partida')
    titulo = models.CharField(max_length=1200, blank=True, null=True, verbose_name='Titulo')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripcion')
    carrera = models.ForeignKey('sga.Carrera', default=True, blank=True, null=True, verbose_name='Carrera', on_delete=models.PROTECT)
    campoamplio = models.ManyToManyField('sga.AreaConocimientoTitulacion', verbose_name=u'Campo Amplio')
    campoespecifico = models.ManyToManyField('sga.SubAreaConocimientoTitulacion', verbose_name=u'Campo Especifico')
    campodetallado = models.ManyToManyField('sga.SubAreaEspecificaConocimientoTitulacion', verbose_name=u'Campo Detallado')
    titulos = models.ManyToManyField('sga.Titulo', verbose_name=u'Titulos Relacionados')
    nivel = models.IntegerField(choices=NIVEL_INSTRUCCION, null=True, blank=True, verbose_name=u'Nivel de Instrucción')
    modalidad = models.IntegerField(choices=MODALIDAD_PARTIDA, null=True, blank=True, verbose_name=u'Modalidad')
    dedicacion = models.IntegerField(choices=DEDICACION_PARTIDA, null=True, blank=True, verbose_name=u'Dedicación')
    jornada = models.IntegerField(choices=JORNADA_PARTIDA, null=True, blank=True, verbose_name=u'Jornada')
    ano = models.IntegerField(choices=JORNADA_PARTIDA, null=True, blank=True, verbose_name=u'Jornada')
    rmu = models.FloatField(blank=True, null=True, verbose_name=u'Remuneracion Mensual Unificada')
    vigente = models.BooleanField(default=False, verbose_name='¿Vigente?')
    cerrada = models.BooleanField(default=False, verbose_name='¿Cerrada?')
    estado = models.IntegerField(choices=ESTADO_PLANIFICACION, null=True, blank=True, verbose_name=u'Estado Planificacion')
    temadisertacion = models.TextField(blank=True, null=True, verbose_name='Tema disertacion')
    observacion = models.TextField(blank=True, null=True, verbose_name='Observacion')
    minhourcapa = models.IntegerField(blank=True,null=True, verbose_name='Minimo hora capacitacion', default=0)
    minmesexp = models.IntegerField(blank=True,null=True, verbose_name='Minimo meses experiencia', default=0)

    def __str__(self):
        return '({}) {}'.format(self.codpartida, self.denominacionpuesto.descripcion if self.denominacionpuesto else '')

    class Meta:
        verbose_name = u"Partida"
        verbose_name_plural = u"Partidas"

    def participantes_mejores_puntuados(self):
        return self.personaaplicarpartida_set.filter(status=True, esmejorpuntuado=True).order_by('-nota_final_meritos')

    def participantes_banco_aspirantes(self):
        return self.personaaplicarpartida_set.filter(status=True, estado__in=[1,4]).order_by('-nota_final_meritos')[self.convocatoria.nummejorespuntuados:]

    def participantes(self):
        return self.personaaplicarpartida_set.filter(status=True).order_by('persona__apellido1')

    def total_sexo(self):
        hombres = len(self.personaaplicarpartida_set.filter(status=True, persona__sexo_id=2))
        mujeres = len(self.personaaplicarpartida_set.filter(status=True, persona__sexo_id=1))
        return {'t_hombres':hombres, 't_mujeres':mujeres}

    def participantes_apelando(self):
        return self.personaaplicarpartida_set.filter(status=True, solapelacion=True).order_by('persona__apellido1')

    def total_postulantes(self):
        return self.personaaplicarpartida_set.values('id').filter(status=True).count()

    def puede_aplicar_postulante_nivel(self, persona):
        return Titulacion.objects.values('id').filter(persona=persona, titulo__nivel__nivel__gte=self.nivel).exists()

    def permite_aplicar(self):
        hoy = datetime.now().date()
        return self.vigente and self.convocatoria.finicio <= hoy <= self.convocatoria.ffin

    def existe_relacion(self):
        return not self.personaaplicarpartida_set.values('id').exists()

    def partidas_asignaturas(self):
        return self.partidaasignaturas_set.filter(status=True).order_by('asignatura__nombre')

    def vigente_str(self):
        return 'fa fa-check-circle text-success' if self.vigente else 'fa fa-times-circle text-error'

    def puede_eliminar(self):
        if self.personaaplicarpartida_set.values('id').exists():
            return False
        return True

    def cargos_tribunal(self, etapa):
        return self.partidatribunal_set.filter(status=True,tipo=etapa)

    def ganador(self):
        return self.personaaplicarpartida_set.values('id').filter(status=True,estado__in=[1,4],esganador=True).exists()

    def banco_elegible(self):
        return self.personaaplicarpartida_set.filter(status=True, estado__in=[1,4], finsegundaetapa=True, nota_final__gte=70, esganador=False).order_by('-nota_final')[:3]

    def cumple_con_capacitaciones_requeridas(self, id_evaluar):
        ids_tiposcompetencias = self.detallecapacitacionplanificacion_set.values_list('tipocompetencia_id', flat=True).filter(status=True)
        listado_cumplimiento = []
        estado_cumplimiento_general = True
        tipos_competencias = TipoCompetenciaPlanificacion.objects.filter(pk__in=ids_tiposcompetencias)

        for tipo_competencia in tipos_competencias:
            capacitaciones = self.detallecapacitacionplanificacion_set.filter(status=True,tipocompetencia=tipo_competencia)
            requisitos = tipo_competencia.requisitocompetenciaperiodo_set.filter(periodo=self.periodoplanificacion.periodo, status=True)
            for req in requisitos:
                req_competencia = req.requisito_competencia
                content_type = req_competencia.content_type
                object_id = req_competencia.object_id
                tiempo_capacitacion = capacitaciones.aggregate(total_horas=Coalesce(Sum('canttiempocapacitacion'), 0, output_field=models.IntegerField()))['total_horas']#canttiempocapacitacion
                instancia = content_type.model_class()
                query = instancia.objects
                filtros = req_competencia.filtro % id_evaluar if req_competencia.filtro.find('%s') > -1 else req_competencia.filtro
                query = query.filter(eval(f'Q({filtros})')) if req_competencia.filtro else query.filter(status=True)
                horas_cumplidas = query.aggregate(total_horas=Coalesce(Sum(req_competencia.campo_calculo), 0, output_field=models.IntegerField()))['total_horas']
                estado_cumplimiento = horas_cumplidas >= tiempo_capacitacion
                estado_cumplimiento_general &= estado_cumplimiento
                #print(content_type.id, object_id, tiempo_capacitacion, horas_cumplidas, estado_cumplimiento)
                listado_cumplimiento.append([req, tiempo_capacitacion, horas_cumplidas, estado_cumplimiento])

        # for capacitacion in capacitaciones:
        #     requisitos = capacitacion.tipocompetencia.requisitocompetenciaperiodo_set.filter(periodo=self.periodoplanificacion.periodo, status=True)
        #     for req in requisitos:
        #         req_competencia = req.requisito_competencia
        #         content_type = req_competencia.content_type
        #         object_id = req_competencia.object_id
        #         tiempo_capacitacion = capacitacion.canttiempocapacitacion
        #         instancia = content_type.model_class()
        #         query = instancia.objects
        #         filtros = req_competencia.filtro % id_evaluar if req_competencia.filtro.find('%s') > -1 else req_competencia.filtro
        #         query = query.filter(eval(f'Q({filtros})')) if req_competencia.filtro else query.filter(status=True)
        #         horas_cumplidas = query.aggregate(total_horas=Coalesce(Sum(req_competencia.campo_calculo), 0, output_field=models.IntegerField()))['total_horas']
        #         estado_cumplimiento = horas_cumplidas >= tiempo_capacitacion
        #         estado_cumplimiento_general &= estado_cumplimiento
        #         print(content_type.id, object_id, tiempo_capacitacion, horas_cumplidas, estado_cumplimiento)
        #         listado_cumplimiento.append([req, tiempo_capacitacion, horas_cumplidas, estado_cumplimiento])

        return {'estado_general': estado_cumplimiento_general, 'listado_requisitos': listado_cumplimiento}

    def obtener_titulo_amortizacion(self):
        if not self.partidaarmonizacionnomenclaturatitulo_set.filter(status=True).values('id').exists():
            return []
        return self.partidaarmonizacionnomenclaturatitulo_set.filter(status=True).values_list('combinacion__id',flat=True)

    def obtener_titulos(self):
        if not self.partidaarmonizacionnomenclaturatitulo_set.filter(status=True).values('id').exists():
            return None
        return self.partidaarmonizacionnomenclaturatitulo_set.filter(status=True)

    def obtener_armonizacion(self):
        id_armonizacion = self.partidaarmonizacionnomenclaturatitulo_set.filter(status=True).values_list('combinacion__id', flat=True)
        return ArmonizacionNomenclaturaTitulo.objects.filter(status=True,id__in=id_armonizacion)

    def cumple_horas_exp_cap_mayor_limite(self,persona):
        hoy = datetime.now().date()
        experiencias = persona.mis_experienciaslaborales()
        capacitaciones_externa_todas = persona.mis_capacitaciones().filter(horas__gte=self.minhourcapa).order_by('-horas')
        capacitaciones_internas_todas = persona.mis_capacitacioneseducontinua().filter(capeventoperiodo__horas__gte=self.minhourcapa).order_by('-capeventoperiodo__horas')

        # capacitaciones_externa = persona.mis_capacitaciones().aggregate(total_horas=Sum('horas'))['total_horas']
        # capacitaciones_internas = persona.mis_capacitacioneseducontinua().aggregate(total_horas=Sum('capeventoperiodo__horas'))['total_horas']

        if len(experiencias)>0:
            meses = experiencias.aggregate(
                    total_meses=Sum(
                        Case(
                            When(fechafin__isnull=True, then=Extract(hoy, 'year') * 12 + Extract(hoy, 'month') - Extract('fechainicio', 'year') * 12 - Extract('fechainicio', 'month')),
                            default=Extract('fechafin', 'year') * 12 + Extract('fechafin', 'month') - Extract('fechainicio', 'year') * 12 - Extract('fechainicio', 'month')
                        ),
                        output_field=DateTimeField()
                    )
                )['total_meses']
        else:
            meses = 0
        # horas_capacitaciones = capacitaciones_internas+capacitaciones_externa
        cumple_exp = True if meses >= self.minmesexp else False
        cumple_capa = True
        horas_final_capa=0
        if self.minhourcapa > 0:
            cumple_capa = False
            if capacitaciones_externa_todas:
                cumple_capa = True
                horas_final_capa=capacitaciones_externa_todas.first().horas
            if capacitaciones_internas_todas:
                cumple_capa = True
                horas_final_capa = capacitaciones_internas_todas.first().capeventoperiodo.horas
        return [cumple_exp, cumple_capa, meses, horas_final_capa]

    def cumple_horas_exp_cap_suma(self,persona):
        hoy = datetime.now().date()
        experiencias = persona.mis_experienciaslaborales()
        capacitaciones_externa = persona.mis_capacitaciones().aggregate(total_horas=Sum('horas'))['total_horas']
        capacitaciones_internas = persona.mis_capacitacioneseducontinua().aggregate(total_horas=Sum('capeventoperiodo__horas'))['total_horas']

        if len(experiencias)>0:
            meses = experiencias.aggregate(
                    total_meses=Sum(
                        Case(
                            When(fechafin__isnull=True, then=Extract(hoy, 'year') * 12 + Extract(hoy, 'month') - Extract('fechainicio', 'year') * 12 - Extract('fechainicio', 'month')),
                            default=Extract('fechafin', 'year') * 12 + Extract('fechafin', 'month') - Extract('fechainicio', 'year') * 12 - Extract('fechainicio', 'month')
                        ),
                        output_field=DateTimeField()
                    )
                )['total_meses']
        else:
            meses = 0
        capacitaciones_externa = capacitaciones_externa if capacitaciones_externa else 0
        capacitaciones_internas = capacitaciones_internas if capacitaciones_internas else 0
        horas_capacitaciones = capacitaciones_internas+capacitaciones_externa
        cumple_exp = True if meses >= self.minmesexp else False
        cumple_capa = True if horas_capacitaciones >= self.minhourcapa else False

        return [cumple_exp, cumple_capa, meses, horas_capacitaciones]

    def tribunal_primeraetapa(self):
        return self.partidatribunal_set.filter(status=True, tipo=1)

    def tribunal_segundaetapa(self):
        return self.partidatribunal_set.filter(status=True, tipo=2)

    def actas_partida(self):
        return self.actapartida_set.filter(status=True)

    def actas_primera_etapa(self):
        return self.actapartida_set.filter(status=True, tipotribunal=1)

    def actas_segunda_etapa(self):
        return self.actapartida_set.filter(status=True, tipotribunal=2)

ESTADO_PLANIFICACION_ACEPTACION = (
    #(1, u'PENDIENTE'),
    #(2, u'ENVIADO'),
    (3, u'APROBADO'),
    (4, u'RECHAZADO'),
)

ESTADO_PLANIFICACION_CREACION = (
    (1, u'PENDIENTE'),
    (2, u'ENVIADO'),
    #(3, u'APROBADO'),
    #(4, u'RECHAZADO'),
)

class TipoCompetenciaPlanificacion(ModeloBase):
    nombre = models.TextField(blank=True, null=True, verbose_name='Nombre')
    aplicasubtipo = models.BooleanField(default=True, verbose_name='Aplica Sub Tipo')

    class Meta:
        verbose_name = u"Tipo competencia Planificacion"
        verbose_name_plural = u"Tipos competencias Planificacion"

    def __str__(self):
        return '{}'.format(self.nombre)

TIPOS_PARAMETRO_REQUISITO = (
    *TIPOS_PARAMETRO_REPORTE,
)


class RequisitoCompetencia(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de contenido general')
    object_id = models.IntegerField(blank=True, null=True, verbose_name=u'Objeto id')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    tipo = models.IntegerField(choices=TIPOS_PARAMETRO_REQUISITO, default=1, verbose_name=u'Tipo de parametro')
    filtro = models.TextField(blank=True, null=True, verbose_name=u'filtro a clase relacionada')
    campo_calculo = models.CharField(default='', max_length=200, verbose_name=u'Campo cálculo')

    class Meta:
        verbose_name = u"Requisito competencia"
        verbose_name_plural = u"Requisitos competencias"

    def __str__(self):
        return '{}'.format(self.nombre)


class DetalleRequisitoCompetencia(ModeloBase):
    requisito_competencia = models.ForeignKey(RequisitoCompetencia, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de contenido')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de contenido')
    nombre = models.TextField(blank=True, null=True, verbose_name='Nombre')
    descripcion = models.CharField(default='', max_length=200, verbose_name=u'Descripción')
    tipo = models.IntegerField(choices=TIPOS_PARAMETRO_REQUISITO, default=1, verbose_name=u'Tipo de parametro')
    filtro = models.CharField(default='', max_length=200, verbose_name=u'filtro a clase relacionada', blank=True)

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Parametro de requisito"
        verbose_name_plural = u"Parametros de requisitos"
        ordering = ['nombre']
        #unique_together = ('reporte', 'nombre',)


class RequisitoCompetenciaPeriodo(ModeloBase):
    requisito_competencia = models.ForeignKey(RequisitoCompetencia, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de contenido')
    periodo = models.ForeignKey(PeriodoAcademicoConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo de contenido')
    tipo_competencia = models.ForeignKey(TipoCompetenciaPlanificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo competecia planificación')
    es_opcional = models.BooleanField(default=False, verbose_name='¿Es opcional?')

    def __str__(self):
        return u'%s - %s - %s' % (self.periodo, self.tipo_competencia, self.requisito_competencia)

    class Meta:
        verbose_name = u"Parametro de requisito"
        verbose_name_plural = u"Parametros de requisitos"
        #ordering = ['nombre']


class TipoCompetenciaEspecificaPlanificacion(ModeloBase):
    nombre = models.TextField(blank=True, null=True, verbose_name='Nombre')

    class Meta:
        verbose_name = u"Tipo competencia especifica Planificacion"
        verbose_name_plural = u"Tipos competencias específicas Planificacion"

    def __str__(self):
        return '{}'.format(self.nombre)


TIEMPO_CAPACITACION = (
    (1, u'HORAS'),
    (2, u'DIAS'),
    (3, u'MESES'),
    (4, u'AÑOS'),
)

class DetalleCapacitacionPlanificacion(ModeloBase):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Partida')
    tiempocapacitacion = models.IntegerField(choices=TIEMPO_CAPACITACION, null=True, blank=True, verbose_name=u'Tiempo de capacitacion')
    canttiempocapacitacion = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Cantidad tiempo capacitacion')
    cespecifica=models.ForeignKey(TipoCompetenciaEspecificaPlanificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo competencia especifica Planificacion')
    tipocompetencia=models.ForeignKey(TipoCompetenciaPlanificacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo competencia Planificacion')
    descripcioncapacitacion = models.TextField(blank=True, null=True, verbose_name='Descripcion de capacitacion')


    def participantes_mejores_puntuados(self):
        return self.personaaplicarpartida_set.filter(status=True, estado__in=[1,4]).order_by('-nota_final_meritos')[:3]

    def participantes_banco_aspirantes(self):
        return self.personaaplicarpartida_set.filter(status=True, estado__in=[1,4]).order_by('-nota_final_meritos')[3:]

    def participantes(self):
        return self.personaaplicarpartida_set.filter(status=True).order_by('persona__apellido1')

    def participantes_apelando(self):
        return self.personaaplicarpartida_set.filter(status=True, solapelacion=True).order_by('persona__apellido1')

    def total_postulantes(self):
        return self.personaaplicarpartida_set.values('id').filter(status=True).count()

    def puede_aplicar_postulante_nivel(self, persona):
        return Titulacion.objects.values('id').filter(persona=persona, titulo__nivel__nivel__gte=self.nivel).exists()

    def permite_aplicar(self):
        hoy = datetime.now().date()
        return self.vigente and self.convocatoria.finicio <= hoy <= self.convocatoria.ffin

    def existe_relacion(self):
        return not self.personaaplicarpartida_set.values('id').exists()

    def partidas_asignaturas(self):
        return self.partidaasignaturas_set.filter(status=True).order_by('asignatura__nombre')

    def vigente_str(self):
        return 'fa fa-check-circle text-success' if self.vigente else 'fa fa-times-circle text-error'

    def puede_eliminar(self):
        if self.personaaplicarpartida_set.values('id').exists():
            return False
        return True

    def cargos_tribunal(self, etapa):
        return self.partidatribunal_set.filter(status=True,tipo=etapa)

    def ganador(self):
        return self.personaaplicarpartida_set.values('id').filter(status=True,estado__in=[1,4],esganador=True).exists()

    def __str__(self):
        return '({}), {}'.format(self.cespecifica, self.tipocompetencia)

    class Meta:
        verbose_name = u"Detalle Capacitacion Partida"
        verbose_name_plural = u"Detalle Capacitacion Partida"

class DetalleCompetenciaPlanificacion(ModeloBase):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Partida')
    competencialaboral=models.ForeignKey(DetalleCompetenciaLaboral, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo competencia especifica Planificacion')

    def __str__(self):
        return '({}), {}'.format(self.competencialaboral, self.partida)

    class Meta:
        verbose_name = u"Detalle competencia laboral partida"
        verbose_name_plural = u"Detalles competencias laborales partida"


class PartidaAsignaturas(ModeloBase):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Partida')
    asignatura = models.ForeignKey(Asignatura, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u'Asignatura Malla')

    class Meta:
        verbose_name = u"Asignatura Partida"
        verbose_name_plural = u"Asignatura Partida"

    def __str__(self):
        return '({}) {}'.format(self.partida.codpartida, self.asignatura.__str__())


class PartidaTribunal(ModeloBase):
    tipo = models.IntegerField(choices=TIPO_TRIBUNAL, default=1, verbose_name=u'Tipo Tribunal')
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Partida')
    persona = models.ForeignKey('sga.Persona', on_delete=models.PROTECT, blank=True, null=True, verbose_name=u'Persona')
    cargos = models.IntegerField(choices=CARGOS_TRIBUNAL, null=True, blank=True, verbose_name=u'Cargos')
    firma = models.BooleanField(default=False, verbose_name='¿Firma?')
    item = models.ForeignKey(DetalleModeloEvaluativoConvocatoria, verbose_name=u"Item que califica",blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = u"Tribunal Partida"
        verbose_name_plural = u"Tribunal Partida"

    def __str__(self):
        return '{}: {}'.format(self.get_cargos_display(), self.persona.__str__())


ESTADOS_APLICACION = (
    (0, u'PENDIENTE'),
    (1, u'VALIDADO'),
    (2, u'RECHAZADO'),
    (3, u'APELANDO'),
    (4, u'APROBADO'),
    (5, u'REPROBADO'),
)


class PersonaAplicarPartida(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    partida = models.ForeignKey(Partida, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Partida Aplicada")
    # MERITOS
    pgradoacademico = models.FloatField(default=0, verbose_name=u"Nota Grado Academico")
    obsgradoacademico = models.TextField(default='', verbose_name='Observación Experiencia')
    pexpdocente = models.FloatField(default=0, verbose_name=u"Nota Experiencia Docente")
    obsexperienciadoc = models.TextField(default='', verbose_name='Observación Experiencia Docente')
    pexpadministrativa = models.FloatField(default=0, verbose_name=u"Nota Experiencia Administrativo")
    obsexperienciaadmin = models.TextField(default='', verbose_name='Observación Experiencia Administrativo')
    pcapacitacion = models.FloatField(default=0, verbose_name=u"Nota Capacitaciones")
    obscapacitacion = models.TextField(default='', verbose_name='Observación Capacitación')
    obsgeneral = models.TextField(default='', verbose_name='Observación General')
    estado = models.IntegerField(choices=ESTADOS_APLICACION, default=0, verbose_name=u'Estado Postulación')
    calificada = models.BooleanField(default=False, verbose_name='¿Calificada?')
    revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Revisado por')
    fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión')
    # DESEMPATE
    aplico_desempate = models.BooleanField(default=False, verbose_name='¿Desempate?')
    pdmaestria = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Maestrias")
    pdphd = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Phd")
    pdexpdocente = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Experiencia Docente")
    pdcappeda = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Capacitacion Pedagocica")
    valpdcapprof = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Capacitacion Profesional')
    pdcapprof = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Capacitacion Profesional")
    valpdidioma = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Idioma Extranjero')
    pdidioma = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Idioma Extranjero")
    valpdepub1 = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Publicación Cientifica (JCR, Scopus)')
    pdepub1 = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Publicación Cientifica (JCR, Scopus)")
    valpdepub2 = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Publicación Cientifica (Regionales, Latindex)')
    pdepub2 = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Publicación Cientifica (Regionales, Latindex)")
    valpdecongreso = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Participación Congresos')
    pdecongreso = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Participación Congresos")
    valpdaccionafirmativa = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Acción Afirmativa')
    pdaccionafirmativa = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Acción Afirmativa")
    obdadicional = models.CharField(default='', max_length=1000, blank=True, null=True, verbose_name='Obs. Desempate')
    pdadicional = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Observación Adicional")
    desempate_revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Desempate Revisado por')
    desempate_fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Desempate Fecha Revisión')
    # APELACION
    solapelacion = models.BooleanField(default=False, verbose_name='¿Registro una apelación?')
    # SEGUNDA ETAPA
    finsegundaetapa = models.BooleanField(default=False, verbose_name='¿Finaliza Segundo Etapa?')
    setapa_revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Segunda Etapa Revisado por')
    setapa_fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Segunda Etapa Fecha Revisión')
    # NOTAS
    nota_calificacion = models.FloatField(default=0, verbose_name=u"Nota Meritos (Desempates) Historico")
    nota_desempate = models.FloatField(default=0, verbose_name=u"Nota Desempate")
    nota_final_meritos = models.FloatField(default=0, verbose_name=u"Nota Meritos")
    nota_final_disertacion = models.FloatField(default=0, verbose_name=u"Nota Disertación")
    nota_final_entrevista = models.FloatField(default=0, verbose_name=u"Nota Entrevista")
    nota_final = models.FloatField(default=0, verbose_name=u"Nota Final Disertación + Entrevista")
    # CAMPOS FINALES
    esganador = models.BooleanField(default=False, verbose_name='¿Es Ganador?')
    esmejorpuntuado = models.BooleanField(default=False, verbose_name='¿Es mejorpuntuado?')
    # IMPORTAR
    archivojustificacion = models.FileField(upload_to='Archivo', blank=True, null=True, verbose_name=u'Archivo de justificación para importar postulante')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')
    #ARCHIVO PRUEBA PSICOLOGICA
    archivopsc = models.FileField(upload_to='Archivo', blank=True, null=True, verbose_name=u'Archivo de resultados de la prueba psicologica.')


    def soy_mejor_puntuado(self):
        return self.id in self.partida.participantes_mejores_puntuados().values_list('id', flat=True)

    def soy_banco_elegible(self):
        return self.id in self.partida.participantes_banco_aspirantes().values_list('id', flat=True)

    def total_segunda_etapa(self):
        try:
            if self.partida.convocatoria.modeloevaluativoconvocatoria:
                return self.nota_final
            evadis_ = self.traer_calificacion_disertacion().nota_porcentual_70() if self.traer_calificacion_disertacion() else 0
            evaent_ = self.traer_calificacion_entrevista().nota_porcentual_30() if self.traer_calificacion_entrevista() else 0
            return evaent_ + evadis_
        except Exception as ex:
            return 0

    def traer_calificacion_disertacion(self):
        return self.calificaciondisertacion_set.filter(status=True).order_by('id').last()

    def traer_calificacion_entrevista(self):
        return self.calificacionentrevista_set.filter(status=True).order_by('id').last()

    def get_nota_final_disertacion(self):
        if self.partida.convocatoria.modeloevaluativoconvocatoria:
            return self.nota_final - self.nota_final_entrevista
        else:
            cal = self.traer_calificacion_disertacion()
            if cal:
                return cal.nota_porcentual_70()
            return 0

    def get_nota_final_entrevista(self):
        if self.partida.convocatoria.modeloevaluativoconvocatoria:
            return self.nota_final_entrevista
        else:
            cal = self.traer_calificacion_entrevista()
            if cal:
                return cal.nota_porcentual_30()
            return 0

    def get_nota_disertacion(self):
        context = {}
        finalizada = False
        revisado_por = ''
        fecha_revision = ''
        codigo = ''
        notadisertacion = ''
        if self.partida.convocatoria.modeloevaluativoconvocatoria:
            finalizada = True
            notadisertacion = round(self.nota_final - self.nota_final_entrevista, 2)
            revisado_por = str(self.revisado_por)
            fecha_revision = self.fecha_revision.strftime('%d-%m-%Y | %H:%M') if self.fecha_revision else ''
        else:
            cal = self.traer_calificacion_disertacion()
            if cal:
                notadisertacion = cal.nota_porcentual_70()
                finalizada = cal.finalizada
                revisado_por = str(cal.revisado_por)
                fecha_revision = cal.fecha_revision.strftime('%d-%m-%Y | %H:%M') if cal.fecha_revision else ''
                codigo = cal.id
        context['notadisertacion'] = notadisertacion
        context['finalizada'] = finalizada
        context['revisado_por'] = revisado_por
        context['fecha_revision'] = fecha_revision
        context['codigo'] = codigo
        return context

    def get_nota_entrevista(self):
        context = {}
        finalizada = False
        revisado_por = ''
        fecha_revision = ''
        codigo = ''
        notaentrevista = ''
        if self.partida.convocatoria.modeloevaluativoconvocatoria:
            finalizada = True
            notaentrevista = round(self.nota_final_entrevista, 2)
            revisado_por = str(self.setapa_revisado_por)
            fecha_revision = self.setapa_fecha_revision.strftime('%d-%m-%Y | %H:%M') if self.setapa_fecha_revision else ''
        else:
            cal = self.traer_calificacion_entrevista()
            if cal:
                notaentrevista = cal.nota_porcentual_30()
                finalizada = cal.finalizada
                revisado_por = str(cal.revisado_por)
                fecha_revision = cal.fecha_revision.strftime('%d-%m-%Y | %H:%M') if cal.fecha_revision else ''
                codigo = cal.id
        context['notaentrevista'] = notaentrevista
        context['finalizada'] = finalizada
        context['revisado_por'] = revisado_por
        context['fecha_revision'] = fecha_revision
        context['codigo'] = codigo
        return context

    def traer_agenda_entrevista(self):
        return self.convocatoriapostulante_set.filter(status=True).order_by('id').last()

    def traer_apelacion(self):
        return self.personaapelacion_set.filter(status=True).order_by('id').last()

    def traer_last_calificacion(self):
        return self.calificacionpostulacion_set.filter(status=True, vigente=True).order_by('id').last()

    def aplica_puntuacion(self):
        return True if self.nota_final_meritos >= 70 else False

    def total_puntos_gradoacademico(self):
        try:
            puntos = 0
            tercer_nivel = PersonaFormacionAcademicoPartida.objects.filter(personapartida=self, aceptado=True, titulo__nivel__nivel=3)
            cuarto_nivel = PersonaFormacionAcademicoPartida.objects.filter(personapartida=self, aceptado=True, titulo__nivel__nivel=4)
            phd = PersonaFormacionAcademicoPartida.objects.filter(personapartida=self, aceptado=True, titulo__nivel__nivel=5)
            if tercer_nivel.exists():
                puntos = self.partida.convocatoria.valtercernivel if self.partida.convocatoria.valtercernivel else 0
            if cuarto_nivel.exists():
                puntos = self.partida.convocatoria.valposgrado if self.partida.convocatoria.valposgrado else 0
            if phd.exists():
                puntos = self.partida.convocatoria.valdoctorado if self.partida.convocatoria.valdoctorado else 0
            return puntos
        except Exception as ex:
            return 0

    def total_horas_capacitacion(self):
        try:
            return PersonaCapacitacionesPartida.objects.filter(personapartida=self).aggregate(total=Sum(F('horas'))).get('total')
        except Exception as ex:
            return 0

    def primera_hora_capacitacion_cumple(self):
        try:
            capacitaciones_partida_todas = PersonaCapacitacionesPartida.objects.filter(personapartida=self,
                                                                                       horas__gte=self.partida.minhourcapa).order_by("-horas")
            if capacitaciones_partida_todas:
                return capacitaciones_partida_todas.first().horas
            return 0
        except Exception as ex:
            return 0

    def total_meses_experiencia(self):
        try:
            hoy = datetime.now().date()
            experiencias = PersonaExperienciaPartida.objects.filter(personapartida=self)
            meses=0
            if len(experiencias) > 0:
                meses = experiencias.aggregate(
                    total_meses=Sum(
                        Case(
                            When(fechafin__isnull=True,
                                 then=Extract(hoy, 'year') * 12 + Extract(hoy, 'month') - Extract('fechainicio',
                                                                                                  'year') * 12 - Extract(
                                     'fechainicio', 'month')),
                            default=Extract('fechafin', 'year') * 12 + Extract('fechafin', 'month') - Extract(
                                'fechainicio', 'year') * 12 - Extract('fechainicio', 'month')
                        ),
                        output_field=DateTimeField()
                    )
                )['total_meses']
            else:
                meses = 0
            return meses
        except Exception as ex:
            return 0

    def cumple_horas_exp_cap_mayor_limite(self):
        hoy = datetime.now().date()
        experiencias = PersonaExperienciaPartida.objects.filter(personapartida=self)
        capacitaciones_partida_todas=PersonaCapacitacionesPartida.objects.filter(personapartida=self,horas__gte=self.partida.minhourcapa).order_by("-horas")
        if len(experiencias)>0:
            meses = experiencias.aggregate(
                    total_meses=Sum(
                        Case(
                            When(fechafin__isnull=True, then=Extract(hoy, 'year') * 12 + Extract(hoy, 'month') - Extract('fechainicio', 'year') * 12 - Extract('fechainicio', 'month')),
                            default=Extract('fechafin', 'year') * 12 + Extract('fechafin', 'month') - Extract('fechainicio', 'year') * 12 - Extract('fechainicio', 'month')
                        ),
                        output_field=DateTimeField()
                    )
                )['total_meses']
        else:
            meses = 0
        cumple_exp = True if meses >= self.partida.minmesexp else False
        cumple_capa = False
        horas_final_capa=0
        if capacitaciones_partida_todas:
            cumple_capa = True
            horas_final_capa=capacitaciones_partida_todas.first().horas
        return [cumple_exp, cumple_capa, meses, horas_final_capa]

    def total_puntos_capacitacion(self):
        try:
            from django.db.models.functions import Coalesce
            from django.db.models import F, Sum, FloatField
            puntos = 0
            total_horas = 0
            for l in PersonaCapacitacionesPartida.objects.filter(personapartida=self, aceptado=True):
                total_horas += l.horas
            if total_horas == 40:
                puntos = self.partida.convocatoria.valcapacitacionmin if self.partida.convocatoria.valcapacitacionmin else 0
            elif total_horas > 40:
                puntos = self.partida.convocatoria.valcapacitacionmax if self.partida.convocatoria.valcapacitacionmax else 0
            return puntos
        except Exception as ex:
            return 0

    def total_puntos_experiencia_docente(self):
        try:
            puntos = 0
            listexp = PersonaExperienciaPartida.objects.filter(personapartida=self, actividadlaboral_id=2, aceptado=True)
            total_meses = 0
            for le in listexp:
                total_meses += le.meses()
            if total_meses == 12:
                puntos = self.partida.convocatoria.valexpdocentemin if self.partida.convocatoria.valexpdocentemin else 0
            elif total_meses > 12:
                puntos = self.partida.convocatoria.valexpdocentemax if self.partida.convocatoria.valexpdocentemax else 0
            return puntos
        except Exception as ex:
            return 0

    def total_puntos_experiencia_administrativo(self):
        try:
            puntos = 0
            listexp = PersonaExperienciaPartida.objects.filter(personapartida=self, actividadlaboral_id=1, aceptado=True)
            total_meses = 0
            for le in listexp:
                total_meses += le.meses()
            if total_meses == 12:
                puntos = self.partida.convocatoria.valexpadminmin if self.partida.convocatoria.valexpadminmin else 0
            elif total_meses > 12:
                puntos = self.partida.convocatoria.valexpadminmax if self.partida.convocatoria.valexpadminmax else 0
            return puntos
        except Exception as ex:
            return 0

    def aplica_desempate_yes(self):
        if self.calificada:
            return PersonaAplicarPartida.objects.filter(status=True, calificada=True, partida=self.partida, nota_final_meritos=self.nota_final_meritos, estado__in=[1,4]).exclude(id=self.id).exists()
        else:
            return False

    def total_desempate_maestria(self):
        cuarto_nivel = PersonaFormacionAcademicoPartida.objects.filter(personapartida=self, aceptado=True, titulo__nivel__nivel=4).count()
        return 2 if cuarto_nivel > 1 else 0

    def total_desempate_phd(self):
        phd_nivel = PersonaFormacionAcademicoPartida.objects.filter(personapartida=self, aceptado=True, titulo__nivel__nivel=5).count()
        return 2 if phd_nivel > 1 else 0

    def total_desempate_experiencia_docente(self):
        try:
            puntos = 0
            listexp = PersonaExperienciaPartida.objects.filter(personapartida=self, actividadlaboral_id=2, aceptado=True)
            total_meses = 0
            for le in listexp:
                total_meses += le.meses()
            return 1 if int(total_meses) >= 36 else 0
        except Exception as ex:
            return 0

    def total_desempate_capacitacion(self):
        try:
            from django.db.models.functions import Coalesce
            from django.db.models import F, Sum, FloatField
            total_horas = 0
            for th in PersonaCapacitacionesPartida.objects.filter(personapartida=self, aceptado=True):
                total_horas += th.horas
            return 1 if int(total_horas) >= 200 else 0
        except Exception as ex:
            return 0

    def total_puntos_desempate(self):
        try:
            puntos = self.total_desempate_maestria() + self.total_desempate_phd() + self.total_desempate_experiencia_docente() + self.total_desempate_capacitacion() + int(self.pdadicional)
            if self.valpdcapprof:
                puntos += self.pdcapprof
            if self.valpdidioma:
                puntos += self.pdidioma
            if self.valpdepub1:
                puntos += self.pdepub1
            if self.valpdepub2:
                puntos += self.pdepub2
            if self.valpdecongreso:
                puntos += self.pdecongreso
            if self.valpdaccionafirmativa:
                puntos += self.pdaccionafirmativa
            return puntos
        except Exception as ex:
            return 0

    def total_puntos(self):
        return self.total_puntos_gradoacademico() + self.total_puntos_capacitacion() + self.total_puntos_experiencia_docente() + self.total_puntos_experiencia_administrativo()

    def total_desempate_calificacion(self):
        return self.total_puntos_desempate() + self.total_puntos()

    def estado_color(self):
        label = 'text-default'
        if self.estado == 0:
            label = 'text-default'
        elif self.estado == 1 or self.esmejorpuntuado:
            label = 'text-success'
        elif self.estado == 2:
            label = 'text-danger'
        elif self.estado == 3:
            label = 'text-warning'
        return label

    def calificada_str(self):
        return 'fa fa-check-circle text-success' if self.calificada else 'fa fa-times-circle text-danger'

    def tiene_formacionacademica(self):
        return self.personaformacionacademicopartida_set.filter(status=True).exists()

    def formacionacademica(self):
        return self.personaformacionacademicopartida_set.filter(status=True)

    def tiene_experienciapartida(self):
        return self.personaexperienciapartida_set.filter(status=True).exists()

    def tiene_capacitaciones(self):
        return self.personacapacitacionespartida_set.filter(status=True).exists()

    def tiene_publicaciones(self):
        return self.personapublicacionespartida_set.filter(status=True).exists()

    def tiene_idiomas(self):
        return self.personaidiomapartida_set.filter(status=True).exists()

    def aplica_gradoacademico(self):
        try:
            from sga.models import CamposTitulosPostulacion
            titulos_persona = self.persona.titulacion_set.filter(status=True)
            qscampostitulos = CamposTitulosPostulacion.objects.select_related().filter(status=True, titulo__in=titulos_persona.values_list('titulo__id', flat=True))
            numcumplimiento, lista_amplios, lista_especificos, lista_detallados = 0, [], [], []
            for campotitulo in qscampostitulos:
                lista_amplios += campotitulo.campoamplio.all().values_list('id', flat=True)
                lista_especificos += campotitulo.campoespecifico.all().values_list('id', flat=True)
                lista_detallados += campotitulo.campodetallado.all().values_list('id', flat=True)
            cumpleamplios = len((set(lista_amplios) & set(list(self.partida.campoamplio.values_list('id', flat=True))))) > 0
            cumpleespecifico = len((set(lista_especificos) & set(list(self.partida.campoespecifico.values_list('id', flat=True))))) > 0
            cumpledetallado = len((set(lista_detallados) & set(list(self.partida.campodetallado.values_list('id', flat=True))))) > 0
            if not cumpleamplios:
                numcumplimiento += 1
            if not cumpleespecifico:
                numcumplimiento += 1
            if not cumpledetallado:
                numcumplimiento += 1
            return {'resp': True, 'numcumplimiento': numcumplimiento, 'cumpleamplio': cumpleamplios, 'cumpleespecifico': cumpleespecifico, 'cumpledetallado': cumpledetallado}
        except Exception as ex:
            return {'res': False, 'numcumplimiento': 0, 'cumpleamplio': False, 'cumpleespecifico': False, 'cumpledetallado': False}

    def puede_seleccionar_horario(self, horario):

        if HorarioPersonaPartida.objects.filter(horario__tipo=horario.tipo,partida=self, status=True).exists():
            return False
        return True

    def horario_seleccionado(self, horario):
        return HorarioPersonaPartida.objects.filter(horario=horario,partida=self, status=True).exists()

    def mis_horarios(self):
        return HorarioPersonaPartida.objects.filter(partida=self, status=True)

    def evaluacion(self):
        if not self.evaluacionpostulante_set.filter(status=True).values("id").exists():
            modelo = self.partida.convocatoria.modeloevaluativoconvocatoria
            for campos in modelo.detallemodeloevaluativoconvocatoria_set.all():
                evaluacion = EvaluacionPostulante(postulante=self,
                                                detallemodeloevaluativo=campos,
                                                valor=0)
                evaluacion.save()
        return self.evaluacionpostulante_set.filter(status=True)

    def esta_aprobado_final(self):
        self.actualiza_estado()
        return self.estado == 4

    def actualiza_estado(self):
        modelo = self.partida.convocatoria.modeloevaluativoconvocatoria
        self.estado = 1
        actualizar = False
        determinar_estado_final = False

        for campo in modelo.campos().filter(actualizaestado=True):
            if null_to_numeric(self.valor_nombre_campo(campo.nombre)) > 0:
                actualizar = True
                break
        for campo in modelo.campos().filter(determinaestadofinal=True):
            if null_to_numeric(self.valor_nombre_campo(campo.nombre)) > 0:
                determinar_estado_final = True
                break
        if actualizar:
            if self.nota_final >= modelo.notaaprobar:
                self.estado = 4
            else:
                self.estado=5
        if determinar_estado_final or (self.partida.convocatoria.vigente==False):
            if not self.estado == 4:
                self.estado = 2
        self.save()

    def actualiza_estadofinal(self):
        modeloevaluativomateria = self.partida.convocatoria.modeloevaluativoconvocatoria
        d = locals()
        exec(modeloevaluativomateria.logicamodelo, globals(), d)
        d['calculo_modelo_evaluativo'](self)
        self.nota_final = null_to_decimal(self.nota_final, 2)
        self.save()
        encurso = True
        if self.nota_final>=70:
            self.estado = 4
        else:
            self.estado = 5
        self.save()

    def verifica_evaluacion_postulante(self):
        if not self.evaluacionpostulante_set.filter(status=True).exists():
            modelo = self.partida.convocatoria.modeloevaluativoconvocatoria
            for campo in modelo.detallemodeloevaluativoconvocatoria_set.filter(status=True):
                evaluacion = EvaluacionPostulante(postulante=self,
                                                detallemodeloevaluativo=campo,
                                                valor=0)
                evaluacion.save()
        return True

    def valor_nombre_campo(self, campo):
        if self.verifica_evaluacion_postulante():
            if self.evaluacionpostulante_set.values("valor").filter(status=True, detallemodeloevaluativo__nombre=campo):
                return self.evaluacionpostulante_set.values("valor").filter(status=True, detallemodeloevaluativo__nombre=campo)[
                    0].get("valor")
            return 0
        return 0

    def campo(self, campo):
        if self.evaluacion().filter(detallemodeloevaluativo__nombre=campo).exists():
            return self.evaluacion().filter(detallemodeloevaluativo__nombre=campo)[0]
        return None

    def tres_mejores_puntuados_pt(self):
        try:
            if EvaluacionPostulante.objects.values('id').filter(status=True,valor__gte=70,detallemodeloevaluativo__nombre='PT', postulante__partida=self.partida).exists():
                evaluacionpostuales = EvaluacionPostulante.objects.values_list('postulante_id', flat=True).filter(status=True,valor__gte=70,detallemodeloevaluativo__nombre='PT', postulante__partida=self.partida).order_by('-valor')[:3]
                if self.id in evaluacionpostuales:
                    return True
                return False
            return False
        except Exception as ex:
            print(ex)
            return False

    def notificacion_ganador(self):
        return self.notificacionganador_set.filter(status=True).last()

    def estado_primera_fase(self):
        estado = self.get_estado_display()
        if self.esmejorpuntuado:
            estado = 'VALIDADO'
        return estado

    def estado_segunda_fase(self):
        estado = self.get_estado_display()
        if self.estado == 1:
            estado = 'PENDIENTE'
        return estado

    def __str__(self):
        return '{} [{}]'.format(self.persona.__str__(), self.partida.__str__())

    def save(self, *args, **kwargs):
        super(PersonaAplicarPartida, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Persona Partida"
        verbose_name_plural = u"Persona Partida"

class ConvocatoriaPostulante(ModeloBase):
    persona = models.ForeignKey(PersonaAplicarPartida, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    tema = models.TextField(default='', blank=True, null=True, verbose_name='Tema')
    fechaasistencia = models.DateField(default='', verbose_name='Fecha Asistencia')
    horasistencia = models.TimeField(default='', verbose_name=u'Hora Asistencia')
    lugar = models.TextField(default='', blank=True, null=True, verbose_name='Lugar')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')

    def __str__(self):
        return '{} {}'.format(self.persona.__str__(), self.lugar)


ESTADO_APELACION = (
    (0, u'PENDIENTE'),
    (1, u'ACEPTADO'),
    (2, u'RECHAZADO'),
)


class PersonaApelacion(ModeloBase):
    personapartida = models.ForeignKey(PersonaAplicarPartida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Aplicación')
    factores = models.ManyToManyField(FactorApelacion, verbose_name='Factores de Apelación')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')
    estado = models.IntegerField(choices=ESTADO_APELACION, default=0, verbose_name=u'Estado')
    archivo = models.FileField(upload_to='apelacionpersonas', blank=True, null=True, verbose_name=u'Archivo')
    revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Revisado por')
    observacion_revisor = models.TextField(default='', blank=True, null=True, verbose_name='Observación Revisor')
    fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión')

    def estado_color(self):
        label = 'label label-default'
        if self.estado == 0:
            label = 'label label-default'
        elif self.estado == 1:
            label = 'label label-success'
        elif self.estado == 2:
            label = 'label label-danger'
        elif self.estado == 3:
            label = 'label label-warning'
        return label

    def __str__(self):
        return '{} - {}'.format(self.personapartida, self.get_estado_display())


class PersonaIdiomaPartida(ModeloBase):
    personapartida = models.ForeignKey(PersonaAplicarPartida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Aplicación')
    aceptado = models.BooleanField(default=False, verbose_name=u'¿Aceptado?')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Observación')
    idioma = models.ForeignKey('sga.Idioma', blank=True, null=True, verbose_name=u'Idioma', on_delete=models.CASCADE)
    institucioncerti = models.ForeignKey('sga.InstitucionCertificadora', blank=True, null=True, verbose_name=u'Institución Certificadora', on_delete=models.CASCADE)
    validainst = models.BooleanField(default=False, blank=True, verbose_name=u'Otra institucion')
    otrainstitucion = models.TextField(default='', verbose_name=u'Otra institución certificadora')
    nivelsuficencia = models.ForeignKey('sga.NivelSuficencia', blank=True, null=True, verbose_name=u'Nivel de suficiencia', on_delete=models.CASCADE)
    fechacerti = models.DateField(verbose_name=u'Fecha certificación', blank=True, null=True)
    archivo = models.FileField(upload_to='postulacioncertificados', blank=True, null=True, verbose_name=u'Archivo')

    def aceptado_str(self):
        return 'fa fa-check-circle text-success' if self.aceptado else 'fa fa-times-circle text-danger'

    def __str__(self):
        return "{}".format(self.personapartida)

    class Meta:
        verbose_name = u"Idioma Persona Partida"
        verbose_name_plural = u"Idiomas Persona Partida"


class PersonaFormacionAcademicoPartida(ModeloBase):
    personapartida = models.ForeignKey(PersonaAplicarPartida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Aplicación')
    aceptado = models.BooleanField(default=False, verbose_name=u'¿Aceptado?')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Observación')
    titulo = models.ForeignKey(Titulo, blank=True, null=True, verbose_name=u'Titulo', on_delete=models.CASCADE)
    registro = models.CharField(default='', max_length=50, verbose_name=u'Registro SENESCYT')
    pais = models.ForeignKey(Pais, blank=True, null=True, verbose_name=u'País', on_delete=models.CASCADE)
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u'Provincia', on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u'Canton', on_delete=models.CASCADE)
    parroquia = models.ForeignKey(Parroquia, blank=True, null=True, verbose_name=u"Parroquia", on_delete=models.CASCADE)
    educacionsuperior = models.BooleanField(default=True, verbose_name=u'Tipo de titulo')
    institucion = models.ForeignKey(InstitucionEducacionSuperior, blank=True, null=True, verbose_name=u'Institucion de educacion superior', on_delete=models.CASCADE)
    cursando = models.BooleanField(default=False, verbose_name=u'Cursando')
    campoamplio = models.ManyToManyField('sga.AreaConocimientoTitulacion', verbose_name=u'Campo Amplio')
    campoespecifico = models.ManyToManyField('sga.SubAreaConocimientoTitulacion', verbose_name=u'Campo Especifico')
    campodetallado = models.ManyToManyField('sga.SubAreaEspecificaConocimientoTitulacion', verbose_name=u'Campo Detallado')
    archivo = models.FileField(upload_to='postulacionarchivo', blank=True, null=True, verbose_name=u'Archivo')
    combinacion = models.ForeignKey('postulate.ArmonizacionNomenclaturaTitulo',blank=True, null=True, verbose_name=u"Armonización Nomenclatura Título",on_delete=models.SET_NULL)

    def aceptado_str(self):
        return 'fa fa-check-circle text-success' if self.aceptado else 'fa fa-times-circle text-danger'

    def __str__(self):
        return "{} - {}".format(self.personapartida, self.titulo)

    class Meta:
        verbose_name = u"Formacion Academica Persona Partida"
        verbose_name_plural = u"Formacion Academica Persona Partida"


class PersonaExperienciaPartida(ModeloBase):
    personapartida = models.ForeignKey(PersonaAplicarPartida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Aplicación')
    aceptado = models.BooleanField(default=False, verbose_name=u'¿Aceptado?')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Observación')
    institucion = models.CharField(default='', max_length=200, verbose_name=u'Institución')
    actividadlaboral = models.ForeignKey('sagest.ActividadLaboral', blank=True, null=True, verbose_name=u'Actividad laboral', on_delete=models.CASCADE)
    cargo = models.CharField(default='', max_length=200, verbose_name=u'Cargo')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicio')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin')
    archivo = models.FileField(upload_to='postulacionarchivo', blank=True, null=True, verbose_name=u'Archivo')

    def aceptado_str(self):
        return 'fa fa-check-circle text-success' if self.aceptado else 'fa fa-times-circle text-danger'

    def meses(self):
        if not self.fechainicio:
            return 0
        if not self.fechafin:
            return rangomeses(self.fechainicio, datetime.now())
        else:
            return rangomeses(self.fechainicio, self.fechafin)

    def __str__(self):
        return "{}".format(self.personapartida)

    class Meta:
        verbose_name = u"Experiencia Profesional Persona Partida"
        verbose_name_plural = u"Experiencia Profesional Persona Partida"


class PersonaCapacitacionesPartida(ModeloBase):
    personapartida = models.ForeignKey(PersonaAplicarPartida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Aplicación')
    aceptado = models.BooleanField(default=False, verbose_name=u'¿Aceptado?')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Observación')
    institucion = models.CharField(default='', max_length=200, verbose_name=u"Institución")
    tipo = models.IntegerField(choices=TIPO_CAPACITACION_P, default=0, verbose_name=u'Tipo')
    nombre = models.CharField(default='', max_length=600, verbose_name=u"Nombre del curso")
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')
    tipocurso = models.ForeignKey('sga.TipoCurso', blank=True, null=True, verbose_name=u"Tipo Curso", on_delete=models.CASCADE)
    tipocapacitacion = models.ForeignKey('sga.TipoCapacitacion', blank=True, null=True, verbose_name=u"Tipo capacitación", on_delete=models.CASCADE)
    tipocertificacion = models.ForeignKey('sga.TipoCertificacion', blank=True, null=True, verbose_name=u"Tipo certificación", on_delete=models.CASCADE)
    tipoparticipacion = models.ForeignKey('sga.TipoParticipacion', blank=True, null=True, verbose_name=u"Tipo participación", on_delete=models.CASCADE)
    anio = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Año')
    contextocapacitacion = models.ForeignKey('sga.ContextoCapacitacion', blank=True, null=True, verbose_name=u'Contexto capacitacion', on_delete=models.CASCADE)
    detallecontextocapacitacion = models.ForeignKey('sga.DetalleContextoCapacitacion', blank=True, null=True, verbose_name=u'Detalle contexto capacitacion', on_delete=models.CASCADE)
    auspiciante = models.CharField(default='', max_length=200, verbose_name=u"Auspiciante")
    areaconocimiento = models.ForeignKey('sga.AreaConocimientoTitulacion', blank=True, null=True, verbose_name=u'Area de conocimiento', on_delete=models.CASCADE)
    subareaconocimiento = models.ForeignKey('sga.SubAreaConocimientoTitulacion', blank=True, null=True, verbose_name=u'Sub area de conocimiento', on_delete=models.CASCADE)
    subareaespecificaconocimiento = models.ForeignKey('sga.SubAreaEspecificaConocimientoTitulacion', blank=True, null=True, verbose_name=u'Sub area especifica de conocimiento', on_delete=models.CASCADE)
    pais = models.ForeignKey(Pais, blank=True, null=True, verbose_name=u'País', on_delete=models.CASCADE)
    provincia = models.ForeignKey(Provincia, blank=True, null=True, verbose_name=u'Provincia', on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u'Canton', on_delete=models.CASCADE)
    parroquia = models.ForeignKey(Parroquia, blank=True, null=True, verbose_name=u"Parroquia", on_delete=models.CASCADE)
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicio')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin')
    horas = models.FloatField(default=0, verbose_name=u'Horas')
    expositor = models.CharField(default='', max_length=200, verbose_name=u"Expositor")
    modalidad = models.IntegerField(choices=MODALIDAD_CAPACITACION, blank=True, null=True, verbose_name=u'Modalidad Capacitacion')
    otramodalidad = models.CharField(default='', max_length=600, verbose_name=u"Otra Modalidad")
    archivo = models.FileField(upload_to='postulacionarchivo', blank=True, null=True, verbose_name=u'Archivo')

    def aceptado_str(self):
        return 'fa fa-check-circle text-success' if self.aceptado else 'fa fa-times-circle text-danger'

    def __str__(self):
        return "{}".format(self.personapartida)

    class Meta:
        verbose_name = u"Capacitación Persona Partida"
        verbose_name_plural = u"Capacitación Persona Partida"


class PersonaPublicacionesPartida(ModeloBase):
    personapartida = models.ForeignKey(PersonaAplicarPartida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Aplicación')
    aceptado = models.BooleanField(default=False, verbose_name=u'¿Aceptado?')
    observacion = models.TextField(default='', null=True, blank=True, verbose_name=u'Observación')
    nombre = models.TextField(blank=True, null=True, verbose_name=u"Nombre")
    tiposolicitud = models.IntegerField(choices=TIPO_SOLICITUD_PUBLICACION, blank=True, null=True, verbose_name=u'Tipo Solicitud')
    fecha = models.DateField(verbose_name=u'Fecha', blank=True, null=True)
    archivo = models.FileField(upload_to='postulacionpublicacion', blank=True, null=True, verbose_name=u'Archivo')

    def aceptado_str(self):
        return 'fa fa-check-circle text-success' if self.aceptado else 'fa fa-times-circle text-danger'

    def __str__(self):
        return "{}".format(self.personapartida)

    class Meta:
        verbose_name = u"Publicaciones Persona Partida"
        verbose_name_plural = u"Publicaciones Persona Partida"


class CalificacionPostulacion(ModeloBase):
    postulacion = models.ForeignKey(PersonaAplicarPartida, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    pgradoacademico = models.FloatField(default=0, verbose_name=u"Nota Grado Academico")
    obsgradoacademico = models.TextField(default='', verbose_name='Observación Experiencia')
    pcapacitacion = models.FloatField(default=0, verbose_name=u"Nota Capacitaciones")
    obscapacitacion = models.TextField(default='', verbose_name='Observación Experiencia')
    pexpdocente = models.FloatField(default=0, verbose_name=u"Nota Experiencia Docente")
    obsexperienciadoc = models.TextField(default='', verbose_name='Observación Experiencia Docente')
    pexpadministrativa = models.FloatField(default=0, verbose_name=u"Nota Experiencia Administrativo")
    obsexperienciaadmin = models.TextField(default='', verbose_name='Observación Experiencia Administrativo')
    aplico_desempate = models.BooleanField(default=False, verbose_name='¿Desempate?')
    pdmaestria = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Maestrias")
    pdphd = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Phd")
    pdexpdocente = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Experiencia Docente")
    pdcappeda = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Capacitacion Pedagocica")
    valpdcapprof = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Capacitacion Profesional')
    pdcapprof = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Capacitacion Profesional")
    valpdidioma = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Idioma Extranjero')
    pdidioma = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Idioma Extranjero")
    valpdepub1 = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Publicación Cientifica (JCR, Scopus)')
    pdepub1 = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Publicación Cientifica (JCR, Scopus)")
    valpdepub2 = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Publicación Cientifica (Regionales, Latindex)')
    pdepub2 = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Publicación Cientifica (Regionales, Latindex)")
    valpdecongreso = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Participación Congresos')
    pdecongreso = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Participación Congresos")
    valpdaccionafirmativa = models.BooleanField(default=False, verbose_name='Valido Desempate Puntos por Acción Afirmativa')
    pdaccionafirmativa = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Acción Afirmativa")
    obdadicional = models.CharField(default='', max_length=1000, blank=True, null=True, verbose_name='Obs. Desempate')
    pdadicional = models.FloatField(default=0, verbose_name=u"Desempate Puntos por Observación Adicional")
    nota_meritos = models.FloatField(default=0, verbose_name=u"Nota Meritos")
    nota_desempate = models.FloatField(default=0, verbose_name=u"Nota Desempate")
    nota_final = models.FloatField(default=0, verbose_name=u"Nota Final")
    obsgeneral = models.TextField(default='', verbose_name='Observación General')
    estado = models.IntegerField(choices=ESTADOS_APLICACION, default=0, verbose_name=u'Estado Postulación')
    revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Revisado por')
    fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión')
    desempate_revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Desempate Revisado por')
    desempate_fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Desempate Fecha Revisión')
    valida = models.BooleanField(default=False, verbose_name='¿Valida?')

    def estado_color(self):
        label = 'label label-default'
        if self.estado == 0:
            label = 'label label-default'
        elif self.estado == 1:
            label = 'label label-success'
        elif self.estado == 2:
            label = 'label label-danger'
        elif self.estado == 3:
            label = 'label label-warning'
        return label

    def str_valida(self):
        return 'fa fa-check-circle text-success' if self.valida else 'fa fa-times-circle text-danger'

    def save(self, *args, **kwargs):
        super(CalificacionPostulacion, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Calificación Postulación"
        verbose_name_plural = u"Calificación Postulación"


class ParametrosDisertacion(ModeloBase):
    descripcion = models.TextField(null=True, blank=True, default='', verbose_name=u'Descripción')
    valor = models.FloatField(default=0, verbose_name='Valor')
    porcentaje = models.FloatField(default=0, verbose_name='%')

    def __str__(self):
        return u'%s ' % (self.descripcion)

    class Meta:
        verbose_name = u"Parametros Disertación"
        verbose_name_plural = u"Parametros Disertación"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(ParametrosDisertacion, self).save(*args, **kwargs)


class AspectosModeloEvaluativos(ModeloBase):
    modeloevaluativo = models.ForeignKey(ModeloEvaluativoDisertacion, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Modelo Evaluativo")
    orden = models.IntegerField(default=0, verbose_name=u"Orden")
    descripcion = models.TextField(default='', verbose_name='Aspecto')
    peso = models.FloatField(default=0, verbose_name=u"Peso %")

    def __str__(self):
        return u'%s ' % (self.descripcion)

    def porcentaje_factores(self, valor):
        try:
            qsbase = self.aspectosfactormodeloevaluativos_set.filter(status=True, parametro__valor=valor)
            if qsbase.exists():
                return qsbase.first().parametro.porcentaje
            else:
                return 0
        except Exception as ex:
            return 0


    def traer_factores(self):
        return self.aspectosfactormodeloevaluativos_set.filter(status=True).order_by('orden')

    class Meta:
        verbose_name = u"Aspectos Modelo Evaluativo Disertación"
        verbose_name_plural = u"Aspectos Modelo Evaluativo Disertación"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(AspectosModeloEvaluativos, self).save(*args, **kwargs)


class AspectosFactorModeloEvaluativos(ModeloBase):
    aspecto = models.ForeignKey(AspectosModeloEvaluativos, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    orden = models.IntegerField(default=0, verbose_name=u"Orden")
    descripcion = models.TextField(default='', verbose_name='Descripción')
    parametro = models.ForeignKey(ParametrosDisertacion, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Parametros")

    class Meta:
        verbose_name = u"Aspectos Modelo Evaluativo Disertación"
        verbose_name_plural = u"Aspectos Modelo Evaluativo Disertación"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(AspectosFactorModeloEvaluativos, self).save(*args, **kwargs)


class CalificacionDisertacion(ModeloBase):
    postulacion = models.ForeignKey(PersonaAplicarPartida, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    modeloevaluativo = models.ForeignKey(ModeloEvaluativoDisertacion, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Modelo Evaluativo")
    observacion = models.TextField(default='', verbose_name='Observación Final')
    notadisertacion = models.FloatField(default=0, verbose_name=u"Nota Disertación")
    totalporcentaje = models.FloatField(default=0, verbose_name=u"Porcentaje Total")
    finalizada = models.BooleanField(default=False, verbose_name='¿Finalizada?')
    revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Revisado por')
    fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión')
    archivo = models.FileField(upload_to='postulate/disertacion', blank=True, null=True, verbose_name=u'Archivo Disertacion')

    def nota_porcentual_70(self):
        return round((self.notadisertacion*0.70), 2)

    def totalporcentaje(self):
        try:
            porcentaje = 0
            for porc in self.get_parametros():
                porcentaje += porc.get_porcentaje()
            return porcentaje
        except Exception as ex:
            return 0

    def totalpuntos(self):
        try:
            puntos = 0
            for porc in self.get_parametros():
                puntos += porc.get_puntos()
            return puntos
        except Exception as ex:
            return 0

    def get_parametros(self):
        return self.detallecalificaciondisertacion_set.filter(status=True).order_by('parametro__orden')

    def __str__(self):
        return "{} ({})".format(self.postulacion, self.notadisertacion)

    def save(self, *args, **kwargs):
        super(CalificacionDisertacion, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Calificación Disertación Postulación"
        verbose_name_plural = u"Calificación Disertación Postulación"


class DetalleCalificacionDisertacion(ModeloBase):
    calificacion = models.ForeignKey(CalificacionDisertacion, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Calificacion")
    parametro = models.ForeignKey(AspectosModeloEvaluativos, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Parametro")
    valor = models.FloatField(default=0, verbose_name='Valor')
    porcentaje = models.FloatField(default=0, verbose_name='%')
    puntos = models.FloatField(default=0, verbose_name='Puntos')

    def get_porcentaje(self):
        try:
            return (self.parametro.peso * self.parametro.porcentaje_factores(self.valor))/self.calificacion.modeloevaluativo.ponderacion
        except Exception as ex:
            return 0

    def get_puntos(self):
        try:
            return (self.get_porcentaje()/100) * self.calificacion.modeloevaluativo.ponderacion
        except Exception as ex:
            return 0

    def __str__(self):
        return "{} | {}: ({})".format(self.calificacion.__str__(), self.parametro.__str__(), self.valor)

    class Meta:
        verbose_name = u"Detalle Calificación Disertación Postulación"
        verbose_name_plural = u"Detalle Calificación Disertación Postulación"


class CalificacionEntrevista(ModeloBase):
    postulacion = models.ForeignKey(PersonaAplicarPartida, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    notaentrevista = models.FloatField(default=0, verbose_name=u"Nota Entrevista")
    finalizada = models.BooleanField(default=False, verbose_name='¿Finalizada?')
    revisado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', blank=True, null=True, verbose_name='Revisado por')
    fecha_revision = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Revisión')

    def nota_porcentual_30(self):
        return round((self.notaentrevista*0.30), 2)

    def total_notas(self):
        try:
            return self.detallecalificacionentrevista_set.filter(status=True).aggregate(total=Sum(F('nota'))).get('total')
        except Exception as ex:
            return 0

    def nota_promedio(self):
        try:
            qsbase = self.detallecalificacionentrevista_set.filter(status=True)
            totnotas = qsbase.aggregate(total=Sum(F('nota'))).get('total')
            cantnotas = len(qsbase)
            return totnotas/cantnotas
        except Exception as ex:
            return 0

    def traer_tribunal(self):
        return self.detallecalificacionentrevista_set.filter(status=True).order_by('tribunal__cargos')

    def calificaion_tribunal(self,cargo):
        if self.detallecalificacionentrevista_set.values('id').filter(status=True,tribunal__cargos=cargo).exists():
            return self.detallecalificacionentrevista_set.filter(status=True,tribunal__cargos=cargo).last()
        return None

    def __str__(self):
        return "{} ({})".format(self.postulacion, self.notaentrevista)

    def save(self, *args, **kwargs):
        super(CalificacionEntrevista, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Calificación Entrevista Postulación"
        verbose_name_plural = u"Calificación Entrevista Postulación"


class DetalleCalificacionEntrevista(ModeloBase):
    calificacion = models.ForeignKey(CalificacionEntrevista, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Calificacion")
    tribunal = models.ForeignKey(PartidaTribunal, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Miembro Tribunal")
    nota = models.FloatField(default=0, verbose_name='Calificación')
    observacion = models.TextField(default='', verbose_name='Observación')

    def __str__(self):
        return "{} | {}: ({})".format(self.calificacion.__str__(), self.tribunal.__str__(), self.nota)

    class Meta:
        verbose_name = u"Detalle Calificación Entrevista Postulación"
        verbose_name_plural = u"Detalle Calificación Entrevista Postulación"


class RequisitoDocumentoContrato(ModeloBase):
    nombre = models.CharField(verbose_name=u'Titulo del requisito', max_length=300)
    descripcion = models.TextField(default='', verbose_name='Descripcion del requisito')
    anio = models.DateField(verbose_name='Año valido', blank=True, null=True)
    tipo = models.IntegerField(default=0,verbose_name='Tipo de requisitos', choices=TIPO_REQUISITO)
    obligatorio = models.BooleanField(default=False, verbose_name='¿Obligatorio?')
    activo = models.BooleanField(default=False, verbose_name='¿Activo?')
    archivo = models.FileField(verbose_name=u'Arvhivo requisitos', upload_to="requisitocontrato/requisitos")

    def __str__(self):
        return "{} - {}".format(self.nombre, self.descripcion.__str__())

    class Meta:
        verbose_name = u"Requisito documento contrato"
        verbose_name_plural = u"Requisitos documentos contratos"
        ordering = ['id']

    def requisitoexiste(self):
        return self.personarequisitodocumentocontrato_set.filter(status=True,archivo__isnull=False).exists()

    def personaarchivo(self):
        if self.personarequisitodocumentocontrato_set.filter(status=True).values('id').exists():
            return self.personarequisitodocumentocontrato_set.last()
        return None


ESTADO_REQUISITOS = (
    (1,'Pendiente'),
    (2,'Corregir'),
    (3,'Aprobar'),
    (4,'Rechazar'),
)


class PersonaRequisitoDocumentoContrato(ModeloBase):
    persona = models.ForeignKey("sga.Persona",verbose_name=u'Postulante', on_delete=models.CASCADE)
    requisito = models.ForeignKey(RequisitoDocumentoContrato,verbose_name=u'Documento', on_delete=models.CASCADE)
    archivo = models.FileField(verbose_name=u'Documento', upload_to="requisitocontrato/postulante")
    estado = models.IntegerField(verbose_name=u'Estado', default=1,choices=ESTADO_REQUISITOS)

    def __str__(self):
        return "{} - {}".format(self.persona.__str__(), self.requisito.__str__())

    class Meta:
        verbose_name = u"Postulante requisito documento contrato"
        verbose_name_plural = u"Postulante requisitos documentos contratos"
        ordering = ['id']


class HistorialPersonaRequisitoDocument(ModeloBase):
    personareq = models.ForeignKey(PersonaRequisitoDocumentoContrato,verbose_name='Requisito persona', on_delete=models.CASCADE)
    estado = models.IntegerField(verbose_name=u'Estado', default=1,choices=ESTADO_REQUISITOS)
    observacion = models.TextField(verbose_name=u'Observación')

    def __str__(self):
        return f"{self.personareq} - {self.get_estado_display()}"

    class Meta:
        verbose_name = u"Historial postulante requisito documento contrato"
        verbose_name_plural = u"Historial postulantes requisitos documentos contratos"
        ordering = ['id']

ESTADO_TITULO_SUGERENCIA =(
    (1, u"PENDIENTE"),
    (2, u"APROBADO"),
    (3, u"RECHAZADO"))

class TituloSugerido(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    nombre = models.CharField(default='', max_length=200, verbose_name=u' Nombre')
    nivel = models.ForeignKey(NivelTitulacion, verbose_name=u'Nivel', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_TITULO_SUGERENCIA, default=1, blank=True, null=True, verbose_name=u'Estado revisión sugerencia titulo')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación de sugerencia rechazada')

    def __str__(self):
        return f"{self.nombre} - {self.nivel}"

class HorarioConvocatoria(ModeloBase):
    # persona = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Persona")
    turno = models.ForeignKey(TurnoConvocatoria, blank=True, null=True, on_delete=models.PROTECT, verbose_name='Turno')
    tipo = models.ForeignKey(TipoTurnoConvocatoria, blank=True, null=True, on_delete=models.PROTECT, verbose_name='Tipo de horario')
    convocatoria = models.ForeignKey(Convocatoria, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Convocatoria')
    dia = models.IntegerField(choices=DIAS_CHOICES, default=0, verbose_name=u'Dia')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar')
    detalle = models.TextField(default='', blank=True, null=True, verbose_name='Detalle de horario')
    lugar = models.TextField(default='', blank=True, null=True, verbose_name='Lugar')
    cupo = models.IntegerField(default=0, verbose_name=u'Cupo')

    def __str__(self):
        return f"{self.turno} - {self.tipo.nombre} - {self.fecha} - {self.lugar}"

    def tiene_cupo(self):
        if self.cupo - HorarioPersonaPartida.objects.values("id").filter(status=True,horario=self).count() >0:
            return True
        return False

    def fuera_de_fecha(self):
        today = datetime.now().date()
        if self.fecha < today:
            return True
        return False

    def puede_eliminar(self):
        return not self.horariopersonapartida_set.filter(status=True)

class HistorialPartida(ModeloBase):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Partida')
    estado = models.IntegerField(choices=ESTADO_PLANIFICACION, null=True, blank=True, verbose_name=u'Estado Planificacion')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True,related_name='envia', on_delete=models.PROTECT, verbose_name=u"Persona que envía")
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación de aprobación/rechazo')

    def __str__(self):
        return '({}) {}'.format(self.partida, self.get_estado_display())

class HorarioPersonaPartida(ModeloBase):
    partida = models.ForeignKey(PersonaAplicarPartida, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'postulante')
    horario = models.ForeignKey(HorarioConvocatoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Horario')
    tomaasistencia = models.ForeignKey(Persona,on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Toma asistencia')
    asistio = models.BooleanField(verbose_name=u'¿Asistió?',default=False, null=True, blank=True)

    def __str__(self):
        return '({}) {}'.format(self.partida, self.horario)

class EvaluacionPostulante(ModeloBase):
    postulante = models.ForeignKey(PersonaAplicarPartida, verbose_name=u"Postulante", on_delete=models.CASCADE)
    detallemodeloevaluativo = models.ForeignKey(DetalleModeloEvaluativoConvocatoria, verbose_name=u'Detalle modelo evaluación', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor evaluación')
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha modificación')
    archivo = models.FileField(verbose_name=u'Documento',blank=True, null=True, upload_to="calificacion/postulante")

    class Meta:
        unique_together = ('postulante', 'detallemodeloevaluativo',)

    def save(self, *args, **kwargs):
        if self.valor >= self.detallemodeloevaluativo.notamaxima:
            self.valor = self.detallemodeloevaluativo.notamaxima
        elif self.valor <= self.detallemodeloevaluativo.notaminima:
            self.valor = self.detallemodeloevaluativo.notaminima
        self.valor = null_to_decimal(self.valor, self.detallemodeloevaluativo.decimales)
        super(EvaluacionPostulante, self).save(*args, **kwargs)


class Programa(ModeloBase):
    nombre = models.TextField(default='', blank=True, null=True, verbose_name='Programa')
    codigo = models.CharField(default='', max_length=900, verbose_name=u'Codigo')
    vigente = models.BooleanField(default=True, verbose_name=u"Vigente")

    def __str__(self):
        return "[{}] - {}".format(self.codigo, self.nombre)

    class Meta:
        verbose_name = u"Programa"
        verbose_name_plural = u"Programas"
        ordering = ['nombre']
        unique_together = ('nombre', 'vigente',)

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        if extra:
            return eval(
                'Programa.objects.filter(Q(nombre__icontains="%s")).filter(%s).distinct()[:%s]' % (
                q, extra, limit))
        return Programa.objects.filter(Q(nombre__icontains=q)).distinct()[:limit]

    def flexbox_repr(self):
        return u'%s' % self.nombre

    def flexbox_alias(self):
        return [self.id, self.nombre.upper()]

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        self.codigo = self.codigo.upper().strip()
        super(Programa, self).save(*args, **kwargs)

class ArmonizacionNomenclaturaTitulo(ModeloBase):
    campoamplio = models.ForeignKey('sga.AreaConocimientoTitulacion', verbose_name=u'Campo Amplio',blank=True, null=True, on_delete=models.SET_NULL)
    campoespecifico = models.ForeignKey('sga.SubAreaConocimientoTitulacion', verbose_name=u'Campo Especifico',blank=True, null=True, on_delete=models.SET_NULL)
    campodetallado = models.ForeignKey('sga.SubAreaEspecificaConocimientoTitulacion',verbose_name=u'Campo Detallado',blank=True, null=True, on_delete=models.SET_NULL)
    programa = models.ForeignKey(Programa, verbose_name=u"Programa",blank=True, null=True, on_delete=models.SET_NULL)
    titulo = models.ForeignKey('sga.Titulo', verbose_name=u'Titulos Relacionados',blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "%s - (Amplio: %s - Especifico: %s - Detallado: %s - Programa: %s) "%(self.titulo.nombre, self.campoamplio.nombre, self.campoespecifico.nombre,self.campodetallado.nombre,self.programa.nombre)

    class Meta:
        verbose_name = u"Armonización Nomenclatura Título"
        verbose_name_plural = u"Armonización Nomenclatura Títulos"
        ordering = ['titulo']
        unique_together = ('campoamplio', 'campoespecifico','campodetallado','programa','titulo',)

class PartidaArmonizacionNomenclaturaTitulo(ModeloBase):
    combinacion = models.ForeignKey(ArmonizacionNomenclaturaTitulo,blank=True, null=True, verbose_name=u"Armonización Nomenclatura Título", on_delete=models.SET_NULL)
    partida = models.ForeignKey(Partida, verbose_name=u'Título',blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "{} - {}".format(self.partida,self.combinacion)

    class Meta:
        verbose_name = u"Partida Armonización Nomenclatura Título"
        verbose_name_plural = u"Partida Armonización Nomenclatura Títulos"
        ordering = ['partida']
SELECCIONA_ESTADO_GANADOR = (
    (1, u'ACEPTAR'),
    (2, u'DESISTIR'),
    )
class NotificacionGanador(ModeloBase):
    # persona = models.ForeignKey(Persona, verbose_name='Persona notificada', on_delete=models.SET_NULL, null=True, blank=True)
    personaaplicapartida = models.ForeignKey(PersonaAplicarPartida, verbose_name='Persona aplica partida', on_delete=models.SET_NULL, null=True, blank=True)
    respondioganador = models.BooleanField(default=False, verbose_name='¿Respondió notificación?')
    fecha = models.DateField(null=True, blank=True,verbose_name='Fecha de notificacion')
    fecharespuesta = models.DateField(null=True, blank=True,verbose_name='Fecha de respuesta')
    observacion = models.TextField(verbose_name='Observacion',null=True, blank=True)
    archivo = models.FileField(upload_to='postulate/personadesiste/Y/m/d', verbose_name='Evidencia')
    estado = models.IntegerField(choices=SELECCIONA_ESTADO_GANADOR, null=True, blank=True, verbose_name=u'Estado ganador')

    class Meta:
        verbose_name = 'Notificación a ganador'
        verbose_name_plural = 'Notificaciones a ganador'
        ordering = ['-id']

    def __str__(self):
        return f'{self.observacion} ({self.fecha})'

# Control de actas para firma en el sistema
ESTADO_FIRMA_ACTA = (
    (1, u"Generado"),
    (2, u"En proceso"),
    (3, u"Firmado"),
    (4, u"Revertido"),
)
TIPO_ACTA = (
    (1, u"Acta de conformación"),
    (2, u"Acta de calificación merito"),
    (3, u"Acta de calificación merito 2"),
    (4, u"Acta de entrevista tribunal 2"),
    (5, u"Acta de puntaje final tribunal 2"),
)
class ActaPartida(ModeloBase):
    partida = models.ForeignKey(Partida, blank=True, null=True, on_delete=models.PROTECT, verbose_name=u"Partida Aplicada")
    archivo = models.FileField(upload_to='postulate/actaspartida/', blank=True, null=True, verbose_name=u'Archivo firmado')
    estado = models.IntegerField(choices=ESTADO_FIRMA_ACTA,null=True, blank=True, verbose_name=u'Estado del del documento')
    tipo = models.IntegerField(choices=TIPO_ACTA, null=True, blank=True, verbose_name=u'Tipo de acta')
    tipotribunal = models.IntegerField(choices=TIPO_TRIBUNAL, default=1, verbose_name=u'Tipo Tribunal')

    def __str__(self):
        return f'{self.get_tipo_display()} | {self.partida}'

    def btn_estado(self):
        color='btn-secondary'
        if self.estado == 2:
            color='btn-primary'
        elif self.estado == 3:
            color = 'btn-success'
        elif self.estado == 4:
            color = 'btn-primary-old'
        return color

    def color_estado(self):
        color = 'text-primary'
        if self.estado==2:
            color='text-warning'
        elif self.estado==3:
            color = 'text-success'
        return color

    def get_documento(self):
        return self.ultimo_archivo().get_documento()

    def ultimo_archivo_con_exclusion(self, persona):
        return self.historialactafirma_set.filter(status=True).exclude(personatribunal_persona=persona, estado=3).last()

    def ultimo_archivo(self):
        return self.historialactafirma_set.filter(status=True).last()

    def historial_firmados(self):
        return self.historialactafirma_set.filter(status=True, estado=3)

    def historial_firmas_all(self):
        return self.historialactafirma_set.filter(status=True)

    def ultimo_archivo_generado(self):
        return self.historialactafirma_set.filter(status=True, estado=1).last()

    def persona_tribunal(self, persona):
        return self.partida.partidatribunal_set.filter(status=True, tipo=self.tipotribunal, persona=persona, firma=True).first()

    def responsables(self):
        return self.partida.partidatribunal_set.filter(status=True, tipo=self.tipotribunal, firma=True)

    def firmado_all(self):
        ids_responsables = self.responsables().values_list('id',flat=True).order_by('id').distinct()
        firmados = self.historial_firmados().filter(personatribunal_id__in=ids_responsables).values_list('personatribunal_id',flat=True).order_by('personatribunal_id').distinct('personatribunal_id')
        return len(firmados) >= len(ids_responsables)

    def puede_firmar(self, persona):
        r_tribunal = self.responsables().filter(persona=persona).first()
        if not r_tribunal:
            return False
        firmado = self.historial_firmados().filter(personatribunal=r_tribunal).exists()
        return not firmado

    class Meta:
        verbose_name = u'Acta de partida'
        verbose_name_plural = u'Actas de partida'
        ordering = ('fecha_creacion',)

class HistorialActaFirma(ModeloBase):
    acta = models.ForeignKey(ActaPartida,blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Certificado de salida de paz y salvo')
    personatribunal = models.ForeignKey(PartidaTribunal, blank=True, null=True, verbose_name=u'Persona que firmo el documento', on_delete=models.CASCADE)
    archivo_original = models.FileField(upload_to='postulate/actaspartida/original/', blank=True, null=True, verbose_name=u'Archivo original')
    archivo_firmado = models.FileField(upload_to='postulate/actaspartida/firmadas/', blank=True, null=True, verbose_name=u'Archivo firmado')
    cantidadfirmas = models.IntegerField(default=0, verbose_name=u'Cantidad de firmas colocadas')
    estado = models.IntegerField(choices=ESTADO_FIRMA_ACTA,null=True, blank=True, verbose_name=u'Estado del del documento')

    def __str__(self):
        return u'%s' % (self.personatribunal)

    def get_documento(self):
        if self.archivo_firmado:
            return self.archivo_firmado
        return self.archivo_original

    def color_estado(self):
        color = 'text-primary'
        if self.estado==2:
            color='text-warning'
        elif self.estado==3:
            color = 'text-success'
        return color

    class Meta:
        verbose_name = u'Historial de acta firmado'
        verbose_name_plural = u'Historial de actas firmadas'
        ordering = ('fecha_creacion',)
