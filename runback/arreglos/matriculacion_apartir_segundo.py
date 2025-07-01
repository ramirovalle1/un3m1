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
from Moodle_Funciones import *
from datetime import date
from settings import PROFESORES_GROUP_ID, DEBUG, ADMINISTRADOR_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, \
    DIAS_MATRICULA_EXPIRA
from sga.funciones import calculate_username, generar_usuario, fechatope, null_to_decimal
import xlwt
from xlwt import *
import unicodedata



def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()


from moodle import moodle


def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha

import openpyxl
archivo = "filexlsx/marzo_sept_2022_matriculados_en_linea_exclude_tics_turismo.xlsx"
miarchivo = openpyxl.load_workbook(archivo)
lista = miarchivo.get_sheet_by_name('resultados')
linea = 1
periodo = Periodo.objects.get(pk=126)
totallista = lista.rows
for filas in totallista:
    if linea > 1:
        id_inscripcion = int(filas[0].value)
        print(id_inscripcion)
        bandera = True
        if Inscripcion.objects.filter(pk=id_inscripcion).exists():
            inscripcion = Inscripcion.objects.get(pk=id_inscripcion)
            if not inscripcion.persona.tiene_otro_titulo():
                sesion = inscripcion.sesion
                carrera = inscripcion.carrera
                modalidad = inscripcion.modalidad
                cordinacion_alias = str(carrera.coordinacion_set.all()[0].alias)
                inscripcion.malla_inscripcion()
                inscripcion.actualizar_nivel()
                nivel = Nivel.objects.get(periodo=periodo, sesion=sesion, paralelo__icontains=cordinacion_alias)
                asignatura_malla=RecordAcademico.objects.values_list('asignaturamalla_id',flat=True).filter(inscripcion=inscripcion,asignaturamalla__nivelmalla__id__lte=int(filas[2].value), aprobada=True).distinct()
                if Materia.objects.filter(nivel__periodo=periodo, paralelomateria_id=int(filas[1].value),
                                                      asignaturamalla__malla__carrera=carrera, nivel__sesion=sesion,
                                                      asignaturamalla__nivelmalla__id=int(filas[2].value)).exclude(asignaturamalla_id__in=asignatura_malla).exists():
                    if not inscripcion.matricula_periodo(periodo):
                        matricula = Matricula(inscripcion=inscripcion,
                                              nivel=nivel,
                                              pago=False,
                                              iece=False,
                                              becado=False,
                                              # porcientobeca=0,
                                              fecha=convertirfecha2('2022-05-09'),
                                              hora=datetime.now().time(),
                                              fechatope=fechatope(datetime.now().date()),
                                              automatriculapregrado=True,
                                              fechaautomatriculapregrado=convertirfecha2('2022-05-09'))
                        matricula.save()
                    else:
                        matricula = Matricula.objects.get(inscripcion=inscripcion, nivel=nivel)



                    for materia in Materia.objects.filter(nivel__periodo=periodo, paralelomateria_id=int(filas[1].value),
                                                          asignaturamalla__malla__carrera=carrera, nivel__sesion=sesion,
                                                          asignaturamalla__nivelmalla__id=int(filas[2].value)).exclude(asignaturamalla_id__in=asignatura_malla):
                        if not MateriaAsignada.objects.filter(matricula=matricula, materia=materia).exists():
                            matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                            materiaasignada = MateriaAsignada(matricula=matricula,
                                                              materia=materia,
                                                              notafinal=0,
                                                              asistenciafinal=0,
                                                              cerrado=False,
                                                              matriculas=matriculas,
                                                              observaciones='',
                                                              estado_id=NOTA_ESTADO_EN_CURSO)
                            materiaasignada.save()
                            materiaasignada.asistencias()
                            materiaasignada.evaluacion()
                            materiaasignada.mis_planificaciones()
                            materiaasignada.save()
                        else:
                            materiaasignada = MateriaAsignada.objects.filter(matricula=matricula, materia=materia)[0]
                        # profesormateria = materia.profesormateria_set.filter(activo=True, tipoprofesor=2)
                        # if profesormateria.exists():
                        #     if profesormateria[0].gruposprofesormateria_set.filter(status=True).count() > 0:
                        #         grupoprofesor = GruposProfesorMateria.objects.filter(profesormateria=profesormateria[0], paralelopractica=int(cols[3]))[0]
                        #         if not AlumnosPracticaMateria.objects.filter(profesormateria=profesormateria[0], materiaasignada=materiaasignada, grupoprofesor=grupoprofesor).exists():
                        #             alumnospracticas = AlumnosPracticaMateria(profesormateria=profesormateria[0], materiaasignada=materiaasignada, grupoprofesor=grupoprofesor)
                        #             alumnospracticas.save()
                        #     print(u"matriculado (%s) en la materia %s " % (inscripcion.persona, materia))
                        # else:
                        #     print(u"ya estaba matriculado (%s) en la materia %s " % (inscripcion.persona, materia))

                    inscripcion.actualizar_nivel()
                    matricula.actualiza_matricula()
                    matricula.inscripcion.actualiza_estado_matricula()
                    matricula.grupo_socio_economico(1)
                    matricula.calcula_nivel()
                    print(u"matriculado %s" % matricula)
    linea += 1
    print(linea)

