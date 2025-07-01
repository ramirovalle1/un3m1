# coding=utf-8
# !/usr/bin/env python

import os
import sys

import openpyxl

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from datetime import datetime, timedelta
from django.db import transaction
from sga.models import Materia, Clase, Leccion, LeccionGrupo, AsistenciaLeccion
from sga.funciones import variable_valor
from django.db import transaction
from django.db.models import Q, Case, When, Value, CharField
from sga.models import *
from sagest.models import Rubro
from voto.models import *
from postulate.models import *
import xlrd


def importarmejorespuntuados(excel):
    linea, leidos, excluidos = 1, 0, 0
    try:
        print('--------------------------------------------------------')
        print(excel)
        wb = openpyxl.load_workbook(excel)
        worksheet = wb.worksheets[0]
        excluidoslist = []
        for row in worksheet.iter_rows():
            currentValues = [str(cell.value) for cell in row]
            if linea > 1:
                cedula = currentValues[6]
                fecha = convertir_fecha_invertida(currentValues[10].split(' ')[0])
                hora = currentValues[11].replace('h', ':').replace('H', ':')
                lugar = "ZOOM {}".format(currentValues[12])
                obs = currentValues[13]
                print(f"{cedula}")
                # print('{}, {}: {} - {}'.format(cedula, lugar, fecha, hora))
                if PersonaAplicarPartida.objects.filter(status=True, partida__convocatoria__vigente=True, persona__cedula=cedula).exists():
                    persona_ = PersonaAplicarPartida.objects.filter(status=True, partida__convocatoria__vigente=True, persona__cedula=cedula).first()
                    if ConvocatoriaPostulante.objects.filter(persona=persona_, status=True).exists():
                        conv = ConvocatoriaPostulante.objects.filter(persona=persona_, status=True).first()
                    else:
                        conv = ConvocatoriaPostulante(persona=persona_)
                    conv.tema = persona_.partida.temadisertacion
                    # conv.fechaasistencia = fecha
                    # conv.horasistencia = hora
                    # conv.lugar = lugar
                    # conv.observacion = obs
                    conv.save()
                else:
                    excluidoslist.append({'cedula': cedula, 'linea': linea})
            linea += 1
        print('Cargados: {}'.format(leidos))
        print('Excluidos: {}'.format(excluidos))
        print('Lista Excluidos: {}'.format(excluidoslist))
    except Exception as ex:
        print('Error en linea {} - {}'.format(linea, excel))
        print(ex)


importarmejorespuntuados('filexlsx/POSTULANTES_2.xlsx')
