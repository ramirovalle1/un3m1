#!/usr/bin/env python

import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from django.db import transaction
from sagest.models import Rubro

def enviar_mensaje_bot_telegram(mensaje):
    import requests
    json_arr=[]
    try:
        api = '1954045154:AAFK8CJo2Wr3nWpS-acBRgchZzcz2qxUKSU'
        cgomez, clocke, rviteri = '900543432', '838621184', '2006141724'
        chats = [clocke, rviteri]
        for x in chats:
            data = {'chat_id': x, 'text': mensaje, 'parse_mode': 'HTML'}
            url = "https://api.telegram.org/bot{}/sendMessage".format(api)
            json_arr.append(requests.post(url, data).json())
    except Exception as ex:
        print("TELEGRAM ERROR" + str(ex))
    return json_arr

try:
    cont = 0
    rubros = Rubro.objects.filter(cancelado=False, epunemi=False,
                                 relacionados__isnull=False, status=True)
    for rubro in rubros:
        relacionado = Rubro.objects.get(pk=rubro.relacionados_id)
        if relacionado:
            if relacionado.cancelado:
                rubro.relacionados_id=None
                rubro.save()
                cont += 1
        else:
            rubro.relacionados_id=None
            rubro.save()
            cont += 1
    print("TOTAL DESVINCULADOS: %s " % cont )
except Exception as ex:
    textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
    enviar_mensaje_bot_telegram(textoerror)
    transaction.set_rollback(True)


