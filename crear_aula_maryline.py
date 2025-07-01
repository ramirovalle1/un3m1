#!/usr/bin/env python

import os
import sys
import time

import warnings

import xlsxwriter
from django.db import transaction


warnings.filterwarnings('ignore', message='Unverified HTTPS request')

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *

from sagest.models import Rubro, Pago, PagoLiquidacion
#from moodle import moodle

# from django.db import connections
# cursor = connections['moodle_db'].cursor()
#from Moodle_Funciones import crearhtmlphpmoodle
#
# periodo = Periodo.objects.get(pk=153)
#
# cursos = Materia.objects.filter(nivel__periodo=periodo).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id').exclude(idcursomoodle=0)
# imagenes = ImagenMoodle.objects.values_list("id", flat=True).filter(status=True)
# imagenr = random.choice(imagenes)
# imagen = ImagenMoodle.objects.get(pk=imagenr)

# for curso in cursos:
#     if curso.idcursomoodle != 0:
#         cursoid = curso.idcursomoodle
#
#         sql = """select id from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
#         cursor.execute(sql)
#         buscar = cursor.fetchall()
#         contextid = buscar[0][0]
#
#         sql = """INSERT INTO mooc_files (contenthash,pathnamehash,contextid,component,filearea,itemid,filepath,filename,
#          userid,filesize, mimetype,status,source, author,license,timecreated,timemodified,sortorder,referencefileid)
#          VALUES(NULL,NULL,'%s','course','overviewfiles','0','/','%s','2','%s','image/jpeg','0','%s','%admin321','unknown',%s',%s',0,NULL )"""\
#               % (contextid,nombrearchivo, tamaniarchivo, nombrearchivo,fecha,fecha)
#         cursor.execute(sql)
# #
# #NUEVO FIN
#
#
# #servidor
# AGREGAR_ESTUDIANTE = False
# AGREGAR_DOCENTE = False
# AGREGAR_SILABO = False
# AGREGAR_MODELO_NOTAS = True
# TIPO_AULA_VIRTUAL = True
# parent_grupoid = 0
# tipourl = 1
# # ID:121 ABRIL- MAYO 2021
# periodo = Periodo.objects.get(pk=126)
#
# # PRESENCIAL
# # if TIPO_AULA_VIRTUAL == True:
# #     bgrupo = moodle.BuscarCategoriasid(periodo, tipourl, 2)
# # else:
# #     bgrupo = moodle.BuscarCategoriasid(periodo, tipourl, 18)
#
# # EN LINEA
# bgrupo = moodle.BuscarCategoriasid(periodo, tipourl, 2)
#
# if bgrupo:
#     if 'id' in bgrupo[0]:
#         parent_grupoid = bgrupo[0]['id']
# contador = 0
# print(bgrupo)
# if parent_grupoid > 0:
#     """"
#     CREANDO EL PERIODO ACADEMICO EL ID SE CONFIGURA EN VARIABLES GLABALES
#     """
#     bperiodo = moodle.BuscarCategorias(periodo, tipourl, periodo.idnumber())
#     # if TIPO_AULA_VIRTUAL == True:
#     #     parent_periodoid = 962
#     # else:
#     #     parent_periodoid = 962
#
#     if bperiodo:
#         if 'id' in bperiodo[0]:
#             parent_periodoid = bperiodo[0]['id']
#     else:
#         bperiodo = moodle.CrearCategorias(periodo, tipourl, periodo.__str__(), periodo.idnumber(), periodo.nombre, parent=parent_grupoid)
#         parent_periodoid = bperiodo[0]['id']
#     print('Periodo lectivo: %s' % periodo)
#     if parent_periodoid > 0:
#         """"
#         CREANDO LAS COORDINACIONES
#
#         """
#         # cordinaciones = Coordinacion.objects.filter(pk=6).distinct()
#         cordinaciones = Coordinacion.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera__coordinacion__id').filter(id__in=[53339] , nivel__periodo=periodo).distinct()).distinct()
#         for coordinacion in cordinaciones:
#             # NUMBER EN LINEA
#             if TIPO_AULA_VIRTUAL == True:
#                 idnumber_coordinacion = u'%s-COR%s-LINEA' % (periodo.idnumber(), coordinacion.id)
#             else:
#                 idnumber_coordinacion = u'%s-COR%s' % (periodo.idnumber(), coordinacion.id)
#             bcoordinacion = moodle.BuscarCategorias(periodo, tipourl, idnumber_coordinacion)
#             parent_coordinacionid = 0
#             if bcoordinacion:
#                 if 'id' in bcoordinacion[0]:
#                     parent_coordinacionid = bcoordinacion[0]['id']
#             else:
#                 bcoordinacion = moodle.CrearCategorias(periodo, tipourl, coordinacion, idnumber_coordinacion, coordinacion.nombre, parent=parent_periodoid)
#                 parent_coordinacionid = bcoordinacion[0]['id']
#             print('**Facultad: %s' % coordinacion)
#             if parent_coordinacionid > 0:
#                 """"
#                 CREANDO LAS CARRERAS
#                 """
#                 if TIPO_AULA_VIRTUAL == True:
#                     carreras = Carrera.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(id__in=[53339] , nivel__periodo=periodo, asignaturamalla__malla__carrera__coordinacion=coordinacion).distinct()).distinct()
#                 else:
#                     carreras = Carrera.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(id__in=[53339] , nivel__periodo=periodo, asignaturamalla__malla__carrera__coordinacion=coordinacion).distinct()).distinct()
#
#                 for carrera in carreras:
#                     idnumber_carrera = u'%s-COR%s-CARR%s' % (periodo.idnumber(), coordinacion.id, carrera.id)
#                     bcarrera = moodle.BuscarCategorias(periodo, tipourl, idnumber_carrera)
#                     parent_carreraid = 0
#                     if bcarrera:
#                         if 'id' in bcarrera[0]:
#                             parent_carreraid = bcarrera[0]['id']
#                     else:
#                         bcarrera = moodle.CrearCategorias(periodo, tipourl, carrera, idnumber_carrera, carrera.nombre, parent=parent_coordinacionid)
#                         parent_carreraid = bcarrera[0]['id']
#                     print('****Carrera: %s' % carrera)
#                     if parent_carreraid > 0:
#                         """"
#                         CREANDO LOS NIVELES DE MALLA
#                         """
#                         # niveles = NivelMalla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__nivelmalla').filter(nivel__periodo=periodo).distinct()).distinct()
#                         # niveles = NivelMalla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__nivelmalla').filter(nivel__periodo=periodo).distinct()).distinct()
#                         # niveles = NivelMalla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__nivelmalla').filter(nivel__periodo=periodo).exclude(id__in=[54719,54714,54709]).distinct()).distinct()
#                         niveles = NivelMalla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__nivelmalla').filter(id__in=[53339] , nivel__periodo=periodo).distinct()).distinct()
#                         for semestre in niveles:
#                             idnumber_semestre = u'%s-COR%s-CARR%s-NIVEL%s' % (periodo.idnumber(), coordinacion.id, carrera.id, semestre.id)
#                             bsemestre = moodle.BuscarCategorias(periodo, tipourl, idnumber_semestre)
#                             categoryid = 0
#                             if bsemestre:
#                                 if 'id' in bsemestre[0]:
#                                     categoryid = bsemestre[0]['id']
#                             else:
#                                 bsemestre = moodle.CrearCategorias(periodo, tipourl, semestre, idnumber_semestre, semestre.nombre, parent=parent_carreraid)
#                                 categoryid = bsemestre[0]['id']
#                             print('******Semestre: %s' % semestre)
#                             if categoryid > 0:
#                                 """"
#                                 CREANDO LOS CURSOS
#                                 """
#                                 # excludemateria = Materia.objects.values_list('id', flat=True).filter( nivel__periodo=periodo, asignaturamalla__nivelmalla_id__in=[7, 8], asignaturamalla__malla__carrera__coordinacion__id__in=[1]).distinct()
#                                 cursos = Materia.objects.filter(id__in=[53339] , nivel__periodo=periodo, asignaturamalla__nivelmalla=semestre, asignaturamalla__malla__carrera=carrera).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
#                                 # cursos = cursos.exclude(id__in=excludemateria)
#                                 for curso in cursos:
#                                     idnumber_curso = u'%s-COR%s-CARR%s-NIVEL%s-CURS%sP' % (periodo.idnumber(), coordinacion.id, carrera.id, semestre.id, curso.id)
#                                     # print(idnumber_curso)
#                                     bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
#                                     # print(bcurso)
#                                     if not bcurso:
#                                         bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
#                                     cursoid = 0
#                                     # print(bcurso)
#                                     if bcurso['courses']:
#                                         # print(bcurso['courses'][0])
#                                         if 'id' in bcurso['courses'][0]:
#                                             cursoid = bcurso['courses'][0]['id']
#                                             # print(cursoid)
#                                         else:
#                                             cursoid = curso.idcursomoodle
#                                     else:
#                                         numsections = 12
#                                         planificacionclasesilabo = curso.planificacionclasesilabo_materia_set.filter(
#                                             status=True)
#                                         objetivocur = ObjetivoProgramaAnaliticoAsignatura.objects.filter(
#                                             programaanaliticoasignatura__asignaturamalla=curso.asignaturamalla,
#                                             programaanaliticoasignatura__activo=True,
#                                             programaanaliticoasignatura__status=True)
#                                         summary = u''
#                                         if objetivocur:
#                                             summary = objetivocur[0].descripcion
#                                         startdate = int(time.mktime(curso.inicio.timetuple()))
#                                         enddate = int(time.mktime(curso.fin.timetuple()))
#                                         bcurso = moodle.CrearCursosTarjeta(periodo, tipourl, u'%s' % curso.nombre_completo(), u'%s,[%s] - %s[%s] - P' % (curso.asignatura.nombre, curso.identificacion, curso.paralelo, curso.id), categoryid, idnumber_curso, summary, startdate, enddate, numsections)
#                                         print(bcurso)
#                                         cursoid = bcurso[0]['id']
#                                     print('********Curso: %s' % curso)
#
#                                     if cursoid > 0:
#                                         if curso.idcursomoodle != cursoid:
#                                             curso.idcursomoodle = cursoid
#                                             curso.modelotarjeta = True
#                                             curso.save()
#                                         if AGREGAR_MODELO_NOTAS:
#                                             try:
#                                                 # curso.crear_actualizar_sub_categoria_notas_curso()
#                                                 curso.crear_actualizar_categoria_notas_curso()
#                                             except Exception as ex:
#                                                 print('Error**------------------------------')
#
#                                         if AGREGAR_DOCENTE:
#                                             curso.crear_actualizar_docente_curso(moodle, 1)
#
#                                         if AGREGAR_SILABO:
#                                             curso.poner_estilo_tarjeta_curso_moodle()
#                                             # if curso.asignaturamalla.nivelmalla_id != 2:
#                                             #     curso.crear_actualizar_silabo_curso_virtual()
#                                             # else:
#                                             curso.crear_actualizar_silabo_curso_virtual_segundo_nivel()
#                                             # crearhtmlphpmoodle(curso.id)
#
#                                         if AGREGAR_ESTUDIANTE:
#                                             try:
#                                                 curso.crear_actualizar_estudiantes_curso(moodle, 1)
#                                             except Exception as ex:
#                                                 print('Error al crear estudiante %s' % ex)
# #
# try:
#     periodo = 126
#     inscritos = CapCabeceraSolicitudDocente.objects.filter(status=True).distinct()
#     for inscrito in inscritos:
#         profesor = inscrito.participante.profesor()
#         if profesor:
#             carrera = profesor.carrera_comun_periodo(periodo)
#             facultad = None
#             if carrera:
#                 facultad = carrera.mi_coordinacion2()
#             inscrito.facultad_id = facultad
#             inscrito.carrera = carrera
#             inscrito.save()
# except Exception as ex:
#      print('error: %s' % ex)


