# -*- coding: UTF-8 -*-
import operator
import os
import random
import time
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.db import models, connection, connections

from settings import ADMINISTRADOR_ID
from sga.models import Persona
from sga.funciones import ModeloBase
from django.contrib.auth.models import User
from clrncelery.models import TYPE_APP_LABEL
from core.choices.models.sagest import AccionesMrcadaChoice
from core.choices.models.sagest import ProfileChoice

class PersonTrainFace(ModeloBase):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, verbose_name='Persona')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fechahora = models.DateTimeField(blank=True, null=True, verbose_name='Fecha y hora')

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name = u"Rostro facial"
        verbose_name_plural = u"Rostros faciales"
        unique_together = ('persona',)

class MarcadaBiometrica(models.Model):
    username = models.CharField(max_length=30, verbose_name='Usuario')
    fecha_creacion = models.DateTimeField(blank=True, null=True, verbose_name='Fecha y hora de acceso')
    fecha_acceso = models.DateField(verbose_name='Fecha de acceso', blank=True, null=True)
    hora_acceso = models.TimeField(blank=True, null=True, verbose_name='Hora de acceso')
    resultado_autenticacion = models.CharField(max_length=255, verbose_name='Resultado de autenticación', blank=True, null=True)
    tipo_autenticacion = models.CharField(max_length=255, verbose_name='Tipo de autenticación', blank=True, null=True)
    nombre_dispositivo = models.CharField(max_length=255, verbose_name='Nombre del dispositivo', blank=True, null=True)
    numero_serie_dispositivo = models.CharField(max_length=255, verbose_name='Número de serie del dispositivo', blank=True, null=True)

    # Campos adicionales de la primera imagen
    nombre_recurso = models.CharField(max_length=255, blank=True, null=True, verbose_name='Nombre del recurso')
    nombre_lector = models.CharField(max_length=255, blank=True, null=True, verbose_name='Nombre del lector')
    grupo_personas = models.CharField(max_length=255, blank=True, null=True, verbose_name='Grupo de personas')
    numero_tarjeta = models.CharField(max_length=255, blank=True, null=True, verbose_name='Número de tarjeta')
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name='Dirección')
    temperatura_superficie = models.CharField(max_length=255, blank=True, null=True, verbose_name='Temperatura de la superficie')
    estado_temperatura = models.CharField(max_length=255, blank=True, null=True, verbose_name='Estado de la temperatura')
    usando_mascara = models.CharField(max_length=255, blank=True, null=True, verbose_name='Usando mascarilla')

    # Campos adicionales de la última imagen
    estado_asistencia = models.CharField(max_length=255, blank=True, null=True, verbose_name='Estado de asistencia')

    def __str__(self):
        return f'Marcada biometrica: {self.username} {self.fecha_creacion}'

class PersonaMarcada(ModeloBase):
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, verbose_name="Persona")
    cargo = models.ForeignKey('sagest.DenominacionPuesto',blank=True, null=True, on_delete=models.CASCADE, verbose_name="Cargo")
    departamento = models.ForeignKey('sagest.Departamento',blank=True, null=True, on_delete=models.CASCADE, verbose_name="Departamento")
    activo = models.BooleanField(default=True, verbose_name='Activo')
    externo = models.BooleanField(default=False, verbose_name='Marca fuera de la institución')
    solo_pc = models.BooleanField(default=True, verbose_name='Marcar solo en pc')

    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name = u"Persona que Marca"
        verbose_name_plural = u"Personas que Marcan"

class HistorialCambioEstado(ModeloBase):
    persona_marcada = models.ForeignKey(PersonaMarcada, on_delete=models.CASCADE, verbose_name="Persona a quien le realizaron la acción")
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, verbose_name="Persona que realizo la acción")
    tipo = models.IntegerField(default=1, choices=AccionesMrcadaChoice.choices, verbose_name='Tipo de acción')
    estado = models.BooleanField(default=True, verbose_name='Estado')
    motivo = models.TextField(blank=True, null=True, verbose_name='Motivo')
    def __str__(self):
        return u'%s' % self.persona

    class Meta:
        verbose_name = u"Estado de cambio de estado"
        verbose_name_plural = u"Estado de cambio de estado"



# class ControlAccesoFaceId(ModeloBase):
#     app = models.IntegerField(default=1, choices=TYPE_APP_LABEL, verbose_name='Aplicación')
#     profile = models.IntegerField(default=1, choices=ProfileChoice.choices, verbose_name='perfil permitido')
#     cargos = models.ManyToManyField('sagest.denominacionpuesto', verbose_name='Cargos')
#     activo = models.BooleanField(default=True, verbose_name='Activo')
#     todos = models.BooleanField(default=False, verbose_name='Todos los cargos')
#     def __str__(self):
#         return u'%s' % self.get_app_display()
#
#     class Meta:
#         verbose_name = u"Control de acceso"
#         verbose_name_plural = u"Controles de acceso"

