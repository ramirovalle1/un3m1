from django.contrib.contenttypes.models import ContentType
from django.contrib import admin
from django.db import models
from django.db.models import Sum, Q, Count
from django.forms import model_to_dict
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from unidecode import unidecode

from sga.funciones import ModeloBase, remover_caracteres_especiales_unicode, null_to_decimal
from sga.models import Inscripcion, Periodo, TestSilaboSemanal, TestSilaboSemanalAdmision, LinkMateriaExamen, \
    Coordinacion

TIPO_INFORMACION = (
    (1, u"RESPUESTA RAPIDA"),
    (2, u"INFORMATIVA"),
)

ESTADO_SOLICITUD_BALCON = (
    (1, u"PENDIENTE"),
    (2, u"RECHAZADO"),
    (3, u"EN TRÁMITE"),
    (4, u"APROBADO"),
    (5, u"CERRADO"),
)

TIPO_SOLICITUD_BALCON = (
    (1, u"INFORMACIÓN"),
    (2, u"SOLICITUD"),
)

ESTADO_HISTORIAL_SOLICITUD_BALCON = (
    (1, u"ASIGNADO"),
    (2, u"REASIGNADO"),
    (3, u"RESUELTO"),
    (4, u"CERRADO"),
)


# tablas del modulo de seguimiento para el departamento de rolando
class Categoria(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    estado = models.BooleanField(default=False, verbose_name=u'Activo')
    coordinaciones = models.ManyToManyField(Coordinacion)

    def en_uso(self):
        return self.proceso_set.all().exists()

    def get_estado(self):
        return 'fa fa-check-circle text-success' if self.estado else 'fa fa-times-circle text-error'

    def __str__(self):
        return u'%s' % self.descripcion

    def procesos(self):
        return self.proceso_set.filter(status=True, activo=True)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(Categoria, self).save(*args, **kwargs)


class Requisito(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    estado = models.BooleanField(default=True, verbose_name=u'Activo')

    def en_uso(self):
        return self.requisitosconfiguracion_set.all().exists()

    def nombre_input(self):
        return remover_caracteres_especiales_unicode(self.descripcion).lower().replace(' ','_')

    def get_estado(self):
        return 'fa fa-check-circle text-success' if self.estado else 'fa fa-times-circle text-error'

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(Requisito, self).save(*args, **kwargs)


class Tipo(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    estado = models.BooleanField(default=True, verbose_name=u'Activo')

    def en_uso(self):
        return self.proceso_set.all().exists()

    def get_estado(self):
        return 'fa fa-check-circle text-success' if self.estado else 'fa fa-times-circle text-error'

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(Tipo, self).save(*args, **kwargs)


class Servicio(ModeloBase):
    from sagest.models import OpcionSistema
    nombre = models.CharField(default='', blank=True, null=True, max_length=500, verbose_name=u"Nombre")
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    estado = models.BooleanField(default=True, verbose_name=u'Activo')
    opcsistema = models.ManyToManyField(OpcionSistema, verbose_name=u'Opcion sistema')

    def en_uso(self):
        return self.procesoservicio_set.all().exists()

    def get_estado(self):
        return 'fa fa-check-circle text-success' if self.estado else 'fa fa-times-circle text-error'

    def __str__(self):
        return u'%s' % self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        super(Servicio, self).save(*args, **kwargs)


class Proceso(ModeloBase):
    sigla = models.CharField(default='', max_length=1000, blank=True, null=True, verbose_name='Sigla Proceso')
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    interno = models.BooleanField(default=False, verbose_name=u'Interno')
    externo = models.BooleanField(default=False, verbose_name=u'Externo')
    tipo = models.ForeignKey(Tipo, null=True, blank=True, verbose_name=u'Tipo solicitud',on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, blank=True, null=True, verbose_name=u'Categoria',on_delete=models.CASCADE)
    departamento = models.ForeignKey('sagest.Departamento', blank=True, null=True, verbose_name=u'Departamento',on_delete=models.CASCADE)
    tiempoestimado = models.TextField(default='', verbose_name=u'Tiempo Estimado', blank=True)
    activo = models.BooleanField(default=True, verbose_name=u'Activo')
    activoadmin = models.BooleanField(default=True, verbose_name=u'Activo administrador')
    unicasolicitud = models.BooleanField(default=False, verbose_name=u'Unica solicitud')
    subesolicitud = models.BooleanField(default=False, verbose_name=u'Debe subir solicitud')
    persona = models.ForeignKey('sga.Persona', on_delete=models.PROTECT, verbose_name=u"Persona", blank=True, null=True)
    presidentecurso = models.BooleanField(default=False, verbose_name=u'Aplica presidente curso')

    def __str__(self):
        return u'%s - %s' % (self.sigla,self.categoria.descripcion)

    def name_estadistica(self):
        return f'{self.sigla} - {self.categoria.descripcion}'

    def encuesta_configurada(self):
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(self)
        return EncuestaProceso.objects.filter(object_id=self.id, content_type=content_type, status=True).first()

    def total_servicios(self):
        idlist = self.procesoservicio_set.filter(status=True).values_list('id', flat=True)
        return Informacion.objects.filter(status=True, servicio_id__in=idlist).count()

    def informacion_mostrada(self):
        idlist = self.procesoservicio_set.filter(status=True).values_list('id', flat=True)
        return Informacion.objects.filter(status=True, servicio_id__in=idlist, mostrar=True)

    def get_procesoservicios(self):
        return self.procesoservicio_set.filter(status=True).order_by('id')

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        self.sigla = self.sigla.strip().upper()
        super(Proceso, self).save(*args, **kwargs)

    def get_estado(self):
        return 'fa fa-check-circle text-success' if self.activo else 'fa fa-times-circle text-error'

    def tiene_encuesta(self):
        return self.encuestaproceso_set.exists()

    def encuesta_proceso(self):
        return self.encuestaproceso_set.filter(status=True).order_by('-valoracion').first()

    class Meta:
        verbose_name = u"Proceso Balcon"
        verbose_name_plural = u"Proceso Balcon"


class ProcesoServicio(ModeloBase):
    proceso = models.ForeignKey(Proceso, verbose_name=u'Proceso', blank=True, null=True,on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, verbose_name=u'Servicio', blank=True, null=True,on_delete=models.CASCADE)
    tiempominimo = models.IntegerField(default=0, verbose_name=u"Tiempo minimo")
    tiempomaximo = models.IntegerField(default=0, verbose_name=u"Tiempo maximo")
    minutos = models.IntegerField(default=0, verbose_name=u"Tiempo en minutos")
    opcsistema = models.ForeignKey('sagest.OpcionSistema', verbose_name=u'Opcion sistema',  blank=True, null=True,on_delete=models.CASCADE)
    url = models.CharField(default='', max_length=5000, verbose_name=u'Url', blank=True, null=True)
    #activo = models.BooleanField(default=True, verbose_name=u'Mostrar')

    def __str__(self):
        return u'%s' % (self.servicio.nombre)

    def tiene_requisitos(self):
        tiene = self.requisitosconfiguracion_set.filter(status=True).exists()
        return 'fa fa-check-circle text-success' if tiene else 'fa fa-times-circle text-error'

    def puede_eliminar(self):
        if self.historialsolicitud_set.filter(status=True).exists():
            return False
        return True

    def solicitudes(self):
        return Solicitud.objects.filter(pk__in=self.historialsolicitud_set.filter(status=True).values_list('solicitud_id', flat=True).distinct(), status=True)

    def solicitudes_por_estado(self, estado):
        return Solicitud.objects.filter(pk__in=self.historialsolicitud_set.filter(status=True).values_list('solicitud_id', flat=True).distinct(), status=True, estado=estado)

    def total_solicitudes(self):
        if self.solicitudes().exists():
            return self.solicitudes().count()
        return 0

    def tiene_novedades_admision(self):
        return RegistroNovedadesExternoAdmision.objects.filter(solicitud_id__in=self.historialsolicitud_set.filter(status=True).values_list('solicitud_id', flat=True).distinct()).exists()

    def novedades_admision(self):
        if self.tiene_novedades_admision():
            return RegistroNovedadesExternoAdmision.objects.filter(solicitud_id__in=self.historialsolicitud_set.filter(status=True).values_list('solicitud_id', flat=True).distinct())
        return None

    def tiene_novedades_admision_por_estado(self, estado):
        return RegistroNovedadesExternoAdmision.objects.filter(solicitud_id__in=self.historialsolicitud_set.filter(status=True).values_list('solicitud_id', flat=True).distinct(), solicitud__estado=estado).exists()

    def novedades_admision_por_estado(self, estado):
        if self.tiene_novedades_admision_por_estado(estado):
            return RegistroNovedadesExternoAdmision.objects.filter(solicitud_id__in=self.historialsolicitud_set.filter(status=True).values_list('solicitud_id', flat=True).distinct(), solicitud__estado=estado)
        return None

    def tiene_tipos(self):
        return self.tipoprocesoservicio_set.filter(status=True).exists()
        # return 'fa fa-check-circle text-success' if tiene else 'fa fa-times-circle text-error'

    def tipos_servicios(self):
        return self.tipoprocesoservicio_set.filter(status=True, mostrar=True)

    class Meta:
        verbose_name = u'Proceso Servicio Balcón de Servicios'
        verbose_name_plural = u'Procesos Solicitudes Balcón de Servicios'


class TipoProcesoServicio(ModeloBase):
    servicio = models.ForeignKey(ProcesoServicio, verbose_name=u'Servicio', blank=True, null=True,on_delete=models.CASCADE)
    nombre = models.CharField(default='', max_length=1000, blank=True, null=True, verbose_name='Nombre')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name='Descripción')
    departamento = models.ForeignKey('sagest.Departamento', blank=True, null=True, verbose_name=u'Departamento',on_delete=models.CASCADE)
    mostrar = models.BooleanField(default=True, verbose_name=u'Mostrar')

    def __str__(self):
        return f'{self.nombre}'

    class Meta:
        verbose_name = u'Tipo de Proceso Servicio Balcón de Servicios'
        verbose_name_plural = u'Tipos de Procesos Solicitudes Balcón de Servicios'


class Informacion(ModeloBase):
    tipo = models.IntegerField(choices=TIPO_INFORMACION, null=True, blank=True, verbose_name=u'Tipo respuesta')
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    informacion = models.TextField(default='', verbose_name=u'Cuerpo de información', blank=True, null=True)
    archivomostrar = models.FileField(upload_to='mostrarinfobalcon', blank=True, null=True, verbose_name=u'Archivo')
    archivodescargar = models.FileField(upload_to='descargarinfobalcon', blank=True, null=True, verbose_name=u'Archivo')
    mostrar = models.BooleanField(default=True, verbose_name=u'Mostrar')
    servicio = models.ForeignKey(ProcesoServicio, null=True, blank=True, verbose_name=u'Servicio',on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.get_tipo_display(), self.descripcion)

    class Meta:
        verbose_name = u'Información'
        verbose_name_plural = u'Informaciones'

    # def tipoinformacion(self):
    #     return model_to_dict(TIPO_INFORMACION)[self.tipo]

    # def en_uso(self):
    #     return self.detalletipoinformacion_set.filter(status=True).exists()

    def typefilemostrar(self):
        if self.archivomostrar:
            return self.archivomostrar.name[self.archivomostrar.name.rfind("."):]
        else:
            return None

    def typefiledescargar(self):
        if self.archivodescargar:
            return self.archivodescargar.name[self.archivodescargar.name.rfind("."):]
        else:
            return None

    def get_tipo(self):
        if self.tipo:
            return dict(TIPO_INFORMACION)[self.tipo]
        else:
            return ''

    def get_mostrar(self):
        return 'fa fa-eye text-info' if self.mostrar else 'fa fa-eye-slash text-error'

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(Informacion, self).save(*args, **kwargs)



class RequisitosConfiguracion(ModeloBase):
    servicio = models.ForeignKey(ProcesoServicio, verbose_name=u'Servicio', blank=True, null=True,on_delete=models.CASCADE)
    requisito = models.ForeignKey(Requisito, verbose_name=u'Requisito', blank=True, null=True,on_delete=models.CASCADE)
    # leyenda = models.TextField(default='', blank=True, null=True, verbose_name='Leyenda')
    obligatorio = models.BooleanField(default=False, verbose_name=u'Obligatorio')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def get_obligatorio(self):
        return 'fa fa-check-circle text-success' if self.obligatorio else 'fa fa-times-circle text-error'

    def get_activo(self):
        return 'fa fa-check-circle text-success' if self.activo else 'fa fa-times-circle text-error'


class Video(ModeloBase):
    video = models.FileField(upload_to='videobalcon', blank=True, null=True, verbose_name=u'video')
    servicio = models.ForeignKey(ProcesoServicio, verbose_name=u'Servicio', blank=True, null=True,on_delete=models.CASCADE)
    mostrar = models.BooleanField(default=True, verbose_name=u'Mostrar')
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u'Descripcion')

    def get_mostrar(self):
        return 'fa fa-eye text-info' if self.mostrar else 'fa fa-eye-slash text-info'

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        super(Video, self).save(*args, **kwargs)


class ResponsableDepartamento(ModeloBase):
    from sagest.models import Departamento
    responsable = models.ForeignKey('sga.Persona', verbose_name=u'Persona que recibe solicitud en dirección',
                                    on_delete=models.CASCADE)
    alias = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name=u'Alias')
    departamento = models.ForeignKey(Departamento, verbose_name=u'Dirección', on_delete=models.CASCADE)
    estado = models.BooleanField(default=True, verbose_name=u'Activo')

    def get_estado(self):
        return 'fa fa-check-circle text-success' if self.estado else 'fa fa-times-circle text-error'

    def en_uso(self):
        return HistorialSolicitud.objects.filter(status=True,asignadorecibe=self.responsable).exists()

    def total_solicitud(self):
        return HistorialSolicitud.objects.filter(status=True,asignadorecibe=self.responsable,estado=2).count()



