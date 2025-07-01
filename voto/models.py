from django.contrib.auth.models import User
from django.db import models

from sga.My_Model import Persona
from sga.funciones import ModeloBase
from sga.models import Coordinacion,MesasPadronElectoral,DetPersonaPadronElectoral,CabPadronElectoral,TIPO_PERSONA_PADRON
from django.db.models import Sum, Q, F, FloatField, Count, IntegerField
from django.db.models.functions import Coalesce
from django.core.cache import cache

class ListaElectoral(ModeloBase):
    nombre = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name=u'Nombre')

    def total_x_lista(self, ids, periodo):
        ids_list = ids.values_list('id', flat=True)
        # qs = SubDetalleMesa.objects.filter(status=True, detallemesa__gremio_periodo__id=periodo, lista=self)
        qs = SubDetalleMesa.objects.filter(status=True, detallemesa__mesa_responsable__abierta=False, detallemesa__gremio_periodo__in=ids, lista=self)
        return qs.aggregate(total=Coalesce(Sum(F('totalvoto'), output_field=IntegerField()), 0)).get('total')

    def __str__(self):
        return f'{self.nombre}'

    class Meta:
        verbose_name = u'Lista Electoral'
        verbose_name_plural = u'Listas Electoral'

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(ListaElectoral, self).save(*args, **kwargs)


