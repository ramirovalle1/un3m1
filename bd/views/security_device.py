# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django_user_agents.utils import get_user_agent

from bd.funciones import generate_code
from bd.models import LogQuery, UserAccessSecurity, UserAccessSecurityType, UserAccessSecurityDevice, \
    UserAccessSecurityCode
from decorators import secure_module, last_access
from bd.forms import CodeTwoStepVerificationForm
from settings import DEBUG
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery
from sga.models import CUENTAS_CORREOS
from sga.tasks import send_html_mail


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if not 'validateTwoStepAccess' in request.session:
        return HttpResponseRedirect("/")
    validateTwoStepAccess = request.session['validateTwoStepAccess']
    if not validateTwoStepAccess:
        return HttpResponseRedirect("/")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'validaCode':
            try:
                form = CodeTwoStepVerificationForm(request.POST, request.FILES)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if not 'idc' in request.POST:
                    raise NameError(u"No se encontro parametro correcto")
                idc = request.POST['idc']
                eUserAccessSecurityCode = UserAccessSecurityCode.objects.filter(pk=idc).first()
                if not eUserAccessSecurityCode:
                    raise NameError(u"Parametro de código incorrecto")
                if eUserAccessSecurityCode.wasValidated:
                    raise NameError(u"Código fue validado")
                if not eUserAccessSecurityCode.isActive:
                    raise NameError(u"Código fue inactivado")
                if not eUserAccessSecurityCode.isValidoTime():
                    raise NameError(u"Código tiempo de caducidad")
                codigo = form.codigo()
                if not eUserAccessSecurityCode.isValidoCodigo(codigo):
                    raise NameError(u"Código invalido")
                eUserAccessSecurityType = eUserAccessSecurityCode.user_access_type
                UserAccessSecurityCode.objects.filter(user_access_type=eUserAccessSecurityType).exclude(pk=idc).update(isActive=False)
                date_expires = datetime.now() + timedelta(minutes=5)
                eUserAccessSecurityCode.wasValidated = True
                eUserAccessSecurityCode.date_expires = date_expires
                eUserAccessSecurityCode.save(request)
                request.session['eUserAccessSecurityCode'] = eUserAccessSecurityCode
                return JsonResponse({"result": 'ok', "mensaje": f''})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f'{ex.__str__()}'})

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

        elif action == 'addDesvice':
            try:
                eUserAccessSecurity = request.session['eUserAccessSecurity']
                eUserAccessSecurityType = request.session['eUserAccessSecurityType']
                # eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(user_access_type=eUserAccessSecurityType)
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_public = x_forwarded_for.split(',')[0]
                else:
                    ip_public = request.META.get('REMOTE_ADDR')
                user_agent = get_user_agent(request)
                # Let's assume that the visitor uses an iPhone...
                type = 6
                if user_agent.is_mobile:
                    type = 1
                elif user_agent.is_tablet:
                    type = 2
                elif user_agent.is_touch_capable:
                    type = 3
                elif user_agent.is_pc:
                    type = 4
                elif user_agent.is_bot:
                    type = 5
                # Accessing user agent's browser attributes
                browser = user_agent.browser
                browser_family = browser.family
                browser_version = browser.version_string
                # Operating System properties
                os = user_agent.os
                os_family = os.family
                os_version = os.version_string
                # Device properties
                device = user_agent.device
                device_family = device.family
                isActiveGet = request.POST.get('isActive', '0')
                isActive = isActiveGet == '1'
                eUserAccessSecurityDevice = UserAccessSecurityDevice.objects.filter(user_access_type=eUserAccessSecurityType,
                                                                              ip_public=ip_public, type=type,
                                                                               browser=browser_family,
                                                                               browser_version=browser_version,
                                                                               os=os_family,
                                                                               os_version=os_version,
                                                                               device=device_family,
                                                                               ).first()
                if eUserAccessSecurityDevice:
                    if eUserAccessSecurityDevice.isActive:
                        raise NameError(u"Dispositivo ya se encuentra registrado")
                    eUserAccessSecurityDevice.isActive = isActive
                    eUserAccessSecurityDevice.last_access = datetime.now()
                else:
                    eUserAccessSecurityDevice = UserAccessSecurityDevice(user_access_type=eUserAccessSecurityType,
                                                                         ip_public=ip_public,
                                                                         type=type,
                                                                         browser=browser_family,
                                                                         browser_version=browser_version,
                                                                         os=os_family,
                                                                         os_version=os_version,
                                                                         device=device_family,
                                                                         last_access=datetime.now())
                eUserAccessSecurityDevice.save(request)
                log(u'Adiciono dispositivo de verificación de dos pasos: %s' % eUserAccessSecurityDevice, request, "add")
                request.session['validateTwoStepAccess'] = False
                request.session['eUserAccessSecurity'] = None
                request.session['eUserAccessSecurityType'] = None
                request.session['eUserAccessSecurityCode'] = None
                eUserAccessSecurityType = eUserAccessSecurityDevice.user_access_type
                UserAccessSecurityCode.objects.filter(user_access_type=eUserAccessSecurityType).update(isActive=False)
                if isActive:
                    return JsonResponse({"result": 'ok', "mensaje": u"Se adicionó correctamente el dispositivo como confiable"})
                else:
                    return JsonResponse({"result": 'cancel'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error: {ex.__str__()}"})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            try:
                eUserAccessSecurity = request.session['eUserAccessSecurity']
                eUserAccessSecurityType = request.session['eUserAccessSecurityType']
                if not 'eUserAccessSecurityCode' in request.session or request.session['eUserAccessSecurityCode'] is None:
                    code = generate_code(6)
                    date_expires = datetime.now() + timedelta(minutes=5)
                    eUserAccessSecurityCodes = UserAccessSecurityCode.objects.filter(user_access_type=eUserAccessSecurityType, isActive=True, date_expires__gt=datetime.now())
                    if not eUserAccessSecurityCodes.values("id").exists():
                        UserAccessSecurityCode.objects.filter(user_access_type=eUserAccessSecurityType).update(isActive=False)
                        eUserAccessSecurityCode = UserAccessSecurityCode(user_access_type=eUserAccessSecurityType,
                                                                         date_expires=date_expires,
                                                                         codigo=code)
                        eUserAccessSecurityCode.save(request)
                        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                        if x_forwarded_for:
                            ip_public = x_forwarded_for.split(',')[0]
                        else:
                            ip_public = request.META.get('REMOTE_ADDR')
                        user_agent = get_user_agent(request)
                        send_html_mail("Código de verificación de dos pasos",
                                       "security/emails/codigo_verificacion.html",
                                       {
                                           'sistema': u'Sistema de Gestión Académica',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'ip': ip_public,
                                            'user_agent': user_agent,
                                            'persona': persona,
                                            'eUserAccessSecurityCode': eUserAccessSecurityCode
                                        },
                                       persona.lista_emails_envio(), [],
                                       cuenta=CUENTAS_CORREOS[0][1])
                    else:
                        eUserAccessSecurityCode = eUserAccessSecurityCodes.first()
                    request.session['eUserAccessSecurityCode'] = eUserAccessSecurityCode
                    if not eUserAccessSecurityCode.wasValidated:
                        request.session['eUserAccessSecurityCode'] = None
                        data['eUserAccessSecurityCode'] = eUserAccessSecurityCode
                        data['title'] = 'Seguridad acceso código'
                        return render(request, "security/code.html", data)
                eUserAccessSecurityCode = request.session['eUserAccessSecurityCode']
                if not DEBUG:
                    if not eUserAccessSecurityCode.wasValidated or not eUserAccessSecurityCode.isValidoTime() or not eUserAccessSecurityCode.isActive:
                        request.session['eUserAccessSecurityCode'] = None
                        raise NameError(f"{request.path}?info=Tiempo de acceso terminó")
                eUserAccessSecurity = request.session['eUserAccessSecurity']
                eUserAccessSecurityType = request.session['eUserAccessSecurityType']
                eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(user_access_type=eUserAccessSecurityType)
                data['title'] = 'Gestionar privacidad de mis dispostivos'
                if eUserAccessSecurityType.can_add_device():
                    data['title'] = 'Verificación de dos pasos'
                    # data['sub_title'] = 'Dónde has iniciado sesión'
                data['eUserAccessSecurity'] = eUserAccessSecurity
                data['eUserAccessSecurityType'] = eUserAccessSecurityType
                data['eUserAccessSecurityDevices'] = eUserAccessSecurityDevices
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_public = x_forwarded_for.split(',')[0]
                else:
                    ip_public = request.META.get('REMOTE_ADDR')
                user_agent = get_user_agent(request)
                data['user_agent'] = user_agent
                data['ip_public'] = ip_public
                return render(request, "security/view.html", data)
            except Exception as ex:
                data['error'] = ex.__str__()
                return render(request, "security/error.html", data)
