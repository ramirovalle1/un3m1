# coding=latin-1
# -*- coding: latin-1 -*-
import random
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template

from bd.models import FLAG_FAILED, FLAG_SUCCESSFUL, FLAG_UNKNOWN, APP_VINCULACION
from core.funciones_adicionales import redireccion_acceso
from core.generic_forms import SignupForm, LoginForm
from decorators import last_access
from poli.models import PoliticaPolideportivo
from postulate.models import PersonaAplicarPartida
from settings import EMAIL_DOMAIN, SERVER_RESPONSE, DEBUG, PIE_PAGINA_CREATIVE_COMMON_LICENCE, CHEQUEAR_CORREO

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.db.models.query_utils import Q

from datetime import datetime

from sga.commonviews import adduserdata
from sga.funciones import calculate_username, generar_usuario_cedula, log, loglogin, \
    resetear_clave_postulate, convertir_fecha_invertida, null_to_decimal, generar_usuario, generar_usuario_externo, validarcedula
from sga.models import Persona, CUENTAS_CORREOS, PerfilUsuario, Postulante, Group, User, miinstitucion, Notificacion, Externo
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import consultarPersona


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# CIERRA LA SESSION DEL USUARIO
def signout_user(request):
    if 'url_offline' in request.session:
        url_ = request.session['url_offline']+'?next=login'
        logout(request)
        return HttpResponseRedirect(url_)
    else:
        logout(request)
        return HttpResponseRedirect("/?next=login")

# ADICIONA LOS DATOS DEL USUARIO A LA SESSION
def adduserdata(request, data):
    # ADICIONA EL USUARIO A LA SESSION
    if 'persona' not in request.session:
        if not request.user.is_authenticated:
            raise Exception('Usuario no autentificado en el sistema')
        request.session['persona'] = Persona.objects.get(usuario=request.user)
    data['version_static'] = '23.0.1'
    data['persona'] = persona = request.session['persona']
    data['check_session'] = False
    data['server_response'] = SERVER_RESPONSE
    data['DEBUG'] = DEBUG
    if 'ultimo_acceso' not in request.session:
            request.session['ultimo_acceso'] = datetime.now()
    data['nombresistema'] = request.session['nombresistema']
    data['tiposistema'] = request.session['tiposistema']
    data['url_entrada'] = request.session['url_entrada']
    data['url_offline'] = ''
    data['currenttime'] = datetime.now()
    data['remotenameaddr'] = '%s' % (request.META['SERVER_NAME'])
    data['remoteaddr'] = '%s - %s' % (get_client_ip(request), request.META['SERVER_NAME'])
    data['pie_pagina_creative_common_licence'] = PIE_PAGINA_CREATIVE_COMMON_LICENCE
    data['chequear_correo'] = CHEQUEAR_CORREO
    data['perfilprincipal'] = perfilprincipal = request.session['perfilprincipal']
    request.user.is_superuser = False
    data['request'] = request
    data['info'] = request.GET['info'] if 'info' in request.GET else ''



