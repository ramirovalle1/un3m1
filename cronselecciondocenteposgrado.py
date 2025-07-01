# coding=utf-8
# !/usr/bin/env python

import os
import sys

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from datetime import datetime, timedelta
from django.db import transaction
from sga.funciones import variable_valor
from sga.models import *
from sagest.models import *
import xlrd
from empleo.models import PersonaAplicaOferta, OfertaLaboralEmpresa
from sga.models import *
from sga.funciones import variable_valor, notificacion2
from postulaciondip.models import *


def notifica_vencimiento_plazo_documentos():
    try:
        email_prueba = [u"%s@unemi.edu.ec" % persona.usuario for persona in Persona.objects.filter(pk=37121)]
        now = datetime.now().date()
        lista_receptores = Persona.objects.filter(id__in=variable_valor('RECEPTORES_VENCIMIENTO_PLAZO_SUBIR_DOCUMENTOS'))

        inscritos_sin_requisitos = InscripcionInvitacion.objects.filter(fecharevisionrequisitos__lt=now, estadorequisitos=1, status=True).exclude(estado=7)
        for inscrito in inscritos_sin_requisitos:
            inscrito.estado = 7
            inscrito.estadorequisitos = 7
            inscrito.observacionrequisitos = u"EXCEDIÓ EL PLAZO MÁXIMO PARA LA CARGA DE REQUISITOS DE CONTRATACIÓN"
            inscrito.save()
            HistorialInvitacion.objects.create(invitacion=inscrito, estado=7, estadoinvitacion=5)

            #------------------- Sección de notificaciones
            title = '🔴 [Atención] Cumplimiento del plazo para entrega de requisitos'
            cuerpo_inscrito = f"""
                <p style="text-align: justify">Estimado profesional, agradecemos su voluntad de haber postulado en el proceso de selección docente para el módulo {inscrito.inscripcion.convocatoria.asignaturamalla.asignatura} del programa {inscrito.inscripcion.convocatoria.carrera}, cohorte {inscrito.inscripcion.convocatoria.periodo.cohorte}; y, en virtud al no cargar en el tiempo establecido la documentación requerida, se informa que su proceso de contratación no ha sido procesado.<br><br>
                Esperamos contar con su alto nivel de experiencia profesional en una próxima postulación.</p>
            """

            cuerpo_administ = f"""
                Estimad%s, la contratación {'de la' if inscrito.get_genero() else 'del'} profesional {inscrito.inscripcion} del módulo <b>{inscrito.inscripcion.convocatoria.asignaturamalla.asignatura}</b> del programa {inscrito.inscripcion.convocatoria.carrera},
                cohorte {inscrito.inscripcion.convocatoria.periodo.cohorte}, paralelo {inscrito.inscripcion.personalacontratar_set.first().actaparalelo.paralelo if inscrito.inscripcion.personalacontratar_set.first() else '--'}, no ha cargado los documentos requeridos para iniciar el proceso de contratación.
            """

            # Notificar postulante
            email_inscrito = [u"%s@unemi.edu.ec" % inscrito.inscripcion.postulante.persona.usuario]
            send_html_mail(title, "emails/vencimiento_plazo_requisitos_contratacion.html", {'inscrito': inscrito, 'cuerpo': cuerpo_inscrito}, email_inscrito, [], [], cuenta=CUENTAS_CORREOS[0][1])
            notificacion2(title, cuerpo_inscrito, inscrito.inscripcion.postulante.persona, None, '', inscrito.id, 1, 'sga', InscripcionInvitacion)

            # Notificar administrativos
            for persona in lista_receptores:
                _cuerpo = cuerpo_administ % 'a' if persona.es_mujer() else cuerpo_administ % 'o'
                notificacion2(title, _cuerpo, persona, None, '', inscrito.id, 1, 'sga', InscripcionInvitacion)
                send_html_mail(title, "emails/vencimiento_plazo_requisitos_contratacion.html", {'inscrito': inscrito, 'cuerpo': _cuerpo}, [u"%s@unemi.edu.ec" % persona.usuario], [], [], cuenta=CUENTAS_CORREOS[0][1])

    except Exception as ex:
        transaction.rollback()
        print(ex.__str__())

notifica_vencimiento_plazo_documentos()


def notificacion_web_push():
    import json
    from helpdesk.models import HdIncidente
    from webpush.utils import _send_notification
    from wpush.models import SubscriptionInfomation

    persona = Persona.objects.get(cedula='0954778106')
    incidente = HdIncidente.objects.last()
