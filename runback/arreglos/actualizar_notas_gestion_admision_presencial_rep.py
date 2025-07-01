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
    for materia in Materia.objects.filter(status=True, nivel__periodo=periodo, esintroductoria=False, asignaturamalla__malla_id__in=[151,
163,
155,
166,
169,
167,
168,
165,
156,
162,
152,
159,
153,
160,
157,
158,
164,
154,
184,
161] ):
    # for materia in Materia.objects.filter(id=24079  ,status=True, nivel__periodo=periodo, esintroductoria=False):
        for alumno in materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3], retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__nombres'):
            if materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
                for notasmooc in materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
                    if type(notasmooc[0]) is Decimal:
                        campo = alumno.campo(notasmooc[1].upper())
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
                print("Migrada: %s" % alumno)
            else:
                print("Problemas al importar: %s" % alumno)
            # alumno.cierre_materia_asignada()

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