# periodoactual = 153
# try:
#     distributivo = ProfesorDistributivoHoras.objects.filter(status = True, periodo_id=periodoactual, profesor_id=3461)
#     for dis in distributivo:
#         if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=118, criteriodocenciaperiodo__periodo=periodoactual, distributivo = dis).exists():
#             distant = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=118, criteriodocenciaperiodo__periodo=periodoactual, distributivo= dis)
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=121, criteriodocenciaperiodo__periodo=periodoactual, distributivo_id=dis).exists():
#                 horas = distant.horas
#                 porcprincipal = null_to_decimal(horas * 60 / 100, 0)
#                 porcrit1= null_to_decimal(porcprincipal * 40 / 100, 0)
#                 detdistri = DetalleDistributivo(
#                     distributivo_id=distant.distributivo_id,
#                     criteriodocenciaperiodo_id=749,
#                     horas=porcrit1
#                 )
#                 detdistri.save()
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=periodoactual, distributivo_id=dis).exists():
#                 horas = distant.horas
#                 porcprincipal = null_to_decimal(horas * 60 / 100, 0)
#                 porcrit2= null_to_decimal(porcprincipal * 60 / 100, 0)
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=distant.distributivo_id,
#                     criteriodocenciaperiodo_id=748,
#                     horas=porcrit2
#                 )
#                 detdistri2.save()
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=124, criteriodocenciaperiodo__periodo=periodoactual, distributivo_id=dis).exists():
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=distant.distributivo_id,
#                     criteriodocenciaperiodo_id=822,  #REVISAR ID EN PRODUCCIÓN
#                     horas=1
#                 )
#                 detdistri2.save()
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=periodoactual, distributivo_id=dis).exists():
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=distant.distributivo_id,
#                     criteriodocenciaperiodo_id=820,  #REVISAR ID EN PRODUCCIÓN
#                     horas=2
#                 )
#                 detdistri2.save()
#
#         for detalledistributivo in DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis).order_by('-criteriodocenciaperiodo__criterio_id'):
#             actividad1 = None
#             actividad2 = None
#             actividad3 = None
#             actividad4 = None
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 122:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis).exists():
#                     distant = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=122).exists():
#                             actividad1 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"PLANIFICAR Y ACTUALIZAR CONTENIDOS DE CLASES, SEMINARIOS, TALLERES, ENTRE OTROS.",
#                                                                       desde=convertir_fecha('14-11-2022'),
#                                                                       hasta=convertir_fecha('31-03-2023'),
#                                                                       horas=distant.horas,
#                                                                       vigente=True)
#                             actividad1.save()
#                             print(u"Inserta atividad 1 %s" % actividad1)
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 121:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=121, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=121, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=121).exists():
#                             actividad2 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"PREPARAR, ELABORAR, APLICAR Y CALIFICAR EXÁMENES, TRABAJOS Y PRÁCTICAS",
#                                                                       desde=convertir_fecha('14-11-2022'),
#                                                                       hasta=convertir_fecha('31-03-2023'),
#                                                                       horas=distant2.horas,
#                                                                       vigente=True)
#                             actividad2.save()
#                             print(u"Inserta atividad 2 %s" % actividad2)
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 124:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=124, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=124, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=124).exists():
#                             actividad3 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"ORIENTAR Y ACOMPAÑAR A ESTUDIANTES A TRAVÉS DE TUTORÍAS ACADÉMICAS DE FORMA PRESENCIAL Y/O EN LÍNEA.",
#                                                                       desde=convertir_fecha('14-11-2022'),
#                                                                       hasta=convertir_fecha('31-03-2023'),
#                                                                       horas=distant2.horas,
#                                                                       vigente=True)
#                             actividad3.save()
#                             print(u"Inserta atividad 3 %s" % actividad3)
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 123:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=periodoactual, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=123).exists():
#                             actividad4 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"DISEÑAR Y ELABORAR MATERIAL DIDÁCTICO, GUÍAS DOCENTES O SYLLABUS",
#                                                                       desde=convertir_fecha('14-11-2022'),
#                                                                       hasta=convertir_fecha('31-03-2023'),
#                                                                       horas=distant2.horas,
#                                                                       vigente=True)
#                             actividad4.save()
#                             print(u"Inserta atividad 4 %s" % actividad4)
# #
# #
# #
# #
# #
# #
# except Exception as ex:
#     print(ex)

# try:
#
#     distributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo_id=153)
#
#     for dis in distributivo:
#         profmateria = ProfesorMateria.objects.filter(profesor=dis.profesor_id, materia__nivel__periodo=153,
#                                        activo=True, tipoprofesor__id__in=[12, 11, 6, 7, 1, 2, 3, 14 ])
#         # cabhoras = profmateria.aggregate(valor=Sum('hora'))['valor']
#         # horasact = dis.horasdocencia
#         # if cabhoras != horasact and horasact != 0:
#         # print(dis.id)
#         dis.actualiza_hijos()
#         dis.resumen_evaluacion_acreditacion().actualizar_resumen()
#
# except Exception as ex:
#     print(ex)

# materias = Materia.objects.filter(nivel__periodo_id__in=[153], status=True)

# for materia in materias:
#     materia.crear_actualizar_categoria_notas_curso()
#
# print('FIN')


