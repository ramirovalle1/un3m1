import json
from datetime import time, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, F, FloatField
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from webpush import send_user_notification

from wpush.functiones import action_depurar_dispositivos_activos
from wpush.models import PushInformation
from webpush.utils import _send_notification

from decorators import secure_module, last_access
from sga.commonviews import adduserdata


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'delalldispositivo':
                try:
                    listado_ = PushInformation.objects.filter(user=request.user)
                    for l_ in listado_:
                        eliminarcontrato = PushInformation.objects.get(pk=l_.id)
                        eliminarcontrato.delete()
                    return JsonResponse({'error': False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'error'
                                         '': True, 'mensaje': u'Error al eliminar los datos'})
            if action == 'deldispositivo':
                try:
                    eliminarcontrato = PushInformation.objects.get(pk=request.POST['id'])
                    eliminarcontrato.delete()
                    return JsonResponse({'error': False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'error'
                                         '': True, 'mensaje': u'Error al eliminar los datos'})
            if action == 'notiall':
                try:
                    send_user_notification(user=request.user, payload={
                        "head": "Mensaje de Prueba",
                        "body": 'Enviado por: {} {} {}'.format(persona.nombres, persona.apellido1, persona.apellido2),
                        "action": "notificacion",
                        "url": "{}".format(request.path),
                        "noti_mensaje": "Notificación Recibida",
                    }, ttl=500)
                    return JsonResponse({'error': False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, 'mensaje': u'Error al eliminar los datos'})
            if action == 'notiindv':
                try:
                    id = request.POST['id']
                    device = PushInformation.objects.get(pk=id)
                    _send_notification(device.subscription, json.dumps({
                        "head": "{} Prueba".format(device.subscription.browser),
                        "body": 'Enviado por: {} {} {}'.format(persona.nombres, persona.apellido1, persona.apellido2),
                        "action": "notificacion",
                        "url": "{}".format(request.path),
                        "noti_mensaje": "Notificación Recibida",
                    }), 500)

                    _send_notification(device.subscription, json.dumps({
                        "head": "{} Prueba".format(device.subscription.browser),
                        "body": 'Enviado por: {} {} {}'.format(persona.nombres, persona.apellido1, persona.apellido2),
                        "action": "notificacion",
                        "timestamp": time.mktime(datetime.now().timetuple()),
                        "url": "{}".format(request.path),
                        "btn_notificaciones": {"data": 1},
                        "mensaje": 'Notificación Recibida'
                    }), ttl=500)
                    return JsonResponse({'error': False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'error': True, 'mensaje': u'Error al eliminar los datos'})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
        else:
            try:
                # action_depurar_dispositivos_activos(request.user)
                data['webpush_permisos'] = permisos = PushInformation.objects.filter(user=request.user).order_by('-pk')
                return render(request, "misdispositivos/listado.html", data)
            except Exception as ex:
                messages.error(request, str(ex))
                return render(request, "misdispositivos/listado.html", data)
