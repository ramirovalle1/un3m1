# -*- coding: utf-8 -*-
import os
import sys

from django.db import transaction

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *

periodo = Periodo.objects.get(id=153)

# @transaction.atomic()
# def copiarniveles(periodo, periodocopiar, inicio=convertir_fecha('28-11-2022'), fin=convertir_fecha('24-03-2023')):
#     try:
#         for coordinacion in Coordinacion.objects.filter(id__in=[2,3,5]):
#             # niveles = periodo.nivel_set.filter(status=True,
#             #                                nivellibrecoordinacion__coordinacion=coordinacion).exclude(nivellibrecoordinacion__coordinacion_id=1)
#             # print('BORRANDO NIVELES DE PERIODO (153) DE FACULTAD '+ str(coordinacion))
#             # niveles.delete()
#             # if not periodocopiar.nivel_set.filter(status=True, nivellibrecoordinacion__coordinacion=coordinacion).exclude(nivellibrecoordinacion__coordinacion_id=1).exists():
#             #     print('NIVELES DE PERIODO (153) DE FACULTAD ' + str(coordinacion)+ 'BORRADOS')
#             # se crea los niveles copiando los niveles del periodo partida al periodo destino
#             for niveles in periodocopiar.nivel_set.filter(status=True,
#                                                           nivellibrecoordinacion__coordinacion=coordinacion).exclude(nivellibrecoordinacion__coordinacion_id=1):
#                 if not Nivel.objects.filter(status=True, periodo=periodo, sede=niveles.sede, carrera=niveles.carrera,
#                                             sesion=niveles.sesion, malla=niveles.malla, nivelmalla=niveles.nivelmalla,
#                                             paralelo=niveles.paralelo).exists():
#                     print('CREANDO NIVEL.........................')
#                     print('')
#                     print('')
#                     print('')
#                     print('')
#                     print('')
#                     nivelnew = Nivel(periodo=periodo, sede=niveles.sede, carrera=niveles.carrera,
#                                      modalidad=niveles.modalidad,
#                                      sesion=niveles.sesion, malla=niveles.malla, nivelmalla=niveles.nivelmalla,
#                                      grupo=niveles.grupo, paralelo=niveles.paralelo, inicio=inicio,
#                                      fin=fin, capacidadmatricula=niveles.capacidadmatricula,
#                                      nivelgrado=niveles.nivelgrado, aplicabecas=niveles.aplicabecas,
#                                      distributivoaprobado=niveles.distributivoaprobado,
#                                      responsableaprobacion=niveles.responsableaprobacion,
#                                      visibledistributivomateria=niveles.visibledistributivomateria,
#                                      fechatopematricula=fin, fechafinquitar=fin,
#                                      fechatopematriculaes=fin, fechaprobacion=inicio,
#                                      fechatopematriculaex=fin,
#                                      fechacierre=fin, fechainicioagregacion=inicio, fechafinagregacion=fin
#                                      )
#                     nivelnew.save()
#                 else:
#                     nivelnew = Nivel.objects.get(status=True, periodo=periodo, sede=niveles.sede,
#                                                  carrera=niveles.carrera,
#                                                  modalidad=niveles.modalidad, paralelo=niveles.paralelo,
#                                                  sesion=niveles.sesion,
#                                                  malla=niveles.malla, nivelmalla=niveles.nivelmalla)
#                 print('NIVEL: ........' + str(nivelnew))
#                 print(' ')
#                 print(' ')
#                 print(' ')
#                 print(' ')
#                 print(' ')
#                 #  se crea las materias en base a los niveles que se va creando al periodo destino
#                 nivellibrecoordinacion = nivelnew.coordinacion(coordinacion)
#                 for materia in niveles.materia_set.filter(status=True):
#                     if not Materia.objects.filter(status=True, nivel=nivelnew, asignatura=materia.asignatura,
#                                                   paralelo=materia.paralelo).exists():
#                         materianew = Materia(nivel=nivelnew, asignatura=materia.asignatura,
#                                              asignaturaold=materia.asignaturaold,
#                                              asignaturamalla=materia.asignaturamalla,
#                                              identificacion=materia.identificacion,
#                                              alias=materia.alias, paralelo=materia.paralelo, horas=materia.horas,
#                                              horassemanales=materia.horassemanales, creditos=materia.creditos,
#                                              inicio=periodo.inicio, fin=fin, fechafinasistencias=fin,
#                                              rectora=materia.rectora, cerrado=materia.cerrado, fechacierre=fin,
#                                              tutoria=materia.tutoria, practicas=materia.practicas, grado=materia.grado,
#                                              cupo=materia.cupo, modeloevaluativo=materia.modeloevaluativo,
#                                              usaperiodoevaluacion=materia.usaperiodoevaluacion,
#                                              diasactivacion=materia.diasactivacion,
#                                              usaperiodocalificaciones=materia.usaperiodocalificaciones,
#                                              diasactivacioncalificaciones=materia.diasactivacioncalificaciones,
#                                              validacreditos=materia.validacreditos,
#                                              validapromedio=materia.validapromedio,
#                                              laboratorio=materia.laboratorio, parcial=materia.parcial,
#                                              tipomateria=materia.tipomateria, paralelomateria=materia.paralelomateria,
#                                              seevalua=materia.seevalua, inicioeval=inicio, fineval=fin,
#                                              cupoadicional=materia.cupoadicional,
#                                              totalmatriculadocupoadicional=materia.totalmatriculadocupoadicional,
#                                              codigosakai=materia.codigosakai, esintroductoria=materia.esintroductoria,
#                                              inicioevalauto=inicio, finevalauto=fin,
#                                              modelotarjeta=materia.modelotarjeta,
#                                              namehtml=materia.namehtml, urlhtml=materia.urlhtml,
#                                              inglesepunemi=materia.inglesepunemi,
#                                              visiblehorario=materia.visiblehorario)
#                         materianew.save()
#                     else:
#                         materianew = Materia.objects.get(status=True, nivel=nivelnew, asignatura=materia.asignatura,
#                                                          paralelo=materia.paralelo)
#
#                         # se agrega el campo manytomany de carreras comunes en materia creadas
#                     print('MATERIA:   ' + str(materianew))
#                     print('')
#                     print('')
#                     print('')
#                     print('')
#                     print('')
#                     print('')
#                     for comunes in materia.carrerascomunes.all():
#                         materianew.carrerascomunes.add(comunes)
#
#                     # se agrega las materias a los docentes al periodo destino
#                     for profesor in materia.profesormateria_set.filter(status=True, activo=True):
#                         if not ProfesorMateria.objects.filter(status=True, materia=materianew,
#                                                               profesor=profesor.profesor,
#                                                               tipoprofesor=profesor.tipoprofesor,
#                                                               segmento=profesor.segmento).exists():
#                             profmat = ProfesorMateria(materia=materianew, profesor=profesor.profesor,
#                                                       tipoprofesor=profesor.tipoprofesor, segmento=profesor.segmento,
#                                                       desde=inicio, hasta=fin, principal=profesor.principal,
#                                                       hora=profesor.hora,
#                                                       activo=profesor.activo, afinidad=profesor.afinidad,
#                                                       afinidadcampoamplio=profesor.afinidadcampoamplio,
#                                                       afinidadcampoespecifico=profesor.afinidadcampoespecifico,
#                                                       afinidadcampodetallado=profesor.afinidadcampodetallado,
#                                                       novalidahorario=profesor.novalidahorario,
#                                                       aceptarmateria=profesor.aceptarmateria,
#                                                       aceptarmateriaobs=profesor.aceptarmateriaobs,
#                                                       aceptarhorario=profesor.aceptarhorario,
#                                                       aceptarhorarioobs=profesor.aceptarhorarioobs,
#                                                       tituloafin=profesor.tituloafin,
#                                                       evalua=profesor.evalua, utilizawebex=profesor.utilizawebex,
#                                                       subactividadtutorvirtual=profesor.subactividadtutorvirtual,
#                                                       puedemodificarasistencia=profesor.puedemodificarasistencia,
#                                                       modificarasistenciafin=profesor.modificarasistenciafin)
#                             profmat.save()
#                         else:
#                             profmat = ProfesorMateria.objects.get(status=True, materia=materianew,
#                                                                   profesor=profesor.profesor,
#                                                                   tipoprofesor=profesor.tipoprofesor,
#                                                                   segmento=profesor.segmento)
#                         print('PROFESOR MATERIA:     ' + str(profmat))
#                         print('')
#                         print('')
#                         print('')
#                         print('')
#                         print('')
#                         print('')
#                         # se crea la tabla intermedia de grupo profesor
#                         gruposet = profesor.gruposprofesormateria_set.first() if profesor.gruposprofesormateria_set.exists() else None
#                         if gruposet:
#                             if not GruposProfesorMateria.objects.filter(profesormateria=profmat,
#                                                                         paralelopractica=gruposet.paralelopractica,
#                                                                         cupo=gruposet.cupo).exists():
#                                 grupoprof = GruposProfesorMateria(profesormateria=profmat,
#                                                                   paralelopractica=gruposet.paralelopractica,
#                                                                   cupo=gruposet.cupo)
#                                 grupoprof.save()
#
#                     # se crea las clases en base a las materias que se van creado en periodo destino
#                     for clase in materia.clase_set.filter(status=True, activo=True):
#                         grupo = GruposProfesorMateria.objects.filter(status=True,
#                                                                      profesormateria__materia=materianew,
#                                                                      profesormateria__profesor=clase.profesor).first() if GruposProfesorMateria.objects.filter(
#                             status=True, profesormateria__materia=materianew,
#                             profesormateria__profesor=clase.profesor).exists() else None
#                         if not Clase.objects.filter(status=True, materia=materianew, turno=clase.turno, dia=clase.dia,
#                                              inicio=periodo.inicio,
#                                              fin=periodo.fin,
#                                              aula=clase.aula, activo=clase.activo, tipoprofesor=clase.tipoprofesor,
#                                              profesor=clase.profesor,
#                                              grupoprofesor=grupo, tipohorario=clase.tipohorario,
#                                              profesorayudante=clase.profesorayudante,
#                                              subirenlace=clase.subirenlace).exists():
#
#                             clasenew = Clase(materia=materianew, turno=clase.turno, dia=clase.dia,
#                                              inicio=periodo.inicio,
#                                              fin=periodo.fin,
#                                              aula=clase.aula, activo=clase.activo, tipoprofesor=clase.tipoprofesor,
#                                              profesor=clase.profesor,
#                                              grupoprofesor=grupo, tipohorario=clase.tipohorario,
#                                              profesorayudante=clase.profesorayudante,
#                                              subirenlace=clase.subirenlace)
#                             clasenew.save()
#                             print('CLASE:       ' + str(clasenew))
#                             print('')
#                             print('')
#                             print('')
#                             print('')
#                             print('')
#                             print('')
#
#     except Exception as e:
#         print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
#         print(e)
#         transaction.set_rollback(True)
#
#
# copiarniveles(periodo, periodocopiar)


@transaction.atomic()
def borrar_niveles(periodo):
    try:
        for coordinacion in Coordinacion.objects.filter(id__in=[2, 3, 5]):
            print('COORDINACION.....' + str(coordinacion))
            for nivel in Nivel.objects.filter(status=True, periodo=periodo,
                                              nivellibrecoordinacion__coordinacion=coordinacion):
                print('Nivel.....' + str(nivel))
                if nivel.materia_set.filter(status=True).exists():
                    for materia in nivel.materia_set.filter(status=True):
                        print('Materia.....' + str(materia))
                        if ProfesorMateria.objects.filter(status=True, materia=materia).exists():
                            for prof in ProfesorMateria.objects.filter(status=True, materia=materia):
                                print('Profesor materia.....' + str(materia))
                                prof.delete()
                                if Clase.objects.filter(status=True, materia=materia).exists():
                                    for clase in Clase.objects.filter(status=True, materia=materia):
                                        print('Clase...' + str(clase))
                                        clase.delete()
        print('FIN ')
    except Exception as ex:
        transaction.set_rollback(True)

borrar_niveles(periodo)