class Agente(ModeloBase):  # PersonaSolicitud
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona',on_delete=models.CASCADE)
    alias = models.CharField(max_length=50,blank=True, null=True, unique=True, verbose_name=u'Alias')
    estado = models.BooleanField(default=False, verbose_name=u'Estado de la Persona')
    admin = models.BooleanField(default=False, verbose_name=u'Es administrador')
    proceso = models.ManyToManyField(Proceso, verbose_name=u'procesos')

    def en_uso(self):
        return self.solicitud_set.all().exists()

    def total_solicitud(self):
        return self.solicitud_set.filter(status=True, estado=1).count()

    def total_solicitud_rechazadas(self):
        return self.solicitud_set.filter(status=True, estado=2).count()

    def total_solicitud_entramite(self):
        return self.solicitud_set.filter(status=True, estado=3).count()

    def total_solicitud_resuelto(self):
        return self.solicitud_set.filter(status=True, estado=4).count()

    def total_solicitud_cerrado(self):
        return self.solicitud_set.filter(status=True, estado=5).count()

    def total_general_solicitud(self):
        return self.solicitud_set.filter(status=True).count()

    def get_estado(self):
        return 'fa fa-check-circle text-success' if self.estado else 'fa fa-times-circle text-error'

    def get_admin(self):
        return 'fa fa-check-circle text-success' if self.admin else 'fa fa-times-circle text-error'

    def __str__(self):
        return u'%s' % (self.persona)


