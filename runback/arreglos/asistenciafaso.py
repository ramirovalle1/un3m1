
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
# from sagest.models import *
#
# #**********************************SOCIALES***************************
#
# try:
#     coordinacion = Coordinacion.objects.get(pk=2)
#     for car in coordinacion.carreras():
#         print("INICIA" + car.nombre)
#         materia = Materia.objects.filter(nivel__periodo_id=113, asignaturamalla__malla__carrera=car).exclude(
#             nivel__modalidad_id=3)
#         for mat in materia:
#             for fecha in mat.lecciones_zoom():
#                 if not DiasNoLaborable.objects.values('id').filter(fecha=fecha.fecha,
#                                                                    periodo_id=mat.nivel.periodo_id).exists():
#                     clases = Clase.objects.filter(materia=mat)
#                     for cl in clases:
#                         for asignadomateria in mat.asignados_a_esta_materia():
#                             if SesionZoom.objects.filter(fecha=fecha.fecha, clase=cl, clase__materia=mat,
#                                                          modulo=1).exists():
#                                 if not SesionZoom.objects.select_related().filter(materiaasignada=asignadomateria,
#                                                                                   modulo=1,
#                                                                                   clase__materia=mat,
#                                                                                   fecha=fecha.fecha, clase=cl).exists():
#                                     asistencia = SesionZoom(materiaasignada=asignadomateria,
#                                                             modulo=1,
#                                                             fecha=fecha.fecha,
#                                                             hora=cl.turno.comienza,
#                                                             clase_id=cl.id,
#                                                             activo=False
#                                                             )
#                                     asistencia.save()
#                                     obser = DesactivarSesionZoom(sesion=asistencia,
#                                                                  observacion="NO ASISTIÓ")
#                                     obser.save()
#         print("FIN "+car.nombre)
# except Exception as ex:
#     print(ex)
#
#
# #**********************************FASO***************************
#
# try:
#     coordinacion = Coordinacion.objects.get(pk=3)
#     for car in coordinacion.carreras():
#         print("INICIA"+car.nombre)
#         materia = Materia.objects.filter(nivel__periodo_id=113,asignaturamalla__malla__carrera=car).exclude(nivel__modalidad_id=3)
#         for mat in materia:
#             for fecha in mat.lecciones_zoom():
#                 if not DiasNoLaborable.objects.values('id').filter(fecha=fecha.fecha,
#                                                                    periodo_id=mat.nivel.periodo_id).exists():
#                     clases = Clase.objects.filter(materia=mat)
#                     for cl in clases:
#                         for asignadomateria in mat.asignados_a_esta_materia():
#                             if SesionZoom.objects.filter(fecha=fecha.fecha, clase=cl, clase__materia=mat,
#                                                          modulo=1).exists():
#                                 if not SesionZoom.objects.select_related().filter(materiaasignada=asignadomateria,
#                                                                                   modulo=1,
#                                                                                   clase__materia=mat,
#                                                                                   fecha=fecha.fecha, clase=cl).exists():
#                                     asistencia = SesionZoom(materiaasignada=asignadomateria,
#                                                             modulo=1,
#                                                             fecha=fecha.fecha,
#                                                             hora=cl.turno.comienza,
#                                                             clase_id=cl.id,
#                                                             activo=False
#                                                             )
#                                     asistencia.save()
#                                     obser = DesactivarSesionZoom(sesion=asistencia,
#                                                                  observacion="NO ASISTIÓ")
#                                     obser.save()
#
#         print("FIN "+car.nombre)
# except Exception as ex:
#     print(ex)
#
#
