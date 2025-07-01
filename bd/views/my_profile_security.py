# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from bd.models import LogQuery, UserAccessSecurity, UserAccessSecurityType, UserAccessSecurityDevice
from decorators import secure_module, last_access
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery
from sagest.funciones import encrypt_id


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}

    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'activate':
            try:
                eUserAccessSecurity = None
                if UserAccessSecurity.objects.values("id").filter(user=persona.usuario).exists():
                    eUserAccessSecurity = UserAccessSecurity.objects.get(user=persona.usuario)
                value = request.POST.get('value', '0')
                value = int(value)
                if value == 0:
                    mensaje = 'Se desactivo verificación de dos pasos correctamente'
                    if eUserAccessSecurity:
                        eUserAccessSecurity.isActive = False
                        eUserAccessSecurity.save(request)
                        eUserAccessSecurityTypes = UserAccessSecurityType.objects.filter(user_access=eUserAccessSecurity, type=1)
                        if eUserAccessSecurityTypes.values("id").exists():
                            eUserAccessSecurityTypes.update(isActive=False)
                            eUserAccessSecurityType = eUserAccessSecurityTypes.first()
                        else:
                            eUserAccessSecurityType = UserAccessSecurityType(user_access=eUserAccessSecurity,
                                                                             type=1,
                                                                             isActive=False)
                            eUserAccessSecurityType.save(request)
                        eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(user_access_type=eUserAccessSecurityType)
                        if eUserAccessSecurityDevices.values("id").exists():
                            eUserAccessSecurityDevices.update(isActive=False)
                        log(u'Desactivo verificación de dos pasos: %s' % eUserAccessSecurity, request, "edit")
                else:
                    mensaje = 'Se activo verificación de dos pasos correctamente'
                    if eUserAccessSecurity:
                        eUserAccessSecurity.isActive = True
                        eUserAccessSecurity.save(request)
                        eUserAccessSecurityTypes = UserAccessSecurityType.objects.filter(user_access=eUserAccessSecurity, type=1)
                        if eUserAccessSecurityTypes.values("id").exists():
                            eUserAccessSecurityTypes.update(isActive=True)
                            eUserAccessSecurityType = eUserAccessSecurityTypes.first()
                        else:
                            eUserAccessSecurityType = UserAccessSecurityType(user_access=eUserAccessSecurity,
                                                                             type=1,
                                                                             isActive=True)
                            eUserAccessSecurityType.save(request)
                        eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(user_access_type=eUserAccessSecurityType)
                        # if eUserAccessSecurityDevices.values("id").exists():
                        #     eUserAccessSecurityDevices.update(isActive=True)
                        log(u'Activo verificación de dos pasos: %s' % eUserAccessSecurity, request, "edit")
                    else:
                        eUserAccessSecurity = UserAccessSecurity(user=persona.usuario,
                                                                 isActive=True)
                        eUserAccessSecurity.save(request)
                        eUserAccessSecurityType = UserAccessSecurityType(user_access=eUserAccessSecurity,
                                                                         type=1,
                                                                         isActive=True)
                        eUserAccessSecurityType.save(request)
                        eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(user_access_type=eUserAccessSecurityType)
                        # if eUserAccessSecurityDevices.values("id").exists():
                        #     eUserAccessSecurityDevices.update(isActive=True)
                        log(u'Agrego y activo verificación de dos pasos: %s' % eUserAccessSecurity, request, "add")
                return JsonResponse({"result": 'ok', "mensaje": mensaje})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error: {ex.__str__()}"})

        elif action == 'deleteDesvice':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Parametro de dispositivo no encontrado")
                eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(pk=request.POST['id'])
                if not eUserAccessSecurityDevices.values("id").exists():
                    raise NameError(u"Dispositivo no encontrado")
                eUserAccessSecurityDevice = delete = eUserAccessSecurityDevices.first()
                eUserAccessSecurityDevice.delete()
                log(u'Elimino dispositivo de verificación de dos pasos: %s' % delete, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Se elimino correctamente dispositivo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error: {ex.__str__()}"})

        elif action == 'cambiarestadodispositivo':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Parametro de dispositivo no encontrado")
                eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(pk=encrypt_id(request.POST['id']))
                if not eUserAccessSecurityDevices.values("id").exists():
                    raise NameError(u"Dispositivo no encontrado")
                eUserAccessSecurityDevice = eUserAccessSecurityDevices.first()
                eUserAccessSecurityDevice.isActive = not eUserAccessSecurityDevice.isActive
                eUserAccessSecurityDevice.save(request)
                log(u'Cambio estado de dispositivo de verificación de dos pasos: %s' % eUserAccessSecurityDevice,
                    request, "edit")
                return JsonResponse({"result": True, "mensaje": u"Estado actualizado correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'two_step_verification':
                try:
                    data['tab'] = action
                    data['title'] = 'Verificación en dos pasos'
                    eUserAccessSecurity = None
                    eUserAccessSecurityType = None
                    eUserAccessSecurityDevices = None
                    if UserAccessSecurity.objects.values("id").filter(user=persona.usuario).exists():
                        eUserAccessSecurity = UserAccessSecurity.objects.get(user=persona.usuario)
                        eUserAccessSecurityTypes = UserAccessSecurityType.objects.filter(user_access=eUserAccessSecurity, type=1)
                        if eUserAccessSecurityTypes.values("id").exists():
                            eUserAccessSecurityType = eUserAccessSecurityTypes.first()
                        eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(user_access_type=eUserAccessSecurityType)
                    data['eUserAccessSecurity'] = eUserAccessSecurity
                    data['eUserAccessSecurityType'] = eUserAccessSecurityType
                    data['eUserAccessSecurityDevices'] = eUserAccessSecurityDevices
                    request.session['viewactivoth'] = ['configuraciones', 'two_step_verification']
                    return render(request, "my_profile/security/two_step_verification_new.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Mi cuenta'
                request.session['viewactivoth'] = ['configuraciones', 'micuenta']
                data['url_vars'] = ''
                return render(request, "my_profile/security/view2.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info{ex.__str__()}")
