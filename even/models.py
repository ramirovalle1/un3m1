from django.core.cache import cache
from django.db import models
from sga.funciones import ModeloBase
from sga.models import Inscripcion, Canton, Periodo

TIPOS_PERFILES = (
    (1, u'ESTUDIANTE'),
    (2, u'ADMINISTRATIVOS'),
    (3, u'PROFESORES'),
    (4, u'EXTERNO'),
    (5, u'VISITANTE')
)

class Evento(ModeloBase):
    nombre = models.CharField(max_length=500, default='', verbose_name=u'Nombre de evento')

    class Meta:
        verbose_name = u"Evento"
        verbose_name_plural = u"Eventos"

    def __str__(self):
        return u'%s' % (self.nombre)

    def puede_eliminar(self):
        if self.periodoevento_set.filter(status=True):
            return False
        return True


class TipoEvento(ModeloBase):
    nombre = models.CharField(max_length=500, default='', verbose_name=u'Tipo de evento')

    class Meta:
        verbose_name = u"Tipo de evento"
        verbose_name_plural = u"Tipos de eventos"

    def __str__(self):
        return u'%s' % (self.nombre)

    def puede_eliminar(self):
        if self.periodoevento_set.filter(status=True):
            return False
        return True


class PeriodoEvento(ModeloBase):
    periodo = models.ForeignKey(Periodo, blank=True, null=True,verbose_name=u'Periodo académico',on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, verbose_name=u'Evento',on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoEvento, verbose_name=u'Tipo de Evento',blank=True, null=True,on_delete=models.CASCADE)
    fechainicio = models.DateField(null=True, blank=True,verbose_name='Fecha inicio evento')
    fechainicioinscripcion = models.DateField(null=True, blank=True,verbose_name='Fecha inicio inscripcion evento')
    fechainicioconfirmar = models.DateField(null=True, blank=True,verbose_name='Fecha inicio confirmar evento')
    fechafin = models.DateField(null=True, blank=True,verbose_name='Fecha fin evento')
    fechafininscripcion = models.DateField(null=True, blank=True,verbose_name='Fecha fin inscripcion evento')
    fechafinconfirmar = models.DateField(null=True, blank=True,verbose_name='Fecha fin confirmar evento')
    horainicio = models.TimeField(null=True, blank=True, verbose_name=u"Hora inicio")
    horafin = models.TimeField(null=True, blank=True, verbose_name=u"Hora fin")
    imagen = models.FileField(upload_to='imagenevento', blank=True, null=True, verbose_name=u'Imagen del evento')
    portada = models.FileField(upload_to='imagenportadaevento', blank=True, null=True, verbose_name=u'Portada del evento')
    cuerpo = models.TextField(default='', verbose_name=u'Cuerpo', blank=True)
    descripcionbreve = models.TextField(default='', verbose_name=u'Descripción breve', null=True, blank=True)
    iframemapa = models.TextField(default='', verbose_name=u'Iframe Mapa', null=True, blank=True)
    publicar = models.BooleanField(default=False, verbose_name=u'Publicar')
    todos = models.BooleanField(default=True, verbose_name=u'Mostrar para todos los cantones')
    aplicaperiodo = models.BooleanField(default=False, verbose_name=u'Aplica a periodo académico')
    tipoperfil = models.IntegerField(choices=TIPOS_PERFILES, default=1, verbose_name=u'Tipo de evento')
    cerrado = models.BooleanField(default=False, verbose_name=u'Evento cerrado')
    permiteregistro = models.BooleanField(default=False, verbose_name=u'Permite registrarse')
    validacupo = models.BooleanField(default=False, verbose_name=u'Valida')
    cupo = models.IntegerField(default=0, verbose_name=u'Cupo')
    link = models.CharField(max_length=500, blank=True, null=True, verbose_name='Link de redirección')
    obligatorio = models.BooleanField(default=False, verbose_name=u'Obligatorio')

    class Meta:
        verbose_name = u"Periodo evento"
        verbose_name_plural = u"Periodos eventos"

    def __str__(self):
        return u'%s - %s' % (self.evento,self.tipo)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(PeriodoEvento, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(PeriodoEvento, self).delete(*args, **kwargs)

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        from sga.models import Persona
        participantes = Persona.objects.filter(status=True).values_list('id', flat=True)
        cache.delete_many([f"eventosdisponible_persona_id{encrypt(p)}" for p in participantes])
        cache.delete_many([f"miseventos_persona_id{encrypt(p)}" for p in participantes])
        cache.delete_many([f"periodoevento_disponible_sinconfirmar_persona_id{encrypt(p)}" for p in participantes])

    def get_perfil(self):
        if self.tipo:
            return dict(TIPOS_PERFILES)[self.tipoperfil]
        else:
            return ''

    def puede_eliminar(self):
        if self.registroevento_set.filter(status=True):
            return False
        return True

    def nro_inscritos(self):
        return self.registroevento_set.filter(status=True).count()

    def nro_asistentes(self):
        return self.registroevento_set.filter(status=True, estado_confirmacion=1).count()

    def nro_faltas(self):
        return self.registroevento_set.filter(status=True, estado_confirmacion=2).count()

    def nro_pendiente(self):
        return self.registroevento_set.filter(status=True, estado_confirmacion=0).count()



class DetallePeriodoEvento(ModeloBase):
    periodo = models.ForeignKey(PeriodoEvento, verbose_name=u'Periodo del evento', blank=True, null=True,on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u"Cantón",on_delete=models.CASCADE)


ESTADOS_CONFIRMACION = (
    (0, u'PENDIENTE'),
    (1, u'ASISTIRÁ'),
    (2, u'NO ASISTIRÁ'),
)


class RegistroEvento(ModeloBase):
    periodo = models.ForeignKey(PeriodoEvento, verbose_name=u'Periodo del evento',on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, verbose_name=u"Cantón",on_delete=models.CASCADE)
    perfil = models.ForeignKey('sga.PerfilUsuario', blank=True, null=True, verbose_name=u'Perfil del participante',on_delete=models.CASCADE)
    participante = models.ForeignKey('sga.Persona', verbose_name=u'Participante',on_delete=models.CASCADE)
    inscripcion = models.ForeignKey(Inscripcion,  blank=True, null=True,verbose_name=u'Inscripción',on_delete=models.CASCADE)
    estado_confirmacion = models.IntegerField(choices=ESTADOS_CONFIRMACION, default=0, verbose_name=u'Confirmación de asistenciá al evento')

    class Meta:
        verbose_name = u"Registro de evento"
        verbose_name_plural = u"Registros de eventos"

    def __str__(self):
        return self.periodo.evento.__str__()

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        cache.delete_many([f"eventosdisponible_persona_id{encrypt(self.participante_id)}",
                           f"miseventos_persona_id{encrypt(self.participante_id)}",
                           f"periodoevento_disponible_sinconfirmar_persona_id{encrypt(self.participante_id)}"])

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(RegistroEvento, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(RegistroEvento, self).save(*args, **kwargs)