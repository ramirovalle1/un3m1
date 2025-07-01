#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import time

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
from sagest.models import ControlMatriculaMoodle
try:
    periodo = Periodo.objects.get(id=99)

    miarchivo = openpyxl.load_workbook("../../filexlsx/2020/2s/mate2021-969-14-04-2021GB.xlsx")
    lista = miarchivo.get_sheet_by_name('Hoja1')
    totallista = lista.rows
    a=0
    for filas in totallista:
        a += 1
        if a > 1:
            username = filas[1].value.strip()
            nota=0
            categoria=0
            if Persona.objects.filter(usuario__username=username, status=True).exists():
                persona = Persona.objects.get(usuario__username=username, status=True)
                nota = float(filas[2].value)
                categoria = filas[3].value.strip().upper()
                mateid = int(filas[4].value)
                matricula = Matricula.objects.get(status=True, inscripcion__persona=persona, nivel__periodo=periodo, estado_matricula__in=[2,3])
                if MateriaAsignada.objects.filter(status=True, matricula=matricula, retiramateria=False, materia__asignatura_id=mateid).exists():
                    materiaasignada = MateriaAsignada.objects.get(status=True, matricula=matricula, retiramateria=False, materia__asignatura_id=mateid)
                    campo = materiaasignada.campo(categoria)
                    if campo:
                        if null_to_decimal(campo.valor) != float(nota):
                            actualizar_nota_planificacion(materiaasignada.id, categoria, nota)
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                            calificacion=nota)
                            auditorianotas.save()
                            print('%s %s %s' % (materiaasignada, categoria, nota))
                    else:
                        control = ControlMatriculaMoodle(
                            materia=materiaasignada.materia,
                            persona=persona
                        )
                        control.save()
            else:
                print("No se encontro el usuario %s *************************************"%username)
except Exception as ex:
    print('error: %s' % ex)