class Solicitud(ModeloBase):
    codigo = models.CharField(default='', max_length=1000, blank=True, null=True, verbose_name='Codigo Solicitud')
    solicitante = models.ForeignKey('sga.Persona', blank=True, null=True, related_name='solicitante_persona', verbose_name=u'Persona que solicita',on_delete=models.CASCADE)
    agente = models.ForeignKey(Agente, blank=True, null=True, verbose_name=u'Agente recibe',on_delete=models.CASCADE)
    agenteactual = models.ForeignKey('sga.Persona', blank=True, null=True, related_name='agente_actual', verbose_name=u'Agente recibe',on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_BALCON, default=1, verbose_name=u'Estado')
    tipo = models.IntegerField(choices=TIPO_SOLICITUD_BALCON, default=1, verbose_name=u'Es solicitud o información')
    archivo = models.FileField(upload_to='solicitudbalcon', blank=True, null=True, verbose_name=u'Archivo de soporte')
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    perfil = models.ForeignKey('sga.PerfilUsuario', blank=True, null=True, verbose_name=u'Perfil del solicitante',on_delete=models.CASCADE)
    externo = models.BooleanField(default=False, verbose_name=u'Identifica usuario externo')
    numero = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Codigo')
    tiempoespera = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Tiempo espera (minutos)')
    tiempoesperareal = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Tiempo espera real (minutos)')

    def __str__(self):
        return u'%s - %s' % (self.solicitante, self.descripcion)

    def get_estado(self):
        return dict(ESTADO_SOLICITUD_BALCON)[self.estado]

    def color_estado(self):
        color='black'
        if self.estado == 2:
            color='danger'
        elif self.estado == 3:
            color='warning'
        elif self.estado == 4:
            color='success'
        elif self.estado == 5:
            color='info'
        return color

    def get_tiposolicitud(self):
        return dict(TIPO_SOLICITUD_BALCON)[self.tipo]

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def detalle(self):
        return self.historialsolicitud_set.filter(status=True).exists()

    def estadosolicitud(self):
        return ESTADO_SOLICITUD_BALCON[self.estado - 1][1]

    def tiposolicitud(self):
        return TIPO_SOLICITUD_BALCON[self.tipo - 1][1]

    def ver_servicio(self):
        return self.historialsolicitud_set.filter(status=True).order_by('id').last()

    def encuesta_proceso(self):
        from django.contrib.contenttypes.models import ContentType
        proceso = self.ver_servicio().servicio.proceso
        content_type = ContentType.objects.get_for_model(proceso)
        return EncuestaProceso.objects.filter(object_id=proceso.id, content_type=content_type, status=True)

    def encuesta_proceso_preguntas_vigentes(self):
        return self.encuesta_proceso().filter(vigente=True)

    def puede_calificar_proceso(self):
        #estado  de solicitud del proceso debe estar en estado ["Rechazado", "Aprobado", "Cerrado"] y el proceso tenga encuestas configuradas
        encuesta_vigentes = self.encuesta_proceso_preguntas_vigentes().values_list('id', flat=True).exists()
        return self.estado in [2, 4, 5] and not self.respondio_encuesta()

    def traer_departamento(self):
        qsbase = self.historialsolicitud_set.filter(status=True).order_by('id').last()
        if qsbase:
            return qsbase.departamento
        else:
            return None

    def tiene_departamento(self):
        depa = self.historialsolicitud_set.filter(status=True).order_by('id').last()
        if depa:
            if depa.departamento:
                return True
            else:
                return False
        return False

    def traer_ultimo_con_departamento(self):
        if self.historialsolicitud_set.filter(status=True,departamento__isnull=False).exists():
            return self.historialsolicitud_set.filter(status=True, departamento__isnull=False).order_by('id').last()
        return None

    def get_codigo(self):
        histori = self.historialsolicitud_set.all()
        if histori.exists():
            if histori.first().servicio:
                if histori.first().servicio.proceso:
                    tiposol = self.tiposolicitud()[:3]
                    inicial = histori.first().servicio.proceso.sigla
                    # codigo = str(self.numero).zfill(6)
                    codigo = str(self.pk).zfill(6)
                    return '{}-{}-{}{}-{}'.format(tiposol,inicial,self.fecha_creacion.year,self.fecha_creacion.month,codigo)
                else:
                    return ''
            else:
                return ''
        return ''

    def get_cerrado(self):
        return self.historialsolicitud_set.filter(estado=4).exists()

    def get_estudiante(self):
        Inscripcion.objects.filter(self.perfil.es_estudiante)

    def sol_devuelta(self, idpersona):
        historial=self.historialsolicitud_set.filter(status=True)
        ban=False
        if len(historial.filter(asignadorecibe_id=idpersona)) > 2:
            ultimo=historial.last()
            if ultimo.asignadorecibe.id == idpersona:
                ban=True
        return ban

    def devuelto(self):
        try:
            historial=self.historialsolicitud_set.filter(status=True, estado=2).values_list('asignadorecibe_id')
            ultimo=historial.last()
            if len(historial.filter(asignadorecibe_id=ultimo).values_list('id')) >= 2:
                return True
            return False
        except Exception as ex:
            return False

    def respondio_encuesta(self):
        from django.contrib.contenttypes.models import ContentType
        proceso = self.historialsolicitud_set.first().servicio.proceso
        content_type = ContentType.objects.get_for_model(proceso)
        encuesta = EncuestaProceso.objects.filter(object_id=proceso.id, content_type=content_type, status=True)
        totalpreguntas = len(encuesta.first().preguntas()) if encuesta.exists() else 0
        return len(self.respuestaencuestasatisfaccion_set.filter(status=True)) == totalpreguntas

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(Solicitud, self).delete(*args, **kwargs)

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        if cache.has_key(f"balconsolicitudes_persona_id{encrypt(self.solicitante_id)}"):
            cache.delete(f"balconsolicitudes_persona_id{encrypt(self.solicitante_id)}")

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.strip().upper()
        self.delete_cache()
        super(Solicitud, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Solicitud Balcón de Servicios'
        verbose_name_plural = u'Solicitudes Balcón de Servicios'
        ordering = ('numero',)


class HistorialSolicitud(ModeloBase):
    from sagest.models import Departamento
    #proceso = models.ForeignKey(Proceso, blank=True, null=True, verbose_name=u'Proceso')
    solicitud = models.ForeignKey(Solicitud, blank=True, null=True, verbose_name=u'Solicitud',on_delete=models.CASCADE)
    asignaenvia = models.ForeignKey('sga.Persona', blank=True, related_name="+", null=True, verbose_name=u'quien asigna',on_delete=models.CASCADE)
    asignadorecibe = models.ForeignKey('sga.Persona', related_name="+", blank=True, null=True, verbose_name=u'a quien se le asignó',on_delete=models.CASCADE)
    departamentoenvia = models.ForeignKey(Departamento, blank=True, null=True,  related_name="+", verbose_name=u'Departamento envia',on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, blank=True, related_name="+", null=True, verbose_name=u'Departamento',on_delete=models.CASCADE)
    servicio = models.ForeignKey(ProcesoServicio, blank=True, null=True, verbose_name=u'Servicio',on_delete=models.CASCADE)
    tiposervicio = models.ForeignKey(TipoProcesoServicio, blank=True, null=True, verbose_name=u'Tipo de Servicio',on_delete=models.CASCADE)
    respuestarapida = models.ForeignKey(Informacion, blank=True, null=True, verbose_name=u'Respuesta rápida',on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u'Observación', blank=True)
    estado = models.IntegerField(choices=ESTADO_HISTORIAL_SOLICITUD_BALCON, default=1, verbose_name=u'Estado')
    archivo = models.FileField(upload_to='solicitudbalconhistorial', blank=True, null=True, verbose_name=u'Archivo de soporte')

    def __str__(self):
        return u'%s' % (self.servicio)

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def estadohistorial(self):
        return dict(ESTADO_HISTORIAL_SOLICITUD_BALCON)[self.estado]

    def save(self, *args, **kwargs):
        super(HistorialSolicitud, self).save(*args, **kwargs)


class DetalleHistorialSolicitud(ModeloBase):
    from sagest.models import Departamento
    hsolicitud = models.ForeignKey(HistorialSolicitud, blank=True, null=True, verbose_name=u'Detalle historial Solicitud', on_delete=models.CASCADE)

    asignadorecibe = models.ForeignKey('sga.Persona', related_name="+", blank=True, null=True,
                                       verbose_name=u'a quien se le asignó', on_delete=models.CASCADE)
    respuestarapida = models.ForeignKey(Informacion, blank=True, null=True, verbose_name=u'Respuesta rápida',
                                        on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u'Observación', blank=True , null=True)
    estado = models.IntegerField(choices=ESTADO_HISTORIAL_SOLICITUD_BALCON, default=1, verbose_name=u'Estado')
    archivo = models.FileField(upload_to='solicitudbalconhistorial', blank=True, null=True,
                               verbose_name=u'Archivo de soporte')

    def __str__(self):
        return u'%s' % (self.servicio)

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def estadohistorial(self):
        return dict(ESTADO_HISTORIAL_SOLICITUD_BALCON)[self.estado]

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.strip().upper()
        super(DetalleHistorialSolicitud, self).save(*args, **kwargs)

class RequisitosSolicitud(ModeloBase):
    solicitud = models.ForeignKey(Solicitud, verbose_name=u'Solicitud',on_delete=models.CASCADE)
    requisito = models.ForeignKey(RequisitosConfiguracion, verbose_name=u'Requisito',on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='solicitudbalconrequisitos', verbose_name=u'Archivo del requisito')


#SERVICIOS INFORMATICOS
ESTADOS_SOLICITUD_INFORMATICOS = (
    (1, u'PENDIENTE'),
    (2, u'FINALIZADA'),
    (3, u'RECHAZADO'),
)

class SolucitudServiciosInformaticos(ModeloBase):
    numerodocumento = models.IntegerField(blank=True, null=True)
    codigodocumento = models.CharField(blank=True, null=True, max_length=200)
    fechaoperacion = models.DateTimeField(verbose_name='Fecha Operación')
    departamento = models.ForeignKey('sagest.Departamento', verbose_name=u'Departamento',on_delete=models.CASCADE)
    responsable = models.ForeignKey('sga.Persona', verbose_name=u'Responsable',on_delete=models.CASCADE)
    denominacionpuesto = models.CharField(blank=True, null=True, max_length=1000)
    director = models.ForeignKey('sga.Persona', related_name="serv_director_persona", verbose_name=u'Director', blank=True, null=True,on_delete=models.CASCADE)
    directordenominacionpuesto = models.CharField(blank=True, null=True, max_length=1000)
    descripcion = models.TextField(default='', verbose_name=u"Descripción")
    archivo = models.FileField(upload_to='solicitudbalcon', blank=True, null=True, verbose_name=u'Archivo de soporte')
    estados = models.IntegerField(default=1, choices=ESTADOS_SOLICITUD_INFORMATICOS, verbose_name=u'Estados Solicitud')

    def dict_estados(self):
        return dict(ESTADOS_SOLICITUD_INFORMATICOS)[self.estados]

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def __str__(self):
        return u'%s - %s %s %s' % (self.codigodocumento, self.departamento.nombre, self.responsable, self.fechaoperacion.strftime('%d-%m-%Y'))

    class Meta:
        verbose_name = u'Solicitud Servicio '
        verbose_name_plural = u'Solicitud de Servicio'
        ordering = ('-fechaoperacion', '-responsable')

    def repr_id(self):
        return str(self.id).zfill(4)

    def persona_entrega(self):
        return self.usuario_creacion.persona_set.all()[0]

    def save(self, *args, **kwargs):
        super(SolucitudServiciosInformaticos, self).save(*args, **kwargs)


class SolicitudObservacionesServiciosInformaticos(ModeloBase):
    solicitud = models.ForeignKey(SolucitudServiciosInformaticos, verbose_name='Solicitud',on_delete=models.CASCADE)
    estados = models.IntegerField(default=1, choices=ESTADOS_SOLICITUD_INFORMATICOS, verbose_name=u'Estados Solicitud')
    observacion = models.TextField(default='', blank=True, null=True, verbose_name='Observación')

    def __str__(self):
        return u"%s  -  %s " % (self.solicitud.codigodocumento, self.observacion)

    def dict_estados(self):
        return dict(ESTADOS_SOLICITUD_INFORMATICOS)[self.estados]

    class Meta:
        verbose_name = u'Observacion Solicitud Servicios Informaticos'
        verbose_name_plural = u'Observaciones Solicitudes Servicios Informaticos'
        ordering = ('solicitud',)


TIPO_ACTIVIDAD_REGISTRO_NOVEDADES = (
    (1, u'TEST'),
    (2, u'EXAMEN'),
    (3, u'AMBOS'),
)


class ConfigInformacionExterno(ModeloBase):
    fechaapertura = models.DateTimeField(verbose_name='Fecha Apertura', null=True, blank=True)
    fechacierre = models.DateTimeField(verbose_name='Fecha Cierre', null=True, blank=True)
    fechaactividad = models.DateField(verbose_name='Fecha del Test/Examen', null=True, blank=True)
    actividad = models.TextField(default='', verbose_name='Nombre de la Actividad', null=True, blank=True)
    tipo_actividad = models.IntegerField(default=3, choices=TIPO_ACTIVIDAD_REGISTRO_NOVEDADES, verbose_name=u'Tipo de actividades')
    informacion = models.ForeignKey(Informacion, related_name='+', verbose_name=u'Proceso del Servicio',on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, related_name='+', null=True, blank=True, verbose_name=u'Periodo Académico Admisión',on_delete=models.CASCADE)
    activo = models.BooleanField(default=False, verbose_name=u'Activo?')
    agente_ok = models.BooleanField(default=False, verbose_name=u'Activo con agente?')
    agenteregistro = models.ManyToManyField('sga.Persona', verbose_name=u'Agentes')
    banner = models.FileField(upload_to='registro_novedades/banner/', blank=True, null=True, verbose_name=u'Banner')

    def __str__(self):
        return u"FI:%s hasta FF:%s - %s" % (self.fechaapertura, self.fechacierre, self.informacion.servicio)

    def agentesregistros(self):
        return self.agenteregistro.all()

    class Meta:
        verbose_name = u'Configuración de Información Externo'
        verbose_name_plural = u'Condifguraciones de Información Externos'
        ordering = ('fechaapertura', 'fechacierre',)


CAUSALES = (
    (1, u"PROBLEMAS EN PLATAFORMA"),
    (2, u"ENFERMEDAD"),
)


class RegistroNovedadesExternoAdmision(ModeloBase):
    persona = models.ForeignKey('sga.Persona', related_name='+', verbose_name=u'Persona',on_delete=models.CASCADE)
    agente = models.ForeignKey('sga.Persona', related_name='+', verbose_name=u'Agente de Registro', blank=True, null=True,on_delete=models.CASCADE)
    matricula = models.ForeignKey('sga.Matricula', related_name='+', verbose_name=u'Matricula', blank=True, null=True,on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey('sga.MateriaAsignada', related_name='+', verbose_name=u'Materia Asignada', blank=True, null=True,on_delete=models.CASCADE)
    causal = models.IntegerField(choices=CAUSALES, default=0, verbose_name=u'Causal', blank=True, null=True)
    tipoprocesoservicio = models.ForeignKey(TipoProcesoServicio, related_name='+', verbose_name=u'Tipo proceso servicio', blank=True, null=True,on_delete=models.CASCADE)
    solicitud = models.ForeignKey(Solicitud, related_name='+', verbose_name=u'Solicitud', blank=True, null=True,on_delete=models.CASCADE)
    test = models.ForeignKey(TestSilaboSemanalAdmision, related_name='+', verbose_name=u'Test', blank=True, null=True,on_delete=models.CASCADE)
    examen = models.ForeignKey(LinkMateriaExamen, related_name='+', verbose_name=u'Examen', blank=True, null=True,on_delete=models.CASCADE)

    def __str__(self):
        return u"%s - %s" % (self.persona, self.solicitud.codigo)

    class Meta:
        verbose_name = u'Registro de Novedades Externo Admisión'
        verbose_name_plural = u'Registros de Noveades Externo Admisión'
        ordering = ('persona', 'solicitud',)


class CategoriaEncuesta(ModeloBase):
    nombre = models.TextField(default='', verbose_name=u'Nombre de la categoría', blank=True)

    def encuesta_proceso(self):
        return self.encuestaproceso_set.filter(status=True).order_by('-valoracion').first()

    def encuestas(self):
        return self.encuestaproceso_set.filter(status=True)

    def __str__(self):
        return u"%s" % (self.nombre)

    class Meta:
        verbose_name = u'Categoría Encuesta'
        verbose_name_plural = u'Categorías de Encuestas'


class EncuestaProceso(ModeloBase):
    categoria = models.ForeignKey(CategoriaEncuesta, verbose_name=u'Categoría encuesta', blank=True, null=True, on_delete=models.CASCADE)
    proceso = models.ForeignKey(Proceso, verbose_name=u'Proceso', blank=True, null=True, on_delete=models.CASCADE)
    valoracion = models.IntegerField(default=0, verbose_name=u"Cantidad de estrellas")
    vigente = models.BooleanField(default=False, verbose_name=u'Vigente')
    object_id = models.IntegerField(blank=True, null=True, verbose_name="Id de objeto")
    content_type = models.ForeignKey(ContentType, models.SET_NULL, verbose_name=u'Modelo',blank=True,null=True)
    sigla = models.CharField(default='', max_length=1000, blank=True, null=True, verbose_name='Sigla de la encuesta')

    def __str__(self):
        return u"%s - %s" % (self.name_estadistica(), self.valoracion)

    def name_estadistica(self):
        from django.apps import apps
        content_type = self.content_type
        # Utiliza el nombre del modelo para obtener la clase del modelo correspondiente
        modelo = apps.get_model(app_label=content_type.app_label, model_name=content_type.model)
        objeto = modelo.objects.get(id=self.object_id)
        return objeto.name_estadistica() if objeto.name_estadistica() else str(objeto)

    def sigla_text(self):
        sigla = self.sigla
        if not sigla:
            nombre = unidecode(self.name_estadistica()).split()
            cantidad = len(nombre) if len(nombre) <= 3 else 3
            for idx in range(0, cantidad):
                sigla += nombre[idx][:3]
                if idx + 1 < cantidad:
                    sigla += '-'
        return sigla

    def encuesta_objeto(self):
        from django.apps import apps
        content_type = self.content_type
        # Utiliza el nombre del modelo para obtener la clase del modelo correspondiente
        modelo = apps.get_model(app_label=content_type.app_label, model_name=content_type.model)
        objeto = modelo.objects.get(id=self.object_id)
        return objeto

    def preguntas(self, solicitud=None):
        preguntas_excluir = solicitud.respuestaencuestasatisfaccion_set.filter(status=True).values_list('pregunta_id', flat=True) if solicitud is not None else []
        return self.preguntaencuestaproceso_set.filter(status=True, estado=True).exclude(id__in=preguntas_excluir)

    def preguntas_obj(self):
        return self.preguntaencuestaproceso_set.filter(status=True, estado=True)

    def preguntas_para_estadisticas(self):
        return self.preguntaencuestaproceso_set.filter(status=True).order_by('id')

    def configuracion_estrellas(self):
        config = {
            'readOnly': False,
            'countStars': self.valoracion,
            'range': {
                'min': 0,
                'max': self.valoracion,
                'step': 1
            },
            'score': 0,
            'observacion': '',
            #showScore: True,
            'starConfig': {
                'size': 30,
                'fillColor': '#FFAA46',
                'strokeColor': '#0A0A0A'
            }
        }
        return config

    def lista_valoracion(self):
        return [i for i in range(1, self.valoracion+1)]

    def valoracion_colspan_general(self):
        return self.valoracion + 2

    def valoracion_colspan(self):
        return self.valoracion + 1

    class Meta:
        verbose_name = u'Encuestas de Proceso'
        verbose_name_plural = u'Encuestas de procesos'


class PreguntaEncuestaProceso(ModeloBase):
    encuesta = models.ForeignKey(EncuestaProceso, verbose_name=u'Encuesta Proceso', blank=True, null=True, on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    estado = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u"%s" % (self.encuesta)

    def valores_estadisticos(self, valoracion):
        lista = []
        lista.append(['Estrella', 'Valor'])
        for numero in range(1, valoracion + 1):
            text = 'estrella' if numero == 1 else 'estrellas'
            lista.append([f'{numero} {text}', self.cantidad_valoracion_respuesta_encuesta_estadistica(numero)])
        return lista

    def cantidad_total_respuesta_encuesta_estadistica(self):
        filtro = Q(status=True)
        return self.respuestaencuestasatisfaccion_set.aggregate(cantidad_respuesta=Count('id', filter=filtro))['cantidad_respuesta']

    def cantidad_valoracion_respuesta_encuesta_estadistica(self, valoracion):
        filtro = Q(valoracion=valoracion, status=True)
        return self.respuestaencuestasatisfaccion_set.aggregate(cantidad_respuesta=Count('id', filter=filtro))['cantidad_respuesta']

    def porcentaje_valoracion_respuesta_encuesta_estadistica(self, cantidad_valoracion):
        total = self.cantidad_total_respuesta_encuesta_estadistica()
        valor = ((cantidad_valoracion * 100) / total) if total > 0 else 0
        return null_to_decimal(valor, 2)

    def en_uso(self):
        return RespuestaEncuestaSatisfaccion.objects.filter(status=True, pregunta=self).exists()

    class Meta:
        verbose_name = u'Pregunta Encuestas '
        verbose_name_plural = u'Preguntas de Encuestas'


class RespuestaEncuestaSatisfaccion(ModeloBase):
    pregunta = models.ForeignKey(PreguntaEncuestaProceso, verbose_name=u'Pregunta Encuesta', blank=True, null=True, on_delete=models.CASCADE)
    solicitud = models.ForeignKey(Solicitud, verbose_name=u'Solicitud', blank=True, null=True, on_delete=models.CASCADE)
    valoracion = models.IntegerField(default=0, verbose_name=u"Cantidad de estrellas, seleccionada")
    observacion = models.TextField(default='', verbose_name=u'Observación', blank=True)
    object_id = models.IntegerField(blank=True, null=True, verbose_name="Id de objeto")
    content_type = models.ForeignKey(ContentType, models.SET_NULL, verbose_name=u'Modelo', blank=True, null=True)

    def __str__(self):
        return u"%s - %s" % (self.pregunta, self.valoracion)

    class Meta:
        verbose_name = u'Respuesta Encuesta'
        verbose_name_plural = u'Respuestas Encuestas'


class PreguntaGeneralEncuesta(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True)
    estado = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u"%s" % self.descripcion