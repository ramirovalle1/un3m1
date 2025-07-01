#!/usr/bin/env python

import sys
import os
import time
from datetime import datetime, timedelta

from django.db import transaction


SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from settings import TIPO_PERIODO_REGULAR
from sga.models import Periodo, ActividadDetalleDistributivoCarrera, HorarioTutoriaPacticasPP, AgendaPracticasTutoria, Persona, Notificacion, DIAS_CHOICES
from django.contrib.auth.models import User
from webpush import send_user_notification
from sga.commonviews import traerNotificaciones



def periodoactual():
    if Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, inicio__lte=datetime.now().date(), activo=True, fin__gte=datetime.now().date()).exists():
        if Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).order_by('id').count() > 1:
            periodo = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, marcardefecto=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).order_by('id')[0] if Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, marcardefecto=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).exists() else None
        else:
            periodo = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).order_by('id')[0] if Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).exists() else None
        return periodo


@transaction.atomic()
def notificarhorario():
    try:
        # AgendaPracticasTutoria
        periodo = periodoactual()
        ahora = datetime.now()
        print(periodo)
        docentes = ActividadDetalleDistributivoCarrera.objects.filter(
            actividaddetalle__criterio__criteriodocenciaperiodo__criterio__id=6,
            actividaddetalle__criterio__distributivo__periodo=periodo,
            actividaddetalle__criterio__distributivo__status=True, status=True)
        for act in docentes:
            if act.actividaddetalle.criterio.distributivo.profesor.id == 1304:
                print('alto')
            if HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=act.actividaddetalle.criterio.distributivo.profesor, periodo=periodo, turno__comienza__lte=ahora.time(), turno__termina__gte=ahora.time(), dia=ahora.weekday()+1).exists():
                if not AgendaPracticasTutoria.objects.filter(status=True, docente=act.actividaddetalle.criterio.distributivo.profesor, fecha=ahora.date(), hora_inicio__gte=ahora.time(), hora_fin__lte=ahora.time()).exists():
                    horario = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=act.actividaddetalle.criterio.distributivo.profesor, periodo=periodo, turno__comienza__lte=ahora.time(), turno__termina__gte=ahora.time(), dia=ahora.weekday()+1).first()
                    print('Estimado Docente '+str(act.actividaddetalle.criterio.distributivo.profesor)+' no tiene agendado la practica pre profesional el dia de hoy ')
                    usernotify = User.objects.get(pk=act.actividaddetalle.criterio.distributivo.profesor.persona.usuario.pk)
                    # usernotify = User.objects.get(pk=43766)
                    pers = act.actividaddetalle.criterio.distributivo.profesor.persona
                    # pers = Persona.objects.get(usuario=usernotify)
                    noti = Notificacion(cuerpo='Estimado docente no ha agendado la tutoria de practicas preprofesionales plaficada para los dias: '+str(DIAS_CHOICES[horario.dia])+'a las: '+ str(horario.turno.nombre_horario()),
                                        titulo='Agenda de Practicas PreProfesionales',
                                        destinatario=pers, url="http://127.0.0.1:8000/pro_cronograma?action=tutoriapractica", prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1),
                                        tipo=2, en_proceso=False)
                    noti.save()
                    #
                    send_user_notification(user=usernotify, payload={
                        "head": "Agenda de Practicas PreProfesionales",
                        "body": 'Estimado docente no ha agendado la tutoria de practicas preprofesionales plaficada para los dias: '+str(DIAS_CHOICES[horario.dia])+'a las: '+ str(horario.turno.nombre_horario())+'',
                        "action": "notificacion",
                        "timestamp": time.mktime(datetime.now().timetuple()),
                        "url": 'http://127.0.0.1:8000/pro_cronograma?action=tutoriapractica',
                        "btn_notificaciones": traerNotificaciones(request=None, data=None, persona=pers),
                        "sinmensaje": True
                    }, ttl=500)
    except Exception as e:
        print(e)




notificarhorario()