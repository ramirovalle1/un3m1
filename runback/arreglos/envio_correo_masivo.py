#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import openpyxl
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
from sga.models import *
# from balcon.models import *
from moodle import moodle
from posgrado.models import FormatoCarreraIpec
print(u"Inicio")

def envio_correo_masivo():
    try:
        formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=195, status=True)[0]
        archivoadjunto = formatocorreo.archivo
        miarchivo = openpyxl.load_workbook("lista_promocion_edubas1.xlsx")
        lista = miarchivo.get_sheet_by_name('Hoja 1')
        totallista = lista.rows
        a = 0
        for filas in totallista:
            a += 1
            if a > 2:
                if filas[1].value:
                    correo = str(filas[1].value).lower()
                    lista_correo=[]
                    lista_correo.append(correo)
                    nombres = str(filas[0].value)
                    print("Procesando: ", nombres)
                    send_html_mail("¡Tu oportunidad de ascender en el escalafón docente!",
                                   "emails/promocion_maestrias.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'persona': u"%s" %nombres,
                                    },
                                   lista_correo,
                                   [],[archivoadjunto],
                                   cuenta=CUENTAS_CORREOS[23][1]
                                   )
                    print('Correo enviado (%s)' % (nombres))
                    time.sleep(3)
        print("Correos enviados...")
    except Exception as ex:
        print('error: %s' % ex)

def envio_correo_prueba():
    formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=195, status=True)[0]
    archivoadjunto = formatocorreo.archivo
    lista_correo = []
    lista_correo.append('jplacesc@unemi.edu.ec')
    # lista_correo.append('kpalaciosz@unemi.edu.ec')
    # lista_correo.append('amirandar4@unemi.edu.ec')
    # lista_correo.append('hllerenaa@unemi.edu.ec')
    print("Procesando: ", "JUSSIBETH TATIANA PLACES CHUNGATA")
    send_html_mail("¡Tu oportunidad de ascender en el escalafón docente!",
                   "emails/promocion_maestrias.html",
                   {'sistema': u'SGA - UNEMI',
                    'fecha': datetime.now().date(),
                    'hora': datetime.now().time(),
                    'persona': "JUSSIBETH TATIANA PLACES CHUNGATA",
                    },
                   lista_correo,
                   [],[archivoadjunto],
                   cuenta=CUENTAS_CORREOS[24][1]
                   )
    print("Correo enviado: ", "JUSSIBETH TATIANA PLACES CHUNGATA")

envio_correo_masivo()