# @last_access
@transaction.atomic()
def control_acceso(request):
    data = {}
    client_address = get_client_ip(request)
    data['currenttime'] = datetime.now()

    if request.method == 'POST':
        nombresistema = request.POST.get('nombresistema', 'Servicios de Vinculación')
        tiposistema = request.POST.get('tiposistema', 'serviciosvinculacion')
        url_entrada = request.POST.get('url_entrada', '')
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'signup':
                try:
                    form = SignupForm(request.POST)
                    if not form.is_valid():
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    tipo = form.cleaned_data['tipoidentificacion']
                    identificacion = form.cleaned_data['identificacion'].strip()
                    pers = consultarPersona(identificacion)
                    if not pers:
                        pers = Persona(cedula=identificacion if tipo == 1 else '',
                                       pasaporte=identificacion if tipo == 2 else '',
                                       nombres=form.cleaned_data['nombres'],
                                       apellido1=form.cleaned_data['apellido1'],
                                       apellido2=form.cleaned_data['apellido2'],
                                       nacimiento=form.cleaned_data['nacimiento'],
                                       telefono=form.cleaned_data['telefono'],
                                       sexo=form.cleaned_data['sexo'],
                                       email=form.cleaned_data['email'],
                                       )
                        pers.save(request)
                    else:
                        pers.nombres = form.cleaned_data['nombres']
                        pers.apellido1 = form.cleaned_data['apellido1']
                        pers.apellido2 = form.cleaned_data['apellido2']
                        pers.nacimiento = form.cleaned_data['nacimiento']
                        pers.sexo = form.cleaned_data['sexo']
                        pers.telefono = form.cleaned_data['telefono']
                        pers.email = form.cleaned_data['email']
                        pers.save(request, update_fields=['email', 'telefono', 'nombres', 'apellido1', 'apellido2','nacimiento','sexo'])

                    if not pers.tiene_perfil():
                        externo = Externo.objects.filter(status=True, persona=pers)
                        if not externo:
                            externo = Externo(persona=pers)
                            externo.save(request)
                        perfil = PerfilUsuario(persona=pers, externo=externo)
                        perfil.save(request)
                    if not pers.usuario:
                        username = calculate_username(pers)
                        password = generar_usuario_externo(pers, username, 459)
                        mensaje = f"Se envio un correo de verificación de cuenta a {pers.email}, por favor revisar su bandeja de entrada"
                        send_html_mail(f"Registro exitoso {nombresistema.upper()}",
                                       "emails_notificacion/registro_serviciosvinculacion.html",
                                       {'sistema': nombresistema.upper, 'usuario': username,
                                        'datospersona': pers, 'fecha': datetime.now(),
                                        'clave': password, 'tiposistema':tiposistema,
                                        'tit': 'Servicios Unemi.'},
                                       pers.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                        return JsonResponse({'result': False, 'funcion': True, 'titulo': f'¡Cuenta creada con éxito!', 'mensaje': mensaje})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'login':
                try:
                    request.POST = request.POST.copy()
                    request.POST['client_address'] = client_address

                    form = LoginForm(request.POST)
                    if not form.is_valid():
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                    url_redirect = request.POST['url_redirect'] if 'url_redirect' in request.POST else url_entrada
                    url_offline = form.cleaned_data['url_offline']
                    capippriva = form.cleaned_data['capippriva']
                    browser = form.cleaned_data['browser']
                    ops = form.cleaned_data['ops']
                    cookies = form.cleaned_data['cookies']
                    screensize = form.cleaned_data['screensize']
                    username = form.cleaned_data['username']
                    password = form.cleaned_data['password']
                    user = authenticate(username=username, password=password)
                    persona = user.persona_set.filter(status=True).first()
                    if not Group.objects.filter(pk=356, user=persona.usuario):
                        usuario = User.objects.get(pk=persona.usuario.id)
                        g = Group.objects.get(pk=356)
                        g.user_set.add(usuario)
                        g.save()
                    perfiles = mis_perfilesusuarios_requeridos(persona)
                    perfilprincipal = perfil_pricipal_definidio(perfiles, persona)
                    if not perfilprincipal:
                        if not Externo.objects.filter(status=True, persona=persona):
                            externo = Externo(persona=persona, activo=True)
                            externo.save(request)
                            if not PerfilUsuario.objects.filter(status=True, externo=externo):
                                perfil = PerfilUsuario(persona=persona, externo=externo)
                                perfil.save(request)
                        perfilprincipal =perfil_pricipal_definidio(perfiles, persona)
                    request.session.set_expiry(240 * 60)
                    request.session['login_manual'] = True
                    login(request, user)
                    request.session['perfiles'] = perfiles
                    request.session['persona'] = persona
                    request.session['capippriva'] = capippriva
                    request.session['tiposistema'] = tiposistema
                    request.session['tipoentrada'] = tiposistema
                    request.session['url_entrada'] = url_entrada.strip()
                    request.session['perfilprincipal'] = perfilprincipal
                    request.session['nombresistema'] = nombresistema
                    request.session['url_offline'] = url_offline
                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_VINCULACION, ip_private=capippriva,
                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                             screen_size=screensize, user=user)
                    log(u'Login con éxito: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                    adduserdata(request, data)
                    send_html_mail(f"Login exitoso {nombresistema}", "emails/loginexito.html",
                                   {'sistema': request.session['nombresistema'],
                                    'nombresistema': request.session['nombresistema'],
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(), 'bs': browser, 'ip': client_address,
                                    'ipvalida': capippriva, 'os': ops, 'cookies': cookies,
                                    'screensize': screensize, 't': miinstitucion(), 'tit': nombresistema},
                                   persona.lista_emails_envio(), [],
                                   cuenta=CUENTAS_CORREOS[4][1])
                    return JsonResponse({"result": False, 'to': f'{url_redirect}', "sessionid": request.session.session_key})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, 'mensaje': u'Login fallido, Error en el sistema. {}'.format(str(ex))})

            # elif action == 'logout':
            #     try:
            #         logout(request)
            #         if 'url_offline' in request.session:
            #             urlreturn = request.session['url_offline']+'?next=login'
            #             return JsonResponse({'result': 'ok', 'url': urlreturn})
            #         else:
            #             return JsonResponse({'result': 'ok', 'url': '/serviciosvinculacion?next=login'})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al cerrar session."})

            elif action == 'restaurar':
                try:
                    with transaction.atomic():
                        qspostulante = Postulante.objects.filter(status=True, persona__usuario_id=encrypt(request.POST['usuario']))
                        if qspostulante.exists():
                            postulante_ = qspostulante.first()
                            persona_ = postulante_.persona
                            password, anio = '', ''
                            if persona_.nacimiento:
                                anio = "*" + str(persona_.nacimiento)[0:4]
                            password = persona_.cedula.strip() + anio
                            resetear_clave_postulate(persona_)
                            send_html_mail("CONTRASEÑA RESTAURADA", "emails/postulate_cambiar_pass.html",
                                           {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': persona_, 'pass': password,
                                            't': miinstitucion()}, [persona_.email], [], cuenta=CUENTAS_CORREOS[30][1])
                            emailpersona = "{}*****@{}".format(persona_.email.split('@')[0][:3], persona_.email.split('@')[1])
                            msg = "Se restablecio contraseña, verificar su nueva contraseña en el correo {}".format(emailpersona)
                            res_json = {"resp": True, "message": msg}
                        else:
                            return JsonResponse({'resp': False, "message": "El usuario ingresado no esta asociado a ninguna cuenta de postulante."}, safe=False)
                except Exception as ex:
                    res_json = {'resp': False, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'persona' in request.session:
            return JsonResponse({'result': False, 'url_redirect': '/'})
        data['nombresistema'] = request.GET.get('nombresistema', 'Servicios de Vinculación')
        data['tiposistema'] = request.GET.get('tiposistema', 'serviciosvinculacion')
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'signup':
                try:
                    form = SignupForm()
                    data['form'] = form
                    template = get_template('core/modal/signup.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": str(ex)})

            elif action == 'login':
                try:
                    form = LoginForm()
                    data['form'] = form
                    urls = request.GET.get('args', '').split(',')
                    url_offline, url_entrada = urls[0], urls[1]
                    if len(urls) > 2:
                        url_redirect = urls[2]
                        data['url_redirect'] = url_redirect.strip()
                    data['url_offline'] = url_offline.strip()
                    data['url_entrada'] = url_entrada.strip()
                    # data['seccionado'] = True
                    template = get_template('core/modal/login.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": str(ex)})

            elif action == 'consultarcedula':
                try:
                    identificacion = request.GET['value'].strip().upper()
                    tipoidentificacion = int(request.GET.get('args',0))
                    if tipoidentificacion == 1:
                        result = validarcedula(identificacion)
                        if result != 'Ok':
                            return JsonResponse({'results': True, 'errorForm': True, 'validacion': True, 'mensaje': result})
                    elif identificacion[:2] != 'VS':
                        return JsonResponse({'results': True, 'errorForm': True, 'validacion': True, 'mensaje': 'Pasaporte incorrecto, recuerde colocar VS al inicio.'})

                    pers = consultarPersona(identificacion)
                    if pers and not pers.usuario:
                        context = {'nombres': pers.nombres,
                                   'apellido1': pers.apellido1,
                                   'apellido2': pers.apellido2,
                                   'cedula': pers.cedula != '',
                                   'nacimiento': pers.nacimiento,
                                   'sexo': pers.sexo.id,
                                   'telefono': pers.telefono,
                                   'email': pers.email}
                        return JsonResponse({'results': True, 'data': context})
                    return JsonResponse({'results': True, 'errorForm': pers != None, 'mensaje': 'Identificación ingresada ya se encuentra registrada.'})
                except Exception as ex:
                    return JsonResponse({'results': False, 'mensaje': f'Error: {ex}'})

            return HttpResponseRedirect(request.path)
        else:
            try:
                pass
            except Exception as ex:
                import sys
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                pass

@login_required(redirect_field_name='ret', login_url='/unemideportes?next=login')
@last_access
@transaction.atomic()
def passwd(request):
    data = {}
    nombresistema = request.GET.get('nombresistema', 'Servicios de Vinculación')
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'changepass':
                try:
                    currentpassword = request.POST['currentpassword']
                    newpassword = request.POST['newpassword']
                    confirmpassword = request.POST['confirmpassword']
                    espacio = mayuscula = minuscula = numeros = False
                    long = len(newpassword)  # Calcula la longitud de la contraseña
                    adduserdata(request, data)
                    persona = data['persona']
                    usuario = persona.usuario

                    for carac in newpassword:
                        espacio = True if carac.isspace() else espacio # si encuentra un espacio se cambia el valor user
                        mayuscula = True if carac.isupper() else mayuscula # acumulador o contador de mayusculas
                        minuscula = True if carac.islower() == True else minuscula # acumulador o contador de minúsculas
                        numeros = True if carac.isdigit() == True else numeros # acumulador o contador de numeros

                    if espacio == True:  # hay espacios en blanco
                        raise NameError("La clave no puede contener espacios.")
                    if not mayuscula or not minuscula or not numeros or long < 8:
                        raise NameError("La clave elegida no es segura: debe contener letras minúsculas, mayúsculas, números y al menos 8 carácter.")
                    if newpassword.lower() == currentpassword.lower():
                        raise NameError("Clave nueva no puede ser igual a la clave actual.")
                    if not newpassword.lower() == confirmpassword.lower():
                        raise NameError("Clave nueva no coincide con la confirmación de la clave")
                    if newpassword == persona.cedula:
                        raise NameError("No puede usar como clave su numero de Cédula.")
                    if not usuario.check_password(currentpassword):
                        raise NameError("Clave anterior no coincide.")

                    usuario.set_password(newpassword)
                    usuario.save()
                    persona.clave_cambiada()
                    log(u'%s - cambio clave desde IP %s' % (persona, get_client_ip(request)), request, "add")
                    send_html_mail(f"Cambio Clave {nombresistema}", "emails/cambio_clave.html", {'sistema': f'Sistema de Servicios de Vinculación', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'ip': get_client_ip(request), 'persona': persona}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                    del request.session['persona']
                    return JsonResponse({"result": False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": f"Error en formulario: {ex}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        try:
            adduserdata(request, data)
            data['title'] = u'Cambiar contraseña'
            data['subtitle'] = u'Una vez que hayas completado todos los campos, el botón de guardar se mostrará automáticamente si cumple con los criterios predefinidos.'
            data['action'] = action = 'changepass'
            data['viewactivo'] = action
            persona = data['persona']
            data['cambio_clave_obligatorio'] = persona.necesita_cambiar_clave()
            return render(request, "unemideporte/gestionarperfil/seguridad.html", data)
        except Exception as ex:
            messages.error(request, f'{ex}')
            return HttpResponseRedirect('/')

def mis_perfilesusuarios_requeridos(persona):
        return persona.perfilusuario_set.filter(visible=True, status=True).\
                                                exclude(instructor__isnull=False).\
                                                exclude(administrativo__isnull=False, administrativo__activo=False).\
                                                exclude(postulante__isnull=False).\
                                                exclude(empleador__isnull=False).\
                                                exclude(inscripcionaspirante__isnull=False, inscripcionaspirante__activo=False).\
                                                exclude(postulanteempleo__isnull=False).order_by('id')


def perfil_pricipal_definidio(perfiles, persona):
    perfil_sga = persona.perfilusuario_principal(perfiles, 'sga')
    if perfil_sga:
        return perfil_sga
    perfil_sagest = persona.perfilusuario_principal(perfiles, 'sagest')
    if perfil_sagest:
        return perfil_sagest
    perfil_posgrado = persona.perfilusuario_principal(perfiles, 'posgrado')
    if perfil_posgrado:
        return perfil_posgrado
    perfil_seleccionposgrado = persona.perfilusuario_principal(perfiles, 'seleccionposgrado')
    if perfil_seleccionposgrado:
        return perfil_seleccionposgrado
    return None
