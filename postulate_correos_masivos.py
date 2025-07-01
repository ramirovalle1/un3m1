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
from sga.models import Materia, Clase, Leccion, LeccionGrupo, AsistenciaLeccion, CamposTitulosPostulacion
from sga.funciones import variable_valor
# from sga.models import *
# from sagest.models import *
import xlrd
from postulate.models import Partida, PersonaAplicarPartida, PersonaFormacionAcademicoPartida, PartidaTribunal
from sga.models import *


def email_meritos_etapa():
    partidas = Partida.objects.filter(status=True, vigente=True, convocatoria__apelacion=True)
    for filtro in partidas:
        print('----------------------------------------------------------*--------------------------------------------------')
        print(filtro.__str__())
        envio = 1
        for post_ in filtro.participantes():
            personaemail_ = post_.persona.email if post_.persona.email else None
            if personaemail_:
                print('{}/{} - {}'.format(envio, filtro.participantes().count(), post_.persona.__str__()))
                send_html_mail("Postulate: Terminación de Revisión", "emails/postulate_primeraetapa.html",
                               {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': post_.persona, 'partida': filtro,
                                't': miinstitucion()}, [personaemail_], ['talento_humano@unemi.edu.ec', 'mfloresz@unemi.edu.ec'], cuenta=CUENTAS_CORREOS[30][1])

                envio += 1

            # postulate_cargar_tribunal()


def email_apelacion_etapa():
    partidas = Partida.objects.filter(status=True, convocatoria__apelacion=True)
    for filtro in partidas:
        print('----------------------------------------------------------*--------------------------------------------------')
        print(filtro.__str__())
        envio = 1
        for post_ in filtro.participantes_apelando():
            personaemail_ = post_.persona.email if post_.persona.email else None
            if personaemail_:
                print('{}/{} - {}'.format(envio, filtro.participantes_apelando().count(), post_.persona.__str__()))
                send_html_mail("Postulate: Terminación de Apelación", "emails/postulate_segundoetapa.html",
                               {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': post_.persona, 'partida': filtro,
                                't': miinstitucion()}, [personaemail_], ['rviterib1@unemi.edu.ec'], cuenta=CUENTAS_CORREOS[30][1])

                envio += 1

            # postulate_cargar_tribunal()


def email_tres_mejores_puntuados():
    partidas = Partida.objects.filter(status=True, convocatoria__vigente=True)
    for filtro in partidas:
        print('----------------------------------------------------------*--------------------------------------------------')
        print(filtro.__str__())
        envio = 1
        trespuntuados = filtro.personaaplicarpartida_set.filter(status=True, estado=1).order_by('-nota_final_meritos')[:3]
        for post_ in trespuntuados:
            personaemail_ = post_.persona.email if post_.persona.email else None
            if personaemail_:
                print('{}/{} - {}'.format(envio, trespuntuados.count(), post_.persona.__str__()))
                send_html_mail("Postulate: Fase de Preselección", "emails/postulate_tres_puntuados.html",
                               {'sistema': u'SISTEMA POSTULATE UNEMI', 'postulante': post_, 'persona': post_.persona, 'partida': filtro,
                                't': miinstitucion()}, [personaemail_], ['rviterib1@unemi.edu.ec', 'talento_humano@unemi.edu.ec'], cuenta=CUENTAS_CORREOS[30][1])
                envio += 1


def email_banco_datos_puntuados():
    partidas = Partida.objects.filter(status=True, convocatoria__vigente=True)
    for filtro in partidas:
        print('----------------------------------------------------------*--------------------------------------------------')
        print(filtro.__str__())
        envio = 1
        bancopuntuados = filtro.personaaplicarpartida_set.filter(status=True, estado=1).order_by('-nota_final_meritos')[3:]
        for post_ in bancopuntuados:
            personaemail_ = post_.persona.email if post_.persona.email else None
            if personaemail_:
                print('{}/{} - {}'.format(envio, bancopuntuados.count(), post_.persona.__str__()))
                send_html_mail("Postulate: Fase de Preselección", "emails/postulate_banco_datos.html",
                               {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': post_.persona, 'partida': filtro,
                                't': miinstitucion()}, [personaemail_], ['rviterib1@unemi.edu.ec', 'talento_humano@unemi.edu.ec'], cuenta=CUENTAS_CORREOS[30][1])
                envio += 1

email_tres_mejores_puntuados()
email_banco_datos_puntuados()