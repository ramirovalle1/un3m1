import os
import sys
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
from datetime import datetime, timedelta
from django.db import transaction
from sga.models import Materia, Clase, Leccion, LeccionGrupo, AsistenciaLeccion, CamposTitulosPostulacion
from sga.funciones import variable_valor
import xlrd
from postulate.models import Partida, PersonaAplicarPartida, PersonaFormacionAcademicoPartida, PartidaTribunal
from sga.models import *
from sagest.models import *
from django.db.models import Sum, F, FloatField, IntegerField
from django.db.models.functions import Coalesce
from settings import MEDIA_ROOT, BASE_DIR
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side, colors
from django.http import HttpResponse
from sga.models import Modulo
from gdocumental.models import *
from bd.models import *
from moodle import moodle
from zeep import Client

try:
    url_ = f'https://sga.unemi.edu.ec/soap/wu/cobro'
    cliente = Client(url_)
    if cliente.service.Login("westernunion", "Unemi1234"):
        print(f'Credenciales Correctas')
    else:
        print(f'Credenciales Incorrectas')

    if cliente.service.prodece(0,0):
        print('Pago Realizado')
except Exception as ex:
    print(f'{ex}')
