from django.db import models
import datetime
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from sga.models import *

# Create your models here.

#PROCESO ANTEPROYECTO EDCON

class TipoAnteproyecto(ModeloBase):
    descripcion = models.CharField(default='', max_length=500, verbose_name=u"descripcion")

    def __str__(self):
        return u'%s' % self.descripcion

    def en_uso(self):
        return self.configtipoanteproyectorequisito_set.filter(status=True).exists() or \
               self.configtipoantecomponenteapre_set.filter(status=True).exists() or \
               self.solicitudanteproyecto_set.filter(status=True).exists()
    #   return self.empresaempleadora_set.all() or self.convenioempresa_set.all()

    class Meta:
        verbose_name = u"Tipo anteproyecto"
        verbose_name_plural = u"Tipos anteproyectos"
        ordering = ['id']
        # unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(TipoAnteproyecto, self).save(*args, **kwargs)


class Requisito(ModeloBase):
    descripcion = models.CharField(default='', max_length=200, verbose_name=u'Descripción')

    class Meta:
        verbose_name = 'Requisito anteproyecto'
        verbose_name_plural = 'Requisitos anteproyectos'
        # unique_together = ('descripcion',)
        ordering = ('-id',)

    def __str__(self):
        return u'%s' % (self.descripcion)

    def en_uso(self):
        return self.configtipoanteproyectorequisito_set.filter(status=True).exists()


    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(Requisito, self).save(*args, **kwargs)


class ConfigTipoAnteproyectoRequisito(ModeloBase):
    tipoanteproyecto = models.ForeignKey(TipoAnteproyecto, verbose_name=u'Tipo anteproyecto', on_delete=models.PROTECT)
    vigente = models.BooleanField(default=False, verbose_name=u'Vigente')
    requisitos = models.ManyToManyField(Requisito, verbose_name=u'Requisitos')

    class Meta:
        verbose_name = 'Configuración de tipo anteproyecto y requisito'
        verbose_name_plural = 'Configuración de tipo anteproyectos y requisitos'
        # unique_together = ('tipoanteproyecto', 'vigente')
        ordering = ('-id',)

    def __str__(self):
        return u'%s %s' % (self.tipoanteproyecto, u'Vigente' if self.vigente else u'No vigente')

    # Proceso automático. Si el usuario ingresa una configuracion vigente=true,se coloca en false las demás
    # configuraciones del mismo tipo de anteproyecto, porque sólo debe existir una vigente.
    def desactivar_configuraciones(self, request):
        lista = ConfigTipoAnteproyectoRequisito.objects.filter(status=True, tipoanteproyecto=self.tipoanteproyecto,
                                                               vigente=True).exclude(pk=self.id)
        id_desactivar = []
        for lis in lista:
            lis.vigente = False
            id_desactivar.append(lis.id)
            lis.save(request)
        return id_desactivar

    def listar_requisitos(self):
        return self.requisitos.filter(status=True)

    def esta_aplicandose(self):
        pass

    # validar que si ésta configuracion está en uso en solicitud de anteproyecto, NO pueda cambiar el tipo de anteproyecto
    def puede_editar_tipoanteproyecto(self):
        pass

    def en_uso(self):
        return self.solicitudanteproyecto_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(ConfigTipoAnteproyectoRequisito, self).save(*args, **kwargs)


# class DetalleConfigRequisito(ModeloBase):
#     configtipoanteproyectorequisito = models.ForeignKey(ConfigTipoAnteproyectoRequisito, verbose_name=u'Configuració tipo anteproyecto y requisito', on_delete=models.PROTECT)
#     requisito = models.ForeignKey(Requisito, verbose_name=u'Requisito', on_delete=models.PROTECT)
#
#     class Meta:
#         verbose_name = 'Detalle de configuración de requisito'
#         verbose_name_plural = 'Detalle de  configuración de requisitos'
#         unique_together = ('configtipoanteproyectorequisito', 'requisito')
#         ordering = ('id',)
#
#     def __str__(self):
#         return u'%s' % (self.configtipoanteproyectorequisito, self.requisito)
#
#     # validar que sólo se permita eliminar o editar un requisito mientras no haya sido usado en solicitud de anteproyecto
#     def puede_eliminar_editar(self):
#         pass
#
#     # def en_uso(self):
#     #     return self.detallerequisito_set.filter(status=True).exists()
#
#     def save(self, *args, **kwargs):
#         super(DetalleConfigRequisito, self).save(*args, **kwargs)


class ComponenteAprendizaje(ModeloBase):
    descripcion = models.CharField(default='', max_length=500, verbose_name=u'Descripción')

    class Meta:
        verbose_name = 'Componente de aprendizaje'
        verbose_name_plural = 'Componentes de aprendizaje'
        # unique_together = ('descripcion',)
        ordering = ('-id',)

    def __str__(self):
        return u'%s' % (self.descripcion)

    def en_uso(self):
        return self.configtipoantecomponenteapre_set.filter(status=True).exists() or \
               self.detallecomponenteaprendizaje_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(ComponenteAprendizaje, self).save(*args, **kwargs)

