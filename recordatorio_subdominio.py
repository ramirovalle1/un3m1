#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time

import openpyxl

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from inno.models import *
from sga.models import *
from sga.funciones import convertir_fecha,convertir_hora
import xlrd
from bd.models import *
from sga.funciones import *
from django.contrib.contenttypes.models import ContentType
try:
    hoy=datetime.now()
    subdominio=SubDominio.objects.filter(status=True,estado=1)
    for x in subdominio:
        if x.fecha_caduca_certificado:
            resta_certificado=x.fecha_caduca_certificado-hoy
            if resta_certificado.days <= 30:
                for user in User.objects.filter(groups__id=343):
                    persona=Persona.objects.get(usuario=user)
                    cuerpo = ('Buen día estimados se informa que la fecha del  %s esta a punto de terminar' % x.nombre)
                    notificacion = Notificacion(titulo="Recordatorio caducidad certificado",
                                                cuerpo=cuerpo,
                                                destinatario=persona,
                                                url='notificacion',
                                                content_type=ContentType.objects.get(app_label=SubDominio._meta.app_label,
                                                                                     model=SubDominio._meta.model_name),
                                                object_id=x.id,
                                                prioridad=1,
                                                app_label='sga',
                                                fecha_hora_visible=datetime.now() + timedelta(days=1)
                                                )
                    notificacion.save()
        if x.fecha_caduca_dominio:
            resta_dominio=x.fecha_caduca_dominio-hoy
            if resta_dominio.days <= 30:
                for user in User.objects.filter(groups__id=343):
                    persona = Persona.objects.get(usuario=user)
                    cuerpo = ('Buen día estimados se informa que la fecha del dominio %s esta a punto de terminar' % x.nombre)
                    notificacion = Notificacion(titulo="Recordatorio caducidad dominio",
                                                cuerpo=cuerpo,
                                                destinatario=persona,
                                                url='notificacion',
                                                content_type=ContentType.objects.get(app_label=SubDominio._meta.app_label,
                                                                                     model=SubDominio._meta.model_name),
                                                object_id=x.id,
                                                prioridad=1,
                                                app_label='sga',
                                                fecha_hora_visible=datetime.now() + timedelta(days=1)
                                                )
                    notificacion.save()
except Exception as ex:
    print(ex)

