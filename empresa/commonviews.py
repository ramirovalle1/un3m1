# coding=latin-1
# -*- coding: latin-1 -*-
import random
import json

from django.contrib.auth.decorators import login_required
from django.urls import reverse

from bd.models import FLAG_FAILED, APP_POSTULATE, TemplateBaseSetting, FLAG_SUCCESSFUL, FLAG_UNKNOWN, APP_POSTULATE, \
    APP_EMPRESA
from empleo.models import SolicitudAprobacionEmpresa
from empresa.forms import EmpleadorForm, CambioClaveFormEmpresa
from moodle.models import UserAuth
from posgrado.models import InscripcionAspirante
from settings import EMAIL_DOMAIN, ARCHIVO_TIPO_MANUALES, DECLARACION_SAGEST, DEFAULT_PASSWORD, CLAVE_USUARIO_CEDULA

from urllib.parse import urlencode
from urllib.request import urlopen, Request

from django.contrib.auth import authenticate, login
from decorators import last_access
from bd.funciones import recoveryPassword
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models.query_utils import Q

from datetime import datetime, timedelta

from sga.commonviews import adduserdata
from sga.forms import CambioClaveForm
from sga.funciones import variable_valor, calculate_username, generar_usuario_cedula, log, loglogin, resetear_clave, generar_nombre
from sga.models import Persona, CUENTAS_CORREOS, PerfilUsuario, Postulante, Group, User, Archivo, miinstitucion, \
    DeclaracionUsuario, Empleador
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# @last_access
@transaction.atomic()
def login_user(request):
    data = {}
    if EMAIL_DOMAIN in request.META['HTTP_HOST']:
        if 'empleo' not in request.META['HTTP_HOST']:
            if 'admisionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginposgrado')
            elif 'sagest' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsagest')
            elif 'seleccionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulacion')
            elif 'sga' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsga')
            elif 'postulate' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulate')

    ipvalidas = ['192.168.61.96', '192.168.61.97', '192.168.61.98', '192.168.61.99']
    client_address = get_client_ip(request)
    # site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    # if site_maintenance:
    #     return render(request, "maintenance.html", data)
    data['currenttime'] = datetime.now()
    data['sbu'] = variable_valor('SBU_VALOR')
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'login':
                try:
                    data = {}
                    capippriva = request.POST['capippriva'] if 'capippriva' in request.POST else ''
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if user is not None:
                        if not user.is_active:
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_EMPRESA, ip_private=capippriva, ip_public=client_address,
                                     browser=browser, ops=ops, cookies=cookies, screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if not persona.empleador_set.filter(status=True).exists():
                                    return JsonResponse({"result": "bad", 'mensaje': u'Lo sentimos, este usuario no cuenta con un perfil de empresa.'})
                                if not persona.empleador_set.filter(status=True, autorizada=True).exists():
                                    return JsonResponse({"result": "bad", 'mensaje': u'Lo sentimos, esta empresa aun no se encuetra autoriaza por UNEMI.'})
                                if not Group.objects.filter(pk=392, user=persona.usuario):
                                    usuario = User.objects.get(pk=persona.usuario.id)
                                    g = Group.objects.get(pk=392)
                                    g.user_set.add(usuario)
                                    g.save()
                                if persona.tiene_perfil():
                                    app = 'empresa'
                                    perfiles = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    # if not perfilprincipal:
                                    #     if not Empleador.objects.filter(status=True, persona=persona):
                                    #         empleador = Empleador(persona=persona, activo=True)
                                    #         empleador.save(request)
                                    #         if not PerfilUsuario.objects.filter(status=True, postulanteempleo=postulante):
                                    #             perfil = PerfilUsuario(persona=persona, postulanteempleo=postulante)
                                    #             perfil.save(request)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                        # return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfil para esta aplicacion.'})
                                    request.session.set_expiry(240 * 60)
                                    request.session['login_manual'] = True
                                    login(request, user)
                                    request.session['perfiles'] = perfiles
                                    request.session['persona'] = persona
                                    request.session['capippriva'] = capippriva
                                    request.session['tiposistema'] = app
                                    request.session['perfilprincipal'] = perfilprincipal
                                    nombresistema = u'Sistema de Gestión de Empresas'
                                    request.session['nombresistema'] = nombresistema
                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_EMPRESA, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user)
                                    log(u'Login con exito: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                                    adduserdata(request, data)
                                    send_html_mail("Login exitoso UNEMI EMPRESAS", "emails/loginexitoempresa.html",
                                                   {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(),
                                                    'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies,
                                                    'screensize': screensize, 't': miinstitucion(), 'tit': 'Unemi - Empresas'}, persona.lista_emails_envio(), [],
                                                   cuenta=CUENTAS_CORREOS[17][1])
                                    # return JsonResponse({"result": "ok", "sessionid": request.session.session_key})
                                    url_redirect = request.POST.get('next', '/')
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key, 'url_redirect': url_redirect})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_EMPRESA, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if not Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_EMPRESA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_EMPRESA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            # log(u'Login fallido POSGRADO: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add", user=persona.usuario)
                            send_html_mail("Login fallido UNEMI EMPRESAS.", "emails/loginfallidoempresa.html",
                                           {'sistema': u'Login fallido, no existen perfiles activos.', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser,
                                            'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize,
                                            't': miinstitucion(), 'tit': 'Unemi - Empleo'},
                                           persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[17][1])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema. {}'.format(str(ex))})

            elif action == 'registrousuario':
                try:
                    hoy, datospersona, newfile= datetime.now().date(), None, None
                    ruc = request.POST['ruc'].strip()
                    email = request.POST['email']
                    confi_correo = request.POST['confi_correo']
                    if not email == confi_correo:
                        return JsonResponse({"result": "bad", "mensaje": u"El email de confirmación es incorrecto"})
                    if 'documentoruc' in request.FILES:
                        newfile = request.FILES['documentoruc']
                        newfile._name = generar_nombre("documentoruc_", newfile._name)
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfiles = request.FILES['documentoruc']
                            newfilesd = newfiles._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext == '.pdf':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, debe cargar un documento habilitante valido."})
                    tipoinstitucionnacionalidad = request.POST['tipoinstitucionnacionalidad']
                    nombre = request.POST['nombre']
                    nombrecorto = request.POST['nombrecorto']
                    tipoempresa = request.POST['tipoempresa']
                    # tipoinstitucion = request.POST['tipoinstitucion']
                    sectoreconomico = request.POST['sectoreconomico']
                    email = request.POST['email']
                    pais = request.POST['pais']
                    provincia = request.POST['provincia']
                    canton = request.POST['canton']
                    direccion = request.POST['direccion']
                    telefonos = request.POST['telefonos']
                    telefonoconv = request.POST['telefonoconv']
                    actividadprincipal = request.POST['actividadprincipal']
                    tiposolicitud = request.POST['tiposolicitud']
                    if Persona.objects.filter(Q(ruc=ruc)).exists():
                        datospersona = Persona.objects.filter(Q(ruc=ruc)).first()
                    else:
                        datospersona = Persona(nombres=nombre, ruc=ruc, pais_id=pais, canton_id=canton, provincia_id=provincia,
                                               direccion=direccion, telefono=telefonos, telefono_conv=telefonoconv,
                                               nacimiento=hoy)
                    datospersona.email=email
                    datospersona.save(request)
                    if Empleador.objects.filter(persona=datospersona).exists():
                        datosempresa = Empleador.objects.get(persona=datospersona)
                        if datosempresa.autorizada and datospersona.usuario and PerfilUsuario.objects.filter(status=True, empleador=datosempresa).exists():
                            return JsonResponse({"result": "ok", "mensaje": u"Usted ya cuenta con un perfil de empresa. "
                                                                            u"por favor regrese al login e inicie sesión"})
                        if SolicitudAprobacionEmpresa.objects.filter(status=True, empleador=datosempresa, estadoempresa=0, fecha__lte=hoy+timedelta(days=30)).exists():
                            return JsonResponse({"result": "ok", "mensaje": u"Usted ya cuenta con una solicitud de "
                                                                            u"usuario, por favor verifique su correo electronico.",
                                                 'titulo': 'Ya se encuentra registrado'})
                    else:
                        datosempresa = Empleador(persona=datospersona)
                    datosempresa.tipoempresa_id = tipoempresa
                    # datosempresa.tipoinstitucion = tipoinstitucion
                    datosempresa.tipoinstitucionnacionalidad = tipoinstitucionnacionalidad
                    datosempresa.nombre = nombre
                    datosempresa.nombrecorto = nombrecorto
                    datosempresa.actividadprincipal = actividadprincipal
                    datosempresa.sectoreconomico = sectoreconomico
                    datosempresa.documentoruc = newfile
                    datosempresa.save(request)
                    mensaje = u"Se envio un correo de verificacion de cuenta por favor revisar"
                    solicitud = SolicitudAprobacionEmpresa(empleador=datosempresa, fecha=hoy, tiposolicitud=tiposolicitud)
                    solicitud.save(request)
                    # envio de email para el usuario sobre su solicitud de aprobacion de empresa
                    send_html_mail(u"Registro exitoso UNEMI-EMPRESAS.", "emails/empresa_registro_usuario.html",
                                   {'sistema': u'UNEMI-EMPRESAS', 'fecha': datetime.now(), 'tit': 'Unemi - Empresas'},
                                   datospersona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[17][1])

                    # envio de email para personal de unemi empleo
                    send_html_mail(u"Solicitud de aprobación de empresa", "emails/empresa_registro_usuario_validar.html",
                                   {'sistema': u'UNEMI-EMPRESAS', 'fecha': datetime.now(), 'tit': 'Unemi - Empresas'},
                                   'graduados@unemi.edu.ec', [], cuenta=CUENTAS_CORREOS[17][1])
                    return JsonResponse({'result': 'ok', "mensaje": mensaje, 'titulo': 'Registro Existoso'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            elif action == 'consultacedula':
                try:
                    ruc = request.POST['ruc'].strip()
                    datospersona, idgenero, datosempresa = None, 0, None
                    if Persona.objects.filter(ruc=ruc).exists():
                        datospersona = Persona.objects.filter(ruc=ruc).first()
                        if datospersona.usuario:
                            return JsonResponse({"result": "setlogin", 'mensaje': 'Estimado usuario usted ya cuenta con un usuario, por favor inicie sesion para continuar <br><br>'})
                        datosempresa = datospersona.empleador_set.first() if datospersona.empleador_set.exists() else None
                    if datospersona and datosempresa:
                        return JsonResponse({"result": "ok", "nombrecorto": datosempresa.nombrecorto,
                                             'sectoreconomico': datosempresa.sectoreconomico,
                                             "tipoempresa": datosempresa.tipoempresa_id, "nombre": datospersona.nombres,
                                             "email": datospersona.email, "telefonos": datospersona.telefono, "tipoinstitucion": datosempresa.tipoinstitucion,
                                             'provincia': datospersona.provincia_id, "telefonoconv": datospersona.telefono_conv,
                                             'provincia_nombre': datospersona.provincia.nombre,
                                             'pais': datospersona.pais_id,
                                             'canton_nombre': datospersona.canton.nombre, 'tipoinstitucionnacionalidad': datosempresa.tipoinstitucionnacionalidad,
                                             'canton': datospersona.canton_id, 'actividadprincipal': datosempresa.actividadprincipal,
                                             'direccion': datospersona.direccion,
                                             'documentoruc': datosempresa.documentoruc.url
                                             })
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'restaurar':
                try:
                    with transaction.atomic():
                        empresaset = Empleador.objects.filter(status=True, persona__email=request.POST['correo'], persona__usuario__username=request.POST['username'].lower().strip())
                        if empresaset.exists():
                            postulante_ = empresaset.first()
                            persona_ = postulante_.persona
                            # password, anio = '', ''
                            # if persona_.nacimiento:
                            #     anio = "*" + str(persona_.nacimiento)[0:4]
                            # password = persona_.cedula.strip() + anio
                            password = resetear_clave_empresa(persona_)
                            if not password:
                                raise NameError('No fue posible recuperar la clave')
                            send_html_mail("CONTRASEÑA RESTAURADA", "emails/empresa_cambiar_pass.html",
                                           {'sistema': u'SISTEMA UNEMI EMPRESAS', 'persona': persona_, 'pass': password,
                                            't': miinstitucion()}, [persona_.email], [], cuenta=CUENTAS_CORREOS[17][1])
                            emailpersona = "{}*****@{}".format(persona_.email.split('@')[0][:3], persona_.email.split('@')[1])
                            msg = "Se restablecio contraseña, verificar su nueva contraseña en el correo {}".format(emailpersona)
                            res_json = {"resp": True, "message": msg}
                        else:
                            return JsonResponse({'resp': False, "message": "El correo ingresado no esta asociado a ninguna cuenta de UNEMI EMPRESAS."}, safe=False)
                except Exception as ex:
                    res_json = {'resp': False, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'registrar':
                try:
                    data['title'] = "Registro de empresas"
                    data['currenttime'] = datetime.now()
                    data['institucion'] = miinstitucion().nombre
                    data['tipoentrada'] = request.session['tipoentrada'] = "EMPRESA"
                    data['form'] = EmpleadorForm()
                    data['permite_modificar'] = True
                    hoy = datetime.now().date()
                    return render(request, "empresa/login/registrar.html", data)
                except Exception as e:
                    print(e)
        else:
            if 'persona' in request.session:
                return HttpResponseRedirect("/")
            try:
                data['title'] = "Inicio de Sesión | UNEMI EMPRESAS"
                data['currenttime'] = datetime.now()
                data['institucion'] = miinstitucion().nombre
                data['tipoentrada'] = request.session['tipoentrada'] = "EMPRESA"
                data['form'] = EmpleadorForm()
                data['fecha_actual'] = datetime.now().date()
                data['nombreempresa'] = datetime.now().date()
                return render(request, "empresa/login/loginempresa.html", data)
            except Exception as ex:
                import sys
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                pass


@login_required(redirect_field_name='ret', login_url='/empresa/loginempresa')
@last_access
@transaction.atomic()
def passwd(request):
    if request.method == 'POST':
        if 'action' in request.POST:

            action = request.POST['action']
            if action == 'changepass':
                try:
                    f = CambioClaveForm(request.POST)
                    if f.is_valid():
                        data = {}
                        password = f.cleaned_data['nueva']
                        espacio = mayuscula = minuscula = numeros = False
                        long = len(password)  # Calcula la longitud de la contraseña
                        # y = password.isalnum()  # si es alfanumérica retona True
                        for carac in password:
                            espacio = True if carac.isspace() else espacio # si encuentra un espacio se cambia el valor user
                            mayuscula = True if carac.isupper() else mayuscula # acumulador o contador de mayusculas
                            minuscula = True if carac.islower() == True else minuscula # acumulador o contador de minúsculas
                            numeros = True if carac.isdigit() == True else numeros # acumulador o contador de numeros

                        if espacio == True:  # hay espacios en blanco
                            return JsonResponse({"result": "bad", "mensaje": u"La clave no puede contener espacios."})
                        if not mayuscula or not minuscula or not numeros or long < 8:
                            return JsonResponse({"result": "bad", "mensaje": u"La clave elegida no es segura: debe contener letras minúsculas, mayúsculas, números y al menos 8 carácter."})

                        adduserdata(request, data)
                        persona = data['persona']
                        if f.cleaned_data['nueva'].lower() == f.cleaned_data['anterior'].lower():
                            return JsonResponse({"result": "bad", "mensaje": u"Clave nueva no puede ser igual a la clave actual."})
                        if f.cleaned_data['nueva'] == persona.cedula:
                            return JsonResponse({"result": "bad", "mensaje": u"No puede usar como clave su numero de Cédula."})
                        usuario = persona.usuario
                        if usuario.check_password(f.cleaned_data['anterior']):
                            usuario.set_password(f.cleaned_data['nueva'])
                            usuario.save()
                            persona.clave_cambiada()
                            log(u'%s - cambio clave desde IP %s' % (persona, get_client_ip(request)), request, "add")
                            send_html_mail("Cambio Clave Unemi Empresa.", "emails/cambio_clave.html", {'sistema': u'Sistema de Gestión de Empresas', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'ip': get_client_ip(request),'persona': persona}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[17][1])
                            del request.session['persona']
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Clave anterior no coincide."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"No puedo cambiar la clave."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        try:
            data = {}
            adduserdata(request, data)
            data['title'] = u'Cambio de clave empresa'
            data['form'] = CambioClaveFormEmpresa()
            persona = data['persona']
            data['cambio_clave_obligatorio'] = persona.necesita_cambiar_clave()
            return render(request, "empresa/changepass_empresa.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')

def calculate_username_empresa(empresa, variant=1):
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
                'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    s = empresa.nombrecorto.lower().split(' ')
    while '' in s:
        s.remove('')
    usernamevariant = s[0]
    usernamevariant = usernamevariant.replace(' ', '').replace(u'ñ', 'n').replace(u'á', 'a').replace(u'é', 'e').replace(
        u'í', 'i').replace(u'ó', 'o').replace(u'ú', 'u')
    usernamevariantfinal = ''
    for letra in usernamevariant:
        if letra in alfabeto:
            usernamevariantfinal += letra
    if variant > 1:
        usernamevariantfinal += str(variant)

    if not User.objects.filter(username=usernamevariantfinal).exclude(persona=empresa.persona).exists():
        return usernamevariantfinal
    else:
        return calculate_username_empresa(empresa, variant + 1)

def resetear_clave_empresa(persona):
    from sga.models import UsuarioLdap
    anio = '**'
    # anio = "*" + str(persona.nacimiento)[0:4]
    if CLAVE_USUARIO_CEDULA:
        if not persona.usuario.is_superuser:
            if persona.cedula:
                password = persona.cedula.strip() + anio
            elif persona.pasaporte:
                password = persona.pasaporte.strip() + anio
            elif persona.ruc:
                password = persona.ruc.strip() + anio
            else:
                return None
            user = persona.usuario
            user.set_password(password)
            user.save()
            UsuarioLdap.objects.filter(usuario=user).delete()
            persona.cambiar_clave()
            return password
    return None