# descripcion = forms.CharField(required=False, label=u'Descripción',widget=forms.Textarea(attrs={'separator3': True}))


class ConfigTipoAnteComponenteApre(ModeloBase):
    tipoanteproyecto = models.ForeignKey(TipoAnteproyecto, verbose_name=u'Tipo anteproyecto', on_delete=models.PROTECT)
    vigente = models.BooleanField(default=False, verbose_name=u'Vigente')
    componentesaprendizajes = models.ManyToManyField(ComponenteAprendizaje, verbose_name=u'Componentes de aprendizajes')

    class Meta:
        verbose_name = 'Configuración de tipo anteproyecto y componente de aprendizaje'
        verbose_name_plural = 'Configuración de tipo anteproyectos y componentes de aprendizajes'
        # unique_together = ('tipoanteproyecto', 'vigente')
        ordering = ('-id',)

    def __str__(self):
        return u'%s %s' % (self.tipoanteproyecto, u'Vigente' if self.vigente else u'No vigente')

    def listar_requisitos(self):
        return self.componentesaprendizajes.filter(status=True)

    # def esta_aplicandose(self):
    #     pass

    # validar que si ésta configuracion está en uso en solicitud de anteproyecto, NO pueda cambiar el tipo de anteproyecto
    def puede_editar_tipoanteproyecto(self):
        pass

    # Proceso automático. Si el usuario ingresa una configuracion vigente=true,se coloca en false las demás
    # configuraciones del mismo tipo de anteproyecto, porque sólo debe existir una vigente.
    def desactivar_configuraciones(self, request):
        lista = ConfigTipoAnteComponenteApre.objects.filter(status=True, tipoanteproyecto=self.tipoanteproyecto,
                                                               vigente=True).exclude(pk=self.id)
        id_desactivar = []
        for lis in lista:
            lis.vigente = False
            id_desactivar.append(lis.id)
            lis.save(request)
        return id_desactivar

    def en_uso(self):
        return self.solicitudanteproyecto_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(ConfigTipoAnteComponenteApre, self).save(*args, **kwargs)


ESTADO_SOLICITUD_ANTEPROYECTO = (
    (1, u"INGRESADO"),
    (2, u"FIRMADO"),
    (3, u"APROBADO"),
    (4, u"RECHAZADO"),
)


TIPO_CERTIFICADO = (
    (1, u"CERTIFICADO DE ASISTENCIA Y APROBACIÓN"),
)


class SolicitudAnteproyecto(ModeloBase):
    fecha = models.DateField(verbose_name=u'Fecha de solicitud', null=True)
    tema = models.CharField(max_length=500, verbose_name=u'Tema')
    persona = models.ForeignKey("sga.Persona",verbose_name=u'Profesional que presenta anteproyecto', on_delete=models.PROTECT)
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_ANTEPROYECTO, default=1, verbose_name=u'Estado de la solicitud')
    tipoanteproyecto = models.ForeignKey(TipoAnteproyecto, verbose_name=u'Tipo anteproyecto', on_delete=models.PROTECT)
    #Secciones del documento anteproyecto
    introduccion = models.TextField(verbose_name=u'Introducción')
    metodologia = models.TextField(verbose_name=u'Metodología')
    estudiopertinencia = models.TextField(verbose_name=u'Estudio de pertinencia')
    problemasoluciona = models.TextField(verbose_name=u'Problema soluciona')
    objetivogeneral = models.TextField(verbose_name=u'Objetivo general')
    objetivoespecifico = models.TextField(verbose_name=u'Objetivos específicos')
    dirigidoa = models.TextField(verbose_name=u'Dirigido a')
    # Control interno del área
    configtipoanteproyectorequisito = models.ForeignKey(ConfigTipoAnteproyectoRequisito, verbose_name=u'Configuración requisito', on_delete=models.PROTECT)
    configtipoantecomponente = models.ForeignKey(ConfigTipoAnteComponenteApre, verbose_name=u'Configuración componente aprendizaje', on_delete=models.PROTECT, null=True)
    contenido = models.TextField(verbose_name=u'Contenido')
    # duración del anteproyecto
    # fechainicio =  models.DateField(verbose_name=u'Fecha inicio')
    # fechafin = models.DateField(verbose_name=u'Fecha fin')
    # duracion
    duracion = models.CharField(max_length=500, verbose_name=u'Duración', default=None)
    horario = models.TextField(verbose_name=u'Horario')
    considerarhorasautonomas = models.BooleanField(default=False, verbose_name=u'¿Desea contabilizar las horas de trabajo autónomo para la totalidad de horas del curso?')
    modalidad = models.ForeignKey(Modalidad, verbose_name=u'Modalidad', on_delete=models.PROTECT)
    tipocertificado = models.IntegerField(choices=TIPO_CERTIFICADO, default=1, verbose_name=u'Tipo certificado')
    # emitidopor = models.CharField(max_length=100, verbose_name=u'Emitido por')
    conclusion = models.TextField(verbose_name=u'Conclusión')
    recomendacion = models.TextField(verbose_name=u'Recomendación', blank=True, null=True)
    # observacion = models.CharField(max_length=500, verbose_name=u'Observación', blank=True, null=True)
    # solicitud pdf actual
    archivo = models.FileField(upload_to='qrcode/anteproyectos', blank=True, null=True, verbose_name=u'Archivo pdf')

    class Meta:
        verbose_name = u'Solicitud de anteproyecto'
        verbose_name_plural = u'Solicitudes de anteproyectos'
        ordering = ['id']
        # unique_together = ('tema', 'persona',)

    def __str__(self):
        return u'%s %s' % (self.tema, self.persona)

    def color_estado(self):
        if self.estado == 1:
            return 'default'
        elif self.estado ==2:
            return 'warning'
        elif self.estado ==3:
            return 'success'
        elif self.estado == 4:
            return 'danger'

            # return 'inverse'
            # return 'default'
            # return 'important'

    # validar que exista una configuración con sus requisitos asignados para permitir adicionar una solicitud de anteproyecto

    def historial_orden_ascendente(self):
        return self.historialsolicitudanteproyecto_set.filter(status=True).order_by('id')

    def puede_eliminar(self):
        if self.estado == 1 or self.estado == 2:
            return True
        return False

    def puede_editar(self):
        if not self.estado == 3:
            return True
        return False

    # def en_uso(self):
        # return self.historialsolicitudAnteproyecto_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        # self.observacion = self.observacion.upper().strip()
        super(SolicitudAnteproyecto, self).save(*args, **kwargs)