#actualizar modelo evaluativo
# materias = Materia.objects.filter(status=True, pk__in=[60342,
# 60354,
# 59990,
# 60165,
# 59078,
# 59079,
# 56917,
# 56919,
# 56925,
# 57750,
# 57859,
# 57115,
# 57117,
# 57122,
# 57134,
# 57142,
# 57144,
# 57506,
# 56474,
# 56487,
# 57216,
# 57250,
# 57387,
# 57511,
# 57687,
# 57513,
# 57587,
# 60331,
# 60333,
# 58318,
# 58294,
# 58913,
# 60296,
# 60301,
# 60306,
# 60311,
# 58831,
# 58832,
# 58838,
# 58840,
# 60563,
# 60605,
# 60764,
# 60743,
# 52597,
# 52782,
# 60105,
# 56206,
# 56161,
# 56464,
# 56522,
# 56601,
# 59687,
# 56535,
# 52656,
# 60809,
# 60812,
# 58066,
# 58170,
# 58366,
# 60535,
# 60536,
# 59772,
# 60531,
# 60533,
# 58879,
# 58538,
# 58630,
# 58692,
# 58613,
# 58808,
# 58606,
# 57452,
# 57551,
# 57689,
# 57481,
# 57470,
# 60268,
# 59797,
# 56823,
# 56712,
# 60824,
# 56783,
# 57489,
# 56866,
# 57588,
# 57226,
# 59134,
# 59140,
# 59044,
# 59049,
# 59054,
# 60368,
# 60433,
# 60451,
# 60463,
# 60475,
# 60487,
# 60499,
# 60505,
# 60505,
# 58023,
# 59840,
# 57850,
# 59850,
# 59789,
# 60143,
# 59790,
# 60183,
# 56687,
# 60371,
# 57107,
# 57114,
# 60322,
# 59857,
# 60319,
# 56441,
# 56497,
# 59862,
# 59867,
# 60849,
# 60852,
# 60853,
# 60855,
# 60856,
# 60928,
# 60929,
# 58172,
# 58080,
# 58299,
# 58319,
# 58562,
# 58834,
# 58835,
# 58837,
# 58828,
# 58713,
# 58775,
# 58962,
# 60298,
# 60303,
# 60308,
# 60313,
# 60537,
# 58675,
# 58680,
# 58652,
# 60770,
# 60749,
# 52577,
# 52790,
# 59802,
# 60253,
# 60130,
# 56120,
# 56213,
# 56414,
# 61095,
# 61100,
# 52664,
# 60810,
# 60813,
# 60544,
# 58090,
# 60534,
# 58465,
# 58404,
# 59770,
# 58051,
# 58300,
# 58752,
# 60517,
# 60519,
# 60521,
# 60522,
# 56947,
# 60124,
# 60946,
# 60282,
# 60286,
# 56296,
# 56316,
# 56274,
# 59817,
# 59823,
# 59829,
# 56735,
# 56808,
# 56720,
# 56732,
# 56907,
# 57608,
# 57622,
# 57638,
# 57647,
# 57518,
# 57639,
# 58025,
# 60391,
# 60438,
# 60455,
# 60467,
# 60467,
# 57806,
# 57920,
# 56595,
# 60370,
# 60372,
# 57002,
# 57808,
# 57902,
# 57463,
# 57508,
# 57509,
# 56968,
# 57048,
# 57510,
# 56944,
# 59983,
# 58289,
# 58282,
# 58694,
# 58684,
# 58626,
# 58739,
# 59526,
# 59531,
# 59536,
# 59541,
# 58401,
# 58409,
# 58439,
# 58640,
# 58821,
# 58824,
# 58825,
# 60571,
# 60613,
# 60774,
# 60753,
# 52559,
# 52777,
# 56430,
# 52638,
# 60878,
# 59917,
# 58146,
# 60932,
# 57600,
# 56268,
# 56269,
# 59256,
# 56706,
# 56704,
# 59193,
# 59198,
# 59204,
# 59209,
# 59213,
# 59224,
# 57352,
# 57427,
# 57582,
# 57399])
# from django.db import connections
#
# for materia in materias:
#     if not materia.cerrado:
#         print(materia)
#         materia.modeloevaluativo_id = 27
#         materia.save()
#         evaluaciones = EvaluacionGenerica.objects.filter(materiaasignada__materia=materia)
#         evaluaciones.delete()
#         for maa in materia.asignados_a_esta_materia():
#             maa.evaluacion()
#             maa.notafinal = 0
#             maa.save(actualiza=False)
#         if materia.cronogramaevaluacionmodelo_set.exists():
#             cronograma = materia.cronogramaevaluacionmodelo_set.all()[0]
#             cronograma.materias.remove(materia)
#
#         if materia.coordinacion():
#             if materia.coordinacion().id == 9:
#                 cursor = connections['db_moodle_virtual'].cursor()
#             else:
#                 if materia.coordinacion().id == 7:
#                     cursor = connections['moodle_pos'].cursor()
#                 else:
#                     cursor = connections['moodle_db'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
#         #################################################################################################################
#         # AGREGAR SISTEMA DE CALIFICACION
#         #################################################################################################################
#         if materia.idcursomoodle:
#             print(" Curso a eliminar %s " % materia.idcursomoodle)
#             cursoid = materia.idcursomoodle
#             modelonotas = materia.modeloevaluativo.detallemodeloevaluativo_set.filter(migrarmoodle=True)
#             if modelonotas:
#                 query = u"SELECT id FROM mooc_grade_categories WHERE parent is null and depth=1 and courseid= %s" % cursoid
#                 cursor.execute(query)
#                 row = cursor.fetchall()
#                 padrenota = 0
#                 fecha = int(time.mktime(datetime.now().date().timetuple()))
#                 if not row:
#                     query = u"INSERT INTO mooc_grade_categories(courseid, parent, depth, path, fullname, aggregation, keephigh, droplow, aggregateonlygraded, hidden, timecreated, timemodified) VALUES (%s, null, 1, E'', E'?', 13, 0, 0, 0, 0, %s, %s)" % (
#                         cursoid, fecha, fecha)
#                     cursor.execute(query)
#                     query = u"SELECT id FROM mooc_grade_categories WHERE parent is null and depth=1 and courseid= %s" % cursoid
#                     cursor.execute(query)
#                     row = cursor.fetchall()
#                     query = u"UPDATE mooc_grade_categories SET path='/%s/' WHERE id= %s" % (row[0][0], row[0][0])
#                     cursor.execute(query)
#                     padrenota = row[0][0]
#                 else:
#                     padrenota = row[0][0]
#                 if padrenota > 0:
#                     ordennota = 1
#                     query = u"SELECT id FROM mooc_grade_items WHERE courseid=%s and itemtype='course' and iteminstance=%s" % (
#                         cursoid, padrenota)
#                     cursor.execute(query)
#                     row = cursor.fetchall()
#                     if not row:
#                         query = u"INSERT INTO mooc_grade_items (courseid, categoryid, itemname, itemtype, itemmodule, iteminstance, itemnumber, iteminfo, idnumber, calculation, gradetype, grademax, grademin, scaleid, outcomeid, gradepass, multfactor, plusfactor, aggregationcoef, aggregationcoef2, sortorder, display, decimals, hidden, locked, locktime, needsupdate, weightoverride, timecreated, timemodified) VALUES (%s, null, null, E'course', null, %s, null, null, null, null, 1, 100, 0, null, null, 0, 1, 0, 0, 0, %s, 0, 2, 0, 0, 0, 0, 0, %s, %s)" % (
#                             cursoid, padrenota, ordennota, fecha, fecha)
#                         cursor.execute(query)
#
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='N4'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='N3'" % cursoid
#                     cursor.execute(query)
#
#
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='N1'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='N2'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='EX'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_items WHERE courseid=%s and itemtype='category'" % cursoid
#                     cursor.execute(query)
#                     for modelo in modelonotas:
#                         query = u"SELECT id FROM mooc_grade_categories WHERE parent=%s and depth=2 and courseid= %s and fullname='%s'" % (
#                             padrenota, cursoid, modelo.nombre)
#                         cursor.execute(query)
#                         row = cursor.fetchall()
#                         padremodelo = 0
#                         if not row:
#                             query = u"INSERT INTO mooc_grade_categories(courseid, parent, depth, path, fullname, aggregation, keephigh, droplow, aggregateonlygraded, hidden, timecreated, timemodified) VALUES (%s, %s, 2, E'', E'%s', 0, 0, 0, 0, 0, %s, %s)" % (
#                                 cursoid, padrenota, modelo.nombre, fecha, fecha)
#                             cursor.execute(query)
#                             query = u"SELECT id FROM mooc_grade_categories WHERE parent=%s and depth=2 and courseid= %s and fullname='%s'" % (
#                                     padrenota, cursoid, modelo.nombre)
#                             cursor.execute(query)
#                             row = cursor.fetchall()
#                             padremodelo = row[0][0]
#                             query = u"UPDATE mooc_grade_categories SET path='/%s/%s/' WHERE id= %s" % (
#                                 padrenota, padremodelo, padremodelo)
#                             cursor.execute(query)
#                         else:
#                             padremodelo = row[0][0]
#                         if padremodelo > 0:
#                             ordennota += 1
#                             query = u"SELECT id FROM mooc_grade_items WHERE courseid=%s and itemtype='category' and iteminstance=%s" % (
#                                 cursoid, padremodelo)
#                             cursor.execute(query)
#                             row = cursor.fetchall()
#                             if not row:
#                                 query = u"INSERT INTO mooc_grade_items (courseid, categoryid, itemname, itemtype, itemmodule, iteminstance, itemnumber, iteminfo, idnumber, calculation, gradetype, grademax, grademin, scaleid, outcomeid, gradepass, multfactor, plusfactor, aggregationcoef, aggregationcoef2, sortorder, display, decimals, hidden, locked, locktime, needsupdate, weightoverride, timecreated, timemodified) " \
#                                         u"VALUES (%s, null, E'', E'category', null, %s, null, E'', E'', null, 1, %s, 0, null, null, 0, 1, 0, 0, %s, %s, 0, %s, 0, 0, 0, 0, 0, %s, %s)" \
#                                         % (cursoid, padremodelo, modelo.notamaxima,
#                                            null_to_decimal(modelo.notamaxima / 100, 2), ordennota, modelo.decimales,
#                                            fecha, fecha)
#                                 cursor.execute(query)
#
#
# print('fin actualizar modelo evaluativo')



###

# for materia in materias:
#     if not materia.cerrado:
#         if materia.coordinacion():
#             if materia.coordinacion().id == 9:
#                 cursor = connections['db_moodle_virtual'].cursor()
#             else:
#                 if materia.coordinacion().id == 7:
#                     cursor = connections['moodle_pos'].cursor()
#                 else:
#                     cursor = connections['moodle_db'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
#         #################################################################################################################
#         # AGREGAR SISTEMA DE CALIFICACION
#         #################################################################################################################
#         if materia.idcursomoodle:
#             print(" Curso a eliminar %s " % materia.idcursomoodle)
#             cursoid = materia.idcursomoodle
#             modelonotas = materia.modeloevaluativo.detallemodeloevaluativo_set.filter(migrarmoodle=True)
#             if modelonotas:
#                 query = u"SELECT id FROM mooc_grade_categories WHERE parent is null and depth=1 and courseid= %s" % cursoid
#                 cursor.execute(query)
#                 row = cursor.fetchall()
#                 padrenota = 0
#                 fecha = int(time.mktime(datetime.now().date().timetuple()))
#                 if not row:
#                     query = u"INSERT INTO mooc_grade_categories(courseid, parent, depth, path, fullname, aggregation, keephigh, droplow, aggregateonlygraded, hidden, timecreated, timemodified) VALUES (%s, null, 1, E'', E'?', 13, 0, 0, 0, 0, %s, %s)" % (
#                         cursoid, fecha, fecha)
#                     cursor.execute(query)
#                     query = u"SELECT id FROM mooc_grade_categories WHERE parent is null and depth=1 and courseid= %s" % cursoid
#                     cursor.execute(query)
#                     row = cursor.fetchall()
#                     query = u"UPDATE mooc_grade_categories SET path='/%s/' WHERE id= %s" % (row[0][0], row[0][0])
#                     cursor.execute(query)
#                     padrenota = row[0][0]
#                 else:
#                     padrenota = row[0][0]
#                 if padrenota > 0:
#                     ordennota = 1
#                     query = u"SELECT id FROM mooc_grade_items WHERE courseid=%s and itemtype='course' and iteminstance=%s" % (
#                         cursoid, padrenota)
#                     cursor.execute(query)
#                     row = cursor.fetchall()
#                     if not row:
#                         query = u"INSERT INTO mooc_grade_items (courseid, categoryid, itemname, itemtype, itemmodule, iteminstance, itemnumber, iteminfo, idnumber, calculation, gradetype, grademax, grademin, scaleid, outcomeid, gradepass, multfactor, plusfactor, aggregationcoef, aggregationcoef2, sortorder, display, decimals, hidden, locked, locktime, needsupdate, weightoverride, timecreated, timemodified) VALUES (%s, null, null, E'course', null, %s, null, null, null, null, 1, 100, 0, null, null, 0, 1, 0, 0, 0, %s, 0, 2, 0, 0, 0, 0, 0, %s, %s)" % (
#                             cursoid, padrenota, ordennota, fecha, fecha)
#                         cursor.execute(query)
#
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='N4'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='N3'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='EX2'" % cursoid
#                     cursor.execute(query)
#
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='N1'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='N2'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_categories WHERE depth=2 and courseid=%s and fullname='EX1'" % cursoid
#                     cursor.execute(query)
#                     query = u"DELETE FROM mooc_grade_items WHERE courseid=%s and itemtype='category'" % cursoid
#                     cursor.execute(query)
#                     for modelo in modelonotas:
#                         query = u"SELECT id FROM mooc_grade_categories WHERE parent=%s and depth=2 and courseid= %s and fullname='%s'" % (
#                             padrenota, cursoid, modelo.nombre)
#                         cursor.execute(query)
#                         row = cursor.fetchall()
#                         padremodelo = 0
#                         if not row:
#                             query = u"INSERT INTO mooc_grade_categories(courseid, parent, depth, path, fullname, aggregation, keephigh, droplow, aggregateonlygraded, hidden, timecreated, timemodified) VALUES (%s, %s, 2, E'', E'%s', 0, 0, 0, 0, 0, %s, %s)" % (
#                                 cursoid, padrenota, modelo.nombre, fecha, fecha)
#                             cursor.execute(query)
#                             query = u"SELECT id FROM mooc_grade_categories WHERE parent=%s and depth=2 and courseid= %s and fullname='%s'" % (
#                                     padrenota, cursoid, modelo.nombre)
#                             cursor.execute(query)
#                             row = cursor.fetchall()
#                             padremodelo = row[0][0]
#                             query = u"UPDATE mooc_grade_categories SET path='/%s/%s/' WHERE id= %s" % (
#                                 padrenota, padremodelo, padremodelo)
#                             cursor.execute(query)
#                         else:
#                             padremodelo = row[0][0]
#                         if padremodelo > 0:
#                             ordennota += 1
#                             query = u"SELECT id FROM mooc_grade_items WHERE courseid=%s and itemtype='category' and iteminstance=%s" % (
#                                 cursoid, padremodelo)
#                             cursor.execute(query)
#                             row = cursor.fetchall()
#                             if not row:
#                                 query = u"INSERT INTO mooc_grade_items (courseid, categoryid, itemname, itemtype, itemmodule, iteminstance, itemnumber, iteminfo, idnumber, calculation, gradetype, grademax, grademin, scaleid, outcomeid, gradepass, multfactor, plusfactor, aggregationcoef, aggregationcoef2, sortorder, display, decimals, hidden, locked, locktime, needsupdate, weightoverride, timecreated, timemodified) " \
#                                         u"VALUES (%s, null, E'', E'category', null, %s, null, E'', E'', null, 1, %s, 0, null, null, 0, 1, 0, 0, %s, %s, 0, %s, 0, 0, 0, 0, 0, %s, %s)" \
#                                         % (cursoid, padremodelo, modelo.notamaxima,
#                                            null_to_decimal(modelo.notamaxima / 100, 2), ordennota, modelo.decimales,
#                                            fecha, fecha)
#                                 cursor.execute(query)



