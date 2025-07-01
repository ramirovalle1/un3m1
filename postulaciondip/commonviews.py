# coding=latin-1
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import calendar
import json
import random
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from sga.funciones import fechatope, loglogin
from moodle.models import UserAuth
from postulaciondip.models import InscripcionPostulante
from sagest.models import *
from settings import CONTACTO_EMAIL, EMAIL_DOMAIN, DECLARACION_SAGEST, ARCHIVO_TIPO_MANUALES
from sga.commonviews import adduserdata
from sga.funciones import log, calculate_username, generar_usuario_admision, variable_valor, resetear_clavepostulante
from sga.models import Persona, miinstitucion, DeclaracionUsuario, Noticia, Archivo, Carrera, PerfilUsuario, Nivel, \
    Periodo, CoordinacionImagenes
from sga.tasks import send_html_mail, conectar_cuenta
from posgrado.forms import RegistroForm, RegistroAdmisionIpecForm
from sga.templatetags.sga_extras import encrypt
from bd.models import APP_SGA, APP_SAGEST, APP_POSGRADO, FLAG_FAILED, FLAG_SUCCESSFUL, FLAG_UNKNOWN, TemplateBaseSetting


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# AUTENTIFICA EL USUARIO
@transaction.atomic()
def login_user(request):
    if EMAIL_DOMAIN in request.META['HTTP_HOST']:
        if 'seleccionposgrado' not in request.META['HTTP_HOST']:
            if 'admisionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginposgrado')
            elif 'sagest' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsagest')
            elif 'postulate' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulate')
            elif 'sga' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsga')
            else:
                return HttpResponseRedirect('/loginsga')

    ipvalidas = ['192.168.61.96', '192.168.61.97', '192.168.61.98', '192.168.61.99']
    client_address = get_client_ip(request)
    site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    if site_maintenance:
        data = {}
        return render(request, "maintenance.html", data)
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
                    if not client_address in ipvalidas:
                        if variable_valor('VALIDAR_CON_CAPTCHA_SAGEST'):
                            # ''' Inicio recaptcha validacion '''
                            recaptcha_response = request.POST.get('g-recaptcha-response')
                            url = 'https://www.google.com/recaptcha/api/siteverify'
                            values = {'secret': variable_valor('GOOGLE_RECAPTCHA_SECRET_KEY'),
                                      'response': recaptcha_response
                                      }
                            data = urlencode(values)
                            data = data.encode('utf-8')
                            req = Request(url, data)
                            response = urlopen(req)
                            result = json.loads(response.read().decode())
                            if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                                persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                                log(u'CAPTCHA ERROR SAGEST: %s - %s - %s - %s' % (persona, browser, ops, client_address), request, "add", user=persona.usuario)
                            if not result['success']:
                                return HttpResponse(
                                    json.dumps({"result": "bad", 'mensaje': u'ReCaptcha no válido. Vuelve a intentarlo..'}),content_type="application/json")
                            # ''' Fin recaptcha validacion '''

                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if user is not None:
                        if not user.is_active:
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_POSGRADO, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if not UserAuth.objects.filter(usuario=user).exists():
                                usermoodle = UserAuth(usuario=user)
                                usermoodle.set_data()
                                usermoodle.set_password(request.POST['pass'])
                                usermoodle.save()
                            else:
                                usermoodle = UserAuth.objects.filter(usuario=user).first()
                                isUpdateUserMoodle = False
                                if not usermoodle.check_password(request.POST['pass']) or usermoodle.check_data():
                                    if not usermoodle.check_password(request.POST['pass']):
                                        usermoodle.set_password(request.POST['pass'])
                                    usermoodle.save()
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if persona.tiene_perfil():
                                    app = 'seleccionposgrado'
                                    if not InscripcionPostulante.objects.filter(persona=persona):
                                        aspirante = InscripcionPostulante(persona=persona)
                                        aspirante.save()
                                        persona.crear_perfil(inscripcionpostulante=aspirante)
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(pk=347)
                                        g.user_set.add(usuario)
                                        g.save()
                                    else:
                                        aspirante = InscripcionPostulante.objects.filter(persona=persona)[0]
                                    if not Group.objects.filter(pk=347, user=persona.usuario):
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(pk=347)
                                        g.user_set.add(usuario)
                                        g.save()
                                    perfilesvalida = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipalvalida = persona.perfilusuario_principal(perfilesvalida, app)
                                    if not perfilprincipalvalida:
                                        aspirante = InscripcionPostulante.objects.filter(persona=persona)[0]
                                        persona.crear_perfil(inscripcionpostulante=aspirante)
                                        persona.mi_perfil()
                                    perfiles = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    if not perfilprincipal:
                                        return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfiles para esta aplicacion.'})
                                    request.session.set_expiry(240 * 60)
                                    request.session['login_manual'] = True
                                    login(request, user)
                                    data['archivos'] = Archivo.objects.filter(tipo__id=ARCHIVO_TIPO_MANUALES,grupo_id=347, sga=True, visible=True)
                                    request.session['perfiles'] = perfiles
                                    request.session['persona'] = persona
                                    request.session['postulante'] = aspirante
                                    request.session['capippriva'] = capippriva
                                    request.session['tiposistema'] = app
                                    request.session['perfilprincipal'] = perfilprincipal
                                    nombresistema = u'Sistema Posgrado'
                                    request.session['eTemplateBaseSetting'] = None
                                    request.session['nombresistema'] = nombresistema
                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_POSGRADO, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user)
                                    # log(u'Login con exito: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                                    # validacion ldap por sga
                                    if client_address in ipvalidas:
                                        if DECLARACION_SAGEST:
                                            declaracionusuario = DeclaracionUsuario(persona=persona,
                                                                                    fecha=datetime.now(),
                                                                                    ip=client_address,
                                                                                    sistema='POSGRADO')
                                            declaracionusuario.save(request)
                                            log(u'Declaracion de usuario en el posgrado: %s [%s]' % (declaracionusuario, declaracionusuario.id), request, "add")
                                    adduserdata(request, data)
                                    # send_html_mail("Login exitoso POSGRADO", "emails/loginexito.html", {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[28][1])
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_POSGRADO, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if not Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_POSGRADO, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_POSGRADO, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            # log(u'Login fallido POSGRADO: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add", user=persona.usuario)
                            # send_html_mail("Login fallido POSGRADO.", "emails/loginfallido.html", {'sistema': u'Login fallido, no existen perfiles activos.', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=variable_valor('CUENTAS_CORREOS')[4])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'persona' in request.session:
            # return HttpResponseRedirect("/postu_requisitos")
            # return HttpResponseRedirect("/postu_requisitos")
            return HttpResponseRedirect("/")
        from posgrado.models import CohorteMaestria
        data = {"title": u"Login", "background": 9}
        data['info'] = request.GET.get('info', None)
        data['request'] = request
        hoy = datetime.now().date()
        # data['noticias'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=True),(Q(publicacion=1) | Q(publicacion=3))).order_by('-desde', 'id')[0:5]
        data['noticias'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=True), (Q(publicacion=1) | Q(publicacion=3)), banerderecho=False, tipos__in=[1]).distinct().order_by('-desde', 'id')[0:5]
        # data['noticiasgraficas'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=False),(Q(publicacion=1) | Q(publicacion=3))).order_by('-desde','id')[:1]
        data['noticiasgraficas'] = None
        data['currenttime'] = datetime.now()
        data['institucion'] = miinstitucion().nombre
        data['contacto_email'] = CONTACTO_EMAIL
        data['puedeinscribirse'] = CohorteMaestria.objects.filter(fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)
        if client_address in ipvalidas:
            data['validar_con_captcha'] = False
            data['declaracion_sagest'] = False
        else:
            data['validar_con_captcha'] = variable_valor('VALIDAR_CON_CAPTCHA_SAGEST')
            data['declaracion_sagest'] = DECLARACION_SAGEST
        data['tipoentrada'] = request.session['tipoentrada'] = "POSTULACIONPOSGRADO"
        data['public_key'] = variable_valor('GOOGLE_RECAPTCHA_PUBLIC_KEY')
        return render(request, "loginpostulacion.html", data)

