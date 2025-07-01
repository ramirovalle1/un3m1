from django.db import models
from django.db.models import Count, F, Q
from django.utils.text import capfirst
from sga.models import Idioma, Periodo, Inscripcion, Asignatura, AsignaturaMalla, ModuloMalla, NivelMalla, Carrera

from sga.funciones import ModeloBase

ESTADO_INSCRIPCION = (
    (0, u'En curso'),
    (1, u'Asignado'),
    (2, u'No asignado'),
)

class Periodo(ModeloBase):
    idioma = models.ForeignKey(Idioma, verbose_name=u"Idioma", on_delete=models.CASCADE, null=True, blank=True)
    descripcion = models.CharField(default='', max_length=200, verbose_name=u"Descripcion Periodo")
    fecinicioinscripcion= models.DateTimeField(blank=True, null=True, verbose_name='Fecha Inicio Inscripcion')
    fecfininscripcion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha Fin Inscripcion')
    estado = models.BooleanField(default=False, verbose_name='Activo')
    sinmodulosaprobados = models.BooleanField(default=False, verbose_name='Puede aplicar solo con 0 modulos aprobados')
    url = models.CharField(blank=True, null=True, max_length=500, verbose_name=u'url')

    def __str__(self):
        return '{} [{}]'.format(self.idioma.__str__(), self.descripcion.__str__())

    def save(self, *args, **kwargs):
        super(Periodo, self).save(*args, **kwargs)

    def existe_grupo(self):
        return self.grupo_set.values('id').filter(status=True).exists()

    def primer_grupo_disponible(self):
        primer_grupo = self.grupo_set.annotate(num_inscripciones=Count('grupoinscripcion', filter=Q(grupoinscripcion__status=True))).filter(status=True,num_inscripciones__lt=F('cupo')).order_by('orden').first()
        return primer_grupo

    def grupos_disponibles(self):
        grupos = self.grupo_set.annotate(num_inscripciones=Count('grupoinscripcion', filter=Q(grupoinscripcion__status=True))).filter(status=True,num_inscripciones__lt=F('cupo')).order_by('orden')
        return grupos

    def cronograma_fechas_inscripcion_activa(self):
        from datetime import datetime
        hoy = datetime.now().date()
        return True if self.fecinicioinscripcion.date() <= hoy and self.fecfininscripcion.date() >= hoy else False

class PeriodoAsignatura(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u"Periodo", on_delete=models.CASCADE, null=True, blank=True)
    asignatura = models.ForeignKey(Asignatura, verbose_name=u"Asignatura", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return '{} - {}'.format(self.periodo.__str__(), self.asignatura.__str__())

    def save(self, *args, **kwargs):
        super(PeriodoAsignatura, self).save(*args, **kwargs)

class Grupo(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u"Periodo", on_delete=models.CASCADE, null=True, blank=True)
    idcursomoodle= models.IntegerField(default=0, verbose_name='Id Curso Moodle', null=True, blank=True)
    nombre= models.CharField(default='', max_length=200, verbose_name=u"Nombre Grupo")
    cupo= models.IntegerField(default=0, verbose_name='Cupo', null=True, blank=True)
    fecinicio = models.DateField(blank=True, null=True, verbose_name='Fecha Inicio')
    horainicio = models.TimeField(blank=True, null=True, verbose_name='Hora Inicio')
    fecfin = models.DateField(blank=True, null=True, verbose_name='Fecha Fin')
    horafin = models.TimeField(blank=True, null=True, verbose_name='Hora Fin')
    orden = models.IntegerField(default=0, verbose_name='Orden', null=True, blank=True)

    class Meta:
        verbose_name = u'Grupo '
        verbose_name_plural = u'Grupo'
        ordering = ('id',)

    def __str__(self):
        return '{} [{}]'.format(self.nombre.__str__(), self.periodo.__str__())

    def save(self, *args, **kwargs):
        super(Grupo, self).save(*args, **kwargs)

    def total_inscritos(self):
        return self.grupoinscripcion_set.filter(status=True).count()

    def existe_inscritos(self):
        return self.grupoinscripcion_set.values('id').filter(status=True).exists()

    def existe_cupo_disponible(self):
        return True if self.total_inscritos() < self.cupo else False

    def horario(self):
        return f'{self.horainicio.strftime("%I:%M %p")} a {self.horafin.strftime("%I:%M %p")}'

    def cupos_disponible(self):
        return self.cupo - self.total_inscritos()

    def existe_curso_moodle(self):
        return True if self.idcursomoodle != 0 else False

    def puede_visualizar_url_moodle(self):
        from datetime import datetime
        hoy = datetime.now().date()
        return True if self.fecinicio >= hoy and  self.fecinicio <= hoy else False

class GrupoInscripcion(ModeloBase):
    grupo = models.ForeignKey(Grupo, verbose_name=u"Grupo", on_delete=models.CASCADE, null=True, blank=True)
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u"Inscripcion", on_delete=models.CASCADE, null=True, blank=True)
    nota = models.FloatField(default=0, verbose_name=u'Nota', null=True, blank=True)
    estado = models.IntegerField(choices=ESTADO_INSCRIPCION, default=0, verbose_name=u'Estado')
    observacion = models.TextField(default='', verbose_name=u"Observacion", null=True, blank=True)
    migrado = models.BooleanField(default=False, verbose_name=u'Migrado al record')

    class Meta:
        verbose_name = u'Grupo Inscripcion '
        verbose_name_plural = u'Grupo Inscripcion'
        ordering = ('id',)

    def __str__(self):
        return '{} [{}]'.format(self.grupo.__str__(), self.inscripcion.__str__())

    def save(self, *args, **kwargs):
        super(GrupoInscripcion, self).save(*args, **kwargs)

    def obtener_creditos_horas_modulo(self):
        id_malla = self.inscripcion.inscripcionmalla_set.values_list('malla_id', flat=True).filter(status=True)
        id_asignatura= self.grupo.periodo.periodoasignatura_set.values_list('asignatura_id', flat=True).filter(status=True)
        modulomalla= ModuloMalla.objects.values_list('horas','creditos').filter(asignatura_id__in=id_asignatura, malla_id__in=id_malla, status=True).distinct()
        return modulomalla

    def obtener_asignaturas_homologadas(self):
        return self.grupoinscripcionasignatura_set.filter(status=True)

class GrupoInscripcionAsignatura(ModeloBase):
    grupoinscripcion = models.ForeignKey(GrupoInscripcion, verbose_name=u"Grupo Inscripcion ", on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, verbose_name=u"Asignatura", on_delete=models.CASCADE)

    class Meta:
        verbose_name = u'Grupo Inscripcion Asignatura'
        verbose_name_plural = u'Grupo Inscripcion Asignatura'
        ordering = ('id',)

    def __str__(self):
        return f"{self.asignatura}"

class PeriodoCarrera(ModeloBase):
    periodo = models.ForeignKey(Periodo, verbose_name=u"Periodo", on_delete=models.CASCADE, null=True, blank=True)
    carrera = models.ForeignKey(Carrera, verbose_name=u"Carrera", on_delete=models.CASCADE, null=True, blank=True)
    nivel = models.ManyToManyField(NivelMalla, verbose_name=u'Nivel Malla')


    class Meta:
        verbose_name = u'Periodo carrera'
        verbose_name_plural = u'Periodos carreras'
        ordering = ('id',)

    def __str__(self):
        return f'{self.carrera.__str__()} [{self.nivel.__str__()}]'
