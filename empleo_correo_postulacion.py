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
# from sga.models import *
# from sagest.models import *
import xlrd
from empleo.models import PersonaAplicaOferta, OfertaLaboralEmpresa
from sga.models import *


def emails_postulaciones_diarias():
    empresas = OfertaLaboralEmpresa.objects.filter(status=True, estadooferta=1, personaaplicaoferta__fecha_creacion__gte=datetime.now().date()).values_list('empresa_id', flat=True).distinct()

    for empresa in empresas:
        listadooferta = OfertaLaboralEmpresa.objects.filter(empresa_id=empresa, finicio__lte=datetime.now().date(),
                                                            ffin__gte=datetime.now().date(), estadooferta=1, status=True)
        empresa = Empleador.objects.get(id=empresa)
        oferta = OfertaLaboralEmpresa.objects.filter(status=True,empresa_id=empresa).first()
        send_html_mail(u"Postulación recibida, UNEMI-EMPLEO.",
                       "emails/postulate_aplica_partida_empresa.html",
                       {'sistema': u'UNEMI- EMPLEO', 'fecha': datetime.now().date(),
                        'hora': datetime.now().time(), 'empresa': empresa,
                        'listadooferta': listadooferta, 't': miinstitucion(),
                        'tit': 'Unemi-Empleo'},
                       oferta.empresa.persona.lista_emails_envio(), [], [], cuenta=CUENTAS_CORREOS[17][1])


emails_postulaciones_diarias()