# #asignar procedimiento eva
# programas = ProgramaAnaliticoAsignatura.objects.filter(status=True)
# for programa in programas:
#     facultad = None
#     programa.procedimientoeva_id = 1 ##modelo de calificacion 2 parciales 22017
#     programa.save()
#     if programa.asignaturamalla.malla.carrera.coordinaciones():
#         facultad = programa.asignaturamalla.malla.carrera.coordinaciones()[0]
#
#
#     if facultad.id == 12:
#         programa.procedimientoeva_id = 3 ##modelo de integración curricular
#         programa.save()
#
#     elif programa.asignaturamalla.transversal:
#         programa.procedimientoeva_id = 4  ##modelo de transversal
#         programa.save()
#
#     else:
#         if programa.asignaturamalla.malla.carrera.modalidad == 3:
#             asignaturas = AsignaturaMalla.objects.values_list('id', flat=True).filter(status=True, validarequisitograduacion=True, nivelmalla_id=8)
#             if programa.asignaturamalla.id in asignaturas:
#                 programa.procedimientoeva_id = 2 ##modelo de titulacion carreras en línea
#                 programa.save()
#         else:
#             asignaturas = AsignaturaMalla.objects.values_list('id', flat=True).filter(status=True, validarequisitograduacion=True, nivelmalla_id=8)
#             if programa.asignaturamalla.id in asignaturas:
#                 programa.procedimientoeva_id = 3 ##modelo de integración curricular
#                 programa.save()
#
# print('fin asignacion procedimiento evaluativo')
#
#

# creditos computacion
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(status=True):
#         # print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         asigmal = AsignaturaMalla.objects.get(asignatura_id=1053, malla_id=32)
#         # for asigmal in AsignaturaMalla.objects.filter(malla_id=32):
#         modulos = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion, asignatura_id=asigmal.asignatura_id, creditos=0).order_by('id')
#         for record2 in modulos:
#                 print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#                 record2.creditos = asigmal.creditos
#                 record2.save()
#                 historico =  HistoricoRecordAcademico.objects.filter(status=True, recordacademico = record2).order_by('-aprobada', '-fecha')[0]
#                 historico.creditos = record2.creditos
#                 historico.save()
#                 # record2.actualizar()
#                 print('------------------ COMPUP %s - %s' % (linea, record2.asignatura))
#         print('------------------ FIN CREDITOS COMPUTACION')
#
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)




# creditos ingles
#
#
# def reasjute_horas_creditos_malla_modulos_ingles():
#
#     print(SITE_STORAGE)
#     with xlsxwriter.Workbook(f'{SITE_STORAGE}/media/migracion_modulos_ingles_2021_{random.randrange(1, 100)}.xlsx') as workbook:
#         wk = workbook.add_worksheet(f"Hoja1")
#         columns = [
#             (u"ID_INSCRIPCION", 10),
#             (u"APELLIDOS_NOMBRES", 100),
#             (u"CEDULA", 80),
#             (u"CARRERA", 80),
#             (u"ID_MALLA", 80),
#             (u"ID_RECORD", 10),
#             (u"MODULO", 30),
#             (u"CREDITOS_ANTERIOR", 10),
#             (u"CREDITOS_ACTUAL", 10),
#             (u"HORAS_ANTERIOR", 10),
#             (u"HORAS_ACTUAL", 10),
#         ]
#         row_num = 1
#         for col_num in range(len(columns)):
#             wk.write(row_num, col_num, columns[col_num][0])
#             wk.set_column(col_num, col_num, columns[col_num][1])
#         row_num = 2
#         wrap_format = workbook.add_format({'text_wrap': True})
#         c = 0
#         ids = [10, 21, 15, 147, 16, 148, 12, 232, 228, 233, 18, 17, 222, 225, 202, 226, 205, 8, 207, 6, 210, 201, 224, 356, 9, 204, 218, 206, 212, 114, 219, 113, 4, 5, 3, 7, 115, 199, 237, 208, 332, 231, 200, 11, 19, 14, 213, 258, 355, 173, 174, 13, 2, 172]
#        # ids = [210]
#       #2013 -2012  ids = [9, 10, 13, 2, 15, 19, 11, 7, 3, 14, 16, 115, 6, 12, 148, 147, 8, 4, 113, 18, 17, 114, 5, 21]
#         # inscripcion_ids = [131795, 104493]
#         # ids = [219]
#         mallas = Malla.objects.filter(pk__in=ids)
#         for malla in mallas:
#             print(f"Malla: {malla.__str__()}")
#             for inscripcionmalla in InscripcionMalla.objects.filter(malla=malla):
#                 inscripcion = inscripcionmalla.inscripcion
#                 # inscripcion = Inscripcion.objects.get(status=True, pk=74728)
#                 if not inscripcion.usado_graduados() or not inscripcion.egresado():
#                     # print(f"Inscripcion: {inscripcion.__str__()}")
#                     recordacademico = inscripcion.recordacademico_set.filter(modulomalla__isnull=False, aprobada=True, creditos=0)
#                     # print(f"Total de record: {len(recordacademico)}")
#                     for record in recordacademico:
#                         if record.historicorecordacademico_set.filter(status=False, fecha=record.fecha).exists():
#                             recordfalse = record.historicorecordacademico_set.filter(status=False, fecha=record.fecha)
#                             recordfalse.delete()
#                         print(f"Inscripcion: {inscripcion.__str__()}")
#                         record.actualizar()
#                         historico = record.mi_historico()
#                         historico.creditos = record.modulomalla.creditos
#                         historico.horas = record.modulomalla.horas
#                         historico.validapromedio = False
#                         historico.valida = True
#                         historico.save()
#                         creditos_anterior = record.creditos
#                         creditos_actual = record.modulomalla.creditos
#                         record.creditos = record.modulomalla.creditos
#                         horas_anterior = record.horas
#                         horas_actual = record.modulomalla.horas
#                         record.horas = record.modulomalla.horas
#                         record.validapromedio = False
#                         record.valida = True
#                         record.save()
#                         # ID_INSCRIPCION
#                         wk.write(row_num, 0, inscripcion.id)
#                         # APELLIDOS_NOMBRES
#                         wk.write(row_num, 1, inscripcion.persona.nombre_completo_inverso())
#                         # CEDULA
#                         wk.write(row_num, 2, inscripcion.persona.documento())
#                         # CARRERA
#                         wk.write(row_num, 3, inscripcion.carrera.__str__())
#                         # ID_MALLA
#                         wk.write(row_num, 4, malla.id)
#                         # ID_RECORD
#                         wk.write(row_num, 5, record.id)
#                         # MODULO
#                         wk.write(row_num, 6, record.modulomalla.asignatura.nombre)
#                         # CREDITOS_ANTERIOR
#                         wk.write(row_num, 7, creditos_anterior)
#                         # CREDITOS_ACTUAL
#                         wk.write(row_num, 8, creditos_actual)
#                         # HORAS_ANTERIOR
#                         wk.write(row_num, 9, horas_anterior)
#                         # HORAS_ACTUAL
#                         wk.write(row_num, 10, horas_actual)
#                         row_num += 1
#                     print(f"Final de Inscripcion: {inscripcion.__str__()}")
#                     print(f"------------------------------------------------")
#         print('------------------ FIN CREDITOS INGLES')
# #
# # #
# reasjute_horas_creditos_malla_modulos_ingles()

# periodo = Periodo.objects.get(id=153)
# seguimientos = SeguimientoTutor.objects.filter(status=True, periodo=periodo, tutor_id=1173)
# for seguimiento in seguimientos:
#     seguimiento.delete()
#
# fechas = (
#     (datetime(2022,12,1).date(), datetime(2022,12,31).date()),
#     (datetime(2023,1,3).date(), datetime(2022,1,31).date()),
#     (datetime(2023,2,1).date(), datetime(2022,2,28).date()),
#     (datetime(2023,3,1).date(), datetime(2022,3,30).date())

