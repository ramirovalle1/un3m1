#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import random

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from datetime import datetime, timedelta
from sagest.models import LogDia, LogMarcada, PermisoInstitucionalDetalle, TrabajadorDiaJornada, DetalleJornada
from faceid.functions import calculando_marcadasotro
from sga.models import DiasNoLaborable
id_personal = [ 20539,10730,825,75935]
fechahoy = datetime.now().date()
fin_semana=fechahoy.weekday()
try:
    if not DiasNoLaborable.objects.filter(fecha=fechahoy).exclude(periodo__isnull=False).exists():
        if fin_semana < 5:
            for id_persona in id_personal:
                ePermisoInstitucionalDetalles = PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita_id=id_persona, status=True)
                if not ePermisoInstitucionalDetalles.values("id").filter(fechainicio__gte=fechahoy, fechafin__lte=fechahoy).exists():
                    idjornada= TrabajadorDiaJornada.objects.values('jornada_id').filter(persona_id=id_persona, status=True).order_by('jornada_id').last()
                    eDetalleJornadas = DetalleJornada.objects.filter(jornada_id=idjornada['jornada_id'], status=True, dia=(fechahoy.weekday() + 1) )
                    if eDetalleJornadas.values("id").exists():
                        try:
                            eLogDia = LogDia.objects.get(persona_id=id_persona, fecha=fechahoy)
                        except ObjectDoesNotExist:
                            eLogDia = LogDia(persona_id=id_persona,
                                             fecha=fechahoy)
                        eLogDia.jornada_id= idjornada['jornada_id']
                        eLogDia.save()
                        if eDetalleJornadas.values("id").count() == 1:
                            eDetalleJornada = eDetalleJornadas.first()
                            minutes_1 = random.randint(0, 5)
                            secuencia_1 = 1
                            horainicio = eDetalleJornada.horainicio - timedelta(minutes=minutes_1)
                            try:
                                eLogMarcada_1 = LogMarcada.objects.get(logdia=eLogDia, secuencia=secuencia_1)
                            except ObjectDoesNotExist:
                                eLogMarcada_1 = LogMarcada(logdia=eLogDia,
                                                           time=eDetalleJornada.horainicio,
                                                           secuencia=secuencia_1)
                            eLogMarcada_1.save()
                            minutes_2 = random.randint(0, 59)
                            secuencia_2 = 1
                            horafin = eDetalleJornada.horafin + timedelta(minutes=minutes_2)
                            try:
                                eLogMarcada_2 = LogMarcada.objects.get(logdia=eLogDia, secuencia=secuencia_2)
                            except ObjectDoesNotExist:
                                eLogMarcada_2 = LogMarcada(logdia=eLogDia,
                                                           secuencia=secuencia_2,
                                                           time=eDetalleJornada.horafin)
                            eLogMarcada_2.save()
                        else:
                            secuencia = 1
                            for eDetalleJornada in eDetalleJornadas:
                                horainicio = eDetalleJornada.horainicio
                                horafin = eDetalleJornada.horafin
                                if secuencia == 1:
                                    minutes = random.randint(0, 5)
                                    horainicio = eDetalleJornada.horainicio - timedelta(minutes=minutes)
                                if secuencia == 3:
                                    minutes = random.randint(0, 5)
                                    horainicio = eDetalleJornada.horainicio - timedelta(minutes=minutes)

                                try:
                                    eLogMarcada_1 = LogMarcada.objects.get(logdia=eLogDia, secuencia=secuencia)
                                except ObjectDoesNotExist:
                                    eLogMarcada_1 = LogMarcada(logdia=eLogDia,
                                                               secuencia=secuencia,
                                                               time=horainicio)
                                eLogMarcada_1.save()
                                secuencia += 1

                                if secuencia == 2:
                                    minutes = random.randint(0,5)
                                    horafin = eDetalleJornada.horafin + timedelta(minutes=minutes)

                                if secuencia == 4:
                                    minutes = random.randint(0, 59)
                                    horafin = eDetalleJornada.horafin + timedelta(minutes=minutes)
                                try:
                                    eLogMarcada_2 = LogMarcada.objects.get(logdia=eLogDia, secuencia=secuencia)
                                except ObjectDoesNotExist:
                                    eLogMarcada_2 = LogMarcada(logdia=eLogDia,
                                                               secuencia=secuencia,
                                                               time=eDetalleJornada.horafin)
                                eLogMarcada_2.save()
                                secuencia += 1
                        eLogDia.cantidadmarcadas = LogMarcada.objects.values("id").filter(logdia=eLogDia).count()
                        calculando_marcadasotro(eLogDia.fecha, eLogDia.fecha, eLogDia.solicita)
                        eLogDia.save()
except Exception as ex:
    pass

