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

# from django.db import connections
# cursor = connections['moodle_db'].cursor()
from Moodle_Funciones import crearhtmlphpmoodle

# servidor
AGREGAR_ESTUDIANTE = False
AGREGAR_DOCENTE = True
AGREGAR_SILABO = True
AGREGAR_MODELO_NOTAS = True
TIPO_AULA_VIRTUAL = False
parent_grupoid = 0
tipourl = 3
# ID:121 ABRIL- MAYO 2021
try:
    periodo = Periodo.objects.get(pk=336)
    ano = '%s_%s-%s_%s' % (periodo.inicio.year, periodo.inicio.month, periodo.fin.year, periodo.fin.month)
    # PRESENCIAL
    # if TIPO_AULA_VIRTUAL == True:
    #     bgrupo = moodle.BuscarCategoriasid(periodo, tipourl, 2)
    # else:
    #     bgrupo = moodle.BuscarCategoriasid(periodo, tipourl, 18)

    # EN LINEA
    bgrupo = moodle.BuscarCategoriasid(periodo, tipourl, 2)

    if bgrupo:
        if 'id' in bgrupo[0]:
            parent_grupoid = bgrupo[0]['id']

    contador = 0
    print(bgrupo)

    if parent_grupoid > 0:
        """"
        CREANDO EL PERIODO ACADEMICO EL ID SE CONFIGURA EN VARIABLES GLABALES
        """
        bperiodo = moodle.BuscarCategorias(periodo, tipourl, periodo.idnumber())
        # if TIPO_AULA_VIRTUAL == True:
        #     parent_periodoid = 962
        # else:
        #     parent_periodoid = 962

        if bperiodo:
            if 'id' in bperiodo[0]:
                parent_periodoid = bperiodo[0]['id']
        else:
            bperiodo = moodle.CrearCategorias(periodo, tipourl, periodo.__str__(), periodo.idnumber(), periodo.nombre,
                                              parent=parent_grupoid)
            parent_periodoid = bperiodo[0]['id']
        print('Periodo lectivo: %s' % periodo)
        if parent_periodoid > 0:

            cordinaciones = Coordinacion.objects.filter(
                pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera__coordinacion__id').filter(
                    nivel__periodo=periodo, status=True,
                    asignaturamalla__malla__carrera__coordinacion__id__lte=5).distinct()).distinct()
            for coordinacion in cordinaciones:
                noti = Notificacion(titulo='Error',
                                    cuerpo=coordinacion,
                                    destinatario_id=29898, url="",
                                    prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1),
                                    tipo=2, en_proceso=False, error=True)
                noti.save()
                # NUMBER EN LINEA
                idnumber_coordinacion = u'%s-COR%s-LINE' % (periodo.idnumber(), coordinacion.id)
                bcoordinacion = moodle.BuscarCategorias(periodo, tipourl, idnumber_coordinacion)
                parent_coordinacionid = 0
                if bcoordinacion:
                    if 'id' in bcoordinacion[0]:
                        parent_coordinacionid = bcoordinacion[0]['id']
                else:
                    bcoordinacion = moodle.CrearCategorias(periodo, tipourl, coordinacion, idnumber_coordinacion,
                                                           coordinacion.nombre, parent=parent_periodoid)
                    parent_coordinacionid = bcoordinacion[0]['id']
                print('**Facultad: %s' % coordinacion)
                if parent_coordinacionid > 0:

                    """"CREANDO LAS CARRERAS"""
                    # Se exlcuye mallas de inglés
                    eMallasIngles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
                    carreras = Carrera.objects.filter(
                        pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(
                            nivel__periodo=periodo, asignaturamalla__malla__carrera__coordinacion=coordinacion,
                            status=True, asignaturamalla__malla__modalidad__id__in=[3]).exclude(asignaturamalla__malla_id__in=eMallasIngles).distinct()).distinct()
                    for carrera in carreras:
                        idnumber_carrera = u'%s-COR%s-CARR%s' % (periodo.idnumber(), coordinacion.id, carrera.id)
                        bcarrera = moodle.BuscarCategorias(periodo, tipourl, idnumber_carrera)
                        parent_carreraid = 0
                        if bcarrera:
                            if 'id' in bcarrera[0]:
                                parent_carreraid = bcarrera[0]['id']
                        else:
                            bcarrera = moodle.CrearCategorias(periodo, tipourl, carrera, idnumber_carrera,
                                                              carrera.nombre, parent=parent_coordinacionid)
                            parent_carreraid = bcarrera[0]['id']
                        print('****Carrera: %s' % carrera)
                        if parent_carreraid > 0:

                            """"CREANDO LOS NIVELES DE MALLA"""
                            niveles = NivelMalla.objects.filter(
                                pk__in=Materia.objects.values_list('asignaturamalla__nivelmalla').filter(
                                    nivel__periodo=periodo, status=True,
                                    asignaturamalla__malla__carrera__coordinacion=coordinacion, asignaturamalla__malla__modalidad__id__in=[3]).distinct()).distinct()
                            for semestre in niveles:
                                try:
                                    idnumber_semestre = u'%s-COR%s-CARR%s-NIVEL%s' % (
                                    periodo.idnumber(), coordinacion.id, carrera.id, semestre.id)
                                    bsemestre = moodle.BuscarCategorias(periodo, tipourl, idnumber_semestre)
                                    categoryid = 0
                                    if bsemestre:
                                        if 'id' in bsemestre[0]:
                                            categoryid = bsemestre[0]['id']
                                    else:
                                        bsemestre = moodle.CrearCategorias(periodo, tipourl, semestre,
                                                                           idnumber_semestre, semestre.nombre,
                                                                           parent=parent_carreraid)
                                        categoryid = bsemestre[0]['id']
                                    print('******Semestre: %s' % semestre)
                                    if categoryid > 0:

                                        """"
                                        CREANDO LOS CURSOS
                                        """
                                        # excludemateria = Materia.objects.values_list('id', flat=True).filter( nivel__periodo=periodo, asignaturamalla__nivelmalla_id__in=[7, 8], asignaturamalla__malla__carrera__coordinacion__id__in=[1]).distinct()
                                        cursos = Materia.objects.filter(nivel__periodo=periodo,
                                                                        asignaturamalla__nivelmalla=semestre,
                                                                        asignaturamalla__malla__carrera=carrera,
                                                                        status=True,
                                                                        asignaturamalla__malla__carrera__coordinacion=coordinacion, asignaturamalla__malla__modalidad__id__in=[3]).exclude(
                                            asignaturamalla__malla_id__in=eMallasIngles).distinct().order_by(
                                            'asignatura__nombre', 'inicio', 'identificacion', 'id')
                                        # cursos = cursos.exclude(id__in=excludemateria)
                                        for curso in cursos:

                                            if curso.coordinacion().id == 9:
                                                idnumber_periodo = u'PER%s-%s' % (periodo.id, ano)
                                                idnumber_curso = u'%s-COR%s-CARR%s-NIVEL%s-CURS%s' % (
                                                idnumber_periodo, coordinacion.id, carrera.id, semestre.id, curso.id)
                                            else:
                                                idnumber_curso = u'%s-COR%s-CARR%s-NIVEL%s-CURS%sP' % (
                                                periodo.idnumber(), coordinacion.id, carrera.id, semestre.id, curso.id)
                                            # print(idnumber_curso)
                                            # bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
                                            cursoid = curso.buscar_cursomoodle(idnumber_curso)
                                            # print(bcurso)
                                            # if not bcurso:
                                            #     bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
                                            # cursoid = 0
                                            # print(bcurso)
                                            # if bcurso['courses']:
                                            # if cursoid > 0:
                                            #     # print(bcurso['courses'][0])
                                            #     if 'id' in bcurso['courses'][0]:
                                            #         cursoid = bcurso['courses'][0]['id']
                                            #         # print(cursoid)
                                            #     else:
                                            #         cursoid = curso.idcursomoodle
                                            # else:
                                            # if curso.idcursomoodle > 0:
                                            #     cursoid = curso.idcursomoodle
                                            if cursoid == 0:
                                                numsections = 12
                                                planificacionclasesilabo = curso.planificacionclasesilabo_materia_set.filter(
                                                    status=True)
                                                objetivocur = ObjetivoProgramaAnaliticoAsignatura.objects.filter(
                                                    programaanaliticoasignatura__asignaturamalla=curso.asignaturamalla,
                                                    programaanaliticoasignatura__activo=True,
                                                    programaanaliticoasignatura__status=True)
                                                summary = u''
                                                if objetivocur:
                                                    summary = objetivocur[0].descripcion
                                                startdate = int(time.mktime(curso.inicio.timetuple()))
                                                enddate = int(time.mktime(curso.fin.timetuple()))
                                                bcurso = moodle.CrearCursosTarjeta(periodo, tipourl,
                                                                                   u'%s' % curso.nombre_completo(),
                                                                                   u'%s,[%s] - %s[%s] - P' % (
                                                                                   curso.asignatura.nombre,
                                                                                   curso.identificacion, curso.paralelo,
                                                                                   curso.id), categoryid,
                                                                                   idnumber_curso, summary, startdate,
                                                                                   enddate, numsections)
                                                print(bcurso)
                                                cursoid = bcurso[0]['id']

                                                if curso.idcursomoodle != cursoid:
                                                    curso.idcursomoodle = cursoid
                                                    curso.modelotarjeta = True
                                                    curso.save()

                                            if AGREGAR_MODELO_NOTAS:
                                                try:
                                                    # curso.crear_actualizar_sub_categoria_notas_curso()
                                                    curso.crear_actualizar_categoria_notas_curso()
                                                except Exception as ex:
                                                    print('Error**------------------------------')

                                            if AGREGAR_SILABO:
                                                curso.poner_estilo_tarjeta_curso_moodle()
                                                curso.crear_actualizar_silabo_curso_virtual_segundo_nivel()
                                                # crearhtmlphpmoodle(curso.id)
                                            print('********Curso: %s' % curso)

                                            if cursoid > 0:
                                                if curso.idcursomoodle != cursoid:
                                                    curso.idcursomoodle = cursoid
                                                    curso.modelotarjeta = True
                                                    curso.save()

                                                if AGREGAR_DOCENTE:
                                                    curso.crear_actualizar_docente_curso(moodle, 1)

                                                if AGREGAR_ESTUDIANTE:
                                                    try:
                                                        curso.crear_actualizar_estudiantes_curso(moodle, 1)
                                                    except Exception as ex:
                                                        print('Error al crear estudiante %s' % ex)
                                #
                                except Exception as ex:
                                    print('Error**------------------------------ %s' % ex)
                                    print('Error  {} en linea {} '.format(ex, sys.exc_info()[-1].tb_lineno))
                                    pass




except Exception as ex:
    print('error: %s' % ex)
    noti = Notificacion(titulo='Error',
                        cuerpo='Ha ocurrido un error {} - Error en la linea {}'.format(
                            ex, sys.exc_info()[-1].tb_lineno),
                        destinatario_id=29898, url="",
                        prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1),
                        tipo=2, en_proceso=False, error=True)
    noti.save()