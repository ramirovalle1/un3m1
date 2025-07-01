from django.db import models

# Create your models here.
from sga.funciones import ModeloBase, remover_caracteres_especiales
from sga.models import Periodo, NivelMalla

ESTADO_SOLICITUD_DOCENTE=(
    (0, u'Pendiente'),
    (2, u'Aprobado director'),
    (3, u'Rechazado director'),
    (4, u'Aprobado decano'),
    (5, u'Rechazado decano'),
    (6, u'Aprobado')
)

class ActividadAyudantiaInvestigacion(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripción')

    def __str__(self):
        return u'%s' % (self.descripcion)


class PeriodoInvestigacion(ModeloBase):
    periodolectivo = models.ForeignKey(Periodo, on_delete=models.CASCADE, verbose_name=u'Periodo Lectivo')
    nombre = models.CharField(default='', max_length=250, verbose_name=u'Nombre Periodo Ayudantia Investigacion')
    fregistroactividad = models.DateField(verbose_name=u'Fecha límite para registrar actividad', blank=True,null=True)  # la fecha se usará para la subida de evidencias y registro de actividaes
    freceptarsolicitud = models.DateField(verbose_name=u'Fecha límite para receptar solicitudes', blank=True,null=True)  # la fecha se usará para la subida de evidencias y registro de actividaes
    finicio = models.DateField(verbose_name=u'Fecha inicio para recibir solicitudes', null=True, blank=True)
    ffin = models.DateField(verbose_name=u'Fecha final para recibir solicitudes', null=True, blank=True)
    publico = models.BooleanField(default=False, verbose_name=u'Publicado')
    descripcion = models.TextField(default='', null=True, blank=True, verbose_name=u'Descripción')

    def __str__(self):
        return u'%s - %s' % (self.periodolectivo, self.nombre)

    def en_uso(self):
        return not self.solicituddocente_set.filter(status=True).exists()

    def solicitudes(self):
        return self.solicituddocente_set.filter(status=True)

    def total_solicitudes(self):
        return len(self.solicituddocente_set.filter(status=True))

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(PeriodoInvestigacion, self).save(*args, **kwargs)

class SolicitudDocente(ModeloBase):
    periodoinvestigacion = models.ForeignKey(PeriodoInvestigacion, on_delete=models.CASCADE, verbose_name=u'Periodo de apertura de ayudantias de investigación')
    proyecto = models.ForeignKey('investigacion.ProyectoInvestigacion', verbose_name=u'Proyecto de investigacion aprobado', on_delete=models.CASCADE)
    solicitante = models.ForeignKey('sga.Persona', verbose_name=u'Director de proyecto',related_name="+", on_delete=models.CASCADE)
    mensaje = models.TextField(default='', null=True, blank=True, verbose_name=u'Mensaje de director de proyecto')
    dir_investigacion= models.ForeignKey('sga.Persona',null=True, blank=True, verbose_name=u'Director de Investigación', related_name="+", on_delete=models.CASCADE)
    val_dir_investigacion=models.IntegerField(choices=ESTADO_SOLICITUD_DOCENTE, default=0, verbose_name=u'Estado')
    fvalidacion_dir_investigacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha validacion de director de investigacion')
    obs_dir_investigacion= models.TextField(default='', blank=True, null=True, verbose_name='Observación director de investigación')
    dir_facultad = models.ForeignKey('sga.Persona',null=True, blank=True, verbose_name=u'Director de Facultad',related_name="+", on_delete=models.CASCADE)
    val_dir_facultad=models.IntegerField(choices=ESTADO_SOLICITUD_DOCENTE, default=0, verbose_name=u'Estado')
    fvalidacion_dir_facultad = models.DateTimeField(blank=True, null=True, verbose_name='Fecha validacion de director de facultad')
    obs_dir_facultad= models.TextField(default='', blank=True, null=True, verbose_name='Observación director de facultad')
    responsable_vinculacion = models.ForeignKey('sga.Persona',null=True, blank=True, verbose_name=u'Responsable Vinculación',related_name="+", on_delete=models.CASCADE)
    obs_responsable= models.TextField(default='', blank=True, null=True, verbose_name='Observación de responsable de vinculacion')
    cantidad = models.IntegerField(default=0, verbose_name=u'Cantidad de ayudantes requeridos')
    estado=models.IntegerField(choices=ESTADO_SOLICITUD_DOCENTE, default=0, verbose_name=u'Estado')

    def __str__(self):
        return f'{self.proyecto}'

    def nombre_simple(self):
        return '{}'.format(remover_caracteres_especiales(self.proyecto))


class AyudantiaInvestigacion(ModeloBase):
    solicitud = models.ForeignKey(SolicitudDocente,verbose_name=u'Solicitud aprobada del docente', on_delete=models.CASCADE)
    diasevidencia = models.IntegerField(default=0, verbose_name=u'Días subir evidencia')
    actividades = models.ManyToManyField(ActividadAyudantiaInvestigacion, verbose_name=u'Actividades')
    mostrar = models.BooleanField(default=False, verbose_name=u'Mostrar')
    nivelmalla = models.ForeignKey(NivelMalla, on_delete=models.CASCADE, verbose_name=u'Nivel')
    fechahastaaprobar = models.DateField(verbose_name=u'Fecha hasta aprobar', blank=True, null=True)
    notamaxima = models.IntegerField(default=0, verbose_name=u'Nota Maxima')
    horasmaxima = models.IntegerField(default=0, verbose_name=u'Horas máxima')

    def __str__(self):
        return f'{self.solicitud}'

class SolicitudEstudiante(ModeloBase):
    ayudantia = models.ForeignKey(AyudantiaInvestigacion, on_delete=models.CASCADE, verbose_name=u'Ayudantia de investigación')
    mensaje = models.TextField(default='', null=True, blank=True, verbose_name=u'Mensaje de estudiante')
    inscripcion = models.ForeignKey('sga.Inscripcion', verbose_name=u'Inscripción de estudiante', on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.inscripcion}'

