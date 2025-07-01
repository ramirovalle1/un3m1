#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.http import HttpResponse

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

from datetime import datetime
from sagest.models import LogDia, LogMarcada, MarcadasDia, RegistroMarcada
id_personal = [121078]
fechasentradasalida = ['2022-11-10','2022-11-14']
fechassalida = ['2022-11-09']
fechasentrada = ['2022-11-15','2022-11-16']
horas = ['07:58:34', '17:10:12']
try:
    for id_persona in id_personal:
        for fecha in fechasentradasalida:
            logdia = LogDia.objects.filter(persona_id=id_persona, fecha=fecha, status=True)
            if not logdia.exists():
                registrodia = LogDia(persona_id=id_persona,
                                     fecha=datetime.fromisoformat(fecha).date(),
                                     cantidadmarcadas=1,
                                     jornada_id=85,
                                     procesado=True)
                registrodia.save()
                marcada = LogMarcada(logdia=registrodia,
                                     time=datetime.fromisoformat(fecha + ' ' + horas[0]),
                                     secuencia=1
                                     )
                marcada.save()
                marcada = LogMarcada(logdia=registrodia,
                                     time=datetime.fromisoformat(fecha + ' ' + horas[1]),
                                     secuencia=1
                                     )
                marcada.save()
            else:
                marcada = LogMarcada(logdia=logdia[0],
                                     time=datetime.fromisoformat(fecha + ' ' + horas[0]),
                                     secuencia=1
                                     )
                marcada.save()
                marcada = LogMarcada(logdia=logdia[0],
                                     time=datetime.fromisoformat(fecha + ' ' + horas[1]),
                                     secuencia=1
                                     )
                marcada.save()

        for fecha in fechasentrada:
            logdia = LogDia.objects.filter(persona_id=id_persona, fecha=fecha, status=True)
            if not logdia.exists():
                registrodia = LogDia(persona_id=id_persona,
                                     fecha=datetime.fromisoformat(fecha).date(),
                                     cantidadmarcadas=1,
                                     jornada_id=85,
                                     procesado=True)
                registrodia.save()
                marcada = LogMarcada(logdia=registrodia,
                                     time=datetime.fromisoformat(fecha + ' ' + horas[0]),
                                     secuencia=1
                                     )
                marcada.save()
                # marcada = LogMarcada(logdia=registrodia,
                #                      time=datetime.fromisoformat(fecha + ' ' + horas[1]),
                #                      secuencia=1
                #                      )
                # marcada.save()
            else:
                marcada = LogMarcada(logdia=logdia[0],
                                     time=datetime.fromisoformat(fecha + ' ' + horas[0]),
                                     secuencia=1
                                     )
                marcada.save()
                # marcada = LogMarcada(logdia=logdia[0],
                #                      time=datetime.fromisoformat(fecha + ' ' + horas[1]),
                #                      secuencia=1
                #                      )
                # marcada.save()

        for fecha in fechassalida:
            logdia = LogDia.objects.filter(persona_id=id_persona, fecha=fecha, status=True)
            if not logdia.exists():
                registrodia = LogDia(persona_id=id_persona,
                                     fecha=datetime.fromisoformat(fecha).date(),
                                     cantidadmarcadas=1,
                                     jornada_id=85,
                                     procesado=True)
                registrodia.save()
                marcada = LogMarcada(logdia=registrodia,
                                     time=datetime.fromisoformat(fecha + ' ' + horas[1]),
                                     secuencia=1
                                     )
                marcada.save()
            else:
                marcada = LogMarcada(logdia=logdia[0],
                                     time=datetime.fromisoformat(fecha + ' ' + horas[1]),
                                     secuencia=1
                                     )
                marcada.save()
                # marcada = LogMarcada(logdia=logdia[0],
                #                      time=datetime.fromisoformat(fecha + ' ' + horas[1]),
                #                      secuencia=1
                #                      )
                # marcada.save()
except Exception as ex:
    pass

