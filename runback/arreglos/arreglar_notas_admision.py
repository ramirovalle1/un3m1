#!/usr/bin/env python

import os
import sys
import time


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

from sga.models import *

# try:
#     periodo = Periodo.objects.get(id=95)
#     coordinacion = Coordinacion.objects.filter(status=True, id=9)
#     matriculas = Matricula.objects.filter(pasoayuda=True, status=True, nivel__periodo=periodo, inscripcion__carrera__coordinacion=coordinacion, estado_matricula__in=[2, 3]).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
#     for matricula in matriculas:
#         for materiaasignada in matricula.materiaasignada_set.filter(estado_id__in=[2, 3], retiramateria=False, notafinal__lt=70):
#             campos = materiaasignada.evaluaciongenerica_set.filter(status=True).order_by('id')
#             puntosfalta = 70 - float(materiaasignada.notafinal)
#             for campo in campos:
#                 notacampo = 0
#                 difecampo = 0
#                 # puntosfalta = 70 - float(materiaasignada.notafinal)
#                 if campo.valor<campo.detallemodeloevaluativo.notamaxima and puntosfalta > 0:
#                     difecampo = campo.detallemodeloevaluativo.notamaxima - campo.valor
#                     if difecampo > puntosfalta:
#                         notacampo = puntosfalta + campo.valor
#
#                     else:
#                         notacampo = float(difecampo + campo.valor)
#                     puntosfalta = float(puntosfalta - difecampo)
#
#                     actualizar_nota_planificacion(materiaasignada.id, campo.detallemodeloevaluativo.nombre, notacampo)
#                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
#                                                     calificacion=notacampo,
#                                                     observacion=u"SE PROCEDE A COMPLETAR NOTA AUTOMÁTICAMENTE POR DISPOSICIÓN DE LA AUTORIDAD %s"%datetime.now())
#                     auditorianotas.save()
#             print("Nota actualizada: %s" % materiaasignada)
#             # alumno.cierre_materia_asignada()
#
#             # alumno.actualiza_notafinal()
#         # cerrar materias
#         # materia.cerrado = True
#         # materia.fechacierre = datetime.now().date()
#         # materia.save()
#         # for asig in materia.asignados_a_esta_materia():
#         #     asig.cerrado = True
#         #     asig.save()
#         #     asig.actualiza_estado()
#         # for asig in materia.asignados_a_esta_materia():
#         #     asig.cierre_materia_asignada()
#         # materia.materiaasignada_set.all()[0].cierre_materia_asignada_pre()
#         # print("Cerrada: %s" % materia)
# except Exception as ex:
#     print('error: %s' % ex)


Matricula.objects.filter(nivel__periodo_id=202).update(aprobado=False)
matriculas = Matricula.objects.filter(status=True, nivel__periodo_id=202, aprobado=False).distinct().order_by("inscripcion__carrera")
conta=0
totalaprobados = 0
for matricula in matriculas:
    cantidadmaterias = matricula.materiaasignada_set.filter(status=True, retiramateria=False).count()
    cantidadaprobadas = matricula.materiaasignada_set.filter(notafinal__gte=70, status=True, retiramateria=False).count()
    # print("%s %s"% (cantidadaprobadas, cantidadmaterias))
    if cantidadmaterias == cantidadaprobadas and cantidadmaterias > 0 and cantidadaprobadas > 0:
        conta += 1
        totalaprobados += 1
        print("************************************************************# %s: Aprobadas=%s Total=%s"% (conta,cantidadaprobadas, cantidadmaterias))
        matricula.aprobado = True
        matricula.save()
        print(matricula)
print("Total de aprobados %s" % totalaprobados)
