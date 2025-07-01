from django.db import models
from sga.funciones import ModeloBase
from sga.models import Profesor, Matricula, Carrera, Inscripcion


class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_agregar_cronogramaferia", "Puede agregar cronograma feria"),
            ("puede_modificar_cronogramaferia", "Puede modificar cronograma feria"),
            ("puede_eliminar_cronogramaferia", "Puede eliminar cronograma feria"),
            ("puede_gestionar_solicitudesferia", "Puede gestionar solicitudes del cronograma feria"),
            ("puede_generar_certificadosparticipacion_feria", "Puede generar Certificados de participación feria"),
            ("puede_generar_certificadosganador_feria", "Puede generar Certificados de ganadores feria"),
        )


class CronogramaFeria(ModeloBase):
    carreras = models.ManyToManyField(Carrera, verbose_name=u'Cronograma')
    objetivo = models.TextField(default='', verbose_name=u"Objetivo")
    fechainicio = models.DateField(verbose_name=u'Fecha inicio')
    fechafin = models.DateField(verbose_name=u'Fecha fin')
    fechainicioinscripcion = models.DateField(verbose_name=u'Fecha inicio inscripción')
    fechafininscripcion = models.DateField(verbose_name=u'Fecha fin inscripción')
    minparticipantes = models.IntegerField(verbose_name=u'Minimo num. participantes', null=True, blank=True)
    maxparticipantes = models.IntegerField(verbose_name=u'Máximo num. participantes', null=True, blank=True)


    class Meta:
        verbose_name = u'Cronograma'
        verbose_name_plural = u'Cronogramas'
        ordering = ('-fecha_creacion', )

    def __str__(self):
        return u'%s %s %s' % (self.objetivo, self.fechainicio, self.fechafin)

    def save(self, *args, **kwargs):
        #self.objetivo= self.objetivo.upper()
        super(CronogramaFeria, self).save(*args, **kwargs)

    def numero_solicitudes(self):
        return self.solicitudferia_set.filter(status=True).count()


ESTADO_SOLICITUD = (
    (1, u'SOLICITADO'),
    (2, u'APROBADO'),
    (3, u'RECHAZADO')
)
GANADOR_FACULTAD = (
    (1, u'NO ES GANADOR'),
    (2, u'GANADOR FACULTAD')
)

class SolicitudFeria(ModeloBase):
    cronograma = models.ForeignKey(CronogramaFeria, verbose_name=u'Cronograma', on_delete=models.CASCADE)
    tutor = models.ForeignKey(Profesor, verbose_name=u'Tutor', on_delete=models.CASCADE)
    titulo = models.TextField(default='', verbose_name=u"Titulo del Proyecto")
    resumen = models.TextField(default='', verbose_name=u"Resumen del Proyecto")
    objetivogeneral = models.TextField(default='', verbose_name=u"Objetivo General")
    objetivoespecifico = models.TextField(default='', verbose_name=u"Objetivo Especifico")
    materiales = models.TextField(default='', verbose_name=u"Materiales")
    resultados = models.TextField(default='', verbose_name=u"Resultados")
    estado = models.IntegerField(choices=ESTADO_SOLICITUD, default=1, null=True, blank=True, verbose_name=u'Estado')
    es_ganador = models.BooleanField(verbose_name='Es Ganador', default=False)
    puesto = models.CharField(verbose_name=u"Puesto del Ganador", max_length=300, null=True, blank=True)
    docpresentacionpropuesta = models.FileField(upload_to='feria/solicitudes/propuesta', max_length=500, null=True, blank=True, verbose_name=u"Presentación propuesta")
    es_ganadorfacultad = models.IntegerField(choices=GANADOR_FACULTAD, default=1, null=True, blank=True, verbose_name=u'Es Ganador Facultad')

    class Meta:
        verbose_name = u'Solicitud'
        verbose_name_plural = u'Solicitudes'
        ordering = ('-fecha_creacion', )

    def __str__(self):
        return u'%s - %s - %s - %s' % (self.usuario_creacion.username, self.titulo, self.tutor, self.cronograma)

    def save(self, *args, **kwargs):
        #self.objetivo= self.objetivo.upper()
        super(SolicitudFeria, self).save(*args, **kwargs)

    def get_docpropuesta(self):
        if self.docpresentacionpropuesta:
            return self.docpresentacionpropuesta.url
        else:
            return None

    def get_participantes_inscripciones(self):
        idms = self.participanteferia_set.values_list('inscripcion_id', flat=True).filter(status=True)
        return Inscripcion.objects.filter(pk__in=idms)

    def get_participantes(self):
        return self.participanteferia_set.filter(status=True)

    def save(self, *args, **kwargs):
        if self.puesto:
            self.puesto = self.puesto.upper()
        super(SolicitudFeria, self).save(*args, **kwargs)


class SolicitudFeriaHistorial(ModeloBase):
    solicitud = models.ForeignKey(SolicitudFeria, verbose_name=u'Solicitud', on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u"Observación")
    es_ganador = models.BooleanField(verbose_name='Es Ganador', default=False)
    puesto = models.CharField(default='', verbose_name=u"Puesto del Ganador", max_length=300)
    estado = models.IntegerField(choices=ESTADO_SOLICITUD, default=1, null=True, blank=True, verbose_name=u'Estado')
    es_ganadorfacultad = models.IntegerField(choices=GANADOR_FACULTAD, default=1, null=True, blank=True, verbose_name=u'Es Ganador Facultad')

    class Meta:
        verbose_name = u'Solicitud Historial'
        verbose_name_plural = u'Solicitudes Historial'
        # ordering = ('solicitud', '-fecha_creacion', )

    def __str__(self):
        return u'%s %s' % (self.solicitud, self.get_estado_display())

    def save(self, *args, **kwargs):
        self.observacion= self.observacion.upper()
        super(SolicitudFeriaHistorial, self).save(*args, **kwargs)


class ParticipanteFeria(ModeloBase):
    solicitud = models.ForeignKey(SolicitudFeria, verbose_name=u'Solicitud', on_delete=models.CASCADE)
    matricula = models.ForeignKey(Matricula, verbose_name=u'Matricula', on_delete=models.CASCADE,  null=True, blank=True)
    inscripcion = models.ForeignKey(Inscripcion, verbose_name=u'Inscripción', on_delete=models.CASCADE, null=True, blank=True)
    certificado = models.FileField(upload_to='feria/certificados/participantes', max_length=500, null=True, blank=True, verbose_name=u"Certificado")
    certificadoganador = models.FileField(upload_to='feria/certificados/ganadores', max_length=500, null=True, blank=True, verbose_name=u"Certificado Ganador")
    certificadoganadorfacultad = models.FileField(upload_to='feria/certificados/ganadoresFacultad', max_length=500, null=True, blank=True, verbose_name=u"Certificado Ganador Facultad")

    class Meta:
        verbose_name = u'Participante'
        verbose_name_plural = u'Participantes'
        ordering = ('-fecha_creacion', )
        #unique_together = ('solicitud', 'matricula')

    def __str__(self):
        return u'%s ' % self.matricula.inscripcion

    def save(self, *args, **kwargs):
        #self.objetivo= self.objetivo.upper()
        super(ParticipanteFeria, self).save(*args, **kwargs)

