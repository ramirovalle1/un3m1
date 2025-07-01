#!/usr/bin/env python
# -*- coding: utf-8 -*-
# import os
# import sys
#
# from django.db import transaction
#
# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
# your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# sys.path.append(your_djangoproject_home)
#
# from django.core.wsgi import get_wsgi_application
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# application = get_wsgi_application()
# from sga.models import *
# cont = 0
# #se cambió para migrar solo salud
# # coordinaciones = Coordinacion.objects.filter(pk__in=[1])
# coordinaciones = Coordinacion.objects.filter(pk__in=[2,3,4,5])
# #coordinaciones = Coordinacion.objects.filter(pk__in=[1,2,3,4,5])
# total=0
# conta=0
# for coordinacion in coordinaciones:
#     for car in coordinacion.carreras():
#         cont=0
#         # materia = Materia.objects.filter(nivel__periodo_id=113,asignaturamalla__malla__carrera=car, cerrado=False).exclude(
#         #     nivel__modalidad_id=3)
#         #
#         # Excluye los niveles 7-8
#         materia = Materia.objects.filter(nivel__periodo_id=113, asignaturamalla__malla__carrera=car).exclude(nivel__modalidad_id=3)
#
#         #materia = Materia.objects.filter(pk__in=[43817,41994])
#         # print("INICIA" + car.nombre)
#         for mat in materia:
#             for asignadomateria in mat.asignados_a_esta_materia():
#                 asis = []
#                 nuevo = 0
#                 actual = 0
#                 if asignadomateria.asistencias_zoom_valida() > 0:
#                     asistvalida = asignadomateria.asistencias_zoom_valida()
#                     asistotal = asignadomateria.cantidad_asistencias_zoom()
#                     asisfaltantes = asistotal-asistvalida
#                     por = round(((asistvalida * 100) / asistotal),0)
#                     if por >= 69.5 and por <70:
#                         por=70
#                         print(asignadomateria,por)
#                     if por < 70 and (asignadomateria.asistenciafinal >=70 and asignadomateria.asistenciafinal <100):
#                         conta += 1
#                         # if asignadomateria.estado_id == 1:
#                         deberia = (asignadomateria.asistenciafinal * asistotal)/100
#                         deberia = round((deberia)-asistvalida,0)
#                         asistencias = SesionZoom.objects.filter(materiaasignada=asignadomateria,status=True,activo=False)[:deberia-1]
#                         for asistencia in asistencias:
#                             asistencia.activo=True
#                             asistencia.save()
#                         por = round(((deberia+asistvalida)*100/asistotal),0)
#                         print("IGUALA ASISTENCIA ",asignadomateria ,por, " - ", conta)
#
#                     # asignadomateria.asistenciafinal = por
#                     # asignadomateria.save()
#                     # asignadomateria.actualiza_estado()
#                     #aumenta para eliminar calificación de examen migrada
#                     # asignadomateria.actualiza_notafinal()
#                     # if por < 70:
#                     # if EvaluacionGenerica.objects.filter(status=True, detallemodeloevaluativo_id=37,
#                     #                                      materiaasignada=asignadomateria).exists():
#                     #     exam = EvaluacionGenerica.objects.get(status=True, detallemodeloevaluativo_id=37,
#                     #                                           materiaasignada=asignadomateria)
#                     #     exam.valor = 0
#                     #     exam.save()
#                     #     if AuditoriaNotas.objects.filter(status=True, evaluaciongenerica=exam).exists():
#                     #         auditoria = AuditoriaNotas.objects.filter(status=True, evaluaciongenerica=exam)
#                     #         for aud in auditoria:
#                     #             aud.status = False
#                     #             aud.save()
#
#                     cont+=1
#             # mat.recalcularmateria()
#
#         # print("FIN " + car.nombre)
#         print("FIN,TOTAL MIGRADO CARRERA " + car.nombre , cont)
#         total=total+cont
# print("FIN, TOTAL MIGRADO: " , total)
#
#
#
#
#
#
