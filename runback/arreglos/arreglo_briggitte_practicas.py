#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.http import HttpResponse

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

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
from django.db import connections, transaction

from datetime import datetime
from sga.models import ProfesorMateria, GruposProfesorMateria, AlumnosPracticaMateria, MateriaAsignada, Materia, \
    Matricula
from sga.templatetags.sga_extras import encrypt

id_periodo = 177
facs = 1 #Facultad de salud

cedulasOctavo = ['0953230380',
'0952650810',
'0952898419',
'0942244260',
'1351033582',
'0928186345',
'0942342122',
'0942191867',
'0942115478',
'1729785673',
'0923782635',
'0931062400',
'0923339881',
'0926713363',
'0942775743',
'0958158628',
'0958361503',
'0944228170',
'0927452219',
'0927126938',
'0942652058',
'0924561392',
'1206452961',
'0950922583',
'2100380985',
'0940745185',
'0942125485',
'0956449672',
'0942246356',
'0302342324',
'0940167240',
'0953035599',
'0928061944',
'0952032993',
'0923498695',
'0920817723',
'1850110634',
'0956629240',
'0703923359',
'1727389965',
'1207132570',
'0703624700',
'1715798060',
'0916498678',
'0923709315',
'0952094480',
'0932110067',
'0927180497',
'0952008639',
'0955423140',
'0928269463',
'0957543150',
'0942338757',
'0921984449',
'0923894752',
'0925000606',
'0706695681',
'0941349920',
'0940172646',
'0706233269',
'0750258907',
'0705352086',
'0952024115',
'0928358993',
'0940453608',
'0704932615',
'0704684356',
'0954954798',
'0926304452',
'0928103472',
'0923076061',
'0941543621',
'0605987510',
'0928879956',
'0603764226',
'1207471051',
'0928058379',
'0941996795',
'0940707045',
'0953811320',
'0941228223',
'0959287749',
'0955307137',
'0928939115',
'0958697674',
'0942124470',
'0953543675',
'0944341429',
'0929967560',
'0941144354',
'0919572958',
'1722923594',
'0942097072',
'0931109318',
'0958688038',
'0928935691',
'0706280229',
'0929975332',
'0924600406',
'0302229711',
'1207229236',
'0950225714',
'0931092613',
'0952945947',
'0940326168',
'0942234790',
'0928682665',
'0605524669',
'0942655598',
'1720855996',
'1713630786']

cedulasNoveno = ['0704549518',
'0924211212',
'0953845047',
'1002486775',
'1204814295',
'0923359426',
'0705581049',
'0940325541',
'0917236416',
'0943401174',
'0603499468',
'1719717280',
'0919454561',
'1315149698',
'1400989610',
'0202209599',
'0921705976',
'1105232514',
'0953907342',
'1805181375',
'0202520292',
'0928034594',
'1308968757',
'0956649073',
'0951613967',
'0922254941',
'0705671600',
'0927763466',
'0940956105',
'0924183841',
'0915571780',
'0750995920',
'0928043397',
'0922182480',
'0953661709',
'1313965400',
'1207744507',
'0955930987',
'1206149351',
'1003689385',
'0942917683',
'0915529986',
'0942110834',
'0958275141',
'0916848849',
'0940749187',
'0920611472',
'0605704683',
'0928653211',
'2100472782',
'0704915081',
'1207269398',
'0926162629',
'0953362951',
'0922698675',
'1208934313',
'0931570311',
'0940769110',
'0301376505',
'0940575756',
'0940539141']
deudores = []
contador = []
def desmatricular(periodo,carrera,id_Asignatura,cedulasDatos):
    cont = 0
    for cedula in cedulasDatos:
        for materiaasignada in MateriaAsignada.objects.filter(status=True, materia__status=True,
                                                  materia__nivel__status=True,
                                                  materia__asignatura_id=id_Asignatura, materia__nivel__periodo_id=periodo,
                                                  matricula__inscripcion__persona__cedula=cedula,
                                                  matricula__inscripcion__carrera_id=carrera):
            materia = materiaasignada.materia
            matricula = materiaasignada.matricula
            if materiaasignada.matricula.cantidad_rubros_matricula() > 0:
                deudores.append(cedula)
            else:
                print(matricula.inscripcion, matricula.inscripcion.carrera, materiaasignada.materia)
                materia.cupo -= 1
                materia.totalmatriculadocupoadicional -= 1
                materia.save()
                materiaasignada.delete()
                matricula.actualizar_horas_creditos()
                cont = cont + 1
    contador.append(cont)