@transaction.atomic()
def registro_user(request):
    if request.method == 'POST':
        try:
            browser = request.POST['navegador']
            ops = request.POST['os']
            cookies = request.POST['cookies']
            screensize = request.POST['screensize']
            arregloemail = [23, 24, 25, 26, 27, 28]
            emailaleatorio = random.choice(arregloemail)
            tipoconta = 0
            tipobeca = None
            hoy = datetime.now().date()
            f = RegistroAdmisionIpecForm(request.POST)
            if f.is_valid():
                if not Persona.objects.filter(Q(pasaporte=f.cleaned_data['cedula']) | Q(cedula=f.cleaned_data['cedula']), status=True).exists():
                    if f.cleaned_data['cedula'][:2] == u'VS':
                        persona = Persona(pasaporte=f.cleaned_data['cedula'],
                                          nombres=f.cleaned_data['nombres'],
                                          apellido1=f.cleaned_data['apellido1'],
                                          apellido2=f.cleaned_data['apellido2'],
                                          email=f.cleaned_data['email'],
                                          telefono=f.cleaned_data['telefono'],
                                          sexo_id=request.POST['genero'],
                                          nacimiento='1999-01-01',
                                          direccion='',
                                          direccion2=''
                                          )
                    else:
                        persona = Persona(cedula=f.cleaned_data['cedula'],
                                          nombres=f.cleaned_data['nombres'],
                                          apellido1=f.cleaned_data['apellido1'],
                                          apellido2=f.cleaned_data['apellido2'],
                                          email=f.cleaned_data['email'],
                                          telefono=f.cleaned_data['telefono'],
                                          sexo_id=request.POST['genero'],
                                          nacimiento='1999-01-01',
                                          direccion='',
                                          direccion2=''
                                          )
                    persona.save()
                    nomusername = calculate_username(persona)
                    persona.emailinst = nomusername + '@unemi.edu.ec'
                    persona.save()
                    generar_usuario_admision(persona, nomusername, 347)
                    if not InscripcionPostulante.objects.filter(persona=persona, status=True).exists():
                        aspirante = InscripcionPostulante(persona=persona)
                        aspirante.save()
                    else:
                        aspirante = InscripcionPostulante.objects.filter(persona=persona, status=True)[0]
                    persona.crear_perfil(inscripcionpostulante=aspirante)
                    persona.mi_perfil()
                    lista = []
                    if persona.emailinst:
                        lista.append(persona.emailinst)
                    if persona.email:
                        lista.append(persona.email)
                    resetear_clavepostulante(persona)
                    if persona.cedula:
                        clavepostulante = persona.cedula.strip()
                    elif persona.pasaporte:
                        clavepostulante = persona.pasaporte.strip()
                    validapersonal(aspirante, lista, persona.usuario.username, clavepostulante)
                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario registrado, hemos generado sus credenciales \n usuario:" + persona.usuario.username + " \n clave: " + clavepostulante + " por favor acceder al siguiente link"}), content_type="application/json")
                # else:
                #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Correo ya existe, si no recuerda el usuario y la clave, siga los pasos en la opción, Olvidó su usuario y contraseña?.: "}), content_type="application/json")
                # else:
                #     return HttpResponse(json.dumps({"result": "bad", "mensaje": "Persona ya existe.: "}), content_type="application/json")
                else:
                    postulante = Persona.objects.filter(Q(pasaporte=f.cleaned_data['cedula']) | Q(cedula=f.cleaned_data['cedula']), status=True)[0]
                    lista = []
                    if not postulante.es_personalactivo():
                        postulante.email = f.cleaned_data['email']
                        postulante.save()
                    if postulante.emailinst:
                        lista.append(postulante.emailinst)
                    if postulante.email:
                        lista.append(postulante.email)
                    if not postulante.usuario:
                        nomusername = calculate_username(postulante)
                    else:
                        nomusername = postulante.usuario.username
                    if not postulante.emailinst:
                        postulante.emailinst = nomusername + '@unemi.edu.ec'
                    if not postulante.telefono:
                        postulante.telefono = f.cleaned_data['telefono']
                    postulante.save()
                    if not postulante.usuario:
                        generar_usuario_admision(postulante, nomusername, 347)
                    if not InscripcionPostulante.objects.filter(persona=postulante, status=True).exists():
                        aspirante = InscripcionPostulante(persona=postulante)
                        aspirante.save()
                    else:
                        aspirante = InscripcionPostulante.objects.filter(persona=postulante, status=True)[0]
                    if not PerfilUsuario.objects.filter(persona=postulante, inscripcionpostulante=aspirante).exists():
                        postulante.crear_perfil(inscripcionpostulante=aspirante)
                    postulante.mi_perfil()

                    if postulante.cedula:
                        clavepostulante = postulante.cedula.strip()
                    elif postulante.pasaporte:
                        clavepostulante = postulante.pasaporte.strip()
                    #Solo se debe resetear la clave a todo personal que no este activo
                    if not postulante.es_personalactivo():
                        resetear_clavepostulante(postulante)

                    if not postulante.es_personalactivo():
                        validapersonal(aspirante, lista, postulante.usuario.username, clavepostulante)
                        return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario registrado, hemos generado sus credenciales \n usuario:" + postulante.usuario.username + " \n clave: " + clavepostulante + " por favor acceder al siguiente link"}), content_type="application/json")
                    else:
                        if postulante.es_administrativo() and postulante.es_personalactivo():
                            validapersonalinterno(postulante, hoy, request, lista, tipobeca, tipoconta)
                            return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario registrado, favor acceder con las mismas credenciales del SGA o SAGEST al siguiente link"}), content_type="application/json")
                        if postulante.es_profesor() and postulante.es_personalactivo():
                            validapersonalinterno(postulante, hoy, request, lista, tipobeca, tipoconta)
                            return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario registrado, favor acceder con las mismas credenciales del SGA o SAGEST al siguiente link"}), content_type="application/json")

                return HttpResponse(json.dumps({"result": "ok","mensaje": "Usuario registrado, favor acceder al siguiente link"}), content_type="application/json")
        except Exception as ex:
            transaction.set_rollback(True)
            return HttpResponseRedirect('/loginposgrado')