# class DetalleRequisito(ModeloBase):
#     solicitudanteproyecto = models.ForeignKey(SolicitudAnteproyecto, verbose_name=u'Solicitud anteproyecto', on_delete=models.PROTECT)
#     requisito = models.ForeignKey(Requisito, verbose_name=u'Requisito', on_delete=models.PROTECT)
#
#     class Meta:
#         verbose_name = u'Detalle requisito'
#         verbose_name_plural = u'Detalle requisitos'
#         ordering = ['id']
#
#     def __str__(self):
#         return u"%s - %s" % (self.solicitudanteproyecto, self.requisito)
#
#     # def en_uso(self):
#     #     return self.solicitudanteproyecto_set.filter(status=True).exists()
#
#     def save(self, *args, **kwargs):
#         super(DetalleRequisito, self).save(*args, **kwargs)

class DetalleComponenteAprendizaje(ModeloBase):
    solicitudanteproyecto = models.ForeignKey(SolicitudAnteproyecto, verbose_name=u'Solicitud anteproyecto', on_delete=models.PROTECT)
    componenteaprendizaje = models.ForeignKey(ComponenteAprendizaje, verbose_name=u'Componente de aprendizaje', on_delete=models.PROTECT)
    hora = models.IntegerField(default=1, verbose_name=u"Hora(s)", null=True, blank=True)

    class Meta:
        verbose_name = u'Detalle Componente de aprendizaje'
        verbose_name_plural = u'Detalle Componentes de aprendizajes'
        ordering = ['id']

    def __str__(self):
        return u"%s - %s" % (self.solicitudanteproyecto, self.componenteaprendizaje, self.hora)

    def total_horas(self):
        pass

    # def en_uso(self):
    #     return self.solicitudanteproyecto_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(DetalleComponenteAprendizaje, self).save(*args, **kwargs)


class HistorialSolicitudAnteproyecto(ModeloBase):
    fecha = models.DateField(verbose_name=u'Fecha')
    persona = models.ForeignKey("sga.Persona",verbose_name=u'Persona que generó cambio de estado', on_delete=models.PROTECT)
    solicitudanteproyecto = models.ForeignKey(SolicitudAnteproyecto, verbose_name=u'Solicitud', on_delete=models.PROTECT)
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_ANTEPROYECTO, default=1, verbose_name=u'Estado de la solicitud')
    archivo = models.FileField(upload_to='qrcode/anteproyectos', blank=True, null=True, verbose_name=u'Archivo')
    observacion = models.CharField(max_length=500, verbose_name=u'Observación', blank=True, null=True)

    class Meta:
        verbose_name = u'Historial de Solicitud de anteproyecto'
        verbose_name_plural = u'Historial de Solicitudes de anteproyectos'
        ordering = ['id']

    def __str__(self):
        return u"%s - %s - %s - %s - %s" % (self.fecha, self.persona, self.solicitudanteproyecto, self.get_estado_display(), self.archivo)

    def color_estado(self):
        if self.estado == 1:
            return 'default'
            # return 'info'
        elif self.estado ==2:
            return 'warning'
        elif self.estado ==3:
            return 'success'
        elif self.estado == 4:
            return 'danger'

    def save(self, *args, **kwargs):
        # self.observacion = self.observacion.upper().strip()
        super(HistorialSolicitudAnteproyecto, self).save(*args, **kwargs)