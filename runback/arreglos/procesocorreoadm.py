#!/usr/bin/env python
import os
import sys
import openpyxl
# import urllib2

# Full path and name to your csv file
import unicodedata
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record

import xlrd
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
from django.http import HttpResponse
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
from setuptools.windows_support import hide_file
from urllib3 import request
from docx import Document

from sga.tasks import conectar_cuenta, send_html_mail, conectar_cuenta2

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
from settings import SERVER_RESPONSE
from sga.models import *

__author__ = 'Unemi'

def enviocorreomatriculados():
    titulo = "Confirmación de Matrícula Admisión 1S-2020"

    matriculas=Matricula.objects.filter(nivel__periodo_id=95, status=True).exclude(inscripcion__carrera_id__in=[87,65,171,83,82,67])
    #matriculas=Matricula.objects.filter(id=242462)
    #matriculas = Inscripcion.objects.filter(periodo_id=6, status=True, estado__in=[1, 2], notificado=False).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
    total = matriculas.count()
    procesado = 1
    cuenta = 8

    for m in matriculas:
        mimalla = m.inscripcion.malla_inscripcion()
        if mimalla.malla.inicio.year == 2020:
            print("Enviando ", procesado, " de ", total)
            print("Procesando: ", cuenta, " - ", m.inscripcion.persona.identificacion(), " - ", m.inscripcion)
            if m.inscripcion.persona.lista_emails_envio():
                send_html_mail( titulo,
                                "emails/notificacionmatricula.html",
                                {'sistema': u'SGA - UNEMI',
                                'fecha': datetime.now().date(),
                                'hora': datetime.now().time(),
                                'persona': m.inscripcion.persona,
                                },
                                m.inscripcion.persona.lista_emails_envio(),
                                [],
                                cuenta=CUENTAS_CORREOS[cuenta][1]
                               )
            # # Temporizador para evitar que se bloquee el servicion de gmail
            time.sleep(5)
            cuenta += 1
            if cuenta >= 14:
                cuenta = 8
            procesado += 1


    print("Correos enviados...")

enviocorreomatriculados()
