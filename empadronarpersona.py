# coding=utf-8
#!/usr/bin/env python

import os
import sys

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
import xlrd


def empadronarFacultad(coordinacionid):
    try:
        sede_por_defecto = SedesElectoralesPeriodo.objects.get(pk=12)
        evento = CabPadronElectoral.objects.get(pk=2, status=True)
        empadronadosperiodo = DetPersonaPadronElectoral.objects.filter(status=True, cab=evento).values_list('persona_id', flat=True)
        total = 0
        fechaactual = datetime.now()
        coordinacion = Coordinacion.objects.get(pk=coordinacionid)
        print('EMPADRONAR {}'.format(coordinacion.alias))
        # condeudapersonas = Rubro.objects.filter(matricula__isnull=False, matricula__inscripcion__coordinacion=coordinacion, matricula__nivel__periodo=evento.periodo, matricula__nivelmalla__in=[3, 4, 5, 6, 7, 8, 9, 10], matricula__cerrada=False, status=True, cancelado=False, fechavence__lt=fechaactual).distinct('persona').values_list('persona__id', flat=True)
        matricula = Matricula.objects.select_related('inscripcion').filter(inscripcion__coordinacion=coordinacion, status=True, nivel__periodo=evento.periodo, nivelmalla__in=[3, 4, 5, 6, 7, 8, 9, 10], retiradomatricula=False)
        lista_persona_excluidas = list(empadronadosperiodo)
        # lista_persona_excluidas = list(empadronadosperiodo) + list(condeudapersonas)
        sindeudapersonas = matricula.exclude(inscripcion__persona__in=(list(lista_persona_excluidas))).order_by('nivelmalla')
        print('TOTAL MATRICULADOS: {}'.format(matricula.count()))
        # print('TOTAL CON DEUDA: {}'.format(condeudapersonas.count()))
        print('TOTAL A EMPADRONAR: {}'.format(sindeudapersonas.count()))
        totalcargado = 0
        for per in sindeudapersonas:
            if not DetPersonaPadronElectoral.objects.filter(status=True, cab=evento, persona=per.inscripcion.persona).exists():
                # print('{} Carrera: {} Nivel: {}'.format(per.inscripcion.persona.__str__(), per.inscripcion.carrera, per.nivelmalla))
                padron = DetPersonaPadronElectoral(cab=evento, persona=per.inscripcion.persona, inscripcion=per.inscripcion, matricula=per, tipo=1)
                # lugarsede = PersonasSede.objects.filter(persona=per.inscripcion.persona).first()
                # if lugarsede:
                #     padron.lugarsede = lugarsede.sede
                # else:
                padron.lugarsede = sede_por_defecto
                padron.save()
                totalcargado += 1
        print('{} TOTAL EMPADRONADO: {}'.format(coordinacion.alias, totalcargado))
    except Exception as ex:
        print(ex)


def vincularSedePersonaDocente():
    workbook = xlrd.open_workbook("OCAS2023.xls")
    sheet = workbook.sheet_by_index(0)
    col_persona, col_cedula, col_lugar, col_nummesa = 1, 0, 2, 3
    linea, leidos, excluidos, nuevos = 1, 0, 0, 0
    print(f"Se vincularan sedes a {sheet.nrows - 1} docentes")
    evento = CabPadronElectoral.objects.get(pk=3, status=True)
    for rowx in range(sheet.nrows):
        if linea > 1:
            cols = sheet.row_values(rowx)
            with transaction.atomic():
                try:
                    cedula = cols[col_cedula]
                    lugar_mesa = ""
                    padronpersona = DetPersonaPadronElectoral.objects.filter(status=True, cab=evento, persona__cedula=cedula, tipo=2)
                    if padronpersona.exists():
                        # personap = padronpersona.first()
                        personap.lugar = lugar_mesa
                        # personap.save()
                        leidos += 1
                    else:
                        if Persona.objects.filter(status=True, cedula=cedula).exists():
                            personap = Persona.objects.filter(status=True, cedula=cedula).first()
                            det = DetPersonaPadronElectoral(cab=evento, persona=personap, tipo=2, lugar=lugar_mesa, lugarsede_id=12)
                            det.save()
                            nuevos += 1
                        else:
                            excluidos += 1
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
        linea += 1
    print('Cargados: {}'.format(leidos))
    print('Excluidos: {}'.format(excluidos))
    print('Nuevos: {}'.format(nuevos))