def validapersonalinterno(postulante, hoy, request, lista, tipobeca, tipoconta):
    arregloemail = [23, 24, 25, 26, 27, 28]
    emailaleatorio = random.choice(arregloemail)
    if not InscripcionPostulante.objects.filter(persona=postulante, status=True).exists():
        aspirante = InscripcionPostulante(persona=postulante)
        aspirante.save()
    else:
        aspirante = InscripcionPostulante.objects.filter(persona=postulante, status=True)[0]

    if not Group.objects.filter(pk=347, user=postulante.usuario):
        usuario = User.objects.get(pk=postulante.usuario.id)
        g = Group.objects.get(pk=347)
        g.user_set.add(usuario)
        g.save()
    archivoadjunto = ''
    banneradjunto = ''
    asunto = u"Requisitos para admisión de "
    if archivoadjunto:
        send_html_mail(asunto, "emails/registroexitopersonal.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], [archivoadjunto], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    else:
        send_html_mail(asunto, "emails/registroexitopersonal.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])

    return aspirante

def validapersonal(aspirante, lista, userpostulante, clavepostulante):
    from sga.models import  CUENTAS_CORREOS
    archivoadjunto = ''
    banneradjunto = ''
    lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
    arregloemail = [23, 24, 25, 26, 27, 28]
    emailaleatorio = random.choice(arregloemail)
    asunto = u"Registro exitoso Posgrado-UNEMI"
    imagen_url = CoordinacionImagenes.objects.filter(coordinacion_id=7, tipoimagen=1, tipoimagennombre=1)[0]
    if archivoadjunto:
        send_html_mail(asunto, "emails/registroexitodip.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
                        'usuario': userpostulante,
                        'clave': clavepostulante,
                        'formato': banneradjunto, 'imagen_url': imagen_url.imagen},
                       lista, [], [archivoadjunto],
                       cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    else:
        send_html_mail(asunto, "emails/registroexitodip.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,
                        'usuario': userpostulante,
                        'clave': clavepostulante,
                        'formato': banneradjunto, 'imagen_url': imagen_url.imagen},
                       lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    return aspirante