# )
# def segumientos():
#     docentes = DetalleDistributivo.objects.filter(status=True,  distributivo__periodo_id=153, criteriodocenciaperiodo__criterio_id=136, distributivo__profesor_id=1173).values_list('distributivo__profesor', flat=True)
#     # Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo=periodo,nivel__periodo__visible=True, profesormateria__status=True,status=True,profesormateria__activo=True).distinct().order_by('asignatura').distinct()
#     try:
#         c = 1
#         for p in docentes:
#             print('TOTAL DE DOCENTES  %s' % len(docentes))
#             for fecha in fechas:
#                 if p == 1173:
#                     profesor = Profesor.objects.get(id=p)
#                     text = 'N° {}  DOCENTE .... ---  .....: {}'.format(c, profesor)
#                     for materia in Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo=periodo,nivel__periodo__visible=True, profesormateria__status=True,status=True,profesormateria__activo=True).distinct().order_by('asignatura').distinct():
#                         print(materia)
#                         if PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=1).exists():
#                             ponderacion_plataforma = PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=1).order_by(
#                                 '-id').first().porcentaje
#                         if PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=2).exists():
#                             ponderacion_recurso = PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=2).order_by(
#                                 '-id').first().porcentaje
#                         if PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=3).exists():
#                             ponderacion_actividad = PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=3).order_by(
#                                 '-id').first().porcentaje
#                         # materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
#                         materiasasignadas = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2, 3]).order_by(
#                             'matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
#                         inicio = fecha[0]
#                         fin = fecha[1]
#                         seguimiento = materia.seguimientotutor_set.filter(status=True).order_by('-fechainicio')
#                         if not seguimiento.filter(fechainicio__range=[inicio, fin]):
#                             # hoy = seleccionar_fecha_ramdom()
#                             hoy = inicio
#                             if seguimiento:
#                                 seguimientoaux = materia.seguimientotutor_set.filter(status=True, fechainicio__lte=hoy,
#                                                                                      fechafin__gte=hoy).order_by('-fechainicio')
#                                 if seguimientoaux:
#                                     finic = seguimientoaux[0].fechainicio
#                                     ffinc = seguimientoaux[0].fechafin
#                                 else:
#                                     finic = seguimiento[0].fechafin + timedelta(days=1)
#                                     ffinc = hoy
#                             else:
#                                 finic = materia.inicio
#                                 ffinc = hoy
#
#                             lista = []
#                             listaalumnos = []
#                             if materia.tareas_asignatura_moodle(finic, ffinc):
#                                 listaidtareas = []
#                                 for listatarea in materia.tareas_asignatura_moodle(finic, ffinc):
#                                     listaidtareas.append(listatarea[0])
#                                 lista.append(listaidtareas)
#                             else:
#                                 lista.append(0)
#                             if materia.foros_asignatura_moodledos(finic, ffinc):
#                                 listaidforum = []
#                                 for listaforo in materia.foros_asignatura_moodledos(finic, ffinc):
#                                     listaidforum.append(listaforo[0])
#                                 lista.append(listaidforum)
#                             else:
#                                 lista.append(0)
#                             if materia.test_asignatura_moodle(finic, ffinc):
#                                 listaidtest = []
#                                 for listatest in materia.test_asignatura_moodle(finic, ffinc):
#                                     listaidtest.append(listatest)
#                                 lista.append(listaidtest)
#                             else:
#                                 lista.append(0)
#                             diapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,
#                                                                                    silabosemanal__fechafinciosemana__range=(finic, ffinc),
#                                                                                    silabosemanal__silabo__status=True,
#                                                                                    iddiapositivamoodle__gt=0)
#                             if diapositivas:
#                                 listaidpresentacion = []
#                                 for listadias in diapositivas:
#                                     listaidpresentacion.append(listadias.iddiapositivamoodle)
#                                 lista.append(listaidpresentacion)
#                             else:
#                                 lista.append(0)
#                             fechacalcula = datetime.strptime('2020-07-24', '%Y-%m-%d').date()
#                             if finic > fechacalcula:
#                                 guiasestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,
#                                                                                               silabosemanal__fechafinciosemana__range=(
#                                                                                               finic, ffinc), silabosemanal__silabo__status=True,
#                                                                                               idguiaestudiantemoodle__gt=0)
#                                 if guiasestudiantes:
#                                     listaidguiaestudiante = []
#                                     for listaguiasestu in guiasestudiantes:
#                                         listaidguiaestudiante.append(listaguiasestu.idguiaestudiantemoodle)
#                                     lista.append(listaidguiaestudiante)
#                                 else:
#                                     lista.append(0)
#                                 guiasdocentes = GuiaDocenteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,
#                                                                                         silabosemanal__fechafinciosemana__range=(finic, ffinc),
#                                                                                         silabosemanal__silabo__status=True,
#                                                                                         idguiadocentemoodle__gt=0)
#                                 if guiasdocentes:
#                                     listaidguiadocente = []
#                                     for listaguiasdoce in guiasdocentes:
#                                         listaidguiadocente.append(listaguiasdoce.idguiadocentemoodle)
#                                     lista.append(listaidguiadocente)
#                                 else:
#                                     lista.append(0)
#                                 compendios = CompendioSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,
#                                                                                    silabosemanal__fechafinciosemana__range=(finic, ffinc),
#                                                                                    silabosemanal__silabo__status=True, idmcompendiomoodle__gt=0)
#                                 if compendios:
#                                     listaidcompendio = []
#                                     for listacompendios in compendios:
#                                         listaidcompendio.append(listacompendios.idmcompendiomoodle)
#                                     lista.append(listaidcompendio)
#                                 else:
#                                     lista.append(0)
#                             else:
#                                 lista.append(0)
#                                 lista.append(0)
#                                 lista.append(0)
#                             totalverde = 0
#                             totalamarillo = 0
#                             totalrojo = 0
#                             for alumnos in materiasasignadas:
#                                 nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' + alumnos.matricula.inscripcion.persona.nombres
#                                 esppl = 'NO'
#                                 esdiscapacidad = 'NO'
#                                 if alumnos.matricula.inscripcion.persona.ppl:
#                                     esppl = 'SI'
#                                 if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
#                                     esdiscapacidad = 'SI'
#                                 if alumnos.matricula.nivel.periodo_id >= 113:
#                                     totalaccesologuin = float("{:.2f}".format(
#                                         alumnos.matricula.inscripcion.persona.total_loguinusermoodle_sin_findesemana(finic,
#                                                                                                                      ffinc)))
#                                 else:
#                                     totalaccesologuin = float(
#                                         "{:.2f}".format(alumnos.matricula.inscripcion.persona.total_loguinusermoodle(finic, ffinc)))
#                                 totalaccesorecurso = float("{:.2f}".format(
#                                     alumnos.matricula.inscripcion.persona.total_accesorecursomoodle(finic, ffinc, materia.idcursomoodle,
#                                                                                                     lista)))
#                                 totalcumplimiento = float("{:.2f}".format(
#                                     alumnos.matricula.inscripcion.persona.total_cumplimientomoodle(finic, ffinc, materia.idcursomoodle, lista)))
#                                 totalporcentaje = float("{:.2f}".format(((((totalaccesologuin * ponderacion_plataforma) / 100) + (
#                                             (totalaccesorecurso * ponderacion_recurso) / 100) + (
#                                                                                       (totalcumplimiento * ponderacion_actividad) / 100)))))
#
#                                 if totalporcentaje >= 70:
#                                     colorfondo = '5bb75b'
#                                     totalverde += 1
#                                 if totalporcentaje <= 30:
#                                     colorfondo = 'b94a48'
#                                     totalrojo += 1
#                                 if totalporcentaje > 31 and totalporcentaje < 70:
#                                     colorfondo = 'faa732'
#                                     totalamarillo += 1
#                                 listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
#                                                      nombres,
#                                                      esppl,
#                                                      esdiscapacidad,
#                                                      totalaccesologuin,
#                                                      totalaccesorecurso,
#                                                      totalcumplimiento,
#                                                      totalporcentaje,
#                                                      alumnos.matricula.inscripcion.persona.email,
#                                                      alumnos.matricula.inscripcion.persona.telefono,
#                                                      alumnos.matricula.inscripcion.persona.canton,
#                                                      colorfondo,
#                                                      alumnos.matricula.inscripcion.id,
#                                                      alumnos.matricula,
#                                                      alumnos.esta_retirado(),
#                                                      alumnos.id,
#                                                      alumnos.retiromanual])
#
#                             porcentajeverde = float("{:.2f}".format((totalverde / materiasasignadas.count()) * 100))
#                             porcentajerojo = float("{:.2f}".format((totalrojo / materiasasignadas.count()) * 100))
#                             porcentajeamarillo = float("{:.2f}".format((totalamarillo / materiasasignadas.count()) * 100))
#
#                             s = SeguimientoTutor.objects.filter(materia=materia, tutor=profesor, fechainicio__lte=hoy, fechafin__gte=hoy)
#                             if not s:
#                                 s = SeguimientoTutor(tutor=profesor,
#                                                      fechainicio=finic,
#                                                      fechafin=ffinc,
#                                                      materia=materia,
#                                                      periodo=periodo)
#                                 s.save()
#                             else:
#                                 s = s[0]
#                             # s.matriculaseguimientotutor_set.all().delete()
#                             for integrantes in listaalumnos:
#                                 ppl = False
#                                 if integrantes[2] == 'SI':
#                                     ppl = True
#                                 discapacidad = False
#                                 if integrantes[3] == 'SI':
#                                     discapacidad = True
#                                 if not MatriculaSeguimientoTutor.objects.filter(seguimiento=s, matricula=integrantes[13]).exists():
#                                     m = MatriculaSeguimientoTutor(seguimiento=s,
#                                                                   matricula=integrantes[13],
#                                                                   ppl=ppl,
#                                                                   discapacidad=discapacidad,
#                                                                   accesoplataforma=integrantes[4],
#                                                                   accesorecurso=integrantes[5],
#                                                                   cumplimientoactividades=integrantes[6],
#                                                                   promediovariables=integrantes[7],
#                                                                   color=integrantes[11])
#                                     m.save()
#                                 else:
#                                     m = MatriculaSeguimientoTutor.objects.get(seguimiento=s, matricula=integrantes[13])
#                                     m.ppl = ppl
#                                     m.discapacidad = discapacidad
#                                     m.accesoplataforma = integrantes[4]
#                                     m.accesorecurso = integrantes[5]
#                                     m.cumplimientoactividades = integrantes[6]
#                                     m.promediovariables = integrantes[7]
#                                     m.color = integrantes[11]
#                                     m.save()
#
#                                 if MatriculaSeguimientoTutor.objects.filter(seguimiento=s, matricula=integrantes[13], promediovariables__lt=70.00).exists():
#                                     matriculaseguimiento = MatriculaSeguimientoTutor.objects.get(seguimiento=s, matricula=integrantes[13], promediovariables__lt=70.00)
#                                     llamada = LlamadasMatriculaSeguimientoTutor(
#                                         matriculaseguimientotutor=matriculaseguimiento,
#                                         fecha= finic,
#                                         hora=datetime.now().time(),
#                                         minutos=5,
#                                         descripcion='ok')
#                                     llamada.save()
#
#                     c += 1
#     except Exception as e:
#         print(e)
#         print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
#
#
# def poner_asistencia():
#     fechas = [
#         (datetime(2023, 1, 3, 0, 0, 0)).date(),
#     ]
#     for fecha in fechas:
#         for cl in Clase.objects.filter(activo=True, inicio__lte=fecha, fin__gte=fecha, dia=(fecha.weekday() + 1),
#                                        status=True, materia__nivel__periodo_id=153):
#             if cl.materia.profesor_principal():
#                 if LeccionGrupo.objects.filter(profesor=cl.materia.profesor_principal(), turno=cl.turno,
#                                                fecha=fecha).exists():
#                     lecciongrupo = LeccionGrupo.objects.get(profesor=cl.materia.profesor_principal(), turno=cl.turno,
#                                                             fecha=fecha)
#                 else:
#                     lecciongrupo = LeccionGrupo(profesor=cl.materia.profesor_principal(),
#                                                 turno=cl.turno,
#                                                 aula=cl.aula,
#                                                 dia=cl.dia,
#                                                 fecha=fecha,
#                                                 horaentrada=cl.turno.comienza,
#                                                 horasalida=cl.turno.termina,
#                                                 abierta=False,
#                                                 automatica=True,
#                                                 contenido='REGISTRO MASIVO 2023 - AUTORIZADO POR DIRECTOR TICS',
#                                                 observaciones='REGISTRO MASIVO 2023 - AUTORIZADO POR DIRECTOR TICS')
#                     lecciongrupo.save()
#                 if Leccion.objects.filter(clase=cl, fecha=fecha).exists():
#                     leccion = Leccion.objects.get(clase=cl, fecha=fecha)
#                 else:
#                     leccion = Leccion(clase=cl,
#                                       fecha=fecha,
#                                       horaentrada=cl.turno.comienza,
#                                       horasalida=cl.turno.termina,
#                                       abierta=True,
#                                       contenido=lecciongrupo.contenido,
#                                       observaciones=lecciongrupo.observaciones)
#                     leccion.save()
#                 if not lecciongrupo.lecciones.filter(pk=leccion.id).exists():
#                     lecciongrupo.lecciones.add(leccion)
#                 if AsistenciaLeccion.objects.filter(leccion=leccion).exists():
#                     for asis in AsistenciaLeccion.objects.filter(leccion=leccion):
#                         if not asis.asistio:
#                             asis.asistio = True
#                             asis.save()
#                             mateasig = asis.materiaasignada
#                             mateasig.save(actualiza=True)
#                             mateasig.actualiza_estado()
#                 else:
#                     for materiaasignada in cl.materia.asignados_a_esta_materia():
#                         if not AsistenciaLeccion.objects.filter(leccion=leccion,
#                                                                 materiaasignada=materiaasignada).exists():
#                             asistencialeccion = AsistenciaLeccion(leccion=leccion,
#                                                                   materiaasignada=materiaasignada,
#                                                                   asistio=True)
#                             asistencialeccion.save()
#                             materiaasignada.save(actualiza=True)
#                             materiaasignada.actualiza_estado()
#
#                 lecciongrupo.save()
#                 print(cl)
#
#
# poner_asistencia()

