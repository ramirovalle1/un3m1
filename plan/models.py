from django.db import models

# Create your models here.
from sga.funciones import ModeloBase

TIPO_ACCION = (
    (1, u"EXPERIENCIA"),
    (2, u"LOGRO"),
)

ESTADO_PLAN = (
    (1, u"PENDIENTE"),
    (2, u"EN PROCESO"),
    (3, u"FINALIZADO"),
)


MODELO_DAFO = (
    (1, u"DEBILIDADES"),
    (2, u"AMENAZAS"),
    (3, u"FORTALEZA"),
    (4, u"OPORTUNIDADES"),
)
MOVILIDAD = (
    (1, u"POR ESTRUCTURA"),
    (2, u"POR COMPETENCIA"),
)

class PeriodoPlanTh(ModeloBase):
    descripcion = models.CharField(blank=True, null=True, max_length=10000, verbose_name=u'Descripcion')
    fechainicio = models.DateField(blank=True, null=True)
    fechafin = models.DateField(blank=True, null=True)
    estado = models.IntegerField(choices=ESTADO_PLAN, default=1, verbose_name=u"Estado")

    def __str__(self):
        return u'%s [ %s - %s ]' % (self.descripcion, str(self.fechainicio),str(self.fechafin))

    class Meta:
        verbose_name = u'Periodo de plan de carrera'
        verbose_name_plural = u'periodos de plan de carrera'
        ordering = ('id', )

    def puede_eliminar(self):
        if self.direccionperiodoplanth_set.filter(status=True):
            return False
        return True

class DireccionPeriodoPlanTh(ModeloBase):
    direccion = models.ForeignKey('sagest.Departamento', blank=True, null=True, verbose_name=u"Unidad organizacional", on_delete=models.CASCADE)
    periodo = models.ForeignKey(PeriodoPlanTh, blank=True, null=True, verbose_name=u"Periodo plan", on_delete=models.CASCADE)
    responsable = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_PLAN, default=1, verbose_name=u"Estado")

    class Meta:
        verbose_name = u'Dirección de plan de carrera'
        verbose_name_plural = u'Direcciones de plan de carrera'
        ordering = ('periodo_id', )

    def puede_eliminar(self):
        return not self.personaplanth_set.filter(status=True).values_list('id', flat=True).exists()

    def personal_seleccionado(self):
        return self.personaplanth_set.filter(status=True)

    def personal(self):
        return self.direccion.distributivopersona_set.filter(status=True).exclude(persona_id__in=self.personal_seleccionado().values_list('persona_id', flat=True)) if self.direccion else []

    def __str__(self):
        return u'%s - %s' % (self.direccion, self.responsable if self.responsable else 'SIN RSPONSABLE')

class ModeloGestionOrganizacionPlanTh(ModeloBase):
    descripcion = models.TextField(blank=True, null=True, verbose_name=u'Descripcion')
    activo = models.BooleanField(default=True, verbose_name=u'Usa actualmente')

    def __str__(self):
        return u'%s' % (self.descripcion)

    def puede_eliminar(self):
        return not self.personaplanth_set.filter(status=True).values_list('id', flat=True).exists()

    def model_name(self):
        return self._meta.model_name

    def app_label(self):
        return self._meta.app_label

class ModeloGestionTrabajadorPlanTh(ModeloBase):
    descripcion = models.TextField(blank=True, null=True, verbose_name=u'Descripcion')
    activo = models.BooleanField(default=True, verbose_name=u'Usa actualmente')

    def __str__(self):
        return u'%s' % (self.descripcion)

    def puede_eliminar(self):
        return not self.personaplanth_set.filter(status=True).values_list('id', flat=True).exists()

    def model_name(self):
        return self._meta.model_name

    def app_label(self):
        return self._meta.app_label

class PersonaPlanTh(ModeloBase):
    persona = models.ForeignKey('sga.Persona', related_name='+', blank=True, null=True, verbose_name=u'Responsable', on_delete=models.CASCADE)
    direccion = models.ForeignKey(DireccionPeriodoPlanTh, verbose_name=u'Dirección', on_delete=models.CASCADE)
    organizacion = models.ForeignKey(ModeloGestionOrganizacionPlanTh, blank=True, null=True, verbose_name=u'Modelo de gestión de carrera centrada en la organización', on_delete=models.CASCADE)
    trabajador = models.ForeignKey(ModeloGestionTrabajadorPlanTh, blank=True, null=True,verbose_name=u'Modelo de gestión de carrera centrada en el trabajador', on_delete=models.CASCADE)
    puesto = models.ForeignKey('sagest.DenominacionPuesto', verbose_name = u'Puesto', blank=True, null=True, on_delete = models.CASCADE)
    perfil = models.ForeignKey('sagest.PerfilPuestoTh', verbose_name = u'Puesto', blank=True, null=True, on_delete = models.CASCADE)
    escala = models.ForeignKey('sagest.EscalaOcupacional', verbose_name = u'Escala', blank=True, null=True, on_delete = models.CASCADE)
    rmupuesto = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"RMU Puesto")
    vision = models.TextField(default='', verbose_name=u'Visión profesional', blank=True)
    objetivo = models.TextField(default='', verbose_name=u'Visión profesional', blank=True)
    comentarios = models.TextField(default='', verbose_name=u'Comentarios', blank=True)
    estado = models.IntegerField(choices=ESTADO_PLAN, default=1, verbose_name=u"Estado")

    def __str__(self):
        return u'%s' % (self.persona)

    def planes_acciones(self):
        return self.planaccionpersonaplanth_set.filter(status=True)

    class Meta:
        verbose_name = u'Persona con plan de carrera'
        verbose_name_plural = u'Personas con plan de carrera'
        ordering = ('persona_id', )

