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
id_personal = [30010,27241,26996,865,29034,1244,17579,708,3725,25133,1917,19420,16493]
# id_personal = [902,8854,27989,23333,12130,9826,176203,6534,149169,20236,30085,20839,4896,26741,56557,22270,813,1683,25072]
# fechas = ['2022-09-13','2022-09-14','2022-09-15']
fechas = ['2022-12-09']
horas = ['07:58:34', '17:10:12']
horas2 = ['07:28:31', '16:11:15']
try:
    for id_persona in id_personal:
        for fecha in fechas:
            logdia = LogDia.objects.filter(persona_id=id_persona, fecha=fecha)
            if not logdia.exists():
                registrodia = LogDia(persona_id=id_persona,
                                     fecha=datetime.fromisoformat(fecha).date(),
                                     cantidadmarcadas=1)
                registrodia.save()
                if id_persona == 1244:
                    marcada = LogMarcada(logdia=registrodia,
                                         time=datetime.fromisoformat(fecha + ' ' + horas2[0]),
                                         secuencia=1
                                         )
                    marcada.save()
                    marcada = LogMarcada(logdia=registrodia,
                                         time=datetime.fromisoformat(fecha + ' ' + horas2[1]),
                                         secuencia=1
                                         )
                    marcada.save()
                else:
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
                if id_persona == 1244:
                    marcada = LogMarcada(logdia=registrodia,
                                         time=datetime.fromisoformat(fecha + ' ' + horas2[0]),
                                         secuencia=1
                                         )
                    marcada.save()
                    marcada = LogMarcada(logdia=registrodia,
                                         time=datetime.fromisoformat(fecha + ' ' + horas2[1]),
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
    # for id_persona in id_personal:
    #     if not id_persona == 25072:
    #         logdia = LogDia.objects.filter(persona_id=id_persona, fecha='2022-09-15')
    #         if not logdia.exists():
    #             registrodia = LogDia(persona_id=id_persona,
    #                                  fecha=datetime.fromisoformat('2022-09-15').date(),
    #                                  cantidadmarcadas=1)
    #             registrodia.save()
    #             marcada = LogMarcada(logdia=registrodia,
    #                                     time=datetime.fromisoformat('2022-09-15 07:58:34'),
    #                                     secuencia=1
    #                                 )
    #             marcada.save()
    #             marcada = LogMarcada(logdia=registrodia,
    #                                  time=datetime.fromisoformat('2022-09-15 17:10:12'),
    #                                  secuencia=1
    #                                  )
    #             marcada.save()
    #         else:
    #             marcada = LogMarcada(logdia=logdia[0],
    #                                  time=datetime.fromisoformat('2022-09-15 07:58:34'),
    #                                  secuencia=1
    #                                  )
    #             marcada.save()
    #             marcada = LogMarcada(logdia=logdia[0],
    #                                  time=datetime.fromisoformat('2022-09-15 17:10:12'),
    #                                  secuencia=1
    #                                  )
    #             marcada.save()
    #
    #     else:
    #         for fecha in fechas:
    #             logdia = LogDia.objects.filter(persona_id=id_persona, fecha=fecha)
    #             if not logdia.exists():
    #                 registrodia = LogDia(persona_id=id_persona,
    #                                      fecha=datetime.fromisoformat(fecha).date(),
    #                                      cantidadmarcadas=1)
    #                 registrodia.save()
    #                 marcada = LogMarcada(logdia=registrodia,
    #                                      time=datetime.fromisoformat(fecha + ' ' + horas[0]),
    #                                      secuencia=1
    #                                      )
    #                 marcada.save()
    #                 marcada = LogMarcada(logdia=registrodia,
    #                                      time=datetime.fromisoformat(fecha + ' ' + horas[1]),
    #                                      secuencia=1
    #                                      )
    #                 marcada.save()
    #             else:
    #                 marcada = LogMarcada(logdia=logdia[0],
    #                                      time=datetime.fromisoformat(fecha + ' ' + horas[0]),
    #                                      secuencia=1
    #                                      )
    #                 marcada.save()
    #                 marcada = LogMarcada(logdia=logdia[0],
    #                                      time=datetime.fromisoformat(fecha + ' ' + horas[1]),
    #                                      secuencia=1
    #                                      )
    #                 marcada.save()
except Exception as ex:
    pass