#cambiar modelo evaluativo - agregar RE
#materias = Materia.objects.filter(status=True, modeloevaluativo_id=27, nivel__periodo_id=153)
# for materia in materias:
#     if not materia.cerrado:
#         for maa in materia.asignados_a_esta_materia():
#             evaluacion = EvaluacionGenerica(materiaasignada_id=maa.id,
#                                             detallemodeloevaluativo_id=1345)   #cambiar 1345
#
#             evaluacion.save()
#
# print('fin')

#

# with transaction.atomic():
#     try:
#
#         materias = Materia.objects.filter(status=True, modeloevaluativo_id=27, nivel__periodo_id=153)
#
#         for materia in materias:
#             for materiaasignada in materia.materiaasignada_set.filter(status=True):
#                 d = locals()
#                 exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
#                 d['calculo_modelo_evaluativo'](materiaasignada)
#                 materiaasignada.actualiza_estado()
#
#     except Exception as ex:
#         print(ex)
#         transaction.set_rollback(True)

#CAMBIAR PROFESOR MATERIA A DOCENTES DE ASIGNTURAS TRANSVERSALES
#
# materias = Materia.objects.filter(status=True,nivel__periodo_id=177,pk__in=[61715,
# 61796,
# 61852,
# 62193,
# 67021,
# 65133,
# 63209,
# 63224,
# 62272,
# 62242,
# 62646,
# 63356,
# 62497,
# 62432,
# 62518,
# 62567,
# 62611,
# 63747,
# 64042,
# 64056,
# 64142,
# 64995,
# 63871,
# 63872,
# 63888,
# 65780,
# 65593,
# 65655,
# 65923
# ])
# for materia in materias:
#     materia.modeloevaluativo_id = 27
#     materia.tipomateria = 3
#     materia.save()
#     evaluaciones = EvaluacionGenerica.objects.filter(materiaasignada__materia=materia)
#     evaluaciones.delete()
#     for maa in materia.asignados_a_esta_materia():
#         maa.evaluacion()
#         maa.notafinal = 0
#         maa.save()



#mdelo evaluativo integración curricular
# materias =Materia.objects.filter(status=True, nivel__periodo=153, modeloevaluativo_id=25, cerrado=False, fin='2023-03-31')
# for materia in materias:
#     if not materia.cerrado:
#         materia.modeloevaluativo_id = 25
#         materia.save()
#         evaluaciones = EvaluacionGenerica.objects.filter(materiaasignada__materia=materia)
#         evaluaciones.delete()
#         for maa in materia.asignados_a_esta_materia():
#             maa.evaluacion()
#             maa.notafinal = 0
#             maa.save()

#AMPLIAR FECHAS RUBROS

# rubros = Rubro.objects.filter(status=True, tipo_id=2923, matricula__nivel__periodo_id=177, cancelado=False, matricula__retiradomatricula=False).exclude(fechavence='2023-04-28')
#
# for rubro in rubros:
#     if rubro.fechavence == convertir_fecha_invertida('2023-07-05'):
#         print(rubro.id,"-",rubro.matricula_id, "-", rubro.fechavence)
#         rubro.fechavence = '2023-08-05'
#         rubro.save()
#     elif rubro.fechavence == convertir_fecha_invertida('2023-06-05'):
#         print(rubro.id, "-", rubro.matricula_id, "-", rubro.fechavence)
#         rubro.fechavence = '2023-07-05'
#         rubro.save()
#     elif rubro.fechavence == convertir_fecha_invertida('2023-05-05'):
#         print(rubro.id, "-", rubro.matricula_id, "-", rubro.fechavence)
#         rubro.fechavence = '2023-06-05'
#         rubro.save()
#
# rubrosmatricula = Rubro.objects.filter(status=True, tipo_id=2923, matricula__nivel__periodo_id=177, cancelado=False, matricula__retiradomatricula=False, matricula__aranceldiferido=1).exclude(fechavence='2023-04-28').distinct('matricula_id')
# for rmatricula in rubrosmatricula:
#     isResult, message = rmatricula.matricula.generar_actacompromiso_matricula_pregrado()
#     if not isResult:
#         raise NameError(message)
#     url_acta_compromiso = message
#     rmatricula.matricula.aranceldiferido = 1
#     rmatricula.matricula.actacompromiso = url_acta_compromiso
#     rmatricula.matricula.save()
# try:
#     bloqueados = Matricula.objects.filter(status=True,retiradomatricula=True,nivel__periodo_id=153, inscripcion__persona__cedula__in=[
#     '0105766703',
#     '0930132188',
#     '0956652580',
#     '0926506981',
#     '1311073702',
#     '1206281428',
#     '0803785823',
#     '0705170868',
#     '0804606366',
#     '0952872059',
#     '0954184123',
#     '1718485392',
#     '0941554487',
#     '0912345808',
#     '0958780389',
#     '0925811820',
#     '0925972952',
#     '0913846556',
#     '0958069221',
#     '0958643413',
#     '0952558385',
#     '0930727011',
#     '0944308469',
#     '0941155293',
#     '1754167060',
#     '0922633953',
#     '0930627989',
#     '0942018904',
#     '0953257003',
#     '0940717697',
#     '0924870017',
#     '0943290668',
#     '0942111931',
#     '0604978882',
#     '0928179001',
#     '0705587640',
#     '0924701675',
#     '0704376698',
#     '0918628470',
#     '1717350647',
#     '1208012227',
#     '1003273966',
#     '2000132718',
#     '0929142651',
#     '0924176837',
#     '0952094290',
#     '2450601915',
#     '0942765363',
#     '0941670721',
#     '1719738955',
#     '0706156437',
#     '0942119462',
#     '0920065307',
#     '0925057788',
#     '2450835018',
#     '0943963942',
#     '0958921199',
#     '0940113301',
#     '0921506523',
#     '0924885585',
#     '0923310866',
#     '0953685138',
#     '0750309361',
#     '0959393851',
#     '1106101916',
#     '0925855181',
#     '0950577254',
#     '0943449116',
#     '0944135110',
#     '0957142037',
#     '2200486377',
#     '0925594137',
#     '0952137628',
#     '0940407109',
#     '1207961002',
#     '0956694939',
#     '0941715260',
#     '0940150691',
#     '1103736656',
#     '0926403205',
#     '0929871945',
#     '0952337061',
#     '0952837557',
#     '1753884764',
#     '1351401441',
#     '1721684429',
#     '0929745412',
#     '0940304272',
#     '0929804599',
#     '2450333246',
#     '1205839499',
#     '0924185077',
#     '0928366228',
#     '1725335366',
#     '0920372927',
#     '0923175996',
#     '1717656548',
#     '1206048678',
#     '0923608160',
#     '0956803134',
#     '1207559244',
#     '0958557373',
#     '0704850866',
#     '0944280858',
#     '0923638613',
#     '0952165900',
#     '0956836704',
#     '0957626922',
#     '0928189877',
#     '0958947541',
#     '0942265315',
#     '0943782870',
#     '0750700569',
#     '0941990061',
#     '0957736333',
#     '0955704747',
#     '0925074437',
#     '0950722322',
#     '0928365865',
#     '0952576718',
#     '0942240789',
#     '0928444645',
#     '0928178805',
#     '0954259958',
#     '0942987645',
#     '0705605764',
#     '1718651878',
#     '0704851732',
#     '2450560855',
#     '0750739336',
#     '0958249336',
#     '0953426061',
#     '0941242315',
#     '0956492094',
#     '0922630041',
#     '0944310085',
#     '0928449701',
#     '1722763933',
#     '0929744647',
#     '0940190044',
#     '0928109271',
#     '0930575709',
#     '0927057273',
#     '0952395259',
#     '0603362500',
#     '1206299305',
#     '0751081274',
#     '1251254197',
#     '1250839311',
#     '0955739487',
#     '0944125434',
#     '2300686363',
#     '1104554926',
#     '1315509743',
#     '0951149368',
#     '0502234040',
#     '0953440997',
#     '1723457089',
#     '0927458836',
#     '1150461018',
#     '1803353018',
#     '0940665722',
#     '0918598632',
#     '0923904593',
#     '1310854276',
#     '0928636216',
#     '0957581333',
#     '0931189096',
#     '0940423007',
#     '0942437245',
#     '1205669946',
#     '0941216632',
#     '0927954032',
#     '0941527293',
#     '0605614460',
#     '0921676763',
#     '0910952001',
#     '0928266832',
#     '0917218364',
#     '0942199118',
#     '0930546320',
#     '0940931348',
#     '0923398812',
#     '2400097230',
#     '2450425802',
#     '1718561846',
#     '1723581847',
#     '0958969883',
#     '0951953504',
#     '0942470493',
#     '0922280912',
#     '0925229031',
#     '0955344411',
#     '2100651260',
#     '0928044536',
#     '0502188220',
#     '1804553756',
#     '1105207979',
#     '0958222424',
#     '0940157068',
#     '0913551891',
#     '0959283615',
#     '2450113432',
#     '1725497752',
#     '0951675180',
#     '0956296610',
#     '0953577764',
#     '0930582259',
#     '0926818394',
#     '0941310708',
#     '0959036757',
#     '0940230741',
#     '1900713460',
#     '0944091156',
#     '1314409325',
#     '0951023621',
#     '0958820060',
#     '0925012213',
#     '0940351471',
#     '0942093675',
#     '0957817703',
#     '0927817502',
#     '0954680849',
#     '0955459730',
#     '0942095282',
#     '0932492911',
#     '0955407309',
#     '0950661850',
#     '0940741184',
#     '0955586730',
#     '0941536534',
#     '0952511111',
#     '0941335812',
#     '0951462951',
#     '0926778887',
#     '0953934783',
#     '1207483668',
#     '0941349029',
#     '0920162062',
#     '0941364747',
#     '0951629492',
#     '0942051517',
#     '1750011239',
#     '0931041859',
#     '1900670249',
#     '1206148635',
#     '1104806540',
#     '0951270529',
#     '0931095632',
#     '0926210709',
#     '0925762585',
#     '0957015704',
#     '0941232399',
#     '0940610611',
#     '0930144605',
#     '0923423248',
#     '0930597133',
#     '0930977228',
#     '0940954761',
#     '2350907305',
#     '0605159052',
#     '0606233559',
#     '0958095267',
#     '1205484296',
#     '0944335702',
#     '1207131515',
#     '0926616293',
#     '0952301166',
#     '0925988974',
#     '0928894971',
#     '0927133454',
#     '0942247594'
#     ])
#     idpersona_liquidar_deuda= []
#     for bloqueado in bloqueados:
#         rubros = Rubro.objects.filter(status=True, matricula_id=bloqueado.id)
#         totalrubros = Rubro.objects.filter(status=True, matricula_id=bloqueado.id).count()
#         totalcancelado = 0
#         for rubro in rubros:
#             if rubro.cancelado:
#                 totalcancelado += 1
#         if totalcancelado == totalrubros:
#             idpersona_liquidar_deuda.append(bloqueado.inscripcion.persona.id)
#
#
#     matriculados_periodo_actual = Matricula.objects.filter(status=True, nivel__periodo_id=177, inscripcion__persona__id__in = idpersona_liquidar_deuda)
#     for matriculadoactual in matriculados_periodo_actual:
#
#         rubros_periodo_actual = Rubro.objects.filter(status=True, matricula_id=matriculadoactual.id, cancelado=False)
#         if rubros_periodo_actual:
#             print('liquidar rubro -', matriculadoactual.inscripcion.persona.cedula)
#             for rubroact in rubros_periodo_actual:
#                 if not rubroact.cantidad_pagos() > 0:
#                     if not rubroact.bloqueado:
#                         subtotal0 = 0
#                         subtotaliva = 0
#                         iva = 0
#                         if rubroact.iva.porcientoiva > 0:
#                             subtotaliva = Decimal(rubroact.saldo / (rubroact.iva.porcientoiva + 1)).quantize(
#                                 Decimal('.01'))
#                             iva = Decimal(rubroact.saldo - subtotaliva).quantize(Decimal('.01'))
#                         else:
#                             subtotal0 = rubroact.saldo
#
#                         pago = Pago(rubro=rubroact,
#                                     fecha=datetime.now().date(),
#                                     subtotal0=subtotal0,
#                                     subtotaliva=subtotaliva,
#                                     iva=iva,
#                                     valordescuento=0,
#                                     valortotal=rubroact.saldo,
#                                     efectivo=False)
#                         pago.save()
#                         liquidacion = PagoLiquidacion(fecha=datetime.now().date(),
#                                                       motivo='Liquidación de rubro según resolución OCS-SO-6-2023-No8',
#                                                       valor=rubroact.saldo)
#                         liquidacion.save()
#                         liquidacion.pagos.add(pago)
#                         rubroact.save()
#                         matriculadoactual.estado_matricula = 2
#                         matriculadoactual.save()
#                     else:
#                         print('tiene rubro bloqueado',matriculadoactual.inscripcion.persona.cedula)
#                 else:
#                     print('tiene rubro con pagos', matriculadoactual.inscripcion.persona.cedula )
#
#
# except Exception as ex:
#     print(ex)
#     transaction.set_rollback(True)

