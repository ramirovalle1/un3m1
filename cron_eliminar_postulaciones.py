import os
import json

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from certi.models import Certificado
from secretaria.models import Solicitud, HistorialSolicitud
from datetime import datetime, timedelta
from sagest.models import Rubro, Matricula
from django.db import connections
from posgrado.models import InscripcionCohorte
from sga.models import Persona
from sga.funciones import notificacion2, variable_valor
try:
    solicitudes = Solicitud.objects.filter(status=True, estado=22, certificadofirmado=False)

    secretarias = Persona.objects.filter(id__in=variable_valor('PERSONAL_SECRETARIA_GENERAL'))

    for secretaria in secretarias:
        for solicitud in solicitudes:
            titulo = "CERTIFICADOS PENDIENTES DE FIRMA"
            cuerpo = f'Se le comunica que a {secretaria} que el maestrante {solicitud.perfil.inscripcion.persona} ha realizado el pago del rubro generado, y requiere la firma electrónica de la secretaria general. Clic en URL, para ser redirigido al respectivo módulo.'

            notificacion2(titulo, cuerpo, secretaria, None,
                          '/adm_secretaria?action=listadoafirmar&id=1&ide=0&s=' + str(solicitud.perfil.inscripcion.persona.cedula),
                          secretaria.pk, 1, 'sga', secretaria)

    # hoy = datetime.now().date()
    id_inscripcion = Matricula.objects.filter(inscripcion__carrera__coordinacion__id=7).values_list('inscripcion__id', flat=True)
    postulantes = InscripcionCohorte.objects.filter(status=True, cohortes__procesoabierto=False, estado_aprobador=1, todosubido=False).exclude(inscripcion__id__in=id_inscripcion)
    c = 0
    if postulantes:
        for postulante in postulantes:
            if postulante.total_pagado_rubro_cohorte() == 0:
                postulante.status = False
                postulante.save()
                c += 1
            print(f"N°: {c} - Postulante: {postulante.inscripcionaspirante.persona} - Cohorte:{postulante.cohortes} - Asesor: {postulante.asesor.persona if postulante.asesor else'No registra'}")
except Exception as ex:
    pass
