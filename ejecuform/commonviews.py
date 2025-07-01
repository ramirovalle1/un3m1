from django.db import transaction
from settings import EMAIL_DOMAIN
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from sga.funciones import variable_valor, log, loglogin, validarcedula
from django.shortcuts import render
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json
from sga.models import Persona, CUENTAS_CORREOS
from django.contrib.auth import authenticate, login
from bd.models import APP_FORMACION, FLAG_FAILED, FLAG_SUCCESSFUL, FLAG_UNKNOWN
from moodle.models import UserAuth
from ejecuform.models import InscripcionInteresadoFormacionEjecutiva, CategoriaEventoFormacionEjecutiva, EventoFormacionEjecutiva
from django.contrib.auth.models import User, Group
from sga.commonviews import adduserdata
from datetime import datetime
from django.db.models import Q
from sga.tasks import send_html_mail
from sga.funciones import log, calculate_username, generar_usuario_formacion

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@transaction.atomic()
def login_user(request):
    # if EMAIL_DOMAIN in request.META['HTTP_HOST']:
    #     if 'formacionejecutiva' not in request.META['HTTP_HOST']:
    #         if 'seleccionposgrado' in request.META['HTTP_HOST']:
    #             return HttpResponseRedirect('/loginpostulacion')
    #         elif 'sagest' in request.META['HTTP_HOST']:
    #             return HttpResponseRedirect('/loginsagest')
    #         elif 'postulate' in request.META['HTTP_HOST']:
    #             return HttpResponseRedirect('/loginpostulate')
    #         elif 'sga' in request.META['HTTP_HOST']:
    #             return HttpResponseRedirect('/loginsga')
    #         else:
    #             return HttpResponseRedirect('/loginsga')

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
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_FORMACION, ip_private=capippriva,
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
                                    app = 'formacionejecutiva'
                                    if not InscripcionInteresadoFormacionEjecutiva.objects.filter(persona=persona):
                                        interesado = InscripcionInteresadoFormacionEjecutiva(persona=persona)
                                        interesado.save()
                                        persona.crear_perfil(inscripcionformacion=interesado)
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(name='INTERESADO-FORMACION-EJECUTIVA')
                                        g.user_set.add(usuario)
                                        g.save()
                                    if not Group.objects.filter(name='INTERESADO-FORMACION-EJECUTIVA', user=persona.usuario):
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(name='INTERESADO-FORMACION-EJECUTIVA')
                                        g.user_set.add(usuario)
                                        g.save()
                                    perfilesvalida = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipalvalida = persona.perfilusuario_principal(perfilesvalida, app)
                                    if not perfilprincipalvalida:
                                        interesado = InscripcionInteresadoFormacionEjecutiva.objects.filter(persona=persona)[0]
                                        persona.crear_perfil(inscripcionformacion=interesado)
                                        persona.mi_perfil()
                                    perfiles = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    if not perfilprincipal:
                                        return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfiles para esta aplicacion.'})
                                    request.session.set_expiry(240 * 60)
                                    request.session['login_manual'] = True
                                    login(request, user)
                                    # data['archivos'] = Archivo.objects.filter(tipo__id=ARCHIVO_TIPO_MANUALES,grupo_id=199, sga=True, visible=True)
                                    request.session['perfiles'] = perfiles
                                    request.session['persona'] = persona
                                    request.session['capippriva'] = capippriva
                                    request.session['tiposistema'] = app
                                    request.session['perfilprincipal'] = perfilprincipal
                                    nombresistema = u'Sistema Posgrado'
                                    request.session['eTemplateBaseSetting'] = None
                                    request.session['nombresistema'] = nombresistema
                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_FORMACION, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user)
                                    # log(u'Login con exito: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                                    # validacion ldap por sga
                                    # if client_address in ipvalidas:
                                    #     if DECLARACION_SAGEST:
                                    #         declaracionusuario = DeclaracionUsuario(persona=persona,
                                    #                                                 fecha=datetime.now(),
                                    #                                                 ip=client_address,
                                    #                                                 sistema='POSGRADO')
                                    #         declaracionusuario.save(request)
                                    #         log(u'Declaracion de usuario en el posgrado: %s [%s]' % (declaracionusuario, declaracionusuario.id), request, "add")
                                    adduserdata(request, data)
                                    # send_html_mail("Login exitoso POSGRADO", "emails/loginexito.html", {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[28][1])
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_FORMACION, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if not Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_FORMACION, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_FORMACION, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            # log(u'Login fallido POSGRADO: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add", user=persona.usuario)
                            # send_html_mail("Login fallido POSGRADO.", "emails/loginfallido.html", {'sistema': u'Login fallido, no existen perfiles activos.', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[28][1])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        try:
            if 'persona' in request.session:
                return HttpResponseRedirect("/index_ejecutiva")

            data = {"title": u"Login", "background": 9}
            data['request'] = request
            hoy = datetime.now().date()
            # data['noticias'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=True), (Q(publicacion=1) | Q(publicacion=3)), banerderecho=False, tipos__in=[1]).distinct().order_by('-desde', 'id')[0:5]
            data['noticiasgraficas'] = None
            data['currenttime'] = datetime.now()
            # data['institucion'] = miinstitucion().nombre
            # data['contacto_email'] = CONTACTO_EMAIL
            # data['puedeinscribirse'] = CohorteMaestria.objects.filter(fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)
            if client_address in ipvalidas:
                data['validar_con_captcha'] = False
                data['declaracion_sagest'] = False
            else:
                data['validar_con_captcha'] = variable_valor('VALIDAR_CON_CAPTCHA_SAGEST')
                # data['declaracion_sagest'] = DECLARACION_SAGEST
            data['tipoentrada'] = request.session['tipoentrada'] = "FORMACIONEJECUTIVA"
            data['public_key'] = variable_valor('GOOGLE_RECAPTCHA_PUBLIC_KEY')
            return render(request, "loginfe.html", data)
        except Exception as ex:
            pass

