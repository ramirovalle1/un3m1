#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.db import transaction

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
import xlrd
from time import sleep
from sga.models import *
from sagest.models import *
from datetime import date
from settings import PROFESORES_GROUP_ID
from sga.funciones import calculate_username, generar_usuario, fechatope, null_to_decimal
import xlwt
from xlwt import *
import unicodedata



try:
    with transaction.atomic():
        personas = Persona.objects.all()
        for p in personas:
            if p.usuario:
               p.emailinst = "{}@unemi.edu.ec".format(p.usuario.username.strip())
               p.save()
               print("{}@unemi.edu.ec".format(p.usuario.username))
except Exception as ex:
    print(ex)
    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))





