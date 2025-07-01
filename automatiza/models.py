from datetime import datetime

from django.db import models

# Create your models here.
from sga.funciones import ModeloBase
from core.choices.models.sagest import MY_ESTADO_EVALUACION_REQUERIMIENTO

#
PRIORIDAD = (
    (1, u"Baja"),
    (2, u"Media"),
    (3, u"Alta"),

)
ESTADO_REQUERIMIENTO = (
    (1, u"Pendiente"),
    (2, u"Asignado"),
    (3, u"Finalizado"),
)

TIPO_REQUERIMIENTO_AUTOMATIZA = (
    (1, u"Requerimiento"),
    (2, u"Incidente"),
)

class PlanificacionAutomatiza(ModeloBase):
    departamento = models.ForeignKey('sagest.Departamento', blank=True, null=True, verbose_name=u"Unidad organizacional", on_delete=models.CASCADE)
    fechainicio = models.DateField(blank=True, null=True)
    fechafin = models.DateField(blank=True, null=True)
    nombre = models.CharField(default='', max_length=500, blank=True, null=True, verbose_name=u"Nombre de planificacion")
    detalle = models.TextField(default='', verbose_name=u"Detalle")
    mostrar = models.BooleanField(default=False, verbose_name=u"¿Se muestra?")

    def __str__(self):
        return u'%s' % (self.nombre.capitalize())

    class Meta:
        verbose_name = u"Planificación"
        verbose_name_plural = u"Planificaciones"

    def vigente(self):
        return datetime.now().date() <= self.fechafin

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip()
        self.detalle = self.detalle.strip()
        super(PlanificacionAutomatiza, self).save(*args, **kwargs)

    def puede_eliminar(self):
        return True if not self.rq_planificaciones().exists() else False

    def rq_planificaciones(self):
        return self.requerimientoplanificacionautomatiza_set.filter(status=True)


class RequerimientoPlanificacionAutomatiza(ModeloBase):
    periodo = models.ForeignKey(PlanificacionAutomatiza, verbose_name=u"Periodo", on_delete=models.CASCADE)
    gestion = models.ForeignKey('sagest.SeccionDepartamento', blank=True, null=True, verbose_name=u"Gestión", on_delete=models.CASCADE)
    prioridad = models.IntegerField(choices=PRIORIDAD, default=3, verbose_name=u"Prioridad")
    orden = models.IntegerField(default=0, verbose_name=u"Orden")
    responsable = models.ForeignKey('sga.Persona', verbose_name=u'Responsable', on_delete=models.CASCADE)
    detalle = models.TextField(default='', verbose_name=u"Detalle")
    procedimiento = models.CharField(default='', max_length=500, blank=True, null=True, verbose_name=u"Procedimiento")
    estado = models.IntegerField(choices=ESTADO_REQUERIMIENTO, default=1, verbose_name=u"Estado")
    tiporequerimiento = models.IntegerField(choices=TIPO_REQUERIMIENTO_AUTOMATIZA, default=1, verbose_name=u"Tipo de requerimiento")
    evaluo = models.BooleanField(default=False, verbose_name=u"¿se evaluó?")
    estadoevaluacion = models.IntegerField(choices=MY_ESTADO_EVALUACION_REQUERIMIENTO, default=1, verbose_name=u"Estado de evaluación", blank=True, null=True)
    observacionevaluacion = models.TextField(default='', verbose_name=u"Observación de evaluación", blank=True, null=True)

    def __str__(self):
        return u'%s - %s' % (self.periodo.nombre, self.procedimiento)

    def documentos(self):
        return self.documentoadjuntorequerimiento_set.filter(status=True)

    def incidencia(self):
        return self.incidenciascrum_set.filter(status=True).first()

    def preguntas(self):
        incidencia = self.incidencia()
        if incidencia:
            preguntas = incidencia.categoria.gestion_recepta.preguntas_encuesta()
        return preguntas

    def respuestas_encuesta(self):
        from django.contrib.contenttypes.models import ContentType
        from balcon.models import RespuestaEncuestaSatisfaccion
        content_type = ContentType.objects.get_for_model(self)
        return RespuestaEncuestaSatisfaccion.objects.filter(object_id=self.id, content_type=content_type, status=True).order_by('pregunta_id')

    def color_prioridad(self):
        if self.prioridad == 3:
            return 'text-danger'
        elif self.prioridad == 2:
            return 'text-warning'
        elif self.prioridad == 1:
            return 'text-success'

    def color_estado(self):
        if self.estado == 1:
            return 'text-default'
        elif self.estado == 2:
            return 'text-primary'
        elif self.estado == 3:
            return 'text-success'

    def color_estado_evaluacion(self):
        if self.estadoevaluacion == 1:
            return 'text-default'
        elif self.estadoevaluacion == 2:
            return 'text-success'
        elif self.estadoevaluacion == 3:
            return 'text-danger'

    class Meta:
        verbose_name = u"Requerimiento"
        verbose_name_plural = u"Requerimientos"


class DocumentoAdjuntoRequerimiento(ModeloBase):
    requerimiento = models.ForeignKey(RequerimientoPlanificacionAutomatiza, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Documento principal de informe de baja')
    leyenda = models.CharField(default='', verbose_name=u"Leyenda del documento", max_length=200)
    archivo = models.FileField(upload_to='archivo_adjunto/', blank=True, null=True, verbose_name=u'Archivo firmado')

    def __str__(self):
        return u'%s' % (self.requerimiento)

    def tipo_archivo(self):
        namefile = self.archivo.name
        ext = namefile[namefile.rfind("."):].lower()
        if ext in ['.pdf']:
            return {'formato': 'pdf', 'icon': 'fa-file-pdf-o text-danger'}
        elif ext in ['.png', '.jpg', '.jpeg', '.svg']:
            return {'formato': 'img', 'icon': 'fa-file-image texto-blue'}
        elif ext in ['.xls', '.xlsx', '.xlsx', '.xlsb']:
            return {'formato': 'excel', 'icon': 'fa-file-excel-o text-success'}
        elif ext in ['.docx', '.doc']:
            return {'formato': 'word', 'icon': 'fa-file-word-o text-primary'}
        else:
            return {'formato': 'otro', 'icon': 'fa-file text-secondary'}

    class Meta:
        verbose_name = u'Documento Adjunto'
        verbose_name_plural = u'Documentos Adjuntos'
        ordering = ('fecha_creacion',)