#DESMATRICULAR ESTUDIANTES
#ADMINISTRACION DE EMPRESAS 2019 - DISEÑO DE INTEGRACION CURRICULAR
desmatricular(id_periodo, 140, 3978, cedulasOctavo)
#BIOTECNOLOGIA 2019 - INTEGRACIÓN CURRICULAR
desmatricular(id_periodo, 146, 4355, cedulasOctavo)
#COMUNICACIÓN 2019	UNIDAD DE INTEGRACIÓN CURRICULAR
desmatricular(id_periodo, 143, 4345, cedulasOctavo)
#COMUNICACIÓN EN LÍNEA	TRABAJO DE TITULACIÓN I [TTI]
desmatricular(id_periodo, 131, 1932, cedulasOctavo)
#CONTABILIDAD Y AUDITORIA 2019	DISEÑO DE INTEGRACION CURRICULAR
desmatricular(id_periodo, 141, 3978, cedulasOctavo)
#DERECHO EN LÍNEA	DISEÑO DE LA INVESTIGACIÓN [024DI07]
desmatricular(id_periodo, 126, 2463, cedulasOctavo)
#ECONOMIA 2019	INTEGRACIÓN CURRICULAR
desmatricular(id_periodo, 158, 4355, cedulasOctavo)
#EDUCACIÓN BÁSICA EN LÍNEA	TRABAJO DE TITULACIÓN I [TTI]
desmatricular(id_periodo, 135, 1932, cedulasOctavo)
#EDUCACIÓN INICIAL 2019	INTEGRACIÓN CURRICULAR EDUINI-08IC
desmatricular(id_periodo, 149, 4447, cedulasOctavo)
#INGENIERÍA AMBIENTAL 2019	DISEÑO DE INTEGRACION CURRICULAR
desmatricular(id_periodo, 151, 3978, cedulasOctavo)
#INGENIERIA INDUSTRIAL 2019	DISEÑO DE INTEGRACIÓN CURRICULAR [0]
desmatricular(id_periodo, 153, 4271, cedulasOctavo)
#LICENCIATURA EN PSICOLOGIA 2019	INTEGRACIÓN CURRICULAR
desmatricular(id_periodo, 137, 4355, cedulasOctavo)
#PEDAGOGÍA DE LA ACTIVIDAD FISICA Y DEPORTE 2019	DISEÑO DE INTEGRACION CURRICULAR
desmatricular(id_periodo, 142, 3978, cedulasOctavo)
#PEDAGOGÍA DE LA LENGUA Y LA LITERATURA	UNIDAD DE INTEGRACIÓN CURRICULAR
desmatricular(id_periodo, 170, 4345, cedulasOctavo)
#PEDAGOGÍA DE LOS IDIOMAS NACIONALES Y EXTRANJEROS 2019	UNIDAD DE INTEGRACIÓN CURRICULAR
desmatricular(id_periodo, 157, 4345, cedulasOctavo)
#PSICOLOGÍA EN LÍNEA	TRABAJO DE TITULACIÓN I [TTI]
desmatricular(id_periodo, 132, 1932, cedulasOctavo)
#SOFTWARE 2019	DISEÑO DE INTEGRACIÓN CURRICULAR [0]
desmatricular(id_periodo, 139, 4271, cedulasOctavo)
#TRABAJO SOCIAL 2019	DISEÑO DE INTEGRACION CURRICULAR
desmatricular(id_periodo, 160, 3978, cedulasOctavo)
#TRABAJO SOCIAL EN LÍNEA	SEMINARIO DE TITULACION I
desmatricular(id_periodo, 130, 3649, cedulasOctavo)

#EDUCACIÓN 2019	UNIDAD DE INTEGRACIÓN
desmatricular(id_periodo, 156, 4380, cedulasNoveno)
#EDUCACIÓN INICIAL EN LÍNEA	TRABAJO DE TITULACIÓN I [TTI]
desmatricular(id_periodo, 127, 1932, cedulasNoveno)
#FISIOTERAPIA	TITULACIÓN I
desmatricular(id_periodo, 112, 3224, cedulasNoveno)
print(f"Alumnos desmatriculados: ",sum(contador))
if(len(deudores)>0):
    print("**********************************ALUMNOS CON DEUDA**********************************")
    for deudor in deudores:
        print(deudor)
##ARREGLO ASIGANCION DE GRUPOS DE PRACTICA
# def matricular_estudiantes_cursos_practicos(matricula, alumnsingrupo, profesormateria, materiasasignada, grupoprofesor,
#                                             matriculaid):
#     try:
#         with transaction.atomic():
#             if (len(alumnsingrupo) == 0):
#                 alumnosingrupo = AlumnosPracticaMateria(
#                     profesormateria=profesormateria,
#                     materiaasignada=materiasasignada,
#                     grupoprofesor=grupoprofesor)
#                 alumnosingrupo.save()
#                 print(f"Estudiante matriculado: {alumnosingrupo.materiaasignada.matricula}")
#             else:
#                 alumnsingrupo[0].grupoprofesor = grupoprofesor
#                 alumnsingrupo[0].save()
#                 print(f"Asignacion de grupo matriculado: {alumnsingrupo[0].materiaasignada.matricula}")
#             conflicto = matricula.verificar_conflicto_en_materias()
#             if conflicto:
#                 print(conflicto)
#                 if(alumnosingrupo):
#                     alumnosingrupo.delete()
#                 else:
#                     alumnsingrupo[0].delete()
#                 print(f"Estudiante no se puede matricular por conflicto de horario. Matricula: {matriculaid}")
#     except Exception as ex:
#         print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
#         print(str(ex))

