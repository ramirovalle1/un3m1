#!/usr/bin/env python

import sys
import os

from sga.tasks import send_html_mail

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from datetime import datetime
from sga.models import Profesor, miinstitucion, Materia
from django.contrib.admin.models import LogEntry


# ENVIO DE NOTIFICACIONES DE MODIFICACION DE NOTAS POR CADA DOCENTE
hoy = datetime.now().date()
fechainicio = datetime(hoy.year, hoy.month, hoy.day, 0, 0, 0)
fechafin = datetime(hoy.year, hoy.month, hoy.day, 23, 59, 0)
for profesor in Profesor.objects.filter(persona__usuario__is_active=True):
    logs = LogEntry.objects.filter(user_id=profesor.persona.usuario.id, action_time__gte=fechainicio, action_time__lte=fechafin).exclude(change_message='')
    if logs:
        send_html_mail("Resumen de acciones realizadas en el SGA.", "emails/resumenacciones.html", {'d': {'sistema': 'Sistema de Gestion Academica', 'fecha': hoy, 'logs': logs}, 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [])

# # cerrar materias
# for materia in Materia.objects.filter(nivel__periodo__id=9, cerrado=False).order_by('-id'):
#     materia.cerrado = True
#     materia.fechacierre = datetime.now().date()
#     materia.save()
#     for asig in materia.asignados_a_esta_materia():
#         asig.cerrado = True
#         asig.save()
#         asig.actualiza_estado()
#     for asig in materia.asignados_a_esta_materia():
#         asig.cierre_materia_asignada()
#     print(materia.id)
