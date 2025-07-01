#!/usr/bin/env python

import os
import json

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()


from sga.models import *
from sagest.models import *
from posgrado.models import InscripcionCohorte
from sga.funciones import notificacion2, notificacion4, variable_valor
from sga.funciones_templatepdf import recordatoriopagomaestrante, recordatoriopagoavencermaestrante
from webpush import send_user_notification
from sga.commonviews import traerNotificaciones2
from webpush.utils import _send_notification
from wpush.models import SubscriptionInfomation
from datetime import datetime, timedelta
from posgrado.models import RecordatorioPagoMaestrante

hoy = datetime.now().date()
cnmoodle = connections['moodle_pos'].cursor()
# Consultar las matrículas bloqueadas
contador = 0
listadoidsmatriculas = Rubro.objects.values_list('matricula_id').filter(matricula__bloqueomatricula=True, tipo__tiporubro=1, tipo__subtiporubro=1, status=True).distinct()
excepciones = [int(num) for num in variable_valor('IDS_NO_BLOQUEADOS')]

for lismatri in listadoidsmatriculas:
    if int(lismatri[0]) not in [513163, 513127, 512508, 512524, 513250, 512615]:
        matricula = Matricula.objects.get(pk=lismatri[0])

        # Obtener total rubros vencidos
        rubrosvencidos = matricula.rubro_set.filter(fechavence__lt=hoy, tipo__tiporubro=1, cancelado=False, status=True).count()

        if rubrosvencidos < 2:
            # Desbloqueo de matrícula
            matricula.bloqueomatricula = False
            matricula.save()

            # Consulto usuario de moodle posgrado
            usermoodle = matricula.inscripcion.persona.idusermoodleposgrado

            if usermoodle != 0:
                # Consulta en mooc_user
                sql = """Select id, username From mooc_user Where id=%s""" % (usermoodle)
                cnmoodle.execute(sql)
                registro = cnmoodle.fetchall()
                idusuario = registro[0][0]
                username = registro[0][1]
                #
                # Asignar estado deleted = 0 para que pueda acceder al aula virtual
                sql = """Update mooc_user Set deleted=0 Where id=%s""" % (idusuario)
                cnmoodle.execute(sql)

            contador += 1
            print('Matrícula desbloqueada ' + str(matricula))

print("Total desbloqueados:", contador)


listarubroos = Rubro.objects.values_list('matricula_id', 'matricula__nivel__periodo_id').filter(fechavence__lt=hoy, matricula__bloqueomatricula=False, matricula__isnull=False, tipo__tiporubro=1, tipo__subtiporubro=1, cancelado=False, status=True).annotate(id=Count('id')).distinct()
# print(listarubroos.query)
contador = 0
for lis in listarubroos:
    # Si numero de cuotas es mayor o igual a 3
    if lis[2] >= 2:
        # No bloquear a Avecilla Guzman José Manuel, Diana Macías manifiesta por e-mail del 28/04/2022 que el va a recibir descuento
        if lis[0] not in excepciones:
            contador = contador + 1
            matricula = Matricula.objects.get(pk=lis[0])
            if not matricula.esta_cursando_modulo():
                matricula.bloqueomatricula = True
                matricula.save()

                # Consulto usuario de moodle posgrado
                usermoodle = matricula.inscripcion.persona.idusermoodleposgrado

                if usermoodle != 0:
                    # Consulta en mooc_user
                    sql = """Select id, username From mooc_user Where id=%s""" % (usermoodle)
                    cnmoodle.execute(sql)
                    registro = cnmoodle.fetchall()
                    idusuario = registro[0][0]
                    username = registro[0][1]
                    #
                    # Asignar estado deleted = 1 para que no pueda acceder al aula virtual
                    sql = """Update mooc_user Set deleted=1 Where id=%s""" % (idusuario)
                    cnmoodle.execute(sql)
                    #
                    # Envío de correo notificando el motivo del bloqueo en el moodle
                    tituloemail = "Notificación de inhabilitación de credenciales de sistemas académicos por valores pendientes"
                    #
                    send_html_mail(tituloemail,
                                   "emails/bloqueomatriculaposgrado.html",
                                   {'sistema': u'POSGRADO - UNEMI',
                                    'saludo': 'Estimada' if matricula.inscripcion.persona.sexo_id == 1 else 'Estimado',
                                    'estudiante': matricula.inscripcion.persona.nombre_completo_inverso(),
                                    },
                                   matricula.inscripcion.persona.lista_emails(),
                                   [],
                                   cuenta=CUENTAS_CORREOS[18][1]
                                   )

                print('Matrícula bloqueada ' + str(matricula))