"""nivelesperiodoanterios = Nivel.objects.filter(periodo=periodoanterior, materia__asignaturamalla__nivelmalla_id=ID_NIVELMALLA_PERIODOANTERIOR, modalidad_id__in=ID_MODALIDAD, sesion_id__in=ID_SESION, materia__asignaturamalla__malla__carrera__in=ID_CARRERA).exclude(nivellibrecoordinacion__coordinacion_id__in=[6, 7, 8, 9, 10, 11, 12]).distinct()

for nivelanterior in nivelesperiodoanterios:
    print("****************************************NIVEL ANTERIOR**************************************************")
    print("%s - %s" % (nivelanterior.id, nivelanterior.__str__()))
    carrrerasanterior = Carrera.objects.filter(pk__in=Materia.objects.filter(nivel=nivelanterior, asignaturamalla__malla__carrera_id__in=ID_CARRERA).values_list('asignaturamalla__malla__carrera_id')).distinct()
    for carreraanterior in carrrerasanterior:
        print("*** CARRERA: %s - %s" % (carreraanterior.id, carreraanterior.nombre))
        materiasanteriores_ofertadas = Materia.objects.filter(asignaturamalla__malla__carrera=carreraanterior,
                                                              nivel=nivelanterior,
                                                              asignaturamalla__nivelmalla_id=ID_NIVELMALLA_PERIODOANTERIOR,
                                                              nivel__modalidad_id__in=ID_MODALIDAD,
                                                              nivel__sesion_id__in=ID_SESION).distinct()

        sesionesanterior = Sesion.objects.filter(pk__in=nivelesperiodoanterios.values_list('sesion_id')).distinct()
        for sesionanterior in sesionesanterior:
            print("****** SECCIÓN: %s - %s" % (sesionanterior.id, sesionanterior.nombre))
            paralelosanterior = Paralelo.objects.filter(pk__in=materiasanteriores_ofertadas.filter(nivel__sesion=sesionanterior).values_list('paralelomateria_id'))
            materiasactuales_ofertadas = Materia.objects.filter(asignaturamalla__malla__carrera=carreraanterior,
                                                                nivel__periodo=periodoactual,
                                                                asignaturamalla__nivelmalla_id=ID_NIVELMALLA_PERIODOACTUAL,
                                                                nivel__modalidad_id__in=ID_MODALIDAD,
                                                                nivel__sesion=sesionanterior).distinct()
            #paralelosactuales = Paralelo.objects.filter(pk__in=materiasactuales_ofertadas.filter(nivel__sesion=sesionanterior).values_list('paralelomateria_id'))

            #if paralelosanterior.count() == paralelosactuales.count():
            for paraleloanterior in paralelosanterior:
                print("********* PARALELO: %s - %s" % (paraleloanterior.id, paraleloanterior.nombre))
                materiasanteriores = materiasanteriores_ofertadas.filter(paralelomateria=paraleloanterior)
                matriculadosanteriores = Matricula.objects.filter(materiaasignada__materia__in=materiasanteriores, materiaasignada__estado_id=1, nivel=nivelanterior, materiaasignada__materia__paralelomateria=paraleloanterior, materiaasignada__materia__asignaturamalla__nivelmalla_id=ID_NIVELMALLA_PERIODOANTERIOR, materiaasignada__matriculas__lte=1)
                for matriculadoanterior in matriculadosanteriores:
                    materiasaprobadasanteriores = MateriaAsignada.objects.filter(matricula=matriculadoanterior, estado_id=1)
                    if materiasaprobadasanteriores.count() == materiasanteriores.count():
                        print("********* MATRICULADO: %s - %s % s" % (matriculadoanterior.inscripcion.id, matriculadoanterior.inscripcion.persona.cedula, matriculadoanterior.inscripcion.persona))
                            #Materia.objects.filter(nivel__periodo=periodoactual, asignaturamalla__nivelmalla_id=ID_NIVELMALLA_PERIODOACTUAL, nivel__sesion=sesionanterior, paralelomateria=)"""
