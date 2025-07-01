#!/usr/bin/env python

import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import Periodo, DiasNoLaborable, FaltasMateriaPeriodo, ProfesorMateria, Clase, LeccionGrupo

from datetime import datetime
from django.db import transaction
from sagest.models import date, timedelta

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def convertirfecha(fecha):
    try:
        return date(int(fecha[6:10]),int(fecha[3:5]),int(fecha[0:2]))
    except Exception as ex:
        return datetime.now().date()

def convertirfechahora(fecha):
    try:
        return datetime(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]),int(fecha[11:13]),int(fecha[14:16]),int(fecha[17:19]))
    except Exception as ex:
        return datetime.now()


def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]),int(fecha[5:7]),int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()

# cron de falta asistencia
@transaction.atomic()
def faltasmateriaperiodo():
    fechatope = datetime.now().date() - timedelta(days=2)
    periodos=Periodo.objects.filter(inicio__lte=fechatope, fin__gte=fechatope)
    for periodo in periodos:
        if DiasNoLaborable.objects.filter(periodo=periodo, fecha=fechatope).exists():
            diasnolaborables = DiasNoLaborable.objects.filter(periodo=periodo, fecha=fechatope).order_by('fecha')[0]
            coordinacion = None
            if diasnolaborables.coordinacion:
                coordinacion = diasnolaborables.coordinacion

            carrera = None
            if diasnolaborables.carrera:
                carrera = diasnolaborables.carrera

            nivelmalla = None
            if diasnolaborables.nivelmalla:
                nivelmalla = diasnolaborables.nivelmalla
            else:
                if coordinacion and carrera and nivelmalla:
                    FaltasMateriaPeriodo.objects.filter(periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion_carrera__coordinacion=coordinacion, materia__asignaturamalla__malla__carrera=carrera, materia__asignaturamalla__nivelmalla=nivelmalla, fecha=fechatope).delete()
                else:
                    if coordinacion and carrera:
                        FaltasMateriaPeriodo.objects.filter(periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion_carrera__coordinacion=coordinacion, materia__asignaturamalla__malla__carrera=carrera, fecha=fechatope).delete()
                    else:
                        if coordinacion:
                            FaltasMateriaPeriodo.objects.filter(periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion_carrera__coordinacion=coordinacion, fecha=fechatope).delete()
                        else:
                            FaltasMateriaPeriodo.objects.filter(periodo=periodo, fecha=fechatope).delete()

        inicio_aux=''
        fin_aux=''
        profesormaterias=ProfesorMateria.objects.filter(materia__nivel__periodo=periodo)
        diasnolaborables = DiasNoLaborable.objects.filter(periodo=periodo, fecha=fechatope).order_by('fecha')
        claseshorarios = Clase.objects.filter(materia__nivel__periodo=periodo, activo=True).distinct().order_by('materia__profesormateria__profesor', 'turno__comienza')
        n = 1
        for profesormateria in ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, desde__lte=fechatope, hasta__gte=fechatope):
            # print(n)
            n += 1
            profesorid = profesormateria.profesor.id
            claseshorario = claseshorarios.filter(materia__profesormateria__profesor__id=profesorid)

            inicio = profesormateria.materia.inicio
            fin = profesormateria.materia.fin
            fecha = fechatope
            bandera = False
            if inicio <= fecha:
                if fin >= fecha:
                    bandera = True
                    inicio = fecha
                    fin = fecha

            if bandera:
                if not (inicio == inicio_aux and fin == fin_aux):
                    fechas = []
                    if inicio == fin:
                        fechas.append(inicio)
                        dia_semana = inicio.isoweekday()
                        claseshorario = claseshorario.filter(dia=dia_semana)
                    else:
                        for dia in daterange(fechatope, (fechatope + timedelta(days=1))):
                            fechas.append(dia)
                profesormateria.faltas_docente(periodo, inicio, fin, diasnolaborables, claseshorario, fechas)

    periodos=Periodo.objects.filter(inicio__lte=fechatope, fin__gte=fechatope)
    for periodo in periodos:
        for diasnolaborables in DiasNoLaborable.objects.filter(periodo=periodo):
            coordinacion = None
            if diasnolaborables.coordinacion:
                coordinacion = diasnolaborables.coordinacion

            carrera = None
            if diasnolaborables.carrera:
                carrera = diasnolaborables.carrera

            nivelmalla = None
            if diasnolaborables.nivelmalla:
                nivelmalla = diasnolaborables.nivelmalla
            else:
                if coordinacion and carrera and nivelmalla:
                    FaltasMateriaPeriodo.objects.filter(periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion_carrera__coordinacion=coordinacion, materia__asignaturamalla__malla__carrera=carrera, materia__asignaturamalla__nivelmalla=nivelmalla, fecha=diasnolaborables.fecha).delete()
                else:
                    if coordinacion and carrera:
                        FaltasMateriaPeriodo.objects.filter(periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion_carrera__coordinacion=coordinacion, materia__asignaturamalla__malla__carrera=carrera, fecha=diasnolaborables.fecha).delete()
                    else:
                        if coordinacion:
                            FaltasMateriaPeriodo.objects.filter(periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion_carrera__coordinacion=coordinacion, fecha=diasnolaborables.fecha).delete()
                        else:
                            FaltasMateriaPeriodo.objects.filter(periodo=periodo, fecha=diasnolaborables.fecha).delete()

        for faltas in FaltasMateriaPeriodo.objects.filter(periodo=periodo):
            if LeccionGrupo.objects.filter(fecha=faltas.fecha, turno=faltas.turno, profesor=faltas.materia.profesor_principal()).exists():
                faltas.delete()

    print('listo')

faltasmateriaperiodo()