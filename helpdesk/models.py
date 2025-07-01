# -*- coding: UTF-8 -*-
import operator
import os
import random
import time
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal

from sagest.models import AnioEjercicio, Departamento, ActivoFijo, ESTADO_PARTES, GruposCategoria, HdBloqueUbicacion, \
    ESTADO_DETALLE_INCIDENTE, TIPO_USUARIO, EstadoProducto, Ubicacion, UnidadMedidaPresupuesto, ESTADO_DANIO, Proveedor, \
    ActivoTecnologico
from sga.funciones import ModeloBase, null_to_decimal
from datetime import datetime
from django.db import models, connection, connections
from django.db.models import Q, Sum

from sga.models import CUENTAS_CORREOS, MONTH_CHOICES
from sga.tasks import conectar_cuenta

unicode = str


def actualizar_kardex_e_s(tipo, cantidad, obj):
    # Obtener el registro del producto en la tabla "BodegaKardex"
    try:
        kardex = BodegaKardex.objects.filter(status=True, producto=obj.producto).latest('fecha')
        saldo_inicial = kardex.saldoFinal
    except BodegaKardex.DoesNotExist:
        saldo_inicial = 0

    # Calcular el saldo final
    if tipo == 1:
        saldo_final = saldo_inicial + cantidad

    if tipo == 2 or tipo == 3:
        if not saldo_inicial <= 0:
            saldo_final = saldo_inicial - cantidad
        else:
            saldo_final = 0

    instancia = BodegaKardex(bodega=BodegaPrimaria.objects.get(pk=1),
                             producto=obj.producto,
                             tipotransaccion=BodegaTipoTransaccion.objects.get(pk=tipo),
                             unidadmedida=obj.unidadmedida,
                             cantidad=obj.cantidad,
                             saldoInicial=saldo_inicial,
                             saldoFinal=saldo_final,
                             fecha=datetime.now())

    if tipo == 2:
        instancia.detalleincidente = obj
    else:
        instancia.detallefactura = obj


    return instancia


#Modulo de HelpDesk
class HdDirector(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Director',related_name='hdDirector')
    vigente = models.BooleanField(default=False, verbose_name=u'Vigente')

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name = u"Grupo"
        verbose_name_plural = u"Grupos"


    def save(self, *args, **kwargs):
        super(HdDirector, self).save(*args, **kwargs)


class HdTipoIncidente(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')

    def __str__(self):
        return u'%s' % self.nombre

    def total_encuestas(self):
        if HdCabEncuestas.objects.filter(status=True).exists():
            return HdCabEncuestas.objects.filter(status=True).count()
        else:

            return 0

    def esta_activo(self):
        if self.hdcategoria_set.filter(status=True).exists():
            return True
        return False

    class Meta:
        verbose_name = u"Tipo de incidente"
        verbose_name_plural = u"Tipos de Incidentes"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.descripcion  = self.descripcion.upper()
        super(HdTipoIncidente, self).save(*args, **kwargs)


class HdCabEncuestas(ModeloBase):
    tipoincidente = models.ForeignKey(HdTipoIncidente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Tipo incidente",related_name='tipoincidente')
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % self.nombre

    def total_preguntas(self):
        return self.hdEncuestas.filter(status=True).count()

    class Meta:
        verbose_name = u"Encuesta de incidente"
        verbose_name_plural = u"Encuestas de Incidentes"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.descripcion  = self.descripcion.upper()
        super(HdCabEncuestas, self).save(*args, **kwargs)


class HdPreguntas(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Pregunta de incidente"
        verbose_name_plural = u"Preguntas de Incidentes"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdPreguntas, self).save(*args, **kwargs)


class HdDetEncuestas(ModeloBase):
    encuesta = models.ForeignKey(HdCabEncuestas, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Encuesta",related_name='hdEncuestas')
    pregunta = models.ForeignKey(HdPreguntas, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u"Pregunta",related_name='hdPreguntas')
    tiporespuesta = models.ForeignKey('sga.TipoRespuesta', on_delete=models.CASCADE, verbose_name=u'Tipo Respuesta',related_name='hddtiprespuesta')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % self.encuesta

    class Meta:
        verbose_name = u"Detalle Encuesta de incidente"
        verbose_name_plural = u"Detalles Encuestas de Incidentes"

    def save(self, *args, **kwargs):
        super(HdDetEncuestas, self).save(*args, **kwargs)


class HdGrupo(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(max_length=100, verbose_name=u'Descripción')
    tipoincidente = models.ForeignKey(HdTipoIncidente,  on_delete=models.CASCADE, null=True, blank=True, verbose_name=u'Tipo de incidente',related_name='t_incidente')

    def __str__(self):
        return u'%s' % self.nombre

    def mis_agentes(self):
        return self.hdgrupo.filter(status=True, estado=True).order_by('persona')

    def agentes_grupos(self):
        return self.hddetalle_grupo_set.values_list('id', flat=True).filter(status=True)

    def mis_agentesview(self):
        return self.hddetalle_grupo_set.filter(status=True).order_by('persona')

    def esta_activo(self):
        return True if self.hddetalle_grupo_set.filter(status=True).exists() else False

    class Meta:
        verbose_name = u"Grupo"
        verbose_name_plural = u"Grupos"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.descripcion  = self.descripcion.upper()
        super(HdGrupo, self).save(*args, **kwargs)


class HdDetalle_Grupo(ModeloBase):
    grupo = models.ForeignKey(HdGrupo, on_delete=models.CASCADE, verbose_name=u'Grupo',related_name='hdgrupo')
    persona = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, verbose_name=u'Persona',related_name='hdpersona')
    responsable = models.BooleanField(default=False, verbose_name=u'Responsable')
    estado = models.BooleanField(default=True, verbose_name=u'Estado')

    def __str__(self):
        return u'%s' % self.persona

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        from sga.models import Administrativo
        s = q.split(" ")
        if s.__len__() == 2:
            return Administrativo.objects.filter(Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])).distinct()[:limit]
        return Administrativo.objects.filter(Q(persona__nombres__contains=s[0]) | Q(persona__apellido1__contains=s[0]) | Q(persona__apellido2__contains=s[0]) | Q(persona__cedula__contains=s[0])).distinct()[:limit]

    def flexbox_repr(self):
        return self.persona.cedula + " - " + self.persona.nombre_completo_inverso() + ")"

    def mis_cargos(self):
        from sga.models import Persona
        return self.persona.distributivopersona_set.all()

    def mi_agente(self):
        return self.persona_id

    def esta_activo(self):
        return True if self.h_d_incidentes.filter(status=True).exists() else False

    class Meta:
        verbose_name = u"Detalle"
        verbose_name_plural = u"Detalles"

    def save(self, *args, **kwargs):
        super(HdDetalle_Grupo, self).save(*args, **kwargs)


class HdImpacto(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(max_length=100, verbose_name=u'Descripción')
    codigo = models.CharField(default='', max_length=10, verbose_name=u'Codigo')

    def __str__(self):
        return u'%s' % self.nombre

    def esta_activo(self):
        return True if self.hdurgencia_impacto_prioridad_set.filter(status=True).exists() else False

    class Meta:
        verbose_name = u"Impacto"
        verbose_name_plural = u"Impactos"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdImpacto, self).save(*args, **kwargs)


class HdUrgencia(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(max_length=100, verbose_name=u'Descripción')
    codigo = models.CharField(default='', max_length=10, verbose_name=u'Codigo')


    def __str__(self):
        return u'%s' % self.nombre

    def esta_activo(self):
        return True if self.hdurgencia_impacto_prioridad_set.filter(status=True).exists() else False

    class Meta:
        verbose_name = u"HdUrgencia"
        verbose_name_plural = u"HdUrgencias"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdUrgencia, self).save(*args, **kwargs)


class HdPrioridad(ModeloBase):
    codigo = models.CharField(default='', max_length=10, verbose_name=u'Codigo')
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    horamax = models.CharField(default='00', max_length=100, verbose_name=u'Hora')
    minutomax = models.CharField(default='00', max_length=100, verbose_name=u'Minutos')
    segundomax = models.CharField(default='00', max_length=100, verbose_name=u'Segundos')
    imagen = models.FileField(upload_to='Imagen/%Y/%m/%d', blank=True, null=True, verbose_name=u'Imagen')

    def __str__(self):
        return u'%s' % self.nombre

    def esta_activo(self):
        return True if self.hdurgencia_impacto_prioridad_set.filter(status=True).exists() else False

    class Meta:
        verbose_name = u"Prioridad"
        verbose_name_plural = u"Prioridad"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdPrioridad, self).save(*args, **kwargs)


class HdUrgencia_Impacto_Prioridad(ModeloBase):
    urgencia = models.ForeignKey(HdUrgencia, on_delete=models.CASCADE, verbose_name=u'Urgencia',related_name='hdurgencia')
    impacto = models.ForeignKey(HdImpacto, on_delete=models.CASCADE, verbose_name=u'Categoria',related_name='hdimpacto')
    prioridad = models.ForeignKey(HdPrioridad, on_delete=models.CASCADE, verbose_name=u'Prioridad',related_name='hdprioridad')
    modificar = models.BooleanField(default=False, verbose_name=u"Modificar")
    horamax = models.CharField(default='00', max_length=100, verbose_name=u'Hora')
    minutomax = models.CharField(default='00', max_length=100, verbose_name=u'Minutos')
    segundomax = models.CharField(default='00', max_length=100, verbose_name=u'Segundos')


    def __str__(self):
        return u'%s' % self.prioridad.nombre

    class Meta:
        verbose_name = u"Prioridad"
        verbose_name_plural = u"Prioridad"

    def esta_activo(self):
        return True if self.hddetalle_subcategoria_set.filter(status=True).exists() else False

    def save(self, *args, **kwargs):
        super(HdUrgencia_Impacto_Prioridad, self).save(*args, **kwargs)


class HdCategoria(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    tipoincidente = models.ForeignKey(HdTipoIncidente, on_delete=models.CASCADE, null=True, blank=True, verbose_name=u'Tipo de incidente',related_name='hdtipoincidente')
    orden = models.IntegerField(default=0, verbose_name=u"Orden")

    def __str__(self):
        return u'%s' % self.nombre

    def esta_activo(self):
        return True if self.hdsubcategoria_set.filter(status=True).exists() else False

    def mis_dispositivos(self):
        return self.hdsubcategoria_set.filter(status=True)

    class Meta:
        verbose_name = u"Impacto"
        verbose_name_plural = u"Impactos"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdCategoria, self).save(*args, **kwargs)


class HdMateriales(ModeloBase):
    codigo = models.CharField(max_length=100, verbose_name=u'Codigo')
    nombre = models.CharField(max_length=300, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper().strip()
        super(HdMateriales, self).save(*args, **kwargs)


class HdSubCategoria(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    categoria = models.ForeignKey(HdCategoria, on_delete=models.CASCADE, verbose_name=u'Categoria',related_name='hdcategoria')

    def __str__(self):
        return u'%s' % self.nombre

    def mis_problemas(self):
        return self.hddetalle_subcategoria_set.filter(status=True)

    def esta_activo(self):
        return True if self.hddetalle_subcategoria_set.filter(status=True) else False

    class Meta:
        verbose_name = u"Sub Categoria"
        verbose_name_plural = u"Sub Categorias"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdSubCategoria, self).save(*args, **kwargs)


class HdDetalle_SubCategoria(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    subcategoria = models.ForeignKey(HdSubCategoria, on_delete=models.CASCADE, verbose_name=u'SubCategoria',related_name='hdsubcategoria')
    prioridad = models.ForeignKey(HdUrgencia_Impacto_Prioridad, on_delete=models.CASCADE, verbose_name=u'Prioridad', blank=True, null=True,related_name='hdurgencia_impacto')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"HdDetalle_SubCategoria"
        verbose_name_plural = u"HdDetalle_SubCategoria"

    def esta_activo(self):
        return True if self.hdincidente_set.filter(status=True) else False

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdDetalle_SubCategoria, self).save(*args, **kwargs)


class HdEstado(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    imagen = models.FileField(upload_to='Imagen/%Y/%m/%d', blank=True, null=True, verbose_name=u'Imagen')

    def __str__(self):
        return u'%s' % self.nombre

    def esta_activo(self):
        return True if self.hdincidente_set.filter(status=True).exists() else False

    class Meta:
        verbose_name = u"HdEstado"
        verbose_name_plural = u"HdEstados"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdEstado, self).save(*args, **kwargs)


class HdMedioReporte(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    descripcion = models.CharField(max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Medio de Reporte"
        verbose_name_plural = u"Medios de Reportes"
        ordering = ('nombre',)
        unique_together = ('nombre',)

    def esta_activo(self):
        return True if self.hdincidente_set.filter(status=True).exists() else False

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.descripcion = self.descripcion.upper()
        super(HdMedioReporte, self).save(*args, **kwargs)

# class HdBloque(ModeloBase):
#     nombre = models.CharField(max_length=300, verbose_name=u"Nombre Bloque")
#
#     def __str__(self):
#         return u'%s' % self.nombre
#
#     def puede_eliminar_bloque(self):
#         if not self.hdbloqueubicacion_set.values("id").filter(status=True).exists():
#             return True
#         return False
#
#     class Meta:
#         verbose_name = u"Bloque"
#         verbose_name_plural = u"Bloques"
#
#     def save(self, *args, **kwargs):
#         super(HdBloque, self).save(*args, **kwargs)
#
#
# class HdUbicacion(ModeloBase):
#     nombre = models.CharField(max_length=300, verbose_name=u"Nombre Ubicación")
#
#     def __str__(self):
#         return u'%s' % self.nombre
#
#     def puede_eliminar_ubicacion(self):
#         if self.hdbloqueubicacion_set.values("id").filter(status=True).exists():
#             return True
#         else:
#             return False
#     class Meta:
#         verbose_name = u"Ubicación"
#         verbose_name_plural = u"Ubicaciones"
#
#     def save(self, *args, **kwargs):
#         super(HdUbicacion, self).save(*args, **kwargs)
#
#
# class HdBloqueUbicacion(ModeloBase):
#     bloque = models.ForeignKey(HdBloque, blank=True, null=True, verbose_name=u'Bloque')
#     ubicacion = models.ForeignKey(HdUbicacion, blank=True, null=True, verbose_name=u'Ubicación')
#
#     def __str__(self):
#         return u'%s' % self.ubicacion
#
#     def mis_ubicaciones(self):
#         if HdBloqueUbicacion.objects.filter(status=True, bloque=self.bloque).exists():
#             return HdBloqueUbicacion.objects.filter(status=True, bloque=self.bloque)
#         return []
#
#     class Meta:
#         verbose_name = u"Ubicación"
#         verbose_name_plural = u"Ubicaciones"

class HdCausas(ModeloBase):
    nombre = models.CharField(max_length=300, verbose_name=u"Nombre Causa")
    tipoincidente = models.ForeignKey(HdTipoIncidente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Tipo incidente',related_name='hdtipincidente')

    def __str__(self):
        return u'%s' % self.nombre

    def en_uso(self):
        return self.hdincidente_set.filter(status=True).exists()

    class Meta:
        verbose_name = u"Causa"
        verbose_name_plural = u"Causas"

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdCausas, self).save(*args, **kwargs)


class SecuenciaHdIncidente(ModeloBase):
    anioejercicio = models.ForeignKey(AnioEjercicio, on_delete=models.CASCADE, verbose_name=u'Anio Ejercicio',related_name='Anio')
    secuenciaincidente =  models.IntegerField(default=0, verbose_name=u'Secuencia Caja')


ESTADO_ORDEN_TRABAJO = (
    (1, u"GENERADO"),
    (2, u"CERRADO"),
    (3, u"PENDIENTE REPUESTO"),
    (4, u"TALLER PARTICULAR"),
    (5, u"EN TRÁMITE")
)

class OrdenTrabajo(ModeloBase):
    codigoorden = models.CharField(default='', max_length=250, null=True, blank=True, verbose_name=u'codigo orden de trabajo')
    informe = models.TextField(blank=True, null=True, verbose_name=u'Repuestos')
    estado = models.IntegerField(choices=ESTADO_ORDEN_TRABAJO, default=1, verbose_name=u'Estado Orden Trabajo')
    calificacion = models.FloatField(blank=True, null=True, verbose_name=u'calificacion solicitante')
    archivo = models.FileField(upload_to='OrdenTrabajo/%Y/%m/%d', blank=True, null=True, verbose_name=u'Informe')

    def __str__(self):
        return u'%s' % self.codigoorden

    def en_uso(self):
        return self.hdincidente_set.filter(status=True).exists()

    def download_link(self):
        return self.archivo.url

    class Meta:
        verbose_name = u"Orden Trabajo"
        verbose_name_plural = u"Ordenes Trabajo"
        unique_together = ('codigoorden',)

    def save(self, *args, **kwargs):
        self.codigoorden = self.codigoorden.upper()
        super(OrdenTrabajo, self).save(*args, **kwargs)


class DetalleOrdenTrabajo(ModeloBase):
    orden = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Orden Trabajo',related_name='hdorden')
    repuesto = models.TextField(blank=True, null=True, verbose_name=u'Repuestos')
    cantidad = models.CharField(default='', max_length=250, verbose_name=u'Cantidad')

    def __str__(self):
        return u'%s' % self.orden

    class Meta:
        verbose_name = u"Detalle Orden Trabajo"
        verbose_name_plural = u"Detalle Ordenes Trabajo"

    def save(self, *args, **kwargs):
        self.repuesto = self.repuesto.upper()
        super(DetalleOrdenTrabajo, self).save(*args, **kwargs)


class ActivosSinCodigo(ModeloBase):
    codigointerno = models.CharField(default='', blank=True, null=True, max_length=20, verbose_name=u"Código Interno")
    fechaingreso = models.DateField(blank=True, null=True, verbose_name=u"Fecha Ingreso")
    observacion = models.TextField(default='', max_length=250, blank=True, null=True, verbose_name=u"Observación")
    costo = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Costo")
    serie = models.CharField(default='', max_length=100, verbose_name=u"Serie")
    descripcion = models.CharField(default='', max_length=250, blank=True, null=True, verbose_name=u"Descripción")
    modelo = models.CharField(default='', max_length=100, verbose_name=u"Modelo")
    marca = models.CharField(default='', max_length=300, verbose_name=u"Marca")
    estado = models.ForeignKey(EstadoProducto, on_delete=models.CASCADE, verbose_name=u"Estado activo",default='')
    responsable = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, related_name='responsableactivo_set', verbose_name=u"Usuario", blank=True, null=True)
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.CASCADE, verbose_name=u"Ubicación", related_name='Ubicacion_set', blank=True, null=True)


    def __str__(self):
        return u"Cod.Inv. %s - %s"  % (self.codigointerno, self.descripcion)

    def flexbox_reprhd(self):
        return u"Cod.Inv. %s - %s" % (self.codigointerno, self.descripcion)
    class Meta:
        verbose_name = u"nombre"
        verbose_name_plural = u"nombres"

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(ActivosSinCodigo, self).save(*args, **kwargs)


class HdIncidente(ModeloBase):
    asunto = models.CharField(max_length=500, verbose_name=u'Asunto')
    persona = models.ForeignKey('sga.Persona', blank=True, on_delete=models.CASCADE, null=True,related_name='hdpersona_set', verbose_name=u'Solicitante')
    departamento = models.ForeignKey(Departamento,blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Departamento',related_name='hddepartamento')
    descripcion = models.TextField(blank=True, null=True, verbose_name=u'Descripción')
    subcategoria = models.ForeignKey(HdSubCategoria, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Sub categoria',related_name='hdsubcat')
    detallesubcategoria = models.ForeignKey(HdDetalle_SubCategoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Detalle',related_name='hddetallesub')
    activo = models.ForeignKey(ActivoFijo, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Activo',related_name='hdActivo')
    fechareporte = models.DateField(verbose_name=u"Fecha de reporte")
    horareporte = models.TimeField(verbose_name=u"hora de reporte")
    medioreporte = models.ForeignKey(HdMedioReporte, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Medio de reporte',related_name='hdmedioreporte')
    director = models.ForeignKey('sga.Persona', blank=True, on_delete=models.CASCADE, null=True,related_name='hd_director_set', verbose_name=u'Director')
    archivo = models.FileField(upload_to='Archivo/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    estado = models.ForeignKey(HdEstado, verbose_name=u'Estado' , on_delete=models.CASCADE)
    tipoincidente = models.ForeignKey(HdTipoIncidente, on_delete=models.CASCADE, null=True, blank=True, verbose_name=u'Tipo de incidente',related_name='htipoincidente')
    # tipo = models.BooleanField(default=False, verbose_name=u'Estado de envio')
    ubicacion = models.ForeignKey(HdBloqueUbicacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Ubicacion',related_name='hdubica')
    causa = models.ForeignKey(HdCausas, blank=True, null=True, verbose_name=u'Causa',related_name='hdcausa', on_delete=models.CASCADE)
    responsableactivofijo = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, related_name='hdresponsableactivofijo', verbose_name=u"Usuario", blank=True, null=True)
    realizoencuesta = models.BooleanField(default=False, verbose_name=u'Realizo Encuesta')
    revisionequipoexterno = models.BooleanField(default=False, verbose_name=u'Revisión de equipo personal que realiza gestión institucional')
    revisionequiposincodigo = models.BooleanField(default=False, verbose_name=u'Revisión de equipo institucional sin código de barra o sin registro de sistema interno')
    serie = models.CharField(default='', max_length=250, verbose_name=u'Serie o código')
    ordentrabajo = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Ubicacion')
    tercerapersona = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, blank=True, null=True, related_name='hdtercerapersona_set', verbose_name=u'Tercera Persona')
    tipousuario = models.IntegerField(choices=TIPO_USUARIO, default=1, verbose_name=u'Tipo usuario')
    concodigo = models.BooleanField(default=False, verbose_name=u'Con Código')
    activosincodigo = models.ForeignKey(ActivosSinCodigo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Activo Sin Codigo',related_name='hdactivosincodigo')
    aprobarmaterial = models.BooleanField(default=False, verbose_name=u'Aprobar Material')
    observacion = models.TextField(default='', verbose_name=u'Observación')

    def __str__(self):
        return u'%s' % self.asunto

    class Meta:
        verbose_name = u"Incidente"
        verbose_name_plural = u"Incidentes"

    def download_link(self):
        return self.archivo.url

    def turno(self):
        count, puesto, total = 0, None, HdIncidente.objects.values('id').filter(status=True, estado__id__in=[1, 2]).order_by('id').all()
        if HdIncidente.objects.values('id').filter(status=True, estado__id__in=[1, 2], persona=self.persona, id=self.id).exists():
            puesto = HdIncidente.objects.get(status=True, estado__id__in=[1, 2], persona=self.persona, id=self.id)

        for t in total:
            if t['id'] == puesto.id:
                return count + 1
            count += 1
        return False

    def tiene_detalle(self):
        return True if self.h_d_incidentes.filter(status=True).exists() else False

    def mi_detalle(self):
        return self.h_d_incidentes.filter(status=True).order_by('-id')

    def mi_detallepersona(self,persona):
        return self.h_d_incidentes.filter(agente__persona_id=persona, status=True).exclude(estadoasignacion=3).order_by('-id')

    def tiene_prioridad(self):
        return True if self.detallesubcategoria.prioridad else False

    def es_critica(self):
        return True if self.detallesubcategoria.prioridad.prioridad.codigo=='1' else False

    def es_alta(self):
        return True if self.detallesubcategoria.prioridad.prioridad.codigo=='2' else False

    def es_media(self):
        return True if self.detallesubcategoria.prioridad.prioridad.codigo=='3' else False

    def es_baja(self):
        return True if self.detallesubcategoria.prioridad.prioridad.codigo=='4' else False

    def esta_abierto(self):
        return True if self.estado_id == 1 else False

    def esta_pendiente(self):
        return True if self.estado_id == 2 else False

    def esta_resulto(self):
        return True if self.estado_id == 3 else False

    def esta_cerrado(self):
        return True if self.estado_id == 4 else False

    def ultimo_agente_asignado(self):
        if self.h_d_incidentes.filter(status=True).exists():
            return self.mi_detalle()[0].agente
        else:
            return None

        # if self.h_d_incidentes.all().exists():
        #     return self.mi_detalle()[0].agente
        # else:
        #     return None

    def ultimo_registro(self):
        if self.h_d_incidentes.filter(status=True).exists():
            return self.mi_detalle().order_by('-id')[0]
        else:
            return None

        # if self.h_d_incidentes.all().exists():
        #     return self.mi_detalle().order_by('-id')[0]
        # else:
        #     return None

    def ultimo_registropersona(self, persona):
        if self.h_d_incidentes.filter(agente__persona_id=persona, status=True).exclude(estadoasignacion=3).exists():
            return self.mi_detallepersona(persona)
        else:
            return None

    def puede_eliminar(self):
        if self.h_d_incidentes.filter(status=True).exists():
            if self.h_d_incidentes.filter(status=True).count()==1:
                return True
            else:
                return False
        return True


    def mi_grupo(self,persona):
        if self.h_d_incidentes.all().exists():
            if self.ultimo_registro().grupo:
                if self.ultimo_registro().grupo.hddetalle_grupo_set.filter(persona_id=persona).exists():
                    return True
                else:
                    return False
            return False
        return False

    def es_mi_grupo(self,persona):
        agente = HdDetalle_Grupo.objects.filter(persona_id=persona, status=True).first()
        if agente:
            # if HdIncidente.objects.filter(Q(pk=self.id),(Q(tipoincidente=agente.grupo.tipoincidente)| Q(hddetalle_incidente__agente__grupo=agente.grupo)),status=True).exclude(estado=3).exists():
            return HdIncidente.objects.values('id').filter(Q(pk=self.id), Q(tipoincidente=agente.grupo.tipoincidente),status=True).exclude(estado=3).exists()

    def es_mi_agente(self,persona):
        agente = HdDetalle_Grupo.objects.filter(persona_id=persona, status=True).first()
        if agente:
            if self.h_d_incidentes.filter(status=True).exists():
                if self.ultimo_registro().agente:
                    if (self.ultimo_registro().agente == agente and self.ultimo_registro().estadoasignacion == 1) or (self.ultimo_registro().estadoasignacion == 2 or self.ultimo_registro().estadoasignacion == 3):
                        return True
                    else:
                        return False
                elif self.es_mi_grupo(persona):
                    return  True
            return True

    def mi_agente(self, persona):
        if self.h_d_incidentes.all().exists():
            if self.ultimo_registro().agente:
                if self.ultimo_registro().agente.persona_id==persona:
                    return True
                else:
                    return False
            return False
        return False

    def es_agente_tic(self, persona):
        if HdDetalle_Grupo.objects.filter(persona_id=persona, status=True).exists():
            agente = HdDetalle_Grupo.objects.filter(persona_id=persona, status=True)[0]
            if agente.grupo.tipoincidente_id == 2:
                return True
        return False

    def agente(self, persona):
        if self.h_d_incidentes.filter(status=True, agente__persona__id=persona).exists():
            return self.h_d_incidentes.filter(status=True, agente__persona__id=persona)[0]
        return None

    def cantidad_detalle_incidente(self):
        return self.h_d_incidentes.filter(status=True).count()

    def email_notificacion_tic(self, nombresistema):
        from sga.tasks import send_html_mail
        from sga.models import miinstitucion
        lista = ['tic@unemi.edu.ec']
        asunto = "HelpDesk: Nuevo Incidente #"+ str(self.id)
        send_html_mail(asunto, "emails/notificarnuevoincidentehelpdesk.html",
                       {'sistema': nombresistema, 'incidente': self, 't': miinstitucion(),'fecha': datetime.now().date()},
                       lista, [], cuenta=CUENTAS_CORREOS[4][1])

    def email_notificacion_mantenimiento(self):
        from sga.tasks import send_html_mail
        from sga.models import miinstitucion
        lista = ['mguerreroc@unemi.edu.ec','jsoriac@unemi.edu.ec','kbritol@unemi.edu.ec']
        asunto = "HelpDesk: Nuevo Incidente #"+ str(self.id)
        send_html_mail(asunto, "emails/notificarnuevoincidentehelpdesk.html",
                       {'sistema': 'Sagest', 'incidente': self, 't': miinstitucion(),'fecha': datetime.now().date()},
                       lista, [], cuenta=CUENTAS_CORREOS[4][1])

    def email_notificacion_equipo_sin_codigo(self, nombresistema):
        # departamento = Departamento.objects.get()
        detalle = self.h_d_incidentes.filter(status=True).order_by('-id')[0]
        from sga.tasks import send_html_mail
        from sga.models import miinstitucion
        lista = ['bbarco@unemi.edu.ec', 'helpdesk-novedades@unemi.edu.ec', detalle.agente.persona.emailinst]
        asunto = "HelpDesk: Nuevo incidente sin codigo barra, interno # cod.: "+ str(self.id)
        send_html_mail(asunto, "emails/notificar_incidente_sincodigo.html",
                       {'sistema': nombresistema, 'incidente': self, 'agente':detalle.agente.persona.nombre_completo_inverso(), 't': miinstitucion(),'fecha': datetime.now().date()},
                       lista, [], cuenta=CUENTAS_CORREOS[4][1])

    def cantidad_pendientes(self):
        return len(HdIncidente.objects.values('id').filter(status=True, estado__id__in=[1, 2]).order_by('id').all())

    def implementa_producto(self):
        return HdIncidenteProductoDetalle.objects.values('id').filter(status=True, incidente_id=self.id).exists()

    def productos_utilizados(self):
        if HdIncidenteProductoDetalle.objects.values('id').filter(status=True, incidente=self).exists():
            return HdIncidenteProductoDetalle.objects.filter(status=True, incidente=self).order_by('id')
        return None

    def software_instalado(self, ids):
        if self.productos_utilizados():
            return self.productos_utilizados().filter(producto_id__in=ids).exists()
        else:
            return False

    # def email_notificacion_escalar(self, nombresistema, incidente):
    #     from sga.tasks import send_html_mail
    #     from sga.models import miinstitucion
    #     lista = []
    #
    #     for agente in self.grupo.mis_agentes():
    #         lista.append(agente.persona.lista_emails_interno())
    #     #Notificar al grupo de incidente escalado
    #     send_html_mail("HelpDesk: Incidente escalado #"+ str(self.id),
    #                    "emails/notificarincidenteescaladohelpdesk.html",
    #                    {'sistema': nombresistema, 'detalle': self, 't': miinstitucion(), 'dedetalle': dedetalle, 'fecha': datetime.now().date()}, lista,[],
    #                    cuenta=CUENTAS_CORREOS[4][1])

    # def puede_eliminar(self):
    #     return True if self.hddetalle_incidente_set.all().count()==1 and self.estado == 1  and self.ultimo_registro().estadoasignacion == 1 else False

    def save(self, *args, **kwargs):
        self.asunto = self.asunto.upper()
        if self.descripcion:
            self.descripcion = self.descripcion.upper()
        super(HdIncidente, self).save(*args, **kwargs)


class HdProceso(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Proceso de Incidente"
        verbose_name_plural = u"Proceso de incidente"
        ordering = ('nombre',)
        unique_together = ('nombre',)

    def esta_activo(self):
        return True if self.hdestado_proceso_set.all().exists() else False

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdProceso, self).save(*args, **kwargs)

class HdEstado_Proceso(ModeloBase):
    nombre = models.CharField(max_length=250, verbose_name=u"Nombre")
    proceso = models.ForeignKey(HdProceso, on_delete=models.CASCADE, verbose_name=u'Proceso')
    detalle = models.CharField(default='',max_length=500, verbose_name=u"Detalle")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Estado del proceso de Incidente"
        verbose_name_plural = u"Estado del proceso de Incidentes"
        ordering = ('nombre',)
        unique_together = ('nombre',)

    def esta_activo(self):
        return True if HdDetalle_Incidente.objects.filter(estadoproceso=self).exists() else False

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(HdEstado_Proceso, self).save(*args, **kwargs)

class HdDetalle_Incidente(ModeloBase):
    incidente = models.ForeignKey(HdIncidente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Incidente',related_name='h_d_incidentes')
    agente = models.ForeignKey(HdDetalle_Grupo,  on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Agente',related_name='hd_agente')
    responsable = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, blank=True, null=True, related_name='hdresponsable_set', verbose_name=u'Responsable Grupo')
    grupo = models.ForeignKey(HdGrupo, related_name=u'hdGrupo',  on_delete=models.CASCADE,)
    resolucion = models.TextField(blank=True, null=True, verbose_name=u'Resolución')
    fecharesolucion = models.DateField(blank=True, null=True, verbose_name=u"Fecha Resolucion")
    horaresolucion = models.TimeField(blank=True, null=True, verbose_name=u"hora de reporte")
    estadoasignacion = models.IntegerField(choices=ESTADO_DETALLE_INCIDENTE, blank=True, null=True,verbose_name=u'Estado de Asignación')
    estadoproceso = models.ForeignKey(HdEstado_Proceso, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Estado de Proceso',related_name='hd_estado_proceso')
    estado = models.ForeignKey(HdEstado, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Estado',related_name='hd_estado')

    def __str__(self):
        return u'%s' % self.incidente

    class Meta:
        verbose_name = u"Detalle de Incidente"
        verbose_name_plural = u"Detalle de Incidentes"

    def es_asignado(self):
        return True if self.estadoasignacion == 1 else False

    def es_reasingnado(self):
        return True if self.estadoasignacion == 2 else False

    def es_escalamiento(self):
        return True if self.estadoasignacion == 3 else False

    def mi_grupo(self,persona):
        if self.grupo:
            return True if self.grupo.hddetalle_grupo_set.filter(persona_id=persona).exists() else False
        return None

    def mis_ayudantes(self):
        return self.hddetalle_incidente_ayudantes_set.filter(status=True)

    def mi_agente(self):
        return self.agente.persona_id if self.agente else None

    def email_notificacion_agente(self, nombresistema):
        from sga.tasks import send_html_mail
        from sga.models import miinstitucion
        #Notificar al agente que se a asignado un nuevo incidente
        if self.agente:

            send_html_mail("HelpDesk: Incidente Asignado #"+ str(self.incidente_id),
                           "emails/notificarincidenteasignadohelpdesk.html",
                           # {'sistema': nombresistema, 'detalle': self, 't': miinstitucion(), 'fecha': datetime.now().date()}, self.agente.persona.lista_emails_interno(),[],
                           {'sistema': nombresistema, 'detalle': self, 't': miinstitucion(), 'fecha': datetime.now().date()}, self.agente.persona.lista_emails_interno(),[],
                           cuenta=CUENTAS_CORREOS[4][1])

            if self.incidente.persona:
                send_html_mail("HelpDesk: Incidente Asignado #" + str(self.incidente_id),
                               "emails/notificarincidenteasignadohelpdesksolicitante.html",
                               # {'sistema': nombresistema, 'detalle': self, 't': miinstitucion(), 'fecha': datetime.now().date()}, self.agente.persona.lista_emails_interno(),[],
                               {'sistema': nombresistema, 'detalle': self, 't': miinstitucion(),
                                'fecha': datetime.now().date()}, self.incidente.persona.lista_emails_interno(), [],
                               cuenta=CUENTAS_CORREOS[4][1])
            # else:
            #     lista = []
            #     for agente in self.grupo.mis_agentes():
            #         lista.append(agente.persona.lista_emails_interno())
            #         send_html_mail("Nuevo Incidente Reasignado",
            #                        "emails/notificarincidenteescaladohelpdesk.html",
            #                        {'sistema': nombresistema, 'detalle': self, 't': miinstitucion()},lista, [],cuenta=CUENTAS_CORREOS[4][1])

    def email_notificacion_agente_reasignado(self, nombresistema, deagente):
        from sga.tasks import send_html_mail
        from sga.models import miinstitucion
        #Notificar al agente que se a asignado un nuevo incidente
        lista = ['bbarcom@unemi.edu.ec',self.agente.persona.lista_emails_interno()]
        send_html_mail("HelpDesk: Incidente Reasignado #"+ str(self.id),
                       "emails/notificarincidentereasignadohelpdesk.html",
                       {'sistema': nombresistema, 'detalle': self, 't': miinstitucion(), 'deagente':deagente, 'fecha': datetime.now().date()}, lista,[],
                       cuenta=CUENTAS_CORREOS[4][1])

    def email_notificacion_escalar(self, nombresistema, dedetalle):
        from sga.tasks import send_html_mail
        from sga.models import miinstitucion
        lista = ['bbarcom@unemi.edu.ec']
        for agente in self.grupo.mis_agentes():
            lista.append(agente.persona.lista_emails_interno())
        #Notificar al grupo de incidente escalado
        send_html_mail("HelpDesk: Incidente escalado #"+ str(self.id),
                       "emails/notificarincidenteescaladohelpdesk.html",
                       {'sistema': nombresistema, 'detalle': self, 't': miinstitucion(), 'dedetalle': dedetalle, 'fecha': datetime.now().date()}, lista,[],
                       cuenta=CUENTAS_CORREOS[4][1])

    def save(self, *args, **kwargs):
        super(HdDetalle_Incidente, self).save(*args, **kwargs)


class HdDetalle_Incidente_Ayudantes(ModeloBase):
    detallleincidente = models.ForeignKey(HdDetalle_Incidente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Detalle Incidente')
    agente = models.ForeignKey(HdDetalle_Grupo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Agente')

    def __str__(self):
        return u'%s' % self.detallleincidente

    def save(self, *args, **kwargs):
        super(HdDetalle_Incidente_Ayudantes, self).save(*args, **kwargs)


class HdPiezaPartes(ModeloBase):
    descripcion = models.CharField(max_length=300, verbose_name=u'Descripción')
    estado = models.IntegerField(default=1, choices=ESTADO_PARTES, verbose_name=u'Estado')
    imagen = models.FileField(upload_to='piezapartes/%Y/%m/%d', blank=True, null=True, verbose_name=u'imagen')
    grupocategoria = models.ForeignKey("helpdesk.HdGruposCategoria", blank=True, null=True, verbose_name=u"Grupo Categoria", on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.descripcion

    def en_uso(self):
        return self.hdsolicitudespiezapartes_set.exists()

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(HdPiezaPartes, self).save(*args, **kwargs)


class HdSolicitudesPiezaPartes(ModeloBase):
    piezaparte = models.ForeignKey(HdPiezaPartes, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"pieza y parte")
    grupocategoria = models.ForeignKey(GruposCategoria, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Grupo Categoria",related_name='GrupoCategorias')
    tipo = models.CharField(default='', max_length=300, verbose_name=u'Tipo')
    capacidad = models.CharField(default='', max_length=300, verbose_name=u'Capacidad')
    velocidad = models.CharField(default='', max_length=300, verbose_name=u'Velocidad')
    descripcion = models.TextField(blank=True, null=True, verbose_name=u'Descripción')

    def __str__(self):
        return u"%s - %s - %s - %s - %s" % (self.grupocategoria, self.piezaparte, self.tipo, self.capacidad, self.velocidad)

    def en_uso(self):
        return self.hdrequerimientospiezapartes_set.exists()

    def precioactivo(self):
        if self.hdpreciosolicitudespiezapartes_set.filter(cierresolicitudes__estado=False,cierresolicitudes__activo=True,activo=True,status=True).exists():
            return self.hdpreciosolicitudespiezapartes_set.filter(cierresolicitudes__estado=False,cierresolicitudes__activo=True,activo=True,status=True)[0].valor
        else:
            return None

    def save(self, *args, **kwargs):
        self.tipo = self.tipo.upper()
        self.capacidad = self.capacidad.upper()
        self.velocidad = self.velocidad.upper()
        self.descripcion = self.descripcion.upper()
        super(HdSolicitudesPiezaPartes, self).save(*args, **kwargs)


class HdFechacierresolicitudes(ModeloBase):
    from django.contrib.auth.models import User
    observacion = models.TextField(verbose_name=u"Observacion")
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha inicio')
    fechafin = models.DateField(blank=True, null=True, verbose_name=u'Fecha fin')
    activo = models.BooleanField(default=False, verbose_name=u'Activo')
    estado = models.BooleanField(default=True, verbose_name=u'Activo')
    usuariocierre = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Usuario resuelve',related_name='hduser')
    fecha_cierre = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return u"%s  (FECHA INI. %s - FECHA FIN. %s )" % (self.observacion,self.fechainicio,self.fechafin)

    def en_uso(self):
        return self.hdpreciosolicitudespiezapartes_set.exists()

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        super(HdFechacierresolicitudes, self).save(*args, **kwargs)


class HdPrecioSolicitudesPiezaPartes(ModeloBase):
    solicitudes = models.ForeignKey(HdSolicitudesPiezaPartes, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Solicitudes de piezas y partes")
    cierresolicitudes = models.ForeignKey(HdFechacierresolicitudes, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Fechas cierres Solicitudes de piezas y partes")
    valor = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Precio Referencial")
    activo = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % self.valor

    def en_uso(self):
        return self.hdrequerimientospiezapartes_set.exists()

    def si_edita(self):
        return self.cierresolicitudes.estado


class HdRequerimientosPiezaPartes(ModeloBase):
    from django.contrib.auth.models import User
    incidente = models.ForeignKey(HdIncidente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Incidentes",related_name='hd_incidentes')
    solicitudes = models.ForeignKey(HdSolicitudesPiezaPartes, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Solicitudes de piezas y partes")
    usuarioresuelve = models.ForeignKey(User, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Usuario resuelve',related_name='hd_usarioresuelve')
    fecharesuelve = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha resuelve')
    observacionresuelve = models.CharField(default='', max_length=300, verbose_name=u'Observación de pieza y parte puesta')
    codigoresuelve = models.CharField(default='', max_length=300, verbose_name=u'Codigo de pieza y parte puesta')
    preciosolicitud = models.ForeignKey(HdPrecioSolicitudesPiezaPartes, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Precio Solicitudes de piezas y partes")

    def __str__(self):
        return u"%s - %s" % (self.incidente, self.solicitudes)

    def save(self, *args, **kwargs):
        self.observacionresuelve = self.observacionresuelve.upper()
        self.codigoresuelve = self.codigoresuelve.upper()
        super(HdRequerimientosPiezaPartes, self).save(*args, **kwargs)


class HdMaterial_Incidente(ModeloBase):
    incidente = models.ForeignKey(HdIncidente, on_delete=models.CASCADE,  blank=True, null=True, verbose_name=u'Incidente')
    material = models.ForeignKey(HdMateriales,on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Material')
    cantidad = models.IntegerField(default=0)
    unidadmedida = models.ForeignKey(UnidadMedidaPresupuesto, on_delete=models.CASCADE, blank=True, null=True)


    def __str__(self):
        return u'%s' % self.material

    def save(self, *args, **kwargs):
        super(HdMaterial_Incidente, self).save(*args, **kwargs)


class HdCabRespuestaEncuestas(ModeloBase):
    incidente = models.ForeignKey(HdIncidente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Incidente")
    fecha_encuesta = models.DateTimeField(blank=True, null=True)
    mantenimientoexterno = models.BooleanField(default=True, verbose_name=u"mantenimiento externo")

    def __str__(self):
        return u'%s' % self.incidente

    class Meta:
        verbose_name = u"Cabecera Respuesta Encuesta de incidente"
        verbose_name_plural = u"Cabeceras Respuestas Encuestas de Incidentes"

    def save(self, *args, **kwargs):
        super(HdCabRespuestaEncuestas, self).save(*args, **kwargs)


class HdRespuestaEncuestas(ModeloBase):
    cabrespuesta = models.ForeignKey(HdCabRespuestaEncuestas,  on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Cab Respuesta",related_name='hdrespuestencuesta')
    detencuesta = models.ForeignKey(HdDetEncuestas, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Pregunta Encuesta",related_name='hddetencuesta')
    respuesta = models.ForeignKey('sga.Respuesta', on_delete=models.CASCADE, verbose_name=u'Respuesta',related_name='hdrespuesta')
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u"Observaciones")

    def __str__(self):
        return u'%s' % self.cabrespuesta

    class Meta:
        verbose_name = u"Respuesta Encuesta de incidente"
        verbose_name_plural = u"Respuestas Encuestas de Incidentes"

    def save(self, *args, **kwargs):
        self.observaciones = self.observaciones.upper()
        super(HdRespuestaEncuestas, self).save(*args, **kwargs)


class HdGrupoSistemaEquipo(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripción')

    def __str__(self):
        return u'%s' % self.descripcion
    class Meta:
        verbose_name = u"HdGrupoSistemaEquipo"
        verbose_name_plural = u"HdGrupoSistemaEquipos"

    def flexbox_reprhd(self):
        return u" %s" % (self.descripcion)

    def save(self, *args, **kwargs):

        self.descripcion  = self.descripcion.upper()
        super(HdGrupoSistemaEquipo, self).save(*args, **kwargs)


class HdBien(ModeloBase):
    ubicacion =  models.ForeignKey(HdBloqueUbicacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Ubicacion')
    gruposistema = models.ForeignKey(HdGrupoSistemaEquipo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'GrupoSistema')
    sistemaequipo = models.TextField(default='', verbose_name=u'Descripcion')
    cantidad = models.IntegerField(default=0, verbose_name=u"Cantidad")
    observacion = models.TextField(default='', verbose_name=u'Observacion')

    def __str__(self):
        return u'%s' % self.sistemaequipo

    class Meta:
        verbose_name = u"HdBien"
        verbose_name_plural = u"HdBien"

    def flexbox_reprhd(self):
        return u" %s" % (self.sistemaequipo)
    def save(self, *args, **kwargs):
        self.sistemaequipo = self.sistemaequipo.upper()
        self.observacion  = self.observacion.upper()
        super(HdBien, self).save(*args, **kwargs)


class HdReparacion(ModeloBase):
    ubicacion =  models.ForeignKey(HdBloqueUbicacion, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Ubicacion')
    gruposistema = models.ForeignKey(HdGrupoSistemaEquipo, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'GrupoSistema')



    def __str__(self):
        return u'%s' % self.ubicacion

    class Meta:
        verbose_name = u"HdReparacion"
        verbose_name_plural = u"HdReparaciond"

    def save(self, *args, **kwargs):

        super(HdReparacion, self).save(*args, **kwargs)


class HdDetalle_Reparacion(ModeloBase):
    reparacion = models.ForeignKey(HdReparacion, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'HdReparacion')
    bien = models.ForeignKey(HdBien, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Bien')
    cantidad = models.IntegerField(default=0)
    descripcion = models.TextField(default='', verbose_name=u'Descripción')



    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        super(HdDetalle_Reparacion, self).save(*args, **kwargs)

TIPO_BIEN = (
    (1, u'BIEN'),
    (2, u'SERVICIO'),
)
PROCESO = (
    (1, u'INTERNO'),
    (2, u'EXTERNO'),
)
TIPO_MANTENIMIENTO = (
    (1, u'PREVENTIVO-GARANTÍA'),
    (2, u'CORRECTIVO-GARANTÍA'),
    (3, u'PREVENTIVO INTERNO'),
    (4, u'CORRECTIVO INTERNO'),
)


class HdMaterialMantenimiento(ModeloBase):
    ubicacion =  models.ForeignKey(HdBloqueUbicacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Ubicacion')
    gruposistema = models.ForeignKey(HdGrupoSistemaEquipo, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'GrupoSistema')
    bien = models.ForeignKey(HdBien, blank=True, null=True, on_delete=models.CASCADE, verbose_name=u'Bien')
    tipobien = models.IntegerField(default=1, choices=TIPO_BIEN, verbose_name=u'Tipo Bien')
    proceso = models.IntegerField(default=1, choices=PROCESO, verbose_name=u'Proceso')
    tipomantenimiento = models.IntegerField(default=1, choices=TIPO_MANTENIMIENTO, verbose_name=u'Tipo Mantenimiento')



    def __str__(self):
        return u'%s' % self.ubicacion

    class Meta:
        verbose_name = u"HdMaterialMantenimiento"
        verbose_name_plural = u"HdMaterialMantenimientos"

    def save(self, *args, **kwargs):
        super(HdMaterialMantenimiento, self).save(*args, **kwargs)


class HdMaterialMantenimiento_Responsable(ModeloBase):
    materialmantenimiento = models.ForeignKey(HdMaterialMantenimiento, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Material Mantenimiento')
    agente = models.ForeignKey(HdDetalle_Grupo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Agente')

    def __str__(self):
        return u'%s' % self.materialmantenimiento

    def save(self, *args, **kwargs):
        super(HdMaterialMantenimiento_Responsable, self).save(*args, **kwargs)


class HdMaterialMantenimiento_Material(ModeloBase):
    materialmantenimiento = models.ForeignKey(HdMaterialMantenimiento, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Material Mantenimiento')
    material = models.TextField(default='', verbose_name=u'Insumo/Material/Repuesto')
    cantidad = models.IntegerField(default=0)
    precio = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Precio")
    total = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Total")
    unidadmedida = models.ForeignKey(UnidadMedidaPresupuesto, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return u'%s' % self.materialmantenimiento

    def save(self, *args, **kwargs):
        super(HdMaterialMantenimiento_Material, self).save(*args, **kwargs)


class HdPresupuestoRecurso(ModeloBase):
    gruposistema = models.ForeignKey(HdGrupoSistemaEquipo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'GrupoSistema')
    bien = models.ForeignKey(HdBien, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Bien')
    presupuestoreq = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Presupuesto Requerido")
    presupuestoiva = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Presupuesto mas iva")
    presupuestototal = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"PresupuestoTotal")


    def __str__(self):
        return u'%s' % self.gruposistema

    def save(self, *args, **kwargs):
        super(HdPresupuestoRecurso, self).save(*args, **kwargs)


DURACION = (
    (1, u'AÑO'),
    (2, u'MESES'),
    (3, u'SEMANAS'),
    (4, u'DIAS'),
    (5, u'HORAS'),
)


class HdConfFrecuencia(ModeloBase):
    duracion = models.IntegerField(default=1, choices=DURACION, verbose_name=u'Duracion')
    cantidad = models.IntegerField(default=0)

    def __str__(self):
        return u'%s %s ' % (self.cantidad,self.get_duracion_display())
    def flexbox_reprhd(self):
        return u" %s" % (self.get_duracion_display())
    def save(self, *args, **kwargs):
        super(HdConfFrecuencia, self).save(*args, **kwargs)


class HdFrecuencia(ModeloBase):
    gruposistema = models.ForeignKey(HdGrupoSistemaEquipo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'GrupoSistema')
    bien = models.ForeignKey(HdBien, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Bien')
    tipomantenimiento = models.IntegerField(default=1, choices=TIPO_MANTENIMIENTO, verbose_name=u'Tipo Mantenimiento')
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')
    frecuencia = models.ForeignKey(HdConfFrecuencia, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Frecuencia')
    consideracion = models.TextField(default='', verbose_name=u'Consideracion')
    proceso = models.IntegerField(default=1, choices=PROCESO, verbose_name=u'Proceso')


    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        super(HdFrecuencia, self).save(*args, **kwargs)


class HdCronogramaMantenimiento(ModeloBase):
    gruposistema = models.ForeignKey(HdGrupoSistemaEquipo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'GrupoSistema')
    tipomantenimiento = models.IntegerField(default=1, choices=TIPO_MANTENIMIENTO, verbose_name=u'Tipo Mantenimiento')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Proveedor')
    desde = models.DateField(blank=True, null=True, verbose_name=u"Fecha desde")
    hasta = models.DateField(blank=True, null=True, verbose_name=u"Fecha hasta")
    def __str__(self):
        return u'%s' % self.tipomantenimiento

    class Meta:
        verbose_name = u"HdCronogramaMantenimiento"
        verbose_name_plural = u"HdCronogramaMantenimiento"

    def save(self, *args, **kwargs):
        super(HdCronogramaMantenimiento, self).save(*args, **kwargs)


class HdDetCronogramaMantenimiento(ModeloBase):
    cronograma = models.ForeignKey(HdCronogramaMantenimiento, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Cronograma Mantenimiento')
    bien = models.ForeignKey(HdBien, blank=True, on_delete=models.CASCADE, null=True, verbose_name=u'Bien')
    ubicacion =  models.ForeignKey(HdBloqueUbicacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Ubicacion')
    inventario = models.DecimalField(max_digits=30, decimal_places=2, default=0,verbose_name=u"Inventario")
    mes = models.IntegerField(default=1, choices=MONTH_CHOICES, verbose_name=u'Meses')
    descripcion = models.TextField(default='', verbose_name=u'Descripcion del Trabajo')
    cantidad = models.IntegerField(default=0)

    def __str__(self):
        return u'%s' % self.cronograma

    class Meta:
        verbose_name = u"HdDetCronogramaMantenimiento"
        verbose_name_plural = u"HdDetCronogramaMantenimientos"

    def save(self, *args, **kwargs):
        super(HdDetCronogramaMantenimiento, self).save(*args, **kwargs)

class HdDetMantenimientosActivos(ModeloBase):
    cronograma = models.ForeignKey(HdCronogramaMantenimiento, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Cronograma Mantenimiento')
    activotecno = models.ForeignKey("sagest.ActivoTecnologico", verbose_name=u"Activo fijo", on_delete=models.CASCADE)
    # tipoactivo = models.ForeignKey("sagest.GruposCategoria", verbose_name=u"Activo fijo", on_delete=models.CASCADE)
    tipoactivoc = models.ForeignKey("helpdesk.HdGruposCategoria", verbose_name=u"Activo fijo",null=True, blank=True, on_delete=models.CASCADE)
    estusu = models.BooleanField(default=False, verbose_name=u'Usuario entrega el equipo')
    archivo = models.FileField(upload_to='activosgarantia/%Y/%m/%d', blank=True, null=True, verbose_name=u'Activos garantía')
    fecha = models.DateField(verbose_name=u'Fecha de mantenimiento')
    horamax = models.CharField(default='00', blank=True, null=True, max_length=100, verbose_name=u'Hora')
    minutomax = models.CharField(default='00', blank=True, null=True, max_length=100, verbose_name=u'Minutos')
    funcionarecibe = models.BooleanField(default=False, verbose_name=u'funcionamiento de equipo')
    funcionaentrega = models.BooleanField(default=False, verbose_name=u'funcionamiento de equipo entrega')
    marca = models.CharField(default='', max_length=250, verbose_name=u"Marca")
    modelo = models.CharField(default='', max_length=250, verbose_name=u"Modelo")
    sbequipo = models.BooleanField(default=False, verbose_name=u'Sugiere baja de equipo')
    descbaja = models.CharField(default='', max_length=250, verbose_name=u"Descripcion de sugerencia")
    observaciones = models.TextField(default='', verbose_name=u"Observaciones")
    nuevo = models.BooleanField(default=False, verbose_name=u'Referencia a nuevos ingresos')

    # Campos Antiguos
    tipomantenimiento = models.IntegerField(choices=TIPO_MANTENIMIENTO, verbose_name=u'Tipo Mantenimiento', default=1)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u"Persona", on_delete=models.CASCADE)
    monitor = models.TextField(default='', verbose_name=u"monitor")
    mouse = models.TextField(default='', verbose_name=u"mouse")
    teclado = models.TextField(default='', verbose_name=u"teclado")
    procesador = models.TextField(default='', verbose_name=u"procesador")
    memoria = models.TextField(default='', verbose_name=u"memoria")
    discoduro = models.TextField(default='', verbose_name=u"discoduro")
    particiones = models.TextField(default='', verbose_name=u"particiones")
    sistemaoperativo = models.TextField(default='', verbose_name=u"sistemaoperativo")
    service = models.TextField(default='', verbose_name=u"service")
    arquitectura = models.TextField(default='', verbose_name=u"arquitectura")

    def __str__(self):
        return u"%s" % self.activotecno

    def save(self, *args, **kwargs):
        self.observaciones = self.observaciones.upper()
        super(HdDetMantenimientosActivos, self).save(*args, **kwargs)
    class Meta:
        verbose_name = u"HdPlanaprobacion"
        verbose_name_plural = u"HdPlanaprobacions"
        ordering = ['id']

ESTADO_APROBACION = (
    (1, u'ELABORADA'),
    (2, u'REVISADA'),
    (3, u'OBSERVADA'),
    (4, u'APROBADA'),
    (5, u'RECHAZADA'),
)

class HdPlanAprobacion(ModeloBase):
    periodo = models.ForeignKey(AnioEjercicio, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Anio')
    solicita = models.ForeignKey('sga.Persona', on_delete=models.CASCADE)
    fecharegistro = models.DateField(blank=True, null=True, verbose_name=u"Fecha Registro")
    archivo = models.FileField(upload_to='PlanAprobacion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Planificacion')
    estadoaprobacion = models.IntegerField(default=1, choices=ESTADO_APROBACION, verbose_name=u'Tipo Mantenimiento')
    solicitarevision = models.BooleanField(default=False, verbose_name=u'Solicitar Revision')
    observacion = models.TextField(default='', verbose_name=u"Observacion")


    def __str__(self):
        return u'%s' % self.estadoaprobacion

    class Meta:
        verbose_name = u"HdPlanaprobacion"
        verbose_name_plural = u"HdPlanaprobacions"

    def save(self, *args, **kwargs):
        super(HdPlanAprobacion, self).save(*args, **kwargs)
class HdAprobarSolicitud(ModeloBase):
    plan = models.ForeignKey(HdPlanAprobacion, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Plan')
    observacion = models.TextField(default='', verbose_name=u"Observacion")
    aprueba = models.ForeignKey('sga.Persona', on_delete=models.CASCADE)
    fechaaprobacion = models.DateField(verbose_name=u"Fecha Aprobación")
    estadosolicitud = models.IntegerField(default=1, choices=ESTADO_APROBACION, verbose_name=u"Estado Solicitud")

    def __str__(self):
        return u"Aprobador: %s, solicitante: %s, estado asignado:%s" % (self.aprueba, self.plan, self.estadosolicitud)

    def mail_notificar_jefe_departamento(self, nombresistema):
        from sga.tasks import send_html_mail
        from sga.models import miinstitucion
        send_html_mail("Aprobacion de permiso por Jefe de Departamento", "emails/permisojefedepartamento.html", {'sistema': nombresistema, 'd': self, 't': miinstitucion()}, self.plan.solicita.lista_emails_interno(), [], cuenta=CUENTAS_CORREOS[1][1])

    def mail_notificar_talento_humano(self, nombresistem):
        from sga.tasks import send_html_mail
        from sga.models import miinstitucion
        send_html_mail("Aprobacion de permiso por Talento Humano", "emails/permisotalentohumano.html", {'sistema': nombresistem, 'd': self, 't': miinstitucion()}, self.plan.solicita.lista_emails_interno(), [], cuenta=CUENTAS_CORREOS[1][1])

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        super(HdAprobarSolicitud, self).save(*args, **kwargs)


class HdCronogramaMantenimientoSem(ModeloBase):
    gruposistema = models.ForeignKey(HdGrupoSistemaEquipo, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'GrupoSistema')
    mes = models.IntegerField(default=1, choices=MONTH_CHOICES, verbose_name=u'Meses')

    def __str__(self):
        return u'%s' % self.mes

    class Meta:
        verbose_name = u"HdCronogramaMantenimientoSem"
        verbose_name_plural = u"HdCronogramaMantenimientoSems"

    def save(self, *args, **kwargs):
        super(HdCronogramaMantenimientoSem, self).save(*args, **kwargs)


class HdDetCronogramaMantenimientoSem(ModeloBase):
    cronograma = models.ForeignKey(HdCronogramaMantenimientoSem, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Cronograma Mantenimiento')
    bien = models.ForeignKey(HdBien, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Bien')
    bloque = models.ForeignKey(HdBloqueUbicacion, on_delete=models.CASCADE, blank=True, null=True,verbose_name=u'Bloque')
    cantidad = models.IntegerField(default=0)
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u"Fecha Inicio")
    fechafin = models.DateField(blank=True, null=True, verbose_name=u"Fecha Fin")

    def __str__(self):
        return u'%s' % self.cronograma

    class Meta:
        verbose_name = u"HdDetCronogramaMantenimientoSem"
        verbose_name_plural = u"HdDetCronogramaMantenimientoSems"

    def save(self, *args, **kwargs):
        super(HdDetCronogramaMantenimientoSem, self).save(*args, **kwargs)

class HdGruposCategoria(ModeloBase):
    descripcion = models.CharField(max_length=250, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(HdGruposCategoria, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Grupo categoria"
        verbose_name_plural = u"Grupos categorias"
        ordering = ['id']

class HdMantenimientoGruDanios(ModeloBase):
    grupocategoria = models.ForeignKey(HdGruposCategoria, blank=True, null=True, verbose_name=u"Grupo Categoria", on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=250, verbose_name=u"Descripción")
    activo = models.BooleanField(default=True, verbose_name=u"Tarea activa?")

    def __str__(self):
        return u"%s - %s" % (self.grupocategoria,self.descripcion)

    class Meta:
        verbose_name = u"Mantenimiento grupo danios"
        verbose_name_plural = u"Mantenimientos grupos danios"
        ordering = ['id']

class HdMantenimientoGruCategoria(ModeloBase):
    grupocategoria = models.ForeignKey(HdGruposCategoria, blank=True, null=True, verbose_name=u"Grupo Categoria", on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=250, verbose_name=u"Descripción")
    activo = models.BooleanField(default=True, verbose_name=u"Tarea activa?")

    def __str__(self):
        return u"%s - %s" % (self.grupocategoria,self.descripcion)

    class Meta:
        verbose_name = u"Mantenimiento grupo categoria"
        verbose_name_plural = u"Mantenimientos grupos categorias"
        ordering = ['id']

class HdTareasActivosPreventivos(ModeloBase):
    mantenimiento = models.ForeignKey(HdDetMantenimientosActivos, verbose_name=u"mantenimiento", on_delete=models.CASCADE)
    grupos = models.ForeignKey(HdMantenimientoGruCategoria, verbose_name=u"mantenimiento",blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u"%s" % self.mantenimiento

    class Meta:
        verbose_name = u"Tarea preventiva"
        verbose_name_plural = u"Tareas preventivas"
        ordering = ['id']

class HdPiezaParteActivosPreventivos(ModeloBase):
    mantenimiento = models.ForeignKey(HdDetMantenimientosActivos, verbose_name=u"mantenimiento", on_delete=models.CASCADE)
    piezaparte = models.ForeignKey(HdPiezaPartes, verbose_name=u"piezaparte",blank=True, null=True, on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=500, verbose_name=u'Descripcion de pieza',blank=True, null=True)

    def __str__(self):
        return u"%s" % self.mantenimiento

    class Meta:
        verbose_name = u"Pieza parte"
        verbose_name_plural = u"Pieza partes"
        ordering = ['id']

class HdTareasActivosPreventivosDanios(ModeloBase):
    mantenimiento = models.ForeignKey(HdDetMantenimientosActivos, verbose_name=u"mantenimiento", on_delete=models.CASCADE)
    grupos = models.ForeignKey(HdMantenimientoGruDanios, verbose_name=u"mantenimiento",blank=True, null=True, on_delete=models.CASCADE)
    estadodanio = models.IntegerField(choices=ESTADO_DANIO, verbose_name=u"Estado Daño",blank=True, null=True)

    def __str__(self):
        return u"%s" % self.mantenimiento

    class Meta:
        verbose_name = u"Tarea preventiva danio"
        verbose_name_plural = u"Tareas preventivas danios"
        ordering = ['id']

ESTADO_SOLICITUD_CONFIRMACION_MANT = (
    (1,'Solicitado'),
    (2,'Aprobado'),
    (3,'Rechazado'),
)

class SolicitudConfirmacionMantenimiento(ModeloBase):
    mantenimiento = models.ForeignKey(HdDetMantenimientosActivos,verbose_name=u'Mantenimiento', on_delete=models.CASCADE)
    observacion = models.CharField(max_length=500, verbose_name=u'Observacion de solicitud confirmacion')
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_CONFIRMACION_MANT,default=1,verbose_name=u'Estado de la solicitud')

    class Meta:
        verbose_name = u'Solicitud confimacion del mantenimiento'
        verbose_name_plural = u'Solicitudes de confirmacion de los mantenimientos'
        ordering = ['id']

    def __str__(self):
        return u"%s (%s - %s)"%(self.mantenimiento,self.get_estado_display(),self.estado)

class HistorialSolicitudConfirmacionMantenimiento(ModeloBase):
    solicitud = models.ForeignKey(SolicitudConfirmacionMantenimiento, verbose_name=u'Solicitud de confirmacion de mantenimiento', on_delete=models.CASCADE)
    persona = models.ForeignKey("sga.Persona",verbose_name=u'Persona quien realizo el cambio de estado', on_delete=models.CASCADE)
    observacion = models.CharField(max_length=500, verbose_name=u'Observacion de solicitud confirmacion')
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_CONFIRMACION_MANT, default=1, verbose_name=u'Estado de la solicitud')

    class Meta:
        verbose_name = u'Historial de la solicituf confimacion del mantenimiento'
        verbose_name_plural = u'Historial de las solicitudes de confirmacion de los mantenimientos'
        ordering = ['id']

    def __str__(self):
        return u"%s (%s - %s)" % (self.solicitud, self.get_estado_display(), self.estado)




# Proceso Solicitud copia
class ConfiguracionCopia(ModeloBase):
    cantidad = models.IntegerField(default=1, verbose_name=u"Cantidad de páginas")
    tiempo = models.IntegerField(default=0, verbose_name=u"Tiempo en minutos", null=True, blank=True)
    # tiempo = models.TimeField(verbose_name=u'Tiempo')

    class Meta:
        verbose_name = u"Copia"
        verbose_name_plural = u"Copias"
        ordering = ['-id']

    def tiempo_a_formato24horas(self):
        # minutoplural = ''
        # horaplural = ''
        # if self.tiempo.minute > 1:jpr
        #     minutoplural = 's'
        if self.tiempo.hour > 0:
            # if self.tiempo.hour > 1:
            #     horaplural = 's'
            return self.tiempo.strftime('%H horas %M minutos')
        else:
            return self.tiempo.strftime(f'%M minutos')

    def str_tiempo(self):
        if self.tiempo > 1:
            return f'{self.tiempo} minutos'
        else:
            return f'{self.tiempo} minuto'

    def str_cantidad(self):
        if self.cantidad > 1:
            return f'{self.cantidad} páginas'
        else:
            return f'{self.cantidad} página'

    def __str__(self):
        return u'%s/%s' % (self.str_cantidad(), self.str_tiempo())

    def en_uso(self):
        return self.impresora_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(ConfiguracionCopia, self).save(*args, **kwargs)

class Impresora(ModeloBase):
    impresora = models.ForeignKey("sagest.ActivoTecnologico", on_delete=models.PROTECT, verbose_name=u'Impresora', default=34)
    configuracioncopia = models.ForeignKey(ConfiguracionCopia, verbose_name=u'Configuración Copia', on_delete=models.PROTECT, null=True, blank=True)
    # ubicacion = models.ForeignKey("sagest.Ubicacion", on_delete=models.PROTECT, verbose_name=u'Ubicación')

    def __str__(self):
        return u'%s - %s' % (self.impresora, self.configuracioncopia)
        # return u'Cod. %s %s %s - %s %s' % (self.impresora.activotecnologico.codigointerno, self.impresora.activotecnologico.marca, self.impresora.activotecnologico.modelo, self.impresora.ubicacion.bloque.descripcion, self.ubicacion.nombre)

    def informativo(self):
        return u'%s' % (self.impresora)

    def get_impresora(self):
        pass
        # return u'Cod. %s - %s %s' % (self.activofijo.codigointerno, self.activofijo.marca, self.activofijo.modelo)

    def get_ubicacion(self):
        pass
        # return u'Ubicación: %s %s' % (self.ubicacion.bloque.descripcion, self.ubicacion.nombre)

    class Meta:
        verbose_name = u"Impresora"
        verbose_name_plural = u"Impresoras"

    def en_uso(self):
        return self.detallejornadaimpresora_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(Impresora, self).save(*args, **kwargs)


DIAS_CHOICES = (
    (1, u'LUNES'),
    (2, u'MARTES'),
    (3, u'MIERCOLES'),
    (4, u'JUEVES'),
    (5, u'VIERNES'),
    (6, u'SABADO'),
    (7, u'DOMINGO')
)

# Disponibilidad de las impresoras
class JornadaImpresora(ModeloBase):
    dia = models.IntegerField(choices=DIAS_CHOICES, default=1, verbose_name=u'Día')
    comienza = models.TimeField(verbose_name=u'Hora que comienza')
    termina = models.TimeField(verbose_name=u'Hora que termina')

    def __str__(self):
        # return u'%s de %s a %s' % (DIAS_CHOICES[self.C.dia-1][1], self.comienza, self.termina)
        return u'%s de %s a %s' % (self.get_dia_display().title(), self.comienza.strftime('%Hh:%Mm'), self.termina.strftime('%Hh:%Mm'))

    class Meta:
        verbose_name = u"Jornada de Solicitud Copia"
        verbose_name_plural = u"Jornadas de Solicitudes de Copias"
        ordering = ['dia', 'comienza']

    def en_uso(self):
        return self.detallejornadaimpresora_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(JornadaImpresora, self).save(*args, **kwargs)


class DetalleJornadaImpresora(ModeloBase):
    impresora = models.ForeignKey(Impresora, verbose_name=u'Impresora', on_delete=models.PROTECT)
    jornadaimpresora = models.ForeignKey(JornadaImpresora, verbose_name=u'Jornada impresora', on_delete=models.PROTECT)

    class Meta:
        verbose_name = u'Solicitud de Copia'
        verbose_name_plural = u'Solicitudes de Copias'
        ordering = ['id']

    def __str__(self):
        return u"%s - %s" % (self.jornadaimpresora, self.impresora)

    def tiempo_configurado_impresora(self):
        jornadaimpresora = self.jornadaimpresora.filter(status=True)
        hoy = datetime.now().date()
        comienza = jornadaimpresora.comienza
        termina = jornadaimpresora.termina
        tiempoensegundos = (datetime.time(termina.hour, termina.minute, termina.second) - (datetime.time(comienza.hour, comienza.minute, comienza.second))).seconds
        return tiempoensegundos

    # def get_detallejornadaimpresora(self):
    #     return u"Horario: %s, %s" % (self.jornadaimpresora, self.impresora)

    def en_uso(self):
        return self.solicitudcopia_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(DetalleJornadaImpresora, self).save(*args, **kwargs)


ESTADO_SOLICITUD_COPIA = (
    (1, u"SOLICITADO"),
    (2, u"ATENDIDO"),
)


class SolicitudCopia(ModeloBase):
    fechaagendada = models.DateField(verbose_name=u'Fecha agendada', null=True)
    profesor = models.ForeignKey("sga.Profesor", verbose_name=u'Profesor', on_delete=models.PROTECT)
    cantidadcopia = models.IntegerField(default=0, verbose_name=u"Cantidad de copias")
    horainicio = models.TimeField(verbose_name=u'Hora de inicio:', null=True)
    horafin = models.TimeField(verbose_name=u'Hora de fin: (hh:mm)', null=True)
    # tiemporequerido = models.IntegerField(default=1, verbose_name=u"Tiempo requerido en minutos")
    tiemporequerido = models.TimeField(verbose_name=u'Tiempo requerido')
    detallejornadaimpresora = models.ForeignKey(DetalleJornadaImpresora,verbose_name=u'Jornada', on_delete=models.PROTECT)
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_COPIA, default=1, verbose_name=u'Estado de la solicitud')

    class Meta:
        verbose_name = u'Solicitud de Copia'
        verbose_name_plural = u'Solicitudes de Copias'
        ordering = ['id']

    def __str__(self):
        return u"Prof. ci %s - f. agen. %s - %s de %s a %s - %s copias - %s - Jornada conf. %s." % (
                        self.profesor.persona.cedula,
                        # self.profesor,
                        # self.historial_ordenascendente().first().fecha if self.historial_ordenascendente().first() else '',
                        self.fechaagendada, self.get_estado_display(),
                        self.horainicio, self.horafin, self.cantidadcopia, self.detallejornadaimpresora.impresora,
                        self.detallejornadaimpresora.jornadaimpresora)

    def historial_ordenascendente(self):
        return self.historialsolicitudcopia_set.filter(status=True).order_by('id')

    def puede_eliminar(self):
        if self.estado == 1:
            return True
        return False

    def str_tiemporequerido(self):
        minutoplural = ''
        horaplural = ''
        if self.tiemporequerido.minute > 1:
            minutoplural = 's'
        if self.tiemporequerido.hour > 0:
            if self.tiemporequerido.hour > 1:
                horaplural = 's'
            return self.tiemporequerido.strftime(f'%H hora{horaplural} %M minuto{minutoplural}')
        else:
            return self.tiemporequerido.strftime(f'%M minuto{minutoplural}')

    def en_uso(self):
        return self.historialsolicitudcopia_set.filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(SolicitudCopia, self).save(*args, **kwargs)


class HistorialSolicitudCopia(ModeloBase):
    fecha = models.DateField(verbose_name=u'Fecha')
    persona = models.ForeignKey("sga.Persona",verbose_name=u'Persona que realizó el cambio de estado', on_delete=models.PROTECT)
    solicitudcopia = models.ForeignKey(SolicitudCopia, verbose_name=u'Solicitud de Copia', on_delete=models.PROTECT)
    observacion = models.CharField(max_length=500, verbose_name=u'Observacion de solicitud de copia', blank=True, null=True)
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_COPIA, default=1, verbose_name=u'Estado de la solicitud')

    class Meta:
        verbose_name = u'Historial de Solicitud de Copia'
        verbose_name_plural = u'Historial de Solicitudes de Copias'
        ordering = ['id']

    def __str__(self):
        return u"%s - %s - %s - %s" % (self.fecha, self.persona, self.solicitudcopia, self.get_estado_display())


    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        super(HistorialSolicitudCopia, self).save(*args, **kwargs)

class BodegaProducto(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=400, verbose_name=u"Descripción")
    grupo = models.ForeignKey("sagest.GruposCategoria",verbose_name=u'Grupo Categoria', on_delete=models.PROTECT,null=True, blank=True)
    def __str__(self):
        return f"{self.descripcion}"

    class Meta:
        verbose_name = u'Bodega Producto'
        verbose_name_plural = u'Bodega Productos'
        ordering = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        self.grupo = self.grupo
        super(BodegaProducto, self).save(*args, **kwargs)

    def en_uso(self):
        return True if self.bodegakardex_set.values('id').filter(status=True).exists() else False

    def cantidad_total(self):
        cantidad = self.bodegakardex_set.filter(status=True).order_by('producto__id', '-fecha').distinct('producto__id', 'fecha').first()
        if cantidad.saldoFinal != 0:
            cantidadfinal = cantidad.saldoFinal
        else:
            cantidadfinal = 0
        return cantidadfinal

    def producto_en_factura(self):
        productoenfactura = DetalleFacturaCompra.objects.filter(producto=self.id, status=True)
        return productoenfactura


class BodegaUnidadMedida(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=400, verbose_name=u"Descripción")

    def __str__(self):
        return f"{self.descripcion}"

    class Meta:
        verbose_name = u'Bodega Unidad Medida'
        verbose_name_plural = u'Bodega Unidades Medida'
        ordering = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(BodegaUnidadMedida, self).save(*args, **kwargs)

    def en_uso(self):
        return True if self.bodegaproductodetalle_set.values('id').filter(status=True).exists() else False


class BodegaProductoDetalle(ModeloBase):
    producto = models.ForeignKey(BodegaProducto, verbose_name=u'BodegaProducto', on_delete=models.PROTECT, null=True, blank=True)
    unidadmedida = models.ForeignKey(BodegaUnidadMedida, verbose_name=u'Unidadmedida', on_delete=models.PROTECT, null=True, blank=True)
    valor = models.IntegerField(default=0, verbose_name=u"Valor", null=True, blank=True)

    def __str__(self):
        return f"{self.unidadmedida}"

    class Meta:
        verbose_name = u'Bodega Producto Detalle'
        verbose_name_plural = u'Bodega Producto Detalles'
        ordering = ['id']

    def en_uso(self):
        return True if self.bodegakardex_set.values('id').filter(status=True, tipotransaccion=1 ).exists() else False

class BodegaTipoTransaccion(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=400, verbose_name=u"Descripción")

    def __str__(self):
        return f"{self.descripcion}"

    class Meta:
        verbose_name = u'Bodega Tipo Transaccion'
        verbose_name_plural = u'Bodega Tipos Transacciones'
        ordering = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(BodegaTipoTransaccion, self).save(*args, **kwargs)

    def en_uso(self):
        return True if self.bodegakardex_set.values('id').filter(status=True).exists() else False


class FacturaCompra(ModeloBase):
    fecha = models.DateTimeField( verbose_name=u'Fecha', null=True, blank=True)
    codigo = models.CharField(max_length=30, verbose_name=u"Código de factura", null=True, blank=True)
    proveedor = models.ForeignKey('sagest.Proveedor',verbose_name=u'Proveedor', on_delete=models.PROTECT, null=True, blank=True)
    total = models.DecimalField(max_digits=50,verbose_name=u'Total', decimal_places=4, default=0, null=True, blank=True)
    detalle = models.CharField(max_length=300, verbose_name=u'Detalle Factura Compra', null= True, blank=True)
    archivo = models.FileField(upload_to='facturacompra', blank=True, null=True)

    def __str__(self):
        return f"{self.codigo}"

    class Meta:
        verbose_name = u'Factura de Compra'
        verbose_name_plural = u'Facturas de Compras'
        ordering = ('codigo',)

    def existen_salidas(self):
        productos = self.detallefacturacompra_set.values_list('id', flat=True).filter(status=True)
        return True if HdIncidenteProductoDetalle.objects.filter(status=True, producto_id__in=productos).exists() else False


class DetalleFacturaCompra(ModeloBase):
    factura = models.ForeignKey(FacturaCompra, verbose_name=u'Factura de compra', on_delete=models.PROTECT, null=True, blank=True)
    producto = models.ForeignKey(BodegaProducto, verbose_name=u'BodegaProducto', on_delete=models.PROTECT, null=True, blank=True)
    # unidadmedida = models.ForeignKey(BodegaUnidadMedida, verbose_name=u'BodegaUnidadMedida', on_delete=models.PROTECT, null=True, blank=True)
    unidadmedida = models.ForeignKey(BodegaProductoDetalle, verbose_name=u'BodegaProductoDetalle', on_delete=models.PROTECT, null=True, blank=True)
    cantidad = models.IntegerField(default=0, verbose_name=u"Cantidad", null=True, blank=True)
    costo = models.DecimalField(max_digits=50, verbose_name=u'Costo', decimal_places=4, default=0, null=True, blank=True)
    total = models.DecimalField(max_digits=50, verbose_name=u'Total', decimal_places=4, default=0, null=True, blank=True)

    def __str__(self):
        return f"{self.producto}"

    class Meta:
        verbose_name = u'Detalle de Factura de Compra'
        verbose_name_plural = u'Detalles de Facturas de Compras'
        ordering = ['id']

    def actualizar_kardex(self, tipo, cantidad):
        # Obtener el registro del producto en la tabla "BodegaKardex"
        try:
            kardex = BodegaKardex.objects.filter(status=True, producto=self.producto).latest('fecha')
            saldo_inicial = kardex.saldoFinal
        except BodegaKardex.DoesNotExist:
            saldo_inicial = 0

        # Calcular el saldo final
        if tipo == 1:
            saldo_final = saldo_inicial + cantidad

        if tipo == 3:
            if not saldo_inicial <= 0:
                saldo_final = saldo_inicial - cantidad
            else:
                saldo_final = 0

        instancia = BodegaKardex(bodega = BodegaPrimaria.objects.get(pk=1),
                                 detallefactura=self,
                                 producto=self.producto,
                                 tipotransaccion=BodegaTipoTransaccion.objects.get(pk=tipo),
                                 unidadmedida=self.unidadmedida,
                                 cantidad=self.cantidad,
                                 saldoInicial=saldo_inicial,
                                 saldoFinal=saldo_final,
                                 fecha=datetime.now())


        return instancia


class BodegaPrimaria(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=400, verbose_name=u"Descripción")

    def __str__(self):
        return f"{self.descripcion}"

    class Meta:
        verbose_name = u'Bodega Primaria'
        verbose_name_plural = u'Bodegas Primarias'
        ordering = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(BodegaPrimaria, self).save(*args, **kwargs)


class BodegaKardex(ModeloBase):
    bodega = models.ForeignKey(BodegaPrimaria, verbose_name=u'BodegaInicial', on_delete=models.PROTECT, null=True, blank=True)
    detallefactura = models.ForeignKey(DetalleFacturaCompra, verbose_name=u'DetalleFactura', on_delete=models.PROTECT, null=True, blank=True)
    detalleincidente = models.ForeignKey("helpdesk.HdIncidenteProductoDetalle", verbose_name=u'DetalleIncidente', on_delete=models.PROTECT, null=True, blank=True)
    producto = models.ForeignKey(BodegaProducto, verbose_name=u'BodegaProducto', on_delete=models.PROTECT)
    tipotransaccion = models.ForeignKey(BodegaTipoTransaccion, verbose_name=u'BodegaTipoTransaccion', on_delete=models.PROTECT, null=True, blank=True)
    # unidadmedida = models.ForeignKey(BodegaUnidadMedida, verbose_name=u'BodegaUnidadMedida', on_delete=models.PROTECT)
    unidadmedida = models.ForeignKey(BodegaProductoDetalle, verbose_name=u'BodegaProductoDetalle', on_delete=models.PROTECT)
    cantidad = models.IntegerField(default=0, verbose_name=u"Cantidad")
    saldoInicial = models.IntegerField(default=0, verbose_name=u"SaldoInicial")
    saldoFinal = models.IntegerField(default=0, verbose_name=u"SaldoFinal")
    fecha = models.DateTimeField(verbose_name=u'Fecha', null=True, blank=True)
    observacion = models.TextField(default='', verbose_name=u'Observación')

    def __str__(self):
        return f"{self.producto}"

    class Meta:
        verbose_name = u'Bodega Kardex'
        verbose_name_plural = u'Bodega Kardex'
        ordering = ('producto',)


ESTADO_NOTIFICACION = (
    (1, u"PENDIENTE"),
    (2, u"ACEPTADO"),
    (3, u"RECHAZADO"),
)
class HdIncidenteProductoDetalle(ModeloBase):
    activo = models.ForeignKey(ActivoTecnologico, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Activo tecnologico')
    incidente = models.ForeignKey(HdIncidente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Incidente',related_name='hd_p_incidentes')
    producto = models.ForeignKey(BodegaProducto, verbose_name=u'BodegaProducto', on_delete=models.PROTECT, null=True, blank=True)
    unidadmedida = models.ForeignKey(BodegaProductoDetalle, verbose_name=u'BodegaProductoDetalle', on_delete=models.PROTECT, null=True, blank=True)
    cantidad = models.IntegerField(default=0, verbose_name=u"Cantidad", null=True, blank=True)
    estado = models.IntegerField(choices=ESTADO_NOTIFICACION, default=1, blank=True, null=True, verbose_name=u'Estado')
    fechaestado = models.DateField(blank=True, null=True, verbose_name=u"Fecha de Cambio de estado")
    horaestado = models.TimeField(blank=True, null=True, verbose_name=u"hora de Cambio de estado")

    def __str__(self):
        return f"{self.incidente}"

    class Meta:
        verbose_name = u'Detalle de Incidente Producto '
        verbose_name_plural = u'Detalle de Incidentes Productos'
        ordering = ('producto',)



# class DetalleIncidenteProducto(ModeloBase):
#     producto = models.ForeignKey(BodegaProductoDetalle, verbose_name=u'BodegaProducto', on_delete=models.PROTECT, null=True, blank=True)
#     cantidad = models.IntegerField(default=0, verbose_name=u"Cantidad", null=True, blank=True)
#     costo = models.DecimalField(max_digits=50, verbose_name=u'Costo', decimal_places=4, default=0, null=True, blank=True)
#     total = models.DecimalField(max_digits=50, verbose_name=u'Total', decimal_places=4, default=0, null=True, blank=True)