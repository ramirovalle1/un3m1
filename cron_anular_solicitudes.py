import os
import json

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from certi.models import Certificado
from secretaria.models import Solicitud, HistorialSolicitud
from datetime import datetime, timedelta
from sagest.models import Rubro
from django.db import connections

try:
    print('*********ANULACIÓN DE SOLICITUDES VENCIDAS****************')
    c = 0
    eSolicitudes = Solicitud.objects.filter(status=True, estado__in=(1, 3)).exclude(servicio__categoria__id=7)
    for eSolicitud in eSolicitudes:
        if Rubro.objects.filter(status=True, solicitud=eSolicitud, tipo=eSolicitud.servicio.tiporubro, epunemi=True).exists():
            rubrosoli = Rubro.objects.get(status=True, solicitud=eSolicitud, tipo=eSolicitud.servicio.tiporubro, epunemi=True)
            fecha_limite = eSolicitud.fecha_limite_pago()
            if datetime.today() > fecha_limite:
                cursor = connections['epunemi'].cursor()
                sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (
                    eSolicitud.perfil.persona.cedula, eSolicitud.perfil.persona.cedula,
                    eSolicitud.perfil.persona.cedula)
                cursor.execute(sql)
                idalumno = cursor.fetchone()

                if idalumno is not None:
                    sql = """SELECT deta.id FROM crm_detallepedidoonline deta 
                                INNER JOIN crm_pedidoonline pedi ON deta.pedido_id = pedi.id
                                WHERE deta.rubro_id = %s AND pedi.persona_id=%s AND deta."status" AND pedi."status"
                                AND pedi.estado = 1;""" % (rubrosoli.idrubroepunemi, idalumno[0])
                    cursor.execute(sql)
                    idpedi = cursor.fetchone()

                    if idpedi is None:
                        solicitudVencida = eSolicitud
                        ePersona = solicitudVencida.perfil.persona
                        solicitudVencida.estado = 8
                        solicitudVencida.save()
                        eRubro = Rubro.objects.get(persona=ePersona, solicitud=solicitudVencida)

                        eHistorialSolicitud = HistorialSolicitud(solicitud=solicitudVencida,
                                                                 observacion=f'Cambio de estado por solicitud eliminada',
                                                                 fecha=datetime.now().date(),
                                                                 hora=datetime.now().time(),
                                                                 estado=solicitudVencida.estado,
                                                                 responsable=ePersona)
                        eHistorialSolicitud.save()

                        solicitudVencida.generar_notificacion(ePersona)

                        if eRubro.tiene_pagos():
                            solicitudVencida.estado = 3
                            solicitudVencida.en_proceso = True
                            eRubro.save()
                        else:
                            eRubro.status = False
                            solicitudVencida.en_proceso = False
                            eRubro.save()

                            if eRubro.idrubroepunemi != 0:
                                cursor = connections['epunemi'].cursor()
                                sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s;""" % (eRubro.idrubroepunemi)
                                cursor.execute(sql)
                                tienerubropagos = cursor.fetchone()

                                if tienerubropagos is None:
                                    sql = """UPDATE  sagest_rubro SET status=FALSE  WHERE sagest_rubro.id=%s AND sagest_rubro.idrubrounemi=%s; """ % (
                                    eRubro.idrubroepunemi, eRubro.id)
                                    cursor.execute(sql)
                                    cursor.close()
                        c += 1
        else:
            fecha_limite = eSolicitud.fecha_limite_pago()
            if datetime.today() > fecha_limite:
                solicitudVencida = eSolicitud
                ePersona = solicitudVencida.perfil.persona
                solicitudVencida.estado = 9
                solicitudVencida.en_proceso = False
                solicitudVencida.save()

                eHistorialSolicitud = HistorialSolicitud(solicitud=solicitudVencida,
                                                         observacion=f'Cambio de estado por solicitud vencida',
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         estado=solicitudVencida.estado,
                                                         responsable=ePersona)
                eHistorialSolicitud.save()

                solicitudVencida.generar_notificacion_2(ePersona)

    #SOLICITUDES ELIMINADAS
    eSolicitudes = Solicitud.objects.filter(status=True, estado=9).exclude(servicio__categoria__id=7)

    if eSolicitudes:
        for solicitudVencida in eSolicitudes:
            ePersona = solicitudVencida.perfil.persona
            if Rubro.objects.filter(persona=ePersona, solicitud=solicitudVencida).exists():
                eRubro = Rubro.objects.filter(persona=ePersona, solicitud=solicitudVencida).first()

                tiempoadd = solicitudVencida.tiempo_cobro + 72
                fecha_comparacion = eRubro.fechavence + timedelta(hours=tiempoadd)
                if datetime.today().date() > fecha_comparacion:
                    if eRubro.tiene_pagos():
                        solicitudVencida.estado = 3
                        solicitudVencida.en_proceso = True
                        solicitudVencida.save()
                        eRubro.save()
                    else:
                        eRubro.status = False
                        solicitudVencida.estado = 8
                        solicitudVencida.en_proceso = False
                        solicitudVencida.save()
                        eRubro.save()

                solicitudVencida.generar_notificacion(ePersona)

    print(f'Solicitudes anuladas: {c}')
except Exception as ex:
    pass

