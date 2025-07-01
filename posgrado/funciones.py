#!/usr/bin/env python

import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()


def enviar_sms_telegram(mensaje, url_archivo=None):
    import requests
    json_arr = []
    try:
        api = '7478991777:AAFGUvzFBW61tyb4IXpSdO17NN5ZcNzEaD4'
        nfuentesp = '1098544136'
        chats = [nfuentesp]
        for chat_id in chats:
            # Enviar mensaje
            data = {'chat_id': chat_id, 'text': mensaje, 'parse_mode': 'HTML'}
            url = f"https://api.telegram.org/bot{api}/sendMessage"
            json_arr.append(requests.post(url, data).json())

            # Enviar archivo si existe
            if url_archivo:
                url_envio = f"https://api.telegram.org/bot{api}/sendDocument"
                # Descargar el archivo desde la URL
                response = requests.get(url_archivo)
                if response.status_code == 200:
                    # El archivo se ha descargado correctamente
                    file_data = response.content

                    # Usamos 'files' para enviar el archivo descargado
                    files = {'document': ('archivo.xlsx', file_data)}
                    data = {'chat_id': chat_id, 'caption': mensaje}

                    # Enviar el archivo a Telegram
                    response_telegram = requests.post(url_envio, data=data, files=files)
                    return response_telegram.json()
    except Exception as ex:
        print(f"Error al enviar mensaje o archivo: {str(ex)}")
    return json_arr
