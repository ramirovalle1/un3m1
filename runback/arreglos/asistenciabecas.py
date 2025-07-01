#!/usr/bin/env python
#
# import os
# import sys
#
#
#
# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
# your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# sys.path.append(your_djangoproject_home)
#
# from django.core.wsgi import get_wsgi_application
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
# application = get_wsgi_application()
#
# from datetime import datetime
# from django.db import transaction
# from sga.models import BecaAsignacion, Periodo, BecaAsistencia
# from sga.funciones import null_to_decimal
#
# # @transaction.atomic()
# def procesar_asistencias():
#     try:
#         horainicio = datetime.now()
#         fechaactual = datetime.now().date()
#         periodo = Periodo.objects.get(pk=90)
#
#         print("Inicio: ", horainicio)
#         becados = BecaAsignacion.objects.filter(status=True,
#                                                 solicitud__periodo=periodo
#                                                 ).order_by('solicitud__inscripcion__persona__apellido1',
#                                                            'solicitud__inscripcion__persona__apellido2',
#                                                            'solicitud__inscripcion__persona__nombres')
#         c = 1
#         total = becados.count()
#         for beca in becados:
#             if not BecaAsistencia.objects.filter(asignacion=beca).exists():
#                 print("Procesando ", c, " de ", total)
#                 alumno = beca.solicitud.inscripcion.persona
#                 # Obtengo la matricula
#                 matricula = beca.solicitud.inscripcion.matricula_periodo_actual(periodo)[0]
#                 estado_matricula = "MATRICULADO" if not matricula.retirado() else "RETIRADO"
#
#                 # asistencia mes 1
#                 desde = datetime.strptime('2019-11-01', '%Y-%m-%d').date()
#                 hasta = datetime.strptime('2019-11-30', '%Y-%m-%d').date()
#                 porcmes1 = null_to_decimal(matricula.porcentaje_asistencia_mensual_beca(desde, hasta), 0)
#
#                 print("Noviembre...")
#                 asistencia = BecaAsistencia(asignacion=beca,
#                                             inicio=desde,
#                                             fin=hasta,
#                                             porcentaje=porcmes1
#                                             )
#                 asistencia.save()
#
#                 # asistencia mes 2
#                 desde = datetime.strptime('2019-12-01', '%Y-%m-%d').date()
#                 hasta = datetime.strptime('2019-12-31', '%Y-%m-%d').date()
#                 porcmes2 = null_to_decimal(matricula.porcentaje_asistencia_mensual_beca(desde, hasta), 0)
#                 print("Diciembre...")
#                 asistencia = BecaAsistencia(asignacion=beca,
#                                             inicio=desde,
#                                             fin=hasta,
#                                             porcentaje=porcmes2
#                                             )
#                 asistencia.save()
#                 # asistencia mes 3
#                 desde = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
#                 hasta = datetime.strptime('2020-01-31', '%Y-%m-%d').date()
#                 porcmes3 = null_to_decimal(matricula.porcentaje_asistencia_mensual_beca(desde, hasta), 0)
#                 print("Enero...")
#                 asistencia = BecaAsistencia(asignacion=beca,
#                                             inicio=desde,
#                                             fin=hasta,
#                                             porcentaje=porcmes3
#                                             )
#                 asistencia.save()
#                 # asistencia mes 4
#                 desde = datetime.strptime('2020-02-01', '%Y-%m-%d').date()
#                 hasta = datetime.strptime('2020-02-29', '%Y-%m-%d').date()
#                 porcmes4 = null_to_decimal(matricula.porcentaje_asistencia_mensual_beca(desde, hasta), 0)
#                 print("Febrero...")
#                 asistencia = BecaAsistencia(asignacion=beca,
#                                             inicio=desde,
#                                             fin=hasta,
#                                             porcentaje=porcmes4
#                                             )
#                 asistencia.save()
#
#             else:
#                 print("Ya fue procesado...")
#
#             print("Registro ", c, " procesado")
#             c += 1
#
#
#         print("Fin: ", datetime.now())
#     except Exception as ex:
#         # transaction.set_rollback(True)
#         msg = ex.__str__()
#         print("Error:", msg)
#
# def actualizar_asistencias():
#     try:
#         horainicio = datetime.now()
#         fechaactual = datetime.now().date()
#         periodo = Periodo.objects.get(pk=90)
#
#         print("Inicio: ", horainicio)
#         becados = BecaAsignacion.objects.filter(status=True,
#                                                 solicitud__periodo=periodo
#                                                 ).order_by('solicitud__inscripcion__persona__apellido1',
#                                                            'solicitud__inscripcion__persona__apellido2',
#                                                            'solicitud__inscripcion__persona__nombres')
#         c = 1
#         total = becados.count()
#         for beca in becados:
#             if BecaAsistencia.objects.filter(asignacion=beca).exists():
#                 print("Procesando actualización ", c, " de ", total)
#                 alumno = beca.solicitud.inscripcion.persona
#                 # Obtengo la matricula
#                 matricula = beca.solicitud.inscripcion.matricula_periodo_actual(periodo)[0]
#                 # estado_matricula = "MATRICULADO" if not matricula.retirado() else "RETIRADO"
#
#                 # asistencia mes 1
#                 desde = datetime.strptime('2019-11-01', '%Y-%m-%d').date()
#                 hasta = datetime.strptime('2019-11-30', '%Y-%m-%d').date()
#                 porcmes1 = null_to_decimal(matricula.porcentaje_asistencia_mensual_beca(desde, hasta), 2)
#                 print("Noviembre...")
#                 BecaAsistencia.objects.filter(asignacion=beca, inicio=desde, fin=hasta).update(porcentaje=porcmes1)
#
#                 # asistencia mes 2
#                 desde = datetime.strptime('2019-12-01', '%Y-%m-%d').date()
#                 hasta = datetime.strptime('2019-12-31', '%Y-%m-%d').date()
#                 porcmes2 = null_to_decimal(matricula.porcentaje_asistencia_mensual_beca(desde, hasta), 2)
#                 print("Diciembre...")
#                 BecaAsistencia.objects.filter(asignacion=beca, inicio=desde, fin=hasta).update(porcentaje=porcmes2)
#
#                 # asistencia mes 3
#                 desde = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
#                 hasta = datetime.strptime('2020-01-31', '%Y-%m-%d').date()
#                 porcmes3 = null_to_decimal(matricula.porcentaje_asistencia_mensual_beca(desde, hasta), 2)
#                 print("Enero...")
#                 BecaAsistencia.objects.filter(asignacion=beca, inicio=desde, fin=hasta).update(porcentaje=porcmes3)
#
#                 # asistencia mes 4
#                 desde = datetime.strptime('2020-02-01', '%Y-%m-%d').date()
#                 hasta = datetime.strptime('2020-02-29', '%Y-%m-%d').date()
#                 porcmes4 = null_to_decimal(matricula.porcentaje_asistencia_mensual_beca(desde, hasta), 2)
#                 print("Febrero...")
#                 BecaAsistencia.objects.filter(asignacion=beca, inicio=desde, fin=hasta).update(porcentaje=porcmes4)
#             else:
#                 print("No existe...")
#
#             print("Registro ", c, " procesado")
#             c += 1
#
#
#         print("Fin: ", datetime.now())
#     except Exception as ex:
#         # transaction.set_rollback(True)
#         msg = ex.__str__()
#         print("Error:", msg)
#
# # procesar_asistencias()
# actualizar_asistencias()