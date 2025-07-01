import base64
import os
import sys


from datetime import datetime, timedelta

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import Notificacion, Persona
from postulaciondip.models import InscripcionInvitacion, PersonalApoyoMaestria
from django.contrib.auth.models import Group


def notificar_analistas_posgrado(eUsers, eInscripcionInvitacion):
    print("start process notification")
    ecarrera = eInscripcionInvitacion.get_personal_a_contratar().actaparalelo.convocatoria.carrera
    eperiodo = eInscripcionInvitacion.get_personal_a_contratar().actaparalelo.convocatoria.periodo
    ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=ecarrera, periodo=eperiodo)
    titulonotificacion = f"Plazo para subir requisitos por vencer: {eInscripcionInvitacion.get_personal_a_contratar()} - {eInscripcionInvitacion.fecharevisionrequisitos}"
    cuerponotificacion = f"La fecha limité para subir los requisitos esta por terminar, le quedan 2 días para subir todos los documentos."

    if ePersonalApoyoMaestrias:
        for ePersona in ePersonalApoyoMaestrias:
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=ePersona.personalapoyo.persona,
                url=f"https://sga.unemi.edu.ec/adm_postulacion?action=revision_requisitos_personal_a_contratar&id={eInscripcionInvitacion.get_personal_a_contratar().pk}",
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save()

    else:
        for user in eUsers:
            ePersona = Persona.objects.filter(status=True, usuario=user).first()
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=ePersona,
                url=f"https://sga.unemi.edu.ec/adm_postulacion?action=revision_requisitos_personal_a_contratar&id={eInscripcionInvitacion.get_personal_a_contratar().pk}",
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save()
    print("End proccess notification")


def notificar_persona_a_contratar(eInscripcionInvitacion):
    print("start process notification")
    titulonotificacion = f"Plazo para subir requisitos por vencer {eInscripcionInvitacion.fecharevisionrequisitos}"
    cuerponotificacion = f"La fecha limité para subir los requisitos esta por terminar, le quedan 2 días para subir todos los documentos."
    ePersona = eInscripcionInvitacion.inscripcion.postulante.persona
    if ePersona:
        notificacion = Notificacion(
            titulo=titulonotificacion,
            cuerpo=cuerponotificacion,
            destinatario=ePersona,
            url=f"https://seleccionposgrado.unemi.edu.ec/loginpostulacion",
            content_type=None,
            object_id=None,
            prioridad=1,
            app_label='SGA',
            fecha_hora_visible=datetime.now() + timedelta(days=3))
        notificacion.save()
    print("End proccess notification")


def notificar_plazo_a_vencer_requisitos():
    # Obtener la fecha actual
    fecha_actual = datetime.now().date()

    # Obtener la fecha actual + 2 días
    fecha_limite = fecha_actual + timedelta(days=2)
    eInscripcionInvitacion = InscripcionInvitacion.objects.filter(status=True, fecharevisionrequisitos=fecha_limite)
    eGrupo = Group.objects.get(pk=422)
    eUsers = eGrupo.user_set.all()

    # Realizar acciones con las inscripciones caducas si es necesario
    for inscripcion in eInscripcionInvitacion:
        notificar_analistas_posgrado(eUsers, inscripcion)
        notificar_persona_a_contratar(inscripcion)


notificar_plazo_a_vencer_requisitos()