# -*- coding: latin-1 -*-
from __future__ import unicode_literals

import json
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.forms import model_to_dict

from bd.models import CronogramaCoordinacion, UserToken
from sagest.models import Departamento, CuentaBanco, Rubro
from sga.models import Periodo, Coordinacion, PeriodoMatriculacion, MateriaAsignada, Matricula, Inscripcion, \
    AsignaturaMalla, Persona, Carrera
from sga.funciones import ModeloBase, remover_caracteres_especiales_unicode

TIPO_AMBIENTE = (
    (1, u"Desarrollo"),
    (2, u"Producción"),
)


TIPO_SERVICIO_SOAP = (
    (1, u"Cobro en linea"),
)


class Setting(ModeloBase):
    nombre = models.CharField(default='', max_length=250, blank=True, null=True, verbose_name=u'Nombre del servicio')
    cuenta = models.ForeignKey(CuentaBanco, verbose_name=u'Cuenta del banco', blank=True, null=True, on_delete=models.CASCADE)
    activo = models.BooleanField(default=False, verbose_name=u'Activo?')
    tipo = models.IntegerField(choices=TIPO_SERVICIO_SOAP, default=1, verbose_name=u'Tipo de servicio')
    tipo_ambiente = models.IntegerField(choices=TIPO_AMBIENTE, default=1, null=True, verbose_name=u'Tipo de ambiente')
    hora_conciliacion = models.TimeField(blank=True, null=True, verbose_name=u'Hora de conciliación')
    usuarios = models.ManyToManyField(User)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"

    def get_str(self):
        return self.__str__()

    def color_tipo(self):
        if self.es_desarrollo():
            return 'warning'
        elif self.es_produccion():
            return 'success'
        else:
            return 'default'

    def get_usuarios(self):
        return self.usuarios.all()

    def es_desarrollo(self):
        return self.tipo_ambiente == 1

    def es_produccion(self):
        return self.tipo_ambiente == 2

    def en_uso(self):
        return PagoBanco.objects.values("id").filter(status=True, config=self).exists()

    def save(self, *args, **kwargs):
        if self.id and self.cuenta:
            setting = Setting.objects.filter(cuenta=self.cuenta, tipo=self.tipo).exclude(pk=self.id)
            if setting.exists():
                raise NameError(u"Ya existe cuenta de banco con tipo de servicio")
        else:
            if self.cuenta:
                setting = Setting.objects.filter(cuenta=self.cuenta, tipo=self.tipo)
                if setting.exists():
                    raise NameError(u"Ya existe cuenta de banco con tipo de servicio")
        self.nombre = self.nombre.strip()
        super(Setting, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Configuración del SOAP"
        verbose_name_plural = u"Configuraciones del SOAP"


TIPO_TRANSACCION = (
    (1, u"0001: Consulta"),
    (2, u"0002: Respuesta de la Consulta"),
    (3, u"0003: Pago"),
    (4, u"0004: Respuesta del Pago"),
    (5, u"0005: Reverso"),
    (6, u"0005: Respuesta del Reverso"),
)

CANAL_PROCESO = (
    ("VEN", u"VEN: Ventanilla Banco"),
    ("AUD", u"AUD: Audiomatico"),
    ("INT", u"INT: Intermatico"),
    ("BAN", u"BAN: bancomatico"),
    ("BEF", u"BEF: bancomatico Efectivo"),
    ("CPT", u"CPT: Easysoft"),
    ("CXY", u"CXY: XY Prepago"),
    ("CWU", u"CWU: Western Union"),
    ("MVL", u"MVL: Movilmatico"),
    ("WEB", u"WEB: Bizbank"),
)


class PagoBanco(ModeloBase):
    config = models.ForeignKey(Setting, related_name='+', verbose_name=u'Configuración', on_delete=models.CASCADE)
    tipo_ambiente = models.IntegerField(choices=TIPO_AMBIENTE, default=1, null=True, verbose_name=u'Tipo de transacción')
    num_transaccion = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Numero de Transaccion')
    producto = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Producto')
    tipo_transaccion = models.IntegerField(choices=TIPO_TRANSACCION, blank=True, null=True, verbose_name=u'Tipo de ambiente')
    fecha_transaccion = models.DateField(blank=True, null=True, verbose_name=u'Fecha de transacción')
    fecha_contable = models.DateField(blank=True, null=True, verbose_name=u'Fecha contable')
    hora_transaccion = models.TimeField(blank=True, null=True, verbose_name=u'Hora de transacción')
    canal_proceso = models.CharField(choices=CANAL_PROCESO, max_length=10, blank=True, null=True, verbose_name=u'Canal de proceso')
    agencia = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Agencia')
    terminal = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Terminal')
    servicio = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Servicio')
    rubro = models.ForeignKey(Rubro, blank=True, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=u'Rubro')
    valor = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u'Valor a pagar')
    persona = models.ForeignKey(Persona, blank=True, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=u'Persona')
    reverso = models.BooleanField(default=False, verbose_name=u'Reverso?')
    procesado = models.BooleanField(default=False, verbose_name=u'Procesado?')
    fecha_procesado = models.DateField(blank=True, null=True, verbose_name=u'Fecha de procesado')
    hora_procesado = models.TimeField(blank=True, null=True, verbose_name=u'Hora de procesado')

    def __str__(self):
        if self.es_desarrollo():
            return f"AMBIENTE DE DESARROLLO - {self.num_transaccion} - {self.rubro.id} - {self.persona.nombre_completo_inverso()}"
        return f"{self.num_transaccion} - {self.rubro.id} - {self.persona.nombre_completo_inverso()}"

    def es_desarrollo(self):
        return self.tipo_ambiente == 1

    def es_produccion(self):
        return self.tipo_ambiente == 2

    def save(self, *args, **kwargs):
        # if self.id:
        #     pagos = PagoBanco.objects.filter(rubro=self.rubro, reverso=False)
        #     if pagos.values("id").exists():
        #         raise NameError(u"Ya existe")

        if not self.id:
            self.tipo_ambiente = self.config.tipo_ambiente
        super(PagoBanco, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Pago de banco"
        verbose_name_plural = u"Pagos del banco"
        # unique_together = ('num_identificacion_pago', 'tipo_ambiente', 'config')


class ReversoPagoBanco(ModeloBase):
    pago = models.ForeignKey(PagoBanco, verbose_name=u'Pago', on_delete=models.CASCADE)
    tipo_ambiente = models.IntegerField(choices=TIPO_AMBIENTE, default=1, null=True, verbose_name=u'Tipo de transacción')
    fecha_transaccion = models.DateField(blank=True, null=True, verbose_name=u'Fecha de transacción')
    fecha_contable = models.DateField(blank=True, null=True, verbose_name=u'Fecha contable')
    hora_transaccion = models.TimeField(blank=True, null=True, verbose_name=u'Hora de transacción')
    canal_proceso = models.CharField(choices=CANAL_PROCESO, max_length=10, blank=True, null=True, verbose_name=u'Canal de proceso')
    agencia = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Agencia')
    terminal = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Terminal')
    servicio = models.CharField(max_length=250, blank=True, null=True, verbose_name=u'Servicio')

    def __str__(self):
        if self.pago.es_desarrollo():
            return f"AMBIENTE DE DESARROLLO - {self.pago.num_transaccion} - {self.pago.rubro.id} - {self.pago.persona.nombre_completo_inverso()}"
        return f"{self.pago.num_transaccion} - {self.pago.rubro.id} - {self.pago.persona.nombre_completo_inverso()}"

    def save(self, *args, **kwargs):
        pago = self.pago
        pago.reverso = True
        pago.save()
        super(ReversoPagoBanco, self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Reverso Pago de banco"
        verbose_name_plural = u"Reverso Pagos del banco"
        unique_together = ('pago', )


def upload_conciliacion_directory_path(instance, filename):
    # ahora = datetime.now()
    ahora = instance.fecha_transaccion
    return f'soap/western_union/conciliacion/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/{filename}'


class ConciliacionPago(ModeloBase):
    config = models.ForeignKey(Setting, related_name='+', verbose_name=u'Configuración', on_delete=models.CASCADE)
    tipo_ambiente = models.IntegerField(choices=TIPO_AMBIENTE, default=1, null=True, verbose_name=u'Tipo de transacción')
    fecha_transaccion = models.DateField(blank=True, null=True, verbose_name=u'Fecha de transacción')
    hora_transaccion = models.TimeField(blank=True, null=True, verbose_name=u'Hora de transacción')
    fecha_conciliacion = models.DateField(blank=True, null=True, verbose_name=u'Fecha de conciliación')
    hora_conciliacion = models.TimeField(blank=True, null=True, verbose_name=u'Hora de conciliación')
    procesado = models.BooleanField(default=False, verbose_name=u'Procesado?')
    fecha_procesado = models.DateField(blank=True, null=True, verbose_name=u'Fecha de procesado')
    hora_procesado = models.TimeField(blank=True, null=True, verbose_name=u'Hora de procesado')
    archivo_original = models.FileField(upload_to=upload_conciliacion_directory_path, max_length=1000, blank=True, null=True, verbose_name=u'Archivo')
    archivo_procesado = models.FileField(upload_to=upload_conciliacion_directory_path, max_length=1000, blank=True, null=True, verbose_name=u'Archivo')

    def __str__(self):
        if self.config.es_desarrollo():
            return f"AMBIENTE DE DESARROLLO - {self.fecha_transaccion.strftime('%Y-%m-%d')} {self.hora_transaccion.strftime('%H:%M:%S')}"
        return f"{self.fecha_transaccion.strftime('%Y-%m-%d')} {self.hora_transaccion.strftime('%H:%M:%S')}"

    class Meta:
        verbose_name = u"Conciliación Pago de banco"
        verbose_name_plural = u"Conciliaciones Pagos del banco"
        unique_together = ('config', 'fecha_transaccion')

    def save(self, *args, **kwargs):
        super(ConciliacionPago, self).save(*args, **kwargs)


class ConciliacionDetallePago(ModeloBase):
    conciliacion = models.ForeignKey(ConciliacionPago, related_name='+', verbose_name=u'Conciliación', on_delete=models.CASCADE)
    pago = models.ForeignKey(PagoBanco, verbose_name=u'Pago', on_delete=models.CASCADE)
    valor_cobrado = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u'Valor cobrado')
    valor_conciliado = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u'Valor conciliado')
    procesado = models.BooleanField(default=False, verbose_name=u'Procesado?')
    fecha_procesado = models.DateField(blank=True, null=True, verbose_name=u'Fecha de procesado')
    hora_procesado = models.TimeField(blank=True, null=True, verbose_name=u'Hora de procesado')

    def __str__(self):
        if self.conciliacion.config.es_desarrollo():
            return f"AMBIENTE DE DESARROLLO - {self.pago.num_transaccion}"
        return f"{self.pago.num_transaccion}"

    class Meta:
        verbose_name = u"Detalle de la conciliación Pago de banco"
        verbose_name_plural = u"Detalles de la conciliación Pagos del banco"
        unique_together = ('conciliacion', 'pago')

    def save(self, *args, **kwargs):
        super(ConciliacionDetallePago, self).save(*args, **kwargs)


