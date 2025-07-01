#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime

import openpyxl
from django.db import transaction



SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()



from postulate.models import Convocatoria, Partida
from sga.models import Carrera, AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion

c = 0
with transaction.atomic():
    try:

        miarchivo = openpyxl.load_workbook("MATRICES_PERFILES_2022.xlsx")
        lista = miarchivo.get_sheet_by_name('Lockedata')
        totallista = lista.rows
        a = 0
        for filas in totallista:
            hoy = datetime.now().date()
            a += 1
            if a > 2:
                print(filas[0].value.strip())
                carr = Carrera.objects.get(id=int(filas[20].value))
                titulo = filas[23].value
                if filas[24].value:
                    titulo = "%s - %s" % (titulo, filas[24].value)
                if filas[25].value:
                    titulo = "%s - %s" % (titulo, filas[25].value)
                campoamplio = None
                campoespecifico = None
                campodetallado = None
                if AreaConocimientoTitulacion.objects.filter(status=True, nombre__icontains=filas[3].value.strip()).exists():
                    campoamplio = AreaConocimientoTitulacion.objects.filter(status=True, nombre__icontains=filas[3].value.strip()).first()
                    if SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=campoamplio, nombre__icontains=filas[4].value.strip()).exists():
                        campoespecifico = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=campoamplio, status=True, nombre__icontains=filas[4].value.strip()).first()
                        if SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento =campoespecifico,  status=True, nombre__icontains=filas[4].value.strip()).exists():
                            campodetallado = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento =campoespecifico, status=True, nombre__icontains=filas[5].value.strip()).first()

                part = Partida(titulo=titulo, convocatoria_id=int(filas[1].value), descripcion=filas[10].value, ano=int(filas[9].value), codpartida=filas[0].value, carrera=carr, nivel=3, modalidad=filas[21].value, dedicacion=filas[28].value, jornada=filas[22].value, rmu=float(filas[29].value))
                part.save()
                if campoamplio:
                    part.campoamplio.add(campoamplio)
                    if campoespecifico:
                        part.campoespecifico.add(campoespecifico)
                        if campodetallado:
                            part.campodetallado.add(campodetallado)
            c+=1
    except Exception as e:
        transaction.set_rollback(True)
        print(e)
        print('Error  {} en linea {} en registro numero {}'.format(e, sys.exc_info()[-1].tb_lineno, str(c)))