#!/usr/bin/env python

import os
import sys
import time



SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from sga.commonviews import *

try:
    periodo=Periodo.objects.get(id=90)
    for materia in Materia.objects.filter(status=True, nivel__periodo=periodo, esintroductoria=False, asignaturamalla__malla__carrera__in=[126,127,128,129,130,131,132,133,134,135]):
        for alumno in materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3], retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__nombres'):
            aux=0
            for notasmooc in materia.notas_de_examen_pregradovirtual_porcategoria_moodle(alumno.matricula.inscripcion.persona):
                if type(notasmooc[0]) is Decimal:
                    campo = alumno.campo(notasmooc[1].upper())
                    if campo:
                        if null_to_decimal(campo.valor) != float(notasmooc[0]):
                            aux = 1
                            actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                            calificacion=notasmooc[0])
                            auditorianotas.save()

            if aux==1:
                print("Migrada: %s" % alumno)
except Exception as ex:
    print('error: %s' % ex)