def registro_user(request):
    site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    if site_maintenance:
        data = {}
        return render(request, "maintenance.html", data)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'consultacedula2':
                try:
                    cedula = request.POST['cedula'].strip()
                    hoy = datetime.now().date()
                    if request.POST['tipoidentificacion'].strip() == '1':
                        resp = validarcedula(cedula)
                        if resp != 'Ok':
                            raise NameError(u"%s." % (resp))

                    datospersona = None
                    if cedula:
                        if Persona.objects.filter(cedula=cedula).exists():
                            datospersona = Persona.objects.get(cedula=cedula)
                        elif Persona.objects.filter(pasaporte=cedula).exists():
                            datospersona = Persona.objects.get(pasaporte=cedula)
                    if datospersona:
                        postulante = datospersona
                        return JsonResponse({"result": "ok", "idpersona": datospersona.id, "apellido1": datospersona.apellido1,
                                             "apellido2": datospersona.apellido2,
                                             "nombres": datospersona.nombres, "email": datospersona.email,
                                             "telefono": datospersona.telefono, "genero": datospersona.sexo.id})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s" % (ex)})

            elif action == 'registrar':
                try:
                    tipo = int(request.POST['id_tipoiden'])
                    identificacion = request.POST['identificacion']
                    nombres = request.POST['nombres']
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    email = request.POST['email']
                    telefono = request.POST['telefono']
                    genero = int(request.POST['genero'])

                    if tipo == 1:
                        if not Persona.objects.filter(cedula=identificacion).exists():
                            ePersona = Persona(cedula=identificacion,
                                              nombres=nombres,
                                              apellido1=apellido1,
                                              apellido2=apellido2,
                                              sexo_id=genero,
                                              email=email,
                                              telefono=telefono)
                            ePersona.save()
                        else:
                            ePersona = Persona.objects.filter(cedula=identificacion).first()
                            ePersona.cedula = identificacion
                            ePersona.nombres = nombres
                            ePersona.apellido1 = apellido1
                            ePersona.apellido2 = apellido2
                            ePersona.sexo_id = genero
                            ePersona.email = email
                            ePersona.telefono = telefono
                            ePersona.save()
                    else:
                        if not Persona.objects.filter(pasaporte=identificacion).exists():
                            ePersona = Persona(pasaporte=identificacion,
                                              nombres=nombres,
                                              apellido1=apellido1,
                                              apellido2=apellido2,
                                              sexo_id=genero,
                                              email=email,
                                              telefono=telefono)
                            ePersona.save()
                        else:
                            ePersona = Persona.objects.filter(pasaporte=identificacion).first()
                            ePersona.cedula = identificacion
                            ePersona.nombres = nombres
                            ePersona.apellido1 = apellido1
                            ePersona.apellido2 = apellido2
                            ePersona.sexo_id = genero
                            ePersona.email = email
                            ePersona.telefono = telefono
                            ePersona.save()

                    if not ePersona.usuario:
                        nomusername = calculate_username(ePersona)
                        generar_usuario_formacion(ePersona, nomusername)
                        ePersona.save()
                    if InscripcionInteresadoFormacionEjecutiva.objects.filter(persona=ePersona, status=True, activo=True).exists():
                        return HttpResponse(json.dumps({"result": "bad",
                                                        "mensaje": f"Estimado {ePersona} usted ya se encuentra registrado en el sistema. Por favor, inicie sesión para que pueda acceder al catálogo de Formación Ejecutiva, y realizar su compra."}),
                                            content_type="application/json")
                    else:
                        app = 'formacionejecutiva'
                        interesado = InscripcionInteresadoFormacionEjecutiva(persona=ePersona)
                        interesado.save()
                        ePersona.crear_perfil(inscripcionformacion=interesado)
                        usuario = User.objects.get(pk=ePersona.usuario.id)
                        g = Group.objects.get(name='INTERESADO-FORMACION-EJECUTIVA')
                        g.user_set.add(usuario)
                        g.save()

                        if not Group.objects.filter(name='INTERESADO-FORMACION-EJECUTIVA', user=ePersona.usuario):
                            usuario = User.objects.get(pk=ePersona.usuario.id)
                            g = Group.objects.get(name='INTERESADO-FORMACION-EJECUTIVA')
                            g.user_set.add(usuario)
                            g.save()

                        perfilesvalida = ePersona.mis_perfilesusuarios_app(app)
                        perfilprincipalvalida = ePersona.perfilusuario_principal(perfilesvalida, app)
                        if not perfilprincipalvalida:
                            interesado = InscripcionInteresadoFormacionEjecutiva.objects.filter(persona=ePersona)[0]
                            ePersona.crear_perfil(inscripcionformacion=interesado)
                            ePersona.mi_perfil()
                        perfiles = ePersona.mis_perfilesusuarios_app(app)
                        perfilprincipal = ePersona.perfilusuario_principal(perfiles, app)

                        asunto = f'Bienvenido, {ePersona}, al Sistema de Formación Ejecutiva de UNEMI PosgradoS'
                        correo = []
                        correo.append(ePersona.email)

                        send_html_mail(asunto, "emails/registroexitoso.html",
                                           {'sistema': 'Formación ejecutiva - UNEMI POSGRADOS', 'ePersona': ePersona, 'formato': ''},
                                           correo, [],
                                           cuenta=CUENTAS_CORREOS[18][1])

                        return HttpResponse(json.dumps({"result": "ok",
                                                        "mensaje": f"Gracias por su registro, sus credenciales de acceso al sistema han sido enviadas al siguiente correo {ePersona.email}."}),
                                            content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": "%s"%ex}), content_type="application/json")

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            try:
                data = {"title": u"Registro de usuario", "background": 9}
                return render(request, "registerfe.html", data)
            except Exception as ex:
                pass

def index(request):
    site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    if site_maintenance:
        data = {}
        return render(request, "maintenance.html", data)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'allevents':
                try:
                    data = {"title": u"Todos los eventos", "background": 9}
                    data['eEventos'] = EventoFormacionEjecutiva.objects.filter(status=True, activo=True)
                    data['eCategorias'] = CategoriaEventoFormacionEjecutiva.objects.filter(status=True)
                    return render(request, "allevents.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewevent':
                try:
                    data = {"title": u"Todos los eventos", "background": 9}
                    data['eEvento'] = EventoFormacionEjecutiva.objects.get(status=True, activo=True, pk=int(request.GET['id']))
                    data['eEventos'] = EventoFormacionEjecutiva.objects.filter(status=True, activo=True)
                    return render(request, "viewevent.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewcart':
                try:
                    data = {"title": u"Carrito de compra", "background": 9}
                    return render(request, "carrito.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data = {"title": u"Formación ejecutiva", "background": 9}
                data['eCategorias'] = CategoriaEventoFormacionEjecutiva.objects.filter(status=True)
                data['eEventosCant'] = EventoFormacionEjecutiva.objects.filter(status=True).count()
                data['eEventos'] = EventoFormacionEjecutiva.objects.filter(status=True, activo=True)
                return render(request, "index.html", data)
            except Exception as ex:
                pass
