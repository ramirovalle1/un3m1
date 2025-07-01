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

try:
    periodo=Periodo.objects.get(id=90)
    # for materia in Materia.objects.filter(status=True, nivel__periodo=periodo, esintroductoria=False, asignaturamalla__malla__carrera__in=[97,98,99,100,101,104,105], asignaturamalla__malla_id__in=[289,287,288,281,279, 284, 282], asignaturamalla__malla__inicio__year=2019):
    for alumno in MateriaAsignada.objects.filter(id__in=[798648,798647,798933,798934,800299,800300, 799012, 799011,802041,802041,802962,802961,802620,802619,
                                                             803751,803752,802618,802617,803259,803260,802760,802759,803647,803648,804896,804895,804898, 804897,
                                                             804376,804375,807384,807383, 807201, 807202,807363,807364,807350,807349,806931,806932,799831,799832,801525,801526,
                                                             801282,801281, 801964, 801963,803185, 803186, 802778,802777,804961,804962, 807167,807168, 807275,807276,798966,
                                                             798965, 806375,806376,807178,807177, 795083,795084,805637,805638,805795,805796,799111,799112,804425,804426,806339,
                                                         806340,805629,805630,798691,798692,807291,807292,799709,799710,806879,806880,800819,800820,807199,
                                                         807200,805817,805818,807014,807013,800220,800219,803733,803734,802269,802270,803059,
                                                         803060,803381,803382,803923,803924,802263,802264,803025,803026,802837,802838,803686,
                                                         803685,803681,803682,803480,803479,805867,805868,806339,806340,799471,799472,803025,
                                                         803026,803753,803754,805145,805146 ] ,matricula__estado_matricula__in=[2,3],  retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__nombres'):
        if alumno.materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
            for notasmooc in alumno.materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
                if type(notasmooc[0]) is Decimal:
                    campo = alumno.campo(notasmooc[1].upper())
                    # if type(notasmooc[0]) is Decimal:
                    if campo:
                        if null_to_decimal(campo.valor) != float(notasmooc[0]):
                            actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                            calificacion=notasmooc[0])
                            auditorianotas.save()
                    # else:
                    #     if campo:
                    #         if null_to_decimal(campo.valor) != float(0):
                    #             actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
                    #             auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
                    #             auditorianotas.save()
            # alumno.cierre_materia_asignada()
            print("Migrada: %s" % alumno)
            # alumno.actualiza_notafinal()
        # cerrar materias
        # materia.cerrado = True
        # materia.fechacierre = datetime.now().date()
        # materia.save()
        # for asig in materia.asignados_a_esta_materia():
        #     asig.cerrado = True
        #     asig.save()
        #     asig.actualiza_estado()
        # for asig in materia.asignados_a_esta_materia():
        #     asig.cierre_materia_asignada()
        # materia.materiaasignada_set.all()[0].cierre_materia_asignada_pre()
        # print("Cerrada: %s" % materia)
except Exception as ex:
    print('error: %s' % ex)