cedulasDatosEn = ["0604067470", "0930184320", "0940326838", "1003156948", "1003156948", "0958178535",
                             "0958178535", "1203404643", "0909378465", "0942799198", "0930835137", "0704932615",
                             "0952024115", "1103352199", "1103352199", "1103352199", "1722063243", "0958323784",
                             "0958323784", "0921173142", "0931090831", "0931090831", "0958687675", "0955019138",
                             "0927160994", "0921409496", "0955399514", "0926376211", "0942376963", "0922057088", "0104550405", "0930328695", "0955467691", "1900526326", "0955751193", "1203592827", "0914891510", "1756471411", "1207201995", "1311567851", "1311567851", "0915038186", "0750118614", "1715077002", "0704365618", "0922987508", "1313456103", "1313456103", "1313456103", "1205688581", "0924431067", "1204779647", "1204779647", "0944136563", "0944136563", "0942757758", "2400010175", "0921984449", "0941349920", "0927739706", "0927739706", "0927739706", "1751284686", "1312618257", "0954875225", "0925106148", "0927996868", "0956401574", "0956401574", "0943571570", "0943571570", "1205538109", "1003295514", "0923168017", "0923168017", "0941334740", "1723299879", "0923073829", "0107263360",
                             "0107263360", "0924716764", "0706310943", "0706310943", "0706310943", "0706695681", "0956918502", "0956918502", "0924777436", "0924777436", "0704489798", "0704489798", "0926559121", "0927705053", "0942251877", "0202040481", "0944263466", "0944263466", "0944263466", "0953598646", "0703113886", "2300121965", "2300121965", "2300121965", "0922269543", "0955024864", "0955024864", "1754306791", "0923568950", "0923568950", "0942338757", "1804636338", "1804636338", "0952354892", "0952354892", "0952354892", "1204324345", "0927843045", "0603224411", "0925800633", "0926927328", "0707078630", "0924834245", "1105124430", "0927670380", "1105449696", "0803670025", "0803670025", "0703583120","1721760765", "0951902022", "0914214416", "0923795942", "0923795942", "0923795942", "0952881985", "0952881985", "0952881985", "0959053943", "0930179882", "1207479260", "1207479260", "1207479260", "0928369461", "0604244947", "1103999676", "0401688536", "0920463312", "0706233269", "1207775402", "1207775402", "0705952554", "0705952554", "0926423849", "0953162625", "1712432903", "1004631303", "0923894752", "0958393332", "0958393332", "0917786394", "0941643108", "0401246863", "1104664097", "1104664097", "1104664097", "0930898622", "1206786350", "1206786350", "1206322016", "0917501561", "2300135833", "2300135833", "0941881070", "1723310056", "1724754070", "1724754070", "1724754070", "0928105592", "1720450269", "1720450269", "0504030057", "0504030057", "0504030057", "1103379671", "0928797265", "0918865288", "0918865288", "0918865288", "0940568512", "0940568512", "0944056480", "0940123284", "0941377368", "0924602865", "0502708910", "0502708910", "0502708910", "0705096469", "0705096469", "0941333445", "0951285162", "0302655642", "0940974975", "0924075369", "0928819713", "0926717760", "0930458484", "0926176132", "0928172352", "0942500877", "0504111170", "1756158752", "0703729186", "0928987783", "0750193211", "0750193211", "0750193211", "1711948685", "0919820043", "0919820043", "0919820043", "2350201360", "1500496565", "0957077225", "0957077225", "0706990140", "0706990140", "1104969736", "1208390946", "1208390946", "1208390946", "0202231155", "1204803918", "0952883676", "0952883676", "0952883676", "1150594180", "0955367834", "0922863998", "1752296853", "1752296853", "0704409648", "0705364198", "0102803079", "0706040268", "0706708740", "1717606261", "0920235074", "0924727704", "0924727704", "0751037169", "1309402004", "1309402004", "1208295814", "0957488901", "0928765197",
                  "0920930211", "0942265208", "1753782273", "0925749707", "0958763146", "0958763146", "0926162629",
                  "2300795826", "0931940795", "0925521122", "0953278959", "0952496347", "0950564682", "0919871798",
                  "1206613307", "0924516180", "0201870888", "0706356334", "0603128877", "0921282984", "0924396823",
                  "0929489920", "0956549943", "0919412577", "0705804227", "0929580207", "0916958192", "0503793960",
                  "2100829064", "0705437663", "0924589948", "0956669709", "0924609654", "0943821918", "0951961747",
                  "0932042617", "1715831788", "0929351260", "0954284170", "0707172664", "0914109954", "0850572801",
                  "0951306356", "0928106087", "1724349574", "1723393722", "1715384275", "0604143537", "1716341225",
                  "0930155098", "0929896785", "0929011666", "0953367422", "0604039305", "0927427815", "1207604438",
                  "1105421513", "0958425985", "0954199964", "0919232603", "0919425892", "1204931230", "1208926368",
                  "1103915482", "0926146788", "0929347292", "1104494099", "0950490870", "0930485834", "1203036031",
                  "1706073366", "0921808457", "1208013118", "0926133547", "1724137177", "0917885469", "1724462237",
                  "2400298556", "1725122236", "0954782082", "0955342472", "0924810021", "0202367637", "1720882164",
                  "1104612997", "0922318894", "0922318894", "0705561405", "0953514080", "0940453780", "0802744250",
                  "0924521255", "0958275141", "0928600212", "0928600212", "1720831369", "0944148576", "0923555767",
                  "0930101480", "0706557626",
                  "2450441817", "0705004943", "0922574520", "1716038961", "1716038961", "0957757578", "0958908824",
                  "0958908824", "0958908824", "0923573679", "0929062305", "0940236409", "0915207823", "1726600297",
                  "0930178496", "0959440298", "0923701544", "1104109887", "1717709925", "0804152999", "1717219289",
                  "1104567217", "0920191103", "0914828306", "0926681578", "0954771416", "0953408796", "0953408796",
                  "0921072443", "0930609417", "1204044968", "1204837031", "1314564269", "1104711690", "0921664926",
                  "0750057333", "0706323359", "FB392233", "1803496239", "0940293194", "0928269695", "0928269695",
                  "0802802454", "0953204781", "0923711170", "2100771233", "0605048453", "0919970426", "0932045313",
                  "1003992052", "1728185016", "0604201350", "1206387936", "0952555910", "0916474406", "0926124470",
                  "1206236901", "1206324590", "0606168813", "0952050680", "1707498372", "1001930229", "1001930229",
                  "1400522700", "0921410924", "1204833923", "1207982511", "0705873438", "0202031746", "0912747888",
                  "0704204007", "0911363166", "0604668038", "0202195913", "0952789790", "0952789790", "0921194874",
                  "0918663428", "0923399513", "1724647118", "0926426529", "0917279291", "0922837158", "0930910302",
                  "1713072385", "1752764801", "0958750242", "0923582746", "0942086554", "0942086554", "0930777883",
                  "0930777883", "1002182812", "2100603352", "0503097883", "1104729783", "1250118583", "0911063394",
                  "0303162655", "0703984039",
                  "0603928441", "0955390885", "0919647156", "1313024844", "0956022792", "1307884112", "0924084023",
                  "0926693912", "0955798087", "0924121270", "1004163323", "0941342693", "0105868699", "1712621505",
                  "1722797071", "1716989031", "0941536674", "1709890188", "1751340371", "0503108193", "0925648693",
                  "0705049013", "0104261532", "0104261532", "0928288018", "0704459544", "0929766541", "0929766541",
                  "0953406600", "0805418100", "0940749187", "0926487257", "1316824844", "0959170671", "0930411384",
                  "1312163239", "0942113697", "1850123207", "0705189975", "0923122287", "1250181938", "0803012384",
                  "0850203175", "0850203175", "0850203175", "0928047992", "0941142481", "0941142481", "0924734841",
                  "0929487031", "0919619775", "0942439563", "0704320217", "0942071218", "1709267189", "0942254228", "0941528481", "0942029190", "0952300168", "0931645444", "0943120964", "0958853822", "0927999599","0302667548", "1450174576", "0941990483","0950899443", "0955872783", "0955701008","0961256005", "0941320806", "0955595145", "0955595145", "0955791652", "0927953547", "0959034745", "0959034745", "0940496565", "0957229438", "0942194739", "0957420680", "0957420680", "0957420680", "0928551209", "0941526741", "0941114415", "0941114415", "0940350432", "0940350432", "0940350432", "0940350432", "0943692723", "0943692723", "0929315992", "0940111719", "0940111719", "0924604739", "0919413146", "0919413146", "0302868328", "0927576975", "0940782428", "0958635625", "0958026692", "0958026692", "0958026692", "0955920053", "0955920053", "0924309016", "0958577710", "0940153513", "0705113736", "0942071663", "0942071663", "0942071663", "0952161388",
                         "0941600215", "0954344149", "0953353216", "0958538977", "0958538977", "1205831207", "0929225993", "0953084530", "1206554014", "1206554014", "0927434233", "0929578706", "0950937060", "0923000475", "0941659021", "0930728266", "0930728266", "0928598093", "0952522415", "2450090291", "2450090291", "0942095019", "0942356064", "0942356064", "0942356064", "0957292634", "0706468378", "0941605495", "0941605495", "0302786397", "0928055326", "0929425528", "0929425528", "0923666184", "0954733325", "0943003913", "0925284002", "0958601536", "0942248451", "0940609324", "0940609324", "0940609324", "0940609324", "0930909791", "0951906064", "0940665524", "0941984106", "0941984106", "0953947686", "0956265144", "0954762175", "0957793912", "0957793912", "0955480041", "0926332263", "0940144454", "0955803952", "0302463088",
                         "0954158093", "0952559490", "0957978786", "0942193665", "0953960010", "0704692847", "0704692847", "0940323470", "0954888160", "1726499922", "0942490236", "0942490236", "1205915208", "0941601916", "0941601916", "0915686182", "0915686182", "0850795618", "0954948055", "0942058736", "0928981513", "0921525143", "0302271432", "0302271432", "0922981345", "0961521077", "1205283151", "0928792498", "0953745700", "0953745700", "0941336489", "0953852308", "0953852308", "0953156049", "0953156049", "0942242207", "0923656334", "0959092925", "0959092925", "0930963418", "0941120826", "0940996630", "0940935547", "0940935547", "0940390586", "1317948485", "0941325789", "0941325789", "0952464048", "0940905029", "1206706747", "0923811434", "0929134286", "0929134286", "0955787924", "0942055484", "0940810070", "0958967465", "0931770242", "0931483648", "0931483648", "0952659290", "0952166742", "0952166742",
                         "0942439860", "0941529042", "0953062353", "0953062353", "0923208094", "0921177788", "0605048149", "0952546299", "1207839893", "0940114697", "0929856367", "0944385905", "0942121047", "0942121047", "0942121047", "0959308156", "0950946921", "0950946921", "0956963177", "0927385351", "0956138960", "0955495163", "0941157729", "0941157729", "0931718332", "0942365966", "0942365966", "0924013741", "0924013741", "0926151226", "0926151226", "0926151226", "0928950278", "0953486446", "0953486446", "0928790724", "0957635709", "0944272046", "0940104813", "0943598011", "0940582471", "0940582471", "0943190074", "0943190074", "0924019045", "0942491705", "0942491705", "0927959742", "0955784210", "0923220909", "0923220909", "0923220909", "0955129226", "0928067040", "0955956917", "0955956917", "0943780890", "0952560571", "0952560571", "0929566883", "0923170229", "0923170229", "0923170229", "0929076149", "0929076149", "0952117497", "0952117497", "0942097189", "0942097189",
                         "0750133571", "0929362499", "0941881781", "0931312086", "0951194315", "0951194315", "1729750842", "1751219278", "0952118446", "0952118446", "0952118446", "0955508148", "0942531534", "0915864961", "0952359230", "0952359230", "0951688183", "0955614599", "0923937288", "0930159884", "0930468707", "0954970083", "0941798639", "0926302365", "0926302365", "0926302365", "0923375562", "0940142532", "0940142532", "0929158202", "0919612150", "0940906266", "0940935174", "0940935174", "0951896588", "0951896588", "0942095373", "0942095373", "0942095373", "0952061281", "0955416599", "0929973519", "0942233495", "0941601445", "0941601445", "1207506914", "1207506914", "0954331880", "0952780955", "0606230886", "1207344233", "0957886526", "0957886526", "0957886526", "2101003040", "2101003040", "2101003040", "2101003040", "0952487239", "0954640512", "0954640512", "0928261536", "0954144325", "0954144325", "0955509179", "0955509179", "0942098039", "0942126590",
                         "0605190982", "0943382531", "0942193897", "0942193897", "0918502535", "0954327268", "0955189758", "0953506318", "0923647614", "0929593366", "0930724711", "0931713929", "0931713929", "0951948223", "0951804467", "0951804467", "0952059459", "0959423732", "0955391040", "0955391040", "0955391040", "0921655601", "0930551254", "0930551254", "0929266427", "0929266427", "0928477793", "0922980966", "0922980966", "0951971043", "0924308299", "0920779121", "0920779121", "0955267042", "0952386944", "0955369467", "0950926550", "0955891304", "0929249324", "0943639732", "0926403049", "0926402652", "0944169853", "0944169853", "0605006444", "0605006444", "0107054603", "0953826500", "0953826500", "0928858224", "0928858224", "0957090228", "0957090228", "0953937216", "0955627021", "0953194636", "0926858739", "0925458358", "0958195752", "1724929292", "0927311712", "0927311712"

]

