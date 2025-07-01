#!/usr/bin/env python

import os
import sys
import time

import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from moodle import moodle

from django.db import connections
cursor = connections['moodle_db'].cursor()

#servidor
AGREGAR_ESTUDIANTE = True
AGREGAR_DOCENTE = True
AGREGAR_SILABO = True
AGREGAR_MODELO_NOTAS = True

parent_grupoid = 0
tipourl = 1
periodo = Periodo.objects.get(pk=112)
bgrupo = moodle.BuscarCategoriasid(periodo, tipourl,periodo.categoria)

if bgrupo:
    if 'id' in bgrupo[0]:
        parent_grupoid = bgrupo[0]['id']
contador = 0
if parent_grupoid > 0:
    """"
    CREANDO EL PERIODO ACADEMICO EL ID SE CONFIGURA EN VARIABLES GLABALES
    """
    bperiodo = moodle.BuscarCategorias(periodo, tipourl, periodo.idnumber())
    parent_periodoid = 0
    if bperiodo:
        if 'id' in bperiodo[0]:
            parent_periodoid= bperiodo[0]['id']
    else:
        bperiodo = moodle.CrearCategorias(periodo, tipourl, periodo.__str__(), periodo.idnumber(),  periodo.nombre, parent=parent_grupoid)
        parent_periodoid = bperiodo[0]['id']
    print('Periodo lectivo: %s' % periodo)
    if parent_periodoid > 0:
        """"
        CREANDO LAS COORDINACIONES
        """
        cordinaciones = Coordinacion.objects.filter(id__in=[1, 3], carrera__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(nivel__periodo=periodo, status=True).distinct()).distinct().exclude(id=9)
        # cordinaciones = Coordinacion.objects.filter(carrera__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(nivel__periodo=periodo).distinct()).distinct()
        for coordinacion in cordinaciones:
            idnumber_coordinacion = u'%s-COR%s' % (periodo.idnumber(), coordinacion.id)
            bcoordinacion = moodle.BuscarCategorias(periodo, tipourl, idnumber_coordinacion)
            parent_coordinacionid = 0
            if bcoordinacion:
                if 'id' in bcoordinacion[0]:
                    parent_coordinacionid = bcoordinacion[0]['id']
            else:
                bcoordinacion = moodle.CrearCategorias(periodo, tipourl, coordinacion, idnumber_coordinacion, coordinacion.nombre, parent=parent_periodoid)
                parent_coordinacionid = bcoordinacion[0]['id']
            print('**Facultad: %s' % coordinacion)
            if parent_coordinacionid > 0:
                """"
                CREANDO LAS CARRERAS
                """
                # carreras = Carrera.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(nivel__periodo=periodo, asignaturamalla__malla__carrera__coordinacion=coordinacion).distinct()).distinct().exclude(modalidad=3)
                carreras = Carrera.objects.filter(pk__in=[1, 3])
                for carrera in carreras:
                    idnumber_carrera = u'%s-COR%s-CARR%s' % (periodo.idnumber(), coordinacion.id, carrera.id)
                    bcarrera = moodle.BuscarCategorias(periodo, tipourl, idnumber_carrera)
                    parent_carreraid = 0
                    if bcarrera:
                        if 'id' in bcarrera[0]:
                            parent_carreraid = bcarrera[0]['id']
                    else:
                        bcarrera = moodle.CrearCategorias(periodo, tipourl, carrera, idnumber_carrera, carrera.nombre, parent=parent_coordinacionid)
                        parent_carreraid = bcarrera[0]['id']
                    print('****Carrera: %s' % carrera)
                    if parent_carreraid > 0:
                        """"
                        CREANDO LOS NIVELES DE MALLA
                        """

                        niveles = NivelMalla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__nivelmalla').filter(id__in=[31801, 33261, 31809, 31808, 31833, 31832],nivel__periodo=periodo, asignaturamalla__malla__carrera=carrera, status=True).distinct()).distinct()
                        for semestre in niveles:
                            idnumber_semestre = u'%s-COR%s-CARR%s-NIVEL%s' % (periodo.idnumber(), coordinacion.id, carrera.id, semestre.id)
                            bsemestre = moodle.BuscarCategorias(periodo, tipourl, idnumber_semestre)
                            categoryid = 0
                            if bsemestre:
                                if 'id' in bsemestre[0]:
                                    categoryid = bsemestre[0]['id']
                            else:
                                bsemestre = moodle.CrearCategorias(periodo, tipourl, semestre, idnumber_semestre, semestre.nombre, parent=parent_carreraid)
                                categoryid = bsemestre[0]['id']
                            print('******Semestre: %s' % semestre)
                            if categoryid > 0:
                                """"
                                CREANDO LOS CURSOS
                                """
                                cursos = Materia.objects.filter(id__in=[31801, 33261, 31809, 31808, 31833, 31832] ,status=True, nivel__periodo=periodo,asignaturamalla__nivelmalla=semestre, asignaturamalla__malla__carrera=carrera).order_by('asignatura__nombre', 'inicio', 'identificacion', 'id').exclude(nivel__sesion__id=13)
                                for curso in cursos:
                                    idnumber_curso = u'%s-COR%s-CARR%s-NIVEL%s-CURS%s' % ( periodo.idnumber(), coordinacion.id, carrera.id, semestre.id, curso.id)
                                    bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
                                    if not bcurso:
                                        bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
                                    numsections = 23
                                    planificacionclasesilabo = curso.planificacionclasesilabo_materia_set.filter(status=True)
                                    if planificacionclasesilabo:
                                        numsections = planificacionclasesilabo[0].tipoplanificacion.detalle_planificacion().count()
                                    objetivocur = ObjetivoProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura__asignaturamalla=curso.asignaturamalla, programaanaliticoasignatura__activo=True, programaanaliticoasignatura__status=True)
                                    summary = u''
                                    if objetivocur:
                                        summary = objetivocur[0].descripcion
                                    startdate = int(time.mktime(curso.inicio.timetuple()))
                                    enddate = int(time.mktime(curso.fin.timetuple()))
                                    cursoid = 0
                                    if bcurso['courses']:
                                        if 'id' in bcurso['courses'][0]:
                                            cursoid = bcurso['courses'][0]['id']
                                    else:
                                        bcurso = moodle.CrearCursos(periodo, tipourl, u'%s' % curso.nombre_completo(), u'%s,[%s] - %s[%s]-SALUD' % (curso.asignatura.nombre,curso.identificacion, curso.paralelo, curso.id), categoryid , idnumber_curso, summary, startdate, enddate, numsections)
                                        cursoid = bcurso[0]['id']
                                    print('********Curso: %s' % curso)
                                    if cursoid > 0:
                                        if curso.idcursomoodle != cursoid:
                                            curso.idcursomoodle = cursoid
                                            curso.save()

                                        if AGREGAR_MODELO_NOTAS:
                                            try:
                                                curso.crear_actualizar_categoria_notas_curso()
                                            except:
                                                print('Error**------------------------------')

                                        if AGREGAR_SILABO:
                                            curso.crear_actualizar_silabo_curso()

                                        if AGREGAR_DOCENTE:
                                            curso.crear_actualizar_docente_curso(moodle, 1)

                                        if AGREGAR_ESTUDIANTE:
                                            try:
                                                curso.crear_actualizar_estudiantes_curso(moodle, 1)
                                            except Exception as ex:
                                                print('Error al crear estudiante %s' % ex)
#
