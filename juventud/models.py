# -*- coding: UTF-8 -*-
import json
import operator
import os
import random
import time
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal
import PyPDF2

from dateutil import rrule
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User, Group
from django.contrib.sessions.models import Session
from django.db import models
from django.db.models import Sum

from sga.funciones import ModeloBase
from django.contrib.contenttypes.models import ContentType
from sga.models import Sexo, Pais, Provincia, Canton
from django.db.models import Q
unicode = str

ESTADO_APROBACION = (
    (1, u'PENDIENTE'),
    (2, u'APROBADA'),
    (3, u'RECHAZADA'),
)

class Personaformacion(ModeloBase):
    nombres = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    apellido1 = models.CharField(default='', max_length=50, verbose_name=u"1er Apellido")
    apellido2 = models.CharField(default='', max_length=50, verbose_name=u"2do Apellido")
    cedula = models.CharField(default='', max_length=20, verbose_name=u"Cedula", blank=True, db_index=True)
    pasaporte = models.CharField(default='', max_length=20, blank=True, verbose_name=u"Pasaporte", db_index=True)
    sexo = models.ForeignKey(Sexo, default=2, verbose_name=u'Sexo', on_delete=models.CASCADE)
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electronico personal")
    lugarnacimiento = models.CharField(default='', max_length=300, verbose_name=u"Lugar de nacimiento")
    direccion = models.CharField(default='', max_length=300, verbose_name=u"Calle principal")
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Telefono movil")
    pais = models.ForeignKey(Pais, blank=True, null=True, related_name='+', verbose_name=u'País residencia', on_delete=models.CASCADE)
    provincia = models.ForeignKey(Provincia, blank=True, null=True, related_name='+', verbose_name=u"Provincia de residencia", on_delete=models.CASCADE)
    canton = models.ForeignKey(Canton, blank=True, null=True, related_name='+', verbose_name=u"Canton de residencia", on_delete=models.CASCADE)
    fechanacimiento = models.DateField(blank=True, null=True, verbose_name=u"Fecha Nacimiento")

    def __str__(self):
        return u'%s %s %s' % (self.apellido1, self.apellido2, self.nombres)

    class Meta:
        verbose_name = u"Personajuventud"
        verbose_name_plural = u"Personasjuventud"
        ordering = ['apellido1']

class Programaformacion(ModeloBase):
    nombres = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    fechainicio = models.DateField(blank=True, null=True, verbose_name=u"Fecha")
    modalidad = models.CharField(default='', max_length=100, verbose_name=u'Modalidad')
    duracion = models.CharField(default='', max_length=100, verbose_name=u'Duracion')
    banner = models.FileField(upload_to='banner', blank=True, null=True, verbose_name=u'Banner de la formación')
    activo = models.BooleanField(default=True, verbose_name=u'Programa activo')

    def __str__(self):
        return f'{self.nombres}'

    def download_banner(self):
        return self.banner.url

    class Meta:
        verbose_name = u"Programajuventud"
        verbose_name_plural = u"Programasjuventud"
        ordering = ['nombres']

class PersonaPrograma(ModeloBase):
    personaformacion = models.ForeignKey(Personaformacion, verbose_name=u"PersonaFormacion", blank=True, null=True, on_delete=models.CASCADE)
    programa = models.ForeignKey(Programaformacion, verbose_name=u"PersonaFormacion", blank=True, null=True, on_delete=models.CASCADE)
    nombreproyecto = models.TextField(verbose_name=u"Nombre proyecto", blank=True, null=True)
    poblacion = models.TextField(verbose_name=u"Poblacion", blank=True, null=True)
    meta = models.TextField(verbose_name=u"Meta", blank=True, null=True)
    resultado = models.TextField(verbose_name=u"Resultado", blank=True, null=True)
    terminocondicion = models.BooleanField(default=False, verbose_name=u'Acepta terminos y condiciones')
    fecharegistroestado = models.DateField(blank=True, null=True, verbose_name=u"Fecha Registro estado")
    estado = models.IntegerField(default=1, choices=ESTADO_APROBACION, verbose_name=u'Estado')
    observacion = models.TextField(default='', verbose_name=u"Observacion")
    aprobador = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE)
    emailenviado = models.BooleanField(default=False, verbose_name=u'Envio email')

    def __str__(self):
        return f'{self.nombreproyecto}'

    class Meta:
        verbose_name = u"personaprograma"
        verbose_name_plural = u"personasprogramas"
        ordering = ['nombreproyecto']