def reasjute_horas_creditos_malla_modulos_ingles_2(cedulaDatos):
    total= len(cedulaDatos)
    procesados = 0
    for cedula in cedulaDatos:
        inscripcions = Inscripcion.objects.filter(status=True, persona__cedula=cedula)
        for inscripcion in inscripcions:
            if not inscripcion.usado_graduados() or not inscripcion.egresado():
                recordacademico = inscripcion.recordacademico_set.filter(modulomalla__isnull=False, aprobada=True, creditos=0, status=True)
                for record in recordacademico:
                    if record.historicorecordacademico_set.filter(status=False, fecha=record.fecha).exists():
                        recordfalse = record.historicorecordacademico_set.filter(status=False, fecha=record.fecha)
                        recordfalse.delete()
                    print(f"Inscripcion: {inscripcion.__str__()}")
                    record.actualizar()
                    historico = record.mi_historico()
                    historico.creditos = record.modulomalla.creditos
                    historico.horas = record.modulomalla.horas
                    historico.validapromedio = False
                    historico.valida = True
                    historico.save()
                    record.creditos = record.modulomalla.creditos
                    record.horas = record.modulomalla.horas
                    record.validapromedio = False
                    record.valida = True
                    record.save()

                print(f"Final de Inscripcion: {inscripcion.__str__()}")
        procesados += 1
        print(procesados, "de", total )
        print(f"------------------------------------------------")
    print('------------------ FIN CREDITOS INGLES')

# reasjute_horas_creditos_malla_modulos_ingles_2(cedulasDatosEn)

#computacion
def actualizar_creditos_computacion(cedulaDatos):
    try:
        linea = 1
        total = len(cedulaDatos)
        procesados = 0
        for cedula in cedulaDatos:
            for inscripcion in Inscripcion.objects.filter(status=True, persona__cedula=cedula):
            # print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
                inscripcionold = inscripcion.inscripcionold
                # asigmal = AsignaturaMalla.objects.get(asignatura_id=1053, malla_id=32)
                for asigmal in AsignaturaMalla.objects.filter(malla_id=32):
                    modulos = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion, asignatura_id=asigmal.asignatura_id, creditos=0).order_by('id')
                    for record2 in modulos:
                            print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
                            record2.creditos = asigmal.creditos
                            record2.save()
                            historico =  HistoricoRecordAcademico.objects.filter(status=True, recordacademico = record2).order_by('-aprobada', '-fecha')[0]
                            historico.creditos = record2.creditos
                            historico.save()
                            # record2.actualizar()
                            print('------------------ COMPUP %s - %s' % (linea, record2.asignatura))
                            linea += 1
        print('------------------ FIN CREDITOS COMPUTACION')

        linea += 1
        procesados += 1
        print(procesados, "de", total)
    except Exception as ex:
        print('error: %s' % ex)

# actualizar_creditos_computacion(cedulasDatosEn)

def actualizar_creditos(inscripcion):
    records = inscripcion.recordacademico_set.filter(aprobada=True, status=True)
    computacion = AsignaturaMalla.objects.values_list('asignatura_id', flat=True).filter(malla_id=32)
    if inscripcion.inscripcionmalla_set.filter(status=True).exists():
        for record in records:
            modulo_malla= inscripcion.asignatura_en_modulomalla(record.asignatura)
            if modulo_malla:
                record.creditos = modulo_malla.creditos
                record.horas = modulo_malla.horas
                record.save(update_asignaturamalla=False)
                record.historicorecordacademico_set.filter(status=True, aprobada=True).update(creditos=record.creditos,
                                                                                              horas=record.horas)
            if record.tiene_acta_curso():
                acta = record.acta_materia_curso()
                if acta.creditos>0 and record.creditos == 0:
                    record.creditos = acta.creditos
                    record.horas = acta.horas
                elif record.asignatura_id in computacion and record.creditos == 0:
                    asigcompu = AsignaturaMalla.objects.get(asignatura=record.asignatura_id, malla_id=32)
                    record.creditos = asigcompu.creditos
                record.save(update_asignaturamalla=False)
                record.historicorecordacademico_set.filter(status=True, aprobada=True).update(creditos=record.creditos,
                                                                                 horas=record.horas)

def actualizar_creditos_derecho():
    try:
        inscripciones = InscripcionMalla.objects.filter(malla__carrera__modalidad__in=[1,2],
                                                        malla__carrera__coordinacion__id__in=[2,3,4,5])
        total  = inscripciones.count()
        procesados = 0
        for inscripcionmalla in inscripciones:
            # inscripcion = inscripcionmalla.inscripcion
            # inscripcion.actualizar_creditos()
            actualizar_creditos(inscripcionmalla.inscripcion)
            procesados += 1
            print(procesados, "de", total)
            print("%s"%inscripcionmalla.inscripcion)

    except Exception as ex:
        print('error: %s' % ex)