class GremioElectoral(ModeloBase):
    nombre = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name=u'Nombre')

    def __str__(self):
        return f'{self.nombre}'

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(GremioElectoral, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u'Gremio Electoral'
        verbose_name_plural = u'Gremios Electoral'


class GremioPeriodo(ModeloBase):
    gremio = models.ForeignKey(GremioElectoral, blank=True, null=True, verbose_name=u'Gremio', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.CabPadronElectoral', blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    coordinacion = models.ForeignKey(Coordinacion,blank=True, null=True, verbose_name=u'Coordinación', on_delete=models.CASCADE)
    tipo = models.IntegerField(default=1, choices=TIPO_PERSONA_PADRON, verbose_name=u'Tipo')

    def listas_electorales(self):
        qs = SubDetalleMesa.objects.filter(status=True, detallemesa__mesa_responsable__abierta=False, detallemesa__gremio_periodo=self).distinct('lista')
        return qs.order_by('lista')

    def tota_listas_electorales(self, lista):
        qs = SubDetalleMesa.objects.filter(status=True, detallemesa__mesa_responsable__abierta=False, detallemesa__gremio_periodo=self, lista_id=lista)
        return qs.aggregate(total=Coalesce(Sum(F('totalvoto'), output_field=IntegerField()), 0)).get('total')

    def totales_votos(self):
        votos = {}
        qs = DetalleMesa.objects.filter(status=True, mesa_responsable__abierta=False, gremio_periodo=self)
        votos['empadronado'] = qs.aggregate(total=Coalesce(Sum(F('empadronado'), output_field=IntegerField()), 0)).get(
            'total')
        votos['ausentismo'] = qs.aggregate(total=Coalesce(Sum(F('ausentismo'), output_field=IntegerField()), 0)).get(
            'total')
        votos['votovalido'] = qs.aggregate(total=Coalesce(Sum(F('votovalido'), output_field=IntegerField()), 0)).get(
            'total')
        votos['votonulo'] = qs.aggregate(total=Coalesce(Sum(F('votonulo'), output_field=IntegerField()), 0)).get(
            'total')
        votos['votoblanco'] = qs.aggregate(total=Coalesce(Sum(F('votoblanco'), output_field=IntegerField()), 0)).get(
            'total')
        return votos

    def totales_votos_rector(self):
        try:
            votos = {}
            valorglobal, valoradm, valorest = 0, self.periodo.adm_porcentaje(), self.periodo.est_porcentaje()
            ausentismoporc, validosporc, nulosporc, blancosporc = 0, 0, 0, 0
            ausentismotot, validostot, nulostot, blancostot = 0, 0, 0, 0
            if self.tipo == 1:
                valorglobal = float(valorest)
            if self.tipo == 3:
                valorglobal = float(valoradm)
            qs = DetalleMesa.objects.filter(status=True, mesa_responsable__abierta=False, gremio_periodo=self)
            votos['empadronado'] = empadronados = qs.aggregate(total=Coalesce(Sum(F('empadronado'), output_field=IntegerField()), 0)).get('total')
            votos['ausentismo'] = ausentismos = qs.aggregate(total=Coalesce(Sum(F('ausentismo'), output_field=IntegerField()), 0)).get('total')
            if not self.tipo == 2:
                votos['ausentismoporc'] = ausentismoporc = (ausentismos/empadronados)
                votos['ausentismotot'] = ausentismotot = (ausentismoporc*valorglobal)
            else:
                votos['ausentismoporc'] = ausentismos
                votos['ausentismotot'] = ausentismos
            votos['votovalido'] = validos = qs.aggregate(total=Coalesce(Sum(F('votovalido'), output_field=IntegerField()), 0)).get('total')
            if not self.tipo == 2:
                votos['validosporc'] = validosporc = (validos/empadronados)
                votos['validostot'] = validostot = (validosporc*valorglobal)
            else:
                votos['validosporc'] = validos
                votos['validostot'] = validos
            votos['votonulo'] = nulos = qs.aggregate(total=Coalesce(Sum(F('votonulo'), output_field=IntegerField()), 0)).get('total')
            if not self.tipo == 2:
                votos['nulosporc'] = nulosporc = (nulos/empadronados)
                votos['nulostot'] = nulostot = (nulosporc*valorglobal)
            else:
                votos['nulosporc'] = nulos
                votos['nulostot'] = nulos
            votos['votoblanco'] = blancos = qs.aggregate(total=Coalesce(Sum(F('votoblanco'), output_field=IntegerField()), 0)).get('total')
            if not self.tipo == 2:
                votos['blancosporc'] = blancosporc = (blancos/empadronados)
                votos['blancostot'] = blancostot = (blancosporc*valorglobal)
            else:
                votos['blancostot'] = blancos
                votos['blancostot'] = blancos
            totaleslista = []
            for lista in self.get_listas():
                subdet = SubDetalleMesa.objects.filter(status=True, detallemesa__mesa_responsable__abierta=False, detallemesa__gremio_periodo=self, lista_id=lista.lista.pk)
                total = subdet.aggregate(total=Coalesce(Sum(F('totalvoto'), output_field=IntegerField()), 0)).get('total')
                totalporc, totaltot = 0, 0
                if not self.tipo == 2:
                    totalporc = ((total*100)/validos)/100
                    totaltot = (totalporc*validostot)
                else:
                    totaltot = total
                totaleslista.append({'id': lista.lista.id, 'lista': lista.lista.nombre, 'total': total, 'porcentaje': totalporc, 'totaltot': totaltot})
            votos['totaleslista'] = totaleslista
            return votos
        except Exception as ex:
            return None

    def get_listas(self):
        return self.listagremio_set.filter(status=True).order_by('lista__nombre')

    class Meta:
        verbose_name = u'Gremio Periodo'
        verbose_name_plural = u'Gremios Periodo'

    def __str__(self):
        return f'({self.coordinacion_id}) / {self.coordinacion if self.coordinacion else "" } / {self.gremio}  ({self.get_tipo_display()})'

    def save(self, *args, **kwargs):
        super(GremioPeriodo, self).save(*args, **kwargs)


class ListaGremio(ModeloBase):
    gremio_periodo = models.ForeignKey(GremioPeriodo, blank=True, null=True, verbose_name=u'Gremio', on_delete=models.CASCADE)
    lista = models.ForeignKey(ListaElectoral, blank=True, null=True, verbose_name=u'Lista', on_delete=models.CASCADE)

    class Meta:
        verbose_name = u'Lista Gremio Periodo'
        verbose_name_plural = u'Listas Gremios Periodo'

    def __str__(self):
        return f'{self.gremio_periodo.coordinacion if self.gremio_periodo.coordinacion else ""  } {self.gremio_periodo.gremio} {self.lista.nombre} {self.gremio_periodo.get_tipo_display()}'

    def save(self, *args, **kwargs):
        super(ListaGremio, self).save(*args, **kwargs)


class SedesElectoralesPeriodo(ModeloBase):
    periodo = models.ForeignKey('sga.CabPadronElectoral', blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    canton = models.ForeignKey('sga.Canton', blank=True, null=True, verbose_name='Canton', on_delete=models.CASCADE)
    nombre = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name=u'Nombre Institución')
    latitud = models.FloatField(default=0, blank=True, null=True, verbose_name="Latitud")
    longitud = models.FloatField(default=0, blank=True, null=True, verbose_name="Longitud")
    direccion = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name=u'Dirección')
    provincias = models.ManyToManyField('sga.Provincia', verbose_name='Provincias')

    def latitudstr(self):
        return str(self.latitud)

    def longitudstr(self):
        return str(self.longitud)

    def __str__(self):
        return "{} - {} - {}".format(self.canton.provincia.nombre, self.canton.nombre, self.nombre)

    def personasporsede_count(self):
        return self.personassede_set.filter(status=True).count()

    def personasporsede(self):
        return self.personassede_set.filter(status=True).order_by('canton__provincia__nombre')

    def mesas(self):
        return self.configuracionmesaresponsable_set.filter(status=True).order_by('tipo', 'mesa__orden')

    class Meta:
        verbose_name = u'Sede Electoral'
        verbose_name_plural = u'Sedes Electorales'

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(SedesElectoralesPeriodo, self).save(*args, **kwargs)


class PersonasSede(ModeloBase):
    sede = models.ForeignKey(SedesElectoralesPeriodo, blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', blank=True, null=True, on_delete=models.CASCADE)
    canton = models.ForeignKey('sga.Canton', blank=True, null=True, verbose_name=u"Cantón", on_delete=models.CASCADE)
    perfil = models.ForeignKey('sga.PerfilUsuario', blank=True, null=True, verbose_name=u'Perfil del participante', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey('sga.Inscripcion',  blank=True, null=True,verbose_name=u'Inscripción', on_delete=models.CASCADE)
    matricula = models.ForeignKey('sga.Matricula',  blank=True, null=True,verbose_name=u'Matricula', on_delete=models.CASCADE)

    def __str__(self):
        return "{}, {} - {}".format(self.sede.canton.nombre, self.sede.canton.provincia.nombre, self.persona.__str__())

    def delete_cache(self):
        from sga.templatetags.sga_extras import encrypt
        if self.persona.id:
            if cache.has_key(f"data_seleccion_sede_electoral_id_{encrypt(self.persona.id)}_serializer_data"):
                cache.delete(f"data_seleccion_sede_electoral_id_{encrypt(self.persona.id)}_serializer_data")

    def delete(self, *args, **kwargs):
        self.delete_cache()
        super(PersonasSede, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.delete_cache()
        super(PersonasSede, self).save(*args, **kwargs)


class ConfiguracionMesaResponsable(ModeloBase):
    sede = models.ForeignKey(SedesElectoralesPeriodo, blank=True, null=True, verbose_name='Sedes Electorales', on_delete=models.CASCADE)
    mesa = models.ForeignKey(MesasPadronElectoral, blank=True, null=True, verbose_name=u'Mesa electoral', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.CabPadronElectoral', blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    tipo = models.IntegerField(default=1, choices=TIPO_PERSONA_PADRON, verbose_name=u'Tipo')
    presidente = models.ForeignKey(DetPersonaPadronElectoral,related_name='+', blank=True, null=True, verbose_name=u'Presidente', on_delete=models.CASCADE)
    secretario = models.ForeignKey(DetPersonaPadronElectoral,related_name='+', blank=True, null=True, verbose_name=u'Secretario', on_delete=models.CASCADE)
    vocal = models.ForeignKey(DetPersonaPadronElectoral,related_name='+', blank=True, null=True, verbose_name=u'Vocal', on_delete=models.CASCADE)
    presidente_alterno = models.ForeignKey(DetPersonaPadronElectoral,related_name='+', blank=True, null=True, verbose_name=u'Presidente Alterno', on_delete=models.CASCADE)
    secretario_alterno = models.ForeignKey(DetPersonaPadronElectoral,related_name='+', blank=True, null=True, verbose_name=u'Secretario Alterno', on_delete=models.CASCADE)
    vocal_alterno = models.ForeignKey(DetPersonaPadronElectoral,related_name='+', blank=True, null=True, verbose_name=u'Vocal Alterno', on_delete=models.CASCADE)
    logistica = models.ManyToManyField('sga.Persona', related_name='+', verbose_name=u'Logistica')
    acta_evidencia = models.FileField(upload_to='acta_electoral_evidencia', blank=True, null=True, verbose_name=u'Acta Electoral Evidencia')
    abierta = models.BooleanField(default=True, verbose_name=u'Acta Abierta')
    fecha_cierre = models.DateField(verbose_name=u'Fecha Cierre', blank=True, null=True)
    hora_cierre = models.TimeField(verbose_name=u'Hora Cierre', blank=True, null=True)
    persona_cierre = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u"Persona Cierre", related_name="+", on_delete=models.CASCADE)
    totalempadronados = models.IntegerField(default=0, verbose_name=u"Total Empadronados")
    acta_presidente = models.FileField(upload_to='actapresidente', max_length=8000, blank=True, null=True, verbose_name=u'Acta Presidente')
    fecha_notificacion_presidente = models.DateField(verbose_name=u'Fecha Presidente', blank=True, null=True)
    acta_secretario = models.FileField(upload_to='actapresidente', max_length=8000, blank=True, null=True, verbose_name=u'Acta Secretario')
    fecha_notificacion_secretario = models.DateField(verbose_name=u'Fecha Secretario', blank=True, null=True)
    acta_vocal = models.FileField(upload_to='actapresidente', max_length=8000, blank=True, null=True, verbose_name=u'Acta Vocal')
    fecha_notificacion_vocal = models.DateField(verbose_name=u'Fecha Vocal', blank=True, null=True)
    acta_presidente_alterno = models.FileField(upload_to='actamesa', max_length=8000, blank=True, null=True, verbose_name=u'Acta Presidente Alterno')
    fecha_notificacion_presidente_alterno = models.DateField(verbose_name=u'Fecha Presidente Alterno', blank=True, null=True)
    acta_secretario_alterno = models.FileField(upload_to='actamesa', max_length=8000, blank=True, null=True, verbose_name=u'Acta Secretario Alterno')
    fecha_notificacion_secretario_alterno = models.DateField(verbose_name=u'Fecha Secretario Alterno', blank=True, null=True)
    acta_vocal_alterno = models.FileField(upload_to='actamesa', max_length=8000, blank=True, null=True, verbose_name=u'Acta Vocal Alterno')
    fecha_notificacion_vocal_alterno = models.DateField(verbose_name=u'Fecha Vocal Alterno', blank=True, null=True)

    def get_tipo(self):
        return dict(TIPO_PERSONA_PADRON)[self.tipo]

    def get_abierta(self):
        return 'fa fa-check-circle text-success' if self.abierta else 'fa fa-times-circle text-error'

    def tf_acta_evidencia(self):
        if self.acta_evidencia:
            return self.acta_evidencia.name[self.acta_evidencia.name.rfind("."):]
        else:
            return None

    def total_votos(self):
        return DetalleMesa.objects.filter(status=True, mesa_responsable=self).aggregate(total=Coalesce(Sum(F('votovalido'), output_field=FloatField()), 0)).get('total')

    def gremio_mesas(self):
        return self.detallemesa_set.filter(status=True).order_by('gremio_periodo__gremio__nombre')

    def gremio_mesas_count(self):
        return self.detallemesa_set.filter(status=True).count()

    class Meta:
        verbose_name = u'Configuración Mesa'
        verbose_name_plural = u'Configuraciones de Mesas'

    def __str__(self):
        return f'{self.mesa.nombre} {self.periodo.nombre} {self.get_tipo_display()}'

    def save(self, *args, **kwargs):
        super(ConfiguracionMesaResponsable, self).save(*args, **kwargs)


class DetalleMesa(ModeloBase):
    mesa_responsable = models.ForeignKey(ConfiguracionMesaResponsable, blank=True, null=True, verbose_name=u'La mesa y sus reposables', on_delete=models.CASCADE)
    gremio_periodo = models.ForeignKey(GremioPeriodo, blank=True, null=True, verbose_name=u'Gremio', on_delete=models.CASCADE)
    empadronado = models.IntegerField(default=0, verbose_name=u"Numero de empadronados")
    ausentismo = models.IntegerField(default=0, verbose_name=u"Votos no utilizados (ausentismo)")
    votovalido = models.IntegerField(default=0, verbose_name=u"Votos total validos")
    votonulo = models.IntegerField(default=0, verbose_name=u"Votos nulos")
    votoblanco = models.IntegerField(default=0, verbose_name=u"Votos blanco")

    def adicional(self):
        return SubDetalleMesa.objects.filter(status=True, detallemesa=self).order_by('lista__nombre')

    class Meta:
        verbose_name = u'Detalle Mesa'
        verbose_name_plural = u'Detalles de Mesas'

    def __str__(self):
        return f'{self.mesa_responsable} {self.gremio_periodo} '

    def mis_listas(self):
        return self.gremio_periodo.listagremio_set.filter(status=True)

    def save(self, *args, **kwargs):
        super(DetalleMesa, self).save(*args, **kwargs)


class SubDetalleMesa(ModeloBase):
    detallemesa = models.ForeignKey(DetalleMesa, blank=True, null=True, verbose_name=u'Detalle de la mesa', on_delete=models.CASCADE)
    lista = models.ForeignKey(ListaElectoral, blank=True, null=True, verbose_name=u'Listas electorales', on_delete=models.CASCADE)
    totalvoto = models.IntegerField(default=0, verbose_name=u"Total de votos")

    class Meta:
        verbose_name = u'SubDetalles Mesa'
        verbose_name_plural = u'SubDetalles de Mesas'

    def __str__(self):
        return f'{self.detallemesa} {self.lista} '

    def save(self, *args, **kwargs):
        super(SubDetalleMesa, self).save(*args, **kwargs)


class DignidadesElectorales(ModeloBase):
    periodo = models.ForeignKey('sga.CabPadronElectoral', blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    nombre = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name=u'Nombre')

    def requisitos(self):
        return self.requisitosdignidadeselectorales_set.filter(status=True).order_by('pk')

    def solicitudes(self):
        return self.solicituddignidadeselectorales_set.filter(status=True).order_by('pk')

    def __str__(self):
        return f'{self.nombre}'

    class Meta:
        verbose_name = u'Diginidades Elecciones'
        verbose_name_plural = u'Diginidades Elecciones'

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(DignidadesElectorales, self).save(*args, **kwargs)


class RequisitosDignidadesElectorales(ModeloBase):
    dignidad = models.ForeignKey(DignidadesElectorales, blank=True, null=True, verbose_name=u'Dignidad', on_delete=models.CASCADE)
    orden = models.IntegerField(blank=True, null=True, verbose_name=u'Orden')
    requisito = models.CharField(default='', blank=True, null=True, max_length=5000, verbose_name=u'Requisito')
    marcolegal = models.CharField(default='', blank=True, null=True, max_length=5000, verbose_name=u'Marco Legal')
    medioverificacion = models.CharField(default='', blank=True, null=True, max_length=5000, verbose_name=u'Medio Verificción')

    def __str__(self):
        return f'{self.requisito}'

    class Meta:
        verbose_name = u'Requisito Diginidades Elecciones'
        verbose_name_plural = u'Requisitos Diginidades Elecciones'


ESTADOS_SOLICITUD_DIGNIDAD = (
    (1, u"PENDIENTE"),
    (2, u"APROBAR"),
    (3, u"RECHAZAR"),
)


class SolicitudDignidadesElectorales(ModeloBase):
    dignidad = models.ForeignKey(DignidadesElectorales, blank=True, null=True, verbose_name=u'Dignidad', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', blank=True, null=True, on_delete=models.CASCADE)
    solicitud = models.FileField(upload_to='solicitudelectoral', blank=True, null=True, verbose_name=u'Solicitud')
    estado = models.IntegerField(choices=ESTADOS_SOLICITUD_DIGNIDAD, default=1,verbose_name='Estado')

    def get_estado_color(self):
        label = 'label label-default'
        if self.estado == 2:
            label = 'label label-success'
        elif self.estado == 3:
            label = 'label label-important'
        return label

    def typefile(self):
        if self.solicitud:
            return self.solicitud.name[self.solicitud.name.rfind("."):]
        else:
            return None

    def __str__(self):
        return "{} {}".format(self.dignidad, self.persona)

    class Meta:
        verbose_name = u'Solicitud Diginidades Elecciones'
        verbose_name_plural = u'Solicitudes Diginidades Elecciones'


class RequisitoSolicitudDignidadesElectorales(ModeloBase):
    solicitud = models.ForeignKey(SolicitudDignidadesElectorales, blank=True, null=True, verbose_name=u'Solicitud', on_delete=models.CASCADE)
    requisito = models.ForeignKey(RequisitosDignidadesElectorales, blank=True, null=True, verbose_name=u'Requisito', on_delete=models.CASCADE)
    validado = models.BooleanField(default=False, verbose_name='¿Validado?')
    observacion = models.CharField(default='', blank=True, null=True, max_length=5000, verbose_name=u'Observación')
    archivo = models.FileField(upload_to='requisitoelectoral', blank=True, null=True, verbose_name=u'Evidencia')

    def typefile(self):
        if self.archivo:
            return self.archivo.name[self.archivo.name.rfind("."):]
        else:
            return None

    def __str__(self):
        return "{} {}".format(self.solicitud, self.requisito.requisito)

    class Meta:
        verbose_name = u'Requisito Solicitud Diginidades Elecciones'
        verbose_name_plural = u'Requisitos Solicitud Diginidades Elecciones'