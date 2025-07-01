
import os
import random
import shutil
import sys
from time import sleep

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

import xlwt
from webpush import send_user_notification
from xlwt import easyxf
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

import pyqrcode
from django.core.files.base import ContentFile

import time
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_name_bitacora

import uuid
from hashlib import md5
from datetime import datetime
from settings import  SITE_STORAGE, DEBUG
from sga.templatetags.sga_extras import encrypt
from sga.models import DetPersonaPadronElectoral, CabPadronElectoral, FotoPersona
from sga.adm_padronelectoral import generar_qr_padronelectoral

try:
    detpersons = DetPersonaPadronElectoral.objects.filter(cab=3, tipo=1, inscripcion__coordinacion__id=4)
    ahora = datetime.now()
    url_path = 'https://sga.unemi.edu.ec'
    total_, totcount = detpersons.count(), 1
    for person in detpersons:
        print(f"{total_}/{totcount} {person}")
        result = generar_qr_padronelectoral(person, detalle_id=person.id)
        if result.get('isSuccess', {}):
            aData = result.get('data', {})
            url_pdf = aData.get('url_pdf', None)
            if url_pdf == None:
                raise NameError(u"No se encontro url del documento")
            link_pdf = f"https://sga.unemi.edu.ec/media/{url_pdf}"
            person.pdf = url_pdf
            person.save()
        totcount += 1
except Exception as ex:
    print(ex)