class AccionPersonalPersonaPlanTh(ModeloBase):
    persona = models.ForeignKey(PersonaPlanTh, verbose_name=u'Persona', on_delete=models.CASCADE)
    accion = models.ForeignKey('sagest.AccionPersonal', blank=True, null=True, verbose_name=u"Acción de personal", on_delete=models.CASCADE)
    tipo = models.IntegerField(choices=TIPO_ACCION, default=1, verbose_name=u"Tipo de acción")

    class Meta:
        verbose_name = u'Acción de personal'
        verbose_name_plural = u'Acciones de personal'
        ordering = ('persona_id', )

# class CapacitacionPersonaPlanTh(ModeloBase):
#
#
# class LogroPersonaPlanTh(ModeloBase):
#
# class EvaluacionPersonaPlanTh(ModeloBase):
#
#
class DafoPersonaPlanTh(ModeloBase):
    persona = models.ForeignKey(PersonaPlanTh, verbose_name=u'Persona', on_delete=models.PROTECT)
    tipo = models.IntegerField(choices=MODELO_DAFO, default=1, verbose_name=u"DAFO")
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)

    def __str__(self):
        return u'%s - %s' % (self.descripcion, self.get_tipo_display())

    class Meta:
        verbose_name = u'DAFO'
        verbose_name_plural = u'DAFO'
        ordering = ('id', )

class TipoLineaPlanTh(ModeloBase):
    descripcion = models.TextField(blank=True, null=True, verbose_name=u'Descripcion')
    activo = models.BooleanField(default=True, verbose_name=u'Usa actualmente')

    def __str__(self):
        return u'%s' % (self.descripcion)

    class Meta:
        verbose_name = u'Tipo de línea'
        verbose_name_plural = u'Tipos de líneas'
        ordering = ('id', )

    def puede_eliminar(self):
        return not self.movilidadpersonaplanth_set.filter(status=True).values_list('id', flat=True).exists()

    def model_name(self):
        return self._meta.model_name

    def app_label(self):
        return self._meta.app_label

class MedioPlanTh(ModeloBase):
    descripcion = models.TextField(blank=True, null=True, verbose_name=u'Descripcion')
    activo = models.BooleanField(default=True, verbose_name=u'Usa actualmente')

    def __str__(self):
        return u'%s' % (self.descripcion)


    class Meta:
        verbose_name = u'Medio'
        verbose_name_plural = u'Medios'
        ordering = ('id', )

    def puede_eliminar(self):
        return not self.planaccionpersonaplanth_set.filter(status=True).values_list('id', flat=True).exists()

    def model_name(self):
        return self._meta.model_name

    def app_label(self):
        return self._meta.app_label

class PlanAccionPersonaPlanTh(ModeloBase):
    persona = models.ForeignKey(PersonaPlanTh, verbose_name=u'Persona', on_delete=models.PROTECT)
    competencia = models.ForeignKey('sagest.CompetenciaLaboral', verbose_name = u'Competencia Laboral', blank=True, null=True, on_delete = models.CASCADE)
    medio = models.ForeignKey(MedioPlanTh, verbose_name=u'Medio, recurso o mecanismo',blank=True, null=True, on_delete=models.PROTECT)
    porcentaje_medio = models.IntegerField(default=0, verbose_name=u'Porcentaje Gratuidad')
    tematica = models.TextField(blank=True, null=True, verbose_name=u'Temática de la formación específica')
    validacionplan = models.BooleanField(default=True, verbose_name=u'Validación en el plan de formación y capacitación')
    evidencia = models.BooleanField(default=True, verbose_name=u'Requiere evidencia')
    archivo = models.FileField(upload_to='planaccion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Evidencia')

    class Meta:
        verbose_name = u'Plan de acción'
        verbose_name_plural = u'Planes de acción'
        ordering = ('id', )

class MovilidadPersonaPlanTh(ModeloBase):
    persona = models.ForeignKey(PersonaPlanTh, verbose_name=u'Persona', on_delete=models.PROTECT)
    tipo = models.IntegerField(choices=MOVILIDAD, default=1, verbose_name=u"Tipo de movilidad")
    areaconocimiento = models.ForeignKey('sga.AreaConocimientoTitulacion', blank=True, null=True, verbose_name=u"Área de conocimiento", on_delete=models.CASCADE)
    competencia = models.ForeignKey('sagest.CompetenciaLaboral', verbose_name = u'Competencia Laboral', blank=True, null=True, on_delete = models.CASCADE)
    tipolinea = models.ForeignKey(TipoLineaPlanTh, verbose_name=u'Tipo de línea',blank=True, null=True, on_delete=models.PROTECT)
    unidadorganizacional = models.ForeignKey('sagest.Departamento', blank=True, null=True, verbose_name=u"Unidad organizacional", on_delete=models.CASCADE)
    cargo = models.ForeignKey('sagest.DenominacionPuesto', verbose_name = u'Cargo', blank=True, null=True, on_delete = models.CASCADE)

    class Meta:
        verbose_name = u'Plan de carrera'
        verbose_name_plural = u'Planes de carrera'
        ordering = ('id', )