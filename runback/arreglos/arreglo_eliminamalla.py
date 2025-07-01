#!/usr/bin/env python
import csv
import os
import sys

import xlrd

from settings import USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA

# import urllib2
# Full path and name to your csv file
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
csv_filepathname3 = "problemas2021_corregido_g5.csv"
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

AsignaturaMalla.objects.filter(pk__in=(7284,7288,7293)).delete()