#
# try:
#
#     cursor = connections['sga_select'].cursor()
#     materias = f"""
#                     SELECT materia.id
#                     FROM sga_gruposprofesormateria grupoprofesor
#                     INNER JOIN sga_profesormateria profesormateria ON (grupoprofesor.profesormateria_id = profesormateria.id)
#                     INNER JOIN sga_materia materia ON (profesormateria.materia_id = materia.id)
#                     INNER JOIN sga_nivel nivel ON (materia.nivel_id = nivel.id)
#                     inner join sga_asignaturamalla asmalla on asmalla.id=materia.asignaturamalla_id
#                     inner join sga_malla malla on malla.id=asmalla.malla_id
#                     inner join sga_asignatura asignatura on asignatura.id=materia.asignatura_id
#                     inner join sga_carrera carrera on malla.carrera_id=carrera.id
#                     inner join sga_nivelmalla nivelmalla on nivelmalla.id=asmalla.nivelmalla_id
#                     INNER JOIN sga_coordinacion_carrera coordinacioncarrera ON coordinacioncarrera.carrera_id = carrera.id
#                     INNER JOIN sga_coordinacion coordinacion ON coordinacion.id = coordinacioncarrera.coordinacion_id
#                     WHERE nivel.periodo_id = {id_periodo} AND coordinacion.id != {facs} GROUP BY materia.id HAVING COUNT(*)=1;
#             """
#     cursor.execute(materias)
#     resultsmaterias = cursor.fetchall()
#     for result in resultsmaterias:
#         materiaid = result[0]
#         profesoresygrupos = f"""
#                                 SELECT grupoprofesor.id, profesormateria.id
#                                 FROM sga_gruposprofesormateria grupoprofesor
#                                 INNER JOIN sga_profesormateria profesormateria ON (grupoprofesor.profesormateria_id = profesormateria.id)
#                                 INNER JOIN sga_materia materia ON (profesormateria.materia_id = materia.id)
#                                 WHERE materia.id = {materiaid};
#         """
#         cursor.execute(profesoresygrupos)
#         resultprofesoresygrupos = cursor.fetchall()
#         grupoprofesor_id = resultprofesoresygrupos[0][0]
#         profesormateria_id = resultprofesoresygrupos[0][1]
#         alumnossingrupo = f"""SELECT DISTINCT sga_materiaasignada.id, sga_materiaasignada.matricula_id, sga_materiaasignada.materia_id
#                                         FROM sga_materiaasignada
#                                         INNER JOIN sga_matricula ON (sga_materiaasignada.matricula_id = sga_matricula.id)
#                                         INNER JOIN sga_inscripcion ON (sga_matricula.inscripcion_id = sga_inscripcion.id)
#                                         INNER JOIN sga_persona ON (sga_inscripcion.persona_id = sga_persona.id)
#                                         WHERE (sga_materiaasignada.materia_id = {materiaid}
#                                         AND NOT sga_materiaasignada.retiramateria
#                                         AND sga_materiaasignada.status
#                                         AND NOT (sga_materiaasignada.id
#                                         IN (SELECT sga_alumnospracticamateria.materiaasignada_id
#                                             FROM sga_alumnospracticamateria
#                                             WHERE (sga_alumnospracticamateria.grupoprofesor_id = {grupoprofesor_id}
#                                             AND sga_alumnospracticamateria.profesormateria_id = {profesormateria_id}
#                                             AND sga_alumnospracticamateria.status))))
#                                     """
#         cursor.execute(alumnossingrupo)
#         resultsalumnossingrupo = cursor.fetchall()
#         if (len(resultsalumnossingrupo) > 0):
#             print(f" Materia: {materiaid} Profesor: {profesormateria_id} Grupo: {grupoprofesor_id}")
#             print(len(resultsalumnossingrupo))
#
#             for resultalumnossingrupo in resultsalumnossingrupo:
#
#                 materiaasignada_id = resultalumnossingrupo[0]
#                 profesormateria = ProfesorMateria.objects.get(id=profesormateria_id)
#                 grupoprofesor = GruposProfesorMateria.objects.get(id=grupoprofesor_id)
#                 materiasasignada = MateriaAsignada.objects.get(id=materiaasignada_id)
#                 materia = Materia.objects.get(id=materiaid)
#                 matriculaid = materiasasignada.matricula.id
#                 matricula = Matricula.objects.get(pk=matriculaid)
#
#                 alumnsingrupo = AlumnosPracticaMateria.objects.filter(profesormateria=profesormateria,
#                                                                       materiaasignada=materiasasignada, status=True)
#                 matricular_estudiantes_cursos_practicos(matricula, alumnsingrupo, profesormateria, materiasasignada, grupoprofesor, matriculaid)
#
# except Exception as ex:
#     print(str(ex))