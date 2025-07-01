
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
#
# #**********************************EDUCACION***************************
#
# try:
#     coordinacion = Coordinacion.objects.get(pk=5)
#     for car in coordinacion.carreras():
#         print("INICIA" + car.nombre)
#         materia = Materia.objects.filter(nivel__periodo_id=113,asignaturamalla__malla__carrera=car).exclude(nivel__modalidad_id=3)
#         for mat in materia:
#             for asignadomateria in mat.asignados_a_esta_materia():
#                 asis = []
#                 nuevo = 0
#                 actual = 0
#                 for fechas in mat.lecciones_zoom():
#                     clases = Clase.objects.filter(materia=mat)
#                     for cl in clases:
#                         if SesionZoom.objects.filter(materiaasignada=asignadomateria,
#                                                      fecha=fechas.fecha, clase=cl).exists():
#
#                             if SesionZoom.objects.filter(materiaasignada=asignadomateria,
#                                                          fecha=fechas.fecha, clase=cl, activo=True).exists():
#
#                                 excluir = SesionZoom.objects.filter(materiaasignada=asignadomateria,
#                                                                     fecha=fechas.fecha, clase=cl, activo=True).first()
#                             else:
#                                 excluir = SesionZoom.objects.filter(materiaasignada=asignadomateria,
#                                                                     fecha=fechas.fecha, clase=cl).first()
#
#                             asistencia = SesionZoom.objects.filter(materiaasignada=asignadomateria,
#                                                                    fecha=fechas.fecha, clase=cl).exclude(pk=excluir.pk)
#
#                 # print(actual,nuevo)
#         print("FIN " + car.nombre)
# except Exception as ex:
#     print(ex)