print("Total bloqueados:", contador)

cnmoodle.close()

# listarubroos = Rubro.objects.values_list('matricula_id').filter(matricula__bloqueomatricula=False, matricula__isnull=False, tipo__tiporubro=1, cancelado=False, status=True).distinct().order_by('-id')
# contador = 0
# today = datetime.now()
# hora_actual = today.strftime("%H:%M:%S")
# hora_ac = datetime.strptime(hora_actual, "%X").time()
# hora1 = datetime.strptime("11:30:00", "%X").time()
# hora2 = datetime.strptime("13:30:00", "%X").time()
# for lis in listarubroos:
#     matricula = Matricula.objects.get(pk=lis[0])
#     rubroafacturar = matricula.rubro_set.filter(tipo__tiporubro=1, cancelado=False, status=True).order_by('fechavence').first()
#     vencidas = matricula.rubro_set.filter(fechavence__lt=hoy, tipo__tiporubro=1, cancelado=False, status=True).count()
#
#     actual = datetime.now().date()
#     vence = rubroafacturar.fechavence
#
#     if vencidas == 0:
#         if rubroafacturar:
#             if vence >= actual:
#                 resu = vence - actual
#                 if resu.days >= 0 and resu.days <= 10:
#                     if resu.days == 0 or resu.days == 1 or resu.days == 3 or resu.days == 5 or resu.days == 10:
#                         if hora_ac >= hora1 and hora_ac <= hora2:
#                             contador = contador + 1
#                             titulo = "Recordatorio de pagos a vencer"
#                             cuerpo = 'Se informa a usted que de acuerdo con lo previsto en su tabla de amortización ' \
#                                      'se encuentra próximo a cancelar su siguiente cuota del programa de maestría ' \
#                                      'adquirido. Agradecemos realizar la gestión de pago pertinente, ' \
#                                      'a fin de que su proceso de estudios de posgrados no se vea afectado. Puede ' \
#                                      'obtener más información dando clic en la URL.'
#                             notificacion2(titulo,
#                                           cuerpo, matricula.inscripcion.persona, None, recordatoriopagoavencermaestrante(matricula.id),
#                                           matricula.pk, 1, 'sga', matricula)
#
#                             notificacion4(titulo,
#                                           cuerpo, matricula.inscripcion.persona, None, recordatoriopagoavencermaestrante(matricula.id)[24:],
#                                           matricula.pk, 1, 'SIE', matricula, matricula.inscripcion.perfil_usuario_posgrado())
#
#                             # perso = Persona.objects.get(status=True, id=38472)
#                             # usua = User.objects.get(id=35288)
#
#                             send_user_notification(user=matricula.inscripcion.persona.usuario, payload={
#                                 "head": "Recordatorio de pagos a vencer",
#                                 "body": 'Alerta de pagos próximos a vencer',
#                                 "action": "notificacion",
#                                 "timestamp": time.mktime(datetime.now().timetuple()),
#                                 "url": recordatoriopagoavencermaestrante(matricula.id),
#                                 "btn_notificaciones": traerNotificaciones2(matricula.inscripcion.persona),
#                                 "mensaje": 'Se informa a usted que de acuerdo con lo previsto en su tabla de amortización, '
#                                         'se encuentra próximo a cancelar su siguiente cuota del programa de maestría '
#                                         'adquirido. Agradecemos realizar la gestión de pago pertinente, '
#                                         'a fin de que su proceso de estudios de posgrados no se vea afectado. Puede '
#                                         'obtener más información dando clic en la campana de notificaciones del SGA.'
#                             }, ttl=500)
#
#                             # subscriptions = perso.usuario.webpush_info.select_related("subscription")
#                             subscriptions = matricula.inscripcion.persona.usuario.webpush_info.select_related("subscription")
#                             push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=2, status=True).select_related("subscription")
#
#                             url = recordatoriopagoavencermaestrante(matricula.id)
#                             titulo = "Recordatorio de pagos a vencer"
#                             cuerpo = 'Se informa a usted que de acuerdo con lo previsto en su tabla de amortización, '\
#                                      'se encuentra próximo a cancelar su siguiente cuota del programa de maestría '\
#                                      'adquirido. Agradecemos realizar la gestión de pago pertinente, '\
#                                      'a fin de que su proceso de estudios de posgrados no se vea afectado. Puede '\
#                                      'obtener más información dando clic en la campana de notificaciones del SGA.'
#
#
#                             for device in push_infos:
#                                 payload = {
#                                     "head": titulo,
#                                     "body": cuerpo,
#                                     "url": url,
#                                     "action": "loadNotifications",
#                                 }
#                                 try:
#                                     _send_notification(device.subscription, json.dumps(payload), ttl=500)
#                                 except Exception as exep:
#                                     print(f"Fallo de envio del push notification: {exep.__str__()}")
#     else:
#         ultirubro = matricula.rubro_set.filter(fechavence__lt=hoy, tipo__tiporubro=1, cancelado=False, status=True).order_by('-fechavence').first()
#
#         if not RecordatorioPagoMaestrante.objects.filter(status=True, matricula=matricula, rubro=ultirubro).exists():
#             if hora_ac >= hora1 and hora_ac <= hora2:
#                 contador = contador + 1
#                 titulo = "Recordatorio de pagos vencidos"
#                 cuerpo = "Se informa a usted que conforme lo reflejado en el sistema de gestión académica (SGA) de " \
#                          "acuerdo con lo previsto en su tabla de amortización, actualmente mantiene cuotas vencidas " \
#                          "del programa de maestría adquirido. Agradecemos realizar la gestión de pago pertinente, " \
#                          "a fin de que su proceso de estudios de posgrados no se vea afectado. Puede obtener más " \
#                          "información dando clic en la URL."
#                 notificacion2(titulo,
#                               cuerpo, matricula.inscripcion.persona, None, recordatoriopagomaestrante(matricula.id),
#                               matricula.pk, 1, 'sga', matricula)
#
#                 notificacion4(titulo,
#                               cuerpo, matricula.inscripcion.persona, None, recordatoriopagomaestrante(matricula.id)[24:],
#                               matricula.pk, 1, 'SIE', matricula, matricula.inscripcion.perfil_usuario_posgrado())
#
#                 # perso = Persona.objects.get(status=True, id=38472)
#                 # usua = User.objects.get(id=35288)
#                 send_user_notification(user=matricula.inscripcion.persona.usuario, payload={
#                     "head": "Recordatorio de pagos vencidos",
#                     "body": 'Alerta de pagos vencidos',
#                     "action": "notificacion",
#                     "timestamp": time.mktime(datetime.now().timetuple()),
#                     "url": recordatoriopagomaestrante(matricula.id),
#                     "btn_notificaciones": traerNotificaciones2(matricula.inscripcion.persona),
#                     "mensaje": 'Se informa a usted que conforme lo reflejado en el sistema de gestión académica (SGA) de '
#                                'acuerdo con lo previsto en su tabla de amortización, actualmente mantiene cuotas vencidas '
#                                'del programa de maestría adquirido. Agradecemos realizar la gestión de pago pertinente,  '
#                                'a fin de que su proceso de estudios de posgrados no se vea afectado. Puede obtener más '
#                                'información dando clic en la campana de notificaciones del SGA.'
#                 }, ttl=500)
#
#                 # subscriptions = perso.usuario.webpush_info.select_related("subscription")
#                 subscriptions = matricula.inscripcion.persona.usuario.webpush_info.select_related("subscription")
#                 push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=2, status=True).select_related("subscription")
#
#                 url = recordatoriopagomaestrante(matricula.id)
#                 titulo = "Recordatorio de pagos vencidos"
#                 cuerpo = 'Se informa a usted que conforme lo reflejado en el sistema de gestión académica (SGA) de ' \
#                          'acuerdo con lo previsto en su tabla de amortización, actualmente mantiene cuotas vencidas ' \
#                          'del programa de maestría adquirido. Agradecemos realizar la gestión de pago pertinente, ' \
#                          'a fin de que su proceso de estudios de posgrados no se vea afectado. Puede obtener más ' \
#                          'información dando clic en la campana de notificaciones del SGA.'
#
#                 for device in push_infos:
#                     payload = {
#                         "head": titulo,
#                         "body": cuerpo,
#                         "url": url,
#                         "action": "loadNotifications",
#                     }
#                     try:
#                         _send_notification(device.subscription, json.dumps(payload), ttl=500)
#                     except Exception as exep:
#                         print(f"Fallo de envio del push notification: {exep.__str__()}")
#         else:
#             recor = RecordatorioPagoMaestrante.objects.get(status=True, matricula=matricula, rubro=ultirubro)
#             fecha_au = recor.fecha_creacion.date() + timedelta(days=10)
#
#             resu = fecha_au - hoy
#             if resu.days >= 0 and resu.days <= 10:
#                 if resu.days == 0 or resu.days == 1 or resu.days == 3 or resu.days == 5 or resu.days == 10:
#                     if hora_ac >= hora1 and hora_ac <= hora2:
#                         contador = contador + 1
#                         titulo = "Recordatorio de pagos vencidos"
#                         cuerpo = "Se informa a usted que conforme lo reflejado en el sistema de gestión académica (SGA) de " \
#                                  "acuerdo con lo previsto en su tabla de amortización, actualmente mantiene cuotas vencidas " \
#                                  "del programa de maestría adquirido. Agradecemos realizar la gestión de pago pertinente, " \
#                                  "a fin de que su proceso de estudios de posgrados no se vea afectado. Puede obtener más " \
#                                  "información dando clic en la URL."
#                         notificacion2(titulo,
#                                       cuerpo, matricula.inscripcion.persona, None, recordatoriopagomaestrante(matricula.id),
#                                       matricula.pk, 1, 'sga', matricula)
#
#                         notificacion4(titulo,
#                                       cuerpo, matricula.inscripcion.persona, None, recordatoriopagomaestrante(matricula.id)[24:],
#                                       matricula.pk, 1, 'SIE', matricula, matricula.inscripcion.perfil_usuario_posgrado())
#
#                         # perso = Persona.objects.get(status=True, id=38472)
#                         # usua = User.objects.get(id=35288)
#                         send_user_notification(user=matricula.inscripcion.persona.usuario, payload={
#                             "head": "Recordatorio de pagos vencidos",
#                             "body": 'Alerta de pagos vencidos',
#                             "action": "notificacion",
#                             "timestamp": time.mktime(datetime.now().timetuple()),
#                             "url": recordatoriopagomaestrante(matricula.id),
#                             "btn_notificaciones": traerNotificaciones2(matricula.inscripcion.persona),
#                             "mensaje": 'Se informa a usted que conforme lo reflejado en el sistema de gestión académica (SGA) de '
#                                        'acuerdo con lo previsto en su tabla de amortización, actualmente mantiene cuotas vencidas '
#                                        'del programa de maestría adquirido. Agradecemos realizar la gestión de pago pertinente,  '
#                                        'a fin de que su proceso de estudios de posgrados no se vea afectado. Puede obtener más '
#                                        'información dando clic en la campana de notificaciones del SGA.'
#                         }, ttl=500)
#
#                         subscriptions = matricula.inscripcion.persona.usuario.webpush_info.select_related("subscription")
#                         # subscriptions = perso.usuario.webpush_info.select_related("subscription")
#                         push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=2, status=True).select_related("subscription")
#
#                         url = recordatoriopagomaestrante(matricula.id)
#                         titulo = "Recordatorio de pagos vencidos"
#                         cuerpo = 'Se informa a usted que conforme lo reflejado en el sistema de gestión académica (SGA) de ' \
#                                  'acuerdo con lo previsto en su tabla de amortización, actualmente mantiene cuotas vencidas ' \
#                                  'del programa de maestría adquirido. Agradecemos realizar la gestión de pago pertinente, ' \
#                                  'a fin de que su proceso de estudios de posgrados no se vea afectado. Puede obtener más ' \
#                                  'información dando clic en la campana de notificaciones del SGA.'
#
#                         for device in push_infos:
#                             payload = {
#                                 "head": titulo,
#                                 "body": cuerpo,
#                                 "url": url,
#                                 "action": "loadNotifications",
#                             }
#                             try:
#                                 _send_notification(device.subscription, json.dumps(payload), ttl=500)
#                             except Exception as exep:
#                                 print(f"Fallo de envio del push notification: {exep.__str__()}")
#
# print("Total de recordatorios enviados:", contador)
