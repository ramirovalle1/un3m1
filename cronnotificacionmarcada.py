#!/usr/bin/env python
import csv
import os
import sys

import xlrd
from docx import Document
from settings import USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA

# import urllib2
# Full path and name to your csv file
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *
from sagest.models import *


from datetime import datetime, timedelta
from django.db import transaction



# cron de notificación para director
@transaction.atomic()
def notificacionfaltasmarcadas():
    fechahoy = datetime.now().date()
    personasdistributivos = DistributivoPersona.objects.filter(status=True).order_by('persona')
    cantidad = len(personasdistributivos)


    for perso in personasdistributivos:
        if TrabajadorDiaJornada.objects.filter(persona=perso.persona, status=True).exists():

            # Contador que me permite que la primera hora de marcada, no tengo una validación entre de mi hora de inicio
            contadorhorainicio = 1
            # Contador que me permite que la ultima hora de marcada, no tengo una validación entre de mi hora de final jornada
            contadorhorafinal = 2

            trabajadorpersona = TrabajadorDiaJornada.objects.filter(persona= perso.persona, status = True).order_by('id').last()
            trabajador = perso.persona
            jornada = trabajadorpersona.jornada

            # Trabajador y jornada de prueba
            trabajador = Persona.objects.get(pk=22213)
            jornada = Jornada.objects.get(pk=85)

            # Obtengo mi detalle de jornada
            numero_dia = fechahoy.weekday() + 1
            detalle_jornada = DetalleJornada.objects.filter(jornada=jornada, dia=numero_dia, status=True)
            num = detalle_jornada.count()

            for det in detalle_jornada:

                # Asignación de hora inicio
                time1 = det.horainicio
                # Asignación de hora final
                time2 = det.horafin
                # horarealiza = datetime.now().time()
                horarealiza =  datetime(2022, 1, 1, 15, 59, 59)
                horarealiza = horarealiza.time()

                # El primer if solo identifica mis horas de inicio
                if time1 < horarealiza:
                    time = datetime(fechahoy.year, fechahoy.month, fechahoy.day, time1.hour, time1.minute, time1.second)
                    hora_adicionar = timedelta(minutes=59)
                    sumahora = time + hora_adicionar
                    restahora = time - hora_adicionar

                    if trabajador.logdia_set.filter(fecha=fechahoy).exists():
                        print('Si ha marcado')
                        logdia = trabajador.logdia_set.filter(fecha=fechahoy).first()
                        if contadorhorainicio == 1:
                            if not logdia.logmarcada_set.filter(time__gte=sumahora, status = True).exists():
                                print("Notificación enviada")
                            else:
                                print("Tiene marcada")
                        else:
                            if not logdia.logmarcada_set.filter(Q(time__lte=restahora) & Q(time__gte=sumahora) & Q(status = True)).exists():
                                print("Notificación enviada")
                            else:
                                print("Tiene marcada")

                    else:
                        print('No ha marcado aún')
                contadorhorainicio +=1

                # El segundo if solo identifica mis horas de finales
                if time2 < horarealiza:
                    time = datetime(fechahoy.year, fechahoy.month, fechahoy.day, time2.hour, time2.minute, time2.second)
                    hora_adicionar = timedelta(hours=1)
                    sumahora = time + hora_adicionar
                    restahora = time - hora_adicionar

                    if trabajador.logdia_set.filter(fecha=fechahoy).exists():
                        print('Si ha marcado')
                        logdia = trabajador.logdia_set.filter(fecha=fechahoy).first()
                        if contadorhorafinal == 4:
                            if not logdia.logmarcada_set.filter(time__lte=sumahora, status = True).exists():
                                print("No tiene marcada")
                            else:
                                print("Tiene marcada")
                        else:
                            if not logdia.logmarcada_set.filter(Q(time__lte=restahora) & Q(time__gte=sumahora) & Q(status=True)).exists():
                                print("No tiene marcada")
                            else:
                                print("Tiene marcada")
                    else:
                        print('No ha marcado aún')
                contadorhorafinal +=2

            print('listo')
        else:
            print('No tiene jornada laboral')

    print('listo')

notificacionfaltasmarcadas()