def vincularSedePersonaAdministrativo():
    workbook = xlrd.open_workbook("OCAS2023.xls")
    sheet = workbook.sheet_by_index(1)
    col_persona, col_cedula, col_lugar, col_nummesa = 1, 0, 2, 3
    linea, leidos, excluidos, nuevos = 1, 0, 0, 0
    print(f"Se vincularan sedes a {sheet.nrows - 1} administrativos")
    evento = CabPadronElectoral.objects.get(pk=3, status=True)
    for rowx in range(sheet.nrows):
        if linea > 1:
            cols = sheet.row_values(rowx)
            with transaction.atomic():
                try:
                    cedula = cols[col_cedula]
                    lugar_mesa = ""
                    padronpersona = DetPersonaPadronElectoral.objects.filter(status=True, cab=evento, persona__cedula=cedula, tipo=3)
                    if padronpersona.exists():
                        # personap = padronpersona.first()
                        personap.lugar = lugar_mesa
                        # personap.save()
                        leidos += 1
                    else:
                        if Persona.objects.filter(status=True, cedula=cedula).exists():
                            personap = Persona.objects.filter(status=True, cedula=cedula).first()
                            det = DetPersonaPadronElectoral(cab=evento, persona=personap, tipo=3, lugar=lugar_mesa, lugarsede_id=12)
                            det.save()
                            nuevos += 1
                        else:
                            excluidos += 1
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
        linea += 1
    print('Cargados: {}'.format(leidos))
    print('Excluidos: {}'.format(excluidos))
    print('Nuevos: {}'.format(nuevos))


def vincularSedePersonaEstudiantesMilagro():
    workbook = xlrd.open_workbook("empadronadosrector2022.xls")
    sheet = workbook.sheet_by_index(2)
    col_persona, col_cedula, col_lugar, col_nummesa = 0, 1, 2, 3
    linea, leidos, excluidos = 1, 0, 0
    excluidoslist = []
    print(f"Se vincularan sedes a {sheet.nrows - 1} estudiantes")
    evento = CabPadronElectoral.objects.get(pk=2, status=True)
    for rowx in range(sheet.nrows):
        if linea > 1:
            cols = sheet.row_values(rowx)
            with transaction.atomic():
                try:
                    cedula = cols[col_cedula]
                    lugar_mesa = "{} - {}".format(cols[col_lugar], cols[col_nummesa])
                    padronpersona = DetPersonaPadronElectoral.objects.filter(status=True, cab=evento, persona__cedula=cedula, tipo=1)
                    if padronpersona.exists():
                        personap = padronpersona.first()
                        personap.lugar = lugar_mesa
                        personap.lugarsede_id = 1
                        personap.save()
                        leidos += 1
                    else:
                        excluidos += 1
                        excluidoslist.append(cedula)
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
        linea += 1
    print('Cargados: {}'.format(leidos))
    print('Excluidos: {}'.format(excluidos))
    print('Lista Excluidos: {}'.format(excluidoslist))


def vincularSedePersonaEstudiantesFueraMilagro():
    workbook = xlrd.open_workbook("filexlsx/empadronadosrector2022.xlsx")
    sheet = workbook.sheet_by_index(3)
    col_persona, col_cedula, col_lugar, col_espacio, col_nummesa = 0, 1, 2, 3, 4
    linea, leidos, excluidos = 1, 0, 0
    excluidoslist = []
    print(f"Se vincularan sedes a {sheet.nrows - 1} estudiantes")
    evento = CabPadronElectoral.objects.get(pk=2, status=True)
    totalReal = DetPersonaPadronElectoral.objects.filter(status=True, cab=evento, tipo=1).exclude(lugarsede_id=1)
    print('Total Real: {}'.format(totalReal.count()))
    for rowx in range(sheet.nrows):
        if linea > 1:
            cols = sheet.row_values(rowx)
            with transaction.atomic():
                try:
                    cedula = cols[col_cedula]
                    if len(cols[col_espacio]) > 4:
                        lugar_mesa = "{} - {} - {}".format(cols[col_lugar], cols[col_espacio], cols[col_nummesa])
                    else:
                        lugar_mesa = "{} {} - {}".format(cols[col_lugar], cols[col_espacio], cols[col_nummesa])
                    print(lugar_mesa)
                    padronpersona = DetPersonaPadronElectoral.objects.filter(status=True, cab=evento, persona__cedula=cedula, tipo=1)
                    if padronpersona.exists():
                        personap = padronpersona.first()
                        lugarsede = PersonasSede.objects.filter(persona=personap.persona).first()
                        if lugarsede:
                            personap.lugarsede = lugarsede.sede
                        personap.lugar = lugar_mesa
                        personap.save()
                        leidos += 1
                    else:
                        excluidos += 1
                        excluidoslist.append(cedula)
                except Exception as ex:
                    print(ex)
                    transaction.set_rollback(True)
        linea += 1
    print('Cargados: {}'.format(leidos))
    print('Excluidos: {}'.format(excluidos))
    print('Lista Excluidos: {}'.format(excluidoslist))


vincularSedePersonaDocente()