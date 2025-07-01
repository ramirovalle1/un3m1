# -*- coding: UTF-8 -*-
from _decimal import Decimal

from django import template

from settings import TIPO_RESPUESTA_EVALUACION
from sga.funciones import fechaletra_corta, fields_model, field_default_value_model, trimestre, null_to_decimal, \
    convertir_fecha
from sga.models import Notificacion
from datetime import datetime, timedelta, date


class My_Notificacion(Notificacion):
    
    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_Notificacion, self).__init__(*args, **kwargs)

    def prueba_rever(self):
        return False

    def save(self, *args, **kwargs):
        super(My_Notificacion, self).save(*args, **kwargs)
