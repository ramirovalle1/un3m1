#!/usr/bin/env python
import os
import sys


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
from posgrado.models import *


def resetear_clavepostulante(persona):
    if not persona.usuario.is_superuser:
        if persona.cedula:
            password = persona.cedula.strip()
        elif persona.pasaporte:
            password = persona.pasaporte.strip()
        user = persona.usuario
        user.set_password(password)
        user.save()
        # if variable_valor('VALIDAR_LDAP'):
        #     validar_ldap(user.username, password, persona)



listado = PreInscripcion.objects.filter(carrera_id=174, status=True)
lista = []
for listapre in listado:
    print(listapre)
    if not listapre.persona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
        resetear_clavepostulante(listapre.persona)
        formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=listapre.carrera_id, status=True)[0]
        if formatocorreo.correomaestria:
            lista.append(formatocorreo.correomaestria)
        lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
        if listapre.persona.cedula:
            password = listapre.persona.cedula.strip()
        elif listapre.persona.pasaporte:
            password = listapre.persona.pasaporte.strip()
        aspirante = InscripcionAspirante.objects.filter(persona=listapre.persona, status=True)[0]
        asunto = u"ADMISIÓN POSGRADO"
        send_html_mail(asunto, "emails/masivoregistroexito.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
                        'usuario': listapre.persona.usuario.username,
                        'clave': password,
                        'carrera': listapre.carrera.nombre,
                        'formato': formatocorreo.banner},
                       lista, [], [formatocorreo.archivo],
                       cuenta=CUENTAS_CORREOS[18][1])
    else:
        formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=listapre.carrera_id, status=True)[0]
        if formatocorreo.correomaestria:
            lista.append(formatocorreo.correomaestria)
        lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
        if listapre.persona.cedula:
            password = listapre.persona.cedula.strip()
        elif listapre.persona.pasaporte:
            password = listapre.persona.pasaporte.strip()
        aspirante = InscripcionAspirante.objects.filter(persona=listapre.persona, status=True)[0]
        asunto = u"ADMISIÓN POSGRADO"
        send_html_mail(asunto, "emails/masivoregistroexitopersonal.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
                        'carrera': listapre.carrera.nombre,
                        'formato': formatocorreo.banner},
                       lista, [], [formatocorreo.archivo],
                       cuenta=CUENTAS_CORREOS[18][